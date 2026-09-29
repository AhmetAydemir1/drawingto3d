# Önerilen adlar turu — ad sorunu kapandı, hata bir adım derine indi — 2026-09-27

> Güncel denetim: PLAN §21 ve `step-validation-audit.md`. İlk bildirilmemiş ad hatasının
> arkasında yanlış basılı değerler ve 7.82 ölçek/uzunluk karışıklığı da var. “Tek sınıf kaldı”
> yorumu geri çekildi; sonraki teslim uygulamanın oluşturduğu basılı parametre kataloğudur.
> Ham yanıtlar değiştirilmeden `latest-parameter-evidence.json` içine kaydedildi.

Bir önceki tur (`params-3b-01`) şunu ölçmüştü: kuralı kelimelerle söylemek yetmiyor, çünkü okuma bloğu
cevaba **kopyalayabileceği yasal bir ad** vermiyor; model ölçü kimliğini (`pdf-0`, `d2`) ad sanıyor.
Bu tur o boşluğu kapatıyor: her basılı sayının yanına, okumanın kendi `kind` alanından ve çapalarından
türeyen bir ad konuyor.

## Tek değişken, kanıtla

| | önceki tur | bu tur |
|---|---|---|
| etiket | `params-3b-01` | `suggest-3b-01` |
| `PROMPT_VERSION_SPLIT` | `general-plan-v5-split-parameter-rules` | `general-plan-v6-split-suggested-names` |
| parameters istem baytı (`relations` / `chain_model`) | — / `2aca1ef8ad9b…` | `f76b7707b97f…` / `0368f339b04e…` |
| kanıt bloğu (chain_model) | `0c1747f69ab9…` | **aynı baytlar** (`sha256` eşit) |
| plaka · model · ayarlar | `plate-pocket-1` · `qwen2.5vl:3b` · 16384/4096 · `--split` · sıcaklık 0 | aynı |

Kanıt bloğu (okuma) değişmedi; değişen, aynı okumanın isteme nasıl basıldığı. Koşu:
`eval/model_baseline.py --label suggest-3b-01 --cases plate-pocket-1 --conditions relations,chain_model
--split --num-ctx 16384 --predict 4096`.

## Ne eklendi (kod)

`src/drawingto3d/planner.py`, `_readings_line` içinde, "Printed numbers" bloğunun hemen ardından:

```
Names for those numbers (each derived from that reading's own kind and the anchors it was measured
between — copy one, or write your own CAD identifier):
[{"span_id":"pdf-0","kind":"linear","anchors":"circle+circle","axis":"x","name":"circle_spacing_x"}, …]
A span id is not a name and never belongs inside an expression: cite it in `span_ids`, and build a
derived expression out of the names you declare.
```

- `suggested_names(evidence)` (`SUGGESTED_NAMES_VERSION = "reading-derived-names-v1"`) her basılı sayı
  için bir ad üretir: `form`/`kind` (distance → `…_spacing`, diameter → `diameter`, radius → `radius`,
  angle → `angle`), çapa türleri (`circle-centre` → `circle`, `arc-rim` → `arc`, uç → `edge`) ve
  çapaların kendi ekseni (`|Δx| ≥ |Δy|` → `_x`, yoksa `_y`). Aynı biçimde ölçülen iki sayı
  indekslenir (`diameter_1`, `diameter_2`), yani hiçbir ad çıplak kalmaz ve adlar benzersizdir.
- **Şablon değil:** girdi yalnız okumanın kendi alanları (`kind`, `claims[].form`, `anchors[].kind`,
  `anchors[].point_mm`); dosya adı, parça ailesi, vaka kimliği okunmuyor. Bir test bunu çiviyor:
  bütün span ve geometri kimlikleri değiştirilse de önerilen adlar aynı kalıyor.
- İki arayüz de aynı bloğu basıyor (tek kelime kuralı), bu yüzden `PROMPT_VERSION` →
  `general-plan-v6-suggested-names`, `PROMPT_VERSION_SPLIT` → `general-plan-v6-split-suggested-names`.
  Koşu kaydı artık `settings.suggested_names` taşıyor.

## Ölçüm sonucu

`suggest-3b-01`: **46,12 sn, `complete`, iki koşul da `failed (planning)`, STEP yok** — ama ilk hata
**sınıf değiştirdi**:

| koşul | önceki ilk hata | bu turun ilk hatası | ham cevapta ne oldu |
|---|---|---|---|
| `chain_model` | `parametre adı küçük harfle başlamalı …: 'pdf-0'` | `ifadede tanımsız parametre: 'diameter_2'` | adlar **önerilen menüden** alındı (`circle_spacing_x`, `arc_spacing_y`, `circle_spacing_y`, `edge_spacing_x`, `edge_spacing_y`); 7 öneriden 5'i bildirildi, ifade bildirilmeyen `diameter_1`/`diameter_2`'yi kullanıyor |
| `relations` | `ifadede tanımsız parametre: 'd2'` | `ifadede tanımsız parametre: 'd1'` | menünün *üslubu* alındı (`distance_1`…`distance_7`) ama adlar birebir kopyalanmadı ve ifadeler yine ölçü kimlikleriyle yazıldı (`(d1 - d2) / 2`) |

Okuma: **"ad olarak ölçü kimliği" sorunu `chain_model`'de kapandı** — cevap artık okumanın kendi
ölçümünden türeyen adları kullanıyor. İki koşulun ilk hatası da artık aynı dar sınıfa indi:
**bildirilen parametre kümesi ile ifadede kullanılan adlar uyuşmuyor.** `relations`'ta menü zayıftı
(o kanıtın `claims` kayıtları `anchors` taşımıyor, yalnız `between` var; öneriler `distance_1…5` +
`diameter_1/2`), ve model menüyü birebir kopyalamak yerine kendi `distance_N` adlarını üretti.

Bu, projenin kendi kuralının ölçülmüş hâli: bir sınıf kapanınca hata **kaybolmaz, bir adım derine
iner** (bkz. `ids-3b-01`'de `relations`'ın ilk hatasının adım derine inmesi).

## Sınırlar (iddia edilmeyenler)

- Tek plaka, tek model, sıcaklık 0, tek koşu — kapasite ya da eğitim hükmü değil.
- Hiçbir plan geçmedi: **CAD inşası, çizim kontrolü ve ikinci parça grubu çalıştırılmadı; STEP yok.**
- Önerilen adların *anlamı* iddia edilmiyor: ad, ölçümün türünü ve eksenini söylüyor, hangi özelliğe
  ait olduğunu değil (`arc_spacing_y` = iki yay kenarı arasında dikey ölçü; paftada bu dış kontur
  yüksekliği). Model adı istediği gibi değiştirebilir; amaç yasal bir ad vermek.
- `pilot`/`hidden` hâlâ boş, yani kapsam depodaki örnekler.

## Sıradaki adım (ölçümün işaret ettiği)

Tek sınıf kaldı: **bildirilen küme ile ifadede kullanılan adlar**. Ölçümün doğrudan işaret ettiği
iki yol:

- **Menüyü yükümlülük yapmak:** blokta "aşağıdaki her satır için o adla bir `printed` parametre bildir"
  demek ve okumanın her basılı sayısı için bildirilmiş bir parametre beklemek (istem + adım denetimi).
  Ucuz; ama `relations` menüsü zayıf olduğu için orada tek başına yetmez.
- **Adımı okumanın ölçtüğü hedeflere göre bölmek** (basılı parametreler → türetilmişler), ki her çağrı
  yalnız kendi hedefini görsün ve ifade edebileceği ad kümesi *kapalı* olsun (profil adımında ölçülen
  desen: soruyu hedeflerine göre bölmek, kuralı tekrarlamaktan iyi çalıştı).

## Ham kanıt nerede

- `out/model-baseline/suggest-3b-01/` (`run.json`, `cases/plate-pocket-1-{relations,chain_model}-candidate.json`,
  `…-chain_model-evidence.json`), log `out/profile-step/suggest-3b-01.log`. `out/` Git dışıdır.
- Git içi tablo: `eval/reports/model-baseline.md` (`--write` ile bu koşudan üretildi, `--check` bağlıyor).

## Doğrulama

- `pytest -q` (tam paket): **358 geçti**, 251,22 sn (`out/profile-step/pytest-round4.txt`) — bu turda eklenen üç
  test: (1) önerilen adlar CAD kuralına uyuyor, benzersiz, hiçbiri ölçü kimliği değil ve blok iki
  arayüzde de "Printed numbers"tan sonra geliyor; (2) aynı biçimde ölçülen iki sayı indeksleniyor
  (`diameter_1`, `diameter_2`); (3) span ve geometri kimlikleri değiştirilince adlar aynı kalıyor.
- `eval/baseline_report.py --check` uyuşuyor (yeni satır `suggest-3b-01`), `eval/check_tables.py`
  20 satır / 0 kayma, `eval/profile_step_evidence.py --check` uyuşuyor, `git diff --check` temiz,
  `git diff src/drawingto3d/general.py` boş (kalıcı sözleşme, şema ve CAD doğrulaması değişmedi).
