"""Adapter sınırındaki çağrı kaydı: kanıt dosyada, açıklama cümlesinde değil."""

import json

import pytest

from drawingto3d import llama
from drawingto3d.inference_log import (
    RecordedChat,
    RecordedCoder,
    RecordedVision,
    Recorder,
    read_record,
)


def test_the_recorder_counts_calls_and_whether_an_image_went(tmp_path):
    recorder = Recorder(tmp_path / "inference-log.json", label="deneme")
    # The evidence file exists from the start and says "no calls yet": "no evidence" and "no calls" must
    # not look the same in a record.
    assert read_record(recorder.path)["calls"] == 0

    recorder.note("chat", image_sent=False, prompt_chars=120)
    recorder.note("chat", image_sent=True, image_bytes=4096, prompt_chars=200)

    record = read_record(recorder.path)
    assert record["schema"] == "drawingto3d.inference-log/1"
    assert record["calls"] == 2 and record["inference_called"] is True
    assert record["image_sent"] is True
    assert [call["image_sent"] for call in record["calls_detail"]] == [False, True]
    assert record["note"] == "deneme"


def test_a_record_without_calls_says_so(tmp_path):
    recorder = Recorder(tmp_path / "inference-log.json")
    recorder.write()

    record = read_record(recorder.path)
    assert record["calls"] == 0 and record["inference_called"] is False
    assert record["image_sent"] is False, "çağrı yokken görüntü gitti denemez"


def test_the_wrapper_keeps_the_adapter_type():
    """`reason._ask` çağrıyı isinstance ile seçiyor: sarmalayıcı tipi bozmamalı."""
    assert issubclass(RecordedChat, llama.OllamaChat)
    assert issubclass(RecordedVision, llama.OllamaVision)
    assert issubclass(RecordedCoder, llama.OllamaCoder)


def test_a_chat_call_is_recorded_at_the_adapter_boundary(tmp_path, monkeypatch):
    """Çağrı kanıtı: iç adapter ne aldıysa kayda o yazılır."""
    seen = {}

    def fake_init(self, model, *args, **kwargs):
        self.settings = llama.ChatSettings(model=model)

    def fake_complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None):
        seen.update({"prompt": prompt, "image_png": image_png, "num_predict": num_predict})
        return "cevap"

    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    chat = RecordedChat("qwen3-vl:8b-instruct", recorder=recorder)
    assert chat.complete("ölçüleri oku", image_png=b"png-bytes", num_predict=64) == "cevap"

    assert seen["image_png"] == b"png-bytes", "görüntü iç adapter'a gerçekten gitmeli"
    record = read_record(recorder.path)
    assert record["calls"] == 1 and record["image_sent"] is True
    assert record["models"]["chat"]["model"] == "qwen3-vl:8b-instruct"
    assert record["calls_detail"][0]["image_bytes"] == len(b"png-bytes")


def test_a_failed_call_is_recorded_and_the_error_still_travels(tmp_path, monkeypatch):
    """Düşen çağrı da kanıttır; sarmalayıcı hatayı yutmaz."""

    def fake_init(self, model, *args, **kwargs):
        self.settings = llama.ChatSettings(model=model)

    def fake_complete(self, prompt, **kwargs):
        raise RuntimeError("ollama yok")

    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    with pytest.raises(RuntimeError):
        RecordedChat("qwen3-vl:8b-instruct", recorder=recorder).complete("oku")

    record = json.loads(recorder.path.read_text())
    assert record["calls"] == 1 and record["calls_detail"][0]["ok"] is False
    assert "ollama yok" in record["calls_detail"][0]["error"]


def test_a_coder_call_records_that_no_image_went(tmp_path, monkeypatch):
    def fake_init(self, *args, **kwargs):
        self.model = "qwen2.5-coder:7b"

    def fake_complete(self, prompt):
        return "geo.program"

    monkeypatch.setattr(llama.OllamaCoder, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaCoder, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    assert RecordedCoder(recorder=recorder).complete("kod yaz") == "geo.program"

    record = read_record(recorder.path)
    assert record["calls"] == 1 and record["image_sent"] is False
    assert record["kinds"] == ["coder"]
