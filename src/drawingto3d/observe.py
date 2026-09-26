"""Family-independent observations from one drawing page.

Every vector subpath and every printed phrase becomes a record with an id, the frame it was
measured in, a bounding box and the method that produced it. Nothing here names a part family,
decides what a shape means, or requires a particular layout: the plate recognizer is one
consumer of these records, and a part nobody has seen yet is another.

What this first slice does not do, and says so in the record it writes:

- raster sheets are read by `raster.py` (CV strokes and circles, tesseract OCR phrases), whose
  record carries its own limits — no source paths, no arcs, no anchors yet;
- curve segments are recorded as skipped — this pdfium binding exposes a bezier's end point but
  no control points, so a curve cannot be rebuilt faithfully, and inventing a polyline for it
  would be a guess dressed as a measurement;
- dimensions are not yet bound to the geometry their arrows touch (no anchors, no view split):
  the text records carry the number, its unit, its count and the characters it came from, and
  the binding step is the next slice.
"""

from __future__ import annotations

from ctypes import byref, c_float
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from pydantic import BaseModel, Field

from drawingto3d.ingest import (
    RASTER_DPI,
    load_page,
    parse_dimension_unit,
    split_count,
    text_groups,
    upright_placement,
)
from drawingto3d.plan import source_hash
from drawingto3d.schema import BBox, Page


class Unsupported(ValueError):
    """The drawing cannot be observed yet; the message says why, not that it is wrong."""


@dataclass(frozen=True)
class VectorPath:
    """One subpath of one vector object, in the rendered page frame (pixels, top-left, y down)."""

    object_index: int
    path_index: int
    points: np.ndarray
    closed: bool


@dataclass(frozen=True)
class SkippedObject:
    object_index: int
    curves: int
    reason: str


def _rounded(value: float) -> float:
    return float(round(value, 2))


def _bbox(points: np.ndarray) -> BBox:
    low, high = points.min(axis=0), points.max(axis=0)
    return BBox(x=_rounded(low[0]), y=_rounded(low[1]), w=_rounded(high[0] - low[0]), h=_rounded(high[1] - low[1]))


def vector_paths(page: Page) -> tuple[list[VectorPath], list[SkippedObject]]:
    """Every line-segment subpath of the page's top-level vector objects.

    Points are in rendered raster pixels (top-left origin, y down, 200 dpi), the same frame the
    text boxes sit in once placed, so a later reader can compare geometry and numbers directly.
    An object holding a curve segment is skipped whole and recorded with its count: a partial
    outline that looks complete is worse than a named hole in the record.
    """
    paths: list[VectorPath] = []
    skipped: list[SkippedObject] = []
    with pdfium.PdfDocument(page.path) as document:
        pdf_page = document[0]
        if pdf_page.get_rotation() != 0:
            raise Unsupported("döndürülmüş sayfa: gözlem katmanı dönmeyi henüz çözmüyor")
        width, height = pdf_page.get_size()
        sx, sy = page.width / width, page.height / height
        for object_index, obj in enumerate(pdf_page.get_objects(max_depth=1)):
            if obj.type != raw.FPDF_PAGEOBJ_PATH:
                continue
            matrix = obj.get_matrix()
            object_paths: list[VectorPath] = []
            points: list[tuple[float, float]] = []
            closed = False
            curves = 0
            broken = False
            for index in range(raw.FPDFPath_CountSegments(obj)):
                segment = raw.FPDFPath_GetPathSegment(obj, index)
                kind = raw.FPDFPathSegment_GetType(segment)
                if kind == raw.FPDF_SEGMENT_BEZIERTO:
                    curves += 1
                    continue
                if kind not in (raw.FPDF_SEGMENT_MOVETO, raw.FPDF_SEGMENT_LINETO):
                    broken = True
                    break
                if kind == raw.FPDF_SEGMENT_MOVETO and points:
                    object_paths.append(VectorPath(object_index, len(object_paths), np.array(points), closed))
                    points = []
                    closed = False
                x, y = c_float(), c_float()
                if not raw.FPDFPathSegment_GetPoint(segment, byref(x), byref(y)):
                    broken = True
                    break
                px, py = matrix.on_point(x.value, y.value)
                points.append((px * sx, (height - py) * sy))
                if raw.FPDFPathSegment_GetClose(segment) and points:
                    closed = True
                    points.append(points[0])
            if points:
                object_paths.append(VectorPath(object_index, len(object_paths), np.array(points), closed))
            if curves:
                skipped.append(SkippedObject(object_index, curves,
                                             "curve segments: control points are not exposed by this PDF binding"))
                continue
            if broken:
                skipped.append(SkippedObject(object_index, 0, "unreadable path segment"))
                continue
            paths.extend(object_paths)
    return paths, skipped


