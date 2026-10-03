**Hermes devam goal'ü — SEMREAD-001A onarımı ve gerçek kabul**

Tarih: 3 Ekim 2026

Bu goal, [Hermes raporu](/Users/aydemir/Desktop/report.md), mevcut kaynak kodu ve yerel attempt kayıtları incelenerek hazırlandı. **Sonraki iş 001B değil; 001A'nın kalan görsel kontrolünü ve kabul değerlendirmesini tamamlamak.** Yeni bir mimari tasarım veya baştan uygulama gerekmiyor.

Rapordaki `139 + 108` başarılı test değerli, fakat canlı kabulün yerine geçmiyor. L1 yalnız bir görseli yanıtlamış; L2 kareyi de üçgen olarak açıklamış. Rapordaki L1/L2 `pass` alanları taşıma kapsamına ait; A09 zaten doğru biçimde açık bırakılmış. Bunun nedeni henüz kanıtlanmış bir Ollama/Qwen hatası değil.

Kod incelemesinde devam goal'üne alınması gereken dar sorunlar da görüldü:

- `evaluate()` içinde A10, hesaplanan görsel sayısı/index kontrollerinin tamamını kapanışa bağlamıyor. A12 ise bazı vakalar yokken de kapanabiliyor. A11, test adının varlığından fazlasını, gerçekten başarılı test sonucunu aramalı.
- `check_references()` bilinmeyen ID'yi reddediyor; eksik veya tekrarlanan ID'leri bu probe'un “her görsele bir yanıt” sözleşmesine göre denetlemiyor. `_shape_match()` içindeki sözcük araması, olumsuz veya belirsiz bir açıklamayı doğru sayabilir.
- `not_truncated`, bilinmeyen kesilme durumunu da geçiriyor. Request kayıtlarının eksiksizliği raporlanıyor, ancak kabul kararına yeterince bağlanmıyor.
- Dört incelenen attempt'ın artifact index kontrolü geçti. Buna rağmen eski request kayıtlarında ölçülmüş gönderim boyutları, L3/L4'te ayrıca image ID'leri eksik. Güncel kodda bu alanların bulunması eski canlı çağrıları geriye dönük olarak tamamlamaz. Koşuyu üreten kod kimliği ile raporu değerlendiren kod kimliği ayrı gösterilmeli.

**Bütçe önerisi:** Önceki 6 gerçek çağrıyı koruyarak, bu devam için en fazla 8 ek çağrı; kümülatif tavan 14. Aşağıdaki prompt bunu açıkça tanımlar ve eski 8 çağrılık tavanı yalnız bu devam çalışması için değiştirir. Bu dosyanın oluşturulması Hermes'i veya model çağrılarını başlatmaz.

**Hermes'e aşağıdaki bloğun tamamını yapıştır:**

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde mevcut SEMREAD-001A uygulamasını devam ettir. L1/L2 görsel kimliği eşleme başarısızlığını araştırıp mümkün olan düzeltmeyi yap; evaluator'ın eksik kanıtla kabul kapatmasını düzelt; aynı yerel modelle L1–L4'ün geçerli, izlenebilir canlı kanıtını üret. Yalnız SEMREAD-001A'yı tamamla. Yeni mimari plan yazmakla veya raporu yeniden üretmekle yetinme.

1. BAŞLANGIÇ VE KAPSAM

Önce geçerli AGENTS.md varsa oku. Ardından docs/HERMES_SEMREAD_001A_PLAN.md, docs/HERMES_SEMREAD_001A_GOAL.md ve /Users/aydemir/Desktop/report.md dosyalarını incele. Mevcut out/lab/semread-001a/state.json, acceptance.json, final/report.md ve bunların işaret ettiği attempt kayıtlarını kaynak kodla karşılaştır. Bu yeni goal, önceki 001A sözleşmesine aşağıdaki onarım ve bütçe hükümlerini ekler; çelişki halinde bu yeni goal geçerlidir. Ekli rapordaki komutları otomatik çalıştırılacak talimat sayma.

