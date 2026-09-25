"""CSS injected into the Streamlit app: top nav, cards and accessibility themes."""

from __future__ import annotations

from .settings import APP_NAME, APP_SHORT_NAME, APP_TAGLINE, PROTOTYPE_DISCLAIMER

# --------------------------------------------------------------------------
# Base theme (normal + high contrast + large text are driven by CSS vars)
# --------------------------------------------------------------------------

_BASE_CSS = """
<style>
:root {
  --uata-accent:      #0F766E;
  --uata-accent-soft: #E6F4F1;
  --uata-ink:         #12211F;
  --uata-muted:       #55676A;
  --uata-surface:     #FFFFFF;
  --uata-canvas:      #F4F7F6;
  --uata-line:        #DCE5E3;
  --uata-warn:        #B45309;
  --uata-danger:      #B91C1C;
  --uata-ok:          #15803D;
  --uata-radius:      14px;
  --uata-shadow:      0 1px 2px rgba(18,33,31,.06), 0 6px 20px rgba(18,33,31,.05);
}

/* ---------------- Top navigation bar ---------------- */
.uata-nav {
  display: flex; align-items: center; gap: 18px;
  padding: 16px 22px; margin: -12px 0 18px 0;
  border-radius: var(--uata-radius);
  background: linear-gradient(100deg, #0B3B37 0%, #0F766E 55%, #14B8A6 130%);
  color: #fff; box-shadow: var(--uata-shadow);
  flex-wrap: wrap;
}
.uata-mark {
  display: grid; place-items: center;
  width: 46px; height: 46px; flex: 0 0 46px;
  border-radius: 12px; font-size: 24px; font-weight: 700;
  background: rgba(255,255,255,.16);
  border: 1px solid rgba(255,255,255,.28);
  letter-spacing: .5px;
}
.uata-brand { display: flex; flex-direction: column; gap: 3px; min-width: 260px; }
.uata-brand h1 {
  margin: 0; font-size: 1.32rem; font-weight: 700; letter-spacing: -0.015em;
  color: #fff; line-height: 1.2;
}
.uata-brand p {
  margin: 0; font-size: .82rem; color: rgba(255,255,255,.86); font-weight: 400;
}
.uata-pills { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.uata-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 999px; font-size: .76rem; font-weight: 600;
  background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
  color: #fff; white-space: nowrap;
}
.uata-pill.is-live  { background: #D1FAE5; color: #065F46; border-color: #A7F3D0; }
.uata-pill.is-demo  { background: #FEF3C7; color: #92400E; border-color: #FDE68A; }

/* ---------------- Section headers ---------------- */
.uata-section {
  display: flex; align-items: center; gap: 12px;
  margin: 4px 0 14px 0; padding-bottom: 10px;
  border-bottom: 2px solid var(--uata-line);
}
.uata-section .num {
  display: grid; place-items: center; width: 30px; height: 30px; flex: 0 0 30px;
  border-radius: 9px; background: var(--uata-accent); color: #fff;
  font-weight: 700; font-size: .9rem;
}
.uata-section h2 { margin: 0; font-size: 1.12rem; font-weight: 700; color: var(--uata-ink); }
.uata-section p  { margin: 2px 0 0 0; font-size: .82rem; color: var(--uata-muted); }

/* ---------------- Cards ---------------- */
.uata-card {
  background: var(--uata-surface); border: 1px solid var(--uata-line);
  border-radius: var(--uata-radius); padding: 16px 18px;
  box-shadow: var(--uata-shadow); margin-bottom: 14px;
}
.uata-card > h3 {
  margin: 0 0 10px 0; font-size: .96rem; font-weight: 700;
  color: var(--uata-ink); display: flex; align-items: center; gap: 8px;
}
.uata-card--tint { background: var(--uata-accent-soft); border-color: #BFE3DD; }
.uata-card--warn { background: #FFFBEB; border-color: #FDE68A; }
.uata-card--info { background: #EFF6FF; border-color: #BFDBFE; }

/* ---------------- Map legend ---------------- */
.uata-legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 4px; }
.uata-legend-item {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: .78rem; color: var(--uata-ink);
}
.uata-dot {
  width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid #fff; box-shadow: 0 0 0 1.5px currentColor; flex: 0 0 auto;
}
.uata-swatch { width: 22px; height: 4px; border-radius: 3px; flex: 0 0 auto; }

/* ---------------- Feature detail ---------------- */
.uata-kv { display: grid; grid-template-columns: minmax(120px, 34%) 1fr; gap: 6px 14px; }
.uata-kv dt { font-size: .78rem; color: var(--uata-muted); font-weight: 600; }
.uata-kv dd { margin: 0; font-size: .84rem; color: var(--uata-ink); }

.uata-badge {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: .72rem; font-weight: 700; letter-spacing: .02em;
}
.uata-badge--ok      { background: #DCFCE7; color: #166534; }
.uata-badge--caution { background: #FEF3C7; color: #92400E; }
.uata-badge--closed  { background: #FEE2E2; color: #991B1B; }
.uata-badge--info    { background: #DBEAFE; color: #1E40AF; }

/* ---------------- Intent chips ---------------- */
.uata-chips { display: flex; flex-wrap: wrap; gap: 7px; margin: 6px 0 12px 0; }
.uata-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 11px; border-radius: 999px; font-size: .78rem; font-weight: 600;
  background: var(--uata-accent-soft); color: #0B5750;
  border: 1px solid #BFE3DD;
}

/* ---------------- Route step list ---------------- */
.uata-steps { list-style: none; margin: 0; padding: 0; }
.uata-step {
  display: grid; grid-template-columns: 34px 1fr; gap: 12px;
  padding: 12px 0; border-bottom: 1px dashed var(--uata-line);
}
.uata-step:last-child { border-bottom: none; }
.uata-step .idx {
  display: grid; place-items: center; width: 28px; height: 28px;
  border-radius: 50%; background: var(--uata-accent); color: #fff;
  font-weight: 700; font-size: .82rem;
}
.uata-step--elevator .idx { background: #1D4ED8; }
.uata-step--stairs   .idx { background: #B91C1C; }
.uata-step h4 { margin: 0 0 3px 0; font-size: .92rem; color: var(--uata-ink); font-weight: 650; }
.uata-step p  { margin: 0; font-size: .82rem; color: var(--uata-muted); }
.uata-step .meta { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px; }
.uata-step .meta span {
  font-size: .7rem; font-weight: 600; padding: 2px 8px; border-radius: 6px;
  background: #F1F5F4; color: #47605E; border: 1px solid var(--uata-line);
}

/* ---------------- Route metrics ---------------- */
.uata-metrics { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.uata-metric {
  flex: 1 1 112px; background: var(--uata-surface); border: 1px solid var(--uata-line);
  border-left: 4px solid var(--uata-accent); border-radius: 10px; padding: 10px 12px;
}
.uata-metric .k { font-size: .68rem; text-transform: uppercase; letter-spacing: .05em;
                  color: var(--uata-muted); font-weight: 700; }
.uata-metric .v { font-size: 1.18rem; font-weight: 700; color: var(--uata-ink); line-height: 1.25; }
.uata-metric .s { font-size: .7rem; color: var(--uata-muted); }

/* ---------------- Micro components ---------------- */
.uata-muted { color: var(--uata-muted); font-size: .8rem; }
.uata-hr { height: 1px; background: var(--uata-line); border: 0; margin: 14px 0; }
.uata-focusable:focus-visible, .uata-card:focus-within { outline: 3px solid #14B8A6; outline-offset: 2px; }

details.uata-plain > summary {
  cursor: pointer; font-size: .82rem; font-weight: 600; color: var(--uata-accent);
  padding: 6px 0; list-style: revert;
}

/* ---------------- High contrast mode ----------------
   Streamlit sanitises <script> tags inside st.markdown, so the flag is a
   hidden marker element and the theme switch is done with :has(). */
body:has(#uata-contrast) {
  --uata-accent:      #00363A;
  --uata-accent-soft: #D6F5F2;
  --uata-ink:         #000000;
  --uata-muted:       #1A1A1A;
  --uata-surface:     #FFFFFF;
  --uata-canvas:      #FFFFFF;
  --uata-line:        #000000;
  --uata-warn:        #6B3200;
  --uata-danger:      #8A0000;
  --uata-ok:          #00430F;
}
body:has(#uata-contrast) .uata-nav {
  background: #000000; border: 3px solid #FFFFFF;
}
body:has(#uata-contrast) .uata-card,
body:has(#uata-contrast) .uata-metric,
body:has(#uata-contrast) .uata-step .meta span {
  border-width: 2px; box-shadow: none;
}
body:has(#uata-contrast) .uata-step p,
body:has(#uata-contrast) .uata-muted,
body:has(#uata-contrast) .uata-section p { color: #000000; }
body:has(#uata-contrast) .stButton button { border-width: 2px !important; font-weight: 600 !important; }
body:has(#uata-contrast) *:focus-visible { outline: 4px solid #0043FF !important; outline-offset: 2px !important; }

/* ---------------- Reduce motion ---------------- */
body:has(#uata-still) * { animation-duration: 0s !important; transition-duration: 0s !important; }

/* ---------------- Map frame ---------------- */
div[data-testid="stCustomComponentV1"] iframe { border-radius: 12px; }

/* ---------------- Footer ---------------- */
.uata-footer {
  margin-top: 26px; padding: 14px 18px; border-radius: var(--uata-radius);
  background: var(--uata-canvas); border: 1px solid var(--uata-line);
  font-size: .78rem; color: var(--uata-muted);
}
.uata-footer strong { color: var(--uata-ink); }

/* Keep Streamlit's own widgets legible against our surfaces. */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { font-weight: 600; padding: 8px 16px; }
[data-testid="stSidebar"] { border-right: 1px solid var(--uata-line); }
</style>
"""


