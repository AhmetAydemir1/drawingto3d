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
                                             CandidateResponse, ProvenanceField, candidate_prompt,
                                             candidate_json_schema, check_candidate_references,
                                             parse_candidate_json)
from drawingto3d.semantic_images import (PreparedImage, SourcePage, overlay_from_observations,
                                         prepare_full_page)
from drawingto3d.semantic_run_contract import (EVIDENCE_MODES, IMAGES_LAYOUT,  # noqa: E501
                                               IMAGE_LABEL_PREFIX)

V_ARM = "V"
VE_ARM = "VE"
ARMS = (V_ARM, VE_ARM)
# Kollar aynı generation ayarlarıyla çalışır: bu üçlü yalnız kayıt için burada durur.
# Not (PLAN-4 §7): burada eskiden bir SHARED_SETTINGS sözlüğü vardı (temperature/top_p/seed).
# Üretimi etkileyen ayarların **tek** kaynağı `semantic_run_contract.SETTINGS`; ikinci bir tanım
# gerçek istekle çelişebilirdi. Kaldırıldı.
OVERLAY_IMAGE_ID = "image-2"          # ham sayfa kimliği image-1'dir; overlay ayrı ama nötr kimlik
RAW_IMAGE_ID = "image-1"


def raw_observation_rows(observations: Observations) -> list[dict]:
    """Ham gözlem satırları (eleme **uygulanmaz**): yalnız ölçülmüş alanlar; gold/karar yok.

    Referans/kimlik denetimleri bu tam listeyi kullanır: extraction bir kimliği ürettiyse, o satır
    serileştirmede elenmiş olsa bile vardır (P3 §17 yalnız VLM'e giden tabloyu küçültür).
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


def _empty_evidence(row: dict) -> bool:
    """P3 §17: bölgesi, metni ve değeri olmayan satır **kanıt taşımaz** — serileştirilmez."""
    return (row.get("region") is None and not (row.get("text") or "").strip()
            and row.get("value") is None)


def observation_table_with_counts(observations: Observations) -> tuple[list[dict], dict]:
    """VE tablosu + sayım kaydı (PLAN-12 §17): raw / sent / dropped.

    Kaynak `Observations` **değişmez**; yalnız VLM'e giden serileştirme küçülür. Sıra stabildir
    (primitives sonra texts, kaynak sırası korunur) ve kayıt gold'a bağlı değildir.
    """
    rows = raw_observation_rows(observations)
    kept = [row for row in rows if not _empty_evidence(row)]
    counts = {"raw": len(rows), "sent": len(kept), "dropped": len(rows) - len(kept)}
    return kept, counts


def observation_table(observations: Observations) -> list[dict]:
    """VE'nin gördüğü **adreslenebilir** tablo: yalnız ölçülmüş gözlem alanları.

    `meaning`/gold/karar yoktur. Kimlikler gerçek gözlem kimlikleridir (`g*` primitive, `t*` metin,
    `p*` yol); bölge normalize `[x0,y0,x1,y1]`. Boş kanıt satırları elenir (§17); sayımlar için
    `observation_table_with_counts` kullanılır.
    """
    return observation_table_with_counts(observations)[0]


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
        table, counts = observation_table_with_counts(observations)
    else:
        # V kolu gözlem satırı **görmez**; sayım kaydı yine tutulur (karşılaştırma için ham adet).
        counts = {"raw": len(observations.primitives) + len(observations.texts), "sent": 0,
                  "dropped": 0}
    return {"arm": arm, "images": images, "image_ids": [image.image_id for image in images],
            "page_image_id": image_id, "observations": table,
            "observation_counts": counts,
            "arm_input_variant": arm, "evidence_mode": EVIDENCE_MODES[arm]}


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
                              images_layout=IMAGES_LAYOUT,
                              image_label_prefix=IMAGE_LABEL_PREFIX)
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
    # P4 §18: sıra **önce** bütünlük denetimi, sonra ayrıştırma. Kesilmiş/eksik-metadata yanıt
    # tam sayılmaz: semantik ayrıştırıcı çağrılmaz, ham yanıt saklanır, sınıflandırma üst katmana
    # aittir (`truncated_output` / `incomplete_metadata`).
    if done_reason == "stop" and metadata_complete:
        state, parse_eligible = "complete", True
    elif done_reason == "length":
        state, parse_eligible = "truncated", False
    else:
        state, parse_eligible = "unknown", False
    outcome["truncated"] = {"done_reason": done_reason, "state": state,
                            "metadata_complete": bool(metadata_complete),
                            "parse_eligible": parse_eligible}
    if not parse_eligible:
        kind = "truncated_output" if done_reason == "length" else "incomplete_metadata"
        outcome["failure_kind"] = kind
        outcome["parse"] = {"ok": False, "kind": kind,
                            "error": (f"done_reason={done_reason!r}: yanıt tamamlanmadı; "
                                      "ayrıştırıcı çağrılmadı")}
        outcome["leakage"] = leak_check(prompt + str(trace) + str(answer), forbidden)
        return outcome
    try:
        response = parse_candidate_json(answer)
    except CandidateParseError as exc:
        outcome["failure_kind"] = exc.kind
        outcome["parse"] = {"ok": False, "kind": exc.kind, "error": str(exc)}
        outcome["leakage"] = leak_check(prompt + str(trace) + str(answer), forbidden)
        return outcome
    # P2 §16.2: `provenance` harness'a aittir — model onu yazmaz (şemada yok). Burada kanıtlanabilir
    # biçimde enjekte edilir: kind = dal (vlm), method = çağrıda gerçekten görülen model kimliği.
    model_seen = str(((outcome.get("request") or {}).get("model")) or "")
    for item in response.items:
        item.provenance = ProvenanceField(kind="vlm", method=model_seen)
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


__all__ = ["ARMS", "OVERLAY_IMAGE_ID", "RAW_IMAGE_ID", "EVIDENCE_MODES", "V_ARM", "VE_ARM",
           "leak_check", "observation_table", "observation_table_with_counts", "prepare_arm_inputs",
           "raw_observation_rows", "read_page"]
