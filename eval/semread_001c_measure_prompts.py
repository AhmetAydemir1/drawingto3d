"""001C dev: kalan iki sayfanın V/VE prompt boyutlarını YEREL ölçer (çağrı yok).

Amaç (PLAN-12 §19.3): num_ctx kararını ölçüme dayandırmak. `dev-flange-book-VE`
14121 token ile 12288 ctx'i aştığı için kalan sayfaların prompt'larını önden ölçüyoruz.
Çıktı: prompt byte'ları + kaba token tahmini (ölçülen iki noktadan kalibre: 0.816 tok/byte + ~664
image/template sabiti) + %25 güvenlik payı.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", ROOT / "eval/semread_001b_pilot.py")
pilot = importlib.util.module_from_spec(spec)
sys.modules["pilot"] = pilot
spec.loader.exec_module(pilot)

from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_candidate_reader import prepare_arm_inputs  # noqa: E402
from drawingto3d.semantic_images import open_source  # noqa: E402

result: dict[str, dict] = {}
for page_id in ("dev-flange-elbow", "dev-drawing-2"):
    page = next(row for row in pilot.PAGES if row["page_id"] == page_id)
    source = open_source(ROOT / page["path"])
    observations = observe(ROOT / page["path"])
    for arm in ("V", "VE"):
        bundle = prepare_arm_inputs(source, observations, image_id="image-1", arm=arm,
                                    resize_max_side=pilot.SETTINGS["image_max_side"])
        prompt = pilot.candidate_prompt([bundle["page_image_id"]],
                                        observations=bundle["observations"] or None)
        nbytes = len(prompt.encode("utf-8"))
        est = round(0.816 * nbytes + 664)
        result[f"{page_id}-{arm}"] = {"prompt_bytes": nbytes, "estimate_tokens": est,
                                      "estimate_with_25pct": round(est * 1.25),
                                      "observation_counts": bundle.get("observation_counts")}
        (Path("/Users/aydemir/.hermes/cache/scratch") / f"prompt-{page_id}-{arm}.txt") \
            .write_text(prompt, encoding="utf-8")
        print(f"{page_id}-{arm}: {nbytes} B | ~{est} tok (×1.25: {round(est * 1.25)})", flush=True)

print("JSON:", json.dumps(result, ensure_ascii=False))
