# G11R-01–05 düzeltme turu — rapor

- Tarih: 2026-10-07 · Başlangıç HEAD: `0ff46a8` · İnceleme: `eval/audits/20261007-guided-g9-g11-independent-review/`
- Kapsam: yalnız G11R-01…05. G9'a dokunulmadı; eski kanıtlar ve dondurulmuş manifest değiştirilmedi
  (inceleme dizini bu turda ilk kez commit'e alınır, içeriği aynen).
- Düzeltilmiş girdiyle yeniden koşum: `rerun-round2/` (ayrı run: reçeteler `rerun-round2/recipes`,
  kayıtlar `rerun-round2/cases`, görüntüler `rerun-round2/shots`, loglar `logs/rerun-round2`).

| Bulgu | Durum | Ana kanıt |
| --- | --- | --- |
| G11R-01 metrik paydası | düzeltildi | `eval/guided_10_report.md` (1/9), `tests/test_g11_report.py` |
| G11R-02 kalibrasyon | düzeltildi+koşuldu | `rerun-round2/cases/*.json`, `input_verification` blokları |
| G11R-03 oto-ilerleme | düzeltildi+tarayıcıda doğrulandı | `g11r03-ui-result.json` (8/8) |
| G11R-04 kanıt kaydı | düzeltildi | `recovered/`, runner kanıt yolları |
| G11R-05 hata sınıflaması | düzeltildi | `g11_evidence.py`, r2 kayıtlarında sıfır yanlış EVALUATOR |

Kabul kontrolü: `.venv/bin/python eval/audits/20261007-guided-g11-fixes/check_fixes.py` — tüm
kontroller yeşilken `acceptance.json` olarak saklandı. (Commit öncesi tek kırmızı: inceleme dizini
henüz untracked; commit ile kapanır.)

## G11R-01 — başarı oranının paydası

**Değişiklik.** `g11_report.py` yeniden yazıldı: `compute()` ana metriği artık donmuş manifestin
`expected_scope_class == "full_step"` kümesi (9 vaka) üzerinden hesaplıyor — STEP üretilemeyen,
build/evaluator hatası alan ve bekleyen vakalar paydadan düşülmüyor. Koşullu oran (yalnız verdict'lı
vakalar) ayrı adla (`conditional_correct_rate_among_verdicts`) ve "ana metrik DEĞİLDİR" notuyla
raporlanıyor; JSON'a `denominator_source`, `unproduced_full_step` alanları eklendi.

**Sonuç.** `GUIDED_CORRECT_STEP_RATE = 0.111 (1/9)` — önceki rapor 1/6 yayımlıyordu. Koşullu oran
bilgi satırı: 1/6 = 0.167. Yeniden üretilen teslimler: `eval/guided_10_report.md`,
`eval/guided_10_report.json`.

**Regresyon.** `tests/test_g11_report.py` — sentetik ağaçta 3 full_step biri build-hatalı + biri
bekleyen + bir callout_scope_only vaka; payda 3, oran 1/3, koşullu oran ayrı alan, scope-dışı vaka
metriğe girmez. Ayrıca yayımlanan `eval/guided_10_report.json` (payda 9, oran 1/9) ve manifestin
9 full_step + 1 callout_scope_only kaldığı çivilenir. Sonuç: 4 passed.

## G11R-02 — flange ve exercise-51 kalibrasyonu (doğrulanmış girdi + yeniden koşum)

**Doğrulama (çizim + piksel, çift yönlü).**
- **Flange:** `R35.00` cıvata dairesi yarıçap ölçüsü; uçları g385 (merkez) ↔ g386 (cıvata deliği)
  merkezleridir — kalibrasyonun kaydettiği iki nokta arası 207,35 px; 207,35 ÷ 35 = **5,924 px/mm**.
  Çapraz kontrol: dış Ø100,00 ↦ 295,87 px = 5,917 px/mm (fark %0,1). Eski resmî koşunun OCR'ı
  "90.00" (t4) demişti; çizimde o ölçü **50.00**'dır ve bu bağ artık kullanılmıyor.
- **Exercise-51:** "40" okuması **70.00**'dır (hub merkezi ↔ 30°'deki alt-sol göbek merkezi;
  274,80 px ÷ 70 = **3,926 px/mm**). Çapraz kontrol: 80.00 ↦ 315 px (3,938), 150.00 ↦ 590,5 px
  (3,937) — üç ölçü ±%0,4 içinde. 40 mm bu paftada hiçbir çapraz kontrolde tutmaz.
