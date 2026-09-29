"""Dimension lines: the thin, long, arrow-tipped strokes a printed number sits next to.

A technical drawing prints far more numbers than it has dimensions; the ones that size a feature sit
against a dimension line and nowhere else. Finding those lines prunes the candidate set and hands the
interpreter the two anchors (the line's ends, or the extension lines they stop at) it needs to turn a
number into geometry.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

# A stroke whose ink runs past this many characters of the sheet's own type is a line drawn on the
# sheet, not a word: measured on the plate sheet, printed blobs are 2.3 characters long at most and the
# leader of `6,80 THRU ALL` is 5.9 (158 px against a 27 px character).
TEXT_BOUND = 3.0

# How much of a stroke may lie in the text mask before the mask is asked whether it is telling the truth.
TEXT_FRACTION = 0.25


@dataclass(frozen=True)
class Segment:
    """A thin straight stroke of the drawing, in pixels."""

    x0: float
    y0: float
    x1: float
    y1: float
    thickness: float
    horizontal: bool

    @property
    def length(self) -> float:
        return abs(self.x1 - self.x0) if self.horizontal else abs(self.y1 - self.y0)

    @property
    def middle(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    def ends(self) -> list[tuple[float, float]]:
        return [(self.x0, self.y0), (self.x1, self.y1)]


@dataclass(frozen=True)
class Stroke:
    """A thin straight stroke at any angle, given by the two ends of its own centre line.

    A stroke that runs along an axis is a `Segment`: it can be found row by row, and it knows its axis,
    which is what makes its ends a range rather than a pair of points. A leader is drawn at whatever
    angle the sheet leaves room for, so most callouts are carried by a diagonal, and a diagonal has no
    axis to be found along: it is followed instead, and carries the ends of the line it lies on.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    thickness: float

    @property
    def length(self) -> float:
        return float(np.hypot(self.x1 - self.x0, self.y1 - self.y0))

    @property
    def middle(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    def ends(self) -> list[tuple[float, float]]:
        return [(self.x0, self.y0), (self.x1, self.y1)]


def _basis(stroke: Segment | Stroke) -> tuple[tuple[float, float], tuple[float, float]]:
    """The direction the stroke runs in, and the normal across it.

    An axis stroke knows its own axis and its ends are the corners of a range, so its axis is read from
    that flag rather than from the corner-to-corner line, which is off the centre by its own weight. A
    stroke at an angle carries the ends of its centre line, so it reads the direction from those.
    """
    horizontal = getattr(stroke, "horizontal", None)
    if horizontal is True:
        return (1.0, 0.0), (0.0, 1.0)
    if horizontal is False:
        return (0.0, 1.0), (1.0, 0.0)
    dx, dy = stroke.x1 - stroke.x0, stroke.y1 - stroke.y0
    length = float(np.hypot(dx, dy)) or 1.0
    return (dx / length, dy / length), (-dy / length, dx / length)


def _ink_across(binary: np.ndarray, x: float, y: float, normal: tuple[float, float], half: int) -> int:
    """Length of the ink stroke through a point, measured across the stroke.

    An arrow is wide across the line it sits on and a bare line is exactly its own weight: the same
    question an axis stroke is asked along its fixed direction, asked here along the stroke's own normal
    so it can be asked of a stroke at any angle.
    """
    start_x, start_y = int(round(x)), int(round(y))
    if not (0 <= start_y < binary.shape[0] and 0 <= start_x < binary.shape[1]) or binary[start_y, start_x] == 0:
        return 0
    steps = 1
    for direction in (-1, 1):
        for offset in range(1, half + 1):
            next_x = int(round(x + normal[0] * direction * offset))
            next_y = int(round(y + normal[1] * direction * offset))
            if not (0 <= next_y < binary.shape[0] and 0 <= next_x < binary.shape[1]) or binary[next_y, next_x] == 0:
                break
            steps += 1
    return steps


def diagonal_strokes(
    gray: np.ndarray,
    binary: np.ndarray,
    min_length: float,
    max_thickness: float,
    text_mask: np.ndarray | None = None,
    min_angle: float = 6.0,
    glyph_fraction: float = 0.75,
) -> list[Stroke]:
    """The thin strokes of the sheet that do not run along an axis: where a drawing keeps its callouts.

    A leader is drawn from the words to the feature at whatever angle fits, so a stroke list holding
    only horizontal and vertical lines loses every callout on the sheet. Measured on the eval sheets,
    the Ø and R numbers were exactly the ones left unread, and every one of them is carried by a stroke
    at an angle.

    The band a stroke has to be in is set by the sheet's own thin weight, not by a pixel count: on the
    sheets at hand the weight comes out 2-3 px and the outlines 5-6 px, so a leader is thin relative to
    the drawing it is printed on.

    `min_angle` is small on purpose. A line a drafting office draws at 8 degrees is not an axis stroke
    and the row-by-row pass reads it as thick and drops it, so anything past a few degrees has to be
    found here or nowhere: on the plate sheet the callout `Ø50,00` hangs on a line drawn at 8 degrees.

    A stroke lying inside printed words is a glyph, not a leader, but only when it is *mostly* inside
    them: the same `Ø50,00` line passes under the number it belongs to, and rejecting it for touching
    the words would throw away the callout with the glyph.
    """
    detector = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    found = detector.detect(gray)[0]
    if found is None:
        return []
    strokes: list[Stroke] = []
    for raw in found.reshape(-1, 4):
        x0, y0, x1, y1 = (float(value) for value in raw)
        angle = abs(np.degrees(np.arctan2(y1 - y0, x1 - x0))) % 180.0
        if angle < min_angle or abs(angle - 90.0) < min_angle:
            continue
        if float(np.hypot(x1 - x0, y1 - y0)) < min_length:
            continue
        thickness = _across_run(binary, x0, y0, x1, y1)
        if thickness <= 0.0 or thickness > max_thickness:
            continue
        candidate = Stroke(x0, y0, x1, y1, thickness)
        if text_fraction(text_mask, candidate) > glyph_fraction:
            continue
        strokes.append(candidate)
    return _merged(strokes, max_thickness)


def _across_run(binary: np.ndarray, x0: float, y0: float, x1: float, y1: float, half: int = 6, step: float = 3.0) -> float:
    """The ink's thickness across a stroke, counted the same way as an axis stroke's.

    `Segment.thickness` is a run of ink counted row by row, so a stroke's weight and the width an arrow
    has to reach are in the same unit only if a diagonal is measured as a run too. Measured as a
    half-width instead, a bare diagonal line comes out as wide as one of its own arrowheads and every
    leader looks arrowed at both ends: a leader once scored 26 wide samples at its blank end.

    The median of the samples that found ink, not of all of them: a faint line is darker along some of
    its length than along the rest, and a sample that misses it entirely is not evidence that the line is
    thin, only that the sheet prints it lightly - counting those as zero made every dimension line on the
    plate sheet measure no ink at all.
    """
    dx, dy = x1 - x0, y1 - y0
    length = float(np.hypot(dx, dy)) or 1.0
    normal = (-dy / length, dx / length)
    count = int(min(48.0, max(4.0, length / step)))
    runs = [
        _ink_across(binary, x0 + dx * (index + 0.5) / count, y0 + dy * (index + 0.5) / count, normal, half)
        for index in range(count)
    ]
    found = [run for run in runs if run > 0]
    return float(np.median(found)) if found else 0.0


def _angle_between(first: Stroke, second: Stroke) -> float:
    """How far apart two strokes point, off 180 degrees: strokes along one line point together."""
    first_angle = np.arctan2(first.y1 - first.y0, first.x1 - first.x0)
    second_angle = np.arctan2(second.y1 - second.y0, second.x1 - second.x0)
    difference = abs(float(np.degrees(first_angle - second_angle))) % 180.0
    return min(difference, 180.0 - difference)


def _gap_between(first: Stroke, second: Stroke) -> float:
    """The shortest distance between the two strokes' ends."""
    return float(min(np.hypot(a[0] - b[0], a[1] - b[1]) for a in first.ends() for b in second.ends()))


def _joined(first: Stroke, second: Stroke) -> Stroke:
    """One stroke spanning two that lie along the same line: the detector reports a line's two edges,
    and reports a long line in pieces."""
    ends = first.ends() + second.ends()
    pair = max(
        ((a, b) for a in ends[:2] for b in ends[2:]),
        key=lambda item: float(np.hypot(item[0][0] - item[1][0], item[0][1] - item[1][1])),
    )
    return Stroke(pair[0][0], pair[0][1], pair[1][0], pair[1][1], min(first.thickness, second.thickness))


def _merged(strokes: list[Stroke], tolerance: float) -> list[Stroke]:
    """Longest first, then anything lying along it is the same line seen twice."""
    merged: list[Stroke] = []
    for stroke in sorted(strokes, key=lambda item: -item.length):
        for index, other in enumerate(merged):
            if _angle_between(stroke, other) <= 8.0 and _gap_between(stroke, other) <= 3.0 * tolerance:
                merged[index] = _joined(other, stroke)
                break
        else:
            merged.append(stroke)
    return merged


@dataclass(frozen=True)
class DimensionLine:
    """A segment that is a dimension line: something printed a number next to it, at both of whose
    ends the ink is heavier than a bare line end (an arrowhead, or an arrow meeting an extension
    line)."""

    segment: Segment
    text_box: tuple[float, float, float, float]
    arrow_steps: int

    @property
    def anchors(self) -> list[tuple[float, float]]:
        return self.segment.ends()

    @property
    def measured_px(self) -> float:
        return self.segment.length


@dataclass(frozen=True)
class Leader:
    """A callout: an arrow touching the feature it names, and the text at the other end of the stroke.

    A leader does not measure a distance between two points the way a dimension line does. Its arrow
    points at one feature - the circle a Ø belongs to - and the number gives that feature's size.
    """

    segment: Segment | Stroke
    text_box: tuple[float, float, float, float]
    arrow_end: int

    @property
    def tip(self) -> tuple[float, float]:
        """The point on the drawing the arrow touches: the feature this callout is about."""
        return self.segment.ends()[self.arrow_end]

    @property
    def tail(self) -> tuple[float, float]:
        return self.segment.ends()[1 - self.arrow_end]


def ink(gray: np.ndarray, contrast: float = 0.08) -> np.ndarray:
    """The ink of a sheet: what is darker than its own paper by a real fraction of its own contrast.

    Splitting the histogram in the middle (Otsu) is right when a sheet has two tones, ink and paper, and
    wrong when it has three. Measured on the plate sheet, the text runs 0-50 grey, the paper sits at 255,
    and the thin lines that carry every dimension on the sheet are printed at 161-235: Otsu splits at 158
    and drops exactly the lines a number hangs on, leaving the reader with title-block rules and glyph
    stems. Judging ink against the sheet's own paper and its own darkest tone keeps a dimension line on
    any sheet, faint or dark, without a threshold picked per file.
    """
    paper = float(np.percentile(gray, 90))
    darkest = float(np.percentile(gray, 1))
    threshold = paper - contrast * (paper - darkest)
    return np.where(gray <= threshold, 255, 0).astype(np.uint8)


def thin_segments(binary: np.ndarray, min_length: int = 36, max_thickness: int = 4, max_length: float = 1400.0) -> list[Segment]:
    """Every long, thin, straight stroke, horizontal or vertical, anywhere on the sheet.

    Runs are found row by row (and column by column) and merged across rows, so an arrowhead on the end
    of a line - short runs, never `min_length` long - does not hide the line it sits on. Line weight
    separates the strokes that carry dimensions from the ones that do not: an outline or a title-block
    rule prints at 5-6 px at 200 dpi, a dimension or extension line at 2-3 px.

    A dimension line is cut where an extension line crosses it, which is exactly where it ends: two
    chained dimensions drawn on one row are two segments, not one long one, and each segment's ends are
    the two points its number measures between.
    """
    horizontal_mask = _line_mask(binary, True, min_length)
    vertical_mask = _line_mask(binary, False, min_length)
    wide = np.ones((3, 3), np.uint8)
    horizontal, _ = _axis_segments(binary & ~cv2.dilate(vertical_mask, wide), True, min_length, max_thickness, max_length)
    vertical, _ = _axis_segments(binary & ~cv2.dilate(horizontal_mask, wide), False, min_length, max_thickness, max_length)
    return horizontal + vertical


def _line_mask(binary: np.ndarray, horizontal: bool, min_length: int) -> np.ndarray:
    """Every pixel that belongs to a straight stroke at least `min_length` long in one direction.

    Marking both directions first, then cutting each line where the other direction crosses it, is what
    makes a dimension line end at its extension lines instead of running past them into the next
    dimension of a chain - only then are its ends the two points its number measures between.
    """
    work = binary if horizontal else binary.T
    mask = np.zeros_like(work)
    for row in range(work.shape[0]):
        line = work[row] > 0
        if not line.any():
            continue
        padded = np.concatenate(([0], line.astype(np.int8), [0]))
        edges = np.flatnonzero(np.diff(padded))
        for start, end in zip(edges[::2], edges[1::2]):
            if end - start >= min_length:
                mask[row, start:end] = 255
    return mask if horizontal else mask.T


def _axis_segments(
    binary: np.ndarray, horizontal: bool, min_length: int, max_thickness: int, max_length: float
) -> tuple[list[Segment], np.ndarray]:
    work = binary if horizontal else binary.T
    height, width = work.shape
    mask = np.zeros_like(work)
    segments: list[Segment] = []
    open_rows: list[dict] = []
    for row in range(height):
        line = work[row] > 0
        row_runs: list[tuple[int, int]] = []
        if line.any():
            padded = np.concatenate(([0], line.astype(np.int8), [0]))
            edges = np.flatnonzero(np.diff(padded))
            for start, end in zip(edges[::2], edges[1::2]):
                if end - start >= min_length:
                    mask[row, start:end] = 255
                    row_runs.append((int(start), int(end)))
        merged: list[dict] = []
        for start, end in row_runs:
            for group in open_rows:
                if min(group["end"], end) - max(group["start"], start) >= 0.7 * (end - start):
                    group.update(row=row, start=min(group["start"], start), end=max(group["end"], end), rows=group["rows"] + 1)
                    merged.append(group)
                    break
            else:
                merged.append({"row": row, "start": start, "end": end, "rows": 1})
        for group in open_rows:
            if not any(group is item for item in merged):
                _add_segment(segments, group, horizontal, max_thickness, max_length)
        open_rows = merged
    for group in open_rows:
        _add_segment(segments, group, horizontal, max_thickness, max_length)
    return segments, mask


def _add_segment(segments: list[Segment], group: dict, horizontal: bool, max_thickness: int, max_length: float) -> None:
    """A stroke's weight is how many rows carry a run of it.

    Measured this way on the practice sheet, the strokes that carry dimensions come out 2-4 px and the
    outlines and title-block rules 5-6 px. Measuring instead by sampling the ink across the stroke reads
    a few pixels high on a raster, which shifts the weight of every arrow out of the band that finds it.
    """
    thickness = float(group["rows"])
    length = float(group["end"] - group["start"])
    if thickness > max_thickness or length > max_length:
        return
    if horizontal:
        segments.append(
            Segment(float(group["start"]), float(group["row"] - group["rows"] + 1), float(group["end"]), float(group["row"] + 1), thickness, True)
        )
    else:
        segments.append(
            Segment(float(group["row"] - group["rows"] + 1), float(group["start"]), float(group["row"] + 1), float(group["end"]), thickness, False)
        )


@dataclass(frozen=True)
class Dimension:
    """The dimension a printed number belongs to, in the sheet's pixels.

    `ends` are the two points on the drawing the number measures between: the extension lines the
    dimension is drawn to, which are not always the ends of the stroke the number sits next to. Small
    dimensions are printed with the arrows outside the span and the number beside the line, so anchors
    taken from the stroke alone put the span in the wrong place — a 0.688 in feature once measured 58 px
    instead of the 109 px its own extension lines stand.
    """

    horizontal: bool
    offset: float
    ends: tuple[tuple[float, float], tuple[float, float]]

    @property
    def anchors(self) -> list[tuple[float, float]]:
        return [self.ends[0], self.ends[1]]

    @property
    def length(self) -> float:
        (x0, y0), (x1, y1) = self.ends
        return float(np.hypot(x1 - x0, y1 - y0))


def dimension_for(
    binary: np.ndarray,
    segments: list[Segment],
    box: tuple[float, float, float, float],
    text_mask: np.ndarray | None = None,
    strokes: Sequence[Stroke] | None = None,
) -> Dimension | None:
    """The dimension a printed number belongs to, read as a row rather than as one stroke.

    A drafting office draws a dimension as a row of collinear strokes with the number in it or beside it,
    ending at the strokes that cross the row: the extension lines of the feature being measured. Two
    layouts share that shape, and reading the row covers both:

      - the number breaks its dimension line, so the row continues on either side of it (the plate);
      - the number sits beside a short arrowed line and the span is the empty gap between two facing
        arrows, with no stroke drawn across it at all (the catalog fitting).

    Everything is measured in the number's own text size, so the same code reads a drawing at any scale.
    A row with no arrowhead on it is a title-block rule or an outline edge, not a dimension.

    A row along an axis is read from `segments`. A dimension drawn at an angle is the same row projected
    onto the stroke's own direction and the normal across it (`strokes`): the axis pass cannot see it,
    and a leader — one arrow, the words at the blank end — is left for `leader_near`.
    """
    found = _axis_dimension(binary, segments, box)
    if found is None and strokes:
        found = _angled_dimension(binary, strokes, box)
    return found


def _axis_dimension(binary: np.ndarray, segments: list[Segment], box: tuple[float, float, float, float]) -> Dimension | None:
    """The axis-aligned row. Kept as its own pass so a diagonal cannot steal a line the axis already owns."""
    reading_across, size, text_span, text_offset, reach, near = _row_near(box, segments)
    # The row a number stands on is found beside the digits; `near` is every collinear stroke on the sheet,
    # and it is used below only to *follow* the row that was found, never to choose it. A callout's box can
    # be square to a pixel, and which axis it is read along then hangs on that pixel: on the plastic sheet
    # the `R8.00` box is 82.39 × 82.36, and choosing the row from the whole sheet moved it onto the
    # dimension line of `46.00` 390 px to its right, reading a radius as a length.
    window = [
        segment
        for segment in near
        if not (_row_end(segment, reading_across) < text_span[0] - reach
                or _row_start(segment, reading_across) > text_span[1] + reach)
    ]
    if not window:
        return None
    # A dimension whose line carries an arrow at both ends and passes *under* its number states its own
    # span: the two arrow tips are the extension lines. A number printed beside such a line instead is a
    # dimension drawn with its arrows outside the span, and its span has to be found from the extension
    # lines, so this only applies when the number really sits on the line.
    arrowed = [
        segment
        for segment in window
        if arrow_steps(binary, segment, 0) >= 8
        and arrow_steps(binary, segment, 1) >= 8
        and _row_start(segment, reading_across) - 0.2 * size <= text_span[0]
        and text_span[1] <= _row_end(segment, reading_across) + 0.2 * size
    ]
    if arrowed:
        chosen = min(arrowed, key=lambda segment: abs(_row_offset(segment, reading_across) - text_offset))
        start, end = _row_start(chosen, reading_across), _row_end(chosen, reading_across)
        return Dimension(
            horizontal=reading_across,
            offset=_row_offset(chosen, reading_across),
            ends=((start, _row_offset(chosen, reading_across)), (end, _row_offset(chosen, reading_across)))
            if reading_across
            else ((_row_offset(chosen, reading_across), start), (_row_offset(chosen, reading_across), end)),
        )

    # Which line the number stands on is decided beside the digits, as it always was: the row is taken
    # from the strokes at the number, and only then followed along its own ink (`_row_run`). Reading the
    # offset off every piece of the row instead moves the number onto whatever other line happens to lie
    # nearer its centre — measured on the plastic sheet, `3.00` and `4.00` were moved 11 px off their line
    # and the row repair that used to name them stopped firing.
    beside_the_number = [
        segment
        for segment in near
        if not (_row_end(segment, reading_across) < text_span[0] - 0.5 * size
                or _row_start(segment, reading_across) > text_span[1] + 0.5 * size)
    ] or near
    offset = min(
        (_row_offset(segment, reading_across) for segment in beside_the_number),
        key=lambda value: abs(value - text_offset),
    )
    row = [segment for segment in near if abs(_row_offset(segment, reading_across) - offset) <= 0.5 * size]
    if not any(max(arrow_steps(binary, segment, 0), arrow_steps(binary, segment, 1)) >= 8 for segment in row):
        return None
    row = _row_run(binary, reading_across, offset, size, text_span, row)

    row_span = (
        min(_row_start(segment, reading_across) for segment in row),
        max(_row_end(segment, reading_across) for segment in row),
    )
    crossings = _crossings(segments, reading_across, offset, (row_span[0] - reach, row_span[1] + reach), size)
    ends = _span_ends(reading_across, offset, crossings, text_span, row_span, size)
    if ends is None:
        return None
    return Dimension(horizontal=reading_across, offset=offset, ends=ends)


def _project(x: float, y: float, axis: tuple[float, float]) -> float:
    """Where a point sits along one axis of a stroke's own frame."""
    return x * axis[0] + y * axis[1]


def _off_axis(stroke: Stroke) -> float:
    """Degrees away from the nearer sheet axis. A leftward horizontal line is 0, not 180."""
    angle = abs(float(np.degrees(np.arctan2(stroke.y1 - stroke.y0, stroke.x1 - stroke.x0)))) % 180.0
    return min(angle, 180.0 - angle, abs(angle - 90.0))


def _along_span(stroke: Stroke, direction: tuple[float, float]) -> tuple[float, float]:
    ends = [_project(x, y, direction) for x, y in stroke.ends()]
    return min(ends), max(ends)


def _angled_dimension(binary: np.ndarray, strokes: Sequence[Stroke], box: tuple[float, float, float, float]) -> Dimension | None:
    """The same row as `_axis_dimension`, read in the stroke's own frame.

    Project the text and the strokes onto the stroke's direction and reject anything that is really on
    an axis: `diagonal_strokes` also keeps a line drawn a fraction of a degree off 180, and that line
    already had its chance in the axis pass. A leader has one arrow, so a row is a dimension only when
    two arrowed ends bracket the number — claiming the shaft itself would turn the callout into a length.
    """
    size = max(min(box[2] - box[0], box[3] - box[1]), 1.0)
    centre_x, centre_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    reach = 3.0 * size
    angled = [stroke for stroke in strokes if _off_axis(stroke) >= 6.0]
    seeds = []
    for stroke in angled:
        if _distance_to_line(centre_x, centre_y, stroke) > 1.2 * size:
            continue
        direction, _normal = _basis(stroke)
        text_along = [_project(x, y, direction) for x, y in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3]))]
        text_lo, text_hi = min(text_along), max(text_along)
        stroke_lo, stroke_hi = _along_span(stroke, direction)
        if text_hi < stroke_lo - reach or text_lo > stroke_hi + reach:
            continue
        seeds.append(stroke)
    for seed in sorted(seeds, key=lambda stroke: _distance_to_line(centre_x, centre_y, stroke)):
        found = _angled_row(binary, angled, seed, box, size, reach, centre_x, centre_y)
        if found is not None:
            return found
    return None


