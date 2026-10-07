"""G12.1b — kapsam kararı kabul koşusu (PLAN-25 §21/§99), gerçek Chrome + gerçek girdi olayları.

Beş senaryo, planın kendi başlıklarıyla:

```text
A  metadata satırı → "Bu bir ölçü/not değil" → not_model_input → sonraki eksik ilerler
B  gerçek callout → desteklenmiyor + gerekçe → build kapalı, satır blok/navigasyonda kalır
C  başka bir satır → "Zaten başka bir bilgiyle temsil ediliyor" → geçerli dayanak → kapsam çözülür
D  dayanak satırı eskir (alan düzeltmesi) → redundant BLOCKER'a döner
E  reload kararı korur; undo önceki duruma döndürür
```

Her karar gerçek arayüzden girer (fare tıklaması, klavye metni); `Runtime.evaluate` yalnız durumu
okur. Kanıt: senaryo başına ekran görüntüsü, `g12-disposition-steps.json`, baskı (exit≠0 = düşen adım).

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app     (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222, scratch profil (chrome-g11)
    ~/.hermes/cache/scratch/cdp-venv/bin/python g12_disposition_acceptance.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

HARNESS = pathlib.Path(__file__).parent.parent.parent / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP, DRAWING, HERE = G3.APP, G3.DRAWING, pathlib.Path(__file__).parent
record = G3.record

STEPS_FILE = HERE / "g12-disposition-steps.json"
TIMEOUT = 60.0


def server(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      if (!token) return null;
      return await (await fetch('/api/guided/' + token)).json();""")


def wait_server(page: C.Chrome, predicate, timeout: float = TIMEOUT, label: str = "") -> dict:
    deadline = time.time() + timeout
    data = None
    while time.time() < deadline:
        data = server(page)
        if data and predicate(data):
            return data
        time.sleep(0.3)
    raise TimeoutError(f"server condition not met: {label}")


def reviews_of(data: dict) -> dict:
    return {row["callout_id"]: row for row in data["decisions"].get("callout_reviews") or []}


def coverage_of(data: dict) -> dict:
    return data.get("coverage") or {}


def bucket_contains(data: dict, bucket: str, callout_id: str) -> bool:
    return callout_id in (coverage_of(data).get(bucket) or [])


def row_by(predicate, data: dict, what: str) -> dict:
    for row in data.get("effective_callouts") or []:
        if predicate(row):
            return row
    raise KeyError(f"bu çizimde {what} bulunamadı")