- Belirsiz değerler kesin karar olarak kullanılmadı: her iki reçeteye `input_verification` bloğu
  (kanıt zinciri + `replaces` kaydı) eklendi; runner bu bloğu + reçete sha'sını vaka kaydına taşıyor.

**Değişiklik.** `g11_runner.py`'ye elle giriş kalibrasyon yolu (`calibration.manual_value` — "Ölçüyü
ben gireceğim" + `#cal-value`); düzeltilmiş reçeteler `rerun-round2/recipes/{flange,exercise-51}-raster.json`;
`run_official.py --round <ad>` ile koşular tur dizinine ayrılır.

**Yeniden koşum sonuçları (gerçek koşu, ayrı run).**
- flange-r2: build ok; kalibrasyon `value=35` (ilk/son noktalar eski kayıtla **aynı** — yalnız değer
  90→35 düzeltildi); bbox `[20, 30.907, 30.907]` (eski hatalı ölçek 79,475 mm disk üretiyordu);
  verdict CAD_WRONG — kalan fark artık girdi hatası değil, tek-disk arketipi (G12 konusu).
- exercise-51-r2: build ok; `value=70`; bbox `[15, 49.978, 49.978]` (hub Ø49,98 — doğru ölçek);
  verdict CAD_WRONG — aynı şekilde arketip sınırı.
- Eski koşu sonuçları silinmedi; eski kayıtlar git'te aynen (aşağıda doğrulama).

**Regresyon.** `check_fixes.py` G11R-02: r2 kayıtlarında reçete elle-değeri = kayıt kalibrasyon
değeri, span × çapraz kontrol ppm aralığı, `recipe_sha256` eşleşmesi, `input_verification` ve
reçete notlarının kayda taşınmış olması; eski resmî kalibrasyonların resmî koşunun
`cases/*/session-public.json` artefaktında (flange 90/t4, ex51 40/t0) yerinde durması. Ayrıca `tests/test_g11_evidence.py` runner wiring'i çiviler.

## G11R-03 — "Bu bir ölçü/not değil" sonrası oto-ilerleme

**Kök neden.** Karar satırı görünür listeden düştüğünde (ihmal edilenler gizliyken)
`busy(false) → render() → renderCallouts()` seçimi temizliyordu; `advanceAfterDecision`'ın
`selectedCallout === previousId` kapısı bu yüzden erken dönüyor ve sıradaki açık alan açılmıyordu.

**Değişiklik (`src/drawingto3d/static/guided.js`).** Karar öncesi görünür sıra (`previousOrder`)
taşınır; ilerleme bu sıradan, kararın kendi konumundan başlar (sarmalı). Kullanıcı başka satıra
geçtiyse (`selectedCallout` ≠ previousId ve boş değilse) yine ilerlenmez; çözülmemiş satırdan
zıplanmaz (§6.4 korunur).

**Gerçek tarayıcı doğrulaması.** `g11r03_browser_check.py` (3 callout'lu fixture; gerçek CDP
tıklamaları) — **8/8 adım geçti** (`g11r03-ui-result.json`; görüntüler `g11r03-ui-00-baseline.png`,
`g11r03-ui-01-after-ignore.png`, `g11r03-ui-02-all-decided.png`):
S1 orta satır ignore → seçim C3'e geçti (eski hata: seçim boşta kalırdı) · S2 elle "Sonraki eksik"
sarmalı · S3 ipucu-ignore → yalnız açık alan kaldı · S4 göster-açık + son satır (satır seçili kalır) ·
S5 geri al (yerinde kalır) · S6 göster-kapalı + son satır (liste boşalır, detay kapanır) ·
S7 sunucu kaydı: 3/3 ignored, 5 revizyon.

