import numpy as np
import pytest

from drawingto3d.reader import read_dimension


class _QueueReader:
    """Answers one scripted reply per call, so the order of rotations can be checked."""

    def __init__(self, *answers: str | None) -> None:
        self.answers = list(answers)
        self.calls = 0

    def read(self, crop: np.ndarray) -> str | None:
        self.calls += 1
        return self.answers.pop(0) if self.answers else None


CROP = np.zeros((40, 30), dtype=np.uint8)


def test_a_horizontal_dimension_is_read_once_as_it_stands():
    reader = _QueueReader("20")
    assert read_dimension(reader, CROP, vertical=False) == "20"
    assert reader.calls == 1


def test_the_calibrated_length_decides_which_turn_of_a_vertical_dimension_to_believe():
    # The sheet prints 80 on a line 470 px long; sideways the model answers R100 on one turn.
    reader = _QueueReader("R100", "80")
    assert read_dimension(reader, CROP, vertical=True, expected_mm=80.0) == "80"
    assert reader.calls == 2


def test_without_a_calibration_the_first_number_read_is_taken():
    reader = _QueueReader("R100", "80")
    assert read_dimension(reader, CROP, vertical=True) == "R100"


def test_a_read_that_is_not_a_number_is_skipped():
    reader = _QueueReader("pipe size", "80")
    assert read_dimension(reader, CROP, vertical=True) == "80"


def test_both_turns_unreadable_gives_nothing():
    reader = _QueueReader(None, None)
    assert read_dimension(reader, CROP, vertical=True) is None


@pytest.mark.parametrize("printed,answer", [("35", "35"), ("Ø20", "Ø20"), ("R20", "R20")])
def test_dimension_marks_survive_the_read(printed, answer):
    assert read_dimension(_QueueReader(answer), CROP, vertical=False) == printed
