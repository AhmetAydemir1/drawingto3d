"""Read geometry and dimension strings. Roles are assigned later, not here."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

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
    gate = _DimensionGate(binary, segments, _text_mask(gray))
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
    gate = _DimensionGate(binary, segments, text_mask)
    # One glyph list for both passes. Narrow per-pass size limits used to drop half of a rotated number
    # (the digit that looked too wide for that pass), leaving a fragment that then read as a stray digit.
    glyphs = _glyphs(gray, text_mask)
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


def _glyphs(gray: np.ndarray, text_mask: np.ndarray, longest: int = 60, amin: int = 8, amax: int = 500) -> list[tuple]:
    count, _, stats, centroids = cv2.connectedComponentsWithStats(text_mask, 8)
    height, width = gray.shape
    glyphs = []
    for index in range(1, count):
        x, y, w, h, area = [int(value) for value in stats[index]]
        if not (width * 0.04 < x < width * 0.96 and height * 0.04 < y < height * 0.96):
            continue
        # Judged on the longest side, not the height: text along a vertical dimension is printed a
        # quarter turn round, so a digit of the same size is as wide as it is tall elsewhere.
        if 8 <= min(w, h) and max(w, h) <= longest and amin <= area <= amax:
            glyphs.append((float(centroids[index][0]), float(centroids[index][1]), x, y, w, h))
    return glyphs


class _DimensionGate:
    """Keeps a printed number only if it sits against a dimension line, and remembers that line.

    A drawing prints part numbers, dates, sheet numbers, notes and title-block text; only the text that
    a dimension line points at sizes anything. The gate is the one place that decides, so the anchors it
    finds can travel with the span.
    """

    def __init__(self, binary: np.ndarray, segments, text_mask: np.ndarray) -> None:
        self.binary = binary
        self.segments = segments
        self.text_mask = text_mask
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
        leader = lines.leader_near(self.binary, self.segments, box, self.text_mask)
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


def _cluster_box(glyphs: list[tuple], cluster: list[int]) -> tuple[float, float, float, float]:
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


def _collect_spans(gray: np.ndarray, glyphs: list[tuple], mode: str, gate=None, reader=None) -> list[Span]:
    spans: list[Span] = []
    for cluster in _cluster_glyphs(glyphs, mode):
        if not 1 <= len(cluster) <= 5:
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


def _cluster_glyphs(glyphs: list[tuple], mode: str = "center") -> list[list[int]]:
    unused = set(range(len(glyphs)))
    clusters: list[list[int]] = []
    while unused:
        seed = unused.pop()
        group = [seed]
        grew = True
        while grew:
            grew = False
            for index in list(unused):
                close = _same_word if mode == "gap" else _centers_near
                if any(close(glyphs[index], glyphs[other]) for other in group):
                    group.append(index)
                    unused.remove(index)
                    grew = True
        clusters.append(group)
    return clusters


def _read_cluster(
    gray: np.ndarray,
    glyphs: list[tuple],
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
    if reader is not None:
        vertical = bool(anchors) and abs(anchors[0][0] - anchors[1][0]) < abs(anchors[0][1] - anchors[1][1])
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


def _centers_near(a: tuple, b: tuple) -> bool:
    """Two glyphs are part of the same printed number if they sit within one character's reach of each other.

    The reach is measured on the glyph's *longest* side, not its height: a number printed along a vertical
    dimension line is a quarter turn round, so its digits are wider than they are tall and two of them sit
    as far apart as two upright digits would — measuring on height split `35` into a `3` and a `5`, each
    then matched to the same line and read as its own number.
    """
    limit = 0.7 * max(a[4], a[5], b[4], b[5]) + 6
    return math.hypot(a[0] - b[0], a[1] - b[1]) < limit


def _same_word(a: tuple, b: tuple) -> bool:
    _, _, ax, ay, aw, ah = a
    _, _, bx, by, bw, bh = b
    gap_x = max(0, max(ax, bx) - min(ax + aw, bx + bw))
    gap_y = max(0, max(ay, by) - min(ay + ah, by + bh))
    same_row = abs((ay + ah / 2) - (by + bh / 2)) <= max(ah, bh) * 0.6
    same_col = abs((ax + aw / 2) - (bx + bw / 2)) <= max(aw, bw) * 0.8
    return (same_row and gap_x <= 12 and gap_y <= max(ah, bh)) or (same_col and gap_y <= 12 and gap_x <= max(aw, bw))


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
