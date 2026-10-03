**Hermes /goal — SEMREAD-001B: tek modelle dar semantic aday pilotu**

4 Ekim 2026. Bu metin Hermes'e verilecek uygulama talimatıdır; bu dosyanın hazırlanması modeli veya Hermes'i başlatmaz. 001B için yeni ve ayrı bütçe: en fazla 30 gerçek inference. 001A'nın kullanılan 16 çağrısı tarihsel kayıtta korunur.

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde yalnız SEMREAD-001B'yi uygula ve ölç: mevcut deterministic hat (D), ham çizimi gören yerel model (V) ve aynı çizimle adreslenebilir gözlemleri gören model (VE) için ortak sözleşmeli, kaynak gösteren dar semantic aday pilotu oluştur. Sabit gerçek çizimlerde doğruluk, omission, target binding, recovery/regression ve maliyeti karşılaştır. Sonucu olumlu göstermek değil, gerçek katkıyı ölçmek bu goal'ün hedefidir.

1. BAĞLAM, BAŞLANGIÇ VE SINIR

Geçerli AGENTS.md varsa uygula. docs/SEMANTIC_READER_REVISED_REVIEW_20261003.md, docs/HERMES_SEMREAD_001A_PLAN.md ve /Users/aydemir/Desktop/HERMES_SEMREAD_001A_HANDOFF.md dosyalarını oku. 001A'nın güncel kanıtı out/lab/semread-001a/acceptance.json ve continuations/semread-001a-identity-20261004 altındadır. Güncel kaynak ve dosyalar rapor anlatımından önce gelir.

Bu goal eski revize plandaki 001B kapsamını açıkça günceller: yalnız kurulu qwen3-vl:8b-instruct ile D/V/VE ölçülür; 4B/8B karşılaştırması ve verifier sonraya kalır. Bu kapsam daraltmasını raporda yaz. F/fusion, supported kararları, FeaturePlan/CAD/STEP, 001C adaptive discovery, eğitim/LoRA, UI, ikinci model, bulut ve runtime/model indirme kapsam dışıdır. Pocket/cavity ve kapsamlı cross-view çözümü completion şartı değildir.

Önce 001A kodunu ve gitignored kanıt paketini hash manifestli, geri kazanılabilir bir snapshot ile sabitle; mevcut ilgili tracked/untracked dosyaları dahil et, ilgisiz kullanıcı işini değiştirme. Commit kullanırsan yalnız ilgili dosyaları al; reset/clean/stash yapma. Tarihsel üretici kimliğini koru. 001B geliştirilince değişen global fingerprint nedeniyle eski 001A'yı otomatik tekrar çalıştırma veya yeni kimlikle damgalama; eski başarı kendi snapshot'ına aittir. Etkilenen compatibility testleri yine çalıştırılmalı.

001A gerçek kullanımının 16 olduğunu doğrula. Önceki goal'ün yetkili tavanı 16 iken state 18 gösteriyordu: geçmiş uzatma kaydını silmeden yetkili kalan çağrının sıfır olduğunu bir düzeltme kaydında açıkla. 001A'dan çağrı payı aktarma. Bu goal 001A için yeni inference yetkisi vermez.

2. DAR ÇIKTI SÖZLEŞMESİ

İlk semantic kapsam: circle representation / physical hole adayı ayrımı; R ile Ø ayrımı; basılı değer ve birim; count; THRU / finite-depth / unknown sonlanma; açıkça yazılmış derinlik; callout→target binding. Circle bulundu diye hole, derinlik yazmıyor diye THRU, hatch var diye cavity sonucu çıkarma. Belirsizlik alan bazında ifade edilebilsin.

001A'nın generic description/shape probe'unu ürün ontology'si gibi genişletme. Mevcut llama.py, RecordedChat, semantic_images ve kaynak referans altyapısını kullanarak küçük, ayrı sürümlü bir semantic candidate schema ve okuma yolu ekle. Model doğrudan CAD kodu veya supported/confirmed/source=user kararı üretmesin.

Her adayda en az candidate_id, predicate/type, value+unit veya unknown, kaynak image_id ve normalize region referansı, varsa observation_id/callout region/target region, candidate provenance ve uncertainty gerekçesi olsun. Kaynak hash/page/transform uygulama manifestinden bağlansın; model bu kimlikleri uydurmasın. Observation ID'si olmayan fakat geçerli region gösteren aday kabul edilebilsin; extractor'ın hiç temsil etmediği bölgeyi bildirmek yasaklanmasın. Geçerli bbox yalnız adres doğrulamasıdır, semantic doğruluk değildir.

