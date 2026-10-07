"""Read-only audit of G11 records; emits JSON. Exit 1 = acceptance evidence discrepancy."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "eval/audits/20261007-guided-g11"


def main():
    manifest = json.loads((ROOT / "eval/guided_10_manifest.json").read_text())
    report = json.loads((ROOT / "eval/guided_10_report.json").read_text())
    cases = [(entry, json.loads((BASE / "cases" / (entry["case_id"] + ".json")).read_text()))
             for entry in manifest["cases"]]
    eligible = [(entry, record) for entry, record in cases if entry["expected_scope_class"] == "full_step"]
    correct = [entry["case_id"] for entry, record in eligible
               if (record.get("final_geometry_verdict") or {}).get("pass") is True]
    expected = len(correct) / len(eligible)
    missing = [entry["case_id"] for entry, record in cases
               if not all(record.get("artifacts", {}).get(name)
                          and (ROOT / record["artifacts"][name]).exists()
                          for name in ("session-public.json", "review-bundle.json"))]
    mislabeled = [{"case_id": entry["case_id"], "detail": failure["detail"]}
                  for entry, record in cases for failure in record.get("failures", [])
                  if failure["code"] == "EVALUATOR" and "console_errors" in failure["detail"]]
    checks = [
        {"id": "G11R-01", "expected_denominator": len(eligible), "correct": correct,
         "expected_rate": expected, "reported_rate": report["metric"]["guided_correct_step_rate"],
         "reported_denominator": report["metric"]["with_verdict"],
         "passed": abs(report["metric"]["guided_correct_step_rate"] - expected) < 1e-12},
        {"id": "G11R-04", "missing_session_evidence": missing, "passed": not missing},
        {"id": "G11R-05", "browser_failures_labeled_evaluator": mislabeled, "passed": not mislabeled},
    ]
    print(json.dumps({"checks": checks, "passed": all(row["passed"] for row in checks)},
                     ensure_ascii=False, indent=2))
    return 0 if all(row["passed"] for row in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
