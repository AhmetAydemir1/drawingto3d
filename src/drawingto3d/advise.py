"""The reading's own claims, offered to the guided flow as suggestions with their evidence.

PLAN section 24-A. The guided flow asks the user for seventeen fields on the plate sheet; the reading
(`observe` -> `bind` -> `meaning` -> `proposal.read_sheet`) already answers eight of them, and two more
are printed numbers whose *identity* nothing settles. This module turns those answers into proposals.

What a proposal is, and is not:

* A proposal is a candidate with evidence (the span id, its printed text, the geometry ids it names,
  the measured length in px and the sheet's own scale). It becomes a decision only when the user
  accepts it, and it is recorded as the user's value — `general.py` keeps model and rule guesses out of
  the parameter sources, and this module does not invent a new one.
* Nothing here writes to the session. `guided.GuidedStore` stores the proposals beside the decisions and
  logs both, so "the reading suggested X, the user accepted Y" stays readable afterwards.
* An anchor is resolved by geometry id and a length constraint, never by assuming a coordinate
  transform between the reading's millimetres and the flow's pixels...

Two claims stay open by design, and are offered as a ranked choice among the sheet's own printed
numbers rather than as a value to type: which printed distance is the **thickness** (a distance whose
two anchors are ends of one axis-aligned edge outside the outline, shorter than the outline) and which
is a **pocket depth** (a remaining distance between line ends). On the plate these are 15,00 and 8,00 —
both printed, neither identified by any rule the sheet states. The user picks in one tap, and a model
(`§24-C`) is the fallback for the choices a rule cannot rank.
"""

from __future__ import annotations

import math
from pathlib import Path

from drawingto3d import proposal

PROPOSAL_VERSION = "guided-proposal-v1"
ALIGNED_TOLERANCE_PX = 1.0
LENGTH_TOLERANCE = 0.01
# A row resolved in the reading's frame counts as an x/y distance only when it is drawn along that
# axis: the across-axis part may not exceed half the span. A diagonal whose span merely equals the
# printed length is a coincidence, not a measurement (`5/Plate With A Pocket Drawing`'s 8 mm depth
# row: 275 px across a 63 px y span), and reading it as an axis row moved it out of the depth bucket.
AXIS_CROSS_MAX = 0.5
# A hole stands on a flange face when it lies inside the face's outer circle; the margin absorbs the
# drawing's own line width, and keeps a hole of a neighbouring view (drawn just outside this face) out.
HOLE_MARGIN_PX = 2.0
# How far a row's own ends may sit from the reading's fitted scale and still be offered as the flow's
# calibration anchor. Measured agreement on four sheets: 0.42-0.71 % for the ordinary rows. A short
# rim-to-rim row is fuzzy by half a pixel — the flange sheet's 10 mm row measured 2.99 % while its arc
# rims were walked the wrong way round and 0.58 % once the reading's own frame resolved it.
CALIBRATION_AGREEMENT = 0.02


def reading_record(drawing: str | Path) -> dict:
    """One sheet's reading as plain data, or the reason it refused. A refusal is a result."""
    try:
        sheet = proposal.read_sheet(Path(drawing))
    except ValueError as exc:
        return {"version": PROPOSAL_VERSION, "refused": str(exc), "printed": [], "claims": []}
    return {"version": PROPOSAL_VERSION, "px_per_mm": sheet.sheet_px_per_mm, "printed": sheet.printed,
            "claims": sheet.claims, "outline_mm": sheet.outline_mm, "circles_mm": sheet.circles_mm,
            "notes": sheet.notes, "refusals": sheet.refusals}


def _printed(reading: dict, span_id: str) -> dict:
    for row in reading.get("printed", []):
        if row.get("span_id") == span_id:
            return row
    return {}


