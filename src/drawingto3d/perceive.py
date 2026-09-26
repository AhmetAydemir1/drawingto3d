"""Read geometry and dimension strings. Roles are assigned later, not here."""

from __future__ import annotations

from typing import NamedTuple

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from drawingto3d import lines
from drawingto3d.ingest import apply_sheet_unit, parse_dimension, parse_dimension_unit
from drawingto3d.reader import read_dimension
from drawingto3d.schema import AnchorMode, BBox, Page, Primitive, PrimitiveKind, Source, Span, SpanKind, Unit


def perceive(page: Page, reader=None) -> tuple[list[Primitive], list[Span]]:
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    primitives = _primitives(gray)
    if page.vector_text:
        spans = _gated_text_layer(page, gray)
    else:
        spans = list(page.spans)
        spans.extend(_oriented_spans(gray, reader))
    apply_sheet_unit(spans)
    spans = [span for span in spans if _inside_drawing_area(span, page)]
    _assign_views(spans, page.views)
    spans = _dedupe_spans(spans)
    page.spans = spans
    return primitives, spans


def _gated_text_layer(page: Page, gray: np.ndarray) -> list[Span]:
    """The sheet's own text layer, kept only where the drawing carries the number.

    A PDF text layer is exact about what is printed and where, which is why it is read instead of OCR;
    it also contains the title block, the scale note, the part number and the copyright year. Which of
    those numbers size a feature is decided by the drawing's own geometry — the gate the raster path
    uses, with the text layer's exact boxes in place of glyph clustering and OCR.

    If no number on the sheet is carried by a dimension, the sheet is kept as it is: a reader that
    silently returns nothing is worse than one that shows what is printed and admits it has no anchors.
    """
    binary = lines.ink(gray)
    segments = lines.thin_segments(binary)
    heights = [float(span.bbox.h) for span in page.spans if span.value is not None]
    gate = _DimensionGate(
        binary,
        segments,
        _text_mask(gray),
        gray=gray,
        text_height=float(np.median(heights)) if heights else None,
    )
    kept: list[Span] = []
    for span in page.spans:
        if span.value is None or span.kind == SpanKind.text:
            continue
        box = (span.bbox.x, span.bbox.y, span.bbox.x + span.bbox.w, span.bbox.y + span.bbox.h)
        accepted, anchors, mode = gate.accepts(box)
        if not accepted:
            continue
        span.anchors = anchors or []
        span.anchor_mode = mode
        kept.append(span)
    return kept or [span for span in page.spans if span.value is not None]


MARGIN_FRACTION = 0.04


def _inside_drawing_area(span: Span, page: Page) -> bool:
    """Keep text inside the sheet border. The A-D / 1-4 markers in the frame band are not dimensions.

    A vision reader asked about a `D` in that band answered `30` once; numbers cannot be trusted there,
    and nothing inside the frame band ever sizes a feature.
    """
    band_x = page.width * MARGIN_FRACTION
    band_y = page.height * MARGIN_FRACTION
    centre_x = span.bbox.x + span.bbox.w / 2
    centre_y = span.bbox.y + span.bbox.h / 2
    return band_x <= centre_x <= page.width - band_x and band_y <= centre_y <= page.height - band_y


def _primitives(gray: np.ndarray) -> list[Primitive]:
    edges = cv2.Canny(gray, 50, 150)
    found: list[Primitive] = []
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=40, maxLineGap=6)
    if lines is not None:
        for index, line in enumerate(lines.reshape(-1, 4)[:80]):
            x0, y0, x1, y1 = [float(value) for value in line]
            kind = PrimitiveKind.axis if _dashed_like(gray, x0, y0, x1, y1) else PrimitiveKind.line
            found.append(
                Primitive(id=f"line-{index}", kind=kind, points=[(x0, y0), (x1, y1)])
            )
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30, param1=120, param2=28, minRadius=8, maxRadius=80
    )
    if circles is not None:
        for index, (x, y, radius) in enumerate(circles[0][:12]):
            found.append(
                Primitive(
                    id=f"circle-{index}",
                    kind=PrimitiveKind.circle,
                    points=[(float(x), float(y))],
                    radius=float(radius),
                )
            )
    return found


