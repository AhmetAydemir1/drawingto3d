# drawingto3d — ayrıntılı uygulama planı

Güncelleme: **2026-09-29**. Bu belge devralan AI için güncel iş sırasıdır.
**Bu güncellemede yalnız plan ve devir belgeleri düzenlendi; aşağıdaki düzeltmeler henüz uygulanmadı.**

## 1. Önce bunu oku

**Hedef:** M1 / 16 GB cihazda, kurulumdan sonra çevrimdışı çalışan; farklı teknik çizim PDF/PNG/JPG dosyalarını ortak geometri, ölçü ve CAD işlemleriyle STEP'e dönüştüren bir program. Belirsiz veya yanlış okunan yerlerde kullanıcı çizimin üzerinde düzeltme yapabilmeli.

**Kapsam geneldir.** `examples/pdf with steps` yalnız test ve değerlendirme verisidir. Bu klasördeki bir parçanın çözülmesi, ürünün kapsamını o parçaya daraltmaz ve genel hedefi tamamlamaz. Uygulama yeni parçaları aynı işlemlerin farklı birleşimleriyle ele almalıdır.

Bu belgeyi okuduktan sonra:

1. Bölüm 2'deki durum tablosunu ve Bölüm 3'teki kusurları oku.
2. P00 ile çalışma ağacını ve kanıtları kaydet.
3. **İlk kod işi P01: özgün geometrinin üretim sırasında değişmesini önle.**
4. Ardından P02 → P03 → P04 → P05 → P06 → P07 → P08 sırasını izle.
5. Bir aşamanın kabul koşulları geçmeden onu tamamlandı işaretleme. Büyük aşamayı alt teslimlere böl.
6. Her teslim sonunda Bölüm 2'yi ve devir belgelerinin güncel bölümünü güncelle.

Önceki uzun plan, deneyler ve komut çıktıları [plan arşivinde](docs/PLAN_HISTORY_BEFORE_DETAILED_20260929.md) aynen korunmuştur. **Arşivdeki Bölüm 26, “A/B tamamlandı” ve “tek sonraki iş” ifadeleri güncel yönlendirme değildir.** Eski devir kayıtları da tarihçedir. Güncel iş sırası yalnız bu belgededir; gerçek çalışma durumu kod ve yeniden üretilebilir kanıtla doğrulanır.

### Değişmez kurallar

- Üretim kodunda dosya adı, örnek numarası, bilinen koordinat, sabit delik sayısı veya referans STEP'e göre özel çözüm yazma.
- Referans STEP yalnız değerlendirme aracına girebilir. Okuyucuya, model istemine, önericiye veya üretim yoluna cevap kaynağı olarak verilmez.
- Test klasörünü eğitim, ince ayar veya benzer parça getirip kopyalama kaynağı yapma.
- Daha önce incelenmiş çizimler artık regresyon verisidir. Bunları yeniden “görülmemiş” diye raporlama.
- Ölçü veya görünüş eksikse birden çok şekil mümkün olabilir. Gerekli bilgiyi kullanıcıdan al; sessizce geometri uydurma.
- Geçerli katı, doğru dış ölçüler ve STEP'in yeniden açılması gereklidir; çizimin bütünüyle doğru yeniden kurulduğunu tek başlarına kanıtlamaz.
- Mevcut kodu, testleri ve kullanıcı dosyalarını koru. Temiz başlangıç için `git reset`, `git clean`, toplu silme veya mevcut oturumların üzerine yazma yapma.
- Bir model öneri üretebilir; geometri geçerliliği ve ölçü ilişkileri deterministik kontrollerden geçmelidir. Serbest Python üretip çalıştırmak genel ürünün varsayılan yolu değildir.

## 2. Durum ve tamamlanma kapıları

Durumlar: `bekliyor`, `çalışılıyor`, `doğrulandı`, `engelli`. “Kod var” ile “kabul koşulları geçti” aynı şey değildir.

