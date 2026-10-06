# Guided progress

Scope: G0 + G1 (düzeltme turu 1 dahil)  
Active plan: `docs/PLAN-20.md`  
Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
Current HEAD: `5175f37` + G0 `373e096` + G1.2/G1.3 `554f5ae` + G1.4–G1.7 `e59c5eb` + düzeltme turu 1 (bu commit)  
Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)  
Current task: **G1 + düzeltme turu 1 tamam** — teslim edildi; G2+ hâlâ açılmadı

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
| **Düzeltme turu 1** | **PASS** | Bağımsız incelemedeki 4 sorun kapatıldı; 8 yeni regresyon testi önce kırmızı → sonra yeşil; models+callouts **74 passed** (`g1-fix1-models-callouts.log`); birleşik küme **183 passed / 78.31 s / EXIT=0** (`g1-fix1-final.log`) | — |

## Düzeltme turu 1 (bağımsız inceleme) — önce/sonra

**Önceki kabulün eksikleri (dürüst kayıt):** G1.2–G1.7 kabulü şunları kaçırmıştı — (a) taşınan onayın sunucu alanlarının istemci değerleriyle yazılması; (b) tek-save'de pin/doğrulama bağlamı tutarsızlığı; (c) parse kapısının **varlık** kontrolünde kalması (status'a bakmaması); (d) vertex_pair sözleşmesinin yanlış daraltılması (ardışıklık şartı + yalnız `v{index}` kabulü).

| # | Sorun (inceleme) | Önce (repro) | Sonra (nasıl kapatıldı) | Kanıt |
|---|---|---|---|---|
| 1 | Taşınan hedefin sunucu alanları istemciden yazılabiliyordu | Onayla → profil değiştir → stale; istemci `geometry_key`+`profile_id` güncelleyince hedef yeniden **current** yazılıyordu | `_target_carried` artık sunucu alanlarını/evidence'ı karşılaştırmıyor; taşınan satır **kalıcı kayıttan byte-korunur** (istemci sürüklenmesi yazılmaz). Gerçek yeniden onay tek kullanımlık açık `reconfirm` isteğidir (`CalloutTargetDecision.reconfirm`): doğrulama gördükten **sonra** tüketilir, kayıtta daima `false`. Evidence değişimi yeniden onay **değildir**. | `test_a_carried_target_keeps_its_persisted_server_fields`, `test_a_real_reconfirmation_is_an_explicit_act` |
| 2 | Profil değişimi + yeni hedef onayı aynı save'de tutarsız | `selected=outline_2` iken `target.profile_id=outline_1` yazıldı, key yeni bağlamdan; target **current** görünüyordu (kırmızı kanıt: `assert 'outline_1' == 'outline_2'`) | Pinleme **ve** geometri denetimi bu save'in payload bağlamından: `profile_id` = seçili profil, kenar çözümü **yeni** konturda yapılır; eski konturun uç kimliği yeni bağlamda reddedilir | `test_a_profile_switch_and_a_new_confirmation_in_one_save_agree`, `test_a_new_confirmation_is_checked_against_the_new_context` |
| 3 | Başarısız/çelişkili parse hedef onayına dayanak olabiliyordu | `status=unsupported`/`ambiguous` fixture ile yeni target kabul edilip **current** gösteriliyordu; kapı yalnız "kayıt var mı" diyordu | Kapı: exact kayıt **tek ve `status='parsed'`** olmalı; aynı kimlikli farklı içerikli parse kayıtları reddedilir. Tazelik hesabı ile anlamsal geçerlilik ayrı kaldı (hesap current diyebilir; onay dayanağı olamaz) | `test_a_failed_parse_cannot_be_the_basis_of_a_target_confirmation[unsupported/ambiguous]`, `test_conflicting_parse_records_refuse_a_target_confirmation` |
| 4 | vertex_pair sözleşmesi yanlış daraltılmış | Ardışıklık şartı vardı (v0–v2 reddediliyordu); mevcut kararlı uç kimlikleri (`g0:start`) reddediliyor, yalnız `v{index}` kabul ediliyordu | Mevcut kararlı uç kimlik yolu kullanılır: `<edge_id>:start|end` (binding çözücüsüyle aynı kenar araması) + kanonik `v{index}`; **komşuluk şartı kaldırıldı**; aynı fiziksel noktanın iki farklı ID ile seçilmesi ayrıca reddedilir. Ardışık-olmayan çifti reddeden eski test düzeltildi. | `test_a_vertex_pair_uses_the_stable_endpoint_ids`, `test_a_vertex_pair_rejects_the_same_physical_point_twice`, düzeltilen `test_wrong_targets_are_refused_without_touching_the_record` |

Ek: eski akışı kodlayan 4 mevcut test yeni açık mekanizmaya taşındı (evidence-reconfirm → `reconfirm` bayrağı; "hedef düzenlemesi" → gerçek seçim değişikliği). **RED kanıtı:** düzeltme öncesi hedefli koşum **8 failed / 2 passed** (yalnız yeni testler; hata 2 birebir: `assert 'outline_1' == 'outline_2'`); düzeltme sonrası aynı hedef küme **11 passed**. İlk yeşil koşumda ek bir hata yakalandı ve düzeltildi: `reconfirm` bayrağının `_prepare_callouts` içinde erken tüketilmesi doğrulamayı atlatıyordu (`DID NOT RAISE`) → tüketim `_consume_reconfirm` ile doğrulamadan sonraya alındı.

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
- **`source_unavailable` semantiği:** kaynak değişmiş/okunamaz (geometry_stale) ise parse kaydı "current veri" olarak sunulmaz (PLAN-20 §7 satırı) — transcription tarihsel kalır, target stale, build `historical`, current indirme yok.
- **Bulunan/düzeltilen hatalar:** (a) fixture sınıfı: `_fake_build` `revision: 0` sabitliyordu → `record["revision"]`; (b) ürün, dar: `_prepare_callouts` pin anahtarı bu save'in bağlamından; (c) düzeltme turu 1 içi: `reconfirm` bayrağının erken tüketilmesi doğrulamayı atlatıyordu (`DID NOT RAISE`) → `_consume_reconfirm` doğrulamadan sonraya alındı.
- Test fixture'larındaki parse/target hazırlık verisidir; ürün parser/önerici kanıtı sayılmaz. G1'de gerçek parser yok; `CALLOUT_PARSER_VERSION="callout-parser/1"` G4'e açık parametre; public'te `missing/needs_parse` görünür; log'a parse olayı yazılmaz.
- Baseline ve tüm kümeler yeşil; skip/xfail ile kapı geçilmedi. `rg` host'ta yok; aramalar daraltılmış yolla yapıldı. Pydantic bool→int lax modu nedeniyle bool guard'lar açık.

## Yeniden başlarken ilk somut işlem

- G1 + düzeltme turu 1 teslim edildi; **G2+ hâlâ açılmadı.** Kullanıcı G2'yi açarsa: `docs/PLAN-20.md` §11.1'i oku; Observations → callout candidate adaptörünü `source_digest + page_index + canonical region + detector_version + source_kind` deterministik kimliğiyle küçük iş paketlerine böl; sahte kutu üretme kuralını koru.
