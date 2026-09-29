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
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d_lab import LAB_VERSION  # noqa: E402
from drawingto3d_lab.runner import subprocess_runner  # noqa: E402
from drawingto3d_lab.state import Lab, sha256_file, write_json  # noqa: E402

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


CASE_BUDGET_SECONDS = 600     # bir vakanın *bütün* adımları bu bütçeyi paylaşır (anlaşma)
RUN_BUDGET_SECONDS = 7200     # koşunun tamamı


class Budget:
    """Kalan süre: adımlar aynı bütçeyi paylaşır, yeni adım yalnız kalan süreyle başlar.

    Tavan sessizce yükseltilmez. Süre bitmişse adım hiç başlamaz ve bu, satırda sonuç olarak yazılır;
    süre azsa adım kalan süreyle başlar ve zaman aşımı gerçek bir sonuç olarak raporlanır.
    """

    def __init__(self, seconds: float, *, label: str = "case") -> None:
        self.total = float(seconds)
        self.label = label
        self.started = time.monotonic()
        self.steps: list[dict] = []

    def remaining(self) -> float:
        return max(0.0, self.total - (time.monotonic() - self.started))

    def note(self, step: str, seconds: float) -> None:
        self.steps.append({"step": step, "seconds": round(float(seconds), 3),
                           "remaining_seconds": round(self.remaining(), 3)})

    def as_record(self) -> dict:
        return {"label": self.label, "budget_seconds": self.total,
                "remaining_seconds": round(self.remaining(), 3), "steps": self.steps}


def _cli(arguments: list[str], workdir: Path, *, log: Path | None = None,
         budget: "Budget | None" = None) -> dict:
    """Run one product command under the lab runner's proven timeout/process-tree protection.

    `subprocess.run(timeout=...)` kills the direct child only: a product command that starts children of
    its own — the raster arm runs vision and code models — would leave them running, which is exactly how
    a local experiment slips into the background. `subprocess_runner` signals the whole process group.

    `log` is where the product writes its model-call evidence (adapter boundary); the file is the record,
    not a sentence about one. `budget` is the case's remaining time: a step never gets more than the case
    has left, and a step with no time left is not started at all.
    """
    command = [sys.executable, "-m", "drawingto3d.cli", *arguments]
    shown = ["python", "-m", "drawingto3d.cli", *arguments]
    if log is not None:
        command += ["--inference-log", str(log)]
    if budget is not None and budget.remaining() <= 1.0:
        return {"command": shown, "started": False, "exit_code": None, "seconds": 0.0,
                "timed_out": False, "descendants_alive": False, "result": None,
                "not_started_reason": f"kalan süre yok ({budget.remaining():.1f} s): adım başlatılmadı",
                "stdout_tail": "", "stderr_tail": ""}
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    timeout = int(budget.remaining()) if budget is not None else CASE_BUDGET_SECONDS
    completed = subprocess_runner(command, timeout=timeout, env=environment)
    if budget is not None:
        budget.note(arguments[0], completed.get("seconds") or 0.0)
    # A refusal is printed by `parser.exit(2, json)`, which writes to *stderr*; a success goes to
    # stdout. Both are the CLI's own JSON, so both are read as the result.
    payload = None
    for stream in (completed.get("stdout"), completed.get("stderr")):
        text = (stream or "").strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            break
    return {"command": shown, "started": True, "exit_code": completed["exit_code"],
            "seconds": completed.get("seconds"), "timed_out": bool(completed.get("timed_out")),
            "descendants_alive": completed.get("descendants_alive"),
            "result": payload, "stdout_tail": (completed.get("stdout") or "")[-1200:],
            "stderr_tail": (completed.get("stderr") or "")[-1200:]}


def _call_evidence(workdir: Path, name: str) -> dict | None:
    """The product's own model-call record; None when the product wrote none."""
    path = workdir / name
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _step_logs(workdir: Path, folder: str = "product") -> list[dict]:
    """Every step's own call record, in step order.

    Each command writes its own file (`inference-log-<step>.json`): sharing one path meant the second
    command's Recorder rewrote the file and the first command's calls disappeared from the evidence.
    """
    home = workdir / folder
    records = []
    for path in sorted(home.glob("inference-log*.json")):
        record = _call_evidence(home, path.name)
        if record is not None:
            record["step"] = path.name.removeprefix("inference-log").removesuffix(".json").lstrip("-")
            records.append(record)
    return records


def _merged(records: list[dict]) -> dict | None:
    """Union of the step records: None when the arm left no record at all (unmeasured, not zero)."""
    if not records:
        return None
    from drawingto3d.inference_log import merge_records

    merged = merge_records(records)
    merged["per_step"] = [{"step": record.get("step"), "attempts": record.get("attempts"),
                           "completed": record.get("completed"), "failed": record.get("failed"),
                           "unfinished": record.get("unfinished"),
                           "image_attached": record.get("image_attached"),
                           "kinds": record.get("kinds")} for record in records]
    return merged


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


