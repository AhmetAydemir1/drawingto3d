"""SEMREAD-001B — **tahmin üreten sözleşme** (P0R-2).

Bu modül, ham tahminin byte'larını/içeriğini değiştirebilecek sabitlerin **tek** yeridir:
model etiketi, beklenen digest, beklenen runtime, üretim ayarları, görüntü işleme sözleşmesi ve
çağrı düzeni. `producer_identity()` bu dosyayı hash'ler.

Kural: buradaki bir değeri değiştirmek ham tahmini geçersiz kılar. Değerlendirme, kabul kapıları,
rapor üretimi ve referans doğrulaması bu dosyada **yaşamaz** — onlar `evaluation_identity()`ye girer.
Böylece yalnız evaluator/gold düzeltmesi geçerli ham tahmini yeniden üretmeyi gerektirmez.

Sürüm `/3` (P0R-FINAL-C): tahmin girdisi kimliği artık gerçekten hazırlanan paketten (hazırlanmış
görüntü byte'ları + gönderilen prompt + VE gözlem tablosu) kurulur; eski sürümdeki sayfa PNG'sine
dayanan `input_identity` yalnız meta veri olarak kalır. Girdi sözleşmesi değiştiği için bu dosyayı
hash'leyen attempt'ler bayatlar (yeniden kullanım yok; D yeniden koşar, inference harcamaz).
"""

from __future__ import annotations

CONTRACT_VERSION = "semread-001b-run-contract/3"

MODEL = "qwen3-vl:8b-instruct"
EXPECTED_DIGEST = "0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319"
EXPECTED_RUNTIME = "0.32.1"

PAGE_IMAGE_ID = "image-1"
GOLD_SENTINEL = "semread-001b-gold-sentinel-4f21"
CASE_SCHEMA = "semread-001b-case/1"

# Ham sayfa stratejisi ve kola bağlı kanıt modu (PLAN-4 §8): ortak bir "input_strategy" alanı
# VE'nin fazladan aldığı kanıtı gizleyebilirdi; ikisi ayrı adlarla yazılır.
RAW_PAGE_STRATEGY = "single_full_page"
ARM_VARIANTS = {"V": "V", "VE": "VE"}
EVIDENCE_MODES = {"V": "none", "VE": "deterministic_overlay_and_table"}


def arm_evidence_mode(arm: str) -> str:
    """Kolun kanıt modu: V ham sayfa, VE ham sayfa + nötr overlay + gözlem tablosu."""
    if arm not in EVIDENCE_MODES:
        raise ValueError(f"bilinmeyen kol: {arm}")
    return EVIDENCE_MODES[arm]


# Çerçeveleme: okuyucu (semantic_candidate_reader) bu değerleri buradan alır — kopya literal yok.
IMAGES_LAYOUT = "per_image_message_labeled"
IMAGE_LABEL_PREFIX = "Image ID: "

IMAGE_MAX_SIDE = 1280          # development'ta sabitlenir; final koşuya kadar değişmez
NUM_PREDICT = 2048

# Üretim ayarları: taşıma katmanı bu değerlerden kurulur (kopyası tutulmaz).
#
# `top_p` ve `seed` **bilerek yoktur** (PLAN-3 §4 alternatifi): taşıma katmanı (`ChatSettings` →
# `_chat_request`) bu iki seçeneği Ollama `options` gövdesine koymuyor. Donmuş sözleşmeye yazıp
# göndermemek, kaydetmenin gerçeği anlatması kuralını çiğnerdi. Desteklenmeyen bir donmuş ayar
# eklenirse `write_live_attempt()` gönderimi durdurur (`blocking_kind=unsupported_frozen_setting`).
SETTINGS = {"num_ctx": 8192, "temperature": 0.0,
            "num_predict": NUM_PREDICT, "keep_alive": "5m", "image_max_side": IMAGE_MAX_SIDE,
            "images_layout": IMAGES_LAYOUT, "image_label_prefix": IMAGE_LABEL_PREFIX,
            "raw_page_strategy": RAW_PAGE_STRATEGY}

# Görüntü hazırlama sözleşmesi (preprocessing identity): hazırlama kodu bu dosyalarda yaşar.
PREPROCESSING_FILES = ("src/drawingto3d/semantic_images.py",
                       "src/drawingto3d/semantic_candidate_reader.py")

# Tahmini üreten (bu modül dışındaki) kaynak dosyalar.
PRODUCER_SOURCE_FILES = (
    "src/drawingto3d/semantic_candidates.py",
    "src/drawingto3d/semantic_candidate_reader.py",
    "src/drawingto3d/semantic_schema.py",
    "src/drawingto3d/semantic_images.py",
    "src/drawingto3d/llama.py",
    "src/drawingto3d/inference_log.py",
)

# Deterministic D kolunun tahminini üreten dosyalar.
D_SOURCE_FILES = ("src/drawingto3d/semantic_deterministic.py",
                  "src/drawingto3d/observe.py", "src/drawingto3d/bind.py",
                  "src/drawingto3d/meaning.py")
