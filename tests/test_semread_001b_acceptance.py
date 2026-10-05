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


def _page(page_id: str = "dev-plate-pocket") -> dict:
    return next(row for row in pilot.PAGES if row["page_id"] == page_id)


def _write_attempt(report_root: Path, case_id: str, *, state: str, image_sha: str | None,
                   evaluation_identity: str | None, with_files: bool = True,
                   result_verdict: str = "pass", prediction_input: dict | None = None,
                   send_attempted: bool | None = None, blocking_kind: str | None = None,
                   prediction_identity: str | None = None, producer_identity: str | None = None,
                   input_identity: str | None = None, page_id: str = "dev-plate-pocket") -> Path:
    """Sahte attempt klasörü — **gerçek** kimliklerle (kanıt zinciri eşitlik denetler).

    `prediction_identity` verilirse manifest'e yazılan `prediction_input_identity` bilinçli olarak
    bozulur (sapma testleri); varsayılan, kaydın yeniden hesaplanan kimliğidir.
    """
    directory = report_root / "attempts" / case_id / "attempt-0001"
    directory.mkdir(parents=True, exist_ok=True)
    attempt_id = f"{case_id}/{directory.name}"
    arm = case_id.rsplit("-", 1)[1]
    page = _page(page_id)
    identity = pilot.prediction_input_identity(prediction_input)
    manifest = {"schema": "semread-001b-attempt/2", "attempt_id": attempt_id, "case_id": case_id,
                "page_id": page_id, "arm": arm, "phase": "dev", "split": "dev",
                "code_identity": pilot.code_identity(),
                "producer_identity": (producer_identity if producer_identity is not None
                                      else pilot.producer_identity()),
                "input_identity": (input_identity if input_identity is not None
                                   else pilot.input_identity(page)),
                "model": pilot.MODEL, "model_identity": pilot.model_identity(),
                "expected_digest": pilot.EXPECTED_DIGEST, "runtime": pilot.EXPECTED_RUNTIME,
                "request_manifest_sha256": "req-manifest-hash",
                "page_png_sha256": image_sha, "evaluation_identity": evaluation_identity,
                "prediction_input_state": ("recorded" if prediction_input
                                           else "not_applicable_no_model_input"),
                "prediction_input_identity": (prediction_identity if prediction_identity is not None
                                              else identity)}
    if not with_files:
        return directory
    sent = send_attempted if send_attempted is not None else arm != "D"
    result = {"verdict": result_verdict, "arm": arm, "state": state, "send_attempted": sent,
              "prediction_input_identity": identity}
    if blocking_kind:
        result["blocking_kind"] = blocking_kind
    files: dict[str, object] = {"manifest.json": manifest, "prompt.txt": "istem",
                                "request-manifest.json": {}, "result.json": result}
    if prediction_input is not None:
        files["prediction-input.json"] = prediction_input
    index = {"schema": "semread-001b-artifact-index/1", "files": []}
    for name, payload in files.items():
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        (directory / name).write_text(text, encoding="utf-8")
        index["files"].append({"path": name, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                               "bytes": len(text.encode())})
    index["count"] = len(index["files"])
    (directory / "artifact-index.json").write_text(json.dumps(index), encoding="utf-8")
    return directory


def _history_row(directory: Path, *, case_id: str, arm: str, page_id: str,
                 state: str = "pass", evaluation_identity: str | None = None,
                 page_png_sha256: str | None = None,
                 prediction_input_identity: str | None = None,
                 producer_identity: str | None = None) -> dict:
    return {"attempt_id": f"{case_id}/{directory.name}", "directory": str(directory),
            "arm": arm, "page_id": page_id, "split": "dev", "phase": "dev",
            "verdict": state, "state": state, "seconds": 1.0,
            "producer_identity": producer_identity or pilot.producer_identity(),
            "evaluation_identity": evaluation_identity,
            "prediction_input_identity": prediction_input_identity,
            "page_png_sha256": page_png_sha256}


