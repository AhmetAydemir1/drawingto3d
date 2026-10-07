# 20261007-g12-decision-coverage — G12.1a kanıt demeti

Kapsam: **PLAN-24 §69 sırasının ilk ürün düzeltmesi** — false-readiness / karar kapsamı
(`PLAN.md` §10–§17). Bu tur yalnız **G12.1a (backend)**:

* `CalloutReviewDecision` **disposition sözleşmesi** (`CALLOUT_SCHEMA_VERSION` 3 → 4):
  `not_model_input` / `redundant (+ duplicate_of)` / `build_relevant_unsupported (+ disposition_reason)`;
* eski `ignored`/`unbindable` kayıtları **otomatik terfi etmez** → `legacy_unclassified` (§12);
* `callout_coverage(record)` — her etkin callout tek kovaya (§15); `coverage_issues` → `build_readiness`
  (§16): `legacy_unclassified`, `build_relevant_unsupported`, `invalid_duplicate` build'i kendi başına kapatır;
* komutlar: yeni `set_disposition` (dayanak çözülebilir olmak zorunda), `set_ignored` → `not_model_input`,
  `set_unbindable` → `build_relevant_unsupported` (artık **engel**, eski "açar" davranışı kaldırıldı),
  `bulk_set_ignored`/`set_ignored_many` yalnız `not_model_input` (§14), komşu düzenlemeler kararı düşürmez;
* dışa/içe aktarma: paket disposition'ı taşır; `set_disposition` import aksiyonu **aynı komuttan** geçer (§17).

## Kanıt

- `pytest-g12.1a.log` — 276 passed (coverage + disposition + HTTP + derleme/kayıt/panel ilgili süitler).
- Geniş regresyon: `630 passed in 151.89s` (callout/guided/plate/g11/g12/baseline/view) — bu turda koşuldu.
- Yeni testler: `tests/test_callout_coverage.py` (12), `tests/test_guided_disposition.py` (19),
  `tests/test_guided_callout_http.py::test_http_disposition_command_and_readiness_agree_over_the_boundary` (1).

## Değişen ürün davranışı (kasıtlı, §11)

1. „Bağlanamaz“ artık build'i **açmaz**: gerçek ölçü/not ise `build_relevant_unsupported` olarak kayda geçer
   ve kapsam kapanana kadar build bekler. (G11 koşusunun sahte hazırlığı tam buradan geliyordu.)
2. Toplu „yok say“ yalnız `not_model_input` yazar; gerçek ölçü asla toplu kararla kapsam dışına çıkmaz.
3. G11 öncesi kayıtlar (`ignored` bayrağı, adı konmamış) fresh bir doğruluk koşusunda **bloklar** —
   kullanıcı üç seçenekten birini yeniden verene kadar.

## Sınırlar

- UI kopyası/paneli ve koşucu politikası v2 → **G12.1b** (bu demette yok).
- `eval/guided_10_manifest.json`, `eval/guided_10_report.json` ve G9/G11 audit klasörleri **değiştirilmedi**
  (bayt pinleri `eval/audits/20261007-g12-baseline/run-01/frozen-evidence-sha256.txt`).
- Ana metrik paydası değişmedi: **GUIDED_CORRECT_STEP_RATE = 1/9**; bu tur bir ürün düzeltmesidir, koşu değil.

---

# G12.1b — UI kapsam sözleşmesi + koşucu v2

Bu bölüm G12.1a backend sözleşmesini **ürün yüzeyine** bağlar (PLAN-25 §8–§29): arayüz artık kendi
ikinci kapsam motorunu kurmaz, backend kovasından okur; üç kapsam kararı adıyla vardır; desteklenmeyen
satır çözülmüş sayılmaz ve build'i kapatır; G12 koşucusu blanket-ignore yapamaz.

## Kanıt

- `browser/README.md` + `browser/browser-acceptance.log` + `browser/g12-disposition-steps.json` —
  gerçek Chrome kabulü **10/10 PASS** (senaryo A–E; kararlar gerçek fare/klavye olayları).
- `pytest-g12.1b-focused.log` — §28 odak kümesi **78 passed / 6.52 s**.
- `pytest-broad.log` — `pytest -q tests -k "not semread"` (komut + sayılar + süre + exit kodu logun içinde).
- Yeni testler: `tests/test_guided_disposition_ui.py` (§20'nin sekiz davranışı, gerçek `guided.js`
  saplama DOM'da), `tests/test_g12_recipe_v2.py` (şema + blanket yasağı + ID disiplini + referans koruması).
- Ürün: `guided.py` (public state'te `coverage`), `callout_readiness.py` (§18 kopyası), `guided.html`
  (üç karar düğmesi, gerekçe kutusu, dayanak seçimi, `coverage-summary`), `guided.js`
  (`rowResolved`+`calloutList` kovadan; oto-ilerleme listesi; kapsam özeti), `eval/g12_runner/`
  (`recipe_v2.py` + `g12_runner.py`).

## Kasıtlı ürün değişiklikleri

1. “Modele uygulanmayacak” belirsizliği kalktı → üç adı konmuş karar (PLAN-25 §9/§10).
2. Legacy `set_unbindable` arayüzden **çağrılmıyor** (gerekçe kutusu + gerekçe zorunlu); backend
   uyumluluğu durur ama artık build'i açan bir yol değil (§10/§17).
3. Eski çıplak “yok sayıldı” bayrağı satırı **gizlemez ve çözmez** — `legacy_unclassified` olarak
   listede kalır ve kullanıcıdan yeni karar ister (§14).
4. Koşucu v2 reçetesi blanket alanları (`ignore_rest`, `bulk_remaining`, `ignore_all_unhandled`)
   **reddeder**; toplu karar yalnız açık ID listesiyle; reçetede vaka/dosya/hash sabiti taşınamaz (§24–§26).
