"""SEMREAD-001B — P0R-FINAL-A/B: total attempt lifecycle and attempt/inference ledger separation.

Bu testler **hiç model çağırmaz**: taşıma yolu taklit edilir, tüm yazma yolları geçici köke taşınır.
İki kalıcı kural sınanır:

* A — her `attempts/<vaka>/attempt-NNNN/` klasörü için **tam olarak bir** geçmiş kaydı olur ve aynı
  `attempt_id` iki kez sonuçlandırılamaz (yerel hata yolları dahil).
* B — gönderilmeyeceği kanıtlanabilen yerel/preflight retleri attempt defterine yazılır ama inference
  bütçesini **harcamaz**; gerçek gönderim ve gönderimi belirsiz kalan deneme tam bir slot harcar.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_module_lifecycle",
                                                  ROOT / "eval/semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pilot sürücüsü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()

PAGE = {"page_id": "page", "split": "dev", "group": "g", "path": "pyproject.toml",
        "type": "raster", "source_sha256": "a" * 64}


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Bütün yazma yollarını geçici köke taşı: gerçek koşu kaydı bu testlerde değişmez."""
    monkeypatch.setattr(pilot, "REPORT_ROOT", tmp_path)
    monkeypatch.setattr(pilot, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", tmp_path / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(pilot, "PREPARED_INPUT_DIR", tmp_path / "prepared")
    monkeypatch.setattr(pilot, "CORPUS_DIR", tmp_path / "corpus")
    monkeypatch.setattr(pilot, "GOLD_DIR", tmp_path / "corpus" / "gold")
    (tmp_path / "pages").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pages" / "page.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"p" * 32)
    return tmp_path


class _Image:
    """Hazırlanmış görüntü yerine geçen minimal nesne (gerçek PNG byte'ı taşımaz)."""

    def __init__(self, image_id: str, png: bytes) -> None:
        self.image_id = image_id
        self.png = png


def _bundle(arm: str = "V") -> dict:
    return {"arm": arm, "images": [_Image("image-1", b"raw-page")], "observations": [],
            "arm_input_variant": arm, "evidence_mode": pilot.arm_evidence_mode(arm)}


class _Model:
    def __init__(self, digest: str) -> None:
        self.digest = digest

    def as_dict(self) -> dict:
        return {"model": pilot.MODEL, "digest": self.digest, "quantization": "test"}


@pytest.fixture()
def local_only(monkeypatch, sandbox):
    """Yerel adımları taklit et: ağ ve OCR yok, hazırlama sabit."""
    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe", lambda _path: object())
    monkeypatch.setattr(pilot, "prepare_arm_inputs", lambda *_a, **_k: _bundle())
    monkeypatch.setattr(pilot, "candidate_prompt", lambda *_a, **_k: "görev")
    monkeypatch.setattr(pilot, "installed_models", lambda: [])
    monkeypatch.setattr(pilot, "find_model", lambda _installed, _name: _Model(pilot.EXPECTED_DIGEST))
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {"version": pilot.EXPECTED_RUNTIME, "model": {}, "error": None})
    return sandbox


def _answered(*, parse_ok: bool = True, transport: bool = False) -> dict:
    return {"arm": "V", "outcome": "error" if transport else "answered",
            "failure_kind": "unreachable" if transport else None,
            "parse": {"ok": parse_ok, "error": None if parse_ok else "bozuk JSON"},
            "references": {"ok": True, "coverage": {"exact": True}},
            "truncated": {"done_reason": "stop", "state": "complete"},
            "leakage": [], "images": [], "stats": {"done_reason": "stop", "eval_count": 3,
                                                   "prompt_eval_count": 9},
            "request": {"model": pilot.MODEL}, "raw_response": "{}", "parsed": {"items": []}}


def _history(case_id: str) -> list[dict]:
    records = pilot.load_state().get("attempts", {}).get(case_id) or []
    return records if isinstance(records, list) else [records]


def _dirs(case_id: str) -> list[Path]:
    return [path for path in pilot.attempt_root(case_id).glob("attempt-*") if path.is_dir()]


# ------------------------------------------------------------ A: yaşam döngüsü toplam mı


