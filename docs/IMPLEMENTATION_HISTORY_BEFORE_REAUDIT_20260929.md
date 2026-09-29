# Uygulama durumu (P00–P08)

Guncelleme: 2026-09-29 02:29

## P00 — Baslangic kaydi (tamamlandi kabulu bekliyor)

- Kanit klasoru: `out/plan-run-20260929-022902/` (git disi) — `git-status-short.txt`, `git-rev-parse-HEAD.txt`, `python-version.txt`, `inventory.json`, `untracked-list.txt`, `historical-suite-summary.txt`.
- HEAD `96e01189f5f3`; izlenmeyen dosya 89; toplam degisiklik satiri 116.
- **Tarihsel sonuclar (yeni kodun sonucu DEGIL):** tam takim 585 passed / 951,46 s (dosya varsa kopyalandi), odak 18 passed.
- Bilinen acik kusurlar PLAN.md Bölüm 3 tablosunda; ilk kod isi P01 (ozgun geometrinin uretimde degismemesi).


## P00-P01 dilimi (2026-09-29 02:31) — plan-run baslangic kaydi + ozgun geometri izolasyonu

**P00 (kayit):** `out/plan-run-20260929-022902/` acildi: `git-status-short.txt`, `git-rev-parse-HEAD.txt`
(HEAD 96e01189f5f3), `python-version.txt` (3.11.16), `inventory.json` (izlenmeyen 89 dosya, 116 satir),
`untracked-list.txt`, `historical-suite-summary.txt` (/tmp/suite-26b.txt varsa kopyalandi). Kalici ozet:
`eval/reports/implementation-status.md`. Tarihsel sonuclar (585 passed / 951,46 s, odak 18 passed) yeni kodun
sonucu diye sunulmuyor.

**P01 ilk dilim:** `guided.py` `make_plan` artik `options=copy.deepcopy(record["options"])` ile calisiyor —
temel geometri salt veri kaynagi; cozulen konumlar/rapor yalniz cagriya ait kopyada kaliyor, store'daki
secenekler ve dolayisiyla sonraki build'ler orijinali goruyor. Yeni kabul testi (gercek GuidedStore yolu,
plaka paftasi): `tests/test_guided_geometry_state.py` — create→save→build A→save+bag→build B→bag kaldir→build C
(A'ya donus, tolerans icinde birebir parametre esitligi)→undo→yeniden ac; her adimda temel seceneklerin
normalize JSON ozeti degismiyor; cozum raporu options'a sizmiyor. Kosu: `proc_4e7feda7a4b7`
(`/tmp/p01-test.txt`) — sonuc bildirimle gelecek.

**P01 kalan isler (siradaki):** (1) cozum raporunu ayri sonuc nesnesine baglayip arayuz satirini oradan
beslemek; (2) eski kayitlar icin temel geometriyi kaynaktan yeniden cikaran guvenli gecis (ozet/okuyucu
surumu/kimlik eslesmesi; eslesme yoksa yeniden secim iste, sessizce tasima); (3) atomik yazim ve yarida
kesilme testi. P00'un acik parcasi: P02'nin iki yarim-yay ve son-aciklik kusurlarini kucuk girdilerle
tekrarlamak (kabul icin tekrar veya acikca yazili tekrar engeli gerekli).

**P02'ye gecis kosulu:** P01 kabul testleri (bu dosya + store yolu) gectikten sonra.


### P01 ilk dilim sonucu + gecis tasarimi (2026-09-29 02:32)

**Kabul testi gecti:** `tests/test_guided_geometry_state.py` (gercek GuidedStore yolu, plaka paftasi):
create -> save -> build A -> ayni kararla tekrar (ayni geometri) -> bagli olcu ekle -> build B (geometri degisti)
-> olcuyu kaldir -> build C (A ile birebir) -> cozum raporu options'a sizmiyor -> geri al -> build (B ile
birebir) -> store'u yeniden ac (ayni). Kosu: **1 passed in 13.22 s**; odak regresyon seti (test_guided,
test_user_dimensions, test_sketch_constraints, test_contour_audit, test_contour_fix + bu dosya) kosuyor:
`proc_7a95837a7755` (/tmp/p01-focused.txt).

**Kalan P01 isi — guvenli gecis (tasarim, kodlanacak):**
1. `create` kaydina `geometry_version` alani (yeni surum sabiti) yazilir; mevcut kayitlar surumsuz = eski.
2. `load` sirasinda surum eskiyse `_migrate_geometry(record)`: temel geometri **kaynak veriden** yeniden
   uretilir — once oturum klasorundeki `observations.json` (varsa; saf ve hizli) `drawing_options` ile
   yeniden hesaplanir, yoksa `observe(source)`. Kullanici kararlari (`decisions`) aynen korunur.
