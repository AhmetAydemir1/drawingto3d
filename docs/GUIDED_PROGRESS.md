# Guided progress

Scope: G0 + G1 (düzeltme turu 1 ve 2 dahil) + G2 (tamamlandı) + **G3 + G1R3-01 (PLAN-21, tamamlandı)**  
Active plan: kök `PLAN.md` (PLAN-21 = inceleme planı; bayt kopya `docs/PLAN-22.md` sha256 `5743bb06…`; önceki kök arşivi `docs/PLAN_ROOT_BEFORE_G3_REVIEW_20261006.md` sha256 `09e18c82…`) + `docs/PLAN-20.md`  
Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
G2 initial HEAD: `316518eb8d67c7a4ad81eed59c09e6c59ef4df37`  
G3 initial HEAD: `ff97295065260ba8d46bf6fcd2c6e864e63dfcef` (`ff97295` = G2)  
Current HEAD: G0 `373e096` + G1.2/G1.3 `554f5ae` + G1.4–G1.7 `e59c5eb` + düzeltme turu 1 `67ff518` + düzeltme turu 2 `316518e` + G2 `ff97295` + **G3 (commit edilmedi)**  
Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)  
Current task: **G1R3-01 + G3 (PLAN-21) tamamlandı** — G1R3-01 ve G3.0–G3.6 PASS; G4+ açılmadı, model çağrısı 0  

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G0 | PASS | `docs/PLAN-20.md`, `report.md` pivot + park kaydı, bu dosya; commit `373e096`; kod değişmedi; 0 model çağrısı | — |
| G1.1 | PASS | Entegrasyon haritası + odak baseline **59 passed / 83.30 s / EXIT=0** (`g1-baseline.log`) | — |
| G1.2 | PASS | `callout_models.py` + `tests/test_callout_models.py` **35 passed** (`g1-2-models.log`); negatifler doğru nedenle kırmızı | — |
| G1.3 | PASS | Store entegrasyonu + `tests/test_guided_callouts.py` 11 passed (`g1-3-callouts.log`); odak kümesi **105 passed / 80.14 s** (`g1-3-green.log`) | — |
| G1.4 | PASS | Freshness/target testleri (T06/T07/T09/T10/T11/T12/T17/T21 + contour varyantı); `source_unavailable` parse semantiği | — |
| G1.5 | PASS | Undo/olay günlüğü testleri (T13/T14/T22 + log denetimi) | — |
| G1.6 | PASS | Build/artifact stale (T15/T16): geç build yeni kararlara bağlanmaz, `build=None` ile çökmez | — |
| G1.7 | PASS | Birleşik doğrulama **174 passed / 79.51 s / EXIT=0** (`g1-7-final.log`); `git diff --check` temiz; kabul tablosu | — |
| **Düzeltme turu 1** | **PASS** | Bağımsız incelemede tekrarlanan 4 sorun kapatıldı; 8 yeni regresyon testi önce kırmızı → sonra yeşil; models+callouts **74 passed** (`g1-fix1-models-callouts.log`); birleşik küme **183 passed / 78.31 s / EXIT=0** (`g1-fix1-final.log`) | — |
| **Düzeltme turu 2** | **PASS** | G1R2-01 (etkin konturda hedef doğrulaması) + G1R2-02 (gerçek yeniden onay günlüğü); bağımsız tekrar exit 0 (`probe-results-after.json`); odak **98 passed** (`g1r2-focus.log`); birleşik **198 passed / 80.05 s / EXIT=0** (`g1r2-final.log`) | — |

## PLAN-21 — G1R3-01 + G3 ilerleme tablosu (aktif görev)

