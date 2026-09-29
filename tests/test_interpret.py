"""One measurement binds to the drawing's own ids; a binding that cannot be resolved stays a question."""
import json

import pytest

from drawingto3d.interpret import (
    INTERPRETATION_VERSION,
    REVIEW_VERSION,
    corrupt_proposal,
    geometry_ids,
    interpret_measurement,
    interpret_prompt,
    judge_interpretation,
    measurement_context,
    reading_proposal,
    reply_schema,
    review_injects_a_defect,
)
from test_planner import FakeChat


@pytest.fixture
def evidence():
    return {
        "printed": [
            {"span_id": "p1", "value": 100.0, "unit": "mm", "text": "100,00", "kind": "linear"},
            {"span_id": "p2", "value": 6.8, "unit": "mm", "text": "4 x Ø6,80", "kind": "linear", "count": 4},
        ],
        "claims": [
            {"span_id": "p1", "form": "distance", "resolution": "confirmed", "printed_mm": 100.0,
             "anchors": [{"geometry_id": "g9", "kind": "circle-centre", "point_mm": [-50.0, -30.0]},
                         {"geometry_id": "g11", "kind": "circle-centre", "point_mm": [50.0, -30.0]}]},
            {"span_id": "p2", "form": "diameter", "resolution": "confirmed", "printed_mm": 6.8,
             "anchors": [{"geometry_id": "g12", "kind": "circle-centre", "point_mm": [-50.0, 30.0]}],
             "matched_geometry": ["g9", "g12", "g10", "g11"]},
        ],
        "geometry": {"units": "mm",
                     "circles": [{"id": "g9", "diameter_mm": 6.85, "centre_mm": [-50.35, -30.21]},
                                 {"id": "g11", "diameter_mm": 6.84, "centre_mm": [50.36, -30.21]}],
                     "outline_mm": {"width_mm": 120.87, "height_mm": 80.56}},
        "notes": ["sayfa çerçevesi atlandı (1 döngü)"],
    }


def contract(span_id="p1", **fields):
    payload = {"span_id": span_id, "kind": "distance",
               "between": ["g9", "g11"], "matched": [], "unresolved": False,
               "question": "", "reason": "two hole centres"}
    payload.update(fields)
    return payload


def test_offered_ids_are_only_the_ones_the_reading_measured(evidence):
    ids = geometry_ids(evidence)
    assert sorted(ids) == ["g10", "g11", "g12", "g9"]
    assert ids["g9"]["kinds"] == ["circle-centre", "circle"] and ids["g9"]["diameter_mm"] == 6.85
    context = measurement_context(evidence, "p1")
    assert context["allowed_ids"] == ["g10", "g11", "g12", "g9"]
    schema = reply_schema(context)
    assert schema["properties"]["span_id"]["enum"] == ["p1"]
    # A distance may only be measured between a pair the reading itself measured.
    assert schema["properties"]["between"]["items"]["enum"] == context["candidate_pair_ids"] == ["g11", "g9"]
    assert schema["properties"]["matched"]["items"]["enum"] == context["allowed_ids"]
    assert "$defs" not in json.dumps(schema) or "value" not in json.dumps(schema["$defs"])


def test_prompt_asks_for_a_binding_and_forbids_numbers(evidence):
    prompt = interpret_prompt(measurement_context(evidence, "p1"))
    assert "OFF" not in prompt
    assert INTERPRETATION_VERSION.startswith("single-measurement")
    assert "Do not restate its value and do not compute or derive any number" in prompt
    assert "'p1'" in prompt and "g9" in prompt
    assert "7.82" not in prompt and "secret.step" not in prompt


def test_a_distance_binds_two_ids_and_is_accepted(evidence):
    result = judge_interpretation(contract(), measurement_context(evidence, "p1"))
    assert result.status == "needs_review" and not result.errors
    assert result.interpretation.between == ["g9", "g11"]
    assert result.checks["ids_are_measured_geometry"] and result.checks["binding_claimed"]
    assert result.checks["reading_binding_confirmed"] is True
    assert result.axis == "horizontal" and result.checks["axis_derived_from_the_pair"] == "horizontal"
    assert result.checks["values_untouched"] is True


