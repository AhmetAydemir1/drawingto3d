"""Proposals, the one-step accept, and the visible log: who decided what, and with which evidence.

The session here is the store's own record for a synthetic sheet: a 50 x 30 mm rectangle at 2 px/mm
with two circles, a 10 mm thickness row drawn beside it and a 4 mm depth candidate. The reading that
produced these claims is handed to the store the way `create` does it, so the accept path is the same
code the product runs.
"""
import hashlib
import json
import math
from pathlib import Path

import pytest

from drawingto3d import advise
from drawingto3d import guided
from drawingto3d.guided import Decisions, GuidedStore, _atomic, _proposal_note, drawing_options
from drawingto3d.observe import Observations

CENTRE = (70.0, 50.0)
SCALE = 2.0


def mm(point):
    return [round((point[0] - CENTRE[0]) / SCALE, 4), round((point[1] - CENTRE[1]) / SCALE, 4)]


@pytest.fixture
def record(tmp_path):
    primitives = []
    corners = [[20, 20], [120, 20], [120, 80], [20, 80]]
    for i, point in enumerate(corners):
        primitives.append(dict(id=f"g{i}", path_id=f"p{i}", kind="line", start=point, end=corners[(i + 1) % 4]))
    for i, centre in enumerate([[45, 45], [90, 50]]):
        primitives.append(dict(id=f"c{i}", path_id=f"cp{i}", kind="circle", centre=centre, radius=6))
    primitives.append(dict(id="t1", path_id="tp1", kind="line", start=[20, 140], end=[20, 160]))
    primitives.append(dict(id="b1", path_id="bp1", kind="line", start=[20, 140], end=[120, 140]))
    primitives.append(dict(id="b2", path_id="bp2", kind="line", start=[20, 160], end=[70, 160]))
    # PLAN 8.6: a real sheet comes with its own border, and the flow asks about the view only where the
    # frame is missing, tilted or rotated. The border lines go last so the part's own loop index — the
    # fixture's "outline_0" — does not move.
    border = [[10, 10], [290, 10], [290, 190], [10, 190]]
    for i, point in enumerate(border):
        primitives.append(dict(id=f"bf{i}", path_id=f"bp10{i}", kind="line", start=point,
                               end=border[(i + 1) % 4]))
    source = tmp_path / "source.pdf"
    source.write_bytes(b"fixture-source-hash")
    observations = Observations(source={"ref": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
                                frame={"width": 300, "height": 200}, text_placement="as-is", primitives=primitives)
    options = drawing_options(observations)
    options["measurements"] = [{"id": "t0", "text": "50,00", "value": 50.0, "unit": "mm"},
                               {"id": "t1", "text": "6,00 THRU ALL", "value": 6.0, "unit": "mm"}]
    reading = {"version": advise.PROPOSAL_VERSION, "px_per_mm": SCALE,
               "outline_mm": {"width_mm": 50.0, "height_mm": 30.0, "primitives": 4},
               "printed": [{"span_id": "pdf-0", "text": "50,00", "value": 50.0, "unit": "mm"},
                           {"span_id": "pdf-1", "text": "6,00 THRU ALL", "value": 6.0, "unit": "mm"},
                           {"span_id": "pdf-2", "text": "10,00", "value": 10.0, "unit": "mm"},
                           {"span_id": "pdf-3", "text": "10,00", "value": 10.0, "unit": "mm"},
                           {"span_id": "pdf-4", "text": "4,00", "value": 4.0, "unit": "mm"}],
               "claims": [
                   {"span_id": "pdf-0", "form": "distance", "resolution": "confirmed", "printed_mm": 50.0,
                    "drawn_mm": 50.0, "anchors": [{"geometry_id": "g0", "kind": "line-end", "point_mm": mm((20, 20))},
                                                  {"geometry_id": "g0", "kind": "line-end", "point_mm": mm((120, 20))}]},
                   {"span_id": "pdf-1", "form": "diameter", "resolution": "confirmed", "printed_mm": 6.0,
                    "drawn_mm": 6.0, "anchor_mode": "leader", "matched_geometry": ["c0"]},
                   {"span_id": "pdf-2", "form": "diameter", "resolution": "confirmed", "printed_mm": 10.0,
                    "drawn_mm": 10.0, "anchor_mode": "leader", "matched_geometry": ["c1"]},
                   {"span_id": "pdf-3", "form": "distance", "resolution": "confirmed", "printed_mm": 10.0,
                    "drawn_mm": 10.0, "anchors": [{"geometry_id": "t1", "kind": "line-end", "point_mm": mm((20, 140))},
                                                  {"geometry_id": "t1", "kind": "line-end", "point_mm": mm((20, 160))}]},
                   {"span_id": "pdf-4", "form": "distance", "resolution": "confirmed", "printed_mm": 4.0,
                    "drawn_mm": 4.03, "anchors": [{"geometry_id": "b1", "kind": "line-end", "point_mm": mm((120, 140))},
                                                  {"geometry_id": "b2", "kind": "line-end", "point_mm": mm((60, 160))}]}],
               "notes": [], "refusals": []}
    return {"version": 1, "geometry_version": guided.GEOMETRY_VERSION, "token": "b" * 32, "revision": 0, "source": str(source),
            "source_sha256": observations.source.sha256, "options": options, "decisions": Decisions().model_dump(mode="json"),
            "reading": reading, "proposals": advise.proposals(options, reading), "history": [], "build": None, "log": []}


@pytest.fixture
def store(tmp_path, record):
    store = GuidedStore(tmp_path / "store")
    folder = store.folder(record["token"])
    folder.mkdir(parents=True)
    _atomic(folder / "session.json", record)
    return store


def test_one_accept_applies_every_proposal(store, record):
    public = store.accept("b" * 32, 0)
    decisions = Decisions.model_validate(public["decisions"])
    # The border loop is skipped as the sheet's frame, so the part is the wire — by shape, not by index.
    wire = next(p for p in public["options"]["profiles"] if p["kind"] == "wire")
    assert decisions.profile_id == wire["id"]
    xs = [point[0] for point in wire["points"]]
    assert max(xs) - min(xs) == pytest.approx(100, abs=3)  # the 50 mm part at 2 px/mm, not the 280 px frame
    assert decisions.calibration.value == 50.0
    assert decisions.calibration.span_id == "t0"  # the flow's own menu row for the same printed number
    assert decisions.thickness == 10.0
    assert decisions.trace_acknowledged is True
    assert [hole.model_dump(mode="json") for hole in decisions.holes] == [
        {"circle_id": "c0", "kind": "through", "diameter": 6.0, "depth": None},
        {"circle_id": "c1", "kind": "pocket", "diameter": 10.0, "depth": 4.0}]
    assert public["questions"] == []
    assert public["revision"] == 1


def test_the_accept_is_logged_field_by_field_with_evidence(store):
    public = store.accept("b" * 32, 0)
    accepted = [entry for entry in public["log"] if entry["action"] == "accept"]
    assert {entry["field"] for entry in accepted} >= {"calibration", "profile_id", "thickness", "hole:c0", "depth"}
    calibration = next(entry for entry in accepted if entry["field"] == "calibration")
    assert calibration["actor"] == "user"
    assert calibration["evidence"]["span_id"] == "pdf-0"      # the reading's claim
    assert calibration["evidence"]["menu_id"] == "t0"          # the flow's menu row
    assert calibration["confidence"] == "bound"
    assert calibration["value"]["value"] == 50.0


def test_the_log_survives_reopening(store, tmp_path):
    store.accept("b" * 32, 0)
    reopened = GuidedStore(tmp_path / "store")
    public = reopened.public(reopened.load("b" * 32))
    assert [entry["action"] for entry in public["log"]].count("accept") >= 6
    assert public["proposals"], "öneriler yeniden açılışta da görünür"


def test_an_edit_is_logged_as_the_user_and_an_accepted_value_as_an_accept(store):
    store.accept("b" * 32, 0)
    state = store.load("b" * 32)
    decisions = Decisions.model_validate(state["decisions"]).model_dump(mode="json")
    decisions["thickness"] = 7.5
    public = store.save("b" * 32, state["revision"], decisions)
    edit = next(entry for entry in public["log"] if entry["action"] == "edit")
    assert edit["field"] == "thickness" and edit["value"] == 7.5
    state = store.load("b" * 32)
    decisions = Decisions.model_validate(state["decisions"]).model_dump(mode="json")
    decisions["thickness"] = 10.0
    public = store.save("b" * 32, state["revision"], decisions)
    assert any(entry["action"] == "accept" and entry["field"] == "thickness" for entry in public["log"])


def test_undo_returns_the_decisions_and_says_so(store):
    store.accept("b" * 32, 0)
    state = store.load("b" * 32)
    decisions = Decisions.model_validate(state["decisions"]).model_dump(mode="json")
    decisions["thickness"] = 7.5
    store.save("b" * 32, state["revision"], decisions)
    public = store.save("b" * 32, store.load("b" * 32)["revision"], undo=True)
    assert Decisions.model_validate(public["decisions"]).thickness == 10.0
    assert any(entry["action"] == "undo" for entry in public["log"])


def test_accept_without_proposals_is_refused(store):
    state = store.load("b" * 32)
    state["proposals"] = []
    _atomic(store.folder("b" * 32) / "session.json", state)
    with pytest.raises(ValueError):
        store.accept("b" * 32, state["revision"])


def test_accepting_a_new_pocket_does_not_accept_an_unselected_depth(store):
    state = store.accept("b" * 32, 0, fields=["thickness"])
    with pytest.raises(ValueError, match="derinlik de gerekli"):
        store.accept("b" * 32, state["revision"], fields=["hole:c1"])
    reopened = store.load("b" * 32)
    assert reopened["revision"] == state["revision"]
    assert reopened["decisions"]["holes"] == []
    assert reopened["log"] == state["log"]


def test_accepting_a_pocket_preserves_its_existing_user_depth(store):
    state = store.accept("b" * 32, 0)
    decisions = state["decisions"]
    pocket = next(hole for hole in decisions["holes"] if hole["circle_id"] == "c1")
    pocket.update(depth=3.0, diameter=9.0)
    state = store.save("b" * 32, state["revision"], decisions)
    state = store.accept("b" * 32, state["revision"], fields=["hole:c1"])
    pocket = next(hole for hole in state["decisions"]["holes"] if hole["circle_id"] == "c1")
    assert pocket["diameter"] == 10.0
    assert pocket["depth"] == 3.0
    assert state["log"][-1]["field"] == "hole:c1"
    assert state["log"][-1]["value"]["depth"] == 3.0


def test_accepting_only_depth_updates_an_existing_pocket_and_can_be_undone(store):
    state = store.accept("b" * 32, 0)
    decisions = state["decisions"]
    next(hole for hole in decisions["holes"] if hole["circle_id"] == "c1")["depth"] = 3.0
    state = store.save("b" * 32, state["revision"], decisions)
    previous_revision = state["revision"]
    state = store.accept("b" * 32, previous_revision, fields=["depth"])
    assert state["revision"] == previous_revision + 1
    assert next(h for h in state["decisions"]["holes"] if h["circle_id"] == "c1")["depth"] == 4.0
    assert next(h for h in state["decisions"]["holes"] if h["circle_id"] == "c0")["depth"] is None
    assert state["log"][-1]["field"] == "depth"
    undone = store.save("b" * 32, state["revision"], undo=True)
    assert next(h for h in undone["decisions"]["holes"] if h["circle_id"] == "c1")["depth"] == 3.0


def test_accepting_depth_without_a_pocket_is_a_clear_error(store):
    with pytest.raises(ValueError, match="uygulanacağı kör cep yok"):
        store.accept("b" * 32, 0, fields=["depth"])
    reopened = store.load("b" * 32)
    assert reopened["revision"] == 0 and reopened["log"] == []


def test_explicit_pocket_dependencies_can_be_accepted_together(store):
    state = store.accept("b" * 32, 0, fields=["hole:c1", "depth", "thickness"])
    assert state["decisions"]["thickness"] == 10.0
    assert state["decisions"]["holes"] == [{"circle_id": "c1", "kind": "pocket", "diameter": 10.0, "depth": 4.0}]
    assert state["decisions"]["profile_id"] is None
    assert state["decisions"]["trace_acknowledged"] is False


@pytest.mark.parametrize("field", ["hole:inner", "calibration", "profile_id"])
def test_geometric_proposal_notes_do_not_require_printed_span_evidence(field):
    item = {"field": field, "value": "circle_inner", "confidence": "rule",
            "evidence": {"rule": "eş merkezli daire geometrisi", "drawn_mm": 12.0}}
    note = _proposal_note(item)
    assert "önerisi" in note
    if field != "profile_id":
        assert "Basılı ölçüye bağlanmamış geometri" in note


def test_the_accepted_decisions_build_the_measured_solid(store):
    store.accept("b" * 32, 0)
    public = store.build("b" * 32, store.load("b" * 32)["revision"])
    assert public["build_status"] == "complete", public.get("error")
    folder = Path(store.load("b" * 32)["build"]["folder"])
    sizes = [float(value) for value in (folder / "measure.txt").read_text().split()]
    assert math.isclose(sizes[0], 50.0, abs_tol=0.2) and math.isclose(sizes[1], 30.0, abs_tol=0.2)
    log = public["log"]
    assert [entry["action"] for entry in log].count("build") == 2
    assert log[-1]["evidence"].get("passed") is True
