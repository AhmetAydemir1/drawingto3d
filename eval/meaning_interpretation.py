"""Bind ONE printed measurement per call to the drawing's own ids; measure against the label.

No numeric derivation is asked for. For every measurement the raw request is written before the
call and the raw answer after it. Kind, axis and source binding are compared with an independent
relation label when one exists; the label is never an input to the model. Unresolved bindings stay
questions. Correct interpretation and ambiguity are reported separately — neither proves a STEP.

    PYTHONPATH=src .venv/bin/python eval/meaning_interpretation.py --label meaning-3b-01 --dry-run
    PYTHONPATH=src .venv/bin/python eval/meaning_interpretation.py --label meaning-3b-01
    PYTHONPATH=src .venv/bin/python eval/meaning_interpretation.py --check out/meaning-interpretation/meaning-3b-01/evidence.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.catalog import build_catalog
from drawingto3d.interpret import (
    INTERPRETATION_VERSION,
    JUDGE_VERSION,
    REPLY_VERSION,
    REVIEW_VERSION,
    corrupt_proposal,
    geometry_ids,
    interpret_measurement,
    interpret_prompt,
    judge_interpretation,
    NEEDS_MATCHED,
    measured_sizes,
    measurement_context,
    reading_proposal,
    reply_schema,
    review_injects_a_defect,
)
from drawingto3d.llama import ChatSettings, OllamaChat, find_model, installed_models
from drawingto3d.meaning import ABSOLUTE_TOLERANCE_MM, RELATIVE_TOLERANCE
from drawingto3d.planner import chain_evidence, suggested_names
from drawingto3d.proposal import read_sheet
from model_baseline import CASES_FILE, ResourceSampler, _atomic_json, code_record, manifest_record

LABELS = ROOT / "eval" / "relations"
POSITION_TOLERANCE_MM = 2.0


def label_rows(case_id: str) -> dict:
    path = LABELS / f"{case_id}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def pair_label_with_reading(evidence: dict, label: dict) -> dict:
    """Pair a label row with the measured span that carries the same printed value and unit.

    Value alone cannot pair the rows a drawing repeats: on the third sheet four rows print 20 and two print 40,
    so those label rows stayed unpaired although both sides had been measured. The reading publishes the kind
    it classified for each span (the Ø/R prefix it read), so a row is paired when value, unit *and* kind single
    it out, and only value+unit is used as the fallback. A value repeated with the same kind is still refused:
    the label stays unpaired rather than guessed onto one of the candidates.
    """
    pairs: dict[str, str] = {}
    for row in label.get("printed") or []:
        candidates = [printed for printed in evidence.get("printed") or []
                      if printed.get("unit") == row.get("unit")
                      and isinstance(printed.get("value"), (int, float))
                      and abs(printed["value"] - row["value"]) < 1e-6]
        if row.get("kind"):
            # An unstated kind is not evidence: the criterion applies only when both sides name one.
            typed = [printed for printed in candidates if printed.get("kind") == row["kind"]]
            if len(typed) == 1:
                pairs[row["span_id"]] = typed[0]["span_id"]
                continue
        if len(candidates) == 1:
            pairs[row["span_id"]] = candidates[0]["span_id"]
    return pairs


def _nearest_measured_id(measured: dict, point: list) -> tuple[str | None, float]:
    best, distance = None, math.inf
    for geometry_id, entry in measured.items():
        centre = entry.get("centre_mm") or (entry.get("points_mm") or [None])[0]
        if not isinstance(centre, list) or len(centre) != 2:
            continue
        current = math.dist(centre, point)
        if current < distance:
            best, distance = geometry_id, current
    return best, distance


def _unique_by_diameter(sizes: dict, diameter_mm) -> str | None:
    """The measured id whose measured size is the label's, when exactly one is that size.

    A size is an identity of its own. The position path needs the label and the reading to share a
    frame; a diameter does not. Measured on the third sheet: every label position sits 12–34 mm from its
    measured counterpart (the label carries STEP coordinates, the reading reports sheet frames), so
    binding scoring was off for all 17 measurements there while the plate (nominal values coincide
    within 0,4 mm) kept 5 of 8. Tolerance is the reading's own (%3 relative or 0,15 mm, whichever is
    larger) and the mapping is refused unless exactly one measured id is that size — on that sheet the
    Ø40 label meets two arcs of the same radius and is therefore left unmapped, as it should be.
    """
    if not isinstance(diameter_mm, (int, float)):
        return None
    tolerance = max(RELATIVE_TOLERANCE * diameter_mm, ABSOLUTE_TOLERANCE_MM)
    hits = [geometry_id for geometry_id, size in sizes.items()
            if abs(size - diameter_mm) <= tolerance]
    return hits[0] if len(hits) == 1 else None


def expected_for_measurement(evidence: dict, label: dict, span_id: str, pairs: dict) -> dict:
    """What the independent label says about this measurement, in the reading's own id space."""
    label_span = next((key for key, value in pairs.items() if value == span_id), None)
    if label_span is None:
        return {}
    claim = next((row for row in label.get("claims") or [] if row.get("span_id") == label_span), None)
    if claim is None:
        return {}
    circles = {circle["id"]: circle for circle in (label.get("geometry") or {}).get("circles") or []}
    measured = geometry_ids(evidence)
    sizes = measured_sizes(evidence)
    reading_claim = next((row for row in evidence.get("claims") or [] if row.get("span_id") == span_id), None) or {}
    reading_value = reading_claim.get("drawn_mm")
    label_value = claim.get("verified_mm")
    mapping, basis, unmapped = {}, {}, []
    for label_id in list(claim.get("between") or []) + list(claim.get("matched_geometry") or []):
        if label_id in mapping:
            continue
        circle = circles.get(label_id) or {}
        point = circle.get("centre_mm")
        if isinstance(point, list) and len(point) == 2:
            geometry_id, distance = _nearest_measured_id(measured, point)
            if geometry_id is not None and distance <= POSITION_TOLERANCE_MM:
                mapping[label_id] = geometry_id
                basis[label_id] = "position"
                continue
        # Second path: a verified diameter identifies the geometry when the frames disagree.
        geometry_id = _unique_by_diameter(sizes, circle.get("diameter_mm"))
        if geometry_id is not None:
            mapping[label_id] = geometry_id
            basis[label_id] = "diameter"
            continue
        unmapped.append(label_id)
    # Third path: the label's own number, checked against the reading's measurement of this callout. Where
    # the two independent numbers agree, the label has earned the reading's own anchors as the expectation —
    # so the model is scored against the reading on a row the reading itself is confirmed on, and neither
    # frame has to agree (the label's faces live in the part frame, the reading's ids in the sheet frame).
    from_the_reading: list[str] = []
    if unmapped and reading_value is not None and label_value is not None:
        limit = max(RELATIVE_TOLERANCE * abs(label_value), ABSOLUTE_TOLERANCE_MM)
        if abs(reading_value - label_value) <= limit:
            anchors = [anchor.get("geometry_id") for anchor in reading_claim.get("anchors") or []]
            own_ids = list(reading_claim.get("matched_geometry") or []) or anchors
            named = list(claim.get("between") or [])
            if claim.get("form") in NEEDS_MATCHED:
                # A size callout: the reading's own match for it is the expectation, even when one label name
                # covers two reading ids (a boss drawn as two arcs), so the mapping stays one-to-one only
                # where the names and the ids line up.
                if own_ids:
                    from_the_reading = own_ids
                    basis.update({name: "value" for name in unmapped})
                    unmapped = []
            elif len(named) == len(anchors) and unmapped == named and anchors:
                mapping.update(dict(zip(named, anchors)))
                basis.update({name: "value" for name in named})
                unmapped = []
    expected = {
        "label_span_id": label_span, "form": claim.get("form"), "measures": claim.get("measures"),
        "label_between": claim.get("between") or [], "label_matched": claim.get("matched_geometry") or [],
        "reading_id_mapping": mapping, "mapping_basis": basis, "unmapped_label_ids": unmapped,
    }
    if claim.get("between") and len(claim["between"]) == 2:
        centres = [circles.get(key, {}).get("centre_mm") for key in claim["between"]]
        if all(isinstance(centre, list) and len(centre) == 2 for centre in centres):
            (x1, y1), (x2, y2) = centres
            expected["axis"] = "horizontal" if abs(x2 - x1) >= abs(y2 - y1) else "vertical"
    ids = from_the_reading or [mapping[key] for key in (claim.get("between") or claim.get("matched_geometry") or [])
                             if key in mapping]
    complete = (not unmapped) and bool(ids)
    expected["ids"] = sorted(ids) if complete else []
    expected["binding_checkable"] = complete
    return expected


