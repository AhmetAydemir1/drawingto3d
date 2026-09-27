# drawingto3d — devralan AI ajanı için uygulama planı

Tarih: 2026-09-27 · Durum: genel CAD altyapısı ve ilk okuyucu dilimleri uygulandı;
yeni çizimlerde model değerlendirmesi, hedefli eğitim ve ürün doğrulaması açık.

## Devralan ajana görev

Bu belgeyi uygulama görevi olarak kullan. Önce mevcut kodu ve değişiklikleri doğrula,
ardından aşağıdaki aşamaları ölçülebilir teslimlerle uygula. Kullanıcının hedefi M1 / 16 GB
üzerinde çevrimdışı, yeni teknik çizimlere genellenen PDF/PNG/JPG → STEP aracıdır.
Verilmiş örnekler test içindir; her birine ayrı parça şablonu yazmak hedefi karşılamaz.
Sohbet geçmişine ihtiyaç duyduğun bir karar olursa önce bu belgedeki kapsamı ve kaynak
kayıtlarını kullan. Belirsiz uygulama ayrıntılarını gerekçesiyle çöz; veri veya donanım
eksikliğini tamamlanmış sonuç gibi sunma.

**Başlangıç noktası:** Bölüm 9'daki ortamı doğrula; Bölüm 7'deki güncel ölçüm dilimini
uygula. Genel şema ve derleyici zaten var; bunları yeniden kurma. Bölüm 18, hazır model
karşılaştırması, veri hazırlığı ve gerekirse eğitim için güncel uygulama sözleşmesidir.
Yeni gerçek veri beklenirken değerlendirme aracını, sentetik veri üretimini ve raster
ankrajlarını geliştirebilirsin; yeni parçalara genelleme başarısını açık iş bırak.

**Gereken teslim paketi:** Bu `PLAN.md` ile birlikte güncel proje çalışma ağacı.
Devralırken commit edilmemiş ve izlenmeyen dosyaları `git status` ile kontrol et;
varsa bunları da teslim paketine dahil et.
Başka bilgisayarda `.venv` klasörlerini kopyalamak yerine uyumlu ortamları yeniden kur.

## 1. Hedef ve yaklaşım

M1 / 16 GB MacBook üzerinde, kurulumdan sonra internet gerektirmeden PDF, PNG ve JPG
teknik çizimlerini okuyup ölçülere bağlı, düzenlenebilir bir CAD planından STEP üretmek.
Başarı, geliştirmede kullanılmamış parçalar üzerinde ölçülecek.

Kullanıcının verdiği dosyalar test örnekleridir. Her yeni parça için ayrı tanıyıcı veya
şablon yazılması ürünün geliştirme yöntemi olmayacak. Sistem ortak işlemleri öğrenilmiş
görsel yorum, geometri ve ölçü ilişkileriyle bir araya getirecek:

- Kapalı bir profili uzatma: `extrude`.
- Bir kesiti eksen etrafında döndürme: `revolve`.
- Hacim ekleme ve çıkarma: birleşim, delik, kör cep ve kanal.
- Aynı işlemi çizgisel veya dairesel düzende tekrarlama.
- Kenarları yuvarlama ve pah kırma; bunlar sağlam kenar seçimi geliştikten sonra eklenecek.

Örneğin bir braket profil uzatma + deliklerden; kademeli bir mil profil döndürme +
ek kesmelerden oluşabilir. Yeni bir parça bu işlemleri farklı sırada kullanabilmeli.
Parça adı, dosya adı, sabit delik sayısı veya örneğin ölçüleri üretim kararını belirlememeli.

İlk sürümün kapsamı, çizgi/yay/daire profilleriyle tanımlanabilen tek parçalı mekanik
teknik çizimlerdir. Ortogonal görünüşler, kesitler, mm/inç ve açık ölçülendirme önceliklidir.
Çok sayfalı PDF'de sayfa seçimi sağlanacak; sayfalar arasında otomatik parça birleştirme
sonraki kapsamdır. Fotoğraftan serbest biçimli yüzey, montaj, vida helisi, sweep/loft ve
GD&T'den imalat doğrulaması ilk teslimin başarı iddiasına dahil değildir. Bu bilgiler
çizimde bulunursa kaybolmadan raporlanacak; destek durumu kullanıcıya gösterilecek.

Eksik görünüş veya ölçü nedeniyle birden fazla katı mümkünse sistem bunu gösterecek ve
gerekli bilgiyi soracak. Her görüntünün tek ve kesin bir STEP karşılığı olduğu varsayılmayacak.

Hedef, desteklenen işlemlerin yeni birleşimlerini okuyabilen genel bir araçtır.
"Herhangi bir PDF'de koşulsuz doğru sonuç" ürün vaadi değildir. Başarılı normal akış
dosya yükleme → otomatik plan → kontroller → STEP olacak; eksik bilgide program ilgili
görünüşü işaretleyip kısa bir soru soracak. Eğitim, çizimde bulunmayan bilgiyi kanıt yapmaz.

## 2. Mevcut durum ve korunacak yatırım

`plate.py` belirli bir vektör düzenini tanıyor: 13 alt yol, dört köşe deliği ve merkez cep
gibi yapısal koşulları var. Parametrelerin değişebilmesi, farklı parçaları çözebildiğini
kanıtlamıyor. Mevcut örnekte referansla sıfır hacim farkı elde edilmesi geçerli bir yerel
sonuçtur; genel dönüşüm başarısı değildir. Bu çalışmada bir yapay zekâ modeli eğitilmedi.

| Mevcut parça | Yeni düzende kullanımı |
|---|---|
| `ingest.py`, PDF metin katmanı, OCR, çizgi/ankraj çıkarma | Kaynak gözlemlerini ortak biçime aktaran giriş katmanı |
| `views.py`, `scale.py`, `roles.py` | Görünüş, ölçek ve ölçü bağlama için denetlenebilir başlangıç; doğrulukları ayrıca ölçülecek |
| `schema.py` içindeki `FeatureGraph` | Genel temsil için incelenecek; tek sürümlü şemaya geçilecek |
| `geo.py`, CadQuery, `cadrun.py` | Ortak CAD işlemleri, STEP dışa aktarma ve yeniden açma kontrolleri |
| `plan.py` içindeki kaynak kaydı ve düzenleme | Genel plana aktarıldı; eski kayıt uyumluluğu korunacak |
| `general.py`: `GeneralPlan`, derleyici, parametre düzenleme, STEP kontrolleri | Uygulanmış ortak sözleşme; model ve eğitim hedefleri bunun sürümüne bağlanacak |
| `observe.py`, `raster.py`, `bind.py`, `meaning.py`, `proposal.py` | Uygulanmış ilk okuma dilimleri; yeni çizimlerde kapsam ve hata ölçümü yapılacak |
| `plate.py`, `PlatePlan`, `eval/plate_plan.py` | Dar kapsamlı karşılaştırma deneyi ve regresyon kaydı |
| Yerel arayüz, yükleme izolasyonu, önizleme, oturum kaydı | Genel plan inceleme ve düzeltme arayüzünün temeli |

Yeni varsayılan akış hazır olduğunda plaka tanıyıcısı deneysel seçeneğe taşınacak.
Eski serbest Python üreten model yolu da deneysel kalacak. Genel akışın çözemediği çizim
sessizce eski yola geçirilip başarılı sayılmayacak. Bu değişiklikler bu plan oturumunda yapılmadı.

`proposal.py` şu anda belirli kontur ve çap ilişkileri bekliyor. Genel derleyiciyi kullanması,
okuyucunun genel olduğunu göstermiyor. Raster gözlemci var; ölçü ankrajları ve ölçek
kalibrasyonu eksik. Bağımsız pilot/saklı kümeleri boş. Bölüm 11–17 geçmiş uygulama
kayıtlarıdır; oralardaki "sıradaki dilim" notları yerine Bölüm 7 ve 18 uygulanacak.

## 3. Ortak işlem hattı

```text
PDF / PNG / JPG
  → kaynak gözlemleri: metin, çizgi, yay, daire, ölçü oku, kesit, görünüş
  → ölçü ve geometri ilişkileri: hangi ölçü hangi özelliğe bağlı?
  → sınırlı sayıda aday CAD işlem planı
  → tip ve kısıt kontrolü → deterministik CAD üretimi
  → STEP'i yeniden açma + çizim görünüşleriyle karşılaştırma
  → doğrulanmış sonuç / düzeltme sorusu / desteklenmeyen durum
```

### A. Kaynağı koruyan gözlemler

Vektör PDF ve raster için farklı okuyucular aynı kayıtları üretecek. Her gözlem kaynak
dosya özeti, sayfa, görünüş, koordinat dönüşümü, sınır kutusu, geometri kimliği ve okuma
yöntemini taşıyacak. Ölçü, sadece `50 mm: diameter` metnine indirgenmeyecek.

