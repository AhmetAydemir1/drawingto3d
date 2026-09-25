"""General solid-modelling verbs for the CadQuery runner. Runs inside .venv-cad only.

Every function returns a cq.Workplane holding one solid and checks its inputs.
Error messages are short English sentences meant for the code model to read.
Conventions: a named plane ("XY", "XZ", "YZ", ...) is centred on the origin;
extrusions go along the plane normal, starting at the plane. Plates and tubes
remember their two end faces so `attach` can stack parts without coordinates.
"""

from __future__ import annotations

import math

import cadquery as cq

PLANES = ("XY", "YZ", "XZ", "YX", "ZY", "ZX")
Vec = tuple[float, float, float]
End = tuple[Vec, Vec]  # (face centre, outward normal)


def plate(width: float, height: float, thickness: float, corner_radius: float = 0, plane: str = "XY") -> cq.Workplane:
    """Rectangular plate centred on the plane origin, extruded `thickness` along the plane normal; ends: 'start' = bottom face, 'end' = top face."""
    _positive("plate", width=width, height=height, thickness=thickness)
    _non_negative("plate", corner_radius=corner_radius)
    if corner_radius * 2 >= min(width, height):
        raise ValueError("plate: corner_radius must be smaller than half the shortest side")
    wp = _wp(plane, "plate")
    shape = wp.rect(width, height).extrude(thickness)
    if corner_radius > 0:
        shape = shape.edges(_normal_selector(plane)).fillet(corner_radius)
    return _with_ends(shape, _straight_ends(wp, thickness))


def rect_points(dx: float, dy: float | None = None) -> list[tuple[float, float]]:
    """Four corner points of a centred rectangle with sides dx, dy; e.g. hole spacing 260 -> (+-130, +-130)."""
    dy = dx if dy is None else dy
    _positive("rect_points", dx=dx, dy=dy)
    return [(-dx / 2, -dy / 2), (dx / 2, -dy / 2), (dx / 2, dy / 2), (-dx / 2, dy / 2)]


def holes(
    part: cq.Workplane,
    positions: list[tuple[float, float]],
    diameter: float,
    depth: float | None = None,
    counterbore: tuple[float, float] | None = None,
    plane: str = "XY",
    counterbore_face: str = "top",
) -> cq.Workplane:
    """Drill `part` (a solid from an earlier geo call) along the plane normal at (x, y) positions; through when depth is None; counterbore=(diameter, depth) on the 'top' (max) or 'bottom' (min) face."""
    _positive("holes", diameter=diameter)
    if not positions:
        raise ValueError("holes: positions must hold at least one (x, y) pair")
    points = [(float(x), float(y)) for x, y in positions]
    wp = _wp(plane, "holes")
    low, high = _extent_along(part, wp.plane.zDir)
    if depth is None:
        tool = wp.workplane(offset=low - 1).pushPoints(points).circle(diameter / 2).extrude(high - low + 2)
    else:
        _positive("holes", depth=depth)
        start = high - depth if counterbore_face == "top" else low - 1
        tool = wp.workplane(offset=start).pushPoints(points).circle(diameter / 2).extrude(depth + 1)
    result = part.cut(tool)
    if counterbore is not None:
        cb_diameter, cb_depth = counterbore
        _positive("holes", counterbore_diameter=cb_diameter, counterbore_depth=cb_depth)
        if cb_diameter <= diameter:
            raise ValueError("holes: counterbore diameter must be larger than the hole diameter")
        if counterbore_face == "top":
            start = high - cb_depth
        elif counterbore_face == "bottom":
            start = low - 1
        else:
            raise ValueError("holes: counterbore_face must be 'top' or 'bottom'")
        cb = wp.workplane(offset=start).pushPoints(points).circle(cb_diameter / 2).extrude(cb_depth + 1)
        result = result.cut(cb)
    return _with_ends(_one_solid(result, "holes"), _ends(part))


