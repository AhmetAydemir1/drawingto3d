"""H01: the feature evaluator must reject a wrong part and accept an equivalent one.

The mandatory counter-examples from the plan are all here: extra and missing hole of the same
diameter, wrong centre, wrong blind depth, wrong unit, wrong axis, and a part with the same box and
the same volume that is still a different part. Plus the acceptances that keep the evaluator honest
in the other direction: the correct part, a re-exported STEP, and an allowed rigid transform —
because an evaluator that fails everything rejects nothing.

Nothing here reads the correct answer out of the evaluator: the fixtures' truth lives in
`eval/feature_fixtures.py` as hand-written analytic specs, and one test checks the extraction against
those specs so a wrong fixture cannot become "the answer".
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Loaded at collection time so the counter-example matrix can parametrise the test.
CASES = load_module("feature_fixtures_for_matrix", ROOT / "eval" / "feature_fixtures.py").CASES


@pytest.fixture(scope="session")
def metrics():
    return load_module("feature_metrics_under_test", ROOT / "eval" / "feature_metrics.py")

@pytest.fixture(scope="session")
def fixtures():
    return load_module("feature_fixtures_under_test", ROOT / "eval" / "feature_fixtures.py")


@pytest.fixture(scope="session")
def fixture_paths(fixtures, tmp_path_factory) -> dict[str, Path]:
    directory = tmp_path_factory.mktemp("feature-fixtures")
    return {name: fixtures.export(name, directory) for name in fixtures.PARTS}


@pytest.fixture(scope="session")
def extract(metrics, fixtures, fixture_paths):
    """`extract(name)` — the fixture's feature record, with its recorded unit."""
    def _extract(name: str, units: str | None = None) -> dict:
        return metrics.extract(fixture_paths[name], units=units or fixtures.SPECS[name]["units"])
    return _extract


# ---------------------------------------------------------------- independent truth


def test_every_fixture_matches_its_hand_written_spec(metrics, fixtures, extract) -> None:
    """The fixtures are the correct answer, so they are checked against arithmetic, not against the
    evaluator's own output."""
    problems = []
    for name, spec in fixtures.SPECS.items():
        record = extract(name)
        if record["unmodelled"] != spec["unmodelled"]:
            problems.append(f"{name}: modellenmeyen {record['unmodelled']} ≠ {spec['unmodelled']}")
        if abs(record["volume_mm3"] - spec["volume_mm3"]) / spec["volume_mm3"] > 1e-6:
            problems.append(f"{name}: hacim {record['volume_mm3']} ≠ {spec['volume_mm3']:.3f}")
        if [round(value, 6) for value in record["bbox"]["size"]] != [round(v, 6) for v in spec["bbox_size"]]:
            problems.append(f"{name}: kutu {record['bbox']['size']} ≠ {spec['bbox_size']}")
        wanted = sorted(spec["features"], key=lambda f: (f["kind"], f["diameter_mm"], f["centre_mm"]))
        if len(record["features"]) != len(wanted):
            problems.append(f"{name}: özellik sayısı {len(record['features'])} ≠ {len(wanted)}")
            continue
        for got, want in zip(record["features"], wanted, strict=True):
            if got["kind"] != want["kind"]:
                problems.append(f"{name}/{got['id']}: tür {got['kind']} ≠ {want['kind']}")
            if abs(got["diameter_mm"] - want["diameter_mm"]) > 1e-6:
                problems.append(f"{name}/{got['id']}: çap {got['diameter_mm']} ≠ {want['diameter_mm']}")
            if any(abs(a - b) > 1e-6 for a, b in zip(got["centre"], want["centre_mm"], strict=True)):
                problems.append(f"{name}/{got['id']}: merkez {got['centre']} ≠ {want['centre_mm']}")
            if got["through"] != want["through"]:
                problems.append(f"{name}/{got['id']}: through {got['through']} ≠ {want['through']}")
            if want["depth_mm"] is not None and got["depth_mm"] is not None:
                if abs(got["depth_mm"] - want["depth_mm"]) > 1e-6:
                    problems.append(f"{name}/{got['id']}: derinlik {got['depth_mm']} ≠ {want['depth_mm']}")
    assert not problems, "fixture ile analitik spec uyuşmuyor:\n" + "\n".join(problems)


