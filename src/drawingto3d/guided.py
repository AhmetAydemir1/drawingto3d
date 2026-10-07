"""Persistent, model-free drawing decisions compiled through GeneralPlan.

Trace geometry is explicitly an assumption. User measurements and feature decisions are
kept separately; valid CAD is not an assertion that a drawing has been reconstructed exactly.

The session record carries four things besides the decisions: what the sheet's own reading found
(`reading`), the decisions that reading can offer (`proposals`), a step `log` of who proposed,
accepted, edited, vetoed or built what, and the `history` an undo walks back. A proposal is data
until the user accepts it; `general.py` keeps a guess out of the parameter sources, and nothing
here promotes one.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from drawingto3d import advise
from drawingto3d import build_strategy
from drawingto3d.build_strategy import BuildStrategyDecision
from drawingto3d import callout_bind
from drawingto3d import callout_compile
from drawingto3d import callout_models
from drawingto3d import callout_parse
from drawingto3d import callout_readiness
from drawingto3d import callout_review
from drawingto3d import callouts
from drawingto3d.general import GeneralPlan, build_general
from drawingto3d.ingest import load_page
from drawingto3d.observe import observe
from drawingto3d import contour_audit
from drawingto3d import sketch_constraints as constraint_core
from drawingto3d.proposal import (_annotation_loops, _arc_points, _frame_loops, _loops, _phrases,
                                  _primitives, _loop_box, part_class, raster_arcs,
                                  ARC_JOIN_SLACK_PX, LOOP_TOLERANCE_PX, RASTER_JOIN_TOLERANCE_PX)

LOG_LIMIT = 200
# Raster arcs are trimmed back to their own ink, so a join can miss by a few pixels where the drawing
# joins exactly; a gap this small is closed at the middle (the corner rule handles the big, tangent ones).
ARC_JOIN_MIDDLE_PX = LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX


class Calibration(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    first: list[float] = Field(min_length=2, max_length=2)
    second: list[float] = Field(min_length=2, max_length=2)
    value: float = Field(gt=0, le=1e6)
    unit: Literal["mm", "in"] = "mm"
    span_id: str | None = None

    @model_validator(mode="after")
    def distinct(self):
        if math.dist(self.first, self.second) < 2:
            raise ValueError("ölçek için birbirinden ayrı iki nokta seçin")
        return self


class Hole(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    circle_id: str
    kind: Literal["through", "pocket"]
    diameter: float = Field(gt=0, le=1e6)
    depth: float | None = Field(default=None, gt=0, le=1e6)


class BindingEnd(BaseModel):
    """One end of a printed-measure tie, with *where* and *when* it was chosen (PLAN §8 P03-b).

    `id` alone is not enough: the same edge id can be part of two different contours, and a contour walked
    the other way round labels the same physical end `start` where it was `end`. So the record carries the
    contour it was chosen in, the geometry version it was chosen against, and which physical end of that
    edge the user clicked — while `x`/`y` stay the click itself, which is what makes the end physical even
    after a reversal.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["centre", "vertex"]
    id: str                      # a circle's geometry id, or "<edge id>:<start|end>" in the chosen contour
    x: float
    y: float
    profile: str | None = None            # the contour it was chosen in (never inferred from id text)
    geometry_version: int | None = None   # the geometry version it was chosen against
    end: Literal["start", "end"] | None = None   # the physical end the user clicked, as it was labelled then


class Binding(BaseModel):
    """One printed measurement the user tied to two pieces of the drawing (see `sketch.py`)."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str | None = Field(default=None, max_length=100)   # the decision's own identity, never the span's
    value: float = Field(gt=0, le=1e6)
    unit: Literal["mm", "in"] = "mm"
    span_id: str | None = None                             # the printed measurement it came from, if any
    axis: Literal["x", "y"] | None = None                  # what the user confirmed (PLAN §8.4); None = asked
    direction: Literal[-1, 1] | None = None                # +1: second sits +axis of first; -1 the other way
    first: BindingEnd
    second: BindingEnd


class ContourFix(BaseModel):
    """The user's correction of the traced contour: edges dropped, and the close join approved (PLAN §26.4-A).

    Dropping an edge removes a link the drawing does not have; the join is only ever the closure of what the
    drawing itself left, never a new segment invented to make a solid possible.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    drop: list[str] = Field(default_factory=list, max_length=50)
    approve_join: bool = False


class ViewConfirm(BaseModel):
    """The user's confirmation of the view axes (PLAN 8.6): which page way the sheet's own x and y go.

    The product (`options["sheet_frame"]`) proposes where the sheet's border is and how it is turned;
    this records what the user approved, against the geometry version they approved it in. The vectors
    are page-frame directions (px, y down) and nothing is inferred from a click delta.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x_page: list[float] = Field(min_length=2, max_length=2)
    y_page: list[float] = Field(min_length=2, max_length=2)
    frame_rect: list[float] | None = Field(default=None, min_length=4, max_length=4)
    source: Literal["sheet_frame", "page_axes"] = "sheet_frame"
    geometry_version: int | None = None


class Decisions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    calibration: Calibration | None = None
    profile_id: str | None = None
    thickness: float | None = Field(default=None, gt=0, le=1e6)
    holes: list[Hole] = Field(default_factory=list, max_length=100)
    bindings: list[Binding] = Field(default_factory=list, max_length=200)
    trace_acknowledged: bool = False
    contour: ContourFix = Field(default_factory=ContourFix)
    view: ViewConfirm | None = None
    # PLAN-20 §6.1: the callout layer's user decisions live here, in the undo-scoped decisions; a
    # parse result never becomes a "decision" — it rides in the session's `callout_parses`.
    transcriptions: list[callout_models.TranscriptionDecision] = Field(default_factory=list, max_length=200)
    callout_targets: list[callout_models.CalloutTargetDecision] = Field(default_factory=list, max_length=200)
    # PLAN-21 §6.1: G3's two user decisions — areas the user drew themselves, and their own review
    # (region correction / "not a callout") of any callout. Both undo-scoped, like every decision.
    manual_callouts: list[callout_models.ManualCalloutDecision] = Field(default_factory=list, max_length=200)
    callout_reviews: list[callout_models.CalloutReviewDecision] = Field(default_factory=list, max_length=200)
    # G12.2 (PLAN-25 §31): the part's own build strategy — an explicit user decision, so a selected
    # profile never implies an extrude. Backward-compatible: an older record simply has none, and the
    # build asks for it instead of assuming one.
    build_strategy: BuildStrategyDecision | None = None

    @model_validator(mode="after")
    def one_callout_entry_each(self):
        """PLAN-20 §6.5 + PLAN-21 §6.1: one current entry per callout — never silently pick the last."""
        for name, rows, key_field in (("transcriptions", self.transcriptions, "callout_id"),
                                      ("callout_targets", self.callout_targets, "callout_id"),
                                      ("manual_callouts", self.manual_callouts, "id"),
                                      ("callout_reviews", self.callout_reviews, "callout_id")):
            seen = set()
            for row in rows:
                key = getattr(row, key_field)
                if key in seen:
                    raise ValueError(f"aynı callout için birden fazla {name} kaydı olamaz: {key}")
                seen.add(key)
        return self


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, data: dict) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def _line_arc_corner(arc: dict, line: dict):
    """Where an arc meets a line: the arc's centre projected onto the line — the tangent point.

    The merged straight stroke runs some thirty pixels past that corner (the arc's own tangent ink
    is parallel to the line and the merge takes it), so the line's recorded end is *not* the corner.
    """
    if arc.get("kind") != "arc" or line.get("kind") != "line":
        return None
    centre = np.array(arc["center"], dtype=float)
    start = np.array(line["start"], dtype=float)
    direction = np.array(line["end"], dtype=float) - start
    length = float(np.linalg.norm(direction))
    if length <= 0.0:
        return None
    unit = direction / length
    along = float((centre - start) @ unit)
    if along < -LOOP_TOLERANCE_PX or along > length + LOOP_TOLERANCE_PX:
        return None
    foot = start + along * unit
    if abs(float(np.linalg.norm(foot - centre)) - float(arc["radius"])) > LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX:
        return None
    return foot


def _reangle(edge: dict) -> None:
    """Take an arc's canonical angles from its (just moved) endpoints, keeping the ink's own side.

    The span is the detector's ink, so a corner snap may only move the angle of the end it moved: a
    start pulled past b wraps below it, an end pulled past a wraps above it (the sign of b - a is kept).
    """
    a = -math.degrees(math.atan2(edge["start"][1] - edge["center"][1], edge["start"][0] - edge["center"][0]))
    b = -math.degrees(math.atan2(edge["end"][1] - edge["center"][1], edge["end"][0] - edge["center"][0]))
    # The sketch rebuilds the arc from centre, radius and angles, so the ring must pass through the ends
    # the neighbours join at: take the radius from the ends themselves (no projecting them off the join).
    edge["radius"] = float((math.dist(edge["center"], edge["start"]) + math.dist(edge["center"], edge["end"])) / 2)
    if edge["b"] > edge["a"]:
        while b <= a:
            b += 360.0
    else:
        while b >= a:
            b -= 360.0
    edge["a"], edge["b"] = a, b


def _align(edge: dict) -> None:
    """Pin an arc to a ring through its incoming end, so the sketch rebuilds exactly the traced point.

    The sketch rebuilds an arc from centre, radius and angles: a mean radius leaves the first end off
    the ring (a real gap at the join), so the radius is taken from the incoming end and the outgoing end
    is projected onto that ring — and the next piece is asked to start at the projected point.
    """
    centre = np.asarray(edge["center"], dtype=float)
    start = np.asarray(edge["start"], dtype=float)
    radius = float(np.linalg.norm(start - centre))
    span = float(edge["b"] - edge["a"])          # the sweep the reader (or the run) measured — trusted
    a = -math.degrees(math.atan2(start[1] - centre[1], start[0] - centre[0]))
    b = a + span
    end_angle = -b                                # back to sheet angles for the projection
    end = centre + radius * np.array([math.cos(math.radians(end_angle)), math.sin(math.radians(end_angle))])
    edge["radius"], edge["end"], edge["a"], edge["b"] = radius, end.tolist(), a, b


def _on_ring(edge: dict, point) -> bool:
    """True when a point stands on this arc's own circle — the corner the drawing joins at."""
    offset = np.array([point[0] - edge["center"][0], point[1] - edge["center"][1]], dtype=float)
    return abs(float(np.linalg.norm(offset)) - float(edge["radius"])) <= LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX


def _trace(loop: dict, mid_join_px: float = ARC_JOIN_MIDDLE_PX,
           close_tolerance_px: float | None = None) -> dict:
    """Orient fitted arcs for the canonical sketch and join near line endpoints explicitly."""
    edges = []
    for gid, start, end, meta in loop["entities"]:
        edge = {"id": gid, "kind": meta["kind"], "start": start.tolist(), "end": end.tolist()}
        if meta["kind"] == "arc":
            a, b = meta["start_degrees"], meta["end_degrees"]
            delta = b - a
            if delta > 360: delta -= 360
            if delta < -360: delta += 360
            # The ink is one run of the circle whichever end the chain walked in from, so the canonical
            # span is taken from the detector's own order (0 < b - a < 360) and never flipped per arc:
            # a per-arc flip is what made contours of mixed arcs unrepresentable.
            first = a if delta > 0 else b
            # A near-straight edge the vector reader stored as a bezier can come back as a huge-radius
            # arc of a ~350 degree sweep — its samples then leave the page and drag the whole contour
            # with them. When the ring is that much wider than the two ends, the ink between them is the
            # minor way, and that is what the contour needs.
            chord = float(np.linalg.norm(np.asarray(end, dtype=float) - np.asarray(start, dtype=float)))
            if chord > 0 and float(meta["radius"]) > 4.0 * chord and abs(delta) > 180.0:
                delta = delta - math.copysign(360.0, delta)
            # The ink runs from the detector's own `a` end by `delta`; the chain may have walked it from
            # either end, and the sketch needs the traversal it walked (a negative sweep is a clockwise
            # arc — how a right-hand bulge is built). Canonical angles are the sheet's angles negated.
            walked = math.degrees(math.atan2(start[1] - meta["centre"][1], start[0] - meta["centre"][0]))
            at_seam = abs((walked - a + 180.0) % 360.0 - 180.0) <= 90.0
            span = -delta if at_seam else delta
            # Sheet y points down; the sketch y points up.
            edge.update(center=meta["centre"].tolist(), radius=float(meta["radius"]),
                        a=-walked, b=-walked + span)
            # The sketch draws the arc from centre and angles; a fraction of a pixel here is a real gap
            # in mm. Pin the ring through the incoming end and project the outgoing end onto it.
            _align(edge)
        edges.append(edge)
    arcs = [e for e in edges if e["kind"] == "arc"]
    if any(e["kind"] == "arc" and (e["b"] == e["a"] or abs(e["b"] - e["a"]) >= 360) for e in edges):
        raise ValueError("bu konturun yay yönleri mevcut eskiz sözleşmesinde birlikte desteklenmiyor")
    max_join = 0.0
    joins = []
    for i, left in enumerate(edges):
        right = edges[(i+1) % len(edges)]
        gap = math.dist(left["end"], right["start"])
        max_join = max(max_join, gap)
        # Every link's own gap, so a caller can see where the contour was closed by force (PLAN §26.3) and so
        # the closure can be bounded: a ring whose ends are a hundred pixels apart is not a ring.
        joins.append({"index": i, "gap_px": round(gap, 4), "left": left.get("id"), "right": right.get("id")})
        if close_tolerance_px is not None and gap > close_tolerance_px:
            raise ValueError(f"kapanış boşluğu {gap:.1f} px ({close_tolerance_px:.0f} px sınırı): "
                             "bu halka kapalı bir kontur değil")
        # The drawing's own geometry decides where two pieces meet: an arc's corner is its centre
        # projected onto the line, and that holds even when the chain left the two ends touching each
        # other (the chain snaps the arc end onto the line's overshoot end, six pixels off the ring).
        corner = _line_arc_corner(left, right)
        if corner is None:
            corner = _line_arc_corner(right, left)
        meeting = None
        if corner is not None:
            meeting = corner.tolist()
        elif gap <= max(3.0001, mid_join_px) and gap > 1e-7:
            # Raster ends miss by a few pixels (a trimmed arc against a merged line, or two arcs of one
            # blend): the drawing joins them, so they meet at the middle — a sub-3 px correction.
            meeting = ((np.asarray(left["end"], dtype=float) + np.asarray(right["start"], dtype=float)) / 2).tolist()
        if meeting is None and gap > 3.0001:
            if left["kind"] == "arc" and _on_ring(left, right["start"]):
                meeting = list(right["start"])
            elif right["kind"] == "arc" and _on_ring(right, left["end"]):
                meeting = list(left["end"])
            else:
                raise ValueError(f"kontur uçları çizimde birleşmiyor ({i}. birleşim, boşluk {gap:.1f} px, "
                                 f"{left['kind']}→{right['kind']})")
        if meeting is not None:
            left["end"], right["start"] = list(meeting), list(meeting)
            if left["kind"] == "arc":
                # The arc's own ring decides the point: the next piece starts where the arc really ends.
                _align(left)
                right["start"] = list(left["end"])
            elif right["kind"] == "arc":
                _align(right)
            gap = 0.0
        if left["kind"] == right["kind"] == "arc":
            if gap > 1e-7: raise ValueError("iki yay arasında açık uç var; kontur düzeltmesi gerekli")
        elif left["kind"] == "arc": right["start"] = list(left["end"])
        elif right["kind"] == "arc": left["end"] = list(right["start"])
        else:
            point = [(a+b)/2 for a,b in zip(left["end"],right["start"])]
            left["end"], right["start"] = point, list(point)
    return {"edges": edges, "points": _display_points(edges), "join_max_px": max_join, "joins": joins}


def _sheet_frame_from_frame_loops(loops: list[dict], frames: set[int], observations) -> object | None:
    """Publish the sheet's own frame from the loop the trace skips (PLAN 8.6).

    `_frame_loops` already decides which loops are the sheet's border so the menu can leave them out;
    this asks the same loop for what it *is*: its own box, its own angle, and the axis directions that
    come from the source's /Rotate. It is published next to the profiles so the interface can show it and
    the user can confirm it - the flow never treats it as approved on its own.
    """
    from drawingto3d.observe import sheet_frame

    if getattr(observations, "frame", None) is None:
        return None
    candidates = []
    for index in sorted(frames):
        points = [[float(value) for value in point]
                  for _gid, start, end, _meta in loops[index]["entities"] for point in (start, end)]
        candidates.append(SimpleNamespace(id=f"outline_{index}", points=points, closed=True))
    rotation = int(getattr(getattr(observations, "source", None), "rotation", 0) or 0)
    product = sheet_frame(candidates, observations.frame, rotation)
    if frames:
        product.notes.insert(0, f"Kaynak: izlemenin atladığı pafta çerçevesi döngüsü ({len(frames)} aday).")
    return product


