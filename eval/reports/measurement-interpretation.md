# Tek ölçü yorum arayüzü — sözleşme tuttu, yorum zayıf — 2026-09-27

Rapor PLAN.md Bölüm 22'nin devam kaydıdır. Ham koşu: `out/meaning-interpretation/meaning-3b-01/`
(22 istek + 22 cevap, istek model çağrısından **önce** diske yazıldı). Git ile taşınabilir kanıt:
`eval/reports/meaning-interpretation-evidence.json` (`--check` ile yeniden yargılanabilir).

## Sonuç

| Soru | Ölçüm |
|---|---|
| Arayüz sözleşmesi tutuyor mu? | **Evet.** 22/22 cevap yalnız sunulan gerçek geometri kimliklerini kullandı; uydurulmuş kimlik yok, basılı değer/birim/adet hiç değişmedi, her cevapta kaynak kimliği geri yansıtıldı. |
| Yorum doğru mu? | **Hayır.** Bağımsız etiketin denetleyebildiği 15 alandan yalnız **1** tanesi puanlanabildi (7/8 cevap sözleşmede düştü); tam doğru ölçü **0**. |
| Belirsizlik soru olarak kaldı mı? | **Hayır.** 22 cevapta `unresolved` **hiç** seçilmedi; model bağdan emin olmadığında bile bir çift söyledi. |
| Plastik grupta doğruluk? | **Ölçülemedi.** O grupta bağımsız etiket yok; 13/14 cevap sözleşmeden geçti ama ayrım gücü yok: eksen 14/14 "horizontal", 14 ölçünün **7'si aynı çifti** (`g57`,`g60`) gösteriyor, okumanın kendi bağıyla uyuşan yalnız 3/14. |

**Bu bir STEP, profil veya genel çizim başarısı değildir.** Yalnız "tek ölçü → kaynak+geometri bağı"
arayüzünün sözleşmesi ve yerel 3B modelin bu sözleşmedeki davranışı ölçüldü.

## Arayüz

- `src/drawingto3d/interpret.py` (`single-measurement-interpretation-v1` / `MeasurementInterpretation v1`).
  Tek ölçü için alanlar: `span_id` (kaynak kimliği, geri yansıtılır), `kind` (distance/diameter/radius/
  angle/count/unclear), `axis` (horizontal/vertical/none), `between` (iki uç), `matched` (ölçtüğü/ saydığı
  geometri), `unresolved` + `question` (çözülemeyen bağ için), `reason`.
- Ayrılan kimlik uzayı: `between` ve `matched` şemada **sunulan kimliklerin enum'u**; şemada sayısal alan
  yok, fazladan alan yasak. Böylece "ölçü kimliğini ad sanma" ve "sayı türetme" sözleşmeyle engelleniyor.
- Sunulan kimlikler uydurulmuyor: okumanın kendi çapa/eşleşme kimlikleri + ölçülen daireler
  (`geometry_ids`). Plakada 11, plastikte daha geniş bir gerçek kimlik kümesi.
- Sözleşme denetimi (`judge_interpretation`): tür↔alan uyumu (distance/angle → iki uç, diameter/radius/
  count → eşleşen geometri, eksen yok), aynı kimliğin iki kez bağlanması, çözülemeyen bağda geometri veya
  tür iddiası, ve **gerekçe/soruda kimlik dışı sayı** yasağı. Ayrıca kendi kendine tutarlılık ölçüleri
  kaydediliyor: okumanın kendi bağını doğruladı mı, eksen sunulan noktalarla tutarlı mı.
- Referans etiket (`eval/relations/<parça>.json`) yalnız değerlendirmede: eşleşme **basılı değer+birim**
  ile kuruluyor, etiket kimlikleri okuma kimliklerine **en yakın konum** (2 mm tolerans) ile eşleniyor;
  eşlenmeyen uç varsa alan "ölçülemez" sayılıyor, uydurulmuyor.

## Ölçüm — plaka (bağımsız etiket var)

`qwen2.5vl:3b` fb90415cde1e · 16384 bağlam · 4096 çıktı · sıcaklık 0 · toplam 186,971 sn (plaka 71,04 sn,
plastik 115,584 sn).

| ölçü | basılı | etiket (form/eksen/bağ) | cevap | sınıf | sayı kuralı olmasaydı |
|---|---|---|---|---|---|
| pdf-0 | 100,00 | distance / horizontal / g9-g11 | g9-g11, horizontal | invalid (gerekçede sayı) | kind ✓ eksen ✓ **bağ ✗** |
| pdf-1 | 80,00 | distance / — / — (uçlar koordinatsız) | g4-g2, horizontal | invalid (gerekçede sayı) | kind ✓ |
| pdf-2 | 60,00 | distance / **vertical** / g9-g12 | g9-g12, horizontal | invalid (gerekçede sayı) | kind ✓ **eksen ✗** bağ ✓ |
| pdf-3 | 6,80 (4×) | diameter / — / g9,g10,g11,g12 | diameter ama `between` g9-g12, eksen horizontal | invalid (tür↔alan) | — |
| pdf-3 sayı | 4 | count / — / g9,g10,g11,g12 | diameter (adet değil) | invalid (tür↔alan) | — |
| pdf-4 | 50,00 | diameter / — / g8 (cep) | diameter, `matched` **g10,g11**, eksen horizontal | invalid (eksen) | bağ ✗ |
| pdf-5 | 15,00 | distance / — / — (uçlar koordinatsız) | g48-g9, horizontal | **correct** (yalnız tür denetlenebildi) | — |
| pdf-6 | 8,00 | distance / — / — (uçlar koordinatsız) | g48-g56, horizontal | invalid (gerekçede sayı) | kind ✓ |

Okunuşu: etiket 15 alanı denetleyebiliyordu; **7 cevap sözleşmede düştüğü için yalnız 1 alan puanlandı**.
Düşmelerin 5'i gerekçede sayı yazmaktan (model değeri tekrar ediyor: *"The measurement of 100.0 mm is
between…"*), 2'si çap/yarıçap cevabının şeklinden (iki uç verme, çapa eksen yazma). Ölçülebilir üç şey:
**tür** doğru (denetlenen 5 cevapta 5/5), **eksen** dikey olan tek ölçüde yanlış (pdf-2), **bağ** iki
denetlenebilir ölçüden birinde doğru (pdf-2 ✓, pdf-0 ✗), cep çapı (pdf-4) iki deliğe bağlanmış.

## Ölçüm — plastik gövde (bağımsız etiket yok)

14 ölçü, 13'ü sözleşmeden geçti, 115,584 sn. Etiket olmadığı için doğruluk ölçülemedi; ölçülen şey
ayrım gücü: **eksen 14/14 "horizontal"**, 8 farklı bağ, **7 ölçü aynı çifti** (`g57`,`g60`) gösteriyor,
okumanın kendi bağıyla uyuşan 3/14 (`pdf-0`, `pdf-3`, `pdf-7`), bir cevapta eksen sunulan noktalarla
tutarsız (`pdf-7`). `radius` (R8,00) cevabı `g8`'i eşleştirdi ama eksen yazdığı için düştü.

## Ölçülen arıza sınıfları

1. **Değeri tekrar etme:** 5/22 cevapta gerekçede sayı var; sözleşme bunu tüm cevabı düşürerek
   cezalandırıyor. Bağın kendisi bu yüzden ölçülemez hale geliyor (plakada 4 cevap).
2. **Çap/yarıçap şekli:** model çapı iki uç arasında ölçmeye veya çapa eksen yazmaya çalışıyor (3 cevap),
   ve 50,00 cep çapını iki deliğe bağlıyor.
3. **Eksen varsayılanı:** 22/22 cevapta "horizontal"; dikey ölçüde de. Eksen alanı okumadan değil,
   alışkanlıktan geliyor.
4. **Belirsizlik kaçışı kullanılmıyor:** `unresolved` 0/22; okuma bağıyla uyuşmayan 11 plastik cevabı
   bile soru sormak yerine çift söyledi.
5. **Ayrım gücü:** gövdede 7/14 ölçü aynı çift; sunulan kimlik kümesi geniş olduğunda model
   merkezî/olası bir çifte çöküyor.

## Ne kanıtlanmadı

- STEP üretimi, profil başarısı, genel (depo dışı) çizim başarısı ve model eğitimi: **hiçbiri**.
- Plastik gövdede doğruluk: bağımsız etiket olmadığı için ölçülmedi.
- Plakada tür/eksen/bağ: 15 denetlenebilir alandan yalnız 1'i puanlandı; üç alanın hiçbiri
  1/1 doğrulanmış sayılmaz.
