# PLAN.md — drawingto3d / SEMREAD-001B

## 7/10 canonical gold sonrası uygulama planı

**Tarih:** 2026-10-04  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `c5d788af1fe52bee468e2abb794c6b33e2148e5e`  
**Son substantive gold commit:** `bc9cd5106aac42e75e0fd0f78634d3bf27d75b04`  
**Canonical gold:** **7/10**  
**Ex13 sonrası SEMREAD test kaydı:** **183 passed**  
**Son kayıtlı full-suite:** **1188 passed** (`b092acc...`; ex13 öncesi)  
**Gerçek V/VE inference:** **başlamadı**  
**Inference budget:** **0/30** korunmalı.

---

# 1. Tek hedef

Şu anda yeni ürün özelliği ekleme.

Önce deney sistemini tamamla:

```text
7/10 canonical gold
→ dev-flange-book
→ frozen-exercise-51
→ frozen-views-exercise
→ 10/10
→ tüm referansları yeniden üret ve doğrula
→ D sonuçlarını reuse ederek değerlendir
→ clean-clone reproducibility
→ P5 freeze
→ V/VE preflight
→ 20 final V/VE hücresi
→ immutable evaluation
→ hata sınıfları
→ yalnız ölçülen probleme göre reader geliştirmesi
→ sonra ürün hattına dön
```

Şu anki darboğaz:

```text
3 eksik canonical gold sayfası
```

Benchmark altyapısını gereksiz büyütme.

---

# 2. Ürünün asıl amacı

Nihai hedef:

> M1 / 16 GB sınıfı yerel makinede, çalışma zamanında bulut servisine ihtiyaç duymadan, farklı teknik çizim PDF/PNG/JPG dosyalarını okuyup güvenilir 3D STEP üretmek; belirsiz veya yanlış okunan yerlerde kullanıcıya çizimin üzerinde düzeltme yaptırmak.

Tam ürün zinciri:

```text
source drawing
→ observe
→ bind
→ semantic meaning
→ uncertainty / abstention
→ constraints
→ solved geometry
→ typed CAD plan
→ deterministic CAD
→ STEP
→ reopen / feature audit
→ user correction
→ revision
```

SEMREAD-001B bunun yalnız semantic-reading bölümünü ölçüyor.

Benchmark ürün değildir.

---

# 3. Güncel durum

## 3.1 Canonical gold

Manifestte izlenen 7 sayfa:

```text
dev-plate-pocket
dev-drawing-2
dev-flange-elbow
frozen-exercise-12
frozen-exercise-17
frozen-exercise-13
frozen-enclosure
```

Eksik:

```text
dev-flange-book
frozen-exercise-51
frozen-views-exercise
```

Güncel gold identity:

```text
40a9569103345dff06679a7da96a151dc61b82fe474ca9c1ca7d381655170d17
```

Bu kimlik 7/10 durumuna aittir ve yeni gold eklendikçe değişmesi normaldir.

## 3.2 `frozen-exercise-13` kapandı

Tekrar yapma.

Kayıt:

```text
7 Ø/R claim
vision_checked = true
exhaustiveness = predicates
```

Bağımsız scale root:

```text
240.00 mm doğrusal datum
≈709.1 px
≈2.955 px/mm
```

Cross-check'ler:

```text
170 mm ≈ 502 px
50 mm  ≈ 148 px
42 mm  ≈ 124.2 px
30 mm  ≈ 88.7 px
25 mm  ≈ 74 px
10 mm  ≈ 29.5 px
```

Yaklaşık yayılım:

```text
~%0.3
```

`SCALE 1:5` px/mm kaynağı yapılmadı.

`--verify` birebir yeniden üretim verdi.

## 3.3 Test durumu

Ex13 sonrası:

```text
tests/test_semread_001b*.py
183 passed
```

Son full-suite kayıt:

```text
1188 passed
```

ama ex13 öncesindedir.

10/10 milestone'da full suite yeniden koşulmalı.

## 3.4 V/VE

```text
budget = 0/30
```

Freeze öncesi değişmemeli.

---

# 4. Değişmez kurallar