@pytest.mark.parametrize("mutation, message", [
    ({"span_id": "p2"}, "yanlış kaynak kimliği"),
    ({"between": ["g9", "g99"]}, "ölçüde olmayan geometri kimliği"),
    ({"between": ["g9", "g9"]}, "iki kez bağlanmış"),
    ({"between": ["g9"]}, "iki geometri kimliği gerekli"),
    ({"axis": "horizontal"}, "Extra inputs"),
    ({"between": [], "matched": ["g9"]}, "eşleşen geometri değil"),
    ({"value": 100.0}, "Extra inputs"),
])
def test_a_binding_cannot_bend_the_contract(evidence, mutation, message):
    result = judge_interpretation(contract(**mutation), measurement_context(evidence, "p1"))
    assert result.status == "invalid", mutation
    assert any(message in error for error in result.errors), (mutation, result.errors)


def test_a_diameter_matches_the_geometry_it_sizes(evidence):
    payload = contract("p2", kind="diameter", between=[], matched=["g9", "g12", "g10", "g11"])
    result = judge_interpretation(payload, measurement_context(evidence, "p2"))
    assert result.status == "needs_review" and not result.errors
    assert result.checks["reading_binding_confirmed"] is True  # matched geometry confirmed


def test_an_unsolvable_binding_stays_a_question(evidence):
    payload = contract(kind="unclear", between=[], matched=[], unresolved=True,
                       question="which two edges carry this number?")
    result = judge_interpretation(payload, measurement_context(evidence, "p1"))
    assert result.status == "needs_input" and not result.errors
    assert result.questions == ["which two edges carry this number?"]
    assert result.checks["binding_claimed"] is False


@pytest.mark.parametrize("mutation", [
    {"unresolved": True, "question": "", "between": [], "matched": [], "kind": "unclear"},
    {"unresolved": True, "kind": "unclear"},
    {"unresolved": True, "question": "hangi iki kenar?", "kind": "distance", "between": ["g9", "g11"]},
    {"kind": "unclear", "between": [], "matched": []},
])
def test_an_unresolved_answer_cannot_also_claim_a_binding(evidence, mutation):
    result = judge_interpretation(contract(**mutation), measurement_context(evidence, "p1"))
    assert result.status == "invalid", mutation
    assert result.errors


def test_the_request_is_persisted_before_the_model_is_called(evidence):
    chat = FakeChat(json.dumps(contract()))
    seen = []
    result = interpret_measurement(chat, evidence, "p1", on_request=seen.append)
    assert len(seen) == 1 and seen[0]["span_id"] == "p1"
    assert seen[0]["request"]["prompt"] == chat.prompts[0]
    assert seen[0]["context"]["allowed_ids"] == ["g10", "g11", "g12", "g9"]
    assert result.status == "needs_review" and result.seconds >= 0
    assert result.request["offered_ids"] == ["g10", "g11", "g12", "g9"]


def test_an_unavailable_model_leaves_the_measurement_untouched(evidence):
    from drawingto3d.errors import UnavailableModel

    result = interpret_measurement(FakeChat(UnavailableModel("yerel model yanıt vermiyor")), evidence, "p1")
    assert result.status == "unavailable" and result.interpretation is None
    assert result.errors == ["yerel model yanıt vermiyor"]
    assert all(row["value"] == row["value"] for row in evidence["printed"])  # values not rewritten
    assert measurement_context(evidence, "p1")["measurement"]["value"] == 100.0


def test_a_number_in_the_explanation_is_a_warning_not_a_lost_binding(evidence):
    """v1 threw the whole answer away over a quoted value, hiding the binding it protects."""
    from drawingto3d.interpret import JUDGE_VERSION

    payload = contract(reason="the gap is 100 mm wide")
    result = judge_interpretation(payload, measurement_context(evidence, "p1"))
    assert result.status == "needs_review" and not result.errors
    assert result.warnings == ["gerekçe veya soruda kimlik dışı sayı var"]
    assert result.interpretation.between == ["g9", "g11"]
    assert result.checks["no_number_written"] is False
    assert result.checks["binding_claimed"] is True
    assert result.axis == "horizontal" and result.checks["axis_derived_from_the_pair"] == "horizontal"
    assert JUDGE_VERSION == "interpretation-contract-v5-size-agreement"
    # A number inside an id is not a violation, and the prompt still forbids derived numbers.
    clean = judge_interpretation(contract(reason="between g9 and g11"), measurement_context(evidence, "p1"))
    assert clean.warnings == [] and clean.checks["no_number_written"] is True
    from drawingto3d.interpret import interpret_prompt

    assert "do not compute or derive any number" in interpret_prompt(measurement_context(evidence, "p1"))


