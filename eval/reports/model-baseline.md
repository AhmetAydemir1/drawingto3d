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

### 5. CAD katmanı henüz suçlanmıyor

Hiçbir model adayı derleyiciye ulaşamadı, çünkü ikisi de planlama katmanında düştü (madde 4).
CAD sınırı yalnız elle doğrulanmış planlarla ölçülüyor (`verified_plan` koşulu): plaka planı
kapalı formla 124 825.4 mm³'e karşı 0.0000% farkla kuruluyor. Yani ölçülen hata sınıfları
şimdilik **okuma** ve **planlama**; CAD bu ölçümde kendini göstermedi. Bu, CAD'in doğru olduğu
iddiası değildir — ölçülmüş planların küçük kümesi hakkındadır.

## Bir sonraki iyileştirme kararı (Bölüm 18C'ye göre)

Baskın hata iki tanedir ve ikisi de **ölçülmüş olarak tasarım** sorunudur, model kapasitesi
değil. Sıra:

1. **Raster aday kapısı** (Bölüm 18C satır 1: "küçük sayı/çap sembolü/ölçü oku kaçıyor → önce
   kırpma, OCR ve raster ankrajlarını iyileştir"). Ölçüm net: adayların çoğu sayı değil. Ok
   başı/kavis korumasını kılavuz moduna da sormak ve konum testini eksen hizası varsayımından
   gerçek nokta–doğru parçası uzaklığına genelleştirmek ilk adım; sonra kapsam **tüm vaka
   kümesinde** yeniden ölçülür (`found/printed` + gürültü listesi + ölçek), tek paftada değil.
2. **Plan arayüzü**: modele plan gövdesini sözlü olarak yazdırmak yerine, kanıtı daraltıp
   istenen iç içe yapıyı azaltmak (ve gerekirse şema sürümünü yükseltip eğitim verisini ona
   göre sürümlemek — Bölüm 18A). Bu, derleyiciye ulaşan aday sayısını ölçülebilir biçimde
   artırmalı.
3. **Eğitim kararı henüz verilmedi.** Bölüm 18C'nin eğitim koşulu "tekrarlanan hata,
   doğrulanmış hedef etiket, ayrı doğrulama kümesi ve ölçülebilir iyileştirme hedefi"dir.
   Bunlardan ikisi bugün yok: (a) 1. ve 2. adımlar uygulanmadan "tekrarlanan hata"nın model
   kapasitesine ait olduğu gösterilmedi, (b) ayrı doğrulama kümesi henüz kurulmadı (pilot ≥10,
   saklı ≥20 hedefi bekliyor). **Etiket kaynağı ise hazır ve ölçülmüş:** vektör paftaların
   metin katmanı, render edilmiş rasterinde hangi basılı sayının nerede olduğunu tam veriyor —
   yani "bu kırpma basılı sayı mı, çizginin kendi mürekkebi mi" görevi için etiketli veri
   üretilebilir. Hedef görev küçük bir algılayıcıdır (sınıflandırıcı), LoRA değil.

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

### Koşu kaynakları (Apple M1, 16 GB, takas ölçülü)

| koşu | takas başı MB | takas tepe MB | boş sayfa en az MB | ollama RSS tepe MB |
| --- | --- | --- | --- | --- |
| smoke | 7168.0 | 7168.0 | 14.3 | 14.5 |
| relations-3b-probe | 10240.0 | 10240.0 | 3.7 | 3735.3 |
| relations-3b-structured | 11264.0 | 11264.0 | 14.1 | 4953.1 |
| relations-8b-structured | 13312.0 | 13312.0 | 14.5 | 8295.3 |
| relations-8b-source-overridden | 13312.0 | 13312.0 | 14.5 | 8295.6 |

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