def _dashed_like(gray: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> bool:
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length < 50:
        return False
    samples = 12
    dark = 0
    for step in range(samples):
        t = step / (samples - 1)
        x = int(x0 + (x1 - x0) * t)
        y = int(y0 + (y1 - y0) * t)
        if 0 <= y < gray.shape[0] and 0 <= x < gray.shape[1] and gray[y, x] < 160:
            dark += 1
    return 2 <= dark <= 7


def _oriented_spans(gray: np.ndarray, reader=None) -> list[Span]:
    """Read dimension text that is horizontal, vertical, or diagonal."""
    if shutil.which("tesseract") is None and reader is None:
        return []
    binary = lines.ink(gray)
    segments = lines.thin_segments(binary)
    text_mask = _text_mask(gray)
    # One glyph list for both passes. Narrow per-pass size limits used to drop half of a rotated number
    # (the digit that looked too wide for that pass), leaving a fragment that then read as a stray digit.
    glyphs = _glyphs(gray, text_mask)
    sizes = [max(glyph.w, glyph.h) for glyph in glyphs if not glyph.separator]
    gate = _DimensionGate(
        binary,
        segments,
        text_mask,
        gray=gray,
        text_height=float(np.median(sizes)) if sizes else None,
    )
    spans = _collect_spans(gray, glyphs, "center", gate, reader) + _collect_spans(gray, glyphs, "gap", gate, reader)
    spans = _one_number_per_line(spans)
    for index, span in enumerate(spans):
        span.id = f"ocr-{index}"
    return spans


def _one_number_per_line(spans: list[Span], step: float = 8.0) -> list[Span]:
    """A dimension line carries a single number, so keep the fullest candidate on each line.

    Clustering can still hand back a rotated number as two pieces, and each piece then claims the same
    line and gets read as a number of its own — that is how a printed 40 turns into a 4 and a 0. The
    candidate that holds the most ink is the one that is really on that line.
    """
    chosen: dict[tuple, Span] = {}
    for span in spans:
        if len(span.anchors) != 2:
            key: tuple = ("unattached", span.id)
        else:
            (x0, y0), (x1, y1) = span.anchors
            key = (round(min(x0, x1) / step), round(min(y0, y1) / step), round(max(x0, x1) / step), round(max(y0, y1) / step))
        current = chosen.get(key)
        if current is None or span.bbox.w * span.bbox.h > current.bbox.w * current.bbox.h:
            chosen[key] = span
    keep = {id(span) for span in chosen.values()}
    return [span for span in spans if id(span) in keep]


class Glyph(NamedTuple):
    """A blob of printed text: where it sits, how big it is, and whether it is a separator not a digit."""

    cx: float
    cy: float
    x: int
    y: int
    w: int
    h: int
    separator: bool = False


def _glyphs(gray: np.ndarray, text_mask: np.ndarray, longest: int = 60, amin: int = 8, amax: int = 500) -> list[Glyph]:
    """Printed text as blobs: centre, box, size, and whether the blob is a separator rather than a digit.

    A blob the size of a character is a glyph, and so is one too small in one direction to be a character
    at all: a decimal separator is a few pixels across, and it is the whole difference between the printed
    `100,00` and two numbers, `10` and `00`. Measured on the plate sheet, the comma's own room pushed the
    digits on either side of it 30.6 px apart against a chaining limit of 25.6 px, so every dimension on
    that sheet came apart at its decimal point. The small blobs are flagged, so the rest of the code can
    tell a comma from a digit.
    """
    count, _, stats, centroids = cv2.connectedComponentsWithStats(text_mask, 8)
    height, width = gray.shape
    blobs = []
    for index in range(1, count):
        x, y, w, h, area = [int(value) for value in stats[index]]
        if not (width * 0.04 < x < width * 0.96 and height * 0.04 < y < height * 0.96):
            continue
        if max(w, h) <= longest and area <= amax:
            blobs.append((float(centroids[index][0]), float(centroids[index][1]), x, y, w, h, area))
    # What a character is on this sheet, measured from the blobs that are one in both directions. A `1`
    # printed at this size is 6 px wide and 28 px tall, so the thinness of a blob says nothing about it,
    # and a comma 8 px across is nearly as wide as it is tall: only the two together tell them apart.
    core = [max(blob[4], blob[5]) for blob in blobs if min(blob[4], blob[5]) >= 8]
    character = float(np.median(core or [max(blob[4], blob[5]) for blob in blobs] or [longest]))
    glyphs = []
    for cx, cy, x, y, w, h, area in blobs:
        side = max(w, h)
        # Judged on the longest side, not the height: text along a vertical dimension is printed a
        # quarter turn round, so a digit of the same size is as wide as it is tall elsewhere.
        if 3 <= min(w, h) and 0.6 * character <= side <= longest and amin <= area <= amax:
            glyphs.append(Glyph(cx, cy, x, y, w, h, False))
        elif side <= 0.5 * character and area >= 2:
            glyphs.append(Glyph(cx, cy, x, y, w, h, True))
    return glyphs


class _DimensionGate:
    """Keeps a printed number only if it sits against a dimension line, and remembers that line.

    A drawing prints part numbers, dates, sheet numbers, notes and title-block text; only the text that
    a dimension line points at sizes anything. The gate is the one place that decides, so the anchors it
    finds can travel with the span.
    """

    def __init__(
        self,
        binary: np.ndarray,
        segments,
        text_mask: np.ndarray,
        gray: np.ndarray | None = None,
        text_height: float | None = None,
    ) -> None:
        self.binary = binary
        self.segments = segments
        self.text_mask = text_mask
        # A callout is drawn at whatever angle the sheet has room for, so the strokes that can carry one
        # are not only the axis ones. Their band is read from the sheet's own thin weight instead of from
        # a pixel count at one dpi: on these sheets the lines that carry dimensions come out 2-3 px and
        # the outlines and title-block rules 5-6 px, so a leader is long and thin relative to its own
        # drawing. Length is measured against the printed text where it is known, because a glyph stroke
        # is about as long as the letter it belongs to and a leader is longer than the words it points
        # from.
        weight = float(np.median([segment.thickness for segment in segments])) if len(segments) else 2.0
        min_length = 1.5 * text_height if text_height else 12.0 * weight
        self.diagonals = (
            lines.diagonal_strokes(
                gray,
                binary,
                min_length=min_length,
                max_thickness=2.0 * weight,
                text_mask=text_mask,
            )
            if gray is not None
            else []
        )
        self.strokes = [*segments, *self.diagonals]
        self.anchors: dict[tuple[float, float], list[tuple[float, float]]] = {}
        self.taken: list[tuple[float, float, float, float]] = []

    def accepts(self, box: tuple[float, float, float, float]) -> tuple[bool, list[list[float]] | None, AnchorMode]:
        if any(_overlaps(box, taken) for taken in self.taken):
            return False, None, "dimension"
        found = lines.dimension_for(self.binary, self.segments, box, self.text_mask)
        if found is not None:
            anchors = [[point[0], point[1]] for point in found.anchors]
            self.anchors[box] = anchors
            self.taken.append(box)
            return True, anchors, "dimension"
        leader = lines.leader_near(self.binary, self.strokes, box, self.text_mask)
        if leader is None:
            return False, None, "dimension"
        # A leader's arrow marks the feature; its tail is only where the text is.
        anchors = [list(leader.tip), list(leader.tail)]
        self.anchors[box] = anchors
        self.taken.append(box)
        return True, anchors, "leader"


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float], limit: float = 0.3) -> bool:
    """Do two candidate text boxes claim the same printed characters?

    Glyph clustering is done twice, in two modes, and a rotated number can be found both as a whole and
    as its fragments; without this a printed 80 arrives once as itself and once as a stray 0, and each
    copy costs its own read.
    """
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    if right <= left or bottom <= top:
        return False
    overlap = (right - left) * (bottom - top)
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1.0
    return overlap / smaller > limit