| Aşama | Teslim | Güncel durum | Tamamlanma kanıtı |
|---|---|---|---|
| P00 | Başlangıç kaydı ve kusur tekrarları | doğrulandı | `out/plan-run-20260929-022902/` (git durumu, HEAD, sürüm, envanter) + `eval/reports/implementation-status.md`; P01 mutasyon tekrarı `tests/test_guided_geometry_state.py`; P02 tekrarları `tests/test_contour_audit_p02_repeats.py` (iki kusur önce xfail(strict) ile tekrarlandı, düzeltmeyle düz assertion oldu); 100×100 kare çift-bağ tekrarı: girdiler kayıtlı, köşe-bağı kapısı yüzünden **tekrar engeli açıkça yazılı** (P04 kapsamı) |
| P01 | Değişmeyen özgün geometri ve güvenli oturum geçişi | doğrulandı | `tests/test_guided_geometry_state.py` (create→build A→ölçü ekle→build B→ölçü kaldır→build C=A→geri al→build=B→yeniden aç; temel seçenekler her adımda aynı) + `tests/test_guided_geometry_migration.py` (eski kayıt kaynaktan tazelenir/kararlar korunur; kimlik uyuşmazlığında `geometry_stale` ve build reddi); odak set 53 passed / 68,89 s |
| P02 | Doğru çizgi/yay kontur denetimi | doğrulandı | `test_contour_audit_matrix.py` (10 matris girdisi) + `test_contour_audit_p02_repeats.py` (iki kusur + gerçek-örtüşme kontrolü); dokuz dosyalık odak set **80 passed / 72,57 s**; §7.7 sınır notu ve ters-yön tanısı kodda; §7.3 kanıtı kayıtlı |
| P03 | Açık ölçü anlamı ve kararlı geometri referansları | çalışılıyor | Beş dilim doğrulandı (`Binding.id/axis/direction`, yumuşak eksen sorusu, arayüzde Eksen/Yön, "yeniden bağlama gerekir" durumu, kararlı uç kimliği `<edge_id>:start\|end` + eski `edge:<sayı>` dönüşümü). **Kabul listesi eşlendi ve yeşil: 64 passed / 57,08 s** — X/Y, yön (doğrudan), mm/inç, profil değişimi (doğrudan), silinen kenar, eski sürüm. Kalan tek madde: §8.6 görünüş ekseni/orijini + döndürülmüş paftada çerçeve kararı |
| P04 | Ölçü çözümünün bütün ürün yoluna doğru uygulanması | bekliyor | Son geometri, parametre kaynakları ve STEP özellik ölçümleri |
| P05 | Genel kontur düzeltme akışı | bekliyor | Önizleme, kenar düzenleme, kaydetme ve geri alma |
| P06 | Oturum/API dayanıklılığı | bekliyor | Kaydet → üret → geri al → yeniden aç zinciri ve hata senaryoları |
| P07 | Gerçek arayüz kabulü | bekliyor | Tarayıcıdan yapılan işlemler ve aynı revizyonun çıktı kontrolü |
| P08 | Bağımsız doğruluk ve kullanıcı eforu ölçümü | bekliyor | Tam parça/özellik karşılaştırması; görülen ve saklı veri ayrımı |
| P09 | Giriş, görünüş ve ortak CAD işlemlerinin genişletilmesi | bekliyor | Her yeni yetenek için ayrı kabul paketi |
| P10 | Yay kısıtları ve daha geniş geometri kapsamı | bekliyor | Destek tablosu, çözüm/ret testleri, bağımsız CAD kontrolü |
| P11 | Yerel modelin ölçülmüş öneri desteği | bekliyor | Modelsiz temel ile aynı koşullarda karşılaştırma |
| P12 | Koşula bağlı eğitim/ince ayar | bekliyor | Ayrı veri, hata hedefi, saklı değerlendirme ve cihaz ölçümü |

**Şu anki ilk iş:** P00 kayıtlarından sonra P01. P02 matematiği ayrı dosyalarda paralel incelenebilir; aynı `guided.py` üzerinde çakışan değişiklikler yapılmamalı.

**İlk kullanılabilir teslim:** P00–P08 kabul koşullarının desteklenen profil uzatma + delik/cep akışında geçmesi. Bu, genel ürünün bir kilometre taşıdır. Diğer çizim ve işlem türleri P09–P12 ile genişletilir; evrensel hedef tamamlandı diye raporlanmaz.

**Bu turdaki belge kontrolü:** Eski plan arşivlendi ve SHA256 özetiyle aynen korunduğu doğrulandı. Dosya bağlantıları, mevcut test yolları, aşama tablosu, Hermes promptu ve üç devir başlığının eşleşmesi kontrol edildi; `git diff --check` geçti. Uygulama testleri bu belge güncellemesinde yeniden çalıştırılmadı. Aşağıdaki sayılar geçmiş koşuların kanıtıdır.

