"""G1 callout contract (PLAN-20 §6): candidate / transcription / parse / confirmed target.

Model-level tests: round-trip, "missing information stays null", and every rejection the contract
names — regions, counts, sizes, enums, unknown fields, cardinality, duplicate ids. Pure helpers
(`normalize_text`, `geometry_key`, `callout_states`) are pinned here too; the store behaviour
(save/merge/undo/public/build) lives in `test_guided_callouts.py`.
"""
import copy
import json

import pytest
from pydantic import ValidationError

from drawingto3d import callout_models as cm
from drawingto3d.callout_models import (CalloutCandidate, CalloutTargetDecision, SemanticParse,
                                        TranscriptionDecision, callout_states, geometry_key,
                                        normalize_text)

SOURCE = "d" * 64


def candidate(**over):
    row = {"id": "k1", "source_digest": SOURCE, "page_index": 0,
           "region": [0.1, 0.2, 0.4, 0.5], "crop_region": [0.05, 0.15, 0.45, 0.55],
           "source_kind": "vector_text", "observation_ids": ["o1"], "detector_version": "callout-detector/1",
           "geometry_version": 3, "machine_text_hint": "4x Ø8 THRU"}
    row.update(over)
    return row


def transcription(**over):
    row = {"callout_id": "k1", "raw_text": "4x Ø8 THRU", "entered_by": "user",
           "source_region": [0.1, 0.2, 0.4, 0.5], "revision": 5}
    row.update(over)
    return row


def parse(**over):
    row = {"callout_id": "k1", "parser_version": cm.CALLOUT_PARSER_VERSION, "transcription_revision": 5,
           "status": "parsed", "form": "diameter", "size": 8.0, "count": 4, "termination": "thru"}
    row.update(over)
    return row


def target(**over):
    row = {"callout_id": "k1", "target_kind": "circle", "target_ids": ["c0"],
           "geometry_version": 3, "geometry_key": "pin", "profile_id": "outline_0",
           "transcription_revision": 5, "parser_version": cm.CALLOUT_PARSER_VERSION,
           "evidence": [{"kind": "user_click", "ref": "c0"}]}
    row.update(over)
    return row


def options():
    return {
        "frame": {"width": 300, "height": 200},
        "profiles": [
            {"id": "outline_0", "kind": "wire", "points": [[20, 20], [120, 20], [120, 80], [20, 80]],
             "edges": [{"id": "g0", "kind": "line", "start": [20.0, 20.0], "end": [120.0, 20.0]},
                       {"id": "g1", "kind": "line", "start": [120.0, 20.0], "end": [120.0, 80.0]},
                       {"id": "g2", "kind": "line", "start": [120.0, 80.0], "end": [20.0, 80.0]},
                       {"id": "g3", "kind": "line", "start": [20.0, 80.0], "end": [20.0, 20.0]}]},
            {"id": "outline_1", "kind": "wire", "points": [[220, 20], [260, 20], [260, 40], [220, 40]],
             "edges": [{"id": "h0", "kind": "line", "start": [220.0, 20.0], "end": [260.0, 20.0]},
                       {"id": "h1", "kind": "line", "start": [260.0, 20.0], "end": [260.0, 40.0]}]},
        ],
        "circles": [{"id": "c0", "center": [45.0, 45.0], "radius": 6.0},
                    {"id": "c1", "center": [90.0, 50.0], "radius": 6.0}],
        "measurements": [],
    }


def make_record(*, transcriptions=(), targets=(), parses=(), candidates=None, decisions=None, **over):
    decisions = {"profile_id": "outline_0", "thickness": 10.0,
                 "transcriptions": list(transcriptions), "callout_targets": list(targets),
                 **(decisions or {})}
    record = {"token": "a" * 32, "revision": 0, "source_sha256": SOURCE, "geometry_version": 3,
              "options": options(), "decisions": decisions,
              "callout_candidates": candidates if candidates is not None else [candidate()],
              "callout_parses": list(parses), "history": [], "build": None, "log": []}
    record.update(over)
    return record


# --- models ---------------------------------------------------------------