def test_the_axis_is_derived_from_the_chosen_pair_not_asked_for(evidence):
    """v2 asked for the axis and the answer's word contradicted its own pair; v3 removes the word."""
    context = measurement_context(evidence, "p1")
    assert "axis" not in reply_schema(context)["properties"]
    assert "do not state an axis" in interpret_prompt(context)
    # With the pair standing vertically on the sheet, the derived axis is vertical — no word asked.
    vertical = {**evidence, "claims": [dict(claim) for claim in evidence["claims"]]}
    vertical["claims"][0] = {**vertical["claims"][0], "anchors": [
        {"geometry_id": "g9", "kind": "circle-centre", "point_mm": [-50.0, -30.0]},
        {"geometry_id": "g12", "kind": "circle-centre", "point_mm": [-50.0, 30.0]}]}
    result = judge_interpretation(contract(between=["g9", "g12"]), measurement_context(vertical, "p1"))
    assert result.status == "needs_review" and result.axis == "vertical"
    assert result.checks["axis_derived_from_the_pair"] == "vertical"
    diameter = judge_interpretation(contract("p2", kind="diameter", between=[],
                                             matched=["g9", "g12", "g10", "g11"]),
                                    measurement_context(evidence, "p2"))
    assert diameter.axis == "none" and diameter.status == "needs_review"


def test_the_choice_is_narrowed_to_the_pairs_the_reading_measured():
    """The menu is the reading's own pairs: its anchors plus the alternatives it recorded."""
    from drawingto3d.interpret import candidate_pairs

    sheet = {
        "printed": [{"span_id": "s1", "value": 100.0, "unit": "mm", "text": "100,00", "kind": "linear"}],
        "claims": [{"span_id": "s1", "form": "distance", "anchors": [
            {"geometry_id": "g9", "kind": "circle-centre", "point_mm": [-50.0, -30.0]},
            {"geometry_id": "g11", "kind": "circle-centre", "point_mm": [50.0, -30.0]}],
            "notes": ["Aynı ölçüyü veren başka aday çiftleri de var: g9/g10, g12/g11, g12/g10."]}],
        "geometry": {"circles": [
            {"id": "g9", "centre_mm": [-50.0, -30.0]}, {"id": "g10", "centre_mm": [50.0, 30.0]},
            {"id": "g11", "centre_mm": [50.0, -30.0]}, {"id": "g12", "centre_mm": [-50.0, 30.0]}]},
    }
    assert candidate_pairs(sheet, "s1") == [["g9", "g11"], ["g9", "g10"], ["g12", "g11"], ["g12", "g10"]]
    context = measurement_context(sheet, "s1")
    assert context["candidate_pair_ids"] == ["g10", "g11", "g12", "g9"]
    assert reply_schema(context)["properties"]["between"]["items"]["enum"] == ["g10", "g11", "g12", "g9"]
    # A pair outside the measured candidates is refused; one of them is accepted and its axis derived.
    outside = judge_interpretation({"span_id": "s1", "kind": "distance", "between": ["g11", "g10"],
                                    "matched": [], "unresolved": False, "question": "", "reason": "r"}, context)
    assert outside.status == "invalid"
    assert any("adaylar arasında değil" in error for error in outside.errors), outside.errors
    inside = judge_interpretation({"span_id": "s1", "kind": "distance", "between": ["g9", "g10"],
                                   "matched": [], "unresolved": False, "question": "", "reason": "r"}, context)
    assert inside.status == "needs_review" and inside.axis == "horizontal"
    assert inside.checks["pair_is_a_measured_candidate"] is True
    # An id the reading named but never gave a position cannot form a checkable pair.
    no_point = {**sheet, "geometry": {"circles": [circle for circle in sheet["geometry"]["circles"]
                                                 if circle["id"] != "g10"]}}
    assert candidate_pairs(no_point, "s1") == [["g9", "g11"], ["g12", "g11"]]


