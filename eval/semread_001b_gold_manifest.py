"""SEMREAD-001B — izlenen (git'te) kanonik gold spec'ler ve manifest (PLAN-8 §3–§4, §13; PLAN-9 §6, §14–§17).

Neden var: benchmark'ın **gerçeği** artık `eval/semread_001b_gold/` altında izlenir. Daha önce
spec dosyaları yalnız `out/lab/semread-001b/corpus/gold-specs/` altındaydı ve `out/` gitignored
olduğu için temiz bir klon gerçeği yeniden kuramıyordu (PLAN-8 §3). Üretilmiş dosyalar
(`gold-src/`, `gold/`) çalışma zamanı çıktısı olarak kalır ama izlenen spec'ten **yeniden
üretilebilir** olmalıdır.

Zincir:

    eval/semread_001b_gold/specs/<page>.json      (izlenen kanonik spec)
      --eval/semread_001b_gold_regions.py-->      out/lab/.../gold-src/<page>.json
      --eval/semread_001b_reference.py-->         out/lab/.../gold/<page>.json
      --eval/semread_001b_pilot.py check_reference--> B02

Komutlar:

    --write    izlenen spec'lerden manifesti üret/güncelle (hash'ler + kararlı gold kimliği)
    --check    manifesti doğrula: spec/kaynak/referans hash'leri, claim sayısı, nitelikler,
               gold_content_identity
    --freeze   P5 kapısı (atomik, PLAN-9 §16–§17): 10/10 kapsam + tüm hash'ler + TÜM sayfaların
               izlenen spec'ten **yeniden üretim kanıtı** + gold_content_identity; başarıda
               dondurma kaydını (FREEZE.json) yazar — ayrıca `--verify` çalıştırmak gerekmez
    --verify   izlenen spec'ten referansı yeniden üret (gözlem çıkarımı dahil) ve manifestteki
               referans hash'iyle karşılaştır; `--page` ile sayfa seçilebilir

Doğrulama kuralları (PLAN-8 §10, §11, §25; PLAN-9 §6, §15):

* ölçülen hedef kutusu: dört sonlu değer, `0<=x0<x1<=1`, `0<=y0<y1<=1`, pafta sınırları içinde ve
  gerekçesi yazılı (`target_reason` / `measurement_reason` ya da kanıt metninde ölçüm ifadesi);
* raster sayfa: `vision_checked=true` **ve** her claim'in `source_evidence`ı `vision` içermeli;
* döngüsel ölçek kanıtı yasak (§11 + §6): bir claim `corroboration.independent_scale` beyan
  ediyorsa dayanak değer **ne kendi** yazılı değeri **ne de başka bir değerlendirilen Ø/R
  claim'inin** yazılı değeri olabilir — kök, claim setinin dışındaki bağımsız bir datuma
  çözülmelidir (A→B, B→A geçemez);
* `gold_content_identity` (§15): manifest zaman damgası **taşımaz**; dondurmanın bağlandığı
  kimlik yalnız gerçeği etkileyen alanların kanonik sha256'sıdır — aynı içerik her koşuda aynı
  kimliği ve aynı manifest baytlarını verir.

Bu araç hiç model çağırmaz; `--verify` / `--freeze` dışında OCR/render de çalıştırmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TRACKED = ROOT / "eval" / "semread_001b_gold"
SPECS = TRACKED / "specs"
MANIFEST = TRACKED / "manifest.json"
MANIFEST_SCHEMA = "semread-001b-gold-manifest/1"
FREEZE_SCHEMA = "semread-001b-freeze/1"

# §15: kararlı gold kimliğine giren alanlar — zaman/yol gibi üstveri kimliğe girmez.
IDENTITY_FIELDS = ("page_id", "source_sha256", "spec_sha256", "reference_sha256",
                   "claim_count", "vision_checked", "exhaustiveness")

# Ölçüm gerekçesi ararken kabul edilen ifadeler (Türkçe/İngilizce ölçüm sözcükleri).
_MEASURE_WORDS = ("ölç", "measure", "piksel", "pixel")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pilot():
    """Pilot modülünü yükler: sayfa tablosu (`PAGES`) ve korpus gold dizini tek kaynaktır."""
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_gold_manifest",
                                                  ROOT / "eval" / "semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise SystemExit("pilot modülü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pages() -> list[dict]:
    return list(_pilot().PAGES)


def gold_dir() -> Path:
    return Path(_pilot().GOLD_DIR)


def gold_src_dir() -> Path:
    return Path(_pilot().GOLD_SRC_DIR) if hasattr(_pilot(), "GOLD_SRC_DIR") \
        else ROOT / "out/lab/semread-001b/corpus/gold-src"


def spec_path(page_id: str) -> Path:
    return SPECS / f"{page_id}.json"


def load_spec(page_id: str) -> dict | None:
    path = spec_path(page_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------- spec doğrulaması (PLAN-8 §10/§11)


def _measure_reason(spec: dict, claim: dict) -> bool:
    """Ölçülen kutunun gerekçesi yazılmış mı? (§10: 'reason documented')"""
    candidates = [claim.get("target_reason"), spec.get("measurement_reason"),
                  spec.get("annotation_method"), claim.get("evidence"),
                  claim.get("source_evidence"), " ".join(spec.get("notes") or [])]
    for item in candidates:
        text = str(item or "").lower()
        if any(word in text for word in _MEASURE_WORDS):
            return True
    return False


def _box_problem(box, frame: tuple[int, int] | None) -> str | None:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return "ölçülen kutu dört sayı olmalı"
    try:
        x0, y0, x1, y1 = (float(value) for value in box)
    except (TypeError, ValueError):
        return "ölçülen kutu değerleri sayıya çevrilemedi"
    if not all(math.isfinite(value) for value in (x0, y0, x1, y1)):
        return "ölçülen kutuda NaN/inf var"
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        return f"ölçülen kutu 0..1 aralığında ve sıralı olmalı: {[x0, y0, x1, y1]}"
    if frame:
        width, height = frame
        if x1 * width > width + 0.5 or y1 * height > height + 0.5:
            return "ölçülen kutu pafta sınırlarının dışında"
    return None


def _evaluated_size_claims(claims: list[dict]) -> list[tuple[str, float]]:
    """Değerlendirilen Ø/R claim seti (§6): yazılı sayısal `size` taşıyan çap/yarıçap claim'leri.

    Bir ölçek dayanağı bu setin **içindeki** bir değere çözülüyorsa kanıt bağımsız sayılmaz
    (karşılıklı döngüsellik dâhil: A→B, B→A); kök setin dışındaki bir datum olmalıdır (doğrusal
    ölçü, bilinen referans, güvenilir kalibrasyon …).
    """
    rows: list[tuple[str, float]] = []
    for index, claim in enumerate(claims, start=1):
        form = str(claim.get("form") or "").strip().lower()
        size = claim.get("size")
        if form not in ("diameter", "radius", "r") or isinstance(size, bool) \
                or not isinstance(size, (int, float)):
            continue
        rows.append((str(claim.get("claim_id") or f"#{index}"), float(size)))
    return rows


def validate_spec(page: dict, spec: dict, frame: tuple[int, int] | None = None) -> list[str]:
    """İzlenen spec'in yapısal + kanıt kurallarını denetler. Boş liste = sorun yok."""
    problems: list[str] = []
    page_id = page["page_id"]
    raster = page.get("type") == "raster"
    if not spec.get("scope"):
        problems.append(f"{page_id}: kapsam (scope) yazılmamış")
    scope = spec.get("exhaustiveness")
    if not isinstance(scope, dict) or not scope.get("scope"):
        problems.append(f"{page_id}: exhaustiveness yapılı değil")
    if raster and not spec.get("vision_checked"):
        problems.append(f"{page_id}: raster sayfa ama vision_checked=true değil (§16)")
    claims = spec.get("claims") or []
    if not claims:
        problems.append(f"{page_id}: hiç claim yok")
    evaluated = _evaluated_size_claims(claims)
    seen: set[str] = set()
    for index, claim in enumerate(claims, start=1):
        claim_id = claim.get("claim_id") or f"#{index}"
        if claim_id in seen:
            problems.append(f"{page_id}/{claim_id}: tekrarlanan claim_id")
        seen.add(claim_id)
        observation = claim.get("target_observation")
        box = claim.get("target_box_norm")
        if not observation and not box:
            problems.append(f"{page_id}/{claim_id}: hedef yok (target_observation ya da kutu)")
        if box:
            problem = _box_problem(box, frame)
            if problem:
                problems.append(f"{page_id}/{claim_id}: {problem}")
            elif not _measure_reason(spec, claim):
                problems.append(f"{page_id}/{claim_id}: ölçülen kutunun gerekçesi yazılmamış (§10)")
        for field in ("evidence", "source_evidence"):
            if not str(claim.get(field) or "").strip():
                problems.append(f"{page_id}/{claim_id}: {field} boş")
        if raster and "vision" not in str(claim.get("source_evidence") or "").lower():
            problems.append(f"{page_id}/{claim_id}: raster claim'de görsel doğrulama kanıtı yok (§16)")
        corroboration = claim.get("corroboration")
        if corroboration:
            problems.extend(_corroboration_problem(page_id, claim_id, claim, corroboration,
                                                   evaluated))
    return problems