## 3. Mevcut kod ve doğrulanmış açıklar

### Korunacak çalışan parçalar

- `general.py`: `GeneralPlan`, parametre ifadeleri, CAD derleme, STEP üretimi ve yeniden açma kontrolleri.
- `guided.py` ve `static/guided.*`: çizim yükleme, kontur/özellik seçimi, ölçü bağlama, karar kaydı, geçmiş, üretim.
- `contour_audit.py`: kontur denetiminin ilk sürümü; bazı yay ve açıklık hesapları hatalı.
- `sketch_constraints.py`: çizgi kontur köşeleri ve daire merkezleri için X/Y fark denklemleri; yatay/dikey ilişkiler, çelişki ve serbest koordinat raporu.
- Çözücü **artık `guided.py` içine bağlıdır**. “Henüz entegre değil” diyen eski notlar güncel değildir. Entegrasyonun doğruluğu ve kalıcılığı düzeltilmelidir.
- `ContourFix`: kenar çıkarma ve tek küçük açıklığı onayla kapatma. Genel kesme, ekleme ve alt zincir düzenleme henüz yeterli değildir.
- Girdi okuma, öneri ve kaynak kayıtları vardır. Tamamını yeniden yazmak yerine kusurlu sınırları düzelt.

### Açık kusurlar ve hangi aşamada kapanacakları

| Kusur | Etkisi | Aşama |
|---|---|---|
| `make_plan`/`user_dimensions` seçili profili `record["options"]` üzerinden değiştiriyor; build bunu saklayabiliyor | Ölçü kaldırılınca veya geri alınınca özgün geometri dönmeyebiliyor | P01 |
| Tam daire oluşturan iki yarım yay, kiriş üzerindeki örtüşmeye göre çakışıyor sayılabiliyor | Geçerli kontur reddediliyor | P02 |
| Son birleşimin açıklığı, daha önce bulunan en büyük açıklığın üzerine yazılıyor | İçeride açık birleşim varken kapanış 0 raporlanabiliyor | P02 |
| X/Y anlamı tıklanan noktaların büyük farkından seçiliyor; ölçüler ortak ölçeği de değiştiriyor | Yerel kısıt yerine bütün parçanın ölçeği değişebiliyor | P03–P04 |
| Eski ortak ölçek kapısı desteklenen köşe kısıtlarını reddedebiliyor | Çekirdeğin çözebildiği karar ürün yolundan geçemiyor | P04 |
| `unsupported` sonucu bazı yollarda yalnız not olarak kalıyor | Kullanıcının ölçüsü uygulanmadan STEP üretilebiliyor | P04 |
| Çözücünün türetilmiş ifadeleri kayboluyor; hesaplanan mutlak koordinatlar `user` etiketlenebiliyor | Parametre düzenleme ve kaynak açıklaması yanlış oluyor | P04 |
| Kontur denetimi koordinatlar değişmeden yapılıyor | Çözüm sonrası kesişen/açılan şekil son denetimden kaçabiliyor | P04 |
| Seçili geometriyle ilgisiz pafta daireleri de çözüme katılabiliyor | Serbestlik ve uygulanan etki raporu yanıltıcı oluyor | P04 |
| `_changed_fields` ölçü bağı ve kontur değişikliklerini kapsamıyor | Kaydetme/geri alma günlüğü eksik kalıyor | P06 |

Örnek mutasyon tekrarı: 100×100 piksel kareye 100 ve 99,6 mm bağları uygulandıktan sonra bağlar kaldırıldığında, genişlik 100 yerine yaklaşık 100,2 mm kalabiliyor. Bu sayılar yalnız kusur tekrarının girdileridir; üretim koduna özel durum ekleme.

### Geçmiş kanıtın sınırı

