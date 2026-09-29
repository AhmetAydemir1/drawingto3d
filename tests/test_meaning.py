"""The meaning layer: every number read into the claim the drawing supports, or left unresolved.

The plate is the strict check — its seven numbers have one true reading each, and the record must
find it (holes, corner rounds, section lines, the pocket, the callout's four holes) while keeping
the symmetric readings it rejected visible as alternatives. The plastic sheet checks the same
shape without pretending: four numbers resolve, ten say so honestly.
"""

import json
from pathlib import Path

import pytest

from drawingto3d.meaning import Unsupported, _meaning_for, meaning_page
from drawingto3d.bind import SpanBinding
from drawingto3d.observe import observe

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/6/plastic enclosue.pdf")
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


@pytest.mark.parametrize("scale", [None, 4.0])
@pytest.mark.parametrize("unit", ["mm", "in"])
def test_original_value_is_not_converted_or_rounded(unit, scale):
    binding = SpanBinding(span_id="s1", text="2.345", value=2.345, unit=unit,
                          kind="linear", anchor_mode="none")
    result = _meaning_for(binding, None, [], scale)
    assert result.printed_value == 2.345 and result.unit == unit
    assert result.printed_mm == pytest.approx(2.345 * (25.4 if unit == "in" else 1), abs=0.005)


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


def test_every_printed_number_of_the_second_sheet_is_bound_to_measured_geometry(plastic):
    """All fourteen numbers measure their printed value at the sheet's own scale.

    Four only after the row's ends were re-picked, one after a segment attached to its anchor was measured,
    two after a segment lying on the axis but off both anchors was measured (`bind.py`), and three after the
    fallback pass offered the ends of the lines their anchors cross (`meaning.py`). Source ids are asserted
    rather than texts: two numbers can carry the same read text (`1 0.00`), so the texts alone would not say
    which span is which.
    """
    resolutions = [span.resolution for span in plastic.spans]
    assert resolutions.count("confirmed") == 14
    assert resolutions.count("unresolved") == 0
    confirmed = {span.span_id for span in plastic.spans if span.resolution == "confirmed"}
    assert confirmed == {f"pdf-{index}" for index in range(14)}
    assert all(span.claim is not None and span.form in {"distance", "diameter", "radius"}
               for span in plastic.spans)


def test_a_number_nothing_measures_stays_unresolved_and_says_so():
    """The property that needs no sheet: a span whose candidates verify nothing invents no claim."""
    from drawingto3d.bind import AnchorBinding, SpanBinding
    from drawingto3d.meaning import _meaning_for
    binding = SpanBinding(span_id="pdf-none", text="12,34", value=12.34, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=48.0,
                          anchors=[AnchorBinding(point=[0.0, 0.0]), AnchorBinding(point=[0.0, 48.0])])
    record = _meaning_for(binding, None, {}, 3.92)
    assert record.resolution == "unresolved" and record.claim is None and record.form == "none"
    assert "Adaylar basılı değeri doğrulamadı." in record.notes



def test_a_re_picked_row_says_which_row_it_left_and_where_it_landed(plastic):
    """Every row that had to be re-picked names what it left, how it landed and the residual."""
    def note_of(span):
        return next((note for note in span.notes if "satır ölçeğe uymadı" in note), None)

    by_pair = {span.span_id for span in plastic.spans
               if (note_of(span) or "").find("yeniden seçildi") >= 0}
    by_segment = {span.span_id for span in plastic.spans
                  if (note_of(span) or "").find("çapanın üzerindeki parça çizgisi") >= 0}
    by_axis = {span.span_id for span in plastic.spans
               if (note_of(span) or "").find("ölçü ekseni üzerinde çizilmiş") >= 0}
    assert by_pair == {"pdf-6", "pdf-8", "pdf-9", "pdf-12"}
    assert by_segment == {"pdf-10"}
    assert by_axis == {"pdf-11", "pdf-13"}
    repaired = {span.span_id for span in plastic.spans if note_of(span) is not None}
    assert by_pair | by_segment | by_axis == repaired
    for span in plastic.spans:
        note = note_of(span)
        if note is not None:
            assert "artık %" in note and "beklenen" in note
    # A row that already measures its number is not re-picked and carries no such note.
    assert all(note_of(span) is None
               for span in plastic.spans if span.span_id in {"pdf-0", "pdf-3", "pdf-7"})


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


