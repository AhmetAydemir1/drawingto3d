"""G12.3 (PLAN-25 §45–§54): the geometry belongs to the view it was measured in.

The candidates are the segmenter's own boxes, persisted once when the session is created; each
profile/circle is owned by the one candidate that actually contains it, and "which view is the
solid's source" is the user's own decision — never inferred from the picture. A picture classified
as isometric (or any view the user did not name) is never a solid source by default.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from drawingto3d import build_strategy, callout_models, guided, view_scope
from drawingto3d.guided import Decisions, GuidedStore, _atomic

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
PART_VIEW = "view-3"          # the plate's own front view, in the segmenter's ranked order
EQUATION_HOLES = 4            # the plate's own drilled holes live in that same view


def _record(store, token):
    return json.loads((store.folder(token) / "session.json").read_text(encoding="utf-8"))


def test_create_persists_candidates_once_and_owns_every_geometry(tmp_path):
    """§46/§48: candidates ride in the public state and each geometry names its one owning view."""
    opened = GuidedStore(tmp_path / "store").create(PLATE.read_bytes())
    candidates = opened["view_candidates"]
    ids = [row["id"] for row in candidates]
    assert ids == ["view-0", "view-1", "view-2", "view-3", "view-4"]
    assert {"kind": "isometric", "used_for_solid": False} == {
        key: next(row for row in candidates if row["id"] == "view-0")[key]
        for key in ("kind", "used_for_solid")}
    assert next(row for row in candidates if row["id"] == "view-0")["label"] == "İzometrik adayı"
    assert next(row for row in candidates if row["id"] == "view-4")["label"] == "Kesit adayı"
    assert [row["label"] for row in candidates if row["id"] in ("view-1", "view-2", "view-3")] \
        == ["Görünüş 1", "Görünüş 2", "Görünüş 3"]
    # Every offered geometry carries its ownership — a candidate id, or an explicit None.
    profiles = opened["options"]["profiles"]
    circles = opened["options"]["circles"]
    allowed = set(ids) | {None}
    assert all(row.get("view_id", "missing") in allowed for row in profiles + circles)
    # The plate's own contour and its holes belong to the part view; the title block's content does not.
    assert any(row.get("view_id") == PART_VIEW for row in profiles)
    part_circles = [c for c in circles if c.get("view_id") == PART_VIEW]
    assert len(part_circles) >= EQUATION_HOLES
    pocket = next(c for c in circles if abs(c["radius"] - 196.9) < 0.1)
    assert pocket["view_id"] == PART_VIEW
    assert any(row.get("view_id") == "view-4" for row in profiles)
    # §51: the roles menu is server-labelled, and no machine classification is claimed as truth.
    assert opened["view_roles"]["primary"] == "Ana görünüş"
    assert opened["view_roles"]["isometric_ignore"] == "İzometrik (üretim kaynağı değil)"
    assert opened["drawing_views"] == []


def test_assignment_is_deterministic_and_refuses_ambiguity():
    """§48: fully/strongly inside one candidate → that view; anything straddling → None."""
    candidates = [{"id": "v1", "kind": "front", "bbox": {"x": 0, "y": 0, "w": 100, "h": 100}},
                  {"id": "v2", "kind": "front", "bbox": {"x": 100, "y": 0, "w": 100, "h": 100}}]
    options = {"profiles": [
        {"id": "inside", "kind": "wire", "points": [[10, 10], [20, 10], [20, 20], [10, 20]]},
        {"id": "touching", "kind": "wire", "points": [[90, 10], [100, 10], [100, 20], [90, 20]]},
        {"id": "strong", "kind": "wire", "points": [[90, 10], [100.5, 10], [100.5, 20], [90, 20]]},
        {"id": "straddle", "kind": "wire", "points": [[95, 10], [105, 10], [105, 20], [95, 20]]},
        {"id": "outside", "kind": "wire", "points": [[500, 500], [510, 500], [510, 510], [500, 510]]},
    ], "circles": [
        {"id": "hole", "center": [50, 50], "radius": 5.0},
        {"id": "bridge", "center": [100, 50], "radius": 30.0},
    ]}
    counts = view_scope.assign_view_ids(options, candidates)
    got = {row["id"]: row["view_id"] for row in options["profiles"] + options["circles"]}
    assert got == {"inside": "v1", "touching": "v1", "strong": "v1",
                   "straddle": None, "outside": None, "hole": "v1", "bridge": None}
    assert counts == {"v1": 4, "v2": 0, "unowned": 3}


def test_reopen_does_not_resegment(tmp_path):
    """§46: a stored candidate list is the session's own; a reopen must never re-run the segmenter."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    record = _record(store, opened["token"])
    sentinel = [{"id": "view-sentinel", "kind": "unknown",
                 "bbox": {"x": 1.0, "y": 2.0, "w": 3.0, "h": 4.0}}]
    record["view_candidates"] = sentinel
    _atomic(store.folder(opened["token"]) / "session.json", record)
    reopened = GuidedStore(store.root).public(GuidedStore(store.root).load(opened["token"]))
    assert [row["id"] for row in reopened["view_candidates"]] == ["view-sentinel"]


