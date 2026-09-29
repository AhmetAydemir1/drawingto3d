"""H-R12 olcusu: uzun cizgiler nerede kayboluyor - murekkep esiginde mi, inceltmede mi?

`lines.ink` murekkebi paftanin kendi kagidina gore seciyor; `thin_segments` ise kalinligi `max_thickness`
(4 px) gecen her seyi "olcu cizgisi degil" sayip atiyor (gerekce: 200 dpi'da olcu/uzatma cizgisi 2-3 px,
govde ve antet cizgisi 5-6 px). Bu pafta 2526x1786 px: eger olcu cizgileri burada 5-6 px basiliyorsa
kural onlari da eliyor - ve tam olarak `40`/`8`/`4` cizgileri kumede yok (bkz.
iterations/scale-bootstrap-and-missing-strokes).

Olcu: `max_thickness` ve `min_length` degistikce kac cizgi cikiyor, 337.3 px'lik (40 mm) cizgi gorunuyor mu,
ve basili `40` satirinda (y 600-900) uzun murekkep kosulari hangi kalinlikta.

Yalniz geometri: OCR yok.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from drawingto3d import lines, perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.scale import RELATIVE_TOLERANCE  # noqa: E402

PART = ROOT / "out/lab/data/v2/pilot-block-01"
TARGET = 40.0 * 8.433  # 337.3 px, the 40 mm dimension of the sheet's own scale
BAND = (300, 600, 1000, 900)  # around the printed `40` (621,735)-(653,758)

page = load_page(PART / "drawing.png")
image = perceive.cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), perceive.cv2.IMREAD_COLOR)
gray = perceive.cv2.cvtColor(image, perceive.cv2.COLOR_BGR2GRAY)
binary = lines.ink(gray)
print(f"piksel {gray.shape[1]}x{gray.shape[0]}, murekkep orani {float((binary > 0).mean()):.4f}, "
      f"paper p90 {float(np.percentile(gray, 90)):.0f}, koyu p1 {float(np.percentile(gray, 1)):.0f}")

x0, y0, x1, y1 = BAND
crop = binary[y0:y1, x0:x1] > 0
runs: list[tuple[int, int]] = []
for row in range(crop.shape[0]):
    length = 0
    for column in range(crop.shape[1]):
        if crop[row, column]:
            length += 1
            continue
        if length >= 60:
            runs.append((y0 + row, length))
        length = 0
    if length >= 60:
        runs.append((y0 + row, length))
print(f"basili `40` bolgesinde (x {x0}-{x1}, y {y0}-{y1}) >=60 px murekkep kosusu: {len(runs)} satir")
print("  en uzun kosular:", sorted(runs, key=lambda row: -row[1])[:8])

print("=== thin_segments parametreleri ===")
report = {}
for max_thickness in (4, 6, 8, 10):
    for min_length in (36, 24):
        segments = lines.thin_segments(binary, min_length=min_length, max_thickness=max_thickness)
        lengths = sorted(segment.length for segment in segments)
        near = [round(length, 1) for length in lengths if abs(length - TARGET) <= TARGET * RELATIVE_TOLERANCE]
        longest = [round(length, 1) for length in lengths[-6:]]
        key = f"thickness<={max_thickness},min_length>={min_length}"
        report[key] = {"segments": len(segments), "longest": longest, "near_337": near}
        print(f"  {key}: {len(segments)} cizgi | en uzun {longest} | 337.3 px'e yakin {near}")
print(json.dumps(report, ensure_ascii=False))
