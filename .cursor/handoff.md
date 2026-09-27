# drawingto3d — proje devam kaydı

## Güncel yön: ölçüm, hedefli eğitim ve çevrimdışı ürün — 2026-09-27

`PLAN.md` Bölüm 7'nin beş teslimi tamamlandı ve ölçüm bu makinede koşuldu. Sonuç:
`eval/reports/model-baseline.md` (tablolar `eval/baseline_report.py --check` ile koşu
kayıtlarına bağlı). Eğitim **çalıştırılmadı** ve gerekçesi raporda.

- Genel CAD şeması/derleyici ve okuma katmanları mevcut; bunları yeniden kurma.
- Ölçülen ayrım: **okuma** (vektör tam, gerçek tarama taban) ve **planlama** (iki hazır model
  de şema derinliğinde düşüyor). CAD bu ölçümde suçlanmadı.
- Sıradaki iş sırası: (1) raster aday kapısı — ok başı korumasını kılavuz moduna da sor,
  konum testini gerçek nokta–doğru parçası uzaklığına genelleştir, sonra kapsamı **tüm
  vaka kümesinde** yeniden ölç; (2) plan arayüzü — modelden istenen iç içe gövdeyi azalt.
- Eğitim kararı Bölüm 18C'nin koşullarını bekliyor: tekrarlanan hata (1 ve 2 uygulanmadan
  gösterilemez) ve ayrı doğrulama kümesi (pilot ≥10 / saklı ≥20, kullanıcı kararı bekliyor).
  Etiket kaynağı hazır: vektör paftanın metin katmanı, render rasterinde hangi basılı sayının
  nerede olduğunu tam veriyor.
- Geçiş eşiği (eğitim başlamadan kayıtlı): raster kapsamı tüm kümede `found/printed ≥ 0.8`,
  ölçek kuran pafta ≥ 4/5; planlama koşulunda derleyiciye ulaşan aday ≥ 1/2.
- PLAN Bölüm 18; veri sözleşmesi, sentetik üretim, parça gruplarına göre ayrım, eğitim seçim
  koşulları ve son modelin M1/ağ kapalı kabulünü tanımlar.
- `examples/pdf with steps/2/` ve `7/` aynı parçadır (dosyalar bayt bayt aynı: `Drawing.jpg` ≡
  `my_part.jpg`, `Part-2.STEP` ≡ `my_part.STEP`); yeni bağımsız örnek sayılmaz. Pilot ≥10 ve
  saklı ≥20 hedefi açık; mevcut sonuçlar genelleme kanıtı değil.
- Hedef yeterli bilgide otomatik dönüşüm, belirsizlikte kısa soru. Geçerli STEP tek başına
  doğru çizim yorumu değildir; bağımsız ölçü/görünüş kontrolü gerekir.

## Bu oturum: eğitim öncesi ölçüm dilimi — 2026-09-27 (3. oturum)

Kullanıcı isteği: PLAN.md'yi uygula, Bölüm 7'deki eğitim öncesi ölçümden başla, hazır modelleri
ölç, hatayı okuma/bağlama/planlama/CAD olarak ayır, sonuç gerektiriyorsa hedefli eğitim yap.

### Ne yapıldı

- `src/drawingto3d/planner.py` (yeni): modelden serbest Python yerine sürümlü `GeneralPlan`
  adayı ister; kanıt okuma zincirinden (`observe`→`bind`→`meaning`) atıflı gelir, modelin işi
  yalnız işlem seçmek. Atıf denetimi, şema denetimi ve derleyici kararı adayı yargılar.
  Modelin verdiği `source` artık adayı düşürmüyor: koşunun kaynağı yerine geçiyor ve durum
  `overrides` alanına yazılıyor (önce tüm aday `invalid` sayılıyordu ve bu, modelin yapmadığı
  bir planlama hatasını raporluyordu).
- `eval/model_baseline.py` (yeni): Bölüm 18B'nin dört koşulu ayrı ölçülür (`reading`, `chain`,
  `verified_plan`, `relations`); koşu başına okunur kayıt (kod HEAD + kirli dosya listesi,
  manifest, model digest/nicemleme, istem/şema/kanıt sürümü, örnekleme, soğuk/sıcak başlangıç,
  aşama süreleri, çıktı durumu, swap/boş sayfa örnekleri, ollama RSS tepesi). Referans STEP,
  doğru plan ve dosya adı isteme girmiyor.
- `eval/relations/plate-pocket-1.json` (yeni): elle doğrulanmış ilişki tablosu; `relations`
  koşusunun girdisi, teşhis amaçlı (otomatik başarıya sayılmaz).
