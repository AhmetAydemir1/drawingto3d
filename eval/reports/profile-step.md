# Profil adımı: ölçülen her kapalı profil için bir çağrı — PLAN Bölüm 20, sıradaki teslim (2026-09-27)

Bu rapor Bölüm 20'nin “sıradaki tek değişken profil adımı” teslimini kapatır. Önceki turun
ölçtüğü olay şuydu: profil adımı tek çağrıda tüm profilleri isterken yanıt kapanmıyor, çıktı
bütçesini (4 096 token, 178,47 sn) `radius_exprs_1d_array_2d_array_…` tekrarıyla dolduruyordu.
Bu turda tek değişken o adımdır: **profil adımı artık okumanın ölçtüğü her kapalı profil için
ayrı bir çağrı** yapar ve her alt yanıt, sonraki çağrı harcanmadan denetlenir. Ad kuralı, yanıt
şeması, kalıcı `GeneralPlan v1` sözleşmesi ve CAD doğrulaması değiştirilmedi.

Kanıt: `eval/reports/profile-step-evidence.json` (bu koşunun tam ham yanıtları, istem/şema
parmak izleri, süreler, doğrulama hataları, kaynak ölçümü); koşu klasörü
`out/model-baseline/profile-3b-01/`. Ham yanıtın tamamı ayrıca koşu klasöründe durur.

## Ne değişti

- `planner.profile_targets(evidence)`: okumanın ölçtüğü kapalı profiller — bir kapalı dış kontur
  döngüsü ve her kapalı daire — sırayla listelenir. Bu bir **okuma**dır, plan değil: yalnız hangi
  ölçülmüş bölgenin sorulduğunu söyler; ad, gövde, koordinat ve ifade modelin cevabıdır.
  Okuma hiçbir kapalı profil ölçmediyse liste boştur ve profil adımı eskisi gibi tek çağrıda
  tümünü ister.
- Profil çağrıları tek tek kaydedilir: `response_format` başlığı `…: profile i/K`, kayıtta
  `profile {index, count, kind, geometry_id}` ve `label` alanı (`profile 3/6 (g12)`). Bir adım
  düşerse hata o çağrıyı adıyla söyler: `adım profile 1/6 (outline): …`.
- Her alt yanıt sonraki çağrıdan önce aynı adım denetiminden geçer (yapı, ifade, birim, kapatma,
  bilinen başvurular, ölçü atıfları) ve tam olarak **bir** eskiz istediği de denetlenir
  (“tek kapalı profil istendi, N eskiz geldi”). Bir ad kardeş çağrıda kullanıldıysa yanıt
  reddedilir; ad uydurulmaz veya yeniden yazılmaz.
- Profil çağrısının çıktısı `PROFILE_PREDICT_CAP = 1024` ile sınırlanır (koşunun kendi sınırı
  tavan olarak kalır) ve sınır kayda yazılır: tek profil küçük bir cevaptır, döngü uzun bir
  düşünce değil. Kesilme (truncation) yine başarısızlıktır.
- İstem sürümü `general-plan-v3-split-profile`; yanıt şeması sürümü **aynı** kaldı
  (`GeneralPlan reply v4 split`) — bu turda değişen, sorulan sorudur, gramer değil.
  `step_reply_schema(step)` yalnız `title` parametresi kazandı (hangi profilin çağrısı olduğu
  kayda yazılabilsin diye); üretilen şema gövdesi eskisiyle aynıdır (`tests/test_planner.py`).
- Sağlayıcı sondası bu turda **tekrarlanmadı**: `eval/name_probe.py` ve
  `eval/reports/name-probe-evidence.json` önceki turun kaydıdır ve ölçülen kısıt
  (`pattern` dize alanında uygulanıyor, `propertyNames` uygulanmıyor) bu turda değişmedi.
  Aynı deneyi değişiklik yapmadan yeniden koşmak ölçüm üretmez.

## Koşu: `profile-3b-01`

Tek koşu, iki koşul, aynı plaka (`plate-pocket-1`), aynı 3B model, aynı ayar; yeni etiket.
Önceki turların etiketleri (`names-3b-02`…`names-3b-05`) korunur, hiçbir klasör taşınmadı.

```
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen2.5vl:3b \
  --conditions relations,chain_model --cases plate-pocket-1 \
  --num-ctx 16384 --predict 4096 --timeout 400 --split --label profile-3b-01
```

| koşul | durum | sınıf | koşu sn | ilk kalan hata |
| --- | --- | --- | --- | --- |
| `relations` | `failed` | planning | 19,16 | `adım parameters: parametre 'hole_spacing_x': kanıtta olmayan ölçü kaydına atıf ['h1', 'h2']` (ve `hole_spacing_y` için `['h1','h3']`) |
| `chain_model` | `failed` | planning | 42,45 | `adım profile 1/6 (outline): şema hatası: ifadede izin verilmeyen fonksiyon: 'x(6.84/2)'` |

