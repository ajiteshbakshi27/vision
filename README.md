# Urban Accessibility & Tactile Navigation Assistant

A Streamlit prototype for **Project A**. It combines an interactive campus
accessibility map, Gemini Vision obstacle checking, and a voice-style route
assistant — all three tuned for people who navigate by wheelchair, white cane,
or who are blind or have low vision.

> **Prototype / sample data.** Every building, gradient, elevator dimension and
> hazard report in this project is fictional and exists only to demonstrate the
> interface. Do not use it for real navigation or mobility decisions.

---

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

Add your key (optional — the app runs fully without one, in demo mode):

```bash
# edit .env
GEMINI_API_KEY=your_google_ai_studio_key_here
```

Then:

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501>.

---

## Layout

```
.
├── app.py                          # Streamlit entry point — all three sections
├── .env                            # Google AI Studio key (git-ignored)
├── requirements.txt
├── .streamlit/config.toml          # base theme
├── components/
│   └── campus_map/                 # bidirectional custom component
│       ├── index.html              #   the SVG map, rendered in an iframe
│       └── streamlit-shim.js       #   minimal self-hosted component runtime
└── src/
    ├── settings.py                 # env loading, API-key lookup, constants
    ├── campus_data.py              # mock campus graph: places, edges, features
    ├── routing.py                  # accessibility-aware Dijkstra + instructions
    ├── assistant.py                # spoken-command intent parsing
    ├── gemini.py                   # Google AI Studio client (both SDKs)
    ├── demo_content.py             # canned responses for offline demo mode
    ├── sample_image.py             # synthetic test photo generator
    ├── speech.py                   # read-aloud button (Web Speech API)
    └── styles.py                   # CSS: top nav, cards, accessibility themes
```

---

## The three sections

### 1. Interactive campus map

A self-contained SVG map rendered in a Streamlit custom component — no tile
server, no map API key, works offline.

- **Clickable pins** for accessible paths/ramps, elevators, tactile paving,
  accessible restrooms, accessible drop-off bays, and reported hazards
  (stairs without a ramp, construction, missing tactile paving).
- **Clickable paths.** Walkways, stairs and elevators are all clickable and
  report length, surface, clear width, gradient, crossings and lighting.
- **Route highlighting.** A route planned in section 3 is drawn in purple
  across the map with `A`/`B` end caps.
- **Pan, zoom and reset** via mouse wheel, drag, or the toolbar. Arrow keys pan
  the map; `0` resets the view.
- **Keyboard and screen-reader support.** Every pin is a focusable `role="button"`
  with an `aria-label`, activation works with <kbd>Enter</kbd>/<kbd>Space</kbd>,
  and the whole map is mirrored by the *Accessible feature list* panel — native
  Streamlit buttons that do the same thing without a pointer.

### 2. Check Obstacle via Gemini Vision

Upload a photo, use the camera, or generate a synthetic test image. Two actions:

- **Quick hazard alert (2 sentences)** — calls
  `check_accessibility_hazards()` in `app.py` with
  `google.generativeai` and `HAZARD_PROMPT`, and shows the returned text in a
  large alert card with a read-aloud button. The function:
  1. reads `GEMINI_API_KEY` from the environment (falling back to
     `GOOGLE_API_KEY` / `GOOGLE_AI_STUDIO_API_KEY`),
  2. sends the image to `HAZARD_MODEL` (`gemini-1.5-flash`) as a
     prompt-plus-image pair,
  3. returns a `HazardAlert` instead of raising, so a missing key, bad key,
     quota or network failure all surface as a readable message.
- **Full accessibility report** — the longer structured analysis. You supply
  context (where, which level, what to focus on) and get what the model can see,
  the obstacle, the wheelchair impact, tactile and trip hazards, a recommended
  action, and an explicit *uncertainty* section. A fenced JSON block is parsed
  out to drive the severity / passability / clear-width tiles.

If no API key is set, both fall back to clearly-labelled built-in text, so the
whole flow is demonstrable offline.

