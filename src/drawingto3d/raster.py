"""Raster sheets read into the same observation records as vector ones — measured, not smoothed.

CV reads what pixels can support: straight strokes merged from Hough segments, circles proposed
by Hough and then *verified against the ink they claim* (enough of the circumference must
actually be drawn, and the interior must be empty enough for a hole), and printed phrases from
tesseract OCR, each carrying its confidence. The record states its own limits:

- no source paths: a raster has no subpath to cite, so `paths` stays empty and every primitive
  is a pixel measurement, not a citation of the file's own drawing commands;
- arcs are not fitted yet (straight strokes and full circles only);
- dimension anchors are not found yet, so binding waits for its own raster slice — this record
  is what that anchor finder will read;
- circle detection is high-precision, moderate-recall: dashed (hidden) circles and small circles
  in dense clusters can pass under the gates, and the gates are named in the notes.

Nothing here is rounded into belief: each circle carries the fraction of its circumference that
lies on ink, each line the spread of the segments merged into it, each phrase its OCR confidence.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from drawingto3d.ingest import parse_dimension_unit, split_count
from drawingto3d.observe import (sheet_frame, Frame, Observations, Primitive, SourceRef, TextObservation,
                                 Unsupported)
from drawingto3d.plan import source_hash
from drawingto3d.schema import BBox

RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
INK_THRESHOLD = 180
MIN_LINE_LENGTH_PX = 40.0
ANGLE_TOLERANCE_DEGREES = 2.5
OFFSET_TOLERANCE_PX = 3.0
CIRCLE_PARAM2 = 60
CIRCLE_MIN_DIST_PX = 15
CIRCLE_MIN_RADIUS_PX = 5
CIRCLE_MAX_RADIUS_FRACTION = 0.35
CIRCLE_COVERAGE_MIN = 0.85
CIRCLE_INTERIOR_MAX = 0.25
CIRCLE_SAMPLES = 72
CIRCLE_RADIUS_REFINE_PX = 6.0

# Arcs: a partial circle never fills the strict pass's accumulator, so a second, weaker pass proposes
# candidates and the *support* decides — how long a stretch of the ring is ink, and how solid it is
# within that stretch. A run long enough to be the whole circle is the strict pass's business, not ours.
ARC_PARAM2 = 30
ARC_SAMPLES = 144
ARC_MIN_SPAN_DEGREES = 45.0
ARC_SPAN_COVERAGE_MIN = 0.75
ARC_CIRCLE_FRACTION = 0.85
ARC_MIN_SAGITTA_PX = 4.0         # ink that bulges less than this over its own chord is a straight edge
ARC_MIN_RADIUS_PX = 12.0         # the weak pass rings glyphs and ink blobs; a drawn arc is bigger
ARC_RADIUS_TO_MEDIAN_LINE = 0.12  # and not vanishing next to the strokes it joins
CIRCLE_FRAGMENT_TOLERANCE_PX = 7.0
CIRCLE_FRAGMENT_MAX_LENGTH_PX = 80.0
GLYPH_BOX_MAX_FRACTION = 0.03
OCR_PSM = "11"
OCR_TIMEOUT_S = 240.0


def _rounded(value: float) -> float:
    return float(round(value, 2))


def _dpi(path: Path) -> float | None:
    """The image's own stated resolution, when it states one (a scan usually does)."""
    try:
        with Image.open(path) as image:
            dpi = image.info.get("dpi")
    except (OSError, ValueError, TypeError):
        return None
    if isinstance(dpi, tuple) and dpi:
        return float(dpi[0])
    if isinstance(dpi, (int, float)):
        return float(dpi)
    return None


def _segments(ink: np.ndarray) -> list[np.ndarray]:
    found = cv2.HoughLinesP(ink * 255, 1, np.pi / 360, threshold=50,
                            minLineLength=int(MIN_LINE_LENGTH_PX), maxLineGap=3)
    if found is None:
        return []
    return [segment for segment in found.reshape(-1, 4)]