def test_source_observe_and_preparation_failures_each_finalize_once(local_only, monkeypatch):
    """`open_source`/`observe`/`prepare_arm_inputs` hataları tek kayıtla kapanmalı (P0R-FINAL-A)."""
    monkeypatch.setattr(pilot, "open_source",
                        lambda _path: (_ for _ in ()).throw(RuntimeError("kaynak yok")))
    source_out = pilot.write_live_attempt(PAGE, "V", phase="dev")

    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe",
                        lambda _path: (_ for _ in ()).throw(RuntimeError("OCR çöktü")))
    observe_out = pilot.write_live_attempt(PAGE, "V", phase="dev")

    monkeypatch.setattr(pilot, "observe", lambda _path: object())
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("paket kurulamadı")))
    preparation_out = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert [row["state"] for row in _history("page-V")] == \
        ["local_error_source", "local_error_observe", "local_error_preparation"]
    assert [out["verdict"] for out in (source_out, observe_out, preparation_out)] == \
        ["fail", "fail", "fail"]
    for out in (source_out, observe_out, preparation_out):
        result = json.loads((Path(out["directory"]) / "result.json").read_text(encoding="utf-8"))
        assert result["send_attempted"] is False and result["inference_calls"] == 0
        assert result["local_error"], "yerel hata kayda geçmeli"
    assert pilot.budget_report()["total_used"] == 0, "yerel hata inference harcamamalı"
    assert pilot.budget_report()["legacy_non_dispatch_records"] == 0
    assert pilot.attempt_lifecycle_report()["ok"] is True


def test_d_arm_source_and_observe_failures_each_finalize_once(local_only, monkeypatch):
    """D kolunda da kaynak/gözlem hatası tam bir geçmiş kaydı bırakır (P0R-FINAL-A, §3)."""
    monkeypatch.setattr(pilot, "open_source",
                        lambda _path: (_ for _ in ()).throw(RuntimeError("kaynak yok")))
    source_out = pilot.write_d_attempt(PAGE)

    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe",
                        lambda _path: (_ for _ in ()).throw(RuntimeError("OCR çöktü")))
    observe_out = pilot.write_d_attempt(PAGE)

    assert [row["state"] for row in _history("page-D")] == ["local_error_source",
                                                            "local_error_observe"]
    assert [out["verdict"] for out in (source_out, observe_out)] == ["fail", "fail"]
    assert pilot.budget_report()["total_used"] == 0
    assert pilot.attempt_lifecycle_report()["ok"] is True
    assert len(_dirs("page-D")) == len(_history("page-D")) == 2


def test_model_discovery_failure_and_missing_model_each_finalize_once(local_only, monkeypatch):
    monkeypatch.setattr(pilot, "find_model",
                        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("ollama kapalı")))
    raised = pilot.write_live_attempt(PAGE, "V", phase="dev")
    monkeypatch.setattr(pilot, "find_model", lambda *_a, **_k: None)
    missing = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert [row["state"] for row in _history("page-V")] == \
        ["blocked_model_discovery", "blocked_model_discovery"]
    assert raised["verdict"] == "fail" and missing["verdict"] == "fail"
    report = pilot.budget_report()
    assert report["total_used"] == 0 and report["by_send_state"] == {}
    assert report["attempt_ledger"]["total"] == 2


@pytest.mark.parametrize("case,expected_state,expected_verdict", [
    ("model_mismatch", "blocked_model_mismatch", "fail"),
    ("runtime_mismatch", "blocked_runtime_mismatch", "blocked"),
    ("unsupported_setting", "blocked_unsupported_setting", "blocked"),
])
def test_known_pre_send_failures_consume_zero_inference_budget(local_only, monkeypatch, case,
                                                              expected_state, expected_verdict):
    """Bilinen uyuşmazlık/ret: attempt defteri +1, inference bütçesi +0 (P0R-FINAL-B)."""
    if case == "model_mismatch":
        monkeypatch.setattr(pilot, "find_model", lambda *_a, **_k: _Model("f" * 64))
    elif case == "runtime_mismatch":
        monkeypatch.setattr(pilot, "runtime_identity",
                            lambda: {"version": "0.31.0", "model": {}, "error": None})
    else:
        monkeypatch.setitem(pilot.SETTINGS, "top_k", 7)
    try:
        before_attempts = pilot.budget_report()["attempt_ledger"]["total"]
        outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")
    finally:
        pilot.SETTINGS.pop("top_k", None)

    assert outcome["state"] == expected_state and outcome["verdict"] == expected_verdict
    report = pilot.budget_report()
    assert report["total_used"] == 0, "gönderilmeyen istek inference sayılmamalı"
    assert report["by_send_state"] == {}
    assert report["legacy_non_dispatch_records"] == 0
    assert report["attempt_ledger"]["total"] == before_attempts + 1
    assert report["attempt_ledger"]["dispatched"] == 0
    assert pilot.attempt_lifecycle_report()["ok"] is True


