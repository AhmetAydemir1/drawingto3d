# Genel girdi dilimleri: döngü kurma, ikinci arketipin kapısı, raster ölçeği, kanıt kimlikleri

Bu tur `PLAN.md` Bölüm 20'nin "sonraki adımlar" zincirini ölçer. Dört adımın üçü kod değişikliği,
biri kararlaştırılmış tek model koşusu; her biri tek değişken ve kayıtlı bir sonuçla kapanıyor.
Hiçbir adım "genel girdi çalışıyor" iddiası taşımıyor — ölçülen paftalar depodaki örneklerdir.

## 1. Kapalı döngü kurma: detay görünüşünü parça sanmayı kapatan düzeltme (uygulandı)

`proposal._loops` (şimdi `src/drawingto3d/proposal.py:81`) zincir kurarken üç kural kullanıyor:

1. zincirin başlangıcına dönen bir segment varsa o alınır (çizimin kendi konturu kapalı bir koşudur),
2. yoksa en az dönen devam alınır (kontur pürüzsüz gider, ölçü/uzatma çizgisi açıyla ayrılır),
3. çıkmaza giren zincir hiçbir segmenti sahiplenmez; segmentler havuza döner.

Üçüncü kural ölçümün kendisi: eski kod zincire eklediği segmenti "tüketilmiş" sayıyordu, ilk çıkmaz
sokak parçanın kendi kenarlarını yiyordu. `Drawing.pdf` (239 çizgi) eski kodda **3 döngü** veriyordu
ve parça konturu bu üçünün içinde değildi; yeni kodda **7 döngü** var ve seçilen döngü
**8 ilkel, 53,62 × 82,29 mm, kendisine bağlı R20 (`pdf-13`)** — paftanın parça konturu.

Ölçüm (`eval/loop_candidates.py`, modelsiz):

| pafta | döngü (önce → sonra) | seçilen döngü | kendine bağlı ölçü |
|---|---|---|---|
| `plate-pocket-1` | 3 → 5 | #1, 8 ilkel, 120,87 × 80,56 mm, yuvarlatılmış dikdörtgen | `pdf-1` = 80,00 |
| `plastic-enclosure-1` | 30 → 32 | #2, 8 ilkel, 121,49 × 61,17 mm, yuvarlatılmış dikdörtgen | yok (0) |
| `exercise-1-vector` | 3 → 7 | #2, 8 ilkel, 53,62 × 82,29 mm | `pdf-13` = R20 |

Plaka planı **değişmedi**: `propose` hâlâ `proposed`, `eval/plate_plan.py` geçiyor, plaka ölçüleri
(120,87 × 80,56 mm, R10,05, Ø6,85, kalınlık 15,00) aynı. İki yeni test bunu çiviliyor:
`tests/test_proposal.py::test_loop_chaining_keeps_a_run_a_dead_end_would_have_eaten` ve
`::test_loop_chaining_takes_the_closing_segment_over_a_straighter_continuation`.

## 2. İkinci arketip: bugün ateşlenemez, ve nedeni ölçüldü (kod yazılmadı)

Sorulan adım "`propose`'a ikinci arketip (serbest kapalı profil + basılı kalınlık)" idi. Seçilen
döngü için adaylar (`eval/loop_candidates.py`, koşu kaydı `out/profile-step/section-candidates.txt`):

| pafta | kontur ölçüleri bağlı mı? | kesit adayı (kalınlık olacak uzaklık) |
|---|---|---|
| `plate-pocket-1` | 1/2 (`pdf-1` = 80,00) | **2** (`pdf-5` = 15,00, `pdf-6` = 8,00) |
| `plastic-enclosure-1` | 0/2 | **4** (`pdf-0` = 25,00, `pdf-2` = R8, `pdf-3` = 46,00, `pdf-7` = 18,00) |
| `exercise-1-vector` | 0/2 (`pdf-13` = R20 bir köşe yarıçapı, ölçü değil) | **10** (80, 60, 35, 57, 37, 20, 26, 40, 20, 40) |

Bir serbest-kontur arketipinin dürüst kapısı şu olurdu: konturun kendi en/boy ölçüleri basılı bir
ölçüyle onaylanmış, ve geriye **tek** kesit uzaklığı kalmış. Üç paftanın **hiçbiri** bu kapıdan
geçmiyor: plastic ve `Drawing.pdf`'te konturun hiçbir ölçüsü kendi konturuna bağlı değil (bağlama
eksik), plakada iki, diğerlerinde dört ve on kesit adayı var (kalınlık belirsiz). Bu yüzden bugün
yazılacak arketip hiçbir ölçülmüş paftada ateşlenmezdi; kanıtsız kod yazmak yerine kapı ve gerekçesi
kayda geçti. Bağlamayı iyileştirmek (kontur ölçülerinin döngüye bağlanması) bu adımın ön koşulu.

