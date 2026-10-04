"""SEMREAD-001B — P2 §18–§20: matris nihai durumları, rapor içeriği kapısı, kanıt zinciri.

Bu testler **model çağırmaz** ve gerçek lab kökünü yazmaz: geçici köke yazılan sahte attempt
klasörleriyle çalışır (`out/lab/semread-001b/` dokunulmaz).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


pilot = _load("semread_001b_pilot_acceptance", ROOT / "eval" / "semread_001b_pilot.py")


@pytest.fixture()
def lab(tmp_path, monkeypatch):
    """Geçici lab kökü: gerçek `out/lab` asla yazılmaz."""
    report_root = tmp_path / "semread-001b"
    (report_root / "attempts").mkdir(parents=True)
    (report_root / "evaluations").mkdir(parents=True)
    monkeypatch.setattr(pilot, "REPORT_ROOT", report_root)
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", report_root / "attempts")
    monkeypatch.setattr(pilot, "state_path", lambda: report_root / "state.json")
    monkeypatch.setattr(pilot, "load_state", lambda: json.loads(
        (report_root / "state.json").read_text(encoding="utf-8"))
        if (report_root / "state.json").exists() else {})
    return report_root


def _write_attempt(report_root: Path, case_id: str, *, state: str, image_sha: str | None,
                   evaluation_identity: str | None, with_files: bool = True,
                   result_verdict: str = "pass") -> Path:
    directory = report_root / "attempts" / case_id / "attempt-0001"
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "semread-001b-producer/1", "case_id": case_id,
                "code_identity": "c0de", "model": "qwen3-vl:8b-instruct",
                "page_png_sha256": image_sha, "evaluation_identity": evaluation_identity}
    if not with_files:
        return directory
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "prompt.txt").write_text("istem", encoding="utf-8")
    (directory / "request-manifest.json").write_text("{}", encoding="utf-8")
    (directory / "result.json").write_text(
        json.dumps({"verdict": result_verdict, "product_verdict": result_verdict}),
        encoding="utf-8")
    index = {"schema": "semread-001b-artifact-index/1", "files": [],
             "count": 4}
    for name in ("manifest.json", "prompt.txt", "request-manifest.json", "result.json"):
        payload = (directory / name).read_bytes()
        index["files"].append({"path": name,
                               "sha256": hashlib.sha256(payload).hexdigest(),
                               "bytes": len(payload)})
    index["count"] = len(index["files"])
    (directory / "artifact-index.json").write_text(json.dumps(index), encoding="utf-8")
    return directory


def _history_row(directory: Path, *, case_id: str, arm: str, page_id: str,
                 state: str = "pass", evaluation_identity: str | None = None,
                 page_png_sha256: str | None = None) -> dict:
    return {"attempt_id": f"{case_id}/{directory.name}", "directory": str(directory),
            "arm": arm, "page_id": page_id, "split": "dev", "phase": "dev",
            "verdict": state, "state": state, "seconds": 1.0,
            "evaluation_identity": evaluation_identity,
            "page_png_sha256": page_png_sha256}


def _state(report_root: Path, rows: list[dict], live_calls: list[dict | None] | None = None) -> None:
    (report_root / "state.json").write_text(
        json.dumps({"attempts": {"case": rows}, "live_calls": live_calls or []}),
        encoding="utf-8")


def _cell(page_id: str, arm: str, attempt: Path | None, *, cell: str = "to_run") -> dict:
    return {"page_id": page_id, "arm": arm, "kind": "vlm" if arm != "D" else "deterministic",
            "cell": cell, "split": "dev", "attempt": str(attempt) if attempt else None}


# --------------------------------------------------------------- §18 nihai durumlar

def test_dispositions_use_final_states_on_the_real_repository_pagination():
    """Gerçek corpusla 30 hücre üretilir ve her hücre bir nihai/bekleme durumu alır (§18)."""
    matrix = pilot.final_matrix()
    dispositions = matrix["dispositions"]
    assert len(dispositions["cells"]) == 30
    allowed = set(pilot.DISPOSITION_FINAL) | set(pilot.DISPOSITION_PENDING)
    assert all(cell["disposition"] in allowed for cell in dispositions["cells"])
    assert dispositions["complete"] == (not dispositions["open_cells"])


def test_a_pending_cell_keeps_the_matrix_incomplete(lab):
    """`to_run`/`not_run` nihai değildir: matris tamamlanmış sayılmaz, B05 kapanamaz (§18)."""
    dispositions = pilot.matrix_dispositions([_cell("dev-plate-pocket", "V", None)])
    assert dispositions["complete"] is False
    assert dispositions["counts"] == {"to_run": 1}
    assert dispositions["open_cells"]


def test_a_failed_attempt_is_final_and_does_not_disappear(lab):
    """Başarısız deneme nihaidir: sayıdan düşmez, `failed_attempt` olarak görünür (§18)."""
    directory = _write_attempt(lab, "dev-plate-pocket-V", state="parse_error",
                               image_sha=None, evaluation_identity=None,
                               result_verdict="fail")
    _state(lab, [_history_row(directory, case_id="dev-plate-pocket-V", arm="V",
                              page_id="dev-plate-pocket", state="parse_error")])
    dispositions = pilot.matrix_dispositions([_cell("dev-plate-pocket", "V", directory)])
    assert dispositions["counts"] == {"failed_attempt": 1}
    assert dispositions["complete"] is True
    assert dispositions["cells"][0]["reason"].startswith("ürün kararı")


def test_a_blocked_history_row_is_final_and_named_as_such(lab):
    """Kapı/bütçe engeli de nihaidir; sebebi durum adıyla raporlanır (§18)."""
    directory = lab / "attempts" / "dev-plate-pocket-V" / "attempt-0001"
    directory.mkdir(parents=True, exist_ok=True)
    _state(lab, [_history_row(directory, case_id="dev-plate-pocket-V", arm="V",
                              page_id="dev-plate-pocket", state="blocked_budget")])
    dispositions = pilot.matrix_dispositions([_cell("dev-plate-pocket", "V", None)])
    assert dispositions["counts"] == {"blocked": 1}
    assert dispositions["cells"][0]["attempt_state"] == "blocked_budget"
    assert dispositions["complete"] is True


def test_a_previous_pass_not_selected_by_the_matrix_stays_pending(lab):
    """Geçmişte geçmiş ama matrise seçilmemiş deneme hücreyi kapatmaz: yeniden koşulmalı (§18)."""
    directory = _write_attempt(lab, "dev-plate-pocket-V", state="pass", image_sha=None,
                               evaluation_identity=None)
    _state(lab, [_history_row(directory, case_id="dev-plate-pocket-V", arm="V",
                              page_id="dev-plate-pocket", state="pass")])
    dispositions = pilot.matrix_dispositions([_cell("dev-plate-pocket", "V", None)])
    assert dispositions["counts"] == {"to_run": 1}
    assert "yeniden koşulmalı" in dispositions["cells"][0]["reason"]
    assert dispositions["complete"] is False


# --------------------------------------------------------------- §19 rapor içeriği

def test_a_comparison_without_the_required_report_content_cannot_close_b06():
    """Boş olmayan `vs_d` yetmez: rapor işaretleri ve ölçüm şarttır (§19)."""
    checks = pilot.report_evidence("## Kollar\nboş rapor", {"aggregates": {}, "comparison": {}})
    assert checks["complete"] is False
    assert set(checks["missing"]) == {name for name, _ in pilot.REPORT_MARKERS}


def test_the_report_carries_every_required_section_on_the_real_payload():
    """Gerçek rapor §19'un bütün işaretlerini taşır; ölçüm yokken B06 yine açık kalır."""
    payload = pilot.evaluate(write_report=False)
    text = pilot.render_report(payload)
    checks = pilot.report_evidence(text, payload)
    assert checks["missing"] == []
    assert "yüklem bazında" in text and "Matris hücreleri" in text
    assert checks["measured"] is False and checks["complete"] is False, (
        "gerçek lab'da henüz ölçülecek tahmin/referans yok: B06 kapanmamalı")
    # Ölçüm geldiğinde aynı rapor metni kapıyı geçer (tahmin uydurulmaz, koşul simüle edilir).
    assert pilot.report_evidence(text, {"aggregates": {"D": {}},
                                        "comparison": {"vs_d": {"V": {}}}})["complete"] is True


