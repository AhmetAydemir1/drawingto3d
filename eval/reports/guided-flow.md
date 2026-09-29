# Kullanıcı yönlendirmeli PDF → STEP: ilk uygulama

2026-09-28. PLAN Bölüm 23 geçerlidir. Bölüm 23-A'nın tarayıcı kabul turu **tamamlandı** (aşağıda); genel
PDF→STEP hedefi tamamlanmış sayılmaz.

## Çalışan yol

`/guided`: PDF/PNG/JPG açma, iki noktayla kalibrasyon, bulunan kapalı çizgi/yay/daire konturunu seçme, kalınlık,
dairesel geçişli delik ve kör cep, taslak STEP ve STL önizleme. Model çağrısı veya indirme yok. GeneralPlan v1
sözleşmesi ve CAD derleyicisi değiştirilmedi.

Kararlar çizim SHA-256 özetiyle atomik kaydedilir. Revizyon, geri alma, URL ile yeniden açma, CAD hatasında
kararları koruma, sunucu başlangıcında yarıda kalan üretimi işaretleme eklendi. Karar değişikliği eski STEP
bağlantısını kaldırır; geç biten üretim yeni kararlara bağlanamaz.

## Kanıt

- **§23-A kabul turu (temiz oturum, gerçek tarayıcı, 2026-09-28):** oturum
  `out/guided/1ad6f871e3fc4021bfbc5763f8f17b5e`, çizim `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`.
  Dosya yükleme → **iki noktalı kalibrasyon gerçek tıklamayla** (787,6 px = okumanın kendi `1 00,00` satırı, değer
  100 mm) → **kontur tıklamayla** (`outline_1`) → **kalınlık "Kalınlığı kaydet" düğmesiyle** (15) → **4 × Ø6,8
  geçişli delik ve Ø50 kör cep (derinlik 8) daire tıklaması ve klavye ile** → taslak onayı → **üret** (geometri
  denetimi geçti) → **indir** (tarayıcının indirdiği `part.step` sunucudaki çıktıyla SHA-256 birebir:
  `e7f2756a…76ce`) → **yeniden aç** (kararlar, bağlantılar, önizleme, 27 satır günlük) → **geri al** (son karar
  döndü, eski STEP/plan/denetim bağlantıları kaldırıldı). Oturum günlüğüne göre **2 dk 48 sn**, 16 kullanıcı
  karar eylemi (11 düzenleme, 2 onay, 1 veto, 2 geri alma) — bu tur her kararı elle girdi.
- **Bağımsız geometrik doğrulama** (referans yalnız karşılaştırmada): üretilen katı **119,9957 × 79,9865 ×
  15,0000 mm**, hacim **124 797,96 mm³**; dört delik r=3,4 merkezleri (10;10)(10;70)(110;10)(110;70), z 0→15;
  cep r=25,0 taban z=7 → **derinlik 8 mm**, merkez (60;40) ↔ referans `plate with a pocket.STEP`: 120 × 80 × 15 mm,
  124 825,42 mm³ (**fark %0,022**), cep aynı, köşe yuvarlatmaları r≈9,97 ↔ r=10. Referansın kendi delikleri yarık
  olarak duruyor (r=3,4 çiftleri 4,33 mm aralık), pafta düz daire çiziyor — pafta↔referans sürüm farkı; akış
  paftanın çizdiğini kurar.
- **Bu turda bulunan ve düzeltilen iki arayüz sorunu:** (1) büyük dairenin ortasına tıklamak seçmiyordu (yakalama
  yalnız kenara 18 px mesafeyle çalışıyordu; Ø50 cep için yarıçap 197 px) → artık dairenin içine tıklama **en küçük
  kapsayan daireyi** seçer; (2) kör cep derinlik alanı tür "geçişli" iken gizli ama yazılabilirdi ve yazılan değer
  sessizce yok sayılıyordu → artık `disabled` ve boşaltılır. İkisi de tarayıcıda yeniden sınandı.
- Gerçek PDF üretimi (önceki tur): dört delik ve kör cep, 11 işlem, geçerli tek katı; hacim farkı %0,022.
  Tam özellik eşdeğerliği iddiası yok.
- Testler: tam takım **567 geçti** (2026-09-28); bu dilimde `test_raster.py` **12**, `test_guided.py` **24**,
  `test_catalog_cli + test_chain_model` **36** geçti. İki eski kırık kapandı: katalog CLI'de korumasız `getattr`
  (§23-C23) ve rasterda sahte bir yayı geri alan ikinci kopya tolerans (§23-C27/C28).
