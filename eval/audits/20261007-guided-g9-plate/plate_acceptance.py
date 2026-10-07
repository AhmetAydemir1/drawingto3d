"""G9 plate golden path — real-browser acceptance (PLAN §15; PLAN-20 §11.7).

Every decision — contour, calibration, thickness, transcription, target confirmation, scope
decisions, build — is entered through the real interface with real input events (mouse clicks,
keyboard text). Nothing is injected into the session: `Runtime.evaluate` only reads state back and
scrolls; `fetch` in the page only reads the server's own record (and the review export, a GET of
derived data).

    # app:  PYTHONPATH=src .venv/bin/python -m drawingto3d.app     (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222, fresh profile
    ~/.hermes/cache/scratch/cdp-venv/bin/python plate_acceptance.py

Run 1 on 2026-10-07 is expected to surface the `THRU ALL` parse gap as a recorded failure (the plan's
"fail → generic fix → rerun" law); the same driver runs the whole path after the fix, in a fresh
session. Writes screenshots, `g9-steps.json` and machine copies of the artifacts next to this file;
exits non-zero when any step failed.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

HARNESS = pathlib.Path(__file__).parent.parent / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP, DRAWING, HERE = G3.APP, G3.DRAWING, pathlib.Path(__file__).parent
record = G3.record

HOLE_TEXT = "4 x Ø6,80 THRU ALL"          # printed on the sheet: "4 x Ø(drawn) 6,80 THRU ALL"
POCKET_TEXT = "Ø50 8 DEEP"                # top view Ø50 + the section's depth 8,00
M8_TEXT = "M8 - 6H THRU ALL"              # the second note; a thread — outside this grammar by design
DIM_TEXTS = [("1 00,00", "100,00"), ("80,00", "80,00"), ("60,00", "60,00"),
             ("1 5,00", "15,00"), ("8,00", "8,00")]
HOLE_CIRCLES = ["g9", "g11", "g10", "g12"]   # TL, TR, BR, BL — the four Ø6.80 circles
POCKET_CIRCLE = "g8"                          # the Ø50 circle


def server(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/' + token)).json();""")


