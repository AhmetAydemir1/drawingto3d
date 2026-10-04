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

## 6. PLAN.md (P0–P8) DURUMU

`PLAN.md` (kullanıcı eki) sırası: P0 artefakt/kimlik → P1 değerlendirici → P2 kabul kapıları →
P3 gold → P4 D taban çizgisi → P5 dondurma → P6 V/VE → P7 ölçüm → P8 karar.
**P6/P7 (gerçek çağrılar) başlatılmadı; bütçe 0/30.**

**P0 — tamamlandı (0 inference):**

| Madde | Durum | Kanıt |
| --- | --- | --- |
| P0 değişmez attempt artefaktları | **bitti** | `attempts/<vaka>/attempt-NNNN/`; `new_attempt_dir()` var olanı asla yeniden yazmaz; ilk sürümün düz klasörü tarihsel kayıt olarak okunur |
| P0 attempt kimlik kaydı | **bitti** | `manifest.json` (`semread-001b-attempt/2`): attempt_id, page_id, arm, **phase**, split, created_at, üretici+değerlendirme kimliği, kaynak+sayfa PNG hash'i, model/digest/runtime/meta veri, `settings`, `request_sha256` |
| P0 attempt geçmişi | **bitti** | `state.json → attempts[<vaka>]` artık **liste**; `record_attempt()` ekler, üzerine yazmaz (`fcntl` kilidi) |
| P0 yeniden kullanım/bayat doğrulaması | **bitti** | `reusable_attempt()`: verdict=pass + üretici kimliği + değerlendirme kimliği + digest + `settings` + kaynak hash'i + **sayfa PNG hash'i** + sızıntı kapısı + runtime uyumu; girdi byte'ı değişirse bayat |
| P0 gerçek runtime kimliği | **bitti** | `runtime_identity()` Ollama `/api/version` + `/api/tags` okur (inference değil); gerçek sürüm **0.32.1** (beklenenle aynı, ölçüldü). Uyuşmazlıkta çağrı **gönderilmez**: `blocking_kind: runtime_mismatch`, `send_state: not_sent_runtime_mismatch`, rezervasyon defterde kalır |
| P0 üretici/değerlendirici kimliği ayrımı | **bitti** | `producer_identity()` yalnız tahmini etkileyen dosyalar + `settings` + şema + model/digest/runtime + corpus byte'ları; `evaluation_identity()` gold + politika + **`semantic_evaluation.py`/`semread_001b_reference.py` byte'ları**. Test: evaluator dosyası değişince üretici kimliği sabit kalıyor, tersi de öyle |
| P0 `evaluate` seçilen attempt'i okur | **bitti** | `evaluate()` matrisi kurar ve **hücrenin seçtiği** attempt klasörünü okur; `cells_status` seçilemeyen hücreleri `not_run` olarak yazar; `evaluation.json` artık `matrix`, `cells_status`, `matrix_totals` taşır |

## 6b. PLAN-2 (P0R) DURUMU — HEAD `27bbe8d` incelemesi

P0 tam kapanmamıştı; P0R maddeleri uygulandı (hepsi 0 inference):

| P0R | Durum | Nasıl |
| --- | --- | --- |
| P0R-1 evaluator değişikliği ham tahmini bayatlatmasın | **bitti** | `reusable_attempt()` artık `evaluation_identity` **eşitliği aramıyor**; test: yalnız evaluator değişince tahmin yeniden kullanılabilir kalıyor, eski değerlendirme bayat işaretleniyor |
| P0R-2 pilot dosyası üretici kimliğinde olmasın | **bitti** | yeni `src/drawingto3d/semantic_run_contract.py`: model/digest/runtime/settings/görüntü sözleşmesi orada; `PRODUCER_IDENTITY_FILES` = kontrat + üretici kaynak dosyaları (pilot **yok**); pilot artık `EVALUATION_IDENTITY_FILES` içinde |
| P0R-3 gerçek HTTP istek hash'i | **bitti** | `http_request_sha256` (taşımanın serileştirdiği gövde) ve `request_manifest_sha256` (kayıt izi) ayrı alanlar olarak manifestte |
| P0R-4 kanonik model meta verisi | **bitti** | `find_model(installed_models(), MODEL).as_dict()` → name/digest/size_bytes/parameter_size/quantization/context_length/families/capabilities + runtime sürümü |
| P0R-5 her attempt geçmişe girsin | **bitti** | erken çıkışlar da kayıtlanıyor: `local_error`, `blocked_budget`, `blocked_model_mismatch`, `blocked_runtime_mismatch`; test her attempt klasörüne **tam bir** geçmiş kaydı düştüğünü doğruluyor |
| P0R-6 D için bayat denetimi | **bitti** | `reusable_d_attempt()`: üretici kimliği + kaynak hash'i + sayfa PNG + aday şeması; bayatsa matris hücresi `to_run` (`stale_detected: true`) — D yeniden koşar, inference harcanmaz |
| P0R-7 kimlik adları | **bitti** | `producer_identity` / `input_identity` / `model_identity` / `evaluation_identity` / `attempt_id` / `evaluation_run_id`; `code_identity` yalnız geriye dönük ad |
| P0R-8 kapanış kapısı | **bitti** | kapı testleri **26 geçti** (6'sı P0R); toplam SEMREAD-001B takımı **133 geçti** (26 kapı + 25 + 26 + 56). Matris: 30 hücre, 20 VLM `to_run`, 10 D `to_run`, **4 bayat D** (kontrat öncesi attempt'ler) — bütçe 0/30 |

Not: kontrat modülü eklendiği için **eski** (bu değişiklikten önceki) attempt'ler üretici kimliği bakımından bayat sayılır — D hücreleri yeniden koşacak (0 inference), V/VE hücreleri zaten hiç çağrı yapmadı.

## 6c. PLAN-3 (P0R-FINAL) DURUMU — maddeler tamamlandı, PLAN-5 §31 ile kapatıldı (§6e)

PLAN-3 sırası: P0R-FINAL → P1 → … → P8; final V/VE harcaması P0R–P5 kapanmadan yok.
Aşağıdaki tablo PLAN-3 turunda kalan işi, §6e ise PLAN-5 §31 (A–F) kapanışını ve çıkış kapısını yazar.

| # | Madde | Durum | Not |
| --- | --- | --- | --- |
| 1 | Donmuş ayar = gerçek istek (`top_p`/`seed`) | **bitti (alternatif yol)** | taşıma (`ChatSettings` → `_chat_request`) bu iki seçeneği `options`'a koymuyor; PLAN-3 §4'ün izin verdiği alternatifle **kontrattan çıkarıldı** (`CONTRACT_VERSION` → `/2`) |
| 2 | Desteklenmeyen donmuş ayar gönderimi durdurur | **bitti** | `write_live_attempt()` gönderimden önce kesiyor: `blocking_kind=unsupported_frozen_setting`, `send_attempted=false`, geçmişte `blocked_unsupported_setting`. **P0R-FINAL-B sonrası:** ret rezervasyon bile almaz, inference bütçesine dokunmaz (PLAN-5 §4) |
| 3 | Yaşam döngüsünün tamamı kayıtlanır (`finalize_attempt`) | **bitti** | ortak `finalize_attempt(...)`: `local-error.json` + `prediction-input.json` + `manifest.json` + **geçmiş kaydı** + `result.json` + `artifact-index.json`; kapalı durum kümesi (`local_error_source/observe/preparation`, `blocked_budget/model_discovery/model_mismatch/runtime_mismatch/unsupported_setting`, `sending`, `transport_error`, `parse_error`, `failed_gates`, `pass`); aynı `attempt_id` ikinci kez sonuçlandırılamaz (`AttemptFinalizedError`); `--lifecycle` + `attempt_lifecycle_report()` (orphan/çift kayıt denetimi) |
| 4 | `prediction_input_identity` (gerçek hazırlanan girdi) | **bitti** | `prediction_input_record()`: hazırlanmış görüntü byte'ları (sıra + sha256 + boyut), **gönderilen prompt'un hash'i**, VE gözlem tablosu hash'i, `preprocessing_identity` (hazırlama kodu + `image_max_side` + `raw_page_strategy`), `contract_version`; kayıt `prediction-input.json`'a, hash manifest'e yazılır; önbellek üretici kimliğine bağlı (`corpus/prepared-inputs/`); V/VE ham `image-1` eşitliği `v_ve_raw_page_invariant()` ile mekanik denetlenir |
| 5 | Okuyucu literalleri kontrattan | **bitti** | `IMAGES_LAYOUT` / `IMAGE_LABEL_PREFIX` kontratta; `read_page()` bunları kullanır, kopya literal yok |
| 6 | Kanonik model meta verisi tek yol | **bitti** | `runtime_identity()` elle `/api/tags` ayrıştırmıyor: tek yol `installed_models()` → `find_model()` → `as_dict()`; dönen alanlar `model`, `model_canonical`, `parser`, `endpoint`, `version`, `error` |
| 7 | Liste tabanlı `state.attempts` için kabul kodu | **bitti** | `all_attempt_records(state)` (eski dict / yeni liste / karışık / boş) + `acceptance_rows()` ondan besleniyor; `--evaluate` liste geçmişiyle çalıştı, `evaluation_run_id` + `evaluation_stale_cells` üretiyor |
| 8 | Odaklı 0-inference testler | **bitti** | yeni `tests/test_semread_001b_lifecycle.py` (15) + `tests/test_semread_001b_identity.py` (15); 3 dosyalık SEMREAD koşusu **64 geçti, 0 fail, 2,56 sn** |

Gerçek runtime kanıtı: `runtime_identity()` yerel Ollama'dan **0.32.1** okuyor, kanonik ayrıştırıcı `installed_models/find_model/as_dict`, digest beklenenle aynı — ölçüldü, varsayılmadı.

Karar kaydı: §4'ün "tercih edilen" yolu (top_p/seed'i taşıma katmanına ekleyip gövdeye koymak) yerine **alternatif** seçildi — taşıma katmanının istek gövdesini değiştirmek dondurulmuş 001A kanıtlarını da etkilerdi; alternatif sözleşmeyi gerçeğe uydurur ve hiçbir ayarı sessizce düşürmez.

**P1'de kalanlar (sıradaki iş):** predicate-geneli recovery/regression, belirsiz eşleşme politikası
(şimdiki davranış bir adayı puanlıyor), `localization_match_rate` / `semantic_field_accuracy` /
`overclaim_rate` / `abstention_rate` ayrımı, `exhaustiveness`'e göre `unscorable_extra_candidate` ↔
`false_positive` ayrımı, `EKSİK:`/`TODO` yer tutucularının reddi, referans bölge doğrulaması
(`0<=x0<x1<=1`, NaN/inf, sıfır alan), gözlem kimliği denetiminin fail-closed olması.

