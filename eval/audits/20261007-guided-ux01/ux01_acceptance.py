"""UX-01 gerçek-Chrome kabulü (UX_PLAN §15–§21): 5 senaryo + Plate UX smoke.

Aynı kural: her karar gerçek arayüzden gerçek input olayıyla girer (mouse/klavye); `Runtime.evaluate`
yalnız okur, kaydırır ve sunucunun kendi kaydını çeker. Shared CDP harness yeniden kullanılır
(`20261006-guided-g3-review/`) — yeni harness kopyalanmadı. Çizim G9/G11 ile aynı plate.

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app        (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222
    ~/.hermes/cache/scratch/cdp-venv/bin/python ux01_acceptance.py

Senaryolar (uzunluk sırası plandaki gibi değil; tek oturumda sırayla ve durum bozmadan koşulur):

    §16 S1 — makine ipucu tek tık + reload yazmaz + çözülünce oto-ilerleme
    §17 S2 — Düzelt yalnız taslak; save sonrası kesin metin; oto-ilerleme çözülünce
    §18 S3 — çoklu seçim + tek atomik bulk; tek undo hepsini geri alır; reload kalıcı
    §19 S4 — Eksik kalanlar sayısı backend ile aynı; navigasyonlar; hazır metni
    §20 S5 — hiçbir sessiz karar yok (seçim/gezinme/aç-kapa/checkbox revizyon yazmaz)
    §21 SMOKE — build + dondurulmuş değerlendirici (evaluate_case.py) + G9 build ile birebir karşılaştırma
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
HARNESS = HERE.parent / "20261006-guided-g3-review"
ROUND = HERE.parent / "20261007-guided-ux-round"
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(ROUND))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402
import ux_acceptance as U  # noqa: E402  (yardımcılar: server/wait/row/checkbox okuma-gezinme)

APP, DRAWING = G3.APP, G3.DRAWING
record = G3.record

HOLE_TEXT = U.HOLE_TEXT
POCKET_TEXT = U.POCKET_TEXT
M8_HINT = U.M8_HINT
DIM_SINGLE = U.DIM_SINGLE
DIM_TYPED = U.DIM_TYPED
HOLE_CIRCLES = U.HOLE_CIRCLES
POCKET_CIRCLE = U.POCKET_CIRCLE
REFERENCE = str(ROOT / "examples/pdf with steps/5/plate with a pocket.STEP")
G9_STEP = HERE.parent / "20261007-guided-g11/cases/plate-pocket-vector/part.step"
EVALUATOR = HERE.parent / "20261007-guided-g11/evaluate_case.py"
CAD_PYTHON = ROOT / ".venv-cad/bin/python"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- UX-01'e özgü okumalar ---------------------------------------------------------------------------

def panel_state(page: C.Chrome) -> dict:
    return page.ev("""return {title: $('callout-title').textContent,
      remaining: $('callout-remaining').textContent,
      selected: [...document.querySelectorAll('#callout-list li')].findIndex(li => li.classList.contains('selected')),
      rows: document.querySelectorAll('#callout-list li').length,
      status: $('status').textContent};""")


def checklist_probe(page: C.Chrome) -> dict:
    return page.ev("""return {summary: $('readiness-summary').textContent,
      items: [...$('readiness-questions').querySelectorAll('li')].map(li => li.textContent.trim()),
      buildDisabled: $('build').disabled};""")


def visible_row_ids(data: dict) -> list[str]:
    return [row["id"] for row in data["effective_callouts"] if not row["ignored"]]


def resolved_ids(data: dict) -> set[str]:
    """§6.2 çözülmüş tanımı — sayfa JS'inden bağımsız, sunucu kaydından okunur."""
    states = {row["id"]: row for row in data.get("callouts") or []}
    parses = {row["callout_id"]: row for row in data.get("callout_parses") or []}
    out = set()
    for row in data["effective_callouts"]:
        if row["ignored"] or row.get("unbindable"):
            out.add(row["id"])
            continue
        state = states.get(row["id"]) or {}
        transcription = (state.get("transcription") or {})
        parse = (state.get("parse") or {})
        target = (state.get("target") or {})
        status = parse.get("status") or (parses.get(row["id"]) or {}).get("status")
        if (transcription.get("state") == "current" and parse.get("state") == "current"
                and status == "parsed" and target.get("state") == "current"):
            out.add(row["id"])
    return out


