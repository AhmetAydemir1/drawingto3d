**Hermes uygulama planı — SEMREAD-001A**

Tarih: 3 Ekim 2026 · Plan hazırlanırken incelenen HEAD: `4fb09b6`

Çalışma dizini: `/Users/aydemir/Desktop/drawingto3d`

Bu belge yalnız **görsel taşıma, kaynak izlenebilirliği ve yapılandırılmış yanıt yolunun uygulanması** içindir. Yeni bir mimari araştırma başlatmaz. Eşlik eden [Hermes goal promptu](/Users/aydemir/Desktop/drawingto3d/docs/HERMES_SEMREAD_001A_GOAL.md) bu planı uygulatır; dosyaların hazırlanması Hermes'in başlatıldığı anlamına gelmez.

**1. Teslimin sınırı ve tamamlanma tanımı**

Kurulacak ve kanıtlanacak yol:

```text
PDF / PNG / JPG
  → kaynak hash'i + seçili sayfa
  → ham sayfa + ayrı observation overlay + crop
  → mevcut OllamaChat ile gerçek çoklu görsel isteği
  → ham yanıt + schema/reference doğrulaması
  → mevcut lab runner altında tekrar üretilebilir kanıt paketi
```

001A tamamlandığında “yerel modele doğru görselleri, doğru kimliklerle gönderebiliyoruz ve yanıtı kaynağa geri bağlayabiliyoruz” denebilir. Delik/cavity okuma doğruluğu, feature recall, yanlış semantic kabul, model seçimi veya doğru STEP başarısı iddia edilemez.

**Kapsam dışı:** 001B/001C benchmark'ı, 4B–8B kıyaslaması, semantic verifier/fusion, genel FeaturePlan, CAD/STEP üretimi, proposal genişletme, kullanıcı arayüzü, eğitim, yeni scheduler, cloud servis, model router. Model yanıtından `supported` veya `source=user` üretmek yok.

**2. Önceki goal ve Phase 0 ile ilişki**

Bu görev için güncel kapsam yalnız 001A'dır. Eski [HERMES_PROMPT.md](/Users/aydemir/Desktop/drawingto3d/HERMES_PROMPT.md) içindeki “bütün ürünü tamamlayana kadar devam et” hedefi bu dar goal'un tamamlanma koşulu değildir. Eski dosyaları, ürün goal state'ini veya kapanmamış ürün kabullerini tamamlandı diye değiştirme.

X01–X03 ve P01–P08 ürün kabul işleri açık kalır. 001A, eski `reason_drawing`, `offline_flow` veya STEP evaluator yolunu çalıştırmayacağı için bunların tamamını bu göreve çekme. Semantic/ürün başarısı raporlamadan önce Phase 0 gereksinimi sonraki aşamalarda korunur.

X04'ün bu işe uygulanan kuralları şimdi zorunludur: ortak ağır iş kilidi, vaka/koşu bütçesi, benzersiz attempt dizini, gerçek exit/timeout kaydı, eski artifact'ın yeni başarı sayılmaması. Bunları mevcut runner üzerinden sağla; eski bütün harness'leri bu goal içinde yeniden düzenleme.

Aktif bir başka Hermes goal veya ağır deney varsa ikinci paralel işi başlatma. Kullanıcının bu promptla verdiği dar kapsamı mevcut oturumun desteklediği goal değiştirme/devam mekanizmasıyla uygula; başka bir oturumun sürecini öldürme. Kullanılan Hermes sürümünde olmayan yönetim komutlarını uydurma.

**3. Başlangıç kontrolü ve okunacak kod**

Önce geçerli `AGENTS.md` kurallarını, çalışma ağacını ve gerçek HEAD'i kontrol et. HEAD değişmişse aynı commit'e resetleme; güncel kodda aşağıdaki varsayımları tekrar doğrula. Kullanıcının tracked/untracked dosyalarını koru.

Başlıca giriş noktaları:

- [llama.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/llama.py): `_ollama_chat`, `OllamaChat`, `ChatSettings`, model metadata ve localhost kontrolü.
- [inference_log.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/inference_log.py): özellikle `RecordedChat.complete`; mevcut imza tek görsele göre.
- [ingest.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/ingest.py) ve [observe.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d/observe.py): render, observation ID'leri ve koordinatlar.
- [runner.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d_lab/runner.py) ve [state.py](/Users/aydemir/Desktop/drawingto3d/src/drawingto3d_lab/state.py): `Job`, `{run_dir}`/`{result}` yer tutucuları, cache kimliği, ortak kilit.
- [İkinci review](/Users/aydemir/Desktop/drawingto3d/docs/SEMANTIC_READER_REVISED_REVIEW_20261003.md): yalnız 001A'ya ait kararlar; benchmark tartışmasını bu teslimde uygulama.

Başlangıç kanıtına HEAD, dirty-file listesi, Python/Ollama sürümü, cihaz/bellek bilgisi, yerel model envanteri ve mevcut runner limitlerini yaz. Sırları veya ortam değişkenlerinin bütününü dökme. Python için mevcut `.venv` kullan; yeni CAD ortamı kurma.

**4. Dosya bazında iş dağılımı**

| Dosya | Bu teslimde sorumluluk |
|---|---|
| `src/drawingto3d/llama.py` | Geriye uyumlu çoklu görsel çağrısı, gerçek ayarlar ve request trace. |
| `src/drawingto3d/inference_log.py` | Gerekli imza uyumu; çoklu görüntünün yanlışlıkla “image_attached=false” kaydedilmesini önleme. |
| `src/drawingto3d/semantic_schema.py` — yeni | Küçük input manifest, referans ve probe yanıt tipleri. Genel ontology yok. |
| `src/drawingto3d/semantic_images.py` — yeni | Ham görüntü/overlay/crop hazırlama, byte hash'i, dönüşüm ve referans çözümleme. |
| `src/drawingto3d/semantic_reader.py` — yeni | Verilen image bundle'ı yerel modele gönderme ve yapısal/reference kontrolü. Semantic doğrulama yok. |
| `eval/semantic_reader_probe.py` — yeni | Küçük kontrollü fixture'lar, config, mevcut runner'a job verme ve rapor. |
| Hedefli test dosyaları | Aşağıdaki davranışları sınayan testler; mevcut regression'ları koruma. |

Dosya adları sorumluluğu anlatır; küçük yardımcıları birleştirmek mümkündür. İşlev eklenmeyen boş modüller oluşturma. `proposal.py`, `general.py`, `guided.py`, eğitim kodu veya global runner şemasını gereksiz yere değiştirme. Ortak taşıma değişikliğinin zorunlu uyarlamaları kapsam içindedir.

**5. Kesin veri ve koordinat kararları**

İlk kaynak kapsamı: PDF'nin sıfırıncı, dönmemiş sayfası; PNG/JPG'nin gerçekten decode edilen görüntüsü. Desteklenmeyen sayfa/rotasyon açıkça reddedilir; istenen sayfa yerine sessizce ilk sayfa kullanılmaz. Genel çok sayfalı PDF, deskew ve perspektif dönüşümü ekleme.

Kanonik sayfa çerçevesi: normalize `[0,1]`, sol üst `(0,0)`, x sağa ve y aşağı. Model bbox'ı **referans verdiği input image'ın** aynı normalize çerçevesindedir. mm/CAD koordinatı değildir.

Her hazırlanmış görselde en az:

```text
image_id, kind=full_page|overlay|crop
source_sha256, page_index=0, source_type
prepared_image_sha256, width_px, height_px
render_mode=pdf_rerender|native_raster
render_dpi (native raster için null)
source_bbox_page_norm
T_image_norm_to_page_norm
observation_snapshot_id (varsa)
preprocessing_version, resize_policy
```

Bu alanları uygulama üretir. Boyut ve hash, **gönderilecek son PNG byte'larından** hesaplanır; çağıranın verdiği metadata ile çelişki varsa hata verilir. Resize yapılırsa kayda girer. Input image ID'leri call içinde benzersizdir; kaynak hash'i veya dosya adı modele ezberlenecek kimlik olarak verilmez.

Bir crop'un kaynak sayfadaki normalize kutusu `[x0,y0,x1,y1]` ise, ilk kapsamda dönüşüm:

```text
x_page = x0 + u_image * (x1 - x0)
y_page = y0 + v_image * (y1 - y0)
```

Full-page/overlay için bu eşleme identity'dir. Crop köşeleri ve merkezi bağımsız beklenen koordinatlarla test edilir; farklı gönderim çözünürlüklerinde aynı kaynak bölgesi korunur.

