"""Dimension records to STEP. A local code model writes a short geo.* program; this machine runs it.

First turn: the sheet is read into DimensionRecords (one closed question per number) and returned
for the user to correct. Second turn: the records come back and the code model builds the solid.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from drawingto3d.cadrun import GEO_MODULE, CadFailure, extract_code, run_program
from drawingto3d.ingest import load_page
from drawingto3d.llama import LlamaCoder, OllamaCoder, OllamaVision, retry_prompt
from drawingto3d.roles import read_records
from drawingto3d.schema import ROLES, Audit, ConvertResult, DimensionRecord, Page

ATTEMPTS = 3
MAX_LINES = 30
SMALL_NUMBERS = frozenset(float(n) for n in range(0, 11))
ANGLES = frozenset((45.0, 90.0, 180.0, 270.0, 360.0))

AfterBuild = Callable[[Path, Page], str | None]

CODE_ASK = (
    "Write one Python program that builds this part with the geo helpers below. "
    "The names cq and geo are already defined; do not import anything. "
    "Use only geo.* calls. At most 25 lines, one statement per line, no functions or loops. "
    "Assign the finished part to solid. "
    "Every millimetre must come from the dimension records; you may halve a value or add two values "
    "for positions. Do not invent numbers. Return only Python code.\n\n"
    "geo helpers (all return one solid):\n{api}\n\n"
    "Rules:\n"
    "- `part` in holes, place, cut, chamfer_edges and fillet_edges is a variable holding a solid "
    "returned by an earlier geo call (for example a = geo.plate(...); a = geo.holes(a, ...)). "
    "Never pass a string or a number there. holes returns the drilled part: reassign it to the same "
    "variable and do not fuse it with the undrilled one.\n"
    "{shape}"
    "- No comments. Write numbers directly in the calls.\n"
    "- Order of work: make the main body first; make each further part with geo.attach(new_part, base, 'start' or 'end'), "
    "which returns new_part moved onto that face of base (base stays where it is); drill plates with holes; "
    "finally solid = geo.fuse(every named part). Every part you created must appear in that fuse call. "
    "Do not use geo.place for stacking.\n"
    "- Every record names a feature that must exist in the solid: a hole_diameter needs holes, "
    "a bend_radius needs ring_revolve, a thickness needs a plate or a wall of that thickness, "
    "a corner_radius needs a plate corner.\n"
    "- Role meanings: thickness = the thin depth of a plate or wall; edge = a side length of the body "
    "(a plate side, a tube length, an arm); outer_diameter / inner_diameter = the round body; "
    "bend_radius = ring_revolve bend_radius; hole_diameter with count = holes at geo.rect_points(hole_spacing); "
    "corner_radius = plate corner_radius; fillet = fillet_edges radius; chamfer = chamfer_edges size.\n"
    "- Write every millimetre as a literal number. Role names such as edge or thickness are not variables.\n"
    "- Do not call fillet_edges or chamfer_edges; a wrong selector fails the program. Leave edges sharp.\n\n"
    "Dimension records (millimetres):\n{records}\n"
)

TUBE_ROLES = frozenset({"outer_diameter", "inner_diameter", "bend_radius"})
PLATE_ROLES = frozenset({"thickness", "corner_radius"})

TUBE_SHAPE = (
    "The records name a round part: an outer or inner diameter. A bent tube is one ring_revolve; straight "
    "lengths are ring_extrude attached to its ends; plates are attached to the tube ends and drilled with holes.\n"
)
PLATE_SHAPE = (
    "The records name a plate: a thin depth beside side lengths, with holes drilled through it. Build it with "
    "geo.plate(width, height, thickness) - the two largest edge values are width and height, the thin depth is "
    "the thickness - then drill it: a = geo.holes(a, positions=geo.rect_points(dx, dy), diameter=d). A "
    "hole_diameter beside a hole_spacing is that pattern; a hole_diameter alone is one hole through the middle.\n"
)
UNKNOWN_SHAPE = (
    "The records name no shape: no diameter, no thickness, no bend. Build the simplest body the records "
    "describe, and add no feature they do not name.\n"
)


def shape_note(records: Sequence[DimensionRecord]) -> str:
    """Which shape the records name, said only as far as they prove it.

    The prompt used to hand the model a tube recipe before it had seen anything, and a plate sheet came out as
    a bent tube with a plate glued to its end - measured twice, on a drawing where all seven numbers are
    printed, so nothing about the reading can be blamed. What the records carry decides: a diameter means a
    round part, a thin depth beside side lengths means a plate, and when neither is there the prompt says so
    rather than picking one (a flange whose `Ø` was never read as a diameter lands here, which is where the
    failure belongs: in its records).
    """
    roles = {record.role for record in records}
    if roles & TUBE_ROLES:
        return TUBE_SHAPE
    if roles & PLATE_ROLES and "edge" in roles:
        return PLATE_SHAPE
    return UNKNOWN_SHAPE


def reason_drawing(
    path: str | Path,
    out_dir: str | Path,
    coder: LlamaCoder | OllamaCoder | None = None,
    progress=None,
    records: Sequence[DimensionRecord] | None = None,
    reader=None,
    after_build: AfterBuild | None = None,
    auto_build: bool = False,
) -> ConvertResult:
    def tell(title: str, detail: str) -> None:
        if progress is not None:
            progress(title, detail)

    page = load_page(path)
    if records is None:
        vision = reader or OllamaVision()
        tell("Ölçüler okunuyor", "Her ölçü için tek soru soruluyor.")
        try:
            records = read_records(page, vision, progress)
        finally:
            _release(vision)
        if not auto_build:
            tell("Ölçüler hazır", "Yanlış rolü tabloda düzelt, sonra katıyı kur.")
            return ConvertResult(audit=Audit(accepted=False), page=page, records=list(records))
    records = list(records)
    if not records:
        raise CadFailure("kayıt yok; ölçü okunmadı", "")

    model = coder or _default_coder()
    folder = Path(out_dir)
    largest = max(record.value for record in records)
    tell("Model yazıyor", "Ölçü kaydı yerel kod modeline gidiyor.")
    code = extract_code(_ask(model, page, build_prompt(records)))
    step = stl = None
    for attempt in range(ATTEMPTS):
        tell("Kod çalışıyor", "CadQuery yerelde çalışıyor." if attempt == 0 else "Düzeltilen program çalışıyor.")
        try:
            wordy = _program_problem(code, records) or _number_problem(code, records)
            if wordy:
                raise CadFailure(wordy, code)
            step, stl = run_program(code, folder)
            problem = _scale_problem(folder, largest)
            if problem is None and after_build is not None:
                problem = after_build(Path(step), page)
            if problem:
                raise CadFailure(problem, (folder / "program.py").read_text(encoding="utf-8"))
            break
        except CadFailure as exc:
            if attempt == ATTEMPTS - 1:
                dropped = _drop_edge_finish(exc.code)
                if dropped != exc.code:
                    tell("Pah atlandı", "Kavis ve pah satırları düşürüldü, program yeniden çalışıyor.")
                    wordy = _program_problem(dropped, records) or _number_problem(dropped, records)
                    if not wordy:
                        step, stl = run_program(dropped, folder)
                        problem = _scale_problem(folder, largest)
                        if problem is None and after_build is not None:
                            problem = after_build(Path(step), page)
                        if not problem:
                            break
                raise
            tell("Yeniden deniyor", "Katı ölçülerle tutmadı, hata modele geri gidiyor.")
            code = extract_code(_ask(model, page, build_prompt(records) + "\n" + retry_prompt(exc.code, exc.stderr)))
    tell("STEP hazır", "Dosyayı indirebilirsin.")
    return ConvertResult(
        audit=Audit(accepted=True),
        step_path=str(step),
        stl_path=str(stl) if stl is not None and Path(stl).is_file() else None,
        page=page,
        records=records,
    )


def build_prompt(records: Sequence[DimensionRecord]) -> str:
    return CODE_ASK.format(api=geo_summary(), shape=shape_note(records), records=records_text(records))


def records_text(records: Sequence[DimensionRecord]) -> str:
    lines = []
    for record in records:
        count = f", count {record.count}" if record.count > 1 else ""
        lines.append(f"- {record.value:g} mm: {record.role}{count}")
    return "\n".join(lines)


def geo_summary(source: Path = GEO_MODULE) -> str:
    """Signature lines with the first docstring sentence, read from geo.py so the two never drift."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    lines = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        doc = (ast.get_docstring(node) or "").strip().split("\n")[0]
        lines.append(f"geo.{node.name}({_signature(node)})  # {doc}")
    return "\n".join(lines)


