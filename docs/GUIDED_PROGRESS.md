# Guided progress

- Scope: G0 + G1 (düzeltme turu 1 ve 2 dahil) + G2 (tamamlandı) + G3 + G1R3-01 (PLAN-21, tamamlandı) + **G3R-01–04 kayıt sınırı düzeltmeleri (kök `PLAN.md`, tamamlandı)**
- Active plan: kök `PLAN.md` = **PLAN-25-G12-CONTINUATION** (byte kopya `docs/PLAN-25-G12-CONTINUATION.md`, sha256 `02c924c9…`; kullanıcı girdisi `PLAN-21.md`) + `docs/PLAN-24-G12-CORRECTNESS.md` (sha256 `2535e1e6…`, donmuş tarih: G12.0–G12.2 orada planlandı)
- Önceki kök arşivler: `docs/PLAN_ROOT_BEFORE_G3_REVIEW_20261006.md` `09e18c82…` ve `docs/PLAN_ROOT_BEFORE_G3_ACCEPTANCE_REVIEW_20261006.md` `5743bb06…` (= bugünkü `docs/PLAN-22.md`; dikkat: `docs/PLAN-21.md` de `09e18c82…` = PLAN-18 kopyasıdır, bugünkü `PLAN-21.md` girdisiyle karıştırılmamalı)
- Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`
- G2 initial HEAD: `316518eb8d67c7a4ad81eed59c09e6c59ef4df37`
- G3 initial HEAD: `ff97295065260ba8d46bf6fcd2c6e864e63dfcef` (`ff97295` = G2)
- G3R initial HEAD: `2cdb4d0424b17e4299d625066c24e6a0eab4de6d` (`2cdb4d0` = G3 + G1R3-01 kabul commit'i; eski “G3 commit edilmedi” ifadesi artık geçerli değil)
- Current HEAD: `0c1b721` (**G12R** — bağımsız inceleme düzeltme turu: beş bulgu düzeltildi, taze Plate 11/11 + gerçek Chrome 11/11); öncesi `190a065` (G12.2 kapanışı).
- **G12.3 tamamlandı (commit bekliyor):** view-scoped geometry foundation (PLAN-25 §45–§54) — adaylar oturumla bir kez yazılır, geometri sahibi `view_id` taşır, roller kullanıcının (sunucu damgalı), `GEOMETRY_VERSION 4`, `geometry_key` sahiplik+rolleri içerir, `view_scope_conflict` kapısı + görünüş paneli/menü kapsamı. Kanıt: `eval/audits/20261008-g12-3-view-scope/` (gerçek Chrome 7/7, ilgili süit 628 passed, Plate kabulü v4 altında 11/11).
- **G12.4 tamamlandı (commit bekliyor):** exact supported 2D constraints (§55–§60) — koordinat başına köken kaydı (§57), dimension/trace denetimi (§59), P4 sentetik STEP kabulü 5/5 (§60). Kanıt: `eval/audits/20261008-g12-4-constraints/` (ilgili süit 678 passed, Plate 11/11). Sıradaki: G12.5 (§61–§64).
- Active plan (güncel): `PLAN-24-G12-CORRECTNESS` (kök `PLAN.md`, commit `5605cb5`) + devam planı `PLAN-25-G12-CONTINUATION` (kullanıcı girdisi `PLAN-21.md`: G12.1b → dondurulmuş manifest kabulü)
- G11 baseline: **1/9** (`plate-pocket-vector`; payda sabit — PLAN-24 §75) — bu bir ölçümdür, kabul değil
- Current task: **G12R tamamlandı** — bağımsız incelemenin (`eval/audits/20261007-guided-g12-2-independent-review`) beş bulgusu düzeltildi (R-01 değer bazlı strateji eşitliği; R-02 sunucu pinli kapsam onayı + `stale_scope_claim` + şema 5; R-03 yazılı karar listeli kabul betiği; R-04 kaynak-only varsayılan sürücü + G11 reddi; R-05 reçete alan denetimi + strateji alanı uçtan uca). Kanıt: `eval/audits/20261007-g12r-strategy-plate/` — taze Plate **11/11**, gerçek Chrome **11/11**, ilgili süit + geniş regresyon log'ları
- Sıradaki iş: **G12.3** — view-scoped geometry foundation (PLAN-25 §45–§54): görünüş adaylarının BİR KEZ kalıcı yazılması (§46) + "görünüş" ve "geometri" kavramlarının ayrılması (§47) + geometriyi görünüşe atama (§48) + `GEOMETRY_VERSION 3→4` ve `geometry_key` güncellemesi (§49/§50); RED testleri §53, gerçek Chrome §54
- Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)
- (tarihsel) G12.1b kapanışındaki durum: sıradaki iş G12.2 idi — `c59f814`; G12.2 artık `190a065` ile kapandı.

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

## PLAN-22-G3R — kök `PLAN.md` düzeltme turu (aktif görev)

Başlangıç: HEAD `2cdb4d0`; worktree ` M PLAN.md` (bu turun planı; kök plan baytı `docs/PLAN_ROOT_BEFORE_G3_ACCEPTANCE_REVIEW_20261006.md` sha256 `5743bb06…`), `?? PLAN-17-HERMES.md`, `?? eval/audits/20261006-guided-g3-independent-review/`, `?? eval/audits/20261006-guided-g3r-fix-review/`. Çalışan G3 arayüzü ve store komutları baştan yazılmadı; dört bulgu için dar düzeltme yapıldı.
Ortam: uygulama `PYTHONPATH=src .venv/bin/python -m drawingto3d.app` (gerçek 8765); tarayıcı gerçek Chrome + CDP 9222 (`~/.hermes/cache/scratch/cdp-venv/bin/python`, `cdp_client.py` G3 turundan yeniden kullanıldı). Hermes'in tarayıcı aracı bu makinede Chromium bulamadığı için kullanılmadı; güvenlik ayarı değiştirilmedi. Model çağrısı **0**.

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G3R-01 | PASS | `/save` artık komut kurallarını atlayamıyor: ortak `_commit` yolu, satır sahipliği (manual/review/text), etkin callout görünümü + kaynak/page/ignored/bölge denetimi. 5 store + 1 HTTP regresyonu düzeltme öncesi kırmızı (`g3r-red.log` 15 failed), sonrası yeşil; probe `probe-results-after.json` 7/7 + `http-probe-after.json` 1/1 exit 0 | — |
| G3R-02 | PASS | Yeni hedef onayı freshness'i kaydın **bırakacağı** etkin kararlardan hesaplanıyor (`callout_models.callout_state(record, id, decisions=payload)`): region_changed/ignored/stale parse → ret; taşınan hedef etkilenmiyor. 3 store + 1 HTTP regresyonu; probe `new_confirmation_requires_current_transcription_and_parse` | — |
| G3R-03 | PASS | Şema damgası yalnız gerçek diske yazımda ve yalnız ileri: v1/versiyonsuz kayıt ilk gerçek yazımda 2 olur, okuma/no-op baytı değiştirmez, undo geri düşürmez, gelecekteki bilinmeyen sürüm korunur. 4 regresyon; probe `v1_session_real_g3_write_stamps_current_schema` | — |
| G3R-04 | PASS | `public()` `callout_detection` sunuyor (eski kayıtta `null`); UI boş listeyi nedeniyle açıklıyor (no_text_observations / invalid_frame / unsupported_page / source_digest_mismatch / bilinmeyen kod birebir), aday varsa yalnız uyarı. 1 store + 1 yapısal HTML regresyonu; probe `public_preserves_detection_metadata`; tarayıcı senaryo 5 (3 durum + yazımsızlık kanıtı) | — |
| Doğrulama + teslim | PASS | Dört probe exit 0; birleşik pytest (19 dosya) **304 passed / 133.47 s / EXIT=0**; gerçek tarayıcı **30/30 adım PASS / EXIT=0** (16 screenshot, `browser-steps.json`, 1 beklenen 400; belgelenen komutla 18:51'de yeniden koşuldu); `git diff --check` temiz | commit `a187bf3` + push (`2cdb4d0..a187bf3`) |

### G3R-01 — eski `/save` yeni kuralları atlamasın

**Tekrar (düzeltme öncesi, aynen bağımsız probla):** `/save` `manual_callouts`/`callout_reviews` satırlarını bağlam denetimi olmadan yazıyordu — istemcinin seçtiği `manual:000…` kimliği, başka source digest, `page_index=7`, `revision=999` kabul; `unknown-callout` için review/ignore; ignored callout'a yeni metin (`/callout` 400 verirken); etkin bölgeden farklı `source_region` snapshot'ı.
**Düzeltme:** tek kalıcılık yolu `GuidedStore._commit` (public `save` ve `edit_callout` aynı yol); `save()` artık `events` kabul etmiyor; `_validate_callouts(record, decisions, produced=None)`; yeni manual/review satırı yalnız kendi komutunun ürettiği satır olabilir (`produced`, HTTP'den okunmaz, `trusted/internal/skip_validation` yok); transcription satırı (callout, etkin bölge, metin) eşleşmesiyle taşınır — taşınan satır yeniden damgalanmaz; yeni metin kaydı ignored/yanlış sayfa/yanlış bölgede ret; hedef onayı freshness'i `callout_models.callout_state(record, id, decisions=payload)` ile işlem sonrası görünümden; `_log_callout_changes(..., produced=...)` aynı eylemi iki kez loglamaz (transcribe olayı komuttan gelir); `_set_review`/`_clear_review` gerçek restore olarak kayda geçer; `_apply_callout_command` `(events, produced)` döner.
**Dosyalar:** `src/drawingto3d/guided.py` (`_commit`, `save`, `edit_callout`, `_validate_callouts`, `_transcription_carried`/`_target_carried`/`_same_stored_decision`, `_log_callout_changes`, `_apply_callout_command`), `src/drawingto3d/callout_models.py` (`callout_state`).
**Regresyonlar:** `test_a_public_save_cannot_create_or_change_a_manual_region`, `test_a_public_save_cannot_set_a_review_decision`, `test_clearing_the_review_list_is_a_real_restore_not_a_silent_edit`, `test_a_public_save_cannot_write_text_to_an_ignored_callout`, `test_a_public_save_checks_the_text_region_against_the_effective_region` (store) + yeni `tests/test_guided_callout_http.py::test_http_save_cannot_bypass_the_callout_rules` (gerçek HTTP: hem `/callout` hem `/save` 400 + bayt değişimi yok); koruma testleri `test_an_unrelated_full_save_carries_every_g3_row_verbatim`, `test_the_full_review_flow_still_works_end_to_end`.
**Komut/kanıt:** `.venv/bin/python -m pytest -q tests/test_guided_callout_review.py tests/test_guided_callout_http.py` → EXIT 1 (kırmızı, 15 failed) → düzeltmeden sonra EXIT 0; `out/guided-g3r/g3r-red.log`, `out/guided-g3r/g3r-combined.log`; probe: `PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/review_probes.py` EXIT 0 (7/7) — `probe-results-after.json`; `.../http_review_probes.py` EXIT 0 — `http-probe-after.json`.

### G3R-02 — yeni hedef onayında freshness

**Tekrar:** `edit_region` ile taşınan bölgeden sonra public state `region_changed`/stale dese de eski transcription/parse bağıyla yeni circle hedefi `confirmed` kaydedilebiliyordu.
**Düzeltme:** onay denetimi kaydın bırakacağı etkin kararlar üzerinden (yukarıdaki `callout_state` çağrısı); ret nedenleri: kaynak yok, ignored, transcription current değil, parse current/`parsed` değil; taşınan hedef bayt-korunur; ilgisiz kalınlık/profil kaydı bloke olmaz.
**Regresyonlar:** `test_a_new_confirmation_after_a_region_move_needs_a_current_text_and_parse`, `test_a_region_move_and_a_target_confirmation_in_one_save_cannot_skip_freshness`, `test_an_ignored_callout_cannot_be_confirmed_and_a_carried_target_is_untouched` + `tests/test_guided_callout_http.py::test_http_save_cannot_confirm_a_target_on_a_stale_region`; koruma (guard) testi: `test_a_carried_stale_target_survives_an_unrelated_full_save` (aynı sözleşme HEAD'de de yeşildi — §5 “ilgisiz kayıt stale target'ı yeniden onaylamaz/bloke etmez” maddesini kilitler).
**Komut/kanıt:** aynı kırmızı→yeşil koşu (`g3r-red.log`, `g3r-combined.log`); probe satırı `new_confirmation_requires_current_transcription_and_parse` (`probe-results-before.json` `passed=false` → `probe-results-after.json` `passed=true`). Gerçek parser yazılmadı; fixture'lar parse verisi olarak kalır.

### G3R-03 — v1→v2 şema damgası

**Tekrar:** `_stamp_callout_version` kayıt zaten sürüm taşıyorsa hemen dönüyordu → `callout_schema_version=1` oturumuna `add_region` ile yazılan G3 kararı sürümü 1 bırakıyordu.
**Düzeltme:** damga yalnız gerçek yazım yolunda; `version >= CALLOUT_SCHEMA_VERSION` ise dokunulmaz (gelecekteki bilinmeyen sürüm 2'ye düşürülmez); load/public/no-op baytı değiştirmez; damga ayrı revision/history/log üretmez.
**Regresyonlar:** `test_a_v1_session_is_stamped_by_its_first_real_write_and_reads_stay_read_only`, `test_a_versionless_legacy_session_is_stamped_on_a_real_write_only`, `test_a_future_unknown_schema_version_is_never_downgraded` (HEAD'de de yeşil: koruma), `test_undo_never_lowers_the_callout_schema_version`.
**Komut/kanıt:** `g3r-red.log` (3'ü kırmızı) → `g3r-combined.log` EXIT 0; probe satırı `v1_session_real_g3_write_stamps_current_schema`.

### G3R-04 — detection sonucu ve nedenleri public/UI'da

**Tekrar:** `create()` diagnostics'i kaydediyor ama `public()` alanı döndürmüyordu; UI her boş listeyi “metinsiz çizim normal bir sonuçtur” diye açıklıyordu (`source_digest_mismatch`/`invalid_frame` böyle anlaşılamaz).
**Düzeltme:** `public()` `callout_detection` (`{"detector_version","diagnostics"}`; eski kayıtta `null` — sahte başarı yok). `guided.html`'e `#callout-detection` satırı; `guided.js` `DETECTION_REASON` eşlemesi + `detectionReasons()`/`detectionNotice()`: aday yok + neden varsa “Aday üretilemedi: <neden>”, yalnız `no_text_observations` ise “metinsiz çizim normal bir sonuçtur”, metadata hiç yoksa “eski kayıtta tespit bilgisi yok”, bilinmeyen kod birebir; aday varsa yalnız “Uyarı: bazı gözlemler adaya çevrilemedi”. Diagnostics göstermek karar/revision/log üretmez; normal boş çizimde manuel alan çizimi çalışır.
**Regresyonlar:** `test_the_public_state_serves_the_detection_metadata_and_admits_its_absence` (store) + `tests/test_guided_html.py::test_the_empty_callout_list_gives_the_detectors_own_reason` (yapısal) + tarayıcı senaryo 5 (gerçek metinsiz PNG; `source_digest_mismatch` fixture'ı; metadata'sız fixture; üçünde de baytlar değişmedi).
**Komut/kanıt:** `g3r-red.log` (ikisi kırmızı) → `g3r-combined.log` EXIT 0; probe satırı `public_preserves_detection_metadata`; `eval/audits/20261006-guided-g3r-fix-review/browser-acceptance.log` adım “scenario 5 …” + `g3r-13/14/15-*.png`.

