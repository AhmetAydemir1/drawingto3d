# Model öncesi ölçüm — PLAN Bölüm 7

## Denetim sonrası geçerli yorum — 2026-09-27

Bu raporun tabloları `out/model-baseline/*/run.json` ve `out/frontend/*.json` kayıtlarından
üretilir. `eval/baseline_report.py --check` tablo–kayıt tutarlılığını sınar; deney tasarımının
ve ölçüm kodunun doğru olduğunu kanıtlamaz. Eski kayıtlar korunmuştur. Denetim bulguları
ve sıradaki iş `eval/reports/step-validation-audit.md`, PLAN Bölüm 21 ve HANDOFF.md içindedir.
En son `suggest-3b-01` ham yanıtları ve bağımsız parametre kontrolleri
`eval/reports/latest-parameter-evidence.json` içinde korunur. Önceki profil, kanıt başlıkları,
parametre kuralları ve önerilen ad deneyleri Bölüm 20'de tarihçe olarak durur.
Önceki ölçüm denetimi `eval/reports/progress-audit.md` dosyasında korunur.

`şema` sütunu hangi arayüzün sorduğunu kayıttan okur: `üç adımlı` = profiller tek çağrıda,
`adım başına profil` = okumanın ölçtüğü her kapalı profil için bir çağrı; bu iki sayı
karşılaştırılabilir değildir.

**İlerleme var; eğitim ve ürün kabulü açık.** Genel CAD derleyicisi çalışıyor. Gerçek raster
okuma zayıf; model planlayıcısı `chain_model` ve CLI yoluna bağlandı, ancak model planıyla
uçtan uca doğru STEP henüz elde edilmedi. Önceki kesin
neden yorumlarının yerine aşağıdaki sınırlar geçer.

### Okuma ölçütü

Tablodaki kapsam, manifestteki sayısal değerlerin bulunmasını sayar. Aynı değerin bir
başka konumda okunması doğru ölçü eşleşmesi sayılabilir; her ölçü örneğinin konumu,
birimi, sembolü ve bağlandığı özellik doğrulanmaz. Dolayısıyla 7/7, 11/11 veya 13/13
"bütün çizim doğru anlaşıldı" demek değildir. Yeni kabul, kimlikli ölçü örneğine ve
geometri ilişkisine dayanmalıdır.

Vektör/raster karşılaştırması için PDF'nin kendi render'ı kullanılabilir. `2/Drawing.pdf`
ile `7/my_part.jpg` aynı parçayı farklı paftalarda gösterir; metin kutuları aralarında
kayıtsızca aktarılamaz. `2/Drawing.jpg` ile `7/my_part.jpg` ise bayt-eş kopyadır; bağımsız
iki parça değildir. Manifestteki pilot/saklı kümeleri boş kalmaktadır.

### Raster kaybı: neden henüz belirlenmedi

`Exercise 17`'de kabul edilen adayların çoğunun rakam olmaması, sonucun neden zayıf
olabileceğine dair kanıttır. Düşük nihai kapsam tek başına "doğru rakam hiç aday olmadı"
sonucunu vermez; aday üretimi, eleme, OCR ve sonraki filtreler ayrı ölçülmelidir.

`eval/offering.py` koşusu kesilmiş; `out/agent-s7/offering.txt` yalnız 61 bayt ve bir atlama
satırı içeriyor. Araç henüz karar için güvenilir değil: örtüşen yanlış değer de `okundu`
sayılıyor; ikinci ok başı korumasını ve okuma sonrası filtreleri ayrı izlemiyor. Bu araç
onarılıp aynı paftanın render'ında konum + değer eşleşmesiyle ölçülmeden baskın kayıp
adımı ilan edilmeyecek. Temiz render da her gerçek tarama için matematiksel üst sınır değildir.

Aday lojistik sınıflandırıcı deneyi yapıldı (`eval/classifier.py`, üç parça grubu, 150
aday). Bu bir eğitim deneyidir; VLM/LoRA eğitimi veya ürün modeli seçimi değildir. Küçük
aday kümesinde filtreleme başarısı, tüm sayfalarda algılama/genelleme başarısı sayılmaz.
Ok başı/konum korumasındaki önceki düzeltme 22 eski kayıtta kapsam değişikliği getirmedi.

### Model planlama deneyinin sınırları ve onarımı

Eski `relations` koşuları tek plakanın elle hazırlanmış ilişkilerini metin olarak verdi;
`propose_plan` çağrısında çizim görüntüsü gönderilmiyor. Bu koşulun adı görüntü + ilişki
planlaması gibi okunmamalı. Gerçek `chain` ise kurallı `proposal.py` yolunu ölçüyor;
model planlayıcısının gerçek çizim koşulu aşağıdaki `chain_model` ölçümlerinde ayrıca sınandı.

3B ve 8B modeller bu eski koşullarda geçerli plan üretmedi. Ancak sonuç yalnız model
kapasitesine veya şema derinliğine bağlanamaz:

- İstem `source` istemiyor, gönderilen `GeneralPlan` şeması `source` zorunlu tutuyordu.
- İstem `questions` istiyor, şema bu alanı yasaklıyordu.
- `verified_against` metadatasındaki referans STEP yolu isteme gidiyordu. Referans
  geometrisi yüklenmedi; dosya adı sızıntısı yine de deney sözleşmesine aykırıydı.

