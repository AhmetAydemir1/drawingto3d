"""Derive the two compiler example plans in `eval/plans/` and verify their expectations.

Run from the repo root:  PYTHONPATH=src .venv/bin/python eval/plans/derive_examples.py

The expected volumes are closed forms; the shaft's cross-hole term is a numeric
quadrature of the exact removal integral, independent of the CAD kernel. The shaft
declares no volume expectation at all: a cylinder-cylinder cut is approximated by the
CAD kernel (measured ~1.6e-2 mm3 here), so its hole is verified through the tool
cylinder's radius, position and depth instead. See `eval/plans/README.md`.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "src")
from drawingto3d.general import GeneralPlan

ROOT = Path(__file__).resolve().parents[2]


def simpson(function, low, high, steps=20000):
    if steps % 2:
        steps += 1
    width = (high - low) / steps
    total = function(low) + function(high)
    for index in range(1, steps):
        total += (4 if index % 2 else 2) * function(low + index * width)
    return total * width / 3


NOT_READ = "Sentetik derleyici örneği: ölçü bir çizimden okunmadı."

bracket = {
    "version": 1,
    "unit": "mm",
    "source": {
        "kind": "synthetic",
        "ref": "eval/plans/bracket_linear_pattern.json",
        "sha256": None,
        "page": 1,
    },
    "parameters": {
        "length": {"unit": "mm", "source": "assumed", "value": 80, "explanation": NOT_READ},
        "height": {"unit": "mm", "source": "assumed", "value": 50, "explanation": NOT_READ},
        "width": {"unit": "mm", "source": "assumed", "value": 30, "explanation": NOT_READ},
        "thickness": {"unit": "mm", "source": "assumed", "value": 6, "explanation": NOT_READ},
        "hole_dx": {"unit": "mm", "source": "assumed", "value": 50, "explanation": NOT_READ},
        "hole_d": {"unit": "mm", "source": "assumed", "value": 5, "explanation": NOT_READ},
        "pi": {"unit": "count", "source": "assumed", "value": 3.141592653589793,
               "explanation": "İfadelerdeki π sabiti; boyutsuz."},
        "area": {"unit": "mm", "source": "derived",
                 "expr": "length * thickness + (height - thickness) * thickness",
                 "explanation": "L kesitinin alanı."},
    },
    "sketches": {
        "outline": {
            "plane": "XY",
            "offset": "0",
            "entities": [
                {"type": "line", "start": ["-(length / 2)", "0"], "end": ["length / 2", "0"]},
                {"type": "line", "start": ["length / 2", "0"], "end": ["length / 2", "thickness"]},
                {"type": "line", "start": ["length / 2", "thickness"],
                 "end": ["-(length / 2) + thickness", "thickness"]},
                {"type": "line", "start": ["-(length / 2) + thickness", "thickness"],
                 "end": ["-(length / 2) + thickness", "height"]},
                {"type": "line", "start": ["-(length / 2) + thickness", "height"],
                 "end": ["-(length / 2)", "height"]},
                {"type": "line", "start": ["-(length / 2)", "height"], "end": ["-(length / 2)", "0"]},
            ],
        },
        "hole": {
            "plane": "XZ",
            "offset": "-(thickness + 1)",
            "entities": [{"type": "circle", "center": ["0", "width / 2"], "radius": "hole_d / 2"}],
        },
    },
    "operations": [
        {"op": "extrude", "id": "outer", "output": "body", "sketch": "outline", "distance": "width"},
        {"op": "extrude", "id": "hole_pin", "output": "hole_tool", "sketch": "hole",
         "distance": "thickness + 2"},
        {"op": "repeat", "id": "hole_pair", "input": "hole_tool", "output": "hole_tools",
         "linear": {"x_pitch": "hole_dx", "x_count": 2, "y_pitch": "0", "y_count": 1}},
        {"op": "cut", "id": "holes", "target": "body", "tool": "hole_tools", "output": "finished"},
    ],
    "result": "finished",
    "assumptions": [
        "Sentetik derleyici örneği; hiçbir ölçü bir çizimden okunmuş gibi gösterilmez.",
        "Delikler XZ düzleminde tanımlı; eksenleri Y boyunca, bacak kalınlığından (thickness) geçer.",
        "Beklenen hacim kapalı formdan: area * width - 2 * pi * (hole_d / 2) ** 2 * thickness.",
    ],
    "expect": {
        "bbox": ["length", "height", "width"],
        "volume": "area * width - 2 * pi * (hole_d / 2) ** 2 * thickness",
    },
}

pi = math.pi
shaft_r, fillet_r, length = 9.0, 3.0, 40.0
flange_r, flange_h, hole_d, hole_z = 18.0, 5.0, 5.0, 20.0
shaft_washers = shaft_r ** 2 * (length - fillet_r) + (shaft_r - fillet_r) ** 2 * fillet_r \
    + (pi / 2) * (shaft_r - fillet_r) * fillet_r ** 2 + 2 * fillet_r ** 3 / 3
before_hole = pi * (flange_r ** 2 * flange_h + shaft_washers - shaft_r ** 2 * flange_h)
hole_r = hole_d / 2
# Removal = 8 * integral_0^r sqrt((R^2 - y^2)(r^2 - y^2)) dy  (cross-hole through the barrel).
removal = 8 * simpson(lambda y: math.sqrt((shaft_r ** 2 - y ** 2) * (hole_r ** 2 - y ** 2)), 0, hole_r)

shaft = {
    "version": 1,
    "unit": "mm",
    "source": {
        "kind": "synthetic",
        "ref": "eval/plans/shaft_revolve_cross_hole.json",
        "sha256": None,
        "page": 1,
    },
    "parameters": {
        "shaft_r": {"unit": "mm", "source": "assumed", "value": 9, "explanation": NOT_READ},
        "fillet_r": {"unit": "mm", "source": "assumed", "value": 3, "explanation": NOT_READ},
        "length": {"unit": "mm", "source": "assumed", "value": 40, "explanation": NOT_READ},
        "flange_r": {"unit": "mm", "source": "assumed", "value": 18, "explanation": NOT_READ},
        "flange_h": {"unit": "mm", "source": "assumed", "value": 5, "explanation": NOT_READ},
        "hole_d": {"unit": "mm", "source": "assumed", "value": 5, "explanation": NOT_READ},
        "hole_z": {"unit": "mm", "source": "assumed", "value": 20, "explanation": NOT_READ},
        "pi": {"unit": "count", "source": "assumed", "value": 3.141592653589793,
               "explanation": "İfadelerdeki π sabiti; boyutsuz."},
        "shaft_washers": {"unit": "mm", "source": "derived",
                          "expr": ("shaft_r ** 2 * (length - fillet_r) + (shaft_r - fillet_r) ** 2 * fillet_r"
                                   " + (pi / 2) * (shaft_r - fillet_r) * fillet_r ** 2 + 2 * fillet_r ** 3 / 3"),
                          "explanation": "Mil profilinin dönel hacim integrali (π hariç), kapalı form."},
    },
    "sketches": {
        "shaft_profile": {
            "plane": "XZ",
            "offset": "0",
            "entities": [
                {"type": "line", "start": ["0", "0"], "end": ["shaft_r", "0"]},
                {"type": "line", "start": ["shaft_r", "0"], "end": ["shaft_r", "length - fillet_r"]},
                {"type": "arc", "center": ["shaft_r - fillet_r", "length - fillet_r"],
                 "radius": "fillet_r", "start_degrees": 0, "end_degrees": 90},
                {"type": "line", "start": ["shaft_r - fillet_r", "length"], "end": ["0", "length"]},
                {"type": "line", "start": ["0", "length"], "end": ["0", "0"]},
            ],
        },
        "flange_profile": {
            "plane": "XZ",
            "offset": "0",
            "entities": [
                {"type": "line", "start": ["0", "0"], "end": ["flange_r", "0"]},
                {"type": "line", "start": ["flange_r", "0"], "end": ["flange_r", "flange_h"]},
                {"type": "line", "start": ["flange_r", "flange_h"], "end": ["0", "flange_h"]},
                {"type": "line", "start": ["0", "flange_h"], "end": ["0", "0"]},
            ],
        },
        "cross_hole": {
            "plane": "YZ",
            "offset": "-25",
            "entities": [{"type": "circle", "center": ["0", "hole_z"], "radius": "hole_d / 2"}],
        },
    },
    "operations": [
        {"op": "revolve", "id": "shaft_body", "output": "shaft", "sketch": "shaft_profile", "angle": "360"},
        {"op": "revolve", "id": "flange_body", "output": "flange", "sketch": "flange_profile", "angle": "360"},
        {"op": "fuse", "id": "blank", "output": "blank", "inputs": ["flange", "shaft"]},
        {"op": "extrude", "id": "cross_tool_body", "output": "cross_tool", "sketch": "cross_hole",
         "distance": "50"},
        {"op": "cut", "id": "cross_drill", "target": "blank", "tool": "cross_tool", "output": "finished"},
    ],
    "result": "finished",
    "assumptions": [
        "Sentetik derleyici örneği; hiçbir ölçü bir çizimden okunmuş gibi gösterilmez.",
        "Hacim beklentisi bildirilmedi: yan delikteki silindir-silindir kesişimini CAD çekirdeği "
        "yaklaşık hesaplar (ölçülen sapma ~1,6e-2 mm³). Delik, araç silindirinin yarıçap/konum/"
        "derinlik denetimiyle doğrulanır.",
        f"Bağımsız sayısal beklenti (rapor): kesme öncesi {before_hole:.3f} mm³, "
        f"yan deliğin kaldırdığı {removal:.3f} mm³, sonuç {before_hole - removal:.3f} mm³.",
    ],
    "expect": {
        "bbox": ["2 * flange_r", "2 * flange_r", "length"],
        "volume": None,
    },
}

out_dir = ROOT / "eval" / "plans"
out_dir.mkdir(parents=True, exist_ok=True)
for name, data in (("bracket_linear_pattern", bracket), ("shaft_revolve_cross_hole", shaft)):
    GeneralPlan.model_validate(data)
    (out_dir / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: written and valid")

# Independent cross-checks of the closed forms (no CAD involved).
bracket_volume = (80 * 6 + 44 * 6) * 30 - 2 * pi * (5 / 2) ** 2 * 6
print(f"bracket expected volume: {bracket_volume:.6f}")
print(f"shaft before hole      : {before_hole:.6f}")
print(f"shaft hole removal     : {removal:.6f}  (naive pi r^2 * 2R = {pi * hole_r ** 2 * 2 * shaft_r:.6f})")
print(f"shaft expected volume  : {before_hole - removal:.6f}")
