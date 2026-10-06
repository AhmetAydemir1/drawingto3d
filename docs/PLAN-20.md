# PLAN.md — drawingto3d / GUIDED-TRANSCRIPTION (aktif plan)
## Hermes için uygulanabilir guided transcription planı — ilk kapsam: G0 + G1

**Hazırlanma:** 2026-10-06 (bu repo kopyası: `docs/PLAN-20.md`, yeni history entry)  
**Hedef yürütücü:** Hermes / DeepSeek V4.1 Flash  
**Kaynak belge:** Kullanıcının verdiği `Downloads/PLAN-17.md` (Hermes uyarlaması: repo kökünde `PLAN-17-HERMES.md`, untracked)  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Hazırlanırken doğrulanan HEAD:** `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
**İlk uygulama kapsamı:** Yalnız **G0 + G1**  
**Ürün hedefi:** Kullanıcı tarafından doğrulanan çizim bilgileriyle 10/10 geometrik olarak doğru STEP.  
**İzleme:** `docs/GUIDED_PROGRESS.md` — iş kalemleri, komutlar, exit code'lar ve kanıt yolları orada tutulur.

Bu dosya **izlenen aktif plandır** (G0 kaydıyla repo authority yapıldı); uygulama bu planla başladı. Önceki planlar (`docs/PLAN-19.md`, `PLAN-18.md`, …) **korunur ve değiştirilmez**; bu dosya pivotun kendi history entry'sidir.

Kaynak belge adı ile repodaki `docs/PLAN-17.md` aynı belge değildir. Mevcut plan geçmişini dosya adlarına bakarak değiştirme.

## 1. Hermes'e verilecek başlangıç mesajı

Kullanıcı aşağıdaki mesajı bu dosyayla birlikte verebilir:

> Ekteki planı uygula. Bu oturumun kapsamı yalnız G0 ve G1. Önce bölüm 2–8'i oku; sonra bölüm 9'daki küçük işleri sırayla tamamla. Her işin kabul koşulunu gerçek test çıktısıyla doğrula. Kaldığın yeri `docs/GUIDED_PROGRESS.md` dosyasına yaz. G1'in bütün kapıları geçmeden sonraki faza geçme. G1 geçince de bu görevi teslim et; G2 ve sonrası ayrı görev kapsamıdır. Kullanıcı kararını, parser sonucunu ve model önerisini birbirine karıştırma. Eski araştırma çağrılarını başlatma. Çalışan kodu yeniden yazmak yerine mevcut store, revision, undo ve CAD yolunu genişlet.

**Okuma haritası:** İlk görevde bölüm 2–10 ve bölüm 13'ün G1 kontrol listesi yeterlidir. Bölüm 11–12 ve 14 sonraki görevler içindir; hepsini aynı anda uygulama listene alma. Yeni oturumda önce ilerleme dosyasını, sonra yalnız sıradaki işin sözleşmesini ve testlerini yeniden oku.

## 2. Önce hedefi ve görev sınırını sabitle

### 2.1 Ürün kararı

Otomatik çizim okuma ürünün kritik yolundan çıkarılıyor. Yeni akış:

```text
Çizim → callout alanları → kullanıcı metni yazar/doğrular
      → deterministik parser → kullanıcı parse önizlemesini onaylar
      → sistem geometri hedefi önerir → kullanıcı hedefi onaylar
      → eksik fiziksel anlam/birim/eksen kararları tamamlanır
      → mevcut guided kararları → GeneralPlan → CAD → STEP
      → STEP yeniden açılır → bağımsız geometri kontrolü
```

**Callout:** Çizimde ölçü veya özellik bilgisi taşıyan metin alanı; örneğin `4x Ø8 THRU`.

### 2.2 Bu görevde ne bitecek?

- **G0:** Yeni plan izlenecek, aktif ürün yönü raporda değişecek, eski araştırma park edilecek.
- **G1:** Dört temel veri modeli, kalıcı kayıt, revision, undo, eski oturum uyumu ve stale kontrolleri testlerle tamamlanacak.
- **G2–G13:** Bu dosyada gelecek işler olarak tanımlıdır. Bu görevde uygulanmayacak.

G1'in bitmesi, callout arayüzünün veya yeni yoldan STEP üretiminin hazır olduğu anlamına gelmez.

Uzun süre çalışabilmen kapsamı genişletme yetkisi değildir. Süreyi G0/G1'i sağlam tamamlamak, hataları gidermek ve kanıtları toplamak için kullan.

### 2.3 Araştırma durumu

Korunacak tarihsel sonuç:

```text
SEMREAD-001D Round 1 = FAIL
formal = 0/4
dev budget used = 4/12
context/truncation = bu başarısızlığın blocker'ı değil
current research status = PARKED RESEARCH — Round 1 FAIL
```

Yeni 001D requalification çağrısı yapma. 001E açma. VLM prompt tuning, model değişimi veya yeni OCR/VLM servisi kurulumu yapma. Eski planları, attempts, raw responses, dev-report, preflight ve input identities kayıtlarını koru.

## 3. Çalışma yöntemin: tek iş, açık test, kalıcı kayıt

Her küçük işte şu döngüyü uygula:

1. İlgili dosyayı ve en yakın mevcut testleri oku.
2. `docs/GUIDED_PROGRESS.md` içine mevcut iş ID'sini ve beklenen davranışı yaz.
3. Veri kaybı, geçersiz karar veya stale davranışı değişiyorsa bunu yakalayan küçük bir davranış testi ekle.
4. Testi çalıştır. Düzeltme öncesinde beklenen nedenle başarısız olduğunu doğrula; import hatasını davranış kanıtı sayma.
5. En küçük gerekli kod değişikliğini yap.
6. Önce o testi, sonra işin ilgili regresyon kümesini çalıştır.
7. Diff'i oku. Alakasız değişiklikleri kendi değişikliklerinden çıkar; başkasının değişikliklerini geri alma.
8. Test komutu, exit code, geçti/kaldı/atlandı sayısı ve kanıt yolunu kaydet.
9. Kabul kapısı geçtiyse sıradaki **yetkili** işe geç. Geçmediyse mevcut işi onar.

Doküman değişiklikleri için göstermelik test yazma. Kalıcılık ve invalidation gibi veri güvenilirliğini etkileyen davranışları test et.

### 3.1 Uzun çalışma ve tekrar başlama

- Aynı anda tek iş `IN_PROGRESS` olsun.
- Her küçük işten sonra ve bağlamı kaybetmeden önce ilerleme dosyasını güncelle.
- Yeniden başlayınca önce ilerleme dosyasını, `git status --short` çıktısını ve son diff'i oku.
- Tamamlanmış işi sırf konuşma geçmişi yok diye baştan yazma.
- Önceki testi yalnız ilgili kod değişmişse, çıktı belirsizse veya test yarım kaldıysa tekrarla.
- Hâlâ çalışan bir test süreci varsa ikinci kopyasını başlatma; mevcut sürecin sonucunu al.
- Uzun testte son tamamlanan test veya log değişimiyle ilerlemeyi takip et. Sessiz kaldı diye başarısız sayma.
- Kesilen koşuyu `INTERRUPTED`, çalışmayan testi `NOT_RUN`, araç eksikliğini `BLOCKED_ENV` yaz. Bunlar `PASS` değildir.

### 3.2 Hata çözme kuralı

Bir başarısızlıkta sırayla şunları yaz:

```text
İş ID:
Tekrar komutu:
Beklenen:
Gerçekleşen:
Hata sınıfı: kod / fixture / ortam / kapsam kararı
Tek hipotez:
Bu hipotezi ayıran kontrol:
Kontrolün sonucu:
```

Üç farklı denemede aynı engelde kalırsan dördüncü kör değişikliği yapma. Küçük tekrar örneği ve denenen çözümleri kaydet. Bağımsız ve kapsam içindeki işleri sürdür; bağımlı işleri başarılı gösterme. Kullanıcı girdisi gerekiyorsa tek somut soruyla eksik bilgiyi iste.

Eksik paket, izin veya kullanıcı tarafından okunması gereken çizim bilgisi yerine sahte sonuç üretme. Projede mevcut kurulum yolunu kullan; ilgisiz paketleri/model servislerini kurma.

### 3.3 İlerleme dosyası şablonu

```markdown
# Guided progress
Scope: G0 + G1
Active plan: docs/PLAN-20.md
Initial HEAD: ...
Current HEAD: ...
Initial worktree changes: ...
Current task: G1.3

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G0 | TODO | — | — |
| G1.1 | TODO | — | — |

