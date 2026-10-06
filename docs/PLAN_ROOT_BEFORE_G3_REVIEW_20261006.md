# PLAN.md — drawingto3d / GUIDED-TRANSCRIPTION G2
## Observations → deterministic `CalloutCandidate` adapter
### G1 kapanışı sonrası tek yetkili iş: callout bölgelerini dürüst, kararlı ve kalıcı biçimde üretmek

**Tarih:** 2026-10-06  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Doğrulanan uzak `main` HEAD:** `316518eb8d67c7a4ad81eed59c09e6c59ef4df37`  
**Umbrella ürün planı:** `docs/PLAN-20.md`  
**Yürütme kaydı:** `docs/GUIDED_PROGRESS.md`  
**Mevcut kök `PLAN.md`:** tamamlanmış G1 düzeltme turu 2 görevi  
**Yeni yetkili kapsam:** yalnız **G2**  
**G3 ve sonrası:** kapalı  
**SEMREAD-001D:** PARKED RESEARCH — Round 1 FAIL; dev `4/12`, final `0/20`  
**Model çağrısı:** `0`  
**Ürün hedefi:** kullanıcı doğrulamalı akışla fixed 10-sheet sette geometrik doğru STEP

---

# 0. Yönetici özeti

Repo artık G0 pivotunu ve G1 veri güvenilirliği katmanını tamamlamış durumda:

```text
G0 guided-transcription pivot
→ G1 dört callout modeli
→ persistence / reopen / undo / stale
→ explicit reconfirm
→ etkin kontur üzerinde target doğrulaması
→ bağımsız review/fix turu 1
→ bağımsız review/fix turu 2
→ G1 tekrar kabul
```

Current kanıt:

```text
HEAD                         316518eb8d67c7a4ad81eed59c09e6c59ef4df37
G1R2 callout tests           54 passed
G1R2 focused                 98 passed
G1R2 selected combined       198 passed / 80.05 s / EXIT=0
review probes                EXIT=0
full current-tree pytest     bu kanıtta yok; iddia etme
external GitHub statuses     yok
```

`docs/GUIDED_PROGRESS.md` sıradaki işi açıkça şöyle bırakıyor:

```text
G1 complete
G2+ not opened
next if authorized = Observations → CalloutCandidate adapter
```

Bu plan G2'yi açar; G3'ü açmaz.

G2'nin amacı:

```text
observe(source)
      ↓
Observations.texts
      ↓
pure deterministic adapter
      ↓
CalloutCandidate[] + diagnostics
      ↓
GuidedStore.create persistence
      ↓
reopen = same candidate identities/regions/provenance
```

G2 metni anlamaz, target bağlamaz, UI çizmez, parser çalıştırmaz, CAD üretmez.

---

# 1. Current sözleşmeler

`src/drawingto3d/callout_models.py` şu dört katmanı hazır tutuyor:

```text
CalloutCandidate         = machine observation
TranscriptionDecision    = user's verbatim text
SemanticParse            = computed result
CalloutTargetDecision    = user-confirmed geometry target
```

`CalloutCandidate` current alanları:

```text
id
source_digest
page_index
region              # normalized 0..1
crop_region         # normalized 0..1, region'u kapsar
source_kind         # vector_text | observation | raster_region | manual
observation_ids[]
detector_version
geometry_version
machine_text_hint?  # hint only
```

Validatorlar finite/0..1/pozitif alan/crop coverage kurallarını zaten zorlar. İkinci candidate schema yaratma.

---

# 2. G1'den korunacak değişmezler

G2 şu davranışları bozamaz:

```text
raw user text birebir
normalized_text server-derived
transcription revision ayrı
parse freshness computed
confirmation için exact parsed record
server-pinned target fields
explicit single-use reconfirm
geometry/context change → target stale
corrected contour = target validation authority
removed endpoint silent rebind yok
undo fake confirmation event yaratmaz
reopen freshness event yaratmaz
late build yeni decisions'a bağlanmaz
stale STEP current sunulmaz
```

---

# 3. G2 kesin scope

```text
G2.0 kickoff + baseline
G2.1 pure observations adapter
G2.2 deterministic identity + dedup + diagnostics
G2.3 GuidedStore.create integration
G2.4 vector + raster + honest-none regression
G2.5 reopen + legacy-session behavior
G2.6 final regression + progress/handoff
```

Şunlar bu görevde yok:

```text
G3 overlay/crop/transcription UI
G4 real semantic parser
G5 target proposal
G6 target confirmation UI work
G7 callout→CAD compiler
G8 build-readiness workflow
G9 Plate guided golden path
G10–G13 10-sheet program
```

---

# 4. Current observation contract

`Observations`:

```text
source
frame
sheet_frame
text_placement
paths[]
primitives[]
texts[]
skipped[]
notes[]
```

`TextObservation`:

```text
id
text
value
unit = "mm"   # default olabilir
kind = "text"
count = 1      # default olabilir
bbox
char_range
method = "pdf-text"
confidence
```

