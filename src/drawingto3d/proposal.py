"""Propose a general plan from what the reading layers saw: observations, bindings, meanings.

The target is the flat-part archetype the plate experiment stands for: one closed outer profile
in the plan view, circular holes and one central pocket, a thickness and a pocket depth read off
a section view. Every number that reaches the plan is either **printed** (carrying the span id it
came from) or **derived** from those by an expression; the drawing's measured geometry is used to
*verify* those numbers and to place the sketch, and a disagreement beyond tolerance refuses the
proposal instead of rounding it away. Nothing here guesses: when a sheet is not this archetype
yet — a missing section, an asymmetric layout, a third diameter callout — the proposal is empty
and the refusal list says exactly what was missing, which is the roadmap for the next slice.

The proposal is reviewable JSON: the plan it carries is a `GeneralPlan` and can be handed to
`build-general` as it stands, which is how the plate sheet goes drawing to STEP through the
family-independent engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from drawingto3d.general import (ArcEntity, CircleEntity, CutOp, Expect, ExtrudeOp,
                                 GeneralPlan, LineEntity, LinearRepeat, Parameter, RepeatOp,
                                 Sketch, SourceRef)
from drawingto3d.meaning import Meanings, SpanMeaning, meaning_page
from drawingto3d.observe import observe

LOOP_TOLERANCE_PX = 3.0
# A tangent joint breaks endpoint proximity: at the corner the line's ink and the arc's ink are the
# same ink, so an arc that was trimmed to its own ink stops some ten pixels short of the corner and an
# arc that was not overshoots it by about the same. The join is therefore kept when a point stands *on
# the arc's circle*, inside the arc's own angular range — that is where the corner is.
ARC_JOIN_SLACK_PX = 2.5
ARC_JOIN_DEGREES = 25.0
ARC_JOIN_PENALTY_PX = 8.0
ARC_JOIN_SNAP_PX = 16.0   # how far apart a corner and a trimmed arc end may sit and still be one corner
# A raster outline is broken by the drawing's own dimension lines, leaders and print noise: measured on
# `1/Exercise_51.PNG` the part's own pieces sit 1.6 … 32.7 px apart where a vector reading's joins are
# exact. The widening is a raster rule only — a vector reading's chains were measured at 3 px, and the
# least-turn rule is what keeps the wider tolerance from walking off along a dimension line.
# Measured sweep (2026-09-28, four real sheets): 6 px leaves 15-31 small junk wires per sheet, 36 px
# collapses Flange to 4 wires and 52x121 px; 20 px keeps 9-17 wires with a part-scale outline on top
# (723x718 / 730x816 / 356x568 / 427x334) and no sheet-frame box. 20 px ~ 1.6 mm on these sheets.
# (The sweep reused one `observe` per sheet and may carry per-call state; a fresh-process re-measure
# at 20 px follows — /tmp/guided-raster2-run8.txt.)
RASTER_JOIN_TOLERANCE_PX = 20.0


def _line_arc_corner(line_start: np.ndarray, line_end: np.ndarray, meta: dict) -> np.ndarray | None:
    """Where a line meets an arc: the arc's centre projected onto the line — the tangent point.

    Endpoints will not do here. The merge pass extends a straight stroke over the arc's own tangent
    ink (that ink runs parallel to the line), so a line's recorded end can sit thirty pixels past the
    corner; and the arc's end is trimmed back for the same reason. The corner is where the two
    geometries meet, so the arc's centre is projected onto the line and that foot is the join.
    """
    if meta.get("kind") != "arc":
        return None
    centre = np.asarray(meta["centre"], dtype=float)
    start = np.asarray(line_start, dtype=float)
    direction = np.asarray(line_end, dtype=float) - start
    length = float(np.linalg.norm(direction))
    if length <= 0.0:
        return None
    unit = direction / length
    along = float((centre - start) @ unit)
    if along < -LOOP_TOLERANCE_PX or along > length + LOOP_TOLERANCE_PX:
        return None
    foot = start + along * unit
    if abs(float(np.linalg.norm(foot - centre)) - float(meta["radius"])) > LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX:
        return None
    return foot


def _arc_hit(point: np.ndarray, meta: dict) -> np.ndarray | None:
    """The point projected onto an arc's ring when it stands at that arc's end, else None."""
    if meta.get("kind") != "arc":
        return None
    centre = np.asarray(meta["centre"], dtype=float)
    radius = float(meta["radius"])
    offset = np.asarray(point, dtype=float) - centre
    distance = float(np.linalg.norm(offset))
    if abs(distance - radius) > LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX:
        return None
    angle = float(np.degrees(np.arctan2(offset[1], offset[0]))) % 360.0
    span = float(meta["end_degrees"]) - float(meta["start_degrees"])
    delta = (angle - float(meta["start_degrees"])) % 360.0
    if delta > span + ARC_JOIN_DEGREES and delta < 360.0 - ARC_JOIN_DEGREES:
        return None
    return centre + offset / (distance or 1.0) * radius
ARC_SAMPLES = 12
CHECK_RELATIVE = 0.01
CHECK_ABSOLUTE_MM = 0.5
FRAME_COVERAGE = 0.80
# A closed loop that carries printed phrases inside it is an annotation region, not the part: a title
# block, a parts table or the sheet's own border. Measured on the four vector sheets this project has:
# every part loop holds 0 phrases, the border holds 25-66, and one sheet's title-block box (a plain
# 4-line rectangle, the biggest loop left once the border is skipped) held 18 phrases, 16 of them
# words. The share test is what keeps a dimension text printed inside a view from condemning a real
# outline: a part loop that happens to hold a number or two still holds almost no words.
ANNOTATION_MIN_PHRASES = 3
ANNOTATION_WORD_SHARE = 0.5
# A rotational body seen face-on carries a stack of circles about one centre. Measured on the four vector
# sheets: the flanged elbow's stack has 5 circles at 5 distinct diameters with its biggest circle 0.193 of
# the page width, against 0.011 for the plastic's small holes and no stack at all on the two flat sheets.
FLANGE_FAMILY_MIN_CIRCLES = 3
FLANGE_FAMILY_MIN_STEPS = 3
FLANGE_DIAMETER_SHARE = 0.15
OUTLINE_REFUSALS = {
    "no-loops": "kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor)",
    "frame-only": "kapalı dış kontur bulunamadı (sayfa çerçevesi dışında döngü yok)",
    "annotation-only": "kapalı dış kontur bulunamadı (döngüler yalnız çerçeve ve antet/tablo bölgesi)",
}


class Proposal(BaseModel):
    version: int = 1
    source_ref: str
    source_sha256: str
    sheet_px_per_mm: float | None = None
    status: Literal["proposed", "refused"] = "refused"
    plan: GeneralPlan | None = None
    readings: list[str] = Field(default_factory=list)
    measurements: dict[str, float] = Field(default_factory=dict)
    refusals: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _round(value: float) -> float:
    return float(round(value, 2))


def _arc_points(centre: np.ndarray, radius: float, start_degrees: float,
                end_degrees: float, samples: int) -> list[np.ndarray]:
    """Sample the drawn run. `observe` unwraps its angles, so `end - start` is the signed sweep
    (a corner round drawn clockwise arrives as -90): keep the sign, and pull a difference that
    crossed the wrap point back inside one turn."""
    start = np.radians(start_degrees)
    delta = np.radians(end_degrees) - start
    if delta > 2 * np.pi:
        delta -= 2 * np.pi
    elif delta < -2 * np.pi:
        delta += 2 * np.pi
    return [centre + radius * np.array([np.cos(t), np.sin(t)])
            for t in np.linspace(start, start + delta, samples)]


def _turn_degrees(direction: np.ndarray, following: np.ndarray) -> float:
    """How sharply a chain would turn if it continued with `following`: 0 is straight on."""
    a = direction / (float(np.linalg.norm(direction)) or 1.0)
    b = following / (float(np.linalg.norm(following)) or 1.0)
    return float(np.degrees(np.arccos(float(np.clip(np.dot(a, b), -1.0, 1.0)))))


def raster_arcs(observations) -> bool:
    """True when the arcs came off image ink: only then do the tangent-corner joins apply.

    A raster reading shares the corner between a line and its tangent arc (the ink is one blob there),
    so endpoint proximity alone can never close a curved outline; a vector reading has real endpoints
    and its chains were measured without the corner join, so it keeps that rule.
    """
    return any(getattr(primitive, "method", "") == "hough-arc"
               for primitive in getattr(observations, "primitives", ()))


def _loops(lines: dict[str, tuple[np.ndarray, np.ndarray]],
           arcs: dict[str, tuple[np.ndarray, float, float, float]],
           corner_joins: bool = False, join_tolerance_px: float = LOOP_TOLERANCE_PX) -> list[dict]:
    """Chain lines and arcs into closed loops by endpoint proximity; biggest first.

    `corner_joins` turns on the tangent-corner join (below): it is what lets a *raster* outline close —
    image ink shares the corner between a line and its tangent arc — but on a *vector* reading it also
    closes small chains the sheet did not intend, which changed which loop the refusal named, so it is
    off unless the caller knows its arcs came off pixels.

    Three rules pick the chain, and each one exists because the first cut of this walked into a
    drawing's dimension lines and lost the part: a segment whose far end returns to the chain's
    start is taken at once (the drawing's own outline is a closed run; letting a neighbour in first
    walks off along a dimension line), otherwise the continuation that turns least is taken (a drawn
    contour carries on smoothly where an extension or a leader leaves at an angle), and a chain that
    dead-ends claims nothing — its segments stay in the pool, so one greedy dead end cannot swallow
    the runs a real loop is made of. On `Drawing.pdf` the previous version chained 239 lines into
    three loops, because the first chains ate the outline's own segments.
    """
    segments: list[tuple[str, np.ndarray, np.ndarray, dict]] = []
    for geometry_id, (start, end) in lines.items():
        segments.append((geometry_id, start, end, {"kind": "line"}))
    for geometry_id, (centre, radius, start_degrees, end_degrees) in arcs.items():
        points = _arc_points(centre, radius, start_degrees, end_degrees, 2)
        segments.append((geometry_id, points[0], points[-1],
                         {"kind": "arc", "centre": centre, "radius": radius,
                          "start_degrees": start_degrees, "end_degrees": end_degrees}))
    loops: list[dict] = []
    claimed: set[int] = set()
    for index in range(len(segments)):
        if index in claimed:
            continue
        geometry_id, start, end, meta = segments[index]
        chain = [(geometry_id, start, end, meta)]
        chain_indexes = [index]
        tail = end
        direction = end - start
        while len(chain) < len(segments):
            candidates = []
            for other_index, (other_id, other_start, other_end, other_meta) in enumerate(segments):
                if other_index in chain_indexes or other_index in claimed:
                    continue
                for near, far in ((other_start, other_end), (other_end, other_start)):
                    gap = float(np.linalg.norm(near - tail))
                    meet, terminal = near, far
                    if gap > join_tolerance_px:
                        if not corner_joins:
                            continue
                        previous = chain[-1]
                        corner = _line_arc_corner(previous[1], previous[2], other_meta)   # candidate is the arc
                        if corner is None:
                            corner = _line_arc_corner(near, far, previous[3])             # the chain's is
                        if corner is not None:
                            if float(np.linalg.norm(corner - near)) > float(np.linalg.norm(corner - far)):
                                continue   # that corner sits at this candidate's far end: it is a U-turn
                            meet = corner
                            gap = float(np.linalg.norm(corner - tail)) + ARC_JOIN_PENALTY_PX
                        else:
                            corner = _arc_hit(tail, other_meta)
                            if corner is not None:
                                meet, gap = corner, gap + ARC_JOIN_PENALTY_PX
                            else:
                                corner = _arc_hit(near, chain[-1][3])
                                if corner is None:
                                    continue
                                gap = float(np.linalg.norm(corner - tail)) + ARC_JOIN_PENALTY_PX
                    closing = float(np.linalg.norm(far - start)) <= join_tolerance_px
                    if not closing and corner_joins:
                        corner = _line_arc_corner(chain[0][1], chain[0][2], other_meta)
                        if corner is not None and float(np.linalg.norm(corner - far)) <= ARC_JOIN_SNAP_PX:
                            closing = True
                        else:
                            corner = _line_arc_corner(near, far, chain[0][3])
                            if corner is not None and float(np.linalg.norm(corner - start)) <= ARC_JOIN_SNAP_PX:
                                closing = True
                            else:
                                closing = (_arc_hit(far, chain[0][3]) is not None
                                           or _arc_hit(start, other_meta) is not None)
                    closing = closing and len(chain) >= 3   # two segments cannot be a loop
                    candidates.append((not closing, _turn_degrees(direction, terminal - meet), gap,
                                       other_index, other_id, meet, terminal, other_meta))
            if not candidates:
                break
            candidates.sort(key=lambda item: item[:3])
            _, _, _, other_index, other_id, near, far, other_meta = candidates[0]
            if corner_joins and float(np.linalg.norm(near - tail)) > LOOP_TOLERANCE_PX:
                previous_id, previous_start, _previous_end, previous_meta = chain[-1]
                chain[-1] = (previous_id, previous_start, near, previous_meta)  # the corner, not the end
            chain.append((other_id, near, far, other_meta))
            chain_indexes.append(other_index)
            tail = far
            direction = far - near
            closed = float(np.linalg.norm(tail - start)) <= join_tolerance_px
            if not closed and corner_joins:
                corner = _line_arc_corner(chain[0][1], chain[0][2], chain[-1][3])
                if corner is not None and float(np.linalg.norm(corner - tail)) <= ARC_JOIN_SNAP_PX:
                    closed = True
                else:
                    closed = (_arc_hit(tail, chain[0][3]) is not None
                              or _arc_hit(start, chain[-1][3]) is not None)
            if closed and len(chain) >= 3:
                loops.append({"entities": chain, "area_px": _loop_area(chain)})
                claimed.update(chain_indexes)
                break
    loops.sort(key=lambda loop: -loop["area_px"])
    return loops


def _loop_area(chain: list[tuple[str, np.ndarray, np.ndarray, dict]]) -> float:
    points: list[np.ndarray] = []
    for _geometry_id, start, end, meta in chain:
        if meta["kind"] == "arc":
            points.extend(_arc_points(meta["centre"], meta["radius"],
                                      meta["start_degrees"], meta["end_degrees"], ARC_SAMPLES))
        else:
            points.append(start)
            points.append(end)
    polygon = np.array(points)
    x, y = polygon[:, 0], polygon[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def _rounded_rectangle(chain: list[tuple[str, np.ndarray, np.ndarray, dict]],
                       scale: float) -> tuple[float, float, float] | None:
    """(width_mm, height_mm, corner_radius_mm) if the loop is two axis-aligned line pairs and
    four quarter arcs of one radius; None otherwise."""
    lines_ = [item for item in chain if item[3]["kind"] == "line"]
    arcs_ = [item for item in chain if item[3]["kind"] == "arc"]
    if len(lines_) != 4 or len(arcs_) != 4:
        return None
    for _gid, start, end, _meta in lines_:
        if abs(start[0] - end[0]) > 1.0 and abs(start[1] - end[1]) > 1.0:
            return None
    radii = [item[3]["radius"] for item in arcs_]
    radius = float(np.mean(radii))
    if any(abs(item - radius) / radius > 0.02 for item in radii):
        return None
    for item in arcs_:
        sweep = item[3]["end_degrees"] - item[3]["start_degrees"]
        if abs(abs(sweep) - 90) > 5:
            return None
    points = np.array([p for _gid, start, end, _meta in chain for p in (start, end)])
    width = float(points[:, 0].max() - points[:, 0].min())
    height = float(points[:, 1].max() - points[:, 1].min())
    return width / scale, height / scale, radius / scale


def _loop_box(loop: dict) -> tuple[np.ndarray, np.ndarray]:
    points = np.array([p for _gid, start, end, _meta in loop["entities"] for p in (start, end)])
    return points.min(axis=0), points.max(axis=0)


def _frame_loops(loops: list[dict], page_width: float, page_height: float) -> set[int]:
    """Indexes of loops that are the sheet frame: covering most of the page, or holding the
    other loops."""
    page_area = page_width * page_height
    frames: set[int] = set()
    for index, loop in enumerate(loops):
        (x0, y0), (x1, y1) = _loop_box(loop)
        coverage = (x1 - x0) * (y1 - y0) / page_area
        contained = 0
        for other_index, other in enumerate(loops):
            if other_index == index:
                continue
            (ox0, oy0), (ox1, oy1) = _loop_box(other)
            if x0 - 1 <= ox0 and ox1 <= x1 + 1 and y0 - 1 <= oy0 and oy1 <= y1 + 1:
                contained += 1
        if coverage >= FRAME_COVERAGE or (coverage >= 0.60 and contained >= 1):
            frames.add(index)
    return frames


def _annotation_loops(loops: list[dict], phrases) -> set[int]:
    """Indexes of loops that are annotation regions: their inside carries printed phrases, and most of
    those phrases are words rather than numbers — a title block, a parts table, a note column.

    An outline of the part itself holds no phrases at all on the sheets measured; a *view* can hold a
    dimension number or two, which is why the test asks for a minimum count and a word share instead
    of "any phrase at all".
    """
    regions: set[int] = set()
    for index, loop in enumerate(loops):
        (x0, y0), (x1, y1) = _loop_box(loop)
        inside = [item for item in phrases
                  if x0 < item[2] + item[4] / 2 < x1 and y0 < item[3] + item[5] / 2 < y1]
        if len(inside) < ANNOTATION_MIN_PHRASES:
            continue
        words = [item for item in inside if item[1] is None and any(ch.isalpha() for ch in item[0])]
        if len(words) >= ANNOTATION_WORD_SHARE * len(inside):
            regions.add(index)
    return regions


def _phrases(observations) -> list[tuple[str, float | None, float, float, float, float]]:
    """The sheet's printed phrases as `(text, value, x, y, w, h)` in the sheet's own pixels."""
    return [(item.text, item.value, float(item.bbox.x), float(item.bbox.y),
             float(item.bbox.w), float(item.bbox.h)) for item in observations.texts]


def _concentric_families(circles: dict, tolerance_px: float = 2.0,
                         tolerance_share: float = 0.03) -> list[list[tuple[str, np.ndarray, float]]]:
    """Circles that share a centre: one flange's diameter stack, a bore with its counterbore, a boss."""
    families: list[list[tuple[str, np.ndarray, float]]] = []
    for geometry_id, (centre, radius) in sorted(circles.items()):
        for family in families:
            if float(np.linalg.norm(centre - family[0][1])) <= max(tolerance_px,
                                                                   tolerance_share * max(radius, family[0][2])):
                family.append((geometry_id, centre, radius))
                break
        else:
            families.append([(geometry_id, centre, radius)])
    return families


