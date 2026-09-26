"""Ask one closed question per printed dimension: which feature does this number size?

The sheet is cut into a square around each dimension text and the vision model picks
one word from a short list. Anything outside the list becomes `unknown`; the user
corrects roles in the table. No millimetre is invented here.
"""

from __future__ import annotations

import re
from typing import Protocol

import cv2
import numpy as np

from drawingto3d.ingest import split_count
from drawingto3d.perceive import perceive
from drawingto3d.schema import MM_PER_INCH, ROLES, DimensionRecord, Page, Span, SpanKind

DIAMETER_ROLES = ("outer_diameter", "inner_diameter", "hole_diameter")
RADIUS_ROLES = ("bend_radius", "corner_radius", "fillet")
LENGTH_ROLES = ("edge", "thickness", "hole_spacing")
# A callout that names a through-hole or a thread is a diameter even when the `Ø` itself is not typed: on a
# vector sheet the mark is a drawn path that never reaches the text layer, so `6,80 THRU ALL` arrives bare and
# the length family was the only list offered - the reader then had to answer `hole_spacing`, a wrong role no
# later stage can repair. The note is the part of a callout that survives as text, so it decides the family.
HOLE_NOTES = ("THRU", "TAP", "CBORE", "C'BORE", "CSK", "6H", "PILOT")


class RoleReader(Protocol):
    def ask(self, image_png: bytes, prompt: str) -> str: ...


def crop_for_span(
    page: Page,
    span: Span,
    pad: float = 6.0,
    min_size: int = 220,
    mark: bool = True,
    reach: float = 0.25,
    limit: int = 1000,
) -> bytes:
    """The number *and what it measures*: its own line to both ends, plus a margin past them.

    The question asked about a number is what it measures, and a crop of the number alone cannot answer it. The
    plate's `100,00` is its corner holes' centre spacing: the dimension line's ends sit 10.6 mm *inside* the
    plate's drawn edge and the extension lines run from the holes up to them. A crop of the number showed none of
    that, so the reader answered `edge` for a hole pattern, `edge` for a `Ø50` bore and `thickness` for an 8 mm
    pocket depth. `Span.anchors` are the two ends of the number's own line - a dimension line's arrow tips, or a
    leader's tip and the text it carries - so this box spans them and then reaches `reach` of the measured length
    past each end, which is where the extension lines run to the features. The number itself is boxed in red, so
    the question still names its subject.
    """
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("sayfa resmi çözülemedi")
    height, width = image.shape[:2]
    xs = [span.bbox.x, span.bbox.x + span.bbox.w]
    ys = [span.bbox.y, span.bbox.y + span.bbox.h]
    for ax, ay in span.anchors:
        xs.append(ax)
        ys.append(ay)
    measured = max(max(xs) - min(xs), max(ys) - min(ys))
    margin = max(reach * measured, pad * max(span.bbox.w, span.bbox.h), min_size / 2)
    x0 = int(max(0, min(xs) - margin))
    y0 = int(max(0, min(ys) - margin))
    x1 = int(min(width, max(xs) + margin))
    y1 = int(min(height, max(ys) + margin))
    crop = image[y0:y1, x0:x1].copy()
    if crop.size == 0:
        raise ValueError("kesit boş")
    if mark:
        left = int(span.bbox.x - x0) - 3
        top = int(span.bbox.y - y0) - 3
        right = int(span.bbox.x + span.bbox.w - x0) + 3
        bottom = int(span.bbox.y + span.bbox.h - y0) + 3
        cv2.rectangle(crop, (left, top), (right, bottom), (0, 0, 255), 1)
    long_side = max(crop.shape[:2])
    if long_side > limit:
        factor = limit / long_side
        crop = cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".png", crop)
    if not ok:
        raise ValueError("kesit kodlanamadı")
    return encoded.tobytes()


