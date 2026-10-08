"""Dimension equations are checked against independent coordinates and a reopened STEP."""
import copy
import json
import math

import pytest

from drawingto3d.general import GeneralPlan, Parameter, build_general, evaluate_parameters
from drawingto3d.sketch_constraints import SketchConstraints, solve_constraints


def vertex(index):
    return {"kind": "vertex", "id": f"v{index}"}


def center(circle_id):
    return {"kind": "circle_center", "id": circle_id}


def dimension(identifier, axis, first, second, value, direction=1, **extra):
    return {"id": identifier, "axis": axis, "first": first, "second": second,
            "direction": direction, "value": value, **extra}


def wire(points):
    return {"id": "outline_test", "kind": "wire", "edges": [
        {"id": f"g{i}", "kind": "line", "start": point, "end": points[(i + 1) % len(points)]}
        for i, point in enumerate(points)]}


@pytest.fixture
def profile():
    # Deliberately neither square nor perfectly horizontal/vertical in the image.
    return wire([[10, 20], [109.4, 20.4], [110.2, 80.6], [9.6, 79.8]])


@pytest.fixture
def constraints():
    return {"profile_id": "outline_test", "datum": vertex(0), "relations": [
        {"id": f"r{i}", "kind": "horizontal" if i % 2 == 0 else "vertical", "edge_id": f"g{i}"}
        for i in range(4)], "dimensions": [
            dimension("width", "x", vertex(0), vertex(1), 50, span_id="text_width"),
            dimension("height", "y", vertex(1), vertex(2), 30, direction=-1)]}


def solve(profile, constraints, circles=None, **kwargs):
    return solve_constraints(profile, circles or [], 2, [10, 80],
                             SketchConstraints.model_validate(constraints), {"text_width"}, **kwargs)


def assert_parameter_values_agree(result):
    parameters = {key: Parameter.model_validate(value) for key, value in result["parameters"].items()}
    values = evaluate_parameters(parameters)
    for key, names in result["expressions"].items():
        assert [values[name] for name in names] == pytest.approx(result["points"][key], abs=1e-9)


def test_corrupted_rectangle_obeys_dimensions_and_reports_only_gauge_assumptions(profile, constraints):
    result = solve(profile, constraints)
    assert result["status"] == "constrained" and result["dof"] == 0
    assert result["outer_moves"]
    expected = [[0, 30], [50, 30], [50, 0], [0, 0]]
    for index, point in enumerate(expected):
        assert result["points"][f"vertex:v{index}"] == pytest.approx(point)
    assert result["gauge"] == {"datum": "vertex:v0", "position_mm": [0, 30]}
    assert result["free_coordinates"] == []
    assert result["parameters"]["sk_dim_0"]["source"] == "user"
    assert result["parameters"]["sk_dim_0"]["span_ids"] == ["text_width"]
    assumed = [p for p in result["parameters"].values() if p["source"] == "assumed"]
    assert len(assumed) == 2 and all("koordinat sistemi" in p["explanation"] for p in assumed)
    assert_parameter_values_agree(result)


def test_every_solved_coordinate_records_its_binding_and_equation(profile, constraints):
    """PLAN-25 §57: a solved coordinate's provenance is structured — binding, printed value, targets, equation type.

    The chain is per coordinate, not per solve: `vertex:v2`'s y is reached through the horizontal relation at
    the datum and then the height dimension, and the record has to say exactly that.
    """
    result = solve(profile, constraints)
    assert result["status"] == "constrained"
    rows = {(row["point"], row["axis"]): row for row in result["coordinates"]}
    assert len(rows) == 2 * len(result["points"])          # every coordinate of every point, both axes
    width = rows[("vertex:v1", "x")]
    assert width["source"] == "dimension" and width["value_mm"] == pytest.approx(50.0) and width["unit"] == "mm"
    assert len(width["steps"]) == 1
    step = width["steps"][0]
    assert step["binding_id"] == "width" and step["equation_type"] == "x-distance"
    assert step["printed_value"] == pytest.approx(50.0) and step["unit"] == "mm"
    assert step["span_ids"] == ["text_width"]              # the printed measurement the binding came from
    assert step["targets"] == ["vertex:v0", "vertex:v1"]
    height = rows[("vertex:v2", "y")]
    assert [item["equation_type"] for item in height["steps"]] == ["horizontal", "y-distance"]
    assert [item["binding_id"] for item in height["steps"]] == ["r0", "height"]
    assert [item["printed_value"] for item in height["steps"]] == [None, -30.0]
    # The gauge coordinate is the traced datum, not a dimensioned one, and it says so with an empty chain.
    datum = rows[("vertex:v0", "x")]
    assert datum["source"] == "trace" and datum["steps"] == []


def test_the_audit_splits_dimension_derived_from_trace_derived(profile, constraints):
    """PLAN-25 §59: `dimension-derived coordinates = N`, `trace-derived coordinates = M`, counted per value."""
    result = solve(profile, constraints)
    assert result["audit"] == {"dimension_derived": 6, "trace_derived": 2}
    traced = [(row["point"], row["axis"]) for row in result["coordinates"] if row["source"] == "trace"]
    assert traced == [("vertex:v0", "x"), ("vertex:v0", "y")]
    assert all(row["steps"] == [] and row["unit"] == "mm" for row in result["coordinates"]
               if row["source"] == "trace")


