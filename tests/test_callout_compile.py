"""G7 compiler + G8 readiness (`PLAN.md` §13/§14) on synthetic session records.

The three PLAN §13 examples are pinned as they are written (Ø8 THRU + circle → through hole; 4× the
same → four decisions; a plain number + two ends → the existing Binding shape), together with the
things that must *not* happen: a diameter without THRU/BLIND is not a hole, a radius does not become
a fillet, a count does not invent circles, and the user's own decision is never overwritten.
"""
import copy

from callout_fixtures import ARC, WIRE, record

from drawingto3d import callout_compile, callout_readiness
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION
from drawingto3d.callout_parse import semantic_parse

THRU = {"target_kind": "circle", "target_ids": ["c0"]}


def _add_callout(row, callout_id, text, region, target):
    """A second detected callout with its own text, parse and confirmation (same record)."""
    row["callout_candidates"].append({"id": callout_id, "source_digest": row["source_sha256"],
                                      "page_index": 0, "region": list(region), "crop_region": list(region),
                                      "source_kind": "vector_text", "observation_ids": [],
                                      "detector_version": "callout-detector/1",
                                      "geometry_version": row["geometry_version"],
                                      "machine_text_hint": text})
    row["decisions"]["transcriptions"].append({"callout_id": callout_id, "raw_text": text,
                                               "normalized_text": text, "entered_by": "user",
                                               "source_region": list(region), "revision": 1})
    row["callout_parses"].append(semantic_parse({"callout_id": callout_id, "raw_text": text,
                                                 "revision": 1}, sheet_unit="mm").model_dump(mode="json"))
    target = {"callout_id": callout_id, "transcription_revision": 1,
              "parser_version": CALLOUT_PARSER_VERSION, "geometry_version": row["geometry_version"],
              "geometry_key": row["decisions"]["callout_targets"][0]["geometry_key"],
              "evidence": [{"kind": "user_click", "ref": "c0"}], "status": "confirmed", "reconfirm": False,
              **target}
    row["decisions"]["callout_targets"].append(target)
    return row


# --- PLAN §13 — the three written examples ----------------------------------------------

def test_a_through_callout_and_a_confirmed_circle_compiles_to_one_hole():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == [{"circle_id": "c0", "kind": "through", "diameter": 8.0, "depth": None}]
    assert compiled["rows"][0]["status"] == "compiled"
    assert compiled["rows"][0]["decision"]["kind"] == "through"
    assert compiled["unsupported"] == [] and compiled["conflicts"] == []


def test_a_count_callout_compiles_one_decision_per_confirmed_circle():
    circles = [{"id": f"c{i}", "center": center, "radius": 8.0}
               for i, center in enumerate([[35.0, 40.0], [55.0, 40.0], [35.0, 60.0], [55.0, 60.0]])]
    target = {"target_kind": "circle_group", "target_ids": ["c0", "c1", "c2", "c3"]}
    row = record("4x Ø16 THRU", [0.05, 0.15, 0.30, 0.40], circles=circles, count=4, stored_target=target)
    compiled = callout_compile.compile_callouts(row)
    assert [item["circle_id"] for item in compiled["holes"]] == ["c0", "c1", "c2", "c3"]
    assert {item["kind"] for item in compiled["holes"]} == {"through"}
    assert compiled["rows"][0]["decision"]["count"] == 4


def test_a_plain_number_and_a_vertex_pair_compile_to_a_binding():
    target = {"target_kind": "vertex_pair", "target_ids": ["g0:start", "g0:end"]}
    row = record("50", [0.05, 0.05, 0.45, 0.20], stored_target=target)
    compiled = callout_compile.compile_callouts(row)
    assert len(compiled["bindings"]) == 1
    binding = compiled["bindings"][0]
    assert binding["value"] == 50.0 and binding["unit"] == "mm"
    assert binding["axis"] == "x" and binding["direction"] == 1
    assert binding["first"]["id"] == "g0:start" and binding["second"]["id"] == "g0:end"
    assert binding["first"]["x"] == 20.0 and binding["first"]["y"] == 20.0


# --- what must not be guessed ------------------------------------------------------------

def test_a_diameter_without_termination_is_unsupported_not_a_hole():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == []
    assert compiled["rows"][0]["status"] == "unsupported_cad_feature"
    assert compiled["unsupported"][0]["reason"] == "unsupported_cad_feature"
    assert "THRU" in compiled["unsupported"][0]["detail"]


