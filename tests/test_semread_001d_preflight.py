"""SEMREAD-001D — static preflight aracının testleri (PLAN-18 §32–§41).

Kapsam (hepsi 0 inference; deftere **yazılmaz**):

* §33 kimlik: dört Round-1 hücresinin statik manifesti current kimlikleri taşır; bayat sözleşme
  kimliği kırmızıdır;
* §34 bütçe: sıfır bütçe yeşil, sapma kırmızı;
* §35 runtime: model/digest/runtime birebir; uyuşmazlık ve sunucu erişilemezliği kırmızı;
* §36 paylaşımlı ayar + gövde `options` imzası;
* §37/§38/§39 prompt-context: kalibrasyon formülü pinli; context kapısı düştüğünde §49 kanıtı
  (hücre + tahmin + gerekli ctx + mevcut ctx + eksik) raporlanır;
* §40 structured-output: `format` json-schema yolu; desteklenmeyen birleşim anahtarı eklenirse
  kırmızı;
* §41/§52: dry-run dört çağrı planlar; PNG eksikse kırmızı; cache bayatsa `inputs_current` kırmızı;
  V/VE ham byte aynı, VE kanıtı ayrı hash'li;
* salt-okurluk: varsayılan koşu diske yazmaz, taşıma katmanına dokunmaz (0-inference trap'i);
  `--write` yalnız `corpus/static-preflight.json` yazar.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001d_preflight.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001d_preflight", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()
pilot = tool.pilot
inputs_tool = tool._inputs

EXPECTED_CHECK_IDS = ["identity_current", "dry_run_planned_calls", "budget_zero", "runtime_exact",
                      "shared_settings", "prompt_context_gate", "shared_request_options",
                      "structured_output_static", "inputs_current", "closure_verifier"]


def _good_runtime() -> dict:
    return {"endpoint": "http://127.0.0.1:11434", "version": pilot.EXPECTED_RUNTIME,
            "model": {"name": pilot.MODEL, "digest": pilot.EXPECTED_DIGEST},
            "model_canonical": {"name": pilot.MODEL, "digest": pilot.EXPECTED_DIGEST},
            "parser": "test", "error": None}


def _good_closure() -> dict:
    return {"ok": True, "checked": 45, "total": 45, "exit_code": 0,
            "tail": "kapanış manifesti: 45/45 artifact birebir — TAMAM"}


def _canvas(width: int, height: int, shift: int = 0) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (width - 20, height - 20), (0, 0, 0), 2)
    cv2.circle(image, (width // 2 + shift, height // 2), min(width, height) // 5, (0, 0, 0), 2)
    cv2.putText(image, "O40", (width // 4, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2,
                cv2.LINE_AA)
    return image


def _round1_pages() -> list[dict]:
    return [page for page in pilot.PAGES if page["page_id"] in inputs_tool.ROUND1_PAGES]


def _materialize(lab: dict) -> None:
    """Round-1 girdi katmanını kur: sayfa PNG'leri + kimlik kaydı + kanonik girdi önbelleği."""
    pilot.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for page in _round1_pages():
        source = pilot.open_source(pilot.ROOT / page["path"])
        png = source.frame_png
        (pilot.PAGES_DIR / f"{page['page_id']}.png").write_bytes(png)
        rows.append({"page_id": page["page_id"],
                     "raw_page": {"sha256": hashlib.sha256(png).hexdigest()}})
        observations = pilot.observe(pilot.ROOT / page["path"])
        for arm in pilot.ARMS:
            bundle = pilot.prepare_arm_inputs(source, observations, image_id=pilot.PAGE_IMAGE_ID,
                                              arm=arm, resize_max_side=pilot.IMAGE_MAX_SIDE)
            prompt = pilot.candidate_prompt([pilot.PAGE_IMAGE_ID],
                                            observations=bundle["observations"] or None)
            record = pilot.prediction_input_record(page, arm, bundle=bundle, prompt=prompt)
            pilot.store_prepared_input(page, arm, record)
    pilot.write_json(pilot.CORPUS_DIR / inputs_tool.RECORD_NAME,
                     {"schema": "semread-001d-input-identity/1", "pages": rows})


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """Sahte 001D kökü: iki dev (Round-1 adlarıyla) + bir frozen sayfa; kaynaklar sentetik PNG."""
    root = tmp_path / "repo"
    (root / "examples").mkdir(parents=True)
    source_a = root / "examples" / "synthetic-a.png"
    source_b = root / "examples" / "synthetic-b.png"
    cv2.imwrite(str(source_a), _canvas(300, 220))
    cv2.imwrite(str(source_b), _canvas(340, 240, shift=20))
    monkeypatch.setattr(pilot, "ROOT", root)
    monkeypatch.setattr(pilot, "LAB_ROOT", root / "out" / "lab")
    pilot.use_experiment(tool.EXPERIMENT)
    report_root = root / "out" / "lab" / tool.EXPERIMENT
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", tool.EXPERIMENT)
    monkeypatch.setattr(pilot, "REPORT_ROOT", report_root)
    monkeypatch.setattr(pilot, "CORPUS_DIR", report_root / "corpus")
    monkeypatch.setattr(pilot, "GOLD_DIR", report_root / "corpus" / "gold")
    monkeypatch.setattr(pilot, "PAGES_DIR", report_root / "corpus" / "pages")
    monkeypatch.setattr(pilot, "PREPARED_INPUT_DIR", report_root / "corpus" / "prepared-inputs")
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", report_root / "attempts")
    monkeypatch.setattr(pilot, "PAGES", [
        {"page_id": "dev-plate-pocket", "path": "examples/synthetic-a.png", "split": "dev",
         "group": "synthetic"},
        {"page_id": "dev-flange-book", "path": "examples/synthetic-b.png", "split": "dev",
         "group": "synthetic"},
        {"page_id": "frozen-extra", "path": "examples/synthetic-a.png", "split": "frozen",
         "group": "synthetic"},
    ])
    monkeypatch.setattr(pilot, "runtime_identity", _good_runtime)
    monkeypatch.setattr(tool, "closure_verify", _good_closure)
    state = {"root": root, "report_root": report_root}
    _materialize(state)
    return state