**Regresyon.** `tests/test_guided_callout_ux_advance.py` — servis edilen guided.js Node'da DOM
saplamalarıyla koşar; 7 senaryo (orta satır/asgari, son satır, sarma, göster-açık, kullanıcı
taşındı, çözülmemiş satır, sıra dışı satır). `tests/test_guided_html.py`'deki R03 sözleşme
assert'leri yeni forma güncellendi (eski `advance=previous` çivisi tarihsel kaldı).

## G11R-04 — başarısız vakalarda kanıt + kurtarma etiketi

**Değişiklik.** `g11_runner.py` artık build sonucundan bağımsız olarak her vaka sonunda
`session-public.json`, `review-bundle.json`, `readiness.json` yazar (paylaşımlı stdlib modülü
`g11_evidence.py`); kayda `session_token`, `session_origin`, `recipe_file`,
`recipe_sha256`, `recipe_notes`, `input_verification`, `readiness`, `browser_signals` eklenir.
Yalnız STEP/plan indirmesi gerçek üretime bağlı kalır. Başarısız build'de sunucunun kendi yanıtı
CDP `Network.getResponseBody` ile yakalanıp `build_error_response` alanına yazılır.

**Eski kanıtların kurtarılması (etiketli).** Resmî koşuda kanıt yazılmamış 4 vaka değişmemiş
oturumlardan kurtarıldı: `recovered/{exercise-13-raster,exercise-17-raster,my-part-raster,flange-elbow-90-raster-noref}/`
— her biri `RECOVERY.json` ile **"recovered-after-run"** etiketli (kurtarma zamanı, kaynak oturum,
`source_sha256_match`, oturum dosyası önce/sonra sha'sı → `session_untouched: true`), koşu-anı
kanıtı gibi sunulmuyor. Sunucunun reddediş metni aynı kapı zinciri okuma modunda yeniden oynatılıp
`server-error-recompute.json` olarak saklandı (etiketli: "koşu-anı yanıtı kayıtlı değildi"):
ex13 + ex17 → `make_plan` (kontur geçersizliği), my-part + elbow → `readiness` (ölçek eksik).

**Regresyon.** `tests/test_g11_evidence.py` (7+1 test): kanıt üçlüsünün build'den bağımsız yazımı,
`EVIDENCE_ALWAYS` sözleşmesi, `recovered_note` etiketi (zaman+kaynak+`not_run_time_evidence`),
runner wiring'i (kanıt çağrıları, kayıt alanları, yuvarlak-dizin kayıt yolu, kapı-sonrası token
yakalama) ve eski hatalı yolların yokluğu. `check_fixes.py` G11R-04: r2 kayıtlarında kanıt
üçlüsü+token var; 4 kurtarma dizini etiketli + 5 dosyası tam.

## G11R-05 — tarayıcı/ağ vs değerlendirici hata ayrımı

**Değişiklik.** `g11_evidence.classify_signals`: console/network sinyalleri `assets`
(favicon/statik → UI telemetrisi), `api_failures` (/api yanıtları, durum koduyla), `page_errors`
(gerçek JS hataları), `cancelled` (iptal/status 0) kovalarına ayrılır — hiçbiri hata kodu üretmez.
`EVALUATOR` etiketi yalnız değerlendirici süreci/ayrıştırma başarısızlığından gelir. Build hataları
sunucunun kendi metniyle sınıflanır: `CONSTRAINT_UNSUPPORTED` / `CONSTRAINT_CONFLICT` /
`CAD_UNSUPPORTED` (`classify_build_error`). Runner bu ayrımı kullanır; r2 kayıtlarında hata listesi
yalnız gerçek verdict hatası (`CAD_WRONG`) içerir — sıfır yanlış EVALUATOR.

