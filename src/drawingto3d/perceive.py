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

from drawingto3d import lines, scale
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
    clusters: dict[int, list[int]] = {}
    spans = _collect_spans(gray, glyphs, "center", gate, reader, clusters) + _collect_spans(
        gray, glyphs, "gap", gate, reader, clusters
    )
    spans = _one_number_per_line(spans)
    for index, span in enumerate(spans):
        span.id = f"ocr-{index}"
    # The pairing first, the value second: the re-read judges a candidate against the line it would sit on,
    # so a reading anchored to somebody else's line has to be given its own before it can be judged at all.
    spans = _repoint_lines_that_are_not_their_own(segments, spans)
    spans = _reread_against_the_sheet_scale(gray, glyphs, spans, clusters, reader)
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
        # The sheet's printed text, measured once: `leader_near` needs it to tell a leader drawn at an
        # angle (whose own ink the mask cannot remove) from a stroke that is really part of a word.
        self.printed = lines.PrintedText.of(text_mask)
        self.anchors: dict[tuple[float, float], list[tuple[float, float]]] = {}
        self.taken: list[tuple[float, float, float, float]] = []

    def accepts(
        self,
        box: tuple[float, float, float, float],
        block: tuple[tuple[float, float, float, float], float] | None = None,
    ) -> tuple[bool, list[list[float]] | None, AnchorMode]:
        if any(_overlaps(box, taken) for taken in self.taken):
            return False, None, "dimension"
        found = lines.dimension_for(self.binary, self.segments, box, self.text_mask, strokes=self.diagonals)
        if found is not None:
            anchors = [[point[0], point[1]] for point in found.anchors]
            self.anchors[box] = anchors
            self.taken.append(box)
            return True, anchors, "dimension"
        leader = lines.leader_near(self.binary, self.strokes, box, self.text_mask, printed_text=self.printed)
        if leader is None and block is not None:
            # A number printed inside a note is carried by the note's own leader, wherever in the note it
            # was printed: the gap to the number's box alone throws the `6,80` of `4 x Ø 6,80 THRU ALL`
            # away, and `leader_to_note` asks of that leader what a note's leader has to be.
            note, character = block
            leader = lines.leader_to_note(
                self.binary,
                self.strokes,
                note,
                self.text_mask,
                printed_text=self.printed,
                character=character,
            )
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


def _printed_block(
    glyphs: list[Glyph],
    cluster: list[int],
    gap: float = 2.0,
    lines: float = 2.0,
) -> tuple[tuple[float, float, float, float], float] | None:
    """The printed block this cluster sits in, letters and all: the note the drawing carries it inside.

    A callout's leader is drawn to the note, not to each number in it: on the plate the leader of
    `4 x Ø 6,80 THRU ALL` ends 28 px from the note's own ink and 181 px from the `6,80` it names, so a gate
    that measures the gap to the number alone throws away a number the drawing carries. The block is grown
    from the cluster along the cluster's own line — a number printed under a leader is written along that
    leader, so the line is not always the sheet's axis — joining glyphs of one printed line within `gap`
    characters of each other (a word space is about half a character, so two words of a line are joined),
    and then keeping the printed lines within `lines` characters *across* that line and inside the line's
    own width: a note's lines sit above one another, and the sheet's own type says how far apart they are.

    Returns the block's box and the block's own measured character size, or `None` when nothing joins the
    cluster — the caller then measures the leader against the number's own box, as before.
    """
    size = float(np.median([max(glyphs[index].w, glyphs[index].h) for index in cluster]))
    if size <= 0.0:
        return None
    angle = math.radians(_digits_angle(glyphs, cluster))
    along = (math.cos(angle), math.sin(angle))
    across = (-along[1], along[0])
    anchor = glyphs[cluster[0]]

    def offsets(glyph: Glyph) -> tuple[float, float]:
        dx, dy = glyph.cx - anchor.cx, glyph.cy - anchor.cy
        return dx * along[0] + dy * along[1], dx * across[0] + dy * across[1]

    line = sorted(
        ((index, *offsets(glyph)) for index, glyph in enumerate(glyphs) if abs(offsets(glyph)[1]) <= 0.45 * size),
        key=lambda item: item[1],
    )
    start = min(offsets(glyphs[index])[0] for index in cluster)
    end = max(offsets(glyphs[index])[0] for index in cluster)
    grown = set(cluster)
    grew = True
    while grew:
        grew = False
        for index, at, _across in line:
            if index in grown or not start - gap * size <= at <= end + gap * size:
                continue
            start, end = min(start, at), max(end, at)
            grown.add(index)
            grew = True
    block = [
        index
        for index, glyph in enumerate(glyphs)
        if abs(offsets(glyph)[1]) <= lines * size and start - gap * size <= offsets(glyph)[0] <= end + gap * size
    ]
    if len(block) == len(cluster):
        return None
    character = float(np.median([max(glyphs[index].w, glyphs[index].h) for index in block]))
    return _cluster_box(glyphs, block), character


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


