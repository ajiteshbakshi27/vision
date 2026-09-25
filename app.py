"""Urban Accessibility & Tactile Navigation Assistant.

A Streamlit prototype with three primary sections:

1. An interactive campus map with clickable accessibility pins.
2. "Check Obstacle via Gemini Vision" - image upload + Gemini Vision analysis.
3. A voice assistant panel that turns a spoken-style command into a
   step-free route.

Run with::

    streamlit run app.py
"""

from __future__ import annotations
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Your existing imports go below here:
from src import assistant, demo_content, gemini, sample_image, settings, speech
import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path

import google.generativeai as genai
import streamlit as st
import streamlit.components.v1 as components

from src import assistant, demo_content, gemini, sample_image, settings, speech, styles
from src.campus_data import (
    EDGE_BY_ID,
    EDGES,
    FEATURE_BY_ID,
    FEATURE_META,
    FEATURES,
    HAZARD_CATEGORIES,
    PLACE_BY_ID,
    PLACES,
    STATUS_LABELS,
    place_name,
)
from src.routing import (
    RoutePrefs,
    find_route,
    nearby_features,
    route_summary_text,
    spoken_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parent
MAP_COMPONENT_DIR = PROJECT_ROOT / "components" / "campus_map"

campus_map = components.declare_component(
    "campus_map", path=str(MAP_COMPONENT_DIR)
)

# --------------------------------------------------------------------------
# Mobility profiles -> default routing preferences
# --------------------------------------------------------------------------

PROFILES: dict[str, dict] = {
    "🪑  Manual wheelchair": dict(step_free_only=True, avoid_stairs=True,
                                   avoid_construction=True, max_gradient_pct=6.0,
                                   min_clear_width_m=0.9, prefer_tactile=False,
                                   prefer_ramps=True, avoid_elevators=False),
    "⚡  Power wheelchair": dict(step_free_only=True, avoid_stairs=True,
                                 avoid_construction=True, max_gradient_pct=8.3,
                                 min_clear_width_m=0.8, prefer_tactile=False,
                                 prefer_ramps=False, avoid_elevators=False),
    "🦯  White cane / blind": dict(step_free_only=True, avoid_stairs=True,
                                   avoid_construction=True, max_gradient_pct=8.3,
                                   min_clear_width_m=1.2, prefer_tactile=True,
                                   prefer_ramps=False, avoid_elevators=False),
    "👓  Low vision": dict(step_free_only=True, avoid_stairs=True,
                           avoid_construction=True, max_gradient_pct=8.3,
                           min_clear_width_m=1.0, prefer_tactile=False,
                           prefer_ramps=False, avoid_elevators=False),
    "🛒  Stroller / trolley": dict(step_free_only=False, avoid_stairs=True,
                                    avoid_construction=True, max_gradient_pct=12.0,
                                    min_clear_width_m=0.8, prefer_tactile=False,
                                    prefer_ramps=False, avoid_elevators=False),
    "👣  Stairs are acceptable": dict(step_free_only=False, avoid_stairs=False,
                                      avoid_construction=False, max_gradient_pct=100.0,
                                      min_clear_width_m=0.5, prefer_tactile=False,
                                      prefer_ramps=False, avoid_elevators=False),
}

PREF_KEYS = list(next(iter(PROFILES.values())).keys())


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "map_last_ts": None,
        "selected_pin": None,
        "selected_edge": None,
        "selected_place": None,
        "vision_result": None,
        "vision_source_name": None,
        "hazard_alert": None,
        "hazard_source_name": None,
        "route": None,
        "intent": None,
        "narration": None,
        "narration_source": None,
        "chat": [],
        "applied_profile": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown(f"### {settings.APP_SHORT_NAME} controls")
        st.caption("Everything here is applied live to the map, the routing engine "
                   "and the output formatting.")

        st.divider()
        st.markdown("#### Campus")
        campus = st.selectbox(
            "Campus", [settings.CAMPUS_NAME],
            help="Only the sample campus ships with this prototype.",
            label_visibility="collapsed",
        )

        st.markdown("#### Google AI Studio")
        api_ok, api_msg = settings.api_key_status()
        if api_ok:
            st.success(api_msg, icon="✅")
        else:
            st.warning(api_msg, icon="⚠️")
            st.caption("Vision and narration fall back to built-in demo responses.")
        model = st.selectbox("Model", settings.MODEL_CHOICES, index=0)
        if st.button("How to get a key", width="stretch", key="how_key"):
            st.session_state.show_key_help = not st.session_state.get("show_key_help", False)
        if st.session_state.get("show_key_help"):
            st.info(
                "1. Open https://aistudio.google.com/apikey\n"
                "2. Create an API key\n"
                "3. Put it in `.env` as `GOOGLE_API_KEY=...`\n"
                "4. Restart `streamlit run app.py`",
            )

        st.divider()
        st.markdown("#### Mobility profile")
        profile = st.segmented_control(
            "Mobility profile",
            list(PROFILES),
            label_visibility="collapsed",
            key="profile_pick",
        )
        profile = profile or list(PROFILES)[0]

        if st.session_state.applied_profile != profile:
            for key, value in PROFILES[profile].items():
                st.session_state[f"pref_{key}"] = value
            st.session_state.applied_profile = profile

        prefs = RoutePrefs(
            step_free_only=st.session_state["pref_step_free_only"],
            avoid_stairs=st.session_state["pref_avoid_stairs"],
            avoid_construction=st.session_state["pref_avoid_construction"],
            max_gradient_pct=st.session_state["pref_max_gradient_pct"],
            min_clear_width_m=st.session_state["pref_min_clear_width_m"],
            prefer_tactile=st.session_state["pref_prefer_tactile"],
            prefer_ramps=st.session_state["pref_prefer_ramps"],
            avoid_elevators=st.session_state["pref_avoid_elevators"],
        )

        with st.expander("Fine-tune route preferences", expanded=False):
            st.toggle("Step-free routes only", key="pref_step_free_only",
                      help="Exclude every link that needs stairs.")
            st.toggle("Avoid stairs entirely", key="pref_avoid_stairs",
                      help="Off means stairs may be used as a last resort.")
            st.toggle("Avoid construction and closed walks", key="pref_avoid_construction")
            st.toggle("Prefer tactile paving", key="pref_prefer_tactile",
                      help="Weight routes towards guidance strips and warning surfaces.")
            st.toggle("Prefer ramps and gentle gradients", key="pref_prefer_ramps")
            st.toggle("Avoid elevators", key="pref_avoid_elevators")
            st.slider("Maximum gradient (%)", min_value=2.0, max_value=12.0,
                      step=0.5, key="pref_max_gradient_pct",
                      help="Slopes above this are treated as barriers.")
            st.slider("Minimum clear width (m)", min_value=0.5, max_value=1.8,
                      step=0.1, key="pref_min_clear_width_m",
                      help="Narrower paths are treated as barriers.")

        st.caption(f"Active profile: **{prefs.label()}**")

        st.divider()
        st.markdown("#### Accessibility & display")
        scale_label = st.radio(
            "Text size", list(settings.TEXT_SCALES),
            label_visibility="collapsed", key="text_scale",
        )
        text_scale = settings.TEXT_SCALES[scale_label]
        contrast = st.toggle("High contrast", key="contrast",
                             help="Pure black on white, heavier borders.")
        reduce_motion = st.toggle("Reduce motion", key="reduce_motion",
                                  help="Disable transitions and animation.")
        auto_speak = st.toggle("Offer read-aloud", value=True, key="auto_speak",
                               help="Show a read-aloud button on generated guidance.")

        if st.button("Reset session", width="stretch", key="reset_session"):
            for key in ("vision_result", "vision_source_name", "hazard_alert",
                        "hazard_source_name", "route", "intent", "narration",
                        "narration_source", "chat", "selected_pin",
                        "selected_edge", "selected_place"):
                st.session_state.pop(key, None)
            st.session_state.map_last_ts = None
            st.rerun()

    return {
        "campus": campus,
        "model": model,
        "profile": profile,
        "prefs": prefs,
        "text_scale": text_scale,
        "contrast": contrast,
        "reduce_motion": reduce_motion,
        "auto_speak": auto_speak,
        "api_ok": api_ok,
    }


# --------------------------------------------------------------------------
# Shared UI atoms
# --------------------------------------------------------------------------


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:10]