def _binding_beyond_contract(answer: dict, expected: dict) -> dict:
    """Score the binding even when the contract refused the answer's *shape*.

    A diameter answered as two ends is malformed, but the geometry it points at is still readable: on a
    measurement whose binding the label can check, report it as right or wrong instead of unmeasured.
    """
    interpretation = answer.get("interpretation") or {}
    if not expected.get("binding_checkable") or not interpretation:
        return {}
    ids = sorted((interpretation.get("between") or []) + (interpretation.get("matched") or []))
    return {"ids": ids, "expected_ids": expected["ids"], "right": ids == sorted(expected["ids"]),
            "contract_status": answer.get("status")}


def compare(answer: dict, expected: dict) -> dict:
    """Classify one answer: correct, partial, contradiction, unresolved, invalid or no label."""
    if not expected:
        return {"class": "no_label", "fields": {}, "detail": "bu ölçü için bağımsız etiket yok"}
    status, errors = answer.get("status"), answer.get("errors") or []
    if status == "unavailable":
        return {"class": "unavailable", "fields": {}, "detail": "; ".join(errors)}
    if status == "invalid":
        return {"class": "invalid", "fields": {}, "detail": "; ".join(errors),
                "binding_beyond_contract": _binding_beyond_contract(answer, expected)}
    interpretation = answer.get("interpretation")
    if not interpretation:
        return {"class": "invalid", "fields": {}, "detail": "yorum yok"}
    if interpretation.get("unresolved"):
        return {"class": "unresolved", "fields": {},
                "detail": "; ".join(answer.get("questions") or []), "expected": expected}
    claimed = interpretation.get("between") or interpretation.get("matched") or []
    fields = {}
    if expected.get("form"):
        fields["kind"] = interpretation.get("kind") == expected["form"]
    if expected.get("axis"):
        # The axis is not asked for: it is derived from the pair the answer chose.
        fields["axis"] = (answer.get("axis") or "none") == expected["axis"]
    if expected.get("binding_checkable"):
        fields["binding"] = sorted(claimed) == expected["ids"]
    if not fields:
        return {"class": "label_incomplete", "fields": {}, "detail": "etiket bu alanı ölçemiyor",
                "expected": expected}
    verdict = "correct" if all(fields.values()) else ("partial" if any(fields.values()) else "contradiction")
    return {"class": verdict, "fields": fields, "expected": expected,
            "claimed": {"kind": interpretation.get("kind"), "axis": answer.get("axis"), "ids": claimed}}