def test_a_real_send_consumes_exactly_one_inference_slot(local_only, monkeypatch):
    monkeypatch.setattr(pilot, "read_page", lambda *_a, **_k: _answered())
    outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert outcome["verdict"] == "pass"
    report = pilot.budget_report()
    assert report["total_used"] == 1 and report["dev_used"] == 1
    assert report["by_send_state"] == {"sent": 1}
    assert report["attempt_ledger"]["by_state"] == {"pass": 1}
    assert report["attempt_ledger"]["dispatched"] == 1
    record = pilot.load_state()["live_calls"][0]
    assert record["attempt_id"] == "page-V/attempt-0001"
    assert record["reserved_at"] and record["sent_at"], "rezervasyon ve gönderim zamanı yazılmalı"


def test_an_uncertain_dispatch_consumes_one_slot_and_is_recorded_as_transport_error(local_only,
                                                                                   monkeypatch):
    def boom(*_a, **_k):
        raise TimeoutError("yanıt gelmedi")

    monkeypatch.setattr(pilot, "read_page", boom)
    outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert outcome["state"] == "transport_error" and outcome["verdict"] == "fail"
    report = pilot.budget_report()
    assert report["total_used"] == 1, "gönderilmiş ama yanıtı belirsiz istek bütçede kalmalı"
    assert report["by_send_state"] == {"dispatch_uncertain": 1}
    assert _history("page-V")[-1]["state"] == "transport_error"
    result = json.loads((Path(outcome["directory"]) / "result.json").read_text(encoding="utf-8"))
    assert result["send_attempted"] is True and result["inference_calls"] == 1


def test_a_budget_refusal_is_recorded_without_spending_more(local_only):
    for index in range(pilot.LIVE_CALL_LIMIT_DEV):
        pilot.reserve_live_call(f"dev-{index}-V", phase="dev", arm="V", split="dev",
                                attempt_dir=pilot.REPORT_ROOT / "a",
                                attempt_id=f"dev-{index}-V/attempt-0001")
    outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert outcome["verdict"] == "blocked" and outcome["state"] == "blocked_budget"
    report = pilot.budget_report()
    assert report["total_used"] == pilot.LIVE_CALL_LIMIT_DEV, "reddedilen istek tavanı aşmamalı"
    assert report["attempt_ledger"]["by_state"] == {"blocked_budget": 1}


def test_a_dispatched_timeout_inside_the_transport_is_counted_once(local_only, monkeypatch):
    monkeypatch.setattr(pilot, "read_page", lambda *_a, **_k: _answered(transport=True))
    outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert outcome["state"] == "transport_error"
    report = pilot.budget_report()
    assert report["total_used"] == 1 and report["by_send_state"] == {"transport_unreachable": 1}


def test_a_parse_failure_is_a_dispatched_attempt(local_only, monkeypatch):
    monkeypatch.setattr(pilot, "read_page", lambda *_a, **_k: _answered(parse_ok=False))
    outcome = pilot.write_live_attempt(PAGE, "V", phase="dev")

    assert outcome["state"] == "parse_error" and outcome["verdict"] == "fail"
    assert pilot.budget_report()["by_send_state"] == {"sent": 1}


# ------------------------------------------------------------ A: tek kayıt, tek sonuç


def test_finalizing_the_same_attempt_twice_is_impossible(sandbox, monkeypatch):
    directory = pilot.new_attempt_dir("page-V")
    attempt_id = f"page-V/{directory.name}"
    pilot.finalize_attempt(attempt_id=attempt_id, directory=directory, page=PAGE, arm="V",
                           phase="dev", state="pass", verdict="pass", send_attempted=True,
                           inference_calls=1)
    with pytest.raises(pilot.AttemptFinalizedError):
        pilot.finalize_attempt(attempt_id=attempt_id, directory=directory, page=PAGE, arm="V",
                               phase="dev", state="failed_gates", verdict="fail",
                               send_attempted=True, inference_calls=1)
    assert len(_history("page-V")) == 1, "ikinci sonuçlandırma kayıt eklememeli"


