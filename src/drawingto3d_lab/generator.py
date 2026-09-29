"""Deterministic parametric parts, and the drawing sheet that goes with each one.

The corpus for the pilot cannot be a pile of downloaded files whose labels nobody can check. Here a
part is defined once, by parameters, and everything else is derived from that single definition:

* the solid (build123d, then `export_step`) — the CAD truth;
* the *printed* dimension set — the numbers and callouts that go on the sheet, taken from the same
  parameters that shaped the solid, never read back out of a picture;
* the label record, in the same schema as `eval/feature_metrics.py` (`drawingto3d.features/1`), so the
  evaluator that judges a produced STEP can judge the corpus labels too;
* the sheet itself: a vector PDF (real text layer, like a CAD export) plus the raster form the
  reading path needs.

The analytic volume of a template is checked against the kernel's own volume, so a label that drifted
away from the geometry is a test failure rather than a silent lie.

Nothing here looks at an image to decide a value, and nothing is randomised: the same parameters give
the same bytes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from build123d import (Align, Box, Cylinder, Pos, Rot, export_step, import_step)

from drawingto3d_lab.pdfvec import PdfPage

MM = (Align.CENTER, Align.CENTER, Align.CENTER)
TEXT_MM = 3.2          # printed callout height
DIM_TEXT_MM = 3.5      # dimension text height
VIEW_LABEL_MM = 3.0


@dataclass(frozen=True)
class PartSpec:
    """One pilot part: parameters only, plus which family it belongs to for splitting."""

    id: str
    family: str
    template: str
    params: Mapping[str, Any]


# ---------------------------------------------------------------- solids


def build_solid(spec: PartSpec):
    """The CAD truth of a part, built from its parameters."""
    p = dict(spec.params)
    if spec.template == "plate_holes":
        part = Box(p["width"], p["depth"], p["thickness"])
        for hole in p["holes"]:
            part = _bore(part, hole)
        return part
    if spec.template == "plate_step":
        part = Box(p["width"], p["depth"], p["thickness"])
        # A step: cut the top end away, leaving `step_height` of full thickness on that side. The box
        # is centred on the origin, so the part's top face is at +thickness/2, not at +thickness.
        part = part - Pos(p["width"] / 2 - p["step_width"] / 2, 0,
                          p["thickness"] / 2 - p["step_height"] / 2) * Box(
            p["step_width"], p["depth"] * 2, p["step_height"])
        for hole in p.get("holes", []):
            part = _bore(part, hole)
        return part
    if spec.template == "block_pocket":
        part = Box(p["width"], p["depth"], p["height"])
        pocket = p["pocket"]
        part = part - Pos(pocket["x"], pocket["y"], p["height"] / 2) * Box(
            pocket["width"], pocket["depth"], 2 * pocket["depth_mm"])
        for hole in p.get("holes", []):
            part = _bore(part, hole)
        return part
    raise ValueError(f"bilinmeyen şablon: {spec.template}")


def _bore(part, hole: Mapping[str, Any]):
    radius = hole["diameter"] / 2.0
    axis = hole.get("axis", "z").lower()
    reach = 4 * max(part.bounding_box().size.X, part.bounding_box().size.Y,
                    part.bounding_box().size.Z)
    if hole.get("through", True):
        length = reach
    else:
        length = float(hole["depth"])
    if axis == "z":
        if hole.get("through", True):
            tool = Pos(hole["x"], hole["y"], 0) * Cylinder(radius, length, align=MM)
        else:
            # A blind hole is drilled into the top face.
            top = part.bounding_box().max.Z
            tool = Pos(hole["x"], hole["y"], top - length / 2) * Cylinder(radius, length, align=MM)
    elif axis == "y":
        tool = Pos(hole["x"], hole["y"], hole["z"]) * Rot(90, 0, 0) * Cylinder(radius, length, align=MM)
    else:
        tool = Pos(hole["x"], hole["y"], hole["z"]) * Rot(0, 90, 0) * Cylinder(radius, length, align=MM)
    return part - tool


# ---------------------------------------------------------------- labels


def analytic_volume_mm3(spec: PartSpec) -> float:
    """The closed-form volume of the template, independent of the kernel.

    `span` is how deep a through hole cuts: the plate thickness, or the block height. A template
    whose holes are placed where that is not the local thickness would need a different formula, so
    the templates keep their holes in the full-thickness region and the kernel check catches it if
    that ever stops being true.
    """
    p = dict(spec.params)
    if spec.template == "plate_holes":
        span = p["thickness"]
        volume = p["width"] * p["depth"] * span
        return volume - sum(_hole_volume(hole, span) for hole in p["holes"])
    if spec.template == "plate_step":
        span = p["thickness"]
        volume = p["width"] * p["depth"] * span
        volume -= p["step_width"] * p["depth"] * p["step_height"]
        return volume - sum(_hole_volume(hole, span) for hole in p.get("holes", []))
    if spec.template == "block_pocket":
        span = p["height"]
        volume = p["width"] * p["depth"] * span
        pocket = p["pocket"]
        volume -= pocket["width"] * pocket["depth"] * pocket["depth_mm"]
        return volume - sum(_hole_volume(hole, span) for hole in p.get("holes", []))
    raise ValueError(spec.template)


def _hole_volume(hole: Mapping[str, Any], span: float) -> float:
    length = span if hole.get("through", True) else float(hole["depth"])
    return math.pi * (hole["diameter"] / 2) ** 2 * length


def labels(spec: PartSpec, *, volume_mm3: float) -> dict:
    """The label record, in the evaluator's schema."""
    p = dict(spec.params)
    features = []
    if spec.template == "plate_holes":
        bbox = [p["width"], p["depth"], p["thickness"]]
        for hole in p["holes"]:
            features.append(_hole_feature(hole, p["thickness"]))
    elif spec.template == "plate_step":
        bbox = [p["width"], p["depth"], p["thickness"]]
        for hole in p.get("holes", []):
            features.append(_hole_feature(hole, p["thickness"]))
    elif spec.template == "block_pocket":
        bbox = [p["width"], p["depth"], p["height"]]
        pocket = p["pocket"]
        features.append({"kind": "pocket", "width_mm": pocket["width"], "depth_mm": pocket["depth"],
                         "height_mm": pocket["depth_mm"], "axis": "Z", "through": False,
                         "centre_mm": [pocket["x"], pocket["y"], p["height"] / 2 + 0.0]})
        for hole in p.get("holes", []):
            features.append(_hole_feature(hole, p["height"]))
    else:  # pragma: no cover - build_solid rejects anything else first
        raise ValueError(spec.template)
    return {"schema": "drawingto3d.features/1", "part_id": spec.id, "family": spec.family,
            "units": "mm", "bbox_size": [round(value, 6) for value in bbox],
            "volume_mm3": round(volume_mm3, 6), "features": features, "unmodelled": {}}