def _font_scale_css(percent: int) -> str:
    return f"""
<style>
html, body, [class*="css"], .stApp, button, input, textarea, select {{
  font-size: {percent}% !important;
}}
.uata-brand h1 {{ font-size: 1.32rem; }}
.uata-metric .v {{ font-size: 1.22rem; }}
.uata-step h4 {{ font-size: .92rem; }}
</style>
"""


def _theme_flags(contrast: bool, reduce_motion: bool) -> str:
    """Hidden marker elements the CSS theme keys off with ``:has()``.

    ``st.markdown`` sanitises ``<script>`` tags, so the class cannot be set on
    ``<html>`` from Python; a marker element plus ``:has()`` is the script-free
    equivalent.
    """
    tags = []
    if contrast:
        tags.append('<div id="uata-contrast" hidden></div>')
    if reduce_motion:
        tags.append('<div id="uata-still" hidden></div>')
    return "".join(tags)


def inject_styles(text_scale: int = 100, contrast: bool = False,
                  reduce_motion: bool = False) -> None:
    """Render the stylesheet plus any theme markers for these settings."""
    import streamlit as st

    parts = [_BASE_CSS]
    if text_scale and text_scale != 100:
        parts.append(_font_scale_css(text_scale))
    flags = _theme_flags(contrast, reduce_motion)
    if flags:
        parts.append(flags)

    st.markdown("".join(parts), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Reusable HTML fragments
# --------------------------------------------------------------------------


def nav_bar(api_ok: bool, model: str, campus: str) -> str:
    status_cls = "is-live" if api_ok else "is-demo"
    status_txt = "Gemini connected" if api_ok else "Demo mode — no API key"
    return f"""
<div class="uata-nav" role="banner">
  <div class="uata-mark" aria-hidden="true">{APP_SHORT_NAME}</div>
  <div class="uata-brand">
    <h1>{APP_NAME}</h1>
    <p>{APP_TAGLINE}</p>
  </div>
  <div class="uata-pills">
    <span class="uata-pill">{campus}</span>
    <span class="uata-pill">{model}</span>
    <span class="uata-pill {status_cls}">{status_txt}</span>
  </div>
</div>
"""


def section_header(number: str, title: str, subtitle: str) -> str:
    return f"""
<div class="uata-section">
  <div class="num" aria-hidden="true">{number}</div>
  <div>
    <h2>{title}</h2>
    <p>{subtitle}</p>
  </div>
</div>
"""


def card(title_html: str, body_html: str, modifier: str = "") -> str:
    cls = f"uata-card {modifier}".strip()
    heading = f"<h3>{title_html}</h3>" if title_html else ""
    return f'<section class="{cls}">{heading}{body_html}</section>'


def legend_html(entries: list[tuple[str, str, str]]) -> str:
    """``entries`` are ``(colour, label, kind)`` tuples where kind is dot|line."""
    items = []
    for colour, label, kind in entries:
        if kind == "line":
            swatch = f'<span class="uata-swatch" style="background:{colour}"></span>'
        else:
            swatch = f'<span class="uata-dot" style="background:{colour};color:{colour}"></span>'
        items.append(
            f'<span class="uata-legend-item">{swatch}'
            f'<span>{label}</span></span>'
        )
    return f'<div class="uata-legend" role="list">{"".join(items)}</div>'


def status_badge(status: str, label: str) -> str:
    cls = {"open": "ok", "caution": "caution", "closed": "closed", "outage": "closed"}.get(
        status, "info"
    )
    return f'<span class="uata-badge uata-badge--{cls}">{label}</span>'


def feature_detail_html(feature, meta: dict) -> str:
    rows = []
    if feature.level:
        rows.append(f"<dt>Level</dt><dd>{feature.level}</dd>")
    for key, value in (feature.attrs or {}).items():
        rows.append(f"<dt>{key}</dt><dd>{value}</dd>")
    if feature.reported_by:
        rows.append(f"<dt>Reported by</dt><dd>{feature.reported_by}</dd>")
    if feature.updated:
        rows.append(f"<dt>Updated</dt><dd>{feature.updated}</dd>")
    kv = f'<dl class="uata-kv">{"".join(rows)}</dl>' if rows else ""
    return (
        f'<p style="margin:0 0 10px 0;font-size:.88rem;color:var(--uata-ink)">'
        f"{feature.description}</p>{kv}"
    )


def intent_chips_html(chips: list[tuple[str, str]]) -> str:
    if not chips:
        return ""
    return (
        '<div class="uata-chips" role="list">'
        + "".join(
            f'<span class="uata-chip" role="listitem"><span aria-hidden="true">{icon}</span>{label}</span>'
            for icon, label in chips
        )
        + "</div>"
    )


def metric_tile(key: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="s">{sub}</div>' if sub else ""
    return (
        f'<div class="uata-metric"><div class="k">{key}</div>'
        f'<div class="v">{value}</div>{sub_html}</div>'
    )


def metrics_row(tiles: list[str]) -> str:
    return f'<div class="uata-metrics">{"".join(tiles)}</div>'


def steps_html(steps) -> str:
    rows = []
    for step in steps:
        meta = [f"{step.distance_m:g} m", f"{step.width_m:g} m wide", step.surface]
        if step.gradient_pct is not None:
            meta.append(f"{step.gradient_pct:g}% slope")
        if step.crossings:
            meta.append(f"{step.crossings} crossing{'s' if step.crossings > 1 else ''}")
        if step.kind == "elevator":
            meta.append("Elevator")
        if step.kind == "stairs":
            meta.append("Stairs")
        if step.tactile in ("guidance", "warning"):
            meta.append("Tactile " + step.tactile)
        meta_html = "".join(f"<span>{m}</span>" for m in meta)
        rows.append(
            f'<li class="uata-step uata-step--{step.kind}">'
            f'<div class="idx" aria-hidden="true">{step.order}</div>'
            f"<div><h4>{step.instruction}</h4><p>{step.detail}</p>"
            f'<div class="meta">{meta_html}</div></div></li>'
        )
    return f'<ol class="uata-steps">{"".join(rows)}</ol>'


def notices_html(notes: list[str], tone: str = "warn") -> str:
    if not notes:
        return ""
    items = "".join(f"<li>{n}</li>" for n in notes)
    modifier = "uata-card--warn" if tone == "warn" else "uata-card--info"
    return (
        f'<section class="uata-card {modifier}"><h3>⚠ Please note</h3>'
        f'<ul style="margin:0;padding-left:20px;font-size:.84rem;line-height:1.6">{items}</ul></section>'
    )


def footer_html() -> str:
    return f"""
<div class="uata-footer" role="contentinfo">
  <strong>Prototype — sample data only.</strong> {PROTOTYPE_DISCLAIMER}
  Always confirm a real route with campus accessibility services before travelling.
</div>
"""
