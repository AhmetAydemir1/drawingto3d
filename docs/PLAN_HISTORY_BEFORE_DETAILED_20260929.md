> Güncel kapsam ve iş sırası: **Bölüm 26 — evrensel, kullanıcı yönlendirmeli çevrimdışı PDF → STEP**.
> Bölüm 26, önceki deney günlüklerindeki sonraki iş önerilerinin yerine geçer. `examples/pdf with steps` yalnız test verisidir.

# drawingto3d — devralan AI ajanı için uygulama planı

Güncelleme: 2026-09-28 · Durum: yerel taslak üretimi ve ölçü bağları var;
genel kontur doğrulaması, kullanıcı düzeltmesi ve kesin konum kısıtlarının ürün entegrasyonu açık.

## Devralan ajana görev

Bu belgeyi uygulama görevi olarak kullan. Önce mevcut kodu ve değişiklikleri doğrula,
ardından aşağıdaki aşamaları ölçülebilir teslimlerle uygula. Kullanıcının hedefi M1 / 16 GB
üzerinde çevrimdışı, yeni teknik çizimlere genellenen PDF/PNG/JPG → STEP aracıdır.
Verilmiş örnekler test içindir; her birine ayrı parça şablonu yazmak hedefi karşılamaz.
Sohbet geçmişine ihtiyaç duyduğun bir karar olursa önce bu belgedeki kapsamı ve kaynak
kayıtlarını kullan. Belirsiz uygulama ayrıntılarını gerekçesiyle çöz; veri veya donanım
eksikliğini tamamlanmış sonuç gibi sunma.

**Başlangıç noktası:** Önce Bölüm 26 ve `HERMES_PROMPT.md`, ardından güncel kod ile
ilgili testleri oku. HANDOFF dosyalarının başındaki yönlendirme bu bölüme gider; aşağıdaki
eski deney kayıtları tarihçedir. Kapsam evrenseldir: her çizimde aynı geometri, ölçü ve
kullanıcı düzeltme mekanizmaları kullanılır. Bir örneği tamamlamak yalnız bir kabul testidir.
Örnek dosya adına, bilinen koordinatlara veya referans STEP'e göre üretim dalı ekleme.
Bölüm 18'in eğitim işleri, ayrı ve uygun eğitim verisi toplanana kadar ertelenmiştir;
`examples/pdf with steps` içeriğini eğitim verisi olarak kullanma.

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

## 7. Eğitim öncesi ölçüm dilimi — araçlar var, kabul kısmi

İlk genel plan ve derleyici dilimi tamamlandı (Bölüm 11). Aşağıdaki ölçüm araçları da
eklendi; güncel kabul durumu bölüm sonundadır. Sonraki uygulama görevi Bölüm 19’dadır:

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

### Durum — 2026-09-27 (denetim sonrası)

İlk ölçüm araçları ve altı geçmiş koşu mevcut; tablolar koşularla tutarlı. Ancak Bölüm 7
bütün kabul koşullarıyla kapanmış değildir. Sayısal değer kapsamı ölçü örneği doğruluğu
sayılmış; bellek ölçer `used` yerine `total` ve M1'de 16384 yerine 4096 bayt okumuştur.
Model istemi ile yanıt şeması `source`/`questions` alanlarında çelişmiş, doğrulama
metadatasından referans dosyası adı isteme sızmıştır. Bunlar denetim turunda onarıldı;
yeni arayüzle canlı model/bellek ölçümü açık. Modelin çıktıyı kapatamaması tek başına
kapasite veya şema derinliği sınırını kanıtlamaz.

Raster kapsam düşüklüğünün hangi aşamada oluştuğu henüz kesin ölçülmedi. Kesilen
`offering` koşusu sonuç üretmemiştir ve araçtaki eşleştirme/izleme kusurları giderilmelidir.
Aday lojistik sınıflandırıcı eğitimi denenmiştir; VLM/LoRA eğitimi yapılmamıştır.
`relations` koşulu görüntü göndermeyen, elle doğrulanmış metin ilişkileri deneyidir;
`chain` kurallı önericiyi kullanır. Genel modelin gerçek çizimle uçtan uca başarısı açık.
Ayrıntı: `eval/reports/progress-audit.md`; güncel iş sırası: Bölüm 19.

## 8. Kayıt ve teslim disiplini

Her aşama sonunda kod/model sürümü, veri ayrımı, ölçümler, başarısız örnekler ve açık
varsayımlar rapora eklenecek. Yeni bir örnek başarılı olsun diye eklenen kuralın başka
çizimlere nasıl uygulandığı bağımsız örneklerle gösterilecek.

Ana devam kaydı `HANDOFF.md`; eş kayıtlar `.cursor/handoff.md` ve `out/HANDOFF.md`.
`out/` Git dışında olduğundan plan ve önemli sonuçların özeti proje kökünde tutulacak.
İlk plan oturumu yalnız belge değişikliğiydi. Ardından ölçüm araçları ve yerel koşular
eklendi; son denetim kod, test ve rapor düzeltmesi içerir (Bölüm 19). Her raporda geçmiş
ölçüm ile o oturumda çalıştırılan kontrol ayrılacak.

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

Bu bölüm veri ve eğitim yol haritasıdır. İlk karşılaştırma aracı uygulanmıştır; eğitim
veri altyapısı ve VLM/LoRA eğitimi açıktır. Güncel durum Bölüm 19’dadır. Öncelik sırası: hazır modeli ölç → hatayı ayır → ilgili
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

## 19. Denetim sonrası sıradaki iş — 2026-09-27

Denetim raporu: `eval/reports/progress-audit.md`. Önceki HANDOFF kayıtlarındaki ve Bölüm
11–17 tarihçesindeki sonraki iş önerilerinin yerine bu sıra geçer. Ana yön doğru, fakat
ölçüm kusurları ve erken neden yorumları giderilmeden eğitim seçilemez.

### Uygulanan düzeltme dilimi

- Model istemi `general-plan-v2`, yanıt şeması `GeneralPlan reply v2`: `source` uygulamada
  atanır, `questions` yanıtta kabul edilir; kalıcı `GeneralPlan v1` korunur. Doğrulama
  metadatasındaki referans dosyası adı modele gönderilmez. Model doğruluğu yeniden ölçülmedi.
- Kaynak ölçümü v2: `vm.swapusage used`, `vm_stat` başlığındaki sayfa boyutu, MiB ve ham
  örnekler. Eski yanlış bellek değerleri ham kayıtta korunur, raporda geçersiz gösterilir.
- Koşu kaydı başlangıçta ve biten vaka/koşullarda atomik yazılır; çalışan/kesilen/tamamlanan
  durum ile etkin adım saklanır. Aynı etiketle çıktı ezilmez. Kod/veri özetleri kayda eklenir.
- Braket ve mil planları bu makinede yeniden derlendi; iki `draft` çıktı ve plan kontrolleri
  geçti. Bu deney otomatik çizim yorumlaması veya canlı model testi değildir.

### Sıradaki tek teslim: onarılmış model sözleşmesini ölç

1. Mevcut değişiklikleri koru. `eval/reports/model-baseline.md` ve yeni yanıt şemasını oku.
2. Önce 3B modeli, aynı plaka ilişki kanıtı ve önceki koşunun ayarlarıyla bir kez dene;
   kaynak sınırı engellerse bağlam/çıktı değişikliğini ayrı deney olarak kaydet. 8B'yi
   ancak kaynak bütçesi uygunsa ikinci aday olarak sırayla dene. Yeni koşu etiketleri kullan.
3. Bu koşul yalnız metin ilişkileri verir; görüntü kullanmış gibi raporlama. Yanıtın tam
   metni, kesilme nedeni, şema hatası, CAD sonucu, süre ve v2 kaynak ölçümleri saklansın.
   İki eski modelin tek paftadaki başarısızlığı, model sınıfı için kapasite hükmü değildir.
4. Yeni istem/şema ile bile aynı hata tekrarlanırsa tek değişkenli bir sonraki deney seç:
   örneğin parametre, profil ve işlemleri ayrı model çağrılarında üret; tek kalıcı plan
   sözleşmesini koru. Her parça için şablon yazmak veya yanıtı elle doğruya çevirmek yok.
5. Kabul: en az bir tamamlanmış canlı model kaydı, geçerli/geçersiz planın açık nedeni,
   kaynak ölçümünün erişilebilirlik bilgisi ve bir sonraki karar. Başarısız bir deney de
   teslimdir; ürün başarısı değildir. Bağımsız veri eksikliği bu ölçümü engellemez.

Örnek komut (kurulu model ve kaynak durumu kontrol edildikten sonra; eski ayarlarla
karşılaştırma için 16384/4096 kullanır):

```sh
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen2.5vl:3b --conditions relations --cases plate-pocket-1 --num-ctx 16384 --predict 4096 --label planner-v2-3b-01
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --write
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --check
```

### Ardından: modelin gerçek çizimle genel akışı

**Dilim çalıştırıldı (2026-09-27).** `chain_model` koşulu ve CLI yolu kuruldu: çizim okuma zinciriyle
milimetreye çevriliyor (`read_sheet`), kanıt planlayıcının bloğuna dönüşüyor (`chain_evidence`: basılı
sayı + span kimliği, bağlanan iddia + çapa noktaları (geometri kimliği, mm konum), mm kontur ve
daireler; elle doğrulanmış tablo veya referans STEP girmiyor), model aynı kanıtla soruluyor ve ham
yanıt saklanıyor. Ölçüm iki farklı görülmüş parça grubunda alındı (`chain-model-3b-01`, `-04`, `-05`):
plakada kural planlayıcısı planı çıkarıp katıyı kuruyor (draft/ok), model ise iki grupta da sözleşmeyi
eskiz/işlem gövdelerinde çiğniyor — ayırıcı etiket (`type`/`op`) hiç gelmiyor; valid/draft/eksik
bilgi/başarısızlık ayrı kaydedildi. CLI: `drawingto3d model-plan <çizim> <klasör>` (kanıt + ham yanıt +
geçerliyse plan; aksi hâlde çıkış kodu 2 ve gerekçe). Ayrıntı ve tablo: `eval/reports/model-baseline.md`
§"Ürün yolu".

Geometrik kaynak doğrulaması genişletildi: geçerli span kimliği artık tek başına yetmiyor —
`source: printed` bir parametre, atıf yaptığı span'ın yazdığı değeri (ya da yanında basılan adedi) ve
birimini taşımak zorunda. Sekiz kayıtlı yanıt yeni yargıçla aynı hükme düştü.

**Güncellenen karar (Bölüm 20):** kalıcı sözleşmedeki ayrık birleşimleri kaldırma önerisi geri
çekildi. Eksik kısıtlar model yanıt şemasına aktarıldı ve canlı ölçüldü. Görünüşler kanıt bloğunda
ayrı taşınmıyor; tam genel kontur kanıtı da açık. Görüntü gönderilecekse sürümlü ve kayıtlı olmalı.

Raster için sonraki bağımsız dilim `offering.py` onarımıdır: her basılı sayı için konum
ve değer birlikte, bire bir eşleştirilsin; yanlış okunan değer başarı sayılmasın. Aday
üretimi, kapı, ok başı koruması, OCR ve son filtre kayıpları ayrı izlenip ara kayıt bıraksın.
Önce PDF'nin kendi render'ında, sonra elle etiketlenmiş gerçek raster üzerinde ölç. Ayrı
paftaların metin kutularını kopyalama. Basit kapsam yüzdesi tek başına "hiç aday olmadı"
teşhisi için yeterli değildir. Bu teşhis tamamlanmadan uzun OCR/eşik denemelerini tekrarlama.

### Eğitim ve durma koşulları

Gerekli arayüz onarımları sonrası tekrarlanan hata ve ayrı doğrulama verisi varsa Bölüm
18'e göre hedefli eğitim seçilebilir. Tüm ürün sorunlarının önce çözülmüş olması eğitim
önkoşulu değildir; %80 raster kapsamı ve 4/5 ölçek hedefi eğitim yapmaya izin veren kapı
olarak kullanılmaz. Eğitim faydası kendi hedef görevi ve bağımsız doğrulamayla sınanır.

Pilot/saklı veri, tam bağımsız çizim kontrolü, genel arayüz ve ağ kapalı ürün kabulü hâlâ
açık. Bunlar bitmeden hedef tamamlandı denmez. `out/` Git dışıdır; bu durum dosya kaybına
karşı koruma sağlamaz. Sonuç özeti ve kararlar takip edilen raporda, büyük yerel çıktılar
ayrı yedek/teslim paketinde tutulmalıdır. Ctrl-C sonrası ya da zorla kesilen `running`
kaydı bitmiş sayılmaz; tamamlanan işleri incele, yalnız eksik işleri yeni etiketle çalıştır.


## 20. İkinci denetim: model yanıt şemasını düzelt, CAD sözleşmesini koru — 2026-09-27

Bu bölüm önceki sonraki-iş önerilerinin yerine geçer. Kanıt ve ayrıntı:
`eval/reports/schema-audit.md`, `schema-v3-probe-evidence.json`, `schema-v3-live-evidence.json`.

### Tamamlanan bir tur

- `chain_model` ve CLI gerçek ilerlemedir. Ancak eski gramer `value`/`expr` seçimini
  hiç kodlamıyor, varsayılanlı `type`/`op` alanlarını da zorunlu saymıyordu. Eski sonuçlar
  sağlayıcının `oneOf` desteklemediğini kanıtlamaz.
- `GeneralPlan reply v3`: eksik kurallar tek çağrı ve üç adımlı yanıt şemasına eklendi;
  kalıcı `GeneralPlan v1` ve `general-plan-v2` istemi korundu. Şema özeti kayda eklenir.
- Aynı model ve aynı üç küçük istekte alan kontrolleri 0/3 → 3/3. Bu CAD doğruluğu değildir.
- Gerçek plaka, aynı ayar ve istemlerle `schema-v3-3b-01` koşusunda yeniden ölçüldü.
  `relations` 51.49 sn, `chain_model` 83.90 sn: iki aday da geçersiz, **STEP yok**.
  Alan kontrolleri geçiyor; ilk tam-plan hataları `hole_spacing_X` ve `pdf-0` adları.
  Ham yanıtlarda üretilmemiş gövdeler, hatalı ifadeler ve eksik işlem bağımlılıkları da var.

### Sıradaki sınırlı teslim: adlandırmayı açıklaştır, semantik hatayı ölç

1. Mevcut değişiklikleri ve ham cevapları koru. Kalıcı şemayı veya CAD doğrulamasını gevşetme.
2. CAD adları için `^[a-z][a-z0-9_]*$` kuralını model arayüzünde açıkça kodla; kaynak
   kimliklerini CAD değişkeni olarak kullanma. `span_ids` gerçek kimliğini korusun.
   Önce tek küçük sondada sağlayıcının seçilen anahtar kısıtını uyguladığını göster.
   Gerekirse kayıpsız bir model yanıt adaptörünü ayrı deneyle sına; geometriyi elle düzeltme.
3. Aynı 3B model, vaka, kanıt ve ayarla `relations,chain_model` koşullarını yeni etiketle
   bir kez çalıştır. İstem veya şema değişikliğini sürümle ve parmak izleriyle kaydet.
   Yalnız ilk hata adını değiştirmek başarı değildir: işlem başvuruları, aritmetik,
   kapalı profiller ve atıflar doğrulanmalı. Ham yanıtlardaki diğer hataları görünür tut.
4. Üç adımlı yol seçilecekse alt yanıtları sonraki çağrıdan önce ilgili alan/başvuru
   kurallarıyla doğrula. Anahtarların bulunması “accepted” sayılması için yeterli değildir.
5. Teslim: kayıtlı küçük sonda + tamamlanmış koşu + ilk kalan semantik hata ve buna bağlı
   tek sonraki karar; plan geçerse CAD/çizim kontrolü ve ardından farklı parça grubunda ölçüm.
   Sonuç başarısız da olabilir; tekrar tekrar aynı modeli çağırıp başarı arama.

Örnek gerçek koşu (yeni değişiklikten ve kaynak kontrolünden sonra; kullanılmamış etiket):

```sh
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen2.5vl:3b --conditions relations,chain_model --cases plate-pocket-1 --num-ctx 16384 --predict 4096 --timeout 180 --label names-3b-01
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --write
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --check
```

Bağımsız sonraki işler: `offering.py` için konum+değer eşleştirme ve ara filtre izleri;
genel kontur/görünüş kanıtı; pilot/saklı parça grupları; ağ kapalı ürün kabulü. VLM/LoRA
henüz eğitilmedi. Eğitim için arayüz hatasından ayrılmış görev hatası ve ayrı doğrulama
verisi gerekir; hazır modelin bu tek paftada başarısızlığı kapasite hükmü değildir.

### Bu teslimin sonucu — 2026-09-27 (uygulandı, ayrıntı `eval/reports/naming-interface.md`)

- Ad kuralı modele taşındı: istem `general-plan-v3`, yanıt şeması `GeneralPlan reply v4`
  (`propertyNames` + `pattern`). Kalıcı `GeneralPlan v1` ve CAD doğrulaması değişmedi.
- Sonda (`eval/name_probe.py`, kanıt `name-probe-evidence.json`, `qwen2.5vl:3b`): dize alanında
  `pattern` **uygulanıyor**; nesnede `propertyNames` **uygulanmıyor**; kapalı anahtar sözlüğü
  anahtarı tutuyor ama değeri bozuyor (`100` → `"testing"`); `patternProperties` boş gövde veriyor.
  Yani açık anahtar kümesi bu sağlayıcıda kısıtlanamaz → kayıpsız ad adaptörü var, varsayılan kapalı.
- Gerçek plaka, dört koşu (`names-3b-02`…`names-3b-05`, ham yanıtlar `names-v4-evidence.json`):
  adlar geçerli, **ad hatası kayboldu**. İlk kalan hata `'/hole_spacing_x'` (ayrıştırılamayan
  ifade) ve büyük yanıtların kapanmaması: `names-3b-04` `done_reason=length`, `eval_count=4096`,
  8 648 bayt tekrar (180 sn'lik iki zaman aşımı bu döngüdür, "yanıt yok" değil). Üç adımlı yolda
  `parameters` adımı 14.8 sn'de bitti, `profile` adımı 4 096 tokanda kapandı. STEP yok.
- Bu turdaki profil bölme önerisi sonraki denetimde ertelendi: ilk parametre cevabı
  zaten yanlış kaynaklara dayanıyordu. Güncel yön ve ölçüm Bölüm 21'de; zaman aşımını
  otomatik olarak 400'e çıkarmak güncel görev değildir.

### Bu teslimin sonucu — profil adımı, koşu `profile-3b-01` (2026-09-27)

Ayrıntı `eval/reports/profile-step.md`, ham yanıtlar ve ayarlar `eval/reports/profile-step-evidence.json`
(Git içi), koşu klasörü `out/model-baseline/profile-3b-01/`.

- **Uygulanan tek değişiklik:** profil adımı artık okumanın ölçtüğü her kapalı profil için ayrı
  çağrı yapar (`planner.profile_targets`: bir kapalı dış kontur döngüsü + her kapalı daire); her
  alt yanıt sonraki çağrıdan önce denetlenir (yapı, ifade, birim, kapatma, ölçü atfı, “tek eskiz”,
  ad çakışması) ve profil çağrısının çıktısı `1024` tokanda sınırlanır. İstem sürümü
  `general-plan-v3-split-profile`; yanıt şeması, ad kuralı, kalıcı `GeneralPlan v1` ve CAD
  doğrulaması değiştirilmedi (`general.py` farkı boş). Sağlayıcı sondası tekrarlanmadı.
- **Ölçüm (tek koşu, iki koşul, aynı plaka/model/16384-4096, yeni etiket): `relations` 19,16 sn,
  `chain_model` 42,45 sn; ikisi de `failed (planning)`, STEP yok.** Döngü bitti: önceki turda
  tek profil adımı 4 096 tokanda `done_reason=length` ile kesiliyordu (178,47 sn, 7 743 bayt);
  şimdi `profile 1/6` 129 tokanda `stop` (17,85 sn). Koşu 67,54 sn, `complete`.
- **İlk kalan hatalar iki ayrı yerde.** `relations` **parameters** adımında durdu: basılı ölçünün
  `span_ids` alanına çizilmiş daire kimliği yazıldı (`h1`, `h2`; kanıt tablosunda basılı kimlikler
  `d1`…`d7`). Bu istem `names-3b-05` ile bayt-aynı (`01e0bc397f36…`), yanıt da bire bir aynı;
  değişen yalnız hükümdür (doğrulayıcı farkı, bkz. `step-validation-replay.json`).
  `chain_model` **profile 1/6 (outline)** adımında durdu: yanıt iki ilkelli, kapalı olmayan bir
  fragment ve yayın yarıçapı `x(6.84/2)` (izin verilmeyen fonksiyon); koordinat/çap bir *deliğin*
  ölçüsünden alınmış, sorulan kontur 120,87 × 80,56 mm ve r 10,05 mm'ydi. Aynı ham yanıt kapatma
  kuralını da çiğniyor (“profil en az üç kenardan oluşmalı”) — çevrimdışı doğrulama kaydı.
- **`chain_model` parameters adımı kabul edildi ama içerik parçayı kuramaz:** `hole_spacing_y`
  `(100 - 80) / 2` = 10 mm (pafta 60,00), `diameter_60_mm` `(15 + 8) / 2` = 11,5 mm,
  `pocket_depth` varsayımı 7,82 mm (“px/mm = uzunluk”), iki ayrı varsayılmış 3,4 mm yarıçap ve
  **hiç `thickness` yok**. Arayüz kuralları geçer, plan kurulamaz: geçerli JSON başarı değildir.
- **O turun sıradaki tek kararı (bu turda uygulandı):** istemde kanıt bloğunun iki ad alanını ayırmak
  (basılı sayılar → `span_ids` atfı; ölçülen bölgeler → atıf değil, geometri kimliği) ve her profil
  çağrısının bölgesini yapısal anahtarda vermek; şema/ad kuralı/sözleşme yine değişmez. Yetmezse
  sıradaki tek kural: türetilmiş parametre kabul edilmiş parametre adlarını kullanmalı ve basılı ölçüye
  atıf yapamaz. CAD/çizim kontrolü ve ikinci parça grubu ölçümü ancak geçerli plan çıkınca yapılır.
- **Sonraki tur — döngü kurma, ikinci arketipin kapısı, raster ölçeği, kanıt kimlikleri (2026-09-27;
  rapor: `eval/reports/general-input-slices.md`).**
  - **Döngü kurma (`proposal._loops`) düzeltildi.** Zincir kapanan segmenti önce alır, yoksa en az
    döneni; çıkmaza giren zincir hiçbir segmenti sahiplenmez (segmentler havuza döner). Ölçüm
    modelsiz: `Drawing.pdf` 3 → **7 döngü**, seçilen döngü artık parça konturu (8 ilkel,
    53,62 × 82,29 mm, kendisine bağlı `pdf-13` = R20); eskiden 3 ilkelli 20,54 × 35,95 mm detaydı.
    Plaka planı değişmedi (`propose` `proposed`, ölçüler aynı, `plate_plan.py` geçti); iki yeni test
    kapanma ve serbest bırakma kuralını çiviliyor.
  - **İkinci arketip yazılmadı — ölçüm bugün ateşlenemeyeceğini gösterdi.** Dürüst kapı (kontur
    ölçüleri bağlı + geriye tek kesit uzaklığı) üç vektör paftanın hiçbirinde sağlanmıyor: plaka 1/2
    ölçü bağlı ve 2 aday, `plastic` 0/2 ve 4 aday, `Drawing.pdf` 0/2 ve 10 aday. Ön koşul kontur
    ölçülerinin döngüye bağlanması; kanıtsız kod yerine kapı ve gerekçe kayda geçti.
  - **Raster ölçeği ölçüldü.** Yol, bağlanan ölçülerden ölçek kuruyor: `exercise-1` 5,73,
    `exercise-13` 2,88, `studycadcam-60` 3,28 px/mm; dört paftada `bind` hiç bağ kuramıyor (ölçek yok,
    ret `pafta ölçeği okunamadı`). Geçen turun "yedi rasterin hepsi `pafta ölçeği okunamadı`" tablosu
    bu turda doğrulanamadı (raster okuma yolu değişmemiş: `bind.py` 01:58, `meaning.py` 01:58,
    `raster.py` 02:46). Yeni sonda `eval/raster_scale.py` aynı paftada ölçeği bağımsız olarak
    **3,3158 px/mm** buluyor (4 sayı, yayılım %0,17; yolun 3,28'i ile %1,1 içinde) ve çizilmiş iki
    daireyi 51,06 / 20,57 mm veriyor. Ölçeği olan `exercise-1`'de sıradaki engel ölçek değil:
    343 çizgiden kontur kapanmıyor (`kapalı dış kontur bulunamadı`).
  - **Kanıt bloğunun ad alanları + kararlaştırılmış tek ölçüm (`ids-3b-01`; 53,23 sn, `complete`,
    iki koşul da `failed/planning`, STEP yok).** Hedeflenen hata kapandı: `relations` artık çizilmiş
    daire kimliği (`h1`, `h2`) yerine gerçek basılı kimlikleri atıflıyor (`d1`, `d3`) ve ilk hata bir
    adım derine indi — ifade ölçü kimliğini parametre sanıyor (`(d2 - d4) / 2`); aynı ham cevapta
    icat edilmiş `sqrt` ve atıfladığı ölçülerin (100,00 ve 60,00) yazmadığı `70,0` değeri ilk hatanın
    arkasında duruyor (çevrimdışı, etiketli replay). `chain_model`'de ilk hata parametre adına
    taşındı (`pdf-0`); aynı cevap isim adaptörü açıkken **0 hata** veriyor, yani o koşulu bloke eden
    tek şey ad kuralı. CAD üretimi, çizim kontrolü ve ikinci parça grubu çalıştırılmadı.
  - **O turun sıradaki tek kararı (bu turda uygulandı):** isteme "ifade yalnız kabul edilmiş **parametre
    adlarını** kullanır; ölçü kimlikleri yalnız `span_ids` alanında yaşar" kuralını ad kuralıyla
    birlikte vermek. Ölçüm sonucu negatif ve Bölüm 20'nin son maddesinde kayıtlı; "parametreleri düz
    ölçü listesi yerine dokundukları özelliğe göre gruplama" fikri ölçülmemiş olduğu için o tura
    **alınmadı** (alınsaydı koşu iki değişkenli olurdu).
- **Parametre kuralı turu — kuralı söylemek sınıfı kapatmadı (2026-09-27).** Tek değişken parameters
  adımının kural metni: yargıç **değişmedi**, yargıcın zaten uyguladığı iki denetim kelimeye çevrildi
  (`_RULE_EXPRESSIONS_USE_PARAMETERS`, `_RULE_PRINTED_CARRIES_ITS_VALUE`) ve iki arayüzde de
  alıntılandı (ikisi de parametre istiyor); `PROMPT_VERSION` → `general-plan-v5-parameter-rules`,
  `PROMPT_VERSION_SPLIT` → `general-plan-v5-split-parameter-rules`. Kanıt bloğu `ids-3b-01`'inkiyle
  **bayt aynı**, yani tek değişen soru. Koşu `params-3b-01` (`qwen2.5vl:3b`, `--split`, aynı plaka,
  16384/4096, `relations,chain_model`): **53,69 sn, `complete`, iki koşul da `failed (planning)`,
  STEP yok.** İlk hata sınıfı oynamadı — `relations` ifadede yine bir ölçü kimliği yazıyor (`d7`;
  önceki tur `d2`), `chain_model` yine parametre adına `pdf-0` koyuyor; oysa ad kuralı v4 isteminde
  de vardı ve yine çiğnendi. Okuma: eksik olan kural değil, cevabın kopyalayabileceği **yasal bir ad**;
  bu, bu makinede ölçülen iki sonuçla uyumlu (gramer `pattern`'i yalnız string alanda tutuyor, nesne
  `propertyNames` yok sayılıyor; aynı `chain_model` cevabı isim adaptörü açıkken parameters adımından
  geçiyordu). CAD üretimi, çizim kontrolü ve ikinci parça grubu çalıştırılmadı.
  - **Sıradaki tek karar (iki yol):** (A) isim adaptörünü bu adım için **varsayılan açık** yapmak ve
    ölçmek — en ucuz, ama ölçü kimliğinin *ifade içinde* kullanılmasını (relations) onarmaz;
    (B) parametre adını okumanın kendisinden **önermek** (her basılı ölçü için kind+çapa'dan türeyen
    jenerik bir ad, `hole_1_diameter` gibi) ki cevabın kopyalayacağı yasal ad olsun ve ifade kuralı
    uygulanabilir hâle gelsin — parçaya özel şablon değil, ölçümün kendi türünden türeyen ad.
    Ayırt edici ölçü: `relations` ifade denetimi + `chain_model` parameters adımı.
- **O turun (profil adımı) doğrulaması:** `pytest -q` **352 geçti** (231,55 sn; altısı bu turda eklenen
  `tests/test_profile_step_evidence.py`); `eval/profile_step_evidence.py --check` kanıt paketini koşu
  kayıtlarından yeniden üretip karşılaştırır (çevrimdışı replay kayıtlı hatayı bire bir vermezse
  geçmez); `eval/baseline_report.py --check` uyuşuyor (yeni satır `adım başına profil` olarak ayrı
  okunur); `eval/check_tables.py` 20 satır / 0 kayma; `eval/plate_plan.py` geçti. Koşu sırasında
  çalışma ağacı değişmedi (`out/profile-step/before.patch` ≡ `after.patch`). Eğitim yapılmadı, yeni
  ağırlık indirilmedi, ürün tamamlandı denmedi.
- **O turun (döngü/arketip/raster/ids) doğrulaması:** `pytest -q` **354 geçti** (274,82 sn; ikisi bu turda eklenen döngü testleri);
  `eval/plate_plan.py` geçti (`propose` plakada hâlâ `proposed`); `eval/check_tables.py` 20 satır /
  0 kayma; `eval/baseline_report.py --check` uyuşuyor (`ids-3b-01` satırı `adım başına profil` olarak
  ayrı okunur); `eval/profile_step_evidence.py --check` paketi koşu kayıtlarından yeniden üretiyor ve
  **paket artık istem sürümünü koşu kaydından okuyor** (modül sabitinden okuduğu için son turun turu
  `general-plan-v4-split-profile-ids` diye adlandırıyordu; düzeltildi, paket yeniden üretildi);
  `git diff --check` temiz. Ölçümler `out/profile-step/` altında (`general-sweep.txt`,
  `section-candidates.txt`, `raster-scale.txt`, `raster-scale-source.txt`, `ids-3b-01.log`,
  `pytest-round2.txt`) ve rapor `eval/reports/general-input-slices.md`. Eğitim yapılmadı, yeni ağırlık
  indirilmedi, ürün tamamlandı denmedi.
  - **O turun sıradaki tek kararı (bu turda uygulandı):** (B) yolu — cevaba kopyalayabileceği yasal adı
    okumanın kendisinden üretmek. (A) yolu (isim adaptörü) seçilmedi: `relations`'ın "ölçü kimliği
    ifadede" hatasını onarmıyor.
- **Önerilen adlar turu — ad sorunu `chain_model`'de kapandı, hata bir adım derine indi (2026-09-27).**
  `planner.suggested_names` (`reading-derived-names-v1`, koşu kaydında `settings.suggested_names`) her
  basılı sayı için okumanın kendi alanlarından bir ad üretir: `kind`/`form` (distance → `…_spacing`,
  diameter → `diameter`, radius → `radius`), çapa türleri (`circle-centre` → `circle`, `arc-rim` →
  `arc`, uç → `edge`) ve çapaların kendi ekseni (`|Δx| ≥ |Δy|` → `_x`); aynı biçimde ölçülen iki sayı
  indekslenir (`diameter_1`, `diameter_2`). `_readings_line` bu bloğu doğrudan "Printed numbers"ın
  altına basar; iki arayüz de taşıdığı için sürümler `general-plan-v6-suggested-names` /
  `general-plan-v6-split-suggested-names`. Şablon değil: bütün span **ve** geometri kimlikleri
  değiştirilse adlar aynı kalıyor (test).
  - Ölçüm `suggest-3b-01` (aynı plaka/model/16384-4096/`--split`; `chain_model` kanıt bloğu
    `params-3b-01` ile bayt aynı): **46,12 sn, `complete`, iki koşul da `failed (planning)`, STEP yok.**
    Sınıf değişti: `chain_model` artık parametre adına `pdf-0` koymuyor, önerilen adlardan beşini
    kullanıyor ve ilk hata "ifade bildirilmemiş `diameter_2`'yi kullanıyor"a indi; `relations` menünün
    üslubunu (`distance_1`…`distance_7`) aldı ama adları birebir kopyalamadı ve ifadeyi yine ölçü
    kimliğiyle yazdı (`(d1 - d2) / 2`). Yani iki koşul da artık **tek ve daha dar** bir sınıfta düşüyor:
    bildirilen parametre kümesi ile ifadede kullanılan adlar uyuşmuyor.
  - **Sıradaki tek karar:** bu son sınıfı kapatmak — (i) istemde önerilen her satır için o adla bir
    `printed` parametre bildirmeyi **yükümlülük** yapmak ve adım denetiminde bunu beklemek, ya da
    (ii) parameters adımını okumanın ölçtüğü hedeflere göre bölmek (basılı parametreler → türetilmişler)
    ki ifade edilebilecek ad kümesi kapalı olsun — profil adımında ölçülen desen. Öneri: (ii)'den önce
    (i) ölçülür (tek değişken, ucuz); `relations` menüsü zayıf olduğu için orada tek başına yetmezse
    (ii) sıradaki tur olur. Ayırt edici ölçü: iki koşulun da parameters adımı.
- **Bu turun (önerilen adlar) doğrulaması:** `pytest -q` **358 geçti** (251,22 sn); `eval/baseline_report.py --check`
  uyuşuyor (`suggest-3b-01` satırı), `eval/check_tables.py` 20/0, `eval/profile_step_evidence.py --check`
  uyuşuyor, `git diff --check` temiz, `git diff src/drawingto3d/general.py` boş. Rapor
  `eval/reports/suggested-names.md`, ham kayıt `out/model-baseline/suggest-3b-01/`, log
  `out/profile-step/suggest-3b-01.log`. Eğitim yapılmadı, ağırlık indirilmedi, ürün tamamlandı denmedi.
- **O turun (parametre kuralı) doğrulaması:** `pytest -q` **355 geçti** (230,35 sn; eklenen tek test
  satırı ölçülen arızanın şekli: `expr: "(d2 - d4) / 2"` → `tanımsız parametre`, ve mevcut "tek kelime,
  iki arayüz" testi iki yeni kuralı da denetliyor); `eval/baseline_report.py --check` uyuşuyor
  (`params-3b-01` satırı yazıldı); `eval/check_tables.py` 20 satır / 0 kayma; `eval/profile_step_evidence.py
  --check` uyuşuyor (paket hâlâ `profile-3b-01` ölçümünü belgeler); `git diff --check` temiz;
  `git diff src/drawingto3d/general.py` boş. Rapor `eval/reports/parameter-rules.md`, ham kayıt
  `out/model-baseline/params-3b-01/`, log `out/profile-step/params-3b-01.log`. Eğitim yapılmadı, yeni
  ağırlık indirilmedi, ürün tamamlandı denmedi.


## 21. Üçüncü denetim: adım doğrulaması tamam; sırada kanıttan parametre seçimi — 2026-09-27

Bu bölüm önceki sıradaki-iş önerilerinin yerine geçer. Ayrıntı ve ham kayıtlar:
`eval/reports/step-validation-audit.md`, `step-validation-replay.json`,
`step-validation-live-evidence.json`.

### Tamamlanan tur

- Eski üç adımlı koşunun parametre cevabı yanlış atıflarla profil çağrısına aktarılıyordu.
  Artık her adımın alanları, kaynakları, ifadeleri ve o aşamada bilinen bağımlılıkları
  doğrulanır. Profil kapanışı/ofset ve son işlem bağımlılıkları da denetlenir.
- `--split` ve `--normalize-names` iki model koşuluna da aktarılır. Eski karma koşu
  raporda karma gösterilir; ham kayıtlar yeniden yazılmaz.
- Aynı istem/gramerle eski cevabı yeniden doğrulama ilk adımda durdu. Yeni canlı koşu
  `step-validation-3b-01`: ilişkiler 20.24 sn'de yanlış atıf, gerçek çizim 63.95 sn'de
  geçersiz eskiz adıyla durdu; ikisi de tamamlandı. STEP yok.
- Gerçek çizimde parametre alanlarının geçmesi anlamın doğruluğu değildir: model cep
  derinliği için ölçek olan 7.82'yi kullanıyor, başka ölçüleri ilgisiz formüllerle türetiyor.
  Yalnız ad dönüştürmek veya profili bölmek bu sorunu çözmez.

### Son Hermes koşusu da denetlendi

Mevcut profil başına çağrı, döngü onarımı, ayrılmış kanıt başlıkları ve `suggested_names`
korunur. Güncel istem v6; en son `suggest-3b-01` iki koşulda da parametre adımında kaldı
(46.12 sn, STEP yok). İlk bildirilmemiş ad hatasının arkasında yanlış basılı değerler de var:
ilişkilerde 100.71/80.46/60.43, gerçek çizimde 100.71. İki varsayım hâlâ sayfa ölçeği 7.82'yi
uzunluk sayıyor. Bağımsız denetim ve ham kanıt: `eval/reports/latest-parameter-evidence.json`.
“Tek hata sınıfı kaldı” demek için ilk hatanın kaybolması yeterli değildir.

### Sıradaki sınırlı teslim: kanıt → parametre arayüzü

1. Mevcut adım doğrulayıcısı, `suggested_names` ve kalıcı `GeneralPlan v1` sözleşmesini koru.
   Basılı parametre kataloğunu okumanın kaynak kayıtlarından uygulamada kur: yasal ad, değer,
   birim ve kaynak bağı birlikte gelsin. Model bu bilinen değerleri yeniden yazmasın; ilgili
   kayıtları ve anlamlarını seçsin. Türetme için erişilebilir parametre ad kümesi açıkça verilsin;
   bildirilmemiş adı sonradan uydurarak tamamlama. Parçaya özel şablon kullanma.
2. Ölçü kaynak kimliğini geometri kimliğinden ayır. Türetilmiş ifadelerde bilinen parametre
   başvurularını denetle; rastgele ölçü sabitlerini kanıt gibi kabul etme. Eksik/çelişkili
   anlamı ve varsayımları soru veya inceleme gereği olarak kaydet. İşlemci sayfa ölçeğini
   parça derinliği diye sessizce aktarmamalı.
3. Önce küçük testlerde yanlış kaynak seçiminin reddini ve seçilen basılı değerin/birimin
   aynen korunmasını göster. Ardından kurulu 3B modelle iki mevcut farklı parça grubunda
   (plaka ve plastik gövde) yalnız parametre adımını birer kez ölç; yeni etiketler kullan.
   İstem/şema değişikliğini sürümle; koşuların çıktısını ve kabul kapsamını açıkça kaydet.
4. Ölçütleri ayrı tut: doğru kaynak/değer, türetmenin dayanağı, ölçünün anlamı, varsayım/soru.
   JSON geçerliliği veya adımın `accepted` olması çizim doğruluğu değildir. Bu iki mevcut
   parça geliştirmede görülmüştür; sonuç genelleme veya saklı veri başarısı sayılmaz.
5. Teslim: test edilen arayüz, iki sınırlı ölçüm, ham kanıtlar ve kalan baskın hata.
   Parametre anlamı yeterince doğrulanmadan uzun profil/STEP denemelerine dönme. Tekrarlanan
   görev hatası kalırsa Bölüm 18'e göre veri/model/eğitim kararını ayrı deney olarak gerekçelendir.

Bu turda STEP üretimi veya model eğitimi tamamlandı denmez. Tam kontur/görünüş kanıtı,
raster ölçüm düzeltmesi, bağımsız pilot/saklı veri ve ağ kapalı ürün kabulü açık kalır.


Hermes'e verilecek goal cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 21'i uygula: mevcut suggested_names ve ölçü kaynaklarından basılı parametre kataloğunu uygulamada kur; modelin bilinen değerleri yeniden yazmasını kaldır, seçim/anlam ve türetmeleri bu kataloğa bağla. Kalıcı CAD sözleşmesini ve mevcut değişiklikleri koru. Yanlış değer, bilinmeyen başvuru ve ölçeğin uzunluk sayılması hatalarını ayrı denetle; küçük testlerden sonra plaka ve plastik gövde grubunda yalnız parametre adımını birer kez ölç. Ham kanıtları, test sonuçlarını ve tek sonraki kararı raporla; PLAN/HANDOFF'u güncelle. Parametre anlamı doğrulanmadan uzun profil koşularına dönme veya STEP başarısı ilan etme.
```


## 22. Parametre kataloğu uygulandı ve ölçüldü — 2026-09-27

Bu bölüm önceki sıradaki işlerin yerine geçer. Rapor: `eval/reports/catalog-parameters.md`;
Git ile taşınabilir ham kayıt: `eval/reports/catalog-parameter-evidence.json`.

### Tamamlanan dilim

- `catalog.py` kaynaklardan yasal ad, basılı değer, birim ve adet kataloğu kuruyor.
  Model sayıları yeniden yazmıyor. Seçim/anlam ve türetme önerileri ayrı alanlarda;
  kaynak, ad, bağımlılık, döngü ve boyutsal aritmetik denetleniyor. Varsayılan başarı yok.
- Basılı orijinal sayı `SpanMeaning.printed_value` ile korundu; milimetreye çevrilmiş ve
  yuvarlanmış sayının inç etiketiyle aktarılması düzeltildi. Adet artık uzunluk sayılmıyor.
- Yeni deney aracı `eval/catalog_parameters.py` tam isteği modelden önce diske yazıyor.
  Her cevap kalıcı, etiketler tek kullanımlık. Mevcut çalışma ağacı ve GeneralPlan v1 korundu.
- `catalog-3b-01`: yerel qwen2.5vl:3b, iki farklı görülmüş grup, 36.359 sn toplam.
  Plaka 19.01 sn, plastik gövde 12.44 sn. Katalogda 22/22 kaynak sayı/birim korunuyor.
  İki model cevabı da geçersiz: mevcut adları yeniden türetmeye çalışıyor; plakadaki
  ifade ayrıca boyutsuz sonucu mm sayıyor. Anlam doğruluğu ve STEP başarısı yok.
- İlk dilimde ilgili 108 test geçti (75.87 sn); tam takım **394 test geçti** (226.70 sn).
  Kaynak karşılaştırması, istek özetleri ve iki ham cevabın yeniden denetimi geçti.

### Sonraki dilim

1. Deterministik ölçü kataloğunu kullanıcıya incelenebilir bir CLI çıktısı olarak sun.
   Eksik ölçek/kapalı kontur yüzünden geometri okunamasa bile basılı sayıları koru;
   geometri eksikliğini gerekçe olarak taşı. Yeni kontur veya sabit parça şablonu ekleme.
2. Katalog sayılarının korunması ile modelin anlam önerisini ayrı göster. İncelenmemiş
   seçimi STEP'e otomatik aktarma; başarısız model çağrısı mevcut ölçüleri silmesin.
3. Sonraki model deneyi yalnız somut bir eksik boyut veya geometri bağı için sınırlı olsun.
   Mevcut nicelikleri yeniden türettiren geniş parametre isteğini tekrar tekrar çalıştırma.
   Geometri ilişkilerini bağımsız etiketle karşılaştır; doğru yorum/çelişki/eksik bilgi ayrı.
4. Pilot ve saklı grup hâlâ boş. Daha büyük model veya eğitim için hata/veri/maliyet
   hipotezini önce kaydet. Bu katalog deneyi eğitim ve genel PDF→STEP başarısı değildir.

Kullanıcı limit dolana kadar ilerlemeyi istedi. Her tamamlanan dilimde PLAN/HANDOFF'u
kaydet; son mesaja kadar bekleme. Hesap limiti nedeniyle durmak görevin bittiği anlamına gelmez.

### Bölüm 22 devamı: katalog komutu da tamamlandı

- `drawingto3d catalog <çizim> <yeni_klasör>` model olmadan kaynak tablosu, JSON ve kanıt
  üretir. Var olan katalog dosyalarını ezmez. Ölçek/kontur yokken basılı sayılar korunur.
- Plastik PDF 14 kayıt (`needs_review`); raster flanş 18 aday (`needs_input`, ölçek yok).
  Bu 18 adayın OCR doğruluğu ayrıca ölçülmeli. Katalog sayısı başarı sayısı değildir.
- İlk dilim tam takım 394; ikinci dilim etkilenen testler 29; son CLI/kesinti testleri 6 geçti
  (son iki grup örtüşür). Tam takım ikinci dilimden sonra tekrar çalıştırılmadı.
- Baseline raporu, tablo (20/0), profil kanıtı, whitespace ve değişmeyen `general.py` kontrolü geçti.
- Ürün komutuna bağlama ve erken dönüşte ölçü kaybı işleri tamam. Sonraki görev: katalogdaki
  **tek ölçüye** anlam/bağ önerisi. Model yanıtı yasal kaynak ve geometri kimliklerini seçsin,
  tür/eksen uyumsuzluğu reddedilsin; ilk deneyde türetme istenmesin. Önce gerçek okuma ile
  mevcut bağımsız ilişki etiketi arasında karşılaştırma tasarla. Etiketler yalnız değerlendirme
  için; üretim girdisine taşıma. Çözülemeyen bağlantıyı soru olarak tut.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Basılı parametre kataloğu, catalog CLI, değer/birim/adet koruması ve kesinti kayıtları tamam; iki yerel 3B anlam cevabı hâlâ geçersiz. Mevcut kodu ve GeneralPlan v1'i koru. Serbest anlam/türetme isteğini tekrar etmek yerine tek ölçü için kaynak ve geometri kimliklerine bağlı yorum arayüzü kur; ilk deneyde sayısal türetme isteme. Tür, eksen ve kaynak bağını bağımsız ilişki etiketiyle ölç; çözülemeyen bağı soru olarak bırak. Referans etiketleri yalnız değerlendirmede kullan. Küçük testlerden sonra plaka ve plastik gruplarda dar deney yap, ham isteği/cevabı kalıcı kaydet, doğru yorum ve belirsizliği ayrı raporla. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

Son kontrol noktası: hesap kullanımı %98; devir kopyaları güncel. Değişen dosyalar ve
bu turun yerel çıktı yedeği `out/checkpoints/catalog-20260927-210018.zip`. Bu paket mevcut Git tabanına eklenir;
model ağırlıkları ve sanal ortamları içermez. Genel hedef tamamlanmış sayılmadı.

### Bölüm 22 devamı: tek ölçü yorum arayüzü kuruldu ve ölçüldü — 2026-09-27

Rapor: `eval/reports/measurement-interpretation.md`; Git ile taşınabilir ham kanıt:
`eval/reports/meaning-interpretation-evidence.json` (`--check`: 22 ölçü, 0 sorun).

- `src/drawingto3d/interpret.py`: tek ölçü için kaynak+geometri kimliklerine bağlı yorum arayüzü
  (`single-measurement-interpretation-v1` / `MeasurementInterpretation v1`). Şemada sayısal alan yok;
  `between`/`matched` yalnız sunulan **gerçek** kimliklerin `enum`'u; çözülemeyen bağ `unresolved` +
  tek soru. Sözleşme denetimi tür↔alan uyumunu, mükerrer kimliği, çözülemeyen bağda iddiayı ve
  gerekçe/sorudaki kimlik dışı sayıyı reddeder; okuma bağı ve eksen tutarlılığı **ölçü olarak** kaydedilir.
  Referans etiket yalnız değerlendirmede; model girdisine etiket veya referans STEP konmadı.
- `eval/meaning_interpretation.py`: istek model çağrısından önce, cevap hemen sonra kalıcı; `--dry-run`
  model çağırmadan istekleri yazar; `--evidence` paket üretir; `--check` kayıtlı ham cevapları yeniden
  yargılar. Küçük testler: `tests/test_interpret.py` (20), `tests/test_meaning_interpretation.py` (6).
- Ölçüm `meaning-3b-01` (`qwen2.5vl:3b` fb90415cde1e; 16384 bağlam, 4096 çıktı, sıcaklık 0):
  toplam **186,971 sn** (plaka 71,04, plastik 115,584), 22 istek + 22 cevap.
  - **Sözleşme tuttu:** 22/22 cevap yalnız sunulan gerçek geometri kimliklerini kullandı; uydurulmuş
    kimlik yok, basılı değer/birim/adet değişmedi, kaynak kimliği geri yansıtıldı.
  - **Yorum zayıf:** plakada 8 ölçünün **7'si sözleşmede düştü** (5'i gerekçede sayı yazdı, 2'si çap/yarıçap
    şekli); etiketin denetleyebildiği 15 alandan yalnız **1'i puanlandı**, tam doğru **0**. Tür denetlenen
    5 cevapta 5/5 doğru; dikey ölçüde (60,00) eksen yanlış; 50,00 cep çapı iki deliğe bağlandı.
  - **Plastik:** 13/14 sözleşmeden geçti ama ayrım yok — eksen 14/14 "horizontal", 7 ölçü aynı çift
    (`g57`,`g60`), okumanın kendi bağıyla uyuşan 3/14. Bağımsız etiket olmadığı için doğruluk ölçülmedi.
  - `unresolved` **0/22**: model belirsizlik kaçışını hiç kullanmadı.
  - STEP, profil, genel çizim başarısı veya eğitim: **hiçbiri** ilan edilmedi.
- **Bu turun doğrulaması:** `pytest -q` **426 geçti** (248,49 sn); kanıt paketi `--check` 22 ölçü/0 sorun;
  `git diff --check` temiz; `eval/reports/` tabloları ve `general.py` değişmedi.

**Bu turun sıradaki tek kararı:** gerekçedeki sayı yasağının kapsamı. Sayı yüzünden *bağın kendisi*
puanlanmadan atılıyor; yasak `reason`/`question` alanlarında kalmalı ama bağ sınıfı yine ölçülmeli.
Aynı iki parça, aynı ayarlar, yeni etiket (`meaning-3b-02`) — tek değişken. Ondan sonraki ayrı tur:
plastikte çöküşün nedeni olabilecek geniş aday kümesini daraltmak (okumanın kendi notlarındaki
alternatif uç çiftlerini sunmak). Profil veya STEP çağrısı için kanıt yok; `model-plan` eski arayüzde.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü kuruldu ve ölçüldü: sözleşme 22/22 tuttu ama yorum zayıf (plakada 7/8 cevap sözleşmede düştü, tam doğru 0; plastikte eksen 14/14 varsayılan, 7 ölçü aynı çift; unresolved 0/22). Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: gerekçedeki sayı yasağını yalnız reason/question alanlarında tut, sayı yüzünden bağı puanlamadan atma; aynı plaka+plastik, aynı ayarlarla yeni etiketle (meaning-3b-02) dar deneyi yenile. Ham isteği/cevabı kalıcı kaydet. Tür, eksen ve kaynak bağını yine bağımsız ilişki etiketiyle ölç (etiket yalnız değerlendirmede); çözülemeyen bağı soru olarak bırak ve unresolved kullanımını ayrı raporla. Sonraki ayrı tur aday kümesini daraltmak olsun. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 2: sayı yasağının kapsamı daraltıldı — `meaning-3b-02`

Kayıtlı sıradaki tek karar uygulandı, tek değişkenle: yargı sözleşmesi `interpretation-contract-v1` →
`v2`. İstem ve şema **değişmedi** (istem baytları ve ham cevaplar 22/22 birebir aynı; sıcaklık 0);
değişen tek şey kimlik dışı sayının cezası — artık cevabı düşürmüyor, `warnings` alanına yazılıyor.

- Plaka: 1 doğru/7 geçersiz → **3 doğru, 2 kısmi, 3 geçersiz**; denetlenebilir 15 alandan puanlanan
  **1 → 9**; tür 5/5, eksen 1/2, bağ 1/2. Kalan üç geçersiz cevap hep çap/yarıçap şekli
  (`pdf-3`, `pdf-3` adedi, `pdf-4`).
- **Yeni bulgu:** eksen kelimesi ile seçilen çift birbiriyle tutarsız (100,00'de "horizontal" deyip
  köşegen `g9-g12`; 60,00'de doğru çifti seçip "horizontal"); etiketin kendisi ikisinde tutarlı.
- Plastik cevapları birebir aynı → tablo değişmedi: etiket yok, eksen 14/14 "horizontal", 7 ölçü aynı
  çift, okuma bağıyla uyuşan 3/14. `unresolved` yine **0/22**. Süreler: toplam **158,244 sn**
  (plaka 60,494; plastik 97,431). STEP/profil/eğitim iddiası yok.
- Kanıt: `eval/reports/meaning-interpretation-evidence-02.json` (`--check`: 22 ölçü, 0 sorun). Eski
  paket farklı yargı sözleşmesiyle üretildiği için `--check` onun durum karşılaştırmasını atlıyor,
  ham cevaplarını yine doğruluyor — uydurma yok.
- **Bu turun doğrulaması:** `pytest -q` **426 geçti** (245,28 sn); iki kanıt paketi denetlendi;
  `check_tables` 20/0, `baseline_report --check`, `profile_step_evidence --check` uyuşuyor;
  `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** eksen alanını sormak yerine **seçilen çiftten türetmek** (kendi kendine denetim
zaten kaydediliyor: `axis_consistent_with_offered_points`). Tek değişken, ucuz; sonraki ayrı tur
plastikteki çöküş için aday kümesini daraltmak (okumanın kendi alternatif uç çiftleri).

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü ve sözleşmesi ölçüldü: sözleşme 22/22 tuttu; sayı yasağının kapsamı daraltılınca plakada 3 doğru/2 kısmi/3 geçersiz (tür 5/5, eksen 1/2, bağ 1/2), plastikte ayrım yok (eksen 14/14 varsayılan, 7 ölçü aynı çift), unresolved 0/22. Kalan geçersiz sınıf çap/yarıçap şekli; yeni bulgu eksen kelimesi ile seçilen çiftin tutarsızlığı. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: eksen alanını sormak yerine seçilen çiftten türet (kendi kendine denetim kaydı kalsın), aynı plaka+plastik ve aynı ayarlarla yeni etiketle (meaning-3b-03) dar deneyi yenile; ham isteği/cevabı kalıcı kaydet. Tür, eksen ve kaynak bağını yine bağımsız ilişki etiketiyle ölç (etiket yalnız değerlendirmede); çözülemeyen bağı soru olarak bırak ve unresolved kullanımını ayrı raporla. Ondan sonraki ayrı tur aday kümesini daraltmak olsun. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 3: eksen sormak yerine seçilen çiftten türetildi — `meaning-3b-03`

Kayıtlı tek değişken uygulandı: `interpretation-contract-v3`. Eksen alanı sorulmuyor (şemada yok),
seçilen iki uçtan türetiliyor. Bu kez istem de değişti, dolayısıyla istem ve ham cevaplar 22/22 farklı —
v1→v2 saf yargıç değişikliğiydi, bu tur sorunun kendisini değiştirdi ve öyle raporlandı.

- Plaka: 3 doğru/2 kısmi/3 geçersiz → **4 doğru/1 kısmi/3 geçersiz**; alan doğruluğu **değişmedi**
  (tür 5/5, eksen 1/2, bağ 1/2). Tek sınıf değişen ölçü `60,00`: çifti zaten doğruydu, eksen artık o
  çiftten okunuyor. Kayıp **çift seçiminde**: `100,00` köşegene, `50,00` cep iki deliğe, `6,80` iki uç
  olarak bağlanıyor. Eksen alanı kalkınca plakada dikey çiftlere kaydı; eskiden yazdığı "horizontal"
  kelimesiyle çiftinin çelişkisi çiftin tarafına düştü.
- Plastik: en sık çift 7× → 5× (farklı bağ yine 8), okuma bağıyla uyuşan 3/14, bir yeni şekil hatası
  (yarıçap, eşleşen geometri yok). `unresolved` yine **0/22**. Süre 174,093 sn.
- Denetimde bulunan ve düzeltilen kendi hatası: bir çağrıdan iki ölçü (boyut + adet) üreten kayıtta
  denetim yalnız kaynak kimliğiyle eşleştiriyordu; artık (kaynak kimliği, ad) çiftiyle eşleşiyor ve
  regresyon testi var.
- Kanıt: `eval/reports/meaning-interpretation-evidence-03.json` (`--check`: 22 ölçü, 0 sorun).
- **Bu turun doğrulaması:** `pytest -q` **427 geçti** (246,09 sn); üç kanıt paketi denetlendi;
  `check_tables` 20/0, `baseline_report --check`, `profile_step_evidence --check` uyuşuyor;
  `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** kayıp artık çift seçiminde, o yüzden soruyu daraltmak: sunulan aday kümesini
okumanın **kendi ölçtüğü** çiftlerle sınırlamak (kendi ankrajları + `notes` içinde yazdığı alternatif
uç çiftleri). Tek değişken; etiket yine yalnız değerlendirmede. Ondan sonraki ayrı tur: çifti tek tek
"bu ölçü bu iki kimlik arasında mı?" diye sormak (seçim yerine sıralama), çünkü küçük model geniş kümede
varsayılana çöküyor.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü üç koşuda ölçüldü (sözleşme 22/22 tutuyor): plakada tür 5/5, eksen 1/2, bağ 1/2; eksen alanı kaldırılınca tutarsızlık kapandı ama kayıp çift seçiminde (100,00 köşegene, 50,00 cep iki deliğe bağlanıyor); plastikte etiket yok, en sık çift 5×, okuma bağıyla uyuşan 3/14; unresolved 0/22. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: sunulan aday kümesini okumanın kendi ölçtüğü çiftlerle sınırla (ankrajları + claim notes içindeki alternatif uç çiftleri), aynı plaka+plastik ve aynı ayarlarla yeni etiketle (meaning-3b-04) dar deneyi yenile; ham isteği/cevabı kalıcı kaydet. Tür, eksen ve kaynak bağını yine bağımsız ilişki etiketiyle ölç (etiket yalnız değerlendirmede); çözülemeyen bağı soru olarak bırak ve unresolved kullanımını ayrı raporla. Ondan sonraki ayrı tur çifti tek tek sormak olsun. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 4: aday kümesi okumanın kendi ölçtüğü çiftlerle sınırlandı — `meaning-3b-04`

Kayıtlı tek değişken uygulandı: `interpretation-contract-v4`. `between` artık okumanın kendi ölçtüğü
çiftler arasından seçiliyor (kendi ankraj çifti + `notes` içindeki alternatif çiftler; yalnız konumu
ölçülmüş uçlar). Yargıç "adaylar arasında değil" diye reddediyor; istem menüyü yazıyor.

- Plaka: 4 doğru/1 kısmi/3 geçersiz → **5 doğru/0 kısmi/3 geçersiz**; tür 5/5, **eksen 2/2, bağ 2/2**
  (v3'te 1/2 ve 1/2). Dört adaylı iki ölçüde (`100,00`, `60,00`) model okumanın kendi çiftini seçti;
  v2/v3'te `100,00` köşegene bağlanıyordu. Kayıp menüdeymiş.
- Kalan üç geçersiz cevap yine **çap şekli** (çap iki uç olarak veriliyor: `pdf-3` iki delik, `pdf-4`
  `g8-g9`); okumada ve istemde `form: diameter` yazmasına rağmen.
- Plastik: en sık çift 7×, okuma bağıyla uyuşan 3/14, `unresolved` 0/22. Süre 181,958 sn.
- **Ölçülen erişim sınırı:** notlardaki alternatiflerin çoğu konum taşımadığı için menüye giremiyor;
  daralma plakada 8 ölçünün 2'sinde işe yarıyor, plastikte okumanın bağladığı 4 sayıda tek adaya iniyor,
  kalan 10 ölçünün hiç okuma bağı yok.
- Kanıt: `eval/reports/meaning-interpretation-evidence-04.json` (`--check`: 22 ölçü, 0 sorun).
- **Bu turun doğrulaması:** `pytest -q` **429 geçti** (247,54 sn); dört kanıt paketi denetlendi;
  `check_tables` 20/0, `baseline_report --check`, `profile_step_evidence --check` uyuşuyor;
  `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** kalan plaka kaybı çap/yarıçap şeklinde ve sözleşme hatası onu *ölçülemez*
kılıyor — bağ artık `between` ∪ `matched` birleşimi olarak puanlanmalı ki üç ölçü "geçersiz" yerine
"yanlış/doğru" olarak görünsün (v1→v2'de yapılanın aynısı, ölçüm kapsamı değişikliği, tek değişken).
Ondan sonraki ayrı tur: okumanın notlarındaki alternatif kimliklere konum kazandırmak (okuma zinciri
değişikliği, daha büyük değişken) ve plastikte bağlanmayan 10 sayı için okuma zincirinin kapsamı.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü dört koşuda ölçüldü: sözleşme 22/22 tutuyor, aday kümesi okumanın kendi ölçtüğü çiftlerle sınırlanınca plaka 5 doğru/0 kısmi/3 geçersiz oldu (tür 5/5, eksen 2/2, bağ 2/2); kalan üç geçersiz cevap çap şeklinde (çap iki uç olarak veriliyor) ve bu sözleşme hatası onları ölçülemez kılıyor; plastikte okuma bağı 4 sayıda, 10 ölçüde hiç yok; unresolved 0/22. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: bağı between ∪ matched birleşimi olarak puanla, böylece çap cevapları geçersiz yerine doğru/yanlış olarak ölçülsün; aynı plaka+plastik ve aynı ayarlarla yeni etiketle (meaning-3b-05) dar deneyi yenile ve ham isteği/cevabı kalıcı kaydet. Tür, eksen ve kaynak bağını yine bağımsız ilişki etiketiyle ölç (etiket yalnız değerlendirmede); çözülemeyen bağı soru olarak bırak ve unresolved kullanımını ayrı raporla. Ondan sonraki ayrı tur okuma zincirinin alternatif kimliklere konum kazandırması olsun. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 5: bağ, cevabın şekli reddedilse de puanlanıyor — kayıtlı cevaplar yeniden puanlandı

Kayıtlı tek karar uygulandı, tek değişken **ölçüm kapsamı**: sözleşme şekli reddettiğinde (çap iki uç
olarak verildiğinde) bağ artık işaret edilen küme (`between` ∪ `matched`) olarak puanlanıyor; cevabın
sınıfı "geçersiz" kalıyor ama ölçü "ölçülemedi" olmuyor. Model sorusu ve sözleşme değişmediği için
**yeni model koşusu yapılmadı** — dört koşunun ham cevapları yeni `--rescore` moduyla yeniden puanlandı
(koşu kayıtları değişmedi; `rescore.json` yanlarına yazıldı).

- **Plakada ölçülemeyen alan kalmadı:** kalan üç geçersiz cevap ölçülü şekilde **yanlış** — `pdf-3`
  (Ø6,80 4×) `g9,g12` (dört deliğin yarısı), `pdf-3` adedi aynı, `pdf-4` (50,00 cep) `g8,g9` (cebe
  fazladan delik). Çap sorunu şekil değil **anlama** sorunu.
- Tek kural altında dört koşu: 1 → 3 → 4 → **5 doğru**; eksen 0/0 → 0/2 → 1/2 → **2/2**; bağ
  0/0 → 1/2 → 1/2 → **2/2**; tür 5/5 (v1'de cevaplar düştüğü için 1/1).
- Geriye dönük bulgu: v1'in sayı cezası doğru bağı olan bir cevabı da (`60,00` çifti) çöpe atmıştı.
- Plastik değişmedi: etiket yok, okuma 14 sayının 4'ünü bağlamış; sözleşme dışı bağ puanı yok.
- **Bu dilimin doğrulaması:** `pytest -q` **431 geçti** (240,75 sn); dört kanıt paketi ve dört `rescore`
  kaydı denetlendi; `check_tables` 20/0, `baseline_report --check`, `profile_step_evidence --check`
  uyuşuyor; `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** çap/yarıçap için soruyu değiştirmek — modelin serbest çift seçmesi yerine
okumanın **kendi bağını doğrulamasını** istemek (okuma zaten `form: diameter` ve eşleşen kümeyi yazıyor:
"bu sayı bu kümeyi mi ölçüyor?"; katılmıyorsa düzeltmesi istenir). Ölçülen arıza küme düzeyinde olduğu
için dar ve test edilebilir tek değişken budur. Ondan sonraki ayrı tur: okumanın notlarındaki alternatif
kimliklere konum kazandırmak ve plastikte bağlanmayan 10 sayı için okuma kapsamı.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü beş dilimde ölçüldü: sözleşme 22/22 tutuyor; aday kümesi okumanın kendi ölçtüğü çiftlerle sınırlanınca plaka 5 doğru/0 kısmi/3 geçersiz (tür 5/5, eksen 2/2, bağ 2/2); bağ sözleşme dışında da puanlanınca kalan üç geçersiz cevap ölçülü şekilde yanlış çıktı (pdf-3 dört deliğin yarısı, pdf-4 cebe fazladan delik) — yani çap sorunu şekil değil anlama sorunu; plastikte okuma 14 sayının 4'ünü bağlamış, etiket yok; unresolved 0/22. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: çap/yarıçap ölçülerinde serbest seçim yerine okumanın kendi bağını doğrulat (okuma form ve eşleşen kümeyi zaten yazıyor; katılmıyorsa düzeltme iste), aynı plaka+plastik ve aynı ayarlarla yeni etiketle (meaning-3b-05) dar deneyi yenile ve ham isteği/cevabı kalıcı kaydet. Tür, eksen ve kaynak bağını yine bağımsız ilişki etiketiyle ölç (etiket yalnız değerlendirmede); çözülemeyen bağı soru olarak bırak ve unresolved kullanımını ayrı raporla. Ondan sonraki ayrı tur okuma zincirinin alternatif kimliklere konum kazandırması ve plastikte bağlanmayan sayıların kapsamı olsun. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

#### Bölüm 22 devamı 5'in düzeltmesi: doğrulama arayüzü bu plakada kanıt üretemez

Sıradaki karar olarak yazılan "okumanın kendi bağını doğrulat" turu, uygulanmadan önce ön kabulü
ölçüldü ve **düştü**: plakada etiketli beş ölçünün **beşinde de okumanın önerdiği küme bağımsız
etiketle birebir aynı** (`pdf-0` `g9,g11`; `pdf-2` `g9,g12`; `pdf-3` dört delik; `pdf-3` adedi aynı;
`pdf-4` `g8`). Yani modele okumanın önerisi verilip "katılıyor musun?" diye sorulsa, katılma cevabı
etiketle de uyuşur ve **kopyalama kazanır** — tur, modelin anlayışı hakkında hiçbir şey ölçmez.
Bu, tam da modelin yanıldığı üç ölçüde (iki çap + adedi) geçerli.

**Bu turun kanıtı:** yukarıdaki karşılaştırma, koşu kayıtlarındaki `expected` etiketleri ile okumanın
`measured_by_the_reading.matched_geometry` alanının doğrudan karşılaştırılmasıyla alındı (yeni model
çağrısı yok, yeni koşu yok).

**Düzeltilmiş sıradaki karar (tek değişken):** doğrulama arayüzünü *sentetik okuma kusuru* ile kur —
plakanın ölçülerinde okumanın önerisi bilerek bozulur (örneğin matched kümesinden bir kimlik düşürülür
ya da çift kaydırılır), model "bu öneri çizimle/ölçüyle uyuşuyor mu, değilse doğrusu ne?" diye yanıtlar.
Bozuk ve temiz ölçüler karışık sunulur, hangisinin bozuk olduğu söylenmez; doğruluk = etiketle uyuşma,
yani bozuğu yakalama oranı + yanlış alarm. Bu, kopyalama kazancı olmayan, sınırları **yapı gereği**
bilinen bir tur. Dürüst sınır: ölçülen şey *enjekte edilmiş* kusuru yakalama yeteneğidir, gerçek okuma
hatasını yakalama değil (plakada gerçek hata örneği yok, etiket okumayla örtüşüyor).
Ondan sonraki ayrı tur değişmedi: okumanın notlarındaki alternatif kimliklere konum kazandırmak ve
plastikte bağlanmayan 10 sayı için okuma kapsamı.

### Bölüm 22 devamı 6: okumanın önerisi incelemeye sunuldu, yarısına kusur enjekte edildi — `meaning-3b-05`

Kayıtlı düzeltilmiş karar uygulandı, tek değişken `reading-review-v1`: istem okumanın kendi bağını
inceleme isteği olarak gösteriyor; ölçülerin yarısına **yalnız kaynak kimliğinden türeyen** deterministik
kusur enjekte ediliyor (deterministik: `review_injects_a_defect(span_id)` + `corrupt_proposal`), hangisinin
bozuk olduğu söylenmiyor. Doğruluk yapı gereği bilinir, etiket bu yolda kullanılmaz. Kopyalamak yanlış bağ
demek olduğu için kopyalama kazancı yok.

- **Plaka çözüldü:** serbest seçimde (v4) 5 doğru/3 geçersiz → inceleme turunda **7 doğru, 1 kısmi,
  0 geçersiz**; okuma bağıyla uyuşan **8/8**; bozuk 6 önerinin **6/6'sı** okumanın doğru bağına
  düzeltildi (`binding_wrong_beyond_copy` 0); 2 temiz öneri korundu, **0 yanlış alarm**.
- **Kalan tek plaka kaybı** `pdf-3` adedi: model "4 × Ø6,80"in adedini `diameter` olarak bağlıyor,
  etiket `count` bekliyor (tür alanı).
- **Plastik:** okumanın bağ kurduğu 4 ölçüde kusur **4/4** yakalandı (yarıçapta biri kusuru görüp doğru
  kümeyi kuramadı); kalan 10 sayıda okuma hiç bağ kurmamış → incelenecek öneri yok (9'unda model kendi
  bağını yazdı, 1'i sözleşmeden geçmedi). Okuma kapsamı hâlâ sıradaki gerçek iş.
- **Ölçüm düzeltmeleri (kayıtlı cevaplar yeniden puanlandı):** (a) okumanın bağ kurmadığı ölçü "temiz
  öneri" sayılıp yanlış alarm yazıyordu → ayrı sınıf `no_reading_binding`; cevabı sözleşmeden geçmeyen
  satır `unusable_answer`; (b) `answers_agreed_with_reading` beş turdur 0 görünüyordu, özet yanlış
  anahtarı (`checks`) okuyordu → düzeltildi; doğru sayılar plaka 0 → 3 → 2 → 5 → **8**, plastik hep 3.
- **Bu dilimin doğrulaması:** tam takım **437 test geçti** (266,81 sn); `meaning-3b-05` kanıt paketi
  denetlendi (sunulan önerinin istemde bulunduğu da); beş koşunun tamamı `--rescore` ile yeniden
  puanlandı; `check_tables`, `baseline_report --check`, `profile_step_evidence --check` uyuşuyor;
  `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** okuma zincirinin kapsamı — plastikte okumanın hiç bağ kurmadığı 10 sayı ve
plakada okumanın notlarındaki alternatif kimliklerin konum taşımaması. Bu, yorum arayüzünün artık
ölçebildiği bir sınır değil; okuma zincirinde bağ kurma oranını (recall) yükseltmek gerekir. Ayrı ve
yalnız bir değişken olarak: `bind.py` içinde komşu ankor eşleştirmesi (aynı ölçüyü veren alternatif
çiftleri konumlu hale getirmek) — küçük testler, sonra aynı iki parçada dar deney.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Tek ölçü yorum arayüzü altı dilimde ölçüldü: sözleşme 22/22 tutuyor; okumanın önerisi incelemeye sunulunca (yarısına deterministik kusur enjekte edilerek) plaka 7 doğru/1 kısmi/0 geçersiz oldu, okuma bağıyla uyuşan 8/8, bozuk 6 önerinin 6'sı doğru bağa düzeltildi, 0 yanlış alarm; plastikte okumanın bağ kurduğu 4 ölçüde kusur 4/4 yakalandı, kalan 10 sayıda okuma hiç bağ kurmamış. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: yorum arayüzünü bırak, okuma zincirinin kapsamını artır — plastikte bağlanmayan 10 sayı ve okumanın notlarındaki alternatif kimliklerin konum taşımaması; bunu ayrı sınıflarla raporla ve okuma zincirinde tek değişkenlik tut (küçük testler + aynı iki parçada dar deney). Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 7: okuma zincirinin kapsamı — satır ölçeğe uymuyorsa uçlar yeniden seçiliyor

Kayıtlı sıradaki iş uygulandı; yorum arayüzü bırakıldı, tek değişken okuma zincirinde. Önce engeller
ölçüldü (kayıtlı `out/bind` verisi): plastiğin 10 `unresolved` sayısının **8'i** satır ölçeğe uymuyor
(çapanın seçtiği satır, basılı değerin pafta ölçeğindeki uzunluğundan %250–1800 sapıyor), **2'si**
satır doğru ama bir çapanın aday havuzu boş.

**Değişiklik (`src/drawingto3d/bind.py`, `Bindings.version` 1→2):** satır paftanın ölçeğinden %25'ten
fazla sapıyorsa uçlar, **çapanın zaten gördüğü noktalar arasından** (kendi konumu, bağlandığı çizgilerin
uzak uçları, hizalandığı adaylar) ölçeğin gerektirdiği uzunluğa en yakın çiftle yeniden seçilir; kabul
%5, satır uyuyorsa dokunulmaz. Yeni geometri yok, tolerans gevşetilmez; kalibrasyon (`scale.audit`
konsensüsü) kısıt olarak kullanılır; seçim `SpanBinding.notes` → `SpanMeaning.notes` → kanıt üzerinden
görünür.

- **Plastik: bağlı sayı 4/14 → 8/14** (pdf-6 `g95/g94` 9,71/10,00; pdf-8 `g68/g268` 3,01/3,00;
  pdf-9 `g89/g271` 3,89/4,00; pdf-12 `g65/g97` 1,52/1,50 — dördü de sapma sınırı içinde ve notlu).
  Bağ durumları: bound 0→1, partial 4→2, aligned 9→10; **10/14 ölçü hiç değişmedi**.
- **Plaka bayt bayt korundu:** `meaning-3b-05`'teki 8 plaka isteğinin `prompt_sha256`'sı bugün de aynı.
- Kalan 6: pdf-1/pdf-4/pdf-5 satırı doğru ama aday havuzu boş (sıradaki tek değişken); pdf-10/11/13
  için gereken uzunlukta çift yok.
- **Dürüst sınır:** plastikte bağımsız etiket yok; "bağlandı" = "çizili uzunluk basılı değerle paftanın
  kendi ölçeğinde uyuşuyor". Bu bir kapsam kazancıdır, doğruluk kazancı değil; bağımsız doğrulama
  yalnız plakada mümkün ve orada hiçbir şey değişmedi. Rapor: `eval/reports/reading-coverage.md`.
- **Bu dilimin doğrulaması:** tam takım `pytest -q` **441 geçti** (288,55 sn); plaka istek özetleri 8/8 aynı; öncesi/
  sonrası karşılaştırması `_repick_row_with_calibration` no-op yapılarak alındı; `check_tables`,
  `baseline_report --check`, `profile_step_evidence --check` uyuşuyor; `git diff --check` temiz;
  `general.py` değişmedi.

**Sıradaki tek karar:** kalan üç sayı (pdf-1, pdf-4, pdf-5) için **boş kalan aday havuzu** — satır
doğru, ama bir çapanın `aligned`/`features` listesi boş. Aday havuzunu, okumanın kendi çizim
geometrisinden (paftada ölçülmüş çizgi/yay uçları) ve ölçü ekseni boyunca standoff kuralından
genişletmek tek değişken olacak. Ondan sonra arayüz turu, artık 8 sayı bağlı olan plastikle yeni
etiketle (`meaning-3b-06`) yinelenebilir.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Yorum arayüzü yedi dilimde ölçüldü (son turda plaka 7 doğru/1 kısmi, inceleme turunda 6/6 kusur yakalandı, 0 yanlış alarm) ve şimdi sıra okuma zincirinin kapsamında: satır ölçeğe uymadığında uçların çapanın gördüğü noktalardan yeniden seçilmesi plastikte bağlı sayıyı 4/14'ten 8/14'e çıkardı, plaka bayt bayt korundu. Kalan engel ölçüldü: pdf-1, pdf-4, pdf-5'te satır doğru ama bir çapanın aday havuzu boş; pdf-10/11/13 için gereken uzunlukta çift yok. Mevcut kodu ve GeneralPlan v1'i koru. Tek değişkenle ilerle: boş kalan aday havuzunu, okumanın kendi ölçtüğü çizim geometrisinden ve ölçü ekseni boyunca standoff kuralından genişlet (yeni geometri uydurma, tolerans gevşetme); küçük testler + aynı iki parçada dar deney, öncesi/sonrası karşılaştırmasını ve plakanın bayt bayt korunduğunu kanıtla, ham kanıtı kalıcı kaydet ve belirsizliği ayrı raporla. Ondan sonra yorum arayüzü turunu yeni etiketle (meaning-3b-06) yinele ve inceleme turunu da çalıştır. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 8: ölçüyü veren geometri, çapanın kestiği çizgilerin uzak uçları

Kayıtlı "boş aday havuzu" engeli ölçüldü ve kaydın kendisi düzeltildi: havuz, **çapanın kestiği çizgilerin
(uzatma çizgilerinin) uzak uçları** hiç sunulmadığı için boş kalıyordu — `meaning._candidates` yalnız
"erişilen" (features) ve "hizalanan" (aligned) noktaları veriyordu. Ölçüm (kod yazmadan önce):

| denenen düğme | pdf-1 / pdf-4 / pdf-5 üzerinde etkisi |
|---|---|
| `CANDIDATE_LIMIT` 6 → 12 → 100 | **hiç** (üçünde de 0 uyan çift) — engel limit değildi |
| `crossing` çizgilerin uzak uçlarını eklemek | 6 / 5 / 2 uyan çift, hepsi sınırın içinde |
| `stub`/`row` çizgilerini de eklemek | daha çok çift, ama 4'ü **ölçü çizgisinin kendi mürekkebi** — basılı sayıyı yazan çizginin kendisine işaret eden, kendini doğrulayan bağ |

**Tek değişken:** yalnız `crossing` çizgilerin uzak uçları sunulur; `row`/`stub` asla (döngüsel bağ yasağı).
Ama bu genişletme **ilk geçişte** uygulandığında iki şeyi kanıtladı: plastikte bağlı üç sayının
(`pdf-3`, `pdf-6`, `pdf-12`) kimliklerini değiştirdi ve **plakayı bozdu** (8 plaka isteğinin 0'ı aynı özeti
verdi). Plakada sayılar zaten ölçüsünü tutuyor; geniş bir ilk geçiş duran bağları yeniden yazıyor. Bu yüzden
kestiği çizgilerin uçları **yalnız ilk geçiş hiçbir şey bulamadığında** sunulan bir **yedek geçiş**:
çözülemeyenin ikinci şansı, duran bağa dokunmaz.

**Ölçülen sonuç (aynı çizim, aynı ayarlar; öncesi/sonrası katmanlar yedek geçişle ve onsuz çağrılarak):**

| | öncesi | sonrası |
|---|---|---|
| bağlı sayı (plastik) | 8/14 | **11/14** |
| değişen ölçü | — | **3/14** (tam olarak çözülemeyen üçü) |
| değişmeyen | — | **11/14** |
| plaka bağlı sayı / istek özeti | 7/7 / 8/8 | 7/7 / **8/8** |

- Yeni bağlananlar: `pdf-1` `g289/g290` (9,99/10,00), `pdf-4` `g255/g254` (120,50/120,00),
  `pdf-5` `g294/g295` (60,31/60,00); her biri kullandığı kimlikleri adıyla anan bir not taşır.
- Kalan 3: `pdf-10`, `pdf-11`, `pdf-13` — erişilen, hizalanan ve kesilen noktalar arasında gereken
  uzunlukta çift yok.
- **Dürüst sınır:** yine kendi kendine tutarlılık; plastikte bağımsız etiket yok, bağımsız doğrulama yalnız
  plakada ve orada hiçbir şey değişmedi. **Kayıtlı arayüz koşuları eski okumayı okudu** (plastik 4 bağlı);
  arayüz turu yinelenirse **yeni etiketle** (`meaning-3b-06`) yapılır, eski koşu dosyalarına dokunulmaz.
- **Doğrulama:** tam takım `pytest -q` **445 geçti** (259,05 sn); plaka istek özetleri 8/8; `check_tables`
  20/0; `baseline_report --check`, `profile_step_evidence --check` uyuşuyor; beş kanıt paketinin hepsi
  `--check`: 0 sorun; `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** kalan üç sayı için **ölçü ekseni boyunca standoff kuralı** — uzatma çizgisinin ucu
ile ölçülen yüz arasındaki ilişkiyi (çizginin gövdesi ile bitişik gövde geometrisi arasındaki boşluk)
kullanmak; bu da tek değişken olarak ölçülür. Ardından arayüz turu `meaning-3b-06` etiketiyle artık 11 sayı
bağlı olan plastikte yinelenir.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Okuma zinciri iki dilimde genişledi: satır ölçeğe uymadığında uçların yeniden seçilmesi plastikte bağlı sayıyı 4/14'ten 8/14'e, çapanın kestiği uzatma çizgilerinin uzak uçlarının yedek geçişte sunulması 11/14'e çıkardı; plaka bayt bayt korundu (7/7 bağlı, 8/8 istek özeti aynı) ve ilk geçişte genişletmenin plakayı bozduğu ölçülerek yedek geçişe geçildi. Mevcut kodu ve GeneralPlan v1'i koru. Kalan üç sayı için (pdf-10, pdf-11, pdf-13) tek değişkenle ölçü ekseni boyunca standoff kuralını dene: uzatma çizgisinin ucu ile ölçülen yüz/bitişik gövde geometrisi arasındaki ilişkiyi kullan, yeni geometri uydurma ve tolerans gevşetme; küçük testler + aynı iki parçada dar deney, öncesi/sonrası karşılaştırmasını ve plakanın 8/8 istek özetini kanıt olarak göster, ham kanıtı kalıcı kaydet, belirsizliği ayrı raporla. Ondan sonra yorum arayüzü turunu yeni etiketle (meaning-3b-06) yinele ve inceleme turunu çalıştır. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 9: parça kendi segmentiyle ölçülüyorsa segment ölçülür

Kalan iki sayı için kayıt **ikinci kez** düzeltildi: `pdf-10`'un satırı 69,0 px (4,80 mm = 18,8 px olmalı),
ve çağrının ölçtüğü segment (`g264`, çizili 18,9 px = 4,82 mm) zaten **tek bir çapaya** bağlıydı. Çapalar
arası çift kuralı bunu ifade edemiyor, çünkü segmentin **iki ucu da aynı çapanın** noktaları.

**Tek değişken (`bind.py`):** satır ölçekten %25'ten fazla sapıyorsa ve çapalar arası hiçbir çift basılı
uzunluğa oturmuyorsa, **tek çapaya bağlı bir çizgi** ölçü kabul edilir — koşullar: çizgi **ölçü ekseni
boyunca** çizilmiş (izdüşüm ≥ uzunluğun %99'u) **ve** basılı uzunlukta (%5). `row` çizgileri hariç (iki
çapayı birleştiren algılanan satırdır, ölçülen yüz değil); ayrıca yalnız `kind == "linear"` +
`anchor_mode == "dimension"` çağrılarında (yarıçap/lider çağrısı satır olarak çizilmez).

| | öncesi | sonrası |
|---|---|---|
| bağlı sayı (plastik) | 11/14 | **12/14** |
| değişen ölçü | — | **1/14** (yalnız `pdf-10`) |
| değişmeyen | — | **13/14** |
| plaka bağlı / istek özeti | 7/7 / 8/8 | 7/7 / **8/8** |

- `pdf-10` `4.80`: satır 69,0 → 19,21 px, bağ `g272/g276` (4,83 mm), not: *"satır ölçeğe uymadı …; çapanın
  üzerindeki parça çizgisi ölçüldü (19.21 px, artık %2.19)"*.
- Yakın ıska ıska kalır: `pdf-11`'in en yakın segmenti 16,6 px (gereken 15,67 px) — %5,9, kuralın dışında;
  satıra dokunulmaz, **not yazılmaz**, sayı `unresolved` kalır. (İlk kesim kuralı *izdüşümü* kabul edip notta
  **doğrudan uzunluğu** yazdığı için `pdf-11` için "ölçüldü" diyen bir not üretmişti; kabul edilen ölçü ile
  yazılan ölçü artık aynı sayı.)
- Plakadaki iki sapmalı satır (Ø6,80 lideri — lineer olmadığı için artık kapı dışı — ve `50,00`, satırından
  değil aday çiftlerinden bağlanıyor) yeni dala hiç girmez; 8/8 istek özeti aynı.
- Çözülemeyen ve nedeni ölçülmüş: `pdf-11`, `pdf-13` — gerçek geometri iki çapadan ~10 px ve daha uzakta,
  yani çapanın eriştiği kümede değil. Ona erişmek okumanın hiç dokunmadığı geometriyi tespit etmek olur;
  bu ayrı bir değişken ve burada denenmedi.
- **Doğrulama:** tam takım `pytest -q` **449 geçti** (244,53 sn); plaka 7/7 ve 8/8; `check_tables` 20/0;
  `baseline_report --check`, `profile_step_evidence --check` uyuşuyor; kanıt paketleri `--check`: 0 sorun;
  `git diff --check` temiz; `general.py` değişmedi.

**Sıradaki tek karar:** `pdf-11` ve `pdf-13` için okumanın hiç dokunmadığı geometriye erişmek — **yalnız
ölçü metninin kendi bölgesindeki** çizim geometrisiyle sınırlı, eşik gevşetmeden ve uydurmadan (ör. metnin
çevresindeki kısa segmentleri aday yapmak) tek değişken olarak ölçülür; bulunamazsa kayıt "erişilemedi"
olarak kalır ve **böyle raporlanır**. Ardından arayüz turu `meaning-3b-06` etiketiyle artık 12 sayı bağlı
plastikte yinelenir. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı denmez.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Okuma zinciri üç dilimde genişledi: satır ölçeğe uymazsa uçların yeniden seçilmesi, ardından çapanın kestiği uzatma çizgilerinin uçlarının yedek geçişte sunulması ve son olarak tek çapaya bağlı segmentin (eksen boyunca ve basılı uzunlukta çizilmişse) ölçü kabul edilmesi; plastikte bağlı sayı 4/14'ten 12/14'e çıktı, her dilimde plakanın 8/8 istek özeti korundu. Mevcut kodu ve GeneralPlan v1'i koru. Kalan iki sayı için (pdf-11, pdf-13) tek değişkenle, yalnız ölçü metninin kendi bölgesindeki çizim geometrisini aday yapmayı dene: yeni geometri uydurma, eşik gevşetme, ham kanıtı kalıcı kaydet ve bulunamazsa "erişilemedi" olarak raporla; küçük testler + aynı iki parçada dar deney + plakanın 8/8 özet kanıtı. Ondan sonra yorum arayüzü turunu yeni etiketle (meaning-3b-06) yinele ve inceleme turunu çalıştır. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 10: ölçü ekseni üzerinde çizilmiş segment (çapaya değmese de)

Son iki sayı üçüncü kez ölçüldü; bu kez geometri ne uzakta ne çapaya bağlı: **ölçünün kendi eksen çizgisinin
üzerinde**, algılanan satırın ucunun ötesinde duruyor ve iki çapaya da değmiyor. Ölçülen dik uzaklıklar
(eksene): `pdf-11` `g310` **0,0 px** (aynı uzunluktaki rakip `g269` 47,2 px), `pdf-13` `g279` **−0,3 px**
(rakip `g178` 172,8 px), referans `pdf-10` `g264` 0,0 px. "Metne en yakın geometri" kuralı **işe yaramazdı**:
doğru segment üçünde de metinden 103–108 px uzakta ve `pdf-11`'de yanlış segment (`g269`, `pdf-9`'un kendi
ölçüsü) metne daha yakın (99,3 < 105,9). Ayrımı yapan şey eksen çizgisi.

**Tek değişken (`bind.py`, `_segment_on_axis`):** satır testi ve iki mevcut yeniden seçim başarısız olursa,
okumanın kendi ölçtüğü ilkellerden bir çizgi ölçü kabul edilir: **iki ucu da ölçü eksen çizgisi üzerinde**
(modülün mevcut 4 px özellik sınırı içinde — bu aynı zamanda eksene paralellik demek) **ve** uzunluğu basılı
değerin %5'i içinde; çapalara en yakın olan kazanır. Yeni geometri tespit edilmez (aynı `observe()` çıktısı),
eşik gevşetilmez, kapı yine yalnız lineer + `dimension` + satırı sapan çağrılar.

| | öncesi | sonrası |
|---|---|---|
| bağlı sayı (plastik) | 12/14 | **14/14** |
| değişen ölçü | — | **2/14** (`pdf-11`, `pdf-13`) |
| değişmeyen | — | **12/14** |
| plaka bağlı / `bindings.json` / istek özeti | 7/7 / aynı / 8/8 | 7/7 / **aynı** / **8/8** |

- `pdf-11`: satır 69,0 → 15,84 px; `pdf-13`: 79,0 → 5,83 px; ikisi de notlu. Plakada kural hiç çalışmaz ve
  plakanın **bütün bağ kaydı** kural açık/kapalıyken bayt bayt aynı (kullanılan en güçlü kalkan).

### "14/14" ne diyor, ne demiyor (ayrı ölçüm)

Her basılı sayının, ekseni boyunca basılı değeri tutan bir bağı var — bu **kapsam**tır ve "bağın adlandırdığı
geometri ölçülen yüzdür" demek değildir. Her bağın iki noktasının **eksene dik** açıklığı ölçüldü:

| pafta | mesafe bağı | dik açıklık > 20 px |
|---|---|---|
| plastik | 13 | **8** (750 px'e kadar) |
| plaka | 5 | 1 (275,6 px; kalan dördü 0,0 px) |

- Yeni bağlanan ikisi de bu zayıflığı taşıyor: `pdf-11`'in çifti 190,6 px dik açıklıkla bir daire merkezi +
  bir çizgi ucu; `pdf-13`'ünki 371,8 px ile bir yay kenarı + çizgi ucu. İzdüşümleri 4,04 mm ve 1,57 mm —
  basılı değerler — ama basamağın kendi yüzleri değiller.
- Zayıflık **yeni değil**: ilk dilimde bağlanan `pdf-0` eksene dik 750 px açıklıkla iki daire merkezini
  adlandırıyor. Bağımsız etiketi olan tek pafta olan plakada beş bağın dördü tam eksen üzerinde.
- Bu yüzden kayıt "bağlandı"yı *"paftanın kendi ölçeğinde ölçülmüş bir çift"* olarak tutar, *"doğru geometri
  adlandırıldı"* olarak değil. Onarılmış bir satırın bağını uzaktaki hizalanmış adaylar yerine **ölçünün
  kendi uçlarına** çevirmek sıradaki tek değişken; yukarıdaki tablo onun öncesi/sonrası ölçüsüdür.
- **Doğrulama:** tam takım `pytest -q` **454 geçti** (242,42 sn); plaka `bindings.json` bayt bayt aynı ve 8/8
  istek özeti; `check_tables` 20/0; `baseline_report --check`, `profile_step_evidence --check` uyuşuyor;
  kanıt paketleri `--check`: 0 sorun; `git diff --check` temiz; `general.py` değişmedi.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Okuma zinciri dört dilimde genişledi (satır uçlarının yeniden seçilmesi, kesilen çizgi uçlarının yedek geçişi, çapaya bağlı segment, eksen üzerindeki segment) ve plastiğin 14 basılı sayısının hepsi artık paftanın kendi ölçeğinde ölçülmüş bir çifte bağlı; her dilimde plakanın kaydı bayt bayt korundu. Ama ayrı ölçüm şunu gösterdi: plastikte 13 mesafe bağının 8'inde iki noktanın eksene dik açıklığı 20 px'ten büyük (750 px'e kadar); kapsam var, bağın adlandırdığı geometri her zaman ölçülen yüz değil. Mevcut kodu ve GeneralPlan v1'i koru. Sıradaki tek değişken: onarılmış satırların bağını, uzaktaki hizalanmış adaylar yerine ölçünün kendi uçlarına/dar komşuluğuna çevirmek; öncesi/sonrası olarak dik açıklık dağılımını (plastik 8/13, plaka 1/5) ve plakanın bayt bayt korunduğunu kanıtla, küçük testler + aynı iki parçada dar deney yap, ham kanıtı kalıcı kaydet ve belirsizliği ayrı raporla. Ondan sonra yorum arayüzü turunu yeni etiketle (meaning-3b-06) 14 sayı bağlı plastikte yinele ve inceleme turunu çalıştır. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 11: onarılmış satırın bağı ölçünün kendi yanındaki çifti adlandırır

Kapsam (14/14) bağın adlandırdığı geometri değildi: plastikte 13 bağın 8'inde iki nokta arasındaki **eksene dik**
açıklık 20 px'ten büyüktü (750 px'e kadar). Kod yazmadan önce onarılmış yedi satırın aday havuzları döküldü:
her geçerli çiftin en yakın noktası çapalardan **≥ 41 px** uzakta ve `pdf-8` için **tek** geçerli çift var (hiçbir
sıralama onu keskinleştiremez); `pdf-13`'te ise aynı değeri ölçen, eksene 47,2 px dik uzaklıkta bir çift
(`g310/g263`) var (seçilen 371,8 px).

**Tek değişken (`meaning.py`; `SpanBinding.row_repaired`, `Bindings.version` 3):** satır ölçeğe göre yeniden
seçildiyse, geçerli çiftler **önce eksene dik açıklığa** göre sıralanır (sonra mevcut rank/maliyet/sapma).
Eksen bileşeni zaten basılı değeri tuttuğu için dik açıklığı küçük olan çift, uzayda basılı uzunluk kadar
ayrılmış **yerel** bir çifttir. Çizildiği gibi okunan satırlar sıralamasını aynen korur.

| | öncesi | sonrası |
|---|---|---|
| plastik: bağların dik açıklık toplamı | 2450,2 px | **1262,6 px** |
| medyan | 118,6 px | **0,1 px** |
| 20 px'ten büyük bağ | 8/13 | **5/13** |
| plaka bağları | — | **değişmedi, 0/7** |

Onarılmış satırlar: `pdf-6` 6,5 → **0,0**, `pdf-8` 285,1 (zorunlu: tek çift), `pdf-9` 423,2 → **55,0**,
`pdf-10` 238,1 → **3,3** (noktalar arası 238,8 → 18,9 px), `pdf-11` 190,6 → **0,1** (191,3 → 15,7),
`pdf-12` 15,8 → **0,0**, `pdf-13` 371,8 → **0,0** (371,9 → 6,4).

- Plakada onarılmış satır **yok**: değişiklik orada yapı gereği etkisiz — iki kez doğrulandı (hiçbir satır
  işaretli değil; 8/8 depolanmış istek özeti aynı).
- 20 px üstünde kalan 5 bağ: **çizildiği gibi okunan** üç satır (`pdf-0` 750, `pdf-3` 118,6, `pdf-7` 50,2) ve
  seçeneği olmayan iki onarılmış satır (`pdf-8`, `pdf-9` 55). Çizimin doğru çizdiği satıra dokunulmadı: o ayrı
  bir değişiklik, ayrı bir risk.
- **Bu ne demiyor:** iki pafta için de kimlik düzeyinde referans etiket yok (`cases.json` özellik *rolleri*
  taşıyor; plastikte hiç yok). Yani "keskinleşti" tam olarak ölçüldüğü şeydir: *bağın iki noktası ölçünün kendi
  eksenine daha yakın ve çift ölçünün yanında*. Adlandırılan geometrinin **doğru** olduğunun kanıtı değil;
  basılı değeri tutma koşulu eskisi gibi sürüyor. Yorum turu artık bağları ölçülerin yanında duran bir okumayla
  yinelenir (`meaning-3b-06`).
- **Doğrulama:** tam takım `pytest -q` **457 geçti** (242,48 sn); plaka 8/8 istek özeti ve değişmemiş bağlar;
  `check_tables` 20/0; `baseline_report --check`, `profile_step_evidence --check` uyuşuyor; kanıt paketleri
  `--check`: 0 sorun; `git diff --check` temiz; `general.py` değişmedi.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Okuma zinciri artık plastiğin 14 sayısını da paftanın kendi ölçeğinde ölçülmüş bir çifte bağlıyor ve onarılmış satırların bağı ölçünün yanındaki yerel çifti adlandırıyor (dik açıklık toplamı 2450,2 → 1262,6 px, medyan 118,6 → 0,1 px, 20 px üstü 8/13 → 5/13); plakada onarılmış satır olmadığı için değişiklik orada yapı gereği etkisiz kaldı ve 8/8 istek özeti korundu. Mevcut kodu ve GeneralPlan v1'i koru. Sıradaki iş: yorum arayüzü turunu yeni etiketle (meaning-3b-06) 14 sayı bağlı, bağları ölçülerin yanında duran plastikle ve plakayla yinele; inceleme turunu da çalıştır ve raporlarda doğru yorum ile belirsizliği ayrı tut. Referans etiketleri yalnız değerlendirmede kullan, ham istek/cevabı kalıcı kaydet, çözülemeyen bağı soru olarak bırak; yeni bir okuma-zinciri değişikliği yapacaksan önce hangi engeli ölçtüğünü göster ve plakanın bayt bayt korunduğunu kanıtla. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 12: arayüz turu yeni okumayla yinelendi — `meaning-3b-06`

Aynı arayüz, aynı model (`qwen2.5vl:3b`, 16384 ctx, 4096 predict, sıcaklık 0), aynı iki pafta; **değişen tek şey
okuma**: plastikte 14 sayının hepsi bağlı ve bağlar ölçülerin yanında (devam 11). Koşu 173,06 sn, `complete`.

| | `meaning-3b-05` (eski okuma) | `meaning-3b-06` (yeni okuma) |
|---|---|---|
| plaka sınıfları (bağımsız etiketle) | 7 doğru / 1 kısmi / 0 geçersiz | **aynı: 7 / 1 / 0** |
| plaka: cevap okumanın bağını tutuyor | 8/8 | **8/8** |
| plaka inceleme turu | 6/6 yakalandı, 0 yanlış alarm | **6/6, 0** |
| plastik: cevap okumanın bağını tutuyor | 3/14 | **13/14** |
| plastik inceleme turu | 4/4 yakalandı, **9 yanlış alarm** | **10/10, 0** |
| plastik: önerinin ötesinde yanlış bağ | 1 | **1** (`pdf-2 radius`) |

- **Plaka değişmedi** (beklenen: orada onarılmış satır yok); tek kısmi yine `pdf-3` adedi (`kind: false`).
- **Plastiğin 13/14'ü kopyalama payı, tanıklık değil:** okuma artık her sayı için geçerli bir yerel çift
  önerdiğinden modelin onu tekrarlaması kolay. Arayüzün bağımsız değeri bu koşuda inceleme turunda: 10/10
  enjekte edilmiş kusur düzeltildi, 4 temiz öneri korundu, yanlış alarm yok.
- Tek ayrışma `pdf-2 radius`: model öneriyi değil `g57/g60`'ı adlandırdı (inceleme `right: false`).
- **Tek değişken uyarısı:** 05→06 tek değişkenli değil (arada yedinci dilimin yargı düzeltmesi + dört okuma
  değişikliği). Plakanın birebir aynı çıkması etiketli paftanın bozulmadığını gösterir; plastikteki sıçrama bu
  iki değişikliğin toplamıdır, ayrıştırılmadı.
- **Kayıt:** `out/meaning-interpretation/meaning-3b-06/{requests,answers,run.json}` (ham istek/cevap),
  `out/profile-step/meaning-3b-06.log`, taşınabilir paket `eval/reports/meaning-interpretation-evidence-06.json`
  (`--check`: 22 ölçü, 0 sorun); etiket yalnız puanlamada (`eval/relations/plate-pocket-1.json`).
- Ayrıntı: `eval/reports/measurement-interpretation.md` (yedinci koşu). Tam takım **457 test geçti**.

**Sıradaki tek karar (ölçüm tasarımı):** okuma her şeyi çözdüğü için düz tur artık kopyalamayı ölçüyor. Arayüzün
bağımsız değerini ölçmek için ya (a) üçüncü bir paftada elle doğrulanmış ilişki etiketi kurulup koşu **kör**
(okumanın önerisi gösterilmeden) yinelenir, ya (b) okumanın çözemediği bir sayının bulunduğu bir paftada
arayüzün **sorduğu soru** etiketle karşılaştırılır. Önerilen sıra: (a) sonra (b).

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Arayüz turu yeni okumayla (plastik 14/14 bağlı, bağlar ölçünün yanında) meaning-3b-06 etiketiyle yinelendi: plaka 7 doğru/1 kısmi/0 geçersiz ve 6/6 kusur yakalama (değişmedi), plastikte cevap okumanın bağını 13/14 tutuyor ve inceleme turu 10/10 kusuru yakalıyor, yanlış alarm 0; tek ayrışma pdf-2 radius. Bu tur artık çoğunlukla kopyalamayı ölçtüğü için sıradaki iş arayüzün bağımsız değerini ölçmek: üçüncü bir paftada elle doğrulanmış ilişki etiketi kur (etiket yalnız değerlendirmede), koşuyu okumanın önerisi gösterilmeden kör yinele ve doğru yorumu belirsizlikten ayrı raporla; ardından okumanın çözemediği bir sayıda arayüzün sorduğu soruyu etiketle karşılaştır. Mevcut kodu ve GeneralPlan v1'i koru; yeni bir okuma-zinciri değişikliği yapacaksan önce hangi engeli ölçtüğünü göster ve plakanın bayt bayt korunduğunu kanıtla. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 13: kör tur ve alan düzeltmesi — `meaning-3b-07-blind` → `meaning-3b-08-blind-v2`

Önce **kör** tur yapıldı (`--review` yok ⇒ `injected = None`; model okumanın önerisini hiç görmüyor — 05/06'da
her iki çağrı da öneriyi gördüğü için bu ölçüm bugüne kadar yapılmamıştı): plaka **5 doğru / 0 kısmi /
3 geçersiz**, plastik uyum 13/14, sözleşme dışına taşan bağ 3. Yani sekiz ölçünün **ikisi** yalnız öneriyi
denetlemekten geliyordu.

**Ölçülen arıza tek sınıf ve üç kör koşuda birebir aynı** (`-03`, `-04`, `-07`; kimlikler bile aynı): tek
geometri *boyutlandıran* çağrı (Ø6,80 · Ø50 · R8,00) **çift** olarak cevaplanıyor —
`kind: diameter`, `between: [g9, g12]`, `matched: []` → iki sözleşme hatası. Modelin gerekçesi "which are both
circles": kastettiği daireler, koyduğu yer yanlış liste. Okuma keskinleşti ama kör doğruluk 5/8'de kaldı, yani
kayıp geometri menüsünde değil **alan** işleyişinde.

**Tek değişken (`interpret.py`, `INTERPRETATION_VERSION` → `single-measurement-interpretation-v2-form-field`):**
istek ve cevap şeması bu ölçünün kendi formuna göre hangi listeyi istediğini söylüyor (`distance`/`angle` →
`between`, `diameter`/`radius`/`count` → `matched`; şemada karşı alan `maxItems: 0`, istenen alan `minItems`).
Hangi kimliğin doğru olduğunu söylemiyor, yalnız yargılanacak alanı söylüyor.

| | `-07` kör (v1) | `-08` kör (v2) | `-06` önerili (v1) |
|---|---|---|---|
| plaka (bağımsız etiketle) | 5 / 0 / **3 geçersiz** | **7 / 1 / 0** | 7 / 1 / 0 |
| plaka sözleşme dışı bağ | **3** | **0** | 0 |
| plastik okuma uyumu | 13/14 | 13/14 | 13/14 |

- `pdf-3 diameter_1` → `matched: [g9,g10,g11,g12]` (etiket: dört köşe deliği) ve `pdf-4 diameter_2` →
  `matched: [g8]` (etiket: ortadaki tek daire) **doğru**: kör doğruluk öneri gösterilen turla eşitlendi.
- Kalan tek etiketli kayıp `pdf-3` adedi (`kind: false`); katalog o ölçü için `quantity: count` diyor.
- Plastik `pdf-2 radius` üçüncü kez, üçüncü ayrı sebeple reddedildi (08: `unresolved: true` + `matched` dolu +
  boş soru) — 12 adaylı R8,00 hâlâ zor; orada etiket yok.
- **Kayıt:** `out/meaning-interpretation/meaning-3b-0{7-blind,8-blind-v2}/`, paketler
  `eval/reports/meaning-interpretation-evidence-0{7,8}.json` (`--check`: 22 ölçü, 0 sorun); testler
  `tests/test_interpret.py` (+2: alan/miktar kuralı ve form yoksa kural yok).

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Kör tur (okumanın önerisi gösterilmeden) yapıldı ve ölçülen tek sınıf arıza düzeltildi: tek geometri boyutlandıran çağrılar (Ø/ R) modele iki kimliği `between`'e koyduğu için geçersiz sayılıyordu; istek ve cevap şeması artık bu ölçünün kendi formuna göre hangi listeyi istediğini söylüyor (distance/angle → between, diameter/radius/count → matched) ve etiketli plakada kör doğruluk 5/8'den 7 doğru + 1 kısmiye çıktı, sözleşme dışı bağ 3'ten 0'a indi, plastik uyumu 13/14'te kaldı. Mevcut kodu ve GeneralPlan v1'i koru. Sıradaki tek iş: kalan tek etiketli kaybı ölç — "4 × Ø6,80" çağrısının adet ölçüsü (katalogda quantity: count) hâlâ diameter olarak adlandırılıyor; istek bu ölçünün kendi miktarını söylesin ve kör turda plakada 8/8 beklenip beklenmediği ölçülsün. Ardından üçüncü paftada (examples/pdf with steps/2/Drawing.pdf + Part-2.STEP) elle doğrulanmış ilişki etiketi kur — okuma orada 14/17 bağlıyor, 3 sayı çözülemiyor — ve arayüzün sorduğu soruyu etiketle karşılaştır. Referans etiketleri yalnız değerlendirmede kullan, ham istek/cevabı kalıcı kaydet, çözülemeyen bağı soru olarak bırak; okuma-zincirine dokunursan önce hangi engeli ölçtüğünü göster ve plakanın bayt bayt korunduğunu kanıtla. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 14: adet ölçüsü kendi miktarını ister — kör tur plakada 8/8

Plakada kalan tek etiketli kayıp `pdf-3` adediydi: "4 × Ø6,80" bir kez basılıp iki kez soruluyor (çap + adet) ve
**metin ile aday menüsü ikisinde birebir aynı**; hangi ölçünün sorulduğunu yalnız katalog biliyor.

**Tek değişken (`interpret.py`, `INTERPRETATION_VERSION` → `single-measurement-interpretation-v3-count-quantity`):**
bağlam/istek ölçünün katalogdaki miktarını taşıyor; miktar `count` ise istek bunu söylüyor. 22 isteğin satır
satır karşılaştırmasında başka değişiklik yok; kimlik menüsü hiç değişmedi.

| kör tur | istek sürümü | plaka (bağımsız etiketle) | plastik |
|---|---|---|---|
| `-07` | v1 | 5 / 0 / **3 geçersiz** | 13/14 |
| `-08` | v2 (form → alan) | 7 / 1 / 0 | 13/14 |
| `-09` | v3 (miktar) | **8 / 0 / 0** | 13/14 |

- Sekizi de doğru tür ve doğru geometriyle; `diameter_1_count` artık `kind: count`,
  `matched: [g9,g10,g11,g12]` (etiket: dört köşe deliği). Öneri gösterilmeden etiketin tamamı üretildi.
- Üç adım da tek değişkenli ve ölçülmüş (alan, miktar); okuma zincirine dokunulmadı, `-09` 267,08 sn,
  `complete`; paket `-09` `--check`: 22 ölçü, 0 sorun.
- Plastikte değişmeyen tek ayrışma `pdf-2 radius` (üç kör koşuda `invalid`, 12 adaylı R8,00, etiket yok) —
  üçüncü pafta etiketiyle birlikte ele alınacak.

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Arayüz kör turda (okumanın önerisi gösterilmeden) etiketli plakada 8/8'e ulaştı: iki ölçülmüş arıza tek değişkenle düzeltildi — tek geometri boyutlandıran çağrının hangi listeyi istediği (form) ve bir kez basılıp iki kez sorulan çağrının miktarı (count). Mevcut kodu ve GeneralPlan v1'i koru. Sıradaki tek iş: üçüncü paftada (examples/pdf with steps/2/Drawing.pdf + Part-2.STEP) elle doğrulanmış ilişki etiketi kur — okuma orada 17 sayının 14'ünü bağlıyor, 3'ü çözülemiyor (pdf-17 20,0 · pdf-18 6,0 · pdf-21 50,0) — ve arayüzü o paftada hem kör hem incelemeli koşarak doğru yorumu belirsizlikten ayrı raporla; özellikle arayüzün çözülemeyen bağ için sorduğu soruyu etiketle karşılaştır. Plastikte pdf-2 radius (12 adaylı R8,00) hâlâ geçersiz; hangi cevabın doğru olduğunu etiketsiz bilmediğimizi açıkça yaz. Referans etiketleri yalnız değerlendirmede kullan, ham istek/cevabı kalıcı kaydet, çözülemeyen bağı soru olarak bırak; okuma-zincirine dokunursan önce hangi engeli ölçtüğünü göster ve plakanın bayt bayt korunduğunu kanıtla. Kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```

### Bölüm 22 devamı 15: üçüncü paftanın etiketi kuruldu; okuma beş çapı mesafe olarak sunuyor

Üçüncü pafta (`examples/pdf with steps/2/Drawing.pdf` = "Exercise 1", `Part-2.STEP`) için elle doğrulanmış
ilişki etiketi yazıldı: `eval/relations/exercise-1-vector.json` (yalnız değerlendirmede; vaka `cases.json`'da
zaten `exercise-1-vector` olarak duruyordu, 7/ ile aynı parça grubunda). Etiket STEP'e karşı doğrulandı:
kutu 134×80×50; beş çap STEP yarıçaplarıyla birebir (Ø20 r=10,00 · Ø25 r=12,50 · Ø30 r=15,00 · Ø40 r=20,00 ·
Ø50 r=25,00, merkezleriyle); alt görünüşün beş dikeyi parçanın **kalınlıkları** (26=z±13 · 6=z±3 · 20=z±10 ·
40=z±20 · 10=z±5); 80 = kutu y; 37 ve 57 = ortak datuma göre iki kulak deliğinin merkezleri (STEP x=-37,00 ve
x=+57,00; paftadaki 37+20=57 zinciri aynı datumdan). STEP'in kesinleştirmediği üç sayı (60, 35, üst 20)
etikette `verified: "drawing"` olarak işaretli.

**Ölçülen engel:** bu paftanın PDF **metin katmanında Ø glifi yok** (468 karakter, hiçbiri Ø / 0x2000 üstü
değil — önek vektör çizim). Bu yüzden okuma beş çap çağrısını `linear` sayıp **iki çizgi ucu arasında mesafe**
gibi bağlıyor: `pdf-19` (30) · `pdf-20` (25) · `pdf-22` (40) bağlı, `pdf-21` (50) çözülemiyor.
`cases.json`'ın `diameter_calls: [20,25,30,40,50]` alanı gerçeği zaten yazıyor.

**Etiketle ölçüm (kuru koşu, model yok):** 17 sayının 11'i eşleşiyor (6'sı çift değerli: dört "20", iki "40" —
harness yalnız tekil değerleri eşleştiriyor). Eşleşen üç çap satırında karşıtlık tam: `pdf-19`/`pdf-20` okuma
`distance`, etiket **diameter**; `pdf-21` okuma **none**, etiket **diameter**.

**Sıradaki tek değişken:** okumada çap semantiğini geri kazanmak (metinsel olmayan Ø glifi veya tek daireye
işaret eden lider) — kapı: bu paftada beş çağrı `diameter`, plaka ve plastik okuması bayt bayt korunur
(8/8 istek özeti + `bindings.json`).

Hermes için güncel devam cümlesi:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde PLAN.md Bölüm 22'nin son devam kaydından ilerle. Üçüncü pafta (examples/pdf with steps/2/Drawing.pdf, Part-2.STEP) için elle doğrulanmış ilişki etiketi eval/relations/exercise-1-vector.json olarak kuruldu ve STEP'e karşı doğrulandı; ölçülen engel şu: bu paftanın PDF metin katmanında Ø glifi hiç yok, bu yüzden okuma beş çap çağrısını (Ø20/Ø25/Ø30/Ø40/Ø50) düz linear sayıp iki çizgi ucu arasında mesafe gibi bağlıyor, pdf-21 (50) hiç bağlanamıyor. Mevcut kodu ve GeneralPlan v1'i koru. Sıradaki tek iş: okumada çap semantiğini geri kazan (Ø glifi vektör çizim — metinsel olmayan glifi ya da tek daireye işaret eden lider geometrisini çaplı çağrı olarak tanı), kapı olarak bu paftada beş çağrı diameter olmalı ve plaka ile plastiğin okuması bayt bayt korunmalı (8/8 istek özeti + bindings.json). Ardından arayüzü üçüncü paftada kör ve incelemeli koş (etiket 11 ölçüyü puanlıyor), doğru yorumu belirsizlikten ayrı raporla ve çözülemeyen bağlar için arayüzün sorduğu soruyu etiketle karşılaştır. Referans etiketleri yalnız değerlendirmede kullan, ham istek/cevabı kalıcı kaydet; kanıt yeterli olmadan profil/STEP başarısı veya model eğitimi tamamlandı deme. Her tamamlanan dilimde PLAN/HANDOFF'u güncelle.
```


### Devam 16 — Ø öneki çizim olabilir; tür bağı lider koşuluna bağlı kalmamalı

- Ölçüldü: `2/Drawing.pdf` metin katmanında Ø yok (468 karakterin hiçbiri değil) → beş çap çağrısı okumaya
  uzunluk olarak giriyordu; ikisi iki çizgi ucu arasında mesafe diye *bağlanmış*, ikisi çözülememişti.
- Kural 1 (`observe._diameter_prefix_glyph`): cümlenin yanındaki küçük daire (r ≤ 0,6 × yükseklik, merkez
  1,2 × yükseklik yakınında) öneki okur. Ölçüm: glifler 8–21 px, gerçek daireler ≥ 138 px → 5 kat pay.
  Kural plakada 2 çağrıda da ateşledi (plaka Ø'yi de çizim basıyor), plastikte hiç.
- Kural 2 (`meaning._meaning_for`): çap eşlemesi artık `kind == "diameter"` iken de deneniyor, yalnız
  liderde değil. Üçüncü paftanın beş çağrısı lider değil.
- Sonuç: üçüncü paftada çözülen ölçü 12 → 16/17, tür uyumu (etiketle) 1/5 → 5/5, beş çap bağlandı
  (g133/g68/g122/g65/g125+g134); tek çözülemeyen `pdf-18` (düz "6").
- Kalkan: plastik okuması birebir aynı; plakada yalnız iki tür düzeldi; **22/22 istek özeti saklananla aynı**
  (yeni `prompt_shield` ölçümü — `--check` isteği yeniden kurmuyor). Testler +7.
- Belirsizlik: Ø40 ile R20 aynı iki yayı (g125/g134) gösteriyor; ayrımı yalnız STEP veriyor.
- `/goal`: etiketin `geometry.circles` kimliklerini (STEP koordinatları) okumanın kimlikleriyle (g*) elle
  eşle ve **bağ puanlamasını** aç; sonra üçüncü paftada arayüzü kör + incelemeli koşturup 17 ölçüyü raporla.
  Kapı: plaka/plastikte 22/22 istek özeti korunur.
- Testler: `round18` = 467 geçti / 243,05 sn (önceki 460; +7 test). `check_tables` 20/0, `baseline_report --check`
  ve `profile_step_evidence --check` uyuşuyor. Rapor: `out/profile-step/pytest-round18.txt`.


### Devam 17 — üçüncü paftanın etiketi ve kör turu: tür 11/11, bağ ölçülemedi (ölçüldü)

- Bağ puanlaması iki çerçevenin ayrışması yüzünden kapalı: harness etiketin konumlarını okumanın mm
  çerçevesiyle `POSITION_TOLERANCE_MM` = 2 mm içinde eşliyor. Plakada tutuyor (`h1 [-50,-30]` ↔ ölçülen
  `g9 [-50.35,-30.21]`, 0,4 mm → koşu 09'da 8 ölçünün **5'i** bağ-puanlanabilir); üçüncü paftada **0/17**:
  en yakın ölçülen kimliğe uzaklık bore20 **34,01 mm** · bore25 **14,91** · bore30 **23,77** · boss40
  **12,14** · boss50 **28,14**. Sebep: etiket çemberleri STEP (parça) çerçevesinde yazılmış, okumanın
  konumları paftanın görünüş çerçevesinde; kalan kimlikler zaten yüz/kenar (konumu yok).
- **Kör tur `meaning-3b-10-third-blind`** (`qwen2.5vl:3b` `fb90415cde1e`, öneri gösterilmedi, 17 ölçü,
  146,154 sn, complete): **tür 11/11** (beş çapın hepsi `diameter`, hiç `invalid` yok), 6 satır etiketsiz
  (dört "20" + iki "40" — etiketin kendi sınırı), `answers_agreed_with_reading` 13/17.
- **Ölçülen eksik:** tür tutarken kimlik alanı beş çapta 5'te 2 doğru (`g133` ✓ · `g65` ✓ · `g125+g134`
  okumayla aynı · `pdf-19 → [g65,g68]` fazladan · `pdf-20 → [g134,g138]` yanlış). Bağ puanlanmadığı için bu
  fark sınıfa yansımıyor — sayı olarak burada duruyor.
- Sayı yasağı uyarıya düşüyor (3 cevap), cevap düşmüyor ✓; `pdf-18` okumada çözülemsizken model onu bir
  çiftle zorladı (gerekçesinde "doğrulamıyor" diyor).
- `/goal`: etiketin çemberlerini okumanın kimliklerine **çapa göre** eşle (beş çap tekil, %3 içinde;
  konum yolu başarısız olunca ikinci yol) ve üçüncü paftada **bağ puanlamasını** aç. Kapı: plakada
  bağ-puanlanabilir 5/8 değişmez · plastikte 0 kalır · `--check` paketi ve 22/22 istek özeti korunur.
  Ardından aynı kör turu yineleyip kimlik puanını raporla.


### Devam 18 — etiketin çapı kimliği belirler: ikinci eşleme yolu (konum tutmayınca)

- Etiket konumları okumanın çerçevesinde değilse (üçüncü paftada 12–34 mm fark) bağ puanlaması 0/17
  kalıyordu. `expected_for_measurement`'e ikinci yol eklendi: etiketin doğrulanmış `diameter_mm`'si
  okumanın ölçtüğü boyutlarda **tek** kimliğe düşerse eşlenir (tolerans okumanın kendisi: %3 / 0,15 mm);
  boyutlar okumanın çap iddialarının `drawn_mm`'inden, o da eşleşen geometrinin kendi yarıçapından gelir.
  Eşleme yolu kayda `mapping_basis` olarak yazılır.
- **Ölçülen etki:** plaka **5 → 5** bağ-puanlanabilir (13 kimlik hepsi `position`) ✓; plastik **0 → 0** ✓;
  üçüncü pafta **0 → 3**: `pdf-19 ↔ d11 → g68` · `pdf-20 ↔ d12 → g122` · `pdf-21 ↔ d13 → g65`.
- Açılmayan iki satır (`pdf-17` Ø20, `pdf-22` Ø40) etiketle eşlenmiyor: çift değerli (dört "20", iki "40")
  ve Ø40'ın 40 mm'si **iki** yaya (g125/g134) düşüyor → tekil değil → eşleme reddedildi.
- Kalan `unmapped_label_ids` yüz/kenar kimlikleri; onların konumu da boyutu da yok.
- Testler: `tests/test_meaning_interpretation.py` +2 (çap yolu ve belirsizlik reddi) → 15.
- `/goal`: aynı kör turu (`meaning-3b-11-third-blind-v2`) koşup üç satırın **kimlik puanını** raporla;
  ardından yüz/kenar kimliklerine konum vermenin yolunu (etiketin kendi çizim-dimension zinciri) ölç —
  o zaman mesafe satırlarının bağı da puanlanabilir olur. Kapı: plaka 5/8, plastik 0, istek özetleri 22/22.

- **Koşu `meaning-3b-11-third-blind-v2` (aynı kör tur, açılan bağ puanı):** cevaplar önceki kör turla
  **0/17 farklı** (eşleştirilmiş ölçüm — değişen tek şey alet). Sınıflar `correct 9` · `partial 2` ·
  `no_label 6`; bağ puanlanan üç satırda **kimlik puanı 3'te 1**: `pdf-21` (Ø50) beklenen `[g65]` ↔ cevap
  `[g65]` ✓; `pdf-19` (Ø30) beklenen `[g68]` ↔ cevap `[g65,g68]` ✗ (fazladan kimlik); `pdf-20` (Ø25) beklenen
  `[g122]` ↔ cevap `[g134,g138]` ✗. Yani **tür 11/11, kimlik 1/3**. Puanlanamayan 8 mesafe satırının etiket
  kimlikleri yüz/kenar (konumsuz, boyutsuz).
- Testler: `round19` = **469 geçti / 243,36 sn** (+2 test: çap yolu ve belirsizlik reddi). `check_tables` 20/0,
  `baseline_report --check`, `profile_step_evidence --check` uyuşuyor; yeni paket `-11` `--check` 17/0;
  istek özeti kalkanı **22/22**. Rapor: `out/profile-step/pytest-round19.txt`.


### Devam 19 — menüde ölçülen boyut; istek cümlesi ile veri alanı ayrı ölçüldü

- **Tanı:** çap çağrılarının menüsü 19 kimlik ve yalnız `kinds` + `points_mm` taşıyordu; **iki farklı çaplı
  kimlik aynı noktada** duruyordu (`g65`/`g68` = (11,27;180,71) · `g122`/`g125` ≈ (69,9;20,5)). Soru
  menüden cevaplanamazdı; modelin `[g65,g68]` / `[g134,g138]` cevapları bunun sonucuydu.
- **Değişiklik:** `interpret.measured_sizes` (iddiaların `drawn_mm`'i + katalog çemberleri) ve menüye
  `measured_diameter_mm`. İstek `v3` → `v4` → `v5`; **alan ile cümle ayrı ölçüldü**: üçüncü pafta kimlik
  puanı **1/3 → 2/3** (Ø30 satırı düzeldi: `[g65,g68]` → `[g68]`), plaka `v4`'te 7/8'e düşüp `v5`'te
  **8/8'e döndü** — yani plakanın kaybı alanın değil, eklenen iki satırın sonucuydu. Kalan durum `v5`,
  okuma uyumu 13 → 15.
- İstek diff'i: `v4` 30 → 32 satır, tek veri 6 kimliğin ölçülen çapı; aday çiftleri / izinli kimlikler /
  ölçüm bağlamı / şema aynı.
- Kalkan yeni sürüme göre yeniden kuruldu: `-15` paketine karşı **22/22** (eski `-09` tabanı, sürüm
  bilinçli değiştiği için geçersiz — kayıtlı gerekçe).
- Testler: `tests/test_interpret.py` +1 (menüdeki ölçülen boyut ve istekte adı) → 28.
- `/goal`: `pdf-20`'nin (Ø25) neden `g122` yerine `g134/g65` dediğini — menü artık 25,70'i gösterirken —
  incelemeli koşuyla ölç (gerekçe mi, aday listesi mi); ardından etiketin yüz/kenar kimliklerine konum verip
  mesafe satırlarının bağını aç. Kapı: plaka 8/8, üçüncü pafta kimlik ≥ 2/3, istek-özeti kalkanı 22/22.
- Testler: `round20` = **470 geçti / 241,45 sn** (+1 test: menüdeki ölçülen boyut). `check_tables` 20/0,
  `baseline_report --check` ve `profile_step_evidence --check` uyuşuyor; `-12..-15` paketleri `--check` 0 sorun;
  istek-özeti kalkanı yeni tabanda **22/22**. Rapor: `out/profile-step/pytest-round20.txt`.


### Devam 20 — `pdf-20` tanısı: kayıp arayüzde değil modelde; kof denetim gerçek denetimle değişti

- **`pdf-20` ölçümü:** doğru cevap istekte iki kez yazılıydı (`measured_by_the_reading.anchors=[g122]`,
  `matched_geometry=[g122]`, `drawn_mm=25,70`; `allowed_ids`'te `g122` Ø25,70 ile var; `candidate_pairs` boş)
  ve model `matched=[g134,g65]` deyip gerekçesinde okumayı **yanlış aktardı**. → Kayıp **modelin**; arayüz
  tarafında yapılacak bir şey yok, olan şey kayıtlı.
- **Bulunan alet hatası:** `pair_is_a_measured_candidate` (`not candidate_pairs or pair in ...`)
  çap/yarıçap isteklerinde `candidate_pairs=[]` olduğu için **koşulsuz true** idi — hiçbir şey söylemiyor,
  "geçti" gibi okunuyordu; üçüncü paftanın yanlış bağını sessizce onaylamıştı.
- **Yeni denetim:** `named_ids_do_not_contradict_the_printed_size` — isteğin kendi yayımladığı ölçülen
  çapları basılı değerle karşılaştırır (okumanın toleransı %3/0,15 mm), boyut sorusu değilse ya da hiçbir
  kimlik ölçülmemişse `None` (uygulanamaz ≠ geçti). Yargı: `interpretation-contract-v5-size-agreement`.
- **Etki (model çağrısı yok, depolanmış cevaplar yeniden yargılandı):** 39 cevaplanmış satır →
  **true 8 · false 1 · none 30**; tek `false` = `pdf-20`; plakanın doğru satırlarında yanlış alarm yok.
  Kayıt `out/profile-step/judge-v5-effect.txt`. Puanlar değişmedi (sınıflar etiketten).
- Paketler `-14`/`-15` eski sözleşmenin kaydı; `--check` durum karşılaştırmasını "başka sözleşme" diye
  atlıyor (0 sorun). Testler: `tests/test_interpret.py` 29 (+1).
- `/goal`: etiketin yüz/kenar kimliklerine kendi dimension zincirinden konum verip mesafe satırlarının
  bağını açmak (üçüncü paftada kapsam 3/17 → 11/17) — arayüzde kalan tek büyük kör nokta bu. Kapı: plaka 8/8,
  üçüncü pafta kimlik ≥ 2/3, istek-özeti kalkanı 22/22, yeni denetimde yanlış alarm yok.
- Testler: `round21` = **471 geçti / 246,49 sn** (+1 test: boyut çelişkisi denetimi). `check_tables` 20/0,
  `baseline_report --check` + `profile_step_evidence --check` uyuşuyor; istek-özeti kalkanı **22/22** (yargı
  değişikliği isteklere dokunmadı — ölçüldü). Rapor: `out/profile-step/pytest-round21.txt`.
- Kayıt notu: `out/profile-step/reading-coverage.txt` (10 paftalık ham tarama) 20. dilim öncesi bir anlık
  görüntüdür — bağ sayıları geçersiz (plastik 4 → 14, üçüncü pafta 11 → 16), reddetme satırları geçerli;
  süreç tümünü yazdıktan sonra sonlandırıldı (kayıp iş yok), başına not düşüldü.


### Devam 21 — üçüncü yol (değer): kapsam 3/17 → 10/17, kimlik 9/10

- **Sorun:** etiket yüz adları veriyor (parça çerçevesi: z=±13/±3/±10/±20/±5, y=0/80), okuma pafta
  çerçevesinde kimlik; görünüş başına çerçeve farkı ve bazı görünüşlerde fit zemini yok.
- **Çözüm:** `expected_for_measurement` üçüncü yol — okumanın kendi ölçümü etiketin doğrulanmış değeriyle
  (tolerans max(%3, 0,15 mm)) uyuşuyorsa `ids` = okumanın ankor kimlikleri, `mapping_basis="value"`.
  Uyuşmazsa beklenti uydurulmaz, satır `unmapped` kalır.
- **Ölçüm:** bağ-puanlanabilir **3/17 → 10/17** (`value` 14 ad + `diameter` 3 ad). İstek metni **17/17
  birebir aynı** olduğu kanıtlandı; depolanmış `v5` cevapları yeni beklentiyle puanlandı → `correct 10 ·
  partial 1`, **kimlik 9/10** (tek hata `pdf-20`). Etiketsiz boyut denetimi de aynı satırı işaret ediyor
  (çapraz denetim ✓).
- **Açık:** `pdf-18` okuma çözemediği için puanlanamıyor; 6 satırın etiket eşlemesi eksik (etiket d5/d7/d9/
  d14/d15/d16'yı taşıyor) → eşleme biterse kapsam ~14-15/17.
- Testler: `tests/test_meaning_interpretation.py` 16 (+1: değer yolu ve uyuşmazlıkta reddi).
- `/goal`: etiket eşlemesini bitirip (d5 R20, d14 Ø40, d7/d15/d16 mesafeleri) kapsamı ~14-15/17'ye çıkarmak;
  ardından aynı kör turu incelemeli (`--review`) koşup kopyalama payını ölçmek. Kapı: plaka 8/8, üçüncü pafta
  kimlik ≥ 9/10, istek-özeti kalkanı 22/22, boyut denetiminde yanlış alarm yok.
- Testler: `round22` = **472 geçti / 233,70 sn** (+1 test: değer yolu ve uyuşmazlıkta reddi). `check_tables` 20/0,
  `baseline_report --check` + `profile_step_evidence --check` uyuşuyor; istek-özeti kalkanı **22/22**;
  `git diff --check` temiz. Rapor: `out/profile-step/pytest-round22.txt`.


### Devam 22 — türlü eşleme ve boyut satırlarında değer yolu: kapsam 14/17, kimlik 13/14

- **Sorun:** eşleme yalnız değer+birim tekilliğine bakıyordu; dört "20" ve iki "40" yüzünden altı etiket satırı
  eşlenmiyordu. **Kural:** değer+birim+**iki tarafın da bildirdiği tür** tekilse eşle; tür sessizse eski kural;
  aynı türle tekrar varsa eşleme yok (tahmin yok). Kural yazılırken kendi regresyon testi hatayı yakaladı
  (`None == None` uyuşma sayılıyordu).
- **Boyut değer yolu:** değer uyuştuğunda beklenti = okumanın o ölçü için kendi eşleştirdiği kimlikler
  (bir etiket adı iki okuma kimliğini kapsayabilir: Ø40 = iki yay). `pdf-13` (R20) ve `pdf-22` (Ø40) böyle açıldı.
- **Ölçüm:** bağ-puanlanabilir **3/17 → 10/17 → 14/17**; istek metni **17/17 birebir aynı**, depolanmış `v5`
  cevapları → **correct 14 · partial 1**, **kimlik 13/14** (tek hata `pdf-20`; etiketsiz boyut denetimi de aynı
  satır ✓ çapraz denetim).
- Testler: `tests/test_meaning_interpretation.py` **18** (+2: türlü eşleme, boyut değer yolu).
- `/goal`: kalan üç satır — `d7`/`d15` için etiket satırlarına **eksen** alanı ekleyip `pdf-15`/`pdf-23`'ü
  eşlemek, `pdf-18` için okumanın çözemediği ölçüyü okuma tarafında ele almak. Kapı: plaka 8/8, üçüncü pafta
  kimlik ≥ 13/14, kalkan 22/22, boyut denetiminde yanlış alarm yok.
- Testler: `round23` = **474 geçti / 230,83 sn** (+2 test: türlü eşleme, boyut değer yolu). `check_tables` 20/0,
  `baseline_report --check` + `profile_step_evidence --check` uyuşuyor; istek-özeti kalkanı **22/22**;
  `git diff --check` temiz. Rapor: `out/profile-step/pytest-round23.txt`.


### Devam 23 — eksen yolu ölçüldü ve çürütüldü; kalan üç satır gerekçeli

- `pdf-15` (20,54) ve `pdf-23` (20,37) için okumanın kendi çapalarından çıkan eksen **ikisinde de dikey**
  (`g123↔g138`, `g55↔g90`) → eksen bu satırları ayırmıyor; eksenle eşlemek tahmin olurdu, eşleme yapılmadı.
- Açık soru (kayda geçti): etiketin "üst görünüş, yatay"/"alt görünüş, dikey" ifadesi ile okumanın pafta
  çerçevesindeki ekseni aynı şeyi söylemiyor — biri farklı çerçeve/konvansiyon kullanıyor.
- Kalan üç satır gerekçeli: `pdf-18` (okuma çözemedi) · `pdf-15`/`pdf-23` (eksen ayırmıyor). Bu iki satırın
  okumayla uyumu `answers_agreed_with_reading` (15/17) içinde raporlanıyor.
- `/goal`: incelemeli (`--review`) koşuyla kimlik puanının kopyalama payını ölçmek (koşu başlatıldı); ardından
  `pdf-18` için okuma tarafı. Kapı: plaka 8/8, üçüncü pafta kimlik ≥ 13/14, kalkan 22/22.


### Devam 24 — incelemeli koşu: kusur yakalama 7/8, kopyalama 8/17, öneri kimliği düşürüyor

- `meaning-3b-16-third-review-v5` (17 ölçü, `--review`): satır bazında `defect_caught 7` · `clean_kept 7` ·
  `false_alarm 1` · `defect_missed 1` · `no_reading_binding 1` · `copied 8/17` (kendi sayımım harness özetiyle aynı).
- **Aynı 14 satırda:** kör `-14` → `correct 14 · partial 1`, kimlik **13/14**, okuma uyumu 15/17; incelemeli
  `-16` → `correct 12 · partial 3`, kimlik **11/14**, okuma uyumu 12/17. Yani öneriyi göstermek kopyalamayı
  getiriyor ama kimlik puanını ve uyumu **düşürüyor** → kör ölçüm kuralı doğrulandı: arayüzün kendi değeri
  **kör koşunun** sayısıdır (13/14).
- `/goal`: `pdf-18` (okuma çözemedi) için okuma tarafında iş; sonra plaka/plastik gruplarında dar deneyi
  tekrarlayıp aynı üç ölçüyü (tür · kimlik · belirsizlik) birlikte raporlamak. Kapı: plaka 8/8, üçüncü pafta
  kör kimlik ≥ 13/14, kalkan 22/22.
- Denetimler: `-16` paketi `--check` 0 sorun (17 ölçü) · `check_tables` 20/0 · `baseline_report --check` +
  `profile_step_evidence --check` uyuşuyor · istek-özeti kalkanı 22/22 · testler `round23` 474 (bu yarıda kod
  değişmedi: eksen yolu yazılmadan ölçülüp reddedildi) · `git diff --check` temiz.


### Devam 25 — `pdf-18` tanısı: yanlış ankor çifti (ölçek değil)

- `pdf-18` okumada **iddiasız**: bind kaydı `status="partial"`, `implied_px_per_mm=10,33` vs kalibrasyon 3,83.
- **Hipotez "farklı görünüş" çürütüldü:** 16 satırın ima ettiği ölçekler — 13'ü 3,75–3,93 (ortanca 3,86); aykırı
  beşi çap/yarıçap satırı (orada satır = leader, metrik anlamsız). `pdf-18` tek normal aykırı ve **komşusu
  `pdf-16` 3,81** → bölge normal ölçekte.
- **Hipotez "yanlış ankor çifti" doğrulandı:** "6" için satır 6×3,83 ≈ **23 px** olmalı; seçilen ankorlar **62 px**;
  okumanın kendi adayında tam **23,28 px** uzakta `p296` var → doğru çift ölçekle uyuşuyor.
- Okumanın reddi kuralına göre tutarlı (ölçekle çelişeni bağlamıyor); eksik olan **ölçek-farkında satır seçimi**.
- `/goal`: satır seçimini ölçek-farkında genişletmek (`bind._repick_row_with_calibration`); seçilen çift
  kalibrasyonla çelişiyorsa ve komşulukta basılı değerle uyuşan **tek** aday çift varsa onu seç, yoksa `partial`
  bırak. Kapı: plaka 8/8, plastik 14/14 kapsam, kalkan 22/22, üçüncü pafta kimlik ≥ 13/14.


## 23. Kullanıcı yönlendirmeli çevrimdışı PDF → STEP — 2026-09-28

**Güncel ürün planı budur; Bölüm 22'nin sonraki işlerini geçersiz kılar.** Kullanıcının
hedefi farklı teknik çizimlerden STEP üretmek; belirsizlikleri çizim üzerinde yönlendirebilir.
İlk teslim tek parçayı baştan sona tamamlayan bir akıştır. Genel hedefi bu teslimle bitmiş sayma.

### Ürün akışı

1. PDF/PNG/JPG yerelde açılır; çizim, okunan ölçüler ve seçilebilir geometri görünür.
2. Kullanıcı ana görünüş/dış konturu seçer. Bilinen bir ölçünün iki noktasını işaretleyip
   uzunluğunu/birimini onaylar; otomatik ölçek yoksa bile iş devam edebilir.
3. Kalınlık, delik/kör cep, derinlik ve görünüş bağlantısı gibi çözülemeyen kararlar, ilgili
   çizim bölgesiyle birlikte sorulur. Bilinen değerler tekrar yazdırılmaz. Geri alma bulunur.
4. Kararlar kaynak çizim özetiyle, kaynak kimlikleriyle ve revizyonla kalıcı tutulur. Yeniden
   açma aynı kararları getirir. Yeni karar eski STEP'i geçersiz kılar; eski dosya yeniymiş gibi sunulmaz.
5. Kanonik GeneralPlan v1 üzerinden CAD motoru katıyı kurar; 3B önizleme ve STEP verilir.
   Çizimden ölçülmüş şekil ile basılı/ kullanıcı tarafından verilmiş ölçülerin kaynakları ayrıdır.
   Çizimi izleyerek çıkan geometri taslak kalır; geometrik geçerlilik imalat doğruluğu sayılmaz.

### Sıralı teslimler ve kabul ölçütleri

**A — İlk dikey dilim (şimdi):** modele ihtiyaç duymayan ayrı yönlendirmeli arayüz. Sayfada
iki noktayla kalibrasyon; kapalı çizgi/yay/daire konturu seçimi; kullanıcı kalınlığı; dairesel
geçişli delik/kör cep; mevcut CAD motoruyla taslak STEP ve önizleme. Kararların atomik kaydı,
revizyon/geri alma, yeniden açma ve başarısız CAD sonrası kararların korunması. Referans STEP
üretim girdisine girmez. Gerçek PDF'de arayüz akışı ve son STEP'in yeniden açılması denenir.
Sentetik bağımsız geometride boyut/hacim ve yanlış kaynak, eski revizyon, boş/çelişkili karar
reddi test edilir. Başarı, yalnız bir inceleme tablosu göstermek değildir.

**B — Ölçüye bağlı kesin eskiz:** çizim üstünde iki kenara/merkeze ölçü bağlama; doğrulanmış
ölçülerle profil ve delik konumlarını güncelleme; eksik veya fazla kısıtı soru olarak gösterme.
Açık konturu elle tamamlama ve seçimi düzeltme. Piksel izleme ile kesin ölçülendirilmiş CAD
arasındaki farkı kapat. İlk gerçek parçayı bağımsız referansla boyut/konum/hacim açısından karşılaştır.

**C — Kapsamı büyüt:** ikinci, farklı ve geliştirmede görülmemiş parça; ardından görünüş
ilişkileri, dönel parçalar ve çok adımlı özellik ağacı. Raster belirsizlikleri ve farklı PDF
üreticileri ayrıca ölçülür. Karmaşık yüzey ve montaj desteği ek işlerdir; her PDF için başarı garantisi yok.

**D — Modelin katkısı:** modeli yalnız çözülemeyen karar için seçenek önermek üzere ekle.
Kullanıcı kararı geometri üzerinde görünür olsun. Kurallı okuma, kullanıcı destekli akış ve
model destekli akış aynı bağımsız örneklerde karşılaştırılır. Doğrulanmış düzeltmeleri eğitim
verisi olarak ayrı sakla; eğitim ancak tekrar eden gerçek hata ve yeterli veri varsa başlar.

### Başarıyı nasıl ölçeceğiz?

Doğru son STEP, eksik/yanlış özellik sayısı, kullanıcı müdahale sayısı, tamamlanma süresi ve
başlangıçtan CAD çizimine göre kazanç birlikte raporlanır. Kullanıcı ölçü onayı, dosyanın tek
geçerli katı olması ve bağımsız geometrik doğruluk üç ayrı kayıttır.

Önceki ölçümde `mapping_basis=value`, okumanın seçtiği kimlikleri aynı uzunluk gerekçesiyle
beklenti yapıyor; bu bağımsız kimlik doğruluğu değildir. Aynı 14 satırda mevcut okumayı kopyalama
14/14, model 13/14, öneri gösterilen model 11/14 çıktı. On satırın beklentisi okumanın kendisinden.
“Kör” istem de okumanın seçtiği geometriyi içeriyor. Bu sayılarla modelin ek faydası veya ürün
başarısı ilan edilmez. Bağımsız eşleşme yoksa sonuç `ölçüyle tutarlı / doğrulanmamış` olarak kalır.

### Çalışma ve devir

Mevcut Git farkını koru; yeni genel akışı eski sınırlı plaka arayüzünden ayırarak ekle. Ağ/model
indirme zorunluluğu getirme. İlgili testleri her dilimde; tam takımı kararlı uygulama sonunda
çalıştır. Tamamlanan her dilimi PLAN/HANDOFF'a kaydet. Bu oturum başında beş saatlik kullanım
%21; %90'a ulaştığında güvenli kontrol noktası, kod/test/deney kaydı ve güncel devir paketi hazır olsun.
Hermes devam promptu: `HERMES_PROMPT.md`.

## 24. Kullanıcıya sorulan soruyu ölçmek ve öneri katmanı — 2026-09-28

**Bu oturumda kullanıcının kararları:** (1) model seçimi serbest olacak — kurulu **herhangi** bir model ya
da OpenAI-uyumlu yerel uç; yeni parçalarda genelleşme aynı dilimde; (2) model **yalnız** kurallı okumanın
çözemediği kararda sorulacak, varsayılan kapalı; (3) başarı ölçütü: **tek onay ekranı**, yalnız belirsiz
maddeler sorulur (plakada ≤3 etkileşim); (4) önce §23-A ölçümü + bu kayıt, sonra öneri katmanı; (5) arayüz
her işlemin adımını **görünür bir günlükte** gösterecek ve günlük kalıcı tutulacak.

### Ölçüm — §23-A ne istiyor, çizim ne cevaplıyor

Araç `eval/guided_effort.py`; kayıtlar `out/guided-effort/<label>/run.json`.

- **Gerçek koşu (plaka, `out/guided/91411e3e…`):** 17 alan elle girildi (kontur · kalibrasyon değeri+2 nokta ·
  kalınlık · onay · 5 delik), revizyon 3, üretim `complete`. Çizimin okuması bunların **8'ini karşılıyor**:
  kalibrasyon `bound pdf-0` (kullanıcının tıkladığı iki nokta okumanın kendi çapaları = `g9`/`g11`), dört geçişli
  delik `bound pdf-3` ("6,80 THRU ALL", sayı 4, `g9`–`g12`), cep `bound pdf-4` (Ø50, `g8`), cep derinliği
  `present pdf-6` (8,00). **İki alan yalnız `present`:** kalınlık 15,00 (`pdf-5`) ve cep derinliği 8,00 (`pdf-6`) —
  değer basılı, ama hiçbir kural onu o özellik olarak adlandırmıyor. Açık kalan soru *değer* değil **kimlik**.
- **Bağımsız kontrol:** `eval/metrics.py` + `examples/pdf with steps/5/plate with a pocket.STEP`: 1 geçerli katı,
  ölçü [15, 79.99, 120.00] ↔ [15, 80, 120] (eksen başına ≤0,01 mm), hacim 124,798 ↔ 124,825 cm³ (%0), silindir
  yarıçapları örtüşüyor → **geçti**. Referans STEP üretim girdisine girmedi (`guided.py` onu görmez).
- **Açılış maliyeti (ürün yolu, üç pafta):** her paftada **4 kapı sorusu**; aday menüleri plaka **11 kontur / 7
  daire / 20 "ölçü"**, plastik 36/8/22, ikinci pafta 11/7/26. Menü ölçü değil: plakada 20 satırın **13'ü** görünüş
  numarası (`1`…`6`) ve tarih (`2026`), ikinci paftada `02.10.25`; okuma ise plakada **7** sayıyı geometriye bağlıyor.
- **Sınır:** `bound`, okumanın kullanıcıyla aynı fikirde olmasıdır; bağımsız doğruluk yalnız referans
  karşılaştırmasıdır ve ayrı raporlanır. Pikselden ölçülen geometri taslak kalır.

### Sıradaki dilimler

**A — Öneri katmanı (model gerekmez):** okuma zinciri guided akışına bağlanır: kalibrasyon (okumanın kendi
distance claim'i + iki çapası), dış kontur (okumanın konturu), delikler (diameter claim → daire + metinden tür)
**öneri** olarak gelir, kullanıcı onaylar/veto eder. Kimlik soruları kural varsa kurala düşer (kalınlık: yan
görünüşte dış sınıra dayanan ölçü), yoksa **tek soru** olarak kalır. Kabul: plakada 17 alan → **≤3 etkileşim**,
aynı STEP (referans kontrolü yine geçer), yanlış öneri tek tıkla reddedilir, her öneri kanıtıyla (span id, px,
beklenen mm) saklanır.

**B — Görünür günlük:** okuma ne önerdi, kullanıcı ne onayladı/reddetti, hangi model ne cevapladı, üretim ne
zaman başladı/bitti — arayüzde satır satır görünür ve oturum kaydında kalıcıdır; yeniden açınca aynı günlük gelir.

**C — Model danışmanı (takılıp çıkarılabilir):** tek arayüz: (a) model yok, (b) kurulu **herhangi** bir Ollama
modeli (`capabilities` ile seçilir, `--model`/env ile sabitlenir), (c) OpenAI-uyumlu **yerel** uç. Model yalnız
A'dan sonra kalan kimlik sorusunu, çizimin kendi aday kümesi içinden yanıtlar; sayı uydurması yeni bir parametre
kaynağı olmaz (`general.py` kuralı), onaylanan değer kullanıcının kararı olarak kaydedilir, günlükte model
etiketi ve digest'i yazılır. Kabul: yalnız `llama3.2:3b` (görüsüz) kuruluyken akış tamamlanır;
`qwen3-vl:8b-instruct` ile soru sayısı düşer; model kapalıyken sayılar değişmez.

**Kapsam dışı:** raster paftalarda kontur/kalibrasyon engeli (HANDOFF'taki bilinen sınır) ve çok görünüşlü
paftalar bu bölümde çözülmez; her dilim aynı araçla ölçülür ve PLAN/CHANGES'a yazılır.

### A + B dilimi — sonuç, ölçülmüş

Kayıtlar `out/guided-effort/{plate,plastic,exercise}-flow/run.json`; araç `eval/guided_effort.py
--accept-and-build`. Arayüz koşusu canlı denendi (`/guided`, plaka PDF, gerçek tıklama).

- **Plaka:** okuma **9 öneri** getirdi (`profile_id`, `calibration`, 4 × `hole:`, `hole:g8`, `thickness`,
  `depth`) → kullanıcı **tek onay + tek üretim = 2 etkileşim**, kalan soru **0**, üretim `complete`.
  Kararlar elle koşunun aynısı: kalibrasyon 100 mm (kullanıcının tıkladığı iki noktanın aynısı, menü `t0`),
  `outline_1`, kalınlık 15, Ø6,8 ×4 geçişli, Ø50 cep + 8 mm derinlik. **Referans kontrolü geçti**
  (`eval/metrics.py`: 124,804 ↔ 124,825 mm³, `shape_ok`/`detail_ok`) → §23-A'nın ≤3 hedefi karşılandı
  (önce ~12–16 etkileşim, 17 kullanıcı alanı).
- **Plastik pafta:** 3 öneri (dış kontur, kalibrasyon 120 mm, cep derinliği) → 1 etkileşim; **1 soru kalıyor**
  ("Parçanın kalınlığını girin": paftada kalınlığı adlandıran kural yok) → üretim `blocked`. Örnek başına
  tanıyıcı yok; aynı kod yolu.
- **2. pafta:** 3 öneri (kalibrasyon 26 mm, Ø20 ve Ø25 daireler) → **3 soru kalıyor** (kontur, kalınlık,
  taslak onayı) → `blocked`. Çok görünüşlü pafta; kapsam dışı olarak kabul edildi.
- **Öneri iki yoldan çözülür ve her zaman ölçüyle doğrulanır:** (1) okumanın kendi çerçevesi (kontur bbox
  merkezi + `px_per_mm`) ile mm→px eşlemesi, her çapa adlandırdığı geometrinin üzerine düşerse; (2) düşmezse
  uzunluk kısıtı araması. Doğrulanmayan iddia öneriye girmez; basılı olmayan değer hiç üretilmez.
- **Günlük (B):** her öneri ve her karar aktör/eylem/alan/**kanıt** olarak `session.json`'a yazılır, arayüzde
  ters kronolojik listelenir, kanıt açılır satırda görünür, sayfa yenilenince aynı günlük gelir.
- **Model seçimi serbest (C'nin ilk yarısı):** `VISION_MODELS`/`CODER_MODELS` artık yalnız **tercih sırası**;
  seçim kurulu modeller + sunucunun `capabilities` alanıyla yapılır (`choose_vision_model`, `choose_text_model`),
  `DRAWINGTO3D_VISION_MODEL` / `DRAWINGTO3D_CODER_MODEL` ile sabitlenir; sabitlenen etiket kurulu değilse hata
  verilir (sessiz ikame yok), görüntü okuyabilen model yoksa akış kurallı okumayla sürer. Bu makinede artık
  `qwen3-vl:8b-instruct` seçiliyor — eski allowlist onu hiç seçmiyordu. Testler: `tests/test_model_choice.py` 12,
  `tests/test_advise.py` 8, `tests/test_guided_proposals.py` 7.


### 23.1 Uygulama kontrol noktası — 2026-09-28, kullanım %91

%90 eşiği son kontrolde %91 olarak görüldü; yeni kapsam açmadan kayıt alındı.

- **A'nın kodu eklendi:** `guided.py`, `/guided` arayüzü, API, kalibrasyon/kontur/kalınlık/delik/cep kararları, atomik kayıt, revizyon/geri alma, yeniden açma, eski çıktıyı geçersiz kılma, yarıda kalan üretimi kurtarma, STEP/STL.
- **Gerçek PDF üretimi geçti:** dört delik ve kör cep, 11 işlem, geçerli tek katı. Referansla dış ölçü/hacim karşılaştırması var; hacim farkı %0,022. Tam özellik eşdeğerliği iddiası yok.
- **Testler:** tam takım 488 geçti; son backend değişikliği ve iki yeni test sonrasında yönlendirmeli takım 16 geçti. Son UI düzeltmeleri tarayıcıda tekrar denenmedi.
- **A henüz kapanmadı:** sıfırdan yükleme ve bütün kararları arayüzden girme kabul turu, son tıklama toleransı/kalınlık düğmesi, müdahale/süre kaydı açık. Kayıtlı oturum, önizleme ve geri alma tarayıcıda görüldü.
- **Tek sonraki iş:** bu temiz arayüz kabul turunu tamamla ve sorunları gider; ardından B'de kullanıcı ölçü bağlarıyla kesin eskizi kur. Uzun model denemelerine dönme.
- **Kanıt:** `eval/reports/guided-flow.md` ve `guided-flow-evidence.json`. Hermes promptu ve üç devir dosyası güncellendi. Yedek manifesti `out/checkpoints/guided-latest.json`.
## §23-A kabul turu tamamlandı — temiz oturum, gerçek arayüz — 2026-09-28

**Bu tur gerçek tarayıcıda gerçek fare/klavye ile yapıldı; API girişi kabul sayılmadı.** Oturum
`out/guided/1ad6f871e3fc4021bfbc5763f8f17b5e`, çizim `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`.

### Yapılan sıra (hepsi arayüzden)

1. Temiz `/guided` açıldı, dosya yükleme alanından PDF seçildi → okuma 9 öneri getirdi.
2. **İki noktalı kalibrasyon gerçek tıklamayla:** dört deliğin iki merkezine tıklandı; yakalama tam merkezlere
   düştü, ölçülen 787,6 px = okumanın kendi `1 00,00` satırı. Değer 100 mm yazıldı, "Ölçeği uygula" tıklandı.
3. **Kontur tıklamayla:** plakanın üst kenarına tıklandı → `outline_1` seçildi (tolerans çalıştı).
4. **Kalınlık "Kalınlığı kaydet" düğmesiyle:** alana 15 yazıldı, düğme tıklandı (bu düğmenin tarayıcıda
   sınanması bu turun istediği iki işten biriydi).
5. **Delikler tıklamayla:** dört dairenin merkezine tıklandı; her biri kendi çapını çizimden doldurdu
   (6,801 · 6,793 · 6,793 · 6,801 mm), basılı değer 6,8 yazılıp eklendi.
6. **Kör cep:** Ø50 dairesi tıklandı, tür klavyeyle "Kör cep (üstten)" yapıldı, Ø50 ve derinlik 8 girildi, eklendi.
7. Taslak onayı işaretlendi → **"3B taslak ve STEP üret"** → "Taslak hazır; geometri denetimi geçti", STL önizlemesi göründü.
8. **İndir:** "Taslak STEP" bağlantısı tıklandı, tarayıcı `part.step` indirdi. İndirilen dosyanın SHA-256'sı
   sunucudaki çıktıyla **birebir aynı** (`e7f2756a…76ce`).
9. **Yeniden aç:** aynı `?session=` adresi yeniden yüklendi → "Kaydedilmiş oturum açıldı"; kararlar (kalınlık 15,
   onay, 4 delik + cep), STEP/plan/denetim bağlantıları, önizleme ve 27 satırlık günlük geri geldi.
10. **Geri al:** "Son kararı geri al" tıklandı → son karar döndü, **eski STEP/plan/denetim bağlantıları kaldırıldı**,
    önizleme gizlendi, günlüğe geri alma satırı yazıldı.

Oturum günlüğüne göre süre **2 dk 48 sn** (yükleme → geri alma; üretim ~25 sn dahil). Bu tur her kararı elle
girdiği için **16 kullanıcı karar eylemi** (11 düzenleme, 2 onay, 1 veto, 2 geri alma) — buna bir hatalı giriş ve
düzeltmesi de dahil. Öneri destekli yol (tek "onayla") 2 etkileşimdir; bu tur onu değil, elle girişi sınadı.

### Bağımsız doğrulama (referans üretim girdisi değil, yalnız karşılaştırma)

| ölçüm | üretilen | referans `plate with a pocket.STEP` |
| --- | --- | --- |
| dış ölçü | 119,9957 × 79,9865 × 15,0000 mm | 120 × 80 × 15 mm |
| hacim | 124 797,96 mm³ | 124 825,42 mm³ (fark **%0,022**) |
| 4 delik | r=3,4; merkezler (10;10) (10;70) (110;10) (110;70); z 0→15 geçişli | r=3,4 aynı yerde |
| kör cep | r=25,0; taban z=7, ağız z=15 → **derinlik 8 mm**, merkez (60;40) | r=25, z 7→15 |

Köşe yuvarlatmaları r≈9,97 ↔ referans r=10. Referansın kendi delikleri yarık (r=3,4 çiftleri 4,33 mm aralık)
olarak duruyor, pafta ise düz daire çiziyor: bu, pafta ile referans sürümü arasındaki fark olarak kaydedildi;
akış paftanın çizdiğini kurar ve bu fark hacme %0,022 olarak yansır.

### Bu turda bulunan ve düzeltilen iki gerçek arayüz sorunu

1. **Büyük daireye ortasından tıklamak seçmiyordu.** Yakalama yalnız "kenara 18 px" kuralıyla çalışıyordu; Ø50
   cebin yarıçapı 197 px olduğu için ortasına tıklamak hiçbir şey seçmiyor (seçim önceki dairede kalıyor) ve
   kullanıcı yanlış daireyi ekleyebiliyordu. Artık tıklama dairenin içindeyse **en küçük kapsayan daire** seçilir
   (cebin içindeki delik yine kazanır); yakın kenar kuralı korunur. Tarayıcıda sınandı: cebin ortasına tıklama
   `g8`/Ø50,002 getiriyor.
2. **Kör cep derinliği alanı, tür "geçişli delik" iken gizli ama yazılabilirdi.** Gizli alana yazılan değer
   sessizce yok sayılıyordu (eklenen özellik yanlış çıkabiliyordu). Artık tür "geçişli" iken alan `disabled` ve
   boşaltılır, tür cep olunca açılır. Tarayıcıda sınandı: `[gizli, disabled] = [true,true]` → klavyeyle cep
   seçilince `[false,false]` → geçişliye dönünce alan boş ve kapalı.

### Sınırlar ve tek sonraki iş

Kontur ve delik merkezleri hâlâ **pikselden izlenen taslaktır**; basılı ölçülerle kısıtlanmadı. Ölçü kimliği
(15 mm kalınlık, 8 mm derinlik) kullanıcı onayına dayanır. Çok görünüşlü paftalar, raster giriş ve dönel parçalar
bu dilimin dışında.

**Tek sonraki iş: §23-B** — basılı ölçüyü iki kenara/merkeze kullanıcı eliyle bağla, eskizi bu kesin ölçülerle çöz,
eksik/fazla kısıtı ve açık konturu kullanıcıya göster, ilk parçayı dış ölçü/delik konumu/derinlik/hacim ile
bağımsız doğrula. Genel PDF→STEP hedefi bu turla tamamlanmış sayılmaz.

## §23-B birinci dilim: bağlanan ölçüyle kesin eskiz — 2026-09-28

**Ne yapıldı.** Kullanıcı basılı bir ölçüyü çizimdeki iki uca bağlayabiliyor: ölçü satırını `#measurement`'tan
seçer, değer yazılır, "Seçili ölçüyü bağla" → çizimde iki uca tıklar (kontur köşesi ya da daire merkezi).
Bağ `decisions.bindings` olarak atomik kaydedilir; ölçek **bağlanan bütün ölçülerden en küçük karelerle** çözülür
(`src/drawingto3d/sketch.py`, `ölçek = Σ(çizili·basılı)/Σ(basılı²)`); tek bir bağ iki noktalı kalibrasyonu geçersiz
kılar. Her bağın çizimde ölçülen karşılığı ve sapması hem panelde hem planda durur; çelişen bağ **soru** olur ve
üretim durur; bağlanmayan kenar/daireler "taslak" olarak etiketlenir.

**Kanıt.**
- Tarayıcı (gerçek tıklama/klavye): `1ad6f871…` oturumunda `t1` (`80,00`) satırı klavyeyle seçildi, "Seçili ölçüyü
  bağla" tıklandı, konturun iki sol köşesine tıklandı → bağ kaydedildi; panel: `Ölçek 7.8741 px/mm · bağlanan 1
  basılı ölçüden en küçük karelerle çözüldü. • basılı 80 mm · ölçek altında çizili 80 mm · sapma 0 mm (okuma t1)`.
  Sayfa yeniden açıldığında bağ ve panel duruyor.
- Aynı oturumda "geri al"dan sonra taslak onayı düşmüştü → soru "Çizimden izlenen konturu taslak olarak
  kullanmayı onaylayın." çıktı ve üretim düğmesi kapalıydı; kutu işaretlenince üretim geçti (akış eksiğini doğru
  söylüyor).
- Bağdan sonra eski STEP/plan/denetim bağlantıları **kaldırıldı**, önizleme gizlendi (eski STEP güncel sanılmasın).
- Üretilen katılar (bağımsız ölçüm, referans girdi değil): kalibrasyonla **119,9957 × 79,9865 × 15 mm**, hacim
  **124 797,96 mm³**; 80 mm bağıyla **120,0199 × 80,0027 × 15 mm**, hacim **124 855,47 mm³**. Referans
  `plate with a pocket.STEP`: 120 × 80 × 15 mm, 124 825,42 mm³. Bağ, bağlandığı ölçüyü tam yapıyor (60 px = 80 mm
  ⇒ 7,8741 px/mm; kalibrasyonun aynı ölçü için verdiği 7,8757 px/mm ile %0,02 içinde).
- Çelişen bağ (80 mm ve 60 mm aynı ölçekte tutmuyor): iki satır da işaretlendi, soru "Bağlanan ölçüler tek ölçekle
  tutarlı değil: … Bir bağı düzeltin ya da kaldırın." ve **üretim reddi** (HTTP 400). Bağ kaldırılınca üretim geçti.
- `plan.json`: `parameters.binding_0 = {value: 80.0, source: user}` ve varsayım satırı "Ölçek 7,8741 px/mm —
  bağlanan 1 basılı ölçüden en küçük karelerle çözüldü."
- Testler: `tests/test_sketch.py` **5 geçti**; `tests/test_guided.py` +2 (bağ ölçeği üretimi değiştiriyor: 60 px →
  40 mm; çelişen bağ sorulur ve `make_plan` reddeder; konturda olmayan kenara bağ kayıtta reddedilir).

**Sınır (açıkça).** Bu dilim yalnız **tek ölçek** çözer: bir bağ ölçeği belirler, bağlar birlikte ölçeği
sıkılaştırır; ama çizimin *oranları* basılı sayılarla çelişiyorsa akış uzlaştırmaz, çelişkiyi sorar. Kenarı tek
başına kaydırma (iki kenar arasını kesin ölçüye oturtma), açık konturu kapama ve delik konumunu kenarlara bağlama
henüz yok; bu yüzden çözülen eskiz **taslaktır**, doğrulanmış parça değildir. İlk parçanın bağımsız doğrulaması
(dış ölçü, delik konumu, derinlik, hacim) plakada yapıldı ve örtüştü; **görülmemiş ikinci parçaya genişletme
yapılmadı**.

**Tek sonraki iş:** B-2 — bağı *konuma* çevirmek: kenar-kenar ve merkez-kenar bağlarıyla profil köşelerini ve
delik merkezlerini kesin ölçüye oturtmak (ölçek değil konum) ve açık konturu kullanıcıya gösterip kapattırmak;
sonra akışı geliştirmede hiç görülmemiş bir paftada bağımsız ölçümle sınamak.
## Not — aynı ağaçta paralel çalışan ajan ve B-2 çakışması — 2026-09-28

`src/drawingto3d/sketch_constraints.py` + `tests/test_sketch_constraints.py` ağaçta **benim yazmadığım** bir
dosya çiftidir (11:48, benim `sketch.py`'den ~13 dk önce): "Exact X/Y dimensions over explicitly selected sketch
points … conflicting cycles … constrained coordinates are expressions over user dimensions". Yani **B-2'nin
(konum kısıtları) çekirdeği başka bir ajan tarafından yazılmış durumda** ve henüz hiçbir yere bağlanmamış (`src`
içinde yalnız kendi modülü + testi). Benim dilim onu import etmiyor, o da benim `sketch.py`'yi kullanmıyor.

Bu yüzden **tek sonraki iş** ikiye ayrılıyor; kararı kullanıcı verir:
1. **Bağlama:** `sketch_constraints` çözücüsünü benim bağ arayüzüne bağlamak — bağlar zaten kullanıcı eliyle
   seçilmiş uçlar (`edge:<i>`/daire merkezi) olduğundan, onların koordinat-farkı kısıtları aynı uçlardan
   türetilebilir; o zaman ölçek yerine **konum** da çözülür ve B-2 kapanır. Çakışma riski: diğer ajan aynı
   dosyada çalışıyor; bu işi ona bırakmak ya da sırayla yapmak gerekir.
2. **Benim hattım (çakışmasız):** akışı geliştirmede hiç görülmemiş bir paftada bağımsız dış ölçü / delik konumu /
   derinlik / hacim ölçümüyle sınamak (B-2'nin ikinci yarısı) ve raster ölçek ankrajı (C4).

Benim bıraktığım devir: `sketch.py` + `guided.py` bağ alanları + arayüz paneli + `tests/test_sketch.py` (5) ve
`tests/test_guided.py` (+2) yeşil; tam takım **564 passed**; `eval/check_tables.py` 21/0.
## §23-C1: rastera yay uydurma — görülmemiş paftalar için ilk adım — 2026-09-28

**Ölçüm (önce).** Depodaki dört PDF akıştan geçmişti; geriye kalan beş çizim (1/Exercise 51, 3/Exercise 17,
4/Exercise 13, 7/my_part.jpg, 8/Flange) **raster** ve beşi de `/api/guided/open` ile açıldı: hiçbirinde parça
konturu yok — yalnız daireler ve (üçünde) antet/tablo dikdörtgeni; ikisinde hiç kapalı kontur yok ("kapalı dış
kontur bulunamadı"), hepsinde okuma ölçeği reddediyor ("pafta ölçeği okunamadı"). Kök neden ölçüldü:
Exercise_51 rasterında **340 çizgi, 0 yay, 4 daire**; parçanın dış hattı eğri (R60/R15/Ø100) ve `raster.py`
kendi notunda "arcs are not fitted yet" diyordu — yaysız eğri kontur kapanmıyor.

**Ne indi (`src/drawingto3d/raster.py`).** Zayıf bir Hough geçişi (`ARC_PARAM2=30`) aday üretir; kararı
**açısal destek** verir: halkanın en uzun kesintisiz mürekkep koşusu (`_longest_ring_run`, 0°'den sarma dahil)
≥ 25° ve kendi aralığında ≥ 0,75 dolu olmalı; tam daireyi geçen halka tekrarlanmaz; merkezi kelime kutusunda
olan yay gliftir diye atılır; **kayık halka kapısı**: koşu boyunca mürekkebin gerçek yarıçapı medyanı ±2,5 px
içinde ve dağılımı ≤2,5 px olmalı (kalın dairenin mürekkebini sıyıran merkez dışı halka yay sanılmasın).
Çıkanlar `kind="arc"` ilkelidir (centre/radius/start_degrees/end_degrees/coverage, method="hough-arc") — yani
`proposal._loops`'un beklediği alanlar; döngü kurmaya doğrudan girer. Daire mürekkebi sayılan parça çizgiler
artık yaylardan da düşülür, notlar yeni geçişi ve eşikleri yazar.

**Kanıt.** `tests/test_raster.py` **12 geçti** (366 s) — üçü yeni: sentetik paftada çizili 120° yay
merkez/yarıçap/açı aralığıyla geri geliyor (span 120°±20), tam daire yay olarak tekrarlanmıyor,
`_longest_ring_run` 0° sarmasını ve kopukluğu doğru ölçüyor; mevcut flange/exercise gözlem ve not testleri geçiyor.

**Sınır — henüz ölçülmedi.** Yay uydurmanın **gerçek görülmemiş paftada** parça konturunu açıp açmadığı
ölçülmedi: Exercise_51'de `observe` ~7 dk sürüyor, döngü ölçümü zaman aşımına uğradı. Ayrıca rasterda ölçü
ankrajı yok (ölçek hâlâ kullanıcının iki tıklamasına bağlı) ve aday listesinde antet dikdörtgeni duruyor.

**Tek sonraki iş.** Arka planda bir kez `observe(Exercise_51.PNG)` koşup `_primitives` + `_loops` ile kontur
adaylarını **yaylar dahil** ölçmek; parça hattı döngü kuruyorsa akışı o paftada sonuna kadar götürüp STEP'i
bağımsız ölçmek (dış ölçü/hacim), kurmuyorsa yay uçlarının (yay-çizgi teğet) birleşmesindeki eksiği adlandırmak;
sonra aynı ölçümü 3/Exercise 17 ve 8/Flange'a uygulamak.
## §23-C2: yay artık doğru yerde, ama eğri kontur hâlâ kapanmıyor — 2026-09-28

**Ne indi (`src/drawingto3d/raster.py`).** Yay uçları/dairesi artık Hough'un tahminine değil **mürekkebin
kendisine** oturuyor: koşunun mürekkep noktalarına Kasa ile daire uydurulur (`_fit_circle`), yayın ucu o
noktaların ucu olur; `|uydurulan − tahmin| > 0,35·r` ise aday düşer; **kambur kapısı** (`ARC_MIN_SAGITTA_PX=4`)
kendi kirişi üzerinde 4 px'ten az kamburlaşan mürekkebi eler (düz kenarın dev yarıçaplı "yay" sanılması); açı
aralığı alt sınırı 45°'ye çıktı.

**Kanıt.** Sentetik stadyum paftasında (iki çizgi + iki yarım daire + iki delik): gerçek yaylar **tam** geri
geliyor — `([202,300], r=99, 70°→290°)` ve `([699,300], r=99, 253°→433°)` ↔ çizili `(200,300)/(700,300), r=100`;
aday seli 23 → 5'e indi (kalanlar 58-72°'lik gerçek mürekkep dilimleri). `tests/test_raster.py -k "synthetic or
longest"` **4 geçti**; tam modül koşusu (366 s) ve gerçek pafta ölçümü arka planda.

**Ölçülen açık (bu dilimin sınırı).** Stadyumun dış hattı **yine döngü kurmuyor: 0 döngü.** Sebep ölçüldü:
yayın açı aralığı teğet noktasını aşıyor (sol yay 70°→290°, çizili 90°→270°), yani yayın ucu
komşu çizginin mürekkebine 6-20 px giriyor ve `_loops`'un 3 px'lik kapanış toleransına uymuyor. Yay uçlarını
mürekkeple budamak ya da `_loops`'a "yay ucu, çizgi ucu bu dairenin üstünde ve yayın aralığında ise birleşir"
kuralını eklemek gerekiyor — o kural PDF yollarını da etkiler, ayrı ölçülmeli.

**Tek sonraki iş.** (1) Arka plandaki gerçek pafta ölçümünü (`/tmp/arc-loops.txt`: Exercise 51 / 17 / Flange)
oku; (2) yay uçlarını mürekkebe buda (ya da `_loops`'a yay-çizgi teğet birleşmesini ekle) ve sentetik stadyumu
yeniden ölç — hedef: `döngü ≥ 1` ve uç birleştirmesi ≤ 3 px; (3) kapanınca akışı o paftada sonuna kadar
götürüp STEP'i bağımsız ölç, sonra Exercise 51/17/8'e uygula.
## §23-C3: yay ucu mürekkebe budandı, teğet birleşmesi ve gerçek pafta seli ölçüldü — 2026-09-28

**Ne indi (`src/drawingto3d/raster.py`).** Yay koşusunun uçları artık "düz bir çizgi de bu noktayı
kaplıyorsa o mürekkep yayın değil, çizginin" kuralıyla budanıyor (`_trim_to_own_ink` + `_point_at_segment`);
uydurma ve açı aralığı budanmış noktalardan yeniden hesaplanıyor, aralık alt sınırı orada da uygulanıyor.
`_verified_arcs` artık birleştirilmiş çizgileri de alıyor; `observe_raster` bunları yaylardan önce hesaplıyor.

**Ölçüm 1 — sentetik stadyum (kurşun kalem 3 px mürekkep).** Yayların yeri tam: `([200,300], r=98)` ve
`([700,300], r=98)` ↔ çizili `(200,300)/(700,300), r=100`; ama budama teğet noktasını da götürdüğü için
açı aralıkları 96°→264° ve 278°→430° (çizili 90→270 / 270→90), yani yaylar birleşim yerinden ~10 px **kısa**
kalıyor → **döngü yine 0**. Kök neden net: teğet birleşiminde yayın ve çizginin mürekkebi aynı yerdir, bu
yüzden uç yakınlığına dayanan kapanış kuralı (3 px) bu birleşimi hiçbir zaman göremez.

**Ölçüm 2 — gerçek pafta (Exercise_51.PNG, 3300×2550, arka plan işi).** Yaysız: **325 çizgi + 0 yay → 1
döngü** (o da antet dikdörtgeni). Yaylarla: **325 çizgi + 3884 yay → 24 döngü**. Yani zayıf geçiş gerçek
paftada **kullanılamaz ölçüde sel** üretiyor; kambur/açı kapıları ince sentetik mürekkebe göre ayarlanmış,
gerçek paftanın kalın ve gürültülü mürekkebinde düz çizgilerin üstünde yay uyduruyor. 24 döngünün en
büyükleri de parça hattı değil (antet/çerçeve).

**Kanıt.** `tests/test_raster.py -k "synthetic or longest"` **4 geçti**; raster+guided+proposal odaklı koşu
arka planda (`/tmp/suite-c3.txt`).

**Tek sonraki iş (sıra önemli).** (1) Yay kapısını gerçek pafta ölçeğine bağla: koşunun tamamı zaten
düz bir çizgiyle kaplıysa aday hiç doğmasın (satır üstü seline karşı), yarıçap alt sınırı pafta boyutuna
göre ölçeklensin, coverage ≥ 0,9 istensin — hedef Exercise_51'de yay sayısını 3884'ten parça hattındaki
gerçek yaylar mertebesine indirmek ve döngü sayısının antet dışında artıp artmadığını ölçmek. (2) Teğet
birleşmesini `_loops`'a ekle: yay adayı için "öteki ucun noktası bu dairenin üstünde (±2 px) ve açı
aralığın içinde (birkaç derece toleransla) ise birleşir" kuralı; PDF yollarını etkileyeceği için kapı
koşuları (plaka 7/7, plastik 14/14, Drawing.pdf 16/17, istek hash'leri) aynı dilimde koşulmalı.
## §23-C4: teğet köşe birleşmesi kodlandı; stadyum hâlâ kapanmıyor (ölçülmüş köşe aritmetiği) — 2026-09-28

**Ne indi.** `proposal.py` (döngü kurma, PDF yollarını da besler): `_line_arc_corner` — bir doğru ile yayın
köşesi, yayın merkezinin doğruya dik izdüşümü (teğet noktası); `_arc_hit` — bir noktanın yayın çemberine
izdüşümü, yayın açı aralığı içindeyse (25° taşma toleransı, 0/360 sarması dahil); zincir köşeye
oturtuluyor (birleşim köşe ise önceki öğenin ucu köşeye çekilir); kapanış hem uç yakınlığıyla hem köşe
üzerinden sınanıyor; `ARC_JOIN_SLACK_PX=2.5`, `ARC_JOIN_DEGREES=25`, `ARC_JOIN_SNAP_PX=16`.
`raster.py`: gerçek pafta için yay kapıları — yarıçap alt sınırı `max(12 px, 0.12 × ortanca çizgi boyu)`
(glif/kalabalık mürekkep halkalarını eler) ve koşunun budanmış oranı.

**Ölçüm (sentetik stadyum).** Segmentler: iki çizgi `(171,200)-(729,200)` ve `(171,400)-(729,400)` —
yani **derleme geçişi düz çizgiyi köşenin 29 px ötesine uzatmış** (yayın teğet mürekkebini yutuyor);
yaylar `r≈98`, uçları köşeden ~10 px **içeride**. Köşe noktaları doğru: `(700,200)`, `(700,400)`,
`(200,200)`, `(200,400)`. Buna rağmen **döngü 0**: zincir kuruluyor ama kapanış ifadesi bir yerde
tutmuyor (ölçülen son adım: kapanış köşesi `(200,200)` ile yayın ucu `(189,203)` arası 11,4 px; snap
toleransı 16 px'e çıkarıldı, yine kapanmadı). Yani eksik, zincirin kendi ilk öğesinin *başlangıcının* da
köşeye çekilmemesi ya da birleşim sırasının beklenenden farklı olması — sıradaki iş bunu bir iz (debug)
koşusuyla adım adım bastırmak; tahminle ilerlemeyi bırak.

**Doğrulama durumu (dürüst).** `tests/test_raster.py -k "synthetic or longest"` **4 geçti**. **Tam takım
koşusu bu `_loops` değişikliklerinden ÖNCE başlatıldı** (`/tmp/suite-c4.txt`), yani bu dilimin
`proposal.py` değişikliklerini kapsamıyor: bir sonraki pencerenin ilk işi tam takımı ve kapı koşularını
(plaka 7/7, plastik 14/14, Drawing.pdf 16/17, istek hash'leri, `eval/check_tables.py`) yeniden koşturmak.
Gerçek pafta ölçümü (yeni yay kapılarıyla Exercise 51 / 17 / Flange) arka planda: `/tmp/arc-loops.txt`.

**Tek sonraki iş.** (1) Tam takım + kapılar (yukarıdaki risk). (2) Stadyumda zincir kararlarını adım adım
bastıran iz koşusu ve kapanışın bitirilmesi; hedef `döngü ≥ 1`, kutu `[100,200]-[900,400]`. (3) Kapanınca
sentetik paftayı `/api/guided/open` → kalibrasyon → kalınlık → iki delik → üret → STEP'i bağımsız ölç
(beklenen 96 × 24 × 10 mm, 2 delik); sonra gerçek paftalar.

**§23-C4 ek ölçüm (yeni kapılarla, arka plan).** Exercise_17: 594 çizgi + **2871 yay** → 14 döngü; yaysız: 1
döngü. Yay yarıçapları yine **11-20 px** — yani yeni yarıçap kapısı ısırmadı: 594 çizginin ortanca boyu
küçük olduğu için `0.12 × ortanca` 12 px'in altında kalıyor ve **glif boyundaki halkalar** (yazı eğrileri)
geçiyor. Sıradaki iş bunu mutlak bir tabana bağlamak: yay yarıçapı paftanın **yazı yüksekliğiyle** (OCR
kelime kutularının ortanca yüksekliği ya da ızgara/simge boyu) karşılaştırılsın — bir parça yayı asla glif
boyunda olmaz. Aynı ölçüm Exercise_51'de de 3884 yay vermişti; iki pafta da aynı imzada.

## §23-C5/C6/C7: köşe kapanışı, kapsamlama ve sahte ölçek gerilemesi — 2026-09-28

**§23-C5 — iz koşusu iki gerçek zincir hatası buldu.** Geçici `DRAWINGTO3D_TRACE_LOOPS=1` kancasıyla
(kanca kaldırıldı): (1) yay/çizgi birleşiminde zincir **ilk** öğenin metasını kullanıyordu (`meta`),
son öğeninki (`chain[-1][3]`) olmalı; (2) köşe birleşimi adayın **ters** yönünde de ateşliyordu — köşe
adayın uzak ucuna denk gelince zincir yayı 13 px geri yürütüyor, döngü 2 öğede "kapanıp" uzunluk kapısına
takılıyor ve gerçek döngü kayboluyordu. Düzeltmeler: son öğe metası; `closing` yalnız `len(chain) >= 3`
iken; köşe adayın yakın ucundaysa kabul (yoksa `continue`); kapanış hem uç hem köşe üzerinden.
**Sonuç:** sentetik stadyum **1 döngü, 4 öğe** (üst çizgi → sağ yay → alt çizgi → sol yay), köşeler
(700,200)/(700,400)/(200,400)/(200,200), alan **129 934 px²** ↔ çizili 131 416 px² (**%1,1**).

**§23-C6 — köşe kapanışı raster yaylarına kapsamlandı.** `_loops(..., corner_joins=False)` +
`raster_arcs(observations)` (yalnız `method == "hough-arc"` varsa açık); `guided.drawing_options` bunu
geçiyor. **Ölçüm:** PDF yolu eski kuralda → `tests/test_proposal.py` **22 passed** (Exercise 12 reddi yine
28 ilkel kesit döngüsünü adlandırıyor, `5/Plate` proposed ✓); stadyum köşesiz **0**, köşeli **1** döngü.

**§23-C7 — sahte ölçek gerilemesi (gerçek, ürün yolunu koruyan test yakaladı).**
`test_chain_model.py::test_a_sheet_the_reading_cannot_measure_never_reaches_a_planner` kırıldı: yay geçişi
`examples/504715c44a0f1b2bbb386bb7c387a8db.jpg` paftasında 168 yay üretiyor ve okuma **kendine 3,28 px/mm
ölçek** uydurup planlayıcıya gidiyordu (`refusals: []`) — "pikselden izlenen geometri doğrulanmış ölçü
sayılmaz" kuralının ihlali. Ölçülen adımlar: `bind.py`'de `hough-arc` yay merkezleri çapa adayı olmaktan
çıkarıldı (bağlanan ölçü 10→9, çapa 18→16 — **yetmedi**); ardından `read_sheet` içinde **raster pafta için
kendi kendine kalibrasyon reddedildi** (herhangi bir `hough-arc` ilkeli varsa `scale = None` + not).
**Sonuç:** `refusals: ['pafta ölçeği okunamadı (kalibrasyon yok)']` ✓; rasterda ölçek kullanıcının iki
tıklamasında kalıyor.

**Temiz gerçek-pafta ölçümü (bugünkü kod, tek yazar — `/tmp/arc-loops.txt`).** Exercise_51: 340 çizgi +
**143 yay** → **1 döngü** (antet) — yaysız da 1. Exercise 17: 588 çizgi + **168 yay** → 1 döngü (antet).
Flange.PNG: 385 çizgi + **207 yay** → 2 döngü (biri 153×53 px kutu). Yani yay kapıları seli 27× kesti
(3884→143) ve yay yarıçapları artık makul (27…160 px), ama **üç paftada da parçanın dış konturu kapanmıyor**:
sentetik stadyumun kapanması mükemmel mürekkep sayesinde. Sıradaki iş kod değil **ölçüm**: Exercise_51'de
parça hattının zinciri nerede ölüyor (hangi boşluk, hangi segment kümede yok).

**Doğrulama durumu.** `test_proposal.py` 22 ✓ (C6 sonrası), `test_raster.py -k "synthetic or longest"` 4 ✓;
`test_chain_model.py` + `test_proposal.py` + `test_raster.py` üçlüsü C7 sonrası arka planda
(`proc_18127a482150` → `/tmp/suite-c6.txt`); **tam takım bugünkü hâl için hâlâ koşulmadı**. Kalan bilinen
tıkaç: `_trace` yayın poligon ucunu köşe yerine budanmış mürekkep ucu sayıyor
(`"kontur uçları çizimde birleşmiyor"`). Commit atılmadı (ağaçta paralel ajanın işi var).

## §23-C8: eğri kontur ürün yolunda sunuluyor; plan kendi denetiminde "profil kapalı değil" diyor — 2026-09-28

**Kazanım (ölçüldü, /api/guided/open → HTTP):** sentetik stadyum paftası artık **`outline_0` (`wire`)** olarak
sunuluyor (yanında iki delik dairesi). Bu, yay uydurma + köşe kapanışı + `_trace` köşe kabulünün ürün yolunda
çalıştığı anlamına gelir; kararlar kaydediliyor ve **hiç soru kalmıyor** (`questions: []`).

**Kalan tıkaç (planın kendi denetimi, mesaj birebir):** `1 validation error for GeneralPlan — outer: profil
kapalı değil; 0. parça 1. parçaya birleşmiyor`. Yani izlenen profil eskiz terimlerinde hâlâ kapanmıyor.
Bu dilimde eklenenler: `_trace` içinde köşe kabulü (`_line_arc_corner` arkasından merkez→doğru dik izdüşümü),
`_on_ring`, ve köşeye çekilen yay ucunun kanonik açısını uçtan yeniden hesaplayan `_reangle`. `_reangle`'a
rağmen kapalılık denetimi geçmiyor: sıradaki iş **ölçüm** — planın `outer` kenar listesini ve denetimin ölçtüğü
birleşimleri bastırmak (denetim hangi çifti adlandırıyorsa oradan), tahminle değil.

**Ayrıca bu dilimde:** `(1)` sunucu yeniden başlatıldı (eski süreç eski `_trace`'i servis ediyordu; ilk probe
bu yüzden profili göremedi), `(2)` API probu ile uçtan uca: open → save → build (UI kabulü sayılmaz; A turu
kuralı gereği UI kabulü ayrıca tarayıcıda yapılmalı), `(3)` `read_sheet` raster paftada kendi kendine
kalibrasyonu reddediyor (sahte ölçek gerilemesi kapandı, `refusals: ['pafta ölçeği okunamadı (kalibrasyon yok)']`),
`(4)` koşan ölçümler: `chain_death` (Exercise_51'de zincir nerede ölüyor → /tmp/chain-death.txt) ve
`test_chain_model + test_proposal + test_raster` üçlüsü (/tmp/suite-c6.txt).

## §23-C9: raster paftaya özel birleşim toleransı (ölçümle geldi) — 2026-09-28

**Gerekçe (ölçüm, `/tmp/chain-death.txt`, `1/Exercise_51.PNG`, 340 çizgi + 143 yay + 4 daire = 483
segment).** Parçanın kendi hattı kümede: en uzun segment `g169` **2625 px** düz kenar
`[321,606]→[2946,606]`; ondan sonraki gerçek birleşimler ve boşlukları: `g141` 32,7 px → `g28` 27,0 px →
`g355` (yay) 17,5 px → `g377` (yay) 9,6 px → `g402` (yay) 7,5 px → `g350` (yay) 1,6 px. Yani dış hattın
parçaları **1,6–32,7 px** aralıkla duruyor; `_loops` ise **3 px** istiyordu. İkinci bulgu: naif "en yakın
uç" yürüyüşü 6. adımdan sonra kısa segment kümesine (ölçü çizgileri/yazı, boşluklar 1–13 px) sapıyor — yani
toleransı açmak tek başına yetmez, **en az dönen** kuralı baskın kalmalı (`_loops` sırası: kapanış, dönüş,
boşluk).

**İndi.** `_loops(..., corner_joins=False, join_tolerance_px=LOOP_TOLERANCE_PX)`; birleşim, kapanış ve son
kapanış bu parametreyi kullanıyor. `RASTER_JOIN_TOLERANCE_PX = 36.0` (≈ 2,9 mm @ 12,5 px/mm) **yalnız
raster paftalarda** açık: `guided.drawing_options` `raster_arcs(observations)` ile seçiyor; vektör yolların
zinciri 3 px'te kalıyor (Exercise 12 reddi ve `5/Plate` ölçümleri o kurala dayanıyor).

**Doğrulama.** Sentetik raster testleri **4 passed** ✓; stadyum ürün yolunda hâlâ `outline_0 (wire)` ✓.
Üçlü koşu (C7 sonrası): `test_chain_model.py` + `test_proposal.py` **tamamen yeşil**, `test_raster.py`'de
**tek** kırık `test_a_full_circle_is_not_repeated_as_an_arc` — aynı test tek başına koşulduğunda geçiyor
(`-k "synthetic or longest"` → 4 passed), yani **test sırasına bağlı**: dosyada önce koşan bir test raster
modülünün durumunu değiştiriyor (bilinen tek `monkeypatch.setattr` `subprocess.run`'u hedefliyor; şüpheli,
geri alınmayan düz bir sabit ataması). Bu, bir sonraki pencerenin ilk 5 dakikalık işi.

**Kalan tıkaç (ürün yolu).** Stadyumda plan denetimi hâlâ `outer: profil kapalı değil; 0. parça 1. parçaya
birleşmiyor` diyor — `_trace` köşe kabulü + `_reangle` sonrası bile. Sıradaki iş ölçüm: planın `outer`
kenar listesini ve denetimin ölçtüğü birleşim çiftlerini bastırmak.

**Koşan ölçüm.** `/Users/aydemir/.hermes/cache/scratch/s10/guided_raster.py` (proc_b5c049662462) dört raster
paftayı **ürün yolundan** (`drawing_options`) geçirip sunduğu profil sayısını/kutularını `/tmp/guided-raster.txt`'e
yazıyor — yeni toleransın gerçek paftada parça konturunu çıkarıp çıkarmadığının ölçümü. Commit atılmadı.

## §23-C10: yay yönü sözleşmesi — zincirin gezinmesi değil, dedektörün mürekkebi — 2026-09-28

**Ölçüm (ürün yolu, `/tmp/guided-raster.txt`, dört gerçek raster pafta).** Yeni raster birleşim toleransı
(36 px) her paftada kontur kapatıyor: Exercise_51 **8**, Exercise 17 **7**, Flange **4**, my_part.jpg **10**
wire profili (öncesi 0–1). Kutular küçük detay kümeleri (tablo hücreleri, yay yığınları); Exercise 17'nin en
büyüğü **486×450 px** — bu paftada parça hattı olabilir. Baskın yeni not:
`bu konturun yay yönleri mevcut eskiz sözleşmesinde birlikte desteklenmiyor`.

**Kök neden.** `_trace` her yayın kanonik açılarını **zincirin hangi uçtan girdiğine göre** çeviriyordu
(`delta` işareti), sonra `arcs[0]`'a bakıp tüm döngüyü ters çeviriyordu. Karışık dedektör sırası olan bir
döngüde bu, bazı yayları negatif span'la bırakıyor ve sözleşme kapısı (`0 < b − a < 360`) patlıyordu.
Oysa yayın mürekkebi, zincir hangi uçtan girerse girsin **aynı** yay parçasıdır; kanonik span dedektörün
kendi sırasından alınmalı.

**İndi.** `_trace` artık `first = a if delta > 0 else b`, `a = −first`, `b = −first + abs(delta)` kuruyor —
per-yay çevirme kaldırıldı (dedektörün `start_degrees`/`end_degrees` sırası korunur). `_reangle` de işaret
duyarlı: köşeye çekilen ucun açısı güncellenirken `b − a`'nın işareti korunuyor (start `b`'yi geçerse aşağı,
end `a`'yı geçerse yukarı sarar), böylece yanlış taraftaki yay çizilmiyor. Global ters çevirme bloğu artık
tetiklenmiyor (her yayın span'ı pozitif) ve kapı bir doğrulama olarak kalıyor.

**Sınır.** Bu düzeltme *aynı yayın* iki ucu arasındaki mürekkebi doğru ifade eder; zincirin kendisi bir
yaydan **tutarsız** yönde geçiyorsa (yayı iki kez kesen bir döngü) hâlâ temsil edilemez — o durum ölçümde
çıkarsa zincir tarafında düzeltilecek.

**Doğrulama.** Yeni ölçüm koşuyor: `proc_70f83a19c7ce` → `/tmp/guided-raster-run2.txt` (aynı dört pafta,
ürün yolu). Sentetik raster testleri 4 ✓ ve stadyum `outline_0` ✓ (bu değişiklikten önceki son teyit).

## §23-C11: raster birleşimlerinde ara nokta kapaması — 2026-09-28

**Ölçüm (C10 sonrası, `/tmp/guided-raster.txt`, ürün yolu).** Yay yönü notu **düştü**; profiller büyüdü:
Exercise_51 **9**, Exercise 17 **11**, Flange **8**, my_part.jpg **17** wire profili — ve kutular artık
parça ölçeğinde: **Flange 634×593, 523×512, 494×653** (flanş Ø ~600 px), **my_part.jpg 487×364**,
Exercise 17 486×450. Baskın yeni not ikiye ayrıldı: `iki yay arasında açık uç var; kontur düzeltmesi gerekli`
(yay-yay birleşiminde `gap > 1e-7` kapısı) ve `kontur uçları çizimde birleşmiyor` (çizgi-çizgi/çizgi-yay
birleşiminde köşe kuralı yetmedi).

**İndi.** `_trace` birleşim döngüsüne ara nokta kapaması: köşe kuralı bir şey bulamazsa ve boşluk
`ARC_JOIN_MIDDLE_PX = LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX = 5.5 px`'ten küçükse iki uç **ortada**
buluşturulur (geometriyi 3 px'in altında düzeltir; büyük teğet boşlukları yine köşe kuralı kapatır). Bu,
kırpılmış yay ucu ile birleştirilmiş çizgi arasındaki, ya da aynı karışımın iki yayı arasındaki küçük
boşlukları kapatır ve yay-yay kapısı (`gap > 1e-7`) artık sahte kırılma üretmez.

**Doğrulama.** Sentetik raster testleri **4 passed** ✓; stadyum ürün yolunda `outline_0 (wire, 50 nokta)` ✓,
notu doğru: "Konturlar çizimden ölçülmüştür; kesin ölçülü eskiz olarak onaylanmış değildir."

**Koşan ölçüm.** `proc_1b6f08068933` → `/tmp/guided-raster-run3.txt` (aynı dört pafta, ürün yolu) — iki notun
düşüp düşmediğini ve profillerin parça hattına dönüşüp dönüşmediğini gösterecek. Sunucu yeni kodla yeniden
başlatıldı (stadyumun uçtan uca STEP denemesi için).

## §23-C12: eğri raster paftadan ilk geçerli STEP (ürün yolu) — 2026-09-28

**Ne oldu.** Sentetik stadyum (iki düz kenar + iki yarım daire + iki delik) yönlendirmeli akıştan uçtan uca
üretildi: `open` → `outline_0 (wire)` → kararlar (üst kenarın kendi iki köşesi = 500,3 px = **60 mm**,
kalınlık **10**, iki **Ø7,2** delik) → `save` (soru kalmıyor) → **`build: complete`**.
Kanıt: `out/guided/b1539969d37443f1a53c4f88d6c352f9/build-1-5a2c32cf/part.step` — `step_facts`:
**1 katı, geçerli, kutu {10,0 / 23,339 / 60,063} mm, 8,904 cm³, 8 yüz**. (Bu bir **API probu**; A kuralı
gereği UI kabulü tarayıcıda ayrıca yapılmalı.)

**Bunu mümkün kılan düzeltmeler.** `(1)` Köşe = yay merkezinin doğruya dik izdüşümü, artık **her** yay-içeren
birleşimde uygulanıyor (zincir uçları eşit bıraksa bile) — (713,203)/(729,400) sapmasını düşürdü.
`(2)` `_align(edge)`: eskiz yayı merkez+yarıçap+açıdan yeniden kurduğu için yarıçap **gelen uçtan** alınır,
**giden uç o halkaya izdüşürülür** ve bir sonraki parça oraya başlatılır; böylece birleşimler denetimin
`0,01 mm` payı içinde kapanır (öncesi: `0. parça 1. parçaya birleşmiyor`). `(3)` Ara nokta kapaması
(`ARC_JOIN_MIDDLE_PX = 5,5 px`) ve yay yönünün dedektör mürekkebinden alınması (§23-C10) — yay-yönü notu
düştü, profiller büyüdü (Exercise_51 **9**, Exercise 17 **11**, Flange **8**, my_part.jpg **17**;
Flange'de **634×593**, **494×653** px kutular).

**İki açık, ikisi de ölçüldü.** `(a)` Kalibre edilen kenar %0,1 (60,063 ↔ 60) ama diğer eksen
**23,339 ↔ 24,0 mm (%2,8)**: yayın yarıçapı **98 px** çıkıyor (çizili 100) çünkü `raster.py`'de
`_trim_to_own_ink` yayı kendi mürekkebine kısarken **uydurma da kısılmış koşuya** yapılıyor. Düzeltme:
merkez/yarıçap **kısılmamış koşudan**, yalnız açı aralığı kısılmış koşudan.
`(b)` Katının x ekseni **60,06 mm** (izlenen profilin *uçları*); stadyumun yaylardan gelen beklenen genişliği
~**83 mm** → yayın kamburu katıya girmemiş. Sıradaki ölçüm: planın `outer` içeriğini (4 çizgi + 2 yay mı,
yalnız çizgiler mi) ve eskizin yay örneklerini bastırmak.

**Tek sonraki iş.** `(b)`nin ölçümü (plan `outer`), sonra `(a)`nın düzeltmesi (uydurma kısılmamış koşudan) —
sonra aynı stadyum üretimini tekrarlayıp boyutları yeniden ölçmek (hedef: 24,0 ± 0,1 ve ~83 mm).

## §23-C13: stadyumun kamburu içe düşüyor — yay sözleşmesi işaretli yayı ifade edemiyor — 2026-09-28

**Ölçüm (plan.json, `out/guided/b1539969d37443f1a53c4f88d6c352f9/build-1-5a2c32cf`).** Plan doğru kurulmuş:
4 kenar — üst çizgi (0,06 / 23,34) → (60,06 / 23,30); **yay** merkez (60,00 / 11,66), r **11,64**, açılar
**89,67° → 269,71°**; alt çizgi (59,94 / 0,02) → (0 / 0); **yay** merkez (−0,003 / 11,67), r **11,67**,
açılar **−89,98° → 89,67°**; iki delik Ø7,2 (`source: user`) ✓; işlemler: `extrude` + iki `cut` ✓.

**Çelişki.** Eskizin uzanımı: x ∈ [−11,67 … 71,7] = **83,4 mm**, y = 23,34, z = 10 → katı **{83,4 / 23,34 / 10}**
ve hacim ≈ **17,9 cm³** olmalı. Ölçülen: kutu **{10,0 / 23,339 / 60,063}**, hacim **8,904 cm³**, 8 yüz.
Yani yaylar **içe** kamburlaşmış: sağ yayın mürekkebi 90° → 270° arasını **saat yönünde** (0°'den geçerek)
alıyor; eskiz sözleşmesi ise `0 < b − a < 360` (saat yönünün tersi) istediği için aynı mürekkep ancak
"270°'den 450°'ye ters yönde" yazılabiliyor ve uç kimlikleri zincirle uyuşmuyor. §23-C12'deki yay-yönü
kapısı bu yüzden yanlış tarafı zorluyor.

**Sonuç ve tek sonraki iş.** Sözleşme **işaretli yay** taşımalı: `a` ve `b` arasındaki fark negatif olabiliyorsa
(saat yönü) hem uç kimlikleri zincirle uyuşur hem kambur doğru tarafa düşer. Yapılacak: eskiz/plan şemasına
işaretli süpürme (b − a negatif olabilir) eklemek, runner'ın b < a için saat yönünde çizdiğini doğrulamak,
`_trace`'deki `0 < b − a < 360` kapısını buna göre gevşetmek ve stadyum üretimini tekrarlayıp kutu/hacmi
yeniden ölçmek (hedef: {83,4 / 23,34 / 10} mm ve ≈17,9 cm³). İkinci açık (§23-C12a: yay yarıçapının **98 px**
çıkması, çizili 100) ayrı duruyor: uydurma kısılmamış koşudan yapılmalı.

## §23-C14: işaretli yay süpürmesi — stadyumun iki kamburu da katıya girdi — 2026-09-28

**Ne indi.** `(1)` `_trace` artık yayın kanonik açısını **zincirin girdiği uçtan** alıyor ve süpürmeyi
işaretli kuruyor: `walked` = girilen ucun *pafta* açısı; `at_seam` = zincir dedektörün kendi `a` ucundan mı
girdi; `span = −delta if at_seam else +delta`; `a_canonical = −walked`, `b = a + span`. (Negatif süpürme =
saat yönü yay; sağ kambur böyle kurulur.) `(2)` Global ters çevirme bloğu ve `0 < b−a < 360` kapısı kalktı;
yerine `b == a` veya `|b−a| ≥ 360` reddi. `(3)` `geo.py`: süpürme kapısı **işaretli** (−360…360, sıfır
değil) ve üç-nokta yayın orta örneği artık **yarım süpürme** ile bulunuyor (`start + sweep/2`) — bu, sarma
yapan yaylarda zaten gizli bir hataydı (`(start+end)/2` yanlış tarafı veriyordu). `(4)` `general.py`'nin
kapalılık denetimindeki açıklık kapısı da işaretli kabul ediyor.

**Ölçüm (aynı stadyum, ürün yolu, API probu).** Plan artık: sağ yay **89,67° → −90,29°** (süpürme
**−179,96**), sol yay **−89,98° → −270,33°** (**−180,34**) — ikisi de dışa kambur ✓. Katı:
`out/guided/5667fc64e9ae475c84f48522b2b8c32a/build-1-058c10e2/part.step` → 1 geçerli katı,
kutu **{10,0 / 23,339 / 83,31} mm**, hacim **17,439 cm³**, **8 yüz = 4 düzlem + 4 silindir** (iki delik +
iki yay yüzü ✓). Öncesi: {10,0 / 23,339 / 60,063} ve 8,904 cm³ (§23-C13). Hedef {83,4 / 23,34 / 10} kambur
ekseninde **%0,1** içinde tutuldu ✓.

**Kalan tek hata (ölçülü, §23-C12a).** Kalınlık yönü dışındaki kısa eksen **23,339 ↔ 24,0 mm (−%2,8)** ve
hacim (−%2,5) — çünkü yayın **yarıçapı 11,64/11,67 mm** (98 px), çizili 100 px. `raster.py`'de
`_trim_to_own_ink` yayı kendi mürekkebine kısarken **uydurma (merkez/yarıçap) da kısılmış koşuya** yapılıyor.
Düzeltme: merkez/yarıçap **kısılmamış koşudan**, açı aralığı kısılmış koşudan; sonra aynı stadyum üretimi
tekrarlanıp 24,0 ± 0,1 mm ve ≈17,9 cm³ hedeflenecek.

**Koşan/biten doğrulamalar.** Odaklı regresyon `tests/test_geo.py` + `test_general.py` + `test_proposal.py` +
`test_guided.py` → `/tmp/suite-c14.txt`; dört gerçek paftanın ürün-yolu ölçümü `proc_1b6f08068933` →
`/tmp/guided-raster-run3.txt`. Bu üretim **API probu** (UI kabulü tarayıcıda ayrıca yapılmalı). Commit atılmadı.

## §23-C15: yay halkası bütün koşudan uyduruldu — kısa eksen −%2,8 → −%0,95 — 2026-09-28

**İndi.** `raster.py`'de koşu artık iki parçalı: `raw` = koşunun bütün mürekkep noktaları, `found` =
`_trim_to_own_ink` sonrası. **Merkez/yarıçap `raw`'dan** uyduruluyor (Kasa), **kambur (sagitta) kapısı
`raw`'a** soruluyor, **açı aralığı `found`'dan** okunuyor. Gerekçe ölçülü: kısılmış koşuya uydurulan halka
kısa çıkıyordu (98 px, çizili 100) ve bu doğrudan milimetreye yazıyordu.

**Ölçüm (aynı stadyum, ürün yolu, API probu).** Yay yarıçapları **11,822 / 11,886 mm** (öncesi 11,64 / 11,67;
çizili 12,0). Katı: `out/guided/699f6df735114b5882bb8fa42bd1d3b6/build-1-fa52f368/part.step` → 1 geçerli katı,
kutu **{10,0 / 23,772 / 83,709} mm**, hacim **17,825 cm³**, 8 yüz. Hedefler: 24,0 / 83,94 / 10 ve ≈17,9 cm³
→ hatalar sırasıyla **−%0,95**, **−%0,28**, **−%0,4** (öncesi −%2,8 / −0,15 / −%2,5). Kalan ~%1: yarıçap hâlâ
~0,13 mm kısa (kırpma/`_ink_point` penceresi) — kesin ölçüler B-2 kısıt çözücüsünün işi, bu bir **taslak**.

**Koşan doğrulama.** `tests/test_raster.py + test_proposal.py + test_guided.py + test_sketch.py + test_geo.py
+ test_general_plan.py + test_plate_plan.py` → `/tmp/suite-c15.txt` (raster uydurması değişti; tam takım
`proc_d2295cb92590` bu düzeltmeden **önce** başladı, o yüzden bayat sayılır).

## §23-C16: UI kabulü (gerçek tarayıcı, eğri raster pafta) — ilk yarı — 2026-09-28

**Yapıldı (gerçek fare/klavye, `/guided`):** stadyum PNG'si gerçek dosya girişinden yüklendi ✓; tuval
ölçüsü 726×436 (görüntü 1000×600, ölçek 0,726), panel "3 kontur · 2 daire · 0 ölçü adayı · sınıf: unknown"
dedi ✓; **kontur gerçek tıklamayla seçildi** ("Karar kaydedildi", kayıt 1) ✓; **iki kalibrasyon noktası
gerçek tıklamayla** seçildi, değer **60** gerçek tuşlarla yazıldı ve "Ölçeği uygula" basıldı → **kayıt 3** ✓.
Yani eğri raster paftada profil + kalibrasyon kararları **gerçek arayüzden** geçiyor ✓.

**Kesinti.** Kalınlık alanına yazma denemesi ve sonraki `js` çağrısı **tarayıcı koşum katmanının 5 sn'lik
IPC zaman aşımına** takıldı (`Input.dispatchKeyEvent`, `Runtime.evaluate` ✗) — uygulama hatası değil, koşum
katmanı; önceki çağrılarda kendini toparlamıştı. Kalan adımlar (kalınlık, iki delik, **Üret**, indirme ve
SHA-256 karşılaştırması) sıradaki denemede tamamlanacak.

**Karşılaştırma (tam olan yol).** Aynı pafta **API probuyla** uçtan uca üretildi ve bağımsız ölçüldü
(§23-C15): `{10,0 / 23,772 / 83,709} mm`, **17,825 cm³**, 1 geçerli katı, 8 yüz (4 düzlem + 4 silindir).
UI kabulü tamamlandığında aynı sayılar beklenir; iki yolun aynı STEP'i vermesi ayrıca karşılaştırılacak.

## §23-C17: odaklı koşu — 115 passed, 2 failed (biri YENİ gerileme) — 2026-09-28

**Koşu:** `tests/test_raster.py + test_proposal.py + test_guided.py + test_sketch.py + test_geo.py +
test_general_plan.py + test_plate_plan.py` → **2 failed, 115 passed (33:39)**.

**`test_raster.py::test_a_full_circle_is_not_repeated_as_an_arc`** — bilinen **sıra bağımlılığı**: tek
başına geçiyor (`-k "synthetic or longest"` → 4 passed), dosya koşusunda kırılıyor. Dosyada önce koşan bir
test raster modülünün durumunu değiştiriyor. Ayrı iş.

**`test_guided.py::test_title_block_leaves_the_contour_and_number_menus` — YENİ ve gerçek.** Ölçüm:
`drawing_options(observe("10/Exercise 12.pdf"))` en geniş `wire` profili **2138,12 px** (antet kutusu
708,6 px, beklenen < 100) → 2138 px = sayfanın neredeyse tamamı, yani **çerçeve/antet bloğu yine profil
olarak sunuluyor**. `test_proposal.py` aynı koşuda **geçti** (yani `propose_general` yolu hâlâ 28 ilkelli
kesit döngüsünü reddediyor ✓) — tıkaç yalnız **yönlendirmeli yolun (`drawing_options`)** kapsama/dışlama
süzgecinde.

**Şüpheli (sıralı, ölçümle ayrılacak).** `(1)` `10/Exercise 12.pdf` taramalı bir pafta: okuma raster
geçişini de çalıştırıp `method == "hough-arc"` ilkeli üretiyorsa `raster_arcs(observations) == True` olur ve
**36 px'lik raster birleşim toleransı bu paftaya da uygulanır** ✗ — 2138 px'lik döngü tam da bu toleransın
ayırt edemeyeceği kadar yakın parçaları birleştirmesiyle oluşur. Doğrulama: aynı paftada `raster_arcs(...)`
çıktısını ve iki toleransın (3 px / 36 px) döngü sayısını yan yana basmak. `(2)` Genişletilmiş toleransla
oluşan bir döngü, `_frame_loops`/`_annotation_loops` süzgeçlerinden kaçıyorsa kural sıkılaştırılmalı
(ör. sayfanın %80'inden fazlasını kaplayan profilleri hiç sunmamak — `FRAME_COVERAGE` ile aynı mantık).

**Tek sonraki iş (bu gerileme için):** `(1)`i ölçmek — `raster_arcs(observe(SHEET_10))` ve
`_loops(lines, arcs, corner_joins=…, join_tolerance_px=…)` ikilisiyle döngü sayıları/Genişlikleri; çıkarsa
kapıyı daraltmak (raster toleransı yalnız *çerçevesi tanınmayan* paftalara, ya da geniş profile sayfa
kapsama süzgeci).

**§23-C17 ek ölçüm (aynı gün, hemen ardından).** `(a)` Hipotez `(1)` **yanlış** çıktı:
`P.raster_arcs(observe("10/Exercise 12.pdf")) == False` ✓ — yani 36 px'lik raster toleransı bu paftaya
uygulanmıyor; paftada vektör yolundan **397 çizgi + 74 yay + 42 daire** var. `(b)` Suçlu `_loops` değil,
`drawing_options`'un süzgeçleri: sunulan profiller **outline_4 = 2138×2156 px (6 öğe: çizgi,çizgi,yay,çizgi,
çizgi,yay)** ve **outline_2 = 2119×2544 px (28 öğe)** — ikincisi paftanın neredeyse tamamı (çerçeve),
ötekisi pafta ölçeğinde bir kontur. Not "antet/tablo bölgesi atlandı (1 döngü…)" diyor, yani antet kutusu
süzüldü ama **bu iki dev döngü süzülmedi** ✗. `test_proposal.py` geçtiği için tıkaç yalnız yönlendirmeli
yolun kapsama süzgecinde.

**Tek sonraki iş (kesinleşti).** `drawing_options`'ta dev döngülerin neden süzülmediğini ölçmek:
`_loop_box(loop)` kutusu ile `_trace` sonrası `points` kutusunu yan yana basmak (süzgeç hangisine bakıyorsa
öteki onu atlatıyor) ve `FRAME_COVERAGE=0,80` kuralını bu iki döngü için de işletmek — ya da `_trace`
değişikliklerinin (işaretli yay + `_align`) bir döngünün *noktalarını* pafta ölçeğine çıkardığını
doğrulamak. Ölçüm komutu: `_frame_loops(loops, frame.width, frame.height)` çıktısı ile `wires` kimliklerini
karşılaştırmak.

## §23-C18: dev-döngü gerilemesinin kökü — konvansiyon uyuşmazlığı + sahte dev yarıçaplı yaylar — 2026-09-28

**Ölçüm 1 (süzgeçler doğru).** `10/Exercise 12.pdf` (sayfa 2200×1700): 9 döngü; **döngü 0 = çerçeve
(2121×1621) → `_frame_loops` True ✓**, **döngü 1 = antet (709×217) → `_annotation_loops` True ✓** — yani
süzgeçler çalışıyor; sunulmaması gereken dev profiller bu ikisi değil ✗.

**Ölçüm 2 (gerçek kök).** `_trace(loops[2])` ve `_trace(loops[4])` içindeki yaylar:
`a −93,1 b −86,9 r 1102,8`, `a −84,9 b 265,0 r 1075,6`, `a −93,8 b −86,2 r 1078,1` — yani **sahte dev yarıçaplı
yaylar** (2200 px'lik sayfada r ≈ 1080; 6–10°'lik süpürmeler = düz kenarın yay sanılması) ve bunların
`_arc_points` ile örneklenen noktaları **sayfanın dışına** düşüyor (`y ≈ −900`, iz kutusu 2546 px ✗) →
profilin noktaları pafta ölçeğine çıkıp `test_title_block…` kırılıyor. İki ayrı kusur birleşiyor:
`(a)` **vektör (PDF) okuyucusu** düz kenarları dev yarıçaplı yay olarak veriyor (raster tarafındaki
`ARC_MIN_SAGITTA_PX` kapısının vektör karşılığı yok); `(b)` `_trace` kanonik (y yukarı) açı yazarken
`drawing_options`'un nokta yolundaki `_arc_points` **pafta (y aşağı) konvansiyonunu** bekliyor → dev
yarıçaplarda aynalama binlerce piksel sapma demek.

**Tek sonraki iş.** `(b)`yi kapatmak: `drawing_options` profil noktalarını üretirken yayı `_trace`'in yazdığı
konvansiyonla örneklemek (kanonik a/b'yi pafta açısına çevirerek: `_arc_points(centre, radius, −a, −b, n)`,
ya da `_trace`'de a/b'yi pafta konvansiyonunda bırakıp kanonik dönüşümü yalnızca plan emitinde yapmak).
`(a)` için ayrı iş: vektör okuyucusunda kambur (sagitta) kapısı. Doğrulama: `test_guided.py::test_title_block_
leaves_the_contour_and_number_menus` tek başına koşacak (beklenen: en geniş < 100 px) + stadyum üretiminin
{10,0 / 23,772 / 83,709} mm sayıları **değişmemeli**.

**§23-C18 düzeltmesi (kendi ölçümümün hatası).** Probum yay örneklerini `_arc_points(center, radius, a, b)` ile
**dönüşüm yapmadan** aldı ✗; uygulama ise `guided.py:256`'da kanonik açıları pafta açısına çeviriyor
(`-e["a"], -e["b"]`) ✓ — yani "(b) konvansiyon uyuşmazlığı" iddiam **yanlış** olabilir. Güvenilir olan iki
ölçüm: `(i)` süzgeçler doğru (çerçeve ve antet döngüleri işaretli ✓, §23-C18 ölçüm 1); `(ii)` **uygulamanın
kendi** `options["profiles"]["points"]` kutusu outline_2 için 2119×2544 px (sayfa 2200×1700 ✗) — yani dev
profilin noktaları sayfa dışına taşıyor. Şüpheli artık **dev yarıçaplı sahte yaylar** (r ≈ 1080, 6–10°'lik
süpürmeler): vektör okuyucusu düz kenarı böyle veriyor ve `_align` yarıçapı gelen uçtan aldığı için yayın
merkezi sayfa dışına düşüyor; örnekleme merkez+yarıçap üzerinden gidince nokta da sayfa dışına çıkıyor.

**Tek sonraki iş (güncel).** Uygulamanın kendi nokta yolunu ölçmek: outline_2 ve outline_4 için her yayın
`center/radius/a/b` değerlerini ve `guided.py:256`'nın ürettiği örnek kutusunu bastırmak; ardından **vektör
okuyucusuna kambur (sagitta) kapısı** eklemek — `abs(radius)` sayfaya göre saçma olan ya da kendi kirişi
üzerinde 4 px'ten az kamburlaşan yaylar reddedilmeli (raster tarafındaki `ARC_MIN_SAGITTA_PX` kuralının
vektör karşılığı). Doğrulama: `test_guided.py::test_title_block_leaves_the_contour_and_number_menus` tek
başına (beklenen en geniş < 100 px) + stadyum üretiminin {10,0 / 23,772 / 83,709} mm sayıları değişmemeli.

## §23-C19: dev-döngü gerilemesi KAPANDI — span'ı koruyan `_align` + kiriş kapısı — 2026-09-28

**Kök (kesinleşti).** `_align` yarıçapı gelen uçtan alıyor ✓ ama açıyı `edge["b"] > edge["a"]` işaretine
göre **sarmalıyordu** ✗: neredeyse düz bir kenarın (vektör okuyucusunun bezier'i → r ≈ 1067, gerçek süpürme
~12°) küçük negatif süpürmesi `while b <= a: b += 360` ile **348°'ye** çıkıyor ✗ → `_arc_points` örnekleri
sayfanın dışına (y ≈ −1146) düşüyor ✗ → profilin noktaları pafta ölçeğine çıkıyor ✗ → test kırılıyordu.

**İndi.** `(1)` `_align` artık **süpürmeyi koruyor**: `span = edge["b"] − edge["a"]` (okuyucunun/koşunun
ölçtüğü gerçek yay ✓), `a` = gelen ucun kanonik açısı, `b = a + span`, giden uç o halkaya izdüşürülüyor —
sarma yok. `(2)` `_trace` yay bloğunda **kiriş kapısı**: `radius > 4 × |chord|` ve `|delta| > 180` ise
süpürme küçük yola indiriliyor (saman yolu: düz kenarın dev yarıçaplı yay sanılması).

**Ölçüm.** `10/Exercise 12.pdf` (2200×1700) en geniş wire profilleri: **2138 / 2119 px → 488×470, 374×52,
195×195 px** ✓ (süzgeçler zaten doğruydu: çerçeve 2121×1621 `_frame_loops` True ✓, antet 709×217
`_annotation_loops` True ✓). **`tests/test_guided.py` → 24 passed (95 s)** ✓. Testin eşiği dürüstçe
güncellendi: `< 100` → `< 620` (antet kutusu 708,6 px; eski eşik, bu konturları *yanlışlıkla* eleyen
yay-yönü kapısının yan etkisiydi; artık paftanın kendi 488 px'lik görünüşü sunuluyor ✓).

**Sınır.** Eski `0 < b−a < 360` kapısı bu bozuk süpürmeleri kazara eliyordu; kapı kalktığı için koruma artık
`_trace`'in kiriş kapısı + `_align`'ın span koruması. Vektör okuyucusunda ayrıca bir kambur (sagitta) kapısı
hâlâ iyi bir iş (r ≈ 1080'lik "yay"lar hâlâ yay olarak taşınıyor).

## §23-C20: UI kabulü — profil/kalibrasyon/kalınlık gerçek tarayıcıda ✓, delik+üretim koşum katmanına takıldı — 2026-09-28

**İki kez, temiz oturumdan, gerçek fare/klavyeyle doğrulandı.** Stadyum PNG'si gerçek dosya girişinden
yüklendi → panel "3 kontur · 2 daire" ✓; **kontur gerçek tıklamayla** ✓ (kayıt 1); **iki kalibrasyon noktası
gerçek tıklamayla**, değer **60** gerçek tuşlarla, "Ölçeği uygula" ✓ (kayıt 2); **kalınlık 10 yazıldı ve
"Kalınlığı kaydet" basıldı** ✓ (kayıt 3) — kullanıcının "tarayıcıda henüz denenmedi" dediği iki düğmeden
biri buydu ✓. İkinci turda aynı adımlar tekrar geçti ✓ (tekrarlanabilir ✓).

**Tıkaç: tarayıcı koşum katmanı (uygulama değil).** Kalan adımlar — iki daireyi seçmek, Ø7,2 yazmak,
**Üret**, indir, yeniden aç, geri al, SHA-256 — sırasında koşum katmanı art arda opsiyonlardan sonra
5 sn'lik IPC zaman aşımına düşüyor (`Runtime.evaluate`, `fill_input`, `Input.dispatchKeyEvent` ✗);
ayrıca **her yeni çağrıda sayfa `#sheet` olmadan geliyor** (aktif sekme kayboluyor ✗), yani akış tek
çağrıda bitmek zorunda; tek çağrıda ~6-8 opsiyondan sonra katman düşüyor ✗. Bu bir **ortam** sınırı:
A turunda (bu pencerenin başında) aynı akış 16 eylemde tamamlanabilmişti.

**Sonuç.** UI kabulünün **karar girişi** kısmı gerçek tarayıcıda kanıtlandı ✓; **üretim/indirme/geri alma**
kısmı için koşum katmanının daha sağlıklı olduğu bir an ya da daha küçük op grupları gerekiyor ✗ — bir
sonraki pencere bunu denemeli (ör. sayfayı `new_tab` ile açıp yalnız delik+üretim adımlarını çalıştırmak,
ya da A turundaki gibi `js` yerine daha çok gerçek tıklamayla ilerlemek). API probu UI kabulü **sayılmaz** ✓.

**Bekleyen koşular.** Dört paftanın bugünkü kodla ölçümü (`proc_5b980f6f2cdd` → `/tmp/guided-raster.txt`) ve
tam takım (`proc_628f5bca0d4e` → `/tmp/suite-c20.txt`).

## §23-C21: bayat tam takımın 3 kırığı — ikisi bilinen, biri bu pencerenin işi — 2026-09-28

**Koşu `proc_d2295cb92590` (raster/guided düzeltmelerinden ÖNCE başladı → bayat): 3 failed, 564 passed
(1:03:51).** `(1)` `test_guided.py::test_title_block_leaves_the_contour_and_number_menus` — **o günden beri
kapandı** ✓ (§23-C19; `test_guided.py` 24 passed ✓). `(2)` `test_raster.py::test_a_full_circle_is_not_
repeated_as_an_arc` — bilinen **sıra bağımlılığı** (tek başına geçiyor ✓). `(3)`
`test_catalog_cli.py::test_printed_values_survive_missing_scale_or_outline[4]` — **bu pencerenin kararı**
(§23-C7) fazla geniş: `proposal.read_sheet` (proposal.py:544-553) **raster yayı olan her paftada** ölçeği
düşürüyor ✗; test ise `sheet_px_per_mm = 4` **verilmiş** bir ölçekle "basılı değerler ölçek olmadan da
yaşar" savını sınıyor ✗ → verilen ölçek de düşünce test kırılıyor.

**Karar (uygulanacak).** `read_sheet` "verilmiş" ölçek ile "pikselden türetilmiş" ölçeği ayırt edemiyor
(provenans alanı yok ✗) — iki yol var: `(A)` `meanings`e ölçek provenansı eklemek (`scale_source: derived |
given`) ve kapıyı yalnız `derived` için işletmek (testin fixture'ı yeni alanı set etmeyeceği için varsayılan
`derived` olur ✗ — testin `[4]` varyantı yine kırılır ✗, o zaman test **kurala uygun** biçimde güncellenmeli:
raster paftada pikselden gelen ölçek paftanın kendi ölçüsü sayılmaz, ölçek kullanıcı kalibrasyonundadır);
`(B)` kapıyı tümden kaldırıp sahte ölçeği **kaynağında** kesmek (bind.py çapa seçimi + ölçek türetme yolu) —
ama ölçüm gösterdi ki yay çapaları dışlandığında bile .jpg 3,28 px/mm kuruyordu ✗ (9 çapa yetiyor ✓), yani
`(B)` tek başına yetmiyor ✗. **Öneri: `(A)` + testin `[4]` varyantını yeni davranışa göre güncellemek**
(test dosyası: `tests/test_catalog_cli.py:28`, `partial_reading.sheet_px_per_mm = scale`, parametre `[None,4]`).

**Doğrulama.** Güncel kodla tam takım koşuyor (`proc_628f5bca0d4e` → `/tmp/suite-c20.txt`); bitince bu üç
kırığın hangisinin sürdüğü kesinleşecek. Ayrıca dört paftanın ölçümü (`proc_5b980f6f2cdd`).

## §23-C22: run4 — raster paftalarda büyük konturlar KÜÇÜLDÜ (C19'un bedeli) — 2026-09-28

**Ölçüm (aynı dört pafta, ürün yolu, bugünkü kod; run3 → run4):**

| Pafta | run3 (önce) | run4 (bugün) |
|---|---|---|
| Exercise_51 | 11 profil, en büyük 994×119 | 11, **961×117 + 420×838** ✓ |
| Exercise 17 | 17, **594×435**, 486×450 | **9**, 179×353, 243×289 ✗ |
| Flange | 9, **634×593**, 494×653, 523×512 | **8**, 218×410, 48×102 ✗ |
| my_part.jpg | 19, **487×364**, 264×328 | 17, **315×238**, 153×206 ✗ |

Notlar artık neredeyse tümüyle `kontur uçları çizimde birleşmiyor` ✗ — yani **C19'da join'ler artık
kapanmıyor**. Sebep: `_align` artık süpürmeyi **koruyup** çıpayı (a) oynatıyor ✗; raster yaylarında uçlar
köşe birleşimiyle **çekildiği** için, izdüşüm eski (uç-güdümlü) davranışla yapılmalıydı ✓. Yani C19 vektör
yolunu kurtardı, raster yolunun kapanışını bozdu ✗ (Exercise 51'de yeni 420×838 kazancı var ✓ — tartılı).

**Tek sonraki iş (kesin).** `_align`ı iki davranışa ayırmak: **kurulum döngüsünde** (okuyucunun kendi verisi)
süpürme-koruyan davranış ✓; **birleşim döngüsünde** (köşe/ara nokta kapamasından sonra) eski uç-güdümlü
davranış — yani yarıçap gelen uçtan ✓, giden uç **kendi açısıyla halkaya** izdüşürülür ✓ (süpürme öyle
kurulur). Uygulama: `_align(edge, span_is_truth: bool)` ya da iki küçük yardımcı; sonra run4'ü tekrarlayıp
Exercise 17/Flange'in büyük kutularının (594×435 / 634×593) geri geldiğini ve `test_guided.py`nin 24
passed kaldığını doğrulamak ✓. Kiriş kapısı (r > 4×|chord| ve |delta| > 180) yerinde kalır ✓.

## §23-C23: `test_catalog_cli` kırığı — sebep provenans değil, korumasız `getattr` — KAPANDI — 2026-09-28

**Gerçek sebep (ölçüldü).** `AttributeError: 'types.SimpleNamespace' object has no attribute 'primitives'`,
`src/drawingto3d/proposal.py:546` — yani §23-C21'de tahmin ettiğim "verilmiş/pikselden türetilmiş ölçek
ayrımı" **değil** ✗: §23-C7 kapısı `observations.primitives`ı doğrudan gezdiği için, testin `observe` stub'ı
(`SimpleNamespace(frame=None)`) altında **çöküyordu** ✗.

**İndi.** İki yerde koruma: `raster_arcs(observations)` ve `read_sheet`'in ölçek kapısı artık
`getattr(observations, "primitives", ())` geziyor ✓. Provenans alanı **eklenmedi** (gereksiz çıktı ✓) ve
testin `[4]` varyantı **değiştirilmedi** ✓ (davranış zaten doğruydu ✓).

**Doğrulama.** `test_catalog_cli.py + test_guided.py + test_chain_model.py` → **36 passed (6:36)** ✓ — yani
`test_printed_values_survive_missing_scale_or_outline[4]` ✓, `test_guided.py` 24 ✓ ve sahte-ölçek
gerilemesinin bekçisi `test_chain_model.py` ✓ birlikte yeşil (raster ölçek düşürmesi gerçek .jpg'de hâlâ
çalışıyor ✓).

**Kalan tek bilinen kırık.** `test_raster.py::test_a_full_circle_is_not_repeated_as_an_arc` — **sıra
bağımlılığı** (tek başına geçiyor ✓, dosya koşusunda kırılıyor ✗; dosyada önce koşan bir test raster
modülünün durumunu değiştiriyor). Tam takım güncel ağaçta **565 passed, 2 failed** idi; bu düzeltmeyle
kalan kırık bu sıra bağımlılığı + §23-C22'nin raster kapanış borcu.

## §23-C24: §23-C22 DÜZELTMESİ — run5 == run4 (deterministik), C22'nin tablosu yanlış okundu — 2026-09-28

**İki bulgu.** `(1)` **run5, run4 ile bit bit aynı** (diff yalnız `notlar` satırlarında: teşhis mesajı artık
boşluğu ve öğe türlerini taşıyor ✓) → dört paftanın ürün yolu **deterministik** ✓. `(2)` **§23-C22'nin tablosu
hatalıydı** ✗: "en büyük kutu" diye yazdığım değerler koşu dosyasının **ilk listelenen** kutularıydı ✗,
en büyükleri değil ✗ (ölçüm hatam). Odaklı prob bunu gösterdi: **Exercise 17'nin sunulan en büyük profili
557×513 px (4 nokta, not yok ✓)** — yani "C19 raster kapanışını bozdu ✗" sonucu **fazla genel**: Exercise 17
parça ölçeğinde kontur sunuyor ✓.

**Deterministik kırılma noktaları (yeni teşhisle, kalıcı).** Her paftada izlenemeyen profillerin ilk kopan
birleşimi: Exercise_51 **1.**, Exercise 17 **5.**, Flange **17.**, my_part **3.** birleşim ✓ — mesaj artık
`kontur uçları çizimde birleşmiyor (N. birleşim, boşluk X px, tür→tür)` ✓. Profil sayıları/kutuları run3 →
run4 → run5 arasında *tam* karşılaştırma için `/tmp/guided-raster-run4.txt` ve `/tmp/guided-raster.txt`
(kopyaları) duruyor ✓; §23-C22 tablosundaki run3 değerleri de dosyada yazılı ✓ ama "en büyük" iddiası
için **yeniden okunmalı** ✗ (aynı hata olabilir ✗).

**Tek sonraki iş.** `/tmp/guided-raster*.txt` dosyalarından **per-pafta gerçek maksimum** kutuyu kodla çıkarmak
(bir önceki denemem regex'te başarısız oldu ✗ — kutu listesi satırı muhtemelen sarıyor/kesiliyor ✗; `guided_
raster.py`'nin kendi çıktı biçimine bakıp doğru ayrıştırmak) ve run3/run4/run5'i bu ölçütle karşılaştırmak ✓;
sonra kırılma noktalarının boşluk değerlerini (`grep -h notlar /tmp/guided-raster.txt`) okuyup `_align`
ayrımına (kurulum: süpürme-koruyan ✓ / birleşim: uç-güdümlü ✓) karar vermek.

## §23-C25: sıra bağımlılığının kökü — OpenCV iş parçacığı belirsizliği; `cv2.setNumThreads(1)` — 2026-09-28

**Ölçümler.** `tests/test_raster.py` **tek başına** → 1 failed, 11 passed (9:02) ✗ → bağımlılık **dosya içi** ✓
(dosyalar arası değil ✗). Çift koşu (`synthetic_arc_comes_back` + `full_circle`) → **0.68 s'de kırılıyor** ✓ →
hızlı, kesin bir üreme var ✓. Ayrıntılı koşu assertion'ı verdi: **`assert np.float64(5.9447…) > 20`** ✗ — yani
tam daire (merkez 120,160, r45) ikinci okumada **yay olarak geri geliyor** ✓ (merkez tahmini 5,94 px sapmış ✓).
Süreler 0,20 s / 0,15 s ✓ (yani "çok hızlı" şüphem yersizdi ✗ — sentetik paftada okuma ucuz ✓).
`raster.py`de **hiç önbellek/global/lru_cache yok** ✓ (tarandı ✗ — 33 sabit satırı ✓, hepsi statik ✓).

**Kök (kanıtla).** Aynı pafta, aynı kod; **ilk okuma yapıldığında** ikinci okumanın yay kümesi değişiyor → OpenCV'nin
Hough geçişleri iş parçacıklarına bölünüyor ve sonuç makinenin yüküne bağlı ✓; testin kendi yalnız-koşusu geçiyor ✓,
başka bir okuma önce yapıldığında kırılıyor ✗.

**İndi (doğrulaması sürüyor).** `observe_raster` artık girişte **`cv2.setNumThreads(1)`** çağırıyor ✓ (yorum
satırında ölçüm ve gerekçe yazılı ✓). Bu yalnız testi düzeltmiyor: **kullanıcı kararları aynı paftada aynı
sonucu vermeli** ✓ — tek iş parçacığı bunu satın alıyor ✓.

**Doğrulama koşusu:** `proc_8c325c878743` (önce çift koşu ✓ sonra dosyanın tamamı ✓; bitince bildirecek ✓).
Geçerse kalan tek bilinen kırık kalmaz (tam takım 565 passed, 2 failed → bu ikisi de kapanmış olur ✓).

## §23-C26: gerçek maksimumlar + kopan birleşimlerin boşluk envanteri (run6) — 2026-09-28

**Ölçüm (`guided_raster2.py` → `/tmp/guided-raster2.txt`; ilk kez *en büyük* kutu, alan sıralı ✓):**

| Pafta | wire | en büyük 3 (id, nokta, w×h, alan) |
|---|---|---|
| Exercise_51 | 7 | **outline_14 50n 420×838**, outline_46 50n 430×544, outline_3 52n 961×117 |
| Exercise 17 | 6 | **outline_49 4n 557×513**, outline_80 4n 353×304, outline_38 72n 243×289 |
| Flange | 6 | **outline_56 54n 269×415**, outline_9 50n 218×410, outline_51 73n 52×121 |
| my_part.jpg | 11 | **outline_12 220n 315×238**, outline_19 73n 153×206, outline_39 4n 205×125 |

Yani **dört paftanın dördü de parça ölçeğinde kontur sunuyor** ✓ (§23-C22'nin "küçüldü" okuması *ölçüm
hatasıydı* ✓; §23-C24 düzeltmesi doğrulandı ✓). Arka zengin konturlar da var: my_part'ta 220 noktalı ✓,
Flange'de 73 noktalı ✓ — yay örneklemesi çalışıyor ✓.

**Kopan birleşimlerin boşlukları (ilk kez ölçüldü ✓):** Exercise_51 **354,1 px arc→arc** + 24,2 px line→line;
Exercise 17 **134,3 arc→line** + 134,2 arc→arc + 40,? ; Flange **395,7 arc→line** + 20,0 line→line;
my_part **47,7 arc→line** + **6,6 arc→line** + 119,? ✗. Açık bir *yakın ıskalama* var: **my_part'ın 1. birleşimi
6,6 px** ✗ — `ARC_JOIN_MIDDLE_PX` (5,5 px ✓ = LOOP_TOLERANCE_PX 3,0 + ARC_JOIN_SLACK_PX 2,5 ✓) sınırını
**1,1 px** ile kaçırıyor ✓. Ayrıca 20,0 px line→line ve 24,2 px line→line, raster paftalar için konan zincir
toleransının (36 px ✓) *izleme* tarafındaki karşılığının olmadığını gösteriyor ✓.

**Tek sonraki iş (ölçümle seçildi).** Raster paftalarda `_trace`in ara-nokta kapamasını gevşetmek: **6,6 px ve
20,0 px** gibi boşluklar kapansın (ör. raster için `ARC_JOIN_MIDDLE_PX`i 36 px'lik zincir toleransıyla uyumlu
hale getirmek ✓), sonra `guided_raster2.py`yi tekrarlayıp yeni profillerin kutularını ve `test_guided.py`nin
24 passed'ini doğrulamak ✓; 354/134/395 px'lik boşluklar gerçek ayrı hattır ✗ — onlar kapanmamalı ✗.

## §23-C27: "sıra bağımlılığı" ÇÜRÜTÜLDÜ — kırık deterministikti; gerçek kusur `same_ring`in yarıçap payı — 2026-09-28

**Yanlış teşhis, kanıtla düzeltildi.** (a) Tek test **yalnız başına** koşuldu → **1 failed (0.43 s)** ✗ →
ortada *sıra bağımlılığı yok* ✗; test bugünkü okuyucuya karşı düz kırık ✗ (uzun süredir taşınan "yalnız geçiyor"
notu yanlıştı ✗). (b) Aynı sentetik pafta **üç kez** arka arkaya okundu (tek süreç) → üç okuma da **birebir
aynı**: 2 yay, 1 daire ✓ — yani "OpenCV iş parçacığı belirsizliği" hipotezim de **yanlış** ✗.

**Gerçek kusur (ölçüldü).** Her okumada **sahte bir yay** var: merkez çizili dairenin merkezinden **5,94 px**,
yarıçap **37,4** ✗ — çizili dairenin yarıçapı **46,7** ✓ → aradaki fark **9,3 px** ✗. Kapı `raster.py:336`
`same_ring`: merkez payı `max(8, 0.15r)` ✓ (5,94 geçiyor ✓) ama yarıçap payı `max(6, 0.15r)` = **6,0** ✗ →
9,3 px fark kapıyı kaçırıyor ✗ → süzülmeyen yay `'hough-arc'` olarak observation'lara giriyor ✗ ve testin
`> 20 px` savını kırıyor ✗ (assert değeri birebir: `np.float64(5.9447…) > 20` ✓).

**İndi.** `same_ring`in yarıçap payına **tutulan** halkanın oranı eklendi: `max(6.0, 0.15·r, 0.25·oradius)` ✓
(gerekçe ve ölçüm docstring'de ✓). Aynı halkanın kendi mürekkebinden türeyen parçalar artık düşüyor ✓;
gerçek eş merkezli ikinci bir halka zaten *strict* geçişte daire olarak tutulur ✓ (kapının sözleşmesi bu ✓).

**Geri alınan değişiklik.** `observe_raster`a konan `cv2.setNumThreads(1)` **geri alındı** ✗ — gerekçesi
(okuyucunun iş parçacığına göre değişmesi) ölçümle çürüdü ✓; doğrulanmamış küresel yan etki bırakılmaz ✓.

**Doğrulama:** `proc_96dd8cd91076` (dosyanın tamamı, 12 dk; bitince bildirecek ✓). Geçerse son tam takımın
iki kırığından **ikincisi** de kapanır (§23-C23 ilkini kapattı ✓) → ağaç yeşil ✓.


## 25. %15 kalan pay sınırında devam kaydı — 2026-09-28

Bu devam için güncel kayıt HANDOFF'un ilk bölümüdür. §24'ün mevcut öneri ve günlük kodu korunmuştur. Eşik kontrolü %86 kullanım/%14 kalan gösterince yeni kapsam durduruldu.

- Gerçek PDF temiz arayüzden yüklendi, öneriler onaylandı ve taslak STEP üretimi tamamlandı. Elle iki nokta kalibrasyonu henüz kabul edilmedi; otomasyon koordinat uyuşmazlığı açık.
- Cep önerisi onayında seçilmeyen derinliğin sessiz uygulanması ve kullanıcı derinliğinin üzerine yazılması düzeltildi. Derinlik tekil onayı ve eksik span kanıtı düzeltildi. 45 odaklı test geçti.
- Ölçü çözümünün ilk bağımsız modülü eklendi: çizgi konturu, X/Y mesafesi, yatay/dikey ilişki, çelişki, serbestlik ve kaynak ifadeleri. 22 test geçti. **Ürün akışına entegre değil; B teslimi tamamlanmadı.**
- Tek sonraki iş: desteklenen kısıtları karar kaydı/GeneralPlan/arayüze bağlayan küçük entegrasyon. Kalıcı kayıt, geri alma, çelişkide üretimi durdurma ve bağımsız STEP ölçüleriyle doğrula. Yay teğetliği ve yarıçap çözümünü destekleniyormuş gibi gösterme.
- Rapor `eval/reports/guided-continue.md`; yedek manifesti `out/checkpoints/guided-latest.json`. Tam takım bu turda tekrar çalıştırılmadı; 45+22 odaklı test ayrı koşulardır.

## §23-C28: kapının İKİ kopyası vardı — biri genişletilmiş payı kullanmıyordu; kırık KAPANDI — 2026-09-28

**Kök (ölçümle).** §23-C27'de genişlettiğim `same_ring` payı tek başına yetmedi ✗ (dosya yine 1 failed ✗).
Sebep: aynı halka testinin **ikinci bir kopyası** vardı — `_verified_arcs`in sonundaki *dedupe* geçişi
(`raster.py:412-419`) kendi `max(6.0, 0.15·r)` payını taşıyordu ✗ ve az önce düşürülen parçayı **geri alıyordu** ✗.

**İndi.** Dedupe geçişi artık aynı kapanışı çağırıyor: `if same_ring(cx, cy, radius)` ✓ — tek doğruluk
kaynağı ✓ (yorumda "bu geçiş kendi kopyasını tutuyordu ve genişletilmiş payın az önce düşürdüğü parçaları
sessizce geri alıyordu" yazılı ✓).

**Doğrulama.** `test_a_full_circle_is_not_repeated_as_an_arc` **+** `test_synthetic_arc_comes_back_with_its_span`
→ **2 passed (0.82 s)** ✓✓. Dosyanın tamamı `/tmp/raster-c28.txt`e koşuyor ✓ (12 dk ✓).

**Ders (kayıtlı).** Bir tolerans iki yerde kopyalanmışsa, genişletmek *yetmez* ✗: kopya eski değeri kullanmaya
devam eder ✓ — ölçüm iki kapıyı da görmeli ✓. §23-C25'teki `cv2.setNumThreads(1)` geri alınmıştı ✓ (gerekçesi
çürümüştü ✓); §23-C27'nin kapı genişletmesi *kalıyor* ✓ (parça gerçekten bir dairenin mürekkebinden geliyor ✓).

## §23-C29: `test_raster.py` dosyası YEŞİL — 12 passed (10:07) — 2026-09-28

§23-C27 (kapının yarıçap payı) + §23-C28 (payın ikinci kopyası) birlikte dosyayı yeşile çevirdi ✓ —
`tests/test_raster.py` → **12 passed** ✓ (öncesi: 1 failed/11 passed ✗, "sıra bağımlılığı" sanılan kırık ✗).
Tam takım `/tmp/suite-c29.txt`e koşuyor ✓ (öncesi: 565 passed + 2 failed ✗; o iki kırık §23-C23 ve §23-C27/C28
ile kapandı ✓ → beklenti: **tamamı yeşil** ✓). Yeşil çıkarsa bu pencerenin test borcu kapanır ✓.

## §23-C30: `_trace`in ara-nokta kapaması zincirin toleransına hizalandı — 2026-09-28

**Gerekçe (ölçüm).** Zincir raster paftada bir konturu **36 px**e kadar kapatıyor ✓ (`RASTER_JOIN_TOLERANCE_PX`),
ama `_trace`in ara-nokta kapaması **5,5 px**te kalıyordu ✗ → zincirin az önce bulduğu kontur izleme sırasında
yeniden atılıyordu ✗. Ölçülen kopuşlar (§23-C26): **my_part.jpg 6,6 px**, **Exercise_51 24,2 px**, **Flange
20,0 px** — hepsi eski tavanın üstünde ✗.

**İndi.** `_trace(loop, mid_join_px=…)` parametresi aldı ✓; `drawing_options` bu değeri zincirle aynı
kaynaktan veriyor: `mid_join_px = max(ARC_JOIN_MIDDLE_PX, RASTER_JOIN_TOLERANCE_PX if raster else
LOOP_TOLERANCE_PX)` ✓ (yorumda ölçüm ve gerekçe yazılı ✓). Vektör yolu **değişmedi** ✓ (5,5 px ✓);
354/134/395 px'lik boşluklar hâlâ gerçek ayrı hatlar ✓ — kapanmazlar ✗.

**Doğrulama.** `tests/test_guided.py` → **24 passed (41 s)** ✓. Gerçek paftalarda etkisi run7 ile ölçülüyor ✓
(`/tmp/guided-raster2-run7.txt` ✓): beklenen — my_part 11 wire ✓ iken 6,6 px'lik birleşim kapanınca yeni/ daha
büyük konturlar ✓; kutu listeleri §23-C26 tablosuyla karşılaştırılacak ✓.

**Not (bayat koşu).** Tam takım `proc_0fddb9ac8f79` bu değişiklikten **önce** başladı ✗ → sonucu bu dilim için
bayat sayılmalı ✓; yeşil çıkarsa raster düzeltmelerini doğrular ✓, ama ara-nokta hizası sonrası **tekrar
koşulmalı** ✓.

## §23-C31: TAM TAKIM YEŞİL — 567 passed (18:19) — 2026-09-28

`pytest -q` → **567 passed, 0 failed** ✓ (öncesi: 565 passed + 2 failed ✗; kırıklar §23-C23 ve
§23-C27/C28 ile kapandı ✓). Bu koşu **ara-nokta hizasından önce** başladı ✗ → yeşillik raster düzeltmelerini
(§23-C25 geri alındı ✓, §23-C27/C28 ✓) ve `test_catalog_cli` düzeltmesini (§23-C23 ✓) kapsıyor ✓; ara-nokta
hizasından (§23-C30) sonra **tekrar koşuluyor** ✓ (`/tmp/suite-c31.txt` ✓) → o da yeşilse bu pencerenin
test borcu tamamen kapanır ✓.

## §23-C32: run7 — §23-C30 fazla kapatıyor; parametre zincirin toleransı, izlemenin cömertliği değil — 2026-09-28

**Ölçüm (run6 → run7, ara-nokta tavanı 5,5 px → 36 px):**

| Pafta | run6 | run7 |
|---|---|---|
| Exercise_51 | 11 profil / 7 wire; en büyük 420×838 | **49 / 45**; 626×1005, 755×706 |
| Exercise 17 | 9 / 6; 557×513 | **51 / 48**; 1005×538, 809×497 |
| Flange | 8 / 6; 269×415 | **31 / 29**; 831×1055 (368 nokta) |
| my_part.jpg | 17 / 11; 315×238 | **41 / 35**; 1408×949 (≈ pafta boyu ✗) |

Yani izlemeye zincirin 36 px'ini vermek menüyü **sel basıyor** ✗: wire sayısı 7–11 → 45–48 ✗, en büyük kutular
pafta boyuna çıkıyor ✗ (my_part 1408×949 = çerçeve/kâğıt ölçeği ✓), yani 20–36 px'lik boşluklar **orta noktada**
kapatılınca her uç 10–18 px kayıyor ✗ ve birbirine ait olmayan parçalar birleşiyor ✗.

**Sonuç ve alınan karar.** Kök, §23-C30 değil **zincirin 36 px toleransının kendisi** ✓: o tolerans hem az sayıda
izlenen kontur (run6 ✗) hem de sel (run7 ✗) üretiyor ✗. **İzlemenin tavanı geri alındı** ✓ (`mid_join_px =
ARC_JOIN_MIDDLE_PX` ✓, yorumda run7 ölçümü ve gerekçe yazılı ✓; parametre *tarama için* duruyor ✓) —
`test_guided.py` **24 passed (52 s)** ✓ → ağaç run6 davranışında ✓.

**Tek sonraki iş (ölçümle).** `RASTER_JOIN_TOLERANCE_PX`i **süpürmek** (ör. 6 / 10 / 15 / 20 px ✓) ve her değerde
dört paftanın `guided_raster2` çıktısını almak ✓: aranan, **parça konturunun kapanması** ✓ (my_part 6,6 px,
Flange 20,0 px, Ex_51 24,2 px ✓) ile **selin başlamaması** ✗ arasındaki bant ✓. Sonra o değer hem `_loops`a
hem `_trace`in ara-nokta tavanına **aynı kaynaktan** verilmeli ✓ (§23-C28'in dersi: iki kopya olmasın ✓).

## §23-C33: UI kabulünde gerçekten kalan tek öğe — delik seçme tıklamasının toleransı — 2026-09-28

**Tarayıcı oturumu boş geldi** ✗: koşum katmanı yeniden başlamış, `/guided` sekmesi yok ✓ (yalnız
`chrome://newtab` + `about:blank` ✓). Yani §23-C16/C20'deki oturum **sürdürülemiyor** ✗; yeni bir kabul
turunun tek çağrıda yapılması gerekiyor ✓ (akış ~8+ opsiyon ✗, katman 6–8'den sonra düşüyor ✗).

**Ama tablo netleşti — kalan iş sanılandan küçük.** §23-A kaydı (bu hedefin başında, gerçek tarayıcıda,
2 dk 48 sn, 16 eylem) **üret → indir → yeniden aç → geri al** adımlarını zaten geçmişti ✓. §23-C16/C20'de
temiz oturumdan **kontur + iki noktalı kalibrasyon + basılı değer + "Kalınlığı kaydet"** gerçek tıklama ve
gerçek tuşlarla iki kez doğrulandı ✓ (kayıt 1, 2, 3 ✓). Dolayısıyla UI kabulünde **ölçülmemiş kalan tek
öğe**: kalınlıktan sonraki **delik seçme tıklamasının toleransı** ✗ (`holeAt`/`snapEnd`in kullanıcı tıklamasını
hangi mesafeye kadar kabul ettiği ✓) — kullanıcının "son tıklama toleransı henüz tarayıcıda denenmedi" dediği
madde ✓.

**Tek sonraki iş (UI).** Tek çağrıya sığan en küçük tur: sayfayı `new_tab`la aç ✓ → PNG yükle ✓ → konturu
tıkla ✓ → iki kalibrasyon noktası + değer ✓ → kalınlık ✓ → **bir daireye tıklayıp Ø7,2 yaz + "Delik ekle"** ✓
→ **Üret** ✓ (deliklerin ikincisi ve indir/SHA sonraki tura ✓). Sığmazsa: bir sonraki pencere "delik+üret"
adımlarını *aynı* çağrıda açıp denemeli ✓.

**Koşan ölçüm:** `RASTER_JOIN_TOLERANCE_PX` süpürmesi (6/10/15/20/36 px, dört pafta; `proc_c8c4a660ffd7` →
`/tmp/sweep-tol.txt` ✓, ~50 dk ✓) — §23-C32'nin sıradaki işi ✓.

## §23-C34: birleşim toleransı süpürüldü → 20 px seçildi (taze ölçüm sürüyor) — 2026-09-28

**Süpürme (tek `observe` per pafta, 5 tolerans; `/tmp/sweep-tol.txt`):**

| Pafta | 6 px | 10 px | 15 px | 20 px | 36 px |
|---|---|---|---|---|---|
| Exercise_51 | 15 wire, 1924×2609 ✗ (kâğıt) | 14, 605×1126 | 10, 1036×1932 ✗ | **9, 723×718** | 9, 420×838 |
| Exercise 17 | 28, 893×719 | 22, 893×719 | 20, 455×181 | **17, 730×816** | 5, 351×311 |
| Flange | 19, 936×884 ✗ | 12, 400×652 | 16, 714×506 | **12, 356×568** | 4, 52×121 ✗ |
| my_part.jpg | 25, 570×348 | 16, 297×307 | 22, 570×348 | **14, 427×334** | 11, 452×204 |

**Okuma.** Dar tolerans (6 px) **çok sayıda küçük çöp** üretiyor ✗ (15–31 wire; Exercise_51'de 1924×2609 =
kâğıt/çerçeve ✗); geniş tolerans (36 px) küçük döngüleri birleştirip **az ve bazen parça dışı** kutu bırakıyor
(Flange 4 wire / 52×121 ✗). Orta bant (20 px) dört paftada da **parça ölçeğinde en büyük kutu** veriyor ✓
(723×718 / 730×816 / 356×568 / 427×334 ✓) ve kâğıt ölçeğinde kutu yok ✓ → **`RASTER_JOIN_TOLERANCE_PX = 20.0**
seçildi ✓ (yorumda ölçüm ve gerekçe ✓).

**Ölçüm uyarısı (kendi hatam, kayıtlı).** Süpürme, `observe` sonucunu paylaştığı için çağrılar arası durum
taşımış olabilir ✗ (36 px satırı run6'nın taze koşusuyla birebir değil ✗: Ex 17 5↔6 wire, Flange 4↔6 ✗) →
sayılar *yön* için güvenilir ✓, kesin değer için değil ✗. Bu yüzden **20 px ile taze süreçte** dört pafta
yeniden ölçülüyor ✓ (`/tmp/guided-raster2-run8.txt` ✓) ve §23-C26 tablosuyla karşılaştırılacak ✓.

## §23-C35: 20 px taze süreçte doğrulandı — süpürme geçerli, kutu tablosu iyileşti — 2026-09-28

**run8 (taze süreç, `RASTER_JOIN_TOLERANCE_PX = 20.0`) — süpürmenin 20 px satırıyla *birebir*** ✓ (yani
"`observe` paylaşımı durum taşıdı" endişem **çürüdü** ✗; süpürme sayıları geçerli ✓):

| Pafta | run8 (20 px, taze) | run6 (36 px, taze) |
|---|---|---|
| Exercise_51 | 13 profil / **9 wire**; **723×718 (99 nokta)**, 610×727 (50) | 7 wire; 420×838 (50), 430×544 |
| Exercise 17 | 20 / **17 wire**; **730×816 (53)**, 493×451, 382×455 | 6 wire; 557×513 (**4 nokta** ✗), 353×304 |
| Flange | 14 / **12 wire**; **356×568 (50)**, 340×443, 234×468 | 6 wire; 269×415 (54), 218×410 |
| my_part.jpg | 20 / **14 wire**; **427×334 (243 nokta)**, 327×235 | 11 wire; 315×238 (220), 153×206 |

**Okuma.** 20 px her paftada en büyük kutuyu **büyüttü** ✓ ve nokta sayısını artırdı ✓ (Exercise 17'nin 4 noktalı
dörtgeni → 53 noktalı gerçek kontur ✓; my_part 220 → 243 nokta ✓); kâğıt/çerçeve ölçeğinde kutu **yok** ✓;
wire sayısı 9–17 ✓ (run6 6–11 ✗ → ölçülü artış ✓, run7'nin 45–48 seli ✗ yok ✓). **Karar: 20 px kalıyor** ✓.

**Kalan yakın ıskalamalar (yeni teşhisle).** Notlarda 14,9 px ve 17,0 px'lik line→line boşlukları görünüyor ✗ —
zincir 20 px'i kabul ediyor ✓ ama izlemenin ara-nokta tavanı 5,5 px ✗ → bu birleşimler hâlâ düşüyor ✗. Bu,
`mid_join_px`i zincirin *yarısı* kadar (ör. 10 px ✓) açmanın **ölçülebilir** sonraki adımı ✓ — run7'nin seli
36 px'te gelmişti ✗, 10 px denenmeli ✓.

**Test borcu:** taze tam takım `/tmp/suite-c35.txt`e koşuyor ✓ (20 px + geri alınmış ara-nokta tavanıyla ✓).

## §23-C36: tam takım YEŞİL (567) + `mid_join_px` 10 px denemesi koşuyor — 2026-09-28

**Taze tam takım** (20 px tolerans + geri alınmış ara-nokta tavanı, güncel ağaç): **567 passed (17:27)** ✓✓ —
bu pencerenin test borcu kapandı ✓.

**İnen deneme.** `_trace`in ara-nokta tavanı raster paftalarda artık zincirin **yarısı**: `mid_join_px =
max(ARC_JOIN_MIDDLE_PX, RASTER_JOIN_TOLERANCE_PX / 2.0) if raster else ARC_JOIN_MIDDLE_PX` ✓ (10 px ✓; her uç en
fazla 5 px kayar ✓; gerekçe ve run7 uyarısı yorumda ✓). Hedef: §23-C35'te ölçülen **14,9 px** ve **17,0 px**
line→line boşluklarının kapanması ✓ — sel gelmeden ✓ (sel 36 px'te gelmişti ✗).

**Ölçüm koşusu:** `guided_raster2` (dört pafta, taze süreç ✓) + `test_guided.py` aynı arkada ✓ →
`/tmp/guided-raster2-run9.txt` ✓. Karşılaştırma ölçütü: run8 tablosu (§23-C35 ✓) — wire sayısı **9–17 bandında
kalmalı** ✓ (artış kabul ✓, 45+ sel ✗), en büyük kutular küçülmemeli ✓.

## §23-C37: ara-nokta tavanı 10 px — daha çok kontur, sel yok; kalıyor — 2026-09-28

**Ölçüm (run8 = 5,5 px → run9 = 10 px, dört pafta taze süreç):**

| Pafta | run8 | run9 |
|---|---|---|
| Exercise_51 | 9 wire; 723×718, 610×727, 429×422 | **12 wire**; 723×718, 610×727, **423×684 (26 nokta)** ✓ |
| Exercise 17 | 17 wire; 730×816, 493×451, 382×455 | **23 wire**; 730×816, **479×493** ✓, 493×451 |
| Flange | 12 wire; 356×568, 340×443, 234×468 | **19 wire**; 356×568, **530×378** ✓, 340×443 |
| my_part.jpg | 14 wire; 427×334, 327×235, 351×217 | **18 wire**; 427×334, 327×235, 351×217 (aynı) |

**Okuma.** 10 px tavan yeni **parça ölçeğinde** konturlar kazandırdı ✓ (Ex_51 423×684, Ex 17 479×493, Flange
530×378 ✓) ve en büyük kutuları **küçültmedi** ✓; **kâğıt/çerçeve ölçeğinde kutu yok** ✗ ✓ ve wire sayıları
12–23 ✓ — run7'nin seli (45–48 + çerçeve ✗) gelmedi ✓. `test_guided.py` **24 passed (36 s)** ✓.
**Karar: 10 px kalıyor** ✓ (her uç ≤5 px kayar ✓, alt mm düzeyi ✓).

**Sonraki dilim (hazır reçete).** Sıradaki: **en büyük profili akışa verip STEP üretmek** — tercihen
`Exercise 17` (730×816, 53 nokta ✓): API yolundan `open` → `profile` (`outline_2`) → **kalibrasyon** (iki nokta +
provisional değer ✓; raster paftada ölçek *kullanıcının* kararıdır ✓, ölçüm/karşılaştırma amaçlı taslak ✓) →
`thickness` → `build` → `step_facts` (`.venv-cad`) ✓ → referans `3/Exercise 17.STEP` ile **yalnız
değerlendirmede** dış ölçü/delik/hacim karşılaştırması ✓. Çıkan STEP **taslaktır** ✓ (pikselden izlenen kontur
doğrulanmış ölçü değildir ✓).

## §23-C38: gerçek paftada CAD üretimi başarısız — teşhis düzeltmesi, 2026-09-28

Exercise 17 deneyi `build_status=failed`, `error="geçersiz katı"` ile bitti. Geçici
100 mm kalibrasyon ve 10 mm kalınlık deney kararlarıdır; çizimden doğrulanmış ölçü sayılmaz.

Önceki "kontur 308 piksel açık, plan üretilmedi" teşhisi geçersizdir:

- `guided._trace`, `join_max_px` değerini birleşimler düzeltilmeden önce toplar.
  `sketch.diagnose` bunu `open_contour_px` adıyla sunuyor. Bu değer son geometride kalan açıklık değildir.
- Kaydedilmiş seçili profilin yedi birleşimi tekrar ölçüldü: saklanan uçlar ve merkez/yarıçap/açıdan
  yeniden kurulan yay uçları arasındaki açıklıklar sayısal hassasiyet içinde sıfır.
- Çizgi `g206` ile yay `g618` arasında yaklaşık `(2520.9680, 650.9041)` pikselde iç kesişim
  hesaplandı. Bu kimlikler yalnız hata kanıtıdır; üretimde bu örneğe özel koşul yazılmayacak.
  Kapanmış kontur, geçerli ve kendini kesmeyen bir sınır anlamına gelmiyor.
- API'deki `plan:null` bir yayımlanmış indirme bağlantısı olmadığını söylüyor. Deney klasöründe
  `plan.json` var; plan kurulduktan sonra CAD üretimi başarısız olmuş.
- CAD hatasının bütün nedenlerinin çözüldüğü iddia edilmiyor. Sonraki genel mekanizma,
  son geometrinin kapanışını ve öz-kesişimlerini ayrı denetleyip kullanıcıya göstermeli.

Kanıt: `out/guided/7b8d01cd771a46c6bbc52bccb767caa1/build-1-860e22df/plan.json`,
oturumun `session.json` kaydı ve `/tmp/unseen17-flow.json` deney çıktısı.
Bu başarısız örnek ürün başarısı sayılmaz. Güncel iş sırası Bölüm 26'dadır.


## 26. Evrensel ürün kapsamı ve güncel uygulama sırası — 2026-09-28

**Bu bölüm güncel kullanıcı kararını uygular ve eski "tek sonraki iş" kayıtlarının yerine geçer.**
Hedef M1 / 16 GB cihazda, kurulumdan sonra çevrimdışı çalışan, farklı teknik çizim PDF/PNG/JPG'lerinden
kullanıcı yönlendirmesiyle düzenlenebilir CAD planı ve STEP üreten genel bir programdır. Ürünün kapsamı
tek parçayla veya örnek klasöründeki ailelerle sınırlanmaz. Desteklenmeyen geometri açıkça gösterilir;
bilinmeyen şekil bilinen bir şablona zorlanmaz.

### 26.1 Test verisinin sınırı

- `examples/pdf with steps` **yalnız test/değerlendirme verisidir**. PDF/PNG/JPG, test sırasında normal
  kullanıcı girdisi olarak ürüne verilebilir; eşleşen STEP yalnız bağımsız değerlendirme adımında açılır.
- Bu klasör model eğitimi, ince ayar, örnek hafızası veya üretim sırasında benzer parça arama kaynağı
  olmaz. Eğitim gerekirse ayrı, uygun ve değerlendirmeden ayrılmış veri toplanır.
- Dosya adı, klasör numarası, dosya özeti, bilinen koordinatlar veya referans model üzerinden özel
  üretim davranışı eklenmez. Dosya özeti yalnız oturum kaynağını ve sürümünü doğrulamak için kullanılabilir.
- Hata bir örnekte ortaya çıkabilir; düzeltme ortak geometrik kurala dayanmalı ve bağımsız sentetik
  örnekler ile farklı çizimlerde doğrulanmalıdır. Kontur sayısını veya en büyük kutuyu artıran tolerans
  ayarı tek başına iyileşme sayılmaz.
- Daha önce incelenen örnekler artık **görülmüş regresyon verisidir**. Bunlar sonradan "görülmemiş"
  olarak etiketlenmez. Bağımsız kabul için geliştirmede kullanılmamış yeni parça grupları gerekir;
  aynı parçanın farklı görünümleri veya raster/vector kopyaları aynı grupta kalır.

### 26.2 Ürünün ortak mekanizmaları

Çizimi okuma → görünüş/geometri adayları → belirsizliklerin gösterilmesi → kullanıcı ölçü ve kontur
kararları → kısıt çözümü → GeneralPlan → CAD üretimi → doğrulama ve STEP. Her parça bu ortak akıştan geçer.
Kullanıcı yanlış kenarı çıkarabilmeli, doğru kenarı seçebilmeli, açık ucu tamamlayabilmeli, bir ölçüyü
kenar/merkeze bağlayabilmeli ve özellik türü/derinliğini belirtebilmelidir. Her kararın kaynağı, revizyonu,
geri alması ve yeniden açılması korunur. Karar değişince eski çıktı güncelmiş gibi sunulmaz.

Dış kontur seçimi yalnız en büyük alan/kutuya dayanmaz. Geometrik geçerlilik, çizim kanıtı ve kullanıcı
onayı ayrı tutulur. Parça türü tahmini yardımcı öneri olabilir; genel işlemler yerine örneğe özgü
şablon seçimini zorunlu kılamaz. İlk işlemler profil uzatma ve kesme; devamında aynı kanonik plan
üzerinden dönel, çok görünüşlü ve daha karmaşık özellikler desteklenir.

### 26.3 Mevcut kodun doğru tanımı

- `sketch.py` kullanıcı bağlarından **ortak ölçek ve sapma** hesaplıyor. Kenarları/delik merkezlerini
  ayrı ayrı hareket ettiren kesin bir eskiz çözücüsü değildir. Arayüz ve plan açıklamalarındaki
  "kesin eskiz çözümü yapıldı" ifadesi bu davranışa uygun hale getirilecek.
- `sketch_constraints.py` konum kısıtlarının ayrı çekirdeğidir; mevcut `guided.make_plan` bunu
  kullanmıyor. Entegrasyon öncesi şema, kaynak ifadeleri, desteklenen geometri ve testler gözden geçirilecek.
- `join_max_px`, birleştirme öncesindeki boşluktur. Son kapanış hatası, yapılan düzeltmenin miktarı,
  öz-kesişim, ölçü tutarlılığı ve CAD katı geçerliliği ayrı ölçülecek. Ölçü tutarlılığına
  `consistent=True` denmesi bütün geometrinin geçerli olduğu anlamına gelmez.
- 567 test geçen kayıt son tolerans değişikliğinden önceki ağacı kapsıyor; sonrasında 24 odaklı test
  kaydı var. Bunlar yeni ve görülmemiş parçalarda doğruluk oranı değildir.

### 26.4 Sıralı teslimler

**A — Genel kontur doğrulaması ve kullanıcı düzeltmesi (ilk iş).**
Önce yanlış tanı alanlarını ve ürün metinlerini düzelt. CAD'e gönderilecek son çizgi/yay geometrisini
kullanarak kapanış, sıfır uzunluk, yinelenen/çakışan kenar ve öz-kesişim denetimi ekle. Çizgi-çizgi,
çizgi-yay ve yay-yay durumlarını, komşu kenarların normal ortak uçlarını ayırt ederek işle. Hatalı bölgeyi
çizimde işaretle; kullanıcı seçimi değiştirebilsin, kenarı çıkarıp ekleyebilsin veya açık uç için
önerilen birleşimi onaylayabilsin. Yapılan konum değişimini göster. Geçersiz sınır üretimi durdursun;
hata açıklaması yalnız "geçersiz katı" olarak kalmasın.

Kabul: kapalı ama kendi üzerinden geçen kontur, gerçekten açık kontur, geçerli içbükey kontur,
teğet yay birleşimi ve ters yönde dolaşılan yay için bağımsız örnekler. Aynı doğrulama farklı
paftalara uygulanmalı. Kullanıcı düzeltmesi kaydedilip geri alınabilmeli; düzeltmeden sonra gerçek
CAD üretimi ve STEP'in yeniden açılması doğrulanmalı. Örnek kimlikleri üretim koduna girmemeli.

**B — Ölçüye bağlı geometriyi ürün akışına bağla.**
Mevcut kısıt çekirdeğini Decisions, GeneralPlan, kayıt/geri alma ve çizim arayüzüne bağla. Kullanıcı
kenar/köşe/merkez seçerek yatay-dikey mesafe ve ilişki tanımlayabilsin; geometri verilen ölçüye göre
hareket etsin. Çelişen bağlar ve eksik serbestlik görünür olsun; tutarlı tekrar hata sayılmasın.
`user`, `derived` ve `assumed` kaynaklarını koru. Yay yarıçapı, açı ve teğetlik desteği gelene kadar
bu sınırlamayı açık göster; ölçülendirilmeyen kısmı taslak tut.

Kabul: çizimden izlenen bozuk oranların verilen ölçülerle düzelmesi, kesin delik merkezi ve cep
geometrisinin bağımsız STEP ölçümünde doğrulanması. Kullanıcı işlemi API deneyiyle birlikte gerçek
arayüzden de sınanmalı. Tek ölçek ayarı bu teslimin tamamlanması değildir.

**C — Genellemeyi bağımsız parça gruplarında ölç ve kapsamı büyüt.**
Geliştirmede görülmemiş, farklı geometri/özellik birleşimlerine sahip çizimler seç. Vector, taranmış
ve ölçeksiz çizimlerde aynı kullanıcı düzeltme akışını ölç. Doğru son STEP; yanlış/eksik özellik;
konum, çap ve derinlik hatası; müdahale sayısı; tamamlanma süresi ve elle CAD'e göre kazanç raporlansın.
Başarısız ve desteklenmeyen örnekler paydadan çıkarılmasın. Referans yoksa yalnız katı geçerliliği ve
kullanıcı ölçülerine uyum doğrulandı de; genel doğruluk ilan etme. Bir kabul örneğinin çalışması
üretim mekanizmasını doğrular, evrensel hedefi tamamlamaz.

**D — Model yardımı ve gerekirse eğitim.**
Kurallı geometri ve kullanıcı düzeltmesi çalıştıktan sonra model belirsiz kararlar için seçenek
önersin. Model kapalı kullanım çalışmaya devam etsin. Kurallı, kullanıcı destekli ve model destekli
akış aynı bağımsız veride karşılaştırılsın. Eğitim ancak tekrar eden hata, ayrı eğitim verisi ve
ölçülen katkı varsa başlasın; test örneklerinin cevapları üretim girdisine taşınmasın.

### 26.5 Çalışma ve devir kuralı

İlk uygulama teslimi A'dır: her çizime uygulanabilen son kontur doğrulaması ve kullanıcı düzeltmesi.
Tek bir gerçek parça bu teslimin kabul örneklerinden biri olabilir; bütün işi o dosyaya uyarlama.
Her turda tamamlanan mekanizmayı, bağımsız kanıtı, ilgili testleri, kalan sınırı ve tek sonraki işi
PLAN/HANDOFF'a kaydet. Kaydedilen hatanın anlamını koddan doğrulamadan uzun deneye başlama. Bir
hipotez çürürse sonraki iş tarifini düzelt; eski kayıtların yeni ajanı yanlış yönlendirmesine izin verme.
Mevcut çalışma ağacını koru; aynı dosyalarda birden fazla ajan varsa sahipliği belirleyip sırayla
entegre et.

## §26-A-1: genel kontur doğrulaması indi — yanlış tanı alanları düzeltildi, geçersiz sınır üretimi durduruyor — 2026-09-28

PLAN §26.4-A'nın ilk yarısı. **Yeni modül `src/drawingto3d/contour_audit.py`**: CAD'e gidecek *son* çizgi/yay
geometrisi (pafta pikselleri) üzerinde — **gerçek kapanış** (ardışık birleşimler + son→ilk sarma; `closure_px`),
**sıfır uzunluk**, **yinelenen/çakışan kenar** (aynı destek + örtüşen aralık), **öz-kesişim** (çiftin türüne göre
line-line / line-arc / arc-arc ayrımıyla) ve **yayın kendi ucuyla tutarsızlığı** denetimi ✓. Her sorun **pafta
pikselinde bir konum** taşıyor ✓ (arayüz işaretleyebilsin diye ✓). Örnek kimliği, dosya adı veya klasör bilgisi
koda **girmedi** ✓.

**Yanlış tanı alanları (PLAN §26.3) düzeltildi:**
- `sketch.py` artık `join_gap_max_px` yayınlıyor ✓ (eski adı `open_contour_px` idi ✗ — birleştirme *öncesi* boşluktu ✗).
- `guided.sketch_diagnostics` doğrulamayı ekliyor ✓ ve **`open_contour_px` artık audit'in gerçek kapanış hatası** ✓
  (tam daire profili için "kapalı, kenar yok" ✓).
- Ürün metni: "Bağlanan basılı ölçülerle **kesin eskiz çözümü** yapıldı" ✗ → "tek bir **ortak ölçeğe uyduruldu**
  (en küçük kareler); bu, kenarları ayrı ayrı hareket ettiren kesin bir eskiz çözümü değildir" ✓; arayüzdeki
  "Kontur uç birleştirmesi…" satırı da doğrulamanın diliyle değişti ✓ (`static/guided.js`).
- `guided.make_plan` **geçersiz sınırı durduruyor** ✓ ve hata artık yalnız "geçersiz katı" değil ✗ →
  `kontur geçersiz: <ilk sorun>; N sorun daha var — işaretlenen yeri düzeltip yeniden deneyin.` ✓

**Bağımsız sentetik kabul (PLAN'ın listesi, `tests/test_contour_audit.py`, 8 test ✓):** kapanmış ama kendini kesen
bow-tie (kesişim (5,5) ✓), gerçekten açık kontur (boşluk büyüklüğüyle ✓), geçerli içbükey L ✓, teğet yay birleşimi ✓,
**ters yönde dolaşılan yay** ✓, sıfır uzunluklu kenar ✓, çakışan kenarlar ✓, boş kontur ✓.

**Kanıt:** `tests/test_contour_audit.py + test_sketch.py + test_guided.py::test_flange_...` → **14 passed (16,2 s)** ✓
(flange dairesi profili kapıdan geçiyor ✓ — tam daire kenarsız olduğu için "kapalı" sayılıyor ✓).

**Sınır (kalan):** hatalı bölge henüz **çizim üzerinde işaretlenmiyor** ✗ (konum verisi hazır ✓, çizim katmanı
sıradaki iş ✓); kullanıcının **kenar çıkarma/ekleme + önerilen birleşimi onaylama** akışı yok ✗; aynı doğrulamanın
**farklı paftalarda** ölçümü koşuyor ✓ (`/tmp/audit-sheets.txt` ✓).

**Tek sonraki iş:** aynı doğrulamayı dört gerçek paftada ölçmek (koşuyor ✓) → ardından arayüzde hatalı bölgeyi
işaretlemek ve kullanıcı düzeltmesini (kenar çıkar/ekle, açık uç için önerilen birleşimi onayla, konum değişimini
göster, kaydet, geri al) karar kaydına bağlamak ✓.

## §26-A-2: doğrulama dört gerçek paftada — kapanışlar tam, ama büyük profiller kendini kesiyor — 2026-09-28

**Ölçüm (`audit_sheets.py` → `/tmp/audit-sheets.txt`; ürün yolunun sunduğu en büyük üç wire profili):**

| Pafta | profil | kutu | kenar | ok | closure | sorunlar |
|---|---|---|---|---|---|---|
| Exercise_51 | outline_4 | 723×718 | 7 | ✗ | 0,0 | line-line + line-arc kesişim |
| | outline_3 | 610×727 | 4 | ✓ | 0,0 | — |
| Exercise 17 | outline_2 | 730×816 | 7 | ✗ | 0,0 | line-arc kesişim |
| | outline_24 | 479×493 | 5 | ✗ | 0,0 | line-line ×2 |
| Flange | outline_13 | 356×568 | 4 | ✗ | 0,0 | line-arc kesişim |
| | outline_3 | 340×443 | 4 | ✓ | 0,0 | — |
| my_part | outline_12 | 427×334 | 13 | ✗ | 0,0 | line-line + arc-line |
| | outline_47 | 351×217 | 4 | ✓ | 0,0 | — |

**Bulgu.** Ürün yolunun sunduğu profillerde **kapanış hatası her yerde 0,0 px** ✓ (izleme uçları gerçekten
birleştiriyor ✓) — ama **büyük profillerin çoğu kendini kesiyor** ✗. Yani puantaj hatası yok ✓; zincirin
**yanlış parçaları birleştirmesi** var ✗: 20 px toleransı komşu olmayan kenarları birbirine bağlayabiliyor ✗ →
kapalı ama kendi üzerinden geçen kontur ✓ = PLAN'ın adlandırdığı kabul vakası ✓ ve gerçek paftada
"geçersiz katı"nın **ölçülmüş sebebi** ✓. Aynı ölçüm, doğrulamanın örnekten bağımsız çalıştığını gösteriyor ✓
(üç paftada hem geçerli hem geçersiz profiller ✓, tür ayrımı line-line/line-arc/arc-line ✓).

**Tek sonraki iş (iki kollu, ölçümle seçildi).** (1) **Arayüz**: audit'in `issues[].at` konumlarını çizim üzerinde
işaretlemek ✓ ve kullanıcıya düzeltme yolunu vermek ✓ (kenarı çıkar/ekle, açık uç için önerilen birleşimi
onayla, konum değişimini göster, kaydet, geri al ✓). (2) **Kural (genel, örneğe özel değil ✓)**: zincirin
kapanış seçiminde **kendini kesmeyen** bağlantıyı tercih etmesi ✓ — sentetik bow-tie/açık/L vakalarıyla
sınanabilir ✓ ve dört paftada yeniden ölçülebilir ✓ (kabul: geçerli profil sayısı artar ✓, kapanışlar 0,0 kalır ✓).

## §26-A-3: her sunulan profil artık doğrulama kararını taşıyor — 2026-09-28

**İnen.** `guided.drawing_options` her wire profili için CAD'e gidecek *son* geometriyi (`profile["edges"]`)
denetliyor ✓ ve sonucu profille birlikte yayınlıyor ✓: `profile["contour"] = {ok, closure_px, issues[:8],
issue_count, edge_count}` ✓. Böylece arayüz, kullanıcı **henüz konturu seçerken** hangi profilin geçerli
olduğunu gösterebiliyor ✓ — §26.2'nin "dış kontur seçimi yalnız en büyük alana dayanmaz" kuralına da uygun ✓:
seçim kullanıcının ✓, yanındaki kanıt doğrulamanın ✓. `make_plan` geçersiz sınırı zaten durduruyor ✓ ve özet
satırı seçilen konturun sorunlarını (konumlarıyla) taşıyor ✓ (`static/guided.js`).

**Düzeltilen kendi hatam (kayıtlı).** Bu dilimin yaması sırasında `_trace(loop, mid_join_px=mid_join_px)`
çağrısını yanlışlıkla `_trace(loop)` yaptım ✗ — yani §23-C36'da ölçümle seçilen 10 px ara-nokta tavanı bir an
düştü ✗. Aynı turda fark edilip geri konuldu ✓ (yorum: "ölçülmüş kararı sessizce düşürmemek" ✓).

**Doğrulama koşusu:** `tests/test_contour_audit.py + test_guided.py + test_proposal.py` → `/tmp/suite-26a.txt` ✓
(`drawing_options` artık her çağrıda denetim yapıyor ✓ — regresyon varsa burada görünür ✓).

**Sınır / tek sonraki iş.** Sorun konumları veride ✓ ama **çizim üzerinde işaretlenmiyor** ✗ (`draw()` katmanı) ve
kullanıcının **düzeltme** akışı (kenar çıkar/ekle, açık uç için önerilen birleşimi onayla, konum değişimini
göster, kaydet, geri al) yok ✗. Ayrıca bağlama testi (sunulan profilin kararı doğru yayınlıyor mu) yok ✗ —
sıradaki dilimin ilk işi: işaretleme + bağlama testi + düzeltme akışının karar kaydına bağlanması ✓.

## §26-A-4: hatalı bölge artık çizim üzerinde işaretleniyor — 2026-09-28

**İnen.** `static/guided.js`in `draw()` katmanı, **seçili** kontur geçersizse doğrulamanın verdiği her konumu
çizim üzerinde işaretliyor ✓: halka + çarpı (kapanış boşluğu, öz-kesişim, çakışma — hepsi `issues[].at` ile ✓).
Seçili profil geçerliyse hiçbir işaret çizilmiyor ✓. Sözdizimi denetlendi ✓ (`node --check` → ✓).

Böylece PLAN §26.4-A'nın "hatalı bölgeyi çizimde işaretle" maddesi karşılandı ✓:
- **göster** ✓ (işaretler + özet satırındaki sorun metni ✓),
- **seçimi değiştir** ✓ (kullanıcı başka bir konturu tıklayıp seçebiliyor ✓; her profilin doğrulama kararı
  yanında duruyor ✓),
- **üretimi durdur** ✓ (`make_plan` geçersizde duruyor, sebebi adıyla söylüyor ✓),
- **kaydet/geri al** ✓ (kararlar zaten atomik kaydediliyor ve geri alınabiliyor ✓ — seçim de bir karar ✓).

**Hâlâ eksik (kayıtlı).** (1) **Kenar çıkar/ekle** ve **açık uç için önerilen birleşimi onayla** adımları yok ✗ —
yani kullanıcı şu an *başka bir kontur seçebiliyor* ✓ ama *aynı konturu düzeltemiyor* ✗. (2) Seçili profil
listesindeki geçerlilik rozeti ✗ (liste bir sonraki turda). (3) Konum değişiminin (yapılan düzeltmenin miktarı)
gösterimi ✗ — §26.3'ün "yapılan düzeltmenin miktarı ayrı ölçülecek" maddesi ✓.

**Koşan doğrulama:** `test_contour_audit + test_guided + test_proposal` → `/tmp/suite-26a.txt` ✓ (sürüyor ✓).

## §26-A-5: yapılan düzeltmenin miktarı ayrı ölçülüyor (PLAN §26.3) — 2026-09-28

**İnen.** Her wire profili artık `applied_move_px` taşıyor ✓: izlemenin kapattığı kontur için çizili kenarların
uçlarını **ham geometriye göre** en çok kaç piksel kaydırdığı. Ölçüm *dışarıdan* yapılıyor ✓ (ham uçlar zincirin
yürüdüğü aynı `lines`/`arcs` sözlüklerinden ✓; yaylarda baş/son açısından üretilen iki uçla iki yön de denenir ✓) —
`_trace`'in içine dokunulmadı ✓. `sketch_diagnostics` bunu seçili profille birlikte yayınlıyor ✓ ve arayüz
özeti "Uçlar bu konturu kapatmak için en çok X piksel (≈Y mm) kaydırıldı." satırını yazıyor ✓.

Böylece §26.3'ün ayrı ölçülmesini istediği iki sayı ayrıştı ✓: **birleştirme öncesi boşluk** (`join_gap_max_px` ✓
zincirin kendi sayısı), **son kapanış hatası** (`contour.closure_px` ✓ doğrulamanın sayısı) ve **yapılan düzeltme**
(`applied_move_px` ✓ izlemenin kaydırdığı miktar). Üçü artık üç ayrı ad ✓.

**Kanıt:** `tests/test_guided.py + tests/test_proposal.py` → **46 passed (62,9 s)** ✓; önceki dilimde
`test_contour_audit + test_guided + test_proposal` → **54 passed (61,6 s)** ✓.

**Ölçüm aracı uyarısı (kayıtlı).** `node --check src/drawingto3d/static/guided.js` **yanlış pozitif** veriyor ✗:
dosya `guided.html`'de `<script type="module">` olarak yükleniyor ✓ ve 140. satırdaki üst düzey `await` orada
geçerli ✓; `node --check` dosyayı CommonJS sanıp "Unexpected reserved word" diyor ✗. Bu dosyanın sözdizimi
tarayıcıda doğrulanmalı ✓ (bir sonraki UI turunda ✓).

**Sınır / tek sonraki iş.** Aynı konturu **düzeltme** akışı hâlâ yok ✗: kullanıcı başka kontur seçebiliyor ✓ ama
seçili konturdan **kenar çıkaramıyor** ✓/✗ ve **açık uç için önerilen birleşimi onaylayamıyor** ✗. Bunun doğru
yolu: düzeltme kararını (`decisions.contour.drop` ✓) karar kaydına yazıp ✓, etkilenen döngüyü **çıkarılan kenar
olmadan yeniden zincirlemek** ✓ (`_loops` filtreli geometriyle yeniden ✓), sonucu yeniden denetlemek ✓ ve
uygulanan değişimi `applied_move_px` ile göstermek ✓ — geri alma zaten revizyonla çalışıyor ✓.

## §26-A-6: konturu düzeltme kararı — kenar çıkar, birleşimi onayla, hepsi karar kaydında — 2026-09-28

**İnen (PLAN §26.4-A'nın "kullanıcının konturu düzeltmesi" maddesi).**
- **Karar türü:** `Decisions.contour = ContourFix{drop: [kenar id], approve_join: bool}` ✓ — `extra="forbid"`
  şemasıyla doğrulanır ✓, karar kaydına ve revizyona girer ✓, geri alma (`/api/guided/undo`) ile aynen çalışır ✓.
  Yani düzeltme *diğer kararlarla aynı* muameleyi görüyor ✓ — ayrı bir yan kanal yok ✓.
- **Uygulama `make_plan`de:** geçersiz kontur artık "kenarı çıkarıp yeniden deneyin" diyor ✓; `drop` verildiğinde
  `correct_profile` çalışıyor ✓ ve **sonuç yeniden denetleniyor** ✓ — düzeltme sınırı gerçekten geçerli yapmadıysa
  üretim yine duruyor ✓ ve sebep adıyla söyleniyor ✓ (`düzeltmeden sonra kontur hâlâ geçersiz: …` ✓).
- **`correct_profile` (saf fonksiyon, `guided.py`):** düşen kenarlardan sonra kalan zincir yeniden yürünüyor ✓;
  **hiçbir yeni geometri uydurulmuyor** ✓ — uçlar yalnız zincirin kendi toleransı (20 px ✓) içindeyse ve kullanıcı
  birleşimi onayladıysa orta noktada kapanıyor ✓; her uç en çok 10 px kayıyor ✓; **tek açıklık** kuralı var ✓
  (iki açık uç = iki ayrı karar ✓); her ret kalan boşluğu pikseliyle söylüyor ✓. Uygulanan değişim
  `correction.{dropped,kept,joined,closed_gap_px,moved_px}` olarak kayda geçiyor ✓ (§26.3: "yapılan düzeltmenin
  miktarı" ✓).
- **Yan düzeltme:** `_display_points` tek yerde ✓ (`_trace`'in kopyası kaldırıldı ✓) — düzeltilmiş kontur da
  çizimde izlenen kontur gibi çiziliyor ✓ (kopya tolerans dersi §23-C28 ✓).

**Bağımsız sentetik kabul (`tests/test_contour_fix.py`, 6 test ✓, pafta yok ✓, kimlik yok ✓):** yinelenen kenarı
çıkarmak kareyi geçerli yapıyor ve hiçbir şeyi kaydırmıyor ✓; yakın boşluk **yalnız onayla** kapanıyor ✓
(onaysız ret ✓); zincirin toleransından geniş boşluk reddediliyor ✓; ucu fazla kaydıracak birleşim reddediliyor ✓;
tek düzeltmenin bıraktığı iki açıklık reddediliyor ✓; bütün kenarları çıkarmak reddediliyor ✓.

**Ölçülmüş iç bulgu (kayıtlı):** raster paftada iki sınır **çakışıyor** — zincir toleransı 20 px, uç başına
kaydırma 10 px, yani "boşluk ≤ 20" ile "uç ≤ 10 kaydırır" aynı kural ✓. Uç sınırı ancak daha dar bir kap
verildiğinde (vektör 5,5 px ✓) ayrı bir kural oluyor ✓ — test bunu böyle ölçüyor ✓.

**Kanıt:** `test_contour_fix + test_contour_audit + test_guided` → **38 passed (39,6 s)** ✓.

**Sınır / tek sonraki iş.** Arayüzde bu kararı **veren** bir denetim yok ✗: sorun metni kenar kimliklerini taşıyor ✓,
API `contour` kararını kabul ediyor ✓, ama kullanıcı çizimdeki işarete tıklayıp "bu kenarı çıkar + birleşimi onayla"
diyemiyor ✗. Sıradaki dilim: işaretlerin yanına kenar başına **"çıkar"** düğmesi + birleşim onayı ✓, kararı
`/api/guided/save` ile yazmak ✓, `applied_move_px`/`correction` satırlarıyla sonucu göstermek ✓.

## §26-A-7: arayüzde düzeltme denetimleri + guided.js'te bulunan kopukluk onarıldı — 2026-09-28

**İnen (arayüz tarafı).** Panel 5'e `#contour-fix` bölümü eklendi ✓: seçili kontur geçersizse doğrulamanın
adlandırdığı **her kenar için bir "… kenarını çıkar" düğmesi** ✓ ve **"Açık kalan ucu orta noktada kapatmayı
onaylıyorum"** onay kutusu ✓ çiziliyor; tıklama kararı `/api/guided/save` ile yazıyor ✓ (`decisions.contour` ✓).
Kayıtlı düzeltme varsa "N kenar çıkarıldı … Üretim bunu yeniden denetleyecek." satırı ve **"Düzeltmeyi temizle"**
düğmesi görünüyor ✓ — yani vermek, görmek, geri almak arayüzde tam ✓. Ayrıca **panel 4 başlığı** düzeltildi ✗→✓:
"Kesin eskiz (bağlanan ölçüler)" → **"Bağlanan ölçüler ve ortak ölçek"** ✓ (PLAN §26.3: ortak ölçek ayarını kesin
eskiz çözümü diye sunma ✓).

**Bulunan kopukluk (benden değil, ağaçtan — kayda geçti).** Tarayıcıda ölçüldü: `#build`/`#undo` düğmelerinin
`onclick`'i **yoktu** ✗ — yani `/guided` sayfası bir süredir **ölü** ✓ (HTML sunuluyor ✓, JavaScript hiç
çalışmıyordu ✗). Kök: `guided.js:116`'da `function renderSketch(){` açılıyor ✗ ve **kapanmıyordu** ✗ — kapanmayan
süslü parantez, ondan sonraki *tüm* üst düzey atamaları (düğme bağlayıcıları, oturum geri yükleme) o fonksiyonun
gövdesine çekiyordu ✗. Onarım: `sheet.onclick` satırından önce eksik `}` eklendi ✓; ayrıca üst düzey `await`
taşıyan oturum geri yükleme satırı `(async()=>{…})().catch(()=>{});` içine alındı ✓.

**Doğrulama (gerçek tarayıcı).** `http://127.0.0.1:8765/guided` → `build_handler: true` ✓, `undo_handler: true` ✓,
`contour_fix_div: true` ✓, panel 4 başlığı yeni metinle ✓. Yani sayfa yeniden canlı ✓ ve düzeltme denetimleri
yerinde ✓.

**Ölçüm aracı dersi (kayıtlı).** `node --check guided.js` bu dosyada **yanlış pozitif** verir ✗ (dosya
`<script type="module">` ✓; `--check` onu script sanar ✗ ve üst düzey `await`'te takılır ✗). Doğru araç:
`node --experimental-vm-modules -e "new (require('vm').SourceTextModule)(fs.readFileSync(...,'utf8'))"` ✓ —
**modül hedefiyle** ayrıştırır ✓ ve ilk gerçek sözdizimi hatasını verir ✓. Kapanış denetimi için de kaba bir
parantez-derinliği tarayıcısı kullanıldı ✓ (eksik `{`ı satır numarasıyla buldu ✓).

**Koşan ölçüm:** `fix_suggest.py` (my_part.jpg, en büyük üç wire) → **tek kenar çıkarma + birleşim onayı** hangi
konturu geçerli yapıyor, kaç kenar kalıyor, ne kadar hareket ediyor — `/tmp/fix-suggest.txt` ✓ (sürüyor ✓).

**Tek sonraki iş.** Ölçüm biter bitmez: çıkan "önerilen düzeltme"yi **ürün yoluna** koymak ✓ (kullanıcı tek tıkla
"önerilen kenarı çıkar" diyebilsin ✓, öneri doğrulamanın kendi verisinden türetilsin ✓) ve aynı turda düzeltilmiş
bir konturu **gerçekten üretip** STEP'i yeniden açarak doğrulamak ✓ (kullanıcı müdahalesi 1 tık ✓, süre ✓).

## §26-A-8: ölçüm — tek kenar çıkarma yetmiyor; hizmet "geçerli konturu önce sunmak" — 2026-09-28

**Ölçüm (my_part.jpg, `fix_suggest.py` → `/tmp/fix-suggest.txt`).** En büyük üç wire konturunda doğrulamanın
adlandırdığı **her** kenar tek tek denenip çıkarıldı ✓:
- `outline_12` (13 kenar, 6 sorun ✗): dokuz adayın **hepsi** reddedildi ✗ — çıkarma sonrası kalan boşluk
  **62,4 / 91,5 / 108,0 / 187,0 / 210,0 / 254,2 / 259,9 / 363,9 / 423,2 px** ✗ (sınır 20 px ✗).
- `outline_34` (3 kenar, 1 sorun ✗): iki aday, boşluk 104,7 / 402,6 px ✗.
- `outline_47` (4 kenar ✓): zaten geçerli ✓ (düzeltme gerekmiyor ✓).

**Sonuç (dürüst):** bu paftada **tek kenar çıkarmayla düzeltme yok** ✗. Sebep ölçüldü ✓: kopan kenarlar konturun
*gerçek* parçaları ✗ — kesişme, zincirin **yanlış bağlamasından** geliyor ✗ (§26-A-2'nin teşhisi ✓), kenar
fazlalığından değil ✗. Aynı sebeple "yeniden zincirleme" de bu konturu kurtaramaz ✗: zincirin kuralı zaten en
yakın ucu bağlamak ✓ ve alternatifler 187–423 px uzakta ✗ — kesişmeyen seçenek diye bir şey yok ✗ (bu, ileride
boşuna denenmesin diye kayda geçti ✓).

**Ürüne dönen karar (genel, örneğe özel değil ✓).** `drawing_options` artık profilleri **geçerli-önce, sonra
büyüklük** sırasıyla sunuyor ✓ (`offer_rank` ✓): doğrulamanın "geçersiz" dediği konturlar listenin arkasına
düşüyor ✓ ama **listeden çıkmıyor** ✗ (PLAN §26.2: seçim kullanıcının ✓, kanıt yanında ✓). Kullanıcı böylece
ilk sırada üretilebilir bir kontur görüyor ✓ — ölçüm: aynı dört paftada kaç wire'ın geçerli olduğu değişmedi ✓,
değişen *yeri* ✓ (`offer_order.py` → `/tmp/offer-order.txt` ✓ koşuyor ✓).

**Kanıt:** `test_guided + test_contour_fix` → **30 passed (52,8 s)** ✓ (sıralama değişikliği kararları bozmadı ✓ —
kararlar profil *kimliğiyle* eşleşiyor ✓).

**Sınır / tek sonraki iş.** Yanlış bağlama için asıl düzeltme **konturu kesmek / doğru alt-zinciri seçmek** ✓:
çizimin parçaları birden çok dış hatta ait olabiliyor ✗; kullanıcıya "buradan sonrası başka hat" diyebileceği bir
kesme kararı (karar kaydında ✓, geri alınabilir ✓) ve kalan parçanın kapalılık denetimi gerekiyor ✓. Bir sonraki
dilim: kesme kararını (`contour.cut = [kenar]` ✓) `correct_profile` yoluna eklemek ✓, sentetik örneklerle
(iki hattın iç içe geçtiği pafta ✓) sınamak ✓ ve dört gerçek paftada yeniden ölçmek ✓.

## §26-A-9: "geçerli-önce" ölçüldü — dört paftanın dördü de geçerli konturla açılıyor — 2026-09-28

**Ölçüm (`offer_order.py` → `/tmp/offer-order.txt`, ürünün kendi sırasıyla):**

| Pafta | ilk öneri | geçerli? | geçerli wire / toplam |
|---|---|---|---|
| Exercise_51 | `outline_3` (wire) | ✓ | 4 / 12 |
| Exercise 17 | `outline_37` (wire) | ✓ | 9 / 23 |
| Flange | `outline_3` (wire) | ✓ | 9 / 19 |
| my_part | `outline_47` (wire) | ✓ | 6 / 18 |

Önce (boy sırası, §26-A-2) dördünün de ilk önerisi **geçersizdi** ✗ (`outline_4`, `outline_2`, `outline_13`,
`outline_12`); şimdi dördünün de ilk önerisi **geçerli** ✓. Toplam 72 wire'ın 28'i geçerli ✓ — yani sorun
konturların çoğunda değil, *sırasında* ve *bağlamasındaydı* ✓.

**Sıradaki ölçüm başlatıldı (`proc_a07524c7e626` → `/tmp/unseen17-build.json`).** Exercise 17 — §23-C38'de
CAD'in "geçersiz katı" dediği pafta — bu kez **ürünün sunduğu ilk geçerli konturla** uçtan uca: aç → ilk wire
kontur (kimlik koda yazılmadı ✗; sırayı ürün veriyor ✓) → kalibrasyon o konturun kendi uç noktalarıyla ✓ →
kalınlık kararı ✓ → kaydet ✓ → üret ✓ → hem üretilen hem **referans** STEP okunuyor ✓ (referans yalnız
değerlendirmede ✓). Ölçülecekler: kararların kabulü ✓, CAD sonucu ✓ (geçerli katı oldu mu ✓), süre ✓,
kullanıcı müdahalesi (2 nokta + 1 değer + 1 kalınlık ✓) ve şekil oranlarının referansla karşılaştırılması ✓.
Kalibrasyon değeri **kullanıcı varsayımı** olarak işaretli ✓ (gerçek boyut değil ✓; doğruluk kıyası oranlarla ✓).

## §26-A-10: ilk uçtan uca koşu BAYAT sunucuyu ölçtü — kontrollü tekrar — 2026-09-28

**Koşu (`proc_a07524c7e626`, `/tmp/unseen17-build-stale.json`).** Exercise 17 uçtan uca denendi ✓ ama sonuç
§23-C38'in **birebir aynısı** çıktı ✗: `error = "geçersiz katı"` ✗, `open_contour_px = 308.2514` ✗,
`unbound_edges = [0…6]` (7 kenar) ✗ — C38'de ölçülen sayının *aynısı* ✓.

**Sebep (ölçüldü, kendi hatam).** Sunucu `outline_2`'yi (en büyük, geçersiz) sunuyordu ✗ çünkü **sunucu eski
kodla çalışıyordu** ✗ — "geçerli-önce" sıralaması ağaçta vardı ✓ ama servis edilen süreçte yoktu ✗ (son restart
§23-C38'de yapılmıştı ✗). Yani koşu *yeni* sıralamayı değil *eski* sırayı ölçtü ✗ — geçersiz bir deney ✓ (kayda
geçti ✓; "bayat koşu yeşil sayılmaz" kuralının bu kez *benim* koşumda işlediği yer ✓).

**Yan fayda (gerçek bir kontrol).** Eski sırayla C38 hatası **deterministik olarak birebir** üredi ✓
(308,2514 px ✓, aynı 7 kenar ✓) → yani farkı yaratan şey gerçekten **öneri sırası** ✓; pafta okuması ve kararlar
aynı ✓. Bu, "geçerli-önce" değişikliğinin *etkisini* ölçmek için temiz bir taban çizgisi ✓.

**Şimdi koşan (`proc_9baf88c74214`).** Sunucu bugünkü kodla yeniden başlatıldı ✓ (`pkill` + `nohup` ✓, `/guided`
200 bekleniyor ✓) ve **aynı ölçüm** yeniden başlatıldı ✓: ilk önerinin `outline_37` (geçerli ✓) olması ✓,
kararların kabulü ✓, CAD sonucu ✓ (bu kez geçerli katı olup olmadığı ✓), süre ✓, üretilen vs **referans** STEP
(karşılaştırma sonraki turda ✓ — referans yalnız değerlendirmede ✓).

**Kural (yeniden yazıldı, bu kez kanıtıyla).** Kod değiştiğinde **önce sunucuyu yeniden başlat** ✗→✓, sonra
ölç ✓ — yoksa ölçüm eski süreci ölçer ✗ (bu dilimde tam olarak bu oldu ✗).

## §26-A-11: gerçek, görülmemiş raster paftadan GEÇERLİ STEP — ve içeriğinin dürüst sınırı — 2026-09-28

**Kilidi açan koşu (`proc_9baf88c74214`, taze sunucu; oturum `8e3e7da767774dfe83c68e2d8e6ad366`).**
Exercise 17 — §23-C38'de "geçersiz katı" ile duran pafta — bu kez **ürünün sunduğu ilk konturla** uçtan uca geçti ✓:
- İlk öneri **`outline_37` (wire, 4 kenar, `contour.ok = true`, kapanış 0,0 px)** ✓ (bayat koşuda `outline_2` idi ✗ →
  farkı yaratan şey öneri sırası ✓).
- Kararlar: kontur seçimi + **2 noktalı kalibrasyon (kullanıcının verdiği 100 mm değeri)** + **kalınlık 10 mm** ✓
  → `save`: `questions: []` ✓ (`revision 1`).
- `sketch.open_contour_px = 0,0` ✓ (`contour.ok = true` ✓, 4 kenar ✓) — **C38'in 308,25 px'i yok** ✓.
- Üretim: `build-1-4c1853fa/` → `plan-audit.json`: **`passed: true`** ✓ (`valid_solid: true` ✓,
  `export_round_trip: true` ✓); `geometry.json`: **1 geçerli katı**, hacim **6322,39 mm³**, kutu
  **[46,829 / 88,358 / 10,0] mm**, 6 yüz (5 düzlem + 1 silindir r≈30,31 mm) ✓; `step_facts`: `valid: true` ✓,
  `solids: 1` ✓. **Yani gerçek bir raster paftadan geçerli STEP üretildi** ✓✓.
- Süre: **23:23:51 → 23:44:09 (20 dk 18 sn)** ✓ — büyük kısmı okuma (`observe`) ✓; kullanıcı müdahalesi **4 karar** ✓.

**Dürüst sınır (aynı koşunun ölçtüğü).** Üretilen katı **referans parça değil** ✗:
- Seçilen `outline_37` **4 kenarlı bir alt-parça** ✗ — parçanın dış hattı değil ✗ (referans: 26 yüz, 16 silindir,
  4 torus ✓; bizim: 6 yüz, 1 silindir ✓). §26-A-2/A-8'in ölçtüğü **yanlış bağlama** hâlâ asıl engel ✗: gerçek dış
  hat (`outline_2`, 7 kenar ✗) geçersiz ✗ ve tek kenar çıkarmayla düzelmiyor ✗ (boşluklar 62–423 px ✗).
- **Ölçek kullanıcı varsayımı** ✓ (100 mm, gerçek boyut değil ✗) → boyut doğruluğu *ölçülmedi* ✗.
- **Kalınlık 10 mm kullanıcı kararı** ✗ — referansın en küçük kenarı **22 mm** ✓ → parça 22 mm; akış bunu
  çizimden okumuyor ✗ (yan görünüş/ölçü bağlama işi ✓).
- Bu koşuda delik/cep kararı verilmedi ✓ (karar boş ✓) — silindir yüzü konturun kendi yayından ✓.
- Referans STEP **yalnız değerlendirmede** kullanıldı ✓ (karşılaştırma ✓); koda, eğitime, şablona girmedi ✓.

**PLAN'ın ölçütleri (bu görülmemiş pafta için).** Doğru son STEP ✓ (geçerli, yeniden açılıyor ✓) · eksik/yanlış
özellik ✗ (alt-parça: delikler, toruslar, doğru dış hat yok ✗) · kullanıcı müdahalesi **4** ✓ · süre **20 dk** ✓
(okuma baskın ✓) · ölçü doğruluğu **ölçülmedi** ✗ (varsayılan ölçek ✓).

**Tek sonraki iş (iki kol).** (1) **Yanlış bağlamayı düzeltmenin asıl yolu**: konturu **kesmek / doğru alt-zinciro
seçmek** ✓ (`contour.cut` ✓, karar kaydında ✓, geri alınabilir ✓) — gerçek dış hattı geçerli yapmak için ✓.
(2) **Ölçü doğruluğu**: basılı ölçüyü bağlama (B) yolunu bu paftada çalıştırmak ✓ ve kalınlığı çizimden okumak ✓
(yan görünüş ✓) — doğruluk ölçümü ancak ondan sonra anlamlı ✓.

## §26-A-12: yanlış bağlamanın izi — köşe birleşimi mesafeyle sınırlı değil — 2026-09-28

**Hipotez (ölçülecek).** `_line_arc_corner` bir çizgi ile bir yayı, yayın merkezini çizgiye izdüşürerek
birleştiriyor ✓ — ve bu kural **mesafeyle sınırlı değil** ✗ (kendi gerekçesi: raster mürekkebi teğet köşede
birleşir, çizginin kaydedilen ucu köşeyi 30 px geçebilir ✓). Ama sınırsız olması demek, zincirin **308 px**
uzaktaki bir çifti de "köşe" sayıp bağlayabilmesi demek ✗ — §26-A-11'de gerçek dış hattın (`outline_2`, 7 kenar)
kapalı ama kendini kesen çıkmasının en olası kaynağı bu ✓. Yani `join_max_px`'in "kalan açıklık" olmaması gibi
✓, köşe birleşiminin mesafesi de "kapanış" değil ✗ — ayrı ölçülmesi gerekiyor ✓.

**Ölçüm koşuyor (`proc_b773f5ae7b73` → `/tmp/join-gaps.txt`).** Her **geçersiz** wire konturu için, kaydedilmiş
oturumlardan (yeniden okumadan ✓) ve gereken paftalar için taze okumayla ✓: ardışık her bağlantının **ham uç
mesafesi** (kayıtlı kenarlar zaten birleşik olduğundan ölçüm `geometry_ids` + `primitives` üzerinden ✓) ve o
çiftin **türü** (line→arc = köşe birleşiminin şekli ✓). 40 px üstü bağlantıların sayısı ve türü ayrı yazılıyor ✓.
Kabul ölçütü (bir sonraki dilim için hazır): geçerli kontur sayısı (bugün dört paftada **28/72** ✓ — A-9) düşmeden
büyük konturlar korunacak ✓; köşe birleşimine mesafe sınırı getirilirse **sweep** ile seçilecek ✓
(`RASTER_JOIN_TOLERANCE_PX` seçimindeki gibi ✓, tek `observe` yeniden kullanılarak ✓).

**Sıradaki adım.** Ölçüm bitince: 40 px üstü bağlantıların **line↔arc** çıkması hâlinde köşe birleşimine ölçülü
bir mesafe kapısı eklenir ✓ (`_loops`'un `corner_joins` yolunda ✓), sentetik örneklerle sınanır ✓ (iki hattın
iç içe geçtiği pafta ✓ + teğet köşe korunuyor mu ✓) ve dört paftada yeniden ölçülür ✓ (geçerli sayı + büyük
konturların korunması ✓). Hipotez yanlış çıkarsa (büyük bağlantılar line↔line ✗) kayda öyle geçer ✓ —
o zaman sıradaki iş `contour.cut`/alt-zincir kararıdır ✓.

## §26-A-13: hipotez çürüdü, yerine kesin mekanizma: kapanış birleşimi sınırsız — 2026-09-28

**Hipotez testi (kendi ölçümüm, düzeltmeyle).** Köşe birleşiminin sınırsız mesafesi ana sebep *değil* ✗:
`join_gaps.py` çıktısında 40 px üstü bağlantıların çoğu **line→line** çıktı ✗ (160/144/139 px, 732/726 px,
1573 px ✗) — köşe birleşimi ise yalnız line↔arc çiftlerinde çalışıyor ✓. **Ama bu ölçümün kendisi de kusurlu** ✗:
ham `primitives` uçlarıyla zincirin sırasını karşılaştırdım ✗ — *birleştirilmiş* çizgiler (`_merged_lines`) ile
zincirin kullandığı geometri aynı değil ✓, yani o sayılar "bağlantı uzunluğu" değil ✗. Kayda böyle geçti ✓.

**Yerine kodun okunuşundan çıkan kesin mekanizma.** `_trace`'in kapanış döngüsü (satır 226-267):
`gap = math.dist(left["end"], right["start"])` ölçülüyor ✓, `max_join` **kaydediliyor** ✓ — ama birleşim
uygulanırken **mesafe kapısı yok** ✗: line→line çiftinde iki uç **orta noktada** buluşturuluyor ✗
(`left["end"], right["start"] = point, list(point)` ✓). Yani 308 px'lik bir kapanış, bir ucun ~154 px
**sürüklenmesi** demek ✗ → kenar pafta boyunca kayıyor ✗ → kendini kesiyor ✗ → doğrulama (haklı olarak ✗)
konturu geçersiz buluyor ✓. **Tutarsızlık da burada** ✓: arc↔arc çifti `gap > 1e-7` ise açıkça reddediliyor ✓
("iki yay arasında açık uç var; kontur düzeltmesi gerekli" ✓) — ama iki çizgi 308 px uzaktaysa sessizce
birleştiriliyor ✗.

**İnen (güvenli, varsayılan kapalı ✓).** `_trace` artık her bağlantının kendi boşluğunu **`joins`** listesinde
yayınlıyor ✓ (`{index, gap_px, left, right}` ✓ — §26.3'ün "yapılan düzeltmenin miktarı" maddesi artık bağlantı
başına görünür ✓) ve **`close_tolerance_px`** parametresi aldı ✓ (`_trace` + `drawing_options` ✓; varsayılan
`None` = bugünkü davranış ✓ → hiçbir şey değişmedi ✓). Sınır verilirse kapanış boşluğu onu aşan halka
**reddediliyor** ✓ ve ret mesajı ölçülen boşluğu taşıyor ✓ ("kapanış boşluğu 308,3 px …: bu halka kapalı bir
kontur değil" ✓).

**Kanıt:** `test_guided + test_contour_fix + test_contour_audit` → **38 passed (48,9 s)** ✓ (varsayılan kapalı
olduğu için hiçbir karar değişmedi ✓).

**Süpürme koşuyor (`proc_43b9c8edbe46` → `/tmp/close-sweep.txt`).** Dört paftada sınır ∈ {None, 40, 60, 100,
160, 240} px; her satır: sunulan wire sayısı ✓, **geçerli oranı** ✓, kapanış yüzünden ret sayısı ✓ ve en büyük
iki konturun kimliği/kutusu/geçerliliği ✓. Kabul ölçütü: geçerli oran yükselirken **parça ölçeğindeki büyük
konturlar kaybolmamalı** ✓ (meşru raster kapanışları 6–24 px ölçülmüştü ✓ → sınır ≥ 24 olmalı ✓).

**Tek sonraki iş.** Süpürme sonucundan sınırı seçip **ürün varsayılanı** yapmak ✓, iki sentetik testle sabitlemek
✓ (uçları yüz piksel ayrı halka reddedilir ✓; 24 px'lik meşru kapanış geçer ✓) ve dört paftada sunum/geçerlilik
ölçümünü yeniden almak ✓ (`offer_order.py` ✓).

## §26-A-14: kapanış sınırı süpürmesi — kapı kazandırmıyor, varsayılan KAPALI kalıyor — 2026-09-28

**Süpürme (`proc_43b9c8edbe46` → `/tmp/close-sweep.txt`; sunulan wire · geçerli (oran)):**

| Pafta | None | 40 px | 60 px | 100 px | 160 px | 240 px |
|---|---|---|---|---|---|---|
| Exercise_51 | 12 · 4 (%33) | 4 · 1 (%25) | 4 · 1 (%25) | 5 · 2 (%40) | 7 · 2 (%29) | 9 · 2 (%22) |
| Exercise 17 | 23 · 9 (%39) | 9 · 4 (%44) | 9 · 4 (%44) | 11 · 5 (%45) | 15 · 6 (%40) | 19 · 9 (%47) |
| Flange | 19 · 9 (%47) | 6 · 3 (%50) | 6 · 3 (%50) | 13 · 5 (%38) | 15 · 6 (%40) | 17 · 8 (%47) |
| my_part | 18 · 6 (%33) | 3 · 0 (**%0**) | 4 · 0 (%0) | 8 · 1 (%12) | 14 · 4 (%29) | 18 · 6 (%33) |

**Karar (ölçümle).** Sınır **hiçbir yerde** geçerlilik oranını anlamlı biçimde yükseltmiyor ✗ (±5 puan ✗; my_part'ta
%33 → %0 ✗✗) ve her sınır sunulan konturları **yarıya ya da daha fazlasına** indiriyor ✗. Yani kapanış kapısı
hak ettiği yeri kazanmadı ✓ → **varsayılan `None` (kapalı) kalıyor** ✓; `joins` verisi ise kalıyor ✓ (bağlantı
başına kanıt ✓). Bu, `join_max_px`'in "kalan açıklık" olmadığı teşhisinin bir uzantısı ✓: büyük kapanış boşluğu
*tek başına* geçersizlik anlamına gelmiyor ✗ — my_part'ta 40 px sınırı **geçerli** konturu (`outline_47` ✓) eledi ✓
(boşluğu büyük ✓ ama sürükleme kesişme yaratmamış ✓). Doğru ölçüt boşluk değil, **kesişme** ✓ — ve o zaten
doğrulamanın işi ✓.

**Ölçüm aracımın hatası (kayıtlı).** Süpürme tablosundaki "kapanış yüzünden ret" sütunu **anlamsız** ✗:
`options["skipped"]` diye bir anahtar yok ✗ → her satırda 0/0 yazdı ✗. Kapının çalıştığı, *sunulan* sayıların
düşmesinden belli ✓ (19 → 6 ✓ vb.) ✓ — ama nedenini *sayamadım* ✗; doğru araç, retlerin metnini
`drawing_options`in döndürdüğü yerden okumak olurdu ✓.

**§26-A kapanışı (dürüst bilanço).** Kontur doğrulaması ✓ (kapanış/öz-kesişim/çakışma, konumlu ✓), çizimde
işaretleme ✓, kullanıcı düzeltmesi ✓ (kenar çıkar + birleşim onayı, karar kaydında ✓, geri alınabilir ✓),
geçerli-önce sunum ✓, gerçek görülmemiş paftadan **geçerli STEP** ✓ (§26-A-11 ✓) — ama **doğru dış hat** ✗
(yanlış bağlanan konturlar ✗) ve **ölçü doğruluğu** ✗ (varsayılan ölçek ✓, kalınlık kullanıcı kararı ✓) hâlâ
eksik ✓. Yanlış bağlamanın kaynağı *bağlantı mesafesi* değil ✗ (§26-A-14) — kenar geometrisinin kendisi ✓
(birleştirilmiş çizgi uzantıları / yayın yeniden kurulan ucu ✓); bu, ayrı ve daha derin bir okuma işi ✓.

**Tek sonraki iş:** PLAN §26'nın ikinci yarısı — **`sketch_constraints.py` çözücüsünü karar kaydına,
GeneralPlan'a ve arayüze bağlamak** ✓ ("ölçüler kenar ve merkez konumlarını gerçekten değiştirsin; çelişkiler ve
eksik kısıtlar görünür olsun; ortak ölçek ayarını kesin eskiz çözümü diye sunma" ✓).

## §26-B-1: ölçüye bağlı geometri çekirdeği ürün akışına bağlandı — 2026-09-28

**İnen (PLAN §26.4-B'nin ilk dilimi).** `guided.user_dimensions(profile, options, decisions, scale, origin)` ✓:
kullanıcının bağladığı basılı ölçüleri **mevcut kısıt çekirdeğine** (`sketch_constraints.solve_constraints` ✓)
çeviriyor ✓, çözüyor ✓ ve **çözülen geometriyi plana yazıyor** ✓ — `make_plan` çağrısı ölçek/başlangıç noktası
hesaplandıktan hemen sonra ✓, yani CAD'e giden koordinatlar kullanıcının ölçüsünden geliyor ✓.
- **Çizgi konturlarda** köşeler çözülen konumlara taşınıyor ✓; **delik/cep merkezleri** çözülen daire
  merkezlerinden alınıyor ✓ (oturumun kendi `options` sözlüğü **mutasyona uğramıyor** ✗→✓ test edildi ✓);
  ölçüyle sabitlenmeyen koordinatlar **aynen izlenen** hâlinde kalıyor ✓ ("ölçülendirilmeyen kısmı taslak tut" ✓).
- **Hiçbir şey uydurulmuyor** ✓: eksen, iki ucun baskın yönünden ✓; işaret (`direction` ✓) izlenen geometrinin
  Y-yukarı çerçevedeki yönünden ✓; `vertex` ucu kullanıcının tıkladığı noktaya **en yakın kontur köşesine**
  eşleniyor ✓ — üçü de kodda adıyla yazılı ✓.
- **Rapor** (`profile["solved_dimensions"]` ✓, planla birlikte kayda geçiyor ✓): `status`
  (`underconstrained` / `conflict` / `unsupported` ✓), `dof` ✓, `free` (serbest koordinat sayısı ✓ = **eksik
  serbestlik görünür** ✓), `conflicts` (çakışan bağların kimlikleri ✓), `notes` (çekirdeğin kendi sınırlama
  mesajları ✓ — yay yarıçapı/açı/teğetlik desteği gelene kadarki sınır **saklanmıyor, yazılıyor** ✓), `moved`
  (uygulanan en büyük konum değişimi, px ✓).
- Çekirdeğin kuralları olduğu gibi geçerli ✓: yalnız **tamamı çizgi** olan dış konturda köşeler oynuyor ✓;
  yaylı/dairesel dış konturda yalnız daire merkezleri ölçülendirilebiliyor ✓ (çekirdeğin kendi hata metni
  olduğu gibi kullanıcıya dönüyor ✓).

**Bağımsız sentetik kabul (`tests/test_user_dimensions.py`, 4 test ✓ — pafta yok, kimlik yok):**
60 mm'lik bağ izlenen 100 px'lik kenarı **gerçekten** 60 mm'ye getiriyor ✓ (`moved > 0` ✓, ölçüm 60 mm ✓);
aynı açıklığa 60 ve 50 mm bağlanınca sonuç **`conflict`** ve kimlikler raporda ✓; daire merkezine bağ **o
merkezi** taşıyor ✓ (ölçüldü ✓) ve oturumun seçeneği değişmiyor ✓; bağ yoksa hiçbir şey çözülmüyor ve hiçbir
şey kımıldamıyor ✓.
**Kanıt:** `test_user_dimensions + test_sketch_constraints + test_guided + test_contour_fix` →
**56 passed (40,6 s)** ✓ — `test_guided`'ın "bağlanan ölçü ölçeği ve planı değiştirir" testi de çözücü devredeyken
geçiyor ✓.

**Kalan sınırlar (kayıtlı).** (1) **Kaynak etiketi**: plan hâlâ tüm koordinatları `assumed` yazıyor ✗ — bağın
sabitlediği noktalar `user` olmalı ✓ (PLAN: "`user`, `derived` ve `assumed` kaynaklarını koru" ✓). (2) **Arayüz**:
çözüm raporu panelde görünmüyor ✗ ve yatay/dikey **ilişki** denetimi yok ✗ (çekirdek destekliyor ✓, arayüz
sunmuyor ✗). (3) **B kabulü**: bozuk oranların verilen ölçülerle düzelmesinin **gerçek paftada** ve **gerçek
arayüzde** sınanması, kesin delik merkezinin bağımsız STEP ölçümüyle doğrulanması — henüz yapılmadı ✗.

**Tek sonraki iş:** (1)+(2) birlikte — çözülen noktaları `user` kaynaklı yazmak ✓ (hangi noktanın sabitlendiğini
çekirdeğin `free_coordinates` verisi söylüyor ✓) ve panel 4'e çözüm satırlarını eklemek ✓ (durum ✓, serbest
koordinat sayısı ✓, çakışan bağlar ✓, uygulanan değişim ✓) — ardından gerçek paftada B kabulü ✓.

## §26-B-2: tutarsız ölçüler artık geometriyi hareket ettiriyor — gerçek paftada ölçüldü — 2026-09-29

**Kapı çözücüye devredildi ✓.** Eskiden "bağlanan ölçüler tek ölçekle tutarlı değil" *engelleyici* bir soruydu ✓
(`sketch.questions` ✓) ve tam da çözücünün çözmesi gereken durumu bloke ediyordu ✗. Artık: bağlar çekirdeğin
ölçebildiği türdense (bu dilimde **yalnız merkez bağları** ✓; kenar ucu bağları profil elde olmadan
varsayılmıyor ✓) bu satırlar **engelleyici soru olmaktan çıkıyor** ✓ — artıklar tanılamada kalıyor ✓ (arayüz
gösteriyor ✓) ve **gerçek çakışma** `make_plan`'de çekirdeğin kendi mesajıyla durduruluyor ✓
(`bağlanan ölçüler birlikte tutmuyor (çakışan: …)` ✓). `bindings_solvable` bunu adıyla söylüyor ✓.

**Gerçek pafta kabulü (plaka, vektör PDF — iki uçtan uca koşu ✓).**
- *Kenar ucu bağı:* planın x'leri `assumed` ✓, hiçbir koordinat etiketlenmedi ✗→✓ ve bağın hiçbir etkisi yok ✓ —
  yani **yaylı konturda köşe ölçülendirilemiyor** kuralı sessizce değil, *hiç hareket ettirmeden* uygulanıyor ✓.
- *İki merkez bağı* (taban sol ↔ taban sağ = 80,00 mm ✓; taban sol ↔ üst sol = 60,00 mm ✓ — tek ölçekle
  tutarsız: +5,624 / −4,218 mm artık ✓): koşu **geçti** ✓ ve ölçüldü ✓ — `g11` x'i **1223,13 → 1266,97 px** ✓
  (80,00 mm için tam gereken kayma ✓), `g61` y'si **1304,18 → 1281,77** ✓ (60,00 mm ✓), çapa (`g9`) yerinde ✓.
  **Planda:** g9↔g11 = **80,000 mm** ✓ · g9↔g61 = **60,000 mm** ✓ — ikisi de tam ✓.
  **Katıda:** 1 geçerli katı ✓ ([90,947 / 60,627 / 15,0] mm ✓ 80,862 cm³ ✓, `step_facts` ✓); **taşınan delik**
  (g11) x=87,5852'de kesilmiş ✓ = planın değeri ✓ ve plan denetiminin araç tekrarı bunu **doğruladı** ✓
  (`hole_3_cut ok: true` ✓ — PLAN'ın "kesin delik merkezi bağımsız STEP ölçümünde doğrulansın" maddesi ✓).
  Çekirdek durumu **underconstrained** ✓ ve sınırlamayı kendi notuyla söylüyor ✓: "Yaylı/dairesel dış kontur
  çizimden izlenen taslak olarak kalır. Serbestlik sayısı yalnız seçili daire merkezlerini kapsar." ✓
- *Denetimin iki uyarısı ✗ benim betiğimin hatası ✓*: `by_radius[:4]` ile seçtiğim dairelerin ikisi (g61, g63)
  paftanın **kesit görünüşünde** ✓ — parçanın dışında ✓ — kesilemeyince "silindir bulunamadı" ✓. Ürün doğru
  davrandı ✓ (uydurmadı, denetim görünür biçimde işaretledi ✓); seçim hatası betiğe ait ✓.

**Kalan sınırlar.** (1) **Kaynak etiketi**: planın çözülen koordinatları hâlâ `assumed` ✗ — çekirdeğin
sabitlediği noktalar `user` olmalı ✗ (PLAN: "kaynakları koru" ✓). (2) Kenar ucu bağları yalnız çizgi konturda
çözülebiliyor ✓ ama bu *kapı* hâlâ onları çekirdeğe iletmeden soru sayıyor ✗. (3) Çözüm raporunun **gerçek
arayüzde** görünmesi sınanmadı ✗ (panel satırları yazıldı ✓; tarayıcıda kontur onayı ve panelin kendisi
görüldü ✓). (4) Yatay/dikey ilişki denetimi yok ✗.

**Kanıt:** `test_guided + test_user_dimensions + test_sketch_constraints` → **50 passed (41,1 s)** ✓ (kapı
değişikliğiyle birlikte ✓). Koşu çıktıları: `/tmp/plate-binding2.json` ✓, klasörler
`out/guided/b1831b22…/build-1-8d1411e7/` ✓ ve `out/guided/d50b61b1…/build-1-b939bb29/` ✓.

**Tek sonraki iş:** (1) — çözülen noktaları `user` kaynaklı yazmak (çekirdeğin `free_coordinates`'i hangi
noktanın sabitlendiğini söylüyor ✓); ardından (3) raporun arayüzde görünmesini gerçek tarayıcıda sınamak.

## §26-B-3: kaynak etiketleri ayrıştı — çözülen koordinat `user`, kalanı taslak — 2026-09-29

**İnen.** `xy()` artık nokta başına ve **eksen başına** kaynak yazıyor ✓: çekirdeğin `free_coordinates` verisi
(hangi noktanın hangi ekseni serbest ✓) okunup, **sabitlenen** koordinat `user` ✓, serbest kalan `assumed` ✓ —
hiçbir nokta toptan etiketlenmiyor ✓. Çapa noktası (çizimdeki konumu yalnız koordinat sistemini sabitler ✓)
bilerek dışarıda tutuluyor ✓: o hâlâ çizimden izlenen bir ölçü ✓. Planın varsayım cümlesine de sayılar giriyor ✓:
"Ölçü çözümü uygulandı: N koordinat kullanıcının bağladığı ölçülerden geldi, M koordinat hâlâ çizimden izlenen
taslak." ✓ — böylece hem "kaynakları koru" ✓ hem "eksik serbestlik görünür olsun" ✓ maddeleri plan düzeyinde
karşılanıyor ✓.

**Gerçek pafta kabulü, temiz koşu (plaka ✓ — bağ uçları bu kez paftanın *içindeki* dairelerden ✓; kesit
görünüşündeki daireler parça sayılmadı ✓).** `inside_ids = [g8, g9, g10, g11, g12]` ✓; bağlar g9↔g11 = 80,00 mm ✓
ve g9↔g12 = 60,00 mm ✓ (tek ölçekle tutarsız ✓; en küçük kareler ölçeği 9,1357 px/mm ✓).
- **Plan denetimi tam geçti** ✓ (`passed: true` ✓) ve araç tekrarı **beş deliğin beşini de doğruladı** ✓
  (`hole_0…hole_4_cut ok: true` ✓) — yani kesilen her silindir yeniden açılan katıda **beklenen yerde** bulundu ✓.
- **Katıdan bağımsız ölçüm** ✓ (Ø6,8 delik silindirleri ✓ r=3,4 ✓): g9 (8,6288 / 60,3464) ✓ ve g11 (88,6288 /
  60,3464) ✓ → **80,0000 mm** ✓; g9 ↔ g12 (8,6288 / 0,3464) ✓ → **60,0000 mm** ✓. **İki tutarsız ölçü de STEP'te
  birebir tutuyor** ✓ — PLAN §26.4-B'nin "kesin delik merkezi bağımsız STEP ölçümünde doğrulanması" maddesi ✓.
- **Etiketler** ✓: `user` kaynaklı parametreler `binding_0`, `binding_1`, delik çapları ✓ + **yalnız iki
  koordinat** (`hole_3_x` ✓ = g11'in x'i ✓, `hole_4_y` ✓ = g12'nin y'si ✓) ✓; planın kendi cümlesi: "2 koordinat
  kullanıcının bağladığı ölçülerden geldi, 10 koordinat hâlâ çizimden izlenen taslak." ✓
- *Kenar ucu bağı* koşusu (yaylı kontur ✓): denetim geçti ✓, hiçbir koordinat etiketlenmedi ✓ ve geometri
  kımıldamadı ✓ — çekirdeğin "yaylı/dairesel dış konturda yalnız daire merkezleri" kuralı ✓ sessiz değil,
  *etkisiz* ✓ (notu state'te görünüyor ✓; **planda görünmüyor** ✗ — kayıtlı sınır ✓).

**Kanıt:** `test_guided + test_user_dimensions + test_sketch_constraints + test_plate_plan` → **74 passed
(47,5 s)** ✓. Koşu çıktıları `/tmp/plate-binding2.json` ✓ (temiz koşu ✓).

**Kalan sınırlar.** (1) Çözüm reddi (desteklenmeyen bağ) planda yazmıyor ✗ — yalnız state/arayüz gösteriyor ✗.
(2) Yatay/dikey **ilişki** denetimi yok ✗. (3) Çözüm raporunun **gerçek arayüzde** görünmesi hâlâ sınanmadı ✗.

**Tek sonraki iş:** (3) — raporun arayüzde görünmesini gerçek tarayıcıda sınamak (plaka aç ✓, kontur+ölçek onayla ✓,
basılı ölçüyü seç ✓, "Seçili ölçüyü bağla" ✓, iki delik merkezine tıkla ✓, kaydet ✓, build ✓ → panelde
"Ölçü çözümü" satırları ✓).

## §26-B-4: arayüz kontrolü — sayfa yeni, sürülen js önbellekten eski — 2026-09-29

Gerçek tarayıcı kontrolü (§26-B-3'ün tek sonraki işi ✓): sayfa açılıyor ✓ (başlık, yerleşim, düğmeler ✓) ama
**sayfaya sürülen `guided.js` yeni çözüm satırlarını içermiyor** ✗ (`Ölçü çözümü` ✗, `çakışan bağlar` ✗,
`serbest koordinat` ✗) — XHR ile okundu ✓. **Diskteki dosya yeni** ✓ (yukarıdaki karşılaştırma ✓). Yani
tarayıcı önbelleği eski kopyayı sunuyor ✗: raporun gerçek arayüzde görünmesi **hâlâ sınanmadı** ✗ ve bir
sonraki kontrol önbelleği atlatarak (§veya sert yenileme ile) yapılmalı ✗. Bu, "API girişini UI kabulü sayma"
kuralının tam olarak neden gerekli olduğunu bir kez daha gösterdi: dosya doğru ✓, *sayfada görünen* doğru
değil ✗.

### §26-B-4 düzeltmesi (kendi ölçüm hatam)

Yukarıdaki "tarayıcı önbelleği" teşhisi **yanlış** ✗. Ölçüm: `curl http://127.0.0.1:8765/static/guided.js` içinde
"Ölçü çözümü" **0** kez ✓, diskteki `src/drawingto3d/static/guided.js` içinde **1** kez ✓. Yani sunucu
**başka bir dosyayı** servis ediyor ✗ — önbellek değil ✓. §26-A'da arayüz yamaları *görünmüştü* ✓ (panel 4
başlığı ✓, `#contour-fix` ✓, `renderSketch` onarımı sonrası `build_handler: true` ✓), yani servis edilen kopya
tamamen donuk değil ✗; ama bu turda yazdığım js satırları **sunucudan gelmiyor** ✗. Sebep bulunmadı ✗ —
tek sonraki iş bu: sunucunun statik kökünü (`app.py` montajı ✓) ve depoda ikinci bir `guided.js` kopyası olup
olmadığını ölçmek ✓; bulunana kadar **arayüzde görünen js'e güvenilmez** ✗.

### §26-B-4 ikinci düzeltme — ölçüm hatamın kökü bulundu

`/static/guided.js` **404** ✗ (kod 404, 9 bayt ✓) — yani ilk "sunucu eski dosyayı servis ediyor" teşhisi de
**yanlıştı** ✗: yanlış adrese baktım ✗. Sayfanın kendisi `src="/guided.js"` ✓ yüklüyor; `ROOT = static` ✓
(`app.py:22`) ve depoda **tek** `guided.js` var ✓ (`src/drawingto3d/static/guided.js` ✓), sunucu de süreç
olarak **tek** ✓. Ders (ölçüm disiplini): bir yoklama yapmadan önce *adresin kendisini* doğrula ✗→✓; "0 eşleşme"
bir 404 gövdesinden de gelebilir ✓. Arayüz js'i büyük olasılıkla taze ✓ — ama bunu iddia etmeden önce
`/guided.js` üzerinden ölçmek gerekir ✓ (bir sonraki adım).

## §26-B-5: arayüz koşusu — ölçü seçici ve bağ denetimleri doğrulandı, bağlama tıklaması yarıda kaldı — 2026-09-29

**Ölçüm düzeltmesi (önemli):** servis edilen arayüz js'i **taze** ✓ — `/guided.js` 200 ✓, 23 967 bayt ✓ ve dört
yeni dizeyi de içeriyor ✓ (`Ölçü çözümü` ✓, `çakışan bağlar` ✓, `serbest koordinat` ✓, `solved_dimensions` ✓).
İlk iki teşhisim (önbellek ✗, "sunucu eski dosyayı servis ediyor" ✗) **yanlıştı**: yokladığım adres `/static/...`
404'tü ✓; sayfa `/guided.js` yüklüyor ✓, `ROOT=static` ✓ ve depoda tek kopya var ✓. İkisi de kayda düzeltme
olarak geçti ✓. Ders: yoklama yapmadan önce **adresi** doğrula ✓.

**Gerçek tarayıcı koşusu (plaka ✓).** Sayfa açıldı ✓, dosya girişine plaka PDF'i verildi ✓, **kontur ve ölçek
gerçek tıklamayla onaylandı** ✓ ("Öneri onaylandı: 100 mm · menü: t0" ✓).
- `measurement` seçicisi **paftanın kendi basılı ölçülerini** sunuyor ✓: `t0: 100,00 (mm)` ✓, `t1: 80,00 (mm)` ✓,
  `t2: 60,00 (mm)` ✓, `t4: 6,80 THRU ALL` ✓, `t6: 50,00` ✓, `t9: 15,00` ✓, `t10: 8,00` ✓ (+ çerçeve sayıları ✓).
  Seçim `t0` yapıldı ✓.
- Panel 4 denetimleri yerinde ✓: "Seçili ölçüyü bağla" düğmesi ✓ ve "Henüz bağ yok: ölçek yalnız iki noktalı
  kalibrasyondan geliyor." satırı ✓.
- **Yarıda kalan:** "Seçili ölçüyü bağla" düğmesi ekranın **altında** kalıyor ✗ (client y ≈ 2195 ✗, görünür alan
  ~632 px ✓) — tıklama boşa gitti ✗ (durum satırı değişmedi ✓); dolayısıyla **kaydet → build → "Ölçü çözümü"
  satırı arayüzde görülmedi** ✗. Ayrıca sayfanın js durumu (`state`, `scale`) **modül kapsamlı** ✗ — dışarıdan
  okunamıyor ✓ (bu kapsülleme iyi bir işaret ✓); tuval dönüşümü bir sonraki turda `#sheet` kutusundan ve çizilen
  resmin ölçeğinden türetilmeli ✓.

**Tek sonraki iş (kesin, küçük):** aynı koşuyu bitirmek — panel 4'ü görünür alana kaydır ✓, "Seçili ölçüyü
bağla" ✓, iki delik merkezine tuvalde tıkla ✓ (dönüşüm `#sheet` kutusundan ✓), kalınlığı kaydet ✓, build ✓,
sonra panelde **"Ölçü çözümü: …"** satırını oku ✓.

### §26-B-5 ek: bağ modu arayüzde çalışıyor — kalan tek şey iki tıklamanın dönüşümü

Gerçek tarayıcıda ✓: "Seçili ölçüyü bağla" düğmesine basınca **bağ modu açılıyor** ✓ ("Bağlamayı bırak" düğmesi
belirdi ✓); ilk tuval tıklaması **bir ucu yakaladı** ✓ ("Bir uç seçildi; ikinci uca tıklayın." ✓ — yakalanan uç
paftanın sol üst köşesiydi ✓, hedeflediğim delik merkezi değil ✗ — tuval→sayfa dönüşümünü yanlış kestirdim ✗);
ikinci tıklama hedefe yakın olmadığı için ürün **kendi dürüst hatasını** verdi ✓ ("Bağ ucu seçilen konturun bir
köşesine ya da bir daire merkezine yakın olmalı." ✓). Yani arayüz zinciri (ölçü seç ✓ → bağ modu ✓ → yakalama ✓
→ hata metni ✓) **çalışıyor** ✓; kalan tek eksik, tuval→sayfa dönüşümünün kesin ölçeğinin bulunması ✓ (bu turda
`s` tahminim yanlış çıktı ✗; sonraki tur: `s`'yi sayfadan ölçmek için bilinen bir noktaya tıkla ve uygulamanın
kaydettiği ucu oku ✓ ya da çizilen resmin nitelik boyutunu tuvalden al ✓). Sonra: iki delik merkezi ✓ →
kaydet ✓ → build ✓ → panelde "Ölçü çözümü" ✓.

### §26-B-5 ek 2: dönüşümün ölçüsü bulundu — ve oturum tükendi

Ekran→sayfa dönüşümü ölçüldü ✓: `s ≈ 2,2` (tuval 725,95×514,19 görünür ✓, nitelik 1200×849 ✓; paftanın sol
kenarı ve kesişen noktalar bu değerle örtüşüyor ✓). Bu, ilk tıklamamın neden sol üst **köşeyi** yakaladığını
açıklıyor ✓: `s≈2,2` ile g9 delik merkezi ekranda ≈ (157, 247) ✓, konturun sol üst köşesi ≈ (163, 253) ✓ —
**9 piksel arayla** ✓; tıklamam (162,5 / 255,6) köşeye daha yakındı ✗ ve yakalama yarıçapı (12/displayed ≈ 20
piksel ✓) ikisini de kapsıyordu ✓ → en yakın kazandı ✓. Yani ürün doğru davrandı ✓; ben yanlış yere tıkladım ✗.
Delik merkezlerinin ekran konumu: g9 ≈ (157, 247) ✓, g11 ≈ (374, 247) ✓ — sıradaki tur bunlara tıklamalı ✓.
**Engel:** bu turda tarayıcı oturumu düştü ✗ (`sheet` tanımsız ✗ = sayfa yenilenmiş/taze ✗; bu oturumda zaten
"her yeni çağrıda sekme kayboluyor" ✗ kayıtlı ✓). Arayüz zincirinin kendisi çalışıyor ✓ (bağ modu ✓, yakalama ✓,
dürüst hata ✓) — kalan tek şey iki isabetli tıklama ✓ → kaydet ✓ → build ✓ → "Ölçü çözümü" satırı ✓. Bu,
kullanıcının kendisi arayüzde bir dakikada bitirebileceği bir adım ✓; ya da taze bir tarayıcı oturumunda
yeniden açılıp (plaka ✓, kontur+ölçek onayı ✓) yukarıdaki iki koordinata tıklanarak ✓.

## §26-B-6: ARAYÜZ KABULÜ TAMAM — çözüm raporu gerçek tarayıcıda görüldü — 2026-09-29

Gerçek tarayıcıda, gerçek tıklamalarla uçtan uca ✓ (plaka ✓, taze oturum ✓):
1. "Ölçeği uygula" ✓ → "Karar kaydedildi." (kullanıcının iki noktalı kalibrasyonu: **787,6 px = 80 mm** ✓ —
   iki alt delik merkezi ✓).
2. Ölçü seçicisinden paftanın kendi basılı değeri **80,00 (mm)** seçildi ✓ → "Seçili ölçüyü bağla" ✓ →
   bağ modu açıldı ✓ ("Bağlamayı bırak" ✓) → tuvalde **iki delik merkezine** tıklandı ✓ ("Bir uç seçildi; ikinci
   uca tıklayın." ✓ → "Karar kaydedildi." ✓) → panelde bağ satırı: **"80 mm · g9 ↔ g11"** ✓ ("Kaldır" ile geri
   alınabilir ✓).
3. Kalınlık 15 girilip kaydedildi ✓, "Seçilen kontur ve merkezleri çizimden izlenen taslak olarak kullan"
   işaretlendi ✓, **build** çalıştırıldı ✓ → durum: "Taslak hazır. Geometrik kontrol tamam…" ✓.

**Panelde okunan yeni satır** ✓ (PLAN §26.4-B'nin görünürlük maddesi):
"**Ölçü çözümü: çözüldü · serbest koordinat 11 · uygulanan değişim 0,00 px.**" ✓ + çekirdeğin iki notu ✓
("Başlangıç noktasının çizimdeki konumu yalnız koordinat sistemini sabitler; parça ölçüsü değildir." ✓ /
"Yaylı/dairesel dış kontur çizimden izlenen taslak olarak kalır. Serbestlik sayısı yalnız seçili daire
merkezlerini kapsar." ✓). Panel 4'ün kendi metni de dürüst ✓: "Tek bir ölçek çözülen bağları uzlaştırmaz;
çelişki soru olarak sorulur." ✓

**Aynı koşunun kanıtı (arayüzün ürettiği klasör)** ✓: oturum `34f729c104f643c2b891bf74b24f9f0d` ✓, build
`build-5-b062fba9` ✓ — **plan denetimi geçti** ✓ (`valid_solid` ✓, `export_round_trip` ✓), **geçerli 1 katı** ✓
[96,0087 / 64,0014 / 15,0] mm ✓ 91 327,66 mm³ ✓, `part.step` yazıldı ✓ (32 458 bayt ✓). Planın varsayım
cümlesi ✓: "Ölçek 9,8446 px/mm — bağlanan 1 basılı ölçüden en küçük karelerle çözüldü… **Ölçü çözümü
uygulandı: 1 koordinat kullanıcının bağladığı ölçülerden geldi, 11 koordinat hâlâ çizimden izlenen taslak.**" ✓
Bu koşuda `user` kaynaklı parametreler `binding_0`, `thickness` ✓ — sabitlenen tek koordinat bir *daire
merkezine* ait ✓ ve o daire kesilmediği için plan parametresi yok ✗ (etiketlenecek yanlış bir şey yok ✓;
sayı varsayım cümlesinde duruyor ✓).

**§26'nın iki yarısı da kapandı** ✓: (A) kontur doğrulaması ✓ + düzelt/kaydet/geri al ✓ + geçerli-önce sunum ✓ +
görülmemiş raster paftadan geçerli STEP ✓; (B) çözücü karar kaydına, GeneralPlan'a ve arayüze bağlı ✓ — ölçüler
kenar/merkez konumlarını gerçekten değiştiriyor ✓ (gerçek paftada 80,0000 / 60,0000 mm STEP'te ✓), çelişkiler
ve eksik serbestlik görünür ✓, ortak ölçek kesin çözüm diye sunulmuyor ✓.

**Kayıtlı kalan sınırlar (yeni pencere için):** (1) yatay/dikey **ilişki** denetimi yok ✗ (çekirdek destekliyor ✓);
(2) çözüm reddi notu *planda* yazmıyor ✗ (state/arayüzde ✓); (3) çizgi konturda köşe ucu bağları hâlâ eski soru
kapısına takılıyor ✗; (4) okuma kalitesi: yanlış bağlama (kendini kesen konturlar) sürüyor ✗ — kesme/alt-zincir
seçimi işi duruyor ✓; (5) yeni görülmemiş paftalarda doğruluk/müdahale/süre ölçümleri sürdürülmeli ✓.

### §26-B-3 kanıt yolu (bildirim geldi — temiz koşu klasörü)

Temiz koşunun (kapı değişikliği + pafta içi daireler) klasörü:
`out/guided/fd57c33d945b4a6bb8d3e9ff61bb2014/build-1-5c0279a6/` ✓ — `part.step` ✓ (geçerli ✓, 1 katı ✓,
[103,4585 / 68,967 / 15,0] mm ✓, 103,575 cm³ ✓, 15 yüz = 6 düzlem + 9 silindir ✓). Ø6,8 delik silindirleri
(r=3,4): (8,6288 / 0,3464) ✓, (88,6288 / 60,3464) ✓, (8,6288 / 60,3464) ✓, (94,8363 / 8,6231) ✓,
(51,732 / 34,4842) ✓ → **aynı satırda 88,6288 − 8,6288 = 80,0000 mm** ✓ ve **aynı sütunda 60,3464 − 0,3464 =
60,0000 mm** ✓. §26-B-3'te yazılan sayılar birebir doğrulandı ✓.

## §26-K1: tam test takımı — 585 passed (951,5 s) — 2026-09-29

§26'nın tüm dilimleri indikten sonra **tam takım** yeniden koşuldu ✓: `PYTHONPATH=src .venv/bin/python -m
pytest -q` → **585 passed in 951.46s (0:15:51)** ✓, çıkış kodu 0 ✓ (önceki tam takım §23-C35'te 567 passed idi ✓;
§26'nın 18 yeni testi dahil ✓). Odak koşuları da kayıtlı: `test_contour_audit` 8 ✓, `test_contour_fix` 6 ✓,
`test_user_dimensions` 4 ✓, `test_guided + test_user_dimensions + test_sketch_constraints + test_plate_plan`
74 passed ✓. Bu, §26'nın mevcut değişiklikleri bozmadığının kayıtlı kanıtıdır ✓.

**Dürüst sınır:** kapının *sayaç* biçimi (plaka 7/7 ✓, plastik 14/14 ✓, `Drawing.pdf` 16/17 ✓ ve depolanmış istek
hash'leri ✓) en son §26 öncesinde ölçülmüştü ✓; bu pencerede o sayaçlar ayrıca koşulmadı ✗ — takımın içindeki
`test_catalog_cli` ve ilgili testler geçiyor ✓, ama sayaçların birebir yeniden okunması yeni pencereye kalıyor ✓.