def test_an_unknown_state_is_refused(sandbox):
    directory = pilot.new_attempt_dir("page-V")
    with pytest.raises(ValueError):
        pilot.finalize_attempt(attempt_id=f"page-V/{directory.name}", directory=directory,
                               page=PAGE, arm="V", phase="dev", state="her şey yolunda",
                               verdict="pass", send_attempted=False, inference_calls=0)


def test_lifecycle_report_flags_an_orphan_attempt_directory(sandbox):
    directory = pilot.new_attempt_dir("page-V")
    orphan = pilot.new_attempt_dir("page-V")
    pilot.finalize_attempt(attempt_id=f"page-V/{directory.name}", directory=directory, page=PAGE,
                           arm="V", phase="dev", state="pass", verdict="pass",
                           send_attempted=True, inference_calls=1)
    (orphan / "result.json").write_text("{}", encoding="utf-8")     # kaydı olmayan klasör

    report = pilot.attempt_lifecycle_report()
    assert report["ok"] is False
    assert report["orphan_attempts"] == [f"page-V/{orphan.name}"]


def test_lifecycle_reports_a_history_row_whose_evidence_is_gone(local_only):
    """Kanıt klasörü silinmiş kayıt ayrı raporlanır: kanıt zincirine giremez (PLAN-5 §20/§32)."""
    directory = pilot.new_attempt_dir("page-V")
    out = pilot.finalize_attempt(attempt_id=f"page-V/{directory.name}", directory=directory,
                                 page=PAGE, arm="V", phase="dev", state="pass", verdict="pass",
                                 send_attempted=True, inference_calls=1)
    assert pilot.attempt_lifecycle_report()["rows_without_directory"] == []

    shutil.rmtree(out["directory"])
    report = pilot.attempt_lifecycle_report()
    assert report["rows_without_directory"] == [out["attempt_id"]]
    assert report["ok"] is True, "klasörsüz kayıt sözleşme ihlali değil; yalnız kanıt zincirinde yok"
    assert report["attempt_directories"] == 0 and report["history_rows"] == 1


def test_every_attempt_directory_has_exactly_one_history_row_in_a_mixed_run(local_only,
                                                                           monkeypatch):
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("hazırlık hatası")))
    pilot.write_live_attempt(PAGE, "V", phase="dev")
    monkeypatch.setattr(pilot, "prepare_arm_inputs", lambda *_a, **_k: _bundle())
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {"version": "0.31.0", "model": {}, "error": None})
    pilot.write_live_attempt(PAGE, "V", phase="dev")                 # runtime reddi
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {"version": pilot.EXPECTED_RUNTIME, "model": {}, "error": None})
    monkeypatch.setattr(pilot, "read_page", lambda *_a, **_k: _answered())
    pilot.write_live_attempt(PAGE, "V", phase="dev")                 # gerçek gönderim

    history = _history("page-V")
    directories = [path.name for path in _dirs("page-V")]
    assert len(directories) == len(history) == 3
    assert [row["state"] for row in history] == ["local_error_preparation",
                                                 "blocked_runtime_mismatch", "pass"]
    report = pilot.attempt_lifecycle_report()
    assert report["ok"] is True and report["orphan_attempts"] == []
    assert report["duplicate_attempt_ids"] == []
    assert report["unique_attempt_ids"] == report["history_rows"] == 3
    assert pilot.budget_report()["total_used"] == 1, "yalnız gerçek gönderim bütçe harcar"


def test_legacy_not_sent_records_are_reported_but_not_counted(sandbox):
    """P0R-FINAL-B öncesi kayıtlar silinmez ama artık inference sayılmaz."""
    state = pilot.load_state()
    state["live_calls"] = [{"case_id": "page-V", "arm": "V", "phase": "dev", "split": "dev",
                            "send_state": "not_sent_runtime_mismatch"}]
    pilot.save_state(state)
    report = pilot.budget_report()

    assert report["total_used"] == 0 and report["dev_used"] == 0
    assert report["by_send_state"] == {}
    assert report["legacy_non_dispatch_records"] == 1
    assert report["over_budget"] is False
    assert "sayılmaz" in report["counting_note"]
