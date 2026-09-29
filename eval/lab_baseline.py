"""H03 → H04: hand the product nothing but the drawing file, then judge its STEP separately.

The point of this driver is the boundary it keeps:

* the product run gets the drawing (a copy) and nothing else — no reference STEP, no label file, no
  parameters, no part id, no verified plan. A product result therefore says something about reading a
  drawing, not about finding the answer;
* after a STEP exists, an *independent* evaluator (`eval/feature_metrics.py`) compares it with the
  corpus reference and reports what disagrees. The product never sees that verdict while it works;
* a refusal is written down as a refusal, with the stage it stopped at and the reason it gave. A
  failure is a result here, and it is not counted as a success.

User edits are counted separately from the scripted run: this driver leaves every product artefact
untouched, so `user_interventions` is 0 for the rows it writes and any later hand edit shows up as a
changed hash rather than being folded into the result.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d_lab import LAB_VERSION  # noqa: E402
from drawingto3d_lab.state import sha256_file, write_json  # noqa: E402

BASELINE_SCHEMA = "drawingto3d.lab.baseline/1"

# One row per part: which file the product gets, and which reading path that file belongs to. At
# least one raster input is included on purpose (PLAN §5 asks for raster coverage).
PARTS = [
    {"part_id": "pilot-plate-01", "file": "drawing.pdf", "kind": "vector"},
    {"part_id": "pilot-plate-02", "file": "drawing.pdf", "kind": "vector"},
    {"part_id": "pilot-step-01", "file": "drawing.pdf", "kind": "vector"},
    {"part_id": "pilot-block-01", "file": "drawing.png", "kind": "raster"},
]

# The error classes of PLAN §H04, so a failure lands in one of the named layers instead of "failed".
ERROR_CLASSES = ("girdi/sayfa/görünüş", "OCR-değer-birim", "ölçü→geometri bağlantısı", "model şeması",
                 "kısıt/kalibrasyon", "CAD işlemi", "değerlendirici", "bellek/süre")


def _load_metrics():
    spec = importlib.util.spec_from_file_location("baseline_metrics", ROOT / "eval/feature_metrics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cli(arguments: list[str], workdir: Path) -> dict:
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    completed = subprocess.run([sys.executable, "-m", "drawingto3d.cli", *arguments], cwd=workdir,
                               env=environment, capture_output=True, text=True)
    # A refusal is printed by `parser.exit(2, json)`, which writes to *stderr*; a success goes to
    # stdout. Both are the CLI's own JSON, so both are read as the result.
    payload = None
    for stream in (completed.stdout, completed.stderr):
        text = (stream or "").strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            break
    return {"command": ["python", "-m", "drawingto3d.cli", *arguments], "exit_code": completed.returncode,
            "result": payload, "stdout_tail": completed.stdout[-1200:], "stderr_tail": completed.stderr[-1200:]}


def _classify(steps: list[dict], verdict: dict | None) -> tuple[str, str]:
    """Which layer failed, named from the evidence rather than from the exit code alone."""
    if verdict is not None:
        if verdict.get("verdict") == "pass":
            return "pass", ""
        failed = list(verdict.get("failed_checks") or [])
        detail = ", ".join(failed) or f"verdict {verdict.get('verdict')}"
        # A wrong *part* is a geometry/measurement failure; the evaluator only failed if it could not
        # judge the artefact at all.
        if {"readable", "solids", "valid"} & set(failed):
            return "değerlendirici", f"the produced file could not be judged: {detail}"
        if "units" in failed or "alignment" in failed:
            ratios = ((verdict.get("checks") or {}).get("units") or {}).get("detail", {}).get(
                "scale_ratios")
            return "kısıt/kalibrasyon", f"{detail}; produced/reference size ratios {ratios}"
        return "ölçü→geometri bağlantısı", detail
    for step in reversed(steps):
        result = step.get("result") or {}
        refusals = result.get("refusals") or []
        if refusals:
            text = " | ".join(str(item) for item in refusals)
            if "kalibrasyon" in text or "ölçek" in text:
                return "kısıt/kalibrasyon", text
            if "eşleş" in text or "okunamadı" in text:
                return "girdi/sayfa/görünüş", text
            return "kısıt/kalibrasyon", text
        # A step that died without a JSON refusal still says where it died, on stderr.
        tail = (step.get("stderr_tail") or "").strip()
        if step.get("exit_code") not in (0, None) and tail:
            last = tail.splitlines()[-1]
            if "not printed on the drawing" in last or "CadFailure" in last:
                # The plan carried a number the sheet never printed → the CAD build refused it.
                return "CAD işlemi", last
            if "okunamadı" in last or "pafta" in last.lower():
                return "girdi/sayfa/görünüş", last
            if "süre" in last or "bellek" in last:
                return "bellek/süre", last
            return "CAD işlemi", last
    return "girdi/sayfa/görünüş", "the reading chain produced neither a plan nor a refusal"


def _failure_lines(steps: list[dict]) -> list[str]:
    """The line a dying step left behind, skipping the ones a JSON refusal already explains."""
    out = []
    for step in steps:
        if step.get("exit_code") in (0, None) or (step.get("result") or {}).get("refusals"):
            continue
        tail = (step.get("stderr_tail") or "").strip()
        if not tail:
            continue
        lines = [line.strip() for line in tail.splitlines() if line.strip()]
        marker = [line for line in lines if any(word in line for word in
                                               ("CadFailure", "Error", "error:", "Exception"))]
        out.append((marker or lines)[-1])
    return out


def _model_step(drawing: Path, workdir: Path) -> dict:
    """Run the local model path on the same drawing and keep its own record."""
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "drawingto3d.cli", "model-plan", str(drawing), str(workdir / "model")],
            cwd=workdir, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
            capture_output=True, text=True, timeout=300)
        payload = None
        for stream in (completed.stdout, completed.stderr):
            text = (stream or "").strip()
            if text.startswith("{"):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
                if payload is not None:
                    break
        return {"command": ["python", "-m", "drawingto3d.cli", "model-plan", str(drawing),
                            str(workdir / "model")],
                "exit_code": completed.returncode, "result": payload,
                "stderr_tail": completed.stderr[-600:], "timeout": False}
    except subprocess.TimeoutExpired:
        return {"command": ["model-plan"], "exit_code": None, "result": None,
                "stderr_tail": "", "timeout": True}


def run_part(row: dict, corpus: Path, out_root: Path, metrics, *, with_model: bool = True) -> dict:
    part_id = row["part_id"]
    workdir = out_root / part_id
    (workdir / "input").mkdir(parents=True, exist_ok=True)
    source = corpus / part_id / row["file"]
    drawing = workdir / "input" / row["file"]
    if drawing.exists() and sha256_file(drawing) != sha256_file(source):
        raise SystemExit(f"{drawing} zaten var ve kaynaktan farklı: girdi değişmez")
    shutil.copyfile(source, drawing)

    steps: list[dict] = []
    if row["kind"] == "raster":
        steps.append(_cli(["read", str(drawing), str(workdir / "product")], workdir))
        records = workdir / "product" / "records.json"
        if records.exists():
            steps.append(_cli(["build", str(drawing), str(records), str(workdir / "product")], workdir))
    else:
        steps.append(_cli(["propose", str(drawing), str(workdir / "product")], workdir))
        plan = workdir / "product" / "plan.json"
        if plan.exists():
            steps.append(_cli(["build-general", str(plan), str(workdir / "product"),
                               "--drawing", str(drawing)], workdir))

    steps_path = workdir / "product-steps.json"
    write_json(steps_path, {"schema": BASELINE_SCHEMA, "part_id": part_id, "steps": steps})

    # The same input to the local *model* path, kept apart from the model-less result above. The
    # command picks a vision model when this box has one (the request carries the drawing image), so
    # what it makes of the picture is recorded instead of assumed.
    model_step = _model_step(drawing, workdir) if with_model else None
    write_json(workdir / "model-step.json", {"schema": BASELINE_SCHEMA, "part_id": part_id,
                                             "model_step": model_step})

    produced = sorted((workdir / "product").glob("*.step"))
    verdict = None
    produced_summary = None
    if produced:
        produced_record = metrics.extract(str(produced[0]))
        truth_record = metrics.extract(str(corpus / part_id / "part.step"))
        verdict = metrics.compare(produced_record, truth_record)
        write_json(workdir / "evaluator-verdict.json", verdict)
        produced_summary = {"bbox_size": produced_record.get("bbox_size"),
                            "volume_mm3": produced_record.get("volume_mm3"),
                            "recorded_units": produced_record.get("recorded_units"),
                            "features": len(produced_record.get("features") or []),
                            "reference_bbox_size": truth_record.get("bbox_size"),
                            "reference_volume_mm3": truth_record.get("volume_mm3")}

    error_class, detail = _classify(steps, verdict)
    return {
        "part_id": part_id, "input_kind": row["kind"], "input_file": row["file"],
        "input_sha256": sha256_file(drawing),
        "reference_sha256": sha256_file(corpus / part_id / "part.step"),
        "commands": [step["command"] for step in steps],
        "exit_codes": [step["exit_code"] for step in steps],
        "product_stage_reached": [step["command"][3] for step in steps],
        "product_refusals": [refusal for step in steps
                             for refusal in ((step.get("result") or {}).get("refusals") or [])],
        "product_step": str(produced[0]) if produced else None,
        "produced_part": produced_summary,
        "product_failure": _failure_lines(steps),
        "evaluator": None if verdict is None else {
            "verdict": verdict.get("verdict"), "failed_checks": verdict.get("failed_checks"),
            "issues": verdict.get("issues"), "alignment": verdict.get("alignment"),
            "not_evaluated": verdict.get("not_evaluated"),
        },
        "error_class": error_class, "error_detail": detail,
        "model_path": {
            "ran": model_step is not None and not model_step["timeout"],
            "timed_out": bool(model_step and model_step["timeout"]),
            "model": (model_step or {}).get("result", {}).get("model") if (model_step or {}).get("result") else None,
            "plan_produced": bool((model_step or {}).get("result", {}).get("plan")) if (model_step or {}).get("result") else False,
            "evidence": (model_step or {}).get("result"),
            "note": "the model step receives the drawing (a vision model is chosen when installed, and "
                    "the request carries the image); it plans from the chain's evidence, so an empty "
                    "evidence means the picture was never interpreted",
        },
        "product_input_leakage": "none: the run received the drawing file only "
                                 "(no STEP, labels, parameters, part id or verified plan)",
        "user_interventions": 0,
        "evidence": {"product_steps": str(steps_path),
                     "verdict": str(workdir / "evaluator-verdict.json") if verdict else None},
    }


def _summary(rows: list[dict]) -> dict:
    return {
        "parts": len(rows),
        "by_error_class": {name: sum(1 for row in rows if row["error_class"] == name)
                           for name in ERROR_CLASSES},
        "evaluated": sum(1 for row in rows if row["evaluator"]),
        "product_pass": sum(1 for row in rows if (row["evaluator"] or {}).get("verdict") == "pass"),
        "product_wrong_part": sum(1 for row in rows
                                 if (row["evaluator"] or {}).get("verdict") == "fail"),
        "refused_before_cad": sum(1 for row in rows if not row["product_step"] and row["product_refusals"]),
    }


def summarise_from_disk(row: dict, workdir: Path, corpus: Path, metrics) -> dict:
    """Rebuild a row from what a finished run left on disk (no product call, no model call).

    The raster reading path is not reproducible run to run — one attempt built a STEP the evaluator
    failed, the next refused a fabricated number — so both attempts are kept rather than letting the
    last one overwrite the first.
    """
    part_id = row["part_id"]
    steps = json.loads((workdir / "product-steps.json").read_text(encoding="utf-8"))["steps"]
    model_path_file = workdir / "model-step.json"
    model_step = (json.loads(model_path_file.read_text(encoding="utf-8"))["model_step"]
                  if model_path_file.exists() else None)
    drawing = workdir / "input" / row["file"]
    produced = sorted((workdir / "product").glob("*.step"))
    verdict = None
    produced_summary = None
    if produced:
        produced_record = metrics.extract(str(produced[0]))
        truth_record = metrics.extract(str(corpus / part_id / "part.step"))
        verdict = metrics.compare(produced_record, truth_record)
        produced_summary = {"bbox_size": produced_record.get("bbox_size"),
                            "volume_mm3": produced_record.get("volume_mm3"),
                            "recorded_units": produced_record.get("recorded_units"),
                            "features": len(produced_record.get("features") or []),
                            "reference_bbox_size": truth_record.get("bbox_size"),
                            "reference_volume_mm3": truth_record.get("volume_mm3")}
    error_class, detail = _classify(steps, verdict)
    return {
        "part_id": part_id, "input_kind": row["kind"], "input_file": row["file"],
        "input_sha256": sha256_file(drawing),
        "reference_sha256": sha256_file(corpus / part_id / "part.step"),
        "commands": [step["command"] for step in steps],
        "exit_codes": [step["exit_code"] for step in steps],
        "product_stage_reached": [step["command"][3] for step in steps],
        "product_refusals": [refusal for step in steps
                             for refusal in ((step.get("result") or {}).get("refusals") or [])],
        "product_step": str(produced[0]) if produced else None,
        "produced_part": produced_summary,
        "product_failure": _failure_lines(steps),
        "evaluator": None if verdict is None else {
            "verdict": verdict.get("verdict"), "failed_checks": verdict.get("failed_checks"),
            "issues": verdict.get("issues"), "alignment": verdict.get("alignment"),
            "not_evaluated": verdict.get("not_evaluated"),
        },
        "error_class": error_class, "error_detail": detail,
        "model_path": {
            "ran": model_step is not None and not model_step["timeout"],
            "timed_out": bool(model_step and model_step["timeout"]),
            "model": (model_step or {}).get("result", {}).get("model") if (model_step or {}).get("result") else None,
            "plan_produced": bool((model_step or {}).get("result", {}).get("plan")) if (model_step or {}).get("result") else False,
            "evidence": (model_step or {}).get("result"),
            "note": "the model step receives the drawing (a vision model is chosen when installed, and "
                    "the request carries the image); it plans from the chain's evidence, so an empty "
                    "evidence means the picture was never interpreted",
        },
        "product_input_leakage": "none: the run received the drawing file only "
                                 "(no STEP, labels, parameters, part id or verified plan)",
        "user_interventions": 0,
        "evidence": {"product_steps": str(workdir / "product-steps.json"),
                     "verdict": str(workdir / "evaluator-verdict.json") if verdict else None,
                     "model_step": str(workdir / "model-step.json")},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "out/lab/data/v2")
    parser.add_argument("--out", type=Path, default=ROOT / "out/lab/baseline")
    parser.add_argument("--results", type=Path,
                        default=ROOT / "out/lab/review-checkpoint/baseline-results.json")
    parser.add_argument("--part", action="append", default=None,
                        help="yalnız bu parçayı koş (tekrarlanabilir)")
    parser.add_argument("--reuse", action="store_true",
                        help="ürün/model çağırmadan, diskteki koşulardan sonuç dosyasını yeniden kur")
    parser.add_argument("--no-model", action="store_true",
                        help="yerel model adımını atla (ürün yolu ve evaluator yine koşar)")
    args = parser.parse_args()

    metrics = _load_metrics()
    if args.reuse:
        runs = []
        for run_dir in sorted(path for path in args.out.iterdir() if path.is_dir()):
            rows = []
            for row in PARTS:
                workdir = run_dir / row["part_id"]
                if (workdir / "product-steps.json").exists():
                    rows.append(summarise_from_disk(row, workdir, args.corpus, metrics))
            if rows:
                runs.append({"run_id": run_dir.name, "parts": rows})
        rows = [row for run in runs for row in run["parts"]]
        payload = {
            "schema": BASELINE_SCHEMA, "lab_version": LAB_VERSION,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "mode": "reuse (her koşu ayrı kayıt; raster okuma koşudan koşuya değişiyor)",
            "corpus": str(args.corpus),
            "corpus_manifest_sha256": sha256_file(args.corpus / "manifest.json"),
            "entry_boundary": "product ← drawing only; evaluator ← produced STEP vs corpus reference",
            "error_classes": list(ERROR_CLASSES),
            "runs": runs,
            "summary": _summary(rows),
            "model_path": {
                "runs": [{"run_id": run["run_id"], "part_id": row["part_id"],
                          **(row.get("model_path") or {})}
                         for run in runs for row in run["parts"]],
                "comparison": "model-less: `propose` (vector) / `read`+`build` (raster); model: "
                              "`model-plan` on the same file. The model path plans from the reading "
                              "chain's evidence, so where the chain refuses, the model is never asked "
                              "to interpret the picture.",
            },
        }
        write_json(args.results, payload)
        print(json.dumps({"results": str(args.results), "runs": [r["run_id"] for r in runs],
                          "summary": payload["summary"]}, ensure_ascii=False, indent=2))
        return

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    metrics = _load_metrics()
    rows = []
    for row in PARTS:
        if args.part and row["part_id"] not in args.part:
            continue
        print(f"--- {row['part_id']} ({row['kind']})")
        record = run_part(row, args.corpus, args.out / run_id, metrics,
                          with_model=not args.no_model)
        rows.append(record)
        print(f"    error_class={record['error_class']} "
              f"evaluator={(record['evaluator'] or {}).get('verdict')} "
              f"refusals={record['product_refusals']}")

    payload = {
        "schema": BASELINE_SCHEMA, "lab_version": LAB_VERSION, "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "corpus": str(args.corpus), "corpus_manifest_sha256": sha256_file(args.corpus / "manifest.json"),
        "entry_boundary": "product ← drawing only; evaluator ← produced STEP vs corpus reference",
        "error_classes": list(ERROR_CLASSES),
        "parts": rows,
        "summary": _summary(rows),
        "model_path": {
            "runs": [{"part_id": row["part_id"], **(row.get("model_path") or {})} for row in rows],
            "comparison": "model-less: `propose` (vector) / `read`+`build` (raster); model: `model-plan` "
                          "on the same file. The model path plans from the reading chain's evidence, so "
                          "where the chain refuses, the model is never asked to interpret the picture.",
        },
    }
    write_json(args.results, payload)
    print(json.dumps({"results": str(args.results), "summary": payload["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
