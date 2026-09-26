# drawingto3d — devralan AI ajanı için uygulama planı

Tarih: 2026-09-27 · Durum: geliştirme planı, henüz uygulanmadı.

## Devralan ajana görev

Bu belgeyi uygulama görevi olarak kullan. Önce mevcut kodu ve değişiklikleri doğrula,
ardından aşağıdaki aşamaları ölçülebilir teslimlerle uygula. Kullanıcının hedefi M1 / 16 GB
üzerinde çevrimdışı, yeni teknik çizimlere genellenen PDF/PNG/JPG → STEP aracıdır.
Verilmiş örnekler test içindir; her birine ayrı parça şablonu yazmak hedefi karşılamaz.
Sohbet geçmişine ihtiyaç duyduğun bir karar olursa önce bu belgedeki kapsamı ve kaynak
kayıtlarını kullan. Belirsiz uygulama ayrıntılarını gerekçesiyle çöz; veri veya donanım
eksikliğini tamamlanmış sonuç gibi sunma.

**Başlangıç noktası:** Bölüm 9'daki kontrolleri yap, Bölüm 7'deki ilk kodlama dilimini
uygula. Sonra Bölüm 6'daki sırayla ilerle. Yeni test verisi toplama işi bekliyorsa genel
şema ve derleyici üzerinde bağımsız çalışmayı sürdür; saklı test başarısını açık iş bırak.

**Gereken teslim paketi:** Bu `PLAN.md` ile birlikte güncel proje çalışma ağacı.
Son değişikliklerin bir kısmı commit edilmemiş ve bazı yeni dosyalar izlenmiyor;
yalnız Git deposunun son commit'ini almak mevcut uygulamayı taşımaya yetmez.
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
| `plan.py` içindeki kaynak kaydı ve düzenleme | Genel parametre ve işlem planına taşınacak |
| `plate.py`, `PlatePlan`, `eval/plate_plan.py` | Dar kapsamlı karşılaştırma deneyi ve regresyon kaydı |
| Yerel arayüz, yükleme izolasyonu, önizleme, oturum kaydı | Genel plan inceleme ve düzeltme arayüzünün temeli |

Yeni varsayılan akış hazır olduğunda plaka tanıyıcısı deneysel seçeneğe taşınacak.
Eski serbest Python üreten model yolu da deneysel kalacak. Genel akışın çözemediği çizim
sessizce eski yola geçirilip başarılı sayılmayacak. Bu değişiklikler bu plan oturumunda yapılmadı.

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

Başlangıçta model eğitimi yapılmayacak. Mevcut yerel modeller, aynı geliştirme çizimleri
ve aynı yapılandırılmış görevlerle karşılaştırılacak. Model sürümü, nicemleme, bağlam
uzunluğu ve görüntü boyutu sonuçlarla birlikte kaydedilecek.

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
| **4 — Çizime göre doğrulama** | Plan→katı ve çizim→katı denetimlerini ayır. İzdüşüm/kesit karşılaştırması ve sınırlı düzeltme döngüsü ekle. Geometrik kenar seçimi hazırsa pah/yuvarlamayı genişlet. | Yanlış konumlu delik, eksik cep, yanlış derinlik ve yanlış görünüş eşlemesi içeren olumsuz testler doğrulanmış sayılmaz. |
| **5 — Yerel ürün ve saklı test** | Genel özellik tablosu, kaynak işaretleme, belirsizlik soruları, düzenleme sonrası üretim, iptal ve oturum sürüm geçişi. Bağımlılık/model kurulumu ve çevrimdışı çalıştırma yönergesi. | Dondurulmuş sürüm saklı veriyle değerlendirilir; doğruluk, raster/vektör ayrımı ve M1 kaynak raporu yayımlanır. Ağ kapalı dönüşüm ve art arda 10 iş denemesi geçer. |

Aşama 0'daki pilot, modelin önemli ilişkileri güvenilir biçimde çıkaramadığını gösterirse
parça başına kurallar eklemek çözüm sayılmayacak. Eksik katman iyileştirilecek veya
kullanıcıdan profil/ölçü seçimi isteyen yarı otomatik akış açıkça ürün kapsamına alınacak.
CAD derleyicisinin çalışması, çizim yorumlamasının çözüldüğüne kanıt sayılmayacak.

## 7. İlk kodlama dilimi

Bu plan sonrasında ilk çalışma, Aşama 0 ile Aşama 1'in en küçük kullanılabilir bölümüdür:

1. Değerlendirme manifestine parça grubu, veri ayrımı ve ölçü/özellik kimliklerini eklemek.
2. `schema.py`, `plan.py` ve eski `FeatureGraph` için tek genel plan sözleşmesini belirlemek.
3. Profil uzatma/döndürme ve hacim çıkarma için deterministik üretim ve kaynak kaydı kurmak.
4. Mevcut plakayı genel işlemlerle yeniden ifade etmek; farklı profiller ve işlem sıraları
   kullanan bağımsız planlarla aynı derleyiciyi sınamak.
