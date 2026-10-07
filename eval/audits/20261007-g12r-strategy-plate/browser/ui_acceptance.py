"""G12R — gerçek Chrome kabul koşusu: R-01 (onaydan sonra normal kayıt) + R-02 (bayat kapsam onayı).

Ölçülen yol, kullanıcının kendi yürüyüşüdür; karar komutla verilmez, gerçek fare/klavye kullanılır:

```text
A  hazırlık: kapsam kapalı, üretim biçimi seçilmemiş → üretim düğmesi kapalı
B  gerçek tıklamayla üretim biçimi onayı → sunucu anahtarı ve geometri sürümünü sabitler (§36)
C  R-01: onaydan SONRA kalınlık 20 + "Kalınlığı kaydet" → normal kayıt GEÇER (tarayıcı JSON turu:
   sunucunun `10.0` kanıtı tarayıcıda `10` olur; eskiden bu yüzden reddediliyordu)
C2 R-02 (değer ayağı): kalınlık 20 olunca kalınlığa dayanan "zaten temsil ediliyor" satırı kapsamı
   DÜŞER — onay, onaylandığı DEĞERE bağlıdır; hazırlık o satırı yeniden sorar
D  R-01: profil değişince karar güncelliğini yitirir → hazırlık stratejiyi yine sorar, üretim kapanır;
   profil geri alınır, karar yeniden onaylanır
D2 kalınlık 15'e döner → kalınlığa dayanan onay kendi kendine yeniden geçerli olur (değer yeniden
   sabitlenen değere eşit); hazırlık tümden hazır ve üretim açık
E  R-02 (okuma ayağı): "zaten temsil ediliyor" satırının metni 30,00 yapılır → satırın KENDİ okuması
   değiştiği için onay düşer, üretim kapanır, hazırlık yeni kategoriyi (kapsam kararı) gösterir
F  R-02: aynı satır aynı dayanakla yeniden onaylanır → kapsam yeniden kapanır, üretim açılır
G  gerçek tıklamayla üretim → STEP servis edilir (düzeltmeler üretimi bozmadı, uçtan uca)
```

`Runtime.evaluate` yalnız durumu OKUR ve `fetch`'i gözlemler; metin kutusuna yazı gerçek klavyeyle
girer, düğmelere gerçek fare tıklar. Seçme kutuları (profil/dayanak) için değer + `change` olayı
kullanılır: tarayıcının kendi açılır listesini CDP ile gezmek yerine olay yolu ölçülür (olayın
kendisi ürünün kendi işleyicisini çalıştırır). Kanıt: ekran görüntüleri + `ui-acceptance-steps.json`;
düşen adımda çıkış kodu ≠ 0.

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app     (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222, scratch profil
    ~/.hermes/cache/scratch/cdp-venv/bin/python ui_acceptance.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ACCEPT = HERE.parent / "g12r_strategy_plate_acceptance.py"
ROOT = HERE.parents[3]
HARNESS = ROOT / "eval" / "audits" / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP = G3.APP
record = G3.record
STEPS_FILE = HERE / "ui-acceptance-steps.json"
TIMEOUT = 120.0
VENV = ROOT / ".venv" / "bin" / "python"


def server(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      if (!token) return null;
      return await (await fetch('/api/guided/' + token)).json();""")


