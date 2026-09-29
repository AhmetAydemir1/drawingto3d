"""Attach every printed number to the geometry its dimension line or leader touches.

Where a drawing puts a feature relative to a dimension's arrows is a drafting convention, and
this module records the three ways that happen instead of assuming one:

- an arrow end sits *on* the feature (a leader's tip on a rim, a dimension drawn on the edge),
  so the anchor itself lands on geometry — `features` at the anchor;
- an extension line runs from the row toward the feature, drawn either as a stub that stops
  short of it or as a stroke the anchor crosses — so the anchor's strokes are followed: stubs
  and crossings are attached, chains of coincident open strokes are walked, and the features
  each landing point reaches are recorded together with the chain that got there;
- or the drawing only aligns the feature with the arrow *along the measuring axis* — the plate
  sheet does this (its extension stubs stop tens of pixels short of the holes, but the row's
  ends share the holes' x within 2.4 px), so a two-anchor linear dimension also records
  candidates whose coordinate along the anchor-to-anchor axis matches, with their perpendicular
  offset (an unbounded offset is a fact of drafting, not a bug, so it is recorded, not clipped).

Distances are kept in rendered pixels and nothing picks a winner: a span whose two anchors
agree on one feature and a span aligning with four are both records, and the meaning step is
the one that has to choose. `implied_px_per_mm` (the row's drawn length over the printed value)
against the sheet's own measured calibration (`sheet_px_per_mm`) shows a detail view drawn at
another scale as a ratio away from 1 instead of as a bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from drawingto3d.ingest import load_page
from drawingto3d.observe import Observations, Unsupported, observe
from drawingto3d.perceive import perceive
from drawingto3d.plan import source_hash
from drawingto3d.scale import audit
from drawingto3d.schema import MM_PER_INCH, Span, SpanKind

ANCHOR_TOLERANCE_PX = 3.5
FEATURE_TOLERANCE_PX = 4.0
AXIS_TOLERANCE_PX = 3.0
MAX_FEATURES_PER_SITE = 4
MAX_ALIGNED = 8
MAX_CHAIN = 4
# A dimension is drawn to its own number, so the row's ends must sit `value × px_per_mm` apart. The
# sheet's scale is fitted by consensus and its spread is a few percent; a row that misses by more than
# `ROW_RESIDUAL_LIMIT` is not this dimension's row, and a re-picked pair must land within `ROW_FIT`.
ROW_RESIDUAL_LIMIT = 0.25
ROW_FIT = 0.05

FeatureKind = Literal["circle-centre", "arc-centre", "circle-rim", "arc-rim", "line-end", "path-vertex"]
RANK: dict[str, int] = {"circle-centre": 0, "arc-centre": 1, "circle-rim": 2, "arc-rim": 3,
                        "line-end": 4, "path-vertex": 5}
SiteKind = Literal["anchor", "far-end"]
RoleKind = Literal["row", "stub", "crossing"]
StatusKind = Literal["bound", "partial", "aligned", "unbound", "no-anchor"]


class Feature(BaseModel):
    """A point where an attachment lands: which observed record, where, how far, via which chain."""

    geometry_id: str
    kind: FeatureKind
    point: list[float]
    distance_px: float
    at: SiteKind
    chain: list[str] = Field(default_factory=list)


class Stroke(BaseModel):
    """A drawn stroke the anchor sits on: the row itself, a stub, or a stroke the anchor crosses."""

    geometry_id: str
    role: RoleKind
    far: list[float]
    far_distance_px: float


class AlignedCandidate(BaseModel):
    """A point whose coordinate along the measuring axis matches this anchor's."""

    geometry_id: str
    kind: FeatureKind
    point: list[float]
    along_axis_px: float
    perpendicular_px: float


class AnchorBinding(BaseModel):
    point: list[float]
    strokes: list[Stroke] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    aligned: list[AlignedCandidate] = Field(default_factory=list)


