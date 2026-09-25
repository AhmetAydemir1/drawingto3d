"""Load a PNG, JPG, or one PDF page. Vector PDF text is read from the file."""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from drawingto3d.schema import BBox, Page, Source, Span, SpanKind, Unit

RASTER_DPI = 200


def apply_sheet_unit(spans: list[Span]) -> None:
    """One sheet has one unit. If anything on it is marked inches, the unmarked numbers are inches too.

    A catalog drawing prints `0.688in` and `2X 1 1/4`, then `1.5in`; only the pipe-size callout has no
    mark, and reading that as millimetres would put a 2 mm fitting next to a 39 mm flange.
    """
    if not any(span.unit == "in" for span in spans if span.value is not None):
        return
    for span in spans:
        if span.unit == "mm" and span.value is not None:
            span.unit = "in"


def load_page(path: str | Path) -> Page:
    file = Path(path)
    suffix = file.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(file)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return _load_raster(file)
    raise ValueError(f"desteklenmeyen girdi: {suffix}")


def _load_raster(file: Path) -> Page:
    image = cv2.imread(str(file), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"görüntü okunamadı: {file}")
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("png kodlanamadı")
    height, width = image.shape[:2]
    return Page(path=str(file), width=width, height=height, image_png=encoded.tobytes())