**P2:** B05/B06/B07'yi 30 hücreli matris + gerçek kanıt zincirine bağla (B07 şu an boş kayıtla da
kapanabiliyor). **P3:** 10/10 gold (PDF metin katmanı, raster vision). **P4:** D'nin 10 hücresi
(4'ü hazır). **P5:** dondurma manifesti.

### 6d. Test durumu (tek güncel blok — PLAN-5 §31)

```
.venv/bin/python -m pytest tests/test_semread_001b_gates.py tests/test_semread_001b_lifecycle.py \
    tests/test_semread_001b_identity.py -q
→ 66 geçti, 0 fail (3,27 sn)   # 34 kapı + 17 yaşam döngüsü + 15 kimlik
```
Eski 222 sn'lik koşunun yegâne yavaşı `test_a_local_preparation_error_is_not_reported_as_a_sent_call`
idi: hazırlama hatasını ölçen test gerçek `observe()` (OCR) çağırıyordu; artık `observe` taklit edilir.
Tam takım (`pytest -q`, 253+) ve `tests/test_semread_001b.py` + `test_semantic_candidates.py` +
`test_semantic_reader_probe.py` sonuçları bu satırın yanına yazılır.

### 6e. PLAN-5 §31 (A–F) — **UYGULANDI** (0 inference, bütçe 0/30)

Sıra: A yaşam döngüsü → B rezervasyon sırası → C/D girdi kimliği → E koşu sürümü → F testler.
Hiçbir VLM çağrısı yapılmadı; `--budget` **0/30** (dev 0/10, final 0/20) gösteriyor.

| § | İş | Kanıt |
| --- | --- | --- |
| A | `finalize_attempt()` tek kapanış yolu | `eval/semread_001b_pilot.py`; `write_d_attempt`/`write_live_attempt` ondan geçer; kaynak/gözlem/hazırlama/model keşfi/taşıma/parse hataları tam bir geçmiş kaydı üretir; kayıt `result.json`dan **önce** yazılır (orphan riski azalır); `AttemptFinalizedError` ikinci sonuçlandırmayı engeller; `--lifecycle` orphan/çift kaydı gösterir |
| B | Rezervasyon tüm deterministik preflight'tan **sonra** | sıra: kaynak → gözlem → paket+prompt → donmuş ayar → model keşfi+digest → runtime → girdi kimliği → `reserve_live_call` → gönderim. Gönderilmediği kanıtlanan retler (`local_error_*`, `blocked_model_discovery/model_mismatch/runtime_mismatch/unsupported_setting`) **0 bütçe**; gönderim ve gönderimi belirsiz deneme **1 slot**; `budget_report()` attempt defterini ayrı raporlar (`legacy_non_dispatch_records` dahil) |
| C | `prediction_input_identity` gerçek hazırlanmış girdiden | `prediction_input_record()`/`prediction_input_identity()`/`preprocessing_identity()`; kayıt `prediction_input.json` + manifest; önbellek `corpus/prepared-inputs/<page>-<arm>.json` (üretici kimliğine bağlı); `v_ve_raw_page_invariant()` V/VE ham `image-1` eşitliğini mekanik denetler |
| D | `reusable_attempt()` girdi kimliğine bağlı | kayıtlı `prediction_input_identity` != güncel kimlik → yeniden kullanım yok; `page_png_sha256` yalnız meta veri; gönderilmemiş attempt (`send_attempted is not True`) tahmin sayılmaz; girdi kanıtlanamıyorsa **fail-closed** |
| E | Değerlendirme kanıtı sürümlenir | `out/lab/semread-001b/evaluations/<evaluation_run_id>/{evaluation.json,acceptance.json,report.md,selected-attempts.json}`; `final/pointer.json` yalnız güncel koşuya işaret eder; çakışan kimlik yeni klasör alır, eski koşu **değişmez** (test hash ile doğruluyor) |
| F | Odaklı 0-inference testler | `tests/test_semread_001b_lifecycle.py` (A/B) + `tests/test_semread_001b_identity.py` (C/D/E) |

**P0R-FINAL çıkış kapısı (PLAN-5 §8) — madde madde:**

1. her attempt klasörü tam bir geçmiş kaydı → `attempt_lifecycle_report()` + testler; 2. her yerel istisna
yolu sonuçlandırılıyor → 5 hata sınıfı testli; 3. defterler ayrı → `budget_report()`; 4. bilinen
gönderim-öncesi retler 0 bütçe → parametrik test; 5. rezervasyon gönderimden hemen önce → kod sırası
+ test; 6. kimlik gerçek hazırlanmış girdiden → test; 7. prompt hash'i katılıyor → test; 8. gerçek
görüntü byte/sıra katılıyor → test; 9. VE gözlem tablosu hash'i katılıyor → test; 10. V/VE ham sayfa
eşitliği → `v_ve_raw_page_invariant()` + test; 11. `reusable_attempt()` gerçek kimliği kullanıyor →
test; 12. yalnız evaluator değişikliği ham tahmini koruyor → test; 13. değerlendirme kanıtı
sürümleniyor → test; 14. bu iş için V/VE inference harcanmadı → `--budget` 0/30.

**Bu turda bulunan üç gerçek kusur (düzeltildi):**

1. **Sıra hatası ortaya çıkardı:** eski kodda desteklenmeyen-donmuş-ayar denetimi runtime
   doğrulamasından **sonra** duruyordu. Denetim öne alınınca `image_label_prefix`'in `ChatSettings`
   alanı olmadığı görüldü: ayar `SETTINGS`te var, taşımaya ayrı kwarg olarak gidiyor. Eski sırayla
   **gerçek bir gönderim** `unsupported_frozen_setting` ile dururdu; artık `raw_page_strategy` gibi
   taşıma-kwarg'ı sayılıyor ve gönderim yolu açık.
2. **D kolu manifestte çöküyordu:** ortak `finalize_attempt` yolu `_attempt_manifest()`i D için de
   çağırıyor; manifest `arm_evidence_mode("D")` diyordu ve sözleşme D'yi tanımadığı için
   `ValueError: bilinmeyen kol: D` fırlıyordu — yani `write_d_attempt()` **hiçbir** durumda
   tamamlanamıyordu (D'nin 10 hücresi bu hatayla ölürdü). §3'ün istediği D testi bunu yakaladı;
   düzeltme: `ARM_VARIANTS`/`EVIDENCE_MODES` üzerinden `.get` + D için açık `none` /
   `none_no_model_input` adları.
3. **Gerçek `state.json`'da test artığı:** `out/lab/semread-001b/state.json` içinde eski bir test
   koşusundan kalmış, `send_state: not_sent_runtime_mismatch` taşıyan 1 kayıt var (yolu `/var/folders/…`).
   Kanıt silinmedi; yeni anlamla bu kayıt **inference sayılmıyor** (`legacy_non_dispatch_records: 1`) ve
   `--budget` yeniden **0/30**. Ayrıca `attempt_lifecycle_report()` artık `rows_without_directory`
   alanını da yazar (bu kayıt gibi kanıtı silinmiş satırlar) — B07 böyle bir satırı kanıt zincirine
   alamaz (§20). Güncel testler gerçek köke yazmıyor (koşu öncesi/sonrası `state.json` hash'i aynı:
   `38337c83…`).

**Karar kaydı:** `CONTRACT_VERSION` `/3`'e yükseltildi — girdi kimliği sözleşmesi değişti (PLAN-5 §23
"prediction input contract" dondurulacak maddeler arasında). Bu, eski 4 D attempt'ini bayatlatır:
matris `stale_detected: true` ile `to_run` gösterir; D yeniden koşar, **inference harcamaz**.

**P1'de kalanlar:** yok — §9–§17 uygulandı (§6f).

**P2:** B05/B06/B07'yi 30 hücreli matris + gerçek kanıt zincirine bağla (B07 şu an boş kayıtla da
kapanabiliyor). **P3:** 10/10 gold (PDF metin katmanı, raster vision). **P4:** D'nin 10 hücresi
(4'ü hazır). **P5:** dondurma manifesti.

### 6f. PLAN-5 P1 (§9–§17) — **UYGULANDI** (§17 kod değişikliği gerektirmedi)

Politika **`semread-001b-match/1` → `/2`**: final tahminler görülmeden sabitlendi. Politika
değişikliği **değerlendirici kimliğine** girer (`semantic_evaluation.py`), üretici kimliğine
girmez: eski değerlendirme koşulu (`59ff99ee…`) dokunulmadan duruyor, yeni koşu (`290aab30…`)
ayrı klasöre yazıldı; ham tahminler yeniden üretilebilir kalır.

| § | İş | Kanıt |
| --- | --- | --- |
| 9 | Karşılaştırma **yüklem bazında** | `compare_arms()["vs_d"][arm]["predicate_rows"]`: her alan için `scorable_target_count`, `recovered_count`, `regressed_wrong_count`, `regressed_abstention_count`, `net_correct_gain` + örnekler; toplamlar satırların toplamı; "recovery > regression" karar kuralı kaldırıldı (not olarak yazılı) |
| 10 | Belirsiz eşleşme **dışlanır** | `close_scores` (margin içinde ikinci aday) ve `candidate_contested` (aday iki kalemin de en iyi adayı) → kalem `pairs`e girmez, `not_scored` olur, `ambiguous_claims`/`ambiguous_claim_count` ile sayılır; seçim aday sırasına bağlı değil |
| 11 | Yerelleştirme ↔ semantik ayrımı | `localization_match_rate`, `semantic_field_accuracy`, `target_binding_accuracy`, `candidate_overclaim_rate`, `candidate_abstention_rate`, `candidate_wrong_rate`; `candidate_precision`/`claim_recall` uyum için duruyor + `metric_note` |
| 12 | Kapsam-duyarlı fazla adaylar | `exhaustive_scope()`: `full_page`/`regions`/`predicates`; beyan yok ya da yer tutucu → **hiçbir** aday cezalanmaz; kapsam içi `false_positive`, kapsam dışı `unscorable_extra_candidate`; `evaluate_page()["extras"]` |
| 13 | Yer tutucu gold reddi | `placeholder_text()` (`EKSİK`/`TODO`/`TBD`/`PLACEHOLDER`, önek tabanlı) `scope`/`exhaustiveness`/`evidence`/`source_evidence` alanlarında reddeder; B02 yer tutucuyla kapanamaz |
| 14 | Bölge doğrulaması (hedef **ve** callout) | `region_problem()`: 4 sonlu sayı, `0<=x0<x1<=1`, `0<=y0<y1<=1`; sıfır alan, ters, aralık dışı, NaN/inf, eksik alan ve yanlış tip reddedilir; `exhaustiveness.regions` de denetlenir |
| 15 | Gözlem kimliği fail-closed | `check_reference(..., extraction_ok=False)` ya da boş gözlem listesi + gold `observation_id` → referans **geçersiz** (sessizce geçmez) |
| 16 | Raster gold görsel onay ister | raster sayfada `vision_checked=true` ve claim başına `source_evidence` içinde `vision` zorunlu; PDF sayfada bu şart yok |
| 17 | Anlamsal ayrıştırma korundu | Kod değişikliği gerekmedi: `score_pair()` `representation`/`physical`/`form` için ayrı kararlar üretir, `_categorical_verdict` fiziksel `overclaim`i ayrı sayar, D adapteri fiziksel yorumu `unknown` bırakır (mevcut test) |

Doğrulama: `tests/test_semread_001b.py` (yüklem/belirsizlik/metrik/kapsam) +
`tests/test_semread_001b_reference.py` (22 test: §13–§16) — odaklı tam koşu **124 geçti, 0 fail**.
`--evaluate` gerçek lab kökünde çalıştırıldı: yeni koşu klasörü + `final/pointer.json`, eski koşu
dokunulmadan; inference bütçesi harcanmadı (0/30).

Karar kaydı: belirsiz kalem **tamamen dışlanır** (puanlamak yerine sayılır), çünkü aday sırasına
bağlı alan puanı üretmek §10'un yasakladığı keyfî seçimdir; kopya aday bulunan yerde kalem artık
`ambiguous_claim_count`ta görünür, sessizce "seçilmiş" sayılmaz. Bunun bedeli: iki özdeş adayın
olduğu yerde kalem artık doğruluk paydasına girmiyor — bu, `matches_by_order` yerine
`ambiguous`u raporlamanın kabul edilen maliyetidir.

**P2'de sıradaki iş:** §18 B05'i gerçek 30 hücreli matrise bağla (her hücre
`valid_result`/`valid_reuse`/`failed_attempt`/`blocked`; `not_run`/`to_run` kalırsa B05 açık),
§19 B06'nın rapor içeriğini şart koşması (yüklem metrikleri, D/V/VE karşılaştırması, belirsizlik ve
kapsam-dışı sayaçları, taşıma/parse hataları, referans niteliği, gerçek hata örnekleri), §20 B07
kanıt zinciri (attempt geçmişi → artifact hash → üretici/girdi/model/runtime kimliği → HTTP istek
hash'i → bütçe kaydı → matris seçimi → değerlendirme kimliği). — **bu iş bitti, bkz. §6g.**

### 6g. PLAN-5 P2 (§18–§20) — **UYGULANDI**

| § | İş | Kanıt |
| --- | --- | --- |
| 18 | B05 gerçek matrise bağlı | `matrix_dispositions()` her hücreye nihai durum verir: `valid_result` (seçili attempt'in ürün kararı `pass`), `valid_reuse`, `failed_attempt` (koştu, karar geçmedi / `result.json` yok / taşıma-parse-yerel hata), `blocked` (kapı/bütçe). `to_run`/`not_run` **nihai değildir** → `complete=false` → B05 açık. Başarısız/bloklu hücre sayıdan düşmez, gerekçesiyle yazılır. `--matrix` artık sayaç + açık hücre listesi yazar |
| 19 | B06 rapor içeriğini şart koşar | `REPORT_MARKERS` + `report_evidence()`: yüklem metrikleri, D/V/VE karşılaştırması, geliştirme-frozen ayrımı, matris hücreleri, maliyet/hatalar, gerçek hata örnekleri, referans niteliği, belirsizlik ve kapsam-dışı fazla sayaçları rapora **yazılmalı**; ayrıca gerçek ölçüm şart (`aggregates` ya da `vs_d` boşsa kapı açık). Sayaçlar `outcome_totals()` ile attempt defterinden türetilir (taşıma/parse/kapı/yerel hata + bütçe) |
| 20 | B07 gerçek kanıt zinciri | `evidence_chain_report()`: her seçili hücre için geçmiş kaydı (tek kayıt) → `artifact-index.json` hash'leri **yeniden hesaplanarak** doğrulanır → üretici kimliği → girdi sha256 → istek kaydı → bütçe kaydı (D için `not_applicable`) → seçim → değerlendirme kimliği. Kopuk halka B07'yi açar; **boş zincir kabul edilmez** (`vacuous`). Yeni `--evidence` komutu |

Ek düzeltme: state'e yazılan `blocked.open` listesi ile `conclusion` artık **aynı** kaynaktan gelir
(eskiden B05 state listesinden düşürülüyordu, ikisi çelişebiliyordu); tüm kapılar kapanınca bayat
blok kaydı silinir. Gerçek lab kökünde `--evaluate`: açık kapılar B02, B04, B05, B06, B07 —
B05 30 hücrenin tamamı koşulmadığı için, B06 ölçüm olmadığı için, B07 seçili attempt olmadığı için.

Doğrulama: `tests/test_semread_001b_acceptance.py` (15 test: nihai durumlar, hücre sayaçları, rapor
içeriği kapısı, kategori/hash/kimlik kıran zincir testleri, boş zincir reddi) + mevcut semread
suite → `pytest -k "semread or semantic"` **320 geçti, 0 fail**. Inference bütçesi 0/30.

**P3'te sıradaki iş (gold):** 10 sayfa için referans yazımı — PDF'lerde metin katmanı + görsel
okuma, rasterlarda OCR **üzerine görsel doğrulama** (§16 zorunlu); `exhaustiveness` yapılı yazılmalı
(`{"scope": "full_page"}` / `regions` / `predicates`), kapsam ve kanıt alanlarına yer tutucu
yazılmamalı (yer tutucu B02'yi açık bırakır). **P4:** D kolunun 10 hücresi (dev 4 hücre koşuluyor,
sıfır inference). **P5:** dondurma manifesti + 20 frozen V/VE çağrısı (gerçek inference; başlamadan
önce kullanıcı onayı).

#### P3 ilerlemesi (bu pencerede başladı)

`dev-plate-pocket` gold'u **yazıldı ve doğrulamadan geçti** (`--evaluate`: `reference_status`
`ok=true`, problem yok). Yöntem ve kararlar (kalan 9 sayfa için aynen kullanılacak):

1. **Kısa biçim → builder → kapı.** `out/lab/semread-001b/corpus/gold-src/<page_id>.json` elle
   yazılır (bölgeler **pafta pikselinde**), sonra
   `.venv/bin/python eval/semread_001b_reference.py --page <page_id>` normalize edip
   `corpus/gold/<page_id>.json` üretir; kapı `check_reference()`tir (yer tutucu/bölge/gözlem
   kimliği/raster-vision). Bölgeler elle hesaplanmaz: küçük bir script gözlem tablosundan
   (`observation_table(observe(...))`) hedef bölgeyi ve çağrı metin kutusunu px'e çevirir
   (`/tmp/make_gold_src_plate.py` bu işin örneğidir — kalıcı bir kopyası bir sonraki adımda
   `eval/` altına alınmalı).
2. **Hedef = çağrının işaret ettiği özellik**, gözlem kimliğiyle izlenebilir (`observation_id`),
   ör. köşe deliği `g12`, cep dairesi `g8`. `Ø50,00` hedefinin ölçüsü 393,7 px = 50 mm @200 dpi
   çıktı: gözlem geometrisi ile çap birebir tutuyor (çap okuması bağımsız olarak doğrulandı).
3. **Şema sınırı:** `M8 - 6H THRU ALL` gibi **diş** çağrıları ifade edilemiyor (form kapalı kümesi
   `R | diameter | none | unknown`). Aynı dört delik tek claim olarak yazıldı (matkap Ø6,80), diş
   bilgisi `notes` alanında; dişi ikinci aday olarak üreten VLM'in adayı yanlış pozitif değil, alan
   kararıdır (size/form) — bu ayrım devir notunda yazılı.
4. **Derinlik pafta genelinden bağlanır:** cep derinliği (8,00) çağrının kendisinde değil SECTION
   B-B'de yazıyor; claim'e `depth=8.0, depth_state="stated"` olarak yazıldı ve `evidence` bunu
   açıklıyor. Çağrının yazmadığı sayı (cebin adedi) `count_printed=null` bırakılır: `count_printed`
   **basılı** sayıdır, "aslında bir tane" yorumu değil.
5. **Kapsam beyanı:** bu sayfa için `{"scope": "predicates", "predicates": [<yedi yüklem>]}` —
   "bu yüklemler için eksiksizim" demek; kapsam bölgesi gold claim'lerinin kendisidir (bkz. §6f/§12
   düzeltmesi). Doğrusal ölçüler (1 00,00 / 80,00 / 60,00 / 15,00) kapsam dışı ve `scope` alanında
   yazılı.

