"""Why does the printed `40` get no anchors? Reproduce the gate's inputs and ask it directly."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from drawingto3d import lines, perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import _DimensionGate, _glyphs, _text_mask  # noqa: E402

DRAWING = ROOT / "out/lab/data/v2/pilot-block-01/drawing.png"
page = load_page(DRAWING)
import cv2  # noqa: E402

gray = cv2.cvtColor(
    cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY
)
print("gray:", gray.shape)

binary = lines.ink(gray)
segments = lines.thin_segments(binary)
text_mask = _text_mask(gray)
glyphs = _glyphs(gray, text_mask)
sizes = [max(glyph.w, glyph.h) for glyph in glyphs if not glyph.separator]
gate = _DimensionGate(binary, segments, text_mask, gray=gray, text_height=float(np.median(sizes)))
print("segments:", len(segments), "glyphs:", len(glyphs), "text_height:", round(float(np.median(sizes)), 2))

for name, box in (("printed_40", (621.0, 735.0, 653.0, 758.0)), ("printed_55", (598.0, 809.0, 635.0, 837.0))):
    print(f"--- {name} {box}")
    print("  gate:", gate.accepts(box)[0], gate.accepts(box)[1], gate.accepts(box)[2])
    found = lines.dimension_for(binary, segments, box, text_mask, strokes=None)
    print("  dimension_for:", None if found is None else (found.anchors, found.length if hasattr(found, "length") else ""))
    leader = lines.leader_near(binary, getattr(gate, "strokes", None), box, text_mask)
    print("  leader_near:", None if leader is None else (leader.tip, leader.tail))
    near = []
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    for segment in segments:
        if segment.horizontal:
            gap = abs(segment.y0 - cy) if segment.x0 - 40 <= cx <= segment.x1 + 40 else float("inf")
        else:
            gap = abs(segment.x0 - cx) if segment.y0 - 40 <= cy <= segment.y1 + 40 else float("inf")
        near.append((round(gap, 1), "H" if segment.horizontal else "V",
                     round(segment.x0), round(segment.y0), round(segment.x1), round(segment.y1),
                     round(segment.length, 1), round(segment.thickness, 1)))
    near.sort()
    print("  5 nearest rows:", near[:5])