**Kritik G2 kuralı:** `value/unit/kind/count` semantic truth değildir. Özellikle default `unit="mm"` ve `count=1` hiçbir semantic user/computed karara terfi etmez.

G2 yalnız şunları kullanır:

```text
text hint
bbox
observation id
method
source/page/frame provenance
```

---

# 5. Vector ve raster kaynak davranışı

Vector PDF:

```text
method = pdf-text
source.sha256 = source_hash(drawing)
source.page = 0
bbox = rendered pixel frame
```

Raster:

```text
observe() → observe_raster()
method = tesseract-tsv
```

Raster OCR phrase üretmezse G2 dürüstçe `[]` üretir; ikinci OCR çağrısı yok.

---

# 6. Yeni modül

Önerilen:

```text
src/drawingto3d/callouts.py
```

Current HEAD'de bu dosya yok.

Sorumluluk yalnız:

```text
Observations → candidate regions
identity
source-kind mapping
exact dedup
diagnostics
deterministic ordering
```

Bu modül GuidedStore/CAD/model/filesystem bağımlılığı taşımasın.

---

# 7. Detector version

Tek kaynak sabit:

```text
CALLOUT_DETECTOR_VERSION = "callout-detector/1"
```

Version değişirse candidate identity değişebilmeli.

---

# 8. Önerilen adapter API

```python
def callout_candidates_from_observations(
    observations,
    *,
    geometry_version: int,
    detector_version: str = CALLOUT_DETECTOR_VERSION,
):
    ...
```

Return küçük computed transport olabilir:

```text
candidates[]
diagnostics[]
detector_version
```

Bu yeni user-decision modeli değildir.

---

# 9. Diagnostics

İlk code set:

```text
invalid_frame
unsupported_page
invalid_bbox_nonfinite
invalid_bbox_area
bbox_outside_frame
unknown_text_method
duplicate_hint_conflict
no_text_observations
```

Invalid observation sessizce “düzeltilmez”.

---

# 10. Pixel → normalized region

```text
x0 = bbox.x / width
y0 = bbox.y / height
x1 = (bbox.x + bbox.w) / width
y1 = (bbox.y + bbox.h) / height
```

Pin örneği:

```text
1000×500 frame
bbox x100 y50 w200 h100
→ [0.1, 0.1, 0.3, 0.3]
```

Önce frame ve bbox validate edilir; sonra normalize edilir.

---

# 11. Region canonicalization

Identity için tek helper kullan. Öneri:

```text
REGION_DECIMALS = 8
```

Aynı canonical region hem stored candidate hem identity payload için kullanılsın. Keyfi farklı `round()` noktaları olmasın.

G2 `crop_region = region` kullanabilir; preview padding G3 işidir.

---

# 12. Source-kind mapping

Method authority:

```text
pdf-text       → vector_text
tesseract-tsv  → raster_region
unknown method → observation + diagnostic
```

Dosya suffix'inden yöntem tahmin etme. Machine adapter `manual` source_kind üretmez.

---

# 13. Machine hint

```text
machine_text_hint = observation.text
```

Raw hint semantic normalize edilmez ve `TranscriptionDecision` oluşturmaz.

---

# 14. Candidate identity

Canonical payload:

```text
source_digest
page_index
canonical_region
detector_version
source_kind
```

Canonical JSON + SHA-256.

Identity'de olmayacaklar:

```text
source path
filename
case id
sample number
text
value/unit/count/kind
confidence
list index
UUID
Python hash()
timestamp
```

Aynı bytes + rename edilmiş path → aynı candidate id. Source digest değişirse id değişir.

---

# 15. Exact dedup

Aynı identity → tek candidate.

Merge:

```text
observation_ids = sorted(unique union)
```

Hints aynıysa koru. Hints farklıysa:

```text
machine_text_hint = None
+ duplicate_hint_conflict
```

Yakın iki kutuyu körlemesine merge etme.

---

# 16. Deterministic output order

Input texts sırası değişse de output order sabit. Öneri:

```text
(y0, x0, y1, x1, source_kind, id)
```

Display `C1/C2` ileride bundan türeyebilir; persisted id display sıra numarası değildir.

---

# 17. BBox validation

Candidate olmadan:

```text
x/y/w/h finite
w > 0
h > 0
x >= 0
y >= 0
x+w <= width
y+h <= height
```

Değilse skip + diagnostic. Clamp yok.

---

# 18. Page support

Current observer page 0 destekliyor.

```text
source.page == 0 → supported
other → explicit unsupported
```

Page numarasını sessizce 0'a çevirme.

---

# 19. Store integration ana kuralı

Current `GuidedStore.create()` zaten `observe(source)` çağırıyor. Adapter aynı `Observations` object'ini kullanmalı.

```text
NO second observe
NO second OCR
NO model call
```

New session:

```text
callout_candidates = adapter result
transcriptions = []
callout_parses = []
callout_targets = []
```

---

# 20. Legacy/reopen policy

New session create→disk→new store reopen candidate kayıtlarını aynen korur.

Legacy callout'suz session load sırasında:

