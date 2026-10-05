"""SEMREAD-001C — PLAN_SEMREAD_001D §9 (P0.8): closure manifesti ve değişmezlik denetimleri.

Kapsam:

* izlenen manifest (`eval/semread_001c_closure.json`) 001C kanıt zincirini (dokümanlar, gold
  FREEZE, bütçe defteri, tazelenmiş raporlar, 12 seçili dev attempt'i) hash'leriyle pinliyor mu;
* izlenen (git'te) artifact'lar diskteki dosyalarla birebir mi (her ortamda denetlenebilir);
* seçili attempt'ler "en yeni pass" kuralıyla mı seçilmiş (elbow-VE fallback 0003 dahil);
* kimlikler attempt manifestlerinden mi geliyor (7 paylaşımlı zarf + 4 D + 1 fallback grupları);
* requalification özeti (§8: valid 7/8, stop 8/8, paylaşımlı ayar 8/8) defterden yeniden
  türetilebiliyor mu; bütçe 32/32 + 0/20 yeniden hesaplanabiliyor mu;
* bu çalışma ağacında `--verify` tam geçiyor mu (`out/` bulunan ortam); temiz klonda yalnız
  `out/` dosyaları eksik olabilir — izlenenler asla.

Testler gerçek dosyaları **yazmaz**.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001c_closure.py"
MANIFEST = ROOT / "eval" / "semread_001c_closure.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001c_closure", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _manifest() -> dict:
    assert MANIFEST.exists(), "closure manifesti izlenmeli (eval/semread_001c_closure.json)"
    return json.loads(MANIFEST.read_text())


def test_the_manifest_pins_the_001c_evidence_chain():
    manifest = _manifest()
    assert manifest["schema"] == "semread-001c-closure/1"
    assert manifest["experiment"]["status"] == "closed_read_only_historical"
    paths = [row["path"] for row in manifest["artifacts"]]
    for relative in ("report.md", "docs/HERMES_SEMREAD_001C_HANDOFF.md", "docs/PLAN-13.md",
                     "eval/semread_001b_gold/FREEZE.json",
                     "out/lab/semread-001c/state.json",
                     "out/lab/semread-001c/dev-report.json",
                     "out/lab/semread-001c/dev-report.md",
                     "out/lab/semread-001c/dev-semantic-report.json",
                     "out/lab/semread-001c/dev-semantic-report.md"):
        assert relative in paths, relative
    assert len(manifest["selected_attempts"]) == 12
    for row in manifest["selected_attempts"]:
        for suffix in ("manifest.json", "result.json", "response-parsed.json"):
            assert f"{row['directory']}/{suffix}" in paths, (row["attempt_id"], suffix)


def test_tracked_artifacts_anchor_to_the_closure_commit():
    """İzlenen dokümanlar kapanış HEAD'inin blob'una çapalanır — her (tam) klonda denetlenebilir."""
    manifest = _manifest()
    recorded = manifest["recorded_at_git_head"]
    assert recorded, "closure HEAD kaydı zorunlu"
    rows = {row["path"]: row for row in manifest["artifacts"]}
    for relative in ("report.md", "docs/HERMES_SEMREAD_001C_HANDOFF.md", "docs/PLAN-13.md",
                     "eval/semread_001b_gold/FREEZE.json"):
        row = rows[relative]
        assert row["tracked"] is True
        assert row["sha256"] == tool._git_file_sha256(recorded, relative, ROOT), relative


def test_selected_attempts_follow_the_latest_pass_rule():
    manifest = _manifest()
    attempts_root = ROOT / "out/lab/semread-001c/attempts"
    if not attempts_root.exists():
        return
    for row in manifest["selected_attempts"]:
        cell_dir = attempts_root / row["cell"]
        passes = []
        for attempt_dir in sorted(path for path in cell_dir.iterdir() if path.is_dir()):
            result = json.loads((attempt_dir / "result.json").read_text()) \
                if (attempt_dir / "result.json").exists() else None
            if result and result.get("state") == "pass" \
                    and (attempt_dir / "response-parsed.json").exists():
                passes.append(attempt_dir)
        assert passes, f"seçili attempt'i olmayan hücre: {row['cell']}"
        assert f"{row['cell']}/{passes[-1].name}" == row["attempt_id"]
    # requalification'da elbow-VE 0004 parse_error'dır; seçili fallback son pass'tir (0003).
    elbow_ve = next(row for row in manifest["selected_attempts"]
                    if row["cell"] == "dev-flange-elbow-VE")
    assert elbow_ve["attempt_id"] == "dev-flange-elbow-VE/attempt-0003"


def test_identities_come_from_the_attempt_manifests():
    manifest = _manifest()
    attempts_root = ROOT / "out/lab/semread-001c/attempts"
    groups: dict[str, list[str]] = {}
    for row in manifest["selected_attempts"]:
        recorded = json.loads(
            (attempts_root / row["attempt_id"] / "manifest.json").read_text())
        assert row["producer_identity"] == recorded["producer_identity"]
        assert row["evaluation_identity"] == recorded["evaluation_identity"]
        groups.setdefault(recorded["producer_identity"], []).append(row["attempt_id"])
    identities = manifest["identities"]
    assert identities["producer_identity"]["groups"] == groups
    # 7 paylaşımlı zarflı requal hücresi + 4 D + 1 elbow-VE fallback (eski zarf)
    assert sorted(len(value) for value in groups.values()) == [1, 4, 7]
    run_contract = identities["run_contract"]
    assert run_contract["version"] == "semread-001c-run-contract/1"
    assert run_contract["versions_seen"] == ["semread-001c-run-contract/1"]
    assert run_contract["generation_settings_V_eq_VE"] is True
    assert run_contract["settings"]["repeat_penalty"] == 1.25
    assert run_contract["settings"]["num_ctx"] == 22528
    assert run_contract["file_sha256_at_closure"] != \
        run_contract["file_sha256_before_documentation_revision"]


def test_requalification_summary_is_derivable():
    manifest = _manifest()
    requal = manifest["summary"]["requalification"]
    assert requal["valid_result"]["passed"] == 7 and requal["valid_result"]["total"] == 8
    assert requal["stop"]["passed"] == 8 and requal["stop"]["total"] == 8
    assert requal["shared_settings"]["passed"] == 8
    assert requal["common_options"] == {"num_ctx": 22528, "num_predict": 8192,
                                        "repeat_last_n": 512, "repeat_penalty": 1.25,
                                        "temperature": 0.0}
    assert [row["cell"] for row in requal["violations"]] == ["dev-flange-elbow-VE"]
    assert requal["violations"][0]["state"] == "parse_error"
    if (ROOT / "out/lab/semread-001c/attempts").exists():
        derived = tool.requalification_summary(ROOT)
        assert derived["valid_result"] == requal["valid_result"]
        assert derived["stop"] == requal["stop"]
        assert derived["common_options"] == requal["common_options"]


def test_budget_summary_is_recomputable_from_the_ledger():
    """out/ bu ağaçtaysa manifest bütçesi state.json'dan birebir yeniden hesaplanır."""
    ledger = ROOT / "out/lab/semread-001c/state.json"
    if not ledger.exists():
        return
    manifest = _manifest()
    state = json.loads(ledger.read_text())
    assert manifest["summary"]["budget"] == tool.budget_summary(state)
    assert manifest["summary"]["attempt_ledger"] == tool.attempt_ledger_summary(state)
    budget = manifest["summary"]["budget"]
    assert budget["used"] == 32
    assert budget["limits"] == {"dev": 32, "final": 20, "total": 52}
    assert budget["by_phase"] == {"dev": 32}
    ledger_summary = manifest["summary"]["attempt_ledger"]
    assert ledger_summary["total"] == 29
    assert ledger_summary["by_state"] == {"pass": 19, "transport_error": 2, "truncated_output": 5,
                                          "parse_error": 2, "failed_gates": 1}


def test_verify_passes_where_the_lab_tree_exists():
    manifest = _manifest()
    result = tool.verify_manifest(manifest, ROOT)
    assert result["mismatched"] == [], f"001C artifact'ı değişmiş: {result['mismatched']}"
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


def test_read_only_declaration_is_recorded():
    manifest = _manifest()
    assert manifest["experiment"]["status"] == "closed_read_only_historical"
    assert "READ-ONLY" in manifest["note"]
    assert "SEMREAD-001D" in manifest["experiment"]["decision"]
    assert manifest["recorded_at_git_head"], "closure HEAD kaydı zorunlu"
    selected = {row["cell"] for row in manifest["selected_attempts"]}
    assert len(selected) == 12