def _model_step(drawing: Path, workdir: Path, *, case: "Budget | None" = None) -> dict:
    """Run the local model arm on the same drawing and keep its own record.

    The model arm is a second arm, not a footnote: if it produces a plan, that plan is built and
    evaluated under the same acceptance contract as the rule path, so the model's geometry has a
    measured result. If it produces none, the reason is recorded instead.

    The build gets the source drawing (`--drawing`, T03): a plan whose `source.kind` is a drawing cannot
    be compiled without it, and building without it made every model plan fail for a reason that had
    nothing to do with the model. The plan carries the drawing's hash, so the product — not this driver
    — is the one that decides whether the pair is legitimate.
    """
    home = workdir / "model"
    home.mkdir(parents=True, exist_ok=True)
    step = _cli(["model-plan", str(drawing), str(home)], workdir,
                log=home / "inference-log-plan.json", budget=case)
    step["timeout"] = bool(step.get("timed_out"))
    step["not_started"] = step.get("not_started_reason")
    evidence = _merged(_step_logs(workdir, "model"))
    step["inference_records"] = [str(path) for path in sorted(home.glob("inference-log*.json"))]
    step["inference"] = evidence
    plan = Path((step.get("result") or {}).get("plan") or "")
    step["plan_produced"] = bool(plan.name) and plan.exists()
    step["built"] = None
    step["evaluated"] = None
    if step["plan_produced"]:
        built = _cli(["build-general", str(plan), str(home), "--drawing", str(drawing)], workdir,
                     budget=case)
        step["built"] = {"command": built["command"], "exit_code": built["exit_code"],
                         "started": built.get("started", True),
                         "failure": _failure_lines([built]) or (built.get("result") or {}).get("refusals")}
        produced = sorted(home.glob("*.step"))
        step["built"]["step"] = str(produced[0]) if produced else None
        step["evaluated"] = bool(produced)
    return step


def _trace(stages: list[tuple]) -> dict:
    """Bir kolun izi: hangi adım gerçekten çalıştı, hangisi düştü, hangisi hiç başlamadı.

    "Nerede ayrıldı" ile "nasıl bitti" aynı şey değildir: kural yolu planı üretip kurulumda düşebilir,
    model kolu hiç çağrı almadan bitebilir. Daha önemlisi, çalışılmayan bir adımın `false` bayrağı bir
    hata *değildir*; onu terminal hata saymak kök hatayı hiç koşmamış bir adımda gösterir
    (review4/U02: plan hiç oluşmadığı hâlde `terminal_failure=verdict_pass` yazılıyordu).

    Bu yüzden her adım durumunu taşır:

    * `completed` — çalıştı ve geçti;
    * `failed` — çalıştı ve düştü;
    * `not_started` — hiç başlamadı (ör. kolu başlatan komut çağrılmadı);
    * `blocked_by_previous` — önceki adım düştüğü için hiç çalışamadı.

    Adımlar `(name, ok, detail)` ya da `(name, ok, detail, ran)` olarak verilir; `ran` biliniyorsa
    durum ondan okunur. `first_divergence` geçmeyen ilk adımdır (ilk anlamsal sapma), `terminal_failure`
    ise gerçekten çalışıp düşen **son** adım — çalışılmamış bir adım asla terminal hata olmaz.
    """
    resolved: list[tuple[str, bool, str, str]] = []
    blocked = False
    for entry in stages:
        name, ok, detail = entry[0], entry[1], entry[2]
        ran = entry[3] if len(entry) > 3 else None
        if ok:
            status = "completed"
        elif ran is True:
            status = "failed"
        elif blocked:
            status = "blocked_by_previous"
        elif ran is False:
            status = "not_started"
        else:
            # `ran` bilinmiyor ve kendisinden önce düşen adım yok: ilk düşüş buraya yazılır.
            status = "failed"
        if status == "failed":
            blocked = True
        resolved.append((name, ok, detail, status))
    failed = [name for name, _ok, _detail, status in resolved if status == "failed"]
    reached = [name for name, _ok, _detail, status in resolved if status in ("completed", "failed")]
    return {
        "stages": [{"stage": name, "ok": ok, "detail": detail, "status": status}
                   for name, ok, detail, status in resolved],
        "first_divergence": next((name for name, ok, _detail, _status in resolved if not ok), None),
        "terminal_failure": failed[-1] if failed else None,
        "last_stage_reached": reached[-1] if reached else None,
        "not_started": [name for name, _ok, _detail, status in resolved if status == "not_started"],
        "blocked_by_previous": [name for name, _ok, _detail, status in resolved
                                if status == "blocked_by_previous"],
        "counts": {status: sum(1 for _n, _o, _d, value in resolved if value == status)
                   for status in ("completed", "failed", "not_started", "blocked_by_previous")},
    }


def _call_fields(log: dict | None) -> dict:
    """Kolun çağrı kanıtı: kayıt yoksa `null` (ölçülmedi), kayıt varsa ölçülmüş alanlar."""
    if log is None:
        return {"inference_called": None, "image_attached": None, "server_ok": None,
                "unfinished": None, "attempts": None, "kinds": None, "models": None,
                "per_step": None, "records": 0}
    return {"inference_called": bool(log.get("inference_called")),
            "image_attached": bool(log.get("image_attached")),
            "server_ok": bool(log.get("server_ok")),
            "unfinished": int(log.get("unfinished", 0) or 0),
            "attempts": int(log.get("attempts", 0) or 0),
            "kinds": list(log.get("kinds") or []),
            "models": log.get("models"),
            "per_step": log.get("per_step"),
            "records": int(log.get("records", 0) or 0)}