def _binding_with(features, strokes=(), aligned=()):
    """Two anchors along +x: the first at the origin, the second 100 px away."""
    from drawingto3d.bind import AnchorBinding, Feature, SpanBinding, Stroke

    def feature(geometry_id, point, distance_px=1.0):
        return Feature(geometry_id=geometry_id, kind="line-end", point=list(point),
                       distance_px=distance_px, at="anchor")

    first = AnchorBinding(point=[0.0, 0.0], features=[feature(gid, p) for gid, p in features[0]],
                          strokes=list(strokes[0]))
    second = AnchorBinding(point=[100.0, 0.0], features=[feature(gid, p) for gid, p in features[1]],
                           strokes=list(strokes[1]))
    return SpanBinding(span_id="pdf-x", text="25,51", value=25.51, unit="mm", kind="linear",
                       anchor_mode="dimension", anchors=[first, second])


def _stroke(geometry_id, role, far, far_distance_px=1.0):
    from drawingto3d.bind import Stroke
    return Stroke(geometry_id=geometry_id, role=role, far=list(far), far_distance_px=far_distance_px)


def test_crossed_ends_offer_extension_lines_but_never_the_dimension_lines_own_ink():
    """The circularity guard: the row and the stubs printed the number, so they cannot confirm it."""
    from drawingto3d.meaning import _crossed_ends
    from drawingto3d.bind import AnchorBinding
    from tests.test_meaning import _stroke
    anchor = AnchorBinding(point=[0.0, 0.0], strokes=[
        _stroke("g1", "crossing", [0.0, 300.0]),
        _stroke("g2", "row", [400.0, 0.0]),
        _stroke("g3", "stub", [0.0, 20.0]),
        _stroke("g4", "crossing", [0.0, -120.0]),
    ])
    assert [point.geometry_id for point in _crossed_ends(anchor)] == ["g1", "g4"]


def test_a_number_that_already_measures_its_value_is_not_re_bound_and_gets_no_fallback_note():
    """The fallback is a second chance for the unresolved, not a rewrite of what already stands."""
    from drawingto3d.meaning import _distance_claims
    # 100 px at 3.92 px/mm is 25.51 mm: the reached candidates measure the printed value on their own.
    binding = _binding_with(([("g1", [0.0, 0.0])], [("g2", [100.0, 0.0])]),
                            strokes=([_stroke("g7", "crossing", [0.0, 400.0])],
                                     [_stroke("g8", "crossing", [100.0, 400.0])]))
    notes: list[str] = []
    claims = _distance_claims(binding, 25.51, 3.92, notes)
    assert claims and claims[0].drawn_mm == 25.51
    assert notes == []


def test_when_the_reached_candidates_measure_nothing_the_crossed_ends_are_offered_once():
    """pdf-1/pdf-4/pdf-5 on the second sheet: nothing reached measures the value, the crossed ends do."""
    from drawingto3d.meaning import _distance_claims
    # Reached candidates sit 300 px apart (76.53 mm); the crossed lines' far ends are 100 px apart
    # (25.51 mm). The first anchor's own reached point sits on top of its crossed end, so the reached
    # candidate keeps that point (it was offered first) and the pair is g1/g8 — one end each.
    binding = _binding_with(([("g1", [0.0, 0.0])], [("g2", [300.0, 0.0])]),
                            strokes=([_stroke("g7", "crossing", [0.0, 0.0])],
                                     [_stroke("g8", "crossing", [100.0, 0.0])]),
                            aligned=())
    notes: list[str] = []
    claims = _distance_claims(binding, 25.51, 3.92, notes)
    assert claims, "çapanın kestiği çizgilerin uçları ölçüyü vermeliydi"
    assert claims[0].drawn_mm == 25.51
    assert [point.geometry_id for point in claims[0].points] == ["g1", "g8"]
    assert len(notes) == 1 and "kestiği çizgilerin uzak uçları da hesaba katılınca bağlandı" in notes[0]
    assert "g1/g8" in notes[0]


