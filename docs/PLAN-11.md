# PLAN.md — drawingto3d / SEMREAD-001B

## 9/10 canonical gold sonrası uygulama planı

**Tarih:** 2026-10-04  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `d9881cbf9dbd1c56fb087658f0df8e60341e804c`  
**Canonical gold:** **9/10**  
**Güncel `gold_content_identity`:** `351ad8e5fcdf62b12e917ed682792746b14af2bcb5267ed7d63a8e3c44ef0f05`  
**Güncel yeniden üretilebilir SEMREAD test sayısı:** **179 passed / 0 failed**  
**Son kayıtlı full-suite:** **1188 passed** (`b092acc...`; 9/10 gold öncesi)  
**Gerçek V/VE inference:** **başlamadı**  
**Inference budget:** **0/30**  
**P5 freeze:** **AÇIK**  
**Sıradaki tek iş:** `frozen-views-exercise`

---

# 1. Güncel yön

Proje şu anda doğru sırada ilerliyor.

Artık kalan yol:

```text
9/10 canonical gold
→ frozen-views-exercise
→ 10/10
→ tüm gold/referansları yeniden doğrula
→ full pytest
→ D sonuçlarını reuse ederek değerlendir
→ acceptance snapshot
→ clean-clone reproducibility
→ FREEZE.json bağlamalarını tamamla
→ atomic P5 freeze
→ V/VE preflight
→ 20 final V/VE inference
→ immutable evaluation
→ hata sınıfları
→ ölçülen probleme göre semantic-reader geliştirmesi
→ yeni bağımsız holdout
→ ürün hattına dönüş
```

Şu anda benchmark altyapısına yeni özellik eklemek için gerekçe yoktur.

Darboğaz yalnız:

```text
frozen-views-exercise canonical gold
```

sayfasıdır.

---

# 2. Ürünün asıl hedefi

Nihai ürün:

> Farklı teknik çizim PDF/PNG/JPG dosyalarını yerel makinede okuyup, belirsizliği gizlemeden, kullanıcı düzeltmesini destekleyerek doğru 3D STEP üretmek.

Tam ürün zinciri:

```text
source drawing
→ observe
→ bind
→ semantic meaning
→ uncertainty / abstention
→ constraints
→ multi-view reconciliation
→ typed CAD operations
→ deterministic CAD
→ STEP
→ reopen / feature audit
→ user correction
→ revision
```

SEMREAD-001B yalnız şu parçayı ölçüyor:

```text
observe / bind / semantic meaning
```

Benchmark ürün değildir.

---

# 3. Kanıtlanmış güncel durum

## 3.1 Canonical gold = 9/10

İzlenen sayfalar:

```text
dev-plate-pocket
dev-flange-book
dev-flange-elbow
dev-drawing-2
frozen-exercise-51
frozen-exercise-12
frozen-exercise-17
frozen-exercise-13
frozen-enclosure
```

Eksik tek sayfa:

```text
frozen-views-exercise
```

## 3.2 `dev-flange-book` kapandı

Kayıtlı durum:

```text
7 Ø/R claim
vision_checked = true
exhaustiveness = predicates
```

Bağımsız scale root:

```text
50.00 mm doğrusal datum
296 px
5.920 px/mm
```

Önemli okuma:

```text
6x Ø6.40 ↧15.00
⌴ Ø11.00 ↧3.90
Ø100.00
R35.00
Ø60.00
Ø30.00
R2.00
```

Burada depth sembolleri görsel doğrulandı; OCR truth source yapılmadı.

Coverage bu committe:

```text
8/10
```

## 3.3 `frozen-exercise-51` kapandı

Kayıtlı durum:

```text
10 Ø/R claim
vision_checked = true
exhaustiveness = predicates
```

Bağımsız scale root:

```text
150.00 mm doğrusal datum
590 px
3.9333 px/mm
```

Gold çağrıları:

