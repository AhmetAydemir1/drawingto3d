# Parametre kuralı turu — kuralı söylemek yetmedi — 2026-09-27

Bu rapor PLAN.md Bölüm 20'nin "sıradaki tek karar" turudur: bir önceki turda (`ids-3b-01`) iki koşulun
da takıldığı **parameters adımı** için, yargıcın zaten uyguladığı iki kuralı istemde açıkça söylemek.
Sonuç **negatif** ve bu dosya nedenini kaydediyor.

## Tek değişken, kanıtla

| | önceki tur | bu tur |
|---|---|---|
| etiket | `ids-3b-01` | `params-3b-01` |
| `PROMPT_VERSION_SPLIT` | `general-plan-v4-split-profile-ids` | `general-plan-v5-split-parameter-rules` |
| parameters adımı istem baytı (chain_model) | `aad74cd98422…` | `2aca1ef8ad9b…` |
| kanıt bloğu (chain_model) | `0c1747f69ab9…` | **aynı baytlar** (`sha256` eşit) |
| plaka · model · ayarlar | `plate-pocket-1` · `qwen2.5vl:3b` · 16384/4096 · `--split` · sıcaklık 0 | aynı |

Yani tek değişen şey sorunun kendisi: kanıt, model, ayar ve koşul kümesi sabit. Koşu komutu
`eval/model_baseline.py --label params-3b-01 --cases plate-pocket-1 --conditions relations,chain_model
--split --num-ctx 16384 --predict 4096`.

## Eklenen iki kural (kod)

`src/drawingto3d/planner.py` — yargıcın denetimleri (`evaluate_parameters`,
`_check_parameter_citations`) **değişmedi**; aynı iki kural kelimeye çevrildi ve iki istemde de
alıntılandı (`plan_prompt` ve `step_prompt("parameters", …)`), çünkü ikisi de parametre istiyor:

- `_RULE_EXPRESSIONS_USE_PARAMETERS` — türetilmiş ifade yalnız **bildirilen parametre adları** üzerinde
  aritmetiktir; ölçü kimliği (span id) atıftır, ad değildir (`hole_spacing_x / 2`, `(d2 - d4) / 2` değil).
- `_RULE_PRINTED_CARRIES_ITS_VALUE` — `printed` parametre, atıf yaptığı ölçünün yazdığı sayıyı (ya da
  yanındaki `4 x` adedini, `unit: "count"`) taşır; kendi aritmetiğin `derived`'dır.

Bir bölüm **bilerek dışarıda bırakıldı**: "parametreler dokundukları özelliğe göre gruplansın
(7 basılı sayı → 7 parametre değil)" fikri ölçülmemiş bir tasarım hipotezidir; aynı isteme konsaydı
bu koşu iki değişkenli olurdu.

## Ölçüm sonucu

`params-3b-01`: **53,69 sn, `complete`, iki koşul da `failed (planning)`, STEP yok.**

| koşul | ilk hata (parameters adımı) | önceki turdaki karşılığı |
|---|---|---|
| `relations` | `şema hatası: ifadede tanımsız parametre: 'd7'` | `… tanımsız parametre: 'd2'` |
| `chain_model` | `şema hatası: parametre adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'pdf-0'` | aynı hata, aynı kimlik |

İki koşulun ilk hatası **sınıf olarak aynı kaldı**: model, okumanın *basılı ölçü kimliğini* bir
tanımlayıcı sanıp ifadeye ya da parametre adına koyuyor. Kuralı kelimelerle söylemek bu sınıfı
kapatmadı.

`chain_model` satırı ayrıca şunu söylüyor: **ad kuralı bu turdan önce de istemde vardı**
(`_RULE_CAD_NAMES`, v4) ve yine çiğnendi. Yani bu bir "unutulan kural" değil; modelin önünde, okumanın
kimlik uzayından başka, kopyalayabileceği *yasal bir ad* yok. Bu, bu makinede ölçülmüş iki sonuçla
uyumlu: bir JSON-Schema grameri açık anahtar kümelerini kısıtlayamıyor (nesne `propertyNames`
yok sayılıyor; `pattern` yalnız *string* alanda tutuyor) ve isim adaptörü açıkken aynı cevap
`chain_model` adımından geçiyordu — yani engel ad kuralının kendisi değil, adı modelin üretmesi.

## Sınırlar (iddia edilmeyenler)

- Tek plaka (`plate-pocket-1`), tek model (`qwen2.5vl:3b`), sıcaklık 0, tek koşu: bu bir kapasite ya da
  eğitim hükmü değildir.
- Hiçbir plan geçmedi → **CAD inşası, çizim kontrolü ve ikinci parça grubu çalıştırılmadı; STEP yok.**
- Kapsam hâlâ depodaki örnekler: `pilot`/`hidden` boş.

## Ham kanıt nerede

- Koşu kayıtları ve ham cevaplar: `out/model-baseline/params-3b-01/` (`run.json`,
  `cases/plate-pocket-1-{relations,chain_model}-candidate.json`, `…-chain_model-evidence.json`),
  log `out/profile-step/params-3b-01.log`. `out/` Git dışıdır.
- Git içi tablolar: `eval/reports/model-baseline.md` (`--write` ile bu koşudan üretildi,
  `--check` kayıtlara bağlıyor).
- Önceki turun ayrıntılı kanıt paketi (`eval/reports/profile-step-evidence.json`) hâlâ
  `profile-3b-01` ölçümünü belgeler; bu turun ham cevabı için karşılığı yok, yukarıdaki dosyalar geçerli.

## Doğrulama

- `pytest -q` (tam paket): **355 geçti**, 230,35 sn (`out/profile-step/pytest-round3.txt`) — bu turda
  eklenen: `_RULE_*` iki istemde (mevcut "tek kelime, iki arayüz" testi genişletildi) ve ölçülen
  arızanın şekli (`expr: "(d2 - d4) / 2"` → `tanımsız parametre`) parametrik test satırı.
- `eval/baseline_report.py --check` uyuşuyor (yeni satır `params-3b-01`), `eval/check_tables.py`
  20 satır / 0 kayma, `eval/profile_step_evidence.py --check` uyuşuyor, `git diff --check` temiz.
- `git diff src/drawingto3d/general.py` boş: kalıcı plan sözleşmesi, şema ve CAD doğrulaması
  değişmedi.
