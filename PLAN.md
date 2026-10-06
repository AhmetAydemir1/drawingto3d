# drawingto3d — Hermes görev planı: G1 düzeltme turu 2

**Tarih:** 2026-10-06\
**İncelenen HEAD:** `67ff518`\
**Ana ürün planı:** [docs/PLAN-20.md](docs/PLAN-20.md)\
**İlk uygulanacak kapsam:** G1R2-01 + G1R2-02 + birleşik doğrulama\
**G2 ve sonrası:** Henüz açık değil. G2 hazırlık notları yalnız bölüm 8'de.\
**Sonuç:** Önceki dört bulgu için düzeltme var. Mevcut testler geçti; iki ek davranış hatası doğrulandı. G1 kabulü bu iki madde için yeniden açık.

Bu dosya, kullanıcının “yapılanları kontrol et ve plan.md hazırla” isteğinin çıktısıdır. Bu incelemede ürün kodu değiştirilmedi. Aşağıdaki görevleri, kullanıcı bu planı uygulamanı istediğinde yap.

Bu diskte `plan.md` ve `PLAN.md` aynı dosyadır; Git'in izlediği ad `PLAN.md` olarak korundu. Önceki kök plan baytları değiştirilmeden [arşivlendi](docs/PLAN_ROOT_BEFORE_GUIDED_REVIEW_20261006.md). `docs/PLAN-20.md` ve önceki numaralı planlar tarihsel kayıt olarak korunur.

## 1. Hermes'e doğrudan verilecek mesaj

> Kök PLAN.md'yi uygula. Kapsam yalnız G1 düzeltme turu 2: G1R2-01 ve G1R2-02. Önce bağımsız tekrar scriptini çalıştır; sonra her bulgu için kalıcı regresyon testi ekle ve dar düzeltme yap. Mevcut 183 testin yeşil olması tek başına yeterli değil: yeni tekrarlar da geçmeli. Ürün kodunu baştan yazma. G2'yi başlatma. İş sonunda önce/sonra kanıtı, gerçek test sonuçları ve güncel GUIDED_PROGRESS kaydıyla teslim et.

**Okuma sırası:** Bölüm 2–3 → G1R2-01 → ilgili test/düzeltme → G1R2-02 → ilgili test/düzeltme → bölüm 6–7. G2 notlarını mevcut iş listene alma.

## 2. Bağımsız kontrol: ne doğrulandı?

### 2.1 Önceki dört inceleme maddesi

`e59c5eb → 67ff518` değişiklikleri kaynak kod ve yeni testlerle incelendi:

| Önceki bulgu | Mevcut düzeltme | Bu incelemenin sonucu |
|---|---|---|
| Taşınan target'ın sunucu alanları istemciden değiştirilebiliyordu | `_prepare_callouts` taşınan satırı kalıcı kayıttan alıyor; evidence değişikliği yeniden onay sayılmıyor | Önceki tekrar kapalı; testleri geçti |
| Profil değişimi ve hedef onayı aynı save'de farklı bağlama bakıyordu | `geometry_key`, `profile_id` ve profil doğrulaması yeni payload bağlamını kullanıyor | Önceki tekrar kapalı; testleri geçti |
| `ambiguous`/`unsupported` veya çelişen parse ile target onaylanıyordu | Yeni onayda `status=parsed` ve tek anlamlı exact parse sonucu isteniyor | Önceki tekrar kapalı; testleri geçti |
| Vertex pair yalnız ardışık `vN` uçları kabul ediyordu | Kararlı `<edge_id>:start/end` destekleniyor; komşuluk şartı kaldırıldı | Önceki tekrar kapalı; fakat etkin kontur doğrulaması G1R2-01'de hâlâ açık |

Açık `reconfirm` isteği eklenmiş; doğrulamadan sonra `false` olarak tüketiliyor. Bu mekanizmayı koru. Yeni sorun, stale hedefin geçerli duruma dönüşmesinin onay günlüğüne yazılmaması.

### 2.2 Bu incelemede yeniden çalıştırılan testler

Aynı 15 dosyalık birleşik küme bu HEAD üzerinde yeniden çalıştırıldı:

