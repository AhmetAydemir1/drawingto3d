# drawingto3d — proje devam kaydı

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

- Okuma katmanı genelleştirmesi (PLAN.md Bölüm 3A/3B): çizimden gelen gözlem/ölçü ankrajları
  genel plan önerisine bağlanmadı. Genel plan bugün dosyadan/elle veriliyor; yalnız plaka yolu
  otomatik doluyor (`from_plate`). Bu, sıradaki ana iş.
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
2. Sıradaki iş `PLAN.md`'ye göre: okuma katmanı (Bölüm 3) ya da CLI/arayüzün genel plana
   bağlanması. `git status` ile bu oturumun commit edilmemiş değişikliklerini koru.
3. Pilot/saklı veri gelmeden genelleme iddiası yazma; değerlendirme sonucunu uydurma.

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

Kaynak: `examples/pdf with steps/Plate With A Pocket Drawing.PDF`
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
PYTHONPATH=src .venv/bin/python -m drawingto3d plan "examples/pdf with steps/Plate With A Pocket Drawing.PDF" out/plate-plan
PYTHONPATH=src .venv/bin/python -m drawingto3d build-plan "examples/pdf with steps/Plate With A Pocket Drawing.PDF" out/plate-plan/plan.json out/plate-plan
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
