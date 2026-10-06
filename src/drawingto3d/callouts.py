"""G2 deterministic callout candidate adapter (kök `PLAN.md` / `docs/PLAN-21.md` §6–§18).

`observations → CalloutCandidate[] + diagnostics`, and nothing else: no store, no CAD, no model,
no filesystem, no second observe/OCR. A candidate is a *region with provenance* — the printed text
stays a machine hint. `TextObservation.value/unit/kind/count` are not semantic truth and never
become decisions here (PLAN-18 §4).

Identity is the canonical JSON + SHA-256 of (source digest, page, canonical region, detector
version, source kind) — never the source path, filename, text, confidence, list index, UUID or a
Python `hash()` (§14). Invalid observations are skipped with a diagnostic; nothing is clamped
(§9/§17). Blank printed phrases cannot reach this layer — verified against the real producers:
`ingest.text_groups` drops whitespace characters entirely and `raster` filters empty phrases — so
no blank-text branch is invented (§90).

One canonicalization point (`REGION_DECIMALS`) serves both the stored region and the identity
payload, so a candidate's stored region is exactly what its ID was computed from (§11). The region
must survive canonicalization: a box that collapses to zero width/height in the canonical frame is
skipped with `region_collapsed` rather than being clamped (§17 "clamp yok"). Provenance is the
sorted unique union; a union beyond the schema's own limit is truncated *honestly* with
`provenance_ids_capped` (§89, `CalloutCandidate.observation_ids` max_length).

Diagnostics are deterministic: deduplicated (code, observation id) pairs, sorted by code then id.
Diagnostic codes: `invalid_frame`, `unsupported_page`, `invalid_bbox_nonfinite`, `invalid_bbox_area`,
`bbox_outside_frame`, `unknown_text_method`, `duplicate_hint_conflict`, `no_text_observations`,
`region_collapsed`, `provenance_ids_capped`.
"""
from __future__ import annotations

import hashlib
import json
import math

from pydantic import BaseModel, ConfigDict, Field

from drawingto3d.callout_models import CalloutCandidate
from drawingto3d.observe import Observations
from drawingto3d.schema import BBox

CALLOUT_DETECTOR_VERSION = "callout-detector/1"
"""The single source of the producer contract version (PLAN-18 §7).

Bump when *what* this adapter produces or how regions are canonicalized changes (region
canonicalization, source selection, phrase grouping, merge/split rules); UI crop padding or display
labels are not producer changes.
"""

REGION_DECIMALS = 8
"""The one canonicalization point for stored regions and identity payloads (PLAN-18 §11)."""

_METHOD_SOURCE_KINDS = {"pdf-text": "vector_text", "tesseract-tsv": "raster_region"}
"""Method is the only authority for source kind (PLAN-18 §12): never inferred from a file suffix."""

_PROVENANCE_LIMIT = 200  # CalloutCandidate.observation_ids'in şema sınırı


