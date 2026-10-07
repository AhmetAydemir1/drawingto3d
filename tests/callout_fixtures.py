"""One synthetic session record, shared by the callout-chain test modules (G4/G5/G7/G8/GX).

Built here so every module tests the *same* record shape the store hands to the pure layers: page
frame, primitives, contours, candidates, the user's text, the real parse (`callout_parse`), and the
decisions a user could have made. Nothing in here touches the filesystem, a model, or a reference.
"""
import copy

from drawingto3d import callout_parse
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION, geometry_key

SOURCE = "d" * 64
TOKEN = "a" * 32
WIRE = [[20, 20], [120, 20], [120, 80], [20, 80]]
ARC = {"id": "a0", "center": [206.0, 36.0], "radius": 16.0, "start": [206.0, 20.0], "end": [222.0, 36.0]}


def circle(circle_id, center, *, mm: float = 0.0, radius=None, px_per_mm: float = 2.0):
    """A circle whose *drawn* size can match the printed text: Ø`mm` at the sheet's own scale (px)."""
    drawn = float(radius) if radius is not None else (float(mm) / 2.0) * px_per_mm
    return {"id": circle_id, "center": list(center), "radius": drawn}


def _primitives(circles, *, leader=None, arcs=()):
    rows = []
    for index, point in enumerate(WIRE):
        rows.append({"id": f"g{index}", "kind": "line", "start": list(point),
                     "end": list(WIRE[(index + 1) % 4])})
    for circle in circles:
        rows.append({"id": circle["id"], "kind": "circle", "center": list(circle["center"]),
                     "radius": circle["radius"]})
    if leader:
        rows.append({"id": "ld0", "kind": "line", "start": list(leader[0]), "end": list(leader[1])})
    for arc in arcs:
        rows.append({"id": arc["id"], "kind": "arc", "start": list(arc["start"]), "end": list(arc["end"]),
                     "center": list(arc["center"]), "radius": arc["radius"],
                     "start_degrees": 0.0, "end_degrees": 90.0})
    return rows


def record(text, region, *, circles=None, count=None, leader=None, arcs=(), claims=None,
           px_per_mm=2.0, stored_target=None, ignored=False, profile_id="outline_0",
           unbindable=False, manual_holes=(), manual_bindings=(), region_override=None,
           token=TOKEN, revision=1, sheet_unit: "str | None" = None, geometry_version=3, parses=None,
           source_sha256=SOURCE, candidates=True, callout_id="k1", second_text=None, calibration=True,
           sheet_frame=True, view=None):
    """One synthetic session record: geometry, one detected callout, its text and its real parse."""
    circles = circles if circles is not None else [{"id": "c0", "center": [45.0, 45.0], "radius": 6.0}]
    review = {"callout_id": callout_id, "ignored": bool(ignored), "revision": 1}
    if unbindable:
        review["unbindable"] = True
    if region_override:
        review["region_override"] = [float(value) for value in region_override]
    row = {
        "version": 1, "geometry_version": geometry_version, "token": token, "revision": revision,
        "source_sha256": source_sha256, "source": "/tmp/synthetic/source.pdf",
        "options": {
            "frame": {"width": 300, "height": 200},
            # The product's own frame, as `drawing_options` publishes it for a bordered sheet. The
            # compiler reads its tie axis through `view_transform` (R01), so the record has to carry
            # the same shape the store hands it — `sheet_frame=False` models a sheet without one.
            "sheet_frame": ({"found": True, "aligned": True, "rotation": 0,
                             "rect": [10.0, 10.0, 290.0, 190.0]} if sheet_frame else None),
            "circles": [{"id": c["id"], "center": list(c["center"]), "radius": c["radius"]}
                        for c in circles],
            "primitives": _primitives(circles, leader=leader, arcs=arcs),
            "profiles": [{"id": "outline_0", "kind": "wire", "points": [list(p) for p in WIRE],
                          "edges": [{"id": f"g{i}", "kind": "line", "start": list(WIRE[i]),
                                     "end": list(WIRE[(i + 1) % 4])} for i in range(4)]}],
            "measurements": [],
        },
        "callout_candidates": ([{"id": callout_id, "source_digest": SOURCE, "page_index": 0,
                                 "region": list(region), "crop_region": list(region),
                                 "source_kind": "vector_text", "observation_ids": [],
                                 "detector_version": "callout-detector/1",
                                 "geometry_version": geometry_version,
                                 "machine_text_hint": text}] if candidates else []),
        "callout_parses": [],
        "reading": {"claims": list(claims or [])},
        "sketch": ({} if px_per_mm is None else {"px_per_mm": px_per_mm}),
        "decisions": {"transcriptions": [{"callout_id": callout_id, "raw_text": text,
                                          "normalized_text": text, "entered_by": "user",
                                          "source_region": list(region), "revision": 1}],
                      "callout_targets": [], "callout_reviews": [review] if (ignored or unbindable
                                                                            or region_override) else [],
                      "holes": [dict(item) for item in manual_holes],
                      "bindings": [copy.deepcopy(dict(item)) for item in manual_bindings],
                      "profile_id": profile_id,
                      "calibration": ({"first": [20, 20], "second": [120, 20], "value": 50, "unit": "mm"}
                                      if calibration else None),
                      **({"view": view} if view is not None else {})},
        "history": [], "build": None, "log": [],
    }
    parse = callout_parse.semantic_parse(row["decisions"]["transcriptions"][0], sheet_unit=sheet_unit)
    row["callout_parses"] = list(parses) if parses is not None else [parse.model_dump(mode="json")]
    if second_text is not None:
        row["decisions"]["transcriptions"].append({"callout_id": "k2", "raw_text": second_text,
                                                   "normalized_text": second_text, "entered_by": "user",
                                                   "source_region": list(region), "revision": 1})
    assert count is None or parse.count == count
    if stored_target is not None:
        row["decisions"]["callout_targets"] = [{
            "callout_id": callout_id, "transcription_revision": 1,
            "parser_version": CALLOUT_PARSER_VERSION, "geometry_version": geometry_version,
            "target_kind": "circle", "target_ids": ["c0"],
            "evidence": [{"kind": "user_click", "ref": "c0"}], "status": "confirmed", "reconfirm": False,
            **stored_target}]
        row["decisions"]["callout_targets"][0]["geometry_key"] = geometry_key(row, row["decisions"])
    return row


def kinds(proposals):
    return [row.target_kind for row in proposals]