def test_a_blind_callout_keeps_the_printed_depth():
    row = record("Ø10 6 DEEP", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == [{"circle_id": "c0", "kind": "pocket", "diameter": 10.0, "depth": 6.0}]


def test_a_radius_with_a_confirmed_arc_is_an_explicit_unsupported_cad_feature():
    target = {"target_kind": "arc", "target_ids": ["a0"]}
    row = record("R8", [0.62, 0.10, 0.80, 0.30], circles=[], arcs=[ARC], stored_target=target)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == [] and compiled["bindings"] == []
    assert compiled["rows"][0]["status"] == "unsupported_cad_feature"
    assert compiled["unsupported"][0]["reason"] == "unsupported_cad_feature"
    assert "yarıçap" in compiled["unsupported"][0]["detail"]


def test_a_missing_unit_blocks_the_compile():
    """Ne metinde ne sayfada birim yoksa ölçü çözülemez: derleme durur, tahmin edilmez."""
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU, calibration=False)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["rows"][0]["status"] == "missing_unit"
    assert compiled["holes"] == []
    assert callout_readiness.build_readiness(row)["categories"] == {"missing_unit": 1}


def test_a_unit_less_text_is_resolved_by_the_sheets_own_unit():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"][0]["diameter"] == 8.0
    assert compiled["rows"][0]["unit_source"] == "sheet"


def test_the_users_own_hole_decision_is_never_overwritten():
    manual = [{"circle_id": "c0", "kind": "pocket", "diameter": 12.0, "depth": 3.0}]
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU, manual_holes=manual)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == []
    assert compiled["conflicts"][0]["reason"] == "manual_conflict"
    merged = callout_compile.apply_compiled(row["decisions"], compiled)
    assert merged["holes"] == manual, "kullanıcının kararı aynen kalır"


def test_two_callouts_naming_one_circle_differently_conflict():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    _add_callout(row, "k2", "Ø10 THRU", [0.40, 0.20, 0.60, 0.32], {"target_kind": "circle",
                                                                  "target_ids": ["c0"]})
    compiled = callout_compile.compile_callouts(row)
    assert len(compiled["holes"]) == 1
    assert any(item["reason"] == "callout_conflict" for item in compiled["conflicts"])


def test_an_unknown_target_id_is_a_conflict_not_a_guess():
    target = {"target_kind": "circle", "target_ids": ["c9"]}
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=target)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["conflicts"][0]["reason"] == "unknown_geometry"
    assert compiled["holes"] == []


# --- exclusions and merges ---------------------------------------------------------------

def test_an_ignored_or_unbindable_callout_is_a_declared_exclusion():
    for kwargs, reason in (({"ignored": True}, "ignored"), ({"unbindable": True}, "unbindable_declared")):
        row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU, **kwargs)
        compiled = callout_compile.compile_callouts(row)
        assert compiled["excluded"] == [{"callout_id": "k1", "reason": reason}]
        assert compiled["rows"][0]["status"] == "excluded"
        # G12.1 (PLAN-24 §12): eski kayıt derlemeden dışlanır AMA kanıtsızdır — kapsam denetimi onu
        # `legacy_unclassified` sayar ve build'i AÇMAZ. (Eski "kapsam dışı engel değil" yorumu, G11
        # koşusunun sahte hazırlığını üreten yorumdu.)
        readiness = callout_readiness.build_readiness(row)
        assert readiness["ready"] is False
        assert readiness["coverage"]["legacy_unclassified"] == ["k1"]
        assert [q["category"] for q in readiness["questions"]] == ["legacy_unclassified"]


def test_a_named_disposition_replaces_the_legacy_flags_in_the_compiler_chain():
    """G12.1 (PLAN-24 §11): adı konmuş kapsam claim'i derlemede kendini söyler.

    `not_model_input` engel değildir; `build_relevant_unsupported` gerçek bilgidir ve engeldir —
    exclusions listesi hangi claim'in ne olduğunu kayıtta taşır (denetim izi).
    """
    claim = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU,
                   disposition="not_model_input")
    assert callout_compile.compile_callouts(claim)["excluded"] == [
        {"callout_id": "k1", "reason": "not_model_input", "disposition": "not_model_input",
         "duplicate_of": None, "detail": None}]
    assert callout_readiness.build_readiness(claim)["ready"] is True

    real = record("80,00", [0.10, 0.20, 0.20, 0.32], disposition="build_relevant_unsupported",
                  disposition_reason="yazılı daralma ölçüsü; hedefi yok")
    excluded = callout_compile.compile_callouts(real)["excluded"]
    assert excluded[0]["reason"] == "build_relevant_unsupported"
    assert excluded[0]["disposition"] == "build_relevant_unsupported"
    assert excluded[0]["detail"] == "yazılı daralma ölçüsü; hedefi yok"
    readiness = callout_readiness.build_readiness(real)
    assert readiness["ready"] is False
    assert readiness["coverage"]["build_relevant_unsupported"] == ["k1"]


