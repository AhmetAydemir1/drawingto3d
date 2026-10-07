"""G9 frozen feature regression for the guided Plate build (PLAN §15, PLAN-20 §11.7).

Written and committed BEFORE the first guided build ran (see DELIVERY-PLAN.md in this folder). It uses
the existing evaluator's independent formula (`eval/metrics.py` describe/compare) as the baseline gate,
then adds the feature-level checks PLAN-20 §11.7 demands beyond bbox/volume/cylinder-count: hole and
pocket position, diameter, depth/termination.

    .venv-cad/bin/python plate_regression.py <produced.step> <reference.step> <verdict.json>

Frozen tolerances (rationale at freeze time, before any produced STEP was seen):

  BBOX_TOL_MM 0.2            calibration is exact over 787.57 px; the trace measured within ~0.02 mm
  POSITION_TOL_MM 0.3        traced centres sat within ~0.02 mm of the printed 10/70/110/60 grid
  RADIUS_TOL_MM_TIGHT 0.05   diameters come from printed text ("6,80", "50"), not from ink
  ROUND_RADIUS_TOL_MM 0.3    corner rounds are traced from ink, not printed
  DEPTH_TOL_MM 0.1           the printed depth (8) is exact
  VOLUME_TOL_FRAC_TIGHT .005 all feature sizes are printed values; the only error source is the trace
  SYMDIFF_TOL_FRAC .005      centroid-aligned symmetric difference (raw difference is reported too)

The part frame is not assumed: the thickness axis is the bbox axis nearest 15 mm, positions are read
from the bbox-min corner, and the long/short in-plane axes are ordered by length.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "eval"))
import metrics  # noqa: E402  — the existing evaluator: independent formula and its tolerances
import cadquery as cq  # noqa: E402

BBOX_TOL_MM = 0.2
POSITION_TOL_MM = 0.3
RADIUS_TOL_MM_TIGHT = 0.05
ROUND_RADIUS_TOL_MM = 0.3
DEPTH_TOL_MM = 0.1
VOLUME_TOL_FRAC_TIGHT = 0.005
SYMDIFF_TOL_FRAC = 0.005

PLATE_MM = (120.0, 80.0, 15.0)
NOMINAL_VOLUME = (120.0 * 80.0 * 15.0
                  - math.pi * 25.0**2 * 8.0
                  - 4.0 * math.pi * 3.4**2 * 15.0
                  - 4.0 * (10.0**2 - math.pi * 10.0**2 / 4.0) * 15.0)
HOLE_R, POCKET_R, ROUND_R, POCKET_DEPTH = 3.4, 25.0, 10.0, 8.0
CORNER_UV = [(10.0, 10.0), (110.0, 10.0), (10.0, 70.0), (110.0, 70.0)]
POCKET_UV = (60.0, 40.0)


def _axis_lengths(box) -> list[float]:
    return [box.xlen, box.ylen, box.zlen]


def _features(path: str) -> dict:
    """Logical cylinders: kernel-split faces sharing an axis are merged by (radius, axis point)."""
    shape = cq.importers.importStep(str(path))
    solids = shape.solids().vals()
    body = solids[0] if solids else shape.val()
    box = body.BoundingBox()
    lengths = _axis_lengths(box)
    thickness = min(range(3), key=lambda i: lengths[i])
    plane = [i for i in range(3) if i != thickness]
    plane.sort(key=lambda i: -lengths[i])                     # plane[0] = 120 side, plane[1] = 80 side
    lows = [box.xmin, box.ymin, box.zmin]
    highs = [box.xmax, box.ymax, box.zmax]

    groups: dict[tuple, dict] = {}
    for face in body.Faces():
        if face.geomType() != "CYLINDER":
            continue
        cyl = face._geomAdaptor().Cylinder()  # noqa: SLF001 — OCC has no public wrapper here either
        radius = float(cyl.Radius())
        axis = cyl.Axis()
        direction = axis.Direction()
        location = axis.Location()
        parallel = abs(direction.Coord(thickness + 1))
        face_box = face.BoundingBox()
        span = (face_box.zmin if thickness == 2 else
                face_box.ymin if thickness == 1 else face_box.xmin,
                face_box.zmax if thickness == 2 else
                face_box.ymax if thickness == 1 else face_box.xmax)
        coords = [location.X(), location.Y(), location.Z()]
        u = coords[plane[0]] - lows[plane[0]]
        v = coords[plane[1]] - lows[plane[1]]
        key = (round(radius, 2), round(u, 1), round(v, 1))
        row = groups.setdefault(key, {"radius": round(radius, 3), "u": round(u, 3), "v": round(v, 3),
                                      "parallel": parallel, "z": [span[0], span[1]]})
        row["z"][0] = min(row["z"][0], span[0])
        row["z"][1] = max(row["z"][1], span[1])

    cylinders = sorted(groups.values(), key=lambda r: (r["radius"], r["u"], r["v"]))
    return {
        "solids": len(solids), "valid": bool(body.isValid()), "volume": round(body.Volume(), 3),
        "thickness_axis": "xyz"[thickness], "lengths": [round(len_, 3) for len_ in lengths],
        "u_len": round(lengths[plane[0]], 3), "v_len": round(lengths[plane[1]], 3),
        "thickness": round(lengths[thickness], 3),
        "cylinders": [{**row, "parallel": round(row["parallel"], 6),
                       "z": [round(row["z"][0], 3), round(row["z"][1], 3)]} for row in cylinders],
    }


def _near(got: float, want: float, tol: float) -> bool:
    return abs(got - want) <= tol


def _match_features(produced: dict) -> dict:
    """Every logical cylinder must match exactly one frozen expectation, one-to-one."""
    thickness = produced["thickness"]
    expected = ([("hole", HOLE_R, uv, (0.0, thickness), RADIUS_TOL_MM_TIGHT) for uv in CORNER_UV]
                + [("pocket", POCKET_R, POCKET_UV, (thickness - POCKET_DEPTH, thickness), RADIUS_TOL_MM_TIGHT)]
                + [("round", ROUND_R, uv, (0.0, thickness), ROUND_RADIUS_TOL_MM) for uv in CORNER_UV])
    rows, misses = [], []
    used: set[int] = set()
    for kind, radius, uv, span, radius_tol in expected:
        hit = None
        for index, row in enumerate(produced["cylinders"]):
            if index in used:
                continue
            if (_near(row["radius"], radius, radius_tol) and _near(row["u"], uv[0], POSITION_TOL_MM)
                    and _near(row["v"], uv[1], POSITION_TOL_MM)
                    and _near(row["z"][0], span[0], DEPTH_TOL_MM) and _near(row["z"][1], span[1], DEPTH_TOL_MM)
                    and row["parallel"] > math.cos(math.radians(1.0))):
                hit = index
                break
        if hit is None:
            misses.append({"kind": kind, "radius": radius, "uv": uv, "z": span})
        else:
            used.add(hit)
            rows.append({"kind": kind, "matched": produced["cylinders"][hit]})
    extras = [row for index, row in enumerate(produced["cylinders"]) if index not in used]
    return {"ok": not misses and not extras, "matched": rows, "missing": misses, "extra": extras}


def _symmetric_difference(produced_path: str, reference_path: str) -> dict:
    a = cq.importers.importStep(str(produced_path)).val()
    b = cq.importers.importStep(str(reference_path)).val()
    raw = a.cut(b).Volume() + b.cut(a).Volume()
    ca, cb = a.Center(), b.Center()
    moved = a.translate((cb.x - ca.x, cb.y - ca.y, cb.z - ca.z))
    aligned = moved.cut(b).Volume() + b.cut(moved).Volume()
    return {"raw_mm3": round(raw, 4), "aligned_mm3": round(aligned, 4),
            "centroid_shift_mm": [round(cb.x - ca.x, 4), round(cb.y - ca.y, 4), round(cb.z - ca.z, 4)]}


def main() -> int:
    produced_path, reference_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    produced, reference = _features(produced_path), _features(reference_path)
    metrics_verdict = metrics.compare(metrics.describe(produced_path), metrics.describe(reference_path))
    difference = _symmetric_difference(produced_path, reference_path)
    features = _match_features(produced)

    reference_volume = reference["volume"]
    volume_delta = abs(produced["volume"] - reference_volume) / reference_volume
    nominal_delta = abs(produced["volume"] - NOMINAL_VOLUME) / NOMINAL_VOLUME
    bbox_ok = (_near(produced["u_len"], PLATE_MM[0], BBOX_TOL_MM)
               and _near(produced["v_len"], PLATE_MM[1], BBOX_TOL_MM)
               and _near(produced["thickness"], PLATE_MM[2], BBOX_TOL_MM))

    checks = {
        "one_valid_solid": {"ok": produced["solids"] == 1 and produced["valid"],
                            "got": {"solids": produced["solids"], "valid": produced["valid"]},
                            "want": {"solids": 1, "valid": True}},
        "bbox_120x80x15": {"ok": bbox_ok, "got": [produced["u_len"], produced["v_len"], produced["thickness"]],
                           "want": list(PLATE_MM), "tol_mm": BBOX_TOL_MM},
        "volume_vs_reference": {"ok": volume_delta <= VOLUME_TOL_FRAC_TIGHT,
                                "got_mm3": produced["volume"], "reference_mm3": reference_volume,
                                "delta_frac": round(volume_delta, 6), "tol_frac": VOLUME_TOL_FRAC_TIGHT},
        "volume_vs_nominal": {"ok": nominal_delta <= VOLUME_TOL_FRAC_TIGHT,
                              "nominal_mm3": round(NOMINAL_VOLUME, 3),
                              "delta_frac": round(nominal_delta, 6), "tol_frac": VOLUME_TOL_FRAC_TIGHT},
        "features_4_holes_1_pocket_4_rounds": features,
        "cylinder_inventory": {"ok": len(produced["cylinders"]) == len(reference["cylinders"]) == 9,
                               "produced": len(produced["cylinders"]),
                               "reference": len(reference["cylinders"])},
        "symmetric_difference": {"ok": difference["aligned_mm3"] <= SYMDIFF_TOL_FRAC * reference_volume,
                                 **difference, "tol_frac": SYMDIFF_TOL_FRAC},
        "existing_evaluator": {"ok": bool(metrics_verdict["pass"]), "verdict": metrics_verdict},
        "step_reopened": {"ok": True, "detail": "cadquery importStep reopen (twice: features + difference)"},
    }
    passed = all(row["ok"] for row in checks.values())
    report = {"produced": produced, "reference": reference, "checks": checks, "pass": passed,
              "produced_path": str(produced_path), "reference_path": str(reference_path)}
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, row in checks.items():
        print(f"[{'PASS' if row['ok'] else 'FAIL'}] {name}: {json.dumps(row, ensure_ascii=False)[:300]}",
              flush=True)
    print(f"\nplate regression {'PASS' if passed else 'FAIL'} -> {out_path}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
