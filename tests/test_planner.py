"""The planning layer: a model's answer is a plan candidate, judged by the schema and the compiler.

Every test here builds the answer it needs instead of asking a model, so the suite says what the code
does with an answer, not whether a model is installed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from drawingto3d.errors import UnavailableModel
from drawingto3d.general import GeneralPlan, compile_general
from drawingto3d.llama import ChatSettings, ModelInfo, find_model
from drawingto3d.planner import (
    _RULE_CITE_SPANS,
    _RULE_NO_INVENTED_NUMBERS,
    _RULE_SIMPLEST,
    _check_citations,
    _prints_value,
    PROMPT_VERSION,
    PROMPT_VERSION_SPLIT,
    REPLY_SCHEMA_VERSION,
    REPLY_SCHEMA_VERSION_SPLIT,
    SCHEMA_VERSION,
    SPLIT_STEPS,
    measurements_evidence,
    plan_prompt,
    plan_reply_schema,
    propose_plan,
    propose_plan_split,
    step_prompt,
    step_reply_schema,
)


class FakeChat:
    """A chat client that answers with whatever the test hands it."""

    def __init__(self, answer: str | Exception, model: str = "test-model",
                 done_reason: str | None = "stop") -> None:
        self.answer = answer
        self.done_reason = done_reason
        self.settings = ChatSettings(model=model, num_ctx=4096, temperature=0.0, num_predict=256)
        self.prompts: list[str] = []
        self.formats: list[object] = []

    def complete(self, prompt: str, image_png=None, num_predict=None, response_format=None, stats=None) -> str:
        self.prompts.append(prompt)
        self.formats.append(response_format)
        if isinstance(stats, dict):
            stats.update({"done_reason": self.done_reason, "eval_count": 10})
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def settings_record(self) -> dict:
        return self.settings.as_dict()


def evidence() -> dict:
    return measurements_evidence(
        px_per_mm=7.82,
        frame={"width_px": 1654, "height_px": 1169},
        printed=[
            {"span_id": "d1", "text": "100,00", "value": 100.0, "unit": "mm", "kind": "linear", "count": 1},
            {"span_id": "d4", "text": "4 x Ø6,80", "value": 6.8, "unit": "mm", "kind": "diameter", "count": 4},
        ],
        claims=[{"span_id": "d1", "form": "distance", "resolution": "confirmed", "between": ["h1", "h2"],
                 "measured_mm": 100.71}],
        # One closed outline and one closed circle: two profiles the reading measured, so the profile
        # step has two calls to make.
        geometry={"outline_mm": {"width_mm": 120.0, "height_mm": 80.0},
                  "circles": [{"id": "h1", "diameter_mm": 6.8, "centre_mm": [-50.0, -30.0]}]},
        notes=["pafta 1:1"],
    )


PLATE_ANSWER = json.dumps({
    "version": 1,
    "unit": "mm",
    "parameters": {
        "hole_spacing": {"unit": "mm", "source": "printed", "value": 100.0, "span_ids": ["d1"],
                         "explanation": "iki delik merkezi arası"},
        "hole_diameter": {"unit": "mm", "source": "printed", "value": 6.8, "span_ids": ["d4"],
                          "explanation": "dört köşe deliği"},
        "thickness": {"unit": "mm", "source": "assumed", "value": 15.0,
                      "explanation": "kesitte ölçülen kalınlık; paftada ayrıca yazmıyor"},
    },
    "sketches": {
        "plate": {"plane": "XY", "offset": "0", "entities": [
            {"type": "line", "start": ["-60", "-40"], "end": ["60", "-40"]},
            {"type": "line", "start": ["60", "-40"], "end": ["60", "40"]},
            {"type": "line", "start": ["60", "40"], "end": ["-60", "40"]},
            {"type": "line", "start": ["-60", "40"], "end": ["-60", "-40"]},
        ]},
        "hole": {"plane": "XY", "offset": "-1", "entities": [
            {"type": "circle", "center": ["0", "0"], "radius": "hole_diameter / 2"}]},
    },
    "operations": [
        {"op": "extrude", "id": "outer", "output": "body", "sketch": "plate", "distance": "thickness"},
        {"op": "extrude", "id": "pin", "output": "hole_tool", "sketch": "hole", "distance": "thickness + 2"},
        {"op": "repeat", "id": "grid", "input": "hole_tool", "output": "hole_tools",
         "linear": {"x_pitch": "hole_spacing", "x_count": 2, "y_pitch": "60", "y_count": 2}},
        {"op": "cut", "id": "holes", "target": "body", "tool": "hole_tools", "output": "finished"},
    ],
    "result": "finished",
    "assumptions": ["Kalınlık kesitten alındı."],
    "questions": ["Cep derinliği paftada okunamadı."],
})


def test_a_valid_answer_becomes_a_plan_and_is_cited() -> None:
    candidate = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "proposed"
    assert candidate.plan is not None
    assert candidate.prompt_version == PROMPT_VERSION
    assert candidate.citations["spans_cited"] == ["d1", "d4"]
    assert candidate.questions == ["Cep derinliği paftada okunamadı."]
    assert "solid = finished" in compile_general(candidate.plan)


def test_the_source_identity_is_the_harness_not_the_model() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["source"] = {"kind": "drawing", "ref": "part-2.STEP", "sha256": "b" * 64}
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "proposed"
    assert candidate.plan is not None
    assert candidate.plan.source.ref == "sheet"
    assert candidate.plan.source.sha256 == "a" * 64
    assert candidate.overrides == ["model kaynağı (source) verdi; koşunun kaynağı onun yerine geçti"]
    assert candidate.errors == []


def test_a_citation_the_sheet_does_not_carry_is_refused() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["parameters"]["hole_diameter"]["span_ids"] = ["d9"]
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("d9" in error for error in candidate.errors)
    assert candidate.plan is None


def test_an_assumption_without_a_reason_is_refused() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["parameters"]["thickness"]["explanation"] = ""
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("thickness" in error for error in candidate.errors)


def test_prose_without_an_object_is_an_invalid_candidate() -> None:
    candidate = propose_plan(FakeChat("The part looks like a plate."), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.errors == ["yanıtta JSON nesnesi yok"]
    assert candidate.plan is None


def test_a_fenced_object_is_still_read() -> None:
    answer = "```json\n" + PLATE_ANSWER + "\n```"
    candidate = propose_plan(FakeChat(answer), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "proposed"


def test_a_schema_violation_keeps_the_reason() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["operations"][3]["tool"] = "nowhere"
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("nowhere" in error for error in candidate.errors)


def test_an_open_profile_never_reaches_a_plan() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["sketches"]["plate"]["entities"] = payload["sketches"]["plate"]["entities"][:3]
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.plan is None


def test_a_model_that_does_not_answer_is_recorded_as_unavailable() -> None:
    candidate = propose_plan(FakeChat(UnavailableModel("yerel model yanıt vermiyor")), evidence(),
                             ref="sheet", sha256="a" * 64)
    assert candidate.status == "unavailable"
    assert candidate.model_dump(mode="json")["plan"] is None
    assert candidate.errors and "model yanıt vermedi" in candidate.errors[0]
    assert candidate.settings["model"] == "test-model"


def test_the_prompt_carries_no_file_name_and_no_reference_plan() -> None:
    prompt = plan_prompt(evidence(), notes=["pafta 1:1"])
    assert "d1" in prompt and "100" in prompt
    assert ".STEP" not in prompt and ".pdf" not in prompt and "my_part" not in prompt
    assert "result" in prompt and "operations" in prompt


def test_real_verified_fixture_does_not_leak_reference_metadata() -> None:
    path = Path(__file__).resolve().parents[1] / "eval/relations/plate-pocket-1.json"
    verified = json.loads(path.read_text())
    assert ".STEP" in verified["verified_against"]
    prompt = plan_prompt(verified)
    assert verified["verified_against"] not in prompt
    assert verified["verified_by"] not in prompt
    assert ".STEP" not in prompt
    assert "d1" in prompt and "100.0" in prompt


def test_the_record_says_which_model_and_settings_answered() -> None:
    candidate = propose_plan(FakeChat(PLATE_ANSWER, model="qwen2.5vl:3b"), evidence(),
                             ref="sheet", sha256="a" * 64,
                             model_info={"name": "qwen2.5vl:3b", "quantization": "Q4_K_M"})
    record = candidate.as_record()
    assert record["settings"]["model"] == "qwen2.5vl:3b"
    assert record["model_info"]["quantization"] == "Q4_K_M"
    assert record["plan"]["parameters"] == ["hole_spacing", "hole_diameter", "thickness"]
    assert record["status"] == "proposed"


def test_find_model_accepts_exact_tags_and_refuses_an_ambiguous_prefix() -> None:
    models = [ModelInfo(name="qwen2.5vl:3b"), ModelInfo(name="qwen2.5vl:7b"), ModelInfo(name="llama3.2:3b")]
    assert find_model(models, "qwen2.5vl:3b").name == "qwen2.5vl:3b"
    with pytest.raises(UnavailableModel):
        find_model(models, "qwen2.5vl")
    with pytest.raises(UnavailableModel) as error:
        find_model(models, "qwen3-vl:8b-instruct")
    assert "kurulu olanlar" in str(error.value)


def test_settings_record_is_the_run_record_fields() -> None:
    settings = ChatSettings(model="qwen2.5vl:3b", num_ctx=8192, temperature=0.0, num_predict=2048)
    record = settings.as_dict()
    assert record["num_ctx"] == 8192 and record["num_predict"] == 2048
    assert record["response_format"] == "text"
    assert record["images_layout"] == "single_message", "çerçeveleme de çağrının bir ayarıdır"
    assert set(record) == {"model", "num_ctx", "temperature", "num_predict", "keep_alive", "timeout_s",
                           "image_max_side", "images_per_call", "response_format", "images_layout"}


def test_the_plan_schema_is_sent_as_the_decoder_grammar() -> None:
    chat = FakeChat(PLATE_ANSWER)
    propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    sent = chat.formats[0]
    assert isinstance(sent, dict) and "properties" in sent
    assert {"parameters", "sketches", "operations", "result"} <= set(sent["properties"])
    assert "source" not in sent["properties"] and "source" not in sent["required"]
    assert sent["properties"]["questions"] == {"type": "array", "items": {"type": "string"}}
    assert sent["additionalProperties"] is False
    # Removing provenance from the model's reply must not weaken the saved plan contract.
    assert "source" in GeneralPlan.model_json_schema()["required"]
    # An unstructured run asks for the same thing and gets no grammar.
    chat = FakeChat(PLATE_ANSWER)
    propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64, structured=False)
    assert chat.formats[0] is None


def test_a_cut_off_answer_says_so() -> None:
    class Cutting(FakeChat):
        def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None):
            if isinstance(stats, dict):
                stats.update({"done_reason": "length", "eval_count": 4096})
            return PLATE_ANSWER[:400]

    candidate = propose_plan(Cutting(""), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.answer_truncated is True
    assert "kesildi" in candidate.errors[0]
    assert candidate.stats["eval_count"] == 4096


def test_the_record_names_the_interface_the_answer_came_from() -> None:
    """A schema-constrained decode and a free-text one are two different measurements of a model."""
    candidate = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64,
                             structured=True)
    assert candidate.settings["response_format"] == f"json-schema:{REPLY_SCHEMA_VERSION}"
    free = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64,
                        structured=False)
    assert free.settings["response_format"] == "text"


def test_a_truncated_answer_is_named_as_such() -> None:
    chat = FakeChat("{\"parameters\": {", done_reason="length")
    candidate = propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.answer_truncated is True
    assert "yanıtta JSON nesnesi yok (çıktı sınırında kesildi)" in candidate.errors


# --- the narrower-call interface (PLAN sections 19.4, 20) --------------------------------------

class StepChat(FakeChat):
    """Answers each call from the grammar it was handed, so no call can be answered as another."""

    def __init__(self, answers: dict, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.answers = answers
        self.asked: list[str] = []

    def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None) -> str:
        self.prompts.append(prompt)
        self.formats.append(response_format)
        call = str((response_format or {}).get("title", "")).rsplit(":", 1)[-1].strip()
        self.asked.append(call)
        if isinstance(stats, dict):
            stats.update({"done_reason": "stop", "eval_count": 7, "prompt_eval_count": 100})
        answer = self.answers.get(call, "")
        if isinstance(answer, Exception):
            raise answer
        return answer


def split_answers() -> dict:
    """The one-call answer cut into the calls the interface makes.

    The profile step asks one closed profile per call — the readings measured one outline and one
    circle here, so the outline's sketch is the first profile answer and the hole's the second. The
    merged plan still has to equal the one-call plan.
    """
    full = json.loads(PLATE_ANSWER)
    return {
        "parameters": json.dumps({"unit": full["unit"], "parameters": full["parameters"],
                                  "assumptions": full["assumptions"], "questions": full["questions"]}),
        "profile 1/2": json.dumps({"sketches": {"plate": full["sketches"]["plate"]}}),
        "profile 2/2": json.dumps({"sketches": {"hole": full["sketches"]["hole"]}}),
        "operations": json.dumps({"operations": full["operations"], "result": full["result"]}),
    }


def test_the_calls_merge_into_the_same_plan_the_one_call_produced() -> None:
    chat = StepChat(split_answers())
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "proposed"
    assert candidate.plan is not None
    assert chat.asked == ["parameters", "profile 1/2", "profile 2/2", "operations"]
    assert candidate.citations["spans_cited"] == ["d1", "d4"]
    assert candidate.questions == ["Cep derinliği paftada okunamadı."]
    one_call = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.plan == one_call.plan
    assert candidate.prompt_version == PROMPT_VERSION_SPLIT
    assert candidate.settings["response_format"] == (
        f"json-schema:{REPLY_SCHEMA_VERSION_SPLIT} (parameters + 2 profil + operations = 4 çağrı)")
    assert [step["step"] for step in candidate.steps] == ["parameters", "profile", "profile", "operations"]
    # Each record names the call it came from: the grammar title, and the profile it was about.
    assert [step["response_format"].rsplit(":", 1)[-1].strip() for step in candidate.steps] == chat.asked
    assert [step["label"] for step in candidate.steps] == ["parameters", "profile 1/2 (outline)",
                                                           "profile 2/2 (h1)", "operations"]
    assert all(step["prompt_sha256"] and step["answer"] and step["errors"] == [] for step in candidate.steps)
    assert candidate.stats["steps"] == 4 and candidate.stats["eval_count"] == 28


def test_the_profile_step_asks_one_measured_profile_per_call() -> None:
    """One call per closed profile the reading measured — one outline loop, then each circle."""
    from drawingto3d.planner import PROFILE_PREDICT_CAP, profile_targets

    targets = profile_targets(evidence())
    assert [(target["kind"], target["geometry_id"]) for target in targets] == [
        ("outline", "outline"), ("circle", "h1")]
    chat = StepChat(split_answers())
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    profiles = [prompt for prompt in chat.prompts if "Target profile (this call)" in prompt]

    def target_block(prompt: str) -> dict:
        return json.loads(prompt.split("Target profile (this call):", 1)[1].split("\n")[1])

    first, second = target_block(profiles[0]), target_block(profiles[1])
    # The call's own region is a keyed block, not a sentence: the answer that drew a hole for the
    # outline's call came from a sentence with the numbers inside it.
    assert first == {"index": 1, "count": 2, "kind": "outline", "geometry_id": "outline",
                     "measured": {"width_mm": 120.0, "height_mm": 80.0}}
    assert second["geometry_id"] == "h1"
    # The second call is told which name the first one took: the merge cannot be a designed collision.
    assert "plate" in profiles[1]
    # One profile is a small answer, so the call is bounded — and the record says by how much.
    assert [step["num_predict"] for step in candidate.steps] == [None, PROFILE_PREDICT_CAP,
                                                                 PROFILE_PREDICT_CAP, None]
    assert candidate.settings["profile_targets"] == "measured-closed-profiles-v1"


def test_a_profile_call_that_answers_two_profiles_is_refused() -> None:
    answers = split_answers()
    answers["profile 1/2"] = json.dumps({"sketches": json.loads(PLATE_ANSWER)["sketches"]})
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid" and candidate.plan is None
    assert "tek kapalı profil istendi" in " ".join(candidate.errors)
    assert chat.asked == ["parameters", "profile 1/2"]


def test_a_profile_call_that_takes_a_name_already_used_is_refused() -> None:
    answers = split_answers()
    answers["profile 2/2"] = json.dumps({"sketches": {"plate": json.loads(PLATE_ANSWER)["sketches"]["plate"]}})
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid" and candidate.plan is None
    assert "bu adı başka bir profil aldı" in " ".join(candidate.errors)
    assert chat.asked == ["parameters", "profile 1/2", "profile 2/2"]


def test_a_reading_that_measured_no_closed_profile_asks_for_all_of_them_at_once() -> None:
    """A reading with no measured outline or circle cannot be enumerated: one call, as before."""
    from drawingto3d.planner import profile_targets

    assert profile_targets({"geometry": {"circles": [], "outline_mm": {}}}) == []
    answers = split_answers()
    answers["profile 1/1"] = answers["profile 1/2"]
    del answers["profile 2/2"]
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, {**evidence(), "geometry": {}}, ref="sheet", sha256="a" * 64)
    assert chat.asked == ["parameters", "profile 1/1", "operations"]
    # The question does not name a measured profile; the record says the call asked for all of them.
    assert "every closed profile" in chat.prompts[1]
    assert candidate.steps[1]["profile"]["kind"] == "all"
    assert candidate.steps[0]["accepted"] is True and candidate.steps[1]["accepted"] is True


def test_the_relation_table_shape_yields_the_same_profile_list() -> None:
    from drawingto3d.planner import profile_targets

    verified = json.loads((Path(__file__).resolve().parents[1] / "eval/relations/plate-pocket-1.json")
                          .read_text(encoding="utf-8"))
    targets = profile_targets(verified)
    assert [target["kind"] for target in targets] == ["outline"] + ["circle"] * 5
    assert targets[0]["measured"] == {"width_mm": 120.0, "height_mm": 80.0}
    assert targets[1]["geometry_id"] == "h1"


def test_each_step_grammar_carries_only_that_step_keys() -> None:
    keys = {step: set(step_reply_schema(step)["properties"]) for step in SPLIT_STEPS}
    assert keys["parameters"] == {"unit", "parameters", "assumptions", "questions"}
    assert keys["profile"] == {"sketches", "assumptions", "questions"}
    assert keys["operations"] == {"operations", "result", "assumptions", "questions"}
    # Both interfaces share the stricter wire grammar; the persistent plan remains unchanged.
    full = plan_reply_schema()
    assert step_reply_schema("profile")["properties"]["sketches"] == full["properties"]["sketches"]
    assert step_reply_schema("operations")["$defs"] == full["$defs"]
    assert all(step_reply_schema(step)["additionalProperties"] is False for step in SPLIT_STEPS)
    with pytest.raises(ValueError):
        step_reply_schema("measurements")


def test_a_call_that_fails_is_named_in_the_reason() -> None:
    answers = split_answers()
    answers["operations"] = "The part is a plate with four holes."
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.plan is None
    assert candidate.errors == ["adım operations: yanıtta JSON nesnesi yok"]
    assert [step["step"] for step in candidate.steps] == ["parameters", "profile", "profile", "operations"]
    assert candidate.steps[-1]["errors"] == ["yanıtta JSON nesnesi yok"]


def test_a_step_that_answers_another_step_shape_is_refused() -> None:
    answers = split_answers()
    answers["profile 1/2"] = json.dumps({"parameters": {"hole_diameter": {"unit": "mm", "source": "assumed",
                                                                          "value": 6.8, "explanation": "x"}}})
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.errors == ["adım profile 1/2 (outline): eksik anahtar ['sketches']"]


def test_the_split_path_keeps_the_plan_contract_it_was_given() -> None:
    """A step answer that breaks the plan's rules fails the same way a one-call answer does."""
    answers = split_answers()
    answers["parameters"] = json.dumps({"parameters": {"hole_diameter": {"unit": "mm", "source": "printed",
                                                                        "value": 6.8, "expr": "6.8",
                                                                        "span_ids": ["d4"],
                                                                        "explanation": "dört köşe deliği"}}})
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("hole_diameter" in error for error in candidate.errors)
    # ... and a citation the sheet does not carry is still refused, not repaired.
    answers = split_answers()
    payload = json.loads(answers["parameters"])
    payload["parameters"]["hole_spacing"]["span_ids"] = ["d9"]
    answers["parameters"] = json.dumps(payload)
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert any("d9" in error for error in candidate.errors)