def test_the_review_round_shows_the_reading_s_proposal_and_injects_a_defect(evidence):
    assert REVIEW_VERSION == "reading-review-v1"
    context = measurement_context(evidence, "p1")
    proposal = reading_proposal(context)
    assert proposal == {"kind": "distance", "between": ["g11", "g9"], "matched": []}
    # The prompt without a proposal is unchanged; with one it carries the proposal verbatim.
    assert "The reading proposes:" not in interpret_prompt(context)
    prompt = interpret_prompt(context, proposal)
    assert "The reading proposes:" in prompt
    assert json.dumps(proposal, ensure_ascii=False, separators=(",", ":")) in prompt
    assert "review request, not an authority" in prompt


def test_the_injected_defect_is_deterministic_inside_the_measurements_own_ids(evidence):
    context = measurement_context(evidence, "p1")
    proposal = reading_proposal(context)
    offered = context["allowed_ids"]
    corrupted = corrupt_proposal(proposal, offered, "p1")
    assert corrupted == corrupt_proposal(proposal, offered, "p1")   # same id, same defect
    assert corrupted != proposal
    assert corrupted["between"] != proposal["between"]
    assert set(corrupted["between"]) <= set(offered)
    assert corrupted["kind"] == proposal["kind"]
    # A set is corrupted by a wrong member, a reduced set or a dropped member — never left intact.
    holes = {"kind": "diameter", "between": [], "matched": ["g10", "g11", "g12", "g9"]}
    bad = corrupt_proposal(holes, offered, "p2")
    assert sorted(bad["matched"]) != sorted(holes["matched"])
    assert set(bad["matched"]) <= set(offered) and bad["matched"]
    # Nothing to corrupt: an unresolved proposal and an unknown kind are left alone.
    assert corrupt_proposal({"kind": "unclear", "between": [], "matched": []}, offered, "x") is None
    assert corrupt_proposal({"kind": "distance", "between": ["g9"], "matched": []}, offered, "x") is None


def test_half_the_measurements_are_chosen_for_a_defect_by_source_id_alone():
    ids = [f"pdf-{index}" for index in range(200)]
    chosen = [span for span in ids if review_injects_a_defect(span)]
    assert 60 <= len(chosen) <= 140                      # about half, never all or none
    assert chosen == [span for span in ids if review_injects_a_defect(span)]   # stable


def test_the_prompt_and_schema_name_the_list_this_measurements_form_requires(evidence):
    """Blind rounds answered a diameter callout with a pair in `between`; the field is now stated.

    The measurement's own form comes from the reading, so this says which list the contract will judge —
    not which ids belong in it.
    """
    from drawingto3d.interpret import required_field
    distance = measurement_context(evidence, "p1")
    diameter = measurement_context(evidence, "p2")
    assert required_field(distance) == "between" and required_field(diameter) == "matched"

    distance_schema = reply_schema(distance)["properties"]
    assert distance_schema["between"]["minItems"] == 2 and distance_schema["between"]["maxItems"] == 2
    assert distance_schema["matched"]["maxItems"] == 0
    diameter_schema = reply_schema(diameter)["properties"]
    assert diameter_schema["matched"]["minItems"] == 1 and diameter_schema["between"]["maxItems"] == 0

    assert "put the TWO ids in between" in interpret_prompt(distance)
    assert "put the ids in matched" in interpret_prompt(diameter)
    assert "This measurement's own form is diameter" in interpret_prompt(diameter)


def test_a_measurement_the_reading_left_open_states_no_list(evidence):
    """With no form there is nothing to require: the generic wording stays and both lists remain open."""
    from drawingto3d.interpret import required_field
    open_evidence = json.loads(json.dumps(evidence))
    open_evidence["claims"][0]["form"] = "none"
    context = measurement_context(open_evidence, "p1")
    assert required_field(context) is None
    schema = reply_schema(context)["properties"]
    assert "maxItems" not in schema["matched"] or schema["matched"]["maxItems"] != 0
    prompt = interpret_prompt(context)
    assert "put the TWO ids in between" not in prompt and "put the ids in matched" not in prompt


def test_a_count_measurement_says_it_asks_for_the_count(evidence):
    """"4 x Ø6,80" is printed once and asked twice; the text is identical, so the request must say which.

    The catalog's own quantity decides it — the request still names no geometry.
    """
    counted = measurement_context(evidence, "p2", quantity="count")
    sized = measurement_context(evidence, "p2", quantity="dimension")
    assert counted["measurement"]["quantity"] == "count"
    assert "CALL COUNT" in interpret_prompt(counted)
    assert "set kind to count" in interpret_prompt(counted)
    assert "CALL COUNT" not in interpret_prompt(sized)
    # The ids the answer may name are untouched by this: only the question is stated.
    assert counted["allowed_ids"] == sized["allowed_ids"]
    assert reply_schema(counted)["properties"]["matched"]["minItems"] == 1