def _corroboration_problem(page_id: str, claim_id: str, claim: dict, corroboration,
                           evaluated: list[tuple[str, float]]) -> list[str]:
    """§11 + §6: döngüsel ölçek kanıtını reddet.

    Kanıt ne claim'in **kendi** yazılı değerine (yerel döngüsellik) ne de **başka bir
    değerlendirilen Ø/R claim'inin** yazılı değerine (grafik döngüsellik: A→B, B→A) dayanabilir;
    kök, claim setinin dışındaki bağımsız bir datuma çözülmelidir.
    """
    problems: list[str] = []
    if not isinstance(corroboration, dict):
        return [f"{page_id}/{claim_id}: corroboration sözlük olmalı"]
    kind = corroboration.get("kind")
    if kind not in ("none", "independent_scale"):
        problems.append(f"{page_id}/{claim_id}: corroboration.kind kapalı kümede değil: {kind!r}")
        return problems
    if kind == "none":
        return problems
    basis_value = corroboration.get("basis_value")
    if basis_value is None or not corroboration.get("basis"):
        problems.append(f"{page_id}/{claim_id}: bağımsız ölçek kanıtı için `basis` ve `basis_value` "
                        f"zorunlu")
    else:
        try:
            basis = float(basis_value)
        except (TypeError, ValueError):
            problems.append(f"{page_id}/{claim_id}: basis_value sayı değil: {basis_value!r}")
        else:
            size = claim.get("size")
            if size is not None and abs(basis - float(size)) <= 1e-9:
                problems.append(f"{page_id}/{claim_id}: döngüsel kanıt — ölçek, claim'in kendi "
                                f"yazılı değerine dayanıyor ({basis}) (§11)")
            else:
                for other_id, other_size in evaluated:
                    if other_id == claim_id:
                        continue
                    if abs(basis - other_size) <= 1e-9:
                        problems.append(
                            f"{page_id}/{claim_id}: döngüsel kanıt (grafik) — ölçek dayanağı "
                            f"başka bir değerlendirilen Ø/R claim'inin yazılı değerine çözülüyor: "
                            f"{other_id} = {other_size:g} (§6); kök, claim setinin dışındaki "
                            f"bağımsız bir datum olmalı")
                        break
    scale = corroboration.get("scale_px_per_mm")
    if scale is not None:
        try:
            if float(scale) <= 0:
                problems.append(f"{page_id}/{claim_id}: scale_px_per_mm pozitif olmalı")
        except (TypeError, ValueError):
            problems.append(f"{page_id}/{claim_id}: scale_px_per_mm sayı değil")
    return problems


