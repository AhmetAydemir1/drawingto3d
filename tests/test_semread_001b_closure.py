"""SEMREAD-001B — PLAN-12 §14 (P0): kapanış manifesti ve değişmezlik denetimi.

Kapsam:

* izlenen manifest (`eval/semread_001b_closure.json`) 001B kanıt zincirini (FREEZE.json, gold
  manifesti, final rapor, değerlendirme koşusu artifact'ları, bütçe defteri) hash'leriyle
  pinliyor mu;
* izlenen (git'te) artifact'lar diskteki dosyalarla birebir mi (her ortamda denetlenebilir);
* bu çalışma ağacında `--verify` tam geçiyor mu (`out/` bulunan ortam); temiz klonda yalnız
  `out/` dosyaları eksik olabilir — izlenenler asla;
* manifestteki bütçe sayısı state.json'dan yeniden hesaplanınca aynı mı (out/ varsa).

Testler gerçek dosyaları **yazmaz**.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001b_closure.py"
MANIFEST = ROOT / "eval" / "semread_001b_closure.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001b_closure", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _manifest() -> dict:
    assert MANIFEST.exists(), "kapanış manifesti izlenmeli (eval/semread_001b_closure.json)"
    return json.loads(MANIFEST.read_text())


def test_the_manifest_pins_the_001b_evidence_chain():
    manifest = _manifest()
    assert manifest["schema"] == "semread-001b-closure/1"
    assert manifest["experiment"]["status"] == "closed_as_recorded"
    paths = [row["path"] for row in manifest["artifacts"]]
    for relative in ("eval/semread_001b_gold/FREEZE.json",
                     "eval/semread_001b_gold/manifest.json",
                     "out/lab/semread-001b/final/report.md",
                     "out/lab/semread-001b/state.json"):
        assert relative in paths, relative
    run_id = manifest["evaluation_run_id"]
    assert f"out/lab/semread-001b/evaluations/{run_id}/selected-attempts.json" in paths
    assert f"out/lab/semread-001b/evaluations/{run_id}/acceptance.json" in paths


def test_tracked_artifacts_hash_match_everywhere():
    """İzlenen iki dosya her ortamda denetlenebilir; hash'ler birebir olmalı."""
    manifest = _manifest()
    rows = {row["path"]: row for row in manifest["artifacts"]}
    for relative in ("eval/semread_001b_gold/FREEZE.json",
                     "eval/semread_001b_gold/manifest.json"):
        row = rows[relative]
        assert row["tracked"] is True
        assert row["sha256"] == tool._sha256_file(ROOT / relative)


def test_identities_come_from_the_frozen_evidence():
    manifest = _manifest()
    freeze = json.loads((ROOT / "eval/semread_001b_gold/FREEZE.json").read_text())
    bindings = freeze["bindings"]
    assert manifest["identities"]["gold_content_identity"] == freeze["gold_content_identity"]
    assert manifest["identities"]["producer_identity"] == bindings["producer_identity"]
    assert manifest["identities"]["evaluation_identity"] == bindings["evaluation_identity"]
    assert manifest["identities"]["contract_version"] == bindings["contract_version"]
    assert manifest["identities"]["match_policy_version"] == \
        bindings["match_policy"]["version"]
    pointer = json.loads((ROOT / "out/lab/semread-001b/final/pointer.json").read_text()) \
        if (ROOT / "out/lab/semread-001b/final/pointer.json").exists() else None
    if pointer is not None:
        assert manifest["evaluation_run_id"] == pointer["evaluation_run_id"]


def test_verify_passes_where_the_lab_tree_exists():
    manifest = _manifest()
    result = tool.verify_manifest(manifest, ROOT)
    assert result["mismatched"] == [], f"001B artifact'ı değişmiş: {result['mismatched']}"
    # out/ git dışıdır: temiz klonda yalnız out/ yolları eksik olabilir; izlenenler asla.
    assert all(relative.startswith("out/") for relative in result["missing"])
    if not result["missing"]:
        assert result["ok"] is True
        assert result["checked"] == result["total"]


def test_verify_detects_a_changed_artifact():
    manifest = _manifest()
    tampered = json.loads(json.dumps(manifest))
    tampered["artifacts"][0]["sha256"] = "0" * 64
    result = tool.verify_manifest(tampered, ROOT)
    assert result["ok"] is False
    assert tampered["artifacts"][0]["path"] in [row["path"] for row in result["mismatched"]]
    missing_manifest = {"artifacts": [{"path": "eval/does-not-exist.json", "sha256": "0" * 64}]}
    result = tool.verify_manifest(missing_manifest, ROOT)
    assert result["ok"] is False and result["missing"] == ["eval/does-not-exist.json"]


def test_budget_summary_is_recomputable_from_the_ledger():
    """out/ bu ağaçtaysa manifest bütçesi state.json'dan birebir yeniden hesaplanır."""
    ledger = ROOT / "out/lab/semread-001b/state.json"
    if not ledger.exists():
        return
    manifest = _manifest()
    state = json.loads(ledger.read_text())
    summary = manifest["summary"]["budget"]
    expected = tool._budget_summary(state)
    assert summary["used"] == expected["used"]
    assert summary["by_send_state"] == expected["by_send_state"]
    assert manifest["summary"]["attempt_ledger"] == tool._attempt_ledger_summary(state)