def drawing_options(observations, close_tolerance_px: float | None = None) -> dict:
    lines, arcs, circles = _primitives(observations)
    raster = raster_arcs(observations)
    # A raster chain closes its outline at a much wider gap than a vector one; the trace must accept
    # the same gap, or the contour the chain just found is thrown away again (measured joins on real
    # sheets: my_part.jpg 6.6 px, Exercise_51 24.2 px, Flange 20.0 px — all past the old 5.5 px cap).
    # Measured (run7): handing the trace the chain's own 36 px tolerance floods the menu — 45-48 wires
    # per sheet, the sheet frame among them, where 7-11 were offered before. So the parameter stays for
    # the sweep ahead, but the value reverts to the narrow cap: the chain's tolerance is what must be
    # measured, not the trace's willingness to move endpoints.
    # 20 px is the chain's business; the trace moves endpoints, so it takes half of it: at 10 px each end
    # travels at most 5 px, and the joins measured at 14.9 and 17.0 px come home (36 px flooded the menu
    # — run7 — so this cap never simply equals the chain's).
    mid_join_px = max(ARC_JOIN_MIDDLE_PX, RASTER_JOIN_TOLERANCE_PX / 2.0) if raster else ARC_JOIN_MIDDLE_PX
    loops = _loops(lines, arcs, corner_joins=raster,
                   join_tolerance_px=RASTER_JOIN_TOLERANCE_PX if raster else LOOP_TOLERANCE_PX)
    frames = _frame_loops(loops, observations.frame.width, observations.frame.height)
    sheet = _sheet_frame_from_frame_loops(loops, frames, observations)
    phrases = _phrases(observations)
    annotations = _annotation_loops(loops, phrases)
    profiles, skipped = [], []
    for i, loop in enumerate(loops):
        if i in frames or i in annotations: continue
        try:
            profile = _trace(loop, mid_join_px=mid_join_px, close_tolerance_px=close_tolerance_px)
            profile.update(id=f"outline_{i}", kind="wire", geometry_ids=[e[0] for e in loop["entities"]])
            # PLAN §26.3: the applied position change is measured on its own — how far the drawn edges had to
            # move from where the drawing has them for this contour to close (raw endpoints come from the same
            # primitives the chain walked, so the two numbers are comparable).
            moved = []
            for edge in profile.get("edges") or []:
                raw = lines.get(edge.get("id"))
                if raw is not None:
                    pairs = [(np.asarray(edge["start"], float), np.asarray(raw[0], float)),
                             (np.asarray(edge["end"], float), np.asarray(raw[1], float))]
                    moved.append(float(max(np.hypot(*(a - b)) for a, b in pairs)))
                    continue
                raw_arc = arcs.get(edge.get("id"))
                if raw_arc is None:
                    continue
                centre, radius, start_deg, end_deg = raw_arc
                ends = [np.asarray(centre, float) + float(radius) *
                        np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])
                        for deg in (start_deg, end_deg)]
                forward = max(np.hypot(*(np.asarray(edge["start"], float) - ends[0])),
                              np.hypot(*(np.asarray(edge["end"], float) - ends[1])))
                flipped = max(np.hypot(*(np.asarray(edge["start"], float) - ends[1])),
                              np.hypot(*(np.asarray(edge["end"], float) - ends[0])))
                moved.append(float(min(forward, flipped)))
            profile["applied_move_px"] = round(max(moved), 4) if moved else 0.0
            # The geometry CAD would receive, checked before anything is built, so the interface can flag it
            # and the user can choose another contour (PLAN §26.4-A). Truncated: the positions ride in the
            # first issues.
            audit = contour_audit.audit_contour(profile.get("edges") or [])
            profile["contour"] = {**audit, "issues": audit["issues"][:8], "issue_count": len(audit["issues"])}
            profiles.append(profile)
        except ValueError as exc:
            skipped.append(str(exc))
    circle_rows = []
    for gid, (center, radius) in circles.items():
        row = {"id":gid,"center":center.tolist(),"radius":float(radius)}
        circle_rows.append(row)
        profiles.append({"id":f"circle_{gid}","kind":"circle","circle":row,"geometry_ids":[gid],
                         "points":[p.tolist() for p in _arc_points(center,radius,0,360,60)],"join_max_px":0})
    # Measured on four real sheets (my_part.jpg): a contour the audit calls invalid can only be corrected when
    # the alternative links sit inside the chain's own tolerance — and they do not (single-edge drops left
    # 62-423 px open). So the honest service is to offer the *valid* contours first, by size, and keep the
    # invalid ones behind them, marked: the choice stays the user's and the evidence rides along (PLAN §26.2).
    def offer_rank(row: dict) -> tuple:
        points = row.get("points") or []
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            span = (max(xs) - min(xs)) * (max(ys) - min(ys))
        else:
            span = 0.0
        return (1 if (row.get("contour") or {}).get("ok") is False else 0, -span)
    profiles.sort(key=offer_rank)
    # Every primitive the sheet was read into, so a caller can resolve a geometry id the sheet names
    # (a reading's anchor may sit on a line that belongs to no closed loop).
    primitives = [{"id":gid,"kind":"line","start":row[0].tolist(),"end":row[1].tolist()} for gid,row in lines.items()]
    for gid, (centre, radius, start_degrees, end_degrees) in arcs.items():
        ends = _arc_points(centre, radius, start_degrees, end_degrees, 2)
        primitives.append({"id":gid,"kind":"arc","start":ends[0].tolist(),"end":ends[1].tolist(),
                           "center":centre.tolist(),"radius":float(radius),
                           "start_degrees":float(start_degrees),"end_degrees":float(end_degrees)})
    primitives += [{"id":row["id"],"kind":"circle","center":row["center"],"radius":row["radius"]} for row in circle_rows]
    # Printed numbers offered to the user: everything on the sheet except the phrases printed inside an
    # annotation region (a title block's zone letters, part number, scale). Texts inside the sheet's own
    # *border* stay: the border holds the whole drawing, and on several sheets every phrase is in it.
    table_boxes = [_loop_box(loop) for index, loop in enumerate(loops)
                   if index in annotations and index not in frames]

    def in_table(item) -> bool:
        return any(x0 < item.bbox.x + item.bbox.w / 2 < x1 and y0 < item.bbox.y + item.bbox.h / 2 < y1
                   for (x0, y0), (x1, y1) in table_boxes)

    measurements = [t.model_dump(mode="json") for t in observations.texts
                    if t.value is not None and not in_table(t)]
    table_dropped = sum(1 for t in observations.texts if t.value is not None and in_table(t))
    notes = list(skipped)
    if table_boxes:
        notes.append(f"antet/tablo bölgesi atlandı ({len(table_boxes)} döngü, {table_dropped} basılı sayı "
                     f"menüye alınmadı)")
    notes.append("İlk sayfa işlenir. Konturlar çizimden ölçülmüştür; kesin ölçülü eskiz olarak onaylanmış değildir.")
    return {"frame":observations.frame.model_dump(), "profiles":profiles,"circles":circle_rows,
            "primitives":primitives, "measurements":measurements, "notes":notes,
            "sheet_frame": sheet.model_dump() if sheet is not None else None}


def validate_decisions(options: dict, decisions: Decisions) -> None:
    profiles={p["id"] for p in options["profiles"]}
    circles={p["id"] for p in options["circles"]}
    if decisions.profile_id is not None and decisions.profile_id not in profiles:
        raise ValueError("seçilen kontur bu çizimde yok")
    if len({h.circle_id for h in decisions.holes}) != len(decisions.holes):
        raise ValueError("aynı daire iki kez delik/cep olarak seçilemez")
    for hole in decisions.holes:
        if hole.circle_id not in circles: raise ValueError("seçilen daire bu çizimde yok")
        if decisions.profile_id == f"circle_{hole.circle_id}": raise ValueError("dış kontur kendi deliği olamaz")
        if hole.kind == "pocket" and (hole.depth is None or decisions.thickness is None or hole.depth >= decisions.thickness):
            raise ValueError("kör cep derinliği kalınlıktan küçük ve pozitif olmalı")
        if hole.kind == "through" and hole.depth is not None:
            raise ValueError("geçişli deliğe ayrıca derinlik girilmez")
    cal=decisions.calibration
    if cal:
        for x,y in (cal.first,cal.second):
            if not (0<=x<=options["frame"]["width"] and 0<=y<=options["frame"]["height"]):
                raise ValueError("kalibrasyon noktası çizim dışında")
        if cal.span_id and cal.span_id not in {m["id"] for m in options["measurements"]}:
            raise ValueError("kalibrasyon ölçüsünün kaynağı bu çizimde yok")
    spans={m["id"] for m in options["measurements"]}
    seen_ids: set[str] = set()
    for binding in decisions.bindings:
        if binding.id:
            if binding.id in seen_ids:
                raise ValueError("aynı karar kimliği iki kez kullanılmış: " + binding.id)
            seen_ids.add(binding.id)
        # PLAN §8.4/§8.10: an unconfirmed axis is *asked*, not filled in and not a save error — `questions()`
        # carries the ask and the build waits; removing the binding stays the user's own move.
        if binding.span_id and binding.span_id not in spans:
            raise ValueError("bağlanan ölçünün kaynağı bu çizimde yok")
        for end in (binding.first, binding.second):
            if not (0<=end.x<=options["frame"]["width"] and 0<=end.y<=options["frame"]["height"]):
                raise ValueError("bağ ucu çizim dışında")
        # PLAN §8.9: an end that left the drawing is not a save error and is never re-mapped silently — it
        # becomes a "needs re-binding" state (`unresolved_bindings`), which `questions()` asks about.
    # PLAN 8.6: the confirmed view must be a real pair of page directions. A vector that is not a unit
    # vector, or two that are not perpendicular, cannot describe a sheet's axes — the drawing's own
    # x/y are at 90 degrees to each other, so anything else is a typo, not a view.
    if decisions.view is not None:
        approved = decisions.view
        for name, vector in (("x", approved.x_page), ("y", approved.y_page)):
            length = (vector[0] ** 2 + vector[1] ** 2) ** 0.5
            if abs(length - 1.0) > 0.01:
                raise ValueError(f"görüş {name} ekseni birim vektör olmalı (uzunluk {length:.3f})")
        dot = approved.x_page[0] * approved.y_page[0] + approved.x_page[1] * approved.y_page[1]
        if abs(dot) > 0.01:
            raise ValueError(f"görüş eksenleri dik olmalı (iç çarpım {dot:.3f})")
        if approved.frame_rect is not None:
            x0, y0, x1, y1 = approved.frame_rect
            if not (0 <= x0 <= x1 <= options["frame"]["width"] and 0 <= y0 <= y1 <= options["frame"]["height"]):
                raise ValueError("onaylanan görüş çerçevesi çizim dışında")


def _end_label(end) -> str | None:
    """The end's own label, from the explicit field or the id's `<edge>:<tail>` form (PLAN §8.7/§8.8)."""
    label = getattr(end, "end", None)
    if label in ("start", "end"):
        return label
    raw = str(getattr(end, "id", "") or "")
    edge_key, separator, tail = raw.rpartition(":")
    return tail if separator and tail in ("start", "end") and edge_key else None


def _edge_id_of(end) -> str:
    """The stable edge id a `vertex` end points at, with the end tail removed."""
    raw = str(getattr(end, "id", "") or "")
    edge_key, separator, tail = raw.rpartition(":")
    if separator and tail in ("start", "end") and edge_key:
        return edge_key
    return raw


def resolve_binding_end(edges: list[dict], end, tolerance_px: float = 0.75) -> tuple[str | None, str | None]:
    """Resolve a `vertex` end to a vertex name, physically (PLAN §8 P03-b.2).

    Returns `(vertex_name, None)` or `(None, reason)`. The stored click point decides *which* end of the
    edge the user tied to — so reversing the contour's traversal, which swaps the `start`/`end` labels,
    cannot move the tie to the other corner. The label is evidence: if the point and the label disagree, the
    record contradicts itself and the tie is reported for re-binding rather than guessed at.
    """
    raw = str(getattr(end, "id", "") or "")
    edge_key, separator, tail = raw.rpartition(":")
    if not (separator and tail in ("start", "end")):
        # Pre-P03 forms (`edge:<index>` or a bare index): the index names the edge the user clicked and the
        # click point names the end (PLAN §8 P03-a.1). Anything else is not a usable end identity at all.
        if (edge_key == "edge" and tail.isdigit()) or raw.isdigit():
            index = int(tail if tail.isdigit() else raw)
            if index >= len(edges):
                return None, f"{raw} bu konturda olan bir nokta değil (bağ ucu artık bu konturda yok)"
            point = [float(getattr(end, "x", 0.0) or 0.0), float(getattr(end, "y", 0.0) or 0.0)]
            start = [float(v) for v in edges[index]["start"]]
            stop = [float(v) for v in edges[index]["end"]]
            nearest = "start" if math.dist(start, point) <= math.dist(stop, point) else "end"
            return (f"v{index}" if nearest == "start" else f"v{(index + 1) % len(edges)}"), None
        return None, f"{raw or '(boş)'} geçerli bir uç kimliği değil"
    index = next((i for i, edge in enumerate(edges) if str(edge.get("id")) == edge_key), None)
    if index is None:
        return None, f"{raw} bu konturda olan bir nokta değil (bağ ucu artık bu konturda yok)"
    start = [float(v) for v in edges[index]["start"]]
    stop = [float(v) for v in edges[index]["end"]]
    name_start, name_stop = f"v{index}", f"v{(index + 1) % len(edges)}"
    label = _end_label(end)
    point = [float(getattr(end, "x", 0.0) or 0.0), float(getattr(end, "y", 0.0) or 0.0)]
    to_start, to_stop = math.dist(start, point), math.dist(stop, point)
    nearest = "start" if to_start <= to_stop else "end"
    nearest_distance = min(to_start, to_stop)
    del label  # kept above as documentation of the record's own evidence; the point decides
    if nearest_distance > tolerance_px:
        # The click no longer lands on either end of that edge: the contour was edited around it, so the tie
        # is reported instead of being slid to whichever corner happens to be closest (PLAN §8.9).
        return None, (f"{raw} kenarın uçlarında değil ({nearest_distance:.2f} px uzakta): "
                      "yeniden bağlanmalı")
    # The stored label is *evidence*, never the decision: it says which end it was when the user clicked, and
    # a contour walked the other way round swaps those labels while the point stays where the user put it.
    return (name_start if nearest == "start" else name_stop), None


def _binding_end_issues(options: dict, decisions: Decisions) -> list[dict]:
    """Every tie whose own geometry no longer answers — the one list both the save gate and `questions()` use."""
    profile = next((p for p in options.get("profiles") or [] if p.get("id") == decisions.profile_id), None)
    edges = (profile or {}).get("edges") or []
    circles = {c["id"] for c in options.get("circles") or []}
    stale = []
    for binding in decisions.bindings:
        for role, end in (("first", binding.first), ("second", binding.second)):
            if end.kind == "centre":
                if end.id not in circles:
                    stale.append({"id": binding.id, "end": role, "reason": f"{end.id} bu çizimde olan bir daire değil"})
                continue
            # P03-b.2: an end chosen in another contour is *not* the same end here, even when the edge id
            # still exists in this one — the ids are not the identity of the tie.
            if getattr(end, "profile", None) and end.profile != decisions.profile_id:
                stale.append({"id": binding.id, "end": role,
                              "reason": (f"bağ ucu başka bir konturda seçilmiş ({end.profile}); "
                                         f"bu konturda yeniden bağlanmalı")})
                continue
            if profile is None:
                stale.append({"id": binding.id, "end": role,
                              "reason": f"kontur seçilmemiş; {end.id} yeniden bağlanmalı"})
                continue
            name, reason = resolve_binding_end(edges, end)
            if name is None:
                stale.append({"id": binding.id, "end": role, "reason": reason})
    return stale


def unresolved_bindings(options: dict, decisions: Decisions) -> list[dict]:
    """Ties whose own geometry left the drawing (PLAN §8.9): the chosen contour changed or a circle is gone.

    They stay in the record exactly as the user wrote them — never re-mapped to the nearest point — and the
    interface asks the user to bind them again or drop them; the build waits for that answer. The save gate
    and `questions()` both read this one list, so a tie cannot be "fine" for one and stale for the other.
    """
    return _binding_end_issues(options, decisions)


def _with_end_evidence(record: dict, decisions: Decisions) -> tuple[Decisions, int]:
    """P03-b-2: write down *where and when* each tie's end was chosen, on the way into the record.

    The contour the end was chosen in, the geometry version it was chosen against and which physical end of
    the edge the user clicked are facts only the flow can supply — the id text is not the identity (P03-b.2).
    An end that does not resolve is left exactly as it is: it is already a "re-bind" state and pinning it to a
    guess would be the silent nearest-mapping §8.9 forbids.
    """
    options = record.get("options") or {}
    profile = next((p for p in options.get("profiles") or [] if p.get("id") == decisions.profile_id), None)
    edges = (profile or {}).get("edges") or []
    payload = decisions.model_dump(mode="json")
    written = 0
    for binding in payload.get("bindings") or []:
        for role in ("first", "second"):
            end = binding.get(role) or {}
            if end.get("kind") != "vertex":
                continue
            if end.get("profile") and end.get("geometry_version") is not None and end.get("end"):
                continue
            parsed = BindingEnd.model_validate(end)
            name, _reason = resolve_binding_end(edges, parsed)
            if name is None:
                continue
            edge_index = next((i for i, edge in enumerate(edges) if str(edge.get("id")) == _edge_id_of(parsed)), None)
            if edge_index is None:
                continue
            end["profile"] = decisions.profile_id
            end["geometry_version"] = record.get("geometry_version")
            end["end"] = "start" if name == f"v{edge_index}" else "end"
            written += 1
    if not written:
        return decisions, 0
    return Decisions.model_validate(payload), written


def note_sketch(record: dict) -> dict:
    """Recompute the B-slice diagnostics for a record and keep them next to the decisions.

    The session record carries them so the questions, the panel and the audit log all quote the same fit —
    the flow never recomputes a scale behind the user's back at build time.
    """
    try:
        record["sketch"]=sketch_diagnostics(record["options"],Decisions.model_validate(record["decisions"]))
    except Exception as error:                                   # a broken decision set must not break the page
        record["sketch"]={"error":" ".join(str(error).split())[:300]}
    return record


def sketch_diagnostics(options: dict, decisions: Decisions) -> dict:
    """The B-slice picture for one decision set: the bound measurements, their fit, and what stays traced.

    `sketch.py` does the work; this only hands it the geometry the user's decision set actually refers to —
    the chosen contour's own points, and every circle the flow offered.
    """
    from drawingto3d import sketch as sketch_module

    profile = next((row for row in options.get("profiles", []) if row["id"] == decisions.profile_id), None)
    bindings = [sketch_module.Binding(value=item.value, unit=item.unit, span_id=item.span_id,
                                      first=item.first.model_dump(), second=item.second.model_dump())
                for item in decisions.bindings]
    fallback = None
    if decisions.calibration and decisions.calibration.value:
        first, second = decisions.calibration.first, decisions.calibration.second
        unit = 25.4 if decisions.calibration.unit == "in" else 1.0
        length = math.dist(first, second)
        fallback = length / (decisions.calibration.value * unit) if length > 0 else None
    if bindings and fallback:
        fit = sketch_module.fit_scale(bindings, fallback)
    elif bindings:
        fit = sketch_module.fit_scale(bindings, None)
    else:
        fit = {"px_per_mm": fallback, "source": "calibration" if fallback else None, "rows": [],
               "conflicts": [], "consistent": bool(fallback)}
    picture = sketch_module.diagnose(profile or {}, options.get("circles", []), bindings, fit)
    # PLAN P04-a: the part is built at the scale the user *calibrated*, never at a scale fitted from their
    # printed measures (that fit stays visible right here, as a report). The old line published the fit as
    # `px_per_mm`, so one centre tie silently rescaled the whole body (F12).
    picture["fit"] = {"px_per_mm": fit.get("px_per_mm"), "source": fit.get("source"),
                      "rows": fit.get("rows", []), "conflicts": fit.get("conflicts", []),
                      "consistent": bool(fit.get("consistent"))}
    picture["px_per_mm"] = fallback
    picture["source"] = "calibration" if fallback else None
    if profile:
        edges = profile.get("edges") or []
        if edges:
            audit = contour_audit.audit_contour(edges)
        else:
            # A circle profile has no edges to audit; a full ring is closed by construction.
            audit = {"ok": True, "closure_px": 0.0, "issues": [], "edge_count": 0}
        # `join_max_px` is the gap measured *before* a join; the boundary's real closure error is the audit's
        # number, and the two must not wear the same name (PLAN §26.3).
        picture["contour"] = audit
        picture["open_contour_px"] = audit.get("closure_px")
    if profile:
        # The applied correction, on its own (PLAN §26.3) — the trace moved the drawn edges by this much.
        picture["applied_move_px"] = profile.get("applied_move_px")
        # What the user's own dimensions did to the geometry (PLAN §26.4-B): the core's status, the
        # coordinates still free, the ties that conflict, and the core's own restriction notes.
        picture["solved_dimensions"] = profile.get("solved_dimensions")
    return picture


def unsupported_binding_reasons(profile: dict, decisions: Decisions) -> list[str]:
    """Why the constraint core cannot measure these ties at all (PLAN P04-b).

    The core measures an all-line contour's vertices and any contour's circle centres; on a contour that
    carries an arc it accepts only the centres ("yaylı veya dairesel dış konturda yalnız daire merkezleri
    ölçülendirilebilir"). That rule lives in the core — this reads the same shape of profile and says the
    same thing *before* the build, so the interface can ask instead of letting the user find out at the end.
    A test pins both paths to the same behaviour, because the duplicate must not drift.
    """
    bindings = list(getattr(decisions, "bindings", []) or [])
    if not bindings or profile is None:
        return []
    curved = any(edge.get("kind") in ("arc", "circle") for edge in profile.get("edges") or [])
    if not curved:
        return []
    reasons = []
    for binding in bindings:
        for end in (binding.first, binding.second):
            if getattr(end, "kind", None) == "centre":
                continue
            reasons.append(f"Bağlanan ölçü desteklenmiyor ({binding.id or 'bağ'}): yaylı veya dairesel dış "
                           "konturda yalnız daire merkezleri ölçülendirilebilir; bağı bir merkezler arasına "
                           "taşıyın ya da kaldırın.")
            break
    return reasons


def bindings_solvable(decisions: Decisions, options: dict | None = None) -> bool:
    """Can the constraint core measure *every* tie in this decision set? (PLAN §26.4-B)

    Judged by the same support rules and the same resolver the build uses (PLAN P04-a item 3): a supported
    X/Y tie between two resolvable contour vertices or circle centres is measurable, and whether its printed
    value agrees with one fitted scale is a *residual report* (F13), not a reason to block. Still not
    measurable, and still blocking: an end that cannot be resolved, a kind the core does not support, or a
    tie from an end to itself. Without `options` the profile is not in hand, so only centre ties are assumed.
    """
    bindings = list(getattr(decisions, "bindings", []) or [])
    if not bindings:
        return False
    profile = None
    if options is not None:
        profile = next((row for row in options.get("profiles") or [] if row["id"] == decisions.profile_id),
                       None)
    for binding in bindings:
        if binding.axis is None or binding.direction is None:
            return False
        ends = []
        for end in (binding.first, binding.second):
            if getattr(end, "kind", None) == "centre":
                ends.append(("circle_center", str(getattr(end, "id", ""))))
                continue
            if getattr(end, "kind", None) != "vertex" or profile is None:
                return False
            try:
                reference = binding_reference(profile, end)
            except ValueError:
                return False
            ends.append((reference.kind, reference.id))
        if ends[0] == ends[1]:
            return False
    return True


