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
ARC_SAMPLES = 12
CHECK_RELATIVE = 0.01
CHECK_ABSOLUTE_MM = 0.5
FRAME_COVERAGE = 0.80


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


def _loops(lines: dict[str, tuple[np.ndarray, np.ndarray]],
           arcs: dict[str, tuple[np.ndarray, float, float, float]]) -> list[dict]:
    """Chain lines and arcs into closed loops by endpoint proximity; biggest first."""
    segments: list[tuple[str, np.ndarray, np.ndarray, dict]] = []
    for geometry_id, (start, end) in lines.items():
        segments.append((geometry_id, start, end, {"kind": "line"}))
    for geometry_id, (centre, radius, start_degrees, end_degrees) in arcs.items():
        points = _arc_points(centre, radius, start_degrees, end_degrees, 2)
        segments.append((geometry_id, points[0], points[-1],
                         {"kind": "arc", "centre": centre, "radius": radius,
                          "start_degrees": start_degrees, "end_degrees": end_degrees}))
    loops: list[dict] = []
    consumed: set[int] = set()
    for index, (geometry_id, start, end, meta) in enumerate(segments):
        if index in consumed:
            continue
        chain = [(geometry_id, start, end, meta)]
        consumed.add(index)
        tail = end
        while True:
            found = None
            for other_index, (other_id, other_start, other_end, other_meta) in enumerate(segments):
                if other_index in consumed:
                    continue
                if float(np.linalg.norm(other_start - tail)) <= LOOP_TOLERANCE_PX:
                    found = (other_index, other_id, other_start, other_end, other_meta, other_end)
                elif float(np.linalg.norm(other_end - tail)) <= LOOP_TOLERANCE_PX:
                    found = (other_index, other_id, other_end, other_start, other_meta, other_start)
                if found:
                    break
            if found is None:
                break
            other_index, other_id, near, far, other_meta, new_tail = found
            consumed.add(other_index)
            chain.append((other_id, near, far, other_meta))
            tail = new_tail
            if float(np.linalg.norm(tail - start)) <= LOOP_TOLERANCE_PX and len(chain) >= 3:
                loops.append({"entities": chain, "area_px": _loop_area(chain)})
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

    loops = _loops(lines, arcs)
    if not loops:
        proposal.refusals.append("kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor)")
        return proposal
    frame_indexes = (_frame_loops(loops, observations.frame.width, observations.frame.height)
                     if observations.frame else set())
    if frame_indexes:
        proposal.notes.append(f"sayfa çerçevesi atlandı ({len(frame_indexes)} döngü)")
    part_loops = [loop for index, loop in enumerate(loops) if index not in frame_indexes]
    if not part_loops:
        proposal.refusals.append("kapalı dış kontur bulunamadı (sayfa çerçevesi dışında döngü yok)")
        return proposal
    outline = part_loops[0]
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