def part_class(observations) -> dict:
    """Which class of part the sheet's own geometry supports, and the evidence that decided it.

    Read from the drawing, never from a file name: a stack of circles about one centre whose biggest
    circle covers a real part of the page is a rotational body seen face-on, and it is checked before
    the flat-part test. Measured on the four vector sheets this project reads: `10/Exercise 12` (a
    flanged elbow) carries a five-circle stack — Ø274/Ø160/Ø142/Ø93/Ø77 mm against the printed
    Ø270/Ø158/Ø140/Ø92/Ø76 — whose largest circle is 0.193 of the page width, while the plate and
    `Drawing.pdf` have no stack at all and the plastic's stacks are 0.011 of the width (its small
    holes).
    """
    lines, arcs, circles = _primitives(observations)
    width = float(observations.frame.width) if observations.frame else 0.0
    height = float(observations.frame.height) if observations.frame else 0.0
    stacks = []
    for family in _concentric_families(circles):
        diameters = {round(2.0 * radius, 1) for _gid, _centre, radius in family}
        if len(family) < FLANGE_FAMILY_MIN_CIRCLES or len(diameters) < FLANGE_FAMILY_MIN_STEPS:
            continue
        biggest = max(2.0 * radius for _gid, _centre, radius in family)
        stacks.append({"centre_px": [round(float(v), 1) for v in family[0][1]], "circles": len(family),
                       "diameters_px": sorted(diameters),
                       "biggest_share_of_page": round(biggest / width, 3) if width else 0.0,
                       "geometry_ids": [gid for gid, _centre, _radius in family]})
    stacks.sort(key=lambda row: -row["biggest_share_of_page"])
    if stacks and stacks[0]["biggest_share_of_page"] >= FLANGE_DIAMETER_SHARE:
        return {"class": "rotational-flanged", "evidence": stacks[0], "reason": None}
    loops = _loops(lines, arcs)
    frames = _frame_loops(loops, width, height) if observations.frame else set()
    tables = _annotation_loops(loops, _phrases(observations)) - frames
    if any(index not in frames and index not in tables for index in range(len(loops))):
        return {"class": "flat-part", "evidence": {"loops": len(loops) - len(frames) - len(tables)},
                "reason": None}
    return {"class": "unknown", "evidence": None,
            "reason": "ne kapalı parça konturu ne de eş merkezli çap yığını okunabildi"}


