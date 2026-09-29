"""Source quantities survive incomplete geometry and are reviewable without a model."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from drawingto3d import cli, proposal
from drawingto3d.meaning import Meanings, SpanMeaning


@pytest.fixture
def partial_reading(monkeypatch):
    meanings = Meanings(source_ref="sheet.pdf", source_sha256="a" * 64, spans=[
        SpanMeaning(span_id="s1", text="2.345 in", printed_value=2.345, printed_mm=59.56,
                    unit="in", kind="linear", anchor_mode="none")])
    monkeypatch.setattr(proposal, "observe", lambda path: SimpleNamespace(frame=None))
    monkeypatch.setattr(proposal, "meaning_page", lambda path: meanings)
    monkeypatch.setattr(proposal, "_primitives", lambda observations: ({}, {}, {}))
    monkeypatch.setattr(proposal, "_outline_of", lambda *args: (
        None, {"loops": 0, "frame_loops": 0, "annotation_loops": 0, "reason": "no-loops"}))
    return meanings


@pytest.mark.parametrize("scale", [None, 4])
def test_printed_values_survive_missing_scale_or_outline(partial_reading, scale):
    partial_reading.sheet_px_per_mm = scale
    result = proposal.read_sheet("sheet.pdf")
    assert result.refusals
    assert len(result.printed) == 1
    assert result.printed[0]["value"] == 2.345 and result.printed[0]["unit"] == "in"
    assert not result.outline_mm


def test_cli_writes_partial_catalog_and_refuses_to_erase_it(partial_reading, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "installed_models", lambda: pytest.fail("a catalog must work without Ollama"))
    payload = cli.catalog_from_drawing(Path("sheet.pdf"), tmp_path)
    assert payload["status"] == "needs_input" and payload["entries"] == 1
    path = tmp_path / "catalog.json"
    original = path.read_bytes()
    record = json.loads(original)
    assert record["catalog"]["entries"][0]["value"] == 2.345
    assert record["source_sha256"] == "a" * 64
    assert record["geometry_refusals"] and not record["geometry_verified"]
    assert "2.345" in (tmp_path / "review.md").read_text()
    with pytest.raises(ValueError, match="yeni çıktı"):
        cli.catalog_from_drawing(Path("sheet.pdf"), tmp_path)
    assert path.read_bytes() == original


def test_empty_reading_is_kept_with_reason(partial_reading, tmp_path):
    partial_reading.spans = []
    result = cli.catalog_from_drawing(Path("sheet.pdf"), tmp_path)
    assert result["status"] == "needs_input" and result["entries"] == 0
    record = json.loads((tmp_path / "catalog.json").read_text())
    assert record["catalog"] is None and record["errors"]
    assert (tmp_path / "evidence.json").exists()


def test_catalog_command_dispatches_without_model(partial_reading, tmp_path, monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["drawingto3d", "catalog", "sheet.pdf", str(tmp_path)])
    monkeypatch.setattr(cli, "installed_models", lambda: pytest.fail("unexpected model lookup"))
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert output["entries"] == 1 and output["status"] == "needs_input"
