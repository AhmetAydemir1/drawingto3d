"""The guard that keeps a line's own ink out of the printed numbers, and the mode it is asked in.

An arrowhead is drawn on the line it terminates, at one of its ends, and it is solid; a printed number stands
beside its line, or in the gap the line breaks around, and it is drawn as type. The place half of that question
is arithmetic on the candidate's box and the stroke's two anchors, and it must give the same answer whether the
stroke is axis-aligned or a diagonal — a callout usually is a diagonal, and it is asked now in both modes.
"""

from __future__ import annotations

import numpy as np

from drawingto3d import perceive


def old_place(box: tuple[float, float, float, float], anchors) -> bool:
    """The axis-aligned arithmetic this replaced, kept here to hold the general form to it."""
    (ax, ay), (bx, by) = anchors
    vertical = abs(bx - ax) < abs(by - ay)
    axis = (ax + bx) / 2 if vertical else (ay + by) / 2
    centre_across = (box[0] + box[2]) / 2 if vertical else (box[1] + box[3]) / 2
    centre_along = (box[1] + box[3]) / 2 if vertical else (box[0] + box[2]) / 2
    across, along = (box[2] - box[0]), (box[3] - box[1])
    if abs(centre_across - axis) > max(1.0, 0.05 * min(across, along)):
        return False
    reach = max(across, along)
    return min(abs(centre_along - (ay if vertical else ax)), abs(centre_along - (by if vertical else bx))) <= reach


def test_the_place_test_is_the_same_arithmetic_on_axis_aligned_lines() -> None:
    """A rewrite of a measured rule has to answer exactly as it did for the sheets it was measured on."""
    cases = [
        ([[100.0, 50.0], [100.0, 250.0]], 10, 14),   # a vertical dimension line
        ([[50.0, 100.0], [250.0, 100.0]], 14, 10),   # a horizontal one
        ([[100.0, 100.0], [100.0, 400.0]], 20, 20),
    ]
    checked = 0
    for anchors, width, height in cases:
        for x in range(60, 320, 11):
            for y in range(20, 320, 13):
                box = (float(x), float(y), float(x + width), float(y + height))
                assert perceive._is_the_lines_own_ink(box, anchors) == old_place(box, anchors), (box, anchors)
                checked += 1
    assert checked > 1000


def test_a_mark_on_a_diagonal_callout_at_its_tip_is_the_lines_own_ink() -> None:
    """A leader is a diagonal, and its arrowhead sits on that segment at the tip: one coordinate says nothing."""
    anchors = [[100.0, 100.0], [300.0, 300.0]]
    at_tip = (95.0, 95.0, 115.0, 115.0)
    assert perceive._is_the_lines_own_ink(at_tip, anchors)
    beside_it = (150.0, 95.0, 170.0, 115.0)
    assert not perceive._is_the_lines_own_ink(beside_it, anchors)
    at_the_middle = (195.0, 195.0, 205.0, 205.0)
    assert not perceive._is_the_lines_own_ink(at_the_middle, anchors), "a long leader's middle is not its end"


def test_a_pair_that_is_one_point_is_not_a_line() -> None:
    assert not perceive._is_the_lines_own_ink((0.0, 0.0, 10.0, 10.0), [[50.0, 50.0], [50.0, 50.0]])


def glyph(x: int, y: int, w: int = 10, h: int = 14) -> perceive.Glyph:
    return perceive.Glyph(x + w / 2, y + h / 2, x, y, w, h, False)


class OneStrokeGate:
    """A gate that hands every candidate the same stroke: a diagonal callout arrowed at its tip."""

    def __init__(self, anchors) -> None:
        self.anchors = anchors
        self.accepted = 0

    def accepts(self, box, block=None):
        self.accepted += 1
        return True, self.anchors, "leader"


class StubReader:
    def __init__(self, answer: str = "12") -> None:
        self.answer = answer
        self.calls = 0

    def read(self, crop):
        self.calls += 1
        return self.answer


def collect(fill: int, glyphs, anchors, reader):
    mask = np.full((400, 400), fill, np.uint8)
    gray = np.full((400, 400), 255, np.uint8)
    return perceive._collect_spans(gray, glyphs, "center", gate=OneStrokeGate(anchors), reader=reader,
                                   text_mask=mask)


def test_the_question_is_put_to_a_leader_as_well() -> None:
    """Measured on `Exercise 17`: eight of the gate's thirty accepted clusters were leader-mode arrowheads
    and arcs the guard was never asked about, because it ran only for dimension-mode candidates."""
    anchors = [[100.0, 100.0], [300.0, 300.0]]
    at_tip = [glyph(95, 95, 10, 10)]          # its centre is the stroke's tip, as a drawn arrowhead's is
    solid = StubReader()
    assert collect(255, at_tip, anchors, solid) == []
    assert solid.calls == 0, "the line's own ink is not handed to a reader"
    hollow = StubReader()
    collect(60, at_tip, anchors, hollow)                   # same place, but drawn as type: the reader's turn
    assert hollow.calls == 1, "type that stands on its own line is kept, and read"