#### A note on `gemini-1.5-flash`

The requested model is hard-coded as `HAZARD_MODEL = "gemini-1.5-flash"`, but
**Google has shut down the entire Gemini 1.5 family** — the current lineup is
Gemini 3.x Flash plus 2.5. A live key will therefore get a 404 on that name.

Rather than ship a function that only ever errors, the call walks
`HAZARD_MODEL_FALLBACKS` (`gemini-2.5-flash`, then `gemini-2.0-flash`) when the
API reports the model as missing, and the UI says so explicitly:

> `gemini-1.5-flash` is no longer served by the Gemini API, so this answer came
> from `gemini-2.5-flash` instead.

Only "model not found" errors trigger the walk. A bad key, quota or network
error stops immediately, since those would fail identically on every model.

To pin a specific model, set `HAZARD_MODEL` at the top of `app.py`. Also note
that `google-generativeai` now prints a `FutureWarning` on import — the package
is end-of-life in favour of `google-genai`, which `src/gemini.py` prefers.

### 3. Voice assistant

A text box (placeholder: *"Take me to Library via ramp"*) that simulates hearing
a spoken request, plus quick-phrase chips and a phrase picker for demoing.

- **Intent parsing** is rule-based, so it works offline: destination, origin,
  `via` waypoints, `via ramp`, `via elevator`, `avoid stairs / construction /
  steep slopes`, `prefer tactile paving`.
- **Routing** is a Dijkstra search over the campus graph, weighted by the
  accessibility preferences from the sidebar. If the strict preferences yield
  nothing, constraints are relaxed one at a time and the app reports *exactly*
  which preference it had to give up.
- **Output** is distance, time, steepest gradient, narrowest width, elevator and
  crossing counts, turn-by-turn steps, and spoken guidance with a read-aloud
  button. Gemini polishes the wording when a key is present; without one, the
  app narrates the route it actually computed, so the spoken text can never
  contradict the numbers on screen.

---

## Sidebar settings

| Setting | Effect |
| --- | --- |
| **Campus** | Sample campus selector |
| **Model** | Gemini model for vision and narration |
| **Mobility profile** | Six presets (manual / power wheelchair, white cane, low vision, stroller, stairs acceptable) that set the routing preferences |
| **Fine-tune preferences** | Step-free only, avoid stairs, avoid construction, prefer tactile, prefer ramps, avoid elevators, max gradient, min clear width |
| **Text size** | Standard / Large / Extra Large (115% / 130% root scale) |
| **High contrast** | Black on white, heavier borders, strong focus rings |
| **Reduce motion** | Disables transitions and animation |
| **Offer read-aloud** | Shows the Web Speech API read-aloud button |

---

## Google AI Studio setup

1. Create a key at <https://aistudio.google.com/apikey>.
2. Put it in `.env` as `GEMINI_API_KEY=...`. `GOOGLE_API_KEY` and
   `GOOGLE_AI_STUDIO_API_KEY` are also accepted.
3. Restart the app.

The client prefers the current `google-genai` SDK and falls back to the legacy
`google-generativeai` package. Every call is non-fatal — a missing key, a
missing SDK, a quota error or an empty response all degrade to a friendly
message or the demo content rather than a traceback.

---

## Notes and limitations

- The custom component vendors its own four-message Streamlit runtime shim
  (`components/campus_map/streamlit-shim.js`) because the npm
  `streamlit-component-lib` package no longer publishes a browser bundle.
  Nothing is loaded from a CDN at runtime.
- `via` waypoints are enforced by running the search leg-by-leg rather than as a
  single constrained path, so a route can chain two lifts to satisfy a waypoint.
  A full multi-constraint search would be the next step.
- Spoken narration is generated by the Web Speech API, so it uses the voices
  installed in the user's browser rather than a cloud TTS service.
- The synthetic test image is a flat illustration, not a photograph. It exists to
  exercise the image pipeline when no photo is to hand.
