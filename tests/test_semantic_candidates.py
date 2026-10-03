"""SEMREAD-001B aday sözleşmesi: negatif testler (model taklidi, gerçek inference yok)."""

from __future__ import annotations

import json

import pytest

from drawingto3d.semantic_candidates import (CANDIDATE_SCHEMA_VERSION, CandidateParseError,
                                              candidate_json_schema, candidate_prompt,
                                              check_candidate_references, parse_candidate_json,
                                              regions_match, numeric_tolerance, Region)


def item(**overrides) -> dict:
    base = {
        "candidate_id": "c1",
        "callout": {"text": "4xØ8 THRU", "state": "known"},
        "representation": {"kind": "circle", "diameter_px": 42.0},
        "physical": {"kind": "unknown", "reason": "kesit yok, delik yazmıyor"},
        "form": {"symbol": "diameter"},
        "size": {"value": 8.0, "unit": "mm", "state": "known"},
        "count": {"printed": 4, "found_circles": 4, "state": "known"},
        "termination": {"kind": "thru", "stated": True},
        "depth": {"value": None, "unit": None, "state": "not_stated"},
        "target": {"region": {"x0": 0.1, "y0": 0.2, "x1": 0.3, "y1": 0.4},
                   "observation_id": "t-3", "state": "bound"},
        "source": {"image_id": "image-1",
                   "region": {"x0": 0.05, "y0": 0.15, "x1": 0.35, "y1": 0.45},
                   "callout_region": {"x0": 0.5, "y0": 0.1, "x1": 0.6, "y1": 0.14}},
        "provenance": {"kind": "vlm", "method": "qwen3-vl:8b-instruct"},
        "uncertainty": {"fields": {"physical": "kesit görünmüyor"}, "reason": "tek görünüş"},
    }
    base.update(overrides)
    return base


def body(*items: dict, version: str = CANDIDATE_SCHEMA_VERSION) -> str:
    return json.dumps({"schema_version": version, "items": list(items)}, ensure_ascii=False)


# ----------------------------------------------------------- ayrıştırma negatifleri


def test_a_valid_body_is_parsed_without_repair():
    response = parse_candidate_json(body(item()))
    assert len(response.items) == 1
    assert response.items[0].candidate_id == "c1"
    assert response.items[0].source.image_id == "image-1"


@pytest.mark.parametrize("broken", [
    "", "   ", "not json at all", '{"schema_version": "x", "items": []}',
    '{"schema_version": "%s"}' % CANDIDATE_SCHEMA_VERSION,
    '{"schema_version": "%s", "items": {}}' % CANDIDATE_SCHEMA_VERSION,
    '```json\n{"schema_version": "%s", "items": []}\n```' % CANDIDATE_SCHEMA_VERSION,
    '{"schema_version": "%s", "items": [], "note": "fazladan"}' % CANDIDATE_SCHEMA_VERSION,
    '[1, 2, 3]',
])
def test_a_broken_or_extra_body_is_refused_not_repaired(broken):
    with pytest.raises(CandidateParseError):
        parse_candidate_json(broken)


def test_an_unknown_candidate_key_is_refused():
    payload = item(note="serbest metin")
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(body(payload))
    assert "tanımsız aday anahtarı" in str(excinfo.value)


def test_a_product_decision_field_is_refused():
    """Model ürün kararı üretmez: `supported` gibi alanlar sözleşmede yok."""
    payload = item(supported=True)
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(payload))


def test_an_enum_outside_the_closed_sets_is_refused():
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(termination={"kind": "blind", "stated": True})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(form={"symbol": "phi"})))


# ----------------------------------------------------------- alan tutarlılığı


def test_a_drawn_circle_alone_does_not_become_a_hole():
    """`representation.kind=circle` fiziksel yorumu kanıtlamaz: `physical` unknown kalır."""
    response = parse_candidate_json(body(item(physical={"kind": "unknown", "reason": "kanıt yok"})))
    candidate = response.items[0]
    assert candidate.representation.kind == "circle"
    assert candidate.physical.kind == "unknown"


def test_no_termination_fabrication():
    """Yazılı derinlik yoksa `finite` olamaz; `thru` yalnız yazılıysa iddia edilebilir."""
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(termination={"kind": "finite", "stated": True},
                                        depth={"value": None, "unit": None, "state": "not_stated"})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(termination={"kind": "thru", "stated": False})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(termination={"kind": "thru", "stated": True},
                                        depth={"value": 12.0, "unit": "mm", "state": "known"})))
    # Yazılı derinlik + finite: tutarlı.
    parsed = parse_candidate_json(body(item(termination={"kind": "finite", "stated": True},
                                             depth={"value": 12.0, "unit": "mm", "state": "known"})))
    assert parsed.items[0].depth.value == 12.0


def test_an_unknown_value_cannot_carry_a_number():
    """Bilinmeyen alan değer taşımaz; tahmin yazmak doğrudan reddedilir."""
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(size={"value": 8.0, "unit": "mm", "state": "unknown"})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(size={"value": None, "unit": None, "state": "known"})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(depth={"value": 12.0, "unit": "mm", "state": "not_stated"})))


