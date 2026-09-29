"""Does the printed `40` own a row in the ink at all? Walk the band around it and measure.

`eval/gate_row_probe.py` showed the gate drops this number because no extracted row lies within a text
height of its box (nearest 94.5 px against 21 px). This asks the ink itself: in the band the number sits
in, which rows carry a long dark run — a dimension line — and how long is it.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import lines  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402

DRAWING = ROOT / "out/lab/data/v2/pilot-block-01/drawing.png"
BOX = (621, 735, 653, 758)  # the printed `40`
X0, X1, Y0, Y1 = 380, 900, 690, 870  # the band around it, inside the view's own width

page = load_page(DRAWING)
gray = cv2.cvtColor(cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR),
                    cv2.COLOR_BGR2GRAY)
binary = lines.ink(gray)
segments = {(round(s.y0), round(s.x0), round(s.x1)) for s in lines.thin_segments(binary) if s.horizontal}
print(f"box center x={(BOX[0] + BOX[2]) / 2:.0f} y={(BOX[1] + BOX[3]) / 2:.0f}; extracted horizontal segments in band:",
      sorted(row for row in segments if Y0 <= row[0] <= Y1 and row[1] < X1 and row[2] > X0))

print("\nrows with a dark run of 60 px or more (x band 380..900):")
for y in range(Y0, Y1):
    strip = binary[y, X0:X1] > 0
    if strip.sum() < 60:
        continue
    best, run, start, best_start = 0, 0, 0, 0
    for index, dark in enumerate(strip):
        if dark:
            run += 1
            if run > best:
                best, best_start = run, index - run + 1
        else:
            run = 0
    gap_to_box = min(abs(y - BOX[1]), abs(y - BOX[3]))
    print(f"  y={y} ink={int(strip.sum()):4d} longest_run={best:4d} x={X0 + best_start}..{X0 + best_start + best}"
          f"  {gap_to_box:4d} px from the box")

print("\nthe same walk for the number that IS read (`55`, 598,809-635,837):")
for y in range(800, 860):
    strip = binary[y, X0:X1] > 0
    if strip.sum() < 60:
        continue
    best, run, best_start = 0, 0, 0
    for index, dark in enumerate(strip):
        if dark:
            run += 1
            if run > best:
                best, best_start = run, index - run + 1
        else:
            run = 0
    print(f"  y={y} ink={int(strip.sum()):4d} longest_run={best:4d} x={X0 + best_start}..{X0 + best_start + best}")