def _angled_row(
    binary: np.ndarray,
    strokes: Sequence[Stroke],
    seed: Stroke,
    box: tuple[float, float, float, float],
    size: float,
    reach: float,
    centre_x: float,
    centre_y: float,
) -> Dimension | None:
    """One collinear row around `seed`: the strokes that share its line and meet the text."""
    direction, normal = _basis(seed)
    text_along = [_project(x, y, direction) for x, y in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3]))]
    text_lo, text_hi = min(text_along), max(text_along)
    row = []
    for stroke in strokes:
        if _angle_between(seed, stroke) > 8.0:
            continue
        if _distance_to_line(stroke.middle[0], stroke.middle[1], seed) > 0.5 * size:
            continue
        stroke_lo, stroke_hi = _along_span(stroke, direction)
        if stroke_hi < text_lo - reach or stroke_lo > text_hi + reach:
            continue
        row.append(stroke)
    centre_along = _project(centre_x, centre_y, direction)
    # One stroke, arrowed at both ends, with the number on it: the tips are the span. The text has to
    # sit inside that stroke, or a piece that merely passes the number would claim it.
    for stroke in row:
        if arrow_steps(binary, stroke, 0) < 8 or arrow_steps(binary, stroke, 1) < 8:
            continue
        stroke_lo, stroke_hi = _along_span(stroke, direction)
        if stroke_lo - 0.2 * size <= text_lo and text_hi <= stroke_hi + 0.2 * size:
            first, second = stroke.ends()
            if _project(first[0], first[1], direction) > _project(second[0], second[1], direction):
                first, second = second, first
            return _angled_result(first, second, centre_x, centre_y, normal)
    # The number is printed outside the span, on the row's own extension: a feature too small to hold its
    # number is drawn with both arrows on the feature and the value beside it, along the same line. The
    # tips are the span, and the stroke has to be longer than the number beside it: a drafting office
    # prints the value beside a line only when the words do not fit on it, so a piece shorter than the
    # number's own box is a fragment of a longer line cut by the words it crosses — on the plastic sheet
    # the drawn `R8.00`'s leader crosses its own digits, and a 91 px piece of its 270 px length, widened
    # by a `0` the way an arrowhead widens a line, was read as a dimension between a real arrow and a
    # digit. The number also has to be clear of the span: a row overlapping the number's box is ink
    # inside the number, not a line beside it (my_part.jpg's title block `A4` is two glyphs there).
    #
    # Measured on my_part.jpg: the `50` on the 45-degree diameter sits 67 px along the row past the near
    # corner of its box, against a box of 62 px, 284.6 px of line against a value of 50 — 5.69 px/mm
    # against the 5.9 a 1:2 A4 at 200 dpi expects. Without this the value still arrives, but its anchor
    # comes from a 53 px leader and the sheet's own scale audit is built on that.
    for stroke in row:
        if arrow_steps(binary, stroke, 0) < 8 or arrow_steps(binary, stroke, 1) < 8:
            continue
        stroke_lo, stroke_hi = _along_span(stroke, direction)
        if stroke_hi - stroke_lo <= 2.0 * size:
            continue
        if text_lo > stroke_hi:
            gap = text_lo - stroke_hi
        elif text_hi < stroke_lo:
            gap = stroke_lo - text_hi
        else:
            continue
        if gap > 1.5 * size:
            continue
        first, second = stroke.ends()
        if _project(first[0], first[1], direction) > _project(second[0], second[1], direction):
            first, second = second, first
        return _angled_result(first, second, centre_x, centre_y, normal)
    # The number breaks the line, so each piece keeps the arrow on the end farther from the number.
    # The end facing the number is widened by the text itself and is not an arrow; taking it would
    # measure the gap in the text instead of the tips.
    outer: list[tuple[float, tuple[float, float]]] = []
    for stroke in row:
        ends = stroke.ends()
        farther = max((0, 1), key=lambda end: abs(_project(ends[end][0], ends[end][1], direction) - centre_along))
        if arrow_steps(binary, stroke, farther) < 8:
            continue
        point = ends[farther]
        outer.append((_project(point[0], point[1], direction), point))
    if len(outer) < 2:
        return None
    lo = min(outer, key=lambda item: item[0])
    hi = max(outer, key=lambda item: item[0])
    if not (lo[0] - 0.2 * size <= centre_along <= hi[0] + 0.2 * size) or hi[0] - lo[0] <= 0.5 * size:
        return None
    return _angled_result(lo[1], hi[1], centre_x, centre_y, normal)