def _geometry_points(options: dict) -> dict[str, dict]:
    """Every named geometry of the flow's own candidate set, with the px points it offers."""
    table: dict[str, dict] = {}
    for circle in options["circles"]:
        table[circle["id"]] = {"kind": "circle", "centre": circle["center"], "radius": circle["radius"],
                               "centre_points": [circle["center"]]}
    primitives = options.get("primitives")
    if primitives:
        for row in primitives:
            if row.get("kind") == "circle":
                continue
            entry = table.setdefault(row["id"], {"kind": row["kind"], "ends": []})
            entry["ends"] = [list(row["start"]), list(row["end"])]
            if row.get("center"):
                entry.update({"centre": row["center"], "radius": row["radius"]})
                entry.setdefault("centre_points", []).append(row["center"])
        return table
    # A session stored before `primitives` existed: what a closed loop holds is what can be resolved.
    for profile in options["profiles"]:
        for edge in profile.get("edges", []):
            row = table.setdefault(edge["id"], {"kind": edge["kind"], "ends": []})
            row.setdefault("ends", []).extend([edge["start"], edge["end"]])
            if edge["kind"] == "arc":
                row.update({"centre": edge["center"], "radius": edge["radius"]})
                row.setdefault("centre_points", []).append(edge["center"])
    return table


def anchor_candidates(anchor: dict, table: dict) -> list[list[float]]:
    """Every px point the named geometry offers for this anchor kind. The length decides afterwards."""
    geometry = table.get(anchor.get("geometry_id", ""))
    if geometry is None:
        return []
    kind = anchor.get("kind", "")
    if kind in ("circle-centre", "arc-centre") and geometry.get("centre"):
        return [list(geometry["centre"])]
    if geometry.get("kind") == "circle":
        centre, radius = geometry["centre"], geometry["radius"]
        return [[centre[0] - radius, centre[1]], [centre[0] + radius, centre[1]],
                [centre[0], centre[1] - radius], [centre[0], centre[1] + radius]]
    points = [list(end) for end in geometry.get("ends", [])]
    if geometry.get("kind") == "arc" and geometry.get("centre"):
        # A dimension can touch an arc's rim at its extreme, not only at an end.
        centre, radius = geometry["centre"], geometry["radius"]
        points.extend([[centre[0] - radius, centre[1]], [centre[0] + radius, centre[1]],
                       [centre[0], centre[1] - radius], [centre[0], centre[1] + radius]])
    return points


def _measurement_id(options: dict, value: float) -> str | None:
    """The flow's own menu row for this printed value, so a saved calibration can name its source.

    The reading's span ids (`pdf-3`) and the flow's measurement ids (`t4`) are two namespaces over the
    same printed number; `validate_decisions` checks the flow's one, and the evidence keeps both.
    """
    rows = [row for row in options.get("measurements", [])
            if row.get("value") is not None and abs(float(row["value"]) - value) <= max(0.005, 0.002 * value)]
    return rows[0]["id"] if len(rows) == 1 else None


def _transform(reading: dict, options: dict) -> tuple[list[float], float] | None:
    """The reading's own frame: millimetres relative to the outline's bbox centre, at the sheet's scale.

    `proposal.py` measures every anchor this way and the flow's pixels are the same 200 dpi render, so
    one centre and one scale take a reading point back to a pixel point. The match is verified per
    anchor (`_on_geometry`) instead of trusted: a proposal whose point is not on the geometry it names
    is dropped.
    """
    outline = _profile_for_outline(reading, options)
    if not outline or not reading.get("px_per_mm"):
        return None
    points = outline[0]["points"]
    centre = [(min(p[0] for p in points) + max(p[0] for p in points)) / 2,
              (min(p[1] for p in points) + max(p[1] for p in points)) / 2]
    return centre, reading["px_per_mm"]


