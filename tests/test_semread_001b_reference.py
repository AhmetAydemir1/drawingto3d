"""SEMREAD-001B — P1 §13–§16: referans (gold) doğrulamasının sertleştirilmesi.

Kapsanan kurallar:

* §13 yer tutucu içerik (`EKSİK`, `TODO`, `TBD`, `PLACEHOLDER`) kapsam/kanıt alanlarında reddedilir.
* §14 hedef **ve** callout bölgesi sınırları (sonlu, 0..1, sıralı, sıfır alansız) doğrulanır.
* §15 gözlem kimliği doğrulaması fail-closed: çıkarım yokken gold `observation_id` taşıyamaz.
* §16 raster gold görsel onay (`vision_checked` + `vision` kanıtı) ister; OCR tek başına gold değildir.

Bu testler hiç model çağırmaz ve gerçek lab köküne yazmaz.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_module_reference",
                                                  ROOT / "eval/semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pilot sürücüsü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()

RASTER_PAGE = {"page_id": "page", "split": "dev", "group": "g", "path": "pyproject.toml",
               "type": "raster"}
PDF_PAGE = {**RASTER_PAGE, "type": "pdf"}


def claim(**overrides) -> dict:
    base = {"claim_id": "k1", "target": {"name": "hole-1", "observation_id": None,
                                         "region": {"x0": 0.10, "y0": 0.10, "x1": 0.20, "y1": 0.20}},
            "callout": {"region": {"x0": 0.30, "y0": 0.30, "x1": 0.34, "y1": 0.32}},
            "representation": "circle", "physical": "hole", "form": "diameter", "size": 8.0,
            "unit": "mm", "count_printed": 4, "termination": "thru", "depth": None,
            "state": "determinate_present", "evidence": "görsel inceleme yapıldı, Ø8 THRU okundu",
            "source_evidence": "tesseract+vision"}
    base.update(overrides)
    return base


def reference(**overrides) -> dict:
    base = {"schema": "semread-001b-reference/1", "page_id": "page", "split": "dev",
            "annotator": "agent", "review_status": "provisional",
            "vision_checked": True, "scope": "tek delik: Ø8 THRU",
            "exhaustiveness": {"scope": "full_page"},
            "claims": [claim()]}
    base.update(overrides)
    return base


def _check(ref: dict, page: dict | None = None, ids: list[str] | None = None, **kwargs) -> dict:
    return pilot.check_reference(ref, page or RASTER_PAGE, ids if ids is not None else [],
                                 **kwargs)


def test_a_complete_reference_passes():
    result = _check(reference())
    assert result["ok"] is True, result["problems"]
    assert result["problems"] == [] and result["claims"] == 1
    assert result["raster_vision_required"] is True


@pytest.mark.parametrize("field,value", [
    ("scope", "EKSİK: kapsam yazılmadı"),
    ("scope", "TODO"),
    ("scope", ""),
])
def test_placeholder_scope_is_rejected(field, value):
    result = _check(reference(**{field: value}))
    assert result["ok"] is False
    assert any("§13" in problem for problem in result["problems"])


def test_placeholder_exhaustiveness_and_evidence_are_rejected():
    structured = _check(reference(exhaustiveness="EKSİK: hangi bölgeler tarandı"))
    assert structured["ok"] is False
    assert any("exhaustiveness" in problem for problem in structured["problems"])

    evidence = _check(reference(claims=[claim(evidence="EKSİK: gerekçe yazılmadı")]))
    assert evidence["ok"] is False
    assert any("yer tutucu" in problem and "§13" in problem for problem in evidence["problems"])

    source = _check(reference(claims=[claim(source_evidence="PLACEHOLDER")]))
    assert source["ok"] is False
    assert any("§13" in problem for problem in source["problems"])


@pytest.mark.parametrize("region,expect", [
    ({"x0": 0.10, "y0": 0.10, "x1": 0.10, "y1": 0.20}, "sıfır alan"),
    ({"x0": 0.20, "y0": 0.10, "x1": 0.10, "y1": 0.20}, "sıfır alan/ters"),
    ({"x0": -0.10, "y0": 0.10, "x1": 0.20, "y1": 0.20}, "aralık dışı"),
    ({"x0": 0.10, "y0": 0.10, "x1": 1.20, "y1": 0.20}, "aralık dışı"),
    ([0.10, 0.10, 0.20], "4 değer"),
    ([0.10, 0.10, "x", 0.20], "sayıya çevrilemedi"),
    ({"x0": 0.10, "y0": 0.10, "x1": 0.20}, "eksik alan"),
    ("0.1,0.1,0.2,0.2", "sözlük ya da 4'lü liste değil"),
])
def test_invalid_target_regions_are_rejected(region, expect):
    result = _check(reference(claims=[claim(target={"region": region})]))
    assert result["ok"] is False
    assert any("hedef bölgesi geçersiz" in problem and expect in problem
               for problem in result["problems"]), result["problems"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_region_values_are_rejected(value):
    result = _check(reference(claims=[claim(target={"region": {"x0": 0.10, "y0": value,
                                                              "x1": 0.20, "y1": 0.20}})]))
    assert result["ok"] is False
    assert any("NaN/inf" in problem for problem in result["problems"])


def test_invalid_callout_regions_are_rejected_too():
    result = _check(reference(claims=[claim(callout={"region": {"x0": 0.40, "y0": 0.30,
                                                              "x1": 0.34, "y1": 0.32}})]))
    assert result["ok"] is False
    assert any("callout bölgesi geçersiz" in problem for problem in result["problems"])


def test_missing_callout_is_allowed():
    result = _check(reference(claims=[claim(callout=None)]))
    assert result["ok"] is True, result["problems"]


def test_observation_id_without_extraction_is_a_fail_closed_error():
    bound = claim(target={"region": {"x0": 0.10, "y0": 0.10, "x1": 0.20, "y1": 0.20},
                          "observation_id": "g0"})
    missing = _check(reference(claims=[bound]), ids=[], extraction_ok=False)
    assert missing["ok"] is False
    assert any("fail-closed" in problem for problem in missing["problems"])
    assert missing["observation_extraction_ok"] is False

    empty = _check(reference(claims=[bound]), ids=[], extraction_ok=True)
    assert empty["ok"] is False, "boş gözlem listesi doğrulamayı sessizce geçemez"

    known = _check(reference(claims=[bound]), ids=["g0", "g1"], extraction_ok=True)
    assert known["ok"] is True, known["problems"]

    unknown = _check(reference(claims=[bound]), ids=["g1"], extraction_ok=True)
    assert unknown["ok"] is False
    assert any("bilinmeyen gözlem kimliği" in problem for problem in unknown["problems"])


def test_raster_references_require_visual_adjudication():
    no_flag = _check(reference(vision_checked=False), page=RASTER_PAGE)
    assert no_flag["ok"] is False
    assert any("vision_checked" in problem for problem in no_flag["problems"])

    ocr_only = _check(reference(claims=[claim(source_evidence="tesseract")]), page=RASTER_PAGE)
    assert ocr_only["ok"] is False, "OCR tek başına gold kaynağı olamaz (§16)"
    assert any("görsel doğrulama kanıtı yok" in problem for problem in ocr_only["problems"])

    pdf = _check(reference(vision_checked=False, claims=[claim(source_evidence="pdf-text-layer")]),
                 page=PDF_PAGE)
    assert pdf["ok"] is True, pdf["problems"]


def test_exhaustiveness_regions_and_predicates_are_validated():
    empty = _check(reference(exhaustiveness={"scope": "regions", "regions": []}))
    assert empty["ok"] is False

    bad = _check(reference(exhaustiveness={"scope": "regions",
                                           "regions": [{"x0": 0.5, "y0": 0.5, "x1": 0.4,
                                                        "y1": 0.6}]}))
    assert bad["ok"] is False
    assert any("exhaustiveness bölgesi" in problem for problem in bad["problems"])

    unknown = _check(reference(exhaustiveness={"scope": "predicates",
                                               "predicates": ["size", "uydurma"]}))
    assert unknown["ok"] is False
    assert any("bilinmeyen yüklem" in problem for problem in unknown["problems"])

    known = _check(reference(exhaustiveness={"scope": "predicates", "predicates": ["size"]}))
    assert known["ok"] is True, known["problems"]


def test_placeholder_helper_is_prefix_based():
    assert pilot.placeholder_text("EKSİK: gerekçe yazılmadı") is not None
    assert pilot.placeholder_text("  TODO  ") is not None
    assert pilot.placeholder_text("tbd") is not None
    assert pilot.placeholder_text("") == "boş"
    assert pilot.placeholder_text("görsel inceleme: Ø8 THRU") is None
    assert pilot.placeholder_text("kanıt eksikti ama okundu") is None, \
        "yer tutucu yalnız önekle tanınır; cümle içi geçiş yanlış pozitif üretmez"