Basılı değer, birim, çap/yarıçap/açı/adet, okların bağlandığı geometriler ve alternatif
okumalar birlikte tutulacak. Aynı sayı iki yerde yazıyorsa iki ayrı gözlem olacak.
PDF nesne gruplaması, döndürme ve sayfa ölçeği kaynak biçiminin ayrıntıları olarak çözülecek.
Rasterda düşük kaliteli alanlar için yerel kırpma ve yeniden okuma kullanılacak.

### B. Ölçü ilişkileri ve belirsizlik

Görünüş eksenleri, izdüşüm düzeni, kesit ilişkileri, eşmerkezlilik, simetri ve ölçü
zincirleri bir ilişki grafiğinde tutulacak. Basılı bir ölçünün hangi iki kenara, deliğe
veya kesit derinliğine ait olduğu açıkça kaydedilecek.

Parametrelerin kaynak türleri ayrı olacak: **basılı**, **kısıtlardan türetilmiş**,
**varsayılmış**, **kullanıcı tarafından girilmiş**. Türetme bağımlılıkları saklanacak;
bir ölçü değişince bağlı ölçüler yeniden hesaplanacak. Çizimin piksel ölçeğinden çıkan
yaklaşık değerler kesin imalat ölçüsü gibi gösterilmeyecek. Modelin bildirdiği güven
puanı tek başına doğrulama sayılmayacak.

### C. Genel CAD planı

Tek sürümlü plan; parametreler, kaynak referansları, yerel koordinat sistemleri, çizgi/yay
profilleri ve sıralı CAD işlemlerinden oluşacak. Her işlem girdisini ve ürettiği gövdeyi
adlandıracak. Parametre ifadeleri izin verilen aritmetikle sınırlanacak; birim uyumu,
döngüsel bağımlılık, kapalı profil ve geçerli işlem derinliği üretimden önce denetlenecek.

Yerel model görsel yorum ve yapılandırılmış plan önerisi verecek. Son CAD üretimini
izin verilen işlemleri uygulayan derleyici yapacak. Kenarlar ve yüzler, değişince bozulan
liste sıra numaraları yerine konum, yön ve geometrik ilişkiyle seçilecek.

