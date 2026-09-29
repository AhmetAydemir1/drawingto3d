"""The raster observer: what CV can measure, what OCR can read, and what the record admits.

A synthetic sheet pins the geometry path end to end — drawn circles and lines must come back as
circles and lines with their measured quality — while the two real sheets pin what the gates do
on real ink: the flange's Ø30 bore and the exercise sheet's Ø20 hole survive, and the record
names its own limits in the notes. The OCR failure path is tested by taking the binary away:
geometry must not depend on it.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

import drawingto3d.raster as raster
from drawingto3d.observe import Unsupported, observe
from drawingto3d.raster import observe_raster

FLANGE = Path("examples/pdf with steps/8/Flange.PNG")
EXERCISE = Path("examples/pdf with steps/7/my_part.jpg")


@pytest.fixture(scope="module")
def flange():
    return observe(FLANGE)


@pytest.fixture(scope="module")
def exercise():
    return observe(EXERCISE)


def _synthetic_sheet(folder: Path) -> Path:
    """A 480x320 sheet: two separated circles and three strokes, drawn with 2-3 px ink."""
    image = np.full((320, 480), 255, dtype=np.uint8)
    cv2.circle(image, (120, 160), 60, 0, 3)
    cv2.circle(image, (350, 200), 25, 0, 3)
    cv2.line(image, (250, 60), (250, 260), 0, 2)
    cv2.line(image, (250, 60), (430, 60), 0, 2)
    cv2.line(image, (430, 60), (430, 260), 0, 2)
    path = folder / "synthetic.png"
    cv2.imwrite(str(path), image)
    return path


def test_synthetic_geometry_comes_back_as_measured(tmp_path):
    observations = observe_raster(_synthetic_sheet(tmp_path))
    assert observations.paths == []  # a raster has no subpaths to cite
    lines = [primitive for primitive in observations.primitives if primitive.kind == "line"]
    circles = [primitive for primitive in observations.primitives if primitive.kind == "circle"]
    assert len(lines) == 3
    assert len(circles) == 2
    outer = max(circles, key=lambda primitive: primitive.radius or 0.0)
    inner = min(circles, key=lambda primitive: primitive.radius or 0.0)
    assert outer.centre is not None and inner.centre is not None
    assert outer.centre[0] == pytest.approx(120, abs=5)
    assert outer.centre[1] == pytest.approx(160, abs=5)  # Hough centres land within ~4 px
    assert outer.radius == pytest.approx(60, abs=3)
    assert inner.centre == pytest.approx([350, 200], abs=5)
    assert inner.radius == pytest.approx(25, abs=3)
    assert outer.coverage is not None and outer.coverage >= 0.85
    assert all(primitive.method == "hough-verified" for primitive in circles)
    assert all(primitive.method == "hough-merged" for primitive in lines)


def test_synthetic_observation_is_deterministic(tmp_path):
    path = _synthetic_sheet(tmp_path)
    first = observe_raster(path)
    second = observe_raster(path)
    assert first.model_dump_json() == second.model_dump_json()


def test_flange_frame_and_no_pdf_frame(flange):
    assert (flange.frame.width, flange.frame.height) == (3300, 2550)
    assert flange.frame.dpi == pytest.approx(300, abs=1)
    assert flange.source.page_size_pt is None
    assert flange.source.rotation == 0


def test_flange_bore_survives_the_gates(flange):
    circles = [primitive for primitive in flange.primitives if primitive.kind == "circle"]
    assert circles, "the flange's bore must come back as a circle"
    bore = min(circles, key=lambda primitive: abs(primitive.centre[0] - 901)
               + abs(primitive.centre[1] - 1477))
    assert bore.centre == pytest.approx([901, 1477], abs=8)
    assert bore.radius == pytest.approx(91.6, abs=4)
    assert bore.coverage is not None and bore.coverage >= 0.85


def test_flange_texts_carry_ocr_confidence(flange):
    assert len(flange.texts) >= 15
    assert all(text.confidence is not None for text in flange.texts)
    values = {text.value for text in flange.texts}
    assert 90.0 in values and 20.0 in values
    assert any(text.method == "tesseract-tsv" for text in flange.texts)


def test_notes_name_the_limits(flange):
    joined = " ".join(flange.notes)
    assert "Hough" in joined and "geri çağırma" in joined
    assert "ankraj" in joined and "OCR" in joined


def test_exercise_sheet_hole_survives_the_gates(exercise):
    assert (exercise.frame.width, exercise.frame.height) == (2480, 3509)
    circles = [primitive for primitive in exercise.primitives if primitive.kind == "circle"]
    hole = min(circles, key=lambda primitive: abs(primitive.centre[0] - 805)
               + abs(primitive.centre[1] - 706))
    assert hole.centre == pytest.approx([805, 706], abs=8)
    assert hole.radius == pytest.approx(55.1, abs=5)
    assert hole.coverage is not None and hole.coverage >= 0.9


def test_missing_tesseract_is_a_note_not_a_crash(tmp_path, monkeypatch):
    path = _synthetic_sheet(tmp_path)

    def no_binary(*_args, **_kwargs):
        raise FileNotFoundError("tesseract")

    monkeypatch.setattr(raster.subprocess, "run", no_binary)
    observations = observe_raster(path)
    assert observations.texts == []
    assert any("tesseract bulunamadı" in note for note in observations.notes)
    assert any(primitive.kind == "circle" for primitive in observations.primitives)


def test_unsupported_suffix_is_named():
    with pytest.raises(Unsupported, match="desteklenmeyen"):
        observe(Path("examples/whatever.doc"))


def _synthetic_arc_sheet(folder: Path) -> Path:
    """A 480x320 sheet with one full circle, one 120° arc and one straight stroke."""
    image = np.full((320, 480), 255, dtype=np.uint8)
    cv2.circle(image, (120, 160), 45, 0, 3)
    cv2.ellipse(image, (350, 160), (70, 70), 0, 40, 160, 0, 3)
    cv2.line(image, (250, 40), (250, 290), 0, 2)
    path = folder / "synthetic-arc.png"
    cv2.imwrite(str(path), image)
    return path


def test_synthetic_arc_comes_back_with_its_span(tmp_path):
    """The weak pass plus the angular-support gate is what lets a raster sheet reach a curved outline."""
    observations = observe_raster(_synthetic_arc_sheet(tmp_path))
    arcs = [primitive for primitive in observations.primitives if primitive.kind == "arc"]
    assert arcs, "çizili yay hiç bulunamadı"
    # The drawn arc must come back accurately; the weak pass also offers a few short slivers of real
    # ink (the gates bound that flood — 23 candidates down to a handful — but do not promise purity,
    # and a 60° stretch of drawn ink *is* an arc).
    arc = min(arcs, key=lambda item: abs(np.hypot(item.centre[0] - 350, item.centre[1] - 160))
              + abs((item.radius or 0.0) - 70))
    assert arc.centre == pytest.approx([350, 160], abs=8)
    assert arc.radius == pytest.approx(70, abs=6)
    span = (arc.end_degrees or 0.0) - (arc.start_degrees or 0.0)
    assert span == pytest.approx(120, abs=40)
    assert len(arcs) <= 6
    assert arc.coverage is not None and arc.coverage >= 0.75
    assert arc.method == "hough-arc"
    circles = [primitive for primitive in observations.primitives if primitive.kind == "circle"]
    assert any(circle.centre is not None and abs(circle.centre[0] - 120) <= 6 for circle in circles)


def test_a_full_circle_is_not_repeated_as_an_arc(tmp_path):
    """The strict pass keeps the ring that closes; the arc pass must not re-offer it as a partial one."""
    observations = observe_raster(_synthetic_arc_sheet(tmp_path))
    for arc in (primitive for primitive in observations.primitives if primitive.kind == "arc"):
        assert arc.centre is not None
        assert np.hypot(arc.centre[0] - 120, arc.centre[1] - 160) > 20


def test_longest_ring_run_wraps_around_the_zero_angle():
    """An arc that crosses the ring's start index is still one run; a broken one is measured as broken."""
    assert raster._longest_ring_run(np.array([False, True, True, True, False, False])) == (1, 3)
    assert raster._longest_ring_run(np.array([True, True, False, False, True])) == (4, 3)
    assert raster._longest_ring_run(np.array([True, True, True])) == (0, 3)
    assert raster._longest_ring_run(np.zeros(8, dtype=bool))[1] == 0
