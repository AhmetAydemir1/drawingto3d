# drawingto3d — proje özeti ve PDF okuma akışı (devir notu)

Bu not, projeyi **hiç görmemiş bir agent** için yazıldı: ne yapıldı, PDF tam olarak nasıl okunuyor,
hangi sayı ölçülmüş, hangisi ölçülmemiş, nerede tuzak var.
Yazan tur: 2026-10-03, HEAD **4fb09b6**, ağaç temiz (bu not dışında). Bütün sayılar aynı turda
yeniden koşuldu; koşmayan bir sayı "kayıt" diye işaretlendi.

---

## 1. Proje tek cümlede

M1 / 16 GB bir Mac'te **çevrimdışı** çalışan, 2B teknik çizimi (PDF/PNG/JPG) 3B katıya (STEP + STL)
çeviren ve okumasını kullanıcıya **çizimin üzerinde** düzelttiren bir prototip. Çalışma anında hiçbir
bulut servisi çağrılmaz; çalışan her model yereldir (Ollama), her üretim adımı deterministik Python'dur.

Durum dürüstçe: **erken araştırma prototipi, ürün değil.** Tek bir pafta (plaka) uçtan uca dönüyor;
ölçümler — başarısızlar dahil — depoda tutuluyor. "Genel teknik çizim → STEP başarısı" iddiası yok.

**Değişmez kurallar** (PLAN.md §1, ihlal edilirse iş geçersiz):

- Üretimde dosya adı, örnek numarası, bilinen koordinat, sabit delik sayısı veya referans STEP'e göre
  özel çözüm yazma.
- Referans STEP **yalnız ayrı değerlendiriciye** girer; okuyucuya, model istemine, önericiye verilmez.
- `examples/` **yalnız test/değerlendirme verisidir**; eğitim/ince ayar/kopyalama kaynağı değildir.
- Eksik bilgi birden fazla şekle izin veriyorsa **kullanıcıya sorulur**; varsayım ölçü diye sunulmaz.
- Geçerli katı + doğru dış ölçü + STEP'in yeniden açılması, **parçanın doğruluğunu kanıtlamaz**.
- Test beklentisini hatalı kodun çıktısına uydurma; hata açıklaması eklemek düzeltmek değildir.
- `git reset` / `git clean` / toplu silme yok. Ağaçta **paralel çalışan başka bir ajan** olabilir.

---

## 2. Depo haritası

| Yol | Ne var |
|---|---|
| `src/drawingto3d/` | ürün: `ingest` → `observe`/`raster` → `perceive`/`lines`/`scale`/`reader` → `bind` → `meaning` → `proposal` → `general`/`cadrun`; ayrıca `planner` (yerel model), `guided`+`app`+`static/` (arayüz), `sketch`/`sketch_constraints`, `contour_audit` |
| `tests/` | 66 `test_*.py` (+ `src/drawingto3d/legacy/tests/`), **820 test** (`pytest --collect-only -q` → `820 tests collected in 82.52s`, bu turda doğrulandı) |
| `eval/` | ölçüm koşucuları, kanıt paketleri, `eval/reports/` altında raporlar; `eval/check_tables.py` ve `eval/baseline_report.py --check` tabloyu kayda bağlar |
| `examples/` | pafta + referans STEP çiftleri (yalnız değerlendirme) |
| `PLAN.md` | kabul koşulları + durum tablosu (A0, P00–P12) + F01–F14 açıkları |
| `HANDOFF.md` | 4200 satırlık uzun oturum devri (Türkçe, tarihçe ağırlıklı) |
| `CHANGES.md` | her değişikliğin ne kazandırdığı / neye mal olduğu |
| `docs/` | uygulama planı, denetimler, eski planlar; `DEEPSEEK_PROMPT.md` son devir özeti |
| `out/` | çalışma çıktıları (git-ignored) — oturumlar, STEP'ler, JSON kayıtlar |

Ortamlar: `.venv` (Python 3.12.8, `-e ".[dev]"`), `.venv-cad` (cadquery/metrics için ayrı yorumlayıcı).
Okuma zinciri Python'dur; **CAD ölçümü** (referans STEP karşılaştırması) `.venv-cad` ister.

