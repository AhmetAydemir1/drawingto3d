"""Command line: read a sheet into dimension records, then build a STEP from those records.

    drawingto3d read  sheet.pdf out/                   read every printed dimension and its role
    drawingto3d build sheet.pdf out/records.json out/  build the solid from the (corrected) records

Nothing leaves the machine: the reader and the code model are local only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from drawingto3d.reason import reason_drawing
from drawingto3d.schema import DimensionRecord


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

    args = parser.parse_args()
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


if __name__ == "__main__":
    main()
