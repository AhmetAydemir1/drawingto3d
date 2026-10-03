"""SEMREAD-001B — D adapteri ve değerlendirme/metrikler (model çağrısı yok)."""

from __future__ import annotations

import json

import pytest

from drawingto3d.bind import Bindings, SpanBinding
from drawingto3d.meaning import Claim, ClaimPoint, Meanings, SpanMeaning
from drawingto3d.observe import (BBox, Frame, Observations, Primitive, SourceRef,
                                 TextObservation)
from drawingto3d.semantic_deterministic import (_region_from_points, _termination_and_depth,
                                                _unit_from_text, deterministic_candidates)
from drawingto3d.semantic_evaluation import (MATCH_POLICY, aggregate, compare_arms, evaluate_page,
                                             match_claims, score_pair)


# --------------------------------------------------------------- yardımcılar


def observations() -> Observations:
    return Observations(
        source=SourceRef(ref="test.pdf", sha256="a" * 64, page=0),
        frame=Frame(width=1000, height=500),
        text_placement="as-is",
        primitives=[
            Primitive(id="g0", path_id="p0", kind="circle", centre=[200.0, 100.0], radius=20.0),
            Primitive(id="g1", path_id="p1", kind="line", start=[0.0, 0.0], end=[10.0, 10.0]),
        ],
        texts=[TextObservation(id="t0", text="\u00d88 THRU", value=8.0, unit="mm", kind="diameter",
                               bbox=BBox(x=300, y=90, w=40, h=12))],
    )


def bindings() -> Bindings:
    return Bindings(source_ref="test.pdf", source_sha256="a" * 64, sheet_px_per_mm=2.0,
                    spans=[SpanBinding(span_id="t0", text="\u00d88 THRU", value=8.0, unit="mm",
                                       kind="diameter", anchor_mode="leader",
                                       text_bbox=[300.0, 90.0, 40.0, 12.0], status="bound")])


def meanings(claim_geometry: tuple[str, str] = ("g0", "g1")) -> Meanings:
    claim = Claim(form="diameter", points=[ClaimPoint(geometry_id=claim_geometry[0], kind="circle",
                                                      point=[200.0, 100.0], cost_px=1.0)],
                  drawn_mm=8.0, printed_mm=8.0, deviation_mm=0.0, rank=0, cost_px=1.0,
                  matched_geometry=[claim_geometry[0]])
    return Meanings(source_ref="test.pdf", source_sha256="a" * 64, sheet_px_per_mm=2.0,
                    spans=[SpanMeaning(span_id="t0", text="\u00d88 THRU", printed_mm=8.0,
                                       printed_value=8.0, unit="mm", kind="diameter",
                                       anchor_mode="leader", form="diameter", resolution="confirmed",
                                       claim=claim)])


def claim(**overrides) -> dict:
    base = {"claim_id": "k1", "target": {"name": "hole-1",
                                         "region": {"x0": 0.18, "y0": 0.16, "x1": 0.22, "y1": 0.24}},
             "callout": {"region": {"x0": 0.30, "y0": 0.18, "x1": 0.34, "y1": 0.20}},
             "representation": "circle", "physical": "hole", "form": "diameter",
             "size": 8.0, "unit": "mm", "count_printed": 4, "termination": "thru", "depth": None,
             "state": "determinate_present", "evidence": "görsel inceleme", "source_evidence": "pdf text"}
    base.update(overrides)
    return base


def reference(**overrides) -> dict:
    return {"claims": [claim(**overrides)]}


def candidate(**overrides) -> dict:
    base = {"candidate_id": "c1",
            "target": {"region": {"x0": 0.181, "y0": 0.161, "x1": 0.221, "y1": 0.241},
                       "observation_id": "g0", "state": "bound"},
            "source": {"image_id": "image-1", "region": {"x0": 0.18, "y0": 0.16, "x1": 0.22, "y1": 0.24}},
            "representation": {"kind": "circle"}, "physical": {"kind": "hole"},
            "form": {"symbol": "diameter"}, "size": {"value": 8.0, "unit": "mm", "state": "known"},
            "count": {"printed": 4, "found_circles": 1, "state": "known"},
            "termination": {"kind": "thru", "stated": True},
            "depth": {"value": None, "unit": None, "state": "not_stated"}}
    base.update(overrides)
    return base


# --------------------------------------------------------------- D adapteri


