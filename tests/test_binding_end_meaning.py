"""P03-b: a tie's end knows where and when it was chosen (PLAN.md 8 P03-b).

Expected results first: the same edge id in another contour is *not* the same end, and a contour walked the
other way round (which swaps every `start`/`end` label) must keep tying to the corner the user clicked.
"""
import math

from drawingto3d.guided import Binding, BindingEnd, Decisions, unresolved_bindings, resolve_binding_end


def _line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def _ring(prefix=""):
    return [_line(prefix + "e0", (0, 0), (100, 0)), _line(prefix + "e1", (100, 0), (100, 60)),
            _line(prefix + "e2", (100, 60), (0, 60)), _line(prefix + "e3", (0, 60), (0, 0))]


def _profile(profile_id, edges):
    return {"id": profile_id, "kind": "wire", "join_max_px": 0.0, "points": [], "edges": edges}


def _options(*profiles):
    return {"frame": {"width": 300, "height": 200}, "measurements": [], "circles": [],
            "profiles": list(profiles), "contours": list(profiles)}


def _end(edge_id, point, profile=None, label=None):
    return BindingEnd(kind="vertex", id=edge_id, x=float(point[0]), y=float(point[1]),
                      profile=profile, geometry_version=3, end=label)


def _tie(first, second):
    return Binding(id="b0", value=40.0, unit="mm", span_id=None, axis="x", direction=1,
                   first=first, second=second)


def test_the_same_edge_id_in_another_contour_is_not_the_same_end():
    """P03-b.2: ids are text. Two contours can both contain an edge called `e0`; a tie recorded in one of them
    must ask for re-binding in the other, even though the id resolves there."""
    here = _profile("outline_0", _ring())
    there = _profile("outline_1", _ring(""))
    options = _options(here, there)
    recorded = Decisions(profile_id="outline_0",
                         bindings=[_tie(_end("e0:start", (0, 0), profile="outline_0", label="start"),
                                        _end("e1:start", (100, 0), profile="outline_0", label="start"))])
    assert unresolved_bindings(options, recorded) == []

    moved = recorded.model_copy(update={"profile_id": "outline_1"})
    stale = unresolved_bindings(options, moved)
    assert len(stale) == 2, stale
    assert all("başka bir konturda seçilmiş" in row["reason"] for row in stale), stale

    # The honest limit: a record from before the field existed carries no contour, so nothing protects it —
    # that is why the field has to be written from now on (P03-b-2, the flow's own end).
    unrecorded = Decisions(profile_id="outline_1",
                           bindings=[_tie(_end("e0:start", (0, 0)), _end("e1:start", (100, 0)))])
    assert unresolved_bindings(options, unrecorded) == []


def test_a_reversed_contour_keeps_the_corner_the_user_clicked():
    """P03-b.2: walking the contour the other way round swaps every label. The tie must still land on the
    corner the user clicked, and must not be reported as stale."""
    forward = _profile("outline_2", _ring())
    reversed_edges = [_line("e3", (0, 0), (0, 60)), _line("e2", (0, 60), (100, 60)),
                      _line("e1", (100, 60), (100, 0)), _line("e0", (100, 0), (0, 0))]
    backward = _profile("outline_2", reversed_edges)
    tie = _tie(_end("e0:start", (0, 0), profile="outline_2", label="start"),
               _end("e2:start", (100, 60), profile="outline_2", label="start"))
    decisions = Decisions(profile_id="outline_2", bindings=[tie])
    assert unresolved_bindings(_options(forward), decisions) == []
    assert unresolved_bindings(_options(backward), decisions) == []

    # The index may differ between the two descriptions — in the reversed ring `e0` sits at another position
    # — but the *corner* must not: whatever vertex comes back must stand on the point the user clicked.
    for label, description in (("forward", forward), ("backward", backward)):
        name, reason = resolve_binding_end(description["edges"], tie.first)
        assert reason is None, (label, reason)
        index = int(name[1:])
        assert description["edges"][index]["start"] == [0.0, 0.0], (label, name)


def test_a_click_that_no_longer_lands_on_its_edge_is_asked_about():
    """P03-c: the reference is checked against the contour as it is *now*. When the edge has been edited so
    the click no longer lands on either of its ends, the tie is reported — never slid to the nearest corner."""
    edges = _ring()
    mid = _end("e0:start", (50.0, 0.0), profile="outline_0", label="start")
    name, reason = resolve_binding_end(edges, mid)
    assert name is None and "uçlarında değil" in reason, reason
    decisions = Decisions(profile_id="outline_0", bindings=[_tie(mid, _end("e1:start", (100, 0), profile="outline_0"))])
    stale = unresolved_bindings(_options(_profile("outline_0", edges)), decisions)
    assert len(stale) == 1 and stale[0]["end"] == "first", stale


def test_the_flow_writes_the_end_evidence_when_a_record_is_saved(tmp_path):
    """P03-b-2: the fields only matter if the flow writes them. A save must pin each end to the contour it
    was chosen in, the geometry version it was chosen against, and the physical end that was clicked."""
    from pathlib import Path as _Path

    from drawingto3d.guided import GuidedStore

    plate = _Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
    store = GuidedStore(tmp_path / "store")
    token = store.create(plate.read_bytes())["token"]
    state = store.load(token)
    profile = next(p for p in state["options"]["profiles"] if len(p.get("edges") or []) >= 2)
    edge = profile["edges"][0]
    first_end = {"kind": "vertex", "id": edge["id"] + ":start",
                 "x": float(edge["start"][0]), "y": float(edge["start"][1])}
    second_end = {"kind": "vertex", "id": edge["id"] + ":end",
                  "x": float(edge["end"][0]), "y": float(edge["end"][1])}
    binding = {"id": "b0", "value": 30.0, "unit": "mm", "span_id": None, "axis": "x", "direction": 1,
               "first": first_end, "second": second_end}
    decisions = {"calibration": {"first": [200.0, 100.0], "second": [500.0, 100.0], "value": 80.0, "unit": "mm"},
                 "profile_id": profile["id"], "thickness": 15.0, "holes": [], "trace_acknowledged": True,
                 "bindings": [binding]}
    saved = store.save(token, 0, decisions)
    first = saved["decisions"]["bindings"][0]["first"]
    assert first["profile"] == profile["id"], first
    assert first["geometry_version"] == state["geometry_version"], first
    assert first["end"] == "start", first
    assert saved["decisions"]["bindings"][0]["second"]["end"] == "end", saved["decisions"]["bindings"][0]
    reopened = store.load(token)
    assert reopened["decisions"]["bindings"][0]["first"]["profile"] == profile["id"]
    assert any("bağ ucunun kanıtı" in row.get("note", "") for row in reopened["log"]), reopened["log"][-3:]