def _cluster_box(glyphs: list[Glyph], cluster: list[int]) -> tuple[float, float, float, float]:
    return (
        float(min(glyphs[index][2] for index in cluster)),
        float(min(glyphs[index][3] for index in cluster)),
        float(max(glyphs[index][2] + glyphs[index][4] for index in cluster)),
        float(max(glyphs[index][3] + glyphs[index][5] for index in cluster)),
    )


def _text_mask(gray: np.ndarray) -> np.ndarray:
    """Ink with the long straight strokes taken out: what is left is printed text."""
    _, ink = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY_INV)
    horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (28, 1))
    vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 28))
    rules = cv2.bitwise_or(
        cv2.morphologyEx(ink, cv2.MORPH_OPEN, horizontal),
        cv2.morphologyEx(ink, cv2.MORPH_OPEN, vertical),
    )
    return cv2.subtract(ink, rules)


def _collect_spans(gray: np.ndarray, glyphs: list[Glyph], mode: str, gate=None, reader=None) -> list[Span]:
    spans: list[Span] = []
    for cluster in _cluster_glyphs(glyphs, mode):
        # A printed number is a handful of digits; a cluster longer than eight is a line of words, or two
        # numbers that a separator's reach has bridged together.
        if not 1 <= len(cluster) <= 8:
            continue
        box = _cluster_box(glyphs, cluster)
        anchors = None
        mode: AnchorMode = "dimension"
        if gate is not None:
            accepted, anchors, mode = gate.accepts(box)
            if not accepted:
                continue
        span = _read_cluster(gray, glyphs, cluster, len(spans), reader, anchors, mode)
        if span is not None:
            spans.append(span)
    return spans


