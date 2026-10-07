# PLAN.md — drawingto3d / PLAN-24-G12-CORRECTNESS
## G11 sonrası: yanlış STEP üretimini durdur → geometri stratejisini doğrula → generic CAD yeteneklerini genişlet → fixed manifesti yeniden koş
### Hermes için ayrıntılı, sıra-korumalı yürütme planı

**Tarih:** 2026-10-07  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Başlangıç `main` HEAD:** `cc36f8de62548299761a5b9c8d9a1b97320635f1`  
**Önceki master plan:** PLAN-23-HERMES-CONTINUOUS  
**G9:** PASS  
**G10:** fixed 10-sheet manifest frozen  
**UX-01:** PASS  
**G11:** tamamlandı fakat ürün başarısı düşük  
**G11R-01…05:** bağımsız inceleme düzeltmeleri PASS  
**SEMREAD:** PARKED  
**Model çağrısı:** varsayılan `0`  
**Bu planın amacı:** testleri “geçmiş göstermek” değil; source drawing + explicit user decisions üzerinden geometrik olarak doğru STEP üretme oranını generic biçimde yükseltmek.

---

# 0. HERMES'E VERİLECEK TEK BAŞLANGIÇ TALİMATI

> Bu PLAN.md'yi sırayla uygula. Başlangıç HEAD `cc36f8de62548299761a5b9c8d9a1b97320635f1`. G9/G10/UX-01/G11/G11R tarihsel kanıtlarını rewrite etme. Frozen `eval/guided_10_manifest.json` değişmeyecek. Önce G12.0 truth lock ve G12.1 false-readiness/decision-coverage düzeltmesi; sonra G12.2 build-strategy contract; ardından G12.3 raster contour/extrude, G12.4 revolve/axisymmetric, G12.5 multi-view/composite ve gerekirse G12.6 advanced-operation capability sırasıyla ilerle. Her yetenek için önce generic synthetic regression, sonra source-drawing-only guided run, en son evaluator karşılaştırması yap. Reference STEP, evaluator sonucu veya case adı producer kararına giremez. Bir case için özel koordinat/hash/filename/expected-feature hardcode etme. Bir capability gate geçmeden sonraki capability'ye atlama. Aynı blocker için üç ayrıştırıcı generic hipotez başarısız olursa HARD STOP raporu ver. Aksi halde kullanıcı onayı beklemeden devam et. Final hedef: frozen manifestteki 9 `full_step` vakanın 9/9 geometrik doğru olması ve 1 `callout_scope_only` vakanın kendi sözleşmesini geçmesi; bu sağlanmadan G13 PASS deme.

---

# 1. NEDEN BU PLAN VAR?

G11 sonucu ürünün şu anda Plate dışına genelleşmediğini gösterdi.

Dondurulmuş manifest:

```text
10 vaka toplam
9 full_step
1 callout_scope_only
```

Düzeltilmiş ana metrik:

```text
GUIDED_CORRECT_STEP_RATE = 1 / 9 = 0.1111
```

`full_step` sonuçları:

```text
plate-pocket-vector        correct STEP
drawing-2-vector           STEP var, yanlış
plastic-enclosure-vector   STEP var, bbox yakın fakat iç/geometri çok yanlış
exercise-12-vector         STEP var, yanlış
exercise-51-raster         STEP var, yanlış
flange-raster              STEP var, yanlış
exercise-17-raster         STEP yok
exercise-13-raster         STEP yok
my-part-raster             STEP yok
```

Bu bir evaluator problemi olarak ele alınmayacak.

G11R-01…05 sonrası:

```text
başarı paydası doğru
flange/ex51 kalibrasyon girdileri doğrulandı
UX auto-next düzeltildi
başarısız vaka kanıtları korunuyor
browser/evaluator hata sınıflaması ayrıldı
```

Buna rağmen doğrulanmış kalibrasyonla yeniden koşulan:

```text
flange-r2
exercise-51-r2
```

hala `CAD_WRONG`.

Dolayısıyla G12'nin ana işi:

```text
TEST RUNNER FIX
değil

GEOMETRY / VIEW / CONSTRAINT / CAD CAPABILITY
```

olacak.

---

# 2. G11'İN ANA KÖK NEDENİ — PLANIN BAŞLANGIÇ VARSAYIMI

Current guided `make_plan(record)`:

```text
selected profile
+ calibration
+ thickness
→ outer sketch
→ ALWAYS ExtrudeOp
→ hole/pocket cuts
```

Current ana gövde yolu açıkça:

```python
operations = [
    {
        "op": "extrude",
        "id": "base_extrusion",
        "output": "base",
        "sketch": "outer",
        "distance": "thickness",
    }
]
```

Bu nedenle:

```text
face-on circle
```

seçildiğinde sistem bunu çoğu durumda:

```text
disk extrude
```

olarak üretir.

Bu davranış Plate için uygundur.

Ama:

```text
flange
stepped shaft
axisymmetric part
multi-view part
elbow
shell/enclosure
```

için genel olarak doğru değildir.

Önemli mevcut kabiliyetler zaten repo içinde var:

```text
GeneralPlan:
  ExtrudeOp
  RevolveOp
  RepeatOp
  CutOp
  FuseOp

geo.py:
  profile_extrude
  profile_revolve
  repeat_linear
  repeat_circular
  cut
  fuse
  fillet_edges
  chamfer_edges

views.py:
  page view segmentation
  front / plan / side / section / isometric
```

Yani G12'nin ilk tercihi:

```text
yeni CAD engine yazmak
```

değil;

```text
mevcut generic CAD contract'ını guided workflow'a doğru bağlamak
```

olmalıdır.

---

# 3. G12 DEĞİŞMEZLERİ

Her committe korunacak:

```text
source drawing = producer source
reference STEP = evaluator-only
machine hint != user transcription
proposal != confirmation
ignored != "işimize gelmeyen ölçüyü sil"
valid solid != correct part
bbox match != geometry match
build success != acceptance
```

No-guess:

```text
çizimde olmayan ölçü uydurulmaz
reference STEP'ten ölçü producer'a taşınmaz
evaluator'dan feature listesi producer'a taşınmaz
case adına göre strateji seçilmez
dosya hash'ine göre kod yolu seçilmez
```

---

# 4. TARİHSEL KANITLARI DONDUR

Aşağıdakileri değiştirme:

```text
eval/guided_10_manifest.json
eval/guided_10_report.json
eval/guided_10_report.md

eval/audits/20261007-guided-g9-plate/**
eval/audits/20261007-guided-g11/cases/**
eval/audits/20261007-guided-g11/recipes-official/**
eval/audits/20261007-guided-g11/shots/**
eval/audits/20261007-guided-g11/logs/official/**
eval/audits/20261007-guided-g9-g11-independent-review/**
```