# ---------------------------------------------------------------- the counter-example matrix


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_counter_example_matrix(metrics, extract, case: dict) -> None:
    produced = extract(case["produced"], case.get("produced_units"))
    reference = extract(case["reference"])
    verdict = metrics.compare(produced, reference)

    assert verdict["verdict"] == case["expect"], (
        f"{case['name']}: beklenen {case['expect']}, sonuç {verdict['verdict']} "
        f"(hatalı kontroller {verdict['failed_checks']}) — {case['why']}"
    )
    for check in case.get("expect_checks", []):
        assert check in verdict["failed_checks"], (
            f"{case['name']}: {check} kontrolü başarısız olmalıydı, olanlar {verdict['failed_checks']}")
    issue_types = {issue["type"] for issue in verdict["issues"]}
    for reason in case.get("expect_reasons", []):
        assert reason in issue_types, (
            f"{case['name']}: {reason} sorunu bekleniyordu, bulunanlar {sorted(issue_types)}")


# ---------------------------------------------------------------- specific failure modes


def test_the_extra_hole_is_named_in_the_verdict(metrics, extract) -> None:
    produced = extract("plate_extra_hole")
    reference = extract("plate_through")
    verdict = metrics.compare(produced, reference)
    assert [feature["centre"] for feature in verdict["extra_features"]] == [[-15.0, 0.0, 0.0]]
    assert verdict["missing_features"] == []


def test_split_cylinder_faces_are_one_feature_and_coaxial_bores_are_two(metrics) -> None:
    """A face split by the kernel is not a second hole; two bores in separate walls are two holes.
    The kernel did not split our fixture bore, so the rule is tested on explicit face records."""
    half = dict(radius=4.0, direction=[0.0, 0.0, 1.0], point=[10.0, 0.0, 0.0], inner=True,
                area=60.0, through=True)
    first = {**half, "span_min": [10.0, 0.0, -2.5], "span_max": [10.0, 0.0, 0.0]}
    second = {**half, "span_min": [10.0, 0.0, 0.0], "span_max": [10.0, 0.0, 2.5]}
    assert len(metrics.group_cylinders([first, second])) == 1

    lower = {**half, "span_min": [10.0, 0.0, -5.0], "span_max": [10.0, 0.0, -2.0]}
    upper = {**half, "span_min": [10.0, 0.0, 2.0], "span_max": [10.0, 0.0, 5.0]}
    assert len(metrics.group_cylinders([lower, upper])) == 2

    outside = {**first, "inner": False}
    assert len(metrics.group_cylinders([first, outside])) == 2

    other_radius = {**second, "radius": 5.0}
    assert len(metrics.group_cylinders([first, other_radius])) == 2


def test_an_unreadable_step_never_passes(metrics, extract, tmp_path) -> None:
    broken = tmp_path / "broken.step"
    broken.write_text("ISO-10303-21;\nbu bir STEP değil\n")
    record = metrics.extract(broken)
    assert record["solids"] == 0
    assert record["unreadable"]

    verdict = metrics.compare(record, extract("plate_through"))
    assert verdict["verdict"] == "error"
    assert "readable" in verdict["failed_checks"]


def test_the_coarse_evaluator_would_have_passed_the_wrong_parts(metrics, extract) -> None:
    """Why H01 exists: the coarse check looks at a sorted box, a volume and a radius *set*, so a part
    with an extra hole of the same diameter, a moved layout or a mirrored rib passes it. This test
    does not run the coarse evaluator (it needs the CadQuery interpreter); it asserts the two facts
    the coarse checks measure are identical for those pairs, which is what made it blind to them."""
    for produced_name, reference_name in (("plate_extra_hole", "plate_through"),
                                          ("plate_two_holes_staggered", "plate_two_holes"),
                                          ("plate_asymmetric_mirrored", "plate_asymmetric")):
        produced = extract(produced_name)
        reference = extract(reference_name)
        assert sorted(produced["bbox"]["size"]) == sorted(reference["bbox"]["size"])
        assert abs(produced["volume_mm3"] - reference["volume_mm3"]) <= 0.25 * reference["volume_mm3"]
        assert sorted({round(f["diameter_mm"] / 2, 2) for f in produced["features"]}) == \
            sorted({round(f["diameter_mm"] / 2, 2) for f in reference["features"]}), produced_name
        assert metrics.compare(produced, reference)["verdict"] == "fail"