def test_the_adapter_maps_deterministic_output_into_candidates(tmp_path):
    result = deterministic_candidates("test.pdf", image_id="image-1", observations=observations(),
                                      bindings=bindings(), meanings=meanings())
    items = result["response"].model_dump(mode="json")["items"]
    assert len(items) == 1
    item = items[0]
    assert item["form"]["symbol"] == "diameter"
    assert item["size"]["value"] == 8.0 and item["size"]["unit"] == "mm"
    assert item["representation"]["kind"] == "circle"
    assert item["termination"]["kind"] == "thru" and item["termination"]["stated"] is True
    assert item["target"]["observation_id"] == "g0"
    assert item["target"]["region"] == {"x0": 0.18, "y0": 0.16, "x1": 0.22, "y1": 0.24}
    assert result["evidence"]["no_inference"] is True
    assert result["evidence"]["counts"]["circles"] == 1


def test_the_adapter_keeps_the_physical_interpretation_unknown():
    """Çizilmiş circle + çözülen çap, fiziksel delik iddiası değildir."""
    result = deterministic_candidates("test.pdf", image_id="image-1", observations=observations(),
                                      bindings=bindings(), meanings=meanings())
    item = result["response"].model_dump(mode="json")["items"][0]
    assert item["physical"]["kind"] == "unknown"
    assert json.dumps(item).count('"supported"') == 0 and '"confirmed"' not in json.dumps(item)


def test_the_adapter_does_not_claim_a_value_that_was_not_printed():
    empty = Meanings(source_ref="test.pdf", source_sha256="a" * 64, sheet_px_per_mm=2.0,
                     spans=[SpanMeaning(span_id="t0", text="NOT", printed_mm=None,
                                        printed_value=None, unit="mm", kind="text",
                                        anchor_mode="none", form="none", resolution="no-value")])
    result = deterministic_candidates("test.pdf", image_id="image-1", observations=observations(),
                                      bindings=bindings(), meanings=empty)
    item = result["response"].model_dump(mode="json")["items"][0]
    assert item["size"]["value"] is None and item["size"]["state"] == "unknown"
    assert item["uncertainty"]["fields"]["physical"].startswith("deterministic")


@pytest.mark.parametrize("text,expected", [
    ("\u00d88 THRU", ("thru", True, None, "not_stated")),
    ("\u00d88 \u21a76", ("finite", True, 6.0, "known")),
    ("\u00d88", ("unknown", False, None, "not_stated")),
    ("DEPTH 12", ("finite", True, 12.0, "known")),
    ("\u00d88 THRU \u21a76", ("thru", True, None, "not_stated")),
])
def test_termination_and_depth_read_only_what_is_written(text, expected):
    kind, stated, value, state, _notes = _termination_and_depth(text)
    assert (kind, stated, value, state) == expected


def test_unit_reading_separates_printed_from_defaulted():
    assert _unit_from_text("8 mm", "mm") == ("mm", True)
    assert _unit_from_text("8 in", "mm") == ("in", True)
    assert _unit_from_text("8", "mm") == ("mm", False)
    assert _unit_from_text("8", None) == (None, False)


def test_region_mapping_is_normalised_and_bounded():
    frame = Frame(width=1000, height=500)
    region = _region_from_points([[100.0, 50.0], [300.0, 150.0]], frame)
    assert region is not None
    assert [round(value, 3) for value in region.as_list()] == [0.1, 0.1, 0.3, 0.3]
    assert _region_from_points([[0.0, 0.0]], frame) is not None      # tek nokta genişletilir
    assert _region_from_points([], frame) is None


# --------------------------------------------------------------- eşleştirme


def test_matching_is_one_to_one_and_region_based():
    claims = [claim()]
    candidates = [candidate(), candidate(candidate_id="c2")]
    matching = match_claims(claims, candidates)
    assert len(matching["pairs"]) == 1, "kopya aday recall'u artırmaz"
    assert matching["unmatched_candidates"] == ["c2"]


def test_a_right_value_on_the_wrong_target_is_a_binding_error_not_a_match():
    """Eşleştirme beklenen değere bakmaz: doğru değer yanlış hedefteyse eşleşme kurulmaz."""
    far = candidate(target={"region": {"x0": 0.70, "y0": 0.70, "x1": 0.74, "y1": 0.78},
                            "observation_id": "g1", "state": "bound"})
    matching = match_claims([claim()], [far])
    assert matching["pairs"] == []
    assert matching["unmatched_claims"] == ["k1"]
    assert matching["unmatched_candidates"] == ["c1"]


def test_an_ambiguous_pair_is_reported_and_not_double_counted():
    twin = candidate(candidate_id="c2")
    matching = match_claims([claim()], [candidate(), twin])
    assert len(matching["pairs"]) == 1
    assert matching["ambiguous"], "yakın puanlı ikinci aday belirsiz olarak raporlanmalı"