def _cluster_glyphs(glyphs: list[Glyph], mode: str = "center") -> list[list[int]]:
    """Digits grouped into printed numbers. Separators are not members: they are only bridges.

    A separator small enough to be a comma is small enough to be a speck of ink as well, and there are
    many of them on a rendered sheet - about two hundred on the plate. As members of a cluster they chain
    through each other and swallow the sheet into one group of every glyph on it, which no number can be.
    They are consulted between two digits instead, and the crop of a number already spans the room they
    take, so the reader still sees the comma.
    """
    unused = {index for index, glyph in enumerate(glyphs) if not glyph.separator}
    clusters: list[list[int]] = []
    while unused:
        seed = unused.pop()
        group = [seed]
        grew = True
        while grew:
            grew = False
            for index in list(unused):
                close = _same_word if mode == "gap" else _centers_near
                if any(close(glyphs[index], glyphs[other]) or _separator_between(glyphs[index], glyphs[other], glyphs) for other in group):
                    group.append(index)
                    unused.remove(index)
                    grew = True
        clusters.append(group)
    return clusters


def _reading_turn(glyphs: list[Glyph], cluster: list[int]) -> int | None:
    """Which quarter turn makes a printed number upright, worked out from the drawing instead of tried.

    The digits of a number lie in a line, which says which axis the number is printed along, but not which
    way round it runs: a crop of `80,00` printed up a vertical dimension came back `08`, and of the four
    rotations tried in turn every one of them parses as some number - `08`, `O0`, `8000`. What settles the
    sense is the decimal separator, which sits below the baseline of the digits: the side it lies on is the
    down side of the text, and the text runs a quarter turn from there. On the plate sheet the comma of
    `80,00` sits to the right of its digits, at (174, 875) against a digit line at x = 162, so that number
    reads bottom to top and its crop wants turning clockwise - the one turn that reads it as `8000`.

    `None` when the drawing does not say: a single digit has no line to judge, and without a separator
    there is nothing to say which end of the line is the start.
    """
    digits = [glyphs[index] for index in cluster if not glyphs[index].separator]
    if len(digits) < 2:
        return None
    left, right = min(g.cx for g in digits), max(g.cx for g in digits)
    top, bottom = min(g.cy for g in digits), max(g.cy for g in digits)
    size = float(max(max(glyph.w, glyph.h) for glyph in digits))
    centre = ((left + right) / 2, (top + bottom) / 2)
    down = None
    best = 1.3 * size
    for blob in glyphs:
        if not blob.separator or max(blob.w, blob.h) > 0.6 * size:
            continue
        away = math.hypot(blob.cx - centre[0], blob.cy - centre[1])
        if away < best:
            down, best = (blob.cx - centre[0], blob.cy - centre[1]), away
    if down is None:
        return None
    read = (down[1], -down[0])  # a quarter turn clockwise from the way the digits sit is the way they read
    if right - left >= bottom - top:
        return 0 if read[0] >= 0 else 180
    return 90 if read[1] < 0 else -90


def _turn_crop(crop: np.ndarray, turn: int | None) -> np.ndarray:
    """The crop turned upright by the quarter turn the drawing gave, clockwise as `cv2.rotate` means it."""
    if turn == 90:
        return cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
    if turn == -90:
        return cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if turn == 180:
        return cv2.rotate(crop, cv2.ROTATE_180)
    return crop


