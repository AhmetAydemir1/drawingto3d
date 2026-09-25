"""How a printed number is tied to the geometry that measures it. Synthetic strokes only."""

import cv2
import numpy as np
import pytest

from drawingto3d import lines


def _canvas(width: int = 300, height: int = 120) -> np.ndarray:
    return np.zeros((height, width), dtype=np.uint8)


def _stroke(binary: np.ndarray, x0: int, x1: int, y: int, thickness: int = 2) -> None:
    cv2.line(binary, (x0, y), (x1, y), 255, thickness)


def _upright(binary: np.ndarray, x: int, y0: int, y1: int, thickness: int = 2) -> None:
    cv2.line(binary, (x, y0), (x, y1), 255, thickness)


def _arrow(binary: np.ndarray, tip_x: int, base_x: int, y: int, half: int = 6) -> None:
    cv2.fillPoly(binary, [np.array([[tip_x, y], [base_x, y - half], [base_x, y + half]])], 255)


def _text(binary: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    cv2.rectangle(binary, (x0, y0), (x1, y1), 255, -1)


def _segments(binary: np.ndarray) -> list[lines.Segment]:
    return lines.thin_segments(binary, min_length=30, max_thickness=6)


def test_a_number_on_a_line_arrowed_at_both_ends_measures_that_line():
    binary = _canvas()
    _stroke(binary, 40, 240, 60)
    _arrow(binary, 40, 70, 60)
    _arrow(binary, 240, 210, 60)
    _upright(binary, 40, 30, 90)  # the extension lines the arrows stop at
    _upright(binary, 240, 30, 90)
    box = (120.0, 36.0, 160.0, 52.0)
    _text(binary, 120, 36, 160, 52)

    found = lines.dimension_for(binary, _segments(binary), box)

    assert found is not None
    (x0, _y0), (x1, _y1) = found.ends
    assert x0 == pytest.approx(40, abs=5)
    assert x1 == pytest.approx(240, abs=5)


def test_a_number_beside_a_line_arrowed_outside_measures_the_gap_the_arrows_close():
    # A small feature is drawn with its arrows outside the span and its number beside the line, so the
    # number's own stroke is shorter than what it measures: the span is the empty gap between the two
    # facing arrow tips, which is where the extension lines stand.
    binary = _canvas()
    _upright(binary, 120, 10, 110)  # extension lines long enough to survive the arrowheads beside them
    _upright(binary, 160, 10, 110)
    _stroke(binary, 60, 118, 60)
    _arrow(binary, 118, 90, 60)
    _stroke(binary, 162, 220, 60)
    _arrow(binary, 162, 190, 60)
    box = (10.0, 46.0, 58.0, 74.0)
    _text(binary, 10, 46, 58, 74)

    found = lines.dimension_for(binary, _segments(binary), box)

    assert found is not None
    (x0, _y0), (x1, _y1) = found.ends
    assert x0 == pytest.approx(120, abs=6)
    assert x1 == pytest.approx(160, abs=6)


def test_a_line_with_no_arrowhead_is_not_a_dimension():
    # A title-block rule and the edge of an outline carry numbers past them too; neither sizes anything.
    binary = _canvas()
    _stroke(binary, 40, 240, 60)
    box = (120.0, 36.0, 160.0, 52.0)
    _text(binary, 120, 36, 160, 52)

    assert lines.dimension_for(binary, _segments(binary), box) is None


def test_a_wide_number_beside_a_one_arrow_shaft_is_a_leader():
    # `0.688in` is a wide block of text; its gap to the shaft is measured from the edge of the words, not
    # from their centre, or every wide dimension text on a sheet loses its leader.
    binary = _canvas(width=400, height=140)
    _stroke(binary, 40, 200, 90)
    _arrow(binary, 40, 70, 90)
    box = (206.0, 66.0, 330.0, 88.0)
    _text(binary, 206, 66, 330, 88)

    leader = lines.leader_near(binary, _segments(binary), box)

    assert leader is not None
    assert leader.tip == pytest.approx((40.0, 90.0), abs=5)