def _collect_spans(
    gray: np.ndarray,
    glyphs: list[Glyph],
    mode: str,
    gate=None,
    reader=None,
    clusters: dict[int, list[int]] | None = None,
) -> list[Span]:
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
            accepted, anchors, mode = gate.accepts(box, _printed_block(glyphs, cluster))
            if not accepted:
                continue
        span = _read_cluster(gray, glyphs, cluster, len(spans), reader, anchors, mode)
        if span is not None:
            if clusters is not None:
                # By identity, not by id: the two clustering passes name their spans from zero and the
                # caller renumbers them afterwards, so a name is not unique yet.
                clusters[id(span)] = cluster
            spans.append(span)
    return spans


def _repoint_lines_that_are_not_their_own(segments, spans: list[Span]) -> list[Span]:
    """A reading the sheet's scale calls wrong is given the span on its own row that its value fits.

    The gate has to choose a span without knowing the value, so on a row that carries several features it
    takes the pair of crossings the number sits between — and on the plastic sheet that made `1.50` stand on
    a 113.5 px line where its own value is 5.9 px, `4.80` on the 69 px line of the step below it, and every
    one of that sheet's twenty auditable readings suspect. The sheet is its own ground truth twice over: the
    majority of its readings fit one scale (`scale.consensus`), and every printed number is drawn to the
    line it measures. So a reading no majority agrees with is offered the other pairs of crossings on its own
    row, and the one whose length fits the sheet's scale takes the place of the one that does not.

    Only the readings the calibration names are re-pointed, and only to a pair that fits: a reading whose
    row holds no such pair is left exactly as it was, on the line the gate chose. Nothing is dropped here —
    whether a record with no line of its own should carry no anchors at all is a separate decision, and the
    mispaired readings that survive this are mostly not numbers in the first place (below).

    The value is not re-read on the new pair here: that is `_reread_against_the_sheet_scale`, which runs
    after this one precisely so that it judges a candidate against the line this step has already corrected.
    """
    calibration, suspect = scale.audit(spans)
    if calibration is None or not suspect:
        return spans
    by_id = {span.id: span for span in spans}
    for id_ in suspect:
        span = by_id.get(id_)
        if span is None or span.anchor_mode != "dimension" or not span.value or len(span.anchors) != 2:
            continue
        box = (span.bbox.x, span.bbox.y, span.bbox.x + span.bbox.w, span.bbox.y + span.bbox.h)
        expected = calibration.expected_px(float(span.value))
        holding = ((float(span.anchors[0][0]), float(span.anchors[0][1])), (float(span.anchors[1][0]), float(span.anchors[1][1])))
        fitting = [
            pair
            for pair in lines.crossing_pairs(segments, box, holding)
            if not calibration.disagrees(float(span.value), math.hypot(pair[1][0] - pair[0][0], pair[1][1] - pair[0][1]))
        ]
        if not fitting:
            continue
        best = min(fitting, key=lambda pair: abs(math.hypot(pair[1][0] - pair[0][0], pair[1][1] - pair[0][1]) - expected))
        span.anchors = [list(best[0]), list(best[1])]
    return spans