```text
redetect YOK
silent association YOK
file rewrite on read YOK
```

Candidate refresh ayrı gelecek tasarımdır.

---

# 21. G2.0 kickoff

İlk adımlar:

```text
git status --short
git rev-parse HEAD
read docs/GUIDED_PROGRESS.md
read docs/PLAN-20.md
read current root PLAN.md
check AGENTS.md
inspect user/untracked changes
```

Progress'e:

```text
Scope = G2
Current task = G2.1
Initial HEAD = 316518eb...
```

ekle. Önceki G1 kayıtlarını silme.

Current root PLAN G1R2 görevidir. Bu plan root'a kurulacaksa önce mevcut root bytes'ın zaten archive edilip edilmediğini kontrol et; değilse yeni tarihsel kopya oluştur. `docs/PLAN-20.md` overwrite edilmez.

---

# 22. Baseline

Known current evidence selected 198 PASS'tir; full pytest değildir.

Implementer working tree farklıysa önce ilgili baseline'ı yeniden koşmalı. Exact previous combined command progress/commit evidence'dan alınır; dosya listesini hafızadan uydurma.

Minimum baseline:

```text
tests/test_callout_models.py
tests/test_guided_callouts.py
+ recorded G1R2 selected suite
```

---

# 23. G2.1 — Pure adapter tests

Yeni test dosyası önerisi:

```text
tests/test_callout_candidates.py
```

Zorunlu test matrisi:

1. 1000×500 + bbox 100/50/200/100 → `[0.1,0.1,0.3,0.3]`.
2. source_digest/page/observation_ids/detector_version doğru.
3. `pdf-text → vector_text`.
4. `tesseract-tsv → raster_region`.
5. unknown method suffix inference yapmaz.
6. `value/unit/count/kind` semantic record üretmez.
7. adapter input `Observations` mutate etmez.
8. aynı input → aynı id.
9. list order değişimi → aynı ID set + aynı deterministic output order.
10. digest/page/region/version/source-kind tek tek değişince ID ayrılır.
11. source path rename, digest aynı → ID aynı.
12. hint identity'nin parçası değildir.
13. exact duplicate → one candidate + provenance union.
14. duplicate conflicting hints → hint None + diagnostic.
15. nearby non-identical regions → iki candidate.
16. zero-area bbox → reject.
17. NaN/Inf → reject.
18. out-of-frame → reject, clamp yok.
19. invalid frame → empty + diagnostic.
20. empty texts → honest empty + diagnostic.

G2.1 bitmeden store entegrasyonuna geçme.

---

# 24. G2.2 — Identity/dedup hardening

Implement:

```text
canonical_region
canonical identity JSON
SHA-256 id
source-kind resolver
exact dedup
diagnostic collection
deterministic sorting
```

Ek guard:

```text
candidate ID pathında uuid/random/Python hash yok
```

Diagnostics ordering de deterministic olsun.

---

# 25. G2.1/G2.2 acceptance

- pure adapter
- no filesystem/model/OCR call
- correct normalization
- deterministic SHA-256 identity
- path-independent id
- exact dedup only
- invalid bbox diagnostic
- no semantic promotion
- input immutable
- focused tests green


---

# 26. G2.3 — GuidedStore.create entegrasyonu

İlgili dosya:

```text
src/drawingto3d/guided.py
```

Amaç:

```text
new session create
→ existing observe(source)
→ adapter(observations)
→ persist callout_candidates
```

Mevcut create flow minimum değişsin. Candidate producer source path açıp kendi observe çağrısını yapmasın.

---

# 27. G2.3 integration sırası

Pseudo-order:

```text
source bytes persist
observations = observe(source)          # existing
options = drawing_options(observations)
geometry/session metadata initialized
result = adapter(observations, geometry_version=current)
record.callout_candidates = result.candidates
record.callout_detection = optional metadata
atomic save
```

Gerçek current function order'ı okuyup uygula; pseudo-order'a kör patch yapma.

---

# 28. Source digest cross-check

Session source SHA ile:

```text
observations.source.sha256
```

uyuşmalı. Mismatch varsa candidate identity'yi uydurma; açık fail/diagnostic.

---

# 29. G2.3 karar katmanı guard

New session candidate üretince şunlar boş kalmalı:

```text
Decisions.transcriptions
Decisions.callout_targets
callout_parses
```

Public freshness natural olarak:

```text
transcription = missing
parse = missing
target = missing
```

olmalı.

`machine_text_hint` auto transcription değildir.

---

# 30. Create side effects

G2 create sırasında:

```text
STEP/STL build yok
user/transcribe log yok
user/confirm_target log yok
parser event yok
model inference yok
```

Candidate detection base state'tır.

---

# 31. G2.3 real-store testleri

Temp `GuidedStore` ile gerçek create:

```text
candidate list persisted
candidate fields source observations ile tutarlı
public exposes candidate
no transcription
no parse
no target
no build artifact
```

Mock-only test kabul değil.

---

# 32. One-observe guard

Mümkünse yalnız call-count ölçmek için spy:

```text
one GuidedStore.create → observe once
```

Adapter'ın ikinci OCR/observe yapmadığı pinlenir.

---

# 33. Schema/version policy

Current:

```text
CALLOUT_SCHEMA_VERSION = 1
```

Mevcut `CalloutCandidate` alanlarını doldurmak tek başına schema bump gerektirmez.

```text
GEOMETRY_VERSION
```

de sırf G2 başladı diye artırılmaz.

Persisted yapıya yeni zorunlu structural field eklenecekse önce migration etkisini test et.

---

# 34. Detection metadata tercihi

Honest-none ve invalid observation nedenini reopen sonrası kaybetmemek için küçük metadata yararlı:

```text
callout_detection:
  detector_version
  diagnostics[]
```

Ama bu alan migration yüzeyini gereksiz büyütüyorsa önce minimal adapter + tests tamamla. Diagnostics'i `CalloutCandidate` içine semantic alan gibi sıkıştırma.

---

# 35. G2.3 acceptance

- new session candidates persisted
- no user/computed semantic records created
- existing observations reused
- no second observe/OCR
- create revision semantics preserved
- no build/model side effect
- G1 callout tests green

---

# 36. G2.4 — Real vector fixture

Repo içindeki observation okumayı zaten destekleyen bir vector PDF fixture seç.

Selection rules:

```text
normal dev/test drawing
not reference STEP/gold-only asset
not filename-specific product branch
```

Test:

```text
obs = observe(real_pdf)
result = adapter(obs)
```

Eğer `obs.texts` boş değilse candidate beklenir.

---

# 37. Vector fixture assertions

Her candidate için:

```text
source_digest == obs.source.sha256
page_index == 0
region valid 0..1
observation_ids resolve to obs.texts
pdf-text → vector_text
```

Exact dimension value'yu ürün behavior hardcode olarak pinleme.

---

# 38. G2.4 — Raster fixture

Mevcut raster fixture varsa gerçek `observe_raster` yolu kullan.

Tesseract environment yoksa:

```text
BLOCKED_ENV
```

kaydet; synthetic observation testi gerçek raster PASS yerine geçirilmez.

---

# 39. Raster honest-none

OCR phrase çıkmadığında:

```text
candidates = []
```

olmalı. Primitive/circle/line'lardan sahte text box üretme.

---

# 40. OCR confidence policy

Current raster `TextObservation.confidence` var ama `CalloutCandidate` confidence alanı yok.

G2 sırf confidence taşımak için model genişletmesin. Observation ID provenance yeterli.

Low confidence filtering G2 scope değil.

---

# 41. Title-block policy

G2'nin ilk sürümünde semantic title-block classifier ekleme.

```text
all valid text regions can be candidates
```

False positive G3'te kullanıcı ignore ile çözülebilir.

G2'nin hedefi region recall/provenance, semantic precision değil.

---

# 42. Phrase grouping policy

Yakın `4x`, `Ø8`, `THRU` bölgelerini körlemesine birleştirme.

Current observation layer phrase halinde verdiyse onu taşı. Ayrı observation'larsa G2'de ayrı candidate kalabilir.

Phrase grouping ancak ayrı ölçülmüş generic iş olarak ileride açılır.

---

# 43. G2.4 acceptance

- real vector source path exercised
- raster source path exercised veya dürüst BLOCKED_ENV
- honest empty test
- method-based source kind
- no semantic filter
- no reference/gold leakage

---

# 44. G2.5 — Reopen persistence

Test:

```text
store A create
→ candidate snapshot A
→ new GuidedStore same folder
→ load session
→ candidate snapshot B
```

Expected:

```text
A == B
```

IDs, regions, hints, provenance ve detector version korunur.

---

# 45. Load sırasında re-detection YOK

Session load:

```text
observe() çağırıp yeni candidate listesi üretmemeli
```

Persisted base state okunur.

Neden:

```text
silent detector changes could remap existing user decisions
```

---

# 46. Legacy session behavior

Callout layer öncesi veya candidates boş eski oturum:

```text
load succeeds
callout_candidates = []
```

Sırf load nedeniyle:

```text
disk rewrite yok
new candidates yok
auto target/transcription yok
```

---

# 47. Legacy decision association yasağı

Eski sessionda mevcut:

```text
holes
bindings
profile
calibration
```

olsa bile G2 load bunları yeni machine candidate'larla otomatik bağlamaz.

---

# 48. Reopen log guard

Load/public freshness hesapları:

```text
user/transcribe
user/confirm_target
```

event üretmez.

G1R2 log sözleşmesi korunur.

---

# 49. Source unavailable

Existing `geometry_stale/source_unavailable` davranışını G2 değiştirme.

Source artık okunamıyorsa persisted candidate history silinmez; current state mevcut policy üzerinden stale/unavailable kalır.

---

# 50. G2.5 acceptance

- new session exact reopen
- legacy load succeeds
- no re-detection on load
- read does not rewrite file
- no fake user events
- no stale target resurrection

---