3. Kimlik eslesmesi denetimi: profil kimlikleri/kumesi, daire kimlikleri, olcu span'leri ayni mi? Eslesiyorsa
   `options` tazelenir + `geometry_version` guncellenir + gunluge "temel geometri kaynaktan yenilendi" yazilir.
4. Eslesme yoksa: eski options **korunur**, `record["geometry_stale"]` nedeniyle isaretlenir ve eski
   baglarin kimlikleri cozulemiyorsa `questions()` kullaniciya **yeniden secim** ister; hicbir uc sessizce
   baska noktaya tasinmaz.
5. Yazim yalniz basarili gecisten sonra ve `_atomic` ile (tmp+rename) yapilir; yarida kesilirse eski
   session.json okunabilir kalir; gecis idempotenttir.
6. Kaynak dosya eksik/degismisse: eski sonuc **tarihsel** tutulur; `build` net bir mesajla reddeder
   ("kaynak cizim degismis; eski sonuc tarihsel, yeniden uretilemez"), sayfa kaydi gostermeye devam eder.
   `load`'un bugunku sert hatasi bu yola baglanir.

**P00 kalan parca:** P02'nin iki yarim-yay ortusme kusuru ve son-acikligin en buyuk acikligi ezmesi kucuk
bagimsiz girdilerle tekrarlanacak (kabul: tekrar veya acikca yazili tekrar engeli).

**Sonraki is sirasi:** (1) bu odak setin sonucunu kaydet; (2) P01 gecis kodunu + testini yaz; (3) P02
tekrarlari; (4) P02 duzeltmesi (contour_audit yay/kapali egri ve aciklik mantigi). P02'ye ancak P01 kabulu
gectikten sonra gecilecek.

**Odak regresyon (P01 sonrasi):** `test_guided_geometry_state + test_guided + test_user_dimensions +
test_sketch_constraints + test_contour_audit + test_contour_fix` -> **65 passed in 55.32 s** (2026-09-29 02:33).
`copy.deepcopy` izolasyonu mevcut testleri bozmadi. Kanit: /tmp/p01-focused.txt

### P01 guvenli gecis kodu yazildi (2026-09-29 02:34)

`guided.py`: `GEOMETRY_VERSION = 2` sabiti + `_geometry_ids`/`_same_geometry` yardimcilari; `create` kaydina
`geometry_version` alani; `load` artik `_migrated(token, record)` cagiriyor: eski kayitta temel geometri
**kaynaktan** yeniden cikarilir (`observe` + `drawing_options`), kimlikler (profil/daire/span) eslesirse
`options` tazelenir ve gunluge "Temel geometri kaynaktan yeniden cikarildi" yazilir; eslesmezse **hicbir sey
tasinmaz**, `geometry_stale` nedeni kaydedilir; hata bir kez denenir ve hatirlanir; yazim `_atomic` (tmp+rename).
`build` geometri bayatsa net mesajla reddeder: "temel geometri kaynaktan yenilenemedi (...); eski sonuc
tarihsel, yeniden uretilemez".

Yeni test: `tests/test_guided_geometry_migration.py` — (1) eski kayit (surumsuz + build artigi solved_dimensions
+ kaymis kenar ucu) yuklenince temel geometri kaynaktaki taze kopyaya donuyor, kararlar korunuyor, gunlukte
`migrate` satiri var, ikinci yukleme ayni (idempotent); (2) okuyucu degisti gibi kimlikler bozulunca (monkeypatch)
`geometry_stale` isaretleniyor, options **degismiyor** ve `build` "tarihsel" mesajiyla reddediyor.
Kosu: `proc_76d483149eeb` (/tmp/p01-migrate.txt) — sonuc bildirimle gelecek.

### P01 TAMAM — dogrulandi (2026-09-29 02:36)

Kabul listesinin besi de gecti (gercek store yolu): iki hazirlama determinizmi ✓; olcu ekle->uret->kaldir->uret
(ozgun geometri dondu, cozum raporu kalmadi) ✓; ekle->uret->geri al->uret->store'u yeniden ac ✓; calisma
kopyasi yalitimi (temel secenekler her adimda normalize JSON esit) ✓; eski surum gecisi ✓.
Kanit: `tests/test_guided_geometry_state.py` (1 passed, 13,22 s) ve `tests/test_guided_geometry_migration.py`;
birlikte odak set **53 passed in 68,89 s** (/tmp/p01-migrate2.txt). PLAN.md P01 satiri "dogrulandi" yapildi.

**Kayitli ara hata ve ders:** ilk gecis kodu her surumsuz kaydi yeniden okumaya calisiyordu; stub kaynakli
mevcut test kayitlari "bayat" damgalanip 11 test dustu. Duzeltme: gecis yalnizca eski bir build'in temel
geometriye biraktigi isaret (`solved_dimensions`) varsa calisir; isaretsiz kayit "cizimin kendisi" sayilir,
yeniden okunmaz. Boylece hem mevcut davranis korunuyor hem de gercek eski oturumlar guvenle tasiniyor.

