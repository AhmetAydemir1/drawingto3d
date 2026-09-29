"""PLAN §26.4-A's acceptance list, as independent synthetic contours — no sheet, no example id.

A rule that only works on one drawing is not a rule. Each case here is drawn from scratch: a closed contour
that crosses itself, a genuinely open one, a valid concave one, a tangent arc join, an arc walked the other
way round, a zero-length edge and a duplicated/overlapping edge.
"""
import math

import pytest

from drawingto3d.contour_audit import audit_contour


def line(edge_id: str, start, end) -> dict:
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def arc(edge_id: str, centre, radius: float, start, end, sweep_degrees: float) -> dict:
    """An arc whose canonical angles follow the product convention: the sheet's angles, negated.

    `sweep_degrees` is the sheet-space sweep (positive = counter-clockwise on the drawing); the stored
    canonical span is its negation, and the start angle comes from the start point.
    """
    centre = list(centre)
    start_angle = math.atan2(start[1] - centre[1], start[0] - centre[0])
    a = -math.degrees(start_angle)
    b = a - sweep_degrees
    return {"id": edge_id, "kind": "arc", "start": list(start), "end": list(end), "center": centre,
            "radius": radius, "a": a, "b": b}


def kinds(audit: dict) -> set[str]:
    return {issue["kind"] for issue in audit["issues"]}


def test_closed_but_self_crossing_is_refused():
    """A bow-tie: every join is exact, so only the crossing check can catch it."""
    edges = [line("a", (0, 0), (10, 10)), line("b", (10, 10), (10, 0)),
             line("c", (10, 0), (0, 10)), line("d", (0, 10), (0, 0))]
    audit = audit_contour(edges)
    assert audit["ok"] is False
    assert "self_intersection" in kinds(audit)
    crossing = next(issue for issue in audit["issues"] if issue["kind"] == "self_intersection")
    assert crossing["kinds"] == ["line", "line"]
    assert crossing["at"] == pytest.approx([5.0, 5.0], abs=0.6)


def test_genuinely_open_contour_is_refused_with_the_gap_size():
    edges = [line("a", (0, 0), (10, 0)), line("b", (10, 0), (10, 10))]
    audit = audit_contour(edges)
    assert audit["ok"] is False and "open" in kinds(audit)
    assert audit["issues"][0]["gap_px"] == pytest.approx(math.hypot(10, 10), abs=0.01)


def test_valid_concave_contour_passes():
    edges = [line("a", (0, 0), (20, 0)), line("b", (20, 0), (20, 10)), line("c", (20, 10), (10, 10)),
             line("d", (10, 10), (10, 20)), line("e", (10, 20), (0, 20)), line("f", (0, 20), (0, 0))]
    audit = audit_contour(edges)
    assert audit["ok"] is True, audit["issues"]
    assert audit["closure_px"] == pytest.approx(0.0, abs=0.5)


def test_a_tangent_arc_join_passes():
    """The arc leaves its line tangentially: the join is real, so it must not read as a crossing."""
    edges = [line("a", (0, 0), (10, 0)), arc("b", (10, 5), 5.0, (10, 0), (10, 10), 180.0),
             line("c", (10, 10), (0, 10)), line("d", (0, 10), (0, 0))]
    audit = audit_contour(edges)
    assert audit["ok"] is True, audit["issues"]


def test_an_arc_walked_the_other_way_round_passes():
    """The same D, traversed clockwise: the arc's signed sweep is data, not a special case."""
    edges = [line("a", (0, 0), (0, 10)), line("b", (0, 10), (10, 10)), arc("c", (10, 5), 5.0, (10, 10), (10, 0), -180.0),
             line("d", (10, 0), (0, 0))]
    audit = audit_contour(edges)
    assert audit["ok"] is True, audit["issues"]
    assert audit["closure_px"] == pytest.approx(0.0, abs=0.5)


def test_zero_length_edge_is_reported():
    edges = [line("a", (0, 0), (10, 0)), line("b", (10, 0), (10, 0)), line("c", (10, 0), (10, 10)),
             line("d", (10, 10), (0, 0))]
    audit = audit_contour(edges)
    assert "zero_length" in kinds(audit)
    assert next(issue for issue in audit["issues"] if issue["kind"] == "zero_length")["ids"] == ["b"]


def test_overlapping_edges_are_reported():
    edges = [line("a", (0, 0), (10, 0)), line("b", (5, 0), (15, 0)), line("c", (15, 0), (15, 10)),
             line("d", (15, 10), (0, 0))]
    audit = audit_contour(edges)
    assert "overlap" in kinds(audit)
    assert next(issue for issue in audit["issues"] if issue["kind"] == "overlap")["ids"] == ["a", "b"]


def test_an_empty_contour_is_refused():
    audit = audit_contour([])
    assert audit["ok"] is False and kinds(audit) == {"empty"}
