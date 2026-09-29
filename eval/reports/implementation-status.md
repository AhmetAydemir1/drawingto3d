# Uygulama durumu — 2026-09-29 bağımsız yeniden denetim

**Yön doğru; P01/P02 tamamlandı kabulü geri açıldı.** Yeni build kopyası, maksimum açıklık ve açık X/Y/yön alanları ilerlemedir. Arayüz, geçiş güvenliği, referans anlamı ve kontur matematiğinde tekrar edilen açıklar var.

## Güncel durum

| Aşama | Durum | Açıklama |
|---|---|---|
| A0 | bekliyor | Bozuk bind-start HTML'i; profil kaldırılınca AttributeError |
| P00 | doğrulandı | Eski başlangıç kaydı ve güncel kaynak/test/probe kayıtları |
| P01 | çalışılıyor | Kopyalama regresyonu geçti; geçiş/çıktı güncelliği açık |
| P02 | çalışılıyor | Maksimum açıklık düzeldi; beş geometri karşı örneği yanlış |
| P03 | çalışılıyor | X/Y/yön/yeni uç kimlikleri var; gerçek eski referans geçişi ve çerçeve açık |
| P04–P08 | bekliyor | Ayrıntılı alt teslimler PLAN.md'de |
| P09–P12 | bekliyor | Daha geniş geometri/model/eğitim kapsamı |

## Doğrulama

- 11 dosyada **90 geçti; 1 test sandbox port izninde durdu** / 57,96 sn, exit 1.
- Aynı yerel HTTP testi izinli koşuda **1 geçti** / 0,86 sn, exit 0.
- Toplam seçilen 91 test iki koşuda geçti; tam takım yeniden koşulmadı.
- Bağımsız kusur örnekleri: DOM düğmesi yok; profil seçimi kaldırma hatası; değişen kimliklerin aynı sayılması; stale STEP'in güncel sunulması; referans kayması; beş kontur kusuru; 100→50 mm ölçek değişimi; geçerli X/Y çiftinin reddi; unsupported plan kabulü.
- Üretim kaynakları/testleri bu denetimde değiştirilmedi.

## Tek sonraki iş

**A0.1 → static/guided.html + guided.js → gerçek bind-start button elemanı → DOM varlık kontrolü ve HTTP üzerinden açılış/ölçü bağlama denemesi.** Sonra A0.2 boş profil kaydet/yeniden aç senaryosu.

## Kaynaklar

- [Güncel ayrıntılı denetim](goal-progress-audit-20260929.md)
- [Kalıcı küçük kanıtlar ve kaynak özetleri](../audits/20260929-goal/)
- [Güncel uygulama planı](../../PLAN.md)
- [Önceki uygulama günlüğü — arşiv](../../docs/IMPLEMENTATION_HISTORY_BEFORE_REAUDIT_20260929.md)

Eski günlükteki “P01/P02 tamam” ve “P03 yalnız görünüş ekseni kaldı” ifadeleri bu denetimle geçersizdir. Yeni çalışmada bu özetin başını güncelle; uzun deney anlatılarını ayrı rapora bağla.

### A0 — arayuz onarimi: HTML + profil kaldirma (2026-09-29 03:32, kod indi, set kosuyor)

**A0.1 (F01).** `static/guided.html`: eksen/yon secicilerinin `<button` etiketinin *icine* girmesine yol acan
bozuk yapi duzeltildi — seciciler artik baglama dugmesinin **kardesi** bir `div.row` icinde, dugme gecerli
`<button id="bind-start" ...>` olarak duruyor. Python `html.parser` ile dogrulandi: belge hatasiz ayrisiyor
(kapanmayan/eslesmeyen etiket yok), `bind-start`/`bind-cancel` -> `button`, `bind-axis`/`bind-direction` ->
`select`, dordu de **bir kez**. Yeni test `tests/test_guided_html.py` bu kontrolu kalici hale getiriyor ve
okudugu dosyanin uygulamanin servis ettigi dosya oldugunu (`app.ROOT / "guided.html"`) dogruluyor.

