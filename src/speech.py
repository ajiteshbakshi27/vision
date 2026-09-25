"""Read-aloud button rendered with the browser Web Speech API.

Uses ``st.iframe`` rather than a bidirectional component: the direction of data
flow is one-way (Python -> browser), so no custom-component runtime is needed
and it degrades gracefully when the API is unavailable.
"""

from __future__ import annotations

import json

import streamlit as st

_TEMPLATE = """
<div class="uata-tts">
  <button type="button" id="__ID__play" class="tts-btn">
    <span class="tts-ico" aria-hidden="true">&#128266;</span>
    <span class="tts-lbl">__LABEL__</span>
  </button>
  <button type="button" id="__ID__stop" class="tts-btn tts-btn--ghost" hidden
          aria-label="Stop reading">&#9632;</button>
  <span id="__ID__state" class="tts-state" role="status" aria-live="polite"></span>
</div>

<style>
.uata-tts { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 4px 0 2px 0; }
.tts-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer;
  font-family: inherit; font-size: 0.86rem; font-weight: 650;
  color: #fff; background: #0F766E; border: 1.5px solid #0B5C56;
  transition: background .12s ease, transform .06s ease;
}
.tts-btn:hover { background: #115E59; }
.tts-btn:active { transform: translateY(1px); }
.tts-btn:focus-visible { outline: 3px solid #0F766E; outline-offset: 3px; }
.tts-btn--ghost { background: #fff; color: #0B5C56; padding: 9px 13px; }
.tts-btn[disabled] { opacity: .55; cursor: not-allowed; }
.tts-ico { font-size: 1rem; line-height: 1; }
.tts-state { font-size: .78rem; color: #55676A; }
body.uata-contrast .tts-btn { background: #000; border-color: #000; color: #fff; }
body.uata-contrast .tts-btn--ghost { background: #fff; color: #000; }
</style>

<script>
(function () {
  var TEXT = __TEXT__;
  var RATE = __RATE__;
  var play = document.getElementById("__ID__play");
  var stop = document.getElementById("__ID__stop");
  var state = document.getElementById("__ID__state");

  if (!("speechSynthesis" in window)) {
    play.disabled = true;
    state.textContent = "Text-to-speech is not available in this browser.";
    return;
  }

  function speak() {
    window.speechSynthesis.cancel();
    var utter = new SpeechSynthesisUtterance(TEXT);
    utter.rate = RATE;
    utter.pitch = 1.0;
    utter.onstart = function () {
      state.textContent = "Reading\\u2026";
      stop.hidden = false;
    };
    utter.onend = function () {
      state.textContent = "Finished.";
      stop.hidden = true;
    };
    utter.onerror = function () {
      state.textContent = "Could not read this aloud.";
      stop.hidden = true;
    };
    window.speechSynthesis.speak(utter);
  }

  play.addEventListener("click", speak);
  stop.addEventListener("click", function () {
    window.speechSynthesis.cancel();
    state.textContent = "Stopped.";
    stop.hidden = true;
  });
  window.addEventListener("beforeunload", function () { window.speechSynthesis.cancel(); });
})();
</script>
"""


def read_aloud(
    text: str,
    *,
    label: str = "Read aloud",
    rate: float = 0.95,
    height: int = 62,
    key: str = "tts",
) -> None:
    """Render a read-aloud button for ``text``."""
    if not text or not text.strip():
        return
    html = (
        _TEMPLATE
        .replace("__TEXT__", json.dumps(text))
        .replace("__RATE__", str(float(rate)))
        .replace("__LABEL__", label)
        .replace("__ID__", f"{key}_")
    )
    st.iframe(html, height=height)
