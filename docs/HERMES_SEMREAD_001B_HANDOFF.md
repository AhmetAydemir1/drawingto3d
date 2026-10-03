# SEMREAD-001B devir notu — dar semantic aday sözleşmesi ve D/V/VE pilotu

**Durum: UYGULAMA BÜYÜK ÖLÇÜDE BİTTİ, ÖLÇÜM BİTMEDİ.** Bu not, context penceresi kapanmadan önce
yazıldı; aşağıdaki "KANITLANMIŞ" bölümü gerçek tool çıktısına dayanır, "YAPILMADI" bölümü ise
yapılmamış olandır. Hiçbir gerçek VLM çağrısı yapılmadı: **bütçe 0/30** (10 development, 20 final).

Kaynak: `docs/HERMES_SEMREAD_001B_GOAL.md` (goal metni) — bu not onun yerine geçmez.

---

## 1. KANITLANMIŞ (bu pencerede çalıştırıldı)

| Ne | Kanıt | Sonuç |
| --- | --- | --- |
| 001A geri dönülebilir snapshot | `out/lab/semread-001a/snapshot/manifest.json` + `eval/semread_001b_snapshot.py` | 001A ağacı hash manifestiyle donduruldu; 001B `src/drawingto3d/*.py` eklediği için 001A kimliği kaymasın diye önce bu yapıldı |
| 001A bütçe düzeltmesi | `out/lab/semread-001a/budget-correction.json` (şema `semread-001a-budget-correction/1`) | yetkili tavan **16**, kullanılan **16**, kalan **0**; bu goal'un 30'u ayrı sayaç |
| Dar aday sözleşmesi | `src/drawingto3d/semantic_candidates.py` | ayrı sürümlü şema; `DECISION_FIELDS` alan **adı** düzeyinde yasak (`supported`, `confirmed`, …); "Reply with JSON only"; `CandidateParseError` (tamir yolu yok) |
| D kolu adapterı | `src/drawingto3d/semantic_deterministic.py` | deterministic okuyucuyu adaya çevirir; **VLM çağırmaz** (llama import edilmez, testle bağlı) |
| V/VE okuma yolu | `src/drawingto3d/semantic_candidate_reader.py` | V: yalnız ham sayfa; VE: **aynı byte** ham sayfa + overlay + nötr gözlem tablosu (`observation_table`) |
| Eşleştirme + metrikler | `src/drawingto3d/semantic_evaluation.py` | bölge temelli 1:1 eşleştirme (beklenen değere bakmaz), TP/FP/FN, alan bazlı doğruluk, omission, binding, R/Ø, birim/değer, overclaim, recovery/regression, sıfır payda → `null` |
| Corpus (seçim) | `out/lab/semread-001b/corpus/manifest.json` | **10 sayfa**, **10 bağımsız parça grubu**, 4 dev + 6 frozen, grup bölünmesi yok (`split_violations: []`); sayfa PNG'leri `corpus/pages/` |
| Pilot sürücüsü + bütçe | `eval/semread_001b_pilot.py` | `--corpus/--d/--live/--evaluate/--budget/--dry-run/--worker`; rezervasyon **çağrıdan önce**, `flock`'lu kalıcı sayaç; dry-run 0 çağrı (doğrulandı) |
| Referans üretici | `eval/semread_001b_reference.py` | kısa notasyon → normalize bölgeli gold + `check_reference` denetimi |
| Testler | `pytest tests/test_semread_001b.py tests/test_semantic_candidates.py tests/test_semantic_reader_probe.py -q` | **107 passed** (25 + 26 + 56); D adapteri VLM'siz, eşleştirme/değer-birim/overclaim/recovery vakaları negatif testlerle bağlı |
| D kolu (ilk gerçek pafta) | `out/lab/semread-001b/attempts/dev-plate-pocket-D/result.json` | `product_verdict: pass`, **7 aday**, kapsam `exact: true`, **0 inference**, 2.985 sn; örnek: `d-4` = "6,80 THRU ALL" → form `diameter`, 6.8 mm, `count.printed=4`, `thru` |
| Değerlendirme + kabul yolu | `.venv/bin/python eval/semread_001b_pilot.py --evaluate` | 0.6 sn, OCR'sız; `out/lab/semread-001b/{evaluation.json,acceptance.json,final/report.md}` üretildi. Referans yokken dürüst sonuç: `3/7 kapandı; açık: [B02, B04, B05, B06]`, bütçe **0/30** |

