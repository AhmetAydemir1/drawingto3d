"""SEMREAD-001B — eşleştirme ve metrikler (D/V/VE aynı hedef evreni ve kurallarıyla).

Üç ilke (goal §5):

1. **Eşleştirme bölge/kaynak ilişkisine dayanır**, beklenen sayısal değere bakmaz. Değerle
   eşleştirme yapmak, doğru cevabı bilen bir hakemin adayı seçmesi demekti.
2. **Eşleşmeler bire birdir**; kopya adaylar recall'u şişirmez. Eşit derecede iyi iki eşleşme
   "belirsiz" olarak raporlanır, iki kez sayılmaz.
3. **Payda sıfırsa oran `null`** (not_applicable); tanımsız bölme yapılmaz.

Eşleştirme, tolerans, birim normalizasyonu ve belirsizlik politikası **final tahminlerden önce**
sabitlenir: `MATCH_POLICY` sürümlenir ve rapora aynen yazılır.

P1 (PLAN-5 §9–§12) ile sabitlenen dört karar — hepsi politika v2'de (`MATCH_POLICY`) yazılıdır:

* **Belirsiz eşleşme dışlanır** (§10): yakın puanlı rakip varsa kalem semantik alan puanlanmasına
  girmez, `ambiguous` olarak sayılır. Böylece sonuç aday sırasına bağlı olmaz.
* **Yerelleştirme ile alan doğruluğu ayrılır** (§11): `localization_match_rate` bölge eşleşmesini,
  `semantic_field_accuracy` alan alan doğruluğu ölçer; `target_binding` ayrı raporlanır.
* **Fazla adaylar kapsam-duyarlıdır** (§12): gold `exhaustiveness` o bölgeyi/konumu taradığını
  iddia etmiyorsa aday `unscorable_extra_candidate` olur (cezalanmaz), kapsıyorsa `false_positive`.
* **Karşılaştırma yüklem (predicate) bazındadır** (§9): her alan için scorable/kurtarılan/geriye
  giden sayıları ve `net_correct_gain` ayrı satırlarda; paydalar farklı olduğu için oran
  karşılaştırması tek başına karar kuralı değildir.
"""

from __future__ import annotations

from typing import Any

from drawingto3d.semantic_candidates import (Region, numeric_tolerance, regions_match)

MATCH_POLICY_VERSION = "semread-001b-match/2"
MATCH_POLICY = {
    "version": MATCH_POLICY_VERSION,
    "anchor": "candidate.target.region, yoksa candidate.source.region",
    "region_iou_threshold": 0.15,
    "centre_tolerance_norm": 0.05,
    "ambiguous_score_margin": 0.05,
    "ambiguous_policy": ("yakın puanlı rakip varsa kalem `ambiguous` sayılır ve semantik alan "
                         "puanlanmasına **girmez** (aday sırasına bağlı seçim yapılmaz)"),
    "localization_vs_semantic": ("`localization_match_rate` yalnız bölge eşleşmesini ölçer; alan "
                                 "doğruluğu `semantic_field_accuracy`, bağlama doğruluğu "
                                 "`target_binding_accuracy` ile ayrı raporlanır"),
    "extras_policy": ("gold `exhaustiveness` kapsamı içindeki eşleşmemiş aday `false_positive`; "
                      "kapsam dışındaki aday `unscorable_extra_candidate` (cezalanmaz)"),
    "numeric_relative": 0.02,
    "numeric_absolute": 0.05,
    "unit_normalisation": "in -> mm (25.4); birim bilinmiyorsa yalnız göreli karşılaştırma yapılmaz",
    "pairing": "bire bir; kopya aday recall'u artırmaz",
}

MM_PER_INCH = 25.4
FIELDS = ("representation", "physical", "form", "size", "count_printed", "termination", "depth",
          "target_binding")
# §11: bölge eşleşmesi ("yerelleştirme") ile alan doğruluğu aynı oranda raporlanmaz.
SEMANTIC_FIELDS = ("representation", "physical", "form", "size", "count_printed", "termination",
                   "depth")
