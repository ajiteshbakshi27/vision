"""Campus dataset for JIIT Noida Sector 62: buildings, walkways, vertical links and features.

Everything lives on a single ``1000 x 640`` canvas so the SVG
renderer and the router share one set of coordinates and accessibility attributes.
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
    """A walkable connection between two places."""

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
# Places (JIIT Sector 62 Layout)
# --------------------------------------------------------------------------

PLACES: tuple[Place, ...] = (
    Place("GATE1", "Main Gate 1", 110, 545, 130, 80,
          aliases=("gate 1", "main gate", "entrance", "entry", "front gate")),
    Place("GATE2", "Gate 2 (Side Entry)", 105, 335, 120, 70,
          aliases=("gate 2", "back gate", "side gate")),
    Place("HOSTELS", "Hostel Complex (H1-H4)", 110, 135, 140, 95,
          aliases=("hostel", "hostels", "h1", "h2", "h3", "h4", "residence")),
    Place("SPORTS", "Sports Complex & Ground", 350, 130, 200, 130,
          aliases=("sports", "ground", "basketball court", "badminton")),
    Place("QUAD", "Central Lawns", 380, 295, 75, 55, kind="open",
          aliases=("lawns", "green lawn", "quad")),
    Place("LRC", "Learning Resource Centre (LRC)", 580, 135, 180, 125, level="L2",
          aliases=("lrc", "library", "books", "reading hall")),
    Place("ABB1", "ABB I (Academic Block B1)", 840, 135, 190, 130, level="L2",
          aliases=("abb1", "abb 1", "academic block 1", "cs labs")),
    Place("PLAZA", "Central Plaza", 575, 240, 110, 70, kind="open",
          aliases=("plaza", "amphitheatre", "fountain")),
    Place("ANNAPURNA", "Annapurna (Cafeteria)", 265, 360, 145, 100,
          aliases=("annapurna", "canteen", "cafeteria", "dining", "food court")),
    Place("ABB2", "ABB II (Academic Block B2)", 575, 345, 190, 130,
          aliases=("abb2", "abb 2", "academic block 2", "ece labs")),
    Place("DISPENSARY", "Medical Dispensary", 855, 345, 150, 105,
          aliases=("dispensary", "clinic", "health", "infirmary", "medical")),
    Place("JBS", "Jaypee Business School (JBS)", 345, 530, 190, 120, level="L2",
          aliases=("jbs", "business school", "management")),
    Place("ADMIN", "Administrative Block", 630, 530, 175, 115, level="L2",
          aliases=("admin", "accounts", "registrar", "office")),
    Place("GARDEN", "Herbal Garden", 855, 530, 130, 90, kind="green",
          aliases=("garden", "herbal garden", "park")),
)

PLACE_BY_ID: dict[str, Place] = {p.id: p for p in PLACES}

# --------------------------------------------------------------------------
# Edges
# --------------------------------------------------------------------------

EDGES: tuple[Edge, ...] = (
    # --- Ground level, level walking ---
    Edge("e1", "GATE1", "ANNAPURNA",
         ((110, 545), (200, 480), (265, 410)),
         150, True, "concrete paving", 2.4, "Gate 1 Main Pathway",
         gradient_pct=3.0, tactile="guidance", crossings=1,
         note="Tactile strip leads from Gate 1 directly towards Annapurna Canteen."),
    Edge("e2", "GATE1", "JBS",
         ((110, 545), (230, 560), (345, 530)),
         170, True, "asphalt", 3.0, "JBS Walkway",
         gradient_pct=2.0, tactile="none"),
    Edge("e3", "GATE1", "GATE2",
         ((110, 545), (125, 440), (105, 335)),
         215, True, "asphalt", 2.2, "Perimeter Drive",
         gradient_pct=4.0, tactile="warning", crossings=2, lighting="poor"),
    Edge("e4", "GATE2", "ANNAPURNA",
         ((105, 335), (185, 348), (265, 360)),
         175, True, "concrete paving", 2.6, "Gate 2 Canteen Link",
         gradient_pct=2.0, tactile="none"),
    Edge("e5", "GATE2", "HOSTELS",
         ((105, 335), (85, 235), (110, 135)),
         205, True, "asphalt", 2.4, "Hostel Road",
         gradient_pct=5.0, tactile="none", lighting="poor"),
    Edge("e6", "HOSTELS", "SPORTS",
         ((110, 135), (230, 120), (350, 130)),
         240, True, "asphalt", 3.2, "Sports Walk",
         gradient_pct=2.0, tactile="none"),
    Edge("e8", "ANNAPURNA", "QUAD",
         ((265, 360), (325, 330), (380, 295)),
         95, True, "brick pavers", 2.0, "Lawn Approach",
         gradient_pct=2.0, tactile="none"),
    Edge("e9", "ANNAPURNA", "ABB2",
         ((265, 360), (420, 355), (575, 345)),
         300, True, "concrete paving", 2.8, "Academic Walk",
         gradient_pct=1.0, tactile="guidance", crossings=2,
         note="Tactile guide strip leads directly to ABB II main foyer."),
    Edge("e10", "QUAD", "SPORTS",
         ((380, 295), (368, 215), (350, 130)),
         170, True, "concrete paving", 2.4, "Sports Ground Ramp",
         gradient_pct=6.0, tactile="none"),
    Edge("e11", "QUAD", "PLAZA",
         ((380, 295), (470, 265), (575, 240)),
         275, True, "stone pavers", 3.0, "Central Concourse",
         gradient_pct=3.0, tactile="guidance"),
    Edge("e12", "SPORTS", "LRC",
         ((350, 130), (465, 125), (580, 135)),
         230, True, "concrete paving", 2.6, "LRC North Walk",
         gradient_pct=2.0, tactile="warning"),
    Edge("e13", "LRC", "PLAZA",
         ((580, 135), (580, 190), (575, 240)),
         72, True, "tactile pavers", 2.0, "LRC Access Ramp",
         gradient_pct=8.0, tactile="guidance",
         note="Wheelchair ramp connecting Plaza level to LRC main portal."),
    Edge("e14", "PLAZA", "ABB1",
         ((575, 240), (720, 215), (840, 135)),
         275, True, "concrete paving", 2.4, "ABB I Link",
         gradient_pct=3.0, tactile="guidance"),
    Edge("e15", "PLAZA", "ABB2",
         ((575, 240), (575, 300), (575, 345)),
         140, True, "granite setts", 3.4, "ABB II Foyer Approach",
         gradient_pct=2.0, tactile="guidance"),
    Edge("e16", "ABB1", "DISPENSARY",
         ((840, 135), (862, 240), (855, 345)),
         215, True, "asphalt", 2.2, "Dispensary Lane",
         gradient_pct=3.0, tactile="warning", lighting="poor"),
    Edge("e17", "DISPENSARY", "ADMIN",
         ((855, 345), (830, 440), (760, 510), (630, 530)),
         340, True, "concrete paving", 2.4, "Admin East Path",
         gradient_pct=4.0, tactile="none"),
    Edge("e18", "ADMIN", "GARDEN",
         ((630, 530), (740, 560), (855, 530)),
         240, True, "asphalt", 2.0, "Garden Promenade",
         gradient_pct=3.0, tactile="none"),
    Edge("e19", "ABB2", "DISPENSARY",
         ((575, 345), (715, 350), (855, 345)),
         280, True, "concrete paving", 2.6, "Health Link",
         gradient_pct=2.0, tactile="none"),
    Edge("e21", "ABB2", "ADMIN",
         ((575, 345), (600, 440), (630, 530)),
         195, True, "concrete paving", 2.0, "Admin Walk",
         gradient_pct=5.0, tactile="none"),

    # --- Step-free vertical links (elevators) ---
    Edge("e24", "ABB2", "LRC",
         ((460, 175), (460, 215)),
         40, True, "elevator", 1.1, "ABB II–LRC Central Elevator (L1↔L2)",
         gradient_pct=0.0, style="elevator",
         note="Car 1.4 m × 1.6 m, braille buttons and voice floor announcements."),
    Edge("e26", "ABB2", "ABB1",
         ((695, 210), (695, 250)),
         45, True, "elevator", 1.1, "ABB I North Elevator (L1↔L2)",
         gradient_pct=0.0, style="elevator",
         note="Elevator serving CS & IT laboratories on upper floors."),

    # --- Stairs only, no step-free alternative ---
    Edge("e7", "HOSTELS", "QUAD",
         ((110, 135), (150, 220), (300, 285), (380, 295)),
         320, False, "steps (14 risers)", 1.2, "Hostel Direct Staircase to Quad",
         style="stairs", hazard="stairs", tactile="none",
         note="Stairs without ramp option. Wheelchair users follow Gate 2 road."),
    Edge("e20", "JBS", "QUAD",
         ((345, 530), (368, 420), (380, 295)),
         230, False, "steps (22 risers)", 1.2, "JBS Lawns Staircase",
         style="stairs", hazard="stairs", tactile="none"),
    Edge("e23", "LRC", "ABB1",
         ((580, 135), (710, 120), (840, 135)),
         260, False, "steps (18 risers)", 1.5, "LRC to ABB I Bridge Staircase",
         style="stairs", hazard="stairs", tactile="none"),
    Edge("e28", "ABB2", "LRC",
         ((498, 225), (516, 262)),
         35, False, "steps (11 risers)", 1.2, "ABB II Outer Steps to LRC",
         style="stairs", hazard="stairs", tactile="none"),
    Edge("e29", "ABB2", "ABB1",
         ((762, 220), (778, 258)),
         38, False, "steps (9 risers)", 1.2, "ABB Interconnecting Steps",
         style="stairs", hazard="stairs", tactile="none"),

    # --- Closed for construction ---
    Edge("e22", "ANNAPURNA", "JBS",
         ((265, 360), (300, 440), (345, 530)),
         200, True, "brick pavers", 1.8, "Annapurna–JBS Covered Walkway",
         gradient_pct=4.0, style="construction", closed=True,
         hazard="construction", tactile="none", lighting="poor",
         note="Closed for underground maintenance. Detour via ABB II foyer."),
)

EDGE_BY_ID: dict[str, Edge] = {e.id: e for e in EDGES}

# --------------------------------------------------------------------------
# Features (map pins for JIIT Sector 62)
# --------------------------------------------------------------------------

FEATURES: tuple[Feature, ...] = (
    # Accessible paths / ramps
    Feature("R1", "path", "Gate 1 Entrance Ramp", 200, 480,
            description="1:14 gentle ramp with continuous handrails at JIIT Gate 1.",
            edge_ids=("e1",),
            attrs={"Gradient": "1:14 (7.1%)", "Clear width": "1.8 m",
                   "Handrails": "Both sides", "Resting points": "1"}),
    Feature("R2", "path", "LRC Main Entrance Ramp", 580, 215,
            level="L2",
            description="Step-free wheelchair ramp leading into Learning Resource Centre.",
            edge_ids=("e13",),
            attrs={"Gradient": "1:12.5 (8.0%)", "Clear width": "2.0 m",
                   "Handrails": "Both sides", "Resting points": "1 (top)"}),
    Feature("R3", "path", "JBS North Ramp", 230, 560,
            level="L2",
            description="Step-free entry to Jaypee Business School ground floor.",
            edge_ids=("e2",),
            attrs={"Gradient": "1:20 (5.0%)", "Clear width": "2.4 m",
                   "Handrails": "One side", "Intercom": "Yes"}),

    # Elevators
    Feature("E1", "elevator", "ABB II Central Elevator", 460, 195, level="L1/L2",
            description="Main passenger lift in ABB II connecting ground floor to upper lecture halls and LRC.",
            edge_ids=("e24",),
            attrs={"Car size": "1.4 m × 1.6 m", "Capacity": "1100 kg / 13 persons",
                   "Announcements": "Braille + audible", "Outages": "None recorded"}),
    Feature("E2", "elevator", "ABB I North Elevator", 695, 230, level="L1/L2",
            description="Elevator serving CS & IT Computer Labs in ABB I.",
            edge_ids=("e26",),
            attrs={"Car size": "1.1 m × 1.4 m", "Capacity": "1000 kg / 10 persons",
                   "Announcements": "Braille + audible", "Hold-open": "L1 landing"}),

    # Tactile paving
    Feature("T1", "tactile", "Tactile strip: Gate 1 → ABB II", 420, 355,
            description="Directional guidance tiles installed from Gate 1 entrance to Academic Block II.",
            edge_ids=("e9",),
            attrs={"Type": "Directional (truncated domes)",
                   "Colour": "Yellow on concrete", "Length": "300 m",
                   "Interruptions": "1 crossing"}),

    # Accessible restrooms
    Feature("A1", "restroom", "Accessible Restroom, ABB II Ground Floor", 620, 385,
            description="Wheelchair accessible restroom near ABB II main reception with emergency alarm.",
            edge_ids=("e15",),
            attrs={"Door clear width": "950 mm", "Turning circle": "1500 mm",
                   "Grab rails": "Both sides", "Alarm": "Pull cord"}),
    Feature("A2", "restroom", "Accessible Restroom, LRC L2", 880, 155, level="L2",
            description="Accessible cubicle on LRC second level beside the digital library.",
            edge_ids=("e26",),
            attrs={"Door clear width": "900 mm", "Turning circle": "1500 mm",
                   "Grab rails": "Both sides", "Entry": "Keypad"}),

    # Accessible drop-off
    Feature("P1", "parking", "Accessible Drop-off Bay, Gate 1", 150, 570,
            description="Dedicated drop-off zone with dropped kerb right at Gate 1.",
            edge_ids=("e2",),
            attrs={"Transfer side": "Kerb (left)", "Clear length": "6.0 m",
                   "Time limit": "5 minutes", "Shelter": "Yes"}),

    # Hazards
    Feature("H1", "hazard", "Stairs: Hostel Road to Central Lawns", 150, 220,
            status="closed", category="stairs", reported_by="JIIT Access Panel",
            updated="Reported 2 days ago",
            description="14 steep steps without a ramp alternative. Barrier for wheelchair users.",
            edge_ids=("e7",),
            attrs={"Risers": "14", "Handrail": "One side only",
                   "Alternative": "Use Gate 2 road detour", "Severity": "Barrier"}),
    Feature("H2", "hazard", "Maintenance: Annapurna to JBS Walkway", 300, 440,
            status="closed", category="construction", reported_by="Estate Office",
            updated="Reported yesterday",
            description="Underground pipe repair blocks the pathway. Detour signed via ABB II foyer.",
            edge_ids=("e22",),
            attrs={"Clear width": "0.8 m", "Gradient": "8%",
                   "Detour": "+150 m via ABB II", "Expected": "4 days"}),
    Feature("H3", "hazard", "Damaged Tactile Paving: Dispensary Approach", 862, 240,
            status="caution", category="maintenance", reported_by="Student Report",
            updated="Reported 3 days ago",
            description="Loose tiles near the Dispensary entry. Exercise caution in low light.",
            edge_ids=("e16",),
            attrs={"Missing": "Hazard tiles ~4 m",
                   "Lighting": "Poor after dusk",
                   "Alternative": "Use Health Link via ABB II"}),
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
