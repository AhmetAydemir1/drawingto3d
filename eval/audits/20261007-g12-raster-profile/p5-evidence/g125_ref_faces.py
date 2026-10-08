"""Referans STEP künyesi — silindir yüzlerin yarıçap + eksen + z-aralığı dökümü.

Kullanım: .venv-cad/bin/python g125_ref_faces.py <step> [<step2> ...]
"""
import sys

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_SurfaceType
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

for path in sys.argv[1:]:
    shape = cq.importers.importStep(path)
    solid = shape.val()
    print(f"== {path}")
    print(f"   bbox: {[round(v, 3) for v in (shape.val().BoundingBox().xlen, shape.val().BoundingBox().ylen, shape.val().BoundingBox().zlen)]}")
    print(f"   volume: {round(solid.Volume(), 3)}  faces: {len(shape.faces().vals())}")
    explorer = TopExp_Explorer(solid.wrapped, TopAbs_FACE)
    index = 0
    planes, cylinders = [], []
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        surface = BRepAdaptor_Surface(face)
        kind = surface.GetType()
        bb = cq.Face(face).BoundingBox()
        if kind == GeomAbs_SurfaceType.GeomAbs_Cylinder:
            cyl = surface.Cylinder()
            axis = cyl.Axis()
            loc = axis.Location()
            direction = axis.Direction()
            radii = round(cyl.Radius(), 3)
            cylinders.append((radii, (round(loc.X(), 2), round(loc.Y(), 2)), (round(direction.X(), 2), round(direction.Y(), 2), round(direction.Z(), 2)),
                              (round(bb.zmin, 2), round(bb.zmax, 2)), (round(bb.xmin, 2), round(bb.xmax, 2), round(bb.ymin, 2), round(bb.ymax, 2))))
        elif kind == GeomAbs_SurfaceType.GeomAbs_Plane:
            planes.append((round(bb.zmin, 2), round(bb.zmax, 2)))
        index += 1
        explorer.Next()
    print("   silindir yüzler (r, eksen-xy, yön, z-aralığı, x/y-aralığı):")
    for row in sorted(cylinders):
        print(f"     r={row[0]:<7} eksen=({row[1][0]},{row[1][1]}) yön={row[2]} z=[{row[3][0]},{row[3][1]}] xy=({row[4][0]},{row[4][1]},{row[4][2]},{row[4][3]})")
    zlevels = sorted(set(z for row in planes for z in row))
    print(f"   düzlem z seviyeleri: {zlevels}")
