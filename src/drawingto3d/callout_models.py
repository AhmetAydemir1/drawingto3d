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
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CALLOUT_SCHEMA_VERSION = 3
"""Version of the callout layer itself (PLAN-20 §6.1) — *not* `guided.GEOMETRY_VERSION`.

Adding the callout fields must never bump the geometry contract; a change to these records bumps
this number instead. G3 added the user's own region/ignore decisions (`manual_callouts`,
`callout_reviews`) to the persisted structure, so the written version moved to 2; G5–GX add what the
binding chain needs and move it to 3:

* `CalloutTargetDecision.target_kind` also names `arc` and `profile` — PLAN §10 asks for an arc
  candidate for a radius and a contour candidate for a linear callout, and neither is honestly
  expressible as a circle or a pair of ends. Additive: the three older kinds still validate.
* `CalloutReviewDecision.unbindable` — the user's own "this callout cannot be bound" verdict, so a
  reviewed-and-excluded callout is a declared scope decision instead of silent absence.
* `TranscriptionDecision.entered_by` may be `external_review` — GX import provenance on the row
  itself, so an imported text never looks like something the user typed here.

A record that is merely *loaded* is never rewritten because of it (PLAN-21 §6.1)."""

MANUAL_ID_PREFIX = "manual:"
"""The user-created callout's own namespace (PLAN-21 §6.1).

The G2 detector's determinism ban on uuids does not apply here: adding an area is a *user* act, and
a per-act identity is what keeps two regions drawn at the same place two decisions. The namespace
also keeps a server-assigned id from ever colliding with a detected candidate's id.
"""
MANUAL_ID_PATTERN = r"manual:[0-9a-f]{32}"

CALLOUT_PARSER_VERSION = "callout-parser/2"
"""The parser contract version this slice expects (PLAN-20 §6.5).

v2 reads the standard `THRU ALL` qualifier (a word the grammar knows only behind THRU) — the plate
sheet's own `4 x Ø6,80 THRU ALL` note — so parses computed under v1 are stale by design.

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


def _check_region(value) -> list[float]:
    """One coordinate contract (PLAN-20 §6.2): 0..1 page coordinates, top-left origin, finite, drawn."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
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


def check_region(value) -> list[float]:
    """The one region contract, callable on its own (PLAN-21 §6.4).

    The store's user commands check a region *before* building a record from it, so a bad box is
    named as a bad box rather than as a wrapped validation error.
    """
    return _check_region(value)


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


class ManualCalloutDecision(BaseModel):
    """A callout area the user drew themselves (PLAN-21 §6.1) — a user decision, not a detection.

    The identity is the server's: `manual:<uuid4 hex>`, assigned once when the region is added and
    kept for the life of the record (refresh and undo included). Source, page and revision are the
    server's too; a client can neither borrow another session's identity nor name its own.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=1, max_length=200)
    page_index: int = Field(ge=0)
    region: list[float] = Field(min_length=4, max_length=4)
    revision: int = Field(default=0, ge=0)

    @field_validator("id")
    @classmethod
    def _namespace(cls, value):
        if not re.fullmatch(MANUAL_ID_PATTERN, str(value)):
            raise ValueError(f"manual callout kimliği '{MANUAL_ID_PREFIX}<uuid>' biçiminde olmalı (sunucu atar)")
        return value

    @field_validator("page_index", "revision", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)

    @field_validator("region")
    @classmethod
    def _region(cls, value):
        return _check_region(value)


class CalloutReviewDecision(BaseModel):
    """The user's own review of one callout: a corrected region and/or "not a callout" (PLAN-21 §6.1).

    At most one record per callout. A region override never deletes the detected region or its
    provenance — it only changes which region is *effective*; an ignored callout keeps its text and
    its history. A record that carries neither decision is meaningless and is not stored.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    region_override: list[float] | None = None
    ignored: bool = False
    unbindable: bool = False     # "bağlanamaz": kullanıcının kapsam kararı (G6 panelindeki dördüncü düğme)
    revision: int = Field(default=0, ge=0)

    @field_validator("region_override")
    @classmethod
    def _region(cls, value):
        return None if value is None else _check_region(value)

    @field_validator("revision", mode="before")
    @classmethod
    def _no_bool(cls, value):
        return _no_bool(value)

    @model_validator(mode="after")
    def _carries_a_decision(self):
        if self.region_override is None and not self.ignored and not self.unbindable:
            raise ValueError("gözden geçirme kaydı bir bölge düzeltmesi, yok sayma ya da "
                             "'bağlanamaz' kararı taşımalı")
        return self


