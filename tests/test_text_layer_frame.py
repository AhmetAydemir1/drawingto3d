"""Where a PDF's own text sits on the rendered sheet. The frame is measured, never assumed.

A char box comes in PDF points from the bottom-left corner; the raster this program works on starts at
the top-left. Some drawing tools and some pages put the text in that bottom-left frame and some do not,
so the sheet itself says which by the ink its own boxes cover.
"""

import numpy as np

from drawingto3d import ingest

SCALE = 2.0
SECTION_HEIGHT_PT = 200.0
HEIGHT, WIDTH = 400, 300


def _sheet(marks: list[tuple[float, float, float, float]], shade: tuple[float, float, float, float] | None = None) -> np.ndarray:
    """A white raster with a dark block where each number is printed, in raster pixels."""
    gray = np.full((HEIGHT, WIDTH), 255, dtype=np.uint8)
    if shade is not None:
        x, y, w, h = shade
        gray[int(y) : int(y + h), int(x) : int(x + w)] = 60
    for x, y, w, h in marks:
        gray[int(y) : int(y + h), int(x) : int(x + w)] = 0
    return gray


def _point_box(mark: tuple[float, float, float, float], mirrored: bool) -> tuple[float, float, float, float]:
    """The mark as a PDF char box (left, bottom, right, top) in the frame the sheet is drawn in."""
    x, y, w, h = mark
    if mirrored:
        return (x / SCALE, (HEIGHT - y - h) / SCALE, (x + w) / SCALE, (HEIGHT - y) / SCALE)
    return (x / SCALE, y / SCALE, (x + w) / SCALE, (y + h) / SCALE)


def _boxes(marks: list[tuple[float, float, float, float]], mirrored: bool) -> list[tuple[str, tuple[float, float, float, float]]]:
    return [(f"n{index}", _point_box(mark, mirrored)) for index, mark in enumerate(marks)]


MARKS = [(30.0, 40.0, 40.0, 16.0), (140.0, 120.0, 50.0, 16.0), (60.0, 210.0, 30.0, 16.0)]


def _ok(place, marks, mirrored: bool) -> bool:
    return all(place(box, SCALE)[:2] == (mark[0], mark[1]) for (text, box), mark in zip(_boxes(marks, mirrored), marks))


def test_a_text_layer_drawn_from_the_bottom_left_is_turned_over():
    gray = _sheet(MARKS)
    place = ingest._upright_placement(_boxes(MARKS, mirrored=True), gray, SCALE, SECTION_HEIGHT_PT)
    assert _ok(place, MARKS, mirrored=True)


def test_a_text_layer_drawn_the_other_way_round_is_left_alone():
    gray = _sheet(MARKS)
    place = ingest._upright_placement(_boxes(MARKS, mirrored=False), gray, SCALE, SECTION_HEIGHT_PT)
    assert _ok(place, MARKS, mirrored=False)


def test_a_shaded_pictorial_view_does_not_decide_the_frame():
    # One placement drops the boxes onto a shaded isometric, where nearly every pixel is dark: counting
    # dark pixels would pick it. Text is darker than *its own* surroundings, which is what decides.
    shade = (0.0, 300.0, 200.0, 90.0)
    gray = _sheet(MARKS, shade=shade)
    place = ingest._upright_placement(_boxes(MARKS, mirrored=True), gray, SCALE, SECTION_HEIGHT_PT)
    assert _ok(place, MARKS, mirrored=True)