- İki geliştirme parçası görülmüş durumda; pilot ve saklı grup hâlâ boş.

## Sıradaki tek karar

Bu turun ölçtüğü engel tek ve dar: **gerekçedeki sayı, bağın kendisini ölçülemez kılıyor.** İlk deneyde
sayısal türetme istenmedi (istenen buydu), ama cevabın tamamını düşürmek doğru mu?

1. **Sayı yasağını yalnız kendi alanlarına daraltmak** (önerilen): `reason`/`question` sayısız kalmalı ama
   sayı yüzünden *bağ* puanlanmadan atılmamalı — aynı plaka+plastik, yeni etiket (`meaning-3b-02`),
   tek değişken; bağ/eksen/tür sınıfları o zaman ölçülebilir.
2. **Aday kümesini daraltmak:** plastikte çöküşün nedeni geniş kimlik kümesi olabilir; okumanın kendi
   notlarında geçen alternatif çiftleri sunmak ayrım gücünü zorlar (ikinci değişken, ayrı tur).

Öneri: önce 1, sonra 2. Her ikisi de yalnız bu dar deneyi yeniler; profil/STEP çağrısına geçmek için
kanıt yok.

## İkinci koşu: sayı yasağının kapsamı daraltıldı — `meaning-3b-02`

Tek değişken: sözleşme sürümü `interpretation-contract-v1` → `v2`. Sayı yasağı **aynı istemde ve aynı
şemada** duruyor (istem baytları ve ham cevaplar 22/22 **birebir aynı**; sıcaklık 0), değişen tek şey
ihtarın cezası: kimlik dışı sayı artık cevabı düşürmüyor, `warnings` alanına yazılıyor ve bağ yine
puanlanıyor. Model yeniden örneklemedi — bu yüzden aşağıdaki fark **yalnızca ölçümün kendisinden**.

| | v1 (`meaning-3b-01`) | v2 (`meaning-3b-02`) |
|---|---|---|
| plaka sınıflar | 1 doğru, 7 geçersiz | **3 doğru, 2 kısmi, 3 geçersiz** |
| plakada puanlanan alan (15 denetlenebilir) | 1 | **9** |
| tür / eksen / bağ doğru | 1 / 0 / 0 | **5 / 1 / 1** |
| sayı içeren cevap | 5 (hepsi düştü) | 5 (hiçbiri düşmedi) |
| toplam süre | 186,971 sn | 158,244 sn (plaka 60,494; plastik 97,431) |

Kalan üç geçersiz cevap hep aynı sınıf: çap/yarıçap şekli (iki uç verme veya çapa eksen yazma) —
`pdf-3`, `pdf-3` adedi, `pdf-4`. Yeni ve keskin bulgu: **eksen kelimesi ile seçilen çift birbiriyle
tutarsız.** 100,00 ölçüsünde model "horizontal" diyor ama `g9-g12` (köşegen) çiftini seçiyor; 60,00
ölçüsünde doğru çifti (`g9-g12`) seçip "horizontal" diyor. Etiketin kendisi ikisinde de tutarlı
(sırasıyla `g9-g11` yatay, `g9-g12` dikey). Yani eksen alanı okumadan değil alışkanlıktan geliyor ve
seçilen çift onu yalanlıyor — çiftten eksen türetmek (kendi kendine denetim) sıradaki turun en ucuz
adayı olarak not edildi.

Plastik cevapları da birebir aynı olduğu için oradaki tablo değişmedi: etiket yok, eksen 14/14
"horizontal", 7 ölçü aynı çift, okuma bağıyla uyuşan 3/14, `unresolved` 0/22. STEP/profil başarısı
iddiası yine yok. Yeni kanıt: `eval/reports/meaning-interpretation-evidence-02.json`
(`--check`: 22 ölçü, 0 sorun; eski paket farklı yargı sözleşmesiyle üretildiği için durum
karşılaştırması atlanıyor, ham cevapları yine doğrulanıyor).

## Üçüncü koşu: eksen sormak yerine seçilen çiftten türetildi — `meaning-3b-03`

Tek değişken: `interpretation-contract-v3` — eksen alanı **sorulmuyor**, seçilen iki uçtan türetiliyor
(şemada `axis` yok, istemde "eksen bu iki kimlikten çıkar, yazma" satırı var). Bu kez değişiklik
istemde göründüğü için ham cevaplar da değişti (istem ve cevap 22/22 **farklı**; v1→v2'de ikisi de
birebir aynıydı) — yani bu tur bir yargıç değişikliği değil, sorunun kendisinin değişmesi.

| | v2 (`…-02`) | v3 (`…-03`) |
|---|---|---|
| plaka sınıflar | 3 doğru, 2 kısmi, 3 geçersiz | **4 doğru, 1 kısmi, 3 geçersiz** |
| alan doğruluğu (tür/eksen/bağ) | 5/5 · 1/2 · 1/2 | **5/5 · 1/2 · 1/2** |
| plastik en sık çift | 7× | **5×** (farklı bağ yine 8) |
| okuma bağıyla uyuşan (plastik) | 3/14 | 3/14 |
| toplam süre | 158,244 sn | 174,093 sn |

Okunuşu: **tutarsızlık kapandı, ama yeni anlayış gelmedi.** Tek sınıf değişen ölçü `60,00`: çifti zaten
doğruydu, artık eksen o çiftten okunduğu için o ölçü tam doğru sayıldı. Alan doğruluğu hiç değişmedi —
çünkü kayıp **çift seçiminde**: `100,00` hâlâ köşegen `g9-g12` çiftine bağlanıyor (türetilen eksen
"vertical", etiket "horizontal"), `50,00` cep çapı hâlâ iki deliğe (`g8`,`g9`) bağlanıyor, `6,80` hâlâ
iki uç olarak veriliyor. Eksen alanı kaldırılınca model plakada neredeyse hep dikey çiftlere gitti
(`g2-g4`, `g9-g12`, `g4-g9`, `g4-g2`) — yani eksen kelimesi sorulduğunda yazdığı "horizontal" ile
seçtiği çiftin çelişkisi, alan kaldırılınca çiftin tarafına düştü. Plastikte çöküş biraz gevşedi
(en sık çift 7× → 5×) ama okuma bağıyla uyuşma aynı kaldı (3/14) ve bir cevap yeni bir şekil hatasıyla
düştü (yarıçap, eşleşen geometri vermeden). `unresolved` yine **0/22**.

Kanıt: `eval/reports/meaning-interpretation-evidence-03.json` (`--check`: 22 ölçü, 0 sorun). Bu turda
denetimin kendi hatası da bulundu ve düzeltildi: aynı basılı çağrıdan iki ölçü (boyut + adet) üreten
kayıtta ölçüler yalnız kaynak kimliğiyle eşleştirildiği için karışıyordu; artık eşleşme
(kaynak kimliği, ad) çiftiyle yapılıyor ve bir test bunu koruyor.

## Dördüncü koşu: aday kümesi okumanın kendi ölçtüğü çiftlerle sınırlandı — `meaning-3b-04`

Tek değişken: `interpretation-contract-v4`. Sunulan `between` kimlikleri artık tüm pafta değil, okumanın
**kendi ölçtüğü çiftler**: önce kendi ankraj çifti, sonra claim `notes` içinde "aynı ölçüyü veren başka
aday çiftleri" olarak yazdığı alternatifler; yalnız iki ucu da ölçülmüş konum taşıyan çiftler sunuluyor
(eksen o noktalardan türetildiği için konumsuz uç puanlanamaz). İstem de bu menüyü yazıyor, yargıç ise
"seçilen çift adaylar arasında değil" diye reddediyor. İstem ve ham cevaplar 22/22 yine değişti.

| | v3 (`…-03`) | v4 (`…-04`) |
|---|---|---|
| plaka sınıflar | 4 doğru, 1 kısmi, 3 geçersiz | **5 doğru, 0 kısmi, 3 geçersiz** |
| alan doğruluğu (tür/eksen/bağ) | 5/5 · 1/2 · 1/2 | **5/5 · 2/2 · 2/2** |
| plastik en sık çift | 5× | 7× |
| okuma bağıyla uyuşan (plastik) | 3/14 | 3/14 |
| `unresolved` | 0/22 | 0/22 |
| toplam süre | 174,093 sn | 181,958 sn |

**Ne değişti:** dört aday çift sunulan iki ölçüde model okumanın kendi çiftini seçti — `100,00` artık
`g9-g11` (yatay delik aralığı), `60,00` yine `g9-g12`; ikisi de tam doğru. v2/v3'te `100,00` köşegene
(`g9-g12`) bağlanıyordu. Yani kayıp gerçekten **menüdeydi**: geniş kimlik kümesi verildiğinde model
varsayılana çöküyor, okumanın ölçtüğü dört aday verildiğinde doğru çifti buluyor.

