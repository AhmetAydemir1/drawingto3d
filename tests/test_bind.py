"""The binding layer: every printed number with what its arrows touch, in the record's own words.

The plate's bindings are checked against what the sheet actually draws — its dimensions end on
the holes and the corner rounds, its callout walks a chain of strokes down to a hole's rim —
because those are the relations a human reads off it. The plastic sheet is checked for the same
shape of record and for the parts that are true of it (a hole alignment, a rim landing), not for
a full answer: what the numbers mean is the step after this one.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from drawingto3d.bind import Unsupported, _reachable_points, bind_page
from drawingto3d.ingest import load_page
from drawingto3d.perceive import perceive

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PLASTIC = Path("examples/pdf with steps/6/plastic enclosue.pdf")
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
    # A row re-picked to the printed length can land on a different site, so a feature landing can be
    # traded for a row that measures its number: four re-picked rows turned into eight bound numbers
    # (asserted in the meaning layer), while this count moved by one. It is the row the reading needs.
    assert statuses.count("partial") + statuses.count("bound") >= 3
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
    assert payload["version"] == 4
    assert payload["source_sha256"] and payload["notes"]
    assert payload["spans"][0]["anchors"][0]["strokes"]


def test_unsupported_suffix_is_named():
    with pytest.raises(Unsupported, match="desteklenmeyen"):
        bind_page(Path("examples/whatever.doc"))


def _anchor(point, far_points=(), aligned_points=()):
    from drawingto3d.bind import AlignedCandidate, AnchorBinding, Stroke
    return AnchorBinding(
        point=list(point),
        strokes=[Stroke(geometry_id=f"p{index}", role="crossing", far=list(far), far_distance_px=1.0)
                 for index, far in enumerate(far_points)],
        aligned=[AlignedCandidate(geometry_id=f"a{index}", kind="circle-centre", point=list(aligned),
                                  along_axis_px=0.0, perpendicular_px=1.0)
                 for index, aligned in enumerate(aligned_points)])


def test_a_row_that_disagrees_with_the_sheet_scale_is_re_picked_from_reached_points():
    from drawingto3d.bind import SpanBinding, _best_reached_pair

    binding = SpanBinding(span_id="pdf-8", text="3.00", value=3.0, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=70.0, implied_px_per_mm=23.33)
    binding.anchors = [_anchor((0.0, 0.0), far_points=[(70.0, 0.0)]),
                       _anchor((70.0, 0.0), far_points=[(58.33, 0.0)], aligned_points=[(11.67, 0.0)])]
    expected = 3.0 * 3.92                                     # the printed length at the sheet's scale
    residual, first, second = _best_reached_pair(binding, expected)
    assert residual <= 0.05 and float(np.linalg.norm(second - first)) == pytest.approx(11.67)
    assert _reachable_points(binding.anchors[0])[1].tolist() == [70.0, 0.0]


def test_a_row_that_already_measures_its_number_is_left_alone():
    from drawingto3d.bind import SpanBinding, _best_reached_pair

    binding = SpanBinding(span_id="pdf-7", text="18.00", value=18.0, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=70.5, implied_px_per_mm=3.92)
    binding.anchors = [_anchor((0.0, 0.0)), _anchor((70.5, 0.0))]
    expected = 18.0 * 3.92
    assert abs(70.5 / expected - 1.0) <= 0.25                # the gate the reading uses
    # The gate is what protects a good row: nothing re-picks it, and its points stay where they were.
    assert _best_reached_pair(binding, expected)[0] <= 0.05


def test_no_reachable_pair_at_the_printed_length_means_no_repick():
    from drawingto3d.bind import SpanBinding, _best_reached_pair

    binding = SpanBinding(span_id="pdf-13", text="1.50", value=1.5, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=79.0, implied_px_per_mm=52.67)
    binding.anchors = [_anchor((0.0, 0.0)), _anchor((79.0, 0.0), far_points=[(9.8, 0.0)])]
    expected = 1.5 * 3.92
    assert _best_reached_pair(binding, expected)[0] > 0.05    # 9.8 px is not 5.88 px: the reading stays unresolved


def _span_binding(row_px, kind="linear", anchor_mode="dimension", value=4.8):
    from drawingto3d.bind import SpanBinding
    return SpanBinding(span_id="pdf-x", text="4.80", value=value, unit="mm", kind=kind,
                       anchor_mode=anchor_mode, row_px=row_px)


def test_a_step_dimensioned_by_its_own_segment_is_measured_on_that_segment(plastic):
    """pdf-10: the row the text was read against is not this dimension's row, its own segment is."""
    span = next(span for span in plastic.spans if span.span_id == "pdf-10")
    note = next(note for note in span.notes if "satır ölçeğe uymadı" in note)
    assert "çapanın üzerindeki parça çizgisi ölçüldü" in note
    assert span.row_px == 19.21 and abs(span.implied_px_per_mm - 4.0) < 0.1
    # The row's ends are the two ends of g264 — the segment the callout dimensions (18,9 px drawn where
    # 18,8 px is 4,80 mm at 3,92 px/mm) — and that segment joins them as their row.
    import numpy as np
    first, second = (np.array(anchor.point, dtype=float) for anchor in span.anchors)
    assert abs(float(np.linalg.norm(second - first)) - 19.21) < 0.05
    assert [[round(v, 1) for v in anchor.point] for anchor in span.anchors] == [[1391.0, 380.0],
                                                                               [1391.2, 399.2]]
    assert {stroke.geometry_id for anchor in span.anchors for stroke in anchor.strokes
            if stroke.role == "row"} == {"g264"}


