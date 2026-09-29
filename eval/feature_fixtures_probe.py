"""Build every fixture and check the extraction against its hand-written analytic spec.

    .venv/bin/python eval/feature_fixtures_probe.py

This is a fixture self-check, not a product test: it exists so a wrong fixture cannot quietly become
"the correct answer". A disagreement is printed with both numbers; it is never fixed by editing the
spec to match the kernel.
"""

from __future__ import annotations

import importlib.util

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load("feature_metrics", ROOT / "eval" / "feature_metrics.py")
fixtures = _load("feature_fixtures", ROOT / "eval" / "feature_fixtures.py")


def check_spec(name: str, record: dict, spec: dict) -> list[str]:
    problems = []
    if spec["units"] != record["recorded_units"]:
        problems.append(f"birim: {record['recorded_units']} ≠ {spec['units']}")
    if record["bbox"] is None:
        return problems + ["kutu ölçüsü okunamadı"]
    for axis, want in zip("xyz", spec["bbox_size"], strict=True):
        got = record["bbox"]["size"]["xyz".index(axis)]
        if abs(got - want) > 1e-6:
            problems.append(f"kutu {axis}: {got} ≠ {want}")
    relative = abs(record["volume_mm3"] - spec["volume_mm3"]) / spec["volume_mm3"]
    if relative > 1e-6:
        problems.append(f"hacim: {record['volume_mm3']} ≠ {spec['volume_mm3']:.3f} (%{relative * 100:.4f})")
    if record["unmodelled"] != spec["unmodelled"]:
        problems.append(f"modellenmeyen: {record['unmodelled']} ≠ {spec['unmodelled']}")
    if len(record["features"]) != len(spec["features"]):
        problems.append(f"özellik sayısı: {len(record['features'])} ≠ {len(spec['features'])}")
        return problems
    for got, want in zip(record["features"],
                         sorted(spec["features"], key=lambda f: (f["kind"], f["diameter_mm"], f["centre_mm"])),
                         strict=False):
        if got["kind"] != want["kind"]:
            problems.append(f"{got['id']} türü: {got['kind']} ≠ {want['kind']}")
        if abs(got["diameter_mm"] - want["diameter_mm"]) > 1e-6:
            problems.append(f"{got['id']} çap: {got['diameter_mm']} ≠ {want['diameter_mm']}")
        if any(abs(a - b) > 1e-6 for a, b in zip(got["centre"], want["centre_mm"], strict=True)):
            problems.append(f"{got['id']} merkez: {got['centre']} ≠ {want['centre_mm']}")
        if got["through"] != want["through"]:
            problems.append(f"{got['id']} through: {got['through']} ≠ {want['through']}")
        if want["depth_mm"] is not None and got["depth_mm"] is not None:
            if abs(got["depth_mm"] - want["depth_mm"]) > 1e-6:
                problems.append(f"{got['id']} derinlik: {got['depth_mm']} ≠ {want['depth_mm']}")
    return problems


def main() -> int:
    directory = Path(tempfile.mkdtemp(prefix="feature-fixtures-"))
    failures = 0
    for name, spec in fixtures.SPECS.items():
        path = fixtures.export(name, directory)
        record = metrics.extract(path, units=spec["units"])
        problems = check_spec(name, record, spec)
        faces = sum(record["face_types"].values())
        print(f"{'OK  ' if not problems else 'HATA'} {name:38s} katı={record['solids']} yüz={faces} "
              f"özellik={len(record['features'])} modellenmeyen={record['unmodelled'] or '-'}")
        for problem in problems:
            failures += 1
            print(f"      - {problem}")
        for feature in record["features"]:
            print(f"      {feature['id']:10s} {feature['kind']:5s} Ø{feature['diameter_mm']:8.3f} "
                  f"merkez {feature['centre']} eksen {feature['axis_direction']} "
                  f"through={feature['through']} derinlik={feature['depth_mm']} yüz={feature['faces']}")
    print(f"\nfixture dizini: {directory}")
    print(f"uyumsuzluk: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
