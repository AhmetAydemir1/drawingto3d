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
from drawingto3d.semantic_candidate_reader import read_page
from drawingto3d.semantic_schema import PreparedImage

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


# ---------------------------------------------------------------- P2: compact output


def _minimal_body() -> str:
    """Yalnız zorunlu alanlar: candidate_id + source{image_id, region}."""
    return _candidate_body(NORMALIZED_REGION)


class _FakeChat:
    """Taşıma sınırında duran taklit: ağ yok; stats/trace/raw_response doldurulur."""

    def __init__(self, answer: str, *, done_reason: str = "stop") -> None:
        self.answer = answer
        self.done_reason = done_reason

    def complete(self, prompt, **kwargs):
        kwargs["stats"].update({"done_reason": self.done_reason, "eval_count": 12,
                                "prompt_eval_count": 40})
        kwargs["trace"].update({"model": "fake-model:1b", "options": {"temperature": 0.0},
                                "messages": [{"role": "user", "content": prompt}]})
        kwargs["raw_response"].update({"done": True})
        return self.answer


def _bundle() -> dict:
    return {"arm": "V", "page_image_id": "image-1",
            "images": [PreparedImage(image_id="image-1", kind="full_page",
                                     png=_tiny_png(), source_sha256="a" * 64,
                                     source_type="raster", render_mode="native_raster")],
            "image_ids": ["image-1"], "observations": [], "arm_input_variant": "V",
            "evidence_mode": "raw_only"}


def _tiny_png(width: int = 8, height: int = 6) -> bytes:
    """Gerçek PNG (cv2 çözebilir): sahte byte'lar `PreparedImage` doğrulamasından geçmez."""
    import cv2
    import numpy as np

    ok, buffer = cv2.imencode(".png", np.zeros((height, width), dtype=np.uint8))
    assert ok
    return buffer.tobytes()


def test_p2_optional_defaults_are_deterministic():
    first = parse_candidate_json(_minimal_body())
    candidate = first.items[0]
    assert candidate.callout.state == "unknown" and candidate.callout.text == ""
    assert candidate.representation.kind == "unknown"
    assert candidate.physical.kind == "unknown"
    assert candidate.form.symbol == "unknown"
    assert candidate.size.state == "unknown" and candidate.size.value is None
    assert candidate.count.state == "unknown" and candidate.count.printed is None
    assert candidate.termination.kind == "unknown" and candidate.termination.stated is False
    assert candidate.depth.state == "not_stated" and candidate.depth.value is None
    assert candidate.target.state == "unknown" and candidate.target.region is None
    assert candidate.uncertainty.fields == {}
    second = parse_candidate_json(_minimal_body())
    assert second == first, "aynı gövde aynı varsayılanları vermeli"


def test_p2_provenance_is_not_part_of_the_wire_contract():
    schema = candidate_json_schema()
    assert "provenance" not in schema["properties"]["items"]["items"]["properties"]
    payload = json.loads(_minimal_body())
    payload["items"][0]["provenance"] = {"kind": "vlm", "method": "kendi kendine"}
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(json.dumps(payload))
    assert "provenance" in str(excinfo.value)
    assert excinfo.value.kind == "schema_error"


def test_p2_prompt_asks_to_omit_default_only_optional_fields():
    for prompt in (candidate_prompt(["image-1"]), candidate_prompt(["image-1"], observations=[
            {"id": "t0", "kind": "text", "text": "Ø8", "value": 8.0, "unit": "mm",
             "region": [0.1, 0.2, 0.3, 0.4]}])):
        assert "Omit optional fields that would only contain default unknown/not_stated values." \
            in prompt


def test_p2_read_page_injects_harness_owned_provenance():
    outcome = read_page(_FakeChat(_minimal_body()), _bundle(), forbidden=[])
    assert outcome["parse"]["ok"] is True
    provenance = outcome["parsed"]["items"][0]["provenance"]
    assert provenance["kind"] == "vlm"
    assert provenance["method"] == "fake-model:1b", "method çağrıda görülen model olmalı"
    assert outcome["parsed"]["items"][0]["uncertainty"]["fields"] == {}


def test_p2_parse_error_kinds_are_machine_readable():
    with pytest.raises(CandidateParseError) as broken_json:
        parse_candidate_json("bu JSON değil")
    assert broken_json.value.kind == "invalid_json"
    with pytest.raises(CandidateParseError) as coordinate:
        parse_candidate_json(_candidate_body(PIXEL_REGION))
    assert coordinate.value.kind == "schema_coordinate"
    no_guess = json.loads(_minimal_body())
    no_guess["items"][0]["termination"] = {"kind": "finite", "stated": True}
    with pytest.raises(CandidateParseError) as guessed:
        parse_candidate_json(json.dumps(no_guess))
    assert guessed.value.kind == "schema_no_guess"
