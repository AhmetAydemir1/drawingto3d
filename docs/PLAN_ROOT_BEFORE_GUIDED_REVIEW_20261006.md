# drawingto3d — ayrıntılı uygulama planı

Güncelleme: **2026-09-29, goal sonrası bağımsız denetim**.
**Yön doğru ve çalışan değişiklikler var; P01/P02'nin bütün kabul koşulları henüz geçmedi.**
Bu tur kaynak kod değiştirilmedi; testler ve küçük kusur tekrarları çalıştırıldı, plan/devir güncellendi.

## 1. Önce bunu oku

**Hedef:** M1 / 16 GB cihazda, kurulumdan sonra çevrimdışı çalışan; farklı teknik çizim PDF/PNG/JPG dosyalarını ortak geometri, ölçü ve CAD işlemleriyle STEP'e dönüştüren bir program. Belirsiz veya yanlış okunan yerlerde kullanıcı çizimin üzerinde düzeltme yapabilmeli.

**Kapsam geneldir.** `examples/pdf with steps` yalnız test/değerlendirme verisidir. Bir parçanın çalışması ürünün kapsamını o parçaya daraltmaz. Yeni parçalar aynı genel mekanizmaların farklı birleşimleriyle işlenmelidir.

### Şimdi ne yapacaksın?

1. Bu belgenin 1–4. bölümleriyle [güncel denetimi](eval/reports/goal-progress-audit-20260929.md) oku.
2. **İlk kod işi A0:** Bozuk ölçü bağlama HTML'ini onar; ardından profil seçimi kaldırılınca oluşan hatayı kapat.
3. Sonra sırayla **P01-a/b geçiş/çıktı işleri → P02-a/b/c matematik → P03-a/b/c kimlik/çerçeve → P04-a…P04-f**. P01-c'deki rapor görünürlüğü P04-c ile birlikte kapanır; bu açık P02'ye başlamayı engellemez.
4. Bu kapılar geçince P05 → P06 → P07 → P08'e ilerle. P09–P12 daha geniş ürün kapsamıdır.
5. P00 başlangıç kaydı zaten var. Yeni turda kısa çalışma ağacı/sürüm kaydı al; tamamlanmış kopyalama veya maksimum açıklık düzeltmesini sıfırdan yazma.
6. Her küçük teslimde ilgili kabul testini çalıştır ve durum tablosunu/devir başlıklarını güncelle.

**Eski “tek kalan iş görünüş ekseni” yönlendirmesi geçersizdir.** Otomatik pafta çerçevesi dedektörüyle başlamayın. Önce arayüz, geçiş, kimlik ve geometri doğruluğu açıklarını kapatın.

[İlk plan arşivi](docs/PLAN_HISTORY_BEFORE_DETAILED_20260929.md), [son goal'un plan kaydı](docs/PLAN_HISTORY_BEFORE_REAUDIT_20260929.md) ve [eski uygulama günlüğü](docs/IMPLEMENTATION_HISTORY_BEFORE_REAUDIT_20260929.md) korunmuştur. Bunlardaki tamamlandı iddiaları tarihsel kayıttır; güncel durum aşağıdaki tablodur.

### Değişmez kurallar

- Üretimde dosya adı, örnek numarası, bilinen koordinat, sabit delik sayısı veya referans STEP'e göre özel çözüm yazma.
- Referans STEP yalnız ayrı değerlendiriciye girebilir. Okuyucuya, model istemine, önericiye veya üretim yoluna cevap kaynağı olarak verilmez.
- Test klasörünü eğitim, ince ayar veya benzer parça getirip kopyalama kaynağı yapma.
- Daha önce incelenmiş çizimler regresyon verisidir; tekrar “görülmemiş” diye raporlanmaz.
- Eksik ölçü/görünüş birden fazla şekle izin veriyorsa ilgili bilgiyi kullanıcıdan al. Varsayımı ölçü diye sunma.
- Geçerli katı, doğru dış ölçüler ve STEP'in yeniden açılması tek başlarına bütün parçanın doğruluğunu kanıtlamaz.
- Mevcut değişiklikleri ve oturumları koru. `git reset`, `git clean`, toplu silme veya eski oturumların yedeksiz üzerine yazılması yok.
- Modelin önerileri sürümlü veridir; geometri/ölçü kontrollerinden geçer. Serbest Python üretip çalıştırma genel ürün yolu değildir.
- Test beklentisini hatalı kodun çıktısına uydurma. Başlangıç girdisi gerçekten hatalıysa bunu bağımsız matematikle göster ve kayda geçir.
- Hata açıklaması eklemek, o hatayı düzeltmek veya kabul koşulunu karşılamak değildir.

## 2. Durum ve tamamlanma kapıları

Durumlar: `bekliyor`, `çalışılıyor`, `doğrulandı`, `engelli`.
Bir aşamanın bir alt davranışı doğrulanabilir; aşamanın bütün koşulları geçmeden tamamı kapatılamaz.

| Aşama | Teslim | Güncel durum | Kanıt / açık iş |
|---|---|---|---|
| A0 | Kullanılabilir arayüzü geri getir | doğrulandı | HTML onarıldı — `html.parser`: belge dengeli, dört kimlik doğru türde ve birer kez (`tests/test_guided_html.py`); profil kaldırma artık soru üretir (store yolu + birim testi; odak set **69 passed / 58,53 s**). Gerçek tarayıcıda `/guided`: dosya yükleme → kalibrasyon (80 mm, px/mm 12,9893) → kontur `outline_1` → bağ **"30.32 mm · X+ · g8 ↔ g9"**; kayıtta `axis:'x'`, `direction:1`; **sayfa yenilendiğinde bağ ve kayıt korundu** |
| P00 | Başlangıç kaydı ve kusur tekrarları | doğrulandı | Önceki kayıt + bu denetimin kaynak özetleri ve küçük tekrarları |
| P01 | Temel geometri ve güvenli oturum geçişi | çalışılıyor | **P01-a/b doğrulandı (53 passed / 65,98 s).** P01-a: ham kayıt yedeği (`session.backup.json`), gerçek kimlik karşılaştırması (F03: `measurements[].id`, sıralı kenar kimlikleri), kimlik uyuşmazlığı/okunamayan kaynakta güvenli durdurma, idempotent hatırlama. P01-b: build kimliği = kaynak özeti + geometri sürümü + karar revizyonu; eski çıktı (başarılı geçişten sonra da) `historical`, güncel URL ve `artifact()` istemleri aynı kurala bağlı; `load` kaynak değişmiş/eksikken durum yazar (çökmez), `recheck` kurtarmayı sağlar. P01-c'nin rapor görünürlüğü maddesi P04-c'ye bağlı açık |
| P02 | Doğru kontur denetimi | doğrulandı | Maksimum açıklık düzeldi; beş bağımsız karşı örnek hâlâ yanlış sonuç veriyor |  **P02-a doğrulandı (36 passed / 23,60 s):** tek kanonik yay tanımı (`contour_audit.arc_page_ends`; sayfa açısı = −kanonik), zincir kanonikten kuruluyor, iki uç ayrı ayrı karşılaştırılıyor (`arc_start_mismatch`+`arc_end_mismatch`), sıfır/tam-tur süpürme ayrı tanı; F07 canlı tekrarla kanıtlandı, üç tutarsız fixture doğru kanonik çiftle düzeltildi, iki karşı örnek regresyon oldu.  **P02-b doğrulandı (41 passed / 23,99 s):** destek eşitliği artık sayısal (`SUPPORT_TOLERANCE_PX=0.35`) — %2 yarıçap kuralı kaldırıldı; R100/R99 yarım halka geçiyor; çizgide tek-piksel inme kuralı (`STROKE_TOLERANCE_PX=1.0`) ile ileri/geri 0,8 px tekrar `overlap`+`zero_area` ile reddediliyor; örtüşme 512×512 örnekleme yerine **normalize aralıkların kesişimi** (`angular_overlap_radians`, sarmalama ayrı aralık).  **P02-c doğrulandı (47 passed / 26,38 s):** çizgi–yay ve yay–yay kesişimi **analitik** (quadratic / iki-çember), komşu çift bütünüyle atlanmıyor (yalnız kendi birleşimi), komşu olmayan uç teması `endpoint_touch` ile reddediliyor ve karar **yansıma/ters gezinmede aynı** (line-line testi parametrik; çapraz çarpım işareti kullanılmıyor). F09 (±√1999) ve F10 regresyon testi oldu. **P02'nin zorunlu kabulünden kalan tek parça:** **CAD yay uçlarıyla bağımsız karşılaştırma** (plan entity'leri `guided.py:801`'de `start_degrees=a, end_degrees=b` alıyor; CAD uçlarının denetimin kanonik uçlarıyla sayısal karşılaştırması yazılacak).  P02-c.7 zaten karşılanıyor: `joins`/`join_max_px` (guided.py:233–281), `applied_move_px` (:332), son kalan açıklık denetimde (`closure_px`, guided.py:514 notu).
| P03 | Ölçü anlamı ve kararlı referanslar | çalışılıyor | X/Y/yön ve yeni uç kimlikleri var; eski referans dönüşümü, profil/sürüm, silinen kenar ve çerçeve açık |  **P03-b-1 doğrulandı (53 passed / 73,98 s):** `BindingEnd` artık `profile` + `geometry_version` + fiziksel `end` etiketi taşıyor; uç çözümlemesi **tek ortak fonksiyonda** (`resolve_binding_end`) ve **tamamen fiziksel** (saklanan tıklama noktası hangi uç olduğunu belirler; etiket kanıttır) — kontur ters yüründüğünde etiketler yer değiştirse de bağ **aynı köşede** kalıyor; başka konturda seçilmiş uç (`profile` farklı) id metni aynı olsa bile yeniden bağlama istiyor; tıklama artık kenarın uçlarına oturmuyorsa bağ 'uçlarında değil' diye soruluyor (en yakın köşeye kaydırma yok). Kaydet kapısı ve `questions()` aynı listeyi okuyor (`_binding_end_issues`). Sıradaki: **P03-b-2** (kayıt yolunun bu alanları yazması: save backfill + `guided.js` `snapEnd`), sonra §8.6 çerçeve/eksen maddesi ve P03 kabul kararı.  **P03-b-2 kodu (arayüz kabulü bekliyor):** `_with_end_evidence` kayıt yolunda (save + accept) eksik `profile`/`geometry_version`/`end` alanlarını yazıyor ve günlüğe geçiriyor; çözülemeyen uç **bilerek** yazılmıyor (en yakına sabitleme yok); `guided.js` `snapEnd` artık seçildiği konturu, `state.geometry.version`'ı ve fiziksel ucu gönderiyor (sunucu yeniden başlatıldı; servis edilen `/guided.js`'te doğrulandı: `geometry_version` ×2, `profile:state.decisions.profile_id` ×2, `end:'start'` ×1; `GET /guided` 200). Test: `test_binding_end_meaning.py` **4 passed / 2,94 s** (plaka oturumu + gerçek `save`). Kalan: gerçek tarayıcıyla uç seç → kaydet → kayıtta üç alan; sonra §8.6 çerçeve/eksen maddesi ve P03'ün toptan kabul kararı.  **P03-b-2 arayüz kabulü ✓ (gerçek tarayıcı, oturum `39b0db42439f406c97121609ffe2038b`):** plaka paftası yüklendi → "Önerileri onayla" gerçek tıklamayla → `outline_1` + kalibrasyon (7,8755 px/mm) → bağ modu → iki gerçek tıklama (`g1:start` [435,76 / 1209,53] ve `g1:end` [1223,3 / 1209,43]) → panel satırı **"100 mm · X+ · kontur g1:start ↔ kontur g1:end"**, durum "Karar kaydedildi." → **kayıtta üç kanıt alanı**: `profile:"outline_1"`, `geometry_version:3`, `end:"start"/"end"`. Eksen/yön seçilmeden yapılan ilk denemede arayüz **kaydetmedi** ve "Bağlanan ölçünün eksenini (X/Y) ve yönünü seçin…" dedi (P03 dilim-2 sözleşmesi arayüzde ✓). **Dürüst sapma:** eksen/yön `<select>` değerleri bu headless oturumda gerçek fare+klavye ile kurulamadı (ok tuşları native seçiciyi oynatmadı); değerler betikle kurulup **gerçek `change` olayı** gönderildi — geometri tıklamaları gerçek. Takip: mümkünse normal (headless olmayan) tarayıcıda seçici kabulü tekrarlanmalı.
| P04 | Çözümün bütün ürün yoluna doğru uygulanması | bekliyor | Yerel ölçü gövde ölçeğini değiştiriyor; geçerli X/Y çifti reddediliyor; unsupported plan kabul ediliyor |
| P05 | Genel kontur düzenleme | bekliyor | Mevcut çıkarma/onay akışını koru; ekleme/kırpma/alt zincir ve önizleme eksik |
| P06 | Oturum/API dayanıklılığı | bekliyor | Geçiş ve çözüm verileriyle gerçek revizyon/geri alma/hata kabulü |
| P07 | Gerçek tarayıcı kabulü | bekliyor | A0 açılış kontrolü ilk adım; tam kullanıcı akışı ayrıca yapılmalı |
| P08 | Bağımsız tam parça ve efor ölçümü | bekliyor | Özellik konumu/çap/derinliği, kullanıcı müdahalesi ve saklı veri |
| P09 | Giriş/görünüş/CAD kapsamı | bekliyor | Ortak işlemlerle kapsam genişletme |
| P10 | Yay kısıtları ve geniş geometri | bekliyor | Matematiksel destek, başarısızlık ve CAD doğrulaması |
| P11 | Yerel model önerileri | bekliyor | Modelsiz temel ile ölçülmüş karşılaştırma |
| P12 | Koşula bağlı eğitim | bekliyor | Ayrı veri, hata hedefi ve cihaz ölçümü |

