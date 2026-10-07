"""G7 — confirmed callout → existing guided decisions compiler (kök `PLAN.md` §13).

```text
current transcription + current SemanticParse + current confirmed target
→ existing guided Decisions / constraints
```

No new CAD engine, no model, no reference STEP, no OCR: this reads the session record and returns
*candidate* decision rows (`Hole` / `Binding` shapes), the reasons a callout could not be compiled,
the conflicts with the user's own manual decisions, and one audit row per callout. It is pure —
nothing is written, no confirmation is created, and a compiled row reaches a build only through
`apply_compiled`, which never overwrites a manual decision.

Unsupported semantics stay explicit (`READ success` + `BIND success` + `CAD unsupported`): a
diameter whose text does not say THRU/BLIND does not become a hole, a radius with a confirmed arc
does not become a fillet, and a two-end tie that is not axis-aligned has no axis to bind. A tie's
axis and direction are read in the *sheet's own* frame — the same `view_transform` the build
refuses without (PLAN §8.6) — never off the raw page delta, whose y grows downwards.
"""
from __future__ import annotations

import copy

from drawingto3d.callout_models import (CALLOUT_PARSER_VERSION, callout_state, effective_callouts,
                                        geometry_key, sheet_unit)

INCH_MM = 25.4
AXIS_TOLERANCE_PX = 0.5      # both ends have to move on one axis for an axis tie to exist
MM_LIMIT = 1e6               # `guided.Hole`'s own mm bound (gt=0, le=1e6): a converted value must fit it


def _decisions(record: dict) -> dict:
    return record.get("decisions") or {}


def _parse_row(record: dict, callout_id: str, revision, parser_version) -> dict | None:
    """The parse row this callout's text is standing on — the only one a compile may read."""
    for row in record.get("callout_parses") or []:
        if (row.get("callout_id") == callout_id and row.get("transcription_revision") == revision
                and row.get("parser_version") == parser_version):
            return row
    return None


def _unit_factor(parse: dict, declared: str | None) -> tuple[float, str] | None:
    """Millimetres per reported unit and where the unit came from — never assumed (PLAN §9).

    A printed unit wins; otherwise the unit the user declared for the sheet resolves it and the
    provenance says so (`sheet`). With neither, nothing resolves (`missing_unit`).
    """
    unit = parse.get("unit")
    if unit in ("mm", "in"):
        return (INCH_MM if unit == "in" else 1.0), "printed"
    if declared in ("mm", "in"):
        return (INCH_MM if declared == "in" else 1.0), "sheet"
    return None


def _size_mm(parse: dict, declared: str | None) -> tuple[float | None, str | None]:
    """The reported size in millimetres and where its unit came from — never assumed."""
    size = parse.get("size")
    resolved = _unit_factor(parse, declared)
    if size is None or resolved is None:
        return None, None
    return float(size) * resolved[0], resolved[1]


def _view_axes(record: dict) -> tuple[dict | None, str]:
    """The sheet's own axes as the build reads them, or the reason there are none (PLAN §8.6).

    `make_plan` is the authority the build refuses without; sharing its resolver keeps a compiled
    tie on exactly the axes the solver will read. A record whose view is malformed, or one with no
    vouchable view at all, comes back as a reason — the caller turns that into an open decision
    instead of guessing. Pure by construction: nothing is written, nothing is confirmed.
    """
    from drawingto3d import guided
    try:
        decisions = guided.Decisions.model_validate(_decisions(record))
        axes = guided.view_transform(decisions, record.get("options") or {})
    except ValueError as failure:
        return None, " ".join(str(failure).split())
    if axes is not None:
        return axes, ""
    product = (record.get("options") or {}).get("sheet_frame") or {}
    return None, str(product.get("provenance") or "pafta çerçevesi okunamadı ve onaylı görüş yok")


def _end(profile: dict, profile_id: str, edge: dict, which: str) -> dict | None:
    point = edge.get("start") if which == "start" else edge.get("end")
    if not point:
        return None
    return {"kind": "vertex", "id": f"{edge['id']}:{which}", "x": float(point[0]), "y": float(point[1]),
            "profile": profile_id, "geometry_version": None, "end": which}


