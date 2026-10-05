"""SEMREAD-001D — **tahmin üreten sözleşme** (PLAN-15 §9/§10).

Bu modül, ham tahminin byte'larını/içeriğini değiştirebilecek sabitlerin **tek** yeridir:
model etiketi, beklenen digest, beklenen runtime, üretim ayarları, görüntü işleme sözleşmesi ve
çağrı düzeni. `producer_identity()` bu dosyayı hash'ler.

Kural: buradaki bir değeri değiştirmek ham tahmini geçersiz kılar. Değerlendirme, kabul kapıları,
rapor üretimi ve referans doğrulaması bu dosyada **yaşamaz** — onlar `evaluation_identity()`ye girer.
Böylece yalnız evaluator/gold düzeltmesi geçerli ham tahmini yeniden üretmeyi gerektirmez.

Sürüm `/1` (SEMREAD-001D, PLAN-15 §9/§12): bu deney **semantic-content-aware full-page V/VE**
davranışını test eder — şema/reader `/3` + prompt v3 (semantic-empty aday geçersiz ·
semantic claim ≠ evidence-only · prompt semantic-first · no-guess korunur; tanım
`semantic_candidates.py` version notes'unda). Üretim zarfı (model/digest/runtime/ayarlar) **001C
kapanış zarfından birebir devralınmıştır ve değişmez** (PLAN-15 §10): 001D'nin tek bağımsız
değişkeni semantik sözleşmedir.

**HISTORICAL — 001C (READ-ONLY kapalı):** 001C'nin iki katmanlı revizyon tarihi (ölçümlü dev zarf
revizyonları + paylaşımlı requalification zarfı) ve kapanış kaydı `eval/semread_001c_closure.json`
closure artifact'ında, `report.md` §3'te ve `docs/HERMES_SEMREAD_001C_HANDOFF.md` §1t'de tutulur.
Sabitlerin gerekçe özeti: 001B'de gönderilen 19 çağrının 11'i `done_reason=length` ile kesilmişti →
`num_predict` ölçümle 2048→8192 (plate-VE 3072'de son adayın ortasında kesildi → 4096 → payı dar →
5120; elbow-V 5120'de de kesildi → 8192). `num_ctx` 12288→22528: flange-VE 14.121 token'lık prompt
ile 12288 ctx'te HTTP 400 (`exceed_context_size_error`) aldı; 14.121 + 8.192 = 22.313 ≤ 22.528 —
en büyük bağlam körlemesine seçilmedi. Döngü kırıcı prob taramasıyla bulundu (1.25 kırmadı /
1.6 boşalttı / 1.4 durdu ama plate-VE'nin zengin yanıtını kıstı; kol-başına V 1.4 / VE 1.25 seçimi
HISTORICAL'dır) ve final zarfında **paylaşımlı** `repeat_penalty = 1.25` + `repeat_last_n = 512`
olarak sabitlendi; döngü sampling ile değil yapısal çıktı sözleşmesiyle de sınırlanır
(`items.maxItems = 32` + kopya kuralı). Zaman aşımı hiyerarşisi: MODEL 3000 s < CASE 5400 s <
RUN 14400 s (lab case tavanı 7200 s). `generation_settings(V) == generation_settings(VE)`
invarianttır; kollar arası izin verilen fark yalnız kanıt katmanıdır.

001B sözleşmesi (`semread-001b-run-contract/3`) `docs/PLAN-11.md` kaydında donmuştur; 001C sürümü
(`semread-001c-run-contract/1`) closure artifact'ında tarihsel kayıttır. Bu sürüm 001D deneyinin
kimliğidir.
"""

from __future__ import annotations

# PLAN-15 §9/§12: 001D run-contract kimliği. Bump, `producer_identity()`yi de yeniler (dosya
# hash'i kimliğe girer); üretim zarfı sabitleri DEĞİŞMEZ (§10).
CONTRACT_VERSION = "semread-001d-run-contract/1"

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
# HISTORICAL revizyon (PLAN-12 §19 → PLAN-13 §5): 2048 körlemesine yükseltilmedi; 001B'nin ölçülen
# kesilme tavanına göre 3072 seçildi; `dev-plate-pocket-VE` 25 satırlık tabloda 3072'nin tamamını
# kullanıp **son adayın ortasında** kesildi (state=truncated_output) → 4096; payı dar → 5120;
# `dev-flange-elbow-V` 5120'de de kesildi → **8192** (ctx da 20480→22528; flange 14.121 + 8.192 =
# 22.313 ≤ 22.528). Kabul yalnız `done_reason == stop`; hedef: başarılı eval_count ≤ 0.8 ×
# num_predict (8192 → 6553).
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

# VLM döngü kırıcı — **ORTAK** (PLAN-13 §4/§6): kol-başına repeat_penalty kaldırıldı. Final
# zarfında `generation_settings(V) == generation_settings(VE)` zorunludur; döngü sampling ile
# değil yapısal çıktı sözleşmesiyle (items.maxItems + kopya kuralı, PLAN-13 §5) sınırlanır.
# Ölçüm geçmişi (HISTORICAL — zarf #7 karar kaydı): V 1.25 → elbow tekrar döngüsü (30 özdeş aday,
# 8192'de kesildi); 1.6 → yanıt boşaldı (25 token, items:[]); 1.4 → probda temiz durdu ama
# plate-VE'nin 41 adaylık zengin yanıtını 175 tokene kıstı. Ortak değer 1.25'tir (gerekçe aynı:
# VE zengin rejimini korur; V'nin döngüsünü yapısal cap keser). Requalification (2026-10-05) bu
# zarfla koşuldu: paylaşımlı ayar 8/8 ✓, stop 8/8 ✓, resmî §8 kapısı 7/8 (elbow-VE koordinat
# ihlali) → 001C final yok (PLAN-13 §7); deney READ-ONLY — değerler kapanıştan sonra değişmez.
# Pencere 512: döngü item'ı ~230-580 token; varsayılan 64'lük pencere tekrarı hiç görmez.
REPEAT_LAST_N = 512
REPEAT_PENALTY = 1.25


def generation_settings(arm: str) -> dict:
    """Kola göre üretim ayarları — **tek kaynak** (PLAN-13 §4/§8).

    `generation_settings(V) == generation_settings(VE)` otomatik invarianttır: kollar arasında izin
    verilen fark yalnız kanıt katmanıdır (evidence_mode, overlay, gözlem tablosu, kanıt prompt
    bölümü, görüntü sayısı) — hiçbiri üretim ayarı değildir. `arm` yalnız doğrulama içindir; dönen
    ayarlar kol-farkısızdır.
    """
    if arm not in ARM_VARIANTS:
        raise ValueError(f"bilinmeyen kol: {arm}")
    return {"model": MODEL, **SETTINGS,
            "repeat_penalty": REPEAT_PENALTY, "repeat_last_n": REPEAT_LAST_N}


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
