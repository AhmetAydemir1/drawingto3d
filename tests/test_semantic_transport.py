"""Çoklu görsel taşıması: **gerçekten serialize edilen** HTTP gövdesi üzerinde ölçüm.

Buradaki testler `urllib.request.urlopen` sınırında durur: gövdedeki base64 görseller çözülür ve
kaydedilen hash/boyut/sırayla karşılaştırılır. Yalnız `images_per_call=3` alanını doğrulamak, kaydın
kendi kendini onaylaması olurdu — ölçüm gönderilen byte'lardan yapılır.

Eski yollar (pozisyonel argümanlar, `str` dönüşü, text-only ve tek görselli çağrılar) da burada
korunuyor: bu dilim onları bozmadan genişletmek zorunda.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import urllib.error
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import llama  # noqa: E402
from drawingto3d.errors import UnavailableModel  # noqa: E402
from drawingto3d.llama import ChatSettings, OllamaChat  # noqa: E402

HOST = "http://127.0.0.1:11434"
MODEL = "qwen3-vl:8b-instruct"


class Boundary:
    """`urllib.request.urlopen` yerine geçen sahte sınır: gövdeyi yakalar, cevabı döner."""

    def __init__(self, reply: str = "cevap", *, done_reason: str = "stop", body: dict | None = None,
                 raise_error: BaseException | None = None):
        self.reply = reply
        self.done_reason = done_reason
        self.body = body
        self.raise_error = raise_error
        self.requests: list[dict] = []
        self.data: list[bytes] = []

    def __call__(self, request, timeout=None):
        self.requests.append({"url": request.full_url, "method": request.get_method(),
                              "headers": dict(request.headers), "timeout": timeout})
        self.data.append(request.data)
        if self.raise_error is not None:
            raise self.raise_error
        payload = self.body if self.body is not None else {
            "model": MODEL, "done_reason": self.done_reason,
            "message": {"role": "assistant", "content": self.reply},
            "eval_count": 12, "prompt_eval_count": 34, "total_duration": 10 ** 9,
        }
        raw = json.dumps(payload).encode()
        return _Response(raw)

    # -- yardımcılar ------------------------------------------------------

    def payload(self, index: int = 0) -> dict:
        return json.loads(self.data[index].decode())

    def sent_images(self, index: int = 0) -> list[bytes]:
        message = self.payload(index)["messages"][0]
        return [base64.standard_b64decode(item) for item in message.get("images", [])]


class _Response(io.BytesIO):
    """`json.load(response)` için gerçek dosya benzeri cevap."""

    def __init__(self, raw: bytes):
        super().__init__(raw)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def png(colour: int, width: int = 24, height: int = 16) -> bytes:
    image = np.full((height, width, 3), colour, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


@pytest.fixture
def boundary(monkeypatch):
    fake = Boundary()
    monkeypatch.setattr(llama.urllib.request, "urlopen", fake)
    return fake


def chat(**settings) -> OllamaChat:
    return OllamaChat(MODEL, settings=ChatSettings(model=MODEL, **settings))


# -- çoklu görsel ------------------------------------------------------------------


def test_three_images_are_serialised_in_order_with_measured_hashes(boundary):
    images = [png(10), png(80), png(200)]
    trace: dict = {}
    assert chat().complete("soru", images=images, trace=trace) == "cevap"

    sent = boundary.sent_images()
    assert len(sent) == 3
    assert [hashlib.sha256(item).hexdigest() for item in sent] == \
           [image["sent_sha256"] for image in trace["images"]]
    assert [len(item) for item in sent] == [image["sent_bytes"] for image in trace["images"]]
    assert sent == images, "gövdedeki byte'lar verilen görsellerin kendisi olmalı"
    assert trace["images_per_call"] == 3
    assert trace["request_sha256"] == hashlib.sha256(boundary.data[0]).hexdigest()
    assert trace["request_bytes"] == len(boundary.data[0])


def test_reversing_the_image_list_reverses_the_payload_and_the_record(boundary):
    first, second = png(10), png(200)
    forward, backward = {}, {}
    chat().complete("soru", images=[first, second], trace=forward)
    chat().complete("soru", images=[second, first], trace=backward)

    assert boundary.sent_images(0) == [first, second]
    assert boundary.sent_images(1) == [second, first]
    assert [item["sent_sha256"] for item in forward["images"]] == \
           [item["sent_sha256"] for item in reversed(backward["images"])]
    assert forward["request_sha256"] != backward["request_sha256"]


def test_the_prompt_and_the_image_list_are_the_same_prepared_data(boundary):
    """Prompt metni de gövdede; kayıtta hash'i var — ikisi tek hazırlama noktasından çıkar."""
    trace: dict = {}
    chat().complete("sıra: image-2, image-1", images=[png(10), png(20)], trace=trace)
    message = boundary.payload()["messages"][0]
    assert message["content"] == "sıra: image-2, image-1"
    assert trace["prompt_sha256"] == hashlib.sha256(message["content"].encode()).hexdigest()
    assert trace["prompt_chars"] == len(message["content"])