def questions(decisions: Decisions, diagnostics: dict | None = None, options: dict | None = None) -> list[str]:
    missing=[]
    if not decisions.profile_id: missing.append("Ana görünüşte dış konturu seçin.")
    if not decisions.calibration: missing.append("Bilinen ölçünün iki noktasını ve uzunluğunu belirtin.")
    if not decisions.thickness: missing.append("Parçanın kalınlığını girin.")
    if not decisions.trace_acknowledged: missing.append("Çizimden izlenen konturu taslak olarak kullanmayı onaylayın.")
    if any(b.axis is None or b.direction is None for b in getattr(decisions, "bindings", []) or []):
        missing.append("Bağlanan ölçünün eksenini (X/Y) ve yönünü seçin.")
    if options is not None:
        for row in unresolved_bindings(options, decisions):
            missing.append(f"Bağlanan ölçü yeniden bağlanmalı ({row['reason']}); en yakın noktaya taşınmaz.")
        # PLAN 8.6: the view is asked about where it is not obvious. An upright sheet whose frame was found
        # and aligned needs no question — the page axes *are* the sheet's. A missing border, a tilted frame
        # or a rotated source is exactly where "page x = part x" would be an assumption, so it is asked.
        product = options.get("sheet_frame") or {}
        view = getattr(decisions, "view", None)
        obvious = bool(product.get("found")) and product.get("aligned") is not False \
            and not product.get("rotation")
        if view is None:
            # Only where the page is *not* obviously the sheet: no border, a tilted frame, a rotated source.
            if not obvious:
                missing.append(_view_question(product))
        elif _view_mismatch(view, product):
            missing.append("Onaylanan görüş yönü bu okumayla uyuşmuyor (çerçeve ya da eksenler değişti); "
                           "görüş yeniden onaylanmalı.")
    if options is not None:
        profile = next((row for row in options.get("profiles") or [] if row["id"] == decisions.profile_id), None)
        unsupported = unsupported_binding_reasons(profile, decisions)
        if unsupported:
            # PLAN P04-b: said out loud, in the user's own terms, before the build tries and fails. The fit
            # residuals are not the question here — the tie is not measurable at all.
            missing.extend(unsupported)
            return missing
    if diagnostics and not bindings_solvable(decisions, options):
        # PLAN §26.4-B: when the constraint core can measure these ties, printed values that disagree under
        # one scale are not a blocking error any more — they are the reason the geometry moves. The residuals
        # stay in the diagnostics (the interface shows them); only a genuine core conflict stops the build,
        # and that is raised where the profile is known (`make_plan`), with the core's own message.
        missing.extend(sketch_questions(diagnostics))
    return missing


def _view_mismatch(view: "ViewConfirm", product: dict) -> bool:
    """Has the reading moved out from under the confirmed view? Then the confirmation is asked again."""
    if product.get("found") and view.frame_rect is not None:
        rect = product.get("rect") or []
        if len(rect) == 4 and [round(float(v)) for v in rect] != [round(float(v)) for v in view.frame_rect]:
            return True
    axes = product.get("axes") or []
    if len(axes) == 2:
        for axis, approved in zip(axes, (view.x_page, view.y_page)):
            page = axis.get("page") or []
            if len(page) != 2 or abs(float(page[0]) - approved[0]) > 0.01 or abs(float(page[1]) - approved[1]) > 0.01:
                return True
    return False


def _view_question(product: dict) -> str:
    """The ask for an un-obvious view, with the product's own wording as the reason (PLAN 8.6)."""
    axes = product.get("axes") or []
    compass = {"sağ": (1.0, 0.0), "sol": (-1.0, 0.0), "aşağı": (0.0, 1.0), "yukarı": (0.0, -1.0)}

    def name(axis) -> str:
        if not isinstance(axis, dict):
            return "?"
        vector = axis.get("page") or []
        for word, direction in compass.items():
            if len(vector) == 2 and abs(vector[0] - direction[0]) < 0.01 and abs(vector[1] - direction[1]) < 0.01:
                return word
        return "?"

    if axes:
        proposal = f"öneri: X {name(axes[0])}, Y {name(axes[1])}"
    else:
        proposal = "öneri yok: sayfa yönü çeyrek tur değil"
    return (f"Görüş eksenini ve çerçeveyi onaylayın ({proposal}); "
            f"{product.get('provenance') or 'pafta çerçevesi okunamadı'}.")


def sketch_questions(diagnostics: dict) -> list[str]:
    """Conflicting bindings are asked by `sketch.py`; this keeps the wording in one place."""
    from drawingto3d import sketch as sketch_module

    return sketch_module.questions(diagnostics)


def _display_points(edges: list[dict]) -> list:
    """The contour as the interface draws it: line ends and sampled arcs (canonical angles back to image)."""
    display = []
    for e in edges:
        if e["kind"] == "line": display.append(e["start"])
        else:
            display.extend([p.tolist() for p in _arc_points(np.array(e["center"]),e["radius"],-e["a"],-e["b"],24)])
    return display


def correct_profile(profile: dict, fix: "ContourFix", *, join_tolerance_px: float, mid_join_px: float) -> dict:
    """PLAN §26.4-A: apply the user's correction to the traced contour, without inventing geometry.

    Dropped edges leave their neighbours open. They are closed only when the drawing itself left them within
    the join tolerance the chain uses, the user approved that join, and each end moves no more than the trace
    itself would move one; otherwise the correction is refused with the gap it would leave.
    """
    dropped = set(fix.drop or ())
    original = profile.get("edges") or []
    kept = [edge for edge in original if edge.get("id") not in dropped]
    if not kept:
        raise ValueError("çıkarılan kenarlardan sonra konturda kenar kalmadı")
    joined, moved, closed_gap = 0, 0.0, 0.0
    if len(kept) != len(original):
        gaps = []
        for index, edge in enumerate(kept):
            following = kept[(index + 1) % len(kept)]
            gaps.append((float(np.hypot(*(np.asarray(following["start"], float)
                                          - np.asarray(edge["end"], float)))), index))
        gaps.sort(reverse=True)
        worst, at = gaps[0]
        if worst > join_tolerance_px:
            raise ValueError(f"çıkarılan kenardan sonra uçlar {worst:.1f} px açık kaldı "
                             f"({join_tolerance_px:.0f} px sınırı): bu düzeltme konturu kapatmıyor")
        if worst > 0.0:
            if len(gaps) > 1 and gaps[1][0] > 0.0:
                open_gaps = sum(1 for value, _ in gaps if value > 0.0)
                raise ValueError(f"çıkarma {open_gaps} ayrı açıklık bıraktı; tek açıklıklı bir düzeltme yapın")
            if not fix.approve_join:
                raise ValueError(f"çıkarılan kenardan sonra uçlar {worst:.1f} px açık; "
                                 "birleşimi onaylamadan düzeltme uygulanmaz")
            if worst / 2.0 > mid_join_px:
                raise ValueError(f"birleşim her ucu {worst / 2.0:.1f} px kaydırır "
                                 f"(sınır {mid_join_px:.1f} px): bu düzeltme çizimden fazla uzaklaşıyor")
            left, right = kept[at], kept[(at + 1) % len(kept)]
            point = [(float(a) + float(b)) / 2.0 for a, b in zip(left["end"], right["start"])]
            kept[at] = {**left, "end": list(point)}
            kept[(at + 1) % len(kept)] = {**right, "start": list(point)}
            joined, moved, closed_gap = 1, worst / 2.0, worst
    corrected = {**profile, "edges": kept, "points": _display_points(kept),
                 "join_max_px": closed_gap if joined else profile.get("join_max_px", 0.0),
                 "correction": {"dropped": sorted(dropped), "kept": len(kept), "joined": joined,
                                "closed_gap_px": round(closed_gap, 4), "moved_px": round(moved, 4)}}
    return corrected



def user_dimensions(profile: dict, options: dict, decisions: "Decisions", scale: float,
                    origin: list) -> dict | None:
    """Translate the user's printed-measure ties into the constraint core and solve them (PLAN §26.4-B).

    Nothing is invented here: the axis and direction of a tie are the user's own confirmed decision (PLAN
    §8.4 — never inferred from which click differed more), a
    radius/angle/tangency support yet, arcs and circle outlines only through their centres) come back as the
    `status`/`notes` the interface shows rather than being papered over.
    """
    bindings = list(getattr(decisions, "bindings", []) or [])
    if not bindings:
        return None
    edges = profile.get("edges") or []
    vertices = []
    for index, edge in enumerate(edges):
        for key, end in ((f"vertex:v{index}", edge.get("start")),
                         (f"vertex:v{(index + 1) % len(edges)}", edge.get("end"))):
            if end is not None:
                vertices.append((key, [float(v) for v in end]))

    dimensions = []
    for index, binding in enumerate(bindings):
        first, second = (binding_reference(profile, binding.first),
                         binding_reference(profile, binding.second))
        span = list(bindings)[index].value * (25.4 if binding.unit == "in" else 1.0)
        if binding.axis is None or binding.direction is None:
            raise ValueError("bağlanan ölçünün ekseni ve yönü onaylanmadan çözülemez")
        dimensions.append(constraint_core.DimensionBinding(id=binding.id or f"binding_{index}",
                                                           axis=binding.axis, first=first, second=second,
                                                           direction=binding.direction,
                                                           value=float(span), unit="mm", span_id=binding.span_id))
    constraints = constraint_core.SketchConstraints(profile_id=profile["id"], datum=dimensions[0].first,
                                                    relations=[], dimensions=dimensions)
    try:
        solution = constraint_core.solve_constraints(profile, options.get("circles") or [], scale, origin,
                                                     constraints,
                                                     {b.span_id for b in bindings if b.span_id})
    except ValueError as exc:
        profile["solved_dimensions"] = {"status": "unsupported", "notes": [str(exc)], "conflicts": [],
                                        "moved": 0, "dof": None}
        return profile["solved_dimensions"]
    report = {"status": solution.get("status"), "dof": solution.get("dof"),
              "conflicts": [row.get("constraint_ids") for row in solution.get("conflicts") or []],
              "notes": list(solution.get("notes") or []), "moved": 0.0, "free": len(solution.get("free_coordinates") or [])}
    profile["solved_dimensions"] = report
    if solution.get("status") == "conflict":
        return report
    centres = {}
    for key, value in (solution.get("points") or {}).items():
        if not key.startswith("circle_center:"):
            continue
        centres[key.split(":", 1)[1]] = [origin[0] + value[0] * scale, origin[1] - value[1] * scale]
    if solution.get("outer_moves"):
        moved = 0.0
        for index, edge in enumerate(edges):
            start = (solution.get("points") or {}).get(f"vertex:v{index}")
            end = (solution.get("points") or {}).get(f"vertex:v{(index + 1) % len(edges)}")
            if start is None or end is None:
                continue
            start_px = [origin[0] + start[0] * scale, origin[1] - start[1] * scale]
            end_px = [origin[0] + end[0] * scale, origin[1] - end[1] * scale]
            moved = max(moved, math.dist(start_px, [float(v) for v in edge["start"]]),
                        math.dist(end_px, [float(v) for v in edge["end"]]))
            edge["start"], edge["end"] = start_px, end_px
        profile["points"] = _display_points(edges)
        report["moved"] = round(moved, 4)
    # Which coordinates the core actually fixed (PLAN §26.4-B "kaynakları koru"): the free list is by axis
    # and point, so the plan can label exactly those; the datum keeps the gauge and stays a traced coordinate.
    free = {(row.get("axis"), key) for row in solution.get("free_coordinates") or []
            for key in row.get("points") or []}
    datum_key = f"{constraints.datum.kind}:{constraints.datum.id}"
    report["user_coordinates"] = sorted(f"{key}:{axis}" for key in (solution.get("points") or {})
                                        for axis in ("x", "y")
                                        if (axis, key) not in free and key != datum_key)
    report["free_count"] = len(solution.get("free_coordinates") or [])
    report["centres"] = centres
    profile["solved_dimensions"] = report
    return report


PAGE_IDENTITY_AXES = {"x": [1.0, 0.0], "y": [0.0, -1.0]}


def view_transform(decisions: Decisions, options: dict) -> dict | None:
    """The sheet's own axes as page-frame unit vectors, or None when the flow must not assume (PLAN 8.6).

    A confirmed view is the user's own decision and comes first. When there is none, the *product* may make
    the page's axes the sheet's own: that is only true of a sheet whose border was found, is aligned to the
    page, and whose source is not rotated. Everywhere else the answer is None — the caller refuses rather
    than reading part x off page x.
    """
    approved = getattr(decisions, "view", None)
    if approved is not None:
        x_axis = [float(approved.x_page[0]), float(approved.x_page[1])]
        y_axis = [float(approved.y_page[0]), float(approved.y_page[1])]
        # The sheet's axes are a rotation of the page's, never a reflection: a pair whose cross product
        # points the wrong way describes the sheet seen from behind, which this slice cannot build.
        if x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0] > 0:
            raise ValueError("onaylanan görüş ayna oluşturuyor (x/y çifti ters yönlü); arka yüzden görünüş "
                             "bu dilimde desteklenmiyor — varsayım yapılmadı")
        return {"x": x_axis, "y": y_axis,
                "source": "onaylanan görüş" + (f" ({approved.source})" if approved.source else "")}
    product = options.get("sheet_frame") or {}
    if product.get("found") and product.get("aligned") is not False and not product.get("rotation"):
        return {"x": list(PAGE_IDENTITY_AXES["x"]), "y": list(PAGE_IDENTITY_AXES["y"]),
                "source": "pafta çerçevesi bulundu ve sayfa eksenlerine hizalı"}
    return None


def is_page_identity(axes: dict) -> bool:
    """Does this view leave the page's own axes alone? Only then may the plan be built as it always was."""
    return all(abs(axes[key][index] - PAGE_IDENTITY_AXES[key][index]) < 1e-9
               for key in ("x", "y") for index in (0, 1))


def _view_map(options: dict, decisions: Decisions, axes: dict) -> Decisions:
    """Put the build's own copy of the geometry into the sheet's frame (PLAN 8.6-c-2).

    The trace, the interface and the stored decisions all keep page coordinates; only the deep copy a single
    `make_plan` call works on is mapped, so nothing the user sees or saved moves. The constraint core and the
    plan speak x/y, and on a rotated sheet those must be the *sheet's* x/y: with `u = p·x_axis` and
    `v = p·y_axis` (v being the sheet's +y, i.e. up) the identity view reproduces the old numbers exactly.
    """
    x_axis, y_axis = axes["x"], axes["y"]

    def to_view(point) -> list[float]:
        # The mapped frame stays *page-like* (y increases downward): the constraint core reads it that way
        # (`(origin[1] - y)/scale`) and that module is not this slice's to change. Reading the sheet's +y as
        # the mapped -v is what puts the sheet's up where the page's up used to be, so for an upright sheet
        # (y_axis = [0, -1]) v is exactly the page's y and every number below stays where it was.
        px, py = float(point[0]), float(point[1])
        return [px * x_axis[0] + py * x_axis[1], -px * y_axis[0] - py * y_axis[1]]

    canonical_turn = math.degrees(math.atan2(-x_axis[1], x_axis[0]))    # sheet +x in the canonical frame
    page_turn = math.degrees(math.atan2(x_axis[1], x_axis[0]))          # sheet +x in the page frame

    def shift(value, by: float):
        return (float(value) - by + 180.0) % 360.0 - 180.0

    def map_shape(shape: dict) -> None:
        for key in ("start", "end", "center"):
            if shape.get(key) is not None:
                shape[key] = to_view(shape[key])
        for key in ("a", "b"):                                          # contour arcs: canonical degrees
            if shape.get(key) is not None:
                shape[key] = shift(shape[key], canonical_turn)
        for key in ("start_degrees", "end_degrees"):                    # reader primitives: page degrees
            if shape.get(key) is not None:
                shape[key] = shift(shape[key], page_turn)

    for profile in options.get("profiles") or []:
        profile["points"] = [to_view(point) for point in profile.get("points") or []]
        for edge in profile.get("edges") or []:
            map_shape(edge)
    for circle in options.get("circles") or []:
        if circle.get("center") is not None:
            circle["center"] = to_view(circle["center"])
    for primitive in options.get("primitives") or []:
        map_shape(primitive)

    payload = decisions.model_dump(mode="json")
    for binding in payload.get("bindings") or []:
        for role in ("first", "second"):
            end = binding.get(role)
            if end:
                end["x"], end["y"] = to_view([end.get("x", 0.0), end.get("y", 0.0)])
    calibration = payload.get("calibration")
    if calibration:
        calibration["first"] = to_view(calibration["first"])
        calibration["second"] = to_view(calibration["second"])
    return Decisions.model_validate(payload)


def binding_reference(profile: dict, end) -> "constraint_core.PointRef":
    """Resolve one recorded binding end to a core point reference (PLAN §8 P03-a/b, §8.7/§8.8).

    The single resolver: the build (`user_dimensions`) and the gate (`bindings_solvable`) both
    call it, so the questions, the preview and the production path can never disagree about
    whether an end is real (PLAN P04-a item 3).
    """
    edges = profile.get("edges") or []
    kind = getattr(end, "kind", None)
    if kind == "centre":
        return constraint_core.PointRef(kind="circle_center", id=str(end.id))
    # PLAN §8 P03-b.2: the tie belongs to the contour it was chosen in — the same edge id in another
    # contour is a different end, so a recorded profile that is not the current one asks for re-binding.
    if getattr(end, "profile", None) and end.profile != profile.get("id"):
        raise ValueError(f"bağ ucu başka bir konturda seçilmiş ({end.profile}); bu konturda yeniden bağlanmalı")
    raw = str(getattr(end, "id", "") or "")
    edge_key, sep, tail = raw.rpartition(":")
    if not (sep and tail in ("start", "end")):
        # A pre-P03 `edge:<index>` end (or a bare index): the index named the edge the user clicked, and
        # the stored click point says which of that edge's two ends. Honoured only while that edge is
        # still in the contour — never shifted to another corner (PLAN §8 P03-a.1).
        if (edge_key == "edge" and tail.isdigit()) or raw.isdigit():
            index = int(tail if tail.isdigit() else raw)
            if index >= len(edges):
                raise ValueError(f"eski bağ ucu bu konturda yok: {raw}")
            point = [float(getattr(end, "x", 0.0)), float(getattr(end, "y", 0.0))]
            start = [float(v) for v in edges[index]["start"]]
            stop = [float(v) for v in edges[index]["end"]]
            name = f"v{index}" if math.dist(start, point) <= math.dist(stop, point) else f"v{(index + 1) % len(edges)}"
            return constraint_core.PointRef(kind="vertex", id=name)
        raise ValueError(f"bağ ucu kimliği çözülemedi: {raw or '(boş)'}")
    # PLAN §8.7/§8.8 + P03-b.2: the stable edge id names the edge; the stored click point names the
    # physical end, so a reversed traversal (which swaps the labels) keeps the same corner.
    name, reason = resolve_binding_end(edges, end)
    if name is None:
        raise ValueError(reason)
    return constraint_core.PointRef(kind="vertex", id=name)


