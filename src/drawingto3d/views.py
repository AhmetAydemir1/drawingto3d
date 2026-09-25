"""Split a sheet into views. The isometric picture is not part of the solid."""

from __future__ import annotations

import cv2
import numpy as np

from drawingto3d.schema import BBox, Page, View, ViewKind


def segment_views(page: Page) -> list[View]:
    image = cv2.imdecode(np.frombuffer(page.image_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ink = (gray < 180).astype(np.uint8) * 255
    height, width = ink.shape
    # Drop the sheet border so it is not treated as a view.
    margin_x = int(width * 0.04)
    margin_y = int(height * 0.04)
    ink[:margin_y, :] = 0
    ink[-margin_y:, :] = 0
    ink[:, :margin_x] = 0
    ink[:, -margin_x:] = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []
    page_area = width * height
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < page_area * 0.02 or area > page_area * 0.7:
            continue
        if w < width * 0.08 or h < height * 0.08:
            continue
        boxes.append((x, y, w, h))
    boxes = _merge_overlaps(boxes)
    split: list[tuple[int, int, int, int]] = []
    for box in boxes:
        split.extend(_split_stacked(ink, box))
    boxes = split
    ranked = sorted(boxes, key=lambda item: (item[1], item[0]))
    ortho = [box for box in ranked if box[0] <= width * 0.55 or box[2] >= width * 0.45]
    section_box = max(ortho, key=lambda box: _hatch_score(ink[box[1] : box[1] + box[3], box[0] : box[0] + box[2]]), default=None)
    kinds = _third_angle_kinds(ranked, section_box, width)
    views: list[View] = []
    for index, box in enumerate(ranked):
        kind = kinds.get(box, ViewKind.unknown)
        views.append(
            View(
                id=f"view-{index}",
                kind=kind,
                bbox=BBox(x=float(box[0]), y=float(box[1]), w=float(box[2]), h=float(box[3])),
                section_label=None,
                used_for_solid=kind not in {ViewKind.isometric, ViewKind.unknown},
            )
        )
    return views


def layout_conflict(views: list[View]) -> bool:
    """Third-angle placement could not name every solid view."""
    return any(view.kind == ViewKind.unknown for view in views)


def _third_angle_kinds(
    ranked: list[tuple[int, int, int, int]],
    section_box: tuple[int, int, int, int] | None,
    width: int,
) -> dict[tuple[int, int, int, int], ViewKind]:
    """Bottom-centre is front, above it is plan, to its right is side. Hatch stays section."""
    kinds: dict[tuple[int, int, int, int], ViewKind] = {}
    for box in ranked:
        if section_box is not None and box == section_box:
            kinds[box] = ViewKind.section
        elif box[0] > width * 0.55 and box[2] < width * 0.45:
            kinds[box] = ViewKind.isometric
    rest = [box for box in ranked if box not in kinds]
    if not rest:
        return kinds

    def center_x(box: tuple[int, int, int, int]) -> float:
        return box[0] + box[2] / 2

    def center_y(box: tuple[int, int, int, int]) -> float:
        return box[1] + box[3] / 2

    leftish = [box for box in rest if center_x(box) < width * 0.62] or rest
    front = max(leftish, key=center_y)
    kinds[front] = ViewKind.front
    front_cx, front_cy = center_x(front), center_y(front)
    for box in rest:
        if box == front:
            continue
        if center_x(box) > front_cx + front[2] * 0.25:
            kinds[box] = ViewKind.side
        elif center_y(box) < front_cy - 20:
            kinds[box] = ViewKind.plan
        else:
            kinds[box] = ViewKind.unknown
    return kinds


def _split_stacked(ink: np.ndarray, box: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
    x, y, w, h = box
    if h < 160:
        return [box]
    crop = ink[y : y + h, x : x + w]
    density = crop.mean(axis=1)
    start, stop = h // 5, 4 * h // 5
    band = density[start:stop]
    if band.size == 0 or float(band.min()) > 8:
        return [box]
    valley = start + int(np.argmin(band))
    if valley < 50 or h - valley < 50:
        return [box]
    return [(x, y, w, valley), (x, y + valley, w, h - valley)]


def _merge_overlaps(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    pending = list(boxes)
    merged: list[tuple[int, int, int, int]] = []
    while pending:
        x, y, w, h = pending.pop(0)
        changed = True
        while changed:
            changed = False
            rest = []
            for other in pending:
                if _iou((x, y, w, h), other) > 0.05 or _contains((x, y, w, h), other):
                    x, y, w, h = _union((x, y, w, h), other)
                    changed = True
                else:
                    rest.append(other)
            pending = rest
        merged.append((x, y, w, h))
    return merged


def _hatch_score(crop: np.ndarray) -> float:
    edges = cv2.Canny(crop, 40, 120)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=20, minLineLength=8, maxLineGap=3)
    if lines is None:
        return 0.0
    short = 0
    rows = lines.reshape(-1, 4)
    for line in rows:
        x0, y0, x1, y1 = [float(value) for value in line]
        length = float(np.hypot(x1 - x0, y1 - y0))
        if 8 <= length <= 40:
            short += 1
    return short / max(1.0, crop.shape[0] * crop.shape[1] / 400.0)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def _contains(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return b[0] >= a[0] and b[1] >= a[1] and b[0] + b[2] <= a[0] + a[2] and b[1] + b[3] <= a[1] + a[3]


def _union(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return x0, y0, x1 - x0, y1 - y0
