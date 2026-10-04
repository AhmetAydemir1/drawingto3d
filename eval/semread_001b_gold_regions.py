"""Gold-src bölge çevirici: gözlem tablosundan pafta pikseline (elle hesap yok).

Neden var: referans (`gold-src/<page_id>.json`) kısa biçimi bölgeleri **pafta pikselinde** ister,
`semread_001b_reference.py` bunları normalize eder. Piksel kutularını elle yazmak hem yavaş hem
hataya açıktır; bu araç hedef bölgeyi gözlem tablosundaki (`observation_table(observe(...))`)
geometriden, çağrı kutusunu da çağrı metinlerinin birleşiminden üretir.

Kullanım:

    .venv/bin/python eval/semread_001b_gold_regions.py --page dev-plate-pocket --spec /tmp/x.json
    .venv/bin/python eval/semread_001b_gold_regions.py --page dev-plate-pocket --spec /tmp/x.json --write

Spec (JSON) alanları:

    {
      "page_type": "pdf" | "raster",
      "scope": "...", "notes": ["..."],
      "exhaustiveness": {"scope": "predicates", "predicates": [...]} |
                        {"scope": "regions", "regions": [[x0,y0,x1,y1], ...]} |
                        {"scope": "full_page"},
      "claims": [
        {"claim_id": "...", "name": "...",
         "target_observation": "g12",          # hedef bölge bu gözlemden
         "callout_texts": ["t3", "t4", "t5"],  # çağrı kutusu bu metinlerin birleşimi
         "representation": "circle", "physical": "hole", "form": "diameter",
         "size": 6.8, "unit": "mm", "count_printed": 4, "termination": "thru",
         "depth": null, "depth_state": "not_stated", "state": "determinate_present",
         "evidence": "...", "source_evidence": "pdf-text-layer + vision"}
      ]
    }

`--write` olmadan yalnız özet yazar (hesaplanan kutular + doğrulama uyarıları): önce bak, sonra yaz.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_candidate_reader import observation_table  # noqa: E402

CORPUS = ROOT / "out/lab/semread-001b/corpus"
GOLD_SRC = CORPUS / "gold-src"


def _png_size(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path} PNG değil")
    return (int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big"))


def page_source(page_id: str) -> dict:
    """Pilotun PAGES tablosundan sayfayı okur (kaynak yol, tür, split)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("semread_001b_pilot_gold",
                                                  ROOT / "eval" / "semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise SystemExit("pilot modülü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return next(page for page in module.PAGES if page["page_id"] == page_id)
    except StopIteration:
        raise SystemExit(f"PAGES içinde yok: {page_id}") from None


def build(page_id: str, spec: dict) -> tuple[dict, list[str]]:
    page = page_source(page_id)
    rows = observation_table(observe(ROOT / page["path"]))
    by_id = {row["id"]: row for row in rows}
    width, height = _png_size(CORPUS / "pages" / f"{page_id}.png")
    warnings: list[str] = []

    def px(region: list[float]) -> list[float]:
        x0, y0, x1, y1 = (float(value) for value in region)
        return [round(x0 * width, 1), round(y0 * height, 1),
                round((x1 - x0) * width, 1), round((y1 - y0) * height, 1)]

    def union(ids: list[str]) -> list[float]:
        boxes = []
        for name in ids:
            if name not in by_id:
                raise SystemExit(f"{page_id}: bilinmeyen gözlem kimliği {name}")
            boxes.append(by_id[name]["region"])
        return [min(box[0] for box in boxes), min(box[1] for box in boxes),
                max(box[2] for box in boxes), max(box[3] for box in boxes)]

    claims = []
    for index, raw in enumerate(spec.get("claims") or [], start=1):
        target = raw.get("target_observation")
        if not target:
            raise SystemExit(f"claim #{index}: target_observation yok")
        callout = raw.get("callout_texts") or []
        claim = {
            "claim_id": raw.get("claim_id") or f"{page_id}-{index:02d}",
            "name": raw.get("name") or f"hedef-{index}",
            "target_bbox_px": px(by_id[target]["region"]),
            "observation_id": target,
            "representation": raw.get("representation", "unknown"),
            "physical": raw.get("physical", "unknown"),
            "form": raw.get("form", "unknown"),
            "size": raw.get("size"),
            "unit": raw.get("unit", "mm"),
            "count_printed": raw.get("count_printed"),
            "termination": raw.get("termination", "unknown"),
            "depth": raw.get("depth"),
            "depth_state": raw.get("depth_state", "not_stated"),
            "state": raw.get("state", "determinate_present"),
            "evidence": raw.get("evidence") or "",
            "source_evidence": raw.get("source_evidence") or "",
        }
        if callout:
            claim["callout_bbox_px"] = px(union(callout))
        if not claim["evidence"]:
            warnings.append(f"{claim['claim_id']}: evidence boş — kapı reddeder (§13)")
        if not claim["source_evidence"]:
            warnings.append(f"{claim['claim_id']}: source_evidence boş — kapı reddeder (§13)")
        if spec.get("page_type") == "raster" and "vision" not in claim["source_evidence"].lower():
            warnings.append(f"{claim['claim_id']}: raster sayfada `vision` kanıtı yok (§16)")
        claims.append(claim)

    document = {
        "page_type": spec.get("page_type") or page.get("type"),
        "split": spec.get("split") or page.get("split"),
        "frame_px": [width, height],
        "vision_checked": bool(spec.get("vision_checked")),
        "scope": spec.get("scope") or "",
        "exhaustiveness": spec.get("exhaustiveness") or {},
        "annotation_method": spec.get("annotation_method")
        or "gözlem tablosu (paftanın kendi metni/geometrisi) + görsel doğrulama",
        "notes": spec.get("notes") or [],
        "claims": claims,
    }
    if document["page_type"] == "raster" and not document["vision_checked"]:
        warnings.append("raster sayfa: gold-src'de vision_checked=true yazılmalı (§16)")
    for field, label in (("scope", "kapsam"), ("exhaustiveness", "exhaustiveness")):
        if not document[field]:
            warnings.append(f"{label} boş — kapı reddeder (§13)")
    return document, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="gold-src bölge çevirici")
    parser.add_argument("--page", required=True)
    parser.add_argument("--spec", required=True, help="spec JSON yolu")
    parser.add_argument("--write", action="store_true", help="gold-src dosyasını yaz")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    document, warnings = build(args.page, spec)
    for claim in document["claims"]:
        print(f"{claim['claim_id']}: hedef px {claim['target_bbox_px']} "
              f"callout px {claim.get('callout_bbox_px')}")
    for warning in warnings:
        print("UYARI:", warning)
    target = GOLD_SRC / f"{args.page}.json"
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        print("yazıldı:", target)
    else:
        print("(yazılmadı; görmek için --write)")
    return 0 if not warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