## Son doğrulama
- Kod sürümü: HEAD + uncommitted diff bilgisi
- Komut:
- Exit code:
- Passed / failed / skipped:
- Log yolu:

## Kararlar / engeller
- ...

## Yeniden başlarken ilk somut işlem
- ...
```

Durumlar: `TODO`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED_ENV`, `BLOCKED_INPUT`, `NOT_RUN`, `INTERRUPTED`. G0'ın geçmesi için kod testi gerekmez; diff kontrolünü kanıt olarak yaz.

## 4. Değişmez kurallar

1. **Yeni web uygulaması veya CAD motoru kurma.** Mevcut `/guided` ve `GeneralPlan/build-general` yolunu kullan.
2. **Base reading ≠ user decision ≠ computed result.** Üç katmanı aynı alana yazma.
3. **Proposal ≠ confirmation.** Aday metin, parse sonucu veya en yüksek puanlı hedef kendiliğinden kullanıcı onayı olamaz.
4. **Eksik bilgi bilinmiyor olarak kalır.** `Ø8` tek başına hole, thru, count=1 veya mm demek değildir.
5. **Referans STEP producer girdisi olamaz.** Referans, gold veya evaluator çıktısından metin, hedef, profil, ölçü ya da kod dalı üretme.
6. **Örneğe özel davranış ekleme.** Dosya adı, case numarası, bilinen koordinat veya kaynak hash'i üzerinden farklı çözüm seçme. Hash yalnız kimlik ve provenance içindir.
7. **Eski oturumları ve tarihsel çıktıları koru.** `git reset`, `git clean`, toplu silme veya yedeksiz migration yapma.
8. **Testi hatalı davranışa uydurma.** Skip/xfail veya beklenti zayıflatma ile kapı geçirme. Gerçekten yanlış fixture varsa bağımsız gerekçesini kaydet.
9. **Her başarı iddiasının çıktısı bulunmalı.** Dosya yazılması, HTTP 200 veya STEP reopen tek başına geometrik doğruluk değildir.
10. **Kullanıcının mevcut değişikliklerini koru.** Commit gerekiyorsa yalnız kendi işine ait dosyaları stage et; `git add .` kullanma. Push/merge/deploy bu planın teslim şartı değildir.

## 5. Başlangıç incelemesi: gerçek kodu doğrula

Aşağıdaki harita hazırlık sırasında gerçek repodan kontrol edilmiştir. Çalışmaya başladığında HEAD farklıysa dosyaları tekrar kontrol et; bu belgeyi eski koda zorla uygulama. HEAD farkı tek başına durma sebebi değildir.

| Yer | İlgili sorumluluk |
|---|---|
| `src/drawingto3d/guided.py` | `Decisions`, `GuidedStore`, revision, undo, migration, public state, artifact ve CAD geçişi |
| `src/drawingto3d/app.py` | Mevcut guided HTTP API; save/accept/undo/build store'a gider |
| `src/drawingto3d/static/guided.html` | Mevcut guided arayüz |
| `src/drawingto3d/static/guided.js` | Karar kaydı, geometri seçimi, öneriler, canvas |
| `src/drawingto3d/observe.py` | Vektör/raster gözlemleri ve kaynak alanları |
| `src/drawingto3d/bind.py` | Geometriye bağlama kanıtları; ikinci kopyasını yazma |
| `src/drawingto3d/general.py` | Mevcut GeneralPlan ve build yolu |
| `tests/test_guided.py` | Store, revision conflict, undo, build, artifact, HTTP testleri |
| `tests/test_guided_geometry_state.py` | Temel geometrinin değişmezliği ve undo/reopen |
| `tests/test_guided_geometry_migration.py` | Eski oturum, yedek ve kimlik uyuşmazlığı |
| `tests/test_guided_proposals.py` | Öneri/onay/log sınırları |
| `tests/test_binding_end_meaning.py` | Mevcut measurement binding uç anlamı |
| `tests/test_guided_html.py` | Arayüz yapısı regresyonu |

### 5.1 İlk komutlar

Komutları **repo kökünde** çalıştır. Yerel `/Users/...` yolunu taşınabilir uygulama koduna yazma.

```sh
git status --short
git rev-parse HEAD
rg --files --hidden -g AGENTS.md -g '!.git' -g '!node_modules'
cat pyproject.toml
rg -n '^class |^def |^    def ' src/drawingto3d/guided.py
```

Üst dizinlerde ve değiştireceğin alt dizinlerde geçerli `AGENTS.md` varsa oku. Yorum veya eski plan içindeki geçmiş görevleri otomatik olarak yeni görev sayma.

Mevcut ortam Python `>=3.12,<3.13`, Pydantic 2 ve pytest kullanıyor. `.venv/bin/python` hazırlık sırasında vardı. Başka makinede mevcut değilse repo kurulum talimatını izle; komut çalışmış gibi raporlama.

### 5.2 Mevcut kodda dikkat edilecek somut noktalar

- `GuidedStore.save()` undo için `history` içine **decisions** kaydediyor. Başka alandaki kullanıcı kararları kendiliğinden geri alınmaz.
- `Decisions` bilinmeyen alanları reddediyor (`extra="forbid"`). Yeni alanları sözleşmeye ekle; kontrolü gevşetme.
- Save ve undo global `revision` artırıyor, `build` alanını geçersizleştiriyor. Bu davranışı yeniden icat etme.
- `load()` kaynak hash'i ve geometri migration kurallarını kontrol ediyor. Yeni şema geçişini bununla çakıştırma.
- `public()` ve `artifact()` eski STEP'in güncel olarak sunulmasını engelliyor. Yeni kararlar bu kapıya katılmalı.
- `geometry_version` mevcut kodda geometri sözleşmesinin sürümüdür. Aynı sürüm içinde profil/kontur değişebilir. **Tek başına geometry_version karşılaştırması hedef geçerliliği için yeterli değildir.**
- Build tamamlanırken arada yeni karar kaydedilmiş olabilir. `build=None` dahil yeni durumlarda eski build sonucu ne güncel hale gelmeli ne de tamamlanma yolu çökmelidir.

Bu maddeleri okumadan G1'e başlama.

## 6. G1 veri sözleşmesi: açık yerleşim ve sınırlar

### 6.1 Yerleşim kararı

G1'de şu yerleşimi kullan. Aynı işi yapan mevcut alan varsa küçük bir uyarlamayla onu kullan ve eşlemeyi ilerleme dosyasına yaz.

```text
session
  callout_schema_version         yeni katmanın sürümü; geometri sürümü değildir
  callout_candidates[]           sistemin bulduğu temel adaylar
  callout_parses[]               deterministik hesaplama; kullanıcı kararı değildir
  decisions
    ...mevcut alanlar...
    transcriptions[]             TranscriptionDecision; undo kapsamındadır
    callout_targets[]            CalloutTargetDecision; undo kapsamındadır
  history[]                     mevcut kullanıcı kararı geçmişi
  log[]                         mevcut olay günlüğü
  revision                      oturumun global revision'ı
  build                         yalnız güncel kimliğe ait çıktı
```

