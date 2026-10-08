"""The reading's claims become proposals with evidence — and a claim that cannot be verified is dropped.

The fixture is a drawing the reading already agrees with: a 100 x 50 mm outline at 4 px/mm centred at
(300, 300) px, two 6 mm through holes, one 20 mm pocket, a 10 mm thickness dimension drawn as the
outside view's own edge, and a 4 mm pocket depth dimension beside it. Nothing here is family-specific:
the proposals come from the geometry ids and the printed lengths the reading measured.
"""
import pytest

from drawingto3d import advise

CENTRE = (300.0, 300.0)
SCALE = 4.0


def mm(point):
    """The reading's own frame: a pixel point as millimetres from the outline's centre."""
    return [round((point[0] - CENTRE[0]) / SCALE, 4), round((point[1] - CENTRE[1]) / SCALE, 4)]


def line(gid, start, end):
    return {"id": gid, "kind": "line", "start": list(start), "end": list(end)}


@pytest.fixture
def sheet():
    outline_edges = [line("e0", (100, 200), (500, 200)), line("e1", (500, 200), (500, 400)),
                     line("e2", (500, 400), (100, 400)), line("e3", (100, 400), (100, 200))]
    circles = [{"id": "h1", "center": [180, 260], "radius": 12}, {"id": "h2", "center": [420, 260], "radius": 12},
               {"id": "p1", "center": [300, 300], "radius": 40}]
    outside = [line("v1", (300, 500), (300, 540)), line("b1", (100, 600), (500, 600)), line("b2", (100, 640), (300, 640))]
    primitives = outline_edges + outside + [{"id": row["id"], "kind": "circle", "center": row["center"],
                                             "radius": row["radius"]} for row in circles]
    profile = {"id": "outline_0", "kind": "wire", "join_max_px": 0.0, "geometry_ids": [e["id"] for e in outline_edges],
               "edges": outline_edges, "points": [[100, 200], [500, 200], [500, 400], [100, 400]]}
    options = {"frame": {"width": 1400, "height": 990}, "profiles": [profile], "circles": circles,
               "primitives": primitives, "measurements": []}
    reading = {"version": advise.PROPOSAL_VERSION, "px_per_mm": SCALE,
               "outline_mm": {"width_mm": 100.0, "height_mm": 50.0, "primitives": 4},
               "printed": [{"span_id": "pdf-0", "text": "100,00", "value": 100.0, "unit": "mm"},
                           {"span_id": "pdf-1", "text": "6,00 THRU ALL", "value": 6.0, "unit": "mm"},
                           {"span_id": "pdf-2", "text": "20,00", "value": 20.0, "unit": "mm"},
                           {"span_id": "pdf-3", "text": "10,00", "value": 10.0, "unit": "mm"},
                           {"span_id": "pdf-4", "text": "4,00", "value": 4.0, "unit": "mm"}],
               "claims": [
                   {"span_id": "pdf-0", "form": "distance", "resolution": "confirmed", "printed_mm": 100.0,
                    "drawn_mm": 100.0, "anchors": [{"geometry_id": "e0", "kind": "line-end", "point_mm": mm((100, 200))},
                                                   {"geometry_id": "e1", "kind": "line-end", "point_mm": mm((500, 200))}]},
                   {"span_id": "pdf-1", "form": "diameter", "resolution": "confirmed", "printed_mm": 6.0,
                    "drawn_mm": 6.0, "anchor_mode": "leader", "matched_geometry": ["h1", "h2"]},
                   {"span_id": "pdf-2", "form": "diameter", "resolution": "confirmed", "printed_mm": 20.0,
                    "drawn_mm": 20.0, "anchor_mode": "leader", "matched_geometry": ["p1"]},
                   {"span_id": "pdf-3", "form": "distance", "resolution": "confirmed", "printed_mm": 10.0,
                    "drawn_mm": 10.0, "anchors": [{"geometry_id": "v1", "kind": "line-end", "point_mm": mm((300, 500))},
                                                   {"geometry_id": "v1", "kind": "line-end", "point_mm": mm((300, 540))}]},
                   {"span_id": "pdf-4", "form": "distance", "resolution": "confirmed", "printed_mm": 4.0,
                    "drawn_mm": 4.03, "anchors": [{"geometry_id": "b1", "kind": "line-end", "point_mm": mm((500, 600))},
                                                   {"geometry_id": "b2", "kind": "line-end", "point_mm": mm((260, 640))}]}],
               "notes": [], "refusals": []}
    return options, reading


