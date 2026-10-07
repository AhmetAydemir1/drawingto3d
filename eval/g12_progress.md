# G12 ilerleme raporu — PLAN-24-G12-CORRECTNESS

Ana metrik (G11 baseline, değişmez payda): **GUIDED_CORRECT_STEP_RATE = 1/9** (correct: `plate-pocket-vector`).
Sayaçlar (§75/§76): correct 1 · wrong 5 · blocked 3 (üretilmedi) · scope-only 1 (geometri iddiası yok).

| faz | durum | not |
|---|---|---|
| G12.0 truth lock / baseline | **DONE** | pinler + G9 guard PASS + 540 passed + süreç sınırı |
| G12.1a false readiness (backend) | **DONE** | disposition sözleşmesi (şema 4) + `callout_coverage` + `set_disposition` + 631 passed |
| G12.1b coverage UI + runner v2 | **DONE** | üç adı konmuş karar + gerekçe/dayanak akışı + kapsam otoritesi backend'de; gerçek Chrome 10/10; koşucu v2 blanket-ignore'suz |
| G12.2 build strategy contract | **DONE** | örtük extrude kaldırıldı; açık strateji kararı + panel + kategoriler; taze Plate kabulü 10/10 |
| G12.3 view-scoped geometry foundation | bekliyor | view sahipliği + `GEOMETRY_VERSION 3→4` (PLAN-25 §45–§54) |
| G12.4 exact supported 2D constraints | bekliyor | desteklenen kısıtların tam uygulanması (PLAN-25 §55+) |
| G12.5 raster extrude recovery | bekliyor | raster yoldan profil + ölçü kurtarma |
| G12.6 axisymmetric / revolve | bekliyor | `compile_revolve_plan` gerçek geometri |
| G12.7 multi-view composite v1 | bekliyor | görünüş grafiği + özellik bağlama |
| G12.8 advanced bounded operation audit | bekliyor | capability-gap.json |
| G12.9 frozen manifest rerun | bekliyor | 9/9 + 1/1 scope-only |

> Not: PLAN-24'ün kalan faz adları PLAN-25 (kullanıcı girdisi `PLAN-21.md`, §45+) ile yeniden
> sıralandı; yukarıdaki satırlar artık YÜRÜRLÜKTEKİ planın numaralandırmasıdır.

## G12.0 kanıt demeti