def nearest_place(feature) -> object:
    """The place whose centre is closest to a feature pin."""
    return min(PLACES, key=lambda p: math.hypot(p.x - feature.x, p.y - feature.y))


def take_pending(target_key: str) -> str | None:
    """Move a queued value onto a widget key *before* that widget is created.

    Streamlit forbids writing ``st.session_state[key]`` once the widget owning
    that key has been instantiated in the same script run, so buttons queue the
    value under ``pending_<key>`` and this pops it on the next run, while the
    widget still does not exist.
    """
    return st.session_state.pop(f"pending_{target_key}", None)


def set_pending(target_key: str, value: str) -> None:
    """Queue a value for a widget and rerun so it is applied immediately."""
    st.session_state[f"pending_{target_key}"] = value
    st.rerun()


def map_legend_entries() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    pins = [(meta["color"], meta["label"], "dot") for meta in FEATURE_META.values()]
    lines = [
        ("#7FA39E", "Step-free walk", "line"),
        ("#B91C1C", "Stairs only", "line"),
        ("#1D4ED8", "Elevator", "line"),
        ("#DC2626", "Closed / construction", "line"),
        ("#7C3AED", "Active route", "line"),
    ]
    return pins, lines


def render_map() -> None:
    st.markdown(
        styles.section_header(
            "1",
            "Interactive campus map",
            "Click any pin for accessible paths, elevators and reported hazards. "
            "Paths and stairs are clickable too.",
        ),
        unsafe_allow_html=True,
    )

    route = st.session_state.get("route")
    if route and route.ok:
        st.markdown(
            styles.card(
                "",
                styles.metrics_row([
                    styles.metric_tile("Distance", f"{route.total_m:g} m",
                                       f"~{route.walking_minutes} min"),
                    styles.metric_tile("Steepest", f"{route.max_gradient:g}%",
                                       f"limit {route.prefs.max_gradient_pct:g}%"),
                    styles.metric_tile("Narrowest", f"{route.min_width:g} m",
                                       f"min {route.prefs.min_clear_width_m:g} m"),
                    styles.metric_tile("Elevators", str(route.elevators),
                                       "step-free"),
                    styles.metric_tile("Crossings", str(route.crossings),
                                       "listen before each"),
                ])
                + f'<p class="uata-muted" style="margin:0">'
                  f"<b>{place_name(route.origin)}</b> → <b>{place_name(route.destination)}</b> "
                  f"— highlighted in purple on the map.</p>",
                "uata-card--tint",
            ),
            unsafe_allow_html=True,
        )

    pins, lines = map_legend_entries()
    left, right = st.columns([2.25, 1], gap="medium")

    with left:
        args = {
            "places": [p.to_dict() for p in PLACES],
            "edges": [e.to_dict() for e in EDGES],
            "features": [f.to_dict() for f in FEATURES],
            "selected": st.session_state.selected_pin,
            "route": route.edge_ids if route and route.ok else [],
            "origin": (PLACE_BY_ID[route.origin].to_dict()
                       if route and route.ok else None),
            "destination": (PLACE_BY_ID[route.destination].to_dict()
                            if route and route.ok else None),
            "contrast": st.session_state.get("contrast", False),
        }
        event = campus_map(**args, key="campus_map", default=None)

        if event and event.get("ts") != st.session_state.map_last_ts:
            st.session_state.map_last_ts = event.get("ts")
            if event.get("type") == "feature":
                st.session_state.selected_pin = event["id"]
                st.session_state.selected_edge = None
            elif event.get("type") == "edge":
                st.session_state.selected_edge = event["id"]
                st.session_state.selected_pin = None
            st.rerun()

        st.markdown(
            styles.legend_html(pins + lines),
            unsafe_allow_html=True,
        )

    with right:
        render_selection_panel()
        render_feature_list()


