"""Reading baseline: run the reader over the eval sheets and keep exactly what it produced.

    PYTHONPATH=src .venv/bin/python eval/baseline.py              # every case that has a sheet
    PYTHONPATH=src .venv/bin/python eval/baseline.py exercise-1   # one case by id (or a substring)

Writes out/baseline/<case id>.json for eval/report.py. Nothing is corrected here: the point is to
measure the reader as it is, including the failures, and to time it. Needs the vision model (Ollama).

This is the step that costs minutes: the reader asks the model one closed question per dimension
text, so a 17-dimension sheet is 17 local model calls.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from drawingto3d.reason import reason_drawing

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]
OUT = ROOT / "out" / "baseline"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = [arg.lower() for arg in sys.argv[1:]]
    chosen = [case for case in CASES if _wanted(case, wanted) and (ROOT / case["drawing"]).is_file()]
    if not chosen:
        print("eşleşen pafta yok; eval/cases.json ve dosya yollarını kontrol et")
        raise SystemExit(1)
    for case in chosen:
        _run(case)
    print(f"\nyazıldı: {OUT}")


def _wanted(case: dict, wanted: list[str]) -> bool:
    if not wanted:
        return True
    return any(word in case["id"].lower() or word in Path(case["drawing"]).name.lower() for word in wanted)


def _run(case: dict) -> None:
    sheet = ROOT / case["drawing"]
    start = time.time()
    print(f"--- {case['id']} ({sheet.name}) ---", flush=True)
    try:
        result = reason_drawing(
            sheet,
            ROOT / "out" / "baseline" / case["id"],
            progress=lambda title, detail: print(f"    {title}: {detail}", flush=True),
        )
        payload = {
            "case": case["id"],
            "sheet": case["drawing"],
            "seconds": round(time.time() - start, 1),
            "error": None,
            "records": [record.model_dump(mode="json") for record in result.records],
            "views": [
                {"kind": view.kind.value, "w": view.bbox.w, "h": view.bbox.h, "used": view.used_for_solid}
                for view in (result.page.views if result.page else [])
            ],
            "spans": [
                {"text": span.text, "value": span.value, "kind": span.kind.value, "source": span.source.value}
                for span in (result.page.spans if result.page else [])
            ],
        }
    except Exception as exc:  # noqa: BLE001 - a baseline records the failure, it does not raise
        payload = {"case": case["id"], "sheet": case["drawing"], "seconds": round(time.time() - start, 1), "error": f"{type(exc).__name__}: {exc}"}
    (OUT / f"{case['id']}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    count = len(payload.get("records") or [])
    print(f"    -> {count} kayıt, {payload['seconds']} sn, hata={payload['error']}", flush=True)


if __name__ == "__main__":
    main()
