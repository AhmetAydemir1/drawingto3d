"""ex13: 47 profilin tamamını pafta üzerine işaretle (küme renkleri) + daireler."""
import pickle
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import contour_audit, guided  # noqa: E402

cache = Path.home() / ".hermes/cache/scratch/g125-audit-cache/exercise-13-raster.pkl"
obs = pickle.loads(cache.read_bytes())
options = guided.drawing_options(obs)

img = Image.open(ROOT / "examples/pdf with steps/4/Exercise 13.PNG").convert("RGB")
d = ImageDraw.Draw(img)

iso = (230, 60, 0)
title = (0, 130, 230)
front = (0, 160, 0)
other = (150, 0, 150)

def region(bb):
    if not bb:
        return other
    x0, y0, x1, y1 = bb
    if y0 > 2100:
        return title
    if y0 > 1200:
        return front
    return iso

for pr in options["profiles"]:
    pts = pr.get("points") or []
    if not pts:
        continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bb = (min(xs), min(ys), max(xs), max(ys))
    col = region(bb)
    if pr.get("kind") == "wire":
        d.line([(float(p[0]), float(p[1])) for p in pr.get("points")], fill=col, width=5)

for c in options.get("circles") or []:
    x, y = c["center"]; r = c["radius"]
    d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0), width=5)
    d.text((x + r + 6, y), c["id"], fill=(255, 0, 0))

# ön görünüşün beklenen bölgesini beyaz çerçevele (g252 çevresi)
d.rectangle([850, 1350, 1950, 2150], outline=(0, 0, 0), width=4)
d.text((860, 1360), "front-view?", fill=(0, 0, 0))

out = Path.home() / ".hermes/cache/scratch/ex13-allprofiles-marked.png"
img.save(out)
small = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
small.save(Path.home() / ".hermes/cache/scratch/ex13-allprofiles-small.png")
print("yazıldı:", out, small.size)
