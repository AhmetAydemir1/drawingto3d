"""The planning layer: a model's answer is a plan candidate, judged by the schema and the compiler.

Every test here builds the answer it needs instead of asking a model, so the suite says what the code
does with an answer, not whether a model is installed.
"""

from __future__ import annotations

import json

import pytest

from drawingto3d.errors import UnavailableModel
from drawingto3d.general import GeneralPlan, compile_general
from drawingto3d.llama import ChatSettings, ModelInfo, find_model
from drawingto3d.planner import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    measurements_evidence,
    plan_prompt,
    propose_plan,
)


class FakeChat:
    """A chat client that answers with whatever the test hands it."""

    def __init__(self, answer: str | Exception, model: str = "test-model",
                 done_reason: str = "stop") -> None:
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
        geometry={"circles": [{"id": "h1", "diameter_mm": 6.8, "centre_mm": [-50.0, -30.0]}]},
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
    assert set(record) == {"model", "num_ctx", "temperature", "num_predict", "keep_alive", "timeout_s",
                           "image_max_side", "images_per_call", "response_format"}


def test_the_plan_schema_is_sent_as_the_decoder_grammar() -> None:
    chat = FakeChat(PLATE_ANSWER)
    propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    sent = chat.formats[0]
    assert isinstance(sent, dict) and "properties" in sent
    assert {"parameters", "sketches", "operations", "result"} <= set(sent["properties"])
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
    assert candidate.settings["response_format"] == f"json-schema:{SCHEMA_VERSION}"
    free = propose_plan(FakeChat(PLATE_ANSWER), evidence(), ref="sheet", sha256="a" * 64,
                        structured=False)
    assert free.settings["response_format"] == "text"


def test_a_truncated_answer_is_named_as_such() -> None:
    chat = FakeChat("{\"parameters\": {", done_reason="length")
    candidate = propose_plan(chat, evidence(), ref="sheet", sha256="a" * 64)
    assert candidate.status == "invalid"
    assert candidate.answer_truncated is True
    assert "yanıtta JSON nesnesi yok (çıktı sınırında kesildi)" in candidate.errors
