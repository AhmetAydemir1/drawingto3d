# Hermes ilerleme denetimi — 2026-09-29

Sonuç: **mimari yön doğru; H01/H02 kabulü açık, H03 veri üretimi henüz eğitim için güvenilir değil.** Bu denetim ürünün kodunu onarmaz; düzeltme sırasını ve bağımsız karşı örnekleri Hermes'e devreder. GPU eğitimi, model export'u veya M1 model kabulü henüz kanıtlanmış değil.

## Doğrulanan ilerleme

- `eval/feature_metrics.py` delik sayısı, merkez, eksen, çap, kör delik ve malzeme yerleşimi kontrollerini eklemiş. Eski kaba değerlendiricinin kaçırdığı hatalar için 16 vakalık audit kaydı var.
- `src/drawingto3d_lab/` altında JSON durum kaydı, CLI, cache, lock ve deney koşucusu var. Önceki plandaki “henüz uygulanmadı” ifadesi artık güncel değil; **kısmen uygulandı, kabulü tamamlanmadı**.
- İki sentetik parça için STEP/PDF/PNG/etiket üretilmiş. Bunlar GrabCAD'den edinilmiş gerçek çizim testleri değil.
- Bu denetimde `.venv/bin/python -m pytest tests/test_feature_metrics.py tests/test_lab_runner.py -q` yeniden çalıştırıldı: **43 passed in 7.82s**, çıkış 0. Hatalı STEP testi nedeniyle kernel'in beklenen ayrıştırma uyarısı çıktı. Bütün ürün testleri çalıştırılmış sayılmaz.
- Ek bağımsız [probe betiği](../eval/audits/20260929-hermes-progress/probe.py) aşağıdaki **9 sorunun tamamını** tekrar üretti. [Ham sonuçlar ve kaynak hash'leri](../eval/audits/20260929-hermes-progress/observations.json) bu denetimin anlık kanıtıdır.

## Kabulü engelleyen bulgular

| ID / öncelik | Bulgular ve kaynak | Tekrar üretilen sonuç / gerekli davranış |
|---|---|---|
| R01 / P1 | `runner.py:117,215`: bir `execute` içindeki işler aynı dizin, `result.json`, `manifest.json`, `complete.json` kullanıyor | İki iş çalıştırıldı; ilk işin sonucu ikinci işin etiketini taşıdı. Her iş/deneme ayrı değişmez dizin ve kimliğine bağlı marker kullanmalı. |
| R02 / P1 | `runner.py:204,290`: eksik/bozuk sonuç da `complete=true`; boş hash haritası geçiyor | Sonucu olmayan `failed` işte `resume` çağrıldı ama komut yeniden çalışmadı. Başarısız yürütme cache olamaz; geçerli JSON içindeki ürün `fail` sonucu ise tamamlanmış deney olabilir. |
| R03 / P1 | `runner.py:215`: süreç çağrısından önce `running` durumu yazılmıyor | İlk işte kontrollü KeyboardInterrupt sonrasında jobs boş; resume “iş yok” diyor. Başlatmadan önce durum, kesilince interrupted kaydı ve yeniden başlatmada kurtarma gerekir. |
| R04 / P1 | `runner.py:237`: iş timeout'u ayardaki tavanı aşıyor | Vaka sınırı 600 iken 999999 saniye runner'a geçti. Ayrıca `run_timeout_seconds` ve düzeltme turu sınırı ayarda mevcut ama yürütmede uygulanmıyor. Tavanlar gerçek deadline olmalı. |
| R05 / P1 | `state.py:56`: git status metni kod içeriğinin yerine kullanılıyor | Zaten kirli olan, watched listesinde olmayan kaynak iki kez değiştirildi; fingerprint aynı kaldı. Çalışan bağımlılıkların içerik hash'i gerekir. |
| R06 / P1 | `feature_metrics.py:397`: seyrek malzeme örneklemesi tam parça doğrulaması sayılıyor | 20×24×10 bloğa eklenen 1×1×1 mm cep `pass` aldı. Hacim farkı 1 mm³; 189 örnek nokta bunu görmedi, tüm yüzler düzlem olduğu için `unmodelled={}` kaldı. Kontrol edilmeyen cep/slot geometrisi `not_evaluated` olmalı veya bağımsız geometrik kontrolle reddedilmeli. |
| R07 / P1 | `feature_metrics.py:693`: birim sonucu ana `ok` değerine bağlanmamış | mm parça/inch spec karşılaştırmasında `units_ok=false`, `ok=true`. Birim, geçerli katı ve belirtilmiş ölçü koşulları kabul kararına bağlanmalı. |
| R08 / P1 | `generator.py:427`: kenardan çizilen ölçüye merkez koordinatı yazılıyor | 60×40 levhada (15,10) delik için soldan mesafe 45, alttan 30; çizimde 15 ve 10. Negatif koordinatlı delikte negatif uzunluk yazılmış. Datum ve ok uçlarıyla etiket birlikte düzeltilmeli. |
| R09 / P1 | `generator.py:344`: etiket basılmayan ölçüyü basılmış sayıyor | `pilot-block-01` etiketinde 8 mm cep derinliği `printed_dimensions` içinde; paftanın `printed_text` kaydında ve çizim üretim yolunda yok. Gizli parametre çizimden okunmuş bilgi olamaz. |

R01–R05 küçük kontrollü runner işleriyle sınandı; ürün okuma başarısını ölçmez. R06 gerçek build123d solid ve STEP yeniden okumasıyla sınandı. R08 mevcut PNG'nin görsel incelemesi, kodun ölçü uçları ve bağımsız aritmetikle doğrulandı. R09 etiket/pafta kaydı ve kaynak koduyla doğrulandı. Probe sonuçlarındaki geçici çalışma yolları kalıcı artefakt değildir; yeniden üretim betiği korunmuştur.

Ek kod inceleme riskleri (bu dokuz dinamik karşı örneğin sayısına dahil değil): lock edinimi read-then-write, iki süreç yarışında atomik değil; timeout yalnız doğrudan child'ı öldürüyor, wrapper'ın alt süreç ağacına ilişkin kanıt yok. `next.md` H01 hiç yapılmamış gibi kalmış; görev kuyruğu hâlâ tüm aşamaları pending gösteriyordu. Üretecin blind-hole `centre_mm` tanımı ile değerlendirici eksen aralığı merkezi de açıkça eşlenmeli. Aynı şema adı bu alanların aynı anlama geldiğini kanıtlamaz.

## Aşamaların güncel yorumu

| Aşama | Durum | Sonraki kabul |
|---|---|---|
| H00 | Tarihsel bootstrap kaydı var | Tekrar kurulum yapma; bulut öncesi canlı hesap durumu tazelenir |
| H01 | Uygulandı, 27 ilgili test geçti; kabul yeniden açık | R06/R07 + pozitif eşdeğerlik + desteklenmeyen geometride dürüst sonuç |
| H02 | Uygulandı, 16 ilgili test geçti; kabul yeniden açık | R01–R05, süreç/lock/deadline testleri |
| H03 | İki sentetik taslak var | R08/R09, etiket sözleşmesi, manifest/split/QA ve çizimden gerçek ürün koşusu |
| H04 | Kanıt yok | Yeni ve QA'dan geçmiş girdilerde hata katmanı tablosu |
| H05–H11 | Yerel kanıtta başlamamış | Önceki planın model, bütçe ve bağımsız değerlendirme kapıları geçerli |

43 mevcut testin H01/H02 dağılımı `--collect-only` ile ayrıca doğrulandı: 27 + 16. Aşama kabulü toplam test sayısından çıkarılmaz.

## Yeni öncelik ve sonlu teslim

1. H01 R06/R07: yanlış parçanın geçmesini ve birim hatasını kapat. Küçük cep gibi kontrol edilmeyen geometride konservatif `not_evaluated` ilk teslim için geçerlidir; her şeyi reddeden değişiklik kabul değildir.
2. H02 R01–R05: iki işi aynı koşuda, farklı verdict'lerle ve ardından kesinti/resume ile sınayan test ekle. Gerçek alt süreç timeout'u, atomik kilit ve toplam süre sınırı da doğrulansın. Yeni bir orkestrasyon platformu yazma.
3. H03 R08/R09: önce iki taslak çizimi düzelt, eski hatalı ham dosyaları değişmeden karantinada tut, yeni sürümü ayrı dizine yaz. Ölçü uçları/datum, değer, birim, etiket ve CAD aynı bilgiyi anlatmalı. Etiket varlığı + hacim eşleşmesi yeterli QA değil.
4. QA sonrası önce **bir yeni parçanın** yalnız PDF/PNG girdisiyle gerçek ürün/store/CAD yolunu çalıştır. Sonucu ayrı evaluator ölçsün. Sonra üç yeni geliştirme parçasına genişlet; en az bir vektör, bir raster girdi olsun. Sentetik/gerçek, model çağrısı ve kullanıcı müdahaleleri açık raporlansın. Gizli etiketle `verified_plan` üretmek uçtan uca başarı değildir.
5. `out/lab/review-checkpoint/report.md` altında R01–R09 kapanış kanıtı, testler, üç parçalık baseline, kalan açıklar ve tek sonraki işi teslim et. Bu yerel checkpoint H08'in GPU/M1 aktarım kabulü değildir. QA yapılamıyorsa gerekçeli `need_data`; sadece başarısız ürün vakaları varsa yine raporla, bunları paydadan çıkarma.

Bu yeni goal **yerel düzeltme ve baseline** içindir. Ücretli kaynak oluşturmaz; mevcut 20 USD bütçe ve ilk 3 USD sınırı gelecekteki H06–H08 için korunur. H01–H04 kapanmadan buluta geçiş zaten önceki planın koşullarını sağlamıyordu. Yeni GPU almak veya model büyütmek bu bulguları düzeltmez.

## Bulut ve doğrulama sınırı

Hermes'in 07:19 yerel bootstrap kaydı bakiye 20 USD, proje harcaması 0, aktif kaynak yok diyor. Bu denetimde `runpodctl user` ve `pod list --all` salt okunur yeniden kontrolü **network_error** verdi; dolayısıyla güncel hesap harcaması/boşluğu bağımsız doğrulanamadı. API anahtarı okunmadı veya yazdırılmadı. Bu denetim ücretli kaynak oluşturmadı. DeepSeek API maliyeti ölçülmedi; RunPod 20 USD hizmet bütçesine dahil değil.

Hermes sohbetinin tamamı bu incelemede okunmadı; değerlendirme paylaşılan dosyalar, kaynak kod ve yeniden çalıştırılan testlere dayanır. Aynı anda devam eden bir Hermes işi varsa yeni goal ikinci eşzamanlı koşu olarak başlatılmamalı; mevcut işin devam talimatı olarak uygulanmalı.

## Tekrar üretim

```bash
.venv/bin/python -m pytest tests/test_feature_metrics.py tests/test_lab_runner.py -q
.venv/bin/python eval/audits/20260929-hermes-progress/probe.py
```

Probe yeni sonuçlarını varsayılan olarak `out/lab/review-probes/<timestamp>.json` içine yazar. Bu dizindeki ilk `observations.json` denetim kaydını değiştirme. Düzeltilen pilotlar ayrı dizindeyse `--pilot-root PATH` kullan. Probe bir gözlem raporudur; kabul testlerinin yerini almaz ve çıkış 0 “dokuz hata kapandı” demek değildir. Gerçek düzeltmeler, aynı davranış koşullarını koruyan assertion'lı regresyon testleriyle doğrulansın. Desteklenen şema/datum değişirse probe adaptasyonu ve gerekçesi açık kaydedilsin.