def test_four_models_round_trip_through_json_without_inventing_fields():
    rows = [CalloutCandidate.model_validate(candidate()),
            TranscriptionDecision.model_validate(transcription()),
            SemanticParse.model_validate(parse()),
            CalloutTargetDecision.model_validate(target())]
    for row in rows:
        again = type(row).model_validate(json.loads(json.dumps(row.model_dump(mode="json"))))
        assert again == row
    parsed = rows[2]
    assert set(parsed.model_dump()) == {"callout_id", "parser_version", "transcription_revision",
                                        "status", "form", "size", "count", "termination", "depth",
                                        "unit", "warnings"}
    minimal = SemanticParse.model_validate({"callout_id": "k1", "parser_version": "p/1",
                                            "transcription_revision": 1, "status": "parsed",
                                            "form": "diameter", "size": 8.0})
    assert minimal.count is None and minimal.termination is None and minimal.depth is None
    assert minimal.unit is None and minimal.warnings == []
    assert CalloutCandidate.model_validate(candidate(machine_text_hint=None)).machine_text_hint is None
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate({**candidate(), "bogus": 1})          # unknown alan kendiliğinden dolmaz


@pytest.mark.parametrize("region", [
    [0.4, 0.2, 0.1, 0.5],            # ters kutu (x0 > x1)
    [0.1, 0.5, 0.4, 0.2],            # ters kutu (y0 > y1)
    [0.2, 0.2, 0.2, 0.5],            # sıfır alan
    [0.1, 0.2, 1.2, 0.5],            # sayfa dışı
    [-0.1, 0.2, 0.4, 0.5],           # sayfa dışı
    [float("nan"), 0.2, 0.4, 0.5],   # NaN
    [0.1, 0.2, float("inf"), 0.5],   # sonsuz
    [0.1, 0.2, 0.3],                 # eksik dörtlü
])
def test_a_region_outside_the_contract_is_rejected(region):
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(region=region))
    with pytest.raises(ValidationError):
        TranscriptionDecision.model_validate(transcription(source_region=region))


def test_the_crop_covers_the_region_and_stays_on_the_page():
    CalloutCandidate.model_validate(candidate(crop_region=[0.1, 0.2, 0.4, 0.5]))   # eşitlik serbest
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(crop_region=[0.2, 0.2, 0.3, 0.4]))
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(crop_region=[-0.2, 0.2, 0.4, 0.5]))


def test_candidate_identity_kind_and_page_are_explicit():
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(id=""))
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(source_kind="vlm"))
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(page_index=True))       # bool bir sayfa değildir
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(page_index=-1))
    with pytest.raises(ValidationError):
        CalloutCandidate.model_validate(candidate(detector_version=""))
    assert CalloutCandidate.model_validate(candidate(source_kind="manual")).source_kind == "manual"
    assert CalloutCandidate.model_validate(candidate()).observation_ids == ["o1"]


def test_raw_text_is_kept_verbatim_and_blank_is_refused():
    saved = TranscriptionDecision.model_validate(transcription(raw_text="  4 × Ø8 THRU  "))
    assert saved.raw_text == "  4 × Ø8 THRU  "
    for blank in ("", "   ", "\t\n"):
        with pytest.raises(ValidationError):
            TranscriptionDecision.model_validate(transcription(raw_text=blank))
    with pytest.raises(ValidationError):
        TranscriptionDecision.model_validate(transcription(entered_by="model"))


def test_normalized_text_is_the_servers_own_derivation():
    saved = TranscriptionDecision.model_validate(transcription(raw_text="  a   b ", normalized_text="from-client"))
    assert saved.normalized_text == "a b"                       # istemcinin değeri asla kullanılmaz
    assert normalize_text("  4 × Ø8 THRU  ") == "4 × Ø8 THRU"
    assert normalize_text("a\n\t b") == "a b"
    assert normalize_text("Ø8 SOME_UNKNOWN_NOTE") == "Ø8 SOME_UNKNOWN_NOTE"   # anlam dokunulmaz (G4'ün işi)


@pytest.mark.parametrize("bad", [True, False, 0, -3, 1.5])
def test_count_is_only_an_explicit_positive_integer(bad):
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(count=bad))
    assert SemanticParse.model_validate(parse(count=4)).count == 4
    assert SemanticParse.model_validate(parse(count=None)).count is None


@pytest.mark.parametrize("value", [-1.0, 0.0, float("inf")])
def test_size_and_depth_are_positive_and_finite(value):
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(size=value))
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(depth=value))


