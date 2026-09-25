import cv2
import numpy as np
import pytest

from drawingto3d.app import merge_records
from drawingto3d.ingest import parse_dimension, split_count
from drawingto3d.roles import crop_for_span, parse_role, read_records, role_choices, role_prompt
from drawingto3d.schema import BBox, DimensionRecord, Page, Source, Span, SpanKind


def test_count_prefix_is_split_off():
    assert split_count("4x2-Ø30") == (8, "Ø30")
    assert split_count("4-R20") == (4, "R20")
    assert split_count("2xØ30") == (2, "Ø30")
    assert split_count("360") == (1, "360")
    assert split_count("3.6") == (1, "3.6")


def test_prefixed_dimension_keeps_kind_and_value():
    assert parse_dimension("4x2-Ø30") == (SpanKind.diameter, 30.0)
    assert parse_dimension("4-R20") == (SpanKind.radius, 20.0)
    assert parse_dimension("C10") == (SpanKind.linear, 10.0)


def test_prefix_limits_the_choices():
    assert role_choices("Ø290") == ("outer_diameter", "inner_diameter", "hole_diameter")
    assert role_choices("4x2-Ø60") == ("outer_diameter", "inner_diameter", "hole_diameter")
    assert role_choices("R260") == ("bend_radius", "corner_radius", "fillet")
    assert role_choices("C10") == ("chamfer",)
    assert role_choices("45°") == ("angle",)
    assert role_choices("360") == ("edge", "thickness", "hole_spacing")
    assert "outer_diameter, inner_diameter, hole_diameter" in role_prompt("Ø290", role_choices("Ø290"))


def test_answer_outside_the_list_is_unknown():
    choices = role_choices("R260")
    assert parse_role("bend_radius", choices) == "bend_radius"
    assert parse_role("Bend radius.", choices) == "bend_radius"
    assert parse_role("corner-radius", choices) == "corner_radius"
    assert parse_role("outer_diameter", choices) == "unknown"
    assert parse_role("I think it is the pipe", choices) == "unknown"


def test_crop_is_square_inside_the_page():
    page = _page(400, 300, [_span("s0", "50", 5.0, 5.0), _span("s1", "260", 380.0, 280.0)])
    for span in page.spans:
        crop = cv2.imdecode(np.frombuffer(crop_for_span(page, span), dtype=np.uint8), cv2.IMREAD_COLOR)
        assert crop.shape[0] == crop.shape[1] == 220
    small = _page(120, 90, [_span("s0", "50", 5.0, 5.0)])
    crop = cv2.imdecode(np.frombuffer(crop_for_span(small, small.spans[0]), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert crop.shape[0] == crop.shape[1] == 90


def test_records_take_roles_from_the_reader_and_keep_spans():
    page = _page(400, 300, [_span("s0", "Ø290", 100.0, 100.0), _span("s1", "R260", 200.0, 100.0), _span("s2", "C10", 300.0, 100.0), _span("s3", "4x2-Ø30", 100.0, 200.0)])
    reader = _Reader({"Ø290": "outer diameter", "R260": "nonsense", "4x2-Ø30": "hole_diameter"})
    seen = []
    records = read_records(page, reader, lambda title, detail: seen.append(title))
    by_text = {record.text: record for record in records}
    assert by_text["Ø290"].role == "outer_diameter"
    assert by_text["R260"].role == "unknown"
    assert by_text["C10"].role == "chamfer"
    assert by_text["4x2-Ø30"].role == "hole_diameter" and by_text["4x2-Ø30"].count == 8
    assert by_text["4x2-Ø30"].value == 30.0
    assert reader.asked == ["Ø290", "R260", "4x2-Ø30"]
    assert seen[0] == "Ölçüler okunuyor (1/4)" and seen[-1] == "Ölçüler okunuyor (4/4)"
    assert [span.id for span in page.spans] == ["s0", "s1", "s2", "s3"]


def test_user_edits_replace_roles_and_mark_the_source():

    current = [
        DimensionRecord(span_id="a", text="R10", value=10, role="bend_radius"),
        DimensionRecord(span_id="b", text="360", value=360, role="edge"),
    ]
    merged = merge_records(current, [{"span_id": "a", "role": "fillet", "value": 10}, {"span_id": "zzz", "role": "edge"}])
    assert merged[0].role == "fillet" and merged[0].source == Source.user
    assert merged[1].role == "edge" and merged[1].source == Source.ocr

    with pytest.raises(ValueError):
        merge_records(current, [{"span_id": "b", "role": "pipe"}])


def _page(width: int, height: int, spans: list[Span]) -> Page:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return Page(path="mem.png", width=width, height=height, image_png=encoded.tobytes(), spans=spans, vector_text=True)


def _span(span_id: str, text: str, x: float, y: float) -> Span:
    kind, value = parse_dimension(text)
    return Span(id=span_id, text=text, value=value, kind=kind, bbox=BBox(x=x, y=y, w=30, h=14), source=Source.pdf_text)


class _Reader:
    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def ask(self, image_png: bytes, prompt: str) -> str:
        assert image_png.startswith(b"\x89PNG")
        text = prompt.split("reads '", 1)[1].split("'", 1)[0]
        self.asked.append(text)
        return self.answers.get(text, "")
