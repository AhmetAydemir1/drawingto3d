"""Feature-level comparison of a produced STEP against a ground-truth STEP.

A drawing does not carry enough information to rebuild the same B-rep (catalog fittings have cast
fillets, blends and tapers that nobody dimensions). So the eval asks the engineering question
instead: is this a functionally equal part?

    .venv-cad/bin/python eval/metrics.py out/eval/flange-1/part.step "examples/pdf with steps/Flange.STEP"

Checks, in order of how much they matter:
  solids      exactly one closed solid                  (hard)
  vector      the three bounding-box lengths            (hard, 2% or 1 mm)
  volume      material volume                           (soft, 25%: wall and fillet differ)
  cylinders   the set of cylinder radii present         (soft, 0.5 mm: bores, sockets, pipe OD)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq

VECTOR_TOL_MM = 1.0
VECTOR_TOL_FRAC = 0.02
VOLUME_TOL_FRAC = 0.25
RADIUS_TOL_MM = 0.5


def describe(path: str | Path) -> dict:
    """The facts a built or reference STEP can be held to."""
    shape = cq.importers.importStep(str(path))
    solids = shape.solids().vals()
    body = solids[0] if solids else shape.val()
    box = body.BoundingBox()
    faces = body.Faces()
    return {
        "path": str(path),
        "solids": len(solids),
        "valid": bool(body.isValid()),
        "vector": sorted(round(value, 3) for value in (box.xlen, box.ylen, box.zlen)),
        "volume": round(body.Volume() / 1000.0, 3),
        "faces": len(faces),
        "cylinders": _cylinders(faces),
        "face_types": _face_types(faces),
    }


def compare(produced: dict, truth: dict) -> dict:
    """Tolerance-based verdict. Each check reports its own numbers so a failure is readable."""
    checks: dict[str, dict] = {}

    checks["solids"] = _check(
        produced["solids"] == truth["solids"] == 1,
        f"{produced['solids']} katı",
        f"{truth['solids']} katı",
    )
    checks["valid"] = _check(produced["valid"], str(produced["valid"]), "True")

    pairs = zip(produced["vector"], truth["vector"], strict=True)
    deltas = [abs(one - other) for one, other in pairs]
    allowed = [max(VECTOR_TOL_MM, other * VECTOR_TOL_FRAC) for other in truth["vector"]]
    checks["vector"] = _check(
        all(delta <= limit for delta, limit in zip(deltas, allowed, strict=True)),
        _fmt(produced["vector"]),
        f"{_fmt(truth['vector'])} (fark {_fmt([round(d, 2) for d in deltas])})",
    )

    volume_delta = abs(produced["volume"] - truth["volume"]) / max(truth["volume"], 1e-9)
    checks["volume"] = _check(
        volume_delta <= VOLUME_TOL_FRAC,
        f"{produced['volume']:.1f} cm3",
        f"{truth['volume']:.1f} cm3 (%{volume_delta * 100:.0f} fark)",
    )

    missing = [radius for radius in truth["cylinders"] if not _near_any(radius, produced["cylinders"])]
    extra = [radius for radius in produced["cylinders"] if not _near_any(radius, truth["cylinders"])]
    checks["cylinders"] = _check(
        not missing,
        _fmt(produced["cylinders"]),
        f"{_fmt(truth['cylinders'])}; eksik {_fmt(missing)}, fazla {_fmt(extra)}",
    )

    hard = all(checks[name]["ok"] for name in ("solids", "valid", "vector"))
    soft = all(checks[name]["ok"] for name in ("volume", "cylinders"))
    return {"checks": checks, "pass": hard and soft, "shape_ok": hard, "detail_ok": soft}


def _cylinders(faces) -> list[float]:
    """Cylinder radii, which is where bores, sockets and pipe outside diameters show up."""
    radii = []
    for face in faces:
        if face.geomType() != "CYLINDER":
            continue
        try:
            radii.append(round(float(face._geomAdaptor().Cylinder().Radius()), 2))  # noqa: SLF001 - OCC has no public wrapper
        except Exception:  # noqa: BLE001 - a face we cannot measure is not worth failing on
            continue
    return sorted(set(radii))


def _face_types(faces) -> dict:
    types: dict[str, int] = {}
    for face in faces:
        types[face.geomType()] = types.get(face.geomType(), 0) + 1
    return dict(sorted(types.items(), key=lambda item: -item[1]))


def _near_any(value: float, choices: list[float]) -> bool:
    return any(abs(value - choice) <= RADIUS_TOL_MM for choice in choices)


def _check(ok: bool, got: str, want: str) -> dict:
    return {"ok": bool(ok), "got": got, "want": want}


def _fmt(values) -> str:
    return "[" + ", ".join(f"{value:g}" for value in values) + "]"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    produced = describe(sys.argv[1])
    truth = describe(sys.argv[2])
    verdict = compare(produced, truth)
    print(json.dumps({"produced": produced, "truth": truth, "verdict": verdict}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
