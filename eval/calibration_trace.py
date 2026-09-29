"""calibration-trace/1 — her basılı sayının hangi çizgiye bağlandığını ve nerede elendiğini izler.

S02 teşhisi: bir pafta kendi ölçeğini kendi ölçü çizgilerinden ölçer, bu yüzden "kaç ölçü kaldı"
sorusu tek başına anlamsızdır — hangi sayının hangi çizgiye bağlandığı, bağlanmadıysa nerede
elendiği ve bağlandığı çizginin gerçekten o sayının çizgisi olup olmadığı ayrı ayrı görünmelidir.

Bu araç ürün kodunu değiştirmez; `perceive → scale.measure → consensus` zincirini çağırır ve her
kararın girdisini (satır, ok uçları, kesişen uzatma çizgileri, uçlar, gerekçe) kayda geçirir.
Ayrıca her pafta için `overlays/<parça>.png` üretir: tutulan sayılar, elenen sayılar, seçilen uçlar
ve satırın kendi ok uçları üst üste çizilir.

Kullanım:
    .venv/bin/python eval/calibration_trace.py --corpus out/lab/data/v2 \
        --out out/lab/calibration-checkpoint
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import lines, scale  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402
from drawingto3d.perceive import perceive  # noqa: E402

TRACE_SCHEMA = "drawingto3d.calibration-trace/1"
ARROW_STEPS = 8


def _box(span) -> tuple[float, float, float, float]:
    return (span.bbox.x, span.bbox.y, span.bbox.x + span.bbox.w, span.bbox.y + span.bbox.h)


def _row_diagnostics(gray: np.ndarray, binary: np.ndarray, segments, span) -> dict:
    """A span'ın satırında gerçekte ne olduğu: aday çizgiler, ok uçları, kesişmeler, karar."""
    box = _box(span)
    reading_across, size, text_span, text_offset, reach, near = lines._row_near(box, segments)
    row = [segment for segment in near
           if abs(lines._row_offset(segment, reading_across) - text_offset) <= 1.2 * size]
    candidates = []
    for segment in row:
        candidates.append({
            "extent": [lines._row_start(segment, reading_across), lines._row_end(segment, reading_across)],
            "length_px": round(lines._row_end(segment, reading_across) - lines._row_start(segment, reading_across), 3),
            "offset": round(lines._row_offset(segment, reading_across), 3),
            "arrow_at_start": lines.arrow_steps(binary, segment, 0),
            "arrow_at_end": lines.arrow_steps(binary, segment, 1),
            "arrowed_both_ends": (lines.arrow_steps(binary, segment, 0) >= ARROW_STEPS
                                  and lines.arrow_steps(binary, segment, 1) >= ARROW_STEPS),
        })
    arrowed = [row[index] for index, candidate in enumerate(candidates) if candidate["arrowed_both_ends"]
               and lines._row_start(row[index], reading_across) - 0.2 * size <= text_span[0]
               and text_span[1] <= lines._row_end(row[index], reading_across) + 0.2 * size]
    row_span = (min(lines._row_start(segment, reading_across) for segment in row),
                max(lines._row_end(segment, reading_across) for segment in row)) if row else (0.0, 0.0)
    crossings = lines._crossings(segments, reading_across, text_offset, row_span, size)
    along = 0 if reading_across else 1
    spanning = []
    for first, second in lines.crossing_pairs(segments, box):
        low, high = sorted((float(first[along]), float(second[along])))
        spanning.append([round(low, 3), round(high, 3)])
    chosen = [float(span.anchors[0][0 if reading_across else 1]), float(span.anchors[1][0 if reading_across else 1])]

    def _matches(extent) -> bool:
        return abs(min(chosen) - min(extent)) <= 2.0 and abs(max(chosen) - max(extent)) <= 2.0

    if any(_matches(candidate["extent"]) and candidate["arrowed_both_ends"] for candidate in candidates):
        decision = "arrowed_line"
    elif any(_matches(extent) for extent in spanning):
        decision = "crossing_pair"
    else:
        decision = "unexplained"
    return {
        "reading_across": reading_across, "text_size_px": round(size, 3),
        "text_span": [round(text_span[0], 3), round(text_span[1], 3)],
        "row_offset": round(text_offset, 3), "reach_px": round(reach, 3),
        "candidates": candidates,
        "arrowed_candidates_that_bracket_the_text": [
            {"extent": [round(lines._row_start(segment, reading_across), 3),
                        round(lines._row_end(segment, reading_across), 3)],
             "offset": round(lines._row_offset(segment, reading_across), 3)} for segment in arrowed],
        "crossings": [round(value, 3) for value in crossings],
        "span_pairs_the_row_offers": spanning,
        "selected_ends": [round(chosen[0], 3), round(chosen[1], 3)],
        "decision": decision,
    }


