"""SEMREAD-001D — static preflight (PLAN-19 §4/§11/§49; PLAN-18 §32–§41 karşılığı).

Numaralandırma notu: kod içindeki `§` atıfları kapı tanımlarının yazıldığı PLAN-18
numaralandırmasını izler; PLAN-19'daki karşılıkları §4 (static preflight kanıtı), §11
(pre-dispatch invariant) ve §49 (Round 1 öncesi son acceptance listesi)'dir.

Canlı inference öncesi **0 inference** ile kapanan statik kapı (dördüncü adımın ön koşulu):

* §33 kimlik: dört Round-1 hücresinin statik manifesti current kimlikleri taşımalı —
  experiment `semread-001d`, schema `semread-candidates/3`, reader `semread-candidate-reader/3`,
  contract `semread-001d-run-contract/2` (ölçümlü pre-inference `num_ctx` revizyonu; `/1`e karşı
  bu kapı KIRMIZI verdi: flange-book-VE 23.436 > 22.528 — eksik 908) + current producer/preprocessing
  identity; eski kimlikle gönderim bloğu (`contract_identity_block`) boş olmalı.
* §34 bütçe: dev `0/12`, final `0/20` — Round 1 öncesi tam olarak sıfır.
* §35 runtime: model etiketi, digest ve runtime sürümü beklenenle birebir (yerel Ollama meta
  verisi: `/api/version` + `/api/tags`; **inference değildir** — kapı zaten gönderim öncesi aynı
  denetimi yapar); sunucu okunamazsa çağrı yoktur (fail-closed).
* §36 paylaşımlı ayar: `generation_settings(V) == generation_settings(VE)`; istek gövdesinin
  `options`'ı da dört hücrede aynı olmalı.
* §37/§38 prompt-context: dört hücre için prompt byte/token tahmini + görüntü byte'ları + gözlem
  satırları **model çağrılmadan** ölçülür; kapı `tahmin + NUM_PREDICT <= NUM_CTX`. Tahmin,
  `eval/semread_001c_measure_prompts.py`nin iki ölçülmüş noktadan kalibre ettiği orandır
  (0.816 tok/byte + 664): kalibrasyon noktaları iki VE hücresidir, yani VE hücrelerinde sapma
  ~%1–2'dir ve V hücrelerinde tahmin ölçümün üzerinde kalır (güvenli yön). 001C'nin ölçülmüş
  `prompt_eval_count` değerleri **historical kanıt** olarak rapora girer ama kapı onlarla değil
  güncel prompt'la hesaplanır.
* §39/§49 context fail: kanıt hücre + tahmin + gerekli ctx + mevcut ctx + eksik olarak raporlanır;
  kör `num_ctx` artışı yoktur.
* §40 structured-output: istek gövdesi tek kurucudan (`_chat_request`, gönderilmez) kurulur;
  `format` alanı **json-schema** yolundan tam şemayı taşır (`anyOf` bilinçli olarak yok — schema
  yalnız desteklenen anahtarları kullanır) ve dört hücrede şema byte'ı aynıdır. Semantik inference
  harcanmaz.
* §31/§41 dry-run: `--pages` Round-1 filtresiyle `planned_real_calls == 4` ve dört hücre `call`.
* §52 P3: girişler kurulu ve yeniden türetimle birebir (prepared-input cache == yeniden kurulan
  kayıt), V/VE ham sayfa byte'ı aynı, VE kanıtı ayrı hash'li, 001C closure `--verify` **45/45**.

Araç **salt-okurdur**: defter kurmaz, gönderim yapmaz, bütçe harcamaz; `--write` yalnız
`corpus/static-preflight.json` yazar (corpus katmanı — defter değil; §27 dev-report deseniyle aynı).
Girdi hazırlamanın kendisi (render/gözlem/resize/hash) inference değildir (§38); tek ağ erişimi
yerel metadata okumasıdır.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pilot = _load_module("semread_001d_preflight_pilot", ROOT / "eval" / "semread_001b_pilot.py")
# §35 Round-1 deklarasyonu tek kaynakta yaşar (inputs aracı) — kopya literal yok.
_inputs = _load_module("semread_001d_preflight_inputs", ROOT / "eval" / "semread_001d_inputs.py")

from drawingto3d.llama import _chat_request  # noqa: E402 - istek gövdesinin tek kurucusu

EXPERIMENT = "semread-001d"
SCHEMA = "semread-001d-static-preflight/1"
RECORD_NAME = "static-preflight.json"
PLAN_PATH = ROOT / "docs" / "PLAN-19.md"

# PLAN-18 §33 beyanı (numaralandırma notu: kapı tanımları PLAN-18 §32–§41'de yaşar; PLAN-19
# karşılığı §4/§11/§49): bu beklenen kimlikler burada **bilinçli olarak** pinlidir (sessizce geçmesin).
EXPECTED_VERSIONS = {"contract_version": "semread-001d-run-contract/2",
                     "schema_version": "semread-candidates/3",
                     "reader_version": "semread-candidate-reader/3"}

# §40: `anyOf` bilinçli olarak yok; şema bu birleşim/başvuru anahtarlarını kullanmamalı.
UNSUPPORTED_SCHEMA_KEYS = ("anyOf", "oneOf", "allOf", "$ref", "$defs", "definitions", "not",
                           "if", "then", "else", "patternProperties")

# §37 kalibrasyonu — `eval/semread_001c_measure_prompts.py` (iki ölçülmüş nokta: plate-VE ve
# flange-VE prompt'ları). `%25 pay` raporlanır; kapı ham tahminle kurulur (001C'de `num_ctx`
# kararı da ölçülen değerlerle verilmişti, ölçümün üstüne ikinci bir pay eklenmemişti).
ESTIMATE_SLOPE = 0.816
ESTIMATE_INTERCEPT = 664
ESTIMATE_UPLIFT = 1.25

# §52 dry-run beklenen hücre kümesi: dört Round-1 hücresi (§57/§46).
ROUND1_CELLS = tuple((page_id, arm) for page_id in _inputs.ROUND1_PAGES for arm in pilot.ARMS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _sha256_json(payload) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def estimate_tokens(prompt_bytes: int) -> int:
    """Prompt byte'ından token tahmini (§37 kalibrasyonu — tek yer)."""
    return round(ESTIMATE_SLOPE * prompt_bytes + ESTIMATE_INTERCEPT)