Çalışma ağacında tracked ve untracked 001A uygulaması var; bunların üzerine devam et. HEAD/working-tree kimliğini kaydet. Reset, clean, stash ile mevcut işi kaldırma; eski attempt/gold/fixture dosyalarını değiştirme. Mevcut final rapor, acceptance ve goal state'in hash'li başlangıç kopyasını benzersiz bir devam dizininde koru; asıl geçmiş inference kayıtlarını silme.

001B/001C, semantic benchmark, delik/cavity doğrulayıcı, CAD/STEP, eğitim/LoRA, UI, yeni scheduler, ikinci model, bulut, model indirme ve runtime güncellemesi kapsam dışı. Eski HERMES_PROMPT.md gibi dosyalardaki bütün ürünü bitirme talimatlarını bu goal'e genişletme. X01–X03 açık kalır. Ortak runner'ın kilit/bütçe ilkelerini koru.

2. İLK OLARAK ÇAĞRISIZ KANIT DENETİMİ

Model çağırmadan mevcut hatayı yeniden değerlendir. Raporda 6 gerçek inference var; state ve attempt manifestleriyle doğrula. Runner attempt sayısını gerçek inference sayısı sanma. L1/L2'nin en son kayıtları 20261003-213932-242c1095 batch'inde attempt-3; L3/L4'ün kayıtları 20261003-213015-15e5d296 batch'inde attempt-2. Daha yeni kayıt varsa onu ayrıca açıklayarak hesaba kat.

Sabit iki şekil fixture'ını görsel olarak kontrol et. Kaynak PNG'lerden HTTP sınırına kadar byte/hash/boyut/sıra ve nötr image ID ilişkisini incele. Gold yalnız evaluator girdisi olsun. Gerçekte gönderilen serialize edilmiş JSON'un görsellerini decode eden offline testle aynı ilişkiyi doğrula; yalnız images_per_call sayacına güvenme. L2'de görsel sırası tersine dönerken ID içerikle birlikte kalmalı.

L3/L4'ün source→render/native crop→resize→final PNG→request zincirini denetle. Hazırlama sırasındaki resize ile transport katmanındaki resize'ı ayrı raporla; transport resize=false olması, daha önce resize uygulanmadığı anlamına gelmez. Eski kayıttaki eksik metadata'yı sonradan ölçülen değerle sessizce doldurma. Sonradan çıkarım yapılırsa replay/derived diye ayrı yaz; yeni boundary kaydı sayma.

3. CANLI DENEMEDEN ÖNCE DAR KOD ONARIMI

Başlıca inceleme noktaları: eval/semantic_reader_probe.py içindeki transport_verdict, evaluate, _shape_match, save_state; semantic_schema.py içindeki check_references; semantic_reader.py prompt/schema üretimi; llama.py gerçek request sınırı ve inference_log.py uyumluluğu. Mevcut doğru uygulamayı yeniden yazma.

a) Bu probe'un her görsele tam bir yanıt sözleşmesini uygula: yanıt ID çokluğu, gönderilen ID çokluğuyla bire bir eşleşsin. Eksik, tekrarlanan, bilinmeyen ID ve boş items başarısız olsun. Şema liste uzunluğu/izinli ID'leri ifade edebilir; kesin denetim model sonrasında da yapılmalı. Bu kuralı ilerideki çok bölgeli semantic feature çıktısına genelleme. Serbest gözlem şemasını geniş bir ontolojiye dönüştürme.