Ham sayfa 200 DPI PDF render'ı kullanabilir. Seçili PDF bölgesi kaynaktan 600 DPI'da yeniden render edilebilmelidir; belleği gereksiz büyüten bütün paftayı 600 DPI hazırlama zorunluluğu yoktur. Raster crop native pikselden alınır; büyütme yeni ayrıntı diye sunulmaz. Raster PDF içindeki düşük çözünürlüklü resim de vektör ayrıntısı kazanmış sayılmaz.

Overlay ayrı dosyadır ve ham görüntüyü değiştirmez. Mevcut gözlemlerin gerçek ID'lerini/bbox'larını adresler; “bu deliktir/çaptır” gibi semantic karar basmaz. ID yeniden adlandırılırsa snapshot'a açık eşleme bulunur. Overlay, mevcut `meaning` sonuçlarının doğruluk beyanını taşımaz.

Probe yanıtı için küçük bir sözleşme yeterli:

```json
{
  "schema_version": "semread-probe/1",
  "items": [
    {
      "image_id": "image-2",
      "description": "Kısa görsel gözlem",
      "region": {"x0": 0.2, "y0": 0.3, "x1": 0.6, "y1": 0.7}
    }
  ]
}
```

Metin açıklaması semantic olarak kabul edilmiş bilgi değildir. `region` bilinmiyorsa ayrı null/abstention yolu olabilir. Referans kontrolü yalnız bu çağrıda gönderilen image ID'lerine izin verir. Bbox sonlu, `[0,1]` içinde ve pozitif alanlı olmalıdır; hatalı bbox'ı clamp ederek geçerli yapma. Kaynak/snapshot bilgisi modelin yazdığı alanlardan alınmaz. `supported` ve `source=user` model schema'sında bulunmaz.

**6. Ollama taşıma sözleşmesi**

Eski çağrıların pozisyonel parametreleri ve `str` dönüşü korunmalı. Yeni seçenekler keyword-only eklenebilir. Örneğin aşağıdaki imza bir API taslağıdır; mevcut fonksiyonun bütün parametreleri uygulamada korunur:

```python
def complete(
    self, prompt, image_png=None, num_predict=None,
    response_format=None, stats=None, *, images=None, trace=None,
):
    ...
```

- `images=None` eski single-image/text-only davranışını korur.
- `images=[]` açıkça text-only istek olabilir; `images_per_call=0` olarak gerçek kayda geçer.
- `image_png` ve `images` birlikte verilirse `ValueError`; sessiz seçim/birleştirme yapılmaz.
- Görsel listesi ile prompt'taki image ID/sıra eşlemesi aynı hazırlanmış bundle'dan üretilir.
- `keep_alive`, `num_ctx`, `num_predict`, temperature ve varsa uygulama resize sınırı gerçekten uygulanır.
- `images_per_call` gönderilen listeden ölçülür; `ChatSettings` beyanı gerçek sayı yerine kullanılmaz. Uyumluluk için eski ayar kaydı korunabilir, actual-request kaydı ayrı ve otoritatif olur.
- localhost kısıtı korunur; buluta otomatik fallback ve gizli model değiştirme yoktur.

HTTP payload ve manifest, tek ortak hazırlama noktasından üretilmeli. Testte gerçek payload'ın base64 image alanları decode edilerek kaydedilen son byte/hash/boyut/sırayla karşılaştırılmalı. Sadece `images_per_call=3` alanını assert etmek yeterli değildir.

Actual-request kaydı: prompt/schema içeriği veya hash ve dosya referansı; model tam adı/digest'i; backend sürümü; gerçek seçenekler; gönderilen image listesi; tam serialize edilmiş isteğin hash'i; call ID ve attempt bağlantısı. Base64'ü konsola basma; yeniden oynatma için görsel dosyalarını ve prompt/schema'yı kanıt paketinde sakla.

Raw response hata veya boş content durumunda da korunmalı. HTTP hatası, empty content, JSON parse hatası, schema hatası, reference hatası, token kesilmesi ve timeout ayrı sonuçlardır. Otomatik JSON “tamiri” ile ilk hatayı gizleme. `done_reason` gelmediyse kesilme durumu `unknown` olur. Backend'in iç görüntü çözünürlüğü bilinmiyorsa ölçülmüş gibi yazılmaz.