Fiziksel feature ile görünüşteki temsili ayrı tut; aynı deliği iki görünüşte iki delik sayma. NxØd callout'undaki yazılı count ile bulunan circle sayısını farklı alanlarda taşı. Physical grouping veya view role belirlenemiyorsa unknown bırak. Tek aday içinde çözülen/çözülemeyen alanları sakla; bir alanın bilinmemesi doğru okunan diğer alanları silmesin.

3. D / V / VE KOŞULLARI

D: Mevcut observe/perceive/bind/meaning çıktısını ortak predicate sözleşmesine çeviren küçük adapter. Yeni akıllı okuyucu veya hedef fixture'a özel düzeltme ekleme. Üretemediği predicate not_produced/abstained olsun; bu yanlış kesin iddia değildir. Mevcut resolution=confirmed yeni supported statüsüne dönüşmesin. D yolunda gerçek VLM inference yapılmadığını doğrula; VisionReader/AgreeingReader gibi varsayılanları yanlışlıkla D'ye katma. Mevcut OCR/CV ve basılı PDF text katmanı kullanılabilir; hangi yolun kullanıldığını kaydet.

V: Yalnız ham full-page görüntüsü, nötr image ID ve ortak görev prompt'u. Deterministic semantic yorum veya observation overlay verilmez.

VE: V ile byte düzeyinde aynı ham full-page + gerçek observation overlay + sınırlı, adreslenebilir observation tablosu. Tablo mevcut gözlem ID/text/primitive/region bilgileriyle sınırlı olsun; gold, meaning sonucu veya D'nin nihai semantic kararını truth olarak verme. Gözlemler yanlış olabilir; modelin bunları sorgulayabileceğini belirt.

V ve VE aynı çıktı schema'sı, görev talimatı, model/digest ve generation ayarlarıyla çalışsın; fark yalnız observation girdisi olsun. VE'nin daha fazla görüntü/token taşıdığını maliyette göster. Nötr ID'leri kendi görsel mesajlarına bağlayan per_image_message_labeled yolunu kullan. İlk pilotta adaptive crop, çok turlu zoom ve farklı çözünürlük matrisleri açma. Full-page hazırlama/resize politikasını development aşamasında belirleyip final karşılaştırma öncesi sabitle.

4. CORPUS VE REFERANS

Mevcut examples/ çizimlerinden 10 kaynak sayfa seç; en az 8 bağımsız parça grubu, hem PDF hem raster ve kapsam içindeki callout çeşitliliği hedefle. Aynı parçanın PDF/PNG sürümleri bağımsız örnek sayılmaz. 4 development ve 6 frozen-evaluation sayfası belirle; parça/template grupları iki tarafa dağılmasın. 001A'da kullanılan plate/flange gibi önceden incelenmiş örnekleri development'a ayır. Bu küçük ve önceden bilinen repo corpus'unu bağımsız holdout diye sunma.

Manifestte kaynak hash'i, sayfa, parça grubu, split, kapsam ve seçim gerekçesi bulunsun. Yeterli bağımsız/kapsamlı çizim yoksa örnek sayısını kopya varyantlarla doldurma; mevcutlarla bağımsız uygulama/test işlerini tamamla, corpus eksikliğini açık bırak. Yerel kaynaklar yetmiyorsa kendiliğinden internetten dataset veya model indirme.

Semantic prediction'ları çalıştırmadan önce çizimin kendisinden referans annotation oluştur: hedef feature/representation, predicate, değer/birim, callout ve target region, determinate_present / determinate_absent / underdetermined, gerekçe ve source evidence. Komşu STEP dosyalarını, generator parametrelerini veya model prediction'larını referans üretiminde kullanma. Görsel inceleme ile okunabilir metin/geometriyi karşılaştır; net olmayanı tahmin ederek gold yapma.

Referansı agent hazırladıysa annotator=agent, review_status=provisional yaz; gerçek insan onayı yokken human_verified deme. Mevcut insan onaylı referans varsa kaynağını koru. Provisional referansla pilot çalışabilir, ancak metrikler bu niteliği açıkça taşımalı; ürün doğruluğu sertifikası değildir.

