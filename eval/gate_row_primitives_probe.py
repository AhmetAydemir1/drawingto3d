"""Is the printed `40`'s row in the sheet's *primitives* (Hough) when the thinned segments miss it?"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402

DRAWING = ROOT / "out/lab/data/v2/pilot-block-01/drawing.png"
BOX = (621.0, 735.0, 653.0, 758.0)
CX, CY = (BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2

page = load_page(DRAWING)
gray = cv2.cvtColor(cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR),
                    cv2.COLOR_BGR2GRAY)
primitives = perceive._primitives(gray)
print("primitives:", len(primitives), "kinds:", {p.kind for p in primitives})

near_horizontal, near_vertical = [], []
for primitive in primitives:
    if len(primitive.points) != 2:
        continue
    (x0, y0), (x1, y1) = primitive.points
    horizontal = abs(y1 - y0) <= 3
    vertical = abs(x1 - x0) <= 3
    if horizontal and abs((y0 + y1) / 2 - CY) <= 45 and min(x0, x1) - 60 <= CX <= max(x0, x1) + 60:
        near_horizontal.append((round((y0 + y1) / 2, 1), round(min(x0, x1)), round(max(x0, x1)),
                                round(abs(x1 - x0), 1), primitive.kind))
    if vertical and abs((x0 + x1) / 2 - CX) <= 45 and min(y0, y1) - 60 <= CY <= max(y0, y1) + 60:
        near_vertical.append((round((x0 + x1) / 2, 1), round(min(y0, y1)), round(max(y0, y1)),
                              round(abs(y1 - y0), 1), primitive.kind))

print("horizontal primitives whose row is within 45 px of the box:", sorted(near_horizontal))
print("vertical primitives whose column is within 45 px of the box:", sorted(near_vertical))
print("\nall horizontal primitives on the sheet (row, x0..x1, px):")
rows = sorted(
    (round((p.points[0][1] + p.points[1][1]) / 2, 1), round(min(p.points[0][0], p.points[1][0])),
     round(max(p.points[0][0], p.points[1][0])), round(abs(p.points[1][0] - p.points[0][0]), 1))
    for p in primitives if len(p.points) == 2 and abs(p.points[1][1] - p.points[0][1]) <= 3
)
for row in rows:
    if 660 <= row[0] <= 900:
        print("   ", row)
