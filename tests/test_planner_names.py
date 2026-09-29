"""The lossless name rewrite: a spelling the decoder could not constrain is mapped, not repaired.

Measured with `eval/name_probe.py`: this provider enforces a `pattern` on a string but ignores
`propertyNames` on an object, so an answer can still be keyed `pdf-0` or `hole_spacing_X`. Those tests
pin what the rewrite may do (rename a name everywhere it is used) and what it may never do (change a
value, a citation, a unit, a coordinate, or merge two of the answer's own names).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from drawingto3d.general import NAME_PATTERN, GeneralPlan, compile_general
from drawingto3d.planner import (
    NAME_ADAPTER,
    measurements_evidence,
    normalize_reply_names,
    propose_plan,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeChat:
    """A chat client that answers with whatever the test hands it."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None) -> str:
        self.prompts.append(prompt)
        if isinstance(stats, dict):
            stats.update({"done_reason": "stop"})
        return self.answer

    def settings_record(self) -> dict:
        return {"model": "test-model", "num_ctx": 4096, "num_predict": 256, "temperature": 0.0}


def plate_evidence() -> dict:
    return measurements_evidence(
        px_per_mm=7.82,
        frame={"width_px": 1654, "height_px": 1169},
        printed=[{"span_id": "pdf-0", "text": "100,00", "value": 100.0, "unit": "mm", "kind": "linear",
                  "count": 1},
                 {"span_id": "pdf-3", "text": "4 x Ø6,80", "value": 6.8, "unit": "mm", "kind": "diameter",
                  "count": 4}],
        claims=[{"span_id": "pdf-0", "form": "distance", "resolution": "confirmed", "between": ["h1", "h2"],
                 "measured_mm": 100.71}],
        geometry={"outline_mm": {"width_mm": 120.0, "height_mm": 80.0},
                  "circles": [{"id": "h1", "diameter_mm": 6.8, "centre_mm": [-50.0, -30.0]}]},
        notes=["pafta 1:1"],
    )


def answer_the_model_wrote() -> dict:
    """The recorded failure's shape: the sheet's span id used as a parameter name, one capital letter."""
    return {
        "version": 1,
        "unit": "mm",
        "parameters": {
            "pdf-0": {"unit": "mm", "source": "printed", "value": 100.0, "span_ids": ["pdf-0"],
                      "explanation": "iki delik merkezi arası"},
            "hole_Diameter": {"unit": "mm", "source": "printed", "value": 6.8, "span_ids": ["pdf-3"],
                              "explanation": "dört köşe deliği"},
            "corner_margin": {"unit": "mm", "source": "derived", "expr": "(hole_Diameter - pdf-0) / 2 + 50"},
        },
        "sketches": {
            "Plate-Profile": {"plane": "XY", "offset": "0", "entities": [
                {"type": "line", "start": ["-60", "-40"], "end": ["60", "-40"]},
                {"type": "line", "start": ["60", "-40"], "end": ["60", "40"]},
                {"type": "line", "start": ["60", "40"], "end": ["-60", "40"]},
                {"type": "line", "start": ["-60", "40"], "end": ["-60", "-40"]},
            ]},
            "Hole": {"plane": "XY", "offset": "-1", "entities": [
                {"type": "circle", "center": ["0", "0"], "radius": "hole_Diameter / 2"}]},
        },
        "operations": [
            {"op": "extrude", "id": "Outer", "output": "Body-1", "sketch": "Plate-Profile",
             "distance": "15"},
            {"op": "extrude", "id": "Pin", "output": "hole_tool", "sketch": "Hole",
             "distance": "15 + 2"},
            {"op": "cut", "id": "Holes", "target": "Body-1", "tool": "hole_tool", "output": "finished_part"},
        ],
        "result": "finished_part",
        "questions": [],
    }


def test_the_raw_answer_is_recorded_and_the_rewrite_is_named() -> None:
    answer = json.dumps(answer_the_model_wrote())
    candidate = propose_plan(FakeChat(answer), plate_evidence(), ref="sheet", sha256="a" * 64,
                             normalize_names=True)
    assert candidate.status == "proposed"
    assert candidate.plan is not None
    assert set(candidate.plan.parameters) == {"pdf_0", "hole_diameter", "corner_margin"}
    assert set(candidate.plan.sketches) == {"plate_profile", "hole"}
    # The raw answer stays verbatim beside the renames: what the model wrote, and what CAD read.
    assert candidate.answer == answer
    assert '"pdf-0"' in candidate.answer and '"hole_Diameter"' in candidate.answer
    assert {"from": "pdf-0", "to": "pdf_0"} in candidate.renames
    assert {"from": "hole_Diameter", "to": "hole_diameter"} in candidate.renames
    assert candidate.settings["name_normalization"] == NAME_ADAPTER


