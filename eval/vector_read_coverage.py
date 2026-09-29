"""The vector side of the same question: does `read` account for every printed dimension?

The raster sheet loses numbers at the gate. On a sheet with a text layer the numbers are exact, so the
question there is only which of them the gate anchors — this measures that for every v2 part, with no
model call (the role question answers `edge`).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.reason import reason_drawing  # noqa: E402
from drawingto3d.reason import sheet_scale  # noqa: E402

DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/iterations/vector-read-coverage"
OUT.mkdir(parents=True, exist_ok=True)


class StubReader:
    def ask(self, image_png, prompt):
        return "edge"


summary = {}
for part in sorted(path for path in DATA.iterdir() if path.is_dir()):
    drawing = part / "drawing.png"
    if not drawing.exists():
        drawing = part / "drawing.pdf"
    if not drawing.exists():
        continue
    try:
        result = reason_drawing(drawing, OUT / part.name, coder=None, reader=StubReader())
    except Exception as exc:  # a refusal is a result too, and it is recorded as one
        summary[part.name] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        print(f"{part.name}: {summary[part.name]['error']}")
        continue
    rows = [r.model_dump() for r in result.records]
    sheet = sheet_scale(result.page)
    summary[part.name] = {"records": len(rows), "rows": rows, "scale": sheet}
    print(f"{part.name}: {len(rows)} kayıt, ölçek={sheet['state']}")
    for row in rows:
        print("    ", row)

(OUT / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT / "coverage.json")