def _hole_feature(hole: Mapping[str, Any], thickness: float) -> dict:
    through = bool(hole.get("through", True))
    axis = hole.get("axis", "z").upper()
    centre = [float(hole["x"]), float(hole["y"]), float(hole.get("z", 0.0))]
    if through and abs(centre[2]) < 1e-9 and axis == "Z":
        centre[2] = 0.0
    return {"kind": "hole", "diameter_mm": float(hole["diameter"]), "centre_mm": centre, "axis": axis,
            "through": through, "depth_mm": None if through else float(hole["depth"])}


def edge_offsets(params: Mapping[str, Any]) -> list[dict]:
    """Where each hole sits measured from the part's left and bottom edges.

    The sheet dimensions hole positions from the edge (that is what `_draw_callouts` draws), so the
    number it prints is the edge distance. Printing the centre coordinate instead — which is what this
    generator did — puts a number on the drawing that the dimension line does not measure: a 60 mm
    plate with a hole 15 mm right of centre is drawn 45 mm from the left edge and was labelled 15.
    """
    width = float(params["width"])
    depth = float(params["depth"])
    offsets = []
    for index, hole in enumerate(params.get("holes", [])):
        offsets.append({"index": index, "hole": [hole["x"], hole["y"]],
                        "x_mm": width / 2.0 + float(hole["x"]), "datum_x": "left_edge",
                        "y_mm": depth / 2.0 + float(hole["y"]), "datum_y": "bottom_edge"})
    return offsets