BINDING_FIELD = "target_binding"
# §12: referansın hangi kapsamda eksiksiz olduğunu beyan ettiği kapalı küme.
EXHAUSTIVENESS_SCOPES = ("full_page", "regions", "predicates")


def _region(payload: dict | None) -> Region | None:
    """Bölge okuyucu: `{x0,y0,x1,y1}` ya da `[x0,y0,x1,y1]` (gold kısa biçimi liste yazabilir)."""
    if not payload:
        return None
    if isinstance(payload, (list, tuple)) and len(payload) == 4:
        payload = dict(zip(("x0", "y0", "x1", "y1"), payload))
    try:
        return Region(**{key: float(payload[key]) for key in ("x0", "y0", "x1", "y1")})
    except (KeyError, TypeError, ValueError):
        return None


def candidate_anchor(candidate: dict) -> Region | None:
    target = (candidate.get("target") or {}).get("region")
    return _region(target) or _region((candidate.get("source") or {}).get("region"))


def claim_region(claim: dict) -> Region | None:
    return _region((claim.get("target") or {}).get("region")) or _region(
        (claim.get("callout") or {}).get("region"))


def pair_score(claim: dict, candidate: dict, policy: dict | None = None) -> float:
    """Bölge ilişkisine dayanan eşleşme puanı; değer karşılaştırması **yok**."""
    policy = policy or MATCH_POLICY
    claim_box, candidate_box = claim_region(claim), candidate_anchor(candidate)
    if claim_box is None or candidate_box is None:
        return 0.0
    iou = claim_box.iou(candidate_box)
    (cx, cy), (dx, dy) = claim_box.centre(), candidate_box.centre()
    distance = ((cx - dx) ** 2 + (cy - dy) ** 2) ** 0.5
    if not regions_match(claim_box, candidate_box, iou_threshold=policy["region_iou_threshold"],
                         centre_tolerance=policy["centre_tolerance_norm"]):
        return 0.0
    return round(min(1.0, iou + max(0.0, policy["centre_tolerance_norm"] - distance)), 6)