def _arms(product_log: dict | None, model_log: dict | None, model_step: dict | None,
          model_built: dict, model_verdict: dict | None, raster: bool,
          product_trace: dict | None = None) -> dict:
    """Kol başına gerçek boru hattı, model kimliği ve ayarı.

    The raster arm is named for what it is — a free-code program written by models over OCR records —
    and not as a structured product path; the vector rule path prints no model call at all. Each arm's
    call evidence comes from its own per-step records and is reported per arm: an arm with no record is
    `null` (unmeasured), which is not the same as an arm measured to have made zero calls.
    """
    plan_produced = bool((model_step or {}).get("plan_produced")) or bool(
        ((model_step or {}).get("result") or {}).get("plan"))
    model_trace = _trace([
        ("command_started", bool(model_step), "model-plan", bool(model_step)),
        ("plan_produced", plan_produced, "plan.json" if plan_produced else "yok", bool(model_step)),
        ("step_built", bool(model_built.get("step")), model_built.get("step") or
         (model_built.get("failure") or "yok"), plan_produced),
        ("evaluated", model_verdict is not None,
         "" if model_verdict is None else str(model_verdict.get("verdict")),
         bool(model_built.get("step"))),
        ("verdict_pass", bool(model_verdict and model_verdict.get("verdict") == "pass"),
         "" if model_verdict is None else str(model_verdict.get("verdict")),
         model_verdict is not None),
    ])
    return {
        "product": {
            "arm": "rule" if not raster else "raster-free-code",
            "pipeline": ("raster: OCR'den ölçü kayıtları, görüntü okuyan model + kod modeli geo.* "
                         "programı yazar, sonra katı kurulur (serbest kod kolu)"
                         if raster else
                         "vektör: kural okuyucusu paftayı okur, katı kurulur (kural kolu)"),
            **_call_fields(product_log),
            "trace": product_trace,
        },
        "model": {
            "pipeline": "model-plan: yerel sohbet modeli okuma zincirinin kanıtından plan çıkarır, "
                        "plan aynı kabul sözleşmesiyle derlenip değerlendirilir",
            "ran": model_step is not None and not model_step["timeout"],
            "timed_out": bool(model_step and model_step["timeout"]),
            "command_started": bool(model_step),
            "plan_produced": plan_produced,
            "step_built": bool(model_built.get("step")),
            "evaluated": model_verdict is not None,
            **_call_fields(model_log),
            "build_failure": model_built.get("failure"),
            "verdict": None if model_verdict is None else model_verdict.get("verdict"),
            "trace": model_trace,
        },
    }


