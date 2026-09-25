"""Thin wrapper around the Google AI Studio (Gemini) SDKs.

Supports the current ``google-genai`` package and falls back to the legacy
``google-generativeai`` package. Every call is non-fatal: if no key is set, the
SDK is missing, or the request fails, the caller receives a friendly result and
can fall back to the built-in demo responses.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from . import settings

# --------------------------------------------------------------------------
# Result envelope
# --------------------------------------------------------------------------


@dataclass
class GeminiResult:
    ok: bool
    text: str = ""
    error: str = ""
    source: str = "gemini"  # gemini | demo
    model: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.ok


# --------------------------------------------------------------------------
# Client construction
# --------------------------------------------------------------------------


def _make_client(api_key: str) -> tuple[str, Any]:
    """Return ``(sdk_name, client)`` for whichever SDK is installed."""
    try:
        from google import genai  # type: ignore

        return "genai", genai.Client(api_key=api_key)
    except Exception:
        pass
    try:
        import google.generativeai as legacy  # type: ignore

        legacy.configure(api_key=api_key)
        return "legacy", legacy
    except Exception:
        pass
    try:  # pragma: no cover - google-genai present but needs newer config
        from google import genai  # type: ignore

        return "genai", genai.Client(api_key=api_key)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "No Google Gen AI SDK found. Install it with: "
            "pip install google-genai"
        ) from exc


# --------------------------------------------------------------------------
# Core generation
# --------------------------------------------------------------------------


def generate(
    prompt: str,
    *,
    model: str | None = None,
    image: tuple[bytes, str] | None = None,
    temperature: float = 0.4,
) -> GeminiResult:
    """Run a single-turn generation, optionally with one inline image.

    ``image`` is ``(raw_bytes, mime_type)``.
    """
    api_key = settings.get_api_key()
    if not api_key:
        return GeminiResult(
            ok=False,
            error=settings.api_key_status()[1],
            source="demo",
            model=model or settings.DEFAULT_MODEL,
        )

    chosen = model or settings.DEFAULT_MODEL
    try:
        sdk, client = _make_client(api_key)
    except Exception as exc:
        return GeminiResult(ok=False, error=str(exc), source="demo", model=chosen)

    try:
        if sdk == "genai":
            from google.genai import types  # type: ignore

            contents: list[Any] = [types.Part.from_text(text=prompt)]
            if image:
                data, mime = image
                contents.append(types.Part.from_bytes(data=data, mime_type=mime))
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=SYSTEM_PREAMBLE,
            )
            response = client.models.generate_content(
                model=chosen, contents=contents, config=config
            )
            text = (response.text or "").strip()
        else:
            import google.generativeai as legacy  # type: ignore

            parts: list[Any] = [prompt]
            if image:
                data, mime = image
                parts.append({"mime_type": mime, "data": data})
            client_model = legacy.GenerativeModel(
                chosen, system_instruction=SYSTEM_PREAMBLE
            )
            response = client_model.generate_content(
                parts,
                generation_config={"temperature": temperature},
            )
            text = (response.text or "").strip()

        if not text:
            return GeminiResult(ok=False, error="The model returned an empty response.",
                                source="demo", model=chosen)
        return GeminiResult(ok=True, text=text, source="gemini", model=chosen)
    except Exception as exc:
        return GeminiResult(
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            source="demo",
            model=chosen,
        )


SYSTEM_PREAMBLE = (
    "You are the accessibility co-pilot inside a campus wayfinding prototype. "
    "You describe streets, campuses and buildings for people who navigate by "
    "wheelchair, white cane, or who are blind or have low vision. "
    "Be concrete and safety-first: never invent legal compliance, never give "
    "false reassurance, and clearly say when you are uncertain. "
    "Prefer short spoken sentences that sound natural read aloud. "
    "Always note the nearest step-free alternative when a route is blocked."
)


# --------------------------------------------------------------------------
# Vision: obstacle checking
# --------------------------------------------------------------------------

VISION_SCHEMA = {
    "obstacle_type": "construction | stairs | broken_paving | vehicle | mud | flooding | event | unknown",
    "severity": "clear | minor | moderate | severe | blocked",
    "wheelchair_passable": "true | false | null",
    "clear_width_m": "number or null — narrowest gap you can see",
    "estimated_gradient_pct": "number or null",
    "tactile_hazard": "true | false",
    "summary": "one plain sentence a screen reader can announce",
    "recommended_action": "proceed | proceed_with_caution | use_alternate_route | seek_assistance",
    "detour_hint": "one short sentence, or an empty string",
    "confidence": "number between 0 and 1",
}

_VISION_PROMPT = """\
You are inspecting a photograph of an outdoor walkway for a person who uses a
wheelchair or who is blind.

Location context: {location}
Floor / level: {level}
User's focus: {focus}

Answer these questions from the image only. Do not guess about anything you
cannot see, and do not claim a route is compliant.

1. What physical obstacle or condition is present?
2. What is the narrowest clear width you can estimate, and the gradient?
3. Is there a drop, kerb, step, loose surface, or missing tactile paving?
4. Is the far end still passable, or is the path blocked?
5. What is the nearest step-free alternative, if one is visible or implied?
6. What single sentence should be read aloud to the user right now?

Respond with a short markdown report using these headings:
- **What I can see**
- **Obstacle**
- **Wheelchair impact**
- **Tactile & trip hazards**
- **Recommended action**
- **Uncertainty**

Then append a single fenced ```json block containing EXACTLY these keys:
{schema}

All values must be plain JSON (no comments, no trailing commas).
"""


def analyze_obstacle(
    image: tuple[bytes, str],
    *,
    location: str,
    level: str,
    focus: str,
    model: str | None = None,
) -> GeminiResult:
    """Send one image plus context to Gemini Vision for an obstacle report."""
    prompt = _VISION_PROMPT.format(
        location=location,
        level=level,
        focus=focus,
        schema=json.dumps(VISION_SCHEMA, indent=2),
    )
    result = generate(prompt, model=model, image=image, temperature=0.2)
    if result.ok:
        result.text = f"**Model:** `{result.model}`\n\n" + result.text
    return result


_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)```", re.DOTALL)


def parse_vision_json(text: str) -> dict[str, Any] | None:
    """Pull the trailing JSON block out of a vision report."""
    blocks = _FENCE_RE.findall(text or "")
    for block in reversed(blocks):
        block = block.strip()
        start, end = block.find("{"), block.rfind("}")
        if start == -1 or end == -1:
            continue
        try:
            data = json.loads(block[start : end + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k in VISION_SCHEMA}
    return None


# --------------------------------------------------------------------------
# Assistant
# --------------------------------------------------------------------------


def narrate_route(route_brief: str, question: str, *, model: str | None = None) -> GeminiResult:
    """Ask Gemini to turn a computed route brief into a spoken-style narration."""
    prompt = f"""\
Here is a computed, accessibility-aware route on a fictional campus:

{route_brief}

The user asked: "{question}"

Write the spoken guidance a screen reader or text-to-speech engine should read:
- Maximum 140 words. No markdown, no bullet points, no emoji.
- Open with the total distance and a one-phrase purpose ("Heading to the library").
- Number the directions naturally ("First...", "Then...", "Finally...").
- Call out the step-free alternative for any stairs, and warn clearly before crossings.
- Finish with one short safety sentence.
"""
    result = generate(prompt, model=model, temperature=0.5)
    if result.ok:
        result.text = re.sub(r"\s+", " ", result.text).strip()
    return result
