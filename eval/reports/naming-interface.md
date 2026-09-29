# CAD adları model arayüzünde — PLAN Bölüm 20 ölçümü (2026-09-27)

> Sonraki denetim düzeltmesi: güncel karar PLAN §21 ve `step-validation-audit.md` içindedir.
> Buradaki “profil adımı sırada” kararı ertelendi: ilk parametre cevabı yanlış atıflarla
> aktarılıyordu. `names-3b-05` gerçek çizim koşulu tek çağrıydı. Aşağıdaki ham ölçümler korunur.

Bu rapor Bölüm 20'nin sınırlı teslimini kapatır: ad kuralı model arayüzüne taşındı, sağlayıcının
bu kısıtı gerçekten uygulayıp uygulamadığı küçük bir sondada ölçüldü, aynı plaka aynı 3B model ve
aynı 16384/4096 ayarıyla dört kez koşuldu. Ham yanıtlar, ayarlar ve parmak izleri
`names-v4-evidence.json` (koşular) ve `name-probe-evidence.json` (sonda) içindedir.

## Ne değişti

- `src/drawingto3d/planner.py`: `PROMPT_VERSION` `general-plan-v2` → `general-plan-v3`; yeni
  `_RULE_CAD_NAMES` kuralı tek çağrı ve üç adımlı istemin ikisine de girdi.
- Yanıt şeması (`GeneralPlan reply v4`): `parameters` ve `sketches` nesnelerine `propertyNames`,
  işlem alanlarına (`sketch`, `input`, `target`, `tool`, `inputs.items`) ve `result` alanına
  `pattern` eklendi. Kalıcı `GeneralPlan v1`, `compile_general` ve CAD doğrulaması değişmedi.
- `NAME_ADAPTER = "lossless-identifier-rewrite"`: kısıtlanamayan adlar *onarılmaz*, bire bir
  eşlenir ve eşleme `renames` alanına yazılır. Varsayılan **kapalı** (`normalize_names=False`);
  kapalıyken illegal adlı yanıt reddedilir. Koşu kaydı ayarı `run.name_normalization` alanında tutar.
- `span_ids` gerçek kaynak kimliğini (`pdf-0`) korur; kaynak kimliği artık CAD adı değildir.

## Sağlayıcı sondası: hangi kısıt gerçekten uygulanıyor

`eval/name_probe.py`, `qwen2.5vl:3b`, 4096 bağlam, sıcaklık 0, 200 token. Sorulan ad her koşulda
kasıtlı olarak illegal: `Hole_Spacing-X` (`string-field` sürümünde `Hole_Spacing-1`).

| sonda | kısıt | kontrol | kısıtlı | okuma |
| --- | --- | --- | --- | --- |
| `string-field` | dize alanında `pattern` (`result`) | `Hole_Spacing-1` | `hole_spacing_x` | **uygulanıyor** |
| `property-names` | nesnede `propertyNames.pattern` | `Hole_Spacing-X` | `Hole_Spacing-X` | **uygulanmıyor** |
| `property-names-enum` | kapalı anahtar sözlüğü (`properties` + `additionalProperties: false`) | `Hole_Spacing-X` | `hole_spacing_x` | anahtar tutuldu, **değer bozuldu** (`100` → `"testing"`) |
| `pattern-properties` | nesnede `patternProperties` + `additionalProperties: false` | `Hole_Spacing-X` | `{}` | her anahtar reddedildi, gövde boş döndü |

Bu örnekte dize desenine uyuldu, `propertyNames` ile istenen anahtar kısıtı uygulanmadı.
Ancak açık anahtarları kısıtlamanın imkânsız olduğu veya adaptörün tek çözüm olduğu
kanıtlanmadı. `patternProperties` şeması boş nesneye izin veriyordu; kapalı sözlükteki
serbest dize şeması da `100` değerini zorunlu tutmuyordu. Bunlar sonraki arayüz seçimi
için sınırlı bulgulardır. Adaptör bu turda kapalıydı.

## Gerçek plaka koşuları

Aynı vaka (`plate-pocket-1`), aynı kanıt, `qwen2.5vl:3b`, `num_ctx 16384`, `num_predict 4096`,
sıcaklık 0, görüntü gönderilmedi. Dördü de aynı istem sürümünü (`general-plan-v3`) ve aynı yanıt
şeması sürümünü kaydeder.

| koşu | arabirim | koşul | sn | sonuç | ilk hata / olay |
| --- | --- | --- | --- | --- | --- |
| `names-3b-02` | json-schema | relations | 180.0 | `failed` | istemci zaman aşımı: yanıt gelmedi |
| `names-3b-02` | json-schema | chain_model | 40.9 | `failed` | `şema hatası: ifade ayrıştırılamadı: '/hole_spacing_x'` |
| `names-3b-03` | json-schema | relations | 180.0 | `failed` | aynı zaman aşımı, tekrar |
| `names-3b-04` | json-schema, `timeout 400` | relations | 182.3 | `failed` | `done_reason=length`, `eval_count=4096`, 8 648 bayt: **döngü** |
| `names-3b-05` | üç adımlı | relations | 193.3 | `failed` | `adım profile: yanıtta JSON nesnesi yok (çıktı sınırında kesildi)` |
| `names-3b-05` | üç adımlı | chain_model | 40.8 | `failed` | tek çağrı yolu: `'/hole_spacing_x'`, 02 ile birebir aynı yanıt |