Doğrulanan kritik davranışlar (hepsi test):

* Eşleştirme **beklenen değere bakmaz**: doğru değer yanlış hedefte ise eşleşme kurulmaz → binding
  hatası olarak raporlanır.
* Kopya aday recall'u artırmaz (1:1); belirsiz çift `ambiguous` olarak yazılır.
* `unknown` **çekimserliktir**, doğru sayılmaz; underdetermined claim'e kesin değer verilirse
  `overclaim`.
* Birim hatası ile değer hatası ayrı: `8 in` vs `8 mm` → `unit_error`; `0.315 in` vs `8 mm` →
  dönüşümle doğru (`unit_converted` notu).
* D kolunda `physical.kind` **her zaman** `unknown` (çizilmiş daire, fiziksel delik iddiası değildir).

## 2. YAPILMADI (bu pencerede bitmeyen)

1. **Referans (gold) yazılmadı.** `corpus/gold/` boş; `corpus-probe.json` (10 sayfanın metin katmanı
   ölçümü) hâlâ koşuyordu (rasterlarda Hough+tesseract yavaş). Gold olmadan `--evaluate` hiçbir
   kol için doğruluk üretmez; **sonuç uydurulmayacak.**
2. **Gerçek pilot koşusu yapılmadı** — bilinçli: gold yokken 20 final çağrıyı harcamak bütçeyi
   boşa yakar ve ölçüm geçersiz olur. Bütçe durumu: **0/30**.
3. Kabul satırları `B01–B07` yazıldı; gerçek durum `out/lab/semread-001b/acceptance.json`:
   **`3/7 kapandı; açık: [B02, B04, B05, B06]`** (referans yok → D değerlendirmesi de yok).
4. `out/lab/semread-001b/final/report.md` üretildi **ama** ölçüm satırları boş: referans olmadan
   doğruluk sayısı yazılmaz (uydurulmaz).
5. D kolunun dev sayfalarındaki koşusu **tamamlandı** (`/tmp/semread-001b-d-dev3.log`, `EXIT=0`):
   4/4 sayfa `pass` — drawing-2 17 aday / 4.65 sn, flange-book 12 aday / 921.66 sn, flange-elbow
   17 aday / 206.07 sn, plate 7 aday / 2.99 sn. **Süreler adapter süresidir**: `observe()` (OCR)
   dışarıda; uçtan uca süre olarak kullanılmaz. Dev corpus'ta D'nin 10 hücresinin 4'ü hazır,
   6 frozen hücresi `not_run`.
6. `out/lab/semread-001b/corpus-probe.json` **tamamlandı** (§4): PDF sayfalarının metin katmanı
   temiz, raster sayfaların OCR'ı gürültülü → raster claim'leri `vision` ile yazılmalı.

## 2b. İNCELEME PLANININ AŞAMA A DURUMU (`docs/HERMES_SEMREAD_001B_COMPLETION_PLAN.md`)

Düzeltilenler (hepsi 0 inference, testle bağlı — `tests/test_semread_001b_gates.py`, **14 passed**):

