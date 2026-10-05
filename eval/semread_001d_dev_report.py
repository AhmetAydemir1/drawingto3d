"""SEMREAD-001D — dev rapor katmanı (PLAN-16 §13–§26): formal + semantik + gold + ölçüm kapısı.

Salt-okur araç; **hiçbir model çağrısı yapmaz** (0 inference). Defterden
(`out/lab/semread-001d`) yalnız **güncel 001D kimliğini** taşıyan attempt'leri seçer
(§14: experiment = `semread-001d`, schema/reader `/3`, contract `001d/1`, producer identity
current); 001B/001C attempt'lerine fallback **yoktur** — uygun attempt yoksa hücre `missing`'dir
(§15). Eski kimlikli attempt'ler yok sayılır ve `ignored_attempts` altında gerekçesiyle görünür.

Hücre başına hesaplananlar:

* **formal** (§16): attempt kimliği, durum, gönderim, done_reason, aday sayısı, parse/koordinat/
  referans/sızıntı kapıları, paylaşımlı ayarlar, producer identity eşleşmesi, maxItems sinyali;
* **semantic** (§17): tek kaynak `semantic_claim_flags` / `candidate_has_semantic_claim` /
  `evidence_flags` (kopya tanım yok) — claim/candidate sayıları, oran, alan doldurma,
  evidence-only sayısı;
* **gold** (§18): dondurulmuş dev gold'una karşı `semantic_evaluation.evaluate_page` +
  `aggregate` (D/V/VE aynı değerlendirici; 001D'de D kolu koşmaz) — eşleşme, yerelleştirme,
  alan doğrulukları, bağlama, abstention, overclaim, FP/unscorable;
* **measurement** (§19): gerçek ölçüm **objektif puanlanmış satır** ile tanımlanır; sıfır-satırlı
  bir karşılaştırma nesnesi ölçüm değildir (001B `arms_with_measurement` ile aynı prensip —
  kapının tek kaynağı `cell_measurement`);
* `semantic_valid_output` (§21) = formal valid AND en az bir semantik claim taşıyan aday;
  boş `items` parser açısından abstention'dır ama dev sayfalar için semantik-valid **değildir** (§22);
* **echo v2** (§23, yalnız VE): `empty_echo` (gözlem bölgesi kopyalanmış, claim yok) vs
  `contentful_observation_supported` (kanıt kullanılmış + claim var — otomatik failure değil);
* **kopya** (§24): birebir / yakın-bölge / aynı semantik imza+hedef / aynı callout metni; parser
  sessiz dedupe yapmaz, sayan değerlendiricidir;
* **overclaim** (§26): uydurulmuş ölçü/adet/form/THRU/derinlik ve desteksiz fiziksel yorum sayılır
  (semantik doluluk tek başına başarı değil).

Round 1 / Round 2 kapıları (§57/§72) dört hücrenin tamamı için formal + anlamsal geçerlilik ve kol
başına en az bir gold-eşleşmeli semantik claim + alan doğruluğu > 0 ister. Rapor `complete` diyemez
eğer eligible attempt, scorable ölçüm ya da semantik-valid çıktı yoksa (§20) — "metin işareti var" 
tamamlaması değildir.

Girdiler attempt klasörlerinden okunur: `manifest.json`, `result.json`, `gate-results.json`,
`resources.json`, `request-manifest.json`, `response-parsed.json`, `prompt.txt`. Rapor aracı
**defteri kurmaz/değiştirmez** (§27): `--write` yalnız `dev-report.json` + `dev-report.md` yazar;
kök yoksa tüm hücreler `missing` olarak dürüstçe raporlanır ve hiçbir ledger dosyası oluşmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION,  # noqa: E402
                                             CANDIDATE_SCHEMA_VERSION, EVIDENCE_SOURCES,
                                             MAX_ITEMS, SEMANTIC_CLAIM_SOURCES, Region,
                                             candidate_has_semantic_claim, evidence_flags,
                                             regions_match, semantic_claim_flags)
from drawingto3d.semantic_evaluation import (FIELDS, MATCH_POLICY, MATCH_POLICY_VERSION,  # noqa: E402
                                             aggregate, candidate_anchor, compare_arms,
                                             evaluate_page)
from drawingto3d.semantic_run_contract import CONTRACT_VERSION  # noqa: E402


def _load_pilot():
    """Pilot'u test'lerin yaptığı gibi importlib ile yükle (kimlik fonksiyonlarının tek kaynağı)."""
    spec = importlib.util.spec_from_file_location("semread_001d_dev_report_pilot",
                                                  ROOT / "eval" / "semread_001b_pilot.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()
pilot.use_experiment("semread-001d")

EXPERIMENT = "semread-001d"
LAB = pilot.REPORT_ROOT
ATTEMPTS = pilot.ATTEMPT_ROOT
REPORT_SCHEMA = "semread-001d-dev-report/1"
DEV_PAGES = tuple(row["page_id"] for row in pilot.PAGES if row["split"] == "dev")
ARMS = ("V", "VE")
# §57 Round 1: iki sayfa × V/VE. §72 Round 2: kalan iki sayfa × V/VE.
ROUND_1_PAGES = ("dev-plate-pocket", "dev-flange-book")
ROUND_2_PAGES = ("dev-flange-elbow", "dev-drawing-2")
ROUND_1_CELLS = tuple(f"{page}-{arm}" for page in ROUND_1_PAGES for arm in ARMS)
ROUND_2_CELLS = tuple(f"{page}-{arm}" for page in ROUND_2_PAGES for arm in ARMS)

# Dev gold: 001B dondurulmuş corpus gold'u (001C dev değerlendirmesiyle aynı kaynak ve aynı
# fail-closed hash denetimi). Gold, 001D deney kökünde yaşamaz ve bu araç onu değiştirmez.
GOLD_001B = ROOT / "out" / "lab" / "semread-001b" / "corpus" / "gold"
FREEZE = ROOT / "eval" / "semread_001b_gold" / "FREEZE.json"

# Observation-satırı yankısı eşiği: model koordinatı 4 ondalığa yuvarlar; tablo değerleri daha
# uzun olabilir. Dört koordinatta |Δ| ≤ bu değer ise aday, tablo satırının yankısı sayılır.
ECHO_TOLERANCE = 0.0006

# Değerlendiricinin "karar taşıyan" verdict kümesi (ölçüm sayımı): `aggregate()`in `scorable`
# tanımı + `_field_ok`nun False döndüğü karar türleri. `not_scored` (belirsiz) ve `not_applicable`
# (iki tarafta da yok — karar yok) sayılmaz.
SCORABLE_VERDICTS = frozenset({"correct", "mismatch", "value_error", "unit_error", "overclaim",
                               "false_claim", "abstained", "omission", "not_produced",
                               "binding_error", "unreadable"})

EVALUATOR_FILES = ("src/drawingto3d/semantic_candidates.py",
                   "src/drawingto3d/semantic_evaluation.py",
                   "eval/semread_001b_pilot.py",
                   "eval/semread_001d_dev_report.py")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sha256_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ kimlikler ve seçim (§14/§15)


def current_identities() -> dict:
    """Güncel 001D kimlikleri — tek kaynak pilot fonksiyonları (kopya hesap yok)."""
    return {"experiment": EXPERIMENT,
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "reader_version": CANDIDATE_READER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "producer_identity": pilot.producer_identity(),
            "preprocessing_identity": pilot.preprocessing_identity(),
            "evaluation_identity": pilot.evaluation_identity()}


def eligibility_reasons(manifest: dict | None, expected: dict | None = None) -> list[str]:
    """§14 seçim sözleşmesi: yalnız güncel kimliği taşıyan attempt'ler eligible.

    Eksik/eski alanlar (001B/001C attempt'leri dahil) gerekçesiyle listelenir — fallback yok.
    """
    expected = expected or current_identities()
    manifest = manifest or {}
    reasons: list[str] = []
    for field in ("experiment", "schema_version", "reader_version", "contract_version",
                  "producer_identity"):
        got = manifest.get(field)
        want = expected[field]
        if got != want:
            reasons.append(f"{field}: {got!r} != {want!r}")
    return reasons


def attempt_dirs(cell: str) -> list[Path]:
    root = ATTEMPTS / cell
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def attempt_row(directory: Path) -> dict | None:
    """Attempt klasörünü kayıtlı kanıt dosyalarıyla birlikte oku (salt-okur; yazmaz).

    `result.json` yoksa klasör sonuçlandırılmamış (orphan) demektir ve attempt kaydı sayılmaz.
    """
    result = read_json(directory / "result.json")
    if result is None:
        return None
    return {
        "directory": directory,
        "result": result,
        "manifest": read_json(directory / "manifest.json") or {},
        "request": read_json(directory / "request-manifest.json") or {},
        "resources": read_json(directory / "resources.json") or {},
        "gates": read_json(directory / "gate-results.json") or {},
        "parsed": read_json(directory / "response-parsed.json"),
        "attempt_id": result.get("attempt_id") or f"{directory.parent.name}/{directory.name}",
        "state": result.get("state"),
        "manifest_sha256": sha256_of(directory / "manifest.json"),
        "result_sha256": sha256_of(directory / "result.json"),
        "parsed_sha256": sha256_of(directory / "response-parsed.json"),
    }


def select_attempt(cell: str, expected: dict | None = None) -> tuple[dict | None, list[dict], int]:
    """Hücre için seçili attempt: **en yeni pass** (parsed çıktılı) yoksa en yeni eligible.

    Dönen: (chosen | None, ignored kayıtları, orphan sayısı). Seçim yalnız §14 kimliğiyle yapılır;
    001B/001C attempt'lerine fallback yoktur (§15).
    """
    expected = expected or current_identities()
    rows: list[dict] = []
    ignored: list[dict] = []
    orphans = 0
    for directory in attempt_dirs(cell):
        row = attempt_row(directory)
        if row is None:
            orphans += 1
            ignored.append({"cell": cell, "attempt": directory.name, "state": "orphan_no_result",
                            "reasons": ["result.json yok (sonuçlandırılmamış klasör)"]})
            continue
        reasons = eligibility_reasons(row["manifest"], expected)
        if reasons:
            ignored.append({"cell": cell, "attempt": directory.name, "state": row["state"],
                            "reasons": reasons})
            continue
        rows.append(row)
    passes = [row for row in rows if row["state"] == "pass" and row["parsed"] is not None]
    chosen = passes[-1] if passes else (rows[-1] if rows else None)
    return chosen, ignored, orphans


# ------------------------------------------------------------------ formal metrikler (§16)


def coordinate_valid(parsed: dict | None) -> bool | None:
    """Ayrıştırılmış adayların tüm bölgeleri 0..1 içinde mi (piksel sızıntısı yok)?"""
    items = (parsed or {}).get("items")
    if not isinstance(items, list):
        return None

    def box_ok(box) -> bool:
        if box is None:
            return True
        if not isinstance(box, dict):
            return False
        values = [box.get(key) for key in ("x0", "y0", "x1", "y1")]
        return all(isinstance(value, (int, float)) and 0 <= value <= 1 for value in values)

    for item in items:
        item = item or {}
        if not box_ok((item.get("source") or {}).get("region")):
            return False
        if not box_ok((item.get("source") or {}).get("callout_region")):
            return False
        if not box_ok((item.get("target") or {}).get("region")):
            return False
    return True


def shared_settings_check(manifest: dict | None, request: dict | None, arm: str) -> dict:
    """Attempt'in kaydettiği gerçek ayarlar güncel sözleşmeyle aynı mı (V==VE invariantı dahil).

    Gerçek istek ayarları `request-manifest.json` `options` alanından okunur (001C dev değerlendirme
    kuralı); donmuş sözleşme anlık görüntüsü `manifest.settings`ten denetlenir. Hiçbir kayıt yoksa
    `ok=None` (doğrulanamaz — fail-closed, kapıyı kapatır).
    """
    expected = pilot.generation_settings(arm)
    checks: dict[str, bool] = {}
    options = (request or {}).get("options") or {}
    for key in ("temperature", "num_predict", "num_ctx", "repeat_penalty", "repeat_last_n"):
        if key in options:
            checks[f"options.{key}"] = options[key] == expected[key]
    recorded = (manifest or {}).get("settings") or {}
    for key, value in pilot.SETTINGS.items():
        if key in recorded:
            checks[f"settings.{key}"] = recorded[key] == value
    return {"ok": all(checks.values()) if checks else None, "checks": checks}


def formal_metrics(row: dict, arm: str, expected: dict | None = None) -> dict:
    """§16 formal metrikler — kayıtlı kanıttan; eksik sinyal `None` (kapılar fail-closed okur)."""
    expected = expected or current_identities()
    manifest, result = row["manifest"], row["result"]
    gates = row["gates"]
    parsed = row["parsed"]
    stats = (row["resources"].get("stats") or {})
    options = (row["request"].get("options") or {})
    parse_gate = gates.get("parse") or {}
    references = gates.get("references")
    leakage = gates.get("leakage")
    shared = shared_settings_check(manifest, row["request"], arm)
    items = (parsed or {}).get("items")
    candidate_count = len(items) if isinstance(items, list) else None
    return {
        "attempt_id": row["attempt_id"],
        "attempt_state": row["state"],
        "send_attempted": result.get("send_attempted"),
        "done_reason": stats.get("done_reason"),
        "candidate_count": candidate_count,
        "parse_valid": parse_gate.get("ok") if isinstance(parse_gate, dict) else None,
        "coordinate_valid": coordinate_valid(parsed),
        "reference_valid": (references or {}).get("ok") if isinstance(references, dict) else None,
        "leak_clean": None if leakage is None else leakage == [],
        "shared_settings": shared["ok"],
        "shared_settings_detail": shared["checks"],
        "producer_identity_match": manifest.get("producer_identity") == expected["producer_identity"],
        "preprocessing_identity_match": manifest.get("preprocessing_identity")
        == expected["preprocessing_identity"],
        "max_items_hit": (candidate_count == MAX_ITEMS) if candidate_count is not None else None,
        "eval_count": stats.get("eval_count"),
        "prompt_eval_count": stats.get("prompt_eval_count"),
        "seconds": result.get("seconds"),
        "request_options": options,
        "attempt_hashes": {"manifest_sha256": row["manifest_sha256"],
                           "result_sha256": row["result_sha256"],
                           "parsed_sha256": row["parsed_sha256"]},
    }


def formal_valid(formal: dict | None) -> bool:
    """Formal kapı (§61): gönderilmiş + parse + koordinat + referans + sızıntısız + stop +
    paylaşımlı ayar + producer eşleşmesi. `None` sinyal kapıyı kapatır (fail-closed)."""
    if not formal:
        return False
    return bool(formal.get("send_attempted") is True
                and formal.get("parse_valid") is True
                and formal.get("coordinate_valid") is True
                and formal.get("reference_valid") is True
                and formal.get("leak_clean") is True
                and formal.get("shared_settings") is True
                and formal.get("producer_identity_match") is True
                and formal.get("done_reason") == "stop")


# ------------------------------------------------------------------ semantik metrikler (§17)


def semantic_metrics(items: list[dict]) -> dict:
    """§17: tek kaynak semantik-içerik tanımıyla aday/claim sayıları + kanıt sinyalleri."""
    per_source = {source: 0 for source in SEMANTIC_CLAIM_SOURCES}
    evidence_fill = {source: 0 for source in EVIDENCE_SOURCES}
    claim_total = 0
    with_claim = 0
    evidence_only = 0
    for item in items:
        flags = semantic_claim_flags(item)
        for source, value in flags.items():
            per_source[source] += int(value)
        count = sum(1 for value in flags.values() if value)
        claim_total += count
        if count:
            with_claim += 1
        else:
            evidence_only += 1
        for source, value in evidence_flags(item).items():
            evidence_fill[source] += int(value)
    total = len(items)
    return {
        "candidate_count": total,
        "semantic_claim_count": claim_total,
        "semantic_candidate_count": with_claim,
        "semantic_candidate_rate": (round(with_claim / total, 4) if total else None),
        "semantic_field_fill": per_source,
        "evidence_only_count": evidence_only,
        "evidence_signal_fill": evidence_fill,
    }


# ------------------------------------------------------------------ gold ve ölçüm (§18/§19)


def load_dev_gold() -> dict:
    """Dört dev sayfanın dondurulmuş 001B gold'u — FREEZE.json hash'iyle birebir (fail-closed)."""
    freeze = read_json(FREEZE)
    if not freeze:
        raise SystemExit(f"FREEZE.json okunamadı: {FREEZE}")
    entries = {row["page_id"]: row for row in freeze.get("pages") or []}
    golds: dict = {}
    for page_id in DEV_PAGES:
        entry = entries.get(page_id)
        if entry is None:
            raise SystemExit(f"FREEZE.json'da sayfa yok: {page_id}")
        path = GOLD_001B / f"{page_id}.json"
        actual = sha256_of(path)
        if actual != entry.get("reference_sha256"):
            raise SystemExit(f"gold hash uyuşmuyor (fail-closed): {page_id} "
                             f"{actual} != {entry.get('reference_sha256')}")
        reference = read_json(path)
        if not reference:
            raise SystemExit(f"gold okunamadı: {path}")
        golds[page_id] = {"reference": reference, "reference_sha256": actual,
                          "claim_count": len(reference.get("claims") or [])}
    return golds


def _claim_scorable(record: dict | None) -> bool:
    """Kalem puanlanabilir mi: belirsiz değil ve en az bir karar taşıyan alan verdict'i var.

    Eşleşmemiş kalem `not_produced` taşır → karar (eksik cevap) sayılır — 001B `_field_ok`
    semantiğiyle aynı: abstention puanlanabilir bir hedeftir.
    """
    if not record:
        return False
    if record.get("matching_status") == "ambiguous":
        return False
    return any(value in SCORABLE_VERDICTS for value in (record.get("fields") or {}).values())


def cell_measurement(evaluation: dict | None, *, available: bool) -> dict:
    """§19 gerçek ölçüm kapısı — **tek kaynak** tanım.

    Ölçüm, `scorable_target_count > 0` gibi objektif satır sayısıyla kanıtlanır; karşılaştırma
    nesnesinin varlığı ölçüm değildir (001B `arms_with_measurement` ile aynı prensip). Parse
    edilmiş çıktısı olmayan hücrede ölçüm yoktur (fail-closed).
    """
    if not available or evaluation is None:
        return {"measured": False, "scorable_target_count": None, "scorable_field_rows": None,
                "reason": "puanlanabilir çıktı yok (eligible attempt ya da parsed yok)"}
    targets = sum(1 for record in (evaluation.get("per_claim") or {}).values()
                  if _claim_scorable(record))
    rows = sum(1 for row in evaluation.get("field_rows") or []
               if row.get("verdict") in SCORABLE_VERDICTS)
    return {"measured": targets > 0, "scorable_target_count": targets, "scorable_field_rows": rows,
            "reason": None if targets > 0 else "hiçbir gold kalemi puanlanabilir değil"}


FIELD_METRIC_NAMES = {"representation": "representation_accuracy", "form": "form_accuracy",
                      "size": "size_accuracy", "count_printed": "count_accuracy",
                      "termination": "termination_accuracy", "depth": "depth_accuracy",
                      "physical": "physical_accuracy", "target_binding": "target_binding_accuracy"}


def cell_gold_metrics(evaluation: dict) -> dict:
    """§18 gold-puanlı metrikler — değerlendiricinin kendi toplamasıyla (`aggregate`)."""
    agg = aggregate([evaluation])
    metrics: dict = {
        "matched_claim_count": agg["matched"],
        "scorable_target_count": sum(1 for record in (evaluation.get("per_claim") or {}).values()
                                     if _claim_scorable(record)),
        "scorable_field_rows": sum(agg["fields"][field]["scorable"] for field in FIELDS),
        "localization": agg["localization_match_rate"],
        "abstention_rate": agg["candidate_abstention_rate"],
        "overclaim_rate": agg["candidate_overclaim_rate"],
        "omission_rate": agg["omission_rate"],
        "false_positive_count": agg["false_positive_candidate_count"],
        "unscorable_extra_count": agg["unscorable_extra_candidate_count"],
        "ambiguous_claim_count": agg["ambiguous_claim_count"],
    }
    for field, name in FIELD_METRIC_NAMES.items():
        metrics[name] = agg["fields"][field]["accuracy"]
    return metrics


def matched_semantic_claims(parsed: dict, evaluation: dict) -> int:
    """Gold ile eşleşen **ve semantik claim taşıyan** aday sayısı (§62 kol ölçütü)."""
    by_id = {item.get("candidate_id"): item for item in (parsed.get("items") or [])}
    count = 0
    for pair in (evaluation.get("matching") or {}).get("pairs") or []:
        item = by_id.get(pair.get("candidate_id"))
        if item is not None and candidate_has_semantic_claim(item):
            count += 1
    return count


# ------------------------------------------------------------------ echo / kopya / overclaim (§23–§26)


def prompt_table_rows(prompt_text: str) -> list[dict]:
    """VE prompt'undaki gözlem tablosunu (modele **gönderilen** satırlar) ayrıştırır."""
    rows: list[dict] = []
    started = False
    for raw_line in prompt_text.splitlines():
        line = raw_line.strip()
        if line.startswith("observation_id |"):
            started = True
            continue
        if not started:
            continue
        if line.startswith("Reply with JSON only"):
            break
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 6:
            continue
        numbers = parts[-1].split(",")
        if len(numbers) != 4:
            continue
        try:
            region = tuple(float(number) for number in numbers)
        except ValueError:
            continue
        rows.append({"observation_id": parts[0], "kind": parts[1], "region": region})
    return rows


def echo_of(anchor, rows: list[dict], tolerance: float = ECHO_TOLERANCE) -> dict | None:
    if anchor is None:
        return None
    box = anchor.as_list() if hasattr(anchor, "as_list") else tuple(anchor)
    for row in rows:
        if all(abs(a - b) <= tolerance for a, b in zip(box, row["region"])):
            return {"observation_id": row["observation_id"], "kind": row["kind"]}
    return None


def echo_v2(items: list[dict], table_rows: list[dict] | None) -> dict | None:
    """§23 echo v2 (yalnız VE): `empty_echo` vs `contentful_observation_supported`.

    Gözlem-satırı bölgesini kopyalayan ama hiç semantik claim taşımayan aday `empty_echo`'dur;
    kanıtı kullanan **ve** claim taşıyan aday `contentful_observation_supported` sayılır (otomatik
    failure değildir — gold doğruluğu ayrı ölçülür). Tablo okunamazsa (prompt.txt yok) sınıflama
    yapılamaz ve bu açıkça yazılır.
    """
    if table_rows is None:
        return {"prompt_table_rows": None, "classified": None, "empty_echo": None,
                "contentful_observation_supported": None,
                "note": "prompt.txt yok: yankı sınıflaması yapılamadı (kanıt eksik)"}
    detail: list[dict] = []
    empty = contentful = 0
    for item in items:
        hit = echo_of(candidate_anchor(item), table_rows)
        if hit is None:
            continue
        if candidate_has_semantic_claim(item):
            contentful += 1
            klass = "contentful_observation_supported"
        else:
            empty += 1
            klass = "empty_echo"
        detail.append({"candidate_id": item.get("candidate_id"),
                       "observation_id": hit["observation_id"], "class": klass})
    return {"prompt_table_rows": len(table_rows), "classified": len(detail),
            "empty_echo": empty, "contentful_observation_supported": contentful,
            "detail": detail,
            "note": ("empty_echo: gözlem bölgesi kopyalanmış, semantik claim yok (001D parser'ı "
                     "bunu wire'da reddeder); contentful: kanıt kullanılmış + claim var — kararı "
                     "gold doğruluğu verir")}


def _region_tuple(region) -> tuple | None:
    return tuple(round(float(value), 6) for value in region.as_list()) \
        if region is not None and hasattr(region, "as_list") else None


def _target_key(item: dict):
    target = item.get("target") or {}
    observation_id = target.get("observation_id")
    if observation_id:
        return ("obs", str(observation_id))
    box = target.get("region") or (item.get("source") or {}).get("region")
    if isinstance(box, dict):
        try:
            return ("region", tuple(round(float(box[key]), 6)
                                    for key in ("x0", "y0", "x1", "y1")))
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _semantic_signature(item: dict) -> str | None:
    """Adayın semantik iddia içeriğinin kanonik imzası (claim yoksa None)."""
    flags = semantic_claim_flags(item)
    if not any(flags.values()):
        return None

    def value(block: str, key: str):
        return (item.get(block) or {}).get(key)

    parts = {"callout_text": str(value("callout", "text") or "").strip().lower(),
             "form": value("form", "symbol"),
             "size": [value("size", "value"), value("size", "unit")],
             "count_printed": value("count", "printed"),
             "termination": value("termination", "kind"),
             "depth": [value("depth", "value"), value("depth", "unit")],
             "physical": value("physical", "kind")}
    return json.dumps(parts, sort_keys=True, ensure_ascii=False)


def duplicate_metrics(items: list[dict]) -> dict:
    """§24 kopya metrikleri — parser sessiz dedupe yapmaz; **sayan değerlendiricidir**.

    Dört sınıf: birebir bölge (`exact`), yakın bölge (`near` — eşleştiricinin kendi politikası),
    aynı semantik imza + aynı hedef (`signature_target`) ve aynı callout metninin tekrarı
    (`callout_text_repeat`). İlk üye kopya sayılmaz; her sınıf kendi üye/sayı çiftini taşır ve
    `duplicates_total` sınıfların **birleşimindeki** üye sayısıdır.
    """
    anchors = [candidate_anchor(item) for item in items]
    signatures = [_semantic_signature(item) for item in items]
    targets = [_target_key(item) for item in items]
    texts = [str((item.get("callout") or {}).get("text") or "").strip().lower() for item in items]
    exact_of: list[str | None] = [None] * len(items)
    near_of: list[str | None] = [None] * len(items)
    sig_of: list[str | None] = [None] * len(items)
    text_of: list[str | None] = [None] * len(items)
    exact_pairs = near_pairs = sig_pairs = 0
    for index in range(len(items)):
        for earlier in range(index):
            if anchors[index] is None or anchors[earlier] is None:
                continue
            if _region_tuple(anchors[index]) == _region_tuple(anchors[earlier]):
                exact_pairs += 1
                if exact_of[index] is None:
                    exact_of[index] = items[earlier].get("candidate_id")
            elif regions_match(anchors[index], anchors[earlier]):
                near_pairs += 1
                if near_of[index] is None:
                    near_of[index] = items[earlier].get("candidate_id")
    for index in range(len(items)):
        for earlier in range(index):
            if signatures[index] is not None and signatures[index] == signatures[earlier] \
                    and targets[index] is not None and targets[index] == targets[earlier]:
                sig_pairs += 1
                if sig_of[index] is None:
                    sig_of[index] = items[earlier].get("candidate_id")
            if texts[index] and texts[index] == texts[earlier]:
                if text_of[index] is None:
                    text_of[index] = items[earlier].get("candidate_id")
    flagged = [index for index in range(len(items))
               if exact_of[index] or near_of[index] or sig_of[index] or text_of[index]]
    return {
        "exact_duplicates": sum(1 for value in exact_of if value),
        "near_duplicates": sum(1 for value in near_of if value),
        "signature_target_duplicates": sum(1 for value in sig_of if value),
        "callout_text_repeats": sum(1 for value in text_of if value),
        "duplicates_total": len(flagged),
        "pairs": {"exact": exact_pairs, "near": near_pairs, "signature_target": sig_pairs},
        "definitions": ("exact: aynı anchor bölgesi (6 ondalık); near: regions_match ile yakın "
                        "(birebir olmayan); signature_target: aynı semantik imza + aynı hedef "
                        "(gözlem kimliği ya da bölge); callout_text_repeat: aynı callout metni; "
                        "ilk üye kopya sayılmaz"),
    }


def overclaim_metrics(evaluation: dict) -> dict:
    """§26 overclaim metrikleri — yalnız eşleşmiş çiftlerde (gold kararı verir), verdict'lerden.

    Sayılan: ölçü/adet/derinlik `false_claim` (gold'da yok, adayda var → uydurma); form ve
    termination için gold `unknown`/`underdetermined` iken adayın pozitif değer iddiası; fiziksel
    yorum için değerlendiricinin kendi `overclaim` verdict'i. Semantik doluluk artışı tek başına
    başarı değildir — bu bölüm onu dengelemek için vardır.
    """
    counts: dict[str, int] = {"invented_size": 0, "invented_count": 0, "invented_form": 0,
                              "invented_thru": 0, "invented_depth": 0,
                              "unsupported_physical_meaning": 0}
    for row in evaluation.get("field_rows") or []:
        field, verdict = row.get("field"), row.get("verdict")
        expected, given = row.get("expected"), row.get("given")
        categorical_invented = (verdict in ("overclaim", "mismatch")
                                and expected in ("unknown", "underdetermined", None)
                                and given not in (None, "unknown"))
        if field == "size" and verdict == "false_claim":
            counts["invented_size"] += 1
        elif field == "count_printed" and verdict == "false_claim":
            counts["invented_count"] += 1
        elif field == "depth" and verdict == "false_claim":
            counts["invented_depth"] += 1
        elif field == "form" and categorical_invented:
            counts["invented_form"] += 1
        elif field == "termination" and verdict == "overclaim":
            counts["invented_thru"] += 1
        elif field == "termination" and verdict == "mismatch" and expected in ("unknown",) \
                and given not in (None, "unknown"):
            counts["invented_thru"] += 1
        elif field == "physical" and verdict == "overclaim":
            counts["unsupported_physical_meaning"] += 1
    result: dict = {**counts, "total": sum(counts.values())}
    result["note"] = ("yalnız eşleşmiş çiftler; gold'un verdiği karara karşı sayılır "
                      "(uydurma = gold'da karşılığı yokken adayın pozitif iddiası)")
    return result


# ------------------------------------------------------------------ hücre ve rapor


def missing_cell(cell_id: str) -> dict:
    return {"cell": cell_id, "page_id": cell_id.rsplit("-", 1)[0], "arm": cell_id.rsplit("-", 1)[1],
            "attempt_id": None, "attempt_state": "missing", "attempt_dir": None,
            "formal": None, "semantic": None, "gold": None,
            "measurement": {"measured": False, "scorable_target_count": None,
                            "scorable_field_rows": None,
                            "reason": "eligible 001D attempt yok (§15: fallback yok)"},
            "semantic_valid_output": False, "echo": None, "duplicates": None, "overclaim": None}


def cell_record(cell_id: str, expected: dict, golds: dict | None) -> tuple[dict, dict | None, list[dict], int]:
    """Tek hücrenin tam kaydı: (rapor kaydı, değerlendirme | None, ignored, orphan sayısı)."""
    page_id, arm = cell_id.rsplit("-", 1)
    chosen, ignored, orphans = select_attempt(cell_id, expected)
    if chosen is None:
        return missing_cell(cell_id), None, ignored, orphans
    record = {
        "cell": cell_id, "page_id": page_id, "arm": arm,
        "attempt_id": chosen["attempt_id"],
        "attempt_state": chosen["state"],
        "attempt_dir": str(chosen["directory"].relative_to(ROOT)) if chosen["directory"].is_relative_to(ROOT)
        else str(chosen["directory"]),
    }
    record["formal"] = formal_metrics(chosen, arm, expected)
    parsed = chosen["parsed"]
    items = (parsed.get("items") or []) if isinstance(parsed, dict) else []
    record["semantic"] = semantic_metrics(items) if parsed is not None else None
    evaluation = None
    if parsed is not None and golds is not None and page_id in golds:
        evaluation = evaluate_page(golds[page_id]["reference"], {"response": parsed})
    if evaluation is not None:
        gold_metrics = cell_gold_metrics(evaluation)
        gold_metrics["gold_matched_semantic_claim_count"] = matched_semantic_claims(parsed or {},
                                                                                    evaluation)
        record["gold"] = gold_metrics
    else:
        record["gold"] = None
    record["measurement"] = cell_measurement(evaluation, available=parsed is not None)
    record["semantic_valid_output"] = bool(formal_valid(record["formal"])
                                           and (record["semantic"] or {}).get("semantic_claim_count", 0) >= 1)
    prompt_path = chosen["directory"] / "prompt.txt"
    table_rows = None
    if arm == "VE" and prompt_path.exists():
        table_rows = prompt_table_rows(prompt_path.read_text(encoding="utf-8"))
    record["echo"] = echo_v2(items, table_rows) if arm == "VE" else None
    record["duplicates"] = duplicate_metrics(items) if parsed is not None else None
    record["overclaim"] = overclaim_metrics(evaluation) if evaluation else None
    return record, evaluation, ignored, orphans


def round_gate(label: str, cell_ids: tuple[str, ...], cells: dict[str, dict],
               evaluations: dict[str, dict]) -> dict:
    """Round kapısı: dört hücrenin tamamı formal + semantik-valid; kol başına ≥1 gold-eşleşmeli
    semantik claim ve alan doğruluğu > 0 (§62–§64 / §72–§74)."""
    per_cell = []
    for cell_id in cell_ids:
        cell = cells.get(cell_id) or missing_cell(cell_id)
        per_cell.append({
            "cell": cell_id,
            "attempt_id": cell.get("attempt_id"),
            "formal_valid": formal_valid(cell.get("formal")),
            "semantic_valid": bool(cell.get("semantic_valid_output")),
            "gold_matched_semantic_claims":
                (cell.get("gold") or {}).get("gold_matched_semantic_claim_count"),
        })
    per_arm: dict[str, dict | None] = {}
    for arm in ARMS:
        arm_cells = [cell_id for cell_id in cell_ids
                     if cell_id.endswith(f"-{arm}") and cell_id in evaluations]
        if not arm_cells:
            per_arm[arm] = None
            continue
        agg = aggregate([evaluations[cell_id] for cell_id in arm_cells])
        per_arm[arm] = {
            "cells": arm_cells,
            "localization": agg["localization_match_rate"],
            "semantic_field_accuracy": agg["semantic_field_accuracy"],
            "matched_claims": agg["matched"],
            "matched_semantic_claims": sum(
                (cells[cell_id].get("gold") or {}).get("gold_matched_semantic_claim_count") or 0
                for cell_id in arm_cells),
        }
    v_arm = per_arm.get("V")
    ve_arm = per_arm.get("VE")
    checks = {
        "four_cells_present": all(row["attempt_id"] for row in per_cell),
        "formal_valid_all": all(row["formal_valid"] for row in per_cell),
        "semantic_valid_all": all(row["semantic_valid"] for row in per_cell),
        "v_gold_match": bool(v_arm and v_arm["matched_semantic_claims"] >= 1),
        "ve_gold_match": bool(ve_arm and ve_arm["matched_semantic_claims"] >= 1),
        "v_field_accuracy_positive": bool(v_arm and (v_arm["semantic_field_accuracy"] or 0) > 0),
        "ve_field_accuracy_positive": bool(ve_arm
                                           and (ve_arm["semantic_field_accuracy"] or 0) > 0),
    }
    return {"label": label, "cells": per_cell, "per_arm": per_arm, "checks": checks,
            "passed": all(checks.values()),
            "open": [name for name, value in checks.items() if not value]}


def evaluator_file_hashes() -> list[dict]:
    return [{"path": relative, "sha256": sha256_of(ROOT / relative)}
            for relative in EVALUATOR_FILES]


def build_report() -> dict:
    """Dev raporunu kur (§13): salt-okur; yalnız güncel 001D kimlikli attempt'ler; 0 inference."""
    expected = current_identities()
    cells: dict[str, dict] = {}
    evaluations: dict[str, dict] = {}
    ignored: list[dict] = []
    orphans = 0
    needs_gold = False
    selections: dict[str, tuple] = {}
    for page_id in DEV_PAGES:
        for arm in ARMS:
            cell_id = f"{page_id}-{arm}"
            chosen, cell_ignored, cell_orphans = select_attempt(cell_id, expected)
            selections[cell_id] = (chosen, cell_ignored, cell_orphans)
            ignored += cell_ignored
            orphans += cell_orphans
            if chosen is not None and chosen["parsed"] is not None:
                needs_gold = True
    golds = load_dev_gold() if needs_gold else None
    for cell_id, (chosen, _cell_ignored, _cell_orphans) in selections.items():
        record, evaluation, _ignored, _orphans = cell_record(cell_id, expected, golds)
        cells[cell_id] = record
        if evaluation is not None:
            evaluations[cell_id] = evaluation
    per_page_evals: dict[str, dict] = {}
    for cell_id, evaluation in evaluations.items():
        page_id, arm = cell_id.rsplit("-", 1)
        per_page_evals.setdefault(page_id, {})[arm] = evaluation
    aggregates = {}
    for arm in ARMS:
        arm_evals = [evaluations[cell_id] for cell_id in evaluations if cell_id.endswith(f"-{arm}")]
        if arm_evals:
            aggregates[arm] = aggregate(arm_evals)
    comparison: dict = (compare_arms(per_page_evals) if per_page_evals
                        else {"vs_d": {}, "ve_vs_v": {}})
    comparison["note"] = ("001D'de D kolu koşmaz: `vs_d` satırları boş/sıfırdır ve **ölçüm kanıtı "
                          "değildir** (§19); ölçüm kapısı hücre ölçümüdür. `ve_vs_v` bilgi amaçlıdır.")
    # V/VE paylaşımlı-ayar invariantı (§8): aynı sayfanın iki kolunun kaydettiği ayarlar eşit mi?
    invariants = {}
    for page_id in DEV_PAGES:
        v_cell, ve_cell = cells.get(f"{page_id}-V"), cells.get(f"{page_id}-VE")
        v_detail = (v_cell.get("formal") or {}).get("shared_settings_detail") if v_cell else None
        ve_detail = (ve_cell.get("formal") or {}).get("shared_settings_detail") if ve_cell else None
        if v_detail and ve_detail:
            match: bool | None = v_detail == ve_detail
        else:
            match = None
        invariants[page_id] = {"shared_settings_match": match}
    matched_invariants = [row["shared_settings_match"] for row in invariants.values()]
    invariants["all_match"] = (all(matched_invariants)
                               if matched_invariants and any(value is not None
                                                             for value in matched_invariants)
                               else None)
    max_items_cells = [cell_id for cell_id, cell in cells.items()
                       if (cell.get("formal") or {}).get("max_items_hit") is True]
    degeneracy = {
        "max_items_cells": max_items_cells,
        "degeneracy_warning": len(max_items_cells) >= 2,
        "note": ("tek hücrede maxItems tek başına fail değildir; **birden çok** hücrenin sürekli "
                 "maxItems vermesi degenerasyon uyarısıdır (§25)"),
    }
    measured_cells = [cell_id for cell_id, cell in cells.items()
                      if (cell.get("measurement") or {}).get("measured")]
    semantic_valid_cells = [cell_id for cell_id, cell in cells.items()
                            if cell.get("semantic_valid_output")]
    eligible_cells = [cell_id for cell_id, cell in cells.items() if cell.get("attempt_id")]
    reasons: list[str] = []
    if not eligible_cells:
        reasons.append("eligible attempt yok (§15: 001B/001C fallback yok)")
    if not measured_cells:
        reasons.append("scorable measurement yok (§19)")
    if not semantic_valid_cells:
        reasons.append("semantic-valid çıktı yok (§21)")
    completion = {"complete": not reasons, "reasons": reasons,
                  "eligible_cells": eligible_cells, "measured_cells": measured_cells,
                  "semantic_valid_cells": semantic_valid_cells,
                  "missing_cells": [cell_id for cell_id, cell in cells.items()
                                    if not cell.get("attempt_id")]}
    gold_identity = {"present": golds is not None,
                     "freeze": (str(FREEZE.relative_to(ROOT)) if FREEZE.is_relative_to(ROOT)
                                else str(FREEZE)),
                     "freeze_sha256": sha256_of(FREEZE),
                     "pages": ({page_id: {"claim_count": golds[page_id]["claim_count"],
                                          "reference_sha256": golds[page_id]["reference_sha256"]}
                                for page_id in DEV_PAGES} if golds else {})}
    identity = {
        "experiment": EXPERIMENT,
        "contract_version": CONTRACT_VERSION,
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "reader_version": CANDIDATE_READER_VERSION,
        "producer_identity": expected["producer_identity"],
        "preprocessing_identity": expected["preprocessing_identity"],
        "evaluation_identity": expected["evaluation_identity"],
        "policy": {"version": MATCH_POLICY_VERSION,
                   "sha256": _sha256_text(json.dumps(MATCH_POLICY, sort_keys=True,
                                                     ensure_ascii=False))},
        "evaluator_files": evaluator_file_hashes(),
        "zero_inference": {"model_calls": 0,
                           "note": ("araç hiçbir model çağrısı yapmaz; adaylar yalnız kayıtlı "
                                    "response-parsed.json'dan okunur, ölçüm donmuş gold'a karşıdır")},
    }
    return {
        "schema": REPORT_SCHEMA,
        "created_at": _now(),
        "experiment": EXPERIMENT,
        "method": {
            "inference_calls": 0,
            "selection_rule": ("§14: yalnız experiment/schema/reader/contract + producer identity "
                               "güncel olan 001D attempt'leri; hücre başına en yeni pass (parsed "
                               "çıktılı) yoksa en yeni eligible; fallback yok"),
            "evaluator": "drawingto3d.semantic_evaluation (001D: yalnız V/VE; D kolu koşmaz)",
            "semantic_source": ("semantic_candidates.semantic_claim_flags / "
                                "candidate_has_semantic_claim / evidence_flags (tek kaynak)"),
            "notes": ["hücre kayıtları attempt klasörlerinden salt-okur kurulur",
                      "rapor aracı defteri kurmaz/değiştirmez; --write yalnız iki rapor dosyası"],
        },
        "identity": identity,
        "gold": gold_identity,
        "cells": [cells[cell_id] for page_id in DEV_PAGES for arm in ARMS
                  for cell_id in (f"{page_id}-{arm}",)],
        "arms": aggregates,
        "comparison": comparison,
        "rounds": {"round_1": round_gate("round_1", ROUND_1_CELLS, cells, evaluations),
                   "round_2": round_gate("round_2", ROUND_2_CELLS, cells, evaluations)},
        "invariants": invariants,
        "degeneracy": degeneracy,
        "completion": completion,
        "attempts": {"eligible_cells": len(eligible_cells), "ignored": len(ignored),
                     "orphans": orphans,
                     "ignored_attempts": ignored},
        "limits": [
            ("gold: 001B dondurulmuş corpus gold'u (provizyonel ajan anotasyonu; bağımsız insan "
             "onayı yok — 001B niteliği aynen)"),
            ("001D'de D kolu koşmaz: `comparison.vs_d` satırları ölçüm değildir; ölçüm kapısı "
             "`cell_measurement`tır (§19)"),
            ("rapor `complete` bayrağı yalnız kanıt varlığıdır (eligible attempt + scorable ölçüm "
             "+ semantik-valid çıktı); kapı başarısı ya da ürün doğruluk sertifikası değildir"),
            ("seçili attempt'ler farklı koşu anlarından olabilir; kimlikleri hücre satırındadır"),
        ],
    }


# ------------------------------------------------------------------ markdown


def _mark(value) -> str:
    return {True: "✓", False: "✗"}.get(value, "—")


def _dash(value) -> str:
    return "—" if value is None else str(value)


def render_markdown(report: dict) -> str:
    lines: list[str] = ["# SEMREAD-001D — dev raporu (§13–§26; salt-okur, 0 inference)", ""]
    identity = report["identity"]
    completion = report["completion"]
    lines += [
        f"**Kimlik:** producer `{identity['producer_identity'][:16]}…` · contract "
        f"`{identity['contract_version']}` · schema/reader `{identity['schema_version']}` / "
        f"`{identity['reader_version']}`",
        f"**Tamamlanma:** {'EVET' if completion['complete'] else 'HAYIR'} — "
        f"{'; '.join(completion['reasons']) if completion['reasons'] else 'kanıt var'} "
        f"(eligible {len(completion['eligible_cells'])}/{len(report['cells'])}, ölçülü "
        f"{len(completion['measured_cells'])}, semantik-valid {len(completion['semantic_valid_cells'])})",
        f"**Inference:** {identity['zero_inference']['model_calls']}",
        "",
        "## 1. Hücreler",
        "",
        "| hücre | attempt | durum | formal | aday | semantik aday | semantik-valid | ölçüm | gold eşleşen | yerelleştirme | alan doğr. | kopya | maxItems |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell in report["cells"]:
        formal = cell.get("formal") or {}
        semantic = cell.get("semantic") or {}
        gold = cell.get("gold") or {}
        measurement = cell.get("measurement") or {}
        lines.append(
            f"| {cell['cell']} | {(cell.get('attempt_id') or '—').split('/')[-1]} | "
            f"{cell.get('attempt_state')} | {_mark(formal_valid(formal) if formal else None)} | "
            f"{_dash(formal.get('candidate_count'))} | "
            f"{_dash(semantic.get('semantic_candidate_count'))} | "
            f"{_mark(cell.get('semantic_valid_output'))} | "
            f"{_mark(measurement.get('measured'))} | "
            f"{_dash(gold.get('matched_claim_count'))} | "
            f"{_dash(gold.get('localization'))} | {_dash(gold.get('form_accuracy'))} | "
            f"{_dash((cell.get('duplicates') or {}).get('duplicates_total'))} | "
            f"{_mark(formal.get('max_items_hit'))} |")
    lines += ["", "## 2. Round kapıları (§57/§72)", ""]
    for key in ("round_1", "round_2"):
        gate = report["rounds"][key]
        lines.append(f"**{key}:** {'GEÇTİ' if gate['passed'] else 'AÇIK'} — açık: "
                     f"{', '.join(gate['open']) or 'yok'}")
    lines += ["", "## 3. Kol toplamları (gold; D kolu 001D'de koşmaz)", ""]
    for arm in ARMS:
        agg = report["arms"].get(arm)
        if not agg:
            lines.append(f"- **{arm}:** değerlendirilmiş hücre yok")
            continue
        lines.append(f"- **{arm}:** aday {agg['candidates']} · eşleşen {agg['matched']} · "
                     f"yerelleştirme {_dash(agg['localization_match_rate'])} · alan doğruluğu "
                     f"{_dash(agg['semantic_field_accuracy'])} · bağlama "
                     f"{_dash(agg['target_binding_accuracy'])} · overclaim "
                     f"{_dash(agg['candidate_overclaim_rate'])}")
    degeneracy = report["degeneracy"]
    if degeneracy["degeneracy_warning"]:
        lines += ["", f"**Degenerasyon uyarısı (§25):** birden çok hücre maxItems — "
                      f"{degeneracy['max_items_cells']}"]
    ignored = report["attempts"]["ignored_attempts"]
    if ignored:
        lines += ["", f"## 4. Yok sayılan attempt'ler ({len(ignored)}; fallback yok)", ""]
        for row in ignored:
            lines.append(f"- {row['cell']}/{row['attempt']} ({row.get('state')}): "
                         f"{'; '.join(row['reasons'])}")
    lines += ["", "## 5. Sınırlar", ""]
    for limit in report["limits"]:
        lines.append(f"- {limit}")
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict) -> dict:
    """İki rapor dosyasını yaz (§27) — defter dosyalarına (state/attempt/bütçe) dokunulmaz."""
    LAB.mkdir(parents=True, exist_ok=True)
    json_path = LAB / "dev-report.json"
    md_path = LAB / "dev-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="raporu out/lab/semread-001d/dev-report.{json,md} olarak yaz")
    parser.add_argument("--json", action="store_true", help="stdout'a JSON yaz (varsayılan: markdown)")
    args = parser.parse_args(argv)
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    if args.write:
        paths = write_report(report)
        print(f"yazıldı: {paths['json']} + {paths['md']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
