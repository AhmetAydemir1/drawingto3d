"""Resolve each measured number into the claim it makes about the drawing, or say why it cannot.

The binding layer hands over candidates; this layer picks the reading the drawing itself supports
and writes down what was left over:

- a two-anchor linear dimension claims a *distance*: every pair of candidates, one per anchor,
  whose drawn separation equals the printed value within tolerance. Pairs are ranked by candidate
  kind first (circle centres before arcs before line ends before vertices — a dimension between
  holes is a hole spacing before it is anything else) and then by how close to the arrows the
  candidates sat, which is what resolves the plate's symmetric readings: `100,00` is drawn above
  the plate, its stubs reach down to the top holes, and the same spacing exists at the bottom —
  the top pair wins on cost, the bottom pair stays in the record as an alternative;
- a leader whose value matches some circle's drawn diameter claims a *diameter*, and the claim
  carries every circle of that size (`matched_geometry`), because a callout like "4 x Ø6,80"
  sizes a set: the printed count is read from the neighbouring "N x" text and checked against
  how many circles actually match (`covered`);
- a radius value claims a *radius* against fitted arcs and circles.

Nothing is invented when the drawing does not support a reading: the span is marked
`unresolved` and the candidates that failed are still visible in `bindings.json`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from drawingto3d.bind import RANK, AnchorBinding, SpanBinding, bind_page
from drawingto3d.observe import Observations, Unsupported, observe
from drawingto3d.schema import MM_PER_INCH

RELATIVE_TOLERANCE = 0.03
ABSOLUTE_TOLERANCE_MM = 0.15
CANDIDATE_LIMIT = 6
# The fallback pass keeps the reached candidates and adds room for the ends of the crossed lines, so the
# limit that bounds the first pass cannot hide the very candidate the second pass exists for.
CROSSED_LIMIT = 4
ALTERNATIVE_LIMIT = 3
COUNT_RADIUS_PX = 260.0
COUNT_PATTERN = re.compile(r"^\s*(\d+)\s*[x×]\s*$")

FormKind = Literal["distance", "diameter", "radius", "none"]
ResolutionKind = Literal["confirmed", "unresolved", "no-value", "no-scale"]


class ClaimPoint(BaseModel):
    geometry_id: str
    kind: str
    point: list[float]
    cost_px: float


class Claim(BaseModel):
    form: FormKind
    points: list[ClaimPoint]
    drawn_mm: float
    printed_mm: float
    deviation_mm: float
    rank: int
    cost_px: float
    matched_geometry: list[str] = Field(default_factory=list)


class SpanMeaning(BaseModel):
    span_id: str
    text: str
    printed_mm: float | None
    printed_value: float | None = None
    unit: str
    kind: str
    anchor_mode: str
    form: FormKind = "none"
    resolution: ResolutionKind = "unresolved"
    claim: Claim | None = None
    alternatives: list[Claim] = Field(default_factory=list)
    count: int | None = None
    covered: int | None = None
    # The binding's row was re-picked against the sheet's scale, so the extent is known and the claim
    # was ordered across-axis first (a local pair at the extent).
    row_repaired: bool = False
    notes: list[str] = Field(default_factory=list)


class Meanings(BaseModel):
    version: int = 1
    source_ref: str
    source_sha256: str
    sheet_px_per_mm: float | None = None
    spans: list[SpanMeaning] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _round(value: float) -> float:
    return float(round(value, 2))


def _dedupe(points: list[ClaimPoint]) -> list[ClaimPoint]:
    seen: set[tuple[str, int, int]] = set()
    kept: list[ClaimPoint] = []
    for point in points:
        key = (point.kind, int(round(point.point[0])), int(round(point.point[1])))
        if key in seen:
            continue
        seen.add(key)
        kept.append(point)
    return kept


def _candidates(binding: AnchorBinding) -> list[ClaimPoint]:
    """What this anchor could be measuring: features it reached, then points it aligns with."""
    points: list[ClaimPoint] = []
    for feature in binding.features:
        points.append(ClaimPoint(geometry_id=feature.geometry_id, kind=feature.kind,
                                 point=feature.point, cost_px=feature.distance_px))
    for candidate in binding.aligned:
        points.append(ClaimPoint(geometry_id=candidate.geometry_id, kind=candidate.kind,
                                 point=candidate.point, cost_px=candidate.perpendicular_px))
    points = _dedupe(points)
    points.sort(key=lambda point: (RANK[point.kind], point.cost_px))
    return points[:CANDIDATE_LIMIT]


def _crossed_ends(binding: AnchorBinding) -> list[ClaimPoint]:
    """The far ends of the lines this anchor crosses: a face's own extension line, measured geometry.

    The row and the stubs are the dimension line's own ink and are never offered here — a claim built
    from them would point at the line that printed the number and confirm itself.
    """
    return [ClaimPoint(geometry_id=stroke.geometry_id, kind="line-end", point=list(stroke.far),
                       cost_px=stroke.far_distance_px)
            for stroke in binding.strokes if stroke.role == "crossing"]


def _tolerance(value_mm: float) -> float:
    return max(RELATIVE_TOLERANCE * value_mm, ABSOLUTE_TOLERANCE_MM)


def _pairs_measuring(left: list[ClaimPoint], right: list[ClaimPoint], axis: np.ndarray,
                     value_mm: float, tolerance: float,
                     sheet_px_per_mm: float, across_first: bool = False) -> list[Claim]:
    """Every pair of candidates one from each anchor whose gap measures the printed value along the axis."""
    claims: list[Claim] = []
    for first in left:
        for second in right:
            if first.geometry_id == second.geometry_id:
                continue
            gap = np.array(second.point) - np.array(first.point)
            drawn_mm = abs(float(np.dot(gap, axis))) / sheet_px_per_mm
            deviation = abs(drawn_mm - value_mm)
            if deviation > tolerance:
                continue
            claims.append(Claim(form="distance", points=[first, second], drawn_mm=_round(drawn_mm),
                                printed_mm=value_mm, deviation_mm=_round(deviation),
                                rank=RANK[first.kind] + RANK[second.kind],
                                cost_px=_round(first.cost_px + second.cost_px)))
    if across_first:
        # The pair's two points sit as nearly on the measuring axis as the drawing allows: a local pair
        # at the extent, rather than two distant features sharing only the projection along the axis.
        normal = np.array([-axis[1], axis[0]])

        def key(claim: Claim) -> tuple:
            first, second = (np.array(point.point, dtype=float) for point in claim.points)
            return (round(abs(float(np.dot(second - first, normal))), 3), claim.rank, claim.cost_px,
                    claim.deviation_mm)
    else:
        def key(claim: Claim) -> tuple:
            return (claim.rank, claim.cost_px, claim.deviation_mm)
    claims.sort(key=key)
    return claims


def _distance_claims(binding: SpanBinding, value_mm: float, sheet_px_per_mm: float,
                     notes: list[str] | None = None) -> list[Claim]:
    """A dimension measures along its own row: the projection of the candidate gap onto the axis.

    The first pass offers only what the anchors reached or align with. If nothing there measures the
    printed value, one fallback pass offers the ends of the lines the anchors cross — the faces' own
    extension lines — which is a second chance for a number that would otherwise stay unresolved and
    never a change to a binding that already stands: a sheet whose numbers measure their value reads
    exactly as it did before.

    When the row itself was re-picked against the scale (`SpanBinding.row_repaired`), the extent is known
    rather than perceived, so the claims are ordered by how close their two points lie to the dimension's
    own axis before anything else: the reading then names the pair at the extent (two features the
    printed length apart) instead of two distant features that merely share its projection along the axis.
    A row that was read as drawn keeps the original order untouched.
    """
    if len(binding.anchors) != 2:
        return []
    left, right = _candidates(binding.anchors[0]), _candidates(binding.anchors[1])
    first_anchor = np.array(binding.anchors[0].point, dtype=float)
    axis = np.array(binding.anchors[1].point, dtype=float) - first_anchor
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        return []
    axis = axis / norm
    tolerance = _tolerance(value_mm)
    # A repaired row's extent is known, so its claims are ordered across-axis first (see the docstring).
    across_first = bool(getattr(binding, "row_repaired", False))
    claims = _pairs_measuring(left, right, axis, value_mm, tolerance, sheet_px_per_mm,
                              across_first=across_first)
    if claims:
        return claims
    widened_left = _dedupe(left + _crossed_ends(binding.anchors[0]))[:CANDIDATE_LIMIT + CROSSED_LIMIT]
    widened_right = _dedupe(right + _crossed_ends(binding.anchors[1]))[:CANDIDATE_LIMIT + CROSSED_LIMIT]
    claims = _pairs_measuring(widened_left, widened_right, axis, value_mm, tolerance, sheet_px_per_mm,
                              across_first=across_first)
    if claims and notes is not None:
        pairs = ", ".join("/".join(point.geometry_id for point in claim.points) for claim in claims[:2])
        notes.append("Alışılmış adaylarla ölçülemedi; çapanın kestiği çizgilerin uzak uçları da hesaba "
                     f"katılınca bağlandı: {pairs}.")
    return claims


def _sized_geometry(observations: Observations) -> dict[str, tuple[np.ndarray, float, str]]:
    sized: dict[str, tuple[np.ndarray, float, str]] = {}
    for primitive in observations.primitives:
        if primitive.kind in ("circle", "arc") and primitive.centre and primitive.radius:
            sized[primitive.id] = (np.array(primitive.centre, dtype=float), primitive.radius,
                                   primitive.kind)
    return sized


def _touched_ids(binding: SpanBinding) -> set[str]:
    touched = {feature.geometry_id for anchor in binding.anchors for feature in anchor.features}
    touched |= {candidate.geometry_id for anchor in binding.anchors for candidate in anchor.aligned}
    return touched


def _nearest_anchor_distance(point: np.ndarray, binding: SpanBinding) -> float:
    anchors = [np.array(anchor.point, dtype=float) for anchor in binding.anchors]
    if not anchors:
        return float("inf")
    return min(float(np.linalg.norm(point - anchor)) for anchor in anchors)


def _size_claim(binding: SpanBinding, value_mm: float, sheet_px_per_mm: float,
                sized: dict[str, tuple[np.ndarray, float, str]],
                form: Literal["diameter", "radius"]) -> Claim | None:
    """A leader (or radius mark) sizing circles/arcs: which of them match the printed value."""
    tolerance = _tolerance(value_mm)
    matches: dict[str, tuple[np.ndarray, float, str]] = {}
    for geometry_id, (centre, radius, kind) in sized.items():
        drawn_mm = (2.0 * radius if form == "diameter" else radius) / sheet_px_per_mm
        if abs(drawn_mm - value_mm) <= tolerance:
            matches[geometry_id] = (centre, radius, kind)
    if not matches:
        return None
    touched = _touched_ids(binding)
    preferred = [geometry_id for geometry_id in matches if geometry_id in touched]
    pool = preferred or list(matches)
    chosen = min(pool, key=lambda geometry_id: _nearest_anchor_distance(matches[geometry_id][0], binding))
    centre, radius, kind = matches[chosen]
    drawn_mm = (2.0 * radius if form == "diameter" else radius) / sheet_px_per_mm
    return Claim(form=form,
                 points=[ClaimPoint(geometry_id=chosen, kind=f"{kind}-centre",
                                    point=[_round(centre[0]), _round(centre[1])],
                                    cost_px=_round(_nearest_anchor_distance(centre, binding)))],
                 drawn_mm=_round(drawn_mm), printed_mm=value_mm,
                 deviation_mm=_round(abs(drawn_mm - value_mm)), rank=0, cost_px=0.0,
                 matched_geometry=sorted(matches, key=lambda geometry_id: matches[geometry_id][0][0]))


def _count_near(binding: SpanBinding, observations: Observations) -> tuple[int | None, str | None]:
    """The neighbouring "N x" callout, if one is printed close to this span's own text."""
    reference: np.ndarray | None = None
    if binding.text_bbox:
        x, y, w, h = binding.text_bbox
        reference = np.array([x + w / 2, y + h / 2])
    best: tuple[float, int, str] | None = None
    for text in observations.texts:
        match = COUNT_PATTERN.match(text.text.strip())
        if not match:
            continue
        centre = np.array([text.bbox.x + text.bbox.w / 2, text.bbox.y + text.bbox.h / 2])
        if reference is not None:
            distance = float(np.linalg.norm(centre - reference))
        else:
            distance = _nearest_anchor_distance(centre, binding)
        if distance <= COUNT_RADIUS_PX and (best is None or distance < best[0]):
            best = (distance, int(match.group(1)), text.text.strip())
    if best is None:
        return None, None
    return best[1], best[2]