- İlk koşu: **182 passed, 1 failed**, 79.69 s, exit 1.
- Tek failure: `test_http_revision_and_artifact_contract`; sandbox `127.0.0.1` üzerinde port açılmasını engelledi (`PermissionError`).
- Aynı HTTP testi localhost port izni olan ortamda tekrar: **1 passed**, 0.79 s, exit 0.
- Sonuç: Seçilen **183 test iki koşuda doğrulandı**. İlk koşunun failure kaydı saklandı; “tek koşuda 183 geçti” diye yeniden yazılmadı.
- SEMREAD suite, gerçek yeni callout parser/UI/CAD kabulü bu incelemede koşulmadı; kapsam dışı.

Kanıtlar:

- [Birleşik koşu logu](eval/audits/20261006-guided-g1-review/suite.log)
- [İzinli HTTP tekrar logu](eval/audits/20261006-guided-g1-review/http-recheck.log)
- [Bağımsız tekrar scripti](eval/audits/20261006-guided-g1-review/review_probes.py)
- [Düzeltme öncesi iki bulgunun sonucu](eval/audits/20261006-guided-g1-review/probe-results-before.json)

**Scriptte exit 1 beklenen mevcut sonuçtur:** iki ürün davranışı hâlâ hatalıdır. Bu script test başarısı diye yorumlanmamalı. Script yalnız geçici, sentetik store'larda çalışır; gerçek kullanıcı oturumlarını değiştirmez; referans STEP/gold okumaz.

### 2.3 Yapılmamış olanlar

G2 candidate adaptörü, G3 UI, G4 gerçek parser ve G7 callout→CAD compiler hâlâ sonraki fazlardır. Fixture'a yazılmış parse kaydı çalışan ürün parser'ı kanıtı değildir.

SEMREAD-001D: `PARKED RESEARCH — Round 1 FAIL`; formal 0/4; kullanılmış dev bütçesi 4/12. Requalification veya 001E açılmaz. Yeni model çağrısı yapılmaz.

## 3. Çalışma sözleşmesi

1. Başlangıçta `git status --short` ve `git rev-parse HEAD` kaydet. İnceleme HEAD'inden sonra değişiklik varsa ilgili diff'i oku; eski satır numarasına körlemesine patch uygulama.
2. Geçerli `AGENTS.md` talimatlarını kontrol et. Mevcut kullanıcı değişikliklerini ve `PLAN-17-HERMES.md` dosyasını koru.
3. `docs/GUIDED_PROGRESS.md` içine yeni “G1 düzeltme turu 2” bölümü ekle. Önceki teslim/test kayıtlarını silme. Yeni iki madde bitmeden güncel durumu `G1 tamam` gösterme.
4. Aynı anda tek bulgu üzerinde çalış. Her bulguda küçük tekrar → anlamlı kırmızı test → dar düzeltme → yeşil test → ilgili regresyon sırasını izle.
5. Geometri algoritmasını, CAD motorunu, UI'yı veya parser'ı bu görevde yeniden yazma. G1R2-01 için mevcut geometri düzeltme yolunun gerekli parçasını ortak kullanmak kapsam içidir.
6. Yanlış davranışı sabitleyen eski test varsa beklentisini ürün sözleşmesine göre düzelt; kalan kontrolleri gevşetme. Yeni testleri skip/xfail yaparak geçme.
7. Her küçük iş sonunda gerçek komut/exit code/sonuç/kanıt yolunu ilerleme dosyasına yaz. Bağlam kaybından sonra önce bu dosyayı ve diff'i oku.
8. Aynı hatada üç deneme sonuç vermiyorsa hipotezleri ve küçük tekrarı kaydet; kör değişiklik yapma. Bağımsız kapsam içi işe devam edebilirsin; engeli başarı sayma.
9. Test süreci hâlâ çalışıyorsa ikinci kopyasını başlatma. Ortam kaynaklı failure'ı kod hatasından ayır; port testini kanıt olmadan `PASS` sayma.
10. Commit yapıyorsan yalnız ilgili dosyaları açık adlarıyla stage et. `git add .`, reset/clean veya geçmiş kanıtların üzerine yazma yok. Push/merge bu görevin şartı değil.

## 4. G1R2-01 — Onayı etkin kontur üzerinde doğrula