def render_selection_panel() -> None:
    pin_id = st.session_state.selected_pin
    edge_id = st.session_state.selected_edge

    if pin_id and pin_id in FEATURE_BY_ID:
        feature = FEATURE_BY_ID[pin_id]
        meta = FEATURE_META[feature.kind]
        status = STATUS_LABELS.get(feature.status, feature.status)
        title = (
            f'<span aria-hidden="true">{meta["glyph"]}</span>&nbsp; '
            f"{feature.name} {styles.status_badge(feature.status, status)}"
        )
        note = ""
        if feature.category:
            note = f'<p class="uata-muted" style="margin:8px 0 0 0">Category: ' \
                   f"{HAZARD_CATEGORIES.get(feature.category, feature.category)}</p>"
        st.markdown(
            styles.card(title,
                        styles.feature_detail_html(feature, meta) + note,
                        "uata-card--warn" if feature.kind == "hazard" else ""),
            unsafe_allow_html=True,
        )
        target = nearest_place(feature)
        cols = st.columns(2)
        if cols[0].button(f"Route to {target.name}", width="stretch", key="pin_route",
                          help="Fills the voice assistant with this destination"):
            st.session_state.assistant_notice = (
                f"Request ready in the **Voice assistant** tab: “Take me to "
                f"{target.name}” (nearest place to {feature.name})."
            )
            set_pending("cmd", f"Take me to {target.name}")
        if cols[1].button("Clear", width="stretch", key="pin_clear"):
            st.session_state.selected_pin = None
            st.rerun()

    elif edge_id and edge_id in EDGE_BY_ID:
        edge = EDGE_BY_ID[edge_id]
        rows = [
            ("Between", f"{place_name(edge.a)} ↔ {place_name(edge.b)}"),
            ("Length", f"{edge.length_m:g} m"),
            ("Surface", edge.surface),
            ("Clear width", f"{edge.width_m:g} m"),
            ("Gradient", f"{edge.gradient_pct:g}%" if edge.gradient_pct is not None else "n/a"),
            ("Step-free", "Yes" if edge.step_free else "No"),
            ("Tactile", {"guidance": "Guidance strip", "warning": "Warning tiles",
                         "none": "None"}[edge.tactile]),
            ("Crossings", str(edge.crossings)),
            ("Lighting", edge.lighting),
        ]
        kv = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
        if edge.note:
            kv += f'<dt>Note</dt><dd>{edge.note}</dd>'
        st.markdown(
            styles.card(f"🛣️&nbsp; {edge.name}", f'<dl class="uata-kv">{kv}</dl>',
                        "uata-card--warn" if not edge.step_free else "uata-card--info"),
            unsafe_allow_html=True,
        )
        if st.button("Clear", width="stretch", key="edge_clear"):
            st.session_state.selected_edge = None
            st.rerun()

    else:
        st.markdown(
            styles.card(
                "👆 Nothing selected",
                '<p class="uata-muted" style="margin:0">Click a pin or a path on the '
                "map — or use the feature list below, which works with a keyboard "
                "and a screen reader.</p>",
            ),
            unsafe_allow_html=True,
        )


