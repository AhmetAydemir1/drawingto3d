"""The proposal slice: what the reading layers support, what they refuse, and both honestly.

The plate is the strict end-to-end check — the proposal must come out of the readings alone,
every measured value must sit within tolerance of its printed partner, the plan must build to a
solid whose volume is the closed form (rounded rectangle, four holes, one pocket), and that
volume is checked here against the analytic number, not against the pipeline's own opinion. The
plastic sheet must refuse with a reason: it is not this archetype yet, and the record says so.
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from drawingto3d.general import build_general, evaluate_parameters
from drawingto3d.observe import Unsupported
from drawingto3d.proposal import Proposal, _frame_loops, _rounded_rectangle, propose_general

PLATE = Path("examples/pdf with steps/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/plastic enclosue.pdf")

ANALYTIC_VOLUME = (120 * 80 - (4 - math.pi) * 10 ** 2) * 15 \
    - 4 * math.pi * 3.4 ** 2 * 15 - math.pi * 25.0 ** 2 * 8


@pytest.fixture(scope="module")
def plate():
    return propose_general(PLATE)


@pytest.fixture(scope="module")
def plastic():
    return propose_general(PLASTIC)


def line_loop(items):
    entities = [(gid, np.array(start, float), np.array(end, float), {"kind": "line"})
                for gid, start, end in items]
    return {"entities": entities, "area_px": 0.0}


def arc(gid, centre, radius, start_degrees, end_degrees):
    return (gid, np.array(centre, float), np.array(centre, float),
            {"kind": "arc", "centre": np.array(centre, float), "radius": radius,
             "start_degrees": start_degrees, "end_degrees": end_degrees})


def test_plate_is_proposed(plate):
    """The plate sheet: nine measurements checked, nothing refused, a plan to build."""
    assert plate.status == "proposed"
    assert plate.refusals == []
    assert plate.plan is not None
    assert plate.readings and all("Ölçülen" in reading or "basılı" in reading
                                  for reading in plate.readings)


def test_every_printed_parameter_carries_its_span(plate):
    assert plate.plan is not None
    printed = {"hole_dx", "hole_dy", "height", "thickness", "pocket_depth",
               "hole_diameter", "pocket_diameter"}
    for name in printed:
        parameter = plate.plan.parameters[name]
        assert parameter.source == "printed", name
        assert parameter.span_ids, name
        assert parameter.value is not None


def test_derived_parameters_are_expressions(plate):
    assert plate.plan is not None
    for name in ("corner_radius", "width", "area"):
        parameter = plate.plan.parameters[name]
        assert parameter.source == "derived", name
        assert parameter.expr, name


def test_assumptions_record_how_the_section_was_read(plate):
    assert plate.plan is not None
    joined = " ".join(plate.plan.assumptions)
    assert "kalınlık" in joined and "cep derinliği" in joined


def test_plate_measurements_are_recorded(plate):
    assert plate.measurements["outline_width_mm"] == pytest.approx(120.87, abs=0.01)
    assert plate.measurements["outline_height_mm"] == pytest.approx(80.56, abs=0.01)
    assert plate.measurements["corner_radius_mm"] == pytest.approx(10.05, abs=0.01)
    assert plate.measurements["hole_diameter_mm"] == pytest.approx(6.85, abs=0.01)
    assert plate.measurements["layout_centre_offset_mm"] == 0.0


def test_hole_count_was_checked_against_the_matched_circles(plate):
    assert plate.plan is not None
    assert plate.plan.parameters["hole_count"].value == 4


def test_expected_volume_is_the_closed_form(plate):
    assert plate.plan is not None
    values = evaluate_parameters(plate.plan.parameters)
    assert values["area"] == pytest.approx(120 * 80 - (4 - math.pi) * 10 ** 2, rel=1e-9)
    expected = (values["area"] * values["thickness"]
                - values["hole_count"] * math.pi * (values["hole_diameter"] / 2) ** 2
                * values["thickness"]
                - math.pi * (values["pocket_diameter"] / 2) ** 2 * values["pocket_depth"])
    assert expected == pytest.approx(ANALYTIC_VOLUME, abs=0.5)


def test_plate_plan_builds_and_passes_its_own_audit(plate, tmp_path):
    assert plate.plan is not None
    step, _stl = build_general(plate.plan, PLATE, tmp_path)
    assert step.exists()
    audit = json.loads((tmp_path / "plan-audit.json").read_text(encoding="utf-8"))
    assert audit["passed"] is True
    assert audit["checks"]["declared_volume"] is True
    assert audit["checks"]["declared_bbox"] is True


def test_plate_proposal_is_deterministic(plate):
    again = propose_general(PLATE)
    assert plate.plan is not None and again.plan is not None
    assert again.plan.model_dump_json() == plate.plan.model_dump_json()


def test_proposal_survives_a_json_round_trip(plate):
    clone = Proposal.model_validate_json(plate.model_dump_json())
    assert clone.status == "proposed"
    assert plate.plan is not None and clone.plan is not None
    assert set(clone.plan.parameters) == set(plate.plan.parameters)


def test_plastic_is_refused_with_a_reason(plastic):
    """Not this archetype yet: no diameter claims at all, and the record says so."""
    assert plastic.status == "refused"
    assert plastic.plan is None
    assert plastic.refusals and "çap" in " ".join(plastic.refusals)


def test_unsupported_suffix_is_named():
    with pytest.raises(Unsupported, match="desteklenmeyen"):
        propose_general(Path("examples/whatever.doc"))


def test_frame_loops_skips_a_sheet_border():
    border = line_loop([("b0", (10, 10), (990, 10)), ("b1", (990, 10), (990, 790)),
                        ("b2", (990, 790), (10, 790)), ("b3", (10, 790), (10, 10))])
    part = line_loop([("p0", (100, 100), (400, 100)), ("p1", (400, 100), (400, 300)),
                      ("p2", (400, 300), (100, 300)), ("p3", (100, 300), (100, 100))])
    assert _frame_loops([border, part], 1000, 800) == {0}


def test_frame_loops_keeps_a_part_that_holds_details():
    """A part outline containing detail loops is a part, not a frame (the plastic's grooves)."""
    part = line_loop([("p0", (150, 150), (650, 150)), ("p1", (650, 150), (650, 550)),
                      ("p2", (650, 550), (150, 550)), ("p3", (150, 550), (150, 150))])
    detail_a = line_loop([("d0", (200, 200), (300, 200)), ("d1", (300, 200), (300, 260)),
                          ("d2", (300, 260), (200, 260)), ("d3", (200, 260), (200, 200))])
    detail_b = line_loop([("e0", (400, 400), (500, 400)), ("e1", (500, 400), (500, 460)),
                          ("e2", (500, 460), (400, 460)), ("e3", (400, 460), (400, 400))])
    assert _frame_loops([part, detail_a, detail_b], 1000, 800) == set()


def test_rounded_rectangle_accepts_clockwise_corner_rounds():
    chain = [
        ("l0", np.array([20.0, 0.0]), np.array([180.0, 0.0]), {"kind": "line"}),
        arc("a0", (180, 20), 20.0, 0.0, -90.0),
        ("l1", np.array([200.0, 20.0]), np.array([200.0, 80.0]), {"kind": "line"}),
        arc("a1", (180, 80), 20.0, 90.0, 0.0),
        ("l2", np.array([180.0, 100.0]), np.array([20.0, 100.0]), {"kind": "line"}),
        arc("a2", (20, 80), 20.0, 180.0, 90.0),
        ("l3", np.array([0.0, 80.0]), np.array([0.0, 20.0]), {"kind": "line"}),
        arc("a3", (20, 20), 20.0, 270.0, 180.0),
    ]
    result = _rounded_rectangle(chain, scale=1.0)
    assert result is not None
    width, height, radius = result
    assert (width, height, radius) == pytest.approx((200.0, 100.0, 20.0))


def test_rounded_rectangle_rejects_a_five_entity_loop():
    chain = [("l0", np.array([0.0, 0.0]), np.array([100.0, 0.0]), {"kind": "line"}),
             ("l1", np.array([100.0, 0.0]), np.array([100.0, 50.0]), {"kind": "line"}),
             ("l2", np.array([100.0, 50.0]), np.array([40.0, 50.0]), {"kind": "line"}),
             ("l3", np.array([40.0, 50.0]), np.array([0.0, 30.0]), {"kind": "line"}),
             ("l4", np.array([0.0, 30.0]), np.array([0.0, 0.0]), {"kind": "line"})]
    assert _rounded_rectangle(chain, scale=1.0) is None
