"""Run one CadQuery program in a short-lived process. The process has no network of its own."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

GEO_MODULE = Path(__file__).resolve().parent / "geo.py"

RUNNER = textwrap.dedent(
    """
    import importlib.util
    import json
    import sys
    import traceback
    from pathlib import Path

    import cadquery as cq

    spec = importlib.util.spec_from_file_location("geo", r"{geo}")
    geo = importlib.util.module_from_spec(spec)
    sys.modules["geo"] = geo
    spec.loader.exec_module(geo)

    source = Path("program.py").read_text()
    namespace = {{"cq": cq, "geo": geo, "__name__": "__main__"}}
    try:
        exec(compile(source, "program.py", "exec"), namespace)
    except Exception as exc:
        frames = [frame for frame in traceback.extract_tb(exc.__traceback__) if frame.filename == "program.py"]
        where = "\\nline %d: %s" % (frames[-1].lineno, frames[-1].line) if frames else ""
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
    step = Path(r"{step}")
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
    Path("measure.txt").write_text("%.6f %.6f %.6f\\n" % (bb.xlen, bb.ylen, bb.zlen))
    """
)


class CadFailure(RuntimeError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.stderr = message
        self.code = code


def _cad_python() -> str:
    """CadQuery cannot share build123d's OpenCascade 8 install."""
    override = os.environ.get("DRAWINGTO3D_CADQUERY_PYTHON")
    if override:
        return override
    sibling = Path(__file__).resolve().parents[2] / ".venv-cad" / "bin" / "python"
    if sibling.is_file():
        return str(sibling)
    return sys.executable


def _child_env() -> dict[str, str]:
    """The runner only executes the script. Drop credentials and proxy settings."""
    blocked = ("PROXY", "TOKEN", "SECRET", "KEY", "PASSWORD", "AWS_", "HF_")
    return {
        key: value
        for key, value in os.environ.items()
        if not any(part in key.upper() for part in blocked)
    }


def extract_code(text: str) -> str:
    fenced = re.findall(r"```(?:python)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        return fenced[-1].strip()
    return text.strip()


def close_code(text: str) -> str:
    """Drop a line the model left unfinished when the token limit cut it off."""
    source = extract_code(text).replace("WorkPlane", "Workplane")
    if _parses(source):
        return source
    lines = source.splitlines()
    while lines:
        lines.pop()
        candidate = "\n".join(lines).strip()
        if candidate and _parses(candidate):
            return candidate + "\n"
    return source


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
    except SyntaxError:
        return False
    return True


def run_program(code: str, out_dir: Path, timeout: float = 180) -> tuple[Path, Path]:
    folder = Path(out_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    step = folder / "part.step"
    stl = folder / "part.stl"
    program = folder / "program.py"
    runner = folder / "runner.py"
    source = close_code(code)
    program.write_text(source, encoding="utf-8")
    runner.write_text(RUNNER.format(step=str(step), geo=str(GEO_MODULE)), encoding="utf-8")
    try:
        completed = subprocess.run(
            [_cad_python(), str(runner)],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_child_env(),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CadFailure("program süre sınırını aştı", code) from exc
    if completed.returncode != 0 or not step.is_file():
        detail = (completed.stderr or completed.stdout or "program çalışmadı").strip()
        raise CadFailure(detail[-2000:], source)
    return step, stl