def _state(report_root: Path, rows: list[dict], live_calls: list[dict] | None = None,
           key: str = "case") -> None:
    (report_root / "state.json").write_text(
        json.dumps({"attempts": {key: rows}, "live_calls": live_calls or []}),
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


def test_a_zero_row_vs_d_without_measurement_cannot_close_the_gate():
    """001D dersi: `vs_d` boş olmayabilir, ama satırlar **sıfırsa** ölçüm yoktur → kapı kapanmaz.

    001B defterindeki attempt'ler `semread-candidates/1` sözleşmesine bağlıdır; güncel üretici/şema
    kimliğiyle yeniden seçilemedikleri için `aggregates` boş kalır ve hiçbir kol puanlanmaz. Bu
    durumda işaretler tam olsa bile `measured` false olmalıdır (aksi halde B06 ölçümsüz kapanırdı).
    Ölçüm ölçütü tek kaynaktır: `arms_with_measurement`.
    """
    text = " ".join(needle for _, needle in pilot.REPORT_MARKERS)
    zero_rows = {"aggregates": {},
                 "comparison": {"vs_d": {"V": {"predicate_rows": [{"scorable_target_count": 0}]}}}}
    checks = pilot.report_evidence(text, zero_rows)
    assert checks["missing"] == []
    assert pilot.arms_with_measurement(zero_rows) == []
    assert checks["measured"] is False, "sıfır satırlı vs_d ölçüm sayılamaz"
    assert checks["complete"] is False
    scored = {"aggregates": {},
              "comparison": {"vs_d": {"D": {"predicate_rows": [{"scorable_target_count": 2}]}}}}
    assert pilot.arms_with_measurement(scored) == ["D"]
    assert pilot.report_evidence(text, scored)["measured"] is True


def test_the_report_carries_every_required_section_on_the_real_payload(monkeypatch):
    """Gerçek rapor §19'un bütün işaretlerini taşır; kapı yalnız ölçüm varsa kapanır.

    Test **lab'ı yazmaz**: `evaluate()` normalde `evaluations/<run_id>/` klasörü açar; burada o
    yazım etkisizleştirilir (kanıt klasörleri yalnız gerçek koşularda oluşmalı).
    """
    monkeypatch.setattr(pilot, "write_evaluation_artifacts",
                        lambda *args, **kwargs: {"skipped": "test"})
    payload = pilot.evaluate(write_report=False)
    text = pilot.render_report(payload)
    checks = pilot.report_evidence(text, payload)
    assert checks["missing"] == []
    assert "yüklem bazında" in text and "Matris hücreleri" in text
    # Ölçüm varlığı lab durumuna bağlıdır (dev D koşusu yapıldıysa vardır); kapı bu ölçüme
    # bağlı olmalı: işaretler tam olduğu için `complete` yalnız `measured`a eşittir.
    assert checks["complete"] is checks["measured"]
    assert checks["measured"] == bool(payload["aggregates"])
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

def _png(tmp_path, monkeypatch, data: bytes = b"png-bytes") -> str:
    """Sayfa PNG'sini geçici köke koy ve sha256'sını döndür (PAGES_DIR yamalanır)."""
    (tmp_path / f"{_page()['page_id']}.png").write_bytes(data)
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path)
    return hashlib.sha256(data).hexdigest()


def _fresh_chain_inputs(lab, *, image_sha=None, evaluation_identity=None,
                        with_files=True, result_verdict="pass", arm="D", **attempt_kwargs):
    """Seçili bir hücre + geçmiş kaydı kur (varsayılan D: model girdisi yok)."""
    page_id = "dev-plate-pocket"
    case_id = f"{page_id}-{arm}"
    identity = evaluation_identity if evaluation_identity is not None else pilot.evaluation_identity()
    directory = _write_attempt(lab, case_id, state="pass", image_sha=image_sha,
                               evaluation_identity=identity, with_files=with_files,
                               result_verdict=result_verdict, page_id=page_id, **attempt_kwargs)
    row = _history_row(directory, case_id=case_id, arm=arm, page_id=page_id,
                       evaluation_identity=identity, page_png_sha256=image_sha,
                       prediction_input_identity=attempt_kwargs.get("prediction_input")
                       and pilot.prediction_input_identity(attempt_kwargs["prediction_input"]))
    sent = arm != "D" and attempt_kwargs.get("send_attempted", True) is not False
    calls = ([{"attempt_dir": str(directory), "attempt_id": row["attempt_id"], "arm": arm,
               "phase": "dev", "split": "dev", "send_state": "sent"}] if sent else [])
    _state(lab, [row], live_calls=calls, key=case_id)
    return _cell(page_id, arm, directory)


# Gerçek şemada bir hazırlanmış girdi kaydı (V kolu).
PREDICTION_RECORD = {"schema": pilot.PREDICTION_INPUT_SCHEMA, "contract_version": "contract-1",
                     "page_id": "dev-plate-pocket", "arm": "V", "arm_input_variant": "V",
                     "evidence_mode": "none", "prompt_sha256": "a" * 64,
                     "images": [{"order": 0, "image_id": "image-1", "sha256": "b" * 64,
                                 "bytes": 4096}],
                     "observation_table_sha256": None, "preprocessing_identity": "c" * 64}


