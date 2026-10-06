"""G5 deterministic target proposal (kök `PLAN.md` §10).

`callout region + current SemanticParse + current geometry + deterministic evidence → ranked
TargetProposal[]`, and nothing else: no store, no model, no OCR, no reference STEP, no filesystem.
A proposal is a *machine hint about which geometry the callout may name* — never a confirmation
(PLAN §4: "target proposal ≠ target confirmation"), and never an inference the drawing does not
support (`circle → hole` is not made here: a diameter callout on a circle says the circle's size, not
that a hole exists).

Evidence tiers, best first (PLAN §10):

* `T0` an explicit, still-current confirmation already stored for this callout;
* `T1` leader/arrow connectivity — a drawn line with one end inside the callout and the other on the
  target;
* `T2` dimension/extension-line topology — the sheet's *own* printed dimension for that geometry;
* `T3` semantic geometry compatibility — the form matches (Ø→circle/arc, R→arc, plain→vertex pair)
  and, where a user scale exists, the measured size agrees with the parsed size;
* `T4` count compatibility — the number of compatible pieces equals the parsed count;
* `T5` spatial proximity — the target simply sits in (or next to) the callout region.

The ranking is total and deterministic: `(tier, kind rank, primary distance, sorted ids)`. Every
proposal carries inspectable `EvidenceRef` rows; a callout whose target cannot be proposed gets `[]`,
which is a result, not a failure.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from drawingto3d.callout_models import (CALLOUT_PARSER_VERSION, EvidenceRef, callout_state,
                                        effective_callouts, sheet_unit)

__all__ = ["EVIDENCE_TIERS", "TARGET_KINDS", "TargetProposal", "propose_targets"]

TARGET_KINDS = ("circle", "circle_group", "arc", "vertex_pair", "profile")
"""What a proposal can name, best first within one tier: a group, one circle, an arc, two ends, a contour."""

_KIND_RANK = {"circle_group": 0, "circle": 1, "arc": 2, "vertex_pair": 3, "profile": 4}

EVIDENCE_TIERS = ("T0", "T1", "T2", "T3", "T4", "T5")

REGION_MARGIN = 0.02
"""How far outside its own box a callout still counts as "pointing at" nearby geometry (page units)."""

LEADER_TOUCH_PX = 6.0
"""A leader's far end within this many pixels of a circle's rim or centre is on it."""

SIZE_TOLERANCE = 0.08
"""A measured size agrees with the parsed one within 8 % (or 0.2 mm on small sizes) — no more."""

SIZE_ABSOLUTE_TOLERANCE_MM = 0.2

PROPOSAL_LIMIT = 8
"""How many proposals are offered at most: a long list is a menu, not evidence."""


class TargetProposal(BaseModel):
    """One ranked, inspectable candidate for what a callout names. Not a decision."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    target_kind: Literal["circle", "circle_group", "arc", "vertex_pair", "profile"]
    target_ids: list[str] = Field(min_length=1, max_length=100)
    geometry_version: int = Field(ge=0)
    evidence_tier: Literal["T0", "T1", "T2", "T3", "T4", "T5"]
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=50)

    def unique_ids(self) -> list[str]:
        return sorted(set(self.target_ids))


def _frame_scale(options: dict) -> tuple[float, float]:
    frame = options.get("frame") or {}
    return float(frame.get("width") or 0.0), float(frame.get("height") or 0.0)


def _region_px(region: list[float], width: float, height: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(value) for value in region)
    return x0 * width, y0 * height, x1 * width, y1 * height


def _inside(point, box: tuple[float, float, float, float], margin_px: float = 0.0) -> bool:
    x0, y0, x1, y1 = box
    return x0 - margin_px <= point[0] <= x1 + margin_px and y0 - margin_px <= point[1] <= y1 + margin_px


def _box_distance(point, box: tuple[float, float, float, float]) -> float:
    """Distance from a point to a box: 0 when inside, otherwise the gap to the nearest edge."""
    x0, y0, x1, y1 = box
    dx = max(x0 - point[0], 0.0, point[0] - x1)
    dy = max(y0 - point[1], 0.0, point[1] - y1)
    return math.hypot(dx, dy)