def test_exact_hole_center_and_reopened_step(profile, constraints, tmp_path):
    constraints["dimensions"] += [
        dimension("hole_x", "x", vertex(0), center("hole"), 12),
        dimension("hole_y", "y", vertex(0), center("hole"), 22, direction=-1)]
    result = solve(profile, constraints, [{"id": "hole", "center": [35, 56]}])
    assert result["status"] == "constrained"
    assert result["points"]["circle_center:hole"] == pytest.approx([12, 8])
    parameters = result["parameters"] | {
        "thickness": {"value": 10, "source": "user", "explanation": "Independent test thickness."},
        "radius": {"value": 3, "source": "user", "explanation": "Independent test radius."}}
    expressions = result["expressions"]
    plan = GeneralPlan.model_validate({
        "source": {"kind": "synthetic", "ref": "independent noisy rectangle with located hole"},
        "parameters": parameters,
        "sketches": {
            "outer": {"entities": [{"type": "line", "start": expressions[f"vertex:v{i}"],
                                      "end": expressions[f"vertex:v{(i + 1) % 4}"]} for i in range(4)]},
            "hole": {"entities": [{"type": "circle", "center": expressions["circle_center:hole"], "radius": "radius"}]}},
        "operations": [
            {"op": "extrude", "id": "make_base", "output": "base", "sketch": "outer", "distance": "thickness"},
            {"op": "extrude", "id": "make_tool", "output": "tool", "sketch": "hole", "distance": "thickness"},
            {"op": "cut", "id": "cut_hole", "output": "part", "target": "base", "tool": "tool"}],
        "result": "part"})
    build_general(plan, None, tmp_path)
    facts = json.loads((tmp_path / "geometry.json").read_text())
    assert facts["valid"] and facts["solids"] == 1
    assert facts["size"] == pytest.approx([50, 30, 10], abs=1e-6)
    assert facts["volume"] == pytest.approx(50 * 30 * 10 - math.pi * 3**2 * 10, abs=1e-4)
    assert len(facts["cylinders"]) == 1
    assert facts["cylinders"][0] == pytest.approx([3, 12, 8, 0, 10], abs=1e-6)


def test_missing_hole_y_stays_traced_and_is_not_promoted_to_user_source(profile, constraints):
    constraints["dimensions"].append(dimension("hole_x", "x", vertex(0), center("hole"), 12))
    result = solve(profile, constraints, [{"id": "hole", "center": [35, 56]}])
    assert result["status"] == "underconstrained" and result["dof"] == 1
    assert result["points"]["circle_center:hole"] == pytest.approx([12, 12])
    free = result["free_coordinates"]
    assert len(free) == 1 and free[0]["axis"] == "y" and free[0]["points"] == ["circle_center:hole"]
    assert result["parameters"][free[0]["root_parameter"]]["source"] == "assumed"
    assert_parameter_values_agree(result)


def test_unanchored_component_minimizes_change_without_faking_absolute_position(profile):
    data = {"profile_id": profile["id"], "datum": vertex(0), "dimensions": [
        dimension("spacing", "x", center("a"), center("b"), 10)]}
    result = solve(profile, data, [{"id": "a", "center": [30, 40]}, {"id": "b", "center": [58, 40]}])
    # Traced X coordinates 10 and 24 become 12 and 22, retaining their mean.
    assert result["points"]["circle_center:a"][0] == pytest.approx(12)
    assert result["points"]["circle_center:b"][0] == pytest.approx(22)
    assert result["dof"] == 9  # 12 coordinates, two datum coordinates, one distance.
    assert_parameter_values_agree(result)


def test_consistent_duplicate_dimension_is_redundant_not_conflicting(profile, constraints):
    constraints["dimensions"].append(dimension("width_copy", "x", vertex(0), vertex(1), 50))
    result = solve(profile, constraints)
    assert result["status"] == "constrained" and result["dof"] == 0
    assert result["redundant"] == ["width_copy"] and result["conflicts"] == []


def test_conflicting_measurements_return_evidence_and_no_geometry(profile, constraints):
    constraints["dimensions"].append(dimension("wrong_width", "x", vertex(0), vertex(1), 51))
    result = solve(profile, constraints)
    assert result["status"] == "conflict"
    assert result["points"] == {} and result["expressions"] == {}
    assert all(parameter["source"] == "user" for parameter in result["parameters"].values())
    assert result["conflicts"] == [{"constraint_ids": ["width", "wrong_width"], "axis": "x",
                                     "expected_mm": 51, "actual_mm": 50, "error_mm": -1}]