def printed_dimensions(spec: PartSpec) -> list[dict]:
    """Every number and callout the sheet prints, with its source parameter."""
    p = dict(spec.params)
    dims: list[dict] = []
    if spec.template in ("plate_holes", "plate_step"):
        dims += [{"text": _num(p["width"]), "role": "overall_width", "value_mm": p["width"]},
                 {"text": _num(p["thickness"]), "role": "overall_height", "value_mm": p["thickness"]},
                 {"text": _num(p["depth"]), "role": "overall_depth", "value_mm": p["depth"]}]
    else:
        dims += [{"text": _num(p["width"]), "role": "overall_width", "value_mm": p["width"]},
                 {"text": _num(p["height"]), "role": "overall_height", "value_mm": p["height"]},
                 {"text": _num(p["depth"]), "role": "overall_depth", "value_mm": p["depth"]}]
    if spec.template == "plate_step":
        dims.append({"text": _num(p["step_height"]), "role": "step_height", "value_mm": p["step_height"]})
        dims.append({"text": _num(p["step_width"]), "role": "step_width", "value_mm": p["step_width"]})
    if spec.template == "block_pocket":
        pocket = p["pocket"]
        dims += [{"text": _num(pocket["width"]), "role": "pocket_width", "value_mm": pocket["width"]},
                 {"text": _num(pocket["depth"]), "role": "pocket_depth", "value_mm": pocket["depth"]},
                 {"text": _num(pocket["depth_mm"]), "role": "pocket_height",
                  "value_mm": pocket["depth_mm"]}]
    for hole, offset in zip(p.get("holes", []), edge_offsets(p)):
        callout = f"Ø{_num(hole['diameter'])} "
        callout += "THRU" if hole.get("through", True) else f"DEPTH {_num(hole['depth'])}"
        dims.append({"text": callout, "role": "hole_callout", "value_mm": hole["diameter"],
                     "hole": [hole["x"], hole["y"]]})
        dims.append({"text": _num(offset["x_mm"]), "role": "hole_x", "value_mm": offset["x_mm"],
                     "datum": offset["datum_x"], "hole": [hole["x"], hole["y"]]})
        dims.append({"text": _num(offset["y_mm"]), "role": "hole_y", "value_mm": offset["y_mm"],
                     "datum": offset["datum_y"], "hole": [hole["x"], hole["y"]]})
    return dims


def _num(value: float) -> str:
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- the sheet


@dataclass
class Placed:
    """Where a view landed on the page: the projection's origin and how it was scaled.

    `origin` is the page position of the projection's own (extents[0], extents[1]) corner when the y
    axis is flipped, i.e. the part's bottom-left. `rect` is therefore the part's page rectangle —
    dimensions and callouts are placed against the part's edges, never against a view box.
    """

    name: str
    scale: float
    origin: tuple[float, float]
    extents: tuple[float, float, float, float]

    def to_page(self, x: float, y: float) -> tuple[float, float]:
        return (self.origin[0] + (x - self.extents[0]) * self.scale,
                self.origin[1] - (y - self.extents[1]) * self.scale)

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.origin[0], self.origin[1] - (self.extents[3] - self.extents[1]) * self.scale,
                self.origin[0] + (self.extents[2] - self.extents[0]) * self.scale, self.origin[1])

    @property
    def span_x(self) -> float:
        return (self.extents[2] - self.extents[0]) * self.scale

    @property
    def span_y(self) -> float:
        return (self.extents[3] - self.extents[1]) * self.scale


# Third angle: the top view sits directly above the front view, the right view to its right, and the
# three sit on the same widths, which is what makes a sheet readable.
FRONT_ANCHOR = (45.0, 150.0)     # page mm: the part's bottom-left in the front view
VIEW_GAP_MM = 28.0
SIDE_GAP_MM = 34.0
VIEWPORT = {
    "front": {"viewport": (0, -1.0e4, 0), "up": (0, 0, 1)},
    "top": {"viewport": (0, 0, 1.0e4), "up": (0, 1, 0)},   # looking down, so up cannot be Z
    "right": {"viewport": (1.0e4, 0, 0), "up": (0, 0, 1)},
}
TITLE_BLOCK = (168.0, 180.0, 118.0, 22.0)
LINE_OUTLINE_MM = 0.5
LINE_DIM_MM = 0.18
LINE_HIDDEN_MM = 0.25


