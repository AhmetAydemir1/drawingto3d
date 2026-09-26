"""The meaning layer: every number read into the claim the drawing supports, or left unresolved.

The plate is the strict check — its seven numbers have one true reading each, and the record must
find it (holes, corner rounds, section lines, the pocket, the callout's four holes) while keeping
the symmetric readings it rejected visible as alternatives. The plastic sheet checks the same
shape without pretending: four numbers resolve, ten say so honestly.
"""

import json
from pathlib import Path

import pytest

from drawingto3d.meaning import Unsupported, meaning_page
from drawingto3d.observe import observe

PLATE = Path("examples/pdf with steps/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/plastic enclosue.pdf")
HOLES = {"g9", "g10", "g11", "g12"}


@pytest.fixture(scope="module")
def plate():
    return meaning_page(PLATE)


@pytest.fixture(scope="module")
def plastic():
    return meaning_page(PLASTIC)


def by_text(record, text):
    matches = [span for span in record.spans if span.text == text]
    assert matches, f"no span named {text!r} in the record"
    return matches[0]


def ids(claim):
    return {point.geometry_id for point in claim.points}


def test_plate_every_number_is_read(plate):
    """Seven printed numbers, seven confirmed readings, no leftovers on the plate."""
    assert len(plate.spans) == 7
    assert all(span.resolution == "confirmed" for span in plate.spans)
    forms = [span.form for span in plate.spans]
    assert forms.count("distance") == 5 and forms.count("diameter") == 2


def test_plate_hole_spacing_reads_the_top_holes(plate):
    span = by_text(plate, "1 00,00")
    assert ids(span.claim) == {"g9", "g11"}
    assert span.claim.drawn_mm == pytest.approx(100.71, abs=0.05)
    alternatives = {frozenset(ids(claim)) for claim in span.alternatives}
    assert frozenset({"g12", "g10"}) in alternatives  # the bottom pair stays visible, not hidden


def test_plate_spacing_reads_the_left_holes(plate):
    span = by_text(plate, "60,00")
    assert ids(span.claim) == {"g9", "g12"}
    assert span.claim.drawn_mm == pytest.approx(60.43, abs=0.05)


def test_plate_outline_dimension_reads_the_corner_rounds(plate):
    """80,00's extension lines land on the rounded corners, so the claim is between their arcs."""
    span = by_text(plate, "80,00")
    assert ids(span.claim) == {"g4", "g2"}
    assert all(point.kind == "arc-rim" for point in span.claim.points)
    assert span.claim.drawn_mm == pytest.approx(80.46, abs=0.05)


def test_plate_section_dimensions_read_their_lines(plate):
    thickness = by_text(plate, "1 5,00")
    assert ids(thickness.claim) == {"g52", "g57"}
    assert thickness.claim.drawn_mm == pytest.approx(15.1, abs=0.05)
    depth = by_text(plate, "8,00")
    assert ids(depth.claim) == {"g56", "g48"}
    assert depth.claim.drawn_mm == pytest.approx(8.03, abs=0.05)


def test_plate_hole_callout_sizes_the_four_holes(plate):
    """'4 x Ø6,80' sizes a set: the claim carries every circle of that size, and the count checks."""
    span = by_text(plate, "6,80 THRU ALL")
    assert span.form == "diameter" and span.claim.form == "diameter"
    assert ids(span.claim) == {"g12"}  # the hole the leader walked to
    assert set(span.claim.matched_geometry) == HOLES
    assert span.claim.drawn_mm == pytest.approx(6.85, abs=0.02)
    assert span.count == 4 and span.covered == 4


def test_plate_pocket_leader_sizes_the_pocket(plate):
    span = by_text(plate, "50,00")
    assert span.form == "diameter"
    assert ids(span.claim) == {"g8"}
    assert span.claim.matched_geometry == ["g8"]
    assert span.claim.drawn_mm == pytest.approx(50.36, abs=0.05)


def test_confirmed_claims_hold_their_own_numbers(plate, plastic):
    """Nothing is confirmed whose drawn size disagrees with the printed value beyond tolerance."""
    for record in (plate, plastic):
        for span in record.spans:
            if span.resolution != "confirmed" or span.claim is None:
                continue
            tolerance = max(0.03 * span.claim.printed_mm, 0.15)
            assert span.claim.deviation_mm <= tolerance + 0.005, span.text


def test_claims_cite_observed_geometry(plate):
    observations = observe(PLATE)
    known = {primitive.id for primitive in observations.primitives}
    known |= {path.id for path in observations.paths}
    for span in plate.spans:
        for claim in [span.claim] + span.alternatives:
            if claim is None:
                continue
            assert {point.geometry_id for point in claim.points} <= known
            for matched in claim.matched_geometry:
                assert matched in known


def test_plastic_radius_leader_finds_the_fillet_family(plastic):
    """R8.00 resolves against the sheet's fillets: one chosen arc, the family recorded."""
    span = by_text(plastic, "R8.00")
    assert span.form == "radius" and span.claim is not None
    assert span.claim.points[0].geometry_id == "g8"
    assert "g8" in span.claim.matched_geometry and len(span.claim.matched_geometry) >= 4
    assert span.claim.drawn_mm == pytest.approx(8.02, abs=0.05)


def test_plastic_unresolved_spans_say_so(plastic):
    """Where nothing verifies, the record says unresolved and does not invent a claim."""
    resolutions = [span.resolution for span in plastic.spans]
    assert resolutions.count("confirmed") == 4
    assert resolutions.count("unresolved") == 10
    confirmed = {span.text for span in plastic.spans if span.resolution == "confirmed"}
    assert confirmed == {"25.00", "R8.00", "46.00", "1 8.00"}
    for span in plastic.spans:
        if span.resolution == "unresolved":
            assert span.claim is None and span.form == "none"


def test_meanings_are_deterministic(plate):
    assert meaning_page(PLATE).model_dump_json() == plate.model_dump_json()


def test_json_round_trip(plate):
    payload = json.loads(plate.model_dump_json())
    assert payload["version"] == 1
    assert payload["source_sha256"] and payload["notes"]
    assert payload["spans"][0]["claim"]["form"] in ("distance", "diameter", "radius")


def test_unsupported_suffix_is_named():
    with pytest.raises(Unsupported, match="desteklenmeyen"):
        meaning_page(Path("examples/whatever.doc"))