## 3. Raster ölçeği: yol bağlanan ölçülerden kuruyor, sonda onu bağımsız doğruluyor (ölçüldü)

Önce düzeltme: geçen turun `eval/reports/general-input-status.md` tablosu yedi rasterin hepsi için
`pafta ölçeği okunamadı (kalibrasyon yok)` yazıyordu. Bu tur aynı paftaları doğrudan ölçtü ve bu
satırları doğrulayamadı (`out/profile-step/general-sweep.txt`): `meaning_page` üç rasterde ölçek
kuruyor, çünkü `bind` bağladığı birkaç ölçüden `scale.audit` ile kalibre ediyor. Raster okuma yolu
bu turda değişmedi (`bind.py` 01:58, `meaning.py` 01:58, `raster.py` 02:46 — geçen turun
süpürmesinden önce), dolayısıyla eski satırların kaynağı belirsiz; geçerli ölçüm bugünküdür.

| pafta | onaylı/çözümlenemeyen ölçü | px/mm | ilk ret (ölçülen) |
|---|---|---|---|
| `exercise-1` (`my_part.jpg`) | 3 / 15 | **5,73** | `kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor)` |
| `exercise-51` | 0 / 13 | yok | `pafta ölçeği okunamadı (kalibrasyon yok)` (ölçüldü) |
| `exercise-17` | 0 / 2 | yok | ölçek reddi (kod sırası: `proposal.py:323`) |
| `exercise-13` | 4 / 14 | **2,88** | ölçülmedi |
| `studycadcam-60` | 5 / 18 | **3,28** | `kapalı dış kontur bulunamadı (sayfa çerçevesi dışında döngü yok)` (ölçüldü) |
| `studycadcam-50` | 0 / 9 | yok | ölçek reddi (aynı düzen) |
| `flange-1` | 0 / 10 (`no-scale`) | yok | `pafta ölçeği okunamadı (kalibrasyon yok)` (ölçüldü) |

`px/mm = yok` satırlarında ret gerekçesi *kod sırasından* bellidir (`read_sheet` önce ölçeği,
sonra konturu sorar), ama bu turda koşuyla yazdırılmadı; "ölçüldü" ile karıştırılmamalı.

Yeni sonda `eval/raster_scale.py` (modelsiz; `out/profile-step/raster-scale.txt`) sayı–çizgi
oranlarını `scale.consensus`'a veriyor, sayfa köşegeni ve "en az 3 farklı sayı" koşuluyla
hipotezleri eliyor:

- **`studycadcam-60`: 3,3158 px/mm, 4 sayı uyumlu, yayılım 0,0017** (`80`→265,0; `190`→630,0;
  `90`→298,0; `120`→398,0 px). Dört ilgisiz oranın binde ikide buluşması rastlantı değil ve yolun
  kendi kalibrasyonu (**3,28**) ile **%1,1** içinde örtüşüyor: iki bağımsız yol aynı ölçeği veriyor.
- **İkinci doğrulama yolu:** aynı ölçekle paftanın iki çizilmiş dairesi 51,06 mm ve 20,57 mm çap
  veriyor — basılı `20` ve yuvarlak Ø50 ile %3 içinde.
- **Ölçek kurulamayan paftalarda sonda da kuramıyor:** `exercise-51` 4, `exercise-17` 4,
  `exercise-13` 5, `studycadcam-50` 1 sayı okumuş → 5-9 aday çifti, 3 uyum yok. `flange-1` ve
  `exercise-1`'de okunan sayıların çoğu yanlış okuma; uydurulan hipotezler sayfa sınırına takılıyor
  (`flange-1`: 90 mm × 81,85 px/mm = 7 367 px, sayfa köşegeni 4 170 px).