Başlangıç durumu: `ff97295`, worktree ` M PLAN.md` (yeni kök plan) + `?? PLAN-17-HERMES.md`, `?? docs/PLAN_ROOT_BEFORE_G3_REVIEW_20261006.md`, `?? eval/audits/20261006-guided-g2-review/`. Yeni kök plan bayt kopyası `docs/PLAN-22.md` (sha256 `5743bb06…`); önceki kök plan (G2 = PLAN-18 baytı) arşivde `09e18c82…` — ezilmedi.

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G1R3-01 | PASS | `guided.same_physical_point` + `ENDPOINT_IDENTITY_TOLERANCE_PX = contour_audit.TOLERANCE_PX` (0.5 px); onarım bütçesi (20 px) yalnız `correct_profile`'da kaldı. Bağımsız tekrar: `eval/audits/20261006-guided-g2-review/review_probes.py` **exit 0**, 5/5 satır `passed=true` (`probe-results-after.json`; öncesi `probe-results-before.json` `passed=false`, exit 1) · G1 tekrarı exit 0 · kapı **70 passed / 3.14 s / EXIT=0** (`out/guided-callout-review/g1r3-01-gate.log`) · saf geometri pini `tests/test_contour_fix.py::test_point_equality_is_the_audits_own_tolerance_not_the_repair_budget`; store regresyonları `test_two_short_ends_are_two_distinct_points[5/10/20/21]` + `test_a_short_contours_shared_corner_is_still_one_point` | — |
| G3.0 | PASS | Bu bölüm + `docs/PLAN-22.md` (bayt kopya) + `report.md` ürün pointer'ı; G2.6 satırı gerçek duruma çekildi; tarihsel kayıtlar silinmedi | — |
| G3.1 | PASS | `callout_models.py`: `ManualCalloutDecision`, `CalloutReviewDecision`, `CALLOUT_SCHEMA_VERSION=2`, `effective_callouts()` (base + manual + review), `CROP_PADDING=0.02`, `_no_bool`; `guided.py`: `manual_callouts`/`callout_reviews` alanları + eksik-alan-korur/açık-liste-değiştirir merge + `_require_callout` etkin liste üzerinden. Testler: `tests/test_guided_callout_review.py` (yeni) + `test_callout_models` + `test_guided_callouts` + `test_guided_callout_candidates` **109 passed / 54.97 s / EXIT=0** (`/tmp/g31b.log`) | — |
| G3.2 | PASS | `GuidedStore.edit_callout(token, revision, action, payload)` + `_CALLOUT_COMMANDS = (add_region, edit_region, set_ignored, transcribe)`, tek komut = tek history adımı = tek revision; `/api/guided/callout` dispatch; `public()` `callouts` + `effective_callouts` + `callout_detection`; transcription `source_region` sunucuda etkin bölgeden türetilir, `region_changed` stale. Testler: aynı dosya (HTTP conflict/invalid command/foreign source/region freshness) + `test_guided.py`, `test_guided_geometry_*`. Gerçek tarayıcı: adım 19–21 (revision conflict → tek reddedilen istek `POST /api/guided/callout` 400; taslak korunuyor) ve adım 16–17 (`Alan değişti`) | — |
| G3.3 | PASS | `guided.js`: `renderCallouts()` overlay (etiket = sıralanabilir gösterim adı; gerçek ID `id`), tek paylaşımlı koordinat dönüşümü (§7.2 `imagePoint`/`regionBox`/`normalizedRegion`), örtüşmede en küçük kapsayan kutu + ID tie-break hit-test, çift yeniden örneklemeli crop canvas, liste fallback'i; `guided.html` panel + tools. Testler: `test_guided_html.py` (4 yeni yapısal test: JS'in bağlandığı her id HTML'de tam bir kez var; panel kontrolleri; `innerHTML` yok; üretim sınırı metni) → **40 passed / 0.81 s** (`/tmp/g33.log`). Gerçek tarayıcı: adım 3–4 (seçim + crop), 13–14 (manuel alan seçimi + crop), 18 (dar/geniş pencerede aynı kutu + **aynı crop baytları**), 22 (overlay eski profil tıklamasını engellemiyor) | — |
| G3.4 | PASS | Metin alanı, ipucunun yalnız açık eylemle taslağa geçmesi, kaydet/ignore/restore, `state.drafts` ile kaydedilmemiş taslak koruması (§7.3), `busy()` textarea farkındalığı. Gerçek tarayıcı: adım 5–12 (raw `"  4 × Ø8 THRU  "` aynen + normalized ayrı; reload sonrası aynı; undo; ignore → “Yok sayılanları göster” → geri al), 20–21 (conflict'te taslak duruyor, sonra bilinçli kayıt), 23 (markup metin kalıyor), 27–28 (tek reddedilen istek dışında console hatası yok) | — |
| G3.5 | PASS | `Yeni alan çiz` / `Alanı düzelt` pointer akışı (pointer capture, Escape iptali, `suppressClick` ile drag sonrası click yutma, min/max normalize), `add_region` ID'yi sunucuda `manual:<uuid4>` olarak alır, `edit_region` bölge override'ı detected region'ı silmez. Gerçek tarayıcı: adım 13–17 (manuel alan + seçim + crop; bölge taşıma eski `raw_text`/`source_region`'ı değiştirmiyor; panel `Alan değişti`), 24–26 (sıfır alan ret, Escape iptali, tersten çizim normalize) | — |
| G3.6 | PASS | Birleşik pytest (18 dosya, PLAN-21 §10.1) **285 passed / 139.81 s / EXIT=0** (`out/guided-callout-review/g3-combined.log`); gerçek tarayıcı **28/28 adım PASS / EXIT=0** (`eval/audits/20261006-guided-g3-review/browser-acceptance.log`, 15 screenshot, `browser-steps.json` — adım listesi bu dosyada); iki bağımsız review scripti **exit 0**; teslim bloğu `eval/audits/20261006-guided-g3-review/DELIVERY.md`. Bilinen eski `test_planner::test_settings_record_is_the_run_record_fields` failure'ı kapsam dışı ve açık | — |

### G3 kabul kanıtı — zorunlu davranış matrisi (PLAN-21 §9)

Sürücü: `eval/audits/20261006-guided-g3-review/browser_acceptance.py` + `cdp_client.py` (gerçek Chrome, gerçek fare/klavye olayları, CDP; her adımın gözlemi `browser-steps.json`, tam teslim `DELIVERY.md`). Adım numaraları `browser-steps.json` sırasıdır.

