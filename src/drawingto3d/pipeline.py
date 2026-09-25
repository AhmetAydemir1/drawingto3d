"""PDF/PNG page to STEP. Unsourced or conflicting dimensions block the file."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from drawingto3d.bind import (
    OllamaBinder,
    SemanticBinder,
    UnavailableModel,
    validate_bindings,
)
from drawingto3d.ingest import load_page
from drawingto3d.perceive import perceive
from drawingto3d.schema import (
    BBox,
    Binding,
    ConvertResult,
    Question,
    Source,
    Span,
    SpanKind,
    ViewKind,
)
from drawingto3d.solid import build_part, measured_length, write_step, write_stl
from drawingto3d.strategies import audit_from, graph_from_bindings, questions_for
from drawingto3d.views import layout_conflict, segment_views


def convert_drawing(
    path: str | Path,
    out_dir: str | Path,
    answers: dict[str, float] | None = None,
    binder: SemanticBinder | None = None,
    use_model: bool = True,
    progress=None,
) -> ConvertResult:
    def tell(title: str, detail: str) -> None:
        if progress is not None:
            progress(title, detail)

    tell("Sayfa açılıyor", "Dosya okunuyor.")
    page = load_page(path)
    tell("Görünüşler ayrılıyor", "Paftadaki ön, üst, yan ve kesit kutuları aranıyor.")
    page.views = segment_views(page)
    solid = [view for view in page.views if view.used_for_solid]
    tell("Ölçü yazıları okunuyor", f"{len(solid)} görünüş var. Rakamlar taranıyor; büyük paftada bu adım uzun sürer.")
    primitives, spans = perceive(page)
    page.primitives = primitives
    page.spans = spans
    tell("Ölçüler okundu", f"{len(spans)} sayı bulundu.")
    # #region agent log
    from drawingto3d.bind import _dbg

    _dbg("pipeline.py:perceive", "views and spans", {"views": [{"id": view.id, "kind": view.kind.value, "used": view.used_for_solid, "bbox": view.bbox.model_dump()} for view in page.views], "spans": [{"id": span.id, "text": span.text, "value": span.value, "kind": span.kind.value, "view_id": span.view_id} for span in spans], "primitives": len(primitives)}, "A")
    # #endregion
    questions: list[Question] = []
    if layout_conflict(page.views):
        questions.append(Question(role="datum", reason="görünüş yerleşimi üçüncü açıya uymuyor"))
    if not _has_datum(page.views):
        questions.append(Question(role="datum", reason="plan ve kesit aynı sayfada ayrılmadı"))
    bindings = _bindings_from_views(page, spans, binder, use_model, questions, progress)
    bindings = validate_bindings(bindings, spans)
    if answers:
        questions = [question for question in questions if question.role != "model"]
        bindings = _merge_answers(bindings, spans, answers)
        page.spans = spans
    tell("Bağlar denetleniyor", "Her sayının okunmuş bir yazıya dayandığı kontrol ediliyor.")
    pending = questions_for(bindings, spans)
    questions.extend(pending)
    audit = audit_from(bindings, spans, questions, accepted=False)
    if questions:
        # #region agent log
        _dbg("pipeline.py:early", "stopped before solid", {"questions": [question.model_dump() for question in questions], "bindings": [item.model_dump() for item in bindings]}, "A")
        # #endregion
        tell("Durdu", questions[0].reason if questions else "Eksik ölçü var.")
        return ConvertResult(audit=audit, questions=questions, page=page)
    tell("Kontur kuruluyor", "Profil, delik ve cep kaynak ölçülerle eşleniyor.")
    graph, gate = graph_from_bindings(bindings, spans, page)
    if gate or graph is None:
        audit.questions.extend(gate)
        reason = gate[0].reason if gate else "Kontur kurulamadı."
        tell("Durdu", reason)
        return ConvertResult(audit=audit, questions=audit.questions, graph=graph, page=page)
    tell("Katı derleniyor", "Profil kalınlığı ve delikler işleniyor.")
    try:
        part = build_part(graph)
    except Exception:
        failed = [Question(role="contour", reason="kontur kapanmadı")]
        audit.questions.extend(failed)
        tell("Durdu", "Kontur kapanmadı.")
        return ConvertResult(audit=audit, questions=audit.questions, graph=graph, page=page)
    length_binding = next(item.value for item in bindings if item.kind == "length")
    if abs(measured_length(part) - length_binding) > 0.5:
        mismatch = [Question(role="length", reason="katının boyu kaynak ölçüyle uyuşmuyor")]
        audit.questions.extend(mismatch)
        tell("Durdu", mismatch[0].reason)
        return ConvertResult(audit=audit, questions=audit.questions, graph=graph, page=page)
    tell("STEP yazılıyor", "Katı diske yazılıyor.")
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    step_path = folder / "part.step"
    stl_path = folder / "part.stl"
    write_step(part, step_path)
    write_stl(part, stl_path)
    audit.accepted = True
    tell("STEP hazır", "Dosyayı indirebilirsin.")
    return ConvertResult(
        audit=audit,
        step_path=str(step_path),
        stl_path=str(stl_path),
        graph=graph,
        page=page,
    )


_VIEW_LABEL = {
    ViewKind.front: "Ön görünüş",
    ViewKind.plan: "Üst görünüş",
    ViewKind.side: "Yan görünüş",
    ViewKind.section: "Kesit",
}


def _has_datum(views) -> bool:
    kinds = {view.kind for view in views if view.used_for_solid}
    return ViewKind.section in kinds and (ViewKind.plan in kinds or ViewKind.front in kinds)


def _bindings_from_views(page, spans, binder, use_model, questions: list[Question], progress=None) -> list[Binding]:
    """One padded crop per solid view, in order. Isometric is not sent."""
    if not use_model:
        return []
    active = binder or OllamaBinder()
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    views = [view for view in page.views if view.used_for_solid and view.kind != ViewKind.isometric]
    if image is None or not views:
        return _bind_once(active, spans, page.image_png, questions)
    height, width = image.shape[:2]
    merged: list[Binding] = []
    seen: set[str] = set()
    for view in views:
        box = _padded(view.bbox, width, height)
        local = [span for span in spans if _inside(span, box)]
        if not local:
            continue
        x0, y0 = int(box.x), int(box.y)
        crop = image[y0 : y0 + int(box.h), x0 : x0 + int(box.w)]
        if crop.size == 0:
            continue
        ok, encoded = cv2.imencode(".png", crop)
        if not ok:
            continue
        label = _VIEW_LABEL.get(view.kind, "Görünüş")
        if progress is not None:
            progress(f"{label} modele gidiyor", "Kırpılmış görünüş ve ölçüleri sırayla bağlanıyor. Cevap gelene kadar bu adım sürer.")
        found = _bind_once(active, local, encoded.tobytes(), questions)
        if any(question.role == "model" for question in questions):
            return []
        for binding in found:
            if binding.span_id in seen:
                continue
            seen.add(binding.span_id)
            merged.append(binding)
    return merged


def _bind_once(binder, spans, image: bytes, questions: list[Question]) -> list[Binding]:
    try:
        return list(binder.bind(spans, image))
    except UnavailableModel as exc:
        questions.append(Question(role="model", reason=str(exc)))
        return []


def _padded(bbox: BBox, width: int, height: int) -> BBox:
    pad_x = max(24.0, bbox.w * 0.18)
    pad_y = max(24.0, bbox.h * 0.18)
    x0 = max(0, int(bbox.x - pad_x))
    y0 = max(0, int(bbox.y - pad_y))
    x1 = min(width, int(bbox.x + bbox.w + pad_x))
    y1 = min(height, int(bbox.y + bbox.h + pad_y))
    return BBox(x=float(x0), y=float(y0), w=float(x1 - x0), h=float(y1 - y0))


def _inside(span: Span, box: BBox) -> bool:
    cx = span.bbox.x + span.bbox.w / 2
    cy = span.bbox.y + span.bbox.h / 2
    return box.x <= cx <= box.x + box.w and box.y <= cy <= box.y + box.h


def _merge_answers(bindings: list[Binding], spans: list[Span], answers: dict[str, float]) -> list[Binding]:
    kept = [item for item in bindings if item.role not in answers]
    kinds = {"length", "diameter", "radius", "angle", "height", "depth", "other"}
    for role, value in answers.items():
        previous = next((item for item in bindings if item.role == role), None)
        kind = previous.kind if previous is not None else (role if role in kinds else "other")
        span = Span(
            id=f"user-{role}",
            text=str(value),
            value=float(value),
            kind=SpanKind.linear,
            bbox=BBox(x=0, y=0, w=1, h=1),
            source=Source.user,
        )
        spans.append(span)
        kept.append(Binding(role=role, span_id=span.id, value=float(value), kind=kind, note="kullanıcı"))
    return kept