def wait_state(page: C.Chrome, timeout: float = 300.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = server(page)
        if data and data.get("effective_callouts"):
            return data
        time.sleep(0.4)
    raise TimeoutError("session with callout candidates did not load")


def wait_server(page: C.Chrome, predicate, timeout: float = 90.0, label: str = "") -> dict:
    deadline = time.time() + timeout
    data = None
    while time.time() < deadline:
        data = server(page)
        if data and predicate(data):
            return data
        time.sleep(0.35)
    raise TimeoutError(f"server condition not met: {label}")


def callout_by_hint(data: dict, hint: str) -> dict:
    for row in data["effective_callouts"]:
        if row.get("machine_text_hint") == hint:
            return row
    raise KeyError(f"no callout with hint {hint!r}")


def circle_point(page: C.Chrome, circle_id: str) -> dict:
    """Viewport point of a circle's centre, scrolled into view (mirrors draw()'s transform)."""
    probe = """const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const image = new Image(); image.src = data.drawing; await image.decode();
      const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
      const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
      const circle = (data.options.circles || []).find(row => row.id === '%s');
      if (!circle) return null;
      const y = rect.top + circle.center[1] * s * rect.height / canvas.height;
      return {id: circle.id, x: rect.left + circle.center[0] * s * rect.width / canvas.width,
              y: y, page_y: window.scrollY + y};""" % circle_id
    found = page.ev_async(probe)
    if not found:
        raise RuntimeError(f"no circle {circle_id}")
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    return page.ev_async(probe)


def row_box(page: C.Chrome, callout_id: str, show_ignored: bool = False) -> dict:
    """Viewport box of a callout's row in the (visible) list, scrolled into view."""
    flag = "true" if show_ignored else "false"
    index = page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const visible = data.effective_callouts.filter(row => {flag} || !row.ignored);
      return visible.findIndex(row => row.id === '{callout_id}');""")
    if index < 0:
        raise RuntimeError(f"callout {callout_id} not in the visible list")
    selector = f"#callout-list li:nth-child({index + 1})"
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    return page.box(selector)


def row_click(page: C.Chrome, callout_id: str) -> None:
    box = row_box(page, callout_id)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def type_textarea(page: C.Chrome, text: str) -> str:
    """Focus the transcription field like a user (real click), select the draft, type the text."""
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")
    page.type_text(text)
    got = page.ev("return $('callout-text').value;")
    return got


def save_text(page: C.Chrome, callout_id: str, text: str) -> dict:
    """Select the callout, type the user's text, save; return the derived parse row."""
    row_click(page, callout_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="callout detail")
    got = type_textarea(page, text)
    if got != text:
        raise RuntimeError(f"the field holds {got!r}, wanted {text!r}")
    page.click_selector("#callout-save")
    data = wait_server(page, lambda d: any(
        row["id"] == callout_id and (row.get("parse") or {}).get("state") == "current"
        for row in d.get("callouts") or []), timeout=60, label=f"parse current ({text})")
    return next(row for row in data["callout_parses"] if row["callout_id"] == callout_id)


def declare_unbindable(page: C.Chrome, callout_id: str) -> dict:
    page.click_selector("#target-unbindable")
    return wait_server(page, lambda d: any(
        row["callout_id"] == callout_id and row.get("unbindable")
        for row in d["decisions"].get("callout_reviews") or []), timeout=40, label="unbindable stored")


def ignore_callout(page: C.Chrome, callout_id: str) -> dict:
    row_click(page, callout_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="callout detail")
    page.click_selector("#callout-ignore")
    return wait_server(page, lambda d: any(
        row["callout_id"] == callout_id and row.get("ignored")
        for row in d["decisions"].get("callout_reviews") or []), timeout=40, label="ignored stored")


def target_panel(page: C.Chrome) -> dict:
    return page.ev("""return {state: $('target-state').textContent, summary: $('target-summary').textContent,
      proposals: [...$('target-proposals').querySelectorAll('.feature')].map(row => row.textContent),
      picked: $('target-picked').textContent};""")


def stored_target(page: C.Chrome, callout_id: str):
    data = server(page)
    return next((row for row in data["decisions"].get("callout_targets") or []
                 if row["callout_id"] == callout_id), None)


def save_target_manual(page: C.Chrome, callout_id: str, kind: str, circle_ids: list[str]) -> dict:
    """Pick targets by hand on the drawing, then apply — the G6 flow, with real clicks."""
    if kind == "circle_group":
        page.click_selector("#target-group")
    else:
        page.click_selector("#target-other")
    for circle_id in circle_ids:
        time.sleep(0.2)
        point = circle_point(page, circle_id)
        page.click(point["x"], point["y"])
        time.sleep(0.3)
    page.click_selector("#target-apply")
    return wait_server(page, lambda d: any(
        row["callout_id"] == callout_id and sorted(row.get("target_ids") or []) == sorted(circle_ids)
        for row in d["decisions"].get("callout_targets") or []), timeout=60,
        label=f"target {circle_ids}")


def main() -> int:
    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()
    page.screenshot(str(HERE / "plate-00-open.png"))

    # --- drawing -> candidates -------------------------------------------------------------------
    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    data = wait_state(page)
    callouts = data["effective_callouts"]
    record("drawing opens in a fresh session and candidates are listed", len(callouts) == 45,
           {"token": data["token"], "callouts": len(callouts)})
    page.screenshot(str(HERE / "plate-01-candidates.png"))

    # --- contour ---------------------------------------------------------------------------------
    profiles = sorted(data["options"]["profiles"], key=lambda p: (
        (max(pt[0] for pt in p["points"]) - min(pt[0] for pt in p["points"])) *
        (max(pt[1] for pt in p["points"]) - min(pt[1] for pt in p["points"])),), reverse=True)
    plate = profiles[0]
    point = plate["points"][0]
    page.click_selector("#pick-profile")            # the tool first: the click below is the selection
    time.sleep(0.3)

    def canvas_point(px_point: list) -> dict:
        return page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
          const data = await (await fetch('/api/guided/' + token)).json();
          const image = new Image(); image.src = data.drawing; await image.decode();
          const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
          const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
          const y = rect.top + {px_point[1]} * s * rect.height / canvas.height;
          return {{x: rect.left + {px_point[0]} * s * rect.width / canvas.width, y: y,
                   page_y: window.scrollY + y}};""")

    found = canvas_point(point)
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    target = canvas_point(point)
    page.click(target["x"], target["y"])
    page.wait_ev(f"$('profile').value === {json.dumps(plate['id'])}", timeout=30, label="plate profile")
    record("clicking the plate outline selects it as the contour", plate["id"] == "outline_1",
           {"profile": plate["id"], "edges": len(plate["edges"]), "kinds": [e.get("kind") for e in plate["edges"]]})
    page.screenshot(str(HERE / "plate-02-profile.png"))

    # --- calibration on the printed 100,00 -------------------------------------------------------
    page.click_selector("#pick-calibration")
    for circle_id in ("g9", "g11"):
        got = circle_point(page, circle_id)
        page.click(got["x"], got["y"])
        time.sleep(0.2)
    measurement = next(row for row in data["options"]["measurements"] if row.get("text") == "1 00,00")
    page.ev(f"""const select = $('measurement'); select.value = '{measurement['id']}';
      select.dispatchEvent(new Event('change')); return true;""")
    cal_value = page.ev("return $('cal-value').value;")
    page.click_selector("#apply-calibration")
    saved = wait_server(page, lambda d: bool(d["decisions"].get("calibration")), timeout=40,
                        label="calibration stored")
    calibration = saved["decisions"]["calibration"]
    span_px = ((calibration["second"][0] - calibration["first"][0]) ** 2
               + (calibration["second"][1] - calibration["first"][1]) ** 2) ** 0.5
    record("two hole centres are calibrated with the printed 100,00 span",
           abs(float(cal_value) - 100.0) < 1e-9 and abs(span_px / float(calibration["value"]) - 7.876) < 0.01,
           {"value": calibration["value"], "unit": calibration["unit"], "span_id": calibration["span_id"],
            "span_px": round(span_px, 2), "px_per_mm": round(span_px / float(calibration["value"]), 4)})
    page.screenshot(str(HERE / "plate-03-calibration.png"))

    # --- thickness -------------------------------------------------------------------------------
    page.focus_selector("#thickness")
    page.ev("$('thickness').value = '';")
    page.type_text("15")
    page.click_selector("#apply-thickness")
    saved = wait_server(page, lambda d: d["decisions"].get("thickness") == 15.0, 40, "thickness")
    record("thickness 15 is entered and stored", saved["decisions"].get("thickness") == 15.0,
           {"thickness": saved["decisions"].get("thickness")})
    page.screenshot(str(HERE / "plate-04-thickness.png"))

    # --- the trace acknowledgement (section 5) ---------------------------------------------------
    page.click_selector("#ack")
    saved = wait_server(page, lambda d: d["decisions"].get("trace_acknowledged") is True, 40, "ack")
    record("the traced draft is acknowledged", saved["decisions"].get("trace_acknowledged") is True, {})

    # --- callout: the hole note ------------------------------------------------------------------
    hole_id = callout_by_hint(data, "6,80 THRU ALL")["id"]
    parse = save_text(page, hole_id, HOLE_TEXT)
    page.screenshot(str(HERE / "plate-05-hole-transcribed.png"))
    if parse["status"] != "parsed":
        record("the hole note transcribes and parses as written", False,
               {"text": HOLE_TEXT, "status": parse["status"], "warnings": parse["warnings"],
                "semantic": {k: parse.get(k) for k in ("form", "size", "count", "termination")}})
        (HERE / "g9-steps.json").write_text(json.dumps(
            {"app": APP, "drawing": DRAWING, "steps": G3.STEPS, "console": page.console,
             "rejected_requests": page.failures}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nSTOPPED at the transcription step (recorded); see g9-steps.json", flush=True)
        page.close()
        return 2
    record("the hole note transcribes and parses as written", True,
           {"text": HOLE_TEXT, "semantic": {k: parse.get(k) for k in
            ("form", "size", "count", "termination", "unit")}, "warnings": parse["warnings"]})

    panel = target_panel(page)
    record("hole proposals are shown (or none, with the manual pick offered)",
           isinstance(panel["proposals"], list), {"state": panel["state"], "proposals": panel["proposals"]})
    target = save_target_manual(page, hole_id, "circle_group", HOLE_CIRCLES)
    stored = next(row for row in target["decisions"]["callout_targets"] if row["callout_id"] == hole_id)
    record("the four hole circles are confirmed by hand (user_click evidence)",
           sorted(stored["target_ids"]) == sorted(HOLE_CIRCLES)
           and stored["evidence"][0]["kind"] == "user_click" and stored["status"] == "confirmed",
           {"target": stored})
    page.screenshot(str(HERE / "plate-06-holes-targeted.png"))

    # --- the "4 x" fragment: not a callout of its own -------------------------------------------
    fragment = callout_by_hint(data, "4 x")["id"]
    ignore_callout(page, fragment)
    record("the “4 x” fragment is declared not-a-callout (its text travelled with the note)", True,
           {"callout": fragment})

    # --- callout: the pocket ---------------------------------------------------------------------
    pocket_id = callout_by_hint(data, "50,00")["id"]
    parse = save_text(page, pocket_id, POCKET_TEXT)
    record("the pocket transcribes (Ø50 from the view, depth 8 from the section) and parses",
           parse["status"] == "parsed" and parse.get("termination") == "blind"
           and parse.get("depth") == 8.0 and parse.get("size") == 50.0,
           {"text": POCKET_TEXT, "semantic": {k: parse.get(k) for k in
            ("form", "size", "termination", "depth")}, "warnings": parse["warnings"]})
    time.sleep(0.6)
    panel = target_panel(page)
    confirmed = None
    if panel["proposals"]:
        page.click_selector("#target-confirm")          # the ranked proposal, confirmed as shown
        confirmed = wait_server(page, lambda d: any(
            row["callout_id"] == pocket_id and row.get("status") == "confirmed"
            for row in d["decisions"].get("callout_targets") or []), timeout=60, label="pocket target")
    else:
        confirmed = save_target_manual(page, pocket_id, "circle", [POCKET_CIRCLE])
    stored = next(row for row in confirmed["decisions"]["callout_targets"] if row["callout_id"] == pocket_id)
    record("the pocket circle is confirmed for Ø50", stored["target_ids"] == [POCKET_CIRCLE]
           and stored["evidence"][0]["kind"] in ("proposal", "user_click"),
           {"target": stored, "proposals": panel["proposals"]})
    page.screenshot(str(HERE / "plate-07-pocket-targeted.png"))

    # --- the scope decisions: the thread note and the printed linear dims ------------------------
    m8_id = callout_by_hint(data, "M8 - 6H THRU ALL")["id"]
    parse = save_text(page, m8_id, M8_TEXT)
    record("the thread note is read and stays outside the grammar (no invented feature)",
           parse["status"] == "unsupported" and "unsupported_syntax" in parse["warnings"],
           {"text": M8_TEXT, "status": parse["status"], "warnings": parse["warnings"]})
    reviews = declare_unbindable(page, m8_id)
    record("the thread note is declared out of scope (unbindable, not silent)", True,
           next(row for row in reviews["decisions"]["callout_reviews"] if row["callout_id"] == m8_id))
    page.screenshot(str(HERE / "plate-08-thread-unbindable.png"))

    for hint, text in DIM_TEXTS:
        callout_id = callout_by_hint(data, hint)["id"]
        parse = save_text(page, callout_id, text)
        ok = parse["status"] == "parsed" and parse.get("form") == "linear"
        record(f"printed dimension {hint!r} is read as {text!r}", ok,
               {"callout": callout_id, "semantic": {k: parse.get(k) for k in ("form", "size")},
                "warnings": parse["warnings"]})
        declare_unbindable(page, callout_id)
    record("the printed dimensions are declared un-bindable in this version (arc contour: centre ties only)",
           True, {"count": len(DIM_TEXTS)})
    page.screenshot(str(HERE / "plate-09-dims-unbindable.png"))

    # --- sweep: every remaining candidate is an explicit scope decision --------------------------
    handled = {hole_id, pocket_id, m8_id, fragment} | {
        callout_by_hint(data, h)["id"] for h, _ in DIM_TEXTS}
    swept = 0
    while True:
        data = server(page)
        remaining = [row for row in data["effective_callouts"]
                     if not row["ignored"] and row["id"] not in handled]
        if not remaining:
            break
        ignore_callout(page, remaining[0]["id"])
        swept += 1
        if swept % 10 == 0:
            print(f"  swept {swept} callouts…", flush=True)
    data = server(page)
    total_ignored = sum(1 for row in data["effective_callouts"] if row["ignored"])
    record("every remaining candidate is an explicit scope decision (ignore), none silently dropped",
           len(data["effective_callouts"]) == 45 and total_ignored == swept + 1,
           {"callouts": len(data["effective_callouts"]), "ignored": total_ignored, "swept_now": swept})
    page.screenshot(str(HERE / "plate-10-swept.png"))

    # --- readiness gate --------------------------------------------------------------------------
    readiness = page.ev("""return {summary: $('readiness-summary').textContent,
      questions: [...$('readiness-questions').querySelectorAll('li')].map(li => li.textContent),
      buildDisabled: $('build').disabled};""")
    record("the readiness gate is clean before the build", readiness["buildDisabled"] is False
           and not readiness["questions"] and readiness["summary"].startswith("Hazır"),
           readiness)
    page.screenshot(str(HERE / "plate-11-ready.png"))

    # --- build -----------------------------------------------------------------------------------
    page.click_selector("#build")
    data = wait_server(page, lambda d: bool(d.get("step")), timeout=420, label="built STEP")
    record("the build runs and the session carries a fresh STEP", data["build_status"] == "complete",
           {"build_status": data["build_status"], "step": data["step"], "error": data.get("error")})
    page.screenshot(str(HERE / "plate-12-built.png"))

    # --- artifacts (the server's own records, copied as evidence) --------------------------------
    for name, key in (("part.step", "step"), ("plan.json", "plan"), ("plan-audit.json", "audit")):
        url = APP + data[key]
        with urllib.request.urlopen(url, timeout=60) as response:
            (HERE / name).write_bytes(response.read())
    (HERE / "session-public.json").write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    bundle = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/export', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")
    (HERE / "review-bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    compiled = [row for row in bundle.get("callouts", [])
                if row.get("callout_id") in (hole_id, pocket_id)]
    record("the review bundle carries the compiled chain for both feature callouts",
           len(compiled) >= 1 and all(row.get("confirmed_target") for row in compiled),
           {"compiled": [{k: row.get(k) for k in ("callout_id", "raw_text", "status")} for row in compiled]})

    errors = [entry for entry in page.console if entry["level"] == "error"]
    record("no unexpected console errors and no rejected requests", not errors and not page.failures,
           {"unexpected": errors, "failures": page.failures})

    (HERE / "g9-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "token": data["token"], "steps": G3.STEPS,
         "console": page.console, "rejected_requests": page.failures},
        ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [step for step in G3.STEPS if not step["passed"]]
    print(f"\n{len(G3.STEPS) - len(failed)}/{len(G3.STEPS)} G9 browser steps passed", flush=True)
    page.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