def _axis_tie(first: dict, second: dict, axes: dict) -> tuple[str, int] | None:
    """The tie's axis and direction in the *sheet's* own frame — never the raw page delta (R01).

    `axes` is the view transform the build resolved (page-frame unit vectors for the sheet's +x/+y),
    the same one `make_plan` maps with. Page y grows downwards while the part's y grows upwards, so
    a downward pair is direction -1 — exactly the convention `Binding` carries; reading the page
    sign directly flips it. A pair that is diagonal in the sheet's frame has no axis to bind.
    """
    dx, dy = float(second["x"]) - float(first["x"]), float(second["y"]) - float(first["y"])
    along_x = dx * float(axes["x"][0]) + dy * float(axes["x"][1])
    along_y = dx * float(axes["y"][0]) + dy * float(axes["y"][1])
    if min(abs(along_x), abs(along_y)) > AXIS_TOLERANCE_PX:
        return None                      # çapraz iki uç: ölçünün ekseni yok, uydurulmaz
    if abs(along_x) >= abs(along_y):
        return ("x", 1 if along_x >= 0 else -1)
    return ("y", 1 if along_y >= 0 else -1)


def _same_hole(existing: dict, compiled: dict) -> bool:
    return (existing.get("kind") == compiled.get("kind")
            and abs(float(existing.get("diameter", 0.0)) - float(compiled["diameter"])) < 1e-6
            and (existing.get("depth") is None or compiled.get("depth") is None
                 or abs(float(existing["depth"]) - float(compiled["depth"])) < 1e-6))