def _load_pdf(file: Path) -> Page:
    document = pdfium.PdfDocument(str(file))
    if len(document) == 0:
        raise ValueError("pdf boş")
    page = document[0]
    scale = RASTER_DPI / 72.0
    bitmap = page.render(scale=scale)
    image = bitmap.to_numpy()
    if image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    else:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("pdf raster kodlanamadı")
    height, width = image.shape[:2]
    spans = _vector_spans(page, scale, cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    return Page(
        path=str(file),
        width=width,
        height=height,
        image_png=encoded.tobytes(),
        spans=spans,
        vector_text=bool(spans),
    )


def _vector_spans(page, scale: float, gray: np.ndarray) -> list[Span]:
    """The numbers printed in the file's own text layer, in raster pixels.

    The text layer gives each character's box in PDF points from the bottom-left corner, while everything
    else in this program works in raster pixels from the top-left. Rather than assume one drawing tool's
    convention, the sheet itself is asked: the boxes are placed both ways and the placement that lands on
    the sheet's ink is kept. A sheet whose text is drawn in a bottom-left frame (McMaster's catalog PDFs)
    is mirrored against the raster; the same code reads a sheet drawn the other way round (the self-made
    A4 sheets) without a per-file branch.
    """
    textpage = page.get_textpage()
    count = textpage.count_chars()
    chars: list[tuple[str, float, float, float, float]] = []
    for index in range(count):
        char = textpage.get_text_range(index, 1)
        if char.isspace():
            continue
        left, bottom, right, top = textpage.get_charbox(index)
        chars.append((char, float(left), float(bottom), float(right), float(top)))
    if not chars:
        return []
    rows = _group_along(chars)
    boxes: list[tuple[str, tuple[float, float, float, float]]] = []
    for text, box, _members in rows:
        kind, value, unit = parse_dimension_unit(text)
        if value is None or kind == SpanKind.text:
            continue
        boxes.append((text, box))
    if not boxes:
        return []

    upright = _upright_placement(boxes, gray, scale, section_height_pt=page.get_size()[1])
    spans: list[Span] = []
    for text, box in boxes:
        kind, value, unit = parse_dimension_unit(text)
        x, y, w, h = upright(box, scale)
        spans.append(
            Span(
                id=f"pdf-{len(spans)}",
                text=text,
                value=value,
                kind=kind,
                unit=unit,
                bbox=BBox(x=x, y=y, w=w, h=h),
                source=Source.pdf_text,
            )
        )
    return spans


def _upright_placement(boxes, gray: np.ndarray, scale: float, section_height_pt: float):
    """Which way round a text layer sits on the raster, measured from the ink it must be covering."""

    def mirrored(box, scale: float) -> tuple[float, float, float, float]:
        left, bottom, right, top = box
        x0, y0 = left * scale, (section_height_pt - top) * scale
        return x0, y0, (right - left) * scale, (top - bottom) * scale

    def as_is(box, scale: float) -> tuple[float, float, float, float]:
        left, bottom, right, top = box
        x0, y0 = left * scale, bottom * scale
        return x0, y0, (right - left) * scale, (top - bottom) * scale

    candidates = (mirrored, as_is)
    scores = [sum(_contrast_under(gray, place(box, scale)) for _text, box in boxes) for place in candidates]
    if scores[0] == scores[1]:
        # Nothing on the sheet disagrees: a PDF's own frame starts at the bottom-left, so the plain
        # reading of a char box is the one that has to be turned over to sit on the raster.
        return candidates[0]
    return candidates[int(scores[1] > scores[0])]


def _contrast_under(gray: np.ndarray, box: tuple[float, float, float, float]) -> float:
    """How much darker a placed text box is than the paper around it.

    Counting dark pixels is not enough: a shaded pictorial view is one large dark area, and a box that
    lands anywhere on it scores full marks (that is how a shaded isometric once decided the orientation
    of a whole sheet). Printed text is darker than its own surroundings on any sheet, white or grey, so
    each box is compared with a ring around it instead.
    """
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return 0.0
    pad = max(2, int(round(0.75 * max(w, h))))
    top, bottom = max(int(y) - pad, 0), min(int(y + h) + pad, gray.shape[0])
    left, right = max(int(x) - pad, 0), min(int(x + w) + pad, gray.shape[1])
    if bottom <= top or right <= left:
        return 0.0
    window = gray[top:bottom, left:right]
    y0, y1 = max(int(y) - top, 0), min(int(y + h) - top, bottom - top)
    x0, x1 = max(int(x) - left, 0), min(int(x + w) - left, right - left)
    inside = window[y0:y1, x0:x1]
    if inside.size == 0:
        return 0.0
    around = np.concatenate(
        [window[:y0].ravel(), window[y1:].ravel(), window[y0:y1, :x0].ravel(), window[y0:y1, x1:].ravel()]
    )
    if around.size == 0:
        return 0.0
    return max(0.0, float(around.mean()) - float(inside.mean()))


def _group_along(chars: list[tuple[str, float, float, float, float]]) -> list[tuple[str, tuple[float, float, float, float], list[int]]]:
    """Join the characters that sit next to each other, in the order the PDF prints them.

    The PDF gives characters, not words. Two characters belong to the same printed number when they are
    neighbours either along the line or down a column: a number printed beside a vertical dimension line is
    a quarter turn round, so its digits stack. Every threshold is the size of the two characters being
    compared, never a number of points or pixels, so the same code reads a 1:1 A4 and a 1:4 A0 — and a
    page whose title block is set smaller than its dimensions does not shrink the dimensions with it.
    """
    phrases: list[tuple[str, tuple[float, float, float, float], list[int]]] = []
    current: list[int] = []
    for index, char in enumerate(chars):
        if current and not _next_to(chars[current[-1]], char):
            phrases.append(_phrase(chars, current))
            current = []
        current.append(index)
    if current:
        phrases.append(_phrase(chars, current))
    return phrases


def _next_to(previous: tuple[str, float, float, float, float], char: tuple[str, float, float, float, float]) -> bool:
    """Are these two characters neighbours in one printed number?"""
    return _adjacent(previous, char, "row") or _adjacent(previous, char, "column")


def _start(char: tuple[str, float, float, float, float], axis: str) -> float:
    """Where the character begins along the reading axis."""
    return char[1] if axis == "row" else char[2]


def _end(char: tuple[str, float, float, float, float], axis: str) -> float:
    return char[3] if axis == "row" else char[4]


def _cross_start(char: tuple[str, float, float, float, float], axis: str) -> float:
    """Where the character begins across the reading axis: its bottom for a line, its left for a column."""
    return char[2] if axis == "row" else char[1]


def _cross_end(char: tuple[str, float, float, float, float], axis: str) -> float:
    return char[4] if axis == "row" else char[3]


def _cross_extent(char: tuple[str, float, float, float, float], axis: str) -> float:
    return (char[4] - char[2]) if axis == "row" else (char[3] - char[1])


def _along_gap(a: tuple[str, float, float, float, float], b: tuple[str, float, float, float, float], axis: str) -> float:
    return max(0.0, max(_start(a, axis), _start(b, axis)) - min(_end(a, axis), _end(b, axis)))


def _adjacent(a: tuple[str, float, float, float, float], b: tuple[str, float, float, float, float], axis: str) -> bool:
    """Neighbours along one axis, and sharing the other."""
    overlap = min(_cross_end(a, axis), _cross_end(b, axis)) - max(_cross_start(a, axis), _cross_start(b, axis))
    size = max(_cross_extent(a, axis), _cross_extent(b, axis)) or 1.0
    return _along_gap(a, b, axis) <= 0.9 * size and overlap > 0.5 * min(_cross_extent(a, axis), _cross_extent(b, axis))


def _phrase(chars: list[tuple[str, float, float, float, float]], members: list[int]) -> tuple[str, tuple[float, float, float, float], list[int]]:
    """The text of a run of characters, and the box it covers.

    A gap wide enough to be a printed space is kept as one, so `1 1/4` does not become `11/4`; a gap only
    as wide as the space a narrow digit like `1` leaves is not a space, so `100,00` does not become
    `1 00,00`.
    """
    text = ""
    box: list[float] | None = None
    previous: tuple[str, float, float, float, float] | None = None
    for index in members:
        char = chars[index]
        if previous is not None:
            # Spacing is judged on the axis the two characters actually joined along: a pair on one line
            # overlaps across the column as well, and reading the gap off that axis would close up a real
            # printed space (`2X 1 1/4` becoming `2X11/4`, which reads as eleven quarters).
            axis = "row" if _adjacent(previous, char, "row") else "column"
            spaced = _along_gap(previous, char, axis) > 0.3 * max(_cross_extent(previous, axis), _cross_extent(char, axis))
            if spaced and char[0] not in ".,:;°":
                text += " "
        text += char[0]
        left, bottom, right, top = char[1], char[2], char[3], char[4]
        box = [left, bottom, right, top] if box is None else [min(box[0], left), min(box[1], bottom), max(box[2], right), max(box[3], top)]
        previous = char
    assert box is not None
    return text, (box[0], box[1], box[2], box[3]), members


_COUNT_PREFIX = re.compile(r"^\s*(\d{1,2})\s*(?:[xX×]\s*(\d{1,2}))?\s*(?:[-–]\s*|[xX×]\s*)(?=[ØÖ⌀ΦRrCc\d])")
_INCH_MARK = re.compile(r"(?<![A-Za-z])(?:inch(?:es)?|in)(?![A-Za-z])|\"", re.IGNORECASE)
_MM_MARK = re.compile(r"(?<![A-Za-z])(?:mm|millimet(?:re|er)s?)(?![A-Za-z])", re.IGNORECASE)
_MIXED = re.compile(r"^(\d+)\s+(\d+)\s*/\s*(\d+)$")
_FRACTION = re.compile(r"^(\d+)\s*/\s*(\d+)$")
_LETTERS = re.compile(r"[A-Za-z]")
# Words that say how a feature is made rather than how big it is. They trail a dimension on almost every
# shop drawing (`THRU ALL`, `DEEP 12`, `TYP`, `C'BORE`), and a unit mark is not one of them.
_MANNER_WORDS = {
    "thru",
    "through",
    "all",
    "deep",
    "typ",
    "typical",
    "c'bore",
    "cbore",
    "c'sink",
    "csink",
    "spotface",
    "counterbore",
    "countersink",
    "eq",
    "eqsp",
    "pcd",
    "ref",
}
_UNIT_WORDS = {"in", "inch", "inches", "mm", "millimetre", "millimeter", "millimetres", "millimeters"}


def _drop_trailing_words(text: str) -> str:
    """`4 x 6.80 THRU ALL` is four holes of 6.80: the tail says how, not how big."""
    words = text.split()
    while len(words) > 1 and words[-1].lower().strip(".,;:") in _MANNER_WORDS and words[-1].lower().strip(".,;:") not in _UNIT_WORDS:
        words.pop()
    return " ".join(words)


def split_count(text: str) -> tuple[int, str]:
    """`4x2-Ø30` sizes eight holes of Ø30. Returns the count and the dimension text without it."""
    match = _COUNT_PREFIX.match(text)
    if match is None:
        return 1, text.strip()
    count = int(match.group(1))
    if match.group(2):
        count *= int(match.group(2))
    return max(count, 1), text[match.end() :].strip()


def parse_dimension(text: str) -> tuple[SpanKind, float | None]:
    """Kind and printed number; see parse_dimension_unit for the unit."""
    kind, value, _unit = parse_dimension_unit(text)
    return kind, value


def parse_dimension_unit(text: str) -> tuple[SpanKind, float | None, Unit]:
    """Read one printed dimension as a machine value.

    Rules that matter for real sheets:
      - a trailing in/inch/\" or any fraction makes it inches: `1.563in`, `1 1/4` (a bare fraction is
        never millimetres on these drawings);
      - a mixed number is one dimension: `1 1/4` is 1.25, not two numbers;
      - a trailing word says how the feature is made, not how big it is: `4 x 6.80 THRU ALL` is four holes
        of 6.80, and the same goes for `DEEP`, `TYP`, `C'BORE`, `THRU`;
      - a token with letters left over is not a dimension: `2389K26`, `A4`, `SCALE 1:2` are text;
      - `Ø`, `⌀`, `Φ`, a leading `R`, a leading `C` (chamfer) and `°` set the kind, not the value.
    """
    _count, body = split_count(text)
    body = _drop_trailing_words(body)
    unit = _unit_of(body)
    head = body.strip()
    kind = SpanKind.linear
    if head[:1] in ("R", "r") and not head.lower().startswith("ra"):
        kind = SpanKind.radius
    elif any(mark in head for mark in ("Ø", "⌀", "Φ", "Ö")) or (head[:1] in ("o", "O") and head[1:2].isdigit()):
        kind = SpanKind.diameter
    if "°" in head:
        kind = SpanKind.angle
    raw = _strip_marks(head)
    if not raw or _LETTERS.search(raw):
        return SpanKind.text, None, unit
    value = _number(raw)
    if value is None:
        return SpanKind.text, None, unit
    return kind, value, unit


def _unit_of(text: str) -> Unit:
    """A fraction is inches by convention (nobody dimensions a millimetre part in sixteenths); otherwise
    only an explicit mark decides, and the sheet default is millimetres."""
    if _INCH_MARK.search(text):
        return "in"
    for pattern in (_MIXED, _FRACTION):
        if pattern.match(text.strip()):
            return "in"
    return "mm"


def _strip_marks(text: str) -> str:
    raw = text.replace(",", ".")
    for mark in ("Ø", "⌀", "Φ", "Ö", "°", '"'):
        raw = raw.replace(mark, "")
    raw = re.sub(r"(?<![A-Za-z])(?:inch(?:es)?|in|mm)(?![A-Za-z])", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^[Rr](?=\d)", "", raw)
    raw = re.sub(r"^[Cc](?=\d)", "", raw)
    raw = re.sub(r"^[Mm](?=\d)", "", raw)
    return " ".join(raw.split())


def _number(raw: str) -> float | None:
    mixed = _MIXED.match(raw)
    if mixed:
        whole, numerator, denominator = (float(item) for item in mixed.groups())
        return whole + numerator / denominator if denominator else None
    tight = raw.replace(" ", "")
    fraction = _FRACTION.match(tight)
    if fraction:
        numerator, denominator = (float(item) for item in fraction.groups())
        return numerator / denominator if denominator else None
    number = ""
    for char in tight:
        if char.isdigit() or (char == "." and "." not in number):
            number += char
        elif number:
            break
    if not number or number == ".":
        return None
    return float(number)
