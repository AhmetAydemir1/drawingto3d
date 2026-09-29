"""The name probe's judgement, without asking a model: what it measures and how it reads an answer.

The live part of `eval/name_probe.py` needs Ollama; these tests cover the parts a model does not
decide — which constraints go on the wire, and whether an answer that kept or used an illegal name is
read as such.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    # `eval/name_probe.py` imports its sibling `model_baseline`, exactly as it does when the script is
    # run: the script's own directory is on the path.
    sys.path.insert(0, str(ROOT / "eval"))
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location("name_probe", ROOT / "eval" / "name_probe.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["name_probe"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_each_probe_asks_the_same_question_twice() -> None:
    module = load_module()
    for probe, spec in module.PROBES.items():
        control = spec["schema"](constrained=False)
        constrained = spec["schema"](constrained=True)
        assert control != constrained, probe
        assert json.dumps(control, sort_keys=True) != json.dumps(constrained, sort_keys=True)


def test_the_control_schema_carries_no_pattern_and_the_constrained_one_does() -> None:
    module = load_module()
    constrained = json.dumps(module.PROBES["property-names"]["schema"](constrained=True))
    control = json.dumps(module.PROBES["property-names"]["schema"](constrained=False))
    assert module.NAME_PATTERN in constrained and module.NAME_PATTERN not in control
    assert module.NAME_PATTERN not in json.dumps(
        module.PROBES["string-field"]["schema"](constrained=False))


def test_the_verdict_reads_the_answer_the_decoder_actually_produced() -> None:
    module = load_module()
    legal = module.verdict(["hole_spacing_x"])
    assert legal == {"names": ["hole_spacing_x"], "illegal_names": [], "legal": True}
    illegal = module.verdict(["Hole_Spacing-X"])
    assert illegal["legal"] is False and illegal["illegal_names"] == ["Hole_Spacing-X"]
    # An empty answer is a refusal, not a constraint that worked.
    assert module.verdict([])["legal"] is False
    assert module.verdict(["hole_spacing_x", "pdf-0"])["illegal_names"] == ["pdf-0"]


def test_the_probe_reads_only_the_field_it_asked_about() -> None:
    module = load_module()
    payload = {"parameters": {"Hole-X": 1}, "result": "Hole-X"}
    assert module.PROBES["property-names"]["reads"](payload) == ["Hole-X"]
    assert module.PROBES["string-field"]["reads"](payload) == ["Hole-X"]
    assert module.PROBES["property-names"]["reads"]({}) == []


def test_the_recorded_wire_view_is_the_schema_the_run_sends() -> None:
    module = load_module()
    wire = module.wire_name_fields()
    assert wire["property_names"] == {key: {"pattern": module.NAME_PATTERN}
                                      for key in ("parameters", "sketches")}
    assert wire["result"]["pattern"] == module.NAME_PATTERN
    for operation in ("extrude", "revolve", "repeat", "cut"):
        for field in wire["reference_fields"][operation].values():
            assert all(item == {"type": "string", "pattern": module.NAME_PATTERN} for item in field)
    assert wire["reference_fields"]["fuse"]["inputs.items"] == {"type": "string",
                                                               "pattern": module.NAME_PATTERN}


@pytest.mark.parametrize("probe", ["string-field", "property-names", "property-names-enum",
                                   "pattern-properties"])
def test_every_probe_would_read_a_refusal_as_a_refusal(probe) -> None:
    module = load_module()
    assert module.PROBES[probe]["reads"]({}) == []
