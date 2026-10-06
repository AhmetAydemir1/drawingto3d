# drawingto3d — Hermes: kısa uç düzeltmesi → G3 callout review UI

**Hazırlanma:** 2026-10-06\
**İncelenen HEAD:** `ff97295`\
**Ana ürün planı:** [docs/PLAN-20.md](docs/PLAN-20.md)\
**Tamamlanan G2 planı:** [docs/PLAN-21.md](docs/PLAN-21.md)\
**Önerilen sonraki uygulama kapsamı:** G1R3-01 dar düzeltmesi, ardından G3\
**G4+ / model çağrıları / yeni CAD motoru:** Kapsam dışı.

Bu dosya, “yapılanları kontrol et ve plan.md hazırla” isteği üzerine hazırlandı. Bu inceleme ürün kodunu değiştirmedi ve G3'ü uygulamadı. **Kullanıcı bu dosyayı Hermes'e “uygula” diye verdiğinde görev G1R3-01 + G3 olur:** düzeltme kapısı geçince G3'e devam et; iki adım arasında tekrar kapsam onayı isteme. G4'e geçme.

Önceki kök plan baytları korunarak [arşivlendi](docs/PLAN_ROOT_BEFORE_G3_REVIEW_20261006.md); SHA-256 `09e18c8252ca8d3456864ad75e7fe0e15a7c05f9da1f1e75c7167d45b62b4259`. Bu dosya `docs/PLAN-21.md` ile aynı G2 planıdır. Diske göre `plan.md` ve `PLAN.md` aynı dosyaya gider; Git'teki mevcut `PLAN.md` adı korundu.

## 1. Hermes'e başlangıç mesajı

> Kök PLAN.md'yi uygula. Önce G1R3-01'deki yanlış nokta eşitliği toleransını küçük regresyon testleriyle düzelt. Kapı geçince mevcut /guided uygulamasında G3'ü tamamla: callout overlay, seçim, crop, kullanıcı metni, ignore/geri al, manuel alan ve bölge düzeltme. Veri kararları mevcut history/revision/store yolunu kullanmalı. Gerçek tarayıcı kabulünü yap. Parser, target önericisi ve callout→CAD compiler yazma; G4+ kapalı. İş paketleri arasında ilerleme dosyasını güncelle ve aynı işi baştan yapma. G3 kabul tablosuyla teslim et.

**Okuma sırası:** İnceleme sonucu ve çalışma kuralları (§2–3) → dar düzeltme (§4) → G3 sözleşmesi (§5–7) → iş paketleri (§8) → test/teslim (§9–11). Eski 100+ başlıklı G2 planını yeniden uygulama listesine dönüştürme.

## 2. Bağımsız inceleme sonucu

### 2.1 Doğrulanan ilerleme

- `316518e`: önceki iki bulgu düzeltildi. Çıkarılmış kenar hedefi reddediliyor; gerçek stale→current yeniden onayı tam bir `user/confirm_target` olayı yazıyor.
- Eski bağımsız tekrar scripti güncel HEAD'de tekrar çalıştırıldı: iki bulgu da `passed=true`, exit 0.
- `ff97295`: G2 `Observations → CalloutCandidate` adaptörü var; `GuidedStore.create()` aynı observations nesnesini kullanarak adayları ve detection metadata'yı saklıyor.
- G2 adaptörü normalize bölge, kararlı kimlik, exact dedup, provenance, metin ipucu ve açık diagnostics üretiyor. Kullanıcı transcription/parse/target oluşturmuyor.
- Yeni oturum, reopen, eski oturum ve gerçek vektör/raster testleri geçti. İncelenen G2 değişikliğinde ayrıca doğrulanmış yeni bir adapter hatası bulunmadı.
- Henüz callout overlay, transcription paneli, manuel region ve ignore kullanıcı yolu yok. Sıradaki ürün işi G3.

### 2.2 Bu turda gerçekten çalıştırılan testler

| Kontrol | Sonuç |
|---|---|
| `test_callout_candidates`, `test_guided_callout_candidates`, `test_callout_models`, `test_guided_callouts` | **133 passed / 50.05 s / exit 0** |
| Diğer 13 ilgili guided/geometri/UI yapısı test dosyası | **108 passed, 1 failed / 76.58 s / exit 1**; tek failure localhost portuna sandbox izni |
| Aynı HTTP testi izinli localhost ortamında tekrar | **1 passed / 1.29 s / exit 0** |
| Toplam seçili küme | **242 farklı test doğrulandı; üç koşunun birleşimi**, tek koşu diye raporlama |
| Önceki G1R2 bağımsız tekrarları | 2/2 geçti, exit 0 |
| Yeni kısa kenar tekrarı | 5, 10, 20 px farklı uçlar yanlış reddediliyor; 21 px kabul; aynı köşenin alias'ları doğru reddediliyor |
| Bilinen `test_planner.py::test_settings_record_is_the_run_record_fields` | **1 failed / 0.12 s**; testin eski anahtar kümesinde `repeat_penalty` ve `repeat_last_n` yok |

