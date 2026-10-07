# G9 UX turu — teslim (2026-10-07)

**Sonuç: PASS.** Dar UX turu, `DELIVERY-PLAN.md`'de ilk koşudan önce dondurulan ölçütlerle, taze
oturum ve **gerçek Chrome** üzerinde uçtan uca yürüdü: **33/33 tarayıcı adımı PASS** (`ux-steps.json`,
koşu 04), G9'da dondurulan CAD regresyonu aynı üretilmiş STEP üzerinde **tüm kapılar PASS**
(`verdict.json`), callout/guided regresyon seti **483 passed / 144 s** (`logs/regression-callout.log`).

## Ne değişti (ürün)

| Akış | Ürün değişikliği | Adımlar |
|---|---|---|
| next-unresolved | `#callout-next`: karara bağlanmamış alanlar arasında sırayla ilerler; sayaç düğmede ve özet satırında | 6 |
| explicit bulk ignore | `set_ignored_many` komutu + iki adımlı `#callout-ignore-many` (ilk tık yalnız onay ister); kararlı satıra dokunmaz; tek geçmiş adımı, tek revizyon; her satır kendi `callout_reviews` kaydı + kendi `bulk=true` log satırı | 23–27 |
| makine ipucu tek-tık | `transcribe` + `accept_hint`: sunucu metnin *bu callout'un kendi* ipucuyla birebir aynı olmasını doğrular; log kabul edilen ipucunu (`accepted_hint`, `machine_text_hint`) adlandırır; `#callout-hint-save` | 16–20 |
| readiness checklist | Hazırlık maddeleri kategori rozetli ve `Git` düğmeli; tıklama, *sunucunun kendi* `action`/`reason` değerine göre ilgili denetime odaklanır (callout seçimi + `#callout-text` / `#target-panel` / `#profile` / …) | 3–5 |

Sessiz filtreleme yok: 45 aday 45 satır olarak kalır (adım 2, 28); kapsam kararları yalnız kullanıcı
eylemiyle yazılır ve geri alınabilir. Vakaya özel kural eklenmedi; tüm değişiklikler generic
komut/arayüz düzeyindedir. `İpucunu metne al` yolu (taslağa alma) korunur — tek-tık yalnız *kabul*
yoludur.

## Ölçülen yük (aynı plate, G9 ile karşılaştırma)

| Ölçü | G9 koşusu | UX turu | Kanıt |
|---|---|---|---|
| Kapsam kapatma | 37 tek-satır akışı (seç + ignore ×37) | 1 tek-satır (fragman) + **1 toplu eylem: 36 satır, 2 tık, tek revizyon** (21→22) | 13, 23–24 |
| Elle yazılan metin | 7 | **4** (delik, cep + iki spacing düzeltmesi) | 11, 14, 21–22 |
| Tek tıkla kabul edilen ipucu | 0 | **4** (M8 notu + `80,00` + `60,00` + `8,00`) | 16, 18–20 |
| Toplam aday / kapsam dışı | 45 / 43 | 45 / 43 (değişmedi) | 1–2, 28, 32 |

Adım 32 bunu sunucu log'undan sayarak kaydeder: `typed_texts=4, hint_single_clicks=4,
single_ignores=1, bulk_rows=36` (G9: `7 / 0 / 37`). Hazırlık özeti (adım 29):
`45 callout derlendi · 5 delik · 0 ölçü bağı · 43 kapsam dışı`; STEP `build_status=complete` (adım 30);
konsol hatası 0, reddedilen istek 0 (adım 33).

## Koşu dürüstlüğü

- **Koşu 01** sürücü tarafında durdu: (a) next-unresolved beklentisi, kontrol listesi testinin
  bıraktığı başlangıç seçimini yok sayıyordu; (b) `history` public payload'da yok. Ürün tarafında
  bulgu yok; düzeltme sürücüde. Log: `logs/run-01-stopped.log`.
- **Koşu 02**: 32/33 — kalan tek satır, log satırının *kararın taşındığı andaki* revizyonu
  damgaladığını gösterdi (bir komut = tek damga; tasarım böyle). İddia buna göre düzeltildi; ürün
  değişmedi. Log: `logs/run-02-stopped.log`.
- **Koşu 03 ve 04**: 33/33 PASS. Koşu 04'te yalnız kanıt ekran görüntüleri callout panelini
  gösterecek şekilde hizalandı (kriter değişmedi). Teslim kaydı koşu 04'tür.

## Kanıt dosyaları (bu klasör)

`DELIVERY-PLAN.md` (donmuş ölçütler) · `ux_acceptance.py` · `ux-steps.json` (33 adım) ·
`ux-00…14-*.png` (15 ekran görüntüsü) · `session-public.json` · `review-bundle.json` · `part.step`
`plan.json` `plan-audit.json` · `verdict.json` · `logs/` (red-01, backend-green, frontend-green,
regression-callout, run-01-stopped, run-02-stopped, run-03, run-04, cad-regression).

Delik/cep zinciri pakette: `raw_text \"4 x Ø6,80 THRU ALL\"` → parse `callout-parser/2, parsed,
diameter 6.8, count 4, thru` → `confirmed_target circle_group g9,g11,g10,g12 (user_click)`;
cep: `\"Ø50 8 DEEP\"` → blind derinlik 8, Ø50 → `circle g8 (proposal)`.

## Komutlar (yeniden üretim)

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app                     # 127.0.0.1:8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-ux-round about:blank
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-ux-round/ux_acceptance.py
.venv-cad/bin/python eval/audits/20261007-guided-g9-plate/plate_regression.py \
  eval/audits/20261007-guided-ux-round/part.step \
  "examples/pdf with steps/5/plate with a pocket.STEP" \
  eval/audits/20261007-guided-ux-round/verdict.json
```

## Durum

**UX turu PASS.** Gerçek-tarayıcı kabulü ve mevcut callout regresyonları yeşil; G10 manifesti
(`eval/guided_10_manifest.json`) bu turda **değişmedi** ve G11 için dondurulmuş durumda. Sıradaki iş
**G11**: dondurulmuş manifest ile ilk 10-pafta koşusu.