G12 yeni kanıtı yeni klasörlerde tutacak.

Eski yanlış sonuçlar silinmeyecek.

---

# 5. ROOT PLAN DEVRİ

Bu plan kök `PLAN.md` yapılacaksa:

1. mevcut root PLAN-23 byte-preserving archive:
   ```text
   docs/PLAN_ROOT_BEFORE_G12_20261007.md
   ```
2. bu dosyayı root `PLAN.md` yap.
3. ayrıca:
   ```text
   docs/PLAN-24-G12-CORRECTNESS.md
   ```
   byte copy sakla.
4. archive SHA256'ları progress'e yaz.

Historical plan overwrite etme.

---

# 6. G12 ÇALIŞMA DİZİNLERİ

Yeni:

```text
eval/audits/20261007-g12-baseline/
eval/audits/20261007-g12-decision-coverage/
eval/audits/20261007-g12-build-strategy/
eval/audits/20261007-g12-raster-profile/
eval/audits/20261007-g12-axisymmetric/
eval/audits/20261007-g12-multiview/
eval/audits/20261007-g12-advanced/
eval/audits/20261007-g12-manifest-reruns/
```

Her run ayrı alt dizin:

```text
run-01/
run-02/
...
```

Eski evidence üzerine yazma.

---

# 7. OPERATOR / PRODUCER / EVALUATOR AYRIMI

G12'de üç rol ayrılacak.

## 7.1 Operator

Görebilir:

```text
source drawing
guided UI
session-public
review bundle
detected geometry
callout crop
machine hints
```

Göremez:

```text
reference STEP
reference feature inventory
reference bbox
reference volume
prior evaluator result while making decisions
```

Operator yalnız source drawing'e göre user decisions üretir.

## 7.2 Producer

Görebilir:

```text
source drawing
session decisions
computed deterministic geometry
confirmed build strategy
```

Göremez:

```text
reference STEP
expected bbox
reference cylinders/faces
case-specific expected feature count
```

## 7.3 Evaluator

Build tamamlandıktan sonra:

```text
actual STEP
reference STEP
```

karşılaştırabilir.

Evaluator bulgusu:

```text
next generic engineering hypothesis
```

için kullanılabilir.

Ama:

```text
reference dimension → user decision
```

olarak kopyalanamaz.

---

# 8. PROCESS-LEVEL REFERENCE LEAKAGE KAPISI

G12 runner'ı iki aşamaya ayır:

```text
produce_case.py
evaluate_case.py
```

`produce_case.py` input:

```text
manifest entry WITHOUT reference_identifier_evaluator_only
source path
recipe/review actions
```

`evaluate_case.py` input:

```text
actual STEP
full manifest entry
reference STEP
```

Producer JSON dump'ında reference field bulunursa test fail.

Test:

```text
producer process env / argv / input JSON
```

reference path içeremez.

Source code test:

```text
src/drawingto3d/**
```

manifest reference field kullanmıyor.

---

# 9. G12.0 — TRUTH LOCK / BASELINE

İlk iş ürün koduna dokunmadan baseline kaydetmek.

## G12.0.1 HEAD

Kaydet:

```bash
git status --short
git rev-parse HEAD
git log -10 --oneline
```

Beklenen başlangıç:

```text
cc36f8de62548299761a5b9c8d9a1b97320635f1
```

HEAD farklıysa:

```text
STOP değil
```

fakat değişiklikleri incele, bu planın varsayımlarını güncelle ve progress'te exact HEAD yaz.

## G12.0.2 Historical G11 facts

Programatik assert:

```text
manifest total == 10
full_step == 9
callout_scope_only == 1
report metric denominator == 9
correct == ["plate-pocket-vector"]
rate == 1/9
```

Bu bir test olsun:

```text
tests/test_g12_baseline_contract.py
```

## G12.0.3 G9 guard

Plate donmuş evaluator:

```text
PASS
```

olmalı.

Plate G12 boyunca ana regression guard.

## G12.0.4 Relevant suite

Koş:

```text
tests/test_callout*.py
tests/test_guided*.py
tests/test_g11_report.py
tests/test_g11_evidence.py
tests/test_general*.py
tests/test_geo*.py
```

Exact result/log kaydet.

## G12.0 acceptance

- historical evidence unchanged
- manifest unchanged
- G9 Plate PASS
- G11 rate 1/9 pinned
- product tests green
- reference leakage process boundary hazır

PASS → G12.1.

---

# 10. G12.1 — FALSE READINESS / DECISION COVERAGE

## Amaç

Şu davranışı sona erdir:

```text
66 callout
→ 66 ignored
→ profile + scale + thickness
→ "ready"
→ yanlış STEP
```

`ready` yalnız form alanları dolduğu için true olmayacak.

Gerçek drawing information bilinçli olarak dışarı atılmışsa ürün bunu bilmek zorunda.

---

# 11. `ignored` VE `unsupported` AYRIMI

Mevcut iki davranış yetersiz:

```text
ignored
unbindable
```

çünkü gerçek bir build-relevant dimension `unbindable` olup build'i açabiliyor.

Yeni explicit disposition contract ekle.

Önerilen model:

```python
class CalloutDispositionDecision(BaseModel):
    callout_id: str
    kind: Literal[
        "not_model_input",
        "redundant",
        "build_relevant_unsupported",
    ]
    reason: str
    revision: int
```

Alternatif olarak mevcut review modeline backward-compatible field eklenebilir.

Ama semantik birebir şu olmalı:

```text
not_model_input
  title block
  drawing number
  material note unrelated to geometry
  duplicated detector fragment
  obvious detector false positive

redundant
  same geometry fact is already represented
  must cite the other callout/decision it duplicates

build_relevant_unsupported
  real geometry/dimension information
  current product cannot bind/apply it
```

---

# 12. LEGACY MIGRATION

Legacy:

```text
ignored=true
```

record:

```text
not_model_input
```

diye otomatik PROMOTE ETME.

Çünkü geçmişte relevant dimensions bulk ignored edildi.

Legacy record için:

```text
disposition = legacy_unclassified
```

computed/migration state olabilir.

Fresh build:

```text
legacy_unclassified
```

build-relevant callout varsa readiness block.

Historical G9/G11 evidence rewrite edilmez.

---

# 13. IGNORE UI COPY

Şimdiki:

```text
Bu bir ölçü/not değil
```

korunabilir.

Ama ikinci explicit seçenek:

```text
Gerçek ölçü/not ama bu sürüm modele uygulayamıyor
```

ekle.

Üçüncü:

```text
Bu bilgi zaten başka bir ölçüyle temsil ediliyor
```

ve duplicate reference seçtir.