def _angled_result(
    first: tuple[float, float],
    second: tuple[float, float],
    centre_x: float,
    centre_y: float,
    normal: tuple[float, float],
) -> Dimension:
    horizontal = abs(second[0] - first[0]) >= abs(second[1] - first[1])
    return Dimension(horizontal=horizontal, offset=_project(centre_x, centre_y, normal), ends=(first, second))


def _row_near(box: tuple[float, float, float, float], segments: list[Segment]) -> tuple[bool, float, tuple[float, float], float, float, list[Segment]]:
    """The strokes of the row a printed number sits beside, and the frame that row is read in.

    A dimension is a row, not a stroke: the strokes collinear with the number's own line, within a
    character's reach of it. Everything the row is measured in comes back with it — which axis it runs
    along, the number's own extent along that axis and across it, and how far a stroke may stand off and
    still be on this row.

    The row is gathered from the whole sheet, not from a window drawn around the number: a piece of the
    number's own line may sit well to one side of it, and a window silently truncates the span to whatever
    happens to lie beside the digits. Which of these strokes are the number's own line is decided later,
    by following the line through its crossings (`_row_run`).
    """
    reading_across = (box[2] - box[0]) >= (box[3] - box[1])
    size = max((box[3] - box[1]) if reading_across else (box[2] - box[0]), 1.0)
    text_span = (box[0], box[2]) if reading_across else (box[1], box[3])
    text_offset = (box[1] + box[3]) / 2 if reading_across else (box[0] + box[2]) / 2
    reach = 3.0 * size
    near = [
        segment
        for segment in segments
        if segment.horizontal == reading_across
        and abs(_row_offset(segment, reading_across) - text_offset) <= 1.2 * size
    ]
    return reading_across, size, text_span, text_offset, reach, near


