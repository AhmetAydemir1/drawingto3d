"""SEMREAD-001B — **V** ve **VE** kollarının okuma yolu.

İki kol **aynı** çıktı şemasını, görev metnini, modeli/digest'i ve üretim ayarlarını kullanır; tek
fark gözlem girdisidir:

  * **V**  : yalnız ham full-page görüntüsü (nötr kimlik) + ortak görev prompt'u. Gözlem tablosu,
             deterministic yorum ya da overlay **yoktur**.
  * **VE** : V ile **byte düzeyinde aynı** ham full-page + aynı sayfanın gerçek gözlem overlay'i +
             sınırlı, adreslenebilir gözlem tablosu (id/tür/metin/değer/birim/bölge). Tablo
             gözlemlerin yanlış olabileceğini söyler; gold, `meaning` sonucu ya da deterministic
             karar **verilmez**.

Overlay ayrı bir görsel olduğu için VE daha fazla görüntü taşır; bu fark maliyet kaydında görünür.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from drawingto3d.observe import Observations
from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION, CandidateParseError,
                                             CandidateResponse, candidate_prompt,
                                             candidate_json_schema, check_candidate_references,
                                             parse_candidate_json)
from drawingto3d.semantic_images import (PreparedImage, SourcePage, overlay_from_observations,
                                         prepare_full_page)

V_ARM = "V"
VE_ARM = "VE"
ARMS = (V_ARM, VE_ARM)
# Kollar aynı generation ayarlarıyla çalışır: bu üçlü yalnız kayıt için burada durur.
SHARED_SETTINGS = {"temperature": 0.0, "top_p": 1.0, "seed": 20261004}
OVERLAY_IMAGE_ID = "image-2"          # ham sayfa kimliği image-1'dir; overlay ayrı ama nötr kimlik
RAW_IMAGE_ID = "image-1"


def observation_table(observations: Observations) -> list[dict]:
    """VE'nin gördüğü **adreslenebilir** tablo: yalnız ölçülmüş gözlem alanları.

    `meaning`/gold/karar yoktur. Kimlikler gerçek gözlem kimlikleridir (`g*` primitive, `t*` metin,
    `p*` yol); bölge normalize `[x0,y0,x1,y1]`.
    """
    frame = observations.frame
    width, height = float(frame.width) or 1.0, float(frame.height) or 1.0

    def box(x: float, y: float, w: float, h: float) -> list[float]:
        return [round(x / width, 4), round(y / height, 4),
                round(min(1.0, (x + w) / width), 4), round(min(1.0, (y + h) / height), 4)]

    rows: list[dict] = []
    for primitive in observations.primitives:
        entry = {"id": primitive.id, "kind": primitive.kind, "text": None, "value": None,
                 "unit": None, "region": None}
        if primitive.centre and primitive.radius:
            entry["region"] = box(primitive.centre[0] - primitive.radius,
                                  primitive.centre[1] - primitive.radius,
                                  2 * primitive.radius, 2 * primitive.radius)
        rows.append(entry)
    for text in observations.texts:
        rows.append({"id": text.id, "kind": text.kind, "text": text.text, "value": text.value,
                     "unit": text.unit, "region": box(text.bbox.x, text.bbox.y, text.bbox.w,
                                                      text.bbox.h)})
    return rows


def prepare_arm_inputs(source: "SourcePage", observations: Observations, *, image_id: str, arm: str,
                       resize_max_side: int | None = None) -> dict:
    """Kolun girdisini hazırla. VE'nin ham sayfası V'ninkiyle **aynı byte'lar** olmalıdır."""
    if arm not in ARMS:
        raise ValueError(f"bilinmeyen kol: {arm}")
    raw = prepare_full_page(source, image_id, resize_max_side=resize_max_side)
    images: list[PreparedImage] = [raw]
    table: list[dict] = []
    if arm == VE_ARM:
        overlay = overlay_from_observations(observations, OVERLAY_IMAGE_ID, source=source,
                                           resize_max_side=resize_max_side)
        images.append(overlay)
        table = observation_table(observations)
    return {"arm": arm, "images": images, "image_ids": [image.image_id for image in images],
            "page_image_id": image_id, "observations": table}


