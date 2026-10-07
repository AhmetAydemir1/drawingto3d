"""G12.2 — üretim biçimi paneli kabul koşusu (PLAN-25 §42/§97-8), gerçek Chrome + gerçek girdi olayları.

UX değişti: strateji paneli ve hazırlık kategorisi metinleri yeni. Bu koşu, ÖLÇÜLMÜŞ oturumun (kapsam
tamam, üretim biçimi seçilmemiş) üzerinden kullanıcının yolunu gerçek fare/klavye ile yürür:

```text
A  sayfa açılışında hazırlık listesi "Parçanın ana oluşturma biçimini seç" maddesini gösterir
B  panel dört seçeneği sunar; döndürme "bu sürümde yok" ile SEÇİLEMEZ; uzatma "(önerilir)"
C  karar yokken üretim düğmesi KAPALIDIR (örtük extrude yok)
D  gerçek tıklama + kaydetme → istek /api/guided/strategy'ye gider ve gövde YALNIZ {token, revision, kind}
   taşır (istemci anahtar/sürüm uydurmaz; §36)
E  karar sonrası durum yazısı + üretim düğmesi açılır; gerçek tıklamayla üretim tamamlanır, STEP bağlantısı gelir
```

`Runtime.evaluate` yalnız durumu OKUR ve `fetch`'i gözlemler (istek gövdesini kaydeder); hiçbir karar
komutla verilmez. Kanıt: ekran görüntüleri + `strategy-panel-steps.json`; baskı exit≠0 = düşen adım.

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app     (http://127.0.0.1:8765)
    # chrome: --remote-debugging-port=9222, scratch profil
    # oturum: .venv/bin/python g12_strategy_plate_acceptance.py --prepare-only --store-root out/guided
    ~/.hermes/cache/scratch/cdp-venv/bin/python strategy_panel_acceptance.py <token>
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ACCEPT = HERE.parent / "g12_strategy_plate_acceptance.py"
ROOT = HERE.parents[3]
HARNESS = ROOT / "eval" / "audits" / "20261006-guided-g3-review"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP = G3.APP
record = G3.record
STEPS_FILE = HERE / "strategy-panel-steps.json"
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
    """Ölçülmüş oturumu app'in kendi deposuna yazar; üretim biçimi ve üretim tarayıcıya bırakılır."""
    proc = subprocess.run([str(VENV), str(ACCEPT), "--prepare-only", "--store-root",
                           str(ROOT / "out" / "guided")],
                          capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"prepare failed ({proc.returncode}): {proc.stderr[-400:]}")
    line = [row for row in proc.stdout.splitlines() if row.startswith("{")][-1]
    return json.loads(line)["token"]