### G3R kabul matrisi (PLAN.md §4–§7)

| Madde | Kanıt |
|---|---|
| G3R-01 dört probe kabulü | `probe-results-after.json`: `save_cannot_create_client_owned_manual_identity`, `save_rejects_unknown_review_reference`, `save_cannot_transcribe_ignored_callout`, `save_validates_or_derives_new_transcription_region` — hepsi `passed=true` |
| G3R-01 gerçek HTTP: ignored metin hem `/callout` hem `/save` 400 + bayt değişimi yok | `http-probe-after.json` (`command_status`/`save_status` 400, `command_unchanged`/`save_unchanged` true, `saved_callout` null) + `test_http_save_cannot_bypass_the_callout_rules` |
| G3R-01 akış: add_region → transcribe → edit_region → yeniden kaydet → ignore → restore → undo | Tarayıcı senaryo 2+3 (adım 9–17), `test_the_full_review_flow_still_works_end_to_end` |
| G3R-01 eksik anahtar korur / `[]` temizler / ilgisiz full-save satırları aynen taşır | G1 testleri (`test_missing_keys_keep_callout_decisions_and_explicit_empty_removes_them`) + `test_an_unrelated_full_save_carries_every_g3_row_verbatim` + tarayıcı senaryo 3 kalınlık adımı (`callout_rows_equal: true`) |
| G3R-01 her gerçek eylem = 1 history/revision; aynı karar no-op; reddedilen istek audit yazmaz | G1 no-op/history testleri + `test_a_public_save_*` retlerinde `bytes_of(store)` sabit |
| G3R-02 stale hedef ret; dosya/log/history aynı | `test_a_new_confirmation_after_a_region_move_needs_a_current_text_and_parse` (+ HTTP karşılığı) |
| G3R-02 nedenler: region_changed/ignored/transcription/parse | Yukarıdaki testler + G1 T06/T21 stale-parse testleri; onay `status=parsed` şartı korunuyor |
| G3R-02 aynen taşınan stale hedef + ilgisiz kayıt çalışır | `test_an_ignored_callout_cannot_be_confirmed_and_a_carried_target_is_untouched` (taşınan hedef bayt aynı) |
| G3R-02 önceki 2/2 ve 5/5 scriptleri | `eval/audits/20261006-guided-g1-review/probe-results-g3r-after.json` (`passed: true`), `eval/audits/20261006-guided-g2-review/probe-results-g3r-after.json` (5/5) — ikisi de exit 0 |
| G3R-03 v1/v2, read/no-op, gerçek write, undo | Dört G3R-03 regresyonu + probe `v1_session_real_g3_write_stamps_current_schema` |
| G3R-04 public diagnostics + boş/eski/hatalı detector UI | `test_the_public_state_serves_the_detection_metadata_and_admits_its_absence`, `test_the_empty_callout_list_gives_the_detectors_own_reason`, tarayıcı senaryo 5 (3 durum) |
| G3R-04 diagnostics karar/revision/log üretmez; manuel alan çalışır | Tarayıcı senaryo 5 “merely showing … writes nothing” (bayt karşılaştırması) + “drawing a manual region still works on an empty drawing” |
| Uygulama sırası §8 satırları | RED→düzeltme→yeşil sırası: `g3r-red.log` (15 failed) → `g3r-combined.log` (303 passed, EXIT 0); her satırın komutu/exit kodu yukarıda |

