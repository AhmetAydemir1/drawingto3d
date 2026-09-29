"""A minimal vector PDF writer: lines, circles and real text, for generated drawings.

Generated sheets have to be vector files whose text layer carries the printed callouts, the way a CAD
export does — a bitmap with drawn-on text would not exercise the reader's PDF text path. Drawing the
page here keeps the geometry and the text under the generator's control (nothing is re-derived from
the raster), and it needs no third-party PDF library.

**All page geometry is in millimetres**, both coordinates and sizes, which is how a sheet is laid out;
points are produced at the point of emission. Coordinates are page space with the origin top-left and
y growing downwards, and the y axis is flipped once, when the content stream is written.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

MM_TO_PT = 72.0 / 25.4


def pt(value_mm: float) -> float:
    """Millimetres to PDF points (the unit the file itself uses)."""
    return value_mm * MM_TO_PT


@dataclass
class PdfPage:
    """One page, A4 landscape by default. Coordinates are millimetres, y downwards."""

    width_mm: float = 297.0
    height_mm: float = 210.0
    _ops: list[str] = field(default_factory=list)

    # -- geometry ---------------------------------------------------------

    def line(self, start, end, *, width_mm: float = 0.35, dash_mm: tuple[float, float] | None = None) -> None:
        self.polyline([start, end], width_mm=width_mm, dash_mm=dash_mm)

    def polyline(self, points, *, width_mm: float = 0.35, dash_mm: tuple[float, float] | None = None,
                 close: bool = False) -> None:
        if len(points) < 2:
            return
        ops = [f"{_num(pt(width_mm))} w"]
        if dash_mm:
            ops.append(f"[{_num(pt(dash_mm[0]))} {_num(pt(dash_mm[1]))}] 0 d")
        else:
            ops.append("[] 0 d")
        ops.append(f"{_num(pt(points[0][0]))} {_num(self._flip_y(points[0][1]))} m")
        for x, y in points[1:]:
            ops.append(f"{_num(pt(x))} {_num(self._flip_y(y))} l")
        if close:
            ops.append("h")
        ops.append("S")
        self._ops.append(" ".join(ops))

    def circle(self, centre, radius_mm: float, *, width_mm: float = 0.35, segments: int = 72) -> None:
        cx, cy = centre
        points = [(cx + radius_mm * math.cos(2 * math.pi * i / segments),
                   cy + radius_mm * math.sin(2 * math.pi * i / segments)) for i in range(segments)]
        self.polyline(points, width_mm=width_mm, close=True)

    def arrow(self, tip, direction, *, length_mm: float = 3.0, width_mm: float = 0.3) -> None:
        """An arrowhead, drawn as two short strokes back from the tip."""
        dx, dy = _unit(direction)
        back = (tip[0] - dx * length_mm, tip[1] - dy * length_mm)
        side = (-dy, dx)
        half = length_mm * 0.3
        for sign in (1.0, -1.0):
            corner = (back[0] + side[0] * half * sign, back[1] + side[1] * half * sign)
            self.line(tip, corner, width_mm=width_mm)
        self.line((back[0] + side[0] * half, back[1] + side[1] * half),
                  (back[0] - side[0] * half, back[1] - side[1] * half), width_mm=width_mm)

    def text(self, x: float, y: float, content: str, *, size_mm: float = 3.5, align: str = "left",
             bold: bool = False, rotated: bool = False) -> None:
        """Write one line of text; `y` is the text's baseline."""
        body = escape(content.encode("cp1252", "replace").decode("cp1252"))
        width = self.text_width(content, size_mm, bold=bold)
        if align == "center":
            x -= width / 2
        elif align == "right":
            x -= width
        font = "/F2" if bold else "/F1"
        if rotated:  # 90° counter-clockwise, reading upwards
            matrix = f"0 1 -1 0 {_num(pt(x))} {_num(self._flip_y(y))} Tm"
        else:
            matrix = f"1 0 0 1 {_num(pt(x))} {_num(self._flip_y(y))} Tm"
        self._ops.append(
            f"BT {font} {_num(pt(size_mm))} Tf {matrix} ({body}) Tj ET")

    def text_width(self, content: str, size_mm: float, *, bold: bool = False) -> float:
        return _text_width(content, pt(size_mm), bold) / MM_TO_PT

    # -- output -----------------------------------------------------------

    def _flip_y(self, y: float) -> float:
        return pt(self.height_mm) - pt(y)

    def to_bytes(self) -> bytes:
        content = "\n".join(self._ops).encode("cp1252", "replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_num(pt(self.width_mm))} "
             f"{_num(pt(self.height_mm))}] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> "
             f"/Contents 4 0 R >>").encode(),
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n".encode()
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode()
        return bytes(out)


def escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


# Helvetica advance widths (per 1000 units) for the characters the generator prints.
_WIDTHS = {" ": 278, "(": 333, ")": 333, "±": 584, "Ø": 778, "°": 400, ".": 278, ",": 278, "-": 333,
           "/": 278, ":": 278, "1": 556}
_DEFAULT_WIDTH = 556
_UPPER_WIDTH = 667


def _text_width(text: str, size_pt: float, bold: bool) -> float:
    total = 0
    for char in text:
        if char in _WIDTHS:
            total += _WIDTHS[char]
        elif char.isalpha():
            total += _UPPER_WIDTH if char.isupper() else _DEFAULT_WIDTH
        else:
            total += _DEFAULT_WIDTH
    return total / 1000.0 * size_pt * (1.03 if bold else 1.0)


def _unit(vector) -> tuple[float, float]:
    length = math.hypot(*vector)
    if not length:
        return (0.0, 0.0)
    return (vector[0] / length, vector[1] / length)


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"