def _classify_claims(meanings: Meanings, loop_ids: set[str], circle_ids: set[str]) -> dict:
    """Sort the confirmed claims by the geometry they touch: outline, spacing, section, sizes."""
    classified: dict = {"outline": [], "spacing": [], "section": [], "diameters": []}
    for span in meanings.spans:
        if span.resolution != "confirmed" or span.claim is None:
            continue
        claim = span.claim
        if claim.form == "diameter":
            classified["diameters"].append(span)
            continue
        if claim.form != "distance" or len(claim.points) != 2:
            continue
        ids = {point.geometry_id for point in claim.points}
        if ids <= loop_ids:
            classified["outline"].append(span)
        elif ids <= circle_ids:
            classified["spacing"].append(span)
        else:
            classified["section"].append(span)
    return classified


def _axis_of(span: SpanMeaning) -> str:
    assert span.claim is not None
    first, second = span.claim.points
    dx = abs(second.point[0] - first.point[0])
    dy = abs(second.point[1] - first.point[1])
    return "x" if dx >= dy else "y"


def _measurement_check(name: str, measured_mm: float, printed_mm: float,
                       readings: list[str], refusals: list[str]) -> None:
    deviation = abs(measured_mm - printed_mm)
    tolerance = max(CHECK_RELATIVE * printed_mm, CHECK_ABSOLUTE_MM)
    line = (f"{name}: ölçülen {_round(measured_mm)} mm, basılı {_round(printed_mm)} mm "
            f"(Δ{_round(deviation)})")
    if deviation > tolerance:
        refusals.append(f"{line} — tolerans {_round(tolerance)} mm")
    else:
        readings.append(line)


