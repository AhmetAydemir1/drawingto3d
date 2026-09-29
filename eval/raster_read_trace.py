"""Raster okumanın izini çıkar: her adayın kırpımı, OCR cevabı, kapısı, ankrajı ve ölçü rolü.

Bu bir teşhis aracıdır, ürün yolu değildir. Raster okuma koşudan koşuya değiştiği ve yanlış bir sayı
("09" gibi) hiçbir yerde basılı olmadığı için "hangi değer nereden geldi" sorusu kanıtla yanıtlanmalı:
kırpım dosyası, o kırpıma verilen her OCR cevabı, kapının kararı ve ankrajın gerçek uzunluğu.

Zincir kopyalanmaz: `drawingto3d.perceive` içindeki gerçek fonksiyonlar sarmalanır, yani burada görülen
şey ürünün çalıştırdığı zincirin kendisidir.

Çıktı (`<out_dir>`):
  `trace.json`    — aday aday zincir: kutu, glif sayısı, kapı kararı, ankraj, denenen her OCR açısı,
                    okunan metin/değer/birim, kırpım yolu, varsa ölçü kaydındaki rolü;
  `overlay.png`   — pafta üzerine çizilmiş adaylar: kayıt olanlar yeşil, reddedilenler turuncu, her
                    kutunun üstünde `#no text=… value=… role=…`; ankrajlar mavi çizgi;
  `crops/*.png`   — OCR'a verilen kırpımın aynısı (kayıt olan adaylar için).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import perceive as perceive_module  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive  # noqa: E402

SCHEMA = "drawingto3d.raster-read-trace/1"


def _key(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 1) for value in box)


def _trace_read(records: dict) -> None:
    """`_read_cluster`ı sarmalar: her aday için denenen açıları ve sonucu kaydeder."""
    original_read = perceive_module._read_cluster
    original_ocr = perceive_module._ocr_upright

    def traced_read(gray, glyphs, cluster, serial, reader=None, anchors=None, mode="dimension",
                    skip=0):
        x0 = min(glyphs[index][2] for index in cluster) - 3
        y0 = min(glyphs[index][3] for index in cluster) - 3
        x1 = max(glyphs[index][2] + glyphs[index][4] for index in cluster) + 3
        y1 = max(glyphs[index][3] + glyphs[index][5] for index in cluster) + 3
        box = (float(x0), float(y0), float(x1), float(y1))
        records["reads"].append(box)
        attempts: list[dict] = []

        def traced_ocr(crop, angle, whitelist):
            text = original_ocr(crop, angle, whitelist)
            attempts.append({"angle": round(float(angle), 2), "whitelist": bool(whitelist),
                             "text": text})
            return text

        perceive_module._ocr_upright = traced_ocr
        try:
            span = original_read(gray, glyphs, cluster, serial, reader, anchors, mode, skip)
        finally:
            perceive_module._ocr_upright = original_ocr
        call = records["by_box"].setdefault(_key(box), {"box": list(box)})
        call.setdefault("reads", []).append({
            "glyphs": len(cluster), "mode": mode, "anchors": anchors, "skip": skip,
            "crop": {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)},
            "attempts": attempts,
            "span": None if span is None else {
                "id": span.id, "text": span.text, "value": span.value, "unit": span.unit,
                "kind": span.kind.value,
                "bbox": [span.bbox.x, span.bbox.y, span.bbox.w, span.bbox.h],
                "anchors": span.anchors, "anchor_mode": span.anchor_mode,
            },
        })
        return span

    perceive_module._read_cluster = traced_read


def _trace_gate(records: dict) -> None:
    """`_DimensionGate.accepts` sarmalar: kabul/ret kararı ve ankraj kanıtı kaybolmasın."""
    original_accepts = perceive_module._DimensionGate.accepts

    def traced_accepts(self, box, block=None):
        accepted, anchors, mode = original_accepts(self, box, block)
        call = records["by_box"].setdefault(_key(box), {"box": [float(v) for v in box]})
        call["gate"] = {"accepted": bool(accepted), "anchor_mode": mode, "anchors": anchors,
                        "block": None if block is None else {"box": [float(v) for v in block[0]],
                                                            "character": float(block[1])}}
        return accepted, anchors, mode

    perceive_module._DimensionGate.accepts = traced_accepts


def _anchor_length(anchors) -> float | None:
    if not anchors or len(anchors) != 2:
        return None
    (x0, y0), (x1, y1) = anchors[0], anchors[1]
    return float(np.hypot(float(x1) - float(x0), float(y1) - float(y0)))


def _records_by_text(records_path: Path | None) -> dict:
    """Ürünün yazdığı ölçü kayıtları: rol ve görünüş `read` adımının kendi çıktısıdır."""
    if records_path is None or not records_path.exists():
        return {}
    raw = json.loads(records_path.read_text(encoding="utf-8"))
    return {str(item.get("span_id") or item.get("text")): item for item in raw}


def _draw(image: np.ndarray, calls: list[dict], fonts: tuple[float, float]) -> np.ndarray:
    canvas = image.copy()
    for call in calls:
        box = call.get("box") or []
        if len(box) != 4:
            continue
        span = call.get("span") or {}
        kept = bool(call.get("span"))
        colour = (60, 170, 60) if kept else (0, 140, 255)
        x0, y0, x1, y1 = [int(round(value)) for value in box]
        cv2.rectangle(canvas, (x0, y0), (x1, y1), colour, 3)
        gate = call.get("gate") or {}
        label = f"#{call.get('index')} text={span.get('text')!r} value={span.get('value')} " \
                f"mode={gate.get('anchor_mode')} role={call.get('product_role')}"
        cv2.putText(canvas, label, (max(0, x0 - 4), max(20, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    fonts[0], colour, 2, cv2.LINE_AA)
        anchors = gate.get("anchors") or []
        if len(anchors) == 2:
            (ax0, ay0), (ax1, ay1) = anchors
            cv2.line(canvas, (int(ax0), int(ay0)), (int(ax1), int(ay1)), (200, 60, 0), 2)
            length = _anchor_length(anchors)
            value = span.get("value")
            if length and value:
                per_mm = length / float(value)
                cv2.putText(canvas, f"{length:.0f}px/{value:g}mm={per_mm:.2f}px/mm",
                            (int(ax0), int((ay0 + ay1) / 2)), cv2.FONT_HERSHEY_SIMPLEX, fonts[1],
                            (200, 60, 0), 2, cv2.LINE_AA)
    return canvas


def _overlap_area(a, b) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    if right <= left or bottom <= top:
        return 0.0
    return float((right - left) * (bottom - top))


def _merge_gate_and_read(entries: list[dict]) -> list[dict]:
    """Kapı kaydı ile okuma kayıtlarını aynı adayda birleştirir.

    Kapı kümeyi kendi kutusuyla sorar, okuma aynı kümeyi 3 px payıyla kırpar; iki kayıt bu yüzden ayrı
    anahtarla düşer. Aynı aday olduklarını kutularının örtüşmesinden anlarız — ankraj (ve dolayısıyla
    ölçek kanıtı) kapı kaydındadır, metin okuma kaydında. Bir kutu için birden çok okuma olabilir
    (ölçek denetimi adayı başka açılardan yeniden okur), o yüzden okumalar liste olarak taşınır.
    """
    gates = [entry for entry in entries if "gate" in entry and "reads" not in entry]
    reads = [entry for entry in entries if "reads" in entry]
    taken: set[int] = set()
    candidates: list[dict] = []
    for entry in reads:
        box = entry["box"]
        best, best_key = None, None
        for gate in gates:
            if id(gate) in taken:
                continue
            area = _overlap_area(box, gate["box"])
            if area <= 0:
                continue
            ranking = (1 if (gate["gate"] or {}).get("accepted") else 0, area)
            if best_key is None or ranking > best_key:
                best, best_key = gate, ranking
        call = {"box": box, "reads": entry["reads"], "gate": entry.get("gate")}
        if best is not None:
            taken.add(id(best))
            call["gate"] = best["gate"]
        candidates.append(call)
    for gate in gates:
        if id(gate) not in taken:
            candidates.append({"box": gate["box"], "gate": gate["gate"], "reads": []})
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drawing", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--records", type=Path, default=None,
                        help="ürünün yazdığı records.json: rol ve görünüş oradan okunur")
    parser.add_argument("--no-crops", action="store_true", help="kırpımları diske yazma")
    args = parser.parse_args()

    page = load_page(args.drawing)
    records: dict = {"reads": [], "attempts": [], "by_box": {}}
    _trace_gate(records)
    _trace_read(records)
    primitives, spans = perceive(page)

    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    height, width = image.shape[:2]
    known = _records_by_text(args.records)

    calls = []
    for call in _merge_gate_and_read(list(records["by_box"].values())):
        reads = call.get("reads") or []
        produced_reads = [read for read in reads if read.get("span")]
        # Ürünün son sözü son okumadır: ölçek denetimi bir adayı başka açıdan yeniden okur ve
        # sonucu yalnız uyuyorsa kabul eder.
        call["span"] = produced_reads[-1]["span"] if produced_reads else None
        call["attempts"] = [attempt for read in reads for attempt in (read.get("attempts") or [])]
        span = call.get("span") or {}
        length = _anchor_length((call.get("gate") or {}).get("anchors"))
        if length is None and span.get("anchors"):
            length = _anchor_length(span.get("anchors"))
        value = span.get("value")
        call["anchor_px"] = length
        call["implied_px_per_mm"] = (length / float(value)) if length and value else None
        produced = known.get(str(span.get("id"))) or {}
        call["product_view_id"] = produced.get("view_id")
        call["product_role"] = produced.get("role")
        calls.append(call)

    calls.sort(key=lambda item: (item["box"][1], item["box"][0]))
    for index, call in enumerate(calls):
        call["index"] = index

    kept = [call for call in calls if call.get("span")]
    implied = [call["implied_px_per_mm"] for call in kept if call.get("implied_px_per_mm")]
    median_scale = float(np.median(implied)) if implied else None
    for call in calls:
        if median_scale and call.get("implied_px_per_mm"):
            call["scale_ratio_vs_median"] = round(call["implied_px_per_mm"] / median_scale, 3)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = args.out_dir / "crops"
    if not args.no_crops:
        crops_dir.mkdir(parents=True, exist_ok=True)
        for call in kept:
            crop = call.get("crop")
            if not crop:
                continue
            piece = image[crop["y0"]:crop["y1"], crop["x0"]:crop["x1"]]
            path = crops_dir / f"{call['span']['id']}.png"
            if piece.size:
                cv2.imwrite(str(path), piece)
            call["crop_file"] = str(path)

    fonts = (max(0.6, width / 4200), max(0.5, width / 5200))
    overlay = _draw(image, calls, fonts)
    overlay_path = args.out_dir / "overlay.png"
    cv2.imwrite(str(overlay_path), overlay)

    payload = {
        "schema": SCHEMA, "drawing": str(args.drawing.resolve()),
        "image": {"width": width, "height": height},
        "records_joined": str(args.records) if args.records else None,
        "candidate_count": len(calls), "kept_count": len(kept),
        "median_implied_px_per_mm": median_scale,
        "view_segmentation": {"views": len(page.views), "note": "raster kolunda görünüş ayrımı yok: "
                               "her adayın `view_id`i boş kalır (kayıtlarda da boş)"},
        "candidates": calls,
        "kept": [{"id": call["span"]["id"], "text": call["span"]["text"],
                  "value": call["span"]["value"], "anchor_mode": call["span"]["anchor_mode"],
                  "role": call.get("product_role"), "view_id": call.get("product_view_id"),
                  "anchor_px": call.get("anchor_px"),
                  "implied_px_per_mm": call.get("implied_px_per_mm"),
                  "scale_ratio_vs_median": call.get("scale_ratio_vs_median")} for call in kept],
        "overlay": str(overlay_path),
    }
    (args.out_dir / "trace.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    print(json.dumps({"trace": str(args.out_dir / "trace.json"), "overlay": str(overlay_path),
                      "candidates": len(calls), "kept": len(kept),
                      "median_implied_px_per_mm": median_scale}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
