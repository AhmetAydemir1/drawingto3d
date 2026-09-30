# Dördüncü denetim ve başarıya kadar devam sözleşmesi

İncelenen HEAD: `e801cb1`; T01–T04 uygulaması `fa47c83`. **Altyapı ilerledi; ürün henüz doğru parça üretmiyor. Yeni kullanıcı talimatı: ara kontrol noktalarında işi bitirme, tanımlı başarıya kadar devam et.** Bu inceleme yeni goal'u hazırlar; burada Hermes goal'u, model eğitimi veya ücretli kaynak başlatılmadı.

## Yeniden doğrulama

- `test_inference_log`, `test_baseline_fields`, `test_calibration_trace`, `test_lab_runner`, `test_feature_metrics`: **88 passed in 10.76s**. Hatalı STEP fixture'ının kernel uyarısı beklenen negatif test çıktısıdır. Önceki rapordaki 772-test tam takım koşusu bu turda tekrarlanmadı.
- Ayrı read/build log'ları, started/unfinished kayıtları, model build'e `--drawing` aktarımı ve paylaşılmış süre bütçesi mevcut. Kapanan T01–T04 yeniden yazılmamalı.
- Son deneyde dört parça için model kolu denendi; üçünde model okuma reddi nedeniyle çağrılmadı, step-01'de bir metin planner çağrısı yapıldı. Bu çağrı STEP üretti; bağımsız verdict **fail**. Raster read adımında dört görüntülü çağrı kayıtlı.
- Bağımsız olarak üretilen ve referans STEP'i yeniden açtım: üretilen **60×10×10 mm, 6000 mm³, delik yok**; referans **60×40×6 mm, 11830.354 mm³, Ø6 geçişli delik var**. Bu küçük hizalama toleransı sorunu değil, yanlış geometri/yorumdur.

[Makine okunur kanıt](../eval/audits/20260929-hermes-review4/observations.json) test sonuçları, gerçek STEP ölçümleri, kaynak hash'leri ve aşağıdaki küçük karşı örnekleri içerir. Bu inceleme ürün kaynak kodunu değiştirmedi; gerçek model veya RunPod hesabına çağrı yapmadı.

## Öncelik düzeltmesi: raster CAD'i zorla geçirmek doğru başlangıç değil

`pilot-block-01/product/records.json`: kalınlık **4**, kenar **9**, delik aralığı **2**, kenar **60** okunmuş. Program `geo.plate(9,9,4)` ve Ø2 delikler kurmaya çalışıyor. Referans blok **60×40×20**, cep **40×25×8**, Ø8 delikli. Dolayısıyla “tek kalan adım CAD kurulumu” açıklaması kök nedeni göstermiyor. Katı sayısı hatasını bastırmak yanlış parçayı çalıştırabilir; önce hangi yanlış değerin hangi kırpımdan ve hangi role bağlanarak geldiğini bul.

Step model planında 20 mm adım genişliği başka eksen boyutu gibi yorumlanıp yarıya bölünmüş; 10 mm kalınlık türetilmiş. Circle ayrı body olarak extrude ediliyor, `result=body_outline` onu sonuç dışında bırakıyor. Planın kendi audit'inin geçmesi çizime sadakati kanıtlamaz. Rapordaki “parçada daire yok” ifadesi de doğru değil: referansta Ø6 delik var; modelin son katısında yok.

İlk ürün işi: kaynak okuma → görünüş/datum/ölçü rolü → bağlama → işlem yönü/derinliği → CAD sırasındaki **ilk yanlışlığı** düzelt. Sayı metinde var diye her parametreye kullanılabilir sayma. Sayısal literal, bölme/türetme, varsayım ve kullanılmayan işlemler anlamsal doğrulamadan kaçmamalı. Legacy serbest kod raster kolu teşhis için kalabilir; genel ürün sözleşmesi sürümlü veri + deterministik CAD'dir.

## U01 — eğitim verisi seçimi bilinmeyen sonucu pozitif sayabiliyor

`eval/lab_baseline.py:_training_decision` model kolunda `fail` dışındaki her verdict'i `positive` yapıyor; `step_built/evaluated/inference_called` true olduğunda **not_evaluated, error ve null** karşı örnekleri pozitif çıktı. Yalnız gerçek `pass` pozitif; gerçek `fail` negatif aday; diğerleri excluded/unknown olmalı. Geçersiz model çıktısını doğru hedef olarak öğretme.

Bu fonksiyon eğitim gerekliliği kararı da değil: satırları positive/negative/excluded sınıflıyor. Ayrı `training-decision.json` şu kararlardan biri olmalı: `train_targeted`, `fix_rules_first`, `need_data`, `training_not_justified`; görev, kök hata, kanıt sayısı ve M1/bütçe kapılarıyla. Ret/STEP yokluğu, doğru etiketli bir OCR görev örneğini otomatik olarak eğitim dışı yapmaz; öğretilecek dar görev ve etiket kökeni ayrıca değerlendirilir.

## U02 — hata izi çalışılmayan son adımı “terminal hata” sayıyor