class SpanBinding(BaseModel):
    span_id: str
    text: str
    value: float | None
    unit: str
    kind: str
    anchor_mode: str
    text_bbox: list[float] | None = None
    anchors: list[AnchorBinding] = Field(default_factory=list)
    row_px: float | None = None
    implied_px_per_mm: float | None = None
    status: StatusKind = "unbound"
    # True when the row was re-picked against the scale, i.e. the extent is known rather than perceived.
    row_repaired: bool = False
    notes: list[str] = Field(default_factory=list)

    def touches(self, geometry_id: str) -> bool:
        return any(feature.geometry_id == geometry_id
                   for anchor in self.anchors for feature in anchor.features) or \
            any(candidate.geometry_id == geometry_id
                for anchor in self.anchors for candidate in anchor.aligned)


class Bindings(BaseModel):
    version: int = 3
    source_ref: str
    source_sha256: str
    sheet_px_per_mm: float | None = None
    spans: list[SpanBinding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _round(value: float) -> float:
    return float(round(value, 2))


def _point(values: np.ndarray) -> list[float]:
    return [_round(float(values[0])), _round(float(values[1]))]


def _segment_distance(point: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    if float(np.dot(ab, ab)) == 0.0:
        return float(np.linalg.norm(point - a))
    t = float(np.clip(np.dot(point - a, ab) / np.dot(ab, ab), 0.0, 1.0))
    return float(np.linalg.norm(a + t * ab - point))


def _polyline_distance(point: np.ndarray, points: np.ndarray) -> float:
    return min(_segment_distance(point, points[i], points[i + 1])
               for i in range(len(points) - 1))


def _open_strokes(observations: Observations) -> dict[str, np.ndarray]:
    """Every open stroke once: fitted lines by their primitive, unfitted paths by their points."""
    fitted_paths = {primitive.path_id for primitive in observations.primitives}
    strokes: dict[str, np.ndarray] = {}
    for primitive in observations.primitives:
        if primitive.kind == "line" and primitive.start and primitive.end:
            strokes[primitive.id] = np.array([primitive.start, primitive.end], dtype=float)
    for path in observations.paths:
        if path.closed or len(path.points) < 2 or path.id in fitted_paths:
            continue
        strokes[path.id] = np.array(path.points, dtype=float)
    return strokes


def _feature_points(observations: Observations) -> list[tuple[str, FeatureKind, np.ndarray]]:
    """Points an attachment can land on: circle centres, line ends, vertices of unfitted paths."""
    fitted_paths = {primitive.path_id for primitive in observations.primitives}
    points: list[tuple[str, FeatureKind, np.ndarray]] = []
    for primitive in observations.primitives:
        if primitive.kind in ("circle", "arc") and primitive.centre:
            if getattr(primitive, "method", "") == "hough-arc":
                continue   # fitted off pixels, not drawn: its centre is not a verified measurement
            centre_kind: FeatureKind = "circle-centre" if primitive.kind == "circle" else "arc-centre"
            points.append((primitive.id, centre_kind, np.array(primitive.centre, dtype=float)))
        elif primitive.kind == "line" and primitive.start and primitive.end:
            points.append((primitive.id, "line-end", np.array(primitive.start, dtype=float)))
            points.append((primitive.id, "line-end", np.array(primitive.end, dtype=float)))
    for path in observations.paths:
        if path.id in fitted_paths or len(path.points) < 2:
            continue
        vertices = path.points if path.closed else [path.points[0], path.points[-1]]
        for vertex in vertices:
            points.append((path.id, "path-vertex", np.array(vertex, dtype=float)))
    return points


def _attach_strokes(anchor_point: np.ndarray, other: np.ndarray | None,
                    strokes: dict[str, np.ndarray]) -> list[Stroke]:
    attached: list[Stroke] = []
    for geometry_id, points in strokes.items():
        first, last = points[0], points[-1]
        to_first = float(np.linalg.norm(first - anchor_point))
        to_last = float(np.linalg.norm(last - anchor_point))
        if min(to_first, to_last) <= ANCHOR_TOLERANCE_PX:
            far = last if to_first <= to_last else first
            role: RoleKind = "stub"
            if other is not None and float(np.linalg.norm(far - other)) <= ANCHOR_TOLERANCE_PX:
                role = "row"
            attached.append(Stroke(geometry_id=geometry_id, role=role, far=_point(far),
                                   far_distance_px=_round(float(np.linalg.norm(far - anchor_point)))))
        elif _polyline_distance(anchor_point, points) <= ANCHOR_TOLERANCE_PX:
            far = first if to_first > to_last else last
            attached.append(Stroke(geometry_id=geometry_id, role="crossing", far=_point(far),
                                   far_distance_px=_round(max(to_first, to_last))))
    return attached


def _walk_chain(site: np.ndarray, strokes: dict[str, np.ndarray],
                visited: set[str]) -> tuple[np.ndarray, list[str]]:
    chain: list[str] = []
    for _ in range(MAX_CHAIN):
        found: tuple[str, np.ndarray] | None = None
        for geometry_id, points in strokes.items():
            if geometry_id in visited:
                continue
            if float(np.linalg.norm(points[0] - site)) <= ANCHOR_TOLERANCE_PX:
                found = (geometry_id, points[-1])
            elif float(np.linalg.norm(points[-1] - site)) <= ANCHOR_TOLERANCE_PX:
                found = (geometry_id, points[0])
            if found:
                break
        if not found:
            break
        visited.add(found[0])
        chain.append(found[0])
        site = found[1]
    return site, chain


def _features_at(site: np.ndarray, observations: Observations,
                 points: list[tuple[str, FeatureKind, np.ndarray]],
                 exclude: set[str], at: SiteKind, chain: list[str]) -> list[Feature]:
    hits: list[Feature] = []
    for primitive in observations.primitives:
        if primitive.id in exclude or primitive.kind not in ("circle", "arc"):
            continue
        if not primitive.centre or not primitive.radius:
            continue
        centre = np.array(primitive.centre, dtype=float)
        distance = float(np.linalg.norm(site - centre))
        centre_kind: FeatureKind = "circle-centre" if primitive.kind == "circle" else "arc-centre"
        rim_kind: FeatureKind = "circle-rim" if primitive.kind == "circle" else "arc-rim"
        if distance <= FEATURE_TOLERANCE_PX:
            hits.append(Feature(geometry_id=primitive.id, kind=centre_kind, point=_point(centre),
                                distance_px=_round(distance), at=at, chain=chain))
        elif abs(distance - primitive.radius) <= FEATURE_TOLERANCE_PX and distance > 0.0:
            rim = centre + (site - centre) * (primitive.radius / distance)
            hits.append(Feature(geometry_id=primitive.id, kind=rim_kind, point=_point(rim),
                                distance_px=_round(abs(distance - primitive.radius)),
                                at=at, chain=chain))
    for geometry_id, kind, location in points:
        if geometry_id in exclude or kind == "circle-centre":
            continue
        distance = float(np.linalg.norm(location - site))
        if distance <= FEATURE_TOLERANCE_PX:
            hits.append(Feature(geometry_id=geometry_id, kind=kind, point=_point(location),
                                distance_px=_round(distance), at=at, chain=chain))
    hits.sort(key=lambda feature: feature.distance_px)
    return hits[:MAX_FEATURES_PER_SITE]


def _aligned_at(anchor_point: np.ndarray, other: np.ndarray,
                points: list[tuple[str, FeatureKind, np.ndarray]],
                exclude: set[str]) -> list[AlignedCandidate]:
    axis = other - anchor_point
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        return []
    axis = axis / norm
    perpendicular_axis = np.array([-axis[1], axis[0]])
    aligned: list[AlignedCandidate] = []
    for geometry_id, kind, location in points:
        if geometry_id in exclude or kind in ("circle-rim", "arc-rim"):
            continue
        delta = location - anchor_point
        along = float(np.dot(delta, axis))
        perpendicular = abs(float(np.dot(delta, perpendicular_axis)))
        if abs(along) <= AXIS_TOLERANCE_PX and perpendicular > FEATURE_TOLERANCE_PX:
            aligned.append(AlignedCandidate(geometry_id=geometry_id, kind=kind, point=_point(location),
                                            along_axis_px=_round(along),
                                            perpendicular_px=_round(perpendicular)))
    # A hole aligns through its centre however far the standoff is, so kind outranks distance:
    # circles before arcs, centres before ends and vertices, each group by perpendicular offset.
    # Ties on the 2 px grid (a corner arc concentric with a hole) keep the better-ranked record.
    aligned.sort(key=lambda candidate: (RANK[candidate.kind], candidate.perpendicular_px))
    deduped: list[AlignedCandidate] = []
    seen: set[tuple[int, int]] = set()
    for candidate in aligned:
        key = (int(round(candidate.point[0] / 2)), int(round(candidate.point[1] / 2)))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped[:MAX_ALIGNED]


def _anchor_binding(anchor_point: np.ndarray, other: np.ndarray | None, span: Span,
                    observations: Observations, strokes: dict[str, np.ndarray],
                    points: list[tuple[str, FeatureKind, np.ndarray]]) -> AnchorBinding:
    binding = AnchorBinding(point=_point(anchor_point))
    binding.strokes = _attach_strokes(anchor_point, other, strokes)
    attached_ids = {stroke.geometry_id for stroke in binding.strokes}
    sites: list[tuple[np.ndarray, SiteKind]] = [(anchor_point, "anchor")]
    for stroke in binding.strokes:
        sites.append((np.array(stroke.far, dtype=float), "far-end"))
        if stroke.role == "crossing":
            geometry = strokes[stroke.geometry_id]
            for endpoint in (geometry[0], geometry[-1]):
                if float(np.linalg.norm(endpoint - anchor_point)) > ANCHOR_TOLERANCE_PX:
                    sites.append((endpoint, "far-end"))
    visited = set(attached_ids)
    seen_sites: list[np.ndarray] = []
    for site, at in sites:
        if any(float(np.linalg.norm(site - known)) <= ANCHOR_TOLERANCE_PX for known in seen_sites):
            continue
        seen_sites.append(site)
        landing, chain = _walk_chain(site, strokes, visited)
        if chain:
            visited.update(chain)
        binding.features.extend(_features_at(landing, observations, points,
                                             attached_ids | visited, at, chain))
    if other is not None and span.anchor_mode == "dimension" and span.kind.value == "linear":
        binding.aligned = _aligned_at(anchor_point, other, points, attached_ids | visited)
    binding.features.sort(key=lambda feature: feature.distance_px)
    return binding


def _status_of(binding: SpanBinding) -> SpanBinding:
    """The reading's own verdict on how far the anchors reached."""
    if not binding.anchors:
        binding.status = "no-anchor"
        return binding
    with_features = sum(1 for anchor in binding.anchors if anchor.features)
    if with_features == len(binding.anchors):
        binding.status = "bound"
    elif with_features:
        binding.status = "partial"
    elif any(anchor.aligned for anchor in binding.anchors):
        binding.status = "aligned"
    else:
        binding.status = "unbound"
    return binding


def _reachable_points(anchor: AnchorBinding) -> list[np.ndarray]:
    """Every point one anchor already reached: where it sits, what it attaches to, what it aligns with."""
    points = [np.array(anchor.point, dtype=float)]
    points += [np.array(stroke.far, dtype=float) for stroke in anchor.strokes]
    points += [np.array(candidate.point, dtype=float) for candidate in anchor.aligned]
    return points


def _best_reached_pair(binding: SpanBinding, expected_px: float) -> tuple[float, np.ndarray, np.ndarray] | None:
    """The pair of already-reached points whose separation is closest to the printed length."""
    if len(binding.anchors) != 2 or expected_px <= 0:
        return None
    first_pool, second_pool = (_reachable_points(anchor) for anchor in binding.anchors)
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for first in first_pool:
        for second in second_pool:
            length = float(np.linalg.norm(second - first))
            residual = abs(length / expected_px - 1.0)
            if best is None or residual < best[0]:
                best = (residual, first, second)
    return best


def _segment_matching_value(binding: SpanBinding, expected_px: float,
                            axis: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """A stroke at one anchor whose projection onto the measuring axis is the printed length.

    Short steps on a sheet are dimensioned without a row of their own: the text sits beside a segment of
    the part and that segment is drawn to the number. The perceived anchors then sit on unrelated lines
    that happen to run through the text, and the drawn segment — attached to one anchor — is the
    measurement. `row` strokes are never used: they join the two anchors, so they are the perceived row
    rather than the extent it was supposed to mark.
    """
    for anchor in binding.anchors:
        point = np.array(anchor.point, dtype=float)
        for stroke in anchor.strokes:
            if stroke.role == "row":
                continue
            far = np.array(stroke.far, dtype=float)
            length = float(np.linalg.norm(far - point))
            # The segment must be drawn along the measuring axis and to the printed length, so what the
            # rule accepts and what the record reports as the row are the same number.
            if length == 0.0 or abs(float(np.dot(far - point, axis))) < 0.99 * length:
                continue
            if abs(length / expected_px - 1.0) <= ROW_FIT:
                return point, far
    return None


def _segment_on_axis(observations: Observations, binding: SpanBinding, expected_px: float,
                     axis: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """A drawn segment lying on the measuring axis whose own length is the printed length.

    A sheet can put the number in one place and draw the extent it measures somewhere else along the same
    axis — beyond the end of the perceived row, tens of millimetres away from the text. The geometry is
    measured all the same (it is in `observations`, the reading's own primitives), it simply never touches
    an anchor, so nothing that starts from the anchors can reach it. Only the axis line decides: both ends
    of the segment must sit on it, which also makes the segment parallel to the axis; a segment anywhere
    else on the sheet is not this dimension's extent, however well its length matches.
    """
    origin = np.array(binding.anchors[0].point, dtype=float)
    normal = np.array([-axis[1], axis[0]])
    best: tuple[float, int, np.ndarray, np.ndarray] | None = None
    for primitive in observations.primitives:
        if primitive.kind != "line" or not primitive.start or not primitive.end:
            continue
        start = np.array(primitive.start, dtype=float)
        end = np.array(primitive.end, dtype=float)
        if max(abs(float(np.dot(start - origin, normal))),
               abs(float(np.dot(end - origin, normal)))) > FEATURE_TOLERANCE_PX:
            continue
        length = float(np.linalg.norm(end - start))
        if length == 0.0 or abs(length / expected_px - 1.0) > ROW_FIT:
            continue
        reach = min(abs(float(np.dot(start - origin, axis))), abs(float(np.dot(end - origin, axis))))
        if best is None or reach < best[0]:
            best = (reach, int(primitive.id.lstrip("g") or 0), start, end)
    if best is None:
        return None
    return best[2], best[3]


def _repick_row_with_calibration(binding: SpanBinding, span: Span, calibration,
                                 observations: Observations, strokes: dict[str, np.ndarray],
                                 points: list[tuple[str, FeatureKind, np.ndarray]]) -> None:
    """Re-pick the row's ends when the drawn row disagrees with the sheet's own scale.

    A dimension is drawn to the number printed on it, so the two ends the anchors reached must sit
    `value × px_per_mm` apart. On a sheet whose scale is fitted by consensus, a span whose row misses
    that length by more than `ROW_RESIDUAL_LIMIT` was read against the wrong row (a title-block rule,
    an outline edge that runs through the number), and then no candidate pair measures the printed
    value at all — the reading reports `unresolved` while a usable pair was already reached.

    Two ways to land on the printed length, in this order: a pair with one end at each anchor (the two
    faces a dimension marks), or — when no such pair exists — a single stroke attached to one anchor
    whose own projection onto the axis is the printed length (a step dimensioned by its own segment).
    When neither exists because the extent never touches an anchor at all, the drawn segment lying on the
    axis at the printed length is the last thing tried; if the sheet keeps it nowhere on that axis, the
    span stays as it was read and the reading says so.

    Only points the anchors reached, and the drawing's own measured primitives, are considered: nothing
    new is detected and no tolerance is loosened. A row that already agrees with the scale is left
    untouched, and a re-picked pair is accepted only when it lands within `ROW_FIT` of the printed length.
    """
    if calibration is None or len(binding.anchors) != 2 or not span.value:
        return
    # A linear dimension is drawn as a row to its own number; a radius or leader callout is not, so its
    # anchors are never re-picked against the value.
    if binding.kind != "linear" or binding.anchor_mode != "dimension":
        return
    value_mm = float(span.value) * (MM_PER_INCH if span.unit == "in" else 1.0)
    expected = float(calibration.expected_px(value_mm))
    if expected <= 0 or (binding.row_px or 0.0) <= 0:
        return
    before = float(binding.row_px or 0.0)
    if abs(before / expected - 1.0) <= ROW_RESIDUAL_LIMIT:
        return
    axis = np.array(binding.anchors[1].point, dtype=float) - np.array(binding.anchors[0].point,
                                                                      dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        return
    axis = axis / norm
    best = _best_reached_pair(binding, expected)
    residual = 0.0
    if best is not None and best[0] <= ROW_FIT:
        residual, first, second = best
        how = "uçlar çapanın gördüğü noktalardan yeniden seçildi"
    else:
        segment = _segment_matching_value(binding, expected, axis)
        if segment is not None:
            first, second = segment
            how = "çapanın üzerindeki parça çizgisi ölçüldü"
        else:
            drawn = _segment_on_axis(observations, binding, expected, axis)
            if drawn is None:
                return
            first, second = drawn
            how = "ölçü ekseni üzerinde çizilmiş parça çizgisi ölçüldü"
    binding.anchors = [_anchor_binding(first, second, span, observations, strokes, points),
                       _anchor_binding(second, first, span, observations, strokes, points)]
    length_px = float(np.linalg.norm(second - first))
    binding.row_px = _round(length_px)
    binding.implied_px_per_mm = _round(length_px / value_mm)
    binding.row_repaired = True
    _status_of(binding)
    binding.notes.append(
        f"satır ölçeğe uymadı ({_round(before)} px, beklenen {_round(expected)} px); {how} "
        f"({_round(length_px)} px, artık %{_round(abs(length_px / expected - 1.0) * 100)})")


def _bind_span(span: Span, observations: Observations, strokes: dict[str, np.ndarray],
               points: list[tuple[str, FeatureKind, np.ndarray]],
               calibration=None) -> SpanBinding:
    anchors = [np.array(anchor, dtype=float) for anchor in span.anchors]
    binding = SpanBinding(span_id=span.id, text=span.text, value=span.value,
                          unit=span.unit, kind=span.kind.value, anchor_mode=span.anchor_mode,
                          text_bbox=[span.bbox.x, span.bbox.y, span.bbox.w, span.bbox.h])
    for index, anchor_point in enumerate(anchors):
        other = anchors[1 - index] if len(anchors) == 2 else None
        binding.anchors.append(_anchor_binding(anchor_point, other, span, observations,
                                               strokes, points))
    if len(anchors) == 2:
        row_px = float(np.linalg.norm(anchors[1] - anchors[0]))
        binding.row_px = _round(row_px)
        if span.value:
            value_mm = float(span.value) * (MM_PER_INCH if span.unit == "in" else 1.0)
            binding.implied_px_per_mm = _round(row_px / value_mm)
        _repick_row_with_calibration(binding, span, calibration, observations, strokes, points)
    if not binding.anchors:
        binding.status = "no-anchor"
        return binding
    return _status_of(binding)


def _diameter_glyph_upgrade(spans: list[Span], observations: Observations) -> list[str]:
    """A Ø prefix drawn as stroke art: `observe` sees the glyph circle, the span's own text cannot.

    The text layer of such a sheet carries no Ø at all, so the phrase reaches the reading as a plain
    length. `observe._diameter_prefix_glyph` marks it a diameter there; the two are the same phrase, so
    they are matched by equal text and overlapping box. Nothing is inferred from the value.
    """
    upgraded: list[str] = []
    for text in observations.texts:
        if text.kind != "diameter":
            continue
        for span in spans:
            if span.kind != SpanKind.linear or span.text.strip() != text.text.strip():
                continue
            if (span.bbox.x >= text.bbox.x + text.bbox.w or text.bbox.x >= span.bbox.x + span.bbox.w
                    or span.bbox.y >= text.bbox.y + text.bbox.h or text.bbox.y >= span.bbox.y + span.bbox.h):
                continue
            span.kind = SpanKind.diameter
            upgraded.append(span.text.strip())
    return upgraded


def bind_page(path: str | Path) -> Bindings:
    """Every span of the sheet with what its anchors touch, two hops out."""
    drawing = Path(path)
    observations = observe(drawing)
    page = load_page(drawing)
    _primitives, spans = perceive(page)
    calibration, _suspect = audit(spans)
    glyph_diameters = _diameter_glyph_upgrade(spans, observations)
    record = Bindings(source_ref=str(drawing), source_sha256=source_hash(drawing),
                      sheet_px_per_mm=_round(float(calibration.px_per_mm)) if calibration else None)
    strokes = _open_strokes(observations)
    points = _feature_points(observations)
    for span in spans:
        record.spans.append(_bind_span(span, observations, strokes, points, calibration=calibration))
    record.notes = [
        "Rol: row = iki ankrajı birleştiren satır; stub = ucu ankrajda biten çizgi; crossing = ankrajdan geçen çizgi.",
        "Zincir: uçları çakışan açık çizgiler en çok 4 adım izlenir; 'chain' alanı yürünen kimlikleri taşır.",
        "aligned: ölçü ekseni boyunca hizalanan adaylar; dik uzaklık kırpılmaz, çünkü standoff çizimin kuralıdır.",
        "aligned sırası: daire merkezi > yay merkezi > uçlar/köşeler; 2 px ızgarada eşleşen adaylar tekilleştirilir.",
        "Sınırlar: ankraj 3,5 px, özellik 4,0 px, eksen 3,0 px — ölçümden seçildi, kayıtta anılır.",
        "implied_px_per_mm = satırın çizili uzunluğu / basılı değer; sheet_px_per_mm ile oranı 1'den sapıyorsa detay farklı ölçekte.",
        f"Satır paftanın ölçeğinden %{int(ROW_RESIDUAL_LIMIT * 100)}'den fazla saparsa uçlar, çapanın gördüğü "
        f"noktalar arasından ölçeğin gerektirdiği uzunlukla yeniden seçilir (kabul: %{int(ROW_FIT * 100)}); "
        "seçim kendi notunu taşır. Bu bir seçimdir, yeni geometri bulunmaz ve tolerans gevşetilmez.",
    ]
    if glyph_diameters:
        record.notes.append(
            f"{len(glyph_diameters)} çağrı Ø glifiyle çaplı okundu ({', '.join(glyph_diameters)}): önek metin "
            "katmanında yok, rakamların yanına çizilmiş küçük daire olarak duruyor")
    return record


__all__ = ["Bindings", "SpanBinding", "AnchorBinding", "Feature", "Stroke", "AlignedCandidate",
           "bind_page", "Unsupported"]