def fields(items):
    return {item["field"]: item for item in items}


def test_every_decision_the_reading_can_answer_is_proposed(sheet):
    options, reading = sheet
    items = fields(advise.proposals(options, reading))
    assert set(items) == {"profile_id", "calibration", "hole:h1", "hole:h2", "hole:p1", "thickness", "depth"}
    assert items["profile_id"]["value"] == "outline_0"
    assert items["calibration"]["value"]["value"] == 100.0
    assert items["calibration"]["value"]["first"] == [100.0, 200.0]
    assert items["calibration"]["value"]["second"] == [500.0, 200.0]
    assert items["hole:h1"]["value"] == {"circle_id": "h1", "kind": "through", "diameter": 6.0}
    assert items["hole:p1"]["value"] == {"circle_id": "p1", "kind": "pocket", "diameter": 20.0}
    assert items["thickness"]["value"] == 10.0
    assert items["depth"]["value"] == 4.0


def test_a_proposal_carries_its_evidence(sheet):
    options, reading = sheet
    items = fields(advise.proposals(options, reading))
    assert items["calibration"]["evidence"]["span_id"] == "pdf-0"
    assert items["calibration"]["evidence"]["resolved_from"] == "reading"
    assert items["calibration"]["evidence"]["anchor_geometry_ids"] == ["e0", "e1"]
    assert items["hole:h1"]["evidence"]["text"] == "6,00 THRU ALL"
    assert items["hole:h1"]["confidence"] == "bound"
    assert items["thickness"]["evidence"]["span_id"] == "pdf-3"
    assert items["depth"]["evidence"]["text"] == "4,00"


def test_the_identity_question_offers_the_other_printed_number(sheet):
    options, reading = sheet
    items = fields(advise.proposals(options, reading))
    assert [row["value"] for row in items["thickness"]["alternatives"]] == [4.0]
    assert [row["value"] for row in items["depth"]["alternatives"]] == [10.0]