def make_plan(record: dict) -> GeneralPlan:
    # P01 (PLAN.md): the record's options are the read-only base geometry — a build must never rewrite the
    # drawing the user loaded. Every preparation call works on an independent deep copy (nested dicts/lists
    # included); solved positions and the solve report live on that copy for this call only, so removing a
    # measurement, undoing, or reopening the session brings the original geometry back untouched.
    options=copy.deepcopy(record["options"]); d=Decisions.model_validate(record["decisions"])
    validate_decisions(options,d)
    diagnostics=sketch_diagnostics(options,d)
    if questions(d,diagnostics,options): raise ValueError(" ".join(questions(d,diagnostics,options)))
    # PLAN 8.6: never read part x off page x. Where the sheet's own frame could not be established (no
    # border, a tilted frame, a rotated source) and the user has not confirmed a view, the build stops here
    # instead of assuming; where a *rotated* view was confirmed, the core mapping that would apply it is its
    # own slice (8.6-c-2) and the build stops too — an upright sheet is unaffected and builds as always.
    axes = view_transform(d, options)
    if axes is None:
        raise ValueError("görüş ekseni onaylanmadan üretim başlamaz; sayfa X'i parça X'i varsayılmaz "
                         "(PLAN §8.6): " + str((options.get("sheet_frame") or {}).get("provenance")
                                                or "pafta çerçevesi okunamadı"))
    if not is_page_identity(axes):
        # PLAN 8.6-c-2: rotate this call's own copy into the sheet's frame and re-run the diagnostics there,
        # so the core and the plan speak the sheet's x/y. What the user approved, sees and saved is untouched.
        d = _view_map(options, d, axes)
        diagnostics = sketch_diagnostics(options, d)
    contour = diagnostics.get("contour") or {}
    if contour and contour.get("ok") is False and not d.contour.drop:
        issues = contour.get("issues") or [{}]
        extra = len(issues) - 1
        raise ValueError("kontur geçersiz: " + str(issues[0].get("message", "bilinmeyen sorun"))
                         + (f"; {extra} sorun daha var" if extra > 0 else "")
                         + " — işaretlenen kenarı çıkarıp yeniden deneyin.")
    profile=next(p for p in options["profiles"] if p["id"]==d.profile_id)
    if d.contour.drop:
        # The user's correction, applied before anything is built; the audit runs again on what is left, so a
        # correction that does not actually fix the boundary is refused here and named (PLAN §26.4-A).
        profile=correct_profile(profile, d.contour,
                                join_tolerance_px=RASTER_JOIN_TOLERANCE_PX,
                                mid_join_px=RASTER_JOIN_TOLERANCE_PX / 2.0)
        after=contour_audit.audit_contour(profile.get("edges") or [])
        if after.get("ok") is False:
            first=(after.get("issues") or [{}])[0]
            raise ValueError("düzeltmeden sonra kontur hâlâ geçersiz: "
                             + str(first.get("message", "bilinmeyen sorun"))
                             + f" ({len(after.get('issues') or [])} sorun)")
    cal=d.calibration
    assert cal is not None       # `questions` above refuses without a calibration
    # PLAN P04-a: the scale the part is built at is the user's own calibration, full stop. Printed ties are
    # solved as geometry (below); they never re-scale the sheet, however far their fit is from the drawing.
    scale=math.dist(cal.first,cal.second)/(cal.value*(25.4 if cal.unit=="in" else 1))
    points=profile["points"]
    origin=[min(p[0] for p in points),max(p[1] for p in points)]
    # PLAN §26.4-B: the user's own dimensions are solved before anything is built, and the geometry they
    # determine is the geometry that goes to CAD. The status, the conflicts and the remaining free
    # coordinates are reported, never hidden: this is not a "sharp sketch solution" for the whole contour.
    solution=user_dimensions(profile, options, d, scale, origin)
    if solution is not None and solution.get("status") not in (None, "constrained", "underconstrained"):
        # §26.4-B + PLAN P04: a tie the core cannot measure, or one that cannot hold, stops this revision —
        # no plan, no STEP — and names what to fix. Skipping the measurement and building on would report a
        # part that is not the measured one.
        notes = " ".join(str(note) for note in solution.get("notes") or []) or "ayrıntı yok"
        if solution.get("status") == "unsupported":
            raise ValueError("bağlanan ölçü bu sürümde çözülemiyor (desteklenmiyor): " + notes)
    if solution is not None and solution.get("status") == "conflict":
        ids = ", ".join(", ".join(row or []) for row in solution.get("conflicts") or []) or "kimliksiz"
        raise ValueError("bağlanan ölçüler birlikte tutmuyor (çakışan: " + ids + ")")
    if solution is not None:
        points=profile["points"]
        origin=[min(p[0] for p in points),max(p[1] for p in points)]
    fixed=set((solution or {}).get("user_coordinates") or [])
    def axes_for(point_key):
        return {axis for axis in ("x","y") if f"{point_key}:{axis}" in fixed}
    params={"thickness":{"source":"user","value":d.thickness,"unit":"mm","explanation":"Kullanıcının kalınlık kararı."}}
    for index, row in enumerate(diagnostics.get("rows", [])):
        params[f"binding_{index}"]={"source":"user","value":float(row["value_mm"]),"unit":"mm",
                                    "explanation":(f"Kullanıcının bağladığı basılı ölçü ({row['span_id'] or 'serbest'}); "
                                                   f"ölçek altında çizili {row['drawn_mm']} mm, sapma "
                                                   f"{row['residual_mm']:+.3f} mm.")}
    def value(name,number,user=False):
        params[name]={"source":"user" if user else "assumed","value":float(number),"unit":"mm",
                      "explanation":"Kullanıcı ölçüsü." if user else "Kullanıcının seçtiği kontur ve kalibrasyonla çizimden ölçüldü; basılı ölçü değildir."}
        return name
    def xy(prefix,point,user_axes=None):
        # PLAN §26.4-B: a coordinate the constraint core fixed comes from the user's own measurements, not
        # from the trace; the rest of the point keeps its own source. Nothing is relabelled wholesale.
        return [value(prefix+"_x",(point[0]-origin[0])/scale,bool(user_axes and "x" in user_axes)),
                value(prefix+"_y",(origin[1]-point[1])/scale,bool(user_axes and "y" in user_axes))]
    if profile["kind"]=="circle":
        c=profile["circle"]
        entities=[{"type":"circle","center":xy("outer",c["center"]),"radius":value("outer_radius",c["radius"]/scale)}]
    else:
        entities=[]
        for i,e in enumerate(profile["edges"]):
            key=f"edge_{i}"
            if e["kind"]=="line": entities.append({"type":"line","start":xy(key+"_start",e["start"],axes_for(f"vertex:v{i}")),"end":xy(key+"_end",e["end"],axes_for(f"vertex:v{(i+1)%len(profile['edges'])}"))})
            else: entities.append({"type":"arc","center":xy(key+"_center",e["center"]),"radius":value(key+"_radius",e["radius"]/scale),"start_degrees":e["a"],"end_degrees":e["b"]})
    sketches={"outer":{"entities":entities}}
    # PLAN-25 §38: ortak bağlam buraya kadar hazırdır — nasıl üretileceğine KARAR veren şey kullanıcının
    # oluşturma biçimidir. Burada eskiden olduğu gibi bir extrude'a DÜŞÜLMEZ; strateji yoksa plan yoktur.
    ctx=SimpleNamespace(record=record,options=options,decisions=d,diagnostics=diagnostics,profile=profile,
                        scale=scale,points=points,origin=origin,solution=solution,fixed=fixed,params=params,
                        sketches=sketches,value=value,xy=xy,axes_for=axes_for)
    return dispatch_plan(ctx)


def dispatch_plan(ctx):
    """PLAN-25 §38: explicit strategy dispatch — no default extrude, ever.

    Missing and stale strategies are refused with the same sentences `build_readiness` asks (§41), and
    a geometry-class blacklist is deliberately *not* used: a circle profile builds like any other once
    the user confirms `extrude_profile` (§40). What is refused is the *assumption*, not the shape.
    """
    problems=build_strategy.strategy_questions(ctx.record)
    if problems: raise ValueError(" ".join(problems))
    kind=ctx.decisions.build_strategy.kind
    if kind=="extrude_profile": return compile_extrude_plan(ctx)
    if kind=="revolve_profile": return compile_revolve_plan(ctx)
    if kind=="multi_view_composite": return compile_multiview_plan(ctx)
    raise ValueError(" ".join(build_strategy.strategy_questions(ctx.record))
                     or f"oluşturma biçimi bu sürümde uygulanamıyor: {kind}")


def compile_revolve_plan(ctx):
    """PLAN-25 §38: revolve's own contract point — controlled unsupported until G12.6 builds it."""
    raise ValueError("döndürme (revolve) oluşturma biçimi bu sürümde uygulanamıyor: "
                     "kesit/eksen geometrisi G12.6'da kurulur.")


def compile_multiview_plan(ctx):
    """PLAN-25 §38: multi-view composite's contract point — controlled unsupported until G12.7."""
    raise ValueError("çok görünüşlü birleştirme oluşturma biçimi bu sürümde uygulanamıyor: "
                     "görünüş grafiği ve özellik bağlama G12.7'de kurulur.")


def compile_extrude_plan(ctx):
    """The one strategy this version builds: a profile at a constant thickness (PLAN-25 §35)."""
    options=ctx.options; d=ctx.decisions; profile=ctx.profile; solution=ctx.solution
    params=ctx.params; value=ctx.value; xy=ctx.xy; axes_for=ctx.axes_for; fixed=ctx.fixed
    points=ctx.points; origin=ctx.origin; scale=ctx.scale; diagnostics=ctx.diagnostics; record=ctx.record
    sketches=ctx.sketches
    operations=[{"op":"extrude","id":"base_extrusion","output":"base","sketch":"outer","distance":"thickness"}]
    body="base"
    for i,h in enumerate(d.holes):
        c=next(c for c in options["circles"] if c["id"]==h.circle_id)
        if solution is not None and h.circle_id in (solution.get("centres") or {}):
            # The user's own dimension put this centre where it is (PLAN §26.4-B) — the solved position is
            # what is built, and the traced one is not kept alongside it.
            c={**c,"center":solution["centres"][h.circle_id]}
        key=f"hole_{i}";diameter=value(key+"_diameter",h.diameter,True)
        depth="thickness" if h.kind=="through" else value(key+"_depth",h.depth,True)
        sketches[key]={"offset":"0" if h.kind=="through" else f"thickness - {depth}",
                       "entities":[{"type":"circle","center":xy(key,c["center"],axes_for(f"circle_center:{h.circle_id}")),"radius":f"{diameter} / 2"}]}
        operations.extend([{"op":"extrude","id":key+"_extrude","output":key+"_tool","sketch":key,"distance":depth},
                           {"op":"cut","id":key+"_cut","output":key+"_result","target":body,"tool":key+"_tool"}])
        body=key+"_result"
    return GeneralPlan.model_validate({"source":{"kind":"drawing","ref":record["source"],"sha256":record["source_sha256"]},
            "parameters":params,"sketches":sketches,"operations":operations,"result":body,
            "assumptions":[(f"Ölçek {float(scale):.4f} px/mm — "
                            + (f"bağlanan {len(d.bindings)} basılı ölçüden en küçük karelerle çözüldü."
                               if diagnostics.get("source")=="bindings" else "kullanıcının iki noktalı kalibrasyonundan."))
                           + " Kullanıcı ana konturu, ölçeği ve özellikleri seçti; kontur ve delik merkezleri çizimden izlenen taslaktır."
                           + (f" {len(d.bindings)} basılı ölçü çizimdeki iki noktaya bağlandı, "
                              f"bağlanmayan {len(diagnostics.get('unbound_circles',[]))} daire ve "
                              f"{len(diagnostics.get('unbound_edges',[]))} kenar taslak kalır." if d.bindings else "")
                           + (f" Ölçü çözümü uygulandı: {len(fixed)} koordinat kullanıcının bağladığı ölçülerden"
                              f" geldi, {solution.get('free_count', 0)} koordinat hâlâ çizimden izlenen taslak."
                              if fixed else ""),
                           (f"Birleştirme öncesi en büyük boşluk {profile['join_max_px']:.6f} piksel. "
                           + ("Bağlanan basılı ölçüler tek bir ortak ölçeğe uyduruldu (en küçük kareler); bu, kenarları ayrı ayrı "
                           "hareket ettiren kesin bir eskiz çözümü değildir."
                           if d.bindings else "Basılı ölçülerle ortak ölçek uydurması yapılmadı.")),
                           ("Dış kontur çizimdeki bir dairedir (döner yüz); gövde ve ikinci flanş bu planın kapsamı dışındadır."
                            if profile["kind"] == "circle" else
                            "Kör cepler üst yüzden açılır. Tek görünüşten sabit kalınlıkta gövde kullanıldı.")]})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(record: dict, actor: str, action: str, field: str, value=None, evidence: dict | None = None,
         note: str = "", confidence: str | None = None) -> None:
    """One visible step: who did what, with the evidence that was on screen at the time."""
    entry = {"at": _now(), "revision": record.get("revision", 0), "actor": actor, "action": action,
             "field": field, "value": value, "note": note}
    if evidence:
        entry["evidence"] = evidence
    if confidence:
        entry["confidence"] = confidence
    entries = record.setdefault("log", [])
    entries.append(entry)
    del entries[:-LOG_LIMIT]


def _proposal_note(item: dict) -> str:
    row = item.get("evidence") or {}
    source = (f"{row.get('text') or 'Basılı ölçü'} ({row['span_id']})" if row.get("span_id")
              else "Basılı ölçüye bağlanmamış geometri")
    if item["field"] == "calibration":
        return (f"Ölçek önerisi: {source}, okumanın kendi iki çapası; "
                f"{row.get('px')} px, {row.get('error_px')} px sapma.")
    if item["field"] == "profile_id":
        if row.get("width_mm") is None:
            return f"Dış kontur önerisi: {row.get('rule') or item['value']}."
        return (f"Dış kontur önerisi: {row.get('width_mm')} × {row.get('height_mm')} mm, "
                f"okumanın konturu {row.get('outline_mm')} mm.")
    if item["field"].startswith("hole:"):
        return f"Özellik önerisi: {source} — {row.get('kind_source') or row.get('rule') or 'onay gerekir'}."
    return f"{item['field']} önerisi ({item['confidence']}): {row.get('text')} ({row.get('span_id')}) — {row.get('rule')}."


def _changed_fields(before: dict, after: dict) -> list[tuple[str, object]]:
    """Which decisions an edit moved — one row per field, so the log can name each of them."""
    rows: list[tuple[str, object]] = []
    for field in ("profile_id", "thickness", "trace_acknowledged", "calibration"):
        if before.get(field) != after.get(field):
            rows.append((field, after.get(field)))
    before_holes = {hole["circle_id"]: hole for hole in before.get("holes", [])}
    after_holes = {hole["circle_id"]: hole for hole in after.get("holes", [])}
    for circle_id, hole in after_holes.items():
        if before_holes.get(circle_id) != hole:
            rows.append((f"hole:{circle_id}", hole))
    for circle_id in before_holes:
        if circle_id not in after_holes:
            rows.append((f"hole:{circle_id}", None))
    return rows


def _proposal_match(proposals: list[dict], field: str, value) -> dict | None:
    for item in proposals:
        if item["field"] == field and item["value"] == value:
            return item
    return None


def _audit_summary(folder: Path) -> dict:
    """What the geometry check said, small enough to sit in the log line."""
    path = folder / "plan-audit.json"
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {"passed": audit.get("passed"), "status": audit.get("status"),
            "checks": audit.get("checks", {})}


GEOMETRY_VERSION = 3
"""P01: the version of the base-geometry contract.

v3 compares the reader's *identities* (profile/edge/circle/measurement ids, and the frame) instead of the v2
name-only check, so a changed edge id or measurement id is a mismatch (the audit's F03). A record below the
current version may carry geometry a build already rewrote: `GuidedStore.load` backs it up, re-reads the
source, refreshes the base geometry when the identities still match, and otherwise makes the record
`geometry_stale` and lets the build wait for an explicit re-choice."""


def _geometry_ids(options: dict) -> dict:
    """The reader's *identities*, in its own terms (P01-a.2/P01-a.3).

    Real measurement rows are keyed by `measurements[].id`; there is no `span_id` field there — reading that
    absent name is the audit's F03, which let a measurement-id change pass as "same geometry". Profile
    members, each profile's edge ids *in order* and the circle ids are compared the same way. Coordinates are
    deliberately not identities: an old build moved them, so a numeric difference alone must not read as a
    different drawing (P01-a.4) — `_moved_geometry` reports those separately.
    """
    return {
        "frame": [_round3((options.get("frame") or {}).get("width")),
                  _round3((options.get("frame") or {}).get("height"))],
        "profiles": [{"id": str(profile.get("id")), "kind": profile.get("kind"),
                      "edges": [str(edge.get("id")) for edge in profile.get("edges") or []]}
                     for profile in options.get("profiles") or []],
        "circles": [str(circle.get("id")) for circle in options.get("circles") or []],
        "measurements": [str(row.get("id")) for row in options.get("measurements") or []],
    }


def _round3(value):
    return None if value is None else round(float(value), 3)


def _moved_geometry(old: dict, fresh: dict) -> int:
    """How many stored edge ends / circle centres differ numerically from the re-read drawing.

    The old flow wrote solved coordinates back into `options`; that marker is a refresh, not a mismatch — but
    it belongs in the log, so the refresh is never silent (P01-a.4).
    """
    moved = 0
    for before, after in zip(old.get("profiles") or [], fresh.get("profiles") or []):
        for left, right in zip(before.get("edges") or [], after.get("edges") or []):
            for key in ("start", "end"):
                a = [_round3(v) for v in left.get(key) or []]
                b = [_round3(v) for v in right.get(key) or []]
                if a != b:
                    moved += 1
    for before, after in zip(old.get("circles") or [], fresh.get("circles") or []):
        if ([_round3(v) for v in before.get("center") or []] != [_round3(v) for v in after.get("center") or []]
                or _round3(before.get("radius")) != _round3(after.get("radius"))):
            moved += 1
    return moved


def _geometry_diff(old: dict, fresh: dict) -> list[str]:
    """What the re-read no longer reproduces — identity differences only, short enough for a log line."""
    before, after = _geometry_ids(old or {}), _geometry_ids(fresh or {})
    steps = []
    if before["frame"] != after["frame"]:
        steps.append("çerçeve değişti")
    if [p["id"] for p in before["profiles"]] != [p["id"] for p in after["profiles"]]:
        steps.append("profil kimlikleri değişti")
    else:
        for left, right in zip(before["profiles"], after["profiles"]):
            if left["kind"] != right["kind"]:
                steps.append(f"{left['id']} türü değişti")
            if left["edges"] != right["edges"]:
                steps.append(f"{left['id']} kenar kimlikleri değişti")
    if before["circles"] != after["circles"]:
        steps.append("daire kimlikleri değişti")
    if before["measurements"] != after["measurements"]:
        steps.append("ölçü kimlikleri değişti")
    return steps


def _same_geometry(old: dict, fresh: dict) -> bool:
    """Same identities means the reader still finds the same drawing — only then may the record's base
    geometry be replaced. A mismatch is a reader change: re-ask instead of moving anything."""
    return _geometry_ids(old or {}) == _geometry_ids(fresh or {})


# --- callout layer (PLAN-20 §6–§8): the store boundary around the four callout records -----------

def _transcription_carried(prior: dict | None, row: dict) -> bool:
    """The user's own text or the region they reviewed changed? Then this is a new revision — not a carry."""
    return (prior is not None and prior.get("raw_text") == row.get("raw_text")
            and prior.get("source_region") == row.get("source_region"))


def _target_carried(prior: dict | None, row: dict) -> bool:
    """A confirmation carried along untouched — same selection, no explicit `reconfirm` request.

    Server-owned fields (fingerprint, geometry version, profile) and the evidence text are *not*
    part of the comparison: a carried row keeps its persisted bytes, so client-side drift in those
    fields can never rewrite an old confirmation into a new context, and editing the evidence text
    is never a re-confirmation mechanism — only the explicit request is (PLAN-20 düzeltme turu 1).
    """
    return (prior is not None and not row.get("reconfirm")
            and prior.get("target_kind") == row.get("target_kind")
            and prior.get("target_ids") == row.get("target_ids")
            and prior.get("transcription_revision") == row.get("transcription_revision")
            and prior.get("parser_version") == row.get("parser_version"))


