"""G11 case evaluator — runs under `.venv-cad` (cadquery lives there, not in the driver's venv).

    .venv-cad/bin/python evaluate_case.py <produced.step> <reference.step|->

Prints one JSON line:
    {"step_reopen": bool, "bbox": [...], "features": {...}, "final_geometry_verdict": {...}|null,
     "error": null}

`step_reopen` = `importStep` ran twice on the produced file, the second time after the first shape was
built (the STEP_EXPORT/STEP_REOPEN gates of the plan's failure taxonomy). `final_geometry_verdict` =
the repo's own `eval/metrics.py compare()` against the reference — the frozen evaluator formula, no
new tolerances are invented here. With `-` (no reference) it stays null: a callout-scope-only case is
never reported as geometric correctness.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "eval"))
import metrics  # noqa: E402


def main() -> int:
    produced, reference = sys.argv[1], sys.argv[2]
    result = {"step_reopen": True, "bbox": None, "features": None,
              "final_geometry_verdict": None, "error": None}
    try:
        first = metrics.describe(produced)
        second = metrics.describe(produced)                    # a real reopen after the first read
        result["step_reopen"] = bool(second["solids"] == first["solids"])
        result["bbox"] = first["vector"]
        result["features"] = {"solids": first["solids"], "valid": first["valid"], "faces": first["faces"],
                              "cylinders": first["cylinders"], "face_types": first["face_types"]}
        if reference != "-":
            result["final_geometry_verdict"] = metrics.compare(first, metrics.describe(reference))
    except Exception as error:  # noqa: BLE001 - every failure mode here is a recorded verdict
        result["step_reopen"] = False
        result["error"] = f"{type(error).__name__}: {error}"
        print(json.dumps(result, ensure_ascii=False))
        return 3
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