def ring_extrude(outer_d: float, inner_d: float, length: float, plane: str = "XY") -> cq.Workplane:
    """Straight tube: annulus centred on the plane origin, extruded `length` along the plane normal; ends: 'start' at the plane, 'end' after `length`."""
    _ring("ring_extrude", outer_d, inner_d)
    _positive("ring_extrude", length=length)
    wp = _wp(plane, "ring_extrude")
    shape = wp.circle(outer_d / 2).circle(inner_d / 2).extrude(length)
    return _with_ends(shape, _straight_ends(wp, length))


def ring_revolve(outer_d: float, inner_d: float, bend_radius: float, angle: float = 90, plane: str = "XY") -> cq.Workplane:
    """Bent tube: the annulus at the plane origin leaves along the plane normal and bends toward local -X around an axis `bend_radius` away; ends: 'start' at the origin, 'end' after the bend (for XY and 90: centre (-bend_radius, 0, bend_radius) facing -X)."""
    _ring("ring_revolve", outer_d, inner_d)
    _positive("ring_revolve", bend_radius=bend_radius, angle=angle)
    if angle > 360:
        raise ValueError("ring_revolve: angle must be at most 360")
    if bend_radius <= outer_d / 2:
        raise ValueError("ring_revolve: bend_radius must be larger than outer_d / 2")
    wp = _wp(plane, "ring_revolve")
    shape = (
        wp.circle(outer_d / 2)
        .circle(inner_d / 2)
        .revolve(angle, (-bend_radius, 0, 0), (-bend_radius, -1, 0))
    )
    origin = _tuple(wp.plane.origin)
    normal = _tuple(wp.plane.zDir)
    axis_point = _add(origin, _scale(_tuple(wp.plane.xDir), -bend_radius))
    axis_dir = _scale(_tuple(wp.plane.yDir), -1)
    end_centre = _add(axis_point, _rotate(_sub(origin, axis_point), axis_dir, angle))
    end_normal = _rotate(normal, axis_dir, angle)
    return _with_ends(_one_solid(shape, "ring_revolve"), [(origin, _scale(normal, -1)), (end_centre, end_normal)])


def extrude_profile(points: list[tuple[float, float]], thickness: float, plane: str = "XY") -> cq.Workplane:
    """Closed polygon through (x, y) plane points, extruded `thickness` along the plane normal."""
    _positive("extrude_profile", thickness=thickness)
    wp = _wp(plane, "extrude_profile")
    shape = _one_solid(_polygon(wp, points, "extrude_profile").extrude(thickness), "extrude_profile")
    return _with_ends(shape, _straight_ends(wp, thickness))


def revolve_profile(points: list[tuple[float, float]], angle: float = 360, plane: str = "XZ") -> cq.Workplane:
    """Closed polygon of (radius, height) points revolved about the plane's local Y axis through the origin. x must be >= 0."""
    _positive("revolve_profile", angle=angle)
    if any(x < 0 for x, _y in points):
        raise ValueError("revolve_profile: every x (radius) must be >= 0")
    wp = _wp(plane, "revolve_profile")
    return _one_solid(_polygon(wp, points, "revolve_profile").revolve(angle, (0, 0, 0), (0, 1, 0)), "revolve_profile")


def attach(part: cq.Workplane, base: cq.Workplane, end: str = "end") -> cq.Workplane:
    """Move `part` so its 'start' face sits flat on the chosen end face ('start' or 'end') of `base`, pointing away from base. Works on plates and tubes, not on fused solids."""
    base_ends = _ends(_check_shape(base, "attach"))
    part_ends = _ends(_check_shape(part, "attach"))
    if not base_ends:
        raise ValueError("attach: base has no end faces; attach to a plate or tube, not to a fused or revolved solid")
    if not part_ends:
        raise ValueError("attach: part has no start face; attach a plate or tube")
    if end not in {"start", "end"}:
        raise ValueError("attach: end must be 'start' or 'end'")
    centre, normal = base_ends[0] if end == "start" else base_ends[-1]
    part_centre, part_normal = part_ends[0]
    axis, degrees = _rotation_between(part_normal, _scale(normal, -1))
    moved = part
    ends = list(part_ends)
    if degrees:
        moved = moved.rotate((0, 0, 0), axis, degrees)
        ends = [(_rotate(c, axis, degrees), _rotate(n, axis, degrees)) for c, n in ends]
        part_centre = _rotate(part_centre, axis, degrees)
    shift = _sub(centre, part_centre)
    moved = moved.translate(shift)
    return _with_ends(moved, [(_add(c, shift), n) for c, n in ends])