def test_a_wrong_reading_point_falls_back_to_the_length_constraint(sheet):
    options, reading = sheet
    reading["claims"][0]["anchors"][1]["point_mm"] = [50.0, -125.0]  # 400 px away from e1
    items = fields(advise.proposals(options, reading))
    proposal = items["calibration"]
    assert proposal["evidence"]["resolved_from"] == "search"
    first, second = proposal["value"]["first"], proposal["value"]["second"]
    drawn_mm = ((first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2) ** 0.5 / SCALE
    assert abs(drawn_mm - 100.0) <= 1.0


def test_a_value_the_geometry_cannot_support_is_dropped(sheet):
    options, reading = sheet
    reading["claims"][0]["printed_mm"] = 77.0  # no pair of points is 77 mm apart at this scale
    items = fields(advise.proposals(options, reading))
    assert items["calibration"]["evidence"]["span_id"] != "pdf-0"
    assert items["calibration"]["value"]["value"] == 10.0  # the next span that does hold up


def test_a_row_that_only_matches_by_projection_is_not_a_calibration(sheet):
    options, reading = sheet
    items = fields(advise.proposals(options, reading))
    assert items["calibration"]["evidence"]["span_id"] == "pdf-0"  # not the 4 mm projection row
    assert items["calibration"]["evidence"]["axis"] == "distance"
    assert items["depth"]["value"] == 4.0


def test_without_a_frame_holes_and_span_survive_but_the_rules_do_not(sheet):
    options, reading = sheet
    reading["outline_mm"] = {"width_mm": 300.0, "height_mm": 200.0, "primitives": 4}
    items = fields(advise.proposals(options, reading))
    assert set(items) == {"calibration", "hole:h1", "hole:h2", "hole:p1"}
    assert items["calibration"]["evidence"]["resolved_from"] == "search"
    assert items["hole:p1"]["value"]["kind"] == "through"  # no depth candidate without a frame, so no pocket
    assert items["hole:p1"]["confidence"] == "assumed"


def test_a_refused_reading_proposes_nothing(sheet):
    options, reading = sheet
    reading["refused"] = "pafta ölçeği okunamadı"
    assert advise.proposals(options, reading) == []


def test_a_row_resolved_in_the_readings_frame_keeps_its_axis_decision():
    """A row the reading resolved is an x/y distance when a span matches, not just a straight line.

    `10/Exercise 12`'s three Ø20.00 rows: their mapped ends sit 3.9 px across the axis (a section
    view's extension lines are not perfectly plumb), so `round(distance)` misses the printed 20 mm by
    0.9 px while the y span holds it to 0.67 px — the same decision the search path makes.
    """
    options = {"frame": {"width": 1400, "height": 990}, "profiles": [], "circles": [],
               "primitives": [line("g84", (857.22, 965.28), (849.44, 973.06)),
                              line("g85", (871.39, 986.39), (861.11, 996.94))], "measurements": []}
    claim = {"span_id": "pdf-1", "form": "distance", "resolution": "confirmed", "printed_mm": 20.0,
             "drawn_mm": 20.43, "anchors": [{"geometry_id": "g84", "kind": "line-end", "point_mm": [-132.08, -139.25]},
                                            {"geometry_id": "g85", "kind": "line-end", "point_mm": [-129.57, -118.82]}]}
    resolved = advise.resolve_claim(claim, advise._geometry_points(options), 1.55, ([1061.945, 1181.724], 1.55))
    assert resolved["from"] == "reading"
    assert resolved["mode"] == "y"
    assert resolved["error_px"] == pytest.approx(0.67, abs=0.01)
    assert resolved["points"][0] == pytest.approx([857.22, 965.89], abs=0.01)


def test_a_row_whose_axis_span_is_a_coincidence_is_not_an_axis_row():
    """A diagonal row stays `projected`: its span match must not turn it into an axis distance.

    `5/Plate With A Pocket Drawing`'s 8 mm depth row: its mapped ends sit 275.6 px apart across a
    62.8 px y span — the y span happens to equal the printed 8 mm, but the row is not drawn along y
    (the anchors are no extension-line pair), so it is a plain distance, exactly as before.
    """
    def mm(point):
        return [round((point[0] - 1000.0) / 7.85, 4), round((point[1] - 1000.0) / 7.85, 4)]

    options = {"frame": {"width": 1400, "height": 990}, "profiles": [], "circles": [],
               "primitives": [line("ga", (1301.88, 233.63), (1311.88, 243.63)),
                              line("gb", (1026.30, 296.42), (1036.30, 306.42))], "measurements": []}
    claim = {"span_id": "pdf-6", "form": "distance", "resolution": "confirmed", "printed_mm": 8.0,
             "drawn_mm": 8.0, "anchors": [{"geometry_id": "ga", "kind": "line-end", "point_mm": mm((1301.88, 233.63))},
                                           {"geometry_id": "gb", "kind": "line-end", "point_mm": mm((1026.30, 296.42))}]}
    resolved = advise.resolve_claim(claim, advise._geometry_points(options), 7.85, ((1000.0, 1000.0), 7.85))
    assert resolved["from"] == "reading"
    assert resolved["mode"] == "projected"
    assert resolved["error_px"] == pytest.approx(219.84, abs=0.05)
