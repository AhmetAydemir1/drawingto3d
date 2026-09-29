"""The single versioned CAD plan contract: parameters, profiles, operations.

A plan is reviewable JSON. Every number that reaches the CAD process comes from a
parameter with a recorded source, or from a small arithmetic expression over those
parameters; nothing else can be evaluated. `compile_general` turns a plan into a short
program of `geo.*` calls with numeric literals only, and `check_general` compares the
reopened STEP against what the plan declares.

A parameter's source is one of "printed" (a number read on the sheet), "derived"
(arithmetic over other parameters), "assumed" (an explicit assumption) or "user" (a
value the user typed). A model's guess is not a source in this schema: it cannot become
a validated dimension by being stored here.

Status vocabulary (`PlanStatus`): `needs_input` asks the reader for a missing decision,
`draft` is built geometry whose drawing reading still needs review, `validated` is left
for a later stage when both the plan and the drawing checks have run, `unsupported`
refuses geometry the operation set cannot express, `failed` records a build that was
attempted and did not hold. Legacy `audit.accepted` records stay what they were; nothing
here silently promotes them.
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from drawingto3d.cadrun import CadFailure, run_program
from drawingto3d.plan import PARAMETERS as PLATE_PARAMETERS
from drawingto3d.plan import PlatePlan, source_hash

MM_PER_INCH = 25.4

PlanStatus = Literal["needs_input", "draft", "validated", "unsupported", "failed"]

ParameterSource = Literal["printed", "derived", "assumed", "user"]
ParameterUnit = Literal["mm", "in", "deg", "count"]

NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
NAME_RE = re.compile(NAME_PATTERN)

# Names the CAD program uses itself; a body may not shadow them.
RESERVED_BODIES = ("geo", "cq")

# Local frames of the supported named planes (centred on the origin), matching
# CadQuery: origin, x direction, y direction, normal.
FRAMES = {
    "XY": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "XZ": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    "YZ": ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
}

_AXES = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}

# The plate experiment's two derivations, kept here because the compatibility layer
# must reproduce the stored values rather than trust them.
_PLATE_DERIVATIONS = {
    "width": "(hole_dx + 2 * ((height - hole_dy) / 2))",
    "corner_radius": "((height - hole_dy) / 2)",
}


class Parameter(BaseModel):
    """One named quantity. `value` is the number as printed, in `unit`; `expr` is
    arithmetic over other parameter names. Exactly one of the two is set."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    unit: ParameterUnit = "mm"
    source: ParameterSource = "printed"
    value: float | None = None
    expr: str | None = None
    span_ids: list[str] = Field(default_factory=list)
    explanation: str = ""

    @model_validator(mode="after")
    def _source_matches(self):
        if (self.value is None) == (self.expr is None):
            raise ValueError("parametrede value veya expr alanlarından tam biri bulunmalı")
        if self.expr is not None:
            if self.unit not in ("mm", "deg"):
                raise ValueError("ifadeli parametrenin birimi mm veya deg olmalı")
            if self.source != "derived":
                raise ValueError("ifadeli parametrenin kaynağı 'derived' olmalı")
        elif self.source == "derived":
            raise ValueError("türetilmiş parametrede expr zorunlu")
        if self.source == "printed" and not self.span_ids:
            raise ValueError("basılı ölçü en az bir ölçü kaydına (span_ids) bağlanmalı")
        if self.source in ("assumed", "user") and not self.explanation:
            raise ValueError(f"{self.source} parametrenin gerekçesi (explanation) boş olamaz")
        return self


class LineEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["line"] = "line"
    start: list[str] = Field(min_length=2, max_length=2)
    end: list[str] = Field(min_length=2, max_length=2)


class ArcEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["arc"] = "arc"
    center: list[str] = Field(min_length=2, max_length=2)
    radius: str
    start_degrees: float
    end_degrees: float


class CircleEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["circle"] = "circle"
    center: list[str] = Field(min_length=2, max_length=2)
    radius: str


Entity = Annotated[Union[LineEntity, ArcEntity, CircleEntity], Field(discriminator="type")]


class Sketch(BaseModel):
    """One named closed profile in a plane's local x/y. Coordinates are expressions
    over the plan's parameters, evaluated in millimetres; `offset` moves the profile
    along the plane normal before an operation uses it."""

    model_config = ConfigDict(extra="forbid")
    plane: Literal["XY", "XZ", "YZ"] = "XY"
    offset: str = "0"
    entities: list[Entity] = Field(min_length=1)


class ExtrudeOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["extrude"] = "extrude"
    id: str = Field(pattern=NAME_PATTERN)
    output: str = Field(pattern=NAME_PATTERN)
    sketch: str
    distance: str


class RevolveOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["revolve"] = "revolve"
    id: str = Field(pattern=NAME_PATTERN)
    output: str = Field(pattern=NAME_PATTERN)
    sketch: str
    angle: str = "360"


class LinearRepeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_pitch: str = "0"
    x_count: int = 1
    y_pitch: str = "0"
    y_count: int = 1


class CircularRepeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    axis: Literal["X", "Y", "Z"] = "Z"
    count: int = 2
    span_degrees: float = 360


class RepeatOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["repeat"] = "repeat"
    id: str = Field(pattern=NAME_PATTERN)
    output: str = Field(pattern=NAME_PATTERN)
    input: str
    linear: LinearRepeat | None = None
    circular: CircularRepeat | None = None

    @model_validator(mode="after")
    def _one_mode(self):
        if (self.linear is None) == (self.circular is None):
            raise ValueError("repeat işleminde linear veya circular alanlarından tam biri bulunmalı")
        return self


class CutOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["cut"] = "cut"
    id: str = Field(pattern=NAME_PATTERN)
    output: str = Field(pattern=NAME_PATTERN)
    target: str
    tool: str


class FuseOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["fuse"] = "fuse"
    id: str = Field(pattern=NAME_PATTERN)
    output: str = Field(pattern=NAME_PATTERN)
    inputs: list[str] = Field(min_length=2)


Operation = Annotated[Union[ExtrudeOp, RevolveOp, RepeatOp, CutOp, FuseOp], Field(discriminator="op")]


class SourceRef(BaseModel):
    """Where the plan came from. A drawing must carry its SHA256 so replay cannot
    silently use another file; synthetic compiler examples say so instead."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["drawing", "synthetic"] = "drawing"
    ref: str = ""
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    page: int = 1

    @model_validator(mode="after")
    def _hash(self):
        if self.kind == "drawing" and self.sha256 is None:
            raise ValueError("çizim kaynağı için SHA256 zorunlu")
        return self


class Expect(BaseModel):
    """What the plan says the built solid must measure: bounding box extents (x, y, z)
    and volume, both as millimetre expressions. Optional, checked only when present."""

    model_config = ConfigDict(extra="forbid")
    bbox: list[str] | None = None
    volume: str | None = None


class GeneralPlan(BaseModel):
    """Versioned general CAD plan: parameters with sources, sketches of line/arc/circle
    profiles, and a sequence of operations whose outputs are named bodies. No operation
    may branch on a filename, a part family or a reference model."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    version: Literal[1] = 1
    unit: Literal["mm"] = "mm"
    source: SourceRef
    parameters: dict[str, Parameter] = Field(min_length=1)
    sketches: dict[str, Sketch] = Field(min_length=1)
    operations: list[Operation] = Field(min_length=1)
    result: str = Field(pattern=NAME_PATTERN)
    assumptions: list[str] = Field(default_factory=list)
    expect: Expect | None = None

    @model_validator(mode="after")
    def _consistent(self):
        for name in self.parameters:
            _check_name(name, "parametre")
        for name in self.sketches:
            _check_name(name, "eskiz")
        for name, sketch in self.sketches.items():
            sketch_values(name, sketch, self.parameters)
        bodies: dict[str, object] = {}
        ids: set[str] = set()
        for operation in self.operations:
            if operation.id in ids:
                raise ValueError(f"işlem kimliği iki kez kullanılmış: {operation.id!r}")
            ids.add(operation.id)
            if operation.output in RESERVED_BODIES:
                raise ValueError(f"gövde adı ayrılmış: {operation.output!r}")
            if operation.output in bodies:
                raise ValueError(f"gövde adı iki kez üretilmiş: {operation.output!r}")
            _check_operation(operation, self.parameters, self.sketches, bodies)
            bodies[operation.output] = operation
        if self.result not in bodies:
            raise ValueError(f"result gövdesi tanımlı değil: {self.result!r}")
        if self.expect is not None:
            _check_expect(self.expect, self.parameters)
        return self


def _check_name(name: str, kind: str) -> None:
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError(f"{kind} adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: {name!r}")


# --- parameter and expression evaluation -------------------------------------------


_ALLOWED_FUNCTIONS = {"sqrt": math.sqrt, "abs": abs, "min": min, "max": max}