def _check(report: dict, check_id: str) -> dict:
    return next(check for check in report["checks"] if check["check"] == check_id)


def _tree(root: Path) -> dict:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def test_preflight_passes_on_the_prepared_lab_and_plans_four_calls(lab):
    report = tool.run_preflight()
    assert report["ok"] is True, report["failed"]
    assert report["inference_calls"] == 0
    assert [check["check"] for check in report["checks"]] == EXPECTED_CHECK_IDS
    assert report["round1"]["planned_real_calls"] == 4
    assert report["budget"]["dev_used"] == 0 and report["budget"]["final_used"] == 0
    cells = report["round1"]["cells"]
    assert [(cell["page_id"], cell["arm"]) for cell in cells] == list(tool.ROUND1_CELLS)
    for cell in cells:
        assert cell["experiment"] == "semread-001d"
        assert cell["schema_version"] == tool.EXPECTED_VERSIONS["schema_version"]
        assert cell["reader_version"] == tool.EXPECTED_VERSIONS["reader_version"]
        assert cell["contract_version"] == tool.EXPECTED_VERSIONS["contract_version"]
        assert cell["producer_identity"] == pilot.producer_identity()
        assert cell["preprocessing_identity"] == pilot.preprocessing_identity()
        assert cell["cached_input_key_matches"] is True
        assert cell["cached_record_matches_rebuild"] is True
        assert cell["request"]["format_is_json_schema"] is True
        assert cell["context"]["gate_ok"] is True
        assert cell["historical_001c"] is None  # tmp kökte historical kanıt yok — dürüst null
    per_page = {}
    for cell in cells:
        per_page.setdefault(cell["page_id"], []).append(cell)
    for page_cells in per_page.values():
        v, ve = page_cells
        assert len(v["images"]) == 1 and len(ve["images"]) == 2  # §37: VE ekstra kanıt
        assert v["images"][0]["sent_sha256"] == ve["images"][0]["sent_sha256"]  # §36
        assert ve["images"][1]["sent_sha256"] != ve["images"][0]["sent_sha256"]
        assert v["observation_rows"] == 0 and ve["observation_rows"] > 0
        # §36: üretim ayarı imzası kollar arasında aynı.
        assert v["generation_signature"] == ve["generation_signature"]
    assert _check(report, "closure_verifier")["closure"]["checked"] == 45


def test_context_gate_reports_the_section_49_evidence_when_it_fails(lab, monkeypatch):
    monkeypatch.setitem(pilot.SETTINGS, "num_ctx", 1024)
    report = tool.run_preflight()
    gate = _check(report, "prompt_context_gate")
    assert gate["ok"] is False and report["ok"] is False
    assert "prompt_context_gate" in report["failed"]
    assert len(gate["failures"]) == 4
    for failure in gate["failures"]:
        assert failure["cell"] in {f"{page_id}-{arm}" for page_id, arm in tool.ROUND1_CELLS}
        assert failure["prompt_tokens"] > 0
        assert failure["required_ctx"] == failure["prompt_tokens"] + pilot.NUM_PREDICT
        assert failure["current_ctx"] == 1024
        assert failure["deficit"] == failure["required_ctx"] - 1024


def test_a_stale_contract_identity_is_red(lab, monkeypatch):
    monkeypatch.setattr(pilot, "CONTRACT_VERSION", "semread-001c-run-contract/1")
    report = tool.run_preflight()
    assert _check(report, "identity_current")["ok"] is False
    assert "identity_current" in report["failed"]


def test_budget_drift_is_red(lab, monkeypatch):
    base = pilot.budget_report()
    monkeypatch.setattr(pilot, "budget_report", lambda: {**base, "dev_used": 1})
    report = tool.run_preflight()
    assert _check(report, "budget_zero")["ok"] is False
    assert "budget_zero" in report["failed"]