def test_a_segment_that_misses_the_printed_length_is_not_used(plate):
    """A segment 5,9% off the printed length is left alone and writes no re-pick note.

    (The second sheet's own near miss, pdf-11's 16,6 px segment, is bound by the axis rule instead: the
    extent of that number lies on its axis, not on its anchor — asserted in the bind tests for pdf-11.)
    """
    assert all("parça çizgisi ölçüldü" not in note
               for span in plate.spans for note in span.notes)


def test_the_segment_rule_needs_a_segment_drawn_along_the_axis():
    """A segment across the axis never measures the length along it."""
    from drawingto3d.bind import AnchorBinding, SpanBinding, Stroke, _segment_matching_value
    import numpy as np
    vertical = Stroke(geometry_id="g1", role="stub", far=[0.0, 40.0], far_distance_px=40.0)
    horizontal = Stroke(geometry_id="g2", role="stub", far=[40.0, 0.0], far_distance_px=40.0)
    row = Stroke(geometry_id="g3", role="row", far=[40.0, 0.0], far_distance_px=40.0)
    binding = SpanBinding(span_id="pdf-x", text="10,20", value=10.2, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=100.0,
                          anchors=[AnchorBinding(point=[0.0, 0.0],
                                                 strokes=[vertical, row, horizontal]),
                                   AnchorBinding(point=[100.0, 0.0])])
    # 40 px along +x is 10,20 mm at 3,92 px/mm: the horizontal stub qualifies when the axis is +x, the
    # vertical one only when the axis is +y, and the row never.
    along_x = _segment_matching_value(binding, 40.0, np.array([1.0, 0.0]))
    along_y = _segment_matching_value(binding, 40.0, np.array([0.0, 1.0]))
    assert along_x is not None and list(along_x[1]) == [40.0, 0.0]
    assert along_y is not None and list(along_y[1]) == [0.0, 40.0]
    only_row = SpanBinding(span_id="pdf-y", text="10,20", value=10.2, unit="mm", kind="linear",
                           anchor_mode="dimension", row_px=100.0,
                           anchors=[AnchorBinding(point=[0.0, 0.0], strokes=[row]),
                                    AnchorBinding(point=[100.0, 0.0])])
    assert _segment_matching_value(only_row, 40.0, np.array([1.0, 0.0])) is None


