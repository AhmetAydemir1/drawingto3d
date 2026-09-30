# Üçüncü ilerleme denetimi — 2026-09-29

HEAD `c77ad16`; önceki uygulama `d4cdbd8`. **S01 kilit ve S02 yanlış ölçü uzunluğu düzeltmeleri ilerledi. H04 hâlâ açık: iki levhada ölçü yakalama eksik, dört parçalık son koşuda STEP yok ve model kolu çalıştırılmamış.** Sonraki iş yeni model eğitmek değil, mevcut model karşılaştırmasını gerçekten çalışır ve doğru kayıtlı hâle getirmek.

## Bu turda doğrulananlar

- `tests/test_lab_runner.py`, `test_inference_log.py`, `test_baseline_fields.py`, `test_lines.py`, `test_scale.py`: **54 passed in 3.14s**.
- `test_bind.py`, `test_meaning.py`, `test_perceive.py`, `test_dimensions.py`: **100 passed in 13.95s**. Toplam 154 ilgili test bu turda yeniden çalıştırıldı. Eski rapordaki 755 passed tam takım kaydı bu turda yeniden çalıştırılmış sayılmaz.
- V2 gerçek PDF'lerden yeniden ölçüm: plate-01 `(60,472.5), (45,354.5)`; plate-02 `(80,630), (60,472.5)`; step-01 `(60,472.5), (20,157.5), (15,118)`. Önceki hatalı 236.5/354.5 uzunlukları düzeldi. İki levhada iki tutarlı çift var; step-01 üç çiftle kalibre oluyor.
- Mevcut `calibration-checkpoint` baseline'ı dört parça, sıfır STEP/değerlendirme ve `--no-model` koşusu. Model karşılaştırması henüz ölçülmüş değil. Step parçasının kural arketipinin dışında kalması modelin başarısızlığı değildir.
- S01'in yeni token/guard/publish testleri geçti; eski kilit onarımını baştan yaptırmaya gerek yok. Bu kabul, baseline sürücüsünün bütün sınırları kullandığı anlamına gelmez.

Bağımsız ek probe: [betik](../eval/audits/20260929-hermes-review3/probe.py), [sonuçlar](../eval/audits/20260929-hermes-review3/observations.json). Probe sahte adapter/komut kullanır; gerçek model veya bulut çağırmaz. Ürün kaynak koduna bu denetimde dokunulmadı.

## T01 — read/build aynı çağrı kaydını eziyor (P1)

`eval/lab_baseline.py:240` iki CLI komutuna aynı `product/inference-log.json` yolunu veriyor. Her komutta `cli._recorder` yeni `Recorder` yaratıyor; `Recorder.__init__` boş kayıtla dosyayı yeniden yazıyor. Probe'da vision/image=true kaydı ardından coder/image=false ile değişti; son dosyada ilk çağrı yok.

Bu nedenle önceki raporun “raster kolu hiç görsel göndermedi” sonucu kanıtlanmış değil. Son dosya yalnız son build komutunu anlatıyor olabilir; eski read kaydının tam içeriği artık bu dosyadan çıkarılamaz. Gerçek geçmiş çağrıları tahminle doldurma; eski raporu sürümlü düzeltme notuyla işaretle, yeni koşuda ayrı komut/deneme log'ları kullan ve kol toplamını bunlardan oluştur. `records.json` varlığını doğrulanmış CAD planı diye etiketleme; okuma kaydı / model programı / yapılandırılmış plan ayrı olsun.

## T02 — kesilen model çağrısı “hiç çağrı yok” görünüyor (P1)

`inference_log.py` sarmalayıcıları çağrıyı yalnız dönüşte veya `except Exception` içinde kaydediyor. Kontrollü `KeyboardInterrupt` probe'unda adapter'a girildiği hâlde log `calls=0, inference_called=false` kaldı. Süre dolduğunda süreç grubunun öldürülmesi de sonradan yazmayı garanti etmez; normal `write_text` yarım JSON bırakabilir.

Kabul: adapter'a girmeden kalıcı `started` kaydı, sonra aynı call_id için completed/error; kesinti sonrası unfinished/unknown. Kayıtlar atomik olsun. İstek görseli içermesi ile sunucunun isteği kabul etmesi aynı iddia değil; ölçülen sınırı belirt. Sahte adapter testi artı ağ kullanmadan gerçek alt süreç kesme testi gerekir.

## T03 — model planı build komutunda kaynak çizim eksik (P1)