**Sirada (P00'un kalan parcasi):** P02'nin iki kusurunu kucuk bagimsiz girdilerle tekrarlamak —
(a) tam daire yapan iki yarim yayin kiriş ortusmesiyle "cakisiyor" sayilmasi (gecerli kontur reddi);
(b) son birlesimin acikliginin daha once bulunan en buyuk acikligi ezmesi (icte acik birlesim varken kapanis 0).
Beklenen sonuclar testte onceden yazilacak; mevcut hatali cikti beklenen sonuc yapilmayacak.

### P00 tamam (dogrulandi) + P02 ilk yari (2026-09-29 02:39)

**P00:** baslangic kayitlari + butun kusur tekrarlari yerinde. 100x100 kare cift-bag tekrari (100 ve 99,6 mm
baglari; sonra kaldirinca genislik ~100,2 kalabiliyordu) icin girdiler kayitli; urun yolunda cizgi kontur
kose bagi eski soru kapisina takildigi icin **tekrar engeli acikca yazildi** (PLAN P04 kapsami). PLAN.md P00
satiri "dogrulandi".

**P02 ilk yari (kod):** `contour_audit.py` — (1) yay cakismasi artik kiriş izdusumu degil **acisal aralik**
ortusmesi (`_arc_span` + `_arc_overlap_extent`; esik max(0,02 rad, 1 px/r)); (2) `closure_px` her birlesimde
`max(...)` — son birlesim onceki buyuk acikligi ezmiyor. `tests/test_contour_audit_p02_repeats.py`: iki kusur
tekrari (xfail isaretleri kaldirildi, duz assertion) + gercek ortusme kontrolu (10 derece) ✓.
Kanit: `test_contour_audit_p02_repeats + test_contour_audit + test_contour_fix + test_guided` -> **41 passed
in 41.26 s**.

**P02 kalan isler (PLAN §7 zorunlu matrisi):** ayni yay iki kez -> ret (yazilacak); 0 derece sinirini asan
yaylar -> gecerli; ters yon -> ayri tani (bugun "overlap" olarak isaretleniyor; §7.6 ayrimi istiyor);
cizgi-yay ve yay-yay gercek kesismesi -> isaretli; gecerli komsu ortak uc -> temiz; komsu olmayan kenarin
temas ettigi bozuk halka -> isaretli; icte 2 px aciklik + son birlesim 0 -> closure 2; tutarsiz saklanan yay
ucu -> `arc_end_mismatch`. Ayrica §7.7 (32 ornekli poligon "kesin kesism testi" diye sunulmasin — modul
docstring'ine sinir notu) ve §7.8 (px/mm tolerans ayrimi) notlari acik.

**Sirada:** bu matrisin kalan testlerini yazmak, sonra P03 (olcu anlami ve kararli referanslar).

### P02 zorunlu matris tamam + ters-yon ayrimi (2026-09-29 02:40)

`tests/test_contour_audit_matrix.py` (10 test, **10 passed in 0.10 s**): tamamlayici iki yarim yay gecer ✓;
ayni yay iki kez -> "overlap" ve iki kimlik ✓; 0 derece sinirini asan yaylar gecer ✓; ters yon -> "overlap"
+ mesajda "(ters yön)" (ayri tani, §7.6) ✓; cizgi-yay gercek kesisme -> `self_intersection` kinds
["arc","line"] ✓; yay-yay gercek kesisme (iki farkli cemberin yaylari) -> kinds ["arc","arc"] ✓; gecerli ortak
kose (ucgen) temiz ✓; kapanis 0 iken komsu olmayan kenarin halkayi kesmesi -> ret + e0/e2 cifti ✓; icte 2 px
aciklik + kapali son birlesim -> closure 2,0 ve tek "open" kaydi ✓; saklanan yay ucu kendi tanimiyla
tutmasizsa `arc_end_mismatch` ✓; sifir uzunluk ile kopuk zincir AYRI tanilar ✓.

`contour_audit.py` ek: `_opposite_note` (ayni destekte ters yonde giden yaylar "ters yön" diye adlandirilir) ve
§7.7 sinir notu (32 ornekli poligon = sinirli yaklasim; kesin kesisim testi diye sunulmaz, kacirabilir).

**§7.3 (CAD ile ayni yay tanimi) kaniti:** denetim yayi yalniz merkez/yaricap/isaretli supurme (`a`,`b`) ile
kuruyor ve saklanan start/end'i buna karsi denetliyor; gercek paftalarin yayli gecerli konturlarinda kapanis
0,0 px cikmasi (her iki ucun da bu tanimdan uretilen uclarla ortusmesi demek) boru hattinin kendi icinde
tutarli oldugunu gosteriyor; negatif yon sentetik `arc_end_mismatch` testiyle kapali.

**§7.8 notu:** denetimin toleransi piksel cinsindendir ve buyutulmuyor; mm'ye baglanmasi kalibrasyon
uzerinden P04/P05'te ele alinir (global esik buyutme yasagi §26-A-14'te karar kaydinda duruyor).

**Durum:** P02 kabulu icin kalan tek sey odak setin sonucu (`proc_dcfdf264dd00`); yesilse P02 "dogrulandi".

### P02 TAMAM — dogrulandi (2026-09-29 02:41)

Dokuz dosyalik odak set **80 passed in 72,57 s** (/tmp/p02-set.txt): matris, tekrarlar, mevcut
contour_audit/contour_fix/guided/user_dimensions/sketch_constraints ve P01'in iki yeni dosyasi birlikte yesil.
PLAN.md P02 satiri "dogrulandi".

**Sonraki is — P03 (PLAN §8): "Olcunun anlamini ve referanslarini acik yap."** Is sirasi (ozet):
1. Kalibrasyon = iki kaynak nokta + gercek mesafe -> `px/mm`; **konum olcusu** = iki geometri referansi arasinda
   X veya Y farki; konum olcusu kalibrasyonu **yeniden hesaplamaz** (§8.2).
2. Karar semasina olcu turu/ekseni (X/Y), yonu, deger/birim (mm/inç), varsa basili olcu `span_id`'si ve hedef
   geometri referanslari acik alanlar olarak girsin; cekirdegin `DimensionBinding` sozlesmesi kullanilsin;
   **her kararin tekil `id`'si** kaynak `span_id`'den ayri olsun; ayni `span_id` iki farkli iliskide
   kullanilabilir, ayni karar `id`'si iki kez kullanilirsa ret (§8.3).
3. Arayuz X/Y secimini ve baglanan iki unsuru gostersin; buyuk piksel farkindan otomatik eksen karari YOK -
   oneri sunulabilir, kullanici dogrular (§8.4).
4. Ilk desteklenen turler: X/Y mesafesi + cizgi konturda yatay/dikey iliski; desteklenmeyen turler (uzunluk,
   yaricap, aci, tegetlik) acik ret/eksik karar uretsin (§8.5).
5. Gorus ekseni/orijini kullaniciya gosterilsin; dondurulmus paftada cerceve karar olarak kaydedilsin, sayfa
   X'i parca X'i varsayilmasin (§8.6).
6. Referanslar secili profil + geometri surumu + kararli nokta/kenar kimligine bagli olsun; ekran tiklamasi
   kimligin yerine gecmesin (§8.7). `edge:<index>` sozlesmesinden yeni kararli referanslara gecilecekse mevcut
   kayitlar acikca donusturulup test edilecek; kenar silinince indeks kaymasi baska koseye baglamasin (§8.8);
   profil/gorus degisince veya bagli kenar silinince etkilenen olculer "yeniden baglama gerekir" durumuna
   alinsin, en yakin noktaya sessizce eslenmesin (§8.9); eski kayitta eksen yoksa anlam kesinmis gibi
   doldurulmasin, kullaniciya dogrulatilsin (§8.10).
Kabul: gercek `Decisions.model_validate` + `validate_decisions` yolu; X/Y, yon, mm/inç, profil degisimi,
silinen kenar ve eski surum testleri; ayni `span_id`'den iki tekil karar kabul, ayni karar `id`'si iki kez ret;
degerin basili metinle eslesmesi ile dogru geometriye baglanmasi AYRI tutulur (§8 Kabul).

Bu pencere burada kapaniyor: P00 ✓, P01 ✓, P02 ✓ dogrulandi; P03 henuz baslamadi (kod yazilmadi).

### P03 kesif notu — sema noktalari (2026-09-29 02:42)

P03 icin dogrulanan mevcut sema (`guided.py`): `Calibration` (45-57) iki nokta + value/unit + `span_id`;
`BindingEnd` (68-73) `kind: Literal["centre","vertex"]`, `id`, `x`, `y`; `Binding` (76-84) yalniz value/unit/
span_id/first/second — **karar `id`'si ve eksen alani YOK**; `Decisions` (99-107). `validate_decisions` (389)
span kimliklerini olcuye karsi denetliyor (408, 414) ama karar `id` tekilligini denetlemiyor.
`user_dimensions` (577) cekirdege baglarken **ekseni tiklama farkindan** cikariyor (618: `axis=axis`), karar
id'si olarak `binding.span_id or f"binding_{index}"` kullaniyor (618) — §8.3 ve §3 tablosundaki
"buyuk piksel farkindan eksen" kusuru tam burada.

**P03 ilk dilim (yazilacak):** `Binding`'e `id: str | None` (tekil karar kimligi; `span_id`'den ayri) ve
`axis: Literal["x","y"] | None` ekle; `validate_decisions`'a "ayni karar `id`'si iki kez -> ret, ayni
`span_id` iki farkli kararda -> serbest" kurali; `user_dimensions` ekseni **karardan** alsin, `axis is None`
ise sorusnlar zinciri "ekseni kullanicidan iste" (sessiz cikarim yok, §8.10); yeni kararlarda `id` uretilsin
(yoksa `binding_<index>` yalniz eski kayitlar icin). Once `sketch_constraints.py`'de `DimensionBinding`/
`PointRef`/`EdgeRelation` alanlari okunacak (yon/delta alanlarinin adi oradan alinacak), sonra sema + test.