def test_outcome_totals_are_derived_from_the_ledger_not_invented(lab):
    """Taşıma/parse/yerel hata sayaçları attempt defterinden türetilir (§19)."""
    _state(lab, [
        {"attempt_id": "a/attempt-0001", "state": "transport_error", "arm": "V"},
        {"attempt_id": "a/attempt-0002", "state": "parse_error", "arm": "V"},
        {"attempt_id": "a/attempt-0003", "state": "local_error_prepare", "arm": "VE"},
        {"attempt_id": "a/attempt-0004", "state": "pass", "arm": "VE"},
    ])
    totals = pilot.outcome_totals()
    assert totals["transport_failure_count"] == 1
    assert totals["parse_failure_count"] == 1
    assert totals["local_error_count"] == 1
    assert totals["failed_attempt_total"] == 3
    assert totals["passed_attempts"] == 1


# --------------------------------------------------------------- §20 kanıt zinciri

def _fresh_chain_inputs(lab, *, image_sha=None, evaluation_identity=None,
                        with_files=True, result_verdict="pass"):
    page_id, arm = "dev-plate-pocket", "D"
    case_id = f"{page_id}-{arm}"
    identity = evaluation_identity if evaluation_identity is not None else pilot.evaluation_identity()
    directory = _write_attempt(lab, case_id, state="pass", image_sha=image_sha,
                               evaluation_identity=identity, with_files=with_files,
                               result_verdict=result_verdict)
    row = _history_row(directory, case_id=case_id, arm=arm, page_id=page_id,
                       evaluation_identity=identity, page_png_sha256=image_sha)
    _state(lab, [row])
    return _cell(page_id, arm, directory)