def _measured_size_agrees(measured_radius_px: float | None, size: float, unit: str | None,
                          px_per_mm: float | None, *, diameter: bool) -> bool | None:
    """Does the drawn size match the printed one? `None` when the user has no scale yet."""
    if px_per_mm is None or measured_radius_px is None or size is None or unit is None:
        return None
    in_mm = size * 25.4 if unit == "in" else size
    measured = (2.0 if diameter else 1.0) * float(measured_radius_px) / float(px_per_mm)
    return abs(measured - in_mm) <= max(SIZE_TOLERANCE * in_mm, SIZE_ABSOLUTE_TOLERANCE_MM)


def _px_per_mm(record: dict, given: float | None) -> float | None:
    if given is not None:
        return float(given)
    sketch = record.get("sketch") or {}
    value = sketch.get("px_per_mm")
    return None if value is None else float(value)


def _circles(options: dict) -> list[dict]:
    rows = []
    for circle in options.get("circles") or []:
        center = circle.get("center") or []
        if circle.get("id") and len(center) == 2 and circle.get("radius"):
            rows.append({"id": str(circle["id"]), "center": [float(center[0]), float(center[1])],
                         "radius": float(circle["radius"])})
    return rows


def _arcs(options: dict) -> list[dict]:
    rows = []
    for row in options.get("primitives") or []:
        if row.get("kind") != "arc" or not row.get("id"):
            continue
        center, radius = row.get("center"), row.get("radius")
        if not center or not radius:
            continue
        rows.append({"id": str(row["id"]), "center": [float(center[0]), float(center[1])],
                     "radius": float(radius), "start": [float(v) for v in row.get("start") or []],
                     "end": [float(v) for v in row.get("end") or []]})
    return rows


def _lines(options: dict) -> list[dict]:
    rows = []
    for row in options.get("primitives") or []:
        if row.get("kind") != "line" or not row.get("id"):
            continue
        if not row.get("start") or not row.get("end"):
            continue
        rows.append({"id": str(row["id"]), "start": [float(v) for v in row["start"]],
                     "end": [float(v) for v in row["end"]]})
    return rows


def _profiles(options: dict) -> list[dict]:
    return [row for row in options.get("profiles") or [] if row.get("id") and row.get("kind") == "wire"]


def _printed_dimension(record: dict, geometry_id: str, size_mm: float | None) -> dict | None:
    """The sheet's own printed number for this geometry, if the reading bound one to it (T2)."""
    reading = record.get("reading") or {}
    for claim in reading.get("claims") or []:
        ids = {str(anchor.get("geometry_id")) for anchor in claim.get("anchors") or []}
        ids |= {str(item) for item in claim.get("matched_geometry") or []}
        if geometry_id not in ids:
            continue
        printed = claim.get("printed_mm")
        if size_mm is None or (printed is not None
                               and abs(float(printed) - size_mm) <= max(SIZE_TOLERANCE * size_mm,
                                                                        SIZE_ABSOLUTE_TOLERANCE_MM)):
            return claim
    return None


def _current_parse(record: dict, callout_id: str) -> dict | None:
    """The parse row that is current for this callout's own text — never a stale one."""
    decisions = record.get("decisions") or {}
    transcription = next((row for row in decisions.get("transcriptions") or []
                          if row.get("callout_id") == callout_id), None)
    if transcription is None:
        return None
    exact = [row for row in record.get("callout_parses") or []
             if row.get("callout_id") == callout_id
             and row.get("transcription_revision") == transcription.get("revision")
             and row.get("parser_version") == CALLOUT_PARSER_VERSION]
    return exact[0] if len(exact) == 1 else None


def _evidence(kind: str, ref: str) -> EvidenceRef:
    return EvidenceRef(kind=kind, ref=ref)


def _tier(tiers: list[str]) -> Literal["T0", "T1", "T2", "T3", "T4", "T5"]:
    best = min(tiers, key=lambda code: EVIDENCE_TIERS.index(code))
    return best  # type: ignore[return-value]  # adaylar EVIDENCE_TIERS'tan üretilir


def _rank(proposal: TargetProposal, distance: float) -> tuple:
    return (EVIDENCE_TIERS.index(proposal.evidence_tier), _KIND_RANK[proposal.target_kind],
            round(distance, 3), proposal.unique_ids())