Çağrı bazında (kayıttan):

| koşul | çağrı | kabul | sn | token | sınır | bitiş |
| --- | --- | --- | --- | --- | --- | --- |
| `relations` | `parameters` | hayır | 19,14 | 227 | 4096 | `stop` |
| `chain_model` | `parameters` | **evet** | 22,88 | 286 | 4096 | `stop` |
| `chain_model` | `profile 1/6 (outline)` | hayır | 17,85 | 129 | 1024 | `stop` |

Model: `qwen2.5vl:3b`, Q4_K_M, digest `fb90415c…`; soğuk başlangıç 5,55 sn, sıcak 0,22 sn;
koşu 67,54 sn'de `complete`. Kaynak ölçümü v2: kullanılan takas 8 356,94 → 10 338,50 MiB
(fark 1 981,6, tepe 10 383,44), boş sayfa en az 55,59 MiB, sıkıştırıcı tepe 5 837,42 MiB,
Ollama RSS tepe 3 829,2 MiB, 34 örnek / 2 sn. Sistem sayıları diğer uygulamaları içerir.
Koşu sırasında çalışma ağacı değişmedi: `out/profile-step/before.patch` ve `after.patch`
(index satırları dışında) farkı boş, `before.status` ≡ `after.status`.

## Ölçülen üç sonuç

1. **Döngü bitti.** Aynı adım önceki turda 4 096 tokanda `done_reason=length` ile kesiliyordu
   (178,47 sn, 7 743 bayt tekrar). Şimdi profil çağrısı 129 tokanda `stop` (17,85 sn, 280 bayt):
   tek profili sormak, kapanmayan gövdeyi kapatıyor. Bu, saymaya değer tek kazançtır ve
   **plan değildir**.
2. **Yeni kural tutuldu, cevap tutmadı.** `profile 1/6` yanıtı tam olarak bir eskiz ve geçerli
   bir ad (`profile_1`) taşıyor; çakışma veya fazla eskiz yok. Buna karşılık çizilen şey
   *sorulan bölge değil*: dış kontur yerine iki ilkel (bir çizgi + bir yay), yayın yarıçapı
   `x(6.84/2)` — ifadede izin verilmeyen fonksiyon. Koordinatlar bir *delik* dairesinin
   merkezinden (`-50.35, 30.21`), yarıçapta da o deliğin çapı (6.84) geçiyor; sorulan konturun
   ölçüleri 120,87 × 80,56 mm ve köşe yarıçapı 10,05 mm'ydi.
3. **İlk hata iki koşulda iki ayrı yerde.** `relations` (elle doğrulanmış kanıt) bu turda
   **parameters** adımında durdu: model, basılı ölçünün `span_ids` alanına *çizilmiş dairenin*
   kimliğini (`h1`, `h2`) yazdı — kanıt tablosunun basılı sayı kimlikleri `d1`…`d7`. Aynı yanıt
   ölçülen değeri (100,71) “basılı” olarak verirken tablo 100,00 yazıyor.

### `relations` hatası yeni bir arayüz hatası değil

Bu koşunun `parameters` isteminin parmak izi `01e0bc397f36…`, önceki turun `names-3b-05`
koşusundakiyle **bayt-aynı**; yanıt metni de bire bir aynı (sıcaklık 0). Değişen tek şey
hükümdür: o koşuda adım “kabul” sayılmıştı, şimdi aynı yanıt ölçü atfı denetiminden geçmiyor.
Yani bu bir model/arayüz değişikliği değil, çalışma ağacındaki **doğrulayıcı** farkıdır;
önceki turun çevrimdışı replay kaydı (`eval/reports/step-validation-replay.json`,
`first_prompt_unchanged: true`, `first_schema_unchanged: true`) tam bu hükmü vermişti ve bu
koşu onu canlı doğruladı.

## Ham yanıtlardaki diğer sorunlar

`chain_model` `parameters` adımı **kabul edildi** — arayüz kuralları (yapı, birim, kaynak, atıf)
geçti — ama içerik parçayı kuramaz:

- `hole_spacing_y`: `derived`, `expr (100 - 80) / 2` = 10 mm; pafta 60,00 yazıyor, okuma 60,43
  ölçmüş. İfade hiçbir parametre adı kullanmıyor, yalnız literal aritmetik; üstelik `pdf-0`,
  `pdf-1` atıflarını taşıyor.
- `diameter_60_mm`: `derived`, `(15 + 8) / 2` = 11,5 mm — paftada olmayan üçüncü bir çap.
- `pocket_depth`: `assumed` 7,82 mm, gerekçe “sayfanın genişliği piksel yoğunluğuna bölünür”
  — px/mm ölçek bir uzunluk gibi kullanılmış.
