"""Rule-based intent parsing for the voice assistant panel.

The prototype parses spoken-style commands without needing a network call so
the demo works offline. Gemini is only used afterwards, to polish the wording
of an already-computed route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .campus_data import match_place, place_name

# --------------------------------------------------------------------------
# Intent
# --------------------------------------------------------------------------


@dataclass
class Intent:
    """The parsed result of one spoken-style command."""

    raw: str
    origin: str | None = None
    destination: str | None = None
    waypoints: list[str] = field(default_factory=list)
    via_ramp: bool = False
    via_elevator: bool = False
    avoid: list[str] = field(default_factory=list)  # stairs | construction | steep | elevators
    prefer_tactile: bool = False
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def has_destination(self) -> bool:
        return bool(self.destination)

    def chips(self) -> list[tuple[str, str]]:
        """Short ``(icon, label)`` pairs describing the parsed intent."""
        out: list[tuple[str, str]] = []
        if self.origin:
            out.append(("📍", f"From {place_name(self.origin)}"))
        if self.destination:
            out.append(("🏁", f"To {place_name(self.destination)}"))
        for via in self.waypoints:
            out.append(("↪", f"Via {place_name(via)}"))
        if self.via_ramp:
            out.append(("♿", "Via ramp"))
        if self.via_elevator:
            out.append(("⇅", "Via elevator"))
        if self.prefer_tactile:
            out.append(("≡", "Prefer tactile paving"))
        for avoid in self.avoid:
            out.append(("🚫", f"Avoid {avoid}"))
        return out


# --------------------------------------------------------------------------
# Phrase tables
# --------------------------------------------------------------------------

_RAMP_WORDS = ("ramp", "ramps", "rammed")
_ELEVATOR_WORDS = ("elevator", "lift", "lifts", "elevators")
_TACTILE_WORDS = ("tactile", "guide strip", "guidance", "paving", "blister", "domes")
_STAIR_WORDS = ("stairs", "stair", "steps", "step free", "step-free", "stepless")
_CONSTRUCTION_WORDS = ("construction", "works", "closed", "closure", "roadworks", "dig")
_STEEP_WORDS = ("steep", "hill", "hillock", "slope", "gradient", "incline", "flat")
_URGENT_WORDS = ("urgent", "hurry", "quick", "quickly", "emergency", "asap", "now", "fast")

_FROM_RE = re.compile(r"\bfrom\s+(.+?)(?=\s+to\s+|\s+via\s+|,|$)", re.IGNORECASE)
_TO_RE = re.compile(r"\b(?:to|toward|towards|get to|go to|find|reach|directions to)\s+(.+?)(?=\s+via\s+|,|$)", re.IGNORECASE)
_VIA_RE = re.compile(r"\bvia\s+(.+?)(?=\s+via\s+|,|$)", re.IGNORECASE)

_POLITE_PREFIX = re.compile(
    r"^\s*(please\s+|could you\s+|can you\s+|i need to\s+|i want to\s+|"
    r"i'd like to\s+|help me\s+|take me\s+|show me\s+|navigate\s+|navigate me\s+|"
    r"directions\s+|route\s+|way to\s+|how do i get to\s+)+",
    re.IGNORECASE,
)
_TRAILING_NOISE = re.compile(
    r"[?!.]*\s*(please|thanks|thank you|now|for me|okay|ok|hey|hello)\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    cleaned = _POLITE_PREFIX.sub("", text or "")
    cleaned = _TRAILING_NOISE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.?!")
    return cleaned or (text or "").strip()


def _any(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def parse_command(text: str, default_origin: str | None = None) -> Intent:
    """Parse a spoken-style navigation command into an :class:`Intent`."""
    raw = (text or "").strip()
    intent = Intent(raw=raw)
    if not raw:
        intent.notes.append("Empty command — type or dictate something first.")
        return intent

    body = _normalise(raw)
    low = body.lower()

    # --- Origin -----------------------------------------------------------
    from_match = _FROM_RE.search(body)
    if from_match:
        origin = match_place(from_match.group(1))
        if origin:
            intent.origin = origin
        else:
            intent.notes.append(
                f"Could not place the starting point “{from_match.group(1).strip()}”."
            )

    # --- Destination ------------------------------------------------------
    to_match = _TO_RE.search(body)
    if to_match:
        destination = match_place(to_match.group(1))
        if destination:
            intent.destination = destination
        else:
            intent.notes.append(
                f"Could not place the destination “{to_match.group(1).strip()}”."
            )

    # --- Waypoints --------------------------------------------------------
    for via_match in _VIA_RE.finditer(body):
        fragment = via_match.group(1).strip()
        if _any(fragment, _RAMP_WORDS):
            intent.via_ramp = True
            continue
        if _any(fragment, _ELEVATOR_WORDS):
            intent.via_elevator = True
            continue
        via = match_place(fragment)
        if via and via not in (intent.origin, intent.destination):
            intent.waypoints.append(via)

    # --- Implicit destination ("the library", "library please") ----------
    if not intent.destination:
        candidate = match_place(body)
        if candidate and candidate != intent.origin:
            intent.destination = candidate
        elif candidate and not intent.origin:
            intent.destination = candidate

    # --- Preferences ------------------------------------------------------
    if _any(low, _RAMP_WORDS):
        intent.via_ramp = True
    if _any(low, _ELEVATOR_WORDS):
        intent.via_elevator = True
    if _any(low, _TACTILE_WORDS):
        intent.prefer_tactile = True

    negative = bool(re.search(r"\b(avoid|without|no|skip|not via|not using|don't use|dont use)\b", low))
    if negative:
        if _any(low, _STAIR_WORDS):
            intent.avoid.append("stairs")
        if _any(low, _CONSTRUCTION_WORDS):
            intent.avoid.append("construction")
        if _any(low, _STEEP_WORDS):
            intent.avoid.append("steep slopes")
        if _any(low, _ELEVATOR_WORDS):
            intent.avoid.append("elevators")
    else:
        if _any(low, _STAIR_WORDS):
            intent.notes.append("Stairs mentioned — this will be read as a step-free preference.")
            intent.avoid.append("stairs")
        if _any(low, _CONSTRUCTION_WORDS):
            intent.avoid.append("construction")

    # --- Fallback origin --------------------------------------------------
    if not intent.origin and default_origin:
        intent.origin = default_origin

    # --- Confidence -------------------------------------------------------
    intent.confidence = _score(intent, raw)
    if not intent.destination:
        intent.notes.append(
            "No destination recognised. Try “Take me to Library via ramp”."
        )
    return intent


def _score(intent: Intent, raw: str) -> float:
    if not intent.destination:
        return 0.0
    score = 0.55
    if intent.origin:
        score += 0.15
    if intent.waypoints or intent.via_ramp or intent.via_elevator or intent.avoid:
        score += 0.12
    if _TO_RE.search(_normalise(raw)):
        score += 0.10
    if intent.notes and not intent.destination:
        score -= 0.2
    return round(min(score, 0.97), 2)


# --------------------------------------------------------------------------
# Example commands shown in the UI
# --------------------------------------------------------------------------

EXAMPLE_COMMANDS: tuple[str, ...] = (
    "Take me to Library via ramp",
    "Get me to the Science Centre, avoid stairs",
    "Reach the Health Centre from the Main Gate",
    "Go to the Cafeteria, prefer tactile paving",
    "Nearest accessible restroom to the Union?",
    "Take me to Administration via the Quad",
    "Route me to Engineering Hall, no construction",
)