class SheetReading(BaseModel):
    """What one sheet measures, in millimetres, with no plan and no model involved.

    The reading chain's own product, kept apart from the proposal on purpose: `propose_general`
    refines it into the flat-part archetype's plan, while the model planner is asked the *same*
    measurements — so a comparison between the rules-based proposal and the model's plan is a
    comparison of the planner, not of the reading. A sheet whose outline is not this archetype's
    rounded rectangle still gets its measured regions here, because the model is asked about shapes
    the archetype refuses; a sheet with no fitted scale gets no millimetres at all and says so.
    """

    version: int = 1
    source_ref: str
    source_sha256: str = ""
    sheet_px_per_mm: float | None = None
    frame: dict = Field(default_factory=dict)
    printed: list[dict] = Field(default_factory=list)
    claims: list[dict] = Field(default_factory=list)
    outline_mm: dict | None = None
    circles_mm: list[dict] = Field(default_factory=list)
    components: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    refusals: list[str] = Field(default_factory=list)


def _primitives(observations) -> tuple[dict, dict, dict]:
    """The sheet's fitted lines, arcs and circles, by geometry id, in the sheet's own pixels."""
    lines: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    arcs: dict[str, tuple[np.ndarray, float, float, float]] = {}
    circles: dict[str, tuple[np.ndarray, float]] = {}
    for primitive in observations.primitives:
        if primitive.kind == "line" and primitive.start and primitive.end:
            lines[primitive.id] = (np.array(primitive.start, dtype=float),
                                   np.array(primitive.end, dtype=float))
        elif primitive.kind == "arc" and primitive.centre and primitive.radius:
            arcs[primitive.id] = (np.array(primitive.centre, dtype=float), primitive.radius,
                                  primitive.start_degrees or 0.0, primitive.end_degrees or 360.0)
        elif primitive.kind == "circle" and primitive.centre and primitive.radius:
            circles[primitive.id] = (np.array(primitive.centre, dtype=float), primitive.radius)
    return lines, arcs, circles


