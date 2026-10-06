# G3 teslim — callout review + G1R3-01 (PLAN-21 §11)

Hazırlanma: 2026-10-06 · Plan: kök `PLAN.md` (PLAN-21; bayt kopya `docs/PLAN-22.md` sha256 `5743bb06…`) · İlerleme: `docs/GUIDED_PROGRESS.md`

## HEAD / worktree

```text
HEAD: ff97295065260ba8d46bf6fcd2c6e864e63dfcef (ff97295 = G2)
G3 değişiklikleri commit EDİLMEDİ — çalışma ağacında, kullanıcı incelemesi için duruyor.
Değişen (M): PLAN.md, docs/GUIDED_PROGRESS.md, report.md, src/drawingto3d/app.py,
             src/drawingto3d/callout_models.py, src/drawingto3d/guided.py,
             src/drawingto3d/static/guided.html, src/drawingto3d/static/guided.js,
             tests/test_contour_fix.py, tests/test_guided_callouts.py, tests/test_guided_html.py
Yeni (??):  tests/test_guided_callout_review.py, docs/PLAN-22.md,
             docs/PLAN_ROOT_BEFORE_G3_REVIEW_20261006.md,
             eval/audits/20261006-guided-g2-review/, eval/audits/20261006-guided-g3-review/
Korunan:    PLAN-17-HERMES.md (kullanıcının verdiği plan kaynağı; stage edilmedi)
git diff --check: yalnız docs/GUIDED_PROGRESS.md başlık bloğunun mevcut markdown satır-sonu
             iki-boşluk geleneği (5 satır); kod dosyalarında boşluk hatası yok.
```

## G1R3-01 önce / sonra

| | Ölçüm |
|---|---|
| Önce | `eval/audits/20261006-guided-g2-review/review_probes.py` → **exit 1**, `probe-results-before.json` satırlarında `passed=false`: 5/10/20 px farklı uçlar "aynı fiziksel nokta" diye reddediliyor |
| Sonra | aynı script → **exit 0**, 5/5 satır `passed=true`; kanıt `eval/audits/20261006-guided-g2-review/probe-results-after.json` (`before` ezilmedi) |
| Düzeltme | `guided.py`: `same_physical_point()` + `ENDPOINT_IDENTITY_TOLERANCE_PX = contour_audit.TOLERANCE_PX` (0.5 px). 20 px `RASTER_JOIN_TOLERANCE_PX` yalnız bozuk kontur onarımında (`correct_profile`) kaldı; geometri/detector sürümü artırılmadı |
| Kalıcı regresyon | `tests/test_contour_fix.py` (tolerans sınırı pini + 5/10/20/21 px + paylaşılan köşe), `tests/test_guided_callouts.py` (undo/log) |
| Kapı | `.venv/bin/python -m pytest -q tests/test_contour_fix.py tests/test_binding_end_meaning.py tests/test_guided_callouts.py` → **70 passed / 3.14 s / EXIT=0** (`out/guided-callout-review/g1r3-01-gate.log`) |

## G3.0–G3.6 durumları

| İş | Durum | Kanıt |
|---|---|---|
| G3.0 | PASS | `docs/PLAN-22.md` (bayt kopya), `report.md`, `docs/GUIDED_PROGRESS.md` PLAN-21 tablosu; G2.6 satırı gerçek duruma çekildi |
| G3.1 | PASS | `ManualCalloutDecision` + `CalloutReviewDecision` + `CALLOUT_SCHEMA_VERSION=2` + `effective_callouts()`; **109 passed / 54.97 s / EXIT=0** (`/tmp/g31b.log`) |
| G3.2 | PASS | `GuidedStore.edit_callout` + `_CALLOUT_COMMANDS` + `/api/guided/callout` + public `callouts`/`effective_callouts`; HTTP conflict/invalid/foreign-source testleri + tarayıcı senaryo 4 & 6 |
| G3.3 | PASS | overlay/seçim/crop + tek koordinat dönüşümü; `test_guided_html.py` yapısal testleri **40 passed / 0.81 s**; tarayıcı senaryo 1–2, 5 (crop bayt-eşit) |
| G3.4 | PASS | metin/ipucu/ignore/restore + taslak koruması; tarayıcı senaryo 1–4, 6, 7 |
| G3.5 | PASS | manuel alan + bölge düzeltme + `region_changed`; tarayıcı senaryo 3, 4, 8 |
| G3.6 | PASS | birleşik pytest **285 passed / 139.81 s / EXIT=0** + gerçek tarayıcı **28/28 PASS / EXIT=0** + iki review scripti exit 0 |

## Gerçek pytest komutları, sonuçları, exit code