def test_a_complete_chain_verifies_hashes_and_identity(lab, tmp_path, monkeypatch):
    """Sağlam zincir: geçmiş kaydı + artifact hash'leri + kimlik + sonuç halkaları tamdır (§20)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is True
    assert chain["checked_cells"] == 1
    assert chain["cells"][0]["gaps"] == []
    assert chain["cells"][0]["checks"]["budget_record"] is None, "D kolu bütçe harcamaz"
    assert chain["cells"][0]["checks"]["prediction_input_identity"] is None, \
        "D kolu modele görüntü/prompt göndermez: model girdisi not_applicable (PLAN-7 §4)"
    assert chain["evaluation_run"]["ok"] is True


def test_a_tampered_artifact_breaks_the_chain(lab, tmp_path, monkeypatch):
    """Artifact içeriği değiştirilirse hash tutmaz ve hücre kabul edilmez (§20)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    (Path(cell["attempt"]) / "result.json").write_text("{}", encoding="utf-8")
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "artifact_index" in chain["cells"][0]["gaps"]


def test_a_changed_input_image_breaks_the_chain(lab, tmp_path, monkeypatch):
    """Girdi görüntüsü değişirse kayıtlı sha256 tutmaz: zincir koptu (§20)."""
    _png(tmp_path, monkeypatch, b"new-bytes")
    cell = _fresh_chain_inputs(lab, image_sha=hashlib.sha256(b"png-bytes").hexdigest())
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "input_identity" in chain["cells"][0]["gaps"]


# ------------------------------------------- PLAN-7 §3: kimlik sahipliği (AUDIT-FIX-1)


def test_an_old_attempt_evaluation_identity_is_only_informational_drift(lab, tmp_path, monkeypatch):
    """PLAN-7 §3: attempt'in yaratılış-anı kimliği tahmini geçersiz kılmaz, yalnız sapma olarak yazılır."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, evaluation_identity="bayat-kimlik")
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is True and chain["cells"][0]["gaps"] == []
    drift = chain["attempt_evaluation_identity_drift"]
    assert len(drift) == 1 and drift[0]["page_id"] == "dev-plate-pocket"
    assert drift[0]["attempt_evaluation_identity_at_creation"] == "bayat-kimlik"
    assert drift[0]["current_evaluation_identity"] == pilot.evaluation_identity()
    assert chain["cells"][0]["attempt_evaluation_identity_at_creation"] == "bayat-kimlik"
    assert chain["evaluation_run"]["selected_source"] == "verilmedi"


def test_b07_closes_when_the_run_owns_the_identity(lab, tmp_path, monkeypatch):
    """PLAN-7 §26: yalnız evaluator değiştiğinde ham attempt geçerli kalır ve B07 kapanabilir."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, evaluation_identity="eski-evaluator")
    payload = {"evidence_chain": pilot.evidence_chain_report([cell]),
               "lifecycle": {"ok": True}, "budget": {"by_arm": {}}, "aggregates": {"D": {}},
               "attempt_evaluation_identity_drift": [{"arm": "D"}],
               "matrix_dispositions": {"complete": True}, "comparison": {"vs_d": {}},
               "report_checks": {"complete": True}, "match_policy": {"version": "x"},
               "reference_status": {}}
    rows = pilot.acceptance_rows(payload)
    assert rows["B07"]["status"] == "closed", "attempt kimliği sapması B07'yi açmamalı"
    assert "sapması" in rows["B07"]["detail"]
    payload["evidence_chain"]["evaluation_run"]["ok"] = False
    payload["evidence_chain"]["complete"] = False
    assert pilot.acceptance_rows(payload)["B07"]["status"] == "open"


def test_a_stale_evaluation_identity_in_the_run_payload_opens_the_chain(lab, tmp_path, monkeypatch):
    """Koşunun kendi kimliği bayatsa zincir kapanmaz (kimlik sahibi koşudur)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    run_id = pilot.evaluation_run_id([cell["attempt"]])
    chain = pilot.evidence_chain_report([cell], {"evaluation_identity": "bayat-kimlik",
                                                 "evaluation_run_id": run_id})
    assert "payload_evaluation_identity" in chain["evaluation_run"]["gaps"]
    assert chain["complete"] is False


def test_the_run_payload_must_bind_the_selected_attempts(lab, tmp_path, monkeypatch):
    """Koşu kimliği + seçili attempt kanıtı güncel değerlendiriciyle uyuşmalı (PLAN-7 §5)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    selected = pilot.selected_attempts_payload([cell], "yanlis-kosu")
    selected["evaluation_identity"] = "bayat-kimlik"
    chain = pilot.evidence_chain_report([cell], {"evaluation_identity": pilot.evaluation_identity(),
                                                 "evaluation_run_id": "yanlis-kosu",
                                                 "selected_attempts": selected})
    gaps = chain["evaluation_run"]["gaps"]
    assert {"payload_evaluation_run_id", "selected_attempts_identity",
            "selected_attempts_run_id"} <= set(gaps)
    assert chain["complete"] is False
    # Seçili artifact bağı da hücre bazında denetlenir.
    assert chain["cells"][0]["checks"]["selected_artifact"] is True


