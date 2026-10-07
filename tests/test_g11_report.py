"""G11R-01 regresyonu: ana metrik paydası donmuş full_step kümesidir, üretilemeyen vaka ondan düşmez.

Bağımsız inceleme (20261007): rapor `correct ÷ verdict'lı vaka` (1/6) yayımlıyordu; donmuş
DELIVERY-PLAN tanımı `correct full_step ÷ full_step` (1/9). Bu dosya sentetik bir ağaçla — biri
geçen, biri build hatası alıp verdict üretemeyen, biri hiç koşmamış (pending) full_step vaka ve bir
referanssız vaka — `compute()` ve `render()` sözleşmesini çiviler: build/evaluator hatası ve
bekleyen vakalar paydada KALIR, koşullu oran ayrı adla verilir, manifest kapsamı değişmez.
"""
import importlib.util
import json
import pathlib

from drawingto3d.app import ROOT as SRC_ROOT  # noqa: F401  (app import zinciri testlerin geri kalanıyla aynı)

G11 = (pathlib.Path(__file__).resolve().parents[1]
       / "eval/audits/20261007-guided-g11/g11_report.py")


def _load():
    spec = importlib.util.spec_from_file_location("g11_report_under_test", G11)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path):
    manifest = {
        "manifest_version": 2, "frozen_before_results": True,
        "cases": [
            {"case_id": "ok-vector", "expected_scope_class": "full_step",
             "source_path": "examples/a.png", "source_sha256": "x"},
            {"case_id": "broken-raster", "expected_scope_class": "full_step",
             "source_path": "examples/b.png", "source_sha256": "y"},
            {"case_id": "never-ran-raster", "expected_scope_class": "full_step",
             "source_path": "examples/c.png", "source_sha256": "z"},
            {"case_id": "no-ref-raster", "expected_scope_class": "callout_scope_only",
             "source_path": "examples/d.png", "source_sha256": "w"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    base = {"run_id": "r1", "git_head": "0ff46a8", "source_sha256_checked": True,
            "candidate_count": 5, "ignored_count": 3, "transcription_count": 1,
            "parse_success_count": 1, "proposal_accept_count": 0,
            "manual_target_correction_count": 0, "build_blockers": [], "step_reopen": "reopen",
            "bbox": None, "failures": [], "review_import_used": False, "user_interventions": {}}
    (cases_dir / "ok-vector.json").write_text(json.dumps({
        **base, "build_success": True, "final_geometry_verdict": {"pass": True}}), encoding="utf-8")
    (cases_dir / "broken-raster.json").write_text(json.dumps({
        **base, "build_success": False, "final_geometry_verdict": None,
        "failures": [{"code": "CAD_UNSUPPORTED", "detail": {"what": "build did not produce a STEP"}}],
    }), encoding="utf-8")
    # never-ran-raster: kayıt yok — pending.
    (cases_dir / "no-ref-raster.json").write_text(json.dumps({
        **base, "build_success": True, "final_geometry_verdict": {"pass": True}}), encoding="utf-8")
    return manifest_path, cases_dir


def test_denominator_keeps_unproduced_and_pending_full_step_cases(tmp_path):
    """1/3: verdict üretemeyen build hatası ve hiç koşmamış vaka paydadan düşmez (eski hâl 1/2'di)."""
    module = _load()
    manifest_path, cases_dir = _fixture(tmp_path)
    summary = module.compute(manifest_path, cases_dir)
    metric = summary["metric"]
    assert metric["denominator"] == 3
    assert metric["correct"] == ["ok-vector"]
    assert metric["guided_correct_step_rate"] == 1 / 3, metric
    assert metric["unproduced_full_step"] == ["broken-raster", "never-ran-raster"]
    # Koşullu oran yalnız verdict'lı vakalar arasında ve AYRI adla; ana metrik değildir.
    assert metric["with_verdict"] == 1
    assert metric["conditional_correct_rate_among_verdicts"] == 1.0
    assert "ana metrik DEĞİLDİR" in metric["conditional_definition"]
    # Referanssız vaka paydanın dışında kalır; manifest kapsamı değişmemiştir.
    assert [row["case_id"] for row in summary["cases"] if row["scope_class"] == "callout_scope_only"] \
        == ["no-ref-raster"]
    assert not any(row["case_id"] == "no-ref-raster" for row in summary["cases"]
                   if row["scope_class"] == "full_step")
    # Pending vaka dürüstlük bölümünde açıkça listelenir.
    assert summary["honesty"]["pending"] == ["never-ran-raster"]
    assert summary["honesty"]["cases_recorded"] == 3


def test_rendered_markdown_names_the_primary_rate_and_the_conditional_separately(tmp_path):
    module = _load()
    manifest_path, cases_dir = _fixture(tmp_path)
    markdown = module.render(module.compute(manifest_path, cases_dir))
    assert "GUIDED_CORRECT_STEP_RATE = 0.3333** (1/3 full_step vaka)" in markdown
    assert "paydadan düşülmez (G11R-01)" in markdown
    assert "Koşullu oran (bilgi; ana metrik değildir): 1.0000 (1/1)" in markdown
    assert "üretilmedi" in markdown          # verdict'sız full_step satırı tabloda dürüst görünür
    assert "(bekliyor)" in markdown


def test_the_official_manifest_still_has_nine_full_step_and_one_reference_free():
    """Manifest kapsamı bu düzeltme turunda değişmedi (inceleme: 9 full_step + 1 referanssız)."""
    manifest = json.loads((G11.parents[3] / "eval/guided_10_manifest.json").read_text(encoding="utf-8"))
    classes = [entry["expected_scope_class"] for entry in manifest["cases"]]
    assert classes.count("full_step") == 9
    assert classes.count("callout_scope_only") == 1


def test_the_published_report_carries_the_fixed_denominator():
    """Yayımlanan resmî rapor 1/9 taşır; koşullu oran ayrı adla vardır (G11R-01)."""
    report = json.loads((G11.parents[3] / "eval/guided_10_report.json").read_text(encoding="utf-8"))
    metric = report["metric"]
    assert metric["denominator"] == 9
    assert metric["guided_correct_step_rate"] == 1 / 9
    assert metric["with_verdict"] == 6
    assert metric["conditional_correct_rate_among_verdicts"] == 1 / 6