# 51. G2.6 — Final regression

Final test layers:

```text
1 new G2 candidate unit tests
2 G2 real-store integration tests
3 test_callout_models
4 test_guided_callouts
5 prior G1R2 focused set
6 prior G1R2 selected combined set + G2 tests
```

Her komut progress'e exact yazılır.

---

# 52. Full pytest policy

G2 `GuidedStore.create` davranışına dokunduğu için full current-tree pytest önerilir.

Koşulamıyorsa:

```text
NOT_RUN
```

veya ortam sorunuysa:

```text
BLOCKED_ENV
```

Selected suite'i full suite diye adlandırma.

---

# 53. Diff hygiene

Zorunlu:

```text
git diff --check
git status --short
```

Kullanıcının mevcut/untracked dosyalarını koru. Özellikle mevcut kayıtlarda geçen `PLAN-17-HERMES.md` stage edilmemeli unless user explicitly asks.

`git add .` kullanma.

---

# 54. Product-source leakage scan

Changed production files içinde şu tip string/branch olmamalı:

```text
specific fixture filename
case id
known test dimension
known coordinate
known hole count
reference STEP path
```

Test fixture expected values yalnız test tarafında gerekçeli kullanılabilir.

---

# 55. Network/model audit

G2 diff yeni:

```text
Ollama/model API
web/network API
new OCR invocation
```

eklememeli.

Raster observer'ın mevcut tesseract çağrısı ayrı current behavior; G2 onu ikinci kez tetiklemez.

---

# 56. `docs/GUIDED_PROGRESS.md` güncellemesi

Yeni bölüm/tablo:

```text
G2.0 baseline
G2.1 adapter
G2.2 identity/dedup
G2.3 store integration
G2.4 vector/raster
G2.5 reopen/legacy
G2.6 final
```

Her satır:

```text
status
evidence command
exit code
passed/failed/skipped
log path
remaining blocker
```

Önceki G1 review kayıtları silinmez.

---

# 57. RED→GREEN çalışma kuralı

Her behavior contract:

```text
small failing test
→ failure reason confirmed
→ narrow implementation
→ focused green
→ nearby regression
```

Import bootstrap dışında anlamsız “RED” kanıtı kabul etme.

---

# 58. Failure triage

```text
Task ID:
Repro command:
Expected:
Actual:
Class: code / fixture / environment / scope
Single hypothesis:
Discriminating check:
Result:
```

Aynı blocker'da üç kör değişiklikten sonra dur; hipotez kaydı bırak.

---

# 59. G2 stop conditions

Aşağıdakilerden biri varsa G3 açılmaz:

```text
candidate id nondeterministic
invalid bbox silently clamped
hint → transcription promotion
candidate → parse promotion
candidate → target promotion
legacy load auto-redetect
second observe/OCR call
vector provenance lost
raster no-text case fabricated
G1 stale/undo/reconfirm regression
selected regression red
```

---

# 60. G2 Definition of Done

- [ ] pure adapter module exists
- [ ] detector version single-source
- [ ] px→normalized math pinned
- [ ] deterministic SHA-256 identity
- [ ] source path not identity
- [ ] method-based source kind
- [ ] exact dedup only
- [ ] provenance union
- [ ] conflicting hints not truth
- [ ] invalid bbox diagnostic, no clamp
- [ ] deterministic ordering
- [ ] no semantic field promotion
- [ ] new session persists candidates
- [ ] no auto transcription
- [ ] no auto parse
- [ ] no auto target
- [ ] no model call
- [ ] real vector fixture
- [ ] raster exercised or honestly blocked
- [ ] honest-none test
- [ ] reopen exact
- [ ] legacy no-redetect
- [ ] no fake user events
- [ ] G1 regression green
- [ ] diff check clean
- [ ] progress updated
- [ ] G3 still NOT OPENED

---

# 61. G2 final report format

```text
HEAD / worktree:
G2.0 baseline:
G2.1 adapter:
G2.2 identity/dedup:
G2.3 store integration:
G2.4 vector/raster:
G2.5 reopen/legacy:
Combined tests:
Full pytest:
Diff check:
Changed files:
Known open issues:
Model calls: 0
G3 status: NOT OPENED
NEXT SINGLE STEP: G3 plan/request
```

---

# 62. Suggested commit slicing

```text
1 guided: G2.1/G2.2 deterministic callout candidate adapter
2 guided: G2.3 store-create candidate persistence
3 guided: G2.4/G2.5 vector-raster-reopen regressions
4 docs: G2 final progress evidence
```

Team convention tek commit ise yine logical diff sınırlarını koru.

---

# 63. Expected changed files

Likely:

```text
src/drawingto3d/callouts.py
src/drawingto3d/guided.py
tests/test_callout_candidates.py
possibly tests/test_guided_callout_candidates.py
docs/GUIDED_PROGRESS.md
root PLAN.md if this execution plan is installed
report.md only short current-stage sync if desired
```

`callout_models.py` ancak gerçek contract blocker bulunursa değişir.

---

# 64. `manual` source_kind policy

