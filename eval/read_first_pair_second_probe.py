"""Raster yolunda 'once oku, sonra bagla' degisikliginin olcumu.

Kapı bir sayıyı bir satıra baglayamayınca eskiden hiç okumadan düşürüyordu; artık rapor istendiğinde
kümeyi okuyor ve okunabilen sayıyı 'gate_refused_but_readable' olarak bildiriyor. Bu betik pilot-block-01
PNG'si üzerinde kapının tuttuğu okumaları ve reddedip yine de okuyabildiklerini yan yana yazar.

Ürün yolu değil: teşhis aracı. Model çağrısı yok, yalnız tesseract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive_with_report  # noqa: E402

PART = ROOT / "out/lab/data/v2/pilot-block-01"
page = load_page(PART / "drawing.png")
labels = json.loads((PART / "labels.json").read_text(encoding="utf-8"))
expected = [(entry.get("text"), entry.get("value_mm"), entry.get("role"))
            for entry in labels.get("printed_dimensions", [])]

_primitives, spans, report = perceive_with_report(page, reader=None)

print("=== pafta etiketi (beklenen) ===")
print(json.dumps(expected, ensure_ascii=False))
print("=== kapinin tutttugu okumalar:", len(spans), "===")
for span in spans:
    print(f"  {span.id} text={span.text!r} value={span.value} anchors={span.anchors} mode={span.anchor_mode}")
print("=== kapi reddetti ama okunabilen:", len(report.get("unpaired", [])), "===")
for row in report.get("unpaired", []):
    print(f"  {row['text']!r} value={row['value']} box={row['box']} reason={row['reason']}")
print("=== ozet ===")
print(json.dumps({"path": report.get("path"), "kept": len(spans),
                  "unpaired": len(report.get("unpaired", [])),
                  "sheet_numbers": report.get("sheet_numbers")}, ensure_ascii=False))
