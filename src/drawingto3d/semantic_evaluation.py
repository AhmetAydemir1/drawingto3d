"""SEMREAD-001B — eşleştirme ve metrikler (D/V/VE aynı hedef evreni ve kurallarıyla).

Üç ilke (goal §5):

1. **Eşleştirme bölge/kaynak ilişkisine dayanır**, beklenen sayısal değere bakmaz. Değerle
   eşleştirme yapmak, doğru cevabı bilen bir hakemin adayı seçmesi demekti.
2. **Eşleşmeler bire birdir**; kopya adaylar recall'u şişirmez. Eşit derecede iyi iki eşleşme
   "belirsiz" olarak raporlanır, iki kez sayılmaz.
3. **Payda sıfırsa oran `null`** (not_applicable); tanımsız bölme yapılmaz.

Eşleştirme, tolerans, birim normalizasyonu ve belirsizlik politikası **final tahminlerden önce**
sabitlenir: `MATCH_POLICY` sürümlenir ve rapora aynen yazılır.
"""

from __future__ import annotations

from typing import Any

from drawingto3d.semantic_candidates import (Region, numeric_tolerance, regions_match)

MATCH_POLICY_VERSION = "semread-001b-match/1"
MATCH_POLICY = {
    "version": MATCH_POLICY_VERSION,
    "anchor": "candidate.target.region, yoksa candidate.source.region",
    "region_iou_threshold": 0.15,
    "centre_tolerance_norm": 0.05,
    "ambiguous_score_margin": 0.05,
    "numeric_relative": 0.02,
    "numeric_absolute": 0.05,
    "unit_normalisation": "in -> mm (25.4); birim bilinmiyorsa yalnız göreli karşılaştırma yapılmaz",
    "pairing": "bire bir; kopya aday recall'u artırmaz",
}

MM_PER_INCH = 25.4
FIELDS = ("representation", "physical", "form", "size", "count_printed", "termination", "depth",
          "target_binding")


def _region(payload: dict | None) -> Region | None:
    if not payload:
        return None
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
    """Bire bir eşleştirme (açgözlü, deterministik). Kopya adaylar recall'u artırmaz."""
    policy = policy or MATCH_POLICY
    scores: list[tuple[float, str, str]] = []
    for claim in claims:
        for candidate in candidates:
            score = pair_score(claim, candidate, policy)
            if score > 0:
                scores.append((score, claim["claim_id"], candidate.get("candidate_id", "?")))
    scores.sort(key=lambda row: (-row[0], row[1], row[2]))
    pairs: list[dict] = []
    used_claims: set[str] = set()
    used_candidates: set[str] = set()
    ambiguous: list[dict] = []
    for score, claim_id, candidate_id in scores:
        if claim_id in used_claims or candidate_id in used_candidates:
            # Aynı aday/kalem başka bir eşleşmeye gitti: bu bir "belirsiz" sinyaldir, yeni eşleşme değil.
            if claim_id not in used_claims:
                ambiguous.append({"claim_id": claim_id, "candidate_id": candidate_id,
                                  "score": score, "kind": "candidate_taken"})
            continue
        near = [row for row in scores
                if row[1] == claim_id and row[2] != candidate_id and abs(row[0] - score)
                <= policy["ambiguous_score_margin"] and row[2] not in used_candidates]
        used_claims.add(claim_id)
        used_candidates.add(candidate_id)
        pairs.append({"claim_id": claim_id, "candidate_id": candidate_id, "score": score,
                      "ambiguous_with": [row[2] for row in near]})
        if near:
            ambiguous.append({"claim_id": claim_id, "candidate_id": candidate_id, "score": score,
                              "kind": "close_scores", "others": [row[2] for row in near]})
    unmatched_claims = [claim["claim_id"] for claim in claims if claim["claim_id"] not in used_claims]
    unmatched_candidates = [candidate.get("candidate_id", "?") for candidate in candidates
                            if candidate.get("candidate_id", "?") not in used_candidates]
    return {"pairs": pairs, "ambiguous": ambiguous, "unmatched_claims": unmatched_claims,
            "unmatched_candidates": unmatched_candidates, "policy": policy["version"]}


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


def evaluate_page(reference: dict, arm: dict, policy: dict | None = None) -> dict:
    """Bir sayfanın bir kol için puanı: eşleşmeler, alan kararları, sayımlar."""
    policy = policy or MATCH_POLICY
    claims = reference.get("claims") or []
    candidates = (arm.get("response") or {}).get("items") or []
    matching = match_claims(claims, candidates, policy)
    by_candidate = {candidate.get("candidate_id"): candidate for candidate in candidates}
    by_claim = {claim["claim_id"]: claim for claim in claims}
    field_rows: list[dict] = []
    per_claim: dict[str, dict] = {}
    for pair in matching["pairs"]:
        claim, candidate = by_claim[pair["claim_id"]], by_candidate[pair["candidate_id"]]
        rows = score_pair(claim, candidate)
        per_claim[pair["claim_id"]] = {"matched": True, "candidate_id": pair["candidate_id"],
                                       "fields": {row["field"]: row["verdict"] for row in rows},
                                       "rows": rows, "score": pair["score"]}
        field_rows += [{**row, "claim_id": pair["claim_id"], "candidate_id": pair["candidate_id"]}
                       for row in rows]
    for claim_id in matching["unmatched_claims"]:
        claim = by_claim[claim_id]
        per_claim[claim_id] = {"matched": False,
                               "fields": {field: "not_produced" for field in FIELDS}}
    summary = {"fields": {}, "claims": len(claims), "candidates": len(candidates),
               "matched": len(matching["pairs"]),
               "unmatched_claims": len(matching["unmatched_claims"]),
               "unmatched_candidates": len(matching["unmatched_candidates"]),
               "ambiguous": len(matching["ambiguous"])}
    for field in FIELDS:
        rows = [row for row in field_rows if row["field"] == field]
        verdicts: dict[str, int] = {}
        for row in rows:
            verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
        summary["fields"][field] = verdicts
    return {"matching": matching, "per_claim": per_claim, "field_rows": field_rows,
            "summary": summary, "policy": policy["version"]}


