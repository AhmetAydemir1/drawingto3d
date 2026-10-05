"""SEMREAD-001D — PLAN-15 §9–§15: run-contract `001d/1` kimliği + attempt manifest kimlik alanları.

Kapsam (0 inference; yalnız saf fonksiyonlar ve manifest kurulumu):

* `CONTRACT_VERSION = semread-001d-run-contract/1`; docstring current sözleşmeyi 001D
  (semantic-content-aware) anlatır, 001C tarihi closure artifact'ına işaret eder (§9);
* şema/reader `/3` yürürlükte; üretim zarfı 001C kapanış değerleriyle **birebir** (§10);
* dry-run attempt manifesti (çağrısız) güncel kimlikleri taşır: experiment = `semread-001d`,
  schema/reader `/3`, contract `001d/1`, producer + preprocessing identity (§12/§13); eski 001C
  kimliği manifeste **girmez**;
* producer identity, closure'da kayıtlı 001C kimliklerinden **farklıdır** (§12 "producer identity
  new");
* eski sözleşme kimliğiyle canlı gönderim bloklanır (`blocked_contract_identity` — §13).

Bu testler model çağırmaz; guard testi scratch kökte koşar ve gerçek deftere yazmaz.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    spec = importlib.util.spec_from_file_location("semread_001d_identity_pilot",
                                                  ROOT / "eval/semread_001b_pilot.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()

CLOSURE = ROOT / "eval" / "semread_001c_closure.json"
# PLAN-15 §32 Round 1 hücreleri: dry-run manifesti bu dört hücre için kurulur (çağrı yok).
ROUND1_CELLS = (("dev-plate-pocket", "V"), ("dev-plate-pocket", "VE"),
                ("dev-flange-book", "V"), ("dev-flange-book", "VE"))


def _closure() -> dict:
    assert CLOSURE.exists(), "001C closure artifact'ı izlenmeli (eval/semread_001c_closure.json)"
    return json.loads(CLOSURE.read_text(encoding="utf-8"))


def test_the_run_contract_identity_is_001d():
    from drawingto3d.semantic_run_contract import CONTRACT_VERSION

    assert CONTRACT_VERSION == "semread-001d-run-contract/1"
    # 001C sürümü artık yürürlükte değil — closure artifact'ında tarihsel kayıttır.
    assert CONTRACT_VERSION != "semread-001c-run-contract/1"


def test_the_module_docstring_describes_the_current_001d_contract():
    """PLAN-15 §9: docstring current sözleşmeyi 001D olarak anlatır; 001C history'siz değil."""
    import drawingto3d.semantic_run_contract as contract

    text = contract.__doc__ or ""
    assert "SEMREAD-001D" in text
    assert "semantic-content-aware" in text
    assert "semread_001c_closure.json" in text, "001C tarihi closure artifact'ına işaret edilmeli"


def test_schema_and_reader_consumed_by_the_contract_are_still_v3():
    from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION,
                                                 CANDIDATE_SCHEMA_VERSION)

    assert CANDIDATE_SCHEMA_VERSION == "semread-candidates/3"
    assert CANDIDATE_READER_VERSION == "semread-candidate-reader/3"


def test_the_generation_envelope_equals_the_001c_closure_values():
    """PLAN-15 §10/§11: zarf DEĞİŞMEZ — model/digest/runtime + ayarlar closure kaydıyla birebir."""
    from drawingto3d import semantic_run_contract as contract

    recorded = _closure()["identities"]["run_contract"]["settings"]
    assert contract.SETTINGS["num_ctx"] == recorded["num_ctx"] == 22528
    assert contract.SETTINGS["num_predict"] == recorded["num_predict"] == 8192
    assert contract.SETTINGS["temperature"] == recorded["temperature"] == 0.0
    assert contract.REPEAT_PENALTY == recorded["repeat_penalty"] == 1.25
    assert contract.REPEAT_LAST_N == recorded["repeat_last_n"] == 512
    assert contract.MODEL == "qwen3-vl:8b-instruct"
    assert contract.EXPECTED_RUNTIME == "0.32.1"
    assert contract.EXPECTED_DIGEST == \
        "0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319"
    # V==VE invariantı (§11): kollar arası tek izin verilen fark kanıt katmanıdır.
    assert contract.generation_settings("V") == contract.generation_settings("VE")