def _on_geometry(point: list[float], geometry_id: str, table: dict, tolerance: float = 3.0) -> bool:
    geometry = table.get(geometry_id)
    if geometry is None:
        return False
    if geometry.get("kind") == "circle":
        centre = geometry["centre"]
        return math.dist(point, centre) <= tolerance or abs(math.dist(point, centre) - geometry["radius"]) <= tolerance
    if geometry.get("kind") == "arc":
        centre = geometry["centre"]
        return abs(math.dist(point, centre) - geometry["radius"]) <= tolerance
    ends = geometry.get("ends") or []
    for index in range(len(ends) - 1):
        start, end = ends[index], ends[index + 1]
        span = math.dist(start, end) or 1.0
        along = max(0.0, min(1.0, ((point[0] - start[0]) * (end[0] - start[0])
                                   + (point[1] - start[1]) * (end[1] - start[1])) / span ** 2))
        foot = [start[0] + along * (end[0] - start[0]), start[1] + along * (end[1] - start[1])]
        if math.dist(point, foot) <= tolerance:
            return True
    return bool(ends) and math.dist(point, ends[0]) <= tolerance


def resolve_claim(claim: dict, table: dict, px_per_mm: float | None, transform=None) -> dict | None:
    """A distance claim's two anchors as px points, or None when the geometry does not settle it.

    The reading's own points are used when its frame is known and both anchors land on the geometry
    they name; otherwise both anchors are searched among the points their geometry offers and a pair
    is accepted when the distance, the x span or the y span equals the printed length at the sheet's
    scale (a dimension row measures along its own axis). A pair that cannot match is dropped rather
    than guessed: a proposal that is wrong is worse than a question.
    """
    anchors = claim.get("anchors", [])
    if claim.get("form") != "distance" or len(anchors) != 2 or not px_per_mm:
        return None
    if transform:
        centre, scale = transform
        mapped = [[centre[0] + anchor["point_mm"][0] * scale, centre[1] + anchor["point_mm"][1] * scale]
                  for anchor in anchors]
        if all(_on_geometry(point, anchor.get("geometry_id", ""), table) for point, anchor in zip(mapped, anchors)):
            # The same axis decision the search below makes: a row resolved in the reading's frame is an
            # x/y distance when one of its spans holds the printed length and it is drawn along that
            # axis — its two mapped ends may sit a couple of pixels across (a section view's extension
            # lines are not always plumb), but a diagonal's span match is a coincidence; `distance`
            # wins when the straight line fits best.
            length = float(claim.get("printed_mm", 0.0)) * px_per_mm
            tolerance = max(2.0, LENGTH_TOLERANCE * length)
            width = abs(mapped[0][0] - mapped[1][0])
            height = abs(mapped[0][1] - mapped[1][1])
            straight = math.dist(mapped[0], mapped[1])
            best = None
            for mode, measured, across in (("distance", straight, 0.0), ("x", width, height),
                                           ("y", height, width)):
                if mode != "distance" and across > AXIS_CROSS_MAX * measured:
                    continue
                error = abs(measured - length)
                if error <= tolerance and (best is None or error < best["error_px"]):
                    best = {"error_px": error, "mode": mode, "points": mapped, "from": "reading"}
            if best is None:
                return {"mode": "projected", "error_px": round(abs(straight - length), 2),
                        "points": mapped, "from": "reading"}
            return {**best, "error_px": round(best["error_px"], 2)}
    length_px = float(claim.get("printed_mm", 0.0)) * px_per_mm
    tolerance = max(2.0, LENGTH_TOLERANCE * length_px)
    left, right = anchor_candidates(anchors[0], table), anchor_candidates(anchors[1], table)
    best = None
    for first in left:
        for second in right:
            if math.dist(first, second) < 1.0:
                continue
            for mode, measured in (("distance", math.dist(first, second)),
                                   ("x", abs(first[0] - second[0])), ("y", abs(first[1] - second[1]))):
                error = abs(measured - length_px)
                if error <= tolerance and (best is None or error < best["error_px"]):
                    best = {"error_px": error, "mode": mode, "points": [list(first), list(second)], "from": "search"}
    return best


