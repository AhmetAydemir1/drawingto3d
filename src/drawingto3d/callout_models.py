"""G1 callout transcription contract (PLAN-20 §6).

Four records, three layers kept apart:

* `CalloutCandidate` — what the machine found (a region; a text hint is a hint, never a decision);
* `TranscriptionDecision` — the user's own text, kept verbatim, with the server's own separate
  normalization and the user's revision identity;
* `SemanticParse` — a *computed* result bound to (callout, transcription revision, parser version);
* `CalloutTargetDecision` — the user's confirmation of *which geometry* the callout names, pinned to
  the geometry/context fingerprint it was confirmed against.

The store (`guided.py`) integrates these; this module never imports it (no cycles). Freshness is
computed, never asserted: `callout_states` answers current/stale/missing with a machine reason code
for every callout, and computing it never creates a confirmation. G1 ships no working parser — a
parse is current only when a record was written against the *same expected parser version*
(`CALLOUT_PARSER_VERSION`, an explicit parameter the G4 parser will feed).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CALLOUT_SCHEMA_VERSION = 1
"""Version of the callout layer itself (PLAN-20 §6.1) — *not* `guided.GEOMETRY_VERSION`.

Adding the callout fields must never bump the geometry contract; a change to these records bumps
this number instead.
"""

CALLOUT_PARSER_VERSION = "callout-parser/1"
"""The parser contract version this slice expects (PLAN-20 §6.5).

G1 stores no parser, so this is the explicit expectation freshness is judged against: a parse
record is current only while it was written for this same version. G4 feeds the real parser's
version here; a version change stales every parse (and every target bound to one) without ever
making an old confirmation silently current again. Not a SEMREAD reader version.
"""


def normalize_text(raw_text: str) -> str:
    """G1 normalization: documented whitespace editing only (PLAN-20 §6.3).

    Every run of whitespace collapses to one space and the ends are trimmed; everything else —
    symbols like `Ø`, `×`, `THRU` included — is preserved exactly. Semantic normalization
    (`⌀`→`Ø`, `,` decimals, fractions, threads) belongs to the versioned parser (G4), so this
    function must not guess any of it.
    """
    return " ".join(str(raw_text).split())


def _check_region(value: list[float]) -> list[float]:
    """One coordinate contract (PLAN-20 §6.2): 0..1 page coordinates, top-left origin, finite, drawn."""
    if len(value) != 4:
        raise ValueError("bölge dört sayı olmalı: [x0, y0, x1, y1]")
    x0, y0, x1, y1 = (float(item) for item in value)
    for item in (x0, y0, x1, y1):
        if not math.isfinite(item):
            raise ValueError("bölge yalnız sonlu sayılar içerebilir")
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        raise ValueError(f"bölge sayfa içinde artan bir kutu olmalı (0..1): {list(value)}")
    return [x0, y0, x1, y1]


def _no_bool(value):
    """`True` is not an index, a revision or a count — Pydantic's lax mode would coerce it to 1."""
    if isinstance(value, bool):
        raise ValueError("bool kabul edilmez")
    return value


class CalloutCandidate(BaseModel):
    """One machine-found callout region — observation and identity, no decision."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=1, max_length=200)   # the session source it was found in
    page_index: int = Field(ge=0)
    region: list[float] = Field(min_length=4, max_length=4)
    crop_region: list[float] = Field(min_length=4, max_length=4)
    source_kind: Literal["vector_text", "observation", "raster_region", "manual"]
    observation_ids: list[str] = Field(default_factory=list, max_length=200)
    detector_version: str = Field(min_length=1, max_length=120)
    geometry_version: int = Field(ge=0)
    machine_text_hint: str | None = None   # a hint only — it never becomes a transcription by itself

    @field_validator("page_index", "geometry_version", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)

    @field_validator("region", "crop_region")
    @classmethod
    def _region(cls, value):
        return _check_region(value)

    @model_validator(mode="after")
    def _crop_covers_region(self):
        x0, y0, x1, y1 = self.region
        cx0, cy0, cx1, cy1 = self.crop_region
        if not (cx0 <= x0 and cy0 <= y0 and cx1 >= x1 and cy1 >= y1):
            raise ValueError("crop_region region'u kapsamalı (görüntü kolaylığı; sayfa sınırlarında kalır)")
        return self


class TranscriptionDecision(BaseModel):
    """The user's own text for one callout (PLAN-20 §6.3); `raw_text` is stored exactly as typed."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    raw_text: str = Field(min_length=1)
    normalized_text: str = ""      # the server's derivation — a client value is replaced on validation
    entered_by: Literal["user"] = "user"
    source_region: list[float] = Field(min_length=4, max_length=4)
    revision: int = Field(default=0, ge=0)   # the server's revision id for this text/region decision

    @field_validator("raw_text")
    @classmethod
    def _non_blank(cls, value):
        if not value.strip():
            raise ValueError("boş veya yalnız boşluk metni transcription olarak kaydedilemez")
        return value

    @field_validator("source_region")
    @classmethod
    def _region(cls, value):
        return _check_region(value)

    @field_validator("revision", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)

    @model_validator(mode="after")
    def _derive_normalized(self):
        derived = normalize_text(self.raw_text)
        if self.normalized_text != derived:
            self.normalized_text = derived      # never trust a client-provided normalization
        return self