# ----------------------------------------------------------------- toplama ve karşılaştırma


def _ratio(numerator: int, denominator: int) -> float | None:
    """Payda sıfırsa `None` (not_applicable): tanımsız oran üretilmez."""
    return None if denominator == 0 else round(numerator / denominator, 4)


def aggregate(pages: list[dict]) -> dict:
    """Birden çok sayfanın toplamı: alan bazında TP/FP/FN ve oranlar."""
    totals: dict[str, dict[str, int]] = {field: {} for field in FIELDS}
    claims = candidates = matched = ambiguous = 0
    for page in pages:
        summary = page["summary"]
        claims += summary["claims"]
        candidates += summary["candidates"]
        matched += summary["matched"]
        ambiguous += summary["ambiguous"]
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
        }
    return {
        "claims": claims, "candidates": candidates, "matched": matched,
        "candidate_precision": _ratio(matched, candidates),
        "claim_recall": _ratio(matched, claims),
        "omission": claims - matched,
        "omission_rate": _ratio(claims - matched, claims),
        "ambiguous_pairs": ambiguous,
        "fields": fields,
    }


def _field_ok(per_claim: dict, claim_id: str, field: str) -> bool | None:
    record = per_claim.get(claim_id)
    if not record or not record.get("matched"):
        return False if record else None
    verdict = (record.get("fields") or {}).get(field)
    if verdict is None:
        return None
    return verdict in ("correct", "not_applicable")


def compare_arms(per_page: dict[str, dict]) -> dict:
    """Aynı gold claim'ler üzerinde V/VE vs D recovery/regression; VE vs V farkı.

    `per_page`: `{"<page_id>": {"D": evaluate_page sonucu, "V": ..., "VE": ...}}`.
    """
    result: dict[str, Any] = {"vs_d": {}, "ve_vs_v": {}, "notes": []}
    for arm in ("V", "VE"):
        recovered = regressed_wrong = regressed_abstained = 0
        gain_rows: list[dict] = []
        d_scorable = arm_scorable = 0
        for page_id, arms in per_page.items():
            d_claims = (arms.get("D") or {}).get("per_claim") or {}
            arm_claims = (arms.get(arm) or {}).get("per_claim") or {}
            for claim_id, d_record in d_claims.items():
                arm_record = arm_claims.get(claim_id)
                if arm_record is None:
                    continue
                d_ok = _field_ok(d_claims, claim_id, "size")
                arm_ok = _field_ok(arm_claims, claim_id, "size")
                if d_ok is None or arm_ok is None:
                    continue
                d_scorable += 1
                arm_scorable += 1
                if d_ok is False and arm_ok is True:
                    recovered += 1
                    gain_rows.append({"page_id": page_id, "claim_id": claim_id, "kind": "recovered"})
                elif d_ok is True and arm_ok is False:
                    if arm_record.get("matched"):
                        regressed_wrong += 1
                        kind = "regressed_wrong_candidate"
                    else:
                        regressed_abstained += 1
                        kind = "regressed_abstention"
                    gain_rows.append({"page_id": page_id, "claim_id": claim_id, "kind": kind})
        result["vs_d"][arm] = {
            "recovered": recovered, "regressed_wrong_candidate": regressed_wrong,
            "regressed_abstention": regressed_abstained,
            "regressed_total": regressed_wrong + regressed_abstained,
            "net_correct_gain": recovered - (regressed_wrong + regressed_abstained),
            "d_scorable": d_scorable, "arm_scorable": arm_scorable,
            "recovery_rate": _ratio(recovered, d_scorable),
            "regression_rate": _ratio(regressed_wrong + regressed_abstained, arm_scorable),
            "rows": gain_rows,
            "note": ("oranların paydaları farklı olabilir; 'recovery > regression' tek başına fayda "
                     "kanıtı değildir"),
        }
    # VE vs V: aynı sayfada aynı claim'in size alanındaki fark (bilgi kaynağı bağımsız değildir).
    ve_better = ve_worse = 0
    for _page_id, arms in per_page.items():
        v_claims = (arms.get("V") or {}).get("per_claim") or {}
        ve_claims = (arms.get("VE") or {}).get("per_claim") or {}
        for claim_id in set(v_claims) & set(ve_claims):
            v_ok = _field_ok(v_claims, claim_id, "size")
            ve_ok = _field_ok(ve_claims, claim_id, "size")
            if v_ok is None or ve_ok is None:
                continue
            if ve_ok and not v_ok:
                ve_better += 1
            elif v_ok and not ve_ok:
                ve_worse += 1
    result["ve_vs_v"] = {"ve_better": ve_better, "ve_worse": ve_worse,
                         "net": ve_better - ve_worse}
    result["notes"].append("D ile VE bağımsız kanıt kaynakları değildir: VE'nin gözlem tablosu aynı "
                           "deterministic hattan gelir.")
    return result


__all__ = ["FIELDS", "MATCH_POLICY", "MATCH_POLICY_VERSION", "MM_PER_INCH", "aggregate",
           "candidate_anchor", "claim_region", "compare_arms", "evaluate_page", "match_claims",
           "pair_score", "score_pair"]
