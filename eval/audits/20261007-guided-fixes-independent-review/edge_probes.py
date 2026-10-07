"""Independent rotation/order and same-version import checks; no CAD or model calls."""
import copy
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "eval/audits/20261006-guided-g4-g8-independent-review"))
import test_view_core as views
from test_guided_callout_chain import _with_callout_on
from review_probes import H, TOKEN, store_in
from import_review_probes import attempt, bundle_for
from drawingto3d import callout_compile, guided


def rotated(root, angle, edge, reverse):
    r = views._record(root, name=f"rot-{angle}-{edge}-{reverse}", border=False)
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)

    def turn(point):
        x, y = point
        return [200 + c * x - s * y, 200 + s * x + c * y]

    options = r["options"]
    options["frame"] = {"width": 600, "height": 600}
    options["sheet_frame"] = None
    for profile in options["profiles"]:
        profile["points"] = [turn(p) for p in profile.get("points", [])]
        for item in profile.get("edges", []):
            for key in ("start", "end", "center"):
                if item.get(key) is not None:
                    item[key] = turn(item[key])
    for item in options.get("primitives", []):
        for key in ("start", "end", "center"):
            if item.get(key) is not None:
                item[key] = turn(item[key])
    for side in ("first", "second"):
        r["decisions"]["calibration"][side] = turn(r["decisions"]["calibration"][side])
    r["decisions"]["view"] = {"x_page": [c, s], "y_page": [s, -c], "source": "page_axes"}
    ids = [f"g{edge}:start", f"g{edge}:end"]
    if reverse:
        ids.reverse()
    _with_callout_on(r, text="50 mm" if edge % 2 == 0 else "30 mm", ids=ids)
    untouched = copy.deepcopy(r)
    compilation = callout_compile.compile_callouts(r)
    plan = guided.make_plan({**r, "decisions": callout_compile.apply_compiled(r["decisions"], compilation)})
    expected_vectors = sorted([(50, 0, 50), (-50, 0, 50), (0, 30, 30), (0, -30, 30)])
    actual = views._edge_vectors(plan)
    return {"case": f"rotate_{angle}_edge_{edge}_reverse_{reverse}",
            "axis": compilation["bindings"][0]["axis"],
            "direction": compilation["bindings"][0]["direction"],
            "edge_vectors": actual, "record_unchanged": r == untouched,
            "passed": actual == expected_vectors and r == untouched}


def same_version(root):
    store = store_in(root, "same_version", "Ø8 THRU")
    bundle = bundle_for(store)
    record = store.load(TOKEN)
    next(c for c in record["options"]["circles"] if c["id"] == "c0")["center"] = [70, 45]
    guided._atomic(H["_session_path"](store), record)
    result = attempt(store, bundle)
    result.update(case="same_version_same_revision_moved_geometry",
                  geometry_version_unchanged=bundle["geometry_version"] == record["geometry_version"],
                  revision_unchanged=bundle["base_revision"] == record["revision"])
    return result


def main():
    with tempfile.TemporaryDirectory(prefix="guided-fix-edge-review-") as temporary:
        root = Path(temporary)
        cases = []
        for angle in (30, 90, 180, 270):
            for edge in range(4):
                for reverse in (False, True):
                    try:
                        cases.append(rotated(root, angle, edge, reverse))
                    except Exception as exc:
                        cases.append({"case": f"rotate_{angle}_edge_{edge}_reverse_{reverse}",
                                      "error": str(exc), "passed": False})
        cases.append(same_version(root))
    print(json.dumps({"cases": cases, "passed": all(c["passed"] for c in cases)},
                     ensure_ascii=False, indent=2))
    return 0 if all(c["passed"] for c in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