def sheet(spec: PartSpec, solid, *, scale: float | None = None) -> tuple[bytes, dict]:
    """A drawing sheet for `spec` as a vector PDF: `(pdf_bytes, layout_record)`."""
    if scale is None:
        scale = choose_scale(solid)
    page = PdfPage()
    record: dict = {"page_mm": [page.width_mm, page.height_mm], "scale": scale, "views": {},
                    "dimensions": [], "callouts": [], "printed_text": [], "part_rects": {}}

    projections = {}
    for name, layout in VIEWPORT.items():
        visible, hidden = solid.project_to_viewport(layout["viewport"], viewport_up=layout["up"],
                                                    look_at=(0, 0, 0))
        projections[name] = (visible, hidden, _view_extents((visible, hidden)))

    front_extents = projections["front"][2]
    front_width = (front_extents[2] - front_extents[0]) * scale
    anchors = {
        "front": FRONT_ANCHOR,
        "top": (FRONT_ANCHOR[0], FRONT_ANCHOR[1] - VIEW_GAP_MM - (projections["top"][2][3] - projections["top"][2][1]) * scale),
        "right": (FRONT_ANCHOR[0] + front_width + SIDE_GAP_MM, FRONT_ANCHOR[1]),
    }

    placed: list[tuple[float, float, float, float]] = []
    views: dict[str, Placed] = {}
    for name, (visible, hidden, extents) in projections.items():
        view = Placed(name=name, scale=scale, origin=anchors[name], extents=extents)
        views[name] = view
        _draw_view(page, visible, hidden, view)
        record["views"][name] = {"part_rect_mm": list(view.rect), "visible_edges": len(visible),
                                 "hidden_edges": len(hidden)}
        record["part_rects"][name] = list(view.rect)
        # Reserve the part's own rectangle so no text is printed on the geometry.
        placed.append((view.rect[0] - 1.0, view.rect[1] - 1.0, view.rect[2] + 1.0, view.rect[3] + 1.0))
        page.text(view.rect[0], view.rect[1] - 3.0, name.upper(), size_mm=VIEW_LABEL_MM, bold=True)
        record["printed_text"].append({"text": name.upper(), "role": "view_label"})

    _draw_dimensions(page, spec, views, record, placed)
    _draw_callouts(page, spec, views, record, placed)
    _draw_title_block(page, spec, scale, record)
    record["text_boxes"] = [list(box) for box in placed]
    return page.to_bytes(), record


def choose_scale(solid) -> float:
    """The largest of the usual drawing scales that lets the part fit every view box."""
    size = solid.bounding_box().size
    needed = max(size.X, size.Y, size.Z)
    for candidate in (5.0, 2.0, 1.0, 0.5, 0.25):
        if needed * candidate <= 90.0:
            return candidate
    return 0.1


def _view_extents(projection) -> tuple[float, float, float, float]:
    visible, hidden = projection
    xs: list[float] = []
    ys: list[float] = []
    for edge in list(visible) + list(hidden):
        box = edge.bounding_box()
        xs += [box.min.X, box.max.X]
        ys += [box.min.Y, box.max.Y]
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _draw_view(page: PdfPage, visible, hidden, view: Placed) -> None:
    for edge in visible:
        page.polyline(_edge_points(edge, view.to_page), width_mm=LINE_OUTLINE_MM)
    for edge in hidden:
        page.polyline(_edge_points(edge, view.to_page), width_mm=LINE_HIDDEN_MM, dash_mm=(1.5, 1.0))


def _edge_points(edge, place, *, samples: int = 48):
    if edge.geom_type.name == "LINE":
        return [place(edge.position_at(0).X, edge.position_at(0).Y),
                place(edge.position_at(1).X, edge.position_at(1).Y)]
    return [place(edge.position_at(index / samples).X, edge.position_at(index / samples).Y)
            for index in range(samples + 1)]


