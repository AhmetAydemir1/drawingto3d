# Basılı parametre kataloğu — 2026-09-27

## Sonuç

Kaynak sayı/ad/birim uygulamada kuruluyor; model bu değerleri yeniden yazmıyor.
İki yerel ölçümde katalog **22/22** değer ve kaynak bağını aynen korudu. İki model cevabı
da **geçersiz**: mevcut parametre adını türetme adı olarak yeniden kullanıyorlar.
Bu sonuç, kaynak sözleşmesinin korunmasıdır; ölçü anlamı veya PDF → STEP başarısı değildir.

| Görülmüş geliştirme parçası | Katalog | Seçilen | Model süresi | Sonuç |
|---|---:|---:|---:|---|
| plate-pocket-1 | 7 ölçü + 1 adet | 2 | 19.01 sn | Ad çakışması; boyutsuz oranı mm sayma |
| plastic-enclosure-1 | 14 ölçü | 2 | 12.44 sn | `arc_spacing_y` adını yeniden türetme |

Plaka cevabındaki iki açıklama yalnız ankraj türü/eksenini tekrar ediyor. Model zaten
80 mm verilen aralığı yeniden soruyor; diğer gerekli ölçüleri seçmiyor. Plastik gövdede
yarıçapı bir daireye bağlama iddiası bağımsız olarak doğrulanmadı. Mevcut 18 mm aralık
için ilgisiz oran öneriyor ve katalogda yazan adını soruyor. Yorum doğruluğu açık kalıyor.

## Uygulama

- `src/drawingto3d/catalog.py`: ad/değer/birim/kaynak ve adet ayrımı; sınırlı seçim şeması;
  kaynaklı türetme, ad çakışması/döngü ve boyut denetimi. Sayısal uzunluk varsayımı yok.
- `SpanMeaning.printed_value` kaynaktaki sayıyı korur. `printed_mm` geometri için kalır.
  Önceden 2.345 in → 59.56 sayısı, `in` etiketiyle aktarılabiliyordu; artık 2.345 in kalır.
- Ortak atıf kontrolü parametrenin birimini denetler. `4 × Ø6.8` içindeki 4, yalnız
  `count` parametresini destekler; 4 mm diye kabul edilmez.
- Durumlar `invalid`, `needs_input`, `needs_review`, `unavailable`; otomatik anlam/kabul yok.
  Kalıcı `GeneralPlan v1` değişmedi. Katalog henüz eski `model-plan` yolunun yerini almadı.
- `eval/catalog_parameters.py`: her çağrı öncesi tam istek, tamamlanan her cevap sonrası
  atomik kayıt; çıktı etiketi ezilmez. Kesilmiş koşu tamamlanmış görünmez.

## Deney ve kanıt

`qwen2.5vl:3b`, sıcaklık 0, bağlam 16384, çıktı 4096, çağrı zaman aşımı 180 sn.
`printed-parameter-catalog-v1` / `catalog-selection-v1` / `CatalogSelection v1`.
Toplam koşu 36.359 sn; iki durum da tamamlandı. Model yükleme/boşaltma bu kayıtla yapıldı.

- Ham koşu: `out/catalog-parameters/catalog-3b-01/`.
- Git ile taşınabilir tam kanıt: `catalog-parameter-evidence.json` (aynı klasör).
  İstek/şema/model özeti, kaynak dosya özetleri, cevaplar, kaynak/birim karşılaştırması ve
  tekrar doğrulama burada. İki cevap aynı hatalarla yeniden reddedildi.
- Kaynak ölçeri v2: kullanılan sistem swapı 6675.06 → 9895.44 MiB; tepe 9935.44 MiB.
  Ollama RSS tepesi 3822.9 MiB. Bunlar tüm sistemin swapı ve süreç RSS'idir;
  tek başına modelin toplam birleşik bellek kullanımı değildir.
- Eğitim, ağırlık indirme, referans STEP'i modele verme veya genel STEP üretimi yapılmadı.

## Kontroller ve sonraki adım

İlk dilimde ilgili 108 test geçti (75.87 sn); tam takım **394 test** geçti (226.70 sn).
22/22 kaynak karşılaştırması, istek özetleri ve iki ham cevabın yeniden doğrulaması geçti.

Önce bu deterministik katalog ürün komutundan incelenebilir olsun. Okuma eksik geometri
veya ölçek yüzünden durunca sayısal metinleri de kaybetmemeli. Anlam önerilerini basılı
katalogdan ayrı ve inceleme gereğiyle göster. Sonra türetmeyi yalnız ihtiyaç olan somut
bir boyut için ayrı iste; katalogdaki bilinen nicelikleri yeniden türettiren geniş isteği
tekrarlama. Geometri bağları doğrulanmadan uzun profil/STEP çağrısına geçme.

## Ürüne bağlanan ikinci dilim

`drawingto3d catalog <çizim> <yeni_klasör>` yerel model gerektirmeden `catalog.json`,
`evidence.json` ve `review.md` üretir. Eski dosyaların üzerine yazmaz. Ölçek veya kapalı
kontur bulunamasa da sayısal kaynak kayıtları korunur; geometri reddi ayrı kalır.

- Gerçek plastik PDF: 14 kayıt, `needs_review`, dört otomatik geometri eşleşmesi.
- Gerçek raster flanş: 18 kayıt, `needs_input`; ölçek çözülemedi. Bu 18 adayın doğru
  okunmuş ölçü olduğu doğrulanmadı; katalog koruması OCR doğruluk artışı değildir.
- Taşınabilir örnekler: `catalog-review-evidence.json`; yerel incelemeler
  `out/catalog-review/plastic-01/` ve `out/catalog-review/raster-01/`.
- İkinci dilimde etkilenen öneri/zincir/CLI testleri **29 geçti** (83.78 sn).
  Son CLI yönlendirmesi ve kesinti kaydı kontrolü **6 geçti** (0.53 sn; önceki grupla örtüşür).
  İkinci vaka sırasında kesinti testi ilk cevabı ve ikinci tam isteği korudu; aynı etiket
  reddedildi. İkinci dilimden sonra tam takım tekrar çalıştırılmadı.
- Baseline raporu, 20 değerlendirme satırı ve profil kanıtı kontrolleri geçti;
  `git diff --check` temiz; `general.py` farkı boş.

### Güncel sonraki karar

Katalog ürün komutuna bağlandı; yukarıdaki bağlama önerisi tamamlandı. Sırada serbest
anlam cümlesi ve gereksiz türetme yerine tek ölçü için kanıta bağlı yorum var. Önce model
cevabının geometri türü/ekseni/kaynak uyuşmasını ölçen küçük bağımsız değerlendirme kur;
ilk deneyde sayısal türetme isteme. Katalog, belirsiz okumalar ve model önerisi ayrı kalsın.
Yeni bir model/uzun profil koşusu bu kanıtı sağlamadan anlam başarısı sayılmaz.