def unresolved_ids(data: dict) -> list[str]:
    keep = resolved_ids(data)
    return [row["id"] for row in data["effective_callouts"] if row["id"] not in keep]


def callout_fetch_count(page: C.Chrome) -> int:
    return page.ev("return performance.getEntriesByType('resource')"
                   ".filter(entry => entry.name.includes('/api/guided/callout')).length;")


def bulk_select(page: C.Chrome, ids: list[str]) -> dict:
    for callout_id in ids:
        box = U.row_box(page, callout_id)
        page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
        time.sleep(0.12)
    return page.ev("""return {count: $('callout-bulk-count').textContent,
      checked: document.querySelectorAll('#callout-list li input[type=checkbox]:checked').length,
      barHidden: $('callout-bulk-bar').hidden};""")


def revision_writes(page: C.Chrome) -> tuple[int, int]:
    data = U.server(page)
    return data["revision"], len(data.get("log") or [])


def click_box_selector(page: C.Chrome, selector: str) -> None:
    """Bileşik CSS seçicisi için gerçek tıklama (click_selector yalnız id alır)."""
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def expect_no_write(page: C.Chrome, label: str, action) -> dict:
    before = revision_writes(page)
    action()
    time.sleep(0.5)
    after = revision_writes(page)
    return {"label": label, "before": before, "after": after}