| Bulgu | Durum | Kanıt |
| --- | --- | --- |
| P0 bütçe fazı: `phase=split` ("frozen") sayacı atlıyordu | **düzeltildi** | `split` ≠ `phase`; `phase ∈ {dev,final}` doğrulanır; dev/final/**toplam 30** tek `flock` içinde; geçersiz faz/kol/bölüm bütçe harcamaz; `send_state` (`reserved`/`sending`/`sent`/`transport_*`/`not_sent_model_mismatch`) kaydedilir. Eski davranış kanıtlandı: aynı probe 31 "frozen" rezervasyonunu kabul ediyordu, `final_used=0` kalıyordu |
| P0 VE overlay kimliği geçersizdi (`image-overlay`) | **düzeltildi** | ham sayfa `image-1`, overlay `image-2`; test kimlik–byte sırasını, ham byte eşitliğini, overlay farkını, gözlem tablosunun nötr alanlarını doğrular |
| P0 gerçek istek yolu test edilmemişti | **kısmen** | worker→hazırlama→`read_page`→taşıma sınırı taklit edilerek sınandı: görüntü sırası/etiketleri, `per_image_message_labeled`, `Image ID: `, `response_format`, `num_predict`; sızıntı ve parse hatası kaydı; taşıma hatası türü; **yerel hazırlama hatası gönderim sayılmaz** (`local-error.json`, `send_attempted: false`, bütçe 0) |
| P1 kabul/matris | **kısmen** | `--matrix`: 30 hücre (10 D + 20 VLM), `--phase` zorunlu, `--dry-run --phase final` = 20 planlı çağrı ve kalan bütçe 20; fazsız `--live` reddedilir; `--no-reuse` ile politika dışı tanı |

**Hâlâ açık (sıradaki pencere):** P0-3 (üst düzey metrikler bölgesel eşleşmeyi ölçüyor → adlandır ve
predicate bazında TP/FP/FN hesapla), P0-4 (eksik cevapta alan paydası 0 kalıyor; birimi boş değer
gold'dan doldurulmamalı), P1-5 (recovery/regression tüm predicate'lerde, `not_applicable` başarı
sayılmadan), P1-6 (`build()` gerçekten `check_reference()` çağırsın, geçersiz gold yayımlanmasın),
P1-7 (`evaluate` saklanan gözlemlerden okusun; attempt'ler değişmez; kanıt dosyaları birlikte
doğrulansın), P1-8 (B05/B07 gerçek matris ve boş olmayan bütçe günlüğü üzerinden). Ardından
planın B (10/10 gold), C (D taban çizgisi), D (4 development V/VE çağrısı), E (final matris) aşamaları.

## 3. SIRADAKİ TEK ADIM (sırayla)

```bash
cd ~/Desktop/drawingto3d
# 1) inceleme planının A aşaması: kalan P0-3/P0-4, P1-5/P1-6/P1-7/P1-8 (hepsi 0 inference)
.venv/bin/python -m pytest tests/test_semread_001b_gates.py tests/test_semread_001b.py -q
# 2) her sayfa için gold kaynağı (PDF: metin katmanı, raster: vision) -> gold + denetim
$EDITOR out/lab/semread-001b/corpus/gold-src/<page_id>.json
.venv/bin/python eval/semread_001b_reference.py --page <page_id>   # check_reference zorunlu
# 3) D taban çizgisi: 10 hücre tamamlanır (0 çağrı)
.venv/bin/python eval/semread_001b_pilot.py --d
.venv/bin/python eval/semread_001b_pilot.py --matrix
.venv/bin/python eval/semread_001b_pilot.py --evaluate
# 4) development V/VE denemesi (2 sayfa = 4 çağrı), sonra final matris (20 VLM hücresi)
.venv/bin/python eval/semread_001b_pilot.py --dry-run --phase dev  --split dev --arms V,VE
.venv/bin/python eval/semread_001b_pilot.py --live    --phase dev  --split dev --arms V,VE
.venv/bin/python eval/semread_001b_pilot.py --dry-run --phase final
.venv/bin/python eval/semread_001b_pilot.py --live    --phase final
.venv/bin/python eval/semread_001b_pilot.py --evaluate
```

Not: `--phase` zorunludur (dev ≤10, final ≤20, toplam ≤30); `split` yalnız veri bölümüdür ve
verilmezse 10 sayfanın hepsi kapsanır. `--live` plan kalan bütçeden fazla çağrı isterse hiçbir çağrı
yapmadan reddeder.

Referans yazarken kural: **PDF sayfalarında** metin katmanı çizimin kendi içeriğidir
(`source_evidence: "pdf-text-layer"`). **Rasterlarda** OCR tek başına referans kaynağı değildir;
`vision` ile doğrulanmayan claim `review_flag` alır (`eval/semread_001b_reference.py` bunu zorlar).

## 4. CORPUS PROBE SONUCU (10 sayfanın metin katmanı ölçümü — OCR, inference yok)

`out/lab/semread-001b/corpus-probe.json` (koşu tamamlandı). Özet — bu tablo **referansın nasıl
yazılacağını** belirler:

| sayfa | sn | primitive | metin | okunabilirlik |
| --- | --- | --- | --- | --- |
| dev-plate-pocket (pdf) | ~3 | — | metin katmanı | temiz (`6,80 THRU ALL`, `80,00`) |
| frozen-exercise-12 (pdf) | 0.17 | 513 (42 circle) | 70 | temiz (`R25.00`, `270.00`, `220.00`) |
| frozen-enclosure (pdf) | — | — | metin katmanı | pdf metni |
| dev-flange-book (raster) | 257.16 | 615 | 29 | **OCR gürültülü** (tek okunur: `6x D 6.40 V 15.00` ≈ 6x Ø6.40 ↧15.00) |
| dev-flange-elbow (raster) | 39.16 | 306 | 27 | **OCR gürültülü** (`oe`, `a8 a 7 rH`) |
| frozen-views-exercise (jpg) | 29.61 | 278 | 18 | **OCR gürültülü** (`tp etyeadcan ago com`) |
| (yedek) 504715c4….jpg | 46.35 | 424 | 19 | OCR kullanılabilir (`R5`, `R60`, `R100`, `190`) |

Çıkarım (referans yazarken uygulanacak):

1. **PDF sayfalarında** referans çizimin kendi metninden yazılabilir (`source_evidence:
   "pdf-text-layer"`).
2. **Raster sayfalarda** OCR referans kaynağı **değildir**: o sayfaların claim'leri `vision` ile
   doğrulanmalıdır; `eval/semread_001b_reference.py` bu kuralı zorlar (`review_flag`).
3. Rasterlarda deterministic hat ölçek çözülemediği için (`no-scale`) büyük olasılıkla **çekimser**
   kalacak → D kolu o sayfalarda omission üretecek. Bu beklenen davranıştır ve V/VE ile
   karşılaştırmanın tam olarak ölçmek istediği şeydir; D'yi iyi göstermek için sayfa seçilmez.
4. Yedek sayfa `504715c44a0f1b2bbb386bb7c387a8db.jpg` (OCR'ı okunur) gerekirse frozen'a alınabilir;
   o zaman `frozen-views-exercise` çıkar (grup bütünlüğü korunur).

## 5. Kapsam ve dürüstlük sınırları

* Ölçülen: circle temsili/delik ayrımı, R vs Ø, basılı değer+birim, count, THRU/finite/unknown,
  yazılı derinlik, callout→target binding.
* Ölçülmeyen: CAD/STEP, fusion, verifier, kullanıcı emeği azalması (`not_evaluated`).
* Referans **ajan tarafından** hazırlanıyor (`annotator: agent`, `review_status: provisional`) →
  ürün doğruluğu sertifikası değildir.
* V/VE'nin D'den iyi çıkması completion şartı değildir; negatif sonuç olduğu gibi yazılır.
* Corpus küçük ve bilinen bir repo kaynağıdır; bağımsız holdout değildir.
* `image_attached`/`server_ok` görüntünün **kullanıldığını** kanıtlamaz.
* Ölçülen ilk paftada görülen D sınırı (kayıt için): Ø işareti **yazılmadan** verilen çaplar
  (`80,00`) `form: none` olarak okunur; PDF metin katmanında boşlukla bölünen sayılar (`1 00,00`)
  tek sayı olarak birleşir. Bunlar referansla karşılaştırıldığında **yanlış** sayılacaktır; D kolu
  olduğundan iyi gösterilmez.