def _profile_for_outline(reading: dict, options: dict) -> tuple[dict, dict] | None:
    """The traced contour that measures out like the reading's own outline, with the sizes as evidence."""
    outline = reading.get("outline_mm")
    px_per_mm = reading.get("px_per_mm")
    if not outline or not px_per_mm:
        return None
    best = None
    for profile in options["profiles"]:
        points = profile.get("points") or []
        if profile.get("kind") != "wire" or len(points) < 3:
            continue
        width = (max(p[0] for p in points) - min(p[0] for p in points)) / px_per_mm
        height = (max(p[1] for p in points) - min(p[1] for p in points)) / px_per_mm
        if abs(width - outline["width_mm"]) > 0.02 * outline["width_mm"]:
            continue
        if abs(height - outline["height_mm"]) > 0.02 * outline["height_mm"]:
            continue
        score = abs(width - outline["width_mm"]) + abs(height - outline["height_mm"])
        if best is None or score < best[0]:
            best = (score, profile, {"width_mm": round(width, 2), "height_mm": round(height, 2),
                                     "outline_mm": [outline["width_mm"], outline["height_mm"]]})
    return None if best is None else (best[1], best[2])


def _hole_proposals(reading: dict, options: dict, depth_choice: dict | None) -> list[dict]:
    """A diameter claim's own circles become holes. `THRU` states the kind; without it, the rule below."""
    circle_ids = {circle["id"] for circle in options["circles"]}
    claims = [claim for claim in reading.get("claims", [])
              if claim.get("form") == "diameter" and claim.get("resolution") == "confirmed"]
    plain = [claim for claim in claims if "THRU" not in str(_printed(reading, claim.get("span_id", "")).get("text", "")).upper()]
    largest = max((float(claim["printed_mm"]) for claim in plain), default=0.0)
    proposed: dict[str, dict] = {}
    for claim in claims:
        text = str(_printed(reading, claim.get("span_id", "")).get("text", ""))
        through = "THRU" in text.upper()
        for circle_id in claim.get("matched_geometry", []):
            if circle_id not in circle_ids or circle_id in proposed:
                continue
            if through:
                kind, confidence = "through", "bound"
                note = "metin THRU diyor"
            elif depth_choice and abs(float(claim["printed_mm"]) - largest) < 1e-9:
                kind, confidence = "pocket", "rule"
                note = (f"THRU yazmıyor ve çizimde cep derinliği adayı var ({depth_choice['text']}); "
                        "en büyük THRU'suz çap cep sayıldı")
            else:
                kind, confidence = "through", "assumed"
                note = "THRU yazmıyor; geçişli önerildi, onay gerekir"
            proposed[circle_id] = {"field": f"hole:{circle_id}", "value": {"circle_id": circle_id, "kind": kind,
                                                                         "diameter": float(claim["printed_mm"])},
                                   "confidence": confidence,
                                   "evidence": {"span_id": claim.get("span_id"), "text": text,
                                                "printed_mm": claim.get("printed_mm"),
                                                "drawn_mm": claim.get("drawn_mm"),
                                                "anchor_mode": claim.get("anchor_mode"),
                                                "matched_geometry": claim.get("matched_geometry", []),
                                                "kind_source": note}}
    return list(proposed.values())


