"""The model may interpret a printed quantity, but cannot rewrite its value or source."""
import json

import pytest

from drawingto3d.catalog import build_catalog, judge_reply, propose_parameters, reply_schema, selection_prompt
from drawingto3d.general import evaluate_parameters
from drawingto3d.planner import _check_parameter_citations
from test_planner import FakeChat


@pytest.fixture
def evidence():
    return {
        "printed": [
            {"span_id": "s1", "value": 2.345, "unit": "in", "text": "2.345", "kind": "linear"},
            {"span_id": "s2", "value": 6.8, "unit": "mm", "text": "4 x Ø6.8", "kind": "diameter", "count": 4},
        ],
        "claims": [{"span_id": "s1", "measured_mm": 59.6, "resolution": "confirmed",
                    "verified_against": "secret.step", "anchors": [{"geometry_id": "g1"}]}],
        "sheet": {"px_per_mm": 7.82}, "geometry": {"outline_mm": {"width_mm": 59.6}},
    }


@pytest.fixture
def suggestions():
    return [{"span_id": "s1", "name": "width"}, {"span_id": "s2", "name": "diameter"}]


@pytest.fixture
def catalog(evidence, suggestions):
    return build_catalog(evidence, suggestions)


def reply(expr=None, unit="mm"):
    return {"selections": [{"name": "diameter", "meaning": "hole diameter"}],
            "derived": [] if expr is None else [
                {"name": "result", "expr": expr, "unit": unit, "explanation": "proposed interpretation"}],
            "questions": []}


def test_printed_quantities_keep_exact_units_values_and_separate_count(catalog, evidence):
    result = judge_reply(reply("diameter / 2"), catalog)
    assert result.status == "needs_review"
    params = result.parameters
    assert params["width"].value == 2.345 and params["width"].unit == "in"
    assert params["diameter_count"].value == 4 and params["diameter_count"].unit == "count"
    assert params["width"].span_ids == ["s1"]
    assert _check_parameter_citations(params, {r["span_id"]: r for r in evidence["printed"]}, "mm") == []
    assert evaluate_parameters(params)["width"] == pytest.approx(2.345 * 25.4)
    assert evaluate_parameters(params)["result"] == pytest.approx(3.4)
    assert result.checks["interpretation_verified"] is False
    assert result.checks["geometry_verified"] is False


def test_prompt_omits_scale_and_verification_metadata(catalog, evidence):
    prompt = selection_prompt(catalog, evidence)
    assert "7.82" not in prompt and "secret.step" not in prompt
    assert "59.6" in prompt  # measured geometry is context, not a printed parameter
    assert "measured_mm" not in catalog.model_dump_json()
    schema = reply_schema(catalog)
    selection = schema["$defs"]["Selection"]
    assert selection["properties"]["name"]["enum"] == ["width", "diameter", "diameter_count"]
    assert "value" not in selection["properties"] and selection["additionalProperties"] is False


@pytest.mark.parametrize("mutation", [
    {"value": 59.6}, {"unit": "mm"}, {"span_ids": ["g1"]}, {"name": "not_declared"},
])
def test_selection_cannot_rewrite_source(catalog, mutation):
    payload = reply()
    payload["selections"][0].update(mutation)
    result = judge_reply(payload, catalog)
    assert result.status == "invalid" and not result.parameters


@pytest.mark.parametrize("expr", [
    "unknown / 2", "s1 / 2", "7.82", "width + 2", "width + 2*2", "width + sqrt(2)",
    "width + diameter_count", "width / width", "width * diameter", "sqrt(width)",
    "width ** (2 ** 2)", "width / 0", "abs(width, diameter)", "min(width)",
])
def test_unsupported_literals_units_and_references_fail(catalog, expr):
    result = judge_reply(reply(expr), catalog)
    assert result.status == "invalid" and result.errors and not result.parameters


@pytest.mark.parametrize("expr, expected", [
    ("width + diameter / 2", 2.345 * 25.4 + 3.4),
    ("sqrt(width**2 + diameter**2)", ((2.345 * 25.4)**2 + 6.8**2)**0.5),
    ("width / diameter_count", 2.345 * 25.4 / 4),
    ("max(width, diameter)", 2.345 * 25.4),
])
def test_referenced_dimensional_arithmetic(catalog, expr, expected):
    # width need not be selected again: every printed parameter is already declared.
    result = judge_reply(reply(expr), catalog)
    assert result.status == "needs_review"
    assert evaluate_parameters(result.parameters)["result"] == pytest.approx(expected)


def test_cycles_and_collisions_are_invalid(catalog):
    cyclic = reply("other / 2")
    cyclic["derived"].append({"name": "other", "expr": "result * 2", "unit": "mm", "explanation": "cycle"})
    assert "döngüsel" in " ".join(judge_reply(cyclic, catalog).errors)
    cyclic["derived"][0]["name"] = "width"
    assert "çakışıyor" in " ".join(judge_reply(cyclic, catalog).errors)


def test_missing_dimension_stays_a_question(catalog):
    result = judge_reply({"selections": [], "derived": [], "questions": ["What is the depth?"]}, catalog)
    assert result.status == "needs_input"
    assert all(p.source == "printed" for p in result.parameters.values())
    assert judge_reply({"selections": [], "derived": [], "questions": []}, catalog).status == "invalid"


def test_request_is_recorded_before_call_and_answer_is_retained(evidence, suggestions):
    chat = FakeChat(json.dumps(reply()))
    saved = []

    def before(record):
        assert chat.prompts == []
        saved.append(record)

    result = propose_parameters(chat, evidence, suggestions, on_request=before)
    assert result.status == "needs_review"
    assert result.request == saved[0]["request"]
    assert result.answer == chat.answer
    assert result.stats["done_reason"] == "stop"
    chat.done_reason = "length"
    truncated = propose_parameters(chat, evidence, suggestions)
    assert truncated.status == "invalid" and truncated.answer == chat.answer


@pytest.mark.parametrize("change", [{"unit": "unknown"}, {"value": float("nan")}, {"count": 2.5}])
def test_bad_evidence_stops_before_model(evidence, suggestions, change):
    evidence["printed"][0].update(change)
    chat = FakeChat("{}")
    result = propose_parameters(chat, evidence, suggestions)
    assert result.status == "invalid" and not chat.prompts


def test_duplicate_sources_or_names_do_not_silently_overwrite(evidence, suggestions):
    evidence["printed"].append(evidence["printed"][0])
    with pytest.raises(ValueError, match="tekrarlı"):
        build_catalog(evidence, suggestions)
    suggestions[1]["name"] = "width"
    with pytest.raises(ValueError, match="çakışması"):
        build_catalog(evidence, suggestions)