def _draw_dimensions(page: PdfPage, spec: PartSpec, views: dict, record: dict, placed: list) -> None:
    p = dict(spec.params)
    height = p["thickness"] if spec.template != "block_pocket" else p["height"]
    front = views["front"]
    top = views["top"]
    front_left, front_top, front_right, front_bottom = front.rect
    top_left, top_top, _, top_bottom = top.rect

    _dim(page, record, "overall_width", _num(p["width"]), (front_left, front_bottom + 6),
         (front_right, front_bottom + 6), placed, side="below")
    _dim(page, record, "overall_height", _num(height), (front_left, front_top),
         (front_left, front_bottom), placed, side="left")
    _dim(page, record, "overall_depth", _num(p["depth"]), (top_left, top_top), (top_left, top_bottom),
         placed, side="left")

    if spec.template == "plate_step":
        step_x = front.to_page(p["width"] / 2.0 - p["step_width"], 0.0)[0]
        _dim(page, record, "step_width", _num(p["step_width"]), (step_x, front_bottom + 6),
             (front_right, front_bottom + 6), placed, side="below", offset_mm=24.0)
        # `step_height` is a measurement in Z, so the dimension line runs vertically from the part's
        # top face down to the step's floor, at the notch's left wall. It used to be drawn as a
        # horizontal line across the step's width — 40 mm long under a printed "3", which the corpus QA
        # now catches by comparing the number with the span its own dimension line covers.
        floor_z = p["thickness"] / 2.0 - p["step_height"]
        notch = front.to_page(p["width"] / 2.0 - p["step_width"] / 2.0, 0.0)[0]
        _dim(page, record, "step_height", _num(p["step_height"]),
             (notch, front.to_page(0.0, p["thickness"] / 2.0)[1]),
             (notch, front.to_page(0.0, floor_z)[1]), placed, side="left", offset_mm=10.0)

    if spec.template == "block_pocket":
        pocket = p["pocket"]
        centre = top.to_page(pocket["x"], pocket["y"])
        _dim(page, record, "pocket_width", _num(pocket["width"]),
             (centre[0] - pocket["width"] * top.scale / 2, centre[1] + 4),
             (centre[0] + pocket["width"] * top.scale / 2, centre[1] + 4), placed, side="below",
             offset_mm=9.0)
        _dim(page, record, "pocket_depth", _num(pocket["depth"]),
             (centre[0], centre[1] - pocket["depth"] * top.scale / 2),
             (centre[0], centre[1] + pocket["depth"] * top.scale / 2), placed, side="left",
             offset_mm=9.0)
        # The pocket's own depth: dimensioned on the front view, from the top face down to the floor.
        # The sheet printed only the pocket's plan size before, while the labels claimed a
        # `pocket_height` — a number the drawing never carried.
        floor_z = p["height"] / 2.0 - pocket["depth_mm"]
        _dim(page, record, "pocket_height", _num(pocket["depth_mm"]),
             (front_right, front.to_page(0.0, p["height"] / 2.0)[1]),
             (front_right, front.to_page(0.0, floor_z)[1]), placed, side="right")


def _dim(page: PdfPage, record: dict, role: str, text: str, start, end, placed: list, *,
         side: str, offset_mm: float = 13.0, **extra):
    """Draw one dimension and record what it prints *and* the two points it measures between.

    They are recorded together on purpose: QA can then check that the number equals the span the
    dimension line actually covers (divided by the sheet's scale), so a datum that does not match the
    printed value is a finding rather than something only a human eye would catch.
    """
    box = _linear_dim(page, start, end, text, placed, side=side, offset_mm=offset_mm)
    _note(record, role, text, box, span=[list(start), list(end)], **extra)
    return box


def _note(record: dict, role: str, text: str, box, **extra) -> None:
    record["dimensions"].append({"role": role, "text": text, "box": list(box), **extra})
    record["printed_text"].append({"text": text, "role": role, **extra})


def _linear_dim(page: PdfPage, start, end, text: str, placed: list, *, side: str,
                offset_mm: float = 13.0, tick_mm: float = 2.0) -> tuple[float, float, float, float]:
    """A dimension line with extension lines, arrows and the number, drawn outside the geometry."""
    horizontal = abs(start[1] - end[1]) < 1e-6
    size = DIM_TEXT_MM
    if horizontal:
        sign = 1.0 if side == "below" else -1.0
        y = start[1] + sign * offset_mm
        for point in (start, end):
            page.line(point, (point[0], y + sign * tick_mm), width_mm=LINE_DIM_MM)
        page.line((start[0], y), (end[0], y), width_mm=LINE_DIM_MM)
        page.arrow((start[0], y), (1, 0))
        page.arrow((end[0], y), (-1, 0))
        if abs(end[0] - start[0]) < 6.0:  # too narrow for arrows inside: keep them outside
            page.arrow((start[0], y), (-1, 0))
            page.arrow((end[0], y), (1, 0))
        box = (start[0], y - size * 1.2, end[0], y)
        box = _place_text(page, text, (start[0] + end[0]) / 2, y - 1.0, size, "center", placed, box)
    else:
        sign = 1.0 if side == "left" else -1.0
        x = start[0] + sign * offset_mm
        for point in (start, end):
            page.line(point, (x + sign * tick_mm, point[1]), width_mm=LINE_DIM_MM)
        page.line((x, start[1]), (x, end[1]), width_mm=LINE_DIM_MM)
        page.arrow((x, start[1]), (0, 1))
        page.arrow((x, end[1]), (0, -1))
        if abs(end[1] - start[1]) < 6.0:
            page.arrow((x, start[1]), (0, -1))
            page.arrow((x, end[1]), (0, 1))
        box = (x, min(start[1], end[1]), x, max(start[1], end[1]))
        box = _place_text(page, text, x - 1.0, (start[1] + end[1]) / 2 + size / 2, size, "right", placed, box)
    return box


