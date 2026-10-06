# Guided progress

Scope: G0 + G1  
Active plan: `docs/PLAN-20.md`  
Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
Current HEAD: `5175f37` + G0 `373e096` + G1.2/G1.3 `554f5ae` + G1.4–G1.7 (bu commit)  
Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)  
Current task: **G1 tamam** — teslim raporu verildi

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G0 | PASS | `docs/PLAN-20.md`, `report.md` pivot + park kaydı, bu dosya; commit `373e096`; kod değişmedi; 0 model çağrısı | — |
| G1.1 | PASS | Entegrasyon haritası + odak baseline **59 passed / 83.30 s / EXIT=0** (`g1-baseline.log`) | — |
| G1.2 | PASS | `callout_models.py` + `tests/test_callout_models.py` **35 passed** (`g1-2-models.log`); negatifler doğru nedenle kırmızı | — |
| G1.3 | PASS | Store entegrasyonu + `tests/test_guided_callouts.py` 11 passed (`g1-3-callouts.log`); odak kümesi **105 passed / 80.14 s** (`g1-3-green.log`) | — |
| G1.4 | PASS | Freshness/target testleri (T06/T07/T09/T10/T11/T12/T17/T21 + contour varyantı); `source_unavailable` parse semantiği | — |
| G1.5 | PASS | Undo/olay günlüğü testleri (T13/T14/T22 + log denetimi): A→B→undo→reopen A'yı aynen döndürür; `transcribe`/`edit_transcription`/`confirm_target` yalnız kullanıcı olayı; parser olayı yok | — |
| G1.6 | PASS | Build/artifact stale (T15/T16): geç build yeni kararlara bağlanmaz, `build=None` ile çökmez; eski STEP diskte tarihsel kalır, current sunulmaz | — |
| G1.7 | PASS | Birleşik doğrulama **174 passed / 79.51 s / EXIT=0** (`g1-7-final.log`); `git diff --check` temiz; kabul tablosu aşağıda | — |

## G1 kabul tablosu (PLAN-20 §13)

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
| Stale client, yanlış hedef ve geç biten build doğrulandı | PASS | T07; `test_wrong_targets_are_refused_...`; `test_a_build_that_finishes_late_...` |
| İlgili eski testler + T01–T22 yeşil; skip/blocked başarıya katılmadı | PASS | **174 passed, 0 failed, 0 skipped** (`g1-7-final.log`); T eşlemesi aşağıda |
| UI/parser/compiler uygulanmadı → rapor bunu sonraki faz yazıyor | PASS | Teslim raporu; G2/G3/G4 kapsamı |
| İlerleme dosyasında kalan ve gerçek komut sonuçları | PASS | bu dosya + `out/guided-transcription/*.log` |

## T01–T22 eşlemesi (`tests/test_guided_callouts.py` / `tests/test_callout_models.py`)

T01 round-trip → models testleri · T02 raw/reopen → `test_save_persists_a_transcription_and_reopen_keeps_raw_text` · T03 hint → `test_a_machine_text_hint_never_becomes_a_decision` · T04 eski session → `test_an_old_session_opens_serves_its_build_and_is_not_rewritten` · T05 eski history'ye undo → `test_undo_accepts_a_history_entry_without_the_new_fields` · T06 metin değişimi → `test_editing_the_text_stales_the_old_parse_and_target_and_keeps_history` · T07 revision conflict → `test_a_stale_revision_save_is_refused_and_the_record_keeps_its_first_value` · T08 ilgisiz edit → `test_an_unrelated_edit_bumps_the_session_but_not_the_transcription_revision` · T09 kaynak/sürüm → `test_a_changed_source_stales_the_callout_layer_and_the_build` + `test_a_geometry_version_mismatch_stales_the_target` · T10 profil/kontur → `test_a_profile_change_stales_the_target_within_the_same_geometry_version` + `test_a_contour_change_stales_the_target_in_the_same_version` · T11 yanlış hedef → `test_wrong_targets_are_refused_without_touching_the_record` · T12 count → `test_an_explicit_count_must_match_the_unique_targets` · T13 undo → `test_undo_restores_the_earlier_callout_decisions_and_stales_the_build` · T14 → `test_undo_does_not_make_an_old_target_current_again` · T15 → `test_a_later_edit_leaves_the_old_step_historical_and_never_current` + `test_a_target_edit_also_makes_the_old_step_historical` · T16 → `test_a_build_that_finishes_late_never_attaches_to_newer_decisions` · T17 çift load → `test_loading_twice_changes_nothing` · T18 no-op → `test_saving_the_same_transcription_again_is_a_noop` · T19 eski istemci → `test_missing_keys_keep_callout_decisions_and_explicit_empty_removes_them` · T20 accept → `test_accept_keeps_callout_decisions_and_confirms_nothing` · T21 parser sürümü → `test_an_old_parser_version_fixture_stales_its_parse_and_target` · T22 temel veri → `test_base_reading_and_options_survive_callout_edits_and_undo`

