"""H-R11 sonrasi soru: kazanan oran 8.433 px/mm etiketi tutuyor, ama yalniz 2 okuma satir buldu.
Eksik olan olcek mi, cizgi kumesi mi? Bu betik cizgi kumesini dogrudan olcer.

Okumalar OCR'dan geldigi icin burada sabit yazildi (kaynak: /tmp/scale-bootstrap.log ve
iterations/raster-read-first-pair-second/record.json): betik yalniz cizgi cikarimini olcuyor, model
cagrisi ve OCR yok - saniyeler surer.

Sorular:
  1. Paftada kac cizgi parasi var ve en uzunlari ne kadar?
  2. Etiketin bekledigi her uzunluk (deger x 8.433) cizgi kumesinde HERHANGI bir yerde var mi?
  3. O okumanin kendi satirinda (dikey bandi icinde) hangi uzunluklar var?
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
PX_PER_MM = 8.433

# Okunan sayilar: (metin, deger mm, kutu x0,y0,x1,y1) - olcülmüs degerler.
READINGS = [
    ("40", 40.0, 321.0, 517.0, 359.0, 546.0),
    ("29", 29.0, 670.0, 517.0, 708.0, 546.0),
    ("40", 40.0, 618.0, 732.0, 656.0, 761.0),
    ("8", 8.0, 755.0, 1130.0, 776.0, 1159.0),
    ("7", 7.0, 1242.0, 1153.0, 1262.0, 1194.0),
    ("20", 20.0, 322.0, 1181.0, 359.0, 1210.0),
    ("09", 9.0, 598.0, 809.0, 635.0, 837.0),
    ("60", 60.0, 619.0, 1404.0, 656.0, 1433.0),
]
LABELS = {"60": 60.0, "20": 20.0, "40": 40.0, "25": 25.0, "8": 8.0, "55": 55.0, "4": 4.0}

page = load_page(PART / "drawing.png")
image = perceive.cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), perceive.cv2.IMREAD_COLOR)
gray = perceive.cv2.cvtColor(image, perceive.cv2.COLOR_BGR2GRAY)
segments = [segment for segment in lines.thin_segments(lines.ink(gray)) if segment.length > 0]
lengths = sorted((segment.length, segment.horizontal, segment.x0, segment.y0) for segment in segments)

print(f"cizgi parasi: {len(segments)}")
print("en uzun 15:", [(round(length, 1), "H" if horizontal else "V") for length, horizontal, _x, _y in lengths[-15:]])


def fits(candidate: float, target: float) -> bool:
    return abs(candidate - target) <= target * RELATIVE_TOLERANCE


print("=== etiketin bekledigi uzunluk cizgi kumesinde var mi? ===")
for text, value in LABELS.items():
    target = value * PX_PER_MM
    hits = [(round(length, 1), "H" if horizontal else "V", int(x), int(y))
            for length, horizontal, x, y in lengths if fits(length, target)]
    print(f"  {text!r} -> {target:.1f} px | eslesen cizgi: {len(hits)} {hits[:6]}")

print("=== her okumanin kendi satirinda (bant icinde) cizgiler ===")
for text, value, x0, y0, x1, y1 in READINGS:
    target = value * PX_PER_MM
    band = [(round(length, 1), "H" if horizontal else "V", int(x), int(y))
            for length, horizontal, x, y in lengths
            if (y0 - 0.5 * (y1 - y0) * 4 <= y <= y1 + 0.5 * (y1 - y0) * 4)
            or (x0 - 0.5 * (x1 - x0) * 4 <= x <= x1 + 0.5 * (x1 - x0) * 4)]
    nearby = [row for row in band if fits(row[0], target)]
    print(f"  {text!r} (beklenen {target:.1f} px): bantta {len(band)} cizgi, uzunlugu tutan {len(nearby)} {nearby[:4]}")

print(json.dumps({"segments": len(segments), "px_per_mm": PX_PER_MM,
                  "labels_with_a_stroke_of_their_length": {
                      text: sum(1 for length, _h, _x, _y in lengths if fits(length, value * PX_PER_MM))
                      for text, value in LABELS.items()}}, ensure_ascii=False))
