"""PLAN.md section 7: the pre-training measurement.

Four conditions, measured apart so the error has an owner (PLAN section 18B):

  reading        drawing -> cited dimensions and relations, against an independent label
  chain          drawing -> reader -> plan -> CAD -> drawing check   (what the user will see)
  relations      verified relations + drawing -> the same model -> plan
  verified_plan  a hand-verified GeneralPlan -> the same CAD compiler

Which layer is wrong is then a number, not an opinion: `reading` isolates perception, `relations`
holds perception fixed and isolates operation planning, `verified_plan` holds planning fixed and
isolates the compiler and the validator, and `chain` is the result the user actually gets.

Rules this file obeys, because a measurement that breaks them measures something else:

* A reference STEP and a correct plan never reach the model prompt. The relation tables under
  `eval/relations/` are hand-verified *inputs* for the diagnosis condition only, and the report
  says so wherever it quotes them.
* Every run writes one machine-readable record: code revision and local diff, data manifest summary,
  model/weight summary, prompt and schema version, sampling, quantisation, image settings, context,
  output limit, timeout, candidate counts, stage times, the memory measurement method and its result,
  and the output status of every case.
* A model that is not installed is reported as a missing dependency. No result is written for a run
  that did not happen.

    PYTHONPATH=src .venv/bin/python eval/model_baseline.py --no-model
    PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen2.5vl:3b --conditions relations
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import scale as sheet_scale  # noqa: E402
from drawingto3d.cadrun import CadFailure  # noqa: E402
from drawingto3d.errors import UnavailableModel  # noqa: E402
from drawingto3d.general import GeneralPlan, build_general  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.llama import ChatSettings, OllamaChat, installed_models  # noqa: E402
from drawingto3d.planner import (  # noqa: E402
    EVIDENCE_VERSION,
    NAME_ADAPTER,
    PROMPT_VERSION,
    PROMPT_VERSION_SPLIT,
    PlanCandidate,
    chain_evidence,
    measurements_evidence,
    propose_plan,
    propose_plan_split,
)
from drawingto3d.reader import TesseractReader, VisionReader  # noqa: E402
from drawingto3d.perceive import perceive  # noqa: E402
from drawingto3d.proposal import propose_general, read_sheet  # noqa: E402
from drawingto3d.bind import bind_page  # noqa: E402
from drawingto3d.meaning import meaning_page  # noqa: E402

CASES_FILE = ROOT / "eval" / "cases.json"
RELATIONS_DIR = ROOT / "eval" / "relations"
SCHEMA_VERSION = "GeneralPlan v1"
ALL_CONDITIONS = ("reading", "chain", "chain_model", "relations", "verified_plan")


# --- the environment a run has to be reproducible against ----------------------------


def _git(*arguments: str) -> str:
    try:
        done = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip()


def _command(*arguments: str) -> str:
    try:
        done = subprocess.run(list(arguments), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip()


def code_record() -> dict:
    """Revision, local changes and the interpreter the numbers came from."""
    status = _git("status", "--short")
    return {
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
        "dirty_files": status.splitlines(),
        "diff_stat": _git("diff", "--stat"),
        "file_sha256": {str(path.relative_to(ROOT)): _sha256(path)
                        for path in sorted(set(ROOT.glob("src/**/*.py"))
                                           | set(ROOT.glob("eval/*.py"))
                                           | {ROOT / "pyproject.toml"})},
        "python": platform.python_version(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": _command("sysctl", "-n", "machdep.cpu.brand_string"),
        "memory_bytes": int(_command("sysctl", "-n", "hw.memsize") or 0),
        "tesseract": (_command("tesseract", "--version").splitlines() or [""])[0],
        "cadquery": (ROOT / ".venv-cad" / "bin" / "python").is_file(),
    }


def manifest_record(cases: list[dict]) -> dict:
    splits: dict[str, int] = {}
    groups: dict[str, list[str]] = {}
    for case in cases:
        splits[case["split"]] = splits.get(case["split"], 0) + 1
        groups.setdefault(case["part_group"], []).append(case["id"])
    return {
        "file": str(CASES_FILE.relative_to(ROOT)),
        "sha256": _sha256(CASES_FILE),
        "drawing_sha256": {case["id"]: _sha256(ROOT / case["drawing"])
                           for case in cases if (ROOT / case["drawing"]).is_file()},
        "cases": len(cases),
        "split_counts": splits,
        "part_groups": groups,
        "note": (
            "A part group is one part: several source files of the same part are one sample. "
            "pilot >= 10 and hidden >= 20 real parts stay the user's call and are empty here."
        ),
    }


# --- resource sampling: method and result --------------------------------------------


class ResourceSampler:
    """Swap, free memory and the model server's resident size while the run is going.

    The method is named in the record because it is half the number: these are `sysctl vm.swapusage`
    and `vm_stat` pages plus `ps` RSS of the Ollama process, sampled by a thread in this process.
    Disk size of the weights is not RAM and is not counted here.
    """

    VERSION = 2
    METHOD = "vm.swapusage used field + vm_stat reported page size; ps Ollama RSS; MiB; 2 s samples"
    INTERVAL = 2.0

    def __init__(self) -> None:
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.samples.append(self._sample())
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.samples.append(self._sample())

    def _loop(self) -> None:
        while not self._stop.wait(self.INTERVAL):
            self.samples.append(self._sample())

    def _sample(self) -> dict:
        swap_text = _command("sysctl", "-n", "vm.swapusage")
        vm_text = _command("vm_stat")
        return {
            "seconds": round(time.time(), 2),
            "swap_used_mb": _swap_used_mb(swap_text),
            "pages_free_mb": _vm_stat("Pages free", vm_text),
            "pages_compressed_mb": _vm_stat("Pages occupied by compressor", vm_text),
            "ollama_rss_mb": _ollama_rss_mb(),
            "raw_swapusage": swap_text,
            "raw_vm_stat": vm_text,
        }

    def record(self) -> dict:
        usable = [sample for sample in self.samples if sample["swap_used_mb"] is not None]
        rss = [sample["ollama_rss_mb"] for sample in self.samples if sample["ollama_rss_mb"]]
        free = [sample["pages_free_mb"] for sample in self.samples if sample["pages_free_mb"] is not None]
        compressed = [sample["pages_compressed_mb"] for sample in self.samples
                      if sample["pages_compressed_mb"] is not None]
        first, last = (usable[0], usable[-1]) if usable else (None, None)
        return {
            "measurement_version": self.VERSION,
            "unit": "MiB",
            "method": self.METHOD,
            "samples": len(self.samples),
            "raw_samples": list(self.samples),
            "interval_s": self.INTERVAL,
            "swap_used_mb_start": None if first is None else first["swap_used_mb"],
            "swap_used_mb_end": None if last is None else last["swap_used_mb"],
            "swap_used_mb_delta": None if first is None or last is None else round(last["swap_used_mb"] - first["swap_used_mb"], 1),
            "swap_used_mb_peak": max((sample["swap_used_mb"] for sample in usable), default=None),
            "pages_free_mb_min": min(free) if free else None,
            "pages_compressed_mb_peak": max(compressed) if compressed else None,
            "ollama_rss_mb_peak": max(rss) if rss else None,
            "note": "System swap/page counts include other apps. RSS is not total GPU/unified memory. "
                    "Unavailable measurements are null; legacy *_mb keys use MiB in version 2.",
        }


def _swap_used_mb(text: str | None = None) -> float | None:
    text = _command("sysctl", "-n", "vm.swapusage") if text is None else text
    match = re.search(r"\bused\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT])\b", text)
    if not match:
        return None
    return round(float(match[1]) * {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024**2}[match[2]], 3)


def _vm_stat(label: str, text: str | None = None) -> float | None:
    text = _command("vm_stat") if text is None else text
    page_size = re.search(r"page size of (\d+) bytes", text)
    if not page_size:
        return None
    for line in text.splitlines():
        match = re.fullmatch(re.escape(label) + r":\s*(\d+)\.?\s*", line)
        if match:
            return round(int(match[1]) * int(page_size[1]) / 1024**2, 3)
    return None


def _ollama_rss_mb() -> float | None:
    """Resident size of every process whose command line mentions Ollama.

    The server process on its own is not the model: the weights live in a runner child, so summing
    every matching process is the number worth quoting. Still not counted: the size of the weights
    on disk.
    """
    listing = _command("ps", "-Ao", "rss=,command=")
    total = 0
    seen = False
    for line in listing.splitlines():
        stripped = line.strip()
        if "ollama" not in stripped.lower():
            continue
        head, _, _rest = stripped.partition(" ")
        if head.isdigit():
            total += int(head)
            seen = True
    return round(total / 1024, 1) if seen else None


# --- reading and building measurements -----------------------------------------------


def reading_metrics(case: dict, spans, seconds: float) -> dict:
    """Coverage, missing and noise against the numbers a human reads on the sheet."""
    printed = [float(value) for value in case["printed"]]
    callouts = [_squash(item) for item in case.get("callouts") or []]
    valued = [span for span in spans if span.value is not None]
    covers: list[float] = []
    noise: list[dict] = []
    named: list[str] = []
    for span in valued:
        hit = next((value for value in printed if _same(span.value, value)), None)
        if hit is not None:
            if hit not in covers:
                covers.append(hit)
            continue
        if any(callout.startswith(_squash(span.text)) for callout in callouts):
            named.append(span.text)
            continue
        noise.append({"text": span.text, "value": span.value, "unit": span.unit, "kind": span.kind.value})
    calibration, suspect = sheet_scale.audit(valued)
    return {
        "spans": len(spans),
        "valued_spans": len(valued),
        "refused": len(spans) - len(valued),
        "printed": len(printed),
        "covers": sorted(covers),
        "covered": len(covers),
        "missing": sorted(set(printed) - set(covers)),
        "noise": noise,
        "callouts_named": named,
        "px_per_mm": None if calibration is None else round(calibration.px_per_mm, 4),
        "px_per_mm_spread": None if calibration is None else round(calibration.spread, 5),
        "suspect": suspect,
        "seconds": round(seconds, 2),
    }


def drawing_check(plan_facts: dict, meanings, case: dict) -> dict:
    """Does the solid the plan built measure what the sheet's own readings say?

    This is the seed of the section 3D check: the *plan* audit is what `build_general` already does,
    and this second question is asked of the drawing. A diameter or radius claim the reading confirmed
    has to be a cylinder in the built solid within `max(1 %, 0.5 mm)`, and a distance claim between two
    circle centres has to be the distance between two cylinders' axes. Absent evidence is not a pass:
    an unchecked claim is reported as unchecked.
    """
    cylinders = list(plan_facts.get("cylinders_axis") or [])
    radii = [item[0] for item in cylinders]
    checks: list[dict] = []
    for span in getattr(meanings, "spans", []):
        claim = span.claim
        if claim is None or span.resolution != "confirmed":
            continue
        printed = span.printed_mm
        if printed is None:
            continue
        if claim.form in ("diameter", "radius"):
            wanted = printed / 2 if claim.form == "diameter" else printed
            matched = [radius for radius in radii if abs(radius - wanted) <= max(0.01 * wanted, 0.5)]
            checks.append({
                "span_id": span.span_id,
                "text": span.text,
                "claim": claim.form,
                "wanted_radius_mm": round(wanted, 3),
                "drawn_radius_mm": round(claim.drawn_mm / 2 if claim.form == "diameter" else claim.drawn_mm, 3),
                "ok": bool(matched),
                "matched_radii": sorted({round(radius, 3) for radius in matched}),
            })
            continue
        if claim.form == "distance" and len(claim.points) == 2:
            if any(point.kind != "circle-centre" for point in claim.points):
                continue
            wanted = printed
            best = None
            for one, other in _pairs(cylinders):
                gap = ((one[1] - other[1]) ** 2 + (one[2] - other[2]) ** 2) ** 0.5
                if best is None or abs(gap - wanted) < abs(best - wanted):
                    best = gap
            if best is None:
                continue
            checks.append({
                "span_id": span.span_id,
                "text": span.text,
                "claim": claim.form,
                "wanted_mm": round(wanted, 3),
                "drawn_mm": round(claim.drawn_mm, 3),
                "nearest_axis_gap_mm": round(best, 3),
                "ok": abs(best - wanted) <= max(0.01 * wanted, 0.5),
            })
    return {
        "checked_claims": len(checks),
        "checks": checks,
        "solid_size_mm": [round(value, 3) for value in plan_facts.get("size") or []],
        "solid_radii_mm": sorted({round(radius, 3) for radius in radii}),
        "ok": all(item["ok"] for item in checks) if checks else None,
        "scope": "drawing readings against the built solid; a claim the reading left unresolved is not checked here",
    }


def _pairs(items: list) -> list[tuple]:
    out = []
    for index, one in enumerate(items):
        for other in items[index + 1:]:
            out.append((one, other))
    return out


def _squash(text: str) -> str:
    import re

    return re.sub(r"[^0-9a-z]", "", text.lower())


def _same(value, printed: float) -> bool:
    if value is None:
        return False
    return abs(float(value) - printed) <= max(1e-6, 0.001 * abs(printed))


# --- the four conditions -------------------------------------------------------------


def condition_reading(case: dict, folder: Path, chat: OllamaChat | None, timeout: float) -> dict:
    """Perception on its own: the cheap CV path, the chain's binding, and the model's ceiling."""
    sheet = ROOT / case["drawing"]
    row: dict = {"case": case["id"], "condition": "reading", "stages": {}}
    started = time.time()

    page = load_page(sheet)
    start = time.time()
    _primitives, spans = perceive(page, reader=None)
    floor = reading_metrics(case, spans, time.time() - start)
    row["stages"]["ocr_floor"] = floor

    if chat is not None:
        start = time.time()
        _model_primitives, model_spans = perceive(page, reader=VisionReader(vision=_ChatVision(chat)))
        row["stages"]["model_ceiling"] = reading_metrics(case, model_spans, time.time() - start)

    try:
        start = time.time()
        bindings = bind_page(sheet)
        statuses: dict[str, int] = {}
        for span in bindings.spans:
            statuses[span.status] = statuses.get(span.status, 0) + 1
        row["stages"]["binding"] = {
            "spans": len(bindings.spans),
            "status": statuses,
            "sheet_px_per_mm": bindings.sheet_px_per_mm,
            "seconds": round(time.time() - start, 2),
        }
    except ValueError as exc:
        row["stages"]["binding"] = {"error": str(exc)}
    try:
        start = time.time()
        meanings = meaning_page(sheet)
        resolutions: dict[str, int] = {}
        forms: dict[str, int] = {}
        for span in meanings.spans:
            resolutions[span.resolution] = resolutions.get(span.resolution, 0) + 1
            forms[span.form] = forms.get(span.form, 0) + 1
        row["stages"]["meaning"] = {
            "spans": len(meanings.spans),
            "resolution": resolutions,
            "forms": forms,
            "seconds": round(time.time() - start, 2),
        }
    except ValueError as exc:
        row["stages"]["meaning"] = {"error": str(exc)}

    row["seconds"] = round(time.time() - started, 2)
    row["status"], row["error_class"], row["reason"] = _reading_verdict(row)
    (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


def _reading_verdict(row: dict) -> tuple[str, str, str]:
    floor = row["stages"].get("ocr_floor") or {}
    applied = row["stages"].get("model_ceiling") or floor
    printed = applied.get("printed") or 0
    covered = applied.get("covered") or 0
    binding = row["stages"].get("binding") or {}
    if "error" in binding:
        return "failed", "reading", f"bağlama katmanı okumadı: {binding['error']}"
    if not binding.get("sheet_px_per_mm"):
        return "refused", "reading", "pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik)"
    if covered < printed:
        missing = ", ".join(f"{value:g}" for value in applied.get("missing") or [])
        return "partial", "reading", f"basılı {printed} sayının {covered} tanesi bulundu; eksik: {missing}"
    noise = applied.get("noise") or []
    if noise:
        return "partial", "reading", f"kapsam tam, ama {len(noise)} yanlış okuma var: " + \
            ", ".join(f"{item['text']}->{item['value']:g}" for item in noise[:5])
    return "ok", "ok", "basılı sayıların tamamı bulundu, yanlış okuma yok"


def condition_chain(case: dict, folder: Path, timeout: float) -> dict:
    """The real chain: drawing -> reading -> plan -> CAD -> drawing check."""
    sheet = ROOT / case["drawing"]
    row: dict = {"case": case["id"], "condition": "chain", "stages": {}}
    started = time.time()
    start = time.time()
    try:
        proposal = propose_general(sheet)
    except ValueError as exc:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "reading", "reason": f"okuma zinciri çalışmadı: {exc}"})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row
    row["stages"]["propose"] = {
        "status": proposal.status,
        "readings": len(proposal.readings),
        "refusals": proposal.refusals,
        "measurements": proposal.measurements,
        "seconds": round(time.time() - start, 2),
    }
    (folder / f"{case['id']}-proposal.json").write_text(
        proposal.model_dump_json(indent=2), encoding="utf-8"
    )
    if proposal.plan is None:
        row["seconds"] = round(time.time() - started, 2)
        row.update({
            "status": "refused",
            "error_class": "reading",
            "reason": "; ".join(proposal.refusals) or "öneri reddedildi",
        })
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    start = time.time()
    build_folder = folder / f"{case['id']}-build"
    try:
        step, _stl = build_general(proposal.plan, sheet, build_folder)
        facts = json.loads((build_folder / "geometry.json").read_text(encoding="utf-8"))
        audit = json.loads((build_folder / "plan-audit.json").read_text(encoding="utf-8"))
        row["stages"]["cad"] = {
            "ok": True,
            "step": str(step.relative_to(ROOT)),
            "seconds": round(time.time() - start, 2),
            "checks": audit.get("checks"),
            "tool_checks": audit.get("tool_checks"),
        }
    except (CadFailure, ValueError) as exc:
        row["stages"]["cad"] = {"ok": False, "error": str(exc)[:800], "seconds": round(time.time() - start, 2)}
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "cad", "reason": f"CAD kurulumu başarısız: {str(exc)[:200]}"})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    start = time.time()
    try:
        meanings = meaning_page(sheet)
        row["stages"]["drawing_check"] = {**drawing_check(facts, meanings, case),
                                          "seconds": round(time.time() - start, 2)}
    except ValueError as exc:
        row["stages"]["drawing_check"] = {"error": str(exc)}
    row["seconds"] = round(time.time() - started, 2)
    check = row["stages"]["drawing_check"]
    if check.get("checked_claims") and not check.get("ok"):
        failed = [item for item in check["checks"] if not item["ok"]]
        row.update({
            "status": "built_unverified",
            "error_class": "cad",
            "reason": "katı üretildi ama çizim kontrolü geçmedi: " + "; ".join(
                f"{item['text']} ({item['claim']}) -> {item.get('wanted_radius_mm', item.get('wanted_mm'))}"
                for item in failed
            ),
        })
        return row
    row.update({
        "status": "draft",
        "error_class": "ok",
        "reason": "plan önerildi, katı kuruldu, plan denetimi geçti"
        + ("" if check.get("checked_claims") else "; çizim kontrolü için doğrulanmış iddia yok"),
    })
    (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


def condition_chain_model(
    case: dict, folder: Path, chat: OllamaChat | None, timeout: float, model_info: dict | None,
    structured: bool = True, normalize_names: bool = False, split: bool = False,
) -> dict:
    """The product path: a real drawing read by the chain, planned by the model, built by the compiler.

    The evidence is neither hand-written (that is `relations`) nor produced by the rules-based
    proposal (that is `chain`): it is what `read_sheet` measured off this sheet, in the same block the
    planner is asked with, so `chain` and `chain_model` differ in the planner alone. The sheet's own
    reference part is opened only after a solid exists, by the drawing check at the end.
    """
    sheet = ROOT / case["drawing"]
    row: dict = {"case": case["id"], "condition": "chain_model", "stages": {}}
    started = time.time()
    start = time.time()
    try:
        reading = read_sheet(sheet)
    except ValueError as exc:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "reading", "reason": f"okuma zinciri çalışmadı: {exc}"})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row
    evidence = chain_evidence(reading)
    (folder / f"{case['id']}-chain_model-evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    row["stages"]["evidence"] = {
        "source": "okuma zinciri (read_sheet)",
        "file": f"{case['id']}-chain_model-evidence.json",
        "printed": len(evidence["printed"]),
        "claims": len(evidence["claims"]),
        "circles": len(evidence["geometry"]["circles"]),
        "scale_known": bool(evidence["sheet"]["scale_known"]),
        "outline_mm": evidence["geometry"]["outline_mm"],
        "notes": list(reading.notes),
        "refusals": list(reading.refusals),
        "seconds": round(time.time() - start, 2),
    }
    if reading.refusals:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "refused", "error_class": "reading",
                    "reason": "okuma milimetreye çevrilemedi: " + "; ".join(reading.refusals)})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row
    if chat is None:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "skipped", "error_class": "unsupported", "reason": "model koşusu istenmedi (--no-model)"})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    candidate = (propose_plan_split if split else propose_plan)(
        chat, evidence, ref=case["id"], sha256=_sha256(sheet), model_info=model_info,
        normalize_names=normalize_names, **({} if split else {"structured": structured}),
    )
    slug = f"{case['id']}-chain_model"
    (folder / f"{slug}-candidate.json").write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
    row["stages"]["plan"] = candidate.as_record()
    row["model_seconds"] = candidate.seconds
    if candidate.plan is None:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "planning",
                    "reason": "model şemaya uyan plan vermedi: " + "; ".join(candidate.errors)[:400]})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row
    return _plan_then_cad(row, case, folder, candidate, sheet, started, slug=slug,
                          ok_reason="çizimin kendi ölçümlerinden şemaya uyan model planı; katı kuruldu",
                          error_class="planning")


def _plan_then_cad(row: dict, case: dict, folder: Path, candidate, drawing, started: float, *, slug: str,
                   ok_reason: str, error_class: str) -> dict:
    """The tail both model-plan conditions share: build the plan, then check it against the sheet.

    `slug` names the condition's own artifacts — two model conditions in one run must not overwrite
    each other's raw answer or build folder, because the raw answer is the measurement. `drawing` is
    the sheet the plan must belong to: `chain_model` passes the real one, so `build_general` re-checks
    the source hash, while the hand-written-evidence condition has no drawing of its own to bind to
    and passes `None`.
    """
    start = time.time()
    build_folder = folder / f"{slug}-build"
    try:
        step, _stl = build_general(candidate.plan, drawing, build_folder)
        facts = json.loads((build_folder / "geometry.json").read_text(encoding="utf-8"))
        audit = json.loads((build_folder / "plan-audit.json").read_text(encoding="utf-8"))
        row["stages"]["cad"] = {"ok": True, "step": str(step.relative_to(ROOT)),
                                "checks": audit.get("checks"), "seconds": round(time.time() - start, 2)}
    except (CadFailure, ValueError) as exc:
        row["stages"]["cad"] = {"ok": False, "error": str(exc)[:800]}
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "cad", "reason": f"model planı kurulamadı: {str(exc)[:200]}"})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    start = time.time()
    try:
        meanings = meaning_page(ROOT / case["drawing"])
        row["stages"]["drawing_check"] = {**drawing_check(facts, meanings, case),
                                          "seconds": round(time.time() - start, 2)}
    except ValueError as exc:
        row["stages"]["drawing_check"] = {"error": str(exc)}
    row["seconds"] = round(time.time() - started, 2)
    check = row["stages"]["drawing_check"]
    if check.get("checked_claims") and not check.get("ok"):
        failed = [item for item in check["checks"] if not item["ok"]]
        row.update({"status": "built_unverified", "error_class": error_class,
                    "reason": "model planı kuruldu ama çizim kontrolü geçmedi: " + "; ".join(
                        f"{item['text']} -> {item.get('wanted_radius_mm', item.get('wanted_mm'))}"
                        for item in failed)})
    else:
        row.update({"status": "draft", "error_class": "ok", "reason": ok_reason})
    (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


def condition_relations(
    case: dict, folder: Path, chat: OllamaChat | None, timeout: float, model_info: dict | None,
    structured: bool = True, split: bool = False, normalize_names: bool = False,
) -> dict:
    """Perception held fixed: a hand-verified relation table goes to the same model.

    `split` asks the plan in three narrower calls instead of one (PLAN section 19.4); everything else
    about the condition — the evidence, the model, the context, the output limit — is unchanged.
    """
    row: dict = {"case": case["id"], "condition": "relations", "stages": {}}
    started = time.time()
    relations = RELATIONS_DIR / f"{case['id']}.json"
    if not relations.is_file():
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "skipped", "error_class": "unsupported",
                    "reason": f"elle doğrulanmış ilişki tablosu yok: {relations.relative_to(ROOT)}"})
        return row
    evidence = json.loads(relations.read_text(encoding="utf-8"))
    row["stages"]["evidence"] = {"file": str(relations.relative_to(ROOT)), "version": EVIDENCE_VERSION,
                                 "verified_by": evidence.get("verified_by"),
                                 "printed": len(evidence.get("printed") or []),
                                 "claims": len(evidence.get("claims") or [])}
    if chat is None:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "skipped", "error_class": "unsupported", "reason": "model koşusu istenmedi (--no-model)"})
        return row

    candidate = (propose_plan_split if split else propose_plan)(
        chat,
        evidence,
        ref=case["id"],
        sha256=_sha256(ROOT / case["drawing"]),
        model_info=model_info,
        normalize_names=normalize_names,
        **({} if split else {"structured": structured}),
    )
    slug = f"{case['id']}-relations"
    (folder / f"{slug}-candidate.json").write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
    row["stages"]["plan"] = candidate.as_record()
    row["model_seconds"] = candidate.seconds
    if candidate.plan is None:
        row["seconds"] = round(time.time() - started, 2)
        row.update({"status": "failed", "error_class": "planning",
                    "reason": "model şemaya uyan plan vermedi: " + "; ".join(candidate.errors)[:400]})
        (folder / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    return _plan_then_cad(row, case, folder, candidate, None, started, slug=slug,
                          ok_reason="doğrulanmış ilişkilerden şemaya uyan plan; katı kuruldu",
                          error_class="planning")


def condition_verified_plans(cases: list[dict], folder: Path) -> list[dict]:
    """Planning held fixed: written plans go to the same compiler and validator, no model in the loop.

    Every plan in `eval/plans/` is run. A plan whose source is a drawing is built against the drawing
    that carries its SHA256, so the run cannot quietly build it against another sheet.
    """
    rows: list[dict] = []
    by_hash = {_sha256(ROOT / case["drawing"]): ROOT / case["drawing"] for case in cases}
    for path in sorted((ROOT / "eval" / "plans").glob("*.json")):
        started = time.time()
        row: dict = {"case": path.stem, "condition": "verified_plan", "stages": {},
                     "split": "verified-input", "part_group": path.stem}
        try:
            plan = GeneralPlan.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            row.update({"status": "failed", "error_class": "planning",
                        "reason": f"plan dosyası okunamadı: {str(exc)[:200]}",
                        "seconds": round(time.time() - started, 2)})
            rows.append(row)
            continue
        drawing = None
        if plan.source.kind == "drawing":
            drawing = by_hash.get(plan.source.sha256 or "")
            if drawing is None:
                row.update({"status": "skipped", "error_class": "unsupported",
                            "reason": "planın kaynak çizimi bu koşuda yok (SHA256 eşleşmedi)",
                            "seconds": round(time.time() - started, 2)})
                rows.append(row)
                continue
        build_folder = folder / f"plan-{path.stem}"
        try:
            step, _stl = build_general(plan, drawing, build_folder)
            facts = json.loads((build_folder / "geometry.json").read_text(encoding="utf-8"))
            audit = json.loads((build_folder / "plan-audit.json").read_text(encoding="utf-8"))
            row["stages"]["cad"] = {
                "ok": True, "step": str(step.relative_to(ROOT)), "checks": audit.get("checks"),
                "tool_checks": audit.get("tool_checks"),
                "size_mm": [round(value, 4) for value in facts.get("size") or []],
                "volume_mm3": round(float(facts.get("volume") or 0.0), 4),
            }
            expect = plan.expect.model_dump() if plan.expect else None
            row.update({
                "status": "draft",
                "error_class": "ok",
                "reason": f"plan derleyiciden geçti; hacim {row['stages']['cad']['volume_mm3']} mm³, "
                          f"beklenti {expect}",
            })
        except (CadFailure, ValueError) as exc:
            row["stages"]["cad"] = {"ok": False, "error": str(exc)[:800]}
            row.update({"status": "failed", "error_class": "cad",
                        "reason": f"plan derleyiciden geçmedi: {str(exc)[:200]}"})
        row["seconds"] = round(time.time() - started, 2)
        (folder / f"{path.stem}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(row)
    return rows


class _ChatVision:
    """`OllamaChat` behind the reader's one-method interface, so a run reads with the model it named."""

    def __init__(self, chat: OllamaChat) -> None:
        self.chat = chat

    def ask(self, image_png: bytes, prompt: str, predict: int = 12) -> str:
        return self.chat.complete(prompt, image_png=image_png, num_predict=predict)

    def release(self) -> None:
        self.chat.unload()


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- driving one run -----------------------------------------------------------------