def _draw_callouts(page: PdfPage, spec: PartSpec, views: dict, record: dict, placed: list) -> None:
    """One leader per hole in the top view: the printed diameter and kind, then its two positions."""
    p = dict(spec.params)
    holes = list(p.get("holes", []))
    if not holes:
        return
    top = views["top"]
    left, top_edge, right, bottom = top.rect
    offsets = edge_offsets(p)
    for index, hole in enumerate(holes):
        offset = offsets[index]
        centre = top.to_page(hole["x"], hole["y"])
        text = f"Ø{_num(hole['diameter'])} " + ("THRU" if hole.get("through", True)
                                               else f"DEPTH {_num(hole['depth'])}")
        reach = 13.0 + page.text_width(text, TEXT_MM)
        # A leader that would run off the sheet is drawn to the left instead.
        direction = -1.0 if centre[0] + reach > page.width_mm - 12.0 else 1.0
        elbow = (centre[0] + direction * 13.0, centre[1] - 13.0)
        shoulder = (elbow[0] + direction * 11.0, elbow[1])
        page.line(centre, elbow, width_mm=LINE_DIM_MM)
        page.line(elbow, shoulder, width_mm=LINE_DIM_MM)
        page.arrow(centre, (-direction, 1))
        size = TEXT_MM
        width = page.text_width(text, size)
        box = (shoulder[0] if direction > 0 else shoulder[0] - width, shoulder[1] - size * 1.2,
               shoulder[0] + width if direction > 0 else shoulder[0], shoulder[1] + size * 0.3)
        align = "left" if direction > 0 else "right"
        box = _place_text(page, text, shoulder[0] + direction * 1.0, shoulder[1], size, align, placed, box)
        record["callouts"].append({"hole": [hole["x"], hole["y"]], "text": text, "box": list(box)})
        _note(record, "hole_callout", text, box, hole=[hole["x"], hole["y"]])

        row = bottom + 6 + 11.0 * index
        # The dimension line runs from the view's left edge to the hole centre, so the number printed
        # is that distance (the edge datum), not the hole's coordinate about the part centre.
        x_text = _num(offset["x_mm"])
        _dim(page, record, "hole_x", x_text, (left, row), (centre[0], row), placed, side="below",
             offset_mm=11.0, hole=[hole["x"], hole["y"]], datum=offset["datum_x"],
             value_mm=offset["x_mm"])

        column = right + 6 + 11.0 * index
        bottom_edge = top.to_page(hole["x"], top.extents[1])
        y_text = _num(offset["y_mm"])
        _dim(page, record, "hole_y", y_text, (column, bottom_edge[1]), (column, centre[1]), placed,
             side="right", offset_mm=11.0, hole=[hole["x"], hole["y"]], datum=offset["datum_y"],
             value_mm=offset["y_mm"])


def _place_text(page: PdfPage, text: str, x: float, y: float, size_mm: float, align: str,
                placed: list, box) -> tuple[float, float, float, float]:
    """Print the text, nudging it until it does not sit on text or on a view already placed."""
    for shift in (0.0, 5.0, 10.0, 15.0, 20.0):
        candidate = _shift(box, align, shift)
        if not any(_overlap(candidate, other) for other in placed):
            page.text(x + _dx(align, shift), y + _dy(align, shift), text, size_mm=size_mm, align=align)
            placed.append(candidate)
            return candidate
    page.text(x, y, text, size_mm=size_mm, align=align)
    placed.append(box)
    return box


def _dx(align: str, shift: float) -> float:
    return shift if align == "left" else (-shift if align == "right" else 0.0)


def _dy(align: str, shift: float) -> float:
    return shift if align == "center" else 0.0


def _shift(box, align: str, shift: float):
    dx, dy = _dx(align, shift), _dy(align, shift)
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