**Son doğrulama:** 11 dosyalık odak koşusunda **90 geçti; 1 HTTP testi sandbox port izninde durdu** (57,96 sn). Aynı HTTP testi izinli localhost koşusunda **1 geçti** (0,86 sn). Böylece seçilen 91 test iki koşuda geçti; tam test takımı bu tur çalıştırılmadı. Buna rağmen aşağıdaki yeni kusur örnekleri mevcut testlerin kapsamadığı yanlış davranışları gösterdi.

**İlk kullanılabilir teslim:** Desteklenen profil uzatma + delik/cep akışında P01–P08'in bütün koşullarının geçmesi. Bu kilometre taşı genel ürün hedefini tamamlamaz.

## 3. Ne ilerledi, ne açık?

### Korunacak ilerleme

- `make_plan` artık `options` üzerinde iç içe bağımsız kopya kullanıyor. Yeni oturumda ölçü ekle/kaldır/geri al ve yeniden açma store testi geçti.
- Eski oturumlar için geometri sürümü/geçiş iskeleti eklendi; güvenli eşleşme ve sonuç güncelliği tamamlanmalı.
- `closure_px` bütün birleşimlerin en büyüğünü koruyor; son birleşim önceki açıklığı silmiyor.
- Yay örtüşmesi kiriş yerine açı örneklerine bakıyor. Bu ilerleme matematiksel kabul için henüz yeterli değil.
- `Binding.id`, `axis`, `direction` var. Yeni uçlar `<edge_id>:start|end` kullanıyor; eksik eksen için soru soruluyor.
- Çözücü zaten ürün yoluna bağlı. Görev yeniden entegrasyon yazmak değil, mevcut bağlantının semantiğini ve sonuçlarını düzeltmek.

### Bu denetimdeki somut açıklar

| Kimlik | Tekrar edilen davranış | Beklenen | İş |
|---|---|---|---|
| F01 | HTML ayrıştırıcısında `bind-start=None`; JS bu elemana `.onclick` atıyor | Tek geçerli düğme ve hatasız yükleme | A0 |
| F02 | Bağ varken profil `None` yapılınca `AttributeError` | Kararlar korunur, kontur seç/yeniden bağla sorusu | A0 |
| F03 | Kenar ve ölçü kimlikleri değişmişken `_same_geometry=True` | Güvenli eşleşme veya açık yeniden seçim | P01 |
| F04 | `geometry_stale=True` iken eski STEP güncel URL ile sunuluyor | Eski çıktı tarihsel; güncel indirme yok | P01 |
| F05 | Eski `edge:0` bağı başka profile geçince `unresolved=[]` | Eski anlam korunur veya bağ geçersizleşir | P03 |
| F06 | Yeni bağ farklı profilde aynı edge ID ile geçiyor; çıkarılan kenar bağları çözülmüş görünüyor | Profil/sürüm/düzenleme kapsamı denetlenir | P03 |
| F07 | Kanonik açıyla çelişen yay ucu kabul ediliyor | CAD ile aynı yay tanımı; tutarsız iki uç reddedilir | P02 |
| F08 | R100/R99 geçerli yarım halka çakışma diye reddediliyor | Ayrı çemberler ayrı destek sayılır | P02 |
| F09 | R1000 yay ile y=999 çizgisinin gerçek kesişimleri kaçıyor | Geçersiz halka reddedilir | P02 |
| F10 | Komşu olmayan temas Y yansımasına göre farklı sonuç veriyor | Yansıma altında aynı doğru ret | P02 |
| F11 | Aynı 0,8 px çizginin ileri/geri tekrarı geçiyor | Sıfır alan/örtüşme reddedilir | P02 |
| F12 | Kalibrasyonla 100 mm gövde, yalnız merkez mesafesi bağlanınca 50 mm oluyor | Yerel ölçü kalibrasyonu değiştirmez | P04 |
| F13 | Geçerli X=50/Y=30 köşe bağları tek ölçek kapısına takılıyor | Bağımsız kısıtlarla çözüm | P04 |
| F14 | Çekirdek `unsupported` döndürdüğü halde `make_plan` plan veriyor | İstenen ölçü uygulanmıyorsa üretim durur | P04 |

F14 için bu tur plan üretimine kadar prob yapıldı; ayrıca yeni STEP build edildiği iddia edilmiyor. F01 kaynak/HTML ayrıştırıcı kanıtıdır; bu denetimde canlı tarayıcı kabulü yapılmadı.

**Diğer açık P04 işleri:** çekirdeğin `derived` ifadeleri kayboluyor; hesaplanan koordinatlar `user` sayılabiliyor; çözüm sonrası orijin değişiyor; son kontur yeniden denetlenmiyor; ilgisiz daireler çözüme giriyor. `Decisions` yatay/dikey ilişki ve görünüş çerçevesi sözleşmesini henüz taşımıyor.

### Kanıtları nasıl kullanacaksın?

Küçük girdiler ve çıktılar [eval/audits/20260929-goal](eval/audits/20260929-goal/) içinde kalıcı olarak saklandı. Komutlar depo kökünden:

```sh
PYTHONPATH=src .venv/bin/python eval/audits/20260929-goal/contour_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20260929-goal/audit_geometry_state_probe.py
PYTHONPATH=src .venv/bin/python eval/audits/20260929-goal/constraints_ui_probe.py
```

Bunlar **denetim tekrarlarıdır, ürün kabul testleri değildir**. Özellikle state probu mevcut hatalı davranışı assert eder; düzeltmeden sonra bu assertion'ın kırılması beklenir. Girdileri kalıcı testlere aktarırken beklentiyi yukarıdaki doğru davranışa çevir. Hatalı çıktıyı koruyan testi yeşil tutma.