def _consensus_rows(pairs: list[tuple[float, float]]) -> dict:
    rows = {}
    for minimum in (2, 3, 4):
        calibration, inliers = scale.consensus(pairs, minimum=minimum)
        rows[str(minimum)] = {
            "calibration": asdict(calibration) if calibration else None,
            "inliers": inliers,
            "implied_px_per_mm": [round(measured / value, 4) for value, measured in pairs
                                  if value > 0 and measured > 0],
        }
    return rows


def _row_facts(gray: np.ndarray, binary: np.ndarray, segments, span) -> dict | None:
    """Bir sayının satırında ölçülen gerçekler — uçlar seçilmeden.

    `_row_diagnostics` ile aynı ölçümler, ama `span.anchors`'a bakmaz: eleme nedenini zincirin *seçtiği*
    uçlara değil, satırda duran mürekkebe bakarak yazabilmek için ayrıldı.
    """
    box = _box(span)
    reading_across, size, text_span, text_offset, reach, near = lines._row_near(box, segments)
    row = [segment for segment in near
           if abs(lines._row_offset(segment, reading_across) - text_offset) <= 1.2 * size]
    candidates = []
    for segment in row:
        start = lines._row_start(segment, reading_across)
        end = lines._row_end(segment, reading_across)
        candidates.append({"extent": [round(start, 3), round(end, 3)],
                           "offset": round(lines._row_offset(segment, reading_across), 3),
                           "arrow_at_start": lines.arrow_steps(binary, segment, 0),
                           "arrow_at_end": lines.arrow_steps(binary, segment, 1)})
    arrowed = [candidate for candidate in candidates
               if candidate["arrow_at_start"] >= ARROW_STEPS and candidate["arrow_at_end"] >= ARROW_STEPS
               and candidate["extent"][0] - 0.2 * size <= text_span[0]
               and text_span[1] <= candidate["extent"][1] + 0.2 * size]
    row_span = (min(candidate["extent"][0] for candidate in candidates),
                max(candidate["extent"][1] for candidate in candidates)) if candidates else (0.0, 0.0)
    crossings = lines._crossings(segments, reading_across, text_offset, row_span, size) if candidates else []
    along = 0 if reading_across else 1
    spanning = []
    for first, second in lines.crossing_pairs(segments, box):
        low, high = sorted((float(first[along]), float(second[along])))
        spanning.append([round(low, 3), round(high, 3)])
    return {"reading_across": reading_across, "text_size_px": round(size, 3),
            "text_span": [round(text_span[0], 3), round(text_span[1], 3)],
            "row_offset": round(text_offset, 3), "reach_px": round(reach, 3),
            "candidates": candidates, "arrowed_lines_that_bracket_the_text": arrowed,
            "crossings": [round(value, 3) for value in crossings],
            "span_pairs_the_row_offers": spanning}


def _why_dropped(span, facts: dict | None) -> str:
    """Elenen sayının nedeni: satırda ölçülen gerçeklerden, tahminden değil."""
    if facts is None:
        return "değer okunamadı (sayı olarak ayrıştırılamadı)"
    if str(span.kind) in {"SpanKind.diameter", "SpanKind.radius"}:
        return ("çağrı ölçüsü (Ø/R): çapa/yarıçapa bağlanır, uçları anket edilmediği için "
                "kalibrasyon çifti olarak kullanılmaz")
    if not facts["candidates"]:
        return "satırda aday çizgi yok: sayının yanında ölçü çizgisi bulunamadı"
    if not facts["reading_across"]:
        return "satır dikey okunuyor: sayının satırı yatay değil"
    if not facts["crossings"]:
        return ("satırda kesişme yok: sayı bir ölçü çizgisinin üstünde değil "
                f"(aday={len(facts['candidates'])}, ok uçlu={len(facts['arrowed_lines_that_bracket_the_text'])})")
    if len(facts["crossings"]) < 2:
        return (f"satır tek kesişme veriyor ({len(facts['crossings'])}): çiftin öteki ucu bulunamadı "
                f"(ok uçlu aday={len(facts['arrowed_lines_that_bracket_the_text'])})")
    if not facts["span_pairs_the_row_offers"]:
        return f"kesişme var ({len(facts['crossings'])}) ama iki kesişimi birleştiren çift kurulamadı"
    return "satır çift sunuyor ama zincir bu sayıyı okumadı (bağlama aşamasında düştü)"


