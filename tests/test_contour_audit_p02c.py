"""P02-c: the crossing/touch decision, decided analytically and consistently (PLAN.md 7 P02-c; F09, F10).

Expected results first: a big arc with a line through it *has* intersections (they were being missed by the
sampled polylines), and a non-neighbour endpoint resting on another edge is a pinch no matter how the sheet
is mirrored or traversed.
"""
import math

import pytest

from drawingto3d.contour_audit import arc_page_ends, audit_contour


def _arc(edge_id, centre, radius, a, b):
    start, end = arc_page_ends(centre, radius, a, b)
    return {"id": edge_id, "kind": "arc", "center": list(centre), "radius": radius, "a": a, "b": b,
            "start": list(start), "end": list(end)}


def _line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def _kinds(result, *wanted):
    return sorted(issue["kind"] for issue in result["issues"] if issue["kind"] in wanted)


def _mirror(edges):
    """The same drawing reflected across the X axis — the verdicts must not change."""
    flipped = []
    for edge in edges:
        copy = dict(edge)
        copy["start"] = [edge["start"][0], -edge["start"][1]]
        copy["end"] = [edge["end"][0], -edge["end"][1]]
        if edge.get("center") is not None:
            copy["center"] = [edge["center"][0], -edge["center"][1]]
            copy["a"], copy["b"] = edge["b"], edge["a"]      # reflection reverses the sweep
        flipped.append(copy)
    return flipped


def _reversed(edges):
    """The same ring walked the other way round, every edge reversed with it."""
    out = []
    for edge in reversed(edges):
        copy = dict(edge)
        copy["start"], copy["end"] = edge["end"], edge["start"]
        if edge.get("center") is not None:
            copy["a"], copy["b"] = edge["b"], edge["a"]
        out.append(copy)
    return out


def test_a_line_through_a_large_arc_finds_both_intersections():
    """F09: R1000 half arc and the line y=999 meet at x = ±sqrt(1999) — two crossings a 32-sample chain
    could not show. The analytic solution must find both, whatever the sampling and tolerance are."""
    arc = _arc("big", (0, 0), 1000, 0.0, -180.0)             # page 0° -> 180°: the lower half
    line = _line("cut", [-50.0, 999.0], [50.0, 999.0])
    result = audit_contour([arc, line])
    crossings = [issue for issue in result["issues"] if issue["kind"] == "self_intersection"]
    assert len(crossings) == 2, result["issues"]
    xs = sorted(issue["at"][0] for issue in crossings)
    assert xs[0] == pytest.approx(-math.sqrt(1999), abs=0.01)
    assert xs[1] == pytest.approx(math.sqrt(1999), abs=0.01)
    for issue in crossings:
        assert issue["at"][1] == pytest.approx(999.0, abs=0.01)
        assert issue["kinds"] == ["arc", "line"]
    loose = audit_contour([arc, line], tolerance_px=2.0)
    assert len([i for i in loose["issues"] if i["kind"] == "self_intersection"]) == 2


def test_a_neighbour_pair_is_checked_beyond_its_shared_joint():
    """P02-c.4: neighbours are not skipped as a pair — their own joint is ignored, nothing else is.

    The arc starts at the line's end (that joint is fine) and comes back through the line's *start* point,
    which is not the joint: it must still be reported."""
    line = _line("l", [0.0, 0.0], [100.0, 0.0])
    arc = _arc("a", (50.0, 0.0), 50.0, 0.0, -270.0)           # page 0° -> 270°, from (100,0) round to (50,0)
    result = audit_contour([line, arc])
    crossings = [issue for issue in result["issues"] if issue["kind"] == "self_intersection"]
    assert len(crossings) == 1, result["issues"]
    assert crossings[0]["at"] == pytest.approx([0.0, 0.0], abs=0.01)
    assert crossings[0]["kinds"] == ["line", "arc"]


def _pinched_ring():
    """A ring whose fourth and fifth edges rest on the first edge's interior at (50,0) — a pinch."""
    return [
        _line("l1", [0.0, 0.0], [100.0, 0.0]),
        _line("l2", [100.0, 0.0], [100.0, 100.0]),
        _line("l3", [100.0, 100.0], [50.0, 0.0]),
        _line("l4", [50.0, 0.0], [0.0, 50.0]),
        _line("l5", [0.0, 50.0], [0.0, 0.0]),
    ]


def test_an_endpoint_touch_on_a_non_neighbour_edge_is_refused():
    """P02-c.5: the simple-ring contract refuses a boundary that only touches itself at a point."""
    result = audit_contour(_pinched_ring())
    assert result["ok"] is False
    touches = [issue for issue in result["issues"] if issue["kind"] == "endpoint_touch"]
    assert touches, result["issues"]
    assert sorted(issue["at"][0] for issue in touches) == [50.0, 50.0]
    assert all("komşu olmayan" in issue["message"] for issue in touches)
    assert "l1" in touches[0]["ids"]


