"""SEMREAD-001D — PLAN-14 §3/§4/§6–§9: schema/reader `/3` + prompt v3 sözleşmesi (0 inference).

Kapsam (§61/§62 kabul listesi):

* şema **ve** okuyucu `/3`'e çıktı; `/2` gövdesi artık kabul edilmez (sürüm uyuşmazlığı);
* JSON şeması item açıklamasında **aynı** asgari sözleşmeyi modele söyler (§4); yapısal `anyOf`
  bilinçli olarak **yok** (§5 — backend desteği kanıtlanmadan production şeması büyütülmez);
* ortak V/VE görev metni **semantic-first** (§6): önce basılı semantik olgu, sonra aday; bölge tek
  başına aday değil, makine gözlem satırı semantik claim değil;
* semantic claim / evidence-only ayrımı prompt'ta açık ve kapalı listelerle ayrılmış (§7);
* **no-guess anti-pressure** (§8) iki kolda da var; 001B'nin no-guess kuralı geri çekilmedi;
* VE farkı **yalnız kanıt bölümü**: satır başına aday yasağı (§9);
* parser semantik-içerik reddini korur (`schema_semantic_empty`), boş `items` geçerli abstention.

Model çağrısı yok; yalnız saf fonksiyonlar (prompt + şema + parser).
"""

from __future__ import annotations

import json

import pytest

from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION, CANDIDATE_SCHEMA_VERSION,
                                             EVIDENCE_ONLY_NOTE, SEMANTIC_CONTENT_REQUIREMENT,
                                             TASK_INSTRUCTIONS, CandidateParseError,
                                             candidate_json_schema, candidate_prompt,
                                             parse_candidate_json)

GOLD_SENTINEL = "semread-001b-gold-sentinel-4f21"
RAW_ID = "image-1"
OBSERVATION_ROW = {"id": "t0", "kind": "text", "text": "Ø8", "value": 8.0, "unit": "mm",
                   "region": [0.10, 0.20, 0.30, 0.40]}

SEMANTIC_FIRST_LINES = (
    "First identify a printed semantic fact. Only then create a candidate.",
    "A region alone is not a candidate.",
    "A machine observation row is not a semantic claim.",
    "Do not emit a candidate unless it contains at least one semantic claim.",
)
NO_GUESS_LINES = (
    "If you cannot read at least one semantic fact, emit no candidate for that feature.",
    "Do not invent a semantic fact merely to satisfy the semantic-content requirement.",
)
VE_EVIDENCE_LINES = (
    "Observations are evidence, not candidate seeds.",
    "Do not create one candidate per observation row.",
    "Use an observation only if it helps support a semantic claim.",
)
SEMANTIC_CLAIM_PHRASES = ("printed callout text", "an R (radius) or a Ø (diameter) symbol",
                          "a printed size", "a printed count", "an explicit THRU",
                          "an explicit finite depth", "a physical meaning the drawing "
                          "explicitly supports")
EVIDENCE_ONLY_PHRASES = ("a circle/arc representation", "a found-circle count", "a target box",
                         "an observation id", "a source region", "an uncertainty note")


def _item(**extra) -> dict:
    """Tek aday: yalnız zorunlu alanlar (semantic claim'i testler ayrıca ekler)."""
    item = {"candidate_id": "c1",
            "source": {"image_id": RAW_ID,
                       "region": {"x0": 0.10, "y0": 0.20, "x1": 0.30, "y1": 0.40}}}
    item.update(extra)
    return item


def _body(*items: dict, version: str = CANDIDATE_SCHEMA_VERSION) -> str:
    return json.dumps({"schema_version": version, "items": list(items)})


def v_prompt() -> str:
    return candidate_prompt([RAW_ID])


def ve_prompt() -> str:
    return candidate_prompt([RAW_ID], observations=[OBSERVATION_ROW])


# ---------------------------------------------------------------- §3: sürüm kimliği


def test_schema_and_reader_are_bumped_to_3_and_the_old_version_is_refused():
    assert CANDIDATE_SCHEMA_VERSION == "semread-candidates/3"
    assert CANDIDATE_READER_VERSION == "semread-candidate-reader/3"
    schema = candidate_json_schema()
    assert schema["properties"]["schema_version"]["const"] == CANDIDATE_SCHEMA_VERSION
    with pytest.raises(CandidateParseError) as old:
        parse_candidate_json(_body(_item(callout={"text": "Ø8", "state": "known"}),
                                   version="semread-candidates/2"))
    assert old.value.kind == "schema_error"


# ---------------------------------------------------------------- §4/§5: şema sözleşmesi


def test_schema_item_description_carries_the_semantic_requirement():
    """§4: modelin gördüğü şema, parser'ın semantik-içerik reddiyle **aynı yönü** göstermeli."""
    item = candidate_json_schema()["properties"]["items"]["items"]
    assert item["description"] == SEMANTIC_CONTENT_REQUIREMENT
    for phrase in ("at least one semantic claim", "representation", "found-circle count",
                   "target binding", "observation id", "uncertainty"):
        assert phrase in SEMANTIC_CONTENT_REQUIREMENT, phrase


