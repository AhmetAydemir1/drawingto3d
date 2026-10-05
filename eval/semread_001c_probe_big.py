"""001C platform tanı: BÜYÜK VE isteğini verilen num_ctx ile tek seferlik dener (kanıt değil).

Kama olayı (attempt-0003/0004, ctx 20480) ile temiz küçük istek (5 s) arasındaki farkı ayırmak
için: plate-VE'nin gerçek girdisi (2 görsel + tablo) yeniden kurulur, /api/chat'e verilen ctx ve
num_predict ile POST edilir. Çıktı KAYDEDİLMEZ (attempt/defter yok) — yalnız zamanlama + durum.

Kullanım: python eval/semread_001c_probe_big.py --ctx 18432 --predict 32 [--timeout 300]
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", ROOT / "eval/semread_001b_pilot.py")
pilot = importlib.util.module_from_spec(spec)
sys.modules["pilot"] = pilot
spec.loader.exec_module(pilot)

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_candidate_reader import prepare_arm_inputs  # noqa: E402
from drawingto3d.semantic_images import open_source  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--page", default="dev-plate-pocket")
parser.add_argument("--arm", default="VE")
parser.add_argument("--ctx", type=int, required=True)
parser.add_argument("--predict", type=int, default=32)
parser.add_argument("--format", action="store_true",
                    help="üretimdeki gibi yanıt şemasını (format=json_schema) ekle")
parser.add_argument("--timeout", type=float, default=300.0)
args = parser.parse_args()

page = next(row for row in pilot.PAGES if row["page_id"] == args.page)
t0 = time.time()
source = open_source(ROOT / page["path"])
observations = observe(ROOT / page["path"])
bundle = prepare_arm_inputs(source, observations, image_id="image-1", arm=args.arm,
                            resize_max_side=pilot.SETTINGS["image_max_side"])
prompt = pilot.candidate_prompt([bundle["page_image_id"]],
                                observations=bundle["observations"] or None)
images = []
for image in bundle["images"]:
    data = getattr(image, "png", None) or getattr(image, "data", None)
    if not isinstance(data, (bytes, bytearray)):
        raise SystemExit(f"görsel verisi okunamadı: image_id={getattr(image, 'image_id', '?')}")
    images.append(base64.b64encode(bytes(data)).decode("ascii"))
print(f"prep: {time.time()-t0:.1f}s | prompt {len(prompt)} B | {len(images)} görsel", flush=True)

options = {key: value for key, value in pilot.SETTINGS.items()}
options["num_ctx"] = args.ctx
options["num_predict"] = args.predict
payload = {"model": pilot.MODEL, "stream": False, "keep_alive": "1m",
           "messages": [{"role": "user", "content": prompt, "images": images}],
           "options": options}
if args.format:
    payload["format"] = pilot.candidate_json_schema()
request = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"})
t1 = time.time()
try:
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    print(f"TAMAM: {time.time()-t1:.1f}s | done={body.get('done_reason')} "
          f"| prompt_eval={body.get('prompt_eval_count')} | eval={body.get('eval_count')} "
          f"| içerik[:60]={body.get('message', {}).get('content', '')[:60]!r}")
except Exception as exc:  # noqa: BLE001 - tanı aracı
    print(f"KAMA/HATA: {time.time()-t1:.1f}s | {type(exc).__name__}: {exc}")
