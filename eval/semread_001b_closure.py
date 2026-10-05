"""SEMREAD-001B — **kapanış manifesti** (PLAN-12 §14, P0).

001B `CLOSED AS RECORDED` kabul edilir (PLAN-12 §11): FREEZE.json, final rapor, seçili/başarısız
attempt'ler, bütçe defteri ve değerlendirme kimliği **değiştirilmez**. Bu araç yalnız **okur**:
mevcut 001B artifact'larının sha256'larını `eval/semread_001b_closure.json` içine yazar ve
`--verify` ile yeniden hesaplayıp karşılaştırır. Hiçbir 001B dosyası (out/ dahil) bu araç
tarafından yazılmaz.

Neden gerekli: FREEZE.json yalnız gold bağlamalarını dondurur; final rapor, değerlendirme koşusu,
seçili attempt'ler ve bütçe defteri `out/` altındadır (git dışı). Kapanış manifesti bu kanıt
zincirinin hash'lerini **izlenen** tek dosyada kayda geçirir; P0 acceptance: *001B historical
artifacts verifiably unchanged*.

Komutlar:

    --write    manifesti (yeniden) yaz — tüm artifact'lar mevcut değilse yazmaz (exit 1)
    --verify   manifesti doğrula (varsayılan): hash'ler + eksik dosyalar

Doğrulama semantiği: `ok` ancak ve ancak listelenen her artifact diskte varsa **ve** hash'i
birebir tutuyorsa True'dur. Temiz bir klonda `out/` yoktur; bu durumda eksikler `missing` altında
**açıkça** raporlanır (sessizce atlanmaz).
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

CLOSURE_SCHEMA = "semread-001b-closure/1"
MANIFEST_PATH = ROOT / "eval" / "semread_001b_closure.json"

FREEZE_REL = "eval/semread_001b_gold/FREEZE.json"
GOLD_MANIFEST_REL = "eval/semread_001b_gold/manifest.json"
FINAL_DIR_REL = "out/lab/semread-001b/final"
LEDGER_REL = "out/lab/semread-001b/state.json"
EVALUATIONS_REL = "out/lab/semread-001b/evaluations"

# Bütçe kuralı (001B pilotu, P0R-FINAL-B): gönderilmediği **kanıtlı** yerel/preflight retleri
# sayılmaz; gönderilmiş/rezerve/taşıma-hatalı kayıtlar sayılır.
NON_DISPATCH_SEND_STATES = ("not_sent_model_mismatch", "not_sent_runtime_mismatch",
                            "not_sent_unsupported_setting")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                text=True, check=True)
        return result.stdout.strip() or None
    except Exception:  # noqa: BLE001 - başlık bilgisi kritik değil; None yazılır
        return None


def artifact_relative_paths(root: Path = ROOT) -> list[str]:
    """Sabit artifact listesi; değerlendirme koşusu `final/pointer.json`'dan çözülür."""
    pointer = json.loads((root / FINAL_DIR_REL / "pointer.json").read_text())
    run_id = pointer["evaluation_run_id"]
    run_dir_rel = f"{EVALUATIONS_REL}/{run_id}"
    return sorted([
        FREEZE_REL,
        GOLD_MANIFEST_REL,
        f"{FINAL_DIR_REL}/report.md",
        f"{FINAL_DIR_REL}/pointer.json",
        LEDGER_REL,
        f"{run_dir_rel}/acceptance.json",
        f"{run_dir_rel}/evaluation.json",
        f"{run_dir_rel}/report.md",
        f"{run_dir_rel}/selected-attempts.json",
    ])


def _budget_summary(state: dict) -> dict:
    calls = state.get("live_calls") or []
    by_send_state: dict[str, int] = {}
    for call in calls:
        key = call.get("send_state") or "?"
        by_send_state[key] = by_send_state.get(key, 0) + 1
    used = sum(1 for call in calls if call.get("send_state") not in NON_DISPATCH_SEND_STATES)
    return {
        "used": used,
        "limits": state.get("budget") or {"dev": 10, "final": 20, "total": 30},
        "by_send_state": by_send_state,
        "rule": ("used = send_state'i not_sent_* olmayan kayıt sayısı (gönderilmiş + rezerve + "
                 "taşıma hatası sayılır; yerel ret sayılmaz — 001B pilot kuralı)"),
    }


def _attempt_ledger_summary(state: dict) -> dict:
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
    dispatched = ("sending", "transport_error", "parse_error", "failed_gates", "pass")
    identifiers = [row.get("attempt_id") for row in rows]
    return {"total": len(rows), "by_state": by_state,
            "unique_attempt_ids": len(set(identifiers)),
            "dispatched": sum(1 for row in rows if row.get("state") in dispatched)}


