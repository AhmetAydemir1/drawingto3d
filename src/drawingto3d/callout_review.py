"""GX — session review export/import (kök `PLAN.md` §12).

```text
session review bundle export → external reviewer → reviewed actions import
→ same server validation / history / revision / stale handling / audit path
```

The bundle is *data about a session*, never a door into the record: importing validates every action
against the record it claims to belong to (session, source digest, base revision, known callouts,
geometry that exists) and then hands the surviving actions to the store's own command path, so the
validation, history, revision bump, staleness and log lines are the ones the interface already uses.

The review JSON is untrusted input (PLAN §24): this module is pure and answers `ok`/`errors` — it
never writes, never creates a confirmation, and never touches the base observation.
"""
from __future__ import annotations

from datetime import datetime, timezone

from drawingto3d import callout_bind, callout_readiness
from drawingto3d.callout_models import (CALLOUT_DISPOSITIONS, CALLOUT_PARSER_VERSION, CALLOUT_SCHEMA_VERSION,
                                        DISPOSITION_DECISION_PREFIX, callout_state, effective_callouts,
                                        geometry_key)

BUNDLE_VERSION = 1
IMPORT_ACTIONS = ("transcribe", "ignore", "restore", "confirm_target", "select_target", "set_disposition")
TARGET_KINDS = ("circle", "circle_group", "arc", "profile", "vertex_pair")
TEXT_LIMIT = 200
EVIDENCE_LIMIT = 50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _region_ok(region) -> bool:
    if not isinstance(region, list) or len(region) != 4:
        return False
    try:
        x0, y0, x1, y1 = (float(value) for value in region)
    except (TypeError, ValueError):
        return False
    return 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0


def _current_parse(record: dict, callout_id: str, revision, parser_version) -> dict | None:
    for row in record.get("callout_parses") or []:
        if (row.get("callout_id") == callout_id and row.get("transcription_revision") == revision
                and row.get("parser_version") == parser_version):
            return row
    return None


def export_bundle(record: dict, *, artifacts: dict | None = None, proposals_limit: int = 4) -> dict:
    """The reviewer's picture of one session: what was read, what it parsed to, what was bound."""
    decisions = record.get("decisions") or {}
    transcriptions = {row.get("callout_id"): row for row in decisions.get("transcriptions") or []}
    targets = {row.get("callout_id"): row for row in decisions.get("callout_targets") or []}
    reviews = {row.get("callout_id"): row for row in decisions.get("callout_reviews") or []}
    rows = []
    for callout in effective_callouts(record):
        callout_id = callout["id"]
        state = callout_state(record, callout_id, decisions) or {}
        transcription = transcriptions.get(callout_id) or {}
        parse = None
        if transcription.get("revision") is not None:
            target = targets.get(callout_id) or {}
            parse = _current_parse(record, callout_id, transcription.get("revision"),
                                   target.get("parser_version") or CALLOUT_PARSER_VERSION)
        review = reviews.get(callout_id) or {}
        rows.append({
            "callout_id": callout_id,
            "page_index": callout.get("page_index"),
            "source_kind": callout.get("source_kind"),
            "region": callout.get("region"),
            "base_region": callout.get("base_region"),
            "crop_region": callout.get("crop_region"),
            "machine_text_hint": callout.get("machine_text_hint"),
            "ignored": bool(review.get("ignored")),
            "unbindable": bool(review.get("unbindable")),
            # G12.1: the reviewer sees every scope claim the session holds, with its dayanak — an
            # imported disposition is judged against the same contract the interface uses (§12/§17).
            "disposition": review.get("disposition"),
            "duplicate_of": review.get("duplicate_of"),
            "disposition_reason": review.get("disposition_reason"),
            "freshness": {"transcription": state.get("transcription"), "parse": state.get("parse"),
                          "target": state.get("target")},
            "raw_text": transcription.get("raw_text"),
            "transcription_revision": transcription.get("revision"),
            "semantic_parse": parse,
            "target_proposals": [row.model_dump(mode="json")
                                 for row in callout_bind.propose_targets(record, callout_id,
                                                                         limit=proposals_limit)],
            "confirmed_target": targets.get(callout_id),
            "image": (artifacts or {}).get(callout_id),
        })
    return {
        "bundle_version": BUNDLE_VERSION,
        "schema_version": CALLOUT_SCHEMA_VERSION,
        "parser_version": CALLOUT_PARSER_VERSION,
        "session": record.get("token"),
        "base_revision": record.get("revision") or 0,
        "source_digest": record.get("source_sha256"),
        "source": record.get("source"),
        "page": 0,
        "created_at": _now(),
        "detector_version": (record.get("callout_detection") or {}).get("detector_version"),
        "geometry_version": record.get("geometry_version"),
        # R05 (review): the fingerprint the reviewer's approval is bound to. The version alone
        # cannot see a same-version content change, and a migration refreshes geometry without
        # bumping the revision — the key is what makes both visible at import time.
        "geometry_key": geometry_key(record),
        "callouts": rows,
        "instructions": ("Her callout için: `transcribe` (metni yaz), `ignore`/`restore` (callout değil), "
                         "`confirm_target` (öneriyi onayla), `select_target` (kendi seçimin), "
                         "`set_disposition` (not_model_input / redundant + duplicate_of / "
                         "build_relevant_unsupported + disposition_reason). "
                         "`base_revision` değiştiyse içe aktarma reddedilir."),
    }


