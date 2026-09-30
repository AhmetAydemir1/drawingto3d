# Hermes için güncel /goal promptu

Güncelleme: 2026-09-29, goal sonrası bağımsız denetim. Komut **`/goal`**.
Proje dosyaları ve güncel `PLAN.md` ile birlikte aşağıdaki bloğu Hermes'e ver:

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde mevcut çalışmayı koruyarak PLAN.md'nin güncel devam sırasını uygula. Önce PLAN.md 1–4. bölümlerini, A0'ı ve eval/reports/goal-progress-audit-20260929.md dosyasını oku. Eski “P01/P02 tamamlandı” ve “P03'te yalnız görünüş ekseni kaldı” kayıtlarına göre ilerleme. Yeni build kopyalama, maksimum açıklık ve X/Y/yön alanları çalışıyor; bunları yeniden yazma.

İlk teslim A0.1: static/guided.html içindeki bozuk <button <div ...> yapısını düzelt. bind-start gerçek ve tekil bir button olmalı; guided.js null üzerinde onclick atamamalı. DOM elemanlarını doğrula ve /guided HTTP sayfasında açılış/ölçü bağlama akışını sına. A0.2: bağlar varken profil seçimi kaldırılınca hata yerine kontur seç/yeniden bağla sorusu gelsin; save ve reopen çalışsın.

Sonra sırayla P01-a/b geçiş ve çıktı güncelliği, P02-a/b/c yay/kesişim matematiği, P03-a/b/c kararlı referans ve kullanıcı çerçevesi, P04-a…f ölçü çözümü entegrasyonunu tamamla. P01-c rapor görünürlüğü P04-c ile, P03-c'nin gerçek CAD kabulü P04-f ile kapanır; bunlar sonraki aşamaya geçişi engellemez. P01'de belirsiz eski referansları koruyup üretimde engellemek yeterli geçiş kapısıdır; eksiksiz kimlik dönüşümü P03-a/b'de yapılır. Geçiş eski oturumu yedeklemeli; kenar/ölçü kimlikleri ve uç anlamı gerçekten eşleşmeli; stale geometride eski STEP güncel sunulmamalı. Eski edge:<index> bağları mevcut listeye her build'de yeniden eşlenmemeli; karar ve undo geçmişinde sürümlü dönüşüm yapılmalı. Görünüş çerçevesi için otomatik pafta dedektörü geliştirmeyi önkoşul yapma; açık kullanıcı seçimi yeterli başlangıçtır.

P04'te yerel ölçü kalibrasyonu değiştirmesin: mevcut probda 100 mm gövde 50 mm oluyor. X=50/Y=30 geçerli köşe ölçüleri ortak ölçek kapısına takılmasın. Unsupported/çelişki üretimi durdursun. Çekirdeğin derived ifadeleri korunsun; önizleme ve CAD aynı son geometriyi kullansın ve çözüm sonrası kontur yeniden denetlensin.

eval/audits/20260929-goal içindeki küçük örnekleri doğru beklentili regresyon testlerine çevir. Denetim scriptlerinin bazı assertion'ları mevcut kusuru yeniden üretir; bunları ürünün beklenen davranışı sanma. Sabit örneklemeye bir sınırlama yorumu eklemek P02'yi tamamlamaz. Mevcut 91 testin geçmesi yeni karşı örneklerin çözüldüğünü göstermez.

Her alt teslimi gerçek karar/store yolu ve ilgili kabul testiyle bitir. P04 kabulü geçince P05–P08'e ilerle; erken tamamlandı yazma. PLAN.md durum tablosunu, eval/reports/implementation-status.md ve üç devir dosyasının güncel başını kanıt, sınır ve tek sonraki işle güncelle. Kesilmeden önce kodu, test çıkışlarını ve aktif iş durumunu diske kaydet.

Hedef M1/16 GB cihazda çevrimdışı, farklı teknik çizimler için genel ve kullanıcı yönlendirmeli PDF/PNG/JPG → STEP aracıdır. examples/pdf with steps yalnız test verisidir; örneğe özel üretim veya bu veriden eğitim yapma. Referans STEP yalnız ayrı değerlendiricide kullanılabilir. Görülmüş veriyi regresyon say. Bu goal'un sonlu teslimi A0 ve P01–P08'in kabul koşullarıdır; genel hedefi tamamlandı ilan etmeden P09–P12 için devir bırak.
```

Goal başladıysa mevcut çalışma ağacını devral; yeni kopyaya geçmek için kullanıcı değişikliklerini silme. P00'daki eski envanteri büyük bir iş olarak tekrarlama; yalnız güncel durumu kaydet. Araç engelini test başarısı sayma; etkilenmeyen işleri sürdür.