def place(part: cq.Workplane, x: float = 0, y: float = 0, z: float = 0, rot: tuple[str, float] | None = None) -> cq.Workplane:
    """Move `part` by (x, y, z); rot=("Z", 90) first rotates about that world axis through the origin."""
    result = _check_shape(part, "place")
    ends = _ends(part)
    if rot is not None:
        axis, degrees = rot
        axes = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}
        if str(axis).upper() not in axes:
            raise ValueError("place: rot axis must be 'X', 'Y' or 'Z'")
        unit = axes[str(axis).upper()]
        result = result.rotate((0, 0, 0), unit, float(degrees))
        ends = [(_rotate(c, unit, float(degrees)), _rotate(n, unit, float(degrees))) for c, n in ends]
    shift = (float(x), float(y), float(z))
    return _with_ends(result.translate(shift), [(_add(c, shift), n) for c, n in ends])


def fuse(*parts: cq.Workplane) -> cq.Workplane:
    """Union of touching parts into one solid. Call it once, at the end."""
    if len(parts) < 1:
        raise ValueError("fuse: give at least one part")
    result = _check_shape(parts[0], "fuse")
    for item in parts[1:]:
        result = result.union(_check_shape(item, "fuse"))
    return _one_solid(result, "fuse", "the parts do not touch; use geo.attach to put them end to end")


def cut(part: cq.Workplane, *tools: cq.Workplane) -> cq.Workplane:
    """Subtract tool solids from `part`."""
    result = _check_shape(part, "cut")
    for tool in tools:
        result = result.cut(_check_shape(tool, "cut"))
    return _with_ends(_one_solid(result, "cut", "the cut split the part in two"), _ends(part))


def chamfer_edges(part: cq.Workplane, size: float, selector: str) -> cq.Workplane:
    """Chamfer the edges of `part` picked by a CadQuery selector such as '>Z', '<X' or '|Z'."""
    _positive("chamfer_edges", size=size)
    try:
        result = _check_shape(part, "chamfer_edges").edges(selector).chamfer(size)
    except Exception as exc:  # noqa: BLE001 - OCC raises plain Exceptions
        raise ValueError(f"chamfer_edges: selector {selector!r} with size {size} failed; use a smaller size or fewer edges") from exc
    return _with_ends(result, _ends(part))


def fillet_edges(part: cq.Workplane, radius: float, selector: str) -> cq.Workplane:
    """Round the edges of `part` picked by a CadQuery selector such as '>Z', '<X' or '|Z'."""
    _positive("fillet_edges", radius=radius)
    try:
        result = _check_shape(part, "fillet_edges").edges(selector).fillet(radius)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"fillet_edges: selector {selector!r} with radius {radius} failed; use a smaller radius or fewer edges") from exc
    return _with_ends(result, _ends(part))


def _wp(plane, name: str) -> cq.Workplane:
    if isinstance(plane, cq.Workplane):
        return cq.Workplane(plane.plane)
    if isinstance(plane, cq.Plane):
        return cq.Workplane(plane)
    if not isinstance(plane, str) or plane.upper() not in PLANES:
        raise ValueError(f"{name}: plane must be one of {', '.join(PLANES)}")
    return cq.Workplane(plane.upper())


def _normal_selector(plane) -> str:
    z = _wp(plane, "plate").plane.zDir
    for axis, vec in (("X", (1, 0, 0)), ("Y", (0, 1, 0)), ("Z", (0, 0, 1))):
        if abs(abs(z.dot(cq.Vector(*vec))) - 1) < 1e-6:
            return "|" + axis
    return "|Z"