def _meaning_for(binding, observations: Observations, sized, sheet_px_per_mm) -> SpanMeaning:
    value_mm = (float(binding.value) * (MM_PER_INCH if binding.unit == "in" else 1.0)
                if binding.value is not None else None)
    record = SpanMeaning(span_id=binding.span_id, text=binding.text, printed_mm=value_mm,
                         printed_value=binding.value,
                         unit=binding.unit, kind=binding.kind, anchor_mode=binding.anchor_mode)
    if binding.value is None:
        record.resolution = "no-value"
        return record
    if sheet_px_per_mm is None:
        record.resolution = "no-scale"
        return record
    record.printed_mm = _round(value_mm)
    # The binding's own notes (a row re-picked against the sheet's scale) travel with the meaning, so
    # the evidence and the interpretation interface see why an anchor moved; the flag itself travels in
    # the claim ordering, which is where the extent being known changes the reading.
    record.row_repaired = bool(getattr(binding, "row_repaired", False))
    record.notes.extend(binding.notes or [])
    if binding.kind == "radius" or binding.text.strip().upper().startswith(("R ", "R2", "R")):
        claim = _size_claim(binding, value_mm, sheet_px_per_mm, sized, "radius")
        if claim:
            record.form, record.claim, record.resolution = "radius", claim, "confirmed"
            return record
    # A phrase typed `diameter` sizes a circle wherever it is printed: a leader is one way to say it, and
    # on the third sheet the five Ø callouts are not leaders — with the branch gated on the leader alone
    # their diameter reached the reading as a plain length and was bound as a distance between two ends.
    if binding.kind == "diameter" or binding.anchor_mode == "leader":
        claim = _size_claim(binding, value_mm, sheet_px_per_mm, sized, "diameter")
        if claim:
            record.form, record.claim, record.resolution = "diameter", claim, "confirmed"
            count, text = _count_near(binding, observations)
            if count is not None:
                record.count = count
                record.covered = len(claim.matched_geometry)
                record.notes.append(
                    f"'{text}' sayısı {record.covered} eşleşen geometriyle karşılaştırıldı.")
            return record
    claims = _distance_claims(binding, value_mm, sheet_px_per_mm, record.notes)
    if claims:
        record.form, record.claim = "distance", claims[0]
        seen_pairs = {tuple(sorted(point.geometry_id for point in claims[0].points))}
        for claim in claims[1:]:
            key = tuple(sorted(point.geometry_id for point in claim.points))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            record.alternatives.append(claim)
            if len(record.alternatives) == ALTERNATIVE_LIMIT:
                break
        record.resolution = "confirmed"
        if record.alternatives:
            pairs = ", ".join("/".join(point.geometry_id for point in claim.points)
                              for claim in record.alternatives)
            record.notes.append(f"Aynı ölçüyü veren başka aday çiftleri de var: {pairs}.")
        return record
    record.resolution = "unresolved"
    record.notes.append("Adaylar basılı değeri doğrulamadı.")
    return record