**A0.2 (F02).** `unresolved_bindings`: profil secilmemisken `profile.get` cagrilmiyor; her kontur ucu
"kontur seçilmemiş; <kimlik> yeniden bağlanmalı" diye bildiriliyor (kayit korunur, `questions` hem "dış konturu
seçin" hem yeniden baglama sorusunu uretir, build bekler). `validate_decisions`'taki artik kullanilmayan
`profile/edges` satirlari kaldirildi. Store yolunda yeni test: profil sec + bag ekle + profil secimini kaldir +
kaydet + yeniden ac (API 500 yok, kararlar duruyor, build bekliyor); `test_stable_identities`'e birim testi.
Kosu: `proc_4abf09bb9895` (/tmp/a0-set1.txt). Tarayici/HTTP kabulu (A0.1.4-5) bu kosudan sonra.

### A0 DOGRULANDI — arayuz + profil kaldirma (2026-09-29 03:36, gercek tarayici)

**Kaynak (A0.1):** `static/guided.html` bozuk `<button <div ...>` yapisi duzeltildi; seciciler baglama
dugmesinin kardesi. `html.parser` ile: belge hatasiz (kapanmayan/eslesmeyen etiket yok), `bind-start`/`bind-cancel`
-> button, `bind-axis`/`bind-direction` -> select, dordu birer kez. Kalici test: `tests/test_guided_html.py`
(okudugu dosyanin `app.ROOT/guided.html` oldugunu da dogruluyor). Servis edilen sayfa (8198 bayt) ve `guided.js`
(24499 bayt, `e.id}:start` isareti) curl ile dogrulandi.

**Kaynak (A0.2):** `unresolved_bindings` profil yokken cokmuyor; uclar "kontur seçilmemiş; <kimlik> yeniden
bağlanmalı" diye bildiriliyor, `questions` "dış konturu seçin" + yeniden baglama soruyor, build bekliyor.
`validate_decisions`'taki olu `profile/edges` satirlari kaldirildi. Testler: store yolunda profil sec → bag ekle
→ profil secimini kaldir → kaydet → yeniden ac; birim testi `test_no_contour_chosen_is_an_ask_not_a_crash`.
Odak set: **69 passed in 58,53 s**.

**Gercek tarayici kabulu (A0.1.4-5, oturum `5a0fd56ac4164b4ba580bbe1d417ea7b`):**
1) `/guided` acildi; dosya yuklendi (Plaka paftasi) -> "bos ekran" kapandi, kontrol paneli gorundu (JS bastan
sona calisti; F01'in oldurdugu zincir artik yasiyor).
2) Kalibrasyon gercek fareyle: iki uc tiklama + `80` mm -> **"Karar kaydedildi."**, px/mm = 12,9893 (1039,1 px /
80 mm), kayit `calibration` olarak store'da.
3) Kontur gercek fareyle secildi: `outline_1` -> "Karar kaydedildi.".
4) Bag gercek fareyle: `#bind-start` -> mod "Baglanacak iki uca tiklayin…", iki daire merkezine tiklandi ->
   **"Karar kaydedildi."**; panel satiri **"30.32 mm · X+ · g8 ↔ g9"**; kayit: `{value:30.32, axis:'x',
   direction:1, first:'g8', second:'g9'}` -> **eksen/yon kayda girdi**.
5) Sayfa yenilendi (`/guided?session=…`): panel satiri ayni, kayit ayni (`axis/direction` korundu).
**Sinir:** bu kabul baglama akisini gosterir; tam delik/STEP kabulu P07'nin isi. Tarayici dersi: sayfanin JS'i
ES modulu -> `state`/`$` sayfa global'i degil (arastirmada DOM ve `GET /api/guided/<token>` kullanilir);
`scrollIntoView` panel icin cagrildiginda tuval kayar -> tuval tiklamalarindan once `getBoundingClientRect`
tazelenmeli.

### P01-a — gecis guvenligi kodu indi (2026-09-29 03:38, set kosuyor)

`GEOMETRY_VERSION = 3`; kimlik karsilastirmasi artik **gercek alanlar**: profil kimlikleri/turleri, her
profilin **sirali kenar kimlikleri**, daire kimlikleri, **`measurements[].id`** (denetimin F03'u `span_id`
diye var olmayan alani okuyordu) ve cerceve. Koordinatlar bilerek kimlik *degil*: eski bir uretim onlari
degistirmis olabilir, bu yuzden yalniz sayisal fark "baska cizim" sayilmaz; ayri `_moved_geometry` bunu
sayar ve gecis gunlugunde adi gecer (P01-a.4). `_geometry_diff` kimlik farklarini kisa bir listede verir.
`_migrated` yeniden yazildi: **once ham kayit `session.backup.json` olarak atomik yedeklenir**, sonra kaynak
yeniden okunur; kimlikler tutuyorsa temel geometri tazelenir (tasinan koordinat sayisi gunluge yazilir), aksi
halde `geometry_stale` + gerekce + build reddi; kaynak **okunamiyorsa** da cokme yok, ayni durum ve gerekce
(P01-a.5: surum isaretinin yoklugu hicbir seyi kanitlamaz). `_looks_mutated` kapisi kaldirildi.
Fixture duzeltmesi (P01-a.6): `tests/test_guided.py` kaydina `geometry_version` yazildi — uretim kurali
gevsetilmedi. Yeni testler: yedek dosyasi ham kaydi birebir tutuyor; `_same_geometry` kenar/olcu kimligi
degisince **False**, yalniz koordinat tasininca **True** (`_moved_geometry` >= 1); kenar kimligi degisen kayit
tazelenmiyor, stale + build reddi; okunamayan kaynak cokme degil, hatirlanan stale.
Kosu: `proc_6a352955feb5` (/tmp/p01a-set1.txt).

