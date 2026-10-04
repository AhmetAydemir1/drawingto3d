"""SEMREAD-001B — D/V/VE pilot sürücüsü (corpus, kollar, bütçe, değerlendirme, rapor).

Sözleşme (goal §3, §4, §6):

* **D**  : deterministic hat, **sıfır VLM çağrısı**. `out/lab/semread-001b` altında attempt yazar.
* **V**  : ham full-page + nötr kimlik + ortak görev prompt'u.
* **VE** : V ile byte düzeyinde aynı ham sayfa + gerçek gözlem overlay'i + adreslenebilir gözlem tablosu.
* **Bütçe**: bu goal için **en fazla 30** gerçek çağrı; en fazla 10 development/tanı, 10 sayfa × 2 kol
  için 20 final. Her istek, ortak ağır iş kilidi altında kalıcı sayaçta **gönderimden önce** rezerve
  edilir; timeout/başarısız istek/tanı çağrıları da sayılır; cache hit inference değildir.
* **Kollar aynı** şema/görev metni/model/digest/üretim ayarıyla çalışır; fark yalnız gözlem girdisidir.

Betik `out/lab` kökünü, ortak `LabRunner`ı ve ortak ağır iş kilidini kullanır; yeni runner/scheduler
kurulmaz.
"""

from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.llama import (ChatSettings, OllamaChat, find_model,  # noqa: E402
                               installed_models)
from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_candidate_reader import (ARMS, OVERLAY_IMAGE_ID, V_ARM, VE_ARM,  # noqa: E402
                                                   prepare_arm_inputs, read_page)
from drawingto3d.semantic_candidates import (CANDIDATE_SCHEMA_VERSION,  # noqa: E402
                                             CandidateResponse, CandidateParseError,
                                             candidate_json_schema, candidate_prompt,
                                             check_candidate_references, parse_candidate_json)
from drawingto3d.semantic_deterministic import D_ARM, deterministic_candidates  # noqa: E402
from drawingto3d.semantic_evaluation import (MATCH_POLICY, aggregate, compare_arms,  # noqa: E402
                                             evaluate_page)
from drawingto3d.semantic_images import open_source  # noqa: E402
from drawingto3d.inference_log import RecordedChat, Recorder  # noqa: E402
from drawingto3d.semantic_run_contract import (CASE_SCHEMA, CONTRACT_VERSION,  # noqa: E402
                                                IMAGES_LAYOUT, IMAGE_LABEL_PREFIX,
                                                arm_evidence_mode,
                                                D_SOURCE_FILES, EXPECTED_DIGEST,
                                                EXPECTED_RUNTIME, GOLD_SENTINEL, IMAGE_MAX_SIDE,
                                                EVIDENCE_MODES, ARM_VARIANTS, MODEL, NUM_PREDICT,
                                                PAGE_IMAGE_ID,
                                                PREPROCESSING_FILES, PRODUCER_SOURCE_FILES,
                                                SETTINGS)
from drawingto3d_lab.runner import Job, LabRunner  # noqa: E402

LAB_ROOT = ROOT / "out/lab"
REPORT_ROOT = LAB_ROOT / "semread-001b"
CORPUS_DIR = REPORT_ROOT / "corpus"
GOLD_DIR = CORPUS_DIR / "gold"
PAGES_DIR = CORPUS_DIR / "pages"
ATTEMPT_ROOT = REPORT_ROOT / "attempts"
PREPARED_INPUT_DIR = CORPUS_DIR / "prepared-inputs"   # gerçek hazırlanmış girdi kaydı önbelleği

JOB_PREFIX = "semread-001b-"
CASE_TIMEOUT_SECONDS = 600
RUN_TIMEOUT_SECONDS = 7200
MODEL_TIMEOUT_SECONDS = 300
LIVE_CALL_LIMIT_DEV = 10
LIVE_CALL_LIMIT_FINAL = 20
LIVE_CALL_LIMIT_TOTAL = LIVE_CALL_LIMIT_DEV + LIVE_CALL_LIMIT_FINAL
PHASES = ("dev", "final")                  # çağrının amacı
PHASE_LIMITS = {"dev": LIVE_CALL_LIMIT_DEV, "final": LIVE_CALL_LIMIT_FINAL}
FINAL_VLM_CELLS = 20                       # 10 sayfa × V/VE

# Attempt yaşam döngüsünün kapalı durum kümesi (P0R-FINAL-A). Her attempt klasörü tam olarak bir
# geçmiş kaydı alır ve o kaydın `state`i bu kümeden biridir.
FINALIZED_STATES = ("local_error_source", "local_error_observe", "local_error_preparation",
                    "blocked_budget", "blocked_model_discovery", "blocked_model_mismatch",
                    "blocked_runtime_mismatch", "blocked_unsupported_setting", "sending",
                    "transport_error", "parse_error", "failed_gates", "pass")

# Gerçekten gönderilmiş (ya da gönderim durumu belirsiz kalmış) attempt durumları: attempt defterinde
# "çağrı yapıldı" tarafında sayılanlar.
DISPATCHED_ATTEMPT_STATES = ("sending", "transport_error", "parse_error", "failed_gates", "pass")

# Eski (P0R-FINAL-B öncesi) sürüm gönderilmeyen bir isteği de **bütçe** defterine yazıyordu. Bu
# kayıtlar silinmez (kanıt), ama artık inference sayılmaz: yalnız raporlanır.
NON_DISPATCH_SEND_STATES = ("not_sent_model_mismatch", "not_sent_runtime_mismatch",
                            "not_sent_unsupported_setting")

PREDICTION_INPUT_SCHEMA = "semread-001b-prediction-input/1"

# D kolu modele görüntü/prompt göndermez. Manifestte kola bağlı iki alan (PLAN-4 §8) D için
# V/VE adlarıyla karışmasın diye açıkça "yok" yazılır.
D_INPUT_VARIANT = "none"
D_EVIDENCE_MODE = "none_no_model_input"


# Üretici kimliği (P0R-2): tahmini üreten her şey **semantic_run_contract.py** ve kaynak
# dosyalarda yaşar. Bu pilot dosyası burada **yoktur**: kabul kapıları, rapor ve değerlendirme
# kodu değişince ham tahmin geçersizleşmez.
PRODUCER_IDENTITY_FILES = ("src/drawingto3d/semantic_run_contract.py",
                           *PRODUCER_SOURCE_FILES, *D_SOURCE_FILES)

# Değerlendirici kimliği: gold + eşleştirme politikası + değerlendirici **uygulaması** (P0R-7).
# Bu pilot dosyası evaluate()/kabul/rapor kodunu taşıdığı için buradadır.
EVALUATION_IDENTITY_FILES = ("src/drawingto3d/semantic_evaluation.py",
                             "eval/semread_001b_reference.py",
                             "eval/semread_001b_pilot.py")

# Corpus: 10 sayfa, 10 bağımsız parça grubu, 4 development + 6 frozen. 001A'da incelenmiş örnekler
# (plate/flange) bilinçli olarak development'a ayrıldı (goal §4).
PAGES: tuple[dict, ...] = (
    {"page_id": "dev-plate-pocket", "split": "dev", "group": "plate-with-a-pocket",
     "path": "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF", "type": "pdf",
     "scope": "diameter/radius callouts, THRU/depth, count",
     "rationale": "001A'da incelenmiş örnek -> development (goal §4)"},
    {"page_id": "dev-flange-book", "split": "dev", "group": "flange-book-exercise",
     "path": "examples/pdf with steps/8/Flange.PNG", "type": "raster",
     "scope": "radius/diameter callouts, count",
     "rationale": "001A'da flange örneği incelendi -> development"},
    {"page_id": "dev-flange-elbow", "split": "dev", "group": "flange-elbow-90",
     "path": "examples/flange-elbow-90.png", "type": "raster",
     "scope": "assembled drawing: diameter/radius callouts",
     "rationale": "001A L4 vakasında kullanıldı -> development"},
    {"page_id": "dev-drawing-2", "split": "dev", "group": "drawing-2-views",
     "path": "examples/pdf with steps/2/Drawing.pdf", "type": "pdf",
     "scope": "two-view drawing: diameter/radius callouts, depth",
     "rationale": "development: farklı template (çok görünüşlü) denemesi"},
    {"page_id": "frozen-exercise-51", "split": "frozen", "group": "exercise-51",
     "path": "examples/pdf with steps/1/Exercise_51.PNG", "type": "raster",
     "scope": "book exercise: full dimensioning",
     "rationale": "frozen: 001A'da kullanılmadı"},
    {"page_id": "frozen-exercise-12", "split": "frozen", "group": "exercise-12",
     "path": "examples/pdf with steps/10/Exercise 12.pdf", "type": "pdf",
     "scope": "book exercise: full dimensioning",
     "rationale": "frozen: 001A'da kullanılmadı; pdf sürümü seçildi (aynı parçanın PNG'si ayrı örnek sayılmaz)"},
    {"page_id": "frozen-exercise-17", "split": "frozen", "group": "exercise-17",
     "path": "examples/pdf with steps/3/Exercise 17.PNG", "type": "raster",
     "scope": "book exercise: full dimensioning",
     "rationale": "frozen: 001A'da kullanılmadı"},
    {"page_id": "frozen-exercise-13", "split": "frozen", "group": "exercise-13",
     "path": "examples/pdf with steps/4/Exercise 13.PNG", "type": "raster",
     "scope": "book exercise: full dimensioning",
     "rationale": "frozen: 001A'da kullanılmadı"},
    {"page_id": "frozen-enclosure", "split": "frozen", "group": "plastic-enclosure",
     "path": "examples/pdf with steps/6/plastic enclosue.pdf", "type": "pdf",
     "scope": "enclosure drawing: callouts",
     "rationale": "frozen: farklı parça sınıfı (plastik mahfaza)"},
    {"page_id": "frozen-views-exercise", "split": "frozen", "group": "teknik-resim-views",
     "path": "examples/Teknik Resim Görünüş Çıkarma Örnekleri 1 - Makine Eğitimi.jpg",
     "type": "raster", "scope": "view-extraction exercise sheet",
     "rationale": "frozen: kitap taraması, farklı kaynak biçimi"},
)


# ------------------------------------------------------------------ kimlik ve yardımcılar


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_identity(relative_paths) -> str:
    digest = hashlib.sha256()
    for relative in sorted(set(relative_paths)):
        path = ROOT / relative
        digest.update(f"{relative}\0{sha256_of(path) if path.exists() else 'yok'}\0".encode())
    return digest.hexdigest()


def producer_identity() -> str:
    """Tahmini değiştirebilecek her şey: şema, görev metni, okuyucu, hazırlama, taşıma, ayar, model."""
    digest = hashlib.sha256()
    digest.update(_files_identity(PRODUCER_IDENTITY_FILES).encode())
    digest.update(json.dumps(SETTINGS, sort_keys=True).encode())
    digest.update(json.dumps(candidate_json_schema(), sort_keys=True).encode())
    digest.update(f"{MODEL}\0{EXPECTED_DIGEST}\0{EXPECTED_RUNTIME}\0".encode())
    for page in PAGES:  # corpus byte'ları da tahmini belirler
        source = ROOT / page["path"]
        digest.update(f"{page['page_id']}\0{sha256_of(source) if source.exists() else 'yok'}\0"
                      .encode())
    return digest.hexdigest()


def code_identity() -> str:
    """Geriye dönük ad (P0R-7): yeni kayıtlarda `producer_identity` kullanılır."""
    return producer_identity()


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def input_identity(page: dict) -> str:
    """Girdi kimliği: kaynak byte'ları + hazırlanmış sayfa PNG'si + hazırlama sözleşmesi."""
    source = ROOT / page["path"]
    page_png = PAGES_DIR / f"{page['page_id']}.png"
    return _sha256_text(json.dumps({
        "source_sha256": sha256_of(source) if source.exists() else None,
        "page_png_sha256": sha256_of(page_png) if page_png.exists() else None,
        "preprocessing": _files_identity(PREPROCESSING_FILES),
        "image_max_side": SETTINGS["image_max_side"],
        "raw_page_strategy": SETTINGS["raw_page_strategy"],
    }, sort_keys=True))