`test_planner` hatası G2 diff'inde değişmeyen test/ayar sözleşmesine aittir; yeni G2 hatası olarak sayılmadı. **Tam test takımı yeşil değildir.** Önceki teslimin `1479 passed, 1 failed` tam koşu raporu tarihsel kanıttır; bu tur 75 dakikalık tüm takım tekrar çalıştırılmadı. Bu planın odak işi dışında kalan test beklentisini sessizce gevşetme veya model ayarlarını kaldırma.

Kanıt klasörü: [eval/audits/20261006-guided-g2-review](eval/audits/20261006-guided-g2-review).

- [focused.log](eval/audits/20261006-guided-g2-review/focused.log)
- [regression.log](eval/audits/20261006-guided-g2-review/regression.log)
- [http-recheck.log](eval/audits/20261006-guided-g2-review/http-recheck.log)
- [previous-findings-recheck.json](eval/audits/20261006-guided-g2-review/previous-findings-recheck.json)
- [Yeni bulgu: probe-results-before.json](eval/audits/20261006-guided-g2-review/probe-results-before.json)
- [Bilinen planner test hatası](eval/audits/20261006-guided-g2-review/known-planner-failure.log)

### 2.3 İncelemede bulunan yeni gerileme

`guided._check_target_geometry()` fiziksel nokta eşitliği için `RASTER_JOIN_TOLERANCE_PX = 20.0` kullanıyor. Bu değer bozuk konturdaki bir açıklığın onarılmasına izin veren mesafedir; iki ayrı ölçü ucunun aynı nokta olduğunu göstermez.

Geçerli bir konturda `(20,20)` ve `(30,20)` uçlarını seçince:

```text
Beklenen: 10 px uzaklıktaki iki farklı uç kabul edilir.
Gerçek: "vertex_pair aynı fiziksel noktayı iki kez seçemez" hatası.
```

Aşağıdaki ilk iş bu dar gerilemeyi kapatır; G2'yi baştan yazmak gerekmez.

## 3. Çalışma kuralları

1. Başlangıç HEAD/worktree durumunu kaydet. `ff97295` sonrasında yeni değişiklik varsa ilgili diff'i oku; bu planın satır numaralarını sabit kabul etme.
2. Geçerli `AGENTS.md` dosyalarını kontrol et. Kullanıcının değişikliklerini, numaralı planları ve `PLAN-17-HERMES.md` dosyasını koru.
3. `docs/GUIDED_PROGRESS.md` içine bu görev için yeni bölüm aç. Eski test ve teslim kayıtlarını silme. G2.6 hâlâ `DEVAM`, current HEAD eski gibi kalmış özetleri gerçek durumla tutarlı hale getir; geçmiş sonuçları yeniden yazma.
4. Bir seferde tek küçük iş: davranışı tanımla → kritik store/geometri davranışı için kırmızı test → dar uygulama → ilgili yeşil test → ilerleme kaydı.
5. Her iş sonunda komut, exit code, sonuç sayıları ve log yolunu yaz. Yeniden başlarken önce ilerleme dosyası ve diff'i oku; biten fazı baştan yapma.
6. Üç başarısız denemeden sonra kör değişiklik yerine küçük tekrar, hipotez ve engeli kaydet. Bağımsız kapsam içi işler sürdürülür; engel başarı sayılmaz.
7. Yeni paralel uygulama, UI framework göçü, CAD motoru, OCR servisi, model çağrısı ve SEMREAD requalification yok. 001D park edilmiş kalır; 001E açılmaz.
8. Testi skip/xfail yaparak veya beklentiyi hataya uydurarak kabul kapısı geçme. Ortam engeli, ürün hatası ve bilinen eski failure ayrı raporlanır.
9. Kaynak çizim dışındaki gold/reference STEP bilgisi producer'a giremez. Dosya adı, case no veya kaynak hash'i ile özel CAD davranışı yazma.
10. Commit gerekiyorsa yalnız ilgili dosyaları açık adlarıyla stage et. Push/merge/deploy bu planın teslim şartı değildir.

## 4. G1R3-01 — Nokta eşitliği ve kontur onarım toleransını ayır