```text
Ø100.00
Ø50.00
R60.00
R10.00
Ø15.00
Ø18.00
R15.00 ×2
R16.00
Ø12.00
```

`R60` için slot/yay geometrisi ayrıca fit edilerek cross-check edildi.

Coverage:

```text
9/10
```

Budget:

```text
0/30
```

## 3.4 Test kaydı düzeltmesi

Önceki handoff'ta:

```text
183 passed
```

yazılmıştı.

Bu sayı commitli test ağacından yeniden üretilemiyor.

Güncel yeniden üretilebilir gerçek durum:

```text
179 collected
179 passed
0 failed
```

Test dosyaları kaybolmadı; önceki 183 farkının çalışma ağacındaki commitlenmemiş ekstra test dosyasından kaynaklanmış olması en makul açıklama olarak kaydedildi.

Bundan sonra referans alınacak SEMREAD test baseline:

```text
179
```

Yeni test eklenirse sayı artabilir.

---

# 4. Şu anda yapılmayacaklar

Şu aşamada YAPMA:

```text
V/VE inference
semantic-reader tuning
frozen sayfaya özel heuristic
new evaluator feature
matching-policy değişikliği
prompt tuning
model tuning
CAD planner rewrite
multi-view implementation
UI redesign
STEP feature expansion
```

Bunlar 001B final ölçümden sonra sonuçlara göre seçilecek.

---

# 5. Değişmez deney kuralları

## 5.1 Gold production yoluna sızmaz

Gold / reference / expected value şuralara girmez:

```text
observe
bind
meaning
semantic candidate reader
V prompt
VE prompt
planner
CAD
```

Yalnız evaluator kullanır.

## 5.2 Frozen tuning verisi değildir

`frozen-views-exercise` yalnız gold annotation için incelenebilir.

Şu amaçlarla kullanma:

```text
production threshold ayarlamak
OCR heuristic yazmak
leader finder tuning yapmak
prompt tuning yapmak
model seçmek
```

## 5.3 Örneğe özel production logic yasak

Yasak:

```text
filename
page_id
exercise number
known coordinates
known dimensions
known hole count
reference STEP
```

Örnek:

```python
if page_id == "frozen-views-exercise":
    ...
```

geçersizdir.

## 5.4 Raster OCR truth değildir

Raster gold zinciri:

```text
OCR / primitive discovery
→ visual adjudication
→ target binding
→ measured box or trusted observation
→ evidence
```

OCR tek başına ground truth değildir.

## 5.5 Printed callout truth source'tur

Çizimde yazan:

```text
Ø
R
count
depth
THRU
```

anlamı gold'un ana kaynağıdır.

Pixel geometry yalnız:

```text
corroboration
```

olabilir.

## 5.6 Independent scale şartı

Geçersiz:

```text
Ø20 claim scale root = Ø22 claim
Ø22 claim scale root = Ø20 claim
```

Geçerli root:

```text
independent linear dimension
trusted physical raster calibration
non-target datum
```

Independent root yoksa:

```text
corroboration.kind = none
```

kullan.

## 5.7 `SCALE 1:n` px/mm değildir

Raster export/tarama/resizing nedeniyle başlık bloğundaki scale tek başına pixel calibration sağlamaz.

## 5.8 Belirsizlikte uydurma yok

Çözülemeyen claim:

```text
exclude / underdetermined / out_of_scope
```

olabilir.

Yanlış kesin gold yazmak daha kötüdür.

## 5.9 Geçmişi silme

Yasak:

```text
git reset --hard
git clean -fd
failed attempt silme
budget sıfırlama
eski evaluation overwrite
```

---

# 6. Deney kolları değişmeyecek

## D

```text
observe
→ bind
→ meaning
→ deterministic semantic adapter
```

Model inference yok.

## V

```text
raw full-page image only
```

## VE

```text
V ile aynı raw full-page bytes
+
real observation overlay
+
addressable observation table
```

VE'ye verilmez:

```text
gold
expected answer
reference STEP
deterministic final semantic decision
```

V/VE arasında farklı olan tek deneysel değişken:

```text
evidence
```

olmalıdır.

---

# 7. Budget değişmeyecek

Sözleşme:

```text
dev maximum   = 10
final maximum = 20
total maximum = 30
```

Şu an:

```text
0/30
```

Freeze kapanana kadar:

```text
0/30
```

kalmalıdır.

Gerçek request gönderildiyse:

```text
timeout
transport failure
parse failure
failed response
```

bütçe harcar.

Gönderilmeyen preflight retleri harcamaz.

---

# 8. ŞİMDİKİ TEK İŞ — `frozen-views-exercise`

Kaynak:

```text
examples/Teknik Resim Görünüş Çıkarma Örnekleri 1 - Makine Eğitimi.jpg
```

Bilinen yaklaşık raster boyutu:

```text
736 × 1041
```

Bu düşük çözünürlüklü sayfada amaç:

```text
maksimum claim sayısı
```

değildir.

Amaç:

```text
güvenilir, yeniden üretilebilir, savunulabilir scorable gold
```

oluşturmaktır.

---

# 9. `frozen-views-exercise` çalışma yöntemi

## 9.1 Başlangıç snapshot

İlk olarak kaydet:

```text
git status
git log -5
manifest --check
budget
```

Beklenen:

```text
coverage 9/10
budget 0/30
HEAD d9881cb...
```

## 9.2 Sayfayı görsel bölgelere ayır

Önce:

```text
views
callout clusters
dimension zones
title / irrelevant text
```

olarak böl.

Ama bu segmentation yalnız annotation yardımıdır; production heuristiğine dönüştürme.

## 9.3 Callout discovery

Bulunabilecek aday tipleri:

```text
Ø callout
R callout
count prefix
THRU/depth
leader-attached dimensions
```

OCR yalnız aday üretir.

Her aday görsel doğrulanmalı.

## 9.4 Symbol ambiguity

Düşük çözünürlükte özellikle dikkat:

```text
Ø vs 0
R vs ordinary character
3 vs 8
1 vs 7
5 vs 6
20 vs 28
10 vs 16
```

Karakter açık değilse exact gold yazma.

## 9.5 Leader / target binding

Her scorable claim için:

```text
callout region
leader path
arrowhead
first target geometry
view ownership
```

kanıtlanmalı.

Leader başka çizgilerle çakışıyorsa:

```text
manual visual path tracing
```

yapılabilir.

Ama sonuç hâlâ belirsizse claim'i dışla.

## 9.6 Target representation

Trusted primitive varsa:

```text
target_observation
```

kullanılabilir.

Primitive extraction güvenilmezse:

```text
target_box_norm
```

ölç.

Box:

```text
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

şartını sağlamalı.

## 9.7 Vision evidence

Sayfa raster olduğu için:

```text
vision_checked = true
```

zorunlu.

Her scorable claim:

```text
source_evidence içinde vision
```

taşımalı.

## 9.8 Scale corroboration

Önce independent linear dimension ara.

Kullanılacaksa:

```text
printed mm value
measured pixel span
endpoint rationale
px/mm
```

yaz.

Sonra başka independent linear ölçüyle cross-check yap.

Bağımsız span güvenilir değilse scale kullanma.

```text
corroboration.kind = none
```

geçerlidir.

## 9.9 Scope

Sayfanın bütün detayları güvenilir şekilde okunamıyorsa:

```text
full_page
```

exhaustiveness iddiası yapma.

Tercih:

```text
predicates
```

veya güvenilir:

```text
regions
```

scope.

## 9.10 Physical semantics

Sırf çizilmiş çember gördün diye:

```text
physical = hole
```

deme.

Sırf section görünüşünden:

```text
THRU
blind
```

uydurma.

Printed notation veya açık multi-view evidence gerekli.

---

# 10. `frozen-views-exercise` kabul kriteri

Sayfa ancak aşağıdakiler tamamlandığında bitmiş sayılır:

```text
tracked spec mevcut
vision_checked = true
her scorable claim visual evidence taşıyor
target binding belgeli
unclear claims dışlanmış
exhaustiveness dürüst
corroboration independent veya none
reference üretilebiliyor
check_reference ok=true
manifest --write başarılı
page --verify birebir
manifest --check = 10/10
budget = 0/30
```

Sonuç:

```text
canonical gold = 10/10
```

olmalı.

---

# 11. 10/10 olur olmaz yapılacaklar

Yeni feature geliştirmeden doğrudan doğrulama turuna geç.

Sıra:

```text
1. manifest --check
2. all-page --verify
3. stable identity check
4. SEMREAD tests
5. full pytest
6. D reuse evaluation
7. acceptance snapshot
8. clean clone
9. freeze binding
10. atomic freeze
```

---

# 12. All-page verify

Tüm 10 sayfa için:

```text
tracked spec
→ regenerate gold-src
→ regenerate reference
→ compare exact hash
```

Geçerli olmalı.

Kontrol:

```text
10/10 source hashes
10/10 spec hashes
10/10 reference hashes
```

Her page için mismatch = P3 açık.

---

# 13. Final gold identity

10/10 tamamlanınca yeni:

```text
gold_content_identity
```

oluşacak.

Bu 9/10 identity'den farklı olmalıdır.

Aynı içerikle iki kez manifest yazıldığında:

```text
byte-identical manifest
same gold_content_identity
```

beklenir.

Timestamp/machine path identity'ye girmemeli.

---

# 14. Raster audit

10/10 milestone'da bütün raster spec'leri topluca tarat.

Kontrol:

```text
vision_checked=true
vision source_evidence exists
measured boxes valid
measurement_reason exists
no placeholder text
no NaN/inf/out-of-range boxes
```

---

# 15. Corroboration graph audit

Tüm claims üzerinde:

```text
self dependency = 0
mutual dependency = 0
cycle = 0
```

olmalı.

`independent_scale` root'ları:

```text
non-target linear datum
```

olmalı.

---

# 16. SEMREAD tests

Güncel reproducible baseline:

```text
179 collected / 179 passed
```

10/10 sonrası test suite:

```text
tests/test_semread_001b*.py
```

tam geçmeli.

Yeni test eklenmediyse sayı en az 179 olmalı.

Eğer daha az test toplanıyorsa:

```text
nedenini açıklamadan ilerleme
```

---

# 17. Full pytest milestone

10/10 tamamlanınca:

```bash
pytest -q
```

koş.

Son kayıtlı full-suite:

```text
1188 passed
```

Bu sayı eski HEAD'e ait.

Yeni durumda sayı değişebilir.

Kabul:

```text
0 failed
0 unexplained collection loss
```

---

# 18. D kolunu yeniden inference etme

D zaten:

```text
10/10 attempt
0 model inference
```

olarak var.

İlk tercih:

```text
valid_reuse
```

Kontrol:

```text
producer identity
input identity
source hash
prepared page identity
candidate schema
attempt final state
artifact hashes
```

uyumlu olmalı.

Production identity değişmediyse D'yi yeniden üretme.

---

# 19. D evaluation

10/10 gold sonrası mevcut D predictions yeni final gold'a karşı değerlendirilir.

Ama:

```text
prediction üretimi tekrar edilmez
```

sadece evaluator koşar.

Rapor:

```text
page metrics
predicate metrics
localization
binding
abstention
overclaim
```

taşımalı.

---

# 20. Acceptance snapshot

Freeze öncesi mekanik snapshot al.

En az:

```text
gold coverage
B01..B07
D/V/VE matrix
budget
lifecycle
orphan attempts
producer identity
evaluation identity
match policy version
```

Beklenen:

```text
gold 10/10
D valid_reuse = 10
V to_run = 10
VE to_run = 10
budget = 0/30
orphan = 0
B02 closed
B07 closed
B05 open
B06 open
```

B05/B06 V/VE ölçümü öncesi açık kalmalıdır.

---

# 21. Clean-clone reproducibility

Mevcut çalışma ağacını temizleme.

Ayrı fresh clone kullan.

Fresh clone'da yalnız tracked repo ile:

```text
corpus prepare
observations
canonical specs
gold-src
references
manifest verification
```

çalışmalı.

Kriter:

```text
10 regenerated reference hashes
==
10 manifest reference hashes
```

ve:

```text
gold_content_identity same
```

olmalı.

Şunlara bağımlılık olmamalı:

```text
old out/
scratch files
absolute developer path
hand-edited generated reference
```

---

# 22. FREEZE.json bağlamaları

Freeze yalnız gold identity değildir.

Final deney için minimum:

```text
freeze schema
git HEAD
gold_content_identity
source hashes
spec hashes
reference hashes
producer_identity
evaluation_identity
candidate schema version
match policy version
preprocessing identity
model name
expected model digest
runtime identity
generation settings
D selected attempt ids
D artifact hashes
D evaluation run id
budget snapshot
lifecycle snapshot
matrix snapshot
```

Timestamp metadata olabilir fakat semantic identity'ye girmemeli.

---

# 23. Atomic P5 freeze

`--freeze` başarılı sayılmak için:

```text
coverage = 10/10
manifest strict pass
source hashes pass
spec hashes pass
reference hashes pass
all references regenerate
all regenerated hashes match
no invalid corroboration
gold_content_identity stable
FREEZE.json complete
```

kanıtlamalı.

Başarı:

```text
P5 CLOSED
```

---

# 24. Freeze sonrası değişiklik yasağı

P5 sonrası final V/VE başlamadan:

```text
gold
corpus
prompt
candidate schema
model
model digest
runtime
settings
preprocessing
matching policy
matching tolerance
ambiguity rule
evaluation semantics
```

değişmez.

Bug bulunursa:

```text
freeze invalid
→ fix
→ new identity
→ refreeze
```

---

# 25. V/VE preflight

İlk gerçek model çağrısından önce beklenen:

```text
P5 closed
gold 10/10
D valid_reuse 10
V to_run 10
VE to_run 10
budget 0/30
orphan 0
```

---

# 26. Raw-page invariant

Her page:

```text
sha256(V raw image)
==
sha256(VE raw image)
```

olmalı.

VE yalnız ek olarak:

```text
overlay
observation table
```

alır.

---

# 27. Model invariant

Preflight kontrol:

```text
model name
model digest
runtime
structured output support
num_predict / generation settings
```

Mismatch varsa:

```text
SEND YOK
```

ve blocked state yaz.

---

# 28. Leak audit

Request paketlerinde şunlar bulunmamalı:

```text
gold value
gold filename
reference output
expected semantic label
benchmark answer sentinel
```

---

# 29. Final V/VE matrix

Final:

```text
10 pages × V
10 pages × VE
=
20 final calls
```

Her gerçek gönderim budget'a yazılır.

Her cell final disposition alır:

```text
valid_result
failed_attempt
blocked
```

---

# 30. Retry politikası

Yasak:

```text
bad answer → delete → retry until good
```

Retry yalnız önceden tanımlı transport policy ile.

Her send budget harcar.

Failed attempt geçmişte kalır.

---

# 31. Evaluator değişmeyecek

Final predictions görüldükten sonra:

```text
threshold
match margin
scope
predicate set
gold
```

sonucu güzelleştirmek için değiştirilemez.

Gerçek evaluator bug varsa yeni evaluation version açılır.

---

# 32. Matching policy

Candidate ↔ gold eşleştirmesi:

```text
target.region
source.region
```

ilişkisine dayanır.

Expected numeric value:

```text
candidate seçmek için kullanılmaz
```

Near-tie ambiguity semantic scoring dışı kalır.

---

# 33. Raporlanacak metrikler

En az:

```text
localization_match_rate
semantic_field_accuracy
target_binding_accuracy
candidate_overclaim_rate
candidate_abstention_rate
false_positive
unscorable_extra_candidate
```

Predicate bazında:

```text
representation
physical
form
size
count_printed
termination
depth
target_binding
```

---

# 34. D'ye karşı karşılaştırma

Her predicate için:

```text
scorable
recovered
regressed_wrong
regressed_abstain
net_correct_gain
```

hesapla.

Tek aggregate accuracy ile karar verme.

---

# 35. Cevaplanacak araştırma soruları

## Q1

```text
V, D'den daha mı iyi?
```

## Q2

```text
VE, V'den daha mı iyi?
```

## Q3

```text
Evidence hangi predicate'lerde faydalı?
```

## Q4

```text
Evidence hangi predicate'lerde zararlı?
```

## Q5

```text
En büyük hata sınıfı ne?
```

---

# 36. Failure taxonomy

Final sonrası aday kategoriler:

```text
OCR miss
OCR symbol error
rotated text
R/Ø confusion
count parsing
depth/THRU
leader-target binding
target localization
view ownership
physical meaning
unit/value
abstention
overclaim
evidence-induced error
```

---

# 37. Final rapor kapsamı

Her arm:

```text
D
V
VE
```

şu düzeylerde raporlanmalı:

```text
page
predicate
aggregate
```

Ayrıca:

```text
actual inference count
failed cells
blocked cells
transport failures
parse failures
latency
```

varsa yaz.

---

# 38. Gold sınırlaması

Rapor açıkça söylemeli:

```text
annotator = agent
review_status = provisional
small corpus
not human-certified engineering truth
not broad industrial benchmark
```

Yanlış iddia:

```text
“technical drawing accuracy = X%”
```

Doğru:

```text
“SEMREAD-001B'nin 10 sayfalık corpus'unda...”
```

---

# 39. Sonuca göre reader yönü

## D en iyi ise

```text
deterministic observe/bind/meaning güçlendir
VLM yalnız ambiguity resolver
```

## V en iyi ise

```text
raw vision semantic reader
+
strict deterministic validation
```

## VE en iyi ise

```text
deterministic perception
→ evidence graph
→ VLM semantic resolver
→ deterministic validation
```

## VE karışık ise

Evidence tiplerini ayır:

```text
OCR useful?
primitive harmful?
overlay clutter?
wrong anchors?
```

Amaç:

```text
more evidence
```

değil:

```text
reliable evidence
```

---

# 40. Finalden sonra evaluator engineering durmalı

P6 sonuçlandıktan sonra evaluator'a yeni özellik eklemeyi bırak.

Asıl production reader'a dön.

Her reader değişikliği:

```text
measured failure class
→ explicit hypothesis
→ general fix
→ unit test
→ adversarial test
→ regression
```

sırasıyla yapılmalı.

---

# 41. Yeni bağımsız holdout

001B sonuçlarına bakıp reader değiştirildikten sonra mevcut frozen set artık gerçek holdout değildir.

Yeni benchmark:

```text
SEMREAD-001C
```

veya eşdeğer yeni corpus gerekir.

İçerik:

```text
unseen sources
new drawing styles
vector + raster
multi-view
rotated dimensions
count patterns
depth / THRU
R / Ø
```

Mümkünse human-reviewed subset ekle.

---

# 42. Ürün hattına dönüş

Semantic candidate doğrudan CAD command olmamalı.

Araya:

```text
semantic claim graph
→ geometric/dimensional constraints
```

katmanı girer.

Örnek:

```text
Ø10
leader → circle g17
```

şuna dönüşür:

```text
diameter(g17) = 10 mm
```

Sonra constraint solver.

---

# 43. Belirsizlik üründe nasıl davranmalı

Bir ölçü iki target'a bağlanabiliyorsa:

```text
guess
```

yapma.

UI kullanıcıya sorar:

```text
“Ø10 hangi feature'a ait?”
```

Kullanıcı kararı yeni revision üretir.

---

# 44. Multi-view sonraki aşama

001B ölçümü bitmeden başlamayın.

Sonraki ürün problemi:

```text
view detection
projection frame
same feature across views
hidden line semantics
dimension ownership
```

---

# 45. CAD planner sonraki aşama

Uzun vadeli yön:

```text
constraint state
→ typed operation grammar
→ validator
→ compiler
```

Serbest model JSON'u production truth olmamalı.

---

# 46. STEP doğrulaması

Yalnız:

```text
valid solid
bbox
volume
reopen
```

yeterli değildir.

Feature-level audit:

```text
hole count
hole diameter
position
depth
pocket
profile
arc
pattern
```

gerekir.

---

# 47. User correction loop

UI şu bilgileri göstermeli:

```text
what was read
where it was bound
what meaning was inferred
why uncertain
```

Düzeltme:

```text
decision revision
```

üretmeli.

Yeni revision eski build'i stale yapmalı.

---

# 48. Commit planı

Önerilen sıradaki commits:

```text
1. frozen-views-exercise canonical gold (10/10)
2. P3 closure — all verify + SEMREAD + full pytest
3. D reuse evaluation + acceptance snapshot
4. clean-clone reproducibility
5. complete FREEZE.json binding
6. P5 atomic freeze
7. V/VE final matrix
8. final evaluation/report
9. failure taxonomy + reader next-step plan
```

---

# 49. Commit kanıt formatı

Her commit/handoff:

```text
what changed
why
exact test command
pass/fail count
coverage before/after
budget before/after
gold_content_identity
artifact hashes
gate changes
next single step
```

“tests passed” tek başına yeterli değil.

---

# 50. Dokümantasyon borcu

`docs/PLAN-10.md` artık 7/10 başlangıcını anlatıyor ve güncel repo 9/10'a geldi.

Bu yeni plan yeni agent için güncel authority olmalı.

Ama root ürün planını şimdi geniş çapta refactor ederek gold işini geciktirme.

P5/P6 milestone sonrası:

```text
root PLAN.md
README status
test count
semantic-reader result
```

güncellenir.

---

# 51. CI borcu

Güncel HEAD için dış CI sonucu kanıtlanmış değil.

Şimdilik test kanıtı local repo kayıtlarına dayanıyor.

Daha sonra minimum CI:

```text
SEMREAD unit tests
manifest check
```

çalıştırmalı.

Full suite nightly olabilir.

Şimdi öncelik değil.

---

# 52. Risk register

## R1 — son gold sayfasında over-annotation

Mitigation:

```text
narrow scope
exclude unclear claims
```

## R2 — düşük çözünürlükte yanlış symbol okuma

Mitigation:

```text
visual zoom
cross-context evidence
no guess
```

## R3 — benchmark engineering uzaması

Mitigation:

```text
views → 10/10 → freeze → inference
```

## R4 — frozen leakage

Mitigation:

```text
annotation only
no production tuning
```

## R5 — provisional gold

Mitigation:

```text
vision evidence
independent scale where available
future human review
```

## R6 — final retry bias

Mitigation:

```text
immutable attempts
budget before send
```

---

# 53. Agent için YAPMA listesi

Şunlardan birini yapacaksan dur:

```text
freeze öncesi V/VE inference
views sayfasına özel production heuristic
hardcoded coordinates
OCR çıktısını doğrudan truth kabul etmek
gold value-based matching
reference STEP'i reader'a vermek
SCALE note'tan px/mm üretmek
evaluated Ø/R claim'i scale root yapmak
unclear leader'ı zorla scorable yapmak
failed final attempt silmek
budget resetlemek
finalden sonra evaluator threshold değiştirmek
10 sayfayı genel engineering accuracy diye sunmak
```

---

# 54. P3 checklist — güncel

- [x] dev-plate-pocket
- [x] dev-flange-book
- [x] dev-flange-elbow
- [x] dev-drawing-2
- [x] frozen-exercise-51
- [x] frozen-exercise-12
- [x] frozen-exercise-17
- [x] frozen-exercise-13
- [x] frozen-enclosure
- [ ] frozen-views-exercise
- [ ] 10/10 manifest
- [ ] 10/10 regenerate
- [ ] 10/10 verify
- [ ] final stable gold_content_identity
- [ ] all raster vision audit
- [ ] no corroboration cycle
- [ ] SEMREAD tests pass
- [ ] full pytest pass
- [ ] D reuse evaluation
- [ ] B02 closed
- [ ] B07 closed
- [ ] B05/B06 intentionally open
- [ ] budget remains 0/30

---

# 55. P5 checklist

- [ ] separate clean clone
- [ ] no hidden `out/` dependency
- [ ] regenerate all 10
- [ ] exact reference hashes
- [ ] same final gold identity
- [ ] producer identity bound
- [ ] evaluation identity bound
- [ ] candidate schema bound
- [ ] match policy bound
- [ ] preprocessing identity bound
- [ ] model/digest/runtime bound
- [ ] generation settings bound
- [ ] D attempts bound
- [ ] D artifact hashes bound
- [ ] budget snapshot
- [ ] lifecycle snapshot
- [ ] matrix snapshot
- [ ] FREEZE.json complete
- [ ] atomic freeze pass
- [ ] P5 closed

---

# 56. V/VE preflight checklist

- [ ] P5 closed
- [ ] gold 10/10
- [ ] D valid_reuse 10
- [ ] V to_run 10
- [ ] VE to_run 10
- [ ] budget 0/30
- [ ] orphan 0
- [ ] exact model
- [ ] exact model digest
- [ ] exact runtime
- [ ] supported structured output
- [ ] raw V/VE image hashes identical
- [ ] prompt/task identity controlled
- [ ] generation settings controlled
- [ ] leak audit clean

---

# 57. Final measurement checklist

- [ ] 20 VLM cells resolved
- [ ] every actual send accounted
- [ ] failures preserved
- [ ] no cherry-pick
- [ ] selected attempts recorded
- [ ] artifact hashes checked
- [ ] evaluation identity recorded
- [ ] page metrics
- [ ] predicate metrics
- [ ] recovery/regression
- [ ] localization separate
- [ ] target binding separate
- [ ] overclaim/abstention
- [ ] latency/failure reporting
- [ ] provisional-gold limitation
- [ ] immutable final report

---

# 58. SEMREAD-001B başarı tanımı

Başarı:

```text
VE wins
```

değildir.

Başarı:

```text
reproducible truth
+
controlled experiment
+
bounded inference
+
immutable attempts
+
honest evaluator
+
field-level result
+
actionable failure taxonomy
```

D, V veya VE kazanabilir.

Üçü de geçerli sonuçtur.

---

# 59. Şimdiki tek teslim

Başka agent bu planı aldığında ilk görev:

```text
frozen-views-exercise canonical gold
```

Teslim raporunda yaz:

```text
page dimensions
scorable claim count
excluded ambiguous claims
printed callouts
target binding evidence
target_box_norm / observation ids
independent scale varsa datum
corroboration kind
vision evidence
exhaustiveness
reference hash
new gold_content_identity
coverage = 10/10
SEMREAD test result
budget = 0/30
```

---

# 60. Son talimat

Şu anda:

```text
model çağırma
reader tuning yapma
new evaluator feature ekleme
CAD/planner/UI işine dağılma
```

Önce yalnız:

```text
frozen-views-exercise
```

ile:

```text
9/10 → 10/10
```

Sonra:

```text
verify all
full tests
reuse D
clean clone
freeze once
measure once
```

Ardından gerçek ölçüm ne diyorsa onu geliştir.
