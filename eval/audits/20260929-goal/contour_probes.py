"""Read-only audit probes: each expected outcome is independent of current implementation.
Run from repo root: PYTHONPATH=src .venv/bin/python out/goal-audit-20260929-ycgu28h8/contour_probes.py
These report discrepancies without changing source, tests, or project records.
"""
import json
import math
from drawingto3d.contour_audit import audit_contour


def arc(edge_id, radius, start_degrees, sweep_degrees):
    def point(degrees):
        angle = math.radians(degrees)
        return [radius * math.cos(angle), radius * math.sin(angle)]
    return {"id": edge_id, "kind": "arc", "center": [0, 0], "radius": radius,
            "a": -start_degrees, "b": -start_degrees - sweep_degrees,
            "start": point(start_degrees), "end": point(start_degrees + sweep_degrees)}


def line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def report(name, edges, expected_ok, expected_reason):
    result = audit_contour(edges)
    print(json.dumps({"name": name, "expected_ok": expected_ok, "expected_reason": expected_reason,
                      "observed": result, "expectation_met": result["ok"] == expected_ok,
                      "input": edges}, ensure_ascii=False))


first = arc("first", 100, 0, 180)
second = arc("second", 100, 180, 180)
# Change canonical angles only: CAD will now rebuild the same half twice.
second["a"], second["b"] = 0, -180
report("canonical_angle_disagrees_with_stored_start", [first, second], False,
       "Stored start/end of second arc disagree with canonical a/b used by CAD; must reject.")

outer = arc("outer", 100, 0, 180)
inner = arc("inner", 99, 180, -180)
report("valid_thin_half_annulus", [outer, line("left", outer["end"], inner["start"]), inner,
                                  line("right", inner["end"], outer["start"])], True,
       "Simple closed half-annulus with distinct concentric radii 100 and 99; no overlapping edges.")

semicircle = arc("arc", 1000, 0, 180)
report("genuine_intersections_missed_by_32_samples", [semicircle,
       line("left", semicircle["end"], [-1000, 999]), line("top", [-1000, 999], [1000, 999]),
       line("right", [1000, 999], semicircle["start"])], False,
       "Line y=999 crosses radius-1000 semicircle at x=+/-sqrt(1999), about +/-44.7102.")

for sign in (-1, 1):
    vertices = [[0, 0], [100, 0], [100, sign * 100], [50, 0], [0, sign * 100], [0, 0]]
    edges = [line(f"e{i}", vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
    report(f"non_neighbour_touch_y_sign_{sign}", edges, False,
           "Vertex (50,0) touches non-neighbour first edge; not a simple ring. Reflection must preserve result.")

report("duplicate_short_nonzero_edges", [line("a", [0, 0], [0.8, 0]),
                                        line("b", [0.8, 0], [0, 0])], False,
       "Same nonzero segment walked twice, zero area; must reject although length is below fixed 1px overlap threshold.")