def _agreed_with_reading(row: dict) -> bool:
    """The harness stores the judge's reading check under `reading_agreement`; the pack under `checks`.

    Reading only one of the two keys silently reported zero agreements in every round, so both are read.
    """
    if row.get("reading_agreement") is not None:
        return bool(row["reading_agreement"])
    return bool((row.get("checks") or {}).get("reading_binding_confirmed"))


def review_verdict(row: dict) -> dict:
    """What a *review* answer did: copy the proposal, correct a defect, or raise a false alarm.

    Ground truth here is the defect itself, known by construction — no label is involved.
    """
    claimed = row.get("answer") or {}
    interpretation = claimed.get("interpretation") or {}
    if claimed.get("status") in ("invalid", "unavailable") or not interpretation:
        return {"class": "no_binding", "detail": "; ".join(claimed.get("errors") or [])}
    binding = {"kind": interpretation.get("kind"),
               "between": sorted(interpretation.get("between") or []),
               "matched": sorted(interpretation.get("matched") or [])}
    injected = row.get("proposal_injected") or {}
    reading = row.get("proposal_reading") or {}
    shaped = {"kind": injected.get("kind"),
              "between": sorted(injected.get("between") or []),
              "matched": sorted(injected.get("matched") or [])}
    true = {"kind": reading.get("kind"),
            "between": sorted(reading.get("between") or []),
            "matched": sorted(reading.get("matched") or [])}
    copied = binding == shaped
    if not (true["between"] or true["matched"]):
        # The reading bound nothing here, so there is no proposal to keep or to correct: the answer
        # neither copies nor contradicts a reading, and counting it as a false alarm would inflate
        # the sheet's error rate with measurements that have nothing to review.
        return {"class": "no_reading_binding", "right": False, "copied": copied}
    if row.get("proposal_corrupted"):
        return {"class": "defect_missed" if copied else "defect_caught",
                "right": binding == true, "copied": copied}
    return {"class": "false_alarm" if not copied else "clean_kept",
            "right": binding == true, "copied": copied}


