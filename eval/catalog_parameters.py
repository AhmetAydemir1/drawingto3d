"""Measure the printed-parameter selection interface, without profile generation or CAD.

Every case keeps its source reading, fixed catalog, full request, raw answer and checks.
The run journal is written before each call. A killed run remains explicitly incomplete.
These development parts do not measure generalisation or prove the selected meanings.

    PYTHONPATH=src .venv/bin/python eval/catalog_parameters.py --label catalog-3b-01
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.catalog import CATALOG_VERSION, PROMPT_VERSION, REPLY_VERSION, propose_parameters
from drawingto3d.llama import ChatSettings, OllamaChat, find_model, installed_models
from drawingto3d.planner import chain_evidence, suggested_names
from drawingto3d.proposal import read_sheet
from model_baseline import CASES_FILE, ResourceSampler, _atomic_json, code_record, manifest_record


def run(folder: Path, cases: list[dict], settings: ChatSettings) -> dict:
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    sampler = ResourceSampler()
    record = {
        "status": "running", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": "parameters only; seen development drawings; no CAD, no semantic acceptance",
        "versions": {"catalog": CATALOG_VERSION, "prompt": PROMPT_VERSION, "reply": REPLY_VERSION},
        "code": code_record(), "manifest": manifest_record(cases), "settings": settings.as_dict(),
        "cases": [], "active": None,
    }
    chat = None

    def checkpoint():
        record["seconds"] = round(time.monotonic() - started, 3)
        record["resources"] = sampler.record()
        _atomic_json(folder / "run.json", record)

    checkpoint()
    sampler.start()
    try:
        model = find_model(installed_models(), settings.model)
        record["model"] = model.as_dict()
        chat = OllamaChat(model.name, settings=settings)
        checkpoint()
        for case in cases:
            case_start = time.monotonic()
            record["active"] = {"case": case["id"], "stage": "reading"}
            checkpoint()
            reading = read_sheet(ROOT / case["drawing"])
            evidence = chain_evidence(reading)
            row = {"id": case["id"], "part_group": case["part_group"], "drawing": case["drawing"],
                   "reading_seconds": round(time.monotonic() - case_start, 3),
                   "refusals": reading.refusals, "evidence": evidence}

            def before_call(candidate):
                record["active"] = {"case": case["id"], "stage": "model", "candidate": candidate}
                _atomic_json(folder / f"{case['id']}.request.json", {**row, "candidate": candidate})
                checkpoint()

            candidate = propose_parameters(chat, evidence, suggested_names(evidence), on_request=before_call)
            row["candidate"] = candidate.model_dump(mode="json")
            row["seconds"] = round(time.monotonic() - case_start, 3)
            _atomic_json(folder / f"{case['id']}.json", row)
            record["cases"].append(row)
            record["active"] = None
            checkpoint()
            print(f"{case['id']}: {candidate.status}; {candidate.seconds:.2f}s; {candidate.errors}", flush=True)
        record["status"] = "complete"
    except BaseException as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        # Save before unloading as well: provider cleanup must never lose finished answers.
        sampler.stop()
        checkpoint()
        if chat is not None:
            try:
                chat.unload()
            except Exception as exc:
                record["unload_error"] = f"{type(exc).__name__}: {exc}"
        record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        checkpoint()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "catalog-parameters")
    parser.add_argument("--cases", nargs="+", default=["plate-pocket-1", "plastic-enclosure-1"])
    parser.add_argument("--model", default="qwen2.5vl:3b")
    parser.add_argument("--num-ctx", type=int, default=16384)
    parser.add_argument("--predict", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if not args.label or Path(args.label).name != args.label or args.label in (".", ".."):
        parser.error("etiket tek klasör adı olmalı")
    available = {case["id"]: case for case in json.loads(CASES_FILE.read_text())["cases"]}
    if set(args.cases) - available.keys() or len(set(args.cases)) != len(args.cases):
        parser.error("bilinmeyen veya tekrarlı parça")
    folder = args.out / args.label
    if folder.exists():
        parser.error(f"çıktı zaten var; yeni etiket seç: {folder}")
    settings = ChatSettings(model=args.model, num_ctx=args.num_ctx, num_predict=args.predict,
                            timeout=args.timeout, temperature=0)
    run(folder, [available[key] for key in args.cases], settings)


if __name__ == "__main__":
    main()