**Etkilenecek testler:** eksen alani yeni zorunluluk oldugu icin yeni-taraf baglar kuran testler baglara eksen
verecek: `tests/test_guided_geometry_state.py` (`_tie`), `tests/test_user_dimensions.py`, `test_guided.py`'de
bag kuran test(ler). Eski kayitlar icin eksen `None` kalir ve kullaniciya sorulur (silinen/doldurulan anlam
yok).

**P03 kabul testleri (yazilacak):** ayni `span_id`'den iki tekil karar kabul; ayni karar `id`'si iki kez ret;
X ve Y eksenli baglarin gercekten farkli koordinatlari sabitledigi; mm/in donusumu; profil degisimi ve silinen
kenarda "yeniden baglama gerekir"; eski surum kaydinda eksen yoksa soru uretilmesi. Degerin basili metinle
eslesmesi ile dogru geometriye baglanmasi ayri tutulacak.

### P03 ilk dilim — karar semasi (kod indi, set kosuyor) (2026-09-29 02:43)

`guided.py`:
- `Binding` alanlari: **`id`** (kararin kendi kimligi; `span_id`'den ayri), **`axis`** (`"x"|"y"|None`),
  **`direction`** (`-1|1|None`). `None` = onaylanmamis/eski kayit.
- `validate_decisions`: ayni karar `id`'si iki kez -> "aynı karar kimliği iki kez kullanılmış";
  `axis`/`direction` `None` ise -> "bağlanan ölçünün ekseni ve yönü kullanıcı tarafından onaylanmalı (X/Y)"
  (§8.4/§8.10: anlam uydurulmaz, kullaniciya sorulur); ayni `span_id`'nin iki farkli kararda kullanimi serbest.
- `user_dimensions`: eksen ve yon artik **karardan** geliyor (tiklama farkindan cikarim kaldirildi); karar
  kimligi `binding.id or binding_<index>`; docstring §8.4'e gore guncellendi.
- Testler: `test_user_dimensions.binding()`, `test_guided.binding_record()`, `test_guided_geometry_state._tie()`
  artik id + onaylanmis eksen/yon uretiyor (davranis beklentileri ayni kaldi).

Yeni kabul dosyasi `tests/test_measure_meaning.py` (6 test, gercek `Decisions.model_validate` +
`validate_decisions` + `user_dimensions` yolu): ayni `span_id` iki kararda tekil id'lerle kabul ✓; ayni karar
`id`'si iki kez ret ✓; onaylanmamis eksen -> ret ve mesaj kullaniciya soruyor ✓; **onaylanan eksen** sabitlenen
koordinati belirliyor (X ve Y ayri olculdu) ✓; inç degeri mm olarak tasiniyor (1,0 in -> 25,4 mm) ✓.

**Kosu:** `proc_cb785e3aae48` (10 dosya, /tmp/p03-set.txt) — sonuc bildirimle gelecek.

**P03 kalan isler:** (1) eksen sorusunu sert retten **yumusak soruya** tasimak (`questions()` icinde);
(2) arayuzde X/Y secimi + baglanan iki unsuru gosterme (§8.4) — `static/guided.js`; (3) gorunus ekseni/orijini
gosterme ve dondurulmus paftada cerceve karari (§8.6); (4) `edge:<index>` yerine kararli nokta/kenar
kimlikleri ve mevcut kayitlarin acik donusumu (§8.7/§8.8); (5) profil degisimi/silinen kenarda "yeniden
baglama gerekir" durumu (§8.9); (6) degerin basili metinle eslesmesi ile dogru geometriye baglanmasinin ayri
tutulmasi (kabul maddesi).

### P03 dilim-1 duzeltme notu (2026-09-29 02:44)

Odak sette 1 test dustu: `test_the_confirmed_axis_is_the_one_that_gets_fixed` — hata testin kendi
capasindaydi (cozulen merkezin piksel y'si gorsel orijine gore olculuyordu; dogru capa **datum kosesi**
(0,0) idi; tie iki uc arasindaki farki sabitler, datum izlenen yerinde kalir). Kod dogru davrandi: X durumu
40,0 mm verdi, Y durumunda `underconstrained` + 160,0 px (= 200 − 40) gorunuyordu; test capasi duzeltildi.
Yeniden kosu: `proc_a79d80792b97` (/tmp/p03-set2.txt). Ders kayitli: eksen/yön testlerinde beklenen deger
**datum ucundan** olculur.

### P03 dilim-2 — eksen sorusu yumusak yola tasindi (2026-09-29 02:47)

`validate_decisions` artik onaylanmamis eksen icin **ret vermiyor** (kayit korunur); `questions()` soruyor:
"Bağlanan ölçünün eksenini (X/Y) ve yönünü seçin." — build bu soru gecmeden baslamiyor (PLAN §8.4/§8.10:
anlam uydurulmaz, kullaniciya sorulur). Test `test_a_record_without_a_confirmed_axis_is_asked_not_filled_in`
olarak guncellendi: kayit yukleniyor, `validate_decisions` geciyor, soru metni uretiliyor ✓.
Kanit: `test_measure_meaning + test_guided + test_user_dimensions + test_guided_geometry_state +
test_guided_geometry_migration` -> **36 passed in 57,69 s**. PLAN.md P03 satiri "calisiliyor" + kanitla
guncellendi.

**P03 kalan maddeler (siradaki is):** (1) arayüzde X/Y secimi ve baglanan iki unsuru gosterme (§8.4 —
`static/guided.js` bag modu; yeni baglarda eksen/yön alanlari gonderilmeli); (2) gorunus ekseni/orijini
gosterme, dondurulmus paftada cerceve karari (§8.6); (3) `edge:<index>` yerine kararli nokta/kenar kimlikleri
ve mevcut kayitlarin acik donusumu, kenar silinince indeks kaymasinin baska koseye baglamamasi (§8.7/§8.8);
(4) profil degisimi/silinen kenarda etkilenen olculerin "yeniden baglama gerekir" durumuna alinmasi (§8.9);
(5) kabul maddesi: degerin basili metinle eslesmesi ile dogru geometriye baglanmasinin ayri tutulmasi.

### P03 dilim-3 — arayuzde eksen/yon secimi (2026-09-29 02:48)

`static/guided.html`: bag akisina **Eksen** (X ekseni boyunca / Y ekseni boyunca) ve **Yön** (ikinci uc
+ eksende / − eksende) secimleri eklendi (bag dugmesinin hemen onunde). `static/guided.js`: iki uc
tiklandiktan sonra eksen/yon secilmemisse bag **kaydedilmiyor** ve durum mesaji soruyor; bag kaydedilirken
tekil karar `id`'si uretiliyor ve `axis`/`direction` gonderiliyor; bag listesinde anlam gorunuyor
(`X+`, `Y−`, yok ise "eksen soruldu"). PLAN §8.4: otomatik eksen karari yok — kullanici seciyor.
Dogrulama: `vm.SourceTextModule` modul sozdizimi ✓; **servis edilen** yol denetlendi (`/guided.js` ve
`/guided` yeni isaretleri iceriyor) — §26-B-4 dersi uygulandi. Gercek tarayicida tiklama kabulu P07'nin
isi; karar/API yolu Python tarafinda yesil (36 passed / 57,69 s).

### P03 dilim-4 — kaybolan referans = "yeniden baglama gerekir" durumu (2026-09-29 02:49)

`guided.py`: yeni `unresolved_bindings(options, decisions)` — secili kontur degisti ya da daire kalkti diye
cozulemeyen uclari (kendi kimligiyle) listeler. `validate_decisions` artik bu durumda **ret vermiyor**
(kayit kullanicinin yazdigi gibi korunur; cerceve siniri denetimi kalir) — PLAN §8.9: en yakin noktaya sessizce
esleme YOK. `questions(decisions, diagnostics, options)` soruyor: "Bağlanan ölçü yeniden bağlanmalı (<kimlik>
…); en yakın noktaya taşınmaz." Cagri yerleri: `make_plan` ve `public()` artik cizimi de geciriyor (build bu
soru gecmeden baslamaz; panel soruyu gosterir).
Testler: `test_guided.py`'nin eski "kaydet ret verir" beklentisi §8.9'a gore guncellendi (kayit korunur,
sorular yeniden baglamayi ister, build durur); `test_measure_meaning.py`'ye ayni kuralin dogrudan testi
eklendi (edge:9 konturda yok). Kosu: `proc_f14e29093a78` (/tmp/p03-set3.txt) — sonuc bildirimle gelecek.

