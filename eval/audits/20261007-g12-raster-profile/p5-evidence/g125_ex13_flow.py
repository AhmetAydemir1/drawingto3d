"""Exercise 13 (raster) — ürün akışı: create → önerileri onayla → build. Gerçek blocker'ı yazar.

Kullanım: .venv/bin/python g125_ex13_flow.py
Çıktı: ~/.hermes/cache/scratch/g125-ex13-flow.log
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import guided  # noqa: E402

LOG = Path.home() / ".hermes/cache/scratch/g125-ex13-flow.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
out = open(LOG, "w")


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line, flush=True)
    out.write(line + "\n")
    out.flush()


def brief(value, limit=160):
    text = json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


sheet = (ROOT / "examples/pdf with steps/4/Exercise 13.PNG").read_bytes()
store = guided.GuidedStore(Path(tempfile.mkdtemp(prefix="g125-ex13-")) / "store")

t0 = time.time()
opened = store.create(sheet)
say(f"== create {time.time()-t0:.1f}s")
say("== archetype:", brief(opened.get("archetype"), 220))
say("== proposals:", len(opened.get("proposals", [])))
for item in opened.get("proposals", []):
    say(f"   {item['field']:26} conf={item.get('confidence','?'):8} value={brief(item.get('value'), 110)}")
    ev = item.get("evidence") or {}
    if ev:
        say(f"   {'':26} evidence={brief(ev, 150)}")

token = opened["token"]

say("== readiness (önay öncesi):")
try:
    ready0 = store.readiness(token)
    say("   ", brief(ready0, 400))
except Exception as exc:  # noqa: BLE001
    say("   readiness hata:", exc)

say("== accept-all:")
try:
    accepted = store.accept(token, opened["revision"])
    say("   revision:", accepted["revision"])
    say("   decisions:", brief(accepted["decisions"], 700))
except Exception as exc:  # noqa: BLE001
    say("   ACCEPT HATA:", type(exc).__name__, exc)

say("== readiness (onay sonrası):")
try:
    ready1 = store.readiness(token)
    say("   ", brief(ready1, 700))
except Exception as exc:  # noqa: BLE001
    say("   readiness hata:", exc)

say("== build:")
t1 = time.time()
try:
    current = store.load(token)
    result = store.build(token, current["revision"])
    build = result.get("build") or {}
    say(f"   build {time.time()-t1:.1f}s status={build.get('status')} error={brief(build.get('error'), 500)}")
    say("   build folder:", build.get("folder"))
    folder = Path(build.get("folder") or "")
    if folder.exists():
        say("   folder içeriği:", sorted(p.name for p in folder.iterdir()))
        plan_file = folder / "plan.json"
        if plan_file.exists():
            plan = json.loads(plan_file.read_text())
            params = plan.get("parameters") or {}
            say("   plan parametreleri:")
            for key, value in list(params.items())[:40]:
                say(f"      {key:28} {brief(value, 120)}")
            say("   plan operasyonları:", brief(plan.get("operations"), 400))
        geom = folder / "geometry.json"
        if geom.exists():
            say("   geometry:", brief(json.loads(geom.read_text()), 400))
except Exception as exc:  # noqa: BLE001
    say("   BUILD HATA:", type(exc).__name__, exc)

say("== log kuyruğu (son 12):")
record = store.load(token)
for row in (record.get("log") or [])[-12:]:
    say("   ", brief({k: row.get(k) for k in ("actor", "action", "field", "note", "value")}, 220))

out.close()
print("yazıldı:", LOG)
