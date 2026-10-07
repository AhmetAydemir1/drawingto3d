"""G11 probe — what the *user sees* for a sheet: candidates, hints and the session's own options.

    ~/.hermes/cache/scratch/cdp-venv/bin/python g11_probe.py "<source_path>" <out_basename>

Read-only: it opens a fresh session for the sheet, waits for the trace, writes a trimmed JSON of the
visible data (candidate hints/regions, profile ids with bounds, circle ids/radii/centres, measurement
texts, detection diagnostics) plus a screenshot, and closes. It never reads a reference STEP — the
recipe author works from this (the same information the interface displays) and nothing else.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

G11_DIR = pathlib.Path(__file__).parent
ROOT = G11_DIR.parents[2]
sys.path.insert(0, str(G11_DIR.parent / "20261007-guided-ux-round"))
sys.path.insert(0, str(G11_DIR.parent / "20261006-guided-g3-review"))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402
import ux_acceptance as UX  # noqa: E402

sys.path.insert(0, str(G11_DIR))
from g11_runner import wait_ingest  # noqa: E402


def main() -> int:
    source = ROOT / sys.argv[1]
    name = sys.argv[2]
    out = G11_DIR / "probes"
    out.mkdir(exist_ok=True)
    token = sys.argv[3] if len(sys.argv) > 3 else ""
    if token:
        # recover an orphaned session whose client fetch died (the server kept computing)
        page = C.Chrome(url=G3.APP + "/guided?session=" + token)
        page.wait_ready()
    else:
        page = C.Chrome(url=G3.APP + "/guided")
        page.wait_ready()
        page.set_file("#file", str(source))
    page.wait_ev("!$('controls').hidden", timeout=900, label="session opened")
    data = wait_ingest(page)
    time.sleep(1.0)

    def bbox(points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]

    options = data.get("options") or {}
    snapshot = {
        "case_source": sys.argv[1],
        "token": data.get("token"),
        "candidates": [{"id": row["id"], "hint": row.get("machine_text_hint"),
                        "region": [round(v, 4) for v in row["region"]]}
                       for row in data.get("effective_callouts") or []],
        "profiles": [{"id": row["id"], "points": len(row.get("points") or []),
                      "bbox": bbox(row["points"]) if row.get("points") else None,
                      "closed": bool(row.get("closed")) if "closed" in row else None,
                      "edges": [edge.get("kind") for edge in row.get("edges") or []]}
                     for row in options.get("profiles") or []],
        "circles": [{"id": row["id"], "radius": round(row.get("radius") or 0, 3),
                     "center": [round(value, 1) for value in (row.get("center") or [])]}
                    for row in options.get("circles") or []],
        "measurements": [{"id": row["id"], "text": row.get("text"),
                          "keys": sorted(row)} for row in options.get("measurements") or []],
        "sketch_keys": sorted(data.get("sketch") or {}),
        "detection": data.get("callout_detection"),
        "summary": page.ev("return $('summary').textContent;"),
    }
    (out / f"{name}.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    shots = G11_DIR / "shots"
    shots.mkdir(exist_ok=True)
    page.screenshot(str(shots / f"probe-{name}.png"))
    print(json.dumps({"candidates": len(snapshot["candidates"]),
                      "profiles": [(row["id"], row["points"], row["bbox"]) for row in snapshot["profiles"]],
                      "circles": [(row["id"], row["radius"]) for row in snapshot["circles"]],
                      "measurements": [row["text"] for row in snapshot["measurements"]],
                      "summary": snapshot["summary"]}, ensure_ascii=False)[:1500], flush=True)
    page.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