## 4.1 Örneğe özel production code yok

Yasak:

```text
filename
exercise number
page_id
bilinen coordinate
bilinen ölçü
bilinen hole count
frozen page special-case
reference STEP
```

Örneğin:

```python
if "Exercise_51" in path:
    ...
```

yasak.

## 4.2 Gold reader'a sızmaz

Gold / expected answer / reference:

```text
observe
bind
meaning
semantic candidate reader
V prompt
VE prompt
proposal
planner
CAD
```

tarafına girmez.

Yalnız evaluator kullanır.

## 4.3 Frozen tuning verisi değildir

`frozen-exercise-51` ve `frozen-views-exercise`:

```text
gold annotation için incelenebilir
```

ama production heuristic, threshold veya prompt tuning için kullanılamaz.

## 4.4 Raster OCR truth değildir

Raster için:

```text
OCR hint
→ visual adjudication
→ target binding
→ measured target box / valid observation
→ evidence
```

OCR tek başına exact engineering truth değildir.

## 4.5 Yazılı callout truth source'tur

Çizimde:

```text
Ø25
R10
6x Ø6.40
```

yazıyorsa değer çizimden gelir.

Pixel geometry yalnız corroboration olabilir.

## 4.6 Circular corroboration yasak

Geçersiz:

```text
Ø20 → Ø22 üzerinden scale
Ø22 → Ø20 üzerinden scale
```

Independent scale root:

```text
evaluated Ø/R claim setinin dışındaki datum
```

olmalı.

Bağımsız datum yoksa:

```text
corroboration.kind = none
```

kullan.

## 4.7 `SCALE 1:n` px/mm değildir

Raster yeniden boyutlandırılmış olabilir.

Başlık bloğundaki scale note tek başına pixel calibration değildir.

## 4.8 Belirsizlikte uydurma yok

Leader çözülemiyorsa:

```text
claim'i scorable gold dışında bırak
```

ve gerekçe yaz.

## 4.9 Reference STEP yalnız evaluator

Üretim/reader/planner yoluna girmez.

## 4.10 Geçmişi tahrip etme

Yasak:

```text
git reset --hard
git clean -fd
attempt silme
budget reset
failed result overwrite
```

---

# 5. Deney sözleşmesi

## D

```text
observe
→ bind
→ meaning
→ deterministic candidate adapter
```

Model çağrısı yok.

## V

```text
yalnız raw full-page
```

## VE

```text
V ile byte düzeyinde aynı raw full-page
+
observation overlay
+
addressable observation table
```

Observation table:

```text
id
kind
text
value
unit
region
```

Gold veya deterministic final decision içermez.

## Kontrollü kalanlar

V ve VE'de aynı:

```text
model
model digest
runtime
candidate schema
task
generation settings
raw page bytes
evaluator
match policy
```

Tek deneysel fark:

```text
evidence
```

---

# 6. Budget

Toplam:

```text
30
```

Dağılım:

```text
dev max   = 10
final max = 20
```

Final matrix:

```text
10 pages × 2 VLM arms = 20
```

P5 kapanana kadar:

```text
0/30
```

korunmalı.

Gerçek request gönderildiyse timeout/transport/parse/failed-gate de budget harcar.

Gönderilmeyen preflight retleri inference değildir.

---

# 7. Kesin çalışma sırası

```text
A. dev-flange-book
B. frozen-exercise-51
C. frozen-views-exercise
D. 10/10 verification
E. D reuse evaluation
F. acceptance snapshot
G. clean-clone reproducibility
H. complete FREEZE.json bindings
I. atomic P5 freeze
J. V/VE preflight
K. final 20-cell run
L. immutable evaluation
M. error taxonomy
N. semantic reader improvement
O. next independent benchmark
P. product integration
```

---

# 8. AŞAMA A — `dev-flange-book`

**Sıradaki tek somut iş budur.**

Kaynak:

```text
examples/pdf with steps/8/Flange.PNG
```

Split:

```text
development
```

Eski corpus probe bilgisi:

```text
~615 primitive
~29 OCR text
OCR gürültülü
```

