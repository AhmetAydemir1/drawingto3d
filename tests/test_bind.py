"""The binding layer: every printed number with what its arrows touch, in the record's own words.

The plate's bindings are checked against what the sheet actually draws — its dimensions end on
the holes and the corner rounds, its callout walks a chain of strokes down to a hole's rim —
because those are the relations a human reads off it. The plastic sheet is checked for the same
shape of record and for the parts that are true of it (a hole alignment, a rim landing), not for
a full answer: what the numbers mean is the step after this one.
"""

import json
from pathlib import Path

import pytest

from drawingto3d.bind import Unsupported, bind_page
from drawingto3d.ingest import load_page
from drawingto3d.perceive import perceive

PLATE = Path("examples/pdf with steps/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/plastic enclosue.pdf")
RASTERS = (Path("examples/pdf with steps/my_part.jpg"), Path("examples/pdf with steps/Flange.PNG"))
HOLES = {"g9", "g10", "g11", "g12"}
CORNER_ROUNDS = {"g2", "g4"}
PX_PER_MM = 200 / 25.4


@pytest.fixture(scope="module")
def plate():
    return bind_page(PLATE)


@pytest.fixture(scope="module")
def plastic():
    return bind_page(PLASTIC)


def by_text(record, text):
    matches = [span for span in record.spans if span.text == text]
    assert matches, f"no span named {text!r} in the record"
    return matches


def test_plate_every_number_is_attached_to_something(plate):
    """Seven printed numbers; none of them is left with arrows that touch nothing."""
    assert len(plate.spans) == 7
    statuses = {span.text: span.status for span in plate.spans}
    assert set(statuses.values()) <= {"bound", "aligned"}
    assert statuses["1 00,00"] == "aligned" and statuses["80,00"] == "bound"
    assert statuses["6,80 THRU ALL"] == "bound" and statuses["50,00"] == "bound"


def test_plate_hole_dimension_aligns_with_the_left_holes(plate):
    """100,00 is drawn with a standoff; its arrows align with the two top holes' centres."""
    span = by_text(plate, "1 00,00")[0]
    left, right = span.anchors
    assert left.aligned[0].kind == "circle-centre"
    assert left.aligned[0].point == pytest.approx([435.56, 658.22], abs=0.5)
    assert left.aligned[0].perpendicular_px == pytest.approx(145.22, abs=0.5)
    assert right.aligned[0].kind == "circle-centre"
    assert right.aligned[0].point == pytest.approx([1223.13, 658.22], abs=0.5)
    assert span.touches("g9") and span.touches("g11")
    assert span.row_px == pytest.approx(783.0, abs=0.5)


def test_plate_spacing_dimension_aligns_with_a_hole_each_end(plate):
    """60,00 runs between the left holes: one anchor aligns with each of them."""
    span = by_text(plate, "60,00")[0]
    assert span.anchors[0].aligned[0].point == pytest.approx([435.56, 658.22], abs=0.5)
    assert span.anchors[1].aligned[0].point == pytest.approx([435.56, 1130.75], abs=0.5)


def test_plate_outline_dimension_lands_on_the_corner_rounds(plate):
    """80,00's extension lines reach the plate's rounded corners — the far ends land on their arcs."""
    span = by_text(plate, "80,00")[0]
    assert span.status == "bound"
    rim_hits = [feature for anchor in span.anchors for feature in anchor.features
                if feature.kind == "arc-rim"]
    assert rim_hits and all(feature.distance_px <= 0.5 for feature in rim_hits)
    assert {feature.geometry_id for feature in rim_hits} == CORNER_ROUNDS


def test_plate_hole_callout_walks_to_a_hole_rim(plate):
    """Ø6,80's leader is drawn in more than one stroke; the record walks the chain to the rim."""
    span = by_text(plate, "6,80 THRU ALL")[0]
    assert span.status == "bound"
    walked = [feature for anchor in span.anchors for feature in anchor.features
              if feature.kind == "circle-rim" and feature.geometry_id in HOLES]
    assert walked and any(feature.chain for feature in walked)
    assert min(feature.distance_px for feature in walked) <= 0.2


