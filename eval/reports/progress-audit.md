# İlerleme denetimi ve uygulanan düzeltme turu

Tarih: 2026-09-27. İncelenen başlangıç HEAD: `96e0118`; çalışma ağacı temizdi.
Bu rapor kullanıcı isteğiyle oluşturulan denetim goal'unun sonucudur. Ürünün tamamlandığı
veya modelin yeni çizimlerde başarılı olduğu iddiası taşımaz.

## Karar

**Ana mimari doğru yönde; ölçümden çıkarılan bazı sonuçlar ve sonraki iş sırası düzeltilmeli.**
Genel CAD derleyicisi, deney aracı, model adayları ve geçmiş koşular gerçek ilerlemedir.
Fakat ilk ölçüm dilimi bütün kabul koşullarıyla kapanmamıştır. Modelin genel çizimden plan
üretimi henüz uygulamaya bağlanmamıştır; başarısızlıklar doğrudan model kapasitesine yazılamaz.

## Ne korunmuş, ne eksik?

- Altı eski `out/model-baseline/*/run.json` okunuyor; rapor tablo kontrolü geçiyor.
- `eval/check_tables.py`: 20 satır, 0 uyumsuzluk. Bu kontroller veri tutarlılığıdır;
  ölçüm yönteminin doğru olduğunu tek başlarına kanıtlamazlar.
- Kesilen `offering` kaydı yalnız 61 bayt: bir raster kaynağın atlandığı yazıyor. Yeni
  teşhis tamamlanmamış. Önceki model/CAD sonuçlarının kaybolduğu görülmedi.
- `out/` Git dışıdır; hard stop veya dosya kaybına karşı koruma değildir. Bu turun
  küçük kanıt kaydı `eval/reports/audit-evidence.json` olarak proje raporlarına alındı.
- Pilot/saklı kümeler boş. VLM/LoRA eğitimi yapılmadı; küçük aday sınıflandırıcısı için
  lojistik regresyon deneyi yapılmıştı. Bunlar farklı eğitim kapsamlarıdır.

## Bulunan ve bu turda onarılan kusurlar

| Bulgu | Etki | Uygulanan düzeltme |
|---|---|---|
| İstem `source` istemiyor, gramer zorunlu tutuyor; `questions` istiyor, gramer yasaklıyor | Deney arayüzü kendi içinde çelişkili | Ayrı `GeneralPlan reply v2` yanıt şeması; kalıcı planın kaynak zorunluluğu korundu |
| Gerçek ilişki JSON'undaki `verified_against` referans dosyası yoluyla isteme giriyor | Dosya adı ipucu sızıyor; referans geometrisi yüklenmiyor ama deney sözleşmesi bozuluyor | Yalnız gözlem/ilişki alanları isteme alınır; gerçek fixture ile regresyon testi eklendi |
| Swap ayrıştırıcısı `used` yerine ilk M değerini (`total`) alıyor | Kullanılan bellek iddiası yanlış | Alan adına göre ayrıştırma; sıfır, eksik ve farklı birimler sınandı |
| M1 sayfaları sabit 4096 bayt sayılıyor; cihaz 16384 bildiriyor | Boş/sıkıştırılmış bellek hesabı yanlış | Sayfa boyutu sistem çıktısından okunur; MiB ve ham çıktılar kaydedilir |
| Koşu özeti yalnız bütün işler bittikten sonra yazılıyor | Kesilmede tamamlanan sonuçların özeti kaybolabilir | Başlangıç ve her biten vaka/koşulda atomik ara kayıt, etkin adım ve koşu durumu |
| Aynı etiket tekrar kullanılabiliyor; bozuk JSON raporda sessiz atlanıyor | Önceki veri ezilebilir veya başarısız koşu görünmez olabilir | Eski klasöre yazmayı reddetme; bozuk kayıt için açık hata |

Ek olarak kaynak kod, manifest ve çizim dosyalarının SHA256 özetleri yeni koşulara
eklendi. Bellek örnekleme model yükleme başlangıcını da kapsar. Eski ham sonuçlar
değiştirilmedi; hatalı bellek alanları raporda geçersiz işaretlendi.

## Hâlâ kanıtlanmamış yorumlar

- Mevcut 7/7, 11/11 gibi sayılar değer kümesi kapsamıdır; ölçü örneği, konum, sembol ve
  geometri bağının doğruluğu değildir. Yanlış yerde okunan aynı rakam kapsamı artırabilir.