**Ne değişmedi:** kalan üç geçersiz cevap hâlâ çap şekli — model çapı iki uç olarak veriyor (`pdf-3` iki
delik, `pdf-4` cep + bir delik `g8-g9`), istemde ve okumada `form: diameter` yazmasına rağmen. Plastikte
en sık çift 7×'e döndü (okuma bağıyla uyuşan yine 3/14) ve `unresolved` yine hiç kullanılmadı.

**Müdahalenin erişimi sınırlı ve bu ölçüldü:** okumanın notlarında adı geçen alternatiflerin çoğu hiçbir
claim'in ankrajı olmadığı için konum taşımıyor, dolayısıyla menüye giremiyor. Sonuç: daralma plakada
8 ölçünün **2'sinde** (dört adaylı olanlar), diğerlerinde tek adaya indi (onay/ret sorusu); plastikte
okumanın bağladığı 4 sayının hepsinde tek aday, kalan **10 ölçünün hiç okuma bağı yok**.

Kanıt: `eval/reports/meaning-interpretation-evidence-04.json` (`--check`: 22 ölçü, 0 sorun).

## Beşinci dilim: bağ, cevabın şekli reddedilse de puanlanıyor — kayıtlı cevaplar yeniden puanlandı

Tek değişken: **ölçüm kapsamı**, model sorusu ve sözleşme aynı. Artık sözleşme şekli reddettiğinde
(örneğin çap iki uç olarak verildiğinde) bağ, cevabın işaret ettiği geometri kümesi (`between` ∪
`matched`) olarak yine puanlanıyor; cevabın sınıfı "geçersiz" kalıyor ama ölçü "ölçülemedi" olmaktan
çıkıyor. Bu değişiklik modeli ilgilendirmediği için **yeni model koşusu yapılmadı**: dört koşunun
kayıtlı ham cevapları `--rescore` ile yeniden puanlandı (koşu kayıtları değiştirilmedi, `rescore.json`
yanlarına yazıldı).

**Sonuç: plakada ölçülemeyen alan kalmadı; kalan üç cevap ölçülü şekilde YANLIŞ.**

| kalan üç geçersiz cevap | işaret ettiği küme | etiket | sonuç |
|---|---|---|---|
| `pdf-3` (Ø6,80 4×) | `g9`,`g12` | `g9`,`g10`,`g11`,`g12` | **yanlış** — dört deliğin yarısı |
| `pdf-3` adedi (4) | `g9`,`g12` | `g9`,`g10`,`g11`,`g12` | **yanlış** |
| `pdf-4` (50,00 cep) | `g8`,`g9` | `g8` | **yanlış** — cebe fazladan bir delik |

Yani çap sorunu bir *şekil* sorunu değil, **anlama** sorunu: model çapı iki uç olarak yazmakla kalmıyor,
ölçtüğü kümeyi de karıştırıyor.

**Dört koşu artık tek ölçüm kuralıyla karşılaştırılabilir** (kayıtlı cevaplar, güncel kurallarla):

| koşu | plaka sınıflar | tür | eksen | bağ | sözleşme dışı bağ |
|---|---|---|---|---|---|
| `meaning-3b-01` | 1 doğru, 7 geçersiz | 1/1 | 0/0 | 0/0 | 1 doğru, 4 yanlış |
| `meaning-3b-02` | 3 doğru, 2 kısmi, 3 geçersiz | 5/5 | 0/2 | 1/2 | 0 doğru, 3 yanlış |
| `meaning-3b-03` | 4 doğru, 1 kısmi, 3 geçersiz | 5/5 | 1/2 | 1/2 | 0 doğru, 3 yanlış |
| `meaning-3b-04` | **5 doğru, 3 geçersiz** | 5/5 | **2/2** | **2/2** | 0 doğru, 3 yanlış |

Bu tablonun geriye dönük bulgusu: v1'in sayı cezası, doğru bağı olan bir cevabı da (`60,00` çifti,
yalnız eksen kelimesi yanlış) çöpe atmıştı — "1 doğru" satırı o. Bugünün kuralıyla o cevap
kısmi/doğru sayılırdı.

Plastik değişmedi: bağımsız etiket yok, okuma 14 sayının yalnız 4'ünü bağlamış; orada ölçülecek
doğruluk yok, ölçülen şey ayrım gücü (en sık çift 7×, okuma bağıyla uyuşan 3/14, `unresolved` 0/22).

## Altıncı koşu: okumanın önerisi incelemeye sunuldu, yarısına kusur enjekte edildi — `meaning-3b-05`

Tek değişken `reading-review-v1`: istem artık okumanın **kendi bağını** gösteriyor ve onu bir inceleme
isteği olarak sunuyor ("uyuyorsa aynısını yaz, uymuyorsa okuduğunu yaz"). Ölçülebilir olması için
ölçülerin yarısına, yalnız kaynak kimliğinden türeyen **deterministik bir kusur** enjekte ediliyor
(bir kimlik yanlış üyeyle değiştirilir, küme tek üyeye indirilir veya bir üye düşürülür); hangisinin
bozuk olduğu modele söylenmiyor. Doğruluk **yapı gereği** biliniyor: kopyalamak yanlış bağ demek.

| | plaka (8 ölçü) | plastik (14 ölçü) |
|---|---|---|
| sözleşme sınıfları | **7 doğru, 1 kısmi, 0 geçersiz** | etiket yok (14 `no_label`) |
| okuma bağıyla uyuşan | **8/8** | 3/14 |
| bozuk öneri | 6 | 4 |
| **kusuru yakalayan** | **6/6** | **4/4** |
| kusuru yakalayıp yine yanlış bağ kuran | 0 | 1 (yarıçap: `g76/g95`) |
| temiz öneri | 2 | 0 |
| yanlış alarm | **0** | **0** |
| okumanın hiç bağ kurmadığı / kullanılamaz cevap | 0 / 0 | 9 / 1 |

**Plakada arayüz çözüldü:** serbest seçimde 5 doğru/3 geçersiz olan plaka, öneri incelemeye
sunulduğunda **7 doğru + 1 kısmi** oldu ve model altı bozuk önerinin altısını da okumanın *doğru*
bağına düzeltti (`binding_wrong_beyond_copy` 0) — yani kopyalama değil, okuma. İki temiz öneriyi
değiştirmedi, hiç yanlış alarm vermedi. Kalan tek kayıp `pdf-3` adedi: model "4 × Ø6,80"in adedini
`diameter` olarak bağlıyor, etiket `count` bekliyor (tür alanı).

**Plastik sınırı ölçüldü:** 14 sayının 10'unda okuma hiç bağ kurmamış, dolayısıyla incelenecek öneri
yok (9'unda model kendi bağını yazdı, 1'i sözleşmeden geçmedi). Okumanın bağ kurduğu 4 ölçüde kusur
4/4 yakalandı; yarıçapta model kusuru gördü ama doğru 12 kimlikli kümeyi kuramadı. Bu, okuma
zincirinin kapsamının (bağ kurmadığı 10 sayı) bir sonraki gerçek iş olduğunu yine gösteriyor.

**Ölçüm düzeltmeleri (bu turda, kayıtlı cevaplar yeniden puanlandı):**
- Okumanın **hiç bağ kurmadığı** ölçüler "temiz öneri" sayılıp yanlış alarm yazılıyordu (plastikte 9
  sahte yanlış alarm). Artık ayrı sınıf: `no_reading_binding` (`review_summary`), ve cevabı
  sözleşmeden geçmeyen satır `unusable_answer` olarak sayılıyor.
- `answers_agreed_with_reading` beş turdur **0** görünüyordu: özet, koşu kaydındaki `reading_agreement`
  alanı yerine paketin `checks` alanını okuyordu. Düzeltildi; yeniden puanlanmış doğru sayılar
  plakada 0 → 3 → 2 → 5 → **8**, plastikte 3 → 3 → 3 → 3 → 3. (Önceki raporlardaki "3/14" sayısı
  zaten doğru alandan geliyordu; yanlış olan özet alanıydı.)

Kanıt: `eval/reports/meaning-interpretation-evidence-05.json` (`--check`: 22 ölçü, sunulan önerinin
istemde olduğu da denetleniyor).

## Okuma zinciri ayrı rapor

Yorum arayüzünün ölçümü burada biter. Bu dilimden sonra sıradaki iş okuma zincirinin kapsamıydı;
ölçümü ve sonucu `eval/reports/reading-coverage.md` dosyasında (2026-09-27, satırların ölçekle
karşılaştırılması).

