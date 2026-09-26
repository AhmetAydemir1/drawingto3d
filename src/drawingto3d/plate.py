"""Conservative vector-drawing recognizer for one explicit plate family.

No filenames, expected dimensions, reference STEP, or local model enter recognition.
Unsupported layouts return None. This first version accepts top-level, line-segment
PDF paths only: a rounded rectangular outline, four equal corner holes, a central
circle and an aligned section proving the blind pocket's depth.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from drawingto3d.observe import vector_groups
from drawingto3d.perceive import perceive
from drawingto3d.plan import Evidence, PlatePlan, source_hash
from drawingto3d.scale import audit
from drawingto3d.schema import MM_PER_INCH, Page, Span


class Unsupported(ValueError):
    pass


def propose_plate(page: Page) -> PlatePlan | None:
    if Path(page.path).suffix.lower() != ".pdf" or not page.vector_text:
        return None
    _primitives, spans = perceive(page)
    calibration, _suspect = audit(spans)
    if calibration is None:
        return None
    groups = vector_groups(page)
    proposals = []
    for paths in groups:
        try:
            proposals.append(_from_paths(page, paths, groups, spans, calibration.px_per_mm))
        except Unsupported:
            continue
    return proposals[0] if len(proposals) == 1 else None


def _require(condition, reason: str):
    if not condition:
        raise Unsupported(reason)


def _circle(points: np.ndarray, closed: bool) -> tuple[float, float, float] | None:
    if len(points) < 8:
        return None
    a = np.column_stack((2 * points[:, 0], 2 * points[:, 1], np.ones(len(points))))
    cx, cy, c = np.linalg.lstsq(a, (points**2).sum(axis=1), rcond=None)[0]
    radius2 = c + cx**2 + cy**2
    if radius2 <= 0:
        return None
    radius = float(np.sqrt(radius2))
    distances = np.linalg.norm(points - (cx, cy), axis=1)
    if radius < 3 or max(abs(distances - radius)) > max(0.6, radius * 0.005):
        return None
    angles = np.unwrap(np.arctan2(points[:, 1] - cy, points[:, 0] - cx))
    sweep = abs(angles[-1] - angles[0])
    expected = 2 * np.pi if closed else np.pi / 2
    if abs(sweep - expected) > 0.12:
        return None
    return float(cx), float(cy), radius


def _near(a, b, tolerance=5.0) -> bool:
    return bool(np.max(np.abs(np.asarray(a) - np.asarray(b))) <= tolerance)


def _mm(span: Span) -> float:
    return float(span.value) * (MM_PER_INCH if span.unit == "in" else 1)


def _dimension(spans, axis, low, high, scale) -> Span:
    hits = []
    for span in spans:
        if span.value is None or len(span.anchors) != 2 or span.anchor_mode != "dimension":
            continue
        a, b = np.array(span.anchors)
        if abs(a[1 - axis] - b[1 - axis]) > 3:
            continue
        ends = sorted((a[axis], b[axis]))
        if _near(ends, [low, high], 7) and abs(_mm(span) * scale - (high - low)) < max(8, (high - low) * 0.025):
            hits.append(span)
    _require(len(hits) == 1, "dimension missing or ambiguous")
    return hits[0]


def _from_paths(page, paths, groups, spans, scale) -> PlatePlan:
    # Every subpath in this object must be accounted for, including the outer outline.
    _require(len(paths) == 13, "not a rounded plate with five circles")
    circles = [c for p in paths if (c := _circle(p, True)) is not None]
    arcs = [c for p in paths if (c := _circle(p, False)) is not None]
    lines = [p for p in paths if len(p) == 2]
    _require(len(circles) == 5 and len(arcs) == 4 and len(lines) == 4, "unsupported contours")
    circles.sort(key=lambda c: c[2])
    holes, pocket = np.array(circles[:4]), np.array(circles[4])
    _require(np.ptp(holes[:, 2]) < 1 and pocket[2] > holes[0, 2] * 2, "unequal corner holes")
    points = np.concatenate(paths)
    low, high = points.min(axis=0), points.max(axis=0)
    centre = (low + high) / 2
    _require(_near(pocket[:2], centre, 2), "off-centre pocket")
    xs, ys = [float(holes[:, axis].min()) for axis in (0, 1)], [float(holes[:, axis].max()) for axis in (0, 1)]
    x0, y0 = xs
    x1, y1 = ys
    _require(all(any(_near(h[:2], [x, y], 1) for h in holes) for x in (x0, x1) for y in (y0, y1)), "not four corners")
    _require(_near([(x0 + x1) / 2, (y0 + y1) / 2], centre, 2), "off-centre hole pattern")
    radius = float(np.mean([a[2] for a in arcs]))
    _require(max(abs(a[2] - radius) for a in arcs) < 1, "unequal corners")
    _require(all(any(_near(a[:2], [x, y], 2) for a in arcs)
                 for x in (low[0] + radius, high[0] - radius)
                 for y in (low[1] + radius, high[1] - radius)), "corner arc placement")
    expected_lines = [([low[0] + radius, y], [high[0] - radius, y]) for y in (low[1], high[1])]
    expected_lines += [([x, low[1] + radius], [x, high[1] - radius]) for x in (low[0], high[0])]
    _require(all(any(_near(line, pair, 2) or _near(line[::-1], pair, 2) for line in lines)
                 for pair in expected_lines), "outline not closed")
    dx = _dimension(spans, 0, x0, x1, scale)
    dy = _dimension(spans, 1, y0, y1, scale)
    height = _dimension(spans, 1, low[1], high[1], scale)
    # Symmetry is only proposed when all four margins and the arc radii agree geometrically.
    margin = (_mm(height) - _mm(dy)) / 2
    width = _mm(dx) + 2 * margin
    _require(margin > 0, "no edge margin")
    measured = np.array([x0 - low[0], high[0] - x1, y0 - low[1], high[1] - y1, radius])
    _require(_near(measured, margin * scale, max(3, margin * scale * 0.03)), "unequal edge margins")
    _require(abs(width * scale - (high[0] - low[0])) < width * scale * 0.025, "width conflicts with outline")
    hole_text = [s for s in spans if s.value is not None and "THRU" in s.text.upper()
                 and abs(_mm(s) * scale / 2 - holes[0, 2]) < 2]
    _require(len(hole_text) == 1, "through-hole callout missing or ambiguous")
    hole = hole_text[0]
    pocket_text = [s for s in spans if s.value is not None and s.anchor_mode == "leader"
                   and abs(_mm(s) * scale / 2 - pocket[2]) < max(3, pocket[2] * 0.025)
                   # The thin-line reader stops before a filled arrowhead. Allow at most
                   # one character height (and 20% of the radius) for that missing tip.
                   and any(abs(np.linalg.norm(np.array(a) - pocket[:2]) - pocket[2])
                           < max(6, min(s.bbox.h, pocket[2] * 0.2)) for a in s.anchors)]
    _require(len(pocket_text) == 1, "pocket leader missing or ambiguous")
    diameter = pocket_text[0]
    sections = []
    for group in groups:
        try:
            sections.append(_section(group, low, high, pocket, spans, scale))
        except Unsupported:
            continue
    _require(len(sections) == 1, "section missing or ambiguous")
    thickness, depth = sections[0]
    bindings = {"height": height, "hole_dx": dx, "hole_dy": dy, "hole_diameter": hole,
                "pocket_diameter": diameter, "thickness": thickness, "pocket_depth": depth}
    _require(len({s.id for s in bindings.values()}) == 7, "one dimension used for different features")
    _require({s.id for s in spans if s.value is not None} == {s.id for s in bindings.values()}, "unaccounted dimensions")
    evidence = {key: Evidence(kind="printed", span_ids=[span.id], explanation=span.text)
                for key, span in bindings.items()}
    evidence["width"] = Evidence(kind="derived", span_ids=[dx.id, height.id, dy.id],
                                  explanation="hole_dx + height - hole_dy; four equal edge margins checked against outline")
    evidence["corner_radius"] = Evidence(kind="derived", span_ids=[height.id, dy.id],
                                          explanation="(height - hole_dy) / 2; checked against all four drawn arcs")
    try:
        return PlatePlan(source_sha256=source_hash(page.path), width=width, corner_radius=margin,
                         evidence=evidence, **{key: _mm(span) for key, span in bindings.items()},
                         assumptions=[
                             "Dört kenar payı eşit kabul edildi; dış uzunluk delik aralığı ve kenar payından türetildi.",
                             "Köşe yarıçapı kenar payına eşit kabul edildi; dört çizili yay ile karşılaştırıldı.",
                             "Merkezdeki daire, hizalı kesitteki kör cep olarak eşleştirildi.",
                             "Dişli delikler çağrıdaki matkap çapında düz delik olarak modellenir; vida helisi üretilmez.",
                         ])
    except ValueError as exc:
        raise Unsupported(str(exc)) from exc


def _section(paths, outline_low, outline_high, pocket, spans, scale):
    lines = [p for p in paths if len(p) == 2]
    _require(len(lines) == 8, "section needs eight straight edges")
    points = np.concatenate(lines)
    low, high = points.min(axis=0), points.max(axis=0)
    _require(_near([low[0], high[0]], [outline_low[0], outline_high[0]], 3), "section not aligned")
    _require(high[1] < outline_low[1] or low[1] > outline_high[1], "section overlaps plan")
    ylevels = sorted(set(round(float(y), 1) for y in points[:, 1]))
    _require(len(ylevels) == 3, "unsupported section depths")
    top, floor, bottom = ylevels
    left, right = pocket[0] - pocket[2], pocket[0] + pocket[2]
    required = [([low[0], top], [left, top]), ([left, top], [left, floor]),
                ([left, floor], [right, floor]), ([right, floor], [right, top]),
                ([right, top], [high[0], top]), ([high[0], top], [high[0], bottom]),
                ([high[0], bottom], [low[0], bottom]), ([low[0], bottom], [low[0], top])]
    _require(all(any(_near(line, edge, 2) or _near(line[::-1], edge, 2) for line in lines)
                 for edge in required), "section does not prove a centred blind pocket")
    # Extra paths must lie on the top plane (hidden edge of the circular pocket).
    _require(all(len(p) == 2 or (max(abs(p[:, 1] - top)) < 1 and
                 min(p[:, 0]) >= left - 2 and max(p[:, 0]) <= right + 2) for p in paths), "extra section geometry")
    return _dimension(spans, 1, top, bottom, scale), _dimension(spans, 1, top, floor, scale)
