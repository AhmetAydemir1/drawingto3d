"""SEMREAD-001C — **kapanış (closure) manifesti** (PLAN_SEMREAD_001D §9, P0.8).

001C kapanışta **READ-ONLY HISTORICAL EXPERIMENT** kabul edilir: attempt'ler, bütçe defteri,
raporlar ve dokümanlar **değiştirilmez**. Bu araç yalnız **okur**: closure artifact'larının
sha256'larını `eval/semread_001c_closure.json` içine yazar ve `--verify` ile yeniden hesaplayıp
karşılaştırır. Hiçbir 001C dosyası (out/ dahil) bu araç tarafından yazılmaz.

Pinlenen kanıt zinciri (plan §9 minimumu):

* izlenen dokümanlar: `report.md`, `docs/HERMES_SEMREAD_001C_HANDOFF.md`, `docs/PLAN-13.md`
* gold çapası: `eval/semread_001b_gold/FREEZE.json` (001C değerlendirmesi bunu reuse eder)
* bütçe defteri: `out/lab/semread-001c/state.json` (özet: dev 32/32 · final 0/20)
* raporlar: `dev-report.{json,md}`, `dev-semantic-report.{json,md}` (kapanışta tazelendi)
* seçili dev attempt'leri (12 hücre; "en yeni pass" kuralı — dev-report/dev-semantic-eval ile aynı):
  manifest/result/parsed sha256'ları
* kimlikler: producer/evaluation (attempt manifestlerinden — run-time) + closure recompute +
  run-contract (sürüm, dosya hash'i, paylaşımlı istek `options` eşitliği)

Doğrulama semantiği (`--verify`): çapa **sınıfa göre** değişir — git'te izlenen dokümanlar
(`tracked: true`) **`recorded_at_git_head` commit'indeki blob** ile denetlenir (kapanış kanıtı =
commit'lenen baytlar; kök `report.md`/handoff yaşayan dokümanlardır — sonraki sürüm düzenlemeleri
kapanış kaydını bozmaz, ama kapanış commit'i geriye dönük değiştirilirse/rebase edilirse sapma
yakalanır); `out/` defteri ise **working-tree** hash'i ile denetlenir (001C READ-ONLY: hiçbir out/
dosyası sonradan değişemez). Temiz bir klonda `out/` yoktur; eksikler `missing` altında **açıkça**
raporlanır (sessizce atlanmaz).

Komutlar:

    --write    manifesti (yeniden) yaz — tüm artifact'lar mevcut değilse yazmaz (exit 1)
    --verify   manifesti doğrula (varsayılan)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.semantic_run_contract import (  # noqa: E402 - src yolu yukarıda eklendi
    CONTRACT_VERSION, REPEAT_LAST_N, REPEAT_PENALTY, SETTINGS, generation_settings)

CLOSURE_SCHEMA = "semread-001c-closure/1"
MANIFEST_PATH = ROOT / "eval" / "semread_001c_closure.json"

EXPERIMENT = "semread-001c"
LAB_REL = f"out/lab/{EXPERIMENT}"
ATTEMPTS_REL = f"{LAB_REL}/attempts"

REPORT_REL = "report.md"
HANDOFF_REL = "docs/HERMES_SEMREAD_001C_HANDOFF.md"
PLAN_REL = "docs/PLAN-13.md"
FREEZE_REL = "eval/semread_001b_gold/FREEZE.json"
LEDGER_REL = f"{LAB_REL}/state.json"
REPORT_FILES = (f"{LAB_REL}/dev-report.json", f"{LAB_REL}/dev-report.md",
                f"{LAB_REL}/dev-semantic-report.json", f"{LAB_REL}/dev-semantic-report.md")

CONTRACT_REL = "src/drawingto3d/semantic_run_contract.py"
# Requalification'ın kapandığı HEAD (2c42f1b): docstring revizyonundan (P0.5) ÖNCEKİ sözleşme
# blob'u buradan türetilir — run-time dosya hash'inin kanıtı git'te kalır.
REQUAL_HEAD = "2c42f1b3acbe026bb66215afb8c67fb80064acce"

DEV_PAGES = ("dev-plate-pocket", "dev-flange-book", "dev-flange-elbow", "dev-drawing-2")
ARMS = ("D", "V", "VE")
VVE_ARMS = ("V", "VE")

# Bütçe kuralı (001B pilotu, P0R-FINAL-B): gönderilmediği **kanıtlı** yerel/preflight retleri
# sayılmaz; gönderilmiş/rezerve/taşıma-hatalı kayıtlar sayılır.
NON_DISPATCH_SEND_STATES = ("not_sent_model_mismatch", "not_sent_runtime_mismatch",
                            "not_sent_unsupported_setting")

# Attempt defterinde "çağrı yapıldı" tarafında sayılan nihai durumlar (pilot ile aynı küme).
DISPATCHED_ATTEMPT_STATES = ("sending", "transport_error", "parse_error", "truncated_output",
                             "incomplete_metadata", "failed_gates", "pass")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                text=True, check=True)
        return result.stdout.strip() or None
    except Exception:  # noqa: BLE001 - başlık bilgisi kritik değil; None yazılır
        return None


def _git_file_sha256(rev: str, relative: str, root: Path = ROOT) -> str | None:
    """Belirtilen revizyondaki dosya içeriğinin sha256'sı (audit: doc-revizyonu öncesi blob)."""
    try:
        result = subprocess.run(["git", "show", f"{rev}:{relative}"], cwd=root,
                                capture_output=True, check=True)
        return hashlib.sha256(result.stdout).hexdigest()
    except Exception:  # noqa: BLE001 - git yoksa alan None kalır (not ile açıklanır)
        return None


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def selected_attempts(root: Path = ROOT) -> list[dict]:
    """12 hücrenin seçili attempt'i: **en yeni pass** + parsed çıktı (dev-report ile aynı kural).

    Seçilemeyen hücrede fail-closed: build durur (closure eksik kanıtla yazılmaz).
    """
    rows: list[dict] = []
    missing: list[str] = []
    for page in DEV_PAGES:
        for arm in ARMS:
            cell = f"{page}-{arm}"
            cell_dir = root / ATTEMPTS_REL / cell
            chosen = None
            if cell_dir.is_dir():
                for attempt_dir in sorted(path for path in cell_dir.iterdir() if path.is_dir()):
                    result = read_json(attempt_dir / "result.json")
                    if not result or result.get("state") != "pass":
                        continue
                    if not (attempt_dir / "response-parsed.json").exists():
                        continue
                    chosen = (attempt_dir, result)
            if chosen is None:
                missing.append(cell)
                continue
            attempt_dir, result = chosen
            manifest = read_json(attempt_dir / "manifest.json") or {}
            rows.append({
                "cell": cell,
                "attempt_id": f"{cell}/{attempt_dir.name}",
                "directory": str(attempt_dir.relative_to(root)),
                "state": result.get("state"),
                "contract_version": manifest.get("contract_version"),
                "producer_identity": manifest.get("producer_identity"),
                "evaluation_identity": manifest.get("evaluation_identity"),
                "manifest_sha256": _sha256_file(attempt_dir / "manifest.json"),
                "result_sha256": _sha256_file(attempt_dir / "result.json"),
                "parsed_sha256": _sha256_file(attempt_dir / "response-parsed.json"),
            })
    if missing:
        raise SystemExit(f"closure manifesti yazılamaz — seçili attempt'i olmayan hücre: {missing}")
    return rows


