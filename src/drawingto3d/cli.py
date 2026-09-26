"""Command line: read a sheet into dimension records, then build a STEP from those records.

    drawingto3d read  sheet.pdf out/                   read every printed dimension and its role
    drawingto3d build sheet.pdf out/records.json out/  build the solid from the (corrected) records

Nothing leaves the machine: the reader and the code model are local only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from drawingto3d.reason import reason_drawing
from drawingto3d.schema import DimensionRecord
from drawingto3d.ingest import load_page
from drawingto3d.plate import propose_plate
from drawingto3d.plan import PlatePlan, build_plan
from drawingto3d.cadrun import CadFailure
from drawingto3d.general import GeneralPlan, build_general
from drawingto3d.observe import observe
from drawingto3d.bind import bind_page


def main() -> None:
    parser = argparse.ArgumentParser(prog="drawingto3d", description="PDF veya PNG teknik çizimden STEP")
    commands = parser.add_subparsers(dest="command", required=True)

    read = commands.add_parser("read", help="paftayı oku, ölçü kayıtlarını JSON olarak yaz")
    read.add_argument("drawing")
    read.add_argument("out_dir")

    build = commands.add_parser("build", help="düzeltilmiş kayıtlardan katıyı kur")
    build.add_argument("drawing")
    build.add_argument("records")
    build.add_argument("out_dir")

    plan = commands.add_parser("plan", help="desteklenen vektör paftadan model çağırmadan CAD planı çıkar")
    plan.add_argument("drawing")
    plan.add_argument("out_dir")
    replay = commands.add_parser("build-plan", help="incelenebilir CAD planından deterministik taslak STEP üret")
    replay.add_argument("drawing")
    replay.add_argument("plan")
    replay.add_argument("out_dir")
    general = commands.add_parser("build-general", help="sürümlü genel plandan deterministik taslak STEP üret")
    general.add_argument("plan")
    general.add_argument("out_dir")
    general.add_argument("--drawing", default=None,
                         help="plan.source.kind == 'drawing' ise kaynak çizim yolu")
    observe_command = commands.add_parser("observe", help="çizimden aile-bağımsız gözlem kayıtları çıkar (vektör PDF)")
    observe_command.add_argument("drawing")
    observe_command.add_argument("out_dir")
    bind_command = commands.add_parser("bind", help="basılı sayıları oklarının dokunduğu geometriye bağla (vektör PDF)")
    bind_command.add_argument("drawing")
    bind_command.add_argument("out_dir")

    args = parser.parse_args()
    if args.command == "plan":
        proposal = propose_plate(load_page(args.drawing))
        if proposal is None:
            parser.exit(2, "Bu çizim desteklenen vektör plaka ailesiyle güvenilir biçimde eşleşmedi.\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "plan.json"
        path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"plan": str(path), "assumptions": proposal.assumptions}, ensure_ascii=False, indent=2))
        return
    if args.command == "build-plan":
        proposal = PlatePlan.model_validate_json(Path(args.plan).read_text(encoding="utf-8"))
        step, stl = build_plan(proposal, args.drawing, args.out_dir)
        print(json.dumps({"step": str(step), "stl": str(stl), "draft": True,
                          "audit": str(Path(args.out_dir) / "plan-audit.json")}, indent=2))
        return
    if args.command == "build-general":
        try:
            plan = GeneralPlan.model_validate_json(Path(args.plan).read_text(encoding="utf-8"))
            step, stl = build_general(plan, args.drawing, args.out_dir)
        except CadFailure as exc:
            parser.exit(2, f"Plan uygulanamadı: {exc}\n")
        except ValueError as exc:
            parser.exit(2, f"Geçersiz plan: {_readable(exc)}\n")
        print(json.dumps({"step": str(step), "stl": str(stl), "status": "draft",
                          "audit": str(Path(args.out_dir) / "plan-audit.json")}, indent=2))
        return
    if args.command == "observe":
        try:
            observations = observe(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Gözlem çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "observations.json"
        path.write_text(observations.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"observations": str(path), "paths": len(observations.paths),
                          "primitives": len(observations.primitives), "texts": len(observations.texts)},
                         indent=2))
        return
    if args.command == "bind":
        try:
            bindings = bind_page(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Bağlama çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "bindings.json"
        path.write_text(bindings.model_dump_json(indent=2), encoding="utf-8")
        counts: dict[str, int] = {}
        for span in bindings.spans:
            counts[span.status] = counts.get(span.status, 0) + 1
        print(json.dumps({"bindings": str(path), "spans": len(bindings.spans),
                          "status": counts, "sheet_px_per_mm": bindings.sheet_px_per_mm},
                         ensure_ascii=False, indent=2))
        return
    if args.command == "read":
        _read(args)
        return
    _build(args)


def _read(args) -> None:
    result = reason_drawing(args.drawing, args.out_dir, progress=_tell)
    folder = Path(args.out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "records.json"
    payload = [record.model_dump(mode="json") for record in result.records]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(payload), "file": str(path)}, ensure_ascii=False, indent=2))


def _build(args) -> None:
    raw = json.loads(Path(args.records).read_text(encoding="utf-8"))
    records = [DimensionRecord.model_validate(item) for item in raw]
    result = reason_drawing(args.drawing, args.out_dir, records=records, progress=_tell)
    print(
        json.dumps(
            {"step": result.step_path, "stl": result.stl_path, "accepted": result.audit.accepted},
            ensure_ascii=False,
            indent=2,
        )
    )


def _tell(title: str, detail: str) -> None:
    print(f"{title}: {detail}", flush=True)


def _readable(exc: ValueError) -> str:
    """Validation errors read as one line: location and message, no pydantic internals."""
    if isinstance(exc, ValidationError):
        parts = []
        for error in exc.errors(include_url=False, include_input=False):
            where = ".".join(str(item) for item in error["loc"])
            message = str(error["msg"]).removeprefix("Value error, ")
            parts.append(f"{where}: {message}" if where else message)
        if parts:
            return "; ".join(parts)
    return str(exc)


if __name__ == "__main__":
    main()
