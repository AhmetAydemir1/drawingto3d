"""SEMREAD-001D — dev girdi kurulumu + raw-page kimliği (PLAN-17 §31–§41, §93).

Dört dev sayfanın (ploy-plate §32) ham sayfa PNG'sini **repodaki kaynaktan** yeniden üretir ve
kimliğini kayda geçirir — canlı çağrı öncesi açık olan asıl blocker budur (§31: dry-run
`planned_real_calls 0` çünkü 001D corpus PNG'leri kurulmamış):

* source-of-truth **repo kaynak dosyası + sayfa seçicisi + güncel preprocessing sözleşmesi**dir
  (§33); `out/lab/semread-001c/**` historical evidence'dır, input kaynağı değildir (§34) — kör
  kopya yok, kurulum `source → güncel deterministik hazırlama → prepared raw page` zinciriyle
  yapılır; 001B/001C byte'larıyla eşitlik **hash ile kanıtlanır** (§34).
* kayıt sayfa başına (§35): source path/sha256/boyut, sayfa index'i + rotasyonu (view seçicisi),
  prepared sha256/width/height, `input_identity` ve `preprocessing_identity`;
* **V/VE raw page invariantı** (§36): aynı sayfada kolların `image-1` byte'ı aynı olmalı — VE
  yalnız ekstra kanıt (overlay + gözlem tablosu) alır; ikisi **ayrı hash'lenir** (§37) ve tam
  girdi kimlikleri farklıdır;
* girdi hazırlama **inference değildir** (§38): render/resize/overlay/serileştirme/hash bütçe
  harcamaz; araç hiçbir model çağrısı yapmaz (0 inference) ve defter **kurmaz** — `--write` yalnız
  `corpus/pages/*.png` + `corpus/input-identity.json` + kanonik `corpus/prepared-inputs/*.json`
  yazar (budget_report salt-okur okunur);
* **sızıntı yasağı** (§39): gold / beklenen cevap / referans STEP okunmaz — yalnız kaynak +
  deterministik gözlem katmanı;
* **fail-closed**: kaynak yoksa ya da mevcut sayfa PNG beklenen byte'larla uyuşmuyorsa hiçbir şey
  yazılmaz (üzerine yazma yok); `--check` salt-okurdur ve kurulumu **yeniden türeterek** karşılaştırır
  (§40 "rebuild deterministic" + "preprocessing identity current").

001D corpus'unda **yalnız dört dev sayfa** kurulur: final holdout kullanıcıdan gelecek yeni
çizimlerdir (§82) ve repo'nun eski frozen sayfaları 001D final corpus'u sayılmaz.

Kabul kapısı (§41): kurulum sonrası `--dry-run --phase dev` Round 1 için `planned_real_calls = 4`
vermek zorundadır; 0 ise inference yoktur.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_pilot():
    """Pilot'u test'lerin yaptığı gibi importlib ile yükle (kimlik fonksiyonlarının tek kaynağı)."""
    spec = importlib.util.spec_from_file_location("semread_001d_inputs_pilot",
                                                  ROOT / "eval" / "semread_001b_pilot.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()

EXPERIMENT = "semread-001d"
SCHEMA = "semread-001d-input-identity/1"
RECORD_NAME = "input-identity.json"

# PLAN-17 §57: Round 1 = dev-plate-pocket + dev-flange-book × V/VE (tam 4 çağrı). Bu deklarasyon
# kayıtta görünür kalır ve kurulumun Round 1 hücrelerini açtığı buradan denetlenir (§41).
ROUND1_PAGES = ("dev-plate-pocket", "dev-flange-book")

# PLAN-17 §34: historical artifact'lar yalnız byte-eşitlik **kanıtı** için okunur (input kaynağı
# değildir). 001B ve 001C'nin prepared sayfaları aynı kaynaktan üretildiyse hash'ler eşit çıkar.
CROSS_CHECK_EXPERIMENTS = ("semread-001b", "semread-001c")

# Kayıt karşılaştırmasında "değişken" sayılan alanlar (doğrulamaya girmez): zaman damgası, bütçe
# anlık görüntüsü ve kurulum defteri. Kimlik taşıyan her şey karşılaştırılır.
VOLATILE_KEYS = ("created_at", "budget_snapshot", "materialization", "honesty_note")
STABLE_KEYS = ("versions", "identities", "preprocessing_files", "settings", "pages",
               "round1_cells", "cross_check")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _guard_experiment() -> None:
    if pilot.EXPERIMENT_NAME != EXPERIMENT:
        raise SystemExit(f"yanlış deney kökü: {pilot.EXPERIMENT_NAME!r} "
                         f"(beklenen {EXPERIMENT!r}) — önce `use_experiment({EXPERIMENT!r})`")


def dev_pages() -> tuple[dict, ...]:
    """DEV split'indeki sayfalar — 001D kurulumu yalnız bunları hazırlar (§32)."""
    return tuple(page for page in pilot.PAGES if page["split"] == "dev")