Geçmiş 585-test koşusu ve örnek parçalardan elde edilen geçerli katılar tarihsel kanıttır. Küçük kontur parçası veya gerçek delik kesilmeden görülen çözüm satırı, tam parça başarısı sayılmayacak.

## 4. Teknik yön ve dosya haritası

### Tek geometri hazırlama yolu

Önizleme, soru üretimi ve STEP üretimi aynı revizyonu aynı kurallarla yorumlamalı:

```text
kaynak dosya + kaynak özeti + sayfa/görünüş
  → değişmeyen temel gözlemler/geometri
  + geçerli revizyonun kullanıcı kararları
  → bağımsız çalışma kopyası
  → kontur düzenleme işlemleri
  → düzenlenen konturun ön denetimi
  → kullanıcı kalibrasyonu ve sabit koordinat sistemi
  → desteklenen ölçü/ilişki kısıtlarının çözümü
  → çözülen son geometrinin denetimi
  → aynı son geometriyle önizleme + GeneralPlan
  → CAD + STEP yeniden açma + özellik kontrolleri
  → yalnız ilgili revizyona ait sonuç
```

`prepare_geometry` adıyla veya aynı işi yapan mevcut bir fonksiyonla bu yolu merkezileştir. İsim zorunlu değildir; davranış zorunludur. Fonksiyonun girdiyi değiştirmemesi, tekrarlanabilir olması ve hata durumunda CAD üretimine uygun sonuç vermemesi test edilmelidir. Onarım ekranı hata durumunda kaynak/ara geometriyi ve sorunlu noktaları göstermeye devam edebilmeli; bu önizleme üretim onayı sayılmamalı.

Üç ayrı veri katmanı tut:

1. **Temel geometri:** kaynak özeti, geometri şema/okuyucu sürümü, kaynak koordinatları ve kararlı kimlikler. Build bunu değiştirmez.
2. **Kararlar:** profil, kalibrasyon, ölçüler/ilişkiler, delikler/cepler, kontur düzenlemeleri ve kullanıcının onayları. Geri alma bu kararların geçmişine döner.
3. **Hesaplanan sonuç:** karar revizyonu, çözülmüş geometri, denetimler, kaynak açıklamaları, build durumu ve dosya yolları. Yeni karar eski sonucu güncel olmaktan çıkarır.

Piksel, PDF sayfa koordinatı, görünüş koordinatı ve milimetreyi açıkça ayır. Kalibrasyon `px/mm`; çözücü koordinatları milimetre ve Y yukarıdır. Orijin/datum ve dönüşüm bir revizyonda sabit olmalı. Çözüm sonrası yeni minimum sınır kutusuyla orijini sessizce değiştirme.

### Önce okunacak dosyalar

| Dosya | İncelenecek yer |
|---|---|
| `src/drawingto3d/guided.py` | `Decisions`, `Binding`, `ContourFix`, `validate_decisions`, `sketch_diagnostics`, `questions`, `bindings_solvable`, `correct_profile`, `user_dimensions`, `make_plan`, `_changed_fields`, `GuidedStore` |
| `src/drawingto3d/sketch_constraints.py` | `PointRef`, `DimensionBinding`, `EdgeRelation`, `SketchConstraints`, `solve_constraints` |
| `src/drawingto3d/contour_audit.py` | `edge_points`, `_same_support`, `_overlap_extent`, `audit_contour` |
| `src/drawingto3d/general.py` | `Parameter`, `GeneralPlan`, `evaluate_parameters`, `compile_general`, `build_general`, `edit_parameters` |
| `src/drawingto3d/geo.py` | CAD'e aktarılan yay yönü ve açı sözleşmesi |
| `src/drawingto3d/app.py` | guided HTTP uçları, revizyon/hata/artefakt davranışı |
| `src/drawingto3d/static/guided.js` ve `guided.html` | seçim, dönüşüm, kayıt, çözüm raporu ve indirme |
| `tests/test_guided.py`, `test_user_dimensions.py`, `test_sketch_constraints.py` | Gerçek karar/store yolu ve mevcut yardımcı testler |
| `tests/test_contour_audit.py`, `test_contour_fix.py` | Geometri tanıları ve düzeltme sınırı |

Yeni testler artık mevcut: `test_guided_geometry_state.py`, `test_guided_geometry_migration.py`, `test_measure_meaning.py`, `test_stable_identities.py`, `test_contour_audit_matrix.py`, `test_contour_audit_p02_repeats.py`. Bunları genişlet. `test_guided_workflow.py` gibi henüz oluşturulmamış isimler öneridir. Benzer sorumluluk için ikinci bir paralel uygulama yazma.

## A0 — Önce arayüzü yeniden kullanılabilir yap

**Dosyalar:** `static/guided.html`, `static/guided.js`, `guided.py:unresolved_bindings`; ilgili arayüz ve store testleri.

### A0.1 — Bozuk HTML

1. `guided.html` içindeki `<button <div ...> ... id="bind-start"` yapısını bul. Eksen/yön seçicileri bağımsız bir satır, bağlama düğmesi geçerli ayrı bir `button` olsun.
2. `bind-start`, `bind-cancel`, `bind-axis`, `bind-direction` kimlikleri tekil ve JS'in beklediği eleman türünde olsun. `null` kontrolü ekleyip düğmeyi devre dışı bırakmak kusurun çözümü değildir.
3. HTML ayrıştırma kontrolü ekle: bu dört gerçek elemanın varlığını doğrula. JS sözdizimi testi tek başına HTML/DOM doğrulaması değildir.
4. Uygulamayı normal HTTP yolu `/guided` üzerinden aç; JavaScript hata vermeden başlasın ve dosya yüklemeden sonra kontur/ölçü kontrolleri çalışsın. `file://` açmaya çalışma.
5. Yeni Eksen/Yön seçiminin bağ kaydına girdiğini ve sayfa yenilendiğinde korunduğunu kontrol et. Tam delik/STEP kabulü P07'de ayrıca yapılacak.

**Kabul:** DOM kontrolü geçer; sunulan HTML/JS günceldir; tarayıcı açılış/ölçü bağlama akışı çalışır. Tarayıcı aracı engelliyse “kaynak kontrolü geçti, tarayıcı kabulü açık” diye kaydet.

### A0.2 — Profil seçimi kaldırıldığında hata yerine soru

1. Bağlar varken `profile_id=None` durumunu normal eksik karar olarak ele al.
2. `unresolved_bindings` profil yokken `profile.get` çağırmasın. İlgili bağları ve “kontur seç” sorusunu döndürsün.
3. Gerçek store/API yolunda profil seç → bağ ekle → profil seçimini kaldır → kaydet → yeniden aç zincirini sınayın. Karar geçmişi kaybolmasın, API 500 vermesin, STEP üretimi gerekli kararı beklesin.

**A0 bitince:** Çalışan alanları koruyup aşağıdaki P01 kalanlarına geç.

## 5. P00 — Başlangıcı kaydet ve kusurları küçük örneklerle sabitle

**Durum:** İlk kayıt tamamlandı. Yeni tur için kısa bir sürüm/çalışma ağacı kaydı ekle; eski P00 işini yeniden büyük bir teslim gibi yapma.

**Amaç:** Sonraki modelin yanlış durum varsayımıyla başlamasını ve kesilmede kanıt kaybını önlemek.

1. Proje kökünde `git status --short`, `git rev-parse HEAD` ve Python sürümünü kaydet. İzlenmeyen kaynak/test dosyalarını da envantere al.
2. Kullanıcının mevcut değişikliklerini kendi düzenlemelerinle karıştırıp silme. Aynı dosyada çalışan ajan varsa dosya sorumluluğunu ayır.
3. Yeni, benzersiz bir `out/plan-run-<zaman>/` klasörü aç. Komutlar, çıkış kodları, süreler ve küçük tekrar girdileri burada bulunsun.
4. Kalıcı özeti `eval/reports/implementation-status.md` dosyasına yaz veya güncelle. `out/` Git dışındadır; önemli küçük kusur girdisini/testini yalnız orada bırakma.
5. Yukarıdaki 585/18 sonuçlarının tarihsel olduğunu yaz. Mevcut tam takım yaklaşık 16 dakika sürdüğü için önce ilgili testleri çalıştır; sırf başlangıç sayısı edinmek için aynı pahalı takımı tekrar tekrar çalıştırma.
6. P01 mutasyonu ve P02 iki yarım yay/açıklık kusurlarını bağımsız küçük girdilerle tekrarla. Beklenen sonucu testte önceden belirt; hatalı mevcut çıktıyı beklenen sonuç yapma.

**Kabul:** Başlangıç dosyaları ve kanıt yolları belli; her doğrulanmış kusurun en az bir tekrarı veya açıkça belirtilmiş tekrar engeli var. Tarihsel test sonucu yeni kodun sonucu diye sunulmuyor.

**Engel olursa:** Ortam/bağımlılık hatasını geometri başarısızlığı sayma. Eksik dosyayı kayda geçir; eski kullanıcı oturumlarını onarmaya başlamadan P01 geçiş tasarımını tamamla.

## 6. P01 — Kopyalama düzeltmesini koru, geçiş güvenliğini tamamla

**Durum:** Yeni build'de iç içe kopyalama ve temel seçeneklerin değişmemesi geçti. Aşağıdaki kalanlar bitmeden P01'i kapatma.

**Dosyalar:** `guided.py` içindeki `_geometry_ids`, `_same_geometry`, `_migrated`, `load`, `public`, `artifact`, `build`; `test_guided_geometry_state.py`, `test_guided_geometry_migration.py`, `test_guided.py`.

### P01-a — Eski kayıt korunur, eşleşme açıkça doğrulanır