Gold ve değerlendirme kuralları prediction girdilerinden ayrı kalsın. Model yalnız açıkça hazırlanmış görüntüleri ve izinli metni alsın; dosya adı, gold klasörü, answer key veya yanındaki STEP context'e eklenmesin. Her iki VLM kolunda sentinel testiyle bu ayrımı doğrula. Final koşu öncesinde corpus/gold/schema/prompt/evaluator hash'lerini sabitle. Frozen-evaluation sonucunu gördükten sonra aynı koşunun prompt'unu veya beklenen cevabını değiştirip başarıyı yükseltme. Gerçek annotation hatası bulunursa eski sonucu koru; düzeltmeyi yeni referans sürümü ve gerekçesiyle ayrıca raporla.

5. EVALUATOR VE METRİKLER

D/V/VE aynı hedef evreni, eşleştirme kuralları ve predicate birimleriyle değerlendirilsin. Aday–referans eşleştirmesi kaynak/region/target ilişkisine dayansın; beklenen sayısal değere bakarak en uygun adayı seçme. Eşleşmeler bire bir olsun; kopya adaylar recall'u artırmasın. Birim normalizasyonu, sayısal/region toleransları ve belirsiz eşleşme politikası final prediction öncesi sabitlensin.

Gold'un exhaustiveness kapsamını yaz. Annotation bulunmayan her bölgeyi otomatik determinate_absent veya false-positive sayma. Scorable olmayanlar ayrı kalsın; scorable hedefte timeout/parse failure/boş yanıtı metrikten düşürme, okunamayan/kaçırılan olarak göster.

Her predicate ve kol için TP/FP/FN, candidate precision/recall, omission, correct-target binding, R/Ø karışması, değer/birim hatası, count hatası, through/depth hatası ve underdetermined durumda kesin iddia üretimi raporlansın. Aday doğruluğu ile kaynak referansının geçerliliğini ayrı ölç. D'nin üretemediği alanları ve bütün bilinmeyenleri görünür tut; hiç cevap vermeyerek yüzde yüz başarı elde edilmesin. Payda sıfırsa oran null/not_applicable olsun.

V vs D ve VE vs D için aynı gold claim'leri üzerinde recovered_count, regressed_count ve net_correct_gain=recovered_count-regressed_count hesapla. Regresyonu yanlış adaya dönüşme ile abstention/omission'a dönüşme olarak ayır. Recovery/regression oranlarını kendi paydaları ve ham adetleriyle ver; paydaları farklı oranları karşılaştırarak “recovery > regression, dolayısıyla faydalı” deme. Yeni yanlış adayları ve kritik binding/through hatalarını ayrıca göster. VE vs V farkını da raporla; D ile VE bağımsız kanıt kaynakları değildir.

Development ve frozen-evaluation sonuçlarını ayrı göster. Claim sayısı yanında bağımsız parça grubu sayısını yaz. Küçük örneklemden genel güvenilirlik çıkarma. Verifier olmadığı için wrong-supported, accepted coverage, otomatik CAD güvenliği ve kullanıcı emeği azalması not_evaluated kalsın.

6. RUNNER, BÜTÇE VE KANIT

Mevcut ortak LabRunner root out/lab, ortak heavy lock ve yerel istemci kullanılsın. Yeni job öneki semread-001b-, rapor/state kökü out/lab/semread-001b olsun; yeni runner/scheduler kurma. 001A tarihsel kayıtlarını yeni goal'ün sayacı diye kullanma; iki goal'ün kullanımını raporda ayrı göster.

Model qwen3-vl:8b-instruct, beklenen digest 0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319; 001A ortamı Ollama 0.32.1. Gerçek kurulu ortamı doğrula, farkları kaydet ve eski ortamla eşdeğer sayma. Model değiştirme veya runtime güncelleme yapma.

Bu 001B goal'ü için toplam en fazla 30 yeni gerçek inference yetkilidir: en fazla 10 development/tanı çağrısı ve 10 sayfa×2 kol için 20 final çağrı. Final 20 çağrının bütçesini geliştirme denemelerinde tüketme. Aynı nihai kod/config/input ile alınmış geçerli development sonucu finalde yeniden kullanılabilir. D sıfır VLM çağrısı tüketmeli. Timeout, başarısız istek ve tüm doğrudan tanı/yeniden denemeler sayılır. Cache hit inference değildir. Her isteği gönderim öncesinde ortak kilit altında kalıcı sayaçla rezerve et. Yeni batch, attempt veya CLI ile sayaç sıfırlama; kendiliğinden tekrar payı ekleme veya tavan artırma.