def review_summary(rows: list[dict]) -> dict:
    summary = {"corrupted": 0, "defect_caught": 0, "clean": 0, "false_alarms": 0, "copied": 0,
               "binding_wrong_beyond_copy": 0, "no_reading_binding": 0, "unusable_answer": 0}
    for row in rows:
        verdict = row.get("review") or {}
        if not verdict:
            continue
        summary["copied"] += bool(verdict.get("copied"))
        if verdict.get("class") == "no_binding":
            summary["unusable_answer"] += 1
            continue
        if verdict.get("class") == "no_reading_binding":
            summary["no_reading_binding"] += 1
            continue
        if row.get("proposal_corrupted"):
            summary["corrupted"] += 1
            summary["defect_caught"] += verdict.get("class") == "defect_caught"
            summary["binding_wrong_beyond_copy"] += (verdict.get("class") == "defect_caught"
                                                     and not verdict.get("right"))
        else:
            summary["clean"] += 1
            summary["false_alarms"] += verdict.get("class") == "false_alarm"
    return summary


def summarise(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    beyond = {"right": 0, "wrong": 0}
    for row in rows:
        verdict = row["verdict"]
        counts[verdict["class"]] = counts.get(verdict["class"], 0) + 1
        scored = verdict.get("binding_beyond_contract") or {}
        if scored:
            beyond["right" if scored["right"] else "wrong"] += 1
    summary = {"measurements": len(rows), "classes": counts,
               "correct": counts.get("correct", 0), "ambiguous": counts.get("unresolved", 0),
               "binding_scored_beyond_contract": beyond,
               "answers_agreed_with_reading": sum(
                   1 for row in rows if _agreed_with_reading(row))}
    if any(row.get("review") for row in rows):
        summary["review"] = review_summary(rows)
    return summary


def run(folder: Path, cases: list[dict], settings: ChatSettings, dry_run: bool = False,
        review: bool = False) -> dict:
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    sampler = ResourceSampler()
    record = {
        "status": "running", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": ("one printed measurement per call; source and geometry ids only; no numeric "
                  "derivation; seen development drawings; no CAD and no semantic acceptance"
                  + ("; the reading's own proposal is shown, with a defect injected into half the "
                     "measurements, so copying the proposal cannot score" if review else "")),
        "versions": {"interpretation": INTERPRETATION_VERSION, "reply": REPLY_VERSION,
                     "judge": JUDGE_VERSION, "catalog": "printed-parameter-catalog-v1",
                     **({"review": REVIEW_VERSION} if review else {})},
        "labels": "eval/relations/<case>.json — evaluation only, never an input to the model",
        "code": code_record(), "manifest": manifest_record(cases), "settings": settings.as_dict(),
        "cases": [], "active": None, "dry_run": dry_run,
    }
    chat = None

    def checkpoint():
        record["seconds"] = round(time.monotonic() - started, 3)
        record["resources"] = sampler.record()
        _atomic_json(folder / "run.json", record)

    checkpoint()
    sampler.start()
    try:
        if not dry_run:
            model = find_model(installed_models(), settings.model)
            record["model"] = model.as_dict()
            chat = OllamaChat(model.name, settings=settings)
            checkpoint()
        for case in cases:
            case_start = time.monotonic()
            record["active"] = {"case": case["id"], "stage": "reading"}
            checkpoint()
            reading = read_sheet(ROOT / case["drawing"])
            evidence = chain_evidence(reading)
            catalog = build_catalog(evidence, suggested_names(evidence))
            label = label_rows(case["id"])
            pairs = pair_label_with_reading(evidence, label)
            row = {"id": case["id"], "part_group": case["part_group"], "drawing": case["drawing"],
                   "reading_seconds": round(time.monotonic() - case_start, 3), "refusals": reading.refusals,
                   "catalog_entries": [entry.model_dump(mode="json") for entry in catalog.entries],
                   "label_pairs": pairs, "measurements": []}
            _atomic_json(folder / f"{case['id']}.label.json",
                         {"pairs": pairs, "label_available": bool(label)})
            for entry in catalog.entries:
                expected = expected_for_measurement(evidence, label, entry.span_id, pairs) if label else {}
                if entry.quantity == "count" and expected:
                    # The label describes the callout; the counted quantity is its own measurement.
                    expected = {**expected, "form": "count"}
                requests = folder / "requests"
                answers = folder / "answers"
                requests.mkdir(exist_ok=True)
                answers.mkdir(exist_ok=True)
                stem = f"{case['id']}--{entry.span_id}--{entry.name}"
                context = measurement_context(evidence, entry.span_id, quantity=entry.quantity)
                proposal_reading, injected, corrupted = None, None, False
                if review:
                    proposal_reading = reading_proposal(context)
                    injected = proposal_reading
                    if review_injects_a_defect(entry.span_id):
                        candidate = corrupt_proposal(proposal_reading, context["allowed_ids"],
                                                     entry.span_id)
                        if candidate is not None:
                            injected, corrupted = candidate, True

                def before_call(candidate, stem=stem, case_id=case["id"], entry=entry):
                    record["active"] = {"case": case_id, "stage": "model", "span_id": entry.span_id}
                    _atomic_json(requests / f"{stem}.request.json", candidate)
                    checkpoint()

                if dry_run:
                    request = {"prompt_version": INTERPRETATION_VERSION, "schema_version": REPLY_VERSION,
                               "span_id": entry.span_id, "prompt": interpret_prompt(context, injected),
                               "schema": reply_schema(context), "allowed_ids": context["allowed_ids"],
                               "context": context}
                    if review:
                        request.update({"review_version": REVIEW_VERSION, "proposal": injected,
                                        "proposal_reading": proposal_reading,
                                        "proposal_corrupted": corrupted})
                    _atomic_json(requests / f"{stem}.request.json", request)
                    row["measurements"].append({
                        "span_id": entry.span_id, "name": entry.name, "entry": entry.model_dump(mode="json"),
                        "expected": expected, "prompt_sha256": _sha(request["prompt"]),
                        "allowed_ids": context["allowed_ids"],
                        "verdict": {"class": "dry_run", "fields": {}}})
                    continue
                answer = interpret_measurement(chat, evidence, entry.span_id, on_request=before_call,
                                               proposal=injected, quantity=entry.quantity)
                dumped = answer.model_dump(mode="json")
                _atomic_json(answers / f"{stem}.json", dumped)
                verdict = compare(dumped, expected)
                measurement = {
                    "span_id": entry.span_id, "name": entry.name, "entry": entry.model_dump(mode="json"),
                    "answer": dumped, "expected": expected, "verdict": verdict,
                    "reading_agreement": (answer.checks or {}).get("reading_binding_confirmed")}
                if review:
                    measurement.update({"proposal_reading": proposal_reading, "proposal_injected": injected,
                                        "proposal_corrupted": corrupted})
                    measurement["review"] = review_verdict(measurement)
                row["measurements"].append(measurement)
                print(f"{case['id']}/{entry.span_id} ({entry.name}): {answer.status} → {verdict['class']}"
                      f" {json.dumps(verdict.get('fields'))} {answer.errors or ''}"
                      + (f" | inceleme: {measurement['review']['class']} (bozuk={corrupted})"
                         if review else ""), flush=True)
            row["summary"] = summarise(row["measurements"])
            row["seconds"] = round(time.monotonic() - case_start, 3)
            _atomic_json(folder / f"{case['id']}.json", row)
            record["cases"].append(row)
            record["active"] = None
            checkpoint()
        record["status"] = "dry-run" if dry_run else "complete"
    except BaseException as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        sampler.stop()
        checkpoint()
        if chat is not None:
            try:
                chat.unload()
            except Exception as exc:
                record["unload_error"] = f"{type(exc).__name__}: {exc}"
        record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        checkpoint()
    return record