# ---------------------------------------------------------------- alignment rules


def test_only_proper_rotations_are_allowed_alignments(metrics) -> None:
    matrices = metrics._rotation_matrices()
    assert len(matrices) == 24
    for name, matrix in matrices:
        assert abs(metrics._determinant(matrix) - 1.0) < 1e-9, name
    mirror = [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert all(matrix != mirror for _, matrix in matrices)


def test_a_part_needing_rescaling_has_no_allowed_alignment(metrics, extract) -> None:
    reference = extract("plate_through")
    inch = extract("inch_declared", "in")
    assert metrics.possible_alignments(inch["bbox"], reference["bbox"], metrics.TOLERANCES["bbox_mm"]) == []
    assert inch["recorded_units"] == "in"


# ---------------------------------------------------------------- tolerances are fixed


def test_tolerances_are_pinned_before_results(metrics) -> None:
    """A tolerance that moves after a measurement is not a tolerance. If a real part needs a wider
    one, that is a decision with new evidence — change it here, in the open, not silently."""
    assert metrics.TOLERANCES == {
        "position_mm": 0.05,
        "diameter_mm": 0.02,
        "depth_mm": 0.05,
        "axis_angle_deg": 0.5,
        "bbox_mm": 0.05,
        "unit_ratio_frac": 0.02,
    }
    assert metrics.EVALUATOR_VERSION == "feature-metrics/1.0.0"
    assert metrics.SCHEMA_VERSION == "drawingto3d.features/1"
    assert metrics.MATERIAL_TOL_MM == 0.25


# ---------------------------------------------------------------- printed nominal values


def test_printed_nominal_uses_the_drawing_tolerance(metrics, fixtures, extract) -> None:
    record = extract("plate_through")
    good = metrics.compare_printed(record, fixtures.PRINTED_SPEC)
    assert good["ok"] is True
    assert good["extra_features"] == []
    assert good["unspecified"] == fixtures.PRINTED_SPEC["unspecified"]

    # A hole 0.2 mm off the printed Ø8 with the drawing's ±0.1 must fail; 0.05 must pass.
    spec = json.loads(json.dumps(fixtures.PRINTED_SPEC))
    spec["features"][0]["diameter_mm"] = 8.2
    assert metrics.compare_printed(record, spec)["ok"] is False
    spec["features"][0]["diameter_mm"] = 8.05
    assert metrics.compare_printed(record, spec)["ok"] is True


def test_an_attribute_the_drawing_does_not_state_is_not_required(metrics, extract) -> None:
    record = extract("plate_through")
    spec = {"units": "mm", "features": [{"id": "basılı-1", "kind": "hole", "diameter_mm": 8.0}]}
    result = metrics.compare_printed(record, spec)
    assert result["ok"] is True
    assert set(result["results"][0]["unspecified_attributes"]) == {"through", "depth_mm", "axis",
                                                                   "x", "y", "z"}


def test_an_extra_feature_fails_the_printed_comparison(metrics, fixtures, extract) -> None:
    record = extract("plate_extra_hole")
    result = metrics.compare_printed(record, fixtures.PRINTED_SPEC)
    assert result["ok"] is False
    assert result["extra_features"], "basılı spec'te olmayan delik bildirilmeliydi"


# ---------------------------------------------------- review R06/R07 regressions
#
# These two findings are about what the evaluator refuses to call verified: a feature small enough to
# sit between probe points, and a printed unit that disagrees. Both are counter-examples from the
# review; the expected behaviour is kept here as an assertion, and the acceptance side (an equivalent
# part still passes, with an exactly zero difference) is asserted next to it.


@pytest.fixture(scope="module")
def hidden_pocket(tmp_path_factory) -> dict:
    """A 20x24x10 block and the same block with one extra 1x1x1 mm planar pocket.

    The pocket is placed strictly between the evaluator's probe lattice points, so a sampled material
    check sees no disagreement at all. Its volume is 1.0 mm³ by hand: 1 x 1 x 1.
    """
    from build123d import Box, Pos, export_step

    directory = tmp_path_factory.mktemp("hidden-pocket")
    plain = Box(20, 24, 10)
    pocketed = plain - Pos(1.25, 1.2, 4.5) * Box(1, 1, 1)
    paths = {"plain": directory / "plain.step", "pocketed": directory / "pocketed.step"}
    export_step(plain, str(paths["plain"]))
    export_step(pocketed, str(paths["pocketed"]))
    return paths


def test_an_unmeasured_planar_pocket_cannot_pass(metrics, hidden_pocket) -> None:
    verdict = metrics.compare(metrics.extract(hidden_pocket["pocketed"]), metrics.extract(hidden_pocket["plain"]))

    assert verdict["verdict"] != "pass", "seyrek örneklemenin görmediği cep pass olmamalı"
    assert verdict["verdict"] == "fail"
    assert "solid_difference" in verdict["failed_checks"]
    detail = verdict["checks"]["solid_difference"]["detail"]
    assert detail["only_in_truth_mm3"] == pytest.approx(1.0, abs=1e-6), "cebin hacmi tam 1 mm³"
    assert detail["only_in_produced_mm3"] == pytest.approx(0.0, abs=1e-6)
    # Why sampling alone is not enough: the material lattice agreed on every point it tested.
    assert verdict["checks"]["material"]["ok"] is True


def test_the_exact_difference_is_a_floor_not_a_feature_allowance(metrics) -> None:
    assert metrics.EXACT_DIFFERENCE_TOL_MM3 <= 1e-3, "tolerans özellik boyutuna gevşetilmemeli"


def test_equivalent_parts_still_pass_with_zero_difference(metrics, fixtures, fixture_paths) -> None:
    from build123d import Rot, export_step

    directory = fixture_paths["plate_through"].parent
    turned = directory / "plate_through_turned.step"
    export_step(Rot(0, 0, 90) * fixtures.PARTS["plate_through"](), str(turned))

    for name, path in (("same file", fixture_paths["plate_through"]), ("turned", turned)):
        verdict = metrics.compare(metrics.extract(path), metrics.extract(fixture_paths["plate_through"]))
        assert verdict["verdict"] == "pass", f"{name} eşdeğer sayılmalıydı"
        assert verdict["checks"]["solid_difference"]["ok"] is True
        assert verdict["checks"]["solid_difference"]["detail"]["only_in_produced_mm3"] == pytest.approx(
            0.0, abs=1e-9)


def test_a_printed_unit_mismatch_decides_the_result(metrics, fixtures, extract) -> None:
    record = extract("plate_through")
    printed = fixtures.SPECS["plate_through"]

    # What the sheet prints is the hand-written spec, not the record: same unit, same callout.
    agreeing = metrics.compare_printed(record, {"units": printed["units"],
                                                "features": printed["features"]})
    assert agreeing["units_ok"] is True
    assert agreeing["ok"] is True, "basılı birim ve basılı ölçülerle eşleşen kayıt geçmeli"
    assert agreeing["failed_checks"] == []

    mismatched = metrics.compare_printed(record, {"units": "in", "features": printed["features"]})
    assert mismatched["units_ok"] is False
    assert mismatched["ok"] is False, "basılı birim uyuşmazlığı ok=true veremez"
    assert "units" in mismatched["failed_checks"]

    # Bir delik paftada hiç ölçülendirilmemişse bu bir uyuşmazlıktır, yuvarlama farkı değil: sessizce
    # kabul edilmez, adı söylenir. (Birim doğru olsa bile ok=true olmaz.)
    silent = metrics.compare_printed(record, {"units": "mm", "features": []})
    assert silent["units_ok"] is True
    assert silent["failed_checks"] == ["extra_features"]