Bunlar `general-plan-v2` istemi ve `GeneralPlan reply v2` yanıt şemasıyla düzeltildi.
Kalıcı `GeneralPlan v1` kaynak zorunluluğunu korur; güvenilir kaynak kimliği uygulamada
atanır. Yanıtta sorulara izin verilir ve doğrulama metadatası isteme gönderilmez.

### Düzeltilmiş arayüzün canlı ölçümü — `planner-v2-3b-01`, `planner-v2-8b-01`

Aynı vaka (`plate-pocket-1`), aynı elle doğrulanmış ilişki kanıtı (`eval/relations/`), aynı
ayarlar (16384 bağlam, 4096 çıktı, sıcaklık 0, şema grameri) ve yeni etiketlerle iki model
sırayla ölçüldü. Ham yanıtlar, şema hataları, `stats` ve v2 kaynak örnekleri koşu
kayıtlarındadır; Git içi kopyası `eval/reports/planner-v2-live-evidence.json`. Sonuç:

| koşu | model | durum | süre sn | `done_reason` | şema hatası |
|---|---|---|---|---|---|
| `planner-v2-3b-01` | qwen2.5vl:3b | failed (planning) | 38.3 | `stop` | `parameters.diameter_mm`: `value` ve `expr` birlikte; `sketches.*.entities[*]`: `type` ayırıcısı yok |
| `planner-v2-8b-01` | qwen3-vl:8b-instruct | failed (planning) | 119.3 | `stop` | ifade ayrıştırılamadı: koordinat listesi tek ifade beklenen yere yazılmış |

Bu ölçümün değiştirdiği şey **başarısızlığın sınıfıdır**, kapasite hükmü değil:

- İki model de artık **tam bir JSON nesnesi** döndürüyor; `done_reason=stop`, kesilme yok.
  Eski 3B/8B koşularındaki "çıktı sınırında kesildi" ve "`source` verilemez" hataları
  tekrarlanmadı; eski arayüz çelişkisi artık geçerli bir açıklama değil.
- Kalan hata şema/ifade düzeyinde: 3B `value`/`expr` seçimini ve `type` ayırıcısını
  tutturamıyor, 8B ise ifade beklenen alana nokta listesi koyuyor. Sonraki denetimde v2
  yanıt şemasının bu seçim ve etiket zorunluluklarını taşımadığı görüldü; bu sonuçlar
  tek başına iç içe gövdenin model kapasitesini aştığını göstermez.
- 3B yanıtı uydurma izler taşıyor (`/100.0,0.0` şablonu, ilgisiz `d4/h1..h4` kaynak
  kimlikleri); bu, ölçü/geometri bağının denetlenmesi gerektiğinin kanıtıdır.
- Bu koşul hâlâ **metin ilişkileri** verir, görüntü göndermez; iki modelin de bu tek
  paftadaki başarısızlığı model sınıfı için kapasite hükmü değildir.

### Üç adımlı arayüz ve şema gramerinin sınırı — `planner-v2-split-3b-01`, sonda `planner-v2-split-probe-01`

PLAN §19.4'ün tek değişkenli deneyi koşuldu: tek çağrı yerine aynı kanıt üç dar soruya bölündü
(parametreler → profil → işlemler), her adıma yalnız kendi anahtarlarını taşıyan gramer verildi
ve üç yanıt aynı `GeneralPlan` sözleşmesiyle yargılandı. Tek çağrı referansı aynı kod durumunda
yeniden alındı (`planner-v2-3b-02`), böylece karşılaştırmadaki tek değişken arayüzdür. Her koşu
kaydı artık sorduğu istemin parmak izini taşır (`settings.prompt_sha256`; üç adımlı koşuda her
adım kendi `prompt_sha256` alanıyla), böylece "hangi soru hangi yanıtı doğurdu" sonradan
doğrulanabilir.

| koşu | arayüz | durum | çağrı | toplam sn | adım süreleri sn | ilk ihlal |
|---|---|---|---|---|---|---|
| `planner-v2-3b-02` | tek çağrı | failed (planning) | 1 | 39.1 | — | `parameters.diameter_mm`: `value` ve `expr` birlikte |
| `planner-v2-split-3b-01` | üç adım | failed (planning) | 3 | 71.3 | 35.6 / 15.5 / 20.3 | 7 parametrenin tamamı: `value` ve `expr` birlikte |

**Bölmek hatayı çözmedi, taşıdı.** Üç adımın üçü de geçerli JSON ve istenen anahtarlarla döndü
(adım düzeyinde hata yok, kesilme yok); ama birleşik plan yine sözleşmeyi çiğniyor: yedi
parametrede `value`+`expr` birlikte, eskiz ve işlem gövdelerinde ayırıcı etiket yok. Bölme ayrıca
adım başına hata atfını mümkün kıldı — artık "hangi alt soru bozuldu" okunabiliyor — ve duvar
saati 39 → 71 sn'ye çıktı (bellek tepe RSS 3829 → 5003 MiB).