def _merge_callout_defaults(record: dict, decisions):
    """PLAN-20 §8.7 + PLAN-21 §6.1: for the callout fields only, a missing key keeps the stored value
    while an explicit list (an empty one included) is the client's own statement. Every other field
    keeps the old save contract exactly as it was."""
    if not isinstance(decisions, dict):
        return decisions
    # PLAN §9: a reading is the server's own derivation — a client cannot send one, and a payload that
    # carries the derived rows is refused rather than having them ignored in silence.
    if "callout_parses" in decisions:
        raise ValueError("callout_parses sunucunun türettiği okumadır; istemci okuma gönderemez (PLAN §9)")
    merged = dict(decisions)
    stored = record.get("decisions") or {}
    for key in ("transcriptions", "callout_targets", "manual_callouts", "callout_reviews"):
        if key not in merged:
            merged[key] = stored.get(key, [])
    return merged


def _recorded_endpoint(edges: list[dict], target: str) -> tuple[str, str]:
    """One vertex target → its stable `(edge_id, start|end)` identity *in the recorded context*
    (G1R2-01 kimlik kuralı). `v{index}` is the display name for the start of that edge index in this
    very list and is translated here — never re-indexed against a corrected list, so a removal can
    never silently move it to a different physical corner. A bare index without a stored click point
    stays ambiguous and is not accepted."""
    raw = str(target)
    if raw.startswith("v") and raw[1:].isdigit():
        index = int(raw[1:])
        if edges and 0 <= index < len(edges):
            return str(edges[index].get("id")), "start"
        raise ValueError(f"hedef uç kimliği bu profilin kenarlarında yok: {target}")
    edge_key, separator, tail = raw.rpartition(":")
    if separator and tail in ("start", "end") and any(str(edge.get("id")) == edge_key for edge in edges):
        return edge_key, tail
    raise ValueError(f"hedef uç kimliği bu profilin kenarlarında yok: {target}")


def _endpoint_point(edges: list[dict], identity: tuple[str, str], target: str) -> list[float]:
    """The identity's point in the contour this save leaves (the corrected edge list). An endpoint
    the user's own correction removes has lost its meaning: re-selection is asked for, never a
    silent re-bind (G1R2-01)."""
    edge_key, tail = identity
    edge = next((item for item in edges if str(item.get("id")) == edge_key), None)
    if edge is None:
        raise ValueError(f"hedef uç kimliği bu düzeltmeden sonra konturda yok (yeniden seçin): {target}")
    return [float(value) for value in edge[tail]]


def _refresh_callout_parses(record: dict) -> None:
    """Derive the one current reading per callout (PLAN §9) — derived data, never a decision.

    A saved text gets exactly one reading, computed by the real parser, bound to the transcription
    revision it was computed from and to `CALLOUT_PARSER_VERSION`. The G4 model:

    * a row for the current revision+version is the record's authority and is never rewritten;
    * a row that can no longer be current (the text moved on, the region moved, the parser version
      changed) is *replaced* by the fresh one — its text lives in the decisions (and in history), so
      nothing is lost, and a reading is not a user act: no history step, no log line;
    * a text whose region has moved away keeps its old row and stays `stale`/`region_changed` — no
      reading is fabricated for a box the user has not looked at;
    * with no transcription at all the key is left exactly as it was (an old record keeps its shape).
    """
    decisions = record.get("decisions") or {}
    transcriptions = {row.get("callout_id"): row for row in decisions.get("transcriptions") or []}
    regions = {row["id"]: row.get("region") for row in callout_models.effective_callouts(record)}
    unit = callout_models.sheet_unit(record)
    rows = list(record.get("callout_parses") or [])
    for callout_id, transcription in transcriptions.items():
        region = regions.get(callout_id)
        if region is None:
            continue                       # olmayan bir callout için okuma yazılmaz
        stored = [float(value) for value in transcription.get("source_region") or []]
        if [float(value) for value in region] != stored:
            continue                       # metin okunduğu alandan ayrıldı: okuma yenilenmez
        revision = transcription.get("revision")
        mine = [row for row in rows if row.get("callout_id") == callout_id]
        if any(row.get("transcription_revision") == revision
               and row.get("parser_version") == callout_models.CALLOUT_PARSER_VERSION for row in mine):
            continue                       # güncel okuma kayıt için otoritedir; yeniden yazılmaz
        rows = [row for row in rows if row.get("callout_id") != callout_id]
        rows.append(callout_parse.semantic_parse(transcription, sheet_unit=unit).model_dump(mode="json"))
    if rows != (record.get("callout_parses") or []):
        record["callout_parses"] = rows


def _prepare_callouts(record: dict, decisions: Decisions) -> Decisions:
    """The server's own derivations at the save boundary (PLAN-20 §6.3/§6.5).

    `normalized_text` is the server's separate field, re-derived from the raw text; a transcription
    whose text or region changed gets the *new* revision id (a client cannot keep an old one alive
    across an edit) while an untouched one keeps its stored id. A new target confirmation is pinned
    to the geometry/context fingerprint this save is happening in; a carried one stays byte-for-byte
    as it was confirmed.
    """
    stored = record.get("decisions") or {}
    prior_transcriptions = {row.get("callout_id"): row for row in stored.get("transcriptions") or []}
    prior_targets = {row.get("callout_id"): row for row in stored.get("callout_targets") or []}
    next_revision = (record.get("revision") or 0) + 1
    payload = decisions.model_dump(mode="json")
    # Pin against the context this very save establishes — a profile switch and a confirmation can
    # arrive in one payload, and the fingerprinted context must be the new one (PLAN-20 §6.4).
    key = callout_models.geometry_key(record, payload)
    for row in payload.get("transcriptions") or []:
        prior = prior_transcriptions.get(row.get("callout_id"))
        if prior is not None and _transcription_carried(prior, row):
            row["revision"] = prior.get("revision", 0)
        else:
            row["revision"] = next_revision
        row["normalized_text"] = callout_models.normalize_text(row["raw_text"])
    prepared_targets: list[dict] = []
    for row in payload.get("callout_targets") or []:
        prior = prior_targets.get(row.get("callout_id"))
        if prior is not None and _target_carried(prior, row):
            prepared_targets.append(dict(prior))        # kalıcı kayıt aynen korunur; istemci sürüklenmesi yazılmaz
            continue
        row = dict(row)
        if row.get("target_kind") == "vertex_pair":
            # G1R2-01 kimlik kuralı: yeni onay kayıtlı bağlamdaki kararlı uç kimliğiyle saklanır —
            # `v{index}` düzeltilmiş listenin yeni indisine değil, gerçek kenar ucuna çevrilir.
            profile = next((item for item in (record.get("options") or {}).get("profiles") or []
                            if item.get("id") == payload.get("profile_id")), None)
            edges = (profile or {}).get("edges") or []
            row["target_ids"] = [f"{edge_id}:{tail}" for edge_id, tail in
                                 (_recorded_endpoint(edges, target)
                                  for target in row.get("target_ids") or [])]
        row["geometry_key"] = key
        row["geometry_version"] = record.get("geometry_version")
        row["profile_id"] = payload.get("profile_id")   # pinlenen bağlam = bu save'in bağlamı
        prepared_targets.append(row)
    payload["callout_targets"] = prepared_targets
    return Decisions.model_validate(payload)


def _consume_reconfirm(decisions: Decisions) -> Decisions:
    """The explicit re-confirmation request is a one-shot signal (PLAN-20 düzeltme turu 1): it stays
    on the row until validation has seen it, then it is consumed here and never persisted as true."""
    payload = decisions.model_dump(mode="json")
    for row in payload.get("callout_targets") or []:
        row["reconfirm"] = False
    return Decisions.model_validate(payload)


def _carried_row(rows: list[dict] | None, key_field: str, identity):
    """The one stored row a payload row claims to be carrying — or nothing."""
    return next((row for row in rows or [] if row.get(key_field) == identity), None)


def _same_stored_decision(model, stored_row: dict | None, row: dict) -> bool:
    """PLAN-22 §4.2: `/save` may only carry a stored G3 row along, verbatim.

    Judged through the schema's own normalization on both sides, so a client cannot change a field the
    model reads back differently (an id, a source digest, a page, a region, a revision — or carried
    evidence drift). A stored row the schema cannot read is not the same decision as this one.
    """
    if stored_row is None:
        return False
    try:
        return (model.model_validate(stored_row).model_dump(mode="json")
                == model.model_validate(row).model_dump(mode="json"))
    except ValidationError:
        return False


def _validate_callouts(record: dict, decisions: Decisions, produced=None) -> None:
    """Store-boundary checks Pydantic alone cannot make (PLAN-20 §6.5; PLAN-22 §4/§5).

    Every check runs against the effective view *this operation would leave* — the base detections plus
    the user's own regions, with the pending region overrides and ignore decisions applied — never
    merely against the stored record. Rows the payload carries along untouched are not re-judged, which
    is what keeps a stale record inspectable and an unrelated edit unblocked. New or changed G3 rows are
    judged, and each row-owning command (`add_region`, `edit_region`, `set_ignored`, `set_disposition`,
    `transcribe`) is
    the only writer of its own list: what `/save` did not merely carry, it may not invent (G3R-01).
    A new confirmation is judged on the freshness of the text and parse it binds to, in the same terms
    the public state shows — a moved region or an ignored callout is an explicit refusal (G3R-02).
    `produced` names the rows a validated command wrote in this very operation.
    """
    produced = set(produced or ())
    stored = record.get("decisions") or {}
    payload = decisions.model_dump(mode="json")
    candidates = {row.get("id"): row
                  for row in callout_models.effective_callouts({**record, "decisions": payload})}
    source = record.get("source_sha256")
    parses = record.get("callout_parses") or []
    expected = callout_models.CALLOUT_PARSER_VERSION
    prior_transcriptions = {row.get("callout_id"): row for row in stored.get("transcriptions") or []}
    prior_targets = {row.get("callout_id"): row for row in stored.get("callout_targets") or []}
    transcriptions = {row.get("callout_id"): row for row in payload.get("transcriptions") or []}

    for row in payload.get("manual_callouts") or []:
        manual_id = row.get("id")
        if ("manual_callouts", manual_id) in produced:
            continue
        if not _same_stored_decision(callout_models.ManualCalloutDecision,
                                     _carried_row(stored.get("manual_callouts"), "id", manual_id), row):
            raise ValueError("manual callout alanını yalnız 'add_region' ekler; kayıtlı alanın kimliği, "
                             f"kaynağı, sayfası ve bölgesi yalnız 'edit_region' ile düzeltilir: {manual_id}")
    for row in payload.get("callout_reviews") or []:
        callout_id = row.get("callout_id")
        if ("callout_reviews", callout_id) in produced:
            continue
        if not _same_stored_decision(callout_models.CalloutReviewDecision,
                                     _carried_row(stored.get("callout_reviews"), "callout_id", callout_id), row):
            raise ValueError("gözden geçirme kararı yalnız 'set_ignored'/'set_unbindable'/'set_disposition'/"
                             f"'bulk_set_ignored'/'edit_region' komutlarıyla değişir: {callout_id}")

    for row in payload.get("transcriptions") or []:
        callout_id = row.get("callout_id")
        if _transcription_carried(prior_transcriptions.get(callout_id), row):
            continue
        _require_callout(candidates, source, callout_id)
        current = candidates[callout_id]
        if current.get("page_index") != 0:
            raise ValueError(f"bu sürümde callout metni yalnız 0. sayfada kaydedilebilir: {callout_id}")
        if current.get("ignored"):
            raise ValueError("yok sayılan bir callout'a metin yazılamaz; önce geri alın")
        if ([float(value) for value in row.get("source_region") or []]
                != [float(value) for value in current.get("region") or []]):
            raise ValueError("metnin kaynak bölgesi bu callout'un etkin bölgesi değil; bölgeyi "
                             f"'edit_region' düzeltir: {callout_id}")

    for row in payload.get("callout_targets") or []:
        if _target_carried(prior_targets.get(row.get("callout_id")), row):
            continue
        callout_id = row.get("callout_id")
        _require_callout(candidates, source, callout_id)
        # PLAN-22 §5.2: an ignored callout is not a target candidate at all — named here so the user
        # hears the real reason rather than the missing-text one behind it.
        if candidates[callout_id].get("ignored"):
            raise ValueError(f"yok sayılan bir callout'un hedefi onaylanamaz; önce geri alın: {callout_id}")
        transcription = transcriptions.get(callout_id)
        if transcription is None:
            raise ValueError(f"hedef onayı güncel bir transcription gerektirir: {callout_id}")
        if row.get("transcription_revision") != transcription.get("revision"):
            raise ValueError(f"hedef onayı güncel transcription revision'ına bağlanmalı: {callout_id}")
        if row.get("parser_version") != expected:
            raise ValueError(f"hedef onayı beklenen parser sürümüne bağlanmalı ({expected}): {callout_id}")
        exact = [item for item in parses if item.get("callout_id") == callout_id
                 and item.get("transcription_revision") == transcription.get("revision")
                 and item.get("parser_version") == row.get("parser_version")]
        if not exact:
            raise ValueError(f"hedef onayı için geçerli parse yok: {callout_id}")
        # Düzeltme turu 3: tazelik hesabı ile anlamsal geçerlilik ayrıdır — başarısız ya da çelişkili
        # bir parse, hiçbir hesapta geçerli hedef onayına dayanak olamaz.
        distinct = {json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) for item in exact}
        if len(distinct) > 1:
            raise ValueError(f"aynı kimlikli çelişkili parse kayıtları hedef onaya dayanak olamaz: {callout_id}")
        if exact[0].get("status") != "parsed":
            raise ValueError(f"parse durumu '{exact[0].get('status')}' iken hedef onayı kaydedilemez: {callout_id}")
        _check_target_geometry(record, row, payload)
        count = exact[0].get("count")
        targets = set(row.get("target_ids") or [])
        if count is not None and len(targets) != count:
            raise ValueError(f"parse'taki adet ({count}) ile benzersiz hedef sayısı "
                             f"({len(targets)}) uyuşmuyor: {callout_id}")
        # PLAN-22 §5.1/§5.2 (G3R-02): the confirmation stands only on a text and a parse that are
        # still current for the decisions this save leaves. The same freshness rule the public state
        # shows (`callout_state`) — a moved region, an ignored callout, a staler text or parse refuses
        # here, while a *carried* confirmation above is never re-judged.
        state = callout_models.callout_state(record, callout_id, decisions=payload)
        if state is None:
            raise ValueError(f"bu oturumda böyle bir callout yok: {callout_id}")
        if state["transcription"]["state"] != "current":
            raise ValueError(f"hedef onayı güncel bir transcription gerektirir "
                             f"({state['transcription']['reason']}): {callout_id}")
        if state["parse"]["state"] != "current":
            raise ValueError(f"hedef onayı güncel bir parse gerektirir "
                             f"({state['parse']['reason']}): {callout_id}")


def _require_callout(candidates: dict, source: str | None, callout_id: str) -> None:
    """The callout must exist *in this session* — including a region the user drew themselves.

    PLAN-21 §6.2: the base machine list is not the only source of truth any more, so the check runs
    on the effective list (`effective_callouts`); otherwise a manual callout could never be written
    to. Borrowing another session's id or source digest is still refused here.
    """
    row = candidates.get(callout_id)
    if row is None:
        raise ValueError(f"bu oturumda böyle bir callout yok: {callout_id}")
    if row.get("source_digest") != source:
        raise ValueError(f"callout bu oturumun kaynağına ait değil: {callout_id}")


# PLAN-21 §4 (G1R3-01): two selected ends are the *same physical point* only within the sheet-level
# "same point" tolerance the contour audit itself uses to tell an endpoint from an interior crossing.
# The 20 px repair budget answers a different question (how far a broken contour's closure may miss)
# and never says two measured ends are one point.
ENDPOINT_IDENTITY_TOLERANCE_PX = contour_audit.TOLERANCE_PX


def same_physical_point(first, second) -> bool:
    """Whether two endpoints name one and the same physical point on the sheet (PLAN-21 §4).

    Sheet pixels, compared with the contour audit's own point-equality tolerance — the same value it
    uses to decide that a join has met rather than merely passed close, so "one point" means the same
    thing everywhere. Deliberately *not* `RASTER_JOIN_TOLERANCE_PX`: that is how far a broken
    contour's closure may be repaired, and using it here refused genuinely distinct short measures.
    """
    return math.dist(first, second) <= ENDPOINT_IDENTITY_TOLERANCE_PX


def _check_target_geometry(record: dict, row: dict, payload: dict) -> None:
    """PLAN-20 §6.5 + düzeltme turu 2 (G1R2-01): the ids must name real geometry, of the right type,
    in the profile *this save* selects — and through the contour *this save's own correction
    leaves*, not the raw traced list. The correction is applied exactly the way the build applies
    it, in a working copy; a removal is refused with an explicit re-selection ask. Physical equality
    is a small point tolerance (`same_physical_point`, PLAN-21 §4) — never the repair budget and
    never a raw index."""
    options = record.get("options") or {}
    circles = {str(circle.get("id")) for circle in options.get("circles") or []}
    if row.get("target_kind") in ("circle", "circle_group"):
        missing = [target for target in row.get("target_ids") or [] if target not in circles]
        if missing:
            raise ValueError(f"hedef geometri bulunamadı: {', '.join(missing)}")
        return
    profile = next((item for item in options.get("profiles") or [] if item.get("id") == payload.get("profile_id")), None)
    if profile is None:
        raise ValueError(f"hedef uç kimliği bu profilin kenarlarında yok: "
                         f"{(row.get('target_ids') or [''])[0]}")
    edges = profile.get("edges") or []
    targets = list(row.get("target_ids") or [])
    identities = [_recorded_endpoint(edges, target) for target in targets]
    try:
        corrected = correct_profile(profile, ContourFix.model_validate(payload.get("contour") or {}),
                                    join_tolerance_px=RASTER_JOIN_TOLERANCE_PX,
                                    mid_join_px=RASTER_JOIN_TOLERANCE_PX / 2.0)
    except ValueError as error:
        raise ValueError(f"etkin kontur çözümlenemedi ({error}): hedef onayı kaydedilemez") from None
    points = [_endpoint_point(corrected.get("edges") or [], identity, target)
              for identity, target in zip(identities, targets)]
    if same_physical_point(points[0], points[1]):
        raise ValueError(f"vertex_pair aynı fiziksel noktayı iki kez seçemez: {targets}")


def _strategy_fingerprint(value) -> dict | None:
    """One comparable form of a strategy row: `None`, or the decision's own validated fields.

    The public state hands the client the server's row, so a client that echoes it back carries it
    unchanged — that is the only shape `/save` may post (PLAN-25 §36). Comparison is by **value**, not
    by JSON spelling (G12R-01): the browser's own round trip turns the server's `10.0` evidence into
    `10`, and the same decision must not read as a forged one. `10.0 == 10` and key order never matter
    here; `strategy_key`/`geometry_version` are typed fields, so an invented key still differs.
    """
    if value in (None, {}):
        return None
    if not isinstance(value, dict):
        raise ValueError("oluşturma biçimi bir nesne ya da null olmalı")
    try:
        return build_strategy.BuildStrategyDecision.model_validate(value).model_dump(mode="json")
    except ValidationError as error:
        raise ValueError("oluşturma biçimi bu şemaya uymuyor: " + str(error)) from error


def _refuse_forged_strategy(record: dict, decisions: dict) -> None:
    """PLAN-25 §36: `/save` may carry the stored strategy; it may not author one.

    `strategy_key` and `geometry_version` are pinned by the server (that is what makes staleness
    decidable), so the only writer of the row is the `set_build_strategy` command. A payload that
    invents or edits a strategy is refused by name rather than silently ignored — the same contract
    `/save` already has for rows the server derives.
    """
    stored = _strategy_fingerprint((record.get("decisions") or {}).get("build_strategy"))
    posted = _strategy_fingerprint(decisions.get("build_strategy"))
    if stored != posted:
        raise ValueError("oluşturma biçimi yalnız `set_build_strategy` komutuyla yazılır; "
                         "istemci strategy_key/geometry_version uyduramaz")


def _normalized_decisions(record: dict) -> dict:
    """The stored decisions with the schema's own defaults filled in — the one side the write and the
    byte-level no-op check both compare against, so "nothing changed" never inflates history."""
    return Decisions.model_validate(record["decisions"]).model_dump(mode="json")


