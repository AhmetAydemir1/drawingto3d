# Hermes için güncel goal promptu

2026-09-29. Ana plan: [HERMES_IMPLEMENTATION_PLAN.md](docs/HERMES_IMPLEMENTATION_PLAN.md).
Başlangıç görevleri: [hermes-task-queue.json](docs/hermes-task-queue.json).
Önceki prompt [arşivlendi](docs/HERMES_PROMPT_BEFORE_CLOUD_20260929.md).

Bu dosya Hermes'e verilecek istemdir; burada goal başlatılmadı ve kaynak kiralanmadı.
İlk bloğu Hermes sohbetine yapıştır. Kurulu Hermes sürümünde /goal yoksa aynı metni normal görev olarak ver; desteklenmeyen komut/ayar uydurma.

## İlk goal: kanıtlı altyapı ve en fazla 3 USD teknik deneme

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde docs/HERMES_IMPLEMENTATION_PLAN.md planının H00–H08 aşamalarını uygula. Önce bu planı, docs/hermes-task-queue.json başlangıç kuyruğunu ve PLAN.md'nin değişmez kurallarıyla güncel durum tablosunu oku. Çıktı dosyalarıyla kanıtlanan sonlu bir teslim üret; yalnız planı yeniden anlatıp durma.

Sen DeepSeek ile çalışan geliştirme/deney asistanısın. Son ürün M1/16 GB üzerinde kurulumdan sonra çevrimdışı PDF/PNG/JPG → STEP çalışacak. Gerektiğinde küçük model RunPod'da eğitilebilir; ürüne uzak model API'si bağlama. Mevcut kod, kullanıcı değişiklikleri ve oturumları koru. Eski A0/P04 anlatısını kaynak ve test kanıtı olmadan güncel hata kabul etme; yapılmış işi tekrar yazma.

H00'ı kısa tut: çalışma ağacı/sürüm kaydı, CLI/MCP bağlantısı ve yalnız gerekli salt okunur envanter. Kullanıcı API key'i ayarladı; değerini okuma, yazdırma veya rapora koyma. Bağlantıyı yetkili çağrıyla doğrula. Kurulu CLI yardımını kullan; burada görülen 2.14.0-dd55bcf sürümünde --terminate-after yok. Eski skill bayraklarını körlemesine kopyalama.

İlk kod işi H01: değerlendirici aynı çaplı eksik/fazla delik, yanlış merkez, eksen, birim ve kör delik derinliğini yakalasın; doğru eşdeğer CAD geçsin. Bağımsız karşı örnek testlerini tamamla. Ardından küçük devam edebilir deney koşucusu, kaynak/etiket/split kaydı, gerçek çizim pilotu ve mevcut modelsiz/model yollarının hata raporunu üret. Referans STEP ve doğru etiketler ürün girdisine/model istemine girmesin; examples/eval eğitimde kullanılmasın.

H04'te okuma, bağlama, çözücü ve CAD hatalarını ayır. Önce kodla düzeltilebilen hatayı düzelt. Eğitim gerekiyorsa tek dar görev seç. En fazla iki küçük model adayını M1'de ölç; önceki Qwen başarısızlığını LoRA ile düzelmiş sayma. Seçilen modelin M1 çalışma ve export yolu doğrulanmadan GPU kiralama. Eğitim verisini hazırla, kaynak/grup bazında ayır, sentetik ile gerçek sonuçları ayrı tut.

Toplam kabul edilmiş RunPod hizmet bütçesi 20 USD; bu ilk goal'un ücretli teknik denemesi H07+H08 birlikte EN FAZLA 3 USD. Diğer 12 USD eğitim ve 5 USD rezerv ilk rapor değerlendirilmeden harcanmaz. Vergi ve DeepSeek API maliyeti ayrı raporlanır. Tek GPU, ilk run en fazla 2 saat ve bütçenin gerektirdiği daha kısa deadline. Kurulum/indirme/bekleme/export/storage maliyetlerini say. Gerçek kaynak kapatma koruması doğrulanmadan gözetimsiz iş başlatma; konuşmanın veya eğitim process'inin bitmesini fatura kapanışı sanma. Kimlik doğrulama ya da maliyet engeli varsa yerel bağımsız işleri sürdür.

