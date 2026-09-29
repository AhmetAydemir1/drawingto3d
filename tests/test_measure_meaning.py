"""P03 acceptance (PLAN.md §8): a measurement's *meaning* is the user's decision, not a guess.

The whole file works through the real `Decisions.model_validate` + `validate_decisions` path and through
`user_dimensions` on hand-built profiles — geometry and schema only, no sheet, no example id.

Covered: one printed span tied twice with *distinct decision ids* is accepted; a repeated decision id is
refused; an axis the user confirmed is what gets fixed (X and Y move different coordinates); an inch value
is carried as millimetres; a record without a confirmed axis is refused with a message that asks the user
instead of silently filling the meaning in (PLAN §8.4, §8.10).
"""
import math

import pytest

from drawingto3d.guided import Decisions, questions, user_dimensions, validate_decisions


def line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def square(size=100.0):
    return {"id": "outline_0", "kind": "wire", "join_max_px": 0.0, "points": [],
            "edges": [line("e0", (0, 0), (size, 0)), line("e1", (size, 0), (size, size)),
                      line("e2", (size, size), (0, size)), line("e3", (0, size), (0, 0))]}


def options(circles=None):
    return {"frame": {"width": 400, "height": 400}, "profiles": [square()],
            "circles": circles or [{"id": "g7", "center": [150.0, 100.0], "radius": 8.0}],
            "measurements": [{"id": "t0", "text": "40,00"}, {"id": "t1", "text": "50,00"}]}


def end(kind, edge_or_circle, point):
    return {"kind": kind, "id": edge_or_circle, "x": point[0], "y": point[1]}


def decisions(bindings):
    return Decisions.model_validate({"calibration": {"first": [0, 0], "second": [100, 0], "value": 100.0,
                                                     "unit": "mm", "span_id": None},
                                     "profile_id": "outline_0", "thickness": 10.0, "holes": [],
                                     "bindings": bindings, "trace_acknowledged": True})


SCALE, ORIGIN = 1.0, [0.0, 200.0]


def test_one_print_span_tied_twice_with_distinct_decision_ids_is_accepted():
    """The sheet may carry one printed number that the user ties to two different relations — the *source*
    id repeats, the *decision* ids do not (PLAN §8.3)."""
    ties = [{"id": "b0", "value": 60.0, "unit": "mm", "span_id": "t0", "axis": "x", "direction": 1,
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "e1:start", (100, 0))},
            {"id": "b1", "value": 60.0, "unit": "mm", "span_id": "t0", "axis": "y", "direction": 1,
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "e2:end", (0, 100))}]
    validate_decisions(options(), decisions(ties))          # the real product path: no raise


def test_the_same_decision_id_twice_is_refused():
    ties = [{"id": "b0", "value": 60.0, "unit": "mm", "span_id": "t0", "axis": "x", "direction": 1,
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "e1:start", (100, 0))},
            {"id": "b0", "value": 50.0, "unit": "mm", "span_id": "t1", "axis": "y", "direction": 1,
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "e2:end", (0, 100))}]
    with pytest.raises(ValueError, match="iki kez kullanılmış"):
        validate_decisions(options(), decisions(ties))


def test_a_record_without_a_confirmed_axis_is_asked_not_filled_in():
    """PLAN §8.10: an old record's missing axis stays missing — the flow *asks*, nothing is assumed."""
    ties = [{"value": 60.0, "unit": "mm", "span_id": "t0",
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "e1:start", (100, 0))}]
    parsed = decisions(ties)                                # the schema keeps it None; the old record still loads
    assert parsed.bindings[0].axis is None and parsed.bindings[0].direction is None
    validate_decisions(options(), parsed)                   # saving keeps the record; the meaning stays open
    asks = questions(parsed)
    assert any("eksenini" in ask and "X/Y" in ask for ask in asks), asks


def _tie_to_centre(circle_id, point, axis, direction, value=40.0, unit="mm"):
    return {"id": "b0", "value": value, "unit": unit, "span_id": None, "axis": axis, "direction": direction,
            "first": end("vertex", "e0:start", (0, 0)), "second": end("centre", circle_id, point)}


def test_the_confirmed_axis_is_the_one_that_gets_fixed():
    """X fixes the horizontal difference, Y the vertical: the same two points, two different meanings."""
    circles = [{"id": "g7", "center": [150.0, 100.0], "radius": 8.0}]
    options_x = options([dict(circles[0])])
    report_x = user_dimensions(square(), options_x, decisions([_tie_to_centre("g7", (150, 100), "x", 1)]),
                               SCALE, ORIGIN)
    dx_mm = abs(report_x["centres"]["g7"][0] - 0.0) / SCALE
    assert report_x["status"] != "conflict" and dx_mm == pytest.approx(40.0, abs=1e-6)

    options_y = options([dict(circles[0])])
    report_y = user_dimensions(square(), options_y, decisions([_tie_to_centre("g7", (150, 100), "y", -1)]),
                               SCALE, ORIGIN)
    # The datum is the square's own corner at pixel (0,0); the tie fixes the *difference* from it, so the
    # centre's solved pixel y must sit 40 px (40 mm) away from that corner — not from the image origin.
    dy_mm = abs(report_y["centres"]["g7"][1] - 0.0) / SCALE
    assert report_y["status"] != "conflict" and dy_mm == pytest.approx(40.0, abs=1e-6)


def test_an_inch_value_is_carried_as_millimetres():
    """The decision keeps the user's value and unit; the geometry is solved in millimetres (PLAN §8.3)."""
    parsed = decisions([_tie_to_centre("g7", (150, 100), "x", 1, value=1.0, unit="in")])
    assert parsed.bindings[0].value == 1.0 and parsed.bindings[0].unit == "in"
    report = user_dimensions(square(), options(),
                             parsed, SCALE, ORIGIN)
    dx_mm = abs(report["centres"]["g7"][0] - 0.0) / SCALE
    assert dx_mm == pytest.approx(25.4, abs=1e-6)


def test_a_tie_whose_geometry_left_the_contour_is_asked_about_not_moved():
    """PLAN §8.9: after the contour changes, a tie's own end may no longer exist. The record keeps the tie
    exactly as written, the flow asks for a re-binding, and nothing is re-mapped to the nearest point."""
    ties = [{"id": "b0", "value": 60.0, "unit": "mm", "span_id": "t0", "axis": "x", "direction": 1,
             "first": end("vertex", "e0:start", (0, 0)), "second": end("vertex", "edge:9", (100, 0))}]
    parsed = decisions(ties)
    validate_decisions(options(), parsed)               # saving keeps the record; no hard stop, no move
    asks = questions(parsed, None, options())
    assert any("yeniden bağlanmalı" in ask and "edge:9" in ask for ask in asks), asks
