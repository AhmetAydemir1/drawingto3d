"""Load a PNG, JPG, or one PDF page. Vector PDF text is read from the file."""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from drawingto3d.schema import BBox, Page, Source, Span, SpanKind, Unit

RASTER_DPI = 200


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
    """A PDF draws `1 1/4` as three words. One dimension is one phrase, so join across small gaps."""
    groups: list[list[tuple[str, float, float, float, float]]] = []
    for char in chars:
        if groups and _joins(groups[-1][-1], char):
            groups[-1].append(char)
        else:
            groups.append([char])
    phrases = []
    for group in groups:
        text = "".join(item[0] for item in group)
        x0 = min(item[1] for item in group)
        y0 = min(item[2] for item in group)
        x1 = max(item[3] for item in group)
        y1 = max(item[4] for item in group)
        phrases.append((text, (x0, y0, x1, y1)))
    return phrases


def _joins(previous: tuple[str, float, float, float, float], char: tuple[str, float, float, float, float]) -> bool:
    _pc, _pl, _pb, pr, pt = previous
    _cc, cl, cb, _cr, ct = char
    height = min(pt - _pb, ct - cb) or 1.0
    if min(pt, ct) - max(_pb, cb) < 0.6 * height:
        return False
    gap = cl - pr
    return -height <= gap <= 0.9 * height


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