def _stamp_callout_version(record: dict) -> None:
    """PLAN-20 §8.2 + PLAN-22 §6 (G3R-03): the callout layer carries its own version.

    The stamp lands on the one path that really writes decisions to disk, and only there: a record
    that is merely loaded, or a byte-identical no-op save, is never rewritten, so an older session
    keeps its bytes until the user really decides something. On a real write the record moves to the
    current callout schema — from an older stamp or from no stamp at all — while a record already at
    the current version, or at a *newer* unknown one, is left exactly as it is: a future schema is
    never silently downgraded. Not a user act: no revision, history step or log entry of its own, and
    it never moves `geometry_version`.
    """
    version = record.get("callout_schema_version")
    if version is not None and version >= callout_models.CALLOUT_SCHEMA_VERSION:
        return
    record["callout_schema_version"] = callout_models.CALLOUT_SCHEMA_VERSION


def _confirmation_context_same(prior: dict, row: dict) -> bool:
    """G1R2-02: a carried confirmation — same selection *and* same approved context. Any change to the
    geometry context (fingerprint/version/profile) or to the transcription/parse binding is a real
    (re-)confirmation and must reach the log; incidental evidence drift is neither."""
    return all(prior.get(field) == row.get(field) for field in
               ("target_kind", "target_ids", "transcription_revision", "parser_version",
                "geometry_key", "geometry_version", "profile_id"))


def _log_callout_changes(record: dict, before: dict, payload: dict, produced=None) -> None:
    """The user's own callout acts become user events (PLAN-20 §7/§9-G1.5); the freshness the server
    computes is not an event. G1 has no parser — a parse is never logged as if it had happened.

    PLAN-22 §4.7: a validated command already names its own act (its row rides in `produced`), so the
    common diff does not log that act a second time; clearing a list, removing a region the user drew
    and taking a review decision back *are* real acts and are recorded here even though `/save` is
    their only path.
    """
    produced = set(produced or ())
    before_transcriptions = {row.get("callout_id"): row for row in before.get("transcriptions") or []}
    after_transcriptions = {row.get("callout_id"): row for row in payload.get("transcriptions") or []}
    for callout_id, row in after_transcriptions.items():
        if ("transcriptions", callout_id) in produced:
            continue
        prior = before_transcriptions.get(callout_id)
        evidence = {"callout_id": callout_id, "source_region": row.get("source_region")}
        if prior is None:
            _log(record, "user", "transcribe", f"callout:{callout_id}", row.get("raw_text"), evidence,
                 "Kullanıcı callout metnini yazdı.")
        elif prior.get("raw_text") != row.get("raw_text") or prior.get("source_region") != row.get("source_region"):
            _log(record, "user", "edit_transcription", f"callout:{callout_id}", row.get("raw_text"), evidence,
                 "Kullanıcı callout metnini düzenledi.")
    for callout_id in before_transcriptions:
        if callout_id not in after_transcriptions:
            _log(record, "user", "veto", f"callout:{callout_id}", None, None,
                 "Kullanıcı callout metnini kaldırdı.")
    before_targets = {row.get("callout_id"): row for row in before.get("callout_targets") or []}
    after_targets = {row.get("callout_id"): row for row in payload.get("callout_targets") or []}
    for callout_id, row in after_targets.items():
        prior = before_targets.get(callout_id)
        if prior is not None and _confirmation_context_same(prior, row):
            continue
        _log(record, "user", "confirm_target", f"callout:{callout_id}",
             {"kind": row.get("target_kind"), "ids": row.get("target_ids")},
             {"callout_id": callout_id, "geometry_key": row.get("geometry_key"),
              "profile_id": row.get("profile_id"),
              "transcription_revision": row.get("transcription_revision"),
              "parser_version": row.get("parser_version")},
             "Kullanıcı callout hedefini onayladı.")
    for callout_id in before_targets:
        if callout_id not in after_targets:
            _log(record, "user", "veto", f"callout:{callout_id}", None, None,
                 "Kullanıcı callout hedef onayını kaldırdı.")
    before_manual = {row.get("id"): row for row in before.get("manual_callouts") or []}
    after_manual = {row.get("id"): row for row in payload.get("manual_callouts") or []}
    for manual_id in before_manual:
        if manual_id not in after_manual:
            _log(record, "user", "veto", f"callout:{manual_id}", None, None,
                 "Kullanıcı çizdiği callout alanını kaldırdı.")
    before_reviews = {row.get("callout_id"): row for row in before.get("callout_reviews") or []}
    after_reviews = {row.get("callout_id"): row for row in payload.get("callout_reviews") or []}
    for callout_id, prior in before_reviews.items():
        if callout_id in after_reviews or ("callout_reviews", callout_id) in produced:
            continue
        if prior.get("ignored"):
            _log(record, "user", "restore_callout", f"callout:{callout_id}", None, {"callout_id": callout_id},
                 "Kullanıcı bu callout'u yeniden değerlendirmeye aldı; metni silinmedi.")
        if prior.get("region_override"):
            _log(record, "user", "veto", f"callout:{callout_id}", None, {"callout_id": callout_id},
                 "Kullanıcı bölge düzeltmesini kaldırdı; tespit edilen alan yeniden geçerli.")


# --- G3 user commands (PLAN-21 §6.4): one command, one history step, one revision ---------------

_CALLOUT_COMMANDS = ("add_region", "edit_region", "set_ignored", "set_unbindable", "set_disposition",
                     "set_ignored_many", "bulk_set_ignored", "transcribe")

# G9 UX turu: one bulk decision may close many callouts at once, but never an unbounded number —
# the same order of magnitude the review import already accepts.
BULK_IGNORE_LIMIT = 200


def _next_callout_revision(record: dict) -> int:
    """The save's own revision id for a new user record — the same rule the transcription uses."""
    return (record.get("revision") or 0) + 1


def _upsert(rows: list[dict], key_field: str, row: dict) -> list[dict]:
    """Replace the one row with this key where it already sits, else append — order is data."""
    rows = [dict(item) for item in rows]
    index = next((i for i, item in enumerate(rows) if item.get(key_field) == row.get(key_field)), None)
    if index is None:
        rows.append(row)
    else:
        rows[index] = row
    return rows


def _effective_row(record: dict, decisions: dict, callout_id: str) -> dict:
    """The one effective callout a command names, judged against *this command's* decisions."""
    view = callout_models.effective_callouts({**record, "decisions": decisions})
    row = next((item for item in view if item.get("id") == callout_id), None)
    if row is None:
        raise ValueError(f"bu oturumda böyle bir callout yok: {callout_id}")
    if row.get("source_digest") != record.get("source_sha256"):
        raise ValueError(f"callout bu oturumun kaynağına ait değil: {callout_id}")
    return row


def _review_passthrough(current: dict, **changes) -> dict:
    """The review fields a command must carry over because it did not touch them (G12.1).

    Every scope verdict — ignored, unbindable, disposition + its citation — survives a command that
    only corrects the region or the text. A command that *does* decide one of them says so
    explicitly; nothing is ever silently dropped by a neighbouring edit.
    """
    carried = {key: current.get(key) for key in ("ignored", "unbindable", "disposition",
                                                 "duplicate_of", "disposition_reason",
                                                 "duplicate_pin")}
    carried.update(changes)
    return carried


def _set_review(record: dict, decisions: dict, callout_id: str, *,
                region_override: list[float] | None, ignored: bool, unbindable: bool = False,
                disposition: "callout_models.DispositionName | None" = None, duplicate_of: str | None = None,
                disposition_reason: str | None = None, duplicate_pin: dict | None = None) -> None:
    """Write the one review row for a callout — or remove it when every decision is taken back.

    An unchanged decision keeps its stored revision, so repeating a command is a true no-op rather
    than a rewrite that would inflate history (PLAN-21 §6.4). `unbindable` is the G6 verdict "this
    callout cannot be bound"; `disposition` is the G12.1 contract built on the same idea:

    * `not_model_input` / `redundant` — settled scope claims (`redundant` cites its dayanak);
    * `build_relevant_unsupported` — a real fact this version cannot apply. It is written *and*
      carried into readiness, where it blocks the build: naming the gap is not closing it
      (PLAN-24 §11 — this is the bug the G11 run measured).
    """
    stored = list(decisions.get("callout_reviews") or [])
    prior = next((item for item in stored if item.get("callout_id") == callout_id), None)
    if (region_override is None and not ignored and not unbindable
            and disposition is None and duplicate_of is None and disposition_reason is None
            and duplicate_pin is None):
        decisions["callout_reviews"] = [item for item in stored if item.get("callout_id") != callout_id]
        return
    same = (prior is not None and prior.get("region_override") == region_override
            and bool(prior.get("ignored")) == bool(ignored)
            and bool(prior.get("unbindable")) == bool(unbindable)
            and prior.get("disposition") == disposition
            and (prior.get("duplicate_of") or None) == (duplicate_of or None)
            and (prior.get("disposition_reason") or None) == (disposition_reason or None)
            and (prior.get("duplicate_pin") or None) == (duplicate_pin or None))
    revision = (prior or {}).get("revision", 0) if same else _next_callout_revision(record)
    row = callout_models.CalloutReviewDecision(callout_id=callout_id, region_override=region_override,
                                               ignored=bool(ignored), unbindable=bool(unbindable),
                                               disposition=disposition, duplicate_of=duplicate_of,
                                               disposition_reason=disposition_reason,
                                               duplicate_pin=duplicate_pin,
                                               revision=revision)
    decisions["callout_reviews"] = _upsert(stored, "callout_id", row.model_dump(mode="json"))


