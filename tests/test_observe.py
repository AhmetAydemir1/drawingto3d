"""The observation layer: every sheet in one record shape, no part family named.

The plate's records are checked against its own drawing (100 mm hole spacing, Ø50 pocket — the
values a human reads off the sheet); the plastic sheet's numbers are checked only for presence,
because this layer does not decide what they mean.
"""

import json
from pathlib import Path

import pytest

from drawingto3d.ingest import load_page
from drawingto3d.observe import Unsupported, observe, vector_groups
from drawingto3d.plan import source_hash

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/6/plastic enclosue.pdf")
PX_PER_MM = 200 / 25.4


@pytest.fixture(scope="module")
def plate():
    return observe(PLATE)


@pytest.fixture(scope="module")
def plastic():
    return observe(PLASTIC)


def test_plate_record_carries_its_source_and_frame(plate):
    assert plate.source.sha256 == source_hash(PLATE)
    assert plate.source.page_size_pt == pytest.approx([841.89, 595.28], abs=0.01)
    assert plate.source.rotation == 0
    assert (plate.frame.width, plate.frame.height) == (2339, 1654)
    assert plate.frame.dpi == 200 and plate.frame.origin == "top-left"
    assert plate.text_placement == "mirrored"


def test_plate_geometry_is_observed_everywhere(plate):
    assert len(plate.paths) == 209 and plate.skipped == []
    kinds: dict[str, int] = {}
    for primitive in plate.primitives:
        kinds[primitive.kind] = kinds.get(primitive.kind, 0) + 1
    assert kinds == {"line": 148, "arc": 14, "circle": 7}


def test_plate_circles_measure_what_the_drawing_says(plate):
    circles = [primitive for primitive in plate.primitives if primitive.kind == "circle"]
    holes = sorted((primitive for primitive in circles if 26.5 < primitive.radius < 27.1),
                   key=lambda primitive: (primitive.centre[0], primitive.centre[1]))
    assert len(holes) == 4  # the four corner holes, found without being told where to look
    xs = sorted({round(hole.centre[0], 1) for hole in holes})
    ys = sorted({round(hole.centre[1], 1) for hole in holes})
    assert (xs[1] - xs[0]) / PX_PER_MM == pytest.approx(100.0, abs=0.1)
    assert (ys[1] - ys[0]) / PX_PER_MM == pytest.approx(60.0, abs=0.1)
    assert holes[0].radius / PX_PER_MM == pytest.approx(3.4, abs=0.02)
    pocket = [primitive for primitive in circles if primitive.radius > 100]
    assert len(pocket) == 1
    assert pocket[0].radius / PX_PER_MM == pytest.approx(25.0, abs=0.05)


def test_plate_numbers_are_observed_with_their_source_characters(plate):
    values = {text.value for text in plate.texts if text.value is not None}
    assert {100.0, 80.0, 60.0, 50.0, 15.0, 8.0, 6.8} <= values
    assert len(plate.texts) == 45
    callout = next(text for text in plate.texts if "THRU" in text.text and "M8" in text.text)
    assert callout.value is None and callout.char_range
    hole = next(text for text in plate.texts if text.value == 6.8)
    assert hole.char_range and "THRU" in hole.text.upper()
    for text in plate.texts:
        assert text.char_range and text.bbox.w > 0 and text.bbox.h > 0
        assert text.method == "pdf-text"


def test_a_title_block_number_is_observed_too(plate):
    """Observed, not judged: 2026 is in the record with its box, and what it means is a later step."""
    years = [text for text in plate.texts if text.value == 2026.0]
    assert years and years[0].kind == "linear"


def test_every_record_cites_a_path(plate):
    ids = [path.id for path in plate.paths]
    assert len(ids) == len(set(ids))
    for primitive in plate.primitives:
        assert primitive.path_id in ids
        assert primitive.method in ("two-point", "least-squares-fit")
    for path in plate.paths:
        assert path.method == "pdf-vector" and path.points and len(path.bbox.model_dump()) == 4


def test_plastic_sheet_gets_the_same_record_shape(plastic):
    assert plastic.source.sha256 == source_hash(PLASTIC)
    assert plastic.text_placement == "mirrored"
    assert len(plastic.paths) == 456 and plastic.skipped == []
    values = {text.value for text in plastic.texts if text.value is not None}
    assert {1.5, 3.0, 4.0, 4.8, 8.0, 10.0, 18.0, 25.0, 46.0, 60.0, 120.0} <= values
    circles = [primitive for primitive in plastic.primitives if primitive.kind == "circle"]
    assert len(circles) == 8


def test_observations_are_deterministic(plate):
    again = observe(PLATE)
    assert again.model_dump_json() == plate.model_dump_json()


def test_unsupported_suffix_is_named():
    with pytest.raises(Unsupported, match="desteklenmeyen"):
        observe(Path("examples/whatever.doc"))


def test_vector_groups_still_serve_the_plate_recognizer():
    """The plate recognizer reads object groups; the shared walk must keep handing them over."""
    page = load_page(PLATE)
    groups = vector_groups(page)
    assert len(groups) == 46
    assert sum(len(paths) for paths in groups) == 209


def test_json_round_trip(plate):
    payload = json.loads(plate.model_dump_json())
    assert payload["version"] == 1
    assert payload["source"]["sha256"] == source_hash(PLATE)
    assert payload["notes"]
