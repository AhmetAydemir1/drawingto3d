"""ex13: okunan daireleri + ölçü kutularını çizimin üzerine işaretle."""
from pathlib import Path

from PIL import Image, ImageDraw

SRC = Path("/Users/aydemir/Desktop/drawingto3d/examples/pdf with steps/4/Exercise 13.PNG")
OUT = Path.home() / ".hermes/cache/scratch/ex13-circles-marked.png"

img = Image.open(SRC).convert("RGB")
d = ImageDraw.Draw(img)

circles = [
    ("g249", 1785.8, 507.8, 36.85),
    ("g250", 1106.2, 510.8, 36.95),
    ("g251", 1764.8, 1307.2, 17.90),
    ("g252", 1281.8, 1695.8, 36.80),
]
for name, x, y, r in circles:
    d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0), width=8)
    d.line([x - 60, y, x + 60, y], fill=(0, 160, 255), width=4)
    d.line([x, y - 60, x, y + 60], fill=(0, 160, 255), width=4)
    d.text((x + r + 12, y - r - 40), name, fill=(255, 0, 0))

boxes = [
    ("30.00", 880, 751, 134, 42),
    ("170.00", 1364, 1182, 160, 42),
    ("10.00", 2296, 1581, 129, 42),
    ("90.00", 2291, 1781, 134, 42),
    ("25.00", 1237, 2030, 134, 42),
    ("240.00", 1363, 2229, 165, 42),
]
for text, x, y, w, h in boxes:
    d.rectangle([x, y, x + w, y + h], outline=(0, 180, 0), width=6)
    d.text((x, y - 34), text, fill=(0, 140, 0))

img.save(OUT)
print("yazıldı:", OUT, img.size)