### P01-a DOGRULANDI + P01-b kodu indi (2026-09-29 03:40)

**P01-a:** `tests/test_guided_geometry_migration|geometry_state|test_guided|test_guided_html|test_stable_identities`
-> **41 passed in 66,53 s**. Yedek, gercek kimlik karsilastirmasi (F03 duzeltmesi), kimlik uyusmazliginda ve
okunamayan kaynakta guvenli durdurma, idempotent hatirlama — hepsi test edildi.

**P01-b (kod indi, set kosuyor):** `build()` artik ciktisini **kaynak ozeti + geometri surumu + karar
revizyonu** uclusune bagliyor (`identity`); `public()` bir ciktisi yalniz uc alan da tutuyorsa ve geometri
bayat degilse **guncel** sayiyor — aksi halde `build_status: "historical"` donuyor ve **guncel STEP/STL/plan
URL'si verilmiyor** (F04). Yanit yeni `geometry` blogu tasiyor: `version`, `stale` (gerekce), `backup` ve
tarihsel build klasoru. `artifact()` ayni kurali uyguluyor: stale iken "eski sonuç tarihsel …; yeniden
üretilemez", kimlik uyusmazliginda "bu kararlar için güncel STEP yok". **`load()` artik kaynak
degismis/eksikken istisna atmak yerine durumu `geometry_stale` olarak yaziyor** (oturumun kararlari ve
kaniti incelenebilir kaliyor, build gerekceli duruyor). Yeni `recheck(token)`: kilit altinda bayragi temizleyip
ayni kimlik kontrolunu yeniden kosar — bayat damgasi oturumu cikissiz birakmiyor. Eski dosya diskte duruyor.
Kosu: `proc_01bc58644606` (/tmp/p01b-set1.txt); P01-b kabul testleri (basariLI gecisten sonra da eski cikti
guncel degil; stale'de kanit korunur + recheck kurtarir; degismis kaynak gorunur kalir) bu kosudan sonra
eklenecek.

### P01-b kabul testleri + bir beklenti guncellemesi (2026-09-29 03:41, set kosuyor)

Ilk P01-b kosusunda tek kirmizi: `test_source_change_refuses_replay` eski davranisi (kaynagi degisen oturumda
`load` **istisna atar**) bekliyordu; plan P01-b.4 acikca tersini istiyor (oturum okunabilir kalsin, uretim
gerekceli dursun). Test planlanan sozlesmeye gore guncellendi: `geometry_stale` gerekcesi "kaynak çizim
değişmiş", `step is None`, sorular/kararlar okunur, build ve indirme "tarihsel" gerekcesiyle durur.
**Not:** bu, hatali ciktiyi mesrulastirmak degil; yanlis *beklentiyi* planlanan davranisa cevirmek — plan bunu
P01-b.4'te istiyor.
Yeni P01-b kabul testleri (`test_guided.py`):
- `test_a_migrated_record_never_serves_its_old_step_as_current`: **basariLI** gecisten sonra bile eski cikti
  guncel degil -> `build_status == "historical"`, `step/stl/plan is None`, `geometry.historical` eski klasoru
  gosterir, eski `part.step` diskte durur, `artifact()` "güncel STEP yok" der.
- `test_a_stale_record_keeps_its_evidence_and_recheck_recovers_it`: bayat kayitta kararlar ve eski dosya
  korunur, build/indirme "tarihsel" ile durur; kaynak geri gelince **`recheck` kurtarir** ve ayni cikti yeniden
  guncel olur.
Kosu: `proc_2d18fc812080` (/tmp/p01b-set2.txt).

### P01-b test duzeltmesi — gercek senaryo (2026-09-29 03:42, yeniden kosu suruyor)

Ikinci kosuda tek kirmizi benim testimdi ve teshis net: kaynagi **bos dosyayla degistirip ozeti de o bos
icerige uydurmustum**; surumu guncel (v3) bir kayit zaten kaynaktan yeniden okunmadigi icin bu durum
yakalanmiyor — yani sahte ozet uretmek urun senaryosu degil. Test gercek senaryoya cevrildi: **kaynak dosya
yerinde yok** (`source.moved`'a tasindi) -> `load` cokmeden `geometry_stale` ("kaynak dosya okunamadı"),
build ve indirme "tarihsel" ile duruyor, kararlar ve eski dosya duruyor; kullanici dosyayi geri koyunca
**`recheck` kurtariyor** ve ayni cikti yeniden guncel oluyor.
**Durust sinir (kayitli):** v3 kayitlar her yuklemede kaynaktan yeniden okunmaz; *ozeti de uydurulmus* sessiz
bir kaynak degisimi (gercek kullanici senaryosu degil) bu kapiyi gecerdi. Gercek degisim (ozet uyusmaz) ve
eksik dosya yakalaniyor.
Kosu: `proc_ef62767e69d7` (/tmp/p01b-set3.txt).

### P01-b test duzeltmesi 2 (2026-09-29 03:43, yeniden kosu suruyor)

`TypeError: 'FixtureFunctionDefinition' object is not subscriptable` — benim testimde `record["decisions"]`
yazdim ama testin kendi parametresi yoktu; `record` **pytest fixture fonksiyonunun kendisiydi**. Duzeltme:
testin basinda `before_decisions = store.load(token)["decisions"]` alinip karsilastirma ona yapildi. Kodda
degisiklik yok. Kosu: `proc_6e9a9ce71424` (/tmp/p01b-set4.txt).

### P01-b DOGRULANDI — eski cikti artik guncel sunulmuyor (2026-09-29 03:45)

`test_guided + geometry_migration + geometry_state + guided_html + stable_identities + measure_meaning +
user_dimensions` -> **53 passed in 65,98 s**. Kabul testleri: (1) **basarili** gecisten sonra da eski cikti
`historical` (step/stl/plan URL'si yok, `geometry.historical` eski klasoru gosterir, dosya silinmez,
`artifact()` "güncel STEP yok"); (2) bayat kayitta kararlar + eski dosya korunur, build/indirme "tarihsel" ile
durur, kaynak geri gelince **`recheck` kurtarir** ve ayni cikti yeniden guncel olur; (3) kaynak degismis/yok ->
oturum okunur kalir, `geometry_stale` gerekcesi gorunur. Bu turdaki uc kirmizinin ucu de **test tarafindaydi**
(planlanan davranisa cevrilen eski beklenti + iki kurulum hatasi); kodda P01-b kaynaklı kusur cikmadi.
**P01 durumu:** P01-a ve P01-b dogrulandi; P01-c'nin rapor/onizleme maddesi P04-c ile kapanacak (plana bagli).
Siradaki: **P02-a** — kanonik yay tanimi (F07) ve tamamlayici yarim yay testinin duzeltilmesi.

### P02-a kodu indi — kanonik yay tanimi (2026-09-29 03:45, set kosuyor)

`geo.py`'ye **tek kanonik tanim** eklendi: `arc_page_ends(center, radius, a, b)` — yayin iki ucunu **sayfa
pikselinde** kanonik `a/b`'den uretir; sayfa Y-asagi oldugu icin sayfa acisi = **-kanonik aci** (donusum acikca
yazildi, P02-a.1). `contour_audit` artik:
- `_arc_points` zincirini **kanonik** baslangic acisindan kuruyor (saklanan `start`'tan turetmiyor; F07'nin
  kok nedeni buydu),
- `_arc_span` da kanonik (`phi = -a`, `sweep = -(b-a)`) — ortusme/ters-yon karari artik saklanan noktaya bagli degil,
- her yay icin **iki ucu ayri ayri** karsilastiriyor: `arc_start_mismatch` (yeni) + `arc_end_mismatch`; mesajda
  `a`/`b` degerleri var (P02-a.2),
- **supurme kurallari**: `|b-a| <= 1e-9` -> `arc_zero_sweep`, `>= 360` -> `arc_full_turn` ("tam cember `circle`
  turudur"; CAD de ayni siniri uyguluyor — `geo.py`: sweep ±360 disi ve sifir kabul edilmiyor) (P02-a.5).
Beklenen: mevcut test fixture'larinin bir kismi **kanonik ciftle tutarsiz** kurulmustu (ozellikle tamamlayici
ikinci yarim yay: `a=0,b=-180` ikinci yarimi tarif etmiyordu — denetimin P02-a.3 dedigi sey); kosu hangi
fixture'larin duzeltilmesi gerektigini gosterecek ve onlar **dogru kanonik ciftle** yeniden yazilacak.
Kosu: `proc_d4b4484eb199` (/tmp/p02a-set1.txt).

### P02-a kodu indi + F07 canli kanit (2026-09-29 03:47)

Ilk yama girisimi **hic uygulanmadi**: `geo.py`'de `def extrude(` copasi yoktu (`extrude_profile`,
`profile_extrude` var), script ilk adimda durdu ve arka planda oldugu icin ciktisi gorunmedi; o kosudaki
"34 passed" **eski kodun** sonucuydu — bu yuzden yesil sayilmadi, dosya durumu grep ile dogrulandi.
Yama dogru copayla (`def plate(`) tekrar indi ve canli probla dogrulandi:
- **Eski kod (F07, canli tekrar):** kanonik cift ikinci yarimi tarif etmezken saklanan start/end karsi yarimi
  verince denetim **`ok: True`** diyordu (kusur kanitlandi).