def test_the_three_fallback_bindings_name_their_crossed_lines(plastic):
    """The fallback binds pdf-1, pdf-4 and pdf-5; each says which crossed ends it used."""
    bound = {span.span_id: span for span in plastic.spans
             if any("kestiği çizgilerin uzak uçları" in note for note in span.notes)}
    assert set(bound) == {"pdf-1", "pdf-4", "pdf-5"}
    for span in bound.values():
        note = next(note for note in span.notes if "kestiği çizgilerin uzak uçları" in note)
        ids = [point.geometry_id for point in span.claim.points]
        assert all(geometry_id in note for geometry_id in ids), (span.span_id, note)
        assert abs(span.claim.drawn_mm - span.printed_mm) <= 0.03 * span.printed_mm + 0.15
    # A number bound the ordinary way carries no such note.
    assert all(not any("kestiği çizgilerin uzak uçları" in note for note in span.notes)
               for span in plastic.spans if span.span_id in {"pdf-0", "pdf-3", "pdf-6"})


def test_the_claim_of_a_repaired_row_names_the_pair_at_the_extent(plastic):
    """On a repaired row the extent is known, so the claim is ordered across-axis first: a local pair.

    Measured on the second sheet: the across-axis gap of the claims falls from 2450,2 px in total (median
    118,6 px, eight of thirteen above 20 px) to 1262,6 px (median 0,1 px, five above 20 px). The five that
    remain are the three rows that were read as drawn (`pdf-0`, `pdf-3`, `pdf-7` — left untouched on
    purpose) and two repaired rows with no alternative to choose from (`pdf-8` has exactly one valid pair,
    `pdf-9`'s candidates all sit far from the extent).
    """
    import numpy as np
    from drawingto3d.bind import bind_page
    bindings = {span.span_id: span for span in bind_page(PLASTIC).spans}

    def binding_of(span_id):
        return bindings[span_id]

    expected = {
        "pdf-6": ("g92/g94", 9.99, 0.0),
        "pdf-9": ("g272/g279", 4.04, 55.0),
        "pdf-10": ("g70/g276", 4.74, 3.3),
        "pdf-11": ("g59/g236", 3.99, 0.1),
        "pdf-12": ("g100/g98", 1.56, 0.0),
        "pdf-13": ("g133/g73", 1.63, 0.0),
    }
    for span in plastic.spans:
        if span.span_id not in expected:
            continue
        ids, drawn_mm, across_px = expected[span.span_id]
        claim = span.claim
        assert claim is not None and "/".join(p.geometry_id for p in claim.points) == ids
        assert claim.drawn_mm == drawn_mm
        assert abs(claim.drawn_mm - span.printed_mm) <= 0.03 * span.printed_mm + 0.15
        # The ordering key, recomputed from the binding: the pair's separation across the measuring axis.
        anchors = [np.array(anchor.point, dtype=float)
                   for anchor in binding_of(span.span_id).anchors]
        axis = anchors[1] - anchors[0]
        axis = axis / float(np.linalg.norm(axis))
        normal = np.array([-axis[1], axis[0]])
        first, second = (np.array(point.point, dtype=float) for point in claim.points)
        assert abs(abs(float(np.dot(second - first, normal))) - across_px) < 0.2
    # pdf-8's only valid pair is forced, whatever the ordering: it stays where it was.
    forced = next(span for span in plastic.spans if span.span_id == "pdf-8")
    assert "/".join(p.geometry_id for p in forced.claim.points) == "g68/g268"


def test_a_row_read_as_drawn_keeps_its_claim_order(plate):
    """The plate has no repaired row, so its claims are exactly what the drawn order produced."""
    assert not any(span.row_repaired for span in plate.spans)
    claims = {span.span_id: "/".join(point.geometry_id for point in span.claim.points)
              for span in plate.spans if span.claim and len(span.claim.points) == 2}
    assert claims == {"pdf-0": "g9/g11", "pdf-1": "g4/g2", "pdf-2": "g9/g12", "pdf-5": "g52/g57",
                      "pdf-6": "g56/g48"}