def render_feature_list() -> None:
    st.markdown("##### Accessible feature list")
    st.caption("Keyboard and screen-reader equivalent of the map pins.")

    kinds = ["All"] + list(FEATURE_META)
    wanted = st.radio(
        "Show", kinds, horizontal=True, label_visibility="collapsed",
        key="filter_kind",
    )

    for kind in FEATURE_META:
        if wanted != "All" and wanted != kind:
            continue
        meta = FEATURE_META[kind]
        items = [f for f in FEATURES if f.kind == kind]
        st.markdown(
            f'<div class="uata-muted" style="margin:10px 0 4px 0;font-weight:700;'
            f'color:{meta["color"]}">{meta["glyph"]} {meta["label"]} '
            f'<span style="font-weight:400">({len(items)})</span></div>',
            unsafe_allow_html=True,
        )
        for feature in items:
            selected = st.session_state.selected_pin == feature.id
            label = f"{meta['glyph']} {feature.name}"
            if feature.status == "closed":
                label += "  ⚠ closed"
            if st.button(label, key=f"pick_{feature.id}", width="stretch",
                         type="primary" if selected else "secondary"):
                st.session_state.selected_pin = feature.id
                st.session_state.selected_edge = None
                st.rerun()


# --------------------------------------------------------------------------
# Section 2 - Vision
# --------------------------------------------------------------------------

#: The prompt sent with the image. Kept verbatim so the wording stays stable.
HAZARD_PROMPT = (
    "Identify any accessibility hazards in this picture for a visually or "
    "physically impaired person, such as stairs, curbs, or construction "
    "blockages. Give a 2-sentence audio-friendly alert."
)

#: The model this function asks for. Gemini 1.5 Flash has since been shut down
#: by Google, so a live key will get a 404 on this name and we fall back down
#: the list below. Override HAZARD_MODEL to pin a different model.
HAZARD_MODEL = "gemini-1.5-flash"
HAZARD_MODEL_FALLBACKS = ("gemini-2.5-flash", "gemini-2.0-flash")


@dataclass
class HazardAlert:
    """Outcome of :func:`check_accessibility_hazards`."""

    ok: bool
    text: str = ""
    model: str = ""
    requested_model: str = HAZARD_MODEL
    error: str = ""
    source: str = "gemini"  # gemini | demo
    substituted: bool = False


def _gemini_key() -> str | None:
    """GEMINI_API_KEY from the environment, or the aliases settings accepts."""
    value = os.getenv("GEMINI_API_KEY", "").strip()
    if value and "your_" not in value.lower():
        return value
    return settings.get_api_key()


