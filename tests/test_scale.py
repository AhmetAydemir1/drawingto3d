import pytest

from drawingto3d.scale import calibrate

SHEET = [(50.0, 208.5), (20.0, 83.4), (80.0, 333.6), (35.0, 146.0), (57.0, 237.7)]


def test_scale_is_measured_from_the_dimension_lines_themselves():
    calibration = calibrate(SHEET)
    assert calibration is not None
    assert calibration.px_per_mm == pytest.approx(4.17, abs=0.02)
    assert calibration.samples == 5


def test_a_misread_number_stops_matching_its_own_line():
    # The sheet prints 57; a reader that says 37 is caught by the line the number sits on.
    calibration = calibrate(SHEET)
    assert calibration is not None
    assert calibration.disagrees(37.0, 237.7)
    assert not calibration.disagrees(57.0, 237.7)


def test_too_few_dimensions_cannot_calibrate_a_sheet():
    assert calibrate([(20.0, 83.4), (50.0, 208.5)]) is None


def test_a_sheet_in_inches_calibrates_the_same_way():
    # The same lines described in inches: 1.97in over 208.5 px is 105.8 px per inch.
    calibration = calibrate([(1.97, 208.5), (0.79, 83.4), (3.15, 333.6), (1.38, 146.0)])
    assert calibration is not None
    assert calibration.px_per_mm == pytest.approx(105.8, abs=0.5)
