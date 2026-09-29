"""Exact X/Y dimensions over explicitly selected sketch points.

Each supported constraint is a coordinate difference, not a part-family rule. A forest
of those differences exposes conflicting cycles and the remaining free coordinates.
Free components stay as close as possible to the traced drawing. Their parameters keep
the ``assumed`` source; constrained coordinates are expressions over user dimensions.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PointRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["vertex", "circle_center"]
    id: str = Field(min_length=1, max_length=200)

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.id}"


class EdgeRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["horizontal", "vertical"]
    edge_id: str = Field(min_length=1, max_length=200)


class DimensionBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str = Field(min_length=1, max_length=100)
    axis: Literal["x", "y"]
    first: PointRef
    second: PointRef
    direction: Literal[-1, 1]
    value: float = Field(gt=0, le=1e6)
    unit: Literal["mm", "in"] = "mm"
    span_id: str | None = None


class SketchConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=200)
    datum: PointRef
    relations: list[EdgeRelation] = Field(default_factory=list, max_length=500)
    dimensions: list[DimensionBinding] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [row.id for row in [*self.relations, *self.dimensions]]
        if len(set(ids)) != len(ids):
            raise ValueError("ölçü ve ilişki kimlikleri tekil olmalı")
        return self


def _pair(value, label: str) -> list[float]:
    try:
        pair = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: iki sonlu koordinat gerekli") from exc
    if len(pair) != 2 or not all(math.isfinite(item) for item in pair):
        raise ValueError(f"{label}: iki sonlu koordinat gerekli")
    return pair


def _path(graph: dict, first: str, second: str):
    """Return the existing forest path, or None when the points are disconnected."""
    parents = {first: None}
    queue = deque([first])
    while queue:
        point = queue.popleft()
        if point == second:
            result = []
            while parents[point] is not None:
                previous, step = parents[point]
                result.append(step)
                point = previous
            return list(reversed(result))
        for step in graph[point]:
            target = step["target"]
            if target not in parents:
                parents[target] = (point, step)
                queue.append(target)
    return None


def _expression(root: str, terms: dict[str, int]) -> str:
    parts = [root]
    for name, coefficient in sorted(terms.items()):
        if coefficient:
            factor = name if abs(coefficient) == 1 else f"{abs(coefficient)} * {name}"
            parts.append((" + " if coefficient > 0 else " - ") + factor)
    return "".join(parts)


def solve_constraints(
    profile: dict,
    circles: list[dict],
    scale: float,
    origin: list[float],
    constraints: SketchConstraints,
    measurement_ids: set[str],
) -> dict:
    """Solve the selected dimensions in calibrated, Y-up millimetre coordinates.

    ``scale`` is pixels/mm. The datum stays at its traced coordinates; it selects the
    coordinate gauge, not a new manufactured dimension. ``dof`` excludes its two rigid
    translation coordinates. For a line-only outer wire, vertices may move. For an arc
    wire or circle outer, only the supplied circle centres participate; the outer trace
    stays unchanged and its unmeasured shape is explicitly outside the reported DOFs.

    Invalid identities raise ValueError. Geometrically contradictory decisions instead
    return ``status='conflict'`` with the involved constraint IDs and no usable geometry.
    """
    constraints = SketchConstraints.model_validate(constraints)
    if constraints.profile_id != profile.get("id"):
        raise ValueError("ölçü bağları seçili kontura ait değil")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("ölçek pozitif ve sonlu olmalı")
    origin = _pair(origin, "koordinat başlangıcı")
    if profile.get("kind") not in ("wire", "circle"):
        raise ValueError("desteklenmeyen dış kontur türü")
    edges = profile.get("edges", [])
    if profile["kind"] == "wire" and (not edges or any(e.get("kind") not in ("line", "arc") for e in edges)):
        raise ValueError("kontur çizgi veya yaylardan oluşmalı")
    outer_moves = profile["kind"] == "wire" and all(edge["kind"] == "line" for edge in edges)
    points: dict[str, list[float]] = {}
    edge_vertices = {}

    def calibrated(point) -> list[float]:
        x, y = _pair(point, "çizim noktası")
        return [(x - origin[0]) / scale, (origin[1] - y) / scale]

    if outer_moves:
        if len(edges) < 3:
            raise ValueError("kapalı çizgi konturu en az üç kenar içermeli")
        for index, edge in enumerate(edges):
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id or edge_id in edge_vertices:
                raise ValueError("kontur kenarı kimlikleri tekil olmalı")
            key = f"vertex:v{index}"
            next_key = f"vertex:v{(index + 1) % len(edges)}"
            points[key] = calibrated(edge.get("start"))
            endpoint = _pair(edge.get("end"), "kenar ucu")
            next_start = _pair(edges[(index + 1) % len(edges)].get("start"), "kenar başlangıcı")
            if math.dist(endpoint, next_start) > 1e-6:
                raise ValueError("ölçü çözümü için çizgi konturu kapalı olmalı")
            edge_vertices[edge_id] = (key, next_key)
    for circle in circles:
        circle_id = circle.get("id")
        if not isinstance(circle_id, str) or not circle_id:
            raise ValueError("daire kimliği eksik")
        key = f"circle_center:{circle_id}"
        if key in points:
            raise ValueError("daire kimlikleri tekil olmalı")
        points[key] = calibrated(circle.get("center"))

    def check_reference(reference: PointRef) -> None:
        if not outer_moves and reference.kind == "vertex":
            raise ValueError("yaylı veya dairesel dış konturda yalnız daire merkezleri ölçülendirilebilir")
        if reference.key not in points:
            raise ValueError(f"ölçü noktası seçili geometride yok: {reference.key}")

    check_reference(constraints.datum)
    if not outer_moves and constraints.relations:
        raise ValueError("yaylı veya dairesel dış konturda kenar ilişkisi bu dilimde desteklenmiyor")

    equations = {"x": [], "y": []}
    parameters = {}
    for relation in constraints.relations:
        if relation.edge_id not in edge_vertices:
            raise ValueError(f"ilişkinin kenarı seçili konturda yok: {relation.edge_id}")
        first, second = edge_vertices[relation.edge_id]
        axis = "y" if relation.kind == "horizontal" else "x"
        equations[axis].append((first, second, 0.0, relation.id, None, 0))
    for index, dimension in enumerate(constraints.dimensions):
        check_reference(dimension.first)
        check_reference(dimension.second)
        if dimension.span_id is not None and dimension.span_id not in measurement_ids:
            raise ValueError(f"ölçünün basılı kaynağı bu çizimde yok: {dimension.span_id}")
        name = f"sk_dim_{index}"
        parameters[name] = {
            "source": "user", "value": dimension.value, "unit": dimension.unit,
            "span_ids": [dimension.span_id] if dimension.span_id is not None else [],
            "explanation": f"Kullanıcının {dimension.id} ölçüsü ve geometri bağı; basılı kaynağın bağını kullanıcı seçti.",
        }
        value_mm = dimension.value * (25.4 if dimension.unit == "in" else 1.0)
        equations[dimension.axis].append((dimension.first.key, dimension.second.key,
                                          value_mm * dimension.direction, dimension.id, name, dimension.direction))

    graphs = {axis: {key: [] for key in points} for axis in ("x", "y")}
    conflicts, redundant = [], []
    for axis, rows in equations.items():
        graph = graphs[axis]
        for first, second, delta, constraint_id, parameter, coefficient in rows:
            path = _path(graph, first, second)
            if path is not None:
                actual = math.fsum(step["delta"] for step in path)
                tolerance = 1e-6 + 1e-12 * max(abs(actual), abs(delta))
                if abs(actual - delta) > tolerance:
                    conflicts.append({"constraint_ids": [step["id"] for step in path] + [constraint_id],
                                      "axis": axis, "expected_mm": delta, "actual_mm": actual,
                                      "error_mm": actual - delta})
                else:
                    redundant.append(constraint_id)
                continue
            graph[first].append({"target": second, "delta": delta, "id": constraint_id,
                                 "parameter": parameter, "coefficient": coefficient})
            graph[second].append({"target": first, "delta": -delta, "id": constraint_id,
                                  "parameter": parameter, "coefficient": -coefficient})

    notes = ["Başlangıç noktasının çizimdeki konumu yalnız koordinat sistemini sabitler; parça ölçüsü değildir."]
    if not outer_moves:
        notes.append("Yaylı/dairesel dış kontur çizimden izlenen taslak olarak kalır. Serbestlik sayısı yalnız seçili daire merkezlerini kapsar.")
    result = {"points": {}, "parameters": parameters, "expressions": {}, "status": "conflict" if conflicts else "underconstrained",
              "dof": 0, "conflicts": conflicts, "redundant": redundant, "notes": notes,
              "outer_moves": outer_moves, "gauge": {"datum": constraints.datum.key,
                                                       "position_mm": list(points[constraints.datum.key])},
              "free_coordinates": []}
    values = {key: [0.0, 0.0] for key in points}
    expressions = {key: ["", ""] for key in points}
    indices = {key: index for index, key in enumerate(points)}
    for axis_index, axis in enumerate(("x", "y")):
        graph, visited = graphs[axis], set()
        # Visit the datum's component first so its offset is the original datum position.
        for root in [constraints.datum.key, *points]:
            if root in visited:
                continue
            offsets = {root: 0.0}
            terms = {root: {}}
            queue = deque([root])
            while queue:
                point = queue.popleft()
                visited.add(point)
                for step in graph[point]:
                    target = step["target"]
                    if target in offsets:
                        continue
                    offsets[target] = offsets[point] + step["delta"]
                    terms[target] = dict(terms[point])
                    if step["parameter"] is not None:
                        name = step["parameter"]
                        terms[target][name] = terms[target].get(name, 0) + step["coefficient"]
                    queue.append(target)
            anchored = root == constraints.datum.key
            root_name = f"sk_root_{axis}_{indices[root]}"
            if anchored:
                root_value = points[root][axis_index]
                explanation = "Kullanıcının seçtiği başlangıç noktasının çizim konumu; yalnız koordinat sistemi tercihi, şekil ölçüsü değil."
            else:
                result["dof"] += 1
                root_value = math.fsum(points[key][axis_index] - offset for key, offset in offsets.items()) / len(offsets)
                explanation = "Bu koordinat bileşeni ölçülerle belirlenmedi; çizime en yakın konumu taslak varsayımı olarak korundu."
                result["free_coordinates"].append({"axis": axis, "root_parameter": root_name, "points": list(offsets)})
            parameters[root_name] = {"source": "assumed", "value": root_value, "unit": "mm", "explanation": explanation}
            for point, offset in offsets.items():
                coordinate_name = f"sk_point_{indices[point]}_{axis}"
                parameters[coordinate_name] = {"source": "derived", "expr": _expression(root_name, terms[point]),
                                              "unit": "mm", "explanation": "Kaydedilmiş koordinat ilişkileri ve kullanıcı ölçülerinden hesaplandı."}
                values[point][axis_index] = root_value + offset
                expressions[point][axis_index] = coordinate_name
    if not conflicts:
        result["points"], result["expressions"] = values, expressions
        result["status"] = "constrained" if result["dof"] == 0 else "underconstrained"
    else:
        # Keep the submitted dimensions as evidence, but no arbitrary solution to a subset.
        result["parameters"] = {key: value for key, value in parameters.items() if key.startswith("sk_dim_")}
        result["notes"].append("Çelişen ölçüler çözülmeden bu revizyonun geometrisi üretilemez.")
    return result