def match_claims(claims: list[dict], candidates: list[dict],
                 policy: dict | None = None) -> dict:
    """Bire bir eşleştirme; belirsiz kalemler **dışlanır** (politika v2, PLAN-5 §10).

    İki belirsizlik türü de aday sırasından bağımsız tanımlanır:

    * `close_scores` — kalemin en iyi puanına `ambiguous_score_margin` içinde **birden çok** aday
      var: hangisinin kastedildiği belirsizdir, kalem puanlanmaz.
    * `candidate_contested` — aynı aday birden çok kalemin en iyi adayı: eşleştirme sırası sonucu
      değiştireceği için ikisi de puanlanmaz.

    Dışlanan kalem `pairs`e **girmez** (böylece semantik alan puanı üretilmez), `ambiguous_claims`
    altında sayılır ve rapora mekanik olarak geçer.
    """
    policy = policy or MATCH_POLICY
    margin = policy["ambiguous_score_margin"]
    scores: list[tuple[float, str, str]] = []
    for claim in claims:
        for candidate in candidates:
            score = pair_score(claim, candidate, policy)
            if score > 0:
                scores.append((score, claim["claim_id"], candidate.get("candidate_id", "?")))
    scores.sort(key=lambda row: (-row[0], row[1], row[2]))
    per_claim: dict[str, list[tuple[float, str]]] = {}
    per_candidate: dict[str, list[tuple[float, str]]] = {}
    for score, claim_id, candidate_id in scores:
        per_claim.setdefault(claim_id, []).append((score, candidate_id))
        per_candidate.setdefault(candidate_id, []).append((score, claim_id))

    ambiguous: list[dict] = []
    ambiguous_claims: set[str] = set()
    for claim_id in sorted(per_claim):
        rows = per_claim[claim_id]
        best = max(score for score, _ in rows)
        rivals = sorted(candidate_id for score, candidate_id in rows if best - score <= margin)
        if len(rivals) > 1:
            ambiguous_claims.add(claim_id)
            ambiguous.append({"claim_id": claim_id, "candidate_id": rivals[0], "score": round(best, 6),
                              "kind": "close_scores", "others": rivals[1:]})
    for candidate_id in sorted(per_candidate):
        rows = per_candidate[candidate_id]
        best = max(score for score, _ in rows)
        owners = sorted(claim_id for score, claim_id in rows if best - score <= margin)
        if len(owners) > 1:
            for claim_id in owners:
                if claim_id in ambiguous_claims:
                    continue
                ambiguous_claims.add(claim_id)
                ambiguous.append({"claim_id": claim_id, "candidate_id": candidate_id,
                                  "score": round(best, 6), "kind": "candidate_contested",
                                  "others": [other for other in owners if other != claim_id]})

    pairs: list[dict] = []
    used_candidates: set[str] = set()
    for claim_id in sorted(per_claim, key=lambda cid: (-max(row[0] for row in per_claim[cid]), cid)):
        if claim_id in ambiguous_claims:
            continue
        # Belirsizlik dışlandıktan sonra "kendi en iyi adayı kapılmış" durumu kalmaz: bir adayı
        # birden çok kalem en iyi adayı sayıyorsa hepsi dışlanır. Yedek arama yalnız savunma amaçlı.
        for score, candidate_id in sorted(per_claim[claim_id], key=lambda row: (-row[0], row[1])):
            if candidate_id in used_candidates:
                continue
            used_candidates.add(candidate_id)
            pairs.append({"claim_id": claim_id, "candidate_id": candidate_id,
                          "score": round(score, 6), "matching_status": "matched"})
            break
    pairs.sort(key=lambda row: (-row["score"], row["claim_id"], row["candidate_id"]))
    paired = {pair["claim_id"] for pair in pairs}
    unmatched_claims = [claim["claim_id"] for claim in claims
                        if claim["claim_id"] not in paired
                        and claim["claim_id"] not in ambiguous_claims]
    unmatched_candidates = [candidate.get("candidate_id", "?") for candidate in candidates
                            if candidate.get("candidate_id", "?") not in used_candidates]
    return {"pairs": pairs, "ambiguous": ambiguous, "ambiguous_claims": sorted(ambiguous_claims),
            "unmatched_claims": unmatched_claims, "unmatched_candidates": unmatched_candidates,
            "policy": policy["version"],
            "note": ("belirsiz kalemler semantik puanlanmaz; `pairs` yalnız kesin eşleşmeleri taşır")}


# ----------------------------------------------------------------- alan bazında puanlama


def _norm_value(value: float | None, unit: str | None) -> tuple[float | None, str]:
    if value is None:
        return None, "yok"
    if unit == "in":
        return value * MM_PER_INCH, "in->mm"
    return float(value), "mm"


def _num_verdict(expected: float | None, expected_unit: str | None, given: float | None,
                 given_unit: str | None, *, field: str) -> dict:
    if expected is None and given is None:
        return {"field": field, "verdict": "not_applicable", "note": "iki tarafta da yok"}
    if given is None:
        return {"field": field, "verdict": "omission", "expected": expected, "given": None}
    if expected is None:
        return {"field": field, "verdict": "false_claim", "expected": None, "given": given}
    expected_mm, expected_note = _norm_value(expected, expected_unit)
    given_mm, given_note = _norm_value(given, given_unit)
    if expected_mm is None or given_mm is None:
        return {"field": field, "verdict": "unreadable", "expected": expected, "given": given}
    tolerance = numeric_tolerance(expected_mm, relative=MATCH_POLICY["numeric_relative"],
                                  absolute=MATCH_POLICY["numeric_absolute"])
    expected_norm = (expected_unit or "mm")
    given_norm = (given_unit or expected_norm)
    if abs(given_mm - expected_mm) <= tolerance and expected_norm == given_norm:
        return {"field": field, "verdict": "correct", "expected": expected_mm, "given": given_mm,
                "tolerance": tolerance, "note": f"{expected_note}/{given_note}",
                "unit_expected": expected_unit, "unit_given": given_unit}
    if expected_norm != given_norm:
        # Birim uyuşmuyorsa bu **birim** hatasıdır; dönüştürülmüş değer tutuyorsa okuma doğrudur
        # (ör. 0.315 in = 8 mm) ve yalnız `unit_converted` notuyla doğru sayılır.
        if abs(given_mm - expected_mm) <= tolerance:
            return {"field": field, "verdict": "correct",
                    "expected": expected_mm, "given": given_mm, "tolerance": tolerance,
                    "note": f"unit_converted: {given} {given_unit} = {round(given_mm, 4)} mm",
                    "unit_expected": expected_unit, "unit_given": given_unit}
        return {"field": field, "verdict": "unit_error", "expected": expected_mm, "given": given_mm,
                "tolerance": tolerance, "note": f"{expected_note}/{given_note}",
                "unit_expected": expected_unit, "unit_given": given_unit}
    return {"field": field, "verdict": "value_error", "expected": expected_mm, "given": given_mm,
            "tolerance": tolerance, "unit_expected": expected_unit, "unit_given": given_unit}