`RecordedChat` yeni keyword'leri taşımalı ve çağrı/görsel kaydını doğru tutmalı. Legacy text-only/single-image çağrılarının davranışı, kayıt şemalarının zorunlu alanları ve başarısız çağrı kapanışları korunmalı.

**7. Runner, bütçe ve kayıt düzeni**

`LabRunner` için mevcut ortak `out/lab` kökünü kullan. `out/lab/semread-001a` altında ikinci bir bağımsız runner/kilit kurma; aksi hâlde iki ağır iş paralel başlayabilir. Yeni job ID'leri `semread-001a-` önekli olsun. Goal'a özel rapor/state dosyaları ayrı alt dizinde tutulabilir.

Mevcut limitlerden daha sıkı olanı uygula: tek ağır iş, vaka toplam en fazla 600 saniye, bir runner batch'i en fazla 7200 saniye. Bu goal için ek dar kontrol bütçesi **en fazla 8 gerçek inference çağrısıdır**; final minimumu aşağıdaki dört çağrıdır, kalanlar gerekçeli onarım içindir. Sayacı batch/attempt değiştirerek sıfırlama. Aynı değişmemiş hata için en fazla üç deneme; bütçeyi veya limiti sessizce artırma.

Tek kurulu vision modeli kullan. Başlangıçta kurulu uygun Qwen3-VL Instruct 4B/8B adaylarından birini tam etiketiyle seç ve config'e sabitle; seçim benchmark sonucu değildir. Bunlar yoksa başka kurulu yerel vision modelini bağlantı kanıtı için gerekçesiyle seçebilirsin. Açık kullanıcı model seçimi varsa onu koru. Uygun kurulu model yoksa bağımsız kod/mock testlerini tamamla; live kabulü açık bırak ve eksik önkoşulu bildir. Bu goal model indirme, runtime güncelleme veya ücretli kaynak oluşturma yetkisi vermez.

Çağrı öncesi model tag/digest ve runtime sürümünü kaydet; run içinde değişiklik olursa eski/yeni kanıtı karıştırma. Yeni kod dahil gerçekten kullanılan dosyalar, kaynak dosya, prompt/schema, resize/crop config ve model/runtime kimliği cache anahtarına girsin.

Somut entegrasyon: semantic run config'ini dosyaya yazıp `Job.inputs` içine ekle; `Job.command` argüman listesinden geçir. Mevcut `_key()` yalnız limitleri `settings` olarak kullandığından, modele ait rastgele yeni settings alanlarının zaten hash'lendiğini varsayma. `code_fingerprint` tracked çalışma ağacı dosyalarını kapsar; yeni untracked kod için açık watched/input kaydı ekle. Eksik required input için hash hesabından önce hata ver.

Runner attempt dizininde şu çıktılar bulunmalı:

```text
input-manifest.json
images/*.png
prompt.txt, response-schema.json
request-manifest.json
response-raw.json veya response-error.json
response-parsed.json (varsa)
reference-checks.json
resources.json
result.json
```

Runner'ın `manifest.json`, stdout/stderr ve `complete.json` dosyalarını kendi normal yolu üretir. Ek kanıt dosyalarının hash/varlık kontrolü için probe'a ait artifact index kullan; mevcut marker'ın varsayılan olarak yalnız result dosyasını hash'lemesini bütün bundle denetlenmiş gibi sunma. Final kabul ve cached sonuç tekrar kullanımı kanıt bundle'ını ayrıca doğrulasın. Kapsam için küçük entegrasyon yeterli; genel yeni artifact framework'ü yazma.

`result.json` içinde mevcut runner'ın `product_verdict` alanını koru; ayrıca `evaluation_scope="semread-001a-transport"`, semantic/CAD değerlendirmesi için `not_evaluated` bilgisi yaz. Bu job'un `pass` olması ürünün doğru STEP ürettiği anlamına gelmez.

Süre ve token sayıları gerçek kaynaktan; bellek için yöntem/process kapsamı açık yazılmalı. Ölçülemeyen backend/peak alanları `null + reason`; yalnız Python RSS'ini toplam model RAM'i diye adlandırma. Ayrı bir bellek profiler projesi açma.

