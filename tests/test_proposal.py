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
from drawingto3d.observe import Observations, Unsupported
from drawingto3d.proposal import (Proposal, _annotation_loops, _frame_loops, _loops,
                                  _rounded_rectangle, part_class, propose_general, read_sheet)

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/6/plastic enclosue.pdf")
EXERCISE_12 = Path("examples/pdf with steps/10/Exercise 12.pdf")

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


def sheet_with(primitives, width=2000, height=1400):
    """A synthetic observation record: geometry only, which is all `part_class` reads."""
    return Observations(source={"ref": "synthetic.pdf", "sha256": "0" * 64},
                        frame={"width": width, "height": height}, text_placement="as-is",
                        primitives=primitives)


def test_annotation_loops_are_loops_that_carry_words():
    """Which closed loop is the part: a loop full of printed phrases is a title block or a table."""
    square = line_loop([("g0", (0, 0), (100, 0)), ("g1", (100, 0), (100, 50)),
                        ("g2", (100, 50), (0, 50)), ("g3", (0, 50), (0, 0))])
    table = [("TITLE:", None, 10.0, 10.0, 20.0, 5.0), ("SCALE:", None, 10.0, 20.0, 20.0, 5.0),
             ("1: 5", 1.0, 10.0, 30.0, 10.0, 5.0)]
    assert _annotation_loops([square], table) == {0}
    # A view carrying its own dimensions is not a table: numbers with one note line stay a part loop.
    view = [("100,00", 100.0, 10.0, 10.0, 20.0, 5.0), ("80,00", 80.0, 40.0, 10.0, 20.0, 5.0),
            ("60,00", 60.0, 60.0, 10.0, 20.0, 5.0), ("THRU ALL", None, 10.0, 30.0, 30.0, 5.0)]
    assert _annotation_loops([square], view) == set()
    # A phrase outside the loop is outside the question.
    outside = [("TITLE:", None, 200.0, 10.0, 20.0, 5.0), ("SCALE:", None, 200.0, 20.0, 20.0, 5.0),
               ("NAME:", None, 200.0, 30.0, 20.0, 5.0)]
    assert _annotation_loops([square], outside) == set()


def test_part_class_reads_a_flange_stack_from_the_geometry():
    """A rotational body seen face-on is a stack of circles about one centre; a flat part is its loop."""
    stack = [{"id": f"g{i}", "path_id": f"p{i}", "kind": "circle", "centre": [600, 400], "radius": r}
             for i, r in enumerate((200, 110, 72, 60, 24))]
    assert part_class(sheet_with(stack))["class"] == "rotational-flanged"
    rectangle = [{"id": "g0", "path_id": "p0", "kind": "line", "start": [100, 100], "end": [900, 100]},
                 {"id": "g1", "path_id": "p1", "kind": "line", "start": [900, 100], "end": [900, 500]},
                 {"id": "g2", "path_id": "p2", "kind": "line", "start": [900, 500], "end": [100, 500]},
                 {"id": "g3", "path_id": "p3", "kind": "line", "start": [100, 500], "end": [100, 100]}]
    assert part_class(sheet_with(rectangle))["class"] == "flat-part"
    # The same kind of stack drawn small is a feature of a plate, not a flange face: the test is
    # relative to the page, so a 16 px stack on a 2000 px sheet does not make a rotational body.
    small = rectangle + [{"id": f"c{i}", "path_id": f"q{i}", "kind": "circle", "centre": [500, 300],
                          "radius": r} for i, r in enumerate((4, 6, 8))]
    assert part_class(sheet_with(small))["class"] == "flat-part"
    assert part_class(sheet_with([]))["class"] == "unknown"


def test_new_sheet_refuses_on_a_part_loop_not_the_title_block():
    """`10/Exercise 12`: the biggest loop left after the frame is the title-block box.

    Measured before this change: the proposal refused on a 4-primitive 457.17 x 139.78 mm rectangle —
    the title block's own border, 708.6 x 216.7 px at the sheet's bottom-right corner. The part's own
    outline is a 28-primitive section-view loop, and that is what the refusal has to name.
    """
    proposal = propose_general(EXERCISE_12)
    assert proposal.status == "refused"
    assert any("antet/tablo" in note for note in proposal.notes)
    assert not any("457.17" in refusal for refusal in proposal.refusals)
    assert any("28 ilkel" in refusal for refusal in proposal.refusals)


def test_title_block_is_skipped_by_the_reading_too():
    reading = read_sheet(EXERCISE_12)
    assert reading.components["annotation_loops"] == 1
    assert any("antet/tablo" in note for note in reading.notes)


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


def test_loop_chaining_keeps_a_run_a_dead_end_would_have_eaten():
    """A dead end claims nothing, or the first chain swallows the part's own outline.

    Measured on `Drawing.pdf`: 239 lines came out as three loops and the part's outline was not one
    of them, because the first chain walked off along the dimension lines touching a corner and took
    the outline's segments with it. The square with a collinear dimension line leaving one corner is
    the plainest version of that sheet.
    """
    lines = {
        "dim": (np.array([100.0, 0.0]), np.array([220.0, 0.0])),
        "s0": (np.array([0.0, 0.0]), np.array([100.0, 0.0])),
        "s1": (np.array([100.0, 0.0]), np.array([100.0, 50.0])),
        "s2": (np.array([100.0, 50.0]), np.array([0.0, 50.0])),
        "s3": (np.array([0.0, 50.0]), np.array([0.0, 0.0])),
    }
    loops = _loops(lines, {})
    assert loops, "bir kapalı döngü bulunmalı"
    assert {entity[0] for entity in loops[0]["entities"]} == {"s0", "s1", "s2", "s3"}
    assert "dim" not in {entity[0] for loop in loops for entity in loop["entities"]}


def test_loop_chaining_takes_the_closing_segment_over_a_straighter_continuation():
    """A segment that returns to the chain's start is the drawing's own run closing, not a detour."""
    lines = {
        "c": (np.array([100.0, 40.0]), np.array([100.0, 80.0])),
        "a": (np.array([0.0, 0.0]), np.array([100.0, 0.0])),
        "b": (np.array([100.0, 0.0]), np.array([100.0, 40.0])),
        "zoom": (np.array([100.0, 40.0]), np.array([0.0, 0.0])),
    }
    loops = _loops(lines, {})
    assert loops, "kapanan zincir döngü olmalı"
    assert {entity[0] for entity in loops[0]["entities"]} == {"a", "b", "zoom"}