def test_images_and_the_old_single_image_argument_are_refused_together(boundary):
    with pytest.raises(ValueError):
        chat().complete("soru", image_png=png(10), images=[png(20)])
    assert boundary.data == [], "reddedilen çağrı gönderilmemeli"


# -- eski davranış ---------------------------------------------------------------


def test_a_text_only_call_carries_no_image_and_records_zero(boundary):
    trace: dict = {}
    assert chat().complete("merhaba", trace=trace) == "cevap"
    assert "images" not in boundary.payload()["messages"][0]
    assert trace["images_per_call"] == 0 and trace["images"] == []


def test_an_empty_image_list_is_an_explicit_text_only_request(boundary):
    trace: dict = {}
    chat().complete("merhaba", images=[], trace=trace)
    assert "images" not in boundary.payload()["messages"][0]
    assert trace["images_per_call"] == 0


def test_one_image_still_travels_the_old_way(boundary):
    trace: dict = {}
    single = png(30)
    chat().complete("soru", image_png=single, trace=trace)
    assert boundary.sent_images() == [single]
    assert trace["images_per_call"] == 1
    assert trace["images"][0]["source_sha256"] == hashlib.sha256(single).hexdigest()


def test_positional_arguments_and_the_string_return_are_unchanged(boundary):
    """`_ollama_chat` imzası: eski çağrı biçimi bozulmadan çalışıyor."""
    reply = llama._ollama_chat(HOST, MODEL, "soru", png(40), 30.0, 128)
    assert reply == "cevap"
    assert boundary.sent_images() == [png(40)] or boundary.sent_images()[0]


# -- ayarlar gerçekten uygulanıyor ------------------------------------------------


def test_non_default_settings_reach_the_request_and_the_record(boundary):
    trace: dict = {}
    chat(keep_alive="30m", num_ctx=8192, num_predict=77, temperature=0.9).complete(
        "soru", images=[png(10)], num_predict=55, trace=trace)

    payload = boundary.payload()
    assert payload["keep_alive"] == "30m"
    assert payload["options"] == {"temperature": 0.9, "num_predict": 55, "num_ctx": 8192}
    assert trace["keep_alive"] == "30m"
    assert trace["options"] == payload["options"]