def test_printed_count_and_found_circles_are_separate_fields():
    """NxØd'deki yazılı adet ile bulunan circle sayısı farklı alanlarda taşınır."""
    parsed = parse_candidate_json(body(item(count={"printed": 4, "found_circles": 3, "state": "known"})))
    count = parsed.items[0].count
    assert count.printed == 4 and count.found_circles == 3
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(count={"printed": 0, "found_circles": 0, "state": "known"})))
    with pytest.raises(CandidateParseError):
        parse_candidate_json(body(item(count={"printed": None, "found_circles": None, "state": "known"})))


def test_a_degenerate_or_out_of_bounds_region_is_refused():
    for region in ({"x0": 0.5, "y0": 0.1, "x1": 0.4, "y1": 0.2},
                   {"x0": -0.1, "y0": 0.0, "x1": 0.5, "y1": 0.5},
                   {"x0": 0.1, "y0": 0.1, "x1": 1.4, "y1": 0.5},
                   {"x0": 0.3, "y0": 0.3, "x1": 0.3, "y1": 0.6}):
        with pytest.raises(CandidateParseError):
            parse_candidate_json(body(item(source={"image_id": "image-1", "region": region})))


# ----------------------------------------------------------- kimlik / kapsam


def test_a_candidate_for_an_image_that_was_never_sent_is_a_reference_error():
    response = parse_candidate_json(body(item(source={"image_id": "image-9",
                                                     "region": {"x0": 0.1, "y0": 0.1,
                                                                "x1": 0.2, "y1": 0.2}})))
    report = check_candidate_references(response, ["image-1"])
    assert report["ok"] is False
    assert report["unknown_image_ids"] == ["image-9"]


def test_an_unknown_observation_id_is_a_reference_error_but_a_missing_one_is_allowed():
    with_unknown = parse_candidate_json(body(item(target={"region": {"x0": 0.1, "y0": 0.1, "x1": 0.3,
                                                              "y1": 0.3},
                                                    "observation_id": "p-99", "state": "bound"})))
    report = check_candidate_references(with_unknown, ["image-1"], ["t-3", "p-1"])
    assert report["ok"] is False and report["unknown_observation_ids"] == ["p-99"]

    # Gözlem kimliği yok ama geçerli bölge var: kabul edilir (extractor'ın temsil etmediği bölge).
    no_observation = parse_candidate_json(body(item(target={"region": {"x0": 0.1, "y0": 0.1, "x1": 0.3,
                                                                    "y1": 0.3},
                                                          "observation_id": None, "state": "unknown"})))
    report = check_candidate_references(no_observation, ["image-1"], ["t-3"])
    assert report["ok"] is True and report["coverage"]["exact"] is True


def test_duplicate_candidate_ids_break_coverage():
    duplicate = parse_candidate_json(body(item(), item()))
    report = check_candidate_references(duplicate, ["image-1"])
    assert report["ok"] is False and report["duplicate_candidate_ids"] == ["c1"]


def test_an_image_without_any_candidate_is_missing_coverage():
    only_first = parse_candidate_json(body(item()))
    report = check_candidate_references(only_first, ["image-1", "image-2"])
    assert report["ok"] is False and report["coverage"]["missing"] == ["image-2"]


# ----------------------------------------------------------- prompt izolasyonu


def test_the_plain_prompt_carries_no_observation_table():
    """V kolu yalnız ham görseli görür: gözlem tablosu ve gözlem kimliği prompt'a girmez."""
    text = candidate_prompt(["image-1", "image-2"])
    assert "machine observations" not in text
    assert "observation_id | kind | text" not in text
    assert "image-1, image-2" in text


def test_the_observation_prompt_carries_only_neutral_observation_fields():
    """Gözlem bölümü yalnız kimlik/ilkel/metin/değer/birim/bölge taşır: gold ya da yorum yok."""
    table = [{"id": "p-1", "kind": "circle", "text": None, "value": None, "unit": "mm",
              "region": [0.1, 0.2, 0.3, 0.4]}]
    text = candidate_prompt(["image-1"], observations=table)
    _head, _marker, tail = text.partition("observation_id | kind | text")
    assert _marker, "gözlem tablosu başlığı yok"
    assert "p-1" in tail and "0.1000" in tail
    for leaked in ("gold", "expected", "quadrant", "hole", "thru", "depth", "meaning"):
        assert leaked not in tail.lower(), f"gözlem bölümü '{leaked}' taşımamalı"


def test_the_schema_gives_the_same_options_for_every_image():
    """Şema hiçbir görsele özel cevap taşımaz: tek şema, kimlik yok."""
    schema = json.dumps(candidate_json_schema(), ensure_ascii=False)
    assert "image-1" not in schema and "triangle" not in schema
    assert "hole" in schema and "unknown" in schema


# ----------------------------------------------------------- karşılaştırma yardımcıları


def test_tolerances_and_region_matching_are_explicit():
    assert numeric_tolerance(10.0) == pytest.approx(0.2)      # %2
    assert numeric_tolerance(1.0) == pytest.approx(0.05)      # mutlak taban
    first = Region(x0=0.10, y0=0.10, x1=0.30, y1=0.30)
    assert regions_match(first, Region(x0=0.11, y0=0.11, x1=0.31, y1=0.31)) is True
    assert regions_match(first, Region(x0=0.60, y0=0.60, x1=0.80, y1=0.80)) is False
    assert regions_match(first, None) is False
