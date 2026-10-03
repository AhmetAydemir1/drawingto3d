# SEMREAD-001B — ölçümü tamamlama planı

4 Ekim 2026 · Mevcut 001B için devam planı. Yeni mimari veya 001C çalışması değildir.

**Karar:** 001B'yi tamamlayalım; ancak sıradaki adım mevcut komutla canlı pilotu başlatmak değil. Önce çağrı bütçesi, VE girdisi ve değerlendirme yolundaki açıklar kapatılmalı. Ardından çizimden gold hazırlanmalı ve aynı sözleşmeyle D/V/VE ölçülmeli.

Bu incelemede model çağrısı yapılmadı; üretim bütçe kaydı değiştirilmedi. Aşağıdaki düzeltmeler henüz uygulanmadı. Bu dosya Hermes'e verilecek devam planıdır.

## 1. Mevcut durum ve kararın gerekçesi

Handoff'taki “referans olmadan bütçe harcamama” kararı doğru. Dar aday sözleşmesi, D adapteri, corpus ve mevcut testler korunabilecek bir başlangıç oluşturuyor. Ancak **“uygulama bitti ve doğrulandı” sonucunu mevcut kanıt desteklemiyor**: testler canlı yolu ve bazı ölçüm hatalarını yakalamamış.

İnceleme sırasında gerçek durum:

- `state.json`: 0 gerçek çağrı; tavanlar development 10, final 20, toplam 30.
- Gold sayısı: 0. Kaydedilmiş D sonucu: `dev-plate-pocket-D`.
- Corpus probe inceleme sırasında tamamlandı ve `corpus-probe.json` oluştu. Yeniden başlatılmamalı.
- D development süreci son kontrolde çalışıyordu. Yeni oturum süreç durumunu yeniden doğrulamalı; aynı işi ikinci kez başlatmamalı. Boş log, sürecin durduğu anlamına gelmez.
- Handoff'taki 107 test başarısını burada baştan çalıştırmadım. Bunun yerine aşağıdaki hatalar için kısa, izole ve sıfır inference kontrolleri yaptım.

İzole kontrol sonuçları ve incelenen kaynak hash'leri: [inceleme kanıtı](/Users/aydemir/.codex/visualizations/2026/10/03/01a10295-f8b2-7762-ae88-985d4a1fbfec/semread-001b-preflight-review.json).

| Öncelik | Somut bulgu | Sonuç / gerekli düzeltme |
| --- | --- | --- |
| P0 | `write_live_attempt`, bütçe fazına sayfanın `split` değerini geçiriyor. Sayaç yalnız `dev` ve `final` sayıyor. İzole testte `frozen` için **31 rezervasyon kabul edildi**, final kullanılan **0** kaldı. | Veri bölümü ile çağrı fazını ayır; fazı doğrula; development, final ve toplam tavanlarını aynı kilit içinde uygula. |
| P0 | VE overlay kimliği `image-overlay`; `PreparedImage` yalnız `image-<sayı>` kabul ediyor. Doğrulayıcı mevcut kimliği reddediyor. | Örneğin ham sayfa `image-1`, overlay `image-2`; gerçek V/VE hazırlama ve HTTP istek oluşturma yolunu model çağırmadan sınayan test ekle. |
| P0 | Aynı hedefte gold `8 mm`, aday `999 mm` iken üst düzey `candidate_precision=1`, `claim_recall=1`. Alan bazındaki `size` hatası ise doğru kaydediliyor. | Üst metrikler aslında bölgesel eşleşme ölçüyor. Bunları öyle adlandır; semantik TP/FP/FN ve precision/recall'u predicate bazında hesapla. |
| P0 | Aday tamamen yoksa genel omission artıyor; fakat size alanının scorable paydası **0** kalıyor. Birimi `null` olan `8` de `8 mm` karşısında doğru sayılabiliyor. | Eksik cevapları alan paydalarından düşürme; birim belirsizliğini gold'dan doldurma. Sayfadaki genel birimden çıkarım varsa kaynak kanıtıyla ayrı taşı. |
| P1 | Recovery/regression yalnız `size` alanına bakıyor; `not_applicable` doğru sayılabiliyor. | Karşılaştırmayı kapsam içindeki her predicate için ortak gold evreninde yap; uygulanamaz alanları başarıya katma. |
| P1 | Referans üreticisinin `build()` yolu, açıklamasının tersine `check_reference()` çağırmıyor. `EKSİK` yer tutucuları ve yalnız `review_flag` yeterli engel oluşturmuyor. | Geçersiz gold yayımlanmasın ve pilotu açamasın; kapsam, kaynak, bölgeler, durumlar ve görsel inceleme doğrulansın. |
| P1 | `evaluate`, gold gelince yeniden `observe()` çağırıyor. Sabit attempt klasörleri tekrar yazılabiliyor; yalnız parsed dosyanın varlığı değerlendirmeye yetiyor. | Kaydedilmiş gözlemlerden değerlendir; attempt'leri değişmez tut; kimlik, durum ve kanıt dosyalarını birlikte doğrula. |
| P1 | B07, hiç çağrı yokken de kapanabiliyor. B05 yalnız frozen sayısını esas alıyor. `--split frozen` **6×2=12** V/VE işi; 20 değil. | Kabulü tam sayfa×kol matrisi ve gerçek kanıt zinciri üzerinden hesapla. Final kapsam 10 sayfa×2 VLM koludur. |