def test_runtime_mismatch_and_unreachable_are_red(lab, monkeypatch):
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {**_good_runtime(), "version": "0.31.0"})
    assert _check(tool.run_preflight(), "runtime_exact")["ok"] is False
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {**_good_runtime(),
                                 "model_canonical": {"name": pilot.MODEL,
                                                     "digest": "0" * 64}})
    assert _check(tool.run_preflight(), "runtime_exact")["ok"] is False
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {**_good_runtime(), "error": "URLError: bağlantı yok"})
    report = tool.run_preflight()
    assert _check(report, "runtime_exact")["ok"] is False
    assert "runtime_exact" in report["failed"]


def test_structured_output_check_flags_an_unsupported_schema_key(lab, monkeypatch):
    real = pilot.candidate_json_schema

    def with_anyof():
        schema = real()
        schema["properties"]["items"]["items"]["anyOf"] = [{"type": "string"}]  # bilinçli kırmızı
        return schema

    monkeypatch.setattr(pilot, "candidate_json_schema", with_anyof)
    report = tool.run_preflight()
    check = _check(report, "structured_output_static")
    assert check["ok"] is False and "anyOf" in check["detail"]
    assert "structured_output_static" in report["failed"]


def test_inputs_current_is_red_when_the_cache_is_stale(lab):
    path = pilot.PREPARED_INPUT_DIR / "dev-plate-pocket-V.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    blob["record"]["prompt_bytes"] += 1  # bayat kayıt: yeniden türetimle uyuşmaz
    path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    report = tool.run_preflight()
    assert _check(report, "inputs_current")["ok"] is False
    assert "inputs_current" in report["failed"]
    rebuild = {(row["cell"]): row for row in _check(report, "inputs_current")["rebuild"]}
    assert rebuild["dev-plate-pocket-V"]["cached_matches"] is False
    assert rebuild["dev-plate-pocket-VE"]["cached_matches"] is True


def test_dry_run_check_is_red_when_a_page_png_is_missing(lab):
    (pilot.PAGES_DIR / "dev-flange-book.png").unlink()
    report = tool.run_preflight()
    plan = _check(report, "dry_run_planned_calls")
    assert plan["ok"] is False
    assert plan["plan"]["planned_real_calls"] == 2
    assert "dry_run_planned_calls" in report["failed"]


def test_the_tool_reads_no_gold_and_never_calls_the_transport(lab, monkeypatch):
    source = TOOL_PATH.read_text(encoding="utf-8")
    for forbidden in ("GOLD_DIR", "semread_001b_gold", "load_reference(", "read_page(",
                      "OllamaChat", "LabRunner", "OllamaCoder", "OllamaVision"):
        assert forbidden not in source, f"preflight {forbidden!r} içermemeli"

    import drawingto3d.llama as llama

    def must_not_send(*_args, **_kwargs):
        raise AssertionError("static preflight canlı çağrı yapamaz")

    monkeypatch.setattr(llama, "_ollama_chat", must_not_send)
    before = _tree(lab["report_root"])
    report = tool.run_preflight()
    assert report["ok"] is True
    assert _tree(lab["report_root"]) == before, "varsayılan koşu diske yazmamalı"
    assert not (lab["report_root"] / "state.json").exists()
    assert not (lab["report_root"] / "attempts").exists()


def test_write_scope_is_only_the_preflight_record(lab, capsys):
    code = tool.main(["--write"])
    assert code == 0
    record_path = lab["report_root"] / "corpus" / tool.RECORD_NAME
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["schema"] == tool.SCHEMA and record["ok"] is True
    assert record["inference_calls"] == 0
    assert not (lab["report_root"] / "state.json").exists()
    assert not (lab["report_root"] / "attempts").exists()
    printed = json.loads(capsys.readouterr().out)
    assert printed["ok"] is True and printed["round1"]["planned_real_calls"] == 4


def test_estimate_tokens_pins_the_calibration_formula():
    assert tool.ESTIMATE_SLOPE == 0.816 and tool.ESTIMATE_INTERCEPT == 664
    assert tool.estimate_tokens(0) == 664
    assert tool.estimate_tokens(10000) == 8824


def test_measurement_is_byte_stable_across_runs(lab):
    first = tool.measure_round1()["cells"]
    second = tool.measure_round1()["cells"]
    for left, right in zip(first, second):
        assert left["prompt"]["sha256"] == right["prompt"]["sha256"]
        assert left["request"]["request_sha256"] == right["request"]["request_sha256"]
        assert left["request"]["format_sha256"] == right["request"]["format_sha256"]
        assert left["generation_signature"] == right["generation_signature"]
        assert right["cached_record_matches_rebuild"] is True


def test_round1_declaration_drift_stops_the_tool(lab, monkeypatch):
    monkeypatch.setattr(pilot, "PAGES", [
        {"page_id": "dev-flange-book", "path": "examples/synthetic-b.png", "split": "dev",
         "group": "synthetic"}])
    with pytest.raises(SystemExit, match="Round 1"):
        tool.run_preflight()