def _sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def evidence_pack(record: dict, folder: Path) -> dict:
    """A git-portable record: requests, raw answers, judgements and the label comparison."""
    return {
        "version": 1, "label": folder.name, "run_folder": str(folder),
        "run": {key: record.get(key) for key in (
            "status", "started", "finished", "seconds", "scope", "versions", "settings", "code",
            "manifest", "resources", "model")},
        "cases": [{
            "id": case["id"], "drawing": case["drawing"], "label_pairs": case["label_pairs"],
            "summary": case["summary"],
            "measurements": [{
                "span_id": row["span_id"], "name": row["name"], "printed_value": row["entry"]["value"],
                "printed_unit": row["entry"]["unit"], "expected": row["expected"],
                "request_prompt": (row.get("answer") or {}).get("request", {}).get("prompt", ""),
                "request_sha256": (row.get("answer") or {}).get("request", {}).get("prompt_sha256", ""),
                "raw_answer": (row.get("answer") or {}).get("answer", ""),
                "status": (row.get("answer") or {}).get("status"),
                "errors": (row.get("answer") or {}).get("errors", []),
                "warnings": (row.get("answer") or {}).get("warnings", []),
                "judge_version": (row.get("answer") or {}).get("request", {}).get("judge_version", ""),
                "checks": (row.get("answer") or {}).get("checks", {}),
                "verdict": row["verdict"],
                **({"proposal_reading": row.get("proposal_reading"),
                    "proposal_injected": row.get("proposal_injected"),
                    "proposal_corrupted": row.get("proposal_corrupted"),
                    "review": row.get("review")} if row.get("review") else {}),
            } for row in case["measurements"]],
        } for case in record["cases"]],
    }