5. Çizim okuyucudan gelen ölçü ankrajlarını bu sözleşmeye kayıpsız bağlamak için ilk adaptörü yazmak.

Bu dilimin teslimi, genel işlem temeli ve ölçüm altyapısıdır. Yeni parçalarda otomatik
çizimden üretim başarısı sonraki aşamalarda ayrıca gösterilecek.

## 8. Kayıt ve teslim disiplini

Her aşama sonunda kod/model sürümü, veri ayrımı, ölçümler, başarısız örnekler ve açık
varsayımlar rapora eklenecek. Yeni bir örnek başarılı olsun diye eklenen kuralın başka
çizimlere nasıl uygulandığı bağımsız örneklerle gösterilecek.

Ana devam kaydı `HANDOFF.md`; eş kayıtlar `.cursor/handoff.md` ve `out/HANDOFF.md`.
`out/` Git dışında olduğundan plan ve önemli sonuçların özeti proje kökünde tutulacak.
2026-09-27 tarihli plan hazırlama oturumunda yalnız belgeler güncellendi. Yukarıdaki
geliştirme ve hedefler henüz tamamlanmış çalışma değildir.

## 9. Projeyi devralma ve çalıştırma

### Doğrulanmış yerel bağlam

- Mevcut proje: `/Users/aydemir/Desktop/drawingto3d`. Başka ortamda kendi depo kökünü kullan.
- Plan yazılırken dal `main`, HEAD `148b8ed`; çalışma ağacı temiz değil. Bu bilgiyi
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
`pyproject.toml` → `schema.py`, `plan.py`, `plate.py`, `reason.py` → `geo.py`, `cadrun.py`
→ `eval/README.md`, `eval/cases.json`, testler. Kaynak modüller `src/drawingto3d/` altında.
Varsa devralınan ortamdaki `AGENTS.md` yönergelerini de oku.

### Korunacak mevcut değişiklikler

Plan öncesinden değişmiş dosyalar: `app.py`, `cadrun.py`, `cli.py`, `reason.py`, `schema.py`,
`static/index.html` ve proje kayıtları. Yeni dosyalar: `plate.py`, `plan.py`,
`tests/test_plate_plan.py`, `eval/plate_plan.py`, kök `HANDOFF.md`.
Kaynak dosyalar yukarıdaki modül dizinine göredir. Devralırken bu listeyi `git status`
ile karşılaştır; kullanıcı değişikliklerini silme. `git reset --hard`, toplu checkout
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

Önceki kayıt: 122 mevcut + 24 yeni test ayrı koşularda geçti. Bu, devralınan sürümün
testlerinin şimdi geçtiği anlamına gelmez; yeniden ölç. `test_llama_client_posts_the_image`
yerel HTTP sunucusu açar. Sandbox bağlantı iznini engellerse ortam kısıtını test hatasından
ayır; testi sessizce atlayıp tam başarı raporlama.

Dar plaka deneyini tekrarlamak için mevcut komutlar:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d plan "examples/pdf with steps/Plate With A Pocket Drawing.PDF" out/agent-baseline-01
PYTHONPATH=src .venv/bin/python -m drawingto3d build-plan "examples/pdf with steps/Plate With A Pocket Drawing.PDF" out/agent-baseline-01/plan.json out/agent-baseline-01
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
| `schema.py:DimensionRecord` | Değer/birim temsili ağırlıkla uzunluk için; açı ve adedi uzunlukla karıştırmayan tipli parametreler ekle. |
| `schema.py:FeatureGraph`, `plan.py:PlatePlan` | Birbiriyle yarışan üçüncü kalıcı şema yaratma; tek genel şema, sürüm ve eski kayıt dönüşümü belirle. |
| `plate.py:_from_paths` | Sabit yapısal koşulları yeni örneklere göre çoğaltma; deney olarak koru. |
| `cadrun.py` | Silindir raporu şu an Z eksenine paralel yüzlerle sınırlı; genel eksen/konum raporu gerekir. Süreç ayırma ve ortam temizliği ağ izolasyonu değildir. |
| `llama.py` | Sabit 16384 bağlam ve model yaşam döngüsünü ölç; kaynak sınırlarına göre düzenle. |
| `eval/report.py`, `eval/frontend.py` | Değer eşlemesi aynı sayının farklı kullanımlarını kaçırabilir; gözlem/özellik bazlı değerlendirmeye geç. |
| `eval/metrics.py` | Dış boyut/hacim/yarıçap kümesi, yanlış delik konumunu ve adedini yeterince ölçmez. |
| `app.py`, `static/index.html` | Dokuz plaka parametresi yerine genel parametre/işlem görünümü; eski oturumların sürüm geçişi. |

## 10. İlk teslimin kabul listesi ve raporu

İlk kodlama dilimi sonunda şu kanıtları teslim et:

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

Bölüm 7'deki ilk kodlama dilimi uygulandı; Bölüm 10 kabul listesi karşılandı. Kanıtlar:

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
