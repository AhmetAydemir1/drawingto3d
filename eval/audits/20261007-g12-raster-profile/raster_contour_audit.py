"""G12.5 §63 — raster kontur denetimi.

Her raster vaka için, ürünün kendi okuma yolunu (`guided.observe`) ve kontur denetimini
(`contour_audit.audit_contour`) çağırır; her vaka için en büyük 12 profili (nokta sayısına
göre) PLAN-25 §63'ün istediği alanlarla kaydeder (kalan sayısı `truncated_profiles`):

    profile id, view id, primitive ids, closed, self-intersection, join gaps,
    movement applied, bbox, area, line count, arc count

Bu bir *tanılama* kaydıdır, ürün yolu değil: hiçbir üretim kararı bu dosyayı okumaz.
Okuma maliyetlidir; bu yüzden her paftanın `Observations` nesnesi scratch altında
pickle'lanır (`--refresh` ile yenilenir).

Kullanım:
    .venv/bin/python eval/audits/20261007-g12-raster-profile/raster_contour_audit.py \
        [--refresh] [--only CASE ...] > .../contour-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import contour_audit, guided  # noqa: E402

CACHE_DIR = Path.home() / ".hermes/cache/scratch/g125-audit-cache"

CASES = {
    "exercise-51-raster": "examples/pdf with steps/1/Exercise_51.PNG",
    "exercise-17-raster": "examples/pdf with steps/3/Exercise 17.PNG",
    "exercise-13-raster": "examples/pdf with steps/4/Exercise 13.PNG",
    "my-part-raster": "examples/pdf with steps/7/my_part.jpg",
    "flange-raster": "examples/pdf with steps/8/Flange.PNG",
}

MAX_PROFILES = 12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observations_for(case_id: str, source: Path, refresh: bool):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{case_id}.pkl"
    if cache.exists() and not refresh:
        return pickle.loads(cache.read_bytes()), "cache"
    started = time.time()
    observations = guided.observe(source)
    cache.write_bytes(pickle.dumps(observations))
    return observations, f"read {time.time() - started:.0f}s"


def polygon_area(points: list[list[float]]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def profile_row(profile: dict) -> dict:
    row = {"profile_id": profile.get("id"), "kind": profile.get("kind"),
           "view_id": profile.get("view_id"),
           "primitive_ids": profile.get("geometry_ids") or [],
           "point_count": len(profile.get("points") or [])}
    edges = profile.get("edges") or []
    row["line_count"] = sum(1 for e in edges if e.get("kind") == "line")
    row["arc_count"] = sum(1 for e in edges if e.get("kind") == "arc")
    points = profile.get("points") or []
    if points:
        xs = [p[0] for p in points]; ys = [p[1] for p in points]
        row["bbox_px"] = [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]
    else:
        row["bbox_px"] = None
    row["area_px2"] = round(polygon_area(points), 1) if len(points) >= 3 else None
    joins = profile.get("joins") or []
    row["join_gaps_px"] = {"join_max": profile.get("join_max_px"),
                           "gaps": [j.get("gap_px") for j in joins]}
    row["movement_applied_px"] = profile.get("applied_move_px")
    if edges:
        audit = contour_audit.audit_contour(edges)
        row["closed"] = bool(audit["ok"])
        row["closure_px"] = round(float(audit.get("closure_px") or 0.0), 2)
        row["self_intersection"] = any(i["kind"] == "self_intersection" for i in audit["issues"])
        row["other_issues"] = sorted({i["kind"] for i in audit["issues"] if i["kind"] != "self_intersection"})
    else:
        row["closed"] = profile.get("kind") == "circle"
        row["closure_px"] = 0.0 if row["closed"] else None
        row["self_intersection"] = False
        row["other_issues"] = []
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="G12.5 §63 raster kontur denetimi")
    parser.add_argument("--refresh", action="store_true", help="önbelleği yok say, paftayı yeniden oku")
    parser.add_argument("--only", nargs="*", default=None, help="yalnız bu vakalar")
    parser.add_argument("--quiet", action="store_true", help="ilerleme satırlarını stderr'e yaz")
    args = parser.parse_args()

    cases = [c for c in CASES if not args.only or c in args.only]
    report = {"artifact": "G12.5 §63 raster contour audit", "note":
              "view_id ve movement_applied_px yalnız çözülmüş oturumda doludur; burada okuma ham "
              "haldedir (G12.3 §46/§48: görünüş adayları ve sahiplik oturum açılışında bir kez yazılır).",
              "cases": []}
    for case_id in cases:
        source = ROOT / CASES[case_id]
        observations, how = observations_for(case_id, source, args.refresh)
        started = time.time()
        options = guided.drawing_options(observations)
        profiles = sorted(options["profiles"], key=lambda p: len(p.get("points") or []), reverse=True)
        row = {"case_id": case_id, "source_path": CASES[case_id], "source_sha256": sha256(source),
               "read": how, "options_ms": round((time.time() - started) * 1000),
               "profile_count": len(options["profiles"]), "measurement_count": len(options.get("measurements") or []),
               "profiles": [profile_row(p) for p in profiles[:MAX_PROFILES]],
               "truncated_profiles": max(0, len(profiles) - MAX_PROFILES)}
        report["cases"].append(row)
        if not args.quiet:
            largest = row["profiles"][0] if row["profiles"] else {}
            print(f"[audit] {case_id}: {len(profiles)} profil, en büyük {largest.get('profile_id')} "
                  f"kapalı={largest.get('closed')}", file=sys.stderr, flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