def _atomic_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def checkpoint(folder: Path, record: dict, rows: list[dict], sampler: ResourceSampler,
               started: float, status: str = "running") -> None:
    """Keep completed results on interruption; a killed process leaves an explicit running record."""
    record["run"]["status"] = status
    record["run"]["seconds"] = round(time.time() - started, 2)
    if status != "running":
        record["run"]["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    record["resources"] = sampler.record()
    record["results"] = rows
    record["error_classes"] = _counts(rows, "error_class")
    record["statuses"] = _counts(rows, "status")
    record["summary"] = _summary(rows)
    _atomic_json(folder / "run.json", record)


def main() -> None:
    parser = argparse.ArgumentParser(description="PLAN section 7: the pre-training measurement")
    parser.add_argument("--model", default="qwen2.5vl:3b", help="installed Ollama tag to measure")
    parser.add_argument("--label", default=None, help="run folder name; default: timestamp")
    parser.add_argument("--out", default="out/model-baseline")
    parser.add_argument("--conditions", default=",".join(ALL_CONDITIONS))
    parser.add_argument("--cases", default="", help="comma-separated case ids (default: every case)")
    parser.add_argument("--num-ctx", type=int, default=16384)
    parser.add_argument("--predict", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--keep-alive", default="5m")
    parser.add_argument("--no-model", action="store_true", help="run only the conditions that need no model")
    parser.add_argument("--no-unload", action="store_true", help="leave the weights resident between calls")
    parser.add_argument("--unstructured", action="store_true",
                        help="do not send the plan schema as the decoder grammar (measures the loose interface)")
    parser.add_argument("--split", action="store_true",
                        help="ask the plan in narrower calls: the parameters, then one call per closed "
                             "profile the readings measured, then the operations (PLAN sections 19.4, 20; "
                             "the merged answer meets the same plan contract)")
    parser.add_argument("--normalize-names", action="store_true",
                        help="run the lossless identifier rewrite on the answer before judging it "
                             "(PLAN section 20.2: the decoder enforces a string pattern but not an "
                             "object's propertyNames; the rewrite is recorded either way)")
    arguments = parser.parse_args()
    if arguments.split and arguments.unstructured:
        parser.error("--split ölçümü adım başına şema grameri kullanır; --unstructured ile birlikte kullanılamaz")

    conditions = [item.strip() for item in arguments.conditions.split(",") if item.strip()]
    unknown = [item for item in conditions if item not in ALL_CONDITIONS]
    if unknown:
        parser.error(f"bilinmeyen koşul: {unknown}; geçerli: {list(ALL_CONDITIONS)}")
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    if arguments.cases:
        wanted = {item.strip() for item in arguments.cases.split(",")}
        cases = [case for case in cases if case["id"] in wanted]
    cases = [case for case in cases if (ROOT / case["drawing"]).is_file()]
    if not cases:
        parser.error("ölçülecek pafta yok")

    label = arguments.label or time.strftime("%Y%m%d-%H%M%S")
    folder = ROOT / arguments.out / label
    if folder.exists():
        parser.error(f"koşu klasörü zaten var; yeni --label seç: {folder}")
    folder.mkdir(parents=True)
    (folder / "cases").mkdir(exist_ok=True)

    record: dict = {
        "run": {
            "id": label,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "argv": sys.argv[1:],
            "conditions": conditions,
            "no_model": arguments.no_model,
            "structured_output": not arguments.unstructured,
            "name_normalization": NAME_ADAPTER if arguments.normalize_names else "off",
            "active": {"stage": "setup"},
        },
        "code": code_record(),
        "manifest": manifest_record(json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]),
        "schema_version": SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION_SPLIT if arguments.split else PROMPT_VERSION,
        "plan_interface": ("split-per-profile" if arguments.split
                           else "free-text" if arguments.unstructured else "json-schema"),
        "evidence_version": EVIDENCE_VERSION,
        "model": {"requested": arguments.model, "installed": [], "resolved": None, "settings": None,
                  "cold_start_s": None, "warm_start_s": None, "dependency_missing": None},
        "results": [],
        "notes": [],
    }

    sampler = ResourceSampler()
    started_all = time.time()
    rows: list[dict] = []
    checkpoint(folder, record, rows, sampler, started_all)
    chat: OllamaChat | None = None
    model_info: dict | None = None
    needs_model = (not arguments.no_model) and any(name in conditions
                                                 for name in ("reading", "chain_model", "relations"))
    sampler.start()
    run_status = "running"
    try:
        if needs_model:
            try:
                models = installed_models()
                record["model"]["installed"] = [model.as_dict() for model in models]
                from drawingto3d.llama import find_model

                chosen = find_model(models, arguments.model)
                model_info = chosen.as_dict()
                settings = ChatSettings(
                    model=chosen.name, num_ctx=arguments.num_ctx, temperature=0.0,
                    num_predict=arguments.predict, keep_alive=arguments.keep_alive, timeout=arguments.timeout,
                )
                chat = OllamaChat(chosen.name, settings=settings)
                record["model"]["resolved"] = model_info
                record["model"]["settings"] = chat.settings_record()
                chat.unload()
                started = time.time()
                chat.complete("ok", num_predict=1)
                record["model"]["cold_start_s"] = round(time.time() - started, 2)
                started = time.time()
                chat.complete("ok", num_predict=1)
                record["model"]["warm_start_s"] = round(time.time() - started, 2)
            except UnavailableModel as exc:
                record["model"]["dependency_missing"] = str(exc)
                record["notes"].append(f"model koşusu yapılamadı: {exc}")
                unmeasurable = [name for name in conditions
                                if name in ("reading", "chain_model", "relations")]
                if unmeasurable:
                    conditions = [name for name in conditions if name not in unmeasurable]
                    record["notes"].append("model koşulları model olmadan ölçülemez; koşudan çıkarıldı: "
                                           + ",".join(unmeasurable))
                chat = None

        for case in cases:
            for name in conditions:
                if name == "verified_plan":
                    continue
                record["run"]["active"] = {"case": case["id"], "condition": name}
                checkpoint(folder, record, rows, sampler, started_all)
                start = time.time()
                if name == "reading":
                    row = condition_reading(case, folder / "cases", chat, arguments.timeout)
                elif name == "chain":
                    row = condition_chain(case, folder / "cases", arguments.timeout)
                elif name == "chain_model":
                    row = condition_chain_model(case, folder / "cases", chat, arguments.timeout, model_info,
                                                structured=not arguments.unstructured, split=arguments.split,
                                                normalize_names=arguments.normalize_names)
                else:
                    row = condition_relations(case, folder / "cases", chat, arguments.timeout, model_info,
                                              structured=not arguments.unstructured, split=arguments.split,
                                              normalize_names=arguments.normalize_names)
                row["wall_seconds"] = round(time.time() - start, 2)
                row.setdefault("seconds", row["wall_seconds"])
                row["split"] = case["split"]
                row["part_group"] = case["part_group"]
                rows.append(row)
                _atomic_json(folder / "cases" / f"{case['id']}-{name}.json", row)
                checkpoint(folder, record, rows, sampler, started_all)
                print(_line(row), flush=True)
        if "verified_plan" in conditions:
            record["run"]["active"] = {"condition": "verified_plan"}
            checkpoint(folder, record, rows, sampler, started_all)
            for row in condition_verified_plans(cases, folder / "cases"):
                row["wall_seconds"] = row.get("seconds")
                rows.append(row)
                checkpoint(folder, record, rows, sampler, started_all)
                print(_line(row), flush=True)
        run_status = "complete"
        record["run"]["active"] = None
    except KeyboardInterrupt:
        run_status = "interrupted"
        raise
    except BaseException as exc:
        run_status = "failed"
        record["notes"].append(f"koşu kesildi: {type(exc).__name__}: {exc}")
        raise
    finally:
        sampler.stop()
        checkpoint(folder, record, rows, sampler, started_all, run_status)
        if chat is not None and not arguments.no_unload:
            chat.unload()

    _atomic_json(folder / "summary.json", record["summary"])
    print(f"\nyazıldı: {folder / 'run.json'}")
    print(json.dumps({"error_classes": record["error_classes"], "statuses": record["statuses"],
                      "resources": {key: value for key, value in record["resources"].items()
                                    if key != "raw_samples"}}, ensure_ascii=False, indent=2))


def _counts(rows: list[dict], key: str) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "?"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _summary(rows: list[dict]) -> dict:
    """Per condition: how many cases each outcome, and the median wall time."""
    summary: dict[str, dict] = {}
    for row in rows:
        entry = summary.setdefault(row["condition"], {"cases": 0, "status": {}, "error_class": {},
                                                      "seconds": [], "refusals": []})
        entry["cases"] += 1
        entry["status"][row["status"]] = entry["status"].get(row["status"], 0) + 1
        entry["error_class"][row["error_class"]] = entry["error_class"].get(row["error_class"], 0) + 1
        entry["seconds"].append(row.get("seconds") or 0.0)
        if row["status"] in ("refused", "failed", "skipped", "built_unverified"):
            entry["refusals"].append({"case": row["case"], "reason": row.get("reason")})
    for entry in summary.values():
        values = sorted(entry["seconds"])
        entry["median_seconds"] = round(values[len(values) // 2], 2) if values else None
        entry["total_seconds"] = round(sum(values), 2)
        entry.pop("seconds")
    return summary


def _line(row: dict) -> str:
    return (f"{row['case']:<18} {row['condition']:<14} {row['status']:<17} {row['error_class']:<12} "
            f"{row['seconds']:>7.2f}s  {str(row.get('reason') or '')[:96]}")


if __name__ == "__main__":
    main()
