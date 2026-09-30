# Altıncı denetim — raster ilerledi, kanıt ve ürün kapıları açık

HEAD `68db985`; 2026-09-30. Ürün kaynak kodu değiştirilmedi, model veya bulut çağrısı yapılmadı. Beş ilgili test dosyası (`value_pairing`, `sheet_scale`, `reading_gate`, `baseline_fields`, `scale`): **59 passed in 0.35s**. Hermes'in b8639b1 için 809-test raporu okundu, bu turda tam takım yeniden çalıştırılmadı.

## İlerleme ve sınırı

V01'in eski kendi kendini kalibre etme yolu `anchor_source=value` ayrımıyla onarılmış. V02 tek sayı değişikliği/silme karşı örnekleri ve U01/U02 regresyonları geçiyor. V03 kimlik tabanlı araç mevcut. Raster önce oku/sonra bağla, aday terfisi, ölçek bootstrap ve paftadan çizgi kalınlığı tavanı eklendi. Bu işler yeniden yapılmamalı.

Son raporlarda raster etiketle sayısal uyum 17→18 olarak verilmiş; aşağıdaki W03 nedeniyle bunu doğru bağlama artışı diye yorumlayamayız. block-01'de basılı55'in9 okunması sürüyor. Son commitlerden sonra yeni dört-vaka uçtan uca STEP doğruluk kanıtı bulunmadı. UI/store çevrimdışı kabulü ve 20 yeni parça seti hâlâ açık.

[Çalıştırılan probe](../eval/audits/20260930-hermes-review6/probe.py) ve [kanıtı](../eval/audits/20260930-hermes-review6/observations.json) eski sonuçları ezmeden kaydedildi.

## W01 — tek okuma üç ayrı ölçek kanıtı olabiliyor

`_bootstrap_calibration` sayı×çizgi çiftlerini sayıyor; farklı okumaları saymıyor. Bir adet40 okuması, üç adet400px çizgiyle eşleşince hiçbir yerleşmiş ölçü olmadan px_per_mm=10, samples=3, spread=0 üretiyor. `_promote_unplaced` aynı okumayı tabloya terfi ettiriyor. `anchor_source=value` geri beslemeyi önlese de ilk ölçek hipotezinin desteği sahte çoğalıyor.

Destek tekil kaynak okuması ve tekil fiziksel çizgi ilişkisiyle sayılmalı; aynı OCR'nin parçaları/tekrarı veya aynı çizginin segmentleri bağımsız destek değildir. Çok sayıda aday çifti ve eşit güçlü ölçek kümeleri kesin ölçek yapmaz. Görünüş/ölçek/birim ayrımı ve tutarlı eşleme gerekir. Yalnız uzunluk benzerliğiyle bulunan aday, ölçü çizgisi/özellik ilişkisi doğrulanmadan kesin geometri sayılmamalı.

## W02 — şüpheli ölçü varken guard çalışmıyor

Üç doğru ölçek gözlemi + bir yanlış9 karşı örneğinde verdict `calibrated_with_suspects`, suspect=['wrong']; `reason_drawing` yalnız `contradictory` durumunda inceleme kontrolü yapıyor. Bu özel kontrol şüpheli ölçüyü durdurmuyor. Bu denetim yanlış STEP üretildiğini iddia etmez; eksik kontrol dalı kaynak ve karşı örnekle kanıtlandı.

Şüpheli ölçü read/records/UI/model-plan/CAD boyunca durumunu korumalı. Çizgi uzunluğundan55 hesaplayıp basılı sayı diye kaydetme; piksel kanıtından yeniden oku veya hedefli soru üret. Çözülmemiş şüpheli ölçü kesin CAD parametresi olmamalı. Taslak ve doğrulanmış sonuç ayrımı uygulansın. Çok ölçekli görünüşü yanlış OCR sanma; görünüş bazlı ölçek kullan. V02 source=user onarımı korunmalı, ancak kaynak sürümü ve gerçek kullanıcı eylemi bağı da ürün kabulünde sınanmalı.

## W03 — etiket uyumu yeniden sayı üyeliğine indirgenmiş

`eval/raster_label_match.py` her sayıyı herhangi bir etiket değerine %4 yakınsa eşleşmiş sayıyor. Tek etiket40 için [40,40,41] üç eşleşme verir. Yanlış konum/rol, yinelenen okuma ve yanlış41 değeri böylece gizlenebilir. Bu geometri uzunluğu toleransı OCR metin doğruluğuna taşınmamalı. `answered_by_nothing` da tuple'ın None olup olmadığına bakıyor, value alanına değil.

Yeni aracı V03 kimlik tabanlı ölçümle birleştir: bir-bir eşleşme, konum dönüşümü, değer/birim/tür, görünüş, özellik rolü ve kaynak kimliği. Ham OCR sayı doğruluğu, ölçü çizgisine bağlama doğruluğu ve son CAD doğruluğu ayrı metrikler. PDF/PNG farklı çözünürlükte; kutular doğru dönüşümle karşılaştırılmalı. Set eşitliği yeterli değildir. Önceki17→18 raporu zayıf sayısal uyum olarak saklanır, yeni metrikle yeniden ölçülür. Etiket/pafta çelişkileri çözülmeden otomatik doğruluk kararı verilmez; v2 dosyaları sessizce değiştirilmez.

## Devam sırası

W01/W02 küçük onarım+regresyon → W03 güvenilir kimlik tabanlı ölçüm →55/9 yeniden okuma, callout/küçük ölçü ve görünüş → aynı dört v2 girdide yeni gerçek paired baseline → ilk kalan semantik/CAD hatası → UI/store ve P01–P08 +20 yeni/en az10 raster kabulü. Sadece yeni probe/rapor üretmek bitiş değildir. Kısa onarımların ardından ürün etkisi ölçülmeli; okumaların tümü kusursuz olana kadar uçtan uca ölçüm ertelenmemeli.

state/next/acceptance içinde eski HEAD ve önceki denetim referansları var. Güncel kod HEAD'i ile her kanıtın ölçüldüğü HEAD ayrı tutulmalı; eski sonuçlar yeni çalışmış gibi güncellenmemeli. Bu inceleme runtime state/acceptance'ı değiştirmedi; devir ve görev sırasını güncelledi.

Başarıya kadar devam, üç başarısız denemede hipotezi değiştirme, tek ağır iş/vaka600s/koşu7200s ve ilkRunPod3USD/toplam20USD sınırları korunur. Sonraki ücretli aşama için ilk raporun kullanıcı tarafından değerlendirilmesi gerekir. Eğitim şu anda fix_rules_first; ara rapor goal bitişi değildir.