def _row_offset(segment: Segment, reading_across: bool) -> float:
    return (segment.y0 + segment.y1) / 2 if reading_across else (segment.x0 + segment.x1) / 2


def _row_run(
    binary: np.ndarray,
    reading_across: bool,
    offset: float,
    size: float,
    text_span: tuple[float, float],
    row: list[Segment],
) -> list[Segment]:
    """The pieces of the number's own dimension line: the ones joined to the number's line across a crossing.

    A dimension line is cut where another dimension's extension line crosses it. The crossing puts ink
    across the line, thinning drops the widened run, and the line comes back as two pieces a few pixels
    apart. Reading the row off the pieces beside the number therefore ends the span at that crossing: on
    the pilot sheets a `45` drawn from the edge to a hole came back as the 30 between a neighbouring
    extension line and the hole, and the sheet then refused to calibrate against its own other numbers.

    Joining is only done across a crossing. Two pieces that meet end to end at arrowheads are two
    dimensions drawn on one line (`15 | 45`), and joining them would measure the pair as a single span.
    """
    if not row:
        return []
    weight = max(1.0, float(np.median([segment.thickness for segment in row])))
    ordered = sorted(row, key=lambda segment: _row_start(segment, reading_across))
    seed = min(
        ordered,
        key=lambda segment: _distance_to_span((text_span[0] + text_span[1]) / 2,
                                              (_row_start(segment, reading_across), _row_end(segment, reading_across))),
    )
    kept = [seed]
    growing = True
    while growing:
        growing = False
        for segment in ordered:
            if segment in kept:
                continue
            for held in kept:
                standing = _standing_gap(held, segment, reading_across, size)
                if standing is None:
                    continue
                if _is_a_crossing(binary, reading_across, offset, standing, weight):
                    kept.append(segment)
                    growing = True
                break
    return sorted(kept, key=lambda segment: _row_start(segment, reading_across))