**Sonraki denetimde düzeltilen yorum:** Bu eski sonuçlar `oneOf` desteğinin çalışmadığını
kanıtlamıyor. Gönderilen v2 `Parameter` şemasında `value`/`expr` için `oneOf` kuralı hiç
bulunmuyor; Python `model_validator` kuralı JSON Schema'ya otomatik aktarılmamış. Eskiz ve
operasyon tür etiketleri de Python varsayılanları nedeniyle `required` listesinde değil.
Dolayısıyla eski denemeler eksik kısıtlanmış bir arayüzü ölçmüştür.

Kalıcı CAD sözleşmesini değiştirme önerisi geri çekildi. `GeneralPlan reply v3`, eksik
kuralları yalnız model yanıt şemasında açıkça taşır; kalıcı `GeneralPlan v1` aynı kalır.
Aynı model ve aynı üç küçük istekte eski şema 0/3, v3 şema 3/3 alan sözleşmesi kontrolünü
geçti. Bu ölçüm geometri doğruluğu değildir; tam plandaki adlandırma, bağımlılık ve kapalı
profil kontrolleri ayrıca gerekir. Yeni denetim: `eval/reports/schema-audit.md`.

### Ürün yolu: çizimin kendi ölçümleri → model → CAD — `chain-model-3b-01`, `-04`, `-05`

PLAN §19.5'in istediği `chain_model` koşulu ve CLI yolu kuruldu. Artık iki planlayıcı **aynı kanıttan**
besleniyor: `read_sheet` okuma zincirini (observe → bind → meaning) milimetreye çeviriyor,
`chain_evidence` bunu planlayıcının istediği bloğa koyuyor — her basılı sayı kendi span kimliğiyle, her
iddia kendi çapa noktalarıyla (geometri kimliği + mm konumu), basılı ve ölçülen değeriyle, geometri ise
kontur (plaka: 120,87 × 80,56 mm, köşe r 10,05; plastik: 121,49 × 61,17, r 8,10) ve sayfa içindeki
dairelerin mm çap/merkezidir. Kural tabanlı `chain` ile model koşulu böylece yalnız **planlayıcıda**
ayrışıyor. Referans STEP, dosya adı ve elle doğrulanmış tablo bu koşula girmiyor; paftanın referansı
yalnız katı oluştuktan sonra çizim kontrolünde açılıyor (plakada 7 basılı sayı, 7 bağlanmış iddia, 12
çapa noktası, 5 daire; plastikte 14 / 4 / 8).

Kaynak doğrulaması da §19.5'in istediği gibi genişletildi: geçerli bir span kimliği artık tek başına
yetmiyor. `source: printed` bir parametre, atıf yaptığı span'ın **yazdığı** değeri taşımak zorunda —
basılı sayıyı ya da yanında basılan adedi (`4 x Ø6,80`) — ve planın kendi biriminde; ölçülen değeri
basılı gibi göstermek reddediliyor.

| koşu | vaka | planlayıcı | durum | hata sınıfı | okuma sn | model sn | sonuç |
|---|---|---|---|---|---|---|---|
| `chain-model-3b-01` | plate | kural (`chain`) | draft | ok | — | — | plan önerildi, katı kuruldu, çizim kontrolü geçti |
| `chain-model-3b-01` | plate | model | failed | planning | 1,7 | 34,0 | `sketches.g9.entities.0`: ayırıcı etiket (`type`) yok |
| `chain-model-3b-05` | plate | model | failed | planning | 1,8 | 32,2 | aynı ihlal, istem parmak izi aynı |
| `chain-model-3b-05` | plate | model (ilişki tablosu) | failed | planning | — | 33,8 | `parameters.diameter_mm`: `value` ve `expr` birlikte |
| `chain-model-3b-04` | plastic | kural (`chain`) | refused | reading | — | — | iki çap ölçüsü bekleniyordu, 0 okundu |
| `chain-model-3b-04` | plastic | model | failed | planning | 2,7 | 48,8 | `sketches.g7.entities.0`: ayırıcı etiket (`type`) yok |

Süreler **aşama** bazındadır (kayıttaki `stages.*.seconds`); koşu satırı toplamı okuma + modeldir:
`-01` 35,7 sn, `-05` 33,9 sn, `-04` 51,5 sn. `chain` satırı model çağırmaz, o yüzden iki süre sütunu
boştur; kural yolunun koşul toplamı plakada 8,7 sn (`propose` 2,0 + CAD 5,1 + çizim kontrolü 1,6),
plastikte 3,2 sn (`propose`, orada okuma reddiyle bitiyor).

**Ürün yolu çalışıyor; durduğu yer model katmanı.** Aynı paftada kural planlayıcısı ölçümlerden planı
çıkarıp katıyı kuruyor (draft/ok), model ise kanıtı okuduğu hâlde (parametreleri gerçek span
kimlikleriyle `pdf-0`…`pdf-6` adlandırdı, değerleri doğru yazdı) sözleşmeyi eskiz ve işlem
gövdelerinde çiğniyor: `entities[*]` ve `operations[*]` girdilerinde `type` / `op` ayırıcıları yok. Bu,
§19.4'te ölçülen `value`/`expr` ihlali gibi, gönderilen v2 şemada eksik kodlanan kurallardandır. Aynı sınıf iki farklı parça grubunda (plaka, plastik) ve dört koşuda çıktı;
plastikte kural planlayıcısı reddederken model yine aynı yerde düştü — yani hata kanıtın kaynağına
değil, modele/arayüze yazılmalıdır. Modelin adlandırma eğilimi de ölçüldü: parametreleri ve eskizleri
kanıtın kendi kimlikleriyle adlandırıyor (`pdf-0`, `g7`); kural katmanının eklediği şey bu kimliklerin
rol adlarına çevrilmesidir.