def _page_png(page: dict) -> bytes:
    """Sayfanın deterministik hazırlanmış ham PNG'si (write_corpus'un yazdığı byte'lar)."""
    return pilot.open_source(pilot.ROOT / page["path"]).frame_png


def _png_size(png: bytes) -> tuple[int, int]:
    frame = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if frame is None:
        raise SystemExit("hazırlanan sayfa PNG çözülemedi")
    height, width = frame.shape[:2]
    return int(width), int(height)


# ------------------------------------------------------------------ kimlik blokları


def _versions() -> dict:
    return {"contract_version": pilot.CONTRACT_VERSION,
            "schema_version": pilot.CANDIDATE_SCHEMA_VERSION,
            "reader_version": pilot.CANDIDATE_READER_VERSION}


def _identities() -> dict:
    return {"producer_identity": pilot.producer_identity(),
            "evaluation_identity": pilot.evaluation_identity(),
            "preprocessing_identity": pilot.preprocessing_identity()}


def _preprocessing_files() -> dict:
    return {relative: (pilot.sha256_of(pilot.ROOT / relative)
                       if (pilot.ROOT / relative).exists() else None)
            for relative in pilot.PREPROCESSING_FILES}


def _settings() -> dict:
    return {"image_max_side": pilot.IMAGE_MAX_SIDE,
            "raw_page_strategy": pilot.SETTINGS["raw_page_strategy"]}


def _stable_block(key: str):
    return {"versions": _versions, "identities": _identities,
            "preprocessing_files": _preprocessing_files, "settings": _settings}[key]()


# ------------------------------------------------------------------ türetim (salt-okur)


def derive_page(page: dict) -> dict:
    """Bir dev sayfanın kimlik kaydını **yeniden türet** (disk'e yazmaz).

    Zincir kanoniktir: `open_source` → `observe` → `prepare_arm_inputs` → `prediction_input_record`
    (pilot'un `prepared_input_record`'uyla aynı bileşim; tek kaynak fonksiyonlar, kopya tanım yok).
    `input_identity` burada yoktur: o, sayfa PNG'sinin **diskteki** byte'larına bağlıdır ve kurulum
    tamamlandıktan sonra eklenir.
    """
    source_path = pilot.ROOT / page["path"]
    source = pilot.open_source(source_path)
    raw_png = source.frame_png
    width, height = _png_size(raw_png)
    # Gözlem **bir kez** alınır: aynı girdi için deterministiktir ve iki kol da aynı gözlemi görür
    # (pilot `prepared_input_record`'u kolu başına yeniden gözler; çıktı birebir aynıdır — parite
    # testi `test_derived_arm_records_match_the_pilots_own_preparation` bunu pinler).
    observations = pilot.observe(source_path)
    arms: dict[str, dict] = {}
    for arm in pilot.ARMS:
        bundle = pilot.prepare_arm_inputs(source, observations, image_id=pilot.PAGE_IMAGE_ID,
                                          arm=arm, resize_max_side=pilot.IMAGE_MAX_SIDE)
        prompt = pilot.candidate_prompt([pilot.PAGE_IMAGE_ID], observations=bundle["observations"] or None)
        arms[arm] = pilot.prediction_input_record(page, arm, bundle=bundle, prompt=prompt)
    source_record = source.as_record()
    source_record["path"] = page["path"]  # göreli yol — kayıt taşınabilir kalır
    source_record["bytes"] = source_path.stat().st_size
    v_raw = arms[pilot.ARMS[0]]["images"][0]["sha256"]
    ve_raw = arms[pilot.ARMS[1]]["images"][0]["sha256"]
    return {
        "page_id": page["page_id"], "split": page["split"], "group": page["group"],
        "source": source_record,
        "raw_page": {"file": f"corpus/pages/{page['page_id']}.png", "sha256": _sha256_bytes(raw_png),
                     "width_px": width, "height_px": height, "bytes": len(raw_png)},
        "arms": arms,
        "v_ve_raw_page_identical": v_raw == ve_raw,
        "v_ve_identities_differ": (pilot.prediction_input_identity(arms[pilot.ARMS[0]])
                                   != pilot.prediction_input_identity(arms[pilot.ARMS[1]])),
    }