- **Satır/kesişim modeli bu katmanda işe yaramıyor:** raster gözlemcisi eşdoğrusal parçaları zaten
  birleştiriyor (221 "satırın" 219'u tek çizgi), bu yüzden "sayıyı çizginin boşluğuna oturt" modeli
  0 aday üretti. Doğru eşleme "sayı + yanındaki çizgi".

Sonuç: raster ölçeği bağımsız bir kilit değil — **okuma kapsamının ardından geliyor** (4 paftada
`bind` hiç bağ kuramadı, ölçek de yok). Ölçeği olan iki rasterde sıradaki engel de ölçek değil,
**kontur kapanışı**: `exercise-1`'de 343 çizgiden parça konturu kapanmıyor
(`çizgiler/yaylar döngü kurmuyor`), `studycadcam-60`'ta sayfa çerçevesi dışında döngü yok
(`sayfa çerçevesi dışında döngü yok`). Yani raster iş listesinin başı **okuma kapsamı ve kırık Hough
parçalarından kapalı kontur kurma**, ölçek değil.

## 4. Modelsiz süpürme: bu tur, mevcut ağaç (10 vaka)

`out/profile-step/general-sweep.txt` (ham) + iki vektör paftanın ret metni ayrıca yazdırıldı
(süpürme dosyasındaki `gerekçe:` satırı sondanın yer tutucusudur — `Proposal` nesnesinde `reason`
değil `refusals` alanı var; yer tutucu "kabul edildi" yazıyor, bu okunmamalı).

| pafta | sınıf | çıktı | onaylı/çözümlenemeyen | px/mm | ilk ret |
|---|---|---|---|---|---|
| `plate-pocket-1` | vektör | **proposed** | 7 / 7 | 7,82 | — (regresyon çapası) |
| `plastic-enclosure-1` | vektör | refused | 4 / 14 | 3,92 | `tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1}` |
| `exercise-1-vector` | vektör | refused | 11 / 17 | 3,83 | `en büyük kapalı döngü yuvarlatılmış dikdörtgen değil (8 ilkel, 53.62×82.29 mm; bu dilim yalnız düz parça arketipini öneriyor)` |
| `exercise-1` | raster | refused | 3 / 15 | 5,73 | `kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor)` |
| `exercise-51` | raster | refused | 0 / 13 | yok | `pafta ölçeği okunamadı (kalibrasyon yok)` (ölçüldü) |
| `exercise-17` | raster | refused | 0 / 2 | yok | ölçek reddi (kod sırası) |
| `exercise-13` | raster | refused | 4 / 14 | 2,88 | ölçülmedi |
| `studycadcam-60` | raster | refused | 5 / 18 | 3,28 | `kapalı dış kontur bulunamadı (sayfa çerçevesi dışında döngü yok)` (ölçüldü) |
| `studycadcam-50` | raster | refused | 0 / 9 | yok | ölçek reddi (kod sırası) |
| `flange-1` | raster | refused | 0 / 10 | yok | `pafta ölçeği okunamadı (kalibrasyon yok)` (ölçüldü) |

Dikkat çeken iki satır: `exercise-1-vector`'ün reddi artık **parça konturunu** adıyla anıyor
(döngü düzeltmesi), `plate-pocket-1` dışında hiçbir pafta plan üretmiyor — 9/9 ret.

## 5. İstem kanıt bloğunun ad alanları + yeni etiketle tek ölçüm (`ids-3b-01`)

Değişiklik (tek değişken): `planner._readings_line` artık kanıtı **iki ad alanına ayrılmış** olarak
veriyor — "Printed numbers (`span_ids` yalnız bunlara atıf yapar)" ve "Measured regions (bunlar
atıf değil, geometri kimliği)". Ayrıca profil çağrısının hedefi cümle yerine anahtarlı blok
(`Target profile (this call)`), ve `PROMPT_VERSION` = `general-plan-v4`,
`PROMPT_VERSION_SPLIT` = `general-plan-v4-split-profile-ids`.

Koşu: `qwen2.5vl:3b`, `--split`, aynı plaka/kanıt, 16384 bağlam–4096 çıktı, koşullar
`relations,chain_model`, etiket `ids-3b-01` (`out/model-baseline/ids-3b-01/run.json`,
`status: complete`, 53,23 sn).

| koşul | süre | hüküm | ilk hata |
|---|---|---|---|
| `relations` | 18,66 sn | `failed / planning` | `adım parameters: şema hatası: ifadede tanımsız parametre: 'd2'` |
| `chain_model` | 26,38 sn | `failed / planning` | `adım parameters: şema hatası: parametre adı küçük harfle başlamalı: 'pdf-0'` |

Önceki etiketle (`profile-3b-01`) karşılaştırma, ham cevaplardan:

- **`relations`: hedeflenen hata kapandı.** Önce `hole_spacing_x` basılı 100,71 değerini
  **`span_ids: ["h1","h2"]`** ile (çizilmiş *daire* kimlikleri) atıflıyordu — ad alanı karışması.
  Şimdi `span_ids: ["d1","d3"]` **gerçek basılı ölçü kimlikleri**; atıf denetimi geçti, hata bir
  adım derine indi. Yeni ilk hata: ifadeler **ölçü kimliklerini parametre sanıyor**
  (`(d2 - d4) / 2`); aynı cevapta ikinci bir ifade `(d4 / 2) - (sqrt(3) * d6 / 2)` — yani `sqrt`
  icat edilmiş ve `d4/d6` yine ölçü kimliği.
