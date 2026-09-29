"""PLAN 8.6-c-2: a confirmed view is *applied*, so the sheet's own axes are the part's axes.

The corpus has no rotated sheet, so the evidence here is synthetic and says so: the same physical sheet,
drawn upright in one record and turned a quarter turn in the other, must produce the same plan parameters —
because the sheet's own frame did not change when it was turned on the page. The mapping runs on the build's
own deep copy, and the identity view must leave every number exactly where it was.
"""
from pathlib import Path

import pytest

from drawingto3d.guided import (Decisions, GuidedStore, _view_map, drawing_options, is_page_identity,
                                 make_plan, view_transform)
from drawingto3d.observe import Frame, Observations, Primitive, SourceRef

SCALE = 2.0  # px per mm, as in the other synthetic sessions


def _line(pid, start, end):
    return Primitive(id=pid, path_id="synthetic", kind="line", start=list(start), end=list(end),
                     method="two-point")


def _sheet(*, transpose=False, rotation=0, border=True):
    """The same sheet, either as drawn or turned a quarter turn on the page (page (x,y) -> (y,x))."""
    def place(point):
        x, y = float(point[0]), float(point[1])
        return [y, x] if transpose else [x, y]

    primitives = [_line("g0", place((20, 20)), place((120, 20))), _line("g1", place((120, 20)), place((120, 80))),
                  _line("g2", place((120, 80)), place((20, 80))), _line("g3", place((20, 80)), place((20, 20)))]
    if border:
        for i, (start, end) in enumerate(((place((10, 10)), place((290, 10))), (place((290, 10)), place((290, 190))),
                                          (place((290, 190)), place((10, 190))), (place((10, 190)), place((10, 10))))):
            primitives.append(_line(f"b{i}", start, end))
    width, height = (200, 300) if transpose else (300, 200)
    observations = Observations(source=SourceRef(ref="synthetic.pdf", sha256="0" * 64, rotation=rotation),
                                frame=Frame(width=width, height=height), text_placement="as-is",
                                primitives=primitives)
    return observations, place


def _record(tmp_path, *, transpose=False, rotation=0, view=None, name="session", border=True):
    from drawingto3d import guided
    from drawingto3d.guided import _atomic

    observations, place = _sheet(transpose=transpose, rotation=rotation, border=border)
    options = drawing_options(observations)
    wire = next(p["id"] for p in options["profiles"] if p["kind"] == "wire")
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    decisions = {"calibration": {"first": place((20, 20)), "second": place((120, 20)), "value": 50, "unit": "mm"},
                 "profile_id": wire, "thickness": 10.0, "trace_acknowledged": True}
    if view is not None:
        decisions["view"] = view
    record = {"version": 1, "geometry_version": guided.GEOMETRY_VERSION, "token": "a" * 32, "revision": 0,
              "source": "synthetic.pdf", "source_sha256": observations.source.sha256, "options": options,
              "decisions": decisions, "history": [], "build": None}
    _atomic(folder / "session.json", record)
    return record


def _edge_vectors(plan):
    """The plan's contour as geometry: each edge's (dx, dy) in mm, in a chain-order-independent order.

    Parameter *names* follow the chain — a turned sheet starts its loop at another corner — so comparing
    names would compare bookkeeping. Comparing the edge vectors compares the part.
    """
    import re

    values = {name: float(row.value) for name, row in plan.parameters.items()}
    edges = {}
    for name, value in values.items():
        match = re.fullmatch(r"edge_(\d+)_(start|end)_([xy])", name)
        if match:
            edges.setdefault(int(match.group(1)), {})[(match.group(2), match.group(3))] = value
    vectors = []
    for index, row in sorted(edges.items()):
        dx = row[("end", "x")] - row[("start", "x")]
        dy = row[("end", "y")] - row[("start", "y")]
        vectors.append((round(dx, 6), round(dy, 6), round((dx * dx + dy * dy) ** 0.5, 6)))
    return sorted(vectors)


def _parameters(plan):
    return {name: round(float(row.value), 9) for name, row in plan.parameters.items()}