def test_a_call_that_does_not_answer_is_recorded_and_the_run_stops() -> None:
    answers = split_answers()
    answers["profile 2/2"] = UnavailableModel("yerel model yanıt vermiyor")
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.plan is None
    assert candidate.errors == ["adım profile 2/2 (h1): model yanıt vermedi: yerel model yanıt vermiyor"]
    assert len(candidate.steps) == 3  # the calls that never ran are not invented


def test_one_wording_for_the_plan_rules_across_both_interfaces() -> None:
    """The step prompts quote the one-call prompt's rules instead of restating them."""
    from drawingto3d.planner import (
        _RULE_CITE_SPANS, _RULE_EXPRESSIONS_USE_PARAMETERS, _RULE_NO_INVENTED_NUMBERS,
        _RULE_PRINTED_CARRIES_ITS_VALUE, _RULE_SIMPLEST,
    )

    one_call = plan_prompt(evidence())
    assert _RULE_NO_INVENTED_NUMBERS in one_call and _RULE_CITE_SPANS in one_call and _RULE_SIMPLEST in one_call
    parameters = step_prompt("parameters", evidence(), {})
    accepted = {"parameters": json.loads(split_answers()["parameters"])}
    profiles = [step_prompt("profile", evidence(), accepted, target=target, index=index, count=2,
                            drawn=["plate"] if index == 2 else [])
                for index, target in enumerate(
                    [{"kind": "outline", "geometry_id": "outline", "measured": {"width_mm": 120.0}},
                     {"kind": "circle", "geometry_id": "h1", "measured": {"diameter_mm": 6.8}}], start=1)]
    operations = step_prompt("operations", evidence(), {
        **accepted,
        "profile": json.loads(split_answers()["profile 1/2"]),
    })
    profile = profiles[0]
    assert _RULE_CITE_SPANS in parameters
    # The two rules this round added are the judge's own checks in words — a derived expression may
    # only name declared parameters, and a printed parameter carries its span's number — and they are
    # quoted in both interfaces, because both are asked for parameters.
    for prompt in (one_call, parameters):
        assert _RULE_EXPRESSIONS_USE_PARAMETERS in prompt
        assert _RULE_PRINTED_CARRIES_ITS_VALUE in prompt
    assert _RULE_NO_INVENTED_NUMBERS in profile
    assert _RULE_SIMPLEST in operations
    # A step hands the accepted earlier answers over verbatim, and never the reference metadata.
    assert '"hole_spacing"' in profile and '"hole_spacing"' in operations
    assert '"plate"' in operations
    assert ".STEP" not in parameters + profile + operations
    # Both interfaces render the same evidence block, and it names its two id spaces apart: the
    # printed numbers are the citation space, the measured regions are geometry.
    for prompt in (one_call, parameters, profile, operations):
        assert "Printed numbers" in prompt and "Measured regions" in prompt
        assert "never belong in `span_ids`" in prompt
    assert parameters.index("Printed numbers") < parameters.index("Measured regions")
    # One profile per call: the second call is told the first one's name, and both say which they are.
    assert "outline" in profiles[0] and "h1" in profiles[1]
    assert "Sketch names already used" in profiles[1] and "plate" in profiles[1]
    assert "Sketch names already used" not in profiles[0]