- Geçmiş tam takım kaydı: **585 passed / 951,46 s**, `/private/tmp/suite-26b.txt`. Geçici dosya hâlâ varsa P00'da kalıcı kanıt klasörüne kopyala; yoksa koşuyu yeniden yapılmış gibi gösterme.
- Son denetimde `test_contour_audit.py`, `test_contour_fix.py`, `test_user_dimensions.py`: **18 passed**. Bu testler yukarıdaki bütün kusurları yakalamıyor.
- `test_user_dimensions.py` yardımcı fonksiyon testlerindeki `edge:e0` gibi kimlikler gerçek `validate_decisions` yolunun sayısal `edge:<index>` sözleşmesine uymuyor. Yeni kabul testleri gerçek ürün yolunu kullanmalı.
- Raster oturumu `8e3e7da767774dfe83c68e2d8e6ad366`: küçük bir kontur parçasından geçerli katı üretildi; tam parçanın doğruluğu kanıtlanmadı.
- Arayüz oturumu `34f729c104f643c2b891bf74b24f9f0d`: çözüm raporu görüldü, ancak ilgili daire çıktıdaki delik olarak kesilmedi ve raporlanan hareket 0 piksel idi. Delik konumu düzeltmesinin CAD'e ulaştığını kanıtlamaz.
- API oturumu `fd57c33d945b4a6bb8d3e9ff61bb2014`: merkez mesafelerinin değişebildiğine dair kanıt var. Bu tek başına referans parçanın doğru yeniden kurulduğu anlamına gelmez.

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

Aşağıdaki yeni dosya adları öneridir; henüz var olduklarını varsayma. Aynı sorumluluğu taşıyan mevcut dosya varsa onu genişlet.

## 5. P00 — Başlangıcı kaydet ve kusurları küçük örneklerle sabitle

**Amaç:** Sonraki modelin yanlış durum varsayımıyla başlamasını ve kesilmede kanıt kaybını önlemek.

1. Proje kökünde `git status --short`, `git rev-parse HEAD` ve Python sürümünü kaydet. İzlenmeyen kaynak/test dosyalarını da envantere al.
2. Kullanıcının mevcut değişikliklerini kendi düzenlemelerinle karıştırıp silme. Aynı dosyada çalışan ajan varsa dosya sorumluluğunu ayır.
3. Yeni, benzersiz bir `out/plan-run-<zaman>/` klasörü aç. Komutlar, çıkış kodları, süreler ve küçük tekrar girdileri burada bulunsun.
4. Kalıcı özeti `eval/reports/implementation-status.md` dosyasına yaz veya güncelle. `out/` Git dışındadır; önemli küçük kusur girdisini/testini yalnız orada bırakma.
5. Yukarıdaki 585/18 sonuçlarının tarihsel olduğunu yaz. Mevcut tam takım yaklaşık 16 dakika sürdüğü için önce ilgili testleri çalıştır; sırf başlangıç sayısı edinmek için aynı pahalı takımı tekrar tekrar çalıştırma.
6. P01 mutasyonu ve P02 iki yarım yay/açıklık kusurlarını bağımsız küçük girdilerle tekrarla. Beklenen sonucu testte önceden belirt; hatalı mevcut çıktıyı beklenen sonuç yapma.

**Kabul:** Başlangıç dosyaları ve kanıt yolları belli; her doğrulanmış kusurun en az bir tekrarı veya açıkça belirtilmiş tekrar engeli var. Tarihsel test sonucu yeni kodun sonucu diye sunulmuyor.

**Engel olursa:** Ortam/bağımlılık hatasını geometri başarısızlığı sayma. Eksik dosyayı kayda geçir; eski kullanıcı oturumlarını onarmaya başlamadan P01 geçiş tasarımını tamamla.

## 6. P01 — Özgün geometriyi koru, geri almayı güvenilir yap

**Dosyalar:** `guided.py`; `tests/test_guided.py`; gerekirse yeni `tests/test_guided_geometry_state.py`.