| Matris | Kanıt |
|---|---|
| U01 | tarayıcı adım 2–3 (45 aday listelenir; kutuya tıklama yalnız seçer) + `test_effective_callouts_is_the_base_list_until_the_user_adds_something`, `test_computing_the_effective_view_writes_nothing` |
| U02 | adım 4 (`Makine ipucu (öneri): 6` ayrı satır; textarea boş; otomatik transcription yok) |
| U03 | adım 5–7 (raw `"  4 × Ø8 THRU  "` aynen, normalized ayrı, reload sonrası aynı) + `test_the_text_is_kept_verbatim_and_the_source_region_is_the_servers` |
| U04 | `test_a_blank_text_is_refused` (boş/whitespace açık ret; karar değişmez) |
| U05 | adım 13–15 + `test_a_manual_callout_takes_its_own_server_assigned_identity`, `test_a_manual_callout_can_carry_the_users_text` |
| U06 | adım 16–17 (`Alan değişti`) + `test_moving_the_region_stales_the_old_text_and_never_rewrites_it` |
| U07 | `test_saving_the_text_again_on_the_new_region_is_a_new_user_decision` (yeni revision + yeni `source_region`; eski parse/target geçerli olmaz) |
| U08 | adım 10–12 + `test_ignore_keeps_the_text_and_restore_brings_the_callout_back`, `test_a_text_cannot_be_written_to_an_ignored_callout` |
| U09 | adım 8–9 + `test_a_review_survives_undo_and_a_fresh_store_instance`, `test_an_edit_makes_the_old_step_historical_without_resurrecting_it` |
| U10 | `test_a_missing_key_keeps_the_new_decisions_and_an_explicit_empty_removes_them`, `test_a_history_entry_from_an_older_schema_still_undoes` |
| U11 | adım 19–21 (adım 27–28: tek reddedilen istek `POST /api/guided/callout` → 400; taslak duruyor; sonra bilinçli kayıt başarılı) + `test_a_stale_revision_command_is_refused_and_keeps_the_stored_decisions` |
| U12 | `test_an_unknown_callout_or_a_foreign_source_is_refused_without_a_write` |
| U13 | adım 24–26 (sıfır alan reddi “Alan çok küçük”; Escape iptali hiç karar yazmadı; tersten çizim `[0.62, 0.60, 0.80, 0.80]` olarak normalize) + `test_a_region_the_server_cannot_draw_is_refused` |
| U14 | adım 18 (dar 520 px / geniş 1400 px: aynı satır seçildi, crop canvas **bayt-eşit**) |
| U15 | adım 22 (profil aracı konturu seçti; overlay tıklamayı çalmadı) |
| U16 | adım 23 (`<img src=x onerror=…>` metin olarak; `imgs: 0`) + `test_callout_text_is_never_rendered_as_markup` (script'te `innerHTML` hiç yok) |
| U17 | `test_the_base_candidates_and_the_reading_never_move_from_a_review` + mevcut `/accept` testleri |
| U18 | `test_computing_the_effective_view_writes_nothing`, `test_the_base_candidates_and_the_reading_never_move_from_a_review` |
| U19 | G1 stale/source testleri + `test_an_unknown_callout_or_a_foreign_source_is_refused_without_a_write` |
| U20 | adım 6 (panel yalnız “Metin kaydedildi”; “Kaydet ve ayrıştır”/“Parsed”/“Bound” yok) + `test_the_production_panel_admits_callout_text_is_not_used_yet` |

Harness/ortam notları (teslimi etkileyen, açıkça kayıtlı): Hermes'in tarayıcı aracı bu oturumda `127.0.0.1`'i SSRF korumasıyla reddetti → kabul, aynı Chrome CDP ile doğrudan sürülerek yapıldı; bu sırada yazılan 4 `browser.*` anahtarı iş sonunda geri alındı. Audit dizininde `uv run` `.venv`'i lockfile'a senkronlayıp paketleri kaldırdı → `uv sync --extra dev` + `cadquery-ocp-novtk==8.0.1.1.0` ile onarıldı, `check_env.py` ile doğrulandı; oluşan `uv.lock`/`egg-info` silindi. Ayrıntı: `DELIVERY.md`.

## G2 ilerleme tablosu (kök `PLAN.md` = PLAN-18; bayt kopya `docs/PLAN-21.md`)

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G2.0 | PASS | Kickoff: kök plan kuruldu (PLAN-18 sha256 `09e18c82…`; önceki kök arşivi `docs/PLAN_ROOT_BEFORE_G2_20261006.md` `429a0d75…`; `docs/PLAN-21.md` bayt kopya); baseline odak `test_callout_models`+`test_guided_callouts` **89 passed / 1.95 s / EXIT=0** (`g2-baseline-focus.log`); 15 dosya **198 passed / 82.19 s / EXIT=0** (`g2-baseline-combined.log`) | — |
| G2.1 | PASS | `src/drawingto3d/callouts.py` + `tests/test_callout_candidates.py`; RED `g2-1-red.log` (ModuleNotFoundError, exit 2) → **29 passed / 0.31 s / EXIT=0** (`g2-2-candidates.log`; matris §23 sıra 1–20 + §85/§86/§89 guard'ları) | — |
| G2.2 | PASS | Aynı dosyada sertleştirme: canonical region (tek nokta, 8 basamak), `expected_id` testiyle birebir pinlenen canonical JSON+SHA-256 kimlik, method resolver, exact dedup + provenance union, deterministik sıralama ve dedupe diagnostics, purity guard (uuid/random/Path/observe yok) | — |
| G2.3 | PASS | `guided.py` create: aynı `observations` nesnesinden adaptör (ikinci observe/OCR yok); `callout_candidates` + `callout_detection` persist; §28 digest cross-check → `source_digest_mismatch`; RED `g2-3-red.log` (6 failed / 6 passed) → `tests/test_guided_callout_candidates.py` **12 passed / 19.86 s / EXIT=0** (`g2-3-green.log`); tek-observe + tek-adaptör spy; build/kullanıcı olayı yok | — |
| G2.4 | PASS | Gerçek vektör (plate): 45 text → 45 aday, id kümesi birebir, bağımsız normalizasyon eşitliği (§98); gerçek raster (flange-elbow-90): 27 OCR ifadesi → 27 `raster_region` aday, bölge-sahip eşlemesi birebir; dürüst-none (metinsiz gerçek raster): 0 aday + `no_text_observations`, ikinci OCR çağrısı yasak-spy; ağır flange probe 29/29 (`g2-4-probe.log`); testler `tests/test_guided_callout_candidates.py` **15 passed / 51.40 s / EXIT=0** (`g2-4-green.log`) | — |
| G2.5 | PASS | reopen: kayıt eşitliği + dosya baytları değişmez + load redetect/adaptör çağırmaz + sahte kullanıcı olayı yok; legacy (callout öncesi oturum): observe yasak-spy ile okuma, eski kararlar korunur, hiçbir şey yazılmaz; kaynak kaybı: adaylar silinmez, `geometry.stale` mevcut davranış; §93 save/undo adaptörü hiç çalıştırmaz; §95 aday listesi history snapshot'ında yok; §96 build sonucu candidate base'i oynatmaz | — |
| G2.6 | PASS | Seçili regresyon (15 G1 dosyası + 2 yeni dosya): **242 passed / 130.66 s / EXIT=0** (`g2-6-selected.log`); §68 metrikleri (`g2-6-metrics.log`: vektör 45/45/0/0, raster 27/27/0/0, dürüst-none 0 + `no_text_observations`); full pytest **1479 passed / 1 failed / EXIT=1** (`g2-6-full.log`; tek kırmızı G2 dışı ve önceden mevcut `test_planner` pini); diff check yapıldı (`g2-6-diffcheck*.log`); commit `ff97295` | — |

## G2 final kanıt (kök `PLAN.md` §60/§61/§68/§106)

Exact komut zinciri ve çıktıları:

```text
.venv/bin/python -m pytest -q tests/test_callout_candidates.py        > out/guided-transcription/g2-2-candidates.log    # 29 passed / 0.31 s / EXIT=0
.venv/bin/python -m pytest -q tests/test_guided_callout_candidates.py > out/guided-transcription/g2-4-green.log      # 15 passed / 51.40 s / EXIT=0
.venv/bin/python -m pytest -q <15 G1 dosyası + 2 yeni dosya>          > out/guided-transcription/g2-6-selected.log   # 242 passed / 130.66 s / EXIT=0
.venv/bin/python -m pytest -q                                         > out/guided-transcription/g2-6-full.log       # 1 failed, 1479 passed / 4519.6 s (1:15:19) / EXIT=1 — tek kırmızı G2 dışı, önceden mevcut
PYTHONPATH=src .venv/bin/python ~/.hermes/cache/scratch/g2-6-metrics.py | tee out/guided-transcription/g2-6-metrics.log   # EXIT=0 (§68 metrikleri)
git diff --check ; git status --short                                 # aşağıdaki sınıflandırma
```

G2 §61 final report:

```text
HEAD / worktree: G2 commit'i ("guided: G2 — …"); öncesi 316518e
G2.0 baseline: 89 passed / 1.95 s (odak); 198 passed / 82.19 s (15 dosya) — EXIT=0
G2.1 adapter: RED ModuleNotFoundError (g2-1-red.log) → 29 passed / 0.31 s (g2-2-candidates.log)
G2.2 identity/dedup: canonical JSON+SHA-256 pin; dedup/union/hint/sıra/diagnostics guard'ları (aynı dosya)
G2.3 store integration: RED 6 failed / 6 passed → 12 passed / 19.86 s (g2-3-red.log → g2-3-green.log)
G2.4 vector/raster: plate 45/45 (id kümesi birebir, bağımsız normalizasyon); flange-elbow-90 27/27; Flange probe 29/29 (g2-4-probe.log); dürüst-none 0 + no_text_observations; 15 passed / 51.40 s (g2-4-green.log)
G2.5 reopen/legacy: reopen exact + yazımsız okuma; legacy observe-yasak; save/undo adaptörsüz (§93); history snapshot'ında aday yok (§95); build base'i oynatmaz (§96); kaynak kaybında adaylar korunur (§49)
Combined tests: 242 passed / 130.66 s / EXIT=0 (g2-6-selected.log; 15 G1 dosyası + 2 yeni)
Full pytest: 1479 passed / 1 failed / 4519.6 s (1:15:19) / EXIT=1 (g2-6-full.log) — tek kırmızı G2 dışı ve HEAD'de önceden mevcut: `tests/test_planner.py::test_settings_record_is_the_run_record_fields` (88ba6c5 `repeat_penalty`/`repeat_last_n`'i `ChatSettings.as_dict`'e ekledi, testin pinli anahtar kümesi güncellenmedi; `llama.py` ve `test_planner.py` G2 diff'inde yok, tek başına da kırmızı)
Diff check: kod/test diff'i temiz; staged toplam 25 uyarı, tümü hard-break satır sonu: 10 PLAN.md + 10 docs/PLAN-21.md (verbatim plan kopyası) + 5 GUIDED_PROGRESS başlık/durum satırı — 373e096'da 12 uyarılık yerleşik stille aynı sınıf (kaynak sadakati; `g2-6-diffcheck.log` / `g2-6-diffcheck-cached.log`)
Changed files: src/drawingto3d/callouts.py (yeni); src/drawingto3d/guided.py; tests/test_callout_candidates.py (yeni); tests/test_guided_callout_candidates.py (yeni); docs/GUIDED_PROGRESS.md; report.md; PLAN.md (kurulum); docs/PLAN-21.md (bayt kopya); docs/PLAN_ROOT_BEFORE_G2_20261006.md (arşiv)
Known open issues: §101→G3 (overlay/transcription/ignore/manual region), §102→G4 (grammar), §103→G5/G6 (target), §104→G7/CAD; §65 confidence politikası; §66 yüksek-recall yanlış-pozitifler G3 ignore akışına; ayrıca G2 dışı önceden-kırmızı `test_planner.py::test_settings_record_is_the_run_record_fields` (yukarıda)
Model calls: 0
G3 status: NOT OPENED
NEXT SINGLE STEP: G3 plan/request
```

Ölçülen §68 metrikleri (bu ortam, gerçek fixture'lar; `g2-6-metrics.log`):

```text
vektör / plate          : texts=45  candidate=45  invalid=0  dedup=0  vector=45  raster=0   diagnostics=[]
raster / flange-elbow-90: texts=27  candidate=27  invalid=0  dedup=0  vector=0   raster=27  diagnostics=[]
raster / metinsiz sayfa : texts=0   candidate=0   invalid=0  dedup=0  honest none      diagnostics=["no_text_observations"]
ağır raster / Flange.PNG: texts=29  candidate=29  (probe; 258.3 s — test_raster ile aynı gözlem yolu, g2-4-probe.log)
```

Doğru başarı cümlesi (§69): mevcut observation text bölgeleri deterministic, provenance-preserving ve reopen-stable `CalloutCandidate` kayıtlarına dönüştürülebiliyor. "Program teknik resmi anlıyor / Ø8 otomatik okunuyor / binding çözüldü / STEP doğruluğu arttı" iddiaları bu fazda geçerli değildir.

## G2 DoD kontrol listesi (kök `PLAN.md` §60)

- [x] pure adapter module exists — `src/drawingto3d/callouts.py` + purity guard testi
- [x] detector version single-source — `CALLOUT_DETECTOR_VERSION`; create `detection.detector_version` persist eder
- [x] px→normalized math pinned — 1000×500 / (100,50,200,100) → `[0.1,0.1,0.3,0.3]`
- [x] deterministic SHA-256 identity — `expected_id` canonical JSON pin testi
- [x] source path not identity — kimlik beş alandan; yeniden adlandırma id'yi değiştirmez
- [x] method-based source kind — pdf-text/tesseract-tsv eşlemesi; suffix'ten tahmin testle yasaklı
- [x] exact dedup only — aynı bölge birleşir; 1 px fark ayrı kalır
- [x] provenance union — sıralı/unique; şema sınırında dürüst `provenance_ids_capped`
- [x] conflicting hints not truth — `hint=None` + `duplicate_hint_conflict`
- [x] invalid bbox diagnostic, no clamp — 4 bbox kodu + `region_collapsed`; kırpma yok
- [x] deterministic ordering — y0,x0,y1,x1,kind,id; giriş sırasından bağımsız
- [x] no semantic field promotion — `value/unit/kind/count` karara dönüşmez; dump anahtarları pinli
- [x] new session persists candidates — create → 45 aday; `callout_detection` metadata
- [x] no auto transcription — state'te transcription yok; `needs_transcription`
- [x] no auto parse — `callout_parses == []`
- [x] no auto target — target yok; `needs_target`
- [x] no model call — model/network importu yok; 0 çağrı
- [x] real vector fixture — plate 45/45
- [x] raster exercised or honestly blocked — flange-elbow-90 27/27 (BLOCKED_ENV değil)
- [x] honest-none test — metinsiz gerçek raster → [] + `no_text_observations`
- [x] reopen exact — kayıt eşitliği + bayt sabit + redetect yok
- [x] legacy no-redetect — observe-yasak spy
- [x] no fake user events — create/reopen log'larında user olayı yok
- [x] G1 regression green — 242 passed (17 dosya)
- [x] diff check clean — yukarıdaki sınıflandırma
- [x] progress updated — bu dosya
- [x] G3 still NOT OPENED — G3 işi yapılmadı

## G2 handoff snapshot (kök `PLAN.md` §107)

```text
CURRENT HEAD
G2 commit ("guided: G2 — …") üzerine 316518e

ACTIVE PRODUCT
Guided transcription

UMBRELLA PLAN
docs/PLAN-20.md

PROGRESS
G0 PASS
G1 PASS after two review/fix rounds
G2 PASS — deterministic Observations → CalloutCandidate producer live

G2 CONTRACTS
callouts.CALLOUT_DETECTOR_VERSION = "callout-detector/1"
CalloutDetection / DetectionDiagnostic (computed transport, not user decisions)
GuidedStore.create persists callout_candidates + callout_detection; base state = candidates only
no transcription / parse / target / model / material decisions
reopen and legacy loads never redetect, never rewrite, never fabricate user events

MISSING NEXT PIECE
No G3 decision path: no overlay, no user transcription, no ignore, no manual region.

RESEARCH
SEMREAD-001D parked; no inference.

NEXT SINGLE STEP
G3 plan/request (G3 NOT OPENED)

G3+
NOT OPENED
```

## Düzeltme turu 1 (bağımsız inceleme) — önce/sonra

**Önceki kabulün eksikleri (dürüst kayıt):** G1.2–G1.7 kabulü şunları kaçırmıştı — (a) taşınan onayın sunucu alanlarının istemci değerleriyle yazılması; (b) tek-save'de pin/doğrulama bağlamı tutarsızlığı; (c) parse kapısının **varlık** kontrolünde kalması (status'a bakmaması); (d) vertex_pair sözleşmesinin yanlış daraltılması (ardışıklık şartı + yalnız `v{index}` kabulü).

| # | Sorun (inceleme) | Önce (repro) | Sonra (nasıl kapatıldı) | Kanıt |
|---|---|---|---|---|
| 1 | Taşınan hedefin sunucu alanları istemciden yazılabiliyordu | Onayla → profil değiştir → stale; istemci `geometry_key`+`profile_id` güncelleyince hedef yeniden **current** yazılıyordu | `_target_carried` artık sunucu alanlarını/evidence'ı karşılaştırmıyor; taşınan satır **kalıcı kayıttan byte-korunur** (istemci sürüklenmesi yazılmaz). Gerçek yeniden onay tek kullanımlık açık `reconfirm` isteğidir (`CalloutTargetDecision.reconfirm`): doğrulama gördükten **sonra** tüketilir, kayıtta daima `false`. Evidence değişimi yeniden onay **değildir**. | `test_a_carried_target_keeps_its_persisted_server_fields`, `test_a_real_reconfirmation_is_an_explicit_act` |
| 2 | Profil değişimi + yeni hedef onayı aynı save'de tutarsız | `selected=outline_2` iken `target.profile_id=outline_1` yazıldı, key yeni bağlamdan; target **current** görünüyordu (kırmızı kanıt: `assert 'outline_1' == 'outline_2'`) | Pinleme **ve** geometri denetimi bu save'in payload bağlamından: `profile_id` = seçili profil, kenar çözümü **yeni** konturda yapılır; eski konturun uç kimliği yeni bağlamda reddedilir | `test_a_profile_switch_and_a_new_confirmation_in_one_save_agree`, `test_a_new_confirmation_is_checked_against_the_new_context` |
| 3 | Başarısız/çelişkili parse hedef onayına dayanak olabiliyordu | `status=unsupported`/`ambiguous` fixture ile yeni target kabul edilip **current** gösteriliyordu; kapı yalnız "kayıt var mı" diyordu | Kapı: exact kayıt **tek ve `status='parsed'`** olmalı; aynı kimlikli farklı içerikli parse kayıtları reddedilir. Tazelik hesabı ile anlamsal geçerlilik ayrı kaldı (hesap current diyebilir; onay dayanağı olamaz) | `test_a_failed_parse_cannot_be_the_basis_of_a_target_confirmation[unsupported/ambiguous]`, `test_conflicting_parse_records_refuse_a_target_confirmation` |
| 4 | vertex_pair sözleşmesi yanlış daraltılmış | Ardışıklık şartı vardı (v0–v2 reddediliyordu); mevcut kararlı uç kimlikleri (`g0:start`) reddediliyor, yalnız `v{index}` kabul ediliyordu | Mevcut kararlı uç kimlik yolu kullanılır: `<edge_id>:start|end` (binding çözücüsüyle aynı kenar araması) + kanonik `v{index}`; **komşuluk şartı kaldırıldı**; aynı fiziksel noktanın iki farklı ID ile seçilmesi ayrıca reddedilir. Ardışık-olmayan çifti reddeden eski test düzeltildi. | `test_a_vertex_pair_uses_the_stable_endpoint_ids`, `test_a_vertex_pair_rejects_the_same_physical_point_twice`, düzeltilen `test_wrong_targets_are_refused_without_touching_the_record` |

Ek: eski akışı kodlayan 4 mevcut test yeni açık mekanizmaya taşındı (evidence-reconfirm → `reconfirm` bayrağı; "hedef düzenlemesi" → gerçek seçim değişikliği). **RED kanıtı:** düzeltme öncesi hedefli koşum **8 failed / 2 passed** (yalnız yeni testler; hata 2 birebir: `assert 'outline_1' == 'outline_2'`); düzeltme sonrası aynı hedef küme **11 passed**. İlk yeşil koşumda ek bir hata yakalandı ve düzeltildi: `reconfirm` bayrağının `_prepare_callouts` içinde erken tüketilmesi doğrulamayı atlatıyordu (`DID NOT RAISE`) → tüketim `_consume_reconfirm` ile doğrulamadan sonraya alındı.

## Düzeltme turu 2 (bağımsız inceleme #2, kök `PLAN.md`) — önce/sonra

**Önceki kabulün (tur 1) eksikleri (dürüst kayıt):** (a) `_check_target_geometry` uçları ham `options.profiles[].edges` üzerinden çözüyordu — aynı save'in kontur düzeltmesi (`contour.drop`) uygulanmıyordu ve `vN` düzeltilmiş listenin yeni indisine bağlanabiliyordu; (b) `_log_callout_changes` yalnız `target_kind`/`target_ids` eşitliğine bakıyordu — bağlamı değişmiş *gerçek* yeniden onay (stale→current) log'a yazılmıyordu.

| # | Bulgu | Önce (`probe-results-before.json`, HEAD `67ff518`) | Sonra (düzeltme + kanıt) |
|---|---|---|---|
| G1R2-01 | Çıkarılan kenarın ucu geçerli hedef olarak kaydedilebiliyordu (düzeltilmiş kontur geçerli olmasına rağmen) | `rejection=null`, `record_unchanged=false`, `target=current` — aynı save'de `d2` çıkarılıp `d2:start` onaylanabiliyordu | Doğrulama **etkin kontur** üzerinde: `correct_profile` build ile birebir aynı parametrelerle çalışma kopyasında uygulanır (`record.options` yerinde değişmez); kimlik önce **kayıtlı bağlamda** kararlı `<edge_id>:start\|end`'e çözülür, düzeltmede yoksa `"hedef uç kimliği bu düzeltmeden sonra konturda yok (yeniden seçin)"` ile reddedilir; `vN` asla düzeltilmiş listenin yeni indisine bağlanmaz; yeni onay kararlı kimlikle **saklanır**; fiziksel eşitlik koordinat + `RASTER_JOIN_TOLERANCE_PX` ile (ham sıra numarasıyla değil). `rejection="…(yeniden seçin): d2:start"`, `record_unchanged=true` — `probe-results-after.json`, exit 0 |
| G1R2-02 | Gerçek yeniden onayın (stale→current) log izi yoktu | `new_log_actions=[]`, `new_confirm_events=0` (rev 3→4 yazıldı ama olay yok) | `_confirmation_context_same`: taşınan onay = aynı seçim **artı aynı onay bağlamı** (`geometry_key`/`geometry_version`/`profile_id` + transcription/parser bağı); bağlam değişmişse tam 1 yeni `user/confirm_target` yazılır; evidence'ta `callout_id`/`geometry_key`/`profile_id`/`transcription_revision`/`parser_version` incelenebilir (kişisel metin kopyalanmaz). `new_confirm_events=1`, target current — `probe-results-after.json`, exit 0 |

**Zorunlu matris karşılığı (kalıcı, gerçek store testleri — mock yok):** R1-A `test_a_removed_endpoint_can_never_be_confirmed_in_the_same_save` · R1-B `test_a_saved_correction_keeps_refusing_its_removed_endpoint` · R1-C `test_a_removed_edge_stales_its_target_and_refuses_the_reconfirm` · R1-D `test_a_confirmation_on_the_corrected_contour_uses_the_new_context` · R1-E `test_an_unrelated_edit_leaves_a_carried_stale_target_and_logs_no_confirmation` · R1-F `test_undo_and_reopen_after_a_correction_never_resurrect_a_mismatched_target` · R1-G genişletilen `test_a_vertex_pair_rejects_the_same_physical_point_twice` · R1-H `test_v_names_resolve_in_the_recorded_context_never_the_corrected_list` · R2-A `test_a_stale_to_current_reconfirm_is_written_to_the_log` · R2-B `test_a_reconfirmation_on_a_new_transcription_binding_is_logged` · R2-C genişletilen `test_a_carried_target_keeps_its_persisted_server_fields` (sürüklenme onay üretmez) · R2-D `test_a_reconfirm_against_a_failed_parse_changes_nothing[unsupported/ambiguous/çelişkili]` · R2-E `test_reopen_and_public_freshness_write_no_confirmation_events` · R2-F `test_an_undo_after_a_reconfirmation_logs_no_fake_confirmation` · §5.2 notu `test_a_reconfirm_in_the_unchanged_context_stays_a_noop` (değişmeyen bağlamda no-op korunur — testle belgelendi).

**RED kanıtı:** düzeltme öncesi aynı testlerle `tests/test_guided_callouts.py` → **7 failed, 46 passed** (R1-A/B/C, R1-H, R2-A, R2-B + güncellenen wrap testi; hatalar "DID NOT RAISE" / "0 == 1"); düzeltme sonrası **54 passed**. Eski beklenti düzeltmesi: `test_a_vertex_pair_wraps_around_the_selected_contour` artık kararlı kimliğin saklandığını doğrular (eski `["v3","v0"]` beklentisi sözleşmeye göre düzeltildi; kalan kontroller gevşetilmedi). R1-F dürüst ayrım: undo ile düzeltme geri alınınca hedef **o zamanki** (düzeltmesiz) geometriye uyar — current olması beklenen durum; "uymayan hedef current olmaz" tarafı reopen senaryosuyla doğrulanır.

## G1 kabul tablosu (PLAN-20 §13) — düzeltme turu sonrası

| Kabul maddesi | Durum | Kanıt |
|---|---|---|
| G0 aktif plan/pivot tutarlı; tarihsel araştırma korunmuş | PASS | `373e096`; PLAN-19 ve öncesi dokunulmadı; report.md tarihsel işaretli |
| Dört temel model var; kullanıcı/metin/parse/hedef ayrımı açık | PASS | `callout_models.py`; `test_callout_models.py` (35) |
| Raw text birebir; normalized ayrı ve deterministik | PASS | T02 store testi; sunucu normalizasyon testi; `geometry_key` determinizm testleri |
| Gerçek store round-trip + yeni instance reopen | PASS | `test_save_persists_a_transcription_and_reopen_keeps_raw_text`; pin testinde reopen |
| Eski session, history, eski istemci veri kaybetmiyor | PASS | T04/T05/T19/T20; bayt-karşılaştırmalı dosya kontrolleri |
| Transcription revision ≠ global revision | PASS | T08; ilk kayıtta sunucu ataması (777 → gerçek) |
| Aynı geometry_version'da geometri/bağlam değişimi target'ı stale yapar | PASS | Profil, kontur ve sürüm-uyuşmazlığı testleri; `geometry_key` birim testleri |
| Undo snapshot'ları doğru geri getiriyor; stale STEP dirilmiyor | PASS | T13/T14; `_fake_build` sonrası edit/undo → current STEP yok |
| Parse/target freshness public state'te nedenleriyle görülebiliyor | PASS | `callouts[]`: current/stale/missing + `reason` (tüm stale testleri) |
| Stale client, yanlış hedef ve geç biten build doğrulandı | PASS | T07; `test_wrong_targets_are_refused_...`; T16 yarış; **düzeltme turu 1: alan tampering'i + sahte reconfirm + çelişkili parse** |
| İlgili eski testler + T01–T22 yeşil; skip/blocked başarıya katılmadı | PASS | **183 passed, 0 failed, 0 skipped** (`g1-fix1-final.log`); T eşlemesi aşağıda |
| UI/parser/compiler uygulanmadı → rapor bunu sonraki faz yazıyor | PASS | Teslim raporu; G2/G3/G4 kapsamı |
| İlerleme dosyasında kalan ve gerçek komut sonuçları | PASS | bu dosya + `out/guided-transcription/*.log` |

## T01–T22 eşlemesi (`tests/test_guided_callouts.py` / `tests/test_callout_models.py`)

T01 round-trip → models testleri · T02 raw/reopen → `test_save_persists_a_transcription_and_reopen_keeps_raw_text` · T03 hint → `test_a_machine_text_hint_never_becomes_a_decision` · T04 eski session → `test_an_old_session_opens_serves_its_build_and_is_not_rewritten` · T05 eski history'ye undo → `test_undo_accepts_a_history_entry_without_the_new_fields` · T06 metin değişimi → `test_editing_the_text_stales_the_old_parse_and_target_and_keeps_history` · T07 revision conflict → `test_a_stale_revision_save_is_refused_and_the_record_keeps_its_first_value` · T08 ilgisiz edit → `test_an_unrelated_edit_bumps_the_session_but_not_the_transcription_revision` · T09 kaynak/sürüm → `test_a_changed_source_stales_the_callout_layer_and_the_build` + `test_a_geometry_version_mismatch_stales_the_target` · T10 profil/kontur → `test_a_profile_change_stales_the_target_within_the_same_geometry_version` + `test_a_contour_change_stales_the_target_in_the_same_version` · T11 yanlış hedef → `test_wrong_targets_are_refused_without_touching_the_record` (+ `test_a_vertex_pair_rejects_the_same_physical_point_twice`) · T12 count → `test_an_explicit_count_must_match_the_unique_targets` · T13 undo → `test_undo_restores_the_earlier_callout_decisions_and_stales_the_build` · T14 → `test_undo_does_not_make_an_old_target_current_again` · T15 → `test_a_later_edit_leaves_the_old_step_historical_and_never_current` + `test_a_target_edit_also_makes_the_old_step_historical` · T16 → `test_a_build_that_finishes_late_never_attaches_to_newer_decisions` · T17 çift load → `test_loading_twice_changes_nothing` · T18 no-op → `test_saving_the_same_transcription_again_is_a_noop` · T19 eski istemci → `test_missing_keys_keep_callout_decisions_and_explicit_empty_removes_them` · T20 accept → `test_accept_keeps_callout_decisions_and_confirms_nothing` · T21 parser sürümü → `test_an_old_parser_version_fixture_stales_its_parse_and_target` · T22 temel veri → `test_base_reading_and_options_survive_callout_edits_and_undo`

## Son doğrulamalar

- **Düzeltme turu 2 bağımsız tekrar**: `PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py` → **exit 0**, iki bulgu da `passed=true` — `eval/audits/20261006-guided-g1-review/probe-results-after.json` (öncesi: `probe-results-before.json`)
- **Düzeltme turu 2 odak**: `test_guided_callouts` + `test_callout_models` + `test_contour_fix` + `test_binding_end_meaning` → exit 0, **98 passed** — `out/guided-transcription/g1r2-focus.log`
- **Düzeltme turu 2 birleşik**: 15 dosya → exit **0**, **198 passed** (80.05 s) — `out/guided-transcription/g1r2-final.log`; `git diff --check` temiz
- **Düzeltme turu 2 RED**: hedefli `tests/test_guided_callouts.py` koşumu düzeltme öncesi **7 failed / 46 passed** → sonra **54 passed**
- **Düzeltme turu 1 birleşik**: 15 dosya (models + callouts + odak 6 + guided'a dokunan 7) → exit **0**, **183 passed** (78.31 s) — `out/guided-transcription/g1-fix1-final.log`
- **Düzeltme turu 1 odak**: `test_callout_models.py` + `test_guided_callouts.py` → exit 0, **74 passed** — `out/guided-transcription/g1-fix1-models-callouts.log`
- **RED kanıtı** (düzeltme öncesi hedefli `-k`): **8 failed / 2 passed**; hata 2'nin birebir çıktısı `assert 'outline_1' == 'outline_2'`
- Önceki kümeler: G1.7 **174 passed** (`g1-7-final.log`); G1.3 **105** (`g1-3-green.log`); G1.2 **35** (`g1-2-models.log`); G1.1 **59** (`g1-baseline.log`)
- `git diff --check` → temiz (CHECK_EXIT=0)

## Entegrasyon haritası (G1.1) — mevcut store yolları × yeni callout alanları

| Store yolu | G1'de yeni alanlara nasıl dokundu (uygulandı) |
|---|---|
| `create` | `callout_schema_version` + boş `callout_candidates`/`callout_parses`; `decisions` yeni listeleri boş taşır |
| `load` | Salt-okur; yeni alanlar yoksa varsayılanla okunur; migration/revision döngüsü yok (T17) |
| `_migrated` | Değişmedi; callout alanları kimlik karşılaştırmasına girmez |
| `save` (edit) | `_merge_callout_defaults` + `_prepare_callouts` + `_validate_callouts` + `_consume_reconfirm`; callout olayları loglanır; `revision+1`, `build=None` |
| `save` (undo) | History snapshot'ı aynen; global revision artar; `build=None` (STEP diriltilmez) |
| `accept` | Aynı hazırlık/denetim/tüketim kapılarından geçer; callout kararlarını korur; onay üretmez |
| `public` | `callout_schema_version`/`callout_candidates`/`callout_parses`/`callouts` (current/stale/missing + reason) |
| `build` | Akış değişmedi; geç-build yarışı zaten korumalı (T16 ile doğrulandı) |
| `artifact` | Değişmedi; stale/kimlik kapıları eski çıktıyı current sunmaz |

## Kararlar / engeller

- **Sunucu kuralları (düzeltme turu 1 sonrası yürürlükte):**
  - `normalized_text` daima sunucuda (`raw_text` birebir). Transcription `revision` = yazıldığı/değiştiği save'in `revision+1`'i; taşınan kayıt eski kimliğini korur.
  - **Taşınan hedef = kalıcı kayıttan byte-korunur**; istemcinin `geometry_key`/`geometry_version`/`profile_id`/`evidence` sürüklenmesi yazılmaz. Yeni/değişen seçim veya **açık `reconfirm` isteği** yeni onaydır: sunucu alanları bu save'in payload bağlamından pinlenir; istek doğrulama gördükten sonra tüketilir (kayıtta daima `false`).
  - Store denetimi (yeni/değişen kayıtlar; taşınan kayıt incelenebilir kalır ve başka düzenlemeyi engellemez): callout bu oturumda/kaynakta; exact parse **tek ve `status='parsed'`** (çelişkili kayıtlar reddedilir); güncel transcription revision'ı; hedef kimlikleri bu save'in profilinde gerçek (`circle`/`circle_group` ∈ `options["circles"]`; `vertex_pair` → `<edge_id>:start|end` veya kanonik `v{index}`, iki **farklı fiziksel** uç, komşuluk şartı yok); açık `count` = benzersiz hedef sayısı.
  - No-op karşılaştırması `_normalized_decisions` (dosya hiç yazılmaz). `callout_schema_version` ile sürümleme; `geometry_version` artmaz. Alan eklenmesi geriye uyumlu olduğundan (varsayılanlı, kayıtta tüketilen) numara artırılmadı; yapısal değişimde artırılır.
  - Log: `transcribe`/`edit_transcription`/`confirm_target` yalnız kullanıcı olayı; parser olayı yazılmaz; freshness hesapları olay değil.
- **Sunucu kuralları (düzeltme turu 2 eki):** vertex hedef doğrulaması **etkin konturda** yapılır (seçili profil + bu save'in `contour` düzeltmesi; `correct_profile` build ile aynı parametrelerle, çalışma kopyasında — `record.options`/temel kenarlar yerinde değişmez). `v{index}` kayıtlı bağlamdaki kenar ucuna çevrilir ve yeni onay **kararlı kimlikle saklanır**; düzeltmede kaybolan uç açık ret (`yeniden seçin`), sessiz yeniden bağlama yok; fiziksel eşitlik koordinat + `RASTER_JOIN_TOLERANCE_PX` ile denetlenir. `confirm_target` olayı yalnız gerçek onayda yazılır (yeni seçim, onay bağlamı/bağı değişimi veya açık `reconfirm`); taşınan onay ve istemci sürüklenmesi olay üretmez; değişmeyen bağlamdaki `reconfirm` no-op kalır (testle belgelendi). Yalnız-kontur-düzeltmesi kaydı ve eski stale hedefin taşınması engellenmez.
- **`source_unavailable` semantiği:** kaynak değişmiş/okunamaz (geometry_stale) ise parse kaydı "current veri" olarak sunulmaz (PLAN-20 §7 satırı) — transcription tarihsel kalır, target stale, build `historical`, current indirme yok.
- **Bulunan/düzeltilen hatalar:** (a) fixture sınıfı: `_fake_build` `revision: 0` sabitliyordu → `record["revision"]`; (b) ürün, dar: `_prepare_callouts` pin anahtarı bu save'in bağlamından; (c) düzeltme turu 1 içi: `reconfirm` bayrağının erken tüketilmesi doğrulamayı atlatıyordu (`DID NOT RAISE`) → `_consume_reconfirm` doğrulamadan sonraya alındı.
- Test fixture'larındaki parse/target hazırlık verisidir; ürün parser/önerici kanıtı sayılmaz. G1'de gerçek parser yok; `CALLOUT_PARSER_VERSION="callout-parser/1"` G4'e açık parametre; public'te `missing/needs_parse` görünür; log'a parse olayı yazılmaz.
- Baseline ve tüm kümeler yeşil; skip/xfail ile kapı geçilmedi. `rg` host'ta yok; aramalar daraltılmış yolla yapıldı. Pydantic bool→int lax modu nedeniyle bool guard'lar açık.

## Yeniden başlarken ilk somut işlem

- G2 teslim edildi: kabul kanıtı yukarıda (G2.0–G2.6 tablosu + G2 final kanıt bölümü; birleşik **242 passed / 130.66 s / EXIT=0**, full pytest **1479 passed / 1 failed** — tek kırmızı G2 dışı ve önceden mevcut `test_planner` pini). **G3+ kapalı.** Kullanıcı G3'ü açarsa: kök `PLAN.md` §70 ve `docs/PLAN-20.md` §11.1'i oku; kapsam overlay / candidate select / crop preview / user raw transcription / ignore / manual region / persistence+undo — **G3 semantik parser DEĞİL**; girdi: G1'in dört callout modeli + G2 `callout_candidates` base state (kimlik/bölge/provenance/ipucu hazır).
