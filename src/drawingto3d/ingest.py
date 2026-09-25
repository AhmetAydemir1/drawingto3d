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
    spans = _vector_spans(page, scale)
    height, width = image.shape[:2]
    return Page(
        path=str(file),
        width=width,
        height=height,
        image_png=encoded.tobytes(),
        spans=spans,
        vector_text=bool(spans),
    )


def _vector_spans(page, scale: float) -> list[Span]:
    textpage = page.get_textpage()
    count = textpage.count_chars()
    chars: list[tuple[str, float, float, float, float]] = []
    for index in range(count):
        char = textpage.get_text_range(index, 1)
        if char.isspace():
            continue
        left, bottom, right, top = textpage.get_charbox(index)
        chars.append((char, float(left), float(bottom), float(right), float(top)))
    spans: list[Span] = []
    for text, box in _group_chars(chars):
        kind, value, unit = parse_dimension_unit(text)
        if value is None or kind == SpanKind.text:
            continue
        x0, y0, x1, y1 = box
        spans.append(
            Span(
                id=f"pdf-{len(spans)}",
                text=text,
                value=value,
                kind=kind,
                unit=unit,
                bbox=BBox(x=x0 * scale, y=y0 * scale, w=(x1 - x0) * scale, h=(y1 - y0) * scale),
                source=Source.pdf_text,
            )
        )
    return spans


def _group_chars(chars: list[tuple[str, float, float, float, float]]) -> list[tuple[str, tuple[float, float, float, float]]]:
    """A PDF draws `1 1/4` as three words. One dimension is one phrase, so join across small gaps.

    Thresholds use the taller of the two glyphs: a decimal point is 1 pt tall next to a 9 pt digit,
    and judging the gap by the point's own height is what used to split `1.563in` into `1` and `563in`.
    A gap wide enough to be a printed space is kept as a space so `1 1/4` does not become `11/4`.
    """
    phrases: list[tuple[str, tuple[float, float, float, float]]] = []
    text = ""
    box: list[float] | None = None
    last: tuple[str, float, float, float, float] | None = None
    for char in chars:
        joins, spaced = (False, False) if last is None else _joins(last, char)
        if not joins:
            _add_phrase(phrases, text, box)
            text, box = "", None
            spaced = False
        if spaced and char[0] not in ".,:;°":
            text += " "
        text += char[0]
        left, bottom, right, top = char[1], char[2], char[3], char[4]
        box = [left, bottom, right, top] if box is None else [min(box[0], left), min(box[1], bottom), max(box[2], right), max(box[3], top)]
        last = char
    _add_phrase(phrases, text, box)
    return phrases


def _add_phrase(phrases: list, text: str, box: list[float] | None) -> None:
    text = text.strip()
    if text and box is not None:
        phrases.append((text, (box[0], box[1], box[2], box[3])))


def _joins(previous: tuple[str, float, float, float, float], char: tuple[str, float, float, float, float]) -> tuple[bool, bool]:
    """Same phrase? And if so, was there a printed space between them?"""
    _pc, _pl, _pb, pr, pt = previous
    _cc, cl, cb, _cr, ct = char
    small = min(pt - _pb, ct - cb) or 1.0
    tall = max(pt - _pb, ct - cb)
    if min(pt, ct) - max(_pb, cb) < 0.5 * small:
        return False, False
    gap = cl - pr
    if gap > 0.9 * tall or gap < -1.5 * tall:
        return False, False
    return True, gap > 0.25 * tall


_COUNT_PREFIX = re.compile(r"^\s*(\d{1,2})\s*(?:[xX×]\s*(\d{1,2}))?\s*(?:[-–]\s*|[xX×]\s*)(?=[ØÖ⌀ΦRrCc\d])")
_INCH_MARK = re.compile(r"(?<![A-Za-z])(?:inch(?:es)?|in)(?![A-Za-z])|\"", re.IGNORECASE)
_MM_MARK = re.compile(r"(?<![A-Za-z])(?:mm|millimet(?:re|er)s?)(?![A-Za-z])", re.IGNORECASE)
_MIXED = re.compile(r"^(\d+)\s+(\d+)\s*/\s*(\d+)$")
_FRACTION = re.compile(r"^(\d+)\s*/\s*(\d+)$")
_LETTERS = re.compile(r"[A-Za-z]")


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
      - a trailing in/inch/" or any fraction makes it inches: `1.563in`, `1 1/4` (a bare fraction is
        never millimetres on these drawings);
      - a mixed number is one dimension: `1 1/4` is 1.25, not two numbers;
      - a token with letters left over is not a dimension: `2389K26`, `A4`, `SCALE 1:2` are text;
      - `Ø`, `⌀`, `Φ`, a leading `R`, a leading `C` (chamfer) and `°` set the kind, not the value.
    """
    _count, body = split_count(text)
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
    if _INCH_MARK.search(text) or "/" in text:
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
