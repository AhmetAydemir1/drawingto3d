**drawingto3d — Revize Semantic Reader yanıtına ikinci değerlendirme**

Tarih: 3 Ekim 2026 · İncelenen yerel HEAD: `4fb09b6`

İncelenen belge: [SEMANTIC_READER_REVISED_RESPONSE_20261003.md](/Users/aydemir/Downloads/SEMANTIC_READER_REVISED_RESPONSE_20261003.md)

Bu değerlendirme planlama görüşüdür. Kaynak kodu incelendi; yeni model deneyi veya ürün testi çalıştırılmadı. Aşağıdaki sayısal örnek açıklama amaçlıdır, ölçülmüş sonuç değildir. Belgedeki geliştirme önerileri bu incelemede uygulanmadı.

**1. Kararım: ana mimaride uzlaşma var; geniş bir yeniden planlama gerekmiyor**

Revizyon önceki önemli açıkları karşılıyor:

- Mevcut ID olmadan bölge referansıyla yeni feature adayı bildirilebiliyor.
- Candidate, Verification, UserDecision ve BuildEligibility ayrılıyor.
- Modelin kendi `supported` beyanı kabul kararına dönüşmüyor.
- Deterministic/VLM uyuşması tek başına doğrulama sayılmıyor.
- Mevcut `llama.py` ve lab runner yeniden kullanılıyor.
- İlk FeaturePlan mevcut plate ailesiyle sınırlanıyor.
- D/V/VE/F karşılaştırması, recovery/regression ve gerçek kullanıcı emeği plana giriyor.
- Ground truth çizimden bilinebilen bilgiye göre tanımlanıyor.
- Guided review fusion aşamasına, adapter ilk CAD entegrasyonunun içine geliyor.
- Yerel quantized model değerlendirmesi eğitim sonrasında da korunuyor.

Bu temelde SEMREAD-001A'nın küçük tutulmasına katılıyorum. Ancak aşağıdaki ölçüm ve doğrulama düzeltmeleri nihai uygulama planına işlenmeli. Bunlar yeni bir framework gerektirmiyor.

**2. Runner konusunda önceki değerlendirmemi düzeltiyorum**

Revize yanıtın §2.5 ve §8'de yaptığı düzeltme doğru.

[state.py içindeki code_fingerprint()](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d_lab/state.py:73), `git ls-files` ile izlenen bütün dosyaların çalışma ağacındaki içeriklerini hash'liyor. `WATCHED_FILES` tek kaynak değil; buna eklenen bir liste.

Önceki değerlendirmemde `runner.py` tarafındaki sabit listeyi görüp kapsamı yeterince takip etmemişim. “Fingerprint yalnız birkaç dosyayla sınırlı” çıkarımını geri alıyorum.

İnce ayrım: tracked dosyanın değişikliği henüz commit edilmemiş olsa da mevcut içerik hash'e girer. Commit zorunlu değil. Ancak ilk kez oluşturulan untracked `semantic_reader.py` gibi dosyalar otomatik olarak bu kapsama girmez. Pilot geliştirilirken bunlar da açık watched/input listesinde yer almalı veya başka bir yöntemle gerçek kod kimliğine katılmalı.

Model digest'i, gönderilen görseller, corpus, schema/prompt içeriği ve runtime ayarlarının deney kimliğinde bulunması yönündeki öneri geçerli. Hash'lenmesi gereken bir girdinin varlığını ayrıca doğrulamak gerekir; eksik girdi sessizce atlanmışken deney tamam kabul edilmemeli.

**3. Düzeltilmesi gereken ilk karar: `recovery > regression` geçerli bir fayda kapısı değil**

İlgili bölümler: §12, §14.1 ve §24/9.

Revizyonda recovery, baseline'ın kaçırdıkları üzerinden; regression ise baseline'ın doğru bildikleri üzerinden oranlanıyor. Paydaları farklı iki oranı doğrudan karşılaştırmak toplam iyileşmeyi göstermez.

