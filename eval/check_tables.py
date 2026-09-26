"""Check the README's tables against the runs in `out/frontend/`: the docs may not drift from the files.

The eval tables in `eval/README.md` are the measurement this project is steered by, and they are written by
hand from runs that live in `out/` (which is git-ignored). A row that has drifted is worse than no row, so
this reads every table back and prints the difference. Which table a row belongs to is taken from the
header above it (`vaka | kaynak | ...`, `vaka | kapsam | at the start of this work`,
`vaka | tesseract (floor) | qwen3-vl:8b-instruct (ceiling)`) rather than guessed from the shape of the row: two of
the three tables have three columns.

Usage: `PYTHONPATH=src .venv/bin/python eval/check_tables.py` (exit code 1 when a row has drifted).
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "eval" / "README.md"
OUT = ROOT / "out" / "frontend"

FULL_ROW = re.compile(
    r"\|\s*([a-z0-9\-]+)\s*\|\s*(raster|vektör)\s*\|\s*(\d+/\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+|-)\s*\|\s*(\d+)\s*\|"
)
THREE_CELL = re.compile(r"\|\s*([a-z0-9\-]+)\s*\|\s*(\d+/\d+)\s*\|\s*([^|]+?)\s*\|")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]

READ_AS = {"raster": "-raster", "vektör": ""}
HEADERS = {
    "kaynak": "full",
    "at the start of this work": "raster cover",
    "qwen3-vl:8b-instruct (ceiling)": "ceiling",
}


def _run(case: str, suffix: str) -> dict | None:
    path = OUT / f"{case}{suffix}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _coverage(row: dict) -> str:
    return f"{len(row['covers'])}/{len(row['printed'])}"


def main() -> int:
    drifted = 0
    checked = 0
    table = ""
    for line in README.read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            header = _cells(line)
            if "vaka" in header:
                table = next((value for key, value in HEADERS.items() if key in line), "")
                continue
            if all(cell.startswith("---") for cell in header):
                continue
        else:
            continue

        if table == "full":
            match = FULL_ROW.match(line)
            if not match:
                continue
            case, source, coverage, noise, px, suspect = match.groups()
            row = _run(case, READ_AS[source])
            checked += 1
            if row is None:
                print(f"KAYIT YOK  {case}{READ_AS[source]}: tabloda var, out/frontend'te yok")
                drifted += 1
                continue
            fit = row.get("calibration")
            real = (_coverage(row), str(len(row["noise"])), f"{float(fit['px_per_mm']):.3f}" if fit else "-",
                    str(len(row["suspect"])))
            if (coverage, noise, px, suspect) != real:
                print(f"KAYDI  {case:22} {source:7} README {coverage:>7} {noise:>3} {px:>7} {suspect:>3}"
                      f"  ->  koşu {real[0]:>7} {real[1]:>3} {real[2]:>7} {real[3]:>3}")
                drifted += 1
        elif table == "raster cover":
            match = THREE_CELL.match(line)
            if not match:
                continue
            case, coverage, _start = match.groups()
            row = _run(case, "-raster")
            checked += 1
            if row is None or _coverage(row) == coverage:
                continue
            print(f"KAYDI  {case:22} raster   README {coverage:>7}  ->  koşu {_coverage(row):>7}")
            drifted += 1
        elif table == "ceiling":
            match = THREE_CELL.match(line)
            if not match:
                continue
            case, floor, ceiling = match.groups()
            base, top = _run(case, "-raster"), _run(case, "-raster-model")
            checked += 1
            if base is not None and _coverage(base) != floor:
                print(f"KAYDI  {case:22} taban    README {floor:>7}  ->  koşu {_coverage(base):>7}")
                drifted += 1
            printed_top = ceiling.split()[0]
            if top is not None and _coverage(top) != printed_top:
                print(f"KAYDI  {case:22} tavan    README {printed_top:>7}  ->  koşu {_coverage(top):>7}"
                      f"  (tavan ayrı bir koşudur; tabloda yaşlı koşu notu olabilir)")
                drifted += 1

    print(f"\n{checked} satır okundu, {drifted} satır koşuyla tutmuyor")
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