def round1_pages() -> tuple[dict, ...]:
    """Round-1 sayfalarının pilot kayıtları — deklarasyon ile corpus çelişirse durur (drift)."""
    pages = {page["page_id"]: page for page in pilot.PAGES}
    missing = [page_id for page_id in _inputs.ROUND1_PAGES if page_id not in pages]
    if missing:
        raise SystemExit(f"Round 1 sayfası pilot PAGES'te yok: {missing} (ROUND1_PAGES drifti)")
    return tuple(pages[page_id] for page_id in _inputs.ROUND1_PAGES)


# ------------------------------------------------------------------ statik hücre kaydı


def _cached_input_record(page: dict, arm: str) -> dict | None:
    """Kanonik prepared-input kaydını **salt-okur** oku (kurulum inputs aracının işidir)."""
    path = pilot.PREPARED_INPUT_DIR / f"{page['page_id']}-{arm}.json"
    if not path.exists():
        return None
    blob = pilot.read_json(path)
    if not isinstance(blob, dict):
        return None
    return blob


def _historical_measurement(page_id: str, arm: str) -> dict | None:
    """001C'nin ölçülmüş prompt değerleri (HISTORICAL — farklı prompt/sözleşme; kapı değil)."""
    try:
        attempts = sorted((pilot.LAB_ROOT / "semread-001c" / "attempts" / f"{page_id}-{arm}")
                          .glob("attempt-*/resources.json"))
        measured = None
        for path in reversed(attempts):
            stats = (pilot.read_json(path) or {}).get("stats") or {}
            if isinstance(stats.get("prompt_eval_count"), int):
                measured = stats["prompt_eval_count"]
                break
        record = pilot.read_json(pilot.LAB_ROOT / "semread-001c" / "corpus" / "prepared-inputs"
                                 / f"{page_id}-{arm}.json") or {}
        prompt_bytes = (record.get("record") or {}).get("prompt_bytes")
        if measured is None and prompt_bytes is None:
            return None
        return {"experiment": "semread-001c", "prompt_bytes": prompt_bytes,
                "measured_prompt_eval_count": measured,
                "estimate_on_001c_prompt": (estimate_tokens(prompt_bytes)
                                            if prompt_bytes is not None else None),
                "note": "HISTORICAL (001C prompt/sözleşmesi) — bilgi amaçlı; kapı 001D tahminiyle"}
    except Exception:  # noqa: BLE001 - historical kanıt yoksa rapor dürüstçe `null` kalır
        return None