#### P3 sıradaki sayfalar — keşif durumu

* `dev-drawing-2` (pdf, iki görünüşlü, "Exercise 1"): çağrı metinleri **çıkarıldı** (gözlem
  tablosundan; hedef bölgeler henüz belirlenmedi): `R20` (t53), `Ø20` (t57), `Ø30` (t59), `Ø25`
  (t60), `Ø50` (t61), `Ø40` (t62); derinlik/doğrusal ölçüler: 80 (t49), 60 (t50), 35 (t51), 57
  (t52), 37 (t54), 20 (t55), 26 (t56), 6 (t58), 20/40 (t63/t64), 10 (t65). Pafta dikey
  (1653×2339). Yazım için: alt görünüşte sol taraftaki yuvarlak çıkıntı (Ø50 dış) + iç deliği
  (Ø30), sağ blok (Ø40/20) ve `R20` yayı; her leader'ın hangi özelliğe gittiği **yakınlaştırılarak**
  doğrulanmalı (gold yazılmadan önce).
* `dev-flange-book` (raster PNG), `dev-flange-elbow` (raster PNG): §16 gereği `vision_checked=true`
  + claim başına `vision` kanıtı; OCR metni tek başına gold değildir.
* 6 frozen sayfa (exercise-51/12/17/13 raster+pdf, enclosure pdf, views-exercise jpg): gold'u
  **frozen V/VE çağrılarından önce** yazılmalı (P5).

`eval/semread_001b_gold_regions.py` bu işin kalıcı aracıdır: spec JSON'daki
`target_observation`/`callout_texts` alanlarından piksel kutularını üretir, eksik `evidence`/
`source_evidence`/raster-vision şartlarını **yazmadan önce** uyarır (`--write` olmadan kuru çalışır).

#### D kolunun dev koşusu — **tamamlandı** (4/4 geçti) ve ilk gerçek (dev) ölçüm

`--d --split dev` (sıfır inference) dört dev sayfanın hepsini bitirdi: `dev-plate-pocket-D` 7 aday,
`dev-flange-book-D` 12, `dev-flange-elbow-D` 17, `dev-drawing-2-D` 17; dördü de `verdict=pass`.
Yaşam döngüsü `ok=true` (orphan/çift kayıt yok), matris: `deterministic:valid_reuse 4`,
`stale_d_cells 0`. Frozen D hücreleri (6) henüz koşulmadı → B05 açık.