def test_apply_compiled_adds_without_duplicating():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    merged = callout_compile.apply_compiled(row["decisions"], compiled)
    assert len(merged["holes"]) == 1
    again = callout_compile.apply_compiled(merged, compiled)
    assert len(again["holes"]) == 1, "aynı karar iki kez eklenmez"
    assert row["decisions"]["holes"] == [], "kayıt yerinde değişmez"


# --- G8 readiness ------------------------------------------------------------------------

def test_readiness_blocks_until_the_chain_is_complete():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32])
    plain = callout_readiness.build_readiness(row)
    assert plain["ready"] is False
    assert plain["questions"][0]["category"] == "missing_target"
    assert plain["questions"][0]["callout_id"] == "k1"
    assert "k1" in plain["questions"][0]["text"]
    ready = callout_readiness.build_readiness(
        record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU))
    assert ready["ready"] is True and ready["questions"] == []
    assert ready["compiled"]["compiled_holes"] == 1


def test_readiness_names_every_waiting_state_in_the_plans_categories():
    no_text = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    no_text["decisions"]["transcriptions"] = []
    assert callout_readiness.build_readiness(no_text)["categories"] == {"missing_transcription": 1}
    stale = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32],
                   stored_target={**THRU, "parser_version": "callout-parser/0"})
    assert callout_readiness.build_readiness(stale)["categories"] == {"stale_target": 1}
    bad_arc = record("R8", [0.62, 0.10, 0.80, 0.30], circles=[], arcs=[ARC],
                     stored_target={"target_kind": "arc", "target_ids": ["a0"]})
    assert callout_readiness.build_readiness(bad_arc)["categories"] == {"unsupported_cad_feature": 1}


def test_readiness_carries_the_audit_chain_per_callout():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    readiness = callout_readiness.build_readiness(row, feature_ids={"c0": ["hole_1"]})
    chain = readiness["rows"][0]
    assert chain["callout_id"] == "k1" and chain["raw_text"] == "Ø8 THRU"
    assert chain["parser_version"] == CALLOUT_PARSER_VERSION
    assert chain["semantic"]["form"] == "diameter" and chain["semantic"]["termination"] == "thru"
    assert chain["target_ids"] == ["c0"]
    assert chain["geometry_key"] and chain["compiled_decision"]["kind"] == "through"
    assert chain["generated_features"] == ["hole_1"]
    assert callout_readiness.readiness_questions(readiness) == []


def test_sheet_issues_are_merged_with_their_own_categories():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    readiness = callout_readiness.build_readiness(row, sheet_issues=[
        {"category": "missing_calibration", "detail": "Bilinen ölçünün iki noktasını ve uzunluğunu belirtin."}])
    assert readiness["ready"] is False
    assert readiness["categories"] == {"missing_calibration": 1}
    assert readiness["questions"][0]["text"].startswith("Bilinen ölçünün")


def test_provenance_rows_keep_the_chain_order():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    chain = callout_compile.compile_provenance(compiled)[0]
    assert set(chain) == {"callout_id", "raw_text", "parser_version", "semantic", "target_kind",
                          "target_ids", "geometry_key", "geometry_version", "status", "reason",
                          "compiled_decision", "generated_features"}
    assert copy.deepcopy(compiled) == callout_compile.compile_callouts(row), "derleme deterministik"


# --- R01/R02/R04 — bağımsız inceleme düzeltme turu (2026-10-07) -----------------------------

VERTICAL_END = {"target_kind": "vertex_pair", "target_ids": ["g1:start", "g1:end"]}


def test_a_vertical_tie_reads_the_sheets_own_y_axis():
    """R01: sayfa y'si aşağı, parça y'si yukarı — yön sayfa farkından değil, pafta ekseninden okunur."""
    row = record("30 mm", [0.10, 0.20, 0.20, 0.32], stored_target=VERTICAL_END)
    binding = callout_compile.compile_callouts(row)["bindings"][0]
    assert binding["axis"] == "y" and binding["direction"] == -1
    assert binding["first"]["id"] == "g1:start" and binding["second"]["id"] == "g1:end"