- Az rakam okunması, rakamların hiç aday yapılmadığını göstermez. `offering.py` örtüşen
  yanlış değeri de `okundu` sayar; ok başı koruması ve son filtreleri ayrı izlemez.
  Araç onarılmadan baskın kayıp adımı veya hedef eğitim görevi kesinleştirilemez.
- `relations` modele yalnız metin ilişkileri verir; görüntü vermez. `chain` kurallı
  önerici yoludur. Bu deneyler genel modelle uçtan uca PDF → STEP ölçümü değildir.
- Tek plakanın eski, çelişkili arayüzdeki başarısızlığı modellerin genel kapasitesini
  ölçmez. Önce yeni istem/şema ile canlı deney gerekir; bu turda canlı model çalıştırılmadı.
- Bir değerin var olan span id'sine atıf vermesi, değerin/birimin kaynağa uygun olduğunu
  kanıtlamaz. Kaynak uygunluğu ve tam çizim/katı doğrulaması sonraki işte genişletilmeli.

## Bu turda çalıştırılan kontroller

- Son kodla odaklı testler: **32 geçti** (planlayıcı, kaynak ölçümü, ara kayıt ve rapor).
- Son kodla tam paket: **269 geçti**, yalnız yerel HTTP sunucusu testi sandbox soket
  izninde durdu. Aynı test izinli ortamda ayrıca koşuldu: **1 geçti**. Böylece 270 testin
  tamamı doğrulandı; tam paket tek sandbox koşusunda yeşil olarak sunulmuyor.
- Kaynak ölçümü v2 ile model dışı `verified_plan` koşusu: **2/2 `draft`**, plan kontrolleri
  geçti. Braket hacmi **22084.3806 mm³**, mil hacmi **13544.7373 mm³**; toplam **6.72 sn**.
  Bu, model başarısı veya otomatik çizim doğrulaması değildir.
- Yeni kaynak kaydı M1 sayfa boyutunu doğru okuyor. Sandbox swap/ps erişimi vermediği
  için ilgili alanlar `null`; yokluk sıfır kullanım sayılmadı. Gerçek model yükünde
  kaynak kabulü hâlâ açıktır.
- Güncellenmiş `baseline_report --check` ve `check_tables` geçiyor. `git diff --check`
  temiz. Otomatik kesilme testinde ilk sonuç diske yazıldı, ikinci koşulda Ctrl-C üretildi;
  son kayıt `interrupted` ve ilk sonuç korunmuş olarak bulundu. Aynı etiket reddedildi.

Tam paket günlüğü: `out/audit-2026-09-27-tests.txt`. CAD/ham kaynak kanıtı:
`eval/reports/audit-evidence.json`. Başka bilgisayara taşırken gereken büyük `out/`
artefaktları ayrıca alınmalı; dosya özetleri dosyaların yerini tutmaz.

## Devam görevi

PLAN Bölüm 19'daki tek teslimle başla: düzeltilmiş yanıt sözleşmesini aynı ilişki kanıtıyla
yerel 3B modelde ölç. Sonuç ve kaynak bütçesi uygunsa ikinci modeli karşılaştır. Bu ölçüm
sonrası gerçek çizim kanıtını planlayıcıya bağlayan `chain_model` yolu ve CLI teslimi yap.
Raster teşhisini ayrıca konum+değer, bire bir eşleştirme ve aşama kayıtlarıyla onar.
Yeni eğitim kararı bu ölçümlere ve ayrı doğrulama verisine dayanmalı.

Hermes'e devam mesajı:

```text
PLAN.md Bölüm 19 ve eval/reports/progress-audit.md dosyasını oku. İlk teslim olarak düzeltilmiş general-plan-v2 / GeneralPlan reply v2 sözleşmesini aynı plaka ilişki kanıtıyla yerel modelde kontrollü ölç. Yeni etiketle ham yanıtı, şema/CAD sonucunu ve v2 kaynak ölçümünü kaydet. Eski arayüzün sonuçlarını yeni model başarısı sayma. Sonuçtan sonra gerçek çizim kanıtıyla chain_model yoluna geç. Mevcut değişiklikleri koru; offering ölçümünü onarmadan uzun aday/eşik denemelerine dönme. HANDOFF.md'yi çalıştırılmış kanıtlarla güncelle.
```
