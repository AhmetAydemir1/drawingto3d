"""The wire grammar must encode constraints that Python defaults/validators omit."""

import json

import pytest

from drawingto3d.general import NAME_PATTERN, GeneralPlan, Parameter, Sketch
from drawingto3d.planner import (
    _NAME_DEFINITIONS,
    _NAME_REFERENCE_FIELDS,
    _RULE_CAD_NAMES,
    plan_prompt,
    plan_reply_schema,
    step_prompt,
    step_reply_schema,
)


@pytest.mark.parametrize("name,tag", [
    ("LineEntity", "type"), ("ArcEntity", "type"), ("CircleEntity", "type"),
    ("ExtrudeOp", "op"), ("RevolveOp", "op"), ("CutOp", "op"), ("FuseOp", "op"),
])
def test_union_tags_required_in_wire_schema(name, tag):
    definition = plan_reply_schema()["$defs"][name]
    assert tag in definition["required"]
    assert "const" in definition["properties"][tag]


def test_parameter_branches_exclude_value_expr_conflicts():
    choices = plan_reply_schema()["$defs"]["Parameter"]["oneOf"]
    assert len(choices) == 4
    for branch in choices:
        properties = branch["properties"]
        source = properties["source"]["const"]
        value_field = "expr" if source == "derived" else "value"
        excluded = "value" if source == "derived" else "expr"
        assert excluded not in properties and branch["additionalProperties"] is False
        assert {"source", "unit", value_field} <= set(branch["required"])
        assert properties[value_field]["type"] == ("string" if source == "derived" else "number")
        if source == "printed":
            assert "span_ids" in branch["required"]
            assert properties["span_ids"]["minItems"] == 1
        elif source == "derived":
            assert properties["unit"]["enum"] == ["mm", "deg"]
        else:
            assert "explanation" in branch["required"]
            assert properties["explanation"]["minLength"] == 1


def test_repeat_branches_cannot_emit_both_modes_or_omit_tag():
    choices = plan_reply_schema()["$defs"]["RepeatOp"]["oneOf"]
    assert len(choices) == 2
    for branch in choices:
        modes = set(branch["properties"]) & {"linear", "circular"}
        assert len(modes) == 1
        assert modes | {"op"} <= set(branch["required"])
        assert branch["additionalProperties"] is False
        assert "$ref" in branch["properties"][next(iter(modes))]


def test_wire_generation_does_not_mutate_persistent_schema_or_relax_validation():
    before = json.dumps(GeneralPlan.model_json_schema(), sort_keys=True)
    plan_reply_schema()
    step_reply_schema("parameters")
    assert json.dumps(GeneralPlan.model_json_schema(), sort_keys=True) == before
    with pytest.raises(ValueError, match="value veya expr"):
        Parameter(source="printed", value=6.8, expr="6.8", span_ids=["d4"])
    with pytest.raises(ValueError, match="discriminator"):
        Sketch(entities=[{"center": ["0", "0"], "radius": "4"}])


def test_both_interfaces_use_identical_leaf_constraints():
    full = plan_reply_schema()
    for step in ("parameters", "profile", "operations"):
        schema = step_reply_schema(step)
        assert schema["$defs"] == full["$defs"]
        assert schema["additionalProperties"] is False


def test_the_wire_schema_states_the_name_rule_where_the_wire_can_carry_it():
    """Every place a plan names something carries the identifier pattern, keys included.

    The keys are the one place the provider does not enforce it (`eval/name_probe.py`); the schema
    still states the contract there, and the prompt says it in words.
    """
    schema = plan_reply_schema()
    for key in ("parameters", "sketches"):
        assert schema["properties"][key]["propertyNames"] == {"pattern": NAME_PATTERN}
    for operation, fields in _NAME_REFERENCE_FIELDS.items():
        definition = schema["$defs"][_NAME_DEFINITIONS[operation]]
        for branch in definition.get("oneOf") or [definition]:
            for field in fields:
                assert branch["properties"][field] == {"type": "string", "pattern": NAME_PATTERN}
    assert schema["$defs"]["FuseOp"]["properties"]["inputs"]["items"] == {"type": "string",
                                                                          "pattern": NAME_PATTERN}
    for field in ("id", "output"):
        assert schema["$defs"]["CutOp"]["properties"][field]["pattern"] == NAME_PATTERN
    assert schema["properties"]["result"]["pattern"] == NAME_PATTERN


def test_every_operation_tag_the_adapter_rewrites_is_a_real_tag():
    """The rewrite is keyed by the tag an answer writes, so every tag has to exist in the contract."""
    schema = plan_reply_schema()
    definitions = list(schema["$defs"].values())
    definitions += [branch for definition in schema["$defs"].values()
                    for branch in (definition.get("oneOf") or [])]
    tags = {definition["properties"]["op"]["const"] for definition in definitions
            if isinstance(definition, dict) and "const" in definition.get("properties", {}).get("op", {})}
    assert set(_NAME_REFERENCE_FIELDS) <= tags
    assert set(_NAME_DEFINITIONS) == set(_NAME_REFERENCE_FIELDS)


def test_the_prompt_says_the_naming_rule_in_both_interfaces():
    one_call = plan_prompt({"version": 1, "printed": [], "claims": [], "geometry": {}, "notes": []})
    assert _RULE_CAD_NAMES in one_call
    assert "pdf-0" in one_call  # a span id is named as a citation, not as a name
    accepted = {"parameters": {"unit": "mm", "parameters": {}},
                "profile": {"sketches": {}},
                "operations": {"operations": [], "result": "b"}}
    for step in ("parameters", "profile", "operations"):
        assert _RULE_CAD_NAMES in step_prompt(step, {"version": 1, "notes": []}, accepted)