def check_accessibility_hazards(
    image: bytes,
    mime_type: str = "image/jpeg",
    model: str = HAZARD_MODEL,
) -> HazardAlert:
    """Send one image to Gemini and return a 2-sentence spoken alert.

    Tries ``model`` first. If the API reports that name is unavailable it walks
    ``HAZARD_MODEL_FALLBACKS`` so the function still returns an answer on a live
    key, and flags the substitution for display. Returns ``HazardAlert`` rather
    than raising: a missing key, a missing SDK, a bad key and an API error all
    come back as ``ok=False`` with an explanation.
    """
    key = _gemini_key()
    if not key:
        return HazardAlert(
            ok=False, source="demo",
            error=f"{settings.api_key_status()[1]} — this function reads GEMINI_API_KEY.",
        )

    try:
        genai.configure(api_key=key)
    except Exception as exc:  # malformed key, SDK-level misconfiguration
        return HazardAlert(ok=False, source="demo",
                           error=f"{type(exc).__name__}: {exc}")

    candidates = (model, *(m for m in HAZARD_MODEL_FALLBACKS if m != model))
    last_error = ""

    for candidate in candidates:
        try:
            response = genai.GenerativeModel(candidate).generate_content(
                [HAZARD_PROMPT, {"mime_type": mime_type, "data": image}],
                generation_config={"temperature": 0.2, "max_output_tokens": 200},
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            # Only step to the next model for "no such model"; anything else
            # (bad key, quota, network) would fail identically on every model.
            if "not found" not in last_error.lower() and "404" not in last_error:
                return HazardAlert(ok=False, source="demo", model=candidate,
                                   error=last_error)
            continue

        text = (getattr(response, "text", "") or "").strip()
        if not text:
            last_error = "Gemini returned an empty response."
            continue

        return HazardAlert(
            ok=True, text=text, model=candidate, requested_model=model,
            substituted=(candidate != model),
        )

    return HazardAlert(ok=False, source="demo", model=model, error=last_error)


def render_hazard_alert(alert: HazardAlert, image_name: str) -> None:
    """Show a :class:`HazardAlert` on screen, clearly and accessibly."""
    if not alert.ok:
        st.error(alert.error, icon="🚫")
        st.caption("Add GEMINI_API_KEY to .env and restart the app to enable the "
                   "live Gemini call.")
        return

    if alert.source == "demo":
        st.warning(demo_content.DEMO_BANNER_QUICK)
    if alert.substituted:
        st.info(
            f"`{alert.requested_model}` is no longer served by the Gemini API, so "
            f"this answer came from `{alert.model}` instead.",
            icon="ℹ️",
        )

    st.markdown(
        styles.card(
            "🔊&nbsp; Accessibility alert",
            f'<p style="margin:0;font-size:1.12rem;line-height:1.7;'
            f'color:var(--uata-ink)">{alert.text}</p>',
            "uata-card--warn",
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        f"Model: `{alert.model}` · Source image: **{image_name}** · "
        f"Prompt: 2-sentence audio-friendly alert"
    )
    speech.read_aloud(alert.text, label="Read the alert aloud",
                      key=f"tts_hazard_{_hash(alert.text)}")


def render_vision(cfg: dict) -> None:
    st.markdown(
        styles.section_header(
            "2",
            "Check Obstacle via Gemini Vision",
            "Upload or capture a photo of a walkway. Gemini reports the obstacle, "
            "its effect on a wheelchair, tactile hazards and the best detour.",
        ),
        unsafe_allow_html=True,
    )

    api_ok = cfg["api_ok"]
    if not api_ok:
        st.markdown(
            styles.card(
                "⚠ Demo mode",
                '<p style="margin:0 0 8px 0;font-size:.86rem">'
                f"{settings.api_key_status()[1]}. You can still run the whole flow — "
                "the app will return a built-in example report so the prototype is "
                "demonstrable end to end.</p>",
                "uata-card--warn",
            ),
            unsafe_allow_html=True,
        )

    left, right = st.columns([1, 1], gap="medium")

    with left:
        st.markdown("##### 1. Provide the photo")
        source = st.radio(
            "Image source", ["Upload a photo", "Use the camera", "Synthetic test image"],
            horizontal=True, key="vision_source",
        )
        image_bytes: bytes | None = None
        mime = "image/jpeg"
        source_name = ""

        if source == "Upload a photo":
            uploaded = st.file_uploader(
                "Check Obstacle via Gemini Vision — upload a photo",
                type=["jpg", "jpeg", "png", "webp"],
                key="vision_upload",
                help="A photo of the path ahead, at roughly eye or wheelchair height.",
            )
            if uploaded is not None:
                image_bytes = uploaded.getvalue()
                mime = uploaded.type or mime
                source_name = uploaded.name
                st.image(image_bytes, caption=uploaded.name, width="stretch")
        elif source == "Use the camera":
            shot = st.camera_input(
                "Check Obstacle via Gemini Vision — capture a photo",
                key="vision_camera",
            )
            if shot is not None:
                image_bytes = shot.getvalue()
                mime = "image/png"
                source_name = "camera capture"
                st.image(image_bytes, caption="Camera capture", width="stretch")
        else:
            image_bytes = sample_image.sample_obstacle_photo()
            mime = sample_image.sample_mime()
            source_name = "synthetic test image"
            st.image(image_bytes, caption="Synthetic test image (generated locally)",
                     width="stretch")
            st.caption("A flat illustration, not a photograph. It exercises the "
                       "code path so the demo works without a photo to hand.")

    with right:
        st.markdown("##### 2. Describe the context")
        place_ids = list(PLACE_BY_ID)
        location = st.selectbox(
            "Where was this photo taken?",
            place_ids, format_func=place_name, key="vision_location",
        )
        level = st.selectbox(
            "Level", ["Ground / L1", "L2", "Basement", "Unknown"], key="vision_level",
        )
        focus = st.radio(
            "What should the model focus on?",
            ["Wheelchair passability & clear width",
             "Tactile & trip hazards",
             "Steep gradients & kerbs",
             "Best step-free detour"],
            key="vision_focus",
        )
        extra = st.text_area(
            "Anything else the model should know?", "",
            placeholder="e.g. the chair is a rigid frame with 24-inch wheels; the "
                        "photo was taken from the middle of the path.",
            key="vision_extra", height=90,
        )

        st.markdown("##### 3. Analyse")
        quick = st.button(
            "Quick hazard alert (2 sentences)",
            type="primary", width="stretch",
            disabled=image_bytes is None,
            help=f"Send the image to {HAZARD_MODEL} and get a short spoken alert.",
        )
        clicked = st.button(
            "Full accessibility report",
            width="stretch",
            disabled=image_bytes is None,
            help="A longer structured report with severity, clear width and detour.",
        )
        if not image_bytes:
            st.caption("Add a photo to enable analysis.")
        if image_bytes and not api_ok:
            st.caption("No API key configured — built-in example text will be shown.")

    if quick and image_bytes:
        with st.spinner(f"Analysing with {HAZARD_MODEL}…"):
            alert = check_accessibility_hazards(image_bytes, mime)
        if not _gemini_key():
            alert = HazardAlert(ok=True, text=demo_content.DEMO_QUICK_ALERT,
                                model=f"{HAZARD_MODEL} (canned)", source="demo")
        st.session_state.hazard_alert = alert
        st.session_state.hazard_source_name = source_name
        st.rerun()

    alert = st.session_state.get("hazard_alert")
    if alert:
        st.divider()
        st.markdown("##### Quick alert")
        render_hazard_alert(alert, st.session_state.get("hazard_source_name", "—"))

    if clicked and image_bytes:
        with st.spinner(f"Analysing with {cfg['model']}…"):
            prompt_extra = f"\n\nAdditional user context: {extra}" if extra else ""
            if api_ok:
                result = gemini.analyze_obstacle(
                    (image_bytes, mime),
                    location=place_name(location),
                    level=level,
                    focus=focus + prompt_extra,
                    model=cfg["model"],
                )
            else:
                result = gemini.GeminiResult(
                    ok=True, text=demo_content.DEMO_VISION_REPORT,
                    source="demo", model="demo (canned report)",
                )
        st.session_state.vision_result = result
        st.session_state.vision_source_name = source_name
        st.session_state.vision_context = {
            "location": place_name(location), "level": level,
            "focus": focus, "extra": extra,
        }
        st.rerun()

    result = st.session_state.get("vision_result")
    if not result:
        return

    st.divider()
    st.markdown("##### 4. Result")
    st.caption(
        f"Source image: **{st.session_state.get('vision_source_name', '—')}** · "
        f"Model: **{result.model}**"
    )
    if result.source == "demo":
        st.markdown(demo_content.DEMO_BANNER)

    if not result.ok:
        st.error(result.error, icon="🚫")
        return

    parsed = gemini.parse_vision_json(result.text)
    if parsed:
        st.markdown(
            styles.metrics_row([
                styles.metric_tile("Severity", str(parsed.get("severity", "—")).title()),
                styles.metric_tile("Passable", _passable_label(parsed.get("wheelchair_passable"))),
                styles.metric_tile("Clear width", _width_label(parsed.get("clear_width_m"))),
                styles.metric_tile("Action", str(parsed.get("recommended_action", "—"))
                                   .replace("_", " ").title()),
            ]),
            unsafe_allow_html=True,
        )
        st.markdown(
            styles.card(
                "🔊&nbsp; One-sentence read-aloud",
                f'<p style="margin:0;font-size:1.02rem;line-height:1.55">'
                f"{parsed.get('summary', '—')}</p>",
                "uata-card--tint",
            ),
            unsafe_allow_html=True,
        )
        if parsed.get("detour_hint"):
            st.markdown(
                styles.card("↪️&nbsp; Suggested detour",
                            f'<p style="margin:0;font-size:.9rem">'
                            f"{parsed['detour_hint']}</p>", "uata-card--info"),
                unsafe_allow_html=True,
            )

    with st.expander("Full Gemini report", expanded=True):
        st.markdown(_strip_trailing_json(result.text))

    if cfg["auto_speak"]:
        spoken = (parsed or {}).get("summary") or result.text[:600]
        speech.read_aloud(spoken, label="Read the report aloud",
                          key=f"tts_vision_{_hash(result.text)}")

    with st.expander("Plain-text version (screen reader / copy-paste)"):
        st.code(_strip_trailing_json(result.text), language="markdown")


def _strip_trailing_json(text: str) -> str:
    import re

    cleaned = re.sub(r"```(?:json)?\s*.+?```", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _passable_label(value) -> str:
    if value is None or value == "":
        return "Unclear"
    return "Yes" if str(value).lower() in ("true", "yes") else "No"


def _width_label(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):g} m"
    except (TypeError, ValueError):
        return str(value)


# --------------------------------------------------------------------------
# Section 3 - Voice assistant
# --------------------------------------------------------------------------


def render_assistant(cfg: dict) -> None:
    st.markdown(
        styles.section_header(
            "3",
            "Voice assistant",
            "Type or dictate a request. The assistant works out the destination and "
            "your mobility constraints, then plans a step-free route.",
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1.35], gap="medium")

    # ---------------- input ----------------
    with left:
        st.markdown("##### Say what you need")
        notice = st.session_state.pop("assistant_notice", None)
        if notice:
            st.info(notice, icon="➡️")
        st.markdown(
            '<div class="uata-card uata-card--tint" style="padding:14px 16px">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="font-size:1.7rem" aria-hidden="true">🎙</div>'
            '<div><div style="font-weight:700;font-size:.95rem;color:var(--uata-ink)">'
            "Voice input (simulated)</div>"
            '<div style="font-size:.8rem;color:var(--uata-muted)">'
            "Type below, or pick a suggested phrase</div></div></div></div>",
            unsafe_allow_html=True,
        )

        # Apply anything a map/phrase button queued, before the input exists.
        queued = take_pending("cmd")
        if queued is not None:
            st.session_state.cmd = queued

        # `key` alone owns the value: passing `value=` as well would conflict
        # with the session-state assignment above.
        st.text_input(
            "Your request",
            placeholder="Take me to Library via ramp",
            key="cmd",
            label_visibility="collapsed",
        )
        st.caption("Example: “Take me to Library via ramp”")

        st.markdown("**Suggested phrases**")
        phrase_cols = st.columns(2)
        for index, phrase in enumerate(assistant.EXAMPLE_COMMANDS):
            with phrase_cols[index % 2]:
                if st.button(phrase, key=f"phrase_{index}", width="stretch",
                             help="Simulates hearing this phrase"):
                    set_pending("cmd", phrase)

        with st.expander("🎙 Simulate hearing a phrase", expanded=False):
            picked = st.selectbox(
                "Phrase the microphone 'hears'", assistant.EXAMPLE_COMMANDS,
                key="voice_pick",
            )
            st.markdown(
                '<div aria-hidden="true" style="display:flex;align-items:flex-end;'
                'gap:3px;height:26px;margin:6px 0 10px 0">'
                + "".join(
                    f'<div style="flex:1;background:#0F766E;border-radius:2px;'
                    f'height:{h}%"></div>'
                    for h in (30, 62, 95, 48, 78, 40, 88, 55, 34, 70, 45, 60)
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Use this phrase", width="stretch", key="voice_use"):
                set_pending("cmd", picked)

        c1, c2 = st.columns(2)
        interpret = c1.button("Interpret request", type="primary",
                              width="stretch", key="interpret")
        if c2.button("Clear", width="stretch", key="clear_cmd"):
            st.session_state.route = None
            st.session_state.intent = None
            st.session_state.narration = None
            st.session_state.chat = []
            set_pending("cmd", "")

    # ---------------- output ----------------
    with right:
        st.markdown("##### Understood request")
        intent = st.session_state.get("intent")
        if not intent:
            st.info("Your parsed request will appear here.", icon="👂")

        if interpret and st.session_state.get("cmd", "").strip():
            handle_command(st.session_state["cmd"], cfg)
            st.rerun()

        render_intent_and_route(intent, cfg)


def handle_command(text: str, cfg: dict) -> None:
    default_origin = st.session_state.get("start_place", settings.DEFAULT_ORIGIN)
    intent = assistant.parse_command(text, default_origin=default_origin)

    prefs = RoutePrefs(
        step_free_only=st.session_state["pref_step_free_only"],
        avoid_stairs=st.session_state["pref_avoid_stairs"],
        avoid_construction=st.session_state["pref_avoid_construction"],
        max_gradient_pct=st.session_state["pref_max_gradient_pct"],
        min_clear_width_m=st.session_state["pref_min_clear_width_m"],
        prefer_tactile=st.session_state["pref_prefer_tactile"] or intent.prefer_tactile,
        prefer_ramps=st.session_state["pref_prefer_ramps"] or intent.via_ramp,
        avoid_elevators=st.session_state["pref_avoid_elevators"],
    )
    if "stairs" in intent.avoid:
        prefs.step_free_only = True
        prefs.avoid_stairs = True
    if "construction" in intent.avoid:
        prefs.avoid_construction = True
    if "steep slopes" in intent.avoid:
        prefs.max_gradient_pct = min(prefs.max_gradient_pct, 5.0)
    if "elevators" in intent.avoid:
        prefs.avoid_elevators = True
    if intent.via_ramp:
        # "via ramp" means take the ramp, not the lift. If no ramp route exists the
        # solver relaxes this first and says so.
        prefs.avoid_elevators = True
    if intent.via_elevator:
        prefs.avoid_elevators = False

    st.session_state.intent = intent
    st.session_state.chat.append({"role": "user", "text": text})

    if not intent.destination:
        st.session_state.route = None
        st.session_state.narration = None
        st.session_state.chat.append({
            "role": "assistant",
            "text": "I could not work out where you want to go. "
                    "Try “Take me to Library via ramp”, or name a building such as "
                    "the Student Union, Science Centre or Cafeteria.",
        })
        return

    via = list(intent.waypoints)
    route = find_route(intent.origin or settings.DEFAULT_ORIGIN,
                       intent.destination, prefs, via)
    st.session_state.route = route
    st.session_state.narration = None
    st.session_state.narration_source = None

    if not route.ok:
        st.session_state.chat.append({"role": "assistant", "text": route.reason})
        return

    brief = route_summary_text(route)
    narration = None
    if cfg["api_ok"]:
        with st.spinner("Composing spoken guidance…"):
            result = gemini.narrate_route(brief, text, model=cfg["model"])
        if result.ok:
            narration = result.text
            st.session_state.narration_source = "gemini"

    if narration is None:
        # No key (or the call failed): narrate the route we actually computed, so
        # the spoken guidance can never contradict the numbers on screen.
        narration = spoken_summary(route)
        st.session_state.narration_source = "demo"

    st.session_state.narration = narration
    st.session_state.chat.append({"role": "assistant", "text": narration})


def render_intent_and_route(intent, cfg: dict) -> None:
    if not intent:
        return

    st.markdown(styles.intent_chips_html(intent.chips()), unsafe_allow_html=True)

    if intent.notes:
        st.markdown(styles.notices_html(intent.notes, tone="warn"),
                    unsafe_allow_html=True)

    route = st.session_state.get("route")
    if not route:
        return

    if not route.ok:
        st.error(route.reason, icon="🚫")
        return

    st.markdown(
        styles.metrics_row([
            styles.metric_tile("Distance", f"{route.total_m:g} m",
                               f"~{route.walking_minutes} min"),
            styles.metric_tile("Steepest", f"{route.max_gradient:g}%",
                               f"limit {route.prefs.max_gradient_pct:g}%"),
            styles.metric_tile("Narrowest", f"{route.min_width:g} m",
                               f"min {route.prefs.min_clear_width_m:g} m"),
            styles.metric_tile("Elevators", str(route.elevators)),
            styles.metric_tile("Crossings", str(route.crossings)),
        ]),
        unsafe_allow_html=True,
    )

    if route.relaxations:
        st.markdown(
            styles.notices_html(
                ["To give you a route I had to relax: " + "; ".join(route.relaxations)
                 + ". Check each step before you rely on it."],
                tone="warn",
            ),
            unsafe_allow_html=True,
        )
    if route.warnings:
        st.markdown(styles.notices_html(route.warnings, tone="warn"),
                    unsafe_allow_html=True)

    with st.expander(f"Step-by-step directions ({len(route.steps)} steps)",
                     expanded=True):
        st.markdown(styles.steps_html(route.steps), unsafe_allow_html=True)

    narration = st.session_state.get("narration")
    if narration:
        if st.session_state.get("narration_source") == "demo":
            st.markdown(demo_content.DEMO_BANNER)
        st.markdown(
            styles.card(
                "🔊&nbsp; Spoken guidance",
                f'<p style="margin:0;font-size:1.06rem;line-height:1.7;'
                f'color:var(--uata-ink)">{narration}</p>',
                "uata-card--tint",
            ),
            unsafe_allow_html=True,
        )
        if cfg["auto_speak"]:
            speech.read_aloud(narration, label="Read directions aloud",
                              key=f"tts_route_{_hash(route_summary_text(route))}")

    # Nearby accessible features at the destination
    near = nearby_features(route.destination, radius=150)
    if near:
        with st.expander("Accessible features near the destination"):
            rows = "".join(
                f'<li style="margin-bottom:6px"><b>{FEATURE_META[f.kind]["glyph"]} '
                f'{f.name}</b> <span class="uata-muted">— {f.description}</span></li>'
                for f in near
            )
            st.markdown(f'<ul style="padding-left:20px;font-size:.86rem">{rows}</ul>',
                        unsafe_allow_html=True)

    render_follow_up(route, cfg)


def render_follow_up(route, cfg: dict) -> None:
    with st.expander("Ask a follow-up about this route", expanded=False):
        queued = take_pending("followup_q")
        if queued is not None:
            st.session_state.followup_q = queued
        question = st.text_input(
            "Follow-up question", key="followup_q",
            placeholder="Is there a step-free way if the elevator is out?",
            label_visibility="collapsed",
        )
        if st.button("Ask", key="ask_followup", width="content"):
            if question.strip():
                brief = route_summary_text(route)
                answer = None
                if cfg["api_ok"]:
                    with st.spinner("Thinking…"):
                        result = gemini.narrate_route(brief, question,
                                                      model=cfg["model"])
                    answer = result.text if result.ok else None
                if answer is None:
                    answer = demo_content.DEMO_ASSISTANT_REPLIES[0]
                st.session_state.chat.append({"role": "user", "text": question})
                st.session_state.chat.append({"role": "assistant", "text": answer})
                set_pending("followup_q", "")

    if st.session_state.get("chat"):
        with st.expander("Conversation history", expanded=True):
            for message in st.session_state.chat:
                with st.chat_message(message["role"]):
                    st.markdown(message["text"])


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title=settings.APP_NAME,
        page_icon="♿",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()

    # Accessibility preferences are needed before the first paint of the nav bar.
    scale_key = "text_scale"
    scale_label = st.session_state.get(scale_key, list(settings.TEXT_SCALES)[0])
    styles.inject_styles(
        text_scale=settings.TEXT_SCALES.get(scale_label, 100),
        contrast=st.session_state.get("contrast", False),
        reduce_motion=st.session_state.get("reduce_motion", False),
    )

    cfg = render_sidebar()
    # Sidebar widgets may have changed the settings; re-inject if so.
    styles.inject_styles(
        text_scale=settings.TEXT_SCALES.get(
            st.session_state.get(scale_key, list(settings.TEXT_SCALES)[0]), 100),
        contrast=cfg["contrast"],
        reduce_motion=cfg["reduce_motion"],
    )

    st.markdown(
        styles.nav_bar(cfg["api_ok"], cfg["model"], cfg["campus"]),
        unsafe_allow_html=True,
    )

    map_tab, vision_tab, voice_tab = st.tabs(
        ["🗺️ Campus map", "👁️ Check obstacle (Gemini Vision)", "🎙 Voice assistant"]
    )
    with map_tab:
        render_map()
    with vision_tab:
        render_vision(cfg)
    with voice_tab:
        render_assistant(cfg)

    st.markdown(styles.footer_html(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
