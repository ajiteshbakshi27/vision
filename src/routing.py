"""Accessibility-aware routing over the mock campus graph.

Dijkstra with a cost function that reflects the user's mobility preferences
(step-free only, gradient limits, surface quality, construction avoidance,
tactile preference). If the strict preference set yields nothing, the solver
relaxes constraints one at a time and reports exactly what it had to give up.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Any

from .campus_data import (
    EDGE_BY_ID,
    EDGES,
    FEATURE_BY_ID,
    PLACE_BY_ID,
    Edge,
    Feature,
    features_for_edge,
    place_name,
)

# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------

ROUGH_SURFACES = {"gravel", "dirt", "cobbles", "grass", "mud"}
SMOOTH_SURFACES = {"concrete paving", "asphalt", "tactile pavers", "granite setts"}


def _build_adjacency() -> dict[str, list[tuple[str, Edge]]]:
    """``place_id -> [(neighbour_id, edge), ...]``, precomputed once.

    Every edge is registered against *both* of its endpoints so the search can
    only ever walk real connections.
    """
    adjacency: dict[str, list[tuple[str, Edge]]] = {pid: [] for pid in PLACE_BY_ID}
    for edge in EDGES:
        if edge.a in adjacency:
            adjacency[edge.a].append((edge.b, edge))
        if edge.b in adjacency:
            adjacency[edge.b].append((edge.a, edge))
    for links in adjacency.values():
        links.sort(key=lambda pair: pair[1].id)
    return adjacency


ADJACENCY = _build_adjacency()



@dataclass
class RoutePrefs:
    """Mobility preferences gathered from the sidebar."""

    step_free_only: bool = True
    avoid_construction: bool = True
    avoid_stairs: bool = True
    max_gradient_pct: float = 8.3
    min_clear_width_m: float = 1.2
    prefer_tactile: bool = False
    prefer_ramps: bool = False
    avoid_elevators: bool = False

    def label(self) -> str:
        bits: list[str] = []
        bits.append("step-free" if self.step_free_only else "stairs permitted")
        if self.max_gradient_pct < 8.3:
            bits.append(f"max {self.max_gradient_pct:g}% slope")
        if self.avoid_construction:
            bits.append("no construction")
        if self.prefer_tactile:
            bits.append("prefer tactile paving")
        if self.prefer_ramps:
            bits.append("prefer ramps")
        if self.min_clear_width_m > 1.2:
            bits.append(f"min {self.min_clear_width_m:g} m width")
        return ", ".join(bits)


#: Relaxations tried in order when no route satisfies the strict preferences,
#: ordered from least-bad to worst deviation from what the user asked for.
_RELAXATIONS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("allow an elevator instead of a ramp", {"avoid_elevators": False}),
    ("allow construction zones and closed walks", {"avoid_construction": False}),
    ("allow gradients above your limit", {"max_gradient_pct": 100.0}),
    ("allow narrower paths (minimum 0.8 m)", {"min_clear_width_m": 0.8}),
    ("allow stairs", {"step_free_only": False, "avoid_stairs": False,
                      "max_gradient_pct": 100.0}),
    ("ignore every restriction", {"avoid_construction": False,
                                  "max_gradient_pct": 100.0,
                                  "min_clear_width_m": 0.4,
                                  "step_free_only": False,
                                  "avoid_stairs": False,
                                  "avoid_elevators": False}),
)


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@dataclass
class RouteStep:
    """One instruction in the generated route."""

    order: int
    instruction: str
    detail: str
    distance_m: float
    cumulative_m: float
    surface: str
    gradient_pct: float | None
    width_m: float
    edge_id: str
    edge_name: str
    tactile: str
    crossings: int
    features: list[Feature] = field(default_factory=list)
    kind: str = "walk"  # walk | elevator | stairs

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "instruction": self.instruction,
            "detail": self.detail,
            "distance_m": self.distance_m,
            "cumulative_m": self.cumulative_m,
            "surface": self.surface,
            "gradient_pct": self.gradient_pct,
            "width_m": self.width_m,
            "edge_id": self.edge_id,
            "edge_name": self.edge_name,
            "tactile": self.tactile,
            "crossings": self.crossings,
            "kind": self.kind,
            "features": [f.id for f in self.features],
        }


@dataclass
class Route:
    origin: str
    destination: str
    steps: list[RouteStep]
    total_m: float
    cost: float
    edge_ids: list[str]
    prefs: RoutePrefs
    relaxations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ok: bool = True
    reason: str = ""

    @property
    def walking_minutes(self) -> int:
        return max(1, round(self.total_m / 70))

    @property
    def crossings(self) -> int:
        return sum(s.crossings for s in self.steps)

    @property
    def elevators(self) -> int:
        return sum(1 for s in self.steps if s.kind == "elevator")

    @property
    def stairs(self) -> int:
        return sum(1 for s in self.steps if s.kind == "stairs")

    @property
    def max_gradient(self) -> float:
        grads = [s.gradient_pct for s in self.steps if s.gradient_pct]
        return max(grads) if grads else 0.0

    @property
    def min_width(self) -> float:
        widths = [s.width_m for s in self.steps]
        return min(widths) if widths else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "total_m": self.total_m,
            "edge_ids": self.edge_ids,
            "prefs": self.prefs.label(),
            "relaxations": self.relaxations,
            "warnings": self.warnings,
            "ok": self.ok,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------
# Cost model
# --------------------------------------------------------------------------


def _blocked(edge: Edge, prefs: RoutePrefs) -> str | None:
    """Return a human reason if the edge is unusable under ``prefs``."""
    if edge.closed and prefs.avoid_construction:
        return "closed for construction"
    if not edge.step_free and prefs.step_free_only:
        return "stairs with no step-free alternative"
    if not edge.step_free and prefs.avoid_stairs:
        return "stairs"
    if (
        edge.step_free
        and edge.gradient_pct is not None
        and edge.gradient_pct > prefs.max_gradient_pct
    ):
        return f"gradient {edge.gradient_pct:g}% exceeds your {prefs.max_gradient_pct:g}% limit"
    if edge.width_m < prefs.min_clear_width_m:
        return f"clear width {edge.width_m:g} m is below {prefs.min_clear_width_m:g} m"
    if edge.style == "elevator" and prefs.avoid_elevators:
        return "you asked to avoid elevators"
    return None


def _cost(edge: Edge, prefs: RoutePrefs) -> float:
    """Heuristic traversal cost. Lower is better; roughly metres-weighted."""
    cost = float(edge.length_m)

    if edge.style == "elevator":
        # Vertical travel: short distance but a real wait for the car.
        return cost * 3.0 + 25.0
    if not edge.step_free:
        # Permitted, but strongly discouraged.
        return cost * 6.0 + 40.0
    if edge.closed:
        return cost * 4.0

    if edge.gradient_pct:
        cost += edge.length_m * (edge.gradient_pct / 12.0)
    if edge.surface in ROUGH_SURFACES:
        cost += edge.length_m * 0.5
    elif edge.surface == "brick pavers":
        cost += edge.length_m * 0.08
    if edge.lighting == "poor":
        cost += 15.0
    if edge.crossings:
        cost += edge.crossings * 12.0

    if prefs.prefer_tactile:
        if edge.tactile == "guidance":
            cost *= 0.75
        elif edge.tactile == "none":
            cost *= 1.15
    if prefs.prefer_ramps:
        if edge.surface == "tactile pavers" or edge.gradient_pct:
            cost *= 0.9
        if any(f.kind == "path" for f in features_for_edge(edge.id)):
            cost *= 0.85

    return max(cost, 1.0)


def _dijkstra(origin: str, destination: str, prefs: RoutePrefs,
              via: list[str] | None = None) -> tuple[float, list[str]] | None:
    """Least-cost path over the campus graph. ``via`` nodes are mandatory."""
    via = via or []
    stops = [origin, *via, destination]

    def leg(start: str, end: str) -> tuple[float, list[str]] | None:
        if start == end:
            return 0.0, []
        dist: dict[str, float] = {start: 0.0}
        prev: dict[str, tuple[str, str]] = {}
        seen: set[str] = set()
        queue: list[tuple[float, str]] = [(0.0, start)]

        while queue:
            cost, node = heapq.heappop(queue)
            if node in seen:
                continue
            seen.add(node)
            if node == end:
                break
            for nxt, edge in ADJACENCY.get(node, ()):
                if nxt in seen:
                    continue
                if _blocked(edge, prefs):
                    continue
                new_cost = cost + _cost(edge, prefs)
                if new_cost < dist.get(nxt, math.inf):
                    dist[nxt] = new_cost
                    prev[nxt] = (node, edge.id)
                    heapq.heappush(queue, (new_cost, nxt))

        if end not in dist:
            return None
        chain: list[str] = []
        cursor = end
        while cursor != start:
            parent, edge_id = prev[cursor]
            chain.append(edge_id)
            cursor = parent
        chain.reverse()
        return dist[end], chain

    total_cost = 0.0
    total_edges: list[str] = []
    for start, end in zip(stops, stops[1:]):
        result = leg(start, end)
        if result is None:
            return None
        leg_cost, leg_edges = result
        total_cost += leg_cost
        total_edges.extend(leg_edges)
    return total_cost, total_edges


# --------------------------------------------------------------------------
# Instruction generation
# --------------------------------------------------------------------------

_TURN_BANDS = (
    (22, "continue on"),
    (60, "bear left onto"),
    (135, "turn left onto"),
    (180, "sharp left onto"),
)

_TACTILE_TEXT = {
    "guidance": "Tactile guide strip runs alongside this section",
    "warning": "Tactile warning tiles mark the crossing",
    "none": "No tactile guidance on this section",
}


def _bearing(points: tuple[tuple[float, float], ...]) -> float:
    """Heading in degrees for the first meaningful leg of a polyline."""
    a, b = points[0], points[-1]
    return math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) % 360


def _turn_phrase(delta: float) -> str:
    if delta < 22 or delta > 338:
        return "Continue on"
    if 22 <= delta < 60:
        return "Bear right onto"
    if 60 <= delta < 135:
        return "Turn right onto"
    if 135 <= delta < 180:
        return "Sharp right onto"
    if 180 <= delta < 202:
        return "Turn back onto"
    if 202 <= delta < 280:
        return "Turn left onto"
    if 280 <= delta < 338:
        return "Bear left onto"
    return "Continue on"


def _describe_vertical(edge: Edge, direction: str) -> tuple[str, str, str]:
    if edge.style == "elevator":
        return (
            f"Take the {edge.name.split('(')[0].strip()}",
            "Wait for the car, then travel one level. Announcements are audible "
            "and in braille; the hold-open button is on the arrival landing.",
            "elevator",
        )
    return (
        f"Use {edge.name.split('(')[0].strip()} going {direction}",
        f"{edge.surface}. {edge.note or 'No step-free alternative is signed here.'}",
        "stairs",
    )


def _build_steps(origin: str, destination: str, edge_ids: list[str]) -> list[RouteStep]:
    steps: list[RouteStep] = []
    cursor = origin
    cumulative = 0.0
    previous_bearing: float | None = None

    for index, edge_id in enumerate(edge_ids, start=1):
        edge = EDGE_BY_ID[edge_id]
        if cursor not in (edge.a, edge.b):
            raise RuntimeError(
                f"route is not continuous: step {index} ({edge_id}) does not touch "
                f"{place_name(cursor)}"
            )
        nxt = edge.b if cursor == edge.a else edge.a
        ahead = place_name(nxt)
        bearing = _bearing(edge.points)
        turn = _turn_phrase((bearing - previous_bearing) % 360) if previous_bearing is not None else "Leave"
        previous_bearing = bearing
        cumulative += edge.length_m
        touched = features_for_edge(edge_id)

        if edge.style in ("elevator", "stairs"):
            head, detail, kind = _describe_vertical(edge, f"toward {ahead}")
            instruction = f"{head} to reach {ahead}."
        else:
            kind = "walk"
            verb = "Leave" if turn == "Leave" else turn
            instruction = f"{verb} {edge.name} toward {ahead} ({edge.length_m:g} m)."
            detail_bits = [
                f"{edge.surface}, {edge.width_m:g} m clear width",
                f"{edge.gradient_pct:g}% gradient" if edge.gradient_pct is not None else "flat",
            ]
            if edge.crossings:
                detail_bits.append(f"{edge.crossings} road crossing{'s' if edge.crossings > 1 else ''}")
            if edge.lighting == "poor":
                detail_bits.append("poor lighting — take care after dark")
            detail = "; ".join(detail_bits).capitalize() + "."
            if edge.closed:
                detail = "CLOSED. " + detail

        if edge.tactile in ("guidance", "warning"):
            detail = f"{detail} {_TACTILE_TEXT[edge.tactile].lower()}."

        for feature in touched:
            if feature.kind == "hazard":
                detail += f" ⚠ {feature.name}: {feature.description}"
            elif feature.kind in ("path", "tactile"):
                detail += f" ♿ {feature.name}."

        steps.append(
            RouteStep(
                order=index,
                instruction=instruction,
                detail=detail,
                distance_m=edge.length_m,
                cumulative_m=cumulative,
                surface=edge.surface,
                gradient_pct=edge.gradient_pct,
                width_m=edge.width_m,
                edge_id=edge_id,
                edge_name=edge.name,
                tactile=edge.tactile,
                crossings=edge.crossings,
                features=touched,
                kind=kind,
            )
        )
        cursor = nxt

    if cursor != destination:  # defensive; should not happen
        raise RuntimeError(f"route ended at {cursor}, expected {destination}")
    return steps


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def find_route(
    origin: str,
    destination: str,
    prefs: RoutePrefs | None = None,
    via: list[str] | None = None,
) -> Route:
    """Route ``origin`` to ``destination``, relaxing preferences if needed."""
    prefs = prefs or RoutePrefs()
    via = [v for v in (via or []) if v and v not in (origin, destination)]

    if origin not in PLACE_BY_ID:
        return Route(origin, destination, [], 0, 0, [], prefs, ok=False,
                     reason=f"Unknown starting point '{place_name(origin)}'.")
    if destination not in PLACE_BY_ID:
        return Route(origin, destination, [], 0, 0, [], prefs, ok=False,
                     reason=f"Unknown destination '{place_name(destination)}'.")

    working = RoutePrefs(**prefs.__dict__)
    original = RoutePrefs(**prefs.__dict__)

    for label, patch in (("", {}), *_RELAXATIONS):
        if patch:
            for key, value in patch.items():
                setattr(working, key, value)
        result = _dijkstra(origin, destination, working, via)
        if result is None:
            continue
        cost, edge_ids = result
        steps = _build_steps(origin, destination, edge_ids)
        return Route(
            origin=origin,
            destination=destination,
            steps=steps,
            total_m=sum(s.distance_m for s in steps),
            cost=cost,
            edge_ids=edge_ids,
            prefs=working,
            # Report only what this route genuinely needs, not every rung of the
            # search ladder it happened to climb.
            relaxations=_required_relaxations(steps, original),
            warnings=_warnings(steps, working),
        )

    return Route(
        origin=origin,
        destination=destination,
        steps=[],
        total_m=0,
        cost=0,
        edge_ids=[],
        prefs=working,
        relaxations=[],
        ok=False,
        reason=(
            f"No path found from {place_name(origin)} to {place_name(destination)}, "
            "even with every restriction lifted."
        ),
    )


#: Maps a `_blocked` reason onto the preference that has to be given up.
_RELAXATION_LABELS = (
    ("closed for construction", "allow construction zones and closed walks"),
    ("stairs with no step-free alternative", "allow stairs"),
    ("stairs", "allow stairs"),
    ("gradient", "allow a steeper gradient"),
    ("clear width", "allow narrower paths"),
    ("avoid elevators", "allow an elevator instead of a ramp"),
)


def _required_relaxations(steps: list[RouteStep], original: RoutePrefs) -> list[str]:
    """Which preferences the returned route actually breaks, in route order."""
    out: list[str] = []
    for step in steps:
        reason = _blocked(EDGE_BY_ID[step.edge_id], original)
        if not reason:
            continue
        for token, label in _RELAXATION_LABELS:
            if token in reason and label not in out:
                out.append(label)
                break
    return out


def _warnings(steps: list[RouteStep], prefs: RoutePrefs) -> list[str]:
    out: list[str] = []
    for step in steps:
        if step.kind == "stairs":
            out.append(f"Step {step.order} uses stairs ({step.surface}).")
        if step.features:
            for feature in step.features:
                if feature.kind == "hazard":
                    out.append(f"Step {step.order}: {feature.name} — {feature.description}")
    if any(s.gradient_pct and s.gradient_pct > 6.0 for s in steps):
        out.append("Route includes a climb steeper than 6%; consider the alternative if manual propulsion is difficult.")
    if any(s.tactile == "none" for s in steps) and prefs.prefer_tactile:
        out.append("Some sections have no tactile guidance despite your preference.")
    return out


def route_summary_text(route: Route) -> str:
    """Plain-text route briefing, used for the read-aloud panel."""
    if not route.ok:
        return f"Route unavailable. {route.reason}"
    lines = [
        f"Route from {place_name(route.origin)} to {place_name(route.destination)}. "
        f"{route.total_m:g} metres, about {route.walking_minutes} minutes on foot.",
    ]
    if route.elevators:
        lines.append(f"You will use {route.elevators} elevator.")
    if route.stairs:
        lines.append(f"Warning. The route includes {route.stairs} flight or flights of stairs.")
    if route.crossings:
        lines.append(f"{route.crossings} road crossings. Listen for traffic before each one.")
    lines.append("")
    for step in route.steps:
        lines.append(f"Step {step.order}. {step.instruction} {step.detail}")
    if route.warnings:
        lines.append("")
        lines.append("Please note:")
        lines.extend(f"- {w}" for w in route.warnings)
    return "\n".join(lines)


def spoken_summary(route: Route) -> str:
    """Route-accurate spoken guidance, used as the offline fallback for Gemini.

    Written to be read aloud in one breath per sentence: no markdown, no
    symbols, no numerals that a screen reader would mangle.
    """
    if not route.ok:
        return f"I cannot plan that route. {route.reason}"

    numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    destination = _spoken_place(route.destination)
    source = _spoken_place(route.origin)

    parts = [
        f"Heading to {destination}, starting from {source}. "
        f"{route.total_m:g} metres, about {route.walking_minutes} minutes on foot."
    ]

    if route.stairs:
        parts.append(
            f"Warning. This route includes {numbers.get(route.stairs, route.stairs)} "
            "flight or flights of stairs, and I could not find a step-free way round."
        )
    else:
        parts.append("The whole route is step-free.")
    if route.elevators:
        parts.append(
            f"You will use {numbers.get(route.elevators, route.elevators)} elevator"
            f"{'s' if route.elevators > 1 else ''}."
        )
    if route.crossings:
        if route.crossings == 1:
            parts.append("There is one road crossing. Stop and listen for traffic "
                         "before you cross.")
        else:
            parts.append(
                f"There are {numbers.get(route.crossings, route.crossings)} road "
                "crossings. Stop and listen for traffic at each one."
            )
    if route.max_gradient >= 6.0:
        parts.append(
            f"The steepest section is {route.max_gradient:g} percent, so take it slowly."
        )

    walk = [s for s in route.steps if s.kind == "walk"]
    vertical = [s for s in route.steps if s.kind != "walk"]

    body: list[str] = []
    ordinals = ("First", "Then", "After that", "Next")
    for index, step in enumerate(walk):
        lead = ordinals[min(index, len(ordinals) - 1)]
        arrival = _spoken_place(_place_after(route, step.order))
        street = _spoken_name(step.edge_name)
        sentence = (
            f"{lead}, continue on {street} for {step.distance_m:g} "
            f"metres toward {arrival}. The surface is {step.surface}, "
            f"{step.width_m:g} metres wide"
        )
        if step.gradient_pct is not None:
            sentence += f", with {_a(step.gradient_pct)} percent gradient"
        else:
            sentence += ", and it is level"
        if step.crossings:
            sentence += (
                f", with {numbers.get(step.crossings, step.crossings)} road "
                "crossing" + ("s" if step.crossings > 1 else "")
            )
        if step.tactile == "guidance":
            sentence += ". A tactile guide strip runs alongside this section"
        elif step.tactile == "warning":
            sentence += ". Tactile warning tiles mark a raised crossing"
        body.append(sentence.rstrip(".") + ".")

        for feature in step.features:
            if feature.kind == "path":
                body.append(f"There is a ramp here: {feature.name}.")
            elif feature.kind == "hazard":
                body.append(f"Caution. {feature.name}. {feature.description}")

    for step in vertical:
        if step.kind == "elevator":
            body.append(
                f"Finally, take {step.edge_name}. Wait for the car, then travel "
                "one level. The announcements are audible and in braille."
            )
        else:
            body.append(f"Finally, use {step.edge_name}. {step.detail}")

    parts.extend(body)

    if route.relaxations:
        parts.append(
            "I could not hold to all of your preferences and had to "
            + ", then ".join(route.relaxations)
            + ". Please check each step before you rely on it."
        )
    parts.append(
        "This is sample data on a prototype map. Confirm the real route with campus "
        "accessibility services before you travel."
    )
    return " ".join(parts)


def _place_after(route: Route, step_order: int) -> str:
    """The place reached after completing step number ``step_order``."""
    place = route.origin
    for edge_id in route.edge_ids[:step_order]:
        edge = EDGE_BY_ID[edge_id]
        place = edge.b if place == edge.a else edge.a
    return place


def _spoken_place(place_id: str) -> str:
    """Place name for text-to-speech, without a stuttering "the The Quad"."""
    name = place_name(place_id)
    if name.lower().startswith("the "):
        return name
    return f"the {name}"


def _spoken_name(name: str) -> str:
    """Prefix a proper-noun way name with an article for text-to-speech."""
    if not name:
        return name
    if name.lower().startswith("the "):
        return name
    return f"the {name}"


def _a(value: float) -> str:
    """"an 8 percent" but "a 3 percent"."""
    text = f"{value:g}"
    return f"an {text}" if text[:1] in "8" or text[:1] in "11" or text[:1] in "18" else f"a {text}"


def nearby_features(place_id: str, radius: float = 130.0) -> list[Feature]:
    """Features whose pin sits within ``radius`` map units of a place."""
    place = PLACE_BY_ID.get(place_id)
    if not place:
        return []
    out: list[tuple[float, Feature]] = []
    for feature in FEATURE_BY_ID.values():
        distance = math.hypot(feature.x - place.x, feature.y - place.y)
        if distance <= radius:
            out.append((distance, feature))
    return [f for _, f in sorted(out, key=lambda pair: pair[0])]
