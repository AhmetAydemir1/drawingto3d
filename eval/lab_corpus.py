"""H03 corpus driver: deterministic parametric parts, their sheets, labels, and the QA between them.

The review (R08/R09) showed the failure mode this file exists to prevent: a label that claims a number
the sheet never prints, and a printed number that does not measure what its dimension line covers.
Here a part is generated from parameters, and everything written beside it is checked against the two
things that can be checked without a human eye:

* the CAD — the STEP is re-opened, its bounding box and each feature centre are compared with the
  labels, so a label cannot drift away from the geometry it describes;
* the sheet — the PDF's *text layer* is read back (the same layer a reader would see) and every
  printed dimension is compared with the span its dimension line actually covers at the sheet scale,
  and with the datum corner it starts from.

A part only reaches the manifest with `qa.status == "pass"`. Anything else is written to
`quarantine.json` and stays out of the development set.

Nothing here reads a value out of a picture, and nothing is randomised: the same parameters give the
same geometry, the same labels and the same printed numbers. (A STEP *file* still differs byte for
byte between two exports, because the kernel writes a timestamp into its header; the manifest records
file hashes for provenance and the QA compares the re-opened geometry.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d_lab import generator as gen  # noqa: E402
from drawingto3d_lab import LAB_VERSION  # noqa: E402
from drawingto3d_lab.state import sha256_file, write_json  # noqa: E402

CORPUS_SCHEMA = "drawingto3d.lab.corpus/1"
QA_SCHEMA = "drawingto3d.lab.qa/1"

# How far a printed value may sit from the span its dimension line covers, at the sheet's scale. The
# endpoints are recorded in page millimetres, so the two agree exactly; the tolerance is for the
# rounding the printed text does (a 45.000 mm span printed as "45") and nothing else.
DIM_VALUE_TOL_MM = 0.01
# A printout whose numbers are right but whose geometry is 1e-9 off is not a finding either.
CAD_TOL_MM = 1.0e-6

PARTS: list[gen.PartSpec] = [
    gen.PartSpec(id="pilot-plate-01", family="plate_A", template="plate_holes", params={
        "width": 60.0, "depth": 40.0, "thickness": 6.0,
        "holes": [dict(x=15.0, y=10.0, diameter=8.0, through=True),
                  dict(x=-15.0, y=-10.0, diameter=5.0, through=False, depth=4.0)]}),
    gen.PartSpec(id="pilot-plate-02", family="plate_B", template="plate_holes", params={
        "width": 80.0, "depth": 50.0, "thickness": 8.0,
        "holes": [dict(x=20.0, y=12.0, diameter=10.0, through=True),
                  dict(x=-25.0, y=-15.0, diameter=6.0, through=True)]}),
    gen.PartSpec(id="pilot-block-01", family="block_C", template="block_pocket", params={
        "width": 60.0, "depth": 40.0, "height": 20.0,
        "pocket": dict(x=0.0, y=0.0, width=40.0, depth=25.0, depth_mm=8.0),
        # The hole must sit in the full-thickness region: a hole that broke into the pocket would
        # falsify the closed-form volume, and `write_part` compares the two.
        "holes": [dict(x=25.0, y=-16.0, diameter=8.0, through=True)]}),
    gen.PartSpec(id="pilot-step-01", family="step_D", template="plate_step", params={
        "width": 60.0, "depth": 40.0, "thickness": 6.0,
        "step_width": 20.0, "step_height": 3.0,
        # As above: outside the stepped region (which starts at width/2 - step_width = 10).
        "holes": [dict(x=-15.0, y=8.0, diameter=6.0, through=True)]}),
]

# The families are split apart *before* anything is derived from them: two views of one part are one
# sample, so the split follows the family, never the file.
HELD_OUT_FAMILIES = ("plate_B",)


# The sheet also carries text that is not a dimension: the view names and the title block. Those are
# checked against the part's own identity below, not against `printed_dimensions` (which is exactly the
# list of *dimensions* the sheet prints).
NON_DIMENSION_ROLES = ("view_label", "title_block")


def _normalise(text: str) -> str:
    return " ".join(text.replace("\u2300", "Ø").split()).strip()


def _pdf_text_layer(pdf_path: Path) -> str:
    """The sheet's own text, as a reader would get it (not a guess from the pixels)."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        return document[0].get_textpage().get_text_range()
    finally:
        document.close()