def _scaled_for_reading(crop: np.ndarray, text_size: float, target: float = 64.0, most: float = 6.0) -> np.ndarray:
    """The crop of a number enlarged until its digits are comfortable to read.

    A dimension on these sheets stands 14-28 px tall, and a reader handed a 14 px digit is being asked
    about a smudge: on the plate sheet read as a raster the crops came back as `,00` and `).00` where the
    sheet prints `80,00`, with the geometry around them already correct.

    The factor is measured against the size of the *text*, not of the crop. A number printed up a vertical
    dimension sits in a crop 33 px wide and 95 px tall, and scaling by the longest side left it untouched:
    the digits stayed 18 px, and turning that crop upright to read it gave `08` for `80,00`. Scaling by the
    size of the digits - which is a ratio of the digits themselves, so the same code reads a sheet at any
    dpi - brings them to a size a reader can work with, which is where `8000` came from.
    """
    factor = min(most, max(1.0, target / max(1.0, text_size)))
    if factor <= 1.01:
        return crop
    return cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def _read_cluster(
    gray: np.ndarray,
    glyphs: list[Glyph],
    cluster: list[int],
    serial: int,
    reader=None,
    anchors: list[list[float]] | None = None,
    mode: AnchorMode = "dimension",
) -> Span | None:
    x0 = min(glyphs[index][2] for index in cluster) - 3
    y0 = min(glyphs[index][3] for index in cluster) - 3
    x1 = max(glyphs[index][2] + glyphs[index][4] for index in cluster) + 3
    y1 = max(glyphs[index][3] + glyphs[index][5] for index in cluster) + 3
    crop = gray[max(0, y0) : y1, max(0, x0) : x1]
    if crop.size == 0:
        return None
    turn = _reading_turn(glyphs, cluster)
    crop = _turn_crop(crop, turn)
    crop = _scaled_for_reading(crop, float(np.median([max(glyphs[index].w, glyphs[index].h) for index in cluster])))
    if reader is not None:
        # The crop is upright already when the drawing said which way round it runs; only without that does
        # the model get told the text stands along a vertical line.
        vertical = turn is None and bool(anchors) and abs(anchors[0][0] - anchors[1][0]) < abs(anchors[0][1] - anchors[1][1])
        text = read_dimension(reader, crop, vertical)
        if text and _plausible(text, crop, mode):
            kind, value, unit = _clean_dimension(text)
            if _usable(value):
                return _make_span(serial, text, kind, value, unit, x0, y0, x1, y1, anchors, mode)
        return None
    angle = _ink_angle(crop)
    text = ""
    for delta in (0, -angle, 90, -90):
        text = _ocr_upright(crop, delta, whitelist=False)
        kind, value, unit = _clean_dimension(text)
        if _usable(value):
            return _make_span(serial, text, kind, value, unit, x0, y0, x1, y1, anchors, mode)
    for delta in (0, 90, -90, -angle):
        text = _ocr_upright(crop, delta, whitelist=True)
        kind, value, unit = _clean_dimension(text)
        if _usable(value):
            return _make_span(serial, text, kind, value, unit, x0, y0, x1, y1, anchors, mode)
    return None


def _centers_near(a: Glyph, b: Glyph) -> bool:
    """Two glyphs are part of the same printed number if they sit within one character's reach of each other.

    The reach is measured on the glyph's *longest* side, not its height: a number printed along a vertical
    dimension line is a quarter turn round, so its digits are wider than they are tall and two of them sit
    as far apart as two upright digits would — measuring on height split `35` into a `3` and a `5`, each
    then matched to the same line and read as its own number.
    """
    limit = 0.7 * max(a[4], a[5], b[4], b[5]) + 6
    return math.hypot(a[0] - b[0], a[1] - b[1]) < limit


