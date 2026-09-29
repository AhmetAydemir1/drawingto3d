"""Turn an existing script into a lab case: run it, write the verdict JSON the runner expects.

    .venv/bin/python eval/lab_case.py --result out/lab/runs/<run>/result.json -- \\
        .venv/bin/python eval/feature_metrics_audit.py

The lab runner enforces the case timeout and captures stdout/stderr; this adapter only decides the
product verdict from the command's real exit code, so a script that fails cannot be recorded as a
pass. A script that wants to say more than pass/fail can write its own JSON with a
`product_verdict` field and be used directly as the job command instead.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bir betiği lab vakası olarak çalıştır")
    parser.add_argument("--result", required=True, help="yazılacak verdict JSON yolu")
    parser.add_argument("--label", default=""
                        , help="sonuç dosyasına yazılacak kısa etiket")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        parser.error("çalıştırılacak komut gerekli: -- KOMUT ...")

    started = time.perf_counter()
    completed = subprocess.run(command, check=False)
    seconds = round(time.perf_counter() - started, 3)
    verdict = "pass" if completed.returncode == 0 else "fail"
    payload = {"product_verdict": verdict, "exit_code": completed.returncode, "seconds": seconds,
               "command": command, "label": args.label}
    Path(args.result).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False))
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
