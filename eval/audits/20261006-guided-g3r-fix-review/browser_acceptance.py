"""G3R fix-round real-browser acceptance (PLAN-22 §9.2) — real Chrome, real clicks, real typing.

Six scenarios: (1) the review flow after the fix round — select, crop, save text, real reload; (2) a
manual region, a region move and an explicit re-save of the same text; (3) ignore → show ignored →
restore → undo, then a thickness edit through the *old* full-save path; (4) an unsaved draft against a
real revision conflict; (5) the three detection-notice cases (normal empty / refused detection /
metadata-less old record) and their no-write guarantee; (6) narrow/wide selection plus the older
profile tool.

Runs against the app started with `PYTHONPATH=src .venv/bin/python -m drawingto3d.app`
(http://127.0.0.1:8765) and a Chrome attached at http://127.0.0.1:9222. Every user action is a real
input event (Input.dispatchMouseEvent / Input.insertText); `Runtime.evaluate` only reads the page back
and fetches the server state the UI claims to have written.

    PYTHONPATH=src:$HOME/.hermes/cache/scratch/cdp-venv/lib/python3.12/site-packages \
        .venv/bin/python eval/audits/20261006-guided-g3r-fix-review/browser_acceptance.py

Both halves are needed: `drawingto3d.guided` imports numpy (only in `.venv`), while the CDP client's
transport (websockets) only lives in the cdp venv; running the cdp venv's own python fails with
`ModuleNotFoundError: No module named 'numpy'`. `cdp_client.py` is found through the G3 audit
directory inserted into `sys.path` below.

Writes screenshots and `browser-steps.json` next to this file; exits non-zero if any step failed.
Scenario 5's two refused/legacy sessions are explicit fixtures: they are created through the real
store and then edited on disk (the detector itself cannot be asked to fail on demand) — the evidence
labels them as such, and the normal-empty case (a real text-less PNG) is *not* a fixture.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "eval/audits/20261006-guided-g3-review"))   # cdp_client lives with the G3 round
import cdp_client as C  # noqa: E402

APP = "http://127.0.0.1:8765"
DRAWING = str(REPO / "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
NO_TEXT = "/Users/aydemir/.hermes/cache/scratch/no-text-sheet.png"
SESSIONS = REPO / "out" / "guided"
STEPS: list[dict] = []


def record(name: str, passed: bool, detail) -> None:
    STEPS.append({"step": name, "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {json.dumps(detail, ensure_ascii=False)[:400]}",
          flush=True)


def server(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/' + token)).json();""")


def wait_until(page: C.Chrome, check, label: str, timeout: float = 90.0) -> bool:
    """Wait for the effect the *server* reports.

    The status line is a log of the last act, not a promise about this one: waiting on its text right
    after a similar act can pass before the new request has even been sent. Every save below is
    therefore awaited on the stored state, and the panel text is asserted afterwards.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check():
            return True
        time.sleep(0.4)
    raise TimeoutError(f"condition never held: {label}")


def transcriptions(page: C.Chrome) -> list[dict]:
    return server(page)["decisions"]["transcriptions"]


def visible_ids(page: C.Chrome) -> list[str]:
    """The visible list's identities, in the page's own order (labels C1… are visible positions).

    With “Yok sayılanları göster” off the page renders exactly `effective_callouts` without the
    ignored rows, so a list position maps back to an identity through this filtered view — the one
    bridge that does not depend on labels the page invents for display.
    """
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      return data.effective_callouts.filter(row => !row.ignored).map(row => row.id);""")


def wait_transcription(page: C.Chrome, callout_id: str, raw_text: str, label: str) -> None:
    wait_until(page, lambda: any(row["callout_id"] == callout_id and row["raw_text"] == raw_text
                                 for row in transcriptions(page)), label)


def panel(page: C.Chrome) -> dict:
    return page.ev("""return {
      status: $('status').textContent,
      statusError: $('status').classList.contains('error'),
      summary: $('callout-summary').textContent,
      detection: $('callout-detection').textContent,
      rows: [...document.querySelectorAll('#callout-list li')].map(li => li.textContent),
      selected: [...document.querySelectorAll('#callout-list li')].findIndex(li => li.classList.contains('selected')),
      title: $('callout-title').textContent,
      badge: $('callout-state').textContent,
      hint: $('callout-hint-line').textContent,
      draft: $('callout-draft').textContent,
      text: $('callout-text').value,
      detailHidden: $('callout-detail').hidden,
      cropNote: $('callout-crop-note').textContent,
      crop: $('callout-crop').toDataURL().slice(-64)};""")


