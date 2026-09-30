# Hermes devam goal’u — üçüncü denetim

Önce [üçüncü denetimi](docs/HERMES_PROGRESS_REVIEW_3_20260929.md) oku. [Plan](docs/HERMES_IMPLEMENTATION_PLAN.md) bölüm 0 ve [görev kaydı](docs/hermes-task-queue.json) güncellendi. Önceki prompt [arşivde](docs/HERMES_PROMPT_BEFORE_REVIEW3_20260929.md).

Aktif goal varsa aynı işi bu talimatlarla sürdür; ikinci paralel koşu başlatma. Aşağıdaki prompt bu dosyada yalnız hazırlanmıştır, burada çalıştırılmadı.

```text
/goal /Users/aydemir/Desktop/drawingto3d projesinde c77ad16 sonrasından devam et. Önce docs/HERMES_PROGRESS_REVIEW_3_20260929.md, docs/HERMES_IMPLEMENTATION_PLAN.md bölüm 0 ve docs/hermes-task-queue.json oku. H00’ı ve kapanan R01–R09/S01 onarımlarını yeniden yapma. Kullanıcının mevcut değişikliklerini, v2 korpusunu ve önceki kanıtları koru. Kod düzeltmeleri ve out/lab/model-baseline-checkpoint/ altında sonlu ölçüm raporu teslim et.

İlerleme: üçüncü denetimde 154 ilgili test geçti; eski kilit yarışı testleri yeşil. Plate-01/02 yanlış uzunlukları düzeldi, şimdi iki tutarlı ölçü var. Step-01 üç ölçüyle kalibre oluyor, kural arketipi dışında kalıyor. Son baseline --no-model ile dört parçada sıfır STEP: model karşılaştırması henüz yapılmış değil. Eski 755 passed log’unu yeni çalıştırılmış gibi raporlama.

Önce T01–T04 dar altyapı açıklarını kapat; eval/audits/20260929-hermes-review3/probe.py ve observations.json kanıtını kullan, eski gözlemleri değiştirme:

T01: read ve build aynı product/inference-log.json yolunu kullanıyor; Recorder yeniden kurulunca ilk çağrıların kanıtı eziliyor. Her komut/attempt ayrı değişmez kayıt tutsun, kol özeti tüm kayıtları birleştirsin. Eski “raster hiç görsel göndermedi” iddiasını kesin gerçek sayma: son log sadece build’i anlatıyor olabilir. Vision çağrılı read ardından coder çağrılı build karşı örneği ekle. Eski koşunun kayıp çağrılarını uydurma; yeniden koşulmadıkça unknown yaz. records.json okumadır, yapılandırılmış CAD planı değildir; records_produced/program_produced/plan_produced ayrı olsun.

T02: çağrı kayıtları adapter dönüşünden sonra yazılıyor; süreç kesilince calls=0 yanlış kalabiliyor. Adapter çağrısından ÖNCE kalıcı started/call_id, ardından completed/error yaz; kesilen çağrı unfinished/unknown kalsın. JSON yazımı atomik olsun. Görselin istekte bulunması ile sunucu kabulünü ayır. Sahte adapter ve ağ kullanmayan gerçek alt süreç kesme testleriyle kanıtla; key/token loglama.

T03: _model_step içindeki build-general çağrısına aynı giriş çizimini --drawing ile ver; source hash kontrolünü koru. Model planı doğru olsa bile şu an kaynak yolu eksikliğinde reddediliyor. Model kolunun plan→build→evaluator bağlantısını kontrollü pozitif fixture ve yanlış kaynak hash’i reddiyle test et. Bu fixture’ı uçtan uca çizim okuma başarısı sayma, model doğruluğu olarak raporlama.

T04: CLI_TIMEOUT=900 anlaşmadaki 600 saniye vaka tavanını aşıyor. Tek vakanın read/build/model/build adımları toplam 600 saniyeyi, koşu toplam 7200 saniyeyi paylaşsın. Her adım kalan deadline’ı alsın; kalan süre yoksa başlamasın. H02’nin süreç ağacı kapatma ve tek ağır iş kilidini baseline’ın tamamında kullan; yeni scheduler yazma. Daha büyük timeout’u sessizce kabul etme. Zaman aşımı gerçek sonuç olarak raporlansın.

Sonra kalibre olan pilot-step-01’de aynı girdinin kural ve model kolunu bir kez sınırlı koş: model gerçekten çağrılıyor mu, metin/görsel ne gönderiliyor, plan çıkarsa STEP/evaluator’a ulaşıyor mu? Mevcut kurulu yerel model ve sabit ayar kullan. Arketip dışı kural reddi modelin başarısızlığı değildir. Model hiç çağrılmadıysa önündeki somut engeli yaz. Model-plan metin kanıtından çalışan planner’dır; vision model etiketi seçildi diye görüntü gönderildi sayma. Ret veya yanlış STEP de dürüst ölçümdür; geçene kadar kör tekrar yapma.

Ana ürün işi iki levhada düşen gerçek ölçülerdir. perceive/bind/meaning hattında kalınlık, dikey boyut ve delik konum değerlerinin hangi span/ok/uzatma çizgisi/datum/görünüş nedeniyle elendiğini kaydet ve overlay göster. calibration_trace kept/dropped ayrımı yalnız metin kümesinden çıkmasın; aynı sayı farklı yerde geçebilir, kimlik/konumla izle. Genel kuralla kayıp ölçüleri geri kazan; antet, ölçek notu, çap/yarıçap ve komşu çizgi yanlış kabul regresyonlarını koru. Recall ile yanlış kabul/precision birlikte raporlansın. Parça adı, dosya yolu, sabit ölçek veya referans ölçüyle özel çözüm yok. Üç ölçü eşiğini/toleransı gevşeterek ya da v2 paftayı değiştirerek başarılı gösterme. Hata sınıfı başına en fazla üç genel düzeltme turu.

Ardından dört mevcut v2 parçayı aynı girdilerle yeni paired baseline’da ölç. Önceki sonuçları ezme; zor parçaları veya başarısız çağrıları paydadan çıkarma. Kural/yapılandırılmış model/legacy serbest kod raster yollarını doğru isimlendir. Reference STEP, labels, generator parametreleri ve doğru plan ürün/model girdisi olamaz. Kullanıcı müdahalelerini ayrı say. command_started, inference_called, image_attached, plan_produced, step_built, evaluated ve unfinished ayrı olsun. attempts, unique_parts, kol bazlı doğru/yanlış STEP, ret, timeout ve destek dışı paydalarını koru. first_divergence ile terminal_failure ayrı kaydedilsin. Bütün dört parça development_exposed; bağımsız hidden iddiası yok.

Sınırlar: tek ağır yerel iş; vaka toplam 600 s, koşu toplam 7200 s; hata sınıfı başına üç düzeltme turu. İlgili testleri ve değişikliğin etkilediği regresyonları çalıştır; her küçük değişiklikte 755 testi yeniden başlatma. Yeni model indirme/eğitme, büyük korpus veya yeni arayüz bu goal’da yok. RunPod kaynağı açma; önceki toplam 20 USD / ilk teknik deneme 3 USD bütçe değişmedi. H05 M1 uyumluluğu ve H06 hazırlığı tamamlanmadan buluta geçilmez.

Son teslim: out/lab/model-baseline-checkpoint/report.md, findings.json, baseline-results.json, training-decision.json, artifact-manifest.json, command-logs/, overlays/ ve test kanıtları. Raporda T01–T04 kapanışı, step-01 model denemesi, düşen/kazanılan ölçüler ve yanlış kabul etkisi, dört parçalık kol karşılaştırması, kalan destek sınırları ve tek sonraki adım olsun. Eğitim kararı train_targeted/fix_rules_first/need_data/training_not_justified değerlerinden biri; train_targeted için en az üç ayrı parçada doğru etiketlenebilir model/okuma hatası kanıtı gerekir. Eksik kaynak/erişimde kısmi teslimi ve somut engeli açık yaz; sonsuz tekrar veya ürün tamamlandı iddiası yok.

Görev kaydını ve out/lab/next.md’yi gerçek kabulle güncelle. Şimdi T01 kayıt izolasyonu regresyonu ve T03 kaynak çizim bağlantısıyla başla; sonra yukarıdaki sırayı tamamla. Sonlu raporu teslim et ve otomatik ücretli eğitime geçme.
```
