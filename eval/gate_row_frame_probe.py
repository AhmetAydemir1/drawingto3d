"""The wider frame: which long strokes exist around the printed `40`'s view, and where do they end?"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402

page = load_page(ROOT / "out/lab/data/v2/pilot-block-01/drawing.png")
gray = cv2.cvtColor(cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR),
                    cv2.COLOR_BGR2GRAY)
primitives = perceive._primitives(gray)
scale = 8.45  # px per mm, agreed by the two readings that fit (55 -> 467.5 px, 60 -> 506 px)

print("strokes longer than 100 px in the window x 150..1150, y 500..1150 (row/col, extent, px, mm):")
rows, cols = [], []
for primitive in primitives:
    if len(primitive.points) != 2:
        continue
    (x0, y0), (x1, y1) = primitive.points
    if abs(y1 - y0) <= 3:
        length = abs(x1 - x0)
        if length > 100 and 500 <= (y0 + y1) / 2 <= 1150 and min(x0, x1) < 1150:
            rows.append((round((y0 + y1) / 2), round(min(x0, x1)), round(max(x0, x1)),
                         round(length), round(length / scale, 1)))
    elif abs(x1 - x0) <= 3:
        length = abs(y1 - y0)
        if length > 100 and 150 <= (x0 + x1) / 2 <= 1150:
            cols.append((round((x0 + x1) / 2), round(min(y0, y1)), round(max(y0, y1)),
                         round(length), round(length / scale, 1)))

for row in sorted(rows):
    print("  H", row)
for col in sorted(cols):
    print("  V", col)