def run_part(row: dict, corpus: Path, out_root: Path, metrics, *, with_model: bool = True,
             run_budget: "Budget | None" = None) -> dict:
    part_id = row["part_id"]
    workdir = out_root / part_id
    (workdir / "input").mkdir(parents=True, exist_ok=True)
    source = corpus / part_id / row["file"]
    drawing = workdir / "input" / row["file"]
    if drawing.exists() and sha256_file(drawing) != sha256_file(source):
        raise SystemExit(f"{drawing} zaten var ve kaynaktan farklı: girdi değişmez")
    shutil.copyfile(source, drawing)

    product = workdir / "product"
    # Bir vakanın bütün adımları 600 saniyeyi paylaşır (T04); koşu bütçesi daha azsa vaka onunla başlar.
    case_seconds = CASE_BUDGET_SECONDS if run_budget is None else min(CASE_BUDGET_SECONDS,
                                                                     run_budget.remaining())
    case = Budget(case_seconds, label=part_id)
    steps: list[dict] = []
    if row["kind"] == "raster":
        steps.append(_cli(["read", str(drawing), str(product)], workdir,
                          log=product / "inference-log-read.json", budget=case))
        records = product / "records.json"
        if records.exists():
            steps.append(_cli(["build", str(drawing), str(records), str(product)], workdir,
                              log=product / "inference-log-build.json", budget=case))
    else:
        steps.append(_cli(["propose", str(drawing), str(product)], workdir,
                          log=product / "inference-log-propose.json", budget=case))
        plan = product / "plan.json"
        if plan.exists():
            steps.append(_cli(["build-general", str(plan), str(product), "--drawing", str(drawing)],
                              workdir, budget=case))

    steps_path = workdir / "product-steps.json"
    write_json(steps_path, {"schema": BASELINE_SCHEMA, "part_id": part_id, "steps": steps,
                            "case_budget": case.as_record()})

    # The same input to the local *model* arm, kept apart from the rule result above. The command plans
    # from the reading chain's evidence; whether a model was called at all, and whether an image went
    # with the request, is the adapter record's answer, not a note here.
    model_step = _model_step(drawing, workdir, case=case) if with_model else None
    write_json(workdir / "model-step.json", {"schema": BASELINE_SCHEMA, "part_id": part_id,
                                             "model_step": model_step})

    produced = sorted((workdir / "product").glob("*.step"))
    truth_record = metrics.extract(str(corpus / part_id / "part.step"))
    verdict = None
    produced_summary = None
    if produced:
        produced_record = metrics.extract(str(produced[0]))
        verdict = metrics.compare(produced_record, truth_record)
        write_json(workdir / "evaluator-verdict.json", verdict)
        produced_summary = {"bbox_size": produced_record.get("bbox_size"),
                            "volume_mm3": produced_record.get("volume_mm3"),
                            "recorded_units": produced_record.get("recorded_units"),
                            "features": len(produced_record.get("features") or []),
                            "reference_bbox_size": truth_record.get("bbox_size"),
                            "reference_volume_mm3": truth_record.get("volume_mm3")}

    # The model arm's own artefact is judged by the same contract as the rule path's: "the model planned
    # something" and "the model got the part right" must not be the same sentence.
    model_built = (model_step or {}).get("built") or {}
    model_verdict = None
    if model_built.get("step"):
        model_verdict = metrics.compare(metrics.extract(model_built["step"]), truth_record)
        write_json(workdir / "model-verdict.json", model_verdict)

    error_class, detail = _classify(steps, verdict)
    product_logs = _step_logs(workdir, "product")
    product_log = _merged(product_logs)
    model_logs = _step_logs(workdir, "model")
    model_log = _merged(model_logs)
    raster = row["kind"] == "raster"
    produced_records = (product / "records.json").exists()
    produced_program = bool(sorted(product.glob("*.py")))
    produced_plan = (product / "plan.json").exists()
    product_trace = _trace([
        ("command_started", bool(steps), f"{len(steps)} adım", bool(steps)),
        ("plan_produced", produced_plan or produced_records,
         "plan.json" if produced_plan else ("records.json" if produced_records else "yok"),
         bool(steps)),
        ("step_built", bool(produced), produced[0].name if produced else "yok",
         produced_plan or produced_records),
        ("evaluated", verdict is not None, "" if verdict else "değerlendirilecek STEP yok",
         bool(produced)),
        ("verdict_pass", bool(verdict and verdict.get("verdict") == "pass"),
         "" if verdict is None else str(verdict.get("verdict")), verdict is not None),
    ])
    return {
        "part_id": part_id, "input_kind": row["kind"], "input_file": row["file"],
        "input_sha256": sha256_file(drawing),
        "reference_sha256": sha256_file(corpus / part_id / "part.step"),
        "commands": [step["command"] for step in steps],
        "exit_codes": [step["exit_code"] for step in steps],
        "timed_out": [bool(step.get("timed_out")) for step in steps],
        "not_started": [step.get("not_started_reason") for step in steps
                        if step.get("not_started_reason")],
        "case_budget": case.as_record(),
        "product_stage_reached": [step["command"][3] for step in steps],
        "product_refusals": [refusal for step in steps
                             for refusal in ((step.get("result") or {}).get("refusals") or [])],
        "product_step": str(produced[0]) if produced else None,
        "produced_part": produced_summary,
        "product_failure": _failure_lines(steps),
        # -- S03/T01: each step asked separately, each answer an artifact rather than a sentence ------
        # `command_started` is the arm's own command list. `inference_called`, `image_attached` and
        # `unfinished` come from the adapter-boundary records the product wrote, one file *per step*
        # (`product/inference-log-<step>.json`): a shared path meant the second command's Recorder
        # rewrote the file and the first command's calls vanished from the evidence. `image_attached`
        # says the request carried the image; it does not say the server used it. `plan_produced`,
        # `records_produced` and `program_produced` are three different artefacts and are not merged
        # into one "produced" flag.
        "command_started": bool(steps),
        "inference_called": None if product_log is None else bool(product_log.get("inference_called")),
        "image_attached": None if product_log is None else bool(product_log.get("image_attached")),
        "unfinished": None if product_log is None else int(product_log.get("unfinished", 0)),
        "plan_produced": produced_plan,
        "records_produced": produced_records,
        "program_produced": produced_program,
        "step_built": bool(produced),
        "evaluated": verdict is not None,
        "inference_logs": [str(path) for path in sorted(product.glob("inference-log*.json"))],
        "product_trace": product_trace,
        "arms": _arms(product_log, model_log, model_step, model_built, model_verdict, raster,
                      product_trace),
        "evaluator": None if verdict is None else {
            "verdict": verdict.get("verdict"), "failed_checks": verdict.get("failed_checks"),
            "issues": verdict.get("issues"), "alignment": verdict.get("alignment"),
            "not_evaluated": verdict.get("not_evaluated"),
        },
        "model_evaluator": None if model_verdict is None else {
            "verdict": model_verdict.get("verdict"), "failed_checks": model_verdict.get("failed_checks"),
            "issues": model_verdict.get("issues"),
        },
        "error_class": error_class, "error_detail": detail,
        "model_path": {
            "ran": model_step is not None and not model_step["timeout"],
            "timed_out": bool(model_step and model_step["timeout"]),
            "model": (model_step or {}).get("result", {}).get("model") if (model_step or {}).get("result") else None,
            "plan_produced": bool((model_step or {}).get("result", {}).get("plan")) if (model_step or {}).get("result") else False,
            "evidence": (model_step or {}).get("result"),
            "note": "model-plan komutu okuma zincirinin kanıtını gönderir; çağrının kendisi ve görüntü "
                    "durumu `model/inference-log*.json` içinde, adapter sınırında kayıtlıdır",
        },
        "product_input_leakage": "none: the run received the drawing file only "
                                 "(no STEP, labels, parameters, part id or verified plan)",
        "user_interventions": 0,
        "evidence": {"product_steps": str(steps_path),
                     "verdict": str(workdir / "evaluator-verdict.json") if verdict else None,
                     "inference_logs": [str(path) for path in sorted(product.glob("inference-log*.json"))],
                     "model_verdict": str(workdir / "model-verdict.json") if model_verdict else None},
    }


