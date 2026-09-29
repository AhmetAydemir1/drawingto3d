"""The generated corpus must not claim anything the sheet does not carry.

These are the independent tests for the two review findings that were about the *drawing* rather than
the evaluator or the runner:

* R08 — the sheet draws a hole's position from the part's edge, so the number printed next to that
  dimension has to be the edge distance (60×40 plate, hole at (15, 10) ⇒ 45 and 30 mm), not the
  coordinate about the part centre;
* R09 — a role in `printed_dimensions` that the sheet never prints is a label for something that does
  not exist on the drawing.

They also check that the corpus QA (`eval/lab_corpus.py`) is not vacuous: a doctored label file has to
fail it, otherwise the QA would be decoration.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d_lab import generator as gen  # noqa: E402


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


corpus = _load("lab_corpus_for_tests", "eval/lab_corpus.py")

PLATE = gen.PartSpec(id="t-plate", family="t_plate", template="plate_holes", params={
    "width": 60.0, "depth": 40.0, "thickness": 6.0,
    "holes": [dict(x=15.0, y=10.0, diameter=8.0, through=True)]})

BLOCK = gen.PartSpec(id="t-block", family="t_block", template="block_pocket", params={
    "width": 60.0, "depth": 40.0, "height": 20.0,
    "pocket": dict(x=0.0, y=0.0, width=40.0, depth=25.0, depth_mm=8.0),
    "holes": [dict(x=25.0, y=-16.0, diameter=8.0, through=True)]})


def _role(dims: list[dict], role: str) -> dict:
    found = [entry for entry in dims if entry["role"] == role]
    assert found, f"{role} basılı ölçülerde yok"
    return found[0]


def test_a_hole_position_is_printed_as_the_edge_distance() -> None:
    """R08: the dimension line runs from the left edge, so the number is the edge distance."""
    dims = gen.printed_dimensions(PLATE)

    x = _role(dims, "hole_x")
    y = _role(dims, "hole_y")
    assert (x["value_mm"], x["datum"]) == (45.0, "left_edge"), "soldan 45 mm olmalı"
    assert (y["value_mm"], y["datum"]) == (30.0, "bottom_edge"), "alttan 30 mm olmalı"
    assert (x["text"], y["text"]) == ("45", "30")
    # The centre coordinate is what the *feature* uses; it must not be what the drawing prints.
    assert x["value_mm"] != PLATE.params["holes"][0]["x"]


def test_the_edge_offsets_are_the_parameters_plus_half_the_extent() -> None:
    offsets = gen.edge_offsets(dict(PLATE.params))
    assert [(o["x_mm"], o["y_mm"]) for o in offsets] == [(45.0, 30.0)]
    assert [(o["datum_x"], o["datum_y"]) for o in offsets] == [("left_edge", "bottom_edge")]


def test_the_pocket_depth_is_printed_on_the_sheet() -> None:
    """R09: `pocket_height` was a label for a number the sheet never carried."""
    solid = gen.build_solid(BLOCK)
    _pdf, layout = gen.sheet(BLOCK, solid)

    printed = [entry for entry in layout["printed_text"] if entry["role"] == "pocket_height"]
    assert printed, "cep derinliği paftada basılmalı"
    assert printed[0]["text"] == "8"

    roles_on_sheet = {entry["role"] for entry in layout["printed_text"]}
    labels = gen.labels(BLOCK, volume_mm3=solid.volume)
    labels["printed_dimensions"] = gen.printed_dimensions(BLOCK)
    assert {entry["role"] for entry in labels["printed_dimensions"]} <= roles_on_sheet


def test_the_printed_number_equals_the_span_its_dimension_line_covers() -> None:
    """Value, endpoints and scale have to agree, not just look right in a picture."""
    solid = gen.build_solid(BLOCK)
    _pdf, layout = gen.sheet(BLOCK, solid)
    scale = float(layout["scale"])

    checked = 0
    for entry in layout["dimensions"]:
        if "span" not in entry:
            continue
        try:
            printed = float(entry["text"])
        except ValueError:
            continue  # a callout, not a number the line measures
        (x0, y0), (x1, y1) = entry["span"]
        measured = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / scale
        assert abs(measured - printed) <= 0.01, entry["role"]
        checked += 1
    assert checked >= 6, "her ölçü çizgisi uçlarıyla birlikte kaydedilmeli"


def test_the_generated_part_passes_the_corpus_qa(tmp_path: Path) -> None:
    record = gen.write_part(PLATE, tmp_path / PLATE.id)
    qa = corpus.qa_part(record, tmp_path / PLATE.id)
    assert qa["status"] == "pass", qa["findings"]
    assert {check["check"] for check in qa["checks"]} >= {"cad_bbox_matches_labels",
                                                         "printed_value_equals_drawn_span",
                                                         "printed_numbers_in_pdf_text_layer"}


def test_the_qa_is_not_vacuous_when_a_label_is_not_printed(tmp_path: Path) -> None:
    directory = tmp_path / PLATE.id
    record = gen.write_part(PLATE, directory)
    labels_path = directory / "labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    labels["printed_dimensions"].append({"text": "99", "role": "hayalet_ölçü", "value_mm": 99.0})
    labels_path.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")

    qa = corpus.qa_part(record, directory)
    assert qa["status"] == "fail"
    failed = {check["check"] for check in qa["checks"] if not check["ok"]}
    # Three independent paths notice: the label is not on the sheet, the role sets differ, and the
    # number itself is missing from the PDF's text layer.
    assert {"every_label_is_printed", "printed_text_matches_labels",
            "printed_numbers_in_pdf_text_layer"} <= failed


def test_the_qa_catches_a_centre_coordinate_printed_as_an_edge_distance(tmp_path: Path) -> None:
    """The R08 bug, put back by hand: the QA has to notice."""
    directory = tmp_path / PLATE.id
    record = gen.write_part(PLATE, directory)
    labels_path = directory / "labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    for entry in labels["printed_dimensions"]:
        if entry["role"] == "hole_x":
            entry["value_mm"] = 15.0
            entry["text"] = "15"
    labels_path.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")

    qa = corpus.qa_part(record, directory)
    assert qa["status"] == "fail"
    failed = {check["check"] for check in qa["checks"] if not check["ok"]}
    assert {"hole_x_is_the_edge_distance", "printed_text_matches_labels"} <= failed


@pytest.mark.parametrize("part", ["pilot-plate-01", "pilot-block-01", "pilot-step-01"])
def test_the_manifest_corpus_is_reproducible(tmp_path: Path, part: str) -> None:
    """Same parameters, same part.

    The STEP *file* is not byte-identical between exports (the kernel writes a header with a
    timestamp), so reproducibility is asserted where it means something: the same geometry (volume and
    bounding box), the same labels and the same printed dimensions as the manifest records.
    """
    spec = next(spec for spec in corpus.PARTS if spec.id == part)
    record = gen.write_part(spec, tmp_path / part)
    manifest_path = ROOT / "out/lab/data/v2/manifest.json"
    if not manifest_path.exists():
        pytest.skip("üretilmiş korpus manifesti yok (out/ sürüm kontrolünde değil)")
    committed = json.loads(manifest_path.read_text(encoding="utf-8"))
    wanted = next(row for row in committed["parts"] if row["part_id"] == part)

    assert record["volume_mm3"] == wanted["volume_mm3"]
    assert record["analytic_volume_mm3"] == wanted["analytic_volume_mm3"]
    assert record["features"] == wanted["features"]
    produced = json.loads((tmp_path / part / "labels.json").read_text(encoding="utf-8"))
    recorded = json.loads(Path(wanted["labels"]).read_text(encoding="utf-8"))
    assert produced == recorded