def derive_all() -> dict:
    """Tüm dev sayfaların türetimi — herhangi biri başarısızsa istisna yukarı gider (fail-closed)."""
    return {page["page_id"]: derive_page(page) for page in dev_pages()}


def round1_cells(pages: tuple[dict, ...]) -> list[dict]:
    """Round 1 hücreleri (§57) — deklarasyon ile kurulum çelişirse durur (drift dedektörü)."""
    have = {page["page_id"] for page in pages}
    missing = [page_id for page_id in ROUND1_PAGES if page_id not in have]
    if missing:
        raise SystemExit(f"Round 1 sayfası dev corpus'ta yok: {missing} (ROUND1_PAGES drifti)")
    return [{"page_id": page_id, "arm": arm} for page_id in ROUND1_PAGES for arm in pilot.ARMS]


def cross_check(derived: dict) -> dict:
    """001B/001C prepared sayfalarıyla byte-eşitlik kanıtı (§34) — kör kopya değil, karşılaştırma."""
    result: dict[str, dict] = {}
    for experiment in CROSS_CHECK_EXPERIMENTS:
        pages_dir = pilot.ROOT / "out" / "lab" / experiment / "corpus" / "pages"
        entry: dict = {"dir": f"out/lab/{experiment}/corpus/pages", "present": pages_dir.is_dir(),
                       "pages": {}}
        for page_id, record in derived.items():
            path = pages_dir / f"{page_id}.png"
            digest = _sha256_bytes(path.read_bytes()) if path.exists() else None
            entry["pages"][page_id] = {
                "sha256": digest,
                "identical": digest is not None and digest == record["raw_page"]["sha256"],
            }
        entry["identical_count"] = sum(1 for row in entry["pages"].values() if row["identical"])
        result[experiment] = entry
    return result


# ------------------------------------------------------------------ fark raporlama


def _diff(prefix: str, expected, actual, problems: list[str], *, skip: frozenset = frozenset(),
          limit: int = 12) -> None:
    """İki JSON ağacının farklarını yol adlarıyla listele (ilk `limit` fark)."""
    if len(problems) >= limit:
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key in skip:
                continue
            if key not in expected:
                problems.append(f"{prefix}.{key}: fazla (yeni tarafta var)")
            elif key not in actual:
                problems.append(f"{prefix}.{key}: eksik (yeni tarafta yok)")
            else:
                _diff(f"{prefix}.{key}", expected[key], actual[key], problems, skip=skip, limit=limit)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            problems.append(f"{prefix}: uzunluk {len(expected)} ≠ {len(actual)}")
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            _diff(f"{prefix}[{index}]", left, right, problems, skip=skip, limit=limit)
        return
    if expected != actual:
        problems.append(f"{prefix}: {json.dumps(expected, ensure_ascii=False)[:80]} ≠ "
                        f"{json.dumps(actual, ensure_ascii=False)[:80]}")


# ------------------------------------------------------------------ kurulum (--write)