## Yedinci koşu: okuma artık her sayıyı ölçünün yanındaki çifte bağlıyor — `meaning-3b-06`

Aynı arayüz, aynı model (`qwen2.5vl:3b`, 16384 ctx, 4096 predict, sıcaklık 0), aynı iki pafta; **değişen tek şey
okuma**: plastikte 14 sayının hepsi bağlı ve bağlar ölçülerin yanında duruyor (bkz. `reading-coverage.md`).
Bu koşu, arayüzün artık *tanıklığını* değil **kopyalamayı** ölçtüğünü gösteriyor — ve inceleme turu ayrıştırıcı
kalıyor.

| | `meaning-3b-05` (eski okuma) | `meaning-3b-06` (yeni okuma) |
|---|---|---|
| plaka sınıfları (bağımsız etiketle) | 7 doğru / 1 kısmi / 0 geçersiz | **aynı: 7 / 1 / 0** |
| plaka: cevap okumanın bağını tutuyor | 8/8 | **8/8** |
| plaka: enjekte edilen kusur yakalandı | 6/6, yanlış alarm 0 | **6/6, yanlış alarm 0** |
| plastik: cevap okumanın bağını tutuyor | 3/14 | **13/14** |
| plastik: enjekte edilen kusur yakalandı | 4/4, **9 yanlış alarm** | **10/10, yanlış alarm 0** |
| plastik: okumanın önerisinin ötesinde yanlış bağ | 1 | **1** (`pdf-2 radius`) |

- **Plaka değişmedi ve bu beklenen**: plakada okuma zaten ölçünün yanındaydı (onarılmış satır yok), arayüzün
  tür/eksen/bağ alanları eskisi gibi dolu. Tek kısmi yine `pdf-3`'ün **adedi**: model "4 × Ø6,80"in adedini
  `diameter` olarak bağlıyor, etiket `count` bekliyor (`kind: false`, `binding: true`).
- **Plastiğin 13/14'ü kopyalama payıdır, tanıklık değil**: okuma artık her sayı için geçerli bir yerel çift
  önerdiği için modelin o çifti tekrarlaması kolay. Arayüzün bağımsız değeri bu koşuda **inceleme turunda**:
  10/10 enjekte edilmiş kusur düzeltildi, 4 temiz öneri olduğu gibi korundu, yanlış alarm yok.
- **Tek ayrışma** (`pdf-2 radius`): model öneriyi değil `g57/g60`'ı adlandırdı ("R8.00 ... g57 diameter_mm 4,02")
  — okumanın önerisi 12 adaylı bir `matched` kümesiydi. İnceleme sınıfı: kusur yakalandı ama `right: false`,
  yani cevap okumanın önerisinin ötesinde bir bağ kurdu. Bu, plastikte okumanın bağının **doğruluğunun**
  sınanmadığı yerin tam olarak nerede olduğunu gösteriyor: bağımsız etiket yok.
- **Tek değişken uyarısı:** 05 → 06 karşılaştırması **tek değişkenli değil** — arada yedinci dilimin yargı
  düzeltmesi (yanlış alarm sınıfı) ve dört okuma-zinciri değişikliği var. Plakanın birebir aynı çıkması,
  değişikliklerin etiketli paftayı bozmadığını gösterir; plastikteki 3/14 → 13/14 ve 9 yanlış alarm → 0 ise
  bu iki değişikliğin **toplamı**dır, ayrıştırılmadı.
- **Kayıt:** ham istek/cevap `out/meaning-interpretation/meaning-3b-06/{requests,answers}/`, özet `run.json`,
  günlük `out/profile-step/meaning-3b-06.log`; taşınabilir kanıt paketi
  `eval/reports/meaning-interpretation-evidence-06.json` (`--check`: 22 ölçü, 0 sorun). Koşu 173,06 sn, durum
  `complete`. Etiket yalnız puanlamada: `eval/relations/plate-pocket-1.json` (`eval/relations/` model arayüzüne
  hiç verilmiyor).

**Ne kanıtlanmadı:** okuma zinciri daha keskin olduğu için arayüzün **doğru yorumu** arttı demek yanlış olur —
plastiğin cevapları okumanın kendi bağını tekrarlıyor ve orada bağımsız etiket yok. Arayüzün ayrıştırıcı gücü
hâlâ yalnız (a) plakanın etiketli 8 ölçüsünde ve (b) her iki paftadaki sentetik kusurlu inceleme turunda
ölçülüyor. Sıradaki tek karar bu yüzden ölçüm tasarımında.

## Sekizinci koşu: kör tur — okumanın önerisi gösterilmeden (`meaning-3b-07-blind`)

`--review` **verilmeden** koşuldu: bu yolda `injected = None`, yani model yalnız ölçü bağlamını ve aday menüsünü
görüyor, okumanın kendi bağını hiç görmüyor. 05/06 turlarında ise **her iki** çağrı da öneriyi görüyordu — bu
yüzden kör ölçüm bugüne kadar yapılmamıştı. Koşu 190,98 sn, `complete`.

| | kör (`-07`, öneri yok) | önerili (`-06`) |
|---|---|---|
| plaka (bağımsız etiketle) | **5 doğru / 0 kısmi / 3 geçersiz** | 7 doğru / 1 kısmi / 0 geçersiz |
| plaka: sözleşme dışına taşan bağ | 3 | 0 |
| plastik: cevap okumanın bağını tutuyor | 13/14 | 13/14 |

- **Arayüzün öneri olmadan doğruluğu plakada 5/8**; öneriyle 7/8 + 1 kısmi. Yani sekiz ölçünün **ikisi**
  yalnızca okumanın önerisini denetlemekten geliyor (`pdf-3 diameter_1`, `pdf-4 diameter_2`); adedi (`count`)
  öneriyle de kısmi kalıyor.
- **Kör kayıpların hepsi tek sınıf:** tek geometri *boyutlandıran* çağrı (Ø6,80 · Ø50 · R8,00) **çift** olarak
  cevaplanıyor. Model `kind: diameter` yazıp iki kimliği `between`'e koyuyor
  (`between: [g9, g12]`, `matched: []` → `"diameter için en az bir geometri kimliği gerekli"` +
  `"diameter için iki uç değil, eşleşen geometri gerekli"`), gerekçesinde de "which are both circles" diyor:
  kastettiği daireler, koyduğu yer yanlış liste.
- **Bu sınıf üç kör koşuda birebir aynı** (`-03`, `-04`, `-07`; kimlikler bile aynı: `g12/g9` ve `g8/g9`) —
  iki ayrı okuma, iki ayrı yargı sözleşmesi boyunca değişmedi. Yani kayıp geometri menüsünde değil, arayüzün
  **alan** işleyişinde: okuma keskinleşti (plastik 4/14 → 14/14 bağlı) ama kör doğruluk plakada 5/8'de kaldı.
- Plastikte kör uyum 13/14: öneri gösterilmeden de modelin adlandırdığı çift okumanın çiftiyle aynı — bu
  öz-tutarlılık, doğruluk değil (plastikte etiket yok) ve tek ayrışma yine `pdf-2 radius` (geçersiz).
- **Kayıt:** `out/meaning-interpretation/meaning-3b-07-blind/`, günlük
  `out/profile-step/meaning-3b-07-blind.log`, paket `eval/reports/meaning-interpretation-evidence-07.json`
  (`--check`: 22 ölçü, 0 sorun).

**Ölçülen arızaya karşı tek değişken (`interpret.py`, sürüm `single-measurement-interpretation-v2-form-field`):**
cevap isteği artık **bu ölçünün kendi formuna** göre hangi listeyi istediğini söylüyor — form `distance`/`angle`
ise "iki kimliği `between`'e koy, `matched` boş kalsın", `diameter`/`radius`/`count` ise "kimlikleri `matched`'e
koy, `between` boş kalsın" — ve cevap şeması aynı kısıtı taşıyor (`matched.maxItems: 0` ya da
`between.maxItems: 0`, karşılığı `minItems`). Bu, hangi kimliğin doğru olduğunu söylemez; yalnız sözleşmenin
yargılayacağı alanı söyler. Kör koşu `meaning-3b-08-blind-v2` etiketiyle yinelendi.

### Sonuç: kör tur `meaning-3b-08-blind-v2` (aynı model, aynı paftalar, yalnız istek metni değişti)

| | `-07` kör (v1) | `-08` kör (v2) | `-06` önerili (v1) |
|---|---|---|---|
| plaka (bağımsız etiketle) | 5 doğru / 0 kısmi / **3 geçersiz** | **7 doğru / 1 kısmi / 0 geçersiz** | 7 doğru / 1 kısmi / 0 geçersiz |
| plaka: sözleşme dışına taşan bağ | **3** | **0** | 0 |
| plastik: cevap okumanın bağını tutuyor | 13/14 | 13/14 | 13/14 |

