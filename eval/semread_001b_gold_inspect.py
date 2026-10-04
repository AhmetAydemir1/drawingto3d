"""Gold yazımı için gözlem tablosu dökümü (PLAN-6 §21 / P3).

Her sayfa için `observation_table(observe(...))` çıktısını JSON olarak diske yazar ve hangi
gözlem kimliklerinin gold için ilgi çekici olduğunu (çağrı metinleri, daireler) özetler.
Gold-src spec'i bu kimliklerle yazılır; bölge çevirisi `semread_001b_gold_regions.py` yapar.

Kullanım:

    .venv/bin/python eval/semread_001b_gold_inspect.py --page dev-drawing-2
    .venv/bin/python eval/semread_001b_gold_inspect.py --page dev-drawing-2 --texts
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_candidate_reader import observation_table  # noqa: E402

CORPUS = ROOT / "out/lab/semread-001b/corpus"
CALL_PATTERN = re.compile(r"(?:Ø|R|⌀)\s*\d|THRU|M\d|\d+\s*[x×]\s*(?:Ø|M)")


def page_source(page_id: str) -> dict:
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_goldinsp",
                                                  ROOT / "eval" / "semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise SystemExit("pilot modülü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return next(page for page in module.PAGES if page["page_id"] == page_id)
    except StopIteration:
        raise SystemExit(f"PAGES içinde yok: {page_id}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description="gözlem tablosu dökümü (gold için)")
    parser.add_argument("--page", required=True)
    parser.add_argument("--out", default=None,
                        help="JSON çıktı yolu (varsayılan: corpus/observations/<page>.json)")
    parser.add_argument("--texts", action="store_true", help="tüm metin satırlarını yazdır")
    args = parser.parse_args()

    page = page_source(args.page)
    rows = observation_table(observe(ROOT / page["path"]))
    target = Path(args.out) if args.out else (CORPUS / "observations" / f"{args.page}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"page_id": args.page, "source": page["path"], "rows": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")

    texts = [row for row in rows if row.get("kind") == "text"]
    circles = [row for row in rows if row.get("kind") in ("circle", "arc")]
    # Çağrı metinleri tabloda `text` dışında `linear`/`diameter`/`radius` türüyle de gelir (ölçülmüş
    # değer + birim taşırlar); gold yazarken hepsi gerekir. `diameter`/`radius` türü kendi başına
    # çağrıdır — metni yalnız sayıdır ("20"), Ø/R işareti metin alanında **yoktur**.
    calls = [row for row in rows
             if row.get("kind") in ("diameter", "radius")
             or (row.get("kind") in ("text", "linear")
                 and CALL_PATTERN.search(row.get("text") or ""))]
    print(f"{args.page}: {len(rows)} gözlem ({len(texts)} metin, {len(circles)} daire) → {target}")
    print(f"\nçağrı benzeri metinler ({len(calls)}):")
    for row in calls:
        text = (row.get("text") or "").replace("\n", " ")
        region = [round(value, 1) for value in row["region"]]
        print(f"  {row['id']:>6} {row['kind']:<8} {region}  değer={row.get('value')} "
              f"{row.get('unit') or ''}  {text}")
    if args.texts:
        print(f"\ntüm metinler ({len(texts)}):")
        for row in texts:
            text = (row.get("text") or "").replace("\n", " ")
            region = [round(value, 1) for value in row["region"]]
            print(f"  {row['id']:>6} {region}  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