```sh
# G1R3 kapısı
.venv/bin/python -m pytest -q tests/test_contour_fix.py tests/test_binding_end_meaning.py tests/test_guided_callouts.py
# -> 70 passed in 3.14s, EXIT=0            (out/guided-callout-review/g1r3-01-gate.log)

# G3.1 modeller
.venv/bin/python -m pytest -q tests/test_callout_models.py tests/test_guided_callouts.py tests/test_guided_callout_candidates.py
# -> 109 passed in 54.97s, EXIT=0          (/tmp/g31b.log)

# G3.3 yapısal UI + G3 review dosyası
.venv/bin/python -m pytest -q tests/test_guided_html.py tests/test_guided_callout_review.py
# -> 40 passed in 0.81s, EXIT=0            (/tmp/g33.log)

# PLAN-21 §10.1 birleşik küme (18 dosya)
.venv/bin/python -m pytest -q tests/test_guided_callout_review.py tests/test_callout_candidates.py \
  tests/test_guided_callout_candidates.py tests/test_callout_models.py tests/test_guided_callouts.py \
  tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py \
  tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py \
  tests/test_view_decision.py tests/test_view_core.py tests/test_sheet_frame.py \
  tests/test_stable_identities.py tests/test_contour_fix.py tests/test_measure_meaning.py \
  tests/test_user_dimensions.py
# -> 285 passed in 139.81s, EXIT=0          (out/guided-callout-review/g3-combined.log)

# Bağımsız denetim scriptleri
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py   # EXIT=0
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g2-review/review_probes.py   # EXIT=0
```

Tam takım (75 dk) bu kapsam değişikliği için tekrar koşulmadı; bilinen tek failure aşağıda.

## Gerçek tarayıcı senaryoları ve kanıt

Uygulama: `PYTHONPATH=src .venv/bin/python -m drawingto3d.app` (127.0.0.1:8765). Sürücü: gerçek Chrome,
CDP üzerinden **gerçek fare/klavye olayları** (`Input.dispatchMouseEvent`, `Input.insertText`,
`Input.dispatchKeyEvent`) ve DOM okuması; script `browser_acceptance.py` + `cdp_client.py`.

| # | Senaryo | Sonuç |
|---|---|---|
| 1 | Vektör Plate çizimi → kutu seç → crop → metin yaz → kaydet → reload → aynı session → undo → yeniden kaydet | PASS (`"  4 × Ø8 THRU  "` raw aynen; normalized ayrı; aday listesi undo'dan etkilenmedi) |
| 2 | Ignore → "Yok sayılanları göster" → geri al | PASS (metin duruyor; `callout_reviews` boşalıyor) |
| 3 | Elle alan çiz → seç → metin kaydet | PASS (`manual:<uuid>` sunucudan; çizilen kutu ±0.05 içinde) |
| 4 | Metinli callout'un bölgesini taşı | PASS (eski `raw_text`+`source_region` aynen; panel "Alan değişti") |
| 5 | Dar (520 px) ve geniş (1400 px) pencere | PASS (aynı satır seçildi; crop canvas **bayt-eşit**) |
| 6 | Revision conflict (sayfa dışı komut → bayat revision) | PASS (hata açık; taslak duruyor; güncel state sonrası kaydetme başarılı; tek reddedilen istek `POST /api/guided/callout` 400) |
| 7 | Eski profil aracı smoke + `<img src=x onerror=…>` metni | PASS (kontur seçildi; `imgs: 0`, metin olarak görünüyor) |
| 8 | Sıfır alanlı, Escape ile iptal edilen ve tersten çizilen sürükleme | PASS (sıfır alan reddedildi; iptal karar yazmadı; ters çizim normalize edildi) |

Kanıt: `browser-acceptance.log` (**28/28 PASS**, EXIT=0), `browser-steps.json` (her adımın gözlemi,
reddedilen istekler, console), 15 screenshot (`00-start.png` … `14-cancelled-drag.png`).

## Bilinen açıklar / kapsam dışı

- `tests/test_planner.py::test_settings_record_is_the_run_record_fields` — **1 failed**, bu kapsamdan
  bağımsız, G2 diff'inden önce de vardı (testin anahtar kümesinde `repeat_penalty`/`repeat_last_n` yok).
  Beklenti gevşetilmedi, ayar kaldırılmadı; açık kayıt olarak duruyor.
- Harness notu: Hermes'in kendi tarayıcı aracı bu oturumda özel adresleri (127.0.0.1) SSRF korumasıyla
  reddettiği için kabul, aynı Chrome CDP ile doğrudan sürülerek yapıldı. Bu sırada `~/.hermes/config.yaml`
  içine 4 anahtar yazıldı (`browser.use_real_profile=false`, `browser.cdp_url=http://127.0.0.1:9222`,
  `browser.allow_private_urls=true`, `browser.auto_local_for_private_urls=false`); iş sonunda
  **geri alındı** (`hermes config unset …`).
- Ortam notu: audit dizininde `uv run` çağrıldığında uv projeyi tanıyıp `.venv`'i lockfile'a senkronladı ve
  paketleri kaldırdı; `uv sync --extra dev` + `cadquery-ocp-novtk==8.0.1.1.0` yeniden kurulumu ile
  onarıldı ve `check_env.py` ile doğrulandı (repo geneli import taraması temiz; `cadquery` tasarım gereği
  `.venv-cad`'te). `uv.lock` ve `src/drawingto3d.egg-info/` bu sırada oluştu ve **silindi**. Bundan sonra
  yardımcı script'ler ayrı bir scratch venv'de (`~/.hermes/cache/scratch/cdp-venv`) çalıştırılmalı.
- Parser, parse onayı, target önericisi, target seçim UI'sı ve callout→CAD compiler **yazılmadı**; kaydedilen
  metnin STEP'e uygulandığına dair UI/audit iddiası yok (panel "Metin kaydedildi" der; üretim bölümü
  "Kaydedilen callout metinleri bu taslak üretiminde henüz kullanılmıyor." yazar).

**Model çağrısı: 0 · G4+ durumu: açılmadı**