def artifact_relative_paths(rows: list[dict]) -> list[str]:
    """Sabit izlenen dosyalar + seçili attempt'lerin manifest/result/parsed üçlüsü."""
    paths = [REPORT_REL, HANDOFF_REL, PLAN_REL, FREEZE_REL, LEDGER_REL, *REPORT_FILES]
    for row in rows:
        directory = row["directory"]
        paths += [f"{directory}/manifest.json", f"{directory}/result.json",
                  f"{directory}/response-parsed.json"]
    return sorted(paths)


def budget_summary(state: dict) -> dict:
    """Bütçe özeti: `used` = not_sent_* olmayan canlı çağrı sayısı; faz dağılımı + limits."""
    calls = state.get("live_calls") or []
    dispatched = [call for call in calls
                  if call.get("send_state") not in NON_DISPATCH_SEND_STATES]
    by_send_state: dict[str, int] = {}
    for call in calls:
        key = call.get("send_state") or "?"
        by_send_state[key] = by_send_state.get(key, 0) + 1
    by_phase: dict[str, int] = {}
    for call in dispatched:
        key = call.get("phase") or "?"
        by_phase[key] = by_phase.get(key, 0) + 1
    return {
        "used": len(dispatched),
        "limits": state.get("budget") or {"dev": 32, "final": 20, "total": 52},
        "by_phase": by_phase,
        "by_send_state": by_send_state,
        "rule": ("used = send_state'i not_sent_* olmayan kayıt sayısı (gönderilmiş + rezerve + "
                 "taşıma hatası sayılır; yerel ret sayılmaz — 001B pilot kuralı, 001C kapanışı)"),
    }