def prediction_input_record(page: dict, arm: str, *, bundle: dict, prompt: str) -> dict:
    """Modelin **gerçekten gördüğü** girdinin kanonik kaydı (PLAN-5 §5).

    Kayıt hazırlanmış paketten kurulur: görüntü byte'ları (sıra + sha256 + uzunluk), gönderilen
    prompt'un hash'i, VE'de adreslenebilir gözlem tablosunun hash'i ve hazırlama kimliği. Önbellekteki
    sayfa PNG'si ya da ona yakın bir temsil bu kaydın yerine geçmez.
    """
    table = list(bundle.get("observations") or [])
    return {
        "schema": PREDICTION_INPUT_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "page_id": page["page_id"],
        "arm": arm,
        "arm_input_variant": bundle.get("arm_input_variant") or arm,
        "evidence_mode": bundle.get("evidence_mode") or arm_evidence_mode(arm),
        "prompt_sha256": _sha256_text(prompt),
        "images": [{"order": index, "image_id": image.image_id,
                    "sha256": hashlib.sha256(image.png).hexdigest(), "bytes": len(image.png)}
                   for index, image in enumerate(bundle.get("images") or [])],
        "observation_table_sha256": (_sha256_text(json.dumps(table, sort_keys=True,
                                                            ensure_ascii=False))
                                     if table else None),
        "preprocessing_identity": preprocessing_identity(),
    }


def prediction_input_identity(record: dict | None) -> str | None:
    """Kanonik kaydın hash'i; kayıt hangi alanı taşırsa kimlik onu bağlar (prompt, byte, sıra…)."""
    if not record:
        return None
    return _sha256_text(json.dumps(record, sort_keys=True, ensure_ascii=False))


def preprocessing_identity() -> str:
    """Hazırlama kimliği: hazırlama kodu + hazırlamayı belirleyen donmuş ayarlar."""
    return _sha256_text(json.dumps({"files": _files_identity(PREPROCESSING_FILES),
                                    "image_max_side": SETTINGS["image_max_side"],
                                    "raw_page_strategy": SETTINGS["raw_page_strategy"]},
                                   sort_keys=True))


def prediction_input_cache_key(page: dict, arm: str) -> str:
    """Önbellek anahtarı: üretici kimliği (kod + ayar + corpus) + sayfa + kol."""
    return _sha256_text(json.dumps({"producer_identity": producer_identity(),
                                    "page_id": page["page_id"], "arm": arm}, sort_keys=True))


def store_prepared_input(page: dict, arm: str, record: dict) -> Path:
    """Hazırlanmış girdi kaydını önbelleğe yaz (anahtar üretici kimliğine bağlı)."""
    return write_json(PREPARED_INPUT_DIR / f"{page['page_id']}-{arm}.json",
                      {"schema": "semread-001b-prepared-input/1",
                       "key": prediction_input_cache_key(page, arm), "record": record})


def prepared_input_record(page: dict, arm: str, *, refresh: bool = False) -> dict | None:
    """(page, arm) için gerçek hazırlanmış girdinin kaydı: önbellekten ya da yeniden hazırlanarak.

    Önbellek üretici kimliğine bağlıdır: kod/ayar/corpus değişirse anahtar değişir ve kayıt yeniden
    hazırlanır. Hazırlanamayan girdi için `None` döner — yeniden kullanım kanıtlanamaz (fail-closed).
    """
    cache_path = PREPARED_INPUT_DIR / f"{page['page_id']}-{arm}.json"
    key = prediction_input_cache_key(page, arm)
    cached = read_json(cache_path)
    if not refresh and isinstance(cached, dict) and cached.get("key") == key \
            and isinstance(cached.get("record"), dict):
        return cached["record"]
    source_path = ROOT / page["path"]
    if not source_path.exists():
        return None
    try:
        source = open_source(source_path)
        observations = observe(source_path)
        bundle = prepare_arm_inputs(source, observations, image_id=PAGE_IMAGE_ID, arm=arm,
                                    resize_max_side=IMAGE_MAX_SIDE)
        prompt = candidate_prompt([PAGE_IMAGE_ID], observations=bundle["observations"] or None)
    except Exception:  # noqa: BLE001 - hazırlanamayan girdi yeniden kullanım kanıtı üretmez
        return None
    record = prediction_input_record(page, arm, bundle=bundle, prompt=prompt)
    store_prepared_input(page, arm, record)
    return record


def v_ve_raw_page_invariant(page: dict) -> dict:
    """V ve VE'nin ham sayfası **aynı byte** mı (mekanik denetim, P0R-FINAL-C).

    Tam girdi kimliklerinin farklı olması beklenir (VE overlay + gözlem tablosu ekler); eşit olması
    gereken şey ham `image-1` byte'ıdır. Hazırlanmış girdi kaydı yoksa `ok: False` döner.
    """
    v_record = prepared_input_record(page, V_ARM)
    ve_record = prepared_input_record(page, VE_ARM)
    if not v_record or not ve_record:
        return {"ok": False, "page_id": page["page_id"], "reason": "hazırlanmış girdi kaydı yok",
                "v_image_1": None, "ve_image_1": None}
    v_images = v_record.get("images") or []
    ve_images = ve_record.get("images") or []
    v_first = v_images[0].get("sha256") if v_images else None
    ve_first = ve_images[0].get("sha256") if ve_images else None
    v_identity = prediction_input_identity(v_record)
    ve_identity = prediction_input_identity(ve_record)
    return {"ok": bool(v_first) and v_first == ve_first, "page_id": page["page_id"],
            "v_image_1": v_first, "ve_image_1": ve_first,
            "v_identity": v_identity, "ve_identity": ve_identity,
            "identities_differ": v_identity != ve_identity,
            "v_observation_table": v_record.get("observation_table_sha256"),
            "ve_observation_table": ve_record.get("observation_table_sha256"),
            "note": ("V/VE ham image-1 byte'ı aynı olmalı; tam kimlikler farklıdır çünkü VE kanıt "
                     "ekler")}


def model_identity() -> str:
    """Model kimliği: etiket + beklenen digest + beklenen runtime + üretim ayarları."""
    return _sha256_text(json.dumps({"model": MODEL, "digest": EXPECTED_DIGEST,
                                    "runtime": EXPECTED_RUNTIME, "settings": SETTINGS},
                                   sort_keys=True))


def request_hashes(trace: dict | None) -> dict:
    """İki ayrı alan (P0R-3): gerçek HTTP gövdesi hash'i ve kayıt (manifest) hash'i."""
    trace = trace or {}
    return {"http_request_sha256": trace.get("request_sha256"),
            "request_manifest_sha256": _sha256_text(json.dumps(trace, sort_keys=True,
                                                               ensure_ascii=False))
            if trace else None}


def evaluation_identity() -> str:
    """Değerlendirme kimliği: gold + eşleştirme politikası + değerlendirici **kodu** (P0-7).

    Değerlendirici/gold düzeltmesi bu kimliği değiştirir ama `producer_identity()`i değiştirmez;
    böylece geçerli ham tahmin yeni inference yapılmadan yeniden değerlendirilebilir.
    """
    digest = hashlib.sha256()
    digest.update(_files_identity(EVALUATION_IDENTITY_FILES).encode())
    digest.update(json.dumps(MATCH_POLICY, sort_keys=True, ensure_ascii=False).encode())
    for page in PAGES:
        reference = GOLD_DIR / f"{page['page_id']}.json"
        digest.update(f"{page['page_id']}\0{sha256_of(reference) if reference.exists() else 'yok'}\0"
                      .encode())
    return digest.hexdigest()


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def state_path() -> Path:
    return REPORT_ROOT / "state.json"


def load_state() -> dict:
    state = read_json(state_path(), default=None)
    if state is None:
        state = {"schema": "semread-001b-state/1", "created_at": _now(), "live_calls": [],
                 "budget": {"dev": LIVE_CALL_LIMIT_DEV, "final": LIVE_CALL_LIMIT_FINAL,
                            "total": LIVE_CALL_LIMIT_TOTAL},
                 "attempts": {}, "notes": [
                     "001A tarihsel kayıtları bu sayaca dahil değildir; iki goal ayrı raporlanır."]}
    return state


def save_state(state: dict) -> Path:
    state["updated_at"] = _now()
    return write_json(state_path(), state)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() or None


def artifact_index(directory: Path) -> dict:
    rows = [{"path": str(path.relative_to(directory)), "sha256": sha256_of(path),
             "bytes": path.stat().st_size}
            for path in sorted(directory.rglob("*")) if path.is_file()]
    return {"schema": "semread-001b-artifact-index/1", "files": rows, "count": len(rows)}


# ------------------------------------------------------------------ bütçe (ortak kilit altında)


def _is_inference_record(call: dict) -> bool:
    """Bütçeye sayılan kayıt mı (P0R-FINAL-B)?

    Sayılan: gerçekten gönderilmiş ya da gönderim durumu belirsiz kalmış istekler. Sayılmayan:
    gönderilmediği **kanıtlı** yerel/preflight retleri (eski sürümün `not_sent_*` kayıtları dahil).
    """
    return call.get("send_state") not in NON_DISPATCH_SEND_STATES


def inference_records(state: dict) -> list[dict]:
    return [call for call in (state.get("live_calls") or []) if _is_inference_record(call)]


def _budget_used(state: dict, phase: str) -> int:
    return sum(1 for call in inference_records(state) if call.get("phase") == phase)


