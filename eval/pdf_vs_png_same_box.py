"""H-R15: raster block-01'de `9` okuyor, metin katmani ayni yerde `55`. Soru: gorselde ne var?

Metin katmani OCR kullanmaz (paftanin kendi metnini okur), raster ise ayni pikselleri OCR'a sorar. Yani fark
OCR'in kendisinde. Ilk dogrulanacak sey basit: ayni kutuda iki gorsel ayni mi, ve orada `55` mi basili?

Olcum:
  1. pdf'te `55` hangi kutuda (metin katmani birebir soyluyor),
  2. raster'in `9` okudugu kutu (598,809)-(635,837) ile ayni mi,
  3. ayni kutu pdf ve png gorselinden kirpilip yan yana kaydedilir (gozle bakilir),
  4. iki kirpigin piksel farki olculur (ayni mi, farkli mi).

Model cagrisi yok.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from drawingto3d.ingest import load_page  # noqa: E402

PART = ROOT / "out/lab/data/v2/pilot-block-01"
RASTER_BOX = (598.0, 809.0, 635.0, 837.0)  # raster yolunun `9` okudugu kutu (olculdu)
SCRATCH = Path("/Users/aydemir/.hermes/cache/scratch/block01-55-vs-9")
SCRATCH.mkdir(parents=True, exist_ok=True)

pdf_page = load_page(PART / "drawing.pdf")
print("metin katmani sayilari (ilk 12):")
for span in pdf_page.spans[:12]:
    if span.value is None:
        continue
    print(f"  {span.id} text={span.text!r} value={span.value} box=({span.bbox.x:.0f},{span.bbox.y:.0f},"
          f"{span.bbox.x + span.bbox.w:.0f},{span.bbox.y + span.bbox.h:.0f})")

fifty_five = [span for span in pdf_page.spans if span.text and "55" in span.text]
print("pdf'te `55` iceren spanlar:", [(round(s.bbox.x), round(s.bbox.y), round(s.bbox.x + s.bbox.w),
                                        round(s.bbox.y + s.bbox.h)) for s in fifty_five])
if fifty_five:
    span = fifty_five[0]
    pdf_box = (span.bbox.x, span.bbox.y, span.bbox.x + span.bbox.w, span.bbox.y + span.bbox.h)
    print("pdf `55` kutusu:", tuple(round(value, 1) for value in pdf_box))
    print("raster `9` kutusu:", RASTER_BOX,
          "-> dikey/yatay ortusme:",
          not (pdf_box[2] < RASTER_BOX[0] or RASTER_BOX[2] < pdf_box[0]
               or pdf_box[3] < RASTER_BOX[1] or RASTER_BOX[3] < pdf_box[1]))

pdf_image = np.array(Image.open(PART / "drawing.pdf" if False else PART / "drawing.png"))
raster_page = load_page(PART / "drawing.png")
pdf_render = np.array(Image.open(__import__("io").BytesIO(pdf_page.image_png)))
png_render = np.array(Image.open(__import__("io").BytesIO(raster_page.image_png)))
print("pdf render", pdf_render.shape, "png", png_render.shape, "png dosyasi", pdf_image.shape)
# Iki yol ayni gorseli farkli olcekte isliyor (pdf renderi kucuk, png dosyasi buyuk). Ayni piksel kutusunu
# karsilastirmak icin once pdf renderi png boyutuna getirilir; yoksa "ayni kutu" paftada ayni yer degildir
# (olculdu: ayni kutuda ortalama fark 44 cikti, cunku kutular farkli yerleri gosteriyordu).
if pdf_render.shape[:2] != png_render.shape[:2]:
    pdf_render = np.array(Image.fromarray(pdf_render).resize(
        (png_render.shape[1], png_render.shape[0]), Image.BILINEAR))
    print("pdf renderi png boyutuna getirildi:", pdf_render.shape)

pad = 6.0
x0, y0, x1, y1 = RASTER_BOX
box = (int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(x1 + pad), int(y1 + pad))


def crop(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    return image[min(y1 + int(pad), height):0:-1][:0] if False else image[box[1]:min(box[3], height), box[0]:min(box[2], width)]


left, right = crop(pdf_render), crop(png_render)
common = (min(left.shape[0], right.shape[0]), min(left.shape[1], right.shape[1]))
difference = float(np.abs(left[: common[0], : common[1]].astype(int) - right[: common[0], : common[1]].astype(int)).mean())
print(f"ayni kutuda pdf/png ortalama piksel farki: {difference:.2f} (0 = birebir ayni)")

scale = 6
strip = np.full((common[0] + 8, common[1] * 2 + 26, 3), 255, dtype=np.uint8)
strip[4 : 4 + common[0], 4 : 4 + common[1]] = left[: common[0], : common[1], :3]
strip[4 : 4 + common[0], common[1] + 22 : common[1] * 2 + 22] = right[: common[0], : common[1], :3]
image = Image.fromarray(strip).resize((strip.shape[1] * scale, strip.shape[0] * scale), Image.NEAREST)
out = SCRATCH / "pdf-vs-png-same-box.png"
image.save(out)
print("kaydedildi:", out, image.size)
print(json.dumps({"pdf_box": [round(value, 1) for value in pdf_box] if fifty_five else None,
                  "raster_box": list(RASTER_BOX), "mean_pixel_difference": round(difference, 2),
                  "crop": str(out)}, ensure_ascii=False))
