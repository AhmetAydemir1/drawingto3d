"""Intermediate drawing model. Every millimetre cites a span or a user edit."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    linear = "linear"
    diameter = "diameter"
    radius = "radius"
    angle = "angle"
    text = "text"


class Source(str, Enum):
    ocr = "ocr"
    pdf_text = "pdf_text"
    user = "user"


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Span(BaseModel):
    id: str
    text: str
    value: float | None = None
    kind: SpanKind = SpanKind.text
    bbox: BBox
    view_id: str | None = None
    source: Source = Source.ocr


class ViewKind(str, Enum):
    plan = "plan"
    section = "section"
    front = "front"
    side = "side"
    isometric = "isometric"
    unknown = "unknown"


class View(BaseModel):
    id: str
    kind: ViewKind
    bbox: BBox
    section_label: str | None = None
    used_for_solid: bool = True


class PrimitiveKind(str, Enum):
    line = "line"
    circle = "circle"
    arc = "arc"
    hatch = "hatch"
    axis = "axis"
    arrow = "arrow"


class Primitive(BaseModel):
    id: str
    kind: PrimitiveKind
    view_id: str | None = None
    points: list[tuple[float, float]] = Field(default_factory=list)
    radius: float | None = None


class Binding(BaseModel):
    role: str
    span_id: str
    value: float
    kind: Literal["length", "diameter", "radius", "angle", "height", "depth", "other"] = "other"
    geometry_id: str | None = None
    note: str = ""
    agrees_with_geometry: bool = True


class Question(BaseModel):
    role: str
    reason: str
    span_ids: list[str] = Field(default_factory=list)


class Point2(BaseModel):
    x: float
    y: float


class Contour(BaseModel):
    """Closed profile in millimetres. Plan uses XY. Section uses XZ stored as x,y."""

    name: str
    points: list[Point2]
    arcs: list[dict] = Field(default_factory=list)


class HoleSpec(BaseModel):
    cx: float
    cy: float
    diameter: float
    depth: float | None = None
    span_id: str | None = None


class HexPocket(BaseModel):
    cx: float
    cy: float
    across_flats: float
    depth: float
    span_id: str | None = None


class PocketSpec(BaseModel):
    """Closed inner island. Depth is a read span, never a guessed millimetre."""

    points: list[Point2]
    depth: float
    span_id: str | None = None


class FeatureGraph(BaseModel):
    strategy: Literal["plan_section", "extrude", "revolve"] = "plan_section"
    unit: Literal["mm"] = "mm"
    plan: Contour | None = None
    section: Contour | None = None
    thickness: float | None = None
    holes: list[HoleSpec] = Field(default_factory=list)
    pockets: list[PocketSpec] = Field(default_factory=list)
    hex_pocket: HexPocket | None = None
    bindings: list[Binding] = Field(default_factory=list)
    datum_ok: bool = False


Role = Literal[
    "edge",
    "thickness",
    "outer_diameter",
    "inner_diameter",
    "bend_radius",
    "hole_diameter",
    "hole_spacing",
    "corner_radius",
    "fillet",
    "chamfer",
    "angle",
    "unknown",
]

ROLES: tuple[str, ...] = (
    "edge",
    "thickness",
    "outer_diameter",
    "inner_diameter",
    "bend_radius",
    "hole_diameter",
    "hole_spacing",
    "corner_radius",
    "fillet",
    "chamfer",
    "angle",
    "unknown",
)


class DimensionRecord(BaseModel):
    """One printed dimension and the feature it sizes. The role may be corrected by the user."""

    span_id: str
    text: str
    value: float
    unit: Literal["mm"] = "mm"
    role: Role = "unknown"
    count: int = 1
    source: Source = Source.ocr
    view_id: str | None = None


class AuditEntry(BaseModel):
    role: str
    value: float
    source: Source
    span_id: str | None = None
    text: str = ""
    kind: str = "other"


class Audit(BaseModel):
    unit: Literal["mm"] = "mm"
    entries: list[AuditEntry] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    accepted: bool = False


class Page(BaseModel):
    path: str
    width: int
    height: int
    image_png: bytes
    spans: list[Span] = Field(default_factory=list)
    views: list[View] = Field(default_factory=list)
    primitives: list[Primitive] = Field(default_factory=list)
    vector_text: bool = False


class ConvertResult(BaseModel):
    audit: Audit
    step_path: str | None = None
    stl_path: str | None = None
    questions: list[Question] = Field(default_factory=list)
    graph: FeatureGraph | None = None
    page: Page | None = None
    records: list[DimensionRecord] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