def _merged_lines(ink: np.ndarray) -> list[tuple[np.ndarray, np.ndarray, float]]:
    """Cluster near-collinear overlapping segments into full strokes.

    A drawn line arrives as several Hough segments; the merge groups them by angle and
    perpendicular offset (both tolerances named above), takes the longest segment's direction,
    and reports how far the merged members sat from the resulting centre line.
    """
    items = []
    for x1, y1, x2, y2 in _segments(ink):
        start = np.array([x1, y1], dtype=float)
        end = np.array([x2, y2], dtype=float)
        delta = end - start
        length = float(np.linalg.norm(delta))
        if length < MIN_LINE_LENGTH_PX:
            continue
        unit = delta / length
        items.append({"start": start, "end": end, "unit": unit, "length": length,
                      "angle": float(np.degrees(np.arctan2(unit[1], unit[0]))) % 180.0})
    items.sort(key=lambda item: item["angle"])
    used = [False] * len(items)
    merged: list[tuple[np.ndarray, np.ndarray, float]] = []
    for index, seed in enumerate(items):
        if used[index]:
            continue
        used[index] = True
        cluster = [seed]
        normal = np.array([-seed["unit"][1], seed["unit"][0]])
        origin = seed["start"]
        for other_index in range(index + 1, len(items)):
            if used[other_index]:
                continue
            other = items[other_index]
            gap = abs(other["angle"] - seed["angle"])
            if min(gap, 180.0 - gap) > ANGLE_TOLERANCE_DEGREES:
                continue
            if (abs(float(np.dot(other["start"] - origin, normal))) <= OFFSET_TOLERANCE_PX
                    and abs(float(np.dot(other["end"] - origin, normal))) <= OFFSET_TOLERANCE_PX):
                cluster.append(other)
                used[other_index] = True
        points = np.array([p for item in cluster for p in (item["start"], item["end"])])
        direction = max(cluster, key=lambda item: item["length"])["unit"]
        centre = points.mean(axis=0)
        along = points @ direction
        axis = float(centre @ direction)
        start = centre + direction * (float(along.min()) - axis)
        end = centre + direction * (float(along.max()) - axis)
        offsets = (points - centre) @ np.array([-direction[1], direction[0]])
        merged.append((start, end, float(np.abs(offsets).max())))
    merged.sort(key=lambda item: ((item[0][1] + item[1][1]) / 2, (item[0][0] + item[1][0]) / 2))
    return merged


def _circle_candidates(image: np.ndarray) -> list[tuple[float, float, float]]:
    found = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, dp=1.5, minDist=CIRCLE_MIN_DIST_PX,
                             param1=120, param2=CIRCLE_PARAM2, minRadius=CIRCLE_MIN_RADIUS_PX,
                             maxRadius=int(CIRCLE_MAX_RADIUS_FRACTION * min(image.shape)))
    if found is None:
        return []
    return [(float(cx), float(cy), float(radius)) for cx, cy, radius in found[0]]


def _circumference_coverage(ink: np.ndarray, cx: float, cy: float, radius: float,
                            samples: int = CIRCLE_SAMPLES) -> float:
    """Fraction of sampled circumference points that land on ink (±1 px)."""
    height, width = ink.shape
    angles = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
    hits = 0
    for angle in angles:
        x = int(round(cx + radius * np.cos(angle)))
        y = int(round(cy + radius * np.sin(angle)))
        if 0 <= x < width and 0 <= y < height and ink[max(0, y - 1):y + 2, max(0, x - 1):x + 2].any():
            hits += 1
    return hits / samples


