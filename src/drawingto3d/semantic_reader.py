"""SEMREAD-001A okuyucusu: hazırlanan paketi gönder, yanıtı **yapısal** olarak doğrula.

Bu dosya semantik doğrulama yapmaz. Yaptığı üç şey:

* gönderilecek görsel listesini ve prompt'taki kimlik/sıra eşlemesini **aynı** hazırlanmış paketten
  üretir (sıra değişirse eşleme kendiliğinden güncellenir, kimlik görselle kalır);
* ham yanıtı, HTTP/boş/parse/şema/referans/kesilme ayrımıyla kaydeder — bozuk yanıt sessizce JSON
  "tamir" edilip başarıya çevrilmez;
* referansı yalnız **bu çağrıda gönderilen** kimliklere izin vererek denetler ve geçerli bölgeleri
  kaynak sayfanın normalize çerçevesine geri çözer.

Modelin metin açıklaması görsel gözlemdir; semantik doğruluk kanıtı değildir. `supported`/`source=user`
alanları sözleşmede yoktur, gelse de şema hatasıdır.
"""

from __future__ import annotations

import hashlib
import json
import time

from drawingto3d.errors import UnavailableModel
from drawingto3d.llama import LAYOUTS
from drawingto3d.semantic_schema import (PREPROCESSING_VERSION, PROBE_SCHEMA_VERSION, SHAPE_CLASSES,
                                         ImageBundle, ProbeParseError, ProbeReferenceError,
                                         ProbeResponse, ProbeSchemaError, check_references,
                                         parse_probe_json, probe_json_schema,
                                         validate_probe_response)

READER_VERSION = "semread-reader/2"
DEFAULT_NUM_PREDICT = 512
# Görsel mesajına yazılan nötr kaynak kimliği biçimi. Yalnız kimliği taşır: hangi görüntünün ne
# olduğunu söylemez, kaynak dosya adı/hash/gold taşımaz.
LABEL_PREFIX = "Image ID: "

# Actual-request kaydının taşıyabileceği anahtarlar. Altın/STEP etiketi gibi bir alanın bu sözlüğe
# sonradan eklenmesi `leak_check`'in yakaladığı şeydir; liste kapalıdır, çünkü açık liste "her şey
# geçebilir" demek olurdu.
ALLOWED_REQUEST_KEYS = frozenset({
    "schema", "endpoint", "method", "model", "prompt_sha256", "prompt_chars", "options",
    "keep_alive", "response_format", "images_per_call", "images", "request_sha256", "request_bytes",
    "images_layout", "messages_layout",
    "timeout_seconds", "outcome", "error_kind", "http_status", "transport_seconds", "response_bytes",
    "done_reason", "eval_count", "prompt_eval_count", "total_duration_ns",
})

ALLOWED_IMAGE_KEYS = frozenset({"index", "image_id", "source_sha256", "sent_sha256", "sent_bytes",
                                "sent_width_px", "sent_height_px", "resize"})

# Mesaj düzeni kaydının alanları da kapalıdır: `label` yalnız nötr kimliği taşır (bkz. LABEL_PREFIX).
ALLOWED_MESSAGE_KEYS = frozenset({"index", "image_ids", "label"})

TRUNCATED = "truncated"
COMPLETE = "complete"
UNKNOWN = "unknown"


def probe_prompt(bundle: ImageBundle) -> str:
    """Prompt, paketin **kendi** sırasından üretilir: kimlik ile sıra tek yerde eşleşir.

    Görsellerin ne içerdiği söylenmez — bu prompt'un işi sıra/kimlik eşlemesini kurmak, cevabı
    vermek değil. Şekil sorusu küçük ve sürümlü bir sınıflandırmadır: seçenekler her görsele aynı
    sunulur, hangi kimliğin hangi sınıfı taşıdığı söylenmez.
    """
    listed = "\n".join(f"  {position}. {image_id}"
                       for position, image_id in enumerate(bundle.image_ids, start=1))
    ids = ", ".join(bundle.image_ids)
    classes = ", ".join(SHAPE_CLASSES)
    # Metin çerçevelemeden bağımsızdır: görseller tek mesajda da, görsel başına bir mesajda da
    # gönderilebilir; hangi düzenin kullanıldığını söylemek modelin işi değil, kaydın işi.
    return (
        f"You are given {len(bundle)} image(s) taken from drawings. "
        "They appear in this exact order:\n"
        f"{listed}\n\n"
        "For every image, say briefly what it shows, and if you can point at the region you mean, give "
        "that region as a box inside *that* image: normalized to [0,1], (0,0) at the top-left corner, "
        "x to the right, y downwards.\n\n"
        f"Also give the shape class of each image on its own: one of {classes}. "
        "Use `other` if it is not a simple shape, `unknown` if you cannot tell. The same options "
        "apply to every image.\n\n"
        "Answer with JSON only, in exactly this shape:\n"
        f'{{"schema_version": "{PROBE_SCHEMA_VERSION}", '
        '"items": [{"image_id": "<one of the ids above>", "description": "<short phrase>", '
        '"shape": "<one class>", "region": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0}}]}\n\n'
        f"Use exactly one item per image and only these image ids: {ids}. "
        "Use null instead of a region if you cannot point at one. Never invent an image id."
    )