### P03 dilim-4 dogrulandi + siradaki is tasarimi (2026-09-29 02:50)

`test_measure_meaning + test_guided + test_user_dimensions + test_guided_geometry_state +
test_guided_geometry_migration + test_sketch_constraints` -> **59 passed in 56,65 s**: kaybolan referans artik
kaydi dusurmuyor; record aynen korunuyor, sorular "yeniden bağlanmalı (…)" diyor ve build duruyor.

**Siradaki is — §8.7/§8.8 kararli kimlik gecisi (tasarim):**
1. Bag ucunun kimligi artik **kenarin kendi kimligi + ucu** olsun (`<edge_id>:start|end`), indeks degil; UI
   `snapEnd` bu bicimi uretir.
2. `user_dimensions.reference()`: edge id'yi profilde bulup guncel indekse cevirir (`v<index>` /
   `v<(index+1)%n>`); kimlik bulunamazsa **ret** (en yakin koseye esleme yok — §8.9 ile ayni cizgi).
3. `unresolved_bindings`: ayni cozumlemeyi kullanir; bulunamayan uc "yeniden baglama gerekir".
4. Eski kayitlardaki `edge:<sayi>` uclari **acikca donusturulur**: gecis sirasinda (mevcut `_migrated`
   desenine uygun, atomik ve idempotent) sayi gecerliyse kenarin kalici kimligine cevrilir ve gunluge
   "eski indeks kimligi donusturuldu" yazilir; gecersizse uca dokunulmaz ve yeniden baglama istenir. Sessiz
   kaydirma yok.
