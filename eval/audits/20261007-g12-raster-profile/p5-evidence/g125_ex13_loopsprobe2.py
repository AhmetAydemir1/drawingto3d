"""ex13: 47 döngünün bbox'ı + ön görünüşte olan var mı (düzeltilmiş şema)."""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import guided  # noqa: E402

cache = Path.home() / ".hermes/cache/scratch/g125-audit-cache/exercise-13-raster.pkl"
obs = pickle.loads(cache.read_bytes())
lines, arcs, circles = guided._primitives(obs)
raster = guided.raster_arcs(obs)
loops = guided._loops(lines, arcs, corner_joins=raster,
                      join_tolerance_px=guided.RASTER_JOIN_TOLERANCE_PX)

FRONT = (800.0, 1280.0, 1980.0, 2320.0)

def ent_pts(gid, start, end, meta):
    if meta.get("kind") == "line":
        return [start, end]
    c = np.asarray(meta["centre"], float)
    r = float(meta["radius"])
    out = []
    for deg in (meta["start_degrees"], meta["end_degrees"]):
        out.append(c + r * np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))]))
    return out

def loop_bbox(loop):
    xs, ys = [], []
    for gid, start, end, meta in loop["entities"]:
        for p in ent_pts(gid, start, end, meta):
            xs.append(float(p[0])); ys.append(float(p[1]))
    return (min(xs), min(ys), max(xs), max(ys))

rows = []
for i, loop in enumerate(loops):
    bb = loop_bbox(loop)
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    in_front = FRONT[0] <= cx <= FRONT[2] and FRONT[1] <= cy <= FRONT[3]
    rows.append((i, len(loop["entities"]), bb, in_front, loop.get("area_px")))

print("=== ÖN GÖRÜNÜŞ bölgesine düşen döngüler:")
n = 0
for i, ne, bb, in_front, area in rows:
    if in_front:
        n += 1
        print(f"  loop[{i}] ent={ne} bbox=({bb[0]:.0f},{bb[1]:.0f},{bb[2]:.0f},{bb[3]:.0f}) alan={area}")
print("ön döngü sayısı:", n, "/", len(rows))

print("\n=== hepsi:")
for i, ne, bb, in_front, area in rows:
    mark = " <== FRONT" if in_front else ""
    print(f"  [{i:3}] ent={ne:3} bbox=({bb[0]:.0f},{bb[1]:.0f},{bb[2]:.0f},{bb[3]:.0f}){mark}")

# ön görünüşün GERÇEK parça siluetinin beklenen kutusu: x 899..1799? kontrol için
# bu bölgede hangi döngüler var/yok — ve en büyük parça döngüsü nerede?
big = max(rows, key=lambda r: r[1])
print("\nen çok entity'li döngü:", big[0], big[1], tuple(round(v) for v in big[2]))
