"""Coverage on the text-layer path: how many printed numbers does the vector sheet carry, and how many
survive the gate into records? The raster path was measured at two records per part; this is the other side.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d import scale  # noqa: E402

DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/iterations/text-layer-coverage"
OUT.mkdir(parents=True, exist_ok=True)
summary = {}

for part in sorted(path for path in DATA.iterdir() if (path / "drawing.pdf").exists()):
    page = load_page(part / "drawing.pdf")
    raw = [(span.text, span.value) for span in page.spans if span.value is not None]
    primitives, spans = perceive.perceive(page, reader=None)
    values = [span.value for span in spans]
    labels = json.loads((part / "labels.json").read_text())
    layout = json.loads((part / "sheet-layout.json").read_text())
    summary[part.name] = {
        "text_layer_numbers": len(raw),
        "text_layer_values": [value for _text, value in raw],
        "kept": len(spans),
        "kept_values": values,
        "missing_values": sorted({value for _text, value in raw} - set(values)),
        "verdict": scale.verdict(spans)["state"],
    }
    print(f"{part.name}: text layer {len(raw)} sayı, kapıdan geçen {len(spans)}")
    print("   text layer:", [f"{text}={value:g}" for text, value in raw][:24])
    print("   kayıtlar  :", [f"{value:g}" for value in values])
    print("   eksik     :", sorted({value for _text, value in raw} - set(values)))
    print("   labels keys:", list(labels)[:10])
    print("   layout keys:", list(layout)[:10])

(OUT / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT / "coverage.json")
