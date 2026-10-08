"""Dilim siluetleri — eksen boyunca N dilimin 2B izdüşümü (katman yapısını okumak için).

Kullanım: .venv-cad/bin/python g125_slice_render.py <step> <eksen> <proj1> <proj2> <out.png> "v1,v2,..."
  eksen: z ya da y (dilim normali)  proj: "xy", "xz", "yz"
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

step, axis, proj1, proj2, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
values = [float(v) for v in sys.argv[6].split(",")]
AXES = {"x": 0, "y": 1, "z": 2}
shape = cq.importers.importStep(step).val()


def mesh_of(solid):
    tmp = Path(tempfile.mkdtemp()) / "m.stl"
    cq.exporters.export(cq.Workplane(obj=solid), str(tmp))
    raw = tmp.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    tri = np.frombuffer(raw, dtype=np.uint8, count=count * 50, offset=84).reshape(count, 50)
    return np.frombuffer(tri[:, 12:48].tobytes(), dtype="<f4").reshape(count, 3, 3)


def draw(ax, verts, proj, title):
    p = (AXES[proj[0]], AXES[proj[1]])
    polys = [[(t[p[0]], t[p[1]]) for t in tri] for tri in verts]
    ax.add_collection(PolyCollection(polys, facecolors="#b03a2e", edgecolors="none"))
    ax.autoscale()
    ax.margins(0.03)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)


fig, axes = plt.subplots(len(values), 2, figsize=(13, 2.1 * len(values)))
for row, value in enumerate(values):
    slab = cq.Workplane("XY").box(1000, 1000, 0.6).translate((0, 0, value)) if axis == "z" \
        else cq.Workplane("XZ").box(1000, 1000, 0.6).translate((0, value, 0))
    inter = shape.intersect(slab.val())
    verts = mesh_of(inter) if inter is not None else np.zeros((0, 3, 3), dtype="<f4")
    draw(axes[row][0], verts, proj1, f"{axis}={value:g} ({proj1})")
    draw(axes[row][1], verts, proj2, f"{axis}={value:g} ({proj2})")
fig.suptitle(f"{Path(step).name} — {axis} dilimleri")
fig.tight_layout()
fig.savefig(out, dpi=100)
print("yazıldı:", out)