Geçmiş OCR hint'i yaklaşık:

```text
6x Ø6.40 ... 15.00
```

Bu yalnız discovery hint'idir.

Gold değildir.

## 8.1 Görsel adjudication

Her olası callout için:

```text
printed text
leader
arrowhead
target geometry
view ownership
```

görsel doğrulanmalı.

## 8.2 Semantik alanlar

Çizim açıkça destekliyorsa:

```text
form
size
count_printed
termination
depth
target binding
representation
```

gold'a girer.

Şekle bakarak şunları uydurma:

```text
physical = hole
THRU
blind
counterbore
countersink
depth
```

## 8.3 `6x Ø6.40 ... 15.00`

Özellikle kontrol et:

```text
6x gerçekten basılı mı?
Ø6.40 açık mı?
15.00 hangi işaretle ilişkili?
depth symbol var mı?
```

Depth simgesi/metni yoksa:

```text
15.00 = depth
```

diye yazma.

## 8.4 Target binding

Primitive güvenilir ise:

```text
target_observation
```

kullan.

Güvenilir değilse:

```text
target_box_norm
```

ölç.

## 8.5 Raster evidence

Spec:

```text
vision_checked = true
```

Her scorable claim:

```text
source_evidence içinde vision
```

taşımalı.

## 8.6 Scale

Başlık scale notundan çıkarma.

Gerekirse independent linear datum kullan.

Bulunamazsa:

```text
corroboration.kind = none
```

geçerli.

## 8.7 Exhaustiveness

Yalnız gerçekten doğrulanan scope'u yaz:

```text
predicates
regions
```

Gerekmedikçe `full_page` kullanma.

## 8.8 Standard chain

```text
tracked spec
→ gold_regions
→ reference
→ check_reference
→ manifest --write
→ manifest --check
→ manifest --verify --page dev-flange-book
```

## 8.9 Kabul

Tamamlandığında:

```text
coverage = 8/10
budget  = 0/30
```

---

# 9. AŞAMA B — `frozen-exercise-51`

Kaynak:

```text
examples/pdf with steps/1/Exercise_51.PNG
```

Split:

```text
frozen
```

Bu sayfa tuning verisi değildir.

## 9.1 Workflow

```text
visual read
→ target binding
→ measured box / observation
→ source evidence
→ optional independent corroboration
→ tracked spec
→ regenerate
→ verify
```

## 9.2 Dikkat noktaları

```text
rotated text
dimension line / object line karışması
leader crossing
multi-view ownership
small Ø symbol
R vs number ambiguity
count prefix
depth symbol
```

## 9.3 Production code değiştirme

Bu sayfa kötü okunuyor diye:

```text
raster.py
observe.py
bind.py
meaning.py
semantic_candidate_reader.py
```

üzerinde target-specific değişiklik yapma.

Bu tur annotation turudur.

Generic evaluator bug bulunursa düzeltilebilir; tüm mevcut gold regression'ları koşulur.

## 9.4 Kabul

```text
coverage = 9/10
budget = 0/30
```

---

# 10. AŞAMA C — `frozen-views-exercise`

Kaynak:

```text
examples/Teknik Resim Görünüş Çıkarma Örnekleri 1 - Makine Eğitimi.jpg
```

Bilinen çözünürlük:

```text
~736 × 1041
```

Düşük çözünürlük nedeniyle zor sayfadır.

## 10.1 Fazla claim hedefleme

Amaç:

```text
maksimum claim sayısı
```

değil.

Amaç:

```text
güvenilir scorable gold
```

## 10.2 Unclear symbol

Şunlarda exact gold yazma:

```text
R mi Ø mü?
8 mi 3 mü?
20 mi 28 mi?
hangi view target?
hangi arc/hole?
```

## 10.3 Narrow scope kabul

Dar `predicates` veya `regions` scope dürüst olabilir.

Çözülemeyen leader'ı dışla ve not yaz.

## 10.4 Kabul

```text
coverage = 10/10
budget = 0/30
```

---

# 11. Her gold sayfasında standart workflow