## Son doğrulamalar

- **G3R düzeltme turu (bu tur):** dört bağımsız probe **exit 0** — `eval/audits/20261006-guided-g3-independent-review/probe-results-after.json` (7/7), `.../http-probe-after.json` (1/1), `eval/audits/20261006-guided-g1-review/probe-results-g3r-after.json` (2/2), `eval/audits/20261006-guided-g2-review/probe-results-g3r-after.json` (5/5)
- **G3R kırmızı kanıt:** düzeltme öncesi HEAD kodu + yeni testler → **15 failed / 44 passed / EXIT 1** (`out/guided-g3r/g3r-red.log`); dosya listesi bu dosyada G3R bölümünde
- **G3R birleşik:** 19 dosya → **304 passed / 133.47 s / EXIT=0** (`out/guided-g3r/g3r-combined.log`; G3 baseline 285 + 19 yeni test: review +16 [12 kırmızı + 4 koruma], yeni HTTP dosyası +2, HTML +1); `git diff --check` temiz
- **G3R tarayıcı:** gerçek Chrome **30/30 adım PASS / EXIT=0**, 16 screenshot, tek beklenen `POST /api/guided/callout` 400 — `eval/audits/20261006-guided-g3r-fix-review/browser-acceptance.log` + `browser-steps.json`; docstring'deki eski komut (cdp-venv tek başına, numpy yok) düzeltildikten sonra **belgelenen birleşik komutla yeniden koşuldu** (18:51, 30/30 exit 0); konsol/ağ adımları tarayıcının kendi `/favicon.ico` isteğini açıkça muaf tutar (`browser_automatic_ignored`, son koşuda boş), başka her hata koşuyu düşürür
- **G3R tam takım:** bu turda koşulmadı. Bilinen ilgisiz kırmızı açık: `tests/test_planner.py::test_settings_record_is_the_run_record_fields` (önceden mevcut, bu turda ele alınmadı)

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

- **G3R düzeltme turu teslim edildi** (kök `PLAN.md` uygulaması): G3R-01–04 düzeltmeleri + 19 yeni regresyon + dört bağımsız probe (7/7, 1/1, 2/2, 5/5) + gerçek tarayıcı 30/30 PASS; birleşik pytest **304 passed / 133.47 s / EXIT=0**; **commit `a187bf3`** (`2cdb4d0..a187bf3`, origin/main). Çalışan G3 baştan yazılmadı.
- **Açık kalanlar:** (1) tam takım bu turda koşulmadı; (2) önceden mevcut `test_planner::test_settings_record_is_the_run_record_fields` kırmızısı; (3) **G4 (deterministik parser + parse onayı) ve sonrası açılmadı** — bu görevde uygulanması istenmiyor; (4) G4/G7 yokken callout metninin STEP'e uygulandığı iddia edilmez.
- Kullanıcı G4'ü açarsa: kök `PLAN.md` §10 sonundaki yönlendirme + `docs/PLAN-20.md`; parser/parse onayı/target önericisi kapsamı. G3R teslim kanıtları: `docs/GUIDED_PROGRESS.md` (bu bölüm) + `eval/audits/20261006-guided-g3r-fix-review/DELIVERY.md`.
- Önceki turlar: G2 teslimi yukarıdaki G2 bölümünde (birleşik **242 passed / 130.66 s / EXIT=0**, full pytest **1479 passed / 1 failed** — tek kırmızı G2 dışı `test_planner` pini); G3 + G1R3-01 `2cdb4d0` commit'iyle kapandı (G3 turu: birleşik 285 passed, tarayıcı **28/28**).