Normal kullanıcı teknik enum görmez.

---

# 14. BULK IGNORE SINIRI

Bulk:

```text
Seçilenler modele ait değil
```

yalnız:

```text
not_model_input
```

üretir.

Bulk operation:

```text
real dimension unsupported
```

semantiği üretmez.

G11 runner artık bütün candidate'ları bulk ignore edip build açamaz.

---

# 15. DECISION COVERAGE METRİĞİ

Yeni pure function:

```python
callout_coverage(record) -> dict
```

en az:

```text
total
not_model_input
redundant
build_applied
build_relevant_unsupported
unclassified
stale
coverage_complete
```

`build_applied`:

```text
current transcription
+ current parse
+ current target
+ compile result = compiled
```

veya build için başka explicit existing decision tarafından represented.

---

# 16. G12.1 READINESS KURALI

Build block:

```text
unclassified > 0
build_relevant_unsupported > 0
stale > 0
```

unless chosen build strategy explicitly declares that fact irrelevant.

Bu istisna generic relation ile olmalı, case name ile değil.

Örneğin:

```text
sheet note = surface finish
```

geometry strategy'nin input'u değildir.

Ama:

```text
Ø50
R35
80
15
DEPTH 8
```

gibi user-classified build-relevant facts unsupported ise build açılmaz.

---

# 17. G12.1 TESTS

RED first.

En az:

```text
all visible candidates blanket ignored
→ fresh correctness run cannot claim coverage complete without explicit disposition semantics

one real dimension explicitly build_relevant_unsupported
→ readiness false

title block not_model_input
→ no blocker

duplicate with valid reference
→ no blocker

duplicate with missing/stale reference
→ blocker

compiled callout
→ build_applied

legacy ignored record
→ legacy_unclassified in fresh correctness run

undo/reopen
→ disposition preserved

revision conflict
→ reject

review export/import
→ disposition carries provenance and same validation
```

---

# 18. G12.1 G11/G12 RUNNER POLICY

Official/G12 operator recipe:

YASAK:

```text
"ignore_rest": true
```

veya equivalent blind blanket ignore.

Yeni recipe satırı:

```json
{
  "callout_id": "...",
  "decision": "not_model_input",
  "reason": "title block drawing number"
}
```

veya:

```json
{
  "callout_id": "...",
  "decision": "build_relevant_unsupported",
  "reason": "printed taper dimension; current strategy has no target"
}
```

Her ignored/unsupported real row gerekçeli.

Bulk yalnız explicit ID listesi.

---

# 19. G12.1 ACCEPTANCE

- false-ready case blocked
- blanket-ignore runner policy removed
- title-block bulk still usable
- build relevant unsupported blocks
- duplicate requires reference
- coverage audit visible
- undo/reopen/import green
- G9 Plate fresh run still buildable with proper dispositions
- historical G11 unchanged

PASS → G12.2.

---

# 20. G12.2 — BUILD STRATEGY CONTRACT

## Problem

Current guided plan effectively assumes:

```text
everything = constant-thickness extrude
```

Bu implicit assumption kaldırılacak.

Build strategy explicit user-confirmed decision olacak.

---

# 21. NEW STRATEGY DECISION

Önerilen:

```python
class BuildStrategyDecision(BaseModel):
    kind: Literal[
        "extrude_profile",
        "revolve_profile",
        "multi_view_composite",
        "unsupported",
    ]
    primary_view_id: str | None
    section_view_id: str | None
    axis: Literal["X", "Y", "Z"] | None
    evidence: list[...]
    geometry_version: int
```

Bu bir user decision.

Machine/deterministic system proposal üretebilir.

Proposal confirmation değildir.

---

# 22. STRATEGY PROPOSAL

Pure function:

```python
propose_build_strategies(record) -> list[BuildStrategyProposal]
```

Evidence:

```text
selected profile kind
view segmentation
section hatch
concentric circle stack
repeated radial circles
available side/section profile
existing archetype evidence
```

No filename/hash/reference.

Örnek deterministic evidence:

```text
single closed non-circular primary profile + thickness
→ extrude_profile candidate

section/profile entirely one side of an axis + axis evidence
→ revolve_profile candidate

multiple solid views required to express different depths/features
→ multi_view_composite candidate

face-on concentric circle stack alone
→ DO NOT propose extrude disk as high confidence
```

---

# 23. STRATEGY USER UI

Yeni panel:

```text
Parçanın ana oluşumu

Programın önerisi:
○ Sabit kalınlıklı profil
○ Eksen etrafında dönen profil
○ Birden fazla görünüş birlikte gerekli
○ Bu sürümde desteklenmiyor

[Onayla]
```

Technical details:

```text
strategy id
evidence
view ids
axis
```

collapsed.

---

# 24. STRATEGY FRESHNESS

Stale olur:

```text
profile change
view selection change
section change
geometry_version change
relevant callout decision change
axis change
```

Stale strategy → build blocked.

---

# 25. MAKE_PLAN DISPATCH

Refactor:

```python
make_plan(record)
```

into:

```python
prepare_build_context(record)
compile_extrude_plan(context)
compile_revolve_plan(context)
compile_multiview_plan(context)
```

Dispatcher:

```text
confirmed strategy
→ exact compiler
```

Default fallback:

```text
NO implicit extrude
```

Strategy missing:

```text
readiness blocker = missing_build_strategy
```

---

# 26. SYNTHETIC STRATEGY TESTS

Production code case-free.

Synthetic fixtures:

```text
rectangle + thickness
→ extrude proposal
→ ExtrudeOp

closed radius-height half-profile + confirmed axis
→ revolve proposal
→ RevolveOp

concentric face circles only, no section
→ not enough evidence to auto-confirm strategy

multiple orthographic view requirement
→ multi_view_composite proposal or explicit unsupported
```

No examples path.

---

# 27. STRATEGY SAFETY TEST

Critical:

```text
circle selected as primary profile
+ no explicit extrude strategy
→ make_plan MUST NOT silently produce disk
```

This directly prevents Flange/Exercise-51 class of false success.

---

# 28. G12.2 ACCEPTANCE

- strategy decision exists
- no implicit extrude
- stale strategy blocks
- proposals deterministic
- user confirmation required
- no reference leakage
- synthetic extrude/revolve tests
- Plate confirms extrude and still PASS
- face-on circle without strategy does not build accidental disk

PASS → G12.3.

---

# 29. G12.3 — RASTER CONTOUR + EXTRUDE CORRECTNESS

Priority cases from G11 failure taxonomy:

```text
exercise-17-raster → make_plan contour invalid
exercise-13-raster → make_plan contour invalid
my-part-raster     → calibration/readiness + contour/profile
```

These names are EVALUATION CASES ONLY.

Production code cannot branch on them.

