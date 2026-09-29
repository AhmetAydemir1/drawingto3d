"""Review5 V03: kapsamı **kimlik** üzerinden ölç — değer kümesi farkı bir kaybı saklıyor.

Önceki araç kayıp sayıyı `set(basılı) - set(kayıt)` ile buluyordu: aynı değer iki konumda basılıysa
birinin kaybı görünmüyordu. Bu araç her basılı sayıyı kendi span kimliği/kutusu üzerinden izler ve
sınıfını ayırır (doğrusal, çap, çağrı/derinlik, adet). `4 x Ø8 THRU` tek bir lineer `4 mm` değildir.

Ayrıca pafta etiketlerinin iddiasını paftanın kendi metin katmanıyla karşılaştırır (V03: "etiket
iddiaları asıl görselle doğrulanmalı"): etiketin dediği metin paftada bulunmuyorsa bu bir bulgudur.

Model çağrısı yok. Girdiler okunur, çıktı `iterations/reading-coverage/coverage.json`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive_with_report  # noqa: E402

DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/iterations/reading-coverage"
OUT.mkdir(parents=True, exist_ok=True)

PHI = "\u00d8"


def klass(text: str) -> str:
    """Sınıf, basılı metnin kendisinden: çap, çağrı (THRU/DEPTH), adet, yoksa doğrusal."""
    if PHI in text:
        return "diameter" if not re.search(r"THRU|DEPTH", text) else "diameter_callout"
    if re.search(r"THRU|DEPTH", text):
        return "callout"
    if re.search(r"\d+\s*[xX]\s*" + PHI, text):
        return "count"
    if text.startswith("R"):
        return "radius"
    return "linear"


def number_in(text: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    return float(match.group(1).replace(",", ".")) if match else None


summary = {}
for part in sorted(path for path in DATA.iterdir() if (path / "drawing.pdf").exists()):
    page = load_page(part / "drawing.pdf")
    raw = [span for span in page.spans if span.value is not None]
    _primitives, spans, report = perceive_with_report(page, reader=None)
    labels = json.loads((part / "labels.json").read_text(encoding="utf-8"))

    kept_ids = list(report.get("kept", []))
    kept_by_id = {span.id: span for span in spans}
    unpaired = report.get("unpaired", [])
    accounted = set(kept_ids) | {row["id"] for row in unpaired}

    rows = {
        "kept": [{"id": span.id, "text": span.text, "value": span.value, "class": klass(span.text),
                  "box": [span.bbox.x, span.bbox.y, span.bbox.w, span.bbox.h]} for span in spans],
        "unpaired": [{"id": row["id"], "text": row["text"], "value": row["value"],
                      "class": klass(row["text"]), "expected_px": row["expected_px"],
                      "resolved": row["resolved"], "candidates": len(row["candidates"])} for row in unpaired],
        "not_accounted": [{"id": span.id, "text": span.text, "value": span.value, "class": klass(span.text)}
                          for span in raw if span.id not in accounted],
    }

    by_class: dict[str, dict[str, int]] = {}
    for name, group in (("kept", rows["kept"]), ("unpaired", rows["unpaired"]),
                        ("not_accounted", rows["not_accounted"])):
        for row in group:
            by_class.setdefault(row["class"], {"kept": 0, "unpaired": 0, "not_accounted": 0})[name] += 1

    # Label claims against the sheet's own text layer: identity here is the printed text itself, compared
    # with whitespace collapsed — the layer splits `15` into `1 5`, and comparing raw strings called three
    # printed numbers "not on the sheet" when they were there (measured on plate-01 and plate-02).
    printed_texts = [" ".join(span.text.split()) for span in raw]
    label_rows = []
    for entry in labels.get("printed_dimensions", []):
        claim = " ".join(str(entry.get("text") or "").split())
        label_rows.append({
            "text": entry.get("text"), "role": entry.get("role"), "value_mm": entry.get("value_mm"),
            "on_sheet": (claim in printed_texts
                         or entry.get("value_mm") in [span.value for span in spans]),
            "class": klass(str(entry.get("text") or "")),
        })

    # What a value-set difference hides: one printed number kept, another with the same value dropped.
    kept_values = [span.value for span in spans]
    hidden = [row for row in unpaired if row["value"] in kept_values]

    summary[part.name] = {
        "path": "text_layer",
        "raw_numbers": len(raw),
        "labels_expected": len(label_rows),
        "kept": len(rows["kept"]),
        "unpaired": len(rows["unpaired"]),
        "not_accounted": len(rows["not_accounted"]),
        "by_class": by_class,
        "rows": rows,
        "labels": label_rows,
        "labels_not_on_sheet": [row["text"] for row in label_rows if not row["on_sheet"]],
        "hidden_by_value_set": [{"id": row["id"], "value": row["value"]} for row in hidden],
        "resolved_candidates": [row["id"] for row in rows["unpaired"] if row["resolved"]],
    }
    print(f"{part.name}: basılı {len(raw)}, etiket {len(label_rows)} | kept {len(rows['kept'])}, "
          f"unpaired {len(rows['unpaired'])}, hesaba girmemiş {len(rows['not_accounted'])}")
    print("   sınıflar:", json.dumps(by_class, ensure_ascii=False))
    print("   aday çözülen:", summary[part.name]["resolved_candidates"])
    print("   etiketi paftada bulunmayan:", summary[part.name]["labels_not_on_sheet"])
    print("   değer farkının sakladığı:", summary[part.name]["hidden_by_value_set"])

(OUT / "coverage.json").write_text(json.dumps(
    {"schema": "drawingto3d.eval.reading-coverage/1",
     "method": "identity (span id + box) based; classes from the printed text; labels checked against the sheet",
     "parts": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", OUT / "coverage.json")