def leak_check(prompt: str, request_manifest: dict | None = None,
               forbidden: list[str] | None = None) -> list[str]:
    """Altın/STEP etiketi gibi referansın isteğe sızıp sızmadığını denetle.

    İki yol aranır: yasaklı dizelerin prompt/istek metninde geçmesi ve request kaydında tanımsız bir
    anahtarın bulunması. Dönen liste boşsa sızıntı görülmedi; bu dar bir sentinel denetimidir, genel
    bir güvenlik sertifikası değildir.
    """
    found: list[str] = []
    for token in forbidden or []:
        if not token:
            continue
        if token in prompt:
            found.append(f"prompt içinde yasaklı iz: {token}")
        if request_manifest is not None and token in json.dumps(request_manifest, ensure_ascii=False):
            found.append(f"request kaydında yasaklı iz: {token}")
    if isinstance(request_manifest, dict):
        for key in request_manifest:
            if key not in ALLOWED_REQUEST_KEYS:
                found.append(f"request kaydında tanımsız anahtar: {key}")
        for entry in request_manifest.get("images") or []:
            if isinstance(entry, dict):
                for key in entry:
                    if key not in ALLOWED_IMAGE_KEYS:
                        found.append(f"görsel kaydında tanımsız anahtar: {key}")
        for entry in request_manifest.get("messages_layout") or []:
            if isinstance(entry, dict):
                for key in entry:
                    if key not in ALLOWED_MESSAGE_KEYS:
                        found.append(f"mesaj düzeni kaydında tanımsız anahtar: {key}")
    return found


class SemanticReader:
    """Bir görsel paketini yerel sohbete gönderir ve yanıtı katman katman doğrular."""

    def __init__(self, chat, *, num_predict: int = DEFAULT_NUM_PREDICT,
                 reader_version: str = READER_VERSION) -> None:
        self.chat = chat
        self.num_predict = int(num_predict)
        self.reader_version = reader_version

    def probe(self, bundle: ImageBundle, *, forbidden: list[str] | None = None,
              images_layout: str = "single_message") -> dict:
        """Tek çağrı: ham yanıt + parse + şema + referans sonuçları ayrı ayrı döner.

        Hiçbir aşama diğerini gizlemez: JSON çözülemediyse ham metin yine de sonuçtadır; şema
        tutmadıysa ham JSON da sonuçtadır; referans düşerse hangi kimliğin uydurulduğu yazılır.

        `images_layout` yalnız multimodal çerçevelemeyi seçer: `single_message` (tek mesaj, N görsel),
        `per_image_message` (görsel başına mesaj, metinsiz) ya da `per_image_message_labeled` (görsel
        başına mesaj ve o mesajın metni yalnız nötr kaynak kimliği, ör. `Image ID: image-2`).
        image ID ↔ sıra sözleşmesi ve prompt metni üç durumda da aynıdır; etiketli düzende kimlik
        görselin **kendi** mesajında taşınır, görüntü byte'ları değişmez.
        """
        prompt = probe_prompt(bundle)
        schema = probe_json_schema()
        trace: dict = {}
        raw_body: dict = {}
        stats: dict = {}
        outcome = {
            "reader_version": self.reader_version,
            "preprocessing_version": PREPROCESSING_VERSION,
            "model": getattr(self.chat, "model", None),
            "image_ids": bundle.image_ids,
            "image_order": bundle.image_ids,
            "images_per_call": len(bundle),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
            "prompt": prompt,
            "response_schema": schema,
            "request": {},
            "raw_response": None,
            "raw_body": None,
            "outcome": "error",
            "failure_kind": None,
            "failure_detail": None,
            "parse": {"ok": False, "error": "çağrı yapılmadı"},
            "schema": {"ok": False, "error": "çağrı yapılmadı"},
            "reference": {"ok": False, "error": "çağrı yapılmadı", "checks": [],
                          "resolved_regions_page_norm": []},
            "truncated": {"done_reason": None, "state": UNKNOWN},
            "stats": stats,
            "seconds": None,
            "leakage": [],
        }
        started = time.perf_counter()
        try:
            answer = self.chat.complete(prompt, images=bundle.pngs, num_predict=self.num_predict,
                                        response_format=schema, stats=stats, trace=trace,
                                        raw_response=raw_body, image_labels=bundle.image_ids,
                                        images_layout=images_layout,
                                        image_label_prefix=LABEL_PREFIX)
        except UnavailableModel as exc:
            outcome.update({
                "outcome": "error",
                "failure_kind": getattr(exc, "transport_kind", "unreachable"),
                "failure_detail": str(exc),
                "raw_body": raw_body or None,
                "request": trace,
                "seconds": round(time.perf_counter() - started, 3),
                "parse": {"ok": False, "error": f"çağrı başarısız: {exc}"},
                "schema": {"ok": False, "error": "çağrı başarısız"},
                "reference": {"ok": False, "error": "çağrı başarısız", "checks": [],
                              "resolved_regions_page_norm": []},
            })
            outcome["leakage"] = leak_check(prompt, trace, forbidden)
            return outcome
        except ValueError:
            # Sözleşme ihlali (ör. image_png ile images birlikte): programlama hatasıdır, yutulmaz.
            raise
        outcome["seconds"] = round(time.perf_counter() - started, 3)
        outcome["request"] = trace
        outcome["raw_response"] = answer
        outcome["raw_body"] = raw_body or None
        outcome["truncated"] = _truncation(trace, stats)

        try:
            payload = parse_probe_json(answer)
        except ProbeParseError as exc:
            outcome.update({"outcome": "error", "failure_kind": "parse_error",
                            "failure_detail": str(exc), "parse": {"ok": False, "error": str(exc)},
                            "schema": {"ok": False, "error": "parse edilemediği için şema denenmedi"},
                            "reference": {"ok": False, "error": "parse edilemedi", "checks": [],
                                          "resolved_regions_page_norm": []}})
            outcome["leakage"] = leak_check(prompt, trace, forbidden)
            return outcome
        outcome["parse"] = {"ok": True, "error": None}

        try:
            response = validate_probe_response(payload)
        except ProbeSchemaError as exc:
            outcome.update({"outcome": "error", "failure_kind": "schema_error",
                            "failure_detail": str(exc), "schema": {"ok": False, "error": str(exc)},
                            "reference": {"ok": False, "error": "şema tutmadığı için referans denenmedi",
                                          "checks": [], "resolved_regions_page_norm": []}})
            outcome["leakage"] = leak_check(prompt, trace, forbidden)
            return outcome
        outcome["schema"] = {"ok": True, "error": None}

        try:
            reference = check_references(response, bundle.image_ids)
        except ProbeReferenceError as exc:
            outcome.update({"outcome": "error", "failure_kind": "reference_error",
                            "failure_detail": str(exc),
                            "reference": {"ok": False, "error": str(exc), "checks": [],
                                          "resolved_regions_page_norm": []}})
            outcome["leakage"] = leak_check(prompt, trace, forbidden)
            return outcome
        resolved = _resolve_regions(response, bundle)
        reference = {**reference, "resolved_regions_page_norm": resolved}
        outcome.update({"outcome": "ok", "failure_kind": None, "failure_detail": None,
                        "reference": reference, "parsed": response.model_dump(),
                        "regions_page_norm": [row["region_page_norm"] for row in resolved]})
        outcome["leakage"] = leak_check(prompt, trace, forbidden)
        return outcome