def _context_of(unit: str) -> str:
    if unit in ("mm", "in"):
        return "mm"
    if unit == "deg":
        return "deg"
    return "count"


def _evaluate(expr: str, parameters: dict, resolve, context: str) -> float:
    """Evaluate one expression over the parameters. Only numbers, parameter names,
    + - * / ** and sqrt/abs/min/max are allowed; a name whose unit does not fit the
    context (a degree value where a length is expected) is a unit mismatch."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"ifade ayrıştırılamadı: {expr!r}") from exc

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError(f"ifadede yalnız sayılar olabilir: {expr!r}")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in parameters:
                raise ValueError(f"ifadede tanımsız parametre: {node.id!r}")
            kind = _context_of(parameters[node.id].unit)
            if kind != context and kind != "count":
                raise ValueError(
                    f"birim uyuşmazlığı: {node.id!r} ({parameters[node.id].unit}) ifadenin beklediği {context} ile uyuşmuyor"
                )
            return resolve(node.id)
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ValueError(f"ifadede sıfıra bölme: {expr!r}")
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            raise ValueError(f"ifadede izin verilmeyen işlem: {expr!r}")
        if isinstance(node, ast.UnaryOp):
            operand = walk(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return operand
            raise ValueError(f"ifadede izin verilmeyen işlem: {expr!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
                raise ValueError(f"ifadede izin verilmeyen fonksiyon: {expr!r}")
            if node.keywords:
                raise ValueError(f"ifadede anahtar kelime argümanı kullanılamaz: {expr!r}")
            arguments = [walk(argument) for argument in node.args]
            try:
                return float(_ALLOWED_FUNCTIONS[node.func.id](*arguments))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"ifade hesaplanamadı: {expr!r}") from exc
        raise ValueError(f"ifadede izin verilmeyen öğe: {expr!r}")

    try:
        value = float(walk(tree))
    except ValueError:
        raise
    except (ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"ifade hesaplanamadı: {expr!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"ifade sonlu bir sayı vermedi: {expr!r}")
    return value


def evaluate_parameters(parameters: dict[str, Parameter]) -> dict[str, float]:
    """Canonical values of every parameter: lengths in millimetres, angles in degrees,
    counts as plain numbers. Raises on cycles, unknown names and unit mismatch — the
    same rules the plan validator applies."""
    resolved: dict[str, float] = {}
    visiting: set[str] = set()

    def resolve(name: str) -> float:
        if name in resolved:
            return resolved[name]
        if name not in parameters:
            raise ValueError(f"tanımsız parametre: {name!r}")
        if name in visiting:
            raise ValueError(f"döngüsel parametre bağımlılığı: {name!r}")
        visiting.add(name)
        parameter = parameters[name]
        if parameter.expr is not None:
            value = _evaluate(parameter.expr, parameters, resolve, parameter.unit)
        else:
            if parameter.value is None:  # unreachable: the validator keeps exactly one of value/expr
                raise ValueError(f"parametrede değer yok: {name!r}")
            value = float(parameter.value)
            if parameter.unit == "in":
                value *= MM_PER_INCH
        visiting.discard(name)
        resolved[name] = value
        return value

    for name in parameters:
        resolve(name)
    return resolved


def sketch_values(name: str, sketch: Sketch, parameters: dict[str, Parameter]) -> list[dict]:
    """Numeric entity dicts for one sketch, with the closure check the CAD verb would
    otherwise raise from inside the worker."""
    resolved = evaluate_parameters(parameters)

    def length(expr: str) -> float:
        return _evaluate(expr, parameters, resolved.__getitem__, "mm")

    entities: list[dict] = []
    for index, entity in enumerate(sketch.entities):
        where = f"{name}: şekil {index}"
        if isinstance(entity, LineEntity):
            entities.append(
                {"type": "line", "start": [length(e) for e in entity.start], "end": [length(e) for e in entity.end]}
            )
        elif isinstance(entity, ArcEntity):
            radius = length(entity.radius)
            if radius <= 0:
                raise ValueError(f"{where}: yay yarıçapı pozitif olmalı")
            entities.append(
                {
                    "type": "arc",
                    "center": [length(e) for e in entity.center],
                    "radius": radius,
                    "start_degrees": float(entity.start_degrees),
                    "end_degrees": float(entity.end_degrees),
                }
            )
        else:
            radius = length(entity.radius)
            if radius <= 0:
                raise ValueError(f"{where}: daire yarıçapı pozitif olmalı")
            entities.append({"type": "circle", "center": [length(e) for e in entity.center], "radius": radius})
    _closed_profile(entities, name)
    return entities


def sketch_offset(name: str, sketch: Sketch, parameters: dict[str, Parameter]) -> float:
    resolved = evaluate_parameters(parameters)
    return _evaluate(sketch.offset, parameters, resolved.__getitem__, "mm")


def _closed_profile(entities: list[dict], name: str) -> None:
    if any(entity["type"] == "circle" for entity in entities):
        if len(entities) != 1:
            raise ValueError(f"{name}: daire tek başına profil olmalı")
        return
    if len(entities) < 3:
        raise ValueError(f"{name}: profil en az üç kenardan oluşmalı")
    starts: list[list[float]] = []
    ends: list[list[float]] = []
    for entity in entities:
        if entity["type"] == "line":
            starts.append(entity["start"])
            ends.append(entity["end"])
            continue
        center_x, center_y = entity["center"]
        radius = entity["radius"]
        span = entity["end_degrees"] - entity["start_degrees"]
        if span == 0 or abs(span) >= 360:
            raise ValueError(f"{name}: yay açıklığı −360 ile 360 derece arasında ve sıfırdan farklı olmalı, {span:g} bulundu")
        for degrees, bucket in ((entity["start_degrees"], starts), (entity["end_degrees"], ends)):
            radians = math.radians(degrees)
            bucket.append([center_x + radius * math.cos(radians), center_y + radius * math.sin(radians)])
    tolerance = 1e-6
    for index in range(len(entities)):
        following = (index + 1) % len(entities)
        if math.dist(ends[index], starts[following]) > tolerance:
            raise ValueError(f"{name}: profil kapalı değil; {index}. parça {following}. parçaya birleşmiyor")


def _length(expr: str, parameters: dict[str, Parameter], resolved: dict[str, float]) -> float:
    return _evaluate(expr, parameters, resolved.__getitem__, "mm")


def _degrees(expr: str, parameters: dict[str, Parameter], resolved: dict[str, float]) -> float:
    return _evaluate(expr, parameters, resolved.__getitem__, "deg")


def _check_operation(operation, parameters, sketches, bodies) -> None:
    resolved = evaluate_parameters(parameters)
    if isinstance(operation, (ExtrudeOp, RevolveOp)):
        if operation.sketch not in sketches:
            raise ValueError(f"işlem {operation.id!r}: tanımsız eskiz {operation.sketch!r}")
        if isinstance(operation, ExtrudeOp):
            if _length(operation.distance, parameters, resolved) <= 0:
                raise ValueError(f"işlem {operation.id!r}: extrude mesafesi pozitif olmalı")
        else:
            angle = _degrees(operation.angle, parameters, resolved)
            if not 0 < angle <= 360:
                raise ValueError(f"işlem {operation.id!r}: dönme açısı 0 ile 360 arasında olmalı")
        return
    if isinstance(operation, RepeatOp):
        if operation.input not in bodies:
            raise ValueError(f"işlem {operation.id!r}: tanımsız gövde {operation.input!r}")
        if operation.linear is not None:
            linear = operation.linear
            for label, pitch, count in (("x", linear.x_pitch, linear.x_count), ("y", linear.y_pitch, linear.y_count)):
                value = _length(pitch, parameters, resolved)
                if count < 1:
                    raise ValueError(f"işlem {operation.id!r}: {label}_count en az 1 olmalı")
                if count > 1 and value <= 0:
                    raise ValueError(f"işlem {operation.id!r}: {label}_pitch pozitif olmalı (count > 1)")
            if linear.x_count == 1 and linear.y_count == 1:
                raise ValueError(f"işlem {operation.id!r}: tekrarda en az bir yönde count 2 veya daha fazla olmalı")
        elif operation.circular is not None:
            circular = operation.circular
            if circular.count < 2:
                raise ValueError(f"işlem {operation.id!r}: dairesel tekrarda count en az 2 olmalı")
            if not 0 < circular.span_degrees <= 360:
                raise ValueError(f"işlem {operation.id!r}: span_degrees 0 ile 360 arasında olmalı")
        return
    if isinstance(operation, CutOp):
        for name in (operation.target, operation.tool):
            if name not in bodies:
                raise ValueError(f"işlem {operation.id!r}: tanımsız gövde {name!r}")
        return
    if isinstance(operation, FuseOp):
        for name in operation.inputs:
            if name not in bodies:
                raise ValueError(f"işlem {operation.id!r}: tanımsız gövde {name!r}")


def _check_expect(expect: Expect, parameters) -> None:
    resolved = evaluate_parameters(parameters)
    if expect.bbox is not None:
        if len(expect.bbox) != 3:
            raise ValueError("expect.bbox üç ifade olmalı: [x, y, z]")
        for expr in expect.bbox:
            if _length(expr, parameters, resolved) <= 0:
                raise ValueError("expect.bbox ölçüleri pozitif olmalı")
    if expect.volume is not None and _length(expect.volume, parameters, resolved) <= 0:
        raise ValueError("expect.volume pozitif olmalı")


def _literal(value) -> str:
    """Deterministic Python literal for numeric structures; no booleans or strings here."""
    return json.dumps(value)


def compile_general(plan: GeneralPlan) -> str:
    """Plan to CAD program: `geo.*` calls with numeric literals only. Nothing in the
    output reads the source name, the file name or any part family, so the same plan
    text builds the same solid everywhere."""
    resolved = evaluate_parameters(plan.parameters)
    lines: list[str] = []
    for operation in plan.operations:
        if isinstance(operation, ExtrudeOp):
            sketch = plan.sketches[operation.sketch]
            entities = sketch_values(operation.sketch, sketch, plan.parameters)
            offset = sketch_offset(operation.sketch, sketch, plan.parameters)
            lines.append(
                f"{operation.output} = geo.profile_extrude({_literal(entities)}, "
                f"{float(_length(operation.distance, plan.parameters, resolved))!r}, "
                f"plane={sketch.plane!r}, offset={float(offset)!r})"
            )
        elif isinstance(operation, RevolveOp):
            sketch = plan.sketches[operation.sketch]
            entities = sketch_values(operation.sketch, sketch, plan.parameters)
            offset = sketch_offset(operation.sketch, sketch, plan.parameters)
            angle = float(_degrees(operation.angle, plan.parameters, resolved))
            lines.append(
                f"{operation.output} = geo.profile_revolve({_literal(entities)}, {angle!r}, "
                f"plane={sketch.plane!r}, offset={float(offset)!r})"
            )
        elif isinstance(operation, RepeatOp):
            if operation.linear is not None:
                linear = operation.linear
                x_pitch = float(_length(linear.x_pitch, plan.parameters, resolved))
                y_pitch = float(_length(linear.y_pitch, plan.parameters, resolved))
                lines.append(
                    f"{operation.output} = geo.repeat_linear({operation.input}, "
                    f"x_pitch={x_pitch!r}, x_count={linear.x_count}, "
                    f"y_pitch={y_pitch!r}, y_count={linear.y_count})"
                )
            elif operation.circular is not None:
                circular = operation.circular
                lines.append(
                    f"{operation.output} = geo.repeat_circular({operation.input}, {circular.count}, "
                    f"span_degrees={float(circular.span_degrees)!r}, axis={circular.axis!r})"
                )
        elif isinstance(operation, CutOp):
            lines.append(f"{operation.output} = geo.cut({operation.target}, {operation.tool})")
        else:
            lines.append(f"{operation.output} = geo.fuse({', '.join(operation.inputs)})")
    lines.append(f"solid = {plan.result}")
    return "\n".join(lines) + "\n"


def check_general(plan: GeneralPlan, facts: dict) -> dict:
    """Compare the reopened STEP with what the plan declares: a valid single solid, an
    export round trip that did not change the volume, the declared bounding box and
    volume when present, and every cylinder a cut tool must have removed. Tools that
    are not plain cylinders are reported as unverified rather than silently passed."""
    checks: dict[str, bool] = {}
    checks["valid_solid"] = facts.get("valid") is True and facts.get("solids") == 1
    before, after = facts.get("volume_before_export"), facts.get("volume")
    # Writing and reopening the STEP perturbs volumes by kernel noise (measured 2.6e-9
    # relative on an approximated intersection curve), so this check is about catching a
    # broken export, not about carrying the kernel's own round-off.
    checks["export_round_trip"] = (
        isinstance(before, (int, float))
        and isinstance(after, (int, float))
        and abs(before - after) <= max(1e-6, abs(before) * 1e-7)
    )
    resolved = evaluate_parameters(plan.parameters)
    if plan.expect is not None and plan.expect.bbox is not None:
        wanted = [_length(expr, plan.parameters, resolved) for expr in plan.expect.bbox]
        size = facts.get("size") or []
        checks["declared_bbox"] = len(size) == 3 and all(abs(a - b) <= 1e-3 for a, b in zip(size, wanted))
    if plan.expect is not None and plan.expect.volume is not None:
        wanted_volume = _length(plan.expect.volume, plan.parameters, resolved)
        checks["declared_volume"] = isinstance(after, (int, float)) and abs(after - wanted_volume) <= max(
            1e-6, abs(wanted_volume) * 1e-7
        )
    tool_checks = [
        _check_cut_tool(plan, operation, facts) for operation in plan.operations if isinstance(operation, CutOp)
    ]
    passed = all(checks.values()) and all(item["ok"] for item in tool_checks)
    return {
        "status": "draft" if passed else "failed",
        "passed": passed,
        "checks": checks,
        "tool_checks": tool_checks,
        "scope": "CAD geometry matches the proposed plan; the drawing reading is not part of this check.",
    }


class Cylinder(BaseModel):
    """An expected cylindrical cut, in world coordinates. `lo`/`hi` run along `direction`
    from `point`."""

    radius: float
    point: tuple[float, float, float]
    direction: tuple[float, float, float]
    lo: float
    hi: float


def _cut_tool_cylinders(plan: GeneralPlan, body_name: str) -> list[Cylinder] | None:
    """The cylinders a tool body is made of, following the operations that built it.
    Returns None when the recipe is not a plain collection of cylinders."""
    operation = next((item for item in plan.operations if item.output == body_name), None)
    if operation is None:
        return None
    if isinstance(operation, ExtrudeOp):
        sketch = plan.sketches[operation.sketch]
        entities = sketch_values(operation.sketch, sketch, plan.parameters)
        offset = sketch_offset(operation.sketch, sketch, plan.parameters)
        if len(entities) != 1 or entities[0]["type"] != "circle":
            return None
        circle = entities[0]
        origin, x_dir, y_dir, normal = FRAMES[sketch.plane]
        resolved = evaluate_parameters(plan.parameters)
        distance = _length(operation.distance, plan.parameters, resolved)
        point = tuple(
            origin[i] + x_dir[i] * circle["center"][0] + y_dir[i] * circle["center"][1] + normal[i] * offset
            for i in range(3)
        )
        return [Cylinder(radius=circle["radius"], point=point, direction=normal, lo=0.0, hi=distance)]
    if isinstance(operation, RepeatOp):
        base = _cut_tool_cylinders(plan, operation.input)
        if base is None:
            return None
        if operation.linear is not None:
            linear = operation.linear
            resolved = evaluate_parameters(plan.parameters)
            x_pitch = _length(linear.x_pitch, plan.parameters, resolved)
            y_pitch = _length(linear.y_pitch, plan.parameters, resolved)
            copies = []
            for i in range(linear.x_count):
                for j in range(linear.y_count):
                    x = x_pitch * (i - (linear.x_count - 1) / 2)
                    y = y_pitch * (j - (linear.y_count - 1) / 2)
                    copies += [
                        Cylinder(radius=item.radius, point=(item.point[0] + x, item.point[1] + y, item.point[2]),
                                 direction=item.direction, lo=item.lo, hi=item.hi)
                        for item in base
                    ]
            return copies
        if operation.circular is not None:
            circular = operation.circular
            axis = _AXES[circular.axis]
            step = (circular.span_degrees / circular.count if circular.span_degrees >= 360
                    else circular.span_degrees / (circular.count - 1))
            copies = []
            for index in range(circular.count):
                angle = index * step
                for item in base:
                    copies.append(
                        Cylinder(radius=item.radius, point=_rotate(item.point, axis, angle),
                                 direction=_rotate(item.direction, axis, angle), lo=item.lo, hi=item.hi)
                    )
            return copies
        return None
    if isinstance(operation, FuseOp):
        cylinders: list[Cylinder] = []
        for name in operation.inputs:
            part = _cut_tool_cylinders(plan, name)
            if part is None:
                return None
            cylinders += part
        return cylinders
    return None


def _rotate(vector, axis, degrees):
    radians = math.radians(degrees)
    cos, sin = math.cos(radians), math.sin(radians)
    kx, ky, kz = axis
    x, y, z = vector
    dot = kx * x + ky * y + kz * z
    cross = (ky * z - kz * y, kz * x - kx * z, kx * y - ky * x)
    return (
        x * cos + cross[0] * sin + kx * dot * (1 - cos),
        y * cos + cross[1] * sin + ky * dot * (1 - cos),
        z * cos + cross[2] * sin + kz * dot * (1 - cos),
    )


def _canonical(direction):
    first = next((value for value in direction if abs(value) > 1e-9), 1.0)
    if first < 0:
        return tuple(-value for value in direction)
    return tuple(direction)


def _cylinder_matches(reported: list, expected: Cylinder) -> bool:
    if len(reported) != 9:
        return False
    radius, px, py, pz, dx, dy, dz, lo, hi = reported
    if abs(radius - expected.radius) > 1e-3:
        return False
    direction = _canonical((dx, dy, dz))
    wanted = _canonical(expected.direction)
    if sum(a * b for a, b in zip(direction, wanted)) < 1 - 1e-9:
        return False
    offset = (px - expected.point[0], py - expected.point[1], pz - expected.point[2])
    cross = (
        offset[1] * wanted[2] - offset[2] * wanted[1],
        offset[2] * wanted[0] - offset[0] * wanted[2],
        offset[0] * wanted[1] - offset[1] * wanted[0],
    )
    if math.sqrt(sum(value * value for value in cross)) > 1e-3:
        return False
    # Expected lo/hi run along the tool's own normal; flip them when the canonical
    # direction points the other way, so both sides measure along `wanted`.
    if sum(a * b for a, b in zip(wanted, expected.direction)) < 0:
        lo, hi = -expected.hi, -expected.lo
    else:
        lo, hi = expected.lo, expected.hi
    shift = sum(value * unit for value, unit in zip(offset, wanted))
    tool_lo, tool_hi = lo - shift, hi - shift
    return lo >= tool_lo - 1e-3 and hi <= tool_hi + 1e-3


def _check_cut_tool(plan: GeneralPlan, operation: CutOp, facts: dict) -> dict:
    expected = _cut_tool_cylinders(plan, operation.tool)
    if expected is None:
        return {
            "operation": operation.id,
            "ok": True,
            "unverified": True,
            "reason": "araç gövdesi düz silindirlerden oluşmuyor; bu kesim bu denetimde doğrulanamaz",
        }
    available = list(facts.get("cylinders_axis", []))
    missing = []
    for cylinder in expected:
        match = next((index for index, got in enumerate(available) if _cylinder_matches(got, cylinder)), None)
        if match is None:
            missing.append(cylinder)
        else:
            available.pop(match)
    if missing:
        return {
            "operation": operation.id,
            "ok": False,
            "unverified": False,
            "cylinders": len(expected),
            "missing": len(missing),
            "reason": f"{len(missing)} silindir yeniden açılan katıda beklenen yerde bulunamadı",
        }
    return {"operation": operation.id, "ok": True, "unverified": False, "cylinders": len(expected)}


def build_general(plan: GeneralPlan, drawing: str | Path | None, folder: str | Path) -> tuple[Path, Path]:
    """Revalidate, check the source hash when the plan names a drawing, compile, run the
    CAD interpreter, and audit the reopened STEP against the plan. Writes `plan.json`
    and `plan-audit.json`; a failed audit raises CadFailure after the record is written."""
    plan = GeneralPlan.model_validate(plan.model_dump())
    if plan.source.kind == "drawing":
        if drawing is None:
            raise ValueError("çizim kaynağı için drawing yolu gerekli")
        if source_hash(drawing) != plan.source.sha256:
            raise ValueError("plan başka bir çizime ait; kaynak özeti uyuşmuyor")
    elif drawing is not None and plan.source.sha256 is not None:
        if source_hash(drawing) != plan.source.sha256:
            raise ValueError("plan başka bir çizime ait; kaynak özeti uyuşmuyor")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    code = compile_general(plan)
    step, stl = run_program(code, folder)
    facts = json.loads((folder / "geometry.json").read_text(encoding="utf-8"))
    audit = check_general(plan, facts)
    (folder / "plan-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if not audit["passed"]:
        raise CadFailure("katı genel planla uyuşmuyor: " + str(audit["checks"]), code)
    return step, stl


def edit_parameters(plan: GeneralPlan, changes: dict[str, float]) -> GeneralPlan:
    """The user's edits: each named parameter takes the new value with source "user". A
    derived parameter the user overrides stops being derived; the others recompute,
    because they stay expressions over the edited values."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("değişiklik sözlüğü boş olamaz")
    unknown = set(changes) - set(plan.parameters)
    if unknown:
        raise ValueError(f"bilinmeyen parametre: {sorted(unknown)}")
    data = plan.model_dump()
    for name, raw in changes.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise ValueError(f"{name}: değer sonlu bir sayı olmalı")
        entry = data["parameters"][name]
        entry["value"] = float(raw)
        entry["expr"] = None
        entry["source"] = "user"
        entry["explanation"] = "Kullanıcı tarafından değiştirildi."
    return GeneralPlan.model_validate(data)