def test_a_citation_keeps_its_real_identity() -> None:
    """`span_ids` are the sheet's own identity: the rewrite must never touch them."""
    candidate = propose_plan(FakeChat(json.dumps(answer_the_model_wrote())), plate_evidence(),
                             ref="sheet", sha256="a" * 64, normalize_names=True)
    assert candidate.plan is not None
    assert candidate.plan.parameters["pdf_0"].span_ids == ["pdf-0"]
    assert candidate.citations["spans_cited"] == ["pdf-0", "pdf-3"]


def test_the_rewrite_is_off_by_default_and_the_answer_is_then_refused() -> None:
    candidate = propose_plan(FakeChat(json.dumps(answer_the_model_wrote())), plate_evidence(),
                             ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.plan is None
    # The record's first error names the illegal value, not only the pattern it broke.
    assert any("'Outer'" in error and NAME_PATTERN in error for error in candidate.errors)
    assert candidate.settings["name_normalization"] == "off"
    assert candidate.renames == []


def test_a_key_the_decoder_cannot_constrain_is_reported_by_the_plan_validator() -> None:
    """A bad key is not a field error, so it reaches the contract's own name check — not silence."""
    payload = {
        "version": 1, "unit": "mm",
        "parameters": {"pdf-0": {"unit": "mm", "source": "printed", "value": 100.0,
                                 "span_ids": ["pdf-0"], "explanation": "x"}},
        "sketches": {"s": {"plane": "XY", "offset": "0", "entities": [
            {"type": "circle", "center": ["0", "0"], "radius": "pdf-0 / 2"}]}},
        "operations": [{"op": "extrude", "id": "e", "output": "b", "sketch": "s", "distance": "pdf-0"}],
        "result": "b",
    }
    candidate = propose_plan(FakeChat(json.dumps(payload)), plate_evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("pdf-0" in error and "parametre adı" in error for error in candidate.errors)


def test_a_name_inside_an_expression_follows_its_key() -> None:
    payload, renames = normalize_reply_names(answer_the_model_wrote())
    assert payload["parameters"]["corner_margin"]["expr"] == "(hole_diameter - pdf_0) / 2 + 50"
    assert payload["sketches"]["plate_profile"]["entities"] == answer_the_model_wrote()["sketches"][
        "Plate-Profile"]["entities"]
    assert payload["sketches"]["hole"]["entities"][0]["radius"] == "hole_diameter / 2"
    assert payload["operations"][2] == {"op": "cut", "id": "holes", "target": "body_1",
                                        "tool": "hole_tool", "output": "finished_part"}
    assert payload["result"] == "finished_part"
    assert [item["from"] for item in renames] == ["pdf-0", "hole_Diameter", "Plate-Profile", "Hole",
                                                  "Outer", "Body-1", "Pin", "Holes"]


def test_a_function_call_in_an_expression_is_not_a_parameter() -> None:
    payload = {"parameters": {
        "Slack-X": {"unit": "mm", "source": "derived", "expr": "max(Hole-A, 2 * sqrt(Hole-A))"},
        "Hole-A": {"unit": "mm", "source": "assumed", "value": 3.0, "explanation": "x"}},
        "sketches": {"S": {"plane": "XY", "offset": "0", "entities": [
            {"type": "circle", "center": ["0", "0"], "radius": "Hole-A"}]}},
        "operations": [{"op": "extrude", "id": "e", "output": "b", "sketch": "S",
                        "distance": "Slack-X"}],
        "result": "b"}
    out, _renames = normalize_reply_names(payload)
    assert out["parameters"]["slack_x"]["expr"] == "max(hole_a, 2 * sqrt(hole_a))"


def test_two_names_the_answer_distinguishes_stay_two_names() -> None:
    """A rewrite may not merge: `hole_1` is legal as written, so the illegal one takes the suffix."""
    payload = {"parameters": {"hole_1": {"unit": "mm", "source": "assumed", "value": 1.0, "explanation": "x"},
                              "hole-1": {"unit": "mm", "source": "assumed", "value": 2.0, "explanation": "y"}},
               "sketches": {"s": {"plane": "XY", "offset": "0", "entities": [
                   {"type": "circle", "center": ["0", "0"], "radius": "hole-1"}]}},
               "operations": [{"op": "extrude", "id": "e", "output": "b", "sketch": "s",
                               "distance": "hole-1"}],
               "result": "b"}
    out, renames = normalize_reply_names(payload)
    assert set(out["parameters"]) == {"hole_1", "hole_1_2"}
    assert out["parameters"]["hole_1"]["value"] == 1.0 and out["parameters"]["hole_1_2"]["value"] == 2.0
    assert out["operations"][0]["distance"] == "hole_1_2"
    assert {"from": "hole-1", "to": "hole_1_2"} in renames


def test_a_legal_answer_is_returned_unchanged_and_rewrites_nothing() -> None:
    plan = json.loads((ROOT / "eval/plans/bracket_linear_pattern.json").read_text())
    plan = {key: value for key, value in plan.items() if key != "source"}
    out, renames = normalize_reply_names(plan)
    assert renames == []
    assert json.dumps(out, sort_keys=True) == json.dumps(plan, sort_keys=True)


def test_a_fully_mangled_plan_round_trips_into_the_compiler() -> None:
    """Every name an answer can carry, illegal at once: the geometry has to survive the rewrite."""
    plan = json.loads((ROOT / "eval/plans/bracket_linear_pattern.json").read_text())
    names = list(plan["parameters"]) + list(plan["sketches"]) + [operation["output"]
                                                                 for operation in plan["operations"]]
    names += [plan["result"]] + [operation["id"] for operation in plan["operations"]]
    mangled = {name: name.upper() for name in dict.fromkeys(names) if name.islower()}

    def rewrite(text):
        for original, bad in sorted(mangled.items(), key=lambda item: -len(item[0])):
            text = text.replace(original, bad)
        return text

    prose = ("assumptions", "questions", "explanation")

    def walk(value, key=None):
        # Prose is not an identifier space: a sentence may name a parameter, and the rewrite must
        # leave that sentence alone.
        if key in prose:
            return value
        if isinstance(value, str):
            return rewrite(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {rewrite(name) if name in mangled else name: walk(item, name)
                    for name, item in value.items()}
        return value

    payload = walk({key: value for key, value in plan.items() if key != "source"})
    assert any(not name.islower() for name in payload["parameters"])
    out, renames = normalize_reply_names(payload)
    assert len(renames) == len(mangled)
    # Names back, everything else untouched — and it still compiles to the same program.
    assert json.dumps(out, sort_keys=True) == json.dumps(
        {key: value for key, value in plan.items() if key != "source"}, sort_keys=True)
    built = GeneralPlan.model_validate({**out, "source": {"kind": "synthetic", "ref": "x"}})
    original = GeneralPlan.model_validate(plan)
    assert compile_general(built) == compile_general(original)


def test_the_split_interface_uses_the_same_adapter() -> None:
    from drawingto3d.planner import propose_plan_split

    answers = answer_the_model_wrote()
    sketches = answers["sketches"]
    merged = {
        "parameters": json.dumps({"unit": "mm", "parameters": answers["parameters"]}),
        "profile 1/2": json.dumps({"sketches": {"Plate-Profile": sketches["Plate-Profile"]}}),
        "profile 2/2": json.dumps({"sketches": {"Hole": sketches["Hole"]}}),
        "operations": json.dumps({"operations": answers["operations"], "result": answers["result"]}),
    }

    class StepChat(FakeChat):
        def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None):
            call = str((response_format or {}).get("title", "")).rsplit(":", 1)[-1].strip()
            self.prompts.append(prompt)
            if isinstance(stats, dict):
                stats.update({"done_reason": "stop"})
            return merged[call]

    candidate = propose_plan_split(StepChat(""), plate_evidence(), ref="sheet", sha256="a" * 64,
                                   normalize_names=True)
    assert candidate.status == "proposed"
    assert candidate.plan is not None
    assert {"from": "Plate-Profile", "to": "plate_profile"} in candidate.renames
    assert candidate.settings["name_normalization"] == NAME_ADAPTER


@pytest.mark.parametrize("payload,expected", [
    ({"result": ""}, {}),
    ({"parameters": {}, "sketches": {}, "operations": [], "result": ""}, {}),
])
def test_an_empty_answer_is_not_given_names(payload, expected) -> None:
    out, renames = normalize_reply_names(payload)
    assert renames == []
    assert {key: value for key, value in out.items() if value not in ([], "", {})} == expected