```text
1. inspect
2. visual adjudication
3. tracked spec
4. gold-src
5. reference
6. strict validation
7. manifest --write
8. manifest --check
9. page --verify
10. SEMREAD tests
11. commit
```

Kanonik truth:

```text
eval/semread_001b_gold/specs/
```

Generated `out/` truth source değildir.

---

# 12. `gold_regions` warning

Ex13 sırasında measured-box claim'lerde bilgilendirici warning görüldü.

Şu anda gold zincirini bloklamıyor.

Sırf warning metni için 10/10 işini durdurma.

Eğer gerçekten automation'ı bloklayan generic bug olduğu kanıtlanırsa düzelt.

Page-specific workaround yazma.

---

# 13. 10/10 kapanış kapısı

Kalan üç sayfa sonrası:

## 13.1 Coverage

```text
10 source
10 tracked spec
10 generated reference
10 manifest entry
```

## 13.2 Spec validity

Her spec:

```text
scope
exhaustiveness
unique claim ids
target
evidence
source_evidence
```

bakımından geçerli.

## 13.3 Raster

Her raster:

```text
vision_checked = true
```

Her raster claim:

```text
vision evidence
```

taşımalı.

## 13.4 Measured boxes

```text
finite
ordered
inside page
reason documented
```

## 13.5 Corroboration

Yasak:

```text
self-scale
A→B evaluated size
B→A
```

## 13.6 Regeneration

Tüm 10 sayfa:

```text
tracked spec
→ regenerate
→ exact reference hash match
```

## 13.7 Manifest determinism

Aynı içerik:

```text
same manifest bytes
same gold_content_identity
```

üretmeli.

## 13.8 Tests

Önce:

```text
tests/test_semread_001b*.py
```

Sonra milestone'da:

```bash
pytest -q
```

0 fail.

1188 sayısı mutlak hedef değildir; yeni testler eklenmiş olabilir.

---

# 14. D kolu

D mevcut:

```text
10/10
0 inference
```

Önce reuse et.

Reuse şartları:

```text
producer identity
input identity
source hash
prepared page identity
schema
final state
artifact hash
```

uyumlu olmalı.

Production identity değişmediyse gereksiz D rerun yapma.

---

# 15. Acceptance snapshot

10/10 sonrası durum kaydı:

```text
budget
lifecycle
matrix
evaluation
evidence chain
```

Beklenen:

```text
D = 10 final/reuse
V = 10 to_run
VE = 10 to_run
budget = 0/30
gold = 10/10
orphan = 0
B02 closed
B07 closed
B05 open
B06 open
```

B05/B06 V/VE ölçülmeden kapanmamalı.

---

# 16. Clean-clone reproducibility

Mevcut repo üzerinde clean/reset yapma.

Ayrı fresh clone kullan.

Fresh clone:

```text
tracked repo
→ corpus preparation
→ observations
→ gold-src
→ references
```

üretebilmeli.

Her sayfa:

```text
regenerated sha256
==
manifest reference_sha256
```

olmalı.

`gold_content_identity` aynı kalmalı.

Şunlara bağımlılık olmamalı:

```text
old out/
scratch files
absolute paths
hand-edited generated gold
```

---

# 17. FREEZE.json

Final deney sözleşmesini bağlamalı.

Minimum:

```text
schema
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
model
expected model digest
runtime
generation settings
D selected attempts
D artifact hashes
D evaluation run id
budget snapshot
lifecycle snapshot
matrix snapshot
```

Timestamp semantic identity'ye girmemeli.

---

# 18. Atomic P5 freeze

Tek freeze işlemi:

```text
10/10 coverage
+
manifest consistency
+
source/spec/reference hashes
+
all 10 regeneration proof
+
gold_content_identity
+
complete freeze bindings
```

kanıtlamalı.

Başarı:

```text
P5 CLOSED
```

---

# 19. Freeze sonrası kilit

Final inference öncesi değiştirme:

```text
corpus
gold
prompt
schema
model
digest
runtime contract
settings
preprocessing
match policy
numeric tolerance
ambiguity policy
evaluation semantics
```

Bug varsa:

```text
old freeze invalid
→ fix
→ new identity
→ refreeze
```