def _categorical_verdict(field: str, expected: str | None, given: str | None, *,
                         unknown_token: str = "unknown", positive: list[str] | None = None) -> dict:
    positive = positive or []
    if expected is None:
        return {"field": field, "verdict": "not_applicable"}
    if given is None or given == unknown_token:
        return {"field": field, "verdict": "abstained", "expected": expected, "given": given}
    if given == expected:
        return {"field": field, "verdict": "correct", "expected": expected, "given": given}
    verdict = "overclaim" if expected in ("underdetermined", unknown_token) and given in positive \
        else "mismatch"
    return {"field": field, "verdict": verdict, "expected": expected, "given": given}


def score_pair(claim: dict, candidate: dict) -> list[dict]:
    """Bir eşleşmiş çift için alan bazında karar. `target_binding` bölgeden ölçülür."""
    rows: list[dict] = []
    rows.append(_categorical_verdict("representation", claim["representation"],
                                     (candidate.get("representation") or {}).get("kind"),
                                     positive=["circle", "arc"]))
    rows.append(_categorical_verdict("physical", claim["physical"],
                                     (candidate.get("physical") or {}).get("kind"),
                                     positive=["hole", "pocket", "slot"]))
    rows.append(_categorical_verdict("form", claim["form"],
                                     (candidate.get("form") or {}).get("symbol")))
    size = candidate.get("size") or {}
    rows.append(_num_verdict(claim["size"], claim.get("unit", "mm"), size.get("value"),
                             size.get("unit") if size.get("state") == "known" else None,
                             field="size"))
    count = candidate.get("count") or {}
    rows.append(_num_verdict(claim.get("count_printed"), "adet",
                             count.get("printed") if count.get("state") == "known" else None, "adet",
                             field="count_printed"))
    rows.append(_categorical_verdict("termination", claim["termination"],
                                     (candidate.get("termination") or {}).get("kind")))
    depth = candidate.get("depth") or {}
    rows.append(_num_verdict(claim.get("depth"), claim.get("unit", "mm"), depth.get("value"),
                             depth.get("unit") if depth.get("state") == "known" else None,
                             field="depth"))
    claim_box, candidate_box = claim_region(claim), candidate_anchor(candidate)
    binding_ok = bool(claim_box and candidate_box and regions_match(
        claim_box, candidate_box, iou_threshold=MATCH_POLICY["region_iou_threshold"],
        centre_tolerance=MATCH_POLICY["centre_tolerance_norm"]))
    rows.append({"field": "target_binding", "verdict": "correct" if binding_ok else "binding_error"})
    return rows