İstem parmak izi bu koşuda da işe yaradı: plaka kanıtıyla sorulan istem `chain-model-3b-01` ve
`chain-model-3b-05`'te bayt-aynıdır (`2f907af35104…`), ilişki tablosuyla sorulan `b22c951458ff…`.
Üç koşu boyunca soru değişmedi, yanıt aynı yerde kaldı.

Genişletilmiş kaynak doğrulaması kayıtlı hükümleri değiştirmedi: sekiz kayıtlı yanıt yeni yargıçla
yeniden yargılandı, hepsi aynı hükme ve aynı ilk hataya düştü. Kuralın sınanması ayrıca yapıldı:
plakanın yedi basılı parametresi (birim + adet dâhil) kabul ediliyor, ölçülen değeri basılı gösteren
aynı plan reddediliyor (`tests/test_planner.py`).

**Kayıt disiplini.** `chain-model-3b-02` (plastik) koşusunda `chain_model` satırı `skipped` düştü:
çalıştırıcı model istemcisini yalnız `reading`/`relations` koşulları için kuruyordu. Bu bir model
sonucu değil çalıştırıcı boşluğudur; düzeltildi, ölçüm yeni etiketle alındı (`-04`). `chain-model-3b-03`
ise benim taşımamla kesildi: koşu `status=running` (`active=chain_model`) iken klasörü
`out/interrupted/` altına aldım, süreç ölmemişti ve bir sonraki yazışında düştü — çıkış kodu 1,
`…/chain-model-3b-03/run.json.tmp` yok. Kayıt bu yüzden `chain_model` satırını hiç taşımıyor ve
kesilme nedenini de yazamıyor (o not da aynı klasöre yazılacaktı); neden yalnız süreç günlüğünde
duruyor. Bitmiş sayılmaz, ölçüm kümesinin dışında. Ayrıca aynı koşuda iki model koşulu çalıştığında ham
yanıtın ve derleme klasörünün ezilmemesi için koşul adı dosya adına eklendi
(`…-chain_model-candidate.json`); bu yüzden `chain-model-3b-01`'in ham yanıtı ilişki koşununkiyle
ezilmişti, yeni adlandırmada her koşulun kendi yanıtı duruyor.

**CLI teslimi:** `drawingto3d model-plan <çizim> <klasör>`. Çizimi okur, kanıtı `evidence.json`'a
yazar, yerel modeli çağırır, ham yanıtı `candidate.json`'a ve geçerliyse planı `plan.json`'a bırakır;
model şemaya uymazsa çıkış kodu 2 ve tek satır gerekçe verir. Çizim milimetreye çevrilemiyorsa model
hiç çağrılmaz. Varsayılan model uygulamanın kendi tercih sırasındadır (`qwen3-vl:8b-instruct` →
`qwen2.5vl:7b` → `qwen2.5vl:3b`), `--model` ile değiştirilir; `--split` §19.4 arayüzünü kullanır.

CLI gerçek bir çağrıyla sınandı: `drawingto3d model-plan "examples/pdf with steps/5/Plate With A
Pocket Drawing.PDF" out/cli-model-plan-plate` — kanıt 7 basılı sayı / 7 iddia / 5 daire olarak yazıldı,
varsayılan sıra gereği `qwen3-vl:8b-instruct` çağrıldı (97,62 sn; istem parmak izi `2f907af35104…`,
yani kapsayıcının sorduğu sorunun aynısı) ve yanıt gövdesi `} } } }` tekrarına düşüp bozuk kaldı:
`status=invalid` ("yanıtta JSON nesnesi yok"), `plan.json` yazılmadı, çıkış kodu 2, ham yanıt
`candidate.json`'da. Bu koşuda Ollama gövdesi `done_reason` vermedi; kayıt artık bu durumda
`answer_truncated=null` ("kesilme durumu bilinmiyor") yazar — sağlayıcının söylemediği bir şeyi
"kesilmedi" diye yazmak, kaydın sırtlayamayacağı bir iddiadır.

**Güncel karar:** Kalıcı sözleşmenin ayrımlarını kaldırma. Yanıt şemasındaki eksik
kurallar düzeltildi; v3 koşusunun kalan hata sınıfına göre tek değişkenli devam et.
Sıradaki görev PLAN Bölüm 21'de; önceki ayrık birleşim/kapasite hükmü geçerli değildir.

### v3 yanıt şemasıyla kontrollü yeniden ölçüm — `schema-v3-3b-01`

