"""Run the frozen evaluator over the corrected-input round's STEPs and merge the verdicts.

    .venv/bin/python eval/audits/20261007-guided-g11-fixes/evaluate_round2.py

For every record under `eval/audits/20261007-guided-g11/rerun-round2/cases/` with a produced STEP:
`evaluate_case.py` runs under `.venv-cad` (cadquery) with the manifest's evaluator-only reference,
exactly like the official round's manual step; `step_reopen`/`bbox`/`features`/
`final_geometry_verdict` are merged into the round's record and the raw evaluator output is kept as
`evaluator.json` next to the case. Cases without a produced STEP are reported as `no-step` — a
recorded outcome, never a silent skip. Only the round's own records are written.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
G11 = ROOT / "eval/audits/20261007-guided-g11"
RERUN = G11 / "rerun-round2"
CAD_PYTHON = ROOT / ".venv-cad/bin/python"


def main() -> int:
    manifest = json.loads((ROOT / "eval/guided_10_manifest.json").read_text(encoding="utf-8"))
    references = {entry["case_id"]: entry.get("reference_identifier_evaluator_only")
                  for entry in manifest["cases"]}
    summary = []
    for record_path in sorted((RERUN / "cases").glob("*.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        case_id = record["case_id"]
        step = (record.get("artifacts") or {}).get("part.step")
        if not (step and (ROOT / step).exists()):
            summary.append({"case_id": case_id, "status": "no-step"})
            continue
        reference = references.get(case_id) or "-"
        result = subprocess.run(
            [str(CAD_PYTHON), str(G11 / "evaluate_case.py"), str(ROOT / step),
             reference if reference == "-" else str(ROOT / reference)],
            cwd=ROOT, capture_output=True, text=True)
        last = [line for line in result.stdout.strip().splitlines() if line.startswith("{")]
        if not last:
            summary.append({"case_id": case_id, "status": "evaluator-error",
                            "exit": result.returncode, "stderr": result.stderr[-500:]})
            continue
        evaluated = json.loads(last[-1])
        (record_path.parent / case_id / "evaluator.json").write_text(
            json.dumps({"exit": result.returncode, "stdout": evaluated,
                        "reference": reference}, ensure_ascii=False, indent=2), encoding="utf-8")
        record["step_reopen"] = evaluated["step_reopen"]
        record["bbox"] = evaluated["bbox"]
        record["features"] = evaluated["features"]
        record["final_geometry_verdict"] = evaluated["final_geometry_verdict"]
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        verdict = evaluated["final_geometry_verdict"]
        summary.append({"case_id": case_id, "status": "evaluated", "exit": result.returncode,
                        "bbox": evaluated["bbox"],
                        "verdict_pass": None if verdict is None else verdict.get("pass"),
                        "error": evaluated.get("error")})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(row["status"] in ("evaluated", "no-step") for row in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