def _signature(node: ast.FunctionDef) -> str:
    args = node.args
    positional = args.posonlyargs + args.args
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    parts = []
    for arg, default in zip(positional, defaults, strict=True):
        parts.append(arg.arg if default is None else f"{arg.arg}={ast.unparse(default)}")
    if args.vararg is not None:
        parts.append("*" + args.vararg.arg)
    return ", ".join(parts)


def _ask(model, page: Page, prompt: str) -> str:
    if isinstance(model, LlamaCoder):
        return model.complete(page.image_png, prompt)
    return model.complete(prompt)


def _release(reader) -> None:
    release = getattr(reader, "release", None)
    if callable(release):
        try:
            release()
        except Exception:  # noqa: BLE001 - unloading is best effort
            return


def _default_coder() -> OllamaCoder | LlamaCoder:
    try:
        return OllamaCoder()
    except Exception:
        return LlamaCoder()


def _program_problem(code: str, records: Sequence[DimensionRecord] = ()) -> str | None:
    body = [line for line in code.splitlines() if line.strip() and not line.strip().startswith("#")]
    if len(body) > MAX_LINES:
        return f"The program is longer than {MAX_LINES} lines. Write one short program and do not repeat an operation."
    if re.search(r"^\s*(import|from)\s+(?!cadquery\b)", code, flags=re.MULTILINE):
        return "Do not import anything. cq and geo are already defined."
    if re.search(r"\b(?:fillet_edges|chamfer_edges)\s*\(", code):
        return "Do not call fillet_edges or chamfer_edges; a wrong selector fails the program. Leave edges sharp."
    return _role_as_variable(code, records)