def _standing_gap(first: Segment, second: Segment, reading_across: bool, size: float) -> float | None:
    """Where two pieces of one row stand apart — `None` when they are not close enough to be one line cut.

    A crossing cuts a line by a pixel or two; a number printed on the line cuts it by its own width, which
    is why the tolerance here is a fraction of the number's box and not a whole one.
    """
    left, right = sorted((first, second), key=lambda segment: _row_start(segment, reading_across))
    left_end = _row_end(left, reading_across)
    right_start = _row_start(right, reading_across)
    if right_start <= left_end:
        return (left_end + right_start) / 2
    if right_start - left_end > 0.5 * size:
        return None
    return (left_end + right_start) / 2


def _across_extent(binary: np.ndarray, reading_across: bool, offset: float, position: float, limit: int) -> int:
    """How far the ink runs away from the row at one point along it, both ways."""
    height, width = binary.shape[:2]
    total = 0
    for sign in (-1, 1):
        step = 1
        while step <= limit:
            if reading_across:
                x, y = int(round(position)), int(round(offset) + sign * step)
            else:
                x, y = int(round(offset) + sign * step), int(round(position))
            if not (0 <= x < width and 0 <= y < height) or binary[y, x] == 0:
                break
            total += 1
            step += 1
    return total


def _is_a_crossing(binary: np.ndarray, reading_across: bool, offset: float, position: float, weight: float) -> bool:
    """Whether the ink standing across the row here is a line crossing it, or a dimension's arrowhead.

    Both put ink across the row at the junction, so the junction alone says nothing. What separates them is
    what stands *beside* it: a crossing is a perpendicular line two or three pixels wide, and the row's own
    ink either side of it is back to the line's weight, while an arrowhead is a wedge whose tip meets the
    junction and whose base stands ten-odd pixels inside the piece. Measured: on the pilot sheet at the
    `45`'s crossing the ink is 31 px tall at the junction and 1 px — the line itself — 3 to 12 px away; on
    a pair of met arrowheads it is 36 px tall there and 4 to 8 px away.
    """
    limit = max(4, int(round(4.0 * weight)))
    if _across_extent(binary, reading_across, offset, position, limit) < 3.0 * weight:
        return False
    beside = max(_across_extent(binary, reading_across, offset, position + sign * step, limit)
                 for sign in (-1, 1) for step in range(3, 13))
    return beside <= max(2.0 * weight, weight + 2.0)