def vector_groups(page: Page) -> list[list[np.ndarray]]:
    """Subpaths grouped by PDF object, for consumers that read object groups (the plate recognizer)."""
    try:
        paths, _skipped = vector_paths(page)
    except Unsupported:
        return []
    groups: dict[int, list[np.ndarray]] = {}
    for path in paths:
        groups.setdefault(path.object_index, []).append(path.points)
    return list(groups.values())


def _fit_circle(points: np.ndarray) -> tuple[float, float, float, float] | None:
    """Least-squares circle through the points: (cx, cy, r, worst deviation in px), or None.

    The thresholds keep a polyline from being called a circle: the deviation is measured against
    the sheet's own drawn size, and tiny specks (under three pixels of radius) are left alone.
    """
    if len(points) < 8:
        return None
    a = np.column_stack((2 * points[:, 0], 2 * points[:, 1], np.ones(len(points))))
    cx, cy, c = np.linalg.lstsq(a, (points**2).sum(axis=1), rcond=None)[0]
    radius2 = c + cx**2 + cy**2
    if radius2 <= 0:
        return None
    radius = float(np.sqrt(radius2))
    if radius < 3.0:
        return None
    deviations = np.linalg.norm(points - (cx, cy), axis=1)
    worst = float(np.max(np.abs(deviations - radius)))
    if worst > max(0.6, radius * 0.005):
        return None
    return float(cx), float(cy), radius, worst


def _sweep_degrees(points: np.ndarray, centre: tuple[float, float]) -> tuple[float, float]:
    """Start and end angle of the drawn run, degrees, unwrapped so a sweep can pass 180."""
    angles = np.unwrap(np.arctan2(points[:, 1] - centre[1], points[:, 0] - centre[0]))
    return float(np.degrees(angles[0])), float(np.degrees(angles[-1]))


class Primitive(BaseModel):
    """A fitted shape: what the path looks like, with the fit's own residual kept."""

    id: str
    path_id: str
    kind: Literal["line", "circle", "arc"]
    start: list[float] | None = None
    end: list[float] | None = None
    centre: list[float] | None = None
    radius: float | None = None
    start_degrees: float | None = None
    end_degrees: float | None = None
    max_residual_px: float | None = None
    coverage: float | None = None
    method: str = "least-squares-fit"


class PathObservation(BaseModel):
    """One subpath exactly as drawn: the points are the measurement, the id is the citation."""

    id: str
    object_index: int
    path_index: int
    closed: bool
    bbox: BBox
    points: list[list[float]]
    method: str = "pdf-vector"


class TextObservation(BaseModel):
    """One printed phrase: the raw string, and what the shared reader makes of it."""

    id: str
    text: str
    value: float | None = None
    unit: Literal["mm", "in"] = "mm"
    kind: str = "text"
    count: int = 1
    bbox: BBox
    char_range: list[int] = Field(default_factory=list)
    method: str = "pdf-text"
    confidence: float | None = None


class SourceRef(BaseModel):
    ref: str
    sha256: str
    page: int = 0
    page_size_pt: list[float] | None = None
    rotation: int = 0


class Frame(BaseModel):
    width: int
    height: int
    dpi: float | None = RASTER_DPI
    origin: str = "top-left"
    y_axis: str = "down"
    detail: str = "the page rendered at 200 dpi from PDF points; text boxes placed on the sheet's ink"


class Skipped(BaseModel):
    object_index: int
    curves: int = 0
    reason: str


