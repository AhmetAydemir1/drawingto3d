# G3R teslim — kök `PLAN.md` düzeltme turu (G3R-01–04)

**Tarih:** 2026-10-06 · **Başlangıç HEAD:** `2cdb4d0424b17e4299d625066c24e6a0eab4de6d` (`2cdb4d0`)
**Kapsam:** G3R-01 → G3R-02 → G3R-03 → G3R-04 + doğrulama ve teslim (kök `PLAN.md` §4–§10)
**Model çağrısı:** 0 · **G4+:** uygulanmadı · **Commit:** yok (değişiklikler çalışma ağacında, kullanıcı kararına bırakıldı)
**Çalışan G3:** baştan yazılmadı; dört bulgu için dar düzeltme (arayüz, store komutları ve kabul kanıtları korundu)

Bu turda ürün kodu dışında hiçbir şey değişmedi: `src/drawingto3d/guided.py`, `src/drawingto3d/callout_models.py`,
`src/drawingto3d/static/guided.js`, `src/drawingto3d/static/guided.html`. Testler: `tests/test_guided_callout_review.py`
(+15), yeni `tests/test_guided_callout_http.py` (gerçek HTTP sınırı, 2 test), `tests/test_guided_html.py` (+1).

## 1. Dört düzeltme — bulgu → değişiklik → regresyon → kanıt