## G4/G5/GX/G7/G8 — callout okuma → hedef → karar zinciri (kök `PLAN.md` §7–§14)

Uygulanan kapsam (bu turda): **G4** deterministik parser + store türetmesi, **G5** deterministik hedef
önerisi, **GX** inceleme dışa/içe aktarma doğrulaması, **G7** onaylı callout → mevcut karar derleyicisi,
**G8** build hazırlığı + callout başına denetim zinciri. **G6 (tarayıcı UX), G9–G13 açılmadı.**

- **G4** `src/drawingto3d/callout_parse.py`: saf, deterministik `parse_callout` / `semantic_parse`
  (`TranscriptionDecision.raw_text → CalloutReading`); dosya/ağ/model/OCR/referans yok; no-guess
  (`unsupported_syntax`, `ambiguous_number`, `conflicting_symbols`, `unit_unresolved`, `unit_differs_from_sheet`).
  Pozitif matris (PLAN §8) ve negatif matris testli: `tests/test_callout_parse.py`.
  **Store türetmesi:** `guided._refresh_callout_parses` — kaydedilen her metin için gerçek parser'ın *tek*
  okuması, bağlı olduğu transcription revizyonu + `CALLOUT_PARSER_VERSION` ile; güncel satır yeniden
  yazılmaz (byte no-op), eskiyen satır yenilenir, alanı taşınan metin eskiyerek kalır (okuma uydurulmaz),
  eski kayıtta anahtar yoksa yok kalmır. Okuma bir kullanıcı olayı değil: geçmiş adımı ve log satırı yok;
  `/save` istemciden okuma kabul etmez. `tests/test_guided_callout_parse.py` (15 test).
- **G5** `src/drawingto3d/callout_bind.py`: `TargetProposal` + T0–T5 kanıt sırası (mevcut onay, ipucu
  çizgisi, basılı ölçü, biçim/ölçü uyumu, adet, yakınlık); deterministik sıralama; adet geometri uydurmaz;
  ölçüsü tutmayan aday `size_mismatch` ile dürüstçe T5'te kalır; birim metinde yoksa sayfanın beyan edilen
  birimi (kalibrasyon) çözer ve kaynağı yazılır, o da yoksa karşılaştırma yapılmaz. `tests/test_callout_bind.py`.
- **GX** `src/drawingto3d/callout_review.py`: `export_bundle` (PLAN §12 asgari alanlar + öneriler/onay/tazelik)
  ve `validate_import` — oturum/kaynak özeti/`base_revision`/şema/callout/geometri doğrulaması, kartellik,
  bölge sınırları, metin sınırı, kanıt biçimi, **all-or-nothing** ve kaydı hiç değiştirmeme. `tests/test_callout_review.py`.
- **G7** `src/drawingto3d/callout_compile.py`: PLAN §13 örnekleri birebir (Ø8 THRU+onaylı daire → through
  delik; 4×Ø8 THRU → 4 karar; düz ölçü + iki uç → mevcut `Binding`, eksen/yön onaylanan uçlardan);
  THRU/BLIND yoksa delik *değil*, kör derinlik yoksa uydurulmaz, R yay → açık `unsupported_cad_feature`,
  kullanıcının kendi kararı asla ezilmez, `apply_compiled` yalnız ekler. `tests/test_callout_compile.py`.
- **G8** `src/drawingto3d/callout_readiness.py`: PLAN §14 kategorileri + callout başına zincir
  (callout → metin → parser sürümü → semantik → hedef → geometri anahtarı → derlenen karar → üretilen özellik).
  Kapsam dışı bırakılan callout engel değil, **beyan edilmiş dışlama**.
- **Sözleşme (v3):** `CalloutTargetDecision.target_kind` artık `arc`/`profile` de kabul eder (PLAN §10/§11
  modları için zorunlu; üç eski tür aynen geçerli); `CalloutReviewDecision.unbindable` ("bağlanamaz"
  kullanıcı kararı — sessiz eksik yerine beyan); `TranscriptionDecision.entered_by` `external_review`
  (GX kaynağı satırda). Birim çözümü `callout_models.sheet_unit()`.
- **Kanıt:** birleşik callout kümesi **311 passed / 63.5 s / EXIT=0**
  (`test_callout_models`, `test_callout_parse`, `test_guided_callout_parse`, `test_callout_bind`,
  `test_callout_compile`, `test_callout_review`, `test_guided_callouts`, `test_guided_callout_review`,
  `test_guided_callout_candidates`, `test_guided_callout_http`). Parser/preview katmanı gerçek fonksiyon
  çağrılarıyla; hiçbir kapı skip/xfail ile geçilmedi.
- **G4 nedeniyle değişen tarihsel pinler (bilinçli, gerekçeli):** metin düzenlenince okuma artık *yenilenir*
  (PLAN §9 "Transcription değişirse parse stale" eski satırın kaderidir; yeni revizyonun okuması hemen
  türetilir, hedef ise eskiyerek kalır) — `test_editing_the_text_replaces_the_stored_reading_and_keeps_history`,
  `test_saving_the_text_again_on_the_new_region_is_a_new_user_decision` ve
  `test_the_base_candidates_and_the_reading_never_move_from_a_review` bu gerçeği pinler; şema pini 3.
- **Açık kalanlar:** G6 tarayıcı kabulü (onay paneli/öneri vurgusu/elle yeniden seçim), G7/G8'in build'e
  bağlanması (`_commit`/`build` yolunda derleme + readiness kapısı), `/api/guided/propose|export|import`
  uçları, guided.js/guided.html, G9 Plate golden path, G10 manifest, G11–G13 koşu + raporlar.
  G4/G7 yokken callout metninin STEP'e uygulandığı iddia edilmez.


## G6/GX/G7/G8 — uçbirim yüzeyi, üretim kapısı, aktarım (tur 2)

Aynı fazın *bağlanma* turu: katmanlar saf kaldı, ama artık mağaza ve HTTP üzerinden erişilebilir.

- **G5 okuması**: `GuidedStore.propose(token, callout_id)` + `POST /api/guided/propose` — yalnız okur
  (revizyon ve oturum dosyası bayt bayt aynı kalır), önerileri kanıt katmanına göre sıralı döner,
  ölçeği kullanıcının kalibrasyonundan alır (`note_sketch`), hiçbir onay yazmaz.
- **G8 hazırlık**: `GuidedStore.readiness(token)` + `POST /api/guided/readiness` — kaydın kendi
  `questions()`i otorite olarak kalır; `_sheet_issues()` aynı koşulları makine kategorilerine çevirir
  (profil, kalibrasyon, kalınlık, iz onayı, bağ ekseni, görüş) ve callout katmanının kategorileriyle
  birleşir. Sorular `action` alanıyla panelin hangi düğmesi olduğunu söyler.
- **Üretim kapısı** (`PLAN.md` §14 "Build only when all relevant inputs current/resolved"):
  `build()` artık hazırlık geçmeden ve derleme çelişkisi varken *hiç başlamaz* — ne `build-*` klasörü
  açar ne `build` durumu yazar; durdurma gerekçesi callout kimliğiyle birlikte hatada görünür.
  Derleme sonucu (`compiled_summary`) üretim log'una `callout_compile` alanıyla geçer (denetim izi).