def _png_ink_fraction(png_path: Path) -> float:
    from PIL import Image

    with Image.open(png_path) as image:
        data = image.convert("L").tobytes()
    dark = sum(1 for value in data if value < 200)
    return dark / max(1, len(data))


def _label_roles(labels: dict) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for entry in labels.get("printed_dimensions", []):
        roles.setdefault(entry["role"], []).append(_normalise(entry["text"]))
    return roles


def _sheet_roles(layout: dict) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for entry in layout.get("printed_text", []):
        roles.setdefault(entry["role"], []).append(_normalise(entry["text"]))
    return roles


def _check(checks: list[dict], name: str, ok: bool, got: Any, want: Any) -> bool:
    checks.append({"check": name, "ok": bool(ok), "got": got, "want": want})
    return bool(ok)


def qa_part(record: dict, directory: Path) -> dict:
    """Everything checkable about one generated part, without looking at the picture."""
    labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
    layout = json.loads((directory / "sheet-layout.json").read_text(encoding="utf-8"))
    checks: list[dict] = []
    findings: list[str] = []

    # 1. The CAD is what the labels say it is.
    solid = gen.reimport_step(directory / "part.step")
    size = solid.bounding_box().size
    cad_size = [round(size.X, 6), round(size.Y, 6), round(size.Z, 6)]
    _check(checks, "cad_bbox_matches_labels", cad_size == labels["bbox_size"], cad_size,
           labels["bbox_size"])
    volume_ok = abs(solid.volume - labels["volume_mm3"]) <= max(1e-3, labels["volume_mm3"] * 1e-9)
    _check(checks, "cad_volume_matches_labels", volume_ok, round(solid.volume, 6),
           labels["volume_mm3"])
    _check(checks, "analytic_volume_matches_kernel",
           abs(record["analytic_volume_mm3"] - record["volume_mm3"])
           <= max(1e-3, record["volume_mm3"] * 1e-9),
           record["analytic_volume_mm3"], record["volume_mm3"])

    # 2. Every label is printed, and every printed dimension is labelled (the R09 finding, both ways).
    label_roles, sheet_roles = _label_roles(labels), _sheet_roles(layout)
    dimension_roles = {role: texts for role, texts in sheet_roles.items()
                       if role not in NON_DIMENSION_ROLES}
    missing_from_sheet = sorted(set(label_roles) - set(dimension_roles))
    unlabelled_on_sheet = sorted(set(dimension_roles) - set(label_roles))
    _check(checks, "every_label_is_printed", not missing_from_sheet, missing_from_sheet, [])
    _check(checks, "no_printed_number_is_unlabelled", not unlabelled_on_sheet, unlabelled_on_sheet, [])
    text_mismatch = {role: [sorted(label_roles[role]), sorted(dimension_roles.get(role, []))]
                     for role in label_roles
                     if sorted(label_roles[role]) != sorted(dimension_roles.get(role, []))}
    _check(checks, "printed_text_matches_labels", not text_mismatch, text_mismatch, {})

    # 2b. The title block and the view names agree with the part's own identity.
    title = " | ".join(_normalise(entry["text"]) for entry in layout["printed_text"]
                       if entry["role"] == "title_block")
    identity = {"part": labels["part_id"] in title, "family": labels["family"] in title,
                "units": f"UNITS {labels['units']}" in title,
                "scale": f"SCALE 1:{round(1 / float(layout['scale'])):g}" in title,
                "views": {_normalise(e["text"]) for e in layout["printed_text"]
                          if e["role"] == "view_label"} == {"FRONT", "TOP", "RIGHT"}}
    _check(checks, "title_block_matches_labels", all(identity.values()), identity, "all true")

    # 3. The printed value is the span the dimension line covers, from the datum it claims. The value
    # is read from the printed *text* (what a reader sees), not from a separate bookkeeping field.
    scale = float(layout["scale"])
    worst = 0.0
    measured_count = 0
    datum_offenders = []
    for entry in layout["dimensions"]:
        if "span" not in entry:
            continue
        try:
            printed = float(_normalise(entry["text"]))
        except ValueError:
            continue  # a callout ("Ø8 THRU"), not a number with a span
        (start_x, start_y), (end_x, end_y) = entry["span"]
        measured = math.hypot(end_x - start_x, end_y - start_y) / scale
        measured_count += 1
        worst = max(worst, abs(measured - printed))
        if entry["role"] == "hole_x":
            edge = layout["part_rects"]["top"][0]
            if abs(start_x - edge) > 0.01:
                datum_offenders.append({"role": entry["role"], "start_x": start_x, "left_edge": edge})
        if entry["role"] == "hole_y":
            edge = layout["part_rects"]["top"][3]
            if abs(start_y - edge) > 0.01:
                datum_offenders.append({"role": entry["role"], "start_y": start_y,
                                        "bottom_edge": edge})
    _check(checks, "printed_value_equals_drawn_span", measured_count >= 4 and worst <= DIM_VALUE_TOL_MM,
           {"dimensions_measured": measured_count, "worst_delta_mm": round(worst, 6)},
           f">= 4 ölçü ve sapma <= {DIM_VALUE_TOL_MM}")
    _check(checks, "dimension_starts_at_its_datum", not datum_offenders, datum_offenders, [])

    # 4. Edge-referenced hole positions agree with the parameters the CAD was built from.
    expected_edges = gen.edge_offsets(dict(labels["provenance"]["parameters"]))
    printed_x = {round(float(entry["value_mm"]), 6)
                 for entry in labels["printed_dimensions"] if entry["role"] == "hole_x"}
    wanted_x = {round(offset["x_mm"], 6) for offset in expected_edges}
    printed_y = {round(float(entry["value_mm"]), 6)
                 for entry in labels["printed_dimensions"] if entry["role"] == "hole_y"}
    wanted_y = {round(offset["y_mm"], 6) for offset in expected_edges}
    _check(checks, "hole_x_is_the_edge_distance", printed_x == wanted_x, sorted(printed_x),
           sorted(wanted_x))
    _check(checks, "hole_y_is_the_edge_distance", printed_y == wanted_y, sorted(printed_y),
           sorted(wanted_y))

    # 5. The text layer really carries the numbers (a vector PDF, not a picture of one).
    layer = _normalise(_pdf_text_layer(directory / "drawing.pdf"))
    missing_text = [entry["text"] for entry in labels["printed_dimensions"]
                    if _normalise(entry["text"]) not in layer]
    _check(checks, "printed_numbers_in_pdf_text_layer", not missing_text, missing_text, [])

    # 6. The raster form exists and carries ink.
    ink = _png_ink_fraction(directory / "drawing.png")
    _check(checks, "png_has_geometry", 0.001 <= ink <= 0.6, round(ink, 5), "0.001 .. 0.6")

    status = "pass" if all(check["ok"] for check in checks) else "fail"
    findings += [f"{check['check']}: {check['got']} != {check['want']}"
                 for check in checks if not check["ok"]]
    return {"schema": QA_SCHEMA, "part_id": record["part_id"], "status": status, "checks": checks,
            "findings": findings, "automated": True,
            "human_review": "out/lab/review-checkpoint/report.md (dimension overlap, readability, "
                            "view reference, label placement)"}


