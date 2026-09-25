from drawingto3d.pipeline import convert_drawing
from drawingto3d.schema import ViewKind

DRAWING = "examples/solidworks-katc4b1-8-1024x729.jpg"


def test_sheet_views_keep_isometric_out():
    from drawingto3d.ingest import load_page
    from drawingto3d.views import segment_views

    page = load_page(DRAWING)
    views = segment_views(page)
    kinds = {view.kind for view in views}
    assert ViewKind.section in kinds
    assert ViewKind.plan in kinds or ViewKind.front in kinds
    assert all(not view.used_for_solid for view in views if view.kind == ViewKind.isometric)


def test_length_span_scales_the_solid(tmp_path):
    result = convert_drawing(DRAWING, tmp_path, use_model=True, binder=_LengthBinder())
    assert result.step_path is not None, [question.reason for question in result.questions]
    assert "ISO-10303-21" in open(result.step_path, errors="ignore").read()
    length = next(entry for entry in result.audit.entries if entry.kind == "length")
    assert length.value == 180
    assert length.role != "hex_across_flats"
    from drawingto3d.solid import measured_length
    from build123d import import_step

    part = import_step(result.step_path)
    assert abs(measured_length(part) - 180) < 0.5


def test_read_numbers_stay_on_spans_without_fixed_roles(tmp_path):
    result = convert_drawing(DRAWING, tmp_path, use_model=False)
    assert result.step_path is None
    values = {span.value for span in result.page.spans}
    for number in (180, 141, 28, 24, 3.6, 32):
        assert number in values
    assert all(question.role != "height_30_32" for question in result.questions)


def test_missing_model_does_not_invent_roles(tmp_path):
    result = convert_drawing(DRAWING, tmp_path, use_model=True, binder=_DownBinder())
    assert result.step_path is None
    assert any(question.role == "model" for question in result.questions)
    assert result.audit.entries == []
    assert 180 in {span.value for span in result.page.spans}


class _DownBinder:
    def bind(self, spans, image=None):
        from drawingto3d.bind import UnavailableModel

        raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez")


class _LengthBinder:
    def bind(self, spans, image=None):
        from drawingto3d.schema import Binding

        span = next((item for item in spans if item.value == 180), None)
        if span is None:
            return []
        return [Binding(role="toplam boy", span_id=span.id, value=span.value, kind="length")]