def role_choices(text: str, kind: SpanKind | None = None) -> tuple[str, ...]:
    """The prefix already fixes the family: Ø is a diameter, R a radius, C a chamfer, ° an angle."""
    _count, body = split_count(text)
    if "°" in body or kind == SpanKind.angle:
        return ("angle",)
    if body[:1].upper() == "C" and body[1:2].isdigit():
        return ("chamfer",)
    if any(mark in body for mark in ("Ø", "⌀", "Φ")) or kind == SpanKind.diameter:
        return DIAMETER_ROLES
    if (body[:1].upper() == "R" and not body.lower().startswith("ra")) or kind == SpanKind.radius:
        return RADIUS_ROLES
    if any(note in body.upper() for note in HOLE_NOTES):
        return DIAMETER_ROLES
    return LENGTH_ROLES


ROLE_HINTS = {
    "edge": "the full length or width of a plate, or the length of a straight tube or arm",
    "thickness": "the thin depth of a plate or flange, measured across its narrow side",
    "hole_spacing": "the distance between the centres of two holes",
    "outer_diameter": "the outside diameter of a tube or cylinder",
    "inner_diameter": "the bore inside a tube",
    "hole_diameter": "a bolt hole or its counterbore",
    "bend_radius": "the centreline arc of a bent tube or arm",
    "corner_radius": "the rounded corner of a plate outline",
    "fillet": "a small rounded transition between two faces",
    "chamfer": "a bevelled edge",
    "angle": "an angle between two directions",
}


def role_prompt(text: str, choices: tuple[str, ...]) -> str:
    options = "\n".join(f"- {choice}: {ROLE_HINTS.get(choice, choice)}" for choice in choices)
    words = ", ".join(choices)
    return (
        "This is a square cut from a mechanical drawing. Look at the dimension text inside the red box; it reads "
        f"'{text}'. Follow its dimension line to the two points it spans and decide what it measures:\n{options}\n"
        f"Reply with exactly one word from this list and nothing else: {words}."
    )


def parse_role(answer: str, choices: tuple[str, ...]) -> str:
    """Take the first listed word found in the answer; anything else is unknown."""
    normalised = re.sub(r"[^a-z_]+", "_", answer.strip().lower().replace("-", "_").replace(" ", "_"))
    for choice in sorted(choices, key=len, reverse=True):
        if choice in normalised and choice in ROLES:
            return choice
    return "unknown"


def ask_role(reader: RoleReader, image_png: bytes, text: str, kind: SpanKind | None = None) -> str:
    choices = role_choices(text, kind)
    if len(choices) == 1:
        return choices[0]
    try:
        answer = reader.ask(image_png, role_prompt(text, choices))
    except Exception:  # noqa: BLE001 - one bad answer must not stop the sheet
        return "unknown"
    return parse_role(answer, choices)


def read_records(page: Page, reader: RoleReader, progress=None) -> list[DimensionRecord]:
    """OCR spans become records; each gets a role from one closed question. Spans are kept on the page."""
    _primitives, spans = perceive(page)
    page.spans = spans
    usable = [span for span in spans if span.value is not None]
    records: list[DimensionRecord] = []
    asked: dict[tuple[float, str, str], str] = {}
    for index, span in enumerate(usable, start=1):
        if progress is not None:
            progress(f"Ölçüler okunuyor ({index}/{len(usable)})", f"{span.text} için rol soruluyor.")
        count, _body = split_count(span.text)
        key = (float(span.value), span.kind.value, span.view_id or "")
        if span.view_id and key in asked:
            role = asked[key]
        else:
            role = ask_role(reader, crop_for_span(page, span), span.text, span.kind)
            if span.view_id:
                asked[key] = role
        records.append(
            DimensionRecord(
                span_id=span.id,
                text=span.text,
                value=_millimetres(span),
                printed_unit=span.unit,
                role=role,  # type: ignore[arg-type]
                count=count,
                source=span.source,
                view_id=span.view_id,
            )
        )
    return records


def _millimetres(span: Span) -> float:
    """The sheet may print inches; the record is always millimetres."""
    value = float(span.value)
    return value if span.unit == "mm" else value * MM_PER_INCH
