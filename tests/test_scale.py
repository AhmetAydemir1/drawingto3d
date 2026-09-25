import pytest

from drawingto3d.scale import audit, calibrate, consensus
from drawingto3d.schema import BBox, Span

SHEET = [(50.0, 208.5), (20.0, 83.4), (80.0, 333.6), (35.0, 146.0), (57.0, 237.7)]


def _span(serial: int, value: float, anchors: list[list[float]], mode: str = "dimension") -> Span:
    return Span(
        id=f"ocr-{serial}",
        text=str(value),
        value=value,
        bbox=BBox(x=anchors[0][0], y=anchors[0][1], w=10, h=10),
        anchors=anchors,
        anchor_mode=mode,
    )


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


def test_audit_names_the_reading_that_does_not_fit_the_sheets_own_scale():
    # Four dimensions drawn to scale, and one whose number was misread as 37 (the sheet prints 57).
    spans = [
        _span(0, 50.0, [[0.0, 0.0], [208.5, 0.0]]),
        _span(1, 20.0, [[0.0, 20.0], [83.4, 20.0]]),
        _span(2, 80.0, [[0.0, 40.0], [333.6, 40.0]]),
        _span(3, 35.0, [[0.0, 60.0], [146.0, 60.0]]),
        _span(4, 37.0, [[0.0, 80.0], [237.7, 80.0]]),
    ]

    calibration, suspect = audit(spans)

    assert calibration is not None
    assert calibration.px_per_mm == pytest.approx(4.17, abs=0.03)
    assert suspect == ["ocr-4"]


def test_a_leader_is_not_audited_against_a_scale():
    # A callout's arrow points at a feature; its tail is only where the words are, so its length is not
    # a measurement and must not be fed into the sheet's scale.
    spans = [
        _span(0, 50.0, [[0.0, 0.0], [208.5, 0.0]]),
        _span(1, 20.0, [[0.0, 20.0], [83.4, 20.0]]),
        _span(2, 80.0, [[0.0, 40.0], [333.6, 40.0]]),
        _span(3, 35.0, [[0.0, 60.0], [146.0, 60.0]]),
        _span(4, 25.0, [[0.0, 80.0], [90.0, 80.0]], mode="leader"),
    ]

    calibration, suspect = audit(spans)

    assert calibration is not None
    assert calibration.samples == 4
    assert suspect == []


def test_consensus_keeps_the_true_scale_even_when_most_readings_are_wrong():
    # Three lines read right, six misread: a median fit is dragged off by the wrong majority, while the
    # scale the three agree on is still the largest group of readings that share one.
    pairs = [
        (50.0, 208.5),
        (20.0, 83.4),
        (80.0, 333.6),
        (5.0, 237.7),  # a 57 read as 5
        (7.0, 146.0),  # a 35 read as 7
        (3.0, 208.5),
        (8.0, 83.4),
        (2.0, 333.6),
        (4.0, 146.0),
    ]

    calibration, agreeing = consensus(pairs)

    assert calibration is not None
    assert calibration.px_per_mm == pytest.approx(4.17, abs=0.02)
    assert agreeing == [0, 1, 2]
    assert cal_median() != pytest.approx(4.17, abs=0.5)  # what a median fit would have produced


def cal_median() -> float:
    return calibrate([(5.0, 237.7), (7.0, 146.0), (3.0, 208.5), (8.0, 83.4), (2.0, 333.6)]).px_per_mm