**Öncelik:** P2; küçük ama gerçek ölçüler seçilemiyor.\
**Yer:** `src/drawingto3d/guided.py`, `_check_target_geometry`, `math.dist(points[0], points[1]) <= RASTER_JOIN_TOLERANCE_PX` kontrolü.

### 4.1 Önce tekrar

```sh
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g2-review/review_probes.py
```

Mevcut HEAD'de exit 1. Script yalnız geçici sentetik session kullanır; her konturun `audit_contour(...).ok=true` olduğunu ayrıca doğrular. Test fixture'ı kontur denetiminin çizgi kalınlığı sınırının üstünde tutulmuştur; geçersiz 1 px konturla hata iddia edilmez.

### 4.2 Yapılacak dar düzeltme

- `correct_profile()` için kullanılan 20 px onarım sınırını değiştirme; bu başka bir davranıştır.
- Etkin konturdaki iki ucun fiziksel olarak aynı olup olmadığını küçük geometrik eşitlik toleransıyla denetle. Mevcut `contour_audit.TOLERANCE_PX = 0.5` nokta/kapanma sözleşmesini inceleyerek ortak kullan; 20 px onarım bütçesini kullanma. Farklı tolerans gerekiyorsa anlamını bağımsız gerekçeyle belgeleyip sınır testlerini ekle.
- Etkin kontur, kararlı endpoint ID, `vN` dönüşümü, çıkarılmış kenar reddi ve yeniden onay audit düzeltmeleri korunmalı.
- Sadece bu karşılaştırma için geometri sürümünü/detector sürümünü artırma veya tüm session'ları migrate etme; geometri üretimi değişmiyor.

### 4.3 Kabul testleri

1. Geçerli konturda 5, 10, 20, 21 px aralıklı farklı uçlar kabul edilir.
2. Aynı fiziksel köşenin `edge_a:end` / `edge_b:start` alias'ları reddedilir; kalıcı kayıt değişmez.
3. Seçilen eşitlik toleransının hemen altı/sınırı/üstü küçük saf geometri testiyle pinlenir; geometri üreticinin destek sınırı ile karıştırılmaz.
4. Çıkarılmış kenar yeni onay ve `reconfirm=true` için hâlâ reddedilir.
5. Önceki review scripti geçer; yeni script tüm satırlarda `passed=true`, exit 0 verir.

Kalıcı regresyonları mevcut `tests/test_guided_callouts.py` ve uygun geometri testine ekle. Yeni çıktıyı `probe-results-after.json` gibi ayrı yola yaz; `before` kanıtını ezme.

**Geçiş kapısı:** Bu işin yeni testleri + `test_guided_callouts`, `test_contour_fix`, `test_binding_end_meaning` yeşil olunca G3'e devam et. Kısa düzeltmeden sonra tekrar tüm G2 corpus'unu işlemeye başlama.

## 5. G3'ün somut ürün sonucu ve sınırı

Kullanıcı mevcut `/guided` ekranında şunları yapabilmeli:

```text
Çizimi aç → callout kutularını gör → birini seç → crop'u incele
→ basılı metni yaz veya makine ipucunu bilinçli kullan → kaydet
→ sayfayı yenile / aynı session URL'ini aç → metin duruyor
→ alanı düzelt / yeni alan çiz / callout değil de → undo
```

G3 **metin ve alan incelemesidir**. Bu görevde parser, parse onayı, target önericisi, target seçim UI'sı veya callout→CAD compiler yoktur. `Ø8` yazıldı diye hole/thru/mm/count=1 üretme.

Mevcut eski kalibrasyon/profil/delik/binding/STEP akışları çalışmaya devam eder. Callout metni henüz CAD'e gitmediğinden UI bu metnin STEP'e uygulanmış olduğunu ima etmemeli. Üretim alanında gerektiğinde açık ürün açıklaması göster: **“Kaydedilen callout metinleri bu taslak üretiminde henüz kullanılmıyor.”** G3 için yeni CAD/readiness sistemi kurma; G7/G8'in işi.

## 6. G3 veri sözleşmesi — UI'dan önce

### 6.1 Mevcut verinin yeri korunacak

```text
session.callout_candidates[]      G2'nin temel makine adayları; değişmez
session.callout_detection         G2 metadata/diagnostics; değişmez
session.callout_parses[]          computed; G3 parser üretmez
session.decisions
  transcriptions[]               mevcut G1 kullanıcı kararları
  callout_targets[]              mevcut G1 onayları; UI bu fazda üretmez
  manual_callouts[]               G3 yeni kullanıcı alanları; undo kapsamı
  callout_reviews[]               G3 region override + ignore; undo kapsamı
```