def test_the_touch_verdict_survives_mirroring_and_reverse_traversal():
    """F10: the old decision depended on cross-product signs, so one mirror image passed and the other was
    refused. Reflected and reversed, the pinch must give the *same* verdict and the same kinds."""
    straight = audit_contour(_pinched_ring())
    mirrored = audit_contour(_mirror(_pinched_ring()))
    reversed_ = audit_contour(_reversed(_pinched_ring()))
    for name, result in (("mirror", mirrored), ("reversed", reversed_)):
        assert result["ok"] is False, name
        assert _kinds(result, "endpoint_touch") == _kinds(straight, "endpoint_touch"), name
        assert _kinds(result, "self_intersection") == _kinds(straight, "self_intersection"), name
        assert result["closure_px"] == pytest.approx(straight["closure_px"], abs=1e-9), name


def test_a_valid_ring_stays_valid_mirrored_and_reversed():
    """The control: an ordinary closed ring must pass in all three descriptions — a P02-c fix may not turn
    correct geometry into a refusal."""
    ring = [_line("l1", [0.0, 0.0], [100.0, 0.0]), _line("l2", [100.0, 0.0], [100.0, 80.0]),
            _line("l3", [100.0, 80.0], [0.0, 80.0]), _line("l4", [0.0, 80.0], [0.0, 0.0])]
    for name, edges in (("straight", ring), ("mirror", _mirror(ring)), ("reversed", _reversed(ring))):
        result = audit_contour(edges)
        assert result["ok"] is True, (name, result["issues"])
        assert result["closure_px"] == pytest.approx(0.0, abs=1e-9), name


def test_the_same_line_crossing_the_same_arc_gives_one_verdict_at_any_size():
    """P02-c.6: scale the whole case by 10 and the topological verdict must not change (the numbers are the
    analytic crossings, not samples)."""
    small = audit_contour([_arc("a", (0, 0), 100, 0.0, -180.0), _line("c", [-5.0, 99.9], [5.0, 99.9])])
    large = audit_contour([_arc("a", (0, 0), 1000, 0.0, -180.0), _line("c", [-50.0, 999.0], [50.0, 999.0])])
    assert len([i for i in small["issues"] if i["kind"] == "self_intersection"]) == 2, small["issues"]
    assert len([i for i in large["issues"] if i["kind"] == "self_intersection"]) == 2, large["issues"]


def _cad_arc_ends(center_mm, radius_mm, start_degrees, end_degrees):
    """CAD's own arc ends: `geo.py` samples an arc as center + radius*(cos, sin) of the CAD angles."""
    ends = []
    for angle in (start_degrees, end_degrees):
        radians = math.radians(angle)
        ends.append((center_mm[0] + radius_mm * math.cos(radians),
                     center_mm[1] + radius_mm * math.sin(radians)))
    return ends


def test_the_audit_and_cad_agree_on_where_an_arc_begins_and_ends():
    """PLAN §7 P02-c mandatory acceptance: an independent comparison against CAD's arc ends.

    The CAD side is fed exactly what the plan builder feeds it (`guided.py:801`: the arc entity's angles are
    the edge's canonical `a`/`b`; its centre goes through `xy()` at `guided.py:788` — origin = (min x, max y)
    of the traced profile, sheet Y flipped — and its radius through `value()` at `guided.py:801`, px/scale).
    CAD then computes the ends from those angles with its own arithmetic (`geo.py`: center + radius*(cos, sin)).
    Whatever the audit calls an arc's ends must land on the same points, or the two sides are drawing
    different arcs while both report success.
    """
    scale = 4.0                                            # px per mm, as the calibration would give
    origin = (20.0, 80.0)                                  # min x, max y of the profile in sheet pixels
    edge = _arc("a1", (100.0, 40.0), 30.0, 30.0, 210.0)     # canonical pair, page ends from arc_page_ends

    def page_to_cad(point):
        return ((point[0] - origin[0]) / scale, (origin[1] - point[1]) / scale)

    centre_cad = page_to_cad(edge["center"])
    radius_cad = edge["radius"] / scale
    cad_start, cad_end = _cad_arc_ends(centre_cad, radius_cad, edge["a"], edge["b"])
    audit_start, audit_end = (page_to_cad(point) for point in arc_page_ends(
        edge["center"], edge["radius"], edge["a"], edge["b"]))
    assert cad_start == pytest.approx(audit_start, abs=1e-9), (cad_start, audit_start)
    assert cad_end == pytest.approx(audit_end, abs=1e-9), (cad_end, audit_end)
    # And the sweep sense agrees: the page-space sweep is the negative of the CAD sweep (Y flip).
    page_sweep = math.atan2(audit_end[1] - centre_cad[1], audit_end[0] - centre_cad[0]) - \
        math.atan2(audit_start[1] - centre_cad[1], audit_start[0] - centre_cad[0])
    cad_sweep = math.radians(edge["b"] - edge["a"])
    assert math.sin(page_sweep) == pytest.approx(-math.sin(cad_sweep), abs=1e-9)
    assert math.cos(page_sweep) == pytest.approx(math.cos(cad_sweep), abs=1e-9)