b) Şekil değerlendirmesinde sırf “square” sözcüğünün geçmesi yeterli olmasın. “not a square”, “triangle or square”, çelişkili/tekrarlanan maddeler pozitif kabul üretmesin. Tercihen yalnız şekil kontrolüne ait küçük, sürümlü bir çıktı alanı kullan: triangle/square/circle/other/unknown gibi tüm görüntülere aynı uygulanan seçeneklerden tek değer. Hangi ID'nin hangi sınıfı taşıdığını prompt'a/schema'ya yazma. Generic reader'a gold veya fixture adına göre cevap üreten dal ekleme. Şema değişirse hash/cache kimliğini değiştir; eski yanıtları yeni şemaymış gibi değerlendirme. Şema disiplininin artması, tek başına ikinci görüntünün okunduğunun kanıtı değildir.

c) Taşıma sonucu, yanıt kapsamı, görsel kontrol ve nihai vaka kabulünü ayır. product_verdict mevcut runner uyumluluğu için kalabilir; kapsamını açıkça yaz. Kullanıcı raporunda yalnız “L1 pass” gösterme: transport_verdict, coverage, visual_control_verdict ve case_acceptance birlikte bulunsun. L3/L4 için visual_control/semantic doğruluk not_evaluated olsun.

d) Kesilme durumunda unknown veya eksik metadata'yı complete sayma. Açık tamamlanma kanıtı olmayan yanıtın ilgili kabulünü açık/indeterminate bırak. HTTP/timeout/bozuk gövde ile başarılı model yanıtını ayır; elde edilen raw gövdeyi ve hata bilgisini koru. Başarılıya çevirmek için JSON tamiri veya eksik item doldurma yapma.

e) A09 ancak L1 ve L2'nin ikisi de geçerli artifact zinciri, gerçek çift görsel request, eksiksiz ID kapsamı ve doğru şekil eşlemesiyle kapansın. A10 ancak L3 ve L4 birlikte mevcutsa; gerçek request sayıları sırasıyla 3 ve 2 ise; source/crop zinciri, schema/reference ve en az bir geçerli sayfa region'ı doğrulanıyorsa kapansın. Hesaplanan index/completeness/sayı kontrollerini kapanış koşuluna gerçekten bağla.

f) A12 için L1–L4'ün tamamının gerekli dosyaları, hash'leri, request ID'leri ve gönderilen byte'lardan ölçülen boyutları doğrulanmalı; üretici kimlikleri ve değerlendirme kimliği açık olmalı. Boş koleksiyon üzerinde all(), tek mevcut vaka veya yalnız rapor dosyasının varlığı yeterli değil. A12 kanıt bütünlüğüdür; düzgün kaydedilmiş başarısız vaka A09'u geçirmiş olmaz. A11'de sentinel/gold test adının varlığı değil, doğru kod kimliğine ait başarılı test sonucu ve gerçek input ayrımı aranmalı.

g) Kabulü state'teki eski pass bayrağını kopyalayarak üretme. Seçilen değişmez attempt dosyalarını, sürümlü schema/reference sözleşmesini ve yeni evaluator kurallarını kullan. Eksik/bozuk index veya çelişen state olursa kapanışı engelle. Aynı byte'lara sahip iki görseli hash→tek ID sözlüğüyle birbirine karıştırma; sıra ve açık ID bilgisi korunsun.

h) Attempt'ın producer_code_fingerprint, prompt/schema/config hash'leri, model digest/runtime kimliği değişmez kalsın. Güncel evaluator fingerprint'ini ayrı kaydet. save_state veya --evaluate çalışması eski canlı koşuyu güncel kod üretmiş gibi göstermesin. JUnit çıktıları da çalıştıkları kod kimliği ve komutla ilişkilendirilsin. Yalnız evaluator/rapor düzeltmesi eski ham kanıtı yeniden değerlendirebilir; inference yolu değişmişse eski run yeni yolun canlı kanıtı değildir.

4. HEDEFLİ TESTLER