def test_legacy_record_migrates_under_the_normal_rules_and_gains_the_view_layer(tmp_path):
    """§46/§49: a pre-view record re-reads on version bump — same identity rules, then it has views."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    legacy = _record(store, opened["token"])
    legacy["geometry_version"] = 3
    legacy.pop("view_candidates", None)
    for row in legacy["options"]["profiles"] + legacy["options"]["circles"]:
        row.pop("view_id", None)
    _atomic(store.folder(opened["token"]) / "session.json", legacy)
    reopened = GuidedStore(store.root).public(GuidedStore(store.root).load(opened["token"]))
    assert reopened["geometry"]["version"] == 4 and not reopened["geometry"]["stale"]
    assert [row["id"] for row in reopened["view_candidates"]][:2] == ["view-0", "view-1"]
    assert any(row.get("view_id") == PART_VIEW for row in reopened["options"]["profiles"])


def test_drawing_view_command_is_server_stamped_and_guarded(tmp_path):
    """§47: the role is the user's; the version it was decided against is the server's own stamp."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    state = store.set_drawing_view(token, opened["revision"], "view-3", "primary")
    assert state["drawing_views"] == [{"view_id": "view-3", "role": "primary", "geometry_version": 4}]
    with pytest.raises(ValueError):
        store.set_drawing_view(token, state["revision"], "view-99", "primary")
    with pytest.raises(ValueError):
        store.set_drawing_view(token, state["revision"], "view-0", "ana")
    # A forged version never lands: the command re-reads the record and stamps it itself.
    state = store.set_drawing_view(token, state["revision"], "view-4", "section",
                                   payload={"geometry_version": 99})
    row = next(r for r in state["drawing_views"] if r["view_id"] == "view-4")
    assert row == {"view_id": "view-4", "role": "section", "geometry_version": 4}
    # Clearing one view's role is its own undoable step.
    state = store.set_drawing_view(token, state["revision"], "view-4", None)
    assert [r["view_id"] for r in state["drawing_views"]] == ["view-3"]