Kalıcı CAD şeması korunarak model yanıt grameri düzeltildi. Aynı üç küçük sondada alan
kontrolleri 0/3 → 3/3; ardından gerçek plaka yeniden ölçüldü. `general-plan-v2` istemi
ve ayarlar (16384/4096, sıcaklık 0, 3B) aynı: iki istem parmak izi de `chain-model-3b-05`
ile bire bir eşleşiyor. Ayrıntı `eval/reports/schema-audit.md`, ham kanıt
`schema-v3-probe-evidence.json` ve `schema-v3-live-evidence.json` dosyalarındadır.

| Koşul | Toplam / model sn | Sonuç | İlk tam plan hatası |
|---|---|---|---|
| `relations` | 51.49 / 51.47 | failed (planning) | `hole_spacing_X` adı geçersiz |
| `chain_model` | 83.90 / 82.21 | failed (planning) | `pdf-0` adı geçersiz |

İki yanıtın parametre/eskiz/işlem alanları ayrı ayrı doğrulanıyor, fakat tam planlar
geçersiz; **STEP yok**. Adlandırma tek kalan sorun da değil: ilişki yanıtı gövde üretmeden
kesme işlemleri istiyor, zincir yanıtında geçersiz aritmetik var ve ikisi de üretilmemiş
bir `result` adı veriyor. Sıradaki teslim adlandırma kuralını arayüze aktarıp semantik
hataları ölçmek; sırf geçerli JSON üretmek ürün başarısı sayılmıyor.

### Alt cevapları doğrulayarak ilerleme — `step-validation-3b-01`

Eski üç adımlı koşunun parametre cevabı yanlış atıflarla sonraki çağrıya aktarılıyordu.
Adım doğrulaması eklendi; değerlendirme aracının `--split` ve `--normalize-names`
seçenekleri iki model koşuluna da aktarılıyor. `names-3b-05` koşusunun yalnız ilişki yolu
üç adımlıydı; gerçek aday ayarlarıyla tablo artık bu koşuyu “karma” gösteriyor.

Yeni 3B koşusunda aynı istem/şema ve 16384/4096 ayarıyla `relations` 20.24 sn'de yanlış
kaynak atfında, `chain_model` 63.95 sn'de geçersiz eskiz adında durdu. İlişki yolunun
ilk istemi, şeması ve cevabı eski kayıtla bire bir aynı. Yeni akış bu cevabı profil
çağrısına taşımıyor. Gerçek çizim yolunda parametre yapısı/atıf kontrolü geçti, ancak
cep derinliği için kullanılan 7.82 ölçek değeri gibi anlam hataları sürüyor.

Tam plan ve STEP yok. Sıradaki iş kanıttan parametre seçimi (PLAN §21). Ham kayıt ve
karşılaştırma `step-validation-live-evidence.json`, eski cevap tekrar doğrulaması
`step-validation-replay.json`, yorumlar `step-validation-audit.md` dosyalarında.

### CAD ve geometri

Elle doğrulanmış planlar derleyiciden geçiyor. Denetim turundaki `audit-resources-v2`
koşusunda braket ve mil planları yeniden üretildi; iki sonuç `draft`, hata sınıfı `ok`.
Bu, PDF'nin otomatik yorumlandığı veya çizime göre tam doğrulama yapıldığı anlamına gelmez.
Delik konumu/adedi, cep derinliği, görünüş/kesit ve çözülmemiş ölçülerin denetimi açık iştir.

### Bellek ölçümünün düzeltilmesi

Eski ölçer `vm.swapusage` çıktısındaki ilk M değerini (`total`) kullanılan swap sayıyordu;
`vm_stat` sayfalarını 4096 bayt varsayıyordu. Bu M1 makinede bildirilen sayfa boyutu
16384 bayttır. Eski swap/boş/sıkıştırılmış sayfa değerleriyle model sığar/sığmaz kararı
verilemez; ham geçmiş değiştirilmeden tabloda geçersiz işaretlenir.

Ölçüm v2, `used` alanını ve bildirilen sayfa boyutunu kullanır; birim MiB'dir. Ham sistem
çıktıları kayda eklenir. Kaynak örnekleme yeni koşularda model yükleme aşamasını da kapsar.
Ollama RSS bütün birleşik belleği ölçmez; sistem swap değerleri diğer uygulamaları da içerir.
Denetimin sandbox koşusunda swap ve süreç ölçümüne erişim yoktu; bunlar `null` saklandı.
Bu koşu bir model yükü ölçümü değildir. Tam M1 model karşılaştırması yeniden yapılmalıdır.

### Kayıt bütünlüğü

Yeni koşular başlangıçta ve her tamamlanan vaka/koşuldan sonra atomik `run.json` kaydı
bırakır. Ctrl-C `interrupted`, hata `failed` olur; zorla öldürme son geçerli `running`
kaydını ve etkin adımı bırakır. Bu durum bitmiş koşu değildir. Aynı `--label` yeniden
kullanılamaz. Kaynak kod ve veri özetleri kaydedilir. Ara kayıt devam ettirme komutu
değildir; yeni etiketle yalnız eksik vaka/koşullar tekrar çalıştırılmalıdır.

## Kabul durumu