def _outline_of(observations, lines: dict, arcs: dict) -> tuple[dict | None, dict]:
    """The biggest closed loop that is not the sheet frame, and how it was chosen.

    Returns the loop and a small record (`loops`, `frame_loops`, `reason`) instead of raising, so
    the two callers below can phrase the same refusal without repeating the search.
    """
    loops = _loops(lines, arcs)
    if not loops:
        return None, {"loops": 0, "frame_loops": 0, "annotation_loops": 0, "reason": "no-loops"}
    frame_indexes = (_frame_loops(loops, observations.frame.width, observations.frame.height)
                     if observations.frame else set())
    annotation_indexes = _annotation_loops(loops, _phrases(observations))
    tables = annotation_indexes - frame_indexes
    part_loops = [loop for index, loop in enumerate(loops)
                  if index not in frame_indexes and index not in annotation_indexes]
    if not part_loops:
        reason = "frame-only" if frame_indexes else "annotation-only"
        return None, {"loops": len(loops), "frame_loops": len(frame_indexes),
                      "annotation_loops": len(tables), "reason": reason}
    return part_loops[0], {"loops": len(loops), "frame_loops": len(frame_indexes),
                           "annotation_loops": len(tables), "reason": None}


def read_sheet(path: str | Path) -> SheetReading:
    """Read one real sheet into millimetres: components, the closed outline, the circles inside it."""
    drawing = Path(path)
    observations = observe(drawing)
    meanings = meaning_page(drawing)
    reading = SheetReading(source_ref=str(drawing), source_sha256=meanings.source_sha256,
                           sheet_px_per_mm=meanings.sheet_px_per_mm)
    # Printed quantities do not depend on recovering a closed outline or a drawing scale.
    # Keep them even when the geometry stage below has to stop.
    for span in meanings.spans:
        if span.printed_value is not None:
            reading.printed.append({"span_id": span.span_id, "text": span.text,
                                    "value": span.printed_value, "unit": span.unit,
                                    "kind": span.kind, "count": span.count})
    if observations.frame:
        reading.frame = {"width_px": observations.frame.width, "height_px": observations.frame.height,
                         "dpi": observations.frame.dpi}
    lines, arcs, circles = _primitives(observations)
    outline, selection = _outline_of(observations, lines, arcs)
    reading.components = {"lines": len(lines), "arcs": len(arcs), "circles": len(circles),
                          "loops": selection["loops"], "frame_loops": selection["frame_loops"],
                          "annotation_loops": selection["annotation_loops"]}
    dropped = sum(1 for span in meanings.spans if span.printed_value is None)
    scale = meanings.sheet_px_per_mm
    if scale is not None and any(getattr(primitive, "method", "") == "hough-arc"
                                 for primitive in getattr(observations, "primitives", ())):
        # A raster sheet's anchors are pixel-fitted geometry, so a scale built on them is an unverified
        # measurement dressed as the sheet's own — and the arcs this reader now fits would hand it such
        # a scale out of nothing (measured: an unmeasurable .jpg gained 3.28 px/mm and reached a
        # planner). The reading refuses instead; on a raster the scale is the user's calibration in the
        # guided flow, which is where a clicked two-point measurement belongs.
        reading.notes.append("raster pafta: ölçek kullanıcı kalibrasyonunda — pikselden uyarlanan "
                             "geometri paftanın kendi ölçüsü sayılmadı")
        scale = None
    if selection["frame_loops"]:
        reading.notes.append(f"sayfa çerçevesi atlandı ({selection['frame_loops']} döngü)")
    if selection["annotation_loops"]:
        reading.notes.append(f"antet/tablo bölgesi atlandı ({selection['annotation_loops']} döngü)")
    if scale is None:
        reading.refusals.append("pafta ölçeği okunamadı (kalibrasyon yok)")
        return reading
    if outline is None:
        reading.refusals.append(OUTLINE_REFUSALS[selection["reason"]])
        return reading

    (x0, y0), (x1, y1) = _loop_box(outline)
    rectangle = _rounded_rectangle(outline["entities"], scale)
    reading.outline_mm = {"width_mm": _round((x1 - x0) / scale), "height_mm": _round((y1 - y0) / scale),
                          "rounded_rectangle": rectangle is not None,
                          "primitives": len(outline["entities"])}
    if rectangle is not None:
        width_mm, height_mm, corner_radius_mm = rectangle
        reading.outline_mm.update({"width_mm": _round(width_mm), "height_mm": _round(height_mm),
                                   "corner_radius_mm": _round(corner_radius_mm)})
    points = np.array([point for _gid, start, end, _meta in outline["entities"] for point in (start, end)])
    min_xy, max_xy = points.min(axis=0), points.max(axis=0)
    centre = (min_xy + max_xy) / 2

    def in_mm(point) -> list[float]:
        """One measured point, relative to the outline's centre and divided by the fitted scale."""
        return [_round((point[0] - centre[0]) / scale), _round((point[1] - centre[1]) / scale)]

    for geometry_id, (position, radius) in sorted(circles.items()):
        if (min_xy[0] - 1 <= position[0] <= max_xy[0] + 1
                and min_xy[1] - 1 <= position[1] <= max_xy[1] + 1):
            reading.circles_mm.append({"id": geometry_id, "diameter_mm": _round(2.0 * radius / scale),
                                       "centre_mm": in_mm(position)})
    for span in meanings.spans:
        if span.printed_value is None:
            continue
        if span.claim is None:
            continue
        claim = {"span_id": span.span_id, "form": span.claim.form, "resolution": span.resolution,
                 "anchor_mode": span.anchor_mode, "printed_mm": _round(span.claim.printed_mm),
                 "drawn_mm": _round(span.claim.drawn_mm), "deviation_mm": _round(span.claim.deviation_mm),
                 "anchors": [{"geometry_id": point.geometry_id, "kind": point.kind,
                              "point_mm": in_mm(point.point)} for point in span.claim.points],
                 "matched_geometry": list(span.claim.matched_geometry)}
        for field in ("count", "covered"):
            value = getattr(span, field, None)
            if value is not None:
                claim[field] = value
        if span.notes:
            claim["notes"] = list(span.notes)
        reading.claims.append(claim)
    reading.notes.append(f"{len(reading.printed)} sayısal ölçü; {len(reading.claims)} tanesi "
                         f"geometriye bağlandı ({sum(len(claim['anchors']) for claim in reading.claims)} "
                         f"çapa noktası)")
    if dropped:
        reading.notes.append(f"{dropped} sayısal olmayan metin ölçü sayılmadı")
    reading.notes.append(
        f"konumlar konturun merkezine göre, paftanın kendi piksel çerçevesinde ölçüldü "
        f"({_round(scale)} px/mm)")
    return reading