def test_a_leader_callout_is_never_re_picked_against_its_value(plastic):
    """A radius callout is not drawn as a row, so its anchors stay where the reading put them."""
    radius = next(span for span in plastic.spans if span.kind == "radius")
    assert not any("satır ölçeğe uymadı" in note for note in radius.notes)


AXIS_SEGMENTS = {
    # span id: (the axis line the extent lies on, its drawn length in px)
    "pdf-11": (1344.0, 15.84),
    "pdf-13": (1202.3, 5.83),
}


def test_a_segment_on_the_axis_is_measured_even_when_it_touches_no_anchor(plastic):
    """pdf-11 and pdf-13: the extent is drawn on the measuring axis, past the row, off both anchors."""
    for span_id, (axis_x, length_px) in AXIS_SEGMENTS.items():
        span = next(span for span in plastic.spans if span.span_id == span_id)
        note = next(note for note in span.notes if "satır ölçeğe uymadı" in note)
        assert "ölçü ekseni üzerinde çizilmiş parça çizgisi ölçüldü" in note
        assert span.row_px == length_px
        assert all(abs(anchor.point[0] - axis_x) < 0.5 for anchor in span.anchors)
        assert abs(abs(span.anchors[0].point[1] - span.anchors[1].point[1]) - length_px) < 0.01


def test_the_axis_rule_needs_a_segment_on_that_axis_and_of_that_length():
    """An off-axis segment never measures the length along the axis, however well its length matches."""
    import numpy as np
    from drawingto3d.bind import AnchorBinding, SpanBinding, _segment_on_axis
    from drawingto3d.observe import Frame, Observations, Primitive, SourceRef

    def line(geometry_id, start, end):
        return Primitive(id=geometry_id, path_id="p0", kind="line", start=list(start), end=list(end))

    def observations(*primitives):
        return Observations(source=SourceRef(ref="probe", sha256="0" * 64),
                            frame=Frame(width=400, height=400, dpi=200),
                            text_placement="as-is", primitives=list(primitives),
                            notes=["probe"])

    binding = SpanBinding(span_id="pdf-x", text="4.00", value=4.0, unit="mm", kind="linear",
                          anchor_mode="dimension", row_px=69.0,
                          anchors=[AnchorBinding(point=[100.0, 100.0]),
                                   AnchorBinding(point=[100.0, 169.0])])
    axis = np.array([0.0, 1.0])
    on_axis = line("g1", [100.0, 178.0], [100.0, 193.8])       # 15,84 px = 4,04 mm, on the axis
    off_axis = line("g2", [147.0, 178.0], [147.0, 193.8])      # same length, 47 px across the axis
    wrong_length = line("g3", [100.0, 178.0], [100.0, 200.0])  # on the axis, 5,6 mm long
    assert _segment_on_axis(observations(off_axis, wrong_length), binding, 15.67, axis) is None
    drawn = _segment_on_axis(observations(off_axis, on_axis, wrong_length), binding, 15.67, axis)
    assert drawn is not None
    assert [round(value, 1) for value in drawn[0]] == [100.0, 178.0]
    assert [round(value, 1) for value in drawn[1]] == [100.0, 193.8]


def test_the_plate_never_uses_the_axis_rule(plate):
    """The plate's numbers already measure their value: no re-pick of any kind fires there."""
    for span in plate.spans:
        assert not any("satır ölçeğe uymadı" in note for note in span.notes)


def test_only_the_span_whose_segment_touches_its_anchor_is_measured_on_that_segment(plastic):
    """pdf-10 is the one number measured by a segment attached to its anchor; pdf-11 and pdf-13 are not."""
    on_anchor = {span.span_id for span in plastic.spans
                 if any("çapanın üzerindeki parça çizgisi ölçüldü" in note for note in span.notes)}
    on_axis = {span.span_id for span in plastic.spans
               if any("ölçü ekseni üzerinde çizilmiş" in note for note in span.notes)}
    assert on_anchor == {"pdf-10"} and on_axis == {"pdf-11", "pdf-13"}