| Koşul | Durum |
|---|---|
| Eski çıktıların bulunması ve tablo tutarlılığı | Doğrulandı; altı eski koşu okunuyor, offering teşhisi tamamlanmamış |
| Model karşılaştırmasının uygulanmış olması | v2 arayüzüyle tek plakada iki model ölçüldü (3B 38.3 sn, 8B 119.3 sn); ikisi de şema düzeyinde başarısız. §19.4'ün üç adımlı arayüzü de denendi: hatayı çözmedi (3B 71.3 sn, tek çağrıya karşı 39.1 sn). Kapasite hükmü için ayrı deney gerekir |
| Şema gramerinin kısıtlayıcılığı | Önceki teşhis düzeltildi: v2 değer/ifade seçimini ve tür etiketlerinin zorunluluğunu kodlamıyordu. v3 yanıt şemasıyla aynı üç sondada alan kontrolleri 0/3 → 3/3; kalıcı plan değişmedi. Bu geometri başarısı değildir. |
| Bellek ölçümünün doğruluğu | v2 ölçüm gerçek model yükünde alındı: 3B takas +1.45 GiB tepe 9.6 GiB, 8B +2.46 GiB tepe 12.1 GiB, boş sayfa en az 14 MiB (8B sınırda) |
| Ölçü örneği ve doğru geometri bağına göre okuma | Açık; mevcut tablo sayısal değer kapsamını gösteriyor |
| Kaynak doğrulamasının genişletilmesi | Uygulandı: `source: printed` bir parametre, atıf yaptığı span'ın **yazdığı** değeri/adet'i ve birimini taşımak zorunda; sekiz kayıtlı yanıt yeni yargıçla aynı hükme düştü |
| Modelin gerçek çizim → plan → STEP akışına bağlanması | Yol kuruldu ve ölçüldü (`chain_model` koşulu + `drawingto3d model-plan`, iki parça grubunda): okuma/kanıt hazır, kural planlayıcısı katıyı kuruyor, model katmanı şema düzeyinde düşüyor. Uçtan uca **model planıyla** STEP hâlâ açık |
| Bağımsız genelleme ve ürün kabulü | Açık; pilot/saklı veri ve uçtan uca kontroller gerekli |

<!-- generated: tables -->

### Koşular

| koşu | başlangıç | model | koşullar | şema | vaka | sonuç | hata sınıfı | süre sn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| smoke | 2026-09-27 03:59 | yok (model dışı) | reading,chain | serbest metin | 2 | [legacy] draft=1 ok=1 refused=2 | ok=2 reading=2 | 391.5 |
| relations-3b-probe | 2026-09-27 04:07 | qwen2.5vl:3b * | relations | serbest metin | 1 | [legacy] failed=1 | planning=1 | 121.4 |
| relations-3b-structured | 2026-09-27 04:13 | qwen2.5vl:3b * | relations | serbest metin | 1 | [legacy] failed=1 | planning=1 | 243.7 |
| relations-8b-structured | 2026-09-27 04:18 | qwen3-vl:8b-instruct * | relations | serbest metin | 1 | [legacy] failed=1 | planning=1 | 147.4 |
| relations-8b-source-overridden | 2026-09-27 04:33 | qwen3-vl:8b-instruct * | relations | serbest metin | 1 | [legacy] failed=1 | planning=1 | 152.8 |
| floor-1 | 2026-09-27 04:36 | yok (model dışı) | reading,chain,verified_plan | json-schema | 12 | [legacy] draft=3 ok=3 partial=3 refused=13 | ok=6 reading=16 | 2129.7 |
| audit-resources-v2 | 2026-09-27 06:22 | yok (model dışı) | verified_plan | json-schema | 2 | [complete] draft=2 | ok=2 | 6.7 |
| planner-v2-3b-01 | 2026-09-27 06:38 | qwen2.5vl:3b * | relations | json-schema | 1 | [complete] failed=1 | planning=1 | 44.4 |
| planner-v2-8b-01 | 2026-09-27 06:39 | qwen3-vl:8b-instruct * | relations | json-schema | 1 | [complete] failed=1 | planning=1 | 130.4 |
| planner-v2-3b-02 | 2026-09-27 06:54 | qwen2.5vl:3b * | relations | json-schema | 1 | [complete] failed=1 | planning=1 | 45.1 |
| planner-v2-split-3b-01 | 2026-09-27 06:55 | qwen2.5vl:3b * | relations | üç adımlı | 1 | [complete] failed=1 | planning=1 | 76.2 |
| chain-model-3b-01 | 2026-09-27 07:11 | qwen2.5vl:3b * | chain,chain_model,relations | json-schema | 1 | [complete] draft=1 failed=2 | ok=1 planning=2 | 86.9 |
| chain-model-3b-02 | 2026-09-27 07:14 | qwen2.5vl:3b | chain,chain_model | json-schema | 1 | [complete] refused=1 skipped=1 | reading=1 unsupported=1 | 6.0 |
| chain-model-3b-04 | 2026-09-27 07:17 | qwen2.5vl:3b | chain,chain_model | json-schema | 1 | [complete] failed=1 refused=1 | planning=1 reading=1 | 64.3 |
| chain-model-3b-05 | 2026-09-27 07:18 | qwen2.5vl:3b * | chain_model,relations | json-schema | 1 | [complete] failed=2 | planning=2 | 72.2 |
| schema-v3-3b-01 | 2026-09-27 14:08 | qwen2.5vl:3b * | relations,chain_model | json-schema | 1 | [complete] failed=2 | planning=2 | 140.1 |
| names-3b-02 | 2026-09-27 15:43 | qwen2.5vl:3b * | relations,chain_model | json-schema | 1 | [complete] failed=2 | planning=2 | 225.4 |
| names-3b-03 | 2026-09-27 15:47 | qwen2.5vl:3b * | relations | json-schema | 1 | [complete] failed=1 | planning=1 | 183.3 |
| names-3b-04 | 2026-09-27 15:50 | qwen2.5vl:3b * | relations | json-schema | 1 | [complete] failed=1 | planning=1 | 185.3 |
| names-3b-05 | 2026-09-27 15:54 | qwen2.5vl:3b * | relations,chain_model | karma: json-schema / üç adımlı | 1 | [complete] failed=2 | planning=2 | 237.6 |
| step-validation-3b-01 | 2026-09-27 17:18 | qwen2.5vl:3b * | relations,chain_model | üç adımlı | 1 | [complete] failed=2 | planning=2 | 90.3 |
| profile-3b-01 | 2026-09-27 17:38 | qwen2.5vl:3b * | relations,chain_model | adım başına profil | 1 | [complete] failed=2 | planning=2 | 67.5 |
| ids-3b-01 | 2026-09-27 18:38 | qwen2.5vl:3b * | relations,chain_model | adım başına profil | 1 | [complete] failed=2 | planning=2 | 53.2 |
| params-3b-01 | 2026-09-27 19:20 | qwen2.5vl:3b * | relations,chain_model | adım başına profil | 1 | [complete] failed=2 | planning=2 | 53.7 |
| suggest-3b-01 | 2026-09-27 19:30 | qwen2.5vl:3b * | relations,chain_model | adım başına profil | 1 | [complete] failed=2 | planning=2 | 46.1 |

