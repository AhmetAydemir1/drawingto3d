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
# A dimension line can be drawn a pixel or two wrong end to end, and the 4% above is a fraction of the
# *value*: on a 1:2 sheet a 1.5 mm dimension is 6 px, where 4% is a quarter of a pixel and one pixel of
# arrowhead or extension line is 17%. The absolute floor is the sheet's own drawn weight — the ink a line
# is made of — so a small dimension is judged in pixels instead of being called wrong by arithmetic that
# no drawing could satisfy.
ABSOLUTE_PX = 2.5


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
        """Is this reading off the line it was read from by more than the drawing can carry?

        Judged against the larger of a relative tolerance and an absolute one in the sheet's own pixels:
        4% of a 6 px dimension is a quarter of a pixel, which no drawing holds, and calling that reading
        suspect says more about the arithmetic than about the sheet.
        """
        expected = self.expected_px(value_mm)
        return abs(measured_px - expected) > max(RELATIVE_TOLERANCE * expected, ABSOLUTE_PX)


def line_length(span) -> float:
    """How long the dimension line a span was read from is, in pixels."""
    (x0, y0), (x1, y1) = span.anchors[0], span.anchors[1]
    return ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5


def measure(spans) -> list[tuple[float, float]]:
    """(printed value in mm, length of its own dimension line in px) for every span that carries both."""
    pairs = []
    for span in measure_spans(spans):
        length = line_length(span)
        if length > 0:
            pairs.append((float(span.value), length))
    return pairs


def audit(spans) -> tuple[Calibration | None, list[str]]:
    """The sheet's scale, and which of its readings do not fit it.

    Every dimension line is drawn to the number printed on it, so once the sheet has a scale, a value
    that was misread — or a number matched up with a line that was never its line — shows up as a pair
    whose length does not agree. No ground truth is needed to notice that something is wrong.

    The fit is made from the ratios (`consensus`, where a majority is the sheet's scale and a single wrong
    ratio is outvoted), but each reading is then *judged* with `Calibration.disagrees`, which has the
    absolute pixel floor: a 1.5 mm dimension on a 1:2 sheet is 6 px, and a 6 px line whose ratio is 17%
    away from the fit is a drawing, not a misreading.
    """
    pairs = measure(spans)
    calibration, _agreement = consensus(pairs)
    if calibration is None:
        return None, []
    suspect = [
        span.id
        for span in measure_spans(spans)
        if calibration.disagrees(float(span.value), line_length(span))
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


def view_scales(spans, tolerance: float = RELATIVE_TOLERANCE, minimum: int = 2) -> dict:
    """The sheet's scale, and each view's own — because a sheet is not obliged to hold one scale.

    A detail view is commonly drawn larger than the view it details, and then its numbers fit a second
    scale. Pooling every reading into one fit makes the minority view's numbers look like misreadings of
    the majority's scale, which is the wrong conclusion about a sheet that is telling the truth twice.
    Grouped by the view each number sits in (`span.view_id`), the same fit is run per view, so a view whose
    scale is not the sheet's is *named* instead of averaged away.
    """
    grouped: dict[str, list[tuple[float, float]]] = {}
    for span in measure_spans(spans):
        name = getattr(span, "view_id", None) or "unnamed"
        grouped.setdefault(name, []).append((float(span.value), line_length(span)))
    every = [pair for rows in grouped.values() for pair in rows]
    sheet, _inliers = consensus(every, tolerance, minimum=3)
    views: dict[str, dict] = {}
    for name, rows in sorted(grouped.items()):
        calibration, inliers = consensus(rows, tolerance, minimum=minimum)
        views[name] = {
            "px_per_mm": round(calibration.px_per_mm, 4) if calibration else None,
            "readings": len(rows),
            "inliers": inliers,
            "own_scale": bool(calibration and sheet
                              and abs(calibration.px_per_mm / sheet.px_per_mm - 1.0) > tolerance),
        }
    return {"sheet_px_per_mm": round(sheet.px_per_mm, 4) if sheet else None,
            "views": views,
            "mixed_scale_views": sorted(name for name, row in views.items() if row["own_scale"])}


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