def test_conflicting_three_point_cycle_identifies_all_involved_dimensions(profile):
    data = {"profile_id": profile["id"], "datum": vertex(0), "dimensions": [
        dimension("ab", "x", vertex(0), vertex(1), 20),
        dimension("bc", "x", vertex(1), vertex(2), 30),
        dimension("ac", "x", vertex(0), vertex(2), 49)]}
    result = solve(profile, data)
    assert result["status"] == "conflict"
    assert set(result["conflicts"][0]["constraint_ids"]) == {"ab", "bc", "ac"}
    assert result["conflicts"][0]["actual_mm"] == 50


def test_inches_are_converted_once_and_can_match_a_millimetre_dimension(profile, constraints):
    constraints["dimensions"][0] = dimension("width", "x", vertex(0), vertex(1), 2, unit="in")
    constraints["dimensions"].append(dimension("same_mm", "x", vertex(0), vertex(1), 50.8))
    result = solve(profile, constraints)
    assert result["points"]["vertex:v1"][0] == pytest.approx(50.8)
    assert result["redundant"] == ["same_mm"]
    assert_parameter_values_agree(result)


@pytest.mark.parametrize("change,reason", [
    ({"profile_id": "other"}, "kontura ait"),
    ({"datum": vertex(20)}, "geometride yok"),
    ({"relations": [{"id": "bad", "kind": "vertical", "edge_id": "missing"}]}, "kenarı seçili"),
    ({"dimensions": [dimension("bad", "x", vertex(0), center("not_selected"), 20)]}, "geometride yok"),
    ({"dimensions": [dimension("bad", "x", vertex(0), vertex(1), 20, span_id="absent")]}, "basılı kaynağı"),
])
def test_invalid_references_are_rejected(profile, constraints, change, reason):
    with pytest.raises(ValueError, match=reason):
        solve(profile, constraints | change)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_dimension_values_are_rejected(profile, constraints, value):
    constraints["dimensions"][0]["value"] = value
    with pytest.raises(ValueError):
        solve(profile, constraints)


def test_duplicate_constraint_identifiers_are_rejected(profile, constraints):
    constraints["dimensions"][0]["id"] = "r0"
    with pytest.raises(ValueError, match="tekil"):
        solve(profile, constraints)


def test_nonrectangular_polygon_uses_the_same_equations():
    profile = wire([[0, 0], [59, 0.2], [61, 39], [20, 61], [-0.4, 40]])
    data = {"profile_id": profile["id"], "datum": vertex(0), "dimensions": []}
    expected = [[0, 40], [30, 40], [30, 20], [10, 10], [0, 20]]
    for i, (x, y) in enumerate(expected[1:], start=1):
        if x:
            data["dimensions"].append(dimension(f"x{i}", "x", vertex(0), vertex(i), x))
        else:
            data.setdefault("relations", []).append({"id": "closing_vertical", "kind": "vertical", "edge_id": "g4"})
        if y != expected[0][1]:
            data["dimensions"].append(dimension(f"y{i}", "y", vertex(0), vertex(i), expected[0][1] - y, direction=-1))
        else:
            data.setdefault("relations", []).append({"id": "top_horizontal", "kind": "horizontal", "edge_id": "g0"})
    result = solve_constraints(profile, [], 2, [0, 80], SketchConstraints.model_validate(data), set())
    assert result["status"] == "constrained" and result["dof"] == 0
    for i, point in enumerate(expected):
        assert result["points"][f"vertex:v{i}"] == pytest.approx(point)
    assert_parameter_values_agree(result)


@pytest.mark.parametrize("kind", ["wire", "circle"])
def test_arc_and_circle_outer_allow_only_center_constraints(profile, kind):
    if kind == "wire":
        profile["edges"][0]["kind"] = "arc"
    else:
        profile = {"id": "outline_test", "kind": "circle"}
    before = copy.deepcopy(profile)
    circles = [{"id": "datum", "center": [40, 40]}, {"id": "hole", "center": [80, 42]}]
    data = {"profile_id": profile["id"], "datum": center("datum"), "dimensions": [
        dimension("spacing_x", "x", center("datum"), center("hole"), 25),
        dimension("spacing_y", "y", center("datum"), center("hole"), 5, direction=-1)]}
    result = solve(profile, data, circles)
    assert result["status"] == "constrained" and result["dof"] == 0
    assert result["outer_moves"] is False
    assert result["points"]["circle_center:datum"] == pytest.approx([15, 20])
    assert result["points"]["circle_center:hole"] == pytest.approx([40, 15])
    assert any("yalnız seçili daire merkezlerini" in note for note in result["notes"])
    assert profile == before  # No accidental edits to the outer trace.
    assert_parameter_values_agree(result)
    with pytest.raises(ValueError, match="yalnız daire merkezleri"):
        solve(profile, data | {"datum": vertex(0)}, circles)
    with pytest.raises(ValueError, match="kenar ilişkisi"):
        solve(profile, data | {"relations": [{"id": "edge", "kind": "horizontal", "edge_id": "g1"}]}, circles)


def test_open_contour_is_not_silently_closed_by_solver(profile, constraints):
    profile["edges"][1]["end"] = [1, 2]
    with pytest.raises(ValueError, match="kapalı olmalı"):
        solve(profile, constraints)