Current candidate enum `manual` içeriyor; machine adapter bunu üretmez.

Manual region future G3 user-decision pathıdır.

---

# 65. Confidence policy

G2 `TextObservation.confidence` üzerinden candidate silme veya semantic karar vermez.

Confidence provenance observation'da kalır; ilk ürün sürümünde user review doğruluğu korur.

---

# 66. False-positive policy

G2 candidate list high recall olabilir. Title block veya başka metinler candidate çıkabilir.

Bu:

```text
G2 semantic failure değildir
```

G3 user ignore akışı bunu yönetecek.

---

# 67. False-negative policy

Observation text üretmemişse G2 box uydurmaz.

Future G3 manual region ile kullanıcı eksik alan ekleyebilir.

---

# 68. Metrics

G2 sonunda minimum diagnostic metrics:

```text
candidate_count
invalid_observation_count
dedup_count
vector_candidate_count
raster_candidate_count or honest none
```

Bunları STEP correctness veya semantic accuracy diye sunma.

---

# 69. Doğru başarı iddiası

G2 sonunda doğru cümle:

> Mevcut observation text bölgeleri deterministic, provenance-preserving ve reopen-stable `CalloutCandidate` kayıtlarına dönüştürülebiliyor.

Yanlış cümleler:

```text
program teknik resmi anlıyor
Ø8 otomatik okunuyor
binding çözüldü
STEP doğruluğu arttı
```

---

# 70. G3'e geçiş

G3 ancak G2 bütün DoD yeşil ve operator fazı açarsa.

G3 hedefi:

```text
canvas overlay
candidate select
crop preview
user raw transcription
ignore
manual region add/edit
persistence/undo
```

G3 semantic parser değildir.

---

# 71. G4+ kısa rota

```text
G4 callout-parser/1 real parser
G5 target proposal
G6 user target confirm/correct
G7 confirmed semantic+target → existing Decisions
G8 readiness/audit
G9 Plate golden path
G10 fixed 10-sheet manifest
G11 run #1
G12 generic fixes
G13 acceptance
```

Nihai hedef değişmedi:

```text
10/10 geometrically correct STEP
```


---

# 72. Current product authority

`report.md` active direction doğru biçimde:

```text
guided transcription
active plan = docs/PLAN-20.md
SEMREAD-001D parked
```

diyor.

Execution truth için current ayrıntı:

```text
docs/GUIDED_PROGRESS.md
```

G2 kickoff'ta report current stage kısa biçimde:

```text
G1 accepted after review rounds; G2 active
```

olarak sync edilebilir. Historical SEMREAD bölümünü yeniden yazma.

---

# 73. Current root `PLAN.md`

Current root plan G1 düzeltme turu 2'yi anlatıyor ve HEAD `316518eb...` ile tamamlandı.

Yeni agent sadece root `PLAN.md` okuyacaksa eski:

```text
NEXT SINGLE STEP = G1R2
```

talimatı stale olacaktır.

Bu G2 plan root'a kurulacaksa önce current root plan archive durumunu kontrol et. Aynı bytes zaten archive edilmişse ikinci duplicate yaratma.

---

# 74. Numbered plan policy

`docs/PLAN-20.md` umbrella plan olarak korunabilir; G2 zaten onun gelecekteki fazıdır.

Yeni `docs/PLAN-21.md` **zorunlu değildir**.

Operator ayrıca history entry isterse bu G2 plan byte-copy olarak `docs/PLAN-21.md` eklenebilir; PLAN-20 overwrite edilmez.

---

# 75. External CI truth

Current GitHub combined status:

```text
[]
```

Bu nedenle:

```text
External CI/status: none observed
```

diye raporla.

Local pytest'i external CI diye sunma.

---

# 76. Current test evidence sınırı

Latest tracked evidence:

```text
G1R2 54 passed callout tests
98 passed focused
198 passed selected combined set
```

Bu full repository suite değildir.

Yeni G2 sonunda exact yeni counts yazılmalı; bu eski sayıları kopyalayıp “current tests passed” denmemeli.

---

# 77. Research freeze

SEMREAD-001D current historical state:

```text
Round 1 FAIL
formal 0/4
dev 4/12
final 0/20
```

G2 sırasında:

```text
no requalification
no 001E
no prompt tuning
no model switch
no inference
```

---

# 78. Reference isolation

G2 adapter:

```text
reference STEP
gold semantic answers
evaluator output
```

okumaz.

Candidate region expected testleri source observation data üzerinden yapılır.

---

# 79. Example hardcoding yasağı

Production code içinde:

```text
filename
case number
known coordinate
known printed value
known circle count
```

üzerinden branch yok.

Source hash yalnız identity/provenance için kullanılabilir; çözüm seçmek için değil.

---

# 80. Source path rename testinin önemi

Identity path içermediği için aynı source bytes başka klasörde açıldığında candidate ID aynı kalmalıdır.

Bu ileride session portability ve stable user decision mapping için temel invarianttır.

---

# 81. Detector version bump gelecekte ne zaman?

