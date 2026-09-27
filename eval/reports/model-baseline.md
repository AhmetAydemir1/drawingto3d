# Model öncesi ölçüm — PLAN Bölüm 7

Bu rapor Bölüm 7'nin beşinci teslimidir: hata sınıfları, model karşılaştırması ve bir sonraki
iyileştirme kararı. Sayılar elle yazılmadı; `eval/baseline_report.py` bunları
`out/model-baseline/*/run.json` (her koşu bir dosya, `eval/model_baseline.py` yazar) ve
`out/frontend/*.json` (okuma koşulunun vaka kayıtları) içinden üretir. Aşağıdaki "üretilen"
blok bu iki kaynaktan gelir; `--check` onu koşulara karşı denetler, yani sayıyı değiştiren bir
koşu raporu eskimiş bırakır.

Bu dilim **evrensel dönüşüm veya eğitim başarısı iddiası taşımaz**. Raster ankraj/ölçek
geliştirmesi Aşama 2'nin açık işidir (PLAN §7 kabul paragrafı).

## Ölçümün koşulları

- Makine: Apple M1, 16 GB. Takas, sayfa ve süreç RSS'i koşu boyunca 2 saniyede bir örneklenir;
  ağırlıkların disk boyutu bellek sayılmaz.
- Modeller: yerel Ollama sunucusu, iki aday — `qwen2.5vl:3b` ve `qwen3-vl:8b-instruct`.
  Ölçüm aynı makinede, aynı kanıtla, tek koşu sırasında tek model yüklü olacak şekilde yapıldı.
- Aynı sürüm ve ayarlarla yeniden üretim: `eval/model_baseline.py --label <etiket>`, koşu
  kaydına kod HEAD'ini, yerel değişiklik listesini, manifest özetini, istem/şema/kanıt
  sürümlerini ve tüm ayarları yazar.
- Referans STEP, doğru plan ve dosya adı model istemine hiçbir koşulda giremez; planlama
  koşulu yalnız okuma zincirinin ürettiği kimlikli ölçüleri ve elle doğrulanmış ilişkileri görür.

## Bölüm 18B'nin dört koşulu

| Koşul | Ne yapar | Hangi hatayı sahiplenir |
|---|---|---|
| `reading` | Çizim → kimlikli ölçüler; basılı sayılarla karşılaştırır | Sayı, sembol, ok, kapsam |
| `chain` | Çizim → `bind` → `meaning` → `proposal` | Bağlama ve planlama öncesi ret sınırı |
| `verified_plan` | Elle doğrulanmış `GeneralPlan` → aynı derleyici | Şema, CAD işlemi, doğrulayıcı |
| `relations` | Elle doğrulanmış ilişkiler + çizim → aynı model → plan | Algı hatası azaltıldığında kalan **planlama** hatası |

`relations` koşulunun bağlamı `eval/relations/*.json` dosyalarından gelir ve bu koşu **otomatik
PDF → STEP başarısına sayılmaz**; teşhis içindir (Bölüm 18B).

## Ölçülen bulgular

### 1. Manifest: `2/` ile `7/` gerçekten aynı parça

Bayt kimliği (`sha256`):

- `examples/pdf with steps/2/Drawing.jpg` ≡ `examples/pdf with steps/7/my_part.jpg`
  (`54adde53e376b5df…`)
- `examples/pdf with steps/2/Part-2.STEP` ≡ `examples/pdf with steps/7/my_part.STEP`
  (`512e74d3501ace5c…`)

İki klasör tek parçadır; iki bağımsız örnek sayılmaz. `eval/cases.json` bunları tek
`part_group` altında `exercise-1` (raster JPG) ve `exercise-1-vector` (vektör PDF) olarak
kaydeder — aynı parçanın iki kaynağı, aynı STEP'e karşı. Yeni veri kararı gelene kadar yalnız
regresyon ölçümü yapıldı; pilot ≥10 / saklı ≥20 hedefi açık kalır.

### 2. Okuma tabanı kaynağa göre değişiyor, ve zayıf olan taraf gerçek taranmış paftalar

