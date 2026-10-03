"""Okuyucu: gönderilen paket, ayrı hata katmanları ve terk edilen semantik iddialar.

Okuyucunun işi taşıma ve sözleşmedir. Burada ölçülen: ham yanıt her durumda korunuyor mu, bozuk JSON
tamir edilmiyor mu, şema/referans negatifleri ayrı ayrı düşüyor mu, bölge kaynağa çözülüyor mu ve
prompt'taki kimlik/sıra eşlemesi görsel paketiyle aynı yerden mi geliyor.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.errors import UnavailableModel  # noqa: E402
from drawingto3d.semantic_reader import SemanticReader, leak_check, probe_prompt  # noqa: E402
from drawingto3d.semantic_schema import ImageBundle, PreparedImage  # noqa: E402


def png(colour: int = 200, width: int = 12, height: int = 8) -> bytes:
    image = np.full((height, width, 3), colour, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def prepared(image_id: str, colour: int = 200, **kwargs) -> PreparedImage:
    base = dict(image_id=image_id, kind="full_page", png=png(colour), source_sha256="a" * 64,
                render_mode="pdf_rerender", render_dpi=200.0)
    base.update(kwargs)
    return PreparedImage(**base)


class FakeChat:
    """Sohbet adapter'ının yerine geçer: verilen yanıtı döner, isteği kaydeder."""

    model = "qwen3-vl:8b-instruct"

    def __init__(self, answer: str = "", *, error: BaseException | None = None,
                 raw_body: dict | None = None):
        self.answer = answer
        self.error = error
        self.raw_body = raw_body or {}
        self.calls: list[dict] = []

    def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None, *,
                 images=None, trace=None, raw_response=None, image_labels=None,
                 images_layout=None, image_label_prefix=""):
        assert images_layout in (None, "single_message", "per_image_message",
                                 "per_image_message_labeled"), \
            "okuyucu yalnız tanımlı çerçevelemeleri geçmeli"
        assert image_label_prefix in ("", "Image ID: "), "etiket metni nötr kimlik olmalı"
        assert image_png is None, "okuyucu görselleri liste olarak göndermeli"
        # Etiketler prompt'un ilan ettiği sırayla birebir aynı olmalı: kimlik↔sıra tek kaynak.
        listed = re.findall(r"^\s+\d+\. (\S+)$", prompt, flags=re.MULTILINE)
        assert image_labels == listed, f"etiketler prompt sırasıyla uyuşmalı: {image_labels} != {listed}"
        assert len(images or []) == len(image_labels or []), "byte sayısı ile etiket sayısı eşit olmalı"
        self.calls.append({"prompt": prompt, "images": list(images or []),
                           "num_predict": num_predict, "response_format": response_format,
                           "image_labels": list(image_labels or []),
                           "images_layout": images_layout,
                           "image_label_prefix": image_label_prefix,
                           "stats": stats})
        if stats is not None:
            stats.update({"done_reason": "stop", "eval_count": 5, "prompt_eval_count": 7})
        if trace is not None:
            trace.update({"schema": "drawingto3d.chat-request/1", "model": self.model,
                          "images_per_call": len(images or []),
                          "images": [{"index": index, "sent_sha256": "0" * 8, "sent_bytes": 1,
                                      "resize": {"applied": False}} for index in range(len(images or []))],
                          "request_sha256": "1" * 64, "prompt_sha256": "2" * 64,
                          "prompt_chars": len(prompt), "options": {"temperature": 0.0},
                          "outcome": "ok"})
        if raw_response is not None:
            raw_response.update(self.raw_body or {"message": {"content": self.answer},
                                                  "done_reason": "stop"})
        if self.error is not None:
            raise self.error
        return self.answer


def response_for(*items) -> str:
    return json.dumps({"schema_version": "semread-probe/2", "items": list(items)})


def item(image_id: str, region=(0.1, 0.2, 0.5, 0.6), description: str = "kısa gözlem",
         shape: str = "triangle") -> dict:
    return {"image_id": image_id, "description": description, "shape": shape,
            "region": None if region is None else
            {"x0": region[0], "y0": region[1], "x1": region[2], "y1": region[3]}}