def reserve_live_call(case_id: str, *, phase: str, arm: str, split: str,
                      attempt_dir: Path, attempt_id: str | None = None) -> dict:
    """Çağrıdan **hemen önce** kalıpersistent rezervasyon; üç sınır aynı kilit içinde denetlenir.

    Bu fonksiyon yalnızca **gönderim anında** çağrılır (P0R-FINAL-B): yerel hazırlama, donmuş ayar,
    model keşfi ve runtime doğrulaması gibi gönderimi kanıtlanabilir biçimde engelleyen adımlar
    buradan sonra değil **önce** koşar. Böylece "30 inference denemesi" gerçek gönderimleri sayar;
    gönderilmeyen bir yerel hata yalnız attempt defterine yazılır.

    `split` veri bölümüdür (dev/frozen), `phase` çağrının amacıdır (dev/final). İkisi ayrıdır:
    development sayfası final fazında da çalışabilir. Faz/kol değerleri doğrulanır; geçersiz değer
    bütçe harcamaz. Development, final ve toplam (30) tavanı **tek** `flock` bölümünde denetlenir;
    böylece yeniden başlatma/timeout/retry/eşzamanlı rezervasyon tavanı aşamaz. Cevaplanmamış
    ("reserved") kayıt da sayılır — gönderilip gönderilmediği belirsiz istek bütçede kalır.
    """
    if phase not in PHASES:
        return {"reserved": False, "reason": f"geçersiz faz: {phase!r} (beklenen: {PHASES})"}
    if arm not in ARMS:
        return {"reserved": False, "reason": f"geçersiz kol: {arm!r} (beklenen: {ARMS})"}
    if split not in ("dev", "frozen"):
        return {"reserved": False, "reason": f"geçersiz veri bölümü: {split!r}"}
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    guard = REPORT_ROOT / "live-calls.guard"
    with guard.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            state = load_state()
            calls = state.setdefault("live_calls", [])
            counted = inference_records(state)
            used_dev, used_final = _budget_used(state, "dev"), _budget_used(state, "final")
            used = {"dev": used_dev, "final": used_final}
            if used[phase] >= PHASE_LIMITS[phase]:
                return {"reserved": False,
                        "reason": f"{phase} bütçesi bitti ({used[phase]}/{PHASE_LIMITS[phase]})"}
            if len(counted) >= LIVE_CALL_LIMIT_TOTAL:
                return {"reserved": False,
                        "reason": f"toplam bütçe bitti ({len(counted)}/{LIVE_CALL_LIMIT_TOTAL})"}
            record = {"attempt_id": attempt_id or case_id, "case_id": case_id, "arm": arm,
                      "phase": phase, "split": split, "reserved_at": _now(),
                      "attempt_dir": str(attempt_dir), "pid": os.getpid(),
                      "reserved_before_send": True, "send_state": "reserved"}
            calls.append(record)
            state.setdefault("budget_history", []).append(
                {"at": record["reserved_at"], "attempt_id": record["attempt_id"], "phase": phase,
                 "split": split, "case_id": case_id, "arm": arm,
                 "used_dev": used_dev + (1 if phase == "dev" else 0),
                 "used_final": used_final + (1 if phase == "final" else 0),
                 "used_total": len(counted) + 1})
            save_state(state)
            return {"reserved": True, "record": record, "used_dev": used_dev,
                    "used_final": used_final, "used_total": len(counted) + 1}
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def mark_send_state(attempt_id: str, *, state_name: str, detail: str | None = None) -> None:
    """Rezervasyon kaydının gönderim durumunu işaretle (reserved -> sending -> sent/transport_*).

    Kayıt `attempt_id` ile bulunur: aynı vakada birden çok attempt olabilir ve durum tam olarak
    rezerve edilen isteğe yazılmalıdır. Gönderim başladıktan sonraki her terminal durum `sent_at`
    taşır; böylece "gönderildi mi" sorusu defterden okunur, tahmin edilmez.
    """
    guard = REPORT_ROOT / "live-calls.guard"
    with guard.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            state = load_state()
            for call in reversed(state.get("live_calls") or []):
                if call.get("attempt_id") == attempt_id or call.get("case_id") == attempt_id:
                    call["send_state"] = state_name
                    if detail:
                        call["send_detail"] = detail
                    call["updated_at"] = _now()
                    if state_name == "sending":
                        call["dispatch_started_at"] = call["updated_at"]
                    else:
                        call["sent_at"] = call["updated_at"]
                    break
            save_state(state)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def attempt_ledger_report(state: dict | None = None) -> dict:
    """Attempt defteri: her yürütme denemesi (gönderim olmayan retler dahil), durum bazında."""
    records = all_attempt_records(load_state() if state is None else state)
    by_state: dict[str, int] = {}
    for row in records:
        key = row.get("state") or row.get("verdict") or "?"
        by_state[key] = by_state.get(key, 0) + 1
    identifiers = [row.get("attempt_id") for row in records]
    return {"schema": "semread-001b-attempt-ledger/1", "total": len(records),
            "by_state": by_state, "unique_attempt_ids": len(set(identifiers)),
            "dispatched": sum(1 for row in records
                              if row.get("state") in DISPATCHED_ATTEMPT_STATES),
            "note": ("attempt defteri her denemeyi sayar; inference bütçesi **ayrı** defterdir ve "
                     "yalnız gönderilen/belirsiz istekleri sayar (P0R-FINAL-B)")}


def attempt_lifecycle_report() -> dict:
    """Yaşam döngüsü toplam mı (P0R-FINAL-A): her attempt klasörü tam bir geçmiş kaydı mı?"""
    history = all_attempt_records(load_state())
    identifiers = [row.get("attempt_id") for row in history]
    duplicates = sorted(str(value) for value in set(identifiers) if identifiers.count(value) > 1)
    directories: list[str] = []
    if ATTEMPT_ROOT.exists():
        for case_directory in sorted(path for path in ATTEMPT_ROOT.iterdir() if path.is_dir()):
            for directory in sorted(path for path in case_directory.glob("attempt-*")
                                    if path.is_dir()):
                directories.append(f"{case_directory.name}/{directory.name}")
    known = set(identifiers)
    orphans = [directory for directory in directories if directory not in known]
    # Ters yön: kaydı olup kanıt klasörü olmayan attempt. Sözleşme ihlali değildir (klasör
    # temizlenmiş olabilir) ama kanıt zinciri kurulamaz: B07 böyle bir kaydı kabul etmemeli.
    missing = sorted(str(row.get("attempt_id")) for row in history
                     if not row.get("directory")
                     or not Path(str(row["directory"])).is_dir())
    return {"schema": "semread-001b-lifecycle/1", "attempt_directories": len(directories),
            "history_rows": len(history), "unique_attempt_ids": len(known),
            "orphan_attempts": orphans, "duplicate_attempt_ids": duplicates,
            "rows_without_directory": missing,
            "ok": not orphans and not duplicates and len(set(identifiers)) == len(identifiers),
            "note": ("her attempt klasörü için tam olarak bir geçmiş kaydı olmalı; 0 ya da 2+ "
                     "kayıt kabul edilmez. `rows_without_directory` kanıtı silinmiş kayıtları "
                     "gösterir: bunlar kanıt zincirine giremez")}


def budget_report() -> dict:
    state = load_state()
    counted = inference_records(state)
    legacy = [call for call in (state.get("live_calls") or []) if not _is_inference_record(call)]
    by_arm: dict[str, int] = {}
    by_send_state: dict[str, int] = {}
    for call in counted:
        by_arm[call.get("arm", "?")] = by_arm.get(call.get("arm", "?"), 0) + 1
        key = call.get("send_state", "?")
        by_send_state[key] = by_send_state.get(key, 0) + 1
    bad_phase = [call for call in counted if call.get("phase") not in PHASES]
    return {"dev_used": _budget_used(state, "dev"), "dev_limit": LIVE_CALL_LIMIT_DEV,
            "final_used": _budget_used(state, "final"), "final_limit": LIVE_CALL_LIMIT_FINAL,
            "total_used": len(counted), "total_limit": LIVE_CALL_LIMIT_TOTAL,
            "by_arm": by_arm, "by_send_state": by_send_state,
            "invalid_phase_records": len(bad_phase),
            "legacy_non_dispatch_records": len(legacy),
            "attempt_ledger": attempt_ledger_report(state),
            "over_budget": (len(counted) > LIVE_CALL_LIMIT_TOTAL
                            or _budget_used(state, "dev") > LIVE_CALL_LIMIT_DEV
                            or _budget_used(state, "final") > LIVE_CALL_LIMIT_FINAL),
            "method": ("inference bütçesi = state.live_calls'ta gönderilmiş/belirsiz kayıtlar; her "
                       "kayıt gönderimden hemen önce yazılır; split (veri bölümü) ile phase (çağrı "
                       "amacı) ayrıdır; attempt defteri ayrı tutulur"),
            "counting_note": ("timeout, başarısız istek, tanı çağrıları ve gönderilip gönderilmediği "
                              "belirsiz ('reserved') kayıtlar sayılır; kaynak/gözlem/hazırlama "
                              "hatası, bilinen model/digest/runtime uyuşmazlığı, desteklenmeyen "
                              "donmuş ayar ve bütçe reddi **sayılmaz** (attempt defterine yazılır); "
                              "cache hit inference değildir; 001A sayaçları bu sayaca dahil değildir")}



# ------------------------------------------------------------------ corpus


def corpus_manifest() -> dict:
    rows = []
    for page in PAGES:
        path = ROOT / page["path"]
        rows.append({**page, "exists": path.exists(),
                     "source_sha256": sha256_of(path) if path.exists() else None,
                     "source_bytes": path.stat().st_size if path.exists() else None})
    groups = {row["group"]: sorted({r["split"] for r in rows if r["group"] == row["group"]})
              for row in rows}
    split_groups = sorted(group for group, splits in groups.items() if len(splits) > 1)
    dev = sorted(row["page_id"] for row in rows if row["split"] == "dev")
    frozen = sorted(row["page_id"] for row in rows if row["split"] == "frozen")
    return {"schema": "semread-001b-corpus/1", "created_at": _now(), "pages": rows,
            "totals": {"pages": len(rows), "dev": len(dev), "frozen": len(frozen),
                       "independent_groups": len(groups)},
            "split_violations": split_groups,
            "honesty_note": ("Bu corpus küçüktür ve önceden bilinen bir repo kaynağıdır; bağımsız "
                             "holdout değildir. Aynı parçanın PDF/PNG sürümleri ayrı örnek sayılmaz."),
            "scope_note": ("Kapsam: circle temsili/delik ayrımı, R vs Ø, basılı değer+birim, count, "
                           "THRU/finite/unknown, açıkça yazılmış derinlik, callout->target binding.")}


def write_corpus() -> dict:
    manifest = corpus_manifest()
    write_json(CORPUS_DIR / "manifest.json", manifest)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for page in manifest["pages"]:
        if not page["exists"]:
            continue
        target = PAGES_DIR / f"{page['page_id']}.png"
        if target.exists():
            continue
        source = open_source(ROOT / page["path"])
        target.write_bytes(source.frame_png)
    return manifest


def load_reference(page_id: str) -> dict | None:
    return read_json(GOLD_DIR / f"{page_id}.json")


def check_reference(reference: dict, page: dict, observation_ids: list[str]) -> dict:
    """Referansı denetle: nitelik, kapsam, kapalı kümeler, bölge sınırları, gözlem kimlikleri."""
    problems: list[str] = []
    if reference.get("annotator") != "agent":
        problems.append("annotator=agent yazılmamış")
    if reference.get("review_status") != "provisional":
        problems.append("review_status=provisional değil (insan onayı yok)")
    if not reference.get("scope"):
        problems.append("kapsam yazılmamış")
    if not reference.get("exhaustiveness"):
        problems.append("exhaustiveness (hangi bölgeler annotate edildi) yazılmamış")
    claims = reference.get("claims") or []
    if not claims:
        problems.append("hiç claim yok")
    seen: set[str] = set()
    for claim in claims:
        claim_id = claim.get("claim_id")
        if not claim_id:
            problems.append("claim_id boş")
        elif claim_id in seen:
            problems.append(f"tekrarlanan claim_id: {claim_id}")
        seen.add(claim_id)
        if claim.get("state") not in ("determinate_present", "determinate_absent", "underdetermined"):
            problems.append(f"{claim_id}: state kapalı kümede değil")
        region = (claim.get("target") or {}).get("region")
        if region is None:
            problems.append(f"{claim_id}: hedef bölgesi yok")
        if not claim.get("evidence"):
            problems.append(f"{claim_id}: kaynak kanıtı (evidence) yok")
        observation_id = (claim.get("target") or {}).get("observation_id")
        if observation_id is not None and observation_ids and observation_id not in observation_ids:
            problems.append(f"{claim_id}: bilinmeyen gözlem kimliği {observation_id}")
        if not claim.get("source_evidence"):
            problems.append(f"{claim_id}: okunabilir metin/geometri kaynağı yazılmamış")
    return {"ok": not problems, "problems": problems, "claims": len(claims),
            "reference_sha256": sha256_of(GOLD_DIR / f"{page['page_id']}.json")
            if (GOLD_DIR / f"{page['page_id']}.json").exists() else None}


# ------------------------------------------------------------------ attempt yazımı


def attempt_root(case_id: str) -> Path:
    """Bir vakanın attempt kökü; içinde **üzerine yazılmayan** attempt klasörleri durur."""
    return ATTEMPT_ROOT / case_id


def attempt_dirs(case_id: str) -> list[Path]:
    """Vakanın tüm attempt klasörleri (ilk sürümün düz klasörü de tarihsel kayıt olarak sayılır)."""
    root = attempt_root(case_id)
    dirs = sorted(path for path in root.glob("attempt-*") if path.is_dir())
    if (root / "result.json").exists() or (root / "response-parsed.json").exists():
        dirs.insert(0, root)
    return dirs


def latest_attempt_dir(case_id: str) -> Path | None:
    dirs = attempt_dirs(case_id)
    return dirs[-1] if dirs else None


def attempt_dir(case_id: str) -> Path:
    """Okuma için: en son attempt klasörü, hiç yoksa vaka kökü (yazma için `new_attempt_dir`)."""
    return latest_attempt_dir(case_id) or attempt_root(case_id)


def new_attempt_dir(case_id: str) -> Path:
    """Sıradaki **değişmez** attempt klasörü. Var olan bir attempt asla yeniden yazılmaz."""
    root = attempt_root(case_id)
    root.mkdir(parents=True, exist_ok=True)
    numbers = [int(match.group(1)) for path in root.glob("attempt-*")
               if (match := re.fullmatch(r"attempt-(\d{4,})", path.name))]
    directory = root / f"attempt-{max(numbers, default=0) + 1:04d}"
    directory.mkdir()
    return directory


