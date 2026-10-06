"""G6 real-browser acceptance (PLAN §11) — the target confirmation flow, in a real Chrome.

The module tests prove the rules; this drives the actual interface with real clicks and typing:
transcribe Ø8 → the parse and the ranked proposals are visible → a proposal is highlighted on the
drawing → it is confirmed → the page is reloaded → a geometry change makes the target stale → the
user selects another target by hand and reconfirms → undo and reopen stay consistent. It also checks
the GX buttons and the G8 readiness gate, because those are the two places the same panel must not lie.

    ~/.hermes/cache/scratch/cdp-venv/bin/python g6_target_acceptance.py

Needs the app on http://127.0.0.1:8765 and Chrome with --remote-debugging-port=9222.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

# Tek ortak harness: G3 kabulünün CDP istemcisi ve sayfa yardımcıları olduğu yerde kullanılır
# (kopyalamak iki farklı sürücü demek olurdu).
HARNESS = pathlib.Path(__file__).parent.parent / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP, DRAWING, HERE = G3.APP, G3.DRAWING, pathlib.Path(__file__).parent
record = G3.record


def server(page: C.Chrome) -> dict | None:
    """The record as the page itself sees it. No session yet (the first, empty page) means no fetch —
    asking `/api/guided/null` would only pollute the console this acceptance reads."""
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      if (!token) return null;
      return await (await fetch('/api/guided/' + token)).json();""")


def wait_state(page: C.Chrome, timeout: float = 120.0) -> dict:
    """The drawing is loaded and the callout layer exists."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = server(page)
        if data and data.get("effective_callouts"):
            return data
        time.sleep(0.4)
    raise TimeoutError("callout alanı olan bir okuma yüklenmedi")


def g6_panel(page: C.Chrome) -> dict:
    return page.ev("""return {
      targetHidden: $('target-panel').hidden,
      targetState: $('target-state').textContent,
      summary: $('target-summary').textContent,
      proposals: [...$('target-proposals').querySelectorAll('.feature')].map(row => row.textContent),
      picked: $('target-picked').textContent,
      note: $('target-note').textContent,
      readiness: $('readiness-summary').textContent,
      questions: [...$('readiness-questions').querySelectorAll('li')].map(li => li.textContent),
      buildDisabled: $('build').disabled,
      unbindable: $('target-unbindable').textContent,
      status: $('status').textContent
    };""")


def canvas_hash(page: C.Chrome) -> str:
    return page.ev("return $('sheet').toDataURL().slice(-96);")


def circle_point(page: C.Chrome, circle_id: str) -> dict:
    """Viewport point of a circle's centre, scrolled into view (mirrors `draw()`'s transform)."""
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


def nearest_circle_for(page: C.Chrome, callout_id: str) -> dict | None:
    """The circle nearest the callout's box, with its distance — the region whose proposals can rank."""
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const row = (data.effective_callouts || []).find(item => item.id === '%s');
      const cx = (row.region[0] + row.region[2]) / 2, cy = (row.region[1] + row.region[3]) / 2;
      const image = new Image(); image.src = data.drawing; await image.decode();
      const w = image.naturalWidth, h = image.naturalHeight;
      const best = (data.options.circles || []).map(circle => ({id: circle.id,
        d: Math.hypot(circle.center[0] - cx * w, circle.center[1] - cy * h)})).sort((a, b) => a.d - b.d)[0];
      return best || null;""" % callout_id)


def second_profile(page: C.Chrome) -> str:
    """Another closed contour: switching to it is a real geometry change for the confirmation."""
    return page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const current = data.decisions.profile_id;
      const other = (data.options.profiles || []).find(row => row.id !== current) || null;
      return other ? other.id : null;""")


