"""Can a dropped number be paired by its own value? Small reproduction before touching the product path.

The text layer gives the number and its box exactly. The gate keeps only the ones it can anchor. Question:
for the dropped ones, does the sheet's own consensus scale (from the anchored readings) predict a stroke
length that matches, and is that candidate unique?
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import lines, scale  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import _DimensionGate, _text_mask  # noqa: E402

PART = ROOT / "out/lab/data/v2/pilot-step-01/drawing.pdf"
page = load_page(PART)
gray = cv2.cvtColor(cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR),
                    cv2.COLOR_BGR2GRAY)
binary = lines.ink(gray)
segments = lines.thin_segments(binary)
text_mask = _text_mask(gray)
heights = [float(span.bbox.h) for span in page.spans if span.value is not None]
gate = _DimensionGate(binary, segments, text_mask, gray=gray, text_height=float(np.median(heights)))

kept, dropped = [], []
for span in page.spans:
    if span.value is None:
        continue
    box = (span.bbox.x, span.bbox.y, span.bbox.x + span.bbox.w, span.bbox.y + span.bbox.h)
    accepted, anchors, mode = gate.accepts(box)
    row = (float(span.value), box, anchors, mode)
    (kept if accepted else dropped).append(row)

print(f"{PART.parent.name}: page {page.width:.0f}x{page.height:.0f} px, segments {len(segments)}")
print(f"kept {len(kept)}, dropped {len(dropped)}")
pairs = [(value, float(np.hypot(a[1][0] - a[0][0], a[1][1] - a[0][1]))) for value, _box, a, _m in kept if a]
calibration, inliers = scale.consensus(pairs, minimum=2)
print("anchored pairs (value, px):", [(v, round(px, 1)) for v, px in pairs])
print("consensus:", None if calibration is None else
      f"{calibration.px_per_mm:.3f} px/mm from {calibration.samples} readings, inliers {inliers}")

if calibration is not None:
    px_per_mm = calibration.px_per_mm
    print("\ndropped numbers: value -> expected px, and strokes of that length (unique?)")
    for value, box, _a, _m in sorted(dropped):
        expected = value * px_per_mm
        candidates = []
        for segment in segments:
            length = segment.length
            if abs(length - expected) <= max(0.04 * expected, 2.5):
                candidates.append((round(length), "H" if segment.horizontal else "V",
                                   round(segment.x0), round(segment.y0), round(segment.y1) if not segment.horizontal else round(segment.x1)))
        print(f"  {value:6g} mm -> {expected:6.1f} px  box={tuple(round(v) for v in box)}  candidates={candidates}")
