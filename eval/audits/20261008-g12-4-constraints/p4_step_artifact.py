#!/usr/bin/env python
"""G12.4 kanıtı (PLAN-25 §60): P4 dikdörtgen senaryosunu ürün yoluyla üretir, STEP'i ve denetimi saklar.

Senaryo `tests/test_g12_p4_constraints.py` ile birebir aynıdır — yardımcıları oradan alır, akışın kopyası
yok. Çıktılar: `p4-rectangle.step` (gerçek katı), `p4-geometry.json` (yeniden açılan katının olguları),
`p4-provenance.json` (§57 koordinat kökenleri + §59 N/M denetimi).
"""
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "src"))

from drawingto3d.guided import Decisions, user_dimensions                # noqa: E402
from test_g12_p4_constraints import _corner, _facts, _record, _tie       # noqa: E402

SCALE = 2.0


def main() -> int:
    work = pathlib.Path(tempfile.mkdtemp(prefix="g124-p4-"))
    probe = _record(work, name="probe")
    v0, v1 = _corner(probe, 20, 20), _corner(probe, 120, 20)
    v2, v3 = _corner(probe, 120, 80), _corner(probe, 20, 80)
    bindings = [_tie("width", 60.0, v0, v1),
                _tie("bottom_width", 60.0, v3, v2),
                _tie("left_height", 40.0, v0, v3),
                _tie("right_height", 40.0, v1, v2),
                _tie("cross_width", 60.0, v1, v3),
                _tie("height", 40.0, v0, v2, axis="y")]
    holes = [{"circle_id": "c0", "kind": "through", "diameter": 6.0, "depth": None}]
    record = _record(work, bindings=bindings, holes=holes)
    _plan, step, facts = _facts(work, record, name="out")
    shutil.copy(step, HERE / "p4-rectangle.step")
    (HERE / "p4-geometry.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    profile = json.loads(json.dumps(next(p for p in record["options"]["profiles"] if p["kind"] == "wire")))
    report = user_dimensions(profile, record["options"], Decisions.model_validate(record["decisions"]),
                             SCALE, [min(p[0] for p in profile["points"]), max(p[1] for p in profile["points"])])
    assert report is not None, "bağlar çözülmeden kanıt yazılmaz"
    provenance = {"audit": report["audit"], "status": report["status"], "coordinates": report["coordinates"],
                  "bindings": [row["id"] for row in bindings]}
    (HERE / "p4-provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    print("STEP:", HERE / "p4-rectangle.step", (HERE / "p4-rectangle.step").stat().st_size, "bayt")
    print("size:", facts["size"], "volume:", round(facts["volume"], 4), "cylinders:", facts["cylinders"])
    print("audit:", report["audit"], "status:", report["status"])
    shutil.rmtree(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