def materialize() -> dict:
    """Dev sayfa PNG'lerini kur + kimlik kaydını yaz. Çelişkide hiçbir şey yazılmaz (§34/§40)."""
    _guard_experiment()
    blocked = pilot.contract_identity_block()
    if blocked is not None:
        raise SystemExit(f"run-contract kimliği uyuşmuyor, kurulum yok: {blocked}")
    pages = dev_pages()
    if not pages:
        raise SystemExit("hiç dev sayfası yok — kurulacak bir şey yok")

    derived = {page["page_id"]: derive_page(page) for page in pages}
    pngs = {page["page_id"]: _page_png(page) for page in pages}
    round1 = round1_cells(pages)  # drift denetimi: kayıt yazılmadan önce

    # 1) Mevcut dosyalar: üzerine yazmadan doğrula. Çelişki = dur (kurulum deterministik olmalı).
    mismatched = [page_id for page_id in derived
                  if (pilot.PAGES_DIR / f"{page_id}.png").exists()
                  and (pilot.PAGES_DIR / f"{page_id}.png").read_bytes() != pngs[page_id]]
    if mismatched:
        raise SystemExit(f"mevcut sayfa PNG beklenen byte'larla uyuşmuyor, üzerine yazılmadı: "
                         f"{mismatched}")
    written = [page_id for page_id in derived
               if not (pilot.PAGES_DIR / f"{page_id}.png").exists()]
    pilot.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for page_id in written:
        (pilot.PAGES_DIR / f"{page_id}.png").write_bytes(pngs[page_id])
    verified = [page_id for page_id in derived if page_id not in written]

    # 2) Girdi kimliği (sayfa PNG'si artık diskte) + kanonik hazırlanmış-girdi kayıtları.
    for page in pages:
        record = derived[page["page_id"]]
        record["input_identity"] = pilot.input_identity(page)
        for arm in pilot.ARMS:
            pilot.store_prepared_input(page, arm, record["arms"][arm])

    record = {
        "schema": SCHEMA, "created_at": _now(), "experiment": EXPERIMENT,
        "versions": _versions(), "identities": _identities(),
        "preprocessing_files": _preprocessing_files(), "settings": _settings(),
        "pages": [derived[page["page_id"]] for page in pages],
        "round1_cells": round1,
        "cross_check": cross_check(derived),
        "budget_snapshot": pilot.budget_report(),
        "materialization": {
            "pages_written": written, "pages_verified": verified,
            "record": f"corpus/{RECORD_NAME}",
            "root": f"out/lab/{EXPERIMENT}",
        },
        "honesty_note": (
            "Bu kayıt deney kökünün corpus katmanındadır (pilot'un kanonik yolu, §36) — defter "
            "değildir: state.json/attempts yalnız ilk gerçek çağrıda kurulur. Yalnız dört dev sayfa "
            "kuruldu; final holdout kullanıcıdan gelecek yeni çizimlerdir (§82) ve repo'nun eski "
            "frozen sayfaları 001D corpus'u sayılmaz. Byte'lar 001B/001C ile karşılaştırıldı "
            "(§34) — eşitlik kanıtı `cross_check` altındadır."),
    }
    pilot.write_json(pilot.CORPUS_DIR / RECORD_NAME, record)
    return {"yazıldı": written, "doğrulandı": verified,
            "kayıt": str(pilot.CORPUS_DIR / RECORD_NAME),
            "sayfalar": [page["page_id"] for page in pages]}


# ------------------------------------------------------------------ doğrulama (--check)


def check() -> dict:
    """Kayıt + kurulumun birebirliğini **yeniden türeterek** doğrula (salt-okur, yazmaz)."""
    _guard_experiment()
    record_path = pilot.CORPUS_DIR / RECORD_NAME
    loaded = pilot.read_json(record_path)
    if not isinstance(loaded, dict):
        return {"ok": False, "problems": [f"kimlik kaydı yok: {record_path} — önce `--write`"],
                "pages_checked": 0}
    problems: list[str] = []
    pages = dev_pages()
    derived = derive_all()

    for key in ("versions", "identities", "preprocessing_files", "settings"):
        _diff(key, loaded.get(key), _stable_block(key), problems)
    _diff("round1_cells", loaded.get("round1_cells"), round1_cells(pages), problems)
    _diff("cross_check", loaded.get("cross_check"), cross_check(derived), problems)

    recorded_pages = {page.get("page_id"): page for page in (loaded.get("pages") or [])
                      if isinstance(page, dict) and page.get("page_id")}
    for page in pages:
        page_id = page["page_id"]
        recorded = recorded_pages.get(page_id)
        if recorded is None:
            problems.append(f"kayıt sayfası eksik: {page_id}")
            continue
        _diff(f"pages[{page_id}]", recorded, derived[page_id], problems,
              skip=frozenset({"input_identity"}))
        target = pilot.PAGES_DIR / f"{page_id}.png"
        if not target.exists():
            problems.append(f"sayfa PNG yok: {target}")
        else:
            on_disk = _sha256_bytes(target.read_bytes())
            if on_disk != recorded.get("raw_page", {}).get("sha256"):
                problems.append(f"sayfa PNG kayıttan farklı: {page_id} "
                                f"({on_disk[:16]}… ≠ "
                                f"{str(recorded.get('raw_page', {}).get('sha256'))[:16]}…)")
        current = pilot.input_identity(page)
        if current != recorded.get("input_identity"):
            problems.append(f"input_identity değişmiş: {page_id} (kayıt ≠ şimdi)")
    extra = sorted(set(recorded_pages) - {page["page_id"] for page in pages})
    if extra:
        problems.append(f"kayıtta fazla sayfa var: {extra}")

    return {"ok": not problems, "problems": problems, "pages_checked": len(pages),
            "record": str(record_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="dev sayfa PNG'lerini kur + corpus/input-identity.json yaz")
    parser.add_argument("--check", action="store_true",
                        help="kayıt + kurulumu yeniden türeterek doğrula (salt-okur; varsayılan)")
    args = parser.parse_args(argv)
    pilot.use_experiment(EXPERIMENT)
    if args.write:
        result = materialize()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