1. Geçişten önce ham oturumu/kararları atomik ve tekrar açılabilir bir yedeğe al. Kullanıcının eski dosyası yeni seçeneklerle yedeksiz değiştirilmesin.
2. Eşleşmede yalnız profil ve daire adlarını kullanma. Gerçek ölçü alanı `measurements[].id`'dir; burada olmayan `span_id` alanını okumayı düzelt.
3. Kaynak özeti, okuyucu/geometri şema sürümü, profil üyeleri, kenar kimlikleri ve uç yönlerinin anlamını doğrula. Aynı sayıda veya aynı indeks adında şekil bulunması aynı geometri anlamına gelmez.
4. Eski koordinatların çözücü tarafından değiştirilmiş olabileceğini hesaba kat. Basit sayısal koordinat eşitliği şartı da yeterli çözüm değildir; kaynak gözlem/kimlik eşleşmesi kurulmalı.
5. `solved_dimensions` işaretinin bulunmaması eski kaydın özgün olduğunu kanıtlamaz. Eski sürümü doğrulanmamış olarak ele al; güvenilir kaynakla doğrula veya açık yeniden seçim iste.
6. Birim testindeki sahte kaynak okunamadı diye üretim geçiş kuralını gevşetme. Yeni-sürüm fixture'ına doğru sürümü yaz; gerçek eski-kayıt testinde okuyucuyu açık fixture ile denetle.
7. Kararların ve undo geçmişinin kimlik dönüşümü P03 ile ortak sözleşmeye bağlansın. Belirsiz eşleşmede eski karar korunur fakat yeniden bağlama gerekir; en yakın noktaya otomatik taşınmaz. P01 geçiş kapısı için belirsiz referansı koruyup üretimde kullanılmasını engellemek yeterlidir; eksiksiz kalıcı kimlik dönüşümü P03-a/b'de tamamlanır. P03 bitmedi diye P01-a/b'nin güvenli durdurma teslimini bekletme.

**Kabul girdileri:** Profil/daire sayısı aynıyken kenar kimliği değişimi; ölçü `id` değişimi; aynı edge ID'leriyle sıra/yön değişimi; işaretsiz eski sürüm; eşleşen gerçek eski oturum; okuyucunun hata vermesi; atomik yazmanın ortada kesilmesi.

### P01-b — Geometri değişince eski çıktı güncel olmaktan çıkar

1. Build kimliği kaynak özeti + geometri sürümü/özeti + karar revizyonuna bağlı olsun.
2. Başarılı veya başarısız geçiş eski build'in güncelliğini düşürsün. Eski STEP tarihsel olarak korunabilir; güncel bağlantı ve güncel `artifact()` isteği aynı kuralla engellensin.
3. `public()` geçiş durumunu ve nedenini açıkça sunsun. `geometry_stale` varken “complete” ve güncel STEP URL'si verilmesin.
4. Kaynak eksik/değişmişse oturumun tarihsel karar/kanıt bilgisi incelenebilir kalsın; yeniden üretim açıklayıcı gerekçeyle dursun.
5. Geçiş başarısızlığından sonra kullanıcı doğru kaynak/seçimle kurtarma yapabilsin. Kalıcı stale bayrağı oturumu çıkışsız bırakmasın.
6. Okuma sırasında geçiş ile eşzamanlı save/build birbirinin kararlarını ezmesin; mevcut store kilidi/revizyon modelini koru.

**Kabul:** Başarılı geçiş, kimlik uyuşmazlığı, eksik kaynak, değişmiş kaynak ve yeniden açma için hem JSON yanıtta hem indirme uçlarında eski dosyanın güncel sunulmaması; eski kanıtın silinmemesi.

### P01-c — Kopyalama regresyonunu koru, çözüm raporunun yerini belirle

- Yeni oturumda aynı kararlarla tekrarlanan üretim, kaldırma, geri alma ve yeniden açma testleri hâlâ geçmeli.
- Önizleme/soru/plan aynı temiz temel üzerinden hesaplansın. Çözüm raporu `options` içinde tutulmasın.
- Mevcut deepcopy ile yerel kopyaya yazılan raporun `public()` tarafından okunamaması P04'te çözüm nesnesiyle tamamlanacak. Bu alt madde P04-c kapanmadan doğrulandı sayılmaz.
- Parametreler `derived` olunca geometri testi yalnız sayısal `value` alanlarını seçmesin; ifadeleri değerlendirip gerçek geometriyi karşılaştırsın.

**Odak komutu:**
```sh
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided.py
```

**Sonraki aşamaya geçiş:** P01-a/b ve mevcut kopyalama regresyonu geçince P02'ye geç. P01-c'nin rapor/önizleme maddesini P04-c'ye bağlı açık alt iş olarak kaydet; döngüsel bekleme oluşturma.

## 7. P02 — Yay ve kesişim matematiğini tamamla

**Durum:** Maksimum açıklık düzeltmesi korunsun. Açı örnekleme ve bir sınırlama yorumu eklenmesi tüm P02'yi bitirmedi.

**Dosyalar:** `contour_audit.py`, `geo.py` ve gerektiğinde ortak geometri yardımcıları; `test_contour_audit.py`, `test_contour_audit_matrix.py`, `test_contour_audit_p02_repeats.py`, `test_geo.py`.

### P02-a — CAD ve denetim aynı yayı kullansın

1. Merkez, yarıçap, kanonik başlangıç açısı `a` ve işaretli süpürme `b-a` tek tanım olsun; sayfa Y-aşağı/CAD Y-yukarı dönüşümünü açık tut.
2. Denetim başlangıç açısını saklanan `start` noktasından türetip `a` açısını yok saymamalı. Önce kanonik tanımdan iki ucu üret; saklanan `start` ve `end` ile ayrı ayrı karşılaştır.
3. Mevcut tamamlayıcı yarım-yay testini düzelt: ikinci yayın kanonik açıları da gerçek ikinci yarımı tarif etsin. Yanlış tanımlı iki yayı geçiren beklentiyi koruma.
4. Geçerli iki yarım yay geçmeli; aynı kanonik yarımı iki kez tarif eden fakat start/end'i farklı verilen örnek açık tutarsızlıkla reddedilmeli.
5. Tam çember, sıfır süpürme ve ±360° anlamını açık tanımla; modulo işlemiyle tam çemberi sıfır yaya dönüştürme.

### P02-b — Çakışma ile yakın ama ayrı geometriyi ayır

1. `_same_support` içindeki yarıçapın %2'sine kadar farklı çemberleri aynı sayan kuralı kaldır veya destek eşitliği için sayısal toleransla değiştir.
2. Kontur kapatma toleransı, CAD sayısal eşitlik toleransı ve gerçek çizim belirsizliği farklı amaçlara hizmet eder; aynı eşikle karar verme.
3. Aynı çemberde örtüşmeyi normalize açısal aralıkların gerçek kesişimiyle hesapla. 512×512 örnek mesafesi kesin açısal örtüşme değildir.
4. R100/R99 yarım halka geçmeli. Aynı yayın tam/ters yön tekrarı reddedilmeli. 0° sarmalanması ve sadece ortak uç ayrı sınanmalı.
5. Çizgi örtüşmesindeki sabit 1 px eşiğine güvenme. İleri/geri 0,8 px çizgi tekrarı ve sıfır alanlı halka reddedilmeli.

### P02-c — Kesişim/temas kararını güvenilir yap

1. Çizgi–çizgi, çizgi–yay, yay–yay için analitik kesişimi tercih et; açı aralığı ve segment sınırlarını uygula.
2. Başka yöntem seçersen hata sınırını ve belirsiz durumda ret/soru davranışını kanıtla. Sabit 32 örnek veya “kesişimi kaçırabilir” yorumu kabul koşulu değildir.
3. R1000 yarım yay ile y=999 çizgisinin x=±sqrt(1999) kesişimleri bulunmalı.
4. Beklenen komşu ortak ucu kabul et; aynı iki komşu kenarın başka noktadaki kesişimini de denetle. Komşu çifti bütünüyle atlama.
5. Komşu olmayan kenara uçtan temas basit halka sözleşmesinde reddedilmeli. Çapraz çarpım 0 olduğunda yön/yansıma kararı değişmemeli.
6. Aynı vakaları Y yansıması, ters gezinme ve farklı boyut/kalibrasyonla tekrarla. Topolojik sonuçlar tutarlı olmalı; sayısal toleransın etkisini ayrıca belirt.
7. Geçmiş birleşme öncesi açıklık (`join_max_px`), yapılan uç hareketi ve son kalan açıklık ayrı raporlansın.

**Zorunlu kabul:** Denetim klasöründeki F07–F11 karşı örneklerini doğru beklentili regresyon testine çevir. Eski 21 testin geçmesi yeterli değildir. Bütün yeni olumlu/olumsuz örnekler ve CAD yay uçlarıyla bağımsız karşılaştırma geçmeli.

**Odak komutu:**
```sh
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_contour_audit.py tests/test_contour_audit_matrix.py tests/test_contour_audit_p02_repeats.py tests/test_contour_fix.py tests/test_geo.py
```

## 8. P03 — Kararlı referanslar ve açık ölçü çerçevesi

**Korunacaklar:** Ayrı karar `id` / kaynak `span_id`, X/Y ve yön alanları; mm/inç; eksik eksen için soru; yeni kenar-uç kimlikleri. Aynı kaynak span farklı tekil kararlarca kullanılabilir.

**Dosyalar:** `guided.py` karar şemaları, `unresolved_bindings`, `user_dimensions.reference`, geçiş; `sketch_constraints.py`; `static/guided.*`; `test_measure_meaning.py`, `test_stable_identities.py`, store/geçiş testleri.

### P03-a — Eski indeksleri bir defa ve doğru bağlamda dönüştür