- `eval/baseline_report.py` (yeni) + `eval/reports/model-baseline.md`: raporun tabloları koşu
  kayıtlarından üretilir, `--check` kayma olursa düşer.
- `tests/test_planner.py` (17), `tests/test_baseline_report.py` (2).
- Ölçüm araçları (`out/agent-s7/`, Git dışı): `where.py` (leke→küme→kapı sayımı),
  `readlog.py` (her aday için okuma sorusu ve cevabı), `crops.py` (kabul edilen adayların
  hazırlanmış kırpmaları tek kontak sayfada), `guard.py` (ok başı korumasının verdiği cevaplar).

### Ölçülen bulgular (ayrıntı: `eval/reports/model-baseline.md`)

- **Manifest:** `2/` ≡ `7/` bayt bayt; tek `part_group`, iki kaynak (`exercise-1` raster,
  `exercise-1-vector` vektör).
- **Okuma:** vektör paftalar tam (`plate-pocket-1` 7/7, `plastic-enclosure-1` 11/11,
  `exercise-1-vector` 13/13); aynı paftaların render'ı 6/7, 8/11 ve 8/13 (ölçek 4 haneye kadar
  aynı: 7.817 / 3.917 / 3.825 px/mm); gerçek taramalar taban — `exercise-17` 2/7,
  `exercise-51` 4/14, `exercise-13` 2/8, `flange-1` 4/13 ve beş taranmış paftanın yalnız ikisi
  ölçek kuruyor.