def wait_ready(page: C.Chrome, timeout: float = 180.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = U.readiness_of(page)
        if last and last.get("ready"):
            return last
        time.sleep(0.5)
    raise TimeoutError(f"readiness did not become ready: {json.dumps(last, ensure_ascii=False)[:300]}")


def main() -> int:
    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()
    page.screenshot(str(HERE / "ux01-00-open.png"))

    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    data = U.wait_state(page)
    total = len(data["effective_callouts"])
    record("S0 plate opens in a fresh session with 45 candidates", total == 45,
           {"token": data["token"], "callouts": total})
    listing = panel_state(page)
    chips = page.ev("""return {multi: $('callout-multi').textContent,
      hintYes: $('callout-hint-yes').textContent, hintEdit: $('callout-hint-edit').textContent,
      hintIgnore: $('callout-hint-ignore').textContent, prev: $('callout-prev').textContent,
      next: $('callout-next').textContent, readiness: document.querySelector('#readiness-box h3').textContent,
      build: $('build').textContent};""")
    record("S0 the UX-01 controls are served with the plan's own words",
           chips["multi"] == "Çoklu seç" and chips["next"] == "Sonraki eksik" and chips["prev"] == "Önceki"
           and chips["hintYes"] == "Evet, doğru" and chips["hintEdit"] == "Düzelt"
           and chips["hintIgnore"] == "Bu bir ölçü/not değil" and chips["readiness"] == "Eksik kalanlar"
           and chips["build"] == "3B Modeli Oluştur" and listing["remaining"] == "45 kontrol kaldı",
           {"chips": chips, "remaining": listing["remaining"]})
    page.screenshot(str(HERE / "ux01-01-candidates.png"))

    # --- §20 S5 (A bölümü: saf liste eylemleri hiçbir karar yazmaz) -------------------------------
    checks = []
    checks.append(expect_no_write(page, "callout select", lambda: U.row_click(page, visible_row_ids(data)[0])))
    checks.append(expect_no_write(page, "next unresolved", lambda: page.click_selector("#callout-next")))
    checks.append(expect_no_write(page, "previous", lambda: page.click_selector("#callout-prev")))
    checks.append(expect_no_write(page, "open technical details",
                                  lambda: click_box_selector(page, "#technical-details summary")))
    opened = page.ev("return document.querySelector('#technical-details').open;")
    checks.append(expect_no_write(page, "close technical details",
                                  lambda: click_box_selector(page, "#technical-details summary")))
    closed = page.ev("return document.querySelector('#technical-details').open;")
    checks.append(expect_no_write(page, "toggle ignored visibility",
                                  lambda: page.click_selector("#callout-show-ignored")))
    page.click_selector("#callout-show-ignored")
    checks.append(expect_no_write(page, "multi-select checkbox", lambda: (
        page.click_selector("#callout-multi"), bulk_select(page, [visible_row_ids(data)[1]]),
        page.click_selector("#callout-bulk-cancel"))))
    record("S5 selection, next/previous, panel open/close, ignored toggle and multi-select clicks write nothing",
           opened is True and closed is False
           and all(row["before"] == row["after"] for row in checks),
           {"checks": checks, "opened": opened, "closed": closed})
    page.screenshot(str(HERE / "ux01-02-no-writes.png"))

    # --- §16 S1: tek tık ipucu + reload güvenliği + oto-ilerleme -----------------------------------
    m8_id = U.callout_by_hint(data, M8_HINT)["id"]
    U.row_click(page, m8_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="M8 detail")
    hint = page.ev("""return {line: $('callout-hint-line').textContent, field: $('callout-text').value,
      yesHidden: $('callout-hint-yes').hidden, yesText: $('callout-hint-yes').textContent};""")
    before_hint = U.server(page)
    record("S1 the machine hint is visible as a question and selection alone writes nothing",
           hint["line"] == f"Çizimde şu mu yazıyor? {M8_HINT}" and hint["field"] == ""
           and hint["yesHidden"] is False and hint["yesText"] == "Evet, doğru"
           and not any(row["callout_id"] == m8_id for row in before_hint["decisions"].get("transcriptions") or []),
           {"hint": hint})

    page.navigate(f"{APP}/guided?session={data['token']}")
    page.wait_ev("!$('controls').hidden", timeout=60, label="reload")
    reloaded = U.wait_state(page)
    record("S1 a real reload before any click leaves the session without a transcription",
           not any(row["callout_id"] == m8_id for row in reloaded["decisions"].get("transcriptions") or []),
           {"transcriptions": len(reloaded["decisions"].get("transcriptions") or [])})

    U.row_click(page, m8_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="M8 detail 2")
    page.click_selector("#callout-hint-yes")           # tek gerçek tık
    accepted = U.wait_server(page, lambda d: any(
        row["callout_id"] == m8_id and row.get("raw_text") == M8_HINT
        for row in d["decisions"].get("transcriptions") or []), timeout=60, label="hint accepted")
    m8_row = next(row for row in accepted["decisions"]["transcriptions"] if row["callout_id"] == m8_id)
    m8_log = [row for row in accepted.get("log") or [] if row.get("action") == "transcribe"
              and (row.get("evidence") or {}).get("callout_id") == m8_id]
    record("S1 one click writes the exact hint as the user's own transcription (server-validated)",
           m8_row["raw_text"] == M8_HINT and m8_row["entered_by"] == "user" and m8_log
           and m8_log[-1]["evidence"].get("accepted_hint") is True
           and m8_log[-1]["evidence"].get("machine_text_hint") == M8_HINT,
           {"raw_text": m8_row["raw_text"], "log": m8_log[-1] if m8_log else None})
    after_hint = panel_state(page)
    m8_label = "C%d" % (visible_row_ids(accepted).index(m8_id) + 1)
    record("S1 a hint click alone does not auto-advance while the row is not yet resolved (no target yet)",
           after_hint["title"].startswith(m8_label + " ") and m8_id in unresolved_ids(accepted),
           {"title": after_hint["title"], "label": m8_label, "m8_unresolved": m8_id in unresolved_ids(accepted)})

    previous_title = page.ev("return $('callout-title').textContent;")
    U.declare_unbindable(page, m8_id)
    time.sleep(0.8)
    advanced = U.server(page)
    moved = panel_state(page)
    unresolved_after = unresolved_ids(advanced)
    order = visible_row_ids(advanced)
    old_id = m8_id
    start = order.index(old_id)
    expected_next = next((cid for cid in order[start + 1:] + order[:start + 1] if cid in unresolved_after and cid != old_id), None)
    shown_next = None
    if expected_next is not None:
        label = "C%d" % (order.index(expected_next) + 1)
        shown_next = label
    record("S1 when the row resolves (unbindable) the next unresolved is selected automatically",
           expected_next is not None and moved["title"].startswith(shown_next + " ")
           and moved["title"] != previous_title,
           {"previous": previous_title, "now": moved["title"], "expected": shown_next,
            "remaining": moved["remaining"]})
    page.screenshot(str(HERE / "ux01-03-hint-one-click.png"))

    # --- §17 S2: Düzelt yalnız taslak -----------------------------------------------------------------
    typed_hint, typed_text = "1 00,00", DIM_TYPED["1 00,00"]
    dim_id = U.callout_by_hint(reloaded, typed_hint)["id"]
    U.row_click(page, dim_id)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="dim detail")
    page.click_selector("#callout-hint-edit")
    draft = page.ev("""return {field: $('callout-text').value, draftNote: $('callout-draft').textContent,
      active: document.activeElement.id};""")
    too_early = U.server(page)
    record("S2 “Düzelt” puts the hint in the field as a draft only — no server write",
           draft["field"] == typed_hint and "Kaydedilmemiş" in draft["draftNote"]
           and draft["active"] == "callout-text"
           and not any(row["callout_id"] == dim_id for row in too_early["decisions"].get("transcriptions") or []),
           {"draft": draft})
    got = U.type_textarea(page, typed_text)
    untouched = U.server(page)
    record("S2 editing the draft still writes nothing before “Kaydet”",
           got == typed_text and not any(row["callout_id"] == dim_id
                                         for row in untouched["decisions"].get("transcriptions") or []),
           {"field": got})
    selected_before_save = page.ev("return $('callout-title').textContent;")
    page.click_selector("#callout-save")
    saved = U.wait_server(page, lambda d: any(
        row["callout_id"] == dim_id and row.get("raw_text") == typed_text
        for row in d["decisions"].get("transcriptions") or []), timeout=60, label="dim saved")
    stayed = panel_state(page)
    record("S2 the edited text is persisted exactly, and no auto-advance happens before the row resolves",
           next(row for row in saved["decisions"]["transcriptions"] if row["callout_id"] == dim_id)["raw_text"] == typed_text
           and stayed["title"] == selected_before_save,
           {"raw_text": typed_text, "title": stayed["title"]})
    U.declare_unbindable(page, dim_id)
    time.sleep(0.6)
    moved2 = panel_state(page)
    record("S2 after the scope decision resolves the row, the selection advances automatically",
           moved2["title"] != stayed["title"], {"before": stayed["title"], "after": moved2["title"]})
    page.screenshot(str(HERE / "ux01-04-edited-draft.png"))

    # --- §18 S3: çoklu seçim + tek atomik bulk --------------------------------------------------------
    current = U.server(page)
    undecided = unresolved_ids(current)
    reserved = {U.callout_by_hint(current, "6,80 THRU ALL")["id"], U.callout_by_hint(current, "50,00")["id"],
                U.callout_by_hint(current, "4 x")["id"]}
    reserved |= {U.callout_by_hint(current, hint)["id"] for hint in (*DIM_SINGLE, "1 5,00")}
    picked = [cid for cid in undecided if cid not in reserved][:5] + \
             [cid for cid in undecided if cid not in reserved][5:6]
    assert len(picked) == 6, picked
    revision_before = current["revision"]
    page.click_selector("#callout-multi")
    page.wait_ev("$('callout-bulk-bar').hidden === false", timeout=30, label="select mode")
    boxes = page.ev("return document.querySelectorAll('#callout-list li input[type=checkbox]').length;")
    selection = bulk_select(page, picked)
    record("S3 multi-select shows a checkbox per visible row and the bar counts the user's own clicks",
           boxes == len(visible_row_ids(current)) and selection["count"] == "6 alan seçildi"
           and selection["checked"] == 6 and selection["barHidden"] is False,
           {"boxes": boxes, "selection": selection})
    no_write = U.server(page)
    record("S3 checkbox clicks alone write nothing", no_write["revision"] == revision_before,
           {"revision": no_write["revision"]})
    fetches_before = callout_fetch_count(page)
    page.click_selector("#callout-bulk-apply")
    bulk = U.wait_server(page, lambda d: all(
        (U.reviews_of(d).get(cid) or {}).get("ignored") for cid in picked), timeout=90, label="bulk ignored")
    time.sleep(0.4)
    fetches = callout_fetch_count(page) - fetches_before
    bulk_events = [row for row in bulk.get("log") or [] if row.get("action") == "bulk_ignore_callouts"]
    cleared = page.ev("return {bar: $('callout-bulk-bar').hidden, multi: $('callout-multi').textContent};")
    record("S3 one explicit action closes six rows: one revision, one audit event, one request (one history step proven by the single undo below)",
           bulk["revision"] == revision_before + 1 and bulk["can_undo"] is True
           and len(bulk_events) == 1 and bulk_events[0]["value"]["count"] == 6
           and sorted(bulk_events[0]["value"]["callout_ids"]) == sorted(picked)
           and fetches == 1 and cleared["bar"] is True and cleared["multi"] == "Çoklu seç",
           {"revision": [revision_before, bulk["revision"]], "can_undo": bulk["can_undo"],
            "events": len(bulk_events), "fetches": fetches, "cleared": cleared})
    page.click_selector("#undo")
    undone = U.wait_server(page, lambda d: not any(
        (U.reviews_of(d).get(cid) or {}).get("ignored") for cid in picked), timeout=60, label="undo restores all")
    record("S3 one undo brings all six back together — the bulk action is exactly one history step",
           undone["revision"] == bulk["revision"] + 1
           and all(cid in unresolved_ids(undone) for cid in picked),
           {"revision": undone["revision"], "restored": len(picked)})
    page.click_selector("#callout-multi")
    page.wait_ev("$('callout-bulk-bar').hidden === false", timeout=30, label="select mode 2")
    bulk_select(page, picked)
    page.click_selector("#callout-bulk-apply")
    again = U.wait_server(page, lambda d: all(
        (U.reviews_of(d).get(cid) or {}).get("ignored") for cid in picked), timeout=90, label="bulk again")
    page.navigate(f"{APP}/guided?session={data['token']}")
    page.wait_ev("!$('controls').hidden", timeout=60, label="reload after bulk")
    reloaded_bulk = U.wait_state(page)
    record("S3 after re-applying and a real reload the six rows stay ignored",
           all((U.reviews_of(reloaded_bulk).get(cid) or {}).get("ignored") for cid in picked),
           {"revision": again["revision"], "still_ignored": len(picked)})
    page.screenshot(str(HERE / "ux01-05-bulk.png"))

    # --- §19 S4: Eksik kalanlar checklist -------------------------------------------------------------
    fresh = U.server(page)
    readiness = U.readiness_of(page)
    probe = checklist_probe(page)
    open_items = [text for text in probe["items"] if text.startswith("○")]
    done_items = [text for text in probe["items"] if text.startswith("✓")]
    expanded = 0
    for text in open_items:
        head = text[1:].strip().split(" ")[0]
        expanded += int(head) if head.isdigit() else 1
    record("S4 the checklist counts match the backend readiness rows exactly",
           expanded == len(readiness["questions"]) > 0
           and f"{len(readiness['questions'])} şey kaldı" in probe["summary"]
           and probe["buildDisabled"] is True,
           {"summary": probe["summary"], "open": open_items, "done": done_items,
            "questions": len(readiness["questions"])})

    def item_index(needle: str) -> int:
        return next(index for index, text in enumerate(probe["items"]) if needle in text and text.startswith("○"))

    text_index = item_index("Ölçü/not")
    U.click_checklist_item(page, text_index)
    page.wait_ev("document.activeElement && document.activeElement.id === 'callout-text'",
                 timeout=30, label="checklist -> text")
    jumped = page.ev("return {title: $('callout-title').textContent, active: document.activeElement.id};")
    first_unresolved = unresolved_ids(fresh)[0]
    order_fresh = visible_row_ids(fresh)
    record("S4 the “Ölçü/not” item opens the first unresolved callout and focuses its field",
           jumped["active"] == "callout-text"
           and jumped["title"].startswith("C%d " % (order_fresh.index(first_unresolved) + 1)),
           {"jumped": jumped, "first_unresolved": first_unresolved})
    record("S4 the checklist read is stable and no decision was written by navigating",
           U.server(page)["revision"] == fresh["revision"], {})
    if any("Gösterdiği yeri seç" in text for text in probe["items"] if text.startswith("○")):
        U.click_checklist_item(page, item_index("Gösterdiği yeri seç"))
        page.wait_ev("!$('target-panel').hidden", timeout=30, label="checklist -> target panel")
        record("S4 the “Gösterdiği yeri seç” item opens the target panel", True,
               {"title": page.ev("return $('callout-title').textContent;")})
    profile_index = item_index("Dış şekli seç")
    U.click_checklist_item(page, profile_index)
    page.wait_ev("document.activeElement && document.activeElement.id === 'profile'", timeout=30,
                 label="checklist -> profile")
    record("S4 the “Dış şekli seç” item focuses the contour control", True,
           {"active": page.ev("return document.activeElement.id;")})
    page.screenshot(str(HERE / "ux01-06-checklist.png"))

    # --- karar tamamlama (G9 akışıyla aynı sıra; UI yeni) --------------------------------------------
    profiles = sorted(fresh["options"]["profiles"], key=lambda p: (
        (max(pt[0] for pt in p["points"]) - min(pt[0] for pt in p["points"])) *
        (max(pt[1] for pt in p["points"]) - min(pt[1] for pt in p["points"])),), reverse=True)
    plate = profiles[0]
    point = plate["points"][0]

    def canvas_point(px_point: list) -> dict:
        return page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
          const data = await (await fetch('/api/guided/' + token)).json();
          const image = new Image(); image.src = data.drawing; await image.decode();
          const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
          const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
          const y = rect.top + {px_point[1]} * s * rect.height / canvas.height;
          return {{x: rect.left + {px_point[0]} * s * rect.width / canvas.width, y: y,
                   page_y: window.scrollY + y}};""")

    page.click_selector("#pick-profile")
    time.sleep(0.3)
    found = canvas_point(point)
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    target = canvas_point(point)
    page.click(target["x"], target["y"])
    page.wait_ev(f"$('profile').value === {json.dumps(plate['id'])}", timeout=30, label="plate profile")
    record("completion: the plate outline is selected by a real click", plate["id"] == "outline_1",
           {"profile": plate["id"], "edges": len(plate["edges"])})

    page.click_selector("#pick-calibration")
    for circle_id in ("g9", "g11"):
        got = U.circle_point(page, circle_id)
        page.click(got["x"], got["y"])
        time.sleep(0.2)
    measurement = next(row for row in fresh["options"]["measurements"] if row.get("text") == "1 00,00")
    page.ev(f"""const select = $('measurement'); select.value = '{measurement['id']}';
      select.dispatchEvent(new Event('change')); return true;""")
    page.click_selector("#apply-calibration")
    U.wait_server(page, lambda d: bool(d["decisions"].get("calibration")), timeout=40, label="calibration")
    page.focus_selector("#thickness")
    page.ev("$('thickness').value = '';")
    page.type_text("15")
    page.click_selector("#apply-thickness")
    U.wait_server(page, lambda d: d["decisions"].get("thickness") == 15.0, 40, "thickness")
    page.click_selector("#ack")
    U.wait_server(page, lambda d: d["decisions"].get("trace_acknowledged") is True, 40, "ack")
    page.screenshot(str(HERE / "ux01-07-calibration.png"))

    hole_id = U.callout_by_hint(fresh, "6,80 THRU ALL")["id"]
    parse = U.save_text(page, hole_id, HOLE_TEXT)
    record("completion: the hole note transcribes by hand and parses", parse["status"] == "parsed",
           {"text": HOLE_TEXT, "status": parse["status"]})
    time.sleep(0.6)
    proposals = page.ev("return [...$('target-proposals').querySelectorAll('.feature')].length;")
    if proposals:
        no_write = expect_no_write(page, "proposal highlight", lambda: page.ev(
            "document.querySelector('#target-proposals .feature span').click();"))
        record("S5 a proposal highlight writes nothing", no_write["before"] == no_write["after"],
               {"proposals": proposals, **no_write})
    U.save_target_manual(page, hole_id, "circle_group", HOLE_CIRCLES)
    record("completion: the four hole circles are confirmed by hand", True, {"circles": HOLE_CIRCLES})

    pocket_id = U.callout_by_hint(fresh, "50,00")["id"]
    U.save_text(page, pocket_id, POCKET_TEXT)
    time.sleep(0.6)
    panel = U.target_panel(page)
    if panel["proposals"]:
        page.click_selector("#target-confirm")
        U.wait_server(page, lambda d: any(
            row["callout_id"] == pocket_id and row.get("status") == "confirmed"
            for row in d["decisions"].get("callout_targets") or []), timeout=60, label="pocket target")
    else:
        U.save_target_manual(page, pocket_id, "circle", [POCKET_CIRCLE])
    record("completion: the pocket target is confirmed", True, {"proposals": len(panel["proposals"])})

    fragment = U.callout_by_hint(fresh, "4 x")["id"]
    U.ignore_callout(page, fragment)
    record("completion: the “4 x” fragment is declared not-a-callout with the single-row action", True,
           {"callout": fragment})

    for hint in DIM_SINGLE:
        cid = U.callout_by_hint(fresh, hint)["id"]
        U.row_click(page, cid)
        page.wait_ev("!$('callout-detail').hidden", timeout=30, label=f"dim {hint}")
        page.click_selector("#callout-hint-yes")
        U.wait_server(page, lambda d, cid=cid, hint=hint: any(
            row["callout_id"] == cid and row.get("raw_text") == hint
            for row in d["decisions"].get("transcriptions") or []), timeout=60, label=f"hint {hint}")
        U.declare_unbindable(page, cid)
    typed5 = U.callout_by_hint(fresh, "1 5,00")["id"]
    U.row_click(page, typed5)
    page.click_selector("#callout-hint-edit")
    U.type_textarea(page, DIM_TYPED["1 5,00"])
    page.click_selector("#callout-save")
    U.wait_server(page, lambda d: any(row["callout_id"] == typed5 and row.get("raw_text") == "15,00"
                                      for row in d["decisions"].get("transcriptions") or []),
                  timeout=60, label="dim 15,00")
    U.declare_unbindable(page, typed5)
    record("completion: the four printed hints are one click each and the two corrected texts are typed exactly",
           True, {"hints": DIM_SINGLE, "typed": list(DIM_TYPED.values())})
    page.screenshot(str(HERE / "ux01-08-decided.png"))

    # kalan her şeyi tek toplu eylemle kapat (plan §7 ruhu: 45→tek adım)
    current = U.server(page)
    remaining = unresolved_ids(current)
    page.click_selector("#callout-multi")
    page.wait_ev("$('callout-bulk-bar').hidden === false", timeout=30, label="final select")
    bulk_select(page, remaining)
    page.click_selector("#callout-bulk-apply")
    swept = U.wait_server(page, lambda d: not unresolved_ids(d), timeout=120, label="all resolved")
    record("the remaining undecided rows close in one explicit bulk action and nothing stays unresolved",
           not unresolved_ids(swept), {"closed": len(remaining), "revision": swept["revision"]})

    readiness = wait_ready(page)
    probe = checklist_probe(page)
    record("S4 with every blocker resolved the checklist says so and the build is enabled",
           probe["summary"] == "✓ Tüm gerekli bilgiler tamamlandı" and probe["buildDisabled"] is False
           and any(text.startswith("✓ Dış şekil seçildi") for text in probe["items"])
           and any(text.startswith("✓ Kalınlık girildi") for text in probe["items"]),
           {"summary": probe["summary"], "items": probe["items"]})
    page.ev("$('readiness-box').scrollIntoView({block:'start'});")
    time.sleep(0.3)
    page.screenshot(str(HERE / "ux01-09-ready.png"))

    # --- §21 smoke: build + dondurulmuş değerlendirici ------------------------------------------------
    page.click_selector("#build")
    built = U.wait_server(page, lambda d: bool(d.get("step")), timeout=420, label="built STEP")
    record("SMOKE the plate builds from the new UI", built.get("build_status") == "complete",
           {"build_status": built.get("build_status"), "step": built.get("step")})
    for name, key in (("part.step", "step"), ("plan.json", "plan"), ("plan-audit.json", "audit")):
        with urllib.request.urlopen(APP + built[key], timeout=60) as response:
            (HERE / name).write_bytes(response.read())
    (HERE / "session-public.json").write_text(json.dumps(built, ensure_ascii=False, indent=2), encoding="utf-8")
    bundle = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/export', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")
    (HERE / "review-bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    page.screenshot(str(HERE / "ux01-10-built.png"))

    evaluation = json.loads(subprocess.run(
        [str(CAD_PYTHON), str(EVALUATOR), str(HERE / "part.step"), REFERENCE],
        capture_output=True, text=True, timeout=600).stdout.strip().splitlines()[-1])
    (HERE / "evaluate.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
    verdict = evaluation.get("final_geometry_verdict") or {}
    record("SMOKE the frozen evaluator returns the G9 plate verdict on the new build",
           evaluation.get("step_reopen") is True and verdict.get("pass") is True
           and verdict.get("shape_ok") is True,
           {"verdict": verdict, "bbox": evaluation.get("bbox"), "features": evaluation.get("features")})
    same_bytes = sha256(HERE / "part.step") == sha256(G9_STEP)
    reference_g11 = json.loads((HERE.parent / "20261007-guided-g11/cases/plate-pocket-vector.json")
                               .read_text(encoding="utf-8"))
    new_bbox, old_bbox = evaluation.get("bbox") or [], reference_g11.get("bbox") or []
    bbox_close = len(new_bbox) == len(old_bbox) and all(
        abs(float(a) - float(b)) < 0.02 for a, b in zip(new_bbox, old_bbox))
    record("SMOKE the new build carries the G9/g11 plate geometry (bbox within 0.02 mm of the recorded case)",
           bbox_close and (evaluation.get("features") or {}).get("solids") == 1,
           {"new_bbox": new_bbox, "g11_bbox": old_bbox, "sha_identical": same_bytes,
            "features": evaluation.get("features")})

    # --- §23 metrikler --------------------------------------------------------------------------------
    final = U.server(page)
    log = final.get("log") or []
    typed = [row for row in log if row.get("action") in ("transcribe", "edit_transcription")
             and not (row.get("evidence") or {}).get("accepted_hint")]
    hints = [row for row in log if (row.get("evidence") or {}).get("accepted_hint") is True]
    ignores = [row for row in log if row.get("action") == "ignore_callout"]
    single = [row for row in ignores if (row.get("evidence") or {}).get("bulk") is not True]
    bulks = [row for row in log if row.get("action") == "bulk_ignore_callouts"]
    bulk_rows = sum(row["value"]["count"] for row in bulks)
    targets = final["decisions"].get("callout_targets") or []
    metrics = {
        "plate_candidate_count": len(final["callout_candidates"]),
        "manual_transcription_count": len(typed),
        "one_click_hint_acceptance_count": len(hints),
        "bulk_ignored_count": bulk_rows,
        "number_of_bulk_actions": len(bulks),
        "manual_target_corrections": sum(1 for row in targets
                                         if (row.get("evidence") or [{}])[0].get("kind") == "user_click"),
        "single_ignores": len(single),
        "total_explicit_user_actions": (len(typed) + len(hints) + len(single) + len(bulks) + len(targets)
                                        + 1 + 1 + 1 + 1),
        "g9_reference": {"typed_texts": 4, "hint_single_clicks": 4, "single_ignores": 1,
                         "bulk_rows": 36, "bulk_actions": 1},
    }
    (HERE / "ux01-metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    record("SMOKE the burden metrics are recorded against the G9 numbers", True, metrics)

    errors = [entry for entry in page.console if entry["level"] == "error"]
    record("no unexpected console errors and no rejected requests", not errors and not page.failures,
           {"unexpected": errors, "failures": page.failures})

    (HERE / "ux01-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "token": final["token"], "steps": G3.STEPS,
         "console": page.console, "rejected_requests": page.failures}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    failed = [step for step in G3.STEPS if not step["passed"]]
    print(f"\n{len(G3.STEPS) - len(failed)}/{len(G3.STEPS)} UX-01 browser steps passed", flush=True)
    for step in failed:
        print("  FAIL:", step["step"], flush=True)
    page.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