1. Eski `edge:<index>` biçimini her build'de o anki profil listesine göre çözme. Bu yöntem profil/kenar sırası değişince yanlış unsura kayıyor.
2. Geçişte yalnız kaydın ait olduğu profil ve geometri sürümünde hangi kenar/uç olduğu güvenilir biçimde belli ise kalıcı referansa dönüştür.
3. Bilinmeyen eski profil, eksik uç bilgisi veya yeniden çıkarma uyuşmazlığında karar korunur; kullanıcıdan yeniden bağlaması istenir.
4. Yalnız güncel `decisions` değil undo `history` kayıtları da aynı sözleşmeyle ele alınmalı. Geri alma eski belirsiz indeksi tekrar etkinleştirmemeli.
5. Dönüşüm atomik, sürümlü, idempotent ve günlükte görünür olsun. Uyumluluk kodunu yeni sessiz en-yakın eşlemeye dönüştürme.

**Kabul:** Eski kayıt → geçiş → profil değiştir/kenar çıkar/sırayı değiştir → kaydet → geri al → yeniden aç; bağ aynı anlamı korur veya açık yeniden seçim ister. Başka profilde aynı indeksin var olması yeterli değildir.

### P03-b — Yeni referanslara profil, sürüm ve uç anlamı ekle

1. `BindingEnd` için seçildiği profil/görünüş, geometri sürümü, kararlı kenar/nokta ve fiziksel uç anlamını tanımla.
2. Aynı edge ID iki farklı profile girebilir; kontur ters yüründüğünde `start/end` yer değiştirebilir. ID metninin eşitliği tek başına yeterli olmasın.
3. Kullanıcı konturdan kenar çıkardığında referansları temel listedeki varlığa göre değil, düzenlenmiş topolojiye göre denetle. Ara kayıt kaydedilebilsin; üretim gerekli yeniden bağı beklesin.
4. Üretim, sorular ve önizleme aynı referans çözümleyicisini kullansın; kopya ve farklı davranan iki çözümleme fonksiyonu bırakma.
5. Başlangıçta x/y yalnız tıklama kanıtıdır; kimliğin yerine geçmez. Kullanıcının onayı olmadan başka noktaya kaydırma.

**Kabul:** Aynı edge ID'lerini paylaşan iki profil; ters yön; silinen kenar; eski sürüm; undo geçmişi. `unresolved=[]` yalnız gerçekten bütün bağlar geçerliyse dönmeli.

### P03-c — Görünüş çerçevesini açık kullanıcı kararı yap

1. Kalibrasyon iki kaynak noktasının gerçek uzunluğundan `px/mm` verir. X/Y kısıtı iki unsur arasındaki yönlü farktır. Yerel kısıt ölçeği değiştirmez; uygulanması P04-a'da sınanır.
2. İlk sürüm için kullanıcıya orijin ve +X yönü seçtir veya mevcut sayfa eksenini açıkça onaylat. +Y ve sayfa dönüşümünü görünür göster. Dönüşüm verisini kararda sakla.
3. Orijini basılı pafta çerçevesinden otomatik çıkarmayı bu işi bitirmenin şartı yapma. Pafta çerçevesi ile parçanın ölçü datum'u farklıdır. Otomatik öneri P09'da genişletilebilir.
4. Aynı dönüşümü kenarlara, dairelere, tıklama dönüşümüne, ölçülere, önizlemeye ve CAD koordinatlarına uygula. Çözüm sonrası minimum sınır kutusundan yeni orijin seçme.
5. Çerçeve değişince mevcut ölçülerin anlamını açık politikayla ele al: aynı fiziksel ilişkiyi doğru dönüştür veya yeniden onay iste. Eski X ölçüsünü sessizce yeni eksende uygulatma.
6. Yatay/dikey ilişki kararlarını açık şema ve UI/API ile çekirdeğe taşı; `relations=[]` sabiti nihai uygulama değildir.
7. Keyfi nokta mesafesi, yay yarıçapı/açı/teğetlik desteklenmiyorsa destek tablosunda açık olsun; X/Y gibi yorumlama. Delik çapı mevcut Hole parametresi üzerinden kullanılabilir.
8. Eski eksensiz bağ için arayüzde eylem sun: eksen/yönü onayla veya bağı yeniden seç. Yalnız hata metni gösterip kullanıcının nasıl düzelteceğini belirsiz bırakma.

**P03-c yerel kabulü:** Çerçeve şeması, UI seçimi, ileri/ters koordinat dönüşümü, mm/inç ve ± yön testleri geçer; eski eksensiz kayıt soru üretir. Gerçek `Decisions → validate_decisions → store` yolu seçimi korur.

**P04-f ile kapanacak kabul:** Sayfada ötelenmiş/döndürülmüş aynı sentetik profil doğru çerçeveyle aynı CAD ölçülerine ulaşır. Bu ürün entegrasyonu kanıtı açık alt madde olarak tutulur; P04'e geçişi engellemez. P03'ün bütün kabulü bu kanıt gelmeden tamamlandı sayılmaz.

**Odak komutu:**
```sh
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_measure_meaning.py tests/test_stable_identities.py tests/test_guided_geometry_migration.py tests/test_guided.py
```

## 9. P04 — Kısıtları son geometriye ve GeneralPlan'a doğru uygula

**Dosyalar:** `guided.py` hazırlama/diagnostics/questions/make_plan; `sketch_constraints.py`; gerektiğinde `general.py`; `test_guided.py`, `test_user_dimensions.py`, `test_sketch_constraints.py`, `test_general_plan.py`.

### Bu aşamayı altı ayrı teslimde uygula

| Alt iş | Değişecek davranış | Teslimi kapatan test |
|---|---|---|
| P04-a | Kalibrasyon sabit kalır; X/Y ölçüleri eski ortak ölçek kapısını kullanmaz | 100 mm gövdeye yalnız merkez bağı eklenince gövde 100 mm kalır; köşeler X=50/Y=30 ile çözülebilir |
| P04-b | Çelişki, unsupported ve geçersiz referans üretimi durdurur | Yay köşe bağı açık ret verir; yeni plan/STEP yayımlanmaz; eski STEP güncel değildir |
| P04-c | Tek hazırlama sonucu geometri/raporu önizleme, sorular ve CAD'e taşır | Değişen köşe/merkez çizimde ve planda aynıdır; P01 kopyalama/geri alma hâlâ geçer |
| P04-d | Çekirdeğin kaynakları ve ifadeleri korunur | Değer değişince `derived` koordinat yeniden hesaplanır; datum/serbest konum `assumed` kalır |
| P04-e | Son geometri yeniden denetlenir; ilgisiz özellikler çözüme katılmaz | Çözümle doğan kesişim reddedilir; kesilmeyen daire yanlış üretim/serbestlik iddiası yaratmaz |
| P04-f | Karar/store yolu gerçek CAD sonucuna ulaşır | Bozuk oranlı kontur düzelir; seçili deliğin merkezi STEP'te istenen yere gider; restart/undo aynı sonucu verir |

Her alt işte önce en küçük doğru beklentili test yaz. Aşağıdaki maddeler bu alt teslimlerin ayrıntılı gereklilikleridir. Birinin kodlanması diğerlerini tamamlamaz.

1. P01'in temiz kopyasına P05 öncesinde mevcut kontur düzeltmelerini uygula; sonra P02 ön denetimini çalıştır. Geçersiz girişte ölçü çözümüne devam etme.
2. Ölçeği yalnız kaydedilmiş kalibrasyondan al. Eski `fit_scale` raporu tanısal kalabilir; bağlar eklenince üretim ölçeğini sessizce değiştirmesin.
3. `bindings_solvable`, `questions`, önizleme ve build aynı destek kurallarını kullansın. Desteklenen X/Y köşe bağını eski “tek ölçek tutmuyor” kontrolüyle engelleme.
4. Çözücüye seçili kontur, gerçekten seçili delik/cep merkezleri ve bilinçli referans olarak bağlanan geometrileri ver. İlgisiz diğer görünüş dairelerini ekleme. Bilinçli referans noktası ile üretilecek özellik arasındaki fark raporda görünsün.
5. `SketchConstraints` içine X/Y bağlarını, yatay/dikey ilişkileri ve datum'u taşı. Çekirdeğin hata bilgilerini kaybetme.
6. `conflict`, `unsupported`, `invalid_reference` veya geçersiz kontur: bu revizyon için STEP yayımlanmaz. Sorunlu ölçü/kenar kimliği ve yapılabilecek düzeltme kullanıcıya gösterilir. Genel exception yakalayıp “ölçüsüz devam et” yapma.
7. `underconstrained`: hangi geometri/koordinatın çizim varsayımı olarak kaldığını göster. Geçerli şekil için kullanıcı bu varsayımları ilgili revizyonda açıkça onaylarsa taslak STEP üretilebilir. `constrained` yalnız çözücünün kapsadığı noktalar/ilişkiler için kullanılmalı; tüm 3B parça kesinleşti anlamına gelmez.
8. Çekirdeğin `parameters` ve `expressions` çıktısını GeneralPlan'a koruyarak aktar. Girilen boyut `user`; hesaplanan koordinat `derived` ve ifadeli; datum/serbest konum `assumed` olarak kalmalı. Önceki sayısal koordinatı `user` etiketiyle sabitleme.
9. Orijini çözüm sonrasında değiştirme. Koordinat çerçevesi dönüşümü gerekliyse bunu parametre ifadelerine tutarlı biçimde uygula.
10. Çözülen kenarları ve delik merkezlerini hem önizlemeye hem CAD işlemlerine aktar. Eski izlenen merkezden kesme yapılıp yeni merkez yalnız raporda kalmamalı.
11. Son kenarlar üzerinde P02 denetimini tekrar çalıştır. Yeni kesişim, açıklık veya dejenere kenar varsa üretimi reddet. Delik/cep kesiminin hedef gövdeyi gerçekten değiştirdiğini de kontrol et; boş kesme başarı değildir.
12. Çözüm/denetim raporunu kaynak özeti, geometri sürümü ve karar revizyonuna bağla. Yeni kararda eski raporu güncelmiş gibi gösterme.

