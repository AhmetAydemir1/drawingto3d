"""Turn a page into a feature graph, or into questions. No silent millimetres."""

from __future__ import annotations

import cv2
import numpy as np

from drawingto3d.legacy.contours import view_islands, view_outline
from drawingto3d.schema import (
    Audit,
    AuditEntry,
    Binding,
    Contour,
    FeatureGraph,
    HoleSpec,
    Page,
    PocketSpec,
    Point2,
    PrimitiveKind,
    Question,
    Source,
    Span,
    View,
    ViewKind,
)

def questions_for(bindings: list[Binding], spans: list[Span]) -> list[Question]:
    by_role: dict[str, list[Binding]] = {}
    for binding in bindings:
        by_role.setdefault(binding.role, []).append(binding)
    span_by_id = {span.id: span for span in spans}
    questions: list[Question] = []

    for binding in bindings:
        span = span_by_id.get(binding.span_id)
        if span is None or span.value is None or abs(span.value - binding.value) > 1e-6:
            questions.append(
                Question(
                    role=binding.role,
                    reason="değer bir OCR/PDF span'ına dayanmıyor",
                    span_ids=[binding.span_id],
                )
            )
        if not binding.agrees_with_geometry:
            questions.append(
                Question(
                    role=binding.role,
                    reason="ok ilişkisi ile rol çelişiyor",
                    span_ids=[binding.span_id],
                )
            )

    for role, group in by_role.items():
        values = {round(item.value, 4) for item in group}
        if len(values) > 1 or len(group) > 1:
            questions.append(
                Question(
                    role=role,
                    reason="aynı role birden fazla sayı bağlandı",
                    span_ids=[item.span_id for item in group],
                )
            )

    return _unique(questions)


def graph_from_bindings(
    bindings: list[Binding], spans: list[Span], page: Page
) -> tuple[FeatureGraph | None, list[Question]]:
    questions = questions_for(bindings, spans)
    lengths = [item for item in bindings if item.kind == "length"]
    if len(lengths) != 1:
        questions.append(Question(role="length", reason="katıyı ölçekleyecek tek bir boy ölçüsü yok"))
    if questions:
        return None, _unique(questions)
    length = lengths[0]
    span_by_id = {span.id: span for span in spans}
    length_span = span_by_id[length.span_id]
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    solid_views = [view for view in page.views if view.used_for_solid and view.kind != ViewKind.isometric]
    section = next((view for view in solid_views if view.kind == ViewKind.section), None)
    profile = next((view for view in solid_views if view.kind == ViewKind.front), None)
    if profile is None:
        profile = next((view for view in solid_views if view.kind == ViewKind.plan), None)
    if profile is None:
        return None, [Question(role="contour", reason="kesit ve plan konturu aynı sayfada yok")]
    profile_px = view_outline(image, profile, spans)
    if profile_px is None:
        return None, [Question(role="contour", reason="kontur kapanmadı")]
    thickness = next((item for item in bindings if item.kind == "height"), None)
    if thickness is not None:
        if not _span_in_view(length_span, profile):
            return None, [Question(role="length", reason="ölçek kurulamadı")]
        profile_scale = _extent_scale(profile_px, length_span, length.value)
        if profile_scale is None:
            return None, [Question(role="length", reason="ölçek kurulamadı")]
        holes = _diameter_holes(bindings, span_by_id, page, profile, profile_scale, profile_px)
        _questions, pockets = _pockets(view_islands(image, profile, spans), bindings, profile_px, profile_scale)
        graph = FeatureGraph(
            strategy="extrude",
            plan=_contour("plan", profile_px, profile_scale, vertical=False),
            thickness=thickness.value,
            holes=holes,
            pockets=pockets,
            bindings=bindings,
            datum_ok=True,
        )
        _apply_radii(graph, bindings, span_by_id, page, profile, section or profile, profile_px, profile_px, profile_scale)
        return graph, _questions
    if section is None:
        return None, [Question(role="contour", reason="kesit ve plan konturu aynı sayfada yok")]
    section_px = view_outline(image, section, spans)
    if section_px is None:
        return None, [Question(role="contour", reason="kontur kapanmadı")]
    host_px = section_px if _span_in_view(length_span, section) else profile_px
    sheet_scale = _extent_scale(host_px, length_span, length.value)
    if sheet_scale is None:
        return None, [Question(role="length", reason="ölçek kurulamadı")]
    holes = _diameter_holes(bindings, span_by_id, page, profile, sheet_scale, profile_px)
    graph = FeatureGraph(
        strategy="plan_section",
        plan=_contour("plan", profile_px, sheet_scale, vertical=False),
        section=_contour("section", section_px, sheet_scale, vertical=True),
        holes=holes,
        bindings=bindings,
        datum_ok=True,
    )
    _apply_radii(graph, bindings, span_by_id, page, profile, section, profile_px, section_px, sheet_scale)
    return graph, []


def _extent_scale(pixels: np.ndarray, span: Span, value: float) -> float | None:
    horizontal = span.bbox.w >= span.bbox.h
    extent = float(pixels[:, 0].max() - pixels[:, 0].min()) if horizontal else float(pixels[:, 1].max() - pixels[:, 1].min())
    if extent < 1.0:
        return None
    return value / extent


def _span_in_view(span: Span, view: View) -> bool:
    if span.view_id == view.id:
        return True
    cx = span.bbox.x + span.bbox.w / 2
    cy = span.bbox.y + span.bbox.h / 2
    box = view.bbox
    return box.x <= cx <= box.x + box.w and box.y <= cy <= box.y + box.h