- Yeni listelerin varsayılanı bağımsız boş liste olmalı (`default_factory=list`).
- `reading`, `options`, `proposals` içine kullanıcının yazdığı metni veya hedef onayını gömme.
- Parser çıktısını `decisions` içine onaylı kullanıcı verisi gibi koyma.
- G1'de bu dört modeli tercihen `src/drawingto3d/callout_models.py` içinde tanımla; store entegrasyonu `guided.py` içinde kalsın. Model modülü `guided.py` import etmesin; döngüsel import oluşturma.
- G1'de gerçek detector/parser/target ranker yazma. Bunlar G2/G4/G5 işleridir.
- G3'te manuel alan ekleme/düzeltme, ignore ve required/optional kararları da **decisions içinde** temsil edilecek. Temel candidate kaydını doğrudan değiştirerek undo dışına çıkarma.
- G4'te parse onayı; G7'de birim ve fiziksel özellik kararları açık kullanıcı kararlarıyla eklenecek. Bunları G1'de uydurma varsayımlarla doldurma.

### 6.2 Koordinat sözleşmesi

Callout bölgeleri `Region = [x0, y0, x1, y1]` olsun:

```text
source sayfasının 0..1 normalize koordinatları
başlangıç: sol üst; x sağa, y aşağı
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
page_index: sıfır tabanlı
```

Tüm değerler sonlu olmalı. NaN/Infinity, ters kutu ve sıfır alan reddedilir. Gözlem katmanındaki piksel `BBox(x,y,w,h)` ile bunu karıştırma. G2'de tek açık dönüşüm fonksiyonu kullan; örnek: 1000×500 sayfada `[100,50,300,150]` piksel kutusu → `[0.1,0.1,0.3,0.3]`.

`crop_region` görüntü kolaylığıdır; `region`u kapsar ve sayfa sınırlarında kalır. Kullanıcı metninin doğruluğunu crop üretildiği için kabul etme. Sadece ilk sayfa destekleniyorsa diğer sayfayı sessizce ilk sayfaya çevirme; açık unsupported sonucu ver.

### 6.3 Dört temel model

**CalloutCandidate — makinenin gözlemi**

| Alan | Kural |
|---|---|
| `id` | Boş olmayan kararlı kimlik; ekran etiketi `C1` ile aynı olmak zorunda değil |
| `source_digest` | Oturumdaki `source_sha256` ile aynı kaynağın kimliği |
| `page_index` | `int >= 0` |
| `region`, `crop_region` | Yukarıdaki tek koordinat sözleşmesi |
| `source_kind` | Açık enum: `vector_text`, `observation`, `raster_region`, `manual` |
| `observation_ids` | Kaynağa geri izleme; yoksa boş liste |
| `detector_version` | Adayı üreten adaptör sürümü; manuel kaynak için de belirli değer |
| `geometry_version` | Üretildiği geometri sözleşme sürümü |
| `machine_text_hint` | Opsiyonel string; yalnız öneri |

**TranscriptionDecision — kullanıcı girdisi**

| Alan | Kural |
|---|---|
| `callout_id` | Bu oturumdaki callout'a referans |
| `raw_text` | Kullanıcının girdiği string **aynen** korunur |
| `normalized_text` | Sunucunun aynı raw text'ten deterministik türettiği ayrı alan |
| `entered_by` | Literal `user`; model veya parser bu kimliği kullanamaz |
| `source_region` | Kullanıcının incelediği etkin bölgenin anlık kopyası |
| `revision` | Bu metin/bölge kararının sunucunun verdiği revision kimliği |

Boş/yalnız whitespace metin kabul edilmez; kullanıcı transcription'ı açık kaldırma işlemiyle kaldırır. Kontrol ederken `raw_text`i trim edip depolama. G1'de normalization yalnız belgelenmiş whitespace düzenlemesi yapabilir; anlamsal sembol normalizasyonu G4'te versioned parser'a aittir.

Transcription revision, global session revision ile aynı kavram değildir. İlk kayıtta yeni global revision değeri kimlik olarak kullanılabilir. İlgisiz karar değişince mevcut transcription revision'ını yeniden yazma. Metin veya source region değişirse yeni transcription revision üret; istemcinin eski revision göndererek bunu atlatmasına izin verme.

**SemanticParse — hesaplanan sonuç**

| Alan | Kural |
|---|---|
| `callout_id` | Transcription ile aynı callout |
| `parser_version` | Açık parser sözleşmesi sürümü |
| `transcription_revision` | Okuduğu transcription revision'ı |
| `status` | `parsed`, `ambiguous` veya `unsupported` |
| `form` | `diameter`, `radius`, `linear` veya `null` |
| `size` | Pozitif sonlu sayı veya `null` |
| `count` | Metinde açık pozitif integer veya `null`; bool/ondalıklı adet kabul etme |
| `termination` | `thru`, `blind` veya `null` |
| `depth` | Pozitif sonlu sayı veya `null` |
| `unit` | Metinde açık `mm`, `in` veya `null` |
| `warnings` | Makinece ayırt edilebilir kodlar; boş liste olabilir |

`parsed` yalnız sözdiziminin anlaşıldığını belirtir. Birim, fiziksel anlam veya sonlanma eksikse build hazır değildir. Sheet unit ile çözümleme, parser metninde birim varmış gibi yazılmaz; ayrı provenance taşır.

**CalloutTargetDecision — kullanıcının hedef onayı**

| Alan | Kural |
|---|---|
| `callout_id` | Bu oturumdaki callout |
| `target_kind` | İlk sözleşme: `circle`, `circle_group`, `vertex_pair`; diğerleri açık unsupported |
| `target_ids` | Sıralı, benzersiz, boş olmayan gerçek geometri kimlikleri |
| `geometry_version` | Onay anındaki geometri sürümü |
| `geometry_key` | Aşağıda tanımlanan geometri/bağlam fingerprint'i |
| `profile_id` | Hedef için gerektiğinde seçili profil |
| `transcription_revision` | Onayın dayandığı transcription revision'ı |
| `parser_version` | Onayın dayandığı parse sürümü |
| `evidence` | Kaynak, yöntem ve incelenebilir referanslar; serbest string tek başına doğrulama sayılmaz |
| `status` | Literal `confirmed`; bu tarihsel onayın bugün geçerli olduğu ayrıca hesaplanır |

`circle` tam 1 ID; `circle_group` en az 2 ID; `vertex_pair` farklı 2 uç ID'si ister. Group'ta aynı ID'yi dört kez yazarak `count=4` sağlanamaz. Vertex pair sırası korunur; axis/direction bu sırayla anlam kazanır. Ekran sıra numarasını ID yerine kullanma.

### 6.4 Tazelik kimlikleri

```text
parse bağı = (callout_id, transcription_revision, parser_version)
target bağı = parse bağı + geometry_key + geometry_version + profile bağlamı
build bağı = mevcut source_sha256 + geometry_version + session revision
             + kullanılan callout parse/target bağımlılıkları
```

Son satırdaki callout build bağımlılıklarının tam entegrasyonu G7/G8'dedir. G1'de zorunlu olan: transcription/target edit ve undo mevcut build'i stale yapar; eski artifact güncel olarak sunulmaz.

`geometry_key` için tek yardımcı kullan: kaynak hash'i, geometry_version, mevcut profil/daire kimlikleri ve geometrileri, seçili profil, kontur düzenlemeleri ve görünüş kararı üzerinden canonical JSON + SHA-256 üret. Timestamp, log, build, parse veya target kaydının kendisini hash'e katma. Aksi halde kendi onayını geçersiz yapan döngü kurarsın. Dictionary anahtarları sıralı, geometri listeleri kararlı ID sıralı olmalı; bir konturun **kenar sırasını** değiştirme.

Bu, aynı geometry_version içinde kontur/profil değişimini yakalar. İlgisiz transcription değişmesi geometry_key'i değiştirmemeli. Gerekenden geniş geometri değişimini stale saymak kabul edilebilir; değişmiş geometriyi current saymak kabul edilemez.

Parse içeriği aynı parser sürümü ve aynı transcription'da farklı çıkıyorsa determinism hatasıdır. Parser davranışı değiştiğinde sürümü artır; eski onayı sessizce yeniden geçerli yapma.

### 6.5 Store sınırında validation

Pydantic alan doğrulaması yetmez. Kaydetmeden önce store şunları da denetler:

- Callout gerçekten bu oturumda ve bu kaynakta mı?
- Aynı callout için birden fazla güncel transcription/target var mı? Varsa açık hata; sonuncuyu sessizce seçme.
- Target ID'leri mevcut geometride var mı, doğru türde mi ve seçili profile ait mi?
- Hedef onayı güncel transcription ve geçerli parse'a mı referans veriyor?
- Metinde açık adet varsa, desteklenen grup bağlamında benzersiz hedef sayısı tutuyor mu?
- İstemci stale revision gönderdi mi? Mevcut revision conflict davranışını kullan.

Yeni/geçerli diye sunulan yanlış target'ı reddet. Kullanıcının eski, artık stale olmuş target kaydını inceleme amacıyla saklamasına izin ver; stale olması başka bir meşru düzenlemenin kaydını engellemesin. Bu ayrımı public state'te göster.

İstemcinin yolladığı `SemanticParse` veya `normalized_text`i doğrulanmış sunucu hesabı diye kaydetme. G1 testlerinde parser çıktısı gerekiyorsa açık store fixture'ı kur; public API'ye “parse sonucu yükle” arka kapısı ekleme.

G1'de henüz çalışan callout parser yoktur. Freshness yardımcıları beklenen parser sürümünü açık parametre olarak alabilir; testler bu parametreyle sürüm değişimini sınar. G4'te bu parametre gerçek parser sürümünden beslenir. G1 public state'inde parse üretilemediğinde `missing/needs_parse` göster; sırf sözleşme testi geçti diye parse üretilmiş sayma. Eski SEMREAD parser sürümlerini yeni callout parser sürümü yerine kullanma.

## 7. Invalidation ve undo: tabloyu uygula

`stale`: kayıt ve kanıt kalır, fakat güncel onay/üretim girdisi olarak kullanılamaz.

| Olay | Parse | Hedef onayı | Build |
|---|---|---|---|
| İlk transcription | Henüz yok; G4'te hesaplanır | Yok | Eski build stale |
| Raw text veya incelenen region değişti | Eski parse stale | Eski onay stale | Stale |
| Target değişti | Güncel parse korunabilir | Yeni seçim açık onayla kaydolur | Stale |
| Profile/contour/view değişti | Metin aynıysa korunabilir | Bağlam değiştiği için stale | Stale |
| Kaynak değişti/okunamıyor veya geometri stale | Güvenilir current veri olarak kullanılamaz | Stale | Stale; current indirme yok |
| Parser sürümü değişti | Yeniden parse gerekir | Eski parse'a bağlı onay stale | İlgili callout build'i stale; G7/G8 |
| Unit/calibration kararı değişti | Basılı metnin parse'ı değişmez | Etkilenen kararlar yeniden doğrulanır | Stale |
| Kullanıcı callout'u ignored yaptı | Tarihsel veri korunabilir | Aktif compile'dan çıkar | Stale; G3/G7 |
| Undo | Geri gelen transcription'a göre doğrula | Geri gelen hedefi güncel bağlamda tekrar denetle | Daima stale; otomatik STEP diriltme yok |
| Sadece sayfayı yenile/reopen | Değişmemeli | Geçerli olan geçerli kalmalı | Kimlikler aynıysa değişmemeli |
| Birebir aynı kararı tekrar save | Değişmemeli | Değişmemeli | No-op; revision/history şişmemeli |

Bu tablo için tek freshness değerlendirme yolu kullan. `public()` “güncel”, build kapısı “stale” diyemez. Tarihsel `status=confirmed` alanını güncel geçerlilik yerine kullanma.

**Undo kuralları:**

- History'ye bağımsız snapshot koy; iç içe nesneler sonraki edit ile değişmemeli.
- Undo eski kullanıcı kararlarını geri getirir; global session revision geriye gitmez, artar.
- Undo eski transcription revision kimliğini geri getirebilir; global revision ile karıştırma.
- Eski parse cache yoksa `needs_parse` göster; uygun görünmesi için sahte parse üretme.
- Undo bugünkü geometriye uymayan eski target'ı otomatik geçerli yapmaz.
- Log geçmişini silme. Undo yeni bir olay olarak loglanır.

## 8. Eski oturum uyumu

G1'de boş callout alanlarıyla eski davranış korunmalıdır.

1. Eski session ve eski `history` entry'lerinde yeni alanlar olmayabilir; boş varsayılanlarla okunmalı.
2. Yeni callout alanlarının eklenmesi için geometry_version artırma. Gerekirse `callout_schema_version` kullan.
3. Load sırasında schema dosyasını değiştiriyorsan mevcut migration yedeğini ezmeyen ayrı yedek al. Bellekte varsayılanla okumak yeterliyse gereksiz disk migration yapma.
4. İkinci load aynı sonucu vermeli; tekrar revision/log artışı veya tekrar geometri üretimi olmamalı.
5. Yalnız yeni boş alanlar eklendi diye eski, kimlikleri geçerli build stale olmamalı. Gerçek karar değişikliği varsa stale olmalı.
6. Eski history'ye undo, callout olmayan karar snapshot'ını doğru yüklemeli; `KeyError` veya validation hatası olmamalı.
7. Eski istemcinin yeni alanları hiç göndermemesi mevcut transcriptions/targets'ı silmemeli. Save sınırında **eksik anahtar = mevcut değeri koru**, **açık boş liste = kullanıcının kaldırma isteği** ayrımını yap. Bunu yalnız yeni alanlar için uygulayarak mevcut save sözleşmesini gereksiz değiştirme.
8. Eski proposals için `accept()` yeni callout kararlarını korumalı; machine text hint veya target proposal'ı callout onayı olarak kabul etmemeli.

## 9. İlk uygulama: G0 ve G1 küçük iş paketleri

### G0 — Pivot kaydı

**Önkoşul:** Başlangıç HEAD ve çalışma ağacı kaydedilmiş.

**Yap:**

1. `docs/PLAN-20.md` yoksa bu uyarlanmış planı o yol altında yeni history entry yap. Varsa içeriğini oku; başka planı ezme. Aynı plan zaten izleniyorsa tekrar kopyalama; çakışma varsa sonraki boş plan numarasını kullan ve pointer'ları tek isimde tutarlı güncelle.
2. `report.md` üstüne yeni aktif ürün durumunu yaz: guided transcription, aktif plan yolu, ilk iş G0+G1, milestone 10 çizim.
3. SEMREAD-001D'yi `PARKED RESEARCH — Round 1 FAIL` olarak göster. 4/12 kullanılmış dev bütçesini koru.
4. Eski araştırma görevlerini tarihsel bölüm olarak işaretle. Eski “sıradaki requalification” ifadesi aktif talimat gibi görünmemeli; tarihsel kanıtı silme.
5. `docs/GUIDED_PROGRESS.md` oluştur ve G0 kanıtını yaz.

**Yapma:** Kod, araştırma ledger'ı, eski planlar veya deney sonuçlarını değiştirme.

**Kabul:** Diff yalnız yeni plan, ilerleme dosyası ve aktif rapor yönlendirmelerini içeriyor; `docs/PLAN-19.md` ve önceki planlar korunmuş; model çağrısı yok.

### G1.1 — Başlangıç testleri ve entegrasyon haritası

**Yap:** Bölüm 5'teki store metotlarını oku. Create/load/save/undo/accept/public/build/artifact'ın yeni alanlara nasıl dokunacağını ilerleme dosyasında kısa bir tabloyla yaz.

Önce mevcut odak kümesini çalıştır:

```sh
.venv/bin/python -m pytest -q tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py
```

Logu `out/guided-transcription/g1-baseline.log` gibi ayrı bir dosyada sakla; pipeline kullanıyorsan pytest exit code'unu kaybetme. Yerel server izni yoksa ilgili HTTP testini ortam engeli olarak ayrı kaydet.

**Kabul:** Gerçek başlangıç sonucu kaydedilmiş. Önceden var olan hata yeni değişiklik hatasından ayrılabiliyor. Başlangıçta hata bulunması bağımsız model çalışmalarını engellemez; G1'in final kapısı için ilgili hatalar çözülmeli veya açıkça engelli kalmalıdır.