1. `make_plan` ve `user_dimensions` boyunca profil, kenar listesi, daire ve iç içe koordinatların nerede değiştiğini izle.
2. Temel geometriyi salt veri kaynağı olarak koru. Her hazırlama çağrısında iç içe nesneleri de ayıran bağımsız bir kopya üret; yalnız dış sözlüğü kopyalamak yeterli değildir.
3. Çözülmüş profil/merkezleri ve raporu ayrı sonuç nesnesine koy. `options` içine `solved_dimensions` gibi geçici sonucu yazma.
4. `GuidedStore.build` yalnız karar revizyonuna ait build sonucunu kaydetsin. Temel seçenekleri çözülen değerlerle değiştirmesin.
5. Önizleme, plan oluşturma ve build girişlerinin aynı temiz kaynaktan hesaplandığını doğrula. Bir fonksiyona “önceki build'in sonucu” başlangıç geometrisi olarak verilmesin.
6. Oturum/geometri sürümünü artırırken eski kayıtları ele al: eski seçenekler zaten değiştirilmiş olabilir. Mevcut sözlüğü “özgün” diye kopyalamak geçmiş hasarı onarmaz.
7. Eski kaydı ve kararlarını koruyarak kaynak dosyadan temel geometriyi yeniden çıkar. Kaynak özeti, okuyucu sürümü ve kimlik eşleşmesini kontrol et. Güvenilir eşleşme yoksa eski bağları yeniden seçim gerektirir durumuna getir; başka noktaya sessizce taşıma.
8. Yeni kayıt atomik yazılsın. Geçiş yarıda kesilirse eski dosya ve kararlar okunabilir kalsın. Kaynak eksik/değişmişse eski sonucu tarihsel tut ve neden yeniden üretilemediğini açıkça göster.

**Kabul testleri:**

- Aynı kararlarla iki hazırlama/build çağrısı aynı geometriyi verir. Temel seçeneklerin normalize JSON özeti öncesi/sonrası aynıdır.
- Ölçü ekle → üret → ölçüyü kaldır → üret: başlangıç geometrisi tolerans içinde geri gelir; eski çözüm raporu kalmaz.
- Ölçü ekle → üret → geri al → üret → store'u yeniden aç: ilgili eski revizyonla aynı geometri.
- Bir revizyonun çalışma kopyasını değiştirmek başka revizyonu veya temel geometriyi etkilemez.
- Eski sürüm geçişi başarıyla tamamlanır veya açık yeniden seçim isteği verir; kararlar ve eski kanıt kaybolmaz.

**Tamamlandı sayma:** Yalnız `deepcopy` eklenmişse veya yalnız yardımcı fonksiyon testi geçmişse. Kalıcı store yolu da geçmelidir.

## 7. P02 — Kontur denetiminin geometrisini düzelt

**Dosyalar:** `contour_audit.py`, gerektiğinde ortak geometri yardımcıları; `test_contour_audit.py`, `test_geo.py`.

1. `closure_px` değerini bütün ardışık birleşimler ve son→ilk birleşim üzerindeki en büyük gerçek uç mesafesi olarak hesapla. Son birleşim 0 ise önceki büyük açıklığı silmemeli.
2. Birleştirme öncesi açıklığı, birleşmede yapılan uç hareketini ve son geometride kalan açıklığı ayrı alanlarda tut. Mevcut `join_max_px` birleştirme öncesi en büyük boşluğu kaydediyor; doğrudan uç hareketi veya şu an kalan açıklık diye sunma. Gerçek uç hareketini işlem öncesi/sonrası koordinatlardan ayrıca hesapla.
3. CAD ile denetim aynı yay tanımını kullansın: merkez, yarıçap, başlangıç açısı, işaretli süpürme/yön. Saklanan start/end ile bu tanımdan hesaplanan uçların tutarlılığını denetle.
4. Aynı çemberdeki yayların çakışmasını kirişe izdüşürerek belirleme. Açısal aralıkların gerçek ortak uzunluğunu ve yön/sarmalanma durumlarını kullan.
5. Çizgi–çizgi, çizgi–yay ve yay–yay kesişmelerini ele al. Ardışık kenarların beklenen ortak ucu geçerli olabilir; fazladan kesişim veya üst üste kenar geçerli sayılmamalı.
6. Sıfır uzunluk, aynı kenarın tekrarı, ters yönde çakışma, kopuk zincir ve desteklenmeyen geometriyi ayrı tanıla. Bu aşamada tek basit dış halka sözleşmesini açık tut.
7. Analitik yöntem veya hata sınırı tanımlı bir yaklaşım kullan. Sabit 32 parça örnekleme, küçük yayı kaçırabileceği halde kesin kesişim testi diye sunulmasın.
8. Piksel/mm toleranslarını ayır; kaynak çözünürlüğü ve kalibrasyonla ilişkilendir. Genel başarısızlığı kapatmak için tek bir global toleransı sürekli büyütme.

