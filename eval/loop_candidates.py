"""List a sheet's closed loop candidates and what the drawing dimensions, with no model involved.

    PYTHONPATH=src .venv/bin/python eval/loop_candidates.py [case-id ...]

`proposal._outline_of` takes the biggest closed loop that is not the page frame, and the sheet that
made that choice visible refused it: on `exercise-1-vector` the biggest loop is a 3-primitive,
20.54 x 35.95 mm detail view, not the part. This probe prints, per sheet, every non-frame loop with
its size, its primitive count and how many confirmed printed claims are anchored to its own
geometry, so a change to the selection can be judged by whether it moves the right sheets and
leaves the others alone — a rule-based change is still a measurement, not a tidy-up.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.meaning import meaning_page  # noqa: E402
from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.proposal import (_frame_loops, _loop_box, _loops, _primitives,  # noqa: E402
                                 _rounded_rectangle)


def report(path: str) -> dict:
    drawing = Path(path)
    observations = observe(drawing)
    meanings = meaning_page(drawing)
    scale = meanings.sheet_px_per_mm
    lines, arcs, _circles = _primitives(observations)
    loops = _loops(lines, arcs)
    frame = (_frame_loops(loops, observations.frame.width, observations.frame.height)
             if observations.frame else set())
    confirmed = [span for span in meanings.spans if span.resolution == "confirmed" and span.claim]
    circle_ids = {primitive.id for primitive in observations.primitives if primitive.kind == "circle"}
    rows = []
    for index, loop in enumerate(loops):
        ids = {item[0] for item in loop["entities"]}
        touching = []
        section = []
        for span in confirmed:
            claim_ids = {point.geometry_id for point in span.claim.points}
            if claim_ids and claim_ids <= ids:
                touching.append({"span_id": span.span_id, "form": span.claim.form,
                                 "printed_mm": span.claim.printed_mm})
            elif claim_ids and not claim_ids <= circle_ids:
                # A distance that touches neither this loop nor circle centres: the only candidate a
                # general flat-part archetype could read a thickness from.
                section.append({"span_id": span.span_id, "form": span.claim.form,
                                "printed_mm": span.claim.printed_mm})
        (x0, y0), (x1, y1) = _loop_box(loop)
        rows.append({
            "index": index,
            "frame": index in frame,
            "primitives": len(loop["entities"]),
            "box_mm": ([round((x1 - x0) / scale, 2), round((y1 - y0) / scale, 2)] if scale else None),
            "box_px": [round(float(x1 - x0), 1), round(float(y1 - y0), 1)],
            "rounded_rectangle": _rounded_rectangle(loop["entities"], scale) is not None if scale else None,
            "claims_on_loop": touching,
            "section_candidates": section,
        })
    part = [row for row in rows if not row["frame"]]
    chosen = part[0] if part else None
    return {
        "case": drawing.name,
        "px_per_mm": scale,
        "loops": len(loops),
        "frame_loops": len(frame),
        "confirmed_claims": len(confirmed),
        "chosen_now": ({"index": chosen["index"], "primitives": chosen["primitives"],
                        "box_mm": chosen["box_mm"], "claims": len(chosen["claims_on_loop"])}
                       if chosen else None),
        "candidates": part[:6],
    }


def main() -> int:
    argv = sys.argv[1:]
    manifest = json.loads((ROOT / "eval" / "cases.json").read_text())
    cases = manifest["cases"]
    if argv:
        cases = [case for case in cases if case["id"] in argv]
    for case in cases:
        try:
            row = report(str(ROOT / case["drawing"]))
        except Exception as exc:  # a probe reports, it does not fail the sweep
            print(f"{case['id']}: okunamadı: {type(exc).__name__}: {exc}")
            continue
        print(f"\n=== {case['id']} ({case['drawing']}) px/mm={row['px_per_mm']} "
              f"döngü={row['loops']} çerçeve={row['frame_loops']} onaylı iddia={row['confirmed_claims']}")
        print(f"    şimdi seçilen: {row['chosen_now']}")
        for candidate in row["candidates"]:
            marks = "".join(f" {c['span_id']}:{c['form']}={c['printed_mm']}" for c in candidate["claims_on_loop"])
            print(f"    #{candidate['index']} ilkel={candidate['primitives']:3d} "
                  f"kutu_mm={candidate['box_mm']} yuvarlak_dikdörtgen={candidate['rounded_rectangle']}"
                  f" bağlı_ölçü={len(candidate['claims_on_loop'])}{marks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
