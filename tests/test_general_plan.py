"""The general plan contract: build, refuse, edit, and the plate through the same engine.

The two JSON examples in `eval/plans/` are synthetic compiler inputs (no printed
dimension is claimed); the plate is the seen regression part. None of these tests ask a
model for anything.
"""

import json
from pathlib import Path

import pytest

from drawingto3d.cadrun import CadFailure, run_program
from drawingto3d.general import (
    GeneralPlan,
    build_general,
    check_general,
    compile_general,
    edit_parameters,
    evaluate_parameters,
    from_plate,
)
from drawingto3d.ingest import load_page
from drawingto3d.plan import build_plan
from drawingto3d.plate import propose_plate

DRAWING = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PLANS = Path("eval/plans")
EXAMPLES = ("bracket_linear_pattern", "shaft_revolve_cross_hole")


def load_example(name: str) -> dict:
    return json.loads((PLANS / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plate_plan():
    plan = propose_plate(load_page(DRAWING))
    assert plan is not None
    return plan


@pytest.fixture(scope="module")
def plate_general(plate_plan):
    return from_plate(plate_plan, ref=str(DRAWING))


@pytest.fixture(scope="module")
def plate_builds(tmp_path_factory, plate_plan, plate_general):
    """Both engines build the same plate once, for every comparison below."""
    root = tmp_path_factory.mktemp("plate-engines")
    build_general(plate_general, DRAWING, root / "general")
    build_plan(plate_plan, DRAWING, root / "plate")
    return {
        "general": json.loads((root / "general" / "geometry.json").read_text(encoding="utf-8")),
        "plate": json.loads((root / "plate" / "geometry.json").read_text(encoding="utf-8")),
        "audit": json.loads((root / "general" / "plan-audit.json").read_text(encoding="utf-8")),
        "root": root,
    }


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_plans_build_and_pass_their_audit(tmp_path, name):
    plan = GeneralPlan.model_validate(load_example(name))
    step, stl = build_general(plan, None, tmp_path)
    assert step.is_file() and stl.is_file()
    audit = json.loads((tmp_path / "plan-audit.json").read_text(encoding="utf-8"))
    assert audit["passed"] and audit["status"] == "draft"
    assert all(audit["checks"].values())
    assert any(item["cylinders"] for item in audit["tool_checks"] if not item["unverified"])


def test_the_two_examples_use_different_operation_combinations():
    first = {operation["op"] for operation in load_example(EXAMPLES[0])["operations"]}
    second = {operation["op"] for operation in load_example(EXAMPLES[1])["operations"]}
    assert first == {"extrude", "repeat", "cut"}
    assert second == {"revolve", "fuse", "extrude", "cut"}


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_plans_carry_the_contract_fields(name):
    data = load_example(name)
    assert data["version"] == 1 and data["unit"] == "mm"
    assert data["source"]["kind"] == "synthetic" and data["source"]["sha256"] is None
    for parameter in data["parameters"].values():
        assert parameter["unit"] in ("mm", "in", "deg", "count")
        assert parameter["source"] in ("printed", "derived", "assumed", "user")
        assert parameter["explanation"]
        assert ("value" in parameter) != ("expr" in parameter)
    for sketch in data["sketches"].values():
        assert sketch["plane"] in ("XY", "XZ", "YZ")
        assert "offset" in sketch and sketch["entities"]
    produced: set[str] = set()
    for operation in data["operations"]:
        for key in ("input", "target", "tool"):
            if key in operation:
                assert operation[key] in produced
        for key in ("inputs",):
            if key in operation:
                assert all(name in produced for name in operation[key])
        produced.add(operation["output"])
    assert data["result"] in produced and data["assumptions"]


def test_plate_builds_through_the_general_engine_and_matches_the_plate_engine(plate_builds):
    general, plate = plate_builds["general"], plate_builds["plate"]
    assert general["valid"] is True and plate["valid"] is True
    assert general["volume"] == pytest.approx(plate["volume"], rel=1e-6)
    assert general["size"] == pytest.approx(plate["size"], abs=1e-6)
    def cylinders(facts):
        return sorted(tuple(round(value, 3) for value in item) for item in facts["cylinders"])
    assert len(plate["cylinders"]) == 9
    assert cylinders(general) == cylinders(plate)


def test_plate_general_audit_checks_holes_and_pocket_positions(plate_general, plate_builds):
    audit = plate_builds["audit"]
    assert audit["passed"]
    checked = {item["operation"]: item for item in audit["tool_checks"]}
    assert checked["holes"]["cylinders"] == 4 and not checked["holes"]["unverified"]
    assert checked["pocket"]["cylinders"] == 1 and not checked["pocket"]["unverified"]
    # A moved hole keeps volume and bounding box; the tool check must still catch it.
    facts = json.loads(json.dumps(plate_builds["general"]))
    moved_index = next(index for index, item in enumerate(facts["cylinders_axis"])
                       if abs(item[0] - 3.4) < 1e-3)
    facts["cylinders_axis"][moved_index][1] += 2
    moved = check_general(plate_general, facts)
    assert not moved["passed"]
    assert any(item["ok"] is False for item in moved["tool_checks"])


def test_compile_output_depends_only_on_geometry(plate_general):
    data = plate_general.model_dump()
    data["source"]["ref"] = "some-other-name.pdf"
    data["assumptions"] = data["assumptions"] + ["ek varsayım"]
    renamed = GeneralPlan.model_validate(data)
    code = compile_general(plate_general)
    assert compile_general(renamed) == code
    lowered = code.lower()
    assert "plate" not in lowered and "examples" not in lowered and ".pdf" not in lowered


def test_plan_json_round_trips(plate_general):
    assert GeneralPlan.model_validate_json(plate_general.model_dump_json()) == plate_general


def test_source_hash_guards_the_build(tmp_path, plate_general):
    other = tmp_path / "drawing.pdf"
    other.write_bytes(b"not the original drawing")
    with pytest.raises(ValueError, match="özet"):
        build_general(plate_general, other, tmp_path / "out")
    with pytest.raises(ValueError, match="çizim kaynağı"):
        build_general(plate_general, None, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_parameter_edit_flows_to_the_rebuilt_solid(tmp_path, plate_general):
    edited = edit_parameters(plate_general, {"hole_dx": 110})
    assert edited.parameters["hole_dx"].source == "user"
    resolved = evaluate_parameters(edited.parameters)
    assert resolved["width"] == pytest.approx(130)
    assert plate_general.parameters["hole_dx"].source == "printed"  # the original is untouched
    build_general(edited, DRAWING, tmp_path)
    facts = json.loads((tmp_path / "geometry.json").read_text(encoding="utf-8"))
    assert facts["size"] == pytest.approx([130, 80, 15], abs=1e-6)
    audit = json.loads((tmp_path / "plan-audit.json").read_text(encoding="utf-8"))
    assert audit["passed"] and audit["checks"]["declared_bbox"]


def test_explicit_override_is_not_replaced_by_a_derivation(plate_general):
    overridden = edit_parameters(plate_general, {"width": 150})
    assert overridden.parameters["width"].source == "user"
    later = edit_parameters(overridden, {"hole_dx": 110})
    assert evaluate_parameters(later.parameters)["width"] == pytest.approx(150)


def test_inch_values_convert_to_millimetres():
    data = load_example(EXAMPLES[0])
    data["parameters"]["length"] = {
        "unit": "in", "source": "assumed", "value": 1.5,
        "explanation": "inç girdi örneği",
    }
    plan = GeneralPlan.model_validate(data)
    assert evaluate_parameters(plan.parameters)["length"] == pytest.approx(38.1)


@pytest.mark.parametrize(
    "damage",
    ["open_profile", "cyclic_parameter", "unit_mismatch", "unsourced_printed",
     "unknown_reference", "unknown_body", "reused_output", "reserved_name"],
)
def test_invalid_plans_are_refused(damage):
    data = load_example(EXAMPLES[0])
    if damage == "open_profile":
        data["sketches"]["outline"]["entities"].pop()
    elif damage == "cyclic_parameter":
        data["parameters"]["area"]["expr"] = "area + 1"
    elif damage == "unit_mismatch":
        data["parameters"]["angle_x"] = {"unit": "deg", "source": "assumed", "value": 30,
                                         "explanation": "birim uyuşmazlığı örneği"}
        data["operations"][0]["distance"] = "angle_x"
    elif damage == "unsourced_printed":
        data["parameters"]["length"].pop("explanation")
        data["parameters"]["length"]["source"] = "printed"
    elif damage == "unknown_reference":
        data["parameters"]["area"]["expr"] = "length * missing_name"
    elif damage == "unknown_body":
        data["operations"][-1]["tool"] = "no_such_body"
    elif damage == "reused_output":
        data["operations"][-1]["output"] = "body"
    else:
        data["operations"][0]["output"] = "geo"
    with pytest.raises(ValueError):
        GeneralPlan.model_validate(data)


def test_a_split_solid_fails_with_the_reason(tmp_path):
    data = load_example(EXAMPLES[0])
    data["sketches"]["splitter"] = {
        "plane": "XY",
        "offset": "-1",
        "entities": [{"type": "line", "start": ["-1", "-60"], "end": ["1", "-60"]},
                     {"type": "line", "start": ["1", "-60"], "end": ["1", "60"]},
                     {"type": "line", "start": ["1", "60"], "end": ["-1", "60"]},
                     {"type": "line", "start": ["-1", "60"], "end": ["-1", "-60"]}],
    }
    data["operations"].append({"op": "extrude", "id": "split_tool", "output": "split_tool",
                               "sketch": "splitter", "distance": "width + 2"})
    data["operations"].append({"op": "cut", "id": "split", "target": "finished",
                               "tool": "split_tool", "output": "split_result"})
    data["result"] = "split_result"
    plan = GeneralPlan.model_validate(data)
    with pytest.raises(CadFailure, match="split the part in two"):
        build_general(plan, None, tmp_path)
    assert not (tmp_path / "plan-audit.json").exists()


def test_kernel_precision_on_the_shaft_is_documented(tmp_path):
    """The revolve and fuse parts are kernel-exact; the cylinder-cylinder cut is not.

    The expected removal 349.9866 mm3 is an independent quadrature (eval/plans/README.md);
    the measured 349.9709 records the kernel's approximated intersection curve.
    """
    plan = GeneralPlan.model_validate(load_example(EXAMPLES[1]))
    code = compile_general(plan)
    blank_dir, final_dir = tmp_path / "blank", tmp_path / "final"
    run_program(code.replace("solid = finished", "solid = blank"), blank_dir)
    run_program(code, final_dir)
    blank = json.loads((blank_dir / "geometry.json").read_text(encoding="utf-8"))["volume"]
    final = json.loads((final_dir / "geometry.json").read_text(encoding="utf-8"))["volume"]
    assert blank == pytest.approx(13894.70825010192, abs=1e-4)
    assert blank - final == pytest.approx(349.98662811415994, abs=0.02)
