"""PLAN-25 §60 (P4): exact constraints against a real CAD solid — STEP generated and reopened.

Every scenario goes through the product path (`make_plan` → `build_general`) on a synthetic sheet, because
the claim under test is not "the solver returns numbers" (that core is tested in `test_sketch_constraints`)
but "the part that comes out is the part its printed dimensions describe, and a set that cannot hold builds
nothing". The sheet is drawn at 2 px/mm with a 100 px span the calibration calls 50 mm, so a tie that does
nothing is visible: the traced rectangle is 50 × 30 mm and each test says which of those numbers is allowed
to survive.
"""
import hashlib
import json
import math
from pathlib import Path

import pytest

from drawingto3d import build_strategy
from drawingto3d.general import build_general
from drawingto3d.guided import Decisions, _atomic, drawing_options, make_plan, user_dimensions
from drawingto3d.observe import Frame, Observations, Primitive, SourceRef

SCALE = 2.0


def _line(pid, start, end):
    return Primitive(id=pid, path_id="synthetic", kind="line", start=list(start), end=list(end),
                     method="two-point")


def _circle(pid, centre, radius=8.0):
    return Primitive(id=pid, path_id="synthetic", kind="circle", centre=list(centre), radius=radius,
                     method="least-squares-fit")


def _sheet():
    """One upright sheet: a rectangular part with two holes, and a border so the page frame is found."""
    primitives = [_line("g0", (20, 20), (120, 20)), _line("g1", (120, 20), (120, 80)),
                  _line("g2", (120, 80), (20, 80)), _line("g3", (20, 80), (20, 20)),
                  _circle("c0", (50, 40)), _circle("c1", (90, 40))]
    primitives.extend([_line("b0", (10, 10), (290, 10)), _line("b1", (290, 10), (290, 190)),
                       _line("b2", (290, 190), (10, 190)), _line("b3", (10, 190), (10, 10))])
    observations = Observations(source=SourceRef(ref="synthetic-p4.pdf", sha256="0" * 64, rotation=0),
                                frame=Frame(width=300, height=200), text_placement="as-is",
                                primitives=primitives)
    return observations


def _record(tmp_path, *, bindings=(), holes=(), name="p4"):
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    # The build re-checks the plan's source against the file itself (source hash); a synthetic session
    # therefore has to name a real file, and this one is the sheet the observations describe.
    source = folder / "synthetic-p4.pdf"
    source.write_bytes(json.dumps({"synthetic": "sheet", "session": name}).encode("utf-8"))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    options = drawing_options(_sheet())
    wire = next(p["id"] for p in options["profiles"] if p["kind"] == "wire")
    decisions = {"calibration": {"first": [20, 20], "second": [120, 20], "value": 50, "unit": "mm"},
                 "profile_id": wire, "thickness": 10.0, "trace_acknowledged": True,
                 "bindings": list(bindings), "holes": list(holes)}
    record = {"version": 1, "geometry_version": 21, "token": "a" * 32, "revision": 0,
              "source": str(source), "source_sha256": digest, "options": options,
              "decisions": decisions, "history": [], "build": None}
    record["decisions"]["build_strategy"] = build_strategy.decision_for(record, record["decisions"],
                                                                        "extrude_profile")
    _atomic(folder / "session.json", record)
    return record


def _wire_of(record):
    options = record["options"]
    return next(p for p in options["profiles"] if p["kind"] == "wire")


def _end(edge, which):
    point = edge["start"] if which == "start" else edge["end"]
    return {"kind": "vertex", "id": f"{edge['id']}:{which}", "x": float(point[0]), "y": float(point[1])}


def _centre_end(circle_id, options):
    circle = next(c for c in options["circles"] if c["id"] == circle_id)
    return {"kind": "centre", "id": circle_id, "x": float(circle["center"][0]), "y": float(circle["center"][1])}


def _tie(identifier, value, first, second, unit="mm", axis=None):
    """One confirmed tie. The axis is the user's own decision (PLAN §8.4); `_tie` only guesses it from the
    click delta for the axis-aligned pairs, and a diagonal pair always declares `axis` itself."""
    if axis is None:
        axis = "x" if abs(second["x"] - first["x"]) >= abs(second["y"] - first["y"]) else "y"
    delta = (second["x"] - first["x"]) if axis == "x" else (first["y"] - second["y"])
    return {"id": identifier, "value": value, "unit": unit, "span_id": None, "axis": axis,
            "direction": 1 if delta >= 0 else -1, "first": first, "second": second}


def _corner(record, x, y):
    """The binding end of the traced corner at (x, y), taken from the contour that owns it."""
    for edge in _wire_of(record)["edges"]:
        for which in ("start", "end"):
            point = edge[which]
            if abs(float(point[0]) - x) < 1e-6 and abs(float(point[1]) - y) < 1e-6:
                return {"kind": "vertex", "id": f"{edge['id']}:{which}", "x": float(point[0]),
                        "y": float(point[1])}
    raise AssertionError(f"konturda ({x}, {y}) köşesi yok")


def _facts(tmp_path, record, name="out"):
    plan = make_plan(record)
    step, _ = build_general(plan, Path(record["source"]), tmp_path / name)
    return plan, step, json.loads((tmp_path / name / "geometry.json").read_text(encoding="utf-8"))


