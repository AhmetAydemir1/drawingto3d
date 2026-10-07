"""Wait for the remaining G11 probe sessions to become ready server-side, then recover them.

    ~/.hermes/cache/scratch/cdp-venv/bin/python probe_recover.py

The client gates (``!$('controls').hidden``) time out while the app (one process, 100% CPU) is still
observing; the sessions themselves keep computing. This watcher polls ``/api/guided/<token>`` until the
session reports options, then runs ``g11_probe.py <source> <name> <token>`` once per pending case and
prints the visible-data summary. Exits when every row is written (or after the wall-clock budget).
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
DEADLINE = time.time() + 3600.0

# (token, source path, out name) — my-part and flange sessions are already uploaded and computing;
# flange-elbow-90 is queued: upload it in a fresh probe once the first two are settled.
ROWS = [
    ("54183758cbde4e5885383b09fe888ee8", "examples/pdf with steps/7/my_part.jpg", "my-part"),
    ("a9ca4c26c29542c6a5e3fe338e0d7210", "examples/pdf with steps/8/Flange.PNG", "flange"),
]


def rows_from_argv(argv: list[str]) -> list[tuple[str, str, str]]:
    """`probe_recover.py <token> <source> <name> [<token> <source> <name> …]` overrides the defaults."""
    if not argv:
        return ROWS
    if len(argv) % 3:
        raise SystemExit("arguments must be token/source/name triples")
    return [(argv[i], argv[i + 1], argv[i + 2]) for i in range(0, len(argv), 3)]


def ready(token: str) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8765/api/guided/{token}", timeout=20) as reply:
            data = json.loads(reply.read().decode("utf-8"))
    except Exception:
        return False
    return bool(data.get("options")) and data.get("callouts") is not None


def main() -> int:
    pending = list(rows_from_argv(sys.argv[1:]))
    while pending and time.time() < DEADLINE:
        for row in list(pending):
            token, source, name = row
            out = HERE / "probes" / f"{name}.json"
            if out.exists():
                print(f"[skip] {name}: already written", flush=True)
                pending.remove(row)
                continue
            if not ready(token):
                continue
            print(f"[ready] {name} ({token[:8]}…) — recovering", flush=True)
            code = subprocess.run([CDP_PYTHON, str(HERE / "g11_probe.py"), source, name, token],
                                  cwd=ROOT).returncode
            print(f"[recover] {name} exit={code}", flush=True)
            if code == 0:
                pending.remove(row)
        if pending:
            time.sleep(30)
    print(json.dumps({"pending": [row[2] for row in pending], "budget_exhausted": bool(pending)},
                     ensure_ascii=False), flush=True)
    return 0 if not pending else 1


if __name__ == "__main__":
    sys.exit(main())