def _refined_radius(ink: np.ndarray, cx: float, cy: float, radius: float) -> float:
    """Hough's radius can sit a few pixels short of the drawn line; measure instead of gating:
    scan the neighbourhood coarsely and keep the radius that lands on the most ink."""
    best_radius, best_coverage = radius, -1.0
    low = max(radius - CIRCLE_RADIUS_REFINE_PX, 1.0)
    for candidate in np.arange(low, radius + CIRCLE_RADIUS_REFINE_PX + 0.5, 1.0):
        coverage = _circumference_coverage(ink, cx, cy, float(candidate), samples=24)
        if coverage > best_coverage or (coverage == best_coverage
                                        and abs(candidate - radius) < abs(best_radius - radius)):
            best_radius, best_coverage = float(candidate), coverage
    return best_radius


def _interior_ink(ink: np.ndarray, cx: float, cy: float, radius: float) -> float:
    """Fraction of the disc inside the circle that is ink: a hole is empty, hatching is not."""
    height, width = ink.shape
    inner = max(int(radius - 3), 1)
    x0, x1 = max(int(cx - inner), 0), min(int(cx + inner) + 1, width)
    y0, y1 = max(int(cy - inner), 0), min(int(cy + inner) + 1, height)
    if x1 <= x0 or y1 <= y0:
        return 1.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= inner ** 2
    if not disc.any():
        return 1.0
    return float(ink[y0:y1, x0:x1][disc].mean())


def _verified_circles(ink: np.ndarray, candidates: list[tuple[float, float, float]],
                      boxes: list[BBox]) -> list[tuple[float, float, float, float]]:
    """Candidates that survive the circumference, interior and glyph-box gates; duplicates of one
    drawn stroke (inner and outer edge) collapse, best coverage first."""
    kept = []
    for cx, cy, radius in candidates:
        measured = _refined_radius(ink, cx, cy, radius)
        coverage = _circumference_coverage(ink, cx, cy, measured)
        if coverage < CIRCLE_COVERAGE_MIN:
            continue
        if _interior_ink(ink, cx, cy, measured) > CIRCLE_INTERIOR_MAX:
            continue
        if any(box.x - 2 <= cx <= box.x + box.w + 2 and box.y - 2 <= cy <= box.y + box.h + 2
               for box in boxes):
            continue  # a circle living inside a word box is a glyph, not a feature
        kept.append((cx, cy, measured, coverage))
    kept.sort(key=lambda item: -item[3])
    deduped: list[tuple[float, float, float, float]] = []
    for item in kept:
        if all(np.hypot(item[0] - other[0], item[1] - other[1]) > max(6.0, 0.05 * item[2])
               or abs(item[2] - other[2]) > max(5.0, 0.05 * item[2]) for other in deduped):
            deduped.append(item)
    deduped.sort(key=lambda item: (item[1], item[0]))
    return deduped


def _point_at_segment(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    """Perpendicular distance from a point to a drawn segment, endpoints included."""
    run = end - start
    length_squared = float(run @ run) or 1.0
    t = float(np.clip((point - start) @ run / length_squared, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + t * run)))


def _trim_to_own_ink(points: np.ndarray,
                     lines: list[tuple[np.ndarray, np.ndarray, float]] | None = None) -> np.ndarray:
    """Cut the arc's run back to ink no straight stroke covers.

    A tangent line's ink lies within a pixel of the ring for some twenty pixels past the tangent
    point, so the run keeps going along it and the arc's end lands *on the line* instead of at the
    joined corner: the loop then cannot close, which is exactly why a curved raster outline stayed
    open. A point a straight stroke also covers is the stroke's ink, not the arc's.
    """
    if not lines or len(points) <= 6:
        return points
    covered = lambda point: any(_point_at_segment(point, start, end) <= 2.5 for start, end, _residual in lines)
    low, high = 0, len(points)
    while low < high - 5 and covered(points[low]):
        low += 1
    while high - 1 > low + 5 and covered(points[high - 1]):
        high -= 1
    return points[low:high]