def exhaustive_scope(reference: dict) -> dict:
    """Gold'un **hangi kapsamda eksiksiz** olduğunu okur (PLAN-5 §12).

    Dönen: `{"scope": ..., "full_page": bool, "regions": [Region, ...]}`. Bilinmeyen ya da yer
    tutucu kapsam `None`'dır ve **hiçbir** fazla aday cezalanmaz: gold kapsamadığı yeri suçlayamaz.
    """
    raw = reference.get("exhaustiveness")
    if not isinstance(raw, dict) or raw.get("scope") not in EXHAUSTIVENESS_SCOPES:
        return {"scope": None, "full_page": False, "regions": [],
                "note": "exhaustiveness beyanı yok/yer tutucu: fazla adaylar cezalanmaz"}
    scope = raw["scope"]
    boxes: list[Region] = []
    if scope == "regions":
        boxes = [region for region in (_region(box) for box in (raw.get("regions") or []))
                 if region is not None]
    elif scope == "predicates":
        for claim in reference.get("claims") or []:
            if claim.get("representation") in (raw.get("predicates") or []):
                box = claim_region(claim)
                if box is not None:
                    boxes.append(box)
    return {"scope": scope, "full_page": scope == "full_page", "regions": boxes,
            "predicates": list(raw.get("predicates") or []), "note": None}


def _within(box: Region | None, boxes: list[Region]) -> bool:
    return bool(box is not None and any(regions_match(box, other) for other in boxes))


def evaluate_page(reference: dict, arm: dict, policy: dict | None = None) -> dict:
    """Bir sayfanın bir kol için puanı: eşleşmeler, alan kararları, sayımlar.

    Belirsiz kalemler (`matching_status="ambiguous"`) **puanlanmaz**: alan kararları `not_scored`
    olur ve `_field_ok` bunları `None` sayar, böylece kurtarma/geriye gitme sayılarına girmezler.
    """
    policy = policy or MATCH_POLICY
    claims = reference.get("claims") or []
    candidates = (arm.get("response") or {}).get("items") or []
    matching = match_claims(claims, candidates, policy)
    ambiguous_ids = set(matching.get("ambiguous_claims") or [])
    by_candidate = {candidate.get("candidate_id"): candidate for candidate in candidates}
    by_claim = {claim["claim_id"]: claim for claim in claims}
    field_rows: list[dict] = []
    per_claim: dict[str, dict] = {}
    for pair in matching["pairs"]:
        claim, candidate = by_claim[pair["claim_id"]], by_candidate[pair["candidate_id"]]
        rows = score_pair(claim, candidate)
        per_claim[pair["claim_id"]] = {"matched": True, "matching_status": "matched",
                                       "candidate_id": pair["candidate_id"],
                                       "fields": {row["field"]: row["verdict"] for row in rows},
                                       "rows": rows, "score": pair["score"]}
        field_rows += [{**row, "claim_id": pair["claim_id"], "candidate_id": pair["candidate_id"]}
                       for row in rows]
    for claim_id in matching["unmatched_claims"]:
        per_claim[claim_id] = {"matched": False, "matching_status": "unmatched",
                               "fields": {field: "not_produced" for field in FIELDS}}
    for claim_id in sorted(ambiguous_ids):
        per_claim[claim_id] = {"matched": False, "matching_status": "ambiguous",
                               "fields": {field: "not_scored" for field in FIELDS},
                               "reason": "belirsiz eşleşme: semantik puanlama yapılmaz (PLAN-5 §10)"}
    scope = exhaustive_scope(reference)
    extras = []
    for candidate_id in matching["unmatched_candidates"]:
        box = candidate_anchor(by_candidate.get(candidate_id) or {})
        scorable = scope["full_page"] or _within(box, scope["regions"])
        extras.append({"candidate_id": candidate_id, "anchor": box.as_list() if box else None,
                       "kind": "false_positive" if scorable else "unscorable_extra_candidate"})
    summary = {"fields": {}, "claims": len(claims), "candidates": len(candidates),
               "matched": len(matching["pairs"]),
               "unmatched_claims": len(matching["unmatched_claims"]),
               "unmatched_candidates": len(matching["unmatched_candidates"]),
               "ambiguous": len(matching["ambiguous"]),
               "ambiguous_claims": len(ambiguous_ids),
               "false_positive_candidates": sum(1 for row in extras
                                                if row["kind"] == "false_positive"),
               "unscorable_extra_candidates": sum(1 for row in extras
                                                  if row["kind"] == "unscorable_extra_candidate"),
               "exhaustiveness": scope["scope"]}
    for field in FIELDS:
        rows = [row for row in field_rows if row["field"] == field]
        verdicts: dict[str, int] = {}
        for row in rows:
            verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
        summary["fields"][field] = verdicts
    return {"matching": matching, "per_claim": per_claim, "field_rows": field_rows,
            "extras": extras, "exhaustiveness": scope, "summary": summary,
            "policy": policy["version"]}


