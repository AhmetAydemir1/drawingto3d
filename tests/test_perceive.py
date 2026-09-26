"""Geometry of reading: which glyphs are one printed number, and which candidate belongs to a line."""

import cv2
import numpy as np
import pytest

from drawingto3d import perceive
from drawingto3d.schema import AnchorMode, BBox, Span


def _glyph(centre_x: float, centre_y: float, x: int, y: int, w: int, h: int, separator: bool = False) -> perceive.Glyph:
    return perceive.Glyph(centre_x, centre_y, x, y, w, h, separator)


def _span(serial: int, box: tuple[float, float, float, float], anchors: list[list[float]]) -> Span:
    return Span(
        id=f"ocr-{serial}",
        text="?",
        value=None,
        bbox=BBox(x=box[0], y=box[1], w=box[2], h=box[3]),
        anchors=anchors,
    )


def test_upright_digits_of_one_number_stay_together():
    first = _glyph(100.0, 100.0, 90, 80, 27, 42)
    second = _glyph(132.0, 100.0, 122, 80, 25, 41)
    assert perceive._centers_near(first, second)


def test_a_quarter_turned_number_is_one_number_not_two_halves():
    # Along a vertical dimension line a digit is wider than it is tall (41x26), and two of them sit just
    # as far apart as two upright digits. Measured on height, this pair came apart and each half was read
    # as its own number — the printed 35 arrived as a 3 and a 5, both on the same line.
    upper = _glyph(1706.0, 709.0, 1686, 696, 41, 26)
    lower = _glyph(1706.0, 738.0, 1685, 725, 42, 27)
    assert perceive._centers_near(upper, lower)


def test_two_numbers_a_line_apart_are_kept_apart():
    left = _glyph(100.0, 100.0, 90, 80, 27, 42)
    right = _glyph(260.0, 100.0, 250, 80, 27, 42)
    assert not perceive._centers_near(left, right)


def test_one_number_per_line_keeps_the_fullest_candidate():
    line = [[10.0, 10.0], [200.0, 10.0]]
    fragment = _span(0, (100.0, 5.0, 17.0, 19.0), line)
    whole = _span(1, (95.0, 0.0, 42.0, 54.0), line)
    elsewhere = _span(2, (400.0, 0.0, 27.0, 42.0), [[400.0, 10.0], [500.0, 10.0]])

    kept = perceive._one_number_per_line([fragment, whole, elsewhere])

    assert [span.id for span in kept] == ["ocr-1", "ocr-2"]


def test_the_decimal_separator_keeps_a_number_whole():
    # The comma is too small to be kept as a glyph of its own, so the digits either side of it are all
    # that is left to measure, and the room it takes pushed them 30.6 px apart against a 25.6 px reach:
    # on the plate sheet every dimension came apart at its decimal point, 100,00 into 10 and 00.
    left = _glyph(805.0, 491.0, 797, 478, 18, 28)
    left_digit = _glyph(825.0, 491.0, 817, 478, 18, 28)
    comma = _glyph(846.0, 500.0, 843, 496, 6, 8, separator=True)
    right_digit = _glyph(856.0, 492.0, 847, 478, 19, 28)
    right = _glyph(876.0, 491.0, 868, 478, 18, 28)
    glyphs = [left, left_digit, comma, right_digit, right]

    assert not perceive._centers_near(left_digit, right_digit), "the digits themselves are out of reach"
    assert perceive._separator_between(left_digit, right_digit, glyphs)
    assert len(perceive._cluster_glyphs(glyphs, "center")) == 1


def test_a_character_sized_blob_between_two_digits_is_not_a_separator():
    # Digits of one number are within a character's reach of each other or the comma between them holds
    # them apart; a blob good enough to be a character is another digit, which is a longer number.
    left = _glyph(100.0, 100.0, 90, 78, 18, 27)
    middle = _glyph(131.0, 100.0, 117, 78, 27, 42)
    right = _glyph(162.0, 100.0, 152, 78, 18, 27)

    assert not perceive._centers_near(left, right)
    assert not perceive._separator_between(left, right, [left, middle, right])


def test_a_comma_beside_the_digits_still_bridges_them():
    # The plate sheet's own `80,00`: its digits at y = 860 and y = 891 are 31 px apart against a 24.9 px
    # reach, and the comma sits 12 px to the side of them at (174, 875).
    upper = _glyph(162.0, 860.0, 148, 851, 27, 18)
    lower = _glyph(162.0, 891.0, 148, 882, 27, 18)
    comma = _glyph(174.0, 875.0, 170, 873, 8, 4, separator=True)

    assert not perceive._centers_near(upper, lower)
    assert perceive._separator_between(upper, lower, [upper, comma, lower])
    assert len(perceive._cluster_glyphs([upper, comma, lower], "center")) == 1


