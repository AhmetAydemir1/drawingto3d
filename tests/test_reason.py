import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from drawingto3d.bind import UnavailableModel
from drawingto3d.cadrun import CadFailure, close_code, extract_code, run_program
from drawingto3d.llama import LlamaCoder, _local_origin
from drawingto3d.reason import allowed_numbers, reason_drawing
from drawingto3d.schema import DimensionRecord

BOX = "import cadquery as cq\nsolid = cq.Workplane('XY').box(10, 20, 30)\n"
BIG = "import cadquery as cq\nsolid = cq.Workplane('XY').box(360, 260, 50)\n"
GEO_BIG = "solid = geo.plate(360, 360, 50, 20)\n"
TWO = (
    "import cadquery as cq\n"
    "solid = cq.Workplane('XY').box(10, 10, 10).union("
    "cq.Workplane('XY').center(40, 0).box(10, 10, 10))\n"
)
DRAWING = Path("examples/flange-elbow-90.png")


def _record(span_id: str, text: str, value: float, role: str, count: int = 1) -> DimensionRecord:
    return DimensionRecord(span_id=span_id, text=text, value=value, role=role, count=count)


RECORDS = [
    _record("s0", "360", 360, "edge"),
    _record("s1", "50", 50, "thickness"),
    _record("s2", "150", 150, "edge"),
    _record("s3", "R260", 260, "bend_radius"),
    _record("s4", "Ø290", 290, "outer_diameter"),
    _record("s5", "Ø210", 210, "inner_diameter"),
    _record("s6", "4x2-Ø60", 60, "hole_diameter", 8),
    _record("s7", "4x2-Ø30", 30, "hole_diameter", 8),
    _record("s8", "260", 260, "hole_spacing"),
    _record("s9", "4-R20", 20, "corner_radius", 4),
    _record("s10", "R10", 10, "fillet"),
    _record("s11", "C10", 10, "chamfer"),
]


def test_remote_host_is_rejected():
    with pytest.raises(UnavailableModel):
        _local_origin("https://example.com/v1")


def test_extracts_fenced_python():
    assert extract_code("açıklama\n```python\nsolid = 1\n```\nson") == "solid = 1"


def test_program_writes_one_solid(tmp_path: Path):
    step, stl = run_program(BOX, tmp_path)
    assert step.is_file() and stl.is_file()
    assert step.stat().st_size > 100


def test_truncated_tail_still_exports(tmp_path: Path):
    cut = BOX + "solid = solid.union(cq.Workplane('XY').box(\n"
    step, _stl = run_program(cut, tmp_path)
    assert step.is_file()
    assert close_code(cut).rstrip().endswith("30)")


def test_two_bodies_fail(tmp_path: Path):
    with pytest.raises(CadFailure):
        run_program(TWO, tmp_path)


def test_records_yield_one_step_without_the_reader(tmp_path: Path):
    reader = _NeverAsked()
    coder = _Scripted([GEO_BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS, reader=reader)
    assert result.audit.accepted
    assert result.step_path and Path(result.step_path).is_file()
    assert result.page is not None and result.page.image_png
    assert [record.role for record in result.records] == [record.role for record in RECORDS]
    prompt = coder.prompts[0]
    assert "geo.ring_revolve(outer_d, inner_d, bend_radius, angle=90, plane='XY')" in prompt
    assert "- 260 mm: bend_radius" in prompt
    assert "- 30 mm: hole_diameter, count 8" in prompt


def test_first_turn_reads_records_and_stops(tmp_path: Path, monkeypatch):
    reader = _Released()
    monkeypatch.setattr("drawingto3d.reason.read_records", lambda page, vision, progress: list(RECORDS[:3]))
    coder = _Scripted([GEO_BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, reader=reader)
    assert result.step_path is None and not result.audit.accepted
    assert [record.text for record in result.records] == ["360", "50", "150"]
    assert reader.released and coder.prompts == []


def test_tiny_solid_is_sent_back(tmp_path: Path):
    coder = _Scripted([BOX, BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert "The CadQuery program failed" in coder.prompts[1]
    assert "360" in coder.prompts[1]
    assert Path(result.step_path).is_file()


def test_failure_is_sent_back_once(tmp_path: Path):
    coder = _Scripted(["import cadquery as cq\nsolid = cq.Workplane('XY').box(\n", BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert "The CadQuery program failed" in coder.prompts[1]
    assert Path(result.step_path).is_file()


def test_invented_millimetre_is_sent_back(tmp_path: Path):
    coder = _Scripted(["solid = geo.plate(360, 173, 50)\n", GEO_BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert "173 are not printed on the drawing" in coder.prompts[1]
    assert Path(result.step_path).is_file()


def test_role_used_as_a_variable_is_sent_back(tmp_path: Path):
    coder = _Scripted(["solid = geo.plate(edge, edge, thickness)\n", GEO_BIG])
    reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert "edge, thickness are role names, not variables" in coder.prompts[1]
    assert "edge -> 360, 150" in coder.prompts[1] and "thickness -> 50" in coder.prompts[1]


def test_halves_and_sums_are_allowed():
    allowed = allowed_numbers(RECORDS)
    assert {130.0, 145.0, 410.0, 100.0, 0.0, 90.0} <= allowed
    assert 173.0 not in allowed


def test_chamfer_line_is_stripped_on_the_last_try(tmp_path: Path):
    coder = _Scripted(
        ["solid = geo.plate(360, 360, 50, 20)\nsolid = geo.chamfer_edges(solid, 10, '>Z')\n"] * 3
    )
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert Path(result.step_path).is_file()
    assert "chamfer_edges" not in Path(tmp_path / "program.py").read_text()
    assert "Leave edges sharp" in coder.prompts[1]


def test_stray_import_is_sent_back(tmp_path: Path):
    coder = _Scripted(["import numpy\n" + GEO_BIG, GEO_BIG])
    reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS)
    assert "Do not import anything" in coder.prompts[1]


def test_after_build_hook_can_send_the_solid_back(tmp_path: Path):
    seen = []

    def hook(step: Path, page) -> str | None:
        seen.append(step)
        return "The front view is missing the second flange." if len(seen) == 1 else None

    coder = _Scripted([GEO_BIG, GEO_BIG])
    result = reason_drawing(DRAWING, tmp_path, coder=coder, records=RECORDS, after_build=hook)
    assert len(seen) == 2 and "second flange" in coder.prompts[1]
    assert Path(result.step_path).is_file()


def test_llama_client_posts_the_image():
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            seen["body"] = json.loads(self.rfile.read(length))
            payload = json.dumps({"choices": [{"message": {"content": "```python\n" + BOX + "```"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        text = LlamaCoder(host=f"http://127.0.0.1:{port}", timeout=5).complete(b"\x89PNG", "çiz")
    finally:
        server.shutdown()
    assert "solid" in text
    content = seen["body"]["messages"][0]["content"]
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")


class _Scripted:
    def __init__(self, programs: list[str]) -> None:
        self.programs = list(programs)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.programs.pop(0)


class _NeverAsked:
    def ask(self, image_png: bytes, prompt: str) -> str:
        raise AssertionError("okuyucu çağrılmamalıydı")


class _Released:
    def __init__(self) -> None:
        self.released = False

    def ask(self, image_png: bytes, prompt: str) -> str:
        return "edge"

    def release(self) -> None:
        self.released = True
