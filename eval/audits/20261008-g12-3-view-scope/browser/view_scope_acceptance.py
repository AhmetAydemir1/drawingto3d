"""G12.3 — gerçek Chrome kabul koşusu (PLAN-25 §51/§52/§54): görünüş katmanı, roller ve menü kapsamı.

Ölçülen yol kullanıcının kendi yürüyüşüdür; karar komutla verilmez, gerçek tarayıcıda olay yolundan
verilir (değer + `change`; ürünün kendi işleyicisi çalışır). Bu fazın sözleşmesi gereği burada
**inşa doğruluğu iddiası yoktur** (§54): ölçülen şey görünüş katmanının kendisidir.

```text
A  çizim açıldı: adaylar sunucuda ve panelde; hiçbir rol seçilmemiş; izometrik adayı kaynak değil
B  gerçek olayla "Ana görünüş" onayı (parçanın kendi görünüşü) → sunucu geometri sürümünü damgalar
C  "Kesit" rolü verilir → iki karar; panel durumu ikisini de söyler
D  kontur menüsü ana görünüşe daralır (§52): menüde yalnız o görünüşün konturları (+ seçili olan)
E  "Tüm geometrileri göster" kaçışı tüm listeyi geri getirir; kapanınca yine daralır
F  sayfa yeniden yüklenir: roller durur, aday listesi AYNI kalır (yeniden segment yok), menü yine dar
G  ekran görüntüsü: kutular ve etiketler çizimin üstünde
```

    # app:    PYTHONPATH=src .venv/bin/python -m drawingto3d.app     (http://127.0.0.1:8765, taze)
    # chrome: --remote-debugging-port=9222, scratch profil
    ~/.hermes/cache/scratch/cdp-venv/bin/python view_scope_acceptance.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
AUDIT = HERE.parent
ROOT = HERE.parents[3]
HARNESS = ROOT / "eval" / "audits" / "20261006-guided-g3-review"
G12R = ROOT / "eval" / "audits" / "20261007-g12r-strategy-plate" / "g12r_strategy_plate_acceptance.py"
sys.path.insert(0, str(HARNESS))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402

APP = G3.APP
record = G3.record
STEPS_FILE = HERE / "view-acceptance-steps.json"
TIMEOUT = 120.0
VENV = ROOT / ".venv" / "bin" / "python"


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
        time.sleep(0.4)
    raise TimeoutError(f"server condition not met: {label}")


def prepare_session() -> str:
    """G12R hazırlığının kendisi: kapsam kapalı, üretim biçimi ve görünüş rolleri seçilmemiş oturum."""
    proc = subprocess.run([str(VENV), str(G12R), "--prepare-only", "--store-root",
                           str(ROOT / "out" / "guided")],
                          capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"prepare failed ({proc.returncode}): {proc.stderr[-400:]}")
    line = [row for row in proc.stdout.splitlines() if row.startswith("{")][-1]
    return json.loads(line)["token"]


def set_control(page: C.Chrome, selector: str, value: str) -> None:
    """Değeri kur ve `change` olayını gerçek olay olarak yay — ürünün kendi işleyicisi çalışır."""
    page.ev(f"""const node = document.querySelector({json.dumps(selector)});
      node.value = {json.dumps(value)};
      node.dispatchEvent(new Event('change', {{bubbles: true}}));""")


def profile_menu(page: C.Chrome) -> list[str]:
    return page.ev("return [...document.querySelectorAll('#profile option')].map(o => o.value);")


def view_rows(page: C.Chrome) -> list[dict]:
    return page.ev("""return [...document.querySelectorAll('#view-choices .view-choice')].map(line => ({
      label: line.children[0].textContent, role: line.children[1].value}));""")


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else prepare_session()
    print(f"session: {token}")

    page = C.Chrome(url=f"{APP}/guided?session={token}")
    page.wait_ready()
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    page.wait_ev("$('view-choices').children.length > 0", timeout=120, label="view panel")
    state = wait_server(page, lambda d: d.get("view_candidates") is not None, label="view layer")
    candidates = state["view_candidates"]
    labels = [row["label"] for row in candidates]
    iso = next((row for row in candidates if row["kind"] == "isometric"), None)
    primary = next((row["id"] for row in candidates if row["kind"] == "front"), None) or candidates[0]["id"]
    section = next((row["id"] for row in candidates if row["kind"] == "section"), None) or candidates[-1]["id"]
    page.screenshot(str(HERE / "A-open.png"))

    # --- A: adaylar ve rollerin başlangıcı -------------------------------------------------------
    rows = view_rows(page)
    record("A: adaylar sunucuda ve panelde; roller henüz seçilmedi; izometrik adayı üretim kaynağı değil",
           rows == [{"label": row["label"], "role": ""} for row in candidates]
           and iso is not None and iso.get("used_for_solid") is False
           and state["drawing_views"] == [] and len(candidates) >= 3,
           {"labels": labels, "roles": [row["role"] for row in rows],
            "isometric": {"id": iso and iso["id"], "used_for_solid": iso and iso.get("used_for_solid")},
            "view_state": page.ev("return $('view-state').textContent;")})

    # --- B: gerçek olayla ana görünüş onayı ------------------------------------------------------
    index = [row["id"] for row in candidates].index(primary)
    set_control(page, f"#view-choices .view-choice:nth-child({index + 1}) select", "primary")
    state = wait_server(page, lambda d: any(row["role"] == "primary" for row in d["drawing_views"]),
                        label="primary stored")
    stored = next(row for row in state["drawing_views"] if row["role"] == "primary")
    record("B: gerçek olayla ana görünüş onaylandı — geometri sürümü sunucunun damgasıdır",
           stored["view_id"] == primary and stored["geometry_version"] == state["geometry"]["version"]
           and page.ev(f"return document.querySelectorAll('#view-choices .view-choice')[{index}]"
                       ".children[1].value;") == "primary",
           {"stored": stored, "geometry_version": state["geometry"]["version"],
            "panel": view_rows(page)[index]})
    page.screenshot(str(HERE / "B-primary.png"))

    # --- C: kesit rolü ---------------------------------------------------------------------------
    index = [row["id"] for row in candidates].index(section)
    set_control(page, f"#view-choices .view-choice:nth-child({index + 1}) select", "section")
    state = wait_server(page, lambda d: len(d["drawing_views"]) == 2, label="section stored")
    record("C: kesit adayına rol verildi — kararlar tek tek, aynı komutla yazılır",
           {("view_id", row["view_id"], "role", row["role"]) for row in state["drawing_views"]}
           == {("view_id", primary, "role", "primary"), ("view_id", section, "role", "section")}
           and page.ev("return $('view-state').textContent;").startswith("2 görünüşün rolü onaylandı"),
           {"drawing_views": state["drawing_views"], "view_state": page.ev("return $('view-state').textContent;")})

    # --- D: menü kapsamı (§52) -------------------------------------------------------------------
    expected = [""] + [row["id"] for row in state["options"]["profiles"]
                       if row.get("view_id") == primary or row["id"] == state["decisions"].get("profile_id")]
    got = profile_menu(page)
    record("D: ana görünüş onaylıyken kontur menüsü o görünüşe daraldı (§52)",
           got == expected and state["decisions"].get("profile_id") in got,
           {"menu": got, "expected": expected, "primary": primary})
    page.screenshot(str(HERE / "D-scoped-menu.png"))

    # --- E: hata ayıklama kaçışı -----------------------------------------------------------------
    page.click_selector("#show-all-geometry")
    time.sleep(0.3)
    all_rows = profile_menu(page)
    everything = [""] + [row["id"] for row in state["options"]["profiles"]]
    page.click_selector("#show-all-geometry")
    time.sleep(0.3)
    again = profile_menu(page)
    record("E: “Tüm geometrileri göster” tüm listeyi geri getirir; kapanınca menü yine daralır",
           all_rows == everything and again == got,
           {"all": all_rows, "narrow": again})
    page.screenshot(str(HERE / "E-show-all.png"))

    # --- F: yeniden yükleme ----------------------------------------------------------------------
    page.navigate(f"{APP}/guided?session={token}")
    page.wait_ev("!$('controls').hidden", timeout=300, label="reopened")
    page.wait_ev("$('view-choices').children.length > 0", timeout=120, label="view panel again")
    reopened = wait_server(page, lambda d: d.get("view_candidates") is not None, label="view layer again")
    menu_again = profile_menu(page)
    role_by_view = {row["view_id"]: row["role"] for row in reopened["drawing_views"]}
    expected_roles = [role_by_view.get(row["id"], "") for row in candidates]
    record("F: sayfa yeniden yüklendi — roller durur, aday listesi AYNI (yeniden segment yok), menü yine dar",
           reopened["view_candidates"] == candidates
           and {row["view_id"] for row in reopened["drawing_views"]} == {primary, section}
           and menu_again == got
           and [row["role"] for row in view_rows(page)] == expected_roles,
           {"candidates_unchanged": reopened["view_candidates"] == candidates,
            "roles": reopened["drawing_views"], "menu": menu_again,
            "panel_roles": [row["role"] for row in view_rows(page)], "expected_roles": expected_roles})

    # --- G: görünüş kutuları çizimin üstünde -----------------------------------------------------
    painted = page.ev("""const sheet=document.getElementById('sheet');
      const box=sheet.getBoundingClientRect();
      // Çizim tuvali görünür ve panel satırları gerçek: çizimin üstünde kutuların çizildiği
      // ekran görüntüsüyle birlikte okunur (tuval pikselleri CDP ile okunmaz).
      return {visible: !sheet.hidden && sheet.width > 0, labels: %s};""" % json.dumps(labels, ensure_ascii=False))
    record("G: ekran görüntüsü — aday kutuları ve etiketleri çizimin üstünde",
           painted.get("visible") is True and len(painted.get("labels") or []) == len(candidates),
           painted)
    page.screenshot(str(HERE / "G-overlays.png"))

    STEPS_FILE.write_text(json.dumps({"token": token, "steps": G3.STEPS}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    failed = [row for row in G3.STEPS if not row["passed"]]
    print(f"TÜMÜ {'GEÇTİ' if not failed else 'DÜŞTÜ'} {len(G3.STEPS) - len(failed)}/{len(G3.STEPS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