def _separator_between(a: Glyph, b: Glyph, glyphs: list[Glyph]) -> bool:
    """Whether two digits are separated only by the decimal separator, with nothing else between them.

    A separator is too small to be kept as a glyph of its own, so the digits on either side of it are all
    that is left to measure, and the room it takes reads as a gap between two numbers: on the plate sheet
    the comma's own room pushed them 30.6 px apart against a 25.6 px reach, and every dimension on the
    sheet came apart at its decimal point.

    A comma is not just any small blob lying between two digits, though. A rendered sheet is full of them
    - about two hundred on the plate, along dimension lines and hatching - and accepting one of those made
    the digits of the whole sheet one group. So the blob has to be close to *both* digits, one character's
    reach at most, small against the digits, and roughly on the way from one to the other.
    """
    reach = math.hypot(a.cx - b.cx, a.cy - b.cy)
    size = float(max(a.w, a.h, b.w, b.h))
    if reach <= 0 or reach > 1.6 * size:
        return False
    along_x, along_y = b.cx - a.cx, b.cy - a.cy
    for blob in glyphs:
        if not blob.separator or max(blob.w, blob.h) > 0.6 * size:
            continue
        # The blob stands between them: its projection falls inside the span, and it is near the line the
        # two digits are on. Measured as the length of the path through it instead, a comma sitting 12 px
        # to the side of the digits it belongs to missed the limit by half a pixel.
        along = ((blob.cx - a.cx) * along_x + (blob.cy - a.cy) * along_y) / reach
        if not 0.15 * reach <= along <= 0.85 * reach:
            continue
        across = abs((blob.cx - a.cx) * along_y - (blob.cy - a.cy) * along_x) / reach
        if across > 0.7 * size:
            continue
        return True
    return False


def _same_word(a: Glyph, b: Glyph) -> bool:
    gap_x = max(0, max(a.x, b.x) - min(a.x + a.w, b.x + b.w))
    gap_y = max(0, max(a.y, b.y) - min(a.y + a.h, b.y + b.h))
    same_row = abs((a.y + a.h / 2) - (b.y + b.h / 2)) <= max(a.h, b.h) * 0.6
    same_col = abs((a.x + a.w / 2) - (b.x + b.w / 2)) <= max(a.w, b.w) * 0.8
    return (same_row and gap_x <= 12 and gap_y <= max(a.h, b.h)) or (same_col and gap_y <= 12 and gap_x <= max(a.w, b.w))


def _usable(value: float | None) -> bool:
    """A span with a number is kept whatever its size: a printed 6 is a dimension, not noise.

    Noise is rejected where it can be told apart (letters in the token, a four-digit number that is
    a part number or a year, the title block, the frame), not by a size threshold.
    """
    return value is not None


def _ink_angle(crop: np.ndarray) -> float:
    ys, xs = np.where(crop < 160)
    if len(xs) < 8:
        return 0.0
    points = np.stack([xs, ys], axis=1).astype(np.float32)
    vx, vy, _, _ = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return math.degrees(math.atan2(float(vy), float(vx)))


def _ocr_upright(crop: np.ndarray, angle: float, whitelist: bool) -> str:
    height, width = crop.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    size = max(width, height) + 16
    rotated = cv2.warpAffine(crop, matrix, (size, size), borderValue=255)
    large = cv2.resize(rotated, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix=".png") as handle:
        cv2.imwrite(handle.name, large)
        command = ["tesseract", handle.name, "stdout", "--psm", "7", "-l", "eng"]
        if whitelist:
            command += ["-c", "tessedit_char_whitelist=0123456789RO."]
        result = subprocess.run(command, check=False, capture_output=True)
    return result.stdout.decode("utf-8", "replace").strip()


def _clean_dimension(text: str) -> tuple[SpanKind, float | None, Unit]:
    stripped = text.strip()
    spaced = re.fullmatch(r"(\d{1,2})\s+(\d)", stripped)
    if spaced:
        stripped = f"{spaced.group(1)}.{spaced.group(2)}"
    cleaned = stripped.replace(",", ".").replace(" ", "")
    cleaned = re.sub(r"[.]+$", "", cleaned)
    if cleaned.isdigit() and int(cleaned) > 999:
        return SpanKind.text, None, "mm"
    broken = re.fullmatch(r"(\d{1,3})\.(\d)$", cleaned)
    kind, value, unit = parse_dimension_unit(stripped)
    if kind == SpanKind.text and broken:
        kind, value, unit = parse_dimension_unit(f"{broken.group(1)}.{broken.group(2)}")
    return kind, value, unit