def test_view_role_change_stales_target_and_strategy(tmp_path):
    """§50 + §53: ownership is part of the fingerprint, so confirming a role moves it."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    state = store.set_strategy(token, opened["revision"], {"kind": "extrude_profile"})
    assert state["build_strategy"]["state"] == "current"
    key_before = callout_models.geometry_key(_record(store, token))
    state = store.set_drawing_view(token, state["revision"], "view-3", "primary")
    assert state["build_strategy"]["state"] == "stale"
    assert callout_models.geometry_key(_record(store, token)) != key_before
    # Re-confirming the strategy against the new ownership makes it current again.
    state = store.set_strategy(token, state["revision"], {"kind": "extrude_profile"})
    assert state["build_strategy"]["state"] == "current"
    state = store.set_drawing_view(token, state["revision"], "view-3", "unused")
    assert state["build_strategy"]["state"] == "stale"


def test_cross_view_target_is_asked_not_built(tmp_path):
    """§52/§53: the solid comes from the confirmed primary view — a different view is a conflict."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    record = _record(store, token)
    title_profile = next(row for row in record["options"]["profiles"] if row.get("view_id") == "view-4")
    part_profile = next(row for row in record["options"]["profiles"] if row.get("view_id") == PART_VIEW)
    state = store.set_drawing_view(token, opened["revision"], PART_VIEW, "primary")
    state = store.save(token, state["revision"], decisions={**state["decisions"],
                                                           "profile_id": title_profile["id"]})
    readiness = store.readiness(token)
    assert "view_scope_conflict" in {row["category"] for row in readiness["issues"]}
    conflict = next(row for row in readiness["issues"] if row["category"] == "view_scope_conflict")
    assert conflict["reason"] == "cross_view" and PART_VIEW in conflict["detail"]
    with pytest.raises(ValueError):
        store.build(token, state["revision"])
    # With the strategy approved *against this geometry*, the dispatcher's next sentence is the view one.
    state = store.set_strategy(token, state["revision"], {"kind": "extrude_profile"})
    fresh = _record(store, token)
    with pytest.raises(ValueError) as refused:
        guided.dispatch_plan(SimpleNamespace(record=fresh, decisions=Decisions.model_validate(fresh["decisions"])))
    assert "ana görünüş" in str(refused.value)
    # The primary view's own contour is not a conflict; it is simply the build's next question.
    state = store.save(token, state["revision"], decisions={**state["decisions"],
                                                            "profile_id": part_profile["id"]})
    readiness = store.readiness(token)
    assert "view_scope_conflict" not in {row["category"] for row in readiness["issues"]}


def test_isometric_candidate_is_never_a_solid_source(tmp_path):
    """§53: without any confirmation the picture is not a source; geometry the user left unowned isn't either."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    record = _record(store, token)
    part_profile = next(row for row in record["options"]["profiles"] if row.get("view_id") == PART_VIEW)
    state = store.save(token, opened["revision"], decisions={**opened["decisions"],
                                                             "profile_id": part_profile["id"]})
    assert "view_scope_conflict" not in {row["category"] for row in store.readiness(token)["issues"]}
    # Same contour, owned by the isometric picture: refused by name, before any confirmation exists.
    record = _record(store, token)
    for row in record["options"]["profiles"]:
        if row["id"] == part_profile["id"]:
            row["view_id"] = "view-0"
    for row in record["options"]["circles"]:
        if row.get("view_id") == PART_VIEW:
            row["view_id"] = "view-0"
    _atomic(store.folder(token) / "session.json", record)
    conflict = next(row for row in store.readiness(token)["issues"]
                    if row["category"] == "view_scope_conflict")
    assert conflict["reason"] == "candidate_isometric" and "view-0" in conflict["detail"]
    state = store.set_strategy(token, state["revision"], {"kind": "extrude_profile"})
    with pytest.raises(ValueError):
        store.build(token, state["revision"])
    # The dispatcher's own next sentence names the picture (the earlier callout gates stay theirs).
    fresh = _record(store, token)
    with pytest.raises(ValueError) as refused:
        guided.dispatch_plan(SimpleNamespace(record=fresh, decisions=Decisions.model_validate(fresh["decisions"])))
    assert "izometrik" in str(refused.value).lower()
    # Unowned is recorded as None, and is *not* a conflict: with no ownership there is no cross-view
    # relation to enforce, so the contour builds as it did before the view layer existed.
    record = _record(store, token)
    for row in record["options"]["profiles"]:
        if row["id"] == part_profile["id"]:
            row["view_id"] = None
    _atomic(store.folder(token) / "session.json", record)
    assert view_scope.conflict(record) is None
    assert "view_scope_conflict" not in {row["category"] for row in store.readiness(token)["issues"]}
    # A record with no view layer at all (a pre-segmenter session) keeps building as before.
    record = _record(store, token)
    record.pop("view_candidates", None)
    for row in record["options"]["profiles"] + record["options"]["circles"]:
        row.pop("view_id", None)
    _atomic(store.folder(token) / "session.json", record)
    assert "view_scope_conflict" not in {row["category"] for row in store.readiness(token)["issues"]}


def test_a_role_decision_from_an_older_geometry_asks_again(tmp_path):
    """§47/§49: the stamp is the server's; a reader migration (new geometry) invalidates the role —
    an old confirmation must not silently keep steering the build."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    record = _record(store, token)
    part_profile = next(row for row in record["options"]["profiles"] if row.get("view_id") == PART_VIEW)
    state = store.set_drawing_view(token, opened["revision"], PART_VIEW, "primary")
    state = store.save(token, state["revision"], decisions={**state["decisions"],
                                                           "profile_id": part_profile["id"]})
    assert "view_scope_conflict" not in {row["category"] for row in store.readiness(token)["issues"]}
    record = _record(store, token)
    # A reader migration moved the geometry on: the role's own stamp stayed on the old version.
    for row in record["decisions"]["drawing_views"]:
        row["geometry_version"] = 3
    _atomic(store.folder(token) / "session.json", record)
    conflict = next(row for row in store.readiness(token)["issues"]
                    if row["category"] == "view_scope_conflict")
    assert conflict["reason"] == "stale_view_decision"
    with pytest.raises(ValueError):
        guided.dispatch_plan(SimpleNamespace(record=_record(store, token),
                                             decisions=Decisions.model_validate(
                                                 _record(store, token)["decisions"])))
    # Re-confirming the role against the new geometry closes it (the command re-stamps).
    state = store.set_drawing_view(token, state["revision"], PART_VIEW, "primary")
    assert "view_scope_conflict" not in {row["category"] for row in store.readiness(token)["issues"]}