def test_the_separator_side_says_which_way_a_vertical_number_reads():
    # The plate sheet's own `80,00`: four digits up a vertical line at x = 162 and the comma to the right
    # of them at (174, 875). A separator sits below the baseline, so that number reads bottom to top.
    digits = [_glyph(162.0, y, 148, int(y) - 9, 27, 18) for y in (840.0, 860.0, 891.0, 910.0)]
    comma = _glyph(174.0, 875.0, 170, 873, 8, 4, separator=True)
    glyphs = [*digits, comma]

    assert perceive._reading_turn(glyphs, list(range(len(glyphs)))) == 90


def test_a_horizontal_number_with_its_comma_below_reads_as_it_stands():
    digits = [_glyph(x, 491.0, int(x) - 9, 477, 18, 28) for x in (785.0, 805.0, 825.0, 856.0, 876.0)]
    comma = _glyph(841.0, 504.0, 838, 500, 5, 7, separator=True)
    glyphs = [*digits, comma]

    assert perceive._reading_turn(glyphs, list(range(len(glyphs)))) == 0


def test_a_single_digit_says_nothing_about_which_way_it_reads():
    glyphs = [_glyph(100.0, 100.0, 90, 78, 18, 27), _glyph(112.0, 108.0, 110, 106, 5, 5, separator=True)]

    assert perceive._reading_turn(glyphs, list(range(len(glyphs)))) is None


def test_glyphs_of_two_printed_lines_are_two_numbers_not_one():
    # The plate sheet's raster path: the comma of the drawn `6,80` takes the same room as any comma, and
    # the digits either side of it are then within 1.6 characters of each other - so it bridged the `8`
    # to a `6` of the *line below* (44.4 px against a 44.8 px limit, missing by half a pixel). The crop
    # of that five-glyph cluster spans two printed lines and 72 px, and was read as `08°9`, an angle
    # printed nowhere on the sheet, while the true 6.80 stayed missing.
    # 22 px apart: inside the digit reach (0.7 of the 28 px side plus 6). The comma is not what holds
    # these two together; it is what pulls the line below into the same cluster.
    first = _glyph(108.0, 100.0, 99, 80, 18, 28)
    second = _glyph(130.0, 100.0, 122, 80, 18, 28)
    below = _glyph(130.0, 140.0, 122, 120, 18, 28)
    comma = _glyph(130.0, 120.0, 127, 117, 6, 7, separator=True)
    glyphs = [first, second, below, comma]

    assert perceive._separator_between(second, below, glyphs), "the comma is what joins them"
    lines = perceive._cluster_glyphs(glyphs, "center")

    assert sorted(sorted(line) for line in lines) == [[0, 1], [2]]


def test_the_note_a_number_is_printed_in_is_its_block_and_not_only_its_line():
    # The plate's `4 x Ø 6,80 THRU ALL`: the note's own leader ends 28 px from the note's ink and 181 px
    # from the `6,80`, so the number is only carried by the block it is printed in. The block is the note's
    # printed lines - two of them here, a line spacing apart - and not the text standing further off.
    number = _glyph(257.4, 1306.6, 249, 1292, 16, 28)
    digits = [_glyph(287.4, 1304.5, 279, 1290, 18, 28), _glyph(307.4, 1303.9, 299, 1290, 18, 28)]
    words = [
        _glyph(336.0, 1301.7, 329, 1289, 15, 26),
        _glyph(355.0, 1304.3, 346, 1291, 19, 26),
        _glyph(379.8, 1303.2, 372, 1289, 16, 26),
        _glyph(402.3, 1305.9, 394, 1291, 17, 27),
        _glyph(439.0, 1305.7, 427, 1293, 25, 26),
        _glyph(458.3, 1306.9, 452, 1294, 13, 26),
    ]
    below = [_glyph(258.4, 1350.6, 251, 1337, 16, 28), _glyph(281.0, 1348.4, 272, 1335, 19, 26)]
    far = [_glyph(300.0, 1900.0, 292, 1886, 18, 28)]
    glyphs = [number, *digits, *words, *below, *far]
    cluster = [0, 1, 2]

    block = perceive._printed_block(glyphs, cluster)

    assert block is not None
    box, character = block
    assert box[0] == pytest.approx(249, abs=2) and box[2] == pytest.approx(465, abs=2), box
    assert box[1] == pytest.approx(1289, abs=2), box
    assert box[3] >= 1361, f"the note's second line is part of its block: {box}"
    assert character == pytest.approx(26, abs=3), character


