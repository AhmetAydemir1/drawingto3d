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
    matching = match_claims(claims, [candidate()])
    assert len(matching["pairs"]) == 1, "tek aday tek kalemle eşleşir"
    assert matching["pairs"][0]["matching_status"] == "matched"
    assert matching["unmatched_candidates"] == [] and matching["unmatched_claims"] == []


def test_a_right_value_on_the_wrong_target_is_a_binding_error_not_a_match():
    """Eşleştirme beklenen değere bakmaz: doğru değer yanlış hedefteyse eşleşme kurulmaz."""
    far = candidate(target={"region": {"x0": 0.70, "y0": 0.70, "x1": 0.74, "y1": 0.78},
                            "observation_id": "g1", "state": "bound"})
    matching = match_claims([claim()], [far])
    assert matching["pairs"] == []
    assert matching["unmatched_claims"] == ["k1"]
    assert matching["unmatched_candidates"] == ["c1"]


def test_an_ambiguous_pair_is_excluded_and_counted_separately():
    """Politika v2 (PLAN-5 §10): yakın puanlı rakip varsa kalem puanlanmaz, `ambiguous` sayılır."""
    twin = candidate(candidate_id="c2")
    matching = match_claims([claim()], [candidate(), twin])
    assert matching["pairs"] == [], "belirsiz kalem kesin eşleşme sayılmaz"
    assert matching["ambiguous_claims"] == ["k1"]
    assert matching["ambiguous"][0]["kind"] == "close_scores"
    assert matching["unmatched_claims"] == [], "belirsiz kalem 'eksik' sayılmaz, ayrı sayılır"


def test_a_contested_candidate_makes_both_claims_ambiguous():
    """Aday iki kalemin de en iyi adayıysa seçim sırası sonucu değiştirir: ikisi de puanlanmaz."""
    second = claim(claim_id="k2")
    matching = match_claims([claim(), second], [candidate()])
    assert matching["pairs"] == []
    assert matching["ambiguous_claims"] == ["k1", "k2"]
    assert {row["kind"] for row in matching["ambiguous"]} == {"candidate_contested"}


def test_an_ambiguous_claim_is_not_scored_and_not_in_the_regression_denominator():
    """Belirsiz kalem `not_scored` olur; kurtarma/geriye gitme paydasına girmez (§9/§10)."""
    gold = reference()
    ambiguous = evaluate_page(gold, {"response": {"items": [candidate(), candidate(candidate_id="c2")]}})
    assert ambiguous["per_claim"]["k1"]["matching_status"] == "ambiguous"
    assert set(ambiguous["per_claim"]["k1"]["fields"].values()) == {"not_scored"}
    assert ambiguous["summary"]["fields"]["size"] == {}
    result = compare_arms({"page": {"D": evaluate_page(gold, {"response": {"items": [candidate()]}}),
                                    "V": ambiguous}})["vs_d"]["V"]
    assert result["scorable_target_count"] == 0 and result["net_correct_gain"] == 0


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
    size_row = next(row for row in result["predicate_rows"] if row["predicate"] == "size")
    assert size_row["regressed_abstention_count"] == 1
    assert size_row["regressed_wrong_count"] == 0 and size_row["net_correct_gain"] == -1
    assert result["regressed_wrong_candidate"] == 0
    assert result["net_correct_gain"] == -result["regressed_abstention"], \
        "eksik cevap her yüklemde geriye gitme sayılır (payda yüklem bazlıdır)"


def test_the_policy_is_versioned_and_frozen_before_predictions():
    assert MATCH_POLICY["version"] == "semread-001b-match/2"
    for key in ("region_iou_threshold", "numeric_relative", "ambiguous_score_margin", "pairing",
                "ambiguous_policy", "localization_vs_semantic", "extras_policy"):
        assert key in MATCH_POLICY


# ---------------------------------------- §9/§11/§12: yüklem bazlı karşılaştırma ve ayrık metrikler


def test_predicate_rows_report_every_field_separately():
    """§9: her yüklem için scorable/kurtarılan/geriye giden + net kazanç ayrı satırdır."""
    wrong_size = candidate(size={"value": 12.0, "unit": "mm", "state": "known"})
    gold = reference()
    result = compare_arms({"page": {"D": evaluate_page(gold, {"response": {"items": [wrong_size]}}),
                                    "V": evaluate_page(gold, {"response": {"items": [candidate()]}})}})
    rows = {row["predicate"]: row for row in result["vs_d"]["V"]["predicate_rows"]}
    assert set(rows) == {"representation", "physical", "form", "size", "count_printed",
                         "termination", "depth", "target_binding"}
    assert rows["size"]["recovered_count"] == 1 and rows["size"]["net_correct_gain"] == 1
    assert rows["size"]["examples"] == [{"page_id": "page", "claim_id": "k1", "kind": "recovered"}]
    assert rows["form"]["scorable_target_count"] == 1 and rows["form"]["net_correct_gain"] == 0
    assert result["vs_d"]["V"]["recovered_count"] == 1, "toplam yüklem satırlarının toplamıdır"