@pytest.fixture
def bundle() -> ImageBundle:
    return ImageBundle([prepared("image-1", 10), prepared("image-2", 200)])


# -- mutlu yol --------------------------------------------------------------


def test_a_valid_answer_passes_every_gate(bundle):
    chat = FakeChat(response_for(item("image-1"), item("image-2", region=None)))
    outcome = SemanticReader(chat).probe(bundle)

    assert outcome["outcome"] == "ok" and outcome["failure_kind"] is None
    assert outcome["parse"]["ok"] and outcome["schema"]["ok"] and outcome["reference"]["ok"]
    assert outcome["reference"]["referenced_image_ids"] == ["image-1", "image-2"]
    assert outcome["regions_page_norm"][0] == [0.1, 0.2, 0.5, 0.6]
    assert outcome["regions_page_norm"][1] is None
    assert outcome["truncated"]["state"] == "complete"
    assert outcome["truncated"]["metadata_complete"] is True
    assert outcome["truncated"]["done_reason"] == "stop"
    assert outcome["leakage"] == []


def test_the_reader_sends_the_bundle_images_in_order_with_a_schema(bundle):
    chat = FakeChat(response_for(item("image-1"), item("image-2")))
    SemanticReader(chat).probe(bundle)
    call = chat.calls[0]
    assert call["images"] == bundle.pngs
    assert call["response_format"]["properties"]["schema_version"]["enum"] == ["semread-probe/2"]
    assert "image-1" in call["prompt"] and "image-2" in call["prompt"]
    assert call["image_label_prefix"] == "Image ID: ", "etiketli düzen için nötr kimlik metni geçmeli"


def test_the_reader_refuses_an_answer_that_leaves_a_sent_image_unanswered(bundle):
    chat = FakeChat(response_for(item("image-1")))
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["failure_kind"] == "reference_error"
    assert "image-2" in outcome["failure_detail"]
    assert outcome["raw_response"] == chat.answer, "kapsam hatasında ham yanıt korunur"


def test_the_reader_refuses_an_answer_that_repeats_a_sent_image(bundle):
    chat = FakeChat(response_for(item("image-1"), item("image-1")))
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["failure_kind"] == "reference_error"
    assert "tekrarlanan" in outcome["failure_detail"]


def test_an_answer_with_unknown_shape_is_a_valid_contract_but_not_a_visual_success(bundle):
    """`unknown` şema ve kapsam açısından geçerlidir; görsel kontrol kararı evaluator'ın işidir."""
    chat = FakeChat(response_for(item("image-1", shape="unknown"), item("image-2", shape="unknown")))
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["outcome"] == "ok"
    assert [row["shape"] for row in outcome["reference"]["checks"]] == ["unknown", "unknown"]


def test_a_region_in_a_crop_is_resolved_to_the_page_frame():
    crop = prepared("image-1", kind="crop", source_bbox_page_norm=(0.2, 0.4, 0.6, 0.8),
                    render_mode="pdf_rerender", render_dpi=600.0)
    chat = FakeChat(response_for(item("image-1", region=(0.0, 0.5, 0.5, 1.0))))
    outcome = SemanticReader(chat).probe(ImageBundle([crop]))
    assert outcome["regions_page_norm"][0] == pytest.approx([0.2, 0.6, 0.4, 0.8])
    assert outcome["reference"]["checks"][0]["has_region"] is True


# -- kimlik / sıra eşlemesi --------------------------------------------------


