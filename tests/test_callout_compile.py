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
        assert callout_readiness.build_readiness(row)["ready"] is True, "kapsam dışı engel değil"


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