def _reread_against_the_sheet_scale(
    gray: np.ndarray,
    glyphs: list[Glyph],
    spans: list[Span],
    clusters: dict[int, list[int]],
    reader=None,
) -> list[Span]:
    """A reading the sheet's own scale calls wrong is offered the reader the angles it was not asked at.

    Every dimension line is drawn to the number printed on it, so the sheet calibrates itself
    (`scale.consensus`), and a misread number is a pair whose ratio is off — a mistake the sheet itself
    names, with no ground truth needed. On the plate the vertical `8,00` is read `3,00` at the angle the
    digits' own line gives (63 px of line against 3 mm is 21 px/mm where the sheet fits 7.817) and `8,00`
    two degrees past it (7.875). The reader keeps its first answer, and when the sheet says that answer is
    wrong, the answer from the next angle is the one to keep.

    Only the readings the calibration names are asked again, and only a candidate that fits the sheet's
    own scale replaces one that does not: a re-read here costs a tesseract call per suspect, where asking
    every crop at every angle would cost three to six times the sheet's whole reading time.

    The vision model's path is left alone: one model call per crop is minutes per sheet, and a model's
    answer is not a function of the angle it was asked at, so skipping to the next angle says nothing.
    """
    if reader is not None:
        return spans
    calibration, suspect = scale.audit(spans)
    if calibration is None or not suspect:
        return spans
    by_id = {span.id: span for span in spans}
    for id_ in suspect:
        span = by_id.get(id_)
        cluster = clusters.get(id(span)) if span is not None else None
        if span is None or cluster is None or span.anchors is None or len(span.anchors) != 2 or not span.value:
            continue
        (ax, ay), (bx, by) = span.anchors
        measured = math.hypot(float(bx) - float(ax), float(by) - float(ay))
        if measured <= 0 or not calibration.disagrees(span.value, measured):
            continue
        for skip in range(1, 4):
            other = _read_cluster(gray, glyphs, cluster, 0, None, span.anchors, span.anchor_mode, skip=skip)
            if other is None or other.value is None or not _usable(other.value):
                break
            if not calibration.disagrees(other.value, measured):
                span.text, span.value, span.kind, span.unit = other.text, other.value, other.kind, other.unit
                break
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
                if any(
                    close(glyphs[index], glyphs[other])
                    or _separator_between(glyphs[index], glyphs[other], glyphs)
                    for other in group
                ):
                    group.append(index)
                    unused.remove(index)
                    grew = True
        clusters.append(group)
    return [line for cluster in clusters for line in _split_lines(glyphs, cluster)]


def _split_lines(glyphs: list[Glyph], cluster: list[int], fraction: float = 0.6) -> list[list[int]]:
    """One printed number lies on one line, so glyphs from two lines of text are two numbers.

    The clustering chains a glyph to any other within reach, and a separator's room is then measured
    between two glyphs rather than one: on the plate sheet the comma of the drawn `6,80` bridged its `8`
    to a `6` of the *line below* - 44.4 px apart against a 1.6-character limit of 44.8, missing by half a
    pixel - and the crop of that five-glyph cluster, 67 x 72 px and two printed lines tall, was read as
    `08°9`, an angle printed nowhere on the sheet, while the true 6.80 stayed missing.

    The digits of one number sit within a fraction of a character of each other across their own line,
    whether the text is printed upright or a quarter turn round, so a break in that direction is a line
    break. Nothing is grouped along the line: that is where a number's own length lives, and it is what
    makes `100,00` one number.
    """
    if len(cluster) < 2:
        return [cluster]
    size = float(np.median([max(glyphs[index].w, glyphs[index].h) for index in cluster]))
    # A number printed along a leader sits on one straight line, diagonal included, so a gap in y is
    # the number's own length and not a line break. Two printed lines are not collinear: the glyph
    # that the comma pulled up off the next line stands off the digits' line.
    if _on_one_line(glyphs, cluster, size):
        return [cluster]
    ordered = sorted(cluster, key=lambda index: glyphs[index].cy)
    rows: list[list[int]] = [[ordered[0]]]
    for index in ordered[1:]:
        if glyphs[index].cy - glyphs[rows[-1][-1]].cy > fraction * size:
            rows.append([index])
        else:
            rows[-1].append(index)
    return rows


def _on_one_line(glyphs: list[Glyph], cluster: list[int], size: float) -> bool:
    """Do these glyphs lie on one straight line, whatever angle that line has?"""
    points = [glyphs[index] for index in cluster]
    first, second = max(
        ((left, right) for index, left in enumerate(points) for right in points[index + 1 :]),
        key=lambda pair: math.hypot(pair[0].cx - pair[1].cx, pair[0].cy - pair[1].cy),
    )
    dx, dy = second.cx - first.cx, second.cy - first.cy
    length = math.hypot(dx, dy) or 1.0
    farthest = max(abs((point.cx - first.cx) * dy - (point.cy - first.cy) * dx) / length for point in points)
    return farthest <= 0.45 * size


