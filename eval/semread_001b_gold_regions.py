"""Gold-src bölge çevirici: gözlem tablosundan pafta pikseline (elle hesap yok).

Neden var: referans (`gold-src/<page_id>.json`) kısa biçimi bölgeleri **pafta pikselinde** ister,
`semread_001b_reference.py` bunları normalize eder. Piksel kutularını elle yazmak hem yavaş hem
hataya açıktır; bu araç hedef bölgeyi gözlem tablosundaki (`observation_table(observe(...))`)
geometriden, çağrı kutusunu da çağrı metinlerinin birleşiminden üretir.

Kullanım:

    .venv/bin/python eval/semread_001b_gold_regions.py --page dev-plate-pocket
    .venv/bin/python eval/semread_001b_gold_regions.py --page dev-plate-pocket --write

Spec kaynağı: `--spec` verilmezse **izlenen kanonik** `eval/semread_001b_gold/specs/<page>.json`
aranır (PLAN-8 §3); yoksa eski yerel kopya (`out/lab/.../corpus/gold-specs/`) kullanılır ve bu
durum çıktıda "yerel (out/ altı — izlenmiyor)" olarak yazılır. Kanonik gerçek git'te izlenen
spec'tir; `out/` altındaki üretilmiş dosyalar yeniden üretilebilir çalışma çıktısıdır.

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
         # ya da (raster sayfalarda Hough primitifleri güvenilmezse) görselden ölçülen kutu:
         "target_box_norm": [x0, y0, x1, y1],  # normalize 0..1, sıralı; gerekçe `notes`a
         "callout_texts": ["t3", "t4", "t5"],  # çağrı kutusu bu metinlerin birleşimi
         "representation": "circle", "physical": "hole", "form": "diameter",
         "size": 6.8, "unit": "mm", "count_printed": 4, "termination": "thru",
         "depth": null, "depth_state": "not_stated", "state": "determinate_present",
         "evidence": "...", "source_evidence": "pdf-text-layer + vision"}
      ]
    }

`--write` olmadan yalnız özet yazar (hesaplanan kutular + doğrulama uyarıları): önce bak, sonra yaz.
Ölçülen kutu kullanıldığında çıkış kodu 1'dir (uyarı var) — bilinçli: gold gözle onaylanmadan
yazılmamalı.
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
    width, height = _png_size(CORPUS / "pages" / f"{page_id}.png")
    warnings: list[str] = []
    # Gözlem tablosu **tembel** yüklenir (PLAN-8 §3): hedefi `target_box_norm` olan spec'ler
    # OCR/Hough çalıştırmadan üretilebilir, böylece kanonik spec'ten yeniden üretim hızlı ve
    # deterministiktir; gözlem kimliği kullanan claim'ler için çıkarım yine zorunludur.
    table: dict[str, dict] = {}

    def observation(name: str) -> dict:
        if not table:
            for row in observation_table(observe(ROOT / page["path"])):
                table[row["id"]] = row
        if name not in table:
            raise SystemExit(f"{page_id}: bilinmeyen gözlem kimliği {name}")
        return table[name]

    def px(region: list[float]) -> list[float]:
        x0, y0, x1, y1 = (float(value) for value in region)
        return [round(x0 * width, 1), round(y0 * height, 1),
                round((x1 - x0) * width, 1), round((y1 - y0) * height, 1)]

    def union(ids: list[str]) -> list[float]:
        boxes = [observation(name)["region"] for name in ids]
        return [min(box[0] for box in boxes), min(box[1] for box in boxes),
                max(box[2] for box in boxes), max(box[3] for box in boxes)]

    claims = []
    for index, raw in enumerate(spec.get("claims") or [], start=1):
        target = raw.get("target_observation")
        box = raw.get("target_box_norm")
        if not target and not box:
            raise SystemExit(f"claim #{index}: target_observation ya da target_box_norm yok")
        callout = raw.get("callout_texts") or []
        if box:
            # Raster sayfalarda Hough primitifleri güvenilmez olabilir (uydurma büyük daireler,
            # eksik köşe delikleri): hedef bölge **görselden ölçülen** normalize kutu olarak
            # verilebilir. Gerekçe gold `notes`una yazılmalı; `target_observation` verilirse yalnız
            # iz olarak saklanır (bölge ondan türetilmez).
            if len(box) != 4:
                raise SystemExit(f"claim #{index}: target_box_norm dört sayı olmalı")
            x0, y0, x1, y1 = (float(value) for value in box)
            if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
                raise SystemExit(f"claim #{index}: target_box_norm 0..1 aralığında ve sıralı olmalı "
                                 f"(0<=x0<x1<=1, 0<=y0<y1<=1)")
            target_bbox = px([x0, y0, x1, y1])
            observation_id = target
            warnings.append(f"claim #{index}: hedef bölge ölçülen kutu — gerekçe `notes`ta olmalı")
        else:
            target_bbox = px(observation(target)["region"])
            observation_id = target
        claim = {
            "claim_id": raw.get("claim_id") or f"{page_id}-{index:02d}",
            "name": raw.get("name") or f"hedef-{index}",
            "target_bbox_px": target_bbox,
            "observation_id": observation_id,
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


TRACKED_SPECS = ROOT / "eval" / "semread_001b_gold" / "specs"
LEGACY_SPECS = CORPUS / "gold-specs"


def resolve_spec(page_id: str, explicit: str | None) -> tuple[Path, str]:
    """Spec kaynağını çözer: açık yol → izlenen kanonik dizin → eski (out/ altındaki) dizin.

    Kanonik gerçek `eval/semread_001b_gold/specs/` altındadır (PLAN-8 §3): `out/` gitignored
    olduğu için oradaki kopyalar yalnız yerel çalışma kopyasıdır.
    """
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise SystemExit(f"spec yok: {path}")
        return path, "açık yol"
    tracked = TRACKED_SPECS / f"{page_id}.json"
    if tracked.exists():
        return tracked, "izlenen kanonik"
    legacy = LEGACY_SPECS / f"{page_id}.json"
    if legacy.exists():
        return legacy, "yerel (out/ altı — izlenmiyor)"
    raise SystemExit(f"{page_id}: spec bulunamadı ({tracked} ya da {legacy}) — "
                     f"`--spec` ile yol ver")


def main() -> int:
    parser = argparse.ArgumentParser(description="gold-src bölge çevirici")
    parser.add_argument("--page", required=True)
    parser.add_argument("--spec", help="spec JSON yolu (verilmezse izlenen kanonik spec aranır)")
    parser.add_argument("--write", action="store_true", help="gold-src dosyasını yaz")
    args = parser.parse_args()
    spec_file, source = resolve_spec(args.page, args.spec)
    print(f"spec kaynağı: {spec_file} ({source})")
    spec = json.loads(spec_file.read_text(encoding="utf-8"))
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