def compile_callouts(record: dict) -> dict:
    """Compile every callout of a session record into candidate decisions + audit rows (pure)."""
    options = record.get("options") or {}
    circles = {row["id"]: row for row in options.get("circles") or [] if row.get("id")}
    profiles = {row["id"]: row for row in options.get("profiles") or [] if row.get("id")}
    decisions = _decisions(record)
    manual_holes = {row.get("circle_id"): row for row in decisions.get("holes") or []}
    manual_bindings = list(decisions.get("bindings") or [])
    declared_unit = sheet_unit(record)
    key = geometry_key(record, decisions)

    holes: list[dict] = []
    bindings: list[dict] = []
    unsupported: list[dict] = []
    conflicts: list[dict] = []
    excluded: list[dict] = []
    rows: list[dict] = []
    seen_holes: dict[str, dict] = {}
    view_axes, view_reason = _view_axes(record)

    for callout in effective_callouts(record):
        callout_id = callout["id"]
        state = callout_state(record, callout_id, decisions) or {}
        row = {"callout_id": callout_id, "page_index": callout.get("page_index"),
               "manual": callout.get("manual"), "geometry_key": key,
               "geometry_version": record.get("geometry_version"),
               "raw_text": None, "parser_version": None, "semantic": None, "target_kind": None,
               "target_ids": [], "decision": None, "status": None, "reason": None,
               "unit_source": None}
        rows.append(row)

        if callout.get("ignored"):
            row.update(status="excluded", reason="ignored")
            excluded.append({"callout_id": callout_id, "reason": "ignored"})
            continue
        if callout.get("unbindable"):
            # The user's own declaration (G6): this callout is not to be bound. Out of scope by
            # decision, visible in the chain — never a silent drop and never a guess.
            row.update(status="excluded", reason="unbindable_declared")
            excluded.append({"callout_id": callout_id, "reason": "unbindable_declared"})
            continue

        transcription = state.get("transcription") or {}
        if transcription.get("state") != "current":
            row.update(status="missing_transcription", reason=transcription.get("reason") or "needs_transcription")
            continue
        parse_state = state.get("parse") or {}
        if parse_state.get("state") != "current":
            row.update(status="stale_parse" if parse_state.get("state") == "stale" else "missing_parse",
                       reason=parse_state.get("reason") or "needs_parse")
            continue

        revision = transcription.get("revision")
        written = next((text for text in decisions.get("transcriptions") or []
                        if text.get("callout_id") == callout_id), None)
        target = next((item for item in decisions.get("callout_targets") or []
                       if item.get("callout_id") == callout_id), None)
        # R04 (review): the reading is chosen from the transcription revision and the *server's own*
        # parser version — never the target's, which may not exist yet. A text the parser cannot
        # support must read as an edit-the-text question, not as a missing-target one (the store
        # refuses that confirmation anyway, so the old order sent the user to a dead-end step).
        parse = _parse_row(record, callout_id, revision, CALLOUT_PARSER_VERSION)
        row.update(raw_text=(written or {}).get("raw_text"),
                   parser_version=(parse or {}).get("parser_version"),
                   semantic={name: (parse or {}).get(name)
                             for name in ("status", "form", "size", "count", "termination", "depth", "unit")})

        if parse is None or parse.get("status") != "parsed":
            status = "parse_ambiguous" if (parse or {}).get("status") == "ambiguous" else "parse_unsupported"
            row.update(status=status, reason="unsupported_syntax")
            continue
        size_mm, unit_source = _size_mm(parse, declared_unit)
        form = parse.get("form")
        if size_mm is None:
            row.update(status="missing_unit", reason="unit_not_resolved")
            continue
        row["unit_source"] = unit_source

        target_state = state.get("target") or {}
        if target is None:
            row.update(status="missing_target", reason="needs_target")
            continue
        if target_state.get("state") != "current":
            row.update(status="stale_target", reason=target_state.get("reason") or "stale")
            continue
        row.update(target_kind=target.get("target_kind"), target_ids=list(target.get("target_ids") or []))

        if form == "diameter":
            resolved = _unit_factor(parse, declared_unit)
            assert resolved is not None           # `size_mm` çözüldü: birim de çözüldü
            factor = resolved[0]
            if size_mm > MM_LIMIT:
                # R02 (review): the converted value has to fit the model it will become — refusing
                # here says so, where `Hole`'s own validation would fail one layer later, unnamed.
                unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                                    "detail": f"çap mm'ye çevrildiğinde {size_mm:g} mm: model sınırı "
                                              f"{MM_LIMIT:g} mm", "raw_text": row["raw_text"]})
                row.update(status="unsupported_semantic", reason="diameter_out_of_range")
                continue
            termination = parse.get("termination")
            if termination is None:
                unsupported.append({"callout_id": callout_id, "reason": "unsupported_cad_feature",
                                    "detail": "geçişli mi kör mü yazmıyor (THRU/BLIND): delik kararı verilemez",
                                    "raw_text": row["raw_text"]})
                row.update(status="unsupported_cad_feature", reason="termination_missing")
                continue
            depth = parse.get("depth")
            if termination == "blind" and depth is None:
                unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                                    "detail": "kör delik derinliği yazmıyor: derinlik uydurulmaz",
                                    "raw_text": row["raw_text"]})
                row.update(status="unsupported_semantic", reason="depth_missing")
                continue
            depth_mm = None
            if termination == "blind":
                # R02 (review): the depth is a measurement like the diameter — converted through the
                # same resolved unit, with the model's own mm bound applied after the conversion.
                depth_mm = float(depth) * factor
                if depth_mm > MM_LIMIT:
                    unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                                        "detail": f"derinlik mm'ye çevrildiğinde {depth_mm:g} mm: model "
                                                  f"sınırı {MM_LIMIT:g} mm", "raw_text": row["raw_text"]})
                    row.update(status="unsupported_semantic", reason="depth_out_of_range")
                    continue
            wanted = {"circle_id": None, "kind": "through" if termination == "thru" else "pocket",
                      "diameter": size_mm, "depth": depth_mm}
            missing = [item for item in row["target_ids"] if item not in circles]
            if missing:
                conflicts.append({"callout_id": callout_id, "reason": "unknown_geometry",
                                  "detail": "onaylanan hedef bu geometride yok: " + ", ".join(missing),
                                  "field": "target_ids"})
                row.update(status="conflict", reason="unknown_geometry")
                continue
            compiled_here: list[dict] = []
            matched_manual = False
            for circle_id in row["target_ids"]:
                decision = {**wanted, "circle_id": circle_id}
                existing = manual_holes.get(circle_id)
                if existing is not None:
                    if _same_hole(existing, decision):
                        matched_manual = True
                    else:
                        conflicts.append({"callout_id": callout_id, "reason": "manual_conflict",
                                          "field": "holes", "existing": existing, "compiled": decision,
                                          "detail": "kullanıcının kendi delik kararı bu callout ile çelişiyor"})
                    continue
                twin = seen_holes.get(circle_id)
                if twin is not None:
                    if not _same_hole(twin, decision):
                        conflicts.append({"callout_id": callout_id, "reason": "callout_conflict", "field": "holes",
                                          "existing": twin, "compiled": decision,
                                          "detail": "iki callout aynı daireye farklı delik kararı veriyor"})
                    continue
                seen_holes[circle_id] = decision
                holes.append(decision)
                compiled_here.append(decision)
            raised = [item for item in conflicts if item.get("callout_id") == callout_id]
            if raised:
                row.update(status="conflict", reason=raised[0]["reason"],
                           decision=compiled_here[0] if compiled_here else None)
            elif compiled_here:
                row.update(status="compiled",
                           decision=compiled_here[0] if len(compiled_here) == 1 else
                           {"count": len(compiled_here), "kind": wanted["kind"],
                            "circle_ids": [item["circle_id"] for item in compiled_here]})
            else:
                # The user's own decision already says exactly this: nothing is duplicated.
                row.update(status="compiled", reason="manual_decision_matches" if matched_manual
                           else "no_target_geometry", decision=None)
            continue

        if form == "radius":
            unsupported.append({"callout_id": callout_id, "reason": "unsupported_cad_feature",
                                "detail": "yay yarıçapı bu sürümde özellik üretmiyor (fillet/yuvarlatma yok)",
                                "raw_text": row["raw_text"]})
            row.update(status="unsupported_cad_feature", reason="radius_not_buildable")
            continue

        if form == "linear":
            if target.get("target_kind") != "vertex_pair" or len(row["target_ids"]) != 2:
                unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                                    "detail": "düz ölçü iki uç hedefi ister (vertex_pair)",
                                    "raw_text": row["raw_text"]})
                row.update(status="unsupported_semantic", reason="target_kind_not_bindable")
                continue
            profile_id = target.get("profile_id") or decisions.get("profile_id")
            profile = profiles.get(profile_id) if profile_id else None
            if profile is None:
                unsupported.append({"callout_id": callout_id, "reason": "missing_profile",
                                    "detail": "bağlanan kontur bu geometride yok",
                                    "raw_text": row["raw_text"]})
                row.update(status="unsupported_semantic", reason="profile_missing")
                continue
            profile_id = str(profile_id)
            edges = {edge.get("id"): edge for edge in profile.get("edges") or [] if edge.get("id")}
            ends = []
            for name in row["target_ids"]:
                edge_id, _, which = str(name).partition(":")
                edge = edges.get(edge_id)
                ends.append(_end(profile, profile_id, edge, which) if edge and which in ("start", "end")
                            else None)
            if any(end is None for end in ends):
                conflicts.append({"callout_id": callout_id, "reason": "unknown_geometry", "field": "target_ids",
                                  "detail": "onaylanan uçlar konturda bulunamadı: " + ", ".join(row["target_ids"])})
                row.update(status="conflict", reason="unknown_geometry")
                continue
            if view_axes is None:
                # R01 (review): the axis/direction decision needs the sheet's own frame; without a
                # vouchable view it is an *open decision* (PLAN §8.6) — never a page-frame guess.
                unsupported.append({"callout_id": callout_id, "reason": "view_not_confirmed",
                                    "detail": "ölçünün ekseni/yönü görüş ekseni onaylanmadan belirlenemez "
                                              "(PLAN §8.6): " + view_reason,
                                    "raw_text": row["raw_text"]})
                row.update(status="view_not_confirmed", reason="view_not_confirmed")
                continue
            axis = _axis_tie(ends[0], ends[1], view_axes)
            if axis is None:
                unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                                    "detail": "iki uç eksenel değil (çapraz): ölçünün ekseni belirlenemez",
                                    "raw_text": row["raw_text"]})
                row.update(status="unsupported_semantic", reason="axis_not_resolved")
                continue
            decision = {"id": f"callout:{callout_id}", "value": size_mm, "unit": "mm", "span_id": None,
                        "axis": axis[0], "direction": axis[1],
                        "first": {**ends[0], "geometry_version": target.get("geometry_version")},
                        "second": {**ends[1], "geometry_version": target.get("geometry_version")},
                        "note": "callout"}
            clash = next((item for item in manual_bindings
                          if item.get("first", {}).get("id") == ends[0]["id"]
                          and item.get("second", {}).get("id") == ends[1]["id"]
                          and abs(float(item.get("value", 0.0))
                                  * (INCH_MM if item.get("unit") == "in" else 1.0) - size_mm) > 1e-6), None)
            if clash is not None:
                conflicts.append({"callout_id": callout_id, "reason": "manual_conflict", "field": "bindings",
                                  "existing": clash, "compiled": decision,
                                  "detail": "kullanıcının kendi ölçü bağı bu callout ile çelişiyor"})
                row.update(status="conflict", reason="manual_conflict")
                continue
            if not any(item.get("id") == decision["id"] for item in bindings):
                bindings.append(decision)
            row.update(status="compiled", decision=decision)
            continue

        unsupported.append({"callout_id": callout_id, "reason": "unsupported_semantic",
                            "detail": "bu okuma biçimi karara derlenmiyor", "raw_text": row["raw_text"]})
        row.update(status="unsupported_semantic", reason="form_not_compilable")

    return {"holes": holes, "bindings": bindings, "unsupported": unsupported, "conflicts": conflicts,
            "excluded": excluded, "rows": rows, "geometry_key": key,
            "geometry_version": record.get("geometry_version")}