Yeni alanları `Decisions` altında tut. Temel `callout_candidates` listesini kullanıcı alanı eklemek, kutuyu taşımak veya ignore yapmak için değiştirme. `localStorage`ı doğruluk kaynağı yapma; yalnız henüz kaydedilmemiş edit taslağı olabilir.

Gerekli en küçük iki ek model:

| Model | Alanlar ve kural |
|---|---|
| `ManualCalloutDecision` | `id`, `source_digest`, `page_index`, `region`, `revision`; kaynak/page/revision sunucudan; ID bir kez sunucuda atanır ve kalıcıdır |
| `CalloutReviewDecision` | `callout_id`, `region_override` (opsiyonel), `ignored` (default false), `revision`; callout başına tek kayıt |

- Mevcut region doğrulamasını kullan: normalize `[x0,y0,x1,y1]`, sonlu, 0..1, pozitif alan; ilk sürüm page 0.
- `manual_callouts` ve `callout_reviews` bağımsız boş liste default'u alır; eski `Decisions/history` kayıtları yüklenebilir.
- Eksik yeni alan = mevcut değeri koru; açık `[]` = açık kaldırma isteği. G1'in eski istemci korumasını yeni alanlara genişlet.
- Manual ID için `manual:<uuid>` gibi ayrı namespace kullan. UUID yasağı G2 deterministik detector içindi; kullanıcı tarafından yeni alan yaratma ayrı bir olaydır. İstemci başka session'ın ID/kaynak kimliğini kabul ettiremez.
- Manual alan aynı yerde tekrar yaratılırsa ikinci kullanıcı eylemi olarak ayrı ID alabilir. Detected adayla yakınlığına bakarak otomatik merge etme.
- Manuel alanı bu fazda kalıcı silme gerekmiyor; ignore + undo yeterli. UI bir kaldırma sunacaksa history/provenance korumalı ve anlamı açık olmalı.
- G3 persist edilen yapıya yeni alan eklediği için `callout_schema_version`ı bilinçli yönet; yeni/yazılan kayıt için yeni sürüm, eski kayıtta yalnız load yüzünden disk rewrite yok. Geometry/detector sürümleri gereksiz artırılmaz.

### 6.2 Tek etkin callout görünümü

Tek saf helper ile aşağıdakini türet:

```text
G2 base candidates + user manual_callouts + user reviews
→ effective callouts: id, page, source kind, base/effective region,
                     crop region, hint, ignored, provenance
```

- Manual alan public görünümde `source_kind=manual`, boş observation IDs ve `machine_text_hint=null` taşır. Bunu makine tespiti diye loglama.
- Region override orijinal detected region/provenance'ı silmez; yalnız etkin bölgeyi değiştirir.
- Ignored alanın kararı ve tarihsel metni durur. UI'da gizlenebilir ama “Yok sayılanları göster” ile geri bulunur.
- `public()` mevcut `callout_candidates` alanını temel veri olarak korur; G3 için `effective_callouts` ve `callout_detection` metadata'sını ayrıca sunar.
- Store referans doğrulaması, freshness ve UI aynı etkin listeyi kullanır. `_require_callout()` yalnız temel makine listesine bakmaya devam ederse manual transcription reddedilir; bunu entegrasyonda kapat.
- `callout_states` manual callout'ları da kapsar. Effective listeyi üretmek kullanıcı kararı oluşturmaz, history/log/revision yazmaz.

### 6.3 Bölge değişimi metni yeniden onaylanmış yapmaz

`TranscriptionDecision.source_region` kullanıcının metni yazarken incelediği alanın snapshot'ıdır.

| İşlem | Beklenen |
|---|---|
| İlk metin kaydı | Raw text aynen; source_region mevcut etkin bölgeden sunucuda; yeni transcription revision |
| Sadece kutuyu taşı/büyüt | Eski raw text ve eski source_region saklanır; transcription `stale/region_changed`; parse/target varsa stale |
| Yeni bölgeyi inceleyip aynı metni açıkça tekrar kaydet | Yeni source_region + yeni transcription revision; eski parse/target otomatik geçerli olmaz |
| Sadece ignore | Metin silinmez; kullanıcı ignore kararı kaydedilir; build mevcut revision kuralıyla stale |
| Ignore'u geri al | Veri geri görünür; mevcut freshness yeniden hesaplanır, sahte metin/target onayı oluşmaz |
| Undo | Önceki karar snapshot'ı döner; global revision artar; STEP otomatik current olmaz |