Geçmiş silinmez.

---

# 20. V/VE preflight

İlk gerçek call öncesi:

```text
gold 10/10
P5 closed
D valid reuse 10
V to_run 10
VE to_run 10
budget 0/30
orphan 0
```

Her page:

```text
sha256(V image-1)
==
sha256(VE image-1)
```

Model:

```text
name
digest
runtime
structured-output capability
settings
```

uyumlu olmalı.

Mismatch varsa send etme.

Leak check:

```text
gold sentinel
gold filename
expected answer
reference-specific label
```

bulmamalı.

---

# 21. Final V/VE run

```text
10 V
10 VE
=
20 final real calls
```

Her request öncesi:

```text
budget reserve
attempt record
prediction input identity
sending state
```

kalıcı.

Final disposition:

```text
valid_result
failed_attempt
blocked
```

Failed result silinmez.

“İyi cevap gelene kadar retry” yasak.

---

# 22. Evaluation

Candidate ↔ gold eşleştirme:

```text
region/source relationship
```

ile yapılır.

Expected numeric value matching için kullanılmaz.

Ambiguous near-tie semantic score dışı kalır.

Ayrı raporla:

```text
localization_match_rate
semantic_field_accuracy
target_binding_accuracy
overclaim
abstention
false_positive
unscorable_extra_candidate
```

Predicate fields:

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

D karşılaştırması:

```text
recovered
regressed_wrong
regressed_abstain
net_correct_gain
scorable
```

---

# 23. Bilimsel sorular

Final sonuç şu soruları cevaplamalı:

```text
V, D'den daha mı iyi?
VE, V'den daha mı iyi?
Evidence hangi alanı iyileştiriyor?
Evidence hangi alanı bozuyor?
En büyük hata sınıfı hangisi?
```

Failure taxonomy:

```text
OCR
rotated text
R/Ø
count
depth/THRU
leader binding
target localization
view ownership
physical semantics
unit
overclaim
abstention
```

---

# 24. Final rapor

Her arm:

```text
D
V
VE
```

için:

```text
page metrics
field metrics
aggregate
```

raporlanmalı.

Ayrıca:

```text
actual inference count
failed cells
blocked cells
transport errors
parse errors
latency
```

varsa yaz.

Gold sınırlamaları açık:

```text
annotator = agent
review_status = provisional
small corpus
not independent industrial benchmark
not human-certified ground truth
```

“Genel technical drawing accuracy” iddiası yok.

---

# 25. Finalden sonra evaluator'ı kurcalama

Sonuç kötü diye:

```text
threshold büyütme
scope değiştirme
ambiguous margin oynama
claim çıkarma
```

yapma.

Gerçek evaluator bug varsa yeni evaluation version aç.

Eski sonuç immutable kalır.

---

# 26. Semantic reader geliştirme yönü

## D en iyi

Deterministic path'i güçlendir.

VLM ambiguous resolver olabilir.

## V en iyi

Raw vision + strict validation yönü değerlendir.

## VE en iyi

Muhtemel hibrit:

```text
deterministic perception
→ evidence graph
→ VLM semantic resolver
→ deterministic validation
```

## VE karışık

Evidence tiplerini ayrı analiz et:

```text
OCR useful?
primitive harmful?
overlay clutter?
bad anchors?
```

Amaç daha fazla evidence değil, güvenilir evidence.

---

# 27. Yeni holdout

001B sonuçlarına göre reader değiştikten sonra 001B frozen artık tam bağımsız holdout değildir.

Yeni tur:

```text
SEMREAD-001C
```

gibi yeni corpus kullanmalı.

İçerik:

```text
unseen sources
different styles
vector + raster
multi-view
rotated dimensions
count
depth/THRU
R/Ø
```

Mümkünse human-reviewed subset.

---

# 28. Ürüne dönüş

Semantic candidate doğrudan CAD operation olmasın.

Önce:

```text
semantic claim
→ geometric/dimensional constraint
```

Örnek:

```text
Ø10
leader → circle g17
```

şuna dönüşür:

```text
diameter(g17) = 10 mm
```

