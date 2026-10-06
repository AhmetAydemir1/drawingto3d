"""G3 real-browser acceptance (PLAN-21 §10.2) — real Chrome, real clicks, real typing.

Runs against the app started with `PYTHONPATH=src .venv/bin/python -m drawingto3d.app`
(http://127.0.0.1:8765) and a Chrome attached at http://127.0.0.1:9222. Every user action is a real
input event (Input.dispatchMouseEvent / Input.insertText); `Runtime.evaluate` only reads the page
back and fetches the server state the UI claims to have written.

    ~/.hermes/cache/scratch/cdp-venv/bin/python browser_acceptance.py

Writes screenshots and `browser-steps.json` next to this file; exits non-zero if any step failed.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cdp_client as C  # noqa: E402

APP = "http://127.0.0.1:8765"
DRAWING = "/Users/aydemir/Desktop/drawingto3d/examples/pdf with steps/5/Plate With A Pocket Drawing.PDF"
HERE = pathlib.Path(__file__).parent
STEPS: list[dict] = []


def record(name: str, passed: bool, detail) -> None:
    STEPS.append({"step": name, "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {json.dumps(detail, ensure_ascii=False)[:400]}",
          flush=True)


def server(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/' + token)).json();""")


def panel(page: C.Chrome) -> dict:
    return page.ev("""return {
      status: $('status').textContent,
      summary: $('callout-summary').textContent,
      rows: [...document.querySelectorAll('#callout-list li')].map(li => li.textContent),
      selected: [...document.querySelectorAll('#callout-list li')].findIndex(li => li.classList.contains('selected')),
      title: $('callout-title').textContent,
      badge: $('callout-state').textContent,
      hint: $('callout-hint-line').textContent,
      draft: $('callout-draft').textContent,
      text: $('callout-text').value,
      detailHidden: $('callout-detail').hidden,
      cropNote: $('callout-crop-note').textContent,
      crop: $('callout-crop').toDataURL().slice(-64),
      fileButtons: [$('pick-profile').disabled, $('pick-calibration').disabled, $('pick-hole').disabled]
    };""")


def boxes(page: C.Chrome, show_ignored: bool = False) -> list[dict]:
    """Screen points for the centre of every listed callout, from the sheet's own transform.

    The image is re-loaded in the page to read its natural size, and the canvas scale/offset mirror
    what `draw()` does (PLAN-21 §7.2). Clicks are then aimed with real mouse events; whether the app
    picks the intended box is asserted separately by the selection/crop comparison.
    """
    flag = "true" if show_ignored else "false"
    return page.ev_async(f"""
      const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const image = new Image(); image.src = data.drawing; await image.decode();
      const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
      const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
      const visible = data.effective_callouts.filter(row => {flag} || !row.ignored);
      return visible.map((row, index) => ({{
        id: row.id, index: index, ignored: row.ignored, source: row.source_kind,
        x: rect.left + ((row.region[0] + (row.region[2] - row.region[0]) / 2) * image.naturalWidth * s) * rect.width / canvas.width,
        y: rect.top + ((row.region[1] + (row.region[3] - row.region[1]) / 2) * image.naturalHeight * s) * rect.height / canvas.height,
        page_y: window.scrollY + rect.top + ((row.region[1] + (row.region[3] - row.region[1]) / 2) * image.naturalHeight * s) * rect.height / canvas.height
      }}));""")