def _validate_target(record: dict, callout_id: str, payload: dict, errors: list) -> dict | None:
    """One target action's payload: the kind's cardinality and the ids the geometry really has."""
    options = record.get("options") or {}
    kind = payload.get("target_kind")
    ids = payload.get("target_ids")
    if kind not in TARGET_KINDS:
        errors.append({"callout_id": callout_id, "reason": "unknown_target_kind", "detail": str(kind)})
        return None
    if not isinstance(ids, list) or not ids or len(ids) > 100 or any(not isinstance(item, str) or not item
                                                                    for item in ids):
        errors.append({"callout_id": callout_id, "reason": "invalid_target_ids"})
        return None
    if len(set(ids)) != len(ids):
        errors.append({"callout_id": callout_id, "reason": "duplicate_target_ids"})
        return None
    if kind == "circle" and len(ids) != 1:
        errors.append({"callout_id": callout_id, "reason": "cardinality", "detail": "circle = 1 kimlik"})
        return None
    if kind == "circle_group" and len(ids) < 2:
        errors.append({"callout_id": callout_id, "reason": "cardinality", "detail": "circle_group ≥ 2"})
        return None
    if kind == "vertex_pair" and len(ids) != 2:
        errors.append({"callout_id": callout_id, "reason": "cardinality", "detail": "vertex_pair = 2 uç"})
        return None
    circles = {row.get("id") for row in options.get("circles") or []}
    arcs = {row.get("id") for row in options.get("primitives") or [] if row.get("kind") == "arc"}
    profiles = {row.get("id") for row in options.get("profiles") or []}
    edges = {edge.get("id") for profile in options.get("profiles") or []
             for edge in profile.get("edges") or []}
    known = {"circle": circles, "circle_group": circles, "arc": arcs, "profile": profiles}.get(kind)
    if known is None:
        for item in ids:
            edge_id, _, which = item.partition(":")
            if edge_id not in edges or which not in ("start", "end"):
                errors.append({"callout_id": callout_id, "reason": "unknown_geometry", "detail": item})
                return None
    else:
        for item in ids:
            if item not in known:
                errors.append({"callout_id": callout_id, "reason": "unknown_geometry", "detail": item})
                return None
    evidence = payload.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list) or not evidence or len(evidence) > EVIDENCE_LIMIT:
            errors.append({"callout_id": callout_id, "reason": "invalid_evidence"})
            return None
        for row in evidence:
            if (not isinstance(row, dict) or not str(row.get("kind") or "").strip()
                    or not str(row.get("ref") or "").strip()):
                errors.append({"callout_id": callout_id, "reason": "invalid_evidence"})
                return None
    return {"target_kind": kind, "target_ids": list(ids),
            "evidence": [{"kind": str(row["kind"])[:60], "ref": str(row["ref"])[:2000]} for row in evidence]
            if evidence else None}