def _arc_candidates(image: np.ndarray) -> list[tuple[float, float, float]]:
    """The weaker Hough pass: partial circles show up here that the full-circle gate throws away."""
    found = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, dp=1.5, minDist=max(CIRCLE_MIN_DIST_PX // 2, 1),
                             param1=120, param2=ARC_PARAM2, minRadius=CIRCLE_MIN_RADIUS_PX,
                             maxRadius=int(CIRCLE_MAX_RADIUS_FRACTION * min(image.shape)))
    if found is None:
        return []
    return [(float(cx), float(cy), float(radius)) for cx, cy, radius in found[0]]


def _angular_support(ink: np.ndarray, cx: float, cy: float, radius: float,
                     samples: int = ARC_SAMPLES) -> np.ndarray:
    """Which sampled angles land on ink (±1 px): the ring's own evidence, one boolean per angle."""
    height, width = ink.shape
    hits = np.zeros(samples, dtype=bool)
    for index, angle in enumerate(np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)):
        x = int(round(cx + radius * np.cos(angle)))
        y = int(round(cy + radius * np.sin(angle)))
        hits[index] = (0 <= x < width and 0 <= y < height
                       and bool(ink[max(0, y - 1):y + 2, max(0, x - 1):x + 2].any()))
    return hits


def _ink_point(ink: np.ndarray, cx: float, cy: float, angle: float, expected: float,
               window: float = 8.0) -> np.ndarray | None:
    """The first ink pixel along one ray, searched around `expected`: the arc's own evidence."""
    for distance in np.arange(max(1.0, expected - window), expected + window + 0.5, 1.0):
        x = int(round(cx + distance * np.cos(angle)))
        y = int(round(cy + distance * np.sin(angle)))
        if 0 <= x < ink.shape[1] and 0 <= y < ink.shape[0] and ink[y, x]:
            return np.array([float(x), float(y)])
    return None


def _fit_circle(points: np.ndarray) -> tuple[float, float, float]:
    """Kasa's algebraic circle fit: the ring the run's own ink sits on, not Hough's guess at it."""
    x, y = points[:, 0], points[:, 1]
    design = np.column_stack([2.0 * x, 2.0 * y, np.ones(len(x))])
    solution, *_rest = np.linalg.lstsq(design, x ** 2 + y ** 2, rcond=None)
    cx, cy, constant = (float(value) for value in solution)
    return cx, cy, float(np.sqrt(max(constant + cx ** 2 + cy ** 2, 0.0)))


def _ink_radius(ink: np.ndarray, cx: float, cy: float, angle: float, expected: float,
                window: float = 8.0) -> float | None:
    """Where the ink actually sits along one ray, searched around `expected`, or None if there is none."""
    point = _ink_point(ink, cx, cy, angle, expected, window)
    return None if point is None else float(np.hypot(point[0] - cx, point[1] - cy))


def _longest_ring_run(hits: np.ndarray) -> tuple[int, int]:
    """The longest unbroken run of ink around the ring, as (first angle index, length)."""
    if hits.all():
        return 0, len(hits)
    doubled = np.concatenate([hits, hits])
    best_start, best_length, start, length = 0, 0, 0, 0
    for index, hit in enumerate(doubled):
        if hit:
            length += 1
            if length > best_length:
                best_length, best_start = length, index - length + 1
        else:
            length = 0
    return best_start % len(hits), min(best_length, len(hits))


def _median_line_length(lines: list[tuple[np.ndarray, np.ndarray, float]] | None) -> float:
    """The sheet's typical stroke length: what "vanishingly small" means for a ring on that sheet."""
    if not lines:
        return 0.0
    return float(np.median([float(np.linalg.norm(end - start)) for start, end, _residual in lines]))