**Tarihsel kayıtlar (değiştirilmedi).** Eski 4 EVALUATOR kaydı: flange + my-part yalnız favicon
404'ü, ex17 + ex13 favicon + build HTTP 400'ü "EVALUATOR" diye etiketlemişti; bunlar eski kanıt
olarak aynen duruyor — düzeltme ileriye dönük ve `recovered/*/server-error-recompute.json` eski
vakalar için gerçek reddi ayrıca belgeliyor.

## Doğrulama özeti (gerçek koşular)

- **Regresyon paketi:** `tests/test_callout*.py tests/test_guided*.py tests/test_g11_report.py
  tests/test_g11_evidence.py` → **510 passed** (134 sn) — önceki R01–R05/UX regresyonları dahil.
- **G9 yeşil:** plaka regresyonu donmuş toleranslarla **PASS**
  (`plate_regression.py`, kanıt: `~/.hermes/cache/scratch/g11fix/g9-plate-verdict.json`).
- **G11R-03 gerçek tarayıcı:** 8/8 (`g11r03-ui-result.json`).
- **Kabul kontrolü:** `check_fixes.py` — G11R-01…05 + eski-kanıt-dokunulmazlık, commit sonrası
  tümü yeşil (`acceptance.json`).
- **Eski kanıt dokunulmazlığı:** `git diff 0ff46a8..HEAD -- cases/ recipes-official/ shots/
  logs/official/ manifest` boş; resmî ex51/flange kayıtları tur aracının yol hatasından sonra
  HEAD ile **bit düzeyinde** eşitliği doğrulanarak geri yüklendi (sha karşılaştırması).

## Tur sırasında yakalanan ve düzeltilen koşu-aracı hataları (şeffaflık)

1. `g11_runner.py` koşu kaydını tur dizininden bağımsız resmî `cases/` yoluna yazıyordu: rerun-round2
   kayıtları oraya düştü → kayıtlar `rerun-round2/cases/` altına taşındı (`salvage_round2_records.py`),
   resmî kayıtlar git'ten geri yüklendi, runner düzeltildi + regresyon çivilendi.
2. 120 sn'lik token yoklaması ağır raster ingest'lerde token'ı kaçırıyordu (kayıtlar token'sız kaldı);
   token `session-public.json` artefaktından tamamlandı (kayıt notunda belirtilir), runner'a
   kapı-sonrası yakalama eklendi + regresyon çivilendi.

## Kalan açıklar / devredilen

- Eski resmî kayıtlarda `artifacts.session-public.json`/`review-bundle.json` alanları hâlâ yok —
  tarihsel kayıt bilinçli olarak değiştirilmedi; karşılığı etiketli `recovered/` dizinidir.
  İncelemenin `audit_g11.py`'si bu iki kontrolü eski kayıtlar üzerinde kırmızı göstermeye devam eder;
  düzeltilmiş durumun kabulü `check_fixes.py` + r2 kayıtları üzerinden doğrulanır.
- ex51-r2 ve flange-r2 verdictleri hâlâ `CAD_WRONG`: girdi artık doğrulanmış; kalan fark tek-disk
  arketipinin yeteneği — **G12 kapsamı**.
- ex13/ex17'nin gerçek kök nedeni (kontur geçersizliği → `make_plan`) bu turda yalnız belgelendi;
  düzeltilmiş girdiyle yeniden koşulmadı (tur kapsamı yalnız G11R-02 vakalarıydı).
- `eval/guided_10_report.json` resmî koşuyu raporlar (1/9); düzeltilmiş girdi turu ayrı run olarak
  `rerun-round2/` altındadır — resmî teslimlere karıştırılmadı.
- Oturum token'ları kayıtlarda/`recovered/` altında açık metindir; depo pratiğiyle (resume
  reçeteleri) tutarlı, ama inceleme öncesi bilinmesi gereken bir durum.