class Observations(BaseModel):
    version: int = 1
    source: SourceRef
    frame: Frame
    text_placement: Literal["mirrored", "as-is"]
    paths: list[PathObservation] = Field(default_factory=list)
    primitives: list[Primitive] = Field(default_factory=list)
    texts: list[TextObservation] = Field(default_factory=list)
    skipped: list[Skipped] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _primitive(path_id: str, path: VectorPath) -> Primitive | None:
    """The fitted shape of a path, or None when the honest answer is 'a polyline'."""
    points = path.points
    if len(points) == 2 and not path.closed:
        start = [float(value) for value in points[0]]
        end = [float(value) for value in points[1]]
        return Primitive(id="", path_id=path_id, kind="line",
                         start=[_rounded(start[0]), _rounded(start[1])],
                         end=[_rounded(end[0]), _rounded(end[1])], method="two-point")
    fit = _fit_circle(points)
    if fit is None:
        return None
    cx, cy, radius, worst = fit
    start_degrees, end_degrees = _sweep_degrees(points, (cx, cy))
    sweep = end_degrees - start_degrees
    if path.closed or abs(sweep) >= 355:
        kind: Literal["circle", "arc"] = "circle"
    elif 5 <= abs(sweep) < 355:
        kind = "arc"
    else:
        return None
    return Primitive(id="", path_id=path_id, kind=kind,
                     centre=[_rounded(cx), _rounded(cy)], radius=_rounded(radius),
                     start_degrees=_rounded(start_degrees), end_degrees=_rounded(end_degrees),
                     max_residual_px=_rounded(worst))


def observe(path: str | Path, page_index: int = 0) -> Observations:
    """Read one drawing page into family-independent observations.

    Vector PDFs only for now; a raster sheet raises `Unsupported` with the reason. The frame is the
    rendered page (200 dpi), and the text layer's own frame is measured against the sheet's ink, with
    the winning placement recorded by name.
    """
    drawing = Path(path)
    if page_index != 0:
        raise Unsupported("gözlem katmanı şimdilik yalnız ilk sayfayı okuyor")
    if drawing.suffix.lower() != ".pdf":
        from drawingto3d.raster import RASTER_SUFFIXES, observe_raster
        if drawing.suffix.lower() in RASTER_SUFFIXES:
            return observe_raster(drawing)
        raise Unsupported(f"desteklenmeyen dosya türü: {drawing.suffix or '(yok)'}")

    loaded = load_page(drawing)
    paths, skipped = vector_paths(loaded)
    with pdfium.PdfDocument(str(drawing)) as document:
        pdf_page = document[0]
        rotation = int(pdf_page.get_rotation())
        pt_width, pt_height = (float(value) for value in pdf_page.get_size())
        groups = text_groups(pdf_page)

    gray = cv2.imdecode(np.frombuffer(loaded.image_png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    numeric = [(text, box) for text, box, _indices in groups if parse_dimension_unit(text)[1] is not None]
    vote = numeric or [(text, box) for text, box, _indices in groups]
    placement_name, place = upright_placement(vote, gray, RASTER_DPI / 72.0, pt_height)

    observations = Observations(
        source=SourceRef(ref=str(drawing), sha256=source_hash(drawing), page=0,
                         page_size_pt=[_rounded(pt_width), _rounded(pt_height)], rotation=rotation),
        frame=Frame(width=loaded.width, height=loaded.height),
        text_placement=placement_name if placement_name in ("mirrored", "as-is") else "mirrored",
    )
    path_ids: list[str] = []
    for index, vector in enumerate(paths):
        path_id = f"p{index}"
        path_ids.append(path_id)
        observations.paths.append(PathObservation(
            id=path_id, object_index=vector.object_index, path_index=vector.path_index,
            closed=bool(vector.closed), bbox=_bbox(vector.points),
            points=[[_rounded(x), _rounded(y)] for x, y in vector.points],
        ))
        primitive = _primitive(path_id, vector)
        if primitive is not None:
            primitive.id = f"g{len(observations.primitives)}"
            observations.primitives.append(primitive)
    for index, (text, box, char_range) in enumerate(groups):
        kind, value, unit = parse_dimension_unit(text)
        x, y, w, h = place(box, RASTER_DPI / 72.0)
        observations.texts.append(TextObservation(
            id=f"t{index}", text=text, value=value, unit=unit, kind=kind.value,
            count=split_count(text)[0],
            bbox=BBox(x=_rounded(x), y=_rounded(y), w=_rounded(w), h=_rounded(h)),
            char_range=list(char_range),
        ))
    observations.skipped = [Skipped(object_index=item.object_index, curves=item.curves, reason=item.reason)
                            for item in skipped]
    observations.notes = [
        "Ölçü oklarının bağlandığı geometri (bağlama) bir sonraki dilimde.",
        "Görünüş ayrımı (plan/kesit/izometrik) bir sonraki dilimde.",
        "Raster paftalar ayrı gözlemciden geçiyor (`raster.py`: CV çizgi/daire + OCR ifade).",
    ]
    return observations
