"""Exercise 13 raster — önbellekten okuma dökümü (profil + daire + ölçü)."""
import pickle
import sys
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import guided  # noqa: E402

cache = Path.home() / ".hermes/cache/scratch/g125-audit-cache/exercise-13-raster.pkl"
obs = pickle.loads(cache.read_bytes())
options = guided.drawing_options(obs)

print("profil:", len(options["profiles"]), " daire:", len(options["circles"]), " ölçü:", len(options["measurements"]))

print("\n=== DAİRELER:")
for c in options["circles"]:
    x, y = c["center"]
    extra = " ".join(f"{k}={c[k]}" for k in c if k not in ("id", "center", "radius", "primitive_ids", "path_id"))
    print(f"  {c['id']:16} merkez=({x:7.1f},{y:7.1f}) r={c['radius']:6.2f} {extra[:90]}")

print("\n=== ÖLÇÜLER:")
for m in options["measurements"]:
    row = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()}
    print("  ", str(row)[:220])

print("\n=== PROFİLLER (nokta sayısına göre ilk 20):")
for p in sorted(options["profiles"], key=lambda q: -q.get("point_count", 0))[:20]:
    bb = p.get("bbox_px")
    n = p.get("point_count", 0)
    lines = sum(1 for e in p.get("entities", p.get("edges", [])) if (e.get("kind") or e.get("type")) == "line")
    arcs = sum(1 for e in p.get("entities", p.get("edges", [])) if (e.get("kind") or e.get("type")) in ("arc", "circle"))
    print(f"  {p['id']:16} {p['kind']:6} n={n:4} çizgi={lines:3} yay={arcs:3} bbox={bb}")
