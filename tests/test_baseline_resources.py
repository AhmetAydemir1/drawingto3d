"""Resource decisions and interrupted measurements must rest on valid, durable records."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def baseline():
    path = Path(__file__).resolve().parents[1] / "eval" / "model_baseline.py"
    spec = importlib.util.spec_from_file_location("audit_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("text, expected", [
    ("total = 13312.00M used = 7811.25M free = 5500.75M (encrypted)", 7811.25),
    ("total = 1.00G used = 0.00M free = 1.00G", 0.0),
    ("total = 2G used = 1.5G free = 0.5G", 1536.0),
    ("total = 13312.00M free = 5500.75M", None),
    ("", None),
])
def test_swap_reads_used_not_total(baseline, text, expected):
    assert baseline._swap_used_mb(text) == expected


@pytest.mark.parametrize("page_bytes, expected", [(16384, 16.0), (4096, 4.0)])
def test_vm_stat_uses_reported_page_size(baseline, page_bytes, expected):
    output = (f"Mach Virtual Memory Statistics: (page size of {page_bytes} bytes)\n"
              "Pages free: 1024.\nPages occupied by compressor: 2048.\n")
    assert baseline._vm_stat("Pages free", output) == expected
    assert baseline._vm_stat("Pages occupied by compressor", output) == expected * 2
    assert baseline._vm_stat("Pages free", "Pages free: 1024.") is None


def test_unavailable_samples_are_not_zero_and_raw_text_is_kept(baseline, monkeypatch):
    monkeypatch.setattr(baseline, "_command", lambda *args: "")
    sampler = baseline.ResourceSampler()
    sampler.start()
    sampler.stop()
    record = sampler.record()
    assert record["measurement_version"] == 2
    assert record["swap_used_mb_start"] is None
    assert record["pages_free_mb_min"] is None
    assert record["ollama_rss_mb_peak"] is None
    assert record["raw_samples"][0]["raw_vm_stat"] == ""


def test_interrupted_run_keeps_finished_case_and_names_active_step(baseline, monkeypatch, tmp_path):
    drawing = tmp_path / "sheet.pdf"
    drawing.write_bytes(b"fixture")
    manifest = tmp_path / "cases.json"
    manifest.write_text(json.dumps({"cases": [{
        "id": "fixture", "drawing": "sheet.pdf", "split": "seen-regression", "part_group": "fixture",
    }]}))
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    monkeypatch.setattr(baseline, "CASES_FILE", manifest)
    monkeypatch.setattr(baseline, "code_record", lambda: {})
    monkeypatch.setattr(baseline, "_command", lambda *args: "")
    monkeypatch.setattr(sys, "argv", ["model_baseline.py", "--no-model", "--conditions", "reading,chain",
                                      "--label", "interrupted"])
    monkeypatch.setattr(baseline, "condition_reading", lambda *args: {
        "case": "fixture", "condition": "reading", "status": "partial", "error_class": "reading",
        "seconds": 0.1, "reason": "fixture result",
    })

    def interrupt(*args):
        path = tmp_path / "out/model-baseline/interrupted/run.json"
        running = json.loads(path.read_text())
        assert running["run"]["status"] == "running"
        assert len(running["results"]) == 1  # Already on disk before the hard stop.
        raise KeyboardInterrupt

    monkeypatch.setattr(baseline, "condition_chain", interrupt)
    with pytest.raises(KeyboardInterrupt):
        baseline.main()
    folder = tmp_path / "out/model-baseline/interrupted"
    record = json.loads((folder / "run.json").read_text())
    assert record["run"]["status"] == "interrupted"
    assert record["run"]["active"] == {"case": "fixture", "condition": "chain"}
    assert len(record["results"]) == 1
    assert record["results"][0]["reason"] == "fixture result"
    assert (folder / "cases/fixture-reading.json").exists()
    original = (folder / "run.json").read_bytes()
    with pytest.raises(SystemExit) as error:
        baseline.main()
    assert error.value.code == 2
    assert (folder / "run.json").read_bytes() == original


def test_atomic_write_failure_preserves_last_good_record(baseline, monkeypatch, tmp_path):
    path = tmp_path / "run.json"
    baseline._atomic_json(path, {"results": ["finished"]})

    def fail_replace(*args):
        raise OSError("simulated interruption before rename")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError):
        baseline._atomic_json(path, {"results": ["finished", "new"]})
    assert json.loads(path.read_text()) == {"results": ["finished"]}


def test_cli_dispatches_split_and_normalization_to_both_model_conditions(baseline, monkeypatch, tmp_path):
    (tmp_path / "sheet.pdf").write_bytes(b"fixture")
    manifest = tmp_path / "cases.json"
    manifest.write_text(json.dumps({"cases": [{
        "id": "fixture", "drawing": "sheet.pdf", "split": "seen-regression", "part_group": "fixture",
    }]}))
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    monkeypatch.setattr(baseline, "CASES_FILE", manifest)
    monkeypatch.setattr(baseline, "code_record", lambda: {})
    monkeypatch.setattr(baseline, "_command", lambda *args: "")
    monkeypatch.setattr(sys, "argv", ["model_baseline.py", "--no-model", "--conditions",
                                      "relations,chain_model", "--split", "--normalize-names",
                                      "--label", "routing"])
    seen = []

    def condition(name):
        def run(case, *args, **kwargs):
            seen.append((name, kwargs))
            return {"case": case["id"], "condition": name, "status": "skipped", "error_class": "unsupported"}
        return run

    monkeypatch.setattr(baseline, "condition_relations", condition("relations"))
    monkeypatch.setattr(baseline, "condition_chain_model", condition("chain_model"))
    baseline.main()
    assert [name for name, _ in seen] == ["relations", "chain_model"]
    assert all(options == {"structured": True, "split": True, "normalize_names": True}
               for _, options in seen)


def test_chain_model_split_uses_step_validation_and_saves_the_failed_answer(baseline, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from drawingto3d.planner import REPLY_SCHEMA_VERSION_SPLIT

    (tmp_path / "sheet.pdf").write_bytes(b"fixture")
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    monkeypatch.setattr(baseline, "read_sheet", lambda path: SimpleNamespace(notes=[], refusals=[]))
    monkeypatch.setattr(baseline, "chain_evidence", lambda reading: {
        "printed": [], "claims": [], "sheet": {"scale_known": True},
        "geometry": {"circles": [], "outline_mm": {}},
    })

    class Chat:
        def __init__(self):
            self.formats = []

        def settings_record(self):
            return {}

        def complete(self, prompt, **kwargs):
            self.formats.append(kwargs["response_format"])
            kwargs["stats"]["done_reason"] = "stop"
            return '{"parameters":{"width":{"value":100,"span_ids":["missing"]}}}'

    chat = Chat()
    row = baseline.condition_chain_model({"id": "fixture", "drawing": "sheet.pdf"}, tmp_path,
                                         chat, 1, None, split=True)
    assert len(chat.formats) == 1
    assert chat.formats[0]["title"] == f"{REPLY_SCHEMA_VERSION_SPLIT}: parameters"
    assert row["status"] == "failed" and "adım parameters" in row["reason"]
    saved = json.loads((tmp_path / "fixture-chain_model-candidate.json").read_text())
    assert len(saved["steps"]) == 1 and saved["steps"][0]["accepted"] is False
    assert '"missing"' in saved["steps"][0]["answer"]
