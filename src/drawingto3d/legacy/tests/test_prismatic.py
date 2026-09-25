"""L profile, a hole, and a pocket whose depth was not read."""

from pathlib import Path

import cv2
import numpy as np

from drawingto3d.schema import BBox, Binding, Page, Primitive, PrimitiveKind, Span, SpanKind, View, ViewKind
from drawingto3d.legacy.strategies import graph_from_bindings


def test_pocket_without_depth_blocks_step_and_keeps_the_l(tmp_path: Path):
    image = _l_sheet()
    path = tmp_path / "l.png"
    cv2.imwrite(str(path), image)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    view = View(id="front", kind=ViewKind.front, bbox=BBox(x=30, y=40, w=420, h=360))
    length = Span(id="len", text="120", value=120, kind=SpanKind.linear, bbox=BBox(x=80, y=330, w=180, h=16), view_id="front")
    diameter = Span(id="dia", text="10", value=10, kind=SpanKind.diameter, bbox=BBox(x=130, y=100, w=28, h=14), view_id="front")
    height = Span(id="thk", text="16", value=16, kind=SpanKind.linear, bbox=BBox(x=360, y=80, w=20, h=40), view_id="front")
    page = Page(
        path=str(path),
        width=image.shape[1],
        height=image.shape[0],
        image_png=encoded.tobytes(),
        spans=[length, diameter, height],
        views=[view],
        primitives=[
            Primitive(id="hole", kind=PrimitiveKind.circle, points=[(70.0, 120.0)], radius=12.0, view_id="front")
        ],
    )
    bindings = [
        Binding(role="boy", span_id="len", value=120, kind="length"),
        Binding(role="delik", span_id="dia", value=10, kind="diameter"),
        Binding(role="kalinlik", span_id="thk", value=16, kind="height"),
    ]
    graph, questions = graph_from_bindings(bindings, page.spans, page)
    assert graph is not None and graph.plan is not None
    assert any(item.reason == "cep derinliği bir span'a dayanmıyor" for item in questions)
    assert graph.holes and graph.holes[0].diameter == 10
    points = np.array([(point.x, point.y) for point in graph.plan.points], dtype=np.float32)
    hull = cv2.convexHull(points)
    assert cv2.contourArea(hull) > cv2.contourArea(points.reshape(-1, 1, 2)) + 1
    assert graph.pockets == []


def test_binder_sees_solid_views_one_at_a_time(tmp_path):
    from drawingto3d.legacy.pipeline import convert_drawing

    seen: list[bytes | None] = []

    class _Record:
        def bind(self, spans, image=None):
            seen.append(image)
            span = next((item for item in spans if item.value == 180), None)
            if span is None:
                return []
            return [Binding(role="toplam boy", span_id=span.id, value=span.value, kind="length")]

    result = convert_drawing("examples/solidworks-katc4b1-8-1024x729.jpg", tmp_path, binder=_Record())
    assert len(seen) >= 2
    full = result.page.image_png if result.page is not None else b""
    assert all(image is not None and len(image) < len(full) for image in seen)


def _l_sheet() -> np.ndarray:
    image = np.full((480, 520, 3), 255, np.uint8)
    leg = np.array([[50, 60], [110, 60], [110, 240], [340, 240], [340, 310], [50, 310]], np.int32)
    cv2.fillPoly(image, [leg], (0, 0, 0))
    cv2.rectangle(image, (150, 255), (230, 295), (255, 255, 255), thickness=-1)
    cv2.circle(image, (70, 120), 12, (255, 255, 255), thickness=-1)
    return image