def _verified_arcs(ink: np.ndarray, candidates: list[tuple[float, float, float]], boxes: list[BBox],
                   circles: list[tuple[float, float, float, float]],
                   lines: list[tuple[np.ndarray, np.ndarray, float]] | None = None) -> list[dict]:
    """Partial circles whose own angular run is solid enough to be a drawn arc.

    The strict pass keeps only rings that are ink all the way round; a fillet, a boss circle broken by
    two arms or a bore crossing another edge fails that and used to vanish, which is why a lever's
    outline could not be chained. Here the ring's longest run is measured instead: it must be at least
    `ARC_MIN_SPAN_DEGREES` long and `ARC_SPAN_COVERAGE_MIN` solid inside itself, it must not be a
    circle the strict pass already kept, and it must not sit inside a word box (a glyph's curve).
    """
    kept: list[dict] = []

    def same_ring(cx: float, cy: float, radius: float) -> bool:
        """One drawn ring, whatever radius Hough guessed: centres and radii within 15% and the
        absolute floors. The radius term also scales with the *kept* ring (a quarter of it), because a
        fragment fitted to a circle's ink can come back well inside it — measured: the synthetic sheet's
        r=45 ring was re-offered as an r=37.4 arc whose centre sat 5.9 px from the circle's, 9.3 px off
        in radius, past the 6 px floor. Without this the weak pass offers the same fillet twenty times
        over and a kept full circle comes back as a handful of arcs sitting on its own ink."""
        for ox, oy, oradius in rings:
            if (np.hypot(cx - ox, cy - oy) <= max(8.0, 0.15 * radius)
                    and abs(radius - oradius) <= max(6.0, 0.15 * radius, 0.25 * oradius)):
                return True
        return False

    rings = [(ox, oy, oradius) for ox, oy, oradius, _coverage in circles]
    for cx, cy, radius in candidates:
        measured = _refined_radius(ink, cx, cy, radius)
        if measured < max(ARC_MIN_RADIUS_PX,
                          ARC_RADIUS_TO_MEDIAN_LINE * _median_line_length(lines)):
            continue
        if same_ring(cx, cy, measured):
            continue
        hits = _angular_support(ink, cx, cy, measured)
        start_index, length = _longest_ring_run(hits)
        span = 360.0 * length / len(hits)
        if span >= 360.0 * ARC_CIRCLE_FRACTION or span < ARC_MIN_SPAN_DEGREES:
            continue
        run = np.roll(hits, -start_index)[:length]
        if float(run.mean()) < ARC_SPAN_COVERAGE_MIN:
            continue
        # A ring that is merely *off centre* grazes a thick drawn circle's ink over a long stretch and
        # would be kept as an arc. Where the ink actually sits along those angles is the discriminator:
        # on a real arc it is one radius, on a graze it scatters.
        # The ring's own ink decides where the arc really is: a Hough centre is off by ten pixels on a
        # big arc, and an arc whose ends miss the outline's lines by that much can never close a loop.
        # So the run's ink points get a circle fitted to them (Kasa), and the arc's ends are the ink's
        # ends, not angles sampled from the guess. Ink that barely bulges over its own chord is a
        # straight edge read as a huge-radius arc, and is refused.
        angles = np.linspace(0.0, 2.0 * np.pi, len(hits), endpoint=False)
        points = [_ink_point(ink, cx, cy, float(angles[index]), measured)
                  for index in ((start_index + step) % len(hits) for step in range(length))]
        raw = np.array([point for point in points if point is not None])
        if len(raw) < 0.9 * length:
            continue
        # The ring is fitted to the whole run; the trim only decides where the arc's ends are. A circle
        # fitted to trimmed ink comes out short — measured: r = 98 px where the drawing has 100 — and
        # that costs real millimetres on the part. The sagitta gate asks about the ink, so it too reads
        # the whole run.
        fitted_x, fitted_y, fitted_radius = _fit_circle(raw)
        if abs(fitted_radius - measured) > 0.35 * measured:
            continue
        chord = raw[-1] - raw[0]
        chord_length = float(np.linalg.norm(chord)) or 1.0
        unit = chord / chord_length
        relative = raw - raw[0]
        bulge = float(np.abs(relative[:, 0] * unit[1] - relative[:, 1] * unit[0]).max())
        if bulge < ARC_MIN_SAGITTA_PX:
            continue
        found = _trim_to_own_ink(raw, lines)
        if len(found) < max(4.0, 0.3 * length):
            continue
        end_angles = np.degrees(np.arctan2(found[:, 1] - fitted_y, found[:, 0] - fitted_x)) % 360.0
        steps = np.abs(np.degrees(np.diff(np.unwrap(np.radians(end_angles)))))
        trimmed_span = float(steps.sum())
        if trimmed_span < ARC_MIN_SPAN_DEGREES:
            continue
        first_degrees = float(end_angles[0])
        last_degrees = first_degrees + trimmed_span
        if any(box.x - 2 <= fitted_x <= box.x + box.w + 2 and box.y - 2 <= fitted_y <= box.y + box.h + 2
               for box in boxes):
            continue
        kept.append({"centre": [fitted_x, fitted_y], "radius": fitted_radius,
                     "start_degrees": first_degrees, "end_degrees": last_degrees,
                     "span_degrees": span, "coverage": float(run.mean())})
    # Longest run first: the widest evidence for a ring picks which of its near-duplicates survives.
    kept.sort(key=lambda row: (-row["span_degrees"], -row["coverage"]))
    deduped: list[dict] = []
    rings = [(ox, oy, oradius) for ox, oy, oradius, _coverage in circles]
    for row in kept:
        cx, cy, radius = row["centre"][0], row["centre"][1], row["radius"]
        # The same test as the loop above, through the same closure: this pass used to keep its own copy
        # of the tolerance and quietly re-admitted the very fragments the widened one had just dropped.
        if same_ring(cx, cy, radius):
            continue
        deduped.append(row)
        rings.append((cx, cy, radius))
    deduped.sort(key=lambda row: (-row["span_degrees"], row["centre"][1], row["centre"][0]))
    return deduped


