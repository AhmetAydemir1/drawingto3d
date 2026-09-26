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


def _arrow_along(binary: np.ndarray, tip: tuple[int, int], base: tuple[int, int], half: int = 6) -> None:
    tip_point, base_point = np.array(tip, dtype=float), np.array(base, dtype=float)
    direction = tip_point - base_point
    direction = direction / float(np.hypot(*direction))
    normal = np.array([-direction[1], direction[0]])
    corners = np.array([tip_point, base_point + normal * half, base_point - normal * half])
    cv2.fillPoly(binary, [np.round(corners).astype(np.int32)], 255)


def _on_line(start: tuple[int, int], end: tuple[int, int], distance: float) -> tuple[int, int]:
    start_point, end_point = np.array(start, dtype=float), np.array(end, dtype=float)
    direction = end_point - start_point
    point = start_point + direction * (distance / float(np.hypot(*direction)))
    return int(round(point[0])), int(round(point[1]))


def test_a_number_on_an_angled_line_arrowed_at_both_ends_measures_that_line():
    # The axis pass only sees a horizontal or vertical row, so a dimension drawn at an angle is
    # invisible there however long its stroke is. The same row, projected onto the stroke, measures it.
    binary = _canvas(width=400, height=400)
    start, end = (80, 260), (320, 180)
    cv2.line(binary, start, end, 255, 2)
    _arrow_along(binary, start, _on_line(start, end, 36))
    _arrow_along(binary, end, _on_line(end, start, 36))
    box = (184.0, 200.0, 224.0, 220.0)
    _text(binary, 184, 200, 224, 220)
    stroke = lines.Stroke(float(start[0]), float(start[1]), float(end[0]), float(end[1]), 3.0)

    found = lines.dimension_for(binary, [], box, strokes=[stroke])

    assert found is not None
    assert found.ends[0] == pytest.approx(start, abs=1)
    assert found.ends[1] == pytest.approx(end, abs=1)


def test_a_number_between_two_angled_strokes_measures_the_outer_arrow_tips():
    # The number breaks its own dimension line. Each piece carries the arrow at the outer tip, and the
    # span is the pair of tips that bracket the number, not either piece on its own.
    binary = _canvas(width=400, height=400)
    start, end = (80, 260), (320, 180)
    outer_start, inner_start = start, _on_line(start, end, 70)
    inner_end, outer_end = _on_line(start, end, 180), end
    cv2.line(binary, outer_start, inner_start, 255, 2)
    cv2.line(binary, inner_end, outer_end, 255, 2)
    _arrow_along(binary, outer_start, _on_line(start, end, 36))
    _arrow_along(binary, outer_end, _on_line(end, start, 36))
    box = (184.0, 200.0, 224.0, 220.0)
    _text(binary, 184, 200, 224, 220)
    strokes = [
        lines.Stroke(*outer_start, *inner_start, 3.0),
        lines.Stroke(*inner_end, *outer_end, 3.0),
    ]

    found = lines.dimension_for(binary, [], box, strokes=strokes)

    assert found is not None
    assert found.ends[0] == pytest.approx(outer_start, abs=1)
    assert found.ends[1] == pytest.approx(outer_end, abs=1)


def test_an_angled_stroke_with_one_arrow_is_not_a_dimension():
    # One arrow and the words beside the blank end is a leader. Reading that shaft as a dimension would
    # turn the callout into a length.
    binary = _canvas(width=400, height=400)
    start, end = (80, 260), (320, 180)
    cv2.line(binary, start, end, 255, 2)
    _arrow_along(binary, end, _on_line(end, start, 36))
    box = (184.0, 200.0, 224.0, 220.0)
    stroke = lines.Stroke(float(start[0]), float(start[1]), float(end[0]), float(end[1]), 3.0)

    assert lines.dimension_for(binary, [], box, strokes=[stroke]) is None


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