def check_pack(path: Path) -> int:
    """Re-judge every stored answer from its own raw text and re-compare with the label."""
    pack = json.loads(path.read_text())
    folder = Path(pack.get("run_folder") or (ROOT / "out" / "meaning-interpretation" / pack["label"]))
    if not folder.exists():
        print(f"koşu klasörü yok: {folder}")
        return 1
    problems, checks, skipped = [], 0, 0
    for case in pack["cases"]:
        stored = json.loads((folder / f"{case['id']}.json").read_text())
        # One printed callout can yield two measurements (a dimension and its count), so the pair
        # (source id, parameter name) identifies a measurement, not the source id alone.
        by_span = {(row["span_id"], row["name"]): row for row in stored["measurements"]}
        for row in case["measurements"]:
            checks += 1
            origin = by_span.get((row["span_id"], row["name"]))
            if origin is None:
                problems.append(f"{case['id']}/{row['span_id']}: koşu kaydında yok")
                continue
            if origin["answer"]["answer"] != row["raw_answer"]:
                problems.append(f"{case['id']}/{row['span_id']}: ham cevap değişmiş")
                continue
            if origin["answer"]["request"]["prompt_sha256"] != row["request_sha256"]:
                problems.append(f"{case['id']}/{row['span_id']}: istek özeti değişmiş")
                continue
            if row.get("proposal_injected") is not None:
                # A review pack must prove what the model was shown: the proposal has to be in the prompt.
                shown = json.dumps(row["proposal_injected"], ensure_ascii=False, separators=(",", ":"))
                if shown not in row["request_prompt"]:
                    problems.append(f"{case['id']}/{row['span_id']}: sunulan öneri istemde yok")
            # The per-answer copy must be the same answer: two records of one call may not drift.
            answer_copy = folder / "answers" / f"{case['id']}--{row['span_id']}--{row['name']}.json"
            if answer_copy.exists():
                copy = json.loads(answer_copy.read_text())
                if copy.get("answer") != origin["answer"]["answer"] or copy.get("status") != origin["answer"]["status"]:
                    problems.append(f"{case['id']}/{row['span_id']}: cevap kopyası koşu kaydıyla aynı değil")
                    continue
            context_path = folder / "requests" / f"{case['id']}--{row['span_id']}--{row['name']}.request.json"
            request = json.loads(context_path.read_text())
            redone = judge_interpretation(json.loads(row["raw_answer"]), request["context"]).model_dump(mode="json")
            # A pack judged by an older contract is not corrupt: its raw answers still verify, but its
            # statuses were produced by different rules, so that comparison is skipped, not faked.
            if (row.get("judge_version") or "") != JUDGE_VERSION:
                skipped += 1
                continue
            if (redone["status"], redone["errors"]) != (row["status"], row["errors"]):
                problems.append(f"{case['id']}/{row['span_id']}: yeniden yargılama farklı sonuç verdi")
            if json.dumps(redone.get("interpretation"), sort_keys=True) != json.dumps(
                    origin["answer"].get("interpretation"), sort_keys=True):
                problems.append(f"{case['id']}/{row['span_id']}: yorum yeniden üretilemedi")
    print(f"kanıt paketi: {checks} ölçü denetlendi, {skipped} ölçüde durum karşılaştırması atlandı "
          f"(paket {skipped and 'başka' or 'bu'} yargı sözleşmesiyle üretilmiş), {len(problems)} sorun")
    for problem in problems:
        print(f"  - {problem}")
    return 1 if problems else 0