def proposals(options: dict, reading: dict, archetype: dict | None = None) -> list[dict]:
    """Every decision the sheet's own reading can put in front of the user, with its evidence.

    Plate-shaped decisions — an outer contour, holes cut into it, a thickness — are only offered when the
    sheet's own geometry supports a flat part (`proposal.part_class`). On a sheet whose circles form a
    flange stack the flow offers the calibration alone and says which class it read, rather than cutting
    a 27-hole plate out of an elbow.
    """
    items: list[dict] = []
    if reading.get("refused"):
        return items
    flat = archetype is None or archetype.get("class") == "flat-part"
    table = _geometry_points(options)
    px_per_mm = reading.get("px_per_mm")
    transform = _transform(reading, options)
    outline = _profile_for_outline(reading, options) if flat else None
    if outline:
        profile, evidence = outline
        items.append({"field": "profile_id", "value": profile["id"], "confidence": "bound",
                      "evidence": {**evidence, "geometry_ids": profile.get("geometry_ids", []),
                                   "join_max_px": profile.get("join_max_px")}})
    points, spans = {}, []
    for claim in reading.get("claims", []):
        resolved = resolve_claim(claim, table, px_per_mm, transform)
        if resolved:
            points[claim["span_id"]] = resolved
            if resolved["mode"] == "distance":
                # The flow's calibration measures the straight line between the two clicked points, so
                # only a row whose *distance* equals the printed value can be offered as a span.
                spans.append(claim)
    if spans:
        # The flow's calibration must not contradict the reading's own fitted scale: a sheet drawn at
        # 1:5 rounds every row, and a row whose *own* ends resolve 3 % away from the consensus (a
        # 10 mm row resolved 0.5 px short between two arc rims) would hand the build a wrong scale for
        # the whole part. Measured: the plate's rows agree within 0.58-0.71 %, the plastic's within
        # 0.53 %, `Drawing.pdf` within 0.42 % — all offered as before. `10/Exercise 12`'s single row
        # came back 0.5 px short while its rim ends were still walked the wrong way round (2.99 %); in
        # the reading's own frame it resolves 0.58 % off and is offered — and the flange's own printed
        # Ø270, appended after it, is the calibration the accept binds.
        def agreement(row: dict) -> float:
            if not px_per_mm:
                return 0.0
            measured = math.dist(*points[row["span_id"]]["points"])
            return abs(measured / float(row["printed_mm"]) / px_per_mm - 1.0) if row.get("printed_mm") else 1.0

        agreed = [row for row in spans if agreement(row) <= CALIBRATION_AGREEMENT]
        if agreed:
            claim = max(agreed, key=lambda row: float(row.get("printed_mm", 0.0)))
            row = _printed(reading, claim["span_id"])
            resolved = points[claim["span_id"]]
            first, second = resolved["points"]
            measurement = _measurement_id(options, float(claim["printed_mm"]))
            items.append({"field": "calibration",
                          "value": {"first": first, "second": second, "value": float(claim["printed_mm"]),
                                    "unit": "mm", "span_id": measurement},
                          "confidence": "bound",
                          "evidence": {"span_id": claim["span_id"], "text": row.get("text", ""),
                                       "measured_mm": claim.get("printed_mm"), "drawn_mm": claim.get("drawn_mm"),
                                       "menu_id": measurement, "px": round(math.dist(first, second), 2),
                                       "px_per_mm": px_per_mm, "axis": resolved["mode"],
                                       "error_px": round(resolved["error_px"], 2),
                                       "resolved_from": resolved.get("from"),
                                       "anchor_geometry_ids": [anchor.get("geometry_id") for anchor in claim.get("anchors", [])]}})
    box = None
    if outline:
        point_list = outline[0]["points"]
        box = (min(p[0] for p in point_list), min(p[1] for p in point_list),
               max(p[0] for p in point_list), max(p[1] for p in point_list))
    if flat:
        thickness = depth = None
        if box and px_per_mm:
            thickness, depth = _identity_candidates(reading, options, points, box)
        items.extend(_hole_proposals(reading, options, depth))
        used = {item["evidence"]["span_id"] for item in items if item["evidence"].get("span_id")}
        if box and px_per_mm:
            # The alternatives for an identity are the sheet's other distances drawn outside the outline —
            # the same kind of row as the chosen one, not every number on the page.
            other = [{"span_id": claim["span_id"], "value": float(claim["printed_mm"]),
                      "text": _printed(reading, claim["span_id"]).get("text", "")}
                     for claim in reading.get("claims", [])
                     if claim.get("span_id") not in used and claim.get("form") == "distance"
                     and claim.get("resolution") == "confirmed"
                     and claim.get("span_id") in points
                     and all(_outside_profile(point, box) for point in points[claim["span_id"]]["points"])]
            if thickness:
                items.append({"field": "thickness", "value": thickness["value"], "confidence": "rule",
                              "alternatives": [row for row in other if abs(row["value"] - thickness["value"]) > 1e-9],
                              "evidence": {"rule": "kontur dışında, eksene hizalı, iki ucu da çizgi ucu; "
                                                   "konturun en küçük kenarından kısa",
                                           **{key: thickness[key] for key in ("span_id", "text", "drawn_mm", "anchors")}}})
                used.add(thickness["span_id"])
            if depth:
                items.append({"field": "depth", "value": depth["value"], "confidence": "rule",
                              "alternatives": [row for row in other if abs(row["value"] - depth["value"]) > 1e-9],
                              "evidence": {"rule": "kontur dışında, eksene hizalı olmayan çizgi ucu uzaklığı; kalınlıktan küçük",
                                           **{key: depth[key] for key in ("span_id", "text", "drawn_mm", "anchors")}}})
    else:
        # A rotational sheet has no contour to trace: its own circles carry the decisions (see
        # `_flange_proposals`). Only a class we could not read gets nothing but the calibration.
        _flange_proposals(reading, options, archetype or {}, points, items)
    return items


