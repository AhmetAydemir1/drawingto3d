"""SEMREAD-001D — semantik-içerik sözleşmesi (PLAN-14 "skeleton sonrası güncel plan" §3/§5/§6/§7/§8/§9).

Kapsam (0 inference; yalnız saf fonksiyonlar + taşıma taklidi):

* **Tek kaynak (§3):** `semantic_claim_flags` / `candidate_has_semantic_claim` / `evidence_flags` —
  parser, dev raporu, final değerlendirici ve testler aynı tanımı reuse eder; ayrıca tanım kayıtlı
  `response-parsed.json` sözlükleriyle de çalışır.
* **semantic claim ≠ evidence-only (§3/§8):** temsil, bulunan-circle sayısı, hedef durumu/kimliği,
  kaynak bölgesi ve belirsizlik **tek başına** adayı geçerli saymaz.
* **Wire reddi (§5):** `parse_candidate_json` semantik-içeriksiz adayı `schema_semantic_empty` alt
  türüyle reddeder — sıra: JSON → yapısal doğrulama → semantik doğrulama → (çağıranda) referanslar;
  boş `items` geçerli abstention olarak kalır (§7).
* **D yolu audit'i (§6):** D kolu `Candidate` nesnelerini doğrudan kurar ve wire parser'dan geçmez;
  kural **global Pydantic validator değildir**, D çıktı yolu etkilenmez.

Fixture'lar generiktir: sayfaya/gold'a özgü metin yok (frozen/dev cevap sızıntısı yok).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import drawingto3d.semantic_candidate_reader as reader_module
import drawingto3d.semantic_deterministic as deterministic_module
from drawingto3d.semantic_candidate_reader import read_page
from drawingto3d.semantic_candidates import (CANDIDATE_SCHEMA_VERSION, EVIDENCE_SOURCES,
                                             SEMANTIC_CLAIM_SOURCES, Candidate, CandidateParseError,
                                             CandidateResponse, candidate_has_semantic_claim,
                                             evidence_flags, parse_candidate_json,
                                             semantic_claim_flags)
from drawingto3d.semantic_schema import PreparedImage

REGION = {"x0": 0.10, "y0": 0.20, "x1": 0.30, "y1": 0.40}


def evidence_only(**overrides) -> dict:
    """Yalnız kanıt alanları taşıyan aday gövdesi: `candidate_id` + `source.region` (+ overrides)."""
    base = {"candidate_id": "e1", "source": {"image_id": "image-1", "region": dict(REGION)}}
    base.update(overrides)
    return base


def body(*items: dict) -> str:
    return json.dumps({"schema_version": CANDIDATE_SCHEMA_VERSION, "items": list(items)},
                      ensure_ascii=False)


# ----------------------------------------------------------- negatif matris (§8)


NEGATIVE_BODIES = {
    "source_region_only": {},
    "representation_only": {"representation": {"kind": "circle", "diameter_px": 42.0}},
    "found_circles_only": {"count": {"found_circles": 3}},
    "target_state_only": {"target": {"state": "bound"}},
    "observation_id_only": {"target": {"observation_id": "g-1"}},
    "uncertainty_only": {"uncertainty": {"fields": {"physical": "kesit görünmüyor"},
                                         "reason": "tek görünüş"}},
}
NEGATIVE_EVIDENCE_KEY = {"source_region_only": "source_region", "representation_only": "representation",
                         "found_circles_only": "found_circles", "target_state_only": "target_state",
                         "observation_id_only": "target_observation_id",
                         "uncertainty_only": "uncertainty"}


def test_the_negative_matrix_covers_every_evidence_source():
    assert set(NEGATIVE_EVIDENCE_KEY.values()) == set(EVIDENCE_SOURCES)


@pytest.mark.parametrize("name", sorted(NEGATIVE_BODIES))
def test_evidence_only_candidates_are_rejected_at_the_wire(name):
    """§8: kanıt-yalnız gövde `schema_semantic_empty` ile reddedilir — sessiz tamir yok."""
    item = evidence_only(**NEGATIVE_BODIES[name])
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(item))
    assert excinfo.value.kind == "schema_semantic_empty"
    assert item["candidate_id"] in str(excinfo.value)


@pytest.mark.parametrize("name", sorted(NEGATIVE_BODIES))
def test_evidence_only_bodies_stay_structurally_valid_but_flagless(name):
    """Red yalnız wire sınırındadır: model düzeyinde gövde geçerli, ama hiçbir claim bayrağı yok."""
    candidate = Candidate.model_validate(evidence_only(**NEGATIVE_BODIES[name]))
    flags = semantic_claim_flags(candidate)
    assert flags == {source: False for source in SEMANTIC_CLAIM_SOURCES}
    assert candidate_has_semantic_claim(candidate) is False
    assert evidence_flags(candidate)[NEGATIVE_EVIDENCE_KEY[name]] is True


# ----------------------------------------------------------- pozitif matris (§9)


POSITIVE_CASES = {
    "known_callout_text": ({"callout": {"text": "Ø8", "state": "known"}}, {"callout_text"}),
    "form_radius": ({"form": {"symbol": "R"}}, {"form_symbol"}),
    "form_diameter": ({"form": {"symbol": "diameter"}}, {"form_symbol"}),
    "known_size": ({"size": {"value": 8.0, "unit": "mm", "state": "known"}}, {"size"}),
    "printed_count": ({"count": {"printed": 4, "state": "known"}}, {"count_printed"}),
    "termination_thru_stated": ({"termination": {"kind": "thru", "stated": True}},
                                {"termination"}),
    "finite_with_depth": ({"termination": {"kind": "finite", "stated": True},
                           "depth": {"value": 6.0, "unit": "mm", "state": "known"}},
                          {"termination", "depth"}),
    "known_depth": ({"depth": {"value": 12.0, "unit": "mm", "state": "known"}}, {"depth"}),
    "physical_hole": ({"physical": {"kind": "hole", "reason": "kesit görünüyor"}}, {"physical"}),
    "physical_not_hole": ({"physical": {"kind": "not_hole", "reason": "cephe yazıyor"}},
                          {"physical"}),
}


@pytest.mark.parametrize("name", sorted(POSITIVE_CASES))
def test_single_semantic_claims_pass_the_wire_and_flag_exactly(name):
    """§9: her tek-claim gövde kabul edilir ve yalnız beklenen bayraklar true olur."""
    payload, expected = POSITIVE_CASES[name]
    parsed = parse_candidate_json(body(evidence_only(**payload)))
    flags = semantic_claim_flags(parsed.items[0])
    assert {key for key, value in flags.items() if value} == expected
    assert candidate_has_semantic_claim(parsed.items[0]) is True


def test_a_rich_candidate_flags_every_semantic_source_and_every_evidence_signal():
    # Tüm bayrakların birlikte true olduğu tek tutarlı kombinasyon `finite` + yazılı derinliktir:
    # şema yazılı derinlikle `thru`yu birlikte kabul etmez (ikisi de iddia edilemez).
    item = evidence_only(
        callout={"text": "4xØ8", "state": "known"},
        representation={"kind": "circle", "diameter_px": 42.0},
        physical={"kind": "hole", "reason": "kesit görünüyor"},
        form={"symbol": "diameter"},
        size={"value": 8.0, "unit": "mm", "state": "known"},
        count={"printed": 4, "found_circles": 4, "state": "known"},
        termination={"kind": "finite", "stated": True},
        depth={"value": 6.0, "unit": "mm", "state": "known"},
        target={"region": dict(REGION), "observation_id": "t-1", "state": "bound"},
        uncertainty={"fields": {"physical": "kesit görünmüyor"}, "reason": "tek görünüş"})
    parsed = parse_candidate_json(body(item)).items[0]
    assert all(semantic_claim_flags(parsed).values())
    assert all(evidence_flags(parsed).values())


# ----------------------------------------------------------- wire sırası ve abstention (§5/§7)


def test_flag_key_sets_are_closed_and_ordered():
    """Bayrak sözlükleri kapalı listelerle birebir aynı anahtar sırasını taşır (rapor kararlılığı)."""
    assert tuple(semantic_claim_flags(evidence_only())) == SEMANTIC_CLAIM_SOURCES
    assert tuple(evidence_flags(evidence_only())) == EVIDENCE_SOURCES


def test_an_empty_items_response_stays_a_valid_abstention():
    """§7: boş yanıt genel abstention'dır — dev sayfalarda içerik kapısı ayrıca aranır (§27)."""
    response = parse_candidate_json(body())
    assert response.items == []