def rescore(folder: Path) -> int:
    """Re-score a stored run with the current comparison — no model call, nothing rewritten.

    The raw answers and their verdicts stay as the run produced them; this prints (and writes beside
    the run) what the current measurement rules say about the same answers.
    """
    record = json.loads((folder / "run.json").read_text())
    out = {"label": folder.name, "judge": record.get("versions", {}).get("judge"),
           "review": record.get("versions", {}).get("review"), "cases": []}
    for case in record["cases"]:
        rows, review_rows = [], []
        for row in case["measurements"]:
            verdict = compare(row.get("answer") or {}, row.get("expected") or {})
            rows.append({"span_id": row["span_id"], "name": row["name"], "class": verdict["class"],
                         "fields": verdict.get("fields") or {},
                         "reading_agreement": row.get("reading_agreement"),
                         "binding_beyond_contract": verdict.get("binding_beyond_contract") or {}})
            scored = verdict.get("binding_beyond_contract") or {}
            review = row.get("review") or {}
            if review:
                # The stored review verdict is recomputed, never trusted: same rule, same row.
                review_rows.append({**row, "review": review_verdict(row)})
            print(f"  {case['id'][:12]}/{row['span_id']:7s} {row['name']:18s} {verdict['class']:12s}"
                  f" alan={verdict.get('fields') or {}}"
                  + (f" sözleşme dışı bağ={scored['ids']} beklenen={scored['expected_ids']} "
                     f"{'DOĞRU' if scored['right'] else 'YANLIŞ'}" if scored else "")
                  + (f" | inceleme: {review['class']}" if review else ""), flush=True)
        summary = summarise([{"verdict": {"class": r["class"], "binding_beyond_contract": r["binding_beyond_contract"]},
                              "reading_agreement": r["reading_agreement"]} for r in rows])
        summary["classes"] = {name: sum(1 for r in rows if r["class"] == name) for name in
                              sorted({r["class"] for r in rows})}
        summary["correct"] = summary["classes"].get("correct", 0)
        summary["ambiguous"] = summary["classes"].get("unresolved", 0)
        out["cases"].append({"id": case["id"], "summary": summary, "measurements": rows,
                             **({"review": review_summary(review_rows)} if review_rows else {})})
        print(f"{case['id']}: {json.dumps(summary, ensure_ascii=False)}"
              + (f" inceleme={json.dumps(review_summary(review_rows), ensure_ascii=False)}"
                 if review_rows else ""), flush=True)
    _atomic_json(folder / "rescore.json", out)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "meaning-interpretation")
    parser.add_argument("--cases", nargs="+", default=["plate-pocket-1", "plastic-enclosure-1"])
    parser.add_argument("--model", default="qwen2.5vl:3b")
    parser.add_argument("--num-ctx", type=int, default=16384)
    parser.add_argument("--predict", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--dry-run", action="store_true", help="write the requests, call no model")
    parser.add_argument("--evidence", type=Path, help="write a git-portable evidence pack here")
    parser.add_argument("--check", type=Path, help="re-judge a stored evidence pack")
    parser.add_argument("--rescore", type=Path, metavar="KOŞU_KLASÖRÜ",
                        help="re-score a stored run with the current comparison, calling no model")
    parser.add_argument("--review", action="store_true",
                        help="show the reading's own proposal and inject a defect into half the "
                             "measurements, so copying the proposal cannot score")
    args = parser.parse_args()
    if args.rescore:
        sys.exit(rescore(args.rescore))
    if args.check:
        sys.exit(check_pack(args.check))
    if not args.label:
        parser.error("--label gerekli")
    if Path(args.label).name != args.label or args.label in (".", ".."):
        parser.error("etiket tek klasör adı olmalı")
    available = {case["id"]: case for case in json.loads(CASES_FILE.read_text())["cases"]}
    if set(args.cases) - available.keys() or len(set(args.cases)) != len(args.cases):
        parser.error("bilinmeyen veya tekrarlı parça")
    folder = args.out / args.label
    if folder.exists():
        parser.error(f"çıktı zaten var; yeni etiket seç: {folder}")
    settings = ChatSettings(model=args.model, num_ctx=args.num_ctx, num_predict=args.predict,
                            timeout=args.timeout, temperature=0)
    record = run(folder, [available[key] for key in args.cases], settings, dry_run=args.dry_run,
                 review=args.review)
    if args.evidence:
        _atomic_json(args.evidence, evidence_pack(record, folder))
    if not args.dry_run:
        for case in record["cases"]:
            print(f"{case['id']}: {case['summary']}")


if __name__ == "__main__":
    main()