# ----------------------------------------------------------------- toplama ve karşılaştırma


def _ratio(numerator: int, denominator: int) -> float | None:
    """Payda sıfırsa `None` (not_applicable): tanımsız oran üretilmez."""
    return None if denominator == 0 else round(numerator / denominator, 4)


def aggregate(pages: list[dict]) -> dict:
    """Birden çok sayfanın toplamı: alan bazında TP/FP/FN ve **ayrık** oranlar (PLAN-5 §11).

    `localization_match_rate` yalnız bölge eşleşmesidir; alan doğruluğu `semantic_field_accuracy`
    (yüklem alanları) ve `target_binding_accuracy` (bağlama) olarak ayrı verilir. Eski
    `candidate_precision`/`claim_recall` adları rapor uyumu için korunur ama bunlar yerelleştirme
    ağırlıklıdır — semantik doğruluk kanıtı değildir.
    """
    totals: dict[str, dict[str, int]] = {field: {} for field in FIELDS}
    claims = candidates = matched = ambiguous = 0
    ambiguous_claims = false_positive = unscorable = 0
    for page in pages:
        summary = page["summary"]
        claims += summary["claims"]
        candidates += summary["candidates"]
        matched += summary["matched"]
        ambiguous += summary["ambiguous"]
        ambiguous_claims += summary.get("ambiguous_claims", 0)
        false_positive += summary.get("false_positive_candidates", 0)
        unscorable += summary.get("unscorable_extra_candidates", 0)
        for field, verdicts in summary["fields"].items():
            for verdict, count in verdicts.items():
                totals[field][verdict] = totals[field].get(verdict, 0) + count
    fields: dict[str, Any] = {}
    for field, verdicts in totals.items():
        correct = verdicts.get("correct", 0)
        wrong = (verdicts.get("mismatch", 0) + verdicts.get("value_error", 0)
                 + verdicts.get("unit_error", 0) + verdicts.get("overclaim", 0)
                 + verdicts.get("false_claim", 0))
        abstained = verdicts.get("abstained", 0) + verdicts.get("omission", 0) \
            + verdicts.get("not_produced", 0)
        scorable = correct + wrong + abstained
        fields[field] = {
            "verdicts": verdicts,
            "correct": correct, "wrong": wrong, "abstained": abstained,
            "scorable": scorable,
            "accuracy": _ratio(correct, scorable),
            "abstention_rate": _ratio(abstained, scorable),
            "wrong_rate": _ratio(wrong, scorable),
            "unscored": verdicts.get("not_scored", 0),
        }
    semantic_correct = sum(fields[field]["correct"] for field in SEMANTIC_FIELDS)
    semantic_scorable = sum(fields[field]["scorable"] for field in SEMANTIC_FIELDS)
    semantic_wrong = sum(fields[field]["wrong"] for field in SEMANTIC_FIELDS)
    semantic_overclaim = sum(fields[field]["verdicts"].get("overclaim", 0)
                             + fields[field]["verdicts"].get("false_claim", 0)
                             for field in SEMANTIC_FIELDS)
    semantic_abstained = sum(fields[field]["abstained"] for field in SEMANTIC_FIELDS)
    binding = fields[BINDING_FIELD]
    return {
        "claims": claims, "candidates": candidates, "matched": matched,
        # Yerelleştirme (bölge) — semantik doğruluk değildir.
        "localization_match_rate": _ratio(matched, claims),
        "candidate_localization_precision": _ratio(matched, candidates),
        "candidate_precision": _ratio(matched, candidates),
        "claim_recall": _ratio(matched, claims),
        "omission": claims - matched,
        "omission_rate": _ratio(claims - matched, claims),
        # Alan doğruluğu (yüklemler) ve bağlama — ayrı ölçülür.
        "semantic_field_accuracy": _ratio(semantic_correct, semantic_scorable),
        "semantic_scorable_fields": semantic_scorable,
        "target_binding_accuracy": binding["accuracy"],
        "candidate_overclaim_rate": _ratio(semantic_overclaim, semantic_scorable),
        "candidate_abstention_rate": _ratio(semantic_abstained, semantic_scorable),
        "candidate_wrong_rate": _ratio(semantic_wrong, semantic_scorable),
        "ambiguous_pairs": ambiguous,
        "ambiguous_claim_count": ambiguous_claims,
        "false_positive_candidate_count": false_positive,
        "unscorable_extra_candidate_count": unscorable,
        "fields": fields,
        "metric_note": ("`candidate_precision`/`claim_recall` yerelleştirme ağırlıklıdır: bölge "
                        "eşleşmesi doğru olsa da R/Ø, değer, bitiş, sayı ve fiziksel yorum yanlış "
                        "olabilir — onlar `semantic_field_accuracy` ve alan satırlarındadır"),
    }


