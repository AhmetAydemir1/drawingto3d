"""SEMREAD-001C — PLAN-12 §15 (P1): region contract v2.

Kapsam (PLAN-12 §15.3 / §49 kontrol listesi):

* `semread-candidates/2` + `semread-candidate-reader/2` sürüm bump'ı;
* region şeması `minimum: 0, maximum: 1` taşır ve `source.region`, `source.callout_region`,
  `target.region` **aynı** sözleşmeden gelir (kopya literal yok);
* ortak V/VE görev metni normalize koordinat kuralını açıkça öğretir (top-left/bottom-right,
  "Never return pixel coordinates", yalnız koordinat biçimi için örnek);
* piksel koordinatlı örnek şema/Pydantic tarafından **reddedilir**; normalize örnek kabul edilir;
* prompt'ta gold/sayfaya özel metin yok.

Model çağrısı yok; yalnız şema + parser + prompt (saf fonksiyonlar).
"""

from __future__ import annotations

import json

import pytest

from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION, CANDIDATE_SCHEMA_VERSION,
                                             TASK_INSTRUCTIONS, CandidateParseError, Region,
                                             candidate_json_schema, candidate_prompt,
                                             parse_candidate_json)

GOLD_SENTINEL = "semread-001b-gold-sentinel-4f21"

PIXEL_REGION = {"x0": 65, "y0": 287, "x1": 349, "y1": 450}
NORMALIZED_REGION = {"x0": 0.10, "y0": 0.20, "x1": 0.30, "y1": 0.40}


def _candidate_body(region: dict) -> str:
    return json.dumps({
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "items": [{
            "candidate_id": "c1",
            "source": {"image_id": "image-1", "region": region},
        }],
    })


def _region_schemas() -> dict[str, dict]:
    items = candidate_json_schema()["properties"]["items"]["items"]["properties"]
    return {
        "source.region": items["source"]["properties"]["region"],
        "source.callout_region": items["source"]["properties"]["callout_region"],
        "target.region": items["target"]["properties"]["region"],
    }


def test_p1_versions_are_bumped():
    """PLAN-12 §13: çıktıyı etkileyen değişiklik sürümü ilerletir."""
    assert CANDIDATE_SCHEMA_VERSION == "semread-candidates/2"
    assert CANDIDATE_READER_VERSION == "semread-candidate-reader/2"


def test_p1_region_schema_declares_normalized_bounds_in_all_three_places():
    schemas = _region_schemas()
    for name, region in schemas.items():
        for key in ("x0", "y0", "x1", "y1"):
            prop = region["properties"][key]
            assert prop["minimum"] == 0.0, f"{name}.{key}"
            assert prop["maximum"] == 1.0, f"{name}.{key}"
        assert "Never use pixel coordinates." in region["description"], name
        assert "[0,1]" in region["description"], name
    # Aynı sözleşme: üç alanın property tanımları birebir aynı nesneden gelir.
    assert schemas["source.region"]["properties"] == schemas["source.callout_region"]["properties"]
    assert schemas["source.region"]["properties"] == schemas["target.region"]["properties"]
    assert schemas["source.region"]["required"] == ["x0", "y0", "x1", "y1"]


def test_p1_pixel_coordinates_are_rejected_not_repaired():
    """Sessiz normalize yok (PLAN-12 §38/§39): piksel bölge reddedilir."""
    with pytest.raises(ValueError):
        Region(x0=65.0, y0=287.0, x1=349.0, y1=450.0)
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(_candidate_body(PIXEL_REGION))
    assert "0..1" in str(excinfo.value)


def test_p1_normalized_example_is_accepted():
    region = Region(**NORMALIZED_REGION)
    assert region.as_list() == [0.10, 0.20, 0.30, 0.40]
    response = parse_candidate_json(_candidate_body(NORMALIZED_REGION))
    assert response.items[0].source.region.as_list() == [0.10, 0.20, 0.30, 0.40]


def test_p1_common_prompt_teaches_the_normalized_convention_in_both_arms():
    """V ve VE aynı ortak metni görür; fark yalnız gözlem tablosudur (§15.2)."""
    v_prompt = candidate_prompt(["image-1"])
    ve_prompt = candidate_prompt(["image-1"], observations=[
        {"id": "t0", "kind": "text", "text": "Ø8", "value": 8.0, "unit": "mm",
         "region": [0.1, 0.2, 0.3, 0.4]},
    ])
    for prompt in (v_prompt, ve_prompt):
        assert TASK_INSTRUCTIONS in prompt
        assert "x0,y0,x1,y1 in [0,1]" in prompt
        assert "Top-left is (0,0), bottom-right is (1,1)." in prompt
        assert "Never return pixel coordinates." in prompt
        assert '{"x0":0.10,"y0":0.20,"x1":0.30,"y1":0.40}' in prompt
    assert "observation_id | kind | text" not in v_prompt
    assert "observation_id | kind | text" in ve_prompt
    # Ortak metin birebir aynı: koordinat bloğu iki kolda da TASK_INSTRUCTIONS'tan gelir.
    assert TASK_INSTRUCTIONS.rstrip("\n") == v_prompt.split("Image ids")[0].rstrip("\n")


def test_p1_prompt_carries_no_gold_or_page_specific_text():
    for prompt in (candidate_prompt(["image-1"]),
                   candidate_prompt(["image-1"], observations=[
                       {"id": "g0", "kind": "circle", "text": None, "value": None,
                        "unit": None, "region": [0.1, 0.1, 0.3, 0.3]},
                   ])):
        assert GOLD_SENTINEL not in prompt
        for marker in ("dev-plate-pocket", "Exercise", "Flange", "semread-001b-gold",
                       "frozen-"):
            assert marker not in prompt
        # Örnek yalnız koordinat biçimidir: piksel örneği yok.
        assert '"x0":65' not in prompt
        assert '"x0":0.10' in prompt