Region edit sırasında transcription.source_region'ı yeni kutuya sessizce kopyalama. Bu, kullanıcı yeni alanı okumuş gibi sahte kanıt üretir. İstemcinin gönderdiği yanlış source_region'ı server-side etkin bölgeye göre doğrula/türet.

Ignore kararı UI render state'inden tahmin edilemez. Hâlâ ignored olan callout'a metin girilecekse kullanıcı önce “Geri al” eylemini yapmalı veya UI bu iki işlemi açık tek kullanıcı komutuyla gerçekleştirmeli; gizli unignore yok.

### 6.4 Store/API işlem yolu

Mevcut store kilidi, optimistic revision, atomic save, history, stale build ve log yolunu kullan.

Önerilen tek komut giriş noktası: `GuidedStore.edit_callout(token, revision, action, payload)` ve `/api/guided/callout` dispatch'i. İsim farklı olabilir; ayrı bir kalıcılık/undo motoru kurulamaz.

Komutlar: `add_region`, `edit_region`, `set_ignored`, `transcribe`. Her komut sunucuda etkin source/callout/page'ı doğrular, yeni `Decisions` çalışma kopyasını hazırlar ve mevcut save yoluna verir. `add_region` ID'sini sunucu üretir. UI'nın save entegrasyonu daha basitse aynı kurallar korunarak mevcut `/save` genişletilebilir; manual kimlik/kaynak alanları istemciden körlemesine alınamaz.

Her kullanıcı komutu tek history adımı ve tek global revision değişimidir. Aynı kararın tekrarı no-op olabilir. Başarısız validation/conflict kararları veya dosyayı kısmen yazmamalı. Eski `/accept` callout ipucunu, yeni alanı veya ignore kararını kendiliğinden onaylayamaz.

Log olayları: `user/add_callout_region`, `user/edit_callout_region`, `user/ignore_callout`, `user/restore_callout`, mevcut `user/transcribe` / `user/edit_transcription`; undo mevcut yoluyla. Parser olayı veya otomatik user actor üretme.

## 7. G3 arayüz sözleşmesi

### 7.1 Mevcut ekranı genişlet

Dosyalar:

- `src/drawingto3d/static/guided.html`
- `src/drawingto3d/static/guided.js`
- `src/drawingto3d/app.py`
- `src/drawingto3d/guided.py`, `callout_models.py` ve gerekiyorsa küçük saf yardımcı modül.

Aynı çizim canvas'ı ve sağ panel düzeni kullanılır. Yeni web uygulaması/framework yok. Canvas araçlarına `Callout incele` ve `Yeni alan çiz` ekle. Mevcut profile/calibration/hole/bind modlarıyla çakışmayan tek aktif mod olsun.

Panelin asgari içeriği:

```text
Callout C4                    [İncelenmedi / Metin kaydedildi / Alan değişti / Yok sayıldı]
[crop preview]
Makine ipucu: 4 × Ø8 THRU     [İpucunu metne al]
Basılı metin: [                         ]
[Metni kaydet] [Bu callout değil] [Alanı düzelt]
```

- Crop kaynak drawing image'dan alınır; doğruluk kararı değildir.
- İpucu ayrı ve `öneri` niteliğinde gösterilir. Alan açılır açılmaz kullanıcı metnine/persisted transcription'a dönüşmez.
- “İpucunu metne al” yalnız edit taslağını doldurur; “Metni kaydet” gerçek kullanıcı kararıdır.
- Bu fazda “Kaydet ve ayrıştır”, “Parsed”, “Bound” gibi çalışmayan başarı eylemleri gösterme. “Metin kaydedildi” yeterlidir.
- Callout sayısı, incelenmiş/ignored sayısı ve boş aday halinde “Yeni alan çiz” yolu görünür olsun. Metinsiz raster normal bir sonuçtur; sahte kutu çizilmez.
- Listeden seçim fallback'i olsun. Örtüşen kutularda kararlı hit-test uygula: en küçük kapsayan kutu, eşitlikte ID; diğer kutuya listeden ulaşılabilir.
- Metni `textContent` / textarea.value ile göster; kullanıcı/hint içeriğini HTML olarak çalıştırma.

### 7.2 Koordinat dönüşümü tek yerde olsun

Mevcut canvas'ta `scale()` görüntüyü sığdırıyor; CSS boyutu canvas piksel boyutundan farklı olabilir. Sadece event.clientX'i image pikseli sayma.

```text
client pointer
→ getBoundingClientRect + canvas backing dimensions
→ image draw offset/scale
→ source image pixel
→ normalize page region
```

