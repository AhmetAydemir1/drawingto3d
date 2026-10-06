"""Independent G1 review probes; synthetic temporary sessions, no product writes.

From the repository root:
    PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py

Exit 1 means a reviewed invariant still fails. These are review reproductions;
the implementation task must also add permanent regression tests.
"""
from __future__ import annotations

import json
import runpy
import tempfile
from pathlib import Path

from drawingto3d import contour_audit, guided

ROOT = Path(__file__).resolve().parents[3]
HELPERS = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))
TOKEN = HELPERS["TOKEN"]


def setup(folder: Path, *, linear: bool = False):
    folder.mkdir()
    store = HELPERS["store"].__wrapped__(folder)
    HELPERS["seed_callouts"](store)
    payload = HELPERS["current_payload"](store)
    raw = "100 mm" if linear else "Ø8 THRU"
    payload["transcriptions"] = [HELPERS["_transcription"](raw=raw)]
    store.save(TOKEN, 0, payload)
    parse = HELPERS["_parse_row"](
        form="linear" if linear else "diameter",
        size=100 if linear else 8,
        termination=None if linear else "thru",
        unit="mm" if linear else None,
        count=None,
    )
    HELPERS["seed_callouts"](store, candidate=False, parses=[parse])
    return store


def save(store, payload):
    return store.save(TOKEN, store.load(TOKEN)["revision"], payload)


def removed_edge_probe(folder: Path) -> dict:
    store = setup(folder, linear=True)
    record = store.load(TOKEN)
    profile = next(p for p in record["options"]["profiles"]
                   if p["id"] == record["decisions"]["profile_id"])

    def line(edge_id, start, end):
        return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}

    # The duplicate partial side is a legitimate contour-repair scenario, also
    # covered by tests/test_contour_fix.py. Removing d2 leaves a valid rectangle.
    edges = [line("a", (20, 20), (120, 20)),
             line("d2", (70, 20), (120, 20)),
             line("b", (120, 20), (120, 80)),
             line("c", (120, 80), (20, 80)),
             line("d", (20, 80), (20, 20))]
    profile["edges"] = edges
    profile["points"] = [edge["start"] for edge in edges]
    guided._atomic(HELPERS["_session_path"](store), record)
    fix = guided.ContourFix(drop=["d2"])
    corrected = guided.correct_profile(
        profile, fix,
        join_tolerance_px=guided.RASTER_JOIN_TOLERANCE_PX,
        mid_join_px=guided.RASTER_JOIN_TOLERANCE_PX / 2,
    )
    assert contour_audit.audit_contour(corrected["edges"])["ok"] is True
    payload = HELPERS["current_payload"](store, contour=fix.model_dump())
    payload["callout_targets"] = [HELPERS["_target_payload"](
        target_kind="vertex_pair", target_ids=["d2:start", "c:start"],
        evidence=[{"kind": "user_click", "ref": "d2:start,c:start"}],
    )]
    before = HELPERS["_session_path"](store).read_bytes()
    rejection = None
    state = None
    try:
        state = save(store, payload)
    except ValueError as error:
        rejection = str(error)
    unchanged = HELPERS["_session_path"](store).read_bytes() == before
    return {
        "id": "G1R2-01",
        "expected": "removed endpoint confirmation is rejected without a write",
        "corrected_contour_ok": True,
        "corrected_edge_ids": [edge["id"] for edge in corrected["edges"]],
        "submitted_target_ids": ["d2:start", "c:start"],
        "rejection": rejection,
        "record_unchanged": unchanged,
        "target_state": None if state is None else state["callouts"][0]["target"],
        "passed": rejection is not None and unchanged,
    }


def reconfirm_log_probe(folder: Path) -> dict:
    store = setup(folder)
    payload = HELPERS["current_payload"](store)
    payload["callout_targets"] = [HELPERS["_target_payload"]()]
    save(store, payload)
    record = store.load(TOKEN)
    new_profile = next(p["id"] for p in record["options"]["profiles"]
                       if p["kind"] == "wire" and p["id"] != record["decisions"]["profile_id"])
    state = save(store, HELPERS["current_payload"](store, profile_id=new_profile))
    assert state["callouts"][0]["target"]["state"] == "stale"
    before = store.load(TOKEN)
    start = len(before.get("log", []))
    payload = HELPERS["current_payload"](store)
    payload["callout_targets"][0]["reconfirm"] = True
    state = save(store, payload)
    after = store.load(TOKEN)
    events = after.get("log", [])[start:]
    confirms = [event for event in events
                if event.get("actor") == "user" and event.get("action") == "confirm_target"]
    current = state["callouts"][0]["target"]["state"] == "current"
    return {
        "id": "G1R2-02",
        "expected": "stale-to-current explicit reconfirm writes one user/confirm_target event",
        "revision_before": before["revision"],
        "revision_after": after["revision"],
        "target_state": state["callouts"][0]["target"],
        "new_log_actions": [event.get("action") for event in events],
        "new_confirm_events": len(confirms),
        "passed": current and len(confirms) == 1,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guided-g1-review-") as root:
        results = [removed_edge_probe(Path(root) / "removed"),
                   reconfirm_log_probe(Path(root) / "log")]
    print(json.dumps({"probes": results, "passed": all(r["passed"] for r in results)},
                     ensure_ascii=False, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