`*` koşunun bağlamı kısmen elle doğrulanmış ilişki tablosundan gelir (`eval/relations/`): o koşu otomatik PDF → STEP başarısı değil, planlama ve CAD katmanlarının ayrı ölçümüdür (PLAN Bölüm 18B).

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
| audit-resources-v2 | bracket_linear_pattern | verified_plan | draft | ok | plan derleyiciden geçti; hacim 22084.3806 mm³, beklenti {'bbox': ['length', 'height', 'width'], 'volume': 'area * width - 2 * pi * (hole_d / 2) ** ... |
| audit-resources-v2 | shaft_revolve_cross_hole | verified_plan | draft | ok | plan derleyiciden geçti; hacim 13544.7373 mm³, beklenti {'bbox': ['2 * flange_r', '2 * flange_r', 'length'], 'volume': None} |
| planner-v2-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parameters.diameter_mm: parametrede value veya expr alanlarından tam biri bulunmalı; sketches.outline_... |
| planner-v2-8b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: ifade ayrıştırılamadı: ':[-60.0, -40.0], [-60.0, 40.0] ], ' |
| planner-v2-3b-02 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parameters.diameter_mm: parametrede value veya expr alanlarından tam biri bulunmalı; sketches.outline_... |
| planner-v2-split-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parameters.hole_spacing_X: parametrede value veya expr alanlarından tam biri bulunmalı; parameters.hol... |
| chain-model-3b-01 | plate-pocket-1 | chain | draft | ok | plan önerildi, katı kuruldu, plan denetimi geçti |
| chain-model-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: sketches.g9.entities.0: Unable to extract tag using discriminator 'type'; sketches.g11.entities.0: Una... |
| chain-model-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parameters.diameter_mm: parametrede value veya expr alanlarından tam biri bulunmalı; sketches.outline_... |
| chain-model-3b-02 | plastic-enclosure-1 | chain | refused | reading | tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1} |
| chain-model-3b-02 | plastic-enclosure-1 | chain_model | skipped | unsupported | model koşusu istenmedi (--no-model) |
| chain-model-3b-04 | plastic-enclosure-1 | chain | refused | reading | tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1} |
| chain-model-3b-04 | plastic-enclosure-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: sketches.g7.entities.0: Unable to extract tag using discriminator 'type'; sketches.g196.entities.0: Un... |
| chain-model-3b-05 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: sketches.g9.entities.0: Unable to extract tag using discriminator 'type'; sketches.g11.entities.0: Una... |
| chain-model-3b-05 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parameters.diameter_mm: parametrede value veya expr alanlarından tam biri bulunmalı; sketches.outline_... |
| schema-v3-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: şema hatası: parametre adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'hole_spacing_X' |
| schema-v3-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: parametre adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'pdf-0' |
| names-3b-02 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: model yanıt vermedi: yerel model yanıt vermiyor; buluta düşülmez |
| names-3b-02 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: ifade ayrıştırılamadı: '/hole_spacing_x' |
| names-3b-03 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: model yanıt vermedi: yerel model yanıt vermiyor; buluta düşülmez |
| names-3b-04 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: yanıtta JSON nesnesi yok (çıktı sınırında kesildi) |
| names-3b-05 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım profile: yanıtta JSON nesnesi yok (çıktı sınırında kesildi) |
| names-3b-05 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: şema hatası: ifade ayrıştırılamadı: '/hole_spacing_x' |
| step-validation-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım parameters: parametre 'hole_spacing_x': kanıtta olmayan ölçü kaydına atıf ['h1', 'h2']; adım parameters: param... |
| step-validation-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: adım profile: şema hatası: eskiz adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'pdf-0' |
| profile-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım parameters: parametre 'hole_spacing_x': kanıtta olmayan ölçü kaydına atıf ['h1', 'h2']; adım parameters: param... |
| profile-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: adım profile 1/6 (outline): şema hatası: ifadede izin verilmeyen fonksiyon: 'x(6.84/2)' |
| ids-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: ifadede tanımsız parametre: 'd2' |
| ids-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: parametre adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'pdf-0' |
| params-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: ifadede tanımsız parametre: 'd7' |
| params-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: parametre adı küçük harfle başlamalı; rakam ve alt çizgi kullanılabilir: 'pdf-0' |
| suggest-3b-01 | plate-pocket-1 | relations | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: ifadede tanımsız parametre: 'd1' |
| suggest-3b-01 | plate-pocket-1 | chain_model | failed | planning | model şemaya uyan plan vermedi: adım parameters: şema hatası: ifadede tanımsız parametre: 'diameter_2' |