def propose_general(path: str | Path) -> Proposal:
    """Read the sheet and propose the general plan it supports, or refuse with the reasons."""
    drawing = Path(path)
    observations = observe(drawing)
    meanings = meaning_page(drawing)
    proposal = Proposal(source_ref=str(drawing), source_sha256=meanings.source_sha256,
                        sheet_px_per_mm=meanings.sheet_px_per_mm)
    scale = meanings.sheet_px_per_mm
    if scale is None:
        proposal.refusals.append("pafta ölçeği okunamadı (kalibrasyon yok)")
        return proposal

    lines, arcs, circles = _primitives(observations)
    outline, selection = _outline_of(observations, lines, arcs)
    if selection["frame_loops"]:
        proposal.notes.append(f"sayfa çerçevesi atlandı ({selection['frame_loops']} döngü)")
    if selection["annotation_loops"]:
        proposal.notes.append(f"antet/tablo bölgesi atlandı ({selection['annotation_loops']} döngü)")
    if outline is None:
        proposal.refusals.append(OUTLINE_REFUSALS[selection["reason"]])
        return proposal
    loop_ids = {item[0] for item in outline["entities"]}
    rectangle = _rounded_rectangle(outline["entities"], scale)
    if rectangle is None:
        (x0, y0), (x1, y1) = _loop_box(outline)
        proposal.refusals.append(
            "en büyük kapalı döngü yuvarlatılmış dikdörtgen değil "
            f"({len(outline['entities'])} ilkel, {_round((x1 - x0) / scale)}×"
            f"{_round((y1 - y0) / scale)} mm; bu dilim yalnız düz parça arketipini öneriyor)")
        return proposal
    width_mm, height_mm, corner_radius_mm = rectangle

    points = np.array([p for _gid, start, end, _meta in outline["entities"] for p in (start, end)])
    min_xy, max_xy = points.min(axis=0), points.max(axis=0)
    inside = {geometry_id: (centre, radius) for geometry_id, (centre, radius) in circles.items()
              if min_xy[0] - 1 <= centre[0] <= max_xy[0] + 1
              and min_xy[1] - 1 <= centre[1] <= max_xy[1] + 1}
    classified = _classify_claims(meanings, loop_ids, set(inside))

    sized = [(span, span.claim) for span in classified["diameters"] if span.claim is not None]
    sized.sort(key=lambda item: item[1].printed_mm)
    if len(sized) != 2:
        forms: dict[str, int] = {}
        for span in meanings.spans:
            if span.resolution == "confirmed" and span.claim is not None:
                forms[span.claim.form] = forms.get(span.claim.form, 0) + 1
        proposal.refusals.append(
            f"tam iki çap ölçüsü bekleniyordu (delik + cep), {len(sized)} okundu; "
            f"doğrulanan iddia türleri: {forms or '{}'}")
        return proposal
    hole_span, hole_claim = sized[0]
    pocket_span, pocket_claim = sized[1]
    hole_diameter = hole_claim.printed_mm
    pocket_diameter = pocket_claim.printed_mm
    hole_matches = hole_claim.matched_geometry
    if hole_span.count is not None and hole_span.count != len(hole_matches):
        proposal.refusals.append(
            f"delik sayısı tutmuyor: yazı {hole_span.count}, eşleşen daire {len(hole_matches)}")
    hole_count = hole_span.count if hole_span.count is not None else len(hole_matches)

    spacing: dict[str, SpanMeaning | None] = {"x": None, "y": None}
    for span in classified["spacing"]:
        axis = _axis_of(span)
        if spacing[axis] is None:
            spacing[axis] = span
    outline_dims: dict[str, SpanMeaning | None] = {"x": None, "y": None}
    for span in classified["outline"]:
        axis = _axis_of(span)
        if outline_dims[axis] is None:
            outline_dims[axis] = span
    section = sorted(classified["section"], key=lambda span: -span.claim.printed_mm)

    if spacing["x"] is None or spacing["y"] is None:
        proposal.refusals.append("delikler arası x/y ölçülerinden biri okunamadı")
    if outline_dims["y"] is None:
        proposal.refusals.append("kontur yüksekliği ölçüsü okunamadı")
    if len(section) < 2:
        proposal.refusals.append("kesit görünüşünde kalınlık ve derinlik ölçüleri okunamadı")
    if proposal.refusals:
        return proposal

    dx_span, dy_span = spacing["x"], spacing["y"]
    height_span = outline_dims["y"]
    assert dx_span is not None and dy_span is not None and height_span is not None
    thickness_span, depth_span = section[0], section[1]
    assert dx_span.claim and dy_span.claim and height_span.claim
    assert thickness_span.claim and depth_span.claim
    hole_dx = dx_span.claim.printed_mm
    hole_dy = dy_span.claim.printed_mm
    height = height_span.claim.printed_mm
    thickness = thickness_span.claim.printed_mm
    pocket_depth = depth_span.claim.printed_mm

    hole_centres = np.array([inside[geometry_id][0] for geometry_id in hole_matches
                             if geometry_id in inside])
    if len(hole_centres) != hole_count:
        proposal.refusals.append("delik merkezleri kontur içinde bulunamadı")
        return proposal
    measured_dx = float(np.ptp(hole_centres[:, 0])) / scale
    measured_dy = float(np.ptp(hole_centres[:, 1])) / scale
    measured_width_mm = width_mm
    measured_hole_diameter = float(np.mean([2.0 * inside[geometry_id][1] for geometry_id
                                            in hole_matches if geometry_id in inside])) / scale
    measured_pocket_diameter = float(np.mean([2.0 * inside[geometry_id][1] for geometry_id
                                              in pocket_span.claim.matched_geometry
                                              if geometry_id in inside])) / scale
    layout_centre = hole_centres.mean(axis=0)
    outline_centre = (min_xy + max_xy) / 2
    centre_offset_mm = float(np.linalg.norm(layout_centre - outline_centre)) / scale
    if centre_offset_mm > 1.0:
        proposal.refusals.append(f"delik yerleşimi kontura göre simetrik değil "
                                 f"(merkez sapması {_round(centre_offset_mm)} mm)")
        return proposal

    _measurement_check("hole_dx", measured_dx, hole_dx, proposal.readings, proposal.refusals)
    _measurement_check("hole_dy", measured_dy, hole_dy, proposal.readings, proposal.refusals)
    _measurement_check("height", height_mm, height, proposal.readings, proposal.refusals)
    _measurement_check("corner_radius", corner_radius_mm,
                       (height - hole_dy) / 2, proposal.readings, proposal.refusals)
    _measurement_check("width", measured_width_mm, hole_dx + (height - hole_dy),
                       proposal.readings, proposal.refusals)
    _measurement_check("thickness", thickness_span.claim.drawn_mm, thickness,
                       proposal.readings, proposal.refusals)
    _measurement_check("pocket_depth", depth_span.claim.drawn_mm, pocket_depth,
                       proposal.readings, proposal.refusals)
    _measurement_check("hole_diameter", measured_hole_diameter, hole_diameter,
                       proposal.readings, proposal.refusals)
    _measurement_check("pocket_diameter", measured_pocket_diameter, pocket_diameter,
                       proposal.readings, proposal.refusals)
    if proposal.refusals:
        return proposal

    proposal.measurements = {
        "hole_spacing_dx_mm": _round(measured_dx),
        "hole_spacing_dy_mm": _round(measured_dy),
        "outline_width_mm": _round(width_mm),
        "outline_height_mm": _round(height_mm),
        "corner_radius_mm": _round(corner_radius_mm),
        "layout_centre_offset_mm": _round(centre_offset_mm),
        "hole_diameter_mm": _round(measured_hole_diameter),
        "pocket_diameter_mm": _round(measured_pocket_diameter),
    }

    def printed(value: float, span: SpanMeaning) -> Parameter:
        return Parameter(unit="mm", source="printed", value=value,
                         span_ids=[span.span_id], explanation=f"'{span.text}' ölçüsünden")

    parameters: dict[str, Parameter] = {
        "hole_dx": printed(hole_dx, dx_span),
        "hole_dy": printed(hole_dy, dy_span),
        "height": printed(height, height_span),
        "thickness": printed(thickness, thickness_span),
        "pocket_depth": printed(pocket_depth, depth_span),
        "hole_diameter": printed(hole_diameter, hole_span),
        "pocket_diameter": printed(pocket_diameter, pocket_span),
        "hole_count": Parameter(unit="count", source="printed", value=hole_count,
                                span_ids=[hole_span.span_id],
                                explanation="komşu 'N x' yazısından; eşleşen daire sayısıyla doğrulandı"),
        "pi": Parameter(unit="count", source="assumed", value=3.141592653589793,
                        explanation="İfadelerdeki π; boyutsuz."),
        "corner_radius": Parameter(unit="mm", source="derived", expr="(height - hole_dy) / 2",
                                   explanation="Köşe yuvarlatması; delik bloğu ile kontur arasındaki farktan."),
        "width": Parameter(unit="mm", source="derived", expr="hole_dx + 2 * corner_radius",
                           explanation="Kontur genişliği delik aralığı ve köşe yuvarlatmasından türetildi."),
        "area": Parameter(unit="mm", source="derived",
                          expr="width * height - (4 - pi) * corner_radius ** 2",
                          explanation="Yuvarlatılmış dikdörtgenin alanı."),
    }

    half_width, half_height = "width / 2", "height / 2"
    quarter_x = "(width - 2 * corner_radius) / 2"
    quarter_y = "(height - 2 * corner_radius) / 2"
    outline_sketch = Sketch(plane="XY", offset="0", entities=[
        LineEntity(start=[f"-({quarter_x})", f"-({half_height})"], end=[quarter_x, f"-({half_height})"]),
        ArcEntity(center=[f"({quarter_x})", f"-({quarter_y})"], radius="corner_radius",
                  start_degrees=-90, end_degrees=0),
        LineEntity(start=[half_width, f"-({quarter_y})"], end=[half_width, quarter_y]),
        ArcEntity(center=[f"({quarter_x})", f"({quarter_y})"], radius="corner_radius",
                  start_degrees=0, end_degrees=90),
        LineEntity(start=[quarter_x, half_height], end=[f"-({quarter_x})", half_height]),
        ArcEntity(center=[f"-({quarter_x})", f"({quarter_y})"], radius="corner_radius",
                  start_degrees=90, end_degrees=180),
        LineEntity(start=[f"-({half_width})", quarter_y], end=[f"-({half_width})", f"-({quarter_y})"]),
        ArcEntity(center=[f"-({quarter_x})", f"-({quarter_y})"], radius="corner_radius",
                  start_degrees=180, end_degrees=270),
    ])
    sketches: dict[str, Sketch] = {
        "outline": outline_sketch,
        "hole": Sketch(plane="XY", offset="-1", entities=[
            CircleEntity(center=["0", "0"], radius="hole_diameter / 2")]),
        "pocket": Sketch(plane="XY", offset="(thickness - pocket_depth)", entities=[
            CircleEntity(center=["0", "0"], radius="pocket_diameter / 2")]),
    }
    operations = [
        ExtrudeOp(id="outer", output="body", sketch="outline", distance="thickness"),
        ExtrudeOp(id="hole_pin", output="hole_tool", sketch="hole", distance="thickness + 2"),
        RepeatOp(id="hole_grid", input="hole_tool", output="hole_tools",
                 linear=LinearRepeat(x_pitch="hole_dx", x_count=2, y_pitch="hole_dy", y_count=2)),
        ExtrudeOp(id="pocket_pin", output="pocket_tool", sketch="pocket", distance="pocket_depth"),
        CutOp(id="holes", target="body", tool="hole_tools", output="body_cut"),
        CutOp(id="pocket", target="body_cut", tool="pocket_tool", output="finished"),
    ]
    proposal.plan = GeneralPlan(
        version=1, unit="mm",
        source=SourceRef(kind="drawing", ref=str(drawing), sha256=meanings.source_sha256),
        parameters=parameters, sketches=sketches, operations=operations, result="finished",
        assumptions=[
            "Ölçüler basılı değerlerdir; geometri yalnız doğrulama ve yerleşim için ölçüldü.",
            f"Kesit görünüşündeki iki mesafe ölçüsünden büyüğü ({_round(thickness)} mm) kalınlık, "
            f"küçüğü ({_round(pocket_depth)} mm) cep derinliği olarak okundu.",
            "Delik yerleşimi 2x2 ızgara ve merkezî cep; ölçülen merkez sapması "
            f"{_round(centre_offset_mm)} mm.",
            f"Cepten deliklerin geçtiği varsayılmadı; delikler {_round(thickness)} mm boyunca "
            "tam geçiyor.",
        ],
        expect=Expect(
            bbox=["width", "height", "thickness"],
            volume=("area * thickness - hole_count * pi * (hole_diameter / 2) ** 2 * thickness "
                    "- pi * (pocket_diameter / 2) ** 2 * pocket_depth"),
        ),
    )
    proposal.status = "proposed"
    proposal.notes = [
        f"kontur {len(loop_ids)} ilkelden kuruldu (en büyük kapalı döngü)",
        f"delikler: {sorted(hole_matches)}; cep: {pocket_span.claim.matched_geometry}",
        "genel plan doğrudan `build-general` ile kurulabilir",
    ]
    return proposal


__all__ = ["Proposal", "propose_general", "Unsupported"]
