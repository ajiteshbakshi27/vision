"""Application settings, environment loading and shared helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

APP_NAME = "Urban Accessibility & Tactile Navigation Assistant"
APP_SHORT_NAME = "UATA"
APP_TAGLINE = (
    "Step-free routing, obstacle checks and voice guidance "
    "for an accessible campus"
)

#: Checked in order when looking for the Google AI Studio key. GEMINI_API_KEY
#: leads because that is the name the app's quick hazard alert documents.
API_KEY_ENV_NAMES = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_AI_STUDIO_API_KEY",
)

#: Values that mean "the developer forgot to paste a real key".
_PLACEHOLDERS = ("your_", "yourkey", "paste", "changeme", "replace", "xxxx", "<", "todo")

MODEL_CHOICES = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]
DEFAULT_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-3.8-flash")
if DEFAULT_MODEL not in MODEL_CHOICES:
    MODEL_CHOICES.insert(0, DEFAULT_MODEL)

#: Sidebar text-size control -> root font scale (percent).
TEXT_SCALES = {
    "Standard": 100,
    "Large": 115,
    "Extra Large": 130,
}

#: Where the user is assumed to be standing unless they say otherwise.
DEFAULT_ORIGIN = os.getenv("DEFAULT_ORIGIN", "MAIN_GATE")

CAMPUS_NAME = os.getenv("CAMPUS_NAME", "Jaypee Campus")

PROTOTYPE_DISCLAIMER = (
    "Prototype build. Locations, gradients and hazard reports on this map are "
    "**fictional sample data** and must not be used for real navigation or "
    "mobility decisions."
)


def get_api_key() -> str | None:
    """Return the Google AI Studio key from the environment, or ``None``."""
    for name in API_KEY_ENV_NAMES:
        raw = os.getenv(name, "")
        value = raw.strip().strip('"').strip("'")
        if not value:
            continue
        if any(token in value.lower() for token in _PLACEHOLDERS):
            continue
        return value
    return None


def api_key_status() -> tuple[bool, str]:
    """Human-readable API key status for the sidebar."""
    key = get_api_key()
    if key:
        return True, f"Key found (…{key[-4:]})"
    missing = ", ".join(API_KEY_ENV_NAMES)
    return False, f"No key set — add {missing} to .env"