**Öncelik:** P1 — kullanıcı tarafından çıkarılmış geometri geçerli hedef olarak kaydedilebiliyor.\
**İlgili kod:** `src/drawingto3d/guided.py`, `_check_target_geometry`, `_vertex_name`, `_validate_callouts`; incelenen sürümde özellikle satır 1581–1583.\
**Dayanak:** PLAN-20 §6.5 gerçek/hedef geometri doğrulaması; §7 kontur değişimi; eski guided yolunda silinmiş kenara sessizce bağlanmama kuralı.

### 4.1 Küçük tekrar ve gerçek sonuç

Sentetik kontur:

```text
 a:  (20,20)  → (120,20)
 d2: (70,20)  → (120,20)    # tekrarlı yarım kenar; kullanıcı çıkarıyor
 b:  (120,20) → (120,80)
 c:  (120,80) → (20,80)
 d:  (20,80)  → (20,20)

contour.drop = ["d2"]
target_kind = "vertex_pair"
target_ids = ["d2:start", "c:start"]
```

Mevcut `correct_profile()` çağrısı `d2`yi kaldırıyor. Son konturun `audit_contour(...).ok` sonucu **true**, kalan kenarlar `[a,b,c,d]`. Buna rağmen aynı save içinde `d2:start` hedefi kabul ediliyor ve public state `target=current` gösteriyor.

Bu tekrar, yalnız geçersiz kontur üzerinde yapılmış bir deney değildir: **düzeltilmiş kontur geçerlidir**, fakat onaylanan kenar artık o konturda yoktur.

**Neden:** Fingerprint `contour.drop` bilgisini içeriyor; ama `_check_target_geometry` ham `options.profiles[].edges` üzerinden kontrol ediyor. Yeni fingerprint'e bağlamak, hedefin etkin geometride bulunduğunu kanıtlamaz.

### 4.2 Uygulama adımları

1. Mevcut tekrar scriptini çalıştır ve `G1R2-01` sonucunun neden kırmızı olduğunu gör.
2. `tests/test_guided_callouts.py` içine yukarıdaki **geçerli düzeltilmiş kontur** senaryosunu taşı. Yeni target onayı açık hatayla reddedilmeli; session baytları/revision/history değişmemeli.
3. Target doğrulamasına yalnız `profile_id` değil, aynı save'in **etkin karar bağlamını** geçir: seçili profil + kontur düzeltmeleri.
4. Mevcut `correct_profile` ve ilgili geometri hazırlama/çözümleme yardımcılarını oku. Etkin konturu çalışma kopyasında oluştur; `record.options` veya temel kenarları yerinde değiştirme. CAD üretimi çağırma.
5. Yeni target veya `reconfirm=true` için uçların etkin konturda varlığını ve fiziksel olarak farklı oluşunu doğrula. Çıkarılmış kenarın ucunu başka köşeye otomatik taşıma.
6. Etkin kontur düzeltmesi üretilemiyorsa ilgili yeni vertex target onayını açık gerekçeyle reddet. Kullanıcının yalnız kontur düzeltmesini kaydetmesi veya eski stale target'ı inceleme için taşıması engellenmemeli.
7. Aynı yordam, yeni onay ve yeniden onay için kullanılsın. Fingerprint kontrolü mevcut yerinde kalsın; bu kontrolün yerine geçmez.

**Kimlik kuralı:** `<edge_id>:start/end` kararlı uç yolunu koru. `vN` gibi eski/kanonik biçimleri düzeltilmiş listenin yeni indislerine sessizce bağlama. Önce kayıtlı bağlamda gerçek uç kimliğine çöz; anlam korunamıyorsa yeniden seçim iste. Yeni target için mümkün olduğunda kararlı uç kimliğini sakla. Bu düzeltme için tüm eski oturumları yeniden yazma.

**Fiziksel eşitlik kuralı:** Komşu kenarların aynı köşeye gelen uçları tek fiziksel noktadır. Kontur düzeltmesi sonrası eşitliği ham sıra numarasına güvenerek kararlaştırma. Mevcut koordinat/tolerans sözleşmesini ortak kullan; sırf testi geçirmek için yeni geniş tolerans ekleme.

### 4.3 Zorunlu test matrisi