def click_box(page: C.Chrome, callout_id: str, show_ignored: bool = False) -> dict:
    """Scroll the box into the viewport and click its centre with a real mouse event.

    The drawing is taller than the window, so an unscrolled click can land outside the visible area
    and hit nothing; the coordinates are re-read after the scroll because they are viewport-relative.
    """
    target = [box for box in boxes(page, show_ignored) if box["id"] == callout_id]
    if not target:
        raise RuntimeError(f"no listed callout {callout_id}")
    page.ev(f"window.scrollTo(0, Math.max(0, {target[0]['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    again = [box for box in boxes(page, show_ignored) if box["id"] == callout_id][0]
    page.click(again["x"], again["y"])
    return again


PROFILE_POINT = """const token = new URLSearchParams(location.search).get('session');
  const data = await (await fetch('/api/guided/' + token)).json();
  const image = new Image(); image.src = data.drawing; await image.decode();
  const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
  const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const point = data.options.profiles[0].points[0];
  const y = rect.top + point[1] * s * rect.height / canvas.height;
  return {id: data.options.profiles[0].id,
          x: rect.left + point[0] * s * rect.width / canvas.width,
          y: y, page_y: window.scrollY + y};"""


def contour_point(page: C.Chrome) -> dict:
    """A contour vertex the profile tool must hit, scrolled into view first."""
    found = page.ev_async(PROFILE_POINT)
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    return page.ev_async(PROFILE_POINT)


def drag_points(page: C.Chrome, fx0: float, fy0: float, fx1: float, fy1: float):
    """Two viewport points on the sheet canvas, scrolled so the drag area is actually visible."""
    box = page.box("#sheet")
    middle = box["y"] + box["h"] * (fy0 + fy1) / 2
    page.ev(f"window.scrollTo(0, Math.max(0, {middle} - window.innerHeight / 2));")
    time.sleep(0.3)
    box = page.box("#sheet")
    return ((box["x"] + box["w"] * fx0, box["y"] + box["h"] * fy0),
            (box["x"] + box["w"] * fx1, box["y"] + box["h"] * fy1))


def main() -> int:
    page = C.Chrome("about:blank", 1400, 900)
    page.navigate(APP + "/guided")
    page.screenshot(str(HERE / "00-start.png"))
    record("page serves the callout panel", page.ev("return !!$('callout-new') && !!$('callout-text');"),
           panel(page)["summary"])

    # --- scenario 1: real vector drawing -> box -> crop -> text -> save -> reload -> undo ----------
    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=240, label="session opened")
    page.wait_ev("$('callout-summary').textContent.length > 0", timeout=60, label="callout summary")
    page.screenshot(str(HERE / "01-loaded.png"))
    summary = panel(page)["summary"]
    record("detected callout candidates are listed", "etkin alan" in summary, summary)

    try:
        page.click_selector("#pick-callout")
    except Exception as error:  # a null here means the probe ran against a stale context
        dump = page.ev("""return {url: location.href, ready: document.readyState,
          ids: document.querySelectorAll('[id]').length, controls: !!$('controls'),
          text: !!$('callout-text'), fresh: !!$('callout-new'), body: document.body ? document.body.innerHTML.length : -1};""")
        print("DIAGNOSTIC", json.dumps(dump, ensure_ascii=False), type(error).__name__, flush=True)
        raise
    first = boxes(page)[0]
    click_box(page, first["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="selection")
    selected = panel(page)
    record("clicking a box selects it and crops the drawing",
           selected["detailHidden"] is False and selected["selected"] == first["index"] and "Kırpma" in selected["cropNote"],
           {"selected_row": selected["selected"], "expected": first["index"], "title": selected["title"],
            "badge": selected["badge"], "hint": selected["hint"], "crop": selected["crop"]})
    page.screenshot(str(HERE / "02-selected.png"))
    record("the hint is offered separately and the field is still empty",
           selected["text"] == "" and (selected["hint"].startswith("Makine ipucu") or
                                       selected["hint"].startswith("Makine ipucu yok")),
           {"hint": selected["hint"], "text": selected["text"]})

    page.focus_selector("#callout-text")
    page.type_text("  4 × Ø8 THRU  ")
    page.click_selector("#callout-save")
    page.wait_ev("$('status').textContent.includes('Metin kaydedildi')", timeout=30, label="saved")
    saved = panel(page)
    rows = server(page)["decisions"]["transcriptions"]
    record("saved text is kept exactly as typed, spaces included",
           saved["text"] == "  4 × Ø8 THRU  " and rows[0]["raw_text"] == "  4 × Ø8 THRU  " and
           rows[0]["normalized_text"].strip() == "4 × Ø8 THRU",
           {"panel": saved["text"], "raw": rows[0]["raw_text"], "normalized": rows[0]["normalized_text"]})
    record("the panel calls it saved, not parsed", saved["badge"] == "Metin kaydedildi" and
           "ayrıştır" not in saved["status"], {"badge": saved["badge"], "status": saved["status"]})
    page.screenshot(str(HERE / "03-saved.png"))
    region_then = rows[0]["source_region"]

    token = page.ev("return new URLSearchParams(location.search).get('session');")
    page.navigate(f"{APP}/guided?session={token}")
    page.wait_ev("!$('controls').hidden", timeout=240, label="reopen")
    page.click_selector("#pick-callout")
    click_box(page, boxes(page)[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="reopen selection")
    reopened = panel(page)
    record("after a real reload the same session shows the same text",
           reopened["text"] == "  4 × Ø8 THRU  " and reopened["badge"] == "Metin kaydedildi",
           {"text": reopened["text"], "badge": reopened["badge"], "selected": reopened["selected"]})
    page.screenshot(str(HERE / "04-reopened.png"))

    before_undo = server(page)
    page.click_selector("#undo")
    page.wait_ev("$('status').textContent.includes('geri alındı')", timeout=30, label="undo")
    after_undo = server(page)
    record("undo removes the transcription and leaves the detected candidates untouched",
           bool(before_undo["decisions"]["transcriptions"]) and
           not after_undo["decisions"]["transcriptions"] and
           after_undo["callout_candidates"] == before_undo["callout_candidates"],
           {"before": len(before_undo["decisions"]["transcriptions"]),
            "after": len(after_undo["decisions"]["transcriptions"]),
            "candidates": len(after_undo["callout_candidates"])})
    page.click_selector("#pick-callout")
    click_box(page, boxes(page)[0]["id"])
    page.focus_selector("#callout-text")
    page.type_text("4 × Ø8 THRU")
    page.click_selector("#callout-save")
    page.wait_ev("$('status').textContent.includes('Metin kaydedildi')", timeout=30, label="re-saved")
    record("re-saving after undo writes the text again (region unchanged)",
           server(page)["decisions"]["transcriptions"][0]["source_region"] == region_then,
           server(page)["decisions"]["transcriptions"][0])

    # --- scenario 2: ignore -> show ignored -> restore --------------------------------------------
    page.click_selector("#callout-ignore")
    page.wait_ev("$('status').textContent.includes('Karar kaydedildi')", timeout=30, label="ignored")
    ignored = panel(page)
    record("ignoring hides the box from the default list and counts it",
           "yok sayıldı" in ignored["summary"] and ignored["detailHidden"] is True,
           {"summary": ignored["summary"], "rows": ignored["rows"]})
    page.screenshot(str(HERE / "05-ignored.png"))

    page.click_selector("#callout-show-ignored")
    page.wait_ev("$('callout-list').textContent.includes('Yok sayıldı')", timeout=30, label="show ignored")
    shown = panel(page)
    record("“Yok sayılanları göster” brings the ignored box back with its text",
           any("Yok sayıldı" in row for row in shown["rows"]),
           {"rows": shown["rows"], "summary": shown["summary"]})
    page.screenshot(str(HERE / "06-ignored-shown.png"))

    hidden_box = [box for box in boxes(page, show_ignored=True) if box["ignored"]][0]
    click_box(page, hidden_box["id"], show_ignored=True)
    page.wait_ev("!$('callout-restore').hidden", timeout=30, label="restore button")
    page.click_selector("#callout-restore")
    page.wait_ev("$('status').textContent.includes('Karar kaydedildi')", timeout=30, label="restored")
    restored = server(page)
    record("restore clears the ignore decision and keeps the text",
           not restored["decisions"]["callout_reviews"] and restored["decisions"]["transcriptions"],
           {"reviews": restored["decisions"]["callout_reviews"],
            "text": restored["decisions"]["transcriptions"][0]["raw_text"]})
    page.screenshot(str(HERE / "07-restored.png"))

    # --- scenario 3: draw a manual region with the mouse ------------------------------------------
    page.click_selector("#callout-new")
    start, end = drag_points(page, 0.60, 0.50, 0.76, 0.66)   # after the click: it scrolls the page
    page.drag(start, end)
    page.wait_ev("$('status').textContent.includes('Yeni alan kaydedildi')", timeout=30, label="manual add")
    manual = server(page)
    manual_rows = manual["decisions"]["manual_callouts"]
    drawn = manual_rows[0]["region"] if manual_rows else []
    expected = [0.60, 0.50, 0.76, 0.66]
    record("a drawn region becomes a manual callout with a server-assigned id and the drawn box",
           len(manual_rows) == 1 and manual_rows[0]["id"].startswith("manual:") and
           manual_rows[0]["page_index"] == 0 and isinstance(manual_rows[0]["revision"], int) and
           all(abs(value - want) < 0.05 for value, want in zip(drawn, expected)),
           {"row": manual_rows, "expected_region": expected})
    manual_panel = panel(page)
    record("the new region is selected, crops the drawing and has no machine hint",
           "elle çizilen alan" in manual_panel["title"] and manual_panel["badge"] == "İncelenmedi" and
           (manual_panel["hint"].startswith("Makine ipucu yok") or manual_panel["hint"].startswith("Makine ipucu")),
           {"title": manual_panel["title"], "badge": manual_panel["badge"], "hint": manual_panel["hint"]})
    page.screenshot(str(HERE / "08-manual-region.png"))

    page.focus_selector("#callout-text")
    page.type_text("KAYNAK: elle çizilen alan")
    page.click_selector("#callout-save")
    page.wait_ev("$('status').textContent.includes('Metin kaydedildi')", timeout=30, label="manual text saved")
    manual_after = server(page)
    record("the manual callout keeps its id and takes the user's text",
           [row["id"] for row in manual_after["decisions"]["manual_callouts"]] ==
           [row["id"] for row in manual_rows] and
           any(row["callout_id"] == manual_rows[0]["id"] for row in manual_after["decisions"]["transcriptions"]),
           manual_after["decisions"]["transcriptions"])

    # --- scenario 4: move the detected region; the old text must go stale, never be rewritten -----
    picked = page.ev("""const rows = [...document.querySelectorAll('#callout-list li')];
      const index = rows.findIndex(li => li.textContent.includes('makine adayı'));
      rows[index].click(); return index;""")
    page.wait_ev("$('callout-state').textContent === 'Metin kaydedildi'", timeout=30, label="detected selected")
    before = [row for row in server(page)["decisions"]["transcriptions"] if row["callout_id"] != manual_rows[0]["id"]][0]
    page.click_selector("#callout-edit")
    page.drag(*drag_points(page, 0.60, 0.50, 0.76, 0.66))
    page.wait_ev("$('status').textContent.includes('Alan düzeltmesi kaydedildi')", timeout=30, label="region edit")
    edited = server(page)
    after = [row for row in edited["decisions"]["transcriptions"] if row["callout_id"] == before["callout_id"]][0]
    record("moving the region keeps the old raw text and its snapshot untouched",
           after["raw_text"] == before["raw_text"] and after["source_region"] == before["source_region"] and
           after["revision"] == before["revision"],
           {"before": before, "after": after})
    badge = panel(page)["badge"]
    record("the panel reports the region change instead of pretending it is current",
           badge in ("Alan değişti", "Metin eskidi"), badge)
    page.screenshot(str(HERE / "09-region-changed.png"))

    # --- scenario 5: narrow and wide layouts stay on the same source region ------------------------
    page.resize(520, 900)
    time.sleep(0.8)
    narrow = boxes(page)
    click_box(page, narrow[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="narrow selection")
    narrow_panel = panel(page)
    page.screenshot(str(HERE / "10-narrow.png"))
    page.resize(1400, 900)
    time.sleep(0.8)
    wide = boxes(page)
    click_box(page, wide[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="wide selection")
    wide_panel = panel(page)
    record("the same box is hit and cropped in a narrow and a wide window",
           narrow_panel["selected"] == narrow[0]["index"] == wide[0]["index"] == wide_panel["selected"] and
           narrow_panel["crop"] == wide_panel["crop"] and narrow_panel["title"] == wide_panel["title"],
           {"narrow_row": narrow_panel["selected"], "wide_row": wide_panel["selected"],
            "expected": narrow[0]["index"], "crop_equal": narrow_panel["crop"] == wide_panel["crop"],
            "title": wide_panel["title"]})
    page.screenshot(str(HERE / "11-wide-again.png"))

    # --- scenario 6: a revision conflict must not silently win, and must keep the draft -----------
    behind = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      const current = await (await fetch('/api/guided/' + token)).json();
      const response = await fetch('/api/guided/callout', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({token, revision: current.revision, action:'set_ignored',
                              payload:{callout_id: current.effective_callouts.at(-1).id, ignored:true}})});
      return [response.status, response.ok];""")
    record("the server accepts a command the page did not send (it is now stale)…", behind[1] is True, behind)
    draft = "  yarım kalan taslak  "
    selected_id = boxes(page)[0]["id"]
    stored_before = [row for row in server(page)["decisions"]["transcriptions"]
                     if row["callout_id"] == selected_id][0]["raw_text"]
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")     # the draft replaces the field, it is not appended
    page.type_text(draft)
    page.click_selector("#callout-save")
    page.wait_ev("$('status').classList.contains('error')", timeout=60, label="conflict surfaced")
    conflict = panel(page)
    record("the conflict is shown and the typed draft survives",
           "oturum değişti" in conflict["status"] and conflict["text"] == draft and conflict["draft"] != "" and
           [row for row in server(page)["decisions"]["transcriptions"]
            if row["callout_id"] == selected_id][0]["raw_text"] == stored_before,
           {"status": conflict["status"], "text": conflict["text"], "draft_note": conflict["draft"],
            "server_still": stored_before})
    page.screenshot(str(HERE / "12-conflict.png"))
    page.click_selector("#callout-save")
    page.wait_ev("$('status').textContent.includes('Metin kaydedildi')", timeout=60, label="re-save")
    saved_draft = [row for row in server(page)["decisions"]["transcriptions"]
                   if row["callout_id"] == selected_id][0]
    record("after the refresh the same draft saves as a conscious decision",
           saved_draft["raw_text"] == draft, saved_draft)

    # --- scenario 7: the older tools still work; markup stays text; no console errors --------------
    profile_point = contour_point(page)
    page.click_selector("#pick-profile")
    page.click(profile_point["x"], profile_point["y"])
    page.wait_ev("$('profile').value !== ''", timeout=30, label="profile chosen")
    record("the profile tool still selects a contour (and the callout overlay is not in the way)",
           page.ev("return $('profile').value;") == profile_point["id"],
           {"profile": page.ev("return $('profile').value;"), "expected": profile_point["id"]})

    page.click_selector("#pick-callout")
    click_box(page, boxes(page)[0]["id"])
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').value = '';")
    markup = "<img src=x onerror=alert(1)>"
    page.type_text(markup)
    page.click_selector("#callout-save")
    page.wait_ev("$('status').textContent.includes('Metin kaydedildi')", timeout=30, label="markup saved")
    injected = page.ev("""return {imgs: document.querySelectorAll('#callout-detail img').length,
      value: $('callout-text').value,
      raw: document.body.innerHTML.includes('<img src=x'),};""")
    record("markup-like text is stored and shown as text", injected["imgs"] == 0 and
           injected["value"] == markup and injected["raw"] is False, injected)
    page.screenshot(str(HERE / "13-markup-text.png"))
    page.click_selector("#undo")
    page.wait_ev("$('status').textContent.includes('geri alındı')", timeout=30, label="undo markup")

    # --- scenario 8: zero-area, cancelled and reversed drags (U13) --------------------------------
    page.click_selector("#pick-callout")
    page.click_selector("#callout-new")
    drawn = len(server(page)["decisions"]["manual_callouts"])

    tiny = drag_points(page, 0.30, 0.30, 0.30, 0.30)
    page.drag(*tiny)
    page.wait_ev("$('status').classList.contains('error')", timeout=30, label="tiny region refused")
    tiny_status = page.ev("return $('status').textContent;")
    record("a zero-area drag is refused and writes nothing",
           len(server(page)["decisions"]["manual_callouts"]) == drawn and "küçük" in tiny_status,
           {"manual_rows": len(server(page)["decisions"]["manual_callouts"]), "status": tiny_status})

    page.click_selector("#callout-new")
    partial = drag_points(page, 0.32, 0.32, 0.46, 0.44)
    page.drag_start(partial[0])
    page.drag_move(partial[1])
    page.press("Escape", "Escape", 27)
    page.wait_ev("$('status').textContent.includes('iptal')", timeout=30, label="drag cancelled")
    cancelled_status = page.ev("return $('status').textContent;")
    page.drag_end(partial[1])                      # the release must not create anything either
    time.sleep(0.5)
    record("a drag cancelled with Escape leaves no decision behind",
           len(server(page)["decisions"]["manual_callouts"]) == drawn,
           {"manual_rows": len(server(page)["decisions"]["manual_callouts"]),
            "status_at_cancel": cancelled_status,
            "status_after_release": page.ev("return $('status').textContent;")})
    page.screenshot(str(HERE / "14-cancelled-drag.png"))

    page.click_selector("#callout-new")
    reversed_drag = drag_points(page, 0.80, 0.80, 0.62, 0.60)   # bottom-right to top-left
    page.drag(*reversed_drag)
    page.wait_ev("$('status').textContent.includes('Yeni alan kaydedildi')", timeout=30,
                 label="reversed add")
    newest = server(page)["decisions"]["manual_callouts"][-1]
    want = [0.62, 0.60, 0.80, 0.80]
    record("a drag drawn bottom-right to top-left is stored as a normalized region",
           bool(newest["region"][0] < newest["region"][2] and newest["region"][1] < newest["region"][3] and
                all(abs(value - target) < 0.05 for value, target in zip(newest["region"], want))),
           {"region": newest["region"], "expected": want})

    errors = [entry for entry in page.console if entry["level"] == "error"]
    # The revision conflict is created on purpose above: the browser logs the rejected request as a
    # failed resource. Anything else — a JS exception, a missing file — is a real finding.
    expected = [entry for entry in errors if "400" in entry["text"]]
    unexpected = [entry for entry in errors if "400" not in entry["text"]]
    record("no console error except the deliberately rejected revision conflict",
           bool(not unexpected and expected and
                all("/api/guided/" in entry["url"] for entry in expected)),
           {"unexpected": unexpected, "expected": expected, "rejected_requests": page.failures})
    record("the only rejected request is the stale save the UI was told to retry",
           bool(page.failures) and all(item["status"] == 400 and "POST" in item["request"]
                                        and "/api/guided/callout" in item["url"]
                                        for item in page.failures),
           page.failures)

    (HERE / "browser-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "steps": STEPS, "console": page.console,
         "rejected_requests": page.failures},
        ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [step for step in STEPS if not step["passed"]]
    print(f"\n{len(STEPS) - len(failed)}/{len(STEPS)} browser steps passed")
    page.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
