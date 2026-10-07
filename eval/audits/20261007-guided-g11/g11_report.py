"""G11 report — reads the frozen manifest + `cases/*.json`, writes the two PLAN §17 deliverables.

    .venv/bin/python eval/audits/20261007-guided-g11/g11_report.py

Outputs:
  eval/guided_10_report.json — machine summary (per-case rows, metric, taxonomy distribution, honesty)
  eval/guided_10_report.md   — the same, for humans

Rules: a case without a record is `pending` — the metric is reported over the run cases and the
pending list is explicit, never silently dropped. GUIDED_CORRECT_STEP_RATE = cases whose frozen
verdict `pass` is true ÷ cases with a geometry verdict (no-reference cases report scope completeness
instead and are outside the rate). The product-HEAD check asserts that no `src/`, `tests/` or
`pyproject.toml` change happened between the first and the last case.
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


def main() -> int:
    manifest = json.loads((ROOT / "eval/guided_10_manifest.json").read_text(encoding="utf-8"))
    cases = []
    for entry in manifest["cases"]:
        case_id = entry["case_id"]
        path = G11 / "cases" / f"{case_id}.json"
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
    with_verdict = [row for row in recorded if row.get("verdict_pass") is not None]
    correct = [row for row in with_verdict if row["verdict_pass"]]
    rate = (len(correct) / len(with_verdict)) if with_verdict else None
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
        "metric": {"guided_correct_step_rate": rate,
                   "correct": [row["case_id"] for row in correct],
                   "with_verdict": len(with_verdict)},
        "taxonomy_distribution": dict(taxonomy),
        "cases": cases, "honesty": honesty,
    }
    out_json = ROOT / "eval/guided_10_report.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# G11 — ilk 10-pafta koşusu, sonuç raporu", ""]
    lines.append(f"- Kayıtlı vaka: **{len(recorded)}/{len(cases)}** · bekleyen: "
                 f"{', '.join(honesty['pending']) or '—'}")
    if rate is not None:
        lines.append(f"- **GUIDED_CORRECT_STEP_RATE = {rate:.2f}** "
                     f"({len(correct)}/{len(with_verdict)} geometri kararı olan vaka)")
    else:
        lines.append("- Henüz geometri kararı olan vaka yok; metrik bekliyor.")
    lines.append(f"- Taksonomi dağılımı: {dict(taxonomy) or '—'}")
    lines.append(f"- Ürün kodu değişmedi (ilk→son vaka HEAD): {'evet' if honesty['same_product_head'] else 'HAYIR'}")
    lines.append("")
    lines.append("| vaka | sınıf | aday | kapsam dışı | metin | derleme | verdict | taksonomi |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in cases:
        if row["status"] == "pending":
            lines.append(f"| {row['case_id']} | {row['scope_class']} | — | — | — | — | — | (bekliyor) |")
        else:
            verdict = ("pass" if row["verdict_pass"] else
                       (f"fail ({'şekil ok, detay -' if row['verdict_shape_ok'] else 'şekil -'})"
                        if row["verdict_pass"] is not None else "—"))
            lines.append(f"| {row['case_id']} | {row['scope_class']} | {row['candidate_count']} | "
                         f"{row['ignored_count']} | {row['transcription_count']} | "
                         f"{'ok' if row['build_success'] else 'durdu'} | {verdict} | "
                         f"{', '.join(row['failure_codes']) or '—'} |")
    lines.append("")
    lines.append("## Dürüstlük notları")
    lines.append(f"- Her vaka taze oturumda, aynı ürün HEAD'inde koştu; kayıtlar `git_head` taşır; "
                 f"ilk→son ürün kodu farkı: {'yok' if honesty['same_product_head'] else 'VAR'}.")
    lines.append(f"- sha256 doğrulaması tüm kayıtlı vakalar: "
                 f"{'tamam' if honesty['sha256_checked_all_recorded'] else 'EKSİK'}.")
    lines.append("- Referans STEP'ler yalnız evaluator'a verildi; kararlar `recipes/*.json` içinde, "
                 "görünen oturum verisi + çizim okumasıyla alındı.")
    lines.append("- Bekleyen vakalar listede açıkça `pending`; sessiz örneklem yok.")
    (ROOT / "eval/guided_10_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"recorded": len(recorded), "rate": rate, "taxonomy": dict(taxonomy)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
