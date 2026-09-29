"""Analytic fixture parts for the feature evaluator, and the counter-example case matrix.

Each fixture exists twice, on purpose:

* ``SPECS`` is the hand-written engineering description of the part — printed values, unit, and one
  entry per feature with centre, diameter, axis, through/blind and depth. These numbers are the
  correct answer, derived by hand (volumes as closed-form expressions such as ``60 * 40 * 5 - pi *
  16 * 5``) and never read out of the evaluator or any production path.
* ``PARTS`` builds a STEP from the same numbers with build123d. The build is the *input*; the spec is
  the *truth*. A fixture whose extraction disagrees with its spec is a fixture bug, and the audit
  records that disagreement instead of hiding it.

``CASES`` is the counter-example matrix. Every case names the reference part, the produced part, the
expected verdict and why. The mandatory ones from the plan are: extra/missing hole of the same
diameter, wrong centre, wrong blind depth, wrong unit, wrong axis, same size and volume but a
different part, plus the acceptances (correct part, re-exported STEP, allowed rigid transform).
"""

from __future__ import annotations

import math
from pathlib import Path

from build123d import (
    Align,
    Box,
    Cone,
    Cylinder,
    Pos,
    Rot,
    Unit,
    export_step,
)

MM = (Align.CENTER, Align.CENTER, Align.CENTER)

PLATE = (60.0, 40.0, 5.0)
BLOCK = (60.0, 40.0, 10.0)
HOLE_R = 4.0  # Ø8
HOLE_D = 2.0 * HOLE_R


def _plate(width=PLATE[0], depth=PLATE[1], height=PLATE[2]):
    return Box(width, depth, height)


def _bore(part, x: float, y: float, *, radius=HOLE_R, along: str = "z", length=None, z: float = 0.0):
    span = length or max(PLATE) * 2
    if along == "z":
        return part - Pos(x, y, z) * Cylinder(radius, span, align=MM)
    if along == "y":
        return part - Pos(x, y, z) * Rot(90, 0, 0) * Cylinder(radius, span, align=MM)
    if along == "x":
        return part - Pos(x, y, z) * Rot(0, 90, 0) * Cylinder(radius, span, align=MM)
    raise ValueError(along)


# ---------------------------------------------------------------- parts


def plate_through():
    """60x40x5 plate, one Ø8 through hole at (10, 0)."""
    return _bore(_plate(), 10.0, 0.0)


def plate_two_holes():
    """Two Ø8 through holes at (10, 0) and (-10, 0)."""
    return _bore(_bore(_plate(), 10.0, 0.0), -10.0, 0.0)


def plate_two_holes_staggered():
    """Two Ø8 through holes at (10, 10) and (-10, -10): same box, same volume, same radius set as
    `plate_two_holes`, different positions."""
    return _bore(_bore(_plate(), 10.0, 10.0), -10.0, -10.0)


def plate_no_hole():
    return _plate()


def plate_extra_hole():
    """Same diameter as the reference hole, one extra hole nobody dimensioned."""
    return _bore(_bore(_plate(), 10.0, 0.0), -15.0, 0.0)


def plate_shifted_hole():
    """Reference hole moved 2 mm in x."""
    return _bore(_plate(), 12.0, 0.0)


def block_blind_8():
    """60x40x10 block, Ø8 blind hole 8 mm deep from the top face at (10, 0)."""
    return _bore(_plate(*BLOCK), 10.0, 0.0, length=8.0, z=BLOCK[2] / 2 - 4.0)


def block_blind_6():
    """The same blind hole, 6 mm deep."""
    return _bore(_plate(*BLOCK), 10.0, 0.0, length=6.0, z=BLOCK[2] / 2 - 3.0)


def block_through_z():
    """60x40x20 block, Ø8 through hole along Z at (10, 0)."""
    return _bore(_plate(60.0, 40.0, 20.0), 10.0, 0.0, length=60.0)


def block_through_y():
    """The same 60x40x20 block with the bore through the 40 mm width at x=10 instead: same centre
    (10, 0, 0), same diameter, different axis. A Ø8 bore cannot go through the 40 mm width of a 5 mm
    plate without cutting the plate in two, so the axis counter-example needs a block thick enough to
    hold it."""
    return _bore(_plate(60.0, 40.0, 20.0), 10.0, 0.0, along="y", length=80.0, z=0.0)