def _polygon(wp: cq.Workplane, points, name: str) -> cq.Workplane:
    if len(points) < 3:
        raise ValueError(f"{name}: give at least three (x, y) points")
    pts = [(float(x), float(y)) for x, y in points]
    if math.dist(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]
    return wp.polyline(pts).close()


def _extent_along(part: cq.Workplane, direction: cq.Vector) -> tuple[float, float]:
    bb = _check_shape(part, "holes").val().BoundingBox()
    corners = [
        cq.Vector(x, y, z)
        for x in (bb.xmin, bb.xmax)
        for y in (bb.ymin, bb.ymax)
        for z in (bb.zmin, bb.zmax)
    ]
    values = [corner.dot(direction) for corner in corners]
    return min(values), max(values)


def _check_shape(part, name: str) -> cq.Workplane:
    if not isinstance(part, cq.Workplane) or not part.solids().vals():
        raise ValueError(
            f"{name}: the part argument must be a solid returned by an earlier geo call such as geo.plate(...), "
            f"got {type(part).__name__} {part!r}"
        )
    return part


def _one_solid(shape: cq.Workplane, name: str, hint: str = "") -> cq.Workplane:
    count = len(shape.solids().vals())
    if count != 1:
        tail = f"; {hint}" if hint else ""
        raise ValueError(f"{name}: result has {count} solids, expected one{tail}")
    return shape


def _ring(name: str, outer_d: float, inner_d: float) -> None:
    _positive(name, outer_d=outer_d, inner_d=inner_d)
    if inner_d >= outer_d:
        raise ValueError(f"{name}: inner_d must be smaller than outer_d")


def _positive(name: str, **values: float) -> None:
    for key, value in values.items():
        if not isinstance(value, (int, float)) or not value > 0:
            raise ValueError(f"{name}: {key} must be a positive number, got {value!r}")


def _non_negative(name: str, **values: float) -> None:
    for key, value in values.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{name}: {key} must be zero or positive, got {value!r}")


# End-face bookkeeping. Kept as plain tuples so it survives without OCC objects.


def _ends(part) -> list[End]:
    return list(getattr(part, "_geo_ends", []))


def _with_ends(part: cq.Workplane, ends: list[End]) -> cq.Workplane:
    part._geo_ends = list(ends)  # noqa: SLF001 - our own marker on the returned object
    return part


def _straight_ends(wp: cq.Workplane, length: float) -> list[End]:
    origin = _tuple(wp.plane.origin)
    normal = _tuple(wp.plane.zDir)
    return [(origin, _scale(normal, -1)), (_add(origin, _scale(normal, length)), normal)]


def _tuple(vector: cq.Vector) -> Vec:
    return (float(vector.x), float(vector.y), float(vector.z))


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vec, k: float) -> Vec:
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a: Vec) -> Vec:
    length = math.sqrt(_dot(a, a))
    return _scale(a, 1 / length) if length > 1e-12 else a


def _rotate(v: Vec, axis: Vec, degrees: float) -> Vec:
    """Rodrigues rotation, right-handed about `axis` through the origin, matching cq.Workplane.rotate."""
    k = _unit(axis)
    theta = math.radians(degrees)
    cos, sin = math.cos(theta), math.sin(theta)
    term1 = _scale(v, cos)
    term2 = _scale(_cross(k, v), sin)
    term3 = _scale(k, _dot(k, v) * (1 - cos))
    return _add(_add(term1, term2), term3)


def _rotation_between(a: Vec, b: Vec) -> tuple[Vec, float]:
    """Axis and angle that turn unit vector a onto unit vector b."""
    a, b = _unit(a), _unit(b)
    d = max(-1.0, min(1.0, _dot(a, b)))
    if d > 1 - 1e-9:
        return (0.0, 0.0, 1.0), 0.0
    if d < -1 + 1e-9:
        helper = (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0)
        return _unit(_cross(a, helper)), 180.0
    return _unit(_cross(a, b)), math.degrees(math.acos(d))