class SemanticParse(BaseModel):
    """A deterministic parse result bound to its transcription revision and parser version."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    parser_version: str = Field(min_length=1, max_length=120)
    transcription_revision: int = Field(ge=0)
    status: Literal["parsed", "ambiguous", "unsupported"]
    form: Literal["diameter", "radius", "linear"] | None = None
    size: float | None = Field(default=None, gt=0, le=1e6)
    count: int | None = Field(default=None, ge=1)          # only an explicit positive integer
    termination: Literal["thru", "blind"] | None = None
    depth: float | None = Field(default=None, gt=0, le=1e6)
    unit: Literal["mm", "in"] | None = None                # only when printed explicitly
    warnings: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("transcription_revision", "count", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)


class EvidenceRef(BaseModel):
    """One inspectable reference behind a confirmation (PLAN-20 §6.3): kind + where to look.

    A bare free-text string is deliberately not enough.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    kind: str = Field(min_length=1, max_length=60)
    ref: str = Field(min_length=1, max_length=2000)


class CalloutTargetDecision(BaseModel):
    """The user's confirmation of which geometry a callout names (PLAN-20 §6.3).

    `status` is the *historical* fact that the user confirmed this; whether it still holds is
    computed separately (`callout_states`) from the parse binding and the geometry fingerprint.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    target_kind: Literal["circle", "circle_group", "vertex_pair"]
    target_ids: list[str] = Field(min_length=1, max_length=100)
    geometry_version: int = Field(default=0, ge=0)
    geometry_key: str = ""     # the server pins the real fingerprint at save time
    profile_id: str | None = None
    transcription_revision: int = Field(ge=0)
    parser_version: str = Field(min_length=1, max_length=120)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=50)
    status: Literal["confirmed"] = "confirmed"

    @field_validator("geometry_version", "transcription_revision", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)

    @model_validator(mode="after")
    def _cardinality(self):
        unique = set(self.target_ids)
        if len(unique) != len(self.target_ids):
            raise ValueError("hedef kimlikleri benzersiz olmalı (aynı ID tekrar edilemez)")
        if self.target_kind == "circle" and len(self.target_ids) != 1:
            raise ValueError("circle hedefi tam olarak 1 geometri kimliği ister")
        if self.target_kind == "circle_group" and len(self.target_ids) < 2:
            raise ValueError("circle_group en az 2 benzersiz hedef ister")
        if self.target_kind == "vertex_pair" and len(self.target_ids) != 2:
            raise ValueError("vertex_pair farklı 2 uç kimliği ister (sıra korunur)")
        return self


# --- geometry/context fingerprint -------------------------------------------------

def _numbers(value) -> list[float] | None:
    return None if value is None else [float(item) for item in value]


def _profile_row(profile: dict) -> dict:
    """One contour as the fingerprint sees it: edges in their own order (never re-sorted)."""
    row = {"id": str(profile.get("id")), "kind": profile.get("kind")}
    edges = []
    for edge in profile.get("edges") or []:
        item = {"id": str(edge.get("id")), "kind": edge.get("kind")}
        for key in ("start", "end", "center"):
            if edge.get(key) is not None:
                item[key] = _numbers(edge[key])
        for key in ("radius", "a", "b"):
            if edge.get(key) is not None:
                item[key] = float(edge[key])
        edges.append(item)
    row["edges"] = edges
    circle = profile.get("circle")
    if circle:
        row["circle"] = {"center": _numbers(circle.get("center")),
                         "radius": None if circle.get("radius") is None else float(circle["radius"])}
    return row


def _circle_row(circle: dict) -> dict:
    return {"id": str(circle.get("id")), "center": _numbers(circle.get("center")),
            "radius": None if circle.get("radius") is None else float(circle["radius"])}


def geometry_key(record: dict, decisions: dict | None = None) -> str:
    """The confirmed target's context fingerprint: canonical JSON + SHA-256 (PLAN-20 §6.4).

    Built from the source hash, the geometry version, the profiles' and circles' own identities and
    geometry, the selected profile, the contour edits and the view decision. Deliberately *not*
    from timestamps, logs, build/parse/target records or the user's other decisions — a target must
    never be invalidated by its own confirmation, and unrelated edits (say thickness) must not move
    the key. Dictionary keys are sorted and id-addressable lists are sorted by stable id; a
    contour's *edge order* is left exactly as the drawing has it.
    """
    record = record or {}
    decisions = decisions if decisions is not None else (record.get("decisions") or {})
    options = record.get("options") or {}
    contour = decisions.get("contour") or {}
    view = decisions.get("view")
    payload = {
        "source_sha256": record.get("source_sha256"),
        "geometry_version": record.get("geometry_version"),
        "profile_id": decisions.get("profile_id"),
        "contour": {"drop": sorted(str(item) for item in (contour.get("drop") or [])),
                    "approve_join": bool(contour.get("approve_join"))},
        "view": None if not view else {"x_page": _numbers(view.get("x_page")),
                                       "y_page": _numbers(view.get("y_page")),
                                       "frame_rect": _numbers(view.get("frame_rect")),
                                       "source": view.get("source")},
        "profiles": sorted((_profile_row(item) for item in options.get("profiles") or []),
                           key=lambda row: row["id"]),
        "circles": sorted((_circle_row(item) for item in options.get("circles") or []),
                          key=lambda row: row["id"]),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --- freshness: current / stale / missing, with machine reason codes ---------------

def _transcription_state(transcription: dict | None) -> dict:
    if transcription is None:
        return {"state": "missing", "revision": None, "reason": "needs_transcription"}
    return {"state": "current", "revision": transcription.get("revision"), "reason": None}


def _parse_state(callout_id: str, transcription: dict | None, parses: list[dict],
                 expected_parser_version: str, record: dict) -> dict:
    mine = [row for row in parses if row.get("callout_id") == callout_id]
    # PLAN-20 §7 (source changed/unreadable or geometry stale): an existing parse cannot be served
    # as current data any more — the page it was read off is no longer verifiable.
    if record.get("geometry_stale") and mine:
        return {"state": "stale", "reason": "source_unavailable"}
    if transcription is None:
        if mine:
            return {"state": "stale", "reason": "transcription_missing"}
        return {"state": "missing", "reason": "needs_parse"}
    revision = transcription.get("revision")
    exact = [row for row in mine if row.get("transcription_revision") == revision
             and row.get("parser_version") == expected_parser_version]
    if exact:
        distinct = {json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) for row in exact}
        if len(distinct) > 1:
            return {"state": "stale", "reason": "parse_conflict"}
        return {"state": "current", "reason": None}
    if not mine:
        return {"state": "missing", "reason": "needs_parse"}
    if any(row.get("transcription_revision") != revision for row in mine):
        return {"state": "stale", "reason": "transcription_changed"}
    return {"state": "stale", "reason": "parser_version_changed"}


def _target_state(callout_id: str, transcription: dict | None, target: dict | None, parses: list[dict],
                  key: str, record: dict, expected_parser_version: str) -> dict:
    """Reason priority, first one wins: source_unavailable → transcription_missing →
    transcription_changed → parser_version_changed → geometry_changed → parse_missing/parse_conflict."""
    if target is None:
        return {"state": "missing", "reason": "needs_target"}
    reasons: list[str] = []
    if record.get("geometry_stale"):
        reasons.append("source_unavailable")
    if transcription is None:
        reasons.append("transcription_missing")
    elif target.get("transcription_revision") != transcription.get("revision"):
        reasons.append("transcription_changed")
    if target.get("parser_version") != expected_parser_version:
        reasons.append("parser_version_changed")
    if target.get("geometry_key") != key or target.get("geometry_version") != record.get("geometry_version"):
        reasons.append("geometry_changed")
    if not reasons:
        exact = [row for row in parses if row.get("callout_id") == callout_id
                 and row.get("transcription_revision") == target.get("transcription_revision")
                 and row.get("parser_version") == target.get("parser_version")]
        if not exact:
            reasons.append("parse_missing")
        else:
            distinct = {json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) for row in exact}
            if len(distinct) > 1:
                reasons.append("parse_conflict")
    return {"state": "current" if not reasons else "stale", "reason": reasons[0] if reasons else None}


def callout_states(record: dict, expected_parser_version: str | None = None) -> list[dict]:
    """The per-callout freshness picture the public state shows (PLAN-20 §6.4/§7).

    Every callout gets its transcription/parse/target state (`current` / `stale` / `missing`) and a
    machine reason code — computed from records, never asserted by them. This computation creates
    no confirmation and never re-pins anything.
    """
    expected = expected_parser_version or CALLOUT_PARSER_VERSION
    decisions = record.get("decisions") or {}
    transcriptions = {row.get("callout_id"): row for row in decisions.get("transcriptions") or []}
    targets = {row.get("callout_id"): row for row in decisions.get("callout_targets") or []}
    parses = record.get("callout_parses") or []
    key = geometry_key(record, decisions)
    rows = []
    for candidate_row in record.get("callout_candidates") or []:
        callout_id = candidate_row.get("id")
        transcription = transcriptions.get(callout_id)
        rows.append({
            "id": callout_id,
            "page_index": candidate_row.get("page_index"),
            "source_kind": candidate_row.get("source_kind"),
            "transcription": _transcription_state(transcription),
            "parse": _parse_state(callout_id, transcription, parses, expected, record),
            "target": _target_state(callout_id, transcription, targets.get(callout_id), parses,
                                    key, record, expected),
        })
    return rows
