"""P02's mandatory test matrix (PLAN.md §7, line "Zorunlu test matrisi"), as small independent inputs.

Each case states its expected result first: a *valid* contour must pass, an *invalid* one must be rejected
with the right diagnosis and the edge ids involved. Geometry only — no file names, no sheet data.

Covered: two complementary half-arcs (valid) — same arc twice (rejected) — arcs crossing the 0° boundary
(valid) — reversed direction on the same support (rejected, and named as reversed) — a real line-arc
crossing — a real arc-arc crossing — a valid shared corner — a broken ring whose non-neighbour edge cuts
through — an interior 2 px gap with a closed wrap join — a stored arc end that disagrees with its own
definition.
"""
import math

import pytest

from drawingto3d.contour_audit import audit_contour

CENTRE = (200.0, 200.0)
RADIUS = 100.0


def _arc(edge_id, a, b, start_degrees, centre=CENTRE, radius=RADIUS):
    """An arc exactly as the flow stores it: start/end points plus the sheet's canonical angle pair."""
    start = [centre[0] + radius * math.cos(math.radians(start_degrees)),
             centre[1] + radius * math.sin(math.radians(start_degrees))]
    sweep = -math.radians(b - a)
    end_angle = math.radians(start_degrees) + sweep
    end = [centre[0] + radius * math.cos(end_angle), centre[1] + radius * math.sin(end_angle)]
    return {"id": edge_id, "kind": "arc", "center": list(centre), "radius": radius, "a": a, "b": b,
            "start": start, "end": end}


def _line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def _kinds(result, kind):
    return [issue for issue in result["issues"] if issue["kind"] == kind]


def test_same_arc_twice_is_rejected_as_a_duplicate():
    """Expected: the same arc riding the same support twice is an overlap, and both ids are named."""
    first = _arc("d0", 0.0, -180.0, 0.0)
    second = _arc("d1", 0.0, -180.0, 0.0)
    result = audit_contour([first, second])
    overlaps = _kinds(result, "overlap")
    assert overlaps, result["issues"]
    assert set(overlaps[0]["ids"]) == {"d0", "d1"}
    assert "ters yön" not in overlaps[0]["message"]          # same direction: a duplicate, not reversed


def test_arcs_crossing_the_zero_degree_boundary_are_valid():
    """Expected: two arcs meeting at 10° and 350° close the circle — they only touch at their endpoints."""
    # P02-a.3: the canonical pair must describe the arc the stored points show. Page angle = -canonical,
    # so a stored 350° start means a = 10°; the sweeps stay +20° and +340°.
    over_zero = _arc("z0", 10.0, -10.0, 350.0)               # 350° -> 10°
    the_rest = _arc("z1", -10.0, -350.0, 10.0)               # 10° -> 350°
    result = audit_contour([over_zero, the_rest])
    assert result["closure_px"] == pytest.approx(0.0, abs=1e-6)
    assert result["ok"] is True, result["issues"]


def test_reversed_direction_on_the_same_support_is_named():
    """Expected: the same angular stretch travelled the other way is rejected *and* named "ters yön" —
    §7.6 asks for reversed overlap to be a distinct diagnosis from a duplicated edge."""
    forward = _arc("r0", 0.0, -180.0, 0.0)                   # 0° -> 180°  (page sweep +180°)
    backward = _arc("r1", -180.0, 0.0, 180.0)                # 180° -> 0°  (page sweep -180°)
    result = audit_contour([forward, backward])
    overlaps = _kinds(result, "overlap")
    assert overlaps, result["issues"]
    assert "ters yön" in overlaps[0]["message"]


def test_line_arc_crossing_is_reported():
    """Expected: a line cutting through an arc's middle is a self-intersection of kinds line-arc."""
    bottom_half = _arc("h0", 0.0, -180.0, 0.0)               # right -> bottom -> left
    cutter = _line("L0", (200.0, 150.0), (200.0, 400.0))     # vertical through the centre
    result = audit_contour([bottom_half, cutter])
    crossings = _kinds(result, "self_intersection")
    assert crossings, result["issues"]
    assert sorted(crossings[0]["kinds"]) == ["arc", "line"]


def test_arc_arc_crossing_is_reported():
    """Expected: an arc of another circle that really cuts this one is a self-intersection of kinds
    arc-arc. Circles: c=(200,200) r=100 and c=(200,260) r=60 cross at (144.7, 283.3) and (255.3, 283.3),
    both mid-arc for the two halves used here."""
    bottom_half = _arc("h0", 0.0, -180.0, 0.0)
    other = _arc("k0", 0.0, -180.0, 0.0, centre=(200.0, 260.0), radius=60.0)
    result = audit_contour([bottom_half, other])
    crossings = _kinds(result, "self_intersection")
    assert crossings, result["issues"]
    assert sorted(crossings[0]["kinds"]) == ["arc", "arc"]