Tek ağır yerel iş; vaka en fazla 600 saniye, batch en fazla 7200 saniye ve varsa daha sıkı mevcut limitler geçerli. Aynı değişmemiş hatayı en fazla 3 kez dene. Timeout sonrası backend'in çalışması bitmeden başka ağır çağrı başlatma; başka oturumun sürecini öldürme.

Her attempt için kaynak/input manifest, final görüntü byte/hash/boyut/sıra/ID, tüm modele görünür mesajlar ve request hash'i, model/digest/runtime/options, raw response/error, parsed adaylar, schema/reference/coverage/truncation sonuçları, süre/token ve artifact index saklansın. D için ham deterministic sonuç ve adapter kaydı da bulunsun. Python RSS'ini toplam model RAM'i diye sunma; ölçülemeyen değer null+gerekçe olsun. Az örnekli latency dağılımını medyan/aralık ve n ile ver; p95 raporlarsan küçük örneklem sınırını yaz.

Kaynak kod/test/config, preprocessing, prompt/schema, model/runtime ve prediction input'ları üretici kimliğine; gold/matching/evaluator değişiklikleri değerlendirme kimliğine bağlansın. Salt gold/evaluator düzeltmesi geçerli eski raw prediction'ın yeniden değerlendirilmesini gerektirebilir, otomatik yeni inference gerektirmez. Yeni untracked dosyaları hash kapsamına kat. Doküman değişimini semantic çalışma değişikliği sanma. Dry-run ve evaluate sıfır inference yapsın.

7. TEST, TESLİM VE TAMAMLANMA

Önce modelleri taklit eden hedefli testleri geçir: schema/reference negatifleri, boş/kesilmiş yanıt, gold izolasyonu, D'nin VLM çağırmaması, V'ye observation sızmaması, VE'ye meaning/gold sızmaması, ters ID–byte eşlemesi, circle≠hole, R≠Ø, unknown≠THRU, count/duplicate feature ayrımı, yanlış target'a doğru değer, duplicate prediction, sıfır payda, timeout'un omission'a etkisi ve bilinen recovery/regression örnekleri. Etkilenen 001A/legacy compatibility testlerini çalıştır; yeni canlı 001A çağrısı yapma. Test beklentilerini modelin yanlış çıktısına uydurma.

Ardından sabit final corpus'ta gerçek D/V/VE pilotunu tamamla. out/lab/semread-001b/final/report.md; makinece okunur per-claim/per-drawing/per-arm sonuçlar; hata örnekleri ve kaynak görsel bölgeleri; acceptance.json; state.json ve yeniden çalıştırma komutları teslim edilsin. En az yanlış binding, yanlış R/Ø, omission ve belirsizlik hataları varsa her türden örneği kaynakla incele; olmayan hata türünü uydurma. Olumlu örnekler kadar olumsuz sonuçları da göster.

B01: 001A snapshot'ı ve ayrı bütçe korunmuş.
B02: Corpus/split/referans ve annotation niteliği açık, hash'ler sabit.
B03: Dar candidate sözleşmesi, D adapter ve ayrılmış V/VE yolları uygulanmış.
B04: Eşleştirme/metrikler ve negatif testler doğru; verifier başarısı iddia edilmiyor.
B05: Aynı final sözleşmeyle sabit corpus'un D/V/VE sonuçları, başarısız vakalar dahil eksiksiz kaydedilmiş.
B06: Kalite farkı, recovery/regression, kritik yanlışlar, maliyet ve kaynaklı hata analizi raporlanmış.
B07: Kanıt zinciri/kimlik/cache/çağrı bütçesi doğrulanmış; sonraki karar ölçümlere dayanıyor.

Bu koşullar sağlandıysa SEMREAD-001B pilot_complete yaz; reference_status ve ölçülen kalite sonucunu ayrıca belirt. V/VE'nin D'den iyi çıkması uygulama completion şartı değildir: sonuç negatifse bunu açıkça raporla. Eksik corpus, eksik gerçek koşu veya bozuk evaluator varsa complete deme; bağımsız işleri bitirip eksik kabul ve gereken tek sonraki adımı bildir. Geçersiz deneyi başarılı ürün sonucu diye sunma. Bu goal sonunda dur; 001C, model karşılaştırması, fusion/verifier, CAD/STEP veya eğitim işini kendiliğinden başlatma.
```