def test_an_answer_the_provider_did_not_explain_is_not_called_complete() -> None:
    """No `done_reason` means the record cannot say how the answer ended — not that it ended well."""
    chat = FakeChat("... }} } } } }", done_reason=None)
    candidate = propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.answer_truncated is None
    assert candidate.errors == ["yanıtta JSON nesnesi yok"]
    assert "done_reason" not in candidate.stats


def test_every_run_records_the_prompt_it_asked() -> None:
    """A version name is not a question: the record carries the prompt's fingerprint."""
    chat = FakeChat(PLATE_ANSWER)
    candidate = propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.settings["prompt_sha256"] == hashlib.sha256(chat.prompts[0].encode()).hexdigest()
    step_chat = StepChat(split_answers())
    steps = propose_plan_split(step_chat, evidence(), ref="sheet", sha256="a" * 64).steps
    assert [step["prompt_sha256"] for step in steps] == [
        hashlib.sha256(prompt.encode()).hexdigest() for prompt in step_chat.prompts
    ]
    assert len({step["prompt_sha256"] for step in steps}) == 4  # four different questions, not one repeated


def _printed_records() -> dict[str, dict]:
    return {record["span_id"]: record for record in evidence()["printed"]}


def test_a_printed_parameter_has_to_carry_what_its_span_prints() -> None:
    """A real span id is not a proof: the number beside it has to be the number that span prints."""
    candidate = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.plan is not None
    assert _check_citations(candidate.plan, _printed_records()) == []

    measured = candidate.plan.model_copy(deep=True)
    measured.parameters["hole_spacing"] = measured.parameters["hole_spacing"].model_copy(
        update={"value": 100.71})  # the measured gap, while the sheet prints 100,00
    errors = _check_citations(measured, _printed_records())
    assert len(errors) == 1 and "100.71" in errors[0] and "d1" in errors[0]


