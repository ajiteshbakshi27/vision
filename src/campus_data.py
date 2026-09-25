"""Mock campus dataset: buildings, walkways, vertical links and features.

Everything lives on a single ``1000 x 640`` "map unit" canvas so the SVG
renderer (custom component) and the router (Dijkstra) share one set of
coordinates and one set of accessibility attributes.

All data in this module is fictional and exists only to drive the prototype.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

MAP_WIDTH = 1000
MAP_HEIGHT = 640

# --------------------------------------------------------------------------
# Feature taxonomy
# --------------------------------------------------------------------------

#: Display metadata per feature kind, keyed by kind.
FEATURE_META: dict[str, dict[str, str]] = {
    "path": {
        "label": "Accessible path / ramp",
        "glyph": "♿",
        "color": "#0F766E",
        "description": "Step-free surface, handrails and a compliant gradient.",
    },
    "elevator": {
        "label": "Elevator",
        "glyph": "⇅",
        "color": "#1D4ED8",
        "description": "Lift linking two levels. Car size, load and announcements noted.",
    },
    "tactile": {
        "label": "Tactile paving",
        "glyph": "≡",
        "color": "#7C3AED",
        "description": "Guidance strips, warning surfaces and textured floor indicators.",
    },
    "restroom": {
        "label": "Accessible restroom",
        "glyph": "WC",
        "color": "#0891B2",
        "description": "All-gender cubicle with grab rails, 900 mm turning circle and alarm.",
    },
    "parking": {
        "label": "Accessible bay / drop-off",
        "glyph": "P",
        "color": "#B45309",
        "description": "Step-free parking bay or kerbside drop-off with boarding space.",
    },
    "hazard": {
        "label": "Reported hazard",
        "glyph": "!",
        "color": "#DC2626",
        "description": "Stairs without a ramp, construction or a surface fault.",
    },
}

#: Sub-categories used for hazard reporting.
HAZARD_CATEGORIES = {
    "stairs": "Stairs without step-free alternative",
    "construction": "Construction / path closed",
    "maintenance": "Surface or equipment fault",
    "surface": "Damaged paving",
}

STATUS_LABELS = {
    "open": "Open / usable",
    "caution": "Usable with caution",
    "closed": "Closed",
    "outage": "Out of service",
}

# --------------------------------------------------------------------------
# Dataclasses
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Place:
    """A building or open area on the map."""

    id: str
    name: str
    x: float
    y: float
    w: float
    h: float
    kind: str = "building"  # building | open | green
    level: str = "L1"
    aliases: tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Edge:
    """A walkable connection between two places.

    ``style`` drives how the renderer draws it:

    * ``walk``         - ordinary polyline through ``points``
    * ``elevator``     - vertical link, drawn as a dashed lift shaft
    * ``stairs``       - vertical link, drawn as a stepped run
    * ``construction`` - closed segment, drawn dashed and red
    """

    id: str
    a: str
    b: str
    points: tuple[tuple[float, float], ...]
    length_m: float
    step_free: bool
    surface: str
    width_m: float
    name: str
    gradient_pct: float | None = None
    style: str = "walk"
    closed: bool = False
    hazard: str | None = None  # hazard category when this edge is impaired
    tactile: str = "none"  # none | guidance | warning
    crossings: int = 0
    lighting: str = "good"  # good | poor | none
    note: str = ""

    def other(self, place_id: str) -> str:
        return self.b if place_id == self.a else self.a

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["points"] = [list(p) for p in self.points]
        return data


@dataclass(frozen=True)
class Feature:
    """A clickable pin on the map."""

    id: str
    kind: str
    name: str
    x: float
    y: float
    level: str = "L1"
    status: str = "open"
    description: str = ""
    category: str | None = None
    edge_ids: tuple[str, ...] = ()
    reported_by: str = ""
    updated: str = ""
    attrs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["edge_ids"] = list(self.edge_ids)
        data["meta"] = FEATURE_META.get(self.kind, {})
        return data


# --------------------------------------------------------------------------
# Places
# --------------------------------------------------------------------------

PLACES: tuple[Place, ...] = (
    Place("MAIN_GATE", "Main Gate", 110, 545, 130, 80,
          aliases=("gate", "gates", "entrance", "entry", "front gate")),
    Place("TRANSIT", "Transit Stop", 105, 335, 120, 70,
          aliases=("bus", "bus stop", "train", "station", "transit")),
    Place("DORM", "Residence Village", 110, 135, 140, 95,
          aliases=("dorm", "dorms", "hostel", "residence", "halls", "student housing")),
    Place("STADIUM", "Riverside Stadium", 350, 130, 200, 130,
          aliases=("stadium", "arena", "gym", "sports")),
    Place("COURT", "The Quad", 380, 295, 75, 55, kind="open",
          aliases=("quad", "courtyard", "green")),
    Place("LIBRARY", "Main Library", 580, 135, 180, 125, level="L2",
          aliases=("library", "lib", "books", "reading room", "study")),
    Place("SCIENCE", "Science Centre", 840, 135, 190, 130, level="L2",
          aliases=("science", "sci", "labs", "laboratory", "chemistry")),
    Place("PLAZA", "Central Plaza", 575, 240, 110, 70, kind="open",
          aliases=("plaza", "square", "fountain")),
    Place("CAFETERIA", "Cafeteria", 265, 360, 145, 100,
          aliases=("cafeteria", "cafe", "caf", "food court", "dining", "canteen", "refectory")),
    Place("UNION", "Student Union", 575, 345, 190, 130,
          aliases=("union", "student union", "su", "hub")),
    Place("HEALTH", "Health Centre", 855, 345, 150, 105,
          aliases=("health", "clinic", "infirmary", "medical", "nurse")),
    Place("ENGINEERING", "Engineering Hall", 345, 530, 190, 120, level="L2",
          aliases=("engineering", "eng", "eng hall", "tech", "engineering hall")),
    Place("ADMIN", "Admin Building", 630, 530, 175, 115, level="L2",
          aliases=("admin", "administration", "registry", "registrar", "office")),
    Place("GREEN", "Campus Green", 855, 530, 130, 90, kind="green",
          aliases=("green", "park", "lawn", "garden")),
)

PLACE_BY_ID: dict[str, Place] = {p.id: p for p in PLACES}

# --------------------------------------------------------------------------
# Edges
# --------------------------------------------------------------------------

EDGES: tuple[Edge, ...] = (
    # --- Ground level, level walking ---
    Edge("e1", "MAIN_GATE", "CAFETERIA",
         ((110, 545), (200, 480), (265, 410)),
         150, True, "concrete paving", 2.4, "Gate forecourt walk",
         gradient_pct=3.0, tactile="guidance", crossings=1,
         note="Continuous tactile guide strip runs the length of this walk."),
    Edge("e2", "MAIN_GATE", "ENGINEERING",
         ((110, 545), (230, 560), (345, 530)),
         170, True, "asphalt", 3.0, "South promenade",
         gradient_pct=2.0, tactile="none"),
    Edge("e3", "MAIN_GATE", "TRANSIT",
         ((110, 545), (125, 440), (105, 335)),
         215, True, "asphalt", 2.2, "Arrival drive crossing",
         gradient_pct=4.0, tactile="warning", crossings=2, lighting="poor",
         note="Single dropped kerb on the north side only."),
    Edge("e4", "TRANSIT", "CAFETERIA",
         ((105, 335), (185, 348), (265, 360)),
         175, True, "concrete paving", 2.6, "Transit link",
         gradient_pct=2.0, tactile="none"),
    Edge("e5", "TRANSIT", "DORM",
         ((105, 335), (85, 235), (110, 135)),
         205, True, "asphalt", 2.4, "West walk",
         gradient_pct=5.0, tactile="none", lighting="poor"),
    Edge("e6", "DORM", "STADIUM",
         ((110, 135), (230, 120), (350, 130)),
         240, True, "asphalt", 3.2, "North promenade",
         gradient_pct=2.0, tactile="none"),
    Edge("e8", "CAFETERIA", "COURT",
         ((265, 360), (325, 330), (380, 295)),
         95, True, "brick pavers", 2.0, "Quad approach",
         gradient_pct=2.0, tactile="none"),
    Edge("e9", "CAFETERIA", "UNION",
         ((265, 360), (420, 355), (575, 345)),
         300, True, "concrete paving", 2.8, "Union Walk",
         gradient_pct=1.0, tactile="guidance", crossings=2,
         note="Tactile guide strip installed during the 2024 resurfacing."),
    Edge("e10", "COURT", "STADIUM",
         ((380, 295), (368, 215), (350, 130)),
         170, True, "concrete paving", 2.4, "Stadium ramp",
         gradient_pct=6.0, tactile="none",
         note="Long ramped climb, 1:16 average, handrails both sides."),
    Edge("e11", "COURT", "PLAZA",
         ((380, 295), (470, 265), (575, 240)),
         275, True, "stone pavers", 3.0, "Plaza approach",
         gradient_pct=3.0, tactile="guidance"),
    Edge("e12", "STADIUM", "LIBRARY",
         ((350, 130), (465, 125), (580, 135)),
         230, True, "concrete paving", 2.6, "Library Walk",
         gradient_pct=2.0, tactile="warning"),
    Edge("e13", "LIBRARY", "PLAZA",
         ((580, 135), (580, 190), (575, 240)),
         72, True, "tactile pavers", 2.0, "Library South Ramp",
         gradient_pct=8.0, tactile="guidance",
         note="Steepest compliant ramp on campus (1:12.5) with a level landing at the top."),
    Edge("e14", "PLAZA", "SCIENCE",
         ((575, 240), (720, 215), (840, 135)),
         275, True, "concrete paving", 2.4, "Science Walk",
         gradient_pct=3.0, tactile="guidance"),
    Edge("e15", "PLAZA", "UNION",
         ((575, 240), (575, 300), (575, 345)),
         140, True, "granite setts", 3.4, "Union Concourse",
         gradient_pct=2.0, tactile="guidance"),
    Edge("e16", "SCIENCE", "HEALTH",
         ((840, 135), (862, 240), (855, 345)),
         215, True, "asphalt", 2.2, "Health approach",
         gradient_pct=3.0, tactile="warning", lighting="poor"),
    Edge("e17", "HEALTH", "ADMIN",
         ((855, 345), (830, 440), (760, 510), (630, 530)),
         340, True, "concrete paving", 2.4, "East perimeter walk",
         gradient_pct=4.0, tactile="none"),
    Edge("e18", "ADMIN", "GREEN",
         ((630, 530), (740, 560), (855, 530)),
         240, True, "asphalt", 2.0, "Green walk",
         gradient_pct=3.0, tactile="none"),
    Edge("e19", "UNION", "HEALTH",
         ((575, 345), (715, 350), (855, 345)),
         280, True, "concrete paving", 2.6, "Health Link",
         gradient_pct=2.0, tactile="none"),
    Edge("e21", "UNION", "ADMIN",
         ((575, 345), (600, 440), (630, 530)),
         195, True, "concrete paving", 2.0, "Admin Walk",
         gradient_pct=5.0, tactile="none"),

    # --- Step-free vertical links (elevators) ---
    Edge("e24", "UNION", "LIBRARY",
         ((460, 175), (460, 215)),
         40, True, "elevator", 1.1, "Union–Library Elevator (L1↔L2)",
         gradient_pct=0.0, style="elevator",
         note="Car 1.4 m × 1.6 m, 1100 kg, braille and audible floor announcements."),
    Edge("e26", "UNION", "SCIENCE",
         ((695, 210), (695, 250)),
         45, True, "elevator", 1.1, "Union–Science Elevator (L1↔L2)",
         gradient_pct=0.0, style="elevator",
         note="Car 1.1 m × 1.4 m, 1000 kg. Hold-open button on the L1 landing."),

    # --- Stairs only, no step-free alternative ---
    Edge("e7", "DORM", "COURT",
         ((110, 135), (150, 220), (300, 285), (380, 295)),
         320, False, "steps (14 risers)", 1.2, "Dormitory Steps to the Quad",
         style="stairs", hazard="stairs", tactile="none",
         note="No ramp or lift alternative. Handrail on one side only."),
    Edge("e20", "ENGINEERING", "COURT",
         ((345, 530), (368, 420), (380, 295)),
         230, False, "steps (22 risers)", 1.2, "Engineering Stair to the Quad",
         style="stairs", hazard="stairs", tactile="none"),
    Edge("e23", "LIBRARY", "SCIENCE",
         ((580, 135), (710, 120), (840, 135)),
         260, False, "steps (18 risers)", 1.5, "North Interconnecting Stair",
         style="stairs", hazard="stairs", tactile="none"),
    Edge("e28", "UNION", "LIBRARY",
         ((498, 225), (516, 262)),
         35, False, "steps (11 risers)", 1.2, "Union–Library Stair",
         style="stairs", hazard="stairs", tactile="none",
         note="Short but steep; no handrail on the upper flight."),
    Edge("e29", "UNION", "SCIENCE",
         ((762, 220), (778, 258)),
         38, False, "steps (9 risers)", 1.2, "Union–Science Stair",
         style="stairs", hazard="stairs", tactile="none"),

    # --- Closed for construction ---
    Edge("e22", "CAFETERIA", "ENGINEERING",
         ((265, 360), (300, 440), (345, 530)),
         200, True, "brick pavers", 1.8, "Cafeteria–Engineering Walk",
         gradient_pct=4.0, style="construction", closed=True,
         hazard="construction", tactile="none", lighting="poor",
         note="Closed for utility works. Signed detour via the Union concourse."),
)

EDGE_BY_ID: dict[str, Edge] = {e.id: e for e in EDGES}

# --------------------------------------------------------------------------
# Features (map pins)
# --------------------------------------------------------------------------

FEATURES: tuple[Feature, ...] = (
    # Accessible paths / ramps
    Feature("R1", "path", "East Gate Ramp", 200, 480,
            description="1:14 ramp with twin handrails and a level landing; "
                        "replaces the 14-step entrance that used to face the gate.",
            edge_ids=("e1",),
            attrs={"Gradient": "1:14 (7.1%)", "Clear width": "1.8 m",
                   "Handrails": "Both sides", "Resting points": "1"}),
    Feature("R2", "path", "Library South Ramp", 580, 215,
            level="L2",
            description="Steepest compliant ramp on campus. Follow the tactile "
                        "guide strip up to the library's L2 entrance.",
            edge_ids=("e13",),
            attrs={"Gradient": "1:12.5 (8.0%)", "Clear width": "2.0 m",
                   "Handrails": "Both sides", "Resting points": "1 (top)"}),
    Feature("R3", "path", "Engineering North Ramp", 230, 560,
            level="L2",
            description="Step-free entrance to Engineering Hall from the south "
                        "promenade, bypassing the closed stair core.",
            edge_ids=("e2",),
            attrs={"Gradient": "1:20 (5.0%)", "Clear width": "2.4 m",
                   "Handrails": "One side", "Intercom": "Yes"}),

    # Elevators
    Feature("E1", "elevator", "Union–Library Elevator", 460, 195, level="L1/L2",
            description="Passenger lift inside the Union core. Connects the "
                        "concourse to the library's L2 reading level.",
            edge_ids=("e24",),
            attrs={"Car size": "1.4 m × 1.6 m", "Capacity": "1100 kg / 13 persons",
                   "Announcements": "Braille + audible", "Outages": "None recorded"}),
    Feature("E2", "elevator", "Union–Science Elevator", 695, 230, level="L1/L2",
            description="Lift to the Science Centre L2 teaching labs. "
                        "Narrowest car on campus — check your chair width.",
            edge_ids=("e26",),
            attrs={"Car size": "1.1 m × 1.4 m", "Capacity": "1000 kg / 10 persons",
                   "Announcements": "Braille + audible", "Hold-open": "L1 landing"}),

    # Tactile paving
    Feature("T1", "tactile", "Tactile guide strip: Gate → Union", 420, 355,
            description="Continuous directional tactile strip installed in the "
                        "2024 resurfacing. Follow the corduroy ribs north-east.",
            edge_ids=("e9",),
            attrs={"Type": "Directional (truncated domes)",
                   "Colour": "Buff on grey", "Length": "300 m",
                   "Interruptions": "2 crossings"}),
    Feature("T2", "tactile", "Tactile warning surface: Library Walk", 465, 125,
            level="L2",
            description="Hazard warning tiles mark the raised crossing between "
                        "the stadium and library approaches.",
            edge_ids=("e12",),
            attrs={"Type": "Hazard warning (domed)",
                   "Colour": "Yellow", "Width": "600 mm", "Crossings": "1"}),

    # Accessible restrooms
    Feature("A1", "restroom", "All-gender accessible restroom, Union", 620, 385,
            description="Left-hand cubicle on the L1 concourse. Alarm pull cord "
                        "plus a vibrating pad option.",
            edge_ids=("e15",),
            attrs={"Door clear width": "950 mm", "Turning circle": "1500 mm",
                   "Grab rails": "Both sides + drop-down", "Alarm": "Pull cord + pad"}),
    Feature("A2", "restroom", "Accessible restroom, Science L2", 880, 155, level="L2",
            description="Cubicle beside the L2 labs. Keypad entry — code held at "
                        "the porters' desk.",
            edge_ids=("e26",),
            attrs={"Door clear width": "900 mm", "Turning circle": "1500 mm",
                   "Grab rails": "Both sides", "Entry": "Keypad"}),

    # Accessible bays / drop-off
    Feature("P1", "parking", "Accessible drop-off, Main Gate", 150, 570,
            description="Kerbside boarding bay with a 1.5 m transfer side and "
                        "a dropped kerb. 3-minute time limit enforced.",
            edge_ids=("e2",),
            attrs={"Transfer side": "Kerb (left)", "Clear length": "6.0 m",
                   "Time limit": "3 minutes", "Shelter": "Yes"}),

    # Hazards
    Feature("H1", "hazard", "Stairs: Residence Village → Quad", 150, 220,
            status="closed", category="stairs", reported_by="Access Panel",
            updated="Reported 4 days ago",
            description="14 risers with a handrail on one side only and no ramp "
                        "or lift alternative. Not navigable in a wheelchair.",
            edge_ids=("e7",),
            attrs={"Risers": "14", "Handrail": "One side only",
                   "Alternative": "None", "Severity": "Barrier"}),
    Feature("H2", "hazard", "Construction: Cafeteria–Engineering closed", 300, 440,
            status="closed", category="construction", reported_by="Estates Office",
            updated="Reported 2 days ago",
            description="Utility works narrow the walk to 900 mm and the "
                        "gradient to 9%. Signed detour via the Union concourse.",
            edge_ids=("e22",),
            attrs={"Clear width": "0.9 m (was 1.8 m)", "Gradient": "9% (was 4%)",
                   "Detour": "+180 m via Student Union", "Expected": "3 weeks"}),
    Feature("H3", "hazard", "Tactile paving missing: Health approach", 862, 240,
            status="caution", category="maintenance", reported_by="Walkability Audit",
            updated="Reported 1 week ago",
            description="The warning tiles before the Health Centre crossing were "
                        "removed during resurfacing and not reinstated.",
            edge_ids=("e16",),
            attrs={"Missing": "Hazard warning tiles, ~6 m",
                   "Crossing": "Uncontrolled", "Lighting": "Poor after dusk",
                   "Alternative": "Use the Health Link via Union"}),
)

FEATURE_BY_ID: dict[str, Feature] = {f.id: f for f in FEATURES}


# --------------------------------------------------------------------------
# Lookup helpers
# --------------------------------------------------------------------------


def place_name(place_id: str) -> str:
    place = PLACE_BY_ID.get(place_id)
    return place.name if place else place_id


def all_place_labels() -> list[str]:
    return [p.name for p in PLACES]


def match_place(text: str) -> str | None:
    """Best-effort place lookup from free text (ids, names and aliases)."""
    if not text:
        return None
    needle = text.lower().strip()
    if needle in PLACE_BY_ID:
        return needle
    best: tuple[int, str] | None = None
    for place in PLACES:
        candidates = (place.id.lower().replace("_", " "), place.name.lower(), *place.aliases)
        for candidate in candidates:
            if not candidate:
                continue
            if candidate == needle:
                return place.id
            if candidate in needle:
                score = len(candidate)
                if best is None or score > best[0]:
                    best = (score, place.id)
    return best[1] if best else None


def features_for_edge(edge_id: str) -> list[Feature]:
    return [f for f in FEATURES if edge_id in f.edge_ids]


def hazards() -> Iterable[Feature]:
    return (f for f in FEATURES if f.kind == "hazard")