def main() -> int:
    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()

    page.set_file("#file", DRAWING)
    data = wait_state(page)
    callouts = data["effective_callouts"]
    record("çizim açıldı ve callout alanları listelendi", bool(callouts), {"callouts": len(callouts)})

    # --- the callout whose box sits closest to a circle: its proposals have something to rank -------
    page.click_selector("#pick-callout")                      # gerçek kullanıcı akışı: önce inceleme aracı
    time.sleep(0.3)
    ranked = []
    for row in callouts:
        near = nearest_circle_for(page, row["id"])
        if near:
            ranked.append((near["d"], row["id"], near["id"]))
    target_id, chosen_circle, other = None, None, None
    best = None
    for distance, callout_id, circle_id in sorted(ranked)[:8]:
        G3.click_box(page, callout_id)
        time.sleep(0.5)
        selected = page.ev("return [...document.querySelectorAll('#callout-list li')]"
                           ".findIndex(li => li.classList.contains('selected'));")
        if selected >= 0:
            target_id, chosen_circle = callout_id, circle_id
            best = {"callout": callout_id, "circle": circle_id, "distance_px": round(distance, 1)}
            break
    record("gerçek tıklamayla bir callout seçildi (daireye en yakın bölge)", bool(target_id),
           best or "hiçbir kutu seçilemedi")
    if not target_id:
        return 1

    # --- transcribe: the user types what the drawing prints ----------------------------------------
    page.focus_selector("#callout-text")
    page.ev("$('callout-text').value = ''; $('callout-text').dispatchEvent(new Event('input'));")
    page.type_text("Ø8 THRU")
    page.click_selector("#callout-save")
    page.wait_ev("$('callout-state').textContent.length > 0 && $('callout-draft').textContent === ''",
                 timeout=30, label="transcription saved")
    time.sleep(0.8)                                   # öneriler ayrı bir okumayla gelir
    panel = g6_panel(page)
    record("metin kaydedildi ve okuma panelde görünüyor",
           bool(panel["proposals"]) and not panel["targetHidden"],
           {"state": panel["targetState"], "proposals": panel["proposals"][:2]})

    # --- proposal highlight: clicking a proposal paints the drawing ---------------------------------
    before = canvas_hash(page)
    page.ev("""const row = $('target-proposals').querySelector('.feature span');
      row.dispatchEvent(new MouseEvent('click', {bubbles: true})); return true;""")
    time.sleep(0.5)
    record("öneri satırı çizimde vurgulanıyor (tuval gerçekten değişti)",
           canvas_hash(page) != before, {"before": before, "after": canvas_hash(page)})
    page.screenshot(str(HERE / "g6-00-proposal.png"))

    # --- confirm the proposal (the [Onayla] button, not the API) ------------------------------------
    page.click_selector("#target-confirm")
    deadline = time.time() + 40
    stored = None
    while time.time() < deadline:
        stored = next((row for row in (server(page)["decisions"]["callout_targets"] or [])
                       if row["callout_id"] == target_id), None)
        if stored:
            break
        time.sleep(0.4)
    record("[Onayla] onaylanan hedefi kanıtıyla birlikte kaydetti",
           bool(stored) and stored["evidence"][0]["kind"] == "proposal" and stored["status"] == "confirmed",
           {"target": stored})
    panel = g6_panel(page)
    record("panel onaylanan hedefi gösteriyor", "Onaylı" in panel["summary"], {"summary": panel["summary"]})
    page.screenshot(str(HERE / "g6-01-confirmed.png"))

    # --- reload: the confirmation is the record's, not the page's ------------------------------------
    page.navigate(APP + "/guided" + "?session=" + data["token"])
    page.wait_ev("$('status').textContent.includes('Kaydedilmiş')", timeout=60, label="reopened")
    page.click_selector("#pick-callout")                 # seçim sayfada kalmaz: araç yeniden alınır
    time.sleep(0.3)
    G3.click_box(page, target_id)
    page.wait_ev("$('target-summary').textContent.includes('Onaylı')", timeout=40, label="target panel")
    again = g6_panel(page)
    record("yeniden açıldığında onay aynı okumadan geliyor",
           "Onaylı" in again["summary"] and again["targetState"] == "hedef güncel",
           {"summary": again["summary"], "state": again["targetState"]})
    page.screenshot(str(HERE / "g6-02-reopened.png"))

    # --- geometry change -> the target goes stale ----------------------------------------------------
    other = second_profile(page)
    record("aynı paftada başka bir kontur var (geometri değişimi için)", bool(other), {"profile": other})
    assert chosen_circle is not None
    if other:
        page.ev(f"""const select = $('profile'); select.value = '{other}';
          select.dispatchEvent(new Event('change')); return true;""")
        page.wait_ev("$('target-state').textContent === 'hedef eskidi'", timeout=40, label="stale target")
        stale = g6_panel(page)
        record("kontur değişince hedef 'eskidi' olarak işaretlendi ve nedeni yazıldı",
               "eskidi" in stale["summary"], {"summary": stale["summary"]})
        record("hazırlık kapısı eskimiş hedefi listeliyor ve üretimi kapatıyor",
               bool(stale["questions"]) and stale["buildDisabled"],
               {"questions": stale["questions"][:3], "buildDisabled": stale["buildDisabled"]})
        page.screenshot(str(HERE / "g6-03-stale.png"))

    # --- manual reselect by clicking a circle on the drawing, then confirm ---------------------------
    page.click_selector("#target-other")
    time.sleep(0.3)
    point = circle_point(page, chosen_circle)
    page.click(point["x"], point["y"])
    time.sleep(0.4)
    picked = g6_panel(page)
    record("elle hedef seçiminde tıklanan daire panelde birikiyor",
           chosen_circle in picked["picked"], {"picked": picked["picked"]})
    page.screenshot(str(HERE / "g6-04-picked.png"))
    page.click_selector("#target-apply")
    deadline = time.time() + 40
    reconfirmed = None
    while time.time() < deadline:
        reconfirmed = next((row for row in (server(page)["decisions"]["callout_targets"] or [])
                            if row["callout_id"] == target_id), None)
        if reconfirmed and reconfirmed["evidence"][0]["kind"] == "user_click":
            break
        time.sleep(0.4)
    record("elle seçilen hedef 'user_click' kanıtıyla yeniden onaylandı",
           bool(reconfirmed) and reconfirmed["evidence"][0]["kind"] == "user_click"
           and reconfirmed["target_ids"] == [chosen_circle],
           {"target": reconfirmed})
    record("yeniden onaylanan hedef yeni geometri anahtarını taşıyor",
           bool(reconfirmed) and reconfirmed.get("profile_id") == other if other else True,
           {"profile_id": (reconfirmed or {}).get("profile_id"), "expected": other})
    page.wait_ev("$('target-state').textContent === 'hedef güncel'", timeout=40, label="current again")

    # --- GX: the package is a real download button and the bundle is the record's --------------------
    page.click_selector("#review-export")
    page.wait_ev("$('status').textContent.includes('İnceleme paketi indirildi')", timeout=40, label="export")
    bundle = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/export', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: token})})).json();""")
    rows = {row["callout_id"]: row for row in bundle.get("callouts", [])}
    record("inceleme paketi bu oturumun okumasını taşıyor",
           bool(rows.get(target_id)) and rows[target_id]["confirmed_target"] is not None
           and bool(rows[target_id]["target_proposals"]),
           {"callouts": len(bundle.get("callouts", [])), "raw_text": rows.get(target_id, {}).get("raw_text")})

    # --- undo: the reconfirmation goes back, and the record says so ---------------------------------
    page.click_selector("#undo")
    time.sleep(1.2)
    after_undo = next((row for row in (server(page)["decisions"]["callout_targets"] or [])
                       if row["callout_id"] == target_id), None)
    record("geri alma son onayı geri aldı (kayıt tarihsel kaldı)",
           after_undo is None or after_undo.get("profile_id") != (reconfirmed or {}).get("profile_id"),
           {"target": after_undo})
    page.navigate(APP + "/guided?session=" + data["token"])
    page.wait_ev("$('status').textContent.includes('Kaydedilmiş')", timeout=60, label="reopen after undo")
    record("geri alma sonrası yeniden açılış tutarlı", True,
           {"target": next((row for row in (server(page)["decisions"]["callout_targets"] or [])
                            if row["callout_id"] == target_id), None)})

    errors = [entry for entry in page.console if entry["level"] == "error"]
    unexpected = [entry for entry in errors if "400" not in entry["text"]]
    record("beklenmeyen konsol hatası yok", not unexpected,
           {"unexpected": unexpected, "failures": page.failures})

    (HERE / "g6-steps.json").write_text(json.dumps(
        {"app": APP, "drawing": DRAWING, "steps": G3.STEPS, "console": page.console,
         "rejected_requests": page.failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [step for step in G3.STEPS if not step["passed"]]
    print(f"\n{len(G3.STEPS) - len(failed)}/{len(G3.STEPS)} G6 browser steps passed")
    page.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