def test_the_selected_attempt_evidence_must_cover_exactly_the_cells(lab, tmp_path, monkeypatch):
    """Seçili-attempt kanıtı hücrelerle birebir örtüşmeli; eksik kayıt zinciri açar."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha)
    other = {"page_id": "dev-plate-pocket", "arm": "V", "cell": "to_run", "split": "dev",
             "attempt": str(lab / "attempts" / "baska" / "attempt-0001")}
    selected = pilot.selected_attempts_payload([other], pilot.evaluation_run_id([other["attempt"]]))
    chain = pilot.evidence_chain_report([cell], {"evaluation_identity": pilot.evaluation_identity(),
                                                 "evaluation_run_id": selected["evaluation_run_id"],
                                                 "selected_attempts": selected})
    assert "selected_attempts_cover_cells" in chain["evaluation_run"]["gaps"]
    assert chain["cells"][0]["checks"]["selected_artifact"] is False


# ------------------------------------------- PLAN-7 §4: gerçek model girdisi (AUDIT-FIX-2)


def test_a_sent_live_attempt_proves_its_prepared_model_input(lab, tmp_path, monkeypatch):
    """V/VE'de B07 kanıtı sayfa PNG'si değil **gerçek hazırlanmış girdi** kaydıdır (PLAN-7 §4)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, arm="V", prediction_input=dict(PREDICTION_RECORD))
    chain = pilot.evidence_chain_report([cell])
    checks = chain["cells"][0]["checks"]
    assert chain["complete"] is True and chain["cells"][0]["gaps"] == []
    assert checks["prediction_input_artifact"] is True
    assert checks["prediction_input_identity"] is True
    assert checks["input_identity"] is True, "sayfa PNG'si yalnız meta veri olarak kalır"


def test_a_tampered_prediction_input_opens_the_chain(lab, tmp_path, monkeypatch):
    """`prediction-input.json` değişirse yeniden hesaplanan kimlik kayıtlı alanlarla tutmaz."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, arm="V", prediction_input=dict(PREDICTION_RECORD))
    directory = Path(cell["attempt"])
    (directory / "prediction-input.json").write_text(
        json.dumps({**PREDICTION_RECORD, "prompt_sha256": "d" * 64}), encoding="utf-8")
    chain = pilot.evidence_chain_report([cell])
    assert chain["complete"] is False
    assert "prediction_input_identity" in chain["cells"][0]["gaps"]


def test_a_tampered_manifest_prediction_identity_opens_the_chain(lab, tmp_path, monkeypatch):
    """Manifest/result alanları bozulursa zincir kapanmaz (alanlar eşitlikle denetlenir)."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, arm="V", prediction_input=dict(PREDICTION_RECORD))
    manifest_path = Path(cell["attempt"]) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["prediction_input_identity"] = "baska-kimlik"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    chain = pilot.evidence_chain_report([cell])
    assert "prediction_input_identity" in chain["cells"][0]["gaps"]


def test_a_missing_prediction_input_artifact_opens_the_chain(lab, tmp_path, monkeypatch):
    """Gönderilmiş V/VE attempt'inde hazırlanmış girdi kaydı yoksa kanıt kurulamaz (fail-closed)."""
    sha = _png(tmp_path, monkeypatch)
    record = dict(PREDICTION_RECORD)
    cell = _fresh_chain_inputs(lab, image_sha=sha, arm="V", prediction_input=record)
    directory = Path(cell["attempt"])
    (directory / "prediction-input.json").unlink()
    index_path = directory / "artifact-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["files"] = [row for row in index["files"] if row["path"] != "prediction-input.json"]
    index["count"] = len(index["files"])
    index_path.write_text(json.dumps(index), encoding="utf-8")
    chain = pilot.evidence_chain_report([cell])
    checks = chain["cells"][0]["checks"]
    assert chain["complete"] is False
    assert checks["prediction_input_artifact"] is False
    assert "prediction_input_identity" in chain["cells"][0]["gaps"]


