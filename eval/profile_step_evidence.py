"""The recorded bundle for the per-profile step (PLAN section 20), derived from the run records.

    PYTHONPATH=src .venv/bin/python eval/profile_step_evidence.py --write   # rebuild the bundle
    PYTHONPATH=src .venv/bin/python eval/profile_step_evidence.py --check   # fail if it has drifted

`eval/reports/profile-step-evidence.json` is the durable half of the `profile-3b-01` measurement:
`out/` is not tracked, so the raw answers, the fingerprints, the timings, the validation errors and
the resource summary have to live in a tracked file or the next window inherits a claim instead of a
record. Everything here is read out of the run's own files — nothing is typed by hand — and the two
comparisons that carry the argument (the answered prompt that is byte-identical to the previous
round's, and the offline replay of the recorded answer) are recomputed at check time, so a bundle
that drifts from the records fails instead of aging quietly.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.planner import (  # noqa: E402  (after the path is set)
    REPLY_SCHEMA_VERSION_SPLIT,
    PROMPT_VERSION_SPLIT,
    validate_step_payload,
)

RUNS = ROOT / "out" / "model-baseline"
LABEL = "profile-3b-01"
PREVIOUS = "names-3b-05"
BUNDLE = ROOT / "eval" / "reports" / "profile-step-evidence.json"

SCOPE = (
    "PLAN section 20, the profile step: one call per closed profile the readings measured, each "
    "sub-answer judged before the next call is spent. Measured once on the real plate with a new "
    "label, same model and same 16384/4096 settings as the previous round. No model-generated STEP "
    "is claimed."
)

NEXT_DECISION = (
    "Both measured first errors are the same class: the answer does not keep the reading's own id "
    "spaces apart (the relations answer cites drawn-circle ids where printed span ids belong; the "
    "outline call of the product path draws a hole's centre and diameter). The single next change is "
    "therefore the evidence block in the prompt: printed numbers under a heading that says span_ids "
    "cite them, measured regions under a heading that says their ids are geometry and not citations, "
    "and each profile call's own region in a structural key rather than glued into a sentence. "
    "Schema, naming rule, persistent contract and call count stay as they are, and the run gets a "
    "fresh label. If the parameters step still invents literal arithmetic, the next single rule is "
    "that a derived parameter names accepted parameters and cites no printed span."
)


def _record(label: str) -> dict:
    path = RUNS / label / "run.json"
    if not path.exists():
        raise SystemExit(f"koşu kaydı yok: {path}")
    return json.loads(path.read_text())


def _plan_step(record: dict, condition: str, step: str) -> dict:
    row = next(item for item in record["results"] if item["condition"] == condition)
    return next(entry for entry in row["stages"]["plan"]["steps"] if entry["step"] == step)


def _steps(record: dict, condition: str) -> list[dict]:
    row = next(item for item in record["results"] if item["condition"] == condition)
    return row["stages"]["plan"]["steps"]


def _rows(record: dict) -> list[dict]:
    rows = []
    for row in record["results"]:
        plan = row["stages"]["plan"]
        rows.append({
            "case": row["case"],
            "condition": row["condition"],
            "status": row["status"],
            "error_class": row["error_class"],
            "reason": row["reason"],
            "seconds": row["seconds"],
            "settings": plan.get("settings"),
            "plan_status": plan.get("status"),
            "errors": plan.get("errors"),
            "steps": [
                {
                    "step": entry["step"],
                    "label": entry.get("label"),
                    "profile": entry.get("profile"),
                    "accepted": entry.get("accepted"),
                    "seconds": entry.get("seconds"),
                    "num_predict": entry.get("num_predict"),
                    "answer_truncated": entry.get("answer_truncated"),
                    "prompt_version": entry.get("prompt_version"),
                    "response_format": entry.get("response_format"),
                    "prompt_sha256": entry.get("prompt_sha256"),
                    "schema_sha256": entry.get("schema_sha256"),
                    "stats": entry.get("stats"),
                    "errors": entry.get("errors"),
                    "answer": entry.get("answer"),
                }
                for entry in plan.get("steps") or []
            ],
        })
    return rows


def _replay(folder: Path) -> dict:
    """Judge the recorded answer again, offline, and read the next error it would hit.

    The verbatim replay has to reproduce the recorded error exactly, or this bundle is describing a
    different question than the run asked. The second pass changes one thing — the illegal function
    in the radius — and is labelled `changed_for_replay`: it is diagnostics on the raw answer, never
    a plan and never a fix applied anywhere in the pipeline.
    """
    evidence = json.loads((folder / "cases" / "plate-pocket-1-chain_model-evidence.json").read_text())
    candidate = json.loads((folder / "cases" / "plate-pocket-1-chain_model-candidate.json").read_text())
    steps = candidate["steps"]
    parameters = next(entry for entry in steps if entry["step"] == "parameters")
    profile = next(entry for entry in steps if entry["step"] == "profile")
    accepted = {"parameters": json.loads(parameters["answer"])}
    payload = json.loads(profile["answer"])
    verbatim = validate_step_payload("profile", payload, accepted, evidence)
    changed = deepcopy(payload)
    changed["sketches"]["profile_1"]["entities"][1]["radius"] = "10.05"
    return {
        "method": "validate_step_payload('profile', recorded answer, accepted={parameters}, run's own evidence file)",
        "verbatim": verbatim,
        "verbatim_matches_record": verbatim == list(profile["errors"]),
        "changed_for_replay": {
            "what": "only the arc radius: 'x(6.84/2)' → '10.05' (the round corner the reading measured)",
            "errors": validate_step_payload("profile", changed, accepted, evidence),
        },
    }


def build() -> dict:
    record = _record(LABEL)
    previous = _record(PREVIOUS)
    folder = RUNS / LABEL
    relations = _plan_step(record, "relations", "parameters")
    before = _plan_step(previous, "relations", "parameters")
    same_prompt = relations["prompt_sha256"] == before["prompt_sha256"]
    same_answer = relations["answer"] == before["answer"]
    return {
        "scope": SCOPE,
        "interface": {
            # From the run record, not from the module constant: the constant moves with the code, and
            # after the evidence-block change it read `general-plan-v4-split-profile-ids` for a round
            # that actually asked `general-plan-v3-split-profile` — a bundle that renames the question
            # it documents is a claim that ages silently.
            "prompt_version": record.get("prompt_version") or PROMPT_VERSION_SPLIT,
            "reply_schema": REPLY_SCHEMA_VERSION_SPLIT,
            "change": (
                "profile_targets() lists the closed profiles the readings measured (one closed outer "
                "loop plus each closed circle); propose_plan_split() makes one call per target, judges "
                "the sub-answer before the next call, caps a profile call at PROFILE_PREDICT_CAP=1024 "
                "tokens and records label/index/count/kind/geometry_id. Reply schema, naming rule, "
                "GeneralPlan v1 and the CAD validator are unchanged."
            ),
        },
        "source": {
            "run": str(folder / "run.json"),
            "settings": record["results"][0]["stages"]["plan"]["settings"],
            "command": record["run"]["argv"],
            "status": record["run"]["status"],
            "seconds": record["run"]["seconds"],
            "model": record["model"],
            "code": record["code"],
            "manifest": {
                "file": record["manifest"]["file"],
                "sha256": record["manifest"]["sha256"],
                "drawing_sha256": record["manifest"]["drawing_sha256"]["plate-pocket-1"],
            },
        },
        "resources": {
            key: value for key, value in (record.get("resources") or {}).items() if key != "raw_samples"
        },
        "runs": _rows(record),
        "answered_same_question_as_previous_round": {
            "label": PREVIOUS,
            "step": "relations/parameters",
            "prompt_sha256": relations["prompt_sha256"],
            "prompt_identical": same_prompt,
            "answer_identical": same_answer,
            "previous_verdict": before.get("accepted"),
            "previous_verdict_note": (
                "The earlier record carries no `accepted` field: the step judge that writes it landed "
                "after `names-3b-05`, which is why the same answer reads as accepted there and refused "
                "here."
            ),
            "this_verdict": relations.get("accepted"),
            "reading": (
                "Same question, same answer, different verdict: the changed thing is the step judge in "
                "the working tree, not the model or the interface. eval/reports/step-validation-replay.json "
                "recorded this verdict offline first."
            ),
        },
        "replay": _replay(folder),
        "measurement_limits": [
            "No plan passed, so no CAD build, no drawing check and no second part group were measured.",
            "The three-call interface (relations) never reached the profile step: it stopped at parameters.",
            "One sheet, one 3B model, one temperature-0 run; not a capacity verdict and not a training claim.",
        ],
        "next_decision": NEXT_DECISION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="paketi koşu kayıtlarından yeniden üret")
    parser.add_argument("--check", action="store_true", help="paket kayıtlarla uyuşmuyorsa çıkış kodu 1")
    arguments = parser.parse_args()
    fresh = build()
    text = json.dumps(fresh, indent=2, ensure_ascii=False) + "\n"
    if arguments.check:
        if not BUNDLE.exists():
            print(f"paket yok: {BUNDLE}", file=sys.stderr)
            return 2
        if BUNDLE.read_text() != text:
            print("kanıt paketi koşu kayıtlarıyla uyuşmuyor: eval/profile_step_evidence.py --write",
                  file=sys.stderr)
            return 1
        if not fresh["replay"]["verbatim_matches_record"]:
            print("kayıtlı yanıtın çevrimdışı tekrarı aynı hatayı vermiyor", file=sys.stderr)
            return 1
        print("kanıt paketi koşu kayıtlarıyla uyuşuyor")
        return 0
    if arguments.write:
        BUNDLE.write_text(text)
        print(f"yazıldı: {BUNDLE}")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