---

# 30. G12.3 GOAL

Generic class:

```text
single-view / profile-extruded part
```

should work even on raster source.

Required:

```text
valid outer contour
verified physical scale
confirmed extrude strategy
required dimensions bound
then CAD
```

---

# 31. CONTOUR CANDIDATE AUDIT

For every profile candidate publish:

```text
profile_id
source primitive ids
closed?
self_intersection?
join gaps
applied endpoint movement
area
bbox
arc count
line count
contained circles
view_id
```

No auto "largest contour wins" without evidence.

---

# 32. VIEW-SCOPED PROFILES

`drawing_options()` currently sheet-global profile menu can contain unrelated views.

Add:

```text
profile.view_id
circle.view_id
primitive.view_id
```

where deterministically resolvable.

UI when user chooses a view:

```text
only profiles/circles in that view
```

by default.

"All geometry" may exist under technical/debug.

This is critical for multi-view pages too.

---

# 33. RASTER CLOSURE POLICY

Do NOT solve by increasing tolerance until contour closes.

For each correction:

```text
raw endpoint gap
movement applied
source ink support
user correction
```

record.

Limits remain generic constants justified by line width / detector uncertainty.

No per-case 20/36/50px branches.

---

# 34. MANUAL CONTOUR CORRECTION

If detector cannot produce correct closed profile:

user can:

```text
select edges to keep/drop
join one visible small gap
select alternate profile
```

Existing contour fix semantics reuse.

Do not add freehand geometry invention in G12.3.

---

# 35. DIMENSION-CONSTRAINED PROFILE

Current `sketch.py` says individual edges are not fully stretched by dimensions.

G12.3 must support at least:

```text
axis-aligned vertex-pair X/Y distance
circle centre X/Y relation
overall width
overall height
```

as exact user measurements.

Introduce/extend constraint solver so:

```text
printed dimensions move controlled coordinates
```

instead of only global scale.

Requirements:

```text
fixed coordinate provenance = user dimension
free coordinate provenance = trace
conflict = build stop
underconstrained = explicit
```

---

# 36. DO NOT CLAIM EXACT IF UNDERCONSTRAINED

Plan status:

```text
draft
```

when unbound trace coordinates remain.

For `full_step` correctness run:

underconstrained geometry may be built only when user explicitly accepts trace assumption.

But G12 score must record:

```text
trace-derived coordinate count
dimension-derived coordinate count
```

Never call underconstrained result "dimensionally verified".

---

# 37. G12.3 SYNTHETIC TESTS

Generic:

```text
raster-like rectangle with 3px corner gaps
→ user approved close
→ correct profile

two separate view contours
→ view selection prevents cross-view profile

overall width binding changes X extent exactly
overall height binding changes Y extent exactly

conflicting width bindings
→ no plan

invalid self-intersecting contour
→ no plan

trace-only contour
→ draft provenance
```

---

# 38. G12.3 REAL SOURCE RUN

Operator source-only.

For the three blocked raster profile cases:

1. source drawing open
2. choose intended view from drawing
3. choose/correct contour
4. transcribe relevant dimensions
5. bind relevant dimensions
6. confirm extrude strategy only if drawing supports it
7. build
8. then evaluator

Do not inspect reference until STEP is produced.

---

# 39. G12.3 ACCEPTANCE

Capability acceptance:

```text
at least one previously non-building raster profile case
must produce a STEP through generic path
AND evaluator must show genuine improvement
```

"Genuine improvement":

```text
not just valid solid
```

must improve shape/bbox/detail evidence compared with G11 baseline.

If all three remain blocked:

apply three-hypothesis rule.

Do not move to axisymmetric capability while basic raster profile path is broken unless blocker is explicitly classified as not an extrude-profile case.

---

# 40. G12.4 — AXISYMMETRIC / REVOLVE PATH

G11 showed:

```text
flange/ex51
```

with corrected scale still became single disks.

This phase removes that class of error.

---

# 41. REVOLVE INPUT CONTRACT

A revolve plan requires:

```text
confirmed revolve strategy
confirmed section/side profile
confirmed revolve axis
physical scale
required diameters/radii/lengths
profile entirely one side of axis
```

Face-on circle alone is insufficient.

---

# 42. SECTION PROFILE SELECTION

Reuse `views.py`:

```text
section
front
side
plan
```

but user confirms.

UI:

```text
Döndürülecek kesit hangisi?
[view thumbnails / overlays]

Dönme ekseni:
[axis overlay]

[Onayla]
```

No auto use without confirmation.

---

# 43. REVOLVE PROFILE GEOMETRY

Build local radius-height coordinates:

```text
x = radius >= 0
y = axial position
```

from selected section.

`GeneralPlan`:

```text
Sketch plane = XZ or appropriate confirmed frame
RevolveOp(angle=360)
```

Use existing operation first.

No new CAD engine.

---

# 44. REVOLVE DIMENSION BINDINGS

Support generic bindings:

```text
diameter → 2 * radius
radius → radius
axial linear → y distance
step diameter
step length
bore diameter
```

Each parameter source:

```text
printed/user/derived
```

with span/callout provenance.

No reference dimensions.

---

# 45. REVOLVE FEATURES

After base revolve:

```text
axial bore
face holes
blind bores
```

may be cuts.

If repeated holes:

```text
one hole tool
→ RepeatOp circular
→ CutOp
```

only when printed count + confirmed target group support repetition.

Do not infer bolt circle from reference.

---

# 46. CURRENT GENERALPLAN LIMITATION

`GeneralPlan` already exposes:

```text
revolve/repeat/cut/fuse
```

Use these.

Do NOT add new op if existing op can express the feature.

---

# 47. G12.4 SYNTHETIC CAD TESTS

No manifest sample coordinates.

At least:

```text
stepped shaft half-profile
→ revolve
→ expected bbox

flange-like revolve profile + axial bore
→ revolve + cut

revolve body + 4 repeated holes
→ repeat + cut

profile crossing axis
→ reject

missing axis
→ readiness block

face circle with no section
→ readiness block, not disk
```

---

# 48. G12.4 REAL RUN

Source-only operator run on axisymmetric candidates.

After output:

evaluator compares.

Success is not:

```text
bbox closer
```

alone.

Need:

```text
bbox
volume
major cylinder radii
feature inventory
```

improve.

At least one axisymmetric previously-wrong case must become geometrically correct before G12.4 PASS.

If no axisymmetric case correct after three generic hypotheses:

HARD STOP with exact missing capability.

---

# 49. G12.5 — MULTI-VIEW COMPOSITE

Only after:

```text
single-profile extrude path reliable
revolve path reliable
```

Do multi-view.

Known evaluation tags include:

```text
drawing-2-vector: multi_view
exercise-12-vector: multiple views / complex rotational-flanged
```

Again: names only evaluator scope; production no branch.

---

# 50. VIEW GRAPH

Create deterministic/user-confirmed:

```python
ViewGraph:
  views[]
  relation[]
  primary
  section
```

Relations:

```text
front ↔ plan
front ↔ side
section_of
```

Evidence from:

```text
layout
section label
hatch
shared axes/alignment
```

User confirms ambiguous mapping.

---

# 51. DO NOT FUSE VIEWS AS PROFILES

Critical regression:

```text
geometry from another orthographic view
must not become same 2D outer profile
```

Every primitive/profile/circle participating in build has:

```text
view_id
```

Build compiler requires view compatibility.

---

# 52. MULTI-VIEW BUILD STRATEGY V1

Do not attempt arbitrary B-rep reconstruction.

First generic supported composition:

```text
one base strategy:
  extrude OR revolve

plus features sourced from secondary views:
  depth
  bore
  pocket
  through cut
  repeated hole
```

This is `multi_view_composite v1`.

If drawing needs:

```text
loft
sweep elbow
shell
freeform surface
```

declare unsupported until G12.6.

---

# 53. CROSS-VIEW FEATURE BINDING

Callout target can include:

```text
view_id
geometry_id
```

Compiler may combine:

```text
diameter from front
depth from section
```

only after explicit user relation says they describe same feature.

New decision:

```text
FeatureLinkDecision
```

e.g.:

```text
feature key
source callout ids
source view ids
target geometry ids
```

No proximity across views.

---

# 54. MULTI-VIEW TESTS

Synthetic:

```text
front circle + section depth linked by user
→ blind bore

front diameter + side length linked
→ revolved/extruded feature

same-size circles in two views without explicit link
→ ambiguous / block

section hatch detected but unconfirmed
→ block

isometric view
→ never used for solid by default
```

---

# 55. G12.5 ACCEPTANCE

- view-scoped geometry
- no cross-view accidental binding
- feature link explicit
- one generic multi-view composition works
- at least one previously wrong multi-view full_step case shows correct or materially improved evaluator result
- Plate and prior G12 passes remain green

If required geometry fundamentally exceeds v1 operations → G12.6 classification.

---

# 56. G12.6 — ADVANCED OPERATION CAPABILITY AUDIT

This phase is NOT automatic code expansion.

First produce:

```text
eval/audits/.../capability-gap.json
```

For every remaining full_step failure:

```text
required operation class
evidence from SOURCE DRAWING
current operation support
can existing GeneralPlan express?
can generic small extension express?
architecture-sized?
```

Reference may only confirm final evaluator mismatch, not define producer inputs.

---

# 57. OPERATION CLASSES

Classify gaps:

```text
fillet
chamfer
shell
taper/cone
loft
sweep
compound revolve
multiple fused bodies
pattern
counterbore/countersink
thread representation
```

---

# 58. SMALL GENERIC EXTENSIONS

`geo.py` already contains:

```text
fillet_edges
chamfer_edges
```

but `GeneralPlan` does not expose them.

If source drawing clearly carries fillet/chamfer data, small plan extensions are allowed:

```python
FilletOp
ChamferOp
```

with:

```text
parameter source
selector contract
validation
compile_general
check_general
synthetic CAD tests
```

No selector string directly from user/untrusted JSON without validation.

---

# 59. TAPER / CONE

If needed and source drawing supplies:

```text
two diameters
axial length
```

prefer expressing taper in revolve profile.

Do not add ConeOp unless it is demonstrably simpler and generic.

---

# 60. SHELL / ENCLOSURE

If remaining case requires shell:

Do not fake by:

```text
outer extrude only
```

Possible small extension only if:

```text
constant wall thickness
selectable opening face
generic shell operation
```

can be represented safely.

Otherwise architecture-sized → HARD STOP.

---

# 61. SWEEP / ELBOW

If a full_step case requires true swept bend:

Current `GeneralPlan` does not expose generic sweep.

`geo.ring_revolve` is a specific tube bend verb outside GeneralPlan.

Do NOT case-wire it.

Options:

```text
A. generic SweepOp added to GeneralPlan
B. classify architecture-sized and HARD STOP
```

Decision based on generic contract complexity, not desire to pass one case.

---

# 62. G12.6 HARD STOP RULE

Stop and report if 9/9 requires:

```text
arbitrary surfacing
unbounded CAD operation language
reference-derived parameters
sample-specific recipes hidden in producer
```

Do not implement hacks to avoid the stop.

---

# 63. G12 RUNNER — HUMAN-ASSISTED GERÇEK KULLANIM

G11 recipes became overly aggressive.

G12 operator must behave like product user.

For each source drawing:

1. open source
2. inspect detected regions
3. mark title block/non-model text
4. transcribe geometry-relevant callouts
5. confirm parse
6. confirm/select target
7. choose view(s)
8. confirm build strategy
9. bind required dimensions
10. build only when readiness is genuinely clear

No:

```text
ignore all → build
```

---

# 64. EXTERNAL REVIEW BUNDLE KULLANIMI

GX exists.

G12 may use:

```text
export bundle
→ external reviewer decisions
→ import
```

but source drawing must accompany review.

Reviewer cannot see reference STEP.

Imported decisions:

```text
external_review
```

provenance.

At least one run per new capability must also be done through manual UI to ensure UX actually works.

---

# 65. RECIPE CONTRACT V2

New recipe schema:

```json
{
  "case_id": "...",
  "source_sha256": "...",
  "operator_basis": "source_drawing_only",
  "view_decisions": [],
  "strategy_decision": {},
  "callout_actions": [],
  "profile_actions": [],
  "dimension_bindings": [],
  "notes": []
}
```

Each action reason required.

No:

```text
expected bbox
expected volume
reference radii
reference feature count
```

inside producer recipe.

Static test rejects these field names.

---

# 66. G12 FAILURE TAXONOMY V2

Refine G11 taxonomy:

```text
READ_DETECT
READ_TRANSCRIPTION
READ_PARSE
VIEW_SEGMENTATION
VIEW_RELATION
STRATEGY_MISSING
STRATEGY_WRONG
PROFILE_INVALID
PROFILE_WRONG
SCALE_UNVERIFIED
CONSTRAINT_MISSING
CONSTRAINT_UNSUPPORTED
CONSTRAINT_CONFLICT
FEATURE_LINK_MISSING
CAD_OPERATION_UNSUPPORTED
CAD_BUILD_FAILED
CAD_WRONG_GEOMETRY
STEP_EXPORT
STEP_REOPEN
EVALUATOR_FAILURE
```

One case can carry multiple secondary codes but exactly one:

```text
primary_root_cause
```

---

