# 20261007-g12-strategy-plate — G12.2 kabulü (PLAN-25 §44)

Taze Plate oturumu, gerçek ürün yolu: **callout incelemesi → açık üretim biçimi → üretim → STEP
yeniden açma → dondurulmuş evaluator**. Sürücü: `g12_strategy_plate_acceptance.py`
(`.venv/bin/python g12_strategy_plate_acceptance.py`; çıktı `acceptance.log`, adım kayıtları
`g12-strategy-plate-steps.json`).

| adım | ne kanıtlar | sonuç |
|---|---|---|
| 0 | kontur (`outline_1`) + ölçek (100,00 · t0) + kalınlık 15 + izleme onayı kaydedilir | PASS |
| 1 / 1b | reçetedeki her ipucu paftanın callout'uyla eşleşir; reçete DIŞINDA kalan 36 satır da **tek tek adıyla** karara bağlanır (örtük/blanket kapatma yok) | PASS |
| 2 | kapsam kapanır: kalan tek madde `missing_build_strategy`; hiçbir callout sorusu kalmaz | PASS |
| 3 / 4 | strateji yokken üretim BAŞLAMAZ; `build` adı konmuş soruyla reddedilir (örtük extrude yok) | PASS |
| 5 | kullanıcı `extrude_profile` onaylar; anahtarı ve geometri sürümünü SUNUCU sabitler (key 64 hex, geometry_version 3) | PASS |
| 6 | üretim tamam: STEP yazıldı, 1 katı, geçerli, ölçü 120,011 × 80,002 × 15 | PASS |
| 7 | STEP yeniden açıldı; **dondurulmuş evaluator 9/9 PASS** (`step_reopened` dahil) | PASS |
| 8 | parça 120 × 80 × 15, **4 delik** (Ø6,8) ve **1 cep** (Ø50) | PASS |
| 9 | gerçek Chrome: hazırlık listesi + strateji paneli + kaydetme gövdesi + tıklamayla üretim (`browser/`) | PASS 7/7 |

**TÜMÜ GEÇTİ 10/10**, exit 0. STEP sha256 `9629516aaa70f7e6…`; değerlendirici kararı
`out/plate-regression-verdict.json` (frozen evaluator: `eval/audits/20261007-guided-g9-plate/plate_regression.py`,
toleransları G12.0'da dondurulmuş — bu turda değiştirilmedi).

## Kapsam kararları (G12 sözlüğü, PLAN-25 §9–§13)

Üretimi bloklayan tek şey **gerçekten uygulanamayan** ölçüdür; zaten başka bir kararla temsil edilen
satır bunu SÖYLER ve dayanağını gösterir. Bu tur kabulünde:

- `4 x` → `not_model_input` (sayı parçası; metni `6,80 THRU ALL` kutusuyla okundu),
- `6,80 THRU ALL` → yazıldı + hedef dört daire (`g9,g10,g11,g12`) → `build_applied`,
- `50,00` → yazıldı (`Ø50 8 DEEP`) + hedef `g8` → `build_applied`,
- `M8 - 6H THRU ALL` → `redundant` → **Ø6,80 callout'u** (aynı dört delik; M8 dişin pilot çapı 6,8 mm),
- `80,00` / `60,00` / `8,00` → `redundant` → `decision:trace` (izlenen merkezler bu aralıkları zaten gerçekliyor),
- `1 00,00` → `redundant` → `decision:calibration` (aralık 100,00 olarak girildi),
- `1 5,00` → `redundant` → `decision:thickness` (kalınlık 15,00 olarak girildi),
- başlık bloğu (14 satır), görünüş/bölüm işaretleri (A–D) ve ölçü parçaları (1–6, 2026)

## Gerçek Chrome koşusu (§97/8: UX değişti)

`browser/` — hazırlanmış oturum üzerinden kullanıcı yolu, gerçek fare/klavye: hazırlık listesi strateji
maddesini gösterir (A), panel dört seçenek sunar ve döndürme/çok görünüş seçilemez (B), karar yokken
üretim kapalı (C), kaydetme gövdesi YALNIZ `{token, revision, kind}` (D), karar sonrası üretim gerçek
tıklamayla tamamlanır (E). **7/7 PASS, EXIT=0** — ayrıntı `browser/README.md`.

## İlgili süit (bu tur)

- `eval/audits/20261007-g12-strategy-plate/pytest-g12.2-relevant.log` — 23 dosya, **401 passed (129,80 s)**, EXIT=0
- `eval/audits/20261007-g12-strategy-plate/pytest-broad.log` — `pytest -q tests -k "not semread"` →
  **1543 passed, 339 deselected, 1637,22 s (27:17), EXIT=0**

## Not

`out/` bilinçli olarak sürüm kontrolü dışındadır (`.gitignore`: `out/`, `*.step`): kanıt, adım kaydı,
evaluator kararı ve log'lardır; STEP yeniden üretilebilir (`g12_strategy_plate_acceptance.py`).
