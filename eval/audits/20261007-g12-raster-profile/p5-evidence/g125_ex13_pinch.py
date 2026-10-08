"""§65 P5 — exercise-13 outline_1 nokta-atışı: kalan sorun sınıfı (çift + konum + px)."""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import contour_audit, guided  # noqa: E402

cache = Path.home() / ".hermes/cache/scratch/g125-audit-cache/exercise-13-raster.pkl"
obs = pickle.loads(cache.read_bytes())
options = guided.drawing_options(obs)
profiles = sorted(options["profiles"], key=lambda p: len(p.get("points") or []), reverse=True)
target = profiles[0]
print("hedef:", target["id"], "kind:", target["kind"], "nokta:", len(target.get("points") or []))


def dump_edges(edges):
    for e in edges:
        row = {"id": e.get("id"), "kind": e.get("kind")}
        for k in ("start", "end"):
            v = e.get(k)
            row[k] = [round(float(x), 1) for x in v] if v else None
        if e.get("center"):
            row["center"] = [round(float(x), 1) for x in e["center"]]
            row["r"] = round(float(e.get("radius") or 0), 1)
            row["a"] = round(float(e.get("a_degrees") or 0), 1)
            row["b"] = round(float(e.get("b_degrees") or 0), 1)
        print("   ", json.dumps(row, ensure_ascii=False))


edges = target.get("edges") or []
print("\n=== EDGES (%d):" % len(edges))
dump_edges(edges)

for tol in (0.5, 40.0):
    audit = contour_audit.audit_contour(edges, tolerance_px=tol)
    print("\n=== AUDIT tol=%.1f -> ok=%s closure=%s issues=%d" % (tol, audit["ok"], audit.get("closure_px"), len(audit["issues"])))
    for i, iss in enumerate(audit["issues"]):
        print("  [%02d] %s" % (i, json.dumps(iss, ensure_ascii=False)))

joins = target.get("joins") or []
print("\n=== JOINS (%d), join_max=%s:" % (len(joins), target.get("join_max_px")))
for j in joins:
    print("   ", json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in j.items()}, ensure_ascii=False)[:240])