- **Raster yay okuması ve eğri kontur (2026-09-28):** `raster.py` zayıf Hough geçişini açısal destek ve kambur
  kapılarıyla süzdü; yay halkası **bütün mürekkep koşusundan** uydurulur (kısa eksen hatası %2,8 → %0,95);
  protokol **işaretli süpürme** taşır (`geo.py`, `general.py`, `guided.py`) — bir konturun içe ve dışa bakan
  iki kamburu da katıya girer. Sentetik stadyum paftası ürün yolundan geçti: **1 geçerli katı,
  {10,0 / 23,772 / 83,709} mm, 17,825 cm³, 8 yüz = 4 düzlem + 4 silindir** (API probu; taslak).
- **Dört gerçek raster paftada parça ölçeğinde konturlar (2026-09-28):** Exercise_51 420×838, Exercise 17
  557×513, Flange 269×415, my_part.jpg 315×238 px — ilk kez *en büyük* kutu ölçülerek (ilk ölçümüm "ilk dört
  kutu"yu en büyük sanmıştı, §23-C24). Zincirin raster birleşim toleransı ölçülüyor: 36 px hem az kontur
  (run6) hem sel (run7) üretebiliyor; süpürme `/tmp/sweep-tol.txt` (§23-C32).

JSON kanıt: `guided-flow-evidence.json`; günlükler: `out/guided-dev/pytest-*.txt`, oturum günlüğü
`out/guided/<token>/session.json`.

## Kalan kabul ve tek sonraki iş

**A kapandı** (yukarıdaki tarayıcı turu). **B'nin birinci dilimi kodlandı:** kullanıcı basılı bir ölçüyü
çizimdeki iki uca bağlar; ölçek bütün bağlardan en küçük karelerle çözülür, her bağın çizili karşılığı ve sapması
panelde ve planda durur, çelişen bağ soru olur ve üretimi durdurur, bağlanmayan özellikler taslak olarak
etiketlenir (`src/drawingto3d/sketch.py`, `guided.py`, `guided.html/js`, `tests/test_sketch.py`).

Sıradaki iş **B-2:** bağı *konuma* çevirmek — kenar-kenar ve merkez-kenar bağlarıyla profil köşelerini ve delik
merkezlerini kesin ölçüye oturtmak (ölçek değil konum), açık konturu kullanıcıya gösterip kapattırmak; ardından
aynı akışı geliştirmede hiç görülmemiş bir paftada bağımsız dış ölçü/delik konumu/derinlik/hacim ölçümüyle
sınamak. İlk parçanın bağımsız doğrulaması plakada yapıldı (119,9957 × 79,9865 × 15 mm ↔ referans 120 × 80 ×
15 mm; 80 mm bağıyla 120,0199 × 80,0027 × 15 mm) — bu, B-2'nin referans adımıdır.

## Sınırlar

İlk sayfa ve bulunan kapalı konturlar destekleniyor. Açık konturu tamamlama, kesin ölçü kısıtları, görünüş
eşleme, dönel parçalar ve serbest yüzeyler henüz yok. Yay birleşimleri köşe/ara-nokta kurallarıyla destekleniyor; kapatma toleransı hâlâ ölçülüyor (§23-C30/C32). Ölçü adaylarına antet
sayıları, daire adaylarına diğer görünüşlerin şekilleri karışabilir. Raster giriş kabulü, genel raster başarı
kanıtı değildir. Kullanıcı süre kazancı ölçülmedi. Eğitim başlatılmadı. Kontur ve delik merkezleri hâlâ pikselden
izlenen taslaktır; kalınlık ve girilen çap/derinlik kullanıcı kararıdır.

Eski `mapping_basis=value` kimlik puanı bağımsız doğruluk değildir; aynı uzunlukta yanlış kenarı doğru sayabilir.
O sayılar yeni ürünün kabul ölçütü değildir.

## Çalıştırma

Proje kökünde:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d.app
```

`http://127.0.0.1:8765/guided` adresini aç. Oturum dosyaları `out/guided/` altındadır; adres `?session=<token>`
ile yeniden açılır, henüz oturum listesi yok.

### §8.6 TASARIMI (P03'un kalan tek kod maddesi) — 2026-09-29 04:56

**Gereksinim (arsiv PLAN'dan birebir):** "Gorus ekseni/orijini kullaniciya gosterilsin; dondurulmus paftada
cerceve karar olarak kaydedilsin, sayfa X'i parca X'i varsayilmasin (§8.6)."

**Kodda simdi ne var (okundu):**
- `observe.Frame(width, height, dpi, origin='top-left', y_axis='down')` — yalniz raster cercevesi; **parca eksen
  yonu yok**.
- `observe.SourceRef.rotation` (PDF `/Rotate`) — kayitli ama hicbir karar/urun onu kullanmiyor.
- `proposal._frame_loops(loops, page_width, page_height)` — pafta cercevesini **buluyor** ama yalnizca
  **atlamak** icin ("frame-only": kapali dis kontur bulunamadi). Cerceve bir **urun** olarak verilmiyor.
- Donusum yolu saf olcek: testlerdeki `mm(point) = (point - CENTRE)/SCALE` ve `user_dimensions` — yani
  **sayfa X = parca X varsayimi** tam da §8.6'nin yasakladigi sey.

**Kabul listesi (§8.6 icin "dogrulandi" demek):**
1. `observations` payload'i **pafta cercevesini** (dikdortgen + kendi yonu) ve **gorunus eksenlerini** urun
   olarak tasir; bulunamazsa "cerceve bulunamadi" gerekcesi (uydurma yok).
2. Donuk paftada cerceve **gorsel kenarlardan degil paftanin kendi cercevesinden** kurulur; donukluk urunde
   gorunur (hangi yon parca X'i) ve sayfa X = parca X varsayimi **kalkar**.
3. UI cerceveyi ve eksen yonunu **gosterir**; kullanici onaylar; onay **karar olarak kaydedilir**
   (`geometry_version` ile), onaysizken `questions()` sorar.
4. Cekirdek (`user_dimensions`/`make_plan`) mm'ye cevirirken **onaylanmis gorunusu** uygular; onay yoksa
   varsayim yapmaz.
5. Donuk pafta testi: ayni cizim 0° ve 90° donukken olculen mm degerleri **ayni** cikar (eksen takasi ile).

**Dilim plani (kucuk, olculebilir):**
- **§8.6-a** `observe`/`proposal`: cerceve + eksen yonu urunu (model-free; rotasyon sentetik paftayla test).
- **§8.6-b** UI gosterim + onay karari (gercek tarayici kabulu; karar alani `view`).
- **§8.6-c** cekirdek donusumu onaylanmis gorunuse baglar + donuk pafta testi.

**Durum: TASARIM (dogrulanmis dilim degil).** Ilk is: §8.6-a. Sonra P03 toptan kabul -> `PLAN.md`de P03
"dogrulandi" -> P04 (100x100 kare cift-bag tekrari; korner bagi kapisi).

### §8.6-a INDI: pafta cercevesi + eksen yonu urunu (2026-09-29 05:06)

**Ne indi:** `observe.SheetFrame`/`SheetAxis` + `rotation_axes()` + `sheet_frame()` (saf fonksiyon, pdfium
gerekmez); `Observations.sheet_frame` alani; `observe()` urunu yaziyor; `raster.observe_raster` ayni alani
**durust "bulunamadi"** gerekcesiyle dolduruyor (raster paftada vektor cerceve yok); `guided.drawing_options`
izlemenin **atladigi pafta cercevesi dongusunden** urunu yayinliyor (`options["sheet_frame"]`).

**Kanit (sentetik):** `tests/test_sheet_frame.py` -> **10 passed / 0,30 s**. Icmali: duz pafta cercevesi+eksen
✓; **donuk pafta invaryanti** (ayni parca kenari 0° ve 90° paftada *ayni* mm deltasini veriyor; sayfa deltalari
farkli) ✓; cerceve yoksa durust gerekce + sayfa eksenleri ✓; 7° egik cerceve kendi acisini soyluyor ve
"gorsel kenarlardan degil + kullanici onayi" notu ✓; `/Rotate` ceyrek tur tablosu ✓; portre cercevesi
regresyonu ✓; `drawing_options` atlanan donguden urunu yayinliyor ✓.

**Kanit (gercek paftalar):** Plate `outline_0` kapsam %93,3×%90,5, aci 0,0°, hizali ✓; `2/Drawing.pdf`
(portre 1653×2339) `outline_0` kapsam %90,5×%96,6 ✓ aci 0,0° ✓; `3/Exercise 17.PNG` (raster) ->
durust "kapali cerceve yolu bulunamadi" + kullanici onayi notu ✓.

**Gercek veriyle bulunan KUSUR (duzeltildi):** ilk surum cercevenin yalniz **uzun kenarini** sayfa x ekseniyle
karsilastiriyordu; portre paftada uzun kenar dikey oldugu icin `2/Drawing.pdf` "hizali degil / 90° sapma"
diyordu — duz pafta icin yanlis "donuk pafta" notu. Duzeltme: cercevenin **iki kenar yonu** de sayfa
eksenlerine karsi olculur; regresyon testi eklendi (portre cercevesi hizali ✓).

**Durust sinir (kayitli):** `observe` seviyesinde (ham *yol* duzeyi) gercek paftalarda cerceve bulunamiyor —
Plate 209 yolun 0'i, `Drawing.pdf` 31 kapali yolun 0'i %80×%80 esigini geciyor; cunku pafta cercevesi tek bir
kapali yol degil, **ayri cizgi nesnelerinden zincirlenen bir dongu**. Calisan urun bu yuzden
`drawing_options`'taki **dongu duzeyli** urun; `observe`'daki yol duzeyli urun durustce "bulunamadi" diyor
(ikisi de gerekceli). Ayrica `Exercise 17.PNG` raster oldugu icin yol duzeyinde de dongu duzeyinde de yok.

**Sirada:** §8.6-b (arayuz gosterimi + kullanicinin onayladigi `view` karari), sonra §8.6-c (cekirdek mm
donusumunun onaylanmis gorunuse baglanmasi + donuk pafta testi). §8.6 toptan "dogrulandi" DEGIL.

### §8.6-b INDI ve ARAYUZ KABULU GECTI (2026-09-29 05:15)

**Ne indi:** `Decisions.view` (`ViewConfirm`: `x_page`/`y_page` birim vektörleri, `frame_rect`, `source`,
`geometry_version`); `validate_decisions` birim/dik/kapsam denetimi; `questions()` **yalnizca** pafta
cercevesi bulunamadi, cerceve hizali degil ya da kaynak donukse soruyor (duz paftada sormuyor); onaylanmis
gorus okumayla uyusmuyorsa "yeniden onaylanmalı" diyor. `guided.html`: "Görüş yönü (PLAN §8.6)" bloktası
(onay kutusu + kaydet dugmesi + "çerçeveyi ve eksenleri çizimde göster"). `guided.js`: `renderView()` +
onay gonderimi + tuvale **kesikli mor çerçeve ve iki eksen oku** çizimi.

**Arayüz kabulü (GERCEK tarayici, oturum `p03b2`):**
- Plaka yuklendi -> panel satiri: "çerçeve 78 / 79 / 2260 / 1575 px; öneri: X sağ, Y yukarı · pafta çerçevesi
  outline_0: kapalı yol sayfanın %93.3×%90.5'ini kaplıyor; kenarları sayfa eksenlerinden en fazla 0.0°
  sapıyor (sayfa eksenlerine 2° içinde hizalı)" — ve **tuvalde kesikli mor pafta çerçevesi görünüyor**.
- Onay kutusu **gerçek tıklamayla** isaretlendi; "Görüş yönünü kaydet" **gerçek tıklamayla** -> durum
  **"Karar kaydedildi."** -> satir "Onaylandı: X sağ, Y yukarı · çerçeve 78 / 79 / 2260 / 1575 px · kaynak
  sheet_frame."
- **Kayit kaniti:** oturum `3bb37c58529e4083a85e335d7f096129`, kayit 1, `decisions.view` =
  `{"x_page":[1.0,0.0],"y_page":[0.0,-1.0],"frame_rect":[78.07,78.84,2259.57,1575.37],"source":"sheet_frame",
  "geometry_version":3}`.
- Soru **gorunmuyor** (duz + cercevesi hizali plaka - tasarim geregi) ✓.

**Testler:** `tests/test_view_decision.py` (8 test) + `tests/test_sheet_frame.py` (10) + `test_guided_html.py`
-> **24 passed / 2,70 s**; ardindan `test_guided.py` + `test_guided_proposals.py` ile birlikte
**63 passed / 54,43 s**.

**Bu dilimde cikan regresyon ve dersi (kayitli):** `questions()` gorus sorusunu ekleyince **7 build testi**
dustu: fixture'larin sentetik paftalarinda **cerceve yoktu** (gercek bir paftada olmayan durum) ve fixture'in
parca konturu cerceve dongusu indeksi aldigi icin `outline_0` -> `outline_1` kaydi. Duzeltme: fixture'lara
gercek pafta gibi **cerceve cizildi** ve parca **sekille** secildi (`kind == "wire"` + genislik 100 px);
uretim kurali gevsetilmedi. Ayni ders skill'in `references/session-workflow-and-handoff.md` dosyasina yazildi.

**Durust acik kalem:** "cercevesi bulunamayan paftada arayuz sorusu" kontrolu gercek tarayicida
**tamamlanamadi** — raster (Exercise 17.PNG) okumasi surerken headless tarayici oturumu kapandi
(`no close frame received or sent`). Soru API testinde kanitli (`test_a_sheet_whose_frame_is_missing_is_asked_
with_the_proposal`); arayuz tarafinda ayni `render()` yolundan gosteriliyor ama ekran kaniti yok. Takip isi.

**Sirada:** §8.6-c (cekirdek mm donusumunun onaylanmis gorunuse baglanmasi + donuk pafta testi), sonra §8.6
toptan karari ve P03 kabulu -> P04-a…f. §8.6 hala toptan "dogrulandi" DEGIL.

### §8.6-c-1 INDI: cekirdek "sayfa X'i parça X'i" varsaymiyor + §8.6-c-2 plani (2026-09-29 05:17)

**Ne indi:** `view_transform(decisions, options)` — paftanin kendi eksenlerini sayfa cercevesinde birim
vektor olarak verir; **once kullanicinin onayladigi gorus**, yoksa yalnizca *urun* sayfa eksenlerini pafta
ekseni yapmaya hak veriyorsa (cerceve bulundu + hizali + kaynak donuk degil) kimlik eksenleri; aksi halde
**None**. `is_page_identity()` ile ayrim. `make_plan` artik: (a) gorus turetilemiyorsa **soruda duruyor**
("Görüş eksenini ve çerçeveyi onaylayın…"; varsayim yok), (b) kullanici **donuk** bir gorus onayladiysa
uretim **duruyor** ("döndürülmüş pafta üretimi ayrı dilimde (§8.6-c-2) — sayfa eksenleri parça ekseni
sayılmadı"), (c) duz pafta **aynen eskisi gibi** uretiliyor (plan sayilari degismedi).

**Kanit:** `tests/test_view_decision.py` -> **15 passed / 4,95 s** (yeni: gorus turetilemeyince build soruda
duruyor ✓; `view_transform` onay > urun sirasi ✓; donuk onay build'i durduruyor ✓; duz plaka plani gorus
engeline takilmiyor ✓). §8.6-b genis seti: **115 passed / 105,37 s**.

**§8.6-c-2 (siradaki dilim, kayitli plan):** onaylanmis gorusu *uygulamak*: `make_plan`'in derin kopyasinda
geometriyi paftanin kendi cercevesine tasi — `u = p·x_axis`, `v = p·y_axis`, `origin = [min u, min v]` ve
`xy()`'nin y-kurali ile `user_dimensions`'taki uc geri-donusumle **birlikte** (kimlik goruste bugunku
sayilar birebir korunmali; korpusta donuk pafta olmadigi icin kanit sentetik olacak: ayni parca duz ve 90°
donuk paftada **ayni plan parametrelerini** vermeli). Yalniz **ceyrek tur** gorunusler; egik gorus icin yay
acilarinin eslenmesi ayri dilim. Kapi: plaka/plastik/flange karşılaştirmalari degismemeli.

**Durust sinirlar:** (1) donuk pafta su an *uretilmiyor* (varsayim yerine ret — bilincli); (2) korpusta
donuk pafta yok, bu yuzden donuk esleme yalniz sentetikle dogrulanabilir; (3) raster paftada arayuz
sorusunun ekran kaniti hala yok (§8.6-b kaydi). §8.6 toptan "dogrulandi" DEGIL.

### §8.6-c-2 TASARIM KESINLESTI (kod yazilmadi) — 2026-09-29 05:18

Gozden gecirilen kod yuzeyleri: `make_plan`'in `origin=[min x, max y]` + `xy()` y-kurali (iki yerde) ve
`user_dimensions` icindeki **uc geri-donusum** (satir ~929, ~937-938: `origin[1] - value*scale`).

**Secilen kural (yaziyla sabitlendi, boylece yeniden turetilmesi gerekmez):** pafta cercevesine gecis
`u = p·x_axis`, `v = p·y_axis` — yani **v paftanin +y yonudur** (yukari), sayfa gibi asagi degil. Bu yuzden:
- `origin = [min u, min v]`; plan x = `(u - origin[0])/scale`, plan y = `(v - origin[1])/scale` (y'de **artik
  ters cevirme yok**, v zaten yukari).
- mm -> geri donusum: `u = origin[0] + x*scale`, `v = origin[1] + y*scale` (eskiden y eksiydi).
- **Kimlik goruste sayilar birebir ayni kalir** (v = -page_y => plan y = (max page_y - page_y)/scale).
- Yay acilari: pafta cercevesi donerse kanonik aci **Delta** kadar kayar; Delta = `atan2(-x_axis[1], x_axis[0])`
  (or. x_axis=[0,1] => Delta = -90°). Yalniz ceyrek tur gorunusler; egik gorus (ayni zamanda yaylar) ayri dilim.
- **Ayna reddi:** det(x_axis, y_axis) isaretini korumayan cift (or. x=[1,0], y=[0,1]) bu dilimde
  desteklenmiyor -> `view_transform` acik ret vermeli (sessizce uretmek yok).

**Dikkat edilecek cagri yerleri:** `user_dimensions`'i dogrudan cagiran testler
(`tests/test_measure_meaning.py`, `tests/test_stable_identities.py`) `origin`'i **eski (sayfa) kuralina gore**
veriyor; yeni kuralda `origin` bir (u,v) cercevesidir -> bu testlerin origin'i `[min u, min v]` olacak sekilde
guncellenmeli, aksi halde `moved` mesafeleri iki farkli cerceveden olculur (test yanlis yere bakar).

**Kanit plani:** `tests/test_view_core.py` — (1) ayni parcanin duz ve 90° donuk paftada *ayni plan
parametrelerini* vermesi (donuk kayit = koordinat takasi: sayfa (x,y) -> (y,x), sayfa olculeri 300x200 ->
200x300, gorus x=[0,1], y=[1,0], kalibrasyon da takas edilir, deger 50 mm kalir); (2) ayna cifti reddi;
(3) kimlik goruste plan sayilari degismiyor. **Kapi:** plaka/plastik/flange karşılaştirmalari ve
`test_guided.py`'nin plaka planlari degismemeli.

### §8.6-c-2 INDI: onaylanmis gorus cekirdekte UYGULANIYOR (2026-09-29 05:21)

**Ne indi:** `_view_map(options, d, axes)` — yalnizca o `make_plan` cagrisinin **derin kopyasini** paftanin
kendi cercevesine tasir (profiller/kenarlar/daireler/ilkel geometri + kararlardaki bag uclari ve kalibrasyon
noktalari); ardindan tani **yeni cercevede** yeniden kosar. Kimlik goruste harita atlanir (bit-bit ayni
sayilar). Donuk gorus artik ret degil, **uygulama**; ayna olusturan eksen cifti (det isareti ters) acik
**ret**. Yay acilari ceyrek turda `+turn_page` kadar kayar.

**Kritik tasarim duzeltmesi (geri alinan bir deneme):** ilk denemede `(u,v)` cercevesini *y-yukari* yaptim ve
`origin`/`xy()`/`user_dimensions`'taki y isaretini cevirdim — sonra **`sketch_constraints.py:137`**'nin
(paralel ajanin modulu) `(origin[1] - y)/scale` okudugu goruldu: yeni cerceve o modulu **aynalardi**. Cozum:
cerceve **sayfa gibi** (y-asagi) kalir; paftanin +y'si haritada `-v` eksenine oturur. Boylece kimlik goruste
v = sayfa y'si ve **tum sayilar birebir ayni**; komsu modul hic degismez. Ders skill'e yazildi.

**Kanit:** `tests/test_view_core.py` -> **30 passed / 4,52 s** (tum dosya grubu). Icmali: ayni pafta duz ve 90°
donukken **ayni kenar geometrisi** (kenar vektorleri; parametre adlari degil — zincir baska koseden basliyor);
ayna ret; kimlik goruste hicbir parametre oynamiyor; haritanin birim kaniti (nokta + kanonik aci kaymasi,
`edge a 90 -> 180`, `b 0 -> 90`). Kaldirilan eski test: "donuk gorus ret" (sozlesme degisti, `test_view_core`
yerini aldi). Genis set kosuyor (`proc_8a6683145ae3`).

**Durust sinirlar:** (1) donuk pafta kaniti **sentetik** — korpusta donuk pafta yok; (2) yaylarin uctan uca
donukluk kaniti yok (birim seviyede kanitli); (3) egik (ceyrek tur olmayan) gorus hala ret; (4) raster
paftada arayuz sorusunun ekran kaniti yok (§8.6-b). §8.6 toptan "dogrulandi" DEGIL.

### §8.6 KABUL LISTESI — madde madde kanit (2026-09-29 05:23)

Genis set yesil: **122 passed / 86,93 s** (13 dosya; `test_guided.py`'nin plaka planlari ve paralel ajanin
`test_sketch_constraints.py` dahil). Kabul listesi:

1. **Urun pafta cercevesini ve eksenleri tasir** — `Observations.sheet_frame` + `options["sheet_frame"]`;
   sentetik **10 passed**; gercek pafta: Plate `outline_0` %93,3x%90,5 -> 0,0°; `2/Drawing.pdf` portre
   %90,5x%96,6; `Exercise 17.PNG` -> durust "bulunamadi + kullanici onayi". ✓
2. **Donuk paftada cerceve paftanin kendi cercevesinden; sayfa X = parca X varsayimi kalkti** — §8.6-c-1
   (turetilemezse soruda durur) + §8.6-c-2 (onaylanmis gorus uygulanir); donuk pafta sentetik kanitla ayni
   kenar geometrisini veriyor. ✓ (kanit sentetik — korpusta donuk pafta yok, kayitli)
3. **Arayuz gosterir, kullanici onaylar, onay karar olarak kaydedilir** — §8.6-b gercek tarayici kabulu
   (oturum `3bb37c58529e4083a85e335d7f096129`): satir "cerceve 78 / 79 / 2260 / 1575 px; oneri: X sag, Y
   yukari - %93.3x%90.5 - 0.0° sapiyor" -> gercek tiklama ile kaydet -> `decisions.view` yazildi
   (`x_page`, `y_page`, `frame_rect`, `source`, `geometry_version`). ✓
4. **Cekirdek onayi uygular; onay yoksa varsaymaz** — §8.6-c-1: turetilemeyen goruste build soruda durur;
   §8.6-c-2: onayli donuk goruste harita uygulanir, kimlik goruste sayilar birebir korunur; ayna cifti ret. ✓
5. **Donuk pafta testi: ayni cizim 0° ve 90°'de ayni olculen mm'yi verir** — `test_view_core.py::`
   `test_a_rotated_sheet_builds_the_same_plan_as_the_upright_one` (kenar vektorleri esit; zincir sirasi
   bagimsiz). ✓ (sentetik; yaylarin uctan uca donuklugu birim seviyede kanitli)

**Durust sinirlar (kapanmadi):** egik (ceyrek tur olmayan) gorus ret; raster paftada arayuz sorusunun ekran
kaniti yok (§8.6-b takip); yayli donuk kontur uctan uca test edilmedi.

**P03 durumu:** kabul listesi (X/Y, yon, mm/inch, profil degisimi, silinen kenar, eski surum) + P03-b-1/b-2 +
§8.6'in tamami tamam — **tam takim kosuyor** (`proc_e154433e97f1`); yesil gelirse P03 "dogrulandi".

### P03 DOGRULANDI + §8.6 DOGRULANDI (2026-09-29 05:39)

**Tam takim: 669 passed / 1025,02 s** (§8.6-a/b/c-1/c-2 sonrasi; onceki yesil 641 — 28 yeni test). Kabul
listesi madde madde kanitlandi (bkz. ustteki bolum) + P03 kabul listesi (X/Y, yon, mm/inch, profil degisimi,
silinen kenar, eski surum) + P03-b-1/b-2 arayuz kabulu + §8.6-b gercek tarayici kabulu.

**P03: DOGRULANDI. §8.6: DOGRULANDI** — kayitli durust sinirlarla (egik gorus ret; raster paftada arayuz
sorusunun ekran kaniti yok; yayli donuk kontur uctan uca test edilmedi; donuk pafta kaniti sentetik).

**Kapilar (P03 boyunca degismedi):** plate-pocket-1 7/7, plastic 11/11, exercise-1-vector 13/13,
exercise-12 19/20, flange 4/13; `check_tables` 21 okundu / 0 tutmuyor; `baseline_report --check` yesil.
Sirasi: **P04-a…f** (100x100 kare cift-bag tekrari — kose-bagi kapisi engeli; P04-c P01-c rapor gorunurlugu).

### P04-a INDI: olcek = kalibrasyon; desteklenen X/Y bagi eski ortak-olcek kapisina takilmaz (2026-09-29 05:43)

**Once olcum (kod degismeden, 600x500 sentetik pafta, kalibrasyon 200 px = 100 mm => 2 px/mm, govde 200 px):**
| Durum | `sketch.px_per_mm` / kaynak | Govde | Kapi |
|---|---|---|---|
| Bag yok | 2,0 / calibration | **100 mm** | soru yok, plan var |
| Yalniz merkez bagi (cekili 200 px, basili 50 mm) | **4,0 / bindings** | **50 mm** (F12) | soru yok — sessizce yanlis |
| Kose bagi X=50 / Y=30 | 6,655 / bindings, 2 conflicts | plan yok | "tek olcek tutmuyor" kapisi (F13) |

**Kok:** `make_plan` uretim olcegini `diagnostics["px_per_mm"]`ten aliyordu; o alan `fit_scale(bindings)` sonucuydu
=> tek bir bag tum govdeyi yeniden olceklendiriyordu. Kapi: `bindings_solvable` yalniz `centre` uclarini kabul
ediyordu (profil elinde degil diye) => gecerli kose bagi "tek olcek" sorusuna takiliyordu.

**Ne indi (`guided.py`):**
1. `sketch_diagnostics`: ust duzey `px_per_mm`/`source` artik **kalibrasyondan**; eski uyum **`sketch["fit"]`**
   altinda rapor olarak duruyor (satirlar, artıklar, conflicts, consistent).
2. `make_plan`: uretim olcegi **yalniz kalibrasyondan**; baglar olcegi degistirmez.
3. Tek cozucu: `binding_reference(profile, end)` modul duzeyine cikarildi; `user_dimensions` ve yeni
   `bindings_solvable(decisions, options)` **ayni** cozucuyu kullaniyor (PLAN P04 madde 3/4: kopya cozumleyici yok).
4. `bindings_solvable`: desteklenen X/Y bagi (iki cozulebilir kose ya da iki daire merkezi) **olculebilir**
   sayilir; uyum artigi artik engel degil. Cozulemeyen uc / desteklenmeyen tur / ayni uca bag hala engel.
5. `make_plan`: cozum durumu `unsupported` ise **uretim durur** (F14'un kapisi P04-b'den one alindi; aksi halde
   F13 duzeltmesi "desteklenmeyen bag sessizce yok sayilir" deligini acardi) — PLAN madde 6 zaten bunu sart kosuyor.

**Kanit:** `tests/test_guided.py` **28 passed / 38,33 s**. Iki eski test **sozlesme degistigi icin** yeniden yazildi
(eskiden uyum olcegi uretim olcegiydi):
- `test_a_bound_measurement_moves_the_geometry_and_the_scale_stays_the_calibrations`: 40 mm bagi geometriyi
  hareket ettirir (yukseklik 40 mm, genislik kalibrasyonun 50 mm'si); `source=calibration`, `px_per_mm=2,0`,
  `sketch["fit"]["source"]=bindings` (tani), plan parametresi `binding_0` `user` 40,0, varsayim metni "kalibrasyonundan".
- `test_supported_corner_ties_are_not_blocked_by_the_fitted_scale`: iki gecerli kose bagi engellenmez; cozum
  50x40 mm; gecersiz referans (`edge:99`) hala "yeniden baglanmali" + build reddi.
- YENI `test_a_lone_centre_tie_does_not_shrink_the_body` (F12'nin kanonik vakasi): 100 mm govde, yalniz merkez
  bagi -> govde **100x60 mm kalir**, `px_per_mm=1,0`.
Iddialar parametre *adlariyla* degil **plan bbox**'u ve cozulen kenar vektorleriyle kuruldu (zincir sirasindan bagimsiz).

**Durust sinirlar:** `unsupported`in kapisi P04-b'nin maddesi — one alindi ve P04-b kapanisinda tamamina
bakilacak (arc bagi ret mesajlari vb.). Daire merkezi bagi icin id dogrulamasi hala `unresolved_bindings`te
(tek cozucuya tasinmadi); genis set kosuyor (`proc_c4308a8977cf`).

### P04-a: cozulen MERKEZ henuz CAD'e uygulanmiyor — P04-f'nin ilk maddesi (2026-09-29 05:46)

Genis set yesil gelirken `test_guided_geometry_state.py` tek kirmizi verdi: "bagli olcu geometriyi hic
degistirmedi". Kok, P04-a'nin bir hatasi degil, ortaya cikan **gercek bosluk**: eski kod bagi *olcege*
yansittigi icin plan degisiyordu (F12'nin ta kendisi); olcek kalibrasyona sabitlenince merkez bagi yalniz
**cozum raporunda** kaliyor.

Olculdu (plaka, kalibrasyon 10,568 px/mm, bagi 120 mm, cizili 472,53 px = 44,71 mm):
- `user_dimensions` durumu **underconstrained**, `dof=11`, notlar: "Serbestlik sayisi yalniz secili daire
  merkezlerini kapsar."
- Cozulen merkezler: `g9` [435,56 / 658,22] sabit, `g12` 1130,75 -> **1926,39** px => mesafe **1268,17 px
  = 120,000 mm** ✓ (core bagi gercekten uyguluyor).
- Ama plan/STEP izlenen merkezi kullaniyor (`hole_0_x/y` degismedi) => **"yeni merkez yalniz raporda kaliyor"**
  (PLAN P04 madde 10 + P04-f kabulu: "Secili deligin merkezi ... STEP'teki silindirin merkezi yeni yerdedir").

**Karar:** P04-a'da merkez uygulamasi yapilmaz (P04-f'nin isi); test iddiasi cozulen merkeze baglandi ve
bosluk burada acikca kayitli. P04-f baslarken **ilk madde** bu: cozulen merkezleri kesime/STEP'e tasi.
Ayrica not: ayni gap `test_guided_geometry_migration`/`test_measure_meaning` gibi setlerde gorunmez, cunku
onlar CAD ciktisindaki merkezi denetlemiyor.