İlgili kaynaklar: [pilot sürücüsü](/Users/aydemir/Desktop/drawingto3d/eval/semread_001b_pilot.py), [V/VE okuyucu](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/semantic_candidate_reader.py), [değerlendirici](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/semantic_evaluation.py), [referans üretici](/Users/aydemir/Desktop/drawingto3d/eval/semread_001b_reference.py).

## 2. Çalışma sırası ve geçiş koşulları

### A. Canlı çağrı öncesi düzeltmeler — 0 inference

Mevcut kodu düzelt; yeni scheduler veya genel değerlendirme framework'ü kurma. Öncelik yukarıdaki P0'lar, ardından gold/kanıt/kabul yoludur.

**Bütçe:** `split ∈ {dev, frozen}` veri özelliğidir; `phase ∈ {dev, final}` çağrının amacıdır. Development sayfası final fazında da çalışabilir. Geçersiz faz/kol reddedilmeli. Faz sınırı ve toplam 30 sınırı atomik denetlenmeli. Yeniden başlatma, timeout, retry ve eşzamanlı rezervasyon tavanı aşamamalı. Gönderilmiş veya gönderilip gönderilmediği belirsiz istekler bütçede kalmalı; sayaç yeniden oluşturulmamalı.

**Gerçek istek yolu:** V için tek ham görsel, VE için aynı ham byte'lar + nötr kimlikli overlay ve gözlem tablosu hazırlanmalı. Test, yardımcı fonksiyonla sınırlı kalmamalı: worker → hazırlama → RecordedChat → HTTP payload sınırına kadar gitmeli; yalnız ağ gönderimi taklit edilmeli. Kimlik–byte sırası, çıktı şeması, mesajlar, gold/meaning sızıntısı ve hata kaydı kontrol edilmeli. Lokal hazırlama hatası gerçek gönderim gibi raporlanmamalı.

**Çalıştırma ve kayıt:** D'nin ağır işlemleri de mevcut ortak LabRunner/lock ve timeout düzenine alınmalı. Vaka 600 saniye, batch 7200 saniye sınırı korunsun. Çalışan başka oturumun işi öldürülmesin; yeni ağır işe başlamadan mevcut işin durumu çözülsün. Gözlem çıktısı kaynak/preprocessing kimliğiyle saklansın; her değerlendirmede OCR tekrarlanmasın.

Her attempt benzersiz ve değişmez olsun. Kaynak, gerçek gönderilen görüntü byte/hash/boyut/ID/sıra, request, raw cevap/hata, parsed çıktı, kapı sonuçları ve runtime kaydı birbirine bağlansın. Eski dosya yeni attempt'e aitmiş gibi okunmasın. Eksik input, boş input listesiyle sessizce geçilmesin.

Üretim kimliği gerçek input/prompt/schema/model/runtime ve ilgili kodu kapsasın. Gold, matching ve **evaluator uygulamasının içeriği** değerlendirme kimliğine girsin. Salt evaluator/gold düzeltmesi geçerli raw prediction'ı yeniden kullanabilsin; otomatik inference doğurmasın. Untracked ilgili kaynaklar hash dışında kalmasın. Commit, bu doğrulamanın önkoşulu değildir.