def test_binding_error_is_scored_inside_a_matched_pair():
    shifted = candidate(target={"region": {"x0": 0.30, "y0": 0.30, "x1": 0.34, "y1": 0.36},
                                "observation_id": None, "state": "bound"})
    rows = score_pair(claim(), shifted)
    verdicts = {row["field"]: row["verdict"] for row in rows}
    assert verdicts["target_binding"] == "binding_error"


# --------------------------------------------------------------- alan kararları


def test_field_verdicts_cover_confusion_types():
    page = evaluate_page(reference(), {"response": {"items": [candidate()]}})
    verdicts = page["summary"]["fields"]
    assert verdicts["form"] == {"correct": 1}
    assert verdicts["size"] == {"correct": 1}
    assert verdicts["termination"] == {"correct": 1}
    assert page["per_claim"]["k1"]["matched"] is True


def test_r_and_diameter_are_not_interchangeable():
    radius = candidate(form={"symbol": "R"})
    page = evaluate_page(reference(), {"response": {"items": [radius]}})
    assert page["summary"]["fields"]["form"] == {"mismatch": 1}


def test_unknown_is_abstention_not_a_success():
    unknown = candidate(form={"symbol": "unknown"},
                        termination={"kind": "unknown", "stated": False})
    page = evaluate_page(reference(), {"response": {"items": [unknown]}})
    assert page["summary"]["fields"]["form"] == {"abstained": 1}
    assert page["summary"]["fields"]["termination"] == {"abstained": 1}


def test_a_determinate_claim_on_an_underdetermined_reference_is_an_overclaim():
    page = evaluate_page(reference(physical="unknown", state="underdetermined"),
                         {"response": {"items": [candidate()]}})
    assert page["summary"]["fields"]["physical"] == {"overclaim": 1}


def test_unit_error_and_value_error_are_distinguished():
    inches = candidate(size={"value": 8.0, "unit": "in", "state": "known"})
    rows = {row["field"]: row["verdict"] for row in score_pair(claim(), inches)}
    assert rows["size"] == "unit_error"
    wrong = candidate(size={"value": 12.0, "unit": "mm", "state": "known"})
    rows = {row["field"]: row["verdict"] for row in score_pair(claim(), wrong)}
    assert rows["size"] == "value_error"


def test_missing_candidate_is_omission_and_uncounted_claims_are_not_produced():
    page = evaluate_page(reference(), {"response": {"items": []}})
    assert page["summary"]["matched"] == 0
    assert page["per_claim"]["k1"]["fields"]["size"] == "not_produced"


# --------------------------------------------------------------- toplama / karşılaştırma


def test_zero_denominator_reports_null_not_a_number():
    empty = {"pages": []}
    totals = aggregate([evaluate_page(reference(), {"response": {"items": []}})])
    assert totals["claim_recall"] == 0.0
    assert totals["candidate_precision"] is None, "aday yokken kesinlik tanımsızdır"
    del empty


def _comparison(d_items, arm_items):
    gold = reference()
    d_page = evaluate_page(gold, {"response": {"items": d_items}})
    arm_page = evaluate_page(gold, {"response": {"items": arm_items}})
    return compare_arms({"page": {"D": d_page, "V": arm_page}})["vs_d"]["V"]


def test_a_claim_d_got_wrong_and_v_got_right_is_recovery():
    wrong = candidate(size={"value": 12.0, "unit": "mm", "state": "known"})
    result = _comparison([wrong], [candidate()])
    assert result["recovered"] == 1 and result["regressed_total"] == 0
    assert result["net_correct_gain"] == 1


def test_a_wrong_candidate_where_d_was_right_is_a_regression_not_an_abstention():
    wrong = candidate(size={"value": 12.0, "unit": "mm", "state": "known"})
    result = _comparison([candidate()], [wrong])
    assert result["regressed_wrong_candidate"] == 1
    assert result["regressed_abstention"] == 0
    assert result["net_correct_gain"] == -1


def test_silence_where_d_was_right_is_a_regression_of_the_abstention_kind():
    result = _comparison([candidate()], [])
    assert result["regressed_abstention"] == 1
    assert result["regressed_wrong_candidate"] == 0
    assert result["net_correct_gain"] == -1


def test_the_policy_is_versioned_and_frozen_before_predictions():
    assert MATCH_POLICY["version"].endswith("/1")
    for key in ("region_iou_threshold", "numeric_relative", "ambiguous_score_margin", "pairing"):
        assert key in MATCH_POLICY