def test_a_measured_value_cannot_be_called_printed_in_a_full_answer() -> None:
    payload = json.loads(PLATE_ANSWER)
    payload["parameters"]["hole_spacing"]["value"] = 100.71
    candidate = propose_plan(FakeChat(json.dumps(payload)), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.plan is None
    assert any("100.71" in error for error in candidate.errors)


def test_the_count_printed_beside_a_dimension_backs_a_count_parameter() -> None:
    """`4 x Ø6,80` prints two numbers: the diameter and how many of them there are."""
    records = _printed_records()
    assert _prints_value(records["d4"], 6.8) is True
    assert _prints_value(records["d4"], 4.0, "count") is True
    assert _prints_value(records["d4"], 4.0, "mm") is False
    assert _prints_value(records["d4"], 6.8, "count") is False
    assert _prints_value(records["d4"], 7.0) is False


def test_a_cited_unit_the_plan_does_not_use_is_refused() -> None:
    candidate = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.plan is not None
    records = _printed_records()
    records["d1"] = dict(records["d1"], unit="inch")
    errors = _check_citations(candidate.plan, records)
    assert len(errors) == 1 and "inch" in errors[0] and "mm" in errors[0]


@pytest.mark.parametrize("change, fragment", [
    ({"span_ids": ["h1", "h2"]}, "kanıtta olmayan"),
    ({"value": 100.71}, "bu değeri yazmıyor"),
    ({"value": None, "source": "derived", "expr": "absent + 1"}, "tanımsız parametre"),
    # The measured shape of the same refusal: a span id used as if it were a parameter name.
    ({"value": None, "source": "derived", "expr": "(d2 - d4) / 2"}, "tanımsız parametre"),
    ({"value": None, "source": "derived", "expr": "hole_spacing + 1"}, "döngüsel"),
])
def test_bad_parameters_stop_before_the_profile_call(change, fragment):
    answers = split_answers()
    payload = json.loads(answers["parameters"])
    payload["parameters"]["hole_spacing"].update(change)
    answers["parameters"] = json.dumps(payload)
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert chat.asked == ["parameters"]
    assert candidate.plan is None and candidate.status == "invalid"
    assert fragment in " ".join(candidate.errors)
    assert candidate.steps[0]["accepted"] is False
    assert candidate.steps[0]["answer"] == answers["parameters"]
    assert candidate.questions == ["Cep derinliği paftada okunamadı."]


@pytest.mark.parametrize("bad, fragment", [
    ({"parameters": {}}, "at least 1"),
    ({"parameters": []}, "dictionary"),
    ({"parameters": {}, "sketches": {}}, "Extra inputs"),
])
def test_empty_wrong_type_and_cross_step_fields_are_rejected_early(bad, fragment):
    answers = split_answers()
    answers["parameters"] = json.dumps(bad)
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert chat.asked == ["parameters"]
    assert fragment in " ".join(candidate.errors)


@pytest.mark.parametrize("kind, sketch, label, fragment", [
    ("radius", "hole", "profile 2/2 (h1)", "ifade ayrıştırılamadı"),
    ("offset", "hole", "profile 2/2 (h1)", "tanımsız parametre"),
    ("open_profile", "plate", "profile 1/2 (outline)", "profil kapalı değil"),
])
def test_profile_expressions_and_closure_are_checked_before_the_operations_call(kind, sketch, label, fragment):
    answers = split_answers()
    call = "profile 1/2" if sketch == "plate" else "profile 2/2"
    payload = json.loads(answers[call])
    if kind == "radius":
        payload["sketches"]["hole"]["entities"][0]["radius"] = "/hole_spacing"
    elif kind == "offset":
        payload["sketches"]["hole"]["offset"] = "unknown_offset"
    else:
        payload["sketches"]["plate"]["entities"][0]["end"][0] = "55"
    answers[call] = json.dumps(payload)
    chat = StepChat(answers)
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert chat.asked[-1] == label.split(" (")[0]
    assert candidate.steps[-1]["label"] == label
    assert "operations" not in chat.asked
    assert candidate.steps[0]["accepted"] is True
    assert candidate.steps[-1]["accepted"] is False
    assert fragment in " ".join(candidate.errors)
    assert candidate.plan is None and candidate.status == "invalid"


def test_operation_dependencies_fail_in_the_operation_step_record():
    answers = split_answers()
    payload = json.loads(answers["operations"])
    payload["operations"] = list(reversed(payload["operations"]))
    answers["operations"] = json.dumps(payload)
    candidate = propose_plan_split(StepChat(answers), evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert "adım operations:" in candidate.errors[0]
    assert "tanımsız gövde" in candidate.errors[0]
    assert candidate.steps[-1]["errors"] and not candidate.steps[-1]["accepted"]


def test_truncation_blocks_the_next_step_even_when_the_json_parses():
    class Truncated(StepChat):
        def complete(self, *args, **kwargs):
            answer = super().complete(*args, **kwargs)
            kwargs["stats"]["done_reason"] = "length"
            return answer

    chat = Truncated(split_answers())
    candidate = propose_plan_split(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert chat.asked == ["parameters"]
    assert candidate.status == "invalid" and candidate.answer_truncated
    assert "kesildi" in candidate.errors[0]
    assert candidate.steps[0]["accepted"] is False


def _anchored_evidence() -> dict:
    """A reading whose every number was measured between named anchors — the shape the chain produces."""
    return measurements_evidence(
        px_per_mm=7.82,
        frame={"width_px": 1654, "height_px": 1169},
        printed=[
            {"span_id": "pdf-0", "text": "100,00", "value": 100.0, "unit": "mm", "kind": "linear", "count": None},
            {"span_id": "pdf-1", "text": "80,00", "value": 80.0, "unit": "mm", "kind": "linear", "count": None},
            {"span_id": "pdf-4", "text": "4 x Ø6,80", "value": 6.8, "unit": "mm", "kind": "diameter", "count": 4},
        ],
        claims=[
            {"span_id": "pdf-0", "form": "distance", "resolution": "confirmed", "anchors": [
                {"geometry_id": "g9", "kind": "circle-centre", "point_mm": [-50.0, -30.0]},
                {"geometry_id": "g11", "kind": "circle-centre", "point_mm": [50.0, -30.0]}]},
            {"span_id": "pdf-1", "form": "distance", "resolution": "confirmed", "anchors": [
                {"geometry_id": "g4", "kind": "arc-rim", "point_mm": [-51.0, -40.0]},
                {"geometry_id": "g2", "kind": "arc-rim", "point_mm": [-51.0, 40.0]}]},
        ],
        geometry={"outline_mm": {"width_mm": 120.0, "height_mm": 80.0}, "circles": []},
        notes=[],
    )


def test_every_printed_number_is_offered_a_legal_name_beside_its_id() -> None:
    """The measured failure was a span id used where a name belongs; a legal name now stands beside it.

    `params-3b-01` wrote `(d2 - d4) / 2` in an expression and named a parameter `pdf-0` *with both rules
    in the question*, because the span id was the only identifier the block offered. The name is derived
    from the reading's own kind and anchors: two circle centres spaced horizontally, two arc rims
    vertically, a diameter callout.
    """
    from drawingto3d.general import NAME_RE
    from drawingto3d.planner import suggested_names

    block = _anchored_evidence()
    names = suggested_names(block)
    assert [(row["span_id"], row["name"]) for row in names] == [
        ("pdf-0", "circle_spacing_x"), ("pdf-1", "arc_spacing_y"), ("pdf-4", "diameter")]
    # A CAD identifier, never one of the sheet's own span ids, and unique.
    assert all(NAME_RE.fullmatch(row["name"]) for row in names)
    assert not ({row["name"] for row in names} & {record["span_id"] for record in block["printed"]})
    assert len({row["name"] for row in names}) == len(names)
    # Both interfaces hand the names over beside the ids they belong to, after the printed numbers.
    for prompt in (plan_prompt(block), step_prompt("parameters", block, {})):
        assert "Names for those numbers" in prompt and "circle_spacing_x" in prompt
        assert prompt.index("Printed numbers") < prompt.index("Names for those numbers")


def test_two_numbers_measured_the_same_way_get_indexed_names() -> None:
    """Two diameters cannot both be `diameter`: the pair is indexed, so no suggested name is bare."""
    from drawingto3d.planner import suggested_names

    block = measurements_evidence(
        px_per_mm=3.9,
        frame={"width_px": 100, "height_px": 100},
        printed=[
            {"span_id": "s1", "text": "Ø50", "value": 50.0, "unit": "mm", "kind": "diameter", "count": None},
            {"span_id": "s2", "text": "4 x Ø6,80", "value": 6.8, "unit": "mm", "kind": "diameter", "count": 4},
        ],
        claims=[], geometry={}, notes=[])
    assert [row["name"] for row in suggested_names(block)] == ["diameter_1", "diameter_2"]


def test_the_suggested_name_comes_from_the_reading_not_from_the_sheet() -> None:
    """Rename every span and geometry id: the same measurements still suggest the same names.

    The names read `kind`, the anchor kinds and the anchors' own coordinates — never a sheet, a case or
    a part identity, so a sheet this project has never seen is named the same way.
    """
    from drawingto3d.planner import suggested_names

    block = _anchored_evidence()
    renamed = dict(block)
    renamed["printed"] = [{**record, "span_id": f"zz-{index}"} for index, record in enumerate(block["printed"])]
    renamed["claims"] = [{**claim, "span_id": f"zz-{index}"} for index, claim in enumerate(block["claims"])]
    assert [row["name"] for row in suggested_names(renamed)] == [row["name"] for row in suggested_names(block)]
