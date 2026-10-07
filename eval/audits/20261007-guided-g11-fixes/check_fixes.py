"""G11R-01–05 acceptance check for the fix round — read-only, exit 0 only when all green.

    .venv/bin/python eval/audits/20261007-guided-g11-fixes/check_fixes.py

Mirrors the independent review's own checks (audit_g11.py) against the post-fix tree, plus the
things this round added: corrected-input re-run records, the recovered-and-labeled old evidence, and
the real-browser UI result. Also asserts the old evidence is untouched (git diff against the
reviewed head for the frozen manifest, official cases, recipes, shots and the review directory).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
G11 = ROOT / "eval/audits/20261007-guided-g11"
FIXES = ROOT / "eval/audits/20261007-guided-g11-fixes"
RERUN = G11 / "rerun-round2"
RECOVERED = G11 / "recovered"
REVIEW_HEAD = "0ff46a8"


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_r01(checks: list[dict]) -> None:
    report = load_json(ROOT / "eval/guided_10_report.json")
    manifest = load_json(ROOT / "eval/guided_10_manifest.json")
    full_step = [entry["case_id"] for entry in manifest["cases"]
                 if entry["expected_scope_class"] == "full_step"]
    correct = []
    for case_id in full_step:
        record = load_json(G11 / "cases" / f"{case_id}.json")
        if (record.get("final_geometry_verdict") or {}).get("pass") is True:
            correct.append(case_id)
    metric = report["metric"]
    want = len(correct) / len(full_step)
    ok = (metric["denominator"] == len(full_step) == 9
          and metric["guided_correct_step_rate"] == want
          and metric.get("conditional_correct_rate_among_verdicts") is not None
          and "ana metrik DEĞİLDİR" in (metric.get("conditional_definition") or ""))
    checks.append({"id": "G11R-01", "passed": ok,
                   "rate": metric["guided_correct_step_rate"], "denominator": metric["denominator"],
                   "correct": correct,
                   "conditional": metric.get("conditional_correct_rate_among_verdicts")})


def check_r02(checks: list[dict]) -> None:
    out = {"id": "G11R-02", "details": {}}
    ok = True
    for case_id, (value, span_px, ppm_range) in (("flange-raster", (35, 207.35, (5.7, 6.1))),
                                                 ("exercise-51-raster", (70, 274.8, (3.8, 4.1)))):
        recipe = load_json(RERUN / "recipes" / f"{case_id}.json")
        ok &= recipe["calibration"].get("manual_value") == value
        ok &= bool(recipe.get("input_verification"))
        record_path = RERUN / "cases" / f"{case_id}.json"
        detail = {"recipe_manual_value": recipe["calibration"]["manual_value"]}
        if record_path.exists():
            record = load_json(record_path)
            calibration = (record.get("calibration") or {})
            first, second = calibration.get("first"), calibration.get("second")
            px = None
            if first and second:
                px = ((second[0] - first[0]) ** 2 + (second[1] - first[1]) ** 2) ** 0.5
            ppm = (px / calibration["value"]) if px and calibration.get("value") else None
            detail.update({"record_calibration_value": calibration.get("value"), "span_px": px,
                           "px_per_mm": ppm,
                           "recipe_sha_matches": record.get("recipe_sha256")
                           == _sha256(RERUN / "recipes" / f"{case_id}.json"),
                           "input_verification_carried": bool(record.get("input_verification")),
                           "recipe_notes_carried": bool(record.get("recipe_notes"))})
            ok &= calibration.get("value") == value
            ok &= bool(record.get("input_verification")) and bool(record.get("recipe_notes"))
            ok &= detail["recipe_sha_matches"]
            if ppm is not None:
                ok &= ppm_range[0] <= ppm <= ppm_range[1]
        else:
            detail["record"] = "pending-round"
            ok = ok and False  # the round must be complete for acceptance
        out["details"][case_id] = detail
    # old official inputs stay as history
    old_flange = load_json(G11 / "cases/flange-raster/session-public.json")["decisions"]["calibration"]
    old_ex51 = load_json(G11 / "cases/exercise-51-raster/session-public.json")["decisions"]["calibration"]
    out["details"]["old_flange_calibration"] = old_flange
    out["details"]["old_ex51_calibration"] = old_ex51
    ok &= old_flange.get("value") == 90 and old_ex51.get("value") == 40
    out["passed"] = ok
    checks.append(out)


def _sha256(path: pathlib.Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_r03(checks: list[dict]) -> None:
    result = load_json(FIXES / "g11r03-ui-result.json")
    joined = " | ".join(row["step"] for row in result["steps"])
    required = ("S1 ignore #callout-ignore (middle row, hidden)",
                "S3 hint-ignore advances",
                "S4 last open row with ignored-visible",
                "S6 last open row hidden",
                "S2 manual Sonraki eksik wraps")
    checks.append({"id": "G11R-03", "passed": bool(result["passed"])
                   and all(item in joined for item in required),
                   "steps_passed": sum(1 for row in result["steps"] if row["passed"]),
                   "steps_total": len(result["steps"]), "failures": result["failures"]})


def check_r04(checks: list[dict]) -> None:
    missing = []
    for case_id in ("flange-raster", "exercise-51-raster"):
        record_path = RERUN / "cases" / f"{case_id}.json"
        if not record_path.exists():
            missing.append({case_id: "pending-round"})
            continue
        record = load_json(record_path)
        for name in ("session-public.json", "review-bundle.json", "readiness.json"):
            path = (record.get("artifacts") or {}).get(name)
            if not (path and (ROOT / path).exists()):
                missing.append({case_id: name})
        if not record.get("session_token") or not isinstance(record.get("readiness"), dict):
            missing.append({case_id: "token/readiness fields"})
    recovered = []
    for case_id in ("exercise-13-raster", "exercise-17-raster", "my-part-raster",
                    "flange-elbow-90-raster-noref"):
        label_path = RECOVERED / case_id / "RECOVERY.json"
        row = {"case_id": case_id,
               "files": sorted(path.name for path in (RECOVERED / case_id).glob("*.json"))
               if label_path.parent.exists() else []}
        if label_path.exists():
            label = load_json(label_path)
            row["labeled"] = (label.get("label") == "recovered-after-run"
                              and label.get("not_run_time_evidence") is True
                              and label.get("session_untouched") is True)
            row["refusal_gate"] = load_json(RECOVERED / case_id / "server-error-recompute.json").get("gate")
        else:
            row["labeled"] = False
        recovered.append(row)
    ok = (not missing and all(row["labeled"] for row in recovered)
          and all(len(row["files"]) == 5 for row in recovered))
    checks.append({"id": "G11R-04", "passed": ok, "r2_missing": missing, "recovered": recovered})


def check_r05(checks: list[dict]) -> None:
    problems = []
    for case_id in ("flange-raster", "exercise-51-raster"):
        record_path = RERUN / "cases" / f"{case_id}.json"
        if not record_path.exists():
            problems.append({case_id: "pending-round"})
            continue
        record = load_json(record_path)
        for failure in record.get("failures") or []:
            if failure["code"] == "EVALUATOR":
                problems.append({case_id: "EVALUATOR label present", "detail": failure["detail"]})
        signals = record.get("browser_signals")
        if not isinstance(signals, dict) or "assets" not in signals:
            problems.append({case_id: "browser_signals missing"})
    # no runner path turns console/network noise into EVALUATOR any more
    source = (G11 / "g11_runner.py").read_text(encoding="utf-8")
    if 'fail("EVALUATOR", {"console_errors"' in source:
        problems.append("runner still labels browser noise as EVALUATOR")
    checks.append({"id": "G11R-05", "passed": not problems, "problems": problems})


def check_old_evidence_untouched(checks: list[dict]) -> None:
    # 0ff46a8'de var olan kanıt dosyaları değişmemiş/silinmemiş olmalı; inceleme dizini o commit'te
    # henüz izlenmiyordu, ilk kez bu turda commit edildi — yalnız EKLENEN (A) dosyalar kabuldür.
    diff = subprocess.run(
        ["git", "diff", "--diff-filter=MDR", "--name-status", f"{REVIEW_HEAD}..HEAD", "--",
         "eval/audits/20261007-guided-g11/cases", "eval/audits/20261007-guided-g11/recipes-official",
         "eval/audits/20261007-guided-g11/recipes-resume", "eval/audits/20261007-guided-g11/shots",
         "eval/audits/20261007-guided-g11/logs/official", "eval/guided_10_manifest.json",
         "eval/audits/20261007-guided-g9-g11-independent-review"],
        cwd=ROOT, capture_output=True, text=True)
    uncommitted = subprocess.run(
        ["git", "status", "--short", "--",
         "eval/audits/20261007-guided-g11/cases", "eval/audits/20261007-guided-g11/recipes-official",
         "eval/audits/20261007-guided-g11/recipes-resume", "eval/audits/20261007-guided-g11/shots",
         "eval/audits/20261007-guided-g11/logs/official", "eval/guided_10_manifest.json",
         "eval/audits/20261007-guided-g9-g11-independent-review"],
        cwd=ROOT, capture_output=True, text=True)
    ok = not diff.stdout.strip() and not uncommitted.stdout.strip()
    checks.append({"id": "old-evidence-untouched", "passed": ok,
                   "diff": diff.stdout.strip(), "untracked_or_modified": uncommitted.stdout.strip()})


def main() -> int:
    checks: list[dict] = []
    check_r01(checks)
    check_r02(checks)
    check_r03(checks)
    check_r04(checks)
    check_r05(checks)
    check_old_evidence_untouched(checks)
    print(json.dumps({"checks": checks, "passed": all(row["passed"] for row in checks)},
                     ensure_ascii=False, indent=2))
    return 0 if all(row["passed"] for row in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
