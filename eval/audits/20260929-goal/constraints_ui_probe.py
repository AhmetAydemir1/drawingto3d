"""Read-only audit probes. No production state is read or changed. Run from repository root."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import json
from drawingto3d.guided import Decisions, make_plan, sketch_diagnostics, questions, user_dimensions, unresolved_bindings

class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.buttons = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids[a["id"]] = tag
        if tag == "button":
            self.buttons.append(a)

out = {}
p = Parse()
p.feed(Path("src/drawingto3d/static/guided.html").read_text())
out["html_parser"] = {"ids": {k: p.ids.get(k) for k in ["bind-axis", "bind-direction", "bind-start", "bind-cancel"]},
                      "malformed_buttons": [b for b in p.buttons if "<div" in b],
                      "live_browser_verified": False,
                      "browser_limitation": "file:// URL blocked by browser security policy; no bypass attempted"}
pts = [[20., 20.], [120., 20.], [120., 120.], [20., 120.]]
prof = {"id": "outline_0", "kind": "wire", "join_max_px": 0., "points": pts,
        "edges": [{"id": f"e{i}", "kind": "line", "start": pts[i], "end": pts[(i + 1) % 4]} for i in range(4)]}
opts = {"frame": {"width": 400, "height": 400}, "profiles": [prof],
        "circles": [{"id": "g0", "center": [40., 40.], "radius": 5.},
                    {"id": "g1", "center": [100., 40.], "radius": 5.}], "measurements": []}
def end(kind, identifier, point):
    return {"kind": kind, "id": identifier, "x": point[0], "y": point[1]}
def tie(identifier, value, axis, first, second, direction=1):
    return {"id": identifier, "value": value, "unit": "mm", "axis": axis, "direction": direction,
            "first": first, "second": second}
d = {"calibration": {"first": pts[0], "second": pts[1], "value": 100, "unit": "mm"},
     "profile_id": "outline_0", "thickness": 10, "trace_acknowledged": True, "bindings": [], "holes": []}
record = {"source": "synthetic-audit-fixture.pdf", "source_sha256": "a" * 64, "options": opts, "decisions": d}
base = make_plan(record).model_dump()
d["bindings"] = [tie("b0", 30, "x", end("centre", "g0", [40, 40]), end("centre", "g1", [100, 40]))]
res = make_plan(record).model_dump()
out["calibration_overwritten"] = {"base_width_mm": base["parameters"]["edge_0_end_x"]["value"],
                                  "width_after_local_centre_binding_mm": res["parameters"]["edge_0_end_x"]["value"],
                                  "reported_px_per_mm": sketch_diagnostics(opts, Decisions.model_validate(d))["px_per_mm"]}
d["bindings"] = [tie("x", 50, "x", end("vertex", "e0:start", pts[0]), end("vertex", "e1:start", pts[1])),
                 tie("y", 30, "y", end("vertex", "e0:start", pts[0]), end("vertex", "e3:start", pts[3]), -1)]
parsed = Decisions.model_validate(d)
out["valid_xy_blocked_by_scale"] = questions(parsed, sketch_diagnostics(opts, parsed), opts)
other = deepcopy(prof)
other["id"] = "outline_1"
other["edges"].reverse()
opts["profiles"].append(other)
out["changed_profile_with_reused_edge_ids"] = unresolved_bindings(opts, parsed.model_copy(update={"profile_id": "outline_1"}))
out["dropped_bound_edge_not_marked_stale"] = unresolved_bindings(opts, Decisions.model_validate({**d, "contour": {"drop": ["e0"], "approve_join": False}}))
arc = {"id": "outline_arc", "kind": "wire", "join_max_px": 0.,
       "points": [[0.,50.], [50.,0.], [100.,50.], [100.,100.], [0.,100.]],
       "edges": [{"id": "arc", "kind": "arc", "start": [0.,50.], "end": [100.,50.], "center": [50.,50.], "radius": 50., "a": 180., "b": 0.},
                 {"id": "l1", "kind": "line", "start": [100.,50.], "end": [100.,100.]},
                 {"id": "l2", "kind": "line", "start": [100.,100.], "end": [0.,100.]},
                 {"id": "l3", "kind": "line", "start": [0.,100.], "end": [0.,50.]}]}
aopts = {"frame": {"width": 200, "height": 200}, "profiles": [arc], "circles": [], "measurements": []}
ad = {**d, "profile_id": "outline_arc", "calibration": {"first": [0.,50.], "second": [100.,50.], "value": 100, "unit": "mm"},
      "bindings": [tie("unsupported", 100, "x", end("vertex", "arc:start", [0,50]), end("vertex", "arc:end", [100,50]))]}
out["arc_solver"] = user_dimensions(deepcopy(arc), aopts, Decisions.model_validate(ad), 1, [0,100])
try:
    ar = make_plan({"source": "synthetic-audit-fixture.pdf", "source_sha256": "a" * 64, "options": aopts, "decisions": ad})
    out["unsupported_make_plan"] = {"accepted": True, "entity_count": len(ar.sketches["outer"].entities)}
except Exception as e:
    out["unsupported_make_plan"] = {"accepted": False, "error": str(e)}
print(json.dumps(out, indent=2, ensure_ascii=False))
