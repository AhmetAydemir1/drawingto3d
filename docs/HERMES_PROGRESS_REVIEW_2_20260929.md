# İkinci Hermes ilerleme denetimi — 2026-09-29

İncelenen HEAD: `a1acfec`. Sonuç: **önceki R01–R09 düzeltmelerinde ilerleme var; şimdi H02 kilit yarışı ve H04 gerçek ölçü/ankraj eşleştirmesi öncelikli. Kalibrasyon eşiğini körlemesine düşürmek doğru sonraki iş değil.** Bu denetim ürün kodunu değiştirmedi; yeni devam goal'unu ve görev kayıtlarını güncelledi.

## Kanıtlanan ilerleme

- Hermes'in `out/lab/review-checkpoint/` teslimi mevcut. Kaydedilmiş tam test log'u **739 passed** diyor; bu denetimde tam takım yeniden çalıştırılmadı.
- İlgili üç test dosyasını bu denetimde yeniden çalıştırdım: **66 passed, 1 failed in 9.65s**. Başarısız test `tests/test_lab_runner.py::test_the_lock_is_atomic_across_two_processes`. Dolayısıyla “H02 tamamen kapalı” güncel tekrar çalıştırmada doğrulanmadı.
- H01 testleri ve H03 generator testleri bu seçili koşuda geçti. R06/R07 düzeltmeleri ve kenardan doğru ölçü yazılması korunuyor. V2 levha PNG'sinde 45/30 etiketleri görsel olarak da kontrol edildi.
- Önceki teslimin manifestindeki **56 dosya hash'i eşleşti**. Dört sentetik parçanın v2 korpusu ve QA raporları var. Bu durum gerçek/bağımsız çizim başarısı veya eğitim seti yeterliliği değildir.
- Mevcut baseline **4 ayrı parçada 5 deneme** içeriyor: üç vektör kalibrasyon reddi ve aynı raster parçanın iki CAD hatası. Değerlendiriciye ulaşan STEP yok. Beş deneme “beş bağımsız parça” değildir; uçtan uca doğru STEP teslimi bu kayıtta 0/5, yalnız üretilmiş STEP'ler üzerindeki geometri doğruluğu ise hesaplanamaz.

Bağımsız inceleme: [probe.py](../eval/audits/20260929-hermes-review2/probe.py), [gözlemler](../eval/audits/20260929-hermes-review2/observations.json). Model çağrısı yapılmadı, ücretli kaynak açılmadı. Canlı RunPod hesabı bu turda sorgulanmadı.

## S01 — H02 kilit dosyası yayınlama yarışı sürüyor

`src/drawingto3d_lab/state.py:169`: `O_EXCL` dosyayı oluşturur; JSON içerik sonraki adımda yazılır. Bu arada ikinci süreç dosyayı okursa boş içerikte `JSONDecodeError` → `ValueError` ile çöker. Mevcut yarış testinde tam olarak bu hata oluştu. Ayrı deterministik probe da bu yayınlama aralığını boş lock dosyasıyla kurarak aynı hatayı üretti.

Kabul: kilit sahipliği ve yayınlama atomik/yarışa dayanıklı olmalı; yarım içerik “boş slot” sayılmamalı. Bayat kilit kurtarma ve bırakma yalnız ilgili sahipliği etkilesin. İki süreç testinde kazanan süreç kilidi tutarken kaybeden kontrollü `acquired=false` dönmeli. Mevcut testte çocukların hemen çıkması da yarışın anlamını zayıflatıyor; barrier ile aynı anda başlat, sahibi kontrol bitene kadar canlı tut. Tek tekrarın yeşil olması yeterli kanıt değil; deterministik yayınlama testi ve sınırlı tekrarlı eşzamanlı test kullan.

## S02 — “Üç yerine iki ölçü yeterli” teşhisi yalnız bir paftaya uyuyor

Gerçek v2 PDF'ler `load_page → perceive → scale.measure → consensus` ile tekrar okundu. Üretici etiketleri ürün girdisi yapılmadı; `minimum=2` yalnız teşhis çağrısıdır, ürün ayarı değiştirilmedi.

| Parça | Okunan (mm, piksel) çiftleri | İma edilen px/mm | minimum=3 | minimum=2 |
|---|---|---|---|---|
| pilot-plate-01 | (60, 472.5), (45, 236.5) | 7.875 ve 5.2556 | yok | yok |
| pilot-plate-02 | (80, 630), (60, 354.5) | 7.875 ve 5.9083 | yok | yok |
| pilot-step-01 | (20, 157.5), (15, 118) | 7.875 ve 7.8667 | yok | var |

İlk iki paftada sadece çift sayısı eksik değil, ölçü ile seçilen uçların uzunluğu uyuşmuyor. Örneğin 45 mm için 7.875 px/mm'de 354.375 px beklenirken 236.5 px seçilmiş. Sabit doğru ölçek ürün girdisi yapılamaz; bu yalnız bağımsız teşhis aritmetiğidir.

Yeni iş: `perceive` ölçü kapısı/ankraj seçimi, görünüş ayırma, `bind` ve `meaning` boyunca hangi gerçek ölçünün nerede elendiğini veya yanlış uçlara bağlandığını kimliğiyle izle. Aynı sayfanın text/arrow/extension/anchor bilgilerini görsel overlay ile göster. `consensus minimum=2` veya paftaya üçüncü ölçü ekleme, ilk iki hatalı eşleşmeyi kapatmaz. Her paftayı tek ölçekli varsaymak yerine farklı ölçekli detay görünüşlerini de kabul sözleşmesinde ayır.