**Çıkış koşulu:** Yeni hata testleri ve etkilenen mevcut testler geçiyor; dry-run/yerel istek testleri 0 gerçek çağrı; bütçe hâlâ 0/30. Yeni testlerin mevcut bozuk kodda ilgili hatayı yakaladığı gösteriliyor.

### B. Referansı çizimden hazırlama — 0 pilot inference

Önce bir PDF ve bir raster development sayfasında anotasyon biçimini doğrula; ardından 10 sayfanın tamamını bitir. Tam corpus probe'u yeniden koşturmak bunun önkoşulu değil; mevcut çıktı yardımcı veri olarak kullanılabilir.

Her claim için hedef bölgesi, varsa callout bölgesi, alan değerleri/durumları, kaynak kanıtı ve belirsizlik gerekçesi yaz. PDF text katmanı metni okumaya yardım eder; hangi geometriye bağlandığını tek başına kanıtlamaz. Raster OCR çıktısı görsel incelemenin yerine geçmez. Çizimin kendisini incele; STEP, D adayları veya V/VE cevaplarını gold kaynağı yapma. Daha önce görülmüş D çıktısının varlığını anotasyon notunda açık tut.

`annotator=agent`, `review_status=provisional` korunmalı. İnsan onayı varmış gibi yazılmamalı. Provisional referansla bu keşif pilotu yapılabilir.

Validator en az şunları zorlamalı:

- Manifestle aynı page/source hash ve koordinat çerçevesi; geçerli, sonlu, sınır içi bbox. Hatalı bölgeyi sessizce kırparak düzeltme.
- Gerçek kapsam/exhaustiveness, kanıt ve alan durumları; `EKSİK` gibi yer tutucular hata.
- `determinate_present`, `determinate_absent`, `underdetermined` ayrımı. Bir alandaki belirsizlik başka alandaki bilinen değeri silmemeli.
- Görsel doğrulama eksiği veya çözülemeyen observation ID denetimi geçilmiş sayılmamalı. Observation ID zorunlu değil; verilmişse doğrulanmalı.
- Anotasyon dışında kalan bölge otomatik negatif/FP sayılmamalı.

Bir sayfanın kapsam uygunluğu şüpheliyse **model sonuçlarını görmeden**, çizim içeriğine göre karar ver. D'nin zayıf performansı veya OCR gürültüsü değiştirme gerekçesi olmasın. Kapsam için gerçek değişiklik gerekiyorsa eski manifesti koru, gerekçeyi yaz ve split/grup bütünlüğünü yeniden doğrula.

**Çıkış koşulu:** 10/10 geçerli gold; sayfa ve predicate kapsam tablosu; provisional niteliği; gold hash manifesti. Bundan sonra gold, model cevabına uyacak şekilde değiştirilmez.

### C. Değerlendiriciyi ve D taban çizgisini tamamla — 0 inference

Önce küçük, elle sonucu bilinen sentetik örneklerle ölçümü doğrula. Ardından mevcut geçerli D çıktısını kimliği uygunsa kullan; eksik D sayfalarını kontrollü tamamla. Bu aşamada D algoritmasını paftalara özel iyileştirme; yalnız adapter/entegrasyon hatalarını düzelt ve etkisini kaydet.

Asgari ölçüm sözleşmesi:

| Durum | Beklenen davranış |
| --- | --- |
| Hedef doğru, değer yanlış | Bölgesel eşleşme başarılı olabilir; ilgili semantik predicate doğru sayılmaz. Örneğin pozitif size iddiasında yanlış değer FP ve kaçırılmış doğru değer FN oluşturur. |
| Pozitif, scorable hedefte boş yanıt/timeout/parse hatası | İlgili predicate için omission/FN; ortak paydadan çıkarılmaz. Teknik hata türü ayrıca korunur. |
| Hiç çalıştırılmamış hücre | `not_run`; pilot eksik kalır. Gerçek timeout ile karıştırılmaz. |
| Fazladan aday | Yalnız anotasyonun kapsadığı ve yargılanabilir bölgede FP olarak puanlanır; kapsam dışı ayrı raporlanır. |
| Unknown veya underdetermined | Doğru kesin bilgi üretmiş gibi TP yazılmaz. Çekimserlik ve aşırı kesin iddia ayrı ölçülür. Uygulanamaz alan recovery hesabına girmez. |
| Eşleştirme belirsiz | Önceden belirlenmiş politika uygulanır; keyfi eşleşme kesin doğru gibi sunulmaz. Beklenen değer eşleşme seçmek için kullanılmaz. |
| Değer/birim/count | Değer ve birim hataları ayrı görülebilir; genel birim ancak kaynakla çıkarılır. Yazılı count tam sayı eşitliğiyle değerlendirilir. |

