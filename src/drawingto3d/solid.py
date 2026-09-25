"""Build a STEP solid from a resolved feature graph. The drawing is not re-read here."""

from __future__ import annotations

from pathlib import Path

from build123d import (
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Line,
    Plane,
    Pos,
    RegularPolygon,
    ThreePointArc,
    export_step,
    export_stl,
    make_face,
    revolve,
)

from drawingto3d.schema import Contour, FeatureGraph, HexPocket, HoleSpec, PocketSpec


def _add_contour_edges(contour: Contour) -> None:
    pts = [(point.x, point.y) for point in contour.points]
    indexed = [arc for arc in contour.arcs if arc.get("kind") == "three" and "start" in arc]
    if len(pts) == 6 and any(arc.get("kind") == "three" and "start" not in arc for arc in contour.arcs):
        ThreePointArc(pts[0], pts[1], pts[2])
        Line(pts[2], pts[3])
        ThreePointArc(pts[3], pts[4], pts[5])
        Line(pts[5], pts[0])
        return
    if not indexed:
        for index in range(len(pts)):
            Line(pts[index], pts[(index + 1) % len(pts)])
        return
    span_at = {arc["start"]: arc for arc in indexed}
    cursor = 0
    count = len(pts)
    for _ in range(count + 2):
        if cursor >= count:
            break
        if cursor in span_at:
            arc = span_at[cursor]
            ThreePointArc(pts[arc["start"]], pts[arc["through"]], pts[arc["end"]])
            end = arc["end"]
            nxt = end + 1
            if nxt < count:
                Line(pts[end], pts[nxt])
                cursor = nxt
            else:
                Line(pts[end], pts[0])
                break
        else:
            nxt = cursor + 1
            if nxt == count:
                Line(pts[cursor], pts[0])
                break
            Line(pts[cursor], pts[nxt])
            cursor = nxt


def _prism(contour: Contour, plane: Plane, amount: float, both: bool = False):
    with BuildPart() as part:
        with BuildSketch(plane):
            with BuildLine():
                _add_contour_edges(contour)
            make_face()
        extrude_amount = amount
        from build123d import extrude

        extrude(amount=extrude_amount, both=both)
    return part.part


def _cut_hole(part, hole: HoleSpec, top_z: float):
    if hole.depth is None:
        tool = Pos(hole.cx, hole.cy, top_z / 2.0) * Cylinder(hole.diameter / 2.0, top_z + 2.0)
    else:
        tool = Pos(hole.cx, hole.cy, top_z - hole.depth / 2.0) * Cylinder(
            hole.diameter / 2.0, hole.depth + 0.2
        )
    return part - tool


def _cut_pocket(part, pocket: PocketSpec, top_z: float):
    contour = Contour(name="pocket", points=pocket.points)
    tool = _prism(contour, Plane.XY.offset(top_z), -(pocket.depth + 0.1))
    return part - tool


def _cut_hex(part, pocket: HexPocket, top_z: float):
    with BuildPart() as tool:
        with BuildSketch(Plane.XY.offset(top_z)):
            RegularPolygon(
                radius=pocket.across_flats / 2.0,
                side_count=6,
                major_radius=False,
                rotation=30,
            )
        from build123d import extrude

        extrude(amount=-(pocket.depth + 0.1))
    return part - Pos(pocket.cx, pocket.cy, 0) * tool.part


def build_part(graph: FeatureGraph):
    if graph.strategy == "plan_section":
        if graph.plan is None or graph.section is None:
            raise ValueError("plan ve kesit konturu gerekli")
        zs = [point.y for point in graph.section.points]
        top_z = max(zs)
        bot_z = min(zs)
        plan_solid = _prism(graph.plan, Plane.XY.offset(bot_z), top_z - bot_z + 2.0)
        section_solid = _prism(graph.section, Plane.XZ, 80.0, both=True)
        solid = plan_solid & section_solid
        for hole in graph.holes:
            solid = _cut_hole(solid, hole, top_z)
        if graph.hex_pocket is not None:
            solid = _cut_hex(solid, graph.hex_pocket, top_z)
        return solid
    if graph.strategy == "extrude":
        if graph.plan is None or graph.thickness is None:
            raise ValueError("profil ve kalınlık gerekli")
        solid = _prism(graph.plan, Plane.XY, graph.thickness)
        top_z = graph.thickness
        for hole in graph.holes:
            solid = _cut_hole(solid, hole, top_z)
        for pocket in graph.pockets:
            solid = _cut_pocket(solid, pocket, top_z)
        if graph.section is not None:
            section_solid = _prism(graph.section, Plane.XZ, 80.0, both=True)
            solid = solid & section_solid
        return solid
    if graph.strategy == "revolve":
        if graph.section is None:
            raise ValueError("kesit gerekli")
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _add_contour_edges(graph.section)
                make_face()
            revolve(axis=Axis.X)
        return part.part
    raise ValueError(f"bilinmeyen strateji: {graph.strategy}")


def write_step(part, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(part, str(path))


def write_stl(part, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(path), tolerance=0.05, angular_tolerance=0.2)


def _solid_of(part):
    solids = part.solids()
    if not solids:
        raise ValueError("katı oluşmadı")
    return solids[0]


def measured_length(part) -> float:
    box = part.bounding_box()
    return float(box.max.X - box.min.X)


def half_width_at(part, x: float, z: float) -> float:
    solid = _solid_of(part)
    low, high = 0.0, 40.0
    for _ in range(24):
        mid = (low + high) / 2.0
        if solid.is_inside((x, mid, z)) or solid.is_inside((x, -mid, z)):
            low = mid
        else:
            high = mid
    return low


def contains(part, point: tuple[float, float, float]) -> bool:
    return bool(_solid_of(part).is_inside(point))


def box_step(path: Path, size: float = 10.0) -> None:
    write_step(Box(size, size, size), path)
