"""PLAN §26.4-B: the user's printed measures must actually move the geometry.

Hand-built profiles only — no sheet, no example id. Each case states one thing the interface promises: a tie
of 60 mm makes that span 60 mm in the plan, an unmeasured span stays where the drawing traced it (visible as
remaining freedom, not silently sharpened), two ties that cannot both hold come back as a conflict with their
own ids, and a tie to a circle centre moves that centre.
"""
import math

import pytest

from drawingto3d.guided import Decisions, user_dimensions


def line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def square(size=100.0):
    """A traced square, closed, with its own pixel coordinates (origin at the top-left of the sheet)."""
    return {"id": "outline_0", "kind": "wire", "join_max_px": 0.0, "points": [],
            "edges": [line("e0", (0, 0), (size, 0)), line("e1", (size, 0), (size, size)),
                      line("e2", (size, size), (0, size)), line("e3", (0, size), (0, 0))]}


def binding(value, first, second, span_id, unit="mm"):
    """One decision: its own id, the user's confirmed axis and direction (PLAN §8.3/§8.4)."""
    axis = "x" if abs(second[2][0] - first[2][0]) >= abs(second[2][1] - first[2][1]) else "y"
    delta = (second[2][0] - first[2][0]) if axis == "x" else (first[2][1] - second[2][1])
    return {"id": span_id, "value": value, "unit": unit, "span_id": span_id, "axis": axis,
            "direction": 1 if delta >= 0 else -1,
            "first": {"kind": first[0], "id": first[1], "x": first[2][0], "y": first[2][1]},
            "second": {"kind": second[0], "id": second[1], "x": second[2][0], "y": second[2][1]}}


def decisions(bindings):
    return Decisions.model_validate({"calibration": {"first": [0, 0], "second": [100, 0], "value": 100.0,
                                                     "unit": "mm", "span_id": None},
                                     "profile_id": "outline_0", "thickness": 10.0, "holes": [],
                                     "bindings": bindings, "trace_acknowledged": True})


SCALE, ORIGIN = 1.0, [0.0, 100.0]     # 1 px/mm, Y-up gauge at the bottom-left of the square


def test_a_tie_of_sixty_millimetres_makes_that_span_sixty_millimetres():
    profile = square()
    report = user_dimensions(profile, {"circles": []},
                             decisions([binding(60.0, ("vertex", "e0:start", (0, 0)), ("vertex", "e1:start", (100, 0)),
                                                "t0")]),
                             SCALE, ORIGIN)
    assert report["status"] != "conflict" and report["moved"] > 0
    start = profile["edges"][0]["start"]
    end = profile["edges"][0]["end"]
    assert math.dist(start, end) / SCALE == pytest.approx(60.0, abs=1e-6)
    # The traced 100 mm span was moved to the user's 60 mm; the free coordinates stay reported as free.
    assert report["free"] > 0 and report["dof"] is not None


def test_two_ties_that_cannot_both_hold_are_a_conflict_with_their_ids():
    profile = square()
    ties = [binding(60.0, ("vertex", "e0:start", (0, 0)), ("vertex", "e1:start", (100, 0)), "t0"),
            binding(50.0, ("vertex", "e0:start", (0, 0)), ("vertex", "e1:start", (100, 0)), "t1")]
    report = user_dimensions(profile, {"circles": []}, decisions(ties), SCALE, ORIGIN)
    assert report["status"] == "conflict"
    assert any(set(ids or []) & {"t0", "t1"} for ids in report["conflicts"])
    assert profile["solved_dimensions"]["status"] == "conflict"


def test_a_tie_to_a_circle_centre_moves_that_centre():
    profile = square()
    circles = [{"id": "g7", "center": [150.0, 100.0], "radius": 8.0}]
    report = user_dimensions(profile, {"circles": circles},
                             decisions([binding(40.0, ("vertex", "e0:start", (0, 0)), ("centre", "g7", (150, 100)),
                                                "t0")]),
                             SCALE, ORIGIN)
    assert report["status"] != "conflict"
    centre = report["centres"]["g7"]
    corner_px = profile["edges"][0]["start"]     # the datum stays where it was traced
    assert abs(centre[0] - corner_px[0]) / SCALE == pytest.approx(40.0, abs=1e-6)
    assert circles[0]["center"] == [150.0, 100.0]   # the session's own option is never mutated


def test_without_bindings_nothing_is_solved_and_nothing_moves():
    profile = square()
    assert user_dimensions(profile, {"circles": []}, decisions([]), SCALE, ORIGIN) is None
    assert profile["edges"][0]["start"] == [0.0, 0.0]
