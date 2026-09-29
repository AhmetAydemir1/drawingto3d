"""A hard stop after one answer must leave both it and the next full request on disk."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from drawingto3d.llama import ChatSettings, ModelInfo


def test_interrupt_preserves_answer_and_next_request(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "eval"))
    spec = importlib.util.spec_from_file_location("catalog_journal", root / "eval/catalog_parameters.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "code_record", lambda: {})
    monkeypatch.setattr(module, "manifest_record", lambda cases: {})
    monkeypatch.setattr(module, "installed_models", lambda: [ModelInfo(name="fixture")])
    monkeypatch.setattr(module, "read_sheet", lambda path: SimpleNamespace(refusals=[]))
    monkeypatch.setattr(module, "chain_evidence", lambda reading: {
        "printed": [{"span_id": "s1", "value": 5, "unit": "mm", "kind": "linear"}]})
    monkeypatch.setattr(module, "ResourceSampler", lambda: SimpleNamespace(
        start=lambda: None, stop=lambda: None, record=lambda: {}))
    folder = tmp_path / "run"

    class Chat:
        calls = 0

        def __init__(self, model, settings):
            self.settings = settings

        def settings_record(self):
            return self.settings.as_dict()

        def complete(self, prompt, response_format, stats):
            self.calls += 1
            record = json.loads((folder / "run.json").read_text())
            assert record["active"]["candidate"]["request"]["prompt"] == prompt
            if self.calls == 2:
                assert len(record["cases"]) == 1
                assert (folder / "second.request.json").exists()
                raise KeyboardInterrupt
            stats["done_reason"] = "stop"
            return json.dumps({"selections": [], "derived": [], "questions": ["Which feature is 5 mm?"]})

        def unload(self):
            pass

    monkeypatch.setattr(module, "OllamaChat", Chat)
    cases = [{"id": name, "part_group": name, "drawing": "fixture.pdf"} for name in ("first", "second")]
    with pytest.raises(KeyboardInterrupt):
        module.run(folder, cases, ChatSettings(model="fixture"))
    record = json.loads((folder / "run.json").read_text())
    assert record["status"] == "interrupted"
    assert record["cases"][0]["candidate"]["status"] == "needs_input"
    assert record["active"]["case"] == "second"
    assert (folder / "first.json").exists() and not (folder / "second.json").exists()
    original = (folder / "run.json").read_bytes()
    with pytest.raises(FileExistsError):
        module.run(folder, cases, ChatSettings(model="fixture"))
    assert (folder / "run.json").read_bytes() == original
