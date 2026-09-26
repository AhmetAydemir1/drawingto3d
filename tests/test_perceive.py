"""Geometry of reading: which glyphs are one printed number, and which candidate belongs to a line."""

from drawingto3d import perceive
from drawingto3d.schema import BBox, Span


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
