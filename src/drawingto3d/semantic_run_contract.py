"""SEMREAD-001B — **tahmin üreten sözleşme** (P0R-2).

Bu modül, ham tahminin byte'larını/içeriğini değiştirebilecek sabitlerin **tek** yeridir:
model etiketi, beklenen digest, beklenen runtime, üretim ayarları, görüntü işleme sözleşmesi ve
çağrı düzeni. `producer_identity()` bu dosyayı hash'ler.

Kural: buradaki bir değeri değiştirmek ham tahmini geçersiz kılar. Değerlendirme, kabul kapıları,
rapor üretimi ve referans doğrulaması bu dosyada **yaşamaz** — onlar `evaluation_identity()`ye girer.
Böylece yalnız evaluator/gold düzeltmesi geçerli ham tahmini yeniden üretmeyi gerektirmez.
"""

from __future__ import annotations

CONTRACT_VERSION = "semread-001b-run-contract/1"

MODEL = "qwen3-vl:8b-instruct"
EXPECTED_DIGEST = "0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319"
EXPECTED_RUNTIME = "0.32.1"

PAGE_IMAGE_ID = "image-1"
GOLD_SENTINEL = "semread-001b-gold-sentinel-4f21"
CASE_SCHEMA = "semread-001b-case/1"

IMAGE_MAX_SIDE = 1280          # development'ta sabitlenir; final koşuya kadar değişmez
NUM_PREDICT = 2048

# Üretim ayarları: taşıma katmanı bu değerlerden kurulur (kopyası tutulmaz).
SETTINGS = {"num_ctx": 8192, "temperature": 0.0, "top_p": 1.0, "seed": 20261004,
            "num_predict": NUM_PREDICT, "keep_alive": "5m", "image_max_side": IMAGE_MAX_SIDE,
            "images_layout": "per_image_message_labeled", "image_label_prefix": "Image ID: ",
            "input_strategy": "single_full_page"}

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