def attempt_ledger_summary(state: dict) -> dict:
    """state.json `attempts` sözlüğü vaka-başına listeler taşır; düzleştirip say."""
    groups = state.get("attempts") or {}
    rows: list[dict] = []
    if isinstance(groups, dict):
        for value in groups.values():
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
            elif isinstance(value, dict):
                rows.append(value)
    elif isinstance(groups, list):
        rows = [row for row in groups if isinstance(row, dict)]
    by_state: dict[str, int] = {}
    for row in rows:
        key = row.get("state") or row.get("verdict") or "?"
        by_state[key] = by_state.get(key, 0) + 1
    identifiers = [row.get("attempt_id") for row in rows]
    return {"total": len(rows), "by_state": by_state,
            "unique_attempt_ids": len(set(identifiers)),
            "dispatched": sum(1 for row in rows if row.get("state") in DISPATCHED_ATTEMPT_STATES)}


def requalification_summary(root: Path = ROOT) -> dict:
    """PLAN-13 §8 denetimi: her V/VE hücresinin **en yeni** attempt'i üzerinden türetilir.

    valid_result = state == pass; stop = done_reason == stop; shared_settings = sekiz attempt'in
    istek `options`'ı birebir aynı (paylaşımlı zarf iddiasının mekanik kanıtı).
    """
    cells = [f"{page}-{arm}" for page in DEV_PAGES for arm in VVE_ARMS]
    latest: dict[str, tuple[Path, dict, dict]] = {}
    missing: list[str] = []
    for cell in cells:
        cell_dir = root / ATTEMPTS_REL / cell
        with_result = ([path for path in sorted(cell_dir.iterdir()) if path.is_dir()
                        and (path / "result.json").exists()] if cell_dir.is_dir() else [])
        if not with_result:
            missing.append(cell)
            continue
        attempt_dir = with_result[-1]
        latest[cell] = (attempt_dir,
                        read_json(attempt_dir / "result.json") or {},
                        read_json(attempt_dir / "request-manifest.json") or {})
    if missing:
        raise SystemExit(f"requalification özeti türetilemez — defteri eksik hücre: {missing}")

    def passed(predicate) -> dict:
        hits = [cell for cell, row in latest.items() if predicate(row)]
        return {"passed": len(hits), "total": len(cells), "cells": hits}

    valid = passed(lambda row: row[1].get("state") == "pass")
    stop = passed(lambda row: row[2].get("done_reason") == "stop")
    options_by_cell = {cell: json.dumps(row[2].get("options"), sort_keys=True)
                       for cell, row in latest.items()}
    options_values = list(options_by_cell.values())
    unique_options = sorted(set(options_values))
    if len(unique_options) == 1:
        shared = passed(lambda row: True)
        common_options = json.loads(unique_options[0])
    else:
        counts = {value: options_values.count(value) for value in unique_options}
        best_value = max(unique_options, key=lambda value: counts[value])
        shared = {"passed": counts[best_value], "total": len(cells),
                  "cells": [cell for cell in cells if options_by_cell[cell] == best_value]}
        common_options = None
    violations = []
    for cell in cells:
        attempt_dir, result, _ = latest[cell]
        if result.get("state") != "pass":
            violations.append({"cell": cell, "attempt_id": f"{cell}/{attempt_dir.name}",
                               "state": result.get("state"),
                               "failure_kind": result.get("failure_kind")})
    return {
        "cells": len(cells),
        "latest_attempts": {cell: f"{cell}/{row[0].name}" for cell, row in latest.items()},
        "valid_result": valid,
        "stop": stop,
        "shared_settings": shared,
        "common_options": common_options,
        "violations": violations,
    }


def _identity_groups(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row["attempt_id"])
    return groups