def _diameter_claim(reading: dict, circle_id: str) -> dict:
    """The printed diameter whose reading matched this circle — the sheet's own number for it.

    A circle can be reached by more than one callout (a through hole's two ends, a diameter printed on a
    section and on a face view); the largest printed value wins, since an inner bore is never larger than
    the outside it sits in.
    """
    best: dict = {}
    for claim in reading.get("claims", []):
        if claim.get("form") != "diameter" or circle_id not in claim.get("matched_geometry", []):
            continue
        if claim.get("resolution") != "confirmed":
            continue
        if not best or float(claim.get("printed_mm", 0.0)) > float(best.get("printed_mm", 0.0)):
            best = claim
    if not best:
        return {}
    row = _printed(reading, best.get("span_id", ""))
    return {"span_id": best.get("span_id"), "text": row.get("text", ""),
            "printed_mm": float(best["printed_mm"]), "drawn_mm": best.get("drawn_mm"),
            "anchor_mode": best.get("anchor_mode"), "matched_geometry": best.get("matched_geometry", [])}


def _flange_proposals(reading: dict, options: dict, archetype: dict, points: dict[str, dict],
                      items: list[dict]) -> None:
    """The decisions a flange face supports — its own circle as the outer size, its bore, its holes.

    A rotational part seen face-on has no contour to trace: the outer size is the stack's biggest circle
    and the bore is the smallest one, both carrying the sheet's own printed diameter. Holes are the circles
    that stand *on that face* whose printed diameter the reading matched; nothing here assumes a bolt
    circle, because the reference part's holes sit in rows (88 mm apart) rather than on one pitch circle,
    so every circle keeps its own measured centre and only the printed diameter is taken as the decision.

    Measured on `10/Exercise 12` (flanged 90° elbow, reference `Exercise 12.STEP`): the stack at
    (347.0, 379.7) px reads Ø274.31/160.55/142.25/93.50/77.17 mm against the printed Ø270/158/140/92/76,
    its biggest circle covers 0.193 of the page width, and the printed Ø18's own circles stand on the face.
    """
    evidence = archetype.get("evidence") or {}
    circles = {circle["id"]: circle for circle in options["circles"]}
    stack_ids = [gid for gid in evidence.get("geometry_ids", []) if gid in circles]
    if not stack_ids:
        return
    px_per_mm = reading.get("px_per_mm")
    outer_id = max(stack_ids, key=lambda gid: circles[gid]["radius"])
    outer = circles[outer_id]
    profile = next((row for row in options["profiles"] if row["id"] == f"circle_{outer_id}"), None)
    if profile is None:
        return
    centre = outer["center"]
    measured = round(2.0 * outer["radius"] / px_per_mm, 2) if px_per_mm else None
    printed = _diameter_claim(reading, outer_id)
    items.append({"field": "profile_id", "value": profile["id"], "confidence": "bound",
                  "evidence": {"rule": "eş merkezli çap yığınının en büyük dairesi; flanş yüzünün dış kenarı",
                               "stack_centre_px": [round(float(v), 2) for v in centre],
                               "measured_mm": measured, "geometry_ids": sorted(stack_ids),
                               "stack_circles": len(stack_ids), "join_max_px": 0, **printed}})
    box = (centre[0] - outer["radius"], centre[1] - outer["radius"],
           centre[0] + outer["radius"], centre[1] + outer["radius"])
    if px_per_mm:
        thickness, _depth = _identity_candidates(reading, options, points, box)
        if thickness:
            items.append({"field": "thickness", "value": thickness["value"], "confidence": "rule",
                          "alternatives": thickness.get("alternatives", []),
                          "evidence": {"rule": "flanş yüzünün dışında, eksene hizalı, iki ucu da çizgi ucu",
                                       "rows": thickness.get("rows"),
                                       **{key: thickness[key]
                                          for key in ("span_id", "text", "drawn_mm", "anchors")}}})
    if printed and px_per_mm:
        # The flange's own printed diameter is the sheet's best anchor: the two points are the face
        # circle's own rim, the value is the number the sheet prints on it, and the resulting scale is
        # the one the part was drawn at (on `10/Exercise 12`: Ø270 over 425.2 px = 1.5748 px/mm, against
        # the consensus fit's 1.550 — the 1.6 % that would otherwise land on every size in the build).
        radius = float(outer["radius"])
        first = [float(centre[0] - radius), float(centre[1])]
        second = [float(centre[0] + radius), float(centre[1])]
        implied = 2.0 * radius / float(printed["printed_mm"])
        items.append({"field": "calibration",
                      "value": {"first": first, "second": second, "value": float(printed["printed_mm"]),
                                "unit": "mm", "span_id": _measurement_id(options, float(printed["printed_mm"]))},
                      "confidence": "bound",
                      "evidence": {"rule": "flanş yüzünün kendi çevresi: çizili çap ÷ basılı çap",
                                   **{key: printed[key] for key in ("span_id", "text", "drawn_mm")},
                                   "px": round(2.0 * radius, 2), "px_per_mm": round(implied, 4),
                                   "fitted_px_per_mm": px_per_mm,
                                   "error_px": round(abs(2.0 * radius - float(printed["printed_mm"]) * px_per_mm), 2),
                                   "circle_id": outer_id}})
    inner_id = min(stack_ids, key=lambda gid: circles[gid]["radius"])
    if inner_id != outer_id:
        inner = circles[inner_id]
        inner_printed = _diameter_claim(reading, inner_id)
        items.append({"field": f"hole:{inner_id}",
                      "value": {"circle_id": inner_id, "kind": "through",
                                "diameter": inner_printed.get("printed_mm")
                                if inner_printed else round(2.0 * inner["radius"] / px_per_mm, 2)},
                      "confidence": "rule",
                      "evidence": {"rule": "yığının en küçük dairesi; flanşın kendi deliği",
                                   "centre_px": [round(float(v), 2) for v in inner["center"]],
                                   "drawn_mm": round(2.0 * inner["radius"] / px_per_mm, 2),
                                   "stack_ids": sorted(stack_ids),
                                   "not_decided": [gid for gid in sorted(stack_ids, key=lambda gid: circles[gid]["radius"])
                                                   if gid not in (outer_id, inner_id)],
                                   **inner_printed}})
    for item in _hole_proposals(reading, options, None):
        circle_id = item["value"]["circle_id"]
        row = circles.get(circle_id)
        if row is None or circle_id in stack_ids:
            # The stack's own circles are the flange's sizes (and its bore), not holes cut into it.
            continue
        if math.dist(row["center"], centre) - float(row["radius"]) > outer["radius"] + HOLE_MARGIN_PX:
            continue      # a circle of another view: it does not stand on this face
        item["evidence"]["rule"] = "yüzün üstünde duran, basılı çapı okunmuş daire"
        item["evidence"]["face_centre_px"] = [round(float(v), 2) for v in centre]
        items.append(item)