Sonra solver.

Belirsizlik varsa user question.

---

# 29. Multi-view daha sonra

P6 bitmeden başlama.

Gelecek:

```text
view detection
projection frames
feature identity across views
hidden line semantics
dimension ownership
```

---

# 30. Planner daha sonra

Serbest plan JSON yerine uzun vadede:

```text
constraint state
→ typed operation grammar
→ validator
→ compiler
```

Model proposer olabilir; truth değildir.

---

# 31. STEP validation daha sonra

Valid solid / bbox / volume tek başına yeterli değil.

Feature audit:

```text
hole count
diameter
position
depth
pocket
profile
arc
pattern
```

gerekir.

---

# 32. User correction

Her decision revisioned.

Yeni karar:

```text
old build = stale
```

yapmalı.

UI kullanıcıya:

```text
ne okundu
nereye bağlandı
ne anlama geldi
neden belirsiz
```

göstermeli.

---

# 33. Test stratejisi

Her gold commit:

```text
page verify
manifest check
SEMREAD tests
```

10/10 milestone:

```text
all SEMREAD
full pytest
```

Freeze:

```text
clean-clone regeneration
freeze tests
```

Final inference sırasında code değiştirme.

---

# 34. Commit stratejisi

Önerilen:

```text
1. dev-flange-book canonical gold (8/10)
2. frozen-exercise-51 canonical gold (9/10)
3. frozen-views-exercise canonical gold (10/10)
4. P3 closure: verify all + full suite
5. clean-clone reproducibility
6. complete freeze bindings
7. P5 freeze
8. V/VE final matrix
9. final evaluation/report
```

---

# 35. Handoff standardı

Her milestone:

```text
CURRENT STATE
WHAT CHANGED
EVIDENCE
OPEN GATES
NEXT SINGLE STEP
```

Ayrıca:

```text
exact tests
pass count
budget
coverage
gold identity
```

yaz.

---

# 36. Root PLAN.md borcu

Repo root `PLAN.md` hâlâ eski ürün planını anlatıyor.

Şimdilik kalan 3 gold'u geciktirmek için dokümantasyon refactor yapma.

P5/P6 sonrasında root plan authority ve README güncellenmeli.

---

# 37. CI borcu

Gözlenen HEAD'de GitHub workflow/status kanıtı yok.

Lokal test kayıtları kullanılıyor.

İleride minimum CI:

```text
semantic unit tests
manifest check
```

Full suite nightly olabilir.

Şu an öncelik değil.

---

# 38. Riskler

## Benchmark engineering uzaması

Çözüm:

```text
3 gold
→ 10/10
→ freeze
→ inference
```

## Provisional gold

Çözüm:

```text
vision evidence
narrow scope
independent corroboration
human review later
```

## Frozen leakage

Çözüm:

```text
no production tuning
new holdout after 001B changes
```

## Raster overconfidence

Çözüm:

```text
printed truth
pixel corroboration
no scale-note calibration
```

## Retry bias

Çözüm:

```text
immutable attempts
budget before send
```

---

# 39. YAPMA listesi

```text
freeze öncesi V/VE inference yapma
dev-flange-book special-case yazma
ex51 special threshold yazma
views için hardcoded coordinate yazma
gold value ile matching yapma
reference STEP'i reader'a verme
SCALE 1:n'den px/mm çıkarma
evaluated Ø/R claim'i scale root yapma
unclear leader'ı zorla scorable yapma
failed final attempt silme
budget resetleme
finalden sonra evaluator threshold oynama
10 sayfayı genel industry accuracy diye sunma
```

---

# 40. ŞİMDİKİ TEK GÖREV

```text
dev-flange-book canonical gold
```

Başlangıç snapshot:

```text
git status
git log -5
manifest --check
budget
```

Sonra yalnız `dev-flange-book`.

Production reader code'a dokunma.

---

# 41. `dev-flange-book` teslim raporu

Tamamlandığında:

```text
page frame
scorable claim count
printed callouts
excluded ambiguous callouts
target binding per claim
target_box_norm / observation ids
independent scale varsa datum
corroboration kinds
vision evidence
exhaustiveness
reference hash
manifest identity
coverage = 8/10
SEMREAD test result
budget = 0/30
```