# ------------------------------------------------------------------- kararlı gold kimliği (§15)


def gold_content_identity(entries: list[dict]) -> str:
    """PLAN-9 §15: dondurmanın bağlanacağı **kararlı** gold kimliği.

    Yalnız gerçeği etkileyen alanlar girer (`IDENTITY_FIELDS`): sayfa kimliği, kaynak/spec/
    referans hash'leri, claim sayısı, `vision_checked`, `exhaustiveness`. Zaman damgası, mutlak
    yol ve makineye özgü üstveri **dışarıda** kalır; sayfa sırası kanoniktir (page_id'ye göre).
    """
    canonical = [
        {field: entry.get(field) for field in IDENTITY_FIELDS}
        for entry in sorted(entries, key=lambda entry: str(entry.get("page_id")))
    ]
    text = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256_text(text)


# ------------------------------------------------------------------------------- manifest


def build_manifest() -> dict:
    """İzlenen spec'lerden manifest üretir (hash'ler diskten okunur). Bkz. PLAN-8 §4, PLAN-9 §14."""
    directory = gold_dir()
    entries: list[dict] = []
    for page in pages():
        page_id = page["page_id"]
        spec_file = spec_path(page_id)
        if not spec_file.exists():
            continue
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        reference = directory / f"{page_id}.json"
        generated = json.loads(reference.read_text(encoding="utf-8")) if reference.exists() else {}
        source = ROOT / page["path"]
        scope = spec.get("exhaustiveness") or {}
        entries.append({
            "page_id": page_id,
            "split": page.get("split"),
            "page_type": page.get("type"),
            "source": page["path"],
            "source_sha256": _sha256(source),
            "spec": str(spec_file.relative_to(ROOT)),
            "spec_sha256": _sha256(spec_file),
            "reference": str(reference.relative_to(ROOT)) if reference.exists() else None,
            "reference_sha256": _sha256(reference),
            "claim_count": len(generated.get("claims") or []),
            "annotator": generated.get("annotator"),
            "review_status": generated.get("review_status"),
            "vision_checked": bool(generated.get("vision_checked")),
            "exhaustiveness": scope.get("scope"),
        })
    return {
        "schema": MANIFEST_SCHEMA,
        "gold_content_identity": gold_content_identity(entries),
        "note": ("izlenen kanonik gold spec'leri ve üretilmiş referans hash'leri; P5 dondurma "
                 "`gold_content_identity`ye bağlanır — dosya hash'ine değil (PLAN-9 §14–§15). "
                 "Manifest zaman damgası taşımaz: aynı içerik yeniden yazılınca bayt bayt "
                 "aynıdır; `--check` / `--freeze` ile doğrulanır."),
        "pages": entries,
    }


