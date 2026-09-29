"""Lab CLI.

    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab status
    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab next
    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab run --dry-run
    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab run
    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab resume
    PYTHONPATH=src .venv/bin/python -m drawingto3d_lab report

Jobs come from a JSON file (`out/lab/jobs.json` by default) so a run is reproducible from a file
rather than from the command line that happened to be typed. `run` refuses to start while another
heavy job holds the slot, and re-running a job whose idempotency key is already complete does
nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from drawingto3d_lab import LAB_VERSION
from drawingto3d_lab.runner import Job, LabRunner
from drawingto3d_lab.state import read_json, write_json

REPOSITORY = Path(__file__).resolve().parents[2]


def load_jobs(path: Path) -> list[Job]:
    payload = read_json(path)
    if payload is None:
        raise SystemExit(f"iş dosyası yok: {path} (H02 pilotu için elle veya bir üreteçle yazılır)")
    jobs = []
    for entry in payload.get("jobs", []):
        jobs.append(Job(id=entry["id"], command=list(entry["command"]),
                        inputs=[Path(item) for item in entry.get("inputs", [])],
                        result=entry.get("result", "result.json"),
                        timeout_seconds=entry.get("timeout_seconds"),
                        error_class=entry.get("error_class"), notes=entry.get("notes", "")))
    return jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drawingto3d_lab",
                                     description=f"DrawingTo3D deney koşucusu ({LAB_VERSION})")
    parser.add_argument("--root", default=str(REPOSITORY / "out" / "lab"))
    parser.add_argument("--jobs", default=str(REPOSITORY / "out" / "lab" / "jobs.json"))
    parser.add_argument("--write", help="sonucu bu JSON dosyasına da yaz")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("status", help="kilit, sınırlar ve iş durumları")
    commands.add_parser("next", help="tek sonraki iş ve gerekçesi")
    run = commands.add_parser("run", help="işleri koş (önbellekteki işler atlanır)")
    run.add_argument("--dry-run", action="store_true", help="hiçbir şey çalıştırmadan planı yaz")
    commands.add_parser("resume", help="kesintiye uğrayan işleri sürdür")
    commands.add_parser("report", help="iş/job_status/product_verdict tablosu")

    args = parser.parse_args(argv)
    runner = LabRunner(Path(args.root), root_repository=REPOSITORY)

    if args.command == "status":
        payload = runner.status()
    elif args.command == "report":
        payload = runner.report(load_jobs(Path(args.jobs)))
    elif args.command == "next":
        payload = runner.next_job(load_jobs(Path(args.jobs)))
    elif args.command == "run":
        payload = runner.execute(load_jobs(Path(args.jobs)), dry_run=args.dry_run)
    elif args.command == "resume":
        payload = runner.resume(load_jobs(Path(args.jobs)))
    else:  # pragma: no cover - argparse rejects anything else
        parser.error(f"bilinmeyen komut: {args.command}")
        return 2

    if args.write:
        write_json(Path(args.write), payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