def _drop_circle_fragments(lines: list[tuple[np.ndarray, np.ndarray, float]],
                           circles: list[tuple[float, float, float, float]]
                           ) -> list[tuple[np.ndarray, np.ndarray, float]]:
    """Short segments riding a verified circle are that circle's ink, not strokes: Hough cuts a
    drawn circle into chords whose ends sit on the ring and whose middle sits up to the sagitta
    inside it, so only short segments (a real line crossing a circle is longer) are tested, with
    room for the ring's own width."""
    kept = []
    for start, end, residual in lines:
        if float(np.linalg.norm(end - start)) > CIRCLE_FRAGMENT_MAX_LENGTH_PX:
            kept.append((start, end, residual))
            continue
        midpoint = (start + end) / 2.0
        on_circle = any(
            all(abs(float(np.hypot(point[0] - cx, point[1] - cy)) - radius)
                <= CIRCLE_FRAGMENT_TOLERANCE_PX for point in (start, end, midpoint))
            for cx, cy, radius, _coverage in circles)
        if not on_circle:
            kept.append((start, end, residual))
    return kept


def _ocr_words(path: Path) -> tuple[list[dict], str | None]:
    """tesseract TSV, word level. A missing binary is a note, not a crash: the geometry part of
    the record is still a measurement."""
    try:
        completed = subprocess.run(["tesseract", str(path), "stdout", "--psm", OCR_PSM, "tsv"],
                                   capture_output=True, text=True, timeout=OCR_TIMEOUT_S)
    except FileNotFoundError:
        return [], "tesseract bulunamadı; metin kaydı boş (geometri kaydı yine geçerli)."
    except subprocess.TimeoutExpired:
        return [], "tesseract zaman aşımı; metin kaydı boş."
    if completed.returncode != 0:
        return [], f"tesseract hatası (çıkış {completed.returncode}); metin kaydı boş."
    words = []
    for row in completed.stdout.splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) != 12 or parts[0] != "5":
            continue
        text = parts[11].strip()
        if not text or not any(character.isalnum() for character in text):
            continue
        words.append({"text": text, "left": int(parts[6]), "top": int(parts[7]),
                      "width": int(parts[8]), "height": int(parts[9]),
                      "confidence": float(parts[10])})
    return words, None