class TranscriptionDecision(BaseModel):
    """The user's own text for one callout (PLAN-20 §6.3); `raw_text` is stored exactly as typed."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    raw_text: str = Field(min_length=1)
    normalized_text: str = ""      # the server's derivation — a client value is replaced on validation
    entered_by: Literal["user", "external_review"] = "user"
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
    `reconfirm` is the client's explicit re-confirmation request — consumed at save time and never
    persisted as true: a carried record is not re-confirmed by incidental field drift.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    callout_id: str = Field(min_length=1, max_length=120)
    target_kind: Literal["circle", "circle_group", "arc", "profile", "vertex_pair"]
    target_ids: list[str] = Field(min_length=1, max_length=100)
    geometry_version: int = Field(default=0, ge=0)
    geometry_key: str = ""     # the server pins the real fingerprint at save time
    profile_id: str | None = None
    transcription_revision: int = Field(ge=0)
    parser_version: str = Field(min_length=1, max_length=120)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=50)
    status: Literal["confirmed"] = "confirmed"
    reconfirm: bool = False   # açık yeniden-onay isteği; kaydederken tüketilir (kayıtta daima false)

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
        if self.target_kind == "arc" and len(self.target_ids) != 1:
            raise ValueError("arc hedefi tam olarak 1 yay kimliği ister")
        if self.target_kind == "profile" and len(self.target_ids) != 1:
            raise ValueError("profile hedefi tam olarak 1 kontur kimliği ister")
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


def sheet_unit(record: dict) -> str | None:
    """The unit the *user* declared for this sheet — their calibration's own unit, or nothing.

    A parse never fills a missing printed unit from here (G4 keeps `unit: None` and says
    `unit_unresolved`); the compiler and the binder may resolve a size with it because it is a
    decision the user made about the sheet, and they say so (`unit_source: "sheet"`).
    """
    calibration = (record.get("decisions") or {}).get("calibration") or {}
    unit = calibration.get("unit")
    return unit if unit in ("mm", "in") else None


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


# --- one effective view: base detections + the user's own regions and reviews --------------

CROP_PADDING = 0.02
"""How much context a derived crop adds around a region (PLAN-21 §6.2/§7.2).