def build_cell(page: dict, arm: str, *, bundle: dict, prompt: str) -> dict:
    """Bir Round-1 hücresinin statik manifesti + prompt/context ölçümü (gönderim yok)."""
    images = [image.png for image in bundle["images"]]
    labels = [image.image_id for image in bundle["images"]]
    generation = pilot.generation_settings(arm)
    body, request = _chat_request(  # tek kurucu; gövde üretilir, gönderilmez
        model=pilot.MODEL, prompt=prompt, images=images,
        temperature=pilot.SETTINGS["temperature"], num_predict=pilot.NUM_PREDICT,
        num_ctx=pilot.SETTINGS["num_ctx"], keep_alive=pilot.SETTINGS["keep_alive"],
        response_format=pilot.candidate_json_schema(), image_max_side=pilot.IMAGE_MAX_SIDE,
        timeout=float(pilot.MODEL_TIMEOUT_SECONDS), image_labels=labels,
        images_layout=pilot.SETTINGS["images_layout"],
        image_label_prefix=pilot.SETTINGS["image_label_prefix"],
        repeat_penalty=generation["repeat_penalty"], repeat_last_n=generation["repeat_last_n"])
    payload = json.loads(body)
    prompt_bytes = len(prompt.encode("utf-8"))
    estimate = estimate_tokens(prompt_bytes)
    num_ctx = pilot.SETTINGS["num_ctx"]
    num_predict = pilot.NUM_PREDICT
    cached = _cached_input_record(page, arm)
    cached_record = (cached or {}).get("record")
    derived_record = pilot.prediction_input_record(page, arm, bundle=bundle, prompt=prompt)
    return {
        "page_id": page["page_id"], "arm": arm, "phase": "dev",
        "experiment": pilot.EXPERIMENT_NAME,
        "schema_version": pilot.CANDIDATE_SCHEMA_VERSION,
        "reader_version": pilot.CANDIDATE_READER_VERSION,
        "contract_version": pilot.CONTRACT_VERSION,
        "producer_identity": pilot.producer_identity(),
        "preprocessing_identity": pilot.preprocessing_identity(),
        "input_identity": pilot.input_identity(page),
        "prediction_input_identity": pilot.prediction_input_identity(cached_record),
        "prediction_input_cache_key": pilot.prediction_input_cache_key(page, arm),
        "cached_input_key_matches": cached is not None and cached.get("key") == pilot.prediction_input_cache_key(page, arm),
        "cached_record_matches_rebuild": cached_record == derived_record,
        "cached_contract_version": (cached_record or {}).get("contract_version"),
        "generation_signature": _sha256_json(generation),
        "generation_settings": generation,
        "prompt": {"bytes": prompt_bytes, "chars": len(prompt),
                   "sha256": _sha256_text(prompt),
                   "estimate_tokens": estimate,
                   "estimate_method": (f"{ESTIMATE_SLOPE} tok/byte + {ESTIMATE_INTERCEPT} "
                                       "(semread_001c_measure_prompts kalibrasyonu)")},
        "images": [{"image_id": entry.get("image_id"), "sent_bytes": entry.get("sent_bytes"),
                    "sent_sha256": entry.get("sent_sha256"),
                    "sent_px": [entry.get("sent_width_px"), entry.get("sent_height_px")],
                    "resize": entry.get("resize")} for entry in request["images"]],
        "observation_counts": bundle.get("observation_counts"),
        "observation_rows": len(bundle.get("observations") or []),
        "context": {"num_ctx": num_ctx, "num_predict": num_predict,
                    "estimate_plus_predict": estimate + num_predict,
                    "headroom": num_ctx - (estimate + num_predict),
                    "conservative_headroom": num_ctx - (round(estimate * ESTIMATE_UPLIFT)
                                                        + num_predict),
                    "gate_ok": estimate + num_predict <= num_ctx},
        "request": {"request_sha256": request["request_sha256"],
                    "request_bytes": request["request_bytes"],
                    "prompt_sha256": request["prompt_sha256"], "prompt_chars": request["prompt_chars"],
                    "format_is_json_schema": isinstance(payload.get("format"), dict),
                    "format_sha256": _sha256_json(payload.get("format")),
                    "options": request["options"]},
        "historical_001c": _historical_measurement(page["page_id"], arm),
    }


