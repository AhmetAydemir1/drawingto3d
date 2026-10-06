"""Independent G3 store review at 2cdb4d0; temporary synthetic sessions only.

PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/review_probes.py
Exit 1 means at least one required invariant still fails. No model or CAD calls.
"""
from __future__ import annotations

import json
import runpy
import tempfile
from pathlib import Path

from drawingto3d import callout_models, guided

ROOT = Path(__file__).resolve().parents[3]
H = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))
TOKEN = H["TOKEN"]


def make_store(root, name):
    folder = root / name
    folder.mkdir()
    store = H["store"].__wrapped__(folder)
    H["seed_callouts"](store)
    return store


def try_save(store, **updates):
    path = H["_session_path"](store)
    before = path.read_bytes()
    try:
        state = store.save(TOKEN, store.load(TOKEN)["revision"], H["current_payload"](store, **updates))
    except ValueError as error:
        return None, str(error), path.read_bytes() == before
    return state, None, path.read_bytes() == before


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="guided-g3-independent-") as temporary:
        root = Path(temporary)
        store = make_store(root, "manual")
        supplied = {"id": "manual:" + "0" * 32, "source_digest": "b" * 64,
                    "page_index": 7, "region": [.2, .2, .3, .3], "revision": 999}
        state, error, unchanged = try_save(store, manual_callouts=[supplied])
        results.append({"case": "save_cannot_create_client_owned_manual_identity",
                        "expected": "reject_without_write; creation belongs to add_region",
                        "error": error, "unchanged": unchanged,
                        "persisted": state and state["decisions"]["manual_callouts"],
                        "passed": bool(error and unchanged)})

        store = make_store(root, "ghost")
        state, error, unchanged = try_save(store, callout_reviews=[{
            "callout_id": "unknown-callout", "ignored": True, "revision": 999}])
        results.append({"case": "save_rejects_unknown_review_reference", "error": error,
                        "persisted": state and state["decisions"]["callout_reviews"],
                        "passed": bool(error and unchanged)})

        store = make_store(root, "ignored")
        store.edit_callout(TOKEN, 0, "set_ignored", {"callout_id": "k1", "ignored": True})
        state, error, unchanged = try_save(store, transcriptions=[H["_transcription"]()])
        results.append({"case": "save_cannot_transcribe_ignored_callout", "error": error,
                        "callout_state": state and state["callouts"][0],
                        "passed": bool(error and unchanged)})

        store = make_store(root, "snapshot")
        state, error, unchanged = try_save(store, transcriptions=[{
            **H["_transcription"](), "source_region": [.6, .6, .7, .7]}])
        actual = state and state["decisions"]["transcriptions"][0]["source_region"]
        results.append({"case": "save_validates_or_derives_new_transcription_region",
                        "error": error, "persisted_region": actual,
                        "effective_region": [.1, .2, .4, .5],
                        "passed": bool(error and unchanged) or actual == [.1, .2, .4, .5]})

        store = make_store(root, "stale-target")
        H["_transcribed"](store)
        store.edit_callout(TOKEN, 1, "edit_region", {"callout_id": "k1", "region": [.6, .6, .7, .7]})
        before_state = store.public(store.load(TOKEN))["callouts"][0]
        state, error, unchanged = try_save(store, callout_targets=[H["_target_payload"]()])
        results.append({"case": "new_confirmation_requires_current_transcription_and_parse",
                        "before": before_state, "error": error,
                        "persisted": state and state["decisions"]["callout_targets"],
                        "passed": bool(error and unchanged)})

        store = make_store(root, "schema")
        record = store.load(TOKEN)
        record["callout_schema_version"] = 1
        guided._atomic(H["_session_path"](store), record)
        before = H["_session_path"](store).read_bytes()
        store.public(store.load(TOKEN))
        read_unchanged = H["_session_path"](store).read_bytes() == before
        state = store.edit_callout(TOKEN, 0, "add_region", {"region": [.2, .2, .3, .3]})
        results.append({"case": "v1_session_real_g3_write_stamps_current_schema",
                        "read_unchanged": read_unchanged,
                        "expected_version": callout_models.CALLOUT_SCHEMA_VERSION,
                        "actual_version": state["callout_schema_version"],
                        "passed": read_unchanged and state["callout_schema_version"] == callout_models.CALLOUT_SCHEMA_VERSION})

        store = make_store(root, "diagnostics")
        record = store.load(TOKEN)
        record["callout_candidates"] = []
        record["callout_detection"] = {"detector_version": "callout-detector/1", "diagnostics": [
            {"code": "source_digest_mismatch", "observation_id": None}]}
        state = store.public(record)
        results.append({"case": "public_preserves_detection_metadata", "present": "callout_detection" in state,
                        "passed": state.get("callout_detection") == record["callout_detection"]})

    passed = all(row["passed"] for row in results)
    print(json.dumps({"reviewed_baseline": "2cdb4d0", "cases": results, "passed": passed}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