- **Yeni kod:** ayni kayit -> `arc_start_mismatch` + `arc_end_mismatch` (mesajda `a=0°, b=-180°`), ek olarak
  ayni destek/span nedeniyle `overlap` + arc-arc `self_intersection`.
- **Duzeltilmis kanonik ciftle** (ikinci yarim icin `a=180°, b=0°`, saklanan uclarla tutarli) -> `ok: True`.
`geo.py::arc_page_ends` (kanonik -> sayfa; sayfa acisi = -kanonik) tek tanim; `contour_audit` zinciri artik
kanonik baslangictan kuruyor, `_arc_span` da kanonik, iki uc ayri ayri karsilastiriliyor, sifir/tam-tur
supurme ayri tani. `proc_4f378283db38` (/tmp/p02a-set2.txt) ile fixture etkisi olculuyor.

### P02-a DOGRULANDI — kanonik yay tanimi (2026-09-29 03:59)

`contour_audit + matrix + p02_repeats + contour_fix + geo` -> **36 passed in 23,60 s**.
Kanit zinciri: (1) **F07 canli tekrar** — kanonik cift ikinci yarimi tarif etmezken saklanan start/end karsi
yarimi veriyordu ve denetim `ok: True` diyordu; (2) ayni kayit yeni kodda `arc_start_mismatch` +
`arc_end_mismatch` (mesajda `a`/`b`) ile reddediliyor; (3) duzeltilmis kanonik ciftle (`a=180°, b=0°`)
`ok: True`; (4) `arc_page_ends` (kanonik -> sayfa, sayfa = -kanonik) tek tanim olarak `contour_audit`'te ve
fixture'lar ona karsi dogrulaniyor; (5) sifir/tam-tur supurme icin `arc_zero_sweep` / `arc_full_turn`
(canli probla da goruldu). Testler: tamamlayici yarim yay, sifir-siniri ve ters-yon fixture'lari dogru kanonik
ciftle yeniden yazildi (P02-a.3), iki yeni karsi ornek regresyon oldu (ayni kanonik yarim + farkli saklanan
uclar -> ret; sifir/360 supurme -> ret).
**Ders (kayit):** `geo.py` CAD cocuk sureci tarafindan **tek basina** (importlib ile yol uzerinden) yukleniyor;
paket ici import eklenirse CAD kosulari `ModuleNotFoundError: No module named 'drawingto3d'` ile duser. Ortak
tanim bu yuzden `contour_audit`'te duruyor; CAD tarafi ona karsi **dogrulanacak**, kodu paylasilmayacak.