H07'de yalnız 20–50 adımlık gerçek görsel görev eğitim denemesi yap. Gradient, checkpoint ve yeniden yükleme doğrulansın. H08'de gerekli dosyaları Mac'e indir, hash'leri karşılaştır, M1 biçimine dönüştür ve yerel gerçek girdide çevrimdışı çalıştır. GPU işi bittiğinde kaynakları boş bekletme; gerekli dosyaların doğrulanmış kopyalarını almadan kalıcı volume'u silme. Yalnız bu goal'un kaynaklarını yönet.

Her küçük teslimde ilgili testi çalıştır, gerçek çıktıyı kaydet, out/lab/state.json ve out/lab/next.md dosyalarını güncelle. Test beklentisini ürünü geçirmek için değiştirme; başarısızlıkları ve kullanıcı müdahalelerini saklama. Yeni model adayı fayda göstermeden varsayılan ürün modeli yapılmasın.

İlk goal'un teslimi: out/lab/checkpoint-1/report.md, teknik test kanıtları, M1 sonucu, artefakt manifesti, toplam maliyet/kalan bütçe, kaynak kapanışı ve tek sonraki adım. H04/H05 eğitim gerektirmediğini veya kanıtın yetersizliğini gösterirse harcamadan training_not_justified/need_data raporu üret; açık işleri dürüstçe belirt. Bu durumları ürünün tamamlanması gibi sunma. İlk raporu verdikten sonra sonraki ücretli eğitime geçme. Şimdi H00 kısa kaydı ve H01 uygulamasıyla başla.
```

## Devam goal'u: yalnız ilk raporu değerlendirdikten sonra gönder

İlk teknik denemenin raporu ve maliyeti görülmeden bu ikinci blok kullanılmaz. İlk goal bitmeden iki goal'u aynı anda başlatma.

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde ilk teknik deneme raporundan devam ederek docs/HERMES_IMPLEMENTATION_PLAN.md H09–H11 aşamalarını uygula. Önce out/lab/checkpoint-1/report.md, state, cost-ledger ve aktif kaynak kayıtlarını oku. Önceki aşamanın eksik zorunlu kabulünü tamamlanmış varsayma.

İlk raporu değerlendirdim; planlanan küçük eğitim aşamasına devam et. H09 için en fazla 12 USD ve projenin bütün RunPod hizmetleri için toplam 20 USD sınırını koru; mevcut harcama ve depolama rezervini düş. Yeni bütçe veya ücretli öğretmen model varsayma. Tek GPU ve en fazla iki eğitim konfigürasyonu kullan. Uygulanmış maliyet/deadline koruması olmadan çalışma başlatma.

Eğitimden önce görev metriğini, M1 kaynak hedeflerini ve model terfi koşullarını sabitle. Train/validation/saklı test grupları ayrı kalsın. Eğitim öncesi/sonrası ve kuantizasyon öncesi/sonrası sonuçları karşılaştır. M1'de iyileşme yoksa adayı varsayılan yapma ve bütçeyi tüketmek için denemeye devam etme.

Ürün entegrasyonunu gerçek store/UI/CAD yolunda test et; ağ erişimi olmayan ürün koşusunda çalışmasını göster. Saklı test yalnız model/ayar seçimi tamamlandıktan sonra değerlendirilsin. Eksik veri ve bağımsızlık sınırlarını raporla; başarısız vakaları paydadan saklama.

Sonlu teslim: out/lab/final altında tekrar edilebilir deney ve M1 kullanım paketi, sonuç tabloları, destek sınırları, geri dönüş yolu, artefakt hash'leri, maliyet dökümü ve bütün görev kaynaklarının kapanış durumu. Başarısız/sonuçsuz deney de kanıtlarıyla raporlansın; genel çizim probleminin çözüldüğünü iddia etme.
```
