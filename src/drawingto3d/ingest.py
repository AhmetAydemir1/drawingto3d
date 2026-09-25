"""Load a PNG, JPG, or one PDF page. Vector PDF text is read from the file."""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from drawingto3d.schema import BBox, Page, Source, Span, SpanKind

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
    spans: list[Span] = []
    buffer = ""
    box: list[float] | None = None
    for index in range(count):
        char = textpage.get_text_range(index, 1)
        rect = textpage.get_charbox(index)
        if char.isspace():
            _flush(spans, buffer, box, scale)
            buffer = ""
            box = None
            continue
        buffer += char
        left, bottom, right, top = rect
        if box is None:
            box = [left, bottom, right, top]
        else:
            box = [min(box[0], left), min(box[1], bottom), max(box[2], right), max(box[3], top)]
    _flush(spans, buffer, box, scale)
    return spans


def _flush(spans: list[Span], text: str, box: list[float] | None, scale: float) -> None:
    text = text.strip()
    if not text or box is None:
        return
    kind, value = parse_dimension(text)
    if value is None and kind == SpanKind.text:
        return
    x0, y0, x1, y1 = box
    spans.append(
        Span(
            id=f"pdf-{len(spans)}",
            text=text,
            value=value,
            kind=kind,
            bbox=BBox(x=x0 * scale, y=y0 * scale, w=(x1 - x0) * scale, h=(y1 - y0) * scale),
            source=Source.pdf_text,
        )
    )


_COUNT_PREFIX = re.compile(r"^\s*(\d{1,2})\s*(?:[xX×]\s*(\d{1,2}))?\s*(?:[-–]\s*|[xX×]\s*)(?=[ØÖ⌀ΦRrCc\d])")


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
    _count, text = split_count(text)
    raw = text.replace(" ", "").replace(",", ".").replace("Ø", "").replace("⌀", "").replace("Φ", "")
    kind = SpanKind.linear
    if text.startswith(("R", "r")) and not text.lower().startswith("ra"):
        kind = SpanKind.radius
        raw = raw[1:]
    elif "Ø" in text or "⌀" in text or text.lower().startswith("o") and raw[:1].isdigit():
        kind = SpanKind.diameter
    if "°" in text:
        kind = SpanKind.angle
        raw = raw.replace("°", "")
    raw = raw.replace("°", "")
    number = ""
    for char in raw:
        if char.isdigit() or (char == "." and "." not in number):
            number += char
        elif number:
            break
    if not number or number == ".":
        return SpanKind.text, None
    return kind, float(number)