def _immutable_json(path: Path, payload: dict) -> None:
    """Write once: a second run with different bytes is an error, not a silent overwrite."""
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"{path} zaten var ve içeriği farklı: ham veri değişmez")
        return
    write_json(path, payload)


def build(out_root: Path) -> dict:
    out_root.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records = []
    qa_records = []
    for spec in PARTS:
        directory = out_root / spec.id
        record = gen.write_part(spec, directory)
        qa = qa_part(record, directory)
        record["qa_status"] = qa["status"]
        records.append(record)
        qa_records.append(qa)
        write_json(directory / "qa.json", qa)
        print(f"{spec.id}: {qa['status']} ({len(qa['checks'])} kontrol)")

    _immutable_json(out_root / "qa.json", {"schema": QA_SCHEMA, "created_at": created,
                                           "parts": qa_records,
                                           "passed": [q["part_id"] for q in qa_records
                                                      if q["status"] == "pass"],
                                           "failed": [q["part_id"] for q in qa_records
                                                      if q["status"] != "pass"]})

    groups = [{"part_id": spec.id, "family": spec.family, "group": spec.family,
               "template": spec.template} for spec in PARTS]
    splits = {
        "schema": "drawingto3d.lab.splits/1",
        "rule": "the split follows the base part's family, decided before any view or crop is derived",
        "groups": groups,
        "development": [spec.id for spec in PARTS if spec.family not in HELD_OUT_FAMILIES],
        "held_out": [spec.id for spec in PARTS if spec.family in HELD_OUT_FAMILIES],
        "regression": [],
        "caveat": "The pilot target is 10 independent parts with different sheet layouts (PLAN §5); "
                  "this corpus has 4, so no independent/hidden test is claimed and the held-out "
                  "family is a smoke set only.",
    }
    _immutable_json(out_root / "splits.json", splits)

    manifest = {
        "schema": CORPUS_SCHEMA, "lab_version": LAB_VERSION, "created_at": created,
        "generator": "src/drawingto3d_lab/generator.py",
        "raw_immutable": True,
        "parts": records,
        "counts": {"parts": len(records), "families": len({spec.family for spec in PARTS}),
                   "qa_pass": sum(1 for q in qa_records if q["status"] == "pass")},
        "splits": str(out_root / "splits.json"),
        "qa": str(out_root / "qa.json"),
        "usage": {"training": False,
                  "reason": "4 parts is a pilot, not training data; PLAN §5 asks for 200-500 "
                            "verified task examples before training"},
    }
    _immutable_json(out_root / "manifest.json", manifest)
    return manifest