def test_schema_marks_the_evidence_only_fields_and_avoids_complex_anyof():
    """§4/§7 işaret + §5 kararı: production şemasına `anyOf`/`oneOf` eklenmez."""
    schema = candidate_json_schema()
    dumped = json.dumps(schema)
    assert "anyOf" not in dumped and "oneOf" not in dumped
    items = schema["properties"]["items"]["items"]["properties"]
    marked = (items["source"]["properties"]["region"],
              items["source"]["properties"]["callout_region"],
              items["target"]["properties"]["region"],
              items["representation"]["properties"]["kind"],
              items["count"]["properties"]["found_circles"],
              items["target"]["properties"]["observation_id"],
              items["target"]["properties"]["state"], items["uncertainty"])
    for field in marked:
        assert EVIDENCE_ONLY_NOTE.strip() in field["description"], field


def test_semantic_claim_fields_are_not_marked_as_evidence_only():
    items = candidate_json_schema()["properties"]["items"]["items"]["properties"]
    for field in (items["count"]["properties"]["printed"], items["form"]["properties"]["symbol"]):
        assert EVIDENCE_ONLY_NOTE.strip() not in field["description"]


# ---------------------------------------------------------------- §6/§7: semantic-first görev


def test_common_task_is_semantic_first_in_both_arms():
    for prompt in (v_prompt(), ve_prompt()):
        for line in SEMANTIC_FIRST_LINES:
            assert line in prompt, line
        # Sıra: semantic-first bloğu, alan listesinden ve koordinat kuralından **önce** gelir.
        assert prompt.index(SEMANTIC_FIRST_LINES[0]) < prompt.index("Report, for every dimension")
        assert prompt.index(SEMANTIC_FIRST_LINES[0]) < prompt.index("Coordinate convention")
        assert prompt.startswith("You read ONE mechanical drawing page")


def test_common_task_separates_semantic_claims_from_evidence_only():
    boundary = "These are evidence only."
    for prompt in (v_prompt(), ve_prompt()):
        assert boundary in prompt
        claims_at = prompt.index(boundary)
        for phrase in SEMANTIC_CLAIM_PHRASES:
            assert phrase in prompt[:claims_at], phrase
        for phrase in EVIDENCE_ONLY_PHRASES:
            assert phrase in prompt[claims_at:], phrase


def test_no_guess_anti_pressure_is_present_in_both_arms():
    """§8: semantik-içerik kapısı hallucination üretmemeli — no-guess cümleleri zorunlu."""
    for prompt in (v_prompt(), ve_prompt()):
        for line in NO_GUESS_LINES:
            assert line in prompt, line
        # 001B/001C no-guess kuralı geri çekilmedi.
        assert "Never guess." in prompt
        assert "A field you cannot read must not delete the fields you did read." in prompt


def test_common_task_keeps_the_shared_anti_loop_rules():
    for prompt in (v_prompt(), ve_prompt()):
        for rule in ("Emit at most one candidate for the same visible callout→target pair.",
                     "Do not repeat a candidate with a new candidate_id.",
                     "When all supported visible callouts are reported, close the items array."):
            assert rule in prompt, rule


# ---------------------------------------------------------------- §9/§62: V vs VE ayrımı


def test_ve_evidence_section_forbids_one_candidate_per_observation_row():
    """§9: yasak VE'nin kanıt bölümüne aittir — ortak görev metnine sızmaz."""
    ve = ve_prompt()
    for line in VE_EVIDENCE_LINES:
        assert line in ve, line
        assert line not in TASK_INSTRUCTIONS
        assert line not in v_prompt()


def test_only_the_evidence_section_differs_between_the_two_arms():
    """§62: ortak görev metni byte düzeyinde aynı; fark yalnız gözlem bölümü."""
    v, ve = v_prompt(), ve_prompt()
    marker = f"Image ids (use exactly these): {RAW_ID}"
    v_head, v_tail = v.split(marker)
    ve_head, ve_tail = ve.split(marker)
    assert ve_head == v_head, "ortak görev metni iki kolda farklı"
    v_rest = v_tail.strip().splitlines()
    ve_rest = ve_tail.strip().splitlines()
    assert v_rest == [ve_rest[-1]], "V kolunda gözlem bölümü olmamalı"
    assert "t0" in ve_rest[0] or any("t0" in line for line in ve_rest)
    assert "t0" not in v


def test_v3_prompt_carries_no_gold_or_page_specific_text():
    for prompt in (v_prompt(), ve_prompt()):
        assert GOLD_SENTINEL not in prompt
        for marker in ("dev-plate-pocket", "dev-flange", "Exercise", "Flange",
                       "semread-001b-gold", "frozen-"):
            assert marker not in prompt, marker


# ---------------------------------------------------------------- parser sözleşmesi


def test_parser_keeps_semantic_empty_rejection_and_abstention():
    with pytest.raises(CandidateParseError) as empty:
        parse_candidate_json(_body(_item()))
    assert empty.value.kind == "schema_semantic_empty"
    assert parse_candidate_json(_body()).items == []
    parsed = parse_candidate_json(_body(_item(callout={"text": "Ø8", "state": "known"})))
    assert parsed.items[0].callout.text == "Ø8"