Timeout sonrası HTTP istemcisinin bitmesi Ollama inference'ının durduğunu kanıtlamaz. Yeni ağır işi başlatmadan backend'in kullanılabilir/boş olduğunu denetle. Başkasının modelini veya genel Ollama servisini zorla kapatma. Kontrol edilemeyen devam eden iş varsa live işi engelli kaydet; bağımsız testleri sürdür.

**8. Uygulama sırası**

| İş | Yapılacak | Çıkış kanıtı |
|---|---|---|
| A0 | Güncel kaynak, ortam, ortak kilit ve limit kontrolü | bootstrap kaydı; kapsam ve mevcut durum net. |
| A1 | Küçük manifest/reference schema ve görüntü hazırlama | Crop dönüşümleri, final-byte hash'leri ve negatif referans testleri. |
| A2 | Ortak Ollama yolu ve log wrapper'ı genişletme | Gerçek serialize edilen payload üzerinde test; legacy çağrılar geçiyor. |
| A3 | Probe CLI ve mevcut runner'a bağlama | Dry-run model çağırmıyor; cache girdi değişimlerini görüyor. |
| A4 | Deterministic/mock hata ve compatibility testleri | Hedefli test çıktısı; bozuk/eksik yanıt başarı sayılmıyor. |
| A5 | Tek yerel modelle aşağıdaki dört canlı çağrı | Kaynak ve artifact zinciri tamam; pozitif kontrol doğru. |
| A6 | Fresh/cached kayıt doğrulaması ve final rapor | Aşağıdaki acceptance tablosu kanıt linkleriyle kapanmış. |

Yalnız plan/probe dosyası yazıp teslimi bitirme. Yetkili ve mümkün adımları uygulama, test ve gerçek yerel çağrı kanıtına kadar sürdür. Kod/hata düzeltmesi gerektiren başarısızlıkları kayıtla düzelt. Harici bağımlılık engelinde yapabildiğin yerel işleri bitir; live kabul olmadan goal complete yazma.

**9. Küçük ve sabit canlı kabul seti**

Fixture'lar bu görevde geliştirme kontrolüdür; holdout veya semantic başarı veri seti diye sunulmaz. Tamamı çağrıdan önce tanımlanır. Görsel hazırlamak için mevcut Python/OpenCV/PDF yardımcılarını kullan; ImageGen, eğitim verisi üretim sistemi veya yeni dataset servisi gerekmez.

| Çağrı | Girdi | Beklenen |
|---|---|---|
| L1 | Birinde büyük üçgen, diğerinde büyük kare bulunan iki görüntü | Model, nötr image ID'leriyle doğru şekilleri eşler. |
| L2 | L1'in aynı görselleri ve aynı ID ilişkisi, payload sırası ters | Prompt'taki sıra eşlemesi otomatik güncellenir; şekil kimliği doğru görselle kalır. |
| L3 | Mevcut bir vector PDF çizimin ham sayfası + observation overlay + kaynaktan yüksek çözünürlüklü crop | Gerçek üç görsel gönderimi, schema-valid yanıt, en az bir geçerli region referansı ve kaynak dönüşümü kaydı. Mühendislik yorumu puanlanmaz. |
| L4 | PNG/JPG kaynak ham görüntü + native crop | Raster kaynak farkı ve doğru crop/source ilişkisi; schema/reference kontrolü. |

L1/L2 prompt'u hangi image'ın hangi şekli içerdiğini söylemez; nötr dosya adları kullanılır. Beklenen cevaplar yalnız probe evaluator'ında kalır. Görsel içerik değişmeden metin/ID'den cevabı çıkarmayı sağlayan etiketler ekleme. Bu kontrol teknik çizim semantiğini sınamaz.

L3 için örneğin mevcut `Plate With A Pocket Drawing.PDF` kullanılabilir; yalnız çizim dosyasını açıkça seç. Yanındaki STEP'i, generator parametrelerini veya etiketleri reader'a verme; klasördeki bütün dosyaları context'e toplama. Crop sabit development bbox'ı olabilir ve kaydı tutulur; ürün koduna örneğe özel tanıma kuralı girmez.

L3/L4'te yanıtın null/boş/bozuk olması saklanır; gerçek schema/reference pozitif kanıtı olmadan live gate geçmez. Tek başına mantıklı görünen açıklama da yeterli değildir. L1/L2'nin başarısızlığı doğrudan transport bug'ı diye etiketlenmez; girdi, runtime ve model davranışı ayrıştırılır.