def _ribbed_plate():
    """60x40x5 plate plus a 60x15x5 rib on top at y=+12.5: the part is not symmetric in z, which is
    what makes a mirror in x a genuinely different part rather than a rotation of the same one. The
    rib covers the Ø8 hole at y=12 completely, so the hole passes through 10 mm of material there."""
    rib = Pos(0.0, 12.5, PLATE[2] / 2) * Box(60.0, 15.0, 5.0,
                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    return _plate() + rib


def plate_asymmetric():
    """Ribbed plate with Ø8 through holes at (10, 0) and (10, 12). The second hole passes through
    plate and rib, so its feature centre is at z=2.5 while the first is at z=0."""
    part = _bore(_ribbed_plate(), 10.0, 0.0)
    return _bore(part, 10.0, 12.0)


def plate_asymmetric_mirrored():
    """The same part mirrored in x. No allowed proper rotation maps it onto `plate_asymmetric`: the
    rib sits on top at y=+15 and stays there under x-mirroring, so every candidate rotation that
    fixes the rib puts the rib underneath or moves the holes."""
    part = _bore(_ribbed_plate(), -10.0, 0.0)
    return _bore(part, -10.0, 12.0)


def plate_asymmetric_turned():
    """The same part rotated 180° about Z: congruent, so it has to pass."""
    return Rot(0, 0, 180) * plate_asymmetric()


def plate_with_boss():
    """Plate with a Ø20 x 10 boss on top: a cylindrical face whose material is outside it."""
    return _plate() + Pos(0, 0, PLATE[2] / 2) * Cylinder(10.0, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def plate_boss_as_hole():
    """The boss replaced by a Ø20 through hole: same bbox, same cylinder radius, opposite meaning."""
    return _bore(_plate(), 0.0, 0.0, radius=10.0)


def plate_countersunk():
    """Ø8 through hole with a countersink (Ø12 -> Ø8 over 3 mm): a CONE face the evaluator cannot
    describe feature-by-feature."""
    base = _bore(_plate(), 0.0, 0.0)
    return base - Pos(0.0, 0.0, PLATE[2] / 2 - 1.5) * Cone(bottom_radius=HOLE_R, top_radius=6.0, height=3.0, align=MM)


def stepped_two_bores():
    """C-shaped block with one Ø8 bore passing through two walls: two coaxial cylindrical surfaces
    with disjoint axial spans, i.e. two features, not one."""
    block = _plate(*BLOCK) - Box(20.0, BLOCK[1], 4.0)
    return _bore(block, 0.0, 0.0, length=BLOCK[2] * 2)


def inch_declared():
    """The reference geometry exported with the file declaring inches."""
    return plate_through()


PARTS = {
    "plate_through": plate_through,
    "plate_two_holes": plate_two_holes,
    "plate_two_holes_staggered": plate_two_holes_staggered,
    "plate_no_hole": plate_no_hole,
    "plate_extra_hole": plate_extra_hole,
    "plate_shifted_hole": plate_shifted_hole,
    "block_blind_8": block_blind_8,
    "block_blind_6": block_blind_6,
    "block_through_z": block_through_z,
    "block_through_y": block_through_y,
    "plate_asymmetric": plate_asymmetric,
    "plate_asymmetric_mirrored": plate_asymmetric_mirrored,
    "plate_asymmetric_turned": plate_asymmetric_turned,
    "plate_with_boss": plate_with_boss,
    "plate_boss_as_hole": plate_boss_as_hole,
    "plate_countersunk": plate_countersunk,
    "stepped_two_bores": stepped_two_bores,
    "inch_declared": inch_declared,
}

# Parts whose STEP must be written with an inch unit instead of mm.
INCH_PARTS = {"inch_declared"}


def export(name: str, directory: Path, *, unit: Unit | None = None) -> Path:
    """Write one fixture's STEP and return its path. `unit` defaults from INCH_PARTS."""
    directory.mkdir(parents=True, exist_ok=True)
    part = PARTS[name]()
    path = directory / f"{name}.step"
    export_step(part, str(path), unit=unit or (Unit.IN if name in INCH_PARTS else Unit.MM))
    return path


def _spec(kind, diameter, centre, axis, through, depth, **extra):
    return {"kind": kind, "diameter_mm": diameter, "centre_mm": list(centre), "axis": axis,
            "through": through, "depth_mm": depth, **extra}


# ---------------------------------------------------------------- independent truth
# Written by hand from the construction above and from closed-form arithmetic. `volume_mm3` is an
# expression, not a number copied from a kernel.

SPECS: dict[str, dict] = {
    "plate_through": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - math.pi * HOLE_R**2 * 5,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_two_holes": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - 2 * math.pi * HOLE_R**2 * 5,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (-10.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_two_holes_staggered": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - 2 * math.pi * HOLE_R**2 * 5,
        "features": [_spec("hole", HOLE_D, (10.0, 10.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (-10.0, -10.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_no_hole": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5,
        "features": [], "unmodelled": {},
    },
    "plate_extra_hole": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - 2 * math.pi * HOLE_R**2 * 5,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (-15.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_shifted_hole": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - math.pi * HOLE_R**2 * 5,
        "features": [_spec("hole", HOLE_D, (12.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "block_blind_8": {
        "units": "mm", "bbox_size": list(BLOCK), "volume_mm3": 60 * 40 * 10 - math.pi * HOLE_R**2 * 8,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 1.0), "Z", False, 8.0)],
        "unmodelled": {},
    },
    "block_blind_6": {
        "units": "mm", "bbox_size": list(BLOCK), "volume_mm3": 60 * 40 * 10 - math.pi * HOLE_R**2 * 6,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 2.0), "Z", False, 6.0)],
        "unmodelled": {},
    },
    "block_through_z": {
        "units": "mm", "bbox_size": [60.0, 40.0, 20.0],
        "volume_mm3": 60 * 40 * 20 - math.pi * HOLE_R**2 * 20,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "block_through_y": {
        "units": "mm", "bbox_size": [60.0, 40.0, 20.0],
        "volume_mm3": 60 * 40 * 20 - math.pi * HOLE_R**2 * 40,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Y", True, None)],
        "unmodelled": {},
    },
    "plate_asymmetric": {
        "units": "mm", "bbox_size": [60.0, 40.0, 10.0],
        "volume_mm3": 60 * 40 * 5 + 60 * 15 * 5 - math.pi * HOLE_R**2 * 15,
        "features": [_spec("hole", HOLE_D, (10.0, 0.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (10.0, 12.0, 2.5), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_asymmetric_mirrored": {
        "units": "mm", "bbox_size": [60.0, 40.0, 10.0],
        "volume_mm3": 60 * 40 * 5 + 60 * 15 * 5 - math.pi * HOLE_R**2 * 15,
        "features": [_spec("hole", HOLE_D, (-10.0, 0.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (-10.0, 12.0, 2.5), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_asymmetric_turned": {
        "units": "mm", "bbox_size": [60.0, 40.0, 10.0],
        "volume_mm3": 60 * 40 * 5 + 60 * 15 * 5 - math.pi * HOLE_R**2 * 15,
        "features": [_spec("hole", HOLE_D, (-10.0, 0.0, 0.0), "Z", True, None),
                     _spec("hole", HOLE_D, (-10.0, -12.0, 2.5), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_with_boss": {
        "units": "mm", "bbox_size": [60.0, 40.0, 15.0], "volume_mm3": 60 * 40 * 5 + math.pi * 100 * 10,
        "features": [_spec("outer", 20.0, (0.0, 0.0, 7.5), "Z", False, 10.0)],
        "unmodelled": {},
    },
    "plate_boss_as_hole": {
        "units": "mm", "bbox_size": list(PLATE), "volume_mm3": 60 * 40 * 5 - math.pi * 100 * 5,
        "features": [_spec("hole", 20.0, (0.0, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
    "plate_countersunk": {
        "units": "mm", "bbox_size": list(PLATE),
        "volume_mm3": 60 * 40 * 5 - math.pi * HOLE_R**2 * 5 - (math.pi * (6.0**2 + 6.0 * HOLE_R + HOLE_R**2) / 3 * 3 - math.pi * HOLE_R**2 * 3),
        "features": [_spec("hole", HOLE_D, (0.0, 0.0, -1.5), "Z", True, None)],
        "unmodelled": {"CONE": 1},
    },
    "stepped_two_bores": {
        "units": "mm", "bbox_size": list(BLOCK), "volume_mm3": 60 * 40 * 10 - 20 * 40 * 4 - 2 * math.pi * HOLE_R**2 * 3,
        "features": [_spec("hole", HOLE_D, (0.0, 0.0, 3.5), "Z", True, None),
                     _spec("hole", HOLE_D, (0.0, 0.0, -3.5), "Z", True, None)],
        "unmodelled": {},
    },
    "inch_declared": {
        "units": "in", "bbox_size": [d * 25.4 for d in PLATE],
        "volume_mm3": (60 * 40 * 5 - math.pi * HOLE_R**2 * 5) * 25.4**3,
        "features": [_spec("hole", HOLE_D * 25.4, (10.0 * 25.4, 0.0, 0.0), "Z", True, None)],
        "unmodelled": {},
    },
}

# A printed (drawing) description of `plate_through`, used for the printed-nominal comparison. It
# states what the drawing prints and marks the rest unspecified.
PRINTED_SPEC = {
    "part": "plate_through",
    "units": "mm",
    "features": [
        {"id": "basılı-1", "kind": "hole", "x": 10.0, "y": 0.0, "axis": "Z",
         "diameter_mm": 8.0, "through": True, "tolerance_mm": 0.1},
    ],
    "unspecified": ["dış köşe pahı", "yüzey pürüzlülüğü"],
}


# ---------------------------------------------------------------- counter-example matrix

CASES: list[dict] = [
    {"name": "correct_part_passes", "reference": "plate_through", "produced": "plate_through",
     "expect": "pass", "why": "zorunlu kabul: doğru parça geçer"},
    {"name": "step_reexport_passes", "reference": "plate_through", "produced": "plate_through",
     "reexport": True, "expect": "pass",
     "why": "zorunlu kabul: üretilen STEP yeniden dışa aktarılıp okunduğunda da aynı parça"},
    {"name": "allowed_rigid_transform_passes", "reference": "plate_asymmetric",
     "produced": "plate_asymmetric_turned", "expect": "pass",
     "why": "zorunlu kabul: tanımlı eşdeğer rigid dönüşüm (Z'de 180°) geçer"},
    {"name": "extra_hole_same_diameter_fails", "reference": "plate_through",
     "produced": "plate_extra_hole", "expect": "fail",
     "why": "zorunlu karşı örnek: aynı çapta fazladan delik reddedilir",
     "old_evaluator": "pass"},
    {"name": "missing_hole_fails", "reference": "plate_through", "produced": "plate_no_hole",
     "expect": "fail", "why": "zorunlu karşı örnek: eksik delik reddedilir"},
    {"name": "wrong_centre_fails", "reference": "plate_through", "produced": "plate_shifted_hole",
     "expect": "fail", "why": "zorunlu karşı örnek: 2 mm kaymış merkez reddedilir",
     "expect_reasons": ["centre"]},
    {"name": "wrong_blind_depth_fails", "reference": "block_blind_8", "produced": "block_blind_6",
     "expect": "fail", "why": "zorunlu karşı örnek: yanlış kör delik derinliği (8'e karşı 6) reddedilir",
     "expect_reasons": ["depth"]},
    {"name": "blind_instead_of_through_fails", "reference": "plate_through", "produced": "block_blind_8",
     "expect": "fail", "why": "zorunlu karşı örnek: kör delik, through deliğin yerine geçmez"},
    {"name": "through_instead_of_blind_fails", "reference": "block_blind_8", "produced": "plate_through",
     "expect": "fail", "why": "zorunlu karşı örnek: through delik, kör deliğin yerine geçmez"},
    {"name": "wrong_unit_fails", "reference": "plate_through", "produced": "inch_declared",
     "expect": "fail", "produced_units": "in",
     "why": "zorunlu karşı örnek: inç bildiren dosya mm referansa göre reddedilir",
     "expect_checks": ["units", "alignment"], "old_evaluator": "fail"},
    {"name": "wrong_axis_fails", "reference": "block_through_z", "produced": "block_through_y",
     "expect": "fail", "why": "zorunlu karşı örnek: aynı merkez/çap, yanlış eksen reddedilir",
     "expect_reasons": ["axis"], "old_evaluator": "pass"},
    {"name": "boss_must_not_be_read_as_hole", "reference": "plate_with_boss",
     "produced": "plate_boss_as_hole", "expect": "fail",
     "why": "dış silindir delik sayılmaz; aynı yarıçap ters anlam taşır",
     "old_evaluator": "pass"},
    {"name": "same_box_same_volume_other_part_fails", "reference": "plate_two_holes",
     "produced": "plate_two_holes_staggered", "expect": "fail",
     "why": "zorunlu karşı örnek: eş boyut ve eş hacimli farklı parça reddedilir",
     "old_evaluator": "pass"},
    {"name": "mirrored_part_is_not_fitted_fails", "reference": "plate_asymmetric",
     "produced": "plate_asymmetric_mirrored", "expect": "fail",
     "why": "ayna ile eşleştirme yok; asimetrik parçanın aynası farklı parçadır",
     "old_evaluator": "pass"},
    {"name": "unmodelled_feature_is_not_pass", "reference": "plate_countersunk",
     "produced": "plate_countersunk", "expect": "not_evaluated",
     "why": "destek dışı (konik havşa) sessizce pass vermez"},
    {"name": "coaxial_bores_in_two_walls_stay_two_features", "reference": "stepped_two_bores",
     "produced": "stepped_two_bores", "expect": "pass",
     "why": "aynı eksende, eksenel aralıkları ayrık iki delik birleştirilmez"},
]
