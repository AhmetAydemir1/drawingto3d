"""Fit a raster sheet's own scale from its numbers and the lines they sit on, with no model.

    PYTHONPATH=src .venv/bin/python eval/raster_scale.py [case-id ...]

A dimension line is drawn between the two points it measures, so a printed number divided into the
length of the line it sits on is the sheet's pixels-per-millimetre. On a vector sheet that pairing
comes from the text layer's anchors; on a raster there are no anchors yet, so this probe pairs each
numeric phrase with every nearby stroke and lets `scale.consensus` decide: the scale most pairs agree
on is the sheet's, and the pairs that fit it are the numbers that have their own dimension line. The
rest are named — a number whose nearby lines all disagree with the sheet's own scale is a misread or
a mispairing, which is what the vector path calls a suspect reading.

A render of a vector sheet is the check that this means anything: its true scale is the vector
sheet's own px/mm times the render factor (dpi / 72), and the probe prints both.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.scale import consensus  # noqa: E402

MIN_LINE_PX = 15.0
GAP_FACTORS = (1.2, 2.0)
MODES = ("nearest:1.2", "nearest:2.0", "row")


def row_candidates(observations, text_height: float) -> list[dict]:
    """Pair each number with the span of the row it sits in, the way the drawing lays a row out.

    The nearest-stroke pairing above only sees a line the number stands *on*. The sheets print the
    number in the line's own gap (rule 13/30: a span is a pair of crossings), so on six of seven
    raster sheets it produced five pairs or fewer and no fit — `exercise-51` gave 5 for 4 numbers,
    `studycadcam-50` 2 for 2. Here a row is the set of strokes that lie on one line (within a tenth of
    the sheet's own text height), its gaps are the merged spans of those strokes, and a number's
    candidates are the pair of gap ends it sits between, plus the span of the gap that contains it.
    """
    strokes = []
    for primitive in observations.primitives:
        if primitive.kind != "line" or not primitive.start or not primitive.end:
            continue
        a = np.array(primitive.start, dtype=float)
        b = np.array(primitive.end, dtype=float)
        if float(np.linalg.norm(b - a)) >= max(2.0, 0.15 * text_height):
            strokes.append((primitive.id, a, b))
    rows: list[dict] = []
    for geometry_id, a, b in strokes:
        direction = (b - a) / float(np.linalg.norm(b - a))
        placed = False
        for row in rows:
            if abs(float(np.dot(row["direction"], direction))) < 0.999:
                continue
            if (abs(float(np.dot(a - row["origin"], row["normal"]))) > 0.1 * text_height
                    or abs(float(np.dot(b - row["origin"], row["normal"]))) > 0.1 * text_height):
                continue
            row["strokes"].append((geometry_id, a, b))
            placed = True
            break
        if not placed:
            rows.append({"origin": a, "direction": direction,
                         "normal": np.array([-direction[1], direction[0]]), "strokes": [(geometry_id, a, b)]})
    merge = 0.25 * text_height
    for row in rows:
        spans = sorted((float(np.dot(a - row["origin"], row["direction"])),
                        float(np.dot(b - row["origin"], row["direction"])), geometry_id)
                       for geometry_id, a, b in row["strokes"])
        merged: list[list] = []
        for low, high, geometry_id in spans:
            low, high = min(low, high), max(low, high)
            if merged and low - merged[-1][1] <= merge:
                merged[-1][1] = max(merged[-1][1], high)
                merged[-1][2].append(geometry_id)
            else:
                merged.append([low, high, [geometry_id]])
        row["gaps"] = merged
    rows = [row for row in rows if len(row["gaps"]) >= 2]
    found = []
    for text in observations.texts:
        if text.value is None or text.kind != "linear" or text.bbox.w <= 0 or text.bbox.h <= 0:
            continue
        centre = np.array([text.bbox.x + text.bbox.w / 2, text.bbox.y + text.bbox.h / 2])
        for row in rows:
            along = float(np.dot(centre - row["origin"], row["direction"]))
            off = abs(float(np.dot(centre - row["origin"], row["normal"])))
            if off > 2.0 * text_height:
                continue
            ends = []
            for index, (low, high, ids) in enumerate(row["gaps"]):
                if index:
                    ends.append((row["gaps"][index - 1][1], low, row["gaps"][index - 1][2] + ids))
                ends.append((low, high, ids))
            for low, high, ids in ends:
                length = high - low
                if length < max(2.0, 0.15 * text_height):
                    continue
                if abs(along - (low + high) / 2) > length / 2 + text.bbox.h:
                    continue
                found.append({"text_id": text.id, "text": text.text, "value": float(text.value),
                              "line_id": "+".join(dict.fromkeys(ids)), "length_px": round(length, 1),
                              "gap_px": round(off, 1), "px_per_mm": round(length / float(text.value), 4)})
    return found


def candidates(observations, gap_factor: float) -> list[dict]:
    """Every (numeric phrase, nearby stroke) pairing, with the ratio it would imply."""
    lines = [(primitive.id, np.array(primitive.start, dtype=float), np.array(primitive.end, dtype=float))
             for primitive in observations.primitives
             if primitive.kind == "line" and primitive.start and primitive.end]
    rows = []
    for text in observations.texts:
        if text.value is None or text.kind != "linear" or text.bbox.w <= 0 or text.bbox.h <= 0:
            continue
        centre = np.array([text.bbox.x + text.bbox.w / 2, text.bbox.y + text.bbox.h / 2])
        reach = gap_factor * max(float(text.bbox.h), 1.0)
        for geometry_id, a, b in lines:
            delta = b - a
            length = float(np.linalg.norm(delta))
            if length < MIN_LINE_PX:
                continue
            along = float(np.dot(centre - a, delta)) / (length ** 2)
            if not -0.15 <= along <= 1.15:
                continue
            gap = float(np.linalg.norm(centre - (a + along * delta)))
            if gap > reach:
                continue
            rows.append({"text_id": text.id, "text": text.text, "value": float(text.value),
                         "line_id": geometry_id, "length_px": round(length, 1),
                         "gap_px": round(gap, 1), "px_per_mm": round(length / float(text.value), 4)})
    return rows


def expected_scale(case_id: str) -> dict | None:
    """A render of a vector sheet has a known scale: the vector sheet's, times dpi / 72."""
    for stem in (case_id.replace("-raster", ""),):
        vector = ROOT / "out" / "frontend" / f"{stem}.json"
        if not vector.exists():
            return None
        record = json.loads(vector.read_text())
        calibration = record.get("calibration")
        px_per_mm = calibration.get("px_per_mm") if isinstance(calibration, dict) else None
        return {"from": f"{stem} (vektör)", "px_per_mm": px_per_mm}


def text_height(observations) -> float:
    """The sheet's own type size: the median height of its numeric phrases."""
    heights = [float(text.bbox.h) for text in observations.texts
               if text.value is not None and text.bbox.h > 0]
    return float(np.median(heights)) if heights else 0.0


def report(observations, mode: str) -> dict:
    if mode == "row":
        rows = row_candidates(observations, text_height(observations))
    else:
        rows = candidates(observations, float(mode.split(":")[1]))
    pairs = [(row["value"], row["length_px"]) for row in rows]
    calibration, inliers = consensus(pairs)
    inlier_rows = [rows[index] for index in inliers]
    numbers = {row["text_id"] for row in rows}
    rejections = []
    if calibration is not None:
        # A dimension line cannot be longer than the sheet it is drawn on, so a hypothesis that
        # implies the sheet's largest printed value is bigger than the page's own diagonal is not
        # this sheet's scale. Flange measured this: the loose pairing fitted 81.85 and 143.67 px/mm,
        # where 90 mm would be 7 367 px on a 3 300 x 2 550 sheet.
        diagonal = float(np.hypot(observations.frame.width, observations.frame.height))
        largest = max((value for value, _length in pairs), default=0.0)
        if largest * calibration.px_per_mm > 0.95 * diagonal:
            rejections.append(f"en büyük basılı değer ({largest} mm) sayfadan uzun olurdu "
                              f"({round(largest * calibration.px_per_mm)} px > {round(diagonal)} px)")
        found = {row["text_id"] for row in inlier_rows}
        if len(found) < 3:
            rejections.append(f"uyum yalnız {len(found)} sayıdan geldi (en az 3 sayı gerekir)")
    return {
        "numbers": len(numbers),
        "candidate_pairs": len(rows),
        "fit": ({"px_per_mm": round(calibration.px_per_mm, 4), "samples": calibration.samples,
                 "spread": round(calibration.spread, 4)} if calibration else None),
        "rejections": rejections,
        "inlier_rows": inlier_rows,
        "unpaired_numbers": sorted(numbers - {row["text_id"] for row in inlier_rows}),
    }


def main() -> int:
    argv = [item for item in sys.argv[1:] if not item.startswith("--")]
    manifest = json.loads((ROOT / "eval" / "cases.json").read_text())
    cases = [case for case in manifest["cases"] if case["id"] in argv] if argv else manifest["cases"]
    for case in cases:
        drawing = Path(case["drawing"])
        if drawing.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        observations = observe(str(ROOT / case["drawing"]))
        rows = [(mode, report(observations, mode)) for mode in MODES]
        for mode, row in rows:
            fit = row["fit"]
            line = (f"{case['id']:22s} {mode:11s} sayı={row['numbers']:3d} "
                    f"aday={row['candidate_pairs']:3d} ")
            if fit and not row["rejections"]:
                line += (f"ölçek={fit['px_per_mm']} px/mm ({fit['samples']} uyum, "
                         f"yayılım {fit['spread']})")
            elif fit:
                line += f"ölçek REDDEDİLDİ ({fit['px_per_mm']} px/mm): " + "; ".join(row["rejections"])
            else:
                line += "ölçek KURULAMADI (en az 3 uyum yok)"
            print(line)
        good = [row for _factor, row in rows if row["fit"] and not row["rejections"]]
        if good:
            print(f"{'':22s} uyan sayılar: "
                  + ", ".join(f"{r['text']!r}={r['value']}→{r['line_id']}({r['length_px']}px)"
                              for r in good[0]["inlier_rows"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