### G1.2 — Dört model ve sözleşme testleri

**Yap:** Bölüm 6 modellerini ve tazelik kimliğinin küçük saf yardımcılarını ekle. `Decisions`a `transcriptions` ve `callout_targets` ekle. G1'de normalization ve ilişki kontrolü dışında gerçek metin parser'ı yazma.

**Önerilen test dosyası:** `tests/test_callout_models.py`.

**Kabul:** Pozitif model round-trip; eksik/bilinmeyen semantik alanların `null` kalması; yanlış region, sayı, duplicate ID, target cardinality ve fazla alanların reddi. Callout modelleri `Binding`e dönüştürülmüyor.

### G1.3 — Kalıcılık ve eski oturumlar

**Yap:** Create/load/public/save'de yeni alanları taşı. Bölüm 8 uyum kurallarını uygula. `raw_text`e dokunma; normalized text'i sunucu üretir.

**Önerilen test dosyası:** `tests/test_guided_callouts.py`.

**Kabul:** Gerçek `GuidedStore` ile save → diske yaz → yeni store instance → reopen; raw text birebir aynı. Eski session ve eski history yükleniyor. Yeni veriler eski istemci save'i ve eski proposals accept'i sırasında kaybolmuyor.

### G1.4 — Revision, parse ve target freshness

**Yap:** Bölüm 7 tablosunun G1'e ait satırlarını uygula. Tazelik sonucu public state'te incelenebilir olsun. Her kayıt için `current/stale/missing` durumu ve gerekçe kodu üret; bu hesap kullanıcı onayı oluşturmasın.

**Kabul:** Metin değişince eski parse/target kullanılmıyor; ilgisiz karar değişince transcription revision gereksiz değişmiyor; profil/kontur değişimi aynı geometry_version içinde bile target'ı stale yapıyor; stale istemci kaydı session'ı bozmuyor.

### G1.5 — Undo ve günlüğe alma

**Yap:** Mevcut history/log yolunu genişlet. Kullanıcı `transcribe`, `edit_transcription`, `confirm_target` olayları ile sistemin freshness hesaplarını ayır. Gerçek parser henüz yokken loga `parser/parse` olmuş gibi yazma.

**Kabul:** A → B → undo akışı A'nın kullanıcı kararlarını geri getiriyor; global revision artıyor; snapshot A edit ile değişmemiş; reopen sonrasında sonuç aynı; stale hedefi undo ile geçerli hale getirme hatası yok.

### G1.6 — Build ve artifact stale regresyonu

**Yap:** Yeni alanların mevcut build invalidation yolunu kullandığını kanıtla. Devam eden build'in geç bitmesi senaryosunu kontrol et; gerekirse yalnız bu yarış durumuna dar düzeltme yap.

**Kabul:** Mevcut build → transcription edit → current STEP yok; aynı kontrol target edit ve undo için geçiyor. Eski çıktı dosyası tarihsel olarak diskte kalıyor. Build sürerken edit gelirse geç sonuç yayımlanmıyor ve tamamlanma yolu çökmüyor.

Bu test eski CAD yoluyla oluşturulmuş bir output üzerinde çalışabilir. G1'de callout'tan gerçek CAD compile edilmiş gibi iddia etme.

### G1.7 — Birleşik doğrulama ve teslim

Yeni testler mevcut olduktan sonra:

```sh
.venv/bin/python -m pytest -q tests/test_callout_models.py tests/test_guided_callouts.py tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py
git diff --check
git diff --stat
git status --short
```

Farklı test dosyası adı seçtiysen komutları gerçek adlarla güncelle. Olmayan dosyayı içeren komutu koşulmuş gibi yazma.

- Yeni modeli kullanan diğer modüllere etkisi varsa ilgili testleri ekle.
- Ortak davranışta daha geniş etki veya repo kuralı yoksa saatlerce tüm SEMREAD araştırma testlerini tekrar çalıştırma.
- G1 için G3 tarayıcı akışını veya G9 yeni CAD yolunu tamamlanmış gösterme.
- G1 kabul tablosunu doldur; unresolved maddesi varsa G1 `PASS` değildir.
- G2'ye geçme. Kullanıcıya somut teslim ve kalan kapsamı raporla.

## 10. G1 zorunlu davranış testleri

Sadece Pydantic dump/load testi yeterli değildir. Aşağıdaki store testleri kalıcı oturum yolu üzerinden çalışmalı. Ucuz sentetik fixture'lar kullan; her testte PDF/CAD üretmek gerekmez. Artifact ve geç build senaryolarında ilgili gerçek sınırı koru.

| ID | Senaryo | Beklenen |
|---|---|---|
| T01 | Dört model JSON round-trip | Veriler korunur; unknown alanlar kendiliğinden dolmaz |
| T02 | `"  4 × Ø8 THRU  "` kaydet ve reopen | Raw text boşluklarıyla aynı; normalized ayrı |
| T03 | Aynı adayda machine_text_hint var | Transcription veya target kendiliğinden oluşmaz |
| T04 | Session yeni alanları içermiyor | Açılır; eski kararlar ve geçerli artifact davranışı korunur |
| T05 | Yeni alanları olmayan history'ye undo | Çökmez; boş callout state doğru yüklenir |
| T06 | A=`Ø8`, parse ve target fixture'ı güncel; B=`Ø10` kaydet | A parse ve target stale; A raw text geçmişte durur |
| T07 | Aynı global revision ile ikinci farklı save | Revision conflict; ilk kayıt ve history bozulmaz |
| T08 | Transcription var; yalnız unrelated thickness değiştir | Session revision artar; transcription revision aynı kalır |
| T09 | Geometry_version değişti veya kaynak hash uyuşmuyor | Target stale; current artifact sunulmaz |
| T10 | Geometry_version aynı; profile/contour değiştir | Geometry_key değişir; eski target stale |
| T11 | Olmayan circle / yanlış profile ait uç / duplicate target | Yeni onay açık hata ile reddedilir; kalıcı kayıt bozulmaz |
| T12 | Explicit count=4; yalnız 3 benzersiz hedefi onayla | Uyumsuz onay kabul edilmez |
| T13 | Geçerli A → edit B → undo → reopen | A kullanıcı kararları geri gelir; global revision artar; build stale |
| T14 | Target başka geometriye aitken undo | Eski target yeniden current sayılamaz |
| T15 | Mevcut build → transcription edit / target edit | Public URL ve artifact erişimi eski STEP'i current sunmaz |
| T16 | Build çalışırken yeni karar save; eski build tamamlanır | Yeni karara bağlanmaz; `build=None` nedeniyle çökmez |
| T17 | Aynı session iki kez load | Yeni migration/revision/log döngüsü yok |
| T18 | Birebir aynı karar iki kez save | İkinci save no-op; history/revision şişmez |
| T19 | Eski istemci yeni alanları göndermiyor | Var olan callout kararları korunur; açık `[]` kaldırabilir |
| T20 | Eski proposals accept edilir | Callout kararları kaybolmaz; yeni callout otomatik onaylanmaz |
| T21 | Parser version farklı fixture | Parse ve ona bağlı target stale |
| T22 | Karar save/undo sonrası base reading/options karşılaştır | Temel veriler kullanıcı girdisiyle değiştirilmemiş |

Ek model testleri: ters/sıfır/NaN region; count=0, count=1.5, bool count; negatif/Infinity size; beklenmeyen enum ve unknown alan. T05 ve T17 migration dosyası yazılıyorsa yedek korunmasını da doğrular.

G1 test fixture'ındaki parse/target, testin hazırlık verisidir. Bunu ürünün çalışan parser/önerici kanıtı sayma.

## 11. Sonraki fazların sırası ve kabul kapıları

**Bu bölüm mevcut görevin uygulama kapsamı değildir.** Kullanıcı daha sonra hangi fazları açarsa yalnız onları yürüt. Her fazdan önce ilgili bölümü tekrar oku ve küçük işlere ayır. Bölüm 3 çalışma döngüsü her fazda geçerlidir.

