"""G1R3 endpoint-identity review; temporary synthetic sessions only.

Run from repository root with PYTHONPATH=src .venv/bin/python <this-file>.
Exit 1 means distinct physical endpoints are still being refused.
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


def probe(folder: Path, width: float, *, same_point: bool = False) -> dict:
    folder.mkdir()
    store = HELPERS["store"].__wrapped__(folder)
    HELPERS["seed_callouts"](store)
    payload = HELPERS["current_payload"](store, holes=[])
    payload["transcriptions"] = [HELPERS["_transcription"](raw=f"{width / 2:g} mm")]
    store.save(TOKEN, 0, payload)
    HELPERS["seed_callouts"](store, candidate=False, parses=[HELPERS["_parse_row"](
        form="linear", size=width / 2, count=None, unit="mm", termination=None)])
    record = store.load(TOKEN)
    profile = next(p for p in record["options"]["profiles"]
                   if p["id"] == record["decisions"]["profile_id"])
    points = [[20, 20], [20 + width, 20], [20 + width, 80], [20, 80]]
    edges = [{"id": f"short{i}", "kind": "line", "start": point,
              "end": points[(i + 1) % 4]} for i, point in enumerate(points)]
    assert contour_audit.audit_contour(edges)["ok"] is True
    profile["edges"] = edges
    profile["points"] = points
    guided._atomic(HELPERS["_session_path"](store), record)
    ids = ["short0:end", "short1:start"] if same_point else ["short0:start", "short0:end"]
    payload = HELPERS["current_payload"](store)
    payload["callout_targets"] = [HELPERS["_target_payload"](
        target_kind="vertex_pair", target_ids=ids,
        evidence=[{"kind": "user_click", "ref": ",".join(ids)}])]
    before = HELPERS["_session_path"](store).read_bytes()
    rejection = None
    state = None
    try:
        state = store.save(TOKEN, record["revision"], payload)
    except ValueError as error:
        rejection = str(error)
    unchanged = HELPERS["_session_path"](store).read_bytes() == before
    current = state is not None and state["callouts"][0]["target"]["state"] == "current"
    return {
        "case": "same_corner_aliases" if same_point else f"distinct_{width:g}px",
        "contour_ok": True,
        "point_distance_px": 0 if same_point else width,
        "target_ids": ids,
        "expected": "reject_without_write" if same_point else "accept_current",
        "rejection": rejection,
        "target_current": current,
        "passed": rejection is not None and unchanged if same_point else current,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guided-g2-review-") as root:
        # Keep every rectangle above the existing contour audit's stroke-collapse
        # threshold; the finding concerns valid, distinct geometry.
        results = [probe(Path(root) / f"distinct-{width}", width) for width in (5, 10, 20, 21)]
        results.append(probe(Path(root) / "same", 40, same_point=True))
    passed = all(row["passed"] for row in results)
    print(json.dumps({"finding": "G1R3-01", "observed_join_tolerance_px": guided.RASTER_JOIN_TOLERANCE_PX,
                      "cases": results, "passed": passed}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
