"""G9 UX turu — real-browser acceptance (PLAN-23 §15 dar tur; DELIVERY-PLAN.md dondurulmuş ölçütler).

Same rule as the G9 driver: every decision goes in through the real interface with real input events
(mouse clicks, keyboard text). `Runtime.evaluate` only reads state back, scrolls, and fetches the
server's own record. The drawing is the same plate as G9.

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app        (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222, fresh profile (chrome-ux-round)
    ~/.hermes/cache/scratch/cdp-venv/bin/python ux_acceptance.py

Writes screenshots, `ux-steps.json` and machine copies of the artifacts next to this file; exits
non-zero when any step failed.
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

HOLE_TEXT = "4 x Ø6,80 THRU ALL"          # composite: printed as two boxes ("4 x" + "6,80 THRU ALL")
POCKET_TEXT = "Ø50 8 DEEP"                # composite: Ø50 from the view, 8 from the section
M8_HINT = "M8 - 6H THRU ALL"              # hint == printed text: one click
DIM_SINGLE = ["80,00", "60,00", "8,00"]   # hint == printed text: one click each
DIM_TYPED = {"1 00,00": "100,00", "1 5,00": "15,00"}   # spacing the user corrects by hand
HOLE_CIRCLES = ["g9", "g11", "g10", "g12"]
POCKET_CIRCLE = "g8"


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


def reviews_of(data: dict) -> dict:
    return {row["callout_id"]: row for row in data["decisions"].get("callout_reviews") or []}


def undecided_ids(data: dict) -> list[str]:
    states = {row["id"]: row for row in data.get("callouts") or []}
    out = []
    for row in data["effective_callouts"]:
        state = ((states.get(row["id"]) or {}).get("transcription") or {}).get("state", "missing")
        if not row["ignored"] and not row.get("unbindable") and state == "missing":
            out.append(row["id"])
    return out


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
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")
    page.type_text(text)
    return page.ev("return $('callout-text').value;")


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


def accept_hint(page: C.Chrome, callout_id: str) -> dict:
    """The single click: the callout's own machine hint becomes the user's transcription."""
    row_click(page, callout_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="callout detail")
    before = {"field": page.ev("return $('callout-text').value;"),
              "hint_line": page.ev("return $('callout-hint-line').textContent;"),
              "clicks": 0}
    page.click_selector("#callout-hint-save")          # the only input: one real click
    before["clicks"] = 1
    data = wait_server(page, lambda d: any(
        row["callout_id"] == callout_id and row.get("raw_text")
        for row in d["decisions"].get("transcriptions") or []), timeout=60, label=f"hint accepted ({callout_id})")
    return {"before": before, "data": data}


def declare_unbindable(page: C.Chrome, callout_id: str) -> dict:
    page.wait_ev("!$('target-panel').hidden", timeout=30, label="target panel")
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


def save_target_manual(page: C.Chrome, callout_id: str, kind: str, circle_ids: list[str]) -> dict:
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
        for row in d["decisions"].get("callout_targets") or []), timeout=60, label=f"target {circle_ids}")


def checklist_probe(page: C.Chrome) -> dict:
    return page.ev("""return {summary: $('readiness-summary').textContent,
      items: [...$('readiness-questions').querySelectorAll('li')].map(li => ({
        text: li.textContent,
        badge: (li.querySelector('.badge') || {}).textContent || '',
        button: !!li.querySelector('button'),
        buttonText: (li.querySelector('button') || {}).textContent || ''})),
      buildDisabled: $('build').disabled};""")


def readiness_of(page: C.Chrome) -> dict:
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/readiness', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")


def click_checklist_item(page: C.Chrome, index: int) -> None:
    selector = f"#readiness-questions li:nth-child({index + 1})"
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def main() -> int:
    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()
    page.screenshot(str(HERE / "ux-00-open.png"))

    # --- drawing -> candidates -------------------------------------------------------------------
    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    data = wait_state(page)
    total = len(data["effective_callouts"])
    record("the plate opens in a fresh session with 45 candidates", total == 45, {"token": data["token"],
           "callouts": total})
    page.screenshot(str(HERE / "ux-01-candidates.png"))

    listing = page.ev("""return {summary: $('callout-summary').textContent,
      rows: document.querySelectorAll('#callout-list li').length,
      next: $('callout-next').textContent, nextDisabled: $('callout-next').disabled,
      many: $('callout-ignore-many').textContent, manyDisabled: $('callout-ignore-many').disabled};""")
    record("45 candidates = 45 listed rows, 45 undecided, nothing hidden by default",
           listing["rows"] == 45 and "45 etkin alan" in listing["summary"]
           and "45 kararsız" in listing["summary"] and listing["next"] == "Sıradaki kararsız (45)"
           and listing["nextDisabled"] is False and listing["manyDisabled"] is False, listing)

    # --- readiness as an actionable checklist ----------------------------------------------------
    readiness = readiness_of(page)
    probe = checklist_probe(page)
    badges = sorted({item["badge"] for item in probe["items"]})
    record("the readiness list is an actionable checklist: every item names its category and offers “Git”",
           len(probe["items"]) == len(readiness["questions"]) > 0
           and all(item["button"] and item["buttonText"] == "Git" and item["badge"] for item in probe["items"]),
           {"items": len(probe["items"]), "questions": len(readiness["questions"]), "badges": badges,
            "build_disabled": probe["buildDisabled"]})
    page.screenshot(str(HERE / "ux-02-checklist.png"))

    first_text = next((index for index, row in enumerate(readiness["questions"])
                       if row["action"] == "transcribe" and row["callout_id"]), None)
    if first_text is None:
        record("a callout item can be opened from the checklist", False, readiness["questions"][:5])
    else:
        want = readiness["questions"][first_text]["callout_id"]
        label = 'C%d' % ([row["id"] for row in data["effective_callouts"]].index(want) + 1)
        click_checklist_item(page, first_text)
        page.wait_ev("document.activeElement && document.activeElement.id === 'callout-text'",
                     timeout=30, label="checklist -> callout text")
        focused = page.ev("return {title: $('callout-title').textContent, active: document.activeElement.id,"
                          " hidden: $('callout-detail').hidden};")
        record("a transcribe item opens its own callout and puts the focus in the text field",
               focused["active"] == "callout-text" and focused["hidden"] is False
               and focused["title"].startswith(label + " "), {"item": first_text, "want": want,
               "label": label, **focused})
    sheet_issue = next((index for index, row in enumerate(readiness["questions"])
                        if row["category"] == "missing_profile"), None)
    if sheet_issue is None:
        record("the contour item opens the contour control", False, "no missing_profile question")
    else:
        click_checklist_item(page, sheet_issue)
        page.wait_ev("document.activeElement && document.activeElement.id === 'profile'", timeout=30,
                     label="checklist -> profile")
        record("the contour item opens the contour control", True,
               {"item": sheet_issue, "active": page.ev("return document.activeElement.id;")})
    page.screenshot(str(HERE / "ux-03-checklist-jump.png"))

    # --- next-unresolved ------------------------------------------------------------------------
    # Position-independent: the checklist step above already selected the first undecided callout,
    # so "next" must move strictly forward from whatever is selected now — that *is* its contract.
    before_next = page.ev("""return {title: $('callout-title').textContent,
      selected: [...document.querySelectorAll('#callout-list li')].findIndex(li => li.classList.contains('selected'))};""")
    steps = []
    for jump in (1, 2):
        want = 'C%d ' % (before_next["selected"] + 1 + jump)
        page.click_selector("#callout-next")
        page.wait_ev(f"$('callout-title').textContent.startsWith({json.dumps(want)})", timeout=30,
                     label=f"next {jump}")
        steps.append(page.ev("""return {title: $('callout-title').textContent, status: $('status').textContent,
          selected: [...document.querySelectorAll('#callout-list li')].findIndex(li => li.classList.contains('selected'))};"""))
    record("next-unresolved walks the undecided list strictly forward and the counter follows",
           before_next["selected"] == 0 and [row["selected"] for row in steps] == [1, 2]
           and all(row["title"].startswith('C%d ' % (row["selected"] + 1)) for row in steps)
           and all("45 kararsız" in row["status"] for row in steps),
           {"before": before_next, "after": steps})
    page.screenshot(str(HERE / "ux-04-next.png"))

    # --- contour ---------------------------------------------------------------------------------
    profiles = sorted(data["options"]["profiles"], key=lambda p: (
        (max(pt[0] for pt in p["points"]) - min(pt[0] for pt in p["points"])) *
        (max(pt[1] for pt in p["points"]) - min(pt[1] for pt in p["points"])),), reverse=True)
    plate = profiles[0]
    point = plate["points"][0]
    page.click_selector("#pick-profile")
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
           {"profile": plate["id"], "edges": len(plate["edges"])})
    page.screenshot(str(HERE / "ux-05-profile.png"))

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
           {"value": calibration["value"], "unit": calibration["unit"], "span_px": round(span_px, 2),
            "px_per_mm": round(span_px / float(calibration["value"]), 4)})
    page.screenshot(str(HERE / "ux-06-calibration.png"))

    # --- thickness + trace acknowledgement -------------------------------------------------------
    page.focus_selector("#thickness")
    page.ev("$('thickness').value = '';")
    page.type_text("15")
    page.click_selector("#apply-thickness")
    saved = wait_server(page, lambda d: d["decisions"].get("thickness") == 15.0, 40, "thickness")
    record("thickness 15 is entered and stored", saved["decisions"].get("thickness") == 15.0, {})
    page.click_selector("#ack")
    saved = wait_server(page, lambda d: d["decisions"].get("trace_acknowledged") is True, 40, "ack")
    record("the traced draft is acknowledged", saved["decisions"].get("trace_acknowledged") is True, {})

    # --- callout: the hole note (composite text: typed by hand) ----------------------------------
    hole_id = callout_by_hint(data, "6,80 THRU ALL")["id"]
    parse = save_text(page, hole_id, HOLE_TEXT)
    record("the hole note transcribes and parses as written", parse["status"] == "parsed",
           {"text": HOLE_TEXT, "semantic": {k: parse.get(k) for k in
            ("form", "size", "count", "termination", "unit")}, "warnings": parse["warnings"]})
    target = save_target_manual(page, hole_id, "circle_group", HOLE_CIRCLES)
    stored = next(row for row in target["decisions"]["callout_targets"] if row["callout_id"] == hole_id)
    record("the four hole circles are confirmed by hand (user_click evidence)",
           sorted(stored["target_ids"]) == sorted(HOLE_CIRCLES)
           and stored["evidence"][0]["kind"] == "user_click" and stored["status"] == "confirmed",
           {"target": stored})
    page.screenshot(str(HERE / "ux-07-hole-targeted.png"))

    # --- the "4 x" fragment: the single-row path still works -------------------------------------
    fragment = callout_by_hint(data, "4 x")["id"]
    ignore_callout(page, fragment)
    record("the “4 x” fragment is declared not-a-callout with the single-row action", True,
           {"callout": fragment})

    # --- callout: the pocket (composite text: typed by hand) ------------------------------------
    pocket_id = callout_by_hint(data, "50,00")["id"]
    parse = save_text(page, pocket_id, POCKET_TEXT)
    record("the pocket transcribes and parses (Ø50 blind, depth 8)",
           parse["status"] == "parsed" and parse.get("termination") == "blind"
           and parse.get("depth") == 8.0 and parse.get("size") == 50.0,
           {"text": POCKET_TEXT, "semantic": {k: parse.get(k) for k in
            ("form", "size", "termination", "depth")}})
    time.sleep(0.6)
    panel = target_panel(page)
    if panel["proposals"]:
        page.click_selector("#target-confirm")
        confirmed = wait_server(page, lambda d: any(
            row["callout_id"] == pocket_id and row.get("status") == "confirmed"
            for row in d["decisions"].get("callout_targets") or []), timeout=60, label="pocket target")
    else:
        confirmed = save_target_manual(page, pocket_id, "circle", [POCKET_CIRCLE])
    stored = next(row for row in confirmed["decisions"]["callout_targets"] if row["callout_id"] == pocket_id)
    record("the pocket circle is confirmed for Ø50", stored["target_ids"] == [POCKET_CIRCLE]
           and stored["evidence"][0]["kind"] in ("proposal", "user_click"),
           {"target": stored, "proposals": panel["proposals"]})
    page.screenshot(str(HERE / "ux-08-pocket-targeted.png"))

    # --- machine hint: single click (M8 note + the three complete printed dimensions) ------------
    m8_id = callout_by_hint(data, M8_HINT)["id"]
    accepted = accept_hint(page, m8_id)
    m8_row = next(row for row in accepted["data"]["decisions"]["transcriptions"]
                  if row["callout_id"] == m8_id)
    m8_log = [row for row in accepted["data"].get("log") or [] if row.get("action") == "transcribe"
              and (row.get("evidence") or {}).get("callout_id") == m8_id]
    record("the hint is written by one click, with no typing: the field was empty before it",
           accepted["before"]["field"] == "" and accepted["before"]["clicks"] == 1
           and m8_row["raw_text"] == M8_HINT and m8_row["entered_by"] == "user"
           and m8_log and m8_log[-1]["evidence"].get("accepted_hint") is True
           and m8_log[-1]["evidence"].get("machine_text_hint") == M8_HINT,
           {"field_before": accepted["before"]["field"], "raw_text": m8_row["raw_text"],
            "log": m8_log[-1] if m8_log else None})
    parse = next(row for row in server(page)["callout_parses"] if row["callout_id"] == m8_id)
    record("the thread note is read and stays outside the grammar (no invented feature)",
           parse["status"] == "unsupported" and "unsupported_syntax" in parse["warnings"],
           {"status": parse["status"], "warnings": parse["warnings"]})
    declare_unbindable(page, m8_id)
    page.screenshot(str(HERE / "ux-09-m8-hint.png"))

    for hint in DIM_SINGLE:
        callout_id = callout_by_hint(data, hint)["id"]
        accepted = accept_hint(page, callout_id)
        row = next(row for row in accepted["data"]["decisions"]["transcriptions"]
                   if row["callout_id"] == callout_id)
        parse = next(row for row in accepted["data"]["callout_parses"] if row["callout_id"] == callout_id)
        record(f"printed dimension {hint!r} is accepted with one click and reads as itself",
               accepted["before"]["field"] == "" and row["raw_text"] == hint
               and parse["status"] == "parsed" and parse.get("form") == "linear",
               {"callout": callout_id, "raw_text": row["raw_text"], "status": parse["status"]})
        declare_unbindable(page, callout_id)
    for hint, text in DIM_TYPED.items():
        callout_id = callout_by_hint(data, hint)["id"]
        parse = save_text(page, callout_id, text)      # spacing corrected by hand: plain typing
        record(f"printed dimension {hint!r} is corrected to {text!r} by hand and parses",
               parse["status"] == "parsed" and parse.get("form") == "linear",
               {"callout": callout_id, "status": parse["status"]})
        declare_unbindable(page, callout_id)
    page.screenshot(str(HERE / "ux-10-dims-unbindable.png"))

    # --- bulk scope decision ---------------------------------------------------------------------
    before_bulk = server(page)
    undecided = undecided_ids(before_bulk)
    reviews_before = len(reviews_of(before_bulk))
    revision_before = before_bulk["revision"]
    page.click_selector("#callout-ignore-many")
    page.wait_ev("$('status').textContent.includes('tekrar tıklayın')", timeout=30, label="bulk armed")
    armed = page.ev("""return {label: $('callout-ignore-many').textContent, status: $('status').textContent};""")
    after_arm = server(page)
    record("the first click only asks for confirmation: nothing is written",
           "Emin misiniz?" in armed["label"] and after_arm["revision"] == revision_before
           and len(reviews_of(after_arm)) == reviews_before,
           {"armed": armed, "revision_same": after_arm["revision"] == revision_before,
            "undecided": len(undecided)})
    page.screenshot(str(HERE / "ux-11-armed.png"))

    page.click_selector("#callout-ignore-many")
    swept = wait_server(page, lambda d: all(
        (reviews_of(d).get(callout_id) or {}).get("ignored") for callout_id in undecided),
        timeout=90, label="bulk ignored")
    page.wait_ev("$('callout-summary').textContent.includes('0 kararsız')", timeout=30, label="summary 0")
    reviews = reviews_of(swept)
    bulk_log = [row for row in swept.get("log") or [] if row.get("action") == "ignore_callout"
                and (row.get("evidence") or {}).get("bulk") is True]
    summary_after = page.ev("return {summary: $('callout-summary').textContent,"
                            " nextDisabled: $('callout-next').disabled,"
                            " manyDisabled: $('callout-ignore-many').disabled,"
                            " label: $('callout-ignore-many').textContent};")
    record("36 undecided candidates are closed in one explicit action: one history step, one revision",
           len(undecided) == 36 and swept["revision"] == revision_before + 1
           and swept["can_undo"] is True
           and all(reviews[callout_id]["revision"] == swept["revision"] for callout_id in undecided)
           and all(reviews[callout_id]["ignored"] for callout_id in undecided),
           {"undecided": len(undecided), "revision_before": revision_before,
            "revision_after": swept["revision"], "can_undo": swept["can_undo"]})
    record("every closed row keeps its own log line, bulk-flagged, all at that same revision",
           len(bulk_log) == 36 and len({row["field"] for row in bulk_log}) == 36
           and {row["revision"] for row in bulk_log} == {swept["revision"]}
           and all("toplu" in (row.get("note") or "") for row in bulk_log),
           {"log_rows": len(bulk_log), "sample": bulk_log[0] if bulk_log else None})
    record("decided rows were not touched: hole, pocket, fragment, M8 and the five dimensions keep their decisions",
           not (reviews.get(hole_id) or {}).get("ignored") and not (reviews.get(pocket_id) or {}).get("ignored")
           and reviews[fragment]["ignored"] is True and reviews[m8_id]["unbindable"] is True
           and all(reviews[callout_by_hint(before_bulk, h)["id"]]["unbindable"] is True
                   for h in (M8_HINT, *DIM_SINGLE, *DIM_TYPED))
           and len(swept["decisions"]["callout_targets"]) == 2,
           {"reviews": {key: {k: row.get(k) for k in ("ignored", "unbindable")}
                        for key, row in list(reviews.items())[:12]}})
    record("the counter follows: 0 undecided and both burden controls go quiet",
           "0 kararsız" in summary_after["summary"] and summary_after["nextDisabled"] is True
           and summary_after["manyDisabled"] is True
           and summary_after["label"].startswith("Kalan kararsızları"),
           summary_after)
    page.screenshot(str(HERE / "ux-12-swept-one-step.png"))

    page.click_selector("#callout-show-ignored")
    page.wait_ev("$('callout-list').textContent.includes('Yok sayıldı')", timeout=30, label="show ignored")
    shown = page.ev("""return {rows: document.querySelectorAll('#callout-list li').length,
      ignored: [...document.querySelectorAll('#callout-list li')].filter(li => li.textContent.includes('Yok sayıldı')).length};""")
    record("with “Yok sayılanları göster” all 45 candidates are still listed, 37 of them ignored",
           shown["rows"] == 45 and shown["ignored"] == 37,
           {"rows": shown["rows"], "ignored": shown["ignored"]})
    page.click_selector("#callout-show-ignored")

    # --- readiness gate + build ------------------------------------------------------------------
    readiness = readiness_of(page)
    probe = checklist_probe(page)
    record("the readiness checklist is clean (one ok line) and the build is enabled",
           readiness["ready"] is True and len(readiness["questions"]) == 0
           and probe["buildDisabled"] is False and len(probe["items"]) == 1
           and probe["items"][0]["text"].startswith("✓"),
           {"summary": probe["summary"], "items": [item["text"] for item in probe["items"]],
            "excluded": len(readiness["excluded"])})
    page.screenshot(str(HERE / "ux-13-ready.png"))

    page.click_selector("#build")
    data = wait_server(page, lambda d: bool(d.get("step")), timeout=420, label="built STEP")
    record("the build runs and the session carries a fresh STEP", data["build_status"] == "complete",
           {"build_status": data["build_status"], "step": data["step"], "error": data.get("error")})
    page.screenshot(str(HERE / "ux-14-built.png"))

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
    compiled = [row for row in bundle.get("callouts", []) if row.get("callout_id") in (hole_id, pocket_id)]
    record("the review bundle carries the compiled chain for both feature callouts",
           len(compiled) >= 1 and all(row.get("confirmed_target") for row in compiled),
           {"compiled": [{k: row.get(k) for k in ("callout_id", "raw_text", "status")} for row in compiled]})

    # --- the burden, measured against G9 ---------------------------------------------------------
    final = server(page)
    typed = [row for row in final.get("log") or [] if row.get("action") in ("transcribe", "edit_transcription")
             and not (row.get("evidence") or {}).get("accepted_hint")]
    hint_logs = [row for row in final.get("log") or []
                 if (row.get("evidence") or {}).get("accepted_hint") is True]
    ignore_logs = [row for row in final.get("log") or [] if row.get("action") == "ignore_callout"]
    single_ignores = [row for row in ignore_logs if (row.get("evidence") or {}).get("bulk") is not True]
    record("the burden numbers, against the G9 run (45 candidates / 43 out of scope)",
           len(typed) == 4 and len(hint_logs) == 4 and len(single_ignores) == 1
           and len(ignore_logs) == 37,
           {"typed_texts": len(typed), "hint_single_clicks": len(hint_logs),
            "single_ignores": len(single_ignores), "bulk_rows": len(ignore_logs) - len(single_ignores),
            "g9": {"typed_texts": 7, "hint_single_clicks": 0, "single_ignores": 37}})

    errors = [entry for entry in page.console if entry["level"] == "error"]
    record("no unexpected console errors and no rejected requests", not errors and not page.failures,
           {"unexpected": errors, "failures": page.failures})

    (HERE / "ux-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "token": final["token"], "steps": G3.STEPS,
         "console": page.console, "rejected_requests": page.failures},
        ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [step for step in G3.STEPS if not step["passed"]]
    print(f"\n{len(G3.STEPS) - len(failed)}/{len(G3.STEPS)} UX round browser steps passed", flush=True)
    page.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
