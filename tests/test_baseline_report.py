"""The report's generated block is built from the run records, so it cannot drift from them.

A measurement report whose numbers were typed by hand is a claim. These tests drive the generator over
synthetic runs and frontend records in a temporary tree: the block must name every run and every case, must
count coverage from the records rather than from a table, and `--check` must fail when the report and the
records disagree.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("baseline_report", ROOT / "eval" / "baseline_report.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["baseline_report"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_run(runs: Path, name: str, payload: dict) -> None:
    folder = runs / name
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(json.dumps(payload))


def sample_run(label: str, case: str, status: str, error_class: str | None) -> dict:
    return {
        "run": {"id": label, "started": "2026-09-27T04:00:00+0300", "conditions": ["relations"],
                "no_model": False, "structured_output": True, "seconds": 12.5},
        "model": {"name": "qwen3-vl:8b-instruct"},
        "statuses": {status: 1},
        "error_classes": ({error_class: 1} if error_class else {}),
        "resources": {"swap_used_mb_start": 13312.0, "swap_used_mb_peak": 13312.0,
                      "pages_free_mb_min": 14.5, "ollama_rss_mb_peak": 8295.3},
        "results": [{"case": case, "condition": "relations", "status": status,
                     "error_class": error_class, "reason": "şema hatası: sketches.outline.entities.0"}],
    }


def test_the_block_names_every_run_and_every_case(tmp_path, monkeypatch) -> None:
    module = load_module()
    runs = tmp_path / "model-baseline"
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    write_run(runs, "a", sample_run("run-a", "plate-pocket-1", "failed", "planning"))
    write_run(runs, "b", sample_run("run-b", "flange-1", "refused", "reading"))
    (frontend / "flange-1.json").write_text(json.dumps({
        "id": "flange-1", "source": "raster", "printed": ["1.00", "30", "60"],
        "covers": ["1.00"], "noise": ["90"], "calibration": None,
        "spans": [{"anchors": [[0, 0], [10, 0]]}, {"anchors": []}],
    }))
    monkeypatch.setattr(module, "RUNS", runs)
    monkeypatch.setattr(module, "FRONTEND", frontend)
    block = module.block()
    assert "run-a" in block and "run-b" in block
    assert "plate-pocket-1" in block and "flange-1" in block
    assert "planning=1" in block and "reading=1" in block
    # Coverage and anchors are counted from the record: one of two spans carries a pair of anchors.
    assert "| flange-1 | raster | 2 | 3 | 1/3 | 1 | - | 1 |" in block
    assert "JSON" not in block


def test_check_fails_when_a_run_is_newer_than_the_report(tmp_path, monkeypatch) -> None:
    module = load_module()
    runs = tmp_path / "model-baseline"
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    write_run(runs, "a", sample_run("run-a", "plate-pocket-1", "failed", "planning"))
    report = tmp_path / "report.md"
    monkeypatch.setattr(module, "RUNS", runs)
    monkeypatch.setattr(module, "FRONTEND", frontend)
    monkeypatch.setattr(module, "REPORT", report)
    report.write_text(f"# başlık\n\n{module.OPEN}\n{module.CLOSE}\n")
    assert module.main.__name__ == "main"
    monkeypatch.setattr(sys, "argv", ["baseline_report.py", "--write"])
    assert module.main() == 0
    monkeypatch.setattr(sys, "argv", ["baseline_report.py", "--check"])
    assert module.main() == 0
    write_run(runs, "b", sample_run("run-b", "flange-1", "refused", "reading"))
    assert module.main() == 1
    monkeypatch.setattr(sys, "argv", ["baseline_report.py", "--write"])
    assert module.main() == 0
    monkeypatch.setattr(sys, "argv", ["baseline_report.py", "--check"])
    assert module.main() == 0