def test_localization_and_semantic_metrics_are_separate():
    """§11: bölge eşleşmesi doğru olsa da alan doğruluğu ayrı ölçülür."""
    wrong_size = candidate(size={"value": 12.0, "unit": "mm", "state": "known"})
    totals = aggregate([evaluate_page(reference(), {"response": {"items": [wrong_size]}})])
    assert totals["localization_match_rate"] == 1.0, "bölge eşleşti"
    assert totals["semantic_field_accuracy"] is not None and totals["semantic_field_accuracy"] < 1.0
    assert totals["fields"]["size"]["correct"] == 0 and totals["fields"]["size"]["wrong"] == 1
    assert totals["target_binding_accuracy"] == 1.0
    assert totals["candidate_wrong_rate"] is not None


def test_overclaim_and_abstention_are_reported_separately():
    """§11/§17: fiziksel yorum overclaim ile abstention ayrı oranlardır, aynı sepete girmez."""
    overclaim = aggregate([evaluate_page(reference(physical="underdetermined"),
                                         {"response": {"items": [candidate(physical={"kind": "hole"})]}})])
    assert overclaim["fields"]["physical"]["verdicts"].get("overclaim") == 1
    assert overclaim["candidate_overclaim_rate"] is not None
    assert overclaim["candidate_overclaim_rate"] > 0

    refused = aggregate([evaluate_page(reference(),
                                       {"response": {"items": [candidate(physical={"kind": "unknown"},
                                                                          size={"value": None, "unit": None,
                                                                                "state": "unknown"})]}})])
    assert refused["fields"]["physical"]["verdicts"].get("abstained") == 1
    # Sayısal alanda değer bildirmemek `omission`dır; ikisi de abstention tarafında toplanır.
    assert refused["fields"]["size"]["verdicts"].get("omission") == 1
    assert refused["candidate_abstention_rate"] is not None
    assert refused["candidate_overclaim_rate"] == 0.0


def test_extras_inside_the_claimed_scope_are_false_positives_and_outside_are_unscorable():
    """§12: gold kapsamadığı yeri suçlamaz; kapsadığı yerdeki fazla aday yanlış pozitiftir."""
    far = candidate(candidate_id="c9", target={"region": {"x0": 0.80, "y0": 0.80, "x1": 0.84,
                                                          "y1": 0.88}, "observation_id": None,
                                                "state": "bound"})
    unscoped = evaluate_page(reference(), {"response": {"items": [candidate(), far]}})
    assert unscoped["extras"] == [{"candidate_id": "c9",
                                   "anchor": [0.8, 0.8, 0.84, 0.88],
                                   "kind": "unscorable_extra_candidate"}]

    scoped = evaluate_page({**reference(), "exhaustiveness": {"scope": "full_page"}},
                           {"response": {"items": [candidate(), far]}})
    assert scoped["extras"][0]["kind"] == "false_positive"
    assert scoped["summary"]["false_positive_candidates"] == 1

    regions = evaluate_page({**reference(), "exhaustiveness": {"scope": "regions",
                                                               "regions": [[0.75, 0.75, 0.9, 0.95]]}},
                            {"response": {"items": [candidate(), far]}})
    assert regions["extras"][0]["kind"] == "false_positive"
    assert regions["summary"]["unscorable_extra_candidates"] == 0

    # §12: "predicates" = "şu yüklemler için eksiksizim" → kapsam gold claim'lerinin kendisidir.
    # Gold'un feature'ına oturan fazla aday yanlış pozitiftir; uzaktaki aday cezalanmaz.
    predicates = evaluate_page({**reference(),
                                "exhaustiveness": {"scope": "predicates",
                                                   "predicates": ["size", "termination"]}},
                               {"response": {"items": [candidate(), far]}})
    assert predicates["exhaustiveness"]["predicates"] == ["size", "termination"]
    assert predicates["extras"][0]["kind"] == "unscorable_extra_candidate"
    duplicate = candidate(candidate_id="c10")
    on_feature = evaluate_page({**reference(),
                                "exhaustiveness": {"scope": "predicates",
                                                   "predicates": ["size"]}},
                               {"response": {"items": [candidate(), duplicate]}})
    # İki aday aynı feature'a oturursa kalem belirsizdir (§10: puanlanmaz) ve gold'un kapsadığı
    # bölgede **iki** fazla aday vardır: ikisi de yanlış pozitiftir, ikisi de sayıdan düşmez.
    assert sorted(row["kind"] for row in on_feature["extras"]) == ["false_positive", "false_positive"]
    assert on_feature["summary"]["ambiguous_claims"] == 1


def test_a_placeholder_exhaustiveness_never_penalizes_extras():
    far = candidate(candidate_id="c9", target={"region": {"x0": 0.80, "y0": 0.80, "x1": 0.84,
                                                          "y1": 0.88}, "observation_id": None,
                                                "state": "bound"})
    page = evaluate_page({**reference(), "exhaustiveness": "EKSİK: hangi bölgeler tarandı"},
                         {"response": {"items": [candidate(), far]}})
    assert page["exhaustiveness"]["scope"] is None
    assert page["summary"]["unscorable_extra_candidates"] == 1
    assert page["summary"]["false_positive_candidates"] == 0