def click_box(page: C.Chrome, selector: str) -> None:
    """Gerçek fare tıklaması: öğeyi görünür alana getir, kutusunu oku, ortasına tıkla."""
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def choice_state(page: C.Chrome) -> list[dict]:
    return page.ev("""
      return Array.from(document.querySelectorAll('#strategy-choices label')).map(label => ({
        kind: label.querySelector('input').value,
        label: label.querySelector('span').textContent,
        disabled: label.querySelector('input').disabled}));""")


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
    data = wait_server(page, lambda d: d.get("build_strategy"), label="public strategy state")
    page.screenshot(str(HERE / "S-00-open.png"))

    # --- A: hazırlık listesi yeni kategoriyi ve adı konmuş soruyu gösterir ------------------------
    state = readiness(page)
    questions = state.get("questions") or []
    category = [q for q in questions if q.get("category") == "missing_build_strategy"]
    # Hazırlık listesi sunucu yanıtıyla ASENKRON dolar: metni bekle, sonra oku (yarış değil, sözleşme).
    try:
        page.wait_ev("$('readiness-questions').textContent.indexOf('oluşturma biçimini seç') >= 0",
                     timeout=90, label="strategy question rendered")
        rendered = True
    except TimeoutError:
        rendered = False
    task_text = page.ev("""return Array.from(document.querySelectorAll('#readiness-questions li'))
      .map(row => row.textContent).join(' | ');""")
    record("A: hazırlık listesi 'Parçanın ana oluşturma biçimini seç' maddesini taşır",
           rendered and state.get("ready") is False and bool(category),
           {"categories": state.get("categories"), "tasks": task_text[:200]})

    # --- B: dört seçenek, döndürme kapalı, uzatma önerilir ---------------------------------------
    choices = choice_state(page)
    kinds = [row["kind"] for row in choices]
    revolve = next((row for row in choices if row["kind"] == "revolve_profile"), {})
    extrude = next((row for row in choices if row["kind"] == "extrude_profile"), {})
    status_text = page.ev("return $('strategy-state').textContent;")
    record("B: panel dört seçeneği sunar; döndürme bu sürümde kapalı, uzatma önerilir",
           kinds == ["extrude_profile", "revolve_profile", "multi_view_composite", "unsupported"]
           and revolve.get("disabled") is True and "(bu sürümde yok)" in revolve.get("label", "")
           and extrude.get("disabled") is False and "(önerilir)" in extrude.get("label", "")
           and status_text.startswith("Henüz seçilmedi"),
           {"choices": choices, "status": status_text})
    page.screenshot(str(HERE / "S-01-choices.png"))

    # --- C: karar yokken üretim kapalı ----------------------------------------------------------
    disabled_before = page.ev("return $('build').disabled;")
    record("C: üretim biçimi seçilmeden üretim düğmesi KAPALI (örtük extrude yok)",
           disabled_before is True, {"build_disabled": disabled_before})

    # --- D: gerçek tıklama → /api/guided/strategy, gövde yalnız tür -------------------------------
    # Seçenek düğmesinin kendisi `value` ÖZELLİĞİ taşımaz (attr seçicisi null döner): etikete tıkla.
    click_box(page, "#strategy-choices label:nth-child(1) span")
    time.sleep(0.3)
    picked = page.ev("return (document.querySelector(\"input[name='strategy']:checked\")||{}).value;")
    page.click_selector("#strategy-save")
    data = wait_server(page, lambda d: (d.get("build_strategy") or {}).get("decision")
                       or (d["decisions"].get("build_strategy") or {}).get("kind") == "extrude_profile",
                       label="strategy stored")
    sent = page.ev("return window.__sent.filter(row => row.url.indexOf('/strategy') >= 0);")
    body = json.loads(sent[-1]["body"]) if sent and sent[-1].get("body") else {}
    record("D: kaydetme isteği sunucuya gider ve gövde YALNIZ {token, revision, kind} taşır",
           picked == "extrude_profile" and bool(sent)
           and set(body) == {"token", "revision", "kind"}
           and body["kind"] == "extrude_profile"
           and "strategy_key" not in body and "geometry_version" not in body,
           {"request": sent[-1] if sent else None, "body_keys": sorted(body)})
    stored = (data["decisions"].get("build_strategy") or {})
    record("D: sunucu kararı anahtarıyla ve geometri sürümüyle sabitledi (istemci uydurmadı)",
           stored.get("kind") == "extrude_profile" and len(stored.get("strategy_key") or "") == 64
           and stored.get("geometry_version") == (data.get("geometry") or {}).get("version"),
           {"kind": stored.get("kind"), "key": (stored.get("strategy_key") or "")[:12] + "…",
            "geometry_version": stored.get("geometry_version"),
            "served_version": (data.get("geometry") or {}).get("version")})
    after_text = page.ev("return $('strategy-state').textContent;")
    page.screenshot(str(HERE / "S-02-strategy-saved.png"))

    # --- E: üretim düğmesi açılır, gerçek tıklama üretimi tamamlar --------------------------------
    disabled_after = page.ev("return $('build').disabled;")
    record("E: karar sonrası durum yazısı seçili biçimi söyler ve üretim düğmesi açılır",
           disabled_after is False and after_text.startswith("Seçili:"),
           {"status": after_text, "build_disabled": disabled_after})
    page.click_selector("#build")
    built = wait_server(page, lambda d: d.get("build_status") in ("complete", "failed", "interrupted"),
                        timeout=900, label="build finished")
    # Artefakt URL'i uydurulmaz: sunucunun public durumda İLAN ETTİĞİ adresten çekilir.
    artifact = page.ev_async(f"""const url = {json.dumps(built.get('step') or '')};
      const response = await fetch(url);
      const body = await response.text();
      return {{status: response.status, bytes: body.length, head: body.slice(0, 24), url}};""")
    links = page.ev("return $('links').textContent;")
    record("E: gerçek tıklamayla üretim tamamlandı; STEP artefaktı servis ediliyor",
           built.get("build_status") == "complete" and artifact.get("status") == 200
           and artifact.get("bytes", 0) > 0 and "ISO-10303" in (artifact.get("head") or "")
           and built.get("step"),
           {"status": built.get("build_status"), "artifact": artifact, "step": built.get("step"),
            "links": links[:120]})
    page.screenshot(str(HERE / "S-03-built.png"))

    STEPS_FILE.write_text(json.dumps({"token": token, "steps": G3.STEPS}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    failed = [row for row in G3.STEPS if not row["passed"]]
    print(f"TÜMÜ {'GEÇTİ' if not failed else 'DÜŞTÜ'} {len(G3.STEPS) - len(failed)}/{len(G3.STEPS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
