
import importlib.util
import json
import sys
import traceback
from pathlib import Path

import cadquery as cq

spec = importlib.util.spec_from_file_location("geo", r"/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/geo.py")
geo = importlib.util.module_from_spec(spec)
sys.modules["geo"] = geo
spec.loader.exec_module(geo)

source = Path("program.py").read_text()
namespace = {"cq": cq, "geo": geo, "__name__": "__main__"}
try:
    exec(compile(source, "program.py", "exec"), namespace)
except Exception as exc:
    frames = [frame for frame in traceback.extract_tb(exc.__traceback__) if frame.filename == "program.py"]
    where = "\nline %d: %s" % (frames[-1].lineno, frames[-1].line) if frames else ""
    raise SystemExit("%s: %s%s" % (type(exc).__name__, exc, where))

def workplane(value):
    return hasattr(value, "solids") and hasattr(value, "val")

chosen = None
for name in ("solid", "result", "part"):
    value = namespace.get(name)
    if workplane(value):
        chosen = value
        break
if chosen is None:
    found = [value for value in namespace.values() if workplane(value)]
    if len(found) == 1:
        chosen = found[0]
if chosen is None:
    raise SystemExit("solid değişkeni yok")
solids = chosen.solids().vals()
if len(solids) != 1:
    raise SystemExit("tek katı bekleniyor, %d bulundu" % len(solids))
if not solids[0].isValid():
    raise SystemExit("geçersiz katı")
step = Path(r"/Users/aydemir/Desktop/drawingto3d/eval/audits/20261007-guided-g9-g11-independent-review/plate-rebuild/part.step")
cq.exporters.export(chosen, str(step))
cq.exporters.export(chosen, str(step.with_suffix(".stl")))
# Validate the exported STEP, not just the in-memory result.
exported = cq.importers.importStep(str(step)).solids().vals()
if len(exported) != 1 or not exported[0].isValid():
    raise SystemExit("STEP yeniden açıldığında geçersiz katı")
body = exported[0]
cylinders = []
for face in body.Faces():
    if face.geomType() == "CYLINDER":
        cylinder = face._geomAdaptor().Cylinder()
        direction = cylinder.Axis().Direction()
        if abs(direction.Z()) > 0.999999:
            centre = cylinder.Location()
            bounds = face.BoundingBox()
            cylinders.append([cylinder.Radius(), centre.X(), centre.Y(), bounds.zmin, bounds.zmax])
# Cylinders along any axis: [radius, axis point xyz, unit direction, min/max along it].
# The direction sign is made canonical (first non-zero component positive) so two
# reports of the same face compare equal. Extents are the face bounding box projected
# on the axis, exact for axis-aligned faces.
cylinders_axis = []
for face in body.Faces():
    if face.geomType() == "CYLINDER":
        cylinder = face._geomAdaptor().Cylinder()
        direction = cylinder.Axis().Direction()
        vector = [direction.X(), direction.Y(), direction.Z()]
        first = next((value for value in vector if abs(value) > 1e-9), 1.0)
        if first < 0:
            vector = [-value for value in vector]
        location = cylinder.Location()
        face_bounds = face.BoundingBox()
        corners = [cq.Vector(x, y, z) for x in (face_bounds.xmin, face_bounds.xmax)
                   for y in (face_bounds.ymin, face_bounds.ymax)
                   for z in (face_bounds.zmin, face_bounds.zmax)]
        heights = [(corner.x - location.X()) * vector[0] + (corner.y - location.Y()) * vector[1]
                   + (corner.z - location.Z()) * vector[2] for corner in corners]
        cylinders_axis.append([cylinder.Radius(), location.X(), location.Y(), location.Z(),
                               vector[0], vector[1], vector[2], min(heights), max(heights)])
bounds = body.BoundingBox()
Path("geometry.json").write_text(json.dumps(dict(
    valid=body.isValid(), solids=len(exported), volume=body.Volume(),
    volume_before_export=chosen.val().Volume(),
    size=[bounds.xlen, bounds.ylen, bounds.zlen], cylinders=cylinders,
    cylinders_axis=cylinders_axis)))
bb = chosen.val().BoundingBox()
Path("measure.txt").write_text("%.6f %.6f %.6f\n" % (bb.xlen, bb.ylen, bb.zlen))
