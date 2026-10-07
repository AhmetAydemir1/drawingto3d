# Düzeltme raporu — R01–R05 (bağımsız inceleme bulguları)

- Tarih: 2026-10-07 ~01:05 +03 · Taban HEAD: `e51f555` (düzeltmeler çalışma ağacında; commit edilmedi)
- Yöntem: **test-önce**. Her bulgu için önce regresyon yazıldı, RED gerçek koşuyla doğrulandı
  (`fix-regressions-red.log`, `ui-fix-red.log`), sonra ürün düzeltildi, GREEN aynı komutlarla alındı.
- **Before kanıtları korundu** (mtime `Oct 6 21:26–23:08`, md5 değişmedi):
  `probe-results-before.json` `fcb3fe0ac83f1b1ccca0b197ca2ce696` ·
  `import-probe-results-before.json` `357c25f5242faa9cc197adf8e9f092b1` · `ui-probe-before.json`.
  Düzeltme çıktıları ayrı adlarla yazıldı: `*-after.*`, `ui-fix-*.log/json/png`.

## Bulgu → düzeltme eşlemesi

### R01 — P1: Dikey ölçüde yön ters; parça geometrisi bozuluyor
- Düzeltme: `callout_compile.py` artık ekseni/yönü **paftanın kendi çerçevesinde** okuyor —
  `guided.view_transform` ile aynı çözücü (PLAN §8.6): `_view_axes()` + `_axis_tie(…, axes)`.
  Sayfa y'si aşağı, parça y'si yukarı; ham `dy` işareti yönü çeviriyordu, artık yön pafta ekseninden.
  Görüş yoksa/sağlam değilse eksen uydurulmaz: `view_not_confirmed` → hazırlıkta `missing_view` /
  `confirm_view` (açık karar).
- Kanıt (before → after): `probe-results-before.json` vertical_30mm yön `-1→+1` yanlıştı;
  `probe-results-after.json`: axis `y`, direction `-1`, plan bbox `[50.0, 30.0]`, ready ✓.
- Regresyon (7): compile — `test_a_vertical_tie_reads_the_sheets_own_y_axis`,
  `test_a_reversed_pair_flips_the_direction_not_the_axis`, `test_a_rotated_view_turns_the_tie_axis_with_the_sheet`,
  `test_a_record_without_a_vouchable_view_makes_the_axis_an_open_decision`;
  chain — `test_a_vertical_callout_tie_leaves_the_plan_upright`,
  `test_a_horizontal_callout_tie_is_the_untouched_control` (kontrol, kırmızıya düşmedi),
  `test_a_rotated_sheet_reads_the_tie_in_the_sheets_own_frame`.

### R02 — P1: İnç kör delik derinliği milimetreye dönüştürülmüyor
- Düzeltme: `callout_compile.py` derinliği çap ile **aynı çözülmüş birimden** çeviriyor
  (`_unit_factor` ortak); çevrim sonrası değer `guided.Hole`'un mm sınırına (`le=1e6`) karşı
  denetleniyor — aşarsa derleme zamanında açık ret (`unsupported_semantic`,
  `diameter_out_of_range` / `depth_out_of_range`), örtük model hatası değil.
- Kanıt: after vertical `printed_inch_depth` → `plan_depth_mm 6.35` (= beklenen), compiled hole
  `{diameter: 12.7, depth: 6.35, kind: pocket}`.
- Regresyon (5): `test_a_printed_inch_depth_is_converted_with_its_diameter`,
  `test_a_sheet_inch_depth_is_converted_too`, `test_a_printed_mm_depth_is_left_alone` (kontrol),
  `test_a_converted_hole_is_refused_when_it_breaks_the_models_own_bound`,
  + chain `test_a_printed_inch_blind_depth_reaches_the_plan_in_mm`,
  `test_a_sheet_inch_blind_depth_reaches_the_plan_in_mm`.