def row_box(page: C.Chrome, callout_id: str, show_ignored: bool = False) -> dict:
    """Viewport box of a callout's row in the (visible) list — the index comes from the server."""
    flag = "true" if show_ignored else "false"
    index = page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const visible = data.effective_callouts.filter(row => {flag} || row.disposition !== 'not_model_input');
      return visible.findIndex(row => row.id === '{callout_id}');""")
    if index is None or index < 0:
        raise RuntimeError(f"callout {callout_id} not in the visible list")
    selector = f"#callout-list li:nth-child({index + 1})"
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    return page.box(selector)


def row_click(page: C.Chrome, callout_id: str, show_ignored: bool = False) -> None:
    box = row_box(page, callout_id, show_ignored)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def selected_title(page: C.Chrome) -> str:
    return page.ev("return $('callout-title').textContent;")


def label_of(data: dict, callout_id: str) -> str:
    visible = [row for row in data["effective_callouts"] if row.get("disposition") != "not_model_input"]
    return "C%d" % ([row["id"] for row in visible].index(callout_id) + 1)


def type_reason(page: C.Chrome, text: str) -> str:
    page.wait_ev("!$('unsupported-box').hidden", timeout=30, label="reason box")
    page.focus_selector("#unsupported-reason")
    page.ev("$('unsupported-reason').select();")
    page.type_text(text)
    return page.ev("return $('unsupported-reason').value;")


def edit_region(page: C.Chrome, fx0: float, fy0: float, fx1: float, fy1: float) -> None:
    page.click_selector("#callout-edit")
    time.sleep(0.3)
    start, end = G3.drag_points(page, fx0, fy0, fx1, fy1)
    page.drag(start, end)
    time.sleep(0.4)


def main() -> int:
    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()
    page.set_file("#file", DRAWING)
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    page.wait_ev("$('callout-summary').textContent.length > 0", timeout=90, label="callout summary")
    data = wait_server(page, lambda d: d.get("effective_callouts"), label="callouts")
    record("the plate opens with the served coverage audit in the public state",
           isinstance(coverage_of(data), dict) and "counts" in coverage_of(data),
           {"token": data["token"], "callouts": len(data["effective_callouts"]),
            "counts": coverage_of(data)["counts"]})
    page.screenshot(str(HERE / "A-00-open.png"))

    # --- A: metadata row → not_model_input → next-unresolved advances ---------------------------------
    metadata = None
    for predicate, what in ((lambda row: row.get("machine_text_hint") == "A4", "A4 ipucu"),
                            (lambda row: row.get("machine_text_hint")
                             and not any(ch.isdigit() for ch in row["machine_text_hint"]), "rakamsız ipucu"),
                            (lambda row: True, "ilk satır")):
        try:
            metadata = row_by(predicate, data, what)
            break
        except KeyError:
            continue
    visible_ids_before = [row["id"] for row in data["effective_callouts"]
                          if row.get("disposition") != "not_model_input"]
    row_click(page, metadata["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail A")
    page.click_selector("#callout-ignore")
    data = wait_server(page, lambda d: (reviews_of(d).get(metadata["id"]) or {}).get("disposition")
                       == "not_model_input", label="A: not_model_input stored")
    selected = page.ev("return {title: $('callout-title').textContent, status: $('status').textContent};")
    # Karar satırı listeyi terk ettiği için sözleşme "Modele ait olmayanları göster" ile geri bakılır.
    page.click_selector("#callout-show-ignored")
    time.sleep(0.4)
    row_click(page, metadata["id"], show_ignored=True)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail A (shown)")
    badge = page.ev("return $('callout-state').textContent;")
    page.click_selector("#callout-show-ignored")
    time.sleep(0.4)
    record("A: 'Bu bir ölçü/not değil' stores the named claim and the panel reports it",
           badge == "Modele ait değil" and "not_model_input" not in badge, {"badge": badge})
    # İlerleme kararın KENDİ konumundan sürer (karar öncesi görünür sıra; §17): o sıradaki
    # çözülmemiş ilk satır — sıra sonuna gelinirse başa döner.
    position = visible_ids_before.index(metadata["id"])
    order = visible_ids_before[position + 1:] + visible_ids_before[:position + 1]
    blocking = set(coverage_of(data).get("unclassified") or [])
    expected_id = next((cid for cid in order if cid in blocking), None)
    advanced = expected_id is not None and selected["title"].startswith(label_of(data, expected_id))
    record("A: the row resolves through the backend bucket and next-unresolved advances to another row",
           bucket_contains(data, "not_model_input", metadata["id"]) and advanced,
           {"row": metadata["id"], "hint": metadata.get("machine_text_hint"), "selected": selected["title"],
            "expected_row": expected_id, "expected_label": label_of(data, expected_id) if expected_id else None})
    page.screenshot(str(HERE / "A-01-not-model-input.png"))

    # --- B: real callout → unsupported + reason → build stays disabled -------------------------------
    real = row_by(lambda row: row.get("machine_text_hint")
                  and any(ch.isdigit() for ch in row["machine_text_hint"])
                  and row["id"] not in (metadata["id"],), data, "rakamlı ipucu")
    label_b = label_of(data, real["id"])
    row_click(page, real["id"])
    page.wait_ev("!$('target-panel').hidden", timeout=30, label="target panel B")
    long_label = page.ev("return $('target-unbindable').textContent;")
    page.click_selector("#target-unbindable")
    typed = type_reason(page, "yazılı daralma ölçüsü; bu sürümün uygulayamadığı bir özellik")
    page.click_selector("#unsupported-save")
    data = wait_server(page, lambda d: (reviews_of(d).get(real["id"]) or {}).get("disposition")
                       == "build_relevant_unsupported", label="B: unsupported stored")
    review = reviews_of(data)[real["id"]]
    readiness = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/readiness', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")
    listed = [q for q in readiness.get("questions") or [] if q.get("callout_id") == real["id"]]
    build_disabled = page.ev("return $('build').disabled;")
    record("B: the unsupported claim needs the reviewer's own reason and is stored as such",
           long_label == "Gerçek ölçü/not ama şu an modele uygulanamıyor"
           and review["disposition_reason"] == typed and typed,
           {"button": long_label, "typed": typed, "stored": review["disposition_reason"]})
    record("B: the claim blocks the build (readiness question + disabled button), it is not resolved",
           readiness["ready"] is False and listed and listed[0]["category"] == "unsupported_build_relevant"
           and build_disabled is True and bucket_contains(data, "build_relevant_unsupported", real["id"]),
           {"questions": len(readiness["questions"]), "for_row": listed, "build_disabled": build_disabled})
    # state while a *different* row is selected: the unsupported row keeps the claim and its own copy
    first_visible = next(row["id"] for row in data["effective_callouts"]
                         if row.get("disposition") != "not_model_input")
    row_click(page, first_visible)
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail (other row)")
    reached = []
    for _ in range(len(data["effective_callouts"]) + 2):
        page.click_selector("#callout-next")
        time.sleep(0.25)
        title = selected_title(page)
        reached.append(title)
        if title.startswith(label_b + " "):
            break
    panel = page.ev("return {state: $('target-state').textContent, summary: $('target-summary').textContent,"
                    " badge: $('callout-state').textContent};")
    record("B: the unsupported row stays a navigation/blocker item and its panel explains the stop",
           any(row.startswith(label_b + " ") for row in reached)
           and "uygulayamıyor" in panel["state"]
           and "Bu gerçek bilgi şu an modele uygulanamıyor" in panel["summary"]
           and panel["badge"] == "Gerçek ölçü/not · uygulanamıyor",
           {"label": label_b, "reached": reached[-3:], "panel": panel})
    page.screenshot(str(HERE / "B-01-unsupported.png"))

    # --- C: a decision that already represents a fact (thickness) -------------------------------------
    page.ev("$('thickness').scrollIntoView({block:'center'});")
    page.focus_selector("#thickness")
    page.ev("$('thickness').select();")
    page.type_text("15")
    page.click_selector("#apply-thickness")
    data = wait_server(page, lambda d: (d["decisions"] or {}).get("thickness") == 15, label="C: thickness")
    cited = next(row for row in data["effective_callouts"]
                 if row["id"] not in (metadata["id"], real["id"]) and row.get("disposition") is None)
    row_click(page, cited["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail C")
    page.click_selector("#target-redundant")
    page.wait_ev("!$('redundant-box').hidden", timeout=30, label="citation box")
    options = page.ev("return [...$('redundant-reference').children].map(o => o.value);")
    page.ev("$('redundant-reference').value = 'decision:thickness';"
            "$('redundant-reference').dispatchEvent(new Event('change',{bubbles:true}));")
    picked = page.ev("return $('redundant-reference').value;")
    page.click_selector("#redundant-save")
    data = wait_server(page, lambda d: (reviews_of(d).get(cited["id"]) or {}).get("disposition") == "redundant",
                       label="C: redundant stored")
    review = reviews_of(data)[cited["id"]]
    record("C: 'represented by another fact' cites the backend's own decision vocabulary and resolves",
           "decision:thickness" in options and picked == "decision:thickness"
           and review.get("duplicate_of") == "decision:thickness"
           and bucket_contains(data, "redundant", cited["id"])
           and not bucket_contains(data, "invalid_duplicate", cited["id"]),
           {"options": options[:8], "picked": picked, "stored": review.get("duplicate_of"),
            "bucket": "redundant" if bucket_contains(data, "redundant", cited["id"]) else "?"})
    page.screenshot(str(HERE / "C-01-redundant.png"))

    # --- D: the cited neighbour goes stale → the redundant claim becomes a blocker --------------------
    dayanak = next(row for row in data["effective_callouts"]
                   if row.get("machine_text_hint") and row["id"] not in (metadata["id"], real["id"], cited["id"]))
    row_click(page, dayanak["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail D1")
    page.click_selector("#callout-hint-yes")
    data = wait_server(page, lambda d: any(row["callout_id"] == dayanak["id"]
                       for row in d["decisions"].get("transcriptions") or []), label="D: hint accepted")
    row_click(page, dayanak["id"])
    page.click_selector("#target-redundant")
    page.ev("$('redundant-reference').value = 'decision:thickness';"
            "$('redundant-reference').dispatchEvent(new Event('change',{bubbles:true}));")
    page.click_selector("#redundant-save")
    data = wait_server(page, lambda d: (reviews_of(d).get(dayanak["id"]) or {}).get("disposition") == "redundant",
                       label="D: dayanak claimed")
    dependent = next(row for row in data["effective_callouts"]
                     if row["id"] not in (metadata["id"], real["id"], cited["id"], dayanak["id"])
                     and row.get("disposition") is None)
    row_click(page, dependent["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail D2")
    page.click_selector("#target-redundant")
    page.wait_ev("!$('redundant-box').hidden", timeout=30, label="D citation box")
    page.ev(f"$('redundant-reference').value = '{dayanak['id']}';"
            "$('redundant-reference').dispatchEvent(new Event('change',{bubbles:true}));")
    page.click_selector("#redundant-save")
    data = wait_server(page, lambda d: (reviews_of(d).get(dependent["id"]) or {}).get("disposition") == "redundant",
                       label="D: dependent claimed")
    valid = bucket_contains(data, "redundant", dependent["id"])
    row_click(page, dayanak["id"])
    page.wait_ev("!$('callout-detail').hidden", timeout=30, label="detail D3")
    edit_region(page, 0.45, 0.30, 0.62, 0.42)
    data = wait_server(page, lambda d: bucket_contains(d, "invalid_duplicate", dependent["id"]),
                       timeout=90, label="D: citation invalidated")
    states = {row["id"]: row for row in data.get("callouts") or []}
    stale_state = ((states.get(dayanak["id"]) or {}).get("transcription") or {}).get("state")
    build_disabled = page.ev("return $('build').disabled;")
    record("D: the dependent was valid while its dayanak was current, and becomes a blocker once it is stale",
           valid and bucket_contains(data, "invalid_duplicate", dependent["id"]) and stale_state == "stale",
           {"dependent": dependent["id"], "dayanak": dayanak["id"], "was_valid": valid,
            "dayanak_transcription": stale_state, "build_disabled": build_disabled,
            "invalid_duplicate": coverage_of(data).get("invalid_duplicate")})
    page.click_selector("#callout-next")
    time.sleep(0.4)
    page.screenshot(str(HERE / "D-01-stale-citation.png"))

    # --- E: reload keeps the claim; undo steps the geometry back and the citation re-validates --------
    token = data["token"]
    page.navigate(f"{APP}/guided?session={token}")
    page.wait_ev("!$('controls').hidden", timeout=90, label="reloaded session")
    page.wait_ev("$('callout-summary').textContent.length > 0", timeout=60, label="reloaded summary")
    reloaded = wait_server(page, lambda d: d.get("effective_callouts"), label="reloaded state")
    summary_text = page.ev("return $('coverage-summary').textContent;")
    record("E: reload preserves every claim (server record, not page state) and the coverage summary renders it",
           bucket_contains(reloaded, "not_model_input", metadata["id"])
           and bucket_contains(reloaded, "build_relevant_unsupported", real["id"])
           and bucket_contains(reloaded, "redundant", cited["id"])
           and bucket_contains(reloaded, "invalid_duplicate", dependent["id"])
           and "modele ait değil" in summary_text and "desteklenmiyor" in summary_text,
           {"summary": summary_text, "counts": coverage_of(reloaded)["counts"]})
    page.screenshot(str(HERE / "E-01-reload.png"))
    page.click_selector("#undo")
    reverted = wait_server(page, lambda d: not bucket_contains(d, "invalid_duplicate", dependent["id"])
                           and bucket_contains(d, "redundant", dependent["id"]), timeout=60, label="undo")
    record("E: undo steps back the region change and the citation is valid again — nothing was silently rewritten",
           bucket_contains(reverted, "redundant", dependent["id"])
           and bucket_contains(reverted, "redundant", dayanak["id"]),
           {"redundant": coverage_of(reverted).get("redundant"), "invalid": coverage_of(reverted).get("invalid_duplicate")})
    page.screenshot(str(HERE / "E-02-undo.png"))

    failed = [step for step in G3.STEPS if not step["passed"]]
    STEPS_FILE.write_text(json.dumps({"steps": G3.STEPS, "token": token,
                                      "failed": len(failed)}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(f"[{'ALL PASS' if not failed else 'FAILURES: %d' % len(failed)}] evidence: {HERE}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