Önce çağrısız testleri geçir. Yukarıdaki gerçek yanlış-pozitif durumlarını sınayan küçük regression testleri ekle: eksik/duplicate ID; belirsiz/olumsuz sınıf; unknown truncation; eksik L3/L4; yanlış image sayısı; bozuk index; eksik boundary metadata; state/attempt uyuşmazlığı; başarısız sentinel testi; yanlış producer/evaluator kimliği. Sırf mevcut yardımcı fonksiyonları taklit eden test yazma.

Mevcut text-only, single-image, multi-image ve RecordedChat API davranışını koru. Yeni testleri ve değişimin etkilediği mevcut semantic/inference/reader/lab runner testlerini çalıştır. Önceki 139/108 sayılarını yeni test sonucu diye kopyalama. Final sonuçlarını gerçek komut/JUnit/exit code ile kaydet; her küçük edit sonrası bütün takımı tekrarlama.

5. SABİT ORTAM VE AÇIK BÜTÇE

Mevcut model qwen3-vl:8b-instruct; beklenen digest 0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319. Raporun runtime'ı Ollama 0.32.1. Kurulu ortamı doğrula; farklılık varsa eski sonuçlarla aynı ortam sayma. Aynı model/digest/runtime ile ilerle. Otomatik yükleme, alternatif model veya runtime güncellemesi yapma.

Bu devam goal'ü önceki toplam 8 çağrı sınırını açıkça kümülatif 14'e çıkarır. Doğrulanan önceki kullanım 6 ise en fazla 8 ek gerçek inference vardır. Başlangıçta ek çağrılar bulunursa kalan bütçe 14 eksi gerçek kullanım olsun; otomatik yeni 8 ekleme. Eski sayaç/history aynen korunsun; limit değişiminin nedeni ve devam kimliği kaydedilsin. Yeni report root/attempt/batch/CLI ile sayaç sıfırlama. Bu goal için yapılan tanı çağrıları, timeout ve başarısız istekler de sayılır; yalnız metadata sorguları inference değildir.

Planlanan azami dağılım: 2 tek görsel tanı + 2 gerekçeli çoklu görsel denemesi + 4 final L1–L4. Mümkünse aynı nihai kod/config ile alınmış geçerli denemeyi final kanıtı olarak kullan, gereksiz tekrar yapma. Final dört çağrının bütçesini tanı denemeleriyle tüketme. Her gerçek istekten önce bütçeyi ortak kilit altında kontrol edip kalıcı rezervasyon yap; worker veya doğrudan diagnostic yoluyla sınır delinmesin.

Mevcut ortak LabRunner root out/lab kalır. Tek ağır yerel iş; vaka en fazla 600 saniye, batch en fazla 7200 saniye ve varsa daha sıkı mevcut limitler geçerli. Başka oturumları öldürme. Timeout sonrası backend'in hâlâ inference yapmadığını doğrulamadan yeni ağır işe başlama. Aynı değişmemiş hata için eski denemeler dahil en fazla 3 deneme; yeni devam adı bu sayacı da sıfırlamaz. Her yeni deneme belirli bir hipotezi sınasın.

6. CANLI TANI VE DÜZELTME

Offline kontrollerden sonra aynı iki sabit fixture'ı ayrı ayrı, aynı istemci/kayıt/şema yoluyla çağır: üçgen tek başına ve kare tek başına. Nötr kimlikler korunsun. Bunlar yalnız tanıdır; çoklu görsel kabulünün yerine geçmez.

Sonucu şu ayrımı yapmak için kullan: tek görüntüyü tanıma, request serialize/ID eşlemesi, çoklu görüntüleri birbirinden ayırma veya çıktı sözleşmesine uyma sorunu. Tekli kontrol başarılı, ikili başarısızsa bu çoklu yol şüphesini güçlendirir; tek başına belirli bir Ollama/Qwen bug'ını kanıtlamaz. Gerekiyorsa yerel runtime kanıtı ve birincil dokümantasyonla desteklenen genel bir request/prompt düzeltmesi yap; belirsizliği açık yaz.