### Koşu kaynakları (ölçüm sürümü denetlenir)

| koşu | kullanılan takas başı MiB | kullanılan takas tepe MiB | boş sayfa en az MiB | ollama RSS tepe MiB |
| --- | --- | --- | --- | --- |
| smoke | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 14.5 |
| relations-3b-probe | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 3735.3 |
| relations-3b-structured | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 4953.1 |
| relations-8b-structured | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 8295.3 |
| relations-8b-source-overridden | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 8295.6 |
| floor-1 | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | 31.3 |
| audit-resources-v2 | None | None | 57.922 | None |
| planner-v2-3b-01 | 8354.12 | 9846.19 | 56.312 | 3953.0 |
| planner-v2-8b-01 | 9774.19 | 12428.75 | 14.156 | 8290.8 |
| planner-v2-3b-02 | 10105.88 | 10120.12 | 55.531 | 3829.3 |
| planner-v2-split-3b-01 | 10096.12 | 10719.25 | 55.141 | 5003.1 |
| chain-model-3b-01 | 9552.44 | 10996.75 | 55.797 | 3849.1 |
| chain-model-3b-02 | 10212.5 | 10212.5 | 57.953 | 33.7 |
| chain-model-3b-04 | 11289.0 | 11289.0 | 55.172 | 3869.2 |
| chain-model-3b-05 | 11063.44 | 11101.44 | 55.516 | 5034.0 |
| schema-v3-3b-01 | 9678.31 | 10349.38 | 50.453 | 5016.1 |
| names-3b-02 | 9911.81 | 11187.5 | 29.328 | 5082.7 |
| names-3b-03 | 10995.5 | 10995.5 | 55.156 | 4785.5 |
| names-3b-04 | 10819.5 | 10838.69 | 14.125 | 5016.8 |
| names-3b-05 | 10766.69 | 10930.31 | 55.516 | 5023.4 |
| step-validation-3b-01 | 7647.62 | 10201.94 | 56.141 | 3838.5 |
| profile-3b-01 | 8356.94 | 10383.44 | 55.594 | 3829.2 |
| ids-3b-01 | 7303.44 | 10824.44 | 14.125 | 3834.4 |
| params-3b-01 | 7505.75 | 9789.69 | 56.328 | 3835.2 |
| suggest-3b-01 | 9325.56 | 10113.06 | 56.141 | 3871.2 |

Eski swap alanları `used` yerine `total` okuyordu; sayfa hesabı sabit 4096 bayt varsayıyordu. Bu değerler kaynak kayıtlarda korunur, bellek kararı için kullanılmaz. Ölçüm v2 işletim sisteminin sayfa boyutunu ve `used` alanını kullanır. Sistem sayıları diğer uygulamaları da içerir; Ollama RSS toplam birleşik bellek tüketimi değildir.

### Okuma tabanı (kapı sonrası kapsam)

Katman `vektör` = PDF'in kendi metin katmanı, `raster` = görüntüden okuma. Kapsam, sayısal değer kümesinin kapsamıdır; her ölçü örneğinin, sembolün veya bağın doğruluğu değildir.

| vaka | katman | span | basılı | kapsam | ankrajlı | px/mm | gürültü |
| --- | --- | --- | --- | --- | --- | --- | --- |
| exercise-1-vector | raster (vektör paftanın render'ı) | 18 | 13 | 8/13 | 18 | 3.8080 | 8 |
| exercise-1-vector | vektör | 17 | 13 | 13/13 | 17 | 3.8250 | 0 |
| exercise-1 | raster | 15 | 13 | 6/13 | 15 | 5.7310 | 6 |
| exercise-12 | vektör | 30 | 20 | 19/20 | 30 | 1.5500 | 3 |
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
