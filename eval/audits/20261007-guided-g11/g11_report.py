"""G11 report — reads the frozen manifest + `cases/*.json`, writes the two PLAN §17 deliverables.

    .venv/bin/python eval/audits/20261007-guided-g11/g11_report.py

Outputs:
  eval/guided_10_report.json — machine summary (per-case rows, metric, taxonomy distribution, honesty)
  eval/guided_10_report.md   — the same, for humans

G11R-01 (bağımsız inceleme): the primary metric is DONMUŞ DELIVERY-PLAN tanımıyla
`correct full_step / full_step` — the denominator is the manifest's fixed full_step set (9 cases).
A case that reached no STEP, failed its build or was never run stays IN the denominator; no verdict
is never an excuse to shrink the denominator. The rate over verdict-having cases only is reported
separately and clearly named as conditional — it is not the primary metric. `compute()` is pure
(files in, dict out) so the regression suite pins this without touching the real tree.

Rules: a case without a record is `pending` — listed explicitly, never silently dropped. No-reference
cases (scope_class `callout_scope_only`) report scope completeness instead and stay outside the rate
set. The product-HEAD check asserts that no `src/`, `tests/` or `pyproject.toml` change happened
between the first and the last case.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from collections import Counter

G11 = pathlib.Path(__file__).parent
ROOT = G11.parents[2]
sys.path.insert(0, str(ROOT / "eval"))


def product_diff(first: str, last: str) -> str:
    if not first or not last:
        return ""
    result = subprocess.run(
        ["git", "diff", "--stat", f"{first}..{last}", "--", "src", "tests", "pyproject.toml"],
        cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def compute(manifest_path: pathlib.Path, cases_dir: pathlib.Path) -> dict:
    """Pure: frozen manifest + case records in, summary dict out (no writes, no git)."""
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    cases = []
    for entry in manifest["cases"]:
        case_id = entry["case_id"]
        path = pathlib.Path(cases_dir) / f"{case_id}.json"
        record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        row = {
            "case_id": case_id,
            "scope_class": entry.get("expected_scope_class") or "callout_scope_only",
            "source_path": entry["source_path"],
            "status": "pending" if record is None else "recorded",
        }
        if record:
            verdict = record.get("final_geometry_verdict")
            row.update({
                "run_id": record["run_id"], "git_head": record["git_head"],
                "source_sha256_checked": record["source_sha256_checked"],
                "candidate_count": record["candidate_count"],
                "ignored_count": record["ignored_count"],
                "transcription_count": record["transcription_count"],
                "parse_success_count": record["parse_success_count"],
                "proposal_accept_count": record["proposal_accept_count"],
                "manual_target_correction_count": record["manual_target_correction_count"],
                "build_success": record["build_success"],
                "build_blockers": record["build_blockers"],
                "step_reopen": record.get("step_reopen"),
                "bbox": record.get("bbox"),
                "verdict_pass": None if verdict is None else verdict.get("pass"),
                "verdict_shape_ok": None if verdict is None else verdict.get("shape_ok"),
                "verdict_detail_ok": None if verdict is None else verdict.get("detail_ok"),
                "failure_codes": [item["code"] for item in record.get("failures") or []],
                "review_import_used": record.get("review_import_used"),
                "user_interventions": record.get("user_interventions"),
            })
        cases.append(row)

    recorded = [row for row in cases if row["status"] == "recorded"]
    full_step = [row for row in cases if row["scope_class"] == "full_step"]
    with_verdict = [row for row in full_step if row.get("verdict_pass") is not None]
    correct = [row for row in full_step if row.get("verdict_pass") is True]
    unproduced = [row["case_id"] for row in full_step if row.get("verdict_pass") is None]
    rate = (len(correct) / len(full_step)) if full_step else None
    conditional = (len(correct) / len(with_verdict)) if with_verdict else None
    taxonomy = Counter(code for row in recorded for code in row.get("failure_codes") or [])

    heads = [row["git_head"] for row in recorded if row.get("git_head")]
    product_clean = product_diff(heads[0], heads[-1]) if len(heads) >= 2 else ""
    honesty = {
        "cases_recorded": len(recorded), "cases_pending": len(cases) - len(recorded),
        "pending": [row["case_id"] for row in cases if row["status"] == "pending"],
        "same_product_head": product_clean == "",
        "product_diff_first_to_last": product_clean,
        "sha256_checked_all_recorded": all(row["source_sha256_checked"] for row in recorded),
        "review_import_used": [row["case_id"] for row in recorded if row.get("review_import_used")],
    }
    summary = {
        "metric": {
            "guided_correct_step_rate": rate,
            "correct": [row["case_id"] for row in correct],
            "denominator": len(full_step),
            "denominator_source": "donmuş manifest — expected_scope_class == 'full_step' (9 vaka); "
                                  "üretilemeyen/bekleyen vakalar paydadan düşülmez (G11R-01)",
            "unproduced_full_step": unproduced,
            "conditional_correct_rate_among_verdicts": conditional,
            "conditional_definition": "yalnız geometri kararı üretilebilen full_step vakalar arasında; "
                                      "ana metrik DEĞİLDİR (G11R-01)",
            "with_verdict": len(with_verdict),
        },
        "taxonomy_distribution": dict(taxonomy),
        "cases": cases, "honesty": honesty,
    }
    return summary


def render(summary: dict, notes: tuple[str, ...] = ()) -> str:
    """Pure: summary dict in, markdown out."""
    metric, cases, honesty = summary["metric"], summary["cases"], summary["honesty"]
    rate, conditional = metric["guided_correct_step_rate"], metric["conditional_correct_rate_among_verdicts"]
    lines = ["# G11 — ilk 10-pafta koşusu, sonuç raporu", ""]
    lines.append(f"- Kayıtlı vaka: **{honesty['cases_recorded']}/{len(cases)}** · bekleyen: "
                 f"{', '.join(honesty['pending']) or '—'}")
    if rate is not None:
        lines.append(f"- **GUIDED_CORRECT_STEP_RATE = {rate:.4f}** "
                     f"({len(metric['correct'])}/{metric['denominator']} full_step vaka) — payda donmuş "
                     f"manifestin sabit full_step kümesi; STEP üretilemeyen/bekleyen vaka paydadan "
                     f"düşülmez (G11R-01). Üretilemeyenler: "
                     f"{', '.join(metric['unproduced_full_step']) or '—'}.")
        if conditional is not None:
            lines.append(f"- Koşullu oran (bilgi; ana metrik değildir): {conditional:.4f} "
                         f"({len(metric['correct'])}/{metric['with_verdict']}) — yalnız geometri kararı "
                         f"üretilebilen vakalar arasında.")
    else:
        lines.append("- Henüz full_step vaka yok; metrik bekliyor.")
    lines.append(f"- Taksonomi dağılımı: {summary['taxonomy_distribution'] or '—'}")
    lines.append(f"- Ürün kodu değişmedi (ilk→son vaka HEAD): {'evet' if honesty['same_product_head'] else 'HAYIR'}")
    lines.append("")
    lines.append("| vaka | sınıf | aday | kapsam dışı | metin | üretim | verdict | taksonomi |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in cases:
        if row["status"] == "pending":
            lines.append(f"| {row['case_id']} | {row['scope_class']} | — | — | — | — | — | (bekliyor) |")
        else:
            if row["verdict_pass"] is None:
                verdict = "üretilmedi" if row["scope_class"] == "full_step" else "kapsam dışı"
            elif row["verdict_pass"]:
                verdict = "pass"
            else:
                verdict = (f"fail ({'şekil ok, detay -' if row['verdict_shape_ok'] else 'şekil -'})")
            lines.append(f"| {row['case_id']} | {row['scope_class']} | {row['candidate_count']} | "
                         f"{row['ignored_count']} | {row['transcription_count']} | "
                         f"{'ok' if row['build_success'] else 'durdu'} | {verdict} | "
                         f"{', '.join(row['failure_codes']) or '—'} |")
    lines.append("")
    lines.append("## Dürüstlük notları")
    lines.append(f"- Ana metrik paydası manifestin 9 full_step vakasıdır; build/evaluator hatası olan ve "
                 f"bekleyen vakalar bu kümeden çıkarılmaz (G11R-01 düzeltmesi).")
    lines.append(f"- Her vaka taze oturumda, aynı ürün HEAD'inde koştu; kayıtlar `git_head` taşır; "
                 f"ilk→son ürün kodu farkı: {'yok' if honesty['same_product_head'] else 'VAR'}.")
    lines.append(f"- sha256 doğrulaması tüm kayıtlı vakalar: "
                 f"{'tamam' if honesty['sha256_checked_all_recorded'] else 'EKSİK'}.")
    lines.append("- Referans STEP'ler yalnız evaluator'a verildi; kararlar `recipes/*.json` içinde, "
                 "görünen oturum verisi + çizim okumasıyla alındı.")
    lines.append("- Bekleyen vakalar listede açıkça `pending`; sessiz örneklem yok.")
    for line in notes:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = compute(ROOT / "eval/guided_10_manifest.json", G11 / "cases")
    out_json = ROOT / "eval/guided_10_report.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    notes = ()
    rerun = G11 / "rerun-round2"
    if rerun.exists():
        runs = sorted(path.name for path in (rerun / "cases").glob("*.json"))
        notes = (f"Düzeltilmiş girdilerle yeniden koşu turu `{rerun.name}/` altında ayrı kayıtlar: "
                 f"{', '.join(runs) or '—'} — bu rapor yalnız resmî turu sayar (G11R-02).",)
    (ROOT / "eval/guided_10_report.md").write_text(render(summary, notes), encoding="utf-8")
    print(json.dumps({"recorded": summary["honesty"]["cases_recorded"],
                      "rate": summary["metric"]["guided_correct_step_rate"],
                      "denominator": summary["metric"]["denominator"],
                      "taxonomy": summary["taxonomy_distribution"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