def test_a_declared_resize_limit_is_really_applied(boundary):
    large = png(10, 600, 400)
    trace: dict = {}
    chat(image_max_side=200).complete("soru", images=[large], trace=trace)

    sent = boundary.sent_images()[0]
    assert sent != large and len(sent) < len(large)
    decoded = cv2.imdecode(np.frombuffer(sent, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert max(decoded.shape[:2]) == 200
    entry = trace["images"][0]
    assert entry["resize"]["applied"] is True
    assert entry["resize"]["from_px"] == [600, 400] and entry["resize"]["to_px"] == [200, 133]
    assert entry["source_sha256"] == hashlib.sha256(large).hexdigest()
    assert entry["sent_sha256"] == hashlib.sha256(sent).hexdigest()


def test_no_declared_limit_means_no_resize_and_the_record_says_so(boundary):
    trace: dict = {}
    chat().complete("soru", images=[png(10, 600, 400)], trace=trace)
    entry = trace["images"][0]
    assert entry["resize"]["max_side"] is None and entry["resize"]["applied"] is False
    assert entry["resize"]["interpolation"] is None
    # Kırpma/ölçekleme olmasa da boyut, gidecek byte'lardan ölçülür: kayıt "ölçülmedi" demez.
    assert entry["resize"]["from_px"] == [600, 400] and entry["resize"]["to_px"] == [600, 400]
    assert (entry["sent_width_px"], entry["sent_height_px"]) == (600, 400)


def test_a_json_schema_response_format_is_reported_as_such(boundary):
    trace: dict = {}
    schema = {"type": "object"}
    chat().complete("soru", response_format=schema, stats={}, trace=trace)
    assert boundary.payload()["format"] == schema
    assert trace["response_format"] == "json-schema"


def test_a_text_response_format_is_reported_as_text(boundary):
    trace: dict = {}
    chat().complete("soru", trace=trace)
    assert trace["response_format"] == "text" and "format" not in boundary.payload()


# -- hata katmanları --------------------------------------------------------------


def test_an_http_rejection_names_its_layer(monkeypatch):
    error = urllib.error.HTTPError(HOST + "/api/chat", 500, "boom", {},
                                   io.BytesIO("patladı".encode()))
    monkeypatch.setattr(llama.urllib.request, "urlopen", Boundary(raise_error=error))
    trace: dict = {}
    with pytest.raises(UnavailableModel) as raised:
        chat().complete("soru", trace=trace)
    assert getattr(raised.value, "transport_kind") == "http_error"
    assert "500" in str(raised.value) and "patladı" in str(raised.value)
    assert trace["outcome"] == "http_error" and trace["http_status"] == 500


def test_a_timeout_is_not_reported_as_a_missing_server(monkeypatch):
    monkeypatch.setattr(llama.urllib.request, "urlopen",
                        Boundary(raise_error=TimeoutError("çok yavaş")))
    trace: dict = {}
    with pytest.raises(UnavailableModel) as raised:
        chat().complete("soru", trace=trace)
    assert getattr(raised.value, "transport_kind") == "timeout"
    assert trace["outcome"] == "timeout"


def test_an_empty_answer_keeps_the_raw_body_and_names_the_layer(monkeypatch):
    monkeypatch.setattr(llama.urllib.request, "urlopen",
                        Boundary(reply="", body={"done_reason": "stop", "message": {"content": "  "},
                                                 "eval_count": 1}))
    raw: dict = {}
    with pytest.raises(UnavailableModel) as raised:
        chat().complete("soru", raw_response=raw)
    assert getattr(raised.value, "transport_kind") == "empty_content"
    assert raw["done_reason"] == "stop", "boş içerikte de ham gövde saklanmalı"


def test_a_broken_body_is_reported_as_unreachable_not_as_an_answer(monkeypatch):
    monkeypatch.setattr(llama.urllib.request, "urlopen", _BrokenBody())
    trace: dict = {}
    with pytest.raises(UnavailableModel) as raised:
        chat().complete("soru", trace=trace)
    assert getattr(raised.value, "transport_kind") == "unreachable"
    assert trace["outcome"] == "unreachable"


def test_a_missing_server_is_unreachable(monkeypatch):
    monkeypatch.setattr(llama.urllib.request, "urlopen",
                        Boundary(raise_error=urllib.error.URLError("bağlantı yok")))
    with pytest.raises(UnavailableModel) as raised:
        chat().complete("soru")
    assert getattr(raised.value, "transport_kind") == "unreachable"


class _BrokenBody:
    def __call__(self, request, timeout=None):
        return _Response(b"bu json degil")


def test_truncation_is_reported_from_done_reason(monkeypatch):
    monkeypatch.setattr(llama.urllib.request, "urlopen",
                        Boundary(reply='{"items":', done_reason="length"))
    trace: dict = {}
    assert chat().complete("soru", trace=trace) == '{"items":'
    assert trace["done_reason"] == "length"


def test_the_transport_still_refuses_a_non_local_host():
    with pytest.raises(UnavailableModel):
        OllamaChat(MODEL, host="https://api.example.com")


# -- çerçeveleme: tek mesaj ya da görsel başına mesaj ---------------------------------


def _decoded_images(payload: dict) -> list[bytes]:
    found = []
    for message in payload["messages"]:
        for item in message.get("images") or []:
            found.append(base64.standard_b64decode(item))
    return found


def test_the_per_image_layout_sends_one_message_per_image_without_extra_text(boundary):
    """Görsel başına bir mesaj: sıra korunur, görsel mesajlarına metin eklenmez (ipucu yok)."""
    first, second = png(0), png(255)
    trace: dict = {}
    chat(images_layout="per_image_message").complete("soru", images=[first, second],
                                                     image_labels=["image-2", "image-1"], trace=trace)
    payload = boundary.payload()
    assert len(payload["messages"]) == 3, "iki görsel + istem: üç mesaj"
    assert [message["content"] for message in payload["messages"]] == ["", "", "soru"]
    assert _decoded_images(payload) == [first, second], "gönderim sırası korunmalı"
    assert all(len(message["images"]) == 1 for message in payload["messages"][:2])
    assert "images" not in payload["messages"][-1]
    # Kayıt çerçevelemeyi ve hangi kimliğin hangi mesajda gittiğini söyler.
    assert trace["images_layout"] == "per_image_message"
    assert [entry["image_ids"] for entry in trace["messages_layout"]] == [["image-2"], ["image-1"]]
    assert [entry["image_id"] for entry in trace["images"]] == ["image-2", "image-1"]


def test_the_single_message_layout_is_the_default_and_is_named_in_the_record(boundary):
    first, second = png(0), png(255)
    trace: dict = {}
    chat().complete("soru", images=[first, second], image_labels=["image-1", "image-2"], trace=trace)
    payload = boundary.payload()
    assert len(payload["messages"]) == 1 and payload["messages"][0]["content"] == "soru"
    assert _decoded_images(payload) == [first, second]
    assert trace["images_layout"] == "single_message"
    assert trace["messages_layout"] == [{"index": 0, "image_ids": ["image-1", "image-2"]}]


def test_one_image_makes_the_two_layouts_identical(boundary):
    """Tek görselde çerçeveleme farkı anlamsızdır: gereksiz mesaj üretilmez."""
    single: dict = {}
    chat(images_layout="single_message").complete("soru", images=[png(0)], trace=single)
    per_image: dict = {}
    chat(images_layout="per_image_message").complete("soru", images=[png(0)], trace=per_image)
    assert single["request_sha256"] == per_image["request_sha256"]
    assert len(boundary.payload()["messages"]) == 1


def test_an_unknown_layout_is_refused_instead_of_sent(boundary):
    with pytest.raises(ValueError):
        chat(images_layout="iki-mesaj").complete("soru", images=[png(0)])
    assert boundary.requests == [], "bilinmeyen çerçeveleme gönderilmeden reddedilmeli"


# -- etiketli çerçeveleme: nötr kimlik görselin kendi mesajında -----------------------


def test_the_labeled_layout_puts_each_neutral_id_in_its_own_image_message(boundary):
    """Gövde çözülerek ölçülür: kimlik ↔ mesaj ↔ byte bağı kaydın beyanından değil, gövdeden gelir."""
    first, second = png(10), png(240)
    trace: dict = {}
    chat(images_layout="per_image_message_labeled").complete(
        "soru", images=[first, second], image_labels=["image-2", "image-1"],
        image_label_prefix="Image ID: ", trace=trace)

    payload = boundary.payload()
    assert [message["content"] for message in payload["messages"]] == \
           ["Image ID: image-2", "Image ID: image-1", "soru"], "kimlik kendi mesajında olmalı"
    assert len(payload["messages"]) == 3
    assert all(len(message["images"]) == 1 for message in payload["messages"][:2])
    assert "images" not in payload["messages"][-1], "istenen son mesaj görsel taşımaz"
    # Byte'ların kendisi çözülür: kayıttaki id ile o mesajın byte'ı aynı görsele ait.
    assert _decoded_images(payload) == [first, second]
    assert base64.standard_b64decode(payload["messages"][0]["images"][0]) == first
    assert base64.standard_b64decode(payload["messages"][1]["images"][0]) == second
    assert trace["images_layout"] == "per_image_message_labeled"
    assert [entry["image_id"] for entry in trace["images"]] == ["image-2", "image-1"]
    assert [entry["label"] for entry in trace["messages_layout"]] == ["Image ID: image-2",
                                                                      "Image ID: image-1"]
    assert [entry["image_ids"] for entry in trace["messages_layout"]] == [["image-2"], ["image-1"]]
    assert trace["request_sha256"] == hashlib.sha256(boundary.data[0]).hexdigest()


def test_the_labeled_layout_follows_a_reversed_declared_order_in_the_body(boundary):
    first, second = png(10), png(240)
    trace: dict = {}
    chat(images_layout="per_image_message_labeled").complete(
        "1. image-2\\n2. image-1", images=[second, first], image_labels=["image-2", "image-1"],
        image_label_prefix="Image ID: ", trace=trace)
    payload = boundary.payload()
    assert [message["content"] for message in payload["messages"][:2]] == ["Image ID: image-2",
                                                                          "Image ID: image-1"]
    assert _decoded_images(payload) == [second, first], "sıra ile kimlik ayrışmamalı"


def test_identical_bytes_under_different_ids_keep_their_own_message(boundary):
    """Aynı byte'lar iki ayrı kimlikle giderse kimlikler birleştirilmez; hash→ID eşlemesi varsayılmaz."""
    same = png(77)
    trace: dict = {}
    chat(images_layout="per_image_message_labeled").complete(
        "soru", images=[same, same], image_labels=["image-11", "image-27"],
        image_label_prefix="Image ID: ", trace=trace)
    payload = boundary.payload()
    assert [message["content"] for message in payload["messages"][:2]] == ["Image ID: image-11",
                                                                          "Image ID: image-27"]
    assert [entry["image_id"] for entry in trace["images"]] == ["image-11", "image-27"]
    assert trace["images"][0]["sent_sha256"] == trace["images"][1]["sent_sha256"]


@pytest.mark.parametrize("kwargs, reason", [
    ({"image_labels": None}, "etiketsiz"),
    ({"image_labels": ["image-1"]}, "uzunluk"),
    ({"image_labels": ["image-1", "image-1"]}, "tekrar"),
    ({"image_labels": ["image-1", "  "]}, "boş"),
])
def test_the_labeled_layout_refuses_bad_labels_before_sending(boundary, kwargs, reason):
    with pytest.raises(ValueError):
        chat(images_layout="per_image_message_labeled").complete(
            "soru", images=[png(0), png(30)], image_label_prefix="Image ID: ", **kwargs)
    assert boundary.requests == [], f"{reason} etiket istek öncesi reddedilmeli"


def test_the_labeled_layout_needs_the_neutral_prefix(boundary):
    with pytest.raises(ValueError):
        chat(images_layout="per_image_message_labeled").complete(
            "soru", images=[png(0)], image_labels=["image-1"])
    assert boundary.requests == []
