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

Not: `EVALUATION_IDENTITY_FILES` içinde `eval/semread_001b_pilot.py` var — pilot/dosya
düzenlemeleri değerlendirme kimliğini değiştirir ve seçili attempt'leri "bayat" yapar. Bu yüzden
sıra: **kod düzenlemeleri bitince D koşusu**, sonra doküman düzenlemeleri (dokümanlar kimliğe
girmez). D kolu şüphede yeniden koşar (inference maliyeti yok); V/VE'de bu bedel gerçek çağrıdır.