Her predicate için TP/FP/FN, precision/recall, omission, abstention ve hata dökümü olsun. Sayısal toleranslar basılı değer okuma amacına göre gerekçelendirilsin; geometrik tolerans doğrudan metin okuma toleransı sayılmasın. Sıfır payda `null` kalsın.

Recovery/regression tüm kapsam alanlarında aynı gold evreni üzerinden hesaplanmalı:

```text
recovered = D'nin doğru üretemediği, karşı kolun doğru ürettiği scorable alanlar
regressed = D'nin doğru ürettiği, karşı kolun yanlış/eksik ürettiği scorable alanlar
net_correct_gain = recovered - regressed
recovery_rate = recovered / D'nin doğru üretemediği scorable alan sayısı
regression_rate = regressed / D'nin doğru ürettiği scorable alan sayısı
```

Yanlış iddiaya regresyon ile çekimserliğe/omission'a regresyon ayrı tutulmalı. VE–V karşılaştırması da aynı kurala uymalı. Yeni yanlış adaylar ayrıca raporlanmalı; net gain bunları gizlememeli.

**Çıkış koşulu:** 10 D hücresinin durumu kayıtlı; eksik koşu yok; evaluator negatif testleri geçiyor; değerlendirme yalnız saklanan artefaktları okuyarak çalışıyor. D doğruluğu ilk kez burada söylenebilir. Önceki `pass`, semantik doğruluk kanıtı değildir.

### D. Sınırlı development V/VE denemesi

Gold ve yerel kontroller tamamlandıktan sonra iki development sayfasında eşli deneme yap: bir PDF + bir raster, her birinde V ve VE. **Başlangıç hedefi 4 çağrı; development tavanı 10.**

Gerçek model digest/runtime, ham görüntü eşitliği, VE overlay'i, request kaydı, schema/reference/coverage/truncation sonuçları ve süre/token kayıtlarını doğrula. Sorun varsa önce sebebini düzelt; aynı hatayı bütçeyi tüketerek tekrar etme. Frozen prediction sonuçlarını geliştirme sırasında açma.

**Çıkış koşulu:** Gerçek V ve VE yolları incelendi; teknik hatalar kapatıldı; final için prompt, preprocessing, schema, model/options, gold ve evaluator sürümleri sabitlendi. Modelin kötü cevabı testi gevşetme gerekçesi değildir.

### E. Final matrisi tamamla

Final ölçüm **10 sayfa × D/V/VE = 30 sonuç hücresi** içerir. Bunun VLM kısmı **10 × V/VE = 20 hücredir**:

| Veri bölümü | D | V | VE | VLM final hücresi |
| --- | ---: | ---: | ---: | ---: |
| Development: 4 sayfa | 4 | 4 | 4 | 8 |
| Frozen: 6 sayfa | 6 | 6 | 6 | 12 |
| Toplam | 10 | 10 | 10 | 20 |

Bu tablo yeni çağrı adediyle karıştırılmamalı. Aynı nihai üretim kimliğiyle alınmış geçerli development cevabı yeniden kullanılabilir; eski faz kaydı değiştirilmez, final hücresi o attempt'e referans verir. Yeniden kullanım sonucu güzel olduğu için seçilmez; politika teknik geçerliliğe dayanır ve önceden sabitlenir.

Örneğin 4 development cevabı değişmeden kullanılabiliyorsa finalde 16 yeni çağrı yeterlidir; kullanılamıyorsa 20 gerekir. Development ≤10, final için yeni çağrı ≤20 ve toplam ≤30 sınırları her durumda korunur. Finaldeki timeout/parse failure da çağrı ve sonuçtur; sessiz tekrar hakkı doğurmaz.