5. Testler: kenar silinince/takilinca ayni uc ayni kenara bagli kalir; eski kayit donusumu dogru kenara
   gider; gecersiz eski indeks "yeniden baglama" ister.
**§8.6 (gorunus ekseni/orijini):** UI'da eksen/orijin gosterimi + dondurulmus paftada cerceve karari — bu
dilimden sonra.

### P03 dilim-5 — kararli uc kimlikleri (kod indi, set kosuyor) (2026-09-29 02:51)

`guided.py` `user_dimensions.reference()`: bag ucu kimligi artik **kenarin kendi kimligi + ucu**
(`<edge_id>:start|end`) — indeks degil; kimlik profilde bulunamazsa **ret** ("bağ ucu artık bu konturda yok").
Eski `edge:<sayi>` bicimi yalnizca o kenar hala konturda ise ve **kullanicinin kendi tiklamasiyla** (stored
x/y) hangi uc oldugu belirlenerek cozulur; gecersizse ret. `unresolved_bindings` ayni cozumlemeyi kullaniyor;
taninmayan kimlik de "yeniden baglama" ister. Gercek paftalarda kenar kimlikleri anlamli (`g1`, `g0`, ...) —
indeks degil — oldugu dogrulandi.
`static/guided.js` `snapEnd`: vertex adaylari `e.id:start` / `e.id:end` uretiyor; modul sozdizimi ✓.
Testler: `test_user_dimensions` ve `test_measure_meaning` yeni bicime gecti; yeni `tests/test_stable_identities.py`
(uc test): zincir sirasi degisince tie ayni kenari takip eder; eski indeks ucu kullanicinin tikiyla cozulur;
cozulemeyen uc yeniden baglama ister ve son cozucuye ulasmaz.
Kosu: `proc_596b81db6358` (/tmp/p03-set4.txt) — sonuc bildirimle gelecek.