- **G6 kapsam kararı**: yeni komut `set_unbindable` ("bağlanamaz") — kullanıcı kararı olarak
  `callout_reviews`'a yazılır, log'da `unbindable_callout` olarak görünür, `ignored` ile birbirini
  dışlar ve bekleyen callout'u kapatır (sessiz düşürme değil, bildirilmiş kapsam kararı).
- **GX aktarımı**: `GuidedStore.review_export` / `review_import` + `POST /api/guided/export|import`.
  İçe aktarma *güvenilmeyen girdidir*: paket bu kayda karşı doğrulanır (sürüm/şema/oturum/kaynak/
  base_revision/eylem/kimlik/geometri), ya tümü uygulanır ya hiçbiri; uygulanan her satır aynı
  `_commit` yolundan geçer (kilit, revizyon, geçmiş, undo), metinler `entered_by="external_review"`
  damgası ve `actor="external_review"` log'u taşır — dış inceleme kullanıcı gibi görünmez.

Kanıt: `tests/test_guided_callout_chain.py` (19 test) — okuma-önermesi kaydı değiştirmiyor,
hazırlık kategorileri, "bağlanamaz" kararının üretimi açması, çelişkide üretimin durması (üretici
çağrılmadan), derlemenin plana geçmesi ve log'a düşmesi, paket/aktarım turu, geri alma, kurcalanmış
paketin revizyonu değiştirmemesi, iki yeni uç noktanın gerçek HTTP'de yanıtı. Hedefli set:
`tests/test_guided_*.py tests/test_callout*.py tests/test_planner.py` → **455 passed** (98 s).
G8 kapısı iki eski beklentiyi bilinçli olarak değiştirdi: `geometry_state` testindeki pafta callout'ları
artık kapsam dışı ilan ediliyor, geç-biten-üretim testindeki callout "bağlanamaz" işaretleniyor.

Açık: G6 paneli (static/guided.js) ve tarayıcı kabulü; H0 tam baseline koşusu bu turda yarıda
kesildi (yarısında G4+ değişiklikleri geldi) — tam koşu G13'te yeniden alınmalı.


## G6 — hedef onayı UX'i + gerçek tarayıcı kabulü

Panel artık öneriyi gösterir, kullanıcı onaylar ya da kendi seçer; karar `CalloutTargetDecision`
sözleşmesinden geçer ve kanıtı (`proposal` / `user_click`) satırda durur.

- **Panel** (`static/guided.html` + `guided.js`): hedef bölümü — durum (`hedef onaylanmadı/güncel/eskidi`),
  kanıtıyla sıralı öneri listesi (tıklayınca çizimde vurgulanır), `[Onayla]` `[Başka hedef seç]`
  `[Birden fazla hedef seç]` `[Bağlama yok / desteklenmiyor]`, tür seçimi
  (`target-circle` / `target-group` / `target-arc` / `target-endpoints` / `target-profile`).
- **Seçim çizimden gelir**: daire, yay, köşe (`edge:start|end`) ve kontur vuruşu; çoklu seçim birikir,
  `Seçimi onayla` ile yazılır. Eskimiş hedefte onay `reconfirm` olarak yeniden yazılır.
- **Hazırlık panosu**: `readiness` kategorileri cümle olarak listelenir ve **üretim düğmesi** hazır
  değilken kapanır (`PLAN §14`).
- **GX düğmeleri**: `İnceleme paketini indir` gerçek indirme, `Paket içe aktar` gerçek dosya seçimi →
  sunucunun doğrulaması; hata kullanıcıya olduğu gibi söylenir.
- Önerinin/onayın panelde görünmesi için gereken sunucu alanları (`parser_version`,
  `transcription_revision`) `propose` okumasına eklendi — tarayıcı bunları tahmin etmez.

**Kanıt — gerçek tarayıcı** (`eval/audits/20261006-guided-g6-target/`, `DELIVERY.md` + `g6-steps.json`):
`17/17 G6 browser steps passed`, beklenmeyen konsol hatası ve reddedilen istek yok. Adımlar: çizim aç
(45 callout) → callout seç → `Ø8 THRU` yaz → öneri vurgusu (tuval pikselleri değişti) → `[Onayla]`
(`evidence kind=proposal`, `T3`) → yeniden aç (onay kayıttan) → konturu değiştir →
`hedef eskidi (geometry_changed)` + hazırlık kapısı kapandı → elle daire seç → `Seçimi onayla`
(`user_click`, yeni `geometry_key`/`profile_id`) → geri al → yeniden aç → paket indir.

Tam regresyon ağı (semread bloğu hariç tüm testler): `pytest -q tests -k "not semread"` →
**1387 passed, 339 deselected** (26 dk, EXIT=0) — G4–G8/G6 değişiklikleri bu turda yalnız altı
bilinçli beklenti güncellemesiyle geçti, başka kırılma yok.

Regresyon: `pytest -k "guided or callout or app or html or static or observe"` → **471 passed**, ve
G8 kapısının getirdiği iki bilinçli test güncellemesi: `geometry_state` paftası ile `test_guided.py`'nin
flange testi callout'ları kapsam dışı ilan ediyor; `test_guided_html.py` artık panelin *doğru*
cümlesini pinliyor (metin kullanılmıyor değil — derleniyor ve kapıyı besliyor).


## Bağımsız inceleme düzeltmesi — R01–R05

`eval/audits/20261006-guided-g4-g8-independent-review/REVIEW.md` beş bulgu getirdi; düzeltme turu
test-önce yürütüldü — her bulgu için önce kırmızı doğrulanan regresyon, sonra ürün düzeltmesi.

- **R01 — dikey ölçüde yön ters**: derleme artık ekseni/yönü paftanın kendi çerçevesinden okur
  (`guided.view_transform` ile aynı çözücü; `callout_compile._view_axes` / `_axis_tie`); görüş
  vouchable değilse `view_not_confirmed` açık kararı (hazırlıkta `missing_view` / `confirm_view`).
  Sayfa deltasından işaret okuma dönemi kapandı.
- **R02 — inç kör derinlik**: derinlik, çapla aynı çözülmüş birimden çevrilir (`0.25 in` → `6.35 mm`);
  çevrilmiş değer `Hole` sınırına (1e6 mm) karşı derleme zamanında denetlenir (`unsupported_semantic`,
  `*_out_of_range`) — model doğrulama hatasına bırakılmaz.
- **R03 — `[Onayla]` vurgulananı yazmıyordu**: `guided.js` tek aktif öneri state'i — etiket tıklaması
  vurguyu kurar, `[Onayla]` vurgulananı yazar ve düğme etiketi hangisini yazacağını söyler
  (`Onayla · N. öneri`); listeyle eşleşmeyen bayat vurgu temizlenir.
- **R04 — parse hatası eksik hedef gibiydi**: okuma, hedef kararından önce ve sunucunun kendi parser
  sürümünden seçilir (`CALLOUT_PARSER_VERSION`); desteklenmeyen/ambiguous metin `parse_error` sorusu
  olur — kullanıcı çıkmaz sokağa gönderilmez (onayı store zaten reddediyordu).
- **R05 — eski paket değişen geometriye onay yazabiliyordu**: dışa aktarmaya `geometry_key` eklendi;
  içe aktarma parser sürümü + `geometry_version` + `geometry_key` bağlam kapılarından geçer — revision
  eşit olsa da bağlam eskimişse paket tamamıyla reddedilir (yazma yok).