| # | Bulgu (bağımsız inceleme) | Düzeltme (dar) | Regresyonlar (düzeltme öncesi KIRMIZI) | Komut / exit | Kanıt yolu |
|---|---|---|---|---|---|
| G3R-01 | Eski `/save`, `/callout` komutlarının kurallarını atlıyordu: istemci `manual:000…` kimliği, yabancı `source_digest`, `page_index=7`, `revision=999`; `unknown-callout` için review; ignored callout'a metin (`/callout` 400 verirken `/save` kabul); etkin bölgeden farklı `source_region` | Tek kalıcılık yolu `GuidedStore._commit`; public `save` artık komut olayı kabul etmiyor; `_validate_callouts(record, decisions, produced)` satır sahipliğini denetliyor (yalnız kendi komutunun ürettiği manual/review satırı); transcription satırı (callout, etkin bölge, metin) eşleşmesiyle taşınır ve yeniden damgalanmaz; yeni metin ignored/yanlış sayfa/yanlış bölgede ret; aynı eylem iki kez loglanmaz | `test_a_public_save_cannot_create_or_change_a_manual_region`, `test_a_public_save_cannot_set_a_review_decision`, `test_clearing_the_review_list_is_a_real_restore_not_a_silent_edit`, `test_a_public_save_cannot_write_text_to_an_ignored_callout`, `test_a_public_save_checks_the_text_region_against_the_effective_region`; HTTP: `test_http_save_cannot_bypass_the_callout_rules` | `pytest -q tests/test_guided_callout_review.py tests/test_guided_callout_http.py` → **EXIT 1** (15 failed) → düzeltme sonrası **EXIT 0** | `out/guided-g3r/g3r-red.log`, `out/guided-g3r/g3r-combined.log`; probe `review_probes.py` **EXIT 0** 7/7 → `probe-results-after.json`; `http_review_probes.py` **EXIT 0** → `http-probe-after.json` |
| G3R-02 | Bölge taşındıktan sonra public state `region_changed`/stale dese de eski transcription/parse bağıyla yeni hedef `confirmed` kaydedilebiliyordu | Onay freshness'i kaydın **bırakacağı** etkin kararlardan: `callout_models.callout_state(record, callout_id, decisions=payload)`; ret: kaynak yok / ignored / transcription current değil / parse current ve `parsed` değil | `test_a_new_confirmation_after_a_region_move_needs_a_current_text_and_parse`, `test_a_region_move_and_a_target_confirmation_in_one_save_cannot_skip_freshness`, `test_an_ignored_callout_cannot_be_confirmed_and_a_carried_target_is_untouched`; HTTP: `test_http_save_cannot_confirm_a_target_on_a_stale_region` | aynı koşu → **EXIT 1** → **EXIT 0** | probe satırı `new_confirmation_requires_current_transcription_and_parse`: `probe-results-before.json` `passed=false` → `probe-results-after.json` `passed=true` |
| G3R-03 | `_stamp_callout_version` kayıt sürüm taşıyorsa erken dönüyordu → `callout_schema_version=1` oturumunda G3 yazımı sürümü 1 bırakıyordu | Damga yalnız gerçek diske yazımda; `version >= CALLOUT_SCHEMA_VERSION` ise dokunulmaz (gelecekteki sürüm düşürülmez); load/public/no-op baytı değiştirmez; ayrı revision/history/log üretmez | `test_a_v1_session_is_stamped_by_its_first_real_write_and_reads_stay_read_only`, `test_a_versionless_legacy_session_is_stamped_on_a_real_write_only`, `test_a_future_unknown_schema_version_is_never_downgraded` (HEAD'de de yeşil — koruma), `test_undo_never_lowers_the_callout_schema_version` | aynı koşu → **EXIT 1** (3 kırmızı) → **EXIT 0** | probe satırı `v1_session_real_g3_write_stamps_current_schema` (before `false` → after `true`) |
| G3R-04 | `create()` detection diagnostics'i yazıyor ama `public()` döndürmüyordu; UI her boş listeyi “metinsiz çizim” diye açıklıyordu | `public()` `callout_detection` (`detector_version` + `diagnostics`; eski kayıtta `null`); `guided.html` `#callout-detection`; `guided.js` neden eşlemesi: “Aday üretilemedi: <neden>” / “metinsiz çizim normal bir sonuçtur” yalnız `no_text_observations` iken / “eski kayıtta tespit bilgisi yok” / bilinmeyen kod birebir; aday varsa yalnız uyarı | `test_the_public_state_serves_the_detection_metadata_and_admits_its_absence`, `test_the_empty_callout_list_gives_the_detectors_own_reason`; tarayıcı senaryo 5 (üç durum) | aynı koşu → **EXIT 1** → **EXIT 0** | probe satırı `public_preserves_detection_metadata`; `browser-acceptance.log` + `g3r-13/14/15-*.png` |

**Koruma (guard) testleri** — düzeltme öncesi de yeşildi, sözleşmeyi bu turda kilitliyor:
`test_an_unrelated_full_save_carries_every_g3_row_verbatim`, `test_the_full_review_flow_still_works_end_to_end`,
`test_a_carried_stale_target_survives_an_unrelated_full_save` (PLAN.md §5 “ilgisiz kayıt stale target'ı ne yeniden
onaylar ne bloke eder” maddesi), `test_a_future_unknown_schema_version_is_never_downgraded` (G3R-03'ün ters yönü).

## 2. Doğrulama

### 2.1 Kırmızı kanıt (düzeltme öncesi kod)

Düzeltmeler tamamlanmadan önce, *aynı* test dosyaları HEAD'in (2cdb4d0) ürün koduyla koşuldu:

```
.venv/bin/python -m pytest -q tests/test_guided_callout_review.py tests/test_guided_callout_http.py tests/test_guided_html.py
→ 15 failed, 44 passed  (EXIT 1)          # out/guided-g3r/g3r-red.log
```

Kırmızı 15: G3R-01 (5 store + 1 HTTP), G3R-02 (3 store + 1 HTTP), G3R-03 (3), G3R-04 (store + HTML). Dosya adları §1 tablosunda.
Düzeltme sonrası aynı üç dosya: **59 passed / EXIT 0**.

`out/` gitignore'da olduğu için iki logun **repo içi kopyaları** bu klasörde: `g3r-red.log`, `g3r-combined.log`,
`combined-files.txt` (birleşik koşunun dosya listesi). Kopyalarda yalnız satır sonu boşlukları kırpıldı
(commit edilebilir diff için); içerik ve sayılar aynı. Orijinaller `out/guided-g3r/` altında:
`g3r-red.log` sha256 `d3ecda60…`, `g3r-combined.log` sha256 `39863051…`.

### 2.2 Bağımsız probe'lar (PLAN.md §9.1 — dördü de exit 0)

| Probe | Önce | Sonra | Kanıt |
|---|---|---|---|
| `eval/audits/20261006-guided-g3-independent-review/review_probes.py` | 0/7, exit 1 | **7/7, exit 0** | `probe-results-before.json` → `probe-results-after.json` |
| `eval/audits/20261006-guided-g3-independent-review/http_review_probes.py` | 0/1, exit 1 | **1/1, exit 0** | `http-probe-before.json` → `http-probe-after.json` (hem `/callout` hem `/save` 400, `*_unchanged: true`, `saved_callout: null`) |
| `eval/audits/20261006-guided-g1-review/review_probes.py` | exit 0 | **exit 0** (`passed: true`) | `probe-results-g3r-after.json` |
| `eval/audits/20261006-guided-g2-review/review_probes.py` | exit 0 | **exit 0** (5/5) | `probe-results-g3r-after.json` |

Probe beklentileri değiştirilmedi; yalnız çıktı yolları bu turun `-after` adlarına yazıldı. Eski tur kanıtları silinmedi.

### 2.3 Birleşik test kümesi (§9.1 + yeni HTTP dosyası)

```
.venv/bin/python -m pytest -q \
  tests/test_guided_callout_review.py tests/test_callout_candidates.py \
  tests/test_guided_callout_candidates.py tests/test_callout_models.py \
  tests/test_guided_callouts.py tests/test_guided.py \
  tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py \
  tests/test_guided_proposals.py tests/test_binding_end_meaning.py \
  tests/test_guided_html.py tests/test_view_decision.py tests/test_view_core.py \
  tests/test_sheet_frame.py tests/test_stable_identities.py tests/test_contour_fix.py \
  tests/test_measure_meaning.py tests/test_user_dimensions.py \
  tests/test_guided_callout_http.py
→ 304 passed / 133.47 s / EXIT 0      # out/guided-g3r/g3r-combined.log
```

Baseline 285 (G3 turu, 18 dosya) + 19 yeni test (review +16 [12 kırmızı + 4 koruma], HTTP +2, HTML +1) = 304. Sayı uydurulmadı; loga gerçek komut/exit/süre yazıldı.
`git diff --check` → temiz. **Tam takım (full pytest) bu turda koşulmadı.**

### 2.4 Gerçek tarayıcı kabulü (PLAN.md §9.2 — 6 senaryo)

Sürücü: `browser_acceptance.py` (yeni) + G3 turundan yeniden kullanılan `cdp_client.py`; gerçek Chrome + CDP 9222,
gerçek fare/klavye olayları (`Input.dispatchMouseEvent` / `Input.insertText`); uygulama gerçek `:8765`.

```
PYTHONPATH=src:$HOME/.hermes/cache/scratch/cdp-venv/lib/python3.12/site-packages \
  .venv/bin/python eval/audits/20261006-guided-g3r-fix-review/browser_acceptance.py
→ 30/30 adım PASS / EXIT 0            # browser-acceptance.log, browser-steps.json, 16 screenshot (g3r-00…g3r-15)
```

Koşu ortamı: numpy `.venv`'de, CDP taşıması (`websockets`) cdp-venv'de; cdp-venv'in kendi python'ı
`ModuleNotFoundError: No module named 'numpy'` ile düşer. Bu, script'in docstring'inde ve bu dosyada yazan
eski komuttu; geç gelen arka plan bildirimi gösterdi, ikisi de yukarıdaki **doğrulanmış** birleşik komuta
çevrildi ve kabul **o komutla yeniden koşuldu**: 2026-10-06 18:51, 30/30 PASS / EXIT 0
(log, `browser-steps.json`, 16 screenshot yenilendi).

İki not (gizlenmedi):
- Konsol/ağ temizliği iki adımı artık tarayıcının **kendi** `GET /favicon.ico` isteğini açıkça muaf tutar
  (uygulama favicon sunmuyor; ilk koşuda Chrome önbelleği sıcak olduğu için görünmedi, ikinci koşuda
  göründü ve iki adımı düşürdü). Muafiyet `browser_automatic_ignored` alanında raporlanır; son koşuda bu
  liste boş. Başka her konsol hatası/reddedilen istek koşuyu yine düşürür.
- Ön koşul: Chrome'da en az bir **page target** olmalı; hiç yoksa script `RuntimeError: no page target in
  the attached Chrome` verir (sekme kapanmışsa: `curl -X PUT http://127.0.0.1:9222/json/new?about:blank`).

| Senaryo (§9.2) | Adım kanıtı |
|---|---|
| 1. PDF aç → aday seç/crop → metin kaydet → reload → aynı metin; seçim + taslak koruması | `scenario 1: …` (7 adım), `g3r-01…g3r-04` |
| 2. Manuel alan → metin → alanı değiştir → “Alan değişti” → aynı metni açıkça yeniden kaydet → güncel; parser iddiası yok | `scenario 2: …` (5 adım; `parses: []`), `g3r-05/g3r-06` |
| 3. Ignore → göster → restore → undo; eski full-save kalınlık işlemi callout kararlarını bozmuyor | `scenario 3: …` (6 adım; `callout_rows_equal: true`), `g3r-07…g3r-09` |
| 4. Kaydedilmemiş taslak + revision conflict → hata görünür, metin durur, güncel state sonrası kayıt çalışır | `scenario 4: …` (3 adım), `g3r-10` |
| 5. Normal boş / hata nedeniyle boş / metadata'sız eski kayıt doğru açıklanır (fixture'lar açık) | `scenario 5: …` (6 adım), `g3r-13/14/15`; üç durumda da yazımsızlık bayt ile doğrulandı |
| 6. Dar/geniş seçim/crop + eski guided kontrolü (profil) smoke; yeni metinlerde HTML çalıştırma yok | `scenario 6: …` (2 adım), `g3r-11/g3r-12`; `<img …>` diagnostic'i birebir metin, `images: 0` |

Console/network: 1 beklenen `POST /api/guided/callout` 400 (bilerek yaratılan revision conflict), başka hata yok —
`browser-steps.json` içindeki `console` / `rejected_requests`. Senaryo 5'in `source_digest_mismatch` ve metadata'sız
oturumları **açık fixture**'dır (gerçek store'dan üretildi, detection alanı diskte düzenlendi); normal boş durum gerçek
metinsiz PNG ile koşuldu, fixture değil. HTTP ret kanıtı UI senaryosu yerine sayılmadı.