### P03 dilim-5 duzeltme (2026-09-29 02:52)

Ilk kosuda 2 test dustu ve **kusur bendeydi**: eski bicim `edge:<sayi>` (yani "edge:" onekiyle) iken ilk
uygulamam yalnizca **cipiak sayi** kabul ediyordu; bu yuzden (a) yeni testteki `edge:1` ucu cozulemedi ve
(b) `test_guided.binding_record`'un `edge:0/1/3` uclari "geçerli bir uç kimliği değil" diye isaretlenip
sorular listesini doldurdu. Duzeltme: eski bicim `edge_key == "edge" and tail.isdigit()` olarak ayristiriliyor
(ciplak sayi da tolera ediliyor); gecersizse mesaj kimligi aynen alintiliyor. Yeniden kosu:
`proc_ca51fc1668cf` (/tmp/p03-set5.txt).

### P03 dilim-5 ikinci duzeltme (2026-09-29 02:55)

Duzeltmeden sonra `test_guided` geri yesil (61 passed), yalnizca **benim yeni testim** dustu: tie eksen-X
anlamli iken ben **oklid uzakligini** olctum; kod dogruydu. v0→v2 tie'sinda x farki 60'a sabitleniyor, y
izlenen deger (100) olarak kaliyor; olculen diyagonal sqrt(60² + 100²) = 116,62 cikti — kodun degil, testimin
yanlisi. **Ders (ayni sinif hata):** eksen ölçüsünde beklenen deger eksen farkidir; diger koordinat izlenen
kalir. Test artik dx = 60 sabitini ve diyagonalin sqrt(60²+100²) oldugunu ayri ayri dogruluyor.
Yeniden kosu: `proc_7cb9de5731b2` (/tmp/p03-set6.txt).