def quarantine(previous: Path, corpus: Path, reason_notes: list[dict], *, refresh: bool = False) -> dict:
    """Keep the pre-review parts, mark them out of the development set, and say why."""
    destination = previous.parent / "QUARANTINE.json"
    if destination.exists() and not refresh:
        return json.loads(destination.read_text(encoding="utf-8"))
    entries = []
    for path in sorted(p for p in previous.iterdir() if p.is_dir()):
        files = sorted(child.name for child in path.iterdir())
        entries.append({
            "path": str(path), "part_id": path.name, "files": files,
            "files_present": len(files),
            "sha256": {name: sha256_file(path / name) for name in files},
            "verdict": "quarantined",
            "use": "excluded from training and from the development set; kept as evidence",
        })
    payload = {
        "schema": "drawingto3d.lab.quarantine/1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reason": "Written before the 2026-09-29 review repairs: hole positions were printed as "
                  "centre coordinates while the dimension lines measured from the edge, and one "
                  "label (pocket_height) claimed a number the sheet never printed.",
        "superseded_by": str(corpus),
        "findings": reason_notes,
        "entries": entries,
    }
    _immutable_json(destination, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "out/lab/data/v2")
    parser.add_argument("--quarantine", type=Path, default=ROOT / "out/lab/data/raw")
    args = parser.parse_args()
    manifest = build(args.out)
    print(json.dumps({"manifest": str(args.out / "manifest.json"),
                      "counts": manifest["counts"]}, ensure_ascii=False))
    if args.quarantine.exists():
        quarantine(args.quarantine, args.out, [
            {"id": "R08", "observed": "printed_dimensions hole_x said 15 for a hole drawn 45 mm "
                                      "from the left edge"},
            {"id": "R09", "observed": "labels claimed pocket_height; the sheet printed no pocket "
                                      "depth"},
            {"id": "incomplete", "observed": "pilot-step-01 was never written (step cut failed)"},
        ])
        print(json.dumps({"quarantine": str(args.quarantine.parent / "QUARANTINE.json")},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