def test_an_unsent_live_attempt_proves_its_local_block_instead(lab, tmp_path, monkeypatch):
    """Gönderilmemiş attempt'te model girdisi yoktur: kanıtlanan şey yerel ret/engel kaydıdır."""
    sha = _png(tmp_path, monkeypatch)
    cell = _fresh_chain_inputs(lab, image_sha=sha, arm="V", send_attempted=False,
                               blocking_kind="budget")
    chain = pilot.evidence_chain_report([cell])
    checks = chain["cells"][0]["checks"]
    assert chain["complete"] is True
    assert checks["prediction_input_identity"] is None
    assert checks["no_dispatch_evidence"] is True
    assert checks["budget_record"] is None


def test_a_gold_change_does_not_invalidate_a_valid_d_attempt(lab, tmp_path, monkeypatch):
    """PLAN-7 §13/§26: evaluator/gold değişimi geçerli ham D tahminini bayatlatmaz, rerun istemez."""
    sha = _png(tmp_path, monkeypatch)
    directory = _write_attempt(lab, "dev-plate-pocket-D", state="pass", image_sha=sha,
                               evaluation_identity="eski-evaluator")
    (directory / "response-parsed.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_schema"] = pilot.CANDIDATE_SCHEMA_VERSION
    manifest["source"] = {"sha256": hashlib.sha256(
        (pilot.ROOT / _page()["path"]).read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    _state(lab, [_history_row(directory, case_id="dev-plate-pocket-D", arm="D",
                              page_id="dev-plate-pocket", state="pass",
                              evaluation_identity="eski-evaluator", page_png_sha256=sha)],
           key="dev-plate-pocket-D")
    reused = pilot.reusable_d_attempt(_page())
    assert reused is not None and reused["directory"] == str(directory), \
        "gold/evaluator değişimi D tahminini yeniden koşmaya zorlamamalı"


def test_an_empty_chain_is_not_complete(lab):
    """Seçili hücre yoksa zincir boştur ve kabul edilmez: B07 kanıtsız kapanamaz (§20)."""
    chain = pilot.evidence_chain_report([_cell("dev-plate-pocket", "V", None)])
    assert chain["checked_cells"] == 0
    assert chain["vacuous"] is True
    assert chain["complete"] is False


def test_b05_and_b07_stay_open_without_selected_attempts(lab, monkeypatch):
    """Gerçek lab durumu: hücreler koşulmamışken B05 ve B07 açık kalır (uydurma kanıt yok)."""
    monkeypatch.setattr(pilot, "write_evaluation_artifacts",
                        lambda *args, **kwargs: {"skipped": "test"})
    payload = pilot.evaluate(write_report=False)
    acceptance = pilot.acceptance_rows(payload)
    assert acceptance["B05"]["status"] == "open"
    assert acceptance["B07"]["status"] == "open"
    assert "açık hücreler" in acceptance["B05"]["detail"]


def test_b06_requires_a_scored_arm_not_just_a_key():
    """§19: `vs_d` satırları boş da olabilir; puanlanmış kol yoksa B06 açık kalır."""
    empty = {"aggregates": {"D": {"localization_match_rate": 1.0}},
             "comparison": {"vs_d": {"V": {"predicate_rows": [
                 {"predicate": "size", "scorable_target_count": 0, "recovered_count": 0,
                  "regressed_wrong_count": 0, "regressed_abstention_count": 0,
                  "net_correct_gain": 0, "examples": []}]}}},
             "report_checks": {"complete": True}, "budget": {"by_arm": {}},
             "lifecycle": {"ok": True}, "match_policy": {"version": "x"},
             "reference_status": {}, "matrix_dispositions": {"complete": True},
             "attempt_evaluation_identity_drift": [], "evidence_chain": {"complete": True}}
    assert pilot.acceptance_rows(empty)["B06"]["status"] == "open", "ölçümsüz kol kapıyı açmaz"

    measured = {**empty, "comparison": {"vs_d": {"V": {"predicate_rows": [
        {"predicate": "size", "scorable_target_count": 2, "recovered_count": 1,
         "regressed_wrong_count": 0, "regressed_abstention_count": 1, "net_correct_gain": 0,
         "examples": []}]}}}}
    acceptance = pilot.acceptance_rows(measured)
    assert acceptance["B06"]["status"] == "closed"
    assert "V" in acceptance["B06"]["detail"]


def test_the_handoff_document_exists_and_names_the_acceptance_gates():
    """B05/B06/B07 adları devir notunda geçer (kapıların izlenebilirliği)."""
    handoff = ROOT / "docs" / "HERMES_SEMREAD_001B_HANDOFF.md"
    text = handoff.read_text(encoding="utf-8")
    for gate in ("B05", "B06", "B07"):
        assert gate in text