def test_a_number_print_beyond_the_tip_still_measures_the_arrowed_line():
    # A feature too small to hold its own number is drawn with both arrows on the feature and the value
    # beside it, on the row's extension: the `50` on my_part.jpg's 45-degree diameter. The tips are the
    # span; the number has to be clear of that span and within a character and a half of it.
    binary = _canvas(width=420, height=400)
    start, end = (60, 260), (300, 180)
    cv2.line(binary, start, end, 255, 2)
    _arrow_along(binary, start, _on_line(start, end, 36))
    _arrow_along(binary, end, _on_line(end, start, 36))
    beyond = _on_line(start, end, 320)  # 45 px past the far tip
    box = (float(beyond[0] - 20), float(beyond[1] - 20), float(beyond[0] + 20), float(beyond[1] + 20))
    _text(binary, int(box[0]), int(box[1]), int(box[2]), int(box[3]))
    stroke = lines.Stroke(float(start[0]), float(start[1]), float(end[0]), float(end[1]), 3.0)

    found = lines.dimension_for(binary, [], box, strokes=[stroke])

    assert found is not None
    assert found.ends[0] == pytest.approx(start, abs=1)
    assert found.ends[1] == pytest.approx(end, abs=1)


def test_a_number_far_past_the_tip_is_not_this_line_s_dimension():
    # Four characters past the tip and the number has a line of its own; this row must not reach for it.
    binary = _canvas(width=560, height=400)
    start, end = (60, 260), (300, 180)
    cv2.line(binary, start, end, 255, 2)
    _arrow_along(binary, start, _on_line(start, end, 36))
    _arrow_along(binary, end, _on_line(end, start, 36))
    beyond = _on_line(start, end, 560)  # 300 px past the far tip
    box = (float(beyond[0] - 20), float(beyond[1] - 20), float(beyond[0] + 20), float(beyond[1] + 20))
    _text(binary, int(box[0]), int(box[1]), int(box[2]), int(box[3]))
    stroke = lines.Stroke(float(start[0]), float(start[1]), float(end[0]), float(end[1]), 3.0)

    assert lines.dimension_for(binary, [], box, strokes=[stroke]) is None


def test_a_short_arrowed_piece_beside_a_number_is_a_fragment_not_a_dimension():
    # A number crossed by a long line widens the ink the way an arrowhead does, so a piece of that line
    # cut by the digits looks arrowed at both ends. The plastic sheet's drawn `R8.00` is this shape: 91 px
    # of a 270 px leader read as a dimension against an 82 px box. A span that fits inside the number's
    # own box is a fragment of the number's line, not the line that measures it.
    binary = _canvas(width=420, height=300)
    start, end = (120, 140), (200, 200)
    cv2.line(binary, start, end, 255, 2)
    _arrow_along(binary, start, _on_line(start, end, 20))
    _arrow_along(binary, end, _on_line(end, start, 20))
    box = (196.0, 132.0, 296.0, 212.0)
    _text(binary, 196, 132, 296, 212)
    stroke = lines.Stroke(float(start[0]), float(start[1]), float(end[0]), float(end[1]), 3.0)

    assert lines.dimension_for(binary, [], box, strokes=[stroke]) is None


def test_a_wide_number_does_not_merge_the_two_edge_lines_that_carry_its_value():
    # The plastic sheet's `1.50`: its own span is the gap between two extension lines 6 px apart, and the
    # number is printed past their tip in a box 71 px wide. A merge tolerance read off that box (0.4 of
    # 71 px) swallowed the two lines into one crossing, so the only pair left on the row was a neighbour's
    # 113.5 px line and the value had nothing to be judged against.
    binary = _canvas(width=400, height=140)
    _stroke(binary, 20, 60, 70)  # the row, broken where the number sits
    _stroke(binary, 250, 380, 70)
    _upright(binary, 66, 40, 100)  # the two extension lines that carry the value
    _upright(binary, 72, 40, 100)
    box = (100.0, 53.0, 271.0, 87.0)

    pairs = lines.crossing_pairs(_segments(binary), box)

    lengths = sorted(round(pair[1][0] - pair[0][0], 1) for pair in pairs)
    assert lengths == [pytest.approx(6, abs=2)]
