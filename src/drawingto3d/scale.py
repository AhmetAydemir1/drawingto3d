"""The sheet's own scale, measured from the dimension lines themselves.

A dimension line is drawn between the two points it measures, so its pixel length divided by the number
printed on it is the sheet's scale (pixels per millimetre). Nothing here needs the title block, the
drawing scale note, or the raster's dpi: the sheet calibrates itself from its own dimensions. Once it is
calibrated, a value that was misread stops matching its own line, and that is a mistake the software can
report without being told the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

RELATIVE_TOLERANCE = 0.04


@dataclass(frozen=True)
class Calibration:
    """Pixels per millimetre for one sheet, and how well each dimension agreed with it."""

    px_per_mm: float
    samples: int
    spread: float

    def expected_px(self, value_mm: float) -> float:
        return value_mm * self.px_per_mm

    def residual(self, value_mm: float, measured_px: float) -> float:
        """Measured length as a fraction away from what the printed number says it should be."""
        expected = self.expected_px(value_mm)
        if expected <= 0:
            return float("inf")
        return measured_px / expected - 1.0

    def disagrees(self, value_mm: float, measured_px: float) -> bool:
        return abs(self.residual(value_mm, measured_px)) > RELATIVE_TOLERANCE


def measure(spans) -> list[tuple[float, float]]:
    """(printed value in mm, length of its own dimension line in px) for every span that carries both."""
    pairs = []
    for span in measure_spans(spans):
        (x0, y0), (x1, y1) = span.anchors[0], span.anchors[1]
        length = ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5
        if length > 0:
            pairs.append((float(span.value), length))
    return pairs


def audit(spans) -> tuple[Calibration | None, list[str]]:
    """The sheet's scale, and which of its readings do not fit it.

    Every dimension line is drawn to the number printed on it, so once the sheet has a scale, a value
    that was misread — or a number matched up with a line that was never its line — shows up as a pair
    whose length does not agree. No ground truth is needed to notice that something is wrong.
    """
    pairs = measure(spans)
    calibration, agreeing = consensus(pairs)
    if calibration is None:
        return None, []
    trusted = {index for index in agreeing}
    suspect = [
        span.id
        for index, span in enumerate(measure_spans(spans))
        if index not in trusted
    ]
    return calibration, suspect


def measure_spans(spans) -> list:
    """The spans that carry a printed value and the two ends of their own dimension line."""
    return [
        span
        for span in spans
        if span.anchor_mode == "dimension" and span.value is not None and len(span.anchors) == 2
    ]


def consensus(pairs: list[tuple[float, float]], tolerance: float = RELATIVE_TOLERANCE, minimum: int = 3) -> tuple[Calibration | None, list[int]]:
    """The scale that most of the sheet agrees on, and which readings agree with it.

    A misread number is a pair whose ratio is off, so every pair's ratio is tried as the sheet's scale and
    the one that the most pairs fit wins. Fitting a median instead assumes the majority of readings are
    right; this does not, and it also says *which* readings were right — the rest are the ones to look at
    again, or to ask about.
    """
    usable = [(index, value, measured) for index, (value, measured) in enumerate(pairs) if value > 0 and measured > 0]
    if len(usable) < minimum:
        return None, []
    best_hypothesis, best_inliers = 0.0, []
    for _, value, measured in usable:
        hypothesis = measured / value
        inliers = [index for index, other_value, other_measured in usable if abs(other_measured / other_value / hypothesis - 1.0) <= tolerance]
        if len(inliers) > len(best_inliers):
            best_hypothesis, best_inliers = hypothesis, inliers
    if len(best_inliers) < minimum:
        return None, []
    fitted = sorted(pairs[index][1] / pairs[index][0] for index in best_inliers)
    px_per_mm = fitted[len(fitted) // 2]
    spread = (fitted[-1] - fitted[0]) / px_per_mm if px_per_mm > 0 else 0.0
    return Calibration(px_per_mm=px_per_mm, samples=len(best_inliers), spread=spread), sorted(best_inliers)


def calibrate(pairs: list[tuple[float, float]], tolerance: float = RELATIVE_TOLERANCE) -> Calibration | None:
    """Fit pixels per millimetre to (value, measured length) pairs, ignoring the ones far off the pack.

    A misread number is exactly a pair whose ratio is off, so the fit uses the median of the ratios and
    drops the values that fall outside `tolerance` once, then fits again on what is left.
    """
    usable = [(value, measured) for value, measured in pairs if value > 0 and measured > 0]
    if len(usable) < 3:
        return None
    ratios = sorted(measured / value for value, measured in usable)
    median = ratios[len(ratios) // 2]
    kept = [(value, measured) for value, measured in usable if abs(measured / value / median - 1.0) <= tolerance]
    if len(kept) < 3:
        kept = usable
    fitted = sorted(measured / value for value, measured in kept)
    px_per_mm = fitted[len(fitted) // 2]
    spread = (fitted[-1] - fitted[0]) / px_per_mm if px_per_mm > 0 else 0.0
    return Calibration(px_per_mm=px_per_mm, samples=len(kept), spread=spread)