**Kanıt** (`eval/audits/20261006-guided-g4-g8-independent-review/`): RED önce — 20 yeni regresyon
kırmızı (`fix-regressions-red.log`), tarayıcıda vurgulanan c1 iken c0 yazılıyordu (`ui-fix-red.log`,
4/7). GREEN sonra — yeni regresyon seti **141 passed** (`fix-regressions-green.log`), incelemecinin
odak seti **410 passed** (`fix-focused-after.log`), geniş set **186 passed** (`fix-extended-after.log`),
inceleme probu **6/6** + import probu **3/3** exit 0 (`probe-results-after.json`,
`import-probe-results-after.json`), gerçek Chrome **7/7** (`ui-fix-after.log`). Özet: `FIX-REPORT.md`.
`*-before` kanıtlarına dokunulmadı (md5 + mtime kayıtlı).

**Bağımsız doğrulama** (`eval/audits/20261007-guided-fixes-independent-review/`): beş bulgu kapandı,
yeni bulgu yok; 12 test dosyası 412 + 2 (sandbox bind), gerçek HTTP tekrarı 2 → toplam **414 farklı
test**; ek sınır probu **33/33** (dönüş/uç sırası + aynı sürüm geometri); gerçek UI'da kalıcı c1.

Açık: geniş semread regresyon ağı ve gerçek CAD/STEP üretimi bu düzeltme turunda koşulmadı; sıradaki
adım kapsamında alınmalı.

## G9 kabul + G10 manifesti donduruldu — 2026-10-07

**G9 PASS kabul edildi (kullanıcı kararı).** Kanıt: `eval/audits/20261007-guided-g9-plate/DELIVERY.md`
(24/24 gerçek-tarayıcı adımı, `verdict.json` tüm kapılar PASS, `THRU ALL` dilbilgisi düzeltmesi commit
`1a40d86`). G9 kaydı böylece "kabul edildi" olarak kapanır; G10 açılır.

**G10 — sabit 10-pafta manifesti, sonuçlar görülmeden donduruldu:** `eval/guided_10_manifest.json`
(manifest_version 1, `created_at_git_head` = `3b92938345988d9c60f98e0c56aa508cccadba72`). Tam 10 vaka;
her kaynak hash'i dosyadan hesaplandı ve dosyadan geri okunarak doğrulandı. Kapsam sınıfları koşu
öncesi bildirildi (`full_step` / `callout_scope_only`) ve koşu sonrası geriye dönük değiştirilmez.
Referans STEP yolları yalnız evaluator içindir (`reference_identifier_evaluator_only`), üreticiye
kapalıdır. Ön maruziyet dürüst etiketlendi: plate = G9 regresyonu (unseen diye raporlanmaz); kalan
dokuz pafta geliştirmede kullanıldı (`previously_seen`) — bu korpusta "unseen" vaka yok.

**Sıra (kullanıcı yönlendirmesi).** G11 henüz başlatılmadı; önce G9'da gözlenen 45 aday / 43 kapsam
dışı kullanıcı yükünü generic biçimde azaltan dar UX turu yürütülür: next-unresolved akışı, açık
(explicit) toplu ignore, makine ipucu için tek-tık kabul akışı ve hazırlığın eyleme dönük kontrol
listesi. Sessiz başlık-bloğu filtreleme veya vakaya özel kural eklenmez. Browser kabulü ve mevcut
callout regresyonları yeşil olduktan sonra dondurulmuş manifest değiştirilmeden G11'e geçilir.

## G9 UX turu — PASS (2026-10-07)

G9'daki 45 aday / 43 kapsam dışı kullanıcı yükünü generic biçimde azaltan dar tur tamamlandı.
Kabul planı **ilk koşudan önce** donduruldu (`eval/audits/20261007-guided-ux-round/DELIVERY-PLAN.md`,
commit `1192082`); teslim: `eval/audits/20261007-guided-ux-round/DELIVERY.md`.

| Akış | Ürün değişikliği | Kanıt |
|---|---|---|
| next-unresolved | `#callout-next` (kararsızlar arasında sırayla; sayaç etiket + özet) | adım 6 |
| explicit bulk ignore | `set_ignored_many` + iki adımlı `#callout-ignore-many`; kararlı satır dokunulmaz; tek revizyon; satır başına `bulk=true` log | adım 13, 23–27 |
| ipucu tek-tık | `transcribe`+`accept_hint` (sunucu ipucuyla birebir doğrular) + `#callout-hint-save` | adım 16–20 |
| readiness checklist | kategori rozetli + `Git` düğmeli; tıklama sunucunun `action`/`reason`'ına göre odağa gider | adım 3–5 |

Ölçülen yük (aynı plate): kapsam kapatma G9'da 37 tek-satır akışı → burada **1 tek + 1 toplu (36
satır, 2 tık, tek revizyon 21→22)**; elle yazılan metin 7 → **4**; tek tıkla kabul edilen ipucu 0 → **4**;
45 aday / 43 kapsam dışı değişmedi, sessiz düşme yok (adım 2, 28, 32). Hazırlık özeti
`45 callout derlendi · 5 delik · 0 ölçü bağı · 43 kapsam dışı`; STEP `build_status=complete`.

Doğrulama: gerçek Chrome kabulü **33/33 PASS** (`ux-steps.json`, koşu 04; 15 ekran görüntüsü,
`session-public.json`, `review-bundle.json`, `part.step`, `plan.json`, `plan-audit.json`); dondurulmuş
G9 CAD regresyonu aynı STEP üzerinde **tüm kapılar PASS** (`verdict.json`, `logs/cad-regression.log`);
callout/guided regresyon seti **483 passed / 144 s** (`logs/regression-callout.log`); yeni RED→GREEN
testleri `tests/test_guided_callout_ux.py` (17 test) + `tests/test_guided_html.py` yapısal pinleri.

