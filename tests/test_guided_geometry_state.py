"""P01 acceptance (PLAN.md): a build must never rewrite the drawing the user loaded.

Everything here goes through the real `GuidedStore` path — create/save/build/undo/load — on a vector sheet,
because the mutation this guards against only shows up when the record that was built is read back.
"""
import copy
import json
import math
from pathlib import Path

import pytest

from drawingto3d.guided import Decisions, GuidedStore, make_plan, user_dimensions

PLATE_SHEET = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _dump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def geometry_of(plan) -> dict:
    """The numeric part of a plan — positions and sizes, without assumption prose or source labels."""
    params = plan if isinstance(plan, dict) else plan.model_dump()
    rows = params.get("parameters") or params
    return {key: round(float(row["value"]), 6) for key, row in rows.items()
            if isinstance(row, dict) and isinstance(row.get("value"), (int, float))
            and key.startswith(("edge_", "hole_", "outer"))}


def _inside_circles(options, wire):
    xs = [p[0] for p in wire["points"]]
    ys = [p[1] for p in wire["points"]]
    return [c for c in options["circles"]
            if min(xs) <= c["center"][0] <= max(xs) and min(ys) <= c["center"][1] <= max(ys)]


def decisions_for(options):
    """A complete, buildable decision set: the first offered wire, its own two ends as calibration, and one
    inside circle cut as a through hole (so the solved centre has a place to show in the plan)."""
    wire = next(p for p in options["profiles"] if p.get("kind") == "wire" and (p.get("points") or []))
    points = [p for edge in wire["edges"] for p in (edge["start"], edge["end"])]
    left = min(points, key=lambda p: p[0])
    right = max(points, key=lambda p: p[0])
    circles = sorted(_inside_circles(options, wire), key=lambda c: (c["center"][0], c["center"][1]))
    assert len(circles) >= 2, "bu paftada kesilebilir daire ikilisi yok"
    return wire, circles, {
        "calibration": {"first": list(left), "second": list(right), "value": 100.0, "unit": "mm",
                        "span_id": None},
        "profile_id": wire["id"], "thickness": 15.0, "trace_acknowledged": True, "bindings": [],
        "holes": [{"circle_id": circles[0]["id"], "kind": "through", "diameter": 6.8, "depth": None}],
    }


def _tie(first, second, value=120.0):
    """One decision with its own id and the user's confirmed axis/direction (PLAN §8.3/§8.4)."""
    axis = ("x" if abs(second["center"][0] - first["center"][0]) >= abs(second["center"][1] - first["center"][1])
            else "y")
    delta = (second["center"][0] - first["center"][0]) if axis == "x" else (first["center"][1] - second["center"][1])
    return {"id": "b0", "value": value, "unit": "mm", "span_id": None, "axis": axis,
            "direction": 1 if delta >= 0 else -1,
            "first": {"kind": "centre", "id": first["id"], "x": first["center"][0], "y": first["center"][1]},
            "second": {"kind": "centre", "id": second["id"], "x": second["center"][0], "y": second["center"][1]}}


def plan_of(store, token):
    return make_plan(store.load(token))


def _declare_callouts_out_of_scope(store, token):
    """G8 (`PLAN.md` §14): üretim, her callout için bir karar bekler.

    Bu testin konusu temel geometrinin yerinde kalması; paftanın metin bölgeleri de kapsam dışı
    bırakılır — sessizce düşürülmez, kullanıcı kararı olarak kayda geçer ve denetimde görünür.
    """
    for row in store.public(store.load(token))["callouts"]:
        store.edit_callout(token, store.load(token)["revision"], "set_ignored",
                           {"callout_id": row["id"], "ignored": True})