## 3. Kabul matrisi (PLAN.md §4–§7 kabul maddeleri)

`docs/GUIDED_PROGRESS.md` → “G3R kabul matrisi (PLAN.md §4–§7)” bölümünde madde-madde eşleme var. Özet:

- G3R-01: dört probe + gerçek HTTP çift yön ret + akış (add_region→…→undo) + eksik anahtar/`[]`/ilgisiz full-save + no-op/history/reddedilen-istek davranışları → hepsi kanıtlı.
- G3R-02: stale yeni hedef ret (store + HTTP) + neden listesi + taşınan hedef bayt-koruma + önceki 2/2 ve 5/5 scriptleri exit 0.
- G3R-03: v1/v2, okuma/no-op, gerçek write, undo sürüm testleri + probe.
- G3R-04: public diagnostics + üç UI durumu + “diagnostic karar/revision/log üretmez” + boş çizimde manuel alan.
- §8 geçiş kapıları: her satırda RED → düzeltme → yeşil sırası bu dosyada kanıtlı; son birleşik koşu **304 passed / EXIT 0**.

## 4. Açık kalanlar (gizlenmedi)

1. **Commit + push yapıldı** (kullanıcı istedi): `a187bf3` → `git push origin main` → `2cdb4d0..a187bf3` (origin/main). Aşağıdaki liste o commit'in içeriğidir; `PLAN-17-HERMES.md` kasıtlı olarak stage dışı kaldı. Teslim kayıtlarındaki (bu dosya, `docs/GUIDED_PROGRESS.md`, `report.md`) commit hash'i sonrası güncellendi.

   ```sh
   git add src/drawingto3d/guided.py src/drawingto3d/callout_models.py \
           src/drawingto3d/static/guided.js src/drawingto3d/static/guided.html \
           tests/test_guided_callout_review.py tests/test_guided_html.py tests/test_guided_callout_http.py \
           docs/GUIDED_PROGRESS.md report.md \
           eval/audits/20261006-guided-g3r-fix-review eval/audits/20261006-guided-g3-independent-review
   ```
