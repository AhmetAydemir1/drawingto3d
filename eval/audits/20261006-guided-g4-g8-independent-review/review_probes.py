"""Independent G4/G7/G8 regression probes at e51f555 (no product mutations).

Run from repository root:
  PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g4-g8-independent-review/review_probes.py

Uses the real store, parser, target save, readiness, compiler and GeneralPlan builder.
Does not invoke the CAD process, a model, or an existing session. Exit 1 = invariant failure.
The fourth finding (UI target selection) has separate real-browser evidence.
"""
import json
import math
import runpy
import tempfile
from pathlib import Path

from drawingto3d import callout_compile, guided

ROOT = Path(__file__).resolve().parents[3]
H = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))
TOKEN = H["TOKEN"]


def store_in(root, name, text, *, inches=False):
    folder = root / name
    folder.mkdir()
    store = H["store"].__wrapped__(folder)
    H["seed_callouts"](store)
    if inches:
        payload = H["current_payload"](store)
        payload["calibration"] = {**payload["calibration"], "value": 50 / 25.4, "unit": "in"}
        store.save(TOKEN, 0, payload)
    store.edit_callout(TOKEN, store.load(TOKEN)["revision"], "transcribe",
                      {"callout_id": "k1", "raw_text": text})
    return store


def confirm(store, kind, ids):
    record = store.load(TOKEN)
    payload = H["current_payload"](store, holes=[])
    payload["callout_targets"] = [H["_target_payload"](
        target_kind=kind, target_ids=ids,
        transcription_revision=record["decisions"]["transcriptions"][0]["revision"])]
    store.save(TOKEN, record["revision"], payload)
    record = store.load(TOKEN)
    compilation = callout_compile.compile_callouts(record)
    merged = callout_compile.apply_compiled(record["decisions"], compilation)
    plan = guided.make_plan({**record, "decisions": merged})
    return record, compilation, plan


def blind_depth(root, *, inches_in_text):
    name = "printed_inch_depth" if inches_in_text else "sheet_inch_depth"
    text = "Ø.5 .25 DEEP in" if inches_in_text else "Ø.5 .25 DEEP"
    store = store_in(root, name, text, inches=not inches_in_text)
    record, compilation, plan = confirm(store, "circle", ["c0"])
    actual = float(plan.parameters["hole_0_depth"].value)
    return {"finding": "R02", "case": name, "text": text,
            "parse": record["callout_parses"][0], "compiled_hole": compilation["holes"][0],
            "readiness_ready": store.readiness(TOKEN)["ready"],
            "expected_depth_mm": 6.35, "plan_depth_mm": actual,
            "passed": math.isclose(actual, 6.35, rel_tol=0, abs_tol=1e-9)}


def linear(root, *, vertical):
    name = "vertical_30mm" if vertical else "horizontal_50mm_control"
    store = store_in(root, name, "30 mm" if vertical else "50 mm")
    ids = ["g1:start", "g1:end"] if vertical else ["g0:start", "g0:end"]
    record, compilation, plan = confirm(store, "vertex_pair", ids)
    edges = {name: float(value.value) for name, value in plan.parameters.items() if name.startswith("edge_")}
    xs = [value for name, value in edges.items() if name.endswith("_x")]
    ys = [value for name, value in edges.items() if name.endswith("_y")]
    height, width = max(ys) - min(ys), max(xs) - min(xs)
    expected_direction = -1 if vertical else 1
    binding = compilation["bindings"][0]
    return {"finding": "R01" if vertical else "control", "case": name,
            "readiness_ready": store.readiness(TOKEN)["ready"],
            "binding_axis": binding["axis"], "binding_direction": binding["direction"],
            "expected_direction_in_part_frame": expected_direction,
            "expected_bbox_mm": [50, 30], "plan_bbox_mm": [width, height], "plan_edges": edges,
            "passed": binding["direction"] == expected_direction
                      and math.isclose(width, 50, abs_tol=1e-9) and math.isclose(height, 30, abs_tol=1e-9)}


def invalid_reading(root, text, expected_category, name):
    store = store_in(root, name, text)
    record = store.load(TOKEN)
    reading = record["callout_parses"][0]
    readiness = store.readiness(TOKEN)
    before = H["_session_path"](store).read_bytes()
    error = None
    payload = H["current_payload"](store)
    payload["callout_targets"] = [H["_target_payload"](
        transcription_revision=record["decisions"]["transcriptions"][0]["revision"])]
    try:
        store.save(TOKEN, record["revision"], payload)
    except ValueError as exc:
        error = str(exc)
    return {"finding": "R04", "case": name, "text": text, "parse_status": reading["status"],
            "expected_category": expected_category, "actual_categories": readiness["categories"],
            "questions": readiness["questions"], "confirmation_error": error,
            "confirmation_rejected_without_write": bool(error) and H["_session_path"](store).read_bytes() == before,
            "passed": expected_category in readiness["categories"]
                      and "missing_target" not in readiness["categories"]}


def main():
    with tempfile.TemporaryDirectory(prefix="guided-g4-g8-review-") as temporary:
        root = Path(temporary)
        cases = [linear(root, vertical=False), linear(root, vertical=True),
                 blind_depth(root, inches_in_text=True), blind_depth(root, inches_in_text=False),
                 invalid_reading(root, "M8", "parse_error", "unsupported"),
                 invalid_reading(root, "Ø8 9", "parse_ambiguous", "ambiguous")]
    passed = all(case["passed"] for case in cases)
    print(json.dumps({"reviewed_baseline": "e51f555", "cases": cases, "passed": passed},
                     ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
