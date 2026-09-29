# Üç adımlı planlayıcı denetimi — 2026-09-27

## Karar

Hermes'in adlandırma düzeltmesi ve kayıtlı yerel deneyleri yararlı. Ancak profil adımını
bölmeye geçme kararı erkendi: modele “accepted parameters” diye verilen ilk cevapta
olmayan ölçü kaynakları ve yanlış basılı değerler vardı. `--split` ayrıca değerlendirme
aracında yalnız `relations` koşuluna uygulanıyor, `chain_model` tek çağrı kullanıyordu.

Bu tur adım doğrulamasını ve seçeneklerin aktarımını düzeltti. Aynı model/istem/şemayla
bir canlı koşu yapıldı. **Modelden geçerli tam plan veya STEP hâlâ yok.** Sıradaki iş
kanıttan parametre seçimini düzeltmek; yalnız eskiz adlarını değiştirmek yeterli olmayacak.

## Bulgular

1. `names-3b-05` ilişki koşulunun parametre cevabı `hole_spacing_x=100.71` için `h1/h2`,
   `hole_spacing_y=60.43` için `h1/h3` yazıyor. Bunlar geometri kimlikleri; basılı kaynaklar
   `d1=100` ve `d3=60`. Eski kod yalnız gerekli kök anahtarları kontrol edip cevabı profil
   çağrısına aktarıyordu. Son birleşimdeki kaynak denetimine ulaşılmadan profil cevabı kesildi.
2. Aynı koşunun üst bilgisi “üç adımlı” diyor, fakat `chain_model` adayının gerçek arayüzü
   tek çağrı. `--normalize-names` seçeneği de koşu üst bilgisine yazılıp iki model koşuluna
   aktarılmıyordu. Kaydedilen istek ayarı ile uygulanan ayar karıştırılmamalı.
3. Ad sondası bazı sınırlı sonuçlar veriyor; “açık anahtarları bu sağlayıcıda kısıtlamak
   imkânsız” ve “tek güvenilir yol yeniden adlandırma” sonuçlarını kanıtlamıyor.
   `patternProperties` şeması boş nesneye izin veriyor; `{}` tek başına destek yokluğunu
   göstermiyor. Kapalı sözlükte `"testing"` dönen alanın şeması serbest dizeydi, `100`
   zorunlu değildi. İstemden sapma görülüyor; bütün alternatif arayüzler elenmiş değil.
4. 400 saniye zaman aşımıyla alınan sonraki yanıt tekrar içeriyor. Önceki iki zaman aşımının
   ham yanıtı yok; onların da aynı olay olduğuna kesin hüküm verilemez. Farklı boyuttaki
   görevlerin süreleri ve sistem swapı, gecikmenin hangi kısmının bellekten geldiğini ayırmaz.

## Uygulanan düzeltme

`planner.validate_step_payload()` kalıcı planın alan tanımlarını ve doğrulama işlevlerini
kullanır. Geometri şablonu veya tamamlanmamış planı geçerli gösterecek yapay CAD işlemi eklemez.

- Parametre adımı: alan türleri, ek/eksik alanlar, adlar, ifade bağımlılıkları ve basılı
  kaynakların kimlik/değer/birim uyumu kontrol edilir.
- Profil adımı: aynı parametrelerle ifadeler, yarıçaplar, kapalı kontur ve ofset kontrol edilir.
- İşlem adımı: üretilmiş gövdeler, işlem sırası ve sonuç adı tam plan doğrulayıcısından geçer.
- Hatalı veya sağlayıcının kesildiğini bildirdiği cevap sonraki çağrıya aktarılmaz. JSON
  ayrıştırılabiliyor olsa bile `done_reason=length` başarısızlıktır. Ham cevap ve hata adımda kalır.
- Kayıtlar `general-plan-step-validation-v1` ve adım başına `accepted` taşır. Buradaki
  kabul, sonraki adımın yapısal girdisi olmaya yeterliliktir; çizim anlamının doğruluğu değildir.
- Değerlendirme aracı `--split` ve `--normalize-names` seçeneklerini iki model koşuluna da
  aktarır. Rapor gerçek aday arayüzünü okur; eski `names-3b-05` satırı artık “karma” görünür.

`GeneralPlan v1`, `general-plan-v3` istemi ve `GeneralPlan reply v4` yanıt grameri korundu.
Ad adaptörü canlı ölçümde kapalı. Başlangıç çalışma ağacı korundu;
farkın kopyası `out/step-audit/before.patch`. Yeni ağırlık indirilmedi, eğitim yapılmadı.

## Eski cevabın yeniden doğrulanması

`eval/reports/step-validation-replay.json`, `names-3b-05` cevabını değiştirmeden yeniden
oynatır. İlk isteğin ve şemanın SHA-256 değerleri eski kayıtla aynı. Yeni karar ilk adımda
iki geçersiz kaynak atfı; profil çağrısı yapılmıyor. Önceden bu cevaptan sonra 178.5 saniyelik
profil çağrısı yapılmıştı. Yeniden oynatma süresi model hızlanması olarak raporlanmaz.

## Yeni canlı koşu: `step-validation-3b-01`

Yerel `qwen2.5vl:3b`, bağlam 16384, çıktı 4096, sıcaklık 0, zaman aşımı 180 saniye,
`--split`; aynı plaka ve mevcut kanıtlar. İki koşul da tamamlandı, toplam 90.26 saniye.
Tam ham kayıt: `eval/reports/step-validation-live-evidence.json`.