def test_a_lone_number_is_its_own_block():
    # Nothing joins it, so the leader is asked about the number's own box, as it always was.
    alone = _glyph(700.0, 700.0, 690, 686, 18, 28)
    glyphs = [alone, _glyph(1600.0, 200.0, 1592, 186, 18, 28)]

    assert perceive._printed_block(glyphs, [0]) is None


def test_the_digits_own_line_gives_the_angle_a_number_is_written_at():
    # my_part.jpg prints `50` at 45 degrees along the diameter it measures. The two glyph centres state
    # that line exactly; a fit through the ink of the crop does not, because a digit's outline leans
    # away from the line its centre lies on.
    first = _glyph(860.2, 1646.3, 841, 1628, 41, 36)
    second = _glyph(881.1, 1666.0, 864, 1649, 35, 35)

    assert perceive._digits_angle([first, second], [0, 1]) == pytest.approx(43.4, abs=0.5)


def test_a_number_written_at_an_angle_is_offered_to_the_reader_at_its_own_angle_first():
    # The reader keeps its first answer, so the order of the angles is the whole question: offered the
    # crop as it stands, `50` printed at 45 degrees came back `2`; offered at the digits' own angle it
    # reads `50`.
    angles = perceive._reading_angles(43.4, -37.4)

    assert angles[0] == pytest.approx(43.4)
    assert angles[1:] == (0.0, 37.4, 90.0, -90.0), "the angles it was read at before are all still there"


def test_text_already_on_an_axis_keeps_the_order_it_had():
    # A number written level, or up a vertical dimension, is already levelled by `_reading_turn` and its
    # sense comes from the separator: the drawing says nothing new about it.
    assert perceive._reading_angles(0.0, 0.0) == (0.0, 90.0, -90.0)
    assert perceive._reading_angles(90.0, 0.0) == (0.0, 90.0, -90.0)


def test_a_vertical_number_is_levelled_by_the_quarter_turn_and_not_by_its_own_line():
    # The plate sheet's own `80,00` up a vertical line: its digits' line is vertical, so measured in the
    # crop's own frame - after the quarter turn - it is a level line and adds no angle of its own.
    digits = [_glyph(162.0, y, 148, int(y) - 9, 27, 18) for y in (840.0, 860.0, 891.0, 910.0)]
    comma = _glyph(174.0, 875.0, 170, 873, 8, 4, separator=True)
    glyphs = [*digits, comma]
    cluster = list(range(len(glyphs)))
    turn = perceive._reading_turn(glyphs, cluster)

    assert turn == 90
    own = perceive._digits_angle(glyphs, cluster) + turn
    assert perceive._reading_angles(own, 0.0) == (0.0, 90.0, -90.0)


def test_a_row_of_one_shape_is_one_number_and_a_digit_that_crosses_it_is_not():
    # my_part.jpg's `50`, printed at 45 degrees: two digits turned together, and a digit turned by 45
    # degrees is as wide as it is tall whatever its own shape.
    level = [_glyph(860.2, 1646.3, 841, 1628, 41, 36), _glyph(881.1, 1666.0, 864, 1649, 35, 35)]

    assert perceive._one_pen(level, [0, 1])


def test_a_blob_from_the_number_that_crosses_the_row_breaks_it():
    # The plastic sheet's drawn `R8.00` at 45 degrees, with the 29x18 blob of the vertical number beside
    # it in the same cluster: 0.62 against 0.96. The crop of the two together read `28.006`, a number
    # printed nowhere on the sheet.
    row = [
        _glyph(483.0, 642.9, 468, 630, 28, 30),
        _glyph(497.6, 659.0, 485, 647, 26, 25),
        _glyph(519.2, 680.5, 507, 669, 25, 24),
        _glyph(533.6, 694.8, 522, 683, 25, 25),
        _glyph(546.8, 715.4, 533, 707, 29, 18),
    ]

    assert not perceive._one_pen(row, list(range(len(row))))