def _summary(rows: list[dict]) -> dict:
    """Denominators that do not hide the work, and each arm's own.

    Four of the five runs are different parts, so `attempt_count` (runs) and `unique_part_count`
    (distinct parts) are separate numbers — "5 attempts, 4 parts" — and every rate is given beside the
    denominator it came from. `inference_log_missing` counts rows where the product wrote no call
    evidence: those are unmeasured, not model-free.
    """
    model_arms = [(row.get("arms") or {}).get("model") or {} for row in rows]
    product_arms = [(row.get("arms") or {}).get("product") or {} for row in rows]
    return {
        "parts": len(rows),
        "attempt_count": len(rows),
        "unique_part_count": len({row["part_id"] for row in rows}),
        "by_error_class": {name: sum(1 for row in rows if row["error_class"] == name)
                           for name in ERROR_CLASSES},
        "evaluated": sum(1 for row in rows if row["evaluator"]),
        "product_pass": sum(1 for row in rows if (row["evaluator"] or {}).get("verdict") == "pass"),
        "product_wrong_part": sum(1 for row in rows
                                 if (row["evaluator"] or {}).get("verdict") == "fail"),
        "refused_before_cad": sum(1 for row in rows if not row["product_step"] and row["product_refusals"]),
        "arms": {
            "product": {
                "ran": sum(1 for row in rows if row.get("command_started")),
                "inference_called": sum(1 for row in rows if row.get("inference_called") is True),
                "inference_log_missing": sum(1 for row in rows if row.get("inference_called") is None),
                "image_attached": sum(1 for row in rows if row.get("image_attached") is True),
                "unfinished_calls": sum(int(arm.get("unfinished") or 0) for arm in product_arms),
                "plan_produced": sum(1 for row in rows if row.get("plan_produced")),
                "records_produced": sum(1 for row in rows if row.get("records_produced")),
                "program_produced": sum(1 for row in rows if row.get("program_produced")),
                "step_built": sum(1 for row in rows if row.get("step_built")),
                "evaluated": sum(1 for row in rows if row.get("evaluated")),
            },
            "model": {
                "ran": sum(1 for arm in model_arms if arm.get("ran")),
                "inference_called": sum(1 for arm in model_arms if arm.get("inference_called") is True),
                "image_attached": sum(1 for arm in model_arms if arm.get("image_attached") is True),
                "unfinished_calls": sum(int(arm.get("unfinished") or 0) for arm in model_arms),
                "plan_produced": sum(1 for arm in model_arms if arm.get("plan_produced")),
                "step_built": sum(1 for arm in model_arms if arm.get("step_built")),
                "evaluated": sum(1 for arm in model_arms if arm.get("evaluated")),
                "timed_out": sum(1 for arm in model_arms if arm.get("timed_out")),
            },
        },
    }


def _started_but_never_finished(steps: list[dict]) -> list[str]:
    """Adımların hangisi hiç başlamadı: bütçe bitince adım başlatılmaz ve bu yazılır."""
    return [str(step["not_started_reason"]) for step in steps if step.get("not_started_reason")]


def _fields_from_disk(workdir: Path, row: dict, steps: list[dict], produced: list, model_step,
                      verdict: dict | None, metrics, corpus: Path) -> dict:
    """The row's own six fields, rebuilt from the run's own files.

    The run already wrote its per-step call records, plan, records and STEP; rebuilding the fields from
    those files keeps `--reuse` honest instead of filling the fields with a default that looks like a
    measurement.
    """
    product_log = _merged(_step_logs(workdir, "product"))
    model_log = (model_step or {}).get("inference") or _merged(_step_logs(workdir, "model"))
    model_built = (model_step or {}).get("built") or {}
    model_verdict = None
    if model_built.get("step"):
        truth = metrics.extract(str(corpus / row["part_id"] / "part.step"))
        model_verdict = metrics.compare(metrics.extract(model_built["step"]), truth)
    product = workdir / "product"
    product_trace = _trace([
        ("command_started", bool(steps), f"{len(steps)} adım", bool(steps)),
        ("plan_produced", (product / "plan.json").exists() or (product / "records.json").exists(),
         "plan.json" if (product / "plan.json").exists() else "records.json", bool(steps)),
        ("step_built", bool(produced), produced[0].name if produced else "yok",
         (product / "plan.json").exists() or (product / "records.json").exists()),
        ("evaluated", verdict is not None, "" if verdict else "değerlendirilecek STEP yok",
         bool(produced)),
        ("verdict_pass", bool(verdict and verdict.get("verdict") == "pass"),
         "" if verdict is None else str(verdict.get("verdict")), verdict is not None),
    ])
    return {
        "command_started": bool(steps),
        "inference_called": None if product_log is None else bool(product_log.get("inference_called")),
        "image_attached": None if product_log is None else bool(product_log.get("image_attached")),
        "unfinished": None if product_log is None else int(product_log.get("unfinished", 0)),
        "plan_produced": (product / "plan.json").exists(),
        "records_produced": (product / "records.json").exists(),
        "program_produced": bool(sorted(product.glob("*.py"))),
        "step_built": bool(produced),
        "evaluated": verdict is not None,
        "not_started": _started_but_never_finished(steps),
        "inference_logs": [str(path) for path in sorted(product.glob("inference-log*.json"))],
        "product_trace": product_trace,
        "arms": _arms(product_log, model_log, model_step, model_built, model_verdict,
                      row["kind"] == "raster", product_trace),
        "model_evaluator": None if model_verdict is None else {
            "verdict": model_verdict.get("verdict"), "failed_checks": model_verdict.get("failed_checks"),
            "issues": model_verdict.get("issues"),
        },
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
        **_fields_from_disk(workdir, row, steps, produced, model_step, verdict, metrics, corpus),
    }


PASS_VERDICT, FAIL_VERDICT = "pass", "fail"

# H04'ün dört eğitim kararı: karar, satır sınıflamasından ayrı bir belge olarak verilir.
TRAINING_DECISIONS = ("train_targeted", "fix_rules_first", "need_data", "training_not_justified")

# `train_targeted` en az bu kadar ayrı parçada etiketlenebilir hata ister (plan §H04).
TRAIN_TARGETED_MIN_PARTS = 3

# Bir hata "model şeması" dışındaki katmanlarda ise ilk iş kural/okuma/CAD onarımıdır; kural, CAD ve
# değerlendirici hatası için model eğitilmez (plan §H04).
MODEL_LAYER = "model şeması"