def check_manifest(*, require_all: bool = False, manifest_path: Path | None = None,
                   gold_directory: Path | None = None) -> dict:
    """Manifesti ve zinciri denetler. `require_all` = P5 dondurma kapısı (10/10 sayfa).

    `manifest_path` / `gold_directory` yalnız testler için: gerçek lab köküne dokunmadan
    eksik spec, izlenmeyen gold ve hash uyuşmazlığı senaryoları kurulabilsin (PLAN-8 §25).
    """
    problems: list[str] = []
    warnings: list[str] = []
    manifest_file = manifest_path or MANIFEST
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {
        "pages": []}
    if not manifest_file.exists():
        problems.append(f"manifest yok: {manifest_file} (`--write` ile üret)")
    page_table = {page["page_id"]: page for page in pages()}
    directory = gold_directory or gold_dir()
    entries = manifest.get("pages") or []
    listed = {entry.get("page_id") for entry in entries}
    for entry in entries:
        page_id = entry.get("page_id")
        page = page_table.get(page_id)
        if page is None:
            problems.append(f"{page_id}: pilot PAGES içinde yok")
            continue
        spec_file = ROOT / str(entry.get("spec") or "")
        if not spec_file.exists():
            problems.append(f"{page_id}: izlenen spec yok ({spec_file})")
            continue
        spec_digest = _sha256(spec_file)
        if spec_digest != entry.get("spec_sha256"):
            problems.append(f"{page_id}: spec hash'i manifestle uyuşmuyor "
                            f"({spec_digest} != {entry.get('spec_sha256')})")
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        frame = _frame_px(page_id)
        problems.extend(validate_spec(page, spec, frame))
        source = ROOT / page["path"]
        source_digest = _sha256(source)
        if source_digest != entry.get("source_sha256"):
            problems.append(f"{page_id}: kaynak çizim hash'i uyuşmuyor "
                            f"({source_digest} != {entry.get('source_sha256')})")
        reference = directory / f"{page_id}.json"
        if not reference.exists():
            problems.append(f"{page_id}: üretilmiş referans yok ({reference})")
            continue
        reference_digest = _sha256(reference)
        if reference_digest != entry.get("reference_sha256"):
            problems.append(f"{page_id}: referans hash'i manifestle uyuşmuyor "
                            f"({reference_digest} != {entry.get('reference_sha256')})")
        generated = json.loads(reference.read_text(encoding="utf-8"))
        if len(generated.get("claims") or []) != entry.get("claim_count"):
            problems.append(f"{page_id}: claim sayısı manifestle uyuşmuyor "
                            f"({len(generated.get('claims') or [])} != {entry.get('claim_count')})")
        if generated.get("vision_checked") != entry.get("vision_checked"):
            problems.append(f"{page_id}: vision_checked manifestle uyuşmuyor")
        if generated.get("annotator") != entry.get("annotator") or \
                generated.get("review_status") != entry.get("review_status"):
            problems.append(f"{page_id}: annotator/review_status manifestle uyuşmuyor")
    # §15: dondurmanın bağlanacağı kararlı kimlik — üstveri değişse de sabit kalır; değer
    # satırlarla uyuşmuyorsa manifest elden geçmiş/bozulmuş demektir (dondurma bunu şart koşar).
    stored_identity = manifest.get("gold_content_identity")
    computed_identity = gold_content_identity(entries)
    if stored_identity is None:
        warnings.append("manifestte gold_content_identity yok — `--write` ile üret (§15); "
                        "atomik `--freeze` bunu şart koşar")
    elif stored_identity != computed_identity:
        problems.append(f"gold_content_identity manifestteki sayfa satırlarıyla uyuşmuyor "
                        f"({str(stored_identity)[:12]}… != {computed_identity[:12]}…) (§15)")
    # izlenmeyen ama üretilmiş gold = dondurma açısından hata (§3: izlenen spec zorunlu)
    untracked_gold = sorted(page_id for page_id in page_table
                            if page_id not in listed and (directory / f"{page_id}.json").exists())
    untracked_specs = sorted(page_id for page_id in page_table if page_id not in listed)
    if untracked_gold:
        message = (f"izlenen spec'i olmayan üretilmiş gold: {untracked_gold} — gerçek "
                   f"yalnız izlenen spec'ten üretilebilir olmalı (PLAN-8 §3)")
        (problems if require_all else warnings).append(message)
    if require_all and untracked_specs:
        problems.append(f"izlenen spec yok: {untracked_specs} — P5 dondurulamaz (PLAN-8 §13)")
    coverage = f"{len(entries)}/{len(page_table)}"
    return {"ok": not problems, "problems": problems, "warnings": warnings,
            "coverage": coverage, "pages": len(entries), "total": len(page_table),
            "identity": computed_identity}


