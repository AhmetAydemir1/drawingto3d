from drawingto3d.legacy.bind import reject_invented, validate_bindings
from drawingto3d.schema import BBox, Binding, Span, SpanKind


def _span(span_id: str, value: float) -> Span:
    return Span(id=span_id, text=str(value), value=value, kind=SpanKind.linear, bbox=BBox(x=0, y=0, w=40, h=12))


def test_model_json_drops_numbers_that_were_not_read():
    from drawingto3d.legacy.bind import _parse_model_json

    spans = [_span("s1", 180)]
    proposed = _parse_model_json(
        '{"features":[{"role":"toplam boy","span_id":"s1","value":180,"kind":"length"},'
        '{"role":"uydurma","span_id":"yok","value":29,"kind":"radius"}]}'
    )
    kept = validate_bindings(proposed, spans)
    assert [(item.role, item.kind) for item in kept] == [("toplam boy", "length")]
    assert all(item.role != "hex_across_flats" for item in kept)


def test_invented_number_is_rejected():
    spans = [_span("s1", 180)]
    proposed = [{"role": "length", "span_id": "s1", "value": 180}, {"role": "end_radius", "span_id": "missing", "value": 29}]
    questions = reject_invented(proposed, spans)
    assert any(item.reason == "listedeki bir span değil" for item in questions)
    bindings = validate_bindings(
        [
            Binding(role="toplam boy", span_id="s1", value=180, kind="length"),
            Binding(role="end_radius", span_id="missing", value=29, kind="radius"),
        ],
        spans,
    )
    assert [item.role for item in bindings] == ["toplam boy"]
