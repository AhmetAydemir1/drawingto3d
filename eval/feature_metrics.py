"""Feature-level comparison of a produced STEP against an independently described part.

Version `feature-metrics/1.0.0`, schema `drawingto3d.features/1`.

`eval/metrics.py` stays in place as the historical coarse evaluator (sorted bounding box, volume,
set of cylinder radii). It does not count holes, does not look at hole centres, axes or depths, and
only fails on *missing* radii: a part with an extra hole of a diameter that already exists, or with
the whole hole layout moved, passes it. This module is the versioned replacement.

    .venv/bin/python eval/feature_metrics.py PRODUCED.step REFERENCE.step
    .venv/bin/python eval/feature_metrics.py PRODUCED.step --printed printed-spec.json

Runs in the product environment (`.venv`, build123d) rather than the CadQuery runner (`.venv-cad`):
the product dependency set is the one that has to keep working.

What this evaluator does differently
------------------------------------
* Holes / bores / outer cylinders are compared as *identified features*: count, kind
  (hole or outer cylinder), axis line, diameter, axis direction, through/blind and blind depth.
  A cylindrical face is never counted as a hole by itself: faces of one cylinder that were split
  by the kernel are grouped, and a cylinder whose material lies outside it is an outer surface.
* Exactly one rigid alignment is used, chosen from the 24 proper rotations of a box plus one
  translation (``ALLOWED_ALIGNMENTS``). There is no rescaling, so a declared-unit error appears as
  a 25.4x size ratio, and no mirroring: a mirrored layout is a different part and must not be
  fitted onto the reference. Symmetric parts still pass because a *proper* rotation can map them.
* Under the chosen alignment the two solids have to agree on where the material is, not only on
  which cylinders exist: a lattice of probe points is classified inside/outside in both solids and
  has to match. Without this, a part whose rib sits on the other side — same box, same holes, same
  volume — passes.
* The decision is then *exact*, not sampled: the two solids are cut against each other under the
  alignment and the leftover volume on each side must be at the numerical floor. A small feature that
  falls between probe points is still a different part, and sampling alone cannot see it.
* Printed nominal values (with the drawing's own tolerance) are compared separately from CAD
  numeric tolerance, and a detail the drawing does not state is never turned into a requirement.
* Anything the evaluator cannot describe — cones, tori, spheres, splines, free-form surfaces — is
  recorded as ``unmodelled`` and the whole-part verdict becomes ``not_evaluated``. It is never
  ``pass``: a partly understood CAD description must not be reported as a fully checked part.
* The coarse metrics (volume, projected areas, face-type histogram) are still computed, but only
  as auxiliary evidence. They never substitute for a feature measurement.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from build123d import Location, import_step
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Pnt, gp_Trsf
from OCP.TopAbs import TopAbs_State

SCHEMA_VERSION = "drawingto3d.features/1"
EVALUATOR_VERSION = "feature-metrics/1.0.0"

# Fixed before any result was observed. Never loosen these to let a part through; a tolerance that
# moves after a measurement is not a tolerance.
TOLERANCES = {
    "position_mm": 0.05,  # axis line distance and centre distance
    "diameter_mm": 0.02,
    "depth_mm": 0.05,
    "axis_angle_deg": 0.5,
    "bbox_mm": 0.05,
    "unit_ratio_frac": 0.02,  # allowed |size ratio - 1| before it counts as a scale/unit error
}

# Diagnostic pairing windows. These decide which produced feature is *compared against* which
# reference feature so the failure can be named (axis / centre / diameter / depth). They are wider
# than the pass tolerances and never accept anything: a pair inside the window still has to pass
# every tolerance above.
PAIR_WINDOW_MM = 8.0
PAIR_DIAMETER_WINDOW_MM = 1.0

# A point this far past the end of a cylindrical feature is tested for material: solid there means
# the feature stops inside the part (blind), air there means it comes out (through).
PROBE_MM = 0.2

# Material agreement: a lattice of probe points is classified in both solids under the chosen
# alignment. Points within MATERIAL_TOL_MM of a surface are skipped, because a difference of that
# size is a modelling tolerance, not a different part.
MATERIAL_TOL_MM = 0.25
MATERIAL_TARGET_SPACING_MM = 2.5
MATERIAL_MAX_POINTS = 8000
MATERIAL_ALIGNMENT_ATTEMPTS = 4  # alignments with the same feature score that get a material check

# The exact check: after the alignment, the two solids are cut and what is left on each side is
# measured. This is a numerical floor, not a feature-size allowance — a correct part re-exported
# through STEP differs by about 1e-12 mm³, and the smallest feature worth catching here is 1e-4 mm³
# (the reviewed counter-example was a 1x1x1 mm pocket, i.e. exactly 1.0 mm³, which no lattice of
# probe points saw).
EXACT_DIFFERENCE_TOL_MM3 = 1.0e-4

# Printed (drawing) comparison: the drawing's tolerance, not the CAD numeric tolerance. Used only
# when neither the spec file nor the feature carries its own tolerance.
PRINTED_DEFAULT_TOL_MM = 0.1

# Anything not in this set is unmodelled and downgrades the verdict to `not_evaluated`.
MODELLED_FACE_TYPES = {"PLANE", "CYLINDER"}

MM_PER_INCH = 25.4


# ---------------------------------------------------------------- extraction


def extract(path: str | Path, *, units: str = "mm") -> dict:
    """Describe a STEP file as identified features.

    `units` is the unit *recorded with the source*, not a guess: an unknown unit is recorded as
    ``"unknown"`` and the unit comparison then refuses to claim agreement. The kernel returns
    millimetres regardless of what the file declares, which is why the scale ratio (below) is what
    actually detects a unit error.
    """
    record = {
        "schema": SCHEMA_VERSION,
        "evaluator": EVALUATOR_VERSION,
        "path": str(path),
        "recorded_units": units,
        "solids": 0,
        "valid": False,
        "bbox": None,
        "volume_mm3": None,
        "features": [],
        "unmodelled": {},
        "projected_area_mm2": {},
        "face_types": {},
        "unreadable": None,
    }
    try:
        shape = import_step(str(path))
        solids = list(shape.solids())
    except Exception as exc:  # noqa: BLE001 - an unreadable file is a result, not a crash
        record["unreadable"] = f"{type(exc).__name__}: {exc}"
        return record
    record["solids"] = len(solids)
    if not solids:
        record["unreadable"] = "katı yok (boş veya ayrıştırılamayan STEP)"
        return record

    solid = solids[0]
    box = solid.bounding_box()
    record["valid"] = bool(solid.is_valid)
    record["bbox"] = {
        "min": [_round(box.min.X), _round(box.min.Y), _round(box.min.Z)],
        "max": [_round(box.max.X), _round(box.max.Y), _round(box.max.Z)],
        "size": [_round(box.size.X), _round(box.size.Y), _round(box.size.Z)],
    }
    record["volume_mm3"] = round(float(solid.volume), 3)
    record["features"] = _features(solid)
    record["unmodelled"] = _unmodelled_counts(solid)
    record["projected_area_mm2"] = _projected_areas(solid)
    record["face_types"] = _face_type_counts(solid)
    return record


def _features(solid) -> list[dict]:
    raw = [_raw_cylinder(index, face, solid) for index, face in enumerate(solid.faces())
           if face.geom_type.name == "CYLINDER"]
    features = [_describe(group) for group in group_cylinders(raw)]
    features.sort(key=lambda feature: (feature["kind"], feature["diameter_mm"],
                                       feature["centre"][0], feature["centre"][1], feature["centre"][2]))
    for number, feature in enumerate(features, start=1):
        feature["id"] = f"{'outer' if feature['kind'] == 'outer' else 'hole'}_{number}"
    return features


def group_cylinders(raw: list[dict]) -> list[list[dict]]:
    """One group per cylindrical feature.

    The kernel may split one cylinder into several faces (a seam, a boolean, a rebuilt B-rep). Two
    raw faces belong to the same feature when they lie on the same cylinder — same radius, same axis
    line, same inside/outside sense — *and* their axial spans overlap. Two coaxial bores in separate
    walls do not overlap, so they stay two features instead of being merged into a hole that spans
    the air between them.
    """
    groups: list[list[dict]] = []
    for face in raw:
        for group in groups:
            if _same_cylinder(group[0], face):
                group.append(face)
                break
        else:
            groups.append([face])
    return groups


def _raw_cylinder(index: int, face, solid) -> dict:
    axis = face.axis_of_rotation
    direction = _canonical_direction(_vector(axis.direction))
    point = _vector(axis.position)
    span_min, span_max = _axial_span(face, direction, point)
    radial = _radial(face, direction, point)
    normal = _vector(face.normal_at(0.5, 0.5))
    inner = _dot(normal, radial) < 0.0
    beyond_max = _add(span_max, _scale(direction, PROBE_MM))
    beyond_min = _add(span_min, _scale(direction, -PROBE_MM))
    through = not solid.is_inside(tuple(beyond_max)) and not solid.is_inside(tuple(beyond_min))
    return {
        "face": index,
        "radius": float(face.radius),
        "direction": direction,
        "point": point,
        "inner": inner,
        "area": float(face.area),
        "span_min": span_min,
        "span_max": span_max,
        "through": through,
    }


def _describe(group: list[dict]) -> dict:
    inner_area = sum(face["area"] for face in group if face["inner"])
    outer_area = sum(face["area"] for face in group if not face["inner"])
    kind = "hole" if inner_area >= outer_area else "outer"
    head = group[0]
    span_min = min(face["span_min"] for face in group)
    span_max = max(face["span_max"] for face in group)
    direction = head["direction"]
    depth = _dot(_subtract(span_max, span_min), direction)
    centre = _scale(_add(span_min, span_max), 0.5)
    return {
        "id": None,
        "kind": kind,
        "diameter_mm": round(2.0 * sum(f["radius"] for f in group) / len(group), 4),
        "axis_point": [_round(v) for v in head["point"]],
        "axis_direction": [_round(v) for v in direction],
        "centre": [_round(v) for v in centre],
        "span_mm": [round(depth, 4)],
        "depth_mm": round(depth, 4) if not all(f["through"] for f in group) else None,
        "through": all(f["through"] for f in group),
        "faces": len(group),
        "area_mm2": round(inner_area + outer_area, 4),
    }


def _axial_span(face, direction, point) -> tuple[list[float], list[float]]:
    """The two ends of a cylindrical face, measured along its own axis.

    The circles at the ends of a bore are exact; a face whose ends are not circles falls back to
    its vertices. Both work for kernel-split faces, so a face split in two is not two features.
    """
    ends = []
    for edge in face.edges():
        if edge.geom_type.name != "CIRCLE":
            continue
        ends.append(_dot(_subtract(_vector(edge.arc_center), point), direction))
    if ends:
        return (_add(point, _scale(direction, min(ends))), _add(point, _scale(direction, max(ends))))
    values = [_dot(_subtract(_vector(vertex.center()), point), direction) for vertex in face.vertices()]
    if not values:
        raise ValueError("silindirik yüzeyin eksen uçları ölçülemedi")
    return (_add(point, _scale(direction, min(values))), _add(point, _scale(direction, max(values))))


def _same_cylinder(one: dict, other: dict) -> bool:
    if abs(one["radius"] - other["radius"]) > 1e-6:
        return False
    if abs(abs(_dot(one["direction"], other["direction"])) - 1.0) > 1e-9:
        return False
    if _line_distance(one["point"], one["direction"], other["point"], other["direction"]) > 1e-6:
        return False
    if one["inner"] != other["inner"]:
        return False
    # Two halves of one split face share their axial span; two coaxial bores in separate walls do
    # not, and they are two features.
    return _dot(_subtract(one["span_min"], other["span_max"]), one["direction"]) <= 0.0 and \
        _dot(_subtract(other["span_min"], one["span_max"]), one["direction"]) <= 0.0


def _unmodelled_counts(solid) -> dict:
    counts: dict[str, int] = {}
    for face in solid.faces():
        name = face.geom_type.name
        if name in MODELLED_FACE_TYPES:
            continue
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def _projected_areas(solid) -> dict:
    """Auxiliary outline evidence: the area of the faces facing each axis.

    A planar face is returned with its inner wires already removed, so a plate with a bore gives the
    bored cross-section. This is a *supporting* number, not a feature measurement.
    """
    areas: dict[str, float] = {}
    for face in solid.faces():
        if face.geom_type.name != "PLANE":
            continue
        normal = _vector(face.normal_at(0.5, 0.5))
        for axis, vector in (("x", (1.0, 0.0, 0.0)), ("y", (0.0, 1.0, 0.0)), ("z", (0.0, 0.0, 1.0))):
            if abs(abs(_dot(normal, vector)) - 1.0) < 1e-6:
                areas[axis] = round(areas.get(axis, 0.0) + float(face.area), 3)
                break
    return dict(sorted(areas.items()))


def _face_type_counts(solid) -> dict:
    counts: dict[str, int] = {}
    for face in solid.faces():
        counts[face.geom_type.name] = counts.get(face.geom_type.name, 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------- alignment


def _rotation_matrices() -> list[tuple[str, list[list[float]]]]:
    """The 24 proper rotations of a box. Determinant +1 only: no reflection, no scaling.

    Each row is the image of one basis vector, so a matrix with a single +/-1 per row and column is
    accepted only when its determinant is +1. That is what keeps a mirror from being used to fit a
    mirrored layout onto the reference.
    """
    matrices = []
    for permutation, signs in _signed_permutations():
        matrix = [[0.0] * 3 for _ in range(3)]
        for row in range(3):
            matrix[row][permutation[row]] = float(signs[row])
        if _determinant(matrix) > 0.5:
            matrices.append(("".join(str(p) for p in permutation)
                             + "".join("+" if s > 0 else "-" for s in signs), matrix))
    return matrices


def _signed_permutations():
    for permutation in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        for signs in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
                      (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1)):
            yield permutation, signs


def _determinant(matrix: list[list[float]]) -> float:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def _apply(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3)]


def possible_alignments(produced_bbox: dict, truth_bbox: dict, tolerance_mm: float) -> list[dict]:
    """Rigid alignments that put the produced box exactly onto the reference box.

    Sizes must already agree within `tolerance_mm`, so this never rescales and never mirrors. If the
    list is empty the parts cannot be the same solid in any allowed pose.
    """
    translated = []
    truth_centre = _centre(truth_bbox)
    for name, matrix in _rotation_matrices():
        corners = [_apply(matrix, corner) for corner in _corners(produced_bbox)]
        mins = [min(corner[axis] for corner in corners) for axis in range(3)]
        maxs = [max(corner[axis] for corner in corners) for axis in range(3)]
        sizes = [maxs[axis] - mins[axis] for axis in range(3)]
        if any(abs(sizes[axis] - truth_bbox["size"][axis]) > tolerance_mm for axis in range(3)):
            continue
        produced_centre = _apply(matrix, _centre(produced_bbox))
        shift = [truth_centre[axis] - produced_centre[axis] for axis in range(3)]
        shifted = [[corner[axis] + shift[axis] for axis in range(3)] for corner in corners]
        if any(abs(min(corner[axis] for corner in shifted) - truth_bbox["min"][axis]) > tolerance_mm for axis in range(3)):
            continue
        translated.append({"rotation": name, "matrix": matrix, "translation": [_round(v) for v in shift]})
    return translated


def _transform_feature(feature: dict, alignment: dict) -> dict:
    matrix = alignment["matrix"]
    shift = alignment["translation"]
    moved = dict(feature)
    moved["axis_point"] = [_round(v) for v in _add(_apply(matrix, feature["axis_point"]), shift)]
    moved["axis_direction"] = [_round(v) for v in _canonical_direction(_apply(matrix, feature["axis_direction"]))]
    moved["centre"] = [_round(v) for v in _add(_apply(matrix, feature["centre"]), shift)]
    return moved


def _rigid(solid, alignment: dict):
    """Apply an allowed alignment (rotation + translation) to a solid."""
    matrix, shift = alignment["matrix"], alignment["translation"]
    trsf = gp_Trsf()
    trsf.SetValues(matrix[0][0], matrix[0][1], matrix[0][2], shift[0],
                   matrix[1][0], matrix[1][1], matrix[1][2], shift[1],
                   matrix[2][0], matrix[2][1], matrix[2][2], shift[2])
    return solid.moved(Location(TopLoc_Location(trsf)))


def _solid_difference(produced: dict, truth: dict, alignment: dict) -> dict:
    """The exact check: under this alignment the two solids must be the same material.

    Sampling points can miss a small feature — a 1x1x1 mm pocket between lattice probes leaves every
    sampled point agreeing while the parts differ by a whole cubic millimetre. So the decision is
    made by cutting the two solids and measuring what is left on each side, which no feature size can
    hide. The tolerance is a numerical floor, not a feature-size allowance: a correct part re-exported
    through STEP differs by ~1e-12 mm³, and the smallest thing worth catching here is 1e-4 mm³.
    """
    cannot = {"ok": False, "gating": True, "got": "katı farkı ölçülemedi",
              "want": f"iki yön de ≤ {EXACT_DIFFERENCE_TOL_MM3:g} mm³",
              "detail": {"reason": "unknown"}}
    try:
        produced_solid = list(import_step(produced["path"]).solids())[0]
        truth_solid = list(import_step(truth["path"]).solids())[0]
        moved = _rigid(produced_solid, alignment)
        only_produced = float((moved - truth_solid).volume)
        only_truth = float((truth_solid - moved).volume)
    except Exception as exc:  # noqa: BLE001 - a cut that cannot run is not a pass
        return {**cannot, "detail": {"reason": f"{type(exc).__name__}: {exc}"}}
    tolerance = max(EXACT_DIFFERENCE_TOL_MM3, 1e-9 * max(float(truth_solid.volume), 1.0))
    return {
        "ok": only_produced <= tolerance and only_truth <= tolerance,
        "gating": True,
        "got": f"üretilende fazla {only_produced:.6g} mm³, referansta fazla {only_truth:.6g} mm³",
        "want": f"iki yön de ≤ {tolerance:g} mm³",
        "detail": {"only_in_produced_mm3": only_produced, "only_in_truth_mm3": only_truth,
                   "tolerance_mm3": tolerance},
    }


def _material_points(bbox: dict) -> list[list[float]]:
    """A deterministic lattice over the comparison box.

    Spacing targets MATERIAL_TARGET_SPACING_MM and the total count is capped, so the cost of the
    material check does not depend on how large the part is.
    """
    steps = []
    for size in bbox["size"]:
        count = int(math.ceil(size / MATERIAL_TARGET_SPACING_MM)) + 1
        steps.append(max(3, min(41, count)))
    while steps[0] * steps[1] * steps[2] > MATERIAL_MAX_POINTS:
        if all(step <= 3 for step in steps):
            break
        steps = [max(3, step - 1) for step in steps]
    points = []
    for i in range(steps[0]):
        for j in range(steps[1]):
            for k in range(steps[2]):
                points.append([
                    bbox["min"][0] + (bbox["max"][0] - bbox["min"][0]) * i / (steps[0] - 1),
                    bbox["min"][1] + (bbox["max"][1] - bbox["min"][1]) * j / (steps[1] - 1),
                    bbox["min"][2] + (bbox["max"][2] - bbox["min"][2]) * k / (steps[2] - 1),
                ])
    return points


def _material_check(produced: dict, truth: dict, alignment: dict) -> dict:
    """Is the material in the same place under this alignment?

    The bounding box and the cylinder list can both agree while the part is different: a rib on the
    other side of the plate is the same box, the same holes and the same volume. So probe points are
    classified inside/outside in both solids and the mapped point has to agree. Points on a surface
    (within MATERIAL_TOL_MM) are skipped: a difference that small is a modelling tolerance.
    """
    missing = {"ok": False, "gating": True, "got": "malzeme karşılaştırması yapılamadı",
               "want": "0 uyuşmayan nokta"}
    try:
        produced_solid = list(import_step(produced["path"]).solids())[0]
        truth_solid = list(import_step(truth["path"]).solids())[0]
    except Exception as exc:  # noqa: BLE001 - a file that cannot be re-read must not pass
        return {**missing, "detail": {"reason": f"{type(exc).__name__}: {exc}"}}
    points = _material_points(truth["bbox"])
    inverse = _transpose(alignment["matrix"])
    shift = alignment["translation"]
    truth_classifier = BRepClass3d_SolidClassifier(truth_solid.wrapped)
    produced_classifier = BRepClass3d_SolidClassifier(produced_solid.wrapped)
    compared = 0
    disagreements = []
    for point in points:
        wanted = _classify(truth_classifier, point)
        if wanted is None:
            continue
        mapped = _apply(inverse, _subtract(point, shift))
        got = _classify(produced_classifier, mapped)
        if got is None:
            continue
        compared += 1
        if got != wanted:
            if len(disagreements) < 8:
                disagreements.append({
                    "point": [_round(v) for v in point],
                    "reference": "malzeme" if wanted else "boşluk",
                    "produced": "malzeme" if got else "boşluk",
                })
    return {
        "ok": not disagreements,
        "gating": True,
        "got": f"{len(disagreements)} uyuşmayan nokta / {compared} karşılaştırıldı",
        "want": "0 uyuşmayan nokta",
        "detail": {"compared": compared, "lattice_points": len(points),
                   "tolerance_mm": MATERIAL_TOL_MM, "first_disagreements": disagreements},
    }


def _classify(classifier, point: list[float]) -> bool | None:
    classifier.Perform(gp_Pnt(point[0], point[1], point[2]), MATERIAL_TOL_MM)
    state = classifier.State()
    if state == TopAbs_State.TopAbs_IN:
        return True
    if state == TopAbs_State.TopAbs_OUT:
        return False
    return None


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [[matrix[column][row] for column in range(3)] for row in range(3)]


# ---------------------------------------------------------------- comparison


def compare(produced: dict, truth: dict, *, tolerances: dict | None = None) -> dict:
    """Decide whether `produced` is the same part as `truth`, feature by feature."""
    tol = dict(TOLERANCES if tolerances is None else tolerances)
    checks: dict[str, dict] = {}
    issues: list[dict] = []

    checks["readable"] = _check(produced.get("unreadable") is None, produced.get("unreadable") or "okunabilir",
                                "okunabilir ve katı var")
    checks["solids"] = _check(produced["solids"] == truth["solids"] == 1,
                              f"{produced['solids']} katı", f"{truth['solids']} katı")
    checks["valid"] = _check(truth["solids"] != 1 or produced.get("valid") is True,
                             str(produced.get("valid")), "True")
    checks["units"] = _unit_check(produced, truth, tol)

    if not all(checks[name]["ok"] for name in ("readable", "solids")):
        # A file that cannot be read or holds no solid is not a wrong part, it is an unusable
        # artifact: report `error`, not `fail`, and never `pass`.
        return _verdict(checks, issues, alignment=None, produced=produced, truth=truth, tol=tol,
                        override="error")

    alignments = possible_alignments(produced["bbox"], truth["bbox"], tol["bbox_mm"])
    checks["alignment"] = _check(
        bool(alignments),
        f"{len(alignments)} izinli rigid hizalama",
        "en az bir izinli rigid hizalama (24 uygun döndürme + öteleme; ölçekleme ve ayna yok)",
    )
    if not alignments:
        return _verdict(checks, issues, alignment=None, produced=produced, truth=truth, tol=tol)

    best = None
    ranked = []
    for alignment in alignments:
        moved = [_transform_feature(feature, alignment) for feature in produced["features"]]
        matched_issues, extras, missing = _compare_features(moved, truth["features"], tol)
        score = (len(extras) + len(missing), len(matched_issues),
                 sum(issue["value"] for issue in matched_issues))
        ranked.append((score, alignment, matched_issues, extras, missing))
    ranked.sort(key=lambda entry: entry[0])

    if not ranked:  # pragma: no cover - the empty-alignment case returned above
        raise RuntimeError("izinli hizalama olmadan özellik karşılaştırması")
    shortlist = [entry for entry in ranked if entry[0] == ranked[0][0]][:MATERIAL_ALIGNMENT_ATTEMPTS]
    if not shortlist:  # pragma: no cover - `ranked` is non-empty here
        raise RuntimeError("malzeme kontrolü için hizalama adayı yok")
    material = None
    best = None
    first_attempt = None
    exact = None
    for entry in shortlist:
        attempt = _material_check(produced, truth, entry[1])
        exact_attempt = _solid_difference(produced, truth, entry[1])
        if first_attempt is None:
            first_attempt = (entry, attempt)
            first_exact = exact_attempt
        if attempt["ok"] and exact_attempt["ok"]:
            best, material, exact = entry, attempt, exact_attempt
            break
    if best is None:
        # No allowed pose puts the same material in the same place: keep the best feature score and
        # the evidence of that pose, so the failure names both the features and the material.
        assert first_attempt is not None  # the loop above always runs at least once
        best, material = first_attempt
        exact = first_exact
    _, alignment, matched_issues, extras, missing = best

    issues.extend(matched_issues)
    checks["solid_difference"] = exact
    assert material is not None  # set on both paths above
    checks["material"] = material
    checks["features"] = _check(
        not extras and not missing,
        f"{len(produced['features'])} özellik",
        f"{len(truth['features'])} özellik; fazla {_names(extras)}, eksik {_names(missing)}",
    )
    checks["hole_geometry"] = _issues_check("feature_geometry", ["axis", "centre", "diameter"], matched_issues)
    checks["hole_type"] = _issues_check("through/blind", ["through_blind"], matched_issues)
    checks["hole_depth"] = _issues_check("kör delik derinliği", ["depth"], matched_issues)

    checks["unmodelled"] = {
        "ok": not produced["unmodelled"] and not truth["unmodelled"],
        "gating": False,
        "got": _describe_unmodelled(produced["unmodelled"]),
        "want": _describe_unmodelled(truth["unmodelled"]),
        "note": "modellenmeyen yüzey varsa tam parça 'pass' verilmez",
    }
    checks["volume"] = _auxiliary(
        abs(produced["volume_mm3"] - truth["volume_mm3"]) / max(truth["volume_mm3"], 1e-9),
        produced["volume_mm3"], truth["volume_mm3"], 0.25,
    )
    for axis in sorted(set(produced["projected_area_mm2"]) | set(truth["projected_area_mm2"])):
        got = produced["projected_area_mm2"].get(axis)
        want = truth["projected_area_mm2"].get(axis)
        if got is None or want is None:
            continue
        checks[f"projected_area_{axis}"] = _auxiliary(
            abs(got - want) / max(want, 1e-9), got, want, 0.02, gating=False)
    checks["face_types"] = {
        "ok": produced["face_types"] == truth["face_types"],
        "gating": False,
        "got": json.dumps(produced["face_types"], sort_keys=True),
        "want": json.dumps(truth["face_types"], sort_keys=True),
        "note": "yardımcı kanıt: aynı CAD'in farklı B-rep temsili eşdeğer olabilir",
    }
    return _verdict(checks, issues, alignment=alignment, produced=produced, truth=truth, tol=tol,
                    extras=extras, missing=missing)


def _compare_features(produced: list[dict], truth: list[dict], tol: dict) -> tuple[list[dict], list[dict], list[dict]]:
    candidates = []
    for truth_index, wanted in enumerate(truth):
        for produced_index, got in enumerate(produced):
            if got["kind"] != wanted["kind"]:
                continue
            distance = _distance(got["centre"], wanted["centre"])
            diameter = abs(got["diameter_mm"] - wanted["diameter_mm"])
            if distance > PAIR_WINDOW_MM or diameter > PAIR_DIAMETER_WINDOW_MM:
                continue
            candidates.append((distance + diameter, truth_index, produced_index))
    candidates.sort()
    used_truth: set[int] = set()
    used_produced: set[int] = set()
    pairs = []
    for _, truth_index, produced_index in candidates:
        if truth_index in used_truth or produced_index in used_produced:
            continue
        used_truth.add(truth_index)
        used_produced.add(produced_index)
        pairs.append((truth_index, produced_index))
    issues: list[dict] = []
    for truth_index, produced_index in pairs:
        issues.extend(_pair_issues(produced[produced_index], truth[truth_index], tol))
    extras = [feature for index, feature in enumerate(produced) if index not in used_produced]
    missing = [feature for index, feature in enumerate(truth) if index not in used_truth]
    return issues, extras, missing


def _pair_issues(got: dict, wanted: dict, tol: dict) -> list[dict]:
    issues = []
    angle = _angle_between(got["axis_direction"], wanted["axis_direction"])
    if angle > tol["axis_angle_deg"]:
        issues.append(_issue("axis", got, wanted, angle, "axis_angle_deg", "eksen yönü"))
    distance = _line_distance(got["axis_point"], got["axis_direction"],
                              wanted["axis_point"], wanted["axis_direction"])
    centre = _distance(got["centre"], wanted["centre"])
    if angle <= tol["axis_angle_deg"] and distance > tol["position_mm"]:
        issues.append(_issue("centre", got, wanted, distance, "position_mm", "eksen hattı uzaklığı"))
    elif angle > tol["axis_angle_deg"] and centre > tol["position_mm"]:
        issues.append(_issue("centre", got, wanted, centre, "position_mm", "merkez uzaklığı"))
    diameter = abs(got["diameter_mm"] - wanted["diameter_mm"])
    if diameter > tol["diameter_mm"]:
        issues.append(_issue("diameter", got, wanted, diameter, "diameter_mm", "çap"))
    if got["through"] != wanted["through"]:
        issues.append(_issue("through_blind", got, wanted,
                             float(got["through"]) - float(wanted["through"]), None, "delik türü"))
    elif not wanted["through"] and got["depth_mm"] is not None and wanted["depth_mm"] is not None:
        depth = abs(got["depth_mm"] - wanted["depth_mm"])
        if depth > tol["depth_mm"]:
            issues.append(_issue("depth", got, wanted, depth, "depth_mm", "kör delik derinliği"))
    return issues


def _issue(kind: str, got: dict, wanted: dict, value: float, tolerance_key: str | None, label: str) -> dict:
    return {
        "type": kind,
        "label": label,
        "produced": got["id"],
        "reference": wanted["id"],
        "value": round(float(value), 6),
        "tolerance": None if tolerance_key is None else TOLERANCES[tolerance_key],
        "detail": f"{got['id']} ({got['kind']} Ø{got['diameter_mm']:g} {_fmt_vector(got['centre'])}) ↔ "
                  f"{wanted['id']} ({wanted['kind']} Ø{wanted['diameter_mm']:g} {_fmt_vector(wanted['centre'])})",
    }


def _unit_check(produced: dict, truth: dict, tol: dict) -> dict:
    """Two different things are called a unit error, and they need different evidence.

    A declared unit that disagrees with the reference is one. A shape that is *uniformly* the wrong
    size — 25.4x in all three directions — is the other, and that is what a file written in inches
    looks like. A part that is merely the wrong size in one direction is not a unit error: that is a
    different part, and the alignment check says so.
    """
    if produced.get("bbox") is None or truth.get("bbox") is None:
        return {"ok": False, "gating": True, "got": "ölçülemedi", "want": "kutu ölçüsü",
                "detail": {"reason": "bbox"}}
    ratios = [produced["bbox"]["size"][axis] / truth["bbox"]["size"][axis]
              for axis in range(3) if truth["bbox"]["size"][axis]]
    uniform = (max(ratios) - min(ratios)) <= tol["unit_ratio_frac"]
    uniform_scale = max(abs(ratio - 1.0) for ratio in ratios)
    label_agrees = (produced["recorded_units"] == truth["recorded_units"]) or "unknown" in (
        produced["recorded_units"], truth["recorded_units"])
    okay = label_agrees and (not uniform or uniform_scale <= tol["unit_ratio_frac"])
    detail = {"scale_ratios": [_round(ratio) for ratio in ratios], "uniform": bool(uniform)}
    if not label_agrees or (uniform and uniform_scale > tol["unit_ratio_frac"]):
        detail["likely"] = "inç/mm" if abs(max(ratios) - MM_PER_INCH) < 0.05 else "ölçek farkı"
    return {
        "ok": bool(okay),
        "gating": True,
        "got": f"birim {produced['recorded_units']}, ölçek {_fmt_vector(ratios)}",
        "want": f"birim {truth['recorded_units']}, ölçek 1 (aynı ölçek; yeniden ölçekleme yok)",
        "detail": detail,
    }


def _verdict(checks: dict, issues: list[dict], *, alignment, produced: dict, truth: dict, tol: dict,
             extras: list[dict] | None = None, missing: list[dict] | None = None,
             override: str | None = None) -> dict:
    failing = [name for name, check in checks.items() if check.get("gating") and not check["ok"]]
    if override:
        verdict = override
    elif failing:
        verdict = "fail"
    elif checks.get("unmodelled") and not checks["unmodelled"]["ok"]:
        verdict = "not_evaluated"
    else:
        verdict = "pass"
    return {
        "schema": SCHEMA_VERSION,
        "evaluator": EVALUATOR_VERSION,
        "verdict": verdict,
        "checks": checks,
        "failed_checks": failing,
        "issues": issues,
        "extra_features": extras or [],
        "missing_features": missing or [],
        "alignment": alignment,
        "tolerances": tol,
        "auxiliary_only": [
            name for name, check in checks.items() if not check.get("gating")
        ],
    }


# ---------------------------------------------------------------- printed nominal values


def compare_printed(produced: dict, spec: dict, *, default_tolerance_mm: float = PRINTED_DEFAULT_TOL_MM) -> dict:
    """Compare against what the drawing prints, using the drawing's tolerance.

    An attribute that is not stated in `spec` is not required: the drawing not mentioning a detail
    is not the same as the drawing requiring it. Extra features are still reported, because a hole
    that nobody dimensioned is a disagreement with the drawing, not a rounding difference.
    """
    results = []
    used: set[int] = set()
    for wanted in spec.get("features", []):
        tolerance = wanted.get("tolerance_mm") or default_tolerance_mm
        pool = [index for index, feature in enumerate(produced["features"])
                if index not in used and feature["kind"] == wanted.get("kind", "hole")]
        if not pool:
            results.append({"feature": wanted.get("id"), "ok": False, "reason": "eksik",
                            "detail": f"{wanted.get('kind', 'hole')} Ø{wanted.get('diameter_mm')} "
                                      f"bu dosyada yok"})
            continue
        # Pick the feature that disagrees with the fewest *stated* attributes, so a failure names an
        # attribute instead of being lost in a position window.
        scored = sorted(((sum(not check["ok"] for check in _printed_checks(produced["features"][index], wanted, tolerance)),
                          _distance(produced["features"][index]["centre"], _spec_centre(wanted)), index)
                         for index in pool))
        index = scored[0][2]
        used.add(index)
        results.append(_printed_result(produced["features"][index], wanted, tolerance))
    extras = [feature["id"] for index, feature in enumerate(produced["features"]) if index not in used]
    units_ok = spec.get("units", "unknown") == produced["recorded_units"] or "unknown" in (
        spec.get("units", "unknown"), produced["recorded_units"])
    failed = []
    if not units_ok:
        failed.append("units")
    if extras:
        failed.append("extra_features")
    if any(not result["ok"] for result in results):
        failed.append("features")
    check = {
        # A declared unit that disagrees is a disagreement with the drawing, so it decides the
        # result: a file whose numbers are right in the wrong unit is not the drawn part.
        "ok": all(result["ok"] for result in results) and not extras and units_ok,
        "units_ok": units_ok,
        "failed_checks": failed,
        "results": results,
        "extra_features": extras,
        "unspecified": spec.get("unspecified", []),
        "default_tolerance_mm": default_tolerance_mm,
    }
    return check


def _printed_checks(feature: dict, wanted: dict, tolerance: float) -> list[dict]:
    """One check per attribute the drawing states. Nothing else is turned into a requirement."""
    checks = []
    if wanted.get("diameter_mm") is not None:
        delta = abs(feature["diameter_mm"] - wanted["diameter_mm"])
        checks.append({"attribute": "diameter_mm", "ok": delta <= tolerance,
                       "delta": round(delta, 4), "tolerance": tolerance})
    if wanted.get("through") is not None:
        checks.append({"attribute": "through", "ok": feature["through"] == wanted["through"],
                       "got": feature["through"], "want": wanted["through"]})
    if wanted.get("depth_mm") is not None:
        delta = abs((feature["depth_mm"] or 0.0) - wanted["depth_mm"])
        checks.append({"attribute": "depth_mm", "ok": delta <= tolerance,
                       "delta": round(delta, 4), "tolerance": tolerance})
    if wanted.get("axis") is not None:
        checks.append({"attribute": "axis", "ok": _principal_axis(feature["axis_direction"]) == wanted["axis"],
                       "got": _principal_axis(feature["axis_direction"]), "want": wanted["axis"]})
    if any(wanted.get(key) is not None for key in ("x", "y", "z")):
        target = _spec_centre(wanted)
        delta = _distance(feature["centre"], target)
        checks.append({"attribute": "position", "ok": delta <= tolerance,
                       "delta": round(delta, 4), "tolerance": tolerance,
                       "got": feature["centre"], "want": target})
    return checks


def _printed_result(feature: dict, wanted: dict, tolerance: float) -> dict:
    checks = _printed_checks(feature, wanted, tolerance)
    unspecified = sorted({key for key in ("kind", "diameter_mm", "through", "depth_mm", "axis", "x", "y", "z")
                          if wanted.get(key) is None})
    return {
        "feature": wanted.get("id"),
        "produced": feature["id"],
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
        "unspecified_attributes": unspecified,
    }


def _spec_centre(wanted: dict) -> list[float]:
    return [float(wanted.get(axis) or 0.0) for axis in ("x", "y", "z")]


def _principal_axis(direction: list[float]) -> str:
    index = max(range(3), key=lambda axis: abs(direction[axis]))
    return "XYZ"[index]


# ---------------------------------------------------------------- helpers


def _check(ok: bool, got: str, want: str, *, gating: bool = True, detail=None) -> dict:
    result = {"ok": bool(ok), "gating": gating, "got": got, "want": want}
    if detail is not None:
        result["detail"] = detail
    return result


def _issues_check(label: str, kinds: list[str], issues: list[dict]) -> dict:
    relevant = [issue for issue in issues if issue["type"] in kinds]
    return _check(not relevant, "sorun yok" if not relevant else f"{len(relevant)} sorun",
                  f"{label} tolerans içinde", detail={"kinds": kinds, "count": len(relevant)})


def _auxiliary(relative_error: float, got, want, limit: float, *, gating: bool = False) -> dict:
    return {
        "ok": relative_error <= limit,
        "gating": gating,
        "got": got,
        "want": want,
        "detail": {"relative_error": _round(relative_error), "limit": limit},
        "note": "yardımcı kontrol; özellik ölçümünün yerine geçmez",
    }


def _describe_unmodelled(counts: dict) -> str:
    return "yok" if not counts else ", ".join(f"{name}x{count}" for name, count in counts.items())


def _names(features: list[dict]) -> str:
    if not features:
        return "yok"
    return ", ".join(f"{feature['id']} Ø{feature['diameter_mm']:g} {_fmt_vector(feature['centre'])}"
                     for feature in features)


def _pointer(data, path: str):
    current = data
    for part in path.split("/"):
        if part:
            current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _vector(value) -> list[float]:
    if isinstance(value, dict):
        return [float(value[axis]) for axis in ("x", "y", "z")]
    if all(hasattr(value, axis) for axis in ("X", "Y", "Z")):
        return [float(value.X), float(value.Y), float(value.Z)]
    return [float(component) for component in value]


def _radial(face, direction: list[float], point: list[float]) -> list[float]:
    offset = _subtract(_vector(face.position_at(0.5, 0.5)), point)
    along = _scale(direction, _dot(offset, direction))
    return _normalize(_subtract(offset, along))


def _canonical_direction(vector: list[float]) -> list[float]:
    normal = _normalize(vector)
    for component in normal:
        if abs(component) > 1e-9:
            return [-value for value in normal] if component < 0 else normal
    raise ValueError("sıfır yön vektörü")


def _normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(component * component for component in vector))
    if length == 0.0:
        raise ValueError("sıfır vektör normalleştirilemedi")
    return [component / length for component in vector]


def _add(one, other) -> list[float]:
    return [one[axis] + other[axis] for axis in range(3)]


def _subtract(one, other) -> list[float]:
    return [one[axis] - other[axis] for axis in range(3)]


def _scale(vector, factor: float) -> list[float]:
    return [component * factor for component in vector]


def _dot(one, other) -> float:
    return sum(one[axis] * other[axis] for axis in range(3))


def _distance(one, other) -> float:
    return math.sqrt(sum((one[axis] - other[axis]) ** 2 for axis in range(3)))


def _line_distance(p1, d1, p2, d2) -> float:
    """Distance between two lines, used with a parallel check: parallel lines that are apart are a
    moved hole; non-parallel lines are an axis error (reported separately)."""
    offset = _subtract(p2, p1)
    if abs(abs(_dot(d1, d2)) - 1.0) < 1e-9:
        return math.sqrt(max(0.0, sum(component * component for component in
                                      _subtract(offset, _scale(d1, _dot(offset, d1))))))
    return math.sqrt(max(0.0, sum(component * component for component in offset)))


def _angle_between(one, other) -> float:
    value = min(1.0, abs(_dot(_normalize(one), _normalize(other))))
    return math.degrees(math.acos(value))


def _centre(bbox: dict) -> list[float]:
    return [(bbox["min"][axis] + bbox["max"][axis]) / 2.0 for axis in range(3)]


def _corners(bbox: dict) -> list[list[float]]:
    return [[bbox[side][axis] for axis in range(3)]
            for side in ("min", "max") for _ in (0, 1)]


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _fmt_vector(values) -> str:
    return "[" + ", ".join(f"{value:g}" for value in values) + "]"


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Üretilen STEP'i özellik düzeyinde referansla karşılaştır (feature-metrics/1.0.0)")
    parser.add_argument("produced")
    parser.add_argument("reference", nargs="?")
    parser.add_argument("--printed", help="basılı nominal ölçü dosyası (JSON)")
    parser.add_argument("--units", default="mm", help="üretilen dosyanın kayıtlı birimi")
    parser.add_argument("--reference-units", default="mm")
    parser.add_argument("--write", help="sonucu bu JSON dosyasına da yaz")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    produced = extract(args.produced, units=args.units)
    result = {"produced": produced, "truth": None, "verdict": None, "printed": None}
    if args.printed:
        spec = json.loads(Path(args.printed).read_text())
        result["printed"] = compare_printed(produced, spec)
    elif args.reference:
        result["truth"] = extract(args.reference, units=args.reference_units)
        result["verdict"] = compare(produced, result["truth"])
    else:
        parser.error("bir referans STEP veya --printed spec gerekir")

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.write:
        Path(args.write).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write).write_text(payload + "\n")
    if not args.quiet:
        print(payload)
    verdict = result["verdict"]["verdict"] if result["verdict"] else (
        "pass" if result["printed"]["ok"] else "fail")
    print(f"karar: {verdict}", file=sys.stderr)


if __name__ == "__main__":
    main()