def test_reversing_the_payload_order_updates_the_prompt_and_keeps_identities(bundle):
    forward = FakeChat(response_for(item("image-1"), item("image-2")))
    backward = FakeChat(response_for(item("image-1"), item("image-2")))
    SemanticReader(forward).probe(bundle)
    reversed_bundle = ImageBundle(list(bundle.images), order=["image-2", "image-1"])
    SemanticReader(backward).probe(reversed_bundle)

    assert forward.calls[0]["images"] == list(bundle.pngs)
    assert backward.calls[0]["images"] == list(reversed(bundle.pngs))
    assert "1. image-1" in forward.calls[0]["prompt"]
    assert "1. image-2" in backward.calls[0]["prompt"]
    assert forward.calls[0]["prompt"] != backward.calls[0]["prompt"]
    # Kimlik görselle kalır: aynı görsel her iki pakette de aynı kimlikle listelenir.
    assert backward.calls[0]["images"][0] == bundle.by_id("image-2").png
    # Etiket listesi de paketin sırasıyla aynı yerden gelir: sıra ile kimlik ayrışamaz.
    assert forward.calls[0]["image_labels"] == ["image-1", "image-2"]
    assert backward.calls[0]["image_labels"] == ["image-2", "image-1"]


def test_the_prompt_lists_the_class_options_without_saying_which_image_has_which(bundle):
    """Sınıf seçenekleri prompt'ta vardır; ama hiçbir kimliğe bağlanmaz (cevap verilmez)."""
    prompt = probe_prompt(bundle)
    for word in ("hole", "delik", "pocket", "drawing.pdf", "plate"):
        assert word not in prompt
    for shape in ("triangle", "square", "circle", "other", "unknown"):
        assert shape in prompt, f"sınıf seçeneği sunulmalı: {shape}"
    # Kimlik ile bir sınıf aynı satırda/imada geçemez: bu, cevabı vermek olurdu.
    assert re.search(r"image-\d+[^\n]*(triangle|square|circle)", prompt) is None
    # Prompt hangi çerçevelemenin kullanıldığını söylemez: o bilgi kaydın işidir.
    assert "single_message" not in prompt and "per_image_message" not in prompt


# -- hata katmanları -------------------------------------------------------


def test_a_broken_json_answer_is_kept_as_raw_and_not_repaired(bundle):
    chat = FakeChat('{"schema_version": "semread-probe/1", "items": [}')
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["outcome"] == "error" and outcome["failure_kind"] == "parse_error"
    assert outcome["raw_response"] == chat.answer
    assert outcome["parse"]["ok"] is False and outcome["schema"]["ok"] is False
    assert "parsed" not in outcome


def test_a_schema_violation_is_not_a_reference_error(bundle):
    chat = FakeChat(response_for({"image_id": "image-1", "description": "x",
                                  "region": {"x0": 0.9, "y0": 0.1, "x1": 0.2, "y1": 0.5}}))
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["failure_kind"] == "schema_error" and outcome["parse"]["ok"] is True
    assert outcome["reference"]["ok"] is False
    assert outcome["raw_response"] == chat.answer, "şema hatasında ham yanıt korunur"


def test_a_response_claiming_acceptance_is_a_schema_error(bundle):
    payload = {"schema_version": "semread-probe/2",
               "items": [item("image-1"), item("image-2")],
               "supported": True}
    outcome = SemanticReader(FakeChat(json.dumps(payload))).probe(bundle)
    assert outcome["failure_kind"] == "schema_error"
    assert "supported" in outcome["schema"]["error"]


def test_an_image_id_that_was_never_sent_is_a_reference_error(bundle):
    chat = FakeChat(response_for(item("image-9")))
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["failure_kind"] == "reference_error"
    assert "image-9" in outcome["failure_detail"]
    assert "image-1, image-2" in outcome["failure_detail"], "izinli kimlikler hatada yazılmalı"


def test_a_stale_snapshot_identity_is_refused(bundle):
    outcome = SemanticReader(FakeChat(response_for(item("image-1"), item("image-1-old")))).probe(bundle)
    assert outcome["failure_kind"] == "reference_error"


def test_a_transport_failure_keeps_its_own_layer_and_the_raw_body(bundle):
    chat = FakeChat(error=UnavailableModel("yerel model istek reddedildi (500)"),
                    raw_body={"error": "patladı"})
    setattr(chat.error, "transport_kind", "http_error")
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["failure_kind"] == "http_error"
    assert outcome["raw_body"] == {"error": "patladı"}
    assert outcome["raw_response"] is None