def test_one_semantic_empty_candidate_rejects_the_whole_response_without_repair():
    good = evidence_only(callout={"text": "R5", "state": "known"})
    empty = evidence_only(candidate_id="e2")
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(good, empty))
    assert excinfo.value.kind == "schema_semantic_empty"
    assert "'e2'" in str(excinfo.value), "hata mesajı suçlu adayı adıyla söylemeli"


def test_structural_errors_are_decided_before_the_semantic_rule():
    """§5 sırası: yapısal hata semantik kuraldan **önce** karara bağlanır (yapı > semantik)."""
    pixel = evidence_only(source={"image_id": "image-1",
                                  "region": {"x0": 65, "y0": 287, "x1": 349, "y1": 450}})
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(pixel))
    assert excinfo.value.kind == "schema_coordinate"
    guessed = evidence_only(termination={"kind": "finite", "stated": True})
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(guessed))
    assert excinfo.value.kind == "schema_no_guess"
    unknown_key = evidence_only(note="serbest metin")
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(unknown_key))
    assert excinfo.value.kind == "schema_error"


def test_helpers_read_candidate_objects_and_stored_json_dicts_alike():
    """Dev raporu kayıtlı `response-parsed.json` sözlüklerini okur: tanım iki biçimde de aynıdır."""
    item = evidence_only(callout={"text": "Ø8", "state": "known"},
                         representation={"kind": "circle", "diameter_px": 42.0})
    parsed = parse_candidate_json(body(item)).items[0]
    stored = parsed.model_dump(mode="json")
    assert semantic_claim_flags(stored) == semantic_claim_flags(parsed)
    assert evidence_flags(stored) == evidence_flags(parsed)
    assert candidate_has_semantic_claim(stored) is True


