# Beşinci denetim — aday artışı var, doğruluk kanıtı hâlâ açık

İncelenen HEAD `2fe138d`. Ürün kodu değiştirilmedi; gerçek model veya bulut çağrısı yapılmadı. Yeni goal, önceki başarıya kadar devam sözleşmesini koruyarak açık iş sırasını günceller.

## Yeniden doğrulanan ilerleme

`test_baseline_fields`, `test_sheet_scale`, `test_value_pairing`, `test_reading_gate`: **37 passed in 0.66s**. U01/U02 karşı örnekleri regresyonda; kapanan işleri yeniden yazma. Hermes'in 790 test raporu tarihsel kanıt; bu denetimde tam takım yeniden çalıştırılmadı.

PDF metin yolu yeniden ölçüldü: block-01 **3**, plate-01 **5**, plate-02 **5**, step-01 **5** span. Önceki 2/3/3/3 sayısına göre artış doğrulandı. Bunlar geometriyle doğru eşleştirilmiş ölçü veya doğru STEP sayısı değildir. Raster yolunda aynı iyileşme uygulanmış değil. Son ürün kabulleri açık; yeni 20 parça seti ve çevrimdışı UI kabulü yok. Son eşleştirme değişikliği sonrası yeni uçtan uca doğru STEP kanıtı bulunmadı.

[Çalıştırılabilir karşı örnek](../eval/audits/20260929-hermes-review5/probe.py) ve [sonuçlar](../eval/audits/20260929-hermes-review5/observations.json) kaynak hash'leriyle kaydedildi. Bu probe model kullanmaz ve eski deney dosyalarını ezmez.

## V01 — eşleştirme kendi varsayımını kalibrasyon kanıtı yapıyor

`_pair_by_value` minimum=2 konsensüsle bir çizgi seçiyor ve `anchor_mode=dimension` yazıyor. `scale.verdict` bu yeni eşleşmeyi bağımsız üçüncü gözlem sayıyor. Karşı örnekte iki gözlemle **uncalibrated**, bunların ölçeğine göre seçilmiş sıradan bir çizgi eklenince **calibrated**, spread=0. Bu yeni bağımsız kanıt değildir. Ayrıca yalnız uzunluk/konumla seçilen Segment'in ölçü çizgisi olduğunu gösteren ok, uzatma çizgisi veya görünüş ilişkisi fonksiyonda sınanmıyor.

Aday üretimi yararlı olabilir; kaynak/provenance ve bağımlılık ayrımı şarttır. Değerden türetilen eşleşme üçüncü bağımsız ölçek gözlemi olarak sayılmamalı, otomatik doğrulanmış ölçüye terfi etmemeli. Birim/tür, görünüş ve datum korunmalı. Aynı uzunlukta gövde kenarı, antet çizgisi, başka görünüş, farklı birim, birden çok aday ve aynı koordinatlı çizgilerle olumsuz regresyon gerekir. 8 metin yüksekliği sınırı v2 üzerinde ayarlanmış; yeni vakalarda precision ölçülmeden genelleme kanıtı değildir.

## V02 — bir sayı değişince bütün tablo doğrulanmış sayılıyor

`_verbatim_readings` yalnız sıralanmış sayıları karşılaştırıyor. Karşı örnekte çelişkili 4/9/60 tablosunda **4→4.1** değişikliği veya bir kaydın silinmesi guard'ı devre dışı bırakıyor; kimin değiştirdiğine, neyin doğrulandığına ve diğer çelişkilere bakılmıyor. Bu probe coder/CAD çağırmadan guard koşulunu doğrular. Kodun mevcut testi “değer değiştiyse coder'a ulaşır” davranışını özellikle kabul ediyor; testin geçmesi ürün doğruluğu değildir.

Açık kullanıcı kararı span/özellik bazında kaynak ve sürüme bağlı tutulmalı; programatik değişiklik inceleme sayılmamalı. Bir düzeltme ilgisiz çelişkileri kaldırmamalı. Güncel tablo tekrar doğrulanmalı; gerekli eksik veya çelişkili parametre varken doğru parça kabulü verilmemeli. Taslak STEP ile doğrulanmış sonuç ayrımı korunmalı.

## V03 — sayısal kapsama ve güncel durum kanıtı eksik

`eval/text_layer_coverage.py` eksikleri value set farkıyla çıkarıyor; aynı sayı iki konumda varsa birinin kaybını saklıyor. Ham span kimliği/konum/görünüş/tür üzerinden kept/unpaired/rejected eşleştir; raw span sayısı, aday sayısı, doğru bağlama ve yanlış kabul ayrı olsun. Çap, adet, derinlik, kalınlık ve doğrusal ölçü aynı sınıf değildir; `4 x Ø8 THRU` tek bir lineer 4 mm ölçüye indirgenmemeli. Pafta/etiket iddiaları asıl görselle doğrulanmalı.

`state.json` aktif hipotezi uygulanmış ikinci yolu hâlâ sonraki iş gösteriyor; `next.md` b9aac1d düzeyinde kalmış, acceptance eski baseline'a bağlı. “790 geçti, doğrulama sürüyor” kalıcı güncel test sonucu değildir: komut, başlangıç HEAD/hash, bitiş, exit ve gerçekten kolekte edilen testler kaydedilsin. Çalışan işi yanlışlıkla çoğaltmadan gerçek süreç/koşu durumu doğrulansın.

## Yeni sıra ve devam

V01/V02 küçük genel onarım ve regresyon → V03 kimlik tabanlı kapsam ve tutarlı durum → raster önce oku/sonra bağla, callout ve küçük ölçüler → aynı dört v2 girdide yeni uçtan uca paired baseline → ilk kalan semantik/CAD hatası → gerçek UI/store akışı ve mevcut P01–P08/final set kabulleri. Yalnız yeni teşhis scriptleri üretmek veya span sayısını artırmak goal başarısı değildir; her uygulanmış değişikliğin gerçek ürün etkisi ölçülmeli.

Aynı hipotez üç kez başarısızsa yaklaşım değişir, goal bitmez. Ara raporlarda durulmaz. Tek ağır iş, vaka600 s/koşu7200 s, ilk RunPod3 USD/toplam20 USD ve sonraki ücretli aşama öncesi kullanıcı değerlendirmesi şartı aynen korunur. Eğitim şu an `fix_rules_first`; bu ürün tamamlandı demek değildir. Bütün başarı koşulları kanıtlanmadan complete/final başarı raporu yazılmaz.