- **Zincir (`floor-1`, 20 satır: ok 6, okuma 16):** retlerin sahibi dört ayrı yerde —
  ölçek yok (4 pafta), dış kontur kapanmıyor (3 pafta), parça bu dilimin arketipine girmiyor
  (`exercise-1-vector`: okuma tam, ret "bu dilim yalnız düz parça arketipini öneriyor"),
  ve bağlama çap iddiası üretmiyor (`plastic-enclosure-1`: okuma 11/11, sonra "tam iki çap
  ölçüsü bekleniyordu, 0 okundu"). Yalnız `plate-pocket-1` zincirin sonuna gidiyor: `draft`.
- **CAD (`verified_plan`):** elle doğrulanmış üç plan derleyiciden geçiyor
  (`bracket_linear_pattern` 22 084.3806 mm³, `shaft_revolve_cross_hole` 13544.7373 mm³).
  CAD bu ölçümde kendini göstermedi.
- **Kaybın yeri:** `Exercise 17`'de koruma gerçek koşu içinde 40 adayın 10'unu düşürüyor,
  30'unu okuyucuya geçiriyor; o 30'un 28'i ok/kavis/daire ve kutuları çizgi ekseninden
  7.5–39 px uzakta. Yani sorun eşik değil, **sınıflandırma**: kırpma basılı sayı mı?
- **Planlama:** `qwen2.5vl:3b` (2048'de de, şema grameriyle 4096'da da) nesneyi kapatamıyor;
  `qwen3-vl:8b-instruct` temiz kapanıyor, yedi değeri ve atıfları doğru veriyor, ama
  `sketches.*.entities[0]` tek dizeye çöküyor.
- **Kaynak:** model koşusunda takas 13 312 MB'da sabit, boş sayfa en az 14.5 MB, ollama RSS
  tepesi 8.3 GB; model dışı koşuda takas 12 288 → 10 240 MB. Ağırlığın disk boyutu bellek
  sayılmıyor.

### Bu dilimde yapılan okuyucu düzeltmesi

Ok başı koruması artık kılavuz moduna da soruluyor ve konum testi gerçek nokta–doğru parçası
uzaklığına genelleştirildi (eski hesap köşegen ankrajda tek koordinat ölçüyordu, yani yanlış
cevap veriyordu; eksen hizalı girdide yeni hesap bit bit aynı — `tests/test_reading_gate.py`).
Tüm vaka kümesinde önce/sonra ölçüldü: **22 kaydın 22'si aynı**, `check_tables` 20 satırda sıfır
kayma. Yani kazanç yok, kayıp da yok; doğruluk için kalıyor.

### Sonraki adım ve nasıl yeniden koşulur

1. **Ölçek kurulamıyor (4 pafta)** — kapsamı artırmak gerekiyor; kaybın yeri ölçüldü, sıradaki
   iş eşik değil ayrı bir **sınıflandırma** sorusu: bu kırpma basılı sayı mı, çizimin kendi
   mürekkebi mi. Etiket kaynağı hazır (vektör paftanın metin katmanı ↔ render'ı).
2. **Dış kontur kapanmıyor (3 pafta)** — taramada çizgi/yay döngüsü birleşmiyor; `proposal`
   dış profili bulamıyor.
3. **Bağlama: çap iddiası (1 pafta)** — `plastic-enclosure-1`'in bilinen açık işi.
4. **Plan arayüzü** — modelden istenen iç içe gövdeyi azalt, derleyiciye ulaşan aday oranını ölç.
5. Eğitim ancak 1-4'ten sonra ve Bölüm 18C koşulları sağlanınca; geçiş eşiği raporda kayıtlı.

```
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --no-model --conditions reading,chain,verified_plan --label <etiket>
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen3-vl:8b-instruct --conditions relations --cases plate-pocket-1 --label <etiket>
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --write   # rapor tablolarını tazele
PYTHONPATH=src .venv/bin/python eval/check_tables.py && .venv/bin/python -m pytest -q
```

## Önceki oturum kayıtları

## Güncel durum: genel plan sözleşmesi ve derleyici kuruldu — 2026-09-27 (2. oturum)

Kullanıcı, verilen parçaların yalnız test örneği olduğunu ve her yeni parçaya özel tanıyıcı
istemediğini belirtti: hedef, her türlü teknik çizimi okuyabilen evrensel bir araç.
**Ana uygulama belgesi: `PLAN.md`.** Sohbet geçmişine ihtiyaç duymayan görev tanımı,
mevcut kod haritası, ortam/komutlar, aşamalar ve kabul koşulları bu dosyadadır.
Hedef: M1 / 16 GB üzerinde kurulum sonrası çevrimdışı PDF/PNG/JPG teknik çizim → STEP.

Bu oturumda PLAN.md Bölüm 7'deki ilk kodlama dilimi uygulandı ve ölçüldü; Bölüm 10 kabul
listesi karşılandı. Plaka artık ayrı bir motor değil: genel planın plaka adaptörüyle
ifade edilmiş hâli, ve genel derleyici iki farklı işlem birleşimiyle sınandı.

### Bu oturumda ne yapıldı

- `src/drawingto3d/general.py` (yeni): sürümlü `GeneralPlan` sözleşmesi — kaynak kimliği
  (kind/ref/sha256), tipli parametreler (mm/in/deg/count; printed/derived/assumed/user +
  açıklama + span kimlikleri), adlandırılmış düzlemde ofsetli eskizler, işlem listesi
  (extrude/revolve/fuse/cut/repeat_linear/repeat_circular/fillet), beklenti ve varsayımlar.
  `evaluate_parameters` (döngü denetimi, inç → mm), `compile_general` (yalnız geo fiillerini
  çağıran deterministik Python; dosya adı/parça ailesi/kaynak metadata koda sızmaz — test edilir),
  `check_general` (geçerli tek katı, STEP gidiş-dönüş hacmi, bbox, bildirilen hacim, her kesim
  aracının silindirleri), `from_plate` (plaka bilgisinin yaşadığı tek katman), `edit_parameters`
  (kullanıcı düzeltmesini türetme sessizce değiştirmez).
- `geo.py`: yeni `profile_extrude`, `profile_revolve` (offset), `repeat_linear`, `repeat_circular`.
  Kod modeli prompt'u geo.py'den okuduğu için yeni fiiller eski model yolunda da görünür.
  `cadrun.py`: artık her eksendeki silindirik yüzü raporlar (`cylinders_axis`: eksen noktası, yön,
  göreli aralık); plaka denetimi yeni raporla geçiyor. Silindir eşleme, aracın kendi normaline
  göre işaret düzeltmesiyle kanonikleştirildi.
- `eval/plans/`: `bracket_linear_pattern.json` (extrude + repeat + cut, XZ düzleminde delikler)
  ve `shaft_revolve_cross_hole.json` (revolve + fuse + yan delik). Beklenen hacimler plandan
  okunmadı: `derive_examples.py` kapalı form + Simpson + Monte Carlo ile bağımsız türetip
  doğruluyor. `eval/plans/README.md` çekirdek (OCC) hassasiyet sınırını kaydeder.
- `tests/test_general_plan.py` (23 test): iki örnek planın inşası + denetimi; 8 şema reddi (açık
  profil, döngüsel parametre, birim uyuşmazlığı, kaynaksız basılı ölçü, tanımsız referans/gövde,
  mükerrer çıktı, ayrılmış ad); ayıran boolean hatası; düzenleme zinciri (hole_dx 100 → 110 →
  130 mm katı, denetim geçer); plaka motoruyla hacim/boyut/silindir eşleşmesi; taşınan deliğin
  araç denetiminden geçmediği; kaynak hash koruması; çekirdek hassasiyet kaydı.
- CLI: `build-general <plan.json> <out_dir> [--drawing çizim]`; geçersiz plan → exit 2, tek satır
  okunabilir hata. `plan`/`build-plan` (PlatePlan) ve eski `read`/`build` korundu.
- `eval/cases.json`: her vakada `part_group`, `split`, `feature_ids`; boş `pilot`/`hidden` dizileri
  ve `_split` notu; `eval/README.md` bu alanları ve `plans/` klasörünü belgeler.

### Ölçümler (bu oturum, yerel)

- pytest: **169 geçti** (146 eski + 23 yeni), 79,9 s. `eval/check_tables.py`: 20 satır, 0 tutmuyor.
  `eval/plate_plan.py`: pass, simetrik hacim farkı 0,0 mm³, inşa 3,49 s.
- İki örnek plan CLI ile kuruldu, denetimler geçti: bracket hacmi kapalı formla fark ~8e-12;
  shaft mil hacmi dönel kapalı formla 1e-4 mm³ toleransla doğrulandı; yan delik silindiri
  yarıçap/eksen/aralık 1e-3 toleransla doğru.
- Plaka genel motorda: hacim/boyut/dokuz silindir kümesi plaka motoruyla eşleşiyor (göreli 1e-6).
- Çekirdek sınırı (kayıtlı): silindir-silindir kesişimi yaklaşık hesaplanır (~1,6e-2 mm³; 4,5e-5
  göreli); STEP'e yazıp geri okuma ~2,6e-9 göreli hacim gürültüsü ekler. Bu yüzden shaft planı
  hacim beklentisi bildirmez ve `export_round_trip` eşiği göreli 1e-7'dir.

### Hâlâ yapılmayan

- Okuma katmanı genelleştirmesi (PLAN.md Bölüm 3A/3B): gözlem (`observe.py`), ölçü bağlama
  (`bind.py`), anlam seçimi (`meaning.py`) ve plan önerisi (`proposal.py`) dilimleri eklendi; plaka
  paftası artık aile-bağımsız motordan STEP'e gidiyor (124 825,4 mm³, kapalı formülle %0.0000 fark).
  Açık işler: raster gözlemci; daha geniş arketipler (zincir ölçüleri, ikiden çok çap, asimetrik
  yerleşim, kare köşeli kontur) — ret listesi bunların yol haritası.
- Pilot (en az 10) ve saklı (en az 20, en az 10'u raster) veri toplama kullanıcıda; ayrım
  altyapısı manifestte hazır, diziler boş.
- Plaka tanıyıcı henüz deneysel seçeneğe taşınmadı; `plan`/`build-plan` hâlâ PlatePlan konuşur.
- Uygulama arayüzü (app.py, static/index.html) genel planı göstermiyor; beş çıktı durumu
  (needs_input/draft/validated/unsupported/failed) uçtan uca ayrıştırılmadı.

### Devralan ajan için ilk adım

1. Önce doğrula (depo kökünde): `.venv/bin/python -m pytest -q`,
   `PYTHONPATH=src .venv/bin/python eval/check_tables.py`,
   `PYTHONPATH=src .venv/bin/python eval/plate_plan.py` ve
   `PYTHONPATH=src .venv/bin/python -m drawingto3d build-general eval/plans/bracket_linear_pattern.json out/general-examples/bracket`.
2. Sıradaki iş `PLAN.md`'ye göre: raster gözlemci (Bölüm 3C) ya da arayüzün genel planı
   göstermesi. `git status` ile bu oturumun commit edilmemiş değişikliklerini koru.
3. Pilot/saklı veri gelmeden genelleme iddiası yazma; değerlendirme sonucunu uydurma.

### Okuma katmanı — ilk dilim (aynı oturum, `ddacd48`)

- `src/drawingto3d/observe.py` (yeni): her çizim sayfası için tek gözlem kaydı — vektör alt yolları
  (noktalar, bbox, nesne/yol kimliği, yöntem), uydurulmuş çizgi/daire/yay kayıtları (kendi artığıyla),
  basılı her metin (ham dize, değer, birim, adet, kaynak karakter aralığı, kutu) ve kaynak özeti +
  ölçüm çerçevesi. Metin katmanının hangi yöne yerleştiği artık adıyla kaydedilir (`mirrored`/`as-is`).
- Plaka deneyiminin vektör yürüyüşü artık ortak: `observe.vector_paths`; `plate.vector_groups` onun
  üstünde ince bir gruplama (plaka testleri değişmedi). `ingest.text_groups` ve
  `ingest.upright_placement` paylaşıldı.
- Bezier segmentli nesneler tümden atlanır ve `skipped` listesinde nedeniyle durur ("control points
  are not exposed"): yarım ama bitmiş görünen bir kontur, adı konmuş bir eksikten kötüdür.
- CLI: `observe <çizim> <out_dir>` → `observations.json`; raster girdi → exit 2, neden tek satır.
- Ölçüm (model yok): plaka 209 yol / 169 ilkel / 45 metin (~0,11 s), plastik 456 / 365 / 65;
  plaka kaydı 239 KB. Plaka kaydı kendi çizimini taşır: dört köşe dairesi 100,02 × 60,01 mm
  aralıkta, Ø6,81 delik, 25,01 mm cep yarıçapı — tanıyıcı kurallarından değil, geometriden.
- Testler: `tests/test_observe.py` 11 test; toplam paket **180 geçti**.
- Sıradaki dilim: ölçü bağlama (okların bağlandığı geometri), görünüş ayrımı ve ölçek; ardından
  raster gözlemci ve gözlem → genel plan önerisi.

### Ölçü bağlama — ikinci dilim (aynı oturum, `9031094`)

- `src/drawingto3d/bind.py` (yeni): her basılı sayı için ankrajlarının oturduğu çizgiler (row =
  iki ankrajı birleştiren satır; stub = ucu ankrajda biten çizgi; crossing = ankrajdan geçen
  çizgi), uçları çakışan açık çizgi zincirleri (en çok 4 adım) ve her iniş noktasının dokunduğu
  özellikler (daire/yay merkez ya da kenar, uç, köşe) — piksel mesafesi, hangi zincirle gidildiği
  ve hangi ankrajda olduğuyla. Seçim yapılmaz; tüm adaylar kayda geçer.
- Ölçü ekseni hizalaması: iki ankrajlı linear ölçüde, eksen boyunca eşleşen adaylar kaydedilir
  (dik uzaklık kırpılmaz — standoff çizimin kuralı). Plakada satır uçları delik x'ini 2,4 px'te
  paylaşıyor; sıra: daire merkezi > yay merkezi > uçlar, 2 px ızgarada tekilleştirme.
- `implied_px_per_mm` = satırın çizili uzunluğu / basılı değer; paftanın kendi kalibrasyonuyla
  oranı 1 → ölçek tutarlı; ayrılıyorsa farklı ölçekli detay ya da şüpheli ankraj.
- Ölçüm: plaka 7/7 bağlı — `100,00` iki üst deliğe 2,4 px hizada; `80,00` köşe yayları 0,5 px;
  `Ø6,80` lideri zincirle delik kenarında 0,09 px; `50,00` cep kenarında 0,12 px. Plastik 14
  sayı: 9 aligned + 4 partial + 1 unbound (`R8.00` radüs lideri — açık).
- CLI: `bind <çizim> <out_dir>` → bindings.json; raster → exit 2.
- Testler: `tests/test_bind.py` (15); tam paket **195 geçti**.
- Sıradaki dilim: anlam seçimi — bağlanan adaylardan hangi özelliğin hangi sayıya ait olduğunu
  seçmek (simetri, "4 x", görünüş ayrımı) ve gözlem+bağlama+anlamı genel plan önerisine çevirmek.

### Anlam seçimi — üçüncü dilim (aynı oturum, `085cd83`)

- `src/drawingto3d/meaning.py` (yeni): bağlanan adaylardan her sayının okunuşu — distance (satır
  eksenine izdüşüm; tür+maliyet sırası, elenen çiftler alternatif olarak kayıtta), diameter/radius
  (`matched_geometry` tüm eşleşenler), komşu "N x" sayısının `count`/`covered` karşılaştırması.
  Doğrulanamayan span `unresolved` kalır; okuma uydurulmaz.
- Ölçüm: plaka 7/7 okundu — `100,00` → g9-g11 (100,71); `60,00` → 60,43; `80,00` → köşe yayları
  (80,46); `15,00` → 15,10; `8,00` → 8,03; `50,00` → cep çapı (50,36); `Ø6,80` → dört delik, sayı
  4/4. Plastik: 4 confirmed, 10 unresolved (zincir/detay ölçüleri — açık iş).
- CLI: `meaning <çizim> <out_dir>` → meaning.json; raster → exit 2.
- Testler: `tests/test_meaning.py` (14); tam paket **209 geçti**.
- Sıradaki dilim: gözlem+bağlama+anlamı **genel plan önerisine** çevirmek (görünüş ayrımı, hangi
  daire delik hangisi cep, kalınlık/derinlik) ve raster gözlemci.

### Öneri — dördüncü dilim (aynı oturum, `f61b7cc`)

- `src/drawingto3d/proposal.py` (yeni): üç okuma katmanından `GeneralPlan` önerisi. Sayfa
  çerçevesi atlanır (sayfanın ≥%80'ini kaplayan ya da ≥%60 kaplayıp başka döngüyü içeren döngü);
  kontur iki eksen-hizalı çizgi çifti + dört çeyrek yay olmalı. Doğrulanan iddialar dokundukları
  geometriye göre ayrılır: delik aralığı (iki daire), kontur yüksekliği (iki köşe yayı), kesit
  kalınlığı ve cep derinliği (parça dışındaki iddialar), delik ve cep çapları.
- Her parametre basılı (span id'siyle) ya da türetilmiş; ölçülen geometri dokuz kontrolle doğrular
  (en büyük Δ0,87 mm, 120 mm genişlikte); tutmazsa ret — ret listesi eksikleri söyler (plastik:
  hiç çap ölçüsü yok; 3 mesafe + 1 yarıçap doğrulandı).
- Ölçüm: plaka artık uçtan uca aile-bağımsız — `propose` → `build-general`: **124 825,4 mm³**
  (kapalı formül farkı %0.0000), **120,00 × 80,00 × 15,00 mm**, 4 delik + 1 cep silindiri
  doğrulandı, tüm zincir ~6 s.
- CLI: `propose <çizim> <out_dir>` → proposal.json (+ plan.json); ret ve raster → exit 2.
- Testler: `tests/test_proposal.py` (16); tam paket **225 geçti**; check_tables 20/20; plate_plan
  geçti.
- Sıradaki dilim: raster gözlemci; sonra daha geniş arketipler (zincir ölçüleri, ikiden çok çap,
  asimetrik yerleşim) ve arayüzün genel planı göstermesi.

## Aktarım ve kayıtlar

Planı başka ajana gönderirken güncel proje çalışma ağacı da erişilebilir olmalı; yalnız
son commit mevcut değişiklikleri içermez. `.venv` ve `.venv-cad` ayrımı korunmalı.
`HANDOFF.md`, `.cursor/handoff.md` ve `out/HANDOFF.md` aynı güncel özeti taşır;
son iki dosyada daha eski oturumların tarihçesi de vardır. `out/` Git tarafından yok sayılır.

Aşağıdaki 2026-09-26 kaydı ölçümlerin ve eski kararların tarihçesidir. Oradaki sonraki iş
önerilerinin yerini `PLAN.md` almıştır.

---

# 2026-09-26 — dar plaka deneyi (tarihsel kayıt)

## O oturumdaki hedef ve durum

2026-09-26: M1 / 16 GB üzerinde çevrimdışı teknik çizim → STEP.
İlk teslim, vektör PDF'deki **dört delikli, yuvarlatılmış dikdörtgen plaka + merkezde dairesel kör cep** ailesi.
Bu ilk aşama çalışıyor; genel PDF/PNG/JPG dönüşümü tamamlanmış değildir.
Değişiklikler çalışma ağacında; bu oturumda commit yapılmadı.

Kullanıcı hem `.cursor/handoff.md` hem proje içindeki kaydın güncellenmesini istedi.
Bu kök dosya Git'e alınabilir ana devam kaydıdır. `out/HANDOFF.md` ve `.cursor/handoff.md` de güncellendi;
eski çalışma notları bu iki dosyanın tarihçe bölümünde korunur. `out/` Git tarafından yok sayılır.

## Ne değişti?

- `src/drawingto3d/plate.py`: PDFium ile vektör alt yolları çıkarır; dört yay + dört düz dış kenar,
  dört eş delik, merkez daire ve hizalı kör cep kesitini eşleştirir. Boyutları ölçü ankrajlarına bağlar.
  Dosya adına veya örneğin sayılarına göre seçim yapmaz; referans STEP'e erişmez.
- `src/drawingto3d/plan.py`: tipli `PlatePlan`, her parametrenin kaynak ölçüsü/türetmesi, kaynak dosya SHA256,
  kullanıcı düzeltmeleri, geometrik ön koşullar ve deterministik üç CAD işlemi.
- Plaka uzunluğu `hole_dx + height - hole_dy`, köşe yarıçapı `(height - hole_dy)/2` ile önerilir.
  Dört kenar payı ve yaylar çizili geometriyle karşılaştırılır. **Bunlar basılı ölçü değildir**;
  planda ve arayüzde incelenecek kabul olarak kalır.
- `cadrun.py`: tek geçerli katı şartı, STEP'i yeniden açarak kontrol ve `geometry.json` üretimi.
  Plan denetimi boyut, analitik hacim, dokuz silindirik yüzün yarıçap/merkez/derinliklerini karşılaştırır.
  Delikleri başka yere taşıyıp aynı hacmi elde etmek denetimden geçmez.
- Arayüz: desteklenen PDF'de model çağırmadan özellik tablosu; düzenlenebilir dokuz parametre,
  kaynak türü ve kabuller; taslak STEP, CAD planı ve denetim bağlantıları.
  Önizleme izometrik ve gölgeli; plakanın cebi/delikleri yan görünüşte kaybolmuyor.
  Yüklemeler artık ayrı klasörlerde tutulur; yeni yükleme eski oturumun çizimini değiştirmez.
- `reason_drawing(..., prefer_plan=True)` planı önce dener; `plate_plan=...` deterministik üretir.
  Desteklenmeyen paftalar mevcut model yoluna gider. Eski CLI `read/build` korunmuştur.
- Yeni CLI: `plan` ve `build-plan`. Bir plan başka dosyaya uygulanırsa SHA256 kontrolü reddeder.
- Taslaklar `audit.accepted=False` taşır; `audit.checks` geometrinin plana uygunluğunu ayrı kaydeder.
  Referansa uymak, basılı olmayan ölçülerin imalat için onaylandığı anlamına gelmez.

## Ölçülen sonuç

Kaynak: `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`
Referans **yalnız üretim bittikten sonra** değerlendirmede kullanıldı.

| Özellik | Yeni çıktı | Referans |
|---|---|---|
| Dış boyut | 120 × 80 × 15 mm | aynı |
| Delik deseni | 100 × 60 mm, dört Ø6,8 | aynı geometri |
| Merkez cep | Ø50, derinlik 8 mm | aynı |
| Köşe yarıçapı | 10 mm, türetilmiş | aynı |
| Hacim | 124,825 cm³ | 124,825 cm³ |
| Geçerli katı | 1 | 1 |
| Simetrik hacim farkı | **0 mm³** | iki yönlü Boolean fark |

Yüz bölünmeleri aynı değildir (16 ve 21 yüz); aynı hacim/geometriyi farklı yüz parçaları temsil eder.
`eval/plate_plan.py` koşusunda PDF → plan → STEP yaklaşık **5,221 saniye**; bu tek koşunun süresidir.
Model çağrısı, ağ isteği veya model indirmesi yoktur. Python/CAD bağımlılıkları önceden kurulu olmalıdır.

Eski model yolunun `out/eval` sonuçları üzerine yazılmadı: plaka 100 mm uzunluk, kutu yanlış hacim,
flanş yanlış boyut. Yeni sonuçlar ayrı `out/plate-plan/` klasöründedir.

## Tekrarlama

Proje kökünde:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d plan "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate-plan
PYTHONPATH=src .venv/bin/python -m drawingto3d build-plan "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate-plan/plan.json out/plate-plan
PYTHONPATH=src .venv/bin/python eval/plate_plan.py
PYTHONPATH=src .venv/bin/python -m drawingto3d.app
```

Son komut normal arayüzü `http://127.0.0.1:8765` adresinde açar.

Çıktılar:

- `out/plate-plan/part.step`, `part.stl`
- `out/plate-plan/plan.json`: parametreler, kaynak ölçü kimlikleri, türetmeler ve kabuller
- `out/plate-plan/geometry.json`: yeniden açılan STEP'in ölçüleri
- `out/plate-plan/plan-audit.json`: planla geometri karşılaştırması
- `out/plate-plan/comparison.json`: referans karşılaştırması ve iki yönlü hacim farkı

## Doğrulama

- 122 mevcut test ve 24 yeni test geçti (146 toplam). Tam koşuda 143 test sandbox içinde geçti;
  localhost gerektiren tek eski test izinli ortamda geçti. Son iki düzeltme testi eklenince yeni
  dosyanın 24 testi yeniden çalıştırıldı ve geçti. Kod hatası nedeniyle başarısız test kalmadı.
- Yeni `tests/test_plate_plan.py`: 24 test. Gerçek PDF, modele hiç başvurmayan üretim, kaynak özeti,
  geçersiz parametreler, kullanıcı düzeltme kaynağı, türetilmiş ölçülerin yeniden hesabı, açık kullanıcı geçersiz kılması, oturum kaydı, üç farklı sentetik boyut/ölçek/konum,
  eksik derinlik, fazla ölçü, belirsiz ikinci kesit, kaymış delik ve yanlış lider reddi.
- `eval/check_tables.py`: 20 satır, 0 kayma. OCR/front-end algoritması değiştirilmedi;
  tüm raster değerlendirmeleri bu oturumda yeniden çalıştırılmadı.
- `eval/plate_plan.py`: tüm karşılaştırmalar geçti, simetrik fark 0 mm³.
- Tarayıcıda PDF yükleme → özellik tablosu → STEP üretimi → indirme bağlantısı doğrulandı.
  15 mm kalınlıkta 15 mm cep reddedildi; 8 mm geri yazılınca tekrar üretildi.
  Test arayüzü bu oturum sonunda localhost:8766 üzerinde açık bırakıldı. Normal komut 8765 kullanır.

## O tarihteki sınırlar ve sonraki iş önerileri (yerini PLAN.md aldı)

1. Otomatik plan çıkarma **yalnız bu vektör ailede**. PDF yollarının aynı nesnede gruplanması,
   poligon çizgileri, eksene hizalı görünüş ve üç seviyeli kesit beklenir. Bezier eğrileri,
   Form XObject içindeki yollar, döndürülmüş sayfalar ve farklı gruplama henüz desteklenmez.
2. Dört eş kenar payı ve köşe yarıçapı varsayımı açık kalır. Genel bir teknik çizimde çizili ölçek
   tek başına imalat ölçüsü kanıtı değildir. Toleranslar, GD&T ve vida helisi modellenmez.
3. Raster PDF/PNG/JPG hâlâ eski OCR/model yolunda; flanş/kutu başarısı iyileştirildi diye raporlanmamalı.
4. Önce vektör kontur birleştirmeyi nesne gruplamasından bağımsız yap; gerçek ikinci bir plaka PDF'si
   ve PDF üreticisiyle doğrula. Sentetik testler farklı parametreleri denetler, farklı PDF ihracatlarını değil.
5. Sonra aynı `PlatePlan` kaydını raster görünüş/daire/ölçü eşleştirmesinden üret; OCR'yi yalnız belirsiz
   bölgelerde yerel görsel modelle destekle. Kaynağı belirsiz ölçüyü kesinmiş gibi doldurma.
6. Model yolunda `records_text` hâlâ geometri ilişkilerini kaybediyor. Genel özellik planına taşı;
   kutu/flanşı bu plaka şablonuna zorlamadan yeni aileler ekle.
7. Birim testleri referans STEP'i üretim girdisi yapmamalı. Karşılaştırma yalnız değerlendirmede.
8. `build123d` ve CadQuery farklı OpenCascade sürümleri kullandığı için `.venv` / `.venv-cad`
   ayrımı korunmalı. Dağıtım bağımlılıklarını sonradan sadeleştir.

Önceki OCR deneyleri ve vazgeçilen yollar için `eval/README.md` Known gaps, `CHANGES.md`
ve aşağıdaki tarihçelere bak. Ölçülüp bırakılan yolları aynı hipotezle tekrarlama.

---

# Önceki oturumların tarihçesi

Aşağıdaki görevler ve durumlar geçmiş kayıttır; güncel devam noktası yukarıdadır.

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

## Raster dilimi — 2026-09-27 (`64ed9d8`)

- `src/drawingto3d/raster.py` (yeni): PNG/JPG paftalar pikselden gözlenir — Hough çizgileri
  birleştirilir; daireler aday + paftanın mürekkep testleri (yarıçap rafine r±6 px, kapsama ≥0,85,
  iç ≤0,25, kelime-boyutlu OCR kutusu dışı); doğrulanan daireye binen kısa kirişler çizgi listesinden
  düşülür; tesseract `psm 11` CLI'dan. `observe()` PNG/JPG'yi bu yola gönderir; kayıt şekli vektörle
  aynı (`page_size_pt`/`dpi` isteğe bağlı).
- Ölçüm: Flange 388 çizgi + 2 daire + 29 ifade; my_part 343 çizgi + 6 daire + 49 ifade; CLI exit 0.
- Üst zincir rasterda koşuyor ama ankraj yok → `meaning` no-scale, `proposal` "pafta ölçeği
  okunamadı". Sıradaki dilim: **raster ankrajları + ölçek kalibrasyonu**.
- Tam paket **234 geçti**; CHANGES.md `64ed9d8` girdisi; PLAN.md §16.