# ----------------------------------------------------------- D yolu audit'i (§6)


def test_the_d_path_never_parses_wire_bodies_and_the_reader_does():
    """§6 audit: kural wire parser'da yaşar — D `Candidate`'ı doğrudan kurar, V/VE parser'dan geçer."""
    d_source = Path(deterministic_module.__file__).read_text(encoding="utf-8")
    reader_source = Path(reader_module.__file__).read_text(encoding="utf-8")
    assert "parse_candidate_json" not in d_source
    assert "parse_candidate_json" in reader_source


def test_an_evidence_only_candidate_still_constructs_directly_for_the_d_path():
    """D gövdeleri (kanıt-yalnız olabilir) model düzeyinde kurulmaya devam eder — regresyon yok."""
    candidate = Candidate.model_validate(evidence_only())
    response = CandidateResponse(items=[candidate])
    assert response.items[0].candidate_id == "e1"
    assert candidate_has_semantic_claim(response.items[0]) is False
    assert evidence_flags(response.items[0])["source_region"] is True


# ----------------------------------------------------------- taşıma sınırı (read_page)


class _FakeChat:
    """Taşıma sınırında duran taklit: ağ yok; stats/trace/raw_response doldurulur."""

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def complete(self, prompt, **kwargs):
        kwargs["stats"].update({"done_reason": "stop", "eval_count": 12, "prompt_eval_count": 40})
        kwargs["trace"].update({"model": "fake-model:1b", "options": {"temperature": 0.0},
                                "messages": [{"role": "user", "content": prompt}]})
        kwargs["raw_response"].update({"done": True})
        return self.answer


def _tiny_png(width: int = 8, height: int = 6) -> bytes:
    import cv2
    import numpy as np

    ok, buffer = cv2.imencode(".png", np.zeros((height, width), dtype=np.uint8))
    assert ok
    return buffer.tobytes()


def _bundle() -> dict:
    return {"arm": "V", "page_image_id": "image-1",
            "images": [PreparedImage(image_id="image-1", kind="full_page", png=_tiny_png(),
                                     source_sha256="a" * 64, source_type="raster",
                                     render_mode="native_raster")],
            "image_ids": ["image-1"], "observations": [], "arm_input_variant": "V",
            "evidence_mode": "raw_only"}


def test_read_page_records_the_new_failure_kind_end_to_end():
    """Wire reddi taşıma katmanına `schema_semantic_empty` olarak ulaşır; ham yanıt korunur."""
    answer = body(evidence_only())
    outcome = read_page(_FakeChat(answer), _bundle(), forbidden=[])
    assert outcome["outcome"] == "answered"
    assert outcome["parse"]["ok"] is False
    assert outcome["parse"]["kind"] == "schema_semantic_empty"
    assert outcome["failure_kind"] == "schema_semantic_empty"
    assert outcome.get("parsed") is None
    assert outcome["raw_response"] == answer