**CLI düzeltildikten sonra önerilen kullanım:** Aşağıdaki `--phase` parametresi mevcut sürümde yoktur; önce uygulanıp test edilmelidir. Bu komutlar mevcut koda olduğu gibi verilmemelidir.

```bash
cd /Users/aydemir/Desktop/drawingto3d
.venv/bin/python eval/semread_001b_pilot.py --dry-run --phase final --arms V,VE
# Plan: 20 final VLM hücresi; yeniden kullanılacak attempt'ler ve kalan gerçek çağrılar ayrı.
# --split verilmemesi bütün 10 sayfanın kapsanması içindir.
.venv/bin/python eval/semread_001b_pilot.py --live --phase final --arms V,VE
.venv/bin/python eval/semread_001b_pilot.py --evaluate
```

Handoff'taki yalnız `--split frozen` komutu finalin development bölümünü tamamlamaz. Worker'lar da fazı açıkça almalı; üst komutta parametre eklemek tek başına yeterli değildir.

**Çıkış koşulu:** Tam matris; her hücrede seçilen attempt ve geçerlilik/failure durumu; doğru çağrı günlüğü; tekrar üretilebilir değerlendirme. Frozen sonuç görüldükten sonra aynı deneyin prompt veya gold'u başarı yükseltmek için değiştirilmez.

## 3. Teslim ve kabul

Mevcut B01–B07 korunmalı; koşulları gerçek kanıta bağlanmalı:

| Kabul | Kapanma kanıtı |
| --- | --- |
| B01 | 001A snapshot hash bütünlüğü ve ayrı bütçe; tarihsel 16/16/0 korunmuş. |
| B02 | 10/10 doğrulanmış gold, split/grup/kapsam bilgileri ve dondurulmuş manifest. |
| B03 | D adapteri ve V/VE yolları için gerçek entegrasyon testleri; dosyanın varlığı yeterli değil. |
| B04 | Semantik TP/FP/FN, omission, belirsizlik ve recovery/regression için bilinen sonuçlu negatif testler. |
| B05 | Aynı final sözleşmesinde 30 hücre; başarısız çalıştırmalar dahil eksiksiz durum ve kanıt. |
| B06 | Dev/frozen ayrı sonuçlar, predicate bazlı farklar, kaynaklı hata örnekleri ve maliyet. |
| B07 | Bütçe günlüğü, attempt bütünlüğü, kimlik/cache doğrulaması; boş kayıt başarı değil. |

Final rapor şu soruyu yanıtlamalı: **V veya VE, D'nin kaçırdığı hangi bilgiyi kazanıyor; bunun karşılığında hangi yeni hataları ve ne kadar maliyeti getiriyor?**

Rapor ve makinece okunur sonuçlar şu ayrımları korusun: görüntüde adreslenebilirlik/semantik doğruluk; yanlış iddia/çekimserlik; development/frozen; teknik failure/not_run; referansın provisional niteliği. İşleme/OCR, model ve değerlendirme süreleri ayrı olsun. İlk D örneğinin 2.985 saniyesi `observe()` sonrasında ölçüldüğü için tam sayfa uçtan uca süre olarak kullanılmasın. Gözlemlerin cache'den okunup okunmadığı yazılsın.

V/VE'nin D'yi geçmesi completion şartı değildir. Eksiksiz ve geçerli negatif sonuç da 001B'yi tamamlar. Sonuçlara göre V veya VE'yi ilerletme, sınırlı bir hatayı araştırma ya da bu yaklaşımı durdurma kararı **ayrıca** verilir; otomatik 001C/verifier/fusion/CAD/eğitim çalışması başlatılmaz.

## 4. Hermes'e verilecek işin tek cümlelik özeti

**Mevcut SEMREAD-001B'yi, önce sıfır inference ile bütçe/VE/evaluator/gold/kanıt açıklarını kapatarak; sonra 10 sayfanın gold'unu, D taban çizgisini ve en fazla 30 yeni çağrı sınırı içinde sabit D/V/VE pilotunu tamamlayarak bitir. “Uygulama tamam” yerine kanıtlanmış ölçümü teslim et.**

Commit ve skill'e referans ekleme bu ölçümün önkoşulu değil; şu an çalışma kapsamını genişletmesin.