def _digits_angle(glyphs: list[Glyph], cluster: list[int]) -> float:
    """The angle of the line the digits themselves sit on, in degrees, as the sheet prints it.

    A number written along a leader is written along that leader, not along the sheet's axes, and the
    two glyphs farthest apart state the line it is written on. A fit through the ink of its crop is a
    different thing - `_ink_angle` - and a worse one: measured on `my_part.jpg`, the `50` printed at
    45 degrees came out 28-37 degrees, because the outline of a digit leans away from the line its
    centre lies on, and the crop turned by that angle read `2` - one digit of the two, a number in its
    own right - while the digits' own 43.4 degrees read `50`.

    `0.0` when the drawing does not say: one digit is not a line, and a separator is not a digit, so a
    crop holding no line is left as it stands.
    """
    points = [glyphs[index] for index in cluster if not glyphs[index].separator]
    if len(points) < 2:
        return 0.0
    first, second = max(
        ((left, right) for index, left in enumerate(points) for right in points[index + 1 :]),
        key=lambda pair: math.hypot(pair[0].cx - pair[1].cx, pair[0].cy - pair[1].cy),
    )
    return math.degrees(math.atan2(second.cy - first.cy, second.cx - first.cx))


def _reading_angles(own: float, ink: float, least: float = 8.0) -> tuple[float, ...]:
    """The angles a crop is offered to the reader at, the drawing's own line first.

    A number written along a leader is written at that leader's angle, and the digits' own centres state
    that angle (`_digits_angle`). The reader keeps its first answer, so asking it first at the number's
    own angle is the whole difference between reading `50` and reading `2`: measured on `my_part.jpg`,
    the crop of `50` printed at 45 degrees came back `2` - one digit of the two, a number in its own
    right - as it stood, and `50` when offered at the digits' own 43.4 degrees.

    A fit through the crop's ink (`_ink_angle`) is not that line: on the same crop a fit through the
    digit outlines reads 28-37 degrees, because the outline of a digit leans away from the line its
    centre lies on. It keeps the place it had - a fallback behind the drawing's own angle and behind the
    quarter turns - and text already on an axis is read in the old order, because the drawing says
    nothing new about a number written level.
    """
    angles = [0.0, -ink, 90.0, -90.0]
    sheet_angle = abs(own) % 180.0
    if min(sheet_angle, 180.0 - sheet_angle, abs(sheet_angle - 90.0)) > least:
        angles.insert(0, (own + 90.0) % 180.0 - 90.0)
    return tuple(dict.fromkeys(round(angle, 3) for angle in angles))


def _one_pen(glyphs: list[Glyph], cluster: list[int], limit: float = 0.25) -> bool:
    """Do these glyphs present one shape, the way the digits of one printed number do?

    A number is drawn by one pen at one angle, so its digits present one shape to the clusterer: a digit
    written at 45 degrees comes out as wide as it is tall - a `1`, a thin stroke when it stands level, is
    as square as a `0` once the two are turned together - while a digit of the number that crosses this
    one is turned by another angle and does not.

    Measured on the plastic sheet: the drawn `R8.00` lies at 45 degrees and the vertical number beside it
    put a 29x18 blob (0.62) into a row of 25x25 ones (0.96); the crop of the two together read `28.006`,
    a number printed nowhere on the sheet. The widest spread a real row showed is the flange's `#50`,
    three blobs 0.23 apart.
    """
    shapes = [
        min(glyphs[index].w, glyphs[index].h) / max(1, max(glyphs[index].w, glyphs[index].h))
        for index in cluster
        if not glyphs[index].separator
    ]
    if len(shapes) < 2:
        return False
    middle = float(np.median(shapes))
    return max(abs(shape - middle) for shape in shapes) <= limit


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
    skip: int = 0,
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
    # The number's own line first, then the crop's ink, then the quarter turns: the drawing says which
    # angle the number is written at, and a reader that keeps its first answer has to be asked at it.
    # Only when the cluster really is one row of one-shaped glyphs: a digit of the number crossing this
    # one is turned by another angle, and asking at this row's angle reads the two together.
    own = _digits_angle(glyphs, cluster) if _one_pen(glyphs, cluster) else 0.0
    text = ""
    for delta in _reading_angles(own + (turn or 0), angle)[skip:]:
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
