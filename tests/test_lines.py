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
    _text_block(binary, 232, 22, 256, 40)  # printed beside the shaft's blank end, not on it
    segments = _segments(binary)

    leader = lines.leader_near(binary, segments, (232.0, 22.0, 256.0, 40.0))

    assert leader is not None
    assert leader.tip == pytest.approx((30.0, 45.0), abs=3)
    assert leader.tail == pytest.approx((220.0, 45.0), abs=3)
    # One arrow is not a dimension line: that needs an arrow at both ends and its number in the middle.
    assert lines.dimension_line_near(binary, segments, (232.0, 22.0, 256.0, 40.0)) is None


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


def test_a_crossing_that_cuts_a_dimension_line_does_not_end_its_span():
    # The number is printed above its own line, and that line runs edge to edge. A neighbouring
    # dimension's extension line crosses it in the middle: the crossing thickens the ink, `thin_segments`
    # drops that widened run, and the line arrives as two pieces a few pixels apart. The pair the number
    # sits between then measures from the crossing to the far end — a 45 read as the 30 left over — and the
    # sheet stops agreeing with its own other numbers. The span is the line's two ends, crossing passed over.
    binary = _canvas()
    _stroke(binary, 30, 118, 40)
    _stroke(binary, 126, 230, 40)
    cv2.line(binary, (122, 22), (122, 58), 255, 2)  # the crossing extension line
    for x in (30, 230):  # the dimension's own extension lines
        cv2.line(binary, (x, 22), (x, 58), 255, 2)
    _arrow(binary, 34, 48, 40)  # the arrowheads sit inside the ends, as they do on a sheet
    _arrow(binary, 226, 212, 40)
    _text_block(binary, 150, 30, 174, 46)  # the number, above the line rather than on it
    segments = _segments(binary)

    found = lines.dimension_for(binary, segments, (150.0, 30.0, 174.0, 46.0))

    assert found is not None
    ends = sorted(round(point[0]) for point in found.ends)
    assert abs(ends[0] - 30) <= 4 and abs(ends[1] - 230) <= 4, ends


def test_only_a_crossing_joins_two_pieces_of_one_row_and_two_met_arrowheads_do_not():
    # The whole difference between "one line cut in two" and "two dimensions end to end" is the ink that
    # stands beside the junction. A crossing is a thin line: the row's own ink either side of it is back to
    # the line's weight. Met arrowheads are wedges: the ink stays several times that weight for ten-odd
    # pixels inside each piece. The first is joined, the second is a boundary — measured on the pilot
    # sheets, at the `45`'s crossing the ink is 31 px tall at the junction and 1 px 3 px away, while met
    # arrowheads are 36 px tall there and 4 to 8 px away.
    pieces = [
        lines.Segment(x0=30.0, y0=40.0, x1=118.0, y1=40.0, thickness=2.0, horizontal=True),
        lines.Segment(x0=126.0, y0=40.0, x1=230.0, y1=40.0, thickness=2.0, horizontal=True),
    ]
    crossing = _canvas()
    cv2.line(crossing, (122, 22), (122, 58), 255, 2)
    met_arrowheads = _canvas()
    cv2.line(met_arrowheads, (122, 22), (122, 58), 255, 2)
    cv2.fillPoly(met_arrowheads, [np.array([[118, 40], [104, 32], [104, 48]])], 255)
    cv2.fillPoly(met_arrowheads, [np.array([[126, 40], [140, 32], [140, 48]])], 255)

    joined = lines._row_run(crossing, True, 40.0, 16.0, (150.0, 174.0), pieces)
    apart = lines._row_run(met_arrowheads, True, 40.0, 16.0, (150.0, 174.0), pieces)

    assert [segment.x0 for segment in joined] == [30.0, 126.0]
    assert [segment.x0 for segment in apart] == [126.0]  # the piece the number was printed on, alone