def _outside_profile(point: list[float], box: tuple[float, float, float, float], margin: float = 2.0) -> bool:
    left, top, right, bottom = box
    return not (left - margin <= point[0] <= right + margin and top - margin <= point[1] <= bottom + margin)


def _identity_candidates(reading: dict, options: dict, points: dict[str, dict], box) -> tuple[dict | None, dict | None]:
    """Which printed distance is the thickness, which is a pocket depth — by shape, not by guessing.

    A row is "aligned" when it is drawn along an axis; the tolerance is half a millimetre rather than a
    pixel, because a sheet drawn at 1:5 has 0.65 mm in one pixel and a vertical thickness row is not
    always drawn perfectly vertical. When several aligned rows carry the *same* printed value they are one
    candidate, not an ambiguity: three rows printing 20.00 measure one thickness.
    """
    px_per_mm = reading.get("px_per_mm") or 1.0
    aligned_tolerance = max(ALIGNED_TOLERANCE_PX, 0.5 * float(px_per_mm))
    thickness, depth = [], []
    for claim in reading.get("claims", []):
        span_id = claim.get("span_id", "")
        resolved = points.get(span_id)
        if claim.get("form") != "distance" or claim.get("resolution") != "confirmed" or not resolved:
            continue
        anchors = claim.get("anchors", [])
        if anchors and not all(anchor.get("kind") == "line-end" for anchor in anchors):
            continue
        first, second = resolved["points"]
        if all(_outside_profile(point, box) for point in (first, second)):
            # The reading already decided which projection matched the printed value: a row resolved on
            # `x` or `y` is an axis distance even when its two ends are a couple of pixels apart across
            # the axis (a section view's extension lines are not always perfectly plumb).
            aligned = (resolved["mode"] in ("x", "y")
                       or abs(first[0] - second[0]) <= aligned_tolerance
                       or abs(first[1] - second[1]) <= aligned_tolerance)
            row = {"span_id": span_id, "value": float(claim["printed_mm"]), "anchors": resolved["points"],
                   "text": _printed(reading, span_id).get("text", ""), "drawn_mm": claim.get("drawn_mm"),
                   "axis": resolved["mode"], "error_px": round(resolved["error_px"], 2), "aligned_px": aligned}
            (thickness if aligned else depth).append(row)
    chosen = _agreed(thickness)
    depth_choice = _agreed(depth)
    if chosen and depth_choice and depth_choice["value"] >= chosen["value"]:
        depth_choice = None
    return chosen, depth_choice


def _agreed(rows: list[dict]) -> dict | None:
    """One candidate from rows of the same shape: the single row, the rows printing one value, or the value
    the sheet prints more than once — a flange's thickness is dimensioned on both its faces, a bore step
    once, so the repeated value is the part's size and the odd one out is a local step."""
    if not rows:
        return None
    counts: dict[float, list[dict]] = {}
    for row in rows:
        counts.setdefault(round(row["value"], 3), []).append(row)
    if len(counts) == 1:
        picked = rows
    else:
        best = max(counts.values(), key=len)
        if len(best) < 2 or len(best) == len(rows):
            return None
        picked = best
    first = picked[0]
    if len(picked) > 1:
        first = {**first, "rows": [row["span_id"] for row in picked],
                 "alternatives": [{"span_id": row["span_id"], "value": row["value"], "text": row["text"]}
                                  for row in rows if row["span_id"] not in {r["span_id"] for r in picked}]}
    return first