Örnek: Aynı 100 hedef iddia üzerinde D hattı 90 doğru sonuç üretmiş ve 10 iddiayı kaçırmış olsun.

| Değişim | Sayı | Kendi oranı |
|---|---:|---:|
| F, D'nin kaçırdığı 10 iddiadan 5'ini kurtarıyor | +5 | recovery = %50 |
| F, D'nin doğru bildiği 90 iddiadan 9'unu bozuyor | −9 | regression = %10 |

Önerilen kapı geçer: `%50 > %10`. Oysa doğru sonuç sayısı `90 + 5 − 9 = 86` olur; sistem kötüleşmiştir.

Recovery ve regression oranlarını raporda koruyalım. Faydayı karşılaştırırken aynı hedef evreni ve aynı sayım birimini kullanalım:

```text
net_correct_gain = recovered_count - regressed_count
normalized_gain = net_correct_gain / total_target_count
```

Bu formül, hedef iddiaların durum değişimini sayar. Yanlış yeni feature üretimi, kritik hatanın şiddeti, belirsizliğe düşme ve kullanıcı maliyeti ayrıca değerlendirilmelidir. Delik sayısını, çap iddiasını ve pafta sayısını aynı sayaçta karıştırmamalıyız.

Araştırma kararını da tek eşitsizliğe indirmeyelim. Öneri:

- Aynı kapsamda doğru otomatik çözüm/coverage farkını raporla.
- Recovery ve regression'ı ham adetleriyle birlikte göster.
- Kritik yanlış kabulü ayrı bir sınır olarak uygula.
- Kullanıcı emeği ve çalışma maliyetini ayrıca raporla.
- Tekrarlanabilir bir görev kazanımı varsa, faydalı kapsamı daraltarak devam etme seçeneğini koru.

İlk prototipte net kazanım olmaması araştırmanın mutlaka bitmesi anlamına gelmez. Ancak negatif toplam sonuç, oranlar karşılaştırılarak pozitif fayda diye sunulamaz.

**4. `wrong-supported = 0` kapısının yanına coverage ve örneklem büyüklüğü gerekiyor**

İlgili bölüm: §14.2.

İlk holdout'ta kritik yanlış kabul görülmemesini istemek makul bir muhafazakâr pilot koşulu. Fakat tek başına otomasyona geçiş için yeterli değil.

İki açık var:

1. Her iddiayı `pending` yapan sistemin de yanlış `supported` sayısı sıfırdır.
2. Az sayıda kabulde sıfır hata gözlenmesi, gerçek hata oranının sıfır olduğunu kanıtlamaz.

Bu nedenle her scope için en az şu değerler birlikte raporlanmalı:

```text
eligible_target_count
supported_claim_count
correct_supported_count
wrong_supported_count
coverage
part/drawing group count
critical error classes
```

`0/20` ve `0/2000` yanlış kabul aynı kanıt gücünde değildir; aynı çizimdeki ilişkili iddialar da 2000 bağımsız örnek gibi değerlendirilmemeli. Sıfır kabul varsa supported precision tanımsızdır; yüzde yüz yazılmamalı.

Ürün terfisi için sıfır gözlenen kritik hatanın yanında önceden belirlenmiş minimum coverage, yeterli görev çeşitliliği ve kabul sayısı olmalı. Sonuçların belirsizliği belirtilmeli. İlk karar kapsamla sınırlı kalmalı; başarılı pilot genel çizim güvenilirliği iddiasına dönüşmemeli.

**5. SEMREAD-001B'nin metrikleri ile verifier sırası çelişiyor**

İlgili bölümler: §16, §17/001B, §20 ve §25/001B.

Revize sırada minimal verifier/F hattı, 001B ve 001C'den sonra geliyor. Buna rağmen 001B'de `wrong-supported` raporlanması isteniyor. Oysa `supported` yalnız uygulama/verifier tarafından üretilecek.

Verifier yokken uygulamanın yanlış kabul oranı anlamlı biçimde ölçülemez. Model adayının yanlış olması ile uygulamanın o yanlış adayı kabul etmesi farklı ölçümlerdir.