class DetectionDiagnostic(BaseModel):
    """One deterministic reason an observation did not become (or shaped) a candidate (PLAN-18 §92)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=60)
    observation_id: str | None = None   # sayfa/çerçeve düzeyinde sorunlarda None


class CalloutDetection(BaseModel):
    """A small computed transport (PLAN-18 §8) — not a new user-decision model."""

    model_config = ConfigDict(extra="forbid")

    detector_version: str = Field(min_length=1, max_length=120)
    candidates: list[CalloutCandidate] = Field(default_factory=list)
    diagnostics: list[DetectionDiagnostic] = Field(default_factory=list)


def _canonical_region(region: list[float]) -> list[float]:
    return [float(round(value, REGION_DECIMALS)) for value in region]


def _identity(source_digest: str, page_index: int, region: list[float],
              detector_version: str, source_kind: str) -> str:
    """PLAN-18 §14: canonical JSON + SHA-256 over exactly these five fields."""
    payload = {"detector_version": detector_version, "page_index": page_index, "region": region,
               "source_digest": source_digest, "source_kind": source_kind}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _bbox_issue(bbox: BBox, width: float, height: float) -> str | None:
    """PLAN-18 §17: finite, positive area, fully inside the frame — otherwise the reason to skip."""
    x, y, w, h = float(bbox.x), float(bbox.y), float(bbox.w), float(bbox.h)
    if not all(math.isfinite(value) for value in (x, y, w, h)):
        return "invalid_bbox_nonfinite"
    if w <= 0 or h <= 0:
        return "invalid_bbox_area"
    if x < 0 or y < 0 or x + w > width or y + h > height:
        return "bbox_outside_frame"
    return None


def callout_candidates_from_observations(observations: Observations, *, geometry_version: int,
                                         detector_version: str = CALLOUT_DETECTOR_VERSION) -> CalloutDetection:
    """Turn one observation record's printed phrases into deterministic candidate regions.

    The returned candidates are sorted canonically (top-left first: y0, x0, y1, x1, kind, id) so the
    same drawing yields the same list whatever order the input phrases arrived in (§16). The input
    record is only read.
    """
    frame = observations.frame
    width, height = float(frame.width or 0), float(frame.height or 0)
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
        return CalloutDetection(detector_version=detector_version,
                                diagnostics=[DetectionDiagnostic(code="invalid_frame")])
    source = observations.source
    if source.page != 0:
        return CalloutDetection(detector_version=detector_version,   # sayfa sessizce 0'a çevrilmez
                                diagnostics=[DetectionDiagnostic(code="unsupported_page")])

    diagnostics: set[tuple[str, str | None]] = set()
    groups: dict[tuple, dict] = {}
    for observation in observations.texts:
        source_kind = _METHOD_SOURCE_KINDS.get(observation.method)
        if source_kind is None:
            source_kind = "observation"                              # makine adaptörü `manual` üretmez
            diagnostics.add(("unknown_text_method", observation.id))
        issue = _bbox_issue(observation.bbox, width, height)
        if issue is not None:
            diagnostics.add((issue, observation.id))
            continue
        bbox = observation.bbox
        region = _canonical_region([float(bbox.x) / width, float(bbox.y) / height,
                                    (float(bbox.x) + float(bbox.w)) / width,
                                    (float(bbox.y) + float(bbox.h)) / height])
        if not (0.0 <= region[0] < region[2] <= 1.0 and 0.0 <= region[1] < region[3] <= 1.0):
            diagnostics.add(("region_collapsed", observation.id))
            continue
        key = (source.sha256, source.page, tuple(region), detector_version, source_kind)
        group = groups.get(key)
        if group is None:
            groups[key] = {"region": region, "source_kind": source_kind,
                           "ids": {observation.id}, "hints": {observation.text}}
        else:
            group["ids"].add(observation.id)
            group["hints"].add(observation.text)

    if not observations.texts:
        diagnostics.add(("no_text_observations", None))              # dürüst boş sonuç; kutu uydurulmaz

    candidates: list[CalloutCandidate] = []
    for (digest, page, region_tuple, version, source_kind), group in groups.items():
        ids = sorted(group["ids"])
        if len(ids) > _PROVENANCE_LIMIT:
            diagnostics.add(("provenance_ids_capped", ids[0]))
            ids = ids[:_PROVENANCE_LIMIT]
        hints = group["hints"]
        if len(hints) == 1:
            hint = next(iter(hints))
        else:
            hint = None                                               # çelişen ipucu gerçek değildir (§15)
            diagnostics.add(("duplicate_hint_conflict", ids[0]))
        region = list(region_tuple)
        candidates.append(CalloutCandidate(
            id=_identity(digest, page, region, version, source_kind),
            source_digest=digest, page_index=page, region=region, crop_region=region,
            source_kind=source_kind, observation_ids=ids, detector_version=version,
            geometry_version=geometry_version, machine_text_hint=hint))
    candidates.sort(key=lambda row: (row.region[1], row.region[0], row.region[3], row.region[2],
                                     row.source_kind, row.id))
    rows = [DetectionDiagnostic(code=code, observation_id=observation_id)
            for code, observation_id in sorted(diagnostics, key=lambda item: (item[0], item[1] or ""))]
    return CalloutDetection(detector_version=detector_version, candidates=candidates, diagnostics=rows)


__all__ = ["CALLOUT_DETECTOR_VERSION", "REGION_DECIMALS", "DetectionDiagnostic", "CalloutDetection",
           "callout_candidates_from_observations"]