def _overlap(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _draw_title_block(page: PdfPage, spec: PartSpec, scale: float, record: dict) -> None:
    left, top, width, height = TITLE_BLOCK
    page.polyline([(left, top), (left + width, top), (left + width, top + height), (left, top + height)],
                  width_mm=LINE_OUTLINE_MM, close=True)
    for offset in (7.5, 15.0):
        page.line((left, top + offset), (left + width, top + offset), width_mm=LINE_DIM_MM)
    page.line((left + 62.0, top), (left + 62.0, top + height), width_mm=LINE_DIM_MM)
    rows = [
        (f"PART {spec.id}", f"SCALE 1:{_num(1 / scale)}"),
        ("UNITS mm", "THIRD ANGLE"),
        ("DRAWINGTO3D SYNTHETIC SHEET", f"FAMILY {spec.family}"),
    ]
    for row, (first, second) in enumerate(rows):
        baseline = top + 5.5 + 7.5 * row
        page.text(left + 2.0, baseline, first, size_mm=3.4, bold=row == 0)
        page.text(left + 64.0, baseline, second, size_mm=3.4)
        record["printed_text"] += [{"text": first, "role": "title_block"},
                                   {"text": second, "role": "title_block"}]
    record["title_block"] = {"box_mm": list(TITLE_BLOCK), "part": spec.id, "scale": scale}


def write_part(spec: PartSpec, directory: Path, *, scale: float | None = None) -> dict:
    """Build one part and write its STEP, sheet (PDF + PNG) and labels. Returns the record."""
    from drawingto3d_lab.state import atomic_write_text, sha256_file, write_json

    directory.mkdir(parents=True, exist_ok=True)
    solid = build_solid(spec)
    measured = solid.volume
    analytic = analytic_volume_mm3(spec)
    if abs(measured - analytic) > max(1e-6, analytic * 1e-9):
        raise AssertionError(f"{spec.id}: kernel hacmi {measured} ile analitik {analytic} uyuşmuyor")

    step_path = directory / "part.step"
    export_step(solid, str(step_path))
    pdf_bytes, layout = sheet(spec, solid, scale=scale)
    pdf_path = directory / "drawing.pdf"
    pdf_path.write_bytes(pdf_bytes)
    png_path = directory / "drawing.png"
    render_png(pdf_path, png_path, dpi=200)
    label_payload = labels(spec, volume_mm3=measured)
    label_payload["printed_dimensions"] = printed_dimensions(spec)
    label_payload["provenance"] = provenance(spec)
    labels_path = directory / "labels.json"
    write_json(labels_path, label_payload)
    write_json(directory / "sheet-layout.json", layout)

    return {
        "part_id": spec.id, "family": spec.family, "template": spec.template,
        "step": str(step_path), "step_sha256": sha256_file(step_path),
        "drawing_pdf": str(pdf_path), "drawing_pdf_sha256": sha256_file(pdf_path),
        "drawing_png": str(png_path), "drawing_png_sha256": sha256_file(png_path),
        "labels": str(labels_path), "labels_sha256": sha256_file(labels_path),
        "volume_mm3": round(measured, 6), "analytic_volume_mm3": round(analytic, 6),
        "features": len(label_payload["features"]),
    }


def render_png(pdf_path: Path, png_path: Path, *, dpi: int = 200) -> None:
    """Rasterise the sheet, the way the reading path will see it."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    page = document[0]
    # pdfium takes an integer upsampling factor; 200 dpi is the nearest whole multiple of 72.
    bitmap = page.render(scale=max(1, round(dpi / 72.0)))
    image = bitmap.to_pil()
    image.convert("RGB").save(png_path, format="PNG")
    document.close()


def provenance(spec: PartSpec) -> dict:
    return {
        "source": "deterministic parametric generator (src/drawingto3d_lab/generator.py)",
        "family": spec.family,
        "template": spec.template,
        "parameters": dict(spec.params),
        "unit": "mm",
        "basis": "parameters define both the solid and the printed numbers; labels are not read "
                 "from any image",
        "license": "generated in-repo, no third-party CAD data",
        "acquired_at": "2026-09-29",
        "method": "build123d solid → export_step; HLR projection → vector PDF → raster PNG",
    }


def reimport_step(path: Path):
    """Re-open a STEP written by this module (used to prove immutability and validity)."""
    return import_step(str(path))