---

# 42. P3 checklist

- [x] dev-plate-pocket
- [x] dev-drawing-2
- [x] dev-flange-elbow
- [x] frozen-exercise-12
- [x] frozen-exercise-17
- [x] frozen-exercise-13
- [x] frozen-enclosure
- [ ] dev-flange-book
- [ ] frozen-exercise-51
- [ ] frozen-views-exercise
- [ ] 10/10 manifest
- [ ] 10/10 regenerate
- [ ] 10/10 verify
- [ ] stable final gold_content_identity
- [ ] all raster vision_checked
- [ ] no circular corroboration
- [ ] SEMREAD tests pass
- [ ] full pytest pass
- [ ] D reuse confirmed
- [ ] B02 closed
- [ ] B07 closed
- [ ] B05/B06 intentionally open
- [ ] budget 0/30

---

# 43. P5 checklist

- [ ] separate clean clone
- [ ] no hidden out cache dependency
- [ ] regenerate 10/10
- [ ] exact reference hashes
- [ ] same gold_content_identity
- [ ] producer identity bound
- [ ] evaluation identity bound
- [ ] candidate schema bound
- [ ] match policy bound
- [ ] preprocessing bound
- [ ] model/digest/runtime bound
- [ ] settings bound
- [ ] D selected attempts bound
- [ ] D artifact hashes bound
- [ ] budget snapshot
- [ ] lifecycle snapshot
- [ ] matrix snapshot
- [ ] atomic freeze pass
- [ ] FREEZE.json complete
- [ ] P5 closed

---

# 44. V/VE preflight checklist

- [ ] P5 closed
- [ ] gold 10/10
- [ ] budget 0/30
- [ ] D valid reuse 10
- [ ] V to_run 10
- [ ] VE to_run 10
- [ ] orphan 0
- [ ] model exact
- [ ] digest exact
- [ ] runtime exact
- [ ] structured schema supported
- [ ] V/VE raw image hashes identical
- [ ] prompt controlled
- [ ] settings controlled
- [ ] leak check clean

---

# 45. Final measurement checklist

- [ ] 20 VLM cells resolved
- [ ] every send in budget ledger
- [ ] failed attempts preserved
- [ ] no cherry-pick
- [ ] selected attempts recorded
- [ ] artifact hashes verified
- [ ] evaluation identity recorded
- [ ] page metrics
- [ ] field metrics
- [ ] recovery/regression
- [ ] localization separate
- [ ] target binding separate
- [ ] overclaim/abstention
- [ ] split results
- [ ] latency/cost
- [ ] provisional-gold limitation
- [ ] immutable report

---

# 46. Başarı tanımı

SEMREAD-001B'nin başarılı olması:

```text
VE mutlaka kazanacak
```

demek değildir.

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
actionable error taxonomy
```

demektir.

D, V veya VE kazanabilir.

---

# 47. Son ürün rotası

001B sonrası:

```text
semantic reading
→ claim graph
→ constraints
→ multi-view correspondence
→ typed CAD planning
→ deterministic solid
→ STEP
→ feature audit
→ user correction
```

Ürün başarısı:

```text
birkaç örnek STEP üretiyor
```

değil.

Gerçek hedef:

```text
yeni teknik çizimde genel mekanizmalar çalışıyor
+
bilmediğini söylüyor
+
kullanıcı düzeltebiliyor
+
provenance izleniyor
+
3D çıktı feature seviyesinde doğrulanıyor
```

---

# 48. Son talimat

Şu anda:

```text
model çağırma
reader tuning yapma
yeni benchmark özelliği ekleme
CAD/planner/UI işine dağılma
```

Önce:

```text
dev-flange-book
→ frozen-exercise-51
→ frozen-views-exercise
```

ile:

```text
7/10 → 10/10
```

Sonra:

```text
verify once
freeze once
measure once
```

Ardından ölçüm ne diyorsa onu geliştir.

## Bir sonraki tek iş

```text
dev-flange-book canonical gold
```