| ID | İşlem | Beklenen |
|---|---|---|
| R1-A | Aynı save: d2'yi çıkar + d2:start hedefini onayla | Ret; kalıcı kayıt değişmez |
| R1-B | Önce kontur düzeltmesini kaydet, sonra çıkarılmış ucu yeni hedef seç | Ret; düzeltme kaydı korunur |
| R1-C | Önce hedef var; sonra ilgili kenarı çıkar; aynı hedefe `reconfirm=true` | Eski hedef stale kalır; yeniden onay reddedilir |
| R1-D | Aynı geçerli düzeltmede kalan `a:start` ve `c:start` uçlarını seç | Onay kabul edilir; key/profil aynı yeni bağlama aittir |
| R1-E | Stale hedefi değiştirmeden ilgisiz thickness kararını kaydet | Kayıt başarılı; target stale; onay olayı yok |
| R1-F | Düzeltme ardından undo/reopen | Kararlar korunur; etkin geometriye uymayan hedef otomatik current olmaz |
| R1-G | Aynı fiziksel köşeyi farklı uç ID'leriyle seç | Ret; farklı geçerli köşeler kabul |
| R1-H | Kontur silmesiyle `vN` sıra numarası anlam değiştirebilir | Başka köşeye sessiz bağlanma yok; anlam korunur veya açık ret |

Kalıcı testler sahte bir `_check_target_geometry` mock'u üzerinden geçmemeli. Store save, gerçek kontur düzeltmesi ve public freshness yolunu kullan.

## 5. G1R2-02 — Gerçek yeniden onayı günlüğe yaz

**Öncelik:** P2 — karar geçerli hale geliyor fakat onu onaylayan kullanıcı eylemi audit izinde bulunmuyor.\
**İlgili kod:** `src/drawingto3d/guided.py`, `_log_callout_changes`, `_consume_reconfirm`, `GuidedStore.save`; incelenen sürümde satır 1648–1650.

### 5.1 Küçük tekrar ve gerçek sonuç

```text
circle c0 hedefini onayla
→ başka profile geç: target stale
→ aynı target_ids ile reconfirm=true gönder
→ target current; global revision 3 → 4
→ yeni log olayları = []
→ confirm_target olay sayısı 1 → 1
```

**Beklenen:** Gerçek stale→current yeniden onay için tam bir yeni `user/confirm_target` olayı; bu olay hangi callout'un hangi bağlamda onaylandığını göstermeli.

**Neden:** `_log_callout_changes` yalnız `target_kind` ve `target_ids` aynı mı diye bakıp satırı atlıyor. Onaylanan geometri bağlamı veya transcription/parse bağı değişmiş olsa da atlama sürüyor. Tek kullanımlık `reconfirm` bayrağı da log aşamasına kadar tüketilmiş oluyor.

### 5.2 Uygulama adımları

1. `tests/test_guided_callouts.py` içine stale→current yeniden onayda tam bir yeni `user/confirm_target` olayı isteyen test ekle. Önce kırmızı sonucu kaydet.
2. Doğrulanmış onay eylemi bilgisini, `reconfirm` tüketilmeden önce işlem bağlamında tut veya önce/sonra onay bağımlılıklarını açık karşılaştır. Persisted karar ile işlem komutunu karıştırma.
3. `reconfirm` doğrulama tamamlanmadan tüketilmesin. Daha önce düzeltilen validation bypass hatasını geri getirme.
4. Gerçek yeniden onayda olay yaz. Evidence içinde callout ID, onaylanan geometry_key/profile ve transcription/parser bağı incelenebilir olsun; kişisel metni veya tüm session'ı gereksiz kopyalama.
5. Başarısız validation hiçbir onay olayı/revision/history yazmamalı. Taşınan onayda istemci alan drift'i yeni olay oluşturmamalı.
6. Kaydedilen target'ta `reconfirm=false` kalmalı. Reopen, public state hesabı ve undo yeni onay gibi loglanmamalı; undo kendi mevcut olayını kullanır.

Güncel bağlamda hiçbir şeyi değiştirmeyen tekrar onayı için mevcut no-op davranışı korunabilir; bu tercihi testte belgeleyin. Bu bulgunun zorunlu kısmı **stale→current veya onay bağı değişimi** olan gerçek yeniden onayın kaybolmamasıdır.

### 5.3 Zorunlu test matrisi