# Karar belgesinin bulut kapıları: bu sürücü hiçbirini ölçmez, o yüzden hiçbiri `verified` yazılamaz.
TRAINING_GATES = ("targeted_training_justified", "dataset_and_script_ready",
                  "m1_base_inference_verified", "export_path_checked", "current_rate_recorded",
                  "shutdown_mechanism_verified", "cost_reserve_available")


def _row_classification(rows: list[dict], run_id: str) -> dict:
    """Satır başına sınıflama: bu kayıt eğitim karışımına hangi rolle girebilir.

    Kural kanıta bağlıdır ve bilinmeyeni uydurmaz:

    * `positive` — kanonik çıktı var ve bağımsız karar gerçekten `pass`;
    * `negative` — kanonik çıktı var ve bağımsız karar gerçekten `fail`: yanlış çıktı yanlış olarak
      etiketlenir, doğru hedef yerine konmaz;
    * `unknown` — çıktı var ama karar yok ya da okunamıyor (`not_evaluated`, `error`, `null`): neyin
      öğretileceği bilinmiyor, bu satır `positive` sayılamaz (review4/U01'in karşı örneği);
    * `excluded` — öğrenilecek çıktı yok: ürün katı kurmadan reddetti ya da hiç çıktı vermedi.

    Model kolunun çıktısı ayrıca *çağrı kanıtı* ister: model derlenmiş bir plan üretmiş ama adapter
    kaydı çağrı göstermiyorsa çıktı modele atfedilemez.

    Bu bir satır sınıflamasıdır, eğitim gerekliliği kararı **değildir**: karar `_training_decision`
    içinde, ayrı belge olarak ve yalnız bu sınıflamanın kanıtıyla verilir.
    """

    def _bucket(*, has_output: bool, verdict, evidence_ok: bool, no_output_reason: str,
                no_evidence_reason: str) -> tuple[str, str]:
        if not has_output:
            return "excluded", no_output_reason
        if not evidence_ok:
            return "excluded", no_evidence_reason
        if verdict == PASS_VERDICT:
            return "positive", "kanonik çıktı + bağımsız `pass` kararı"
        if verdict == FAIL_VERDICT:
            return "negative", ("kanonik çıktı + bağımsız `fail` kararı: yanlış çıktı negatif hedef "
                                "olarak etiketlenir, doğru hedef sayılmaz")
        return "unknown", (f"bağımsız karar okunamadı ({verdict!r}): çıktının doğru olduğu "
                           "bilinmiyor, `positive` sayılamaz")

    entries = []
    for row in rows:
        product = (row.get("arms") or {}).get("product") or {}
        model = (row.get("arms") or {}).get("model") or {}
        product_use, product_reason = _bucket(
            has_output=bool(row.get("step_built")),
            verdict=(row.get("evaluator") or {}).get("verdict"), evidence_ok=True,
            no_output_reason=("ürün katı kurmadan reddetti: öğrenilecek çıktı yok"
                              if row.get("product_refusals")
                              else "ürün katı kurmadı: karşılaştırılacak çıktı yok"),
            no_evidence_reason="")
        model_use, model_reason = _bucket(
            has_output=bool(model.get("step_built")), verdict=model.get("verdict"),
            evidence_ok=bool(model.get("inference_called")),
            no_output_reason=(f"model kolundan öğrenilecek çıktı yok (çağrı: "
                              f"{model.get('inference_called')}, plan: {model.get('plan_produced')}, "
                              f"kurulan: {bool(model.get('step_built'))})"),
            no_evidence_reason="model çıktısı var ama adapter kaydı çağrı göstermiyor: çıktı modele "
                              "atfedilemez")
        shared = {"part_id": row["part_id"], "input_file": row["input_file"],
                  "input_sha256": row["input_sha256"], "reference_sha256": row["reference_sha256"],
                  "input_leakage": row["product_input_leakage"],
                  "not_started": row.get("not_started") or []}
        entries.append({**shared, "arm": product.get("arm") or "product",
                        "usable_as": product_use, "reason": product_reason,
                        "classified_verdict": (row.get("evaluator") or {}).get("verdict"),
                        "produced_step": row["product_step"]})
        entries.append({**shared, "arm": "model", "usable_as": model_use, "reason": model_reason,
                        "classified_verdict": model.get("verdict"),
                        # model kolunun çıktısı: model-verdict.json + satırdaki model_path
                        "produced_step": None})
    counts = {name: sum(1 for entry in entries if entry["usable_as"] == name)
              for name in ("positive", "negative", "excluded", "unknown")}
    return {"schema": "drawingto3d.lab.row-classification/1", "run_id": run_id, "counts": counts,
            "rule": "Yalnız gerçek `pass` positive, gerçek `fail` negative; karar yok/okunamıyorsa "
                    "`unknown`, öğrenilecek çıktı yoksa `excluded`. Negatif çıktı doğru hedef sayılmaz; "
                    "model çıktısı ayrıca çağrı kanıtı ister.",
            "entries": entries}


