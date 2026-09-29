"""The profile-step evidence bundle is derived from the run records, so it cannot drift from them.

`out/` is not tracked, so the bundle is the half of the measurement the next window inherits. These
tests drive the generator over synthetic records: the bundle must quote the record's own settings,
timings, errors and fingerprints, `--check` must fail when a record moves, and the offline replay
must refuse to describe a question the run did not ask (its verbatim pass has to reproduce the
recorded error, while the pass that changes the radius stays labelled as a change).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from drawingto3d.planner import validate_step_payload

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE = {
    "printed": [{"span_id": "pdf-0", "text": "1 00,00", "value": 100.0, "unit": "mm",
                 "kind": "linear", "count": None}],
    "claims": [],
    "geometry": {"circles": [], "outline_mm": {"width": 120.87, "height": 80.56}},
    "sheet": {"scale_known": True},
}

PARAMETERS_ANSWER = json.dumps({"parameters": {
    "hole_spacing_x": {"unit": "mm", "source": "printed", "value": 100.0, "span_ids": ["pdf-0"]}}})

PROFILE_ANSWER = json.dumps({"sketches": {"profile_1": {"entities": [
    {"type": "line", "start": ["-50.35", "-30.21"], "end": ["-50.35", "30.21"]},
    {"type": "arc", "center": ["-50.35", "30.21"], "radius": "x(6.84/2)",
     "start_degrees": 90, "end_degrees": 270}]}}})


def load_module():
    spec = importlib.util.spec_from_file_location("profile_step_evidence",
                                                 ROOT / "eval" / "profile_step_evidence.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["profile_step_evidence"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def plan_stage(condition: str, steps: list[dict]) -> dict:
    return {"case": "plate-pocket-1", "condition": condition, "status": "failed",
            "error_class": "planning", "reason": "şema hatası", "seconds": 42.45,
            "stages": {"plan": {"status": "failed", "errors": ["şema hatası"],
                                "settings": {"model": "qwen2.5vl:3b", "num_ctx": 16384,
                                             "num_predict": 4096,
                                             "response_format": "json-schema:reply v4 split",
                                             "profile_targets": "measured-closed-profiles-v1"},
                                "steps": steps}}}


def step(name: str, accepted: bool, errors: list[str], answer: str, **extra) -> dict:
    record = {"step": name, "accepted": accepted, "errors": errors, "answer": answer,
              "seconds": 17.85, "num_predict": 1024, "answer_truncated": False,
              "prompt_sha256": "a" * 64, "schema_sha256": "b" * 64,
              "stats": {"done_reason": "stop", "eval_count": 129}}
    record.update(extra)
    return record


def write_run(runs: Path, label: str, results: list[dict], **run_overrides) -> Path:
    folder = runs / label
    (folder / "cases").mkdir(parents=True, exist_ok=True)
    run = {"run": {"id": label, "started": "2026-09-27T17:38:07+0300", "status": "complete",
                   "seconds": 67.54, "argv": ["eval/model_baseline.py", "--split"],
                   "conditions": ["relations", "chain_model"]},
           "model": {"requested": "qwen2.5vl:3b"},
           "manifest": {"file": "eval/cases.json", "sha256": "c" * 64,
                        "drawing_sha256": {"plate-pocket-1": "d" * 64}},
           "code": {"git_head": "e" * 40, "dirty": True},
           "resources": {"measurement_version": 2, "samples": 34, "swap_used_mb_start": 8356.94,
                         "swap_used_mb_peak": 10383.44, "pages_free_mb_min": 55.594,
                         "raw_samples": [{"seconds": 1.0}]},
           "results": results}
    run["run"].update(run_overrides)
    (folder / "run.json").write_text(json.dumps(run))
    (folder / "cases" / "plate-pocket-1-chain_model-evidence.json").write_text(json.dumps(EVIDENCE))
    # The candidate file carries the same answer the run record does, and the error the run recorded
    # for it: the replay's whole job is to reproduce that error from the answer.
    profile = next(entry for entry in next(row for row in results
                                           if row["condition"] == "chain_model")["stages"]["plan"]["steps"]
                   if entry["step"] == "profile")
    (folder / "cases" / "plate-pocket-1-chain_model-candidate.json").write_text(json.dumps(
        {"steps": [{"step": "parameters", "answer": PARAMETERS_ANSWER},
                   {"step": "profile", "errors": list(profile["errors"]), "answer": profile["answer"]}]}))
    return folder


def judged_profile_errors() -> list[str]:
    """What the step judge says about the fixture answer — the record's error list, not a guess."""
    return validate_step_payload("profile", json.loads(PROFILE_ANSWER),
                                 {"parameters": json.loads(PARAMETERS_ANSWER)}, EVIDENCE)