def test_a_reversed_pair_flips_the_direction_not_the_axis():
    row = record("30 mm", [0.10, 0.20, 0.20, 0.32],
                 stored_target={"target_kind": "vertex_pair", "target_ids": ["g1:end", "g1:start"]})
    binding = callout_compile.compile_callouts(row)["bindings"][0]
    assert binding["axis"] == "y" and binding["direction"] == 1


def test_a_rotated_view_turns_the_tie_axis_with_the_sheet():
    """R01: x_page=[0,1] ile sayfa-dikey bağ paftanın X eksenindedir — sadece dy işareti çevirmek yetmez."""
    row = record("30 mm", [0.10, 0.20, 0.20, 0.32], stored_target=VERTICAL_END,
                 view={"x_page": [0.0, 1.0], "y_page": [1.0, 0.0], "source": "page_axes"})
    binding = callout_compile.compile_callouts(row)["bindings"][0]
    assert binding["axis"] == "x" and binding["direction"] == 1


def test_a_record_without_a_vouchable_view_makes_the_axis_an_open_decision():
    """R01 + PLAN §8.6: görüş yoksa eksen uydurulmaz — derleme durur ve açık karar döner."""
    row = record("30 mm", [0.10, 0.20, 0.20, 0.32],
                 stored_target={"target_kind": "vertex_pair", "target_ids": ["g0:start", "g0:end"]},
                 sheet_frame=False)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["bindings"] == []
    assert compiled["rows"][0]["status"] == "view_not_confirmed"
    readiness = callout_readiness.build_readiness(row)
    assert readiness["categories"] == {"missing_view": 1}
    assert readiness["questions"][0]["action"] == "confirm_view"


def test_a_printed_inch_depth_is_converted_with_its_diameter():
    """R02: basılı `in` derinliği de belirler — 0.25 in 6.35 mm'dir, çap 12.7 mm."""
    row = record("Ø.5 .25 DEEP in", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == [{"circle_id": "c0", "kind": "pocket", "diameter": 12.7, "depth": 6.35}]


def test_a_sheet_inch_depth_is_converted_too():
    row = record("Ø.5 .25 DEEP", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    row["decisions"]["calibration"]["unit"] = "in"
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"][0]["diameter"] == 12.7 and compiled["holes"][0]["depth"] == 6.35
    assert compiled["rows"][0]["unit_source"] == "sheet"


def test_a_printed_mm_depth_is_left_alone():
    row = record("Ø.5 .25 DEEP mm", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"][0]["depth"] == 0.25
    assert compiled["rows"][0]["unit_source"] == "printed"


def test_a_converted_hole_is_refused_when_it_breaks_the_models_own_bound():
    from drawingto3d.guided import Hole

    bound = next(meta.le for meta in Hole.model_fields["depth"].metadata if hasattr(meta, "le"))
    assert callout_compile.MM_LIMIT == bound, "sınır modelin kendi değerini kopyalar"
    row = record("Ø.5 40000 DEEP in", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    compiled = callout_compile.compile_callouts(row)
    assert compiled["holes"] == []
    assert compiled["rows"][0]["status"] == "unsupported_semantic"
    assert compiled["rows"][0]["reason"] == "depth_out_of_range"


def test_a_supported_reading_is_judged_before_a_missing_target():
    """R04: `M8`'in sorusu metni düzeltmektir; hedefsiz diye eksik hedef gibi sunulmaz."""
    row = record("M8", [0.10, 0.20, 0.20, 0.32])
    compiled = callout_compile.compile_callouts(row)
    assert compiled["rows"][0]["status"] == "parse_unsupported"
    assert compiled["rows"][0]["semantic"]["status"] == "unsupported", "semantik alanlar dolmalı"
    readiness = callout_readiness.build_readiness(row)
    assert readiness["categories"] == {"parse_error": 1}
    assert readiness["questions"][0]["action"] == "edit_transcription"
    assert "missing_target" not in readiness["categories"]


def test_an_ambiguous_reading_is_judged_before_a_missing_target():
    row = record("Ø8 9", [0.10, 0.20, 0.20, 0.32])
    readiness = callout_readiness.build_readiness(row)
    assert readiness["categories"] == {"parse_ambiguous": 1}
    assert readiness["questions"][0]["action"] == "edit_transcription"