def boxes(page: C.Chrome, show_ignored: bool = False) -> list[dict]:
    """Screen points for the centre of every listed callout, from the sheet's own transform."""
    flag = "true" if show_ignored else "false"
    return page.ev_async(f"""
      const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const image = new Image(); image.src = data.drawing; await image.decode();
      const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
      const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
      const visible = data.effective_callouts.filter(row => {flag} || !row.ignored);
      return visible.map((row, index) => ({{
        id: row.id, index: index, ignored: row.ignored, source: row.source_kind, label: row.label,
        x: rect.left + ((row.region[0] + (row.region[2] - row.region[0]) / 2) * image.naturalWidth * s) * rect.width / canvas.width,
        y: rect.top + ((row.region[1] + (row.region[3] - row.region[1]) / 2) * image.naturalHeight * s) * rect.height / canvas.height,
        page_y: window.scrollY + rect.top + ((row.region[1] + (row.region[3] - row.region[1]) / 2) * image.naturalHeight * s) * rect.height / canvas.height
      }}));""")


def click_box(page: C.Chrome, callout_id: str, show_ignored: bool = False) -> dict:
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


def make_fixture_session(image: pathlib.Path, mutate) -> tuple[str, pathlib.Path]:
    """A real store session through the running app's own open endpoint, then an explicit on-disk edit.

    The detector cannot be asked to fail on demand, so the refused/legacy cases are fixtures by
    necessity: the session, its drawing and its public API are the real thing (the app created them
    from the real bytes); only the stored detection result is edited, and the caller labels which case
    was edited. The text-less drawing in the normal-empty case is *not* edited at all.
    """
    request = urllib.request.Request(APP + "/api/guided/open", data=image.read_bytes(), method="POST")
    with urllib.request.urlopen(request) as response:
        state = json.load(response)
    token = state["token"]
    path = SESSIONS / token / "session.json"
    record_file = json.loads(path.read_text(encoding="utf-8"))
    mutate(record_file)
    path.write_text(json.dumps(record_file, ensure_ascii=False, indent=2), encoding="utf-8")
    return token, path


def open_in_page(page: C.Chrome, token: str) -> None:
    page.navigate(f"{APP}/guided?session={token}")
    page.wait_ev("!$('controls').hidden", timeout=240, label=f"session {token} opened")
    page.wait_ev("$('callout-summary').textContent.length > 0", timeout=60, label="callout panel filled")