2. **Tam takım koşulmadı.** Bu turda seçili 19 dosya koşuldu (304 passed). Önceden mevcut ilgisiz kırmızı: `tests/test_planner.py::test_settings_record_is_the_run_record_fields` — bu turda ele alınmadı.
3. **G4 yok.** Deterministik parser, parse onayı, target önericisi ve callout→CAD uygulaması bu turda uygulanmadı; UI metni de bunu söylüyor (callout metni henüz STEP'e uygulanmıyor).
4. **Fixture sınırı.** §2.4'te işaretlenen iki detection fixture'ı ürün hatası değildir; gerçek detector'ın “reddedildi”/“bilgi yok” durumlarını UI'da görebilmek için diskte düzenlenmiştir.
5. Uygulamanın kendi sunucusu ve Chrome CDP oturumu bu tur boyunca açık kaldı (`:8765`, `:9222`); teslim dosyaları dışında ek artefakt yazmadı.

## 5. Yeniden üretme (kısa)

```sh
# 1) sunucu + tarayıcı
PYTHONPATH=src .venv/bin/python -m drawingto3d.app            # :8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-cdp about:blank

# 2) testler
.venv/bin/python -m pytest -q tests/test_guided_callout_review.py tests/test_guided_callout_http.py tests/test_guided_html.py
.venv/bin/python -m pytest -q $(cat out/guided-g3r/combined-files.txt 2>/dev/null || true)   # §2.3'teki liste

# 3) bağımsız probe'lar (hepsi exit 0 bekler)
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/http_review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g2-review/review_probes.py

# 4) tarayıcı kabulü (30/30 bekler)
PYTHONPATH=src:$HOME/.hermes/cache/scratch/cdp-venv/lib/python3.12/site-packages \
  .venv/bin/python eval/audits/20261006-guided-g3r-fix-review/browser_acceptance.py
```