# 67. "CAD_WRONG" TEK BAŞINA YETERLİ DEĞİL

Every wrong STEP:

```text
shape mismatch
detail mismatch
```

sonrası producer-side evidence ile kök neden sınıflandırılacak.

Örnek:

```text
actual = disk
source shows axial section + steps
strategy = extrude
→ STRATEGY_WRONG
```

Reference yalnız sonucu doğrular.

---

# 68. THREE-HYPOTHESIS RULE

Bir blocker için max 3 generic hypothesis.

Her attempt:

```text
H1
evidence
change
focused test
real source run
result

H2
...

H3
...
```

Üçü de fail:

```text
HARD STOP
```

Yeni gizli dördüncü sample hack yok.

---

# 69. G12 COMMIT STRATEJİSİ

Önerilen:

```text
G12.0  baseline + leakage guard
G12.1a disposition/coverage schema + backend
G12.1b coverage UI + runner v2
G12.2a build strategy models/proposals
G12.2b strategy UI + make_plan dispatch
G12.3a view-scoped contour geometry
G12.3b dimension-constrained raster profile
G12.4a revolve compiler
G12.4b revolve guided UX/features
G12.5a view graph
G12.5b cross-view feature links
G12.6x generic advanced op extensions as required
G12.Rn manifest rerun evidence
```

Her commit bir green gate.

---

# 70. DO NOT MIX RUNS AND PRODUCT CODE

Official capability run sırasında:

```text
no src edit
```

Bug bulunursa:

1. run'ı finish/mark fail
2. commit evidence
3. new regression
4. product fix
5. new run id

Same run içinde code version değiştirme.

---

# 71. GENERALPLAN CONTRACT TESTS

Every new operation/strategy:

```text
Pydantic validation
expression/unit validation
compile_general output
CadQuery execution
STEP reopen
geometry.json
check_general
```

testli.

Do not test only dict shape.

---

# 72. CAD TEST ENVIRONMENT

Use `.venv-cad`.

Every synthetic CAD acceptance:

```text
actual STEP generated
reopened
single valid solid
numeric expected geometry
```

No mock-only operation acceptance.

---

# 73. SOURCE-DRAWING REGRESSION VS SYNTHETIC

Two layers:

## Layer A — generic synthetic

Proves capability independent of samples.

## Layer B — fixed manifest

Proves capability helps real drawings.

A feature is not accepted if only Layer B passes with sample-specific logic.

---

# 74. MANIFEST RERUN POLICY

After each major capability:

```text
do NOT necessarily run all 10 immediately
```

First:

```text
affected cluster
+ Plate guard
```

When cluster passes:

```text
full frozen 10-sheet rerun
```

All full reruns under:

```text
eval/audits/20261007-g12-manifest-reruns/run-N/
```

---

# 75. PRIMARY METRIC

Always:

```text
correct full_step / 9
```

No denominator reduction.

Report:

```text
correct
wrong
blocked
unsupported
```

separately.

---

# 76. SAFETY METRIC — WRONG STEP RATE

Add:

```text
WRONG_STEP_RATE =
produced_but_geometry_wrong / 9
```

G12 priority:

```text
first reduce false wrong outputs
then raise correct outputs
```

A safe blocker is better than confidently wrong STEP.

---

# 77. COVERAGE METRICS

Per case:

```text
candidate_count
not_model_input_count
redundant_count
build_applied_count
unsupported_build_relevant_count
unclassified_count

dimension_derived_coordinate_count
trace_derived_coordinate_count

strategy
views_used
operation_types
```

---

# 78. EXPECTED PROGRESSION

Do NOT fake fixed numeric promise.

But engineering direction:

```text
G12.1:
wrong outputs may decrease because unsafe builds block

G12.3:
blocked raster profile cases should begin producing meaningful parts

G12.4:
single-disk axisymmetric failures should disappear

G12.5:
multi-view wrong-strategy failures should decrease

G12.6:
remaining operation gaps classified/extended
```

Metric can temporarily fall in "produced count" while correctness safety improves.

That's acceptable.

---

# 79. PLATE REGRESSION

Every major phase:

```text
Plate source-only guided replay
```

at minimum compiler/session replay.

After CAD strategy changes:

```text
real STEP + frozen Plate evaluator
```

PASS required.

Plate must remain:

```text
extrude_profile
```

not regress to another strategy.

---

# 80. UX REQUIREMENTS

Do not return to giant technical form.

UX-01 principles preserved.

New strategy/view tasks appear in:

```text
Eksik kalanlar
```

as actionable tasks.

Examples:

```text
○ Parçanın ana oluşumunu onaylayın
○ Döndürülecek kesiti seçin
○ Dönme eksenini onaylayın
○ 3 gerçek ölçü bu sürümde modele uygulanamıyor
```

---

# 81. BUILD BUTTON WORDING

If blocked by unsupported geometry-relevant data:

```text
3B Modeli Oluştur
```

disabled.

Reason:

```text
3 gerçek ölçü modele henüz uygulanamıyor.
```

Do not invite user to mark them false just to unlock build.

---

# 82. AUDIT OUTPUT

`plan-audit.json` plus session audit:

```text
strategy
views
callout coverage
parameter provenance
operations
unconstrained coordinates
unsupported build facts
```

Every generated CAD feature maps back to decisions.

---

# 83. REFERENCE LEAKAGE STATIC TEST

Search product source for:

```text
reference_identifier_evaluator_only
guided_10_manifest
examples/pdf with steps
case_id names
known source hashes
```

Allowed:

```text
eval/
tests/
docs/
```

Not allowed:

```text
src/drawingto3d/
```

except generic example-independent documentation wording.

---

# 84. SAMPLE-SPECIFIC HARD-CODE TEST

Automated source scan + review.

Reject production code containing:

```text
plate-pocket-vector
drawing-2-vector
exercise-51-raster
flange-raster
specific SHA256 from manifest
source filename tests
known test coordinates
```

No false positives in eval/tests.

---

# 85. EVALUATOR CHANGE POLICY

Evaluator code is frozen per historical run.

If evaluator bug is discovered:

1. preserve old evaluator/result
2. independent minimal reproduction
3. fix evaluator
4. report both:
   ```text
   historical verdict
   corrected evaluator verdict
   ```
5. evaluator fix cannot alter producer code in same commit.

No tolerance widening to make result pass without physical justification.

---

# 86. TOLERANCES

Every geometry tolerance:

```text
source/detector resolution based
CAD numeric based
manufacturing/drawing tolerance if explicitly printed
```

No:

```text
"case passes at ±X so choose X"
```

---

# 87. G12.3 / G12.4 CASE AUTHORING RULE

Hermes may manually inspect source images/PDF to act as operator.

When writing recipe:

```text
cite visible printed text
cite selected callout id
cite view/profile id
cite user action
```

Do not write:

```text
"reference says outer diameter 100"
```

If source text cannot be verified:

```text
do not use value
```

---

# 88. PDF SOURCE RULE

For vector PDF:

prefer existing vector observations.

No new OCR pass just because operator needs text.

Raster:

machine hints are suggestions only.

User/external reviewer transcription remains authority.

---

# 89. BUILD-RELEVANT DIMENSION DEFINITION

A callout is build relevant when user says it determines:

```text
outer geometry
inner geometry
feature size
feature position
depth
thickness
radius
angle
pattern count
pattern spacing
axis / centreline relation
```

Non-build model text:

```text
drawing number
revision
material
scale note
title block
company name
projection symbol
general metadata
```

Note:

```text
material
```

may matter in manufacturing but not current geometric STEP; mark `not_model_input` with reason, not detector false-positive.

---

# 90. SCALE NOTE RULE

`SCALE 1:5`:

```text
not px/mm calibration
```

unchanged.

Raster physical calibration requires:

```text
verified printed linear/radius/diameter datum
+ confirmed geometry endpoints
```

---

# 91. RADIUS / DIAMETER AS SCALE

Do not use an evaluated/reference diameter as scale.

A user-confirmed printed diameter/radius from source drawing may be used only if target geometry is confirmed and independent enough for intended calibration contract.

Prefer genuine linear datum when available.

Record source.

---

# 92. STRATEGY / CALIBRATION ORDER

Recommended readiness order:

```text
view
→ strategy
→ source measurements
→ calibration
→ profile/section
→ feature targets
→ constraints
→ build
```

But UI can interleave.

Build always revalidates current relationships.

---

# 93. "PROFILE CIRCLE" SPECIAL SAFETY

Current system can expose:

```text
profile kind = circle
```

New rule:

```text
circle profile + extrude strategy
```

requires explicit user statement:

```text
"Bu parça sabit kalınlıklı dairesel disk/plate."
```

Otherwise do not infer.

This prevents accidental flange disk.

---

# 94. ROTATIONAL-FLANGED ARCHETYPE

Existing archetype/proposal code may suggest rotational-flanged.

Treat it only as:

```text
strategy evidence
```

not truth.

User must confirm:

```text
revolve / multi-view / unsupported
```

Do not directly generate special flange code.

---

# 95. CURRENT ADVISE CODE SAMPLE COMMENTS

Production comments/docs currently mention measured sample sheets in places.

G12 should not necessarily remove historical comments, but:

```text
no new sample-derived production thresholds
```

without corpus-independent rationale.

Any new threshold must be justified generically and tested across synthetic variability.

---

# 96. G12 SELF-REVIEW CHECKLIST

Every phase end:

```text
Did I branch on case/file/hash?
Did I copy evaluator/reference value into producer?
Did I classify a real dimension as irrelevant just to build?
Did I make implicit extrude/revolve decision?
Did I widen tolerance to pass?
Did I mutate historical evidence?
Did I accidentally change manifest?
Did I call valid STEP "correct" without evaluator?
Did I use one sample as only regression for generic feature?
```

Any YES → phase not accepted.

---

# 97. TEST ORDER PER PHASE

Always:

```text
1 RED focused tests
2 implementation
3 focused green
4 related historical regression
5 synthetic CAD real run
6 source-only real guided run
7 evaluator
8 Plate guard
9 git diff --check
10 self-review
11 commit
```

---

# 98. FULL SUITE

Run:

```text
pytest -q tests -k "not semread"
```

after:

```text
G12.1
G12.2
G12.4
G12.5
final G12 before G13
```

If runtime expensive, G12.3 minor subcommits can use selected suites, but phase gate needs broad run.

SEMREAD stays parked.

---

# 99. REAL BROWSER

Required whenever:

```text
disposition UX
strategy UX
view/section UX
feature-link UX
```

changes.

DOM-only not enough.

Use existing Chrome/CDP harness.

---

# 100. G12 PROGRESS FILE

`docs/GUIDED_PROGRESS.md` current status:

```text
G9 PASS
G10 frozen
UX-01 PASS
G11 baseline 1/9
G11R-01–05 PASS
G12 current: <phase>
```

Do not say:

```text
G11 accepted product
```

G11 is baseline measurement.

---

# 101. G12 REPORT FILE

Maintain:

```text
eval/g12_progress.json
eval/g12_progress.md
```

Per capability:

```text
HEAD
tests
browser
CAD synthetic
affected real cases
before verdict
after verdict
new correct count / 9
wrong STEP count
blocked count
root cause changes
```

---

# 102. G12.1 DELIVERABLES

Expected files roughly:

```text
src/drawingto3d/callout_models.py
src/drawingto3d/callout_readiness.py
src/drawingto3d/callout_review.py
src/drawingto3d/guided.py
src/drawingto3d/static/guided.html
src/drawingto3d/static/guided.js

tests/test_callout_coverage.py
tests/test_guided_callout_http.py
tests/test_guided_callout_chain.py
tests/test_guided_html.py
```

Naming may differ; semantics may not.

---

# 103. G12.2 DELIVERABLES

Expected:

```text
src/drawingto3d/build_strategy.py
or equivalent pure module

guided models/store/API/UI
make_plan compiler dispatch
tests/test_build_strategy.py
tests/test_guided_build_strategy.py
```

Do not put all strategy logic in `guided.js`.

Backend authority.

---

# 104. G12.3 DELIVERABLES

Likely:

```text
view-scoped geometry metadata
contour diagnostics
constraint-core extension
real raster regression evidence
```

Avoid monolithic `guided.py` growth if pure logic can be separate.

---

# 105. G12.4 DELIVERABLES

Likely:

```text
revolve plan compiler
section profile mapping
axis confirmation
generic diameter/axial constraints
repeated-hole tool path if evidence supports
```

Prefer existing GeneralPlan operations.

---

# 106. G12.5 DELIVERABLES

Likely:

```text
view graph
feature-link decision
cross-view compiler
multi-view readiness
```

No arbitrary solid reconstruction.

---

# 107. G12.6 DELIVERABLES

Only if required:

```text
small generic GeneralPlan operation extensions
```

Each independent.

Do not combine shell+sweep+loft+fillet in one commit.

---

# 108. SUCCESS CRITERIA — INTERMEDIATE

G12 is progressing correctly if:

```text
wrong confident STEP count decreases
build blockers become more truthful
new correct full_step cases appear
generic synthetic capability tests grow
Plate remains correct
```

A temporary rise in "blocked" can be good if previously wrong outputs stop.

---

# 109. FINAL G12 ACCEPTANCE

Before G13:

Frozen manifest full rerun.

