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
from drawingto3d.schema import MM_PER_INCH, Span

ANCHOR_TOLERANCE_PX = 3.5
FEATURE_TOLERANCE_PX = 4.0
AXIS_TOLERANCE_PX = 3.0
MAX_FEATURES_PER_SITE = 4
MAX_ALIGNED = 8
MAX_CHAIN = 4

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

    def touches(self, geometry_id: str) -> bool:
        return any(feature.geometry_id == geometry_id
                   for anchor in self.anchors for feature in anchor.features) or \
            any(candidate.geometry_id == geometry_id
                for anchor in self.anchors for candidate in anchor.aligned)


class Bindings(BaseModel):
    version: int = 1
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


def _bind_span(span: Span, observations: Observations, strokes: dict[str, np.ndarray],
               points: list[tuple[str, FeatureKind, np.ndarray]]) -> SpanBinding:
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
    if not anchors:
        binding.status = "no-anchor"
        return binding
    with_features = sum(1 for anchor in binding.anchors if anchor.features)
    if with_features == len(anchors):
        binding.status = "bound"
    elif with_features:
        binding.status = "partial"
    elif any(anchor.aligned for anchor in binding.anchors):
        binding.status = "aligned"
    else:
        binding.status = "unbound"
    return binding


def bind_page(path: str | Path) -> Bindings:
    """Every span of the sheet with what its anchors touch, two hops out."""
    drawing = Path(path)
    observations = observe(drawing)
    page = load_page(drawing)
    _primitives, spans = perceive(page)
    calibration, _suspect = audit(spans)
    record = Bindings(source_ref=str(drawing), source_sha256=source_hash(drawing),
                      sheet_px_per_mm=_round(float(calibration.px_per_mm)) if calibration else None)
    strokes = _open_strokes(observations)
    points = _feature_points(observations)
    for span in spans:
        record.spans.append(_bind_span(span, observations, strokes, points))
    record.notes = [
        "Rol: row = iki ankrajı birleştiren satır; stub = ucu ankrajda biten çizgi; crossing = ankrajdan geçen çizgi.",
        "Zincir: uçları çakışan açık çizgiler en çok 4 adım izlenir; 'chain' alanı yürünen kimlikleri taşır.",
        "aligned: ölçü ekseni boyunca hizalanan adaylar; dik uzaklık kırpılmaz, çünkü standoff çizimin kuralıdır.",
        "aligned sırası: daire merkezi > yay merkezi > uçlar/köşeler; 2 px ızgarada eşleşen adaylar tekilleştirilir.",
        "Sınırlar: ankraj 3,5 px, özellik 4,0 px, eksen 3,0 px — ölçümden seçildi, kayıtta anılır.",
        "implied_px_per_mm = satırın çizili uzunluğu / basılı değer; sheet_px_per_mm ile oranı 1'den sapıyorsa detay farklı ölçekte.",
    ]
    return record


__all__ = ["Bindings", "SpanBinding", "AnchorBinding", "Feature", "Stroke", "AlignedCandidate",
           "bind_page", "Unsupported"]