def test_plate_pocket_leader_walks_to_the_pocket_rim(plate):
    span = by_text(plate, "50,00")[0]
    assert span.status == "bound"
    pocket = [feature for anchor in span.anchors for feature in anchor.features
              if feature.geometry_id == "g8" and feature.kind == "circle-rim"]
    assert pocket and min(feature.distance_px for feature in pocket) <= 0.5
    assert any("g128" in feature.chain for feature in pocket)


def test_plate_rows_are_named_and_measure_their_own_number(plate):
    """A dimension row joins both anchors and its drawn length over the printed value is the scale."""
    for text in ("1 00,00", "80,00", "60,00", "1 5,00", "8,00"):
        span = by_text(plate, text)[0]
        rows = [stroke for anchor in span.anchors for stroke in anchor.strokes if stroke.role == "row"]
        assert rows, f"{text} has no row stroke"
        assert span.row_px / span.value == pytest.approx(plate.sheet_px_per_mm, rel=0.1)


def test_plate_leaders_do_not_pretend_to_have_a_row(plate):
    """A leader points at one feature; nothing joins its two anchor points, and the record says so."""
    for text in ("6,80 THRU ALL", "50,00"):
        span = by_text(plate, text)[0]
        assert not any(stroke.role == "row" for anchor in span.anchors for stroke in anchor.strokes)


def test_plate_implied_scale_matches_the_sheet_calibration(plate):
    """The five dimension rows measure their own numbers at the sheet's scale; the two leaders
    have no row, so their anchor span is not a measurement and they are not expected to agree."""
    assert plate.sheet_px_per_mm == pytest.approx(7.82, abs=0.05)
    agreed = {span.text for span in plate.spans if span.implied_px_per_mm
              and abs(span.implied_px_per_mm - plate.sheet_px_per_mm) / plate.sheet_px_per_mm <= 0.1}
    assert agreed == {"1 00,00", "80,00", "60,00", "1 5,00", "8,00"}


def test_plastic_sheet_gets_the_same_record_without_a_claim(plastic):
    assert len(plastic.spans) == 14
    statuses = [span.status for span in plastic.spans]
    assert statuses.count("unbound") <= 1
    assert statuses.count("partial") + statuses.count("bound") >= 4
    assert plastic.sheet_px_per_mm == pytest.approx(3.92, abs=0.05)
    agreed = [span for span in plastic.spans if span.implied_px_per_mm
              and abs(span.implied_px_per_mm - plastic.sheet_px_per_mm) / plastic.sheet_px_per_mm <= 0.1]
    assert len(agreed) >= 5


def test_plastic_hole_alignment_and_rim_landing(plastic):
    """The plastic part's numbers find centres and a rim; nothing more is claimed."""
    aligned = [candidate for span in plastic.spans for anchor in span.anchors
               for candidate in anchor.aligned]
    centre_like = [candidate for candidate in aligned if candidate.kind in ("circle-centre", "arc-centre")]
    assert centre_like and any(candidate.kind == "circle-centre" for candidate in centre_like)
    eighteens = by_text(plastic, "1 8.00")[0]
    rim = [feature for anchor in eighteens.anchors for feature in anchor.features
           if feature.kind in ("circle-rim", "arc-rim")]
    assert rim and min(feature.distance_px for feature in rim) <= 2.0


def test_anchors_are_reported_as_measured(plate):
    """Binding must not move an anchor: the record repeats what perception measured."""
    _primitives, spans = perceive(load_page(PLATE))
    assert [span.span_id for span in plate.spans] == [span.id for span in spans]
    for recorded, measured in zip(plate.spans, spans):
        assert [anchor.point for anchor in recorded.anchors] == [
            [pytest.approx(value, abs=0.01) for value in anchor] for anchor in measured.anchors]


def test_bindings_are_deterministic(plate):
    assert bind_page(PLATE).model_dump_json() == plate.model_dump_json()


def test_json_round_trip(plate):
    payload = json.loads(plate.model_dump_json())
    assert payload["version"] == 1
    assert payload["source_sha256"] and payload["notes"]
    assert payload["spans"][0]["anchors"][0]["strokes"]


def test_raster_refuses_with_a_reason():
    for raster in RASTERS:
        with pytest.raises(Unsupported, match="vektör"):
            bind_page(raster)