| Faz | Teslim | Sonraki faza geçmek için kanıt |
|---|---|---|
| G2 | Observations → callout candidate adaptörü | Stable ID, provenance, vektör fixture, raster fixture veya açık “aday yok” |
| G3 | Callout kutuları, crop, metin, add/edit/ignore | Gerçek tarayıcı: load → click → type → save → refresh/reopen → undo |
| G4 | Versioned deterministik parser ve parse onayı | Pozitif/negatif matris; eksik anlamda tahmin yok; confirmation doğru parse sürümüne bağlı |
| G5 | Kanıtlı target proposal sıralaması | Aynı input → aynı sıralama/kanıt; hiçbir proposal otomatik onay değil |
| G6 | Target highlight, seçme, group ve düzeltme | Tarayıcıda gerçek seçim; count/ID/geometry freshness denetimi |
| G7 | Confirmed data → mevcut guided CAD kararları | Saf, tekrarlanabilir compile; kaynak provenance; conflict/unsupported görünür |
| G8 | Ortak readiness ve kullanıcı soruları | UI ve backend aynı revizyon için aynı blocker'ları verir; API ile bypass yok |
| G9 | Plate yeni akış regresyonu | Yeni transcription/binding yolundan üretim + STEP reopen + bağımsız feature kontrolü |
| G10 | Sonuç görmeden 10 dosyalık manifest | Tam 10 kaynak hash'i, sayfa/view, scope ve evaluator ölçütleri dondurulmuş |
| G11 | Aynı manifest ile ilk guided koşu | Her case için karar izi, müdahale sayısı, output ve bağımsız verdict |
| G12 | Genel hata düzeltmeleri | Her düzeltmede tekrar testi + aynı hatayı farklı veride sınama; case hardcode yok |
| G13 | Aynı manifest ve ortak kodla kabul koşusu | 10 case'in tamamı raporlanmış; ana hedef 10/10 doğru STEP |

Faz sırası bağımlılık sırasıdır. Tek bir dosyada tüm fazları uygulayıp sonra test etmeye çalışma.

### 11.1 G2 — Candidate üretimi

Öncelik: vector PDF text spans → mevcut observations/text/number regions → raster kaynakların gerçekten sağladığı bölgeler. Leader/dimension-line kanıtını kullanabilirsin. Yeni VLM servisi şart değildir.

- `source_digest + page_index + canonical region + detector_version + source_kind` üzerinden deterministik kimlik üret. Python'ın süreçler arasında değişen `hash()` fonksiyonunu kullanma.
- Canonical region hassasiyetini belgeleyip sınır testini ekle; aynı kaynak/detector/girdi yeniden işlendiğinde ID aynı kalmalı.
- Detector version değişiminde yeni aday kimliği çıkabilir. Eski kullanıcı kararını yakın kutuya sessizce taşıma.
- Aynı bölgedeki gözlem tekrarları için açık dedup kuralı kullan; iki farklı callout'u gizlice birleştirme.
- Sadece proximity metni doğrulamaz. Machine hint okunmuş veya onaylanmış veri sayılmaz.
- Raster gözlem bölge üretmiyorsa boş liste + gerekçe dön; sahte kutu üretme. G3 manuel alan çizme yoluyla devam edilir.

### 11.2 G3 — Kullanıcı metni ve alan kararları

Mevcut canvas'a callout overlay ekle. Kutuda kısa etiket ve türetilmiş state göster:

```text
unreviewed / transcribed / parsed / bound / conflict / ignored
```

Bunları tek bağımsız mutable state string'iyle doğruluk kaynağı yapma. Örneğin `bound`, güncel parse + kullanıcı onayı + güncel target gerektirir.

Panel: crop, basılı metin girdisi, kaydet, “Bu callout değil”, “Alanı düzelt”, “Yeni callout alanı çiz”. G4 bitmeden “parser hazır” görünümü üretme; metin kaydı ayrı çalışabilir.

- Manuel candidate/region override ve ignore kararı `decisions` + history içindedir.
- Region değişimi metni, parse'ı ve ilgili onayları yeniden incelemeye açar.
- Candidate temel provenance'ını region edit ile ezme; etkin bölgeyi ayrı hesapla.
- Kullanıcı kaynak metnini UI'da HTML olarak çalıştırma; `textContent` veya güvenli metin rendering kullan.
- Bir browser testi başarılı sayılacaksa gerçek click/type/save/reload akışı çalışmalı. API testi browser testi diye raporlanmaz.

### 11.3 G4 — Deterministik parser ve onay

Önerilen modül: `src/drawingto3d/callout_parse.py`. Tek giriş noktası, belgeli normalization ve `parser_version` kullan. Alt string bulup geri kalanını yok sayma; **tüm input** desteklenen grammar ile açıklanmalı.

İlk grammar: `Ø / ⌀ / DIA`, `R`, `x / X / ×` adet öneki, integer/decimal, `mm / in`, `THRU / THROUGH`, `DEPTH / DEEP`, basit linear dimension. `.375` geçerli decimal. Ondalık virgül, kesir, thread, tolerans, counterbore ve countersink ilk sürümde ayrıca tanımlanmadıkça unsupported/ambiguous.

| Input | Beklenen temel sonuç |
|---|---|
| `Ø8` | diameter, size=8; count/unit/termination/depth=null |
| `⌀8` | Yukarıdakiyle aynı anlam; raw text farklı kalır |
| `R5` | radius, size=5; physical feature çıkarma yok |
| `4x Ø8` | diameter, size=8, count=4; termination/unit=null |
| `4 × Ø8 THRU` | count=4, diameter=8, termination=thru; unit=null |
| `Ø10 6 DEEP` | diameter=10, depth=6, termination=blind; unit=null |
| `Ø10 DEPTH 6 mm` | diameter=10, depth=6, termination=blind, unit=mm |
| `25 mm` | linear=25, unit=mm; axis/direction yok |
| `.375 DIA` | diameter=0.375; unit=null, in varsayma |
| `Ø8 THROUGH` | diameter=8, termination=thru |
| `0x Ø8` veya `2.5x Ø8` | Geçerli adet değildir; build'e uygun parse yok |
| `Ø8 THRU 6 DEEP` | Çelişkili sonlanma; ambiguous |
| `M8`, `Ø8 ±0.1`, `Ø8 H7`, `1/4 DIA` | İlk grammar dışında; unsupported |
| `Ø8 SOME_UNKNOWN_NOTE` | Bilinmeyen suffix'i yutma; unsupported/ambiguous |
| `8,5` | İlk sürümde ambiguous/unsupported; 85 veya 8.5 diye tahmin yok |

UI parse önizlemesinde eksik değerleri `unresolved` göster. Birim onayı ayrıysa kaynağını göster: `printed`, `user` veya `confirmed_sheet_unit`.

**Parse confirmation:** Kullanıcının “Onayla” eylemini ayrı decision olarak `(callout_id, transcription_revision, parser_version)` ile sakla. Text edit veya parser version değişince bu onay stale olur. Kullanıcı semantiği düzeltmek istiyorsa metni düzeltir veya açık ek karar verir; parser çıktısını gizli elle değiştirme.

### 11.4 G5/G6 — Hedef önerisi ve kullanıcı onayı

Kanıt sırası: leader/dimension-line connectivity, arrow/extension geometry, type compatibility, count compatibility, proximity, mevcut bind/meaning kanıtları. Bu sinyalleri mevcut `bind.py` ve reading zincirinden adapte et. Kanıt sıralaması ve eşit puan için kararlı tie-break belirle.

```text
diameter → circle adayları daha uyumlu
radius → ilgili arc/circle geometrisi önerilebilir
linear → iki endpoint önerisi
count=4 → dört benzersiz target isteyen öneri
```

Circle uyumu fiziksel delik anlamına gelmez. Radius okunabiliyor ama o hedef türü compiler'da yoksa bunu açık unsupported göster.

