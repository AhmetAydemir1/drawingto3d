"""Exact sketch from the measurements the user bound to the drawing's own geometry.

The traced profile and the hole centres are *pixels*: they carry the drawing's line width, its rounding and
the raster's noise, and nothing in them is a printed number. A **binding** is the user saying which printed
measurement belongs to which two pieces of that geometry — the plate's `80,00` between its two long edges,
its `60,00` between the two hole rows, its `100,00` across two hole centres.

What this module can do with a set of bindings, and what it deliberately does not:

* It fits **one scale** to all of them at once (the least-squares slope through the origin of
  drawn-pixels against printed-millimetres, so a long dimension weighs more than a short one). One binding
  overrules a two-click calibration; several bindings that agree tighten it.
* It reports every binding whose drawn geometry disagrees with its printed value under that fitted scale,
  in millimetres. A set that disagrees is **over-constrained**: the drawing is not to scale in that respect,
  and the user has to see it rather than have the flow average it away.
* It reports which features are **not** bound — those stay traced, and the plan keeps calling them `assumed`.

It does **not** move individual edges: a binding cannot yet stretch the outline along one axis while leaving
its corner arcs intact, so a sheet whose *proportions* disagree with its own printed numbers can be
calibrated but not corrected here. That is the next slice (B-2), and it is why a solved sketch is still a
draft, not a verified part.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# A binding whose drawn geometry is further than this from its printed value (in mm, under the fitted
# scale) is reported as a conflict. Measured on the plate: its own rows sit within 0.02 mm of each other.
CONFLICT_MM = 0.5
MM_PER_INCH = 25.4


@dataclass
class Binding:
    """One printed measurement the user tied to two pieces of the drawing's own geometry."""

    value: float
    unit: str = "mm"
    span_id: str | None = None
    first: dict = field(default_factory=dict)     # {"kind": "centre"|"vertex", "id": str, "x": float, "y": float}
    second: dict = field(default_factory=dict)

    @property
    def value_mm(self) -> float:
        return float(self.value) * (MM_PER_INCH if self.unit == "in" else 1.0)

    def drawn_px(self) -> float:
        return math.dist((self.first["x"], self.first["y"]), (self.second["x"], self.second["y"]))


def fit_scale(bindings: list[Binding], fallback_px_per_mm: float | None) -> dict:
    """One scale from every binding, with each binding's own residual under it.

    Least squares through the origin: `scale = Σ(drawn · value) / Σ(value²)` in px per mm. The row set that
    comes back is the evidence the flow keeps: what the user bound, what the drawing measures under the
    fitted scale, and how far that is from the printed number.
    """
    usable = [binding for binding in bindings if binding.value_mm > 0 and binding.drawn_px() > 0]
    if not usable:
        return {"px_per_mm": fallback_px_per_mm, "source": "calibration" if fallback_px_per_mm else None,
                "rows": [], "conflicts": [], "consistent": bool(fallback_px_per_mm)}
    numerator = sum(binding.drawn_px() * binding.value_mm for binding in usable)
    denominator = sum(binding.value_mm ** 2 for binding in usable)
    scale = numerator / denominator if denominator else fallback_px_per_mm
    if not scale or scale <= 0:
        return {"px_per_mm": fallback_px_per_mm, "source": "calibration" if fallback_px_per_mm else None,
                "rows": [], "conflicts": [], "consistent": bool(fallback_px_per_mm)}
    rows = []
    for binding in usable:
        drawn_mm = binding.drawn_px() / scale
        residual = drawn_mm - binding.value_mm
        rows.append({"span_id": binding.span_id, "value_mm": round(binding.value_mm, 4),
                     "drawn_mm": round(drawn_mm, 4), "residual_mm": round(residual, 4),
                     "first": binding.first.get("id") or binding.first.get("kind"),
                     "second": binding.second.get("id") or binding.second.get("kind")})
    conflicts = [row for row in rows if abs(row["residual_mm"]) > CONFLICT_MM]
    return {"px_per_mm": scale, "source": "bindings", "rows": rows, "conflicts": conflicts,
            "consistent": not conflicts}


def unbound(profile: dict, circles: list[dict], bindings: list[Binding]) -> dict:
    """Which of the sheet's features no binding reaches — these keep their traced coordinates."""
    bound: set[str] = set()
    for binding in bindings:
        for end in (binding.first, binding.second):
            if end.get("id"):
                bound.add(str(end["id"]))
    circle_ids = [circle["id"] for circle in circles]
    profile_edges = list(range(len(profile.get("edges", [])))) if profile else []
    bound_edges = {int(item.split(":")[1]) for item in bound if item.startswith("edge:") and item.split(":")[1].isdigit()}
    return {"circles": sorted(circle_id for circle_id in circle_ids if circle_id not in bound),
            "edges": sorted(index for index in profile_edges if index not in bound_edges),
            "profile_bound": bool(bound_edges)}


def diagnose(profile: dict, circles: list[dict], bindings: list[Binding], fit: dict | None = None) -> dict:
    """The whole picture for the user: the fit, the conflicts, and what is still only traced."""
    fitted = fit or fit_scale(bindings, None)
    touched = unbound(profile, circles, bindings)
    return {"px_per_mm": fitted.get("px_per_mm"), "source": fitted.get("source"),
            "bindings": len(bindings), "consistent": bool(fitted.get("consistent")),
            "rows": fitted.get("rows", []), "conflicts": fitted.get("conflicts", []),
            "unbound_circles": touched["circles"], "unbound_edges": touched["edges"],
            "join_gap_max_px": round(float(profile.get("join_max_px", 0.0)), 4) if profile else None}


def questions(diagnostics: dict, labels: dict[str, str] | None = None) -> list[str]:
    """What the flow must ask before the sketch may claim to be exact.

    A conflict is a hard question (the build waits); unbound features are reported where the user can see
    them, because the trace acknowledgement already covers "this part of the geometry is drawn, not
    dimensioned" — turning them into blocking questions would make every draft unbuildable.

    Disagreeing bindings are asked as one set question when more than one row is off: the point is that the
    *measurements* cannot all hold under one scale, not that one of them is the wrong one.
    """
    names = labels or {}
    conflicts = list(diagnostics.get("conflicts", []))
    if not conflicts:
        return []
    rows = [f"{row['value_mm']} mm → çizili {row['drawn_mm']} mm ({row['residual_mm']:+.3f} mm"
            + (f", okuma {row['span_id']}" if row.get("span_id") else "") + ")" for row in conflicts]
    if len(rows) > 1:
        return ["Bağlanan ölçüler tek ölçekle tutarlı değil: " + " · ".join(rows)
                + ". Bir bağı düzeltin ya da kaldırın."]
    row = conflicts[0]
    return [f"Bağlanan ölçü çizimle çelişiyor: {row['value_mm']} mm bağı, ölçek altında "
            f"{row['drawn_mm']} mm çiziliyor ({row['residual_mm']:+.3f} mm"
            + (f", okuma {row['span_id']}" if row.get("span_id") else "") + "). Bağı düzeltin ya da kaldırın."]