def test_the_offered_ids_carry_the_size_the_reading_measured():
    """Two ids can share a centre (a boss and the bore inside it), so the size is what tells them apart.

    Measured need: on the third sheet the diameter menu offered g65 and g68 with the same kind and the
    same point, and the model answered both; the reading had already measured 51,33 mm for one and
    30,73 mm for the other. The size offered is the reading's own measurement (`drawn_mm`, from the
    geometry's radius), never the printed value the answer must not repeat.
    """
    from drawingto3d.interpret import measurement_context

    evidence = {
        "printed": [{"span_id": "pdf-19", "value": 30.0, "unit": "mm", "text": "30", "kind": "diameter"}],
        "claims": [
            {"span_id": "pdf-19", "form": "diameter", "drawn_mm": 30.73, "matched_geometry": ["g68"],
             "anchors": [{"geometry_id": "g68", "kind": "arc-centre", "point_mm": [11.27, 180.71]}]},
            {"span_id": "pdf-21", "form": "diameter", "drawn_mm": 51.33, "matched_geometry": ["g65"],
             "anchors": [{"geometry_id": "g65", "kind": "arc-centre", "point_mm": [11.27, 180.71]}]},
            {"span_id": "pdf-9", "form": "distance", "drawn_mm": 80.0,
             "anchors": [{"geometry_id": "g123", "kind": "line-end", "point_mm": [37.08, -41.1]}]},
        ],
    }
    context = measurement_context(evidence, "pdf-19")
    offered = context["offered_geometry_ids"]
    assert offered["g68"]["measured_diameter_mm"] == 30.73
    assert offered["g65"]["measured_diameter_mm"] == 51.33
    assert "measured_diameter_mm" not in offered["g123"]          # nobody sized it
    assert "measured_diameter_mm" in interpret_prompt(context)     # and the request says what it is


def test_named_ids_that_contradict_the_printed_size_are_flagged(evidence):
    """A diameter answered with ids the reading measured at other sizes must not read as a pass.

    Measured need: on the third sheet the Ø25 callout was answered with g134 (measured 41,08 mm) and g65
    (51,33 mm) while the request published g122 at 25,70 mm; the old pair check was vacuously true there,
    because a diameter request offers no candidate pairs. Without a label, the sizes the reading itself
    published are enough to say the binding does not fit the number.
    """
    context = measurement_context(evidence, "p2")   # printed 6,80 mm, g9/g11 measured 6,85/6,84
    agreeing = judge_interpretation(
        {"span_id": "p2", "kind": "diameter", "between": [], "matched": ["g9", "g11"],
         "unresolved": False, "question": "", "reason": "the two holes the callout names"}, context)
    assert agreeing.checks["named_ids_do_not_contradict_the_printed_size"] is True

    contradicting = judge_interpretation(
        {"span_id": "p2", "kind": "diameter", "between": [], "matched": ["g10", "g12"],
         "unresolved": False, "question": "", "reason": "the ids the model preferred"}, context)
    assert contradicting.checks["named_ids_do_not_contradict_the_printed_size"] is None  # neither is sized

    mixed = judge_interpretation(
        {"span_id": "p2", "kind": "diameter", "between": [], "matched": ["g9", "g10"],
         "unresolved": False, "question": "", "reason": "a sized id and an unsized one"}, context)
    assert mixed.checks["named_ids_do_not_contradict_the_printed_size"] is True  # judges what it can

    wrong_size = judge_interpretation(
        {"span_id": "p1", "kind": "diameter", "between": [], "matched": ["g9", "g11"],
         "unresolved": False, "question": "", "reason": "a 100 mm callout answered with 6,85 mm holes"},
        measurement_context(evidence, "p1"))
    assert wrong_size.checks["named_ids_do_not_contradict_the_printed_size"] is False

    distance = judge_interpretation(
        {"span_id": "p1", "kind": "distance", "between": ["g9", "g11"], "matched": [],
         "unresolved": False, "question": "", "reason": "two hole centres"},
        measurement_context(evidence, "p1"))
    assert distance.checks["named_ids_do_not_contradict_the_printed_size"] is None  # not a size question
