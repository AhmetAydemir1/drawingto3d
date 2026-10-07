"""GX review export/import (`PLAN.md` §12) on synthetic records.

The bundle is the reviewer's picture of a session; the import is *untrusted input*: every action is
validated against the record it claims to belong to (session, source digest, base revision, known
callouts, geometry that really exists) and nothing is applied here at all — `validate_import` is
pure. The last test pins that: a full validation leaves the record byte-identical.
"""
import copy
import json

from callout_fixtures import ARC, circle, record

from drawingto3d import callout_review
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION, CALLOUT_SCHEMA_VERSION, geometry_key

THRU = {"target_kind": "circle", "target_ids": ["c0"], "transcription_revision": 1,
        "parser_version": CALLOUT_PARSER_VERSION}


def bundle_for(row, actions=None, **over):
    bundle = callout_review.export_bundle(row)
    if actions is not None:
        bundle["actions"] = actions
    bundle.update(over)
    return bundle


def action(name, callout_id="k1", **payload):
    return {"action": name, "callout_id": callout_id, **payload}


# --- export (PLAN §12, minimum fields) ---------------------------------------------------

def test_the_bundle_carries_every_required_field_and_the_chain_per_callout():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    bundle = callout_review.export_bundle(row)
    for key in ("schema_version", "session", "base_revision", "source_digest", "page", "callouts"):
        assert key in bundle, key
    assert bundle["schema_version"] == CALLOUT_SCHEMA_VERSION == 5
    assert bundle["session"] == row["token"] and bundle["base_revision"] == row["revision"] == 1
    assert bundle["source_digest"] == row["source_sha256"]
    callout = bundle["callouts"][0]
    assert callout["callout_id"] == "k1" and callout["raw_text"] == "Ø8 THRU"
    assert callout["region"] == [0.10, 0.20, 0.20, 0.32]
    assert callout["machine_text_hint"] == "Ø8 THRU"
    assert callout["semantic_parse"]["form"] == "diameter" and callout["semantic_parse"]["termination"] == "thru"
    assert callout["freshness"]["target"] == {"state": "current", "reason": None}
    assert callout["confirmed_target"]["target_ids"] == ["c0"]
    assert callout["ignored"] is False and callout["unbindable"] is False
    assert "duplicate_pin" in callout, "dış inceleme onayın kanıtını görür (G12R-02)"
    assert [item["target_kind"] for item in callout["target_proposals"]] == ["circle", "circle"]
    assert callout["target_proposals"][0]["evidence_tier"] == "T0", "onaylanmış hedef ilk sırada"


def test_the_bundle_shows_proposals_and_freshness_for_a_callout_without_a_decision():
    bundle = callout_review.export_bundle(record("Ø8", [0.10, 0.20, 0.20, 0.32],
                                                 circles=[circle("c0", [45.0, 45.0], mm=8.0)]))
    callout = bundle["callouts"][0]
    assert callout["confirmed_target"] is None
    assert callout["target_proposals"] and callout["target_proposals"][0]["target_ids"] == ["c0"]
    assert callout["freshness"]["target"] == {"state": "missing", "reason": "needs_target"}


# --- import validation: associations ------------------------------------------------------

def test_a_matching_bundle_imports_and_its_actions_are_normalised():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    bundle = bundle_for(row, [action("transcribe", raw_text="Ø10 THRU"),
                              action("ignore"), action("confirm_target", target_kind="circle",
                                                       target_ids=["c0"])])
    plan = callout_review.validate_import(row, bundle)
    assert plan["ok"] is True and plan["errors"] == []
    assert plan["actions"] == [
        {"action": "transcribe", "callout_id": "k1", "payload": {"raw_text": "Ø10 THRU"}},
        {"action": "ignore", "callout_id": "k1", "payload": {}},
        {"action": "confirm_target", "callout_id": "k1",
         "payload": {"target_kind": "circle", "target_ids": ["c0"]}}]


def test_a_stale_base_revision_is_rejected():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    plan = callout_review.validate_import(row, bundle_for(row, [action("ignore")], base_revision=0))
    assert plan["ok"] is False and plan["actions"] == []
    assert plan["errors"][0]["reason"] == "stale_base_revision"