def _field_ok(per_claim: dict, claim_id: str, field: str) -> bool | None:
    """Alan kararı: `True` doğru, `False` yanlış/eksik, `None` **puanlanamaz** (PLAN-5 §9/§10).

    `None` dönen hâller karşılaştırmanın paydasına **girmez**: belirsiz eşleşme (politika gereği
    puanlanmaz) ve kayıtsız kalem. Eşleşmemiş kalem yanlış değil **eksik** cevaptır.
    """
    record = per_claim.get(claim_id)
    if not record:
        return None
    if not record.get("matched"):
        return None if record.get("matching_status") == "ambiguous" else False
    verdict = (record.get("fields") or {}).get(field)
    if verdict is None or verdict == "not_scored":
        return None
    return verdict in ("correct", "not_applicable")


def _predicate_row(per_page: dict[str, dict], arm: str, field: str) -> dict:
    """Tek bir yüklem (alan) için kurtarma/geriye gitme satırı (PLAN-5 §9)."""
    recovered = regressed_wrong = regressed_abstained = 0
    scorable = 0
    examples: list[dict] = []
    for page_id, arms in per_page.items():
        d_claims = (arms.get("D") or {}).get("per_claim") or {}
        arm_claims = (arms.get(arm) or {}).get("per_claim") or {}
        for claim_id in d_claims:
            arm_record = arm_claims.get(claim_id)
            if arm_record is None:
                continue
            d_ok = _field_ok(d_claims, claim_id, field)
            arm_ok = _field_ok(arm_claims, claim_id, field)
            if d_ok is None or arm_ok is None:
                continue
            scorable += 1
            kind: str | None = None
            if not d_ok and arm_ok:
                recovered += 1
                kind = "recovered"
            elif d_ok and not arm_ok:
                if arm_record.get("matched"):
                    regressed_wrong += 1
                    kind = "regressed_wrong_candidate"
                else:
                    regressed_abstained += 1
                    kind = "regressed_abstention"
            if kind:
                examples.append({"page_id": page_id, "claim_id": claim_id, "kind": kind})
    return {"predicate": field, "scorable_target_count": scorable, "recovered_count": recovered,
            "regressed_wrong_count": regressed_wrong,
            "regressed_abstention_count": regressed_abstained,
            "net_correct_gain": recovered - regressed_wrong - regressed_abstained,
            "examples": examples}


