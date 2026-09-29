"""Run the feature evaluator over the counter-example matrix and write the audit evidence.

    .venv/bin/python eval/feature_metrics_audit.py

Writes, under `out/lab/evaluator-audit/`:

    fixtures/*.step      every fixture part as it was evaluated
    verdicts.json        one record per case: expected verdict, actual verdict, failed checks,
                         issues, alignment, and the coarse evaluator's verdict for comparison
    report.md            the same, as a readable table

The coarse verdict comes from `eval/metrics.py` running in the CadQuery interpreter
(`.venv-cad`), which is what the project used until now. Where the two disagree, that disagreement
is the point of H01 and is recorded, not smoothed over.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "lab" / "evaluator-audit"
CAD_PYTHON = ROOT / ".venv-cad" / "bin" / "python"
COARSE = ROOT / "eval" / "metrics.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load("feature_metrics_audit_target", ROOT / "eval" / "feature_metrics.py")
fixtures = _load("feature_fixtures_audit_target", ROOT / "eval" / "feature_fixtures.py")


def coarse_verdict(produced: Path, reference: Path) -> str:
    """`eval/metrics.py` in the CadQuery interpreter: pass/fail/not_run."""
    if not CAD_PYTHON.exists():
        return "not_run"
    completed = subprocess.run(
        [str(CAD_PYTHON), str(COARSE), str(produced), str(reference)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    if completed.returncode != 0:
        return f"error({completed.returncode})"
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return "unparsed"
    return "pass" if payload["verdict"]["pass"] else "fail"


def main() -> int:
    directory = OUT / "fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in fixtures.PARTS:
        paths[name] = fixtures.export(name, directory)

    records = []
    for case in fixtures.CASES:
        reference = metrics.extract(paths[case["reference"]],
                                    units=fixtures.SPECS[case["reference"]]["units"])
        produced = metrics.extract(paths[case["produced"]],
                                   units=case.get("produced_units", fixtures.SPECS[case["produced"]]["units"]))
        verdict = metrics.compare(produced, reference)
        record = {
            "case": case["name"],
            "why": case["why"],
            "reference": case["reference"],
            "produced": case["produced"],
            "expected_verdict": case["expect"],
            "actual_verdict": verdict["verdict"],
            "agrees": verdict["verdict"] == case["expect"],
            "failed_checks": verdict["failed_checks"],
            "expected_checks": case.get("expect_checks", []),
            "expected_issue_types": case.get("expect_reasons", []),
            "issue_types": sorted({issue["type"] for issue in verdict["issues"]}),
            "alignment": None if verdict["alignment"] is None else verdict["alignment"]["rotation"],
            "features_produced": [
                {"id": f["id"], "kind": f["kind"], "diameter_mm": f["diameter_mm"], "centre": f["centre"]}
                for f in produced["features"]
            ],
            "coarse_evaluator": coarse_verdict(paths[case["produced"]], paths[case["reference"]]),
            "coarse_evaluator_expected": case.get("old_evaluator"),
        }
        records.append(record)
        mark = "OK " if record["agrees"] else "HATA"
        print(f"{mark} {case['name']:48s} beklenen={case['expect']:14s} gerçek={verdict['verdict']:14s} "
              f"kaba={record['coarse_evaluator']}")

    (OUT / "verdicts.json").write_text(json.dumps({
        "evaluator": metrics.EVALUATOR_VERSION,
        "schema": metrics.SCHEMA_VERSION,
        "tolerances": metrics.TOLERANCES,
        "pairing_windows": {"centre_mm": metrics.PAIR_WINDOW_MM,
                            "diameter_mm": metrics.PAIR_DIAMETER_WINDOW_MM},
        "probe_mm": metrics.PROBE_MM,
        "fixture_directory": str(directory),
        "cases": records,
    }, indent=2, ensure_ascii=False) + "\n")

    (OUT / "report.md").write_text(report(records), encoding="utf-8")
    failures = [record for record in records if not record["agrees"]]
    print(f"\n{len(records)} vaka, uyuşmayan {len(failures)}")
    print(f"kanıt: {OUT / 'report.md'}")
    return 1 if failures else 0


def report(records: list[dict]) -> str:
    lines = [
        "# H01 — özellik değerlendiricisi denetimi",
        "",
        f"Değerlendirici sürümü: `{metrics.EVALUATOR_VERSION}`, şema `{metrics.SCHEMA_VERSION}`.",
        "Fixture'ların doğru cevabı elle yazılmış analitik spec'tir (`eval/feature_fixtures.py`), "
        "üretim kodundan veya değerlendiricinin çıktısından kopyalanmaz.",
        "",
        "Sabitlenmiş toleranslar (sonuç görülmeden önce): "
        + ", ".join(f"`{key}={value}`" for key, value in metrics.TOLERANCES.items()),
        f"Eşleştirme pencereleri (yalnız hata adı vermek için): merkez {metrics.PAIR_WINDOW_MM} mm, "
        f"çap {metrics.PAIR_DIAMETER_WINDOW_MM} mm. Uç sondası {metrics.PROBE_MM} mm.",
        "",
        "| Vaka | Beklenen | Sonuç | Kaba değerlendirici | Hatalı kontroller | Sorun türleri |",
        "|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {record['case']} | {record['expected_verdict']} | "
            f"{'✓ ' if record['agrees'] else '✗ '}{record['actual_verdict']} | "
            f"{record['coarse_evaluator']} | "
            f"{', '.join(record['failed_checks']) or '—'} | "
            f"{', '.join(record['issue_types']) or '—'} |"
        )
    lines += [
        "",
        "## Kaba değerlendiricinin kaçırdıkları",
        "",
        "Aşağıdaki vakalarda `eval/metrics.py` (eski, tarihsel karşılaştırma için korunuyor) yanlış "
        "parçayı geçiriyor; yeni değerlendirici reddediyor.",
        "",
        "| Vaka | Kaba | Yeni | Neden yanlış |",
        "|---|---|---|---|",
    ]
    for record in records:
        if record["coarse_evaluator"] == "pass" and record["expected_verdict"] == "fail":
            lines.append(f"| {record['case']} | pass | {record['actual_verdict']} | {record['why']} |")
    lines += [
        "",
        "## Vaka gerekçeleri",
        "",
    ]
    for record in records:
        lines.append(f"- **{record['case']}** — {record['why']} "
                     f"(beklenen `{record['expected_verdict']}`, sonuç `{record['actual_verdict']}`"
                     f"{'' if record['alignment'] is None else ', hizalama ' + record['alignment']})")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