def main() -> int:
    page = C.Chrome("about:blank", 1400, 900)

    # --- the main session: a real vector drawing -----------------------------------------------
    page.navigate(APP + "/guided")
    page.screenshot(str(HERE / "g3r-00-start.png"))
    record("the page serves the callout panel with its detection line",
           page.ev("return !!$('callout-new') && !!$('callout-text') && !!$('callout-detection');"),
           {"detection": panel(page)["detection"]})
    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=240, label="session opened")
    page.wait_ev("$('callout-summary').textContent.length > 0", timeout=60, label="callout summary")
    page.screenshot(str(HERE / "g3r-01-loaded.png"))
    loaded = panel(page)
    record("scenario 1: detected callout candidates are listed and treated as current information",
           "etkin alan" in loaded["summary"] and loaded["detection"] == "", loaded["summary"])

    # --- scenario 1: select -> crop -> text -> save -> real reload ------------------------------
    page.click_selector("#pick-callout")
    first = boxes(page)[0]
    click_box(page, first["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="selection")
    selected = panel(page)
    record("scenario 1: clicking a box selects it and crops the drawing",
           selected["detailHidden"] is False and selected["selected"] == first["index"] and
           "Kırpma" in selected["cropNote"],
           {"selected_row": selected["selected"], "expected": first["index"], "badge": selected["badge"],
            "crop": selected["crop"]})
    page.screenshot(str(HERE / "g3r-02-selected.png"))
    record("scenario 1: the machine hint is offered separately and the field is still empty",
           selected["text"] == "" and (selected["hint"].startswith("Makine ipucu") or
                                       selected["hint"].startswith("Makine ipucu yok")),
           {"hint": selected["hint"], "text": selected["text"]})

    page.focus_selector("#callout-text")
    page.type_text("  4 × Ø8 THRU  ")
    page.click_selector("#callout-save")
    wait_transcription(page, first["id"], "  4 × Ø8 THRU  ", "saved text")
    saved = panel(page)
    rows = server(page)["decisions"]["transcriptions"]
    record("scenario 1: the saved text is kept exactly as typed, spaces included",
           saved["text"] == "  4 × Ø8 THRU  " and rows[0]["raw_text"] == "  4 × Ø8 THRU  " and
           rows[0]["normalized_text"].strip() == "4 × Ø8 THRU",
           {"panel": saved["text"], "raw": rows[0]["raw_text"], "normalized": rows[0]["normalized_text"]})
    record("scenario 1: the panel calls it saved, not parsed, and no parse is fabricated",
           saved["badge"] == "Metin kaydedildi" and "ayrıştır" not in saved["status"] and
           server(page)["callout_parses"] == [],
           {"badge": saved["badge"], "status": saved["status"],
            "parses": server(page)["callout_parses"]})
    page.screenshot(str(HERE / "g3r-03-saved.png"))
    token = page.ev("return new URLSearchParams(location.search).get('session');")
    page.navigate(f"{APP}/guided?session={token}")
    page.wait_ev("!$('controls').hidden", timeout=240, label="reopen")
    page.click_selector("#pick-callout")
    click_box(page, boxes(page)[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="reopen selection")
    reopened = panel(page)
    record("scenario 1: after a real reload the same session shows the same text",
           reopened["text"] == "  4 × Ø8 THRU  " and reopened["badge"] == "Metin kaydedildi",
           {"text": reopened["text"], "badge": reopened["badge"], "selected": reopened["selected"]})
    page.screenshot(str(HERE / "g3r-04-reopened.png"))

    # --- scenario 2: manual region -> text -> move region -> explicit re-save --------------------
    page.click_selector("#callout-new")
    start, end = drag_points(page, 0.60, 0.50, 0.76, 0.66)
    page.drag(start, end)
    wait_until(page, lambda: len(server(page)["decisions"]["manual_callouts"]) == 1, "manual add")
    manual_rows = server(page)["decisions"]["manual_callouts"]
    manual = manual_rows[0]
    record("scenario 2: a drawn region becomes a manual callout with a server-set identity",
           len(manual_rows) == 1 and manual["id"].startswith("manual:") and manual["page_index"] == 0 and
           all(abs(value - want) < 0.05 for value, want in zip(manual["region"], [0.60, 0.50, 0.76, 0.66])),
           {"row": manual})
    page.focus_selector("#callout-text")
    page.type_text("KAYNAK: elle çizilen alan")
    page.click_selector("#callout-save")
    wait_transcription(page, manual["id"], "KAYNAK: elle çizilen alan", "manual text")
    written = [row for row in server(page)["decisions"]["transcriptions"]
               if row["callout_id"] == manual["id"]][0]
    record("scenario 2: the manual callout takes the user's text with the drawn region as its source",
           written["raw_text"] == "KAYNAK: elle çizilen alan" and
           all(abs(value - want) < 0.05 for value, want in zip(written["source_region"], [0.60, 0.50, 0.76, 0.66])),
           written)
    page.screenshot(str(HERE / "g3r-05-manual.png"))

    page.click_selector("#callout-edit")
    page.drag(*drag_points(page, 0.62, 0.52, 0.72, 0.62))
    wait_until(page, lambda: any(row["callout_id"] == manual["id"] and
                                 abs((row.get("region_override") or [0])[0] - 0.62) < 0.02
                                 for row in server(page)["decisions"]["callout_reviews"]), "region edit")
    after_move = panel(page)
    moved_rows = server(page)["decisions"]
    moved = [row for row in moved_rows["transcriptions"] if row["callout_id"] == manual["id"]][0]
    record("scenario 2: moving the region does not rewrite the stored text (it goes stale, visibly)",
           after_move["badge"] == "Alan değişti" and moved["raw_text"] == written["raw_text"] and
           moved["source_region"] == written["source_region"] and
           bool(moved_rows["callout_reviews"]) and
           all(abs(value - want) < 0.05 for value, want in
               zip(moved_rows["callout_reviews"][0]["region_override"], [0.62, 0.52, 0.72, 0.62])),
           {"badge": after_move["badge"], "text": moved["raw_text"], "review": moved_rows["callout_reviews"][0]})
    page.screenshot(str(HERE / "g3r-06-region-changed.png"))

    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")
    page.type_text("KAYNAK: elle çizilen alan")
    page.click_selector("#callout-save")
    wait_until(page, lambda: any(row["callout_id"] == manual["id"] and
                                 row["revision"] > written["revision"] and
                                 row["source_region"][0] > 0.61
                                 for row in transcriptions(page)), "re-save after the move")
    re_saved = [row for row in server(page)["decisions"]["transcriptions"]
                if row["callout_id"] == manual["id"]][0]
    record("scenario 2: explicitly re-saving binds the text to the moved region and calls it current",
           re_saved["raw_text"] == "KAYNAK: elle çizilen alan" and
           all(abs(value - want) < 0.05 for value, want in zip(re_saved["source_region"], [0.62, 0.52, 0.72, 0.62])) and
           re_saved["revision"] > written["revision"] and server(page)["callout_parses"] == [],
           {"row": re_saved, "parses": server(page)["callout_parses"]})

    # --- scenario 3: ignore -> show -> restore -> undo, then the old full-save path --------------
    machine = page.ev("""const rows = [...document.querySelectorAll('#callout-list li')];
      const index = rows.findIndex(li => li.textContent.includes('makine adayı'));
      rows[index].click(); return index;""")
    page.wait_ev("!$('callout-detail').hidden && $('callout-state').textContent.length > 0", timeout=30,
                 label="machine row selected")
    # Labels (C1…) are the page's own display names, so the row's list position is the bridge back to
    # the identity the server knows; the visible list and `effective_callouts` share that order.
    selected_id = page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      return data.effective_callouts[{machine}].id;""")
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")     # the field already holds this box's stored text
    page.type_text("Ø8 THRU")
    page.click_selector("#callout-save")
    wait_transcription(page, selected_id, "Ø8 THRU", "machine text")
    record("scenario 3: a text is written on the detected box before the ignore cycle",
           any(row["callout_id"] == selected_id and row["raw_text"] == "Ø8 THRU"
               for row in transcriptions(page)),
           {"callout_id": selected_id, "row": machine, "transcriptions": len(transcriptions(page))})

    page.click_selector("#callout-ignore")
    wait_until(page, lambda: any(row["callout_id"] == selected_id and row["ignored"]
                                 for row in server(page)["decisions"]["callout_reviews"]), "ignored")
    ignored = panel(page)
    record("scenario 3: ignoring hides the box from the default list, counts it and keeps the text",
           "yok sayıldı" in ignored["summary"] and ignored["detailHidden"] is True and
           any(row["callout_id"] == selected_id for row in server(page)["decisions"]["transcriptions"]),
           {"summary": ignored["summary"], "rows": ignored["rows"]})
    page.screenshot(str(HERE / "g3r-07-ignored.png"))

    page.click_selector("#callout-show-ignored")
    page.wait_ev("$('callout-list').textContent.includes('Yok sayıldı')", timeout=30, label="show ignored")
    shown = panel(page)
    record("scenario 3: “Yok sayılanları göster” brings the ignored box back",
           any("Yok sayıldı" in row for row in shown["rows"]), {"rows": shown["rows"]})
    hidden_box = [box for box in boxes(page, show_ignored=True) if box["ignored"]][0]
    page.ev("""const rows = [...document.querySelectorAll('#callout-list li')];
      const index = rows.findIndex(li => li.textContent.includes('Yok sayıldı'));
      rows[index].click();""")             # the list selects by identity; the canvas hit-test may land on a smaller box
    page.wait_ev("!$('callout-restore').hidden", timeout=30, label="restore button")
    page.click_selector("#callout-restore")
    wait_until(page, lambda: not any(row["callout_id"] == selected_id
                                     for row in server(page)["decisions"]["callout_reviews"]), "restored")
    restored = server(page)
    record("scenario 3: restore clears the ignore decision and keeps the text",
           not any(row["callout_id"] == selected_id for row in restored["decisions"]["callout_reviews"]) and
           any(row["callout_id"] == selected_id and row["raw_text"] == "Ø8 THRU"
               for row in restored["decisions"]["transcriptions"]),
           {"reviews": restored["decisions"]["callout_reviews"], "box": hidden_box})

    before_undo = server(page)
    page.click_selector("#undo")
    wait_until(page, lambda: server(page)["decisions"] != before_undo["decisions"], "undo")
    after_undo = server(page)
    record("scenario 3: undo steps back one decision and leaves the candidates untouched",
           after_undo["callout_candidates"] == before_undo["callout_candidates"] and
           after_undo["decisions"] != before_undo["decisions"],
           {"candidates": len(after_undo["callout_candidates"])})
    page.screenshot(str(HERE / "g3r-08-restored.png"))

    decisions_before = server(page)["decisions"]
    page.focus_selector("#thickness")
    page.ev("$('thickness').select();")
    page.type_text("6")
    page.click_selector("#apply-thickness")
    wait_until(page, lambda: server(page)["decisions"].get("thickness") == 6.0, "thickness saved")
    decisions_after = server(page)["decisions"]
    callout_before = {key: decisions_before.get(key) for key in ("manual_callouts", "callout_reviews",
                                                                 "transcriptions", "callout_targets")}
    callout_after = {key: decisions_after.get(key) for key in ("manual_callouts", "callout_reviews",
                                                               "transcriptions", "callout_targets")}
    record("scenario 3: a thickness edit through the old full-save path leaves every G3 decision identical",
           decisions_after["thickness"] == 6.0 and callout_after == callout_before,
           {"thickness": decisions_after["thickness"], "callout_rows_equal": callout_after == callout_before})
    page.screenshot(str(HERE / "g3r-09-thickness-fullsave.png"))

    # --- scenario 4: a real revision conflict with an unsaved draft ------------------------------
    if page.ev("return $('callout-show-ignored').checked;"):
        page.click_selector("#callout-show-ignored")     # back to the default list: ignored rows are opt-in
        page.wait_ev("!$('callout-show-ignored').checked", timeout=15, label="ignored rows hidden again")
    page.ev("""const rows = [...document.querySelectorAll('#callout-list li')]; rows[0].click();""")
    page.wait_ev("""[...document.querySelectorAll('#callout-list li')]
      .findIndex(li => li.classList.contains('selected')) === 0""", timeout=30, label="first visible row")
    page.wait_ev("$('callout-state').textContent !== 'Yok sayıldı'", timeout=15,
                 label="the draft box is a visible row, not an ignored one")
    selected_id = visible_ids(page)[0]
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")
    page.type_text("ÖNCE")
    page.click_selector("#callout-save")
    wait_transcription(page, selected_id, "ÖNCE", "baseline text")

    behind = page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
      const current = await (await fetch('/api/guided/' + token)).json();
      const target = current.effective_callouts.find(row => !row.ignored && row.id !== {json.dumps(selected_id)})
        || current.effective_callouts.find(row => row.id !== {json.dumps(selected_id)});
      const response = await fetch('/api/guided/callout', {{method:'POST', headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{token, revision: current.revision, action:'set_ignored',
                              payload:{{callout_id: target.id, ignored:true}}}})}});
      return [response.status, response.ok, target.id];""")
    record("scenario 4: the server accepts a command the page did not send (the page is now stale)",
           behind[1] is True and behind[2] != selected_id, behind)
    draft = "  yarım kalan taslak  "
    stored_before = next(row["raw_text"] for row in transcriptions(page) if row["callout_id"] == selected_id)
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').select();")
    page.type_text(draft)
    page.click_selector("#callout-save")
    page.wait_ev("$('status').classList.contains('error')", timeout=60, label="conflict surfaced")
    conflict = panel(page)
    record("scenario 4: the conflict is shown, the typed draft survives and nothing was written",
           "oturum değişti" in conflict["status"] and conflict["text"] == draft and conflict["draft"] != "" and
           [row for row in server(page)["decisions"]["transcriptions"]
            if row["callout_id"] == selected_id][0]["raw_text"] == stored_before,
           {"status": conflict["status"], "text": conflict["text"], "draft_note": conflict["draft"],
            "server_still": stored_before})
    page.screenshot(str(HERE / "g3r-10-conflict.png"))
    # The conflict path refreshes the state and only re-enables the buttons when it is done: a click
    # thrown while the refresh was still in flight would land on a disabled button and do nothing.
    wait_until(page, lambda: page.ev("return !$('callout-save').disabled;"), "save button re-enabled")
    page.click_selector("#callout-save")
    wait_transcription(page, selected_id, draft, "re-saved draft")
    saved_draft = [row for row in server(page)["decisions"]["transcriptions"]
                   if row["callout_id"] == selected_id][0]
    record("scenario 4: after the refresh the same draft saves as a conscious decision",
           saved_draft["raw_text"] == draft, saved_draft)

    # --- scenario 6: narrow/wide + the older tools still work ------------------------------------
    page.resize(520, 900)
    time.sleep(0.8)
    narrow = boxes(page)
    click_box(page, narrow[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="narrow selection")
    narrow_panel = panel(page)
    page.screenshot(str(HERE / "g3r-11-narrow.png"))
    page.resize(1400, 900)
    time.sleep(0.8)
    wide = boxes(page)
    click_box(page, wide[0]["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="wide selection")
    wide_panel = panel(page)
    record("scenario 6: the same box is hit and cropped in a narrow and a wide window",
           narrow_panel["selected"] == narrow[0]["index"] == wide[0]["index"] == wide_panel["selected"] and
           narrow_panel["crop"] == wide_panel["crop"] and narrow_panel["title"] == wide_panel["title"],
           {"narrow_row": narrow_panel["selected"], "wide_row": wide_panel["selected"],
            "expected": narrow[0]["index"], "crop_equal": narrow_panel["crop"] == wide_panel["crop"]})
    page.screenshot(str(HERE / "g3r-12-wide.png"))

    profile_point = contour_point(page)
    page.click_selector("#pick-profile")
    page.click(profile_point["x"], profile_point["y"])
    page.wait_ev("$('profile').value !== ''", timeout=30, label="profile chosen")
    record("scenario 6: the profile tool still selects a contour (the callout overlay is not in the way)",
           page.ev("return $('profile').value;") == profile_point["id"],
           {"profile": page.ev("return $('profile').value;"), "expected": profile_point["id"]})

    # --- scenario 5: the three detection-notice cases --------------------------------------------
    normal_token, _ = make_fixture_session(pathlib.Path(NO_TEXT), lambda record_file: None)
    open_in_page(page, normal_token)
    page.screenshot(str(HERE / "g3r-13-empty-normal.png"))
    normal = panel(page)
    record("scenario 5: a real text-less drawing is explained as a normal empty result",
           "metinsiz çizim normal bir sonuçtur" in normal["detection"] and
           normal["summary"] == "Bu okumada callout alanı yok.",
           {"detection": normal["detection"], "summary": normal["summary"]})

    normal_path = SESSIONS / normal_token / "session.json"
    before_view = normal_path.read_bytes()
    page.click_selector("#callout-new")
    page.drag(*drag_points(page, 0.30, 0.30, 0.46, 0.44))
    wait_until(page, lambda: len(server(page)["decisions"]["manual_callouts"]) == 1,
               "manual region on the empty drawing")
    manually_added = server(page)["decisions"]["manual_callouts"]
    record("scenario 5: drawing a manual region still works on an empty drawing",
           len(manually_added) == 1 and manually_added[0]["id"].startswith("manual:"),
           {"manual": manually_added})

    refused_token, refused_path = make_fixture_session(pathlib.Path(DRAWING), _refuse_mismatch)
    refused_before = refused_path.read_bytes()
    open_in_page(page, refused_token)
    page.screenshot(str(HERE / "g3r-14-empty-refused.png"))
    refused = panel(page)
    markup_images = page.ev("return document.querySelectorAll('#callout-detection img').length;")
    record("scenario 5: a refused detection is named as such, never as a text-less drawing",
           "Aday üretilemedi" in refused["detection"] and "eşleşmiyor" in refused["detection"] and
           "metinsiz çizim normal bir sonuçtur" not in refused["detection"],
           {"detection": refused["detection"], "summary": refused["summary"]})
    record("scenario 5: an unknown diagnostic code is shown literally, not executed as markup",
           "<img src=x onerror=alert(1)>" in refused["detection"] and markup_images == 0,
           {"detection": refused["detection"], "images": markup_images})

    legacy_token, legacy_path = make_fixture_session(pathlib.Path(DRAWING), _drop_detection)
    legacy_before = legacy_path.read_bytes()
    open_in_page(page, legacy_token)
    page.screenshot(str(HERE / "g3r-15-empty-legacy.png"))
    legacy = panel(page)
    record("scenario 5: an old record with no detection information says exactly that",
           "eski kayıtta tespit bilgisi yok" in legacy["detection"] and
           "metinsiz çizim normal bir sonuçtur" not in legacy["detection"],
           {"detection": legacy["detection"], "summary": legacy["summary"]})

    record("scenario 5: merely showing a detection result writes no decision, revision or log entry",
           SESSIONS.joinpath(normal_token, "session.json").read_bytes() != before_view and
           refused_path.read_bytes() == refused_before and legacy_path.read_bytes() == legacy_before,
           {"normal_changed_by_the_manual_add": SESSIONS.joinpath(normal_token, "session.json").read_bytes() != before_view,
            "refused_bytes_unchanged": refused_path.read_bytes() == refused_before,
            "legacy_bytes_unchanged": legacy_path.read_bytes() == legacy_before,
            "refused_decisions": server(page)["decisions"]["transcriptions"],
            "refused_revision": server(page)["revision"]})

    # --- console and network must be clean apart from the deliberate conflict ---------------------
    # The browser asks for /favicon.ico on its own; the app serves no favicon route, so that 404 is
    # browser noise, not review-flow evidence (it shows up whenever Chrome's favicon cache is cold,
    # which is why the first run did not see it). It is exempted explicitly and still reported.
    # Any other console error or rejected request fails the run.
    noise = lambda row: "favicon" in ((row.get("url") or "") + (row.get("text") or ""))
    ignored_console = [entry for entry in page.console if entry["level"] == "error" and noise(entry)]
    errors = [entry for entry in page.console if entry["level"] == "error" and not noise(entry)]
    expected = [entry for entry in errors if "400" in entry["text"]]
    unexpected = [entry for entry in errors if "400" not in entry["text"]]
    ignored_requests = [item for item in page.failures if noise(item)]
    rejected = [item for item in page.failures if not noise(item)]
    record("no console error except the deliberately rejected stale save",
           bool(not unexpected and expected and
                all("/api/guided/" in entry["url"] for entry in expected)),
           {"unexpected": unexpected, "expected": expected,
            "browser_automatic_ignored": ignored_console + ignored_requests,
            "rejected_requests": page.failures})
    record("the only rejected request is the stale command the UI was told to retry",
           len(rejected) == 1 and all(item["status"] == 400 and "POST" in item["request"] and
                                      "/api/guided/callout" in item["url"] for item in rejected),
           {"rejected_requests": rejected, "browser_automatic_ignored": ignored_requests})

    (HERE / "browser-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "no_text_fixture": NO_TEXT, "steps": STEPS,
         "sessions": {"normal_empty": normal_token, "refused_fixture": refused_token,
                      "legacy_fixture": legacy_token},
         "fixture_note": "refused_fixture and legacy_fixture are edited on disk; normal_empty is a real run",
         "console": page.console, "rejected_requests": page.failures},
        ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [step for step in STEPS if not step["passed"]]
    print(f"\n{len(STEPS) - len(failed)}/{len(STEPS)} browser steps passed")
    page.close()
    return 1 if failed else 0


def _refuse_mismatch(record_file: dict) -> None:
    """The detector's own refusal shape (PLAN-18 §28) plus one unknown code to prove literal display."""
    record_file["callout_candidates"] = []
    record_file["callout_detection"] = {
        "detector_version": "callout-detector/1",
        "diagnostics": [{"code": "source_digest_mismatch", "observation_id": None},
                        {"code": "<img src=x onerror=alert(1)>", "observation_id": None}]}


def _drop_detection(record_file: dict) -> None:
    """A record written before the detector existed: no detection key at all."""
    record_file.pop("callout_detection", None)
    record_file["callout_candidates"] = []


if __name__ == "__main__":
    sys.exit(main())
