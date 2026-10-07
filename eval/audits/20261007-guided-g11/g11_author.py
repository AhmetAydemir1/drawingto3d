"""G11 recipe-authoring probe — select a contour the way a user does and look at the trace.

    ~/.hermes/cache/scratch/cdp-venv/bin/python g11_author.py "<source_path>" <name> <profile_id>

Opens a fresh session, picks the profile with the contour tool (a real canvas click, exactly what the
user does), waits until the session records that choice, then writes a screenshot of the traced result
and the session's own trace summary (`sketch`, summary line, proposals). Read-only after the click:
the author looks at the picture and the numbers, then writes the recipe. The reference STEP is never
touched here.
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
from g11_runner import click_image_point, wait_ingest  # noqa: E402


def main() -> int:
    source = ROOT / sys.argv[1]
    name, profile_id = sys.argv[2], sys.argv[3]
    page = C.Chrome(url=G3.APP + "/guided")
    page.wait_ready()
    page.set_file("#file", str(source))
    page.wait_ev("!$('controls').hidden", timeout=900, label="session opened")
    data = wait_ingest(page)
    time.sleep(1.0)
    profile = next((row for row in data["options"]["profiles"] if row["id"] == profile_id), None)
    if profile is None:
        raise SystemExit(f"no profile {profile_id}")
    page.click_selector("#pick-profile")
    time.sleep(0.3)
    click_image_point(page, profile["points"][0])
    try:
        page.wait_ev(f"$('profile').value === {json.dumps(profile_id)}", timeout=30, label="profile")
    except TimeoutError:
        click_image_point(page, profile["points"][len(profile["points"]) // 2])
        page.wait_ev(f"$('profile').value === {json.dumps(profile_id)}", timeout=30, label="profile retry")
    time.sleep(1.2)
    out = G11_DIR / "probes"
    out.mkdir(exist_ok=True)
    shots = G11_DIR / "shots"
    shots.mkdir(exist_ok=True)
    page.screenshot(str(shots / f"author-{name}-{profile_id}.png"))
    snapshot = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      return {summary: $('summary').textContent,
              profile: $('profile').value,
              proposals: (data.proposals || []).map(row => row.text || row.label || JSON.stringify(row)),
              proposal_rows: [...document.querySelectorAll('#proposals .proposal')].map(row => row.textContent),
              sketch: data.sketch || null,
              decisions: {profile_id: data.decisions.profile_id,
                          thickness: data.decisions.thickness,
                          calibration: data.decisions.calibration}};""")
    (out / f"author-{name}-{profile_id}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"profile": snapshot["profile"], "summary": snapshot["summary"],
                      "proposals": snapshot["proposals"],
                      "sketch_rows": (snapshot["sketch"] or {}).get("rows")}, ensure_ascii=False)[:1600],
          flush=True)
    page.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
