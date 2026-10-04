"""SEMREAD-001B — izlenen (git'te) kanonik gold spec'ler ve manifest (PLAN-8 §3–§4, §13).

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

    --write    izlenen spec'lerden manifesti üret/güncelle (hash'leri hesaplar)
    --check    manifesti doğrula: spec/kaynak/referans hash'leri, claim sayısı, nitelikler
    --freeze   P5 kapısı: TÜM korpus sayfaları izlenen spec'e sahip olmalı ve her şey tutmalı
               (kaynak hash'i, spec hash'i, referans hash'i) — dondurma buna bakacak
    --verify   izlenen spec'ten referansı yeniden üret (gözlem çıkarımı dahil) ve manifestteki
               referans hash'iyle karşılaştır; `--page` ile sayfa seçilebilir

Doğrulama kuralları (PLAN-8 §10, §11, §25):

* ölçülen hedef kutusu: dört sonlu değer, `0<=x0<x1<=1`, `0<=y0<y1<=1`, pafta sınırları içinde ve
  gerekçesi yazılı (`target_reason` / `measurement_reason` ya da kanıt metninde ölçüm ifadesi);
* raster sayfa: `vision_checked=true` **ve** her claim'in `source_evidence`ı `vision` içermeli;
* döngüsel ölçek kanıtı yasak (§11): bir claim `corroboration.independent_scale` beyan ediyorsa
  dayandığı ölçü değeri claim'in **kendi** yazılı değeri olamaz.

Bu araç hiç model çağırmaz; `--verify` dışında OCR/render de çalıştırmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TRACKED = ROOT / "eval" / "semread_001b_gold"
SPECS = TRACKED / "specs"
MANIFEST = TRACKED / "manifest.json"
MANIFEST_SCHEMA = "semread-001b-gold-manifest/1"

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
            problems.extend(_corroboration_problem(page_id, claim_id, claim, corroboration))
    return problems


def _corroboration_problem(page_id: str, claim_id: str, claim: dict, corroboration) -> list[str]:
    """§11: döngüsel ölçek kanıtını reddet — kanıt, claim'in kendi yazılı değerine dayanamaz."""
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
    scale = corroboration.get("scale_px_per_mm")
    if scale is not None:
        try:
            if float(scale) <= 0:
                problems.append(f"{page_id}/{claim_id}: scale_px_per_mm pozitif olmalı")
        except (TypeError, ValueError):
            problems.append(f"{page_id}/{claim_id}: scale_px_per_mm sayı değil")
    return problems


# ------------------------------------------------------------------------------- manifest


def build_manifest() -> dict:
    """İzlenen spec'lerden manifest üretir (hash'ler diskten okunur). Bkz. PLAN-8 §4."""
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
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("izlenen kanonik gold spec'leri ve üretilmiş referans hash'leri; P5 dondurma bu "
                 "manifestin hash'ine bağlanır (PLAN-8 §4, §16). `--check`/`--freeze` ile doğrulanır."),
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
            "coverage": coverage, "pages": len(entries), "total": len(page_table)}


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


def main() -> int:
    parser = argparse.ArgumentParser(description="izlenen gold spec'ler + manifest (PLAN-8 §3–§4)")
    parser.add_argument("--write", action="store_true", help="manifesti izlenen spec'lerden üret")
    parser.add_argument("--check", action="store_true", help="manifesti + zinciri doğrula")
    parser.add_argument("--freeze", action="store_true",
                        help="P5 kapısı: tüm sayfalar izlenmeli ve hash'ler tutmalı")
    parser.add_argument("--verify", action="store_true",
                        help="izlenen spec'ten referansı yeniden üret ve hash karşılaştır")
    parser.add_argument("--page", action="append", help="--verify için sayfa kimliği (tekrarlanabilir)")
    args = parser.parse_args()
    if args.write:
        document = build_manifest()
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"yazıldı: {MANIFEST} ({len(document['pages'])} sayfa)")
        if not (args.check or args.freeze or args.verify):
            return 0
    if args.verify:
        return verify_pages(args.page or [])
    if args.freeze:
        result = check_manifest(require_all=True)
        print(f"P5 kapısı: kapsam {result['coverage']} — {'TAMAM' if result['ok'] else 'AÇIK'}")
        for problem in result["problems"]:
            print("  SORUN:", problem)
        return 0 if result["ok"] else 1
    if args.check:
        result = check_manifest(require_all=False)
        print(f"manifest: {result['coverage']} sayfa izleniyor — "
              f"{'TAMAM' if result['ok'] else 'SORUNLU'}")
        for problem in result["problems"]:
            print("  SORUN:", problem)
        for warning in result["warnings"]:
            print("  UYARI:", warning)
        return 0 if result["ok"] else 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
