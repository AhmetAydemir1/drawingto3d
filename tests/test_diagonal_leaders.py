"""A callout is carried by a diagonal stroke, so the strokes a leader is looked for on are not only the
axis ones. Synthetic geometry: no sheet, no OCR."""

import cv2
import numpy as np
import pytest

from drawingto3d import lines


def _canvas(height: int = 360, width: int = 360) -> np.ndarray:
    return np.zeros((height, width), dtype=np.uint8)


def _line(binary: np.ndarray, start: tuple[int, int], end: tuple[int, int], thickness: int = 2) -> None:
    cv2.line(binary, start, end, 255, thickness)


def _arrow(binary: np.ndarray, tip: tuple[int, int], base: tuple[int, int], half: int = 5) -> None:
    """A slender triangle along the line from base to tip, the way a drafting arrow is drawn: 2-3 times
    the weight of the line it sits on, 40-50 px long."""
    tip_point, base_point = np.array(tip, dtype=float), np.array(base, dtype=float)
    direction = tip_point - base_point
    direction = direction / float(np.hypot(*direction))
    normal = np.array([-direction[1], direction[0]])
    corners = np.array([tip_point, base_point + normal * half, base_point - normal * half])
    cv2.fillPoly(binary, [np.round(corners).astype(np.int32)], 255)