**Zorunlu kabul:**

- Başlangıç geometrisi bozuk oranlı bir çizgi konturuna farklı X/Y ölçüleri ve yatay/dikey ilişkiler verilir; çıktı her ikisine de uyar. Tek ortak ölçekle geçebilecek örnek yeterli değildir.
- Seçili deliğin merkezi verilen X/Y ölçüleriyle hareket eder; STEP'teki silindirin merkezi yeni yerdedir.
- Kullanıcı ölçüsü değiştirilince ona bağlı `derived` koordinat yeniden hesaplanır; kaynak zinciri korunur.
- Çelişki ve desteklenmeyen yay köşe bağı açık hatayla durur; yeni STEP yoktur.
- Geçerli başlangıçtan çözüm sonrası kesişen kontur üreten girdi son denetimde reddedilir.
- Kararlar kaldırıldığında P01 geri dönüş testleri hâlâ geçer.

## 10. P05 — Kullanıcının konturu genel işlemlerle düzeltmesini sağla

**Dosyalar:** `guided.py` kontur kararları ve hazırlama; `static/guided.js`, `guided.html`; `test_contour_fix.py`; gerekirse yeni işlem yardımcı modülü.

Aşamayı üç küçük teslim olarak uygula:

**P05a — Gör ve seç:**

1. Çizimde hata veren kenarı/ucu vurgula. Ham çizim, düzenlenmiş kontur ve ölçü çözümü sonrası kontur ayırt edilebilsin.
2. Kullanıcı herhangi bir kenarı seçebilsin; yalnız ilk sekiz hata kimliğine düğme sunmak yeterli değildir.
3. Yakın adaylar varsa hangi kenar/merkezin seçildiğini göster ve seçim değiştirme olanağı ver.

**P05b — Düzenle:**

1. Ortak işlemleri şu sırayla ayrı alt teslimlerde uygula: kenarı çıkar/geri getir → bağlı alt zinciri seç → iki belirli uç arasına çizgi ekle → çizgiyi kesişimde böl/kırp → yayı kesişimde böl/kırp → küçük açıklığın birleşmesini onayla. Her işlem için olumlu örnek, geçersiz girdi, geri alma ve yeniden açma testleri geçmeden sonraki işlemi tamamlandı sayma.
2. Her işlem bir kimlik, etkilenen kaynak referansları ve açık parametreler taşısın. Eksik çizgiyi kullanıcı ekliyorsa bu kullanıcı düzeltmesi olarak kaydedilsin.
3. Yay kırpma/bölmede merkez, yarıçap ve süpürme tutarlı kalmalı. Yay ucunu keyfi orta noktaya taşıyıp eski yay parametrelerini bırakma.
4. Birleşme öncesinde uçların ne kadar hareket edeceğini piksel ve mm olarak göster. Büyük boşluğu sessizce kapatma; kullanıcıdan çizgi ekleme veya doğru zinciri seçme kararı al.
5. Düzenleme eski ölçü referansını kaldırıyorsa P03 kurallarını uygula. Geçersiz bağı başka unsura taşıma.

**P05c — Kaydet ve yeniden üret:**

1. İşlemleri özgün geometriye sırasıyla yeniden uygulayan bir düzenleme listesi tut; temel gözlemleri değiştirme.
2. Her işlem önizleme ve tanıları yenilesin. Kalıcı kayıt/geri alma aynı işlemleri tekrar oluşturabilsin.
3. Tamamlanmamış/açık kontur düzenleme oturumu kaydedilebilsin; STEP yalnız son geometri geçerliyse üretilebilsin.

**Kabul:** Sentetik açık zincir ve kendini kesen kontur, örneğe özel kod olmadan uygun genel işlemlerle düzeltilebiliyor. Kaydet → yeniden aç aynı düzenlenmiş konturu; geri al önceki konturu veriyor. Yanlış düzeltme üretim kapısından geçmiyor. Tek bir konturun düzelmesi bütün düzenleyicinin kabulü değildir; P05b'deki her işlemin kendi test kanıtı bulunmalı.

## 11. P06 — Kalıcılık, API ve kesilme senaryolarını doğrula

**Dosyalar:** `GuidedStore`, `_changed_fields`, `app.py`; `tests/test_guided.py`; gerekirse yeni `tests/test_guided_workflow.py`.

1. Ölçü bağı, ilişki ve kontur işlem değişikliklerini alan düzeyinde günlüğe al. Kullanıcı kararı, otomatik öneri ve onay ayrı kalsın.
2. Karar değişince eski çözüm/önizleme/STEP'in güncel durumu kalksın. Eski build tarihsel olarak saklanabilir; güncel indirme diye sunulmasın.
3. Üretim sürerken yeni karar gelirse biten eski build yeni revizyona bağlanmasın.
4. Hatalı/yarım üretim kararları silmesin. Sunucu açılışındaki `recover_interrupted` davranışını koru ve yeni çözüm verileriyle sınayıp genişlet.
5. Testleri gerçek `Decisions → validate_decisions → hazırlama → make_plan → GuidedStore` zincirinden geçir. Yalnız helper çağrılarıyla yetinme.
6. Kaynak dosyanın değişmesi, eski revizyonla kayıt ve eski artefakta erişim için mevcut korumaları bozma.

**Zorunlu senaryolar:**

| Senaryo | Beklenen |
|---|---|
| Kaydet → üret → geri al → üret → store yeniden aç | İlgili karar/geometri aynı, temel veri değişmemiş |
| Aynı kararla iki üretim | Aynı geometrik sonuç; STEP metnindeki zaman bilgisi karşılaştırma ölçütü değil |
| Çelişkili/desteklenmeyen yeni ölçü | Açık hata; önceki STEP yeni revizyonun çıktısı değil |
| CAD işlemi hata verir | Kararlar korunur; başarı raporu/indirme yayımlanmaz |
| Build yarıda kesilir, sunucu yeniden başlar | `interrupted` veya eşdeğer açık durum; yeniden deneme mümkün |
| Build sırasında karar değişir | Geç tamamlanan eski sonuç güncel revizyona yazılmaz |
| Kaynak özeti değişir veya referans kaybolur | Açık ret/yeniden seçim; sessiz uyarlama yok |

**Kabul:** Yeni testler gerçek kimliklerle geçer; önceki revizyon/artefakt/hata testleri de geçer. Ortamda HTTP açılması engellenirse sonucu ortam engeli olarak kaydet, geçmiş test sonucuyla boşluğu doldurma.

## 12. P07 — Gerçek arayüzde uçtan uca kabul yap

**Önkoşul:** P01–P06'nın ilgili testleri geçmiş olmalı. Bu aşama API testinin yerine geçmez; kullanıcı akışını ayrıca sınar.

1. Sunucuyu proje ortamından başlat: `PYTHONPATH=src .venv/bin/python -m drawingto3d.app`.
2. Adres `http://127.0.0.1:8765/guided`. JS yolu **`/guided.js`**; `/static/guided.js` mevcut sunucuda doğru yol değildir. Sunulan dosyanın güncel olduğuna bak.
3. Çalışan başka kullanıcı sürecini topluca kapatma. Yeniden başlatman gerekiyorsa kendi başlattığın süreci kimliğiyle yönet.
4. Yeni oturumda PDF/PNG yükle, bütün dış konturu seç, kalibrasyon ve görünüş eksenini doğrula.
5. Bir hatalı konturu P05 işlemiyle düzelt; değişimi çizimde gör, kaydet, yeniden aç.
6. X/Y ölçülerini ve yatay/dikey ilişkileri ekle. Ölçülerden biri başlangıç izinden farklı olsun; yalnız 0 piksel hareket gösteren örnek kabul için yeterli değildir.
7. Ölçüyle hareket ettirilen merkezde **gerçek bir delik/cep seç**, çap/depth kararını ver. Kalınlığı kaydet.
8. Soruları ve kalan varsayımları göster; gerekli onaydan sonra üret. Aynı revizyona ait STEP'i indir.
9. Bir ölçüyü değiştir, eski indirmenin güncel olmaktan çıktığını gör, tekrar üret. Sonra geri al ve sayfayı yenile; geometriyi yeniden karşılaştır.
10. İndirilen STEP'i P08'de bağımsız ölç. Ekran görüntüsü ve ilgili session/revision/build kimliklerini kanıt kaydına koy.

**Tuval testi:** Ekran koordinatlarını önceki koşunun sayılarıyla tahmin etme. Güncel tuval sınır kutusu, CSS boyutu, iç çözünürlük, sayfa dönüşümü, kaydırma ve zoom'u kullan. Pencere yeniden boyutlanınca aynı geometrinin seçildiğini de doğrula. Gerekirse geometri kimliğiyle erişilebilir seçim listesi ekle.

**Araç engeli:** Tarayıcı bağlantısı yoksa iki hedefli teşhis denemesinden sonra engeli kaydet ve bağımsız test/işleri sürdür. “Arayüz kabulü tamamlandı” yazma. Aynı bağlantı hatasına uzun deneme döngüsüyle devam etme.

**Kabul:** Kullanıcının ölçü değişikliği, gerçek seçili özelliğin STEP geometrisine ulaşır; düzenleme/geri alma/yeniden açma çalışır. Yalnız çözüm satırının görünmesi yeterli değildir.

## 13. P08 — Doğru tam parçayı ve kullanıcı eforunu ölç

### P08a — Bağımsız sentetik kabul parçası

Başlangıç için değerlendirme verisi olarak şu parçayı tanımla; üretim koduna sabit değer olarak yerleştirme:

- Gövde: **50 × 30 × 10 mm**, datum sol alt köşe, X sağa/Y yukarı/Z kalınlık yönünde.
- Geçişli delik: **Ø6 mm**, merkez **(12, 8)**.
- Üst yüzden kör cep: **Ø10 mm**, merkez **(35, 18)**, derinlik **3 mm**.
- Beklenen hacim: `50*30*10 - pi*3^2*10 - pi*5^2*3 = 15000 - 165*pi mm³`.

1. Okunan başlangıç konturunu ve merkezleri kontrollü miktarda boz. Dört köşeye yatay/dikey ilişkiler ve bağımsız 50/30 ölçüleri; merkezlere datum'dan X/Y ölçüleri gir.
2. Beklenen değerleri ürünün ürettiği planı okuyarak oluşturma. Test tanımı ve temel matematik ayrı kaynak olsun.
3. STEP'i yeniden aç; tek geçerli gövdeyi, dış ölçüleri, iki özelliğin merkez/çapını, birinin geçişli diğerinin 3 mm derinlikte olduğunu doğrula. Yalnız hacim veya sınır kutusuyla geçirme.
4. Tam tanımlı bu sentetik örnekte doğrusal hata için `0,001 mm`, hacim için `max(0,001 mm³, beklenen_hacim*1e-6)` başlangıç kabul eşiğini kullan. Bunlar yazılım doğruluk eşikleridir; genel imalat toleransı iddiası değildir. Eşiği başarısız çıktıya uydurmak için gevşetme.
5. Genişliği 60 mm, sonra cep derinliğini 4 mm yap; ilgili geometri/ifade değişimini ve geri almayı denetle.
6. Aynı tanımı dosya/kimlik adları değişmiş, sayfada ötelenmiş ve farklı raster çözünürlükte tekrar dene. Döndürülmüş görünüşte açık koordinat çerçevesini kullan. Üretimde bilinen koordinatlara bağlı çözüm olmadığını kontrol et.
7. Helper/store testinin yanında en az bir PDF ve bir raster girişinin gerçek okuyucu→arayüz→STEP yolunu da sınamak üzere çizim fixture'ları oluştur. Elle hazırlanmış options kaydını PDF okuma başarısı diye sunma.

### P08b — Gerçek çizim değerlendirmesi

1. Veri manifestinde parça grubu, kaynak, kullanım hakkı, vektör/raster türü, işlem/şekil kapsamı, görüldü/saklı durumu ve beklenen özellik envanteri olsun.
2. Aynı parçanın görünüşleri, farklı çözünürlükleri ve kopyaları aynı grupta kalsın. Bölme dosya bazında yapılıp aynı parça iki tarafa sızmasın.
3. Şimdiye kadar kullanılan `examples/pdf with steps` dosyalarını regresyon olarak değerlendir. Yeni saklı küme farklı parça gruplarından ve önceden incelenmemiş veriden oluşmalı.
4. Referans STEP varsa yalnız ayrı değerlendirici açsın. Üretim bağımlılığının referans yolu/isim/koordinat okumadığını kontrol et. Kaynakta olmayan bilgiyi referanstan kullanıcı kararı diye aktarma.
5. Önceden tanımlanan özellik envanteriyle dış kontur, delik/cep sayısı, merkezleri, çaplar, kalınlık, derinlik ve görünüş uyumunu karşılaştır. Küçük doğru konturdan çıkan katıyı bütün parça başarısı sayma.
6. Her vakada otomatik öneri, kullanıcı müdahalesi ve nihai geometri başarısını ayrı yaz. Hatalı denemeleri toplamdan çıkarma.
7. En az iki farklı gerçek geometri/çizim grubunda başlangıç denemesi yap; bu küçük örneklemden “genel başarı yüzdesi” iddiası çıkarma. Daha geniş iddia için çeşitliliği ve örneklem sayısını artır.
8. Saklı veri yoksa manifesti boş/kısıtlı olarak dürüstçe bırak ve gerekli veriyi iste. Sentetik/regresyon çalışmasına devam edilebilir; bağımsız gerçek çizim kabulü açık kalır.

**Kaydedilecek ölçüler:** tam parça doğru mu; özellik başına hata; geometriyi durduran ret doğru mu; kullanıcı seçim/düzeltme sayısı; aktif kullanıcı süresi; okuma/çözüm/CAD süreleri; tepe bellek ve varsa swap; çevrimdışı çalışmada dış servis gereksinimi.

Çevrimdışı kabulte kurulu bağımlılıklarla yalnız localhost kullanan akışı çalıştır. Ağ yokluğunda bulut/model servisine sessiz geri dönüş olmamalı. Kullanıcının sistem ağ ayarlarını değiştirmeden, uygulama düzeyinde test/denetim yap. Ölçülemeyen bellek alanını 0 yazma; `ölçülemedi` olarak kaydet.

## 14. P09–P12 — Genel kapsamı kontrollü genişlet

Bu aşamalar ürün hedefinin parçasıdır. P01–P07 ve P08a kanıtı olmadan yeni geniş kapsam işine atlama. P08b veri bekliyorsa bağımsız geliştirme yapılabilir; gerçek çizim başarısı iddiası bekler.

### P09 — Giriş, görünüş ve CAD işlemleri

1. Destek tablosu çıkar: vektör PDF, raster PDF, PNG/JPG, çok sayfalı PDF sayfa seçimi, mm/inç, görünüş ekseni, kesit ve birden çok görünüş. Her satırda mevcut/eksik/testli durumu ayrı yaz.
2. Kaynak dosya özeti, sayfa, görünüş, koordinat dönüşümü, ölçü/çizgi kimliği ve okuma yöntemi gözlemlerden son karara kadar korunsun.
3. Kullanıcıya sayfa/görünüş alanını ve ön/üst/yan/kesit ilişkisini seçtirecek genel mekanizma ekle. Farklı görünüşlerdeki çemberleri tek düzleme deliğe çevirmemeli.
4. Ortak işlem sırası: profil uzatma ve kesmeler → eksen çevresinde döndürme (`revolve`) → farklı düzlemde ekleme/çıkarma → örüntü/tekrar → sağlam kenar seçimiyle pah/yuvarlama.
5. `GeneralPlan` derleyicisinde işlem zaten varsa tekrar yazma; okuyucu/karar/arayüz/üretim bağlantısını tamamla. Her yeni işlem için hatalı girdiyi reddetme, parametre değişimi ve STEP yeniden açma testi ekle.
6. Yeni parça sınıfını bir dosya tanıyıcısına dönüştürme. Braket, mil ve flanş gibi örnekler ortak işlemlerin farklı bileşimleri olmalı.
7. Bir görünüş şekli kesin belirlemiyorsa adayları ve ayrımı yapan eksik bilgiyi göster. Kullanıcı kararını kaynaklı ve geri alınabilir sakla.

**Her alt teslimin kabulü:** Bağımsız sentetik geometri + farklı bir gerçek çizim + kullanıcı düzeltmesi + kalıcılık testleri. Veri eksikse ilgili gerçek kabul açık kalır.

### P10 — Yay kısıtları ve daha geniş geometri

1. Çember merkezinin X/Y konumunu çözmek ile yay yarıçapı/teğetliğini çözmeyi ayrı yetenekler olarak tut.
2. Yay/daire yarıçapı, uçlar, açı, teğetlik ve eşmerkezlilik için matematiksel sözleşme yaz. Doğrusal çekirdeğin sınırını açık bırak; genel doğrusal olmayan çözümü aynı adla varmış gibi sunma.
3. Gerekliyse yerel ve dağıtım lisansı uygun bir çözücü seç; bağımlılık/bellek/başarısızlık davranışını değerlendir. Bir defada bütün kısıt türlerini ekleme.
4. Çözümde çoklu olasılık, kararsızlık, yakınsama hatası ve çelişkiyi kullanıcıya ayırt edilebilir göster. Önceki geometriye yakınlık, teknik ölçünün yerine geçmez.
5. Her tür için çözüm, çelişki, eksik kısıt, yeniden açma ve bağımsız CAD testi ekle. Serbest biçimli yüzey, sweep/loft, montaj ve vida helisi ayrıca planlanmadan tamamlanmış kapsama alınmaz.

### P11 — Yerel modelle öneri kalitesini artır

1. Önce kullanıcı akışındaki tekrar eden okuma/bağlama/işlem seçimi hatalarını say. Bir sonraki model çalışmasının hedefini bu hata dağılımından seç.
2. Model girdisi gerçek çizim/gözlem; çıktısı sürümlü yapılandırılmış öneri, alternatif ve açıklama olsun. Öneri doğrulanmış kullanıcı kararı sayılmasın.
3. Model başarısız/kapalıyken kullanıcıyla çalışan temel yol korunsun. Modelin bulut servisine ihtiyaç duymadan bu cihazda çalıştığı ayrıca ölçülsün.
4. Mevcut yerel modelleri yeniden kullanmadan önce format/donanım uyumunu ve lisansı kontrol et. M1/16 GB için sığmayı tahminle başarı sayma; yükleme, çıkarım, bellek ve süreyi ölç.
5. Aynı veri/karar bütçesiyle modelsiz temel, mevcut model ve varsa yeni modeli karşılaştır. Tek örnek başarısından yeni eğitim kararı çıkarma.

### P12 — Eğitim yalnız kanıt varsa

