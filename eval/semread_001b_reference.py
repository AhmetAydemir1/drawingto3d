"""SEMREAD-001B — yazar notasyonundan doğrulanmış referans (gold) üretir.

Girdi (`out/lab/semread-001b/corpus/gold-src/<page_id>.json`) **kısa biçim**tir: bölgeler pafta
pikselinde verilir, script bunları normalize eder ve `check_reference` ile denetleyip
`gold/<page_id>.json` yazar. Böylece normalize koordinat elle hesaplanmaz.

Her claim iki kanıt alanı taşır:

* `evidence`        : claim'i neye dayanarak yazdığım (insan okuması cümlesi).
* `source_evidence` : `pdf-text-layer` (çizimin **kendi** metni), `vision` (görsel inceleme) ya da
  `tesseract+vision` (rasterda önce OCR, sonra görsel doğrulama). Rasterlarda OCR tek başına
  referans kaynağı sayılmaz: `vision` alanı zorunludur, aksi hâlde claim `unverified` işaretlenir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def _png_size(payload: bytes) -> tuple[int, int]:
    """PNG başlığından genişlik/yükseklik (IHDR). OCR/render yapmadan frame ölçüsü verir."""
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("beklenen biçim PNG değil")
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    return width, height


CORPUS = ROOT / "out/lab/semread-001b/corpus"
SRC_DIR = CORPUS / "gold-src"
GOLD_DIR = CORPUS / "gold"
REFERENCE_SCHEMA = "semread-001b-reference/1"


def _normalise(bbox_px, frame_px) -> dict:
    x, y, w, h = (float(value) for value in bbox_px)
    width, height = (float(value) for value in frame_px)
    region = {"x0": max(0.0, x / width), "y0": max(0.0, y / height),
              "x1": min(1.0, (x + w) / width), "y1": min(1.0, (y + h) / height)}
    return {key: round(value, 5) for key, value in region.items()}


def expand(page_id: str, short: dict) -> dict:
    frame_px = short.get("frame_px")
    if not frame_px:
        png = CORPUS / "pages" / f"{page_id}.png"
        if not png.exists():
            raise SystemExit(f"{page_id}: frame_px yok ve {png} bulunamadı")
        width, height = _png_size(png.read_bytes())
        frame_px = [width, height]
    claims = []
    for index, raw in enumerate(short.get("claims") or [], start=1):
        claim = {
            "claim_id": raw.get("claim_id") or f"{page_id}-{index:02d}",
            "target": {"name": raw.get("name") or f"hedef-{index}",
                       "region": _normalise(raw["target_bbox_px"], frame_px),
                       "observation_id": raw.get("observation_id")},
            "callout": ({"region": _normalise(raw["callout_bbox_px"], frame_px)}
                        if raw.get("callout_bbox_px") else None),
            "representation": raw.get("representation", "unknown"),
            "physical": raw.get("physical", "unknown"),
            "form": raw.get("form", "unknown"),
            "size": raw.get("size"),
            "unit": raw.get("unit"),
            "count_printed": raw.get("count_printed"),
            "termination": raw.get("termination", "unknown"),
            "depth": raw.get("depth"),
            "depth_state": raw.get("depth_state", "not_stated"),
            "state": raw.get("state", "determinate_present"),
            "evidence": raw.get("evidence") or "EKSİK: gerekçe yazılmadı",
            "source_evidence": raw.get("source_evidence") or "EKSİK",
        }
        if claims and claim["claim_id"] in {row["claim_id"] for row in claims}:
            raise SystemExit(f"{page_id}: tekrarlanan claim_id {claim['claim_id']}")
        claims.append(claim)
    if short.get("page_type") == "raster":
        for claim in claims:
            if "vision" not in str(claim["source_evidence"]):
                claim["review_flag"] = ("rasterda OCR tek başına yeterli değil: görsel doğrulama "
                                        "yapılmadı")
    return {
        "schema": REFERENCE_SCHEMA, "page_id": page_id, "split": short.get("split"),
        "annotator": "agent", "review_status": "provisional",
        "annotation_method": short.get("annotation_method", "deterministic metin katmanı + görsel"),
        "vision_checked": bool(short.get("vision_checked")),
        "frame_px": frame_px,
        "scope": short.get("scope") or "EKSİK: kapsam yazılmadı",
        "exhaustiveness": short.get("exhaustiveness") or "EKSİK: hangi bölgeler tarandı",
        "claims": claims,
        "notes": short.get("notes") or [],
    }


def build(page_id: str) -> Path:
    source = SRC_DIR / f"{page_id}.json"
    if not source.exists():
        raise SystemExit(f"kaynak yok: {source}")
    short = json.loads(source.read_text(encoding="utf-8"))
    reference = expand(page_id, short)
    target = GOLD_DIR / f"{page_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="kısa notasyondan gold üret")
    parser.add_argument("--page", action="append", help="sayfa kimliği (tekrarlanabilir)")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.all:
        pages = sorted(path.stem for path in SRC_DIR.glob("*.json"))
    else:
        pages = args.page or []
    if not pages:
        raise SystemExit("--page ya da --all ver")
    for page_id in pages:
        print("yazıldı:", build(page_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
