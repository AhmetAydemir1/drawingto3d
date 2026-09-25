"""Geometry of reading: which glyphs are one printed number, and which candidate belongs to a line."""

from drawingto3d import perceive
from drawingto3d.schema import BBox, Span


def _glyph(centre_x: float, centre_y: float, x: int, y: int, w: int, h: int) -> tuple:
    return (centre_x, centre_y, x, y, w, h)


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
