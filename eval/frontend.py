"""What the reading front end finds, measured without asking a model.

    PYTHONPATH=src .venv/bin/python eval/frontend.py              # every case that has a sheet
    PYTHONPATH=src .venv/bin/python eval/frontend.py pdf          # one case by id or file substring

Writes out/frontend/<case id>.json and prints one row per case. This is the cheap half of the reading
question and it runs in seconds on a vector sheet: `perceive` (glyph geometry, dimension lines, the PDF's
own text layer) plus tesseract where OCR is needed. The vision model is not called here at all — the
minute-per-crop model reading is `eval/baseline.py`, and keeping the two apart is what makes it possible
to tell a geometry change from model noise.

Per case it reports, against the numbers a human reads on the sheet (eval/cases.json):
  spans      numbers the front end found, with and without the two ends of a dimension line
  covers     printed numbers those spans account for   (the coverage that matters)
  missing    printed numbers nothing was found for
  noise      spans whose value is printed nowhere on the sheet
  px_per_mm  the sheet's own scale, fitted from its dimension lines, and the spread of that fit
  suspect    readings whose own line does not agree with that scale (a misread, or a number attached to
             a line that was never its own)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import scale as sheet_scale  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive  # noqa: E402

CASES = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]
OUT = ROOT / "out" / "frontend"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    arguments = [arg.lower() for arg in sys.argv[1:]]
    # `--as-raster` throws away a PDF's own text layer and reads the sheet the way a scan or a phone
    # photo has to be read: glyph geometry, dimension lines, OCR. On a sheet whose printed numbers are
    # known exactly, that measures the CV reader against the truth without a model and without a second
    # hand-drawn eval sheet.
    as_raster = "--as-raster" in arguments
    wanted = [arg for arg in arguments if not arg.startswith("--")]
    chosen = [case for case in CASES if _wanted(case, wanted) and (ROOT / case["drawing"]).is_file()]
    if not chosen:
        print("eşleşen pafta yok; eval/cases.json ve dosya yollarını kontrol et")
        raise SystemExit(1)
    rows = [_case(case, as_raster=as_raster) for case in chosen]
    for row in rows:
        suffix = "-raster" if as_raster else ""
        (OUT / f"{row['id']}{suffix}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    _print(rows)
    print(f"\nyazıldı: {OUT}")


def _wanted(case: dict, wanted: list[str]) -> bool:
    if not wanted:
        return True
    return any(word in case["id"].lower() or word in Path(case["drawing"]).name.lower() for word in wanted)


def _case(case: dict, as_raster: bool = False) -> dict:
    sheet = ROOT / case["drawing"]
    start = time.time()
    page = load_page(sheet)
    if as_raster and page.vector_text:
        page.spans = []
        page.vector_text = False
    _primitives, spans = perceive(page)
    valued = [span for span in spans if span.value is not None]
    printed = [float(value) for value in case["printed"]]
    callouts = [_squash(item) for item in case.get("callouts") or []]

    found: list[float] = []
    noise: list[dict] = []
    named: list[str] = []
    for span in valued:
        hit = next((value for value in printed if _same(span.value, value)), None)
        if hit is not None:
            if hit not in found:
                found.append(hit)
            continue
        if any(callout.startswith(_squash(span.text)) for callout in callouts):
            named.append(span.text)
            continue
        noise.append({"text": span.text, "value": span.value, "unit": span.unit, "kind": span.kind.value})

    calibration, suspect = sheet_scale.audit(valued)
    return {
        "id": case["id"],
        "class": case["class"],
        "sheet": case["drawing"],
        "vector_text": page.vector_text,
        "printed": printed,
        "unit": case["unit"],
        "spans": [
            {
                "text": span.text,
                "value": span.value,
                "unit": span.unit,
                "kind": span.kind.value,
                "source": span.source.value,
                "anchors": len(span.anchors),
                "anchor_mode": span.anchor_mode,
                "bbox": [round(span.bbox.x), round(span.bbox.y), round(span.bbox.w), round(span.bbox.h)],
            }
            for span in valued
        ],
        "print_units": sorted({span.unit for span in valued}),
        "refused": len(spans) - len(valued),
        "covers": sorted(found),
        "missing": sorted(set(printed) - set(found)),
        "noise": noise,
        "callouts": named,
        "calibration": None
        if calibration is None
        else {"px_per_mm": round(calibration.px_per_mm, 3), "samples": calibration.samples, "spread": round(calibration.spread, 4)},
        "suspect": suspect,
        "seconds": round(time.time() - start, 1),
    }


def _squash(text: str) -> str:
    """`2X 1 1/4` and `2x11/4` are the same callout."""
    return re.sub(r"[^0-9a-z]", "", text.lower())


def _same(value: float | None, printed: float) -> bool:
    """Span values keep the sheet's own unit, so this compares printed number with printed number."""
    if value is None:
        return False
    return abs(float(value) - printed) <= max(1e-6, 0.001 * abs(printed))


def _print(rows: list[dict]) -> None:
    header = f"{'vaka':<18} {'kaynak':<8} {'span':<5} {'basılı':<7} {'kapsam':<7} {'eksik':<28} {'gürültü':<22} {'ankraj':<7} {'px/mm':<8} {'şüpheli'}"
    print(header)
    for row in rows:
        anchored = sum(1 for span in row["spans"] if span["anchors"] == 2)
        calibration = row["calibration"] or {}
        covered = f"{len(row['covers'])}/{len(row['printed'])}"
        missing = ", ".join(f"{value:g}" for value in row["missing"]) or "-"
        noise = ", ".join(f"{item['text']}->{item['value']:g}" for item in row["noise"]) or "-"
        px = f"{calibration.get('px_per_mm', 0):g}" if calibration else "-"
        source = "vektör" if row["vector_text"] else "raster"
        print(
            f"{row['id']:<18} {source:<8} {len(row['spans']):<5} {len(row['printed']):<7} {covered:<7} "
            f"{missing:<28} {noise:<22} {anchored:<7} {px:<8} {len(row['suspect'])}"
        )
    print("\nkapı öncesi/sonrası kapsam, vaka vaka:")
    for row in rows:
        print(f"  {row['id']:<18} kapsam {len(row['covers'])}/{len(row['printed'])}  çağrı {', '.join(row['callouts']) or '-'}  süre {row['seconds']} sn")


if __name__ == "__main__":
    main()