def apply_compiled(decisions: dict, compilation: dict) -> dict:
    """The decision set a build runs on: the user's own decisions, then the compiled ones.

    Compiled rows are appended only where the user has no decision of their own (a conflict is
    reported by `compile_callouts` and refused before the build, never patched over here).
    """
    merged = copy.deepcopy(decisions)
    holes = list(merged.get("holes") or [])
    known = {row.get("circle_id") for row in holes}
    for row in compilation.get("holes") or []:
        if row.get("circle_id") in known:
            continue
        row = {name: value for name, value in row.items() if name != "note"}
        holes.append(row)
        known.add(row.get("circle_id"))
    merged["holes"] = holes
    bindings = list(merged.get("bindings") or [])
    known_ids = {row.get("id") for row in bindings}
    for row in compilation.get("bindings") or []:
        if row.get("id") in known_ids:
            continue
        clean = {name: value for name, value in row.items() if name != "note"}
        for side in ("first", "second"):
            end = {name: value for name, value in clean[side].items() if value is not None}
            clean[side] = end
        bindings.append(clean)
        known_ids.add(row.get("id"))
    merged["bindings"] = bindings
    return merged


def compiled_summary(compilation: dict) -> dict:
    """The short counts a panel or a report quotes — never a substitute for the rows themselves."""
    return {"compiled_holes": len(compilation.get("holes") or []),
            "compiled_bindings": len(compilation.get("bindings") or []),
            "unsupported": len(compilation.get("unsupported") or []),
            "conflicts": len(compilation.get("conflicts") or []),
            "excluded": len(compilation.get("excluded") or []),
            "callouts": len(compilation.get("rows") or [])}


def compile_provenance(compilation: dict, feature_ids: dict[str, list[str]] | None = None) -> list[dict]:
    """The chain per compiled decision: decision ← target ← parse ← text ← callout (PLAN §13).

    `feature_ids` maps a compiled decision's own key (`circle_id`, or a binding's `id`) to the
    features the build produced for it — filled in by the caller that has the generated model.
    """
    produced = feature_ids or {}
    rows = []
    for row in compilation.get("rows") or []:
        decision = row.get("decision") or {}
        key = decision.get("circle_id") or decision.get("id")
        rows.append({"callout_id": row.get("callout_id"), "raw_text": row.get("raw_text"),
                     "parser_version": row.get("parser_version"), "semantic": row.get("semantic"),
                     "target_kind": row.get("target_kind"), "target_ids": row.get("target_ids"),
                     "geometry_key": row.get("geometry_key"), "geometry_version": row.get("geometry_version"),
                     "status": row.get("status"), "reason": row.get("reason"),
                     "compiled_decision": decision or None,
                     "generated_features": list(produced.get(key or "") or [])})
    return rows


__all__ = ["compile_callouts", "apply_compiled", "compiled_summary", "compile_provenance"]