def test_rectangle_is_built_at_its_printed_width_and_height(tmp_path):
    """§55/§56: the printed width and height control the coordinates — the traced 50 × 30 mm does not."""
    probe = _record(tmp_path, name="probe")
    v0, v1, v2, v3 = _corner(probe, 20, 20), _corner(probe, 120, 20), _corner(probe, 120, 80), _corner(probe, 20, 80)
    # Six ties — the four sides plus the two cross spans a draughtsman would dimension — leave no corner to
    # the trace: every x and every y comes out of an equation (checked against the audit in the last test).
    bindings = [_tie("width", 60.0, v0, v1),
                _tie("bottom_width", 60.0, v3, v2),
                _tie("left_height", 40.0, v0, v3),
                _tie("right_height", 40.0, v1, v2),
                _tie("cross_width", 60.0, v1, v3),
                _tie("height", 40.0, v0, v2, axis="y")]
    record = _record(tmp_path, bindings=bindings)
    _declared, step, facts = _facts(tmp_path, record)
    assert step.exists() and facts["valid"] and facts["solids"] == 1
    assert facts["size"] == pytest.approx([60.0, 40.0, 10.0], abs=1e-6)
    assert facts["volume"] == pytest.approx(60.0 * 40.0 * 10.0, abs=1e-4)


def test_circle_centres_take_the_tied_spacing(tmp_path):
    """§55: circle centre X and Y spacing are equations between the centres, not a global rescale."""
    probe = _record(tmp_path, name="probe")
    edges = _wire_of(probe)["edges"]
    holes = [{"circle_id": "c0", "kind": "through", "diameter": 6.0, "depth": None},
             {"circle_id": "c1", "kind": "through", "diameter": 6.0, "depth": None}]
    # Both ties are declared by hand: the centres start level with each other, and the user's own confirmed
    # axis (PLAN §8.4) is what makes the 20 mm an x or a y — never the click delta.
    bindings = [_tie("span_x", 30.0, _centre_end("c0", probe["options"]), _centre_end("c1", probe["options"])),
                _tie("span_y", 6.0, _centre_end("c0", probe["options"]), _centre_end("c1", probe["options"]),
                     axis="y")]
    record = _record(tmp_path, bindings=bindings, holes=holes)
    _declared, step, facts = _facts(tmp_path, record)
    assert step.exists() and len(facts["cylinders"]) == 2
    first, second = sorted(facts["cylinders"], key=lambda row: row[1])
    assert (second[1] - first[1]) == pytest.approx(30.0, abs=1e-6)
    assert (second[2] - first[2]) == pytest.approx(6.0, abs=1e-6)


def test_hole_diameter_is_exact_in_the_solid(tmp_path):
    """§55: a printed diameter is a value, not a trace — the opened hole is exactly Ø6, not the traced Ø8."""
    holes = [{"circle_id": "c0", "kind": "through", "diameter": 6.0, "depth": None}]
    record = _record(tmp_path, holes=holes)
    _declared, step, facts = _facts(tmp_path, record)
    assert step.exists() and len(facts["cylinders"]) == 1
    radius, x, y, z_top, z_bottom = facts["cylinders"][0]
    assert radius == pytest.approx(3.0, abs=1e-6)
    assert (z_bottom - z_top if z_bottom > z_top else z_top - z_bottom) == pytest.approx(10.0, abs=1e-6)
    # No ties here, so the part is the traced 50 × 30 mm rectangle and only the hole is the printed Ø6.
    assert facts["size"] == pytest.approx([50.0, 30.0, 10.0], abs=1e-6)
    assert facts["volume"] == pytest.approx(50.0 * 30.0 * 10.0 - math.pi * 3.0 ** 2 * 10.0, abs=1e-3)


def test_a_conflicting_width_refuses_and_names_the_dimensions(tmp_path):
    """§58: no averaging — two widths that cannot both hold stop the revision and name both dimensions."""
    probe = _record(tmp_path, name="probe")
    edges = _wire_of(probe)["edges"]
    bindings = [_tie("width_a", 60.0, _end(edges[0], "start"), _end(edges[0], "end")),
                _tie("width_b", 70.0, _end(edges[0], "start"), _end(edges[0], "end"))]
    record = _record(tmp_path, bindings=bindings)
    with pytest.raises(ValueError) as failure:
        make_plan(record)
    message = str(failure.value)
    assert "tutmuyor" in message and "width_a" in message and "width_b" in message
    assert not list(tmp_path.glob("**/part.step")), "çelişkili ölçüyle STEP üretilmemeli"


def test_underconstrained_draft_counts_its_sources_and_needs_the_trace_acknowledgement(tmp_path):
    """§59: one tie overruns a draft — it builds, its audit names the sources, and it waits for the ack."""
    probe = _record(tmp_path, name="probe")
    edges = _wire_of(probe)["edges"]
    bindings = [_tie("width", 60.0, _end(edges[0], "start"), _end(edges[0], "end"))]
    record = _record(tmp_path, bindings=bindings)
    _declared, step, facts = _facts(tmp_path, record)
    assert step.exists()
    assert facts["size"] == pytest.approx([60.0, 30.0, 10.0], abs=1e-6)     # the tie holds; y stays traced
    profile = json.loads(json.dumps(_wire_of(record)))                       # the solve works on its own copy
    options = record["options"]
    report = user_dimensions(profile, options, Decisions.model_validate(record["decisions"]),
                             SCALE, [min(p[0] for p in profile["points"]), max(p[1] for p in profile["points"])])
    # Twelve coordinate values: the four wire corners and the two hole centres, on both axes.
    assert report is not None and report["audit"] == {"dimension_derived": 1, "trace_derived": 11}
    traced = [row for row in report["coordinates"] if row["source"] == "trace"]
    assert len(traced) == 11 and all(row["steps"] == [] for row in traced)
    # Without the acknowledgement the same draft never starts: the trace assumption is the user's to make.
    unacknowledged = _record(tmp_path, bindings=bindings, name="no-ack")
    unacknowledged["decisions"]["trace_acknowledged"] = False
    with pytest.raises(ValueError) as failure:
        make_plan(unacknowledged)
    assert "taslak olarak kullanmayı onaylayın" in str(failure.value)