Çizme, hit-test, sürükleme ve crop aynı dönüşüm yardımcılarını kullanmalı. Sayfa 0 görüntüsü için `picture.width/height` ile source frame boyutlarının aynı anlamda olduğunu kontrol et. Image yüklenmeden seçim/kayıt yapma.

- Farklı pencere genişliği ve responsive tek kolon görünümünde kutular aynı kaynak alanında kalmalı.
- Drag yönünden bağımsız `min/max` ile region kur; server ters/sıfır/taşmış alanı reddeder.
- Canvas dışına taşan pointer veya görüntü dışı boş alanı callout sayma. Pointer capture + cancel/Escape ile yarım drag iptal edilebilmeli; iptal kayıt oluşturmaz.
- UI kenarda crop padding'i kırpabilir; base/effective region sırf crop için değiştirilemez.
- Pointer drag'ından sonra oluşan click yanlışlıkla profile/hole seçmemeli. Click ve drag modlarını tek dispatcher'da açık ayır.

### 7.3 Metin taslağı ve hata davranışı

- Mevcut `busy()` yalnız button/input/select kapsıyor; textarea ve yeni araçlar için pending davranışını da düzenle.
- Kullanıcının henüz kaydetmediği metni hover, seçim/render veya başarısız save yüzünden kaybetme.
- Session revision conflict'te sessiz last-write-wins yok. Hata açık görünür; kullanıcının typed draft'ı korunur; güncel state alındıktan sonra yeniden bilinçli kaydedilebilir.
- Refresh/reopen için garanti verilen veri server'a başarıyla kaydedilmiş karardır; unsaved taslağı kaydedilmiş gibi gösterme.
- Ignore, restore, region edit ve manual add tam bir undo adımı olmalı. Selected callout undo sonrası yoksa seçim güvenle temizlenir; hayalet panel kalmaz.

## 8. G3 küçük iş paketleri ve sırayla geçilecek kapılar

### G3.0 — Başlangıç ve durum kaydı

Dar düzeltme testleri geçtiğinde G3'ü aç. Bu planın sürümünü yeni history entry olarak izlemek istersen boş numarayı kullan (bu incelemede `docs/PLAN-22.md` yoktu); mevcut planı ezme. `report.md` güncel ürün pointer'ını ve `GUIDED_PROGRESS` iş tablosunu tutarlı güncelle. Araştırma geçmişi değişmez.

### G3.1 — Kullanıcı region/ignore sözleşmesi

§6 modelleri, default'lar, effective callout helper ve kaynak/ID ilişkilerini ekle. Synthetic store testleriyle detected base değişmezliği, manual kimlik, region override ve ignored restore davranışını kanıtla. Bu adımda UI çizme.

**Kapı:** Manual alan + detected override + ignore kararları round-trip ve history içinde; temel adaylar bayt/değer olarak aynı; bilinmeyen source/callout reddi.

### G3.2 — Store ve HTTP; eski session uyumu

Komut/save yolu, API dispatch, public effective state, transcription region freshness ve log'u bağla. Eski istemcinin eksik yeni alanlarının veriyi silmediğini, eski history'ye undo'nun çalıştığını doğrula. G2 adaptörü load/save/undo sırasında tekrar çalışmamalı.

**Kapı:** Gerçek HTTP revision conflict/invalid command testleri ve gerçek store reopen/undo; manual callout transcription için `_require_callout` sorunu yok; source_region değişimi testleri geçiyor.

### G3.3 — Overlay, seçim ve crop

Canvas araçları, kutular, display label, liste seçimi, crop ve durum görünümü ekle. ID olarak `C1` kullanma; label yeniden sıralanabilir, gerçek ID değişmez. Sadece seçim veya crop üretimi mutation değildir.

**Kapı:** Vektör ve raster görüntüde overlay/crop aynı alanı gösterir; responsive görünümde seçim kaymıyor; mevcut profile/calibration/hole/bind click modları korunuyor.

### G3.4 — Transcription ve ignore

Metin alanı, açık hint kopyalama, kaydet, ignore/restore ve dirty draft davranışını ekle. G1 normalize/raw ayrımı kullanılır; frontend raw metni trim edip değiştirme. Kalıcı kayıtta server revision ve source_region doğrulanır.

**Kapı:** Gerçek tarayıcı click→type→save→refresh→aynı session URL→undo; raw text aynen, ignore geri alınabilir. Hata/conflict draft'ı kaybetmiyor.

### G3.5 — Manuel alan ve bölge düzenleme

Add/edit drag, cancel, aynı callout ID'sinde region override ve eski metnin `region_changed` durumu. Manual add→text save→edit→undo→reopen zincirini kur. Base detection tekrar koşulmaz; model/parse çalışmaz.