def test_the_widest_spread_a_real_row_showed_is_still_one_pen():
    # The flange's `#50`: three blobs 0.23 apart, the loosest row the sheets offer.
    row = [
        _glyph(1537.4, 1648.9, 1529, 1640, 18, 19),
        _glyph(1521.3, 1672.5, 1506, 1650, 31, 43),
        _glyph(1498.7, 1687.4, 1490, 1666, 21, 36),
    ]

    assert perceive._one_pen(row, list(range(len(row))))


_BLANK = np.zeros((4, 4), dtype=np.uint8)


def _measured(serial: int, value: float, length: float, mode: AnchorMode = "dimension") -> Span:
    """A reading of `value`, carried by a dimension line `length` pixels long."""
    return Span(
        id=f"ocr-{serial}",
        text=f"{value:.2f}",
        value=value,
        bbox=BBox(x=0, y=0, w=10, h=10),
        anchors=[[0.0, 0.0], [length, 0.0]],
        anchor_mode=mode,
    )


def _calibrated_sheet() -> list[Span]:
    """Four readings the sheet itself agrees on, at 7.85 px/mm."""
    return [
        _measured(0, 15.0, 117.8),
        _measured(1, 60.0, 471.3),
        _measured(2, 80.0, 628.4),
        _measured(3, 100.0, 785.5),
    ]


def test_a_reading_the_sheet_calls_wrong_is_read_again_and_the_fitting_candidate_kept(monkeypatch):
    # The plate's own case: the vertical `8,00` comes back `3,00` at the angle its digits' own line gives
    # — 63 px of dimension line against 3 mm is 21 px/mm where the sheet fits 7.85 — and `8,00` two degrees
    # past it, which fits. The reader keeps its first answer; the sheet says that answer is wrong.
    spans = _calibrated_sheet() + [_measured(4, 3.0, 63.0)]
    clusters = {id(spans[4]): [0, 1]}
    seen = []

    def reread(gray, glyphs, cluster, serial, reader, anchors, mode, skip=0):
        seen.append(skip)
        return _measured(0, 8.0, 63.0)

    monkeypatch.setattr(perceive, "_read_cluster", reread)

    out = perceive._reread_against_the_sheet_scale(_BLANK, [], spans, clusters, None)

    assert out[4].value == 8.0
    assert out[4].text == "8.00"
    assert seen == [1]


def test_a_second_reading_that_does_not_fit_the_sheet_is_not_kept(monkeypatch):
    # A re-read no better than the reading it was meant to replace leaves the sheet as it was.
    spans = _calibrated_sheet() + [_measured(4, 3.0, 63.0)]
    clusters = {id(spans[4]): [0, 1]}
    monkeypatch.setattr(perceive, "_read_cluster", lambda *a, **k: _measured(0, 5.0, 63.0))

    out = perceive._reread_against_the_sheet_scale(_BLANK, [], spans, clusters, None)

    assert out[4].value == 3.0


def test_a_number_a_leader_carries_is_not_asked_again(monkeypatch):
    # The plate's `50,00` rides a stroke the gate reads as a leader — its other arrow is not drawn, or not
    # found — and a leader's two ends say nothing about the value: 617.6 px against 50 mm is 12.35 px/mm
    # on a sheet fitting 7.85, and the sheet cannot call that wrong because its own line is not the pair
    # being compared. So no angle is offered again, and this number is read wrong for good.
    spans = _calibrated_sheet() + [_measured(4, 50.0, 617.6, mode="leader")]
    clusters = {id(spans[4]): [0, 1]}
    calls = []
    monkeypatch.setattr(perceive, "_read_cluster", lambda *a, **k: calls.append(k) or _measured(0, 90.0, 617.6))

    out = perceive._reread_against_the_sheet_scale(_BLANK, [], spans, clusters, None)

    assert out[4].value == 50.0
    assert calls == []


def test_a_sheet_too_sparse_to_calibrate_is_left_alone(monkeypatch):
    # flange-1 and studycadcam-50 fit no scale at all, and the re-read never runs where there is none.
    spans = [_measured(0, 5.0, 100.0), _measured(1, 10.0, 40.0)]
    calls = []
    monkeypatch.setattr(perceive, "_read_cluster", lambda *a, **k: calls.append(k) or _measured(0, 20.0, 100.0))

    out = perceive._reread_against_the_sheet_scale(_BLANK, [], spans, {}, None)

    assert [span.value for span in out] == [5.0, 10.0]
    assert calls == []


