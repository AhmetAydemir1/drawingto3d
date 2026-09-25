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
