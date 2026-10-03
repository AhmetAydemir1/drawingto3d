"""Adapter sınırındaki çağrı kaydı: kanıt dosyada, açıklama cümlesinde değil.

T02'nin iki kuralı burada sınanır: çağrı **dönmeden önce** yazılmalı (kesilen bir çağrı "hiç çağrı
yok" gibi görünmemeli) ve dosya **atomik** değişmeli (yarım JSON okunmamalı).
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from drawingto3d import llama
from drawingto3d.inference_log import (
    RecordedChat,
    RecordedCoder,
    RecordedLlamaCoder,
    RecordedVision,
    Recorder,
    merge_records,
    read_record,
)

SCHEMA = "drawingto3d.inference-log/2"


def _fake_chat(model: str, reply: str = "cevap", error: Exception | None = None):
    def fake_init(self, model, *args, **kwargs):
        self.settings = llama.ChatSettings(model=model)

    def fake_complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None):
        if error is not None:
            raise error
        return reply

    return fake_init, fake_complete


def test_the_recorder_counts_attempts_and_whether_an_image_was_attached(tmp_path):
    recorder = Recorder(tmp_path / "inference-log.json", label="deneme")
    # The evidence file exists from the start and says "no calls yet": "no evidence" and "no calls" must
    # not look the same in a record.
    assert read_record(recorder.path)["attempts"] == 0
    assert read_record(recorder.path)["inference_called"] is False

    recorder.note("chat", image_attached=False, prompt_chars=120)
    recorder.note("chat", image_attached=True, image_bytes=4096, prompt_chars=200)

    record = read_record(recorder.path)
    assert record["schema"] == SCHEMA
    assert record["attempts"] == 2 and record["completed"] == 2 and record["unfinished"] == 0
    assert record["image_attached"] is True and record["server_ok"] is True
    assert [call["image_attached"] for call in record["calls"]] == [False, True]
    assert record["note"] == "deneme"


def test_a_record_without_calls_says_so(tmp_path):
    recorder = Recorder(tmp_path / "inference-log.json")
    recorder.write()

    record = read_record(recorder.path)
    assert record["attempts"] == 0 and record["inference_called"] is False
    assert record["image_attached"] is False, "çağrı yokken görüntü gitti denemez"
    assert record["unfinished"] == 0


def test_the_wrapper_keeps_the_adapter_type():
    """`reason._ask` çağrıyı isinstance ile seçiyor: sarmalayıcı tipi bozmamalı."""
    assert issubclass(RecordedChat, llama.OllamaChat)
    assert issubclass(RecordedVision, llama.OllamaVision)
    assert issubclass(RecordedCoder, llama.OllamaCoder)
    assert issubclass(RecordedLlamaCoder, llama.LlamaCoder)


def test_a_chat_call_is_recorded_at_the_adapter_boundary(tmp_path, monkeypatch):
    """Çağrı kanıtı: iç adapter ne aldıysa kayda o yazılır."""
    seen = {}
    fake_init, _ = _fake_chat("qwen3-vl:8b-instruct")

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
    assert record["attempts"] == 1 and record["image_attached"] is True
    assert record["calls"][0]["state"] == "completed" and record["calls"][0]["server_ok"] is True
    assert record["models"]["chat"]["model"] == "qwen3-vl:8b-instruct"
    assert record["calls"][0]["image_bytes"] == len(b"png-bytes")


def test_a_failed_call_is_recorded_and_the_error_still_travels(tmp_path, monkeypatch):
    """Düşen çağrı da kanıttır; sarmalayıcı hatayı yutmaz."""
    fake_init, fake_complete = _fake_chat("qwen3-vl:8b-instruct", error=RuntimeError("ollama yok"))
    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    with pytest.raises(RuntimeError):
        RecordedChat("qwen3-vl:8b-instruct", recorder=recorder).complete("oku")

    record = json.loads(recorder.path.read_text())
    assert record["attempts"] == 1 and record["failed"] == 1
    assert record["calls"][0]["state"] == "failed"
    assert "ollama yok" in record["calls"][0]["error"]


def test_a_coder_call_records_that_no_image_was_attached(tmp_path, monkeypatch):
    def fake_init(self, *args, **kwargs):
        self.model = "qwen2.5-coder:7b"

    def fake_complete(self, prompt):
        return "geo.program"

    monkeypatch.setattr(llama.OllamaCoder, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaCoder, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    assert RecordedCoder(recorder=recorder).complete("kod yaz") == "geo.program"

    record = read_record(recorder.path)
    assert record["attempts"] == 1 and record["image_attached"] is False
    assert record["kinds"] == ["coder"]


def test_an_interrupted_call_does_not_look_like_no_call_at_all(tmp_path):
    """Kesilen çağrı: kayıt çağrı **başlamadan önce** yazıldığı için `unfinished` olarak okunur.

    Süreç, çağrı dönerken değil **tam çağrı içindeyken** öldürülür (gerçek alt süreç, gerçek kill);
    önceki sürüm yalnız dönüşte yazdığı için bu durum kayıtta `calls: 0` görünüyordu — yani "kesildi"
    ile "hiç çağrılmadı" karışıyordu.
    """
    path = tmp_path / "inference-log.json"
    child = f'''
import sys, time
sys.path.insert(0, {str(Path(__file__).resolve().parents[1] / "src")!r})
from drawingto3d import llama
from drawingto3d.inference_log import RecordedChat, Recorder

def fake_init(self, model, *args, **kwargs):
    self.settings = llama.ChatSettings(model=model)

def fake_complete(self, prompt, **kwargs):
    time.sleep(120)
    return "hiç dönmeyecek"

llama.OllamaChat.__init__ = fake_init
llama.OllamaChat.complete = fake_complete
RecordedChat("qwen3-vl:8b-instruct", recorder=Recorder({str(path)!r}, label="kesilen çağrı")).complete("oku")
'''
    process = subprocess.Popen([sys.executable, "-c", child])
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            record = read_record(path)
            if record and record.get("attempts") == 1:
                break
            time.sleep(0.2)
        else:  # pragma: no cover - alt süreç hiç yazmadıysa test başarısız olmalı
            raise AssertionError("alt süreç çağrı kaydını yazmadı")
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:  # pragma: no cover
            process.kill()

    record = read_record(path)
    assert record["attempts"] == 1, "kesilen çağrı sayılmış olmalı"
    assert record["unfinished"] == 1 and record["completed"] == 0
    assert record["inference_called"] is True, "'kesildi' ile 'hiç çağrı yok' karışmamalı"
    assert record["calls"][0]["state"] == "started"
    assert record["calls"][0]["image_attached"] is False
    assert record["image_attached"] is False, "görüntü gitmediyse gitmiş gibi yazılmamalı"


def test_a_multi_image_call_is_never_recorded_as_image_less(tmp_path, monkeypatch):
    """Çoklu görsel çağrısı (SEMREAD-001A): kayıt görselleri saymalı, "görüntü yok" yazmamalı."""
    seen = {}

    def fake_init(self, model, *args, **kwargs):
        self.settings = llama.ChatSettings(model=model)

    def fake_complete(self, prompt, image_png=None, num_predict=None, response_format=None,
                      stats=None, *, images=None, trace=None, raw_response=None):
        seen.update({"image_png": image_png, "images": images})
        return "cevap"

    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    chat = RecordedChat("qwen3-vl:8b-instruct", recorder=recorder)
    assert chat.complete("üç görsel", images=[b"a" * 10, b"b" * 20, b"c" * 30]) == "cevap"

    assert seen["image_png"] is None and seen["images"] == [b"a" * 10, b"b" * 20, b"c" * 30]
    record = read_record(recorder.path)
    call = record["calls"][0]
    assert call["image_attached"] is True and call["images_in_request"] == 3
    assert call["image_bytes"] == 60
    assert record["images_in_request"] == 3 and record["image_attached"] is True


def test_a_text_only_call_records_zero_images(tmp_path, monkeypatch):
    fake_init, fake_complete = _fake_chat("qwen3-vl:8b-instruct")
    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    RecordedChat("qwen3-vl:8b-instruct", recorder=recorder).complete("sadece metin")

    call = read_record(recorder.path)["calls"][0]
    assert call["image_attached"] is False and call["images_in_request"] == 0 and call["image_bytes"] == 0


def test_a_single_image_call_still_counts_as_one(tmp_path, monkeypatch):
    fake_init, fake_complete = _fake_chat("qwen3-vl:8b-instruct")
    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", fake_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    RecordedChat("qwen3-vl:8b-instruct", recorder=recorder).complete("oku", image_png=b"png")

    call = read_record(recorder.path)["calls"][0]
    assert call["image_attached"] is True and call["images_in_request"] == 1
    assert call["image_bytes"] == len(b"png")


def test_a_rejected_conflicting_call_is_still_recorded_as_failed(tmp_path, monkeypatch):
    """`image_png` + `images` birlikte verilirse iç adapter hata verir; kayıt bunu `failed` yazar."""
    fake_init, _ = _fake_chat("qwen3-vl:8b-instruct")

    def refusing_complete(self, prompt, image_png=None, num_predict=None, response_format=None,
                          stats=None, *, images=None, **kwargs):
        if image_png is not None and images is not None:
            raise ValueError("image_png ile images birlikte verilemez")
        return "cevap"

    monkeypatch.setattr(llama.OllamaChat, "__init__", fake_init)
    monkeypatch.setattr(llama.OllamaChat, "complete", refusing_complete)

    recorder = Recorder(tmp_path / "inference-log.json")
    with pytest.raises(ValueError):
        RecordedChat("qwen3-vl:8b-instruct", recorder=recorder).complete(
            "oku", image_png=b"png", images=[b"png2"])

    record = read_record(recorder.path)
    assert record["failed"] == 1 and record["calls"][0]["state"] == "failed"
    assert "birlikte verilemez" in record["calls"][0]["error"]


def test_the_record_is_replaced_atomically(tmp_path):
    """Yazım yanına yazıp `os.replace` ile yerine koyar: yarım JSON kalmaz, `.tmp` sızmaz."""
    recorder = Recorder(tmp_path / "inference-log.json", label="atomik")
    recorder.started("chat", image_attached=True, image_bytes=10, prompt_chars=5)

    assert not list(tmp_path.glob("*.tmp")), "geçici dosya kalmamalı"
    record = json.loads(recorder.path.read_text())
    assert record["calls"][0]["state"] == "started"


def test_merging_step_records_keeps_every_command_s_own_calls():
    """İki komut iki dosya yazar; özet ikisini de sayar (T01: paylaşılan yol kanıtı eziyordu)."""
    merged = merge_records([
        {"calls": [{"kind": "vision", "state": "completed", "image_attached": True, "server_ok": True}],
         "models": {"vision": {"kind": "vision", "model": "qwen2.5vl:3b"}}},
        {"calls": [{"kind": "coder", "state": "completed", "image_attached": False, "server_ok": True}],
         "models": {"coder": {"kind": "coder", "model": "qwen2.5-coder:7b"}}},
    ])

    assert merged["attempts"] == 2 and merged["records"] == 2
    assert merged["image_attached"] is True, "görüntü taşıyan çağrı birleşimde kaybolmamalı"
    assert merged["kinds"] == ["coder", "vision"]
    assert set(merged["models"]) == {"vision", "coder"}
