"""Is the final line/arc boundary a valid closed contour? (PLAN §26.4-A)

This audit runs on the geometry that would go to CAD — the traced profile's own edges in sheet pixels — and
answers the questions PLAN §26.3 says were being conflated: the *final* closure error (not `join_max_px`,
which is the gap measured *before* a join), zero-length edges, duplicate/overlapping edges, and
self-intersections, distinguished by the kinds of the pair involved (line-line, line-arc, arc-arc) and by
whether the pair is a neighbouring pair that is *meant* to share an endpoint. Every issue carries a position
in sheet pixels so the interface can mark the bad region on the drawing.

Nothing here knows a file name, a folder or an example: it is the same rule for every sheet.
"""
from __future__ import annotations

import math

import numpy as np

TOLERANCE_PX = 0.5          # closure: a join may miss by this much (the drawing's own uncertainty)
SUPPORT_TOLERANCE_PX = 0.35  # support equality: numeric, *not* the closure tolerance (P02-b.2). Two circles whose
                            # radii differ by 1 px are two circles, not one support (F08: R100/R99 must pass).
STROKE_TOLERANCE_PX = 1.0   # two nearly-parallel line strokes within one sheet pixel are one stroke (F11)
SAMPLES_PER_EDGE = 32       # an arc is checked as its own polyline; the sampled endpoints must land on start/end
# §7.7: the checks below work on those sampled polylines. That is a *bounded approximation*, not an exact
# curve intersection test: a crossing narrower than one sample step can slip through, so this audit may
# under-report; it is never presented as proof that no self-intersection exists.


def arc_page_ends(center, radius: float, a_degrees: float, b_degrees: float):
    """Both ends of an arc in *sheet* pixels, from its canonical definition (PLAN P02-a.1).

    The canonical pair (`a`, `b`) is stated in CAD's Y-up frame; the sheet is Y-down, so a page-space angle
    is the negation of its canonical one. This is the single canonical definition on the sheet side; the CAD
    profile builder is *checked against it* (its own module must stay loadable on its own by the CAD child
    process, so it cannot import this one). Deriving an end from a stored point instead would let that point
    and the canonical pair describe different halves of one circle — the audit's F07.
    """
    start = (center[0] + radius * math.cos(math.radians(-a_degrees)),
             center[1] + radius * math.sin(math.radians(-a_degrees)))
    end = (center[0] + radius * math.cos(math.radians(-b_degrees)),
           center[1] + radius * math.sin(math.radians(-b_degrees)))
    return start, end


def _arc_points(edge: dict, samples: int) -> np.ndarray:
    """The arc's own polyline, built from its **canonical** definition (PLAN P02-a.1/P02-a.2).

    The chain runs from the canonical start angle through the canonical signed sweep; the stored
    `start`/`end` are never used to derive it, because a stored point can describe the opposite half of the
    circle from what `a`/`b` say (the audit's F07) — the caller compares the two instead.
    """
    centre = np.asarray(edge["center"], dtype=float)
    radius = float(edge["radius"])
    page_start = math.radians(-float(edge["a"]))                    # sheet is Y-down: page = -canonical
    sweep = math.radians(-(float(edge["b"]) - float(edge["a"])))     # signed sweep, same conversion
    steps = np.linspace(0.0, 1.0, max(2, samples))[:, None]
    angles = page_start + sweep * steps
    return centre + radius * np.column_stack((np.cos(angles), np.sin(angles)))


def edge_points(edge: dict, samples: int = SAMPLES_PER_EDGE) -> np.ndarray:
    """Any edge as a point chain from its start to its end, in sheet pixels."""
    if edge.get("kind") == "arc" and edge.get("center") is not None:
        return _arc_points(edge, samples)
    return np.array([[float(edge["start"][0]), float(edge["start"][1])],
                     [float(edge["end"][0]), float(edge["end"][1])]], dtype=float)