def measure_round1() -> dict:
    """Dört Round-1 hücresini model çağırmadan ölç (sayfa başına gözlem **bir kez**)."""
    cells: list[dict] = []
    for page in round1_pages():
        source_path = pilot.ROOT / page["path"]
        source = pilot.open_source(source_path)
        observations = pilot.observe(source_path)
        for arm in pilot.ARMS:
            bundle = pilot.prepare_arm_inputs(source, observations, image_id=pilot.PAGE_IMAGE_ID,
                                              arm=arm, resize_max_side=pilot.IMAGE_MAX_SIDE)
            prompt = pilot.candidate_prompt([pilot.PAGE_IMAGE_ID],
                                            observations=bundle["observations"] or None)
            cells.append(build_cell(page, arm, bundle=bundle, prompt=prompt))
    return {"cells": cells}


# ------------------------------------------------------------------ kapılar


def dry_run_plan() -> dict:
    """§31/§41: Round-1 filtresiyle dry-run — `planned_real_calls == 4` ve dört hücre `call`."""
    plan = pilot.run_live("dev", dry_run=True, pages=tuple(_inputs.ROUND1_PAGES))["plan"]
    calls = {(cell["page_id"], cell["arm"]) for cell in plan["cells"] if cell.get("action") == "call"}
    actions = {f"{cell['page_id']}-{cell['arm']}": cell.get("action") for cell in plan["cells"]}
    return {"planned_real_calls": plan["planned_real_calls"], "remaining_phase_budget":
            plan["remaining_phase_budget"], "actions": actions, "call_cells": sorted(calls),
            "expected_cells": sorted(ROUND1_CELLS),
            "ok": plan["planned_real_calls"] == 4 and calls == set(ROUND1_CELLS)}


def closure_verify() -> dict:
    """§52: 001C closure doğrulayıcısı (alt süreç, salt-okur) — 45/45 beklenir."""
    process = subprocess.run([sys.executable, str(ROOT / "eval" / "semread_001c_closure.py"),
                              "--verify"], cwd=str(ROOT), capture_output=True, text=True,
                             timeout=600)
    match = re.search(r"(\d+)/(\d+) artifact birebir", process.stdout)
    checked, total = (int(match.group(1)), int(match.group(2))) if match else (None, None)
    return {"ok": process.returncode == 0 and checked == total and total is not None,
            "checked": checked, "total": total, "exit_code": process.returncode,
            "tail": process.stdout.strip().splitlines()[-1] if process.stdout.strip() else ""}