A display convenience only: the crop is clipped to the page, and neither the base nor the effective
region is ever changed for the sake of a crop.
"""


def _crop_for(region: list[float]) -> list[float]:
    """A padded, page-clipped crop box around `region` — always covering it (PLAN-21 §6.2)."""
    x0, y0, x1, y1 = (float(value) for value in region)
    return [max(0.0, x0 - CROP_PADDING), max(0.0, y0 - CROP_PADDING),
            min(1.0, x1 + CROP_PADDING), min(1.0, y1 + CROP_PADDING)]


def _covering_crop(region: list[float], stored: list[float] | None) -> list[float]:
    """Keep the detector's own crop while it still covers the region; derive one when it does not.

    A region override can move the box past the crop the detector wrote — serving the stale crop
    then would show the user the wrong window, so the crop follows the effective region (the base
    region and the provenance are untouched either way).
    """
    if stored and len(stored) == 4:
        cx0, cy0, cx1, cy1 = (float(value) for value in stored)
        if cx0 <= region[0] and cy0 <= region[1] and cx1 >= region[2] and cy1 >= region[3]:
            return [cx0, cy0, cx1, cy1]
    return _crop_for(region)


def effective_callouts(record: dict) -> list[dict]:
    """The one list the store, the checks and the UI all use (PLAN-21 §6.2).

    Base G2 candidates, then the user's own manual regions, each carrying: its id, page, source
    kind, base and effective region, crop region, hint, ignored flag and provenance. Purely
    derived — computing this never creates a decision, writes history, or changes a region.
    """
    decisions = record.get("decisions") or {}
    reviews = {row.get("callout_id"): row for row in decisions.get("callout_reviews") or []}
    rows: list[dict] = []
    for candidate in record.get("callout_candidates") or []:
        callout_id = candidate.get("id")
        review = reviews.get(callout_id) or {}
        base = [float(value) for value in candidate.get("region") or []]
        override = review.get("region_override")
        region = [float(value) for value in override] if override else list(base)
        rows.append({
            "id": callout_id,
            "page_index": candidate.get("page_index"),
            "source_kind": candidate.get("source_kind"),
            "source_digest": candidate.get("source_digest"),
            "manual": False,
            "region": region,
            "base_region": base,
            "region_override": None if not override else [float(value) for value in override],
            "crop_region": _covering_crop(region, candidate.get("crop_region")),
            "machine_text_hint": candidate.get("machine_text_hint"),
            "ignored": bool(review.get("ignored")),
            "unbindable": bool(review.get("unbindable")),
            "provenance": {"kind": "detected", "observation_ids": list(candidate.get("observation_ids") or []),
                           "detector_version": candidate.get("detector_version"),
                           "geometry_version": candidate.get("geometry_version")},
        })
    for manual in decisions.get("manual_callouts") or []:
        callout_id = manual.get("id")
        review = reviews.get(callout_id) or {}
        base = [float(value) for value in manual.get("region") or []]
        override = review.get("region_override")
        region = [float(value) for value in override] if override else list(base)
        rows.append({
            "id": callout_id,
            "page_index": manual.get("page_index"),
            "source_kind": "manual",
            "source_digest": manual.get("source_digest"),
            "manual": True,
            "region": region,
            "base_region": base,
            "region_override": None if not override else [float(value) for value in override],
            "crop_region": _covering_crop(region, None),
            # The user drew this area: there is no machine reading of it, and saying otherwise
            # (a hint, an observation id) would present a detection that never happened.
            "machine_text_hint": None,
            "ignored": bool(review.get("ignored")),
            "unbindable": bool(review.get("unbindable")),
            "provenance": {"kind": "manual", "observation_ids": [], "detector_version": None,
                           "geometry_version": None},
        })
    return rows


# --- freshness: current / stale / missing, with machine reason codes ---------------

def _transcription_state(transcription: dict | None, region: list[float] | None) -> dict:
    """Current while the text was written against the region that is still in front of the user.

    `source_region` is the snapshot of the box the user actually read (PLAN-21 §6.3). Moving the box
    never rewrites that snapshot — the old text simply becomes stale (`region_changed`) until the
    user looks at the new region and saves the text again.
    """
    if transcription is None:
        return {"state": "missing", "revision": None, "reason": "needs_transcription"}
    stored = [float(value) for value in transcription.get("source_region") or []]
    if region is not None and stored != [float(value) for value in region]:
        return {"state": "stale", "revision": transcription.get("revision"), "reason": "region_changed"}
    return {"state": "current", "revision": transcription.get("revision"), "reason": None}


def _parse_state(callout_id: str, transcription: dict | None, parses: list[dict],
                 expected_parser_version: str, record: dict, region_changed: bool = False) -> dict:
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
    if region_changed:
        # The text is no longer standing on the region it was read from: any parse of it describes
        # a box the user has moved away from (PLAN-21 §6.3).
        return {"state": "stale", "reason": "region_changed"} if mine else \
               {"state": "missing", "reason": "needs_parse"}
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
                  key: str, record: dict, expected_parser_version: str,
                  region_changed: bool = False) -> dict:
    """Reason priority, first one wins: source_unavailable → transcription_missing → region_changed →
    transcription_changed → parser_version_changed → geometry_changed → parse_missing/parse_conflict."""
    if target is None:
        return {"state": "missing", "reason": "needs_target"}
    reasons: list[str] = []
    if record.get("geometry_stale"):
        reasons.append("source_unavailable")
    if transcription is None:
        reasons.append("transcription_missing")
    elif region_changed:
        reasons.append("region_changed")
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
    no confirmation and never re-pins anything. The list is the *effective* one (PLAN-21 §6.2), so
    a region the user drew themselves has a state too; `ignored` rides along as the user's own
    review flag, not as a freshness verdict.
    """
    expected = expected_parser_version or CALLOUT_PARSER_VERSION
    decisions = record.get("decisions") or {}
    transcriptions = {row.get("callout_id"): row for row in decisions.get("transcriptions") or []}
    targets = {row.get("callout_id"): row for row in decisions.get("callout_targets") or []}
    parses = record.get("callout_parses") or []
    key = geometry_key(record, decisions)
    rows = []
    for callout in effective_callouts(record):
        callout_id = callout["id"]
        transcription = transcriptions.get(callout_id)
        region_changed = (transcription is not None
                          and [float(value) for value in transcription.get("source_region") or []]
                          != [float(value) for value in callout.get("region") or []])
        rows.append({
            "id": callout_id,
            "page_index": callout.get("page_index"),
            "source_kind": callout.get("source_kind"),
            "manual": callout.get("manual"),
            "ignored": callout.get("ignored"),
            "unbindable": callout.get("unbindable"),
            "transcription": _transcription_state(transcription, callout.get("region")),
            "parse": _parse_state(callout_id, transcription, parses, expected, record, region_changed),
            "target": _target_state(callout_id, transcription, targets.get(callout_id), parses,
                                    key, record, expected, region_changed),
        })
    return rows


def callout_state(record: dict, callout_id: str, decisions: dict | None = None,
                  expected_parser_version: str | None = None) -> dict | None:
    """One callout's freshness row, computed against an explicit decision set (PLAN-22 §5.1).

    The store judges a pending confirmation with exactly the picture the public state would show for
    the decisions the operation is about to leave — one rule shared with `callout_states`, never a
    second implementation that could drift from it. Pure: reads, writes nothing.
    """
    pending = {**record, "decisions": record.get("decisions") if decisions is None else decisions}
    return next((row for row in callout_states(pending, expected_parser_version)
                 if row.get("id") == callout_id), None)