def _segments(points: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _cross(a, b, c) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segment_intersection(p1, p2, p3, p4) -> np.ndarray | None:
    """Where two finite segments meet, or None — collinear overlap is the overlap check's business.

    Decided parametrically, never by the sign of a cross product: with a cross product of exactly zero the
    old sign test answered one way for a segment and the other way for its reflection (F10). A meeting at a
    segment's end counts here; whether that end is a legitimate joint is decided by the pair's context
    (a neighbouring pair's own joint is skipped, a non-neighbour touch is refused).
    """
    p1, p2, p3, p4 = np.asarray(p1, float), np.asarray(p2, float), np.asarray(p3, float), np.asarray(p4, float)
    denominator = (p1[0] - p2[0]) * (p3[1] - p4[1]) - (p1[1] - p2[1]) * (p3[0] - p4[0])
    if abs(denominator) < 1e-12:
        return None                                    # parallel or collinear: no single meeting point
    t = ((p1[0] - p3[0]) * (p3[1] - p4[1]) - (p1[1] - p3[1]) * (p3[0] - p4[0])) / denominator
    u = ((p1[0] - p3[0]) * (p1[1] - p2[1]) - (p1[1] - p3[1]) * (p1[0] - p2[0])) / denominator
    if not (-1e-9 <= t <= 1.0 + 1e-9 and -1e-9 <= u <= 1.0 + 1e-9):
        return None
    return p1 + max(0.0, min(1.0, t)) * (p2 - p1)


def _angle_inside(angle: float, phi: float, sweep: float, epsilon: float) -> bool:
    """Whether `angle` lies strictly inside the arc's span, with `epsilon` carved off both ends."""
    two_pi = 2.0 * math.pi
    if sweep >= 0:
        travelled = (angle - phi) % two_pi
    else:
        travelled = (phi - angle) % two_pi
    return epsilon < travelled < abs(sweep) - epsilon


def _point_on_interior(point, edge: dict, tolerance_px: float) -> bool:
    """Whether a point lies on the edge's *interior* — distance-based, so mirroring cannot change it."""
    point = np.asarray(point, float)
    if edge.get("kind") == "arc" and edge.get("center") is not None:
        centre = np.asarray(edge["center"], float)
        radius = float(edge["radius"])
        offset = point - centre
        if abs(float(np.linalg.norm(offset)) - radius) > tolerance_px:
            return False
        phi, sweep = _arc_span(edge)
        epsilon = tolerance_px / max(radius, 1e-9)
        return _angle_inside(math.atan2(offset[1], offset[0]), phi, sweep, epsilon)
    start = np.asarray(edge["start"], float)
    end = np.asarray(edge["end"], float)
    direction = end - start
    length = float(np.linalg.norm(direction))
    if length < 1e-9:
        return False
    unit = direction / length
    along = float((point - start) @ unit)
    if not (tolerance_px < along < length - tolerance_px):
        return False
    return abs(float(unit[0] * (point - start)[1] - unit[1] * (point - start)[0])) <= tolerance_px


def _line_arc_intersections(first: dict, second: dict, tolerance_px: float) -> list[np.ndarray]:
    """Line vs circle, solved analytically, then filtered by the segment bounds and the arc's own span."""
    line, arc = first, second
    start = np.asarray(line["start"], float)
    end = np.asarray(line["end"], float)
    centre = np.asarray(arc["center"], float)
    radius = float(arc["radius"])
    direction = end - start
    a = float(direction @ direction)
    if a < 1e-12:
        return []
    b = 2.0 * float(direction @ (start - centre))
    c = float((start - centre) @ (start - centre)) - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return []
    root = math.sqrt(discriminant)
    points = []
    for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
        if not (-1e-9 <= t <= 1.0 + 1e-9):
            continue
        point = start + max(0.0, min(1.0, t)) * direction
        phi, sweep = _arc_span(arc)
        offset = point - centre
        epsilon = tolerance_px / max(radius, 1e-9)
        if _angle_inside(math.atan2(offset[1], offset[0]), phi, sweep, epsilon):
            points.append(point)
    return points


def _arc_arc_intersections(first: dict, second: dict, tolerance_px: float) -> list[np.ndarray]:
    """Circle vs circle analytically; a shared support (duplicates) is the overlap check's business."""
    centre_a = np.asarray(first["center"], float)
    centre_b = np.asarray(second["center"], float)
    radius_a, radius_b = float(first["radius"]), float(second["radius"])
    separation = centre_b - centre_a
    distance = float(np.linalg.norm(separation))
    if distance < 1e-9 or distance > radius_a + radius_b or distance < abs(radius_a - radius_b):
        return []
    along = (radius_a * radius_a - radius_b * radius_b + distance * distance) / (2.0 * distance)
    height_squared = radius_a * radius_a - along * along
    if height_squared < 0.0:
        return []
    base = centre_a + along * separation / distance
    if height_squared <= 1e-18:
        candidates = [base]
    else:
        height = math.sqrt(height_squared)
        normal = np.array([-separation[1], separation[0]]) / distance
        candidates = [base + height * normal, base - height * normal]
    points = []
    for point in candidates:
        inside = True
        for edge in (first, second):
            centre = np.asarray(edge["center"], float)
            radius = float(edge["radius"])
            phi, sweep = _arc_span(edge)
            offset = point - centre
            epsilon = tolerance_px / max(radius, 1e-9)
            if not _angle_inside(math.atan2(offset[1], offset[0]), phi, sweep, epsilon):
                inside = False
        if inside:
            points.append(point)
    return points


def _pair_intersections(first: dict, second: dict, tolerance_px: float) -> list[np.ndarray]:
    """Every point where two edges meet, analytically (PLAN P02-c.1) — never by sampling the curves.

    Line-line keeps the finite-segment test; line-arc solves the quadratic; arc-arc solves the two-circle
    intersection. All three are exact up to floating point, so the only tolerance left is the sheet-level
    "same point" tolerance used to decide what counts as an endpoint rather than an interior crossing.
    """
    first_arc = first.get("kind") == "arc" and first.get("center") is not None
    second_arc = second.get("kind") == "arc" and second.get("center") is not None
    if first_arc and second_arc:
        return _arc_arc_intersections(first, second, tolerance_px)
    if first_arc:
        return _line_arc_intersections(second, first, tolerance_px)
    if second_arc:
        return _line_arc_intersections(first, second, tolerance_px)
    point = _segment_intersection(np.asarray(first["start"], float), np.asarray(first["end"], float),
                                  np.asarray(second["start"], float), np.asarray(second["end"], float))
    return [] if point is None else [point]


def _length(edge: dict, points: np.ndarray) -> float:
    if edge.get("kind") == "arc":
        return float(abs(float(edge["b"]) - float(edge["a"])) * math.pi / 180.0 * float(edge["radius"]))
    return float(np.linalg.norm(points[-1] - points[0]))


def _same_support(first: dict, second: dict, tolerance_px: float) -> bool:
    """Whether two edges of one kind ride the same support (a duplicated or overlapped edge)."""
    if first.get("kind") != second.get("kind"):
        return False
    if first["kind"] == "arc":
        if first.get("center") is None or second.get("center") is None:
            return False
        centres = np.linalg.norm(np.asarray(first["center"], float) - np.asarray(second["center"], float))
        radii = abs(float(first["radius"]) - float(second["radius"]))
        # P02-b.1: the old 2%-of-radius rule called R100 and R99 one support. Support equality is numeric.
        return bool(centres <= SUPPORT_TOLERANCE_PX and radii <= SUPPORT_TOLERANCE_PX)
    a1, a2 = np.asarray(first["start"], float), np.asarray(first["end"], float)
    b1, b2 = np.asarray(second["start"], float), np.asarray(second["end"], float)
    direction_a, direction_b = a2 - a1, b2 - b1
    length_a, length_b = float(np.linalg.norm(direction_a)), float(np.linalg.norm(direction_b))
    if length_a < 1e-9 or length_b < 1e-9:
        return False
    unit_a, unit_b = direction_a / length_a, direction_b / length_b
    cross = abs(float(unit_a[0] * unit_b[1] - unit_a[1] * unit_b[0]))
    if cross > 1e-3:                                   # not parallel within 0.057°
        return False
    offset = abs(float(unit_a[0] * (b1 - a1)[1] - unit_a[1] * (b1 - a1)[0]))  # b1's distance from a's line
    # P02-b.5: a stroke drawn forward and back 0.8 px apart is one line, not two — the closure tolerance is
    # the wrong gate for this (the two strokes are separate geometry at closure scale but one line at ink
    # scale). Measured against the ink scale, where one pixel is the resolution of the sheet itself.
    return bool(offset <= max(STROKE_TOLERANCE_PX, tolerance_px))


def _opposite_note(first: dict, second: dict) -> str:
    """Arcs riding the same support in opposite directions are a reversed overlap, not a duplicate."""
    if first.get("kind") == "arc" and second.get("kind") == "arc":
        if _arc_span(first)[1] * _arc_span(second)[1] < 0:
            return " (ters yön)"
    return ""


def _arc_span(edge: dict) -> tuple[float, float]:
    """The arc's canonical start angle in page space and its signed sweep, both in radians."""
    return math.radians(-float(edge["a"])), math.radians(-(float(edge["b"]) - float(edge["a"])))


def _arc_intervals(phi: float, sweep: float) -> list[tuple[float, float]]:
    """The arc's angular span as normalized half-open intervals on [0, 2pi), one per wrap crossing."""
    two_pi = 2.0 * math.pi
    if abs(sweep) >= two_pi:                                   # a full turn covers everything (arcs refuse it)
        return [(0.0, two_pi)]
    if sweep < 0:                                              # travel the same interval backwards
        phi, sweep = phi + sweep, -sweep
    phi %= two_pi
    end = phi + sweep
    if end <= two_pi:
        return [(phi, end)]
    return [(phi, two_pi), (0.0, end - two_pi)]


def angular_overlap_radians(phi_a: float, sweep_a: float, phi_b: float, sweep_b: float) -> float:
    """Exact length of the *intersection* of two angular spans (PLAN P02-b.3).

    Two arcs meeting only at an endpoint share no interval (the endpoints measure zero), so this is 0 where
    a sampled distance test could report a couple of samples. Wrap-around is handled by splitting, so a span
    crossing 0° is compared as two intervals rather than as one broken one.
    """
    total = 0.0
    for start_a, end_a in _arc_intervals(phi_a, sweep_a):
        for start_b, end_b in _arc_intervals(phi_b, sweep_b):
            total += max(0.0, min(end_a, end_b) - max(start_a, start_b))
    return total


def _arc_overlap_extent(first: dict, second: dict) -> bool:
    """Whether two arcs on the same support cover a *stretch* of the same angles.

    Two halves of one circle share the same chord and the same two endpoints, so projecting them onto that
    chord reports "overlap" for what is simply a full circle. The honest test is angular: sample the first
    arc's own sweep and count how much of it also lies on the second arc. Touching endpoints cover only a
    couple of samples; a genuinely shared stretch covers many.
    """
    phi_a, sweep_a = _arc_span(first)
    phi_b, sweep_b = _arc_span(second)
    overlap_radians = angular_overlap_radians(phi_a, sweep_a, phi_b, sweep_b)
    radius = 0.5 * (float(first["radius"]) + float(second["radius"]))
    # A shared stretch counts when it is more than an endpoint touch: at least one sheet pixel of arc length
    # and more than a rounding-level angle (P02-b.3/P02-b.4: "only a common endpoint" is probed separately).
    return bool(overlap_radians > max(0.02, 1.0 / max(radius, 1e-9)))


def _overlap_extent(first: dict, second: dict) -> bool:
    """Two collinear/concentric edges whose spans actually share more than a point."""
    if first.get("kind") == "arc":
        return _arc_overlap_extent(first, second)          # angular spans, never the shared chord
    first_points, second_points = edge_points(first), edge_points(second)
    first_projection = ((first_points - first_points[0]) @ _unit(first_points))
    second_projection = ((second_points - first_points[0]) @ _unit(first_points))
    return float(min(first_projection.max(), second_projection.max())
                 - max(first_projection.min(), second_projection.min())) > 1.0


def _unit(points: np.ndarray) -> np.ndarray:
    direction = points[-1] - points[0]
    length = float(np.linalg.norm(direction))
    return direction / length if length > 1e-9 else np.array([1.0, 0.0])


def audit_contour(edges: list[dict], tolerance_px: float = TOLERANCE_PX,
                  samples: int = SAMPLES_PER_EDGE) -> dict:
    """Everything the drawing's final boundary must pass before CAD sees it.

    Returns `ok` plus each issue with its kind and a sheet-pixel position, so the caller can both stop
    production with a specific reason and mark the bad region on the drawing.
    """
    issues: list[dict] = []
    chains = [edge_points(edge, samples) for edge in edges]
    if not edges:
        return {"ok": False, "closure_px": None, "issues": [{"kind": "empty", "ids": [], "at": None,
                "message": "kontur hiç kenar içermiyor"}]}

    # 1. Closure: every consecutive join, and the wrap from the last edge back to the first.
    closure_px = 0.0
    for index, edge in enumerate(edges):
        following = edges[(index + 1) % len(edges)]
        gap = float(np.linalg.norm(np.asarray(edge["end"], float) - np.asarray(following["start"], float)))
        closure_px = max(closure_px, gap)          # P02: the last join must not overwrite the largest gap
        if gap > tolerance_px:
            issues.append({"kind": "open", "ids": [edge.get("id"), following.get("id")], "at": [round(float(v), 2) for v in edge["end"]],
                           "gap_px": round(gap, 3),
                           "message": f"kontur kapalı değil: {edge.get('id')} ile {following.get('id')} arasında {gap:.2f} px açıklık"})

    # 2. Degenerate edges.
    for index, edge in enumerate(edges):
        length = _length(edge, chains[index])
        if length <= tolerance_px:
            issues.append({"kind": "zero_length", "ids": [edge.get("id")],
                           "at": [round(float(v), 2) for v in edge["start"]],
                           "message": f"{edge.get('id')} sıfır uzunlukta ({length:.3f} px)"})
        if edge.get("kind") == "arc" and edge.get("center") is not None:
            # PLAN P02-a.2/P02-a.5: the canonical pair decides where the arc runs; the stored ends are
            # checked against it, and a sweep of zero or a full turn is not an arc at all (`circle` is).
            sweep_degrees = float(edge["b"]) - float(edge["a"])
            if abs(sweep_degrees) <= 1e-9:
                issues.append({"kind": "arc_zero_sweep", "ids": [edge.get("id")],
                               "at": [round(float(v), 2) for v in edge["start"]],
                               "message": f"{edge.get('id')} yayının süpürmesi sıfır; tam çember `circle` türüdür"})
            elif abs(sweep_degrees) >= 360.0:
                issues.append({"kind": "arc_full_turn", "ids": [edge.get("id")],
                               "at": [round(float(v), 2) for v in edge["start"]],
                               "message": f"{edge.get('id')} yayının süpürmesi {sweep_degrees:g}°: tam tur yay değil, `circle` türüdür"})
            stored_start = np.asarray(edge["start"], float)
            stored_end = np.asarray(edge["end"], float)
            if float(np.linalg.norm(chains[index][0] - stored_start)) > tolerance_px:
                issues.append({"kind": "arc_start_mismatch", "ids": [edge.get("id")],
                               "at": [round(float(v), 2) for v in stored_start],
                               "message": (f"{edge.get('id')} yayının saklanan başlangıcı kanonik tanımıyla tutmuyor "
                                           f"(a={float(edge['a']):g}°, b={float(edge['b']):g}°)")})
            if float(np.linalg.norm(chains[index][-1] - stored_end)) > tolerance_px:
                issues.append({"kind": "arc_end_mismatch", "ids": [edge.get("id")],
                               "at": [round(float(v), 2) for v in stored_end],
                               "message": (f"{edge.get('id')} yayının saklanan ucu kanonik tanımıyla tutmuyor "
                                           f"(a={float(edge['a']):g}°, b={float(edge['b']):g}°)")})

    # 3. Duplicated or overlapping edges — the same support carrying two spans.
    for first_index in range(len(edges)):
        for second_index in range(first_index + 1, len(edges)):
            if _same_support(edges[first_index], edges[second_index], tolerance_px) and \
                    _overlap_extent(edges[first_index], edges[second_index]):
                issues.append({"kind": "overlap",
                               "ids": [edges[first_index].get("id"), edges[second_index].get("id")],
                               "at": [round(float(v), 2) for v in edges[first_index]["start"]],
                               "message": (f"{edges[first_index].get('id')} ile {edges[second_index].get('id')} "
                                           "aynı çizgi üzerinde çakışıyor"
                                           + _opposite_note(edges[first_index], edges[second_index]))})

    # 4. Self-intersections and endpoint touches, decided analytically (PLAN P02-c).
    for first_index in range(len(edges)):
        for second_index in range(first_index + 1, len(edges)):
            neighbours = (second_index == first_index + 1
                          or (first_index == 0 and second_index == len(edges) - 1))
            first_edge, second_edge = edges[first_index], edges[second_index]
            for point in _pair_intersections(first_edge, second_edge, tolerance_px):
                if neighbours:
                    # Item 4 of P02-c: a neighbouring pair is *not* skipped — only their own shared joint is.
                    near_first = min(float(np.linalg.norm(point - np.asarray(first_edge[name], float)))
                                     for name in ("start", "end"))
                    near_second = min(float(np.linalg.norm(point - np.asarray(second_edge[name], float)))
                                      for name in ("start", "end"))
                    if near_first <= tolerance_px and near_second <= tolerance_px:
                        continue
                issues.append({"kind": "self_intersection",
                               "ids": [first_edge.get("id"), second_edge.get("id")],
                               "kinds": [first_edge.get("kind"), second_edge.get("kind")],
                               "at": [round(float(point[0]), 2), round(float(point[1]), 2)],
                               "message": (f"{first_edge.get('id')} ile {second_edge.get('id')} "
                                           f"birbirini kesiyor ({first_edge.get('kind')}-{second_edge.get('kind')})")})
            if not neighbours:
                # P02-c.5: an endpoint resting on a non-neighbour edge is a pinch, not a closed ring. The
                # test is distance-based, so no mirroring or traversal direction can flip the verdict.
                for edge, other in ((first_edge, second_edge), (second_edge, first_edge)):
                    for name in ("start", "end"):
                        if _point_on_interior(edge[name], other, tolerance_px):
                            issues.append({"kind": "endpoint_touch",
                                           "ids": [edge.get("id"), other.get("id")],
                                           "at": [round(float(v), 2) for v in edge[name]],
                                           "message": (f"{edge.get('id')} ucu komşu olmayan "
                                                       f"{other.get('id')} kenarının üzerine oturuyor")})

    # 5. Enclosed area: a boundary that goes out and comes back over itself encloses nothing (P02-b.5).
    if len(edges) > 1:
        polygon = np.vstack([chain[:-1] for chain in chains]) if len(chains) > 1 else chains[0]
        x, y = polygon[:, 0], polygon[:, 1]
        area = 0.5 * float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        if abs(area) <= max(tolerance_px * tolerance_px, 1.0):
            issues.append({"kind": "zero_area", "ids": [edge.get("id") for edge in edges],
                           "at": [round(float(v), 2) for v in edges[0]["start"]],
                           "area_px2": round(area, 4),
                           "message": (f"kontur sıfır alana yakın kapanıyor ({area:.3f} px²): "
                                       "sınır kendi üzerinden geri dönüyor")})

    return {"ok": not issues, "closure_px": round(float(closure_px), 4), "issues": issues,
            "edge_count": len(edges)}