def test_a_valid_shared_corner_is_not_a_crossing():
    """Expected: neighbours that share an endpoint — a closed triangle — pass cleanly."""
    edges = [_line("t0", (0, 0), (100, 0)),
             _line("t1", (100, 0), (100, 100)),
             _line("t2", (100, 100), (0, 0))]
    result = audit_contour(edges)
    assert result["closure_px"] == pytest.approx(0.0, abs=1e-6)
    assert result["ok"] is True, result["issues"]


def test_broken_ring_where_a_non_neighbour_edge_cuts_through():
    """Expected: closure is perfect (0.0) yet the ring crosses itself — e2 cuts e0 in the middle and the
    pair (0, 2) is *not* a neighbouring pair, so this must be rejected."""
    edges = [_line("e0", (0, 0), (100, 0)),
             _line("e1", (100, 0), (100, 100)),
             _line("e2", (100, 100), (20, -20)),
             _line("e3", (20, -20), (0, 0))]
    result = audit_contour(edges)
    assert result["closure_px"] == pytest.approx(0.0, abs=1e-6)
    crossings = _kinds(result, "self_intersection")
    assert crossings, result["issues"]
    assert {"e0", "e2"} in [set(issue["ids"]) for issue in crossings]


def test_interior_two_pixel_gap_with_a_closed_wrap_join():
    """Expected: the honest closure is the largest join gap (2 px), and that join is the single open
    issue — the closed wrap join must not overwrite it."""
    edges = [_line("e0", (0, 0), (100, 0)),
             _line("e1", (102, 0), (200, 0)),
             _line("e2", (200, 0), (0, 0))]
    result = audit_contour(edges)
    assert [issue["gap_px"] for issue in _kinds(result, "open")] == [2.0]
    assert result["closure_px"] == pytest.approx(2.0, abs=0.01)


def test_stored_arc_end_that_disagrees_with_its_own_definition():
    """Expected: an arc whose stored end is not the point its centre/radius/sweep produce is diagnosed."""
    arc = _arc("m0", 0.0, -180.0, 0.0)
    arc["end"] = [150.0, 200.0]                              # 50 px away from the arc's real end
    result = audit_contour([arc, _line("m1", (150.0, 200.0), (300.0, 200.0))])
    mismatches = _kinds(result, "arc_end_mismatch")
    assert mismatches, result["issues"]
    assert mismatches[0]["ids"] == ["m0"]


def test_zero_length_edge_and_a_broken_chain_are_separate_diagnoses():
    """Expected (§7.6): a zero-length edge is `zero_length`; a chain that does not close is `open` with
    both edge ids — never one merged "something is wrong"."""
    edges = [_line("z0", (0, 0), (0, 0)),
             _line("z1", (40, 0), (100, 0))]                 # a 40 px gap between z0.end and z1.start
    result = audit_contour(edges)
    assert [issue["ids"] for issue in _kinds(result, "zero_length")] == [["z0"]]
    opens = _kinds(result, "open")
    assert opens and opens[0]["ids"] == ["z0", "z1"] and opens[0]["gap_px"] == pytest.approx(40.0, abs=0.01)


def test_the_same_canonical_half_twice_with_different_stored_points_is_refused():
    """P02-a.2/.4: two arcs whose canonical pair is the same may not carry stored ends from two different
    halves — that record contradicts itself and must be refused explicitly, not silently passed."""
    first = _arc("c0", 0.0, -180.0, 0.0)                     # canonical: right -> bottom -> left
    second = _arc("c1", 0.0, -180.0, 0.0)                    # same canonical pair ...
    second["start"] = [100.0, 200.0]                         # ... but stored as the *other* half
    second["end"] = [300.0, 200.0]
    result = audit_contour([first, second])
    assert result["ok"] is False
    assert _kinds(result, "arc_start_mismatch") and _kinds(result, "arc_end_mismatch"), result["issues"]
    assert _kinds(result, "arc_start_mismatch")[0]["ids"] == ["c1"]


def test_a_sweep_of_zero_or_a_full_turn_is_not_an_arc():
    """P02-a.5: zero and ±360 sweeps are refused with their own diagnosis — a full turn is a `circle`, and
    nothing may fold a full circle into a zero-sweep arc."""
    zero = _arc("q0", 0.0, 0.0, 0.0)
    turn = _arc("q1", 0.0, -360.0, 0.0)
    result = audit_contour([zero, turn])
    assert result["ok"] is False
    assert _kinds(result, "arc_zero_sweep") and _kinds(result, "arc_full_turn"), result["issues"]
    assert "circle" in _kinds(result, "arc_zero_sweep")[0]["message"]
    assert "circle" in _kinds(result, "arc_full_turn")[0]["message"]