def meaning_page(path: str | Path) -> Meanings:
    """Every printed number of the sheet, read into the claim the drawing supports."""
    drawing = Path(path)
    bindings = bind_page(drawing)
    observations = observe(drawing)
    sized = _sized_geometry(observations)
    record = Meanings(source_ref=str(drawing), source_sha256=bindings.source_sha256,
                      sheet_px_per_mm=bindings.sheet_px_per_mm)
    for binding in bindings.spans:
        record.spans.append(_meaning_for(binding, observations, sized, bindings.sheet_px_per_mm))
    record.notes = [
        "distance: iki ankrajın adayları arasından basılı değeri tutan çiftler; sıra tür, sonra maliyet, sonra sapma.",
        "diameter/radius: liderin değeriyle çizili çapı/yarıçapı eşleşen geometri; matched_geometry tüm eşleşenler.",
        "count/covered: komşu 'N x' yazısı ve eşleşen geometri sayısı — ikisi tutmuyorsa kayıt bunu gösterir.",
        f"Sapma sınırı: basılı değerin %{int(RELATIVE_TOLERANCE * 100)}'ü ile {ABSOLUTE_TOLERANCE_MM:.2f} mm'nin büyüğü.",
        "Seçim yapılmayan durumlar 'unresolved' olarak durur; adaylar bindings.json'da zaten görünür.",
    ]
    return record


__all__ = ["Meanings", "SpanMeaning", "Claim", "ClaimPoint", "meaning_page", "Unsupported"]