def _phrase(group: list[dict]) -> dict:
    text = " ".join(word["text"] for word in group)
    compact = text.replace(" ", "")
    if parse_dimension_unit(text)[1] is None and parse_dimension_unit(compact)[1] is not None:
        text = compact  # OCR split one printed number across two boxes
    left = min(word["left"] for word in group)
    top = min(word["top"] for word in group)
    right = max(word["left"] + word["width"] for word in group)
    bottom = max(word["top"] + word["height"] for word in group)
    return {"text": text,
            "bbox": BBox(x=float(left), y=float(top), w=float(right - left), h=float(bottom - top)),
            "confidence": min(word["confidence"] for word in group)}


def _merge_phrases(words: list[dict]) -> list[dict]:
    """Words into printed phrases: same line, small horizontal gap. Cards on the table: this is
    where '4' and 'x' become the callout the meaning layer reads."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["left"])):
        for line in lines:
            centre = line[0]["top"] + line[0]["height"] / 2
            if abs(word["top"] + word["height"] / 2 - centre) <= 0.6 * max(word["height"],
                                                                          line[0]["height"]):
                line.append(word)
                break
        else:
            lines.append([word])
    phrases = []
    for line in lines:
        line.sort(key=lambda item: item["left"])
        group = [line[0]]
        for word in line[1:]:
            previous = group[-1]
            gap = word["left"] - (previous["left"] + previous["width"])
            if gap <= 1.5 * max(word["height"], previous["height"]):
                group.append(word)
            else:
                phrases.append(_phrase(group))
                group = [word]
        phrases.append(_phrase(group))
    phrases.sort(key=lambda phrase: (phrase["bbox"].y, phrase["bbox"].x))
    return [phrase for phrase in phrases if phrase["text"]]


def observe_raster(path: str | Path) -> Observations:
    """Read a raster sheet into observations: strokes, verified circles, OCR phrases."""
    drawing = Path(path)
    image = cv2.imread(str(drawing), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise Unsupported(f"görüntü okunamadı: {drawing.name} (PNG/JPG/TIF/BMP bekleniyor)")
    height, width = image.shape
    ink = (image < INK_THRESHOLD).astype(np.uint8)
    words, ocr_note = _ocr_words(drawing)
    phrases = _merge_phrases(words)
    candidates = _circle_candidates(image)
    image_area = float(height * width)
    boxes = [BBox(x=float(word["left"]), y=float(word["top"]), w=float(word["width"]),
                  h=float(word["height"]))
             for word in words
             if word["width"] * word["height"] <= GLYPH_BOX_MAX_FRACTION * image_area]
    circle_list = _verified_circles(ink, candidates, boxes)
    arc_candidates = _arc_candidates(image)
    raw_lines = _merged_lines(ink)
    arc_list = _verified_arcs(ink, arc_candidates, boxes, circle_list, raw_lines)
    ring_ink = circle_list + [(row["centre"][0], row["centre"][1], row["radius"], row["coverage"])
                             for row in arc_list]
    merged_lines = _drop_circle_fragments(raw_lines, ring_ink)
    raster_frame = Frame(width=width, height=height, dpi=_dpi(drawing),
                         detail="raster görüntünün kendi pikselleri; PDF nokta çerçevesi yok")
    observations = Observations(
        source=SourceRef(ref=str(drawing), sha256=source_hash(drawing), page=0, page_size_pt=None),
        frame=raster_frame,
        text_placement="as-is",
        # PLAN 8.6: no vector border exists on a raster sheet, and the product says exactly that instead
        # of pretending the image edges are the sheet's frame.
        sheet_frame=sheet_frame([], raster_frame, 0),
    )
    for start, end, residual in merged_lines:
        observations.primitives.append(Primitive(
            id=f"g{len(observations.primitives)}", path_id="raster", kind="line",
            start=[_rounded(start[0]), _rounded(start[1])],
            end=[_rounded(end[0]), _rounded(end[1])],
            max_residual_px=_rounded(residual), method="hough-merged"))
    for cx, cy, radius, coverage in circle_list:
        observations.primitives.append(Primitive(
            id=f"g{len(observations.primitives)}", path_id="raster", kind="circle",
            centre=[_rounded(cx), _rounded(cy)], radius=_rounded(radius),
            coverage=_rounded(coverage), method="hough-verified"))
    for row in arc_list:
        observations.primitives.append(Primitive(
            id=f"g{len(observations.primitives)}", path_id="raster", kind="arc",
            centre=[_rounded(row["centre"][0]), _rounded(row["centre"][1])], radius=_rounded(row["radius"]),
            start_degrees=_rounded(row["start_degrees"]), end_degrees=_rounded(row["end_degrees"]),
            coverage=_rounded(row["coverage"]), method="hough-arc"))
    for index, phrase in enumerate(phrases):
        kind, value, unit = parse_dimension_unit(phrase["text"])
        observations.texts.append(TextObservation(
            id=f"t{index}", text=phrase["text"], value=value, unit=unit, kind=kind.value,
            count=split_count(phrase["text"])[0], bbox=phrase["bbox"],
            method="tesseract-tsv", confidence=phrase["confidence"]))
    lines = sum(1 for primitive in observations.primitives if primitive.kind == "line")
    numeric = sum(1 for text in observations.texts if text.value is not None)
    observations.notes = [
        f"Raster gözlem: vektör alt yolu yok (paths boş); {lines} çizgi + {len(circle_list)} daire + "
        f"{len(arc_list)} yay piksellerden ölçüldü.",
        f"Daire tespiti Hough + doğrulama: kapsama ≥ {CIRCLE_COVERAGE_MIN}, iç mürekkep ≤ "
        f"{CIRCLE_INTERIOR_MAX}, aday {len(candidates)} → doğrulanan {len(circle_list)}; daire "
        f"mürekkebi sayılan {len(raw_lines) - len(merged_lines)} parça çizgi listesinden çıkarıldı. "
        "Gözle görülen bazı daireler (küçük cıvata delikleri, kesikli ve yoğun kümedekiler) bu "
        "eşiklerle kayda girmiyor: yüksek hassasiyet, düşük geri çağırma; yükseltmek gerçek "
        "referans listesiyle ölçülmesi gereken ayrı bir dilim.",
        f"Yay uydurma: zayıf Hough geçişi ({len(arc_candidates)} aday, param2 {ARC_PARAM2}) → "
        f"{len(arc_list)} yay; bir yay kendi açı aralığında ≥ {ARC_SPAN_COVERAGE_MIN} dolu ve "
        f"≥ {ARC_MIN_SPAN_DEGREES:.0f}° olmalı, tam daireyi geçen halka burada tekrarlanmaz. Ölçü "
        "ankrajları rasterda hâlâ yok — bağlama kendi raster dilimini bekliyor.",
        f"Glif filtresi yalnız kelime boyutlu OCR kutularını kullanır; görüntünün %"
        f"{int(GLYPH_BOX_MAX_FRACTION * 100)}'ünden büyük kutular okuma gürültüsü sayılır ve glif "
        "bölgesi tutulmaz.",
        f"OCR: tesseract psm {OCR_PSM}, {len(words)} kelime → {len(phrases)} ifade, {numeric} sayısal.",
    ]
    if ocr_note:
        observations.notes.append(ocr_note)
    observations.notes.append(f"Görüş çerçevesi (PLAN 8.6): {observations.sheet_frame.provenance}.")
    return observations


__all__ = ["RASTER_SUFFIXES", "observe_raster", "Unsupported"]