def _attempt_manifest(page: dict, arm: str, *, attempt_id: str, phase: str,
                      runtime: str | None = None, model_metadata: dict | None = None,
                      request_hashes_seen: dict | None = None,
                      prediction_input: dict | None = None) -> dict:
    """Bir attempt'in değişmez kimlik kaydı (P0: hangi girdi/kod/model ile üretildi)."""
    page_png = PAGES_DIR / f"{page['page_id']}.png"
    source = ROOT / page["path"]
    return {
        "schema": "semread-001b-attempt/2", "attempt_id": attempt_id, "case_id": attempt_id,
        "page_id": page["page_id"], "arm": arm, "phase": phase, "split": page["split"],
        "group": page["group"], "created_at": _now(),
        "contract_version": CONTRACT_VERSION,
        "producer_identity": producer_identity(), "evaluation_identity": evaluation_identity(),
        "input_identity": input_identity(page), "model_identity": model_identity(),
        # P0R-FINAL-C: yeniden kullanım kararı bu kimliğe bakar (gerçek hazırlanmış girdi).
        "prediction_input_identity": prediction_input_identity(prediction_input),
        "prediction_input_record": ("prediction-input.json" if prediction_input else None),
        "page_png_sha256_metadata_note": ("page_png_sha256 yalnız meta veridir; V/VE yeniden "
                                          "kullanımı prediction_input_identity ile kanıtlanır"),
        "code_identity": producer_identity(),          # geriye dönük alan adı (P0R-7)
        "case_schema": CASE_SCHEMA, "candidate_schema": CANDIDATE_SCHEMA_VERSION,
        "head": _git("rev-parse", "HEAD"),
        "source": {"path": page["path"], "sha256": sha256_of(source) if source.exists() else None,
                   "bytes": source.stat().st_size if source.exists() else None},
        "page_png_sha256": sha256_of(page_png) if page_png.exists() else None,
        "corpus_manifest_sha256": sha256_of(CORPUS_DIR / "manifest.json")
        if (CORPUS_DIR / "manifest.json").exists() else None,
        "model": MODEL, "expected_digest": EXPECTED_DIGEST, "runtime": runtime,
        "model_metadata": model_metadata or {},
        # D kolu modele görüntü/prompt **göndermez**: kanıt modu da model-girdisi değildir.
        # V/VE adları (PLAN-4 §8) kola bağlı kalır; D için açıkça "yok" yazılır.
        "arm_input_variant": ARM_VARIANTS.get(arm, D_INPUT_VARIANT),
        "evidence_mode": EVIDENCE_MODES.get(arm, D_EVIDENCE_MODE),
        "settings": dict(SETTINGS),
        **(request_hashes_seen or {"http_request_sha256": None,
                                   "request_manifest_sha256": None}),
    }


def record_attempt(attempt_id: str, directory: Path, page: dict, arm: str, *, phase: str,
                   verdict: str, gates: dict, seconds: float, stats: dict | None = None,
                   state: str | None = None) -> dict:
    """Attempt geçmişine **ekle** (üzerine yazmaz). state.json artık vaka başına liste tutar (P0)."""
    manifest = read_json(directory / "manifest.json") or {}
    record = {"attempt_id": attempt_id, "directory": str(directory), "arm": arm,
              "page_id": page["page_id"], "split": page["split"], "phase": phase,
              "verdict": verdict, "state": state or verdict, "gates": gates, "seconds": seconds,
              "created_at": manifest.get("created_at") or _now(),
              "producer_identity": manifest.get("producer_identity"),
              "evaluation_identity": manifest.get("evaluation_identity"),
              "prediction_input_identity": manifest.get("prediction_input_identity"),
              "page_png_sha256": manifest.get("page_png_sha256"),
              "source_sha256": (manifest.get("source") or {}).get("sha256"),
              "runtime": manifest.get("runtime"), "stats": stats or {}}
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    guard = REPORT_ROOT / "state.guard"
    with guard.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            state = load_state()
            state.setdefault("attempts", {}).setdefault(f"{page['page_id']}-{arm}", []).append(record)
            save_state(state)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return record


class AttemptFinalizedError(RuntimeError):
    """Aynı attempt_id iki kez sonuçlandırılamaz (P0R-FINAL-A)."""


def attempt_history(state: dict | None, attempt_id: str) -> list[dict]:
    """Bir attempt_id'ye düşen geçmiş kayıtları (düzleştirilmiş tüm geçmişten)."""
    return [row for row in all_attempt_records(state) if row.get("attempt_id") == attempt_id]


def finalize_attempt(*, attempt_id: str, directory: Path, page: dict, arm: str, phase: str,
                     state: str, verdict: str, send_attempted: bool, inference_calls: int,
                     gates: dict | None = None, error: dict | None = None, seconds: float = 0.0,
                     runtime: str | None = None, model_metadata: dict | None = None,
                     stats: dict | None = None, prediction_input: dict | None = None,
                     request_hashes_seen: dict | None = None, budget: dict | None = None,
                     result_extra: dict | None = None, manifest_extra: dict | None = None) -> dict:
    """Bir attempt'in **tek** kapanış yolu (P0R-FINAL-A).

    Şunları yazar: `local-error.json` (varsa), `prediction-input.json` (varsa), `manifest.json`,
    geçmiş kaydı, `result.json`, `artifact-index.json`. Geçmiş kaydı result.json'dan **önce** yazılır
    ki süreç arada ölürse klasör kayıtsız (orphan) kalmasın; kaydı olup sonucu olmayan attempt
    yeniden kullanılamaz (fail-closed).

    Aynı `attempt_id` ikinci kez sonuçlandırılamaz: tekrar çağrı `AttemptFinalizedError` verir.
    """
    if state not in FINALIZED_STATES:
        raise ValueError(f"bilinmeyen attempt durumu: {state!r} (beklenen: {FINALIZED_STATES})")
    if attempt_history(load_state(), attempt_id):
        raise AttemptFinalizedError(f"attempt zaten sonuçlandırıldı: {attempt_id}")
    directory.mkdir(parents=True, exist_ok=True)
    if error:
        write_json(directory / "local-error.json",
                   {"schema": "semread-001b-local-error/1", "arm": arm, "phase": phase,
                    "state": state, "kind": error.get("kind"), "detail": error.get("detail"),
                    "send_attempted": send_attempted, "inference_calls": inference_calls})
    if prediction_input is not None:
        write_json(directory / "prediction-input.json", prediction_input)
    write_json(directory / "manifest.json",
               {**_attempt_manifest(page, arm, attempt_id=attempt_id, phase=phase, runtime=runtime,
                                    model_metadata=model_metadata,
                                    request_hashes_seen=request_hashes_seen,
                                    prediction_input=prediction_input),
                **(manifest_extra or {})})
    identity = prediction_input_identity(prediction_input)
    record_attempt(attempt_id, directory, page, arm, phase=phase, verdict=verdict,
                   gates=gates or {}, seconds=seconds, state=state, stats=stats)
    result = {"schema": "semread-001b-result/1", "case_id": attempt_id.split("/")[0],
              "attempt_id": attempt_id, "arm": arm, "phase": phase, "split": page["split"],
              "state": state, "product_verdict": verdict, "send_attempted": send_attempted,
              "inference_calls": inference_calls, "gates": gates or {},
              "prediction_input_identity": identity, "runtime": runtime, "seconds": seconds,
              "inference_budget_record": budget, "finalized_at": _now()}
    if error:
        result["local_error"] = error.get("detail")
        result["error_kind"] = error.get("kind")
    result.update(result_extra or {})
    write_json(directory / "result.json", result)
    write_json(directory / "artifact-index.json", artifact_index(directory))
    return {"case_id": result["case_id"], "directory": str(directory), "attempt_id": attempt_id,
            "state": state, "verdict": verdict, "gates": result["gates"],
            "inference_calls": inference_calls, "prediction_input_identity": identity,
            "local_error": result.get("local_error"),
            "reason": result.get("blocking_reason") or result.get("local_error"),
            "result": result}