UI: hedef highlight, “Onayla”, “Başka hedef”, “Birden fazla hedef”, “Bağlama yok / desteklenmiyor”. Eksik hedefte en yakını sessizce seçme. Group hedefleri benzersiz olmalı. Vertex pair'de endpoint sırası, axis ve direction ayrı ve açık olmalı.

Geometri değişince `STALE BINDING — yeniden onay gerekli` göster. Yüksek öneri puanı kullanıcı onayı yerine geçmez.

### 11.5 G7 — Compile: eksik anlamı tamamlama

Compiler yalnız güncel/onaylı veriden mevcut `Hole`, `Binding` ve diğer desteklenen guided kararlarına çıktı üretir. Fonksiyon tekrarlanabilir olmalı; yeniden çağrı aynı delikleri/binding'leri listeye tekrar eklememeli. Kullanıcının elle oluşturduğu mevcut kararları ezme; çelişkiyi açık göster.

**Doğru delik örneği:**

```text
raw_text = "Ø8 THRU"
+ geçerli parse ve kullanıcı parse onayı
+ unit = mm, onaylı ve provenance'ı belli
+ confirmed target = circle_3, güncel geometri
+ physical feature = hole, kullanıcı tarafından açık onaylı
→ Hole(circle_id="circle_3", kind="through", diameter=8)
```

**Yetersiz örnek:** `Ø8` + bir circle onayı. Bu yalnız çap ve hedefi açıklar; hole/thru/unit eksikleri için soru sor. Hedef onayı ekranı fiziksel hole seçimini de açıkça sunup kaydedebilir; sadece circle tıklanmasını bu anlama çevirme.

**Linear örnek:**

```text
"40" + confirmed vertex pair + confirmed axis=x + direction
+ resolved unit + geçerli profil/görünüş
→ mevcut Binding(value=40, axis="x", direction=..., first=..., second=...)
```

Inch → mm dönüşümü tek yerde yapılır (`1 in = 25.4 mm`). Hem girdide hem compile'da tekrar çevirme. Thickness veya blind depth eksikse başka boyuttan tahmin etme.

Provenance zinciri:

```text
source hash → callout/region → raw text + revision → parser version
→ parse confirmation → resolved unit/physical meaning
→ target confirmation + geometry key → compiled decision → build identity
```

Compile çıktısı kullanıcı elle yazmış gibi yeni log olayı üretmemeli; `derived from confirmed decisions` niteliğinde olmalı. Önceki compile ürünlerini provenance üzerinden yeniden hesapla; listelere kör append yapma.

### 11.6 G8 — Readiness: backend kapısı şart

Callout review role kullanıcı kararıdır:

```text
unreviewed / required / optional / ignored_by_user / unsupported
```

- `unreviewed`: gerekli olup olmadığı henüz kararlaştırılmadı; review sorusu oluşturur, otomatik optional olamaz.
- `required`: transcription, parse onayı, anlam/unit ve target şartlarını sağlamalı.
- `optional`: compile'a katkı vermiyorsa bunu açık göster; geometri için gerekli bilgi bu etiketle atlanamaz.
- `ignored_by_user`: açık kullanıcı kararı ve gerekçe; katılan başka feature kararı varsa conflict çözülmeli.
- `unsupported`: gereken bir bilgi/feature ise build'i engeller; başarı payına yazılmaz.

Build için ayrıca profile, gerekli view, units/calibration, thickness ve feature coherence çözülmüş olmalı. Eski session'da callout listeleri boşken eski guided akış gereksiz bloklanmamalı; yeni transcription akışında “sıfır required seçildi” kaçış yoluyla eksik özellikler doğru sayılmamalı.

Tek readiness fonksiyonu hem UI sorularını hem `make_plan/store.build` engelini beslesin. Sadece build düğmesini disable etmek yetmez.

Question kodları:

```text
unreviewed_callout, missing_transcription, parse_ambiguous,
missing_parse_confirmation, missing_target, stale_target,
missing_unit, missing_feature_meaning, missing_axis_direction,
unsupported_semantic, missing_profile, missing_view, geometry_conflict
```

Aşamaları ayrı raporla: `READ=success, BIND=success, BUILD=unsupported` mümkün ve dürüst bir sonuçtur.

### 11.7 G9 — Plate regresyonu

Mevcut doğrulanmış Plate çizimi yeni transcription + confirmation + target + compiler yolundan geçmeli. Eski hazır planı doğrudan çalıştırmak bu fazın kabulü değildir.

Kaynak: `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`.

Tarihsel referans değerler:

```text
bbox = 120 × 80 × 15 mm
volume ≈ 124825.4 mm³
4 hole cylinders
1 pocket cylinder
STEP reopen = success
```

Bu yuvarlanmış hacmi bit düzeyinde eşitlik testi yapma. Mevcut evaluator'ın bağımsız formülünü ve toleranslarını kullan; yeni tolerans gerekiyorsa çıktı görmeden gerekçesiyle sabitle. Hacim+bbox+silindir sayısı yetmez: delik/cep konumu, çap, derinlik/sonlanma da doğru olmalı.

Doğru çizim metni ve kullanıcı kararları referans STEP'ten doldurulamaz. Hazır replay varsa kaynağını ve bunun scripted replay olduğunu belirt; gerçek kullanıcı testi diye sunma.

## 12. G10–G13: 10 dosyalık ürün kabulü

### 12.1 Sonuç öncesi manifest

G10'da tam 10 çizimi **G11 sonuçlarını görmeden** sabitle. G9 Plate daha önce görülmüş regresyon olarak etiketlenir; unseen diye raporlanmaz.

Önerilen dosya: `eval/guided_transcription/manifest.json`.

Her case:

```text
case_id
source_path                     repo-relative
source_sha256
page_index / view
format
supported_archetype_expectation
prior_exposure                  regression / previously_seen / unseen
reference_evaluator_availability
evaluator_spec_id               evaluator tarafındaki spec'e işaret; cevap içermez
```

Manifest kimliğini/hash'ini run raporuna koy. Başarısız case'i kolay bir dosyayla değiştirerek oranı yükseltme. Yeni corpus gerekiyorsa yeni manifest versiyonu ayrı koşu olur; eski sonuç korunur.

Reference STEP yolları, beklenen feature ölçüleri ve toleranslar evaluator-only dosyada tutulur. Producer yalnız çizim + kullanıcı kararlarını alır. Evaluator önce producer sonucunu bekler; teşhis çıktısından case'e özel producer girdisi üretme.

Referans yoksa çizimden bağımsız çıkarılmış denetim spec'i kullanılabilir; eksik kritik ground truth varsa verdict `UNVERIFIED` olur, `PASS` olmaz.

### 12.2 İnsan yardımı ve uzun otonom koşu sınırı

Bu ürün kullanıcı desteklidir. Coding agent'ın uzun çalışması eksik insan kararını uydurmasını haklı çıkarmaz.

- `interactive`: Gerçek kullanıcı metin/hedef/fiziksel anlam onaylarını verir; ölçülen user-action olaylarını kaydet.
- `scripted replay`: Çizimden daha önce kullanıcı tarafından doğrulanmış kararlar tekrar oynatılır; replay olduğunu raporla. Gerçek kullanıcı eforunu ölçmüş sayma.
- Gerekli kullanıcı girdisi yoksa case `BLOCKED_INPUT` kalır. Diğer bağımsız case'leri sürdürebilirsin; eksik case'i başarı sayamazsın.
- AI'nin otomatik ürettiği metni `entered_by=user` yapma. Önceden onaylanmış karar yoksa evaluator/reference bilgisinden doldurma.

### 12.3 Her koşunun kaydı

Koşular öncekinin üzerine yazılmasın. Run ID altında şunları kaydet:

```text
manifest hash + kod sürümü/diff kimliği
parser/detector/compiler/evaluator sürümleri
her case için session ve karar/audit izi
run_mode: interactive / scripted_replay
manual added/edited regions
manual transcriptions + edits
parse results + confirmed parse sayısı
proposal shown/accepted + manual target corrections
feature confirmations + unit/profile/view kararları
build success/refusal + gerekçesi
STEP yolu/hash'i + reopen sonucu
bbox + feature correctness + final verdict
```