def test_a_bundle_from_another_session_or_source_is_rejected():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    other = bundle_for(row, [action("ignore")], session="b" * 32)
    assert [item["reason"] for item in callout_review.validate_import(row, other)["errors"]] == \
        ["session_mismatch"]
    digest = bundle_for(row, [action("ignore")], source_digest="f" * 64)
    assert [item["reason"] for item in callout_review.validate_import(row, digest)["errors"]] == \
        ["source_mismatch"]


def test_a_bundle_from_another_schema_or_version_is_rejected():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    old = bundle_for(row, [action("ignore")], schema_version=2)
    codes = [item["reason"] for item in callout_review.validate_import(row, old)["errors"]]
    assert codes == ["schema_version_mismatch"]
    alien = bundle_for(row, [action("ignore")], bundle_version=99)
    codes = [item["reason"] for item in callout_review.validate_import(row, alien)["errors"]]
    assert codes == ["unknown_bundle_version"]


def test_unknown_callouts_actions_and_empty_action_lists_are_rejected():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    cases = [([action("ignore", callout_id="k9")], "unknown_callout"),
             ([action("delete_everything")], "unknown_action"),
             ([], "no_actions"),
             (["not-a-dict"], "not_an_object")]
    for actions, reason in cases:
        plan = callout_review.validate_import(row, bundle_for(row, actions))
        assert plan["ok"] is False and plan["actions"] == []
        assert reason in [item["reason"] for item in plan["errors"]], reason


# --- import validation: payloads -----------------------------------------------------------

def test_transcription_payloads_are_bounded_and_regions_checked():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    empty = callout_review.validate_import(row, bundle_for(row, [action("transcribe", raw_text="   ")]))
    assert [item["reason"] for item in empty["errors"]] == ["empty_text"]
    long_text = callout_review.validate_import(row, bundle_for(row, [action("transcribe", raw_text="x" * 201)]))
    assert [item["reason"] for item in long_text["errors"]] == ["text_too_long"]
    outside = callout_review.validate_import(row, bundle_for(row, [action("transcribe", raw_text="Ø8",
                                                                          region=[0.9, 0.9, 0.2, 0.2])]))
    assert [item["reason"] for item in outside["errors"]] == ["invalid_region"]
    inside = callout_review.validate_import(row, bundle_for(row, [action("transcribe", raw_text="Ø8",
                                                                         region=[0.2, 0.2, 0.3, 0.3])]))
    assert inside["ok"] is True and inside["actions"][0]["payload"]["region"] == [0.2, 0.2, 0.3, 0.3]


def test_targets_are_checked_against_the_geometry_the_record_really_has():
    circles = [circle("c0", [45.0, 45.0], mm=8.0), circle("c1", [95.0, 45.0], mm=8.0)]
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], circles=circles, stored_target=THRU)
    missing = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle", target_ids=["c7"])]))
    assert [item["reason"] for item in missing["errors"]] == ["unknown_geometry"]
    group = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle_group", target_ids=["c0", "c1"])]))
    assert group["ok"] is True, "iki daireli grup geometride var"
    one = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle_group", target_ids=["c0"])]))
    assert [item["reason"] for item in one["errors"]] == ["cardinality"]
    duplicate = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle_group", target_ids=["c0", "c0"])]))
    assert [item["reason"] for item in duplicate["errors"]] == ["duplicate_target_ids"]
    kinds = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="hole", target_ids=["c0"])]))
    assert [item["reason"] for item in kinds["errors"]] == ["unknown_target_kind"]


def test_an_arc_target_is_accepted_and_an_unknown_arc_is_not():
    row = record("R8", [0.62, 0.10, 0.80, 0.30], circles=[], arcs=[ARC],
                 stored_target={"target_kind": "arc", "target_ids": ["a0"]})
    assert callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="arc", target_ids=["a0"])]))["ok"] is True
    unknown = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="arc", target_ids=["a9"])]))
    assert [item["reason"] for item in unknown["errors"]] == ["unknown_geometry"]


