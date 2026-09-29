# Model sözleşmesi denetimi ve bir düzeltme turu — 2026-09-27

## Karar

İlerleme var: gerçek çizimin okuma zinciri modele bağlanmış (`chain_model` ve `model-plan`),
model yanıtları ve kaynak kullanımı kaydediliyor. Ancak son devir notundaki “ayrık
birleşimler çalışmıyor, kalıcı CAD şemasını değiştirelim” teşhisi kanıtlanmamıştı.
Eksik kısıtların model yanıt şemasına aktarılması bu turda ölçülerek düzeltildi.
Kalıcı `GeneralPlan v1`, doğrulayıcı ve CAD derleyicisi değiştirilmedi.

**Model planından geçerli STEP hâlâ yok.** Alan sözleşmesindeki ilerleme, doğru parçanın
üretildiği anlamına gelmiyor. Yeni yanıtlarda adlandırma yanında işlem ve ifade hataları da var.

## Başlangıç ve korunan kayıtlar

Başlangıç HEAD: `96e0118`; çalışma ağacında önceki oturumların commit edilmemiş değişiklikleri
vardı. Bunlar korundu. Başlangıç farkı `out/schema-audit/before.patch`, eski tam/adım yanıt
şemaları `out/schema-audit/schema-v2.json` olarak kaydedildi. `out/` Git dışıdır; bu turdaki
iki deneyin ham yanıtları, ayarları ve kaynak örnekleri ayrıca proje raporlarına kopyalandı:

- `schema-v3-probe-evidence.json`: eski/yeni şemalar, altı istek/yanıt ve alan doğrulaması.
- `schema-v3-live-evidence.json`: gerçek plaka koşusu, iki tam aday, istem karşılaştırması.

Önceki kesik koşular bitmiş sayılmadı; çalışan bir koşunun klasörü taşınmadı. Yeni etiketler
kullanıldı. Mevcut Hermes süreci değiştirilmedi; yönlendirme ortak PLAN/HANDOFF dosyalarındadır.

## Hatanın kaynağı

`Parameter` içindeki `value`/`expr` seçimi bir Python `model_validator` kuralıydı.
Pydantic'in ürettiği eski JSON Schema bu seçimi taşımıyordu: iki alan da isteğe bağlıydı,
`oneOf` hiç yoktu. `type` ve `op` etiketleri de Python'da varsayılan taşıdığından JSON
Schema'nın `required` listesine girmiyordu; birleşim doğrulayıcısı ise açık etiket bekliyor.
`RepeatOp` için doğrusal/dairesel seçim kuralı da yalnız Python doğrulayıcısındaydı.

Bu nedenle eski küçük sondaların sonucu, sağlayıcının `oneOf` uygulamadığını göstermez.
Önce gerçekten gönderilen şemanın istenen kuralı içerdiği doğrulanmalıdır.

## Uygulanan değişiklik

`planner.plan_reply_schema()` artık `GeneralPlan reply v3` üretir:

- Eskiz/işlem tür etiketleri zorunlu.
- Parametreler kaynağa göre dört kapalı seçenek: tek `value` veya `expr`, basılı ölçüde
  en az bir kaynak kimliği, varsayım/kullanıcı değerinde açıklama, türetilmiş ifadede uygun birim.
- Tekrar işlemi doğrusal/dairesel seçeneklerinden yalnız birini taşır.
- Üç adımlı arayüz aynı kuralları kullanır; adım kökündeki ek alanlar reddedilir.
- Kayıtlara `schema_sha256` eklenir. `general-plan-v2` istemi değişmedi.

Şema üretimi yanıtları sonradan düzeltmez, ölçü veya geometri eklemez. Son karar yine
kalıcı plan, kaynak ve CAD kontrollerindedir.

## Kontrollü küçük deney

Yerel `qwen2.5vl:3b`, sıcaklık 0, bağlam 8192, çıktı 700; her çiftte aynı istek.
İstekler özellikle yasak alan birleşimini veya eksik etiketi talep ederek grameri sınar.

| Alt görev | Eski v2 | Yeni v3 | v2 / v3 saniye |
|---|---|---|---|
| Parametre: `value` ve `expr` birlikte | Geçersiz | Alan kontrolü geçti | 8.73 / 4.03 |
| Profil: `type` etiketsiz daire | Geçersiz | Alan kontrolü geçti | 5.05 / 5.22 |
| Tekrar: iki mod ve eksik `op` | Geçersiz | Alan kontrolü geçti | 4.04 / 6.96 |

**0/3 → 3/3**, yalnız `Parameter`, `Sketch`, `Operation` alan sözleşmeleri için.
Sonda bütün planı kontrol etmiyor: yeni profil yanıtında fazladan uygunsuz adlı eskiz,
tekrar yanıtında çakışan gövde adları var. Bunlar geometri başarısı olarak sayılmadı.
Bu dar deney tüm JSON Schema özelliklerinin sağlayıcıda desteklendiğini kanıtlamaz.

