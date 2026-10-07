"""R03 regression (independent G4/G8 review fix round): the highlighted proposal is the one [Onayla] writes.

The module/source tests pin the contract; this drives the real served UI in an attached Chrome with
real mouse events: open the callout → click the *second* proposal's label (not its [Seç] button) →
the drawing highlight moves → the general [Onayla] button → the persisted `callout_targets` row must
be that second proposal (pre-fix it was `proposals[0]`) → reload → the panel still shows it. Serves
the app's own static files with an isolated synthetic store on a random localhost port; no user
session, model, PDF ingestion or CAD is touched.

    ~/.hermes/cache/scratch/cdp-venv/bin/python ui_fix_regression.py [tag]

`tag` names the artefacts (`ui-fix-steps-<tag>.json`, `ui-fix-<tag>-NN-*.png`; the caller redirects
stdout to `ui-fix-<tag>.log`). Exit 1 = a step failed.
"""
from __future__ import annotations

import json
import pathlib
import runpy
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

from PIL import Image, ImageDraw

HARNESS = pathlib.Path(__file__).resolve().parent.parent / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # <repo>/eval/audits/<dir> → the repository root
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import app  # noqa: E402

record = G3.record


def wait_callouts(page: C.Chrome, token: str, timeout: float = 90.0):
    """The session the page under test is standing on is really there."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = page.ev_async(f"return await (await fetch('/api/guided/{token}')).json();")
        if data and data.get("effective_callouts"):
            return data
        time.sleep(0.4)
    return None


def proposals_of(page: C.Chrome) -> list:
    """The proposal rows as the page itself reads them (the panel's own endpoint)."""
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return (await (await fetch('/api/guided/propose', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token: token, callout_id: 'k1'})})).json()).proposals;""")


def label_point(page: C.Chrome, index: int) -> dict:
    """Viewport centre of the index-th proposal label, scrolled into view (viewport-relative)."""
    probe = f"""const rows=[...$('target-proposals').querySelectorAll('.feature')];
      if(rows.length<={index})return null;
      const rect=rows[{index}].querySelector('span').getBoundingClientRect();
      const y=rect.top+rect.height/2;
      return {{x:rect.left+rect.width/2,y:y,page_y:window.scrollY+y}};"""
    found = page.ev(probe)
    if not found:
        raise RuntimeError(f"öneri satırı {index} panelde yok")
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    return page.ev(probe)


def canvas_hash(page: C.Chrome) -> str:
    return page.ev("return $('sheet').toDataURL().slice(-96);")


def stored_target(store, token: str):
    return next((row for row in store.load(token)["decisions"].get("callout_targets") or []
                 if row.get("callout_id") == "k1"), None)


def wait_target(store, token: str, timeout: float = 40.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = stored_target(store, token)
        if row:
            return row
        time.sleep(0.4)
    return None


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "after"
    helpers = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))
    token = helpers["TOKEN"]
    temporary = tempfile.TemporaryDirectory(prefix="guided-r03-regression-")
    store = helpers["store"].__wrapped__(pathlib.Path(temporary.name))
    helpers["seed_callouts"](store)
    store.edit_callout(token, 0, "transcribe", {"callout_id": "k1", "raw_text": "Ø8 THRU"})
    drawing = Image.new("RGB", (300, 200), "white")
    canvas = ImageDraw.Draw(drawing)
    canvas.rectangle((10, 10, 290, 190), outline="black")
    canvas.rectangle((20, 20, 120, 80), outline="black")
    for x, y in ((45, 45), (90, 50)):
        canvas.ellipse((x - 6, y - 6, x + 6, y + 6), outline="black")
    drawing.save(store.folder(token) / "drawing.png")

    app.GUIDED = store
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/guided?session={token}"

    page = C.Chrome(url)
    listed = None
    try:
        page.wait_ready()
        data = wait_callouts(page, token)
        record("sentetik oturum gerçek tarayıcıda açıldı",
               bool(data and data.get("effective_callouts")),
               {"url": url, "callouts": [row["id"] for row in (data or {}).get("effective_callouts", [])]})
        page.wait_ev("$('status').textContent.includes('Kaydedilmiş')", timeout=60, label="oturum yüklendi")
        page.click_selector("#pick-callout")
        time.sleep(0.3)
        G3.click_box(page, "k1")
        page.wait_ev("$('target-proposals').querySelectorAll('.feature').length >= 2", timeout=60,
                     label="iki öneri listelendi")
        page.screenshot(str(HERE / f"ui-fix-{tag}-00-proposals.png"))

        listed = proposals_of(page) or []
        record("panel en az iki farklı hedef öneriyor",
               len(listed) >= 2 and listed[0]["target_ids"] != listed[1]["target_ids"],
               {"proposals": [(row["evidence_tier"], row["target_ids"]) for row in listed[:3]]})

        second = listed[1]
        before = canvas_hash(page)
        point = label_point(page, 1)
        page.click(point["x"], point["y"])            # gerçek fare: satırın [Seç] düğmesi değil, etiketi
        time.sleep(0.6)
        page.screenshot(str(HERE / f"ui-fix-{tag}-01-highlight.png"))
        record("ikinci önerinin etiketi çizimde vurguyu taşıdı (gerçek tıklama)",
               canvas_hash(page) != before, {"before": before, "after": canvas_hash(page)})
        label = page.ev("return $('target-confirm').textContent;")
        record("genel [Onayla] hangi öneriyi yazacağını söylüyor", "2. öneri" in str(label),
               {"label": label})

        page.click_selector("#target-confirm")
        stored = wait_target(store, token)
        page.screenshot(str(HERE / f"ui-fix-{tag}-02-confirmed.png"))
        record("kalıcı target vurgulanan öneridir",
               bool(stored) and stored["target_ids"] == second["target_ids"]
               and stored["evidence"][0]["kind"] == "proposal",
               {"stored": stored, "highlighted": second["target_ids"]})

        page.navigate(url)
        page.wait_ev("$('status').textContent.includes('Kaydedilmiş')", timeout=60, label="yeniden açılış")
        page.click_selector("#pick-callout")
        time.sleep(0.3)
        G3.click_box(page, "k1")
        page.wait_ev("$('target-summary').textContent.includes('Onaylı')", timeout=40, label="target panel")
        summary = page.ev("return $('target-summary').textContent;")
        page.screenshot(str(HERE / f"ui-fix-{tag}-03-reloaded.png"))
        record("reload sonrası panel aynı (vurgulanan) hedefi gösteriyor",
               all(str(item) in str(summary) for item in second["target_ids"]),
               {"summary": summary, "expected_ids": second["target_ids"]})

        errors = [entry for entry in page.console if entry.get("level") == "error"
                  and "favicon" not in str(entry.get("text")) and "favicon" not in str(entry.get("url"))]
        record("beklenmeyen konsol hatası yok", not errors,
               {"errors": errors, "failures": page.failures,
                "favicon_error_exempted": [entry for entry in page.console
                                           if "favicon" in str(entry.get("url", ""))
                                           or "favicon" in str(entry.get("text", ""))]})
    finally:
        (HERE / f"ui-fix-steps-{tag}.json").write_text(json.dumps(
            {"url": url, "tag": tag, "session_file": str(helpers["_session_path"](store)),
             "proposals": listed, "stored_target": stored_target(store, token), "steps": G3.STEPS,
             "console": page.console, "rejected_requests": page.failures},
            ensure_ascii=False, indent=2), encoding="utf-8")
        page.close()
        server.shutdown()
        server.server_close()
        temporary.cleanup()

    failed = [step for step in G3.STEPS if not step["passed"]]
    print(f"\n{len(G3.STEPS) - len(failed)}/{len(G3.STEPS)} R03 tarayıcı adımı geçti", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
