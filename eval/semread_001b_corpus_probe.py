"""Corpus adaylarını deterministic yoldan sınar: hangi çizimde hangi callout/metin var?

Bu betik **hiç inference yapmaz**: `observe()` (PDF vektör+metin katmanı, rasterda Hough+tesseract)
çalıştırıp bulunan metinleri, primitive'leri ve süreyi özetler. Seçim gerekçesi bu ölçüme dayanır.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.observe import observe  # noqa: E402

CANDIDATES = [
    "examples/pdf with steps/1/Exercise_51.PNG",
    "examples/pdf with steps/2/Drawing.pdf",
    "examples/pdf with steps/3/Exercise 17.PNG",
    "examples/pdf with steps/4/Exercise 13.PNG",
    "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF",
    "examples/pdf with steps/6/plastic enclosue.pdf",
    "examples/pdf with steps/8/Flange.PNG",
    "examples/pdf with steps/10/Exercise 12.pdf",
    "examples/flange-elbow-90.png",
    "examples/Teknik Resim Görünüş Çıkarma Örnekleri 1 - Makine Eğitimi.jpg",
    "examples/504715c44a0f1b2bbb386bb7c387a8db.jpg",
]

DIAMETER_CALLOUT = re.compile(r"(\d+\s*[xX×]\s*)?[Øø⌀Φφ]|^R\s*\d|\bR\s*\d+(\.\d+)?\b")
DEPTH_WORDS = re.compile(r"thru|through|\u21a7|\bdept?h\b|\u00d8\s*\d+\s*[\u21a7x]\s*\d+", re.I)


def main() -> int:
    rows = []
    for relative in CANDIDATES:
        path = ROOT / relative
        record: dict = {"path": relative, "exists": path.exists()}
        if not path.exists():
            rows.append(record)
            continue
        started = time.perf_counter()
        try:
            observations = observe(path)
        except Exception as exc:  # noqa: BLE001 - tanı
            record.update({"error": f"{type(exc).__name__}: {exc}",
                           "seconds": round(time.perf_counter() - started, 2)})
            rows.append(record)
            continue
        record["seconds"] = round(time.perf_counter() - started, 2)
        record["frame"] = [observations.frame.width, observations.frame.height]
        record["primitives"] = len(observations.primitives)
        record["kinds"] = dict(Counter(p.kind for p in observations.primitives))
        texts = [{"id": t.id, "text": t.text, "value": t.value, "unit": t.unit, "kind": t.kind,
                  "count": t.count,
                  "bbox": [round(float(v), 1) for v in (t.bbox.x, t.bbox.y, t.bbox.w, t.bbox.h)]}
                 for t in observations.texts]
        record["texts"] = len(texts)
        record["diameter_like"] = [t["text"] for t in texts
                                   if DIAMETER_CALLOUT.search(t["text"])
                                   or t["kind"] in ("diameter", "radius")]
        record["depth_like"] = [t["text"] for t in texts if DEPTH_WORDS.search(t["text"])]
        record["sample_texts"] = [t["text"] for t in texts[:25]]
        record["text_detail"] = texts
        rows.append(record)
        print(json.dumps({k: v for k, v in record.items() if k not in ("text_detail", "sample_texts",
                                                                      "diameter_like", "depth_like")},
                         ensure_ascii=False), flush=True)
        print("   Ø/R örnek:", record["diameter_like"][:10], flush=True)
        print("   thru/depth örnek:", record["depth_like"][:10], flush=True)
        print("   metin örnek:", record["sample_texts"][:10], flush=True)

    target = ROOT / "out/lab/semread-001b/corpus-probe.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schema": "semread-001b-corpus-probe/1", "rows": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print("yazıldı:", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