İki tutarlı seçenek var:

| Seçenek | 001B'de ölçülen | Sonraya kalan |
|---|---|---|
| B'yi yalnız candidate pilotu tut | Candidate correctness, omission, binding, R/Ø/count, belirsizlik davranışı ve maliyet | Verifier sonrası wrong-supported ve accepted coverage |
| Dar verifier'ı B'ye al | Candidate kalitesi + dar kapsamlı uygulama kabul kalitesi | Daha geniş fusion ve guided davranış |

Ben ilk seçeneği tercih ederim: ilk semantic pilotu küçük tutar ve verifier kalitesiyle model kapasitesini ayırır. Verifier/F eklendiğinde sistem katkısı ayrıca ölçülür.

Recovery/regression isimleri de aşamaya bağlanmalı:

```text
001B: candidate_recovery_V_vs_D / candidate_recovery_VE_vs_D
F sonrası: accepted_recovery_F_vs_D / accepted_regression_F_vs_D
```

F henüz çalışmıyorken F'ye ait metrikler doldurulmamalı.

Bir bağlı eksik daha var: D çıktısının ortak değerlendirme sözleşmesine dönüşümü. [meaning.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/meaning.py:46) şu an `distance/diameter/radius` iddiaları ve count gibi alanlar taşıyor; genel bir hole/through/blind semantic inventory'si değil.

D için yeni bir akıllı okuyucu eklemeden mevcut çıktıyı ortak predicate'lere eşleyen küçük bir adapter tanımlanmalı. Üretemediği predicate `not_produced/abstained` olarak kalmalı. Bu coverage eksikliğidir; yanlış kesin iddia değildir. Mevcut `confirmed` alanı da kontrolsüz biçimde yeni sistemin `supported` alanına eşlenmemeli.

**6. İlk verifier'da circle ile hole hâlâ karışıyor**

İlgili bölüm: §20, “Circle/hole visual presence”.

“Mevcut circle primitive veya kontrollü image region candidate var mı?” kontrolü bir çember temsilinin varlığını gösterebilir. Fiziksel feature'ın delik olduğunu tek başına göstermez. Bir çember bir çıkıntının veya başka bir dairesel özelliğin temsili de olabilir.

Benzer şekilde modelin kendi gösterdiği region'ın geçerli olması, region içindeki semantic yorumun doğruluğunu kanıtlamaz.

Şu iddialar ayrılmalı:

```text
circle_representation_present
physical_hole_present
callout_applies_to_feature
hole_termination_is_through
```

Örnek kontrol sözleşmesi:

| İddia | Kontrol edilebilen kanıt | Yetmediğinde |
|---|---|---|
| Görünüşte dairesel temsil var | Kaynağa bağlı circle/ink kontrolü | pending veya başka kanıt ara |
| Bu temsil fiziksel delik | İlgili callout/kesit/başka destekleyici ilişki | ambiguous/checker_missing |
| THRU bu deliğe ait | THRU metni + bu feature'a çözülen scope/binding | Metin okunmuş olsa da feature sonlanmasını kabul etme |

Revizyonun genel prensibi doğru; §20'deki somut verifier tanımı da aynı ayrımı uygulamalı. Aksi hâlde modelin bulduğu adayı yine adayın varlığıyla doğrulamış oluruz.

**7. Kabul edilebilir süre ve kullanıcı emeği yalnız deneyden çıkmaz**

İlgili bölüm: §26/9–10.

Deney bize p95 drawing süresinin ne olduğunu veya kaç kullanıcı düzeltmesi gerektiğini gösterir. Bunun kullanıcı için kabul edilebilir olup olmadığı ürün kararıdır.

Dolayısıyla iki alan ayrılmalı:

```text
measured_p95_seconds        → deney sonucu
maximum_acceptable_seconds  → ürün hedefi

measured_user_corrections   → deney sonucu
maximum_acceptable_effort   → ürün hedefi
```