- `eval/audits/20261007-g12-baseline/run-01/git-facts.txt` — HEAD `cc36f8de…` beklenen.
- `…/frozen-evidence-sha256.txt` — G9/G11/G11R kanıtı + üç donmuş dosyanın sha256'sı (değişmedi).
- `…/plate-regression-verdict.json` — dondurulmuş evaluator **PASS** (9/9 kontrol; bbox [120.011, 80.002, 15.0]).
- `…/pytest-relevant.log` — ilgili süit **540 passed** (189.20 s).
- `…/pytest-g12-guards.log` — yeni pinler **9 passed**.
- `tests/test_g12_baseline_contract.py` — manifest 10/9/1 + rapor 1/9 + dosya bayt pinleri.
- `tests/test_g12_runner_boundary.py` — üretici beyaz listesi, env/argv/girdi referans denetimi,
  ürün kaynağında vaka/referans sabiti taraması (§83/§84'ün G12.0 sürümü).
- `eval/g12_runner/{producer_input,produce_case,evaluate_case}.py` — §8 süreç ayrımı.

## G12.1a kanıt demeti

- `eval/audits/20261007-g12-decision-coverage/README.md` — kapsam, kasıtlı davranış değişikliği, sınırlar.
- `…/pytest-g12.1a.log` — 276 passed; geniş regresyon 630 passed (callout/guided/plate/g11/g12/view).
- `tests/test_callout_coverage.py` — §17 matrisinin saf katmanı (12 test): claim/blok/dayanak/eski kayıt.
- `tests/test_guided_disposition.py` — komut + kayıt yolu (19 test): `set_disposition`, eski düğmelerin yeni
  anlamı, toplu karar, undo/revizyon, export/import, legacy kilidi.
- Ürün: `callout_models` (şema 4 + disposition alanları), `callout_compile` (adı konmuş dışlama),
  `callout_readiness` (`callout_coverage` + `coverage_issues`), `guided` (`set_disposition` + toplu kurallar),
  `callout_review` (paket + import aksiyonu).

## G12.1b kanıt demeti (UI kapsam sözleşmesi + koşucu v2)

- `eval/audits/20261007-g12-decision-coverage/browser/README.md` — gerçek Chrome kabulü, senaryo A–E;
  `browser-acceptance.log` + `g12-disposition-steps.json` **10/10 PASS** (kararlar gerçek fare/klavye).
- `…/pytest-g12.1b-focused.log` — §28 odak kümesi **78 passed / 6.57 s**; genişletilmiş küme (yeni
  dosyalar dahil) **198 passed / 8.07 s**; ikisi de EXIT=0.
- `…/pytest-broad.log` — §98 geniş regresyon `pytest -q tests -k "not semread"`: **1527 passed · 0 failed ·
  339 deselected · 1504.78 s (25:04) · EXIT=0** (07.10.2026 18:34→18:59; §5: tek yetkili sayı).
- `tests/test_guided_disposition_ui.py` — §20'nin sekiz davranışı gerçek `guided.js` üzerinde (saplama DOM):
  desteklenmeyen çözülmez/zıplanmaz, `not_model_input` ve geçerli `redundant` çözer, geçersiz dayanak
  ve eski kayıt çözülmez, “Sonraki eksik” bloklara uğrar, özet backend sayılarından, checklist seçer.
- `tests/test_g12_recipe_v2.py` — koşucu v2: şema doğrulaması, blanket alanların reddi (`ignore_rest`,
  `bulk_remaining`, `ignore_all_unhandled`), toplu kararın açık ID listesi şartı, gerekçe/dayanak
  zorunluluğu, referans/STEP yolu yasağı, “kalanları kendiliğinden kapatmama” koşum kanıtı.
- Ürün: `guided.py` (public state `coverage`), `callout_readiness.py` (§18 kategorı kopyası),
  `guided.html`/`guided.js` (üç karar, gerekçe, dayanak, özet; `rowResolved` + liste kovadan),
  `eval/g12_runner/recipe_v2.py`, `eval/g12_runner/g12_runner.py`.
- Tarihsel kanıt değişmedi: G9/G11 klasörleri ve `eval/guided_10_*` dosyalarına dokunulmadı; ana metrik
  paydası hâlâ **1/9** (bu tur karar değil, sözleşme turu).

## G12.2 kanıt demeti (açık üretim biçimi)

- `eval/audits/20261007-g12-strategy-plate/README.md` — taze Plate kabulü **10/10 PASS**:
  callout incelemesi (reçete 9 satır + reçete dışı 36 satır tek tek adıyla) → kapsam kapanır →
  strateji yokken üretim reddedilir → `extrude_profile` onayı (sunucu anahtarı/sürümü sabitler) →
  üretim → STEP reopen → **dondurulmuş evaluator 9/9 PASS**; parça 120 × 80 × 15, 4 delik, 1 cep.
- `src/drawingto3d/build_strategy.py` — öneri + tazeleme + soru cümlesi (saf modül, referanssız).
- `guided.py` — `Decisions.build_strategy`, `set_strategy` komutu, `/save` sahte strateji reddi,
  `make_plan` = ortak bağlam + explicit dispatch (`compile_extrude_plan` / `compile_revolve_plan` /
  `compile_multiview_plan`); **örtük extrude yok**, daire profili açık onayla ekstrüde edilir.
- Readiness kategorileri: `missing_build_strategy`, `stale_build_strategy`, `unsupported_build_strategy`;
  panel + kontrol listesi maddesi (§41/§42).
- Gerçek Chrome (UX değişti, §97/8): `browser/` — hazırlık listesi strateji maddesi, dört seçenek
  (döndürme/çok görünüş seçilemez), karar yokken üretim kapalı, kaydetme gövdesi yalnız
  `{token, revision, kind}`, karar sonrası tıklamayla üretim → **7/7 PASS**.
- Testler: `tests/test_build_strategy.py` (11) · `tests/test_guided_strategy_ui.py` (5) · ilgili süit
  **401 passed (129,80 s)**; geniş `pytest -q tests -k "not semread"` → **1543 passed, 339 deselected,
  1637,22 s (27:17), EXIT=0** — `eval/audits/20261007-g12-strategy-plate/pytest-broad.log`
  (1527 → 1543: +11 build_strategy, +5 strateji UI).

## Kural hatırlatması (her faz sonu, §96)

Case/file/hash dallanması yok · evaluator değeri producer'a kopyalanmaz · gerçek ölçü "gereksiz" diye
işaretlenmez · implicit extrude/revolve yok · tolerans geçirmek için genişletilmez · tarihsel kanıt
değiştirilmez · manifest değişmez · tekil örnek tek regresyon olamaz.