def leak_check(text: str, forbidden: list[str]) -> list[str]:
    """Yasak terim taraması: gold sentinel'i ve referansa özel adlar.

    Uyarı (bilinçli): sayfanın kendi bastığı **sayılar** (ör. `8`, `Ø`) sızıntı sayılmaz; onlar
    çizimin içeriğidir ve referansla sayısal olarak çakışabilir. Bu yüzden aranan şey referansa özel
    işaretlerdir (sentinel, hedef adları, gold dosya adları), değerlerin kendisi değildir.
    """
    haystack = (text or "").lower()
    return sorted({term for term in forbidden if term and term.lower() in haystack})


def read_page(chat, bundle: dict, *, forbidden: list[str], num_predict: int | None = None) -> dict:
    """Kolu gerçek bir çağrıyla oku. Dönen sözlük ham + ayrıştırılmış + kapılar içindir."""
    prompt = candidate_prompt([bundle["page_image_id"]],
                              observations=bundle["observations"] or None)
    schema = candidate_json_schema()
    images = [image.png for image in bundle["images"]]
    labels = [image.image_id for image in bundle["images"]]
    stats: dict = {}
    raw_body: dict = {}
    trace: dict = {}
    outcome: dict = {
        "arm": bundle["arm"], "reader_version": CANDIDATE_READER_VERSION,
        "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "images": [{"image_id": image.image_id, "sha256": hashlib.sha256(image.png).hexdigest(),
                    "bytes": len(image.png)} for image in bundle["images"]],
        "request": {}, "raw_response": None, "outcome": "error", "failure_kind": None,
        "parse": {"ok": False, "error": "çağrı yapılmadı"},
        "truncated": {"done_reason": None, "state": "unknown", "metadata_complete": False},
        "stats": stats, "leakage": [],
    }
    try:
        answer = chat.complete(prompt, images=images, num_predict=num_predict,
                              response_format=schema, stats=stats, trace=trace,
                              raw_response=raw_body, image_labels=labels,
                              images_layout="per_image_message_labeled",
                              image_label_prefix="Image ID: ")
    except Exception as exc:  # noqa: BLE001 - taşıma hatası kayda geçer, yutulmaz
        outcome.update({"failure_kind": getattr(exc, "transport_kind", "unreachable"),
                        "detail": f"{type(exc).__name__}: {exc}", "request": trace,
                        "raw_body": raw_body or None})
        outcome["leakage"] = leak_check(prompt + str(trace), forbidden)
        return outcome

    outcome["raw_response"] = answer
    outcome["raw_body"] = raw_body or None
    outcome["request"] = trace
    outcome["outcome"] = "answered"
    done_reason = stats.get("done_reason")
    metadata_complete = stats.get("eval_count") is not None and stats.get("prompt_eval_count") is not None
    if done_reason == "stop" and metadata_complete:
        state = "complete"
    elif done_reason is None:
        state = "unknown"
    else:
        state = "truncated"
    outcome["truncated"] = {"done_reason": done_reason, "state": state,
                            "metadata_complete": bool(metadata_complete)}
    try:
        response = parse_candidate_json(answer)
    except CandidateParseError as exc:
        outcome["parse"] = {"ok": False, "error": str(exc)}
        outcome["leakage"] = leak_check(prompt + str(trace) + str(answer), forbidden)
        return outcome
    outcome["parsed"] = response.model_dump(mode="json")
    allowed_ids = [image["image_id"] for image in outcome["images"]]
    references = check_candidate_references(
        response, [bundle["page_image_id"]],
        allowed_observation_ids=[row["id"] for row in bundle["observations"]] or None,
        allowed_image_ids=allowed_ids)
    outcome["parse"] = {"ok": True}
    outcome["references"] = references
    outcome["leakage"] = leak_check(prompt + str(trace) + str(answer), forbidden)
    return outcome


__all__ = ["ARMS", "OVERLAY_IMAGE_ID", "RAW_IMAGE_ID", "SHARED_SETTINGS", "V_ARM", "VE_ARM",
           "leak_check", "observation_table", "prepare_arm_inputs", "read_page"]
