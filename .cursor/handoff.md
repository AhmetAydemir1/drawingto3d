# Handoff

Bu sohbette tek bir görev üzerinde dur. Context dolunca aynı sohbette devam et. Yeni sohbet açılırsa bu dosya `sessionStart` ile geri gelir; dersleri buraya yaz.

## Görev

Açılı çizilmiş ölçü çizgisini oku. `lines.diagonal_strokes` ve leader yolu duruyor; `dimension_for` hâlâ eksen boyunca dizilmiş çizgileri okuyor, bu yüzden açılı dimension çizgisi görünmez. Stroku kendi eksenine ve ona dik yönde izdüşür. Hedef: flanştaki `6 x Ø6.40` ve `Ø11.00`, ve `plate-pocket-1` üzerindeki açılı ölçü.

Durumu `dur` yapmadan bitmiş sayma. Bitmiş sayma koşulu: açılı dimension çizgisi en az bir gerçek sayfada okunuyor, ilgili pytest yeşil, `eval/frontend.py` ve `--as-raster` tablosunda kapsam düşmüyor ve gürültü artmıyor.

## Nasıl çalış

- Başlamadan önce `eval/README.md` içindeki Known gaps bölümünü oku. Orada ölçülüp bırakılmış yolları tekrarlama.
- Bir hipotez kur, en küçük değişikliği yap, ölç. Sayı iyileşirse tut. Kötüleşirse geri al ve nedenini aşağıya yaz.
- İlgili test: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagonal_leaders.py tests/test_lines.py tests/test_perceive.py -q`
- Okuma değişince model çağırma. Önce `PYTHONPATH=src .venv/bin/python eval/frontend.py`, sonra aynı komut `--as-raster` ile. Kapsam artmalı, gürültü artmamalı. Bir sayfa kazanç, başka sayfa kayıp ise değişiklik kabul değildir.
- Aynı hatayı ikinci kez aynı yolla deneme.

## Şimdi

**`dur`.** Görevin bitme koşulu karşılandı, ölçümle: **açılı dimension çizgisi bir gerçek paftada okunuyor** — `my_part.jpg`'de 45°'lik çap çizgisinin kendi okları `50`'nin ankrajı (284.6 px, 5.692 px/mm; paftanın kendi fiti 5.731, ÷1:2 A4/200 dpi beklentisi 5.9). Ankraj eskiden 53 px'lik bir liderdi (1.062 px/mm) ve `50` paftanın kendi ölçek denetiminde yer bulamıyordu; şimdi fitin dört örneğinden biri.

`pytest tests/ -q` **97 geçti**. `eval/frontend.py` ve `--as-raster` tabloları ders 3 tabanıyla birebir aynı (kapsam düşmedi, gürültü artmadı): exercise-1 5/13 (gürültü 7; raster 5/13 gürültü 7), flange-1 4/13 (5), plate 7/7 (raster 4/7, gürültü 3), plastic 11/11 (raster 7/11, gürültü 8), studycadcam-60 6/9 (9), studycadcam-50 2/3 (7). Kıyas ve tam muhasebe: `CHANGES.md` son iki giriş.

Ayrıntı: üçüncü düzen yazıldı (`lines._angled_row`, sayı ok ucunun ötesinde). İki koruma ölçülmüş hatadan geliyor: stroke, sayının kutusunun iki katından uzun olmalı (plastikte çizili `R8.00` liderinin 91 px'lik parçası, rakamların kestiği yerde ok gibi genişleyip dimension sanılıyordu; sınır 2, gerçek örnek 4.6, parça 1.11) ve sayı span'a değmemeli (my_part'ın tapu bloğundaki `A4`, rakam whitelist'iyle `4` okunup harfin kendi bacağı oklu görünüyordu).

Sıradaki iş bu görevde değil; `out/HANDOFF.md` "Sıradaki iş" listesinde duruyor (çağrı satırının raster okunuşu, çizili `Ø`/`4 x` önekleri, ölçek denetimine piksel tabanlı mutlak tolerans, `reason_drawing` bağlantısı). Yeni sohbet o görevlerden birini `.cursor/handoff.md`'ye Görev olarak yazıp başlasın; bu dosyanın dersleri ve `eval/README.md` Known gaps ölçülmüş yolların kaydıdır.

Ölçülüp bırakılan yollar: iki oklu açılı satırı ok eşiğini 8'den 6'ya indirmek (ders 1), glifleri lider boyunca zincirlemek (ders 2), `_one_pen` korumasını kaldırmak (ders 3; plastik raster tabanında `28.006` hayaleti), üçüncü düzeni üçüncü düzen olarak *satırın* uçlarıyla okumak (ders 4; `50`'nin ankrajını kaybettiriyor, studycadcam-60'a gürültü ekliyor).

## Dersler

### 1. İki oklu açılı satır tutuldu, kapsamı oynatmadı

`dimension_for` eksen geçidi boş dönünce, açısı eksenden en az 6° olan strokta sayının iki okun arasında olup olmadığına bakıyor (`lines._angled_dimension`). Ok tekse sonuç yok; lider `leader_near`'de kalıyor. Kırık çizgide metne bakan uç ok sayılmıyor.

Sentetik testler yeşil: `tests/test_dimensions.py` içinde üç test. Bu değişikliğin kendi ölçümü, bir önceki koşuyla aynı tabloyu verdi. Gürültü listesi de aynı. Bu tablo, sonraki değişikliğin düşmemesi gereken tabandır:

| vaka | frontend | --as-raster |
|---|---|---|
| plate-pocket-1 | 7/7, gürültü 0, 7.817 px/mm | 4/7, eksik 6.8, 8, 50; gürültü `3,00` `3` `20,00` |
| plastic-enclosure-1 | 11/11, gürültü 0, 3.917 px/mm, 7 şüpheli | 9/11, eksik 8, 25 |
| flange-1 | 2/13, gürültü `90` `C7` `3` `7` `7` | aynı (PNG, metin katmanı yok) |
| studycadcam-60 | 6/9 | 6/9 |
| studycadcam-50 | 2/3 | 2/3 |
| exercise-1 | 3/13 | 3/13 |

Not: bu tablo yazıldığı koşuda alındı; `exercise-1` satırı bugünkü kodla yeniden ölçüldüğünde iki kolonda da **2/13** veriyor (ders 3'ün tabanı budur). Diğer beş satır aynı.

Neden hedef bu yolla gelmedi, tekrar deneme:
- Flanştaki `6 x Ø6.40` ve `Ø11.00` çift oklu ölçü çizgisi değil. LSD bu nottan deliğe 60 px'i aşan çizgi döndürmüyor; not merkezinden delik merkezlerine mürekkep yok. Ok eşiğini düşürmek veya tek oklu şaftı ölçü saymak notu bulmaz, lideri uzunluğa çevirir.
- Plakadaki açılı `50,00` ve `6,80` vektör metinde zaten lider. Açılı geçit bu kutulara yeni uç üretmedi.

### 2. Glifleri lider boyunca zincirlemek ölçüldü, geri alındı

Hipotez: `Ø100.00` rakamları liderin bir yanında, adım 46 px, Öklid erişim yaklaşık 32 px. Aynı strokun eksenine izdüşen, aynı tarafta duran rakamlar tek sayı olsun (`perceive._along_stroke`; yalnız `arrow_steps >= 8` olan köşegenler). Aynı koşuda `_split_lines` / `_on_one_line` de yüklüydü.

Ölçüm (2026-09-26, `eval/frontend.py` ve ardından `--as-raster`, çıkış 0). Vektör tablo ders 1 ile aynı kaldı, bir gürültü kimliği dışında: flanş `3` yerine `5`. Raster düştü:

| vaka | --as-raster, ders 1 | bu koşu |
|---|---|---|
| plate-pocket-1 | 4/7, eksik 6.8, 8, 50; gürültü `3,00` `3` `20,00` | 4/7, aynı eksikler; gürültü `3,00` `3` `250,00` |
| plastic-enclosure-1 | 9/11, eksik 8, 25 | 7/11, eksik 3, 8, 10, 25 |
| exercise-1 | 3/13 | 2/13 |
| studycadcam-60 / 50, flange | aynı | aynı (flanş gürültüsü `3` → `5`) |

`50` okunmadı. Kapsam düştüğü ve plaka gürültüsü `20,00` iken `250,00` olduğu için zincir geri alındı: `_along_stroke` ve `_collect_spans` içindeki ok süzgeci silindi, `test_digits_beside_a_diagonal_leader_are_one_number` silindi. `_on_one_line` duruyor; iki satır testi onunla yeşil. Bu fonksiyon bu koşunun içindeydi, tek başına ölçülmedi. İlgili pytest: 27 geçti (`test_diagonal_leaders`, `test_lines`, `test_perceive`, `test_dimensions`).

Tekrar deneme. Küme sayımı (OCR'siz) şunu göstermişti, okuma getirmiyor: `Ø100` kutusu (448, 991, 626, 1154); iki `1.00 X 45°` kutusu kabaca (1330, 1650, 1537, 1792) ve (2221, 1759, 2415, 1941); tarama oku n=2 (1857, 1304, 1946, 1391) gürültü adayıydı.

### 3. Sayının kendi çizgisi okuma açısıdır — tutuldu

Hipotez: kırpım tesseract'a `(0, -ink, 90, -90)` sırasıyla veriliyor, `ink` kırpımdaki bütün mürekkebin fitLine'ı (`perceive._ink_angle`). Okuyucu ilk ayrışan cevabı tutuyor, yani **sıra** her şey. `my_part.jpg`'de 45°'lik çapta basılı `50`: kırpım 58×56, mürekkep 28-37°'de fit oluyor (rakamın konturu, merkezinin çizgisinden kayıyor), o açıda tesseract `2` dedi — iki rakamdan biri, kendi başına bir sayı — ve tutuldu. Rakamların kendi açısı 43.4°: aynı kırpım `50` okunuyor. Eksen dışı yazıda `-ink`'in işareti yanlış; eksene oturan yazıda `ink` ve `-ink` aynı çeyrek dönüş olduğu için bu hiç görünmemiş.

Değişiklik: `perceive._digits_angle` (birbirinden en uzak iki glif merkezinin çizgisi) `perceive._reading_angles` ile ilk sıraya konuyor, eski açıların hepsi arkasında duruyor. Koruma `perceive._one_pen` (limit 0.25): iki rakam aynı kalemle aynı açıda yazıldığı için aynı şekli sunar — 45°'deki bir rakam, düz duran hâli ne olursa olsun kare kadar. Korumasız ölçüm: plastik paftanın raster tabanı bir hayalet kazandı, `28.006` (bbox 465,627) — çizili `R8.00` ile yanındaki dikey sayının 29×18'lik bir parçası aynı kümede. Kapsam kaybı yok ama gürültü kuralı pazarlık dışı, koruma onu kesiyor; korumanın bedeli de bu: şekilleri ayrışan parça kümesi eski sırayla okunur.

Ölçüm (`eval/frontend.py`, sonra `--as-raster`, çıkış 0):

| vaka | önce | sonra | gürültü önce → sonra |
|---|---|---|---|
| exercise-1 | 2/13 | 5/13 | 10 → 7 |
| flange-1 | 2/13 | 4/13 | 5 → 5 |
| plate-pocket-1 | 7/7 (raster 4/7) | aynı | 0 (raster 3 → 3) |
| plastic-enclosure-1 | 11/11 (raster 7/11) | aynı | 0 (raster 8 → 8) |
| studycadcam-60 | 6/9 | aynı | 9 → 9 |
| studycadcam-50 | 2/3 | aynı | 7 → 7 |

`exercise-1`'de kazanılan üç sayı `30`, `37`, `50`; `flange-1`'de `1`, `1`, `#50` (iki `1.00 X 45°` pahı ve `50.00`) ve eski sıranın tuttuğu iki yanlış okuma (`2,` ve bir `2`) gitti. İlgili pytest: 91 geçti (4 yeni test `tests/test_perceive.py`'de).

