from pathlib import Path

from drawingto3d.ingest import load_page, parse_dimension, parse_dimension_unit
from drawingto3d.schema import SpanKind


def test_parse_diameter_radius_and_angle():
    assert parse_dimension("Ø20") == (SpanKind.diameter, 20.0)
    assert parse_dimension("R29") == (SpanKind.radius, 29.0)
    assert parse_dimension("55°") == (SpanKind.angle, 55.0)
    assert parse_dimension("3.6")[1] == 3.6


def test_parse_dimension_reports_the_sheets_unit():
    assert parse_dimension_unit("1.563in") == (SpanKind.linear, 1.563, "in")
    assert parse_dimension_unit("0.688in") == (SpanKind.linear, 0.688, "in")
    assert parse_dimension_unit('1 1/4"') == (SpanKind.linear, 1.25, "in")
    assert parse_dimension_unit("2X 1 1/4") == (SpanKind.linear, 1.25, "in")
    assert parse_dimension_unit("Ø20") == (SpanKind.diameter, 20.0, "mm")


def test_a_token_with_letters_left_over_is_not_a_dimension():
    assert parse_dimension_unit("2389K26")[1] is None
    assert parse_dimension_unit("A4")[1] is None
    assert parse_dimension_unit("SCALE 1:2")[1] is None
    assert parse_dimension_unit("M8") == (SpanKind.linear, 8.0, "mm")


def test_pdf_vector_text_is_a_span(tmp_path: Path):
    pdf = tmp_path / "note.pdf"
    pdf.write_bytes(_pdf_with_text("180"))
    page = load_page(pdf)
    assert page.width > 0
    assert any(span.value == 180 and span.source.value == "pdf_text" for span in page.spans)


def _pdf_with_text(text: str) -> bytes:
    stream = f"BT /F1 24 Tf 40 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(body)
    body += f"xref\n0 {len(offsets)}\n".encode()
    body += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        body += f"{offset:010d} 00000 n \n".encode()
    body += f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(body)