def _frame_px(page_id: str) -> tuple[int, int] | None:
    png = ROOT / "out/lab/semread-001b/corpus/pages" / f"{page_id}.png"
    if not png.exists():
        return None
    payload = png.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")


# ------------------------------------------------------------------------------- --verify


def regenerate(page_id: str) -> dict:
    """İzlenen spec'ten referansı yeniden üretir (gözlem çıkarımı dahil) — diske yazmaz."""
    spec_file = spec_path(page_id)
    if not spec_file.exists():
        raise SystemExit(f"izlenen spec yok: {spec_file}")
    spec = json.loads(spec_file.read_text(encoding="utf-8"))
    regions = _load("semread_001b_gold_regions_verify", ROOT / "eval/semread_001b_gold_regions.py")
    reference_module = _load("semread_001b_reference_verify", ROOT / "eval/semread_001b_reference.py")
    short, warnings = regions.build(page_id, spec)
    reference = reference_module.expand(page_id, short)
    return {"short": short, "reference": reference, "warnings": warnings}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"yüklenemedi: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pages(page_ids: list[str]) -> int:
    """`--verify`: yeniden üretilen referansı manifestteki hash ile karşılaştırır."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"pages": []}
    by_id = {entry.get("page_id"): entry for entry in manifest.get("pages") or []}
    listing = page_ids or sorted(by_id)
    if not listing:
        raise SystemExit("doğrulanacak sayfa yok (--page ver ya da önce --write)")
    failures = 0
    for page_id in listing:
        entry = by_id.get(page_id)
        if entry is None:
            print(f"{page_id}: manifestte yok — atlandı")
            failures += 1
            continue
        result = regenerate(page_id)
        text = json.dumps(result["reference"], ensure_ascii=False, indent=2)
        digest = _sha256_text(text)
        expected = entry.get("reference_sha256")
        stored_src = gold_src_dir() / f"{page_id}.json"
        src_same = (stored_src.exists()
                    and _sha256_text(json.dumps(result["short"], ensure_ascii=False, indent=2))
                    == _sha256(stored_src))
        state = "TAMAM" if digest == expected else "FARKLI"
        if digest != expected:
            failures += 1
        print(f"{page_id}: referans {state} (yeniden üretilen {digest[:12]}… / manifest "
              f"{str(expected)[:12]}…); gold-src {'aynı' if src_same else 'FARKLI'}; "
              f"{len(result['reference'].get('claims') or [])} claim")
        for warning in result["warnings"]:
            print("   UYARI:", warning)
    return 1 if failures else 0


# --------------------------------------------------------------------- --freeze (§16–§17 atomik)


def _regeneration_problems(entries: list[dict], regenerate_fn) -> list[str]:
    """§16–§17 çekirdeği: her sayfa izlenen spec'ten yeniden üretilip manifest hash'iyle
    karşılaştırılır — saklanan dosya geçerli olsa bile **mevcut kod** yeniden üretemiyorsa
    dondurma kapısı kapanır."""
    problems: list[str] = []
    for entry in entries:
        page_id = entry.get("page_id")
        try:
            outcome = regenerate_fn(page_id)
        except SystemExit as error:
            problems.append(f"{page_id}: yeniden üretilemedi — {error}")
            continue
        except Exception as error:  # noqa: BLE001 — dondurma kapısı her hatada kapanmalı
            problems.append(f"{page_id}: yeniden üretilemedi — {error!r}")
            continue
        text = json.dumps(outcome["reference"], ensure_ascii=False, indent=2)
        digest = _sha256_text(text)
        expected = entry.get("reference_sha256")
        if digest != expected:
            problems.append(f"{page_id}: yeniden üretim manifestten sapıyor "
                            f"(üretilen {digest[:12]}… != kayıtlı {str(expected)[:12]}…) (§17)")
    return problems


def freeze(*, manifest_path: Path | None = None, gold_directory: Path | None = None,
           regenerate_fn=None) -> dict:
    """PLAN-9 §17: atomik P5 kapısı — tek komut yeter.

    Sıra: (1) kapsam 10/10 + `check_manifest(require_all=True)` — kaynak/spec/referans
    hash'leri, spec kuralları, §6 döngüsellik; (2) **TÜM** sayfaların izlenen spec'ten yeniden
    üretim kanıtı (§16: saklanan dosyanın geçerli olması yetmez); (3) kararlı
    `gold_content_identity` (§15). Başarıda dondurma kaydı (FREEZE.json) yazılır.
    """
    manifest_file = manifest_path or MANIFEST
    result = check_manifest(require_all=True, manifest_path=manifest_file,
                            gold_directory=gold_directory)
    problems = list(result["problems"])
    manifest = (json.loads(manifest_file.read_text(encoding="utf-8"))
                if manifest_file.exists() else {"pages": []})
    entries = manifest.get("pages") or []
    problems.extend(_regeneration_problems(entries, regenerate_fn or regenerate))
    identity = gold_content_identity(entries)
    stored = manifest.get("gold_content_identity")
    if stored is None:
        problems.append("gold_content_identity yok — önce `--write` (§15); kimliksiz dondurma yok")
    elif stored != identity:
        problems.append(f"gold_content_identity uyuşmuyor ({str(stored)[:12]}… != "
                        f"{identity[:12]}…) (§15)")
    artifact = None
    if not problems:
        artifact = _write_freeze_artifact(manifest_file, entries, identity, result["coverage"])
    return {"ok": not problems, "problems": problems, "coverage": result["coverage"],
            "identity": identity, "regenerated": len(entries),
            "artifact": str(artifact) if artifact else None}


def _write_freeze_artifact(manifest_file: Path, entries: list[dict], identity: str,
                           coverage: str) -> Path:
    """Dondurma kaydı (§17 adım 8) — manifest dosyasının yanına yazılır.

    Alanlar şimdilik gold tarafıyla sınırlı; §22'nin tam bağlama listesi (HEAD, model tag/digest,
    MATCH_POLICY, değerlendirme uygulaması, prompt, koşu sözleşmesi …) P5 dondurma tamamlanırken
    eklenir (PLAN-9 §31 madde 14).
    """
    artifact = {
        "schema": FREEZE_SCHEMA,
        "gold_content_identity": identity,
        "coverage": coverage,
        "pages": [
            {field: entry.get(field)
             for field in ("page_id", "split", "claim_count",
                           "source_sha256", "spec_sha256", "reference_sha256")}
            for entry in entries
        ],
        "declarations": {
            "gold_annotator": "agent",
            "review_status": "provisional",
            "corpus": "küçük / bağımsız holdout değil",
            "inference": "0/30 — V/VE bu dondurmadan sonra ölçülür (PLAN-9 §24–§26)",
        },
        "note": ("PLAN-9 §17: atomik `--freeze` doğrulamasının kaydı. gold_content_identity "
                 "deterministiktir; §22'nin tam bağlama listesi P5 tamamlanırken genişletilir."),
    }
    path = manifest_file.parent / "FREEZE.json"
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="izlenen gold spec'ler + manifest (PLAN-8 §3–§4; PLAN-9 §14–§17)")
    parser.add_argument("--write", action="store_true", help="manifesti izlenen spec'lerden üret")
    parser.add_argument("--check", action="store_true", help="manifesti + zinciri doğrula")
    parser.add_argument("--freeze", action="store_true",
                        help="P5 kapısı (atomik): 10/10 + tüm hash'ler + tam yeniden üretim kanıtı")
    parser.add_argument("--verify", action="store_true",
                        help="izlenen spec'ten referansı yeniden üret ve hash karşılaştır")
    parser.add_argument("--page", action="append", help="--verify için sayfa kimliği (tekrarlanabilir)")
    args = parser.parse_args()
    if args.write:
        document = build_manifest()
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"yazıldı: {MANIFEST} ({len(document['pages'])} sayfa; gold_content_identity "
              f"{document['gold_content_identity'][:16]}…)")
        if not (args.check or args.freeze or args.verify):
            return 0
    if args.verify:
        return verify_pages(args.page or [])
    if args.freeze:
        outcome = freeze()
        print(f"P5 kapısı: kapsam {outcome['coverage']} — {'TAMAM' if outcome['ok'] else 'AÇIK'}")
        print(f"  gold_content_identity: {outcome['identity'][:16]}…")
        print(f"  yeniden üretim kanıtı: {outcome['regenerated']} sayfa koşuldu (§17)")
        if outcome["artifact"]:
            print("  dondurma kaydı yazıldı:", outcome["artifact"])
        for problem in outcome["problems"]:
            print("  SORUN:", problem)
        return 0 if outcome["ok"] else 1
    if args.check:
        result = check_manifest(require_all=False)
        print(f"manifest: {result['coverage']} sayfa izleniyor — "
              f"{'TAMAM' if result['ok'] else 'SORUNLU'}")
        print(f"  gold_content_identity: {result['identity'][:16]}…")
        for problem in result["problems"]:
            print("  SORUN:", problem)
        for warning in result["warnings"]:
            print("  UYARI:", warning)
        return 0 if result["ok"] else 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
