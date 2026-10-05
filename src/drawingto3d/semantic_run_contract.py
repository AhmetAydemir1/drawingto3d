"""SEMREAD-001C — **tahmin üreten sözleşme** (PLAN-12 §13/§19).

Bu modül, ham tahminin byte'larını/içeriğini değiştirebilecek sabitlerin **tek** yeridir:
model etiketi, beklenen digest, beklenen runtime, üretim ayarları, görüntü işleme sözleşmesi ve
çağrı düzeni. `producer_identity()` bu dosyayı hash'ler.

Kural: buradaki bir değeri değiştirmek ham tahmini geçersiz kılar. Değerlendirme, kabul kapıları,
rapor üretimi ve referans doğrulaması bu dosyada **yaşamaz** — onlar `evaluation_identity()`ye girer.
Böylece yalnız evaluator/gold düzeltmesi geçerli ham tahmini yeniden üretmeyi gerektirmez.

Sürüm `/1` (SEMREAD-001C, PLAN-12 §19): üretim zarfı 001B'nin **ölçülmüş** tavanlarına göre
yeniden seçildi ve dev ölçümüyle iki kez revize edildi. 001B'de gönderilen 19 çağrının 11'i
`done_reason=length` ile kesildi (10'u 2048 tavanında, biri bağlam tavanında). 001C dev'de:
`dev-plate-pocket-VE` 3072'de son adayın ortasında kesildi → `num_predict = 4096`; `dev-flange-book-VE`
14.121 token'lık prompt ile 12288 ctx'te HTTP 400 (`exceed_context_size_error`) aldı → `num_ctx = 20480`
(en kötü ölçülen VE prompt'u 14.121 — dev-flange-book; elbow ≤11,8k, drawing-2 ≤7,7k tahmin üst sınırı;
14.121 + 4.096 = 18.217 ≤ 20.480, %11 pay). En büyük context körlemesine seçilmez (§19.3): değerler
ölçümlü, gerekçesi resources.json `protocol` bloğunda ve deney kaydında izlenir.
001B sözleşmesi (`semread-001b-run-contract/3`) `docs/PLAN-11.md` kaydında donmuştur; bu sürüm
001C deneyinin kimliğidir.
"""

from __future__ import annotations

CONTRACT_VERSION = "semread-001c-run-contract/1"

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
# PLAN-12 §19: 2048 körlemesine yükseltilmedi; 001B'nin ölçülen kesilme tavanına göre 3072 seçildi,
# sonra 001C dev'de ölçüm 4096'ya çıkardı: `dev-plate-pocket-VE` 25 satırlık tabloda 3072'nin
# tamamını kullanıp **son adayın ortasında** kesildi (state=truncated_output; ~7,7 tok/s M1'de
# 4096'nın en kötü karşılığı ~530 s < 900 s model tavanı). Kabul yalnız `done_reason == stop`;
# hedef: başarılı eval_count ≤ 0.8 × num_predict (4096 → 3277).
NUM_PREDICT = 8192

# Üretim ayarları: taşıma katmanı bu değerlerden kurulur (kopyası tutulmaz).
#
# `top_p` ve `seed` **bilerek yoktur** (PLAN-3 §4 alternatifi): taşıma katmanı (`ChatSettings` →
# `_chat_request`) bu iki seçeneği Ollama `options` gövdesine koymuyor. Donmuş sözleşmeye yazıp
# göndermemek, kaydetmenin gerçeği anlatması kuralını çiğnerdi. Desteklenmeyen bir donmuş ayar
# eklenirse `write_live_attempt()` gönderimi durdurur (`blocking_kind=unsupported_frozen_setting`).
SETTINGS = {"num_ctx": 22528, "temperature": 0.0,
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
