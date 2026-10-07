"""G12.0 truth lock — G11 tarihsel gerçeği ve donmuş manifest bu koşuda çivilidir (PLAN-24 §9).

Bu dosya ürün davranışını değil, ölçüm aletini çiviler:

* donmuş manifest 10 vaka / 9 full_step / 1 callout_scope_only;
* yayımlanmış G11 raporu payda 9, tek doğru `plate-pocket-vector`, oran 1/9;
* üç donmuş dosyanın bayt kimliği (manifest + rapor json + rapor md) — G12 boyunca
  değişmemeleri bir temenni değil, test (§4).

G12'nin kendi kanıtı yeni klasörlerde tutulur; bu dosya eski kanıtı *değiştirmeyi* yasaklar.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "eval/guided_10_manifest.json"
REPORT_JSON = ROOT / "eval/guided_10_report.json"
REPORT_MD = ROOT / "eval/guided_10_report.md"

FROZEN_SHA256 = {
    "eval/guided_10_manifest.json": "f4a850c344e61a90623b2f9525ff34129fe392abf0cd96a66e5d525604e248d8",
    "eval/guided_10_report.json": "423350ded42e8e98ac426c8bedacf739d4d94fbb6709f5afd0cceef6ee097587",
    "eval/guided_10_report.md": "ff1828dd8d34e95e1b62ea6d042726ef232e3e34ede445b1d0abe2caf514ce54",
}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _report() -> dict:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def test_manifest_is_ten_cases_nine_full_step_one_scope_only():
    manifest = _manifest()
    classes = [entry["expected_scope_class"] for entry in manifest["cases"]]
    assert manifest["expected_count"] == 10
    assert len(manifest["cases"]) == 10
    assert classes.count("full_step") == 9
    assert classes.count("callout_scope_only") == 1
    # Referanssız vaka gerçekten referanssızdır; kapsam sınıfı sonradan değiştirilemez.
    scope_only = [entry for entry in manifest["cases"] if entry["expected_scope_class"] == "callout_scope_only"]
    assert scope_only[0]["reference_identifier_evaluator_only"] is None
    assert scope_only[0]["reference_available"] is False


def test_report_pins_denominator_correct_and_rate():
    """Ana metrik: correct full_step ÷ donmuş full_step kümesi = 1/9 — üretilemeyen düşmez (G11R-01)."""
    metric = _report()["metric"]
    assert metric["denominator"] == 9
    assert metric["correct"] == ["plate-pocket-vector"]
    assert abs(metric["guided_correct_step_rate"] - 1 / 9) < 1e-12
    assert metric["unproduced_full_step"] == ["exercise-17-raster", "exercise-13-raster", "my-part-raster"]
    assert metric["with_verdict"] == 6
    assert abs(metric["conditional_correct_rate_among_verdicts"] - 1 / 6) < 1e-12
    # Koşullu oran ayrı adla yaşar ve ana metrik olmadığını kendisi söyler.
    assert "ana metrik DEĞİLDİR" in metric["conditional_definition"]


def test_frozen_evidence_is_byte_identical():
    """Manifest ve yayımlanmış raporlar bayt kimliğiyle çivilidir: G12 bunları değiştiremez."""
    for relative, digest in FROZEN_SHA256.items():
        path = ROOT / relative
        assert path.exists(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
