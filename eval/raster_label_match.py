"""Kalınlık tavani degisikliginin yanlislanabilir olcusu: dort v2 paftasinda kept ve **etiketle uyum**.

Degisiklik korunuyor ama tek paftada net kazanc kanitlanmadi (pilot-block-01: kept 3 -> 3, etiketle
uyusan 2 -> 2; kapi `8`i yerlestirebildi, `20` terfisi kayboldu). Bu araç kararı dort paftaya yayıyor:

  - her paftada kept sayisi ve kayda giren degerler,
  - etiketle uyusan / uyusmayan kayit sayisi (asil olcu: kept sayisi degil),
  - yerlesemeyen okumalarin gerekce dagilimi (cizgi yok mu, iki aday mi, olcek mi),
  - pdf (metin katmani) ve png (raster) kume karsilastirmasi: ayni pafta iki yoldan ayni sayilari vermeli.

Etiketler olcum referansidir (degerlendirme verisi), urun girdisi degil. Model cagrisi yok.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive_with_report  # noqa: E402

DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/iterations/raster-label-match"
OUT.mkdir(parents=True, exist_ok=True)


def labelled(part: Path) -> list[float]:
    labels = json.loads((part / "labels.json").read_text(encoding="utf-8"))
    return [float(entry["value_mm"]) for entry in labels.get("printed_dimensions", [])
            if entry.get("value_mm") is not None]


def matches(value: float, expected: list[float], tolerance: float = 0.001) -> bool:
    return any(abs(value - candidate) <= max(tolerance, 0.04 * candidate) for candidate in expected)


summary: dict[str, dict] = {}
for part in sorted(path for path in DATA.iterdir() if (path / "drawing.png").exists()):
    expected = labelled(part)
    per_path = {}
    for name in ("drawing.pdf", "drawing.png"):
        source = part / name
        if not source.exists():
            continue
        page = load_page(source)
        _primitives, spans, report = perceive_with_report(page, reader=None)
        kept = [(span.text, span.value, span.anchor_mode) for span in spans]
        matched = [text for text, value, _mode in kept if value is not None and matches(float(value), expected)]
        per_path["pdf" if name.endswith("pdf") else "png"] = {
            "kept": len(kept),
            "kept_values": [value for _text, value, _mode in kept],
            "label_matching": len(matched),
            "answered_by_nothing": [value for value in kept if value is None],
            "unplaced": dict(Counter(row["reason"] for row in report.get("unpaired", []))),
            "sheet_numbers": report.get("sheet_numbers"),
        }
    summary[part.name] = {"labels": len(expected), "paths": per_path}
    png = per_path.get("png", {})
    pdf = per_path.get("pdf", {})
    print(f"{part.name}: etiket {len(expected)}")
    for path_name, rows in per_path.items():
        print(f"   {path_name}: kept {rows['kept']} (etiketle uyusan {rows['label_matching']}) "
              f"degerler {rows['kept_values']}")
        print(f"      yerlesemeyen: {rows['unplaced']}")
    if pdf and png:
        print(f"   pdf/png kume karsilastirmasi: pdf {sorted(v for v in pdf['kept_values'] if v is not None)}"
              f" | png {sorted(v for v in png['kept_values'] if v is not None)}")

(OUT / "match.json").write_text(json.dumps(
    {"schema": "drawingto3d.eval.raster-label-match/1",
     "question": "Kalınlık tavani degisikligi dort v2 paftasinda etiketle uyusan kayit sayisini artiriyor mu?",
     "parts": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", OUT / "match.json")
