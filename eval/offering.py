"""Where a printed number stops when the sheet is read as pixels: which step never offered it.

    PYTHONPATH=src .venv/bin/python eval/offering.py --verbose plate-pocket-1 exercise-1-vector

The section 7 run says a scanned sheet is read at 6/13, 4/14, 2/8 and 4/13, and that on those sheets the scale
never fits because too few numbers come out: most printed numbers are never offered to the reader at all. A
classifier can only drop a candidate; it cannot summon one that was never offered, which is why this is
measured before anything is trained.

The instrument is the vector sheet's own rendering. The same page answers both halves in one frame: the text
layer says exactly where every printed number sits, and the pixel path is asked to find it without ever being
told. No scale has to be fitted between two drawings, and nothing is assumed about a scan. (An earlier form of
this tool tried to align a part's raster against its vector sheet and the fit refused to close — `7/my_part.jpg`
and `2/Drawing.pdf` are the same part drawn on two different sheets, not one drawing at two sizes.)

For each printed number the four answers are named, and they are four different jobs:

    blob yok          the ink never became a glyph — thresholding or blob sizing, upstream of everything
    küme kurulmadı    glyphs were found but never joined into a candidate — the chaining distance
    kapı reddetti     a candidate existed and the gate would not keep it — anchors
    okuyucu okumadı   a candidate reached the reader and it read nothing — the reader or the crop

A rendering is not a scan: no skew, no blur, no sensor noise. So a number lost here is lost to the pipeline
itself, which puts an upper bound on what any scan of the same sheet could be read at and names the step to fix.
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

from drawingto3d import lines, perceive  # noqa: E402
from drawingto3d.ingest import load_page  # noqa: E402

CASES = json.loads((ROOT / "eval" / "cases.json").read_text())
CASES = CASES["cases"] if isinstance(CASES, dict) else CASES


def overlap(box: tuple[float, float, float, float], other: tuple[float, float, float, float]) -> float:
    left, top = max(box[0], other[0]), max(box[1], other[1])
    right, bottom = min(box[2], other[2]), min(box[3], other[3])
    if right <= left or bottom <= top:
        return 0.0
    smaller = min((box[2] - box[0]) * (box[3] - box[1]), (other[2] - other[0]) * (other[3] - other[1])) or 1.0
    return (right - left) * (bottom - top) / smaller


def pixel_page(case: dict):
    """The same sheet with its text layer thrown away: pixels only, the way a scan has to be read."""
    page = load_page(ROOT / case["drawing"])
    page.spans = []
    page.vector_text = False
    return page, cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)


def diagnose(case: dict, verbose: bool) -> dict:
    vector_page = load_page(ROOT / case["drawing"])
    if not vector_page.vector_text:
        print(f"{case['id']:<20} vektör metin katmanı yok — atlandı")
        return {}
    manifest = {float(value) for value in case.get("printed", [])}
    height = float(vector_page.height)
    truth = [span for span in vector_page.spans
             if span.value is not None and float(span.value) in manifest
             and span.bbox.y >= 0 and span.bbox.y + span.bbox.h <= height]
    if not truth:
        print(f"{case['id']:<20} metin katmanında manifest sayıları bulunamadı — atlandı")
        return {}

    page, image = pixel_page(case)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = lines.ink(gray)
    segments = lines.thin_segments(binary)
    text_mask = perceive._text_mask(gray)
    glyphs = perceive._glyphs(gray, text_mask)
    sizes = [max(glyph.w, glyph.h) for glyph in glyphs if not glyph.separator]
    text_size = float(np.median(sizes)) if sizes else 0.0
    gate = perceive._DimensionGate(binary, segments, text_mask, gray=gray, text_height=text_size or None)
    clusters: list[tuple[list[int], tuple[float, float, float, float], bool, str]] = []
    for mode in ("center", "gap"):
        for cluster in perceive._cluster_glyphs(glyphs, mode):
            if not 1 <= len(cluster) <= 8:
                continue
            box = perceive._cluster_box(glyphs, cluster)
            accepted, _anchors, anchor_mode = gate.accepts(box, perceive._printed_block(glyphs, cluster))
            clusters.append((cluster, box, accepted, anchor_mode))

    _primitives, found = perceive.perceive(page)
    read = [(float(span.value or -1), float(span.bbox.x), float(span.bbox.y),
             float(span.bbox.x + span.bbox.w), float(span.bbox.y + span.bbox.h)) for span in found]

    steps = {"okundu": 0, "blob yok": 0, "küme kurulmadı": 0, "kapı reddetti": 0, "okuyucu okumadı": 0}
    print(f"\n{case['id']}  ({case['drawing']})")
    print(f"  basılı {len(truth)} kutu, okuyucudan çıkan {len(found)} span, glif {len(glyphs)}, "
          f"kapının kabul ettiği küme {sum(1 for entry in clusters if entry[2])}")
    if verbose:
        print(f"  {'sayı':>6} {'glif':>5} {'küme':>5} {'kapı':>9} {'okuma':>7}  adım")
    for span in sorted(truth, key=lambda item: (float(item.value or 0), float(item.bbox.y))):
        value = float(span.value or 0.0)
        box = (float(span.bbox.x), float(span.bbox.y),
               float(span.bbox.x + span.bbox.w), float(span.bbox.y + span.bbox.h))
        inside = [glyph for glyph in glyphs
                  if overlap((float(glyph.x), float(glyph.y), float(glyph.x + glyph.w), float(glyph.y + glyph.h)),
                             box) >= 0.5]
        covering = [entry for entry in clusters if overlap(entry[1], box) >= 0.5]
        accepted = [entry for entry in covering if entry[2]]
        read_here = [entry for entry in read if overlap((entry[1], entry[2], entry[3], entry[4]), box) >= 0.5]
        if read_here:
            step = "okundu"
        elif not inside:
            step = "blob yok"
        elif not covering:
            step = "küme kurulmadı"
        elif not accepted:
            step = "kapı reddetti"
        else:
            step = "okuyucu okumadı"
        steps[step] += 1
        if verbose:
            verdict = accepted[0][3] if accepted else (covering[0][3] if covering else "-")
            best = f"{read_here[0][0]:.0f}" if read_here else "-"
            print(f"  {value:>6.0f} {len(inside):>5} {len(covering):>5} {verdict:>9} {best:>7}  {step}")
            if step == "okuyucu okumadı":
                entry = accepted[0]
                asked = perceive._read_cluster(gray, glyphs, entry[0], 0, anchors=None, mode=entry[3])
                print(f"          okuyucuya sorulan kırpma: {asked.text if asked else '(okuma yok)'}")
    print(f"  adım dağılımı: {steps}")
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="vaka kimlikleri; boşsa vektör katmanı olan hepsi")
    parser.add_argument("--verbose", action="store_true", help="her basılı sayı için satır satır döküm")
    arguments = parser.parse_args()
    wanted = set(arguments.cases)
    total = {"okundu": 0, "blob yok": 0, "küme kurulmadı": 0, "kapı reddetti": 0, "okuyucu okumadı": 0}
    for case in CASES:
        if wanted and case["id"] not in wanted:
            continue
        for key, value in diagnose(case, arguments.verbose).items():
            total[key] += value
    if sum(total.values()):
        print("\ntoplam " + ", ".join(f"{key} {value}" for key, value in total.items() if value))


if __name__ == "__main__":
    main()
