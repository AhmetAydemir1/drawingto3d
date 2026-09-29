"""P00 repeats (PLAN.md §5.6), kept as P02's own geometry tests.

The expected result is written here **first**; the current wrong output was never treated as the
expectation. Both defect repeats started as `xfail(strict=True)`; P02's fix removed the markers, so these
are now plain assertions.

Defect (a): two half-arcs that together make a full circle were counted as "overlapping" because
`_overlap_extent` projected an arc's sampled points onto its *chord* — both halves of a circle share the
same chord, so their projections overlapped even though the arcs only meet at their two endpoints.
Fixed by comparing angular spans instead.

Defect (b): `audit_contour`'s closure loop recorded `max(...)` for every join except the last, where it
*assigned* the wrap gap — so a contour with an 8 px open join inside could report `closure_px = 0.0`.
Fixed to `max(...)` for every join.
"""
import math

import pytest

from drawingto3d.contour_audit import audit_contour
from drawingto3d.contour_audit import arc_page_ends


def _arc(edge_id, centre, radius, a, b, start_degrees):
    """One arc exactly as the flow stores it: start/end points plus the sheet's canonical angle pair."""
    start = [centre[0] + radius * math.cos(math.radians(start_degrees)),
             centre[1] + radius * math.sin(math.radians(start_degrees))]
    sweep = -math.radians(b - a)
    end_angle = math.radians(start_degrees) + sweep
    end = [centre[0] + radius * math.cos(end_angle), centre[1] + radius * math.sin(end_angle)]
    return {"id": edge_id, "kind": "arc", "center": list(centre), "radius": radius, "a": a, "b": b,
            "start": start, "end": end}


def _line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def test_defect_two_half_arcs_making_a_circle_are_not_an_overlap():
    """The P00 defect repeat. Expected (stated first, as PLAN §5.6 requires): a full circle drawn as two
    half-arcs is a *closed valid* contour — no overlap issue. The halves meet only at (300,200) and
    (100,200); their chords are the same diameter, which is what the current projection test mistakes for
    shared span."""
    down_half = _arc("h0", (200, 200), 100, 0.0, -180.0, 0.0)       # right -> bottom -> left
    # P02-a.3: the second half needs its **own** canonical pair. Both halves stated as (0, -180) made the
    # canonical definition describe the first half twice while the stored points described the second — the
    # audit used to read the angles off the stored point, so the inconsistency was invisible (F07).
    up_half = _arc("h1", (200, 200), 100, 180.0, 0.0, 180.0)        # left -> top -> right
    for edge, (start, end) in ((down_half, ((300, 200), (100, 200))),
                               (up_half, ((100, 200), (300, 200)))):
        canonical = arc_page_ends(edge["center"], edge["radius"], edge["a"], edge["b"])
        assert canonical[0] == pytest.approx(start) and canonical[1] == pytest.approx(end), edge["id"]
    assert down_half["end"] == pytest.approx(up_half["start"])
    assert up_half["end"] == pytest.approx(down_half["start"])
    result = audit_contour([down_half, up_half])
    assert result["closure_px"] == pytest.approx(0.0, abs=1e-6)
    assert result["ok"] is True, result["issues"]


def test_arcs_that_really_share_a_span_are_still_an_overlap():
    """Control the other way: two arcs riding the same circle with 10° of genuine angular overlap must
    stay flagged — a P02 fix may not simply switch the check off."""
    first = _arc("h0", (200, 200), 100, 0.0, -180.0, 0.0)           # 0° -> 180°
    second = _arc("h1", (200, 200), 100, 0.0, -180.0, 170.0)        # 170° -> 350°
    result = audit_contour([first, second])
    overlaps = [issue for issue in result["issues"] if issue["kind"] == "overlap"]
    assert overlaps, result["issues"]


def test_defect_last_join_must_not_overwrite_the_largest_gap():
    """Expected: the reported closure is the *largest* join gap. Input: one open join of 8 px inside
    (e0.end -> e1.start), both other joins closed, and the wrap join closed — so the honest number for
    `closure_px` is 8.0, with one `open` issue."""
    edges = [_line("e0", (0, 0), (100, 0)),
             _line("e1", (108, 0), (200, 0)),
             _line("e2", (200, 0), (0, 0))]
    result = audit_contour(edges)
    open_issues = [issue for issue in result["issues"] if issue["kind"] == "open"]
    assert [issue["gap_px"] for issue in open_issues] == [8.0]
    assert result["closure_px"] == pytest.approx(8.0, abs=0.01)