def _words(binary: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """Words drawn as the strokes of a Z, and the mask that says where the printed text is.

    A Z carries a diagonal, which is what makes it the useful fixture: words on a real sheet have
    diagonal strokes in them that must not be read as leaders.
    """
    cv2.line(binary, (x0 + 4, y0 + 4), (x1 - 4, y0 + 4), 255, 2)
    cv2.line(binary, (x1 - 4, y0 + 4), (x0 + 4, y1 - 4), 255, 2)
    cv2.line(binary, (x0 + 4, y1 - 4), (x1 - 4, y1 - 4), 255, 2)
    mask = np.zeros_like(binary)
    cv2.rectangle(mask, (x0, y0), (x1, y1), 255, -1)
    return mask


def _gray(binary: np.ndarray) -> np.ndarray:
    """Ink dark on light paper, the way a sheet reaches the detector."""
    return 255 - binary


def _diagonals(binary: np.ndarray, text_mask: np.ndarray | None = None) -> list[lines.Stroke]:
    # cv2 draws a 2 px line 3 px wide (see test_lines), so the fixture needs more room than a sheet does.
    return lines.diagonal_strokes(_gray(binary), binary, min_length=30.0, max_thickness=6.0, text_mask=text_mask)


TAIL: tuple[int, int] = (285, 75)
TIP: tuple[int, int] = (75, 285)
TEXT_BOX = (300.0, 55.0, 344.0, 79.0)


def _distance(stroke: lines.Segment | lines.Stroke, point: tuple[float, float]) -> float:
    return float(min(np.hypot(end[0] - point[0], end[1] - point[1]) for end in stroke.ends()))


def _off_line(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    return float(abs((point[0] - start[0]) * dy - (point[1] - start[1]) * dx) / np.hypot(dx, dy))


def test_a_diagonal_leader_is_found_from_its_arrow_to_the_words():
    binary = _canvas()
    _line(binary, TAIL, TIP)
    _arrow(binary, TIP, (110, 250))
    text_mask = _words(binary, 300, 55, 344, 79)  # printed beside the shaft's blank end

    strokes = _diagonals(binary, text_mask)
    leader = lines.leader_near(binary, strokes, TEXT_BOX, text_mask)

    assert leader is not None, "a leader drawn at an angle has to be found like any other"
    assert leader.tail == pytest.approx(TAIL, abs=6)
    # The arrowhead is not part of the line: the stroke ends where the arrow widens, the same way a
    # row-by-row pass ends a dimension line at its arrow, so the tip stands at the arrow's base on the
    # line that points at the feature.
    assert _off_line(leader.tip, TAIL, TIP) < 6.0, leader.tip
    assert _distance(leader.segment, TIP) < 60.0, leader.tip


def test_the_arrow_question_is_answered_the_same_along_an_axis_and_across_it():
    # A leader is a leader whatever angle it is drawn at: the same arrowhead has to be recognised on a
    # horizontal line and on a diagonal one, and a bare end has to look bare in both.
    binary = _canvas()
    _line(binary, (60, 40), (300, 40))
    _arrow(binary, (60, 40), (95, 40))
    _line(binary, (60, 200), (300, 200))
    _arrow(binary, (60, 200), (95, 200))
    horizontal = lines.Segment(60.0, 39.0, 300.0, 41.0, 3.0, True)
    diagonal = lines.Stroke(60.0, 200.0, 300.0, 200.0, 3.0)

    assert lines.arrow_steps(binary, horizontal, 0) >= 8
    assert lines.arrow_steps(binary, diagonal, 0) >= 8
    assert lines.arrow_steps(binary, horizontal, 1) < 8
    assert lines.arrow_steps(binary, diagonal, 1) < 8


def test_a_diagonal_arrowed_at_both_ends_is_a_dimension_line_not_a_leader():
    binary = _canvas()
    _line(binary, TAIL, TIP)
    _arrow(binary, TIP, (110, 250))
    _arrow(binary, TAIL, (250, 110))
    text_mask = _words(binary, 300, 55, 344, 79)

    strokes = _diagonals(binary, text_mask)

    assert lines.leader_near(binary, strokes, TEXT_BOX, text_mask) is None


def test_a_diagonal_inside_the_printed_words_is_a_glyph_not_a_leader():
    binary = _canvas()
    text_mask = _words(binary, 40, 40, 150, 110)
    _line(binary, TAIL, TIP)  # a real leader, drawn well clear of the words

    strokes = _diagonals(binary, text_mask)

    assert len(strokes) == 1, [stroke.middle for stroke in strokes]
    assert _distance(strokes[0], TIP) < 20.0


def test_a_leader_whose_own_ink_is_in_the_text_mask_is_still_a_leader():
    """The mask cannot remove a stroke at an angle, so it reports the leader's own ink as printed text.

    On the plate sheet the leader of `6,80 THRU ALL` reads 65% text that way and every callout whose
    leader is not faint was refused; the ink the stroke runs through is what tells the two apart, and
    this fixture is a sheet where the mask is the ink (nothing removed): the leader is one narrow blob
    as long as itself, the words are blobs the size of the sheet's own type.
    """
    binary = _canvas()
    _line(binary, TAIL, TIP)
    _arrow(binary, TIP, (110, 250))
    for x0, y0 in ((300, 55), (150, 40), (40, 120), (260, 300), (30, 300)):
        _words(binary, x0, y0, x0 + 44, y0 + 24)
    text_mask = binary.copy()

    strokes = _diagonals(binary, text_mask)
    printed = lines.PrintedText.of(text_mask)
    leader_stroke = min(strokes, key=lambda stroke: _distance(stroke, TIP))

    assert printed.character == pytest.approx(44, abs=6), printed.character
    assert printed.through_words(leader_stroke) is False
    assert lines.leader_near(binary, strokes, TEXT_BOX, text_mask, printed_text=printed) is not None


def test_a_stroke_running_through_the_words_is_still_refused():
    """The same question asked of a stroke that really is inside type: its blob is one character long."""
    binary = _canvas()
    text_mask = _words(binary, 40, 40, 84, 64)
    inside = lines.Stroke(80.0, 44.0, 44.0, 60.0, 2.0)  # a stroke across the words
    printed = lines.PrintedText.of(text_mask)

    assert lines.text_fraction(text_mask, inside) > lines.TEXT_FRACTION
    assert printed.through_words(inside) is True
    assert lines.leader_near(binary, [inside], (100.0, 30.0, 160.0, 50.0), text_mask, printed_text=printed) is None