**Zorunlu test matrisi:** İki tamamlayıcı yarım yay geçer; aynı yay iki kez kalırsa reddedilir; 0° sınırını aşan yaylar; ters yön; çizgi–yay gerçek kesişimi; yay–yay kesişimi; geçerli komşu ortak uç; komşu olmayan kenarın temas ettiği bozuk halka; içeride 2 piksel açıklık/son birleşimde 0; tutarsız saklanan yay ucu.

**Kabul:** Her ret hata türü ve ilgili kenar kimliklerini verir. Geçerli örneği reddetmek ile geçersiz örneği kabul etmek ayrı ölçülür. Son geometri üzerinde yeniden çağrılması P04'te doğrulanır.

## 8. P03 — Ölçünün anlamını ve referanslarını açık yap

**Dosyalar:** `guided.py` karar şemaları/doğrulama; `sketch_constraints.py`; `static/guided.js`, `guided.html`; ilgili şema testleri.

1. **Kalibrasyon:** Kullanıcının iki kaynak noktası ve gerçek mesafesi çizimin `px/mm` ölçeğini belirler.
2. **Konum ölçüsü:** İki geometri referansı arasındaki X veya Y farkını belirler; kalibrasyonu yeniden hesaplamaz.
3. Kararlarda ölçü türü/ekseni, yönü, değer/birim, varsa basılı ölçü kimliği ve hedef geometri referansları açıkça saklansın. Mevcut çekirdekteki `DimensionBinding` sözleşmesinden yararlan. Her kararın tekil `id` alanı, kaynak metnin `span_id` alanından ayrı olsun. Aynı basılı ölçü farklı ilişkilere bağlandığında karar kimlikleri çakışmamalı; aynı kaynak kimliğinin tekrar kullanılması tek başına şema hatası değildir. İlişkilerin gerçekten tutarlı olup olmadığı ayrıca denetlenir.
4. Arayüzde X/Y seçimini ve hangi iki unsurun bağlandığını göster. Büyük piksel farkından otomatik eksen kararı verme. Öneri sunulabilir; kullanıcı doğrulaması gerekir.
5. İlk desteklenen türleri X/Y mesafesi ve çizgi konturda yatay/dikey ilişki olarak tanımla. Çap, delik/cep kararındaki mevcut parametre yolunu kullanabilir. Keyfi iki nokta uzunluğu, yarıçap, açı ve teğetlik kısıtları desteklenene kadar açık ret/eksik karar üretmeli.
6. Kullanıcıya görünüş eksenini/orijini göster. Döndürülmüş paftada görünüş çerçevesi gerekiyorsa karar olarak kaydet; sayfa X'ini parça X'i diye varsayma.
7. Referanslar seçili profil, geometri sürümü ve kararlı nokta/kenar kimliğine bağlı olsun. Ekrandaki tıklama koordinatı kimliğin yerine geçmesin.
8. Bugünkü `edge:<index>` sözleşmesini yeni kararlı referanslara geçiriyorsan mevcut kayıtları açıkça dönüştür ve test et. Kenar silinince indeks kaymasının başka köşeye bağlamasına izin verme.
9. Profil/görünüş değişince veya bağlanan kenar silinince etkilenen ölçüleri yeniden bağlama gerekir durumuna al. Kaybolan referansı en yakın noktaya sessizce eşleme.
10. Eski kayıtta eksen yoksa belirsiz anlamı kesinmiş gibi doldurma. Eski karar verisini koru ve kullanıcıdan anlamı doğrulamasını iste.

**Kabul:** Gerçek `Decisions.model_validate` ve `validate_decisions` yolu geçer. X/Y, yön, mm/inç dönüşümü, profil değişimi, silinen kenar ve eski sürüm için test vardır. Aynı `span_id` kaynaklı iki farklı kararın tekil kimliklerle kabul edildiği; aynı karar `id` değerinin iki kez kullanıldığında reddedildiği sınanır. Değerin basılı metinle eşleşmesi ile doğru geometriye bağlanması ayrı tutulur.

## 9. P04 — Kısıtları son geometriye ve GeneralPlan'a doğru uygula

**Dosyalar:** `guided.py` hazırlama/diagnostics/questions/make_plan; `sketch_constraints.py`; gerektiğinde `general.py`; `test_guided.py`, `test_user_dimensions.py`, `test_sketch_constraints.py`, `test_general_plan.py`.

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