Tekrarlama (mevcut dosyaları ezmemek için yeni çıktı adı):

```sh
PYTHONPATH=src .venv/bin/python eval/schema_probe.py --before eval/reports/schema-v3-probe-evidence.json --out out/schema-audit/probe-repeat-01.json
```

## Gerçek plaka: `schema-v3-3b-01`

Aynı yerel 3B model, 16384 bağlam, 4096 çıktı, sıcaklık 0. `relations` elle doğrulanmış
metin kanıtı; `chain_model` çizimin gerçek okuma zincirinden gelen metin kanıtıdır.
Görüntü gönderilmedi. Önceki `chain-model-3b-05` koşusuyla iki istemin SHA-256 değerleri
bire bir aynı; değişen deney girdisi yanıt şemasıdır.

| Koşul | Toplam / model sn | İlk tam plan hatası | Parametre / eskiz / işlem alan kontrolleri |
|---|---|---|---|
| `relations` | 51.49 / 51.47 | Geçersiz ad `hole_spacing_X` | 3 / 5 / 5 geçti |
| `chain_model` | 83.90 / 82.21 | Geçersiz ad `pdf-0` | 7 / 6 / 6 geçti |

İki aday da `invalid`, iki koşul da `failed (planning)`; **STEP üretilmedi**.
Etiket ve değer/ifade çakışmaları bu yanıtlarda görülmedi. İlk hata artık adlandırma:
kalıcı sözleşme `^[a-z][a-z0-9_]*$` ister, model arayüzü sözlük anahtarlarında bunu kodlamıyor.

Adları düzeltmek tek başına yeterli olmayacak. Ham `relations` yanıtı hiç gövde oluşturmadan
beş `cut` işlemi ve üretilmemiş `result=part` veriyor. `chain_model` yanıtındaki `/0.0/90`
geçerli bir aritmetik ifade değil; `result=finished_part` da üretilmemiş. Bu gözlemler
ham yanıttan gelir; ilk doğrulama hatasından sonraki aşamaların geçtiği iddia edilmez.

Koşu 140.07 sn'de tamamlandı. Kaynak ölçümü v2: kullanılan sistem swapı 9678.31→10306.75 MiB,
artış 628.4 MiB, tepe 10349.38 MiB; boş sayfa en az 50.453 MiB; Ollama RSS tepe 5016.1 MiB.
Sistem değerleri diğer uygulamaları içerir; RSS toplam GPU/birleşik bellek değildir.
Bu nedenle küçük deneyi büyüterek sürdürmek yerine sonucu kaydedip model boşaltıldı.

## Doğrulama

Odaklı testler: `tests/test_plan_reply_schema.py` ve `tests/test_planner.py`: **42 geçti**.
Tam paket: **300 geçti, 217.24 sn** (`out/schema-audit/pytest.txt`).
`eval/baseline_report.py --write` sonrası `--check` geçti; `eval/check_tables.py`
20 satırda 0 uyuşmazlık buldu. `git diff --check` temiz; `general.py` için fark yok.

## Devam görevi

PLAN Bölüm 20 geçerlidir. İlk küçük deney adlandırma kuralını model arayüzüne taşımalı;
kaynak kimlikleri (`pdf-0`) ile CAD değişken adları ayrılmalı, kaynak kimliği korunmalı.
Sağlayıcı sözlük anahtarı kısıtını uygulamıyorsa kayıpsız bir model yanıt adaptörü
ayrı deney olarak sınanabilir; kalıcı CAD sözleşmesini gevşetmek gerekmez.

Ardından aynı iki koşul tek kez ölçülüp ilk semantik hata kaydedilsin: tanımsız gövde,
ifade, profil kapanışı veya kaynak uyuşmazlığı. Üç adımlı yol kullanılacaksa alt yanıtı
sırf anahtarları var diye “accepted” sayma; ilgili alanları ve o anda bilinen başvuruları
sonraki çağrıdan önce doğrula. Sonsuz şema/istem denemesi yerine ölçülen hataya bağlı
tek değişiklik yap. Geçerli plan çıkarsa CAD ve çizim denetiminden sonra farklı parça grubunda sına.

Raster `offering.py` onarımı, tam kontur/görünüş kanıtı, bağımsız veri ayrımı ve ağ kapalı
ürün kabulü açık. Eğitim kararı, arayüz hatalarından ayrılmış tekrarlanan görev hatası ve
ayrı doğrulama verisiyle alınmalı. Bu tur eğitim yapmadı ve ürünün tamamlandığını göstermedi.