- Üç kayıp da yerini buldu: `pdf-3 diameter_1` → `matched: [g9, g10, g11, g12]` (etiketin "the four corner
  holes"u) ve `pdf-4 diameter_2` → `matched: [g8]` (etiketin "the single circle at the centre"ı) **doğru**;
  yani öneri gösterilmeden ulaşılan doğruluk, öneri gösterilen turla aynı (7/8 + 1 kısmi). Kopyalamadan gelen
  iki ölçü artık kör de doğru.
- Kör doğruluk artık **7/8**, yani arayüzün plakadaki kendi yorumu ile öneri denetimi arasındaki fark kapandı.
- Kalan tek etiketli kayıp `pdf-3`'ün **adedi**: çağrı "4 × Ø6,80" hem çap hem adet taşıyor; model adet
  ölçüsünü de `diameter` olarak adlandırıyor (`kind: false`, `binding: true`). Katalog bu ölçü için
  `quantity: count` diyor — sıradaki tek değişken bunu istekte söylemek.
- Plastikte `pdf-2 radius` **üçüncü kez ayrı bir sebeple** reddedildi: bu kez `unresolved: true` **ve**
  `matched: [g57, g60]` birlikte yazıldı, soru boş → sözleşme "çözülemeyen bağda geometri iddiası var" +
  "soru yazılmamış" diyor. Aynı satır üç koşuda üç ayrı arıza şekli gösterdi: 06'da önerinin ötesinde yanlış
  bağ, 07'de yanlış listede çift, 08'de iddialı "çözülemedi". 12 kimliklik aday kümesiyle R8,00 gerçekten
  zor bir ölçü; plastikte etiket olmadığı için orada doğru cevabı bilmiyoruz.
- **Kayıt:** `out/meaning-interpretation/meaning-3b-08-blind-v2/` (244,83 sn, `complete`, sürüm
  `single-measurement-interpretation-v2-form-field`), paket
  `eval/reports/meaning-interpretation-evidence-08.json` (`--check`: 22 ölçü, 0 sorun).

### İkinci ölçülen arıza ve sonucu: adet ölçüsü kendi miktarını ister (`meaning-3b-09-blind-v3`)

Plakada kalan tek etiketli kayıp `pdf-3`'ün **adediydi** (`kind: false`): "4 × Ø6,80" çağrısı bir kez basılıyor,
iki kez soruluyor — hem çapı hem adedi — ve **metin ile aday menüsü ikisinde birebir aynı**. Yani hangi ölçünün
sorulduğunu metinden çıkarmak mümkün değil; bunu yalnız katalog biliyor (`quantity: count` / `dimension`).

**Tek değişken (`interpret.py`, `INTERPRETATION_VERSION` → `single-measurement-interpretation-v3-count-quantity`):**
bağlam ve istek artık ölçünün **katalogdaki miktarını** taşıyor; miktar `count` ise istek "bu ölçü çağrının
sayısıdır, boyutu değil: saydığı kimlikleri `matched`'e koy ve türü `count` yap" diyor. Diğer ölçüler için tek
fark veri alanının eklenmesi — 22 isteğin satır satır karşılaştırmasında başka değişiklik yok; kimlik menüsü
(`allowed_ids`, `candidate_pairs`) hiç değişmedi.

| kör tur | istek sürümü | plaka (bağımsız etiketle) | plastik |
|---|---|---|---|
| `-07` | v1 | 5 doğru / 0 kısmi / **3 geçersiz** | 13/14 |
| `-08` | v2 (form → alan) | 7 doğru / 1 kısmi / 0 geçersiz | 13/14 |
| `-09` | v3 (miktar) | **8 doğru / 0 / 0** | 13/14 |

- Sekiz ölçünün sekizi de doğru tür ve doğru geometriyle: `pdf-3 diameter_1_count` artık `kind: count`,
  `matched: [g9,g10,g11,g12]` (etiket: "the four corner holes"), `pdf-3 diameter_1` `matched` aynı küme,
  `pdf-4 diameter_2` `matched: [g8]`. Öneri gösterilmeden, elle doğrulanmış etiketin **tamamı** üretildi.
- Kör doğruluk 5/8 → 7/8 → **8/8**; üç adım da tek değişkenli ve ölçülmüş (alan, miktar) — okuma zincirine hiç
  dokunulmadı.
- `-09` 267,08 sn, `complete`; paket `eval/reports/meaning-interpretation-evidence-09.json`
  (`--check`: 22 ölçü, 0 sorun); ham istek/cevap `out/meaning-interpretation/meaning-3b-09-blind-v3/`.
- **Plastikte değişmeyen tek ayrışma** `pdf-2 radius`: üç kör koşuda da `invalid`, bu kez yine
  `unresolved: true` + `matched: [g57,g60]` + boş soru (sözleşme: "çözülemeyen bağda geometri iddiası var" +
  "soru yazılmamış"). 12 adaylı R8,00 için doğru cevabı bilmiyoruz — orada etiket yok. Bu ölçü, üçüncü pafta
  etiketiyle birlikte ele alınacak ilk aday.

### `meaning-3b-10-third-blind` — üçüncü paftada kör tur (10. koşu, 2026-09-28)

Model: `qwen2.5vl:3b` (`fb90415cde1e…`), arayüz sürümü `single-measurement-interpretation-v3-count-quantity`,
yargı sözleşmesi `interpretation-contract-v4`, **öneri gösterilmedi** (kör), 17 ölçü, **146,154 sn**, `complete`.
Etiket `eval/relations/exercise-1-vector.json` — modele hiç verilmedi.

**Sınıflar:** `correct 11` · `no_label 6` · `ambiguous 0` · sözleşme dışı bağ 0. Etiketsiz 6 satır, etiketin
kendi belgelenmiş sınırı (dört "20" + iki "40" → harness yalnız tekil değerleri eşliyor).

**Tür (kind): 11/11.** Beş çap çağrısının tamamı `diameter` olarak cevaplandı (`pdf-17`/`19`/`20`/`21` etiketli,
`pdf-22` çift değerli olduğu için etiketsiz ama o da `diameter`). Ölçünün kendi formu ile cevabın türü on bir
satırın hepsinde uyuştu; **hiç `invalid` yok** (önceki paftalarda kör turda üç satır sözleşme dışıydı).

**Bağ: bu paftada puanlanamıyor** (ölçüldü, yukarıdaki bölüm) — ve ham cevaplar bunun neden önemli olduğunu
gösteriyor. Modelin `matched` listeleri beş çapta:
`pdf-17 (Ø20) → [g133]` **doğru** · `pdf-21 (Ø50) → [g65]` **doğru** ·
`pdf-22 (Ø40) → [g125,g134]` okumanın kendi eşleşmesiyle aynı ·
`pdf-19 (Ø30) → [g65,g68]` **fazladan bir kimlik** (g65 = Ø50 göbeği) ·
`pdf-20 (Ø25) → [g134,g138]` **yanlış** (doğrusu g122; g138 bir çizgi ucu).
Yani tür alanı tutarken kimlik alanı 5'te 2 doğru → **bağ puanlaması açılmadan bu fark görünmez.**

**Okumadan ayrıldığı 4 satır** (kör olduğu hâlde okumanın bağıyla karşılaştırma): `pdf-13` (R20) · `pdf-18` (6) ·
`pdf-19` (Ø30) · `pdf-20` (Ø25) → `answers_agreed_with_reading = 13/17`. `pdf-18` okumada da çözülemsizdi;
model onu bir çiftle (`g55`,`p311`) cevapladı ve gerekçesinde "değeri doğrulamıyor" dedi — yani çözülemsiz
bırakmak yerine zorladı.

**Sayı yasağı (v2 kararı yürürlükte):** üç cevabın gerekçesinde kimlik dışı sayı var → `warnings`'e yazıldı,
cevap düşürülmedi (`pdf-19`/`20`/`21`). `pdf-22`'nin gerekçesi de sayı taşıyor ama etiketsiz satır olduğu için
sınıf `no_label`.

**Bir sonraki adım (ölçülmüş):** etiketin çemberlerini okumanın kimliklerine **çapa göre** eşle (beş çap tekil
ve %3 içinde) → bu paftada bağ puanlaması açılır ve yukarıdaki 5'te 2 sonucu bir puan olur.

## 2026-09-28 — yedinci dilim: etiketin çapı kimliği belirler (konum yolu başarısız olunca ikinci yol)

**Ölçülen engel (önceki dilim):** etiket konumları okumanın çerçevesinde olmadığı için üçüncü paftada
bağ puanlaması 0/17 idi. Plakada tutuyordu (`h1 [-50,-30]` ↔ `g9 [-50.35,-30.21]` = 0,4 mm → 5/8).

**Değişiklik (tek değişken, `eval/meaning_interpretation.py`).** `expected_for_measurement` içindeki kimlik
eşlemesi iki yollu oldu:
1. **Konum yolu** (eskisi): etiket konumu okumanın mm çerçevesinde 2 mm içinde bir kimliğe düşerse eşlenir.
2. **Çap yolu** (yeni): düşmezse, etiketin **doğrulanmış `diameter_mm`'si** okumanın ölçtüğü boyutlarla
   karşılaştırılır ve **yalnız tam olarak bir** kimlik o boyutta ise eşlenir. Boyutlar okumanın kendi
   iddialarından okunur: bir çap iddiası `drawn_mm` taşır ve bu değer **eşleştiği geometrinin kendi
   yarıçapından** hesaplanır (basılı değerden değil), yani kayıt "bu kimlik şu boyutta ölçüldü" bilgisidir.
   Tolerans okumanın kendisi: %3 bağıl ya da 0,15 mm (hangisi büyükse). Sonuç kayda `mapping_basis` olarak
   yazılır (`position` / `diameter`) — hangi kimliğin nasıl eşlendiği görünür kalır.

**Ölçülen etki (dry-17/dry-18, model çağrısı yok):**

| pafta | ölçü | bağ-puanlanabilir (önce → sonra) | eşleme yolu |
|---|---|---|---|
| plaka | 8 | **5 → 5** ✓ değişmedi | 13 kimliğin hepsi `position` |
| plastik | 14 | **0 → 0** ✓ değişmedi | — |
| üçüncü pafta | 17 | **0 → 3** | üçü de `diameter` |

Üçüncü paftada açılan satırlar ve beklenen kimlikler:
`pdf-19` (Ø30) ↔ `d11` → **g68** · `pdf-20` (Ø25) ↔ `d12` → **g122** · `pdf-21` (Ø50) ↔ `d13` → **g65**.
İkisi açılmadı ve bu doğru davranış: `pdf-17` (Ø20) ve `pdf-22` (Ø40) etiketle **eşlenmiyor** çünkü dört
"20"/iki "40" çift değerli (harness yalnız tekil değerleri eşliyor) — ve ayrıca Ø40'ın doğrulanmış 40 mm'si
okumanın ölçtüğü **iki** yaya (g125/g134, ikisi de 41,08) düşüyor, yani boyut tekil değil → eşleme
reddediliyor. Kalan `unmapped_label_ids` listesi yüz/kenar kimlikleri (`top_face`, `datum`,
`left_lug_face_a` …): onların ne konumu ne boyutu var, sessizce "tuttu" sayılmıyor.

**Yöntem sınırı (yazılı):** çap yolu, okumanın ölçtüğü boyutlara dayanır — etiketin rolü *değeri* ve
*karşılaştırmayı* sağlamak; kimliğin kendisi "o boyutta tek geometri" ölçümünden gelir. Yanlış bir bağın
zehirlenmesi mümkün değil: iddianın `drawn_mm`'i eşleştiği geometrinin yarıçapından gelir, basılı değerden
değil, ve eşleşme zaten %3 içinde olmak zorunda.

### `meaning-3b-11-third-blind-v2` — aynı kör tur, açılan bağ puanı (11. koşu, 2026-09-28)

Model ve arayüz değişmedi (`qwen2.5vl:3b` `fb90415cde1e`, `single-measurement-interpretation-v3-count-quantity`,
yargı `interpretation-contract-v4`, öneri gösterilmedi); değişen tek şey ölçü aletiydi (çap yolu).

**Denetim: cevaplar birebir aynı.** On yedi satırın ham cevabı `meaning-3b-10-third-blind` ile
**0/17 farklı** — yani iki koşu eşleştirilmiş bir ölçüm: aradaki tek fark neyin puanlandığı.

**Sınıflar:** `correct 9` · `partial 2` · `no_label 6` (önce: `correct 11` · `no_label 6`). Düşen iki satır
kaybedilmedi, **ölçüldü**: on bir `kind` doğrusu duruyor, üstüne bağ puanı bindi.

| ölçü | beklenen kimlik (etiket) | modelin cevabı | sınıf | alanlar |
|---|---|---|---|---|
| `pdf-19` (Ø30) | `[g68]` | `[g65, g68]` | **partial** | `kind: true`, `binding: false` |
| `pdf-20` (Ø25) | `[g122]` | `[g134, g138]` | **partial** | `kind: true`, `binding: false` |
| `pdf-21` (Ø50) | `[g65]` | `[g65]` | **correct** | `kind: true`, `binding: true` |

**Arayüzün bu paftadaki kimlik puanı: 3'te 1.** Tür 11/11 iken kimlik 1/3 — arayüz doğru *türü* söylüyor,
doğru *kaynağı* çoğu zaman söylemiyor. `pdf-19`'da doğru kimliği (`g68`) bulmuş ama yanına `g65`'i (Ø50
göbeği) eklemiş; `pdf-20`'de doğru kimliği hiç bulamamış (`g134` bir R20 yayı, `g138` bir çizgi ucu).

**Puanlanamayan sekiz etiketli satır** (`pdf-9` · `10` · `11` · `12` · `14` · `16` · `18` · `25`) mesafe
satırları: etiketin kimlikleri yüz/kenar (`top_face`, `datum`, `left_lug_face_a` …) ve onların ne konumu ne
boyutu var. Sıradaki iş, o kimliklere etiketin kendi çizim-dimension zincirinden konum vermek.
- **Doğrulama:** `round19` = 469 geçti / 243,36 sn (+2 test) · paket `-11` `--check` 17/0 · `check_tables` 20/0 ·
  `baseline_report --check` ve `profile_step_evidence --check` uyuşuyor · **istek özeti kalkanı 22/22**
  (alet değişikliği isteklere dokunmadı) · `git diff --check` temiz.

### Menü tanısı ve `v4`/`v5`: ölçülen boyut menüye girdi, istek şişmesi geri alındı (2026-09-28)

**Tanı (ölçüldü).** `pdf-19`/`pdf-20`/`pdf-21` için modele sunulan menü 19 kimlik taşıyor ve her kimlik
yalnız `kinds` + `points_mm` veriyordu. Kritik ayrıntı: **iki farklı çaplı kimlik aynı noktayı** taşıyor —
`g65` (Ø50 göbeği, ölçülen 51,33) ve `g68` (Ø30 deliği, ölçülen 30,73) ikisi de `(11,27; 180,71)`;
`g122` (Ø25 deliği, 25,70) ve `g125` (R20 yayı, 41,08) ikisi de `(69,9x; 20,5x)`. Yani soru menüden
**cevaplanamaz** durumdaydı ve modelin cevapları bunun beklenen sonucuydu (biri iki kimliği birden saydı,
öteki yanlış kimlikleri).

**Değişiklik.** Okumanın kendi ölçtüğü boyut menüye girdi: `interpret.measured_sizes` (iddiaların
`drawn_mm`'i — eşleşen geometrinin kendi yarıçapından — artı katalog çemberleri) ve `offered_geometry_ids`
girdilerine `measured_diameter_mm`. İstek sürümü iki adımda ölçüldü:

| istek | üçüncü pafta (kimlik puanı) | plaka |
|---|---|---|
| `v3-count-quantity` (boyut yok) | correct 9 · partial 2 · **1/3** · okuma uyumu 13 | **correct 8** · 5/5 |
| `v4-measured-sizes` (alan + 2 satır cümle) | correct 10 · partial 1 · **2/3** · 14 | correct 7 · partial 1 · **4/5** ✗ |
| `v5-measured-sizes-quiet` (alan + kısa satır) | correct 10 · partial 1 · **2/3** · **15** | **correct 8** · **5/5** ✓ |

**İki ayrı etki ayrıştırıldı:** `v4 → v5` yalnız cümleyi kısaltı (alan aynı kaldı). Üçüncü pafta 2/3'te
kaldı, okuma uyumu 14 → 15; **plaka 8/8'e döndü** ve `pdf-3`'ün boyut satırı yeniden dördünün hepsini
saydı. Yani `v4`'te plakanın kaybettiği satır **alanın değil, eklenen iki satırın** sonucuydu — ölçüldü,
tahmin edilmedi. Kalan durum `v5`.

**İstek diff'i (tek değişken denetimi, `dry-18` → `dry-19`):** `v4`'te istek 30 → 32 satır; tek eklenen
veri 6 kimliğin `measured_diameter_mm`'i (`g65` 51,33 · `g68` 30,73 · `g122` 25,70 · `g125` 41,08 ·
`g133` 20,56 · `g134` 41,08); aday çiftleri, izinli kimlikler, ölçüm bağlamı ve şema **birebir aynı**.

**Kalkan hedefi taşındı (gerekçeli):** `v3` paketine göre 22/22 olan istek-özeti kalkanı, istek sürümü
kasıtlı olarak değiştiği için geçersiz; yeni taban `v5` koşuları (`-15` paketi) ve kalkan orada
**22/22** veriyor. Yani "kalkan bozuldu" değil, "kalkan yeni sürüme göre yeniden kuruldu" — ve bunun
sebebi kayıtlı.
- **Doğrulama:** `round20` = 470 geçti / 241,45 sn (+1 test) · `-12..-15` paketleri `--check` 0 sorun ·
  `check_tables` 20/0 · `baseline_report --check` + `profile_step_evidence --check` uyuşuyor · istek-özeti
  kalkanı yeni tabanda (`-15`) **22/22** · `git diff --check` temiz.

### `pdf-20` tanısı ve kof denetimin değiştirilmesi (2026-09-28)

**Soru:** menü artık `g122`'yi Ø25,70 ile gösterirken model neden `[g134, g65]` dedi? **Ölçüm:** istekte
doğru cevap **iki kez** yazılıydı — `measured_by_the_reading`: `anchors=[{g122, circle-centre}]`,
`matched_geometry=[g122]`, `drawn_mm=25,70`; `allowed_ids` içinde `g122` var; `candidate_pairs` boş.
Model yine de `matched=[g134,g65]` dedi ve gerekçesinde "okuma bu ölçüyü g134 ile g65 arasında ölçtü"
diye **yanlış** bir cümle kurdu. Yani bu satırdaki kayıp **arayüzün değil, modelin** hatası: istek iyi
kurulmuş, model kendi kanıtıyla çelişmiş.

**Alet hatası (ölçüldü):** `pair_is_a_measured_candidate` denetimi
`not candidate_pairs or pair in candidate_pairs` biçimindeydi; çap/yarıçap istekleri tasarım gereği
`candidate_pairs=[]` taşıdığı için bu denetim **her cevaba true** diyordu — hiçbir şey söylemiyor, ama
"geçti" gibi okunuyordu. Üçüncü paftanın yanlış bağını da sessizce onaylamıştı.

**Yerine konan denetim:** `named_ids_do_not_contradict_the_printed_size` — cevabın adlandırdığı
kimliklerden ölçülmüş çapı olanlardan biri basılı değerle çelişiyor mu? Yalnız isteğin **kendi
yayımladığı** ölçüleri kullanır (etiketsiz ✓), okumanın kendi toleransıyla karşılaştırır
(`%3` / `0,15 mm`), ve soru bir boyut sorusu değilse ya da adlandırılan hiçbir kimlik ölçülmemişse
`None` döner — uygulanamayan denetim "geçti" sayılmaz. Yargı sözleşmesi
`interpretation-contract-v4` → **`-v5-size-agreement`**.

**Etki (depolanmış cevaplar yeniden yargılandı, model çağrısı yok):** iki `v5` koşusundaki 39 cevaplanmış
satır → **true 8 · false 1 · none 30**; tek `false` tam olarak `pdf-20` (`g134` Ø41,08 ve `g65` Ø51,33,
basılı 25,00) ve plakanın 8/8 doğru satırında **hiç yanlış alarm yok**. Puanlar değişmedi (sınıflar
etikete göre ✓); değişen şey, o satırın gerekçesinin artık kendi denetimiyle çeliştiğinin **kayıtlı**
olması. Kayıt: `out/profile-step/judge-v5-effect.txt`.

**Paket sınırı (dürüst sınır):** `-14`/`-15` paketleri eski sözleşmenin kaydı olarak dondu; `--check`
artık onların durum karşılaştırmasını "başka yargı sözleşmesi" diye atlıyor (17/17 ve 22/22, 0 sorun).
Yeni sözleşmenin kanıtı yukarıdaki etki kaydıdır; paketleri yeniden üretmek model çağrısı gerektirirdi ve
aynı deneyi değişiklik olmadan tekrarlamak olurdu.
- **Doğrulama:** `round21` = 471 geçti / 246,49 sn (+1 test) · istek-özeti kalkanı **22/22** (yargı
  değişikliği istekleri değiştirmedi — yeniden hesaplandı ✓) · `-14`/`-15` paketleri `--check` 0 sorun ·
  `check_tables` 20/0 · `baseline_report --check` + `profile_step_evidence --check` uyuşuyor ·
  `git diff --check` temiz.

### Üçüncü yol: etiketin doğruladığı değer, okumanın kendi çapalarını kazandırır (2026-09-28)

**Neden gerekti.** Üçüncü paftada 17 ölçünün 8'i puanlanamaz durumdaydı: etiket **yüz** adları veriyor
(`top_face`, `bottom_face`, `left_lug_face_a` …, STEP'te z=±13/±3/±10/±20/±5, y=0/80), okuma ise **pafta
çerçevesinde** kimlik bildiriyor; ikisi 12–34 mm ayrı ve görünüş başına ayrı çerçeve gerektiği için
görünüş başına fit zemini de yok (etiketin beş dairesi başka görünüşlerde).

**Üçüncü yol (`mapping_basis: "value"`).** Okumanın **kendi ölçümü** ile etiketin **bağımsız doğrulanmış
değeri** okumanın kendi toleransıyla uyuşuyorsa (max(%3, 0,15 mm)), etiket o satır için okumanın kendi
çapalarını beklenti olarak **kazanmış** olur: `ids` = okumanın ankor kimlikleri. Hiçbir çerçevenin
uyuşması gerekmez; uyuşması gereken iki sayıdır. Uyuşmayan satır hiçbir şey kazanmaz — beklenti
uydurulmaz, `unmapped` kalır.

**Ölçüm (kapsam):** bağ-puanlanabilir satır **3/17 → 10/17**; dayanak dağılımı `value` 14 ad + `diameter` 3 ad.
Puanlanan satırlar: `pdf-9`(80)·`pdf-10`(60)·`pdf-11`(35)·`pdf-12`(57)·`pdf-14`(37)·`pdf-16`(26)·`pdf-19`(Ø30)·
`pdf-20`(Ø25)·`pdf-21`(Ø50)·`pdf-25`(10).

**Ölçüm (puan):** istek metni **17/17 birebir aynı** (istek kurucusu değişmedi → aynı cevaplar
karşılaştırılabilir), depolanmış `v5` cevapları yeni beklentiyle yeniden yargılandı → sınıflar
`correct 10 · partial 1`, **kimlik 9 doğru / 1 yanlış**. Yani arayüzün üçüncü paftadaki kimlik doğruluğu
`2/3` değil **9/10**'dur; tek hata yine `pdf-20`. Kayıt: `out/profile-step/dry-20.log`, tarama
`~/.hermes/cache/scratch/value_score2.py`.

**Çapraz denetim:** etikete dayalı karar ile **etiketsiz** boyut denetimi (`named_ids_do_not_contradict_the_printed_size`)
aynı tek satırı (`pdf-20`) işaret ediyor — iki bağımsız alet aynı yerde buluştu.

**Açıkta kalanlar (sonraki adımlar):** (1) `pdf-18` (6 mm) puanlanamıyor çünkü okuma o satırı **çözemedi**
(`unresolved`, ankor yok) — değer yolu ancak okuma bir ölçüm yaptıysa çalışır; (2) 6 satırın etiketle
eşlenmesi yok (`pdf-13` R20 = d5, `pdf-17` = ?, `pdf-22` Ø40 = d14, `pdf-15/23/24` … = d7/d15/d16 zincirleri):
etiket bu satırları **taşıyor**, eksik olan eşleme. Eşlemeyi bitirmek kapsamı ~14-15/17'ye çıkarır.
- **Doğrulama:** `round22` = 472 geçti / 233,70 sn (+1 test) · istek-özeti kalkanı **22/22** · `check_tables`
  20/0 · `baseline_report --check` + `profile_step_evidence --check` uyuşuyor · `git diff --check` temiz.

### Tekrarlanan sayılar: eşleme türle, boyut satırları okumanın kendi eşleşmesiyle (2026-09-28)

**Sorun (ölçüldü).** Eşleme kuralı yalnız **değer+birim tekilliğine** bakıyordu; paftada dört satır "20", iki
satır "40" bastığı için altı etiket satırı hiç eşlenmedi (`d5` R20, `d7`/`d15` 20, `d9` Ø20, `d14` Ø40,
`d16` 40) — oysa iki taraf da ölçülmüştü.

**Kural eklendi:** satır, değer+birim **ve iki tarafın da bildirdiği tür** ile tekil hâle geliyorsa eşlenir;
tür sessizse eski değer+birim kuralı karar verir; aynı türle tekrarlanan değer yine eşlenmez (tahmin yok).
Kural yazılırken **kendi regresyon testi bir hata yakaladı**: `printed.get("kind") == row.get("kind")`
karşılaştırması iki taraf da tür bildirmediğinde `None == None` ile "uyuştu" sayıp satırı türsüz adaya
bağlıyordu; tür yalnız iki taraf da bildirdiğinde ölçüt oldu.

**Boyut satırları için değer yolu genişledi:** değer uyuştuğunda beklenti, okumanın **o ölçü için kendi
eşleştirdiği kimlikler** olur (bir etiket adı iki okuma kimliğini kapsayabilir: Ø40 göbeği iki yay olarak
çizilmiş). Böylece `pdf-13` (R20) ve `pdf-22` (Ø40) — çap yolunun iki eşit yay yüzünden reddettiği iki satır —
puanlanabilir oldu.

| dilim | bağ-puanlanabilir | kimlik |
|---|---|---|
| konum + çap yolu | 3/17 | 1/3 |
| + değer yolu (devam 21) | 10/17 | 9/10 |
| + türlü eşleme ve boyut değer yolu | **14/17** | **13 doğru / 1 yanlış** |

**Puan:** istek metni **17/17 birebir aynı** (cevaplar aynı ✓), depolanmış `v5` cevapları yeni beklentiyle
puanlandı → sınıflar **`correct 14 · partial 1`**, kimlik **13/14**; tek hata yine `pdf-20` ve etiketsiz boyut
denetimi de aynı satırı işaret ediyor (çapraz denetim ✓). Kayıtlar: `out/profile-step/dry-21.log`, `dry-22.log`.

**Açıkta kalan üç satır:** `pdf-18` (okuma çözemedi, ankor yok) · `pdf-15` ve `pdf-23` (iki "20" lineer satır
etiketin `d7`/`d15` satırlarıyla eşlenmiyor; ayrım için etiketin bildirdiği **eksen** gerekir ve o bilgi
etiket satırlarında alan olarak durmuyor, metinde duruyor — sıradaki adım).
- **Doğrulama:** `round23` = 474 geçti / 230,83 sn (+2 test) · istek-özeti kalkanı **22/22** · `check_tables`
  20/0 · `baseline_report --check` + `profile_step_evidence --check` uyuşuyor · `git diff --check` temiz.

### Eksen yolu denendi ve çürütüldü: iki "20" satırı eşlenmeden kalır (2026-09-28)

Kalan iki satırı (`pdf-15` 20,54 mm ve `pdf-23` 20,37 mm — ikisi de lineer "20") etiketin `d7` ("üst görünüş,
yatay") ve `d15` ("alt görünüş, dikey") satırlarıyla eşlemenin yolu **eksen** olabilirdi; etiket bu bilgiyi
taşıyor ama metin olarak, alan olarak değil.

**Ölçüm:** okumanın kendi çapalarından iki satır için de çıkan eksen **dikey** (`pdf-15`: g123(37,08;−41,10) ↔
g138(57,62;−0,02); `pdf-23`: g55(82,78;170,66) ↔ g90(69,98;191,02)). Yani eksen bu iki satırı **ayırmıyor** —
eksenle eşlemek tahmin olurdu ve etiket eşlenmeden kalır (kural: aynı değer + aynı tür → eşleme yok).

**Bunun anlamı (kayda geçen açık soru):** etiketin "üst görünüş, yatay" / "alt görünüş, dikey" ifadesi ile
okumanın pafta çerçevesindeki ekseni **aynı şeyi söylemiyor**; ikisinden biri farklı bir çerçeve/konvansiyon
kullanıyor. Bu, zorla bir eşleme uydurmak yerine soru olarak kalıyor. Kayıp değil: bu iki satırın okumayla
uyumu zaten `answers_agreed_with_reading` sayısında raporlanıyor (15/17), yalnız etikete dayalı bağ puanı yok.

Üç satırın durumu böylece **gerekçeli**: `pdf-18` (etiketle eşli, okuma çözemedi → ankor yok) · `pdf-15` ve
`pdf-23` (iki "20" lineer, eksen ayırmıyor → eşleme yok). Kapsam 14/17, kimlik 13/14.

### İncelemeli koşu: kusur yakalama 7/8, kopyalama 8/17 — ve kör ölçüm neden tek doğru ölçü (2026-09-28)

`meaning-3b-16-third-review-v5` (öneriyi gösteren koşu, 17 ölçü, `--review`). Satır bazında kendi sayımım
harness özetiyle uyuştu:

| inceleme sınıfı | adet |
|---|---|
| `defect_caught` | **7** |
| `clean_kept` | 7 |
| `false_alarm` | 1 |
| `defect_missed` | **1** |
| `no_reading_binding` | 1 |
| öneriyi aynen tekrarlayan (`copied`) | **8/17** |

Yani arayüz, kendisine **bilerek bozulmuş** 8 öneriden 7'sini yakalıyor, 1'ini kaçırıyor; bozulmamış 8 satırın
7'sini koruyup 1'inde yanlış alarm veriyor.

**Asıl ölçüm — öneriyi göstermek kimlik puanını düşürüyor:**

| koşu | sınıflar (aynı 14 satır) | kimlik | okuma uyumu |
|---|---|---|---|
| kör (`-14`) | **correct 14 · partial 1** | **13/14** | 15/17 |
| incelemeli (`-16`) | correct 12 · partial 3 | **11/14** | 12/17 |

Bedava bir iyileşme yok: öneri gösterildiğinde cevapların yarısı öneriyi tekrarlıyor, ama bağ puanı ve okuma
uyumu *düşüyor*. Bu, kayıtlı kör ölçüm kuralını doğruluyor: **arayüzün kendi değeri kör koşunun sayısıdır
(13/14)**; incelemeli koşu kusur yakalama ve kopyalama payını ölçer, doğruluk iddiasını değil.

### `pdf-18` tanısı: satır yanlış ankor çifti, ölçek değil (2026-09-28)

`pdf-18` ("6") okumada **iddiasız** (boş) — okumanın notu da "17 ölçü; 16'sı bağlandı" diyor. Bind katmanındaki
kaydı okundu: iki ankoru var ama `status="partial"` ve `implied_px_per_mm=10,33` — paftanın kalibrasyonu
**3,83 px/mm**.

**Hipotez 1 (farklı görünüş/ölçek) çürütüldü.** Paftadaki 16 satırın ima ettiği ölçekler: 13 satır 3,75–3,93
(ortanca 3,86), aykırılar `pdf-13` 9,34 · `pdf-17` 10,70 · `pdf-20` 5,32 · `pdf-21` 6,16 · `pdf-19` 1,23 ·
`pdf-18` 10,33. Aykırıların beşi **çap/yarıçap** satırı (orada "satır" bir leader'dır, iki uzatma çizgisi
arası değil → metrik anlamsız). Geriye tek normal satır kalıyor: `pdf-18`. Ve **komşusu** `pdf-16` (26 mm,
metin kutusu yalnız ~60 px ötede) **3,81** veriyor → bölge normal ölçekte, "başka görünüş" değil.

**Hipotez 2 (yanlış ankor çifti) doğrulandı.** Pafta ölçeğiyle "6" satırı **6 × 3,83 ≈ 23 px** olmalı; okumanın
seçtiği ankorlar ise **62 px** (317→379) ayrı. Okumanın kendi aday listesinde tam **23,28 px** uzakta bir özellik
duruyor: ikinci ankorun `p296` adayı (y=1229,72 ↔ ankor y=1253). Yani satır uçları yanlış seçilmiş; doğru çift
ölçekle uyuşan çift.

**Sonuç:** okumanın reddi (`partial` → iddiasız) kendi kuralına göre **tutarlı** (ölçekle çelişen satırı
bağlamıyor), ama reddin sebebi ölçek değil **ankor seçimi**. Sıradaki iş: satır seçimini ölçek-farkında yapmak —
seçilen çiftin ima ettiği ölçek kalibrasyonla çelişiyorsa ve aynı komşulukta basılı değerle uyuşan **tek** aday
çift varsa onu seç, yoksa `partial` bırak (uydurma yok). `bind.py`'de `_repick_row_with_calibration` bu iş için
zaten var; genişletme oradan yapılmalı ve kapılar: plaka 8/8, plastik 14/14 kapsam, istek-özeti kalkanı 22/22.