CadQuery'nin STEP içe/dışa aktarma ve SVG izdüşüm desteği bu katman için mevcut bir temel
sağlıyor. Bu yeteneklerin varlığı, çizimi doğru yorumlama sorununu çözmüş olduğumuz
anlamına gelmiyor. [CadQuery belgeleri](https://cadquery.readthedocs.io/en/latest/importexport.html)

### D. Üretimden sonra bağımsız kontrol

Kontrol iki ayrı soruyu yanıtlayacak: **Katı plana uyuyor mu? Plan çizime uyuyor mu?**
Tek geçerli katı, doğru dış boyut ve benzer hacim ikinci soruyu tek başına karşılamıyor.

- Dışa aktarılan STEP yeniden açılıp katı/geçerlilik ve işlem sonuçları denetlenecek.
- Deliklerin adet, çap, konum ve derinlikleri; ceplerin ve duvarların ölçüleri kontrol edilecek.
- Katının ilgili görünüşleri ve kesitleri çizimdeki geometrik kanıtlarla karşılaştırılacak.
  Yazı ve ölçü çizgileri siluet karşılaştırmasına dahil edilmeyecek.
- Açıklanmayan ölçüler, çelişen görünüşler ve kritik varsayımlar denetim raporunda kalacak.
- En fazla üç aday plan ve iki düzeltme turu başlangıç sınırı olacak. Çözülemeyen durumda
  aynı işlemi sınırsız denemek yerine ilgili soru veya başarısızlık nedeni gösterilecek.

## 4. M1 / 16 GB çalışma stratejisi

İlk adım eğitim öncesi ölçümdür. Hazır yerel modeller aynı geliştirme çizimleri ve aynı
yapılandırılmış görevlerle karşılaştırılacak. Sonuçlara göre hedefli LoRA eğitimi veya
küçük algılayıcı eğitimi yapılabilecek; karar koşulları Bölüm 18'de. Model sürümü,
nicemleme, bağlam uzunluğu ve görüntü boyutu sonuçlarla birlikte kaydedilecek.

M1 / 16 GB üzerinde önce küçük, nicemlenmiş modeller denenecek. 3–4B sınıfı başlangıç
adayıdır; 7–8B ancak bellek/süre ölçümü elverirse karşılaştırmaya alınacak. Bu aralıklar
ölçülmüş uygunluk sonucu değildir. Küçük modele LoRA denemesi yapılabilir; görsel
çözünürlük ve eğitim ara hesapları belleği artırır. Büyük bir temel modeli sıfırdan
eğitmek bu cihazın planına dahil değildir. Daha güçlü donanımda eğitilen modelin burada
çalışması mümkündür; son model bu Mac'te ayrıca sınanacak. Dış GPU harcaması veya özel
çizimleri başka sisteme yükleme bu plan güncellemesiyle yetkilendirilmiş değildir.

- Aynı anda tek dönüşüm ve tek yüklü büyük model; görsel okuma ile planlama sırayla.
- Tüm sayfayı her ölçü için tekrar göndermek yerine görünüş/kırpma bazında toplu okuma.
- Dosya özeti ve ayarlara bağlı ara sonuç önbelleği; değişen aşamayı yeniden çalıştırma.
- Bağlam uzunluğu, çözünürlük ve model büyüklüğünü pilot ölçüme göre seçme.
- Model işi bitince belleği bırakma; CAD işçisinde süre sınırı ve iptal desteği.
- İlk kurulumda bağımlılıklar ve model dosyaları hazırlanacak; normal dönüşümde
  dış bağlantı, otomatik indirme veya bulut yedeğine geçiş gerekmeyecek.

Ollama bağlam uzunluğu ve paralellik ayarları bellek ihtiyacını etkiliyor; `keep_alive`
ile modeli boşaltmak ve bulut özelliklerini kapatmak mümkün. Bunlar yapılandırılacak,
ardından ağ bağlantısı kesilmiş durumda dönüşüm denenecek.
[Ollama belgeleri](https://docs.ollama.com/faq)

Pilot koşularda soğuk/sıcak başlangıç, aşama süreleri, bellek baskısı, swap değişimi ve
OOM kaydedilecek. Diskteki model boyutu RAM kullanımı sayılmayacak. Başlangıç performans
hedefi medyan ≤3 dakika, p95 ≤10 dakika ve art arda işlerde sürekli bellek büyümesi olmaması.
**Bunlar ölçülmüş sonuç veya garanti değildir.** İlk aşamada erişilebilirlikleri sınanacak;
olmazsa kırpma/bağlam/model boyutu veya otomasyon kapsamı değiştirilecek.

## 5. Örneğe bağımlılığı ortaya çıkaracak değerlendirme

### Veri ayrımı

1. Mevcut altı örneğin tamamı görülmüş geliştirme/regresyon verisidir.
2. İlk pilot için en az 10 yeni parça toplanacak; farklı işlem birleşimleri, ölçülendirme
   düzenleri ve PDF üreticileri içerecek. Veri kaynağı ve kullanım hakkı kaydedilecek.
3. Ürün değerlendirmesi için geliştirmede kullanılmayan en az 20 ayrı parça ayrılacak.
   En az 10'u raster girdi içerecek; vektör ve raster sonuçları ayrı raporlanacak.
4. Aynı parçanın PDF, PNG, JPG, farklı çözünürlük ve yakın parametrik varyantları aynı
   grupta kalacak. Dosya bazında rastgele ayırmak genelleme testi sayılmayacak.
5. Sentetik CAD/çizim çiftleri birim ve işlem testlerine yardımcı olacak; gerçek, bağımsız
   teknik çizimler değerlendirmede ayrıca bulunacak. Sadece aynı üreticinin sentetik
   çıktılarıyla ürün başarısı ilan edilmeyecek.
6. Saklı test seçimi ve beklenen sonuçlar geliştirme döngüsünden ayrı tutulacak; test
   hatalarına bakıp düzeltme yapılan örnekler sonraki turda regresyon kümesine taşınacak.

Referans STEP yalnız değerlendirme sürecine verilecek. Üretim API'si referans yolunu
almayacak. Referansı olmayan çizimler okuma değerlendirmesinde kullanılabilecek;
geometrik doğruluk iddiası için bağımsız kontrol edilmiş referans hazırlanacak.

### Ölçütler ve geçiş koşulları

| Katman | Raporlanacak sonuç |
|---|---|
| Okuma | Ölçü örneği bazında doğru/eksik/fazla okuma; sayı, birim, sembol ve adet |
| Bağlama | Ölçünün doğru görünüşe, kenara, deliğe ve derinliğe bağlanma oranı |
| CAD üretimi | Geçerli STEP, işlem hatası, zaman aşımı ve desteklenmeyen işlem sayıları |
| Geometri | Özellik ölçüleri/konumları, dış boyut, hacim ve simetrik hacim farkı |
| Kullanıcı yükü | Otomatik doğru sonuç ve kullanıcı düzeltmesiyle doğru sonuç ayrı; soru/düzeltme sayısı |
| Kaynak | Süre dağılımı, bellek baskısı, swap ve art arda işlerde kaynak büyümesi |

Referans karşılaştırmasında birim ve koordinat eşlemesi önceden tanımlanacak; yanlış
ölçeği gizleyen yeniden ölçekleme yapılmayacak. Şekil farkı için normalize simetrik
hacim farkı kullanılabilecek; küçük bir deliğin eksikliğini kaçırmamak için özellik
kontrolleri de zorunlu kalacak. Ölçü toleransları çizime göre değerlendirmeden önce
kaydedilecek. Belirtilmemiş yüzey ayrıntıları, nominal ölçü doğruluğundan ayrı raporlanacak.

İlk ürün hedefi, kapsam içindeki saklı test parçalarının en az %80'inde kullanıcı
düzeltmesi gerektirmeyen geometrik doğruluk; kalanlarda anlaşılır soru veya başarısızlık
nedeni. Örneğin 20 parçada en az 16 doğru sonuç. Yanlış olup doğrulanmış gösterilen bir
sonuç sürümün geçmesini engelleyecek. Başarı yalnız çıktı üretilen parçalar üzerinden
hesaplanmayacak; reddedilen ve zaman aşımına uğrayan kapsam içi parçalar paydaya dahil.
Küçük bir test kümesindeki sıfır hata, bütün çizimlerde sıfır hata garantisi değildir.

## 6. Uygulama sırası

Takvim, veri hazırlığı ve ilk pilot ölçülmeden sabitlenmeyecek. Her aşama aşağıdaki
teslim ve geçiş koşuluyla bitecek; çalışmayan varsayım sonraki aşamalara taşınmayacak.

| Aşama | İş ve somut teslim | Geçiş koşulu |
|---|---|---|
| **0 — Ölçüm ve uygulanabilirlik** | Altı örneği regresyon olarak işaretle; yeni pilot/saklı veri manifesti ve özellik etiketlerini hazırla. Modelin ölçü bağlama/işlem önerme kabiliyetini CAD üretiminden ayrı dene. M1 süre/bellek başlangıç raporu çıkar. | Veri ayrımı ve tekrarlanabilir rapor hazır; modelin hangi alt görevlerde kullanılacağı kanıtla belirlenmiş. Başarı yetersizse tam otomasyon iddiası daraltılır. |
| **1 — Ortak plan ve CAD derleyicisi** | Mevcut şemaları birleştir; kaynaklı parametreler, profiller, extrude/revolve, ekleme/çıkarma ve tekrar işlemlerini uygula. Eski plaka planını bu işlemlere çeviren uyumluluk katmanı ekle. | Elle doğrulanmış en az 10 farklı işlem birleşimi doğru STEP üretir. Geçersiz plan reddedilir; ölçü düzenlemesi bağımlı geometriye yansır. Bu aşama çizim okuma başarısı sayılmaz. |
| **2 — Ortak çizim okuma** | PDF vektörlerini nesne gruplamasından bağımsız çıkar; raster okuyucuyu aynı gözlem biçimine bağla. Görünüş/kesit ayırma, ölçü ankrajları ve birimleri koru. | Pilotun PDF/PNG/JPG girdilerinde ölçü ve bağlama hataları nesne bazında raporlanır. Yeni parça için özel tanıyıcı gerektiren boşluklar kayıtlıdır. |
| **3 — İlişkilerden plan önerme** | Ölçü zincirleri ve görünüş eşleşmelerini kur; yerel modelden şemaya uyan adaylar al; kısıtlarla ele. Desteklenmeyen işlemi ve eksik ölçüyü tanımla. | Pilot parçalarında aynı genel yol kullanılır; örnek adına/aileye göre kod dallanması yoktur. Belirsiz derinlik veya çelişkili ölçü sessizce tamamlanmaz. |
| **3E — Gerekirse hedefli eğitim** | Bölüm 18'e göre eğitim/doğrulama verisi, sentetik üretici ve küçük LoRA veya algılayıcı deneyi hazırla; hazır modelle aynı koşullarda karşılaştır. | Ayrı doğrulama kümesinde önceden belirlenen hedef sağlanır, uçtan uca doğruluk gerilemez ve M1 bütçesi korunur. Fayda yoksa hazır model korunur; eğitim zorunlu aşama değildir. |
| **4 — Çizime göre doğrulama** | Plan→katı ve çizim→katı denetimlerini ayır. İzdüşüm/kesit karşılaştırması ve sınırlı düzeltme döngüsü ekle. Geometrik kenar seçimi hazırsa pah/yuvarlamayı genişlet. | Yanlış konumlu delik, eksik cep, yanlış derinlik ve yanlış görünüş eşlemesi içeren olumsuz testler doğrulanmış sayılmaz. |
| **5 — Yerel ürün ve saklı test** | Genel özellik tablosu, kaynak işaretleme, belirsizlik soruları, düzenleme sonrası üretim, iptal ve oturum sürüm geçişi. Bağımlılık/model kurulumu ve çevrimdışı çalıştırma yönergesi. | Dondurulmuş sürüm saklı veriyle değerlendirilir; doğruluk, raster/vektör ayrımı ve M1 kaynak raporu yayımlanır. Ağ kapalı dönüşüm ve art arda 10 iş denemesi geçer. |

Aşama 0'daki pilot, modelin önemli ilişkileri güvenilir biçimde çıkaramadığını gösterirse
parça başına kurallar eklemek çözüm sayılmayacak. Hata kaynağı Bölüm 18'deki kontrollü
deneylerle ayrılacak; uygun katman iyileştirilecek, gerekirse eğitilecek. Çizimde eksik
bilgi varsa kullanıcıdan profil/ölçü seçimi isteyen akış uygulanacak.
CAD derleyicisinin çalışması, çizim yorumlamasının çözüldüğüne kanıt sayılmayacak.

## 7. Sıradaki kodlama dilimi: eğitim öncesi ölçüm

İlk genel plan ve derleyici dilimi tamamlandı (Bölüm 11). Sıradaki teslim:

1. `eval/cases.json` içindeki parça gruplarını ve veri ayrımlarını doğrula. `2/` ile `7/`
   aynı parçadır; iki bağımsız örnek sayma. Yeni veri kararını beklerken mevcut altı
   örnekle yalnız regresyon ölçümü yap. Pilot ≥10 ve saklı ≥20 gerçek parça hedefi korunur.
2. `eval/model_baseline.py` oluştur: okuma/bağlama, işlem planlama ve CAD üretimini ayrı
   ölç; Bölüm 18B'deki gerçek ve elle doğrulanmış ara girdileri karşılaştır. Referans STEP
   ve doğru plan model istemine girmesin. Koşu başına makinece okunur rapor üret.
3. `llama.py` üzerinden seçilebilir model, bağlam, nicemleme ve kırpma ayarlarını kaydet;
   yerel modelden serbest Python yerine sürümlü `GeneralPlan` adayı al. Eksik kanıtı
   varsayım/soru olarak sakla; mevcut şema kontrollerini kullan.
4. Önce kullanılabilir küçük modelle ilk koşuyu yap; ikinci adayla aynı örnekleri karşılaştır.
   Her koşuda soğuk/sıcak başlangıç, aşama süreleri, bellek baskısı ve swap değişimini ölç.
   Model bulunamıyorsa eksik bağımlılığı raporla; hazırmış gibi sonuç yazma.
5. `eval/reports/model-baseline.md` içine hata sınıflarını, model karşılaştırmasını ve bir
   sonraki iyileştirme kararını yaz. Eğitim kararı varsa hedef görev, veri eksikleri ve
   geçiş eşiğini eğitim başlamadan kaydet. Henüz eğitim çalıştırma.

Kabul: aynı sürüm ve ayarlarla yeniden üretilebilen rapor; çözülemeyen her örnekte açık
hata nedeni; en az bir yerel modelin M1 ölçümü. İkinci model veya bağımsız veri eksikse
karşılaştırma/genelleme kabulü açık kalır. Bu dilim evrensel dönüşüm veya eğitim başarısı
iddiası taşımaz. Raster ankraj/ölçek geliştirmesi Aşama 2'nin açık işidir.

### Durum — 2026-09-27 (kapanış notu)

Bölüm 7'nin beş teslimi tamamlandı; ölçüm `eval/reports/model-baseline.md` içinde ve tabloları
`eval/baseline_report.py --check` ile koşu kayıtlarına bağlı. Ölçülen ayrım: vektör paftalarda
okuma tam (`plate-pocket-1` 7/7, `plastic-enclosure-1` 11/11), temiz render'da neredeyse tam,
gerçek taramalarda taban (`exercise-17` 2/7, `exercise-51` 4/14, `exercise-13` 2/8,
`flange-1` 4/13) ve tarama
paftalarının çoğunda ölçek kurulamıyor — zinciri durduran `no-scale` reddi doğru davranıştır.
Okuma kaybının yeri ölçüldü: sayı aramada değil, kabul edilen aday kümesinde (bir tarama
paftasında kabul edilen 30 adayın 28'i ok başı/kavis, sayı değil). Planlama katmanında iki
hazır model de düştü: `qwen2.5vl:3b` çıktıyı bitiremiyor, `qwen3-vl:8b-instruct` değerleri
doğru üretip plan gövdesinin iç yapısını tutamıyor (`sketches.*.entities[0]` tek dizeye çöküyor).
CAD katmanı bu ölçümde suçlanmadı; elle doğrulanmış plan plaka hacmini 0.0000% farkla kuruyor.
Eğitim kararı verilmedi; Bölüm 18C'nin gerektirdiği "tekrarlanan hata" ve "ayrı doğrulama
kümesi" koşulları henüz karşılanmadı, sıradaki iş raster aday kapısı ve plan arayüzüdür.

## 8. Kayıt ve teslim disiplini

Her aşama sonunda kod/model sürümü, veri ayrımı, ölçümler, başarısız örnekler ve açık
varsayımlar rapora eklenecek. Yeni bir örnek başarılı olsun diye eklenen kuralın başka
çizimlere nasıl uygulandığı bağımsız örneklerle gösterilecek.

Ana devam kaydı `HANDOFF.md`; eş kayıtlar `.cursor/handoff.md` ve `out/HANDOFF.md`.
`out/` Git dışında olduğundan plan ve önemli sonuçların özeti proje kökünde tutulacak.
Bu son güncelleme yalnız plan ve devam kayıtlarını değiştirir; eğitim veya yeni ölçüm
yapıldığı anlamına gelmez. Uygulanmış çalışmalar Bölüm 11–17'de, yeni işler Bölüm 7 ve
18'de kayıtlıdır. Her raporda geçmiş ölçüm ile o oturumda çalıştırılan kontrol ayrılacak.

## 9. Projeyi devralma ve çalıştırma

### Doğrulanmış yerel bağlam

- Mevcut proje: `/Users/aydemir/Desktop/drawingto3d`. Başka ortamda kendi depo kökünü kullan.
- Son plan güncellemesi öncesinde HEAD `f503f93`, çalışma ağacı temizdi. Bu bilgiyi
  geri dönüş talimatı olarak kullanma: devralırken güncel durumu yeniden kontrol et.
- Python şartı `>=3.12,<3.13`; yerel kurulum Python 3.12.8 / arm64.
- `.venv`: ana uygulama, PDFium, OpenCV, Pydantic, build123d ve testler.
- `.venv-cad`: CadQuery işçisi. Mevcut build123d/CadQuery OpenCascade sürümleri çakıştığı
  için iki ortamı koru; `pip install '.[reason]'` ile ana ortama birlikte kurma.
- CAD Python yolu `DRAWINGTO3D_CADQUERY_PYTHON` ile verilebilir; varsayılan `.venv-cad/bin/python`.
- Yerel Ollama adresi `http://127.0.0.1:11434`; uygulama ayarı `DRAWINGTO3D_OLLAMA_URL`.
  Yüklü modelleri `ollama list` ile doğrula. Model indirme ihtiyacı kurulum adımıdır.
- Önceki oturumda test arayüzü `127.0.0.1:8766` üzerinde bırakıldı; hâlâ çalıştığını
  varsayma ve var olan süreci incelemeden kapatma. Normal uygulama portu `8765`.

İlk inceleme sırası: `HANDOFF.md` → `git status` / `git diff` ve izlenmeyen dosyalar →
`pyproject.toml` → `general.py`, `observe.py`, `raster.py`, `bind.py`, `meaning.py`,
`proposal.py`, `llama.py` → `geo.py`, `cadrun.py`
→ `eval/README.md`, `eval/cases.json`, testler. Kaynak modüller `src/drawingto3d/` altında.
Varsa devralınan ortamdaki `AGENTS.md` yönergelerini de oku.

### Çalışma ağacını koruma

Devralırken güncel değişiklikleri `git status` ve `git diff` ile belirle;
kullanıcı değişikliklerini silme. `git reset --hard`, toplu checkout
veya temizlik komutlarıyla başlangıç durumunu değiştirme. Kullanıcının yerel çalışmalarını
koruyarak küçük, incelenebilir değişikliklerle ilerle.

### Başlangıç komutları

Aşağıdaki komutları depo kökünde çalıştır. Mevcut ortamların kurulu olduğunu varsayarlar;
eksik bağımlılığı önce teşhis et. Çıktı klasörünü her değerlendirme koşusunda yeni seç.

```sh
git status --short
git diff --stat
.venv/bin/python --version
.venv-cad/bin/python -c 'import cadquery; print(cadquery.__version__)'
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python eval/check_tables.py
```

Son uygulama kaydı: 234 test geçti (Bölüm 16). Bu, devralınan sürümün
testlerinin şimdi geçtiği anlamına gelmez; yeniden ölç. `test_llama_client_posts_the_image`
yerel HTTP sunucusu açar. Sandbox bağlantı iznini engellerse ortam kısıtını test hatasından
ayır; testi sessizce atlayıp tam başarı raporlama.

Dar plaka deneyini tekrarlamak için mevcut komutlar:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d plan "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/agent-baseline-01
PYTHONPATH=src .venv/bin/python -m drawingto3d build-plan "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/agent-baseline-01/plan.json out/agent-baseline-01
```

`plan` / `build-plan` şu an yalnız `PlatePlan` kullanır. Bunları genel motor tamamlanmış
gibi sunma. Model gerektiren eski `read` / `build` komutları `cli.py` içindedir; tüm örnekleri
başta tekrar modele vermek yerine önce hangi hipotezi ölçeceğini belirle.

Arayüzü mevcut süreç ve portları kontrol ettikten sonra başlat:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d.app
```

### Kodda özellikle incelenecek noktalar

| Yer | Mevcut sorun / sonraki eylem |
|---|---|
| `reason.py:records_text` | Ölçü-geometri bağlarını düz metinde kaybediyor; genel plan önerisine kimlikli ilişkileri taşı. |
| `schema.py:DimensionRecord` | Eski uzunluk ağırlıklı temsili, `general.py` içindeki tipli parametrelere kayıpsız bağla. |
| `schema.py:FeatureGraph`, `plan.py:PlatePlan` | Ortak hedef `GeneralPlan` olarak uygulandı; eski kayıt dönüşümünü ve arayüz geçişini tamamla. |
| `plate.py:_from_paths` | Sabit yapısal koşulları yeni örneklere göre çoğaltma; deney olarak koru. |
| `cadrun.py` | Genel eksen/konum silindir raporu uygulandı; çizimle bağımsız eşleştirmeyi genişlet. Süreç ayırma ve ortam temizliği ağ izolasyonu değildir. |
| `llama.py` | Sabit 16384 bağlam ve model yaşam döngüsünü ölç; kaynak sınırlarına göre düzenle. |
| `eval/report.py`, `eval/frontend.py` | Değer eşlemesi aynı sayının farklı kullanımlarını kaçırabilir; gözlem/özellik bazlı değerlendirmeye geç. |
| `eval/metrics.py` | Dış boyut/hacim/yarıçap kümesi, yanlış delik konumunu ve adedini yeterince ölçmez. |
| `app.py`, `static/index.html` | Dokuz plaka parametresi yerine genel parametre/işlem görünümü; eski oturumların sürüm geçişi. |

## 10. İlk CAD altyapısı tesliminin kabul listesi ve ortak rapor biçimi

Bu ilk dilim Bölüm 11'de tamamlandı; aşağıdaki koşulları regresyonda koru.
Yeni ölçüm diliminin kabulü Bölüm 7'de, eğitim koşulları Bölüm 18'de tanımlıdır.

- Sürümlü genel plan sözleşmesi ve en az iki farklı işlem birleşimini gösteren JSON örnekleri.
  Alanlar kaynak kimliği, parametre/birim/kaynak türü, profil, koordinat sistemi, işlem
  bağımlılıkları ve açık varsayımları içermeli. Kesin alan adlarını mevcut kodu inceleyerek seç.
- Aynı derleyicinin farklı şekilleri üretmesi; referans dosyası, örnek adı veya parça
  ailesi koşulu üretim yoluna girmemeli. Plaka uyumluluk adaptörü ayrı tutulmalı.
- Geçersiz profil, döngüsel parametre, birim uyuşmazlığı, kaynaksız kritik ölçü ve başarısız
  Boolean işlemi için anlamlı sonuçlar. Kaynaksız ölçü kullanıcı girdisiyse bu kaynak türü
  açık olmalı; modele ait tahmin doğrulanmış ölçüye dönüşmemeli.
- Parametre değişikliği → türetilen değer → yeni katı → yeniden açılan STEP zincirinin testi.
- Pilot manifesti, mevcut test sonuçları ve çözülmemiş veri/model bağımlılıkları.

Genel çıktı durumları en az `needs_input`, `draft`, `validated`, `unsupported`, `failed`
anlamlarını ayırmalı. `validated`, uygulanmış plan ve çizim kontrollerinin geçtiğini
belirtmeli; imalat onayı anlamına gelmemeli. Eski `audit.accepted` alanından geçişi açıkça
tanımla; mevcut taslak kayıtları sessizce doğrulanmış sonuca çevirme.

Her teslim sonunda kısa rapor biçimi:

```text
Tamamlanan aşama ve kullanıcıya görünen davranış:
Değişen dosyalar ve gerekçe:
Çalıştırılan kontroller / sonuçlar / çalıştırılamayanlar:
Görülmüş veri ve saklı veri ayrımı:
Geometrik doğruluk, süre ve bellek ölçümleri (varsa):
Bilinen sınırlar, kalan işler ve sıradaki somut adım:
HANDOFF.md, .cursor/handoff.md, out/HANDOFF.md güncellemesi:
```

Uygulamayı devraldığında bu planı yeniden yazmayı tamamlanmış iş sayma. İlk teslimi kod,
anlamlı testler ve yeniden üretilebilir çıktılarla yap; sonraki aşamalara aynı ölçütlerle ilerle.

## 11. Uygulama durumu — 2026-09-27 (2. oturum, ilk kodlama dilimi)

Planın önceki sürümündeki ilk kodlama dilimi uygulandı; Bölüm 10 kabul listesi karşılandı.
Kanıtlar:

- Sürümlü genel plan sözleşmesi `src/drawingto3d/general.py` içinde; iki farklı işlem birleşimi
  `eval/plans/bracket_linear_pattern.json` (extrude + repeat + cut) ve
  `eval/plans/shaft_revolve_cross_hole.json` (revolve + fuse + cut). Alanlar: kaynak kimliği ve
  sha256, parametre/birim/kaynak türü + açıklama + span kimlikleri, eskiz/düzlem/ofset, işlem
  bağımlılıkları, beklenti, varsayımlar.
- Aynı derleyici farklı şekilleri üretir; `compile_general` çıktısında dosya adı, örnek adı veya
  parça ailesi yoktur (test: yalnız kaynak kimliği değişen planlar aynı kodu üretir). Plaka
  uyumluluk adaptörü ayrı tutuldu: `from_plate`, plaka bilgisinin yaşadığı tek katman.
- Anlamlı sonuçlar test edilir: açık profil, döngüsel parametre, birim uyuşmazlığı, kaynaksız
  basılı ölçü, tanımsız referans/gövde, mükerrer çıktı, ayrılmış ad (şema doğrulaması) ve parçayı
  ikiye ayıran boolean (CAD, İngilizce neden mesajıyla: "split the part in two").
- Zincir testi: `edit_parameters(hole_dx 100→110)` → türetilen `width` 130 → yeni katı → STEP
  yeniden açılır; denetim geçer. Kullanıcı verdiği değer sonraki türetmelerle değiştirilmez.
- Pilot manifesti: `eval/cases.json` artık `part_group`, `split` ve `feature_ids` taşır; `_split`
  içindeki `pilot` ve `hidden` dizileri boş — veri toplama kullanıcıda. Pilot ≥10 yeni parça,
  saklı ≥20 parça (≥10'u raster); bu veri gelmeden genelleme ölçülmez.
- Çıktı durumları: `build-general` taslakları `"status": "draft"` yazar; `validated` uçtan uca
  ayrıştırılmadı (açık iş).

Teslim raporu (Bölüm 10 biçimi):

```text
Tamamlanan aşama ve kullanıcıya görünen davranış: genel plan sözleşmesi, derleyici ve denetim;
  CLI build-general; plaka artık aynı motorla üretiliyor.
Değişen dosyalar ve gerekçe: general.py (yeni sözleşme), geo.py (profil/tekrar fiilleri),
  cadrun.py (eksen-bağımsız silindir raporu), cli.py (build-general), eval/plans/* (yeni),
  eval/cases.json, eval/README.md, tests/test_general_plan.py (yeni), HANDOFF/CHANGES.
Çalıştırılan kontroller / sonuçlar: pytest 169/169 (146+23); check_tables 20/20;
  eval/plate_plan.py pass (simetrik fark 0,0 mm³); iki örnek plan CLI koşusu (denetimler geçti);
  bozuk plan CLI koşusu (exit 2, tek satır hata).
Görülmüş veri ve saklı veri ayrımı: altı mevcut pafta görülmüş regresyon; pilot/saklı küme boş.
Geometrik doğruluk, süre ve bellek: bracket hacmi kapalı formla fark ~8e-12 mm³; shaft mil hacmi
  dönel formla 1e-4 mm³; yan delikte çekirdek yaklaşıklığı ~1,6e-2 mm³ (kayıtlı sınır); yeni
  süre/bellek ölçümü bu dilimin kapsamında değil.
Bilinen sınırlar, kalan işler: okuma katmanı genelleştirilmedi (Bölüm 3A/3B); arayüz genel
  planı göstermiyor; plate recognizer hâlâ varsayılan yol. Sıradaki somut adım: gözlem katmanı
  ya da CLI/arayüzün genel plana bağlanması.
HANDOFF.md, .cursor/handoff.md, out/HANDOFF.md güncellemesi: üçü de bu oturumun özetini taşır.
```

## 12. Okuma katmanı — ilk dilim: aile-bağımsız gözlemler (2026-09-27, aynı oturum)

Bölüm 3A'nın vektör dilimi uygulandı (`ddacd48`): `src/drawingto3d/observe.py`.

- Gözlem kaydı: kaynak (yol, sha256, sayfa, pt boyut, döndürme), çerçeve (200 dpi, sol üst),
  metin yerleşimi (adıyla: mirrored/as-is), vektör yolları (noktalar, bbox, nesne/yol kimliği),
  uydurulmuş ilkeller (çizgi/daire/yay + artık), basılı metinler (ham dize, değer, birim, adet,
  karakter aralığı, kutu) ve atlanan nesneler (nedeniyle).
- Ortaklaşan yürüyüş: `observe.vector_paths`; plaka tanıyıcı aynı yürüyüşü kullanır
  (`plate.vector_groups` onun üstünde ince gruplama). `ingest.text_groups` ve
  `ingest.upright_placement` paylaşıldı; plaka testleri değişmedi.
- Ölçüm (model yok): plaka 209 yol / 169 ilkel / 45 metin (~0,11 s), plastik 456 / 365 / 65.
  Plaka kaydı kendi çizimini taşır: 100,02 × 60,01 mm delik aralığı, Ø6,81 delik, 25,01 mm
  cep yarıçapı — tanıyıcı kurallarından değil, geometriden.
- CLI: `observe <çizim> <out_dir>` → `observations.json`; raster girdi → exit 2, neden tek satır.
- Testler: `tests/test_observe.py` (11); tam paket **180 geçti**.
- Açık kalanlar (sonraki dilimler): ölçü ↔ geometri bağlama (§13'te yapıldı), görünüş ayrımı,
  ölçek, raster gözlemci ve gözlemlerden genel plan önerisi. Bu dilim "okuyabiliyoruz" iddiasını
  "gözlemleyebiliyoruz" ile değiştirir; bağlama gelmeden okuma sayılmaz.

## 13. Ölçü bağlama: basılı sayı ↔ geometri (2026-09-27, aynı oturum)

Bölüm 3B'nin ilk somut adımı uygulandı (`9031094`): `src/drawingto3d/bind.py`.

- Her span için: ankrajların oturduğu çizgiler (row = iki ankrajı birleştiren satır; stub = ucu
  ankrajda biten çizgi; crossing = ankrajdan geçen çizgi), uçları çakışan açık çizgi zincirleri
  (en çok 4 adım) ve her iniş noktasının dokunduğu özellikler (daire/yay merkez ve kenarı, uç,
  köşe) — piksel mesafesi, zinciri ve bulunduğu ankrajla. Seçim yapılmaz; tüm adaylar kaydedilir.
- Ölçü ekseni hizalaması: iki ankrajlı linear ölçüde eksen boyunca eşleşen adaylar (dik uzaklık
  kırpılmaz — standoff çizimin kuralı). Plakada satır uçları delik x'ini 2,4 px'te paylaşıyor.
  Sıra: daire merkezi > yay merkezi > uçlar; 2 px ızgarada tekilleştirme.
- `implied_px_per_mm` = satırın çizili uzunluğu / basılı değer; paftanın ölçülmüş kalibrasyonuyla
  oranı 1 → ölçek tutarlı; ayrılıyorsa farklı ölçekli detay ya da şüpheli ankraj.
- Ölçüm: plaka 7/7 bağlı — `100,00` iki üst deliğe 2,4 px hizada; `80,00` köşe yayları 0,5 px;
  `Ø6,80` lideri zincirle delik kenarında 0,09 px; `50,00` cep kenarında 0,12 px; beş satırın
  implied'ı kendi değerini %3 içinde ölçüyor. Plastik 14 sayı: 9 aligned + 4 partial + 1 unbound
  (`R8.00` radüs lideri — açık gap).
- CLI: `bind <çizim> <out_dir>` → bindings.json (plaka 37 KB, plastik 76 KB). Raster → exit 2.
- Testler: `tests/test_bind.py` (15); tam paket **195 geçti**.
- Sıradaki dilim: anlam seçimi — bağlanan adaylardan hangi özelliğin hangi sayıya ait olduğunu
  seçmek (simetri, "4 x", görünüş ayrımı), sonra gözlem+bağlama+anlamı genel plan önerisine
  çevirmek.

## 14. Anlam seçimi: her sayının ölçtüğü şey (2026-09-27, aynı oturum)

Okuma zincirinin üçüncü dilimi uygulandı (`085cd83`): `src/drawingto3d/meaning.py`.

- İki ankrajlı linear ölçü *mesafe* iddia eder: aday çiftlerinden, aralarındaki farkın **satırın
  kendi eksenine izdüşümü** basılı değeri tutanlar (dik uzaklık değil izdüşüm — 8,00 kesit
  boşluğunu ancak bu okudu). Sıra: tür (daire merkezi > yay > uç > köşe), sonra maliyet; simetrik
  okumalarda standoff'a en yakın çift kazanır, elenen çift kayıtta alternatif kalır.
- Lider ya da radüs işareti, değeri çizili çap/yarıçapla eşleşen geometriyi iddia eder ve
  `matched_geometry` tüm eşleşenleri taşır; komşu "N x" yazısı (span'ın kendi metin kutusuna göre)
  eşleşen sayıyla karşılaştırılır (`count`/`covered`).
- Doğrulanamayan span'lar `unresolved` kalır; hiçbir okuma uydurulmaz.
- Ölçüm: plaka 7/7 confirmed — `100,00` (g9-g11, çizili 100,71), `60,00` (60,43), `80,00` (köşe
  yayları, 80,46), `15,00` (15,10), `8,00` (8,03), `50,00` (cebe çap, 50,36), `Ø6,80` (dört delik,
  sayı 4/4). Plastik 14 sayının 4'ü confirmed, 10'u unresolved (zincir ölçüleri/detay görünüşleri —
  ankrajlar pafta ölçeğiyle tutmuyor; kayıt bunu saklamıyor, söylüyor).
- CLI: `meaning <çizim> <out_dir>` → meaning.json (plaka 18 KB, plastik 15 KB). Raster → exit 2.
- Testler: `tests/test_meaning.py` (14); tam paket **209 geçti**.
- Sıradaki dilim: bu okumaları **genel plan önerisine** çevirmek (görünüş ayrımı, hangi daire delik
  hangisi cep, kalınlık/derinlik), sonra raster gözlemci.

## 15. Öneri: okumaların plana dönüşmesi (2026-09-27, aynı oturum)

Dördüncü dilim uygulandı (`f61b7cc`): `src/drawingto3d/proposal.py`.

- Üç okuma katmanı tek sayfada koşup (observe → bind → meaning) o okumaların desteklediği
  `GeneralPlan`'ı önerir; desteklemiyorsa nedenini yazıp reddeder.
- Parça konturu kapalı döngülerden seçilir: sayfa çerçevesi önce atlanır (sayfanın ≥%80'ini
  kaplayan ya da ≥%60 kaplayıp başka döngüyü içeren döngü); kontur iki eksen-hizalı çizgi çifti +
  dört çeyrek yaydan oluşmalıdır.
- Doğrulanan iddialar dokundukları geometriye göre sıralanır: delik aralığı (iki daire; eksen
  uzun deltaya göre), kontur yüksekliği (iki köşe yayı), kesitin kalınlık ve cep derinliği (parça
  dışındaki iddialar), delik çapı ve cep çapı.
- Her parametre **basılı** (span id'siyle) ya da **türetilmiş** (köşe yarıçapı, genişlik, alan);
  ölçülen geometri her basılı sayıyı max(%1, 0,5 mm) içinde doğrular — dokuz kontrol, en büyük
  sapma 120 mm genişlikte 0,87 mm. Tutmayan öneri reddedilir; ret listesi neyin eksik olduğunu
  yazar (plastik: hiç çap ölçüsü okunmadı; 3 mesafe + 1 yarıçap doğrulandı).
- Ölçüm: plaka paftası artık aile-bağımsız motordan STEP'e gidiyor — `propose` → `build-general`:
  **124 825,4 mm³** (kapalı formülle fark **%0.0000**), bbox tam **120,00 × 80,00 × 15,00**,
  yeniden açılan STEP'te dört delik + bir cep silindiri doğrulandı; tüm zincir ~6 s. Kapalı formül
  testte ayrıca analitik sayıya karşı sınanır.
- CLI: `propose <çizim> <out_dir>` → proposal.json (+ önerildiyse plan.json); ret ve raster → exit 2.
- Testler: `tests/test_proposal.py` (16); tam paket **225 geçti**; check_tables 20/20; plate_plan
  geçti.
- Sıradaki dilim: raster gözlemci; sonra daha geniş arketipler (zincir ölçüleri, ikiden çok çap,
  asimetrik yerleşim, kare köşeli kontur) ve arayüzün genel planı göstermesi — ret listesi
  bunların yol haritası.

## 16. Raster gözlemci: piksellerden ölçülen çizgi, daire ve ifadeler (2026-09-27, aynı oturum)

Beşinci dilim uygulandı (`64ed9d8`): `src/drawingto3d/raster.py`.

- `observe()` artık PNG/JPG'yi piksel-önce gözlemciye yollar; kayıt şekli vektör yoluyla **aynı**
  (paths boş; çizgiler/daireler/ifadeler/notlar aynı alanlarda; `page_size_pt` ve `dpi` isteğe
  bağlı yapıldı, tek kayıt şekli iki kaynağa hizmet eder).
- Çizgiler: Hough parçaları açı + dik-uzaklık kümelemesiyle birleştirilir; her çizgi kendi en kötü
  artığını taşır.
- Daireler Hough **adayıdır** ve paftanın kendi mürekkep testlerinden geçer: yarıçap önce rafine
  edilir (r ± 6 px taranır, örneklerin en çoğunu mürekkebe oturtan değer; göbek adayı 0,81
  kapsamayla 3 px kısa çıkmıştı, rafine sonrası 0,92), sonra kapsama ≥ 0,85, iç mürekkep ≤ 0,25,
  merkez kelime-boyutlu OCR kutusunun içinde değil (görüntünün ≥%3'ünü kaplayan kutular okuma
  gürültüsü sayılır — tesseract sentetik bir görünüşün tamamını tek "kelime" okudu) ve daha iyi bir
  dairenin kopyası değil. Doğrulanan daireye binen kısa Hough kirişleri (≤ 80 px; uçlar ve orta
  nokta halkaya ~7 px içinde, sagitta dahil) çizgi listesinden düşürülür — o mürekkep dairenin.
- Metin: tesseract (`psm 11`) CLI'dan kendi zaman aşımıyla çağrılır; kelimeler ifadeye birleşir,
  sayılar vektör yoluyla aynı `parse_dimension_unit` ile ayrıştırılır.
- Ölçüm: Flange **388 çizgi + 2 daire** (Ø30 göbek r 91,6; kapsama 0,92) **+ 29 ifade** (9 sayısal);
  my_part **343 çizgi + 6 daire + 49 ifade** (7 sayısal); `observe` CLI iki dosyada exit 0. Üst
  zincir rasterda değişmeden koşuyor: `bind` 10 span kaydeder, `meaning` hiçbirini çözemez,
  `proposal` "pafta ölçeği okunamadı" diye reddeder — dürüst sınır: ankraj yoksa ölçek yok.
- Testler: `tests/test_raster.py` (9) — sentetik paftada çizilen geometri ölçülmüş olarak dönmeli
  (yarıçap ±3 px, merkez ±5 px) ve tesseract'sız koşu not olarak kalmalı; tam paket **234 geçti**;
  check_tables 20/20; plate_plan geçti.
- Kayıtlı sınırlar: yüksek hassasiyet, düşük geri çağırma (küçük cıvata delikleri, kesikli/yoğun
  kümedekiler kayda girmiyor; notlar bunu yazar); HoughCircles `minDist` eşmerkezli adayları
  bastırır (bore + havşa çifti tek daire verir); rasterda yay uydurulmuyor.
- Sıradaki dilim: **raster ankrajları + ölçek kalibrasyonu** (ölçü oklarını/uzatmalarını piksellerden
  bulup mm/px kurmak) — zincirin anlam/öneri yarısını rasterda da açar; ondan sonra geniş arketipler.

## 17. Veri düzeni: numaralı parça klasörleri (2026-09-27, aynı oturum)

Kullanıcı `examples/pdf with steps/` klasörünü **1–8 numaralı parça klasörlerine** ayırdı; her
klasörde çizim ile referans STEP birlikte durur. Depodaki bütün yol referansları (testler, `eval/`,
`PLAN.md`, `HANDOFF.md`) yeni yollara taşındı; `eval/cases.json` kayıtları yeni yolları taşır.

- `1/` Exercise_51.PNG + Exercise 51.STEP — **yeni parça (raster)**
- `2/` Drawing.pdf + Drawing.jpg + Part-2.STEP — **yeni klasör; `7/` ile aynı parçanın kopyası**
  (jpg ve STEP bayt-eş) ve ek olarak aynı parçanın **vektör PDF sürümü** — aynı geometri için iki
  kaynak (raster + vektör) ilk kez birlikte duruyor.
- `3/` Exercise 17.PNG + Exercise 17.STEP — **yeni parça (raster)**
- `4/` Exercise 13.PNG + Exercise 13.STEP — **yeni parça (raster)**
- `5/` Plate With A Pocket Drawing.PDF + plate with a pocket.STEP (plaka, görülmüş)
- `6/` plastic enclosue.pdf + plastic enclosue.STEP (görülmüş)
- `7/` my_part.jpg + my_part.STEP (exercise-1, görülmüş)
- `8/` Flange.PNG + Flange.STEP (görülmüş)

Yeni kaynaklar (1–4) henüz manifeste kayıtlı değil; 2, görülmüş exercise-1 grubuna aittir.
Diğerlerinin id ve pilot/saklı ayrımı kullanıcının kararı olunca `cases.json`'a girerler (PLAN §5 ölçütü: pilot ≥10, saklı ≥20, en az 10'u raster). Bu, "dosyayı
at → STEP al" hedefinin ölçüm verisinin başlangıcıdır; yolları bugün koddan sınanabilir (testler ve
`eval/` bu klasörlerden okuyor).

## 18. Model değerlendirmesi ve hedefli eğitim planı — 2026-09-27

Bu bölüm son kullanıcı kararıyla eklenen yol haritasıdır; aşağıdaki araçlar, veri kümesi
ve eğitim henüz hazırlanmadı. Öncelik sırası: hazır modeli ölç → hatayı ayır → ilgili
katmanı iyileştir → gerekirse eğit → son modeli M1 üzerinde ve bağımsız çizimlerde doğrula.

### A. Modelin görevi ve ürün sınırı

- Girdi: çizim görünüşleri/kırpmaları, kaynaklı gözlemler ve ölçü ilişkileri.
- Çıktı: sürümlü `GeneralPlan` adayı veya eksik/çelişkili kanıta bağlı soru. Model;
  profil, işlem sırası, görünüş ilişkisi ve ölçü bağları önerebilir. Şema değiştirilirse
  eğitim verisi de sürümlenir ve eski örnekler açık bir dönüşümden geçirilir.
- Çalıştırma: şema ve kısıt denetiminden geçen planı mevcut deterministik derleyici kurar.
  Serbest Python üretimi yeni varsayılan yol olmayacak. `exec()` ya da yalnız alt süreç
  kullanımı güvenli çalıştırma sınırı sayılmayacak.
- Kanıt: üretilen STEP'in geçerli olması, modelin çizimi doğru okuduğunu tek başına
  göstermez. Plan kontrollerinden bağımsız çizim/özellik kontrolleri zorunludur.
- Geometri için zorunlu bilgi eksikse `needs_input`; geçerli ama okuması henüz
  doğrulanmamış katı `draft`; desteklenmeyen işlem `unsupported`; üretim hatası `failed`.
  `validated` yalnız gerekli plan ve çizim kontrolleri tamamlandığında verilir.

### B. Eğitim öncesi hata ayırma deneyi

Aynı parça grupları üzerinde aşağıdaki koşullar ayrı ölçülecek. Elle doğrulanmış ara
girdi kullanılan koşullar teşhis içindir; otomatik PDF → STEP başarısına dahil edilmez.

| Koşul | Girdi ve iş | Ayırdığı hata |
|---|---|---|
| Gerçek zincir | Çizim → okuyucu/model → plan → CAD → çizim kontrolü | Kullanıcının göreceği uçtan uca sonuç |
| Okuma/bağlama | Çizim → kimlikli ölçüler ve ilişkiler; bağımsız etiketle karşılaştır | Sayı, sembol, ok, görünüş ve özellik eşleşmesi |
| Doğrulanmış ilişkiler | Doğru gözlem/ilişkiler + çizim → aynı model → plan | Algı hatası azaltıldığında kalan işlem planlama hatası |
| Doğrulanmış plan | Elle doğrulanmış `GeneralPlan` → aynı CAD derleyicisi | Şema, CAD işlemi ve doğrulayıcı sınırı |

Mevcut kurallı yol, hazır yerel model yolu ve uygulanırsa eğitimli model yolu aynı veri
ve kaynak bütçesiyle karşılaştırılacak. Küçük model adayları mevcut yerel kurulumdan
seçilecek; sürüm ve çalıştırma desteği deney başlamadan doğrulanacak. Genel görsel
benchmark skoru, teknik çizim doğruluğu yerine kullanılmayacak.

Koşu kaydı en az şunları içerecek: kod sürümü ve yerel değişiklik özeti, veri manifesti
özeti, model/ağırlık özeti, istem sürümü, şema sürümü, rastgelelik ayarları, nicemleme,
görüntü boyutu/kırpmalar, bağlam ve çıktı sınırı, zaman aşımı, aday/düzeltme sayısı,
aşama süreleri, bellek ölçüm yöntemi, bellek baskısı, swap değişimi ve çıktı durumu.
Kullanıcı müdahalesiyle çözülen örnekler ayrıca sayılacak. Aynı örneğe yapılan tüm
denemeler saklanacak; yalnız en iyi çıktı raporlanmayacak.

### C. Hangi hata için hangi çalışma?

| Ölçülen baskın hata | Sonraki çalışma |
|---|---|
| Küçük sayı, çap sembolü, ölçü oku veya kesit sınırı kaçıyor | Önce kırpma, PDF vektörü, OCR ve raster ankrajlarını iyileştir; gerekirse etiketli küçük algılayıcı eğit. YOLO/DETR seçimi ölçüme bağlıdır. |
| Ölçü doğru okunuyor, yanlış özelliğe bağlanıyor | Ölçü–geometri ve görünüş eşleşmesi etiketleriyle ilişki görevini iyileştir; gerekirse bu görevde LoRA dene. |
| İlişkiler doğru, plan/işlem sırası yanlış | `GeneralPlan` hedefli planlama eğitimi dene; işlemlerin yeni birleşimlerini içeren veriyi artır. |
| Doğru plan CAD'de kurulamıyor | Derleyici veya işlem kapsamını düzelt; bu hata için okuyucuyu eğitme. |
| Çizim eksik/çelişkili veya kapsam dışı | Açık soru/destek durumu üret; belirsiz örneğe tek bir kesin plan etiketi verme. |

LoRA, hazır modelin küçük ek ağırlıklarını eğitme seçeneğidir. Modeli sıfırdan eğitmek
varsayılan çözüm değildir. Eğitim kararı için tekrarlanan hata, doğrulanmış hedef etiket,
ayrı doğrulama kümesi ve ölçülebilir iyileştirme hedefi gerekir.

### D. Eğitim verisi sözleşmesi

İdeal tam örnek: **çizim + kimlikli ölçü/özellik ilişkileri + doğrulanmış işlem planı +
referans STEP**. Okuma gibi alt görevler, yalnız kendi hedef etiketleriyle de eğitilebilir.
STEP genellikle orijinal eskiz/işlem geçmişini taşımaz; PDF–STEP çifti doğrudan doğru plan
etiketi sayılmaz. Plan ayrıca hazırlanır veya sentetik üretim sırasında kaydedilir.
Geometrik olarak eşdeğer birden fazla plan kabul edilebilir; yalnız JSON metin eşitliği
başarı ölçütü olmayacak.

Manifest kaydı: `sample_id`, `part_group`, `split`, gerçek/sentetik kaynak, kaynak ve
kullanım hakkı, dosya özetleri, şema sürümü, görünüş/kesit dönüşümleri, ölçü birimleri,
ölçü/özellik kimlikleri, işlem planı ve referans yolları, belirsizlikler, etiket kontrolü.
Kaynakta bulunmayan bilgi `assumed` veya soru olarak işaretlenir. Yapay model etiketleri
kontrol edilmeden doğru kabul edilmez.

Veri ayrımı iki amaç için korunacak:

1. **Eğitim (`train`)**: ağırlık güncellemelerinde kullanılan gerçek ve sentetik örnekler.
2. **Doğrulama (`validation`)**: model, istem, eğitim ayarı ve durdurma noktası seçimi.
   Pilot bu amaçla kullanılabilir; böyle kullanıldığında artık saklı test değildir.
3. **Saklı ürün testi (`hidden`)**: tüm kararlar dondurulduktan sonra bir kez değerlendirme.
   Buradan öğrenilerek değişiklik yapılırsa etkilenen örnekler regresyona taşınır ve yeni
   saklı veri gerekir. Hazır modelin geçmiş eğitiminde görülmediği kesin bilinemez;
   rapor yalnız bu projenin geliştirme sürecinden ayrılığı iddia eder.

Mevcut `seen-regression`/`pilot`/`hidden` kayıtları korunacak; eğitim ayrımları eklenirken
manifest ve okuyucuları açıkça güncellenecek. Aynı parçanın tüm kaynakları, yakın ölçü
varyantları ve aynı sentetik üretim ailesi bir grupta tutulur; artırılmış kopyalar gruplar
arasında dağılmaz. Model seçimi için ayrılmış işlem birleşimleri eğitim üreticisinden
dışlanır. Referans STEP ve hedef plan, değerlendirmedeki modele verilmez; eğitimde ise
doğru plan yalnız hedef taraftadır. Dosya adları/parça numaraları cevap ipucu olamaz.

### E. Sentetik üretim ve gerçek çizimlerle kontrol

1. Mevcut `GeneralPlan` işlemlerinden farklı profil, yön, işlem sırası, kör/geçişli delik,
   cep ve tekrar birleşimleri üret. Geçersiz, dejenere ve eş kopya modelleri ayıkla.
2. Her modelden ön/üst/yan görünüş ve gereken kesitleri çıkar; ölçüleri gerçek özelliklere
   bağlayarak ekle. Hedef plan, STEP ve ölçü bağlantı etiketlerini birlikte kaydet.
3. Pafta düzeni, ölçek, çizgi türü, font, ondalık ayracı, birim ve raster kalite varyantları
   üret; dönüşümleri etiketlere uygula. Önce grup ayrımı yap, sonra veri artır.
4. Üreticiden örnekleri görsel olarak incele; ölçülendirmenin geometriyi gerçekten
   tanımladığını, kesitlerin doğru olduğunu ve etiketlerde cevap sızıntısı olmadığını denetle.
5. Gerçek çizimlerle farkı ölç; sentetik başarısını gerçek çizim başarısı olarak sunma.

İlk üretici kabulü için hedef: en az 10 farklı işlem birleşiminden 100 kontrol edilmiş
örnek. Bu sayı model eğitimi için yeterlilik iddiası değildir. Veri miktarı, bağımsız
doğrulama hatasının veri arttıkça nasıl değiştiğiyle belirlenecek. Tek bir şablonun çok
sayıda ölçü varyantı veri çeşitliliği yerine sayılmayacak. Pilot ≥10 ve saklı ≥20 gerçek
parça hedefleri sentetik örneklerle doldurulmayacak.

### F. Küçük eğitim deneyi ve seçim koşulları

- İlk deney tek bir hata sınıfını hedefler. Hazır model ve eğitimli model için aynı
  doğrulama örnekleri, istem, çıktı şeması, deneme sayısı ve CAD kontrolü kullanılır.
- MLX-LM metin/ilişki → plan; MLX-VLM görsel görevler için incelenecek. Seçilen modelin
  eğitim desteği, nicemleme ve yerel çalışma ortamı deneye başlamadan doğrulanır.
  CAD ortamları korunur; eğitim bağımlılıkları ayrı ortamda tutulur.
- Önce küçük bir alt kümede bellek ve adım süresi deneyi yap. Batch, görüntü çözünürlüğü,
  bağlam ve eğitilen katman sayısını kaydet. OOM, sürekli ağır swap veya doğrulama
  hatasında kötüleşme varsa koşuyu durdurup ayar/veri kararını raporla.
- Her deney için eğitim ayarları, veri özeti, tohum, temel model, adaptör, kontrol noktası,
  eğitim/doğrulama eğrileri ve M1 kaynak raporunu sakla. Deneme sayısına önceden sınır koy;
  başlangıç sınırı üç yapılandırmadır. Yeni deney, önceki sonuca dayanan hipotez gerektirir.
- Başlangıç seçim hedefi: hedef görevde hata oranını en az %20 göreli azaltmak; uçtan uca
  doğru parça sayısını düşürmemek ve yeni yanlış `validated` sonuç üretmemek. Örneğin
  50/200 bağlama hatasının en çok 40/200 olması hedefi karşılar. Eşik ilk ölçümden sonra,
  eğitim başlamadan raporda sabitlenir; sonuç görüldükten sonra değiştirilmez.
- Doğrulamada en az 10 ayrı gerçek parça ve hedef görevde en az 100 etiketli karar bulunur.
  Parça bazında hata değişimleri de raporlanır; aynı parçadaki kararlar bağımsız parçalar
  sayılmaz. Daha küçük küme yalnız ön deneydir. İyileşme yalnız sentetikte veya tek bir
  parçada görülüyorsa ürün modeli seçimi için yeterli değildir.
- Fayda gösterilmezse hazır model korunur. Daha çok eğitimi otomatik çözüm sayma; veri
  kapsamını, hedef etiketleri, şemayı veya kullanıcıdan gereken bilgiyi yeniden değerlendir.

Bu eşikler deney kararlarıdır; ölçülmüş başarı veya evrensel doğruluk garantisi değildir.
Daha güçlü eğitim donanımı gerekirse süre/bellek deneyiyle gereksinim raporlanır.
Eğitimin yeri ile uygulamanın çevrimdışı çalışması ayrı kararlardır.

### G. Eğitilmiş modeli ürüne alma ve son kabul

Adaptörün hedef çalışma ortamında yüklenmesi veya birleştirme/dışa aktarma desteği önce
küçük örnekte sınanacak. MLX ve Ollama biçimleri arasında otomatik uyumluluk varsayılmayacak.
Nicemleme veya dönüştürme sonrası aynı doğrulama yeniden yapılacak; son kullanıcıya
dağıtılacak dosyalarla M1 ölçümü alınacak. Çalışan temel modele geri dönüş yolu korunacak.

Ürün kabulü Bölüm 5'teki bağımsız geometri ölçütlerine bağlıdır: kapsam içindeki saklı
parçalarda en az %80 otomatik doğru sonuç hedefi, yanlış `validated` sonucu olmaması,
ret/zaman aşımının paydada kalması. Delik konumu/adedi, cep derinliği ve görünüş/kesit
eşleşmesi denetlenmeden yalnız benzer hacimle geçiş yapılamaz. Eksik ölçüde soru sorma ve
kullanıcının yanıtından sonra yeniden üretme akışı da sınanır.

İlk kurulum tamamlandıktan sonra ağ kapalı durumda PDF/PNG/JPG dönüşümü, yerel OCR/model
yükleme, art arda en az 10 iş, iptal ve hata toparlama sınanır. Gizli ağ isteği, çalışma
sırasında model indirme veya buluta geçiş gerekmez. Bölüm 4'teki süre/bellek hedefleri
son dağıtım modeli için ayrıca raporlanır; eğitimli sürüm bu koşulları geçmeden varsayılan
yapılmaz. STEP ile birlikte plan, kaynak ölçüler ve kontrol raporu saklanır.

### H. Planlanan dosyalar ve teslimler

| Teslim | Planlanan konum / kabul kanıtı |
|---|---|
| İlk karşılaştırma aracı ve raporu | `eval/model_baseline.py`, `eval/reports/model-baseline.md`; Bölüm 7 ve 18B |
| Eğitim veri sözleşmesi ve manifesti | `training/README.md`, `training/manifest.jsonl`; grup ayrımı, kaynaklar, şema sürümü |
| Sentetik örnek üreticisi | `training/generate.py`; 10 işlem birleşimi / 100 kontrol edilmiş örnek |
| Tekrarlanabilir eğitim deneyi | `training/configs/`, eğitim komutu, kontrol noktaları ve rapor; Bölüm 18F |
| Son yerel model değerlendirmesi | `eval/reports/local-model.md`; hazır/eğitimli karşılaştırması, M1 ve ağ kapalı sonuçlar |

Bu yollar planlanan teslimlerdir; mevcut dosya veya tamamlanmış sonuç değildir. Büyük
ağırlıklar ve veri dosyaları Git'e konmaz; kaynak/özet ve yeniden edinme bilgisi tutulur.
Bilimsel/teknik dayanaklar: [Drawing2CAD](https://arxiv.org/abs/2508.18733),
[MLX-LM](https://github.com/ml-explore/mlx-lm), [MLX-VLM](https://github.com/Blaizzy/mlx-vlm).
Drawing2CAD'in vektör çizim kapsamı, her taranmış PDF için başarı kanıtı olarak kullanılmaz.