def test_the_vision_model_is_not_asked_the_same_crop_at_another_angle(monkeypatch):
    # A model call is minutes a sheet, and its answer is not a function of the angle it was asked at, so
    # skipping to the next angle means nothing there.
    spans = _calibrated_sheet() + [_measured(4, 3.0, 63.0)]
    calls = []
    monkeypatch.setattr(perceive, "_read_cluster", lambda *a, **k: calls.append(k) or _measured(0, 8.0, 63.0))

    out = perceive._reread_against_the_sheet_scale(_BLANK, [], spans, {id(spans[4]): [0]}, reader=object())

    assert out[4].value == 3.0
    assert calls == []


def _row_segments(horizontals, uprights, thickness: float = 2.0):
    """The strokes of one row: the collinear pieces the number sits in, and the strokes crossing it."""
    from drawingto3d import lines

    made = [
        lines.Segment(x0=float(x0), y0=float(y), x1=float(x1), y1=float(y), thickness=thickness, horizontal=True)
        for x0, x1, y in horizontals
    ]
    made.extend(
        lines.Segment(x0=float(x), y0=float(y0), x1=float(x), y1=float(y1), thickness=thickness, horizontal=False)
        for x, y0, y1 in uprights
    )
    return made


def test_a_reading_is_moved_to_the_pair_of_crossings_its_value_fits():
    # The plastic sheet's shape: twenty auditable readings, fifteen of them small numbers on long lines.
    # The gate chooses a span without knowing the value, so a `1.50` whose value is 5.9 px was given the
    # 113.5 px line next to it. The sheet has already calibrated itself; the value picks its own pair.
    spans = _calibrated_sheet() + [_measured(4, 20.0, 300.0)]
    spans[4].bbox = BBox(x=120, y=40, w=60, h=20)
    segments = _row_segments([(20, 140, 50), (200, 320, 50)], [(120, 20, 80), (277, 20, 80)])

    out = perceive._repoint_lines_that_are_not_their_own(segments, spans)

    (x0, _y0), (x1, _y1) = out[4].anchors
    assert x0 == pytest.approx(120, abs=2)
    assert x1 == pytest.approx(277, abs=3)


def test_a_row_with_no_pair_that_fits_leaves_the_reading_where_the_gate_put_it():
    # A reading whose row offers nothing that fits is left exactly as it was. Dropping its anchors is a
    # separate decision: on the plastic sheet most of the readings that survive this are not printed
    # numbers at all (an arrowhead read as a digit), and an anchor dropped from those hides a fake number.
    spans = _calibrated_sheet() + [_measured(4, 20.0, 300.0)]
    spans[4].bbox = BBox(x=120, y=40, w=60, h=20)
    segments = _row_segments([(20, 140, 50), (200, 320, 50)], [(250, 20, 80), (290, 20, 80)])

    out = perceive._repoint_lines_that_are_not_their_own(segments, spans)

    assert out[4].anchors == [[0.0, 0.0], [300.0, 0.0]]


def test_the_gap_beside_the_line_a_number_stands_on_is_its_own_span():
    # The plastic sheet's `4.80`: its dimension is drawn with the arrows outside the span, so the stretch
    # the gate took (the run above the arrow) is not the span — the span is the gap between that run's own
    # end and the next crossing, and it fits the value.
    spans = _calibrated_sheet() + [_measured(4, 20.0, 120.0)]
    spans[4].bbox = BBox(x=120, y=40, w=60, h=20)
    segments = _row_segments([(20, 140, 50), (200, 320, 50)], [(120, 20, 80), (277, 20, 80)])

    out = perceive._repoint_lines_that_are_not_their_own(segments, spans)

    (x0, _y0), (x1, _y1) = out[4].anchors
    assert x0 == pytest.approx(120, abs=2)
    assert x1 == pytest.approx(277, abs=3)


def test_a_pair_past_the_end_of_the_line_a_number_stands_on_is_not_its_span():
    # Measured: a datum symbol the reader called a `2` was offered, and took, an 8 px gap 25 px past the end
    # of the line it stood on. It fitted the value, and it stopped the sheet naming a record that is not a
    # printed number at all: a repair is a span at the line the number sits on, never a span further along.
    spans = _calibrated_sheet() + [_measured(4, 20.0, 100.0)]
    spans[4].bbox = BBox(x=120, y=40, w=60, h=20)
    segments = _row_segments([(20, 100, 50), (200, 320, 50)], [(280, 20, 80), (437, 20, 80)])

    out = perceive._repoint_lines_that_are_not_their_own(segments, spans)

    assert out[4].anchors == [[0.0, 0.0], [100.0, 0.0]]