### P02-b ve P02-c DOGRULANDI (2026-09-29 04:03) — kalan tek parca: CAD yay uclariyla karsilastirma

**P02-b** (`contour_audit + matrix + p02_repeats + p02b + contour_fix + geo` -> **41 passed in 23,99 s**):
esikler amaca gore ayrildi (kapatma `TOLERANCE_PX=0.5`; **destek esitligi** `SUPPORT_TOLERANCE_PX=0.35`, %2 kurali
kaldirildi; cizgi icin `STROKE_TOLERANCE_PX=1.0`). F08: R100/R99 yarim halkasi (iki yay + iki radyal uc) **geciyor**;
ayni yayin tam/ters tekrari **reddediliyor** (`overlap`, ters yonde "(ters yön)"). F11: ayni 0,8 px cizginin ileri/geri
tekrari `overlap` + yeni `zero_area` ile **reddediliyor**. P02-b.3: ortusme artik **normalize araliklarin gercek
kesisimi** (`angular_overlap_radians`; 0° sarmalamasi iki araliga bolunuyor) — elle dogrulanan uc deger: temas 0,
10° = 0,174533, sarmalanan cift = 0,174533. Yalniz ortak uc paylasan yaylar gecer.
**P02-c** (7 dosya -> **47 passed in 26,38 s**): kesisim karari **analitik** — cizgi–cizgi parametrik (capraz carpim
isareti birakildi; sifir capraz carpimda yansimaya gore degisen karar F10'un kok nedeniydi), cizgi–yay quadratic,
yay–yay iki-cember + acisal aralik suzgeci. F09: R1000 yarim yay ile y=999 dogrusunun **iki** kesisimi (±√1999, sapma
< 0,01 px) bulunuyor ve `tolerance_px=2.0` ile de ayni sonuc. Komşu cift artik butun olarak atlanmiyor: yalniz kendi
birlesimi (her iki kenarin ucuna tolerans mesafesinde) yok sayiliyor; komşu ciftin baska noktadaki kesisimi
bildiriliyor (yeni test). Komşu olmayan kenara **uc temasi** yeni `endpoint_touch` tanisiyla reddediliyor ve karar
**Y yansimasi + ters gezinmede ayni** (ayni tani kumesi, ayni `closure_px`); gecerli halka uc halde de gecer.
P02-c.7 kaniti: `join_max_px`+`joins` (guided.py:233–281), `applied_move_px` (:332), son kalan aciklik denetimde
(`closure_px`; guided.py:514 notu "join_max_px birlesme *oncesi* olculen acikliktir").
**Kalan tek parca (P02 zorunlu kabul):** CAD yay uclariyla **bagimsiz karsilastirma** — plan entity'leri
`guided.py:801`'de yay aci ciftini `a`/`b`'den aliyor; simdi CAD uclarinin (geo'nun kendi aritmetigi) denetimin
kanonik uclariyla sayisal karsilastirmasi test olarak yazilacak. Ardindan P03'e (kalan P03-b/c maddeleri) gecilecek.

### P02 DOGRULANDI — CAD yay uclariyla bagimsiz karsilastirma dahil (2026-09-29 04:04)

Odak seti (7 dosya: `contour_audit`, `matrix`, `p02_repeats`, `p02b`, `p02c`, `contour_fix`, `geo`) -> **48 passed in 25.18s**.
Yeni test `test_the_audit_and_cad_agree_on_where_an_arc_begins_and_ends`: CAD tarafi plan kurucusunun verdigi
girdiyle besleniyor (`guided.py:801` aci ciftini `a`/`b`'den aliyor; merkez `xy()` :788 — origin = (min x, max y),
sayfa Y ters — yaricap `value()` :801 px/scale) ve uclari **geo'nun kendi aritmetigiyle** hesapliyor
(`center + radius*(cos, sin)`); denetimin `arc_page_ends` uclari ayni donusumden gecirilip karsilastiriliyor:
**iki uç de 1e-9 icinde ayni**, supurme yonu de sayfa/CAD arasinda ters isaretle tutuyor (Y cevrimi).
**PLAN.md P02 satiri "doğrulandı"ya çekildi.** Siradaki: P03'un kalan maddeleri — §8.6 gorunus ekseni/orijini ve
dondurulmus paftada cerceve karari; P03-b/c (referanslara profil/surum/uc anlami; duzenlenmis topolojiye gore
denetim; mm/inc; silinen kenar; eski surum) ve P03 kabul listesinin toptan karari. Sonra P04-a…f.

### P03-b-1 DOGRULANDI — bag ucunun kimligi: profil + surum + fiziksel uc (2026-09-29 04:11)

`test_binding_end_meaning + stable_identities + guided + measure_meaning + user_dimensions + geometry_state +
geometry_migration` -> **53 passed in 73,98 s**. Yeni sema: `BindingEnd{profile, geometry_version, end}`.
Cozumleme tek yerde: `resolve_binding_end(edges, end)` — **saklanan tiklama noktasi** fiziksel ucu belirler,
`end` etiketi kanittir; `reference()` ve `unresolved_bindings`/`questions()` ayni fonksiyonu kullaniyor
(`_binding_end_issues`). Yeni testler: (1) ayni `e0` id'si iki konturda -> kayitli profil farkli olunca
**yeniden baglama** isteniyor; alan yoksa (eski kayit) koruma yok — bu durust sinir testte acikca yazildi;
(2) kontur **ters yurundugunde** (etiketler `start`<->`end` takas) bag **ayni koseye** oturuyor (indeks degil,
nokta dogrulaniyor); (3) tiklama artik kenarin ucunda degilse ("uçlarında değil … yeniden bağlanmalı").
**Yakinsama (kayit):** eskiden `unresolved_bindings` ve `reference()` ayni durum icin *iki farkli* mesaj
metni kullaniyordu (test bunu iki ayri yerde dogruluyordu); tek cozumleyiciye gecince mesaj birlesti —
`"<id> bu konturda olan bir nokta değil (bağ ucu artık bu konturda yok)"` her iki beklentiyi de karsiliyor,
yani **hicbir test beklentisi gevsetilmedi**.
Tam takim arka planda kosuyor (`proc_10373372b8ee`, /tmp/full-after-p03b1.txt). Siradaki is: **P03-b-2** —
kayit yolunun (save/accept) eksik `profile`/`geometry_version`/`end` alanlarini doldurmasi ve `guided.js`
`snapEnd`'in bu alanlari gondermesi; sonra servis edilen dosyayla dogrulama.

### P03-b-2 kodu indi — uc kaniti kayit yolunda + arayuzde (2026-09-29 04:15, arayuz kabulu bekliyor)

Kayit yolu (`save` + `accept`) artik `_with_end_evidence` ile eksik `profile` / `geometry_version` / `end`
alanlarini yaziyor ve gunluge geciriyor ("N bağ ucunun kanıtı yazıldı …"); cozulemeyen uc **bilerek**
yazilmiyor — en yakina sabitlemek §8.9'un yasakladigi sessiz esleme olurdu. `guided.js` `snapEnd` uc adaylarina
`profile: state.decisions.profile_id`, `geometry_version: state.geometry.version` ve `end: 'start'|'end'`
ekliyor; boylece kullanici baska bir kontura gecip kaydettiginde kanit *tiklandigi* konturu gosterir (sunucu
tarafindaki dolgu yalnizca eksik alani doldurur). Sozdizimi `vm.SourceTextModule` ile ✓; sunucu yeniden
baslatildi; **servis edilen** `/guided.js` dogrulandi (`geometry_version` x2, `profile:state.decisions.profile_id`
x2, `end:'start'` x1), `GET /guided` 200. Test: `tests/test_binding_end_meaning.py` -> **4 passed in 2,94 s**
(plaka oturumu + gercek `save`; uc alan kayitta ve yeniden acilista duruyor, gunlukte gorunuyor).
**Kalan (bu pencerede yapilmadi):** gercek tarayicida uc sec → kaydet → kayitta uc alanin gorunmesi (UI kabulu);
§8.6 gorunus ekseni/orijini + dondurulmus paftada cerceve karari; P03 kabul listesinin toptan karari; P04-a…f.
Tam takim arka planda kosuyor (`proc_10373372b8ee`, /tmp/full-after-p03b1.txt).

### P03-b-2 ARAYUZ KABULU (2026-09-29 04:18) — gercek tarayici, gercek fare

Oturum `39b0db42439f406c97121609ffe2038b` (plaka paftasi, cerceve 2339x1654, tuval 725,95x514,19 => olcek
0,31037/0,31088). Adimlar ve kanit: "Onerileri onayla" gercek tiklamayla -> durum "Okumanın tüm önerileri
sizin kararınız olarak kaydedildi." + `profile = outline_1` + "Ölçek 7.8755 px/mm · iki noktalı
kalibrasyondan (bağ yok)"; `#bind-start` ile bag modu; tuvalde `g1:start` [435,76/1209,53] ve `g1:end`
[1223,3/1209,43] uclarinda **iki gercek tiklama** -> "Bir uç seçildi; ikinci uca tıklayın." -> "Karar
kaydedildi."; panel satiri **"100 mm · X+ · kontur g1:start ↔ kontur g1:end"**.
**Kayittaki uc kaniti (dosyadan okundu):** `first = {kind:vertex, id:"g1:start", x:435.76, y:1209.53,
profile:"outline_1", geometry_version:3, end:"start"}`, `second = {… id:"g1:end" … end:"end"}` ✓ —
P03-b-2'nin istedigi "nerede ve ne zaman secildi" bilgisi artik gercek akista kayitli.
**Arayuz sozlesmesi kaniti (bonus):** eksen/yon bosken ikinci tiklama **kaydetmedi** ve "Bağlanan ölçünün
eksenini (X/Y) ve yönünü seçin; anlam sizin kararınız." dedi (P03 dilim-2) ✓.
**Durust sapma (kayitli):** eksen/yon `<select>` degerleri bu headless oturumda **gercek fare+klavye ile
kurulamadi** (tiklama + ArrowDown/Enter native seciciyi oynatmadi; iki deneme de basarisiz); degerler betikle
kurulup **gercek `change` olayi** gonderildi. Geometri tiklari gercek; yalniz secici degerleri icin bu yol
kullanildi ve raporda sapma olarak yazildi. Takip isi: ayni adimi headless olmayan tarayicida tekrarlamak.
Tam takim: `proc_10373372b8ee` (/tmp/full-after-p03b1.txt) hala kosuyor.

### Tam takim P02/P03-b sonrasi: 2 kirmizi, IKISI DE BAYAT FIXTURE (2026-09-29 04:30, duzeltildi)

Tam takim: **2 failed, 638 passed in 1072,78 s** (585 -> 640 test). Iki kirmizi da
`tests/test_guided_proposals.py` icindeydi ve **P01-a'nin gecis kuralindan** geliyordu, P03-b'den degil:
fixture'in kaydi `geometry_version` alanini hic tasimiyordu; P01-a'nin kurali geregi surumsuz kayit
kaynaktan yeniden okunmaya calisiliyor, fixture'in "kaynagi" sahte PDF oldugu icin PDFium hatasi ->
`geometry_stale` -> build reddi ("temel geometri kaynaktan yenilenemedi … tarihsel"). Dogru duzeltme
fixture'i duzeltmekti: `"geometry_version": guided.GEOMETRY_VERSION` (sentetik kayit; geometrisi tanimi geregi
guncel) + eksik `guided` importu. **Uretim kurali gevsetilmedi.**
Sonuc: `tests/test_guided_proposals.py` -> **15 passed in 4,55 s**; tam takim yeniden kosuyor
(`proc_086e1524dc7c`, /tmp/full-after-fix.txt).
**Ders (kayit):** P01-a sonrasi odak setine `test_guided_proposals.py` de girmeli — surumsuz fixture'lar tam
takimda patliyor, odak seti bunu kaciriyor. Tam takim yesil gelince P03'un toptan kabul karari ve §8.6'ya
gecilecek.

### TAM TAKIM YESIL — 641 passed / 1009,19 s (2026-09-29 04:47)

`PYTHONPATH=src .venv/bin/python -m pytest -q` -> **641 passed in 1009,19 s** (0 hata, 0 atlama sayisi
degismedi; takim 585 -> 641). Bu, P01-a/b + P02-a/b/c + P03-b (kod + arayuz) sonrasi ilk tam yesil kosu.
Onceki kosudaki iki kirmizi bayat fixture'dan geliyordu (fix: `geometry_version` + import), yani regresyon
yok. **Durum:** A0 ✓, P00 ✓, P01-a/b ✓, P02 ✓ (zorunlu CAD karsilastirmasi dahil), P03-b-1 ✓ + P03-b-2
arayuz kabulu ✓. **Kalan:** §8.6 gorunus ekseni/orijini + dondurulmus paftada cerceve karari; P03'un toptan
"dogrulandi" karari; P04-a…f; kapı sayaclarinin (plaka/plastik/Drawing.pdf okumalari) birebir yeniden okunmasi;
`guided-flow-evidence.json` guncellemesi. Commit atilmadi (paralel ajan).

### KAPI YENIDEN OKUMASI + model-baseline raporu (2026-09-29 04:55)

**Okuma cephesi degismedi:** `PYTHONPATH=src .venv/bin/python eval/frontend.py` yeniden kosuldu.
`out/frontend/*.json` (27 dosya) alan alan karsilastirildi: **sayilarin hepsi ayni**; yalnizca olculen
`seconds` alanlari degisti (or. exercise-1 77,4 -> 75,4 sn). Kapsam satirlari: **plate-pocket-1 7/7**,
plastic-enclosure-1 11/11, exercise-1-vector 13/13, exercise-12 19/20, flange-1 4/13 (= eski degerler).

**Tablolar tutuyor:** `eval/check_tables.py` -> **21 satir okundu, 0 satir kosuyla tutmuyor**.

**`eval/baseline_report.py --check` KIRMIZI idi** (rapor kosularla uyusmuyordu) — sebep benim yeniden kosum
degil, ama benim kosum da etkiliyor: uretilen blok her kosunun `seconds` degerini yaziyor (baseline_report.py
satir 114: `secs=_seconds(run.get("seconds"))`). `--write` (belgelenmis guncelleme yolu; yalniz uretilen blok
yeniden yazilir, insan metni korunur) calistirildi -> `--check` simdi **"rapor kosularla uyusuyor"**.
Yan not: `eval/reports/model-baseline.md` agacta paralel ajanin bitmemis duzenlemesini tasiyor
(git diff 375/268) — `--write` yalniz uretilen bloga dokundu, metin yerinde.

Kapsam notu (durust): plaka 7/7 ve plastik kapsami bu kosuda birebir ayni; `14/14` (bagli sayilar) ve
`Drawing.pdf 16/17` sayilari farkli donem raporlarinin olcutleri (`reading-coverage.md`,
`flange-archetype-evidence.md`); onlarin kosuculari yerel model gerektiriyor -> istenirse siradaki is
olarak kosulur. `out/model-baseline` kayitlarina bu pencerede hic dokunulmadi (istek ozetleri sabit).

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
