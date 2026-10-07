# G9 — Plate golden path · DELIVERY (sonuç raporu)

**Sonuç: PASS.** `PLAN.md` §15 akışı (drawing → candidates → transcription → parse → proposal →
confirmation → compile → build → STEP → evaluator) taze oturumda, **gerçek Chrome** ve **gerçek
CAD/STEP üretimiyle** uçtan uca yürüdü; dondurulmuş regresyon evaluator'ı tüm kapıları geçti.
Dondurulmuş ölçütler: `DELIVERY-PLAN.md` (ilk koşudan önce commit'lendi, sonuç görüldükten sonra
değiştirilmedi). Bu klasördeki her sayı gerçek koşu çıktısıdır.

## Koşular

| koşu | oturum | sonuç | kanıt |
|---|---|---|---|
| 1 | 390916ea… | Üretime ulaşamadı: paftanın kendi notu `4 x Ø6,80 THRU ALL` **parse edilemedi** (`unknown_tokens` — dilbilgisi `THRU ALL` bilmiyordu). EXIT=2; sapma kaydedildi. | `run1.log` |
| 2 | — | **Geçersiz** (operasyonel hata, ürün hatası değil): uygulama eski süreçle servis ediyordu (`Address already in use` — yeniden başlatma ilk denemede tutmamıştı). | `run2.log` |
| — | a8ced449… | Düzeltilmiş sunucu için HTTP ön kontrol: `preflight-parser-v2.json` → `callout-parser/2`, `parsed` (Ø6,8 · adet 4 · thru). | `preflight-parser-v2.json` |
| 3 | e754a64a… | **24/24 adım PASS** (EXIT=0): tüm kararlar gerçek tıklama/yazıyla; hazırlık kapısı temiz; üretim `complete`; konsol hatası ve reddedilen istek yok. | `run3.log`, `g9-steps.json`, `plate-*.png` |

## Düzeltme (çizime özel değil, genel — PLAN §15 "fail → generic fix → rerun")

Koşu 1'in kök nedeni: yeni G4 dilbilgisi, atölye çizimlerinin standart `THRU ALL` ifadesini
bilmiyordu — eski okuma katmanı (`ingest.parse_dimension_unit("4 x 6,80 THRU ALL")`) bunu zaten
okuyordu; dilbilgisi gerilemişti. Genel düzeltme (commit **1a40d86**): `ALL` yalnız `THRU/THROUGH`dan
hemen sonra tanınan bir niteleyici oldu; başka her yerde no-guess gereği bilinmez kalır
(`ALL`, `Ø8 ALL`, `ALL THRU` → `unknown_tokens`). `CALLOUT_PARSER_VERSION = "callout-parser/2"`
(v1 okumalar tasarımla bayatlar); PLAN §7/§8 güncellendi. Testler: parser 99 + callout/guided 463
yeşil; RED (18 kırık) → GREEN.

## Koşu 3 — kullanıcı kararları (hepsi gerçek UI girdisi; metinler çizimden)

| adım | karar | sonuç/kanıt |
|---|---|---|
| kontur | `outline_1`'e tıklandı (8 kenar, line/arc) | `$('profile').value === outline_1` |
| kalibrasyon | g9 ↔ g11 delik merkezleri; değer basılı `1 00,00` satırından (span t0) | 787.57 px = 100 mm → **7.8757 px/mm** |
| kalınlık | `15` (basılı `1 5,00`) | decisions.thickness = 15 |
| delik notu | `4 x Ø6,80 THRU ALL` yazıldı | v2 parse: diameter 6.8 · count 4 · thru; öneriler listelendi (T2: `daire grubu · g10,g11,g12,g9`); hedef **elle** seçildi: circle_group g9,g11,g10,g12 → `user_click`, `confirmed` |
| cep | `Ø50 8 DEEP` (üst görünüş Ø50 + kesitten derinlik 8) | parse: blind · depth 8; öneri `T1 · g8` **Onayla** ile → `proposal`, `confirmed` |
| diş notu | `M8 - 6H THRU ALL` yazıldı | parse `unsupported` (diş dilbilgide yok — uydurulmadı) → `Bağlama yok / desteklenmiyor` beyanı |
| basılı ölçüler | `100,00` `80,00` `60,00` `15,00` `8,00` okundu | linear parse; yaylı konturda v1 yalnız daire merkezi bağlar → beşi de "bağlanamaz" beyanı (karşılıkları: kalibrasyon, izlenen taslak, kalınlık, cep metni) |
| kapsam | `4 x` parçası + 36 zarf/başlık metni | `Bu callout değil` (beyan edilmiş dışlama) — hiçbiri sessizce düşmedi |

