"""SEMREAD-001C — §37/§3: OFFLINE dev semantic evaluation (0 model çağrısı).

Görev (güncel plan §37, PLAN_LATEST):

    8 seçili geçerli 001C dev attempt (V/VE) + D kolu
    → mevcut (dondurulmuş) dev gold
    → offline D/V/VE semantik değerlendirme
    → `dev-semantic-report.json` + `dev-semantic-report.md`

İlkeler:

* **Sıfır inference:** hiçbir model çağrısı yapılmaz. V/VE adayları defterdeki seçili
  attempt'lerin `response-parsed.json`'ından; D adayları deterministic attempt'ten okunur.
  Script VLM çağrı zincirini (`drawingto3d.llama`) **import etmez** ve bunu çalışma anında
  denetler (fail-closed).
* **Tek değerlendirici:** üç kol da `drawingto3d.semantic_evaluation` ile, aynı `MATCH_POLICY`
  ve aynı gold üzerinden puanlanır (D/V/VE same evaluator).
* **Salt-okur:** deftere/attempt'lere yazılmaz; yalnız iki rapor dosyası yazılır (`--write`).
* **Gold kimliği dondurulmuş kaynaktan:** `eval/semread_001b_gold/FREEZE.json` içindeki
  `reference_sha256` ile birebir denetlenir; uyuşmazlıkta fail-closed durulur.
* **Gerçek istek ayarları** `request-manifest.json` `options` alanından okunur (manifest
  `settings` yalnız donmuş sözleşme anlık görüntüsüdür; kol-başına repeat_penalty orada yaşamaz).

Ek analizler (§27/§28/§38): aday içerik-doluluk taraması (semantic fill), aday sayısı dağılımı,
plate-VE 41-aday sınıflaması (gold match / false positive / unscorable extra / duplicate /
observation-row echo), V 1-aday okuması, kesik (truncated) denemelerin içerik taraması,
değerlendirme kimliği ve sonraki shared-envelope hipotezi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.semantic_candidates import Region, regions_match  # noqa: E402
from drawingto3d.semantic_evaluation import (MATCH_POLICY, MATCH_POLICY_VERSION,  # noqa: E402
                                             aggregate, candidate_anchor, claim_region,
                                             compare_arms, evaluate_page)

EXPERIMENT = "semread-001c"
LAB = ROOT / "out" / "lab" / EXPERIMENT
ATTEMPTS = LAB / "attempts"
DEV_REPORT = LAB / "dev-report.json"
GOLD_001B = ROOT / "out" / "lab" / "semread-001b" / "corpus" / "gold"
FREEZE = ROOT / "eval" / "semread_001b_gold" / "FREEZE.json"
REPORT_SCHEMA = "semread-001c-dev-semantic-eval/1"
DEV_PAGES = ("dev-plate-pocket", "dev-flange-book", "dev-flange-elbow", "dev-drawing-2")
ARMS = ("D", "V", "VE")
EVALUATOR_FILES = ("src/drawingto3d/semantic_evaluation.py",
                   "src/drawingto3d/semantic_candidates.py",
                   "eval/semread_001c_dev_semantic_eval.py")
# Observation-satırı yankısı eşiği: model koordinatı 4 ondalığa yuvarlar; tablo değerleri daha
# uzun olabilir. Tüm dört koordinatta |Δ| ≤ bu değer ise aday, tablo satırının yankısı sayılır.
ECHO_TOLERANCE = 0.0006
FIELD_KEYS = ("callout_text", "representation", "physical", "form", "size", "count",
              "termination", "depth", "target_observation_id", "target_state")


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ gold (dondurulmuş)

def load_dev_gold() -> dict:
    """Dört dev sayfanın dondurulmuş gold'unu yükler ve FREEZE.json hash'iyle denetler."""
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
                          "claim_count": len(reference.get("claims") or []),
                          "spec_sha256": entry.get("spec_sha256"),
                          "split": entry.get("split")}
    return golds


# ------------------------------------------------------------------ attempt seçimi

def attempt_dirs(cell: str) -> list[Path]:
    root = ATTEMPTS / cell
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def attempt_row(directory: Path) -> dict | None:
    """Attempt klasörünü deftere geçmiş kaydıyla birlikte okur (salt-okur; yazmaz)."""
    result = read_json(directory / "result.json")
    if result is None:
        return None                      # sonuçlandırılmamış (orphan) klasör: kayıt değildir
    manifest = read_json(directory / "manifest.json") or {}
    request = read_json(directory / "request-manifest.json") or {}
    resources = read_json(directory / "resources.json") or {}
    return {"directory": directory, "result": result, "manifest": manifest,
            "request": request, "resources": resources,
            "attempt_id": result.get("attempt_id") or f"{directory.parent.name}/{directory.name}",
            "state": result.get("state"),
            "manifest_sha256": sha256_of(directory / "manifest.json"),
            "result_sha256": sha256_of(directory / "result.json"),
            "parsed_sha256": sha256_of(directory / "response-parsed.json")}


def chosen_attempt(cell: str) -> dict | None:
    """Seçili attempt: **en yeni pass** (dev-report cell_view ile aynı kural) + parsed çıktı var."""
    rows = [row for row in (attempt_row(directory) for directory in attempt_dirs(cell))
            if row is not None]
    passes = [row for row in rows if row["state"] == "pass"
              and (row["directory"] / "response-parsed.json").exists()]
    return passes[-1] if passes else None


# ------------------------------------------------------------------ içerik / sınıflama

def candidate_semantic_flags(item: dict) -> dict:
    """Adayın taşıdığı **gerçek semantik içerik** bayrakları (unknown/boş = içerik değil)."""
    callout = (item.get("callout") or {}).get("text") or ""
    representation = (item.get("representation") or {}).get("kind")
    physical = (item.get("physical") or {}).get("kind")
    form = (item.get("form") or {}).get("symbol")
    size = item.get("size") or {}
    count = item.get("count") or {}
    termination = (item.get("termination") or {}).get("kind")
    depth = item.get("depth") or {}
    target = item.get("target") or {}
    return {
        "callout_text": bool(str(callout).strip()),
        "representation": bool(representation) and representation != "unknown",
        "physical": bool(physical) and physical != "unknown",
        "form": bool(form) and form != "unknown",
        "size": size.get("value") is not None or size.get("state") == "known",
        "count": count.get("printed") is not None or count.get("found_circles") is not None,
        "termination": bool(termination) and termination != "unknown",
        "depth": depth.get("value") is not None or depth.get("state") == "known",
        "target_observation_id": bool(target.get("observation_id")),
        "target_state": bool(target.get("state")) and target.get("state") != "unknown",
    }


def semantic_fill(items: list[dict]) -> dict:
    counts = {key: 0 for key in FIELD_KEYS}
    contentful = 0
    for item in items:
        flags = candidate_semantic_flags(item)
        if any(flags.values()):
            contentful += 1
        for key, value in flags.items():
            counts[key] += int(value)
    return {"candidates": len(items), "contentful_candidates": contentful, "fields": counts}


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


def _region_tuple(region) -> tuple | None:
    return tuple(round(float(value), 6) for value in region.as_list()) \
        if region is not None and hasattr(region, "as_list") else None


def duplicate_scan(items: list[dict]) -> dict:
    """Kopya/yakın kopya taraması: anchor bölgesi **daha önceki** bir adayla aynı ya da
    eşleşiyorsa bu aday kopya sayılır (ilk üye değil). İki düzey: exact (6 ondalık eşit) ve
    near (`regions_match` — eşleştiricinin kendi politikası)."""
    anchors = [candidate_anchor(item) for item in items]
    ids = [item.get("candidate_id") for item in items]
    exact_of: list[str | None] = [None] * len(items)
    near_of: list[str | None] = [None] * len(items)
    exact_pairs = near_pairs = 0
    for index in range(len(items)):
        for earlier in range(index):
            if anchors[index] is None or anchors[earlier] is None:
                continue
            same = _region_tuple(anchors[index]) == _region_tuple(anchors[earlier])
            if same:
                exact_pairs += 1
                if exact_of[index] is None:
                    exact_of[index] = ids[earlier]
            elif regions_match(anchors[index], anchors[earlier]):
                near_pairs += 1
                if near_of[index] is None:
                    near_of[index] = ids[earlier]
    return {"exact_of": exact_of, "near_of": near_of, "exact_pairs": exact_pairs,
            "near_pairs": near_pairs,
            "exact_duplicates": sum(1 for value in exact_of if value),
            "near_duplicates": sum(1 for value in near_of if value),
            # Kopya toplamı: birebir ya da yakın — her iki durumda da "daha önceki bir adayın
            # tekrarı" (ilk üye sayılmaz).
            "duplicates_total": sum(1 for index in range(len(items))
                                    if exact_of[index] or near_of[index])}


def classify_partition(flags: list[dict]) -> dict:
    """Adayları sıralı öncelikle **tek** sınıfa böler: matched > kopya (birebir/yakın) > yankı >
    false_positive > unscorable_extra > other. Toplam her zaman aday sayısına eşittir."""
    partition = {"matched": 0, "duplicate": 0, "echo": 0, "false_positive": 0,
                 "unscorable_extra": 0, "other": 0}
    for row in flags:
        if row["matched"]:
            partition["matched"] += 1
        elif row["exact_duplicate_of"] is not None or row["near_duplicate_of"] is not None:
            partition["duplicate"] += 1
        elif row["echo"] is not None:
            partition["echo"] += 1
        elif row["extra_kind"] == "false_positive":
            partition["false_positive"] += 1
        elif row["extra_kind"] == "unscorable_extra_candidate":
            partition["unscorable_extra"] += 1
        else:
            partition["other"] += 1
    return partition


def truncated_raw_scan(text: str) -> dict:
    """Kesik ham gövdede kaba içerik taraması (resmi ayrıştırma değil: kesik JSON parse edilmez)."""
    texts = re.findall(r'"text"\s*:\s*"([^"]*)"', text)
    kinds = re.findall(r'"kind"\s*:\s*"([a-z_]+)"', text)
    sizes = re.findall(r'"value"\s*:\s*(-?[0-9]+(?:\.[0-9]+)?)', text)
    return {"candidate_id_occurrences": text.count('"candidate_id"'),
            "nonempty_callout_texts": sum(1 for value in texts if value.strip()),
            "nonempty_kinds": sum(1 for value in kinds if value not in ("unknown", "")),
            "numeric_size_values": len(sizes),
            "note": "kesik gövde üzerinde regex taraması; resmi parse değildir"}


# ------------------------------------------------------------------ hücre kaydı

def cell_record(page_id: str, arm: str, gold: dict, dev_report_cells: dict) -> dict:
    cell = f"{page_id}-{arm}"
    chosen = chosen_attempt(cell)
    record: dict = {"cell": cell, "page_id": page_id, "arm": arm}
    report_row = dev_report_cells.get(cell) or {}
    record["dev_report_chosen"] = report_row.get("chosen_attempt")
    if chosen is None:
        record["status"] = "no_valid_attempt"
        record["matches_dev_report"] = None
        return record
    record["status"] = "evaluated"
    directory = chosen["directory"]
    record["matches_dev_report"] = (report_row.get("chosen_attempt") == directory.name) \
        if report_row.get("chosen_attempt") else None
    parsed = read_json(directory / "response-parsed.json") or {}
    items = parsed.get("items") or []
    options = (chosen["request"].get("options") or {})
    stats = chosen["resources"].get("stats") or {}
    fill = semantic_fill(items)
    duplicates = duplicate_scan(items)
    evaluation = evaluate_page(gold, {"response": parsed})
    extras_by_id = {row["candidate_id"]: row["kind"] for row in evaluation["extras"]}
    matched_ids = {pair["candidate_id"] for pair in evaluation["matching"]["pairs"]}
    table_rows = []
    prompt_path = directory / "prompt.txt"
    if arm == "VE" and prompt_path.exists():
        table_rows = prompt_table_rows(prompt_path.read_text(encoding="utf-8"))
    flags: list[dict] = []
    for index, item in enumerate(items):
        candidate_id = item.get("candidate_id")
        anchor = candidate_anchor(item)
        echo = echo_of(anchor, table_rows) if arm == "VE" else None
        flags.append({
            "candidate_id": candidate_id,
            "anchor": anchor.as_list() if anchor is not None else None,
            "matched": candidate_id in matched_ids,
            "exact_duplicate_of": duplicates["exact_of"][index],
            "near_duplicate_of": duplicates["near_of"][index],
            "echo": echo,
            "extra_kind": extras_by_id.get(candidate_id),
        })
    partition = classify_partition(flags)
    record.update({
        "attempt_id": chosen["attempt_id"],
        "attempt_dir": str(directory),
        "created_at": chosen["manifest"].get("created_at"),
        "producer_identity": chosen["manifest"].get("producer_identity"),
        "evaluation_identity_at_attempt": chosen["manifest"].get("evaluation_identity"),
        "manifest_sha256": chosen["manifest_sha256"],
        "result_sha256": chosen["result_sha256"],
        "parsed_sha256": chosen["parsed_sha256"],
        "request_options": options,
        "done_reason": stats.get("done_reason"),
        "eval_count": stats.get("eval_count"),
        "prompt_eval_count": stats.get("prompt_eval_count"),
        "seconds": chosen["result"].get("seconds"),
        "gates": chosen["result"].get("gates"),
        "fill": fill,
        "duplicates": {"exact_duplicates": duplicates["exact_duplicates"],
                       "near_duplicates": duplicates["near_duplicates"],
                       "duplicates_total": duplicates["duplicates_total"],
                       "exact_pairs": duplicates["exact_pairs"],
                       "near_pairs": duplicates["near_pairs"]},
        "echo_analysis": None if arm != "VE" else {
            "prompt_table_rows": len(table_rows),
            "echoed_candidates": sum(1 for row in flags if row["echo"]),
            "text_row_echoes": sum(1 for row in flags
                                   if row["echo"] and row["echo"]["kind"] == "text"),
            "geometry_row_echoes": sum(1 for row in flags
                                       if row["echo"] and row["echo"]["kind"] != "text"),
        },
        "partition": partition,
        "flags": flags,
        "summary": evaluation["summary"],
    })
    record["_evaluation"] = evaluation          # toplama/karşılaştırma için tam çıktı (yazılmaz)
    return record


def prior_attempt_rows(page_id: str, arm: str) -> list[dict]:
    """Seçili attempt dışındaki denemelerin özeti (kesik flood kanıtı; §27/§28 destek)."""
    rows: list[dict] = []
    for directory in attempt_dirs(f"{page_id}-{arm}"):
        row = attempt_row(directory)
        if row is None:
            rows.append({"attempt": directory.name, "state": "orphan_no_result"})
            continue
        resources = row["resources"]
        stats = resources.get("stats") or {}
        parsed = read_json(directory / "response-parsed.json")
        entry = {
            "attempt": directory.name,
            "state": row["state"],
            "failure_kind": row["result"].get("failure_kind"),
            "options": (row["request"].get("options") or {}),
            "done_reason": stats.get("done_reason"),
            "eval_count": stats.get("eval_count"),
            "seconds": row["result"].get("seconds"),
        }
        if parsed is not None:
            fill = semantic_fill(parsed.get("items") or [])
            entry["items"] = fill["candidates"]
            entry["contentful"] = fill["contentful_candidates"]
        else:
            raw = read_json(directory / "response-raw.json") or {}
            content = ((raw.get("body") or {}).get("message") or {}).get("content") \
                or raw.get("content") or ""
            if content:
                entry["raw_scan"] = truncated_raw_scan(content)
        rows.append(entry)
    return rows


# ------------------------------------------------------------------ rapor

def evaluator_file_hashes() -> list[dict]:
    return [{"path": relative, "sha256": sha256_of(ROOT / relative)}
            for relative in EVALUATOR_FILES]


def evaluation_identity(golds: dict, attempt_rows: list[dict]) -> dict:
    digest = hashlib.sha256()
    for row in evaluator_file_hashes():
        digest.update(f"{row['path']}\0{row['sha256']}\0".encode())
    digest.update(json.dumps(MATCH_POLICY, sort_keys=True, ensure_ascii=False).encode())
    for page_id in DEV_PAGES:
        digest.update(f"{page_id}\0{golds[page_id]['reference_sha256']}\0".encode())
    for row in sorted(attempt_rows, key=lambda item: item.get("attempt_id") or ""):
        digest.update(f"{row.get('attempt_id')}\0{row.get('manifest_sha256')}\0"
                      f"{row.get('result_sha256')}\0{row.get('parsed_sha256')}\0".encode())
    digest.update(b"inference=0")
    return {
        "evaluation_run_id": digest.hexdigest()[:32],
        "evaluation_identity": digest.hexdigest(),
        "policy": {"version": MATCH_POLICY_VERSION,
                   "sha256": hashlib.sha256(json.dumps(MATCH_POLICY, sort_keys=True,
                                                       ensure_ascii=False).encode()).hexdigest()},
        "evaluator_files": evaluator_file_hashes(),
        "gold": {"freeze": str(FREEZE.relative_to(ROOT)),
                 "freeze_sha256": sha256_of(FREEZE),
                 "pages": {page_id: {"reference_sha256": golds[page_id]["reference_sha256"],
                                     "claim_count": golds[page_id]["claim_count"],
                                     "spec_sha256": golds[page_id]["spec_sha256"]}
                           for page_id in DEV_PAGES}},
        "zero_inference": {
            "model_calls": 0,
            "llama_imported": any(name == "drawingto3d.llama" or name.endswith(".llama")
                                  for name in sys.modules),
            "note": ("V/VE adayları defterdeki seçili attempt'lerin parsed çıktısından, D adayları "
                     "deterministic attempt'ten okunur; bu script model çağırmaz ve llama import "
                     "etmez"),
        },
    }


def determine_reading(cell: dict, priors: list[dict]) -> dict:
    """1-aday/boş hücreler için ölçüme bağlı okuma (§28): bastırma mı, ham sayfa mı?"""
    contentful = (cell.get("fill") or {}).get("contentful_candidates")
    flood = [row for row in priors if row.get("state") == "truncated_output"]
    flood_items = sum(row.get("raw_scan", {}).get("candidate_id_occurrences") or
                      row.get("items") or 0 for row in flood)
    flood_contentful = sum(row.get("raw_scan", {}).get("nonempty_callout_texts") or
                           row.get("contentful") or 0 for row in flood)
    if contentful:
        reading = "içerik var: bastırma sorusu bu hücre için geçerli değil"
    elif flood and flood_contentful == 0 and flood_items > 0:
        reading = ("içerik yokluğu zarf/penaltıdan bağımsız: aynı hücrenin kesilen flood "
                   "denemelerinde de (rp farklı) sıfır içerik var; 'aşırı bastırma gerçek "
                   "içeriği kesti' okuması bu veriyle desteklenmiyor")
    elif flood:
        reading = "flood denemelerinde içerik sinyali var; bastırma okuması incelenmeli"
    else:
        reading = "karşılaştırılabilir flood denemesi yok; okuma için kanıt yetersiz"
    return {"cell": cell["cell"], "contentful_candidates": contentful,
            "prior_flood_attempts": len(flood), "prior_flood_candidate_occurrences": flood_items,
            "prior_flood_contentful_signals": flood_contentful, "reading": reading}


def build_report() -> dict:
    golds = load_dev_gold()
    dev_report = read_json(DEV_REPORT) or {}
    dev_report_cells = dev_report.get("cells") or {}
    cells: list[dict] = []
    per_page: dict[str, dict] = {}
    for page_id in DEV_PAGES:
        arms: dict = {}
        for arm in ARMS:
            record = cell_record(page_id, arm, golds[page_id]["reference"], dev_report_cells)
            cells.append(record)
            if record.get("status") == "evaluated":
                arms[arm] = record["_evaluation"]
                record["prior_attempts"] = prior_attempt_rows(page_id, arm)
        per_page[page_id] = arms
    aggregates = {}
    for arm in ARMS:
        pages = [per_page[page_id][arm] for page_id in per_page if arm in per_page[page_id]]
        if pages:
            aggregates[arm] = aggregate(pages)
    comparison = compare_arms({page_id: arms for page_id, arms in per_page.items() if arms}) \
        if any(per_page.values()) else {"vs_d": {}, "ve_vs_v": {}}
    distribution = {}
    for arm in ARMS:
        counts = {record["cell"]: record["fill"]["candidates"] for record in cells
                  if record["arm"] == arm and record.get("status") == "evaluated"}
        values = sorted(counts.values())
        distribution[arm] = {
            "cells": counts, "min": values[0] if values else None,
            "median": statistics.median(values) if values else None,
            "max": values[-1] if values else None,
            "total": sum(values),
        }
    # plate-VE 41-aday analizi (§27) — sınıflama kayıttan aynen taşınır.
    plate_ve = next((record for record in cells
                     if record["cell"] == "dev-plate-pocket-VE"), None)
    plate_ve_analysis = None
    if plate_ve and plate_ve.get("status") == "evaluated":
        flags = plate_ve["flags"]
        flag_counts = {
            "matched": sum(1 for row in flags if row["matched"]),
            "exact_duplicate": sum(1 for row in flags if row["exact_duplicate_of"]),
            "near_duplicate": sum(1 for row in flags if row["near_duplicate_of"]),
            "echo": sum(1 for row in flags if row["echo"]),
            "echo_text_row": sum(1 for row in flags
                                 if row["echo"] and row["echo"]["kind"] == "text"),
            "false_positive": sum(1 for row in flags if row["extra_kind"] == "false_positive"),
            "unscorable_extra": sum(1 for row in flags
                                    if row["extra_kind"] == "unscorable_extra_candidate"),
        }
        plate_ve_analysis = {
            "cell": "dev-plate-pocket-VE", "candidates": len(flags),
            "flag_counts": flag_counts, "partition": plate_ve["partition"],
            "overlap": {
                "duplicate_and_echo": sum(1 for row in flags
                                          if row["near_duplicate_of"] and row["echo"]),
                "matched_and_echo": sum(1 for row in flags if row["matched"] and row["echo"]),
            },
            "note": ("sınıflar çoklu-etiketlidir; `partition` sıralı öncelikle (matched > kopya > "
                     "yankı > false_positive > unscorable) toplamı aday sayısına eşitler"),
        }
    one_candidate_analysis = []
    for record in cells:
        if record.get("status") != "evaluated":
            continue
        if record["fill"]["candidates"] <= 1:
            gold = golds[record["page_id"]]["reference"]
            anchor = record["flags"][0]["anchor"] if record["flags"] else None
            box = Region(**dict(zip(("x0", "y0", "x1", "y1"), anchor))) if anchor else None
            overlaps = {"target_regions": [], "callout_regions": []}
            for claim in gold.get("claims") or []:
                target = claim_region(claim)
                callout = claim.get("callout") or {}
                callout_box = None
                if isinstance(callout.get("region"), dict):
                    callout_box = Region(**callout["region"])
                if box is not None and target is not None and regions_match(box, target):
                    overlaps["target_regions"].append(claim["claim_id"])
                if box is not None and callout_box is not None and regions_match(box, callout_box):
                    overlaps["callout_regions"].append(claim["claim_id"])
            entry = {"cell": record["cell"], "attempt_id": record["attempt_id"],
                     "candidates": record["fill"]["candidates"], "anchor": anchor,
                     "gold_overlap": overlaps,
                     "gold_claim_count": len(gold.get("claims") or []),
                     "request_options": record["request_options"],
                     "done_reason": record["done_reason"], "eval_count": record["eval_count"]}
            entry.update(determine_reading(record, record.get("prior_attempts") or []))
            one_candidate_analysis.append(entry)
    total_contentful = sum(record["fill"]["contentful_candidates"] for record in cells
                           if record.get("status") == "evaluated")
    total_candidates = sum(record["fill"]["candidates"] for record in cells
                           if record.get("status") == "evaluated")
    by_arm = {}
    for arm in ARMS:
        arm_rows = [record for record in cells
                    if record.get("status") == "evaluated" and record["arm"] == arm]
        by_arm[arm] = {
            "candidates": sum(record["fill"]["candidates"] for record in arm_rows),
            "contentful": sum(record["fill"]["contentful_candidates"] for record in arm_rows),
            "cells": len(arm_rows),
        }
    parse_valid = [record for record in cells
                   if record.get("status") == "evaluated" and record["arm"] in ("V", "VE")]
    pv_candidates = sum(record["fill"]["candidates"] for record in parse_valid)
    pv_contentful = sum(record["fill"]["contentful_candidates"] for record in parse_valid)
    selected_rows = [record for record in cells if record.get("status") == "evaluated"]
    identity = evaluation_identity(golds, selected_rows)
    hypothesis = {
        "question": "parse-valid output semantik olarak tamamen degenerate mı? (§37)",
        "answer": (
            ("EVET — parse-valid (V/VE) çıktı semantik olarak degenerate"
             if pv_contentful == 0 else "HAYIR — en az bir V/VE hücresinde içerik var")
            + f": seçili {len(parse_valid)} V/VE hücresinde {pv_candidates} adayın "
              f"{pv_contentful} tanesi semantik alan taşıyor"),
        "evidence": [
            f"V/VE: {pv_candidates} aday, {pv_contentful} içerikli; "
            f"D (deterministic): {by_arm.get('D', {}).get('candidates')} aday, "
            f"{by_arm.get('D', {}).get('contentful')} içerikli",
            "V/VE hücreleri yalnız biçimsel (parse+refs) geçerli; içerik ölçümü bu raporda ilk kez",
        ],
        "shared_envelope_expectations": [
            ("H1 (§5 yapısal anti-loop): maxItems=32 + kopya kuralı, elbow-V (40–64 öğe) ve "
             "plate-VE (41 öğe) flood rejimini sayıca sınırlar. Bu raporun bulgusu içerik "
             "yokluğudur; H1 yalnız sınırlılığı hedefler, içerik üretimini iyileştirdiği "
             "iddia edilemez."),
            ("H2 (§6 ortak repeat_penalty): V kolu 1.25 ile döngü üretmişti (elbow-V kesik "
             "denemeleri); ortak 1.25'e iniş bu döngüyü geri getirebilir — yapısal cap + kopya "
             "kuralı ile birlikte sınanmalı."),
            ("H3 (§8 requalification): 8/8 biçimsel kapı tekrar aranırken içerik doluluk "
             "ölçümü de kaydedilmeli; bu rapor 'biçimsel geçerli + sıfır içerik' durumunu "
             "belgeliyor."),
        ],
        "note": ("Bu bölüm ölçüme bağlı beklenti/hipotezdir; eşik veya başarı ölçütü değildir "
                 "(sonradan accuracy eşiği uydurma yasağı, plan §9)."),
    }
    return {
        "schema": REPORT_SCHEMA,
        "created_at": _now(),
        "experiment": EXPERIMENT,
        "method": {
            "inference_calls": 0,
            "evaluator": "drawingto3d.semantic_evaluation (D/V/VE aynı yol)",
            "selection_rule": "hücre başına en yeni pass attempt (dev-report cell_view kuralı)",
            "notes": ["adaylar response-parsed.json'dan okunur; D adayları deterministic "
                      "attempt'ten gelir",
                      "gerçek istek ayarları request-manifest.json options'tan okunur"],
        },
        "identity": identity,
        "gold": {page_id: {"claim_count": golds[page_id]["claim_count"],
                           "reference_sha256": golds[page_id]["reference_sha256"]}
                 for page_id in DEV_PAGES},
        "cells": [{key: value for key, value in record.items() if key != "_evaluation"}
                  for record in cells],
        "page_evaluations": {
            page_id: {arm: {"summary": evaluation["summary"],
                            "matching": {key: evaluation["matching"][key] for key in
                                         ("pairs", "ambiguous", "unmatched_claims",
                                          "unmatched_candidates")},
                            "extras": evaluation["extras"],
                            "per_claim": evaluation["per_claim"]}
                      for arm, evaluation in arms.items()}
            for page_id, arms in per_page.items()},
        "aggregates": aggregates,
        "comparison": comparison,
        "candidate_count_distribution": distribution,
        "plate_ve_analysis": plate_ve_analysis,
        "one_candidate_analysis": one_candidate_analysis,
        "hypothesis": hypothesis,
        "totals": {"candidates": total_candidates, "contentful_candidates": total_contentful,
                   "evaluated_cells": len(selected_rows),
                   "parse_valid": {"cells": len(parse_valid), "candidates": pv_candidates,
                                   "contentful": pv_contentful},
                   "by_arm": by_arm},
        "limits": [
            "gold provizyonel ajan annotasyonudur; bağımsız insan onayı yoktur (001B niteliği "
            "aynen taşınır)",
            "metrik oranları bu nitelikle okunmalıdır: ürün doğruluk sertifikası değildir",
            "seçili attempt'ler farklı zarf revizyonlarında koştu (request_options sütununa "
            "bakınız); kol karşılaştırması bu raporda nedensel değildir",
        ],
    }


# ------------------------------------------------------------------ markdown

def _percent(value) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _dash(value) -> str:
    return "—" if value is None else str(value)


def render_markdown(report: dict) -> str:
    lines: list[str] = ["# SEMREAD-001C — dev semantik değerlendirme (§37)", ""]
    totals = report["totals"]
    parse_valid = totals["parse_valid"]
    identity = report["identity"]
    lines += [
        f"**Kimlik:** `{identity['evaluation_run_id']}` · **inference:** "
        f"{identity['zero_inference']['model_calls']} (llama import: "
        f"{'EVET' if identity['zero_inference']['llama_imported'] else 'hayır'})",
        f"**Politika:** {identity['policy']['version']}",
        "",
        "## 1. Özet — asıl soru",
        "",
        f"Parse-valid kollar (V/VE): seçili {parse_valid['cells']} hücrede "
        f"**{parse_valid['candidates']} adayın {parse_valid['contentful']}** tanesi semantik "
        f"alan taşıyor. D kolu (deterministic referans): "
        f"{totals['by_arm'].get('D', {}).get('candidates')} adayın "
        f"{totals['by_arm'].get('D', {}).get('contentful')} tanesi içerikli.",
        "",
    ]
    if parse_valid["contentful"] == 0:
        lines += [
            "**Yanıt (§37): EVET — parse-valid (V/VE) çıktı semantik olarak degenerate.**",
            "Adaylar yalnız kaynak bölgesi kutularıdır (callout metni, temsil, form, ölçü, "
            "bitiş, hedef: hepsi boş/unknown). `valid_output_rate=1.0` yalnız biçimsel "
            "geçerlilikti; içerik ölçümü bu raporda ilk kez yapıldı ve V/VE'de sıfır çıktı. "
            "D kolu ise içerikli okuyor — kıyas aynı evaluator ve aynı gold iledir.",
        ]
    else:
        lines += ["**Yanıt (§37): HAYIR — en az bir V/VE hücresinde içerik var (aşağıdaki "
                  "tablolara bakınız).**"]
    lines += [
        "",
        "## 2. Hücreler (seçili attempt'ler)",
        "",
        "| hücre | attempt | aday | içerikli | eşleşen | kopya (birebir+yakın) | yankı | done | eval | "
        "rp | num_predict | num_ctx |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in report["cells"]:
        if record.get("status") != "evaluated":
            lines.append(f"| {record['cell']} | — | — | — | — | — | — | seçili pass attempt "
                         f"yok | | | | |")
            continue
        options = record["request_options"]
        echo = record["echo_analysis"]
        lines.append(
            f"| {record['cell']} | {record['attempt_id'].split('/')[-1]} | "
            f"{record['fill']['candidates']} | {record['fill']['contentful_candidates']} | "
            f"{record['summary']['matched']} | {record['duplicates']['duplicates_total']} | "
            f"{'—' if echo is None else echo['echoed_candidates']} | "
            f"{_dash(record['done_reason'])} | {_dash(record['eval_count'])} | "
            f"{_dash(options.get('repeat_penalty'))} | {_dash(options.get('num_predict'))} | "
            f"{_dash(options.get('num_ctx'))} |")
    lines += [
        "",
        "| hücre | temsil | fiziksel | form | ölçü | sayı | bitiş | derinlik | hedef-id |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for record in report["cells"]:
        if record.get("status") != "evaluated":
            continue
        fields = record["fill"]["fields"]
        lines.append(
            f"| {record['cell']} | {fields['representation']} | {fields['physical']} | "
            f"{fields['form']} | {fields['size']} | {fields['count']} | "
            f"{fields['termination']} | {fields['depth']} | "
            f"{fields['target_observation_id']} |")
    lines += ["", "## 3. Kol toplamları (D/V/VE — aynı değerlendirici)", "",
              "| kol | aday | eşleşen | yerelleştirme | alan doğruluğu | bağlama | overclaim | "
              "abstention | FP | unscorable | belirsiz |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        agg = report["aggregates"].get(arm)
        if not agg:
            continue
        lines.append(
            f"| {arm} | {agg['candidates']} | {agg['matched']} | "
            f"{_percent(agg['localization_match_rate'])} | "
            f"{_percent(agg['semantic_field_accuracy'])} | "
            f"{_percent(agg['target_binding_accuracy'])} | "
            f"{_percent(agg['candidate_overclaim_rate'])} | "
            f"{_percent(agg['candidate_abstention_rate'])} | "
            f"{agg['false_positive_candidate_count']} | "
            f"{agg['unscorable_extra_candidate_count']} | {agg['ambiguous_claim_count']} |")
    lines += ["", "## 4. Aday sayısı dağılımı", "",
              "| kol | min | medyan | max | toplam |", "|---|---|---|---|---|"]
    for arm in ARMS:
        row = report["candidate_count_distribution"].get(arm) or {}
        lines.append(f"| {arm} | {row.get('min', '—')} | {row.get('median', '—')} | "
                     f"{row.get('max', '—')} | {row.get('total', '—')} |")
    plate = report.get("plate_ve_analysis")
    if plate:
        counts = plate["flag_counts"]
        lines += ["", "## 5. plate-VE 41-aday analizi (§27)", "",
                  f"- aday: **{plate['candidates']}**",
                  f"- gold eşleşmesi: **{counts['matched']}**",
                  f"- false positive (kapsam içi): **{counts['false_positive']}**",
                  f"- unscorable extra (kapsam dışı): **{counts['unscorable_extra']}**",
                  f"- birebir kopya: **{counts['exact_duplicate']}**; yakın kopya: "
                  f"**{counts['near_duplicate']}**",
                  f"- observation-satırı yankısı: **{counts['echo']}** "
                  f"(metin satırı: {counts['echo_text_row']}); kopya∩yankı: "
                  f"**{plate['overlap']['duplicate_and_echo']}**",
                  ""]
    lines += ["", "## 6. 1-aday hücre okuması (§28)", ""]
    for entry in report["one_candidate_analysis"]:
        options = entry.get("request_options") or {}
        lines += [
            f"- **{entry['cell']}** — {entry['candidates']} aday; rp "
            f"{options.get('repeat_penalty', '—')}; gold claim sayısı {entry['gold_claim_count']}; "
            f"gold target ile çakışma: {entry['gold_overlap']['target_regions'] or 'yok'}; "
            f"callout bölgesi ile çakışma: {entry['gold_overlap']['callout_regions'] or 'yok'}",
            f"  - okuma: {entry['reading']}",
        ]
    lines += ["", "## 7. Değerlendirme kimliği", "",
              f"- run: `{identity['evaluation_run_id']}` · evaluator kimliği: "
              f"`{identity['evaluation_identity'][:16]}…`",
              f"- MATCH_POLICY: {identity['policy']['version']} "
              f"(`{identity['policy']['sha256'][:16]}…`)",
              f"- gold FREEZE: `{identity['gold']['freeze']}` "
              f"(`{identity['gold']['freeze_sha256'][:16]}…`)",
              "- seçili attempt'ler: " + ", ".join(
                  f"{record['attempt_id']} (`{(record.get('manifest_sha256') or '')[:12]}…`)"
                  for record in report["cells"] if record.get("status") == "evaluated"),
              "", "## 8. Sonraki shared-envelope hipotezi (§38)", "",
              f"**Soru:** {report['hypothesis']['question']}", ""]
    for line in report["hypothesis"]["shared_envelope_expectations"]:
        lines.append(f"- {line}")
    lines += ["", f"_{report['hypothesis']['note']}_", "", "## 9. Sınırlar", ""]
    for limit in report["limits"]:
        lines.append(f"- {limit}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="raporu out/lab/semread-001c/ altına yaz (json + md)")
    args = parser.parse_args(argv)
    report = build_report()
    print(render_markdown(report))
    if args.write:
        LAB.mkdir(parents=True, exist_ok=True)
        (LAB / "dev-semantic-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (LAB / "dev-semantic-report.md").write_text(render_markdown(report), encoding="utf-8")
        print(f"yazıldı: {LAB / 'dev-semantic-report.json'} + dev-semantic-report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