def test_a_complete_chain_verifies_hashes_and_identity(lab, tmp_path, monkeypatch):
    """Sağlam zincir: geçmiş kaydı + artifact hash'leri + kimlik + sonuç halkaları tamdır (§20)."""
    page_png = tmp_path / "dev-plate-pocket.png"
    page_png.write_bytes(b"png-bytes")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path)
    sha = hashlib.sha256(b"png-bytes").hexdigest()
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is True
    assert chain["checked_cells"] == 1
    assert chain["cells"][0]["gaps"] == []
    assert chain["cells"][0]["checks"]["budget_record"] is None, "D kolu bütçe harcamaz"


def test_a_tampered_artifact_breaks_the_chain(lab, tmp_path, monkeypatch):
    """Artifact içeriği değiştirilirse hash tutmaz ve hücre kabul edilmez (§20)."""
    page_png = tmp_path / "dev-plate-pocket.png"
    page_png.write_bytes(b"png-bytes")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path)
    sha = hashlib.sha256(b"png-bytes").hexdigest()
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    (Path(cell["attempt"]) / "result.json").write_text("{}", encoding="utf-8")
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "artifact_index" in chain["cells"][0]["gaps"]


def test_a_changed_input_image_breaks_the_chain(lab, tmp_path, monkeypatch):
    """Girdi görüntüsü değişirse kayıtlı sha256 tutmaz: zincir koptu (§20)."""
    page_png = tmp_path / "dev-plate-pocket.png"
    page_png.write_bytes(b"new-bytes")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path)
    cell = _fresh_chain_inputs(lab, image_sha=hashlib.sha256(b"png-bytes").hexdigest())
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "input_identity" in chain["cells"][0]["gaps"]


def test_a_stale_evaluation_identity_breaks_the_chain(lab, tmp_path, monkeypatch):
    """Değerlendirme kimliği bayatsa hücre kanıt zincirine giremez (§20)."""
    page_png = tmp_path / "dev-plate-pocket.png"
    page_png.write_bytes(b"png-bytes")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path)
    sha = hashlib.sha256(b"png-bytes").hexdigest()
    cell = _fresh_chain_inputs(lab, image_sha=sha, evaluation_identity="bayat-kimlik")
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "evaluation_identity" in chain["cells"][0]["gaps"]


def test_an_empty_chain_is_not_complete(lab):
    """Seçili hücre yoksa zincir boştur ve kabul edilmez: B07 kanıtsız kapanamaz (§20)."""
    chain = pilot.evidence_chain_report([_cell("dev-plate-pocket", "V", None)])
    assert chain["checked_cells"] == 0
    assert chain["vacuous"] is True
    assert chain["complete"] is False


def test_b05_and_b07_stay_open_without_selected_attempts(lab):
    """Gerçek lab durumu: hücreler koşulmamışken B05 ve B07 açık kalır (uydurma kanıt yok)."""
    payload = pilot.evaluate(write_report=False)
    acceptance = pilot.acceptance_rows(payload)
    assert acceptance["B05"]["status"] == "open"
    assert acceptance["B07"]["status"] == "open"
    assert "açık hücreler" in acceptance["B05"]["detail"]


def test_the_handoff_document_exists_and_names_the_acceptance_gates():
    """B05/B06/B07 adları devir notunda geçer (kapıların izlenebilirliği)."""
    handoff = ROOT / "docs" / "HERMES_SEMREAD_001B_HANDOFF.md"
    text = handoff.read_text(encoding="utf-8")
    for gate in ("B05", "B06", "B07"):
        assert gate in text