45 adayın tamamı çözüldü; hazırlık: **"Hazır: 45 callout derlendi · 5 delik · 0 ölçü bağı ·
43 kapsam dışı."** Üretim `complete` (`build-57-3a85ca0e`), sayfa üç bağlantıyı da sundu
(Taslak STEP / CAD planı / Geometrik kontrol), 3B önizleme canvas'ta çizildi (`plate-12-built.png`).

## Dondurulmuş regresyon — `verdict.json` (tümü PASS)

| kontrol | sonuç | ölçüt |
|---|---|---|
| tek geçerli katı | 1 katı, `isValid=True` | — |
| bbox | **120.011 × 80.002 × 15.0 mm** | her eksen ±0.2 mm |
| hacim | **124812.494 mm³** (referans 124825.417; %0.0104) | ≤ %0.5 (referans ve analitik nominal) |
| 4 geçişli delik | r=3.4; (10.009, 10.003) (110.009, 10.003) (10.009, 70.001) (110.009, 70.001); z 0→15 | r ±0.05; merkez ±0.3; spân ±0.1 |
| 1 kör cep | r=25.0; (60.009, 40.002); z **7→15** (üstten, derinlik 8) | r ±0.05; merkez ±0.3; spân ±0.1 |
| 4 köşe yuvarlatma | r=9.974–9.991, dört köşe, tam kalınlık | r ±0.3 (mürekkepten izlendi) |
| silindir envanteri | 9 mantıksal = referans 9; fazla/eksik yok | eşitlik |
| simetrik fark | hizalı **30.3 mm³** (%0.024); ham fark çerçeve kaymasından (min köşe ↔ merkezli) | hizalı ≤ %0.5 |
| mevcut evaluator | `eval/metrics.compare` PASS (vektör farkı ≤0.01 mm) | PLAN-20 §11.7 |
| STEP yeniden açılış | evaluator iki kez `importStep` + ürünün kendi `plan-audit.json`: `valid_solid ✓`, `export_round_trip ✓`, 5 kesim denetimi ✓ | PLAN §15 |

Ek zincir kanıtı (`review-bundle.json`, PLAN §14 tablosu): `raw_text "4 x Ø6,80 THRU ALL"` →
`semantic_parse {parser_version: callout-parser/2, status: parsed, diameter 6.8, count 4, thru}` →
`confirmed_target {circle_group g9,g11,g10,g12, evidence: user_click, confirmed}` →
freshness transcription/parse/target hepsi `current`. `plan.json`: `thickness=15` (kullanıcı),
kalibrasyon kaynaklı ölçek varsayımı 7.8757 px/mm, `hole_0..4` kesimleri; `session.json`:
manual `decisions.holes = []` — özellikler **yalnız** callout derlemesinden geldi.

## Komutlar (yeniden üretim)

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app                     # 127.0.0.1:8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-g9 about:blank
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g9-plate/plate_acceptance.py
.venv-cad/bin/python eval/audits/20261007-guided-g9-plate/plate_regression.py \
  eval/audits/20261007-guided-g9-plate/part.step \
  "examples/pdf with steps/5/plate with a pocket.STEP" \
  eval/audits/20261007-guided-g9-plate/verdict.json
```

## Kanıt dosyaları (bu klasör)

`DELIVERY-PLAN.md` (donmuş plan) · `run1.log` `run2.log` `run3.log` · `preflight-parser-v2.json` ·
`plate_acceptance.py` `plate_regression.py` · `g9-steps.json` (24 adım) · `plate-00…12-*.png` ·
`session.json` `session-public.json` `review-bundle.json` · `part.step` `plan.json` `plan-audit.json`
`part-projection.svg` · `verdict.json`.

## Durum

**G9 PASS.** Bağımsız kontrol için duruldu; **G10 açılmadı.** Açık işaretler: (1) run 2 yalnızca
operasyonel yeniden-başlatma hatasıydı, ürün kanıtı değildir; (2) yuvarlatma yarıçapları basılı
olmadığından izlemeden gelir (±0.03 mm) ve evaluator'da ±0.3 mm toleransla izlenir; (3) 5 basılı düz
ölçü bu sürümde callout→bağ yolundan derlenemez (yaylı konturda yalnız daire merkezi bağlanır) —
kapsam dışı beyan edildi, geometrideki karşılıkları evaluator'da doğrulandı.