def test_the_dry_run_manifest_carries_only_current_identities(monkeypatch):
    """PLAN-15 §12/§13: çağrısız kurulan attempt manifesti güncel kimlik alanlarını taşır."""
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", "semread-001d")
    for page_id, arm in ROUND1_CELLS:
        page = next(row for row in pilot.PAGES if row["page_id"] == page_id)
        manifest = pilot._attempt_manifest(page, arm, attempt_id=f"{page_id}-{arm}/attempt-0001",
                                           phase="dev")
        assert manifest["experiment"] == "semread-001d"
        assert manifest["phase"] == "dev"
        assert manifest["schema_version"] == "semread-candidates/3"
        assert manifest["reader_version"] == "semread-candidate-reader/3"
        assert manifest["contract_version"] == "semread-001d-run-contract/1"
        assert manifest["producer_identity"] == pilot.producer_identity()
        assert manifest["preprocessing_identity"] == pilot.preprocessing_identity()
        blob = json.dumps(manifest)
        assert "semread-001c-run-contract" not in blob, "eski 001C kimliği manifeste giremez"
        assert "semread-candidates/2" not in blob, "eski şema kimliği manifeste giremez"
        assert "semread-candidate-reader/2" not in blob, "eski reader kimliği manifeste giremez"


def test_the_producer_identity_is_new_relative_to_the_001c_closure():
    """PLAN-15 §12: producer identity değişti — closure'da kayıtlı 001C kimlikleriyle aynı değil."""
    identities = _closure()["identities"]["producer_identity"]
    recorded = set(identities["groups"]) | {identities["value"]}
    assert pilot.producer_identity() not in recorded


def test_a_stale_contract_identity_blocks_the_send(tmp_path, monkeypatch):
    """PLAN-15 §13: eski 001C kimliği current attempt manifestinde görünürse gönderim bloklanır."""
    monkeypatch.setattr(pilot, "REPORT_ROOT", tmp_path)
    monkeypatch.setattr(pilot, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", tmp_path / "attempts")
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", "semread-001d")
    monkeypatch.setattr(pilot, "CONTRACT_VERSION", "semread-001c-run-contract/1")

    def must_not_send(*_args, **_kwargs):
        raise AssertionError("eski sözleşme kimliğiyle gönderim yapılmamalı")

    monkeypatch.setattr(pilot, "read_page", must_not_send)
    page = next(row for row in pilot.PAGES if row["page_id"] == "dev-plate-pocket")
    outcome = pilot.write_live_attempt(page, "V", phase="dev")
    assert outcome["verdict"] == "blocked" and outcome["state"] == "blocked_contract_identity"
    directory = Path(outcome["directory"])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract_version"] == "semread-001c-run-contract/1"
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["blocking_kind"] == "contract_identity"
    assert result["send_attempted"] is False and result["inference_calls"] == 0
    assert pilot.budget_report()["total_used"] == 0, "bloklu gönderim bütçe harcamamalı"
    history = pilot.load_state()["attempts"]["dev-plate-pocket-V"]
    assert history[-1]["state"] == "blocked_contract_identity"
    assert "blocked_contract_identity" in pilot.FINALIZED_STATES


def test_the_contract_identity_block_is_inert_without_a_declared_expectation(monkeypatch):
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", "semread-001b")
    assert pilot.contract_identity_block() is None
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", "semread-001d")
    assert pilot.contract_identity_block() is None, "güncel kimlikte blok yok"
    monkeypatch.setattr(pilot, "CONTRACT_VERSION", "semread-001c-run-contract/1")
    assert pilot.contract_identity_block() == {"experiment": "semread-001d",
                                               "expected": "semread-001d-run-contract/1",
                                               "found": "semread-001c-run-contract/1"}
