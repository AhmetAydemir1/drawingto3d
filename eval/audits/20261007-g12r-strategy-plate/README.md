# G12R — bağımsız inceleme düzeltme turu (G12R-01 … G12R-05)

Bu dizin, `20261007-guided-g12-2-independent-review` incelemesinin beş bulgusunun düzeltilmesinin
kanıtıdır. Eski kanıt dizini (`20261007-g12-strategy-plate/`) **değiştirilmedi**: bu tur kendi taze
Plate kabulünü ve kendi gerçek Chrome koşusunu ayrı dizine yazar (incelemenin istediği gibi).

Kural: her bulgu için önce başarısız regresyon, sonra generic düzeltme. Tarihsel manifest, dondurulmuş
evaluator, G9/G11 dizinleri ve `eval/metrics.py` bu turda değişmedi.

## Bulgu → düzeltme → kanıt

| Bulgu | Düzeltme (ürün) | Regresyon | Kanıt |
| --- | --- | --- | --- |
| **G12R-01** — onaydan sonra normal kayıtlar reddediliyor (kanıttaki `10.0` tarayıcıda `10` oluyor) | `guided._strategy_fingerprint` artık doğrulanmış alanları **değer** olarak karşılaştırır (`model_dump(mode="json")`), dizgi değil; `10.0 == 10` ve anahtar sırası serbest, uydurulan `strategy_key` yine reddedilir | `tests/test_g12r_review_fixes.py` — 5 test (tur geçer, değişen tür reddedilir, uydurma anahtar reddedilir, ikinci onay tek satır + sunucu anahtarı, turdan sonra normal kayıt) | gerçek Chrome: `browser/ui-run.log` adım **C** (kalınlık 20 kaydı geçti, `strategy_key_kept: true`, durum «Karar kaydedildi.») |
| **G12R-02** — `redundant` onayı metin/bölge/dayanak değişince hâlâ kapsamı kapatıyor | Onay artık **sunucunun yazdığı pin** ile bağlı: kendi okuması (transcription revizyonu + bölge) ve dayanağın onaylandığı içerik (`decision:<ad>` → değer anlık görüntüsü; callout → revizyon + bölge). Üç sonuç: kendi okuması değişti → `stale` + yeni kategori `stale_scope_claim`; dayanak değişti → `invalid_duplicate` (`stale_duplicate_reference`); pinsiz (şema 4) onay kanıtlanamaz → yine sorulur. Şema 4 → **5** (`duplicate_pin`), içe aktarmada pin istemciden alınmaz | `tests/test_g12r_review_fixes.py` (7 test: değer değişimi, metin, bölge, yeniden onay, undo, zincir, kategori sözleşmesi) · `tests/test_callout_coverage.py` (pinsiz şema-4 testi dahil) | gerçek Chrome: **C2** (değer ayağı: kalınlık 20 → dayanak sorusu), **E** (okuma ayağı: metin 30,00 → `stale` + üretim kapandı), **F** (aynı dayanakla yeniden onay → kapsam kapandı, pin `kind: callout, revision: 3`) |
| **G12R-03** — kabul betiği kalan callout'ları toplu kapatıyor | Yeni betikte reçete dışı satırlar **yazılı listeden** (`NON_MODEL_RECIPE`, gerekçesiyle 24 satır) karara bağlanır; listede olmayan satır `unexpected_rows()` ile kabulü DURDURUR. `_reason_for` varsayılanı kaldırıldı; eski betiğe tarihsel yönlendirme notu düşüldü | `tests/test_g12r_acceptance_discipline.py` (3 test: bilinmeyen satır durdurur; paftanın bugünkü 33 ipucu tam kapsanır; her satırın kendi gerekçesi var, varsayılan yok) | taze Plate kabulü `acceptance.log` adım **1b** (`unexpected_rows: []`, `written_rows: 24`) + **1c** (36 satır) |
| **G12R-04** — producer'ın varsayılan sürücüsü G11 koşucusu | `produce_case.DEFAULT_DRIVER = eval/g12_runner/g12_runner.py` (kaynak-only); `refuse_legacy_driver()` tarihsel G11 sürücüsünü G12 üretici yolunda **reddeder** (çıkış 4, hiçbir dosya yazılmadan). Tarihsel `g11_runner.py` değişmedi | `tests/test_g12_runner_boundary.py` (+3 test: varsayılan G12 sürücüsü; G11 reddi ve yazımsızlık; **gerçek varsayılan komut** sahte uygulamayla uçtan uca) | adım adım: koşu kaydı `driver_ran: true`, `reference_checked: true`; istek sırası yalnız `open → callout → strategy → readiness`; tarihsel G11 `cases/` dizini değişmedi |
| **G12R-05** — v2 reçete uygulanmayan dolu alanları sessizce kabul ediyor | Dolu `profile_actions`/`view_decisions`/`dimension_bindings`/`feature_links` **oturum açılmadan** açık hatayla reddedilir; `strategy_decision` uçtan uca uygulanır (`/api/guided/strategy`, yalnız `kind`); `notes` içinde katı model dosyası adı geçemez | `tests/test_g12_recipe_v2.py` (+4 test; boş alanlar hâlâ geçerli) + sözlük kayma koruması (`STRATEGY_KINDS ⊆ build_strategy.KINDS`) | aynı uçtan uca testte sürücü `set_strategy` isteğini gerçekten yollar (`/api/guided/strategy` görüldü) |

