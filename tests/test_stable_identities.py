"""PLAN §8.7/§8.8: a binding's end is the edge\'s own identity plus which end — never an index.

The same decision must resolve to the same edge even when the contour\'s edge order changes, an old
`edge:<index>` end is honoured only while that edge is still there (and only through the user\'s own click
point), and an id that resolves to nothing asks for a re-binding instead of being mapped to a neighbour.
"""
import math

import pytest

from drawingto3d.guided import Decisions, questions, unresolved_bindings, user_dimensions

SCALE, ORIGIN = 1.0, [0.0, 100.0]


def line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def square(order=("e0", "e1", "e2", "e3")):
    edges = {"e0": line("e0", (0, 0), (100, 0)), "e1": line("e1", (100, 0), (100, 100)),
             "e2": line("e2", (100, 100), (0, 100)), "e3": line("e3", (0, 100), (0, 0))}
    return {"id": "outline_0", "kind": "wire", "join_max_px": 0.0, "points": [],
            "edges": [edges[key] for key in order]}


def options():
    return {"frame": {"width": 400, "height": 400}, "profiles": [square()], "circles": [],
            "measurements": [{"id": "t0", "text": "60,00"}]}


def end(edge_id, point):
    return {"kind": "vertex", "id": edge_id, "x": point[0], "y": point[1]}


def decisions(bindings):
    return Decisions.model_validate({"calibration": {"first": [0, 0], "second": [100, 0], "value": 100.0,
                                                     "unit": "mm", "span_id": None},
                                     "profile_id": "outline_0", "thickness": 10.0, "holes": [],
                                     "bindings": bindings, "trace_acknowledged": True})


def tie(value, first, second):
    return {"id": "b0", "value": value, "unit": "mm", "span_id": "t0", "axis": "x", "direction": 1,
            "first": first, "second": second}


def span_between(profile, first_edge, second_edge, first_end="start", second_end="start"):
    by_id = {e["id"]: e for e in profile["edges"]}
    a = by_id[first_edge][first_end]
    b = by_id[second_edge][second_end]
    return math.dist([float(v) for v in a], [float(v) for v in b]) / SCALE


def test_the_same_decision_keeps_its_edge_when_the_chain_order_changes():
    """e0\'s start is at index 0 in one contour and index 3 in the rotated one; the tie must follow e0."""
    forward = square()
    report = user_dimensions(forward, options(),
                             decisions([tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))]),
                             SCALE, ORIGIN)
    assert report["status"] != "conflict"
    assert span_between(forward, "e0", "e1") == pytest.approx(60.0, abs=1e-6)

    rotated = square(("e1", "e2", "e3", "e0"))
    report = user_dimensions(rotated, options(),
                             decisions([tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))]),
                             SCALE, ORIGIN)
    assert report["status"] != "conflict"
    assert span_between(rotated, "e0", "e1") == pytest.approx(60.0, abs=1e-6)


def test_a_legacy_index_end_resolves_through_the_users_own_click():
    """Pre-P03 records say `edge:1`; the stored click sat on e1\'s far end, so that is the vertex it keeps."""
    profile = square()
    report = user_dimensions(profile, options(),
                             decisions([tie(60.0, end("e0:start", (0, 0)), end("edge:1", (100, 100)))]),
                             SCALE, ORIGIN)
    assert report["status"] != "conflict"
    # The tie is an *axis* measure (x): it fixes the horizontal difference, and the other coordinate stays
    # the traced one — so the diagonal is sqrt(60² + 100²), not 60.
    by_id = {e["id"]: e for e in profile["edges"]}
    dx = abs(by_id["e1"]["end"][0] - by_id["e0"]["start"][0]) / SCALE
    assert dx == pytest.approx(60.0, abs=1e-6)
    assert span_between(profile, "e0", "e1", second_end="end") == pytest.approx(math.hypot(60.0, 100.0), abs=1e-6)


def test_an_end_that_resolves_to_nothing_asks_for_a_rebinding():
    parsed = decisions([tie(60.0, end("e0:start", (0, 0)), end("e9:start", (100, 0)))])
    stale = unresolved_bindings(options(), parsed)
    assert stale and stale[0]["reason"].startswith("e9:start"), stale
    with pytest.raises(ValueError, match="artık bu konturda yok"):
        user_dimensions(square(), options(), parsed, SCALE, ORIGIN)

    legacy = decisions([tie(60.0, end("e0:start", (0, 0)), end("edge:9", (100, 0)))])
    stale = unresolved_bindings(options(), legacy)
    assert stale and "edge:9" in stale[0]["reason"], stale


def test_switching_profile_makes_the_old_ties_ask_for_a_rebinding():
    """The tie names an edge of the contour it was bound on; under another contour it resolves to nothing —
    asked about, never quietly moved to that other contour's nearest corner."""
    other = {"id": "outline_1", "kind": "wire", "join_max_px": 0.0, "points": [],
             "edges": [line("z0", (0, 0), (50, 0)), line("z1", (50, 0), (50, 50)),
                       line("z2", (50, 50), (0, 50)), line("z3", (0, 50), (0, 0))]}
    opts = options()
    opts["profiles"].append(other)
    parsed = decisions([tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))])
    assert unresolved_bindings(opts, parsed) == []
    changed = parsed.model_copy(update={"profile_id": "outline_1"})
    stale = unresolved_bindings(opts, changed)
    assert len(stale) == 2, stale
    assert all("bu konturda olan bir nokta değil" in row["reason"] for row in stale), stale
    with pytest.raises(ValueError, match="artık bu konturda yok"):
        user_dimensions(other, opts, changed, SCALE, ORIGIN)


def test_the_direction_puts_the_second_end_on_the_side_the_user_chose():
    """Axis x with direction +1 fixes second = first + 60; direction -1 fixes second = first - 60. The side is
    the user's decision, not a guess from the click order."""
    forward = square()
    user_dimensions(forward, options(),
                    decisions([tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))]), SCALE, ORIGIN)
    by_id = {e["id"]: e for e in forward["edges"]}
    assert by_id["e1"]["start"][0] - by_id["e0"]["start"][0] == pytest.approx(60.0, abs=1e-6)

    backward = square()
    flipped = tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))
    flipped["direction"] = -1
    user_dimensions(backward, options(), decisions([flipped]), SCALE, ORIGIN)
    by_id = {e["id"]: e for e in backward["edges"]}
    assert by_id["e1"]["start"][0] - by_id["e0"]["start"][0] == pytest.approx(-60.0, abs=1e-6)


def test_no_contour_chosen_is_an_ask_not_a_crash():
    """A0.2: with no contour chosen the ties that name contour geometry cannot be resolved — each is reported
    with that reason (and the flow asks for a contour), instead of the save path raising a `None.get`."""
    parsed = decisions([tie(60.0, end("e0:start", (0, 0)), end("e1:start", (100, 0)))])
    without = parsed.model_copy(update={"profile_id": None})
    stale = unresolved_bindings(options(), without)
    assert len(stale) == 2, stale
    assert all("kontur seçilmemiş" in row["reason"] for row in stale), stale
    asks = questions(without, None, options())
    assert any("dış konturu seçin" in ask for ask in asks), asks