Required:

```text
full_step total = 9
correct = 9
wrong = 0
unproduced = 0
```

For 10th `callout_scope_only` case:

```text
source opens
callout decisions auditable
no silent guess
unsupported geometry honestly blocked
```

It does NOT need reference STEP because none exists.

Thus final manifest acceptance:

```text
9/9 full_step geometrically correct
+
1/1 callout_scope_only contract correct
```

Do not report fake "10/10 geometry".

---

# 110. G13 HANDOFF

Only after §109.

G13:

```text
fresh sessions
final candidate HEAD
frozen manifest
no code edits mid-run
real UI
STEP reopen
feature evaluator
full pytest
reference leakage audit
```

---

# 111. HARD STOP CONDITIONS — G12-SPECIFIC

Stop only when:

1. Three generic hypotheses for same capability fail.
2. Correct geometry requires reference-only fact not available on drawing/user input.
3. Required geometry needs a new CAD paradigm beyond bounded GeneralPlan extension.
4. View relation cannot be determined and no reasonable user-confirmation UX can express it.
5. Source drawing itself lacks enough information for reference geometry.
6. Evaluator is demonstrably unreliable and cannot be independently corrected.
7. Fix would require sample-specific production hardcode.

Report:

```text
capability
affected manifest cases
source evidence
3 hypotheses tried
why current contracts insufficient
smallest architecture option
what still passes
user decision required
```

---

# 112. DO NOT HARD STOP FOR

Do not stop for:

```text
ordinary failed test
contour bug
parser grammar gap
missing UI button
schema migration
CAD operation bug
view metadata bug
one source run failure
test runner bug
```

Fix and continue.

---

# 113. HERMES İÇİN PHASE-BY-PHASE KISA KOMUT

```text
START cc36f8d

G12.0
freeze truth / leakage boundary

G12.1
ignored ≠ unsupported
coverage gate
no blanket ignore readiness

G12.2
explicit build strategy
no implicit extrude

G12.3
raster profile/extrude correctness
view scoped contours
dimension constraints

G12.4
revolve / axisymmetric path
existing GeneralPlan Revolve/Repeat/Cut first

G12.5
multi-view composite v1
explicit cross-view feature links

G12.6
classify remaining CAD operation gaps
small generic op extensions only

THEN
frozen manifest rerun
9/9 full_step correct
1/1 scope-only honest
→ G13
```

---

# 114. İLK YAPILACAK KOD DEĞİŞİKLİĞİ

Do NOT start by fixing Flange geometry.

Do NOT start by adding revolve code.

First code task:

```text
G12.1 false readiness regression
```

RED test:

```text
a real geometry-relevant callout classified as unsupported
MUST keep readiness false
```

Second RED:

```text
circle profile without explicit build strategy
MUST NOT implicitly compile to extruded disk
```

These two guards prevent the current failure mode from surviving while later capabilities are built.

---

# 115. İLK REAL-RUN HEDEFİ

After G12.1 + G12.2:

Run Plate.

Expected:

```text
strategy = extrude_profile confirmed
coverage complete
build
Plate evaluator PASS
```

Then pick the simplest source-only raster profile capability run.

Do not choose case by "easiest reference".

Choose by source-side classification:

```text
single primary view
closed/explainable profile
constant-thickness extrude evidence
```

Record why.

---

# 116. REFERENCE-FREE CASE SELECTION FOR CLUSTER RUNS

Create:

```text
cluster-classification.json
```

before opening any reference evaluator in that phase.

Fields:

```text
case_id
source_observed_views
source_observed_geometry_style
proposed_strategy_class
current_blocker
classification_basis
```

No reference geometry fields.

Commit classification before evaluator-assisted fix loop.

This prevents hindsight scope manipulation.

---

# 117. CLUSTER CLASSIFICATION ALLOWED LABELS

```text
extrude_profile
axisymmetric_revolve
multi_view_composite
advanced_operation
insufficient_source_information
```

This label is evaluation organization only.

Production code never reads it.

---

# 118. FINAL NO-HACK AUDIT

Before G13:

```bash
git grep -n \
  -e "plate-pocket-vector" \
  -e "drawing-2-vector" \
  -e "exercise-51-raster" \
  -e "flange-raster" \
  -- src/drawingto3d
```

Expected:

```text
no production case branches
```

Also manifest SHA hashes absent from production.

Manual review of numeric constants added in G12:

every constant needs generic explanation.

---

# 119. FINAL DOC WORDING

If final target reached:

Correct wording:

```text
Frozen guided manifest:
9/9 reference-backed full_step cases geometrically correct,
1/1 scope-only case handled without silent geometry claims.
```

Do not say:

```text
arbitrary technical drawings solved
fully automatic
AI reads every drawing
```

---

# 120. MASTER DONE CHECKLIST

Hermes may mark PLAN-24 complete only if ALL are true:

- [ ] historical G9/G10/G11 evidence untouched
- [ ] frozen manifest unchanged
- [ ] reference leakage process guard exists
- [ ] blanket-ignore false readiness removed
- [ ] build-relevant unsupported facts block
- [ ] callout coverage audited
- [ ] explicit build strategy decision exists
- [ ] no implicit extrude fallback
- [ ] Plate extrude path still PASS
- [ ] raster profile path generically improved
- [ ] exact dimension constraints can control relevant profile coordinates
- [ ] revolve path uses existing GeneralPlan generic operations
- [ ] face-on circle cannot silently become flange disk
- [ ] view-scoped geometry exists
- [ ] cross-view feature relation is explicit
- [ ] remaining operation gaps classified
- [ ] any new CAD operations have synthetic real-CAD tests
- [ ] no filename/hash/case hardcodes in production
- [ ] no reference values in producer recipes
- [ ] real browser acceptance for new decisions
- [ ] `pytest -q tests -k "not semread"` green at final G12
- [ ] final frozen manifest rerun complete
- [ ] 9/9 full_step geometrically correct OR a legitimate PLAN hard stop report exists
- [ ] 1/1 scope-only case handled truthfully
- [ ] progress/report current
- [ ] commits pushed

---

# 121. PLANIN ANA PRENSİBİ

```text
Yanlış STEP üretmektense doğru yerde dur.
```

Sonra:

```text
doğru strateji
→ doğru view
→ doğru source measurements
→ generic CAD operation
→ STEP
→ evaluator
```

Plate'in başarılı olması:

```text
extrude-profile + holes/pocket
```

yolunun çalıştığını kanıtladı.

G12'nin görevi Plate mantığını her parçaya zorlamak değil;

```text
parçanın gerçek oluşturma stratejisini
kullanıcı-doğrulamalı ve generic biçimde seçip
mevcut CAD sözleşmesine bağlamak
```

olacaktır.