## Taze kabul koşuları

- **Plate kabulü (PLAN-25 §44, G12R-03 disipliniyle)**: `g12r_strategy_plate_acceptance.py` →
  **11/11 PASS** (`acceptance.log`, `g12r-strategy-plate-steps.json`).
  Akış: kontur + ölçek (100,00) + kalınlık (15) + izleme → callout kararları (reçete 9 satır +
  yazılı liste) → kapsam kapanır → strateji yokken üretim reddedilir → `extrude_profile` onayı →
  üretim → STEP yeniden açılır → dondurulmuş evaluator (**9/9**, `step_reopened` dahil).
  Parça: 120,011 × 80,002 × 15 · 4 delik (Ø6,8) · 1 cep (Ø50) · STEP 52.008 bayt,
  sha256 `c05da6f2…` (`out/part.step`, `out/plate-regression-verdict.json`).
- **Gerçek Chrome (UX değişti, §97/8)**: `browser/ui_acceptance.py` → bkz. `browser/ui-run.log`
  ve `browser/README.md`. A…G adımları R-01 ve R-02'nin iki ayağını canlı ölçer.
- **İlgili süit (incelemenin kendi komutu)**: `test_build_strategy` + `test_callout*` + `test_guided*` +
  `test_g11*` + `test_g12*` → **615 passed / 212,84 s / EXIT=0** (`pytest-relevant.log`; incelemedeki
  589 → +26: bu turun regresyonları).
- **Geniş regresyon**: `pytest -q tests -k "not semread"` → **1569 passed / 339 deselected /
  1614,08 s (26:54) / EXIT=0** (`pytest-broad.log`; 1543 → 1569: +26).

## Sözleşme kayması (kayıt için)

- `CALLOUT_SCHEMA_VERSION` **4 → 5**: şema-4 onayları pinsizdir ve kapsamı kapatmaz; kullanıcıdan
  yeniden onay istenir (satırın kararı silinmez — PLAN-24 §11 durur).
- Yeni readiness kategorisi **`stale_scope_claim`** («satırın okuması değişti; kapsam kararını yeniden
  onaylayın») + panel görev adı **«Kapsam kararını yeniden ver»**.
- Değer ayağı ŞEMA-5 onaylarında *varlık* değil *içerik* denetler: `decision:thickness` gibi dayanak
  yalnız onaylandığı değer duruyorsa kapsar.