| ID | İşlem | Beklenen |
|---|---|---|
| R2-A | Profil değişikliği sonrası aynı target_ids ile açık yeniden onay | Tam 1 yeni user/confirm_target; current; reconfirm=false |
| R2-B | Aynı hedef, yeni transcription/parse bağına gerçek onay | Tam 1 onay olayı; yeni bağ audit'te görülür |
| R2-C | Taşınan target'ta istemci geometry_key/profile/evidence değiştiriyor | Kalıcı onay korunur; yeni confirm olayı yok |
| R2-D | Unsupported/ambiguous/conflicting parse ile reconfirm | Ret; log/revision/history değişmez |
| R2-E | Reopen ve public freshness tekrarları | Yeni onay olayı yok |
| R2-F | Undo | Undo olayı; sahte confirm olayı yok; build eski haliyle dirilmez |

## 6. Doğrulama komutları ve kabul kapısı

Komutları repo kökünde çalıştır. `.venv` yoksa repo kurulumunu izle; çalışmayan komutu başarılı raporlama.

### 6.1 Önce bağımsız tekrar

```sh
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py
```

İncelenen HEAD'de iki `passed=false` ve exit 1 verir. Düzeltme sonrasında iki `passed=true` ve exit 0 vermeli. `probe-results-before.json` tarihsel sonuçtur; üzerine yazma. Yeni sonucu `probe-results-after.json` gibi ayrı yola al.

Scriptte test helper'ı isim değişirse yalnız fixture kurulumunu uyarlayabilirsin; beklenen davranışı veya `passed` koşullarını zayıflatma. Kalıcı pytest regresyonları ayrıca gereklidir.

### 6.2 Odak testleri

```sh
.venv/bin/python -m pytest -q tests/test_guided_callouts.py tests/test_callout_models.py tests/test_contour_fix.py tests/test_binding_end_meaning.py
```

Yeni testleri önce tek tek çalıştır; hepsi geçtiğinde odak kümesini çalıştır. Mevcut testlerin doğru davranışlarını koru.

### 6.3 Birleşik son koşu

```sh
.venv/bin/python -m pytest -q tests/test_callout_models.py tests/test_guided_callouts.py tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py tests/test_view_decision.py tests/test_view_core.py tests/test_sheet_frame.py tests/test_stable_identities.py tests/test_contour_fix.py tests/test_measure_meaning.py tests/test_user_dimensions.py

git diff --check
git diff --stat
git status --short
```

Test sayısını zorla 183'e sabitleme; yeni regresyonlarla artması beklenir. Sonuçta gerçek passed/failed/skipped sayılarını yaz. Log için redirection veya pipeline kullanıyorsan pytest exit code'unu koru.

HTTP testi yine yalnız sandbox port iznine takılırsa aynı testi izinli localhost ortamında ayrı doğrula:

```sh
.venv/bin/python -m pytest -q tests/test_guided.py::test_http_revision_and_artifact_contract
```

Ortam izin vermiyorsa `BLOCKED_ENV` kaydet; skip ile “tamamı geçti” sonucu üretme. Bu iki değişiklik için tüm SEMREAD deney/test zincirini veya gerçek model çağrılarını başlatma.

### 6.4 G1 yeniden kabul listesi

- [ ] G1R2-01 kalıcı regresyonları yeşil; geçerli etkin konturda silinmiş hedef kabul edilmiyor.
- [ ] G1R2-02 kalıcı regresyonları yeşil; gerçek yeniden onay olayının izi var.
- [ ] Bağımsız tekrar scripti iki bulguda da `passed=true`, exit 0.
- [ ] Önceki dört düzeltmenin testleri hâlâ yeşil.
- [ ] İlgili birleşik küme doğrulandı; ortam engelleri varsa dürüstçe ayrı.
- [ ] Raw text, temel geometri, history, eski session ve eski artifact kuralları bozulmadı.
- [ ] G2/UI/parser/compiler için yapılmış gibi iddia yok.
- [ ] GUIDED_PROGRESS içinde eski kabulün eksikleri, düzeltmeler ve yeni gerçek kanıt yolları var.
- [ ] Final diff yalnız ilgili kaynak/test/plan/kanıt dosyalarını içeriyor.