def readiness(page: C.Chrome) -> dict:
    return page.ev_async("""
      const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/readiness', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")


def wait_server(page: C.Chrome, predicate, timeout: float = TIMEOUT, label: str = "") -> dict:
    deadline = time.time() + timeout
    data = None
    while time.time() < deadline:
        data = server(page)
        if data and predicate(data):
            return data
        time.sleep(0.4)
    raise TimeoutError(f"server condition not met: {label}")


def prepare_session() -> str:
    """Ölçülmüş oturumu (kapsam kapalı, üretim biçimi seçilmemiş) app'in kendi deposuna yazar."""
    proc = subprocess.run([str(VENV), str(ACCEPT), "--prepare-only", "--store-root",
                           str(ROOT / "out" / "guided")],
                          capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"prepare failed ({proc.returncode}): {proc.stderr[-400:]}")
    line = [row for row in proc.stdout.splitlines() if row.startswith("{")][-1]
    return json.loads(line)["token"]


def click_box(page: C.Chrome, selector: str) -> None:
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def set_control(page: C.Chrome, selector: str, value: str) -> None:
    """Değeri kur ve `change` olayını gerçek olay olarak yay — ürünün kendi işleyicisi çalışır."""
    page.ev(f"""const node = document.querySelector({json.dumps(selector)});
      node.value = {json.dumps(value)};
      node.dispatchEvent(new Event('change', {{bubbles: true}}));""")


def status_text(page: C.Chrome) -> str:
    return page.ev("return $('status').textContent;")


def select_callout_row(page: C.Chrome, label: str) -> bool:
    """Listedeki satırı gerçek tıklamayla seç (etiket metni sunucudan gelen `label`)."""
    index = page.ev(f"""const items = [...document.querySelectorAll('#callout-list li')];
      return items.findIndex(item => item.querySelector('strong').textContent === {json.dumps(label)});""")
    if index is None or index < 0:
        return False
    page.ev(f"document.querySelectorAll('#callout-list li')[{index}].scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(f"#callout-list li:nth-child({index + 1})")
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    time.sleep(0.4)
    return True


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else prepare_session()
    print(f"session: {token}")

    page = C.Chrome(url=f"{APP}/guided?session={token}")
    page.wait_ready()
    page.ev("""window.__sent=[]; const original=window.fetch;
      window.fetch=(target, options)=>{try{window.__sent.push({
        url:String(target), method:(options&&options.method)||'GET',
        body:(options&&options.body)||null});}catch(error){}
        return original(target, options);};""")
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    page.wait_ev("$('strategy-choices').children.length > 0", timeout=120, label="strategy panel")
    state = wait_server(page, lambda d: d.get("build_strategy"), label="public strategy state")
    coverage = (state.get("coverage") or {})
    page.screenshot(str(HERE / "R-00-open.png"))

    # --- A: hazırlık kategorisi ve kapalı üretim düğmesi -----------------------------------------
    ready = readiness(page)
    record("A: kapsam kapalı ama üretim biçimi seçilmemiş — üretim düğmesi kapalı",
           ready.get("ready") is False and (ready.get("categories") or {}).get("missing_build_strategy") == 1
           and page.ev("return $('build').disabled;") is True,
           {"categories": ready.get("categories"), "coverage": coverage.get("counts"),
            "build_disabled": page.ev("return $('build').disabled;")})

    # --- B: gerçek tıklamayla strateji onayı ------------------------------------------------------
    click_box(page, "#strategy-choices label:nth-child(1) span")
    time.sleep(0.3)
    page.click_selector("#strategy-save")
    state = wait_server(page, lambda d: ((d["decisions"].get("build_strategy") or {}).get("kind")
                                         == "extrude_profile"), label="strategy stored")
    stored = state["decisions"]["build_strategy"]
    sent = page.ev("return window.__sent.filter(row => row.url.indexOf('/strategy') >= 0);")
    body = json.loads(sent[-1]["body"]) if sent and sent[-1].get("body") else {}
    record("B: gerçek tıklamayla onay; istek gövdesi yalnız {token, revision, kind}; anahtarı sunucu yazdı",
           bool(sent) and set(body) == {"token", "revision", "kind"}
           and len(stored.get("strategy_key") or "") == 64
           and page.ev("return $('build').disabled;") is False,
           {"kind": stored.get("kind"), "key": (stored.get("strategy_key") or "")[:12] + "…",
            "body_keys": sorted(body)})
    first_key = stored["strategy_key"]

    # --- C: R-01 — onaydan SONRA kalınlık kaydı geçer --------------------------------------------
    page.ev("window.__sent=[];")
    set_control(page, "#thickness", "20")
    click_box(page, "#apply-thickness")
    state = wait_server(page, lambda d: d["decisions"].get("thickness") == 20, label="thickness 20 stored")
    refusal = "oluşturma biçimi yalnız" in status_text(page)
    after = state["decisions"].get("build_strategy") or {}
    record("C: onaydan sonra kalınlık 20 yazıldı — normal kayıt GEÇTİ (tarayıcı JSON turu sahte sayılmıyor)",
           state["decisions"].get("thickness") == 20 and after.get("kind") == "extrude_profile"
           and after.get("strategy_key") == first_key and not refusal,
           {"thickness": state["decisions"].get("thickness"), "strategy_key_kept": after.get("strategy_key") == first_key,
            "status": status_text(page)[:120]})
    page.screenshot(str(HERE / "R-01-thickness-saved.png"))

    # --- C2: R-02 değer ayağı — kalınlığa dayanan onay DEĞER değişince düşer ----------------------
    after_coverage = state.get("coverage") or {}
    value_questions = [q for q in readiness(page).get("questions") or []
                       if q.get("category") == "stale_duplicate_reference"]
    record("C2: kalınlık 20 olunca kalınlığa dayanan onay düştü (değer ayağı; ölçüt artık sürüyor)",
           bool(value_questions),
           {"questions": len(value_questions), "coverage": after_coverage.get("counts"),
            "tasks": [q.get("text") for q in value_questions][:2]})
    page.screenshot(str(HERE / "R-02-value-stale.png"))

    # --- D: R-01 — profil değişince karar güncelliğini yitirir ------------------------------------
    set_control(page, "#profile", "outline_0")
    time.sleep(1.2)          # ürünün yanıtı (karar güncelliğini yitirir) sunucu kaydına düşsün
    stale_readiness = readiness(page)
    stale_rows = [q for q in stale_readiness.get("questions") or []
                  if q.get("category") == "stale_build_strategy"]
    record("D: profil değişti — karar güncelliğini yitirdi ve hazırlık stratejiyi YENİDEN soruyor",
           bool(stale_rows) or stale_readiness.get("ready") is False,
           {"categories": stale_readiness.get("categories"), "stale_rows": len(stale_rows),
            "build_disabled": page.ev("return $('build').disabled;")})
    page.screenshot(str(HERE / "R-01-stale.png"))

    set_control(page, "#profile", "outline_1")
    time.sleep(0.6)
    click_box(page, "#strategy-choices label:nth-child(1) span")
    time.sleep(0.3)
    page.click_selector("#strategy-save")
    state = wait_server(page, lambda d: ((d["decisions"].get("build_strategy") or {}).get("kind")
                                         == "extrude_profile"), label="strategy re-approved")
    back = readiness(page)
    record("D: profil geri alındı, karar yeniden onaylandı — strateji sorusu KAPANDI",
           "stale_build_strategy" not in (back.get("categories") or {}),
           {"categories": back.get("categories"), "build_disabled": page.ev("return $('build').disabled;")})

    # --- D2: kalınlık 15'e döner → kalınlığa dayanan onay yeniden geçerli ------------------------
    set_control(page, "#thickness", "15")
    click_box(page, "#apply-thickness")
    state = wait_server(page, lambda d: d["decisions"].get("thickness") == 15, label="thickness back to 15")
    restored = wait_server(page, lambda d: (d.get("coverage") or {}).get("coverage_complete") is True,
                           label="coverage complete again")
    ready_again = readiness(page)
    record("D2: kalınlık 15'e döndü — onay sabitlendiği değere yeniden eşit; kapsam kapandı, üretim açık",
           (restored.get("coverage") or {}).get("coverage_complete") is True
           and ready_again.get("ready") is True and page.ev("return $('build').disabled;") is False,
           {"coverage": (restored.get("coverage") or {}).get("counts"),
            "categories": ready_again.get("categories")})

    # --- E: R-02 — "zaten temsil ediliyor" satırının metni değişir --------------------------------
    # Etiket istemcide üretilir (`C1`, `C2`…): sıra, panelin KENDİ süzgecidir — sunucunun verdiği
    # etkin liste (`not_model_input` satırları "Modele ait olmayanları göster" kapalıyken gizlenir).
    state = server(page)
    show_ignored = page.ev("return $('callout-show-ignored').checked;")
    visible = [row for row in (state.get("effective_callouts") or [])
               if show_ignored or row.get("disposition") != "not_model_input"]
    redundant = next((row for row in visible if row.get("disposition") == "redundant"
                      and not str(row.get("duplicate_of") or "").startswith("decision:")), None)
    assert redundant is not None, "taze oturumda başka bir satıra dayanan 'zaten temsil ediliyor' satırı yok"
    label = f"C{visible.index(redundant) + 1}"
    label_in_dom = page.ev(f"""return [...document.querySelectorAll('#callout-list li strong')]
      .map(node => node.textContent).includes({json.dumps(label)});""")
    selected = bool(label_in_dom) and select_callout_row(page, label)
    redundant = {**redundant, "label": label}
    title = page.ev("return $('callout-title').textContent;")     # «C8 · makine tespiti»
    record("E: 'zaten temsil ediliyor' satırı listede gerçek tıklamayla seçildi",
           selected and str(title).startswith(redundant["label"]),
           {"label": redundant["label"], "title": title, "reference": redundant.get("duplicate_of")})
    page.ev("$('callout-text').value = '';")
    page.focus_selector("#callout-text")
    page.type_text("30,00")
    click_box(page, "#callout-save")
    state = wait_server(page, lambda d: any(row["callout_id"] == redundant["id"]
                                           for row in (d["decisions"].get("callout_reviews") or [])),
                        label="text stored")
    after_coverage = state.get("coverage") or {}
    after_readiness = readiness(page)
    stale_claim = [q for q in after_readiness.get("questions") or []
                   if q.get("callout_id") == redundant["id"] and q.get("category") == "stale_scope_claim"]
    record("E: metin değişti — satırın KENDİ okuması değiştiği için onay düştü (üretim kapandı)",
           after_coverage.get("coverage_complete") is False
           and redundant["id"] in (after_coverage.get("stale") or [])
           and bool(stale_claim) and page.ev("return $('build').disabled;") is True,
           {"coverage": after_coverage.get("counts"), "stale_claim_questions": len(stale_claim),
            "status": status_text(page)[:120]})
    page.screenshot(str(HERE / "R-02-claim-stale.png"))

    # --- F: R-02 — aynı satır, aynı dayanakla yeniden onaylanır ----------------------------------
    click_box(page, "#target-redundant")          # mevcut kararı geri al
    time.sleep(0.6)
    click_box(page, "#target-redundant")          # yeniden: dayanak kutusunu aç
    time.sleep(0.4)
    options = page.ev("return [...$('redundant-reference').options].map(row => row.value);")
    page.ev(f"""$('redundant-reference').value = {json.dumps(redundant['duplicate_of'])};""")
    click_box(page, "#redundant-save")
    state = wait_server(page, lambda d: (d.get("coverage") or {}).get("coverage_complete") is True,
                        label="coverage closed again")
    final_readiness = readiness(page)
    review = next((row for row in (state["decisions"].get("callout_reviews") or [])
                   if row["callout_id"] == redundant["id"]), {})
    pin = review.get("duplicate_pin") or {}
    record("F: aynı dayanakla yeniden onaylandı — kapsam kapandı ve onay KANITINI sunucu yazdı",
           (state.get("coverage") or {}).get("coverage_complete") is True
           and final_readiness.get("ready") is True and page.ev("return $('build').disabled;") is False
           and pin.get("kind") == "callout" and pin.get("revision") is not None,
           {"reference_option_present": redundant["duplicate_of"] in (options or []),
            "pin_kind": pin.get("kind"), "pin_revision": pin.get("revision"),
            "categories": final_readiness.get("categories")})
    page.screenshot(str(HERE / "R-02-re-approved.png"))

    # --- G: gerçek tıklamayla üretim (uçtan uca) --------------------------------------------------
    page.click_selector("#build")
    built = wait_server(page, lambda d: d.get("build_status") in ("complete", "failed", "interrupted"),
                        timeout=900, label="build finished")
    artifact = page.ev_async(f"""const url = {json.dumps(built.get('step') or '')};
      const response = await fetch(url);
      const body = await response.text();
      return {{status: response.status, bytes: body.length, head: body.slice(0, 24), url}};""")
    record("G: düzeltmelerden sonra gerçek tıklamayla üretim tamamlandı, STEP servis ediliyor",
           built.get("build_status") == "complete" and artifact.get("status") == 200
           and artifact.get("bytes", 0) > 0 and "ISO-10303" in (artifact.get("head") or ""),
           {"status": built.get("build_status"), "artifact": artifact, "step": built.get("step")})
    page.screenshot(str(HERE / "R-03-built.png"))

    STEPS_FILE.write_text(json.dumps({"token": token, "steps": G3.STEPS}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    failed = [row for row in G3.STEPS if not row["passed"]]
    print(f"TÜMÜ {'GEÇTİ' if not failed else 'DÜŞTÜ'} {len(G3.STEPS) - len(failed)}/{len(G3.STEPS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