def propose_targets(record: dict, callout_id: str, *, scale_px_per_mm: float | None = None,
                    limit: int = PROPOSAL_LIMIT) -> list[TargetProposal]:
    """Ranked target proposals for one callout, from this session's own evidence.

    Reads only the record (and an optional user scale the caller already computed). The callout must
    exist, not be ignored, and have a *current* parse that actually succeeded: without a readable text
    there is nothing to propose, and a proposal is never invented to fill the panel.
    """
    options = record.get("options") or {}
    callout = next((row for row in effective_callouts(record) if row.get("id") == callout_id), None)
    if callout is None or callout.get("ignored"):
        return []
    parse = _current_parse(record, callout_id)
    if parse is None or parse.get("status") != "parsed":
        return []
    size = parse.get("size")
    form = parse.get("form")
    count = parse.get("count")
    # A printed unit wins; the unit the user declared for the sheet (their calibration) resolves a
    # size the text left unit-less. With neither, sizes are simply not compared (never assumed).
    unit = parse.get("unit") or sheet_unit(record)
    if size is None or form is None:
        return []
    px_per_mm = _px_per_mm(record, scale_px_per_mm)

    width, height = _frame_scale(options)
    if width <= 0 or height <= 0:
        return []
    box = _region_px(callout.get("region") or [], width, height)
    margin = REGION_MARGIN * max(width, height)
    version = int(record.get("geometry_version") or 0)
    size_mm = float(size) * (25.4 if unit == "in" else 1.0)

    circles = _circles(options)
    arcs = _arcs(options)
    lines = _lines(options)
    profiles = _profiles(options)
    proposals: list[tuple[float, TargetProposal]] = []

    def near(point) -> bool:
        return _inside(point, box, margin)

    def leader_hits(geometry: dict) -> str | None:
        """A leader line with one end in the callout and the other on this geometry (T1)."""
        for line in lines:
            for first, second in ((line["start"], line["end"]), (line["end"], line["start"])):
                if not _inside(first, box, margin):
                    continue
                to_center = math.dist(second, geometry["center"])
                if to_center <= geometry["radius"] + LEADER_TOUCH_PX or \
                        abs(to_center - geometry["radius"]) <= LEADER_TOUCH_PX:
                    return f"{line['id']}→{geometry['id']}"
        return None

    # --- diameter: circles (and, when the text counts, a group of them) --------------------
    if form == "diameter":

        def circle_evidence(circle: dict, agrees, distance: float, leader, printed) \
                -> tuple[list[str], list[EvidenceRef]]:
            tiers, evidence = [], []
            if leader:
                tiers.append("T1")
                evidence.append(_evidence("leader_connectivity", f"{leader} · uç daireye temas ediyor"))
            if printed is not None:
                tiers.append("T2")
                evidence.append(_evidence("printed_dimension",
                                          f"{printed.get('span_id')} · basılı {printed.get('printed_mm')} mm"))
            if agrees is True and px_per_mm:
                tiers.append("T3")
                evidence.append(_evidence("semantic_geometry",
                                          f"çizilen Ø{2 * circle['radius'] / px_per_mm:.3f} mm "
                                          f"≈ yazılan Ø{size_mm} mm"))
            elif agrees is None:
                tiers.append("T3")
                why = "ölçek yok" if px_per_mm is None else ("birim yok" if unit is None else "ölçü yok")
                evidence.append(_evidence("semantic_geometry", f"biçim uyumlu ({why}: ölçü karşılaştırılmadı)"))
            elif agrees is False and px_per_mm:
                evidence.append(_evidence("size_mismatch",
                                          f"çizilen Ø{2 * circle['radius'] / px_per_mm:.3f} mm "
                                          f"≠ yazılan Ø{size_mm} mm"))
            tiers.append("T5")
            evidence.append(_evidence("spatial_proximity",
                                      ("merkez callout bölgesinin içinde · " if _inside(circle["center"], box)
                                       else "merkez bölge dışında · ") + f"{distance:.2f} px"))
            return tiers, evidence

        rows = []
        for circle in circles:
            agrees = _measured_size_agrees(circle["radius"], size, unit, px_per_mm, diameter=True)
            leader = leader_hits(circle)
            printed = _printed_dimension(record, circle["id"], size_mm)
            # A target is only proposed when something *points* at it: the region, a leader, the
            # sheet's own printed number, or a size that agrees. Form alone points at everything.
            if not (near(circle["center"]) or leader or printed is not None or agrees is True):
                continue
            distance = math.hypot(circle["center"][0] - (box[0] + box[2]) / 2,
                                  circle["center"][1] - (box[1] + box[3]) / 2)
            rows.append((circle, agrees, distance, leader, printed))

        # Count compatibility first: the text says how many pieces it names.
        if count is not None and count > 1:
            ready = [row for row in rows if row[1] is not False]
            if len(ready) == count:
                tiers, evidence = [], []
                for circle, agrees, distance, leader, printed in ready:
                    sub, sub_evidence = circle_evidence(circle, agrees, distance, leader, printed)
                    tiers += sub
                    evidence += sub_evidence
                tiers.append("T4")
                by_fixed = len({round(2 * row[0]["radius"], 3) for row in ready}) == 1
                evidence.append(_evidence("count_compatibility",
                                          f"yazılan adet {count} = uyumlu daire sayısı {len(ready)}"
                                          f" ({'aynı çapta' if by_fixed else 'farklı çaplarda'})"))
                ids = [row[0]["id"] for row in ready]
                proposals.append((sum(row[2] for row in ready) / len(ready),
                                  TargetProposal(callout_id=callout_id, target_kind="circle_group",
                                                 target_ids=sorted(ids), geometry_version=version,
                                                 evidence_tier=_tier(tiers), evidence=evidence)))
            # The count is the text's own: a group that does not match it is not invented.
        for circle, agrees, distance, leader, printed in rows:
            tiers, evidence = circle_evidence(circle, agrees, distance, leader, printed)
            proposals.append((distance, TargetProposal(callout_id=callout_id, target_kind="circle",
                                                       target_ids=[circle["id"]], geometry_version=version,
                                                       evidence_tier=_tier(tiers), evidence=evidence)))

    # --- radius: arcs (and a whole circle, whose radius the callout may be naming) ---------
    if form == "radius":
        for arc in arcs:
            agrees = _measured_size_agrees(arc["radius"], size, unit, px_per_mm, diameter=False)
            leader = leader_hits(arc)
            printed = _printed_dimension(record, arc["id"], size_mm)
            if not (near(arc["center"]) or leader or printed is not None or agrees is True):
                continue
            distance = math.hypot(arc["center"][0] - (box[0] + box[2]) / 2,
                                  arc["center"][1] - (box[1] + box[3]) / 2)
            tiers, evidence = [], []
            if leader:
                tiers.append("T1")
                evidence.append(_evidence("leader_connectivity", f"{leader} · uç yaya temas ediyor"))
            if printed is not None:
                tiers.append("T2")
                evidence.append(_evidence("printed_dimension",
                                          f"{printed.get('span_id')} · basılı {printed.get('printed_mm')} mm"))
            if agrees is True and px_per_mm:
                tiers.append("T3")
                evidence.append(_evidence("semantic_geometry",
                                          f"çizilen R{arc['radius'] / px_per_mm:.3f} mm ≈ yazılan R{size_mm} mm"))
            elif agrees is None:
                tiers.append("T3")
                why = "ölçek yok" if px_per_mm is None else ("birim yok" if unit is None else "ölçü yok")
                evidence.append(_evidence("semantic_geometry", f"biçim uyumlu ({why}: ölçü karşılaştırılmadı)"))
            tiers.append("T5")
            evidence.append(_evidence("spatial_proximity", f"yay callout bölgesine yakın · {distance:.2f} px"))
            proposals.append((distance, TargetProposal(callout_id=callout_id, target_kind="arc",
                                                       target_ids=[arc["id"]], geometry_version=version,
                                                       evidence_tier=_tier(tiers), evidence=evidence)))
        for circle in circles:
            agrees = _measured_size_agrees(circle["radius"], size, unit, px_per_mm, diameter=False)
            if agrees is not True:
                continue                     # bir dairenin *yarıçapı* yazılmışsa ölçü tutmalıdır
            distance = math.hypot(circle["center"][0] - (box[0] + box[2]) / 2,
                                  circle["center"][1] - (box[1] + box[3]) / 2)
            proposals.append((distance, TargetProposal(
                callout_id=callout_id, target_kind="circle", target_ids=[circle["id"]],
                geometry_version=version, evidence_tier="T3",
                evidence=[_evidence("semantic_geometry",
                                    f"çizilen R{circle['radius'] / px_per_mm:.3f} mm ≈ yazılan R{size_mm} mm")])))

    # --- plain linear: two ends of one drawn edge (and a contour whose own size is the number) -
    if form == "linear":
        wanted_px = None if px_per_mm is None else size_mm * px_per_mm
        chosen = (record.get("decisions") or {}).get("profile_id")
        for profile in profiles:
            edges = [edge for edge in profile.get("edges") or [] if edge.get("id")]
            for edge in edges:
                first, second = edge.get("start"), edge.get("end")
                if not first or not second:
                    continue
                span = math.dist(first, second)
                agrees = None if wanted_px is None else abs(span - wanted_px) <= \
                    max(SIZE_TOLERANCE * wanted_px, SIZE_ABSOLUTE_TOLERANCE_MM * (px_per_mm or 1.0))
                middle = [(first[0] + second[0]) / 2, (first[1] + second[1]) / 2]
                if agrees is False and not near(middle):
                    continue                        # ölçü tutmuyor ve bölgeye de yakın değil
                distance = _box_distance(middle, box)
                tiers, evidence = ["T3"], []
                evidence.append(_evidence("semantic_geometry",
                                          f"iki uç arası {span:.2f} px"
                                          + (f" ≈ yazılan {size_mm} mm" if wanted_px is not None else
                                             " (ölçü karşılaştırılmadı)")))
                if profile.get("id") == chosen:
                    evidence.append(_evidence("semantic_geometry", "seçili konturun kendi kenarı"))
                tiers.append("T5")
                evidence.append(_evidence("spatial_proximity",
                                          ("ölçünün ortası bölgenin içinde · " if near(middle)
                                           else "ölçünün ortası bölgeye yakın · ") + f"{distance:.2f} px"))
                proposals.append((distance, TargetProposal(callout_id=callout_id, target_kind="vertex_pair",
                                                           target_ids=[f"{edge['id']}:start", f"{edge['id']}:end"],
                                                           geometry_version=version,
                                                           evidence_tier=_tier(tiers), evidence=evidence)))
            if wanted_px is not None and px_per_mm:
                points = profile.get("points") or []
                if len(points) >= 3:
                    xs = [float(point[0]) for point in points]
                    ys = [float(point[1]) for point in points]
                    drawn = [(max(xs) - min(xs)) / px_per_mm, (max(ys) - min(ys)) / px_per_mm]
                    if any(abs(value - size_mm) <= max(SIZE_TOLERANCE * size_mm, SIZE_ABSOLUTE_TOLERANCE_MM)
                           for value in drawn):
                        center = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
                        if not (near(center) or profile.get("id") == chosen):
                            continue                # ne bölge ne seçili kontur: öneri dayanaksız
                        distance = _box_distance(center, box)
                        proposals.append((distance, TargetProposal(
                            callout_id=callout_id, target_kind="profile", target_ids=[profile["id"]],
                            geometry_version=version, evidence_tier="T3",
                            evidence=[_evidence("semantic_geometry",
                                                f"kontur ölçüsü {drawn[0]:.2f}×{drawn[1]:.2f} mm "
                                                f"yazılan {size_mm} mm ile uyuşuyor")])))

    # --- T0: what the user already confirmed, while it is still current --------------------
    decisions = record.get("decisions") or {}
    stored = next((row for row in decisions.get("callout_targets") or []
                   if row.get("callout_id") == callout_id), None)
    if stored is not None:
        from drawingto3d.callout_models import callout_state
        state = callout_state(record, callout_id)
        if state and state["target"]["state"] == "current":
            proposals.insert(0, (0.0, TargetProposal(
                callout_id=callout_id, target_kind=stored.get("target_kind"),
                target_ids=[str(item) for item in stored.get("target_ids") or []],
                geometry_version=version, evidence_tier="T0",
                evidence=[_evidence("stored_confirmation",
                                    f"kullanıcı bu hedefi onaylamıştı · revizyon {stored.get('transcription_revision')}"
                                    f" · {stored.get('parser_version')}")])))

    proposals.sort(key=lambda item: _rank(item[1], item[0]))
    return [item[1] for item in proposals[:max(1, int(limit))]]