**Kapı:** Metinsiz raster/boş adayda manuel yol çalışır; edit yeni kullanıcı kararıdır; eski source_region sessiz güncellenmez; manual ID refresh/undo boyunca kararlı.

### G3.6 — Birleşik kabul ve teslim

Kalıcı testler + gerçek browser senaryoları + önceki iki bağımsız review scripti. Yeni parse/CAD başarısı iddiası yok. G3 bittiğinde dur; G4 ayrı görevdir.

## 9. Zorunlu G3 davranış matrisi

| ID | Senaryo | Beklenen |
|---|---|---|
| U01 | G2 detected aday aç | Kutu/list/crop var; açmak kullanıcı kararı üretmez |
| U02 | Hint var, user input yok | Transcription boş; ipucu ayrı; otomatik accept yok |
| U03 | `"  4 × Ø8 THRU  "` kaydet ve reopen | Raw aynen; normalized ayrı; source_region doğru |
| U04 | Boş/whitespace metni kaydet | Açık ret; geçmiş/karar değişmez |
| U05 | Manual region ekle→metin kaydet→reopen | Aynı manual ID; source/page sunucuya ait; karar kalıcı |
| U06 | Detected region'ı düzenle | Base candidate aynı; effective region yeni; eski metin stale |
| U07 | Yeni region'da aynı metni açıkça kaydet | Yeni transcription revision/source_region; eski parse/target stale |
| U08 | Ignore→refresh→restore→undo | Metin/provenance silinmez; her mutation doğru tek history adımı |
| U09 | Add/edit/ignore/transcribe→undo→yeni store instance | Önceki kararlar; global revision artar; STEP current dirilmez |
| U10 | Eski session/history/istemci save | Yeni alanlar default/preserve; load dosyayı yeniden yazmaz |
| U11 | Stale revision ile API komutu | Açık conflict; ilk kayıt değişmez; UI draft korunur |
| U12 | Başka session ID/source digest veya bilinmeyen callout | Ret; sahte candidate/transcription yazılmaz |
| U13 | Ters drag, iptal, sıfır kutu, dış alan | Normalize doğru veya açık ret; iptal mutation değil |
| U14 | Normal/geniş ve dar pencere görünümü | Kutu, hit-test ve crop aynı kaynak bölgede |
| U15 | Overlay açıkken mevcut calibration/profile/hole/bind/undo | Önceki görevler çalışır; event çakışması yok |
| U16 | Input `<img src=x onerror=...>` gibi metin | Metin olarak görünür; script çalışmaz |
| U17 | Manuel alan ve reviews mevcutken eski `/accept` | Yeni kullanıcı kararları korunur; otomatik callout onayı yok |
| U18 | save/load/undo/public tekrarları | G2 adaptörü/OCR/model yeniden çağrılmaz; base adaylar aynı |
| U19 | Source eksik/değişmiş session | Kararlar/alanlar korunur; stale görünür; yanlış current output yok |
| U20 | Metin girilmişken eski STEP üretim bölümü | Callout metni CAD'e uygulandı iddiası yok; taslak sınırı açık |

Fixture parse/target kullanımı U06/U07 invalidation testlerinde mümkündür; gerçek parser geliştirmek değildir. Beklenen davranışı testte bağımsız kur; ürün helper'ının çıktısını tekrar aynı helper'la hesaplayarak test yazma.

## 10. Test ve browser kabul yöntemi

### 10.1 Kalıcı testler

Önerilen yeni dosya: `tests/test_guided_callout_review.py` (models/store/API). İsim başka seçilirse ilerleme ve komutları gerçek dosya adıyla güncelle. Mevcut `tests/test_guided_html.py` yapısal kontrolleri genişleyebilir; bu dosya gerçek browser testi yerine geçmez.

G1R3 sonrası hızlı küme:

```sh
.venv/bin/python -m pytest -q tests/test_guided_callouts.py tests/test_callout_models.py tests/test_contour_fix.py tests/test_binding_end_meaning.py
```

G3 son birleşik küme (yeni test dosyası gerçekten oluşturulduktan sonra):

```sh
.venv/bin/python -m pytest -q tests/test_guided_callout_review.py tests/test_callout_candidates.py tests/test_guided_callout_candidates.py tests/test_callout_models.py tests/test_guided_callouts.py tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py tests/test_view_decision.py tests/test_view_core.py tests/test_sheet_frame.py tests/test_stable_identities.py tests/test_contour_fix.py tests/test_measure_meaning.py tests/test_user_dimensions.py
```