# --- plate compatibility layer ------------------------------------------------------


def from_plate(plate: PlatePlan, ref: str | None = None) -> GeneralPlan:
    """The plate experiment expressed as the general operations it already is: a rounded
    profile extruded once, a centred 2x2 hole pattern cut through, a centred pocket cut
    from the top. Derived plate values are re-derived from their expressions and checked
    against the stored millimetres; this layer is the only place plate knowledge lives."""
    parameters: dict[str, Parameter] = {}
    for name in PLATE_PARAMETERS:
        evidence = plate.evidence[name]
        if evidence.kind == "derived":
            parameters[name] = Parameter(
                unit="mm", source="derived", expr=_PLATE_DERIVATIONS[name],
                span_ids=list(evidence.span_ids), explanation=evidence.explanation,
            )
        else:
            parameters[name] = Parameter(
                unit="mm", source=evidence.kind, value=float(getattr(plate, name)),
                span_ids=list(evidence.span_ids), explanation=evidence.explanation,
            )
    resolved = evaluate_parameters(parameters)
    for name in PLATE_PARAMETERS:
        if parameters[name].expr is not None:
            if abs(resolved[name] - float(getattr(plate, name))) > 1e-6:
                raise ValueError(f"plaka türetmesi ifadeyle uyuşmuyor: {name}")
    half_width, half_height = "width / 2", "height / 2"
    quarter_x = "(width - 2 * corner_radius) / 2"
    quarter_y = "(height - 2 * corner_radius) / 2"
    entities = [
        {"type": "line", "start": [f"-({quarter_x})", f"-({half_height})"], "end": [quarter_x, f"-({half_height})"]},
        {"type": "arc", "center": [quarter_x, f"-({quarter_y})"], "radius": "corner_radius",
         "start_degrees": -90, "end_degrees": 0},
        {"type": "line", "start": [half_width, f"-({quarter_y})"], "end": [half_width, quarter_y]},
        {"type": "arc", "center": [quarter_x, quarter_y], "radius": "corner_radius",
         "start_degrees": 0, "end_degrees": 90},
        {"type": "line", "start": [quarter_x, half_height], "end": [f"-({quarter_x})", half_height]},
        {"type": "arc", "center": [f"-({quarter_x})", quarter_y], "radius": "corner_radius",
         "start_degrees": 90, "end_degrees": 180},
        {"type": "line", "start": [f"-({half_width})", quarter_y], "end": [f"-({half_width})", f"-({quarter_y})"]},
        {"type": "arc", "center": [f"-({quarter_x})", f"-({quarter_y})"], "radius": "corner_radius",
         "start_degrees": 180, "end_degrees": 270},
    ]
    sketches = {
        "outline": {"plane": "XY", "offset": "0", "entities": entities},
        "hole": {"plane": "XY", "offset": "-1",
                 "entities": [{"type": "circle", "center": ["0", "0"], "radius": "hole_diameter / 2"}]},
        "pocket": {"plane": "XY", "offset": "(thickness - pocket_depth)",
                   "entities": [{"type": "circle", "center": ["0", "0"], "radius": "pocket_diameter / 2"}]},
    }
    operations = [
        {"op": "extrude", "id": "outer", "output": "body", "sketch": "outline", "distance": "thickness"},
        {"op": "extrude", "id": "hole_pin", "output": "hole_tool", "sketch": "hole",
         "distance": "thickness + 2"},
        {"op": "repeat", "id": "hole_grid", "input": "hole_tool", "output": "hole_tools",
         "linear": {"x_pitch": "hole_dx", "x_count": 2, "y_pitch": "hole_dy", "y_count": 2}},
        {"op": "extrude", "id": "pocket_pin", "output": "pocket_tool", "sketch": "pocket",
         "distance": "pocket_depth"},
        {"op": "cut", "id": "holes", "target": "body", "tool": "hole_tools", "output": "body_cut"},
        {"op": "cut", "id": "pocket", "target": "body_cut", "tool": "pocket_tool", "output": "finished"},
    ]
    return GeneralPlan(
        version=1, unit="mm",
        source=SourceRef(kind="drawing", ref=ref or "plate drawing", sha256=plate.source_sha256),
        parameters=parameters, sketches=sketches, operations=operations, result="finished",
        assumptions=list(plate.assumptions),
        expect=Expect(bbox=["width", "height", "thickness"]),
    )
