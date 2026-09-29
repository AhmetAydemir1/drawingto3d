"""P02-b: overlap vs *near but separate* geometry (PLAN.md 7 P02-b; audit F08, F11).

Expected results are stated first, then asserted: the half ring R100/R99 is valid geometry and must pass,
while one stroke drawn forward and back is not a contour at all and must be refused.
"""
import math

import pytest

from drawingto3d.contour_audit import (angular_overlap_radians, arc_page_ends, audit_contour)


def _arc(edge_id, centre, radius, a, b, page_start_degrees=None):
    """An arc whose stored ends come from its canonical pair (page angle = -canonical).

    `page_start_degrees` may override the stored start angle when a test deliberately wants the stored
    point to disagree with the canonical pair.
    """
    page_start = math.radians(-a if page_start_degrees is None else page_start_degrees)
    end = arc_page_ends(centre, radius, a, b)[1]
    start = [centre[0] + radius * math.cos(page_start), centre[1] + radius * math.sin(page_start)]
    return {"id": edge_id, "kind": "arc", "center": list(centre), "radius": radius, "a": a, "b": b,
            "start": start, "end": list(end)}


def _line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def _kinds(result, kind):
    return [issue for issue in result["issues"] if issue["kind"] == kind]


def test_a_half_ring_of_two_close_circles_is_valid_geometry():
    """F08: R100 outer and R99 inner are two circles, not one support. The half annulus they bound, closed
    by its two radial ends, is valid — the old 2%-of-radius rule called the two arcs one support and
    rejected the ring as an overlap."""
    centre = (200, 200)
    outer = _arc("o", centre, 100, 0.0, -180.0)          # right -> bottom -> left
    left = _line("ll", [100.0, 200.0], [101.0, 200.0])
    inner = _arc("i", centre, 99, 180.0, 0.0)            # left -> bottom -> right
    right = _line("lr", [299.0, 200.0], [300.0, 200.0])
    result = audit_contour([outer, left, inner, right])
    assert result["ok"] is True, result["issues"]
    assert result["closure_px"] == pytest.approx(0.0, abs=1e-9)


def test_an_exact_repeat_of_one_arc_is_still_refused():
    """The other side of F08: the *same* arc twice on the same support is an overlap, both directions."""
    forward = _arc("f", (200, 200), 100, 0.0, -180.0)
    same = _arc("s", (200, 200), 100, 0.0, -180.0)
    reverse = _arc("r", (200, 200), 100, -180.0, 0.0)      # page 180° -> 0°: the same stretch backwards
    assert _kinds(audit_contour([forward, same]), "overlap"), "aynı yay iki kez"
    backwards = audit_contour([forward, reverse])
    overlaps = _kinds(backwards, "overlap")
    assert overlaps, backwards["issues"]
    assert "ters yön" in overlaps[0]["message"], overlaps[0]["message"]


def test_a_forward_and_back_stroke_of_one_line_is_not_a_contour():
    """F11: one line drawn out and back 0.8 px apart encloses no area. The old fixed 1 px overlap threshold
    let it through; a boundary that returns over itself must be refused."""
    forward = _line("f", [0.0, 0.0], [400.0, 0.0])
    back = _line("b", [400.0, 0.8], [0.0, 0.8])
    result = audit_contour([forward, back])
    assert result["ok"] is False
    assert _kinds(result, "overlap"), result["issues"]
    assert _kinds(result, "zero_area"), result["issues"]
    assert "sıfır alana yakın" in _kinds(result, "zero_area")[0]["message"]


def test_angular_overlap_is_the_exact_intersection_of_the_spans():
    """P02-b.3: the overlap is interval arithmetic, not a 512x512 sample distance. These three values are
    exact by hand and the wrap-around pair must not be treated as one broken interval."""
    assert angular_overlap_radians(0.0, math.pi, math.pi, math.pi) == pytest.approx(0.0, abs=1e-12)
    assert angular_overlap_radians(0.0, math.pi, math.pi - math.radians(10), math.pi) == pytest.approx(math.radians(10))
    assert angular_overlap_radians(math.radians(350), math.radians(20), 0.0, math.pi) == pytest.approx(math.radians(10))


def test_arcs_sharing_only_an_endpoint_are_not_an_overlap():
    """P02-b.4: two arcs meeting at 10° and 350° share no interval — only a point."""
    first = _arc("a", (200, 200), 100, 10.0, -10.0)      # page 350° -> 10°
    second = _arc("b", (200, 200), 100, -10.0, -350.0)   # page 10° -> 350°
    assert first["end"] == pytest.approx(second["start"])
    assert second["end"] == pytest.approx(first["start"])
    result = audit_contour([first, second])
    assert result["ok"] is True, result["issues"]