1. İlk ürün teslimini sıfırdan büyük model eğitimi şartına bağlama. Önce somut hata görevi belirle: OCR düzeltme, ölçü-geometri eşleme veya yapılandırılmış işlem önerisi gibi.
2. Eğitim/validasyon/saklı test verisini parça grubu ve kaynak düzeyinde ayır. Kullanım hakkını kaydet. `examples/pdf with steps` bu eğitime girmez.
3. Sentetik veri gerekiyorsa farklı parametreler, çizim stilleri ve işlemler üret; tek şablonun varyasyonlarını genel öğrenme diye sunma.
4. İnce ayardan önce veri boyutu, etiket denetimi, yerel eğitim/bellek maliyeti ve değerlendirme protokolünü yaz. Eğitim donanımı ile son uygulamanın çevrimdışı çıkarım koşulunu ayrı kaydet.
5. Eğitilmiş adayı dokunulmamış testte ve kullanıcı eforunda değerlendir. Kazanç yoksa önceki modeli koru; sırf eğitim koştu diye üründe kullanma.

## 15. Test komutları ve çalışma disiplini

Bütün komutlar `/Users/aydemir/Desktop/drawingto3d` kökünden çalıştırılır. Ana ortam `.venv`, CAD ortamı `.venv-cad` olarak ayrıdır; CadQuery bağımlılıklarını ana ortama rastgele taşıma.

Mevcut testler için örnek odak koşuları:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_guided.py tests/test_user_dimensions.py tests/test_sketch_constraints.py
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_contour_audit.py tests/test_contour_fix.py tests/test_geo.py
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_general_plan.py tests/test_guided_proposals.py
```

Yeni test dosyalarını oluşturduktan sonra ilgili koşuya ekle. Her tur bütün bu komutları mekanik biçimde çalıştırmak gerekmez; değişen davranışın testini ve etkilenen komşu yolu seç. Test adı/fonksiyonu kod değişince güncellenebilir; davranış koşulu korunur.

P01–P06 bütünleştikten ve odak testleri geçtikten sonra:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q
git diff --check
```

Tam takım yeni hata/önemli değişiklik olmadan tekrar tekrar koşulmaz. Son değişiklikten önceki test sonucu son kodun doğrulaması diye sunulmaz. Shell borusu kullanıyorsan pytest'in çıkış kodunu kaybetme; günlük yolu ve gerçek çıkış kodunu kaydet.

### Bir çalışma turunun şablonu

1. Açık ilk aşamayı ve en küçük anlamlı davranış hedefini seç.
2. İlgili kodu oku, mevcut testte eksik kabul koşulunu bul.
3. Doğrulanmış kusur için önce başarısız olan küçük regresyon testi yaz.
4. Genel mekanizmayı düzelt; örnek dosyaya özel dal ekleme.
5. Odak testleri ve ilgili gerçek ürün yolunu çalıştır.
6. Sonucu, sınırını ve kalan tek sonraki işi kaydet. Aşama bütün koşulları geçmediyse `çalışılıyor` bırak.

Aynı başarısız denemeyi veri/topoloji değişmeden yalnız tolerans büyüterek sürdürme. İki sonuçsuz hedefli düzeltmeden sonra küçük tekrar girdisini incele, hata hipotezini değiştir ve gerekçesini yaz. Kontur sayısı, okunan rakam sayısı veya büyük sınır kutusu tek başına ilerleme ölçütü değildir.

## 16. Devir, kesilme ve tamamlandı bildirimi

Her anlamlı teslim veya oturum sonundan önce:

1. Kaynak/test dosyalarını diske kaydet. Çalışan sürecin bitmemiş sonucunu geçmiş gibi yazma.
2. Bölüm 2'de yalnız ilgili aşamanın durumunu ve somut kanıtını güncelle.
3. `eval/reports/implementation-status.md` içine tarih, başlangıç/sunulan kod özeti, değişen dosyalar, komutlar, çıkış kodları, ölçülen sonuç, açık kusur ve kanıt yollarını koy.
4. `HANDOFF.md`, `.cursor/handoff.md`, `out/HANDOFF.md` başındaki güncel bölümü aynı bilgiyle güncelle. Yüzlerce satır yeni deney anlatısı eklemek yerine eski ayrıntıyı rapora bağla.
5. Tek sonraki işi şu biçimde yaz: **aşama → dosya/fonksiyon → beklenen davranış → çalıştırılacak test**.
6. Kesilme/kota varsa aktif test/build kimliğini, log yolunu, son tamamlanan adımı ve kalan işlemi kaydet. Kota veya süre bitmesi hedefin tamamlandığı anlamına gelmez.
7. Önemli küçük kanıtların yalnız `/private/tmp` veya Git dışı `out/` altında kalmadığını kontrol et. Büyük STEP/görüntülerin devirde gerekli olanlarını ayrıca belirt; hash dosyanın yerini tutmaz.

### Sonuç mesajında mutlaka ayrıştır

- **Uygulandı:** Somut davranış değişikliği.
- **Doğrulandı:** Gerçekte çalıştırılan test ve çıktı kontrolü.
- **Açık:** Yapılmayan/başarısız/araç nedeniyle engelli kabul koşulu.
- **Sıradaki iş:** Tek küçük ve uygulanabilir adım.

“Genel PDF → STEP tamamlandı” demek için yalnız bu planın ilk profil akışını bitirmek yeterli değildir. Destek tablosu, bağımsız gerçek çizimler, bütün parça doğruluğu, kullanıcı düzeltmesi ve cihazdaki çevrimdışı çalışma birlikte kanıtlanmalıdır. Desteklenmeyen geometri ve belirsiz çizimler açıkça raporlanmaya devam eder.

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

### P04-b INDI: celiski / desteklenmeyen bag / gecersiz referans uretimi durdurur (2026-09-29 05:57)

**Once olcum (kod degismeden):**
| Senaryo | Bugun |
|---|---|
| Ayni iki daireye 120 ve 90 mm bagi (celiski) | `make_plan` + `store.build` **istisna**: "baglanan olculer birlikte tutmuyor (cakisan: b0, b1)" ✓; kayit **korunuyor** ✓ |
| Reddedilen build sonrasi eski STEP | `build` alani sifirlanmis; `artifact()` -> "**bu kararlar icin guncel STEP yok**" ✓; eski klasor diskte ✓ |
| Yayli konturda kose bagi (plaka `outline_1`: 8 kenar / 4 yay; `2/Drawing.pdf outline_2`: 1 yay) | core **unsupported** ("yayli veya dairesel dis konturda yalniz daire merkezleri olculendirilebilir") ✓ ve `make_plan` (P04-a'nin one alinan kapisiyla) **duruyor** ✓ — ama arayuz sorulari **bos** ✗ |

**Ne indi (`guided.py`):** `unsupported_binding_reasons(profile, decisions)` — core'un kuralini *ayni profil
seklinden* okuyup **build'den once** kullanicinin dilinde soran yardimci; `questions()` bunu once ekliyor ve
bu durumda uyum artiklarini sormuyor (artik sorusu burada anlamsiz). `bindings_solvable` ucta destek kuralina
gore kaliyor (celiski mesajini core veriyor).

**Kanit:** `tests/test_guided.py` -> **2 passed / 9,26 s** (yeni iki test):
- `test_a_conflicting_pair_of_ties_stops_the_build_and_leaves_no_current_step`: baglar **korunur** (kimlikler
  yerinde), `make_plan` ve `store.build` **b0+b1 adiyla** durur, `build.revision` bu revizyon degil,
  `artifact()` "guncel STEP yok" der, **eski build klasoru diskte kalir**.
- `test_a_vertex_tie_on_an_arc_contour_is_asked_and_refused_by_name`: gercek korpus paftasi (`2/Drawing.pdf`,
  yayli kontur) -> arayuz **soruyor**, `make_plan` "desteklenmiyor/yayli" ile durur, `store.build` istisna
  atar ve **cikti klasoru acilmaz**; ayrica core'un kendi kurali da testte pinlendi (`user_dimensions` ->
  `unsupported`), boylece arayuzdeki kopya core'dan ayrisirsa test kirmizilasir.

**Durust sinirlar:** (1) `unsupported_binding_reasons` core'un kuralini *kopyaliyor* (kural `sketch_constraints.py`
icinde; o modul bu dilimin degil) — senkron testle baglandi, ortak yardimci P04-c/d'de core'a sorulabilir;
(2) gecersiz referans zaten P04-a testiyle kapali; (3) tam takim kosuyor (`proc_74f8712272e4`).

### P04-c OLCUMU: onizleme cozumu hic gormuyor (P01-c maddesi) (2026-09-29 06:16)

**Tam takim P04-a+b sonrasi: 672 passed / 1079,27 s** (669 -> +3 test). P04-a ✓ P04-b ✓.

**P04-c oncesi olcum** (sentetik kayit: 100x60 px govde, kalibrasyon 2 px/mm; 60 px'lik kenara 40 mm bagi):
- `public()["sketch"]["solved_dimensions"]` = **null** — onizleme cozum raporunu hic gormuyor.
- Onizlemedeki kontur kosesi: **[20, 80]** (izlenen) — plan/CAD ise **cozulen** geometriyi kuruyor (kenar bagi 60 px -> 80 px; yapilan gecici kosuda cozum sonrasi kutu 100x140 px, durum `underconstrained`, `moved=140 px`).
- Yani bugun: **cizim ve plan ayni seyi gostermiyor** — P04-c'nin kabulunun birinci yarisi ("degisen kose/merkez cizimde ve planda aynidir") saglanmiyor.

**P04-c giris noktasi (kayitli plan):**
1. Tek hazirlama sonucu: `prepare(options, decisions) -> Prepared` (derin kopya -> P02 on denetimi -> sorular ->
   olcu cozumu -> rapor); `sketch_diagnostics`, `public()` ve `make_plan` **ayni** sonucu okur (ikinci cozum yolu yok).
2. `public()["sketch"]`: cozulen kontur/merkezler + `solved_dimensions` raporu (onizleme cizimi cozulmus
   konumlari gosterir).
3. Kabul testleri: onizlemedeki cozulen kose/merkez plan/STEP ile **ayni**; P01 kopyalama/geri alma ve
   "temel geometri degismez" testleri hala gecer.