def sample_results(profile_errors: list[str] | None = None) -> list[dict]:
    return [
        plan_stage("relations", [step("parameters", False,
                                      ["parametre 'hole_spacing_x': kanıtta olmayan ölçü kaydına atıf ['h1', 'h2']"],
                                      PARAMETERS_ANSWER)]),
        plan_stage("chain_model", [
            step("parameters", True, [], PARAMETERS_ANSWER),
            step("profile", False, profile_errors or judged_profile_errors(),
                 PROFILE_ANSWER, label="profile 1/6 (outline)",
                 profile={"index": 1, "count": 6, "kind": "outline", "geometry_id": "outline"}),
        ]),
    ]


def prepare(tmp_path, monkeypatch, *, profile_errors=None):
    module = load_module()
    runs = tmp_path / "model-baseline"
    write_run(runs, "profile-3b-01", sample_results(profile_errors))
    write_run(runs, "names-3b-05", sample_results())
    monkeypatch.setattr(module, "RUNS", runs)
    monkeypatch.setattr(module, "BUNDLE", tmp_path / "profile-step-evidence.json")
    return module


def test_the_bundle_quotes_the_record_instead_of_a_summary(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    bundle = module.build()
    assert bundle["source"]["settings"]["num_ctx"] == 16384
    assert bundle["source"]["settings"]["profile_targets"] == "measured-closed-profiles-v1"
    assert bundle["source"]["seconds"] == 67.54
    chain = next(row for row in bundle["runs"] if row["condition"] == "chain_model")
    assert [entry["step"] for entry in chain["steps"]] == ["parameters", "profile"]
    assert chain["steps"][1]["label"] == "profile 1/6 (outline)"
    assert chain["steps"][1]["profile"]["count"] == 6
    assert chain["steps"][1]["stats"]["eval_count"] == 129
    # The raw answer travels whole: a bundle that paraphrased it could not be judged again.
    assert json.loads(chain["steps"][1]["answer"])["sketches"]["profile_1"]["entities"][1]["radius"] \
        == "x(6.84/2)"
    # Resource samples stay in `out/`; the summary is what the report cites.
    assert "raw_samples" not in bundle["resources"]


def test_the_bundle_names_the_question_that_was_answered_before(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    comparison = module.build()["answered_same_question_as_previous_round"]
    assert comparison["prompt_identical"] is True
    assert comparison["answer_identical"] is True
    assert comparison["this_verdict"] is False


def test_the_offline_replay_has_to_reproduce_the_recorded_error(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    replay = module.build()["replay"]
    assert replay["verbatim_matches_record"] is True
    assert replay["verbatim"] == judged_profile_errors()
    # The second pass changes one thing and says so; it is diagnostics, not a plan.
    assert "changed_for_replay" in replay
    assert "10.05" in replay["changed_for_replay"]["what"]
    assert replay["changed_for_replay"]["errors"] == [] or \
        "profil" in json.dumps(replay["changed_for_replay"]["errors"], ensure_ascii=False)


def test_a_replay_that_describes_another_answer_is_flagged(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    folder = module.RUNS / "profile-3b-01"
    (folder / "cases" / "plate-pocket-1-chain_model-candidate.json").write_text(json.dumps(
        {"steps": [{"step": "parameters", "answer": PARAMETERS_ANSWER},
                   {"step": "profile", "errors": ["başka bir hata"],
                    "answer": PROFILE_ANSWER}]}))
    assert module.build()["replay"]["verbatim_matches_record"] is False


def test_check_fails_when_a_record_moves(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["profile_step_evidence.py", "--write"])
    assert module.main() == 0
    monkeypatch.setattr(sys, "argv", ["profile_step_evidence.py", "--check"])
    assert module.main() == 0
    # A run that changes one number leaves the bundle stale; reading it as current is the failure.
    write_run(module.RUNS, "profile-3b-01", sample_results(), seconds=68.9)
    assert module.main() == 1
    monkeypatch.setattr(sys, "argv", ["profile_step_evidence.py", "--write"])
    assert module.main() == 0
    monkeypatch.setattr(sys, "argv", ["profile_step_evidence.py", "--check"])
    assert module.main() == 0


def test_a_missing_run_record_fails_loudly(tmp_path, monkeypatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    (module.RUNS / "profile-3b-01" / "run.json").unlink()
    with pytest.raises(SystemExit, match="koşu kaydı yok"):
        module.build()