def _row_start(segment: Segment, reading_across: bool) -> float:
    return segment.x0 if reading_across else segment.y0


def _row_end(segment: Segment, reading_across: bool) -> float:
    return segment.x1 if reading_across else segment.y1


def _crossings(
    segments: list[Segment],
    reading_across: bool,
    offset: float,
    row_span: tuple[float, float],
    size: float,
    merge: float | None = None,
) -> list[float]:
    """Where the strokes crossing the row meet it: the extension lines a dimension is drawn between.

    `merge` is how close two crossings have to be before they are one extension line drawn thick. It comes
    in from the caller where the sheet's own stroke weight is known, because a tolerance read off the
    number's box is a tolerance read off the wrong thing: the plastic sheet's `1.50` sits in a box 71 px
    wide, and a 0.4-of-that merge swallowed the two real extension lines 6.5 px apart that carry its value.
    """
    start, end = row_span
    found: list[float] = []
    for segment in segments:
        if segment.horizontal == reading_across:
            continue
        # A crossing stroke runs across the row, so the row reads its position from the axis it does not
        # run along: a vertical line crossing a horizontal row is at its own x.
        position = (segment.x0 + segment.x1) / 2 if reading_across else (segment.y0 + segment.y1) / 2
        if not (start - size <= position <= end + size):
            continue
        cross_lo, cross_hi = (segment.y0, segment.y1) if reading_across else (segment.x0, segment.x1)
        # An extension line stops a hair short of the dimension line it belongs to.
        if cross_lo - 0.6 * size <= offset <= cross_hi + 0.6 * size:
            found.append(position)
    return _merge_close(sorted(found), 0.4 * size if merge is None else merge)