Eşik değişecekse bağımsız kanıt şartı ve karşı örnekler gerekir: aynı ölçünün iki kopyası, iki tutarlı ama yanlış eşleşme, farklı ölçekli görünüş, aykırı değer, ölçüsüz/eksik pafta. Sabit parça adı, beklenen boyut veya korpus ölçeği ile özel çözüm kabul değil.

Hermes'in `out/lab/review-checkpoint/probes/calibration-probe.py` dosyasında `ROOT = Path(__file__).resolve().parent` mevcut konum için yanlış: proje dizini yerine `.../probes` seçiliyor. Eski dosyayı değiştirmeden, proje kökünü doğru bulan yeni sürümlü teşhis aracı kullan.

## S03 — Baseline model kullanımı ve başarı kaydı gerçeği göstermiyor

- `cli.plan_from_drawing`, `read_sheet` reddinde `chat.complete` öncesinde döner. Sahte yerel chat nesnesiyle mevcut levhada **0 inference çağrısı** doğrulandı. Bir CLI'nin çalışması “model çalıştı” değildir.
- `planner.propose_plan` içindeki `chat.complete` çağrısı metin kanıtını gönderir; `image_png` verilmez. Vision yetenekli model seçilmesi, görüntü gönderildiğini kanıtlamaz. Mevcut raporun “request carries the image” açıklaması bu yol için yanlıştır.
- Raster `read/build` kolu `reason_drawing`, `OllamaVision` ve coder kullanır. Bu kol “modelsiz” diye raporlanamaz. Raster kod üretme yoluyla vektör kural yolunu tek modelsiz baseline gibi kıyaslama.
- `_cli` çağrısında timeout yok; yeni baseline script'i H02 koşucusunun süre/süreç ağacı korumasını kullanmıyor. Yerel deneyin arka planda kalmaması için aynı kanıtlanmış korumayı yeniden kullan.
- `model-plan` planı için ayrı STEP derleme/değerlendirme yok; yalnız kural yolunun STEP'i değerlendiriliyor. Bu haliyle modelin geometri başarısı ölçülmüş değil.

Kabul: `command_started`, `inference_called`, `image_sent`, `plan_produced`, `step_built`, `evaluated` ayrı alanlar olsun. Çağrı kanıtı adapter sınırında kaydedilsin; sabit açıklama cümlesi olmasın. İki kol aynı girdide karşılaştırılmalı; kol başına gerçek pipeline ve model revision/settings kayıtlı olmalı. Model planı oluşursa aynı kabul sözleşmesiyle build/eval yap; oluşmazsa nedenini kaydet. Eski serbest kod üreten raster kolu yeni yapılandırılmış ürün yolu gibi adlandırma.

## S04 — Deney/split kayıtları

`splits.json` içinde `pilot-plate-02` held_out yazıyor; buna rağmen baseline ve sonraki hata teşhisinde kullanılmış. Dosyanın caveat alanı zaten “bağımsız gizli test değil, smoke set” diyor. Güncel manifestte bunu `development_exposed`/regression olarak sürümlü kaydet; ileride bağımsız test için yeni parça aileleri seç. Parametreleri değişen aynı `plate_holes` şablonuna ayrı aile adı vermek bağımsız şablon genellemesi kanıtı değil.

Hata raporu `first_divergence` ile `terminal_failure` ayrımını korusun. CAD'de reddedilen uydurma 260 mm'nin kökü okuma/plan olabilir; sadece `CAD işlemi` yazmak eğitimi yanlış katmana yönlendirir. Beş satırın dördü farklı parça olduğundan `attempt_count`, `unique_part_count`, kol bazlı paydalar ayrı olsun.

## Güncel devam kararı

H00'ı yeniden yapma; H01'i bu turdaki kabul kapsamıyla koru. H02 S01 küçük düzeltmesi → H04 S02 gerçek ölçü/uç teşhisi → S03/S04 baseline düzeltmesi → mevcut dört parçanın aynı girdilerle yeni sürümlü ölçümü. H03 sentetik QA ilerlemesi korunur; bağımsız veri ve görünüş/datum kapsamı henüz genel ürün kabulü değildir.

Sonlu hedef: `out/lab/calibration-checkpoint/` içinde rapor, test kanıtı, ankraj overlay'leri, ham çağrı kayıtları ve doğru paydalı baseline. Hedefi “bir örnek geçene kadar eşiği düşür” yapma. Her hata sınıfında en fazla üç genel düzeltme; başarısızlık ve desteklenmeyen şekiller de sonuçtur. Pozitif kontrol yalnız ilan edilmiş destek içinde olmalı, zor örnekler paydadan çıkarılmamalı.

Bu goal yerel. H04 eğitim kararı ancak okuma/model kaynaklı, doğru etiketlenebilir hata en az üç ayrı parçada ölçüldüğünde değerlendirilsin. Bugünkü rapor bunun kanıtı değil. İlk RunPod teknik denemesinin 3 USD ve toplam hizmet bütçesinin 20 USD sınırı değişmedi; H05/M1 ve H06 hazırlığı tamamlanmadan GPU açılmaz.