### R03 — P1: Vurgulanan öneri ile “Onayla”nın kaydettiği hedef farklı
- Düzeltme: `static/guided.js` — tek aktif öneri state'i: `highlightedProposal()` çizimde
  vurgulanan satırı, `activeProposal()` vurgulananı (yoksa ilkini) çözer; [Onayla] düğmesi
  `activeProposal()`ı yazar ve **etiket hangi öneriyi yazacağını söyler** (`Onayla · 2. öneri`);
  listeyle eşleşmeyen bayat vurgu `renderTarget` içinde temizlenir. Onay, yüklenmekte olan
  panelde eski (bayat) state'ten yazamaz; öneri yoksa düğme devre dışı + uyarı.
- Kanıt (gerçek Headless Chrome, gerçek tıklama; `ui_fix_regression.py`):
  `ui-fix-red.log` 4/7 — [Onayla] “Onayla” diyordu, vurgulanan `c1` iken kaydedilen `c0`;
  `ui-fix-after.log` 7/7 — düğme `Onayla · 2. öneri`, kaydedilen `{target_ids:["c1"], evidence:"T5 · c1"}`,
  reload özeti `… · c1`, konsol temiz (favicon 404 muaf tutuldu), ekran görüntüleri
  `ui-fix-red-*` / `ui-fix-after-*`.
- Regresyon: `test_guided_html.py::test_the_target_confirm_button_writes_the_proposal_the_panel_shows`
  (kaynak düzeyi) + tarayıcı koşusu (audit dizini, ürüne test yükü eklemez).

### R04 — P2: Parse hatası kullanıcıya eksik hedef gibi sunuluyor
- Düzeltme: `callout_compile.py` sıralaması — okuma, hedef kararından **önce** ve **sunucunun
  kendi parser sürümünden** (`CALLOUT_PARSER_VERSION`; eskiden hedefin sürümüne bağlıydı ve
  hedef yokken okuma hiç seçilemiyordu). Desteklenmeyen/ambiguous okuma artık `needs_target`
  değil `parse_error` sorusudur — store bu onayı zaten reddettiği için eski sıra çıkmaz sokağa
  gönderiyordu.
- Kanıt: after `unsupported` → kategori `{parse_error: 1}`, `confirmation_rejected_without_write: true`.
- Regresyon (4): `test_a_supported_reading_is_judged_before_a_missing_target`,
  `test_an_ambiguous_reading_is_judged_before_a_missing_target` (compile);
  chain `test_an_unsupported_reading_asks_for_a_text_edit_not_a_target`,
  `test_an_ambiguous_reading_asks_for_a_text_edit_not_a_target` (gerçek akış).

### R05 — P1: Eski dış inceleme paketi değişen geometriye güncel onay yazabiliyor
- Düzeltme: `callout_review.py` — dışa aktarmaya `geometry_key` eklendi; içe aktarma artık üç
  bağlam kapısından geçiriyor: `parser_version` eşitliği, `geometry_version` eşitliği ve
  **`geometry_key` eşitliği** (aynı sürümde içerik değişimi + `_migrated`'ın revision'sız
  geometri tazelemesi). Revision eşit olsa bile bağlam uyuşmuyorsa paket tamamıyla reddedilir.
- Kanıt: `import-probe-results-after.json` 3/3 — mevcut paket yazıyor + undo ✓;
  `obsolete_parser_header` → `parser_version_mismatch`, yazmadı ✓;
  `bundle_exported_before_geometry_migration` → `geometry_version_mismatch (3 ≠ 4)`,
  `base_revision_equal: true` iken reddedildi, yazmadı ✓.
- Regresyon (5): `test_the_bundle_carries_the_parser_and_geometry_context_it_was_reviewed_in`,
  `test_a_bundle_from_another_parser_or_geometry_context_is_refused` (review);
  chain `test_an_import_of_the_same_context_still_lands_and_undo_restores` (kontrol),
  `test_a_bundle_from_an_obsolete_parser_header_is_refused_whole`,
  `test_a_bundle_exported_before_a_geometry_migration_is_refused_whole`.

## Gerçek test sonuçları (after)