def _recompute_identities(root: Path = ROOT) -> dict:
    """Pilot kimliklerini **kapanış anında** yeniden hesapla (bilgi amaçlı; doğrulama artifact
    hash'leriyle yapılır). Doc-only revizyon sonrası producer recompute'u run-time'dan sapar."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "semread_001c_closure_pilot", root / "eval" / "semread_001b_pilot.py")
        assert spec is not None and spec.loader is not None
        pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pilot)
        pilot.use_experiment(EXPERIMENT)
        return {"producer_identity_recomputed_at_closure": pilot.producer_identity(),
                "evaluation_identity_recomputed_at_closure": pilot.evaluation_identity()}
    except Exception as exc:  # noqa: BLE001 - recompute bilgi amaçlıdır; manifest yine yazılır
        return {"producer_identity_recomputed_at_closure": None,
                "evaluation_identity_recomputed_at_closure": None,
                "recompute_note": f"recompute başarısız: {exc}"}


def build_manifest(root: Path = ROOT) -> dict:
    """Artifact hash'lerini ölç ve closure manifest sözlüğünü kur. Eksik artifact'ta hata verir."""
    rows = selected_attempts(root)
    state = read_json(root / LEDGER_REL)
    if not state:
        raise SystemExit(f"closure manifesti yazılamaz — defter okunamadı: {LEDGER_REL}")

    artifacts: list[dict] = []
    missing: list[str] = []
    for relative in artifact_relative_paths(rows):
        path = root / relative
        if not path.exists():
            missing.append(relative)
            continue
        artifacts.append({
            "path": relative,
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
            "tracked": not relative.startswith("out/"),
        })
    if missing:
        raise SystemExit(f"closure manifesti yazılamaz — eksik artifact: {missing}")

    producer_groups = _identity_groups(rows, "producer_identity")
    evaluation_groups = _identity_groups(rows, "evaluation_identity")
    primary_producer = max(producer_groups, key=lambda value: len(producer_groups[value]))
    primary_evaluation = max(evaluation_groups, key=lambda value: len(evaluation_groups[value]))
    contract_versions = sorted({row["contract_version"] for row in rows if row["contract_version"]})

    semantic_report = read_json(root / REPORT_FILES[2]) or {}
    offline_run_id = (semantic_report.get("identity") or {}).get("evaluation_run_id")

    return {
        "schema": CLOSURE_SCHEMA,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment": {
            "name": EXPERIMENT,
            "status": "closed_read_only_historical",
            "plan": PLAN_REL,
            "handoff": HANDOFF_REL,
            "report": REPORT_REL,
            "decision": ("PLAN-13 §7: dev 32/32 sonrası §8 kapısı geçilmedi → 001C final yok; "
                         "yeni experiment version = SEMREAD-001D"),
            "requalification": "7/8 (§8 resmî kapı; elbow-VE schema_coordinate) · paylaşımlı ayar 8/8",
        },
        "recorded_at_git_head": _git_head(root),
        "identities": {
            "producer_identity": {
                "value": primary_producer,
                "value_note": "run-time değer (seçili attempt manifestleri); en kalabalık grup",
                "groups": producer_groups,
            },
            "evaluation_identity": {
                "value": primary_evaluation,
                "value_note": "run-time değer (seçili attempt manifestleri); en kalabalık grup",
                "groups": evaluation_groups,
            },
            "offline_evaluation_run_id": offline_run_id,
            "run_contract": {
                "version": CONTRACT_VERSION,
                "versions_seen": contract_versions,
                "file": CONTRACT_REL,
                "file_sha256_at_closure": _sha256_file(root / CONTRACT_REL),
                "file_sha256_before_documentation_revision": _git_file_sha256(REQUAL_HEAD,
                                                                              CONTRACT_REL, root),
                "documentation_revision": ("P0.5 (2026-10-05, kapanış): yalnız docstring/yorum "
                                           "güncellendi; sabitler (num_ctx 22528 / num_predict 8192 "
                                           "/ temperature 0.0 / repeat_penalty 1.25 paylaşımlı / "
                                           "repeat_last_n 512) ve davranış değişmedi — recompute "
                                           "bu yüzden mekanik sapar"),
                "generation_settings_V_eq_VE": generation_settings("V") == generation_settings("VE"),
                "settings": {"num_ctx": SETTINGS["num_ctx"], "num_predict": SETTINGS["num_predict"],
                             "temperature": SETTINGS["temperature"],
                             "repeat_penalty": REPEAT_PENALTY, "repeat_last_n": REPEAT_LAST_N},
            },
            **_recompute_identities(root),
        },
        "summary": {
            "budget": budget_summary(state),
            "attempt_ledger": attempt_ledger_summary(state),
            "requalification": requalification_summary(root),
        },
        "selected_attempts": rows,
        "artifacts": artifacts,
        "note": ("PLAN_SEMREAD_001D §9 (P0.8): 001C closure kaydı. İzlenen dosya yalnızca hash "
                 "listesidir; `--verify` başarısızsa: bir `out/` artifact'ı değişmiş ya da "
                 "kapanış commit geçmişi yeniden yazılmış demektir — 001C READ-ONLY'dir, "
                 "düzeltme yeni sürümde (001D) yapılır. Çapa: git'te izlenen dokümanlar "
                 "`recorded_at_git_head` blob'una, `out/` defteri working-tree'ye. Kimliklerin "
                 "run-time değerleri attempt manifestlerinden gelir; closure recompute'u bilgi "
                 "amaçlıdır."),
    }


def verify_manifest(manifest: dict, root: Path = ROOT) -> dict:
    """Manifestteki her artifact'ı yeniden hash'le; eksik ve sapanları ayrı raporla.

    Çapa kuralı: `tracked: true` (git'te izlenen dokümanlar) → `recorded_at_git_head`
    commit'indeki blob; `out/` defteri → working-tree dosyası. Böylece yaşayan dokümanların
    (kök `report.md`, handoff) sonraki düzenlemeleri kapanış kaydını bozmaz; kapanış commit'i
    geriye dönük değiştirilirse blob sapar ve yakalanır.
    """
    recorded_head = manifest.get("recorded_at_git_head")
    missing: list[str] = []
    mismatched: list[dict] = []
    checked = 0
    for row in manifest.get("artifacts", []):
        relative = row.get("path")
        if row.get("tracked") and recorded_head:
            actual = _git_file_sha256(recorded_head, relative, root)
            if actual is None:
                missing.append(relative)
                continue
        else:
            path = root / relative
            if not path.exists():
                missing.append(relative)
                continue
            actual = _sha256_file(path)
        checked += 1
        if actual != row.get("sha256"):
            mismatched.append({"path": relative, "expected": row.get("sha256"),
                               "actual": actual})
    return {
        "ok": not missing and not mismatched,
        "checked": checked,
        "total": len(manifest.get("artifacts", [])),
        "missing": missing,
        "mismatched": mismatched,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEMREAD-001C kapanış manifesti "
                                                 "(PLAN_SEMREAD_001D §9)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="manifesti yaz")
    group.add_argument("--verify", action="store_true", help="manifesti doğrula (varsayılan)")
    args = parser.parse_args(argv)

    if args.write:
        manifest = build_manifest()
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                            sort_keys=True) + "\n")
        print(f"kapanış manifesti yazıldı: {MANIFEST_PATH.relative_to(ROOT)}")
        print(f"  artifact: {len(manifest['artifacts'])} · seçili attempt: "
              f"{len(manifest['selected_attempts'])} · HEAD: {manifest['recorded_at_git_head']}")
        budget = manifest["summary"]["budget"]
        requal = manifest["summary"]["requalification"]
        print(f"  bütçe: {budget['used']}/{budget['limits'].get('total')} "
              f"(dev {budget['by_phase'].get('dev', 0)}/{budget['limits'].get('dev')} · "
              f"final {budget['by_phase'].get('final', 0)}/{budget['limits'].get('final')}) · "
              f"requalification: valid {requal['valid_result']['passed']}/"
              f"{requal['valid_result']['total']}, stop {requal['stop']['passed']}/"
              f"{requal['stop']['total']}, paylaşımlı ayar {requal['shared_settings']['passed']}/"
              f"{requal['shared_settings']['total']}")
        print(f"  producer (run-time): {manifest['identities']['producer_identity']['value']}")
        return 0

    if not MANIFEST_PATH.exists():
        print(f"kapanış manifesti yok: {MANIFEST_PATH.relative_to(ROOT)} (önce --write)")
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text())
    result = verify_manifest(manifest)
    if result["ok"]:
        print(f"kapanış manifesti: {result['checked']}/{result['total']} artifact birebir — TAMAM")
        return 0
    print(f"kapanış manifesti: {result['checked']}/{result['total']} artifact doğrulandı — "
          "SORUN VAR")
    for relative in result["missing"]:
        print(f"  eksik: {relative}")
    for row in result["mismatched"]:
        print(f"  değişmiş: {row['path']} (beklenen {row['expected'][:16]}…, ölçülen "
              f"{row['actual'][:16]}…)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