def compare_arms(per_page: dict[str, dict]) -> dict:
    """Aynı gold claim'ler üzerinde V/VE vs D: **yüklem bazında** recovery/regression (PLAN-5 §9).

    Her yüklem için scorable/kurtarılan/geriye giden sayıları ve `net_correct_gain` ayrı satırdır;
    toplamlar yüklem satırlarının toplamıdır (aynı kalem birden çok yüklemde sayılabilir). Paydalar
    farklı olduğu için `recovery_rate > regression_rate` **karar kuralı değildir**.

    `per_page`: `{"<page_id>": {"D": evaluate_page sonucu, "V": ..., "VE": ...}}`.
    """
    result: dict[str, Any] = {"vs_d": {}, "ve_vs_v": {}, "predicates": list(FIELDS),
                              "totals_note": ("toplamlar yüklem satırlarının toplamıdır; aynı kalem "
                                              "birden çok yüklemde sayılabilir"),
                              "notes": []}
    for arm in ("V", "VE"):
        rows = [_predicate_row(per_page, arm, field) for field in FIELDS]
        totals = {
            "scorable_target_count": sum(row["scorable_target_count"] for row in rows),
            "recovered_count": sum(row["recovered_count"] for row in rows),
            "regressed_wrong_count": sum(row["regressed_wrong_count"] for row in rows),
            "regressed_abstention_count": sum(row["regressed_abstention_count"] for row in rows),
        }
        totals["net_correct_gain"] = (totals["recovered_count"] - totals["regressed_wrong_count"]
                                      - totals["regressed_abstention_count"])
        result["vs_d"][arm] = {
            **totals,
            "predicate_rows": rows,
            # Geriye dönük adlar (rapor/uyum): eski anahtarlar korunur.
            "recovered": totals["recovered_count"],
            "regressed_wrong_candidate": totals["regressed_wrong_count"],
            "regressed_abstention": totals["regressed_abstention_count"],
            "regressed_total": (totals["regressed_wrong_count"]
                                + totals["regressed_abstention_count"]),
            "d_scorable": totals["scorable_target_count"],
            "arm_scorable": totals["scorable_target_count"],
            "rows": [example for row in rows for example in row["examples"]],
            "note": ("her yüklem ayrı satırdır; oranların paydaları farklı olduğu için oran "
                     "karşılaştırması tek başına fayda kanıtı değildir (PLAN-5 §9)"),
        }
    # VE vs V: aynı sayfada aynı claim'in **her yüklemdeki** farkı (bilgi kaynağı bağımsız değildir).
    per_predicate: list[dict] = []
    for field in FIELDS:
        ve_better = ve_worse = 0
        for _page_id, arms in per_page.items():
            v_claims = (arms.get("V") or {}).get("per_claim") or {}
            ve_claims = (arms.get("VE") or {}).get("per_claim") or {}
            for claim_id in set(v_claims) & set(ve_claims):
                v_ok = _field_ok(v_claims, claim_id, field)
                ve_ok = _field_ok(ve_claims, claim_id, field)
                if v_ok is None or ve_ok is None:
                    continue
                if ve_ok and not v_ok:
                    ve_better += 1
                elif v_ok and not ve_ok:
                    ve_worse += 1
        per_predicate.append({"predicate": field, "ve_better": ve_better, "ve_worse": ve_worse,
                              "net_difference": ve_better - ve_worse})
    result["ve_vs_v"] = {
        "ve_better": sum(row["ve_better"] for row in per_predicate),
        "ve_worse": sum(row["ve_worse"] for row in per_predicate),
        "per_predicate": per_predicate,
    }
    result["ve_vs_v"]["net"] = result["ve_vs_v"]["ve_better"] - result["ve_vs_v"]["ve_worse"]
    result["notes"].append("D ile VE bağımsız kanıt kaynakları değildir: VE'nin gözlem tablosu aynı "
                           "deterministic hattan gelir.")
    return result


__all__ = ["BINDING_FIELD", "EXHAUSTIVENESS_SCOPES", "FIELDS", "MATCH_POLICY", "MATCH_POLICY_VERSION",
           "MM_PER_INCH", "SEMANTIC_FIELDS", "aggregate", "candidate_anchor", "claim_region",
           "compare_arms", "evaluate_page", "exhaustive_scope", "match_claims", "pair_score",
           "score_pair"]