001A için ürünün bütün hedeflerini kesinleştirmek gerekmez. Pilotun timeout/çağrı/bellek bütçesi baştan tanımlanabilir. Model seçimi veya otomasyona terfi öncesinde kabul eşikleri sonuçlara bakılarak geriye dönük ayarlanmamalı.

4B/8B ve crop politikasını veriden seçelim; kullanıcı ihtiyacını modelin sağlayabildiğine göre sessizce yeniden tanımlamayalım.

**8. 001A için küçük ama gerekli iki uygulama ayrıntısı**

001A'nın semantic mühendislik doğruluğu istememesine katılıyorum. Bununla birlikte yalnız request manifest'i üretebildiğimizi göstermek, görüntünün model davranışına ulaştığını kanıtlamaz.

Bir basit görsel pozitif kontrol ekleyelim: iki görselde farklı büyük semboller/işaretler bulunsun, istem bunların içeriğini söylemesin. Görsel sırası değiştirildiğinde veya crop değiştirildiğinde modelin yanıtının doğru görselle ilişkili kaldığını kontrol edelim. Bu, teknik çizimi anlamayı test etmez; modelin görselleri kullanabildiği ve kimlik-sıra eşlemesinin çalıştığına küçük bir uçtan uca kanıt sağlar.

Bu kontrol başarısız olursa tek başına taşıma hatası teşhisi konmaz; girdi, runtime ve model davranışı ayrıştırılır. Başarılı transport/schema kaydı da görsel okuma başarısı diye sunulmaz.

İkinci ayrıntı, önerilen `ChatImage` metadata'sının sahibidir:

- `width`, `height`, `sha256` çağıranın beyanına güvenilerek kullanılmamalı; uygulama bunları gönderilecek son byte'lardan hesaplamalı veya doğrulamalı.
- Resize varsa hash ve boyutlar resize sonrasına ait olmalı; kaynağa dönüşüm güncellenmeli.
- Prompt içindeki `image_id` ile payload görüntü sırası tek yerde kurulmalı.
- Aynı çağrıda `images` ve eski `image_png` birlikte verilirse davranış açık olmalı; önerim belirsiz bir birleştirme yerine hata vermesi.
- Bbox dönüşümünün doğruluğu bağımsız köşe/merkez örnekleriyle kontrol edilmeli. Geçerli aralıkta bbox, doğru crop eşlemesi demek değildir.

Ek olarak 001C'deki bir miss ve bir belirsizlik fixture'ı mekanizma testi için yeterli bir başlangıçtır. “Genel olarak extractor sınırını aşıyoruz ve uydurmuyoruz” sonucunu tek başına kanıtlamaz. Bu iddia daha geniş semantic benchmark'a ait kalmalı.

**9. Diğer agent'a önerdiğim son değişiklik listesi**

Yeni geniş bir mimari belgeye ihtiyaç görmüyorum. Mevcut revizyona şu değişiklikler işlensin:

1. §14.1: `recovery > regression` kapısını kaldır; aynı hedef evreninde ham adet/net katkı, kritik hata ve maliyet koşullarını kullan.
2. §14.2: sıfır gözlenen yanlış kabulün yanına minimum coverage, kabul/pafta sayısı ve belirsizlik raporunu ekle.
3. §17/001B ve §25/001B: candidate metrikleri ile verifier/F metriklerini ayır; D için ortak çıktı adapter'ını tanımla.
4. §20: circle representation ile physical hole iddialarını ayır; geçerli region adresini semantic doğrulama sayma.
5. §26: ölçülen performansla ürünün kabul sınırını ayır.
6. §17/001A ve §19: görsel pozitif kontrol, son byte'lardan metadata, görüntü ID/sıra eşlemesi ve compatibility davranışını ekle.

Runner düzeltmesini kabul ediyorum. Dar FeaturePlan, mevcut istemciyi genişletme ve küçük 001A teslimi üzerinde uzlaşma var. Bu maddeler kapandıktan sonra ilk teknik işin sınırı yeterince belirgin olacaktır; sonraki tartışmayı gerçek 001A/001B çıktıları üzerinden yapmak daha faydalı olur.