def test_a_rotated_sheet_builds_the_same_plan_as_the_upright_one(tmp_path):
    upright = _record(tmp_path, name="upright")
    turned = _record(tmp_path, transpose=True, rotation=90, name="turned",
                     view={"x_page": [0.0, 1.0], "y_page": [1.0, 0.0], "source": "sheet_frame"})

    assert is_page_identity(view_transform(Decisions.model_validate(turned["decisions"]), turned["options"])) is False
    upright_plan, turned_plan = make_plan(upright), make_plan(turned)

    assert _edge_vectors(turned_plan) == _edge_vectors(upright_plan)
    assert turned_plan.parameters["thickness"].value == upright_plan.parameters["thickness"].value == 10.0
    assert len([name for name in turned_plan.parameters if name.startswith("edge_")]) == \
           len([name for name in upright_plan.parameters if name.startswith("edge_")])


def test_a_mirror_view_is_refused_instead_of_built(tmp_path):
    """A pair whose cross product points the wrong way describes the sheet from behind: refused, not built."""
    record = _record(tmp_path, border=False)
    mirrored = Decisions.model_validate({"view": {"x_page": [1.0, 0.0], "y_page": [0.0, 1.0],
                                                 "source": "page_axes"}})

    with pytest.raises(ValueError, match="ayna"):
        view_transform(mirrored, record["options"])
    # `make_plan` never reaches that refusal with a mirrored view: the confirmation disagrees with the
    # reading, so the ask ("görüş yeniden onaylanmalı") stops the build first — the same line, one step earlier.
    with pytest.raises(ValueError, match="uyuşmuyor"):
        make_plan({**record, "decisions": {**record["decisions"], **mirrored.model_dump(mode="json")}})


def test_the_identity_view_leaves_every_parameter_where_it_was(tmp_path):
    """The upright path must not move a single number — the mapping is for rotated sheets only."""
    obvious = _record(tmp_path, name="obvious")
    confirmed = _record(tmp_path, name="confirmed",
                        view={"x_page": [1.0, 0.0], "y_page": [0.0, -1.0], "source": "sheet_frame"})

    assert is_page_identity(view_transform(Decisions.model_validate(confirmed["decisions"]),
                                           confirmed["options"])) is True
    assert _parameters(make_plan(confirmed)) == _parameters(make_plan(obvious))


def test_the_mapping_moves_points_and_turns_canonical_arc_angles():
    """Unit-level proof of the two halves of the mapping, including arcs (end-to-end arcs stay untested)."""
    observations, _ = _sheet(border=False)
    options = drawing_options(observations)
    options["profiles"][0]["edges"] = [{"id": "e0", "kind": "arc", "center": [70.0, 50.0], "radius": 20.0,
                                        "start": [70.0, 30.0], "end": [90.0, 50.0], "a": 90.0, "b": 0.0}]
    decisions = Decisions.model_validate({"calibration": {"first": [20, 20], "second": [120, 20], "value": 50,
                                                         "unit": "mm"},
                                          "bindings": [{"id": "b0", "value": 10.0, "unit": "mm", "axis": "x",
                                                        "direction": 1,
                                                        "first": {"kind": "vertex", "id": "e0:start", "x": 70.0, "y": 30.0},
                                                        "second": {"kind": "vertex", "id": "e0:end", "x": 90.0, "y": 50.0}}],
                                          "view": {"x_page": [0.0, 1.0], "y_page": [1.0, 0.0],
                                                   "source": "sheet_frame"}})
    axes = view_transform(decisions, options)
    mapped = _view_map(options, decisions, axes)

    edge = options["profiles"][0]["edges"][0]
    # The mapped frame stays page-like: u = p·x_axis = earlier page y, v = -(p·y_axis) = -(earlier page x).
    assert edge["center"] == [50.0, -70.0]
    assert edge["start"] == [30.0, -70.0] and edge["end"] == [50.0, -90.0]
    # Canonical angles are page-frame angles, so the sheet's quarter turn shifts them by +turn_page = 90.
    assert (edge["a"] + 360.0) % 360.0 == pytest.approx(180.0)
    assert edge["b"] == pytest.approx(90.0)
    assert [mapped.bindings[0].first.x, mapped.bindings[0].first.y] == [30.0, -70.0]
    assert mapped.calibration.first == [20.0, -20.0]
    assert mapped.calibration.second == [20.0, -120.0]