def _training_decision(rows: list[dict], classification: dict, run_id: str) -> dict:
    """Eğitim doğru müdahale mi — satır sınıflamasından ayrı, dört karardan biri.

    `train_targeted` en az `TRAIN_TARGETED_MIN_PARTS` ayrı parçada *okunabilir ve doğru
    etiketlenebilir* hata ister: o parçalarda model kolu gerçekten çalışmış, bir çıktı üretmiş ve
    bağımsız karar `pass`/`fail` olarak okunabilmiş olmalı. Bu eşiğin altında — ve hata kural, okuma,
    CAD ya da değerlendirici katmanındaysa — ilk iş o katmanı onarmaktır (`fix_rules_first`): kural ve
    CAD hatası için model eğitilmez. Hiç ölçülmüş satır yoksa `need_data`, okuma zincirinde öğrenilecek
    hata kalmadıysa `training_not_justified`.
    """
    entries = classification.get("entries") or []
    labelable_parts = sorted({entry["part_id"] for entry in entries
                              if entry["usable_as"] in ("positive", "negative")})
    model_labelable_parts = sorted({entry["part_id"] for entry in entries
                                    if entry["arm"] == "model"
                                    and entry["usable_as"] in ("positive", "negative")})
    product_labelable_parts = sorted({entry["part_id"] for entry in entries
                                      if entry["arm"] != "model"
                                      and entry["usable_as"] in ("positive", "negative")})
    layers: dict[str, int] = {}
    for row in rows:
        layers[row["error_class"]] = layers.get(row["error_class"], 0) + 1
    rule_layers = {name: count for name, count in layers.items() if name != MODEL_LAYER and count}
    # Kök hata, adım adım izden okunur: her kolun gerçekten çalışıp düşen son adımı.
    stopping_points = [{"part_id": row["part_id"], "arm": arm,
                        "terminal_failure": (row.get("arms") or {}).get(arm, {}).get("trace", {}).get(
                            "terminal_failure"),
                        "first_divergence": (row.get("arms") or {}).get(arm, {}).get("trace", {}).get(
                            "first_divergence")}
                       for row in rows for arm in ("product", "model")]

    if not rows:
        decision, reason = "need_data", "ölçülmüş satır yok: karar verecek kanıt yok"
    elif len(labelable_parts) >= TRAIN_TARGETED_MIN_PARTS:
        decision = "train_targeted"
        reason = (f"{len(labelable_parts)} ayrı parçada bağımsız kararı okunabilen çıktı var "
                  f"(model kolu: {len(model_labelable_parts)}, ürün kolu: "
                  f"{len(product_labelable_parts)}): {', '.join(labelable_parts)}")
    elif rule_layers:
        decision = "fix_rules_first"
        reason = ("hatalar okuma/kural/CAD katmanında (" +
                  ", ".join(f"{name}: {count}" for name, count in sorted(rule_layers.items())) +
                  "); kural, CAD ya da değerlendirici hatası için model eğitilmez")
    elif layers.get(MODEL_LAYER):
        decision = "need_data"
        reason = (f"hata yalnız `{MODEL_LAYER}` katmanında ve etiketlenebilir çıktı "
                  f"{len(labelable_parts)}/{TRAIN_TARGETED_MIN_PARTS} parçada: dar görev için "
                  "yeterli doğru etiketli örnek yok")
    else:
        decision = "training_not_justified"
        reason = "okuma zincirinde öğrenilecek hata görünmüyor: model eğitimi gerekçesiz"

    return {
        "schema": "drawingto3d.lab.training-decision/1", "run_id": run_id,
        "decision": decision, "reason": reason,
        "allowed_decisions": list(TRAINING_DECISIONS),
        "narrow_task": None,
        "root_error": {"error_layers": layers, "stopping_points": stopping_points},
        "label_origin": {
            "drawings": "korpustaki çizim dosyaları (ürün girdisi)",
            "labels": "korpustaki referans STEP + bağımsız evaluator kararı (eval/feature_metrics.py)",
            "verified_for_training": False,
            "note": "v2 parçaları development_exposed'dır: bağımsız gizli test değildir ve çizim→özellik "
                    "etiketleri bağımsız doğrulanmış sayılmaz",
        },
        "threshold_evidence": {
            "min_parts_for_targeted_training": TRAIN_TARGETED_MIN_PARTS,
            "labelable_parts": labelable_parts, "model_labelable_parts": model_labelable_parts,
            "product_labelable_parts": product_labelable_parts,
            "classification_counts": classification.get("counts"),
        },
        "gates": {name: "unverified" for name in TRAINING_GATES},
        "gates_note": "Bu sürücü bulut kapılarını ölçmez: hiçbiri doğrulanmış sayılmaz ve karar tek "
                      "başına ücretli kaynak açmaz.",
        "classification_schema": classification.get("schema"),
        "decided_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _decision_documents(rows: list[dict], run_id: str, decision_out: Path) -> tuple[dict, dict]:
    """Satır sınıflaması + ondan türeyen eğitim kararı; karar belgesi diske yazılır.

    İkisi ayrı belgedir: sınıflama "bu kayıt hangi rolle kullanılabilir"i satır satır söyler, karar
    "eğitim doğru müdahale mi"yi kanıt sayısıyla verir. Aynı sözlüğü iki iş için kullanmak, ölçülmemiş
    bir satırı eğitim hedefi gibi göstermenin yoluydu (review4/U01).
    """
    classification = _row_classification(rows, run_id)
    decision = _training_decision(rows, classification, run_id)
    write_json(decision_out, decision)
    return classification, decision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "out/lab/data/v2")
    parser.add_argument("--out", type=Path, default=ROOT / "out/lab/baseline")
    parser.add_argument("--results", type=Path,
                        default=ROOT / "out/lab/review-checkpoint/baseline-results.json")
    parser.add_argument("--decision-out", type=Path, default=ROOT / "out/lab/training-decision.json",
                        help="satır sınıflamasından türeyen eğitim kararı belgesi (H04 artefaktı)")
    parser.add_argument("--part", action="append", default=None,
                        help="yalnız bu parçayı koş (tekrarlanabilir)")
    parser.add_argument("--reuse", action="store_true",
                        help="ürün/model çağırmadan, diskteki koşulardan sonuç dosyasını yeniden kur")
    parser.add_argument("--no-model", action="store_true",
                        help="yerel model adımını atla (ürün yolu ve evaluator yine koşar)")
    args = parser.parse_args()
    # Every path this driver writes is also read back by its own subprocesses with a working directory of
    # their own, so a relative --out is re-prefixed onto the run's workdir and the product is handed a
    # drawing that is not there. Measured: `--out out/lab/...` produced
    # `FileNotFoundError: <run>/<part>/out/lab/.../input/drawing.pdf` for all four parts, and the run read
    # as four CAD failures that never reached the CAD at all. Resolved here, once, at the boundary.
    args.corpus = args.corpus.resolve()
    args.out = args.out.resolve()
    args.results = args.results.resolve()
    args.decision_out = args.decision_out.resolve()

    metrics = _load_metrics()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
        classification, decision = _decision_documents(rows, run_id, args.decision_out)
        payload = {
            "schema": BASELINE_SCHEMA, "lab_version": LAB_VERSION, "run_id": run_id,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "mode": "reuse (her koşu ayrı kayıt; raster okuma koşudan koşuya değişiyor)",
            "corpus": str(args.corpus),
            "corpus_manifest_sha256": sha256_file(args.corpus / "manifest.json"),
            "entry_boundary": "product ← drawing only; evaluator ← produced STEP vs corpus reference",
            "error_classes": list(ERROR_CLASSES),
            "runs": runs,
            "summary": _summary(rows),
            "row_classification": classification,
            "training_decision": decision,
            "training_decision_doc": str(args.decision_out),
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

    run_budget = Budget(RUN_BUDGET_SECONDS, label=f"run {run_id}")
    # One heavy job at a time: the lab's own slot (`state.acquire_heavy`, H02) is taken for the whole
    # run, so a baseline started by hand and one started by the lab queue cannot run two model arms at
    # once on the same box. The token is released in `finally`, even when a part raises.
    lab = Lab(ROOT / "out/lab")
    claim = lab.acquire_heavy(f"baseline {run_id}")
    token = claim.get("token") if isinstance(claim, dict) else None
    if isinstance(claim, dict) and claim.get("acquired") is False:
        print(json.dumps({"heavy_slot": "busy", "claim": claim}, ensure_ascii=False, indent=2))
        return
    rows = []
    try:
        for row in PARTS:
            if args.part and row["part_id"] not in args.part:
                continue
            print(f"--- {row['part_id']} ({row['kind']})")
            record = run_part(row, args.corpus, args.out / run_id, metrics,
                              with_model=not args.no_model, run_budget=run_budget)
            rows.append(record)
            print(f"    error_class={record['error_class']} "
                  f"evaluator={(record['evaluator'] or {}).get('verdict')} "
                  f"refusals={record['product_refusals']} "
                  f"kalan={run_budget.remaining():.0f}s")
    finally:
        lab.release_heavy(token)

    classification, decision = _decision_documents(rows, run_id, args.decision_out)
    payload = {
        "schema": BASELINE_SCHEMA, "lab_version": LAB_VERSION, "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "corpus": str(args.corpus), "corpus_manifest_sha256": sha256_file(args.corpus / "manifest.json"),
        "entry_boundary": "product ← drawing only; evaluator ← produced STEP vs corpus reference",
        "error_classes": list(ERROR_CLASSES),
        "budget": {"run": run_budget.as_record(), "case_seconds": CASE_BUDGET_SECONDS,
                   "note": "Vaka bütçesi (600 s) adımlar arasında paylaşılır; süresi biten adım "
                           "başlatılmaz ve satırda `not_started` olarak yazılır. Koşu bütçesi 7200 s."},
        "parts": rows,
        "summary": _summary(rows),
        "row_classification": classification,
        "training_decision": decision,
        "training_decision_doc": str(args.decision_out),
        "splits": {
            "measured": [row["part_id"] for row in rows],
            "development_exposed": [row["part_id"] for row in rows],
            "note": "Bu koşuda ölçülen parçalar geliştirme sırasında görüldü: `held_out` bir aile adıdır, "
                    "bağımsız gizli test değildir (üretici tarafı: eval/lab_corpus.py, splits/2). Bağımsız "
                    "test yeni parça aileleri ister; aynı `plate_holes` şablonunun parametreleri değişmiş "
                    "hâli yeni aile sayılmaz. Korpus dosyaları bu dilimde değiştirilmedi.",
        },
        "arms": {
            "product_pipelines": sorted({(row.get("arms") or {}).get("product", {}).get("pipeline", "")
                                         for row in rows}),
            "note": "İki kol aynı girdi dosyasıyla koşar; hangi kolun hangi boru hattını çalıştırdığı satır "
                    "satır `arms` alanında, model kimliği ve ayarı ise adapter sınırındaki çağrı kaydında "
                    "yazılıdır. Raster kol serbest kod üretir ve yapılandırılmış ürün yolu gibi "
                    "adlandırılmaz.",
        },
        "model_path": {
            "runs": [{"part_id": row["part_id"], **(row.get("model_path") or {})} for row in rows],
            "comparison": "product: `propose` (vektör kural yolu) ya da `read`+`build` (raster serbest kod "
                          "kolu; kural değil model kullanır); model: aynı dosyaya `model-plan`. Model-plan "
                          "okuma zincirinin kanıtını gönderir; görüntünün gidip gitmediği iddia değil, "
                          "`model/inference-log*.json` kaydıdır. Zincir reddederse model hiç çağrılmaz.",
        },
    }
    write_json(args.results, payload)
    print(json.dumps({"results": str(args.results), "summary": payload["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