Şunlar identity/region producer behavior değiştirirse bump düşün:

```text
bbox canonicalization change
different candidate source selection
phrase grouping
new title-block exclusion that changes candidate set
region merge/split rule
```

UI crop padding veya display label değişimi tek başına detector identity bump gerektirmeyebilir.

---

# 82. Candidate model version vs detector version

Ayır:

```text
CALLOUT_SCHEMA_VERSION = data shape
CALLOUT_DETECTOR_VERSION = producer behavior
```

G2 producer değişikliği schema değişikliği değildir.

---

# 83. Candidate geometry version açıklaması

Candidate record `geometry_version` taşır ama callout identity geometry key değildir.

Geometry change sonrası target staleness G1 fingerprint sistemiyle çözülür.

G2 detector ID'sini selected profile/thickness/user decisions'a bağlama.

---

# 84. Candidate generation user decisions'dan bağımsız

Aynı source observations için:

```text
profile selection
thickness
holes
calibration
bindings
view confirmation
```

değişse bile base machine candidate set değişmemeli.

Bu property mümkünse testle pinlensin.

---

# 85. G2 ek property test

Aynı `Observations`, farklı `geometry_version` parametresi:

```text
candidate.id same
candidate.geometry_version different
```

Eğer current intended contract buysa pinle; identity payload geometry version içermiyor.

---

# 86. G2 source-ref mutation guard

`SourceRef.ref` farklı ama digest aynı:

```text
id stable
```

`SourceRef.sha256` farklı:

```text
id changes
```

Bu iki test beraber identity contract'ı netleştirir.

---

# 87. Public state serialization

Candidate public JSON:

```text
normalized region
crop region
source kind
observation ids
detector version
machine hint
```

sunabilir.

Ama public state machine hint'i input alanına otomatik yazmaz; bu G3 UX kararıdır.

---

# 88. Candidate count limit

G2'de keyfi:

```text
max 32
max 100
```

candidate cap ekleme.

SEMREAD maxItems ile bu layer farklıdır.

Çok text region varsa hepsi persisted olabilir; UX filtering G3/G10 ölçüm konusudur.

Resource safety için gerçek ihtiyaç ölçülürse ayrı cap + diagnostic tasarlanır.

---

# 89. Observation ID uniqueness

Adapter observation IDs'lerinin benzersiz olduğunu kör varsaymamalı.

Exact duplicate IDs varsa provenance union deterministic olmalı. Aynı ID farklı region ile gelirse diagnostic/producer integrity issue olarak test edilebilir; silent overwrite yapma.

---

# 90. Machine hint blank behavior

Observation text boş/whitespace olabilir mi kontrol et.

Region valid ise iki seçenekten birini explicit seç:

```text
A candidate with hint None
```

ve diagnostic, veya invalid text observation skip.

Tercih G2 high-recall için:

```text
valid region candidate + machine_text_hint=None + diagnostic
```

ancak real observer contract boş text üretmiyorsa synthetic test üzerinden gereksiz behavior ekleme; önce kaynak kod/fixture doğrula.

---

# 91. Error containment

Tek kötü bbox tüm session create'i düşürmemeli, eğer diğer observations geçerliyse.

Adapter:

```text
per-observation diagnostic + continue
```

kullanabilir.

Ama invalid source/frame tüm batch identity'sini bozuyorsa fail/empty batch açık olmalı.

---

# 92. Deterministic diagnostics

Diagnostics kullanıcıya debug amacıyla dönecekse raw Python exception repr'lerine bağlı olmasın.

Code + stable observation id yeterli; free-form detail secondary.

---

# 93. G2 no-op behavior

Session create dışında save/accept/undo flows G2 candidate adapter çalıştırmamalı.

Candidate base state yalnız source creation'dan gelir.

Böylece unrelated user save candidate bytes değiştirmez.

---

# 94. Candidate mutation test

Create sonrası birkaç unrelated decision save et:

```text
thickness
profile
view
```

Expected persisted candidate base fields unchanged.

Freshness target logic ayrı computed state olabilir.

---

# 95. Undo candidate behavior

Undo user decisions:

```text
callout_candidates
```

base observations'ı geri/ileri değiştirmemeli.

Candidate list history snapshot içine decision gibi alınmamalı; current architecture nasıl ayırıyorsa koru.

---

# 96. Build candidate behavior

Build başarılı/başarısız olması candidate producer state'ini değiştirmez.

```text
build != detection refresh
```

property test faydalı olabilir.

---

# 97. Reopen exactness seviyesi

En az:

```text
model_dump candidate list equality
```

Tercihen persisted JSON relevant subtree exact equality.

Timestamp/log gibi unrelated alanlar compare dışında.

---

# 98. Real vector fixture expected region doğrulaması

Candidate region'un observation bbox'tan türediğini test et:

```text
candidate.observation_ids[0]
→ find TextObservation
→ independently normalize bbox in test
→ candidate.region equal
```

Known drawing coordinate literalini product source'a koyma.

---

# 99. Raster environment classification