def run_preflight() -> dict:
    """Tüm statik kapıları koş; yazmaz (rapor `--write` ile `corpus/static-preflight.json`a)."""
    pilot.use_experiment(EXPERIMENT)
    checks: list[dict] = []

    def add(check_id: str, ok: bool, detail: str, **extra) -> None:
        checks.append({"check": check_id, "ok": bool(ok), "detail": detail, **extra})

    # §33 kimlik (statik): beklenen sürümler + blok devrede değil.
    versions = {"contract_version": pilot.CONTRACT_VERSION,
                "schema_version": pilot.CANDIDATE_SCHEMA_VERSION,
                "reader_version": pilot.CANDIDATE_READER_VERSION}
    block = pilot.contract_identity_block()
    add("identity_current", versions == EXPECTED_VERSIONS and block is None,
        f"versions={versions} · contract_identity_block={block}", versions=versions, block=block)

    # §31/§41 dry-run.
    plan = dry_run_plan()
    add("dry_run_planned_calls", plan["ok"],
        f"planned_real_calls={plan['planned_real_calls']} · actions={plan['actions']}", plan=plan)

    # §34 bütçe.
    budget = pilot.budget_report()
    budget_ok = (budget["dev_used"] == 0 and budget["final_used"] == 0
                 and budget["dev_limit"] == 12 and budget["final_limit"] == 20
                 and not budget["over_budget"])
    add("budget_zero", budget_ok,
        f"dev {budget['dev_used']}/{budget['dev_limit']} · final {budget['final_used']}/"
        f"{budget['final_limit']} · over_budget={budget['over_budget']}", budget=budget)

    # §35 runtime (yerel metadata; inference değil).
    runtime = pilot.runtime_identity()
    canonical = runtime.get("model_canonical") or {}
    runtime_ok = (runtime.get("error") is None and runtime.get("version") == pilot.EXPECTED_RUNTIME
                  and canonical.get("name") == pilot.MODEL
                  and canonical.get("digest") == pilot.EXPECTED_DIGEST)
    add("runtime_exact", runtime_ok,
        f"runtime={runtime.get('version')} (beklenen {pilot.EXPECTED_RUNTIME}) · model="
        f"{canonical.get('name')} · digest={(canonical.get('digest') or 'yok')[:12]}… · hata="
        f"{runtime.get('error')}", runtime=runtime)

    # §36 paylaşımlı ayar (saf).
    v_settings = pilot.generation_settings("V")
    ve_settings = pilot.generation_settings("VE")
    add("shared_settings", v_settings == ve_settings,
        "generation_settings(V) == generation_settings(VE)", v=v_settings, ve=ve_settings)

    # §37/§38/§40 ölçüm zinciri + §52 girdi güncelliği (ağır kısım; gönderim yok).
    measured = measure_round1()
    cells = measured["cells"]
    gate_failures = [{ "cell": f"{cell['page_id']}-{cell['arm']}",
                       "prompt_tokens": cell["prompt"]["estimate_tokens"],
                       "required_ctx": cell["context"]["estimate_plus_predict"],
                       "current_ctx": cell["context"]["num_ctx"],
                       "deficit": cell["context"]["estimate_plus_predict"] - cell["context"]["num_ctx"]}
                     for cell in cells if not cell["context"]["gate_ok"]]
    add("prompt_context_gate", not gate_failures,
        ("dört hücre: tahmin + NUM_PREDICT <= NUM_CTX" if not gate_failures
         else f"context kapısı düştü: {gate_failures}"), failures=gate_failures,
        cells=[{"cell": f"{cell['page_id']}-{cell['arm']}", **cell["context"],
                "prompt_bytes": cell["prompt"]["bytes"]} for cell in cells])

    request_options = [json.dumps(cell["request"]["options"], sort_keys=True) for cell in cells]
    formats = {cell["request"]["format_sha256"] for cell in cells}
    schema_ok = (len(set(request_options)) == 1 and len(formats) == 1
                 and all(cell["request"]["format_is_json_schema"] for cell in cells))
    add("shared_request_options", schema_ok,
        f"options tek imza mı: {len(set(request_options)) == 1} · format json-schema: "
        f"{all(cell['request']['format_is_json_schema'] for cell in cells)} · format sha tek: "
        f"{len(formats) == 1}")

    # §40 şema statik denetimi: desteklenmeyen birleşim anahtarı yok.
    schema = pilot.candidate_json_schema()
    found = sorted({key for key in _schema_keys(schema) if key in UNSUPPORTED_SCHEMA_KEYS})
    add("structured_output_static", not found and schema_ok,
        f"desteklenmeyen anahtar: {found or 'yok'} · şema sha={_sha256_json(schema)[:16]}… "
        "(gövde kuruldu, gönderilmedi; semantik inference yok)")

    # §36/§37/§52 girdi katmanı: V/VE ham byte aynı, VE kanıtı ayrı, cache == yeniden türetim.
    raw_pages: list[dict] = []
    for page in round1_pages():
        v_cell = next(cell for cell in cells if cell["page_id"] == page["page_id"] and cell["arm"] == "V")
        ve_cell = next(cell for cell in cells if cell["page_id"] == page["page_id"] and cell["arm"] == "VE")
        v_raw = v_cell["images"][0]["sent_sha256"]
        ve_raw = ve_cell["images"][0]["sent_sha256"]
        page_png = pilot.PAGES_DIR / f"{page['page_id']}.png"
        identity = pilot.read_json(pilot.CORPUS_DIR / _inputs.RECORD_NAME) or {}
        recorded = next((row for row in (identity.get("pages") or [])
                         if row.get("page_id") == page["page_id"]), {})
        raw_pages.append({
            "page_id": page["page_id"],
            "v_ve_raw_bytes_identical": v_raw == ve_raw,
            "ve_evidence_images": len(ve_cell["images"]),
            "ve_evidence_hashes": [entry["sent_sha256"] for entry in ve_cell["images"][1:]],
            "raw_png_sha256_matches_record": (page_png.exists()
                                              and recorded.get("raw_page", {}).get("sha256")
                                              == _sha256_bytes(page_png.read_bytes())),
        })
    pieces = (("V/VE ham byte aynı", all(row["v_ve_raw_bytes_identical"] for row in raw_pages)),
              ("sayfa PNG == kayıt", all(row["raw_png_sha256_matches_record"] for row in raw_pages)),
              ("cache == yeniden türetim", all(cell["cached_record_matches_rebuild"]
                                               for cell in cells)),
              ("cache anahtarı == producer identity", all(cell["cached_input_key_matches"]
                                                          for cell in cells)))
    inputs_current = all(ok for _, ok in pieces)
    add("inputs_current", inputs_current,
        " · ".join(f"{'✓' if ok else '✗'} {name}" for name, ok in pieces), pages=raw_pages,
        rebuild=[{"cell": f"{cell['page_id']}-{cell['arm']}",
                  "cached_matches": cell["cached_record_matches_rebuild"],
                  "key_matches": cell["cached_input_key_matches"],
                  "cached_contract_version": cell["cached_contract_version"]} for cell in cells])

    # §52 closure.
    closure = closure_verify()
    add("closure_verifier", closure["ok"],
        f"001C closure {closure['checked']}/{closure['total']} (exit {closure['exit_code']})",
        closure=closure)

    fail_open = [check["check"] for check in checks if not check["ok"]]
    return {
        "schema": SCHEMA, "created_at": _now(), "experiment": EXPERIMENT,
        "plan": {"path": "docs/PLAN-19.md",
                 "sha256": _sha256_bytes(PLAN_PATH.read_bytes()) if PLAN_PATH.exists() else None},
        "inference_calls": 0,
        "versions": EXPECTED_VERSIONS, "identities": {"producer_identity": pilot.producer_identity(),
                                                      "preprocessing_identity": pilot.preprocessing_identity()},
        "checks": checks, "ok": not fail_open, "failed": fail_open,
        "round1": {"cells": cells, "planned_real_calls": plan["planned_real_calls"]},
        "budget": budget, "runtime": runtime,
        "honesty_note": ("Statik preflight: hiçbir model çağrısı yapılmadı (0 inference) ve defter "
                         "kurulmadı. Round 1 gönderimi ayrıca P4 kapısını (focused süit + gates "
                         "34/34 + closure + D regression) gerektirir; bu rapor onu yetkilendirmez, "
                         "yalnız statik kapıları kanıtlar. Tek ağ erişimi yerel Ollama meta "
                         "verisidir (kimlik denetimi — inference değil)."),
    }


def _schema_keys(node) -> set[str]:
    """Şema ağacındaki JSON anahtarları (dict anahtarları; liste içlerine inilir)."""
    keys: set[str] = set()
    if isinstance(node, dict):
        keys.update(node.keys())
        for value in node.values():
            keys |= _schema_keys(value)
    elif isinstance(node, list):
        for value in node:
            keys |= _schema_keys(value)
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="raporu corpus/static-preflight.json'a da yaz (salt-okur koşu)")
    args = parser.parse_args(argv)
    report = run_preflight()
    pilot.use_experiment(EXPERIMENT)
    if args.write:
        pilot.write_json(pilot.CORPUS_DIR / RECORD_NAME, report)
        report["written"] = str(pilot.CORPUS_DIR / RECORD_NAME)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
