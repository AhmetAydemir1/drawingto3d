"""What a rotational/flanged sheet shows, family by family — the evidence an archetype would read.

    PYTHONPATH=src .venv/bin/python eval/flange_evidence.py            # every case that has a sheet
    PYTHONPATH=src .venv/bin/python eval/flange_evidence.py exercise-12 [--sheet]

No model is called and nothing is proposed: this prints, per sheet, the concentric stacks the reading's own
circles form, the printed diameters that landed on each stack (with the deviation between print and drawing),
and the bolt rings — equal-diameter circles standing on one circle about a stack's centre. It is the work list
for the rotational archetype, and it is deliberately separate from any decision the flow offers.

`--sheet` also renders the sheet's own circles for a visual check (out/flange-evidence/<case>.png).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.proposal import _concentric_families, _primitives, read_sheet  # noqa: E402

CASES = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]
OUT = ROOT / "out" / "flange-evidence"
STACK_MIN_CIRCLES = 3
STACK_MIN_STEPS = 3
RING_MIN_HOLES = 3
RING_SPREAD = 0.05
DIAMETER_TOLERANCE = 0.03


def _equal_diameter(circles: dict) -> list[list[tuple[str, np.ndarray, float]]]:
    """Circles of the same measured diameter, grouped within a relative tolerance."""
    groups: list[list[tuple[str, np.ndarray, float]]] = []
    for geometry_id, (centre, radius) in sorted(circles.items()):
        for group in groups:
            if abs(radius - group[0][2]) <= DIAMETER_TOLERANCE * max(radius, group[0][2]):
                group.append((geometry_id, centre, radius))
                break
        else:
            groups.append([(geometry_id, centre, radius)])
    return groups


def _ring_about(centre: np.ndarray, group: list[tuple[str, np.ndarray, float]]) -> dict | None:
    """A bolt ring: at least RING_MIN_HOLES circles of one diameter, equidistant from `centre`.

    The group is every circle on the sheet drawn at this diameter — the same Ø18 holes appear in several
    views — so the ring is the largest subset of them that stands on *one* circle about this centre.
    """
    distances = sorted(((gid, float(np.linalg.norm(point - centre))) for gid, point, _radius in group),
                       key=lambda item: item[1])
    distances = [item for item in distances if item[1] > 1.0]
    best: list[tuple[str, float]] = []
    for start in range(len(distances)):
        window = [distances[start]]
        for item in distances[start + 1:]:
            if item[1] > window[0][1] * (1.0 + RING_SPREAD):
                break
            window.append(item)
        if len(window) > len(best):
            best = window
    if len(best) < RING_MIN_HOLES:
        return None
    mean = sum(value for _gid, value in best) / len(best)
    spread = (max(value for _gid, value in best) - min(value for _gid, value in best)) / mean
    return {"holes": [gid for gid, _value in best], "count": len(best),
            "ring_radius_px": round(mean, 1), "spread": round(spread, 3)}


def evidence(case: dict) -> dict:
    sheet = ROOT / case["drawing"]
    observations = observe(sheet)
    _lines, _arcs, circles = _primitives(observations)
    reading = read_sheet(sheet)
    scale = reading.sheet_px_per_mm
    claims = [claim for claim in reading.claims if claim["form"] == "diameter"]
    stacks = []
    for family in _concentric_families(circles):
        diameters = {round(2.0 * radius, 1) for _gid, _centre, radius in family}
        if len(family) < STACK_MIN_CIRCLES or len(diameters) < STACK_MIN_STEPS:
            continue
        ids = {gid for gid, _centre, _radius in family}
        centre = family[0][1]
        printed = []
        for claim in claims:
            matched = ids & set(claim["matched_geometry"])
            if not matched:
                continue
            printed.append({"printed_mm": claim["printed_mm"], "drawn_mm": claim["drawn_mm"],
                            "span_id": claim["span_id"], "matched_here": sorted(matched),
                            "deviation": round(abs(claim["drawn_mm"] - claim["printed_mm"])
                                               / float(claim["printed_mm"]), 4)})
        rings = []
        for group in _equal_diameter(circles):
            ring = _ring_about(centre, group)
            if ring:
                radius_px = ring["ring_radius_px"]
                rings.append({**ring, "hole_diameter_mm": round(2.0 * group[0][2] / scale, 2) if scale else None,
                              "ring_diameter_mm": round(2.0 * radius_px / scale, 2) if scale else None})
        rings.sort(key=lambda row: row["count"], reverse=True)
        stacks.append({"centre_px": [round(float(v), 1) for v in centre], "circles": len(family),
                       "diameters_mm": sorted(round(2.0 * radius / scale, 2)
                                              for _gid, _centre, radius in family) if scale else None,
                       "geometry_ids": sorted(ids), "printed": sorted(printed, key=lambda row: -row["printed_mm"]),
                       "rings": rings})
    stacks.sort(key=lambda row: -row["circles"])
    return {"case": case["id"], "sheet": case["drawing"], "px_per_mm": scale,
            "circles": len(circles), "stacks": stacks}


def main() -> None:
    arguments = [arg.lower() for arg in sys.argv[1:] if not arg.startswith("--")]
    chosen = [case for case in CASES
              if (ROOT / case["drawing"]).is_file()
              and (not arguments or any(word in case["id"].lower() for word in arguments))]
    if not chosen:
        print("eşleşen pafta yok; eval/cases.json ve dosya yollarını kontrol et")
        raise SystemExit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    for case in chosen:
        row = evidence(case)
        (OUT / f"{case['id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"--- {case['id']} ({Path(case['drawing']).name}): {row['circles']} daire, "
              f"{len(row['stacks'])} yığın, px/mm={row['px_per_mm']}")
        for stack in row["stacks"][:4]:
            print(f"    yığın {stack['centre_px']} n={stack['circles']} çaplar={stack['diameters_mm']}")
            for item in stack["printed"][:6]:
                print(f"      basılı Ø{item['printed_mm']:>7} çizili {item['drawn_mm']:>7} "
                      f"({item['deviation'] * 100:.1f}%) span={item['span_id']} geom={item['matched_here'][:4]}")
            for ring in stack["rings"][:3]:
                print(f"      cıvata çemberi: {ring['count']} x Ø{ring['hole_diameter_mm']} mm, "
                      f"çember Ø{ring['ring_diameter_mm']} mm (spread {ring['spread']}) "
                      f"delikler={ring['holes'][:5]}")
    print(f"\nyazıldı: {OUT}")


if __name__ == "__main__":
    main()