def _plausible(text: str, crop: np.ndarray, mode: AnchorMode) -> bool:
    """Does the answer fit the crop it came from?

    A number read a quarter turn round is two or three characters in a box barely wide enough for one,
    and a dimension line carries a length, never a radius: both are ways a crop of scrap ink becomes a
    plausible-looking number the drawing never printed (`R100`, `R105`).
    """
    if mode == "dimension" and any(character.isalpha() for character in text):
        return False
    digits = [character for character in text if character.isdigit()]
    if not digits:
        return False
    longest = max(crop.shape[0], crop.shape[1])
    return len(digits) <= max(2.0, longest / 9.0)


def _make_span(
    serial: int,
    text: str,
    kind: SpanKind,
    value: float,
    unit: Unit,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    anchors: list[list[float]] | None = None,
    mode: AnchorMode = "dimension",
) -> Span:
    return Span(
        id=f"ocr-{serial}",
        text=text,
        value=value,
        kind=kind,
        unit=unit,
        bbox=BBox(x=float(x0), y=float(y0), w=float(x1 - x0), h=float(y1 - y0)),
        anchors=anchors or [],
        anchor_mode=mode,
        source=Source.ocr,
    )


def _ocr_spans(image: np.ndarray) -> list[Span]:
    return _ocr_image(image, scale=3.0, origin=(0, 0))


def _ocr_view(image: np.ndarray, view) -> list[Span]:
    x, y, w, h = (int(view.bbox.x), int(view.bbox.y), int(view.bbox.w), int(view.bbox.h))
    crop = image[y : y + h, x : x + w]
    if crop.size == 0:
        return []
    spans = _ocr_image(crop, scale=4.0, origin=(x, y))
    for span in spans:
        span.view_id = view.id
    return spans


def _ocr_image(image: np.ndarray, scale: float, origin: tuple[int, int]) -> list[Span]:
    if shutil.which("tesseract") is None:
        return []
    big = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "page.png"
        tsv = Path(folder) / "out"
        cv2.imwrite(str(png), big)
        subprocess.run(
            ["tesseract", str(png), str(tsv), "-l", "eng", "--psm", "11", "--dpi", "300", "tsv"],
            check=False,
            capture_output=True,
        )
        table = Path(str(tsv) + ".tsv")
        if not table.exists():
            return []
        spans = _spans_from_tsv(table.read_text(errors="ignore"))
    ox, oy = origin
    for span in spans:
        span.bbox.x = span.bbox.x / scale + ox
        span.bbox.y = span.bbox.y / scale + oy
        span.bbox.w = span.bbox.w / scale
        span.bbox.h = span.bbox.h / scale
    return spans


def _assign_views(spans: list[Span], views) -> None:
    for span in spans:
        if span.view_id:
            continue
        cx = span.bbox.x + span.bbox.w / 2
        cy = span.bbox.y + span.bbox.h / 2
        for view in views:
            box = view.bbox
            if box.x <= cx <= box.x + box.w and box.y <= cy <= box.y + box.h:
                span.view_id = view.id
                break


def _dedupe_spans(spans: list[Span]) -> list[Span]:
    kept: list[Span] = []
    for span in spans:
        if span.value is None:
            continue
        if any(
            abs((other.value or 0) - span.value) < 1e-6
            and other.view_id == span.view_id
            and abs(other.bbox.x - span.bbox.x) < 12
            and abs(other.bbox.y - span.bbox.y) < 12
            for other in kept
        ):
            continue
        kept.append(span)
    return kept


def _spans_from_tsv(text: str) -> list[Span]:
    spans: list[Span] = []
    lines = text.splitlines()
    if not lines:
        return spans
    header = lines[0].split("\t")
    for row in lines[1:]:
        cells = row.split("\t")
        if len(cells) != len(header):
            continue
        record = dict(zip(header, cells, strict=True))
        word = record.get("text", "").strip()
        if not word or word == "-":
            continue
        kind, value, unit = parse_dimension_unit(word)
        if value is None:
            continue
        try:
            conf = float(record.get("conf", "-1"))
        except ValueError:
            conf = -1
        if conf < 40:
            continue
        spans.append(
            Span(
                id=f"ocr-{len(spans)}",
                text=word,
                value=value,
                kind=kind,
                unit=unit,
                bbox=BBox(
                    x=float(record["left"]),
                    y=float(record["top"]),
                    w=float(record["width"]),
                    h=float(record["height"]),
                ),
                source=Source.ocr,
            )
        )
    return spans