## Son doğrulamalar

- **G1.7 birleşik**: 15 dosya (`test_callout_models`, `test_guided_callouts` + odak 6 + `test_view_decision`, `test_view_core`, `test_sheet_frame`, `test_stable_identities`, `test_contour_fix`, `test_measure_meaning`, `test_user_dimensions`) → exit **0**, **174 passed** (79.51 s) — `out/guided-transcription/g1-7-final.log`
- G1.4/G1.5/G1.6: `tests/test_guided_callouts.py` → exit 0, **30 passed** — `out/guided-transcription/g1-5-6-callouts.log`
- G1.3: **105 passed** (80.14 s) — `g1-3-green.log`; G1.2: **35 passed** — `g1-2-models.log`; G1.1: **59 passed** — `g1-baseline.log`
- `git diff --check` → temiz (CHECK_EXIT=0)

## Entegrasyon haritası (G1.1) — mevcut store yolları × yeni callout alanları

| Store yolu | G1'de yeni alanlara nasıl dokundu (uygulandı) |
|---|---|
| `create` | `callout_schema_version` + boş `callout_candidates`/`callout_parses`; `decisions` yeni listeleri boş taşır |
| `load` | Salt-okur; yeni alanlar yoksa varsayılanla okunur; migration/revision döngüsü yok (T17) |
| `_migrated` | Değişmedi; callout alanları kimlik karşılaştırmasına girmez |
| `save` (edit) | `_merge_callout_defaults` + `_prepare_callouts` + `_validate_callouts`; callout olayları loglanır; `revision+1`, `build=None` |
| `save` (undo) | History snapshot'ı aynen; global revision artar; `build=None` (STEP diriltilmez) |
| `accept` | Aynı hazırlık/denetim kapılarından geçer; callout kararlarını korur; onay üretmez |
| `public` | `callout_schema_version`/`callout_candidates`/`callout_parses`/`callouts` (current/stale/missing + reason) |
| `build` | Akış değişmedi; geç-build yarışı zaten korumalı (T16 ile doğrulandı) |
| `artifact` | Değişmedi; stale/kimlik kapıları eski çıktıyı current sunmaz |

## Kararlar / engeller

- **Sunucu kuralları (yürürlükte):** `normalized_text` daima sunucuda (`raw_text` birebir). Transcription `revision` = yazıldığı/değiştiği save'in `revision+1`'i; taşınan kayıt eski kimliğini korur. Target pinleme yalnız yeni/değişen onayda (`geometry_key`/`geometry_version`/`profile_id` bu save'in bağlamından — profil değişimi + onay aynı payload'da gelebilir); taşınan onay bayt-korunur. Store denetimi: callout bu oturumda/kaynakta; hedef id'leri gerçek (circle/circle_group ∈ `options["circles"]`; vertex_pair seçili profilin `v{edge}` ardışık uçları); transcription revision'ı güncel + exact parse; açık `count` = benzersiz hedef sayısı. No-op karşılaştırması `_normalized_decisions` (dosya hiç yazılmaz). `callout_schema_version` ile sürümleme; `geometry_version` artmaz.
- **`source_unavailable` semantiği:** kaynak değişmiş/okunamaz (geometry_stale) ise parse kaydı "current veri" olarak sunulmaz (PLAN-20 §7 satırı) — transcription tarihsel kalır, target stale, build `historical`, current indirme yok.
- **Bulunan ve düzeltilen tek hata (fixture sınıfı)**: `_fake_build` fixture'ı `revision: 0` sabitliyordu; test 2. revizyondaydı → `build_status` beklenenden "historical" çıktı. Kök neden: fixture; düzeltme: `record["revision"]` kullanmak. Ürün kodu değişmedi — sınıf: **fixture**.
- **Ek düzeltme (ürün, dar):** `_prepare_callouts` pin anahtarını payload sonrası hesaplar (aynı save'de gelen profil değişimi + yeni onay yeni bağlamla pinlenir).
- Test fixture'larındaki parse/target hazırlık verisidir; ürün parser/önerici kanıtı sayılmaz. G1'de gerçek parser yok; `CALLOUT_PARSER_VERSION="callout-parser/1"` G4'e açık parametre; public'te `missing/needs_parse` görünür; log'a parse olayı yazılmaz.
- Baseline ve tüm kümeler yeşil; skip/xfail ile kapı geçilmedi. `rg` host'ta yok; aramalar daraltılmış yolla yapıldı. Pydantic bool→int lax modu nedeniyle bool guard'lar açık.

## Yeniden başlarken ilk somut işlem

- G1 teslim edildi; **sonraki faz (G2+) ayrı yetkilendirme ister.** Kullanıcı G2'yi açarsa: `docs/PLAN-20.md` §11.1'i oku; Observations → callout candidate adaptörünü `source_digest + page_index + canonical region + detector_version + source_kind` deterministik kimliğiyle küçük iş paketlerine böl; sahte kutu üretme kuralını koru.