def test_measure_add_build_remove_build_undo_reopen_keeps_base_geometry(tmp_path):
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE_SHEET.read_bytes())
    token = opened["token"]
    base = _dump(store.load(token)["options"])

    wire, circles, decisions = decisions_for(opened["options"])
    revision = store.save(token, opened["revision"], decisions)["revision"]
    _declare_callouts_out_of_scope(store, token)          # G8: kapsam kararı olmadan üretim beklemede
    revision = store.load(token)["revision"]
    built = store.build(token, revision)
    assert built["build_status"] == "complete", built.get("error")
    folder = Path(store.load(token)["build"]["folder"])
    plan_a = geometry_of(json.loads((folder / "plan.json").read_text()))
    assert _dump(store.load(token)["options"]) == base, "build temel geometriyi degistirdi"

    # A second preparation with the same decisions must give the same geometry, and change nothing.
    again = store.load(token)
    assert geometry_of(plan_of(store, token)) == plan_a
    assert _dump(store.load(token)["options"]) == base

    # Add a measurement (the sheet's own two inside circles tied to 120 mm) -> build -> the tie is solved.
    decisions_b = {**decisions, "bindings": [_tie(circles[0], circles[1])]}
    revision_b = store.save(token, revision, decisions_b)["revision"]
    built_b = store.build(token, revision_b)
    assert built_b["build_status"] == "complete", built_b.get("error")
    folder_b = Path(store.load(token)["build"]["folder"])
    plan_b = geometry_of(json.loads((folder_b / "plan.json").read_text()))
    assert _dump(store.load(token)["options"]) == base, "olculu build temel geometriyi degistirdi"
    # PLAN P04-a: the scale is the calibration, so this tie may no longer show up as a *rescaled* plan (that
    # was the F12 defect). Its measured effect is the core's: the tied centre moves to the printed distance.
    # Carrying that solved centre into the cut/STEP is P04-f (PLAN item 10) and stays an open gap here.
    solving = copy.deepcopy(store.load(token)["options"])
    solving_profile = next(p for p in solving["profiles"] if p["id"] == decisions["profile_id"])
    calibration = decisions["calibration"]
    tie_scale = math.dist(calibration["first"], calibration["second"]) / calibration["value"]
    solving_points = solving_profile["points"]
    report = user_dimensions(solving_profile, solving, Decisions.model_validate(decisions_b), tie_scale,
                             [min(p[0] for p in solving_points), max(p[1] for p in solving_points)])
    assert report is not None and report["status"] == "underconstrained", report
    moved = report["centres"][circles[1]["id"]]
    span_px = abs(moved[1] - report["centres"][circles[0]["id"]][1])
    assert span_px / tie_scale == pytest.approx(120.0, abs=1e-6), report["centres"]
    # ...while the plan itself stays exactly what the untied build produced: no silent rescaling (F12).
    assert plan_b == plan_a, "bag olcegi (ve dolayisiyla plani) degistirdi"

    # Remove the measurement -> build -> the original geometry comes back, and no solve report is left over.
    revision_c = store.save(token, revision_b, decisions)["revision"]
    built_c = store.build(token, revision_c)
    assert built_c["build_status"] == "complete", built_c.get("error")
    folder_c = Path(store.load(token)["build"]["folder"])
    plan_c = geometry_of(json.loads((folder_c / "plan.json").read_text()))
    assert plan_c == plan_a, "olcu kaldirilinca ozgun geometri donmedi"
    record = store.load(token)
    assert _dump(record["options"]) == base
    assert not any("solved_dimensions" in profile for profile in record["options"]["profiles"])

    # Undo the removal: the previous revision (binding present) is back, geometry included.
    undone = store.save(token, revision_c, undo=True)
    plan_undone = geometry_of(plan_of(store, token))
    assert plan_undone == plan_b, "geri alma onceki revizyonun geometrisini getirmedi"
    built_undone = store.build(token, undone["revision"])
    assert built_undone["build_status"] == "complete", built_undone.get("error")
    folder_undone = Path(store.load(token)["build"]["folder"])
    assert geometry_of(json.loads((folder_undone / "plan.json").read_text())) == plan_b
    assert _dump(store.load(token)["options"]) == base

    # Reopen the store (fresh instance, same folder): the same revision gives the same geometry.
    reopened = GuidedStore(tmp_path / "store")
    assert geometry_of(plan_of(reopened, token)) == plan_b
    assert _dump(reopened.load(token)["options"]) == base