### P03 dilim-5 dogrulandi — kararli uc kimlikleri (2026-09-29 02:55)

`test_stable_identities + test_measure_meaning + test_user_dimensions + test_guided +
test_guided_geometry_state + test_guided_geometry_migration + test_sketch_constraints` ->
**62 passed in 59,72 s**. Bag ucu kimligi artik `<edge_id>:start|end` (kenarin kendi kimligi; gercek paftalarda
`g1`, `g0`, ...); eski `edge:<sayi>` ucu yalnizca o kenar dururken ve kullanicinin kendi tiklamasiyla cozulur;
cozulemeyen uc "yeniden baglama" ister, cozucuye ulasmaz; zincir sirasi degisse de tie ayni kenari takip eder.

**P03 kabul listesi -> mevcut test eslesmesi (sweep icin):**
- X/Y ve yon: `test_measure_meaning` (onaylanan eksenin hangi koordinati sabitledigi X ve Y icin ayri olculdu;
  yon alani iki-tekil-karar testinde kullaniliyor) — **yon icin ayri test yok (dolayli)**.
- mm/inç: `test_measure_meaning` 1,0 in -> 25,4 mm ✓.
- silinen kenar: `test_stable_identities` (cozulemeyen uc -> yeniden baglama) + `test_guided` (kayit korunur,
  build durur) ✓; eski surum: `test_guided_geometry_migration` + eski `edge:<sayi>` testi ✓.
- profil degisimi: **ayri test yok** — tie bir profilin kenarina bagliyken baska profile gecilince o ucun
  "yeniden baglama" istedigi dogrudan sinanmadi (kabul maddesi).

**Kalan is sirasi:** (1) profil degisimi maddesi icin test (muhtemelen hemen geciyor: kimlik yeni profilde
yok); (2) §8.6 gorunus ekseni/orijini + dondurulmus paftada cerceve karari; (3) P03 kabul listesinin toptan
sinamasi -> "dogrulandi" karari; (4) P04 (100x100 kare cift-bag tekrari; kose-bagi kapisi engeli).

### P03 kabul maddeleri icin iki test (kosu suruyor) (2026-09-29 02:55)

`test_stable_identities.py`'ye eklendi:
1. **profil degisimi:** tie `outline_0`'in `e0/e1` kenarlarina bagli; karar `outline_1`'e gecince `unresolved_bindings`
   iki ucu da "bu konturda olan bir nokta değil" diye isaretler ve cozucu ret verir (en yakin koseye kaydirma yok).
2. **yon (dogrudan sinama):** ayni tie, `direction=+1` iken ikinci uc = birinci + 60; `direction=-1` iken = birinci
   − 60 — yon kullanicinin karari, tiklama sirasindan tahmin degil. Bu test ayni zamanda **prob**: yon alani
   saklanip cekirdek bagina uygulanmiyorsa burada kirmizi cikar; o durumda teshis "yon saklaniyor ama
   uygulanmiyor" olur ve siradaki is `user_dimensions`'in cekirdek `DimensionBinding` degerini `direction` ile
   isaretlemek olur.
Kosu: `proc_5d2de3505242` (/tmp/p03-set7.txt).

### P03 kabul listesi yesil (2026-09-29 02:56)

`test_stable_identities (5) + test_measure_meaning + test_user_dimensions + test_guided +
test_guided_geometry_state + test_guided_geometry_migration + test_sketch_constraints` ->
**64 passed in 57,08 s**. Iki yeni kabul testi ilk kosuda gecti:
- profil degisimi: eski tie'lar yeni konturda cozulemez, "yeniden baglama" ister (kaydirma yok) ✓
- yon dogrudan sinandi: `direction=+1` -> ikinci uc = birinci + 60; `direction=-1` -> birinci - 60 ✓
  (yani yon alani saklanmakla kalmiyor, cekirdek bagina da uygulaniyor — prob temiz cikti.)

**P03'te kalan tek kod maddesi §8.6** (gorunus ekseni/orijini + dondurulmus paftada cerceve karari). Tasarim
notu: `observe` cizimin kendi cercevesini (pafta kenari/cerceve dikdortgeni) ve eksen yonunu urun olarak
vermeli; UI bunu gostermeli; pafta dondurulmusse cerceve **gorsel kenarlardan** degil **paftanin kendi
cercevesinden** kurulmali ve kullanici karari onaylanmali. Sonraki pencere: §8.6 -> P03 toptan kabul ->
`PLAN.md`de "dogrulandi" -> P04 (100x100 kare cift-bag tekrari).