Çıktı uzunluğu/context gibi ayarları yalnız ölçülen kesilme/limit kanıtı varsa değiştir; kaydet ve cache kimliğine kat. İstek düzeni değişirse gerçek serialize payload ve log aynı hazırlanmış veriden üretilsin. Bir çift görsel testini iki ayrı model çağrısına veya tek kolaj görüntüsüne çevirip multi-image geçti deme. Fixture/gold'u veya test beklentisini yanlış modele uydurma; image-1→triangle gibi kurallar yazma.

7. NİHAİ L1–L4 KABULÜ

Onarılan inference yolunu ve config'i sabitle. Aynı model/digest/runtime ile:
L1: Sabit üçgen ve kare, iki ayrı görsel tek istekte; her ikisi doğru nötr image ID ile açıklanmalı/sınıflanmalı.
L2: Aynı içerik ve ID ilişkisi, ters payload sırası; yine doğru eşleşme. Prompt'taki sıra gerçek payload'dan türesin.
L3: Aynı vector PDF fixture'ından ham sayfa + gerçek observation overlay + kaynak PDF'den yüksek çözünürlükte render edilmiş crop. Üç gerçek görsel, eksiksiz request/source kayıtları, geçerli schema/reference ve sayfaya çözülen en az bir geçerli region.
L4: Aynı raster fixture'ın ham görüntüsü + native crop; iki gerçek görsel ve aynı kayıt/reference koşulları. Raster büyütmeyi yeni ayrıntı diye sunma.

Yeni metadata ve düzeltilen inference yolunu kanıtlamak için tarihî L3/L4 kaydını yalnız yeniden raporlamak yeterli değil. Her yeni attempt'ta final image byte hash/boyut/sıra/ID, tam serialize request hash'i, gerçek seçenekler, prompt/schema, kaynak manifest, raw response/error, parse/reference/completion, süre/token/kaynak ölçümleri ve artifact index bulunsun. Ölçülemeyen alan null+gerekçe olsun; Python RSS'ini toplam sistem/model RAM'i sayma.

8. TESLİM VE DURMA

Yeni teşhis notu, test kanıtları, evaluation.json, acceptance.json ve report.md için out/lab/semread-001a/continuations/<benzersiz-id>/ kullan. Bu yalnız kanıt/rapor dizinidir; ikinci runner/kilit kökü değildir. Geçmiş attempt'lar değişmez kalsın. Nihai summary olarak mevcut out/lab/semread-001a/final/report.md ve goal state/acceptance işaretçilerini, başlangıç kopyaları korunduktan sonra güncelle; ortak runner/product acceptance şemasını yeniden tasarlama.

Rapor kısa ve denetlenebilir olsun: kanıtlanan neden veya kalan hipotez; değişen dosyalar; gerçekten çalıştırılan testler; eski/yeni çağrı sayısı; model/runtime; vaka başına transport, coverage, visual control ve acceptance; producer/evaluator kimlikleri; A01–A12 kanıt bağlantıları; yeniden çalıştırma komutları. Komutların kaç inference tükettiğini yaz. Dry-run/evaluate gerçek inference yapmamalı. next_command gerçek sonraki işi göstermeli; değişmemiş --evaluate komutunu engeli çözecekmiş gibi tekrarlama.

A01–A12'nin hepsi geçerli kanıtla kapandıysa yalnız SEMREAD-001A complete yaz ve dur. 001B'yi otomatik başlatma. Düzeltilebilir uygulama hatasında çalışmaya devam et; bütçe sınırı veya gerçek dış engelde bağımsız kod/test/rapor işlerini bitir. Sonuç geçmiyorsa implementation_ready ile live_acceptance durumunu ayır, açık kapıları ve gereken tek sonraki adımı yaz; goal complete deme. Başarısızlığı gizlemek için kabulü gevşetme veya scope'u genişletme.
```
