"""ex13 ön görünüş: ham primitifleri çiz (çizgi=mavi, yay=turuncu, daire=kırmızı) + dead-end noktaları."""
import pickle
import sys
from pathlib import Path

import numpy as np

from PIL import Image, ImageDraw

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import guided  # noqa: E402

cache = Path.home() / ".hermes/cache/scratch/g125-audit-cache/exercise-13-raster.pkl"
obs = pickle.loads(cache.read_bytes())

img = Image.open(ROOT / "examples/pdf with steps/4/Exercise 13.PNG").convert("RGB")
d = ImageDraw.Draw(img)

for p in obs.primitives:
    d0 = p.model_dump()
    kind = d0.get("kind")
    if kind == "line":
        s, e = d0["start"], d0["end"]
        d.line([float(s[0]), float(s[1]), float(e[0]), float(e[1])], fill=(0, 90, 255), width=3)
    elif kind == "arc":
        c = d0["centre"]; r = float(d0["radius"])
        a0 = float(d0["start_degrees"]); a1 = float(d0["end_degrees"])
        # page coords: y-down; sample by angle
        pts = []
        for t in np.linspace(a0, a1, 48):
            pts.append((c[0] + r * np.cos(np.radians(float(t))), c[1] + r * np.sin(np.radians(float(t)))))
        d.line(pts, fill=(255, 120, 0), width=3)
    elif kind == "circle":
        c = d0.get("centre"); r = float(d0.get("radius") or 0)
        if c:
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(255, 0, 0), width=3)

# dead-end noktaları (trace'ten)
dead = [(1164.5, 2094.0), (1771.3, 362.5), (1569.0, 2153.0), (2095.7, 1256.5), (1918.0, 1203.0),
        (1194.0, 1235.0), (1548.7, 1417.0), (1017.5, 1375.0), (913.7, 1518.0)]
for x, y in dead:
    d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(255, 0, 255), width=5)

out = Path.home() / ".hermes/cache/scratch/ex13-front-primitives.png"
img.save(out)
crop = img.crop((800, 1250, 2150, 2400))
crop.save(Path.home() / ".hermes/cache/scratch/ex13-front-primitives-crop.png")
print("yazıldı:", out, "crop:", crop.size)