def test_a_vertex_pair_target_must_name_two_real_ends():
    row = record("50", [0.05, 0.05, 0.45, 0.20], stored_target={"target_kind": "vertex_pair",
                                                                "target_ids": ["g0:start", "g0:end"]})
    good = callout_review.validate_import(row, bundle_for(row, [action(
        "select_target", target_kind="vertex_pair", target_ids=["g0:start", "g0:end"])]))
    assert good["ok"] is True and good["actions"][0]["action"] == "select_target"
    bad = callout_review.validate_import(row, bundle_for(row, [action(
        "select_target", target_kind="vertex_pair", target_ids=["g0:middle", "g0:end"])]))
    assert [item["reason"] for item in bad["errors"]] == ["unknown_geometry"]
    missing_end = callout_review.validate_import(row, bundle_for(row, [action(
        "select_target", target_kind="vertex_pair", target_ids=["g0:start"])]))
    assert [item["reason"] for item in missing_end["errors"]] == ["cardinality"]


def test_a_target_without_a_current_reading_is_rejected():
    """Onay bir okumaya yaslanır; okuma yoksa içe aktarma da onaylayamaz (PLAN §9/§12)."""
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    row["callout_parses"] = []                                   # okuma düşmüş: onay dayanaksız
    plan = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle", target_ids=["c0"])]))
    assert [item["reason"] for item in plan["errors"]] == ["no_current_parse"]
    row["decisions"]["transcriptions"] = []
    plan = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle", target_ids=["c0"])]))
    assert [item["reason"] for item in plan["errors"]] == ["no_transcription"]


def test_evidence_is_bounded_and_never_free_text():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    good = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle", target_ids=["c0"],
        evidence=[{"kind": "review_note", "ref": "sayfa 1, sol üst"}] )]))
    assert good["ok"] is True
    assert good["actions"][0]["payload"]["evidence"] == [{"kind": "review_note", "ref": "sayfa 1, sol üst"}]
    blank = callout_review.validate_import(row, bundle_for(row, [action(
        "confirm_target", target_kind="circle", target_ids=["c0"],
        evidence=[{"kind": "", "ref": "x"}])]))
    assert [item["reason"] for item in blank["errors"]] == ["invalid_evidence"]


# --- the door stays shut ------------------------------------------------------------------

def test_an_all_or_nothing_validation_never_touches_the_record():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    before = json.loads(json.dumps(row))
    mixed = bundle_for(row, [action("transcribe", raw_text="Ø10 THRU"),
                             action("confirm_target", target_kind="circle", target_ids=["c7"])])
    plan = callout_review.validate_import(row, mixed)
    assert plan["ok"] is False
    assert plan["actions"] == [], "tek hata bütün partiyi reddeder (all-or-nothing)"
    assert copy.deepcopy(row) == before, "doğrulama kaydı hiç değiştirmez"


# --- R05 — paket, incelendiği bağlamı taşır (2026-10-07) ------------------------------------

def test_the_bundle_carries_the_parser_and_geometry_context_it_was_reviewed_in():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    bundle = callout_review.export_bundle(row)
    assert bundle["parser_version"] == CALLOUT_PARSER_VERSION
    assert bundle["geometry_version"] == row["geometry_version"]
    assert bundle["geometry_key"] == geometry_key(row)


def test_a_bundle_from_another_parser_or_geometry_context_is_refused():
    row = record("Ø8 THRU", [0.10, 0.20, 0.20, 0.32], stored_target=THRU)
    assert callout_review.validate_import(row, bundle_for(row, [action("ignore")]))["ok"] is True, \
        "bağlam eşitken paket geçer (kontrol)"
    stale_parser = bundle_for(row, [action("ignore")], parser_version="callout-parser/obsolete")
    assert [item["reason"] for item in callout_review.validate_import(row, stale_parser)["errors"]] == \
        ["parser_version_mismatch"]
    moved_version = bundle_for(row, [action("ignore")], geometry_version=row["geometry_version"] + 1)
    assert [item["reason"] for item in callout_review.validate_import(row, moved_version)["errors"]] == \
        ["geometry_version_mismatch"]
    moved_key = bundle_for(row, [action("ignore")], geometry_key="0" * 32)
    assert [item["reason"] for item in callout_review.validate_import(row, moved_key)["errors"]] == \
        ["geometry_mismatch"]
    missing_key = bundle_for(row, [action("ignore")])
    missing_key.pop("geometry_key")
    assert [item["reason"] for item in callout_review.validate_import(row, missing_key)["errors"]] == \
        ["geometry_mismatch"], "bağlamı taşımayan paket kabul edilmez"
