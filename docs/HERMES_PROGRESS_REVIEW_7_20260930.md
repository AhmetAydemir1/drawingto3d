# Yedinci denetim — yanlış STEP'e accepted=true veriliyor

HEAD `b1aec25`, 2026-09-30. Yedi ilgili dosyada **70 passed in 0.54s**: value_pairing, sheet_scale, reading_gate, baseline_fields, scale, scale_witnesses, suspect_guard. Hermes'in819-test raporu bu turda yeniden çalıştırılmadı. Ürün kodu değiştirilmedi; model/bulut çağrısı yapılmadı.

## İlerleme

W01 tekil destek ve W02 şüpheli ölçü kontrolü için regresyonlar geçiyor. Tanık ölçeği, sayfa üzerinde taşıma ve hedefli soru akışı eklenmiş. Yeni offline-flow raporu dört STEP içeriyor, dördünün de bbox'ı referanstan farklı; dört build çıktısında `accepted: true` var. Bu, önceki yalnız okuma deneylerinden ileridir fakat ürün başarısı değildir. Rapor otomatik/insan destekli gerçek UI kabulü olarak kullanılamaz: aşağıda nedenleri var.

## X01 — üretildi ile doğrulandı aynı durum

`reason_drawing` sonunda `Audit(accepted=True)` döndürüyor. Eksik özellik/rol bilgisi, uydurulmuş delikler ve yanlış dış boyutlar varken bile STEP oluşması kabul için yetiyor. Kayıtların kalibre olması parçanın eksiksiz/semantik olarak doğru tanımlandığını kanıtlamaz. Bilinmeyen delik konumuna orta nokta, eksik kalınlığa bir sayı veya eksik özelliğe basit gövde atamak çözüm değildir.

Öncelik: ürünün kendi kaynak kanıtı, rol/datum/özellik kapsamı, açık soru ve plan→CAD kontrollerine bağlı kabul. Çözümsüz durumda açıklanmış ret/soru veya açıkça doğrulanmamış taslak; kullanıcıya doğru STEP denmemeli. Test referansını ürün kabulüne bağlama; bağımsız evaluator yalnız deneyde kalır. Geçerli tam tanımlı pozitif akış da çalışmalı; her şeyi reddetmek başarı değildir.

## X02 — offline-flow gerçek kullanıcı doğrulamasını taklit ediyor

Araç `tam_sayi_adayi` değerini geometriden alıp tabloya yazıyor, ardından **bütün** kayıtları `source=user` yapıyor. Bunu gerçek insan destekli veya otomatik ürün başarısı sayma. Çıkışları simulated_review diagnostic kolu olarak koru. Gerçek otomatik kol kaynakları değiştirmemeli; destekli kol gerçek kullanıcı kararını kaynak/span/sürümle kaydetmeli. `suspect_questions` içindeki “basılı sayı55 olmalı” kesinliği de yanlış: ölçek tahmini basılı metnin kanıtı değildir. Kırpımı gösterip değeri doğrulat; tahmini cevap otomatik doldurulmasın.

## X03 — yeni ölçüm eski kaba evaluator'a dönmüş

`cadrun.py` cylinders[0] alanına **yarıçap** yazar. `offline_flow._compare` bunu çap diye raporluyor: örneğin program diameter10 kullanırken raporØ5 diyor. Silindirik yüz sayısı delik sayısı değildir. Sıralanmış bbox, hacim oranı ve ham silindirler delik merkez/eksen/derinlik, cep ve eşdeğer yüz temsillerini doğrulamaz. Bu karşılaştırmada bağımsız pass/fail de üretilmiyor.

Mevcut `eval/feature_metrics.py` kullanılmalı; STEP'i yeniden aç, tek rigid hizalama ve özellik/geometri karşılaştırmasını kaydet. Yeni evaluator yazma. Raporun dört yanlış parça teşhisi bbox farkıyla destekleniyor; bildirilen çaplar yanlış. [Bağımsız STEP çıkarımı ve kaynak hash'leri](../eval/audits/20260930-hermes-review7/observations.json) kayıtlıdır.

## X04 — yeni araçlar koşucu korumalarını atlıyor

`offline_flow.py` ve `end_to_end.py` adım başına900s, sabit çıktı klasörü, subprocess.run kullanıyor; ortak vaka600s/koşu7200s ve ağır iş kilidi entegrasyonu yok. Başarısız yeni komuttan sonra eski records/geometry/STEP okunabilir. Timeout kayıt/temizlik ve aynı koşuda taze çıktı kanıtı gerekli. Yeni scheduler yerine mevcut koşucu ve artefakt sözleşmesi kullanılsın. Mevcut ürün süreçleri başlatılmadan bu onarım yapılmalı.

## X05 — lider bağlama planının varsayımı düzeltilmeli

“Yakındaki daireye sayıyı delik olarak bağla” yeterli değildir. Ø/R işareti, adet, THRU/DEPTH, leader ucu ve görünüş ilişkisi; delik/dış silindir/yardımcı daire ayrımı birlikte gerekir. Yakında başka daire, Ø ile R karışması, adet4 ve derinlik8 gibi çoklu sayılar negatif örnek olmalı. Yarıçap/çap oranı yalnız ilişki metinden/geometriden bağımsız kurulmuşsa ölçek tanığıdır; mevcut ölçeğe uygun daireyi seçip oranı aynı ölçeğe bağımsız destek sayma. Önceki W01 bağımlılık kuralı burada da geçerli.

## Yeni devam sırası

X01 yanlış kabul + X02 sahte kullanıcı onayı → X03 bağımsız evaluator + X04 koşucu entegrasyonu → yeni otomatik/gerçek destekli/simülasyon ayrımlı baseline → X05 callout/rol/datum, eksik cep/küçük ölçü ve semantik CAD onarımı → her değişikliğin ürün etkisi → UI/store çevrimdışı ve P01–P08/20 yeni parça/10 raster kabulleri. Yeni rapor yazıp durma. Güncel state/acceptance hâlâ eski sonuçlara bağlı; kanıt HEAD'i ve mevcut HEAD ayrı tutulmalı.

Başarıya kadar devam sözleşmesi ve tüm bütçe/deadline kapıları korunur. İlk3USD/toplam20USD ve sonraki ücretli aşama öncesi kullanıcı rapor değerlendirmesi değişmez. Eğitim henüz zorunlu değil. Yanlış accepted sonucunu kaldırmak gerekli fakat tek başına goal başarısı değildir.