Okunanlar:

1. **Ad kuralı işe yaradı, ama tek başına yetmiyor.** Adlar artık geçerli
   (`hole_spacing_x`, `g9_circle_centre`); `pdf-0`/`hole_spacing_X` sınıfı hata kayboldu. Buna
   karşılık ilk hata yer değiştirdi: model `radius` alanına `"/hole_spacing_x"` yazıyor —
   ayrıştırılamayan ifade. Yani "ilk hatanın adı değişti" tuzağına düşmeden söylenebilecek şey
   şudur: adım artık geçerli bir *sözdizimi* hatası, geometri değil.
2. **Sonraki uzun koşuda tekrar gözlendi; eski zaman aşımlarının ham cevabı yok.** `names-3b-04` aynı istemi
   400 sn bütçeyle ölçtü: yanıt 182.3 sn'de **4 096 token sınırında** kesildi ve içeriği
   kendini tekrar eden bir gövde. Bu sonraki koşu çıktı bütçesini doldurdu; önceki iki zaman aşımının aynı biçimde
   gerçekleştiği ham cevap olmadan kesinleştirilemez. 8 648 baytın 663 tekrarı
   `radius_exprs_1d_array_2d_array_…` biçimindedir.
3. **Üç adımlı yol hatayı sonraki adıma taşıdı ve o adı söyledi.** `parameters` adımı 14.8 sn'de
   bitti (742 bayt, geçerli biçim); `profile` adımı 178.5 sn'de 4 096 tokenı doldurdu
   (7 743 bayt). Yani bir çağrıda kapanmayan gövde, bölündüğünde de kapanmıyor — ama artık
   hangi adımın kapanmadığı ölçülü: **profil adımı**.
4. **Kayıpsız adaptör bu vakada no-op.** `names-3b-05` tek çağrı yolunda `names-3b-02` ile
   birebir aynı yanıtı verdi (sıcaklık 0, sabit istem) ve iki koşuda da adlar geçerliydi;
   adaptör kapalıydı. Adaptörün gerekeceği durum sondadaki `property-names` satırıdır: sağlayıcı
   anahtarı kısıtlamadığında. Bu yüzden adaptör ayrı bir deney olarak duruyor, ürün yolunda
   varsayılan değil.
5. **Kaynak durumu ölçüldü, gizlenmedi.** Bu koşular sırasında sistem değişimi 11.0/12.3 GB,
   en düşük boş sayfa 29–55 MB, Ollama RSS tepesi ~5.0 GB. `relations` isteminin ilk çağrısı
   soğuk yüklemeden sonra 180 sn'yi aştı; aynı koşulun ikinci çağrısı (`names-3b-05`,
   `parameters`) 14.8 sn sürdü. Kaynak durumu `resources` bloğundadır; farklı boyuttaki görevlerin bu süreleri,
   bellek baskısının gecikmeye etkisini tek başına ayırmaz.
6. `chain_model` tek çağrı yolunu kullandığı için `--split` o koşulda hiçbir şeyi değiştirmedi;
   iki koşuda aynı 708 tokenlık, 40.8 sn'lik yanıt çıktı. Bu, sıcaklık 0'da ölçümün
   tekrarlanabilir olduğunun da kanıtıdır.

## O turdaki karar — sonraki denetimde ertelendi

İlk kalan hata türü **ifade sözdizimi** (`'/hole_spacing_x'`), onu **profil adımının
kapanmaması** izliyor. Sıradaki tek değişiklik ad kuralını ya da şemayı değil, profil adımının
kendisini hedefleme önerisi verilmişti. Sonraki denetim ilk parametre cevabındaki
atıf hatasını gösterdi; aşağıdaki öneriler güncel görev değildir:

- profil adımını eskiz başına bir çağrıya bölmek (kapalı profillerin sayısı kanıttan biliniyor),
  ya da
- profil adımının çıktısını adım bazında sınırlayıp kesilmeyi başarısızlık olarak kaydetmek ve
  tek eskiz + tek ifade kalıbı isteyen daha küçük bir soru sormak.

Geçerli plan ve STEP yok. Güncel teslim, iki parça grubunda yalnız kanıttan parametre
seçimini ölçmektir (PLAN §21); tam CAD kontrolü geçerli plan gerektirir.

## Doğrulama

- `pytest`: **326 test geçti (215.50 sn)**, tam paket bu değişikliklerle yeşil.
- `eval/name_probe.py` canlı sonda: 8/8 satır, yukarıdaki tablo.
- `eval/baseline_report.py --check`: koşu tabloları `out/model-baseline/*/run.json` ile tutarlı.
- `eval/check_tables.py`: README tabloları `out/frontend` ile tutarlı.