Dürüstlük: koşu 01 ve 02 sürücü tarafında durdu (koşu 01: next-unresolved başlangıç konumu beklentisi
+ public payload'da `history` yok; koşu 02: log satırı taşıma anındaki revizyonu damgalar — tasarım).
Ürün tarafında bulgu yok; loglar `logs/run-01-stopped.log`, `logs/run-02-stopped.log`. G10 manifesti
(`eval/guided_10_manifest.json`) bu turda değişmedi.

**Sıradaki: G11** — dondurulmuş manifest ile ilk 10-pafta koşusu (sürücü + vaka kayıtları + rapor).

## G11 — resmî 10-pafta koşusu **TAMAM: 10/10 kayıtlı** — 2026-10-07

Bu turdaki kayıtlar **pilot** doğrulama kayıtlarıdır (UX-01 öncesi kod; sürücü/akış doğrulaması).
Kullanıcı sırası gereği **resmî G11 koşusu UX-01 PASS'ten sonra** başlar (UX_PLAN §29); resmî koşu 10
paftayı UX-01 sonrası kodla, aynı dondurulmuş manifestle sıfırdan koşar. Yöntem donduruldu (`eval/audits/20261007-guided-g11/DELIVERY-PLAN.md`, ilk vaka koşusundan önce):
taze oturum/vaka, aynı ürün HEAD'i, kararlar yalnız görünen oturum verisi + çizim okumasıyla
(`recipes/<case_id>.json`, denetlenebilir), referans STEP yalnız evaluator'a; tahmin yok — belirsizlik
kayıtta durur. Taksonomi: `DETECT_MISS · DETECT_FALSE_POSITIVE · TRANSCRIPTION · PARSE_UNSUPPORTED ·
PARSE_AMBIGUOUS · BIND_NO_PROPOSAL · BIND_WRONG_PROPOSAL · BIND_STALE · CONSTRAINT_UNSUPPORTED ·
CONSTRAINT_CONFLICT · CAD_UNSUPPORTED · CAD_WRONG · STEP_EXPORT · STEP_REOPEN · EVALUATOR`.

| Vaka | Durum | Kayıt |
|---|---|---|
| plate-pocket-vector | **kayıtlı — PASS** | 45 aday · 8 metin · 37 kapsam dışı · verdict pass (G9 ile aynı bbox) |
| drawing-2-vector | kayıtlı — CAD_WRONG | 66 aday; kesit taraması üst görünüm konturunu böldü; sol gövde (R20) modellendi; ref 50×80×134 |
| plastic-enclosure-vector | kayıtlı — CAD_WRONG (şekil ok) | 65 aday; bbox 0.12 mm içinde ama dolu levha 182.5 cm³ vs içi boş kabuk 23.5 cm³ |
| exercise-12-vector | kayıtlı — CAD_WRONG | 70 aday; rotational okuma (Ø270×20) alt küme kaldı: 1.02 L vs 4.79 L |
| exercise-51-raster | kayıtlı — CAD_WRONG | 26 aday; okuma önerisiz, OCR başlık artığı; ana kontur tespitte parçalı → göbek dairesi (g340) modellendi; kalibrasyon belirsiz (40, g340–g341); göbek 15×28.6×28.6 vs ref 60×100×245; ingest ~20 CPU-dk (istemci koptu, token ile kurtarıldı) |
| exercise-17-raster | kayıtlı — CAD_UNSUPPORTED | 20 aday; okuma önerisiz; kontur parçalı (en büyük tutarlı = outline_2), trace çakışma düzeltmesi tutmadı; üretim isteği sunucuda **400** ile reddedildi, STEP üretilemedi; sürücü kanıt: `cases/exercise-17-raster/` + log (üretim düğmesi beklemesi ve kanıt indirme koruması bu vakada eklendi) |
| exercise-13-raster | kayıtlı — CONSTRAINT_UNSUPPORTED | 32 aday; okuma önerisiz; sürücü dış konturu doğrulayamadı (`missing_profile`: „Ana görünüşte dış konturu seçin“) → build hiç koşmadı; 32 satır tek toplu eylemle kapsam dışı |
| my-part-raster · flange-raster · flange-elbow-90-raster-noref | pilot bekliyor | sonuncusu referanssız: yalnız okuma/kapsam beyanıyla puanlanır; resmî koşuda yeniden |

Altyapı: `g11_runner.py` (vaka sürücüsü; öneri kabul yolu, hint/kapsam akışları UX turunun
yardımcılarını yeniden kullanır), `g11_probe.py` (görünen veri dökümü), `g11_author.py` (kontur izi
doğrulama), `evaluate_case.py` (.venv-cad; reopen + `metrics.compare`), `g11_report.py`
(`eval/guided_10_report.json` + `.md`; `pending` vakalar açıkça listelenir).

Dürüstlük: drawing-2 ilk denemesi sürücü hatasıyla durdu (kutu-tabanlı tıklama düzeltildi;
`logs/case-drawing-2-abort1.log`). Exercise_51 ilk probe'u 300 s oturum beklemesinde zaman aşımına
düştü (raster gözlem + saatlerce açık kalmış uygulama; yeniden başlatma + 900 s). Sürücü verdict
fail'de exit≠0 verir (verdict farkı bilinçli; kanıt log/taksonomide).

### Resmî koşu sonucu (UX-01 sonrası kodla; dondurulmuş manifest sırası)

Teslimler: `eval/guided_10_report.json` + `eval/guided_10_report.md` (`g11_report.py`).
**GUIDED_CORRECT_STEP_RATE = 0.17 (1/6 geometri kararı olan vaka)**; 10/10 kayıtlı; ürün kodu ilk→son
vaka arasında değişmedi.

| vaka | sınıf | aday | sonuç |
|---|---|---|---|
| plate-pocket-vector | full_step | 45 | **verdict pass** (tek doğru; §29 sayaçları: 4 elle metin · 4 tek-tık ipucu · 36 satır tek toplu eylem) |
| drawing-2-vector | full_step | 66 | CAD_WRONG |
| plastic-enclosure-vector | full_step | 65 | CAD_WRONG (şekil ok, detay -) |
| exercise-12-vector | full_step | 70 | CAD_WRONG |
| exercise-51-raster | full_step | 26 | CAD_WRONG (göbek fragmanı) |
| exercise-17-raster | full_step | 20 | CAD_UNSUPPORTED (üretim reddi) + EVALUATOR |
| exercise-13-raster | full_step | 32 | CAD_UNSUPPORTED + EVALUATOR (sunucu-otoriter kontur düzeltmesiyle pilot'tan ileri gitti) |
| my-part-raster | full_step | 49 | CONSTRAINT_UNSUPPORTED (kalibrasyon sunulmadı — uydurma yok) + EVALUATOR |
| flange-raster | full_step | 29 | CAD_WRONG (disk okuması) + EVALUATOR |
| flange-elbow-90-raster-noref | callout_scope_only | 27 | TRANSCRIPTION (kalibrasyon) + CONSTRAINT_UNSUPPORTED — geometric verdict yok (sınıf gereği) |

Taksonomi: CAD_WRONG 5 · CAD_UNSUPPORTED 2 · EVALUATOR 4 · CONSTRAINT_UNSUPPORTED 2 · TRANSCRIPTION 1.

Sürücü turları (ürün kodu sabit): v2 = UX-01 ipucu düğmesi (`#callout-hint-yes`); v3 = yavaş raster
ingest'e karşı token yakala + yeniden bağlan. Kesintiler kanıtlı: `logs/official/abort1-plate-driver-error.log`
(yeniden oluşturulmuş alıntı), `logs/official/abort2-*-gate900.log` (4 rasterın 900 sn kapısı düşüşü);
4 vaka sunucudaki temiz oturumlarına token'la bağlanıp sürdürüldü (`recipes-resume/`).

Kalan: G12 (generic fix loop — bulgular kayıtlı; düzeltmeler ve yeniden koşu G12'nin işi).

---

## UX-01 — guided akış sadeleştirme PASS (2026-10-07)

Kullanıcının verdiği sıra korundu (G10 freeze `3cdeb5f` → UX-01 → resmî G11). Backend doğruluk
sözleşmeleri değişmedi (parser/binder/compiler/CAD'e dokunulmadı). Plan: kullanıcının `UX_PLAN.md`'si;
kabul ve kanıt eşlemesi: `eval/audits/20261007-guided-ux01/DELIVERY.md`.

| Akış | Ürün değişikliği | Kanıt |
|---|---|---|
| Sonraki eksik | `#callout-prev`/`#callout-remaining`/`#callout-next`; çözülmüş tanımı plan §6.2 birebir (parse durumu otoriter `callout_parses` satırından); oto-ilerleme **yalnız başarılı karar + satır çözülünce** | koşu 04 adım 4–8, 11–12 |
| Toplu „modele ait değil“ | atomik `bulk_set_ignored`: 1 revizyon / 1 history / 1 undo / 1 audit; unknown/stale/foreign/boş tümden red; UI: `#callout-multi` → checkbox → `#callout-bulk-apply` (tek istek) | adım 13–17; `test_guided_callout_http.py` 8 test |
| İpucu tek tık | `#callout-hint-yes` (Evet, doğru) → normal `transcribe`+`accept_hint` (sunucu hint'i birebir doğrular); `#callout-hint-edit` yalnız draft; `#callout-hint-ignore` → `set_ignored` | adım 4–10 |
| Eksik kalanlar | ○ görev satırları (backend readiness satırlarından sayıyla gruplu) + ✓ tamamlananlar; tıklama ilgili denetime odaklar; backend `ready` değilken „hazır“ denmez | adım 18–21, 30 |
| Teknik ayrıntılar | günlük `<details id="technical-details">`, callout ham kimliği `<details id="callout-technical">`; ana copy insan diline (Daire N/Köşe N/Dış şekil); `target_kind` normalde gizli | adım 2, 3 + yapı pinleri |

Kabul: gerçek Chrome **35/35 PASS** (koşu 04; 0 console error, 0 reddedilen istek). Plate smoke: build
`complete`; dondurulmuş değerlendirici **verdict pass**; bbox [15, 80.002, 120.011] G9/g11 kaydıyla aynı
(1 katı, 16 yüz, aynı silindirler). Metrikler (`ux01-metrics.json`): 45 aday · 4 elle metin · 4 tek-tık
ipucu · kuyruk tek toplu eylem (senaryo gereği +6+6 egzersiz) · 1 tek-satır ignore · 1 elle hedef.

Regresyon: guided/callout seti **507 passed**; `pytest -q tests -k "not semread"` → **1450 passed / 339 deselected (25:58)**;
semread bloğu bu turda koşulmadı (bilinçli: ağır blok ayrı parkta). Yeni RED→GREEN: HTTP bulk matrisi +
UX-01 HTML pinleri.

Dürüstlük: koşu 01 sürücü hatasıyla durdu (bileşik seçici); koşu 02'de **gerçek ürün bulgusu** yakalandı —
oto-ilerleme çözülmemiş satırdan zıplıyordu, `rowResolved` şartı eklendi + pin; koşu 03'te tek test-tarafı
`history` yanılgısı kaldı; koşu 04 temiz PASS. Metro: `ux01` kabul sürücüsü mevcut CDP koşum takımını
yeniden kullanır (`cdp_client` + `browser_acceptance` + ux-round yardımcıları); kararlar hep gerçek input
olayı, `Runtime.evaluate` yalnız okuma/kaydırma.

---

## G12 — PLAN-24-G12-CORRECTNESS (devam ediyor)

Kök `PLAN.md` artık PLAN-24-G12-CORRECTNESS; eski kök plan byte-kopya olarak
`docs/PLAN_ROOT_BEFORE_G12_20261007.md`, yeni plan `docs/PLAN-24-G12-CORRECTNESS.md`
(SHA256'lar: `eval/audits/20261007-g12-baseline/run-01/plan-handoff-sha256.txt`).
Durum satırları (§100): G9 PASS · G10 frozen · UX-01 PASS · **G11 baseline 1/9** (kabul edilmiş ürün
DEĞİL — ölçüm) · G11R-01–05 PASS · **G12 current: G12.3 (view-scoped geometry foundation, PLAN-25 §45+)**.

G12.0 (truth lock) tamam: donmuş manifest 10/9/1 ve rapor 1/9 testle çivilendi
(`tests/test_g12_baseline_contract.py`); G9 Plate dondurulmuş evaluator **PASS** (9/9,
`eval/audits/20261007-g12-baseline/run-01/plate-regression-verdict.json`); ilgili süit **540 passed**
(189 s); referans sızma **süreç sınırı** kuruldu (`eval/g12_runner/` + `tests/test_g12_runner_boundary.py`).

G12.2 (açık üretim biçimi) tamam: seçili profil artık **hiçbir şey ima etmez**. Kullanıcı parçanın ana
oluşturma biçimini açıkça söyler (`extrude_profile` / `revolve_profile` / `multi_view_composite` /
`unsupported`); `make_plan` ortak bağlam + **explicit dispatch**'tir (`compile_extrude_plan` /
`compile_revolve_plan` / `compile_multiview_plan`) — **örtük extrude yok**, daire profili açık onayla
ekstrüde edilir, geometri-sınıfı kara listesi de yoktur. Anahtarı ve geometri sürümünü **sunucu** sabitler
(`set_strategy`, tek revizyon, geri alınabilir; `/save` sahte strateji yazar). Profil/kontur/görüş/okuma
değişince karar **bayatlar** ve üretim yeniden onay ister. Kanıt: yeni `tests/test_build_strategy.py` (11)
ve `tests/test_guided_strategy_ui.py` (5) + ilgili süit **401 passed**; taze Plate kabulü
`eval/audits/20261007-g12-strategy-plate/` — callout incelemesi (reçete dışı 36 satır tek tek adıyla),
stratejisiz üretimin reddi, açık onay, üretim, STEP reopen ve **dondurulmuş evaluator 9/9 PASS**
(120 × 80 × 15, 4 delik, 1 cep). Ayrıntı: `eval/g12_progress.md` / `eval/g12_progress.json`.

G12.1a (false readiness / decision coverage — backend) tamam: callout gözden geçirmesi artık **adı konmuş
bir kapsam kararı** taşır (`not_model_input` / `redundant + dayanak` / `build_relevant_unsupported + gerekçe`;
şema 4). Eski `ignored`/`unbindable` kayıtları terfi ETMEZ → `legacy_unclassified` ve fresh koşuda
**bloklar**; gerçek ölçü işaretli `build_relevant_unsupported` de build'i artık **açmaz, kapatır** (G11'in
ölçtüğü sahte hazırlık). `callout_coverage` + kapsam soruları readiness'e girdi; toplu karar yalnız
`not_model_input` yazar. Kanıt: 276 passed + 630 passed regresyon, `eval/audits/20261007-g12-decision-coverage/`.
Ayrıntı: `eval/g12_progress.md` / `eval/g12_progress.json`.

G12.1b (coverage UI + runner v2) tamam: arayüz kendi ikinci kapsam motorunu kurmayı bıraktı —
`rowResolved` ve liste süzgeci backend kovasından (`state.coverage`) okur; “Sonraki eksik” desteklenmeyen,
eski kayıt ve geçersiz dayanak satırlarını **atlamaz**; oto-ilerleme yalnız satırı gerçekten çözen
komuttan sonra kurulur (legacy `set_unbindable` arayüzden kalktı, yerine gerekçe isteyen
`set_disposition` geldi). Üç karar adıyla var: “Bu bir ölçü/not değil”, “Zaten başka bir bilgiyle temsil
ediliyor” (+ dayanak seçimi, backend `decision:<ad>` sözlüğü), “Gerçek ölçü/not ama şu an modele
uygulanamıyor” (gerekçe zorunlu). Kapsam özeti backend sayılarından çizilir. Yeni koşucu
`eval/g12_runner/{recipe_v2,g12_runner}.py` blanket alanları reddeder; kalan satırlar kendiliğinden
kapatılmaz. Kanıt: gerçek Chrome **10/10** (`eval/audits/20261007-g12-decision-coverage/browser/`),
odak **78 passed**, geniş `pytest -q tests -k "not semread"` yeşil.
