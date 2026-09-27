"""The candidate crops of a sheet, each labelled by the sheet's own text layer.

    PYTHONPATH=src .venv/bin/python eval/candidates.py --out out/candidates/candidates.jsonl

On a vector sheet the printed numbers are known exactly — the PDF's text layer carries each one with its
box — and the raster reader can be run over the same sheet with that layer thrown away. So every candidate the
reader is offered has a label that no one had to draw: does this box sit on a printed number, or is it ink the
drawing put there for another reason (an arrowhead, an arc, a circle, a piece of a line)?

That is the question the section 7 measurement left open. On `Exercise 17` the gate accepted 30 candidates and
28 of them were not printed numbers, and the guard's place test could not separate them because their boxes
stand 7.5-39 px off the line's axis. This produces the labelled set for that question, with features measured
from the crop itself, and prints how far apart the two classes sit on each one — which is the measurement that
decides whether a rule can do it or a trained classifier has to.

The split is by part group, never by crop: crops from one sheet are not independent samples.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import lines, perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402

CASES = json.loads((ROOT / "eval" / "cases.json").read_text())
CASES = CASES["cases"] if isinstance(CASES, dict) else CASES


def _match(candidate: tuple[float, float, float, float], truth: list[tuple[float, float, float, float]]) -> bool:
    """Does this candidate box sit on a printed number?

    The reader's box is built from the same printed ink the text layer describes, so they agree to within a
    few pixels; a candidate that merely passes near a number is not that number. Judged on the candidate's
    centre lying inside the truth box and the two boxes overlapping by at least half the candidate's area.
    """
    cx, cy = (candidate[0] + candidate[2]) / 2, (candidate[1] + candidate[3]) / 2
    area = max(1.0, (candidate[2] - candidate[0]) * (candidate[3] - candidate[1]))
    for box in truth:
        if not (box[0] <= cx <= box[2] and box[1] <= cy <= box[3]):
            continue
        left, top = max(candidate[0], box[0]), max(candidate[1], box[1])
        right, bottom = min(candidate[2], box[2]), min(candidate[3], box[3])
        if right > left and bottom > top and (right - left) * (bottom - top) / area >= 0.5:
            return True
    return False


def _holes(binary: np.ndarray, box: tuple[float, float, float, float]) -> tuple[int, float]:
    """How many holes the ink inside this box has, and the largest one's share of the box.

    A printed digit has at most two small counters (a 0, an 8); a drawn circle is one big hole and an arc is
    the piece of one. This is the shape half of the question, and it is measured on the ink rather than on the
    text mask so that a hollow arrow drawn in outline reads as the hollow mark it is.
    """
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1, y1 = min(binary.shape[1], int(box[2]) + 1), min(binary.shape[0], int(box[3]) + 1)
    crop = binary[y0:y1, x0:x1]
    if crop.size == 0:
        return 0, 0.0
    contours, hierarchy = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return 0, 0.0
    area = float(crop.shape[0] * crop.shape[1]) or 1.0
    interior = [cv2.contourArea(contours[index]) for index, parent in enumerate(hierarchy[0]) if parent[3] != -1]
    if not interior:
        return 0, 0.0
    return len(interior), max(interior) / area


def features(gray: np.ndarray, binary: np.ndarray, text_mask: np.ndarray, glyphs, cluster, anchors, mode) -> dict:
    box = perceive._cluster_box(glyphs, cluster)
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1, y1 = min(binary.shape[1], int(box[2]) + 1), min(binary.shape[0], int(box[3]) + 1)
    width, height = max(1, x1 - x0), max(1, y1 - y0)
    crop = binary[y0:y1, x0:x1]
    fills = []
    for index in cluster:
        glyph = glyphs[index]
        patch = text_mask[glyph.y : glyph.y + glyph.h, glyph.x : glyph.x + glyph.w]
        if patch.size:
            fills.append(float(patch.mean()) / 255.0)
    border = float(np.count_nonzero(crop[0, :]) + np.count_nonzero(crop[-1, :])
                   + np.count_nonzero(crop[:, 0]) + np.count_nonzero(crop[:, -1]))
    hole_count, hole_share = _holes(binary, box)
    across, along, reach = 0.0, 0.0, 0.0
    if anchors and len(anchors) >= 2:
        (ax, ay), (bx, by) = anchors[0], anchors[1]
        dx, dy = bx - ax, by - ay
        length = float(np.hypot(dx, dy)) or 1.0
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        across = abs((cx - ax) * dy - (cy - ay) * dx) / length
        projection = ((cx - ax) * dx + (cy - ay) * dy) / length
        along = min(abs(projection), abs(projection - length))
        reach = float(max(width, height))
    return {
        "w": width, "h": height,
        "aspect": round(max(width, height) / min(width, height), 3),
        "glyphs": len(cluster),
        "fill_mean": round(statistics.fmean(fills), 3) if fills else 0.0,
        "fill_min": round(min(fills), 3) if fills else 0.0,
        "ink_density": round(float(crop.mean()) / 255.0, 3),
        "border_ink": border,
        "border_per_side": round(border / (2 * (width + height)), 3),
        "holes": hole_count,
        "hole_share": round(hole_share, 3),
        "across_px": round(across, 1),
        "along_px": round(along, 1),
        "reach_px": round(reach, 1),
        "anchor_mode": mode,
        "anchors": bool(anchors),
    }


def candidates_for(case: dict) -> list[dict]:
    sheet = ROOT / case["drawing"]
    page = load_page(sheet)
    if not page.vector_text:
        return []
    truth = [
        (float(span.bbox.x), float(span.bbox.y), float(span.bbox.x + span.bbox.w), float(span.bbox.y + span.bbox.h))
        for span in page.spans
        if span.value is not None
    ]
    # The same sheet, read the way a scan has to be: the text layer is thrown away and the reader has to find
    # the numbers in the pixels.
    page.spans = []
    page.vector_text = False
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = lines.ink(gray)
    segments = lines.thin_segments(binary)
    text_mask = perceive._text_mask(gray)
    glyphs = perceive._glyphs(gray, text_mask)
    sizes = [max(glyph.w, glyph.h) for glyph in glyphs if not glyph.separator]
    median_side = float(np.median(sizes)) if sizes else 0.0
    gate = perceive._DimensionGate(binary, segments, text_mask, gray=gray, text_height=median_side or None)

    rows: list[dict] = []
    for mode in ("center", "gap"):
        for cluster in perceive._cluster_glyphs(glyphs, mode):
            if not 1 <= len(cluster) <= 8:
                continue
            box = perceive._cluster_box(glyphs, cluster)
            accepted, anchors, anchor_mode = gate.accepts(box, perceive._printed_block(glyphs, cluster))
            if not accepted:
                continue
            row = features(gray, binary, text_mask, glyphs, cluster, anchors, anchor_mode)
            row.update({
                "case": case["id"],
                "part_group": case.get("part_group") or case["id"],
                "sheet": case["drawing"],
                "box": [round(box[0]), round(box[1]), round(box[2]), round(box[3])],
                "size_vs_sheet": round(max(row["w"], row["h"]) / median_side, 3) if median_side else 0.0,
                "label": 1 if _match(box, truth) else 0,
            })
            rows.append(row)
    return rows


def separability(rows: list[dict], keys: list[str]) -> None:
    positive = [row for row in rows if row["label"] == 1]
    negative = [row for row in rows if row["label"] == 0]
    print(f"\ncandidates {len(rows)}: sayı {len(positive)}, sayı değil {len(negative)}")
    print(f"   {'özellik':<18} {'sayı (ortanca)':>16} {'değil (ortanca)':>16} {'ayrık?':>8}")
    for key in keys:
        if not positive or not negative:
            continue
        one = statistics.median(row[key] for row in positive)
        zero = statistics.median(row[key] for row in negative)
        spread = statistics.pstdev([row[key] for row in rows]) or 1.0
        separated = abs(one - zero) / spread
        print(f"   {key:<18} {one:>16.3f} {zero:>16.3f} {separated:>8.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "out" / "candidates" / "candidates.jsonl"))
    parser.add_argument("--cases", default="")
    arguments = parser.parse_args()
    wanted = [name for name in arguments.cases.split(",") if name]
    rows: list[dict] = []
    for case in CASES:
        if wanted and case["id"] not in wanted:
            continue
        if not (ROOT / case["drawing"]).is_file():
            continue
        found = candidates_for(case)
        if not found:
            print(f"{case['id']:<20} vektör metin katmanı yok — atlandı")
            continue
        positives = sum(row["label"] for row in found)
        print(f"{case['id']:<20} aday {len(found):<4} basılı sayı {positives:<4} "
              f"(kesinlik {positives / len(found):.2f})")
        rows.extend(found)
    out = Path(arguments.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"\nyazıldı: {out} ({len(rows)} aday)")
    separability(rows, ["w", "h", "aspect", "glyphs", "fill_mean", "fill_min", "ink_density",
                        "border_per_side", "holes", "hole_share", "size_vs_sheet",
                        "across_px", "along_px"])


if __name__ == "__main__":
    main()