Mevcut test sayısını 242'ye zorla sabitleme; yeni testlerle artar. Doğru testleri yeni API düzenine uyarlarken eski korumaları kaldırma. Değişiklik/başarısızlık yoksa aynı pahalı suite'i tekrar tekrar koşma. Bilinen planner failure'ını ayrı açık olarak koru; tüm takım yeşil demezsin. Full suite yalnız kapsam değişimi veya yeni geniş etki bunu gerektirirse çalıştırılır.

### 10.2 Gerçek tarayıcı

Mevcut uygulama başlatma yolu:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d.app
```

Varsayılan `/guided` yerel adresini uygulama çıktısından doğrula. Zaten çalışan servis varsa önce kullandığın kod sürümünü doğrula; başka kullanıcının sürecini körlemesine öldürme.

Mevcut browser/Playwright/automation imkânını kullan. G3 için en az şu gerçek etkileşimler gerekir:

1. Gerçek vektör Plate dosyasını aç → kutu seç → crop → metin yaz → kaydet → refresh/reopen → raw kontrol → undo.
2. Bir detected alanı ignore et → ignored listeden geri getir; kalıcılığı kontrol et.
3. Metinsiz raster veya açıklamalı boş aday oturumunda manual alan çiz → metin kaydet → crop'u kontrol et.
4. Metinli callout'un region'ını taşı → eski metnin yeniden inceleme uyarısı → açık kaydet → undo/reopen.
5. Geniş ve dar pencere görünümünde aynı kutuyu seç; crop/hit-test kaymıyor.
6. API revision conflict oluştur; UI hata verirken yazılan draft korunur.
7. Mevcut calibration/profile/hole/bind ve undo araçlarından smoke akışları; console error yok.

Mümkün olduğunda açık kaynak çizimle 1–2 screenshot ve browser adım kaydı sakla. API'ye doğrudan veri gönderip browser click/type olmuş gibi raporlama. Browser aracı yoksa API/model testlerini bitir, eksik tarayıcı kabulünü `BLOCKED_BROWSER/NOT_RUN` yaz; **G3 tamam** deme. Fixture parse veya scripted input, gerçek kullanıcıdan alınmış karar diye raporlanmaz.

### 10.3 Son denetim

```sh
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g2-review/review_probes.py
git diff --check
git diff --stat
git status --short
```

HTTP testi yalnız sandbox port engeline takılırsa izinli localhost ortamında tek testi tekrar doğrula; skip ederek başarı yazma. Yeni kodu veya test beklentisini port izni hatası yüzünden değiştirme. Logdaki gerçek exit code'u koru.

## 11. Definition of Done ve teslim

- [ ] G1R3-01 geçiyor; kısa fakat farklı ölçü uçları seçilebiliyor; aynı köşe reddediliyor.
- [ ] G2 detector/ID/provenance/base candidate davranışları korunuyor.
- [ ] Kutular/list/crop ve responsive koordinat dönüşümü gerçek browser'da doğrulandı.
- [ ] Kullanıcı metni aynen kalıcı; hint yalnız açık eylemle taslağa, save ile karara geçiyor.
- [ ] Manual region / region edit / ignore / restore / undo / reopen çalışıyor.
- [ ] Alan değişimi eski transcription snapshot'ını sahte biçimde güncellemiyor; stale zinciri açık.
- [ ] Eski session/history/istemci yeni kararları kaybetmiyor.
- [ ] Yanlış kaynak, stale revision ve geçersiz region kalıcı kaydı bozmuyor.
- [ ] Mevcut guided araçları ve artifact stale davranışı korunuyor.
- [ ] Parser, target önericisi veya callout→CAD uygulanmış gibi UI/audit iddiası yok.
- [ ] Test, browser kanıtı ve bilinen açıkların güncel kaydı var.
- [ ] G4+ uygulanmadı.

İlerleme tablosu en az `G1R3-01`, `G3.0` … `G3.6` satırlarını içerir. Her satırda `TODO/IN_PROGRESS/PASS/FAIL/BLOCKED_*`, kanıt yolu ve kalan tek iş bulunur.

Teslim:

```text
HEAD / worktree:
G1R3-01 önce/sonra ve kanıt:
G3.0–G3.6 durumları:
Kalıcı kullanıcı akışları:
Gerçek pytest komutları, sonuçları ve exit code:
Gerçek browser senaryoları ve kanıt:
Değişen dosyalar:
Bilinen eski planner failure / diğer açıklar:
Model çağrısı: 0
G4+ durumu: açılmadı
```

**Şimdi uygulanacak sıra: G1R3-01 → G3.0 → G3.1 → G3.2 → G3.3 → G3.4 → G3.5 → G3.6 → teslim.**
