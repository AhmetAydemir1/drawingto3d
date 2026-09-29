"""The sheet's own scale, measured from the dimension lines themselves.

A dimension line is drawn between the two points it measures, so its pixel length divided by the number
printed on it is the sheet's scale (pixels per millimetre). Nothing here needs the title block, the
drawing scale note, or the raster's dpi: the sheet calibrates itself from its own dimensions. Once it is
calibrated, a value that was misread stops matching its own line, and that is a mistake the software can
report without being told the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

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
    """The spans that carry a printed value and the two ends of their own dimension line.

    A span whose anchors came from its own value (`anchor_source == "value"`) is left out: its line was
    picked with the sheet's scale, so letting it back into `measure` would make the scale evidence for
    itself (review5 V01). It stays geometry for the coder — it is just not calibration evidence.
    """
    return [
        span
        for span in spans
        if span.anchor_mode == "dimension"
        and span.value is not None
        and len(span.anchors) == 2
        and getattr(span, "anchor_source", None) != "value"
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


def _agreeing_pair(usable: list[tuple[float, float]], tolerance: float = RELATIVE_TOLERANCE) -> bool:
    """Do any two readings imply the same scale? Two is not enough to calibrate, but enough to contradict."""
    for index, (value, measured) in enumerate(usable):
        for other_value, other_measured in usable[index + 1:]:
            if abs((other_measured / other_value) / (measured / value) - 1.0) <= tolerance:
                return True
    return False


def verdict(spans, minimum: int = 3, witnesses: Sequence = ()) -> dict:
    """The one thing that can be said about the sheet's own scale, in one of four states.

    `witnesses` are the pairs that never made it into a record: `(reading kimliği, değer, ölçülen px)`, one
    entry per reading-and-stroke candidate. They are what lets a sheet whose *placed* readings fall one short
    of `minimum` still name its scale, because a reading does not stop being evidence when the gate declines
    to place it (H-R17). They are counted per reading, never per pair (review6 W01).

    `calibrated` / `calibrated_with_suspects`: at least `minimum` readings hold the same scale, so the
    numbers are confirmed against the sheet's own geometry and `suspect` names the ones that do not fit.
    `uncalibrated`: the readings cannot settle a scale — either there are fewer than two, or some pair
    agrees but fewer than `minimum` readings support it. Nothing contradicts anything here.
    `contradictory`: two or more readings and *no* pair of them holds the same scale. This is not "the
    scale could not be read": the numbers deny each other, so at least one of them is wrong and which one
    is unknowable from this sheet. One sheet is not drawn at three different scales; building a solid from
    such a set of readings is the shortest way to call a wrong part right. Measured on `pilot-block-01`:
    4, 9 and 60 mm read off 54, 467.5 and 506 px lines — 13.5, 51.9 and 8.4 px/mm on one sheet.
    """
    pairs = measure(spans)
    calibration, inliers = consensus(pairs, minimum=minimum)
    witness_groups = _witness_groups(witnesses)
    usable = [(value, measured) for value, measured in pairs if value > 0 and measured > 0]
    from_witnesses = False
    if calibration is None and witness_groups:
        # Yerleşmiş okumalar `minimum`'a ulaşmadığında ölçek aday çiftlerden kurulur: bir okuma, kapı onu
        # kayda çevirmedi diye kanıt olmaktan çıkmaz (H-R17). Okuma başına tek oy (review6 W01).
        calibration = _calibration_from_witnesses(witness_groups, minimum=minimum)
        from_witnesses = calibration is not None
    if from_witnesses and calibration is not None:
        # Tanık ölçeği, kapının kendi yerleştirdiği okumaların **çoğunluğu** tarafından desteklenmedikçe
        # paftanın ölçeği sayılmaz. Yoksa benzer iki yanlış eşleşmeden doğan bir oran, doğru okumaları
        # şüpheli gösteren bir çoğunluk yaratıyor. Ölçüldü (examples/flange-elbow-90.png): 12 yerleşmiş
        # okumanın 2'si 0.5077 px/mm'de buluşuyor ve o ölçek 10 okumayı şüpheli ilan ediyordu; 0.5077 px/mm
        # ile 2500 px'lik pafta 5 metrelik bir parça olurdu. block-01'de durum tersi: 2 yerleşmiş okumanın
        # 1'i (60/506 px = 8.433) tanık ölçeğini tutuyor ve öteki okuma paftanın `55` yazdığı yeri `9`
        # okuyor — orada şüpheli ilan edilen okuma gerçekten yanlış.
        agreeing = sum(1 for value, length in usable if not calibration.disagrees(value, length))
        if agreeing * 2 < len(usable):
            calibration = None
            from_witnesses = False
    report = {
        "schema": "drawingto3d.sheet-scale/1",
        "readings": len(pairs),
        "usable_readings": len(usable),
        "witness_readings": len(witness_groups),
        "px_per_mm": round(calibration.px_per_mm, 4) if calibration else None,
        "samples": calibration.samples if calibration else 0,
        "spread": round(calibration.spread, 4) if calibration else None,
        "ratios": [round(measured / value, 4) for value, measured in usable],
        "inliers": inliers,
        "suspect": [],
    }
    if calibration is not None:
        suspects = [span.id for span in measure_spans(spans)
                    if calibration.disagrees(float(span.value), line_length(span))]
        report["suspect"] = suspects
        report["state"] = "calibrated" if not suspects else "calibrated_with_suspects"
        if inliers == 0 and witness_groups:
            report["note"] = (f"ölçek yerleşmiş okumalardan kurulamadı; {calibration.samples} okumanın aday "
                              f"çiftleri {calibration.px_per_mm:.3f} px/mm diyor")
        return report
    if len(usable) >= 2 and not _agreeing_pair(usable):
        report["state"] = "contradictory"
        report["note"] = (f"{len(usable)} okuma var ve hiçbiri ötekilerle aynı ölçeği tutmuyor: "
                          f"paftanın sayıları birbirini yalanlıyor")
        return report
    report["state"] = "uncalibrated"
    if len(usable) >= 2:
        report["note"] = (f"ölçülecek okuma sayısı {len(usable)}: en az ikisi aynı ölçeği tutuyor ama "
                          f"ölçek için {minimum} okuma gerekiyor")
    else:
        report["note"] = f"ölçülecek okuma sayısı {len(usable)} < 2: ölçek doğrulanamadı"
    return report


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


def _witness_groups(witnesses: Sequence[tuple[str, float, float]]) -> dict[str, list[float]]:
    """Aday çiftleri okuma kimliğine göre topla: her okumanın öne sürdüğü oranlar."""
    groups: dict[str, list[float]] = {}
    for reading_id, value, length in witnesses:
        if value > 0 and length > 0:
            groups.setdefault(str(reading_id), []).append(length / value)
    return groups


def _calibration_from_witnesses(groups: dict[str, list[float]], minimum: int,
                                tolerance: float = RELATIVE_TOLERANCE) -> Calibration | None:
    """Ölçek, aday çiftlerden: okuma başına bir oy (review6 W01).

    Bir okumanın yanında üç çizgi bulunması üç okuma sayılmaz — kazanan kümede en az `minimum` **tekil
    okuma** olmalı ve her okuma en yakın oranıyla bir kez oy verir. Aynı sayıda okumayı açıklayan ve
    kazananla hiç örtüşmeyen ikinci bir küme varsa pafta hangisine çizildiğini söylemiyor demektir: ölçek
    döndürülmez, çünkü ilk deneneni seçmek tahmin olurdu.
    """
    def window(ratio: float) -> dict[str, float]:
        low, high = ratio / (1 + tolerance), ratio * (1 + tolerance)
        inside: dict[str, float] = {}
        for reading_id, ratios in groups.items():
            near = [other for other in ratios if low <= other <= high]
            if near:
                inside[reading_id] = min(near, key=lambda other: abs(other - ratio))
        return inside

    best: dict[str, float] | None = None
    for ratios in groups.values():
        for ratio in ratios:
            inside = window(ratio)
            if best is None or len(inside) > len(best):
                best = inside
    if best is None or len(best) < minimum:
        return None
    for ratios in groups.values():
        for ratio in ratios:
            inside = window(ratio)
            if len(inside) >= len(best) and not set(inside) & set(best):
                return None
    fitted = sorted(best.values())
    px_per_mm = fitted[len(fitted) // 2]
    spread = (fitted[-1] - fitted[0]) / px_per_mm if px_per_mm > 0 else 0.0
    return Calibration(px_per_mm=px_per_mm, samples=len(fitted), spread=spread)