def _drop_edge_finish(code: str) -> str:
    """Last resort: drop fillet/chamfer lines the model kept adding."""
    kept = [line for line in code.splitlines() if not re.search(r"\b(?:fillet_edges|chamfer_edges)\s*\(", line)]
    return "\n".join(kept).strip() + ("\n" if kept else "")


def _role_as_variable(code: str, records: Sequence[DimensionRecord]) -> str | None:
    """`geo.plate(edge, ...)` is a guess dressed as a name; say which number belongs there."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    assigned = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
    used = [
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in ROLES and node.id not in assigned
    ]
    if not used:
        return None
    hints = []
    for role in dict.fromkeys(used):
        values = ", ".join(f"{record.value:g}" for record in records if record.role == role) or "no value"
        hints.append(f"{role} -> {values}")
    return (
        f"{', '.join(dict.fromkeys(used))} are role names, not variables. "
        f"Write the millimetre number instead: {'; '.join(hints)}."
    )


def allowed_numbers(records: Sequence[DimensionRecord]) -> set[float]:
    """Printed values, their halves, and sums or differences of two of those."""
    base = {0.0}
    for record in records:
        base.add(float(record.value))
        base.add(float(record.value) / 2)
        base.add(float(record.count))
    allowed = set(base) | SMALL_NUMBERS | ANGLES
    items = sorted(base)
    for a in items:
        for b in items:
            allowed.add(a + b)
            allowed.add(abs(a - b))
    return allowed


def _number_problem(code: str, records: Sequence[DimensionRecord]) -> str | None:
    """A millimetre the drawing does not print is a guess; send the program back."""
    allowed = allowed_numbers(records)
    stripped = "\n".join(line.split("#", 1)[0] for line in code.splitlines())
    stripped = re.sub(r"(['\"]).*?\1", "''", stripped)
    stray = []
    for match in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", stripped):
        value = float(match.group(0))
        if not any(abs(value - item) < 1e-6 for item in allowed):
            stray.append(match.group(0))
    if not stray:
        return None
    printed = ", ".join(f"{record.value:g}" for record in records)
    unique = ", ".join(dict.fromkeys(stray))
    return (
        f"The numbers {unique} are not printed on the drawing. "
        f"Use only these millimetres: {printed} (or half of one, or the sum of two)."
    )


def _scale_problem(folder: Path, largest: float | None) -> str | None:
    """A solid far smaller or larger than the printed dimensions is not that part."""
    if largest is None:
        return None
    measure = folder / "measure.txt"
    if not measure.is_file():
        return None
    try:
        sizes = [float(item) for item in measure.read_text(encoding="utf-8").split()]
    except ValueError:
        return None
    if len(sizes) != 3:
        return None
    span = max(sizes)
    if span < largest * 0.4:
        return (
            f"The solid is {span:.1f} mm across, but the drawing prints dimensions up to {largest:.0f} mm. "
            "Rebuild the part in those millimetres."
        )
    if span > largest * 8:
        return (
            f"The solid is {span:.1f} mm across, more than eight times the largest printed dimension {largest:.0f} mm. "
            "Rebuild the part in the printed millimetres."
        )
    return None
