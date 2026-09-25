"""Dimension lines: the thin, long, arrow-tipped strokes a printed number sits next to.

A technical drawing prints far more numbers than it has dimensions; the ones that size a feature sit
against a dimension line and nowhere else. Finding those lines prunes the candidate set and hands the
interpreter the two anchors (the line's ends, or the extension lines they stop at) it needs to turn a
number into geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


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

    segment: Segment
    text_box: tuple[float, float, float, float]
    arrow_end: int

    @property
    def tip(self) -> tuple[float, float]:
        """The point on the drawing the arrow touches: the feature this callout is about."""
        return self.segment.ends()[self.arrow_end]

    @property
    def tail(self) -> tuple[float, float]:
        return self.segment.ends()[1 - self.arrow_end]


def ink(gray: np.ndarray) -> np.ndarray:
    _threshold, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


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


def leader_near(
    binary: np.ndarray,
    segments: list[Segment],
    box: tuple[float, float, float, float],
    text_mask: np.ndarray | None = None,
    min_arrow_steps: int = 8,
) -> Leader | None:
    """The callout a printed Ø/R belongs to: one arrow, and its text at the far end of the same stroke.

    Only one end carries an arrow - the tip that touches the feature - which is what tells a leader from
    a dimension line, whose number sits in the middle of a line arrowed at both ends.
    """
    centre_x, centre_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    best: Leader | None = None
    for segment in segments:
        if text_fraction(text_mask, segment) > 0.25:
            continue
        arrows = [end for end in (0, 1) if arrow_steps(binary, segment, end) >= min_arrow_steps]
        if len(arrows) != 1:
            continue
        arrow_end = arrows[0]
        tail_x, tail_y = segment.ends()[1 - arrow_end]
        reach = max(24.0, 2.5 * segment.thickness + 12.0)
        gap = ((centre_x - tail_x) ** 2 + (centre_y - tail_y) ** 2) ** 0.5
        if gap > reach:
            continue
        if best is None or segment.length > best.segment.length:
            best = Leader(segment, box, arrow_end)
    return best


def _run(binary: np.ndarray, x: int, y: int, half: int, vertical: bool) -> int:
    """Length of the ink stroke through (x, y) across the line: the arrow is wide, a bare line is not."""
    if not (0 <= y < binary.shape[0] and 0 <= x < binary.shape[1]) or binary[y, x] == 0:
        return 0
    steps = 1
    for direction in (-1, 1):
        for offset in range(1, half + 1):
            ny, nx = (y + direction * offset, x) if vertical else (y, x + direction * offset)
            if not (0 <= ny < binary.shape[0] and 0 <= nx < binary.shape[1]) or binary[ny, nx] == 0:
                break
            steps += 1
    return steps


def arrow_steps(
    binary: np.ndarray,
    segment: Segment,
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
    """
    start_x, start_y = segment.ends()[end]
    wide = 0
    for offset in range(-reach, reach + 1):
        # Both sides of the end: a drafting arrow either points at the extension line from inside the
        # dimension or sits outside it pointing in, and both styles appear on one sheet.
        if segment.horizontal:
            x, y = int(round(start_x + offset)), int(round(start_y))
        else:
            x, y = int(round(start_x)), int(round(start_y + offset))
        stroke = _run(binary, x, y, 30, vertical=segment.horizontal)
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


def text_fraction(text_mask: np.ndarray, segment: Segment, samples: int = 48) -> float:
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