def _apply_callout_command(record: dict, decisions: dict, action: str, payload: dict,
                           actor: str = "user") -> tuple[list[tuple], list[tuple]]:
    """One G3 user command → the working decisions plus the log events only it can name.

    Everything the client sends is checked or replaced here: the region against the one coordinate
    contract, the ids against this session's own effective callouts, and the identity/source/page/
    revision fields are the server's. The second half of the answer names the rows this command is the
    only writer of (`produced`), so the shared commit path can let its own act through the ownership
    check and never logs one act twice (PLAN-22 §4.1/§4.7). It writes nothing and takes no lock —
    `GuidedStore.save` commits the result through the one save path (validation, no-op, history,
    revision, log).
    """
    if action == "add_region":
        if payload.get("page_index", 0) != 0:
            raise ValueError("bu sürümde callout alanı yalnız 0. sayfada çizilebilir")
        region = callout_models.check_region(payload.get("region"))
        row = callout_models.ManualCalloutDecision(
            id=f"{callout_models.MANUAL_ID_PREFIX}{uuid.uuid4().hex}",
            source_digest=record["source_sha256"], page_index=0, region=region,
            revision=_next_callout_revision(record))
        decisions["manual_callouts"] = _upsert(decisions.get("manual_callouts") or [], "id",
                                               row.model_dump(mode="json"))
        return ([("add_callout_region", f"callout:{row.id}", region,
                  {"callout_id": row.id, "page_index": 0, "region": region},
                  "Kullanıcı çizim üzerinde yeni bir callout alanı çizdi.")],
                [("manual_callouts", row.id)])

    if action == "set_ignored_many":
        # G9 UX turu: the burden the plate run measured — one click per out-of-scope candidate — gets
        # one *explicit* action that closes every still-undecided callout in a single history step.
        # Two properties make it safe rather than a silent filter: it acts only on callouts with no
        # decision at all (a written text or an earlier scope verdict is never overridden), and it is
        # refused whole — a bulk action must not report success while quietly skipping a row.
        ids = payload.get("callout_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError("toplu kapsam kararı için callout kimlikleri listesi gerekli")
        if any(not isinstance(item, str) or not item for item in ids):
            raise ValueError("toplu kapsam kararı kimlikleri metin olmalı")
        if len(set(ids)) != len(ids):
            raise ValueError("toplu kapsam kararı aynı kimliği iki kez taşıyamaz")
        if len(ids) > BULK_IGNORE_LIMIT:
            raise ValueError(f"toplu kapsam kararı tek adımda en çok {BULK_IGNORE_LIMIT} callout kapatır")
        for callout_id in ids:
            row = _effective_row(record, decisions, callout_id)
            decided = bool(row["ignored"]) or bool(row.get("unbindable")) or row.get("disposition") is not None or any(
                item.get("callout_id") == callout_id for item in decisions.get("transcriptions") or [])
            if decided:
                raise ValueError(f"toplu kapsam kararı yalnız henüz karara bağlanmamış callout'lara "
                                 f"uygulanır: {callout_id}")
        events = []
        for callout_id in ids:
            row = _effective_row(record, decisions, callout_id)
            _set_review(record, decisions, callout_id, region_override=row["region_override"],
                        **_review_passthrough(row, ignored=True, unbindable=False,
                                              disposition="not_model_input", duplicate_of=None,
                                              disposition_reason=None))
            events.append(("ignore_callout", f"callout:{callout_id}", None,
                           {"callout_id": callout_id, "bulk": True, "disposition": "not_model_input"},
                           "Kullanıcı bu callout'u 'modele ait değil' olarak sınıflandırdı "
                           "(toplu kapsam kararı)."))
        return events, [("callout_reviews", callout_id) for callout_id in ids]

    if action == "bulk_set_ignored":
        # UX-01 B (plan §7): the atomic bulk scope decision. One explicit request closes every
        # selected row in ONE revision, ONE history step, ONE undo and ONE audit event — never N
        # sequential per-row writes. Validation is all-or-nothing: an unknown or foreign id refuses
        # the whole action; an empty list is refused; rows that already carry the requested verdict
        # are a no-op *inside* the same action (they don't fail it and they don't rewrite history).
        ids = payload.get("callout_ids")
        ignored = payload.get("ignored")
        if not isinstance(ignored, bool):
            raise ValueError("toplu kapsam kararı true/false olmalı")
        if not isinstance(ids, list) or not ids:
            raise ValueError("toplu kapsam kararı için callout kimlikleri listesi gerekli")
        if any(not isinstance(item, str) or not item for item in ids):
            raise ValueError("toplu kapsam kararı kimlikleri metin olmalı")
        if len(set(ids)) != len(ids):
            raise ValueError("toplu kapsam kararı aynı kimliği iki kez taşıyamaz")
        if len(ids) > BULK_IGNORE_LIMIT:
            raise ValueError(f"toplu kapsam kararı tek adımda en çok {BULK_IGNORE_LIMIT} callout kapatır")
        for callout_id in ids:
            _effective_row(record, decisions, callout_id)   # bilinmeyen/yabancı kimlik: tümü reddedilir
        changed = []
        for callout_id in ids:
            row = _effective_row(record, decisions, callout_id)
            prior_disposition = row.get("disposition")
            if ignored:
                if bool(row["ignored"]) and prior_disposition == "not_model_input":
                    continue                                 # aynı kararı taşıyan satır: içeride no-op
                changes = _review_passthrough(row, ignored=True, unbindable=False,
                                              disposition="not_model_input", duplicate_of=None,
                                              disposition_reason=None)
            else:
                if not bool(row["ignored"]):
                    continue
                # Geri alma yalnız „modele ait değil“ claim'ini kaldırır; başka bir disposition
                # (ör. build_relevant_unsupported) kazara silinmez (PLAN-24 §11).
                keep = None if prior_disposition == "not_model_input" else prior_disposition
                changes = _review_passthrough(row, ignored=False, disposition=keep,
                                              duplicate_of=row.get("duplicate_of") if keep else None,
                                              disposition_reason=(row.get("disposition_reason")
                                                                  if keep else None))
            _set_review(record, decisions, callout_id, region_override=row["region_override"], **changes)
            changed.append(callout_id)
        if not changed:
            return [], []                                    # bayt düzeyinde no-op: revizyon ve olay yok
        note = (f"Kullanıcı {len(ids)} ölçü/not alanını tek adımda 'modele ait değil' ilan etti."
                if ignored else
                f"Kullanıcı {len(ids)} ölçü/not alanını tek adımda yeniden değerlendirmeye aldı.")
        events = [("bulk_ignore_callouts" if ignored else "bulk_restore_callouts", "callout:*",
                   {"count": len(ids), "callout_ids": list(ids)}, None, note)]
        return events, [("callout_reviews", callout_id) for callout_id in ids]

    callout_id = payload.get("callout_id")
    if not isinstance(callout_id, str) or not callout_id:
        raise ValueError("callout kimliği gerekli")
    current = _effective_row(record, decisions, callout_id)
    if action == "edit_region":
        region = callout_models.check_region(payload.get("region"))
        # G12.1: bölge düzeltmesi hiçbir kapsam kararını taşımaz — hepsi aynen korunur.
        _set_review(record, decisions, callout_id, region_override=region,
                    **_review_passthrough(current))
        return ([("edit_callout_region", f"callout:{callout_id}", region,
                  {"callout_id": callout_id, "region": region},
                  "Kullanıcı callout alanını düzeltti; alanın kendisi (makine tespiti) değişmedi.")],
                [("callout_reviews", callout_id)])

    if action == "set_ignored":
        ignored = payload.get("ignored")
        if not isinstance(ignored, bool):
            raise ValueError("yok sayma kararı true/false olmalı")
        # "callout değil" ve "bağlanamaz" birbirini dışlar: biri seçildiğinde öteki bırakılır.
        # G12.1: „callout değil“ artık *adı konmuş* bir sınıflandırmadır — not_model_input
        # (eski bayrak geriye dönük uyum için kalır; kapsam denetimi claim'i bu alandan okur).
        _set_review(record, decisions, callout_id,
                    region_override=current["region_override"],
                    **(_review_passthrough(current, ignored=True, unbindable=False,
                                           disposition="not_model_input", duplicate_of=None,
                                           disposition_reason=None) if ignored else
                       _review_passthrough(current, ignored=False, disposition=None,
                                           duplicate_of=None, disposition_reason=None)))
        return ([("ignore_callout" if ignored else "restore_callout", f"callout:{callout_id}", None,
                  {"callout_id": callout_id, "disposition": "not_model_input" if ignored else None},
                  "Kullanıcı bu callout'u 'modele ait değil' olarak sınıflandırdı." if ignored
                  else "Kullanıcı bu callout'u yeniden değerlendirmeye aldı; metni silinmedi.")],
                [("callout_reviews", callout_id)])

    if action == "set_unbindable":
        unbindable = payload.get("unbindable")
        if not isinstance(unbindable, bool):
            raise ValueError("'bağlanamaz' kararı true/false olmalı")
        # G6 panelinin dördüncü düğmesi; G12.1'de bu *build_relevant_unsupported* demektir: gerçek
        # bir bilgi ve bu sürüm uygulayamıyor. Kayıt görünür kalır AMA build'i artık açar değil,
        # kapatır (PLAN-24 §11 — G11 koşusunun ölçtüğü sahte hazırlık tam buydu).
        reason = None
        if unbindable:
            reason = payload.get("disposition_reason") or (
                "Kullanıcı: bu callout bağlanamıyor — gerçek ölçü/not bu sürümde modele uygulanamıyor.")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("gerekçe boş olamaz")
        _set_review(record, decisions, callout_id,
                    region_override=current["region_override"],
                    **(_review_passthrough(current, ignored=False, unbindable=True,
                                           disposition="build_relevant_unsupported",
                                           duplicate_of=None, disposition_reason=reason) if unbindable else
                       _review_passthrough(current, unbindable=False, disposition=None,
                                           duplicate_of=None, disposition_reason=None)))
        return ([("unbindable_callout" if unbindable else "rebind_callout", f"callout:{callout_id}", None,
                  {"callout_id": callout_id, "disposition": "build_relevant_unsupported" if unbindable else None},
                  "Kullanıcı bu callout'un gerçek bir bilgi olduğunu ama bu sürümün uygulayamadığını "
                  "bildirdi; build bu kapanana kadar açılmaz." if unbindable
                  else "Kullanıcı 'bağlanamaz' kararını geri aldı; callout yeniden bağlanabilir.")],
                [("callout_reviews", callout_id)])

    if action == "set_disposition":
        # G12.1'in tek kapısı: üç kapsam claim'i ve geri alma. Dayanak (redundant → duplicate_of)
        # burada *çözülebilir olmak* zorundadır: bilinmeyen kimlik / tanınmayan decision adı
        # tümden reddedilir (yazım hatası kayda geçmez). Çözülen ama henüz kapsanmamış bir dayanak
        # kabul edilir — kapsam denetimi onu stale_duplicate_reference olarak gösterir ve dayanak
        # karara bağlanınca blok kendiliğinden kalkar (PLAN-24 §15).
        disposition = payload.get("disposition")
        if disposition is None:
            _set_review(record, decisions, callout_id, region_override=current["region_override"],
                        **_review_passthrough(current, ignored=False, unbindable=False,
                                              disposition=None, duplicate_of=None,
                                              disposition_reason=None, duplicate_pin=None))
            return ([("clear_callout_disposition", f"callout:{callout_id}", None,
                      {"callout_id": callout_id},
                      "Kullanıcı callout'un kapsam kararını kaldırdı; yeniden değerlendirilecek.")],
                    [("callout_reviews", callout_id)])
        if disposition not in callout_models.CALLOUT_DISPOSITIONS:
            raise ValueError("kapsam kararı 'not_model_input', 'redundant' ya da "
                             "'build_relevant_unsupported' olmalı")
        duplicate_of = payload.get("duplicate_of")
        reason = payload.get("disposition_reason")
        if disposition == "redundant":
            if not isinstance(duplicate_of, str) or not duplicate_of.strip():
                raise ValueError("'redundant' kararı dayanağını yazmak zorunda (duplicate_of): "
                                 "başka bir callout kimliği ya da decision:<ad>")
            duplicate_of = duplicate_of.strip()
            if duplicate_of.startswith(callout_models.DISPOSITION_DECISION_PREFIX):
                name = duplicate_of[len(callout_models.DISPOSITION_DECISION_PREFIX):]
                if not callout_readiness.decision_ref_present(decisions, name):
                    raise ValueError(f"bu oturumda böyle bir karar yok: {duplicate_of} "
                                     f"(bilinen adlar: {', '.join(sorted(callout_readiness.DECISION_REFS))})")
            elif duplicate_of != callout_id:
                _effective_row(record, decisions, duplicate_of)   # var olmalı; kapsanması şart değil
            else:
                raise ValueError("bir callout kendini dayanak gösteremez")
        else:
            duplicate_of = None
        if disposition == "build_relevant_unsupported":
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("'build_relevant_unsupported' kararı gerekçesiz olamaz "
                                 "(disposition_reason): gerçek bilgi neden uygulanamıyor?")
        elif reason is not None and not isinstance(reason, str):
            raise ValueError("gerekçe metin olmalı")
        events = {"not_model_input": (
                      "set_callout_disposition", f"callout:{callout_id}", None,
                      {"callout_id": callout_id, "disposition": disposition},
                      "Kullanıcı bu callout'u 'modele ait değil' olarak sınıflandırdı."),
                  "redundant": (
                      "set_callout_disposition", f"callout:{callout_id}", None,
                      {"callout_id": callout_id, "disposition": disposition,
                       "duplicate_of": duplicate_of},
                      f"Kullanıcı bu callout'un başka bir kararla zaten temsil edildiğini bildirdi "
                      f"(dayanak: {duplicate_of})."),
                  "build_relevant_unsupported": (
                      "set_callout_disposition", f"callout:{callout_id}", None,
                      {"callout_id": callout_id, "disposition": disposition,
                       "disposition_reason": reason},
                      f"Kullanıcı bu callout'un gerçek bir ölçü/not olduğunu ama bu sürümün "
                      f"uygulayamadığını bildirdi; kapsam tamamlanana kadar build açılmaz.")}[disposition]
        # G12R-02: onayın kanıtı sunucuda doğar — dayanağın O ANKİ değeri ve satırın kendi okuması.
        pin = (callout_readiness.approval_pin(record, decisions, callout_id, duplicate_of)
               if disposition == "redundant" else None)
        _set_review(record, decisions, callout_id, region_override=current["region_override"],
                    **_review_passthrough(current, ignored=False,
                                          unbindable=disposition == "build_relevant_unsupported",
                                          disposition=disposition, duplicate_of=duplicate_of,
                                          disposition_reason=reason if disposition == "build_relevant_unsupported"
                                          else None,
                                          duplicate_pin=pin))
        return ([events], [("callout_reviews", callout_id)])

    subject = "Dış inceleme" if actor == "external_review" else "Kullanıcı"

    if action == "transcribe":
        if current["ignored"]:
            raise ValueError("yok sayılan bir callout'a metin yazılamaz; önce geri alın")
        # G9 UX turu — the machine hint's single-click acceptance. The hint is the server's own
        # reading of this box, so "accept the hint" is checked against it here: a client cannot use
        # the flag to write text the drawing never showed. The decision stays the user's, and the
        # event names the hint it accepted (the audit chain keeps saying where the text came from).
        accept_hint = payload.get("accept_hint", False)
        if not isinstance(accept_hint, bool):
            raise ValueError("accept_hint true/false olmalı")
        hint = str(current.get("machine_text_hint") or "").strip()
        if accept_hint:
            if not hint:
                raise ValueError("bu callout'ta makine ipucu yok; metni kendiniz yazın")
            if str(payload.get("raw_text") or "").strip() != hint:
                raise ValueError("ipucu kabulü metnin makine ipucuyla birebir aynı olmasını gerektirir")
        row = callout_models.TranscriptionDecision(callout_id=callout_id, raw_text=payload.get("raw_text"),
                                                   source_region=current["region"], revision=0,
                                                   # GX: dış inceleme metni kendi kaynağıyla yazılır — kullanıcı
                                                   # burada yazmış gibi görünmez (PLAN §12 provenance).
                                                   entered_by=("external_review" if actor == "external_review"
                                                               else "user"))
        # The region the user actually reviewed is the server's own effective region — a client
        # cannot claim to have read a box the session never showed (PLAN-21 §6.3).
        decisions["transcriptions"] = _upsert(decisions.get("transcriptions") or [], "callout_id",
                                              row.model_dump(mode="json"))
        stored_row = row.model_dump(mode="json")
        prior = next((item for item in (record.get("decisions") or {}).get("transcriptions") or []
                      if item.get("callout_id") == callout_id), None)
        if _transcription_carried(prior, stored_row):
            return [], [("transcriptions", callout_id)]      # aynı karar: olay yok, yazım da olmayacak
        evidence = {"callout_id": callout_id, "source_region": row.source_region}
        note = (f"{subject} callout metnini yazdı." if prior is None
                else f"{subject} callout metnini düzenledi.")
        if accept_hint:
            evidence["accepted_hint"] = True
            evidence["machine_text_hint"] = hint
            note = f"{subject} makine ipucunu doğrulayıp callout metnini {'yazdı' if prior is None else 'düzenledi'}."
        return ([("transcribe" if prior is None else "edit_transcription", f"callout:{callout_id}",
                  row.raw_text, evidence, note)],
                [("transcriptions", callout_id)])

    raise ValueError(f"işlem bulunamadı: {action}")


def _review_target(record: dict, decisions: dict, callout_id: str, action: str,
                   payload: dict) -> tuple[list[tuple], list[tuple]]:
    """GX: a reviewer's target confirmation — server fields come from this record, never the bundle.

    The revision the reading stands on and the parser version are read here, so an imported
    confirmation is bound exactly like one the interface sent; the evidence says where it came from.
    """
    transcription = next((row for row in decisions.get("transcriptions") or []
                          if row.get("callout_id") == callout_id), None)
    if transcription is None:
        raise ValueError(f"hedef onayı için önce metin gerekli: {callout_id}")
    ids = [str(item) for item in payload.get("target_ids") or []]
    evidence = payload.get("evidence") or [{"kind": "external_review",
                                            "ref": f"{action} · {', '.join(ids)}"}]
    row = callout_models.CalloutTargetDecision(callout_id=callout_id,
                                               target_kind=payload.get("target_kind"),
                                               target_ids=ids,
                                               transcription_revision=transcription.get("revision"),
                                               parser_version=callout_models.CALLOUT_PARSER_VERSION,
                                               evidence=evidence, reconfirm=False)
    decisions["callout_targets"] = _upsert(decisions.get("callout_targets") or [], "callout_id",
                                           row.model_dump(mode="json"))
    return ([("confirm_target" if action == "confirm_target" else "select_target",
              f"callout:{callout_id}", ids,
              {"callout_id": callout_id, "source": "external_review", "via": action},
              "Dış inceleme bu callout için hedefi onayladı." if action == "confirm_target"
              else "Dış inceleme bu callout için hedefi kendi seçti.")],
            [("callout_targets", callout_id)])


def _sheet_issues(record: dict) -> list[dict]:
    """The build's own waiting states in the G8 categories (PLAN §14) — never a free-text guess.

    The store's `questions()` stays the authority on *whether* a build may start; this names the same
    conditions with machine reason codes so the callout layer's readiness can merge them without
    re-deriving a rule of its own.
    """
    decisions = Decisions.model_validate(record.get("decisions") or {})
    options = record.get("options") or {}
    issues: list[dict] = []
    if not decisions.profile_id:
        issues.append({"category": "missing_profile", "reason": "profile_not_chosen",
                       "detail": "Ana görünüşte dış konturu seçin."})
    if not decisions.calibration:
        issues.append({"category": "missing_calibration", "reason": "calibration_missing",
                       "detail": "Bilinen ölçünün iki noktasını ve uzunluğunu belirtin."})
    if not decisions.thickness:
        issues.append({"category": "geometry_conflict", "reason": "thickness_missing",
                       "detail": "Parçanın kalınlığını girin."})
    if not decisions.trace_acknowledged:
        issues.append({"category": "geometry_conflict", "reason": "trace_not_acknowledged",
                       "detail": "Çizimden izlenen konturu taslak olarak kullanmayı onaylayın."})
    if any(row.axis is None or row.direction is None for row in decisions.bindings):
        issues.append({"category": "geometry_conflict", "reason": "binding_axis_missing",
                       "detail": "Bağlanan ölçünün eksenini (X/Y) ve yönünü seçin."})
    product = options.get("sheet_frame") or {}
    view = getattr(decisions, "view", None)
    obvious = bool(product.get("found")) and product.get("aligned") is not False and not product.get("rotation")
    if view is None and not obvious:
        issues.append({"category": "missing_view", "reason": "view_not_confirmed",
                       "detail": _view_question(product)})
    elif view is not None and _view_mismatch(view, product):
        issues.append({"category": "missing_view", "reason": "view_mismatch",
                       "detail": "Onaylanan görüş yönü bu okumayla uyuşmuyor; görüş yeniden onaylanmalı."})
    profile = next((row for row in options.get("profiles") or [] if row["id"] == decisions.profile_id), None)
    for reason in unsupported_binding_reasons(profile or {}, decisions):
        issues.append({"category": "geometry_conflict", "reason": "binding_unsupported", "detail": reason})
    if options:
        for row in unresolved_bindings(options, decisions):
            issues.append({"category": "geometry_conflict", "reason": "binding_unresolved",
                           "detail": f"Bağlanan ölçü yeniden bağlanmalı ({row['reason']})."})
    return issues


class GuidedStore:
    def __init__(self, root: Path):
        self.root=Path(root)
        self.lock=threading.RLock()

    def recover_interrupted(self):
        """Call once on server startup, before it accepts requests."""
        for path in self.root.glob("*/session.json"):
            try:
                record=json.loads(path.read_text())
                if (record.get("build") or {}).get("status")=="running":
                    record["build"]["status"]="interrupted"
                    record["build"]["error"]="Önceki üretim yarıda kaldı. Kararlar korundu; yeniden üretebilirsiniz."
                    _atomic(path,record)
            except (OSError,ValueError):
                continue

    def folder(self,token):
        if not re.fullmatch(r"[a-f0-9]{32}",str(token)): raise ValueError("oturum kimliği geçersiz")
        return self.root/token

    def load(self,token):
        """P01-b.4/5: a missing or changed source is a *state*, not an exception.

        Raising here made the whole session unreadable — the decisions and the evidence that the session
        already holds must stay open to the user, while the build waits with an explanatory reason.
        """
        folder=self.folder(token)
        record=json.loads((folder/"session.json").read_text())
        try:
            digest=_digest(Path(record["source"]))
        except Exception as error:
            digest=None
            reason="kaynak dosya okunamadı: " + " ".join(str(error).split())[:120]
        else:
            reason=None if digest==record["source_sha256"] else "kaynak çizim değişmiş: özet uyuşmuyor"
        if reason and not record.get("geometry_stale"):
            record["geometry_stale"]={"reason":reason}
            _log(record,"system","migrate","geometry",None,{"source_sha256":digest},
                 "Eski sonuç tarihsel: " + reason + "; kararlar ve kanıt korundu.")
            _atomic(folder/"session.json",note_sketch(record))
        return self._migrated(token,record)

    def _migrated(self,token,record):
        """P01-a: keep the base geometry read-only, and never take an old record's geometry on trust.

        The raw record is backed up first (atomic, re-openable). Then the source is re-read: identities the
        reader still reproduces refresh the base geometry under the current version — with the moved
        coordinates named in the log — while a mismatch, or a source that cannot be read at all, makes the
        record `geometry_stale` with its reason, keeps every decision and file as they are, and leaves the
        build refusing. Idempotent: a second load does nothing.
        """
        if record.get("geometry_version") == GEOMETRY_VERSION or record.get("geometry_stale"):
            return record
        folder = self.folder(token)
        backup = folder / "session.backup.json"
        if not backup.exists():
            _atomic(backup, record)                    # the raw pre-migration record, exactly as it was
        try:
            fresh = drawing_options(observe(Path(record["source"])))
        except Exception as error:                     # an unreadable source is a state, not a crash
            record["geometry_stale"] = {
                "reason": "kaynak yeniden okunamadı: " + " ".join(str(error).split())[:200],
                "backup": str(backup)}
            _log(record,"system","migrate","geometry",None,{"backup":str(backup)},
                 "Eski sonuç tarihsel: temel geometri kaynaktan doğrulanamadı; kararlar korundu.")
        else:
            steps = _geometry_diff(record.get("options") or {}, fresh)
            if not steps:
                moved = _moved_geometry(record.get("options") or {}, fresh)
                record["options"] = fresh
                record["geometry_version"] = GEOMETRY_VERSION
                _log(record,"system","migrate","geometry",GEOMETRY_VERSION,
                     {"profiles":len(fresh.get("profiles") or []),"circles":len(fresh.get("circles") or []),
                      "moved_ends":moved,"backup":str(backup)},
                     "Temel geometri kaynaktan yeniden çıkarıldı; kararlar korundu."
                     + (f" Kayıttaki {moved} koordinat eski bir üretimden kalmaydı; çizimin kendisi kullanıldı."
                        if moved else ""))
            else:
                record["geometry_stale"] = {
                    "reason": "kaynak geometri kimlikleri kayıttakilerle eşleşmedi: " + ", ".join(steps[:4]),
                    "backup": str(backup)}
                _log(record,"system","migrate","geometry",None,{"backup":str(backup),"diff":steps[:6]},
                     "Geçiş yapılmadı: kaynak geometri kimlikleri eşleşmedi; kararlar ve eski dosyalar korundu.")
        _atomic(folder/"session.json",note_sketch(record))
        return record

    def recheck(self,token):
        """P01-b.5: try the geometry contract again after the source or the reader changed.

        A stale flag is not a dead end — the raw record is already backed up, so this re-runs the same
        identity check and either refreshes the geometry or leaves the record exactly as it was.
        """
        with self.lock:
            r=self.load(token)
            if not r.get("geometry_stale"):
                return self.public(r)
            r.pop("geometry_stale", None)
            _atomic(self.folder(token)/"session.json", r)
            return self.public(self.load(token))

    def create(self,payload: bytes):
        suffix=".pdf" if payload.startswith(b"%PDF-") else ".png"
        token=uuid.uuid4().hex; folder=self.folder(token);folder.mkdir(parents=True)
        source=folder/("source"+suffix);source.write_bytes(payload)
        observations=observe(source)
        detection=callouts.callout_candidates_from_observations(observations,geometry_version=GEOMETRY_VERSION)
        candidates=[row.model_dump(mode="json") for row in detection.candidates]
        diagnostics=[row.model_dump(mode="json") for row in detection.diagnostics]
        source_sha=_digest(source)
        # PLAN-18 §28: gözlemin kendi özeti oturumun kaynak özetiyle uyuşmuyorsa aday kimliği uydurulmaz.
        if observations.source.sha256!=source_sha:
            diagnostics.append({"code":"source_digest_mismatch","observation_id":None})
            candidates=[]
        page=load_page(source);(folder/"drawing.png").write_bytes(page.image_png)
        options=drawing_options(observations)
        archetype=part_class(observations)
        reading=advise.reading_record(source)
        suggested=advise.proposals(options,reading,archetype)
        record={"version":1,"geometry_version":GEOMETRY_VERSION,"token":token,"revision":0,"source":str(source.resolve()),
                "source_sha256":source_sha,"options":options,"decisions":Decisions().model_dump(mode="json"),
                "archetype":archetype,
                "callout_schema_version":callout_models.CALLOUT_SCHEMA_VERSION,"callout_candidates":candidates,
                "callout_detection":{"detector_version":detection.detector_version,"diagnostics":diagnostics},
                "callout_parses":[],
                "reading":reading,"proposals":suggested,"history":[],"build":None,"log":[]}
        _log(record,"system","open","drawing",None,{"source_sha256":record["source_sha256"],
             "profiles":len(options["profiles"]),"circles":len(options["circles"]),
             "measurements":len(options["measurements"])},"Çizim açıldı; konturlar ve daireler hazırlandı.")
        _log(record,"reading","class","archetype",archetype["class"],archetype.get("evidence"),
             (f"Parça sınıfı: {archetype['class']}."
              + (" Kararlar flanş yüzünün kendi dairelerinden okunur; dirsek gövdesi ve ikinci flanş bu "
                 "dilimde kurulmuyor." if archetype["class"] == "rotational-flanged" else "")
              + (f" {archetype['reason']}" if archetype.get("reason") else "")))
        if reading.get("refused"):
            _log(record,"reading","refuse","reading",None,{"reason":reading["refused"]},
                 f"Okuma bu paftayı çözemedi: {reading['refused']}")
        else:
            _log(record,"reading","reading","reading",None,
                 {"printed":len(reading.get("printed",[])),"claims":len(reading.get("claims",[])),
                  "outline_mm":reading.get("outline_mm"),"refusals":reading.get("refusals",[])},
                 f"Okuma {len(reading.get('printed',[]))} basılı ölçüyü geometriye bağladı.")
        for item in suggested:
            _log(record,"reading","proposal",item["field"],item["value"],item["evidence"],_proposal_note(item))
        _atomic(folder/"observations.json",observations.model_dump(mode="json"))
        _atomic(folder/"session.json",record)
        return self.public(record)

    def save(self,token,revision,decisions=None,undo=False):
        """The external full-record path: one payload in, one atomic commit out.

        It and `edit_callout` end in the same private `_commit` below, so validation (including the G3
        row-ownership rules), the byte-level no-op check, history, the global revision, the log and the
        build's staleness behave identically whichever way a decision arrived; a rejected payload
        writes nothing.
        """
        with self.lock:
            return self._commit(token,revision,decisions=decisions,undo=undo)

    def _commit(self,token,revision,*,decisions=None,undo=False,events=None,produced=None,
                actor="user"):
        """The one persistence path (PLAN-22 §4.1).

        `events` and `produced` belong to an *internally validated command* — never read from an HTTP
        request — and a command-produced row still passes the same relation and model checks: `produced`
        only names which row that command is the writer of.
        """
        with self.lock:
            r=self.load(token)
            if type(revision) is not int or revision != r["revision"]: raise ValueError("oturum değişti; yeniden açın")
            if undo:
                if not r["history"]: raise ValueError("geri alınacak karar yok")
                before=r["decisions"]
                r["decisions"]=r["history"].pop()
                _refresh_callout_parses(r)
                _log(r,"user","undo","decisions",r["decisions"],None,"Son karar geri alındı.")
                for field,value in _changed_fields(before,r["decisions"]):
                    _log(r,"user","undo",field,value,None,"Geri alma ile eski değere döndü.")
            else:
                if decisions is not None and not (produced or ()):
                    _refuse_forged_strategy(r,decisions)
                merged=_merge_callout_defaults(r,decisions)
                d,written=_with_end_evidence(r,Decisions.model_validate(merged))
                d=_prepare_callouts(r,d)
                validate_decisions(r["options"],d)
                _validate_callouts(r,d,produced=produced)
                d=_consume_reconfirm(d)
                payload=d.model_dump(mode="json")
                if written:
                    _log(r,"user","edit","bindings",None,None,
                         f"{written} bağ ucunun kanıtı yazıldı (seçildiği kontur, geometri sürümü, fiziksel uç).")
                if payload==_normalized_decisions(r): return self.public(r)
                before=r["decisions"]
                r["history"].append(r["decisions"])
                r["decisions"]=payload
                # PLAN §9: the reading is the server's own derivation, computed here and bound to the
                # revision it was read off — derived data, so no history step and no log line.
                _refresh_callout_parses(r)
                for field,value in _changed_fields(before,payload):
                    item=_proposal_match(r.get("proposals",[]),field,value)
                    if item:
                        _log(r,"user","accept",field,value,item["evidence"],"Öneri onaylandı (kullanıcı).",
                             confidence=item["confidence"])
                    elif value is None:
                        _log(r,"user","veto",field,None,None,"Kullanıcı bu kararı kaldırdı.")
                    else:
                        _log(r,"user","edit",field,value,None,"Kullanıcı bu kararı kendi girdi.")
                _log_callout_changes(r,before,payload,produced=produced)
                for action,field,value,evidence,note in (events or []):
                    _log(r,actor,action,field,value,evidence,note)
            _stamp_callout_version(r)
            r["revision"]+=1;r["build"]=None
            _atomic(self.folder(token)/"session.json",note_sketch(r))
            return self.public(r)

    def edit_callout(self,token,revision,action,payload=None):
        """One G3 user command on the callout layer (PLAN-21 §6.4).

        The command only *proposes* a change to a working copy of the decisions and names the rows it
        is the writer of; the commit goes through the one `_commit` path, so validation, the byte-level
        no-op check, history, the global revision, the stale build and the log behave exactly as they
        do for every other decision. A failed validation or a revision conflict leaves the record
        untouched — and an unknown action is refused before anything is even copied.
        """
        if action not in _CALLOUT_COMMANDS:
            raise ValueError(f"işlem bulunamadı: {action}")
        with self.lock:
            r=self.load(token)
            if type(revision) is not int or revision != r["revision"]: raise ValueError("oturum değişti; yeniden açın")
            decisions=json.loads(json.dumps(r["decisions"]))
            events,produced=_apply_callout_command(r,decisions,action,payload if isinstance(payload,dict) else {})
            return self._commit(token,revision,decisions=decisions,events=events,produced=produced)

    def set_strategy(self,token,revision,payload=None):
        """G12.2 (PLAN-25 §36): the explicit build strategy — one command, one revision, undoable.

        The strategy, its key and the geometry version it was confirmed against are computed here from
        the record itself; whatever the client sends for `strategy_key`, `geometry_version` or
        `evidence` is never read. `clear` removes the decision (back to "no strategy yet"), which is a
        user action like any other and therefore its own history step.
        """
        payload=dict(payload or {})
        clear=bool(payload.pop("clear",False))
        kind=payload.get("kind")
        with self.lock:
            r=self.load(token)
            if type(revision) is not int or revision != r["revision"]: raise ValueError("oturum değişti; yeniden açın")
            decisions=json.loads(json.dumps(r["decisions"]))
            if clear:
                if decisions.get("build_strategy") is None:
                    return self.public(r)
                decisions["build_strategy"]=None
                events=[("veto","build_strategy",None,None,"Kullanıcı oluşturma biçimi kararını kaldırdı.")]
            else:
                decisions["build_strategy"]=build_strategy.decision_for(r,decisions,kind,payload=payload)
                row=decisions["build_strategy"]
                events=[("edit","build_strategy",row,
                         {"strategy_key":row["strategy_key"],"evidence":row["evidence"]},
                         f"Kullanıcı parçanın ana oluşturma biçimini seçti: {build_strategy.STRATEGY_LABEL.get(kind,kind)}.")]
            return self._commit(token,revision,decisions=decisions,events=events,produced="build_strategy")

    def propose(self, token, callout_id):
        """G5 on demand: ranked, evidence-based target proposals for one callout (a read).

        Nothing is written and no confirmation is created: this is the picture the G6 panel shows
        before the user decides. The scale it measures with is the user's own calibration — the same
        number the build uses, never a fit of their printed measures (PLAN P04-a).
        """
        with self.lock:
            r = self.load(token)
            if not isinstance(callout_id, str) or not callout_id:
                raise ValueError("callout kimliği gerekli")
            state = callout_models.callout_state(r, callout_id)
            if state is None:
                raise ValueError(f"callout bulunamadı: {callout_id}")
            scale = (note_sketch({"options": r["options"], "decisions": r["decisions"]}).get("sketch")
                     or {}).get("px_per_mm")
            proposals = callout_bind.propose_targets(r, callout_id, scale_px_per_mm=scale)
            target = next((item for item in (r["decisions"].get("callout_targets") or [])
                           if item.get("callout_id") == callout_id), None)
            return {"callout_id": callout_id, "geometry_version": r.get("geometry_version"),
                    # G6: the panel must build a confirmation the store will accept — the parser
                    # version and the transcription revision it binds to come from the reading,
                    # never from the browser's own guess.
                    "parser_version": callout_models.CALLOUT_PARSER_VERSION,
                    "transcription_revision": (state.get("transcription") or {}).get("revision"),
                    "scale_px_per_mm": scale, "state": state, "target": target,
                    "proposals": [item.model_dump(mode="json") for item in proposals]}

    def readiness(self, token):
        """G8: what the build waits on, per callout and per sheet — the categories, not prose."""
        with self.lock:
            r = self.load(token)
            readiness = callout_readiness.build_readiness(r, sheet_issues=_sheet_issues(r))
            readiness["questions_text"] = [row["text"] for row in readiness["questions"]]
            readiness["sheet_questions"] = questions(Decisions.model_validate(r["decisions"]),
                                                     r.get("sketch"), r["options"])
            return readiness

    def review_export(self, token):
        """GX: the session review bundle an external reviewer works from (PLAN §12)."""
        with self.lock:
            r = self.load(token)
            images = {}
            for row in callout_models.effective_callouts(r):
                name = r.get("callout_crops", {}).get(row["id"])
                if name:
                    images[row["id"]] = name
            return callout_review.export_bundle(r, artifacts=images)

    def review_import(self, token, revision, bundle):
        """GX: import an external review — same validation, history, revision and log as the UI (PLAN §12).

        Untrusted input meets the store's own gates: `validate_import` checks the bundle against this
        very record (all-or-nothing) and every surviving action is applied through the same command and
        commit paths a user's click would take — with `external_review` as its explicit provenance.
        """
        with self.lock:
            r = self.load(token)
            if type(revision) is not int or revision != r["revision"]:
                raise ValueError("oturum değişti; yeniden açın")
            plan = callout_review.validate_import(r, bundle)
            if not plan["ok"]:
                first = plan["errors"][0]
                raise ValueError("içe aktarma reddedildi: " + str(first.get("reason"))
                                 + (f" ({first.get('detail')})" if first.get("detail") else "")
                                 + (f" [+{len(plan['errors']) - 1} hata]" if len(plan["errors"]) > 1 else ""))
            decisions = json.loads(json.dumps(r["decisions"]))
            events: list[tuple] = []
            produced: list[tuple] = []
            for item in plan["actions"]:
                action, callout_id, payload = item["action"], item["callout_id"], dict(item["payload"])
                # The command layer takes the id from the payload it is handed — the import's id is the
                # validated one, so it travels with the payload rather than being trusted twice.
                payload["callout_id"] = callout_id
                if action == "transcribe":
                    region = payload.pop("region", None)
                    if region is not None:
                        extra, rows = _apply_callout_command(r, decisions, "edit_region",
                                                             {"callout_id": callout_id, "region": region},
                                                             actor="external_review")
                        events += extra
                        produced += rows
                    extra, rows = _apply_callout_command(r, decisions, "transcribe", payload,
                                                         actor="external_review")
                elif action in ("ignore", "restore"):
                    extra, rows = _apply_callout_command(r, decisions, "set_ignored",
                                                         {"callout_id": callout_id,
                                                          "ignored": action == "ignore"},
                                                         actor="external_review")
                elif action == "set_disposition":
                    # G12.1: dış inceleme de aynı komuttan geçer — aynı doğrulama, aynı kayıt izi.
                    extra, rows = _apply_callout_command(r, decisions, "set_disposition", payload,
                                                         actor="external_review")
                else:
                    extra, rows = _review_target(r, decisions, callout_id, action, payload)
                events += extra
                produced += rows
            return self._commit(token, revision, decisions=decisions, events=events,
                                produced=produced, actor="external_review")

    def accept(self,token,revision,fields=None):
        """The user takes the reading's own proposals in one step. Values stay the user's decision."""
        with self.lock:
            r=self.load(token)
            if type(revision) is not int or revision != r["revision"]: raise ValueError("oturum değişti; yeniden açın")
            chosen=[item for item in r.get("proposals",[]) if fields is None or item["field"] in fields]
            if not chosen: raise ValueError("bu çizim için onaylanacak öneri yok")
            payload=Decisions.model_validate(r["decisions"]).model_dump(mode="json")
            depth=next((item["value"] for item in chosen if item["field"]=="depth"),None)
            if depth is not None and not (
                any(hole["kind"]=="pocket" for hole in payload["holes"])
                or any(item["field"].startswith("hole:") and item["value"]["kind"]=="pocket"
                       for item in chosen)
            ):
                raise ValueError("Cep derinliğinin uygulanacağı kör cep yok; cep ve derinlik önerilerini birlikte onaylayın veya cebi elle ekleyin.")
            for item in chosen:
                field,value=item["field"],item["value"]
                if field=="calibration": payload["calibration"]=value
                elif field=="profile_id": payload["profile_id"]=value
                elif field=="thickness": payload["thickness"]=value
                elif field=="depth":
                    payload["holes"]=[{**hole,"depth":value} if hole["kind"]=="pocket" else hole
                                      for hole in payload["holes"]]
                elif field.startswith("hole:"):
                    existing=next((hole for hole in payload["holes"] if hole["circle_id"]==value["circle_id"]),None)
                    row={"circle_id":value["circle_id"],"kind":value["kind"],"diameter":value["diameter"],"depth":None}
                    if row["kind"]=="pocket":
                        row["depth"]=depth if depth is not None else (existing or {}).get("depth")
                        if row["depth"] is None:
                            raise ValueError("Yeni kör cep için derinlik de gerekli; cep ve derinlik önerilerini birlikte onaylayın veya cebi derinliğiyle elle ekleyin.")
                    payload["holes"]=[hole for hole in payload["holes"] if hole["circle_id"]!=row["circle_id"]]+[row]
            if any(item["field"]=="profile_id" for item in chosen): payload["trace_acknowledged"]=True
            new,written=_with_end_evidence(r,_prepare_callouts(r,Decisions.model_validate(payload)))
            validate_decisions(r["options"],new)
            _validate_callouts(r,new)
            new=_consume_reconfirm(new)
            if written:
                _log(r,"user","edit","bindings",None,None,
                     f"{written} bağ ucunun kanıtı yazıldı (seçildiği kontur, geometri sürümü, fiziksel uç).")
            if new.model_dump(mode="json")==_normalized_decisions(r): return self.public(r)
            r["history"].append(r["decisions"]);r["decisions"]=new.model_dump(mode="json")
            _stamp_callout_version(r)
            r["revision"]+=1;r["build"]=None
            _log(r,"user","accept","proposals",None,{"fields":[item["field"] for item in chosen]},
                 f"Okumanın {len(chosen)} önerisi tek adımda onaylandı.")
            for item in chosen:
                value=item["value"]
                if item["field"].startswith("hole:"):
                    value=next(hole for hole in r["decisions"]["holes"] if hole["circle_id"]==value["circle_id"])
                _log(r,"user","accept",item["field"],value,item["evidence"],
                     f"Öneri onaylandı: {item['confidence']} kanıt.",confidence=item["confidence"])
            _atomic(self.folder(token)/"session.json",note_sketch(r))
            return self.public(r)

    def build(self,token,revision):
        with self.lock:
            r=self.load(token)
            if type(revision) is not int or revision != r["revision"]: raise ValueError("oturum değişti; yeniden açın")
            if r.get("geometry_stale"):
                raise ValueError("temel geometri kaynaktan yenilenemedi ("+str((r["geometry_stale"] or {}).get("reason"))
                                 +"); eski sonuç tarihsel, yeniden üretilemez")
            # G8 (PLAN §14): the build waits on the categories, not on prose — and a callout conflict
            # is named and refused, never patched over (PLAN §13). A callout the user declared
            # unbindable is a scope decision, so it is not a blocker.
            readiness = callout_readiness.build_readiness(r, sheet_issues=_sheet_issues(r))
            if not readiness["ready"]:
                raise ValueError("üretim için eksik/uyumsuz girdiler var: "
                                 + " ".join(row["text"] for row in readiness["questions"][:3]))
            compiled = callout_compile.compile_callouts(r)
            if compiled["conflicts"]:
                raise ValueError("callout kararları çelişiyor: "
                                 + " ".join(str(item.get("detail") or item.get("reason"))
                                            for item in compiled["conflicts"][:3]))
            plan=make_plan({**r, "decisions": callout_compile.apply_compiled(r["decisions"], compiled)})
            folder=self.folder(token)/f"build-{revision}-{uuid.uuid4().hex[:8]}"
            # P01-b.1: an output belongs to one source digest, one geometry version and one decision
            # revision — the build carries all three, so a later migration or edit cannot inherit it.
            identity={"revision":revision,"source_sha256":r.get("source_sha256"),
                      "geometry_version":r.get("geometry_version")}
            r["build"]={"revision":revision,"status":"running","folder":str(folder),**identity}
            _log(r,"system","build","build",None,{"revision":revision,"folder":str(folder)},
                 "Üretim başladı: kararlar GeneralPlan'a çevrildi, STEP kuruluyor.")
            # G7 (PLAN §13): what the callout chain contributed rides in the log, so the generated
            # part can be traced back to the text the user confirmed.
            summary = callout_compile.compiled_summary(compiled)
            if summary["compiled_holes"] or summary["compiled_bindings"]:
                _log(r,"system","build","callout_compile",None,summary,
                     f"Callout zincirinden {summary['compiled_holes']} delik ve "
                     f"{summary['compiled_bindings']} ölçü bağı derlendi.")
            _atomic(self.folder(token)/"session.json",note_sketch(r))
        try:
            build_general(plan,r["source"],folder)
            outcome={**identity,"status":"complete","folder":str(folder)}
        except Exception as exc:
            outcome={**identity,"status":"failed","folder":str(folder),"error":str(exc)}
        with self.lock:
            current=self.load(token)
            # A late build cannot attach itself to newer decisions.
            if current["revision"]==revision and current.get("build",{}).get("folder")==str(folder):
                current["build"]=outcome
                audit=_audit_summary(folder)
                if outcome["status"]=="complete":
                    _log(current,"system","build","build",None,{"revision":revision,"folder":str(folder),**audit},
                         "Üretim tamam: STEP yeniden açıldı ve geometri denetimi geçti." if audit.get("passed")
                         else "Üretim tamam: geometri denetimi geçmedi, çıktı taslak.")
                else:
                    _log(current,"system","build","build",None,{"revision":revision,"folder":str(folder),
                         "error":outcome.get("error")},f"Üretim durdu: {outcome.get('error')}")
                _atomic(self.folder(token)/"session.json",note_sketch(current))
            return self.public(current)

    def public(self,r):
        build=r.get("build")
        stale=r.get("geometry_stale")
        # P01-b.2/3: an output is current only for the same source digest, geometry version and decision
        # revision — and never while the geometry itself is stale. The old file stays on disk as history.
        ready=bool(build) and build.get("status")=="complete" and not stale \
              and build.get("revision")==r["revision"] \
              and build.get("source_sha256")==r.get("source_sha256") \
              and build.get("geometry_version")==r.get("geometry_version")
        historical=bool(build) and build.get("status")=="complete" and not ready
        status=None
        if build:
            status=build["status"] if (ready or build.get("status")!="complete") else "historical"
        prefix=f"/guided-session/{r['token']}"
        reading=r.get("reading") or {}
        return {**{key:r[key] for key in ("token","revision","options","decisions")},
                "questions":questions(Decisions.model_validate(r["decisions"]), r.get("sketch"), r["options"]), "can_undo":bool(r["history"]),
                "proposals":r.get("proposals",[]), "log":r.get("log",[]),
                "callout_schema_version":r.get("callout_schema_version"),
                "callout_candidates":r.get("callout_candidates") or [],
                # PLAN-22 §7 (G3R-04): the detection's own result and reasons ride in the public state —
                # `None` for a record that predates the detector (an explicit "no information", never a
                # fabricated success), computed fresh by the detector when the session was created.
                "callout_detection":r.get("callout_detection"),
                "callout_parses":r.get("callout_parses") or [],
                "callouts":callout_models.callout_states(r),
                # PLAN-25 §15 (G12.1b): the decision-coverage picture rides in the public state — the
                # panel's navigation reads *these* buckets instead of re-deriving resolved-ness from
                # parse/target flags, so "unsupported" can never be shown as resolved in the UI while
                # the backend blocks the build on it.
                "coverage":callout_readiness.callout_coverage(r),
                # G12.2 (PLAN-25 §42): the panel reads the decision, its freshness and the
                # evidence-based proposals from here — all three computed from the record itself.
                "build_strategy":{"state":build_strategy.strategy_state(r),
                                  "decision":build_strategy.strategy_of(r),
                                  "labels":build_strategy.STRATEGY_LABEL,
                                  "proposals":[row.model_dump(mode="json")
                                               for row in build_strategy.propose_strategies(r)]},
                # PLAN-21 §6.2: the one effective list — base detections plus the user's own regions,
                # with the reviewed region/ignore state applied. Derived, never a decision itself.
                "effective_callouts":callout_models.effective_callouts(r),
                "archetype":r.get("archetype"), "sketch":note_sketch({"options":r["options"],"decisions":r["decisions"]}).get("sketch"),
                "reading":{"printed":reading.get("printed",[]),"outline_mm":reading.get("outline_mm"),
                           "refusals":reading.get("refusals",[]),"refused":reading.get("refused"),
                           "notes":reading.get("notes",[])},
                "drawing":prefix+"/drawing.png","build_status":status,
                "geometry":{"version":r.get("geometry_version"),"stale":(stale or {}).get("reason"),
                            "backup":(stale or {}).get("backup"),
                            "historical":(build or {}).get("folder") if historical else None},
                "error":(build or {}).get("error"),"step":prefix+"/part.step" if ready else None,
                "stl":prefix+"/part.stl" if ready else None,"plan":prefix+"/plan.json" if ready else None,
                "audit":prefix+"/plan-audit.json" if ready else None}

    def artifact(self,token,name):
        r=self.load(token);folder=self.folder(token)
        if name=="drawing.png":return folder/name,"image/png"
        types={"part.step":"application/step","part.stl":"model/stl","plan.json":"application/json","plan-audit.json":"application/json"}
        if name not in types:raise ValueError("dosya yok")
        build=r.get("build")
        if r.get("geometry_stale"):
            raise ValueError("eski sonuç tarihsel: " + str((r["geometry_stale"] or {}).get("reason")) + "; yeniden üretilemez")
        if (not build or build.get("status")!="complete" or build.get("revision")!=r["revision"]
                or build.get("source_sha256")!=r.get("source_sha256")
                or build.get("geometry_version")!=r.get("geometry_version")):
            raise ValueError("bu kararlar için güncel STEP yok")
        return Path(build["folder"])/name,types[name]