def test_a_client_cannot_forge_a_role_decision_through_save(tmp_path):
    """§47: the stamp is the server's — `/save` carries the stored rows, it never authors or edits one."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    state = store.set_drawing_view(token, opened["revision"], PART_VIEW, "primary")
    edited = [dict(row) for row in state["decisions"]["drawing_views"]]
    edited[0]["role"] = "unused"                       # an edit, not a command
    with pytest.raises(ValueError):
        store.save(token, state["revision"], decisions={**state["decisions"], "drawing_views": edited})
    invented = [{"view_id": PART_VIEW, "role": "primary", "geometry_version": 99}]
    with pytest.raises(ValueError):
        store.save(token, state["revision"], decisions={**state["decisions"], "drawing_views": invented})
    # The ordinary save path (every other decision) still passes the stored rows through unchanged.
    assert store.load(token)["decisions"]["drawing_views"][0]["role"] == "primary"
    store.save(token, state["revision"], decisions={**state["decisions"], "thickness": 12.0})


def test_readiness_names_the_view_scope_waiting_state_with_its_question(tmp_path):
    """The checklist and the build must tell the same story about the same conflict (§53)."""
    record = {"options": {"profiles": [{"id": "p1", "kind": "wire", "points": [[0, 0]], "view_id": "v2"}],
                          "circles": []},
              "decisions": {"profile_id": "p1",
                            "drawing_views": [{"view_id": "v1", "role": "primary", "geometry_version": 4}]},
              "view_candidates": [{"id": "v1", "kind": "front", "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}},
                                  {"id": "v2", "kind": "front", "bbox": {"x": 20, "y": 0, "w": 10, "h": 10}}],
              "geometry_version": 4}
    conflict = view_scope.conflict(record)
    assert conflict["reason"] == "cross_view" and conflict["view_id"] == "v2"
    assert view_scope.conflict_questions(record) == [conflict["detail"]]
    assert view_scope.category() == "view_scope_conflict"
