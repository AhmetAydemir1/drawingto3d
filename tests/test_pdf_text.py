"""Grouping a PDF's characters into the numbers it prints, without a model and without a sheet statistic."""

from drawingto3d import ingest


def _laid_out(text: str, x: float, y: float, size: float, advance: float, gap: float = 0.0) -> list[tuple]:
    """Characters of `text` in a row, each `advance` wide with `gap` of space between them."""
    chars, cursor = [], x
    for character in text:
        chars.append((character, cursor, y, cursor + advance, y + size))
        cursor += advance + gap
    return chars


def _typeset(parts: list[tuple[str, float]], x: float, y: float, size: float, advance: float) -> list[tuple]:
    """A run of characters where each part says how much space follows it: `[('1', 9), ('1/4', 0)]`."""
    chars, cursor = [], x
    for text, gap in parts:
        for character in text:
            chars.append((character, cursor, y, cursor + advance, y + size))
            cursor += advance
        cursor += gap
    return chars


def _stacked(text: str, x: float, y: float, size: float, advance: float, gap: float = 0.0) -> list[tuple]:
    """A number printed a quarter turn round: its characters go down, not across."""
    chars, cursor = [], y
    for character in text:
        chars.append((character, x, cursor, x + size * 0.6, cursor + advance))
        cursor += advance + gap
    return chars


def test_characters_side_by_side_are_one_number():
    phrases = ingest._group_along(_laid_out("35", 100.0, 50.0, size=20.0, advance=13.0))
    assert [text for text, _box, _members in phrases] == ["35"]


def test_a_number_drawn_a_quarter_turn_round_is_one_number():
    # Down a vertical dimension line the digits stack; read across, they are four separate characters.
    phrases = ingest._group_along(_stacked("35", 100.0, 50.0, size=20.0, advance=17.0))
    assert [text for text, _box, _members in phrases] == ["35"]


def test_a_gap_wide_enough_to_be_a_space_keeps_it():
    # 1 1/4 is one dimension of 1.25 inches; closing the space makes it eleven quarters.
    chars = _typeset([("1", 9.0), ("1/4", 0.0)], 100.0, 50.0, size=20.0, advance=12.0)
    phrases = ingest._group_along(chars)
    text = phrases[0][0]
    assert text == "1 1/4"
    assert ingest.parse_dimension_unit(text) == (ingest.SpanKind.linear, 1.25, "in")


def test_the_space_a_narrow_digit_leaves_is_not_a_space():
    phrases = ingest._group_along(_laid_out("100,00", 100.0, 50.0, size=20.0, advance=13.0))
    assert phrases[0][0] == "100,00"
    assert ingest.parse_dimension_unit(phrases[0][0])[1] == 100.0


def test_two_numbers_a_blank_apart_stay_two_numbers():
    chars = _laid_out("20", 100.0, 50.0, size=20.0, advance=13.0)
    chars += _laid_out("35", 240.0, 50.0, size=20.0, advance=13.0)
    phrases = ingest._group_along(chars)
    assert [text for text, _box, _members in phrases] == ["20", "35"]


def test_a_word_after_the_number_says_how_not_how_big():
    assert ingest.parse_dimension_unit("4 x 6,80 THRU ALL")[1] == 6.8
    assert ingest.parse_dimension_unit("Ø20 DEEP")[0] == ingest.SpanKind.diameter
    assert ingest.parse_dimension_unit("Ø20 DEEP")[1] == 20.0
    # Two numbers in one phrase is a genuine ambiguity (`Ø20 DEEP 12`): a person has to say which is which.
    assert ingest.parse_dimension_unit("Ø20 DEEP 12")[1] is None
    assert ingest.parse_dimension_unit("M8 - 6H THRU ALL")[1] is None
    assert ingest.parse_dimension_unit("1.563in")[1] == 1.563