Bu kapıdan önce `G1 tamam` deme. Kapı geçince bu görevi teslim et; G2 kendiliğinden açılmaz.

## 7. Teslim ve kalıcı ilerleme

İlerleme dosyasına eklenecek tablo:

| İş | İlk durum | Kanıt | Kalan |
|---|---|---|---|
| G1R2-01 etkin konturda target doğrulama | TODO | probe-results-before.json | test + düzeltme |
| G1R2-02 yeniden onay logu | TODO | probe-results-before.json | test + düzeltme |
| G1R2-FINAL | TODO | — | bağımsız tekrar + birleşik küme |

Her iş `IN_PROGRESS → PASS` sırasıyla ilerler; gerçek başarısızlık `FAIL`, eksik ortam `BLOCKED_ENV`, eksik kullanıcı bilgisi `BLOCKED_INPUT` olarak yazılır. Sıradaki tek somut işlem her zaman görünür olmalı.

Teslim formatı:

```text
İncelenen/teslim edilen commit ve çalışma ağacı:
G1R2-01: önce / sonra / regresyon testleri / kanıt yolu
G1R2-02: önce / sonra / regresyon testleri / kanıt yolu
Bağımsız tekrar sonucu ve exit code:
Birleşik test sonucu ve exit code:
Değişen dosyalar:
Bilinen açıklar ve çalıştırılmayan kontroller:
G2 durumu: açılmadı
```

Önceki `docs/GUIDED_PROGRESS.md` kabulünü silip hiç yanlış olmamış gibi gösterme. Yeni bölümde hangi eksik davranışın bulunduğunu ve hangi testle kapatıldığını yaz. `report.md` güncellenecekse yalnız güncel ürün durumunu düzelt; tarihsel SEMREAD kanıtlarına dokunma.

## 8. G2 için hazır notlar — uygulama kapsamı değil

G1 yeniden kabul edildikten ve kullanıcı G2'yi açtıktan sonra uygulanır. G0/G1'i yeniden baştan yazma. Yeni görev yalnız **Observations → CalloutCandidate adaptörü** olur; G3+ yine ayrı kalır.

### 8.1 Gerçek koddan doğrulanan girişler

- `src/drawingto3d/observe.py`: `Observations.source`, `.frame`, `.texts`, `.notes` mevcut.
- `TextObservation`: `id`, `text`, `bbox(x,y,w,h)`, `method`, `char_range`, `confidence` mevcut.
- `SourceRef.page` sıfır tabanlı; frame genişlik/yüksekliği render pikselidir.
- **Kritik:** `TextObservation.unit` varsayılanı `mm`, `count` varsayılanı `1`. Bu alanları callout semantic truth olarak taşıma. G2 yalnız region/provenance/hint üretir.
- Vektör metin yöntemi `pdf-text`; raster kaynaklarını gerçek `method` değerlerinden eşle. Bilinmeyen yöntemi dosya uzantısından tahmin etme.
- `GuidedStore.create()` zaten `observations=observe(source)` çağırıyor. Adaptör bu nesneyi tekrar kullanmalı; sırf candidate üretmek için ikinci kez observe/OCR çağırma.
- `CalloutCandidate` ve boş session `callout_candidates` alanı hazır. Ayrı bir paralel candidate şeması icat etme.

### 8.2 Önerilen küçük iş sırası

| İş | Yapılacak | Kabul |
|---|---|---|
| G2.1 | Saf `candidate_from_observations` adaptörü; tek piksel→normalize dönüşümü | Synthetic bbox matematiği, provenance, girdi değişmezliği |
| G2.2 | Deterministik ID/dedup ve hata tanıları | Aynı input/list sırası değişimi aynı ID kümesi; farklı kaynak/bölge ayrılır |
| G2.3 | `GuidedStore.create` entegrasyonu | Gerçek yeni oturumda adaylar kaydolur; kullanıcı kararları/parse boş kalır |
| G2.4 | Vektör ve raster/honest-none regresyonu | İki kaynak yolu; OCR yoksa açıklamalı boş aday; sahte kutu yok |
| G2.5 | Store reopen ve eski oturum uyumu | Yeni adaylar kalıcı; eski oturum sessizce yeniden tespit/yeniden bağlama yapmaz |

