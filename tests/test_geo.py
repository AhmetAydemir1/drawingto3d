"""geo.* runs inside the CadQuery interpreter, so it is exercised through the runner."""

from pathlib import Path

import pytest

from drawingto3d.cadrun import CadFailure, run_program
from drawingto3d.reason import geo_summary


def _sizes(folder: Path) -> list[float]:
    return sorted(float(item) for item in (folder / "measure.txt").read_text().split())


def test_ring_revolve_is_one_bent_tube(tmp_path: Path):
    step, _stl = run_program("solid = geo.ring_revolve(290, 210, 260, 90)\n", tmp_path)
    assert step.is_file()
    assert _sizes(tmp_path) == pytest.approx([290, 405, 405], abs=0.5)


def test_plate_with_counterbored_holes(tmp_path: Path):
    program = (
        "plate = geo.plate(360, 360, 50, 20)\n"
        "solid = geo.holes(plate, geo.rect_points(260), 30, counterbore=(60, 10))\n"
        "assert len(solid.faces('%CYLINDER').vals()) >= 8\n"
        "removed = plate.val().Volume() - solid.val().Volume()\n"
        "import math\n"
        "assert abs(removed - 4 * (math.pi * 15**2 * 40 + math.pi * 30**2 * 10)) < 1\n"
    )
    run_program(program, tmp_path)
    assert _sizes(tmp_path) == pytest.approx([50, 360, 360], abs=0.5)


def test_flanged_elbow_fuses_into_one_solid(tmp_path: Path):
    program = (
        "f1 = geo.holes(geo.plate(360, 360, 50, 20, 'XY'), geo.rect_points(260), 30, counterbore=(60, 10), counterbore_face='bottom')\n"
        "s1 = geo.place(geo.ring_extrude(290, 210, 100, 'XY'), 0, 0, 50)\n"
        "bend = geo.place(geo.ring_revolve(290, 210, 260, 90, 'XY'), 0, 0, 150)\n"
        "s2 = geo.place(geo.ring_extrude(290, 210, 100, 'YZ'), -360, 0, 410)\n"
        "f2 = geo.place(geo.plate(360, 360, 50, 20, 'YZ'), -410, 0, 410)\n"
        "solid = geo.fuse(f1, s1, bend, s2, f2)\n"
    )
    run_program(program, tmp_path)
    assert _sizes(tmp_path) == pytest.approx([360, 590, 590], abs=0.5)


def test_attach_stacks_parts_without_coordinates(tmp_path: Path):
    program = (
        "bend = geo.ring_revolve(290, 210, 260, 90)\n"
        "leg1 = geo.attach(geo.ring_extrude(290, 210, 100), bend, 'start')\n"
        "leg2 = geo.attach(geo.ring_extrude(290, 210, 100), bend, 'end')\n"
        "f1 = geo.attach(geo.holes(geo.plate(360, 360, 50, 20), geo.rect_points(260), 30), leg1, 'end')\n"
        "f2 = geo.attach(geo.holes(geo.plate(360, 360, 50, 20), geo.rect_points(260), 30), leg2, 'end')\n"
        "bb = f2.val().BoundingBox()\n"
        "assert abs(bb.xmin + 410) < 0.5 and abs(bb.xmax + 360) < 0.5, (bb.xmin, bb.xmax)\n"
        "solid = geo.fuse(bend, leg1, leg2, f1, f2)\n"
    )
    run_program(program, tmp_path)
    assert _sizes(tmp_path) == pytest.approx([360, 590, 590], abs=0.5)


def test_attach_refuses_a_fused_base(tmp_path: Path):
    program = (
        "a = geo.fuse(geo.plate(100, 100, 10), geo.attach(geo.plate(50, 50, 20), geo.plate(100, 100, 10), 'end'))\n"
        "solid = geo.attach(geo.plate(10, 10, 10), a, 'end')\n"
    )
    with pytest.raises(CadFailure) as failed:
        run_program(program, tmp_path)
    assert "attach: base has no end faces" in failed.value.stderr


def test_bad_arguments_read_as_one_english_line(tmp_path: Path):
    with pytest.raises(CadFailure) as failed:
        run_program("solid = geo.ring_revolve(210, 290, 260, 90)\n", tmp_path)
    assert "ring_revolve: inner_d must be smaller than outer_d" in failed.value.stderr
    assert "line 1:" in failed.value.stderr
    with pytest.raises(CadFailure) as apart:
        run_program("solid = geo.fuse(geo.plate(10, 10, 10), geo.place(geo.plate(10, 10, 10), 50, 0, 0))\n", tmp_path)
    assert "fuse: result has 2 solids" in apart.value.stderr


def test_summary_lists_signatures_only():
    summary = geo_summary()
    assert "geo.ring_revolve(outer_d, inner_d, bend_radius, angle=90, plane='XY')" in summary
    assert "geo.holes(part, positions, diameter, depth=None, counterbore=None, plane='XY', counterbore_face='top')" in summary
    assert "geo.attach(part, base, end='end')" in summary
    assert "geo._" not in summary
    assert "cq.Workplane(" not in summary