`eval/lab_baseline.py:_model_step` şu komutu kuruyor: `build-general PLAN OUT`. Kural yolundaki `--drawing DRAWING` burada yok. `general.build_general`, `source.kind == drawing` planı için çizim verilmezse `ValueError: çizim kaynağı için drawing yolu gerekli` döndürüyor. Probe gerçek model çağırmadan üretilmiş komutu yakaladı ve eksik flag'i doğruladı; build guard ayrıca kaynak koddan doğrulandı.

Kabul: aynı giriş çizimi ve hash doğrulaması model kolunda da korunur. Pozitif adapter/build smoke'u ve yanlış çizim hash'inin reddi sınansın. Source kontrolünü kaldırma veya source.kind'i değiştirerek geçirme. Bu, model ürettiği doğru planın altyapı hatası yüzünden başarısız görünmesini önler. Smoke fixture'ı üründen çizim okuma başarısı sayılmaz.

## T04 — baseline süre sınırı eski anlaşmayı aşıyor (P1)

Sürücü `CLI_TIMEOUT=900` sabitini kullanıyor; mevcut goal vaka başına 600 saniye diyordu. Read/build/model/build adımları için ayrı 900 saniye de toplam vaka süresini çok büyütebilir. Süreç grubu temizleme yeniden kullanılmış, ancak baseline'ın bütün-koşu deadline'ı ve tek ağır iş kilidi kapsamı da sınanmalı.

Kabul: bir vakanın bütün adımları 600 saniyelik kalan bütçeyi, bütün koşu 7200 saniyeyi paylaşır; yeni adım kalan süreyle başlar veya başlamaz. Model denemesi mevcut yerel ayarlarda sığmıyorsa timeout olarak raporlanır; sınır sessizce yükseltilmez. Mevcut H02 araçlarını kullan, yeni scheduler yazma.

## Ana ürün işi: atlanan ölçüleri yakalamak ve gerçek model karşılaştırması

İki plaka şimdi **yanlış uç** nedeniyle değil **eksik ölçü** nedeniyle kalibre olamıyor. Kapı kalınlık, dikey boyut ve delik konum ölçülerini düşürüyor. İlgili span kimlikleri/datum/görünüş bazında nedenlerini bul. `calibration_trace.py` dropped/kept ayrımında yalnız text değerlerini kümeye koyuyor; aynı metin iki yerde geçerse yanlış sayılabilir. İzleme kimlik ve konuma dayanmalı. Sayfa anteti/ölçek notu gibi ölçü olmayan sayılar yine dışarıda kalmalı; recall artarken yanlış kabuller artmamalı.

Önerilen sonlu sıra:

1. T01–T04 için dar regresyonlar ve düzeltmeler. S01/R01–R09'u yeniden yazma.
2. Kalibre olan `pilot-step-01` ile model kolunun tek sınırlı denemesi: inference gerçekten çağrıldı mı, metin/görsel ne gönderildi, plan/build/eval nerede durdu? Başarısız veya desteklenmeyen sonuç da kayıttır. Aynı girişin kural sonucu korunur.
3. İki levhada düşen ölçülerin nedenine en fazla üç genel düzeltme turu; v2 ve zor vakalar değişmez. Üçüncü taraf regresyon paftasını ve çap/yarıçap/antet yanlış kabul testlerini koru. Eşiği veya doğru sonuç koşullarını gevşetme.
4. Dört mevcut parçada yeni sürümlü paired baseline; modelin gerçekten çağrıldığı satırlar, ret, timeout, yanlış/doğru STEP ve destek dışı sonuçlar ayrı. `first_divergence` ile `terminal_failure` ayrı kaydedilir; son CAD hatası her zaman kök neden değildir.

Teslim: `out/lab/model-baseline-checkpoint/` altında rapor, T01–T04 önce/sonra, çağrı kayıtları, ölçü recall/precision tablosu, model/kural sonuçları, eğitim kararı ve tek sonraki iş. Bir örneği geçirene kadar sınırsız deneme yok. Eğitim gerekçesi ölçülebilir model hatasına dayanmalı; şu an kod/veri okuma sorununu eğitimle kapatmaya yeterli kanıt yok.

H00 tekrarlanmaz. H02 kilit kabulü korunur; H04 sürücü entegrasyonu açık. H03 v2 sentetik QA'sı genel/bağımsız veri kabulü değildir; görülen dört parça development_exposed kalır. Model/M1 eğitim çıktısı doğrulanmış değil. Bu goal yerel; RunPod ilk teknik deneme 3 USD / toplam 20 USD sınırı değişmedi, bu denetimde hesap sorgusu veya ücretli kaynak açılması yapılmadı.