def _truncation(trace: dict, stats: dict) -> dict:
    """Kesilme durumu + tamamlanma metadata'sı: eksik metadata `unknown` kalır, tahmin yazılmaz.

    `complete` demek için `done_reason == "stop"` **ve** sayım metadata'sının (prompt/eval token)
    gerçekten gelmiş olması gerekir. Metadata eksikse durum `unknown` olur ve canlı kabul kapısı
    bunu geçirmez: "sessizce kesilmiş ama tam görünen" bir yanıt kabul sayılamaz.
    """
    reason = (trace or {}).get("done_reason") or (stats or {}).get("done_reason")
    counted = (isinstance(stats.get("prompt_eval_count"), int)
               and isinstance(stats.get("eval_count"), int))
    record = {"done_reason": reason, "state": UNKNOWN, "metadata_complete": counted,
              "prompt_eval_count": stats.get("prompt_eval_count"),
              "eval_count": stats.get("eval_count")}
    if reason is None:
        record["state"] = UNKNOWN
    elif reason != "stop":
        record["state"] = TRUNCATED
    elif counted:
        record["state"] = COMPLETE
    return record


def _resolve_regions(response: ProbeResponse, bundle: ImageBundle) -> list[dict]:
    """Her bölgeyi, **referans verdiği görselin** çerçevesinden kaynak sayfaya çöz."""
    rows: list[dict] = []
    for item in response.items:
        image = bundle.by_id(item.image_id)
        if item.region is None:
            rows.append({"image_id": item.image_id, "region_image_norm": None,
                         "region_page_norm": None, "image_kind": image.kind,
                         "prepared_image_sha256": image.sha256})
            continue
        rows.append({
            "image_id": item.image_id,
            "region_image_norm": item.region.as_bbox(),
            "region_page_norm": image.map_region_to_page(item.region),
            "image_kind": image.kind,
            "prepared_image_sha256": image.sha256,
            "t_image_norm_to_page_norm": image.t_image_norm_to_page_norm,
        })
    return rows


__all__ = ["ALLOWED_MESSAGE_KEYS", "ALLOWED_REQUEST_KEYS", "DEFAULT_NUM_PREDICT", "LABEL_PREFIX",
           "LAYOUTS", "READER_VERSION", "SemanticReader", "leak_check", "probe_prompt"]
