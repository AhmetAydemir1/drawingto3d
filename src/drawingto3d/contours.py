"""Closed part outlines from orthographic views, in pixels."""

from __future__ import annotations

import cv2
import numpy as np

from drawingto3d.schema import Span, View


def view_outline(image_bgr: np.ndarray, view: View, spans: list[Span] | None = None) -> np.ndarray | None:
    outer, _islands = _profiles(image_bgr, view, spans or [])
    return outer


def view_islands(image_bgr: np.ndarray, view: View, spans: list[Span] | None = None) -> list[np.ndarray]:
    _outer, islands = _profiles(image_bgr, view, spans or [])
    return islands


def _profiles(
    image_bgr: np.ndarray, view: View, spans: list[Span]
) -> tuple[np.ndarray | None, list[np.ndarray]]:
    x, y, w, h = (int(view.bbox.x), int(view.bbox.y), int(view.bbox.w), int(view.bbox.h))
    if w < 3 or h < 3:
        return None, []
    crop = image_bgr[y : y + h, x : x + w]
    if crop.size == 0:
        return None, []
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _mask_spans(gray, spans, x, y)
    ink = (gray < 180).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, hierarchy = cv2.findContours(ink, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:
        return None, []
    hier = hierarchy[0]
    external = [index for index, item in enumerate(hier) if item[3] < 0]
    if not external:
        return None, []
    outer_index = max(external, key=lambda index: cv2.contourArea(contours[index]))
    if cv2.contourArea(contours[outer_index]) < 0.02 * w * h:
        return None, []
    outer = _simplify(contours[outer_index])
    if outer is None:
        return None, []
    islands: list[np.ndarray] = []
    child = hier[outer_index][2]
    while child >= 0:
        area = cv2.contourArea(contours[child])
        if area > 0.005 * w * h and not _circular(contours[child]):
            island = _simplify(contours[child])
            if island is not None:
                islands.append(island)
        child = hier[child][0]
    outer = outer.astype(float)
    outer[:, 0] += x
    outer[:, 1] += y
    shifted: list[np.ndarray] = []
    for island in islands:
        island = island.astype(float)
        island[:, 0] += x
        island[:, 1] += y
        shifted.append(island)
    return outer, shifted


def _mask_spans(gray: np.ndarray, spans: list[Span], origin_x: int, origin_y: int) -> None:
    height, width = gray.shape[:2]
    for span in spans:
        x0 = int(span.bbox.x) - origin_x - 2
        y0 = int(span.bbox.y) - origin_y - 2
        x1 = int(span.bbox.x + span.bbox.w) - origin_x + 2
        y1 = int(span.bbox.y + span.bbox.h) - origin_y + 2
        if x1 < 0 or y1 < 0 or x0 >= width or y0 >= height:
            continue
        gray[max(0, y0) : min(height, y1), max(0, x0) : min(width, x1)] = 255


def _simplify(contour: np.ndarray) -> np.ndarray | None:
    perimeter = cv2.arcLength(contour, True)
    if perimeter < 1:
        return None
    approx = cv2.approxPolyDP(contour, 0.01 * perimeter, True)
    if len(approx) < 3:
        return None
    return approx.reshape(-1, 2)


def _circular(contour: np.ndarray) -> bool:
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    if area < 1 or perimeter < 1:
        return False
    return 4 * 3.14159265 * area / (perimeter * perimeter) > 0.82