`_trace` son false bayrağını seçiyor. Plan bile oluşmayan örnekte `terminal_failure=verdict_pass`; evaluator hiç koşmadı. Bu alan bu haliyle kök hata önceliğini yanıltıyor. `not_started`, `blocked_by_previous`, `failed`, `completed` ayrı durumlar; terminal hata gerçekten çalışıp duran adım olmalı. En erken semantik hata (ör. yanlış kalınlık okuma) ve son çalışan aşamanın hatası ayrı kanıt taşımalı.

## Başarı sözleşmesi

Bu goal'un ürün kapsamı ilk kullanılabilir **profil uzatma, basamak, geçişli/kör delik ve dikdörtgen cep** akışıdır; her türlü teknik çizimin kusursuz çözümü iddiası değildir. PLAN.md değişmezleri ve P01–P08'in zorunlu ürün kabulleri korunur. Eksik ölçü/görünüşte soru sormak doğrudur; bunu tam otomatik doğru STEP sayma.

1. Mevcut dört v2 geliştirme vakası sonuç tablosunda sabit kalır. Tam tanımlı olanların doğru STEP'i üretilmeli; gerçek belirsizlik varsa kanıtlanmalı, eksik bilgi kullanıcıdan alınmalı ve destekli akış ayrıca ölçülmeli. Okuyamadığı bilgiyi “çizimde yok” sayma. Eksik kaynak yüzünden bekleyen vaka varken hedef tamamlandı denmez.
2. Ürün gerçek UI/store/CAD yolunda ve M1 üzerinde çevrimdışı çalışmalı; yalnız test fixture'ı/elle doğru plan/CLI artefaktı başarı değildir. Kullanıcı müdahaleleri ve otomatik başarı ayrı sayılır. Gerekli parametreleri uyduran/yanlış katı üreten girişler güvenle reddedilmeli.
3. Geliştirme sonrası PLAN'ın P08 hedefiyle **en az 20 yeni parça, en az 10 raster** ayrı değerlendirilir. Girdi yeterliliği, desteklenen kapsam ve beklenen retler ölçümden önce sabitlenir. Tam tanımlı ve kapsam içi pozitif vakaların tamamı zorunlu geometrik kabulleri geçmeli; negatif vakalar yanlış “doğru STEP” almamalı. Sonuçlara bakılarak vaka atılmaz. Bağımsız erişim ayrımı yoksa saklı test iddiası yok.
4. Final sette hata bulunursa artık o vaka görülmüştür: regression'a al, kök nedeni düzelt, yeni bağımsız adaylarla yeni final sürümü oluştur. Eski bütün sonuçları koru. Aynı dört parçayı değiştirip adlandırmak genelleme kanıtı değildir.

## Devam etme kuralı

Önceki “rapor teslim edince dur” ve “üç hata turundan sonra goal'u bitir” talimatları **yerel ürün işi için kaldırıldı**. Üç başarısız deneme aynı hipotezi tekrarlamayı bırakma eşiğidir; görevi bitirme eşiği değildir. Kök neden hipotezini değiştir, daha küçük karşı örnek üret, genel düzeltmeyi uygula, ölç ve sonraki açığa geç. Rapor, milestone ve `fix_rules_first` ara sonuçtur. Yeni kullanıcıdan “devam et” mesajı bekleme.

Vaka 600 s, tek koşu 7200 s, tek ağır iş ve bütün maliyet sınırları korunur. Bir koşu bitince süreçleri temizle ve durumu yaz; bütçe/otorite uygunsa sonraki farklı deney batch'ine devam et. Aynı başarısız komutu sonsuza kadar yineleme; gereksiz tam takım test tekrarı yapma. Runtime/bağlam sınırı olursa devam kaydı bırak; başarı iddiası kurma. Sistem yeniden başlatmayı otomatik desteklemiyorsa varmış gibi vaat etme.

Yalnız başarı, açık kullanıcı durdurması, sistem sınırı, gerçek eksik kullanıcı bilgisi/erişim veya aşılmaması gereken bütçe/onay sınırı işin durmasını gerektirir. Engel yalnız bir kolu etkiliyorsa bağımsız yerel işleri sürdür. Başarının garanti edilemeyeceği gerçeğini gizleme; kanıtlanmamış kabulü tamamlandı yapma.

## Bulut sınırı

Eğitim zorunlu değil. H04 dar görevde öğrenilebilir model hatası gösterirse H05 M1 temel modeli ve export yolu, H06 veri/eğitim betiği/kapatma koruması doğrulanır. Önceden kabul edilmiş ilk RunPod teknik denemesi **en fazla 3 USD**, toplam hizmet bütçesi **20 USD** (12 eğitim + 5 rezerv dahil). İlk 3 USD raporu kullanıcı tarafından değerlendirilmeden sonraki ücretli eğitim başlamaz; bu eski bütçe şartı “başarana kadar” ifadesiyle kaldırılmış sayılmaz. Yerel bağımsız işleri bu bekleme noktasında sürdür. DeepSeek API maliyeti ayrı; yeni bütçe/topup uydurma. Final ürün buluta bağımlı olmaz.
