"""Any installed model, chosen by what it can do — not by a fixed tag list.

These tests replace the local server's model listing, so the choice logic is exercised without Ollama:
capabilities decide vision, a preference order only breaks ties, an explicit choice is honoured
exactly, and a machine with no reader refuses instead of feeding an image to a text model.
"""
from __future__ import annotations

import pytest

from drawingto3d import llama
from drawingto3d.errors import UnavailableModel
from drawingto3d.llama import ModelInfo, OllamaCoder, OllamaVision, choose_text_model, choose_vision_model


def model(name: str, capabilities: tuple[str, ...] = ()) -> ModelInfo:
    return ModelInfo(name=name, capabilities=capabilities)


READER = model("qwen3-vl:8b-instruct", ("vision", "completion", "tools"))
OLDER_READER = model("qwen2.5vl:7b", ("vision", "completion"))
CODER = model("qwen2.5-coder:7b", ("completion", "tools", "insert"))
SMALL_TEXT = model("llama3.2:3b", ("completion", "tools"))


@pytest.fixture
def machine(monkeypatch):
    def install(*models: ModelInfo):
        monkeypatch.setattr(llama, "installed_models", lambda host=None: list(models))
    monkeypatch.delenv("DRAWINGTO3D_VISION_MODEL", raising=False)
    monkeypatch.delenv("DRAWINGTO3D_CODER_MODEL", raising=False)
    return install


def test_a_model_outside_the_preference_list_is_taken_when_it_is_the_one_installed(machine):
    machine(model("moondream:latest", ("vision", "completion")), SMALL_TEXT)
    assert choose_vision_model() == "moondream:latest"


def test_the_preference_order_only_breaks_ties_between_capable_models(machine):
    machine(OLDER_READER, READER, CODER)
    assert choose_vision_model() == READER.name


def test_a_text_only_machine_refuses_the_reader_instead_of_answering_an_image(machine):
    machine(SMALL_TEXT, CODER)
    with pytest.raises(UnavailableModel):
        choose_vision_model()


def test_a_server_that_does_not_report_capabilities_falls_back_to_family_names(machine):
    machine(model("llava:13b"), model("llama3.2:3b"))
    assert choose_vision_model() == "llava:13b"


def test_a_server_without_capabilities_and_without_a_reader_still_refuses(machine):
    machine(model("llama3.2:3b"), model("mistral:7b"))
    with pytest.raises(UnavailableModel):
        choose_vision_model()


def test_an_explicit_choice_is_honoured_exactly(machine, monkeypatch):
    machine(SMALL_TEXT, CODER)
    monkeypatch.setenv("DRAWINGTO3D_VISION_MODEL", "llama3.2:3b")
    assert choose_vision_model() == "llama3.2:3b"


def test_an_explicit_choice_that_is_not_installed_is_an_error_not_a_substitution(machine, monkeypatch):
    machine(SMALL_TEXT)
    monkeypatch.setenv("DRAWINGTO3D_VISION_MODEL", "gemma3:27b")
    with pytest.raises(UnavailableModel):
        choose_vision_model()


def test_any_installed_model_can_write_the_program_when_no_coder_is_installed(machine):
    machine(SMALL_TEXT)
    assert choose_text_model() == "llama3.2:3b"


def test_a_coder_is_preferred_when_the_machine_has_one(machine):
    machine(SMALL_TEXT, CODER)
    assert choose_text_model() == CODER.name


def test_the_reader_is_available_to_the_coder_when_it_is_all_there_is(machine):
    machine(READER)
    assert choose_text_model() == READER.name


def test_an_empty_machine_says_so(machine):
    machine()
    with pytest.raises(UnavailableModel):
        choose_text_model()


def test_the_clients_take_the_models_these_choices_name(machine):
    machine(READER, CODER, SMALL_TEXT)
    assert OllamaVision().model == READER.name
    assert OllamaCoder().model == CODER.name