REPAIRED_ON_THE_SECOND_SHEET = {"pdf-6", "pdf-8", "pdf-9", "pdf-10", "pdf-11", "pdf-12", "pdf-13"}


def test_a_repaired_row_is_marked_as_repaired(plastic, plate):
    """The flag the meaning layer orders claims by is set exactly where a row was re-picked."""
    assert {span.span_id for span in plastic.spans if span.row_repaired} == REPAIRED_ON_THE_SECOND_SHEET
    assert not any(span.row_repaired for span in plate.spans)
    # It is the same fact as the note, not a second record of it.
    assert {span.span_id for span in plastic.spans
            if any("satır ölçeğe uymadı" in note for note in span.notes)} == REPAIRED_ON_THE_SECOND_SHEET


def test_a_span_whose_phrase_is_stroke_art_reaches_the_reading_as_a_diameter():
    """The span's own text cannot carry the Ø, so the observation's kind is what the binding uses."""
    from drawingto3d.bind import _diameter_glyph_upgrade
    from drawingto3d.observe import BBox as ObservationBox
    from drawingto3d.observe import Frame, Observations, Primitive, SourceRef, TextObservation
    from drawingto3d.schema import BBox, Span, SpanKind

    glyph = Primitive(id="g214", path_id="p0", kind="circle", centre=[396.5, 973.7], radius=12.2)
    observations = Observations(source=SourceRef(ref="probe", sha256="0" * 64),
                               frame=Frame(width=400, height=400, dpi=200),
                               text_placement="as-is", primitives=[glyph], notes=["probe"])
    observations.texts.append(TextObservation(
        id="t57", text="20", kind="diameter", bbox=ObservationBox(x=417.1, y=960.9, w=38.2, h=27.4)))
    span = Span(id="pdf-17", text="20", value=20.0, kind=SpanKind.linear,
                bbox=BBox(x=417.1, y=960.9, w=38.2, h=27.4))
    assert _diameter_glyph_upgrade([span], observations) == ["20"]
    assert span.kind is SpanKind.diameter


def test_a_span_of_the_same_value_held_by_another_phrase_keeps_its_own_kind():
    """A plain 20 mm length elsewhere on the sheet is not the diameter: only its own phrase is matched."""
    from drawingto3d.bind import _diameter_glyph_upgrade
    from drawingto3d.observe import BBox as ObservationBox
    from drawingto3d.observe import Frame, Observations, SourceRef, TextObservation
    from drawingto3d.schema import BBox, Span, SpanKind

    observations = Observations(source=SourceRef(ref="probe", sha256="0" * 64),
                               frame=Frame(width=400, height=400, dpi=200),
                               text_placement="as-is", primitives=[], notes=["probe"])
    observations.texts.append(TextObservation(
        id="t57", text="20", kind="diameter", bbox=ObservationBox(x=417.1, y=960.9, w=38.2, h=27.4)))
    distant = Span(id="pdf-23", text="20", value=20.0, kind=SpanKind.linear,
                   bbox=BBox(x=417.1, y=1380.4, w=38.2, h=27.4))
    assert _diameter_glyph_upgrade([distant], observations) == []
    assert distant.kind is SpanKind.linear


def test_the_plate_has_two_stroke_art_diameters_and_the_plastic_none(plate, plastic):
    """Measured: the plate also prints its Ø as stroke art, so the rule fires there — and only there.

    The reading is unchanged on both sheets (form, resolution and matched geometry are identical with
    the rule off): what becomes accurate is the kind the record reports for those two phrases.
    """
    note = next(note for note in plate.notes if "Ø glifiyle" in note)
    assert "6,80 THRU ALL" in note and "50,00" in note
    assert {span.span_id for span in plate.spans if span.kind == "diameter"} == {"pdf-3", "pdf-4"}
    assert not any(span.kind == "diameter" for span in plastic.spans)
    assert not any("Ø glifiyle" in note for note in plastic.notes)