| Koşu | Dosya | Sonuç |
| --- | --- | --- |
| Yeni regresyon seti (RED) | `fix-regressions-red.log` | 20 failed, 121 passed (kırmızıların hepsi yeni) |
| Yeni regresyon seti (GREEN) | `fix-regressions-green.log` | **141 passed** |
| İncelemecinin odak seti (11 dosya, G3R) | `fix-focused-after.log` | **410 passed** (before: 385 passed + 2 ortam hatası; bu hostta yok) |
| Geniş yüzey seti (14 dosya) | `fix-extended-after.log` | **186 passed** (170.8 s) |
| İnceleme probu | `probe-results-after.json` | **6/6 case, exit 0** (before: exit 1) |
| Import probu | `import-probe-results-after.json` | **3/3 case, exit 0** (before: exit 1) |
| R03 tarayıcı (gerçek Chrome) | `ui-fix-after.log` + `ui-fix-steps-after.json` + PNG'ler | **7/7** (red: 4/7) |

Komutlar:
```
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_callout_compile.py tests/test_callout_review.py \
  tests/test_guided_callout_chain.py tests/test_guided_html.py tests/test_guided_callouts.py     # regresyon seti
PYTHONPATH=src .venv/bin/python -m pytest -q <incelemecinin 11 dosyası>                          # odak seti
PYTHONPATH="$HOME/.hermes/cache/scratch/cdp-venv/lib/python3.12/site-packages" .venv/bin/python \
  eval/audits/20261006-guided-g4-g8-independent-review/ui_fix_regression.py after               # tarayıcı
```

## Değişen dosyalar (çalışma ağacı)

```
src/drawingto3d/callout_compile.py      (R01/R02/R04 + view kapısı)
src/drawingto3d/callout_readiness.py    (view_not_confirmed → missing_view/confirm_view)
src/drawingto3d/callout_review.py       (R05: geometry_key + içe aktarma bağlam kapıları)
src/drawingto3d/static/guided.js        (R03: aktif öneri state'i + düğme etiketi)
tests/callout_fixtures.py               (fixture ürün şekline uyduruldu: sheet_frame/view)
tests/test_callout_compile.py           (+10 regresyon)
tests/test_callout_review.py            (+2 regresyon)
tests/test_guided_callout_chain.py      (+10 regresyon, store/akış düzeyi)
tests/test_guided_html.py               (+1 regresyon)
eval/audits/20261006-guided-g4-g8-independent-review/  (yeni kanıt + ui_fix_regression.py; before dosyalarına dokunulmadı)
```

## Kalan açıklar / notlar

1. **Commit yok** — düzeltmeler ve kanıtlar çalışma ağacında; inceleme dizini zaten untracked
   (inceleme turu da commit edilmemişti). İstenirse tek commit'te alınabilir.
2. **R03 kapsamı**: onay anı vurgu state'inden okunur; hiç vurgu yokken düğme ilk öneriyi yazar ve
   bunu etiketle söyler ("Onayla · 1. öneri"). Çizim vurgusu ile düğme aynı kaynaktan beslenir.
   Onay bekleyen istek (pending) sırasında bayat state'e yazma kapalı.
3. **R02 sınır kararı**: mm'ye çevrilen değer model sınırını (1e6 mm) aşarsa derleme açıkça
   `unsupported_semantic` der (`*_out_of_range`) — örtük model doğrulama hatası yerine okunur ret.
4. **Yeni kategori**: `view_not_confirmed` hazırlıkta `missing_view` + `confirm_view` eylemine
   eşlendi; mevcut `unsupported_semantic`/`unsupported_cad_feature` eşlemeleri değişmedi.
5. Semread bloğu (ağır, ~46 dk) bu turda çalıştırılmadı; odak + geniş set yeşil. Tam ağ koşusu
   istenirse ayrıca alınmalı.
6. `PLAN-17-HERMES.md` ve diğer kullanıcı dosyalarına dokunulmadı; before kanıtları değiştirilmedi.