Tekrar deneme: `_one_pen` korumasını kaldırmak (yukarıdaki `28.006`). Ölçülen marj ince, yeni paftada yeniden ölç: en gevşek gerçek satır flanştaki `#50`, 0.23; korumayı gerekli kılan plastik parça 0.34.

`50`'nin ankrajı o koşuda hâlâ yanlıştı (değer doğru, kaynağı 53 px'lik kısa bir lider). Ders 4 onu çapın iki ucuna döndürdü.

### 4. Üçüncü düzen tutuldu: sayı ok ucunun ötesinde — görev bitti

Hipotez (ders 3'ün sonundan): `_angled_row` iki düzeni okuyor — sayı tek oklu strokun içinde, ya da sayı çizgiyi ikiye kırıyor. Üçüncüsü, ölçülecek şey kendi sayısını taşıyamayacak kadar küçükse: iki ok da özellikte, sayı yanında, aynı doğru üzerinde. `my_part.jpg`'deki `50` bu: çapın 45°'lik çizgisi (uçlar arası 284.6 px, `arrows 23/28`), sayı üst ucun ötesinde.

Değişiklik (`lines._angled_row`): satırdaki strok, iki ucu da okluysa, sayı span'a değmiyorsa ve sayıya bir buçuk karakterden yakınsa span o strokun uçlarıdır. İki koruma ölçülmüş hatadan doğdu, ikisi de yalnızca *susturucu*:

- **Uzunluk:** strok, sayının kutusunun en az iki katı olmalı. Sebep ölçüldü: plastik paftada çizili `R8.00`'in lideri kendi rakamlarını kesiyor, rakamlar çizgiyi ok gibi genişletiyor ve 270 px'lik liderin **91 px'lik parçası** iki ucu oklu görünüp `R8.00`'i 11.4 px/mm'lik bir ankraja bağlıyordu (paftanın ölçeği 3.917). Marj: gerçek örnek 4.6× (284.6 px / 62 px), parça 1.11× (91 px / 82 px), sınır 2×.
- **Değmeme:** sayı kutusuyla örtüşen satır sayının içindeki mürekkeptir. `my_part.jpg`'ın tapu bloğundaki `A4` iki gliftir, rakam whitelist'iyle `4` okunur ve `A`'nın kendi bacağı tepesiyle alt çizgisi sayesinde iki ucu oklu görünür; parça kutusunun içinde kaldığı için reddedilir.

Ölçüm (2026-09-26, `eval/frontend.py` sonra `--as-raster`, ikisi de çıkış 0). Kapı öncesi/sonrası **iki tablo da değişmedi**, bütün paftalarda gürültü de değişmedi: exercise-1 5/13 (gürültü 7; raster 5/13, gürültü 7), flange-1 4/13 (5), plate-pocket-1 7/7 (raster 4/7, gürültü 3), plastic-enclosure-1 11/11 (raster 7/11, gürültü 8), studycadcam-60 6/9 (9), studycadcam-50 2/3 (7). pytest `tests/ -q` **97 geçti** (3 yeni test: ok ucunun ötesindeki sayı ölçülür; üç yüz piksel ötedeki sayı ölçülmez; kısa oklu parça dimension değildir).

Kazanç kapsam değil **kaynak**: `50`'nin ankrajı 53 px'lik liderden (1.062 px/mm) çapın kendi oklarına (284.6 px, **5.692 px/mm**) döndü; paftanın kendi fiti artık dört örnek üzerinde (37, 20, 50, 26; yayılım %1.12) ve `50` fitin içinde. Ankraj noktalarını `out/probe/probe_anchors.py` yazdırır — front-end JSON'u yalnızca ankraj *sayısını* taşıyor, bu yüzden liderle uçlar oradan ayırt edilemiyor.

Tekrar deneme: üçüncü düzeni **satırın** uçlarıyla okumak (tek parça yerine satırın en dış iki ucu + ikisinin de oklu olması). Ölçüldü, geri alındı: `50`'nin ankrajı lidere dönüyor ve studycadcam-60'ın gürültüsü 9 → 10 oluyor. Parça + uzunluk koruması bunun yerine duruyor.

### 5. Açık kalan

- `6 x Ø6.40` ve `Ø11.00` okunmuyor. LSD nottan deliğe çizgi döndürmüyor; mürekkep yok.
- `R35` üç çift. Beş kalın rakam tek doğru; araya giren 22×3 px şerit (`_glyphs`, `min(w,h) >= 3`) doğrusallığı bozuyor. Şeridi rakamdan çıkarmak (`min(w,h) >= 4`; gerçek `1` 6 px) uygulanmadı. Zincir geri alındığı için bunu ancak yeni bir ölçümle dene.
- Raster plakada eksik: 6.8, 8, 50.
- `dur` yazma.