def validate_import(record: dict, bundle: dict, *, session_token: str | None = None) -> dict:
    """Validate an external review bundle against this record — pure, all-or-nothing, no writes."""
    errors: list[dict] = []
    if not isinstance(bundle, dict):
        return {"ok": False, "errors": [{"reason": "not_an_object"}], "actions": []}
    if bundle.get("bundle_version") != BUNDLE_VERSION:
        errors.append({"reason": "unknown_bundle_version", "detail": str(bundle.get("bundle_version"))})
    if bundle.get("schema_version") != CALLOUT_SCHEMA_VERSION:
        errors.append({"reason": "schema_version_mismatch",
                       "detail": f"{bundle.get('schema_version')} ≠ {CALLOUT_SCHEMA_VERSION}"})
    token = session_token or record.get("token")
    if str(bundle.get("session") or "") != str(token or ""):
        errors.append({"reason": "session_mismatch"})
    if str(bundle.get("source_digest") or "") != str(record.get("source_sha256") or ""):
        errors.append({"reason": "source_mismatch"})
    base = bundle.get("base_revision")
    if not isinstance(base, int) or isinstance(base, bool):
        errors.append({"reason": "base_revision_invalid"})
    elif base != (record.get("revision") or 0):
        errors.append({"reason": "stale_base_revision",
                       "detail": f"{base} ≠ {record.get('revision') or 0}"})
    # R05 (review): the bundle must carry the context the reviewer *saw* — the parser that read the
    # text and the geometry fingerprint the proposals came from. `_migrated` refreshes geometry
    # without touching the revision, so the base-revision gate alone would let a pre-migration
    # approval land on moved geometry; comparing the context is what makes that refusal whole.
    if str(bundle.get("parser_version") or "") != CALLOUT_PARSER_VERSION:
        errors.append({"reason": "parser_version_mismatch",
                       "detail": f"inceleme '{bundle.get('parser_version')}' okumasıyla yapılmış; sunucu "
                                 f"'{CALLOUT_PARSER_VERSION}' — oturumu yeniden dışa aktarın"})
    if bundle.get("geometry_version") != record.get("geometry_version"):
        errors.append({"reason": "geometry_version_mismatch",
                       "detail": f"{bundle.get('geometry_version')} ≠ {record.get('geometry_version')}; "
                                 "geometri bu paket dışa aktarıldıktan sonra yenilendi — yeniden dışa "
                                 "aktarıp inceleyin"})
    elif str(bundle.get("geometry_key") or "") != geometry_key(record):
        errors.append({"reason": "geometry_mismatch",
                       "detail": "paketin onayladığı geometri bağlamı bu oturumun güncel bağlamıyla "
                                 "eşleşmiyor — oturumu yeniden dışa aktarıp inceleyin"})
    raw = bundle.get("actions")
    if not isinstance(raw, list) or not raw:
        errors.append({"reason": "no_actions"})
        raw = []
    if len(raw) > 200:
        errors.append({"reason": "too_many_actions"})
        raw = raw[:200]

    callouts = {row["id"] for row in effective_callouts(record)}
    decisions = record.get("decisions") or {}
    transcriptions = {row.get("callout_id"): row for row in decisions.get("transcriptions") or []}
    actions: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append({"index": index, "reason": "not_an_object"})
            continue
        name = item.get("action")
        callout_id = item.get("callout_id")
        if name not in IMPORT_ACTIONS:
            errors.append({"index": index, "reason": "unknown_action", "detail": str(name)})
            continue
        if callout_id not in callouts:
            errors.append({"index": index, "reason": "unknown_callout", "detail": str(callout_id)})
            continue
        callout_id = str(callout_id)
        payload: dict = {}
        if name == "transcribe":
            text = item.get("raw_text")
            if not isinstance(text, str) or not text.strip():
                errors.append({"index": index, "callout_id": callout_id, "reason": "empty_text"})
                continue
            if len(text) > TEXT_LIMIT:
                errors.append({"index": index, "callout_id": callout_id, "reason": "text_too_long",
                               "detail": f"≤ {TEXT_LIMIT}"})
                continue
            payload["raw_text"] = text
            region = item.get("region")
            if region is not None:
                if not _region_ok(region):
                    errors.append({"index": index, "callout_id": callout_id, "reason": "invalid_region"})
                    continue
                payload["region"] = [float(value) for value in region]
        elif name in ("ignore", "restore"):
            pass
        elif name == "set_disposition":
            # G12.1 (§17): the same contract as the interface's command — vocabulary, a resolvable
            # dayanak for `redundant`, a reason for `build_relevant_unsupported`. All-or-nothing:
            # one bad row refuses the whole import (PLAN §24 — untrusted input).
            disposition = item.get("disposition")
            if disposition not in CALLOUT_DISPOSITIONS:
                errors.append({"index": index, "callout_id": callout_id, "reason": "unknown_disposition",
                               "detail": str(disposition)})
                continue
            duplicate_of = item.get("duplicate_of")
            reason = item.get("disposition_reason")
            if disposition == "redundant":
                if not isinstance(duplicate_of, str) or not duplicate_of.strip():
                    errors.append({"index": index, "callout_id": callout_id,
                                   "reason": "missing_duplicate_reference"})
                    continue
                duplicate_of = duplicate_of.strip()
                if duplicate_of.startswith(DISPOSITION_DECISION_PREFIX):
                    if not callout_readiness.decision_ref_present(decisions, duplicate_of[len(DISPOSITION_DECISION_PREFIX):]):
                        errors.append({"index": index, "callout_id": callout_id,
                                       "reason": "unknown_decision_reference", "detail": duplicate_of})
                        continue
                elif duplicate_of == callout_id:
                    errors.append({"index": index, "callout_id": callout_id,
                                   "reason": "self_duplicate_reference"})
                    continue
                elif duplicate_of not in callouts:
                    errors.append({"index": index, "callout_id": callout_id,
                                   "reason": "unknown_duplicate_reference", "detail": duplicate_of})
                    continue
            else:
                duplicate_of = None
            if disposition == "build_relevant_unsupported":
                if not isinstance(reason, str) or not reason.strip():
                    errors.append({"index": index, "callout_id": callout_id,
                                   "reason": "missing_disposition_reason"})
                    continue
                reason = reason.strip()[:500]
            else:
                reason = None
            payload.update({"disposition": disposition, "duplicate_of": duplicate_of,
                            "disposition_reason": reason})
        else:
            target = _validate_target(record, callout_id, item, errors)
            if target is None:
                continue
            stored = transcriptions.get(callout_id) or {}
            if stored.get("revision") is None:
                errors.append({"index": index, "callout_id": callout_id, "reason": "no_transcription"})
                continue
            if _current_parse(record, callout_id, stored.get("revision"), CALLOUT_PARSER_VERSION) is None:
                errors.append({"index": index, "callout_id": callout_id, "reason": "no_current_parse"})
                continue
            payload.update({name: value for name, value in target.items() if value is not None})
        actions.append({"action": name, "callout_id": callout_id, "payload": payload})
    return {"ok": not errors, "errors": errors, "actions": actions if not errors else [],
            "session": token, "base_revision": base if isinstance(base, int) else None}


__all__ = ["BUNDLE_VERSION", "IMPORT_ACTIONS", "TARGET_KINDS", "export_bundle", "validate_import"]