İlk gerçek değerlendirme (yalnız `dev-plate-pocket` gold'u varken, D kolu — PLAN-5 §11 metrikleriyle):

| yüklem | doğru | yanlış | çekimser | doğruluk |
| --- | --- | --- | --- | --- |
| representation | 2 | 0 | 0 | 1,00 |
| physical | 0 | 0 | **2** | — (çekimser) |
| form | 2 | 0 | 0 | 1,00 |
| size | 2 | 0 | 0 | 1,00 |
| count_printed | 1 | 0 | 0 | 1,00 |
| termination | 1 | 0 | 1 | 0,50 |
| depth | 0 | 0 | **1** | — (çekimser) |
| target_binding | 2 | 0 | 0 | 1,00 |

Sayfa düzeyi: `matched 2/2`, `localization_match_rate 1.0`, `semantic_field_accuracy 0.6667`,
`candidate_overclaim_rate 0`, `candidate_abstention_rate 0.3333`, `false_positive 0`,
`unscorable_extra 5` (sayfa genelindeki çağrı olmayan metinler). **Okuma:** D kolu bağlama/çap/sayı
yüklemlerinde tam, yorum gerektiren `physical` ve `depth` yüklemlerinde **yanlış değil çekimser** —
planın ölçmek istediği "V/VE gerçekten ne katıyor" sorusunun dev cevabı bu sütunlarda görünecek.

**Açık kalan tek kanıt halkası — ÇÖZÜLDÜ:** ilk koşu sürerken `semantic_evaluation.py` düzenlendiği
için bir attempt eski değerlendirme kimliği taşıyordu (`evidence_chain` 4 hücreden 1'inde
`evaluation_identity` kopuk; B07 açıktı). Kod dondurulup temiz `--d --split dev` koşusu koşuldu
(dört sayfa yine `pass`): yeni koşuda `stale_d_cells 0`, `valid_reuse 4` ve **kanıt zinciri 4 hücre,
0 kopuk** → B07 kapandı. Ders: koşu sürerken `EVALUATION_IDENTITY_FILES` içindeki dosyalara
dokunulmaz; dokunulduysa koşuyu tekrarlamak gerekir.

**Kabul kapılarının ŞU ANKİ durumu** (en yeni koşu `ac91597b…`): **B01, B03, B04, B07 kapalı;
B02, B05, B06 açık.**

| kapı | durum | neden |
| --- | --- | --- |
| B02 | açık | gold 1/10 sayfa (`dev-plate-pocket`) — kalan 9 sayfa yazılmalı |
| B05 | açık | 30 hücre: `valid_reuse 4` (dev D), `to_run 20` (V/VE), `not_run 6` (frozen D) |
| B06 | açık | rapor içeriği tam, ama **puanlanmış kol yok**: V/VE henüz ölçülmedi |

**Testler artık lab'a yazmıyor** (`f861eff`): `evaluate()` testte `write_evaluation_artifacts`
stub'ıyla çağrılıyor; önce/sonra `evaluations/` sayısı 12 → 12. Daha önce koşan testler 4 klasör
bırakmış (`5c6e1839…`, `70f72cbf…`, `d73bb523…`, `fd9ffd67…`, `acceptance.json` yok) — kanıt
değildir, silinmedi (tarih bozulmasın), raporda "test kaydı" olarak anılmalı. `state.json` ve
`live-calls.guard` testlerde **hiç** değişmiyor (bütçe/attempt kaydı yazılmıyor).

**§19 sıkılaştırması (bu pencerede):** B06 artık "boş olmayan `comparison`" ile kapanmıyor; en az
bir **puanlanmış** kol (yüklem satırlarının scorable toplamı > 0) + rapor işaretleri şart
(`f691564`). Dev ölçümü geldiği için B06'nın rapor-içeriği koşulu sağlanıyor, ama V/VE kolları
henüz puanlanmadığından karşılaştırma tarafı boş: kapı, "karşılaştırma gerçekten ölçüldü" diyene
kadar açık kalır.

Tam suite notu: arka planda başlatılan `pytest -q` (değişikliklerin ortasında başlamıştı)
**1098 geçti, 0 fail** ile bitti; bu pencerenin kendi doğrulaması ise `pytest -k "semread or
semantic"` **321 geçti** + `test_semread_001b_acceptance.py` (17) + `test_semread_001b_reference.py`
(22) koşularıdır.

Not: `EVALUATION_IDENTITY_FILES` içinde `eval/semread_001b_pilot.py` var — pilot/dosya
düzenlemeleri değerlendirme kimliğini değiştirir ve seçili attempt'leri "bayat" yapar. Bu yüzden
sıra: **kod düzenlemeleri bitince D koşusu**, sonra doküman düzenlemeleri (dokümanlar kimliğe
girmez). D kolu şüphede yeniden koşar (inference maliyeti yok); V/VE'de bu bedel gerçek çağrıdır.

### 6h. P4 — D kolunun frozen hücreleri koşuldu: **D 10/10** (0 inference)

`--d --split frozen` (log: `/tmp/semread-001b-d-frozen.log`, `EXIT=0`) altı frozen sayfayı bitirdi;
altısı da `verdict=pass`. D kolunun 10 hücresinin tamamı artık geçerli (`reused_d_cells 10`).

| frozen sayfa | aday | adapter sn | verdict |
| --- | --- | --- | --- |
| frozen-exercise-51 (PNG) | 13 | 714.97 | pass |
| frozen-exercise-12 (pdf) | 30 | 9.38 | pass |
| frozen-exercise-17 (PNG) | 1 | 1006.51 | pass |
| frozen-exercise-13 (PNG) | 8 | 748.43 | pass |
| frozen-enclosure (pdf) | 14 | 5.13 | pass |
| frozen-views-exercise (jpg) | 7 | 103.61 | pass |

Süreler **adapter süresidir**; `observe()` (OCR/Hough) dışarıda — uçtan uca okuma süresi olarak
kullanılmaz (PLAN §22). `frozen-exercise-17`'nin 1 adayı çekimserliğin gerçek örneğidir, hata değil.

Koşu sonrası ölçülen durum (`--matrix`, `--lifecycle`, `--budget`):

```text
matris: 30 hücre → deterministic:valid_reuse 10, vlm:to_run 20, stale_d_cells 0, complete=false
yaşam döngüsü: 15 attempt klasörü / 15 geçmiş satırı (+1 eski test kaydı) — orphan yok, çift yok, ok=true
inference bütçesi: 0/30 (dev 0/10, final 0/20)
```

**PLAN-6 notu (bu pencere):** `PLAN-6.md` incelemesi `5e6512a` (origin/main) HEAD'ine bakar; yerel
HEAD bunun **12 commit önünde** (`3952b9c`) ve push edilmemiş. Bu yüzden planın "hâlâ açık" dediği
§4–§7 (A–D) ile §9–§20 (P1/P2) maddeleri yerelde **uygulanmıştır** (dd5c9fc, cb02a1e, 63961df,
bd01c22, f691564) ve §8'in 19 maddelik çıkış kapısı ölçülen raporlarla karşılanmıştır
(`--lifecycle ok=true`, `--budget 0/30`, `--matrix` nihai durumlar, §30 test listesi
`tests/test_semread_001b_{lifecycle,identity,acceptance,reference,gates}.py`). Kapılar değişmedi:
**B01, B03, B04, B07 kapalı; B02, B05, B06 açık** — üçü de gold + V/VE ölçümüne bağlı. Sıradaki
gerçek iş P3'ün kalan 9 sayfası, sonra P5 dondurma; P6 (gerçek V/VE) kullanıcı onayı ister.

### 6i. P3 ilerlemesi — `dev-drawing-2` gold'u yazıldı (**2/10**) + yeni araç

Yöntem (kalan sayfalar için de geçerli): gözlem tablosu dökümü → ölçülen primitif geometri ile
çağrı→özellik eşleşmesi → spec → `gold_regions` → `check_reference`.

* Yeni araç: `eval/semread_001b_gold_inspect.py` — sayfanın gözlem tablosunu
  `out/lab/semread-001b/corpus/observations/<page>.json` olarak döker ve çağrı benzeri satırları
  (`text`/`linear`/`diameter`/`radius`, değer + birim) listeler. **Ders:** çağrı metinleri tabloda
  `text` türüyle değil çoğunlukla `linear`/`diameter`/`radius` türüyle gelir; yalnız `text`e bakan
  filtre `dev-drawing-2`'de altı çağrının hiçbirini göstermiyordu.
* Spec: `out/lab/semread-001b/corpus/gold-specs/dev-drawing-2.json` (spec'ler artık kalıcı klasörde).
  `check_reference`: **ok=true, 6 claim, problem yok** (`reference_sha256 f3be4c26…`).
* Ölçek/ölçüm: 200 dpi + pafta ölçeği 1:2 → **3,9370 px/mm**. Ölçülen özellikler: Ø50 = 196,6 px
  (49,93), Ø30 = 117,7 px (29,89), Ø20 = 78,8 px (20,01), Ø25 = 98,4 px (25,00), Ø40 ve R20 =
  157,3 px (39,96). Bağlama **sayısal** doğrulandı: t61 leader'ı g65 kenarına oturuyor
  (613,3 → 612,8 px), Ø40 uzantıları 828→986 px, Ø25 858→956 px, Ø20 497→576 px.
* Karar (gold notlarında yazılı): hedef bölge **özelliğin çizili olduğu primitiftir**; Ø40/Ø25
  çağrıları üstten görünüşte yazılı olsa da hedef ön görünüşteki daire/yaydır (iki görünüş aynı
  özelliği gösterir). `termination`: Ø30 = `thru` (ön görünüşte bore çizgileri y 390→695 px,
  parçanın tam yüksekliği boyunca kesintisiz); Ø25/Ø20 = `unknown` — pafta hiçbir yerde THRU
  ya da derinlik yazmıyor (çekimserlik uydurmadan doğru okumadır).
* İlk gerçek D ölçümü (koşu `2cd5f310…`, 2/10 gold): `dev-drawing-2` için **matched 0/6**. D'nin 17
  adayının çoğu doğrusal ölçü (kapsam dışı → `unscorable_extra 14`) ve bağlamalar sistematik
  yanlış (ör. "R20" → g125, "37" → g133, "57" → g122; hedef kutuları çağrı boyunca uzadığı için
  IoU tutmuyor) → `ambiguous_pairs 6`. Toplam D: `matched 2/8`, `candidate_precision 0,0833`,
  `claim_recall 0,25`. Bu bir uydurma değil ölçüm: D çok görünüşlü paftada zayıf — V/VE'nin ne
  katacağı sorusunun dev cevabı bu.
* **B07 yeniden açıldı ve nedeni biliniyor:** gold dosyası `evaluation_identity`'ye girer; kimlik
  `2e1bab5c…` → `b64b11df…` oldu, 10 D attempt'i kayıtlı eski kimliği taşıyor (üretici kimliği ve
  ham adaylar **geçerli**, bayat olan yalnız değerlendirme halkası). Doğru sıra:
  **10/10 gold → tek `--d` koşusu (0 inference) → `--evaluate`**; o zaman zincir yine tam olur.
  Bu yüzden gold yazımı bitmeden D'yi yeniden koşmak zaman kaybıdır.
* Kalan 8 sayfa: `dev-flange-book`, `dev-flange-elbow` (raster → §16: `vision_checked` + claim
  başına `vision` kanıtı) + 6 frozen sayfa.

Kabul kapılarının bu koşudaki durumu (`2cd5f310…`): **B01, B03, B04 kapalı; B02, B05, B06, B07
açık** (B07 nedeni yukarıda; B02 gold 2/10; B05 20 VLM hücresi `to_run`; B06 karşılaştırma ölçülmedi).

### 6j. Raster dev sayfaları — keşif (P3'ün sıradaki adımı)

Gözlem dökümleri hazır: `out/lab/semread-001b/corpus/observations/{dev-flange-book,dev-flange-elbow}.json`.

| sayfa | kaynak | sayfa px | gözlem | OCR'ın okuduğu |
| --- | --- | --- | --- | --- |
| dev-flange-book | `examples/pdf with steps/8/Flange.PNG` | **3300×2550** (A3/300 dpi) | 644 (385 çizgi, 2 daire, 228 yay, 9 linear, 20 metin) | `6x D 6.40 V 15.00` (= 6x Ø6,40 ↧15,00), `20.00`, `60.00`, `90.00`, `2 11.00 V 3.90`, başlık bloğu (SECTION A-A, SCALE 1:2, Plain Carbon Steel) |
| dev-flange-elbow | `examples/flange-elbow-90.png` | **871×1024** (A4 200 dpi **değil**) | 333 (173 çizgi, 2 daire, 131 yay, 11 linear, 16 metin) | kısmen sayılar (`50/150/260/360`, `4x2-030`, `4x2-960`, `C10`), gerisi gürültü (`oe`, `a8 a 7 rH`, `CuSLATHA`) |

**Vision okuması (bu pencerede yapıldı, `dev-flange-elbow`):** sayfa 90° dirsek + iki kare flanş.
Çağrılar ve işaret ettikleri: `4-R20` kare plakanın köşe yarıçapı (iki görünüşte de), **`R10`** boru
yüzeyi ile flanş plakası yüzünün birleştiği iç köşedeki fileto (etiket iki görünüşte de zoom ile harf
harf okundu; bu notun önceki sürümündeki `R110` okuması **yanlıştı** — düzeltildi), `4x2-Ø60` +
`4x2-Ø30` flanş cıvata deliği deseni (Ø30 geçen delik + Ø60 havşa; iki flanş × 4 delik = 8),
`Ø210` + `Ø290` dirsek borusunun iç/dış çapı (kesit), `R260` boru ekseninin büküm yarıçapı,
`C10` pah. Doğrusal: 360/260/150/50/10.

**Yöntem kararları (sıradaki pencere için):**

* Raster gold §16 gereği `vision_checked=true` + claim başına `vision` kanıtı ister; `size`
  doğrulaması **görsel okumaya** dayanır ve `evidence` bunu yazmalı.
* Raster sayfalarda **px/mm baştan yazılı değil** (871×1024 ve 3300×2550, A4 200 dpi değil) ama
  **sayfanın kendi ölçü zincirinden türetilebilir**: elbow'da plaka kenarları (597,5→787 px = 360 mm)
  → 0,5264 px/mm, ve bu ölçek boru duvarlarıyla bağımsız doğrulandı (dış 153 px = 290,6 mm, iç
  111 px = 210,9 mm → çağrı değerleriyle birebir). Yani "ölçülen = basılı değer" doğrulaması rasterda
  da yapılabilir; yapılamadığı sayfada `size` görsel okumaya dayanır ve `evidence` bunu yazmalı.
* Hedef bölge için kaynak seçimi: ölçülebilir bir ölçü zinciri varsa **piksel koşu ölçümü** (tercih),
  yoksa Hough primitifi, o da güvenilmezse ızgaralı görsel okuma (§6j-1'de karar verildi).
* Aynı özellik birden çok görünüşte çizili (elbow'da her flanş iki görünüşte): **tek özellik = tek
  claim**; hedef, özelliğin en net çizildiği görünüşün primitifi, diğeri gold notunda anılır.
* `dev-flange-book`'un görsel okuması ve spec'i sıradaki adımdır (döküm hazır; OCR üç çağrıyı zaten
  okumuş durumda).
* **Açık karar (sıradaki pencere):** raster gold'da hedef bölgeyi Hough primitifi mi (gürültülü,
  131–228 yay) yoksa görselden ölçülen normalize kutu mu taşıyacak? `gold_regions` şu an yalnız
  gözlem kimliği kabul ediyor; ölçülen kutu gerekirse araç küçük bir ekleme ister (`target_box_norm`)
  ve gerekçesi gold notunda yazılmalı. Karar verilmeden raster spec yazılmamalı.

Sıra (değişmedi): raster dev gold'ları → 6 frozen gold → **tek `--d` koşusu** → `--evaluate`
(B07 yeniden kapanır, B02 10/10 olur); P5 dondurma; P6 (gerçek V/VE) kullanıcı onayı ister.

#### 6j-1. Raster hedef bölgesi — araç genişletildi (karar uygulandı)

* `eval/semread_001b_gold_regions.py` artık `target_box_norm: [x0,y0,x1,y1]` kabul ediyor
  (normalize, sıralı, 0..1; dördü de doğrulanır). Gözlem kimliği verilirse yalnız **iz** olarak
  saklanır, bölge ondan türetilmez; ölçülen kutuda araç uyarı basar ve **çıkış kodu 1** döner
  (gold gözle onaylanmadan yazılmasın). PDF yolu regresyonsuz: `dev-drawing-2` spec'i aynı altı
  satırı ve aynı px değerlerini veriyor.
* Gerekçe: rasterlarda Hough primitifleri güvenilmez — `dev-flange-elbow`'da 133 adayın çoğu
  düz çizgilerden türeyen dev/hayalet daireler (merkezleri sayfa dışında), köşe delikleri için
  tutarlı küme yok; `dev-flange-book`'da 228 yay. Bu yüzden hedef bölge **görselden ölçülen** kutu.
* **Izgara tekniği** (kalıcı yöntem): sayfa PNG'sinden 0,02'lik ızgaralı kırpma üretilir
  (3× büyütme, kenarlarda normalize etiketler), vision ile kutu okunur. `dev-flange-elbow` için
  üretildi: `elbow-A-section.png` (kesit, x 0–0,62 / y 0,50–1,00), `elbow-C-flange.png`
  (sağ-alt flanş, x 0,40–1,00 / y 0,44–1,00) — scratch 24 saatte silindiği için gerekirse
  tek komutla yeniden üretilir.
* `dev-flange-elbow` hedef adayları (kutuları okunacak): Ø210 + Ø290 → kesitteki boru ağzı
  (dikey flanş yüzü x≈0,49–0,51), R260 → kesitteki kesikli eksen yayı, 4-R20 → kare plakanın köşe
  yayı, `4x2-Ø60` + `4x2-Ø30` → cıvata deliği deseni, `R10` → flanş-boru birleşim filetosu.
  (C10 pahı şemada karşılığı olmadığı için kapsam dışı.)
* **Çözüldü (zoom, 0,01 ızgara):** iki çağrı birebir `4x2-Ø60` ve `4x2-Ø30` (kutuları ≈ x 0,76–0,85;
  üstteki y 0,485–0,507, alttaki y 0,530–0,552). Anlamı: kenar (kesit) görünüşünde her cıvata deliği
  iki çaplı çizilmiş — Ø30 geçen delik + Ø60 havşa/spot yüzey; metindeki `4x2` = **iki flanş × 4
  delik = 8**. Bu yüzden `count_printed` iki claim'de de **8** yazılacak ve gerekçe `evidence`ta
  duracak (VLM bu görünüşte 4 delik görecek; "printed" ile "found" ayrımı tam da burada ölçülüyor).
* **Çözüldü:** `R110` diye bir çağrı yok — iki görünüşteki eğik etiket de zoom ile harf harf **`R10`**
  okundu ve iki leader oku da boru yüzeyi ile flanş yüzünün iç köşesine oturuyor (sol üst görünüşte
  (0,468; 0,437), sağ alt görünüşte (0,868; 0,635)). İlk düşük çözünürlüklü okuma `R110` sanmıştı.

#### 6j-2. `dev-flange-elbow` gold'u yazıldı — gold 3/10

Spec: `out/lab/semread-001b/corpus/gold-specs/dev-flange-elbow.json` → `gold-src/` → `gold/dev-flange-elbow.json`
(7 claim, `check_reference` yapısıyla birebir: `target.region` normalize, `observation_id: null`,
`review_status: provisional`). Yedi dış çağrının hepsi claim oldu; doğrusal ölçüler (150/260/360/50/10)
ve `C10` pahı `scope`ta kapsam dışı yazılı.

**Hedef bölgeler nasıl ölçüldü** (Hough kullanılmadı; ölçüm zinciri `evidence` alanlarında):

| claim | hedef | ölçüm |
| --- | --- | --- |
| 01 Ø290 | kesit, flanş ağzı, dış duvar bandı | y 757→910 px = 153 px = 290,6 mm |
| 02 Ø210 | aynı ağızda iç boşluk | y 778→889 px = 111 px = 210,9 mm |
| 03 4x2-Ø30 | kenar (kesit) görünüşündeki geçen delik | görsel kutu (0,838–0,878 / 0,596–0,644); çap metinden (≈16 px ölçüm gürültüsünde) |
| 04 4x2-Ø60 | ön görünüşteki cıvata deliği dairesi | merkez (623,8; 766,3) px — plaka kenarından 50 mm içeride; delik dairesi ±16 px |
| 05 R260 | kesitteki kesikli eksen yayı bandı | x=174'te duvarlar 749–758/803–809 → eksen ≈780 px; x=278'de 871–874/894–897 → ≈884 px |
| 06 4-R20 | plakanın sağ üst köşe yayı | plaka kenarları x=787, y=740 px (px koşusuyla) |
| 07 R10 | birleşim filetosu köşesi | leader oku ≈ (0,468; 0,437) |

**Bilinen sınır (gold notunda da yazılı):** Ø210 ile Ø290 eş merkezli olduğu için hedef kutuları iç
içe; değerlendirmenin belirsizlik kuralı bu iki claim'i eşleştirmede belirsiz sayabilir. Bu davranış
iki kolda (D, V/VE) aynı işler, yani karşılaştırmayı bozmaz — ölçüm gücünü azaltır, onu da not düştük.

**Kalan:** `dev-flange-book` + 6 frozen sayfa → 10/10 → `--evaluate` (B02 kapanır) → P5 dondurma.

### 6k. PLAN-7 AUDIT-FIX-1/2 — kimlik koşuya ait, B07 gerçek model girdisini kanıtlar (B07 KAPANDI)

`docs/PLAN-7.md` (§3–§5, §25/§26) uygulandı. Plan metni artık repoda: `docs/PLAN-7.md`.

**AUDIT-FIX-1 — değerlendirme kimliği koşuya aittir.** `evidence_chain_report()`, attempt'in
yaratılış anındaki `evaluation_identity`siyle güncel kimliği karşılaştırmayı **bıraktı**. Yerine yeni
`evaluation_context()` koşu seviyesinde şunları denetler: `payload.evaluation_identity` güncel mi,
`payload.evaluation_run_id` seçili attempt'lerden yeniden hesaplanan koşu kimliğine eşit mi,
`selected-attempts.json` kimliği + koşu kimliği güncel mi, seçili küme hücrelerle **birebir** örtüşüyor
mu, aynı koşu klasörü kararlı mı. Hücre bazında yeni `selected_artifact` halkası,
`selected-attempts.json`da yazılı `attempt_id` + `manifest_sha256` + `result_sha256`'i diskteki
dosyalarla karşılaştırır (PLAN-7 §5). Attempt'in eski kimliği artık yalnız **bilgilendirici sapma**:
`attempt_evaluation_identity_drift` + hücre başına `attempt_evaluation_identity_at_creation`; yeniden
inference gerektirmez ve B07'yi açmaz. Eski `evaluation_stale_cells` alanı kaldırıldı; **B07 artık
`chain.complete + lifecycle.ok + evaluation_run.ok + bilinmeyen kollu bütçe kaydı yok`** üzerinden
kapanır.

**AUDIT-FIX-2 — V/VE kanıtı sayfa PNG'si değil gerçek hazırlanmış girdidir.** Gönderilmiş her V/VE
attempt'inde `prediction-input.json` okunur, `prediction_input_identity()` **yeniden hesaplanır** ve
manifest/result/geçmiş satırı/seçili-attempt alanlarıyla eşitliği aranır (`prediction_input_artifact`
+ `prediction_input_identity` halkaları); ek olarak `model_identity`, `runtime`, `request_record`
(istek manifesti **ve** istek hash'i) denetlenir. `page_png_sha256` yalnız meta veri olarak kalır.
Gönderilmemiş (yerel ret/blok) attempt'te model girdisi **yoktur**: `prediction_input_identity =
not_applicable` ve kanıt olarak `no_dispatch_evidence` (blocking/error kaydı) aranır — uydurma kanıt
yazılmaz. D kolunda model girdisi, model kimliği ve runtime `not_applicable`; D'nin girdi bütünlüğü
kaynak + sayfa PNG + hazırlama sözleşmesidir ve `input_identity` artık manifest alanıyla **eşitlik**
olarak denetlenir (10 D attempt'inde tutuyor). Manifeste `prediction_input_state` alanı eklendi
(`recorded` / `not_applicable_no_model_input`).

**Testler.** `tests/test_semread_001b_acceptance.py` **26 passed**: koşu kimliği sapması, koşu
kimliğinin seçili attempt'leri bağlaması, seçili kümenin hücreleri birebir kapsaması, bozuk
`prediction-input.json`, bozuk manifest kimliği, eksik prediction-input artefaktı, gönderilmemiş
attempt'in yerel ret kanıtı, D'de not_applicable, ve **"gold/evaluator değişti → geçerli D tahmini
hâlâ yeniden kullanılabilir"** (rerun yok). Eski `test_a_stale_evaluation_identity_breaks_the_chain`
testi silindi (yanlış sözleşmeyi bağlıyordu); yerine bilgilendirici sapma testi geldi.

**Ölçülen durum (bu pencere, gerçek lab, 0 inference):**

```text
--evidence   : complete=true, 10/10 hücre, kopuk halka 0
--evaluate   : run 6da99ce0b59388c3872465181d9d1c4e, değerlendirme kimliği 1d7f3908e3ea…
               kanıt zinciri 10/10, evaluation_run ok=true, sapma (yalnız bilgi) 10 hücre
kapılar      : B01, B03, B04, B07 KAPALI; B02 (gold 3/10), B05 (20 VLM hücresi to_run),
               B06 (karşılaştırma ölçülmedi) AÇIK  → PLAN-7 §15'in beklediği P6 öncesi durum
bütçe        : 0/30 (değişmedi); D tahminleri **yeniden koşulmadı** (10 attempt aynı kaldı,
               yalnız yeni değerlendirme koşusu açıldı)
```

**Sıradaki iş:** PLAN-7 §25'in 1–3. maddeleri (bu bölüm) bitti; P3 gold ilerliyor — `dev-drawing-2`
(6 claim), `dev-flange-elbow` (7 claim), `frozen-enclosure` (1 claim) ve `frozen-exercise-12`
(14 claim) yazıldı, **gold 5/10** (§6l). Sırada `dev-flange-book` (döküm hazır, OCR üç çağrıyı okumuş)
ve kalan 4 raster frozen sayfa → 10/10 → `--evaluate` (**B02 kapanır**; D hücreleri
PLAN-7'den sonra yalnız bilgilendirici sapma taşıdığı için yeniden koşu gerekmez, yalnız gerçekten
bayat hücre için tek `--d` koşusu) → P5 dondurma. P6 (gerçek V/VE, ücretli çağrı) kullanıcı onayı ister.

### 6l. P3 gold — iki frozen PDF sayfası yazıldı: `frozen-enclosure` (1 claim) + `frozen-exercise-12` (14 claim) → **gold 5/10**

İki sayfanın da kaynağı PDF (vektör/metin katmanı), bu yüzden çağrı metinleri çizimin kendi
metninden okundu; ölçüler gözlem tablosunun ilkel bbox'larıyla mm'ye çevrildi. Specler:
`corpus/gold-specs/frozen-enclosure.json`, `corpus/gold-specs/frozen-exercise-12.json`
(üretilen `corpus/gold-src/*` + `corpus/gold/*` lab'de, `out/` gitignored).

**`frozen-enclosure`** — A4 200 dpi (1654×2339 px), `SCALE 1:2` → 3,9370 px/mm (bağımsız
doğrulamalar: R8 yayı bbox 62,9 px = 16,0 mm; delik daireleri 4,78/3,99/2,97 mm ↔ çağrılar
4,80/4,00/3,00; yuva genişliği 10,03 mm ↔ 10,00).
* 1 claim: `R8,00` kenar filetosu → gözlem `g8` (yay), `callout_texts: [t2]`, leader ucu ızgaralı
  kırpmayla doğrulandı (ok ≈(0,386; 0,355)'te üst yüzey çizgisinin bittiği yere iniyor).
* `exhaustiveness: regions` (yalnız R8 çevresi) — sayfadaki tek Ø/R çağrısı bu; öteki ölçüler
  (120/60/46/25/18/10/10/4,80/4,00/3,00/1,50) Ø/R işareti taşımıyor (metin katmanında `linear`),
  bu yüzden kapsam dışı. Kapsam dışı aday `false_positive` değil `unscorable_extra_candidate`.
* `reference_sha256` **be3e56542f2b8970d876f0f014a9905d639cf4e9ec7765befe4404c67ba8f2ab**.
* D hücresi (bilgi): 14 aday, 1 claim **ambiguous** (d-2/d-3 aynı yere yakın puanlı), 3 FP
  (üçü de exhaustive bölge içinde), 11 kapsam dışı. Sayfa ölçüm gücü düşük ama karşılaştırma
  tüm kollar için aynı.

**`frozen-exercise-12`** — 200 dpi (2200×1700 px = 11×8,5 in), `SCALE 1:5` → **1,5748 px/mm**
(sekiz bağımsız doğrulama: 425,2 px = 269,94 ≈ Ø270; 249,0 = 158,09 ≈ Ø158; 220,4 = 139,94 ≈ Ø140;
189,0 = 120,00 = Ø120; 144,8 = 91,95 ≈ Ø92; 119,7 = 76,00 = Ø76; 346,5 = 220,02 ≈ Ø220 (iki
görünüşte aynı); 28,4 = 18,02 ≈ Ø18; ayrıca 20 mm bbox yayı = 2×R10).
* 14 claim, hepsi **ölçülmüş ilkele** bağlı (`target_observation`): Ø270→g50, Ø220→g178/g79,
  Ø158→g43, Ø140→g51, Ø120→g58, Ø92→g59, Ø76→g60/g72, Ø18→g49/g179/g75, R10→g69, R8→g128.
  Beş adet eşmerkezli daire üst-sol görünüşte (büyük flanş yüzü), küçük flanş üst-orta ve
  alt-sağ görünüşlerde; Ø18 üç ayrı çağrı, R8 SECTION A-A'da.
* Bağlanamayan çağrılar kapsam dışı ve gerekçeli: `Ø180,00` (sayfada Ø180 ilkeli yok;
  eşmerkezli küme 270/158/140/124/120/118,3/92/76), `Ø116,00` ×2 (182,7 px'lik ilkel yok — çağrı
  boru profilinin iki düz çizgisi arasını ölçüyor), `R25,00` ×2 (leader uçları ≈(0,777;0,777) ve
  ≈(0,798;0,816); oradaki ayrık yaylar g68/g69 = 2×R10, R25 yayı ayrı ilkel değil).
* `exhaustiveness: predicates` (representation/physical/form/size/termination/depth);
  `reference_sha256` **bf5d3f7e931d7220dbda98a60e3be7ba54c95e72e6b80d2512ccf5dbc8663261**.
* D hücresi (bilgi): 30 aday, 4 eşleşti, **8 ambiguous**, 2 eşleşmemiş claim, 10 FP, 16 kapsam
  dışı. Ambiguity'nin kaynağı D'nin aynı özellik çevresine birden çok aday koyması; `MATCH_POLICY`
  v2 gereği yakın puanlı kalemler puanlanmıyor (sıra bağımsızlığı).

**Yöntem notu (5 raster sayfa için tekrar kullanılabilir):** gözlem tablosundaki daire/yayları
sayfa PNG'sinin üzerine kimlikleriyle çizmek (`overlay`), leader ucunu 0,01 ızgaralı kırpmada
okumak ve ilkel bbox'ını px→mm çevirip çağrıyla karşılaştırmak. Kullandığım geçici araçlar:
`~/.hermes/cache/scratch/{grid_crop.py,overlay.py,gold_check.py}` (scratch 24 saat sonra
temizlenir; `gold_check.py PAGE_ID --arms` tam `--evaluate` koşmadan tek sayfanın
`check_reference`ını ve kol puanlarını verir — yeni gold yazarken hızlı kapı kontrolü).

**Yeni değerlendirme koşusu** (`--evaluate`, iki gold yazıldıktan sonra): koşu
`2b77eafb044a410ac4b3b872340126f7`, değerlendirme kimliği `c104af7f7f61…`; kanıt zinciri 10 hücre
0 kopuk, `lifecycle.ok=true`, D hücreleri `valid_reuse` 10/10 (yeniden koşu gerekmedi), sapma
kayıtları yalnız bilgilendirici (PLAN-7 §3). **B02 `5/10`** (plate-pocket 2 · drawing-2 6 ·
flange-elbow 7 · enclosure 1 · exercise-12 14 = 30 claim). Açık kapılar: B02 (5 sayfa kaldı),
B05 (20 VLM hücresi `to_run`), **B06** (V/VE hiç koşmadığı için `puanlanmış kol: yok` — önceki
koşularda da aynı durumdaydı, bu değişiklikten bağımsız). B01/B03/B04/B07 kapalı.
**Sırada:** `dev-flange-book` + kalan 4 raster frozen sayfa → 10/10 → B02 kapanır; B06/P6 için
gerçek V/VE çağrıları kullanıcı onayı ister.

### 6m. `frozen-exercise-17` (raster) — P3 başladı, gold **henüz yazılmadı** (sıradaki pencere için durum)

Bu pencerede başlandı, ölçüm/okuma durumu aşağıda; **spec yazılmadı**, `gold/`da dosya yok.

* Gözlem dökümü: `--page frozen-exercise-17` → 782 gözlem (593 `line`, 166 `arc`, 15 `text`,
  5 `linear`, 3 `circle`), **çağrı-benzeri metin 0**. Sebep: rasterda tesseract Ø glifini
  düşürüyor — OCR "20.00" (t6, px 1452-1637/1816-1869), "14.00" (t2), "10.00" (t3), "4.00" (t0)
  olarak okudu; `Ø22.00` / `Ø20.00` çağrıları metin katmanında **yok**. Bu yüzden claim'ler
  `vision` kanıtına + ölçülmüş `target_box_norm`a dayanmak zorunda (PLAN-5 §16).
* Sayfa künyesi (vision): dirsek (socket'li), `SCALE 1:1`, A3, mm, AISI 304; görünüşler:
  üst-sol (üstten görünüş), üst-sağ (izo), alt-sol (ön görünüş), alt-sağ (ağız/yan görünüş).
  Okunan çağrılar: **Ø22.00, Ø20.00** (ön görünüşte dikey), **Ø20.00** (alt-sağ görünüşte leader'lı)
  + doğrusal 5.00/14.00/10.00/4.00/3.00.
* Alt-sağ görünüşün ölçümü (piksel taraması, merkez ≈ (1897, 1417)): **dış daire 390 px**,
  **iç daire 285 px** (Hough: g593 = 389 px, g673 = 279 px). İç daireye `Ø20.00` leader'ı iniyor
  (vision okuması).
* **Açık soru (ilk ölçüm adımı):** px/mm. Hipotez A: iç = Ø20 → **14,25 px/mm** (dış 390 px =
  27,4 mm, çağrısız socket bileziği). Hipotez B: dış = Ø22 → 17,7 px/mm (o zaman iç ≈ 16,1 mm,
  `Ø20` ile çelişir). A, yazılı `Ø20` ile uyuşuyor; doğrulamak için ön görünüşteki genişlik çifti
  (Ø22/Ø20 arası) veya socket derinliği `10.00` (t3) pikselle ölçülmeli. Bu ölçüm yapılmadan
  claim yazılmamalı.

### 6n. PLAN-8 geldi — izlenen kanonik gold + manifest kuruldu (§24 madde 1–4, §25 testleri)

**Sorun (§3):** gold spec'leri yalnız `out/lab/.../corpus/gold-specs/` altındaydı; `out/` gitignored
olduğu için temiz klon gerçeği kuramıyordu. Ayrıca `dev-plate-pocket`ın spec dosyası hiç
saklanmamıştı.

**Yapılan (commit `PLAN8-1`):**

* `eval/semread_001b_gold/` — **izlenen kanonik dizin**: `specs/<page>.json` (5 sayfa),
  `manifest.json`, `README.md` (zincir + kurallar).
* `manifest.json`: sayfa başına `source`/`source_sha256`, `spec`/`spec_sha256`,
  `reference`/`reference_sha256`, `claim_count`, `annotator`, `review_status`, `vision_checked`,
  `exhaustiveness` (§4).
* `eval/semread_001b_gold_manifest.py` — `--write` (spec'lerden manifest), `--check` (hash/claim/
  nitelik), `--freeze` (P5: 10/10 sayfa + tüm hash'ler), `--verify` (izlenen spec'ten referansı
  yeniden üret, manifest hash'iyle karşılaştır). Doğrulama: ölçülen kutu (§10), raster
  `vision_checked` + claim başına `vision` kanıtı (§16), **döngüsel ölçek kanıtı reddi** (§11).
* `eval/semread_001b_gold_regions.py`: `--spec` verilmezse **izlenen** spec aranır (yerel kopya
  yedeğe düştü ve çıktıda "yerel (out/ altı — izlenmiyor)" yazar); gözlem tablosu artık
  **tembel** yüklenir → ölçülen kutulu spec'ler OCR/Hough çalıştırmadan üretilir (§24 madde 4).
* `dev-plate-pocket` spec'i **sadık biçimde yeniden kuruldu**: hedefler gözlem kimliğiyle
  (`g12`, `g8`), çağrı kutuları gözlem tablosundaki metin satırlarıyla (`t3`+`t4`+`t5` =
  "4 x"+"6,80 THRU ALL"+"M8 - 6H THRU ALL", `t6` = "50,00"); truth değişmedi —
  üretilen gold-src **ve** gold eski dosyalarla **bayt bayt aynı** çıktı.

**Kanıt (bu turda koşuldu):**

| Sayfa | `--verify` |
| --- | --- |
| `dev-plate-pocket` (pdf) | TAMAM `48671f50…` (2 claim) |
| `dev-drawing-2` (pdf) | TAMAM `f3be4c26…` (6 claim) |
| `dev-flange-elbow` (raster) | TAMAM `2d9138a7…` (7 claim) |
| `frozen-enclosure` (raster) | TAMAM `be3e5654…` (1 claim) |
| `frozen-exercise-12` (raster) | TAMAM `bf5d3f7e…` (14 claim) |

Yani **5/5 izlenen sayfa** kendi spec'inden yeniden üretilebiliyor (§17 çekirdeği; temiz klon
denetiminin yerel kanıtı). `--check`: "5/10 sayfa izleniyor — TAMAM". `--freeze`: **AÇIK**,
eksik sayfalar: `dev-flange-book`, `frozen-exercise-13`, `frozen-exercise-17`,
`frozen-exercise-51`, `frozen-views-exercise` (§13 kapısı doğru davranıyor).

**Test:** `tests/test_semread_001b_gold_manifest.py` — **22 test** (manifest↔disk, temiz üretim,
eksik spec / izlenmeyen gold / kaynak-spec-referans hash uyuşmazlıkları, `require_all` kapısı,
raster vision kuralları, ölçülen kutu doğrulaması, §11 döngüsel kanıt reddi + ölçeksiz kutunun
geçerliliği, spec kaynağı çözümlemesi).

**Sıradaki (PLAN-8 §24):** 5) `frozen-exercise-17` gold'u (§11 kuralı: ölçek bağımsız dayanak
gerektirir; bağımsız dayanak yoksa `corroboration.kind = none` ve mm değeri yalnız yazılı çağrıdan)
→ 6) `dev-flange-book` → 7–9) `frozen-exercise-51`, `-13`, `views-exercise` → 10) 10/10 gold →
11–12) tek değerlendirme (`B02`+`B07` kapalı, `B05`/`B06` açık kalır) → 13) temiz klon denetimi →
14) P5 dondurma → 15) ancak ondan sonra V/VE.

### 6o. P3 — `frozen-exercise-17` gold'u (PLAN-8 §24 madde 5; §11 kuralına uygun) → izlenen 6/10

**Sayfa:** Letter@300dpi varsayımı, 3300x2550 px; OCR bu rasterda Ø çağrılarını düşürüyor
(gözlem tablosunda çağrı metin satırı **yok**) → hedefler **ölçülmüş kutu**, kanıt **vision +
piksel taraması** (§10/§16).

**Ölçek (döngüsel değil, §11):** px/mm ≈ **17,76** iki yazılı çaptan bağımsız olarak çıkarıldı —
Ø22.00 → ön görünüşte kolon bandı 392 px (17,82), Ø20.00 → boru bandı 354 px (17,70) — ve dört
doğrusal ölçüyle çapraz doğrulandı: 14.00 → 248 px, 10.00 → 177 px, 5.00 → 89 px, 4.00 → 71 px
(hepsi ±%0,5). Başlık bloğundaki SCALE değeri kırpmada bulunamadı; notlarda açıkça yazılı.

**Yazılan 3 claim** (hepsi `target_box_norm` + `target_reason` + `corroboration=independent_scale`,
dayanak **karşı çap**):

| claim | çağrı | hedef (px) | ölçüm |
| --- | --- | --- | --- |
| `-01` | Ø22.00 (ön görünüş dikey) | [794,5 · 1223,5 · 89 · 390] | 390 px → 22,0 mm |
| `-02` | Ø20.00 (ön görünüş dikey) | [883,5 · 1241,5 · 177 · 354] | 354 px → 20,0 mm |
| `-03` | Ø20.00 (yan görünüş yatay) | [1719,5 · 1755,5 · 354 · 177] | 354 px → 20,0 mm |

Kapsam dışı (gerekçeli): doğrusal ölçüler (14.00/10.00/5.00/4.00/3.00) — ex12 ile tutarlı olarak
gold yalnız Ø/R çağrılarını kapsıyor; yan görünüşteki iç daire (285 px ≈ 16,0 mm, yazılı çağrısı
yok) da kapsam dışı. D kolunun tek adayı "4" (doğrusal) → `unscorable_extra_candidates: 1`,
yanlış-pozitif değil.

**Sonuçlar:** `check_reference` **ok: true**, sha `a5ebee5c803a…`; `gold_check` — D: 3 claim'in
3'ü eşleşmedi (0/3), V/VE hücresi yok. Manifest **6/10**, `--check` TAMAM,
`--verify --page frozen-exercise-17` TAMAM (ölçülmüş kutulu olduğu için OCR'sız, saniyeler içinde).
`--freeze` hâlâ AÇIK: kalan 4 sayfa `dev-flange-book`, `frozen-exercise-13`, `frozen-exercise-51`,
`frozen-views-exercise`.

**Sıradaki:** `frozen-exercise-13` veya `-51` gold'u (aynı yöntem: ızgara kırpma + satır/kolon
taraması + ASCII harita; gerekirse `callout_texts` ile gözlem kimliği) → 10/10 → tek değerlendirme
→ temiz klon denetimi (`--verify` tüm sayfalar) → P5 dondurma.

### 6p. P3 — `frozen-exercise-13` keşfi (gold yazılmadı; ölçüm turu yarım kaldı)

**Sayfa:** 3300x2550 px, başlık bloğu görsel okuması: TITLE **Exercise 13**, kâğıt **A3**,
**SCALE 1:5**, MAT AISI 304, tarih 29-Aug-24. Görünüşler: üst-orta (plan), alt-orta (ön),
sol ve sağ yan görünüş, sağ-üst izometrik.

**Gözlem tablosu** (`gold_inspect --page frozen-exercise-13`, ~4 dk): 575 gözlem (25 metin,
294 daire/ark); **çağrı benzeri metin 0** → OCR yine Ø/R etiketlerini düşürdü (ex17 ile aynı
durum). 294 dairenin çoğu izometrik görünüşün konturları ve Hough gürültüsü (ör. göbek için
175/193/293 px'lik tutarsız arklar) → **gözlem kimliğiyle bağlama güvenilmez**, ölçülmüş kutu
+ kendi piksel taraması doğru yol.

**Görsel okunan Ø/R çağrıları (7 adet):** Ø25.00 (üst görünüş, sol plaka deliği, ~x 0.24-0.31
y 0.07-0.12), R25.00 (üst görünüş, sağ plaka ucu, ~x 0.58-0.62 y 0.26-0.28), R30.00 (alt görünüş,
sol üst köşe filetosu, ~x 0.29-0.35 y 0.48-0.52), Ø60.00 (~x 0.49-0.53 y 0.45-0.53, leader göbeğin
dış dairesine), R50.00 (~x 0.55-0.60 y 0.49-0.51, leader parçanın sağ uç yayına), Ø25.00
(alt görünüş, ~x 0.51-0.55 y 0.76-0.79, leader göbek deliğine), R10.00 (~x 0.44-0.48 y 0.78-0.82,
yuva köşesi). Kapsam dışı doğrusal ölçüler: 30.00, 50.00 (üst); 170.00, 42.00, 60.00 (x2),
30.00, 60.00, 25.00, 240.00 (alt); 60.00 (sol yan), 10.00, 50.00 (sağ yan).

**Açık ölçüm sorusu (px/mm):** iki aday çelişiyor —
göbek dış dairesi (merkez ≈ 1549,1572) **310 px** → Ø60 ile **5.17 px/mm**;
göbek deliği (aynı merkez) **125 px** → Ø25 ile **5.00 px/mm** (çizgi kalınlığı düzeltmesiyle
~4.9). Üçüncü bir yazılı çap (üst görünüşün Ø25 deliği) ölçülmeden karar verilmemeli; doğru
yöntem ex17'deki gibi: önce **iki bağımsız yazılı çapı** ölçüp px/mm'i sabitlemek, sonra
hedefleri kutu olarak yazmak (§11: hiçbir claim kendi değerine dayanamaz).

**Hazır araçlar (scratch, 24 saatte silinir — gerekirse yeniden yazılır):**
`grid_crop.py` (ızgara kırpma), `lines_report.py` (satır/kolon koşuları), `ascii_map.py`
(bölge yoğunluk haritası), `circle_measure.py` (merkez çevresi koşular + en-dış açıklık),
`text_groups.py` (eğik yazıları **bulamaz** — Ø/R etiketleri 45° olduğu için gruplara
girmedi; yalnız yatay/dikey yazılar için kullan). Scratch dizini: `~/.hermes/cache/scratch/`.

**Sıradaki adımlar (ex13):** 1) üst görünüşten Ø25 deliğini ve R25 yayını ölç, px/mm'i sabitle;
2) göbek/delik/R50/R30/R10 hedeflerini kutu olarak ölç (ex17'deki gibi `target_box_norm` +
`target_reason` + `corroboration=independent_scale`, dayanak **karşı** çap); 3) spec yaz →
`gold_regions --write` → `reference --page` → `gold_check` → `gold_manifest --write/--check/--verify`;
4) `frozen-exercise-51` ve `frozen-views-exercise` (736x1041 px — düşük çözünürlük, en zor sayfa)
aynı yöntemle; 5) 10/10 → tek değerlendirme → temiz klon denetimi → P5 dondurma.

> **Düzeltme (PLAN-9 §7–§8, aşağıda §6q):** ex13 için yukarıdaki "önce iki bağımsız yazılı çapı
> ölçüp px/mm'i sabitle" yaklaşımı **geçersiz** — Ø60 ile Ø25 birbirine dayandırılamaz. Yeni
> yöntem: **bağımsız doğrusal ölçü** (170 / 60 / 30 / 25 / 240 / 50 / 10 adayları) ya da
> güvenilir span yoksa `corroboration.kind = none` (§8: yalnız `SCALE 1:5` notu px/mm vermez).

### 6q. P5 öncesi — PLAN-9 §31/1–4: ex17 kanıt kökü, §6 grafik denetim, kararlı kimlik, atomik `--freeze`

**Ne düzeltildi (PLAN-9 §4–§6):** `frozen-exercise-17` kanıtı karşılıklı döngüseldi — Ø22 claim'inin
ölçek dayanağı Ø20 claim'i, Ø20'ninki Ø22'ydi (validator yalnız **kendi** değerine dayanmayı
reddediyordu; A→B, B→A geçiyordu). Şimdi üç claim'in de kökü **bağımsız 10,00 mm doğrusal
ölçüsü** (kolonlar arası boru boyu ≈177 px → ≈17,7 px/mm); çapraz doğrulama diğer doğrusal
ölçülerle: 14,00 → 248 px (17,71), 5,00 → 89 px (17,80), 4,00 → 71 px (17,75) — yayılım ≈%0,6.
Spec metinleri (target_reason / evidence / notes / reconstruction_note) 17,7 px/mm'e göre
güncellendi; **hedef kutular ve mm değerleri değişmedi** (yazılı çağrılar tek gerçek kaynak,
px geometrisi yalnız kanıt).

**Kod (`eval/semread_001b_gold_manifest.py`):**

* **§6 grafik düzeyi döngüsellik:** `independent_scale` dayanağı, spec içindeki **başka bir
  değerlendirilen Ø/R claim'inin** yazılı değerine çözülüyorsa reddedilir ("döngüsel kanıt
  (grafik) — … {claim_id} = {değer}", §6); doğrusal datum kökü (claim setinin dışı) kabul.
* **§15 `gold_content_identity`:** manifest artık `created_at` taşımıyor; kimlik yalnız gerçeği
  etkileyen yedi alanın (sayfa, kaynak/spec/referans hash'i, claim sayısı, `vision_checked`,
  `exhaustiveness`) kanonik sha256'sı. Aynı içerik → **bayt bayt aynı manifest** (iki ardışık
  `--write` ile doğrulandı; güncel manifest sha `584b54ed457f…`, kimlik `21bf11951d901d38…` (6/10)).
* **§16–§17 atomik `--freeze`:** kapsam + `check_manifest(require_all=True)` + **TÜM sayfaların
  izlenen spec'ten yeniden üretim kanıtı** + kimlik; başarıda `eval/semread_001b_gold/FREEZE.json`
  yazar (şimdilik gold tarafı; §22 tam bağlama listesi madde 14'te). Ayrıca `--verify`
  çalıştırmayı hatırlamak gerekmez.

**Kanıt (bu turda koşuldu):**

* **Kapı gerçek bir sapmayı yakaladı:** spec metni değişince (gold-src henüz yenilenmeden)
  `--freeze`/`--verify` "frozen-exercise-17: yeniden üretim manifestten sapıyor
  (c4bcca71… != a5ebee5c…)" verdi — saklanan referans geçerliydi ama üretim sapmıştı (§16'nın
  varlık nedeni). Zincir izlenen spec'ten yeniden üretildi (`gold_regions --write` →
  `reference --page` → `gold_manifest --write`), ardından tüm kapılar yeşil.
* `--verify` (6/6 sayfa): hepsi **TAMAM**, gold-src aynı — `dev-drawing-2` `f3be4c26…`,
  `dev-flange-elbow` `2d9138a7…`, `dev-plate-pocket` `48671f50…`, `frozen-enclosure`
  `be3e5654…`, `frozen-exercise-12` `bf5d3f7e…`, `frozen-exercise-17` `c4bcca71…`.
* `--check`: "6/10 sayfa izleniyor — TAMAM" (`gold_content_identity: 21bf1195…`);
  `--freeze`: **AÇIK** — tek sorun kalan 4 spec (`dev-flange-book`, `frozen-exercise-13`,
  `frozen-exercise-51`, `frozen-views-exercise`); 6 sayfanın yeniden üretim kanıtı kapının
  içinde koştu ("6 sayfa koşuldu (§17)").
* **Test:** `tests/test_semread_001b_gold_manifest.py` — **33 test** (22 mevcut + 11 yeni:
  karşılıklı döngüsellik reddi, tek-kök reddi, doğrusal datum kabulü, ex17 kök regresyonu, kimlik
  kararlılığı/üstveri ayrımı, manifest↔taze üretim bayt eşitliği, freeze yeniden üretim kanıtı +
  sapma/kimliksizlik/eksik kapsam kapıları). SEMREAD alt kümesi (`tests/test_semread_001b*.py`):
  **179 geçti** (16:49; en yavaş üç test kabul testleri ~335 sn). **Tam pytest: 1188 geçti**
  (41:06).
* README (`eval/semread_001b_gold/README.md`) komutlar + kurallar §6/§15/§16–§17'ye göre güncellendi.

**Sıradaki (PLAN-9 §31):** 5) `frozen-exercise-13` — px/mm **bağımsız doğrusal ölçüden** (§7) ya da
`corroboration.kind = none`; 6) `dev-flange-book` → 7) `frozen-exercise-51` → 8)
`frozen-views-exercise` (§12: çözülemeyen leader → gold dışı + gerekçe) → 9) 10/10 → 10) `--verify`
tümü → 11) mevcut D denemelerini değerlendir (yeniden koşma yok, §21) → 12) B02/B07 durumu →
13) temiz klon denetimi (§18) → 14) `FREEZE.json`u §22 alanlarıyla tamamla → 15) V/VE (ancak ondan
sonra, §24–§26).