Gerekli ve varsa full trace, `LOG_LIMIT=200` olan UI loguna güvenerek kaybolmamalı. Eval koşusunun audit kaydını UI görünüm sınırından ayrı koru.

### 12.4 Metriklerin pay/payda tanımı

| Metrik | Tanım |
|---|---|
| `GUIDED_CORRECT_STEP_RATE` | Bağımsız evaluator'da geometrik olarak `PASS` olan case sayısı / sabit 10 |
| `SUPPORTED_CASE_CORRECT_RATE` | Ek tanı metriği; önceden belirlenen desteklenen case'lerde doğru STEP / desteklenen case sayısı |
| `USER_INTERVENTIONS_PER_SHEET` | Gerçek kullanıcı mutation/confirmation olayları; kategori sayıları + toplam |
| Detection coverage | Gerekli callout'lar için önceden tanımlı evaluator eşleşme kuralıyla bulunan / beklenen; gold yoksa `NOT_MEASURED` |
| Parser success | Desteklenen transcription'larda başarılı parse / desteklenen transcription sayısı; tüm inputların status dağılımı da ayrıca |
| Proposal accepted rate | Değiştirilmeden onaylanan gösterilmiş proposal / karar verilmiş gösterilmiş proposal; payda 0 ise `N/A` |

UI click/hover sayısını karar sayısıyla karıştırma. Transcription save+parse tek kullanıcı eylemiyse parser çalışmasını ikinci user action sayma. Metni yeniden düzenlemek ek müdahaledir. Multi-select confirmation bir onay olayıdır; kaç hedef içerdiğini ayrıca kaydet. Otomatik log/system olayları kullanıcı müdahalesi değildir.

### 12.5 Failure sınıfları ve genel düzeltme

```text
DETECT         alan bulunamadı/yanlış bölge
TRANSCRIBE     basılı metin yanlış/eksik girildi
PARSE          grammar/semantic çözümleme hatası
BIND           yanlış/eksik/stale hedef
CONSTRAINT     çelişkili veya çözülemeyen boyut/kısıt
CAD_UNSUPPORTED desteklenmeyen geometrik özellik
CAD_WRONG      üretildi, fakat geometri yanlış
EVALUATOR      bağımsız doğrulama aracı/ground truth sorunu
```

Bir case'in birden çok nedeni varsa birincil blocker ve ikincil bulguları ayrı kaydet. Her G12 düzeltmesi için: küçük tekrar → genel düzeltme → aynı davranışı farklı ID/değer/geometriyle test → ilgili regresyon → etkilenen case'leri yeniden koş. Hiç değişmeyen koşuyu döndürüp başarı arama.

### 12.6 İki farklı kabul kapısı

**Dürüst çalışma kapısı:**

```text
10/10 kaynak açılır
10/10 session kalıcıdır
10/10 sessiz tahmin yoktur
10/10 STEP veya açık destek-kapsamı reddi vardır
```

**Asıl ürün başarı kapısı:**

```text
aynı sabit 10 case
aynı genel ürün kodu ve UI
10/10 reopened STEP
10/10 bağımsız geometrik PASS
```

İlk kapı ikinci kapının yerine geçmez. 8 doğru STEP + 2 dürüst refusal = **8/10**, 10/10 başarı değildir. Unsupported case'leri paydadan çıkarma. Bbox doğru ama kritik feature yanlışsa `CAD_WRONG`; evaluator çalışmadıysa `UNVERIFIED`.

## 13. Teslim biçimi ve bitiş kontrolü

Her teslim kısa ve kanıtlı olsun:

```text
Tamamlanan kapsam:
Değişen davranış:
Değişen dosyalar:
Çalıştırılan testler ve gerçek sonuç:
Kanıt/log yolları:
Çalıştırılmayan veya engelli kontroller:
Bilinen açıklar:
Sonraki yetkili işlem:
```

**G1 bitti demeden önce:**

- [ ] G0 aktif plan/pivot yönlendirmesi tutarlı; tarihsel araştırma korunmuş.
- [ ] Dört temel model var; kullanıcı/metin/parse/hedef ayrımı açık.
- [ ] Raw text birebir korunuyor, normalized ayrı ve deterministik.
- [ ] Gerçek store round-trip ve yeni store instance ile reopen geçti.
- [ ] Eski session, history ve eski istemci yeni verileri kaybetmiyor.
- [ ] Transcription revision ile global revision karıştırılmıyor.
- [ ] Geometry_version aynı kalırken geometri/bağlam değişimi target'ı stale yapıyor.
- [ ] Undo snapshot'ları doğru geri getiriyor; stale STEP yeniden güncel olmuyor.
- [ ] Parse/target freshness public state'te nedenleriyle görülebiliyor.
- [ ] Stale client, yanlış hedef ve geç biten build davranışları doğrulandı.
- [ ] İlgili eski testler ve yeni T01–T22 davranışları yeşil; skip/blocked başarıya katılmadı.
- [ ] UI/parser/compiler henüz uygulanmadıysa raporda açıkça sonraki faz olarak yazıyor.
- [ ] İlerleme dosyasında kaldığın yer ve gerçek komut sonuçları var.

**Guided core bitti demeden önce (G2–G9 ayrıca yetkilendirildikten sonra):**

- [ ] Kutular, manual region, crop, transcription, ignore ve undo çalışıyor.
- [ ] Parse gösteriliyor; eksik anlamlar tahmin edilmiyor; onay sürüme bağlı.
- [ ] Target önerisi ve kullanıcı onayı ayrı; geometri değişiminde stale.
- [ ] Unit/physical feature/axis gibi eksikler açık kullanıcı kararlarıyla çözülüyor.
- [ ] Confirmed data mevcut CAD yoluna provenance ile compile ediliyor.
- [ ] Backend readiness kapısı eksik/unsupported required bilgide üretimi durduruyor.
- [ ] Plate yeni yoldan üretilmiş ve feature bazında doğrulanmış.

**10 dosyalık milestone bitti demeden önce:**

- [ ] Sabit manifest, run kimliği, her case için tam iz ve bağımsız verdict var.
- [ ] Reference/evaluator verisi producer'a sızmamış.
- [ ] User interventions gerçekten ölçülmüş; replay ile karıştırılmamış.
- [ ] Failure/refusal/unverified sonuçları dürüst paydada yer alıyor.
- [ ] 10/10 geometrik PASS hedefi gerçekleşmiş; gerçekleşmediyse milestone tamamlandı denmiyor.

## 14. Daha sonra otomasyon

Guided core ve kullanıcı yükü ölçümü güvenilir olduktan sonra ayrı görevler açılır:

```text
A0 kullanıcı metni yazar
A1 OCR/VLM hint → kullanıcı Accept/Edit
A2 crop-first transcription → belirsiz olanları review
A3 daha iyi otomatik target önerisi
A4 mostly automatic sheet
A5 full automatic, yalnız ölçülmüş kanıttan sonra
```

Hiçbir otomasyon aşaması model önerisini kendiliğinden kullanıcı kararı olarak kaydetmez.

**İlk somut iş (yürürlükte): G0 → G1.1 → … → G1.7. Sonra teslim et.**

---

## Uygulama kaydı (bu repo kopyası)

- **Uygulama başlangıcı:** 2026-10-06. Ölçülen HEAD `5175f373f1d6892e481341ed2cbcfd89dec29e36` (planla aynı). `.venv` hazır (Python 3.12.8, pydantic 2.13.5). `rg` bu host'ta yok; geniş dosya aramaları daraltılmış yollarla yapılır.
- **İlk kapsam:** G0 + G1 (§9). Kanıt: `docs/GUIDED_PROGRESS.md`.
- **G2–G13:** Gelecek işler; kullanıcı faz açmadan uygulanmaz (§11–§12 ve §14 bu oturumda kapsam dışıdır).
