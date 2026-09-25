"""Geometry tests on drawn strokes: no sheet, no OCR, just the shapes a drafting office uses."""

import cv2
import numpy as np
import pytest

from drawingto3d import lines


def _canvas() -> np.ndarray:
    return np.zeros((90, 260), dtype=np.uint8)


def _stroke(binary: np.ndarray, x0: int, x1: int, y: int, thickness: int = 2) -> None:
    cv2.line(binary, (x0, y), (x1, y), 255, thickness)


def _arrow(binary: np.ndarray, tip_x: int, base_x: int, y: int, half: int = 6) -> None:
    cv2.fillPoly(binary, [np.array([[tip_x, y], [base_x, y - half], [base_x, y + half]])], 255)


def _text_block(binary: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    cv2.rectangle(binary, (x0, y0), (x1, y1), 255, -1)


def _segments(binary: np.ndarray) -> list[lines.Segment]:
    # cv2 draws a 2 px line 3 px wide, and a stroke with an arrow on it one row wider still, so a test
    # fixture needs a little more room than the sheet does (dimension lines there measure 2-4 px).
    return lines.thin_segments(binary, min_length=30, max_thickness=6)


def test_a_leader_has_one_arrow_and_the_text_at_the_far_end():
    binary = _canvas()
    _stroke(binary, 30, 220, 45)
    _arrow(binary, 30, 60, 45)
    _text_block(binary, 232, 36, 256, 54)
    segments = _segments(binary)

    leader = lines.leader_near(binary, segments, (232.0, 36.0, 256.0, 54.0))

    assert leader is not None
    assert leader.tip == pytest.approx((30.0, 45.0), abs=3)
    assert leader.tail == pytest.approx((220.0, 45.0), abs=3)
    # One arrow is not a dimension line: that needs an arrow at both ends and its number in the middle.
    assert lines.dimension_line_near(binary, segments, (232.0, 36.0, 256.0, 54.0)) is None


def test_a_dimension_line_is_not_a_leader():
    binary = _canvas()
    _stroke(binary, 30, 230, 45)
    _arrow(binary, 30, 60, 45)
    _arrow(binary, 230, 200, 45)
    _text_block(binary, 118, 20, 152, 38)
    segments = _segments(binary)
    box = (118.0, 20.0, 152.0, 38.0)

    assert lines.dimension_line_near(binary, segments, box) is not None
    assert lines.leader_near(binary, segments, box) is None


def test_a_dimension_line_is_cut_at_its_extension_lines():
    binary = _canvas()
    _stroke(binary, 30, 230, 45)
    _arrow(binary, 30, 60, 45)
    _arrow(binary, 230, 200, 45)
    for x in (72, 168):  # the extension lines the dimension is drawn between
        cv2.line(binary, (x, 20), (x, 70), 255, 2)
    segments = _segments(binary)

    middles = [segment for segment in segments if segment.horizontal and 40 <= segment.y0 <= 50]
    spans = sorted(round(segment.length) for segment in middles)

    assert max(spans) < 120, spans  # no single segment spans the whole 200 px stroke
    assert any(85 <= span <= 100 for span in spans), spans  # the part between the extension lines