| Koşul | Çağrılan adımlar | Süre | Sonuç |
|---|---|---|---|
| `relations` | parameters | 20.24 sn | Geçersiz `h1/h2/h3` ölçü atıfları; profil çağrılmadı |
| `chain_model` | parameters, profile | 63.95 sn | Parametre yapısı/atıfları geçti; `pdf-0` eskiz adı geçersiz; işlemler çağrılmadı |

İlişki koşulunun ilk ham cevabı eski cevapla aynı. Gerçek çizimin parametre adımı 23.49 sn,
profil adımı 38.79 sn. Bu koşudaki üç cevap da `done_reason=stop`; çıktı sınırında kesilme yok.

**Kalan anlam hataları önemli:** gerçek çizim cevabı cep derinliğine pafta ölçeği olan
`7.82` değerini varsayım olarak veriyor; `hole_spacing_y` için `(100 - 80) / 2` yazıyor.
Bunlar yapısal denetimden geçebilir, ancak doğru ölçü yorumu oldukları kanıtlanmış değil.
Profil cevabı tek açık çizgiyi eskiz sayıyor ve `x(80 - 100) / 2` gibi geçersiz ifadeler
kullanıyor. Yalnız adları dönüştürmek bu sorunları çözmez. STEP veya geometri başarısı yok.

Kaynak ölçümü v2: sistem swapı 7647.62→10110.44 MiB, tepe 10201.94 MiB;
boş sayfa en az 56.141 MiB, Ollama RSS tepe 3838.5 MiB. Sistem değerleri diğer uygulamaları
kapsar; RSS toplam birleşik bellek değildir. Model koşu sonunda boşaltıldı.

## Doğrulama

Odaklı planlayıcı/adım/seçenek testleri: 81 geçti; rapor testleri: 7 geçti.
Tam çalışma ağacında **358 test geçti, 223.90 sn** (`out/step-audit/pytest.txt`).
`baseline_report.py --check` geçti; `check_tables.py` 20 satırda 0 uyuşmazlık buldu.
`git diff --check` temiz, `general.py` farkı boş.

## En son Hermes çalışması da incelendi: `suggest-3b-01`

Bu denetimin 17:18 ölçümünden sonra çalışma ağacına profil başına çağrı, kontur döngüsü
onarımı, ayrı kanıt başlıkları, parametre kuralları ve `suggested_names` eklendi. Bunlar
korundu. Güncel istemler v6 (`general-plan-v6-suggested-names` ve split karşılığı);
kalıcı CAD sözleşmesi hâlâ v1. Yukarıdaki v3 istemi bilgisi 17:18 koşusuna aittir.

19:30'daki son koşu `suggest-3b-01`, 46.12 sn'de tamamlandı. İki koşul da parametre
adımında başarısız: ilişki cevabı `d1`, gerçek çizim cevabı bildirmediği `diameter_2` adını
ifadede kullanıyor. Bu turda da plan/STEP yok. Güncel kaynak, ham cevaplar ve birbirinden
bağımsız denetimler `latest-parameter-evidence.json` içine kaydedildi.

**“Tek hata sınıfı kaldı” sonucu çıkarılamaz.** İlk hata diğerlerini gizliyor. Aynı cevabı
hiç değiştirmeden yalnız basılı kaynak denetimini çalıştırınca ilişkilerde üç, gerçek
çizimde bir yanlış değer bulunuyor: 100 yerine 100.71, 80 yerine 80.46, 60 yerine 60.43.
Gerçek çizim cevabındaki iki `edge_spacing` varsayımı da 7.82; açıklama bunu sayfa piksel
çözünürlüğünden aldığını söylüyor. Bildirilmemiş parametreyi eklemek bu anlam hatalarını
çözmeyecek. Genel dönüşümün yalnız prompt cümleleriyle düzelmesi gösterilmiş değil.

Sonraki iş, mevcut `suggested_names` ve kaynak kayıtlarını kullanarak basılı parametre
kataloğunu uygulamada kurmaktır. Model bu bilgiyi yeniden yazmamalı; seçim/anlam ve
kaynağı açık türetme önerileri üretmeli. Bu, belirli bir parçaya özel şablon değildir.
Kaynak aktarımının doğruluğu ile ölçünün geometrik anlamı ayrı değerlendirilmelidir.

## Sıradaki teslim

PLAN Bölüm 21: basılı değerleri modelin yeniden yazmasını kaldıran, kanıttan parametre
seçen küçük bir arayüz deneyi. Model mevcut ölçü kaydını ve anlamını seçsin; uygulama
basılı değeri/birimi o kayıttan alsın. Geometri kimliği ile ölçü kaynağı ayrılmalı.
Türetilmiş ifadeler bilinen parametreleri kullanmalı; desteklenmeyen varsayımlar ve
çelişkili ölçü yorumları inceleme/soru olarak görünmeli. Ürün çıktısı doğrulanmış sayılmamalı.

Önce küçük kaynak seçimi testleri, sonra mevcut iki farklı parça grubunda yalnız parametre
adımının sınırlı ölçümü. İlerleme atıf doğruluğu, basılı değerin korunması ve yanlış varsayım
olarak ayrı raporlansın. Parametre anlamı düzelmeden yeni uzun profil denemeleri yapma.
Kalıcı CAD sözleşmesi, önceki ham kayıtlar ve bağımsız veri/eğitim hedefi korunsun.