def test_parse_enums_are_closed():
    for bad in ("ok", "done"):
        with pytest.raises(ValidationError):
            SemanticParse.model_validate(parse(status=bad))
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(form="hole"))
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(termination="through"))
    with pytest.raises(ValidationError):
        SemanticParse.model_validate(parse(unit="cm"))
    ambiguous = SemanticParse.model_validate(parse(status="ambiguous", form=None, size=None, count=None,
                                                   termination=None))
    assert ambiguous.status == "ambiguous" and ambiguous.form is None


def test_target_cardinality_is_enforced_by_kind():
    CalloutTargetDecision.model_validate(target(target_kind="circle", target_ids=["c0"]))
    CalloutTargetDecision.model_validate(target(target_kind="circle_group", target_ids=["c0", "c1"]))
    CalloutTargetDecision.model_validate(target(target_kind="vertex_pair", target_ids=["g0:start", "g1:start"]))
    for bad in ({"target_kind": "circle", "target_ids": ["c0", "c1"]},
                {"target_kind": "circle", "target_ids": []},
                {"target_kind": "circle_group", "target_ids": ["c0"]},
                {"target_kind": "vertex_pair", "target_ids": ["g0:start", "g0:start"]},
                {"target_kind": "line"}):
        with pytest.raises(ValidationError):
            CalloutTargetDecision.model_validate(target(**bad))


def test_a_group_cannot_repeat_one_id_to_reach_a_count():
    with pytest.raises(ValidationError):
        CalloutTargetDecision.model_validate(target(target_kind="circle_group",
                                                    target_ids=["c0", "c0", "c0", "c0"]))


def test_target_evidence_is_structured_and_status_is_historical():
    with pytest.raises(ValidationError):
        CalloutTargetDecision.model_validate(target(evidence=[]))
    with pytest.raises(ValidationError):
        CalloutTargetDecision.model_validate(target(evidence=["user clicked c0"]))
    with pytest.raises(ValidationError):
        CalloutTargetDecision.model_validate(target(evidence=[{"kind": "", "ref": "c0"}]))
    with pytest.raises(ValidationError):
        CalloutTargetDecision.model_validate(target(status="proposed"))
    assert CalloutTargetDecision.model_validate(target()).status == "confirmed"


# --- geometry_key ---------------------------------------------------------

def test_geometry_key_is_stable_for_the_same_context():
    record = make_record()
    assert geometry_key(record) == geometry_key(copy.deepcopy(record))
    assert geometry_key(record) == geometry_key(json.loads(json.dumps(record)))
    listed = copy.deepcopy(record)
    listed["options"]["profiles"] = list(reversed(listed["options"]["profiles"]))
    assert geometry_key(record) == geometry_key(listed)          # listeler kararlı ID sırasına göre kanonik


def test_geometry_key_separates_unrelated_decisions_from_context():
    record = make_record()
    base = geometry_key(record)
    unrelated = copy.deepcopy(record)
    unrelated["decisions"]["thickness"] = 99.0
    assert geometry_key(unrelated) == base                        # ilgisiz karar anahtarı değiştirmez
    assert geometry_key(record, {"profile_id": "outline_0", "thickness": 1.0}) == base
    profile = copy.deepcopy(record)
    profile["decisions"]["profile_id"] = "outline_1"
    assert geometry_key(profile) != base
    contour = copy.deepcopy(record)
    contour["decisions"]["contour"] = {"drop": ["g3"], "approve_join": False}
    assert geometry_key(contour) != base
    view = copy.deepcopy(record)
    view["decisions"]["view"] = {"x_page": [1.0, 0.0], "y_page": [0.0, -1.0], "frame_rect": None,
                                 "source": "page_axes"}
    assert geometry_key(view) != base
    version = copy.deepcopy(record)
    version["geometry_version"] = 4
    assert geometry_key(version) != base
    digest = copy.deepcopy(record)
    digest["source_sha256"] = "e" * 64
    assert geometry_key(digest) != base


