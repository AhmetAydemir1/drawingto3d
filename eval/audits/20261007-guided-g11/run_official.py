"""G11 official 10-sheet run — frozen manifest order, fresh session per case, real input only.

    ~/.hermes/cache/scratch/cdp-venv/bin/python run_official.py [case_id ...]

Each case: tab cleanup -> g11_runner.py recipes-official/<case>.json -> case record under
cases/<case>.json (+ artifacts in cases/<case>/). One case's failure never aborts the run; the summary
is written to logs/official/summary.json and printed at the end. Recipes without a file are reported as
`recipe-missing` — that is a real blocker for that case, never a silent skip.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
CDP_PYTHON = "/Users/aydemir/.hermes/cache/scratch/cdp-venv/bin/python"
MANIFEST = ROOT / "eval/guided_10_manifest.json"
PYTHON = sys.executable


def case_ids() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [row["case_id"] for row in manifest["cases"]]


def run(cmd: list[str], log_path: pathlib.Path, append: bool = False) -> int:
    with log_path.open("a" if append else "w", encoding="utf-8") as handle:
        handle.write(f"$ {' '.join(cmd)}\n")
        handle.flush()
        proc = subprocess.run(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
    return proc.returncode


def main() -> int:
    argv = sys.argv[1:]
    recipes = HERE / "recipes-official"
    if argv and argv[0] == "--recipes":
        recipes = HERE / argv[1]
        argv = argv[2:]
    wanted = argv or case_ids()
    order = [cid for cid in case_ids() if cid in wanted]
    logs = HERE / "logs/official"
    logs.mkdir(parents=True, exist_ok=True)
    summary = []
    for index, case_id in enumerate(order, 1):
        recipe = recipes / f"{case_id}.json"
        log_path = logs / f"{case_id}.log"
        started = time.strftime("%H:%M:%S")
        print(f"[{index}/{len(order)}] {case_id} … ({started})", flush=True)
        if not recipe.exists():
            summary.append({"case_id": case_id, "status": "recipe-missing", "log": str(log_path)})
            print(f"    recipe-missing: {recipe}", flush=True)
            continue
        run([CDP_PYTHON, str(HERE / "g11_clean.py")], log_path)          # tab hygiene first
        code = run([CDP_PYTHON, str(HERE / "g11_runner.py"), str(recipe)], log_path, append=True)
        record_path = HERE / "cases" / f"{case_id}.json"
        status, verdict, failures = "driver-error", None, None
        if record_path.exists():
            record = json.loads(record_path.read_text(encoding="utf-8"))
            failures = [row["code"] for row in record.get("failures") or []]
            verdict = record.get("final_geometry_verdict")
            status = "recorded"
        summary.append({"case_id": case_id, "status": status, "exit": code, "verdict": verdict,
                        "failures": failures, "log": str(log_path)})
        print(f"    -> status={status} exit={code} verdict={verdict} failures={failures}", flush=True)
    (logs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if all(row["status"] == "recorded" for row in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
