"""Referans STEP'in üç ortografik siluetini PNG'ye çizer (mesh → 2B dolgu).

Kullanım: .venv-cad/bin/python g125_ref_render.py <step> <çıktı.png>
"""
import struct
import sys
import tempfile
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

step, out = sys.argv[1], sys.argv[2]
shape = cq.importers.importStep(step)
tmp = Path(tempfile.mkdtemp()) / "mesh.stl"
cq.exporters.export(shape, str(tmp))

raw = tmp.read_bytes()
count = struct.unpack_from("<I", raw, 80)[0]
tris = np.frombuffer(raw, dtype=np.uint8, count=count * 50, offset=84).reshape(count, 50)
verts = np.frombuffer(tris[:, 12:48].tobytes(), dtype="<f4").reshape(count, 3, 3)

pairs = [("önden (x-z)", 0, 2), ("üstten (x-y)", 0, 1), ("yandan (y-z)", 1, 2)]
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
for ax, (title, a, b) in zip(axes, pairs):
    polys = [[(p[a], p[b]) for p in tri] for tri in verts]
    ax.add_collection(PolyCollection(polys, facecolors="#b03a2e", edgecolors="none"))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(True, alpha=0.2)
fig.suptitle(Path(step).name)
fig.tight_layout()
fig.savefig(out, dpi=110)
print("yazıldı:", out)