def test_geometry_key_notices_moved_geometry_and_edge_order_but_not_circle_order():
    record = make_record()
    base = geometry_key(record)
    moved = copy.deepcopy(record)
    moved["options"]["profiles"][0]["edges"][0]["start"] = [20.5, 20.0]
    assert geometry_key(moved) != base                            # aynı geometry_version içinde taşınan geometri
    reordered = copy.deepcopy(record)
    edges = reordered["options"]["profiles"][0]["edges"]
    reordered["options"]["profiles"][0]["edges"] = edges[1:] + edges[:1]
    assert geometry_key(reordered) != base                        # kenar sırası dokunulmaz, kimliğin parçası
    circles = copy.deepcopy(record)
    circles["options"]["circles"] = list(reversed(circles["options"]["circles"]))
    assert geometry_key(circles) == base


# --- freshness states -----------------------------------------------------

def test_states_start_missing_and_name_what_is_needed():
    rows = callout_states(make_record())
    assert [row["id"] for row in rows] == ["k1"]
    assert rows[0]["transcription"] == {"state": "missing", "revision": None, "reason": "needs_transcription"}
    assert rows[0]["parse"] == {"state": "missing", "reason": "needs_parse"}
    assert rows[0]["target"] == {"state": "missing", "reason": "needs_target"}


def test_states_are_current_when_the_whole_chain_matches():
    record = make_record(transcriptions=[transcription(revision=5)], parses=[parse()],
                         targets=[target(transcription_revision=5)])
    record["decisions"]["callout_targets"][0]["geometry_key"] = geometry_key(record)
    rows = callout_states(record)
    assert rows[0]["transcription"] == {"state": "current", "revision": 5, "reason": None}
    assert rows[0]["parse"] == {"state": "current", "reason": None}
    assert rows[0]["target"] == {"state": "current", "reason": None}


def test_an_edited_text_leaves_the_old_parse_and_target_stale():
    record = make_record(transcriptions=[transcription(revision=6)],
                         parses=[parse(transcription_revision=5)],
                         targets=[target(transcription_revision=5)])
    rows = callout_states(record)
    assert rows[0]["parse"] == {"state": "stale", "reason": "transcription_changed"}
    assert rows[0]["target"] == {"state": "stale", "reason": "transcription_changed"}


def test_a_new_parser_version_stales_parse_and_target():
    """Eski sürümle yazılmış okuma/hedef, beklenti ilerleyince bayatlar (v1 → güncel beklenti)."""
    record = make_record(transcriptions=[transcription(revision=5)],
                         parses=[parse(parser_version="callout-parser/1")],
                         targets=[target(transcription_revision=5, parser_version="callout-parser/1")])
    rows = callout_states(record)
    assert rows[0]["parse"] == {"state": "stale", "reason": "parser_version_changed"}
    assert rows[0]["target"] == {"state": "stale", "reason": "parser_version_changed"}


def test_a_changed_geometry_context_stales_the_target_only():
    record = make_record(transcriptions=[transcription(revision=5)], parses=[parse()],
                         targets=[target(transcription_revision=5)])
    record["decisions"]["callout_targets"][0]["geometry_key"] = geometry_key(record)
    assert callout_states(record)[0]["target"] == {"state": "current", "reason": None}
    record["decisions"]["profile_id"] = "outline_1"               # aynı geometry_version, başka kontur
    rows = callout_states(record)
    assert rows[0]["parse"]["state"] == "current"                 # metin değişmedi
    assert rows[0]["target"] == {"state": "stale", "reason": "geometry_changed"}


def test_a_target_without_its_parse_cannot_be_current():
    record = make_record(transcriptions=[transcription(revision=5)], targets=[target(transcription_revision=5)])
    record["decisions"]["callout_targets"][0]["geometry_key"] = geometry_key(record)
    rows = callout_states(record)
    assert rows[0]["parse"] == {"state": "missing", "reason": "needs_parse"}
    assert rows[0]["target"] == {"state": "stale", "reason": "parse_missing"}


def test_geometry_stale_makes_the_target_untrustworthy():
    record = make_record(transcriptions=[transcription(revision=5)], parses=[parse()],
                         targets=[target(transcription_revision=5)])
    record["decisions"]["callout_targets"][0]["geometry_key"] = geometry_key(record)
    record["geometry_stale"] = {"reason": "kaynak dosya okunamadı: fixture"}
    rows = callout_states(record)
    assert rows[0]["target"] == {"state": "stale", "reason": "source_unavailable"}
