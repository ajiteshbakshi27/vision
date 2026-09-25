"""Canned content used when no Google AI Studio key is configured.

Lets the prototype be demoed end-to-end offline while making it obvious that
the response is simulated rather than generated.
"""

from __future__ import annotations

DEMO_BANNER = (
    "> **Simulated response.** No Google AI Studio key is configured, so this is "
    "a canned example of the format. Add `GEMINI_API_KEY` to `.env` for live "
    "Gemini output."
)

#: Same idea, naming the variable the quick-alert function actually reads.
DEMO_BANNER_QUICK = (
    "> **Simulated response.** No API key is configured, so this is a canned "
    "example of the format. Add `GEMINI_API_KEY` to `.env` and restart the app "
    "for live Gemini output."
)

DEMO_VISION_REPORT = """\
### What I can see

A pedestrian walkway photographed at roughly eye level. The path surface is
intact paving with a raised kerb line running along the left-hand side. No
dropped kerb is visible within the frame. A build hoarding stands across the
right-hand third of the walkway, with a mesh fence panel above it.

### Obstacle

Construction hoarding narrowing the walkway. A bright yellow temporary sign is
attached at handrail height, so it is detectable by cane. Behind the hoarding
the ground appears to be broken ground / trench spoil rather than paving.

### Wheelchair impact

The clear gap between the hoarding and the left kerb looks to be roughly
**0.9–1.1 m**, which is below the 1.2 m needed to pass a standard wheelchair
comfortably and well below the 1.5 m turning circle. A manual chair would need
to be angled through the gap, and reversing out would be required if the user
overshoots.

### Tactile & trip hazards

- No tactile warning surface is present at the hoarding line.
- The sign board is at 1.0 m height, inside cane range.
- A trailing cable is visible at ground level crossing the approach, which is a
  trip hazard and will be missed by a white cane.
- The kerb on the left is unbroken for the length of the frame — a full drop.

### Recommended action

**Use an alternate route.** Do not attempt this walkway. The hoarding appears
fully closed to the right of the sign; the left-hand gap is too narrow to be
relied upon. Turn back, keep to the tactile guide strip if one is present, and
follow the signed diversion.

### Uncertainty

I cannot see past the hoarding, so I cannot confirm whether the walkway
reopens beyond it or how wide the gap actually is. Perspective compression in a
wide-angle photo tends to *overstate* clear width, so treat 0.9 m as an upper
bound. Please have someone on site measure it before it is used as a route.

```json
{
  "obstacle_type": "construction",
  "severity": "blocked",
  "wheelchair_passable": false,
  "clear_width_m": 1.0,
  "estimated_gradient_pct": null,
  "tactile_hazard": true,
  "summary": "Construction hoarding narrows the walkway to about one metre and a loose cable crosses the approach; treat the path as blocked and turn back.",
  "recommended_action": "use_alternate_route",
  "detour_hint": "Return to the previous junction and follow the signed diversion away from the hoarding.",
  "confidence": 0.62
}
```
"""

#: Canned answers for follow-up questions when no API key is configured.
#: Canned stand-in for the 2-sentence quick hazard alert, matching the length
#: and audio-friendly register the live prompt asks Gemini for.
DEMO_QUICK_ALERT = (
    "Alert: construction hoarding blocks the right-hand side of this walkway and "
    "the gap to the left kerb looks about one metre wide, too narrow for a "
    "wheelchair. "
    "Turn back and use the signed diversion; there is no dropped kerb and a loose "
    "cable crosses the approach."
)

DEMO_ASSISTANT_REPLIES: tuple[str, ...] = (
    "I would not rely on that lift. The step-free alternative on this campus is the "
    "Library South Ramp from Central Plaza, which is a 1 in 12.5 gradient with "
    "handrails on both sides and a level landing at the top. It adds about 90 "
    "metres. If the ramp is out as well, the northern stair between the library and "
    "the Science Centre is the only other connection, and that one has eighteen "
    "risers with no step-free option.",
    "There is an all-gender accessible restroom in the Student Union concourse, "
    "level 1, immediately on your right as you come out of the main doors. It has "
    "grab rails on both sides, a drop-down rail, a 1500 millimetre turning circle, "
    "and both an alarm pull cord and a vibrating pad. No key is needed, but the "
    "door is heavy, so expect a second push.",
    "The nearest step-free route to the Science Centre leaves you at the Union and "
    "uses the second lift on your right as you come out of the concourse. It is 620 "
    "metres, roughly nine minutes, and crosses two roads. The northern stair "
    "between the library and the Science Centre is faster but has eighteen risers "
    "and no step-free alternative, so I have not used it.",
)