def build_manifest(root: Path = ROOT) -> dict:
    """Artifact hash'lerini ölç ve manifest sözlüğünü kur. Eksik artifact'ta hata verir."""
    freeze = json.loads((root / FREEZE_REL).read_text())
    bindings = freeze.get("bindings", {})
    pointer = json.loads((root / FINAL_DIR_REL / "pointer.json").read_text())
    state = json.loads((root / LEDGER_REL).read_text())
    acceptance = json.loads(
        (root / EVALUATIONS_REL / pointer["evaluation_run_id"] / "acceptance.json").read_text())

    artifacts: list[dict] = []
    missing: list[str] = []
    for relative in artifact_relative_paths(root):
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
        raise SystemExit(f"kapanış manifesti yazılamaz — eksik artifact: {missing}")

    return {
        "schema": CLOSURE_SCHEMA,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment": {
            "name": "semread-001b",
            "status": "closed_as_recorded",
            "plan": "docs/PLAN-11.md",
            "handoff": "docs/HERMES_SEMREAD_001B_HANDOFF.md",
            "final_report": f"{FINAL_DIR_REL}/report.md",
        },
        "recorded_at_git_head": _git_head(root),
        "evaluation_run_id": pointer["evaluation_run_id"],
        "identities": {
            "gold_content_identity": freeze.get("gold_content_identity"),
            "producer_identity": bindings.get("producer_identity"),
            "evaluation_identity": bindings.get("evaluation_identity"),
            "code_identity": bindings.get("code_identity"),
            "preprocessing_identity": bindings.get("preprocessing_identity"),
            "contract_version": bindings.get("contract_version"),
            "candidate_schema": bindings.get("candidate_schema"),
            "match_policy_version": (bindings.get("match_policy") or {}).get("version"),
            "model": bindings.get("model"),
            "expected_model_digest": bindings.get("expected_model_digest"),
            "runtime": bindings.get("runtime"),
        },
        "summary": {
            "acceptance": {key: row.get("status") for key, row in
                           (acceptance.get("acceptance") or {}).items()},
            "open": acceptance.get("open"),
            "conclusion": acceptance.get("conclusion"),
            "budget": _budget_summary(state),
            "attempt_ledger": _attempt_ledger_summary(state),
        },
        "artifacts": artifacts,
        "note": ("PLAN-12 §14 (P0): 001B kapanış kaydı. İzlenen dosya yalnızca hash listesidir; "
                 "`--verify` başarısızsa 001B artifact'ı değişmiş demektir — düzeltme yeni sürümde "
                 "yapılır (§11)."),
    }


def verify_manifest(manifest: dict, root: Path = ROOT) -> dict:
    """Manifestteki her artifact'ı yeniden hash'le; eksik ve sapanları ayrı raporla."""
    missing: list[str] = []
    mismatched: list[dict] = []
    checked = 0
    for row in manifest.get("artifacts", []):
        relative = row.get("path")
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
    parser = argparse.ArgumentParser(description="SEMREAD-001B kapanış manifesti (PLAN-12 §14)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="manifesti yaz")
    group.add_argument("--verify", action="store_true", help="manifesti doğrula (varsayılan)")
    args = parser.parse_args(argv)

    if args.write:
        manifest = build_manifest()
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                            sort_keys=True) + "\n")
        print(f"kapanış manifesti yazıldı: {MANIFEST_PATH.relative_to(ROOT)}")
        print(f"  artifact: {len(manifest['artifacts'])} · kimlik: "
              f"{manifest['identities']['gold_content_identity'][:16]}… · HEAD: "
              f"{manifest['recorded_at_git_head']}")
        print(f"  bütçe: {manifest['summary']['budget']['used']}/"
              f"{manifest['summary']['budget']['limits'].get('total')} · attempt defteri: "
              f"{manifest['summary']['attempt_ledger']['total']}")
        return 0

    if not MANIFEST_PATH.exists():
        print(f"kapanış manifesti yok: {MANIFEST_PATH.relative_to(ROOT)} (önce --write)")
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text())
    result = verify_manifest(manifest)
    if result["ok"]:
        print(f"kapanış manifesti: {result['checked']}/{result['total']} artifact birebir — TAMAM")
        return 0
    print(f"kapanış manifesti: {result['checked']}/{result['total']} artifact doğrulandı — SORUN VAR")
    for relative in result["missing"]:
        print(f"  eksik: {relative}")
    for row in result["mismatched"]:
        print(f"  değişmiş: {row['path']} (beklenen {row['expected'][:16]}…, ölçülen "
              f"{row['actual'][:16]}…)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