def trace_part(part_dir: Path) -> dict:
    drawing = part_dir / "drawing.pdf"
    page = load_page(drawing)
    # `perceive` `page.spans`'ı yerinde daraltıyor: basılı sayıların tam listesi ondan **önce** alınır,
    # yoksa "algılayıcı bu sayıyı hiç okumadı" diye bir katman kalmaz ve eleme sessizce kaybolur.
    original = list(page.spans)
    printed = [{"id": span.id, "text": span.text, "value": span.value, "kind": str(span.kind),
                "bbox": {"x": span.bbox.x, "y": span.bbox.y, "w": span.bbox.w, "h": span.bbox.h}}
               for span in original]
    _, spans = perceive(page)
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = lines.ink(gray)
    segments = lines.thin_segments(binary)

    kept = []
    for span in spans:
        record = {
            "id": span.id, "text": span.text, "value": span.value, "kind": str(span.kind),
            "anchor_mode": span.anchor_mode, "anchors": [list(point) for point in span.anchors],
            "view": getattr(span, "view_id", None),
            "length_px": round(scale.line_length(span), 3) if len(span.anchors) == 2 else None,
        }
        if len(span.anchors) == 2 and span.value:
            record["implied_px_per_mm"] = round(record["length_px"] / float(span.value), 4)
        if span.anchor_mode == "dimension" and len(span.anchors) == 2:
            record["row"] = _row_diagnostics(gray, binary, segments, span)
        kept.append(record)

    pairs = scale.measure(spans)
    fits = _consensus_rows(pairs)
    # Kimlik düzeyinde iz: katmanlar `span.id` ile eşleştirilir, metnin kendisiyle değil. Aynı sayı
    # paftada iki kez basılıysa metin eşleştirmesi ikisini birden "tutuldu" sayardı. İki ayrı eleme
    # katmanı var ve karıştırılmamalı: (a) algılayıcı sayıyı hiç okumamış, (b) okumuş ama bağlayamamış.
    perceived_ids = {span.id for span in spans}
    perceived = [{"id": span.id, "text": span.text, "anchor_mode": span.anchor_mode,
                  "anchors": [list(point) for point in span.anchors]} for span in spans]
    kept_ids = {record["id"] for record in kept}
    dropped = []
    for span in original:
        if span.id in perceived_ids or span.value is None:
            continue
        facts = _row_facts(gray, binary, segments, span)
        dropped.append({"id": span.id, "text": span.text, "value": span.value, "kind": str(span.kind),
                        "bbox": {"x": span.bbox.x, "y": span.bbox.y, "w": span.bbox.w, "h": span.bbox.h},
                        "row": facts, "reason": _why_dropped(span, facts)})
    unbound = []
    for span in spans:
        if span.id in kept_ids or span.value is None:
            continue
        facts = _row_facts(gray, binary, segments, span)
        unbound.append({"id": span.id, "text": span.text, "value": span.value, "kind": str(span.kind),
                        "anchor_mode": span.anchor_mode,
                        "anchors": [list(point) for point in span.anchors],
                        "reason": _why_dropped(span, facts)})
    return {
        "part": part_dir.name, "drawing": str(drawing.relative_to(ROOT)),
        "printed_numbers": printed,
        "perceived": perceived,
        "kept": kept,
        "dropped_by_the_gate": dropped,
        "perceived_but_not_bound": unbound,
        "calibration_pairs": [[value, round(measured, 3)] for value, measured in pairs],
        "fits": fits,
        "view_scales": scale.view_scales(spans),
    }