```bash
# testler (tam takım ~4-5 dk)
.venv/bin/python -m pytest -q
# arayüz
PYTHONPATH=src .venv/bin/python -m drawingto3d.app      # http://127.0.0.1:8765/guided
# bağımsız CAD ölçümü (referans STEP'e karşı)
.venv-cad/bin/python eval/metrics.py <üretilen.step> <referans.step>
# tablo ↔ kayıt tutarlılığı
PYTHONPATH=src .venv/bin/python eval/check_tables.py
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --check
```

---

## 3. PDF nasıl okunuyor — katman katman

Akış (README'deki sözleşme, kodda karşılığı):

```
kaynak dosya + sha256 + sayfa
  → ingest.load_page        : 200 dpi render + PDF metin katmanı
  → observe                 : vektör alt-yollar, ilkel şekiller, basılı ifadeler, pafta çerçevesi
  → perceive (+lines,scale) : basılı sayının "ölçü satırı" mı, lider mi; ankrajlar
  → scale                   : paftanın kendi ölçeği (px/mm), çoğunluk + tanık
  → bind                    : her sayı dokunduğu geometriye (row/stub/crossing/chain/aligned)
  → meaning                 : her sayı desteklediği iddiaya (distance/diameter/radius)
  → proposal / planner      : okumalardan GeneralPlan (kurallı veya yerel model)
  → general + cadrun        : deterministik CAD → STEP + yeniden açma + özellik denetimi
```

Her aşama **kendi JSON kaydını** yazar: `observations.json`, `bindings.json`, `meaning.json`,
`proposal.json`, `plan.json`, `plan-audit.json`. Hiçbir aşama bir sonrakinin çıktısını tahmin etmez.

### 3.1 Açma ve metin katmanı — `ingest.py`

- `load_page`: PDF → **200 dpi** (ör. A4 1653×2339) raster + `text_groups(page)`.
- `text_groups`: PDF karakterlerini **ifade**lere gruplar. Eşikler karakterin kendi boyutuna göre
  (satır veya kolon komşuluğu), yani 1:1 A4 ile 1:4 A0 aynı kodla okunur. Ham metin korunur
  (`100,00` böyle kalır) ve her ifade kullandığı **karakter indekslerini** taşır (kaynak gösterilebilsin).
- `upright_placement`: metin kutusu iki şekilde yerleştirilir (aynalı / olduğu gibi); kutunun altındaki
  mürekkep **çevresindeki halkadan daha koyu** olan kazanır ve kayıt hangisinin seçildiğini adıyla yazar
  (`mirrored`/`as-is`).
- `parse_dimension_unit`: `Ø/⌀/Φ/Ö`, baştaki `R`, `C` (pah), `°` **türü** belirler; sondaki
  `THRU ALL / DEEP / TYP / C'BORE` "nasıl yapılır" der, boyut değildir; `1 1/4` = 1.25; harf kalan
  token ölçü değildir (`SCALE 1:2`, `2389K26` → text). `split_count`: `4x2-Ø30` → 8 adet.
- `apply_sheet_unit`: paftada bir tek birim olur — bir yerde `in` varsa işaretsiz sayılar da inçtir.

### 3.2 Gözlem — `observe.py` (aile-bağımsız, karar vermeyen katman)

- `vector_paths`: pdfium'un **ham** yol segmentleri. Yalnız MOVETO/LINETO okunur; **BEZIERTO varsa
  nesne bütün hâlinde atlanır** ve `skipped` listesine "kontrol noktaları bu bağlamada açık değil"
  gerekçesiyle yazılır (eksik konturu tam göstermektense adı konmuş delik iyidir). Sayfa dönmüşse
  (`/Rotate ≠ 0`) `Unsupported`. Bütün noktalar **200 dpi px, sol üst, y aşağı** — metin kutularıyla
  aynı çerçeve.
- `_primitive`: 2 noktalı açık yol → `line` (`method="two-point"`); ≥8 nokta → en küçük kareler daire
  uydurması, artık `≤ max(0.6 px, 0.005·r)` ve `r ≥ 3 px` ise kabul; kapalı veya `|sweep| ≥ 355°` →
  `circle`, `5 ≤ |sweep| < 355` → `arc`. Uymayan yol dürüstçe "poligon".
- `_diameter_prefix_glyph`: **Ø öneki metin değil, çizim olabilir.** Rakamların yanına çizilmiş küçük
  daire (yarıçap ≤ ifade yüksekliğinin %60'ı, ifade kutusunun 1,2 yükseklik yakınında) bulunursa o
  ifade `kind="diameter"` yapılır. Ölçülmüş ayrım: glifler rakamların 8–21 px yanında, paftadaki gerçek
  daireler ≥138 px uzakta.
- `sheet_frame` (PLAN 8.6): sayfanın **kendi çerçevesi** = iki kenarı da sayfanın %80'ini kaplayan en
  büyük kapalı yol. Dikdörtgen, `minAreaRect` ile köşeler, kenarların sayfa eksenlerinden **küçük**
  sapması açı olarak; `≤ 2°` ise hizalı. Yön eksenleri kaynağın `/Rotate` çeyrek turundan; kaynağın
  değeri çeyrek tur değilse "eksen yalnız çerçeveden okunur, varsayılmaz" notu düşülür.
- Çıktı: `Observations` — `paths`, `primitives`, `texts` (her biri `id`, ham metin, değer, birim, tür,
  adet, kutu, `char_range`), `skipped`, `sheet_frame`, `notes`.

### 3.3 Ölçü satırını bulma — `perceive.py` + `lines.py`

`perceive` ortak ön uçtur: hem **vektör paftada metin katmanı** hem **raster paftada OCR** aynı kapıdan
(`_DimensionGate`) geçer. Vektör paftada bile geometri **görüntüden** ölçülür (metin katmanı yalnız
sayının kendisini ve kutusunu verir):

- `lines.ink` (eşik 0.08 kontrast) → `lines.thin_segments(min_length=36, max_thickness=4, max_length=1400)`
  → `_text_mask` (28 px morfolojik açma eksen kurallarını atar, kalan metindir).
- Kapı sırayla üç yol dener, biri tutarsa **ankrajlar sayıyla birlikte kaydedilir**:
  1. `lines.dimension_for` → bir **ölçü satırı** (iki ucunda ok başı, sayı eksenden ≤30 px, satırın
     üstünde metin oranı ≤0.25): `anchor_mode="dimension"`, çapa = satırın iki kesişimi.
  2. `lines.leader_near` → bir **lider** (uzunluk ≥ 1.5 × metin yüksekliği, kalınlık ≤ 2 × medyan,
     içinden geçtiği mürekkep yazı değil — `PrintedText.through_words`): `anchor_mode="leader"`,
     çapa = **ok ucu ve kuyruğu**.
  3. `leader_to_note` → sayı bir **notanın** (ör. `4 x Ø 6,80 THRU ALL`) içindeyse notanın kendi lideri.
- Hiçbiri tutmazsa sayı **yine de okunur** ve "yerleştirilemedi" olarak *raporlanır* (`pending`), asla
  terfi ettirilmez (review5 V01: değerden türeyen aday, onu seçen ölçeği doğrulayamaz — döngü olur).
- `_is_the_lines_own_ink` + `_is_drawn_solid`: ok başının rakam sanılmasını eler (ölçüm: sahte
  "rakamlar" satır eksenine 0,0–0,5 px ve ucundan 12–14 px uzakta; gerçek sayılar 20,5–21,5 px).
- Ölçek kendini gösterdikten sonra iki onarım: `_repoint_lines_that_are_not_their_own` (yanlış satıra
  düşmüş okumayı kendi satırındaki ölçeğe uyan kesişim çiftine taşır) ve
  `_reread_against_the_sheet_scale` (ölçekle çelişen okuma, tesseract'a başka açıdan tekrar okutulur;
  yalnız modele değil, görüntü okuyucusuna).
- Son süzgeçler: `_inside_drawing_area` (kenar boşluğu %4), `_assign_views`, `_dedupe_spans`.

**Raster pafta** (`raster.py` → `observe_raster`, aynı `Observations` kaydı): Hough ile düz çizgiler,
Hough ile **mürekkebe karşı doğrulanmış** daireler (çevrenin ≥%85'i mürekkep üstünde, iç ≥%75 boş),
zayıf bir Hough geçişiyle yay adayları (kambur ≥4 px, span ≥45°, koşu ≥%75 dolu, kayık halka kapısı),
tesseract ifadeleri + güven değeri. Kayıt kendi sınırlarını yazar: kaynak alt-yol yok (`paths` boş),
yaylar mürekkebe kırpılır, **rasterda ölçek ankrajı yoktur**.

### 3.4 Paftanın kendi ölçeği — `scale.py`

Pafta kendini kalibre eder: her ölçü satırı basılı sayısına çizilmiştir, yani `satır_px / basılı_mm`
= px/mm. `consensus`: her oran bir hipotez olarak denenir, **en çok okumayı tutan** kazanır (medyan
varsaymaz, ayrıca hangi okumaların tuttuğunu söyler); tolerans %4, mutlak taban 2,5 px (1:2 paftada
1,5 mm = 6 px, orada %4 çeyrek pikseldir). Dört durum: `calibrated`, `calibrated_with_suspects`,
`uncalibrated`, `contradictory` (iki+ okuma var ve **hiçbir çift** aynı ölçeği tutmuyor → sayılar
birbirini yalancıyor, katı üretmek en kısa yanlış yol). `view_scales`: ölçüler görünüşe göre ayrı da
fit edilir, kendi ölçeğinde olan görünüş adıyla listelenir (detay görünüşü farklı ölçekte olabilir).
Tanık ölçeği (kapının yerleştiremediği okumalardan kurulan ölçek), yerleşmiş okumaların **çoğunluğu**
doğrulamadıkça paftanın ölçeği sayılmaz (H-R17/H-R18).

### 3.5 Bağlama — `bind.py` (sayı → geometri)

Her ankraj için üç yazım biçimi ayrı ayrı kaydedilir; **hiçbiri kazanan seçilmez**, seçim `meaning`in işi:

- `features`: çapanın **üstüne** oturduğu geometri (daire/yay merkezi, çember üstü iniş, çizgi ucu,
  köşe) — mesafesiyle;
- `strokes`: satır / stub / **kesişen çizgi**; uçları çakışan açık çizgiler en çok 4 adım **zincir**
  olarak yürünür, her iniş noktasının ulaştığı özellikler zinciriyle birlikte yazılır;
- `aligned`: iki çapalı lineer ölçüde, **ölçü ekseni boyunca** hizalanan adaylar + dik uzaklıkları
  (standoff çizimin kuralıdır: kırpılmaz, kaydedilir).

Sabitler (ölçümden seçildi, kayıtta anılır): `ANCHOR_TOLERANCE_PX=3.5`, `FEATURE_TOLERANCE_PX=4.0`,
`AXIS_TOLERANCE_PX=3.0`, `MAX_CHAIN=4`, `MAX_ALIGNED=8`, `ROW_RESIDUAL_LIMIT=0.25`, `ROW_FIT=0.05`.
Durum sözlüğü: `bound | partial | aligned | unbound | no-anchor`.
Satır ölçeğe %25'ten fazla saparsa uçlar yeniden seçilir (`_repick_row_with_calibration`): sırayla
(1) çapanın gördüğü noktalardan basılı uzunluğa en yakın çift, (2) tek çapaya bağlı ve eksene dik
izdüşümü basılı uzunluk olan parça çizgisi, (3) ölçü ekseni **üzerinde** çizilmiş parça çizgisi.
Yeni geometri bulunmaz, tolerans gevşetilmez; seçim kendi notunu taşır (`row_repaired`).
`_diameter_glyph_upgrade`: `observe`in glifle çaplı saydığı ifade `Span.kind`ini `diameter` yapar.
Çıktı: `Bindings` (**version 4**) — `sheet_px_per_mm`, `view_scales`, `spans[]`.

### 3.6 Anlam — `meaning.py` (sayı → iddia)

- `radius` (tür `radius` ya da metin `R...`): çizili yarıçapı basılı değerle (tolerans
  `max(%3, 0.15 mm)`) tutan yay/daireler.
- `diameter` (tür `diameter` ya da `anchor_mode="leader"`): çizili çapı tutan **bütün** daireler
  `matched_geometry`e yazılır (bir çağrı bir küme ölçer); komşu `N x` yazısı (≤260 px) okunup
  `covered` ile karşılaştırılır — tutmuyorsa kayıt bunu gösterir.
- `distance`: iki çapanın adayları arasından, **eksene dik izdüşümü** basılı değeri tutan bütün çiftler.
  Sıra: tür (daire merkezi > yay merkezi > uç/köşe) → maliyet → sapma. Birinci geçiş tutmazsa yedek
  geçiş çapanın **kestiği** çizgilerin uzak uçlarını da hesaba katar (kendi satırını doğrulayan
  `row`/`stub` asla sunulmaz). `row_repaired` ise sıralama **eksene dik** uzaklığa göre yapılır
  (uçlar bilinen bir yerde, uzak iki özellik değil).
- Diğer aday çiftleri `alternatives` olarak durur (≤3). Hiçbiri tutmazsa `resolution="unresolved"`
  ve adaylar `bindings.json`da zaten görünür. `no-value` / `no-scale` ayrı durumlardır.
- Çıktı: `Meanings` — her sayı için `form`, `resolution`, `claim`, `alternatives`, `count`, `covered`.

### 3.7 Plan — `proposal.py` → `general.py`

- `read_sheet` (mm okuma): bileşenler, **kapalı dış kontur**, içindeki daireler, basılı ölçüler ve
  reddetme listesi. Döngü kurma `proposal._loops`: birleşim 3 px (vektör) / 20 px (raster);
  köşe = yay merkezinin doğruya dik izdüşümü; yay ucu kendi mürekkebine kırpılmışsa köşeye oturtulur;
  **sayfa çerçevesi** (%80 kapsama) ve **antet/tablo** (≥3 ifade ve %50'si kelime) atlanır.
- `propose_general`: en büyük kapalı döngü **yuvarlatılmış dikdörtgen** olmalı (değilse reddeder ve
  ölçülerini yazar); tam **iki çap ölçüsü** bekler (delik + cep); delik adedini eşleşen daire sayısıyla
  karşılaştırır; aralık/kontur/kesit ölçülerini sınıflar; her parametre **basılı (span id ile)** ya da
  **türev** olur; her basılı sayı paftanın ölçülmüş geometrisiyle doğrulanır, tutmazsa reddedilir
  (yuvarlanmaz). Yanlış/eksik her durum `refusals` listesine adıyla yazılır.
- `general.py`: sürümlü sözleşme. `Parameter(unit, source, value|expr, span_ids, explanation)` —
  `source ∈ {printed, derived, assumed, user}`; **modelin tahmini bu şemada kaynak değildir**
  (yani depoya yazılınca doğrulanmış ölçü olamaz). `compile_general` planı yalnız `geo.*` çağrıları ve
  sayısal literallerden oluşan kısa bir programa derler; `check_general` açılan STEP'i planın beyan
  ettiği bbox/hacim ve araç kontrolleriyle karşılaştırır. Durumlar: `needs_input`, `draft`,
  `validated`, `unsupported`, `failed`.

### 3.8 Yerel model planlayıcı — `planner.py` (bugün **başarısız**, kayıtlı)

`chain_evidence(read_sheet(...))` modele **yalnız okumanın kendi ölçümlerini** verir: her basılı sayı
span id'siyle, her iddia çapa noktalarıyla, geometri mm cinsinden. Referans STEP, dosya adı veya cevap
asla isteme girmez. Model cevabı şema + atıf kontrolü + derleyici ile yargılanır.
Ölçülen sonuç: model JSON şeklinde bir plan döndürüyor ama **gövdesi bozuk** (geçersiz `value`/`expr`
seçimi, eksik `type` ayırıcıları, uydurma adlar) → **hiçbir model planı derleyiciye ulaşmadı**.

---

## 4. Bu turda yeniden koşulan ölçümler (ham çıktı özetleri)

Plaka paftası: `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`.

| Adım | Komut | Sonuç |
|---|---|---|
| gözlem | `cli observe` | `paths 209`, `primitives 169`, `texts 45`, **0,56 s** |
| bağlama | `cli bind` | `spans 7`, durum: `bound 3`, `aligned 4`, `sheet_px_per_mm 7.82` |
| anlam | `cli meaning` | `spans 7`, form: `distance 5`, `diameter 2`, **7/7 `confirmed`** |
| öneri | `cli propose` | `status proposed`, `readings 9`, `refusals []` |
| üretim | `cli build-general` | `status draft`, denetim `passed: true` (`valid_solid`, `export_round_trip`, `declared_bbox`, `declared_volume`), 4 delik silindiri + 1 cep silindiri |
| bağımsız ölçüm | `.venv-cad eval/metrics.py` | bbox **[15, 80, 120]** ↔ referans aynı, hacim **124.8 cm³ ↔ 124.8 cm³ (%0)**, silindir yarıçapları **[3.4, 10, 25]** iki tarafta birebir |

Okunan yedi sayı (`bindings.json` / `meaning.json`, bu tur):

| span | metin | mod | durum | iddia | nereye |
|---|---|---|---|---|---|
| pdf-0 | `1 00,00` | dimension | aligned | distance, 100,00 ↔ çizili 100,71 | g9/g11 daire merkezleri |
| pdf-1 | `80,00` | dimension | bound | distance, 80,00 ↔ 80,46 | g4/g2 yay çemberi |
| pdf-2 | `60,00` | dimension | aligned | distance, 60,00 ↔ 60,43 | g9/g12 daire merkezleri |
| pdf-3 | `6,80 THRU ALL` | leader | bound | diameter, 6,80 ↔ 6,85, **count 4 = covered 4** | g9,g10,g11,g12 |
| pdf-4 | `50,00` | leader | bound | diameter, 50,00 ↔ 50,36 | g8 |
| pdf-5 | `1 5,00` | dimension | aligned | distance, 15,00 ↔ 15,10 | g52/g57 uçları |
| pdf-6 | `8,00` | dimension | aligned | distance, 8,00 ↔ 8,03 | g56/g48 uçları |

Plana giren parametreler: `hole_dx=100` (pdf-0), `hole_dy=60` (pdf-2), `height=80` (pdf-1),
`thickness=15` (pdf-5), `pocket_depth=8` (pdf-6), `hole_diameter=6.8` + `hole_count=4` (pdf-3),
`pocket_diameter=50` (pdf-4); `width`, `corner_radius`, `area` **türev** ifade; `pi` **varsayım**
(gerekçesi yazılı). Yani "sayı ölçü diye uydurulmuyor" kuralı planda görünür durumda.

---

## 5. Ne ölçüldü, ne ölçülmedi (özet tablo — README/`eval/README.md` ile aynı)

| Yol | Ölçülen |
|---|---|
| Plaka: çizim → STEP | ✅ 124 825,4 mm³ ↔ kapalı form 124 825,4 (**%0,0000**), bbox 120×80×15, 4 delik + 1 cep silindiri (bu turda yeniden doğrulandı) |
| Vektör paftada okuma zinciri | ✅ her basılı sayı bulunup bağlanıyor; paftaya göre 14/17…17/17 iddia çözülüyor, her biri kaynak span id'siyle |
| Raster pafta (PNG/JPG) | ✅ okunuyor, sonra **dürüstçe reddediyor**: ankraj yok → ölçek yok → `pafta ölçeği okunamadı`; gerçek taramada kontur kapanışı hâlâ açık |
| Yerel model planlayıcı | ❌ şemayı tutuyor, gövdeyi bozuyor; hiçbir model planı derleyiciye ulaşmadı |
| Dört sentetik v2 parça | ❌ dördü de STEP üretiyor, dördü de **geometrik olarak yanlış** (bbox uyuşmazlığı, yanlış delik sayısı/çapı) — kayıtlı başarısızlık |
| Arayüz `/guided` | ✅ kalibrasyon, kontur seçimi, delik/cep, taslak STEP + STL önizleme, revizyon/geri alma, URL ile yeniden açma — gerçek tarayıcıda kabul edildi |

**Kapsam:** tek görünüşlü düz parça arketipi (profil ekstrüzyonu, basamak, geçişli/kör delik, bir
dikdörtgen cep) + aynı aile için kullanıcı yönlendirmeli taslak. **Kapsam dışı ve adıyla reddedilen:**
raster ölçek ankrajı, çok görünüşlü pafta, zincir ölçüler, asimetrik yerleşim, dönel parça, GD&T.

---

## 6. Arayüz (`guided.py` + `app.py` + `static/`)

`PYTHONPATH=src .venv/bin/python -m drawingto3d.app` → `http://127.0.0.1:8765/guided`.
Uçlar: `GET /guided`, `/guided.js`, `/preview.js`; `GET /api/job/*`, `/guided-session/*`;
`POST /api/guided/open | save | accept | undo | build`; ayrıca `/api/convert`, `/api/solid`.
Üç veri katmanı ayrı tutulur: **temel geometri** (kaynak özeti, okuyucu sürümü, kararlı kimlikler),
**kararlar** (profil, kalibrasyon, ölçüler/ilişkiler, delik/cep, kontur düzenlemeleri, onaylar),
**hesaplanan sonuç** (karar revizyonu, çözülmüş geometri, denetimler, build durumu, dosya yolları).
Yeni karar eski sonucu **bayat** yapar; eski STEP güncel URL ile sunulmaz.
Oturumlar `out/guided/<token>/session.json`.

---

## 7. Açık işler — bir sonraki agent'ın gündemi

`DEEPSEEK_PROMPT.md` (son devir) sırayı veriyor: **önce X01–X04** (yanlış `accepted`, simüle onay,
deney ölçüm/koşucu açıkları), **sonra X05** (callout/semantik) **ve gerçek ürün kabulü**. Ara raporda
durma; mevcut başarı koşulları, çevrimdışı M1 ve bütçe kapıları korunur. Ayrıntı:
`docs/HERMES_IMPLEMENTATION_PLAN.md`, `docs/HERMES_PROGRESS_REVIEW_7_20260930.md`,
`docs/hermes-task-queue.json`.

PLAN.md §3'teki somut açıklar (F01–F14) hâlâ geçerli sözlüktür; öne çıkanlar:

- F12: kalibrasyonla 100 mm gövde, yalnız merkez mesafesi bağlanınca 50 mm oluyor → **yerel ölçü
  kalibrasyonu değiştirmemeli** (P04-a).
- F13: geçerli X=50/Y=30 köşe bağları tek ölçek kapısına takılıyor → bağımsız kısıtlarla çözüm (P04).
- F14: çekirdek `unsupported` dediği hâlde `make_plan` plan veriyor → istenen ölçü uygulanmıyorsa
  üretim durmalı (P04).
- Raster: ölçek ankrajı (iki tıklama) ve gerçek taramada kontur kapanışı.
- `sketch_constraints.py` çözücüsü yazılmış ama **arayüze/`make_plan`a bağlanmamış** — bilinçli açık.

Aşama durumu (PLAN.md): A0 ✅, P00 ✅, P01 çalışılıyor, P02 ✅ (kalan tek parça: CAD yay uçlarıyla
bağımsız karşılaştırma), P03 çalışılıyor, P04–P12 bekliyor.

---

## 8. Tuzaklar (yeni gelen agent için)

1. **Aynı ağaçta başka bir ajan çalışıyor.** `git status` her turda kontrol edilir; `git reset`/`clean`
   yok; başkasının dosyasında çalışırken önce ölç, sonra sırayla.
2. **Ölçmeden iddia yazma.** Bu projede "başarı" kelimesi yalnız ilgili kabul testi/ürün yolu kanıtıyla
   kullanılır. Yeni bir sayı yazarsan `eval/check_tables.py` ve `eval/baseline_report.py --check`
   yeşil kalmalı (tablolar kayıtlardan türetilir).
3. **`out/` git-ignored**; kalıcı kanıt `eval/reports/`, `eval/audits/` ve yukarıdaki markdown'lar.
4. **Referans STEP yalnız ölçümde**: üretim yolunda, istemde, öneride asla kullanılmaz.
5. **UI kabulü tarayıcıda yapılır**; API probu "UI kabulü" sayılmaz (projede yazılı kural).
6. Raster paftada okuma **kendine ölçek uyduramaz** (`read_sheet`: `hough-arc` ilkeli varsa ölçek
   reddedilir) — bu bilinçli bir kapı, "eksik" değil; ölçek kullanıcının iki tıklamasıdır.
7. Yay/daire sözleşmesi **işaretli süpürme** taşır (`b − a` negatif olabilir = saat yönü); eski
   "0 < b − a < 360" varsayımı stadyum kamburunu içe düşürmüştü (HANDOFF §23-C13/C14).

---

## 9. İlk okunacak dosyalar (sırayla)

1. `README.md` — ne ölçülüyor, ne ölçülmüyor; çalıştırma komutları.
2. `PLAN.md` §1–§4 — hedef, değişmez kurallar, durum tablosu, dosya haritası.
3. `DEEPSEEK_PROMPT.md` + `docs/HERMES_PROGRESS_REVIEW_7_20260930.md` — **sıradaki iş**.
4. `eval/README.md` — ölçüm kavramları ve koşucular; `eval/reports/model-baseline.md` — model sonuçları.
5. Kod: `observe.py` → `perceive.py` (+`lines.py`, `scale.py`) → `bind.py` → `meaning.py` →
   `proposal.py` → `general.py` → `cadrun.py`; arayüz için `guided.py` + `app.py`.
6. `HANDOFF.md` — tarihçe; **başındaki "Güncel devir" bölümü** dışındakiler eski kayıttır.