def crossing_pairs(
    segments: list[Segment],
    box: tuple[float, float, float, float],
    holding: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Every span the drawing offers on the row nearest this number, as the pairs of crossings on it.

    `_span_ends` chooses one pair knowing nothing about the value, and it cannot do otherwise when the gate
    runs: it takes the pair the number sits between, else the pair nearest it. On a sheet drawn as a band of
    closely spaced profile edges that pair belongs to a neighbouring feature — measured on the plastic
    sheet, a printed `1.50` whose value is 5.9 px was given a 113.5 px line and a `4.80` was given the 69 px
    line of the step below it, and fifteen of the sheet's twenty auditable readings came out anchored to a
    line that was not their own. Once the sheet has calibrated itself (`scale.consensus`) the number's own
    value says which pair on that row is its own, so this returns the candidates and leaves the choosing to
    the caller, which can judge a length against the sheet's scale.

    The row is the one the gate itself would choose — the one nearest the number — so the pairs offered are
    the spans of that line and not of whatever else lies within reach. `holding` is the span the gate gave
    this number, and only the spans *at that line* are offered: the ones inside the stretch it was given,
    and the neighbouring gap between one of that stretch's own ends and the next crossing. A pair further
    along the same row belongs to another dimension, and taking it is not a repair — measured, a datum
    symbol read as a `2` was offered and took an 8 px gap 25 px past the end of the line it stood on, which
    fitted its value and made the sheet stop naming a record that is not a printed number at all.
    """
    reading_across, size, text_span, text_offset, reach, near = _row_near(box, segments)
    if not near:
        return []
    # Which spans are offered here is a question about the line beside the digits, so the local window is
    # put back: `_row_near` deliberately no longer truncates the row (the gate has to see a span that runs
    # well past its number), and reading that wider row would offer this number the pairs of a line further
    # along — measured, that took the repair away from three readings on the plastic sheet that it had been
    # putting right (pdf-6, pdf-8, pdf-9), leaving two of them on a line their own values do not fit.
    near = [
        segment
        for segment in near
        if not (_row_end(segment, reading_across) < text_span[0] - reach
                or _row_start(segment, reading_across) > text_span[1] + reach)
    ]
    if not near:
        return []
    offset = min((_row_offset(segment, reading_across) for segment in near), key=lambda value: abs(value - text_offset))
    row = [segment for segment in near if abs(_row_offset(segment, reading_across) - offset) <= 0.5 * size]
    if not row:
        return []
    row_span = (
        min(_row_start(segment, reading_across) for segment in row),
        max(_row_end(segment, reading_across) for segment in row),
    )
    # The sheet's own line weight: two crossings closer together than one stroke of this drawing is wide
    # are one extension line drawn thick, not two lines with a span between them.
    weight = float(np.median([segment.thickness for segment in segments])) if len(segments) else 2.0
    merge = max(weight, 2.0)
    crossings = _crossings(
        segments, reading_across, offset, (row_span[0] - reach, row_span[1] + reach), size, merge=merge
    )
    held = None
    if holding is not None:
        along = 0 if reading_across else 1
        ends = [float(point[along]) for point in holding]
        held = (min(ends), max(ends))
    pairs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for low, high in zip(crossings, crossings[1:]):
        if high - low <= 0:
            continue
        if held is not None and not _at_the_same_line(held, (low, high), merge):
            continue
        first, second = ((low, offset), (high, offset)) if reading_across else ((offset, low), (offset, high))
        pairs.append((first, second))
    return pairs


def _at_the_same_line(held: tuple[float, float], pair: tuple[float, float], merge: float) -> bool:
    """Is this span one of the spans at the line the number was given: inside it, or the gap beside it?"""
    low, high = pair
    if low >= held[0] - merge and high <= held[1] + merge:
        return True
    return abs(low - held[1]) <= merge or abs(high - held[0]) <= merge


def _merge_close(values: list[float], tolerance: float) -> list[float]:
    merged: list[float] = []
    for value in values:
        if merged and value - merged[-1] <= tolerance:
            continue
        merged.append(value)
    return merged


def _span_ends(
    reading_across: bool,
    offset: float,
    crossings: list[float],
    text_span: tuple[float, float],
    row_span: tuple[float, float],
    size: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """The span the number measures: the crossings at the ends of the line it was given, else the pair it sits in."""
    start, end = row_span
    decided = False
    # The number sits on its own dimension line, and that line ends at its two extension lines. A crossing
    # between those two ends is another dimension's extension line passing over this one, not a boundary:
    # on the pilot sheets the `45` from the edge to a hole sits to the right of the neighbouring `15`'s
    # extension line, so taking the nearest bracketing pair measured the 30 from that crossing to the hole,
    # and the sheet then disagreed with its own other numbers and refused to calibrate.
    if len(crossings) >= 2:
        slack = 0.5 * size
        holds_the_number = start - slack <= text_span[0] and text_span[1] <= end + slack
        on_the_line = [value for value in crossings if start - slack <= value <= end + slack]
        if holds_the_number and len(on_the_line) >= 2 and on_the_line[-1] - on_the_line[0] > 0.1 * size:
            start, end = on_the_line[0], on_the_line[-1]
            decided = True
    if not decided and len(crossings) >= 2:
        pairs = list(zip(crossings, crossings[1:]))
        containing = [pair for pair in pairs if pair[0] - 0.4 * size <= text_span[0] and text_span[1] <= pair[1] + 0.4 * size]
        if containing:
            start, end = min(containing, key=lambda pair: pair[1] - pair[0])
        else:
            middle = (text_span[0] + text_span[1]) / 2
            start, end = min(pairs, key=lambda pair: _distance_to_span(middle, pair))
    if end - start <= 0.1 * size:
        return None
    if reading_across:
        return ((start, offset), (end, offset))
    return ((offset, start), (offset, end))


def _distance_to_span(position: float, span: tuple[float, float]) -> float:
    if position < span[0]:
        return span[0] - position
    if position > span[1]:
        return position - span[1]
    return 0.0


def leader_near(
    binary: np.ndarray,
    segments: Sequence[Segment | Stroke],
    box: tuple[float, float, float, float],
    text_mask: np.ndarray | None = None,
    min_arrow_steps: int = 8,
    printed_text: "PrintedText | None" = None,
) -> Leader | None:
    """The callout a printed Ø/R belongs to: one arrow, and its text at the far end of the same stroke.

    Only one end carries an arrow - the tip that touches the feature - which is what tells a leader from
    a dimension line, whose number sits in the middle of a line arrowed at both ends. The stroke may run
    along an axis or at an angle: most callouts on a drawing are diagonals, so both kinds are handed in.
    """
    centre_x, centre_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    height = max(min(box[2] - box[0], box[3] - box[1]), 1.0)
    best: Leader | None = None
    printed = printed_text
    for segment in segments:
        if text_fraction(text_mask, segment) > TEXT_FRACTION:
            # The mask says this stroke is printed text; on a stroke at an angle the mask is counting the
            # stroke's own ink, so ask the sheet's own type whether the ink is a word or a drawn line.
            if printed is None and text_mask is not None:
                printed = PrintedText.of(text_mask)
            if printed is not None and printed.through_words(segment):
                continue
        arrows = [end for end in (0, 1) if arrow_steps(binary, segment, end) >= min_arrow_steps]
        if len(arrows) != 1:
            continue
        arrow_end = arrows[0]
        tip_x, tip_y = segment.ends()[arrow_end]
        tail_x, tail_y = segment.ends()[1 - arrow_end]
        # The words sit beside the shaft, close to its blank end, and nearer that end than the arrow: a
        # blob sitting *on* a stroke is a fragment of the stroke, not a number printed next to it. The
        # gap is measured to the nearest edge of the words, not to their centre: `0.688in` is a wide
        # block of text and still sits right beside the shaft its arrow belongs to.
        gap = distance_to_box(tail_x, tail_y, box)
        if gap > 2.0 * height:
            continue
        if _distance_to_line(centre_x, centre_y, segment) < 1.5 * segment.thickness:
            continue
        if (centre_x - tip_x) ** 2 + (centre_y - tip_y) ** 2 < gap**2:
            continue
        if best is None or segment.length > best.segment.length:
            best = Leader(segment, box, arrow_end)
    return best


def distance_to_box(x: float, y: float, box: tuple[float, float, float, float]) -> float:
    """Distance from a point to the nearest edge of a rectangle (0 inside it)."""
    dx = max(box[0] - x, 0.0, x - box[2])
    dy = max(box[1] - y, 0.0, y - box[3])
    return float(np.hypot(dx, dy))


def leader_to_note(
    binary: np.ndarray,
    segments: Sequence[Segment | Stroke],
    box: tuple[float, float, float, float],
    text_mask: np.ndarray | None = None,
    printed_text: "PrintedText | None" = None,
    character: float = 0.0,
    least: float = 3.0,
    reach: float = 1.5,
) -> Leader | None:
    """The stroke drawn *to* a printed note, for the numbers printed inside it.

    `leader_near` measures the gap from a stroke's blank end to the box it is handed and asks nothing
    else, which fits a one-word callout and misses a note: on the plate the leader of
    `4 x Ø 6,80 THRU ALL` ends 181 px from the `6,80` it names and 28 px from the note's own ink. Handing
    it the note's block instead is not enough on its own — a feature-control frame is a ruled box of
    symbols whose own slanted strokes come out arrowed and 43 px long, and a dashes centreline's arrowhead
    ends beside a cluster of arc ink — so the stroke has to be a line *to* the note: long against the
    note's own character size, and ending beside the note's ink rather than inside it or short of it.

    `character` is the note's own measured character size; `least` and `reach` are ratios of it.
    """
    if character <= 0.0:
        return None
    leader = leader_near(binary, segments, box, text_mask, printed_text=printed_text)
    if leader is None or leader.segment.length < least * character:
        return None
    ends = leader.segment.ends()
    tail_x, tail_y = ends[1 - leader.arrow_end]
    distance = distance_to_box(tail_x, tail_y, box)
    if not 0.0 < distance <= reach * character:
        return None
    return leader


def _distance_to_line(x: float, y: float, segment: Segment | Stroke) -> float:
    """Perpendicular distance from a point to the stroke's own infinite line: through its middle, along
    the direction it runs in."""
    direction, _across = _basis(segment)
    middle_x, middle_y = segment.middle
    return float(abs((x - middle_x) * direction[1] - (y - middle_y) * direction[0]))


def _run(binary: np.ndarray, x: int, y: int, half: int, vertical: bool) -> int:
    """Kept for the probes that measure a stroke by hand; the drawing code asks `_ink_across`."""
    normal = (0.0, 1.0) if vertical else (1.0, 0.0)
    return _ink_across(binary, x, y, normal, half)


def arrow_steps(
    binary: np.ndarray,
    segment: Segment | Stroke,
    end: int,
    reach: int = 45,
    low: float = 1.5,
    high: float = 4.0,
) -> int:
    """How many pixels inward from one end of the line is the stroke wider than the line, but not wider
    than an arrowhead.

    A drafting arrow is a long, slender triangle: at 200 dpi it runs 30-45 px along the line and widens
    to roughly twice to three times the line weight. A dimension line's end also touches the extension
    line, whose stroke goes far past the dimension line in both directions - so a stroke much wider than
    an arrow is that extension line, not an arrow. A bare line end is simply not wider at all.

    The question is asked across the stroke's own normal, so it can be asked of a leader drawn at any
    angle as well as of an axis stroke.
    """
    direction, normal = _basis(segment)
    horizontal = getattr(segment, "horizontal", None)
    half = int(max(6.0, 6.0 * segment.thickness))
    start_x, start_y = segment.ends()[end]
    wide = 0
    for offset in range(-reach, reach + 1):
        # Both sides of the end: a drafting arrow either points at the extension line from inside the
        # dimension or sits outside it pointing in, and both styles appear on one sheet.
        if horizontal is True:
            x, y = int(round(start_x + offset)), int(round(start_y))
        elif horizontal is False:
            x, y = int(round(start_x)), int(round(start_y + offset))
        else:
            x, y = start_x + direction[0] * offset, start_y + direction[1] * offset
        stroke = _ink_across(binary, x, y, normal, half)
        if low * segment.thickness <= stroke <= high * segment.thickness:
            wide += 1
    return wide


def tip_ratio(binary: np.ndarray, segment: Segment, end: int, reach: float = 18.0) -> float:
    """Ink around one end of a segment, as a multiple of what a bare line fills there.

    A plain line end fills thickness / (2 * reach) of the window; an arrowhead fills far more.
    """
    size = int(max(9.0, reach))
    centre_x, centre_y = segment.ends()[end]
    left, top = int(max(0, centre_x - size)), int(max(0, centre_y - size))
    right, bottom = int(min(binary.shape[1], centre_x + size)), int(min(binary.shape[0], centre_y + size))
    window = binary[top:bottom, left:right]
    if window.size == 0:
        return 0.0
    filled = float((window > 0).mean())
    bare = (2.0 * size * segment.thickness) / float(window.size)
    return filled / max(bare, 1e-6)


def text_fraction(text_mask: np.ndarray | None, segment: Segment | Stroke, samples: int = 48) -> float:
    """How much of a stroke lies inside printed text: a digit's stem is all text, a dimension line none.

    Text is wide relative to a line, so the stroke through a letter looks arrow-like to `arrow_steps`.
    Asking whether the stroke is part of a glyph is what tells the two apart.
    """
    if text_mask is None:
        return 0.0
    height, width = text_mask.shape
    inside = 0
    for step in range(samples + 1):
        ratio = step / samples
        x = int(round(segment.x0 + (segment.x1 - segment.x0) * ratio))
        y = int(round(segment.y0 + (segment.y1 - segment.y0) * ratio))
        if 0 <= y < height and 0 <= x < width and text_mask[y, x] > 0:
            inside += 1
    return inside / (samples + 1)


@dataclass(frozen=True)
class PrintedText:
    """The mask's own blobs, and how big a printed character is on this sheet.

    `text_fraction` counts a stroke's *own ink* as text wherever the mask kept it, and the mask only
    removes what a 28-px morphological opening can remove: the rules that run along an axis. A stroke at
    an angle survives, so on the plate sheet the leader of `6,80 THRU ALL` reads 53-65% text while a
    letter's stem reads 51% - the measurement cannot tell a leader from a glyph, and `leader_near`
    refuses every callout whose leader is not faint (the faint one, `Ø50,00`, scores 0.02). What does
    tell them apart is the ink the stroke runs through: printed blobs are bounded by the sheet's own
    type, a line stretches past it.

    The character size is the same statistic `_glyphs` measures — the median longest side of the blobs
    that are a character in both directions — so the two agree on what one character is.
    """

    labels: np.ndarray
    stats: np.ndarray
    character: float

    @classmethod
    def of(cls, text_mask: np.ndarray) -> "PrintedText":
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(text_mask, 8)
        sides = [
            max(int(stats[index][2]), int(stats[index][3]))
            for index in range(1, count)
            if min(int(stats[index][2]), int(stats[index][3])) >= 8
        ]
        return cls(labels, stats, float(np.median(sides)) if sides else 0.0)

    def through_words(self, stroke: Segment | Stroke, samples: int = 24) -> bool:
        """Is the ink this stroke runs through printed type, or a line drawn across the sheet?

        A blob of type is small in both directions; a leader, a rule or a hatch line is one narrow
        shape whose length is the length of its own line, so the blob it lies in outgrows the sheet's
        character. The blob is read from the samples along the stroke and takes the vote, because a
        stroke crosses what it crosses rather than lying inside one thing.
        """
        if self.character <= 0.0:
            return False
        height, width = self.labels.shape
        votes: dict[int, int] = {}
        for step in range(samples + 1):
            ratio = step / samples
            x = int(round(stroke.x0 + (stroke.x1 - stroke.x0) * ratio))
            y = int(round(stroke.y0 + (stroke.y1 - stroke.y0) * ratio))
            if 0 <= y < height and 0 <= x < width:
                label = int(self.labels[y, x])
                if label:
                    votes[label] = votes.get(label, 0) + 1
        if not votes:
            return False
        label = max(votes, key=lambda key: votes[key])
        longest = max(int(self.stats[label][2]), int(self.stats[label][3]))
        return longest <= TEXT_BOUND * self.character


def dimension_line_near(
    binary: np.ndarray,
    segments: list[Segment],
    box: tuple[float, float, float, float],
    text_mask: np.ndarray | None = None,
    max_gap: float = 30.0,
    min_arrow_steps: int = 8,
) -> DimensionLine | None:
    """The dimension line a printed number belongs to, or None if the number sizes nothing.

    The number is centred on its line and sits just off it: within `max_gap` perpendicular pixels and,
    along the line, inside the line's own span.
    """
    x0, y0, x1, y1 = box
    centre_x, centre_y = (x0 + x1) / 2, (y0 + y1) / 2
    best: DimensionLine | None = None
    for segment in segments:
        if text_fraction(text_mask, segment) > 0.25:
            continue
        steps = min(arrow_steps(binary, segment, 0), arrow_steps(binary, segment, 1))
        if steps < min_arrow_steps:
            continue
        if segment.horizontal:
            if not (segment.x0 - 2 <= centre_x <= segment.x1 + 2):
                continue
            below, above = segment.y0 - y1, y0 - segment.y0
            gap = below if 0 <= below <= max_gap else (above if 0 <= above <= max_gap else -1.0)
        else:
            if not (segment.y0 - 2 <= centre_y <= segment.y1 + 2):
                continue
            right, left = segment.x0 - x1, x0 - segment.x1
            gap = right if 0 <= right <= max_gap else (left if 0 <= left <= max_gap else -1.0)
        if gap < 0:
            continue
        if best is None or steps > best.arrow_steps:
            best = DimensionLine(segment, box, steps)
    return best