def test_an_empty_answer_is_not_a_success(bundle):
    error = UnavailableModel("yerel model boş içerik döndürdü; buluta düşülmez")
    setattr(error, "transport_kind", "empty_content")
    outcome = SemanticReader(FakeChat(error=error, raw_body={"message": {"content": ""}})).probe(bundle)
    assert outcome["failure_kind"] == "empty_content" and outcome["outcome"] == "error"
    assert outcome["raw_body"] == {"message": {"content": ""}}


def test_a_truncated_answer_is_recorded_as_truncated_not_as_complete(bundle):
    chat = FakeChat(response_for(item("image-1")))

    def truncated(prompt, image_png=None, **kwargs):
        if kwargs.get("stats") is not None:
            kwargs["stats"].update({"done_reason": "length"})
        return chat.answer

    chat.complete = truncated
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["truncated"]["state"] == "truncated"
    assert outcome["truncated"]["done_reason"] == "length"


def test_a_missing_done_reason_is_unknown_not_complete(bundle):
    chat = FakeChat(response_for(item("image-1"), item("image-2")))

    def no_reason(prompt, image_png=None, **kwargs):
        if kwargs.get("stats") is not None:
            kwargs["stats"].update({"done_reason": None})
        return chat.answer

    chat.complete = no_reason
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["truncated"]["state"] == "unknown"
    assert outcome["truncated"]["done_reason"] is None


def test_complete_metadata_is_required_for_a_complete_verdict(bundle):
    """`stop` var ama sayım metadata'sı yoksa durum `complete` yazılmaz: eksik kanıt kabul etmez."""
    chat = FakeChat(response_for(item("image-1"), item("image-2")))

    def stop_without_counts(prompt, image_png=None, **kwargs):
        if kwargs.get("stats") is not None:
            kwargs["stats"].update({"done_reason": "stop", "eval_count": None,
                                    "prompt_eval_count": None})
        return chat.answer

    chat.complete = stop_without_counts
    outcome = SemanticReader(chat).probe(bundle)
    assert outcome["truncated"]["state"] == "unknown"
    assert outcome["truncated"]["metadata_complete"] is False


# -- sentinel: altın/referans sızıntısı -----------------------------------


def test_a_gold_token_in_the_prompt_or_record_is_flagged(bundle):
    prompt = probe_prompt(bundle)
    assert leak_check(prompt, {"images_per_call": 2}, ["plate with a pocket.STEP"]) == []
    assert leak_check(prompt + " plate with a pocket.STEP", None,
                      ["plate with a pocket.STEP"]) != []


def test_an_undefined_field_in_the_request_record_is_flagged(bundle):
    trace = {"images_per_call": 2, "gold_bbox": [0.1, 0.2, 0.3, 0.4]}
    found = leak_check(probe_prompt(bundle), trace, [])
    assert any("gold_bbox" in entry for entry in found)


def test_the_reader_reports_leakage_instead_of_hiding_it(bundle):
    chat = FakeChat(response_for(item("image-1"), item("image-2")))

    def sneaky(prompt, image_png=None, **kwargs):
        if kwargs.get("trace") is not None:
            kwargs["trace"].update({"images_per_call": 1, "expected_answer": "image-1=triangle"})
        return chat.answer

    chat.complete = sneaky
    outcome = SemanticReader(chat).probe(bundle, forbidden=["image-1=triangle"])
    assert outcome["leakage"], "yasaklı iz ve tanımsız anahtar raporlanmalı"
    assert any("expected_answer" in entry for entry in outcome["leakage"])


def test_the_class_vocabulary_is_contract_not_gold(bundle):
    """Sınıf adları prompt'ta **açıkça** vardır: sentinel onları altın sanmamalı.

    Altın olan şey kimlik→sınıf eşlemesidir; sınıf sözlüğünün kendisi sözleşmedir.
    """
    prompt = probe_prompt(bundle)
    assert leak_check(prompt, None, ["triangle"]) != [], "çıplak sınıf adı ile ayırt edilemez"
    assert leak_check(prompt, None, ["image-1=triangle", "plate with a pocket.STEP"]) == []