- `hole_radius_x`, `hole_radius_y`: iki ayrı `assumed` 3,4 mm yarıçap; pafta çapı bir kez yazar.
- **`thickness` hiç yok**: bu parametrelerle mükemmel profiller de olsa katı kurulamazdı.
- `relations` yanıtında ayrıca `corner_radius` `(80 - 60)/2` ile türetiliyor ve `pocket_depth`
  15,0 varsayılıyor (15 basılı *kalınlıktır*) — aynı sınıf karışıklık.

Bu maddelerin hiçbiri “geçerli JSON” olarak başarı sayılmaz; ham yanıt koşu klasöründe duruyor.

## Sonraki tek karar

Ölçülen iki ilk hatanın ortak yüzü şudur: yanıt, okumanın kendi ad alanlarını ve bölgelerini
birbirine karıştırıyor — `relations` hatası bunun saf hâli (çizilmiş daire kimliği, basılı ölçü
kimliğinin yerine yazıldı), `chain_model` hatası ise aynı karışıklığın geometride görünüşü
(kontur çağrısına deliğin merkezi ve çapı). Bu yüzden sıradaki **tek değişiklik** istemde
kanıt bloğunun yapısını ayırmalıdır, başka hiçbir şeyi değil:

1. Kanıt bloğunu iki ayrı, adı konmuş başlık altında ver: “basılı sayılar — `span_ids` yalnız
   bunlara atıf yapar” ve “ölçülen bölgeler — bu kimlikler geometriyi adlandırır, atıf değildir”,
   ayrıca her profil çağrısının bölgesi kendi yapısal anahtarında dursun (cümle içinde değil).
   Şema, ad kuralı, kalıcı sözleşme ve soru sayısı aynı kalır; yeni etiketle bir kez ölçülür.
2. Bu yetmezse (yani `parameters` adımı yine literal aritmetikle sayı uydurursa) sıradaki tek
   kural: *türetilmiş* bir parametre kabul edilmiş parametre adlarını kullanmak zorundadır ve
   basılı ölçüye atıf yapamaz. `(100 - 80) / 2` ve `(15 + 8) / 2` bu kuralla durur; bugünkü
   koşuda ikisi de kabul edildi.

Bu karar, “model şu derinlikte düşüyor” gibi bir hüküm değildir; tek bir arayüz
belirsizliğinin ölçülmüş hatasıdır. Eğitim kararı için gereken ayrı doğrulama verisi ve
arayüzden ayrılmış tekrarlanan görev hatası hâlâ yoktur (PLAN Bölüm 18C).

## Bu koşunun ölçmediği şeyler

- **STEP yok.** İki koşul da geçersiz plan verdi; CAD üretimi, `plan-audit` ve çizim kontrolü
  bu turda çalıştırılmadı, çalıştırılacak bir plan da yoktu.
- **İkinci parça grubu ölçülmedi.** Geçerli plan çıkmadığı için farklı parça grubunda ölçüm
  yapılmadı; bu bir eksik değil, koşulun kendisidir.
- **Kapasite/eğitim hükmü yok.** Tek pafta, tek model, tek sıcaklık-0 koşusu kapasite hükmü
  değildir; eğitim bu turda da yapılmadı, yeni ağırlık indirilmedi.
- **Üç adımlı arayüz `relations` koşulunda profile hiç ulaşmadı** (parameters adımında durdu):
  per-profile adımın elle doğrulanmış kanıtla davranışı bu turda ölçülmedi, yalnız ürün yolunda
  (`chain_model`) ölçüldü.

## Doğrulama

- `pytest -q`: **352 geçti** (231,55 sn); altısı bu turda eklenen `tests/test_profile_step_evidence.py`.
- `eval/profile_step_evidence.py --check`: kanıt paketi koşu kayıtlarından yeniden üretilip
  karşılaştırılıyor; içindeki çevrimdışı replay kayıtlı hatayı bire bir vermezse kontrol geçmiyor
  (bu turda `verbatim_matches_record: true`).
- `eval/baseline_report.py --check`: rapor tabloları koşu kayıtlarıyla uyuşuyor (yeni satırı
  arayüzü `adım başına profil` olarak ayırır; eski `üç adımlı` sayılarla karıştırılamaz).
- `eval/check_tables.py`: `eval/README.md` tabloları `out/frontend` ile uyuşuyor — 20 satır okundu,
  0 satır kaymayla tutmuyor.
- `eval/plate_plan.py`: geçti (plaka paftası hâlâ aileden bağımsız STEP üretiyor).
- `git diff --check`: boş (boşluk hatası yok). `git diff src/drawingto3d/general.py`: boş — kalıcı
  sözleşme ve CAD doğrulaması değişmedi.
- Ham yanıtlar ve ayarlar `eval/reports/profile-step-evidence.json` içinde Git’e alınmıştır;
  büyük yerel çıktılar `out/model-baseline/profile-3b-01/` altındadır ve `out/` Git dışıdır.