def _pockets(islands, bindings, pixels, scale: float) -> tuple[list[Question], list[PocketSpec]]:
    questions: list[Question] = []
    pockets: list[PocketSpec] = []
    depth = next((item for item in bindings if item.kind == "depth"), None)
    for island in islands:
        if depth is None:
            questions.append(Question(role="depth", reason="cep derinliği bir span'a dayanmıyor"))
            continue
        contour = _contour("pocket", island, scale, vertical=False)
        pockets.append(PocketSpec(points=contour.points, depth=depth.value, span_id=depth.span_id))
    return questions, pockets


def _contour(name: str, pixels: np.ndarray, scale: float, vertical: bool) -> Contour:
    origin_x = float(pixels[:, 0].min())
    if vertical:
        origin_y = float(pixels[:, 1].max())
        points = [Point2(x=(px - origin_x) * scale, y=(origin_y - py) * scale) for px, py in pixels]
    else:
        mid_y = float(pixels[:, 1].mean())
        points = [Point2(x=(px - origin_x) * scale, y=(mid_y - py) * scale) for px, py in pixels]
    return Contour(name=name, points=points)


def _diameter_holes(bindings, span_by_id, page: Page, plan: View, scale: float, plan_px: np.ndarray) -> list[HoleSpec]:
    origin_x = float(plan_px[:, 0].min())
    mid_y = float(plan_px[:, 1].mean())
    circles = [item for item in page.primitives if item.kind == PrimitiveKind.circle and item.radius]
    holes: list[HoleSpec] = []
    for binding in bindings:
        if binding.kind != "diameter":
            continue
        span = span_by_id.get(binding.span_id)
        if span is None:
            continue
        target = (span.bbox.x + span.bbox.w / 2.0, span.bbox.y + span.bbox.h / 2.0)
        inside = [
            circle
            for circle in circles
            if plan.bbox.x <= circle.points[0][0] <= plan.bbox.x + plan.bbox.w
            and plan.bbox.y <= circle.points[0][1] <= plan.bbox.y + plan.bbox.h
        ]
        if not inside:
            continue
        circle = min(inside, key=lambda item: (item.points[0][0] - target[0]) ** 2 + (item.points[0][1] - target[1]) ** 2)
        cx, cy = circle.points[0]
        holes.append(
            HoleSpec(
                cx=(cx - origin_x) * scale,
                cy=(mid_y - cy) * scale,
                diameter=binding.value,
                span_id=binding.span_id,
            )
        )
    return holes


def _apply_radii(graph, bindings, span_by_id, page: Page, plan: View, section: View, plan_px, section_px, scale: float) -> None:
    """Pull contour points that already lie on a nearby arc out to the radius span."""
    import math

    circles = [item for item in page.primitives if item.kind == PrimitiveKind.circle and item.radius]
    for binding in bindings:
        if binding.kind != "radius":
            continue
        span = span_by_id.get(binding.span_id)
        if span is None or not circles:
            continue
        target = (span.bbox.x + span.bbox.w / 2.0, span.bbox.y + span.bbox.h / 2.0)
        circle = min(circles, key=lambda item: (item.points[0][0] - target[0]) ** 2 + (item.points[0][1] - target[1]) ** 2)
        on_section = section.bbox.x <= circle.points[0][0] <= section.bbox.x + section.bbox.w and section.bbox.y <= circle.points[0][1] <= section.bbox.y + section.bbox.h
        contour = graph.section if on_section else graph.plan
        pixels = section_px if on_section else plan_px
        if contour is None:
            continue
        cx, cy = _to_mm(circle.points[0][0], circle.points[0][1], pixels, scale, vertical=on_section)
        band = float(circle.radius) * scale
        moved = False
        for point in contour.points:
            dx, dy = point.x - cx, point.y - cy
            dist = math.hypot(dx, dy)
            if dist < 1e-6 or abs(dist - band) / max(band, 1e-6) > 0.45:
                continue
            point.x = cx + dx / dist * binding.value
            point.y = cy + dy / dist * binding.value
            moved = True
        if moved:
            contour.arcs.append({"kind": "radius", "value": binding.value, "span_id": binding.span_id})


def _to_mm(px: float, py: float, pixels, scale: float, vertical: bool) -> tuple[float, float]:
    origin_x = float(pixels[:, 0].min())
    if vertical:
        origin_y = float(pixels[:, 1].max())
        return (px - origin_x) * scale, (origin_y - py) * scale
    mid_y = float(pixels[:, 1].mean())
    return (px - origin_x) * scale, (mid_y - py) * scale


def audit_from(bindings: list[Binding], spans: list[Span], questions: list[Question], accepted: bool) -> Audit:
    span_by_id = {span.id: span for span in spans}
    entries = []
    for binding in bindings:
        span = span_by_id.get(binding.span_id)
        entries.append(
            AuditEntry(
                role=binding.role,
                value=binding.value,
                source=span.source if span else Source.user,
                span_id=binding.span_id,
                text=span.text if span else "",
                kind=binding.kind,
            )
        )
    return Audit(entries=entries, questions=questions, accepted=accepted)


def _unique(questions: list[Question]) -> list[Question]:
    seen: set[tuple[str, str]] = set()
    out: list[Question] = []
    for question in questions:
        key = (question.role, question.reason)
        if key in seen:
            continue
        seen.add(key)
        out.append(question)
    return out