İlk sürüm için `Observations.texts` içindeki geçerli bölgeleri aday saymak yeterlidir. Bütün metinleri doğru callout diye etiketleme; aday yanlış pozitif olabilir. G3'te kullanıcı ignore edebilir. VLM, OCR doğruluk projesi veya teknik metin grammar'ı bu adaptörün işi değildir.

### 8.3 Sabit sözleşmeler

```text
region = [bbox.x / width, bbox.y / height,
          (bbox.x + bbox.w) / width, (bbox.y + bbox.h) / height]

id = SHA-256(canonical identity payload)
identity payload = source_digest + page_index + canonical region
                   + detector_version + source_kind
```

- Normalize kutu sonlu, pozitif alanlı ve 0..1 içinde olmalı. Gerçekten geçersiz gözlemi sessizce geçerli kutuya kırpma; skip gerekçesi kaydet. Crop padding sayfa sınırında kırpılabilir; crop yalnız gösterimdir.
- Canonical region hassasiyetini ve detector_version'ı bir yerde tanımla. Rastgele UUID veya Python `hash()` kullanma.
- ID oluştururken dosya adı/sample no/text içeriğini karar kestirmesi yapma. Display etiketi `C1` ayrı olabilir.
- Tam aynı bölge ve kaynak tekrarlarını kararlı biçimde birleştir; `observation_ids` birleşimini koru. Birbirine sadece yakın callout'ları körlemesine merge etme.
- Dedup sırasında farklı machine hint'ler çelişirse birini keyfi truth seçme; hint'i boş bırakıp tanı üretmek yeterlidir.
- Adı değişmiş aynı kaynak byte'ı aynı kaynak kimliğidir. Kaynak byte'ı değişirse ID değişmeli.
- Yeni/geçerli candidate eklenmesi transcription, target, parse onayı veya CAD kararı üretmez.
- İlk sürüm yalnız page 0'ı destekliyorsa page>0 için açık unsupported dön; sayfa numarasını 0'a çevirme.
- Eski session açılışında adayları yeniden tespit etme. Candidate refresh/manual region işi ayrıca tasarlanmadan mevcut kararlarla eşleştirme yapma.

### 8.4 G2 için asgari testler

1. 1000×500 frame, x=100/y=50/w=200/h=100 → `[0.1,0.1,0.3,0.3]`.
2. Input liste sırası değişse de ID kümesi ve deterministic çıktı sırası aynı.
3. Kaynak digest/page/bölge/detector_version farklıysa kimlik çakışmıyor.
4. Duplicate observation birleşiyor; provenance ID'leri kaybolmuyor.
5. Boş/ters/taşmış bbox tanıyla reddediliyor; NaN/Infinity yok.
6. Machine hint kullanıcı transcription'ına veya SemanticParse'a terfi etmiyor; observation'ın varsayılan unit/count değerleri taşınmıyor.
7. Gerçek vektör fixture aday üretiyor; gerçek kaynak region'larına geri izlenebiliyor.
8. Raster gözlem varsa bölge taşınıyor; OCR/gözlem yoksa açıklamalı boş liste.
9. Yeni store create→disk→yeni store reopen adayları koruyor; parse/transcription/target kendiliğinden oluşmuyor.
10. Eski callout'suz session mevcut davranışıyla açılıyor; load dosyayı tekrar tekrar değiştirmiyor.

G2'nin bitmesi görünür callout UI, parser, binding proposal veya STEP üretimi bitmiş demek değildir. G3/G4/G5/G7 kabul koşullarını G2 sonucu diye raporlama.

## 9. Değişmeyen ürün hedefi

```text
Kullanıcı tarafından doğrulanmış basılı metin
→ deterministik anlam
→ kullanıcı tarafından doğrulanmış geometri ve fiziksel anlam
→ mevcut CAD yolu
→ bağımsız doğrulanmış STEP
```

Nihai hedef sabit manifestte **10/10 geometrik doğru STEP**. Dürüst refusal, parser başarısı veya STEP reopen tek başına bu hedefin yerine geçmez. Referans STEP evaluator-only kalır; örneğe özel hardcode ve model önerisini kullanıcı onayı sayma yasağı sürer.

**Şimdiki tek somut iş: G1R2-01 → G1R2-02 → G1R2-FINAL → teslim.**