- **Kayıtlı cevabın örtülü ikinci kusuru (çevrimdışı, etiketli replay):** `hole_spacing_x = 70,0`
  değerini `d1` (100,00) ve `d3` (60,00) atıflarıyla veriyor; hiçbir atıf bu değeri yazmıyor. Şema
  hatası önce döndüğü için değer denetimi bu turda hiç çalışmadı. Tek bir şeyi legal edip
  (ifade var olan bir parametre adını kullansın) yeniden yargıladığımda sıradaki hata `d4` oldu.
  Kayıt: bu cevap **iki bağımsız kusurlu**; ilki ikincisini saklıyor.
- **`chain_model`: ilk hata parametre adına taşındı.** Önce parametreler kabul ediliyor, hata
  profil adımına (`profile 1/6`, kapanmayan iki kenarlı fragment) düşüyordu; şimdi cevap basılı
  sayıları birebir parametre yapıp adlarını ölçü kimliğinden alıyor (`pdf-0`, `pdf-1`, …). İsim
  adaptörü açıkken (varsayılan kapalı) aynı cevap **0 hata** veriyor: bu koşulda parametreleri
  bloke eden tek şey adlandırma kuralı.

Ölçüm sınırları: tek pafta (`plate-pocket-1`), tek model (`qwen2.5vl:3b`), koşul başına tek
temperature-0 koşusu; hiçbir plan geçmediği için **CAD üretimi, çizim kontrolü ve ikinci parça
grubu çalıştırılmadı, STEP yok**. Bu koşu bir kapasite ya da eğitim yargısı değildir.

## 6. Sıradaki tek karar

Ölçülen üç kilit, sırayla:

1. **Parametre adlandırma/şekli (model arayüzü):** `chain_model`'de parametreleri bloke eden tek
   şey ad kuralı (adaptör açıkken 0 hata), `relations`'ta ise ifadeler ölçü kimliklerini parametre
   sanıyor. Tek değişken: istemde "ifade yalnız kabul edilmiş **parametre adlarını** kullanır; ölçü
   kimlikleri yalnız `span_ids` alanında yaşar" kuralını adlandırma kuralıyla birlikte vermek.
2. **Bağlama kapsamı (okuma zinciri):** ikinci arketipin ön koşulu — kontur ölçülerinin döngüye
   bağlanması (`plastic` 0/2, `exercise-1-vector` 0/2).
3. **Raster kapsamı ve kontur kapanışı:** ölçek ancak `bind` bağ kurabildiğinde geliyor (4/7
   paftada hiç bağ yok); ölçeği olan `exercise-1`'de bile kırık Hough parçalarından kapalı kontur
   çıkmıyor. Yani raster iş listesi: önce kapsam, sonra döngü kapanışı, ölçek en sonda.

## Doğrulama

- `pytest -q` (tam paket): **354 geçti**, 274,82 sn (`out/profile-step/pytest-round2.txt`) — ikisi bu
  turda eklenen döngü testleri; `tests/test_planner.py`'nin iki istem testi yeni başlıklara güncellendi.
- `eval/plate_plan.py` geçti; plakada `propose` hâlâ `proposed`, ölçüler değişmedi.
- `eval/check_tables.py`: 20 satır, 0 kayma. `eval/baseline_report.py --check`: koşularla uyuşuyor
  (`ids-3b-01` satırı `adım başına profil` arayüzüyle ayrı okunur).
- `eval/profile_step_evidence.py --check`: kanıt paketi koşu kayıtlarından yeniden üretiliyor. Bu
  turda paketin istem sürümünü **modül sabitinden** okuduğu görüldü ve düzeltildi: paket artık sürümü
  koşu kaydından alıyor (öncesinde son turun turunu `general-plan-v4-split-profile-ids` diye
  adlandırıyordu, oysa o koşu `general-plan-v3-split-profile` sormuştu).
- `git diff --check` temiz. Çalışma ağacı korunmuştur: commit yapılmadı, `HEAD` yine `96e0118`.
- Ölçüm sınırları: modelsiz süpürme 10 vaka; model koşusu tek pafta, tek model, koşul başına tek
  temperature-0 koşusu. Hiçbir plan geçmedi → CAD üretimi, çizim kontrolü ve ikinci parça grubu
  çalıştırılmadı; `-3b-01` koşuları bir kapasite ya da eğitim yargısı değildir.