def draw_overlay(source_png: Path, target_png: Path, printed: list[dict], kept: list[dict]) -> bool:
    """Paftanın üzerine: basılı sayılar, elenenler, seçilen uçlar ve satırın ok uçları."""
    if source_png is None or not source_png.exists():
        return False
    image = cv2.imread(str(source_png), cv2.IMREAD_COLOR)
    if image is None:
        return False
    height, width = image.shape[:2]
    kept_texts = {row["text"] for row in kept}
    for row in printed:
        bbox = row["bbox"]
        if row["value"] is None:
            continue
        kept_row = row["text"] in kept_texts
        colour = (60, 160, 60) if kept_row else (40, 40, 220)   # kept green, dropped red
        cv2.rectangle(image, (int(bbox["x"]), int(bbox["y"])),
                      (int(bbox["x"] + bbox["w"]), int(bbox["y"] + bbox["h"])), colour, 2)
        if not kept_row:
            cv2.putText(image, "ELENDI", (int(bbox["x"]), int(bbox["y"]) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)
    for row in kept:
        anchors = row.get("anchors") or []
        if len(anchors) != 2:
            continue
        (x0, y0), (x1, y1) = anchors
        cv2.line(image, (int(x0), int(y0)), (int(x1), int(y1)), (200, 120, 0), 3)
        for x, y in ((x0, y0), (x1, y1)):
            cv2.circle(image, (int(x), int(y)), 6, (0, 215, 255), -1)
        if row.get("row"):
            for candidate in row["row"]["arrowed_candidates_that_bracket_the_text"]:
                start, end = candidate["extent"]
                offset = candidate["offset"]
                horizontal = row["row"]["reading_across"]
                a = (int(start), int(offset)) if horizontal else (int(offset), int(start))
                b = (int(end), int(offset)) if horizontal else (int(offset), int(end))
                cv2.line(image, a, b, (255, 0, 255), 2)
        caption = f"{row['text']} -> {row.get('length_px')}px"
        if row.get("implied_px_per_mm"):
            caption += f" ({row['implied_px_per_mm']} px/mm)"
        cv2.putText(image, caption, (int(anchors[0][0]), int(anchors[0][1]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 120, 0), 2)
    cv2.putText(image, "yesil: tutulan sayi  kirmizi: elenen  sari: secilen uc  mor: ok uclari",
                (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
    cv2.putText(image, "yesil: tutulan sayi  kirmizi: elenen  sari: secilen uc  mor: ok uclari",
                (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    target_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(target_png), image)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Ölçü/ankraj eşleşme izini çıkarır (S02).")
    parser.add_argument("--corpus", type=Path, default=ROOT / "out/lab/data/v2")
    parser.add_argument("--out", type=Path, default=ROOT / "out/lab/calibration-checkpoint")
    parser.add_argument("--part", action="append", default=None)
    args = parser.parse_args()

    overlays = args.out / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    parts = []
    for part_dir in sorted(path for path in args.corpus.iterdir() if path.is_dir()):
        if args.part and part_dir.name not in args.part:
            continue
        if not (part_dir / "drawing.pdf").exists():
            continue
        row = trace_part(part_dir)
        target = overlays / f"{part_dir.name}.png"
        drawn = draw_overlay(part_dir / "drawing.png", target, row["printed_numbers"], row["kept"])
        # `--out` deponun dışındaysa `relative_to` patlıyordu: araç, kanıtı yazdığı hâlde düşüyordu.
        # Yol ya depoya göre yazılır ya da olduğu gibi; ikisi de geçerli kanıt.
        if drawn:
            try:
                row["overlay"] = str(target.relative_to(ROOT))
            except ValueError:
                row["overlay"] = str(target)
        else:
            row["overlay"] = None
        parts.append(row)
        print(f"--- {row['part']}: tutulan={len(row['kept'])} elenen={len(row['dropped_by_the_gate'])} "
              f"çift={row['calibration_pairs']}", flush=True)
        for fit_minimum, fit in row["fits"].items():
            state = "var" if fit["calibration"] else "yok"
            print(f"    minimum={fit_minimum}: {state} inliers={fit['inliers']} "
                  f"px/mm={fit['implied_px_per_mm']}", flush=True)

    payload = {"schema": TRACE_SCHEMA, "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "version_note": "S02 teşhis aracı; ürün kodunu değiştirmez. Eski calibration-probe.py "
                               "kanıt olarak korunur (proje kökünü yanlış bulur), bu araç kökü "
                               "eval/ konumundan bulur.",
               "parts": parts}
    target = args.out / "calibration-trace.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"yazıldı: {target}")


if __name__ == "__main__":
    main()
