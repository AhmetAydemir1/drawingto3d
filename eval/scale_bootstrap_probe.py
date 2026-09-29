"""H-R11 olcusu: olcek, kapinin ince ciktisindan degil aday ciftlerin cogunlugundan adaylanabilir mi?

Yol: paftadaki her okunmus sayi (kapi tutmus + kapi reddedip okunabilmis) ile satirindaki her cizgi
uzunlugunu esle -> oran (px/mm) -> oranlar arasinda en cok ciftin uydugu oran paftanin olcegi mi?

Neden bu: raster yolu tavuk-yumurta durumunda. Kapi sayiyi bir satira yakinlikla baglamadan okumuyor,
bu yuzden 9 etiketli sayidan 2'si tutuluyor; `scale.consensus` olcek adlandirmak icin 3 okuma ister,
2 ile olcek yok, olcek olmayinca reddedilen 8 okuma yerlesemiyor (bkz.
iterations/raster-promotion-blocked-by-scale). Oran cogunlugu bu donguya kapiyi hic kullanmadan girer.

Olcu yanlislanabilir: kazanan oran kac ciftle destekleniyor, kac okumaya satir buluyor ve bulunan
uzunluklar pafta etiketiyle tutuyor mu? Tutmazsa H-R11 de yanlistir.

Uretim yolu degil: olcum araci. Model cagrisi yok.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from drawingto3d import lines, perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive_with_report  # noqa: E402
from drawingto3d.scale import RELATIVE_TOLERANCE  # noqa: E402
from drawingto3d.schema import BBox, Span  # noqa: E402

PART = ROOT / "out/lab/data/v2/pilot-block-01"
MINIMUM_SUPPORT = 3

page = load_page(PART / "drawing.png")
labels = json.loads((PART / "labels.json").read_text(encoding="utf-8"))
_primitives, spans, report = perceive_with_report(page, reader=None)

image = perceive.cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), perceive.cv2.IMREAD_COLOR)
gray = perceive.cv2.cvtColor(image, perceive.cv2.COLOR_BGR2GRAY)
binary = lines.ink(gray)
segments = [segment for segment in lines.thin_segments(binary) if segment.length > 0]
text_mask = perceive._text_mask(gray)
glyphs = perceive._glyphs(gray, text_mask)
sizes = [max(glyph.w, glyph.h) for glyph in glyphs if not glyph.separator]
text_height = float(np.median(sizes)) if sizes else None
if text_height is None or text_height <= 0:
    # Ölçüm aracı: yazı yüksekliği bulunamazsa paftadaki basılı rakamların ölçülen yüksekliği kullanılır.
    text_height = 29.0

readings = list(spans)
for index, row in enumerate(report.get("unpaired", [])):
    x0, y0, x1, y1 = row["box"]
    readings.append(Span(id=f"unplaced-{index}", text=str(row["text"]), value=row["value"], kind="linear",
                         bbox=BBox(x=x0, y=y0, w=x1 - x0, h=y1 - y0), anchors=[], anchor_mode="dimension"))

print(f"okunan sayi: {len(readings)} (kapi {len(spans)} + reddedilip okunan {len(report.get('unpaired', []))})")
print(f"cizgi: {len(segments)}, metin yuksekligi: {text_height}")

pairs: list[tuple[float, float, str, float]] = []
for reading in readings:
    if not reading.value or reading.value <= 0:
        continue
    for segment in segments:
        distance = perceive._beside_distance(reading, segment, text_height)
        if distance is None:
            continue
        pairs.append((segment.length / float(reading.value), distance, reading.text, segment.length))
print(f"yan yana cift: {len(pairs)}")

ratios = sorted(ratio for ratio, _distance, _text, _length in pairs)
window: Counter[float] = Counter()
best = (0, None)
for start, low in enumerate(ratios):
    high = low * (1 + RELATIVE_TOLERANCE)
    end = start
    while end < len(ratios) and ratios[end] <= high:
        end += 1
    if end - start > best[0]:
        best = (end - start, ratios[start : end][len(ratios[start:end]) // 2])
support, winner = best
print(f"kazanan oran: {winner:.3f} px/mm, destek {support} cift (pencere %{RELATIVE_TOLERANCE * 100:.0f})")

agreed = [(ratio, distance, text, length) for ratio, distance, text, length in pairs
          if winner and abs(ratio - winner) <= winner * RELATIVE_TOLERANCE]
by_text: dict[str, list[float]] = {}
for _ratio, _distance, text, length in agreed:
    by_text.setdefault(text, []).append(length)
print("orana uyan okumalar:")
for text, lengths in sorted(by_text.items()):
    print(f"  {text!r}: cizgi uzunluklari {[round(length, 1) for length in sorted(lengths)]}")

expected = {str(entry.get("text")): entry.get("value_mm") for entry in labels.get("printed_dimensions", [])}
print("etiketle karsilastirma (beklenen px = deger x kazanan oran):")
for text, value in expected.items():
    if winner and value:
        print(f"  {text!r} = {value} mm -> {value * winner:.1f} px bekleniyor")
print(json.dumps({"winner_px_per_mm": winner and round(winner, 3), "support": support,
                  "readings": len(readings), "pairs": len(pairs),
                  "agreed_readings": sorted(by_text), "minimum_support": MINIMUM_SUPPORT}, ensure_ascii=False))