Tesseract executable/package yoksa:

```text
BLOCKED_ENV
```

OCR returns no text on a valid source:

```text
PASS honest-none
```

Bu ikisini karıştırma.

---

# 100. Full G2 acceptance gate

G2 PASS diyebilmek için:

```text
G2.1 PASS
G2.2 PASS
G2.3 PASS
G2.4 PASS or explicitly partial only for raster BLOCKED_ENV
G2.5 PASS
G2.6 selected regressions PASS
```

Raster BLOCKED_ENV varsa G2 “complete with environment caveat” diye raporlanabilir ancak real-raster evidence varmış gibi yazılmaz.

---

# 101. G3 planına taşınacak açık konular

G2 sonunda şu maddeler kasıtlı açık kalacak:

```text
visual overlay
crop padding/preview
manual region
ignore state UI
transcription field
machine hint Accept/Edit
keyboard navigation
candidate progress counters
```

Bunları G2 TODO'su gibi başarısızlık sayma.

---

# 102. G4 planına taşınacak açık konular

```text
Ø/R/DIA grammar
count
THRU/DEPTH
units
ambiguity/error taxonomy
```

G2'nin `machine_text_hint` alanını parse ederek G4'ü erkene çekme.

---

# 103. G5/G6 planına taşınacak açık konular

```text
leader connectivity
geometry compatibility
count compatibility
ranked proposals
manual target selection
```

G2 observation region nearest-circle hesabı yapmaz.

---

# 104. G7/CAD planına taşınacak açık konular

```text
semantic + target → Hole/Binding/etc
conflict policy
unsupported CAD semantics
provenance map
```

Candidate detection CAD kararına dokunmaz.

---

# 105. Product milestone perspective

G2 tamamlandığında kullanıcı açısından büyük UI değişimi olmayabilir.

Ama sistem şu sağlam temeli kazanır:

```text
source observation regions
→ stable persisted candidate identities
```

G3'ün güvenilir overlay/transcription UI'sı bunun üstüne kurulacak.

---

# 106. Agent çalışma mesajı

> Bu `PLAN.md`yi uygula. Kapsam yalnız G2. Önce `docs/GUIDED_PROGRESS.md`, `docs/PLAN-20.md`, current root plan ve `callout_models.py`/`observe.py`/`raster.py`/`guided.py` ilgili bölümlerini oku. G1'i yeniden yazma. İlk iş saf `Observations → CalloutCandidate` adaptörü ve contract testleridir; green olmadan store entegrasyonuna geçme. Candidate yalnız region/provenance/hint'tir. `TextObservation.value/unit/count/kind` semantic truth değildir. ID source digest + page + canonical region + detector version + source kind üzerinden deterministic SHA-256 olmalı. Invalid bbox clamp edilmez. Exact duplicate dışında merge yok. `GuidedStore.create()` mevcut observation object'ini reuse eder; ikinci observe/OCR/model çağrısı yok. New session candidate üretirken transcription/parse/target yaratmaz. Legacy load redetect etmez. Vector/raster/honest-none, reopen ve G1 regression kapıları geçmeden G2 tamam deme. G3+ başlatma. Her kanıtı `docs/GUIDED_PROGRESS.md`ye exact command/exit/count/path ile yaz.

---

# 107. Handoff snapshot

```text
CURRENT HEAD
316518eb8d67c7a4ad81eed59c09e6c59ef4df37

ACTIVE PRODUCT
Guided transcription

UMBRELLA PLAN
docs/PLAN-20.md

PROGRESS
G0 PASS
G1 PASS after two review/fix rounds
latest selected evidence = 198 passed

G1 CONTRACTS
CalloutCandidate
TranscriptionDecision
SemanticParse
CalloutTargetDecision
freshness / explicit reconfirm / effective-contour target validation

MISSING NEXT PIECE
No actual Observations → CalloutCandidate producer.
src/drawingto3d/callouts.py absent at checked HEAD.

RESEARCH
SEMREAD-001D parked; no inference.

NEXT SINGLE STEP
G2.0 kickoff → G2.1 pure adapter.

G3+
NOT OPENED
```

---

# 108. ŞİMDİKİ TEK SOMUT İŞ

**G2.1 — pure adapter.**

Önce test yaz:

```text
1000×500 frame
bbox 100/50/200/100
→ [0.1,0.1,0.3,0.3]
```

Sonra minimum:

```text
src/drawingto3d/callouts.py
CALLOUT_DETECTOR_VERSION
region validation/normalization
source-kind mapping
SHA-256 candidate identity
machine_text_hint
observation provenance
```

Henüz `GuidedStore.create()` değiştirme.

G2.1/G2.2 pure layer yeşil olduktan sonra G2.3 integration'a geç.

---

# 109. Final principle

G2'nin başarı ölçüsü:

```text
same observation
→ same candidate identity
→ same region/provenance
→ reopen same record
→ zero invented user/semantic decisions
```

Bu katman sağlam olmadan UI'ya kutu çizmek, parser eklemek veya geometry binding yapmak erken olur.