**10. Hedefli testler ve acceptance**

| ID | Kabul koşulu | Kanıt türü |
|---|---|---|
| A01 | Text-only/single-image eski API ve `RecordedChat` davranışı korunuyor | Mevcut ve hedefli regression testleri. |
| A02 | Çoklu payload byte/hash/boyut/sıra doğru; çakışan API girdisi reddediliyor | HTTP-boundary fake/spied payload testi. |
| A03 | Ayar kaydı gerçekten uygulanan seçeneklerle aynı | Non-default keep_alive/context/output ve resize testi. |
| A04 | PDF crop yeniden render; raster crop native; kaynak eşlemesi doğru | En az iki çözünürlük, crop köşe/merkez ve ham dosya hash'i testi. |
| A05 | Yanlış image ID, eski snapshot, ters/out-of-range/NaN bbox kabul edilmiyor | Negatif schema/reference testleri. |
| A06 | HTTP/empty/parse/schema/reference/truncation/timeout ayrı ve raw kanıt korunmuş | Kontrollü hata testleri; model cevabı tamir edilmeden kayıt. |
| A07 | Ortak runner root/kilit/bütçe kullanılıyor; dry-run inference yapmıyor | Runner entegrasyon testi ve manifest. |
| A08 | Crop/prompt/schema/model digest/untracked kod değişimi cache'i değiştiriyor | Kimlik testi; aynı girdi gereksiz inference tekrarlamıyor. |
| A09 | L1/L2 görsel pozitif kontrolü gerçek yerel modelle geçti | Raw istek/yanıt ve evaluator sonucu. |
| A10 | L3/L4 gerçek drawing path'i schema/reference kapılarından geçti | PDF/raster bundle'ları ve gerçek request manifest. |
| A11 | Reference STEP/gold labels prediction girdisine girmiyor | Açık reader input sözleşmesi; payload incelemesi ve sentinel testi. |
| A12 | Final artifact zinciri geçerli; scope doğru; yeniden çalıştırma tarifi var | Hash kontrolü, test/live kayıtları, final report ve acceptance. |

Sentinel testi, özel bir gold/reference alanının reader girdisine/prompt'a geçirilmesini engellediğini sınamalı; gold yalnız evaluator tarafında kalır. Bu dar test genel bir güvenlik sertifikası sayılmaz.

Mevcut ilgili testleri önce keşfet. Beklenen odak seti `test_model_choice.py`, `test_reader.py`, `test_inference_log.py`, `test_planner.py`, `test_chain_model.py`, `test_baseline_fields.py`, `test_lab_runner.py` ve yeni testlerdir. Her edit sonrası bütün takımı çalıştırma; ilgili testlerle ilerle, finalde bu değişimin etkilediği seti birlikte çalıştır. Test beklentilerini bozulan davranışa uydurma.

**11. Kalıcı ilerleme ve son rapor**

Goal'a özel kayıtlar:

```text
out/lab/semread-001a/state.json
out/lab/semread-001a/acceptance.json
out/lab/semread-001a/final/report.md
```

Bu dizin **rapor köküdür**, ikinci LabRunner kökü değildir. Kayıtta açık/kapanan A01–A12, son kanıt HEAD'i + çalışma ağacı fingerprint'i, attempt yolları, live çağrı sayacı, gerçek engel ve sonraki komut olsun. Eski run kanıtları ezilmesin. Ortak `out/lab/state.json` şemasını ve eski product-goal kabul dosyalarını değiştirme.

Final rapor kısa ve denetlenebilir olsun: ne değişti; hangi testler gerçekten çalıştı; hangi model/digest kullanıldı; dört canlı çağrının sonucu; kaynak/transform/payload kanıtları; süre ve ölçülebilen kaynaklar; tekrar üretme komutları; kalan sınırlar.

Tüm A01–A12 geçtiyse **yalnız SEMREAD-001A complete** yaz ve dur. 001B'yi, ikinci modeli veya semantic benchmark'ı otomatik başlatma. Kod/mock testleri geçip live bağımlılık yoksa `implementation_ready, live_validation_blocked` gibi açık ayrım yaz; bütün goal'u tamamlandı gösterme. Limit dolarsa veya gerçek dış bağımlılık engeli kalırsa yapılabilen işleri ve gerekli tek sonraki adımı kaydet.