Aynı parçanın vektör ve raster kaynağı yan yana okunduğunda fark, hatanın sahibini gösterir
(sayılar aşağıdaki üretilen tabloda):

| parça | vektör | raster (render) |
|---|---|---|
| `plate-pocket-1` | 7/7, gürültü 0 | 6/7, gürültü 2 |
| `plastic-enclosure-1` | 11/11, gürültü 0 | 8/11, gürültü 4 |

Temiz render'larda okuyucu neredeyse tüm sayıları bulur ve **kendi ölçeğini 4 haneye kadar aynı
kurar** (7.817 ve 3.917 px/mm; ikisi de kaynak ne olursa olsun aynı); kaybedilen 0–3 sayı
gürültüyle birlikte gelir. Ama gerçek taranmış paftalarda kapsam tabana iner:
`exercise-17` 2/7, `exercise-51` 4/14, `exercise-13` 2/8 (bu pafta ölçek de kuruyor: 2.883
px/mm) ve `flange-1` 4/13.

Yani: **vektör yolu bu paftalarda tam, temiz render neredeyse tam, gerçek tarama 2–4 sayı / 7–14
basılı sayı ve çoğu zaman hiç ölçek kuramıyor.** Ölçek kurulamadığında `bind`/`meaning`/
`proposal` doğru davranışı gösterip `no-scale` ile reddeder; zinciri durduran şey bir hata
değil, eksik kanıttır. Ölçek kuran paftalar: plate, plastic, exercise-1, exercise-13,
studycadcam-60; kuramayanlar: exercise-17, exercise-51, flange-1, studycadcam-50 (mcmaster
paftalarında basılı sayı iki tane olduğu için kalibrasyon zaten beklenmiyor).

### 3. Okuma kaybının yeri ölçüldü: sayı bulmakta değil, **aday kümesinde**

`Exercise 17` üzerinde aşama aşama sayıldı (`out/agent-s7/where.py`): 425 mürekkep lekesi →
183 ayırıcı dışta → 131 küme → 129 kullanılabilir küme → **kapı 30 kabul** (22 ölçü, 8 kılavuz)
→ **okuyucudan 2 span**. Yani kayıp aramada değil, kabul edilen kümelerin okunmasında.

Kabul edilen 30 kümenin hazırlanmış kırpmaları tek bir kontak sayfada toplandı
(`out/agent-s7/crops-Exercise 17.png`): kırpmaların neredeyse tamamı **ok başları, yay/kavis
parçaları ve küçük daireler** — içlerinde basılı sayı yok. Tesseract bu kırpmalarda haklı olarak
boş ya da anlamsız dönüyor (`''`, `_`, `| |`, `¥`, `A`). Ölçülen sonuç: bu paftada okuyucuya
verilen 30 adayın 28'i sayı değil.

Kırpma ve cevap kaydı (`out/agent-s7/readlog.py`) ile kapı muhakemesi (`out/agent-s7/guard.py`)
aynı farkı iki taraftan doğruluyor: `_collect_spans` ok başı korumasını **yalnız
`mode == "dimension"` iken** soruyor; kılavuz modunda sorulmuyor, ve ölçü modunda kalan ok
başları çizili (içi boş) olduğu için `_is_drawn_solid` maddesi onları ayıramıyor. Bu paftada
kuralın kendi docstring'indeki varsayım (ok başı dolu, basılı rakam içi boş) tersine dönüyor.

### 4. Planlama: hazır modeller şemayı derinlikte tutamıyor

İki aday da **planlama** katmanında düştü, ve düşme biçimleri farklı:

- `qwen2.5vl:3b`, serbest metin (`num_predict=2048`): `parameters` bir **liste**
  (`[{name, value, …}]`) olarak yazıldı, sözlük değil; aynı anahtar birden çok kez; hem `value`
  hem `expr`; ve yanıt **çıktı sınırında kesildi** (`done_reason=length`, 4096'da da kesiliyor).
  Şemayı zorlayan gramerle (`format = GeneralPlan.model_json_schema()`) ikinci koşuda da
  nesne kapanmadı — 3 sınıflık model bu iş için çıktı üretmeyi bitiremiyor.
- `qwen3-vl:8b-instruct` (8.8B, Q4_K_M), şema zorlamalı: yanıt **temiz kapandı**
  (`done_reason=stop`, 929 token, 147 s) ve `parameters` doğru biçimde isimli sözlük olarak
  geldi; yedi parametrenin değerleri paftanın kendi sayılarıyla uyuşuyor (100 / 80 / 60 / 6.8 /
  50 / 15 / 8) ve her biri kanıttaki ölçü kimliğine atıf veriyor. Ama `sketches.*.entities[0]`
  tek bir **dizeye** çöktü: model gövdenin içine kendi muhakemesini yazmaya başlayıp yapıyı
  kaybetti. Şema hatası tam olarak orada raporlanıyor; işlemler de plaka için `revolve` gibi
  yanlış işlemler öneriyor.

Ölçülen ayrım şu: **8B model değerleri ve atıfları doğru üretiyor, 3B üretemiyor; ikisi de
plan gövdesinin iç yapısını (sketch → entity → koordinat ifadesi) tutamıyor.** Bu, "model
planlayamıyor" değil, "istenen çıktı derinliği modelin tutabildiğinden fazla" demektir.

Bir kendi hatamız da bu ölçümde ortaya çıktı ve düzeltildi: model planın kimliğini (`source`)
kendiliğinden yazdığında aday tümden `invalid` sayılıyordu. Bu, modelin yapmadığı bir planlama
hatasını raporluyordu — 8B'nin doğru yedi parametresi bu yüzden çöpe gitti. Artık koşunun
kaynağı modelin verdiğinin yerine geçiyor ve durum `overrides` alanına yazılıyor
(`tests/test_planner.py::test_the_source_identity_is_the_harness_not_the_model`).

### 5. Zincirin retleri dört ayrı sahipli, ve CAD hiç suçlanmıyor

`chain` koşulu (çizim → `bind` → `meaning` → `proposal` → derleyici) yirmi satırın on altısını
**okuma** sınıfına yazdı, ama retlerin *sahibi* dört ayrı yerde. Vaka vaka tablodan:

| ret gerekçesi | paftalar | gerçek sahibi |
|---|---|---|
| `pafta ölçeği okunamadı (kalibrasyon yok)` | exercise-51, exercise-17, studycadcam-50, flange-1 | ölçek kurulamıyor: ölçü sayıları geometriye bağlanamıyor |
| `kapalı dış kontur bulunamadı` | exercise-1, exercise-13, studycadcam-60 | okuma: dış kontur döngü kurmuyor (raster çizgi/yay birleşmiyor) |
| `en büyük kapalı döngü yuvarlatılmış dikdörtgen değil (3 ilkel, 20.54×35.95 mm; bu dilim yalnız düz parça arketipini öneriyor)` | exercise-1-vector | **kapsam sınırı**, okuma değil: okuma tam (`basılı sayıların tamamı bulundu`) ama parça bu dilimin önerdiği arketipe girmiyor |
| `tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1}` | plastic-enclosure-1 | **bağlama**: okuma 11/11 tam, ama çap iddiası hiç oluşmuyor (bu paftanın bilinen açık işi) |

Yalnız `plate-pocket-1` zinciri sonuna kadar gidiyor: `draft` — plan önerildi, katı kuruldu, plan
denetimi geçti.

CAD katmanı bu ölçümde **hiç suçlanmıyor**: elle doğrulanmış üç plan (`plate-pocket-1`,
`bracket_linear_pattern` 22 084.3806 mm³, `shaft_revolve_cross_hole` 13544.7373 mm³) derleyiciden
geçip plan denetimini veriyor. Yani ölçülen hata sınıfları **okuma** (16/20 satır) ve **planlama**
(model yolu); CAD'in doğru olduğu iddiası değil, bu ölçümde kendini göstermediği kaydıdır — ve
`verified_plan` koşulu onu ayrı ölçmeye devam eder, çünkü derleyicinin çalışması çizim
yorumununun çözüldüğüne kanıt sayılmaz (PLAN §6).

### 6. Okuyucuya yapılan düzeltme tüm kümede ölçüldü: kazanç yok, kayıp da yok

Bir uygulama adımı da yapıldı: ok başı koruması artık **kılavuz moduna da** soruluyor ve konum
testi eksen hizası varsayımından **gerçek nokta–doğru parçası uzaklığına** genelleştirildi
(`src/drawingto3d/perceive.py`). İkincisi bir yanlış cevabı kaldırıyor: eski hesap, ankraj çifti
köşegen olduğunda da tek bir koordinatı ölçüyordu, yani köşegen ölçü çizgilerinde koruma
anlamsız bir sayı veriyordu. Eksen hizalı girdide yeni hesap bit bit aynı sonucu verir
(`tests/test_reading_gate.py` 1000'den fazla kutu üzerinde eski formülle karşılaştırır).

Ölçüm (kural: eklenti ancak ölçümle kalır): aynı vaka kümesi, iki kod durumu, `out/frontend`
önce/sonra karşılaştırıldı — **22 kaydın 22'si aynı**, değişen 5 kayıt yalnızca bu dilimde
eklenen yeni vaka/katmanlar. `eval/check_tables.py` de 20 satırda sıfır kayma veriyor. Yani
düzeltme **ölçülebilir kazanç getirmiyor**; kalıyor çünkü köşegen ankrajlı bir çiftte yanlış
cevap vermeyi bırakıyor ve tüm kümede bedeli sıfır.

`Exercise 17`'de korumanın ne yaptığı gerçek koşu içinde sayıldı (`out/agent-s7/guardtruth.py`):
40 aday soruluyor, **10'u düşüyor**, 30'u okuyucuya gidiyor. Yani bu paftanın kaybı korumanın
eşiğinde değil: kalan 30 adayın 28'i ok, kavis ve küçük daire, ve onlar konum testini geçiyor
(kutu merkezleri çizginin ekseninden 7.5–39 px uzakta). Bu yüzden sıradaki iş eşik ayarı değil,
**ayrı bir sınıflandırma sorusu**: bu kırpma basılı bir sayı mı, çizimin kendi mürekkebi mi.

## Bir sonraki iyileştirme kararı (Bölüm 18C'ye göre)

Baskın hata **okuma**dır (20 zincir satırının 16'sı) ama tek bir iş değil: ölçüm onu üç ayrı işe
bölüyor, ve model yolu bir dördüncüsünü ekliyor. Sıra, kaç paftayı açtığına göre:

1. **Ölçek kurulamıyor — 4 pafta** (exercise-51, exercise-17, studycadcam-50, flange-1). Bu,
   Bölüm 18C satır 1'in tarif ettiği iş: küçük sayı/çap sembolü/ölçü oku kaçıyor, ve bu
   paftalarda kaybın yeri ölçüldü (bkz. madde 3: kabul edilen 30 adayın 28'i sayı değil).
   Kalibrasyon üç bağımsız ölçü çiftini istiyor; okuyucu bir paftada 2-4 sayı buldukça bu
   hiçbir zaman dolmaz, yani iş "daha çok sayı oku"dur. İlk somut adım bu dilimde yapıldı ve
   ölçüldü: ok başı koruması artık kılavuz moduna da soruluyor ve konum testi eksen hizası
   varsayımından gerçek nokta–doğru parçası uzaklığına genelleştirildi (eksen hizalı girdide
   bit bit aynı sonuç; `tests/test_reading_gate.py`). Ama ölçüm bu düzeltmenin *kendi başına yetmediğini*
 gösteriyor: `Exercise 17`'de koruma **zaten** kabul edilen 40 adayın 10'unu düşürüyor
 (`out/agent-s7/guardtruth.py` ile gerçek koşu içinde ölçüldü), geri kalan 30'un 28'i ok ve
 kavis ve onlar konum testini geçiyor — yani sıradaki iş kırpma değil **sınıflandırma**: bir
 adayın basılı sayı olup olmadığı ayrı bir sorudur. (Bu düzeltmenin tüm küme üzerindeki
 etkisi ayrı ölçülür; eksen hizalı girdide bit bit aynı sonucu verdiği testle sabit.)
2. **Dış kontur döngü kurmuyor — 3 pafta** (exercise-1, exercise-13, studycadcam-60; ikisi
   tarama). Sayılar okunsa bile `proposal` dış profili bulamıyor; raster çizgi/yay birleşmesi
   burada tıkanıyor.
3. **Bağlama: çap iddiası hiç oluşmuyor — 1 pafta** (plastic-enclosure-1). Okuma 11/11 tam,
   `proposal` "tam iki çap ölçüsü bekleniyordu, 0 okundu" diyor. Bağlama katmanının bilinen açık işi.
4. **Plan arayüzü** (model yolu). Modele plan gövdesini sözlü olarak yazdırmak yerine, kanıtı
   daraltıp istenen iç içe yapıyı azaltmak; derleyiciye ulaşan aday oranını ölçmek (Bölüm 18A).
5. **Eğitim kararı henüz verilmedi.** Bölüm 18C'nin eğitim koşulu "tekrarlanan hata,
   doğrulanmış hedef etiket, ayrı doğrulama kümesi ve ölçülebilir iyileştirme hedefi"dir.
   Bunlardan ikisi bugün yok: (a) 1-4 arası işler uygulanmadan "tekrarlanan hata"nın model
   kapasitesine ait olduğu gösterilmedi, (b) ayrı doğrulama kümesi henüz kurulmadı (pilot ≥10,
   saklı ≥20 hedefi bekliyor). **Etiket kaynağı ise hazır ve ölçülmüş:** vektör paftaların
   metin katmanı, render edilmiş rasterinde hangi basılı sayının nerede olduğunu tam veriyor —
   yani 1. maddedeki "bu kırpma basılı sayı mı, çizginin kendi mürekkebi mi" görevi için
   etiketli veri üretilebilir. Hedef görev küçük bir algılayıcıdır (sınıflandırıcı), LoRA değil.

Geçiş eşiği (eğitim başlamadan önce kayda geçen): raster kapsamı tüm vaka kümesinde
`found/printed ≥ 0.8`; beş taranmış paftanın (`exercise-1`, `exercise-17`, `exercise-51`,
`exercise-13`, `flange-1`) en az dördü ölçek kursun — bugün 2/5; planlama koşulunda derleyiciye
ulaşan aday oranı ≥ 1/2 — bugün 0/1. Bunlar tutmazsa eğitim gerekçesi de yoktur.

## Kabul durumu (PLAN §7)

| Kabul koşulu | Durum |
|---|---|
| Aynı sürüm ve ayarlarla yeniden üretilebilen rapor | Sağlandı — koşu kaydı kod HEAD'i, kirli dosya listesi ve tüm ayarları taşır; tablolar `eval/baseline_report.py --check` ile denetlenir |
| Çözülemeyen her örnekte açık hata nedeni | Sağlandı — vaka vaka tabloda her satır durum + hata sınıfı + gerekçe |
| En az bir yerel modelin M1 ölçümü | Sağlandı — iki model, bellek/takas örneğiyle |
| İkinci model karşılaştırması | Sağlandı (iki aday ölçüldü) |
| Bağımsız veri kümesiyle genelleme | **Açık** — pilot/saklı veri kararı kullanıcıya bırakıldı (PLAN §7.1) |

<!-- generated: tables -->

### Koşular

| koşu | başlangıç | model | koşullar | şema | vaka | sonuç | hata sınıfı | süre sn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| smoke | 2026-09-27 03:59 | yok (model dışı) | reading,chain | serbest metin | 2 | draft=1 ok=1 refused=2 | ok=2 reading=2 | 391.5 |
| relations-3b-probe | 2026-09-27 04:07 | qwen2.5vl:3b * | relations | serbest metin | 1 | failed=1 | planning=1 | 121.4 |
| relations-3b-structured | 2026-09-27 04:13 | qwen2.5vl:3b * | relations | json-schema | 1 | failed=1 | planning=1 | 243.7 |
| relations-8b-structured | 2026-09-27 04:18 | qwen3-vl:8b-instruct * | relations | json-schema | 1 | failed=1 | planning=1 | 147.4 |
| relations-8b-source-overridden | 2026-09-27 04:33 | qwen3-vl:8b-instruct * | relations | json-schema | 1 | failed=1 | planning=1 | 152.8 |
| floor-1 | 2026-09-27 04:36 | yok (model dışı) | reading,chain,verified_plan | json-schema | 12 | draft=3 ok=3 partial=3 refused=13 | ok=6 reading=16 | 2129.7 |

`*` bağlam, elle doğrulanmış ilişki tablosundan gelir (`eval/relations/`): bu koşu otomatik PDF → STEP başarısı değil, planlama ve CAD katmanlarının ayrı ölçümüdür (PLAN Bölüm 18B).

### Vaka vaka

| koşu | vaka | koşul | durum | hata sınıfı | gerekçe |
| --- | --- | --- | --- | --- | --- |
| smoke | plate-pocket-1 | reading | ok | ok | basılı sayıların tamamı bulundu, yanlış okuma yok |
| smoke | plate-pocket-1 | chain | draft | ok | plan önerildi, katı kuruldu, plan denetimi geçti |
| smoke | flange-1 | reading | refused | reading | pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik) |
| smoke | flange-1 | chain | refused | reading | pafta ölçeği okunamadı (kalibrasyon yok) |
| relations-3b-probe | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: yanıtta JSON nesnesi yok |
| relations-3b-structured | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: yanıtta JSON nesnesi yok (çıktı sınırında kesildi) |
| relations-8b-structured | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: model plan kaynağını (source) veremez; kaynak kimliği koşuya aittir |
| relations-8b-source-overridden | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: sketches.outline_sketch.entities.0: Unable to extract tag using discriminator 'type' |
| floor-1 | exercise-1 | reading | partial | reading | basılı 13 sayının 6 tanesi bulundu; eksik: 6, 10, 25, 40, 57, 60, 80 |
| floor-1 | exercise-1 | chain | refused | reading | kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor) |
| floor-1 | exercise-1-vector | reading | ok | ok | basılı sayıların tamamı bulundu, yanlış okuma yok |
| floor-1 | exercise-1-vector | chain | refused | reading | en büyük kapalı döngü yuvarlatılmış dikdörtgen değil (3 ilkel, 20.54×35.95 mm; bu dilim yalnız düz parça arketipini öneriyor) |
| floor-1 | exercise-51 | reading | refused | reading | pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik) |
| floor-1 | exercise-51 | chain | refused | reading | pafta ölçeği okunamadı (kalibrasyon yok) |
| floor-1 | exercise-17 | reading | refused | reading | pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik) |
| floor-1 | exercise-17 | chain | refused | reading | pafta ölçeği okunamadı (kalibrasyon yok) |
| floor-1 | exercise-13 | reading | partial | reading | basılı 8 sayının 2 tanesi bulundu; eksik: 10, 30, 42, 50, 170, 240 |
| floor-1 | exercise-13 | chain | refused | reading | kapalı dış kontur bulunamadı (çizgiler/yaylar döngü kurmuyor) |
| floor-1 | plate-pocket-1 | reading | ok | ok | basılı sayıların tamamı bulundu, yanlış okuma yok |
| floor-1 | plate-pocket-1 | chain | draft | ok | plan önerildi, katı kuruldu, plan denetimi geçti |
| floor-1 | studycadcam-60 | reading | partial | reading | basılı 9 sayının 6 tanesi bulundu; eksik: 25, 30 |
| floor-1 | studycadcam-60 | chain | refused | reading | kapalı dış kontur bulunamadı (sayfa çerçevesi dışında döngü yok) |
| floor-1 | studycadcam-50 | reading | refused | reading | pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik) |
| floor-1 | studycadcam-50 | chain | refused | reading | pafta ölçeği okunamadı (kalibrasyon yok) |
| floor-1 | plastic-enclosure-1 | reading | ok | ok | basılı sayıların tamamı bulundu, yanlış okuma yok |
| floor-1 | plastic-enclosure-1 | chain | refused | reading | tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1} |
| floor-1 | flange-1 | reading | refused | reading | pafta ölçeği yok: ölçü sayıları geometriye bağlanamıyor (raster ankraj/ölçek eksik) |
| floor-1 | flange-1 | chain | refused | reading | pafta ölçeği okunamadı (kalibrasyon yok) |
| floor-1 | bracket_linear_pattern | verified_plan | draft | ok | plan derleyiciden geçti; hacim 22084.3806 mm³, beklenti {'bbox': ['length', 'height', 'width'], 'volume': 'area * width - 2 * pi * (hole_d / 2) ** ... |
| floor-1 | shaft_revolve_cross_hole | verified_plan | draft | ok | plan derleyiciden geçti; hacim 13544.7373 mm³, beklenti {'bbox': ['2 * flange_r', '2 * flange_r', 'length'], 'volume': None} |

### Koşu kaynakları (Apple M1, 16 GB, takas ölçülü)

| koşu | takas başı MB | takas tepe MB | boş sayfa en az MB | ollama RSS tepe MB |
| --- | --- | --- | --- | --- |
| smoke | 7168.0 | 7168.0 | 14.3 | 14.5 |
| relations-3b-probe | 10240.0 | 10240.0 | 3.7 | 3735.3 |
| relations-3b-structured | 11264.0 | 11264.0 | 14.1 | 4953.1 |
| relations-8b-structured | 13312.0 | 13312.0 | 14.5 | 8295.3 |
| relations-8b-source-overridden | 13312.0 | 13312.0 | 14.5 | 8295.6 |
| floor-1 | 12288.0 | 12288.0 | 3.7 | 31.3 |

### Okuma tabanı (kapı sonrası kapsam)

Katman `vektör` = PDF'in kendi metin katmanı, `raster` = aynı pafta görüntüden okunmuş.

| vaka | katman | span | basılı | kapsam | ankrajlı | px/mm | gürültü |
| --- | --- | --- | --- | --- | --- | --- | --- |
| exercise-1 | raster | 15 | 13 | 6/13 | 15 | 5.7310 | 6 |
| exercise-13 | raster | 14 | 8 | 2/8 | 14 | 2.8830 | 10 |
| exercise-17 | raster | 2 | 7 | 2/7 | 2 | - | 0 |
| exercise-51 | raster | 13 | 14 | 4/14 | 13 | - | 8 |
| flange-1 | raster | 10 | 13 | 4/13 | 10 | - | 3 |
| mcmaster-2389K26 | raster (vektör paftanın render'ı) | 6 | 2 | 0/2 | 6 | - | 6 |
| mcmaster-2389K26 | vektör | 2 | 2 | 2/2 | 2 | - | 0 |
| mcmaster-2389K39 | raster (vektör paftanın render'ı) | 2 | 2 | 0/2 | 2 | - | 2 |
| mcmaster-2389K39 | vektör | 2 | 2 | 2/2 | 2 | - | 0 |
| plastic-enclosure-1 | raster (raster-model) | 16 | 11 | 10/11 | 16 | 3.9170 | 3 |
| plastic-enclosure-1 | raster (vektör paftanın render'ı) | 15 | 11 | 8/11 | 15 | 3.9170 | 4 |
| plastic-enclosure-1 | vektör | 14 | 11 | 11/11 | 14 | 3.9170 | 0 |
| plate-pocket-1 | raster (raster-model) | 12 | 7 | 7/7 | 12 | 7.8300 | 4 |
| plate-pocket-1 | raster (vektör paftanın render'ı) | 9 | 7 | 6/7 | 9 | 7.8170 | 2 |
| plate-pocket-1 | vektör | 7 | 7 | 7/7 | 7 | 7.8170 | 0 |
| studycadcam-50 | raster | 9 | 3 | 2/3 | 9 | - | 7 |
| studycadcam-60 | raster | 18 | 9 | 6/9 | 18 | 3.2780 | 9 |

<!-- /generated: tables -->