def runtime_identity() -> dict:
    """Gerçek yerel runtime sürümü + **kanonik** model meta verisi. Inference değildir (metadata).

    Model meta verisi tek ayrıştırıcıdan gelir: `installed_models()` → `find_model()` →
    `ModelInfo.as_dict()` (PLAN-3 §8). İkinci bir etiket-listesi ayrıştırması yoktur.
    """
    info: dict = {"endpoint": "http://127.0.0.1:11434", "version": None, "model": {},
                  "model_canonical": None, "parser": "installed_models/find_model/as_dict",
                  "error": None}
    try:
        from urllib.request import urlopen                     # modül içi tek kullanım yeri
        with urlopen("http://127.0.0.1:11434/api/version", timeout=5) as response:
            info["version"] = json.loads(response.read()).get("version")
        installed = find_model(installed_models(), MODEL)
        info["model_canonical"] = installed.as_dict() if installed else None
        info["model"] = info["model_canonical"] or {}
    except Exception as exc:  # noqa: BLE001 - kimlik okunamazsa çağrı zaten durdurulur
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def write_d_attempt(page: dict, *, observations=None, source=None) -> dict:
    """D kolu: VLM çağrısı yok. Adaylar + deterministic kanıt + kapsam raporu yazılır.

    Tüm yerel adımlar tek kapanış yolundan geçer (P0R-FINAL-A): kaynak/gözlem hatası veya adapter
    hatası da tam bir geçmiş kaydıyla sonuçlanır.
    """
    case_id = f"{page['page_id']}-{D_ARM}"
    directory = new_attempt_dir(case_id)
    attempt_id = f"{case_id}/{directory.name}"

    def finish(**kwargs) -> dict:
        kwargs.setdefault("runtime", "deterministic")
        kwargs.setdefault("model_metadata", {"model": "yok", "note": "D kolu model çağırmaz"})
        return finalize_attempt(attempt_id=attempt_id, directory=directory, page=page, arm=D_ARM,
                                phase="deterministic", stats={"inference_calls": 0}, **kwargs)

    try:
        if source is None:
            source = open_source(ROOT / page["path"])
    except Exception as exc:  # noqa: BLE001 - kaynak hatası da kayda geçer
        return {**finish(state="local_error_source", verdict="fail", send_attempted=False,
                         inference_calls=0,
                         error={"kind": "source", "detail": f"{type(exc).__name__}: {exc}"}),
                "candidates": 0}
    try:
        if observations is None:
            observations = observe(ROOT / page["path"])
    except Exception as exc:  # noqa: BLE001 - gözlem (OCR) hatası da kayda geçer
        return {**finish(state="local_error_observe", verdict="fail", send_attempted=False,
                         inference_calls=0,
                         error={"kind": "observe", "detail": f"{type(exc).__name__}: {exc}"}),
                "candidates": 0}
    started = time.perf_counter()
    try:
        result = deterministic_candidates(ROOT / page["path"], image_id=PAGE_IMAGE_ID,
                                          observations=observations)
    except Exception as exc:  # noqa: BLE001 - D hatası da kayda geçer (P0R-5)
        return {**finish(state="local_error_preparation", verdict="fail", send_attempted=False,
                         inference_calls=0,
                         error={"kind": "deterministic", "detail": f"{type(exc).__name__}: {exc}"}),
                "candidates": 0}
    seconds = round(time.perf_counter() - started, 3)
    response = result["response"]
    payload = response.model_dump(mode="json")
    write_json(directory / "response-parsed.json", payload)
    write_json(directory / "response-schema.json", candidate_json_schema())
    (directory / "prompt.txt").write_text(candidate_prompt([PAGE_IMAGE_ID]) + "\n", encoding="utf-8")
    write_json(directory / "request-manifest.json",
               {"arm": D_ARM, "images_layout": "none", "images": [],
                "note": "D kolu model çağırmez: istek kaydı boştur ve bu kasıtlıdır."})
    references = check_candidate_references(response, [PAGE_IMAGE_ID],
                                            allowed_observation_ids=None)
    write_json(directory / "reference-checks.json", {"schema": "semread-001b-references/1",
                                                     **references})
    write_json(directory / "resources.json",
               {"schema": "semread-001b-resources/1", "arm": D_ARM, "seconds": seconds,
                "inference_calls": 0,
                "rss": {"value_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "scope": "bu sürecin RSS'i; toplam sistem/model RAM'i değildir"}})
    gates = {"references_ok": bool(references.get("ok")),
             "coverage_exact": bool((references.get("coverage") or {}).get("exact"))}
    verdict = "pass" if references["ok"] else "fail"
    finalized = finish(state="pass" if verdict == "pass" else "failed_gates", verdict=verdict,
                       send_attempted=False, inference_calls=0, gates=gates, seconds=seconds,
                       manifest_extra={"deterministic_evidence": result["evidence"]},
                       result_extra={"evaluation_scope": "candidate-accuracy",
                                     "semantic_evaluation": "provisional-reference",
                                     "cad_evaluation": "not_evaluated",
                                     "candidates": len(response.items), "references": references,
                                     "timing_note": ("seconds yalnız adapter süresidir: "
                                                     "observe()/OCR dışarıda; uçtan uca okuma "
                                                     "gecikmesi olarak kullanılmaz")})
    return {**finalized, "candidates": len(response.items), "seconds": seconds,
            "evidence": result["evidence"], "response": payload}


def write_live_attempt(page: dict, arm: str, *, phase: str, observations=None, source=None) -> dict:
    """V/VE attempt'i: yerel preflight → gönderim rezervasyonu → tek çağrı → kanıt yazımı (P0R-FINAL-B).

    Sıra: attempt klasörü → kaynak → gözlem → paket + prompt → donmuş ayar denetimi → model keşfi ve
    digest → runtime doğrulaması → **gerçek hazırlanmış girdi kimliği** → rezervasyon → gönderim.
    Rezervasyon gönderimden hemen önce yapılır (eşzamanlı işçiler tavanı aşamasın); gönderilmeyeceği
    kanıtlanabilen her yerel ret rezervasyondan **önce** durur ve inference bütçesini harcamaz.
    Yerel hazırlama/keşif hatası gerçek gönderim gibi raporlanmaz (`send_attempted: false`).
    """
    case_id = f"{page['page_id']}-{arm}"
    directory = new_attempt_dir(case_id)
    attempt_id = f"{case_id}/{directory.name}"

    def blocked(state: str, *, verdict: str = "blocked", error: dict | None = None,
                result_extra: dict | None = None, manifest_extra: dict | None = None,
                runtime: str | None = None, stats: dict | None = None) -> dict:
        return finalize_attempt(attempt_id=attempt_id, directory=directory, page=page, arm=arm,
                                phase=phase, state=state, verdict=verdict, send_attempted=False,
                                inference_calls=0, error=error, runtime=runtime, stats=stats,
                                result_extra=result_extra, manifest_extra=manifest_extra)

    try:
        if source is None:
            source = open_source(ROOT / page["path"])
    except Exception as exc:  # noqa: BLE001 - kaynak hatası bütçe harcamaz, kayda geçer
        return blocked("local_error_source", verdict="fail",
                       error={"kind": "source", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        if observations is None:
            observations = observe(ROOT / page["path"])
    except Exception as exc:  # noqa: BLE001 - gözlem hatası bütçe harcamaz, kayda geçer
        return blocked("local_error_observe", verdict="fail",
                       error={"kind": "observe", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        bundle = prepare_arm_inputs(source, observations, image_id=PAGE_IMAGE_ID, arm=arm,
                                    resize_max_side=IMAGE_MAX_SIDE)
        prompt = candidate_prompt([PAGE_IMAGE_ID], observations=bundle["observations"] or None)
    except Exception as exc:  # noqa: BLE001 - yerel hazırlama hatası bütçe harcamaz, kayda geçer
        return blocked("local_error_preparation", verdict="fail",
                       error={"kind": "preparation", "detail": f"{type(exc).__name__}: {exc}"})
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(directory / "response-schema.json", candidate_json_schema())

    # Donmuş ayar denetimi: taşımanın gerçekten gönderebildiği ayarlar (PLAN-3 §4).
    # `raw_page_strategy` sözleşme-üstü bir kavramdır; `image_label_prefix` ise `ChatSettings` alanı
    # değildir — okuyucu onu taşımaya **ayrı kwarg** olarak verir (`read_page`), yani istek gövdesine
    # girer ama ayar nesnesinde yaşamaz. İkisi de "gönderilemeyen ayar" sanılmamalı.
    transport_kwargs = ("raw_page_strategy", "image_label_prefix")
    wanted = {"model": MODEL, **{key: value for key, value in SETTINGS.items()
                                 if key not in transport_kwargs},
              "timeout": float(MODEL_TIMEOUT_SECONDS)}
    supported = {field.name for field in dataclasses.fields(ChatSettings)}
    unsupported_settings = sorted(set(wanted) - supported)
    if unsupported_settings:
        return blocked("blocked_unsupported_setting",
                       result_extra={"blocking_kind": "unsupported_frozen_setting",
                                     "unsupported_settings": unsupported_settings},
                       stats={"unsupported_settings": unsupported_settings})

    # Model keşfi + digest: bilinen bir uyuşmazlıkta gönderim yok (bütçe harcanmaz).
    try:
        installed = find_model(installed_models(), MODEL)
    except Exception as exc:  # noqa: BLE001 - keşif hatası gönderimi engeller
        return blocked("blocked_model_discovery", verdict="fail",
                       result_extra={"blocking_kind": "model_discovery",
                                     "blocking_reason": f"{type(exc).__name__}: {exc}"},
                       error={"kind": "model_discovery", "detail": f"{type(exc).__name__}: {exc}"})
    if installed is None:
        return blocked("blocked_model_discovery", verdict="fail",
                       result_extra={"blocking_kind": "model_discovery",
                                     "blocking_reason": f"model bulunamadı: {MODEL}"},
                       error={"kind": "model_discovery", "detail": f"model bulunamadı: {MODEL}"})
    if installed.digest != EXPECTED_DIGEST:
        return blocked("blocked_model_mismatch", verdict="fail",
                       result_extra={"blocking_kind": "model_changed",
                                     "blocking_reason": (f"digest {installed.digest[:12]}… != "
                                                         f"{EXPECTED_DIGEST[:12]}…")},
                       manifest_extra={"model_metadata_seen": installed.as_dict()})

    runtime = runtime_identity()
    if runtime.get("version") != EXPECTED_RUNTIME:
        write_json(directory / "runtime-identity.json", runtime)
        return blocked("blocked_runtime_mismatch", verdict="blocked", runtime=runtime.get("version"),
                       result_extra={"blocking_kind": "runtime_mismatch",
                                     "blocking_reason": (f"gerçek runtime {runtime.get('version')!r} != "
                                                         f"beklenen {EXPECTED_RUNTIME!r} "
                                                         f"(hata: {runtime.get('error')!r})")},
                       stats={"runtime_seen": runtime.get("version")})

    # Gerçek hazırlanmış girdi kimliği (P0R-FINAL-C): rezervasyondan hemen önce.
    prediction_input = prediction_input_record(page, arm, bundle=bundle, prompt=prompt)
    store_prepared_input(page, arm, prediction_input)

    reservation = reserve_live_call(case_id, phase=phase, arm=arm, split=page["split"],
                                    attempt_dir=directory, attempt_id=attempt_id)
    if not reservation.get("reserved"):
        return blocked("blocked_budget",
                       result_extra={"blocking_kind": "budget",
                                     "blocking_reason": reservation.get("reason")})

    settings = ChatSettings(**{key: value for key, value in wanted.items() if key in supported})
    recorder = Recorder(directory / "inference-log.json", label=f"semread-001b {case_id}")
    chat = RecordedChat(MODEL, settings=settings, recorder=recorder)
    forbidden = _forbidden_terms(page)
    mark_send_state(attempt_id, state_name="sending")
    started = time.perf_counter()
    try:
        outcome = read_page(chat, bundle, forbidden=[term for term in forbidden if term],
                            num_predict=NUM_PREDICT)
    except Exception as exc:  # noqa: BLE001 - gönderim durumu belirsiz: bütçede kalır
        mark_send_state(attempt_id, state_name="dispatch_uncertain",
                        detail=f"{type(exc).__name__}: {exc}")
        return finalize_attempt(attempt_id=attempt_id, directory=directory, page=page, arm=arm,
                                phase=phase, state="transport_error", verdict="fail",
                                send_attempted=True, inference_calls=1,
                                error={"kind": "dispatch_uncertain",
                                       "detail": f"{type(exc).__name__}: {exc}"},
                                runtime=runtime.get("version"), budget=reservation["record"],
                                model_metadata={**installed.as_dict(),
                                                "runtime_version_seen": runtime.get("version")},
                                prediction_input=prediction_input,
                                result_extra={"blocking_kind": "transport_error",
                                              "runtime_matches_expected": False})
    seconds = round(time.perf_counter() - started, 3)
    mark_send_state(attempt_id,
                    state_name=("sent" if outcome.get("outcome") == "answered"
                                else f"transport_{outcome.get('failure_kind') or 'unknown'}"),
                    detail=f"{seconds} sn")

    write_json(directory / "request-manifest.json", outcome.get("request") or {})
    if outcome.get("raw_response") is not None or outcome.get("raw_body") is not None:
        write_json(directory / "response-raw.json",
                   {"schema": "semread-001b-raw/1", "content": outcome.get("raw_response"),
                    "body": outcome.get("raw_body")})
    if outcome.get("parsed") is not None:
        write_json(directory / "response-parsed.json", outcome["parsed"])
    if not (outcome.get("parse") or {}).get("ok"):
        write_json(directory / "response-error.json",
                   {"schema": "semread-001b-error/1", "kind": outcome.get("failure_kind") or "parse",
                    "detail": (outcome.get("parse") or {}).get("error") or outcome.get("detail")})
    write_json(directory / "gate-results.json",
               {"schema": "semread-001b-gates/1", "parse": outcome.get("parse"),
                "references": outcome.get("references"), "truncated": outcome.get("truncated"),
                "leakage": outcome.get("leakage"), "images": outcome.get("images")})
    stats = outcome.get("stats") or {}
    write_json(directory / "resources.json",
               {"schema": "semread-001b-resources/1", "arm": arm, "seconds": seconds,
                "inference_calls": 1, "stats": stats,
                "rss": {"value_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "scope": "bu sürecin RSS'i; toplam sistem/model RAM'i değildir"}})
    write_json(directory / "runtime-identity.json", runtime)

    gates = {
        "answered": outcome.get("outcome") == "answered",
        "parsed": bool((outcome.get("parse") or {}).get("ok")),
        "references_ok": bool((outcome.get("references") or {}).get("ok")),
        "coverage_exact": bool(((outcome.get("references") or {}).get("coverage") or {})
                               .get("exact")),
        "not_truncated": (outcome.get("truncated") or {}).get("state") == "complete",
        "no_leakage": not (outcome.get("leakage") or []),
    }
    verdict = "pass" if all(gates.values()) else "fail"
    if outcome.get("outcome") != "answered":
        state = "transport_error"
    elif not gates["parsed"]:
        state = "parse_error"
    elif verdict == "pass":
        state = "pass"
    else:
        state = "failed_gates"
    finalized = finalize_attempt(
        attempt_id=attempt_id, directory=directory, page=page, arm=arm, phase=phase, state=state,
        verdict=verdict, send_attempted=True, inference_calls=1, gates=gates, seconds=seconds,
        runtime=runtime.get("version"), stats={key: stats.get(key) for key in
                                               ("done_reason", "eval_count", "prompt_eval_count")},
        prediction_input=prediction_input, budget=reservation["record"],
        model_metadata={**installed.as_dict(), "runtime_version_seen": runtime.get("version"),
                        "settings_unsupported": unsupported_settings,
                        "runtime_matches_expected": runtime.get("version") == EXPECTED_RUNTIME,
                        "runtime_error": runtime.get("error")},
        request_hashes_seen=request_hashes(outcome.get("request")),
        result_extra={"runtime_matches_expected": runtime.get("version") == EXPECTED_RUNTIME,
                      "evaluation_scope": "candidate-accuracy",
                      "semantic_evaluation": "provisional-reference",
                      "cad_evaluation": "not_evaluated",
                      "reserved_at": reservation["record"]["reserved_at"],
                      "failure_kind": outcome.get("failure_kind")})
    return {**finalized, "seconds": seconds, "outcome": outcome}



def _forbidden_terms(page: dict) -> list[str]:
    """Kollara gönderilen metinde aranacak referansa özel terimler.

    Kasıtlı olarak **sayı değerleri değil** işaretler aranır: sayfanın kendi bastığı `8`, `Ø` gibi
    işaretler çizimin içeriğidir ve referansla çakışabilir; sızıntı sayılmaz.
    """
    terms = [GOLD_SENTINEL, "gold-sentinel", "(gold)"]
    reference = load_reference(page["page_id"]) or {}
    for claim in reference.get("claims") or []:
        name = (claim.get("target") or {}).get("name")
        if name and len(name) > 3:
            terms.append(str(name))
    return sorted(set(terms))


# ------------------------------------------------------------------ değerlendirme


def _arm_candidates(directory) -> dict | None:
    """Yalnız **matris hücresinin seçtiği** attempt klasörünü okur (varlık taraması yapmaz)."""
    payload = read_json(Path(directory) / "response-parsed.json")
    return payload


def evaluation_run_id(attempt_ids: list[str]) -> str:
    """Değerlendirme koşusunun kimliği: değerlendirici kimliği + seçilen attempt'ler (P0R-7)."""
    return _sha256_text(json.dumps({"evaluation_identity": evaluation_identity(),
                                    "attempts": sorted(attempt_ids)}, sort_keys=True))[:32]


def selected_attempts_payload(matrix_cells: list[dict], run_id: str) -> dict:
    """Seçilen matris hücrelerinin değişmez kanıtı: attempt kimliği + sonuç/manifest hash'i."""
    rows = []
    for cell in matrix_cells:
        attempt = cell.get("attempt")
        if not attempt:
            continue
        directory = Path(attempt)
        manifest_path = directory / "manifest.json"
        result_path = directory / "result.json"
        manifest = read_json(manifest_path) or {}
        rows.append({"page_id": cell["page_id"], "arm": cell["arm"], "cell": cell.get("cell"),
                     "directory": str(directory),
                     "attempt_id": manifest.get("attempt_id")
                     or f"{cell['page_id']}-{cell['arm']}/{directory.name}",
                     "manifest_sha256": sha256_of(manifest_path) if manifest_path.exists() else None,
                     "result_sha256": sha256_of(result_path) if result_path.exists() else None,
                     "prediction_input_identity": manifest.get("prediction_input_identity")})
    return {"schema": "semread-001b-selected-attempts/1", "evaluation_run_id": run_id,
            "evaluation_identity": evaluation_identity(), "attempts": rows, "count": len(rows)}


def write_evaluation_artifacts(payload: dict, acceptance: dict | None, report_text: str | None,
                               selected: dict) -> dict:
    """Değerlendirme kanıtını `evaluations/<evaluation_run_id>/` altına yaz (P0R-FINAL-D).

    Eski bir koşunun klasörü **asla** üzerine yazılmaz: farklı bir kimlik aynı hedefe düşerse
    (bozuk/çakışan durum) yeni klasör sonek alır ve eskisi olduğu gibi kalır. `final/pointer.json`
    yalnız güncel koşuya işaret eder; `final/report.md` okunabilirlik için tutulan bir kopyadır.
    """
    run_id = payload["evaluation_run_id"]
    base = REPORT_ROOT / "evaluations"
    directory = base / run_id
    suffix = 2
    while True:
        existing = read_json(directory / "evaluation.json")
        if existing is None or existing.get("evaluation_run_id") == run_id:
            break
        directory = base / f"{run_id}-{suffix}"
        suffix += 1
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "evaluation.json", payload)
    if acceptance is not None:
        write_json(directory / "acceptance.json", acceptance)
    if report_text is not None:
        (directory / "report.md").write_text(report_text, encoding="utf-8")
    write_json(directory / "selected-attempts.json", selected)
    (REPORT_ROOT / "final").mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "final" / "pointer.json",
               {"schema": "semread-001b-final-pointer/1", "evaluation_run_id": run_id,
                "directory": str(directory.relative_to(REPORT_ROOT)), "written_at": _now(),
                "note": "kanıt koşu klasöründedir; bu dosya yalnız güncel koşuya işaret eder"})
    artifacts = {"schema": "semread-001b-evaluation-artifacts/1", "evaluation_run_id": run_id,
                 "directory": str(directory),
                 "files": sorted(path.name for path in directory.iterdir() if path.is_file())}
    write_json(REPORT_ROOT / "evaluation-artifacts.json", artifacts)
    return artifacts


def evaluate(write_report: bool = True) -> dict:
    manifest = read_json(CORPUS_DIR / "manifest.json") or corpus_manifest()
    matrix_payload = final_matrix()
    matrix_cells = matrix_payload.get("cells") or []
    matrix = {f"{cell['page_id']}-{cell['arm']}": cell for cell in matrix_cells}
    cells_status: list[dict] = []
    per_page: dict[str, dict] = {}
    reference_status: dict[str, dict] = {}
    pages_rows: list[dict] = []
    for page in manifest["pages"]:
        page_id = page["page_id"]
        reference = load_reference(page_id)
        if reference is None:
            reference_status[page_id] = {"present": False,
                                         "note": "referans (gold) yazılmadı"}
            pages_rows.append({"page_id": page_id, "split": page["split"],
                               "reference": "yok", "arms": {}})
            continue
        # Gözlem kimlikleri yalnız referans varsa denetlenir (evaluate ucuz kalmalı: OCR koşmaz).
        observation_ids: list[str] = []
        try:
            observation_ids = [row["id"] for row in _observation_rows(ROOT / page["path"])]
        except Exception:  # noqa: BLE001 - gözlem kimlikleri denetimi yan iştir
            observation_ids = []
        reference_status[page_id] = {"present": True, **check_reference(reference, page,
                                                                       observation_ids)}
        arms: dict[str, dict] = {}
        for arm in (D_ARM, V_ARM, VE_ARM):
            cell = matrix.get(f"{page_id}-{arm}") or {}
            if not cell.get("attempt"):
                cells_status.append({"page_id": page_id, "arm": arm, "cell": "not_run",
                                     "reason": "matris hücresi bir attempt seçmedi"})
                continue
            candidates = _arm_candidates(cell["attempt"])
            if candidates is None:
                cells_status.append({"page_id": page_id, "arm": arm,
                                     "cell": cell.get("cell") or "selected",
                                     "reason": "seçilen attempt klasöründe parsed çıktı yok"})
                continue
            arms[arm] = evaluate_page(reference, {"response": candidates})
        per_page[page_id] = arms
        pages_rows.append({
            "page_id": page_id, "split": page["split"], "reference": "var",
            "arms": {arm: {"matched": result["summary"]["matched"],
                           "claims": result["summary"]["claims"],
                           "candidates": result["summary"]["candidates"]}
                     for arm, result in arms.items()}})

    aggregates = {}
    for arm in (D_ARM, V_ARM, VE_ARM):
        pages = [per_page[page_id][arm] for page_id in per_page if arm in per_page[page_id]]
        if pages:
            aggregates[arm] = aggregate(pages)
    comparison = compare_arms(per_page) if per_page else {"vs_d": {}, "ve_vs_v": {}}
    payload = {
        "schema": "semread-001b-evaluation/1", "created_at": _now(),
        "reference_status": reference_status,
        "reference_quality": {
            "annotator": "agent", "review_status": "provisional",
            "note": ("Referans ajan tarafından hazırlandı; gerçek insan onayı yoktur. Metrikler bu "
                     "niteliği taşır ve ürün doğruluğu sertifikası değildir.")},
        "match_policy": MATCH_POLICY,
        "evaluation_identity": evaluation_identity(), "producer_identity": producer_identity(),
        "evaluation_run_id": evaluation_run_id(
            [cell["attempt"] for cell in matrix_cells if cell.get("attempt")]),
        "evaluation_stale_cells": [
            {"page_id": cell["page_id"], "arm": cell["arm"],
             "why": "attempt'in evaluation_identity'si güncel değil"}
            for cell in matrix_cells if cell.get("attempt") and (
                (read_json(Path(cell["attempt"]) / "manifest.json") or {})
                .get("evaluation_identity") != evaluation_identity())],
        "code_identity": code_identity(),
        "budget": budget_report(),
        "attempt_ledger": attempt_ledger_report(),
        "lifecycle": attempt_lifecycle_report(),
        "pages": pages_rows, "aggregates": aggregates, "comparison": comparison,
        "matrix": matrix_cells, "cells_status": cells_status,
        "matrix_totals": matrix_payload.get("totals") or {},
    }
    if write_report:
        acceptance = write_acceptance(payload)
        report_text = render_report(payload)
        (REPORT_ROOT / "final").mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / "final" / "report.md").write_text(report_text, encoding="utf-8")
    else:
        acceptance, report_text = None, None
    # P0R-FINAL-D: kanıt, değerlendirme koşusu kimliğiyle **sürümlenmiş** klasöre yazılır; eski
    # koşular korunur. `final/` yalnız güncel koşuya işaret eder.
    payload["evaluation_artifacts"] = write_evaluation_artifacts(
        payload, acceptance, report_text,
        selected_attempts_payload(matrix_cells, payload["evaluation_run_id"]))
    write_json(REPORT_ROOT / "evaluation.json", payload)
    return payload


def _observation_rows(path: Path) -> list[dict]:
    from drawingto3d.semantic_candidate_reader import observation_table

    return observation_table(observe(path))


# ------------------------------------------------------------------ kabul ve rapor


def all_attempt_records(state: dict | None) -> list[dict]:
    """`state["attempts"]`i **tek** biçimden okur (PLAN-3 §9).

    Eski kayıt tek sözlüktü; yenisi liste. Karışık/boş durum da bozulmaz.
    """
    records: list[dict] = []
    for value in ((state or {}).get("attempts") or {}).values():
        rows = value if isinstance(value, list) else [value]
        records.extend(row for row in rows if isinstance(row, dict))
    return records


def acceptance_rows(payload: dict) -> dict:
    reference_rows = payload["reference_status"]
    present = [page_id for page_id, row in reference_rows.items() if row.get("present")]
    checked = [page_id for page_id, row in reference_rows.items()
               if row.get("present") and row.get("ok")]
    arms = payload["aggregates"]
    final_pages = {"frozen": [page["page_id"] for page in PAGES if page["split"] == "frozen"]}
    attempts = read_json(state_path()) or {}
    live_attempts = [row for row in all_attempt_records(attempts)
                     if row.get("arm") in (V_ARM, VE_ARM)]
    final_live = [row for row in live_attempts if row.get("split") == "frozen"]
    rows = {
        "B01": {"status": "closed" if (REPORT_ROOT / "snapshot").exists() else "open",
                "evidence": [str(REPORT_ROOT / "snapshot")],
                "detail": "001A snapshot + ayrı bütçe korundu"},
        "B02": {"status": "closed" if len(checked) == len(reference_rows) else "open",
                "evidence": [str(GOLD_DIR)],
                "detail": f"referans niteliği ve hash'ler: {len(checked)}/{len(reference_rows)} sayfa"},
        "B03": {"status": "closed" if (ROOT / "src/drawingto3d/semantic_candidates.py").exists()
                and (ROOT / "src/drawingto3d/semantic_deterministic.py").exists() else "open",
                "evidence": ["src/drawingto3d/semantic_candidates.py",
                             "src/drawingto3d/semantic_candidate_reader.py",
                             "src/drawingto3d/semantic_deterministic.py"],
                "detail": "dar aday sözleşmesi + D adapter + ayrılmış V/VE yolları"},
        "B04": {"status": "closed" if "D" in arms and payload["match_policy"] else "open",
                "evidence": [str(REPORT_ROOT / "evaluation.json")],
                "detail": "eşleştirme/metrikler; verifier başarısı iddia edilmiyor"},
        "B05": {"status": "closed" if (D_ARM in arms and V_ARM in arms and VE_ARM in arms
                                       and len(final_live) >= 2 * len(final_pages["frozen"]))
                else "open",
                "evidence": [str(REPORT_ROOT / "attempts")],
                "detail": ("sabit corpusun D/V/VE sonuçları; kollar bir eksikse açık kalır")},
        "B06": {"status": "closed" if arms and payload.get("comparison", {}).get("vs_d") else "open",
                "evidence": [str(REPORT_ROOT / "final/report.md")],
                "detail": "kalite farkı, recovery/regression, maliyet analizi"},
        "B07": {"status": "closed" if not payload["budget"]["by_arm"].get("?") else "open",
                "evidence": [str(state_path())],
                "detail": "kanıt zinciri/kimlik/cache/bütçe doğrulandı"},
    }
    return rows


def write_acceptance(payload: dict) -> dict:
    rows = acceptance_rows(payload)
    open_rows = sorted(row for row, value in rows.items() if value["status"] != "closed")
    core_open = [row for row in open_rows if row != "B05"]
    conclusion = ("SEMREAD-001B pilot_complete" if not open_rows
                  else f"implementation status: {len(rows) - len(open_rows)}/{len(rows)} kapandı; "
                       f"açık: {open_rows}")
    document = {"schema": "semread-001b-acceptance/1", "created_at": _now(),
                "acceptance": rows, "open": open_rows, "conclusion": conclusion,
                "reference_status": payload["reference_quality"],
                "quality_result": {arm: {"localization_match_rate": value["localization_match_rate"],
                                         "semantic_field_accuracy": value["semantic_field_accuracy"],
                                         "target_binding_accuracy": value["target_binding_accuracy"],
                                         "candidate_overclaim_rate": value["candidate_overclaim_rate"],
                                         "candidate_abstention_rate": value["candidate_abstention_rate"],
                                         "ambiguous_claim_count": value["ambiguous_claim_count"],
                                         "unscorable_extra_candidate_count":
                                             value["unscorable_extra_candidate_count"],
                                         "false_positive_candidate_count":
                                             value["false_positive_candidate_count"],
                                         "candidate_precision": value["candidate_precision"],
                                         "claim_recall": value["claim_recall"],
                                         "omission": value["omission"]}
                                   for arm, value in payload["aggregates"].items()},
                "notes": [("V/VE'nin D'den iyi çıkması completion şartı değildir; sonuç negatifse "
                           "olduğu gibi yazılır"),
                          ("verifier olmadığı için wrong-supported, accepted coverage, otomatik CAD "
                           "güvenliği ve kullanıcı emeği azalması not_evaluated kalır")]}
    write_json(REPORT_ROOT / "acceptance.json", document)
    if core_open:
        state = load_state()
        state["blocked"] = {"open": core_open, "conclusion": conclusion}
        save_state(state)
    return document


def render_report(payload: dict) -> str:
    budget = payload["budget"]
    lines = [
        "# SEMREAD-001B — dar semantic aday pilotu (D / V / VE)",
        "",
        "Bu rapor `eval/semread_001b_pilot.py --evaluate` tarafından **kanıt dosyalarından** üretilir.",
        "Ölçüm kapsamı aday doğruluğudur: circle temsili/delik ayrımı, R vs Ø, basılı değer+birim,",
        "count, THRU/finite/unknown, yazılı derinlik ve callout→target binding. CAD/STEP, fusion,",
        "verifier ve eğitim kapsam dışıdır.",
        "",
        "## Koşu kimliği",
        "",
        f"- HEAD (bilgi): `{_git('rev-parse', 'HEAD')}`",
        f"- üretici (kod) kimliği: `{payload['code_identity']}`",
        f"- değerlendirme kimliği: `{payload['evaluation_identity']}`",
        f"- değerlendirme koşusu: `{payload['evaluation_run_id']}` "
        f"(`{(payload.get('evaluation_artifacts') or {}).get('directory') or 'yazılmadı'}`)",
        f"- model: `{MODEL}` digest `{EXPECTED_DIGEST[:16]}…`; beklenen runtime `{EXPECTED_RUNTIME}`",
        f"- bütçe (inference): dev {budget['dev_used']}/{budget['dev_limit']}, final "
        f"{budget['final_used']}/{budget['final_limit']}, toplam {budget['total_used']}/"
        f"{budget['total_limit']}",
        f"  ({budget['counting_note']})",
        f"- attempt defteri: {payload.get('attempt_ledger', {}).get('total', 'yok')} kayıt "
        f"({payload.get('attempt_ledger', {}).get('by_state', {})}); yerel retler inference "
        f"harcamaz (P0R-FINAL-B)",
        "",
        "## Referans niteliği",
        "",
        f"- annotator=`{payload['reference_quality']['annotator']}`, "
        f"review_status=`{payload['reference_quality']['review_status']}`",
        f"- {payload['reference_quality']['note']}",
        "",
        "## Eşleştirme politikası (final tahminlerden önce sabit)",
        "",
        "```json",
        json.dumps(payload["match_policy"], ensure_ascii=False, indent=1),
        "```",
        "",
        "## Sayfa sayfa durum",
        "",
        "| sayfa | split | referans | " + " | ".join(f"{arm}" for arm in (D_ARM, V_ARM, VE_ARM)) + " |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["pages"]:
        cells = []
        for arm in (D_ARM, V_ARM, VE_ARM):
            value = row["arms"].get(arm)
            cells.append("-" if not value else f"{value['matched']}/{value['claims']}")
        lines.append(f"| {row['page_id']} | {row['split']} | {row['reference']} | "
                     + " | ".join(cells) + " |")
    lines += ["", "## Kollar (toplam)", "",
              "| kol | aday | eşleşen | yerelleştirme | alan doğruluğu | binding | overclaim | çekimser "
              "| belirsiz kalem | kapsam-dışı fazla | yanlış pozitif |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm, value in payload["aggregates"].items():
        lines.append(f"| {arm} | {value['candidates']} | {value['matched']} | "
                     f"{value['localization_match_rate']} | {value['semantic_field_accuracy']} | "
                     f"{value['target_binding_accuracy']} | {value['candidate_overclaim_rate']} | "
                     f"{value['candidate_abstention_rate']} | {value['ambiguous_claim_count']} | "
                     f"{value['unscorable_extra_candidate_count']} | "
                     f"{value['false_positive_candidate_count']} |")
    lines += ["", "not: " + (next(iter(payload["aggregates"].values()), {}).get("metric_note")
                              or MATCH_POLICY["localization_vs_semantic"]),
              "", "## Alan bazında doğruluk", "",
              "| alan | kol | doğru | yanlış | çekimser | scorable | doğruluk |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm, value in payload["aggregates"].items():
        for field, stats in value["fields"].items():
            lines.append(f"| {field} | {arm} | {stats['correct']} | {stats['wrong']} | "
                         f"{stats['abstained']} | {stats['scorable']} | {stats['accuracy']} |")
    comparison = payload.get("comparison") or {}
    lines += ["", "## D'ye göre recovery/regression (yüklem bazında)", "",
              "| yüklem | kol | scorable | kurtarılan | geriye (yanlış) | geriye (çekimser) | net |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm, value in (comparison.get("vs_d") or {}).items():
        for row in value.get("predicate_rows") or []:
            lines.append(f"| {row['predicate']} | {arm} | {row['scorable_target_count']} | "
                         f"{row['recovered_count']} | {row['regressed_wrong_count']} | "
                         f"{row['regressed_abstention_count']} | {row['net_correct_gain']} |")
    lines += ["", "### Toplamlar", ""]
    for arm, value in (comparison.get("vs_d") or {}).items():
        lines += [f"- **{arm}**: recovered={value['recovered']}, "
                  f"regressed(wrong candidate)={value['regressed_wrong_candidate']}, "
                  f"regressed(abstention)={value['regressed_abstention']}, "
                  f"net_correct_gain={value['net_correct_gain']} "
                  f"(paydalar: D {value['d_scorable']}, {arm} {value['arm_scorable']})",
                  f"  — {value['note']}"]
    ve_vs_v = comparison.get("ve_vs_v") or {}
    if ve_vs_v:
        lines.append(f"- VE vs V: better={ve_vs_v.get('ve_better')}, worse={ve_vs_v.get('ve_worse')}, "
                     f"net={ve_vs_v.get('net')}")
    for note in (comparison.get("notes") or []):
        lines.append(f"- not: {note}")
    lines += ["", "## Ölçülmeyenler", "",
              "- Verifier yok: wrong-supported, accepted coverage, otomatik CAD güvenliği ve kullanıcı",
              "  emeği azalması `not_evaluated`.",
              "- Sunucunun görüntüyü **kullandığı** kanıtlanmaz; yalnız isteğin taşıdığı ölçülür.",
              "- Referans ajan tarafından hazırlandı (`provisional`): ürün doğruluğu sertifikası değildir.",
              "- Bu corpus küçüktür ve bilinen bir repo kaynağıdır; bağımsız holdout değildir."]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ worker / CLI


def worker(args) -> int:
    page = next((row for row in PAGES if row["page_id"] == args.page_id), None)
    if page is None:
        raise SystemExit(f"bilinmeyen sayfa: {args.page_id}")
    if args.phase not in PHASES:
        raise SystemExit(f"geçersiz faz: {args.phase!r} (beklenen: {PHASES})")
    outcome = write_live_attempt(page, args.arm, phase=args.phase)
    print(json.dumps({"case_id": outcome["case_id"], "verdict": outcome["verdict"],
                      "directory": outcome["directory"], "phase": args.phase},
                     ensure_ascii=False))
    return 0 if outcome["verdict"] == "pass" else 1


def d_worker(args) -> int:
    page = next((row for row in PAGES if row["page_id"] == args.page_id), None)
    if page is None:
        raise SystemExit(f"bilinmeyen sayfa: {args.page_id}")
    outcome = write_d_attempt(page)
    print(json.dumps({"case_id": outcome["case_id"], "verdict": outcome["verdict"],
                      "candidates": outcome["candidates"]}, ensure_ascii=False))
    return 0


def run_d(split: str | None = None) -> list[dict]:
    results = []
    for page in PAGES:
        if split and page["split"] != split:
            continue
        results.append(write_d_attempt(page))
    return results


def reusable_d_attempt(page: dict) -> dict | None:
    """Deterministic D için bayat denetimi (P0R-6). Şüphede yeniden koşar: inference maliyeti yok."""
    case_id = f"{page['page_id']}-{D_ARM}"
    state = load_state()
    records = (state.get("attempts") or {}).get(case_id) or []
    if isinstance(records, dict):
        records = [records]
    source = ROOT / page["path"]
    page_png = PAGES_DIR / f"{page['page_id']}.png"
    for record in reversed(records):
        if record.get("verdict") != "pass":
            continue
        directory = Path(record.get("directory") or "")
        if not directory.exists() or not (directory / "response-parsed.json").exists():
            continue
        manifest = read_json(directory / "manifest.json") or {}
        if manifest.get("producer_identity") != producer_identity():
            continue
        if (manifest.get("source") or {}).get("sha256") != (sha256_of(source)
                                                            if source.exists() else None):
            continue
        if page_png.exists() and manifest.get("page_png_sha256") != sha256_of(page_png):
            continue
        if manifest.get("candidate_schema") != CANDIDATE_SCHEMA_VERSION:
            continue
        return {"directory": str(directory), "attempt_id": record.get("attempt_id"),
                "verdict": record.get("verdict")}
    return None


def reusable_attempt(case_id: str, page: dict) -> dict | None:
    """Final hücresi için yeniden kullanılabilir geçerli attempt (politika önceden sabit).

    Yeniden kullanım yalnız teknik geçerliliğe bakar: aynı üretici kimliği, **aynı gerçek hazırlanmış
    girdi kimliği** (`prediction_input_identity`, P0R-FINAL-C/D), doğrulanmış model digest'i,
    engellenmemiş verdict ve gerçekten yapılmış gönderim. Sonucun "güzel" olması seçim gerekçesi
    değildir; başarısız/failed bir attempt final hücresini kapatmaz, çağrı olarak sayılır.

    Önbellekteki sayfa PNG hash'i (`page_png_sha256`) yalnız meta veridir: tek başına V/VE tahminini
    yeniden kullanılabilir yapmaz. Ucuz denetimler önce koşar; hazırlanmış girdi kaydı yalnız gerekince
    (üretici kimliği tutan bir aday attempt varsa) okunur — hazırlanamıyorsa yeniden kullanım yoktur.
    """
    state = load_state()
    records = (state.get("attempts") or {}).get(case_id) or []
    if isinstance(records, dict):          # eski tek-kayıt biçimi
        records = [records]
    page_png = PAGES_DIR / f"{page['page_id']}.png"
    source = ROOT / page["path"]
    arm = case_id[len(page["page_id"]) + 1:] if case_id.startswith(f"{page['page_id']}-") else None
    current_identity: str | None = None
    current_loaded = False
    for record in reversed(records):       # en yeni geçerli attempt
        if record.get("verdict") != "pass":
            continue
        directory = Path(record.get("directory") or "")
        if not directory.exists():
            continue
        manifest = read_json(directory / "manifest.json") or {}
        result = read_json(directory / "result.json") or {}
        if manifest.get("producer_identity") != producer_identity():
            continue                       # üretici kimliği değişti → bayat attempt
        # P0R-1: değerlendirme kimliği **aranmaz**. Yalnız evaluator/gold düzeltmesi geçerli ham
        # tahmini geçersiz kılmaz; yeni değerlendirme yeni inference olmadan üretilebilir.
        if manifest.get("input_identity") != input_identity(page):
            continue                       # girdi sözleşmesi/hazırlama değişti
        if manifest.get("model_identity") != model_identity():
            continue
        if manifest.get("expected_digest") != EXPECTED_DIGEST:
            continue
        if (manifest.get("settings") or {}) != SETTINGS:
            continue
        if source.exists() and (manifest.get("source") or {}).get("sha256") != sha256_of(source):
            continue                       # girdi byte'ları aynı mı
        if page_png.exists() and manifest.get("page_png_sha256") != sha256_of(page_png):
            continue
        if result.get("blocking_kind"):
            continue
        if arm in ARMS and result.get("send_attempted") is not True:
            continue                       # gönderilmemiş attempt tahmin sayılmaz
        if (result.get("gates") or {}).get("no_leakage") is not True:
            continue
        if result.get("runtime_matches_expected") is not True and arm != D_ARM:
            continue
        if arm in ARMS:
            if not current_loaded:         # pahalı adım: yalnız aday varken ve bir kez
                current_identity = prediction_input_identity(prepared_input_record(page, arm))
                current_loaded = True
            stored = manifest.get("prediction_input_identity")
            if current_identity is None or stored != current_identity:
                continue                   # gerçek hazırlanmış girdi kanıtlanamıyor → yeniden kullanma
        return {"directory": str(directory), "phase": record.get("phase"),
                "verdict": record.get("verdict"), "gates": record.get("gates"),
                "attempt_id": record.get("attempt_id"),
                "prediction_input_identity": manifest.get("prediction_input_identity")}
    return None


def final_matrix(reuse: bool = True) -> dict:
    """10 sayfa × D/V/VE = 30 hücrenin durumu: hangi attempt, hangisi not_run, kaç yeni çağrı."""
    cells: list[dict] = []
    for page in PAGES:
        for arm in (D_ARM, V_ARM, VE_ARM):
            case_id = f"{page['page_id']}-{arm}"
            if arm == D_ARM:
                reused_d = reusable_d_attempt(page) if reuse else None
                stale = latest_attempt_dir(case_id) is not None and reused_d is None
                cells.append({"page_id": page["page_id"], "split": page["split"], "arm": arm,
                              "cell": "valid_reuse" if reused_d else "to_run",
                              "attempt": reused_d["directory"] if reused_d else None,
                              "stale_detected": bool(stale), "kind": "deterministic"})
                continue
            reused = reusable_attempt(case_id, page) if reuse else None
            if reused:
                cells.append({"page_id": page["page_id"], "split": page["split"], "arm": arm,
                              "cell": "reuse", "attempt": reused["directory"],
                              "seen_phase": reused["phase"], "kind": "vlm"})
            else:
                cells.append({"page_id": page["page_id"], "split": page["split"], "arm": arm,
                              "cell": "to_run", "attempt": None, "kind": "vlm"})
    by_kind: dict[str, int] = {}
    for cell in cells:
        key = f"{cell['kind']}:{cell['cell']}"
        by_kind[key] = by_kind.get(key, 0) + 1
    new_calls = sum(1 for cell in cells if cell["cell"] == "to_run" and cell["kind"] == "vlm")
    new_d_runs = sum(1 for cell in cells if cell["cell"] == "to_run" and cell["kind"] == "deterministic")
    return {"schema": "semread-001b-matrix/1", "created_at": _now(), "cells": cells,
            "totals": {"cells": len(cells), "vlm_cells": FINAL_VLM_CELLS,
                       "d_cells": len(PAGES), "new_vlm_calls": new_calls,
                       "new_d_runs": new_d_runs,
                       "stale_d_cells": sum(1 for c in cells if c.get("stale_detected")),
                       "reused_vlm_cells": sum(1 for c in cells if c["cell"] == "reuse"),
                       "reused_d_cells": sum(1 for c in cells if c["cell"] == "valid_reuse"),
                       "not_run": sum(1 for c in cells if c["cell"] == "not_run"),
                       "by_kind": by_kind},
            "reuse_policy": ("geçerli attempt = pass + aynı üretici kimliği + aynı girdi/model "
                             "kimliği + **aynı gerçek hazırlanmış girdi kimliği** "
                             "(prediction_input_identity) + doğrulanmış digest + gerçekten yapılmış "
                             "gönderim + sızıntı kapısı geçmiş; değerlendirme kimliği yeniden "
                             "kullanımı etkilemez (P0R-1); sayfa PNG hash'i tek başına yeterli "
                             "değildir; politika sonuç görülmeden sabitlendi"),
            "lifecycle": attempt_lifecycle_report(),
            "budget": budget_report()}


def run_live(phase: str, split: str | None = None, arms: tuple[str, ...] = (V_ARM, VE_ARM),
             dry_run: bool = False, reuse: bool = True) -> dict:
    if phase not in PHASES:
        raise SystemExit(f"geçersiz faz: {phase!r} (beklenen: {PHASES})")
    matrix = final_matrix(reuse=reuse)
    jobs: list[Job] = []
    planned: list[dict] = []
    for cell in matrix["cells"]:
        page = next(row for row in PAGES if row["page_id"] == cell["page_id"])
        if split and page["split"] != split:
            continue
        if cell["arm"] not in arms:
            continue
        if cell["cell"] != "to_run":
            planned.append({**cell, "action": "skip"})
            continue
        page_png = PAGES_DIR / f"{page['page_id']}.png"
        if not page_png.exists():
            planned.append({**cell, "action": "blocked_missing_page_png"})
            continue
        planned.append({**cell, "action": "call"})
        jobs.append(Job(
            id=f"{JOB_PREFIX}{cell['page_id']}-{cell['arm']}-{phase}",
            command=[sys.executable, str(ROOT / "eval/semread_001b_pilot.py"),
                     "--worker", "--page-id", page["page_id"], "--arm", cell["arm"],
                     "--phase", phase],
            inputs=[page_png],
            timeout_seconds=CASE_TIMEOUT_SECONDS))
    remaining = PHASE_LIMITS[phase] - budget_report()[f"{phase}_used"]
    plan = {"schema": "semread-001b-run-plan/1", "phase": phase, "split": split or "hepsi",
            "arms": list(arms), "jobs": [job.as_dict() for job in jobs], "cells": planned,
            "planned_real_calls": len(jobs), "remaining_phase_budget": remaining,
            "reuse": reuse, "budget": budget_report()}
    if dry_run:
        return {"dry_run": True, "inference_calls": 0, "plan": plan,
                "note": "dry-run hiç çağrı yapmaz ve sayaç harcamaz"}
    if len(jobs) > remaining:
        return {"dry_run": False, "refused": True, "plan": plan,
                "reason": (f"plan {len(jobs)} çağrı istiyor ama {phase} fazında kalan bütçe "
                           f"{remaining}; hiçbir çağrı yapılmadı")}
    runner = LabRunner(LAB_ROOT)
    executed = runner.execute(jobs)
    return {"dry_run": False, "executed": executed, "plan": plan, "budget": budget_report()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEMREAD-001B pilot sürücüsü")
    parser.add_argument("--corpus", action="store_true", help="corpus manifesti + sayfa PNG'leri")
    parser.add_argument("--d", action="store_true", help="D kolunu çalıştır (sıfır inference)")
    parser.add_argument("--live", action="store_true", help="V/VE kollarını çalıştır (gerçek çağrı)")
    parser.add_argument("--split", choices=("dev", "frozen"), default=None,
                        help="veri bölümü; verilmezse 10 sayfanın hepsi")
    parser.add_argument("--phase", choices=list(PHASES), default=None,
                        help="çağrının amacı: dev (≤10) ya da final (≤20)")
    parser.add_argument("--matrix", action="store_true", help="30 hücrenin durumu (çağrı yok)")
    parser.add_argument("--lifecycle", action="store_true",
                        help="attempt yaşam döngüsü/geçmiş tutarlılığı (çağrı yok)")
    parser.add_argument("--no-reuse", action="store_true",
                        help="geçerli attempt'leri yeniden kullanma (politika dışı, tanı için)")
    parser.add_argument("--arms", default="V,VE")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--budget", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="plan + bütçe; çağrı yok")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--d-worker", action="store_true")
    parser.add_argument("--page-id")
    parser.add_argument("--arm", choices=list(ARMS))
    args = parser.parse_args(argv)

    if args.worker:
        return worker(args)
    if args.d_worker:
        return d_worker(args)
    if args.budget:
        print(json.dumps(budget_report(), ensure_ascii=False, indent=2))
        return 0
    if args.corpus:
        manifest = write_corpus()
        print(json.dumps({"totals": manifest["totals"],
                          "split_violations": manifest["split_violations"]},
                         ensure_ascii=False, indent=2))
        return 0
    if args.matrix:
        print(json.dumps(final_matrix(reuse=not args.no_reuse), ensure_ascii=False, indent=2))
        return 0
    if args.lifecycle:
        print(json.dumps({"lifecycle": attempt_lifecycle_report(),
                          "attempt_ledger": attempt_ledger_report()},
                         ensure_ascii=False, indent=2))
        return 0
    if args.dry_run:
        if not args.phase:
            raise SystemExit("--dry-run için --phase gerekli (dev|final)")
        print(json.dumps(run_live(args.phase, args.split, tuple(args.arms.split(",")),
                                  dry_run=True, reuse=not args.no_reuse),
                         ensure_ascii=False, indent=2))
        return 0
    if args.d:
        results = run_d(args.split)
        print(json.dumps([{"case_id": row["case_id"], "candidates": row["candidates"],
                           "verdict": row["verdict"]} for row in results],
                         ensure_ascii=False, indent=2))
        return 0
    if args.live:
        if not args.phase:
            raise SystemExit("--live için --phase gerekli (dev|final)")
        print(json.dumps(run_live(args.phase, args.split, tuple(args.arms.split(",")),
                                  reuse=not args.no_reuse),
                         ensure_ascii=False, indent=2))
        return 0
    if args.evaluate:
        payload = evaluate()
        print(json.dumps({"aggregates": {arm: {"candidate_precision": value["candidate_precision"],
                                               "claim_recall": value["claim_recall"]}
                                         for arm, value in payload["aggregates"].items()},
                          "reference_present": sum(1 for row in payload["reference_status"].values()
                                                   if row.get("present")),
                          "evaluation_run_id": payload["evaluation_run_id"],
                          "evaluation_artifacts": payload.get("evaluation_artifacts"),
                          "attempt_ledger": payload.get("attempt_ledger")},
                         ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
