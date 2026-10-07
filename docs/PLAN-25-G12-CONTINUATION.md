# PLAN.md — drawingto3d / PLAN-25-G12-CONTINUATION
## G12.1b’den final frozen-manifest kabulüne kadar yürütme planı
### Mevcut backend düzeltmesini UI/runner’a tamamla → implicit extrude’u kaldır → view/constraint/CAD kabiliyetlerini generic genişlet → 9/9 doğruluk

**Tarih:** 2026-10-07  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Doğrulanmış başlangıç `main` HEAD:** `5605cb598b8882d95869f959cfd035c85280edf1`  
**Aktif repo planı:** `PLAN-24-G12-CORRECTNESS`  
**Bu dosyanın rolü:** PLAN-24’ün güncel HEAD sonrası ayrıntılı devam/handoff planı  
**G12.0:** DONE — `b5e11c8`  
**G12.1a backend false-readiness:** DONE — `5605cb5`  
**G12.1b UI + runner v2:** NOT DONE  
**G12.2+ geometry strategy/CAD:** NOT DONE  
**Frozen manifest:** DEĞİŞMEYECEK  
**G11 ana metrik:** `1/9 full_step correct`  
**SEMREAD:** PARKED  
**Final hedef:** `9/9 full_step geometrically correct` + `1/1 callout_scope_only truthful`  

---

# 0. Hermes’e verilecek tek komut

> Bu PLAN.md’yi sırayla uygula. Başlangıç HEAD `5605cb598b8882d95869f959cfd035c85280edf1`. G12.0 ve G12.1a tamamlandı; bunları yeniden tasarlama. İlk iş G12.1b: yeni disposition backend sözleşmesini UI ve yeni G12 runner’a doğru bağla. UI hâlâ eski `unbindable` davranışını gösterdiği için G12.2’ye geçmeden bunu kapat. Sonra explicit build-strategy contract, view-scoped geometry, exact supported constraints, raster extrude recovery, revolve/axisymmetric, multi-view composite ve bounded advanced CAD capability sırasıyla ilerle. Frozen manifesti veya tarihsel G9/G11 kanıtlarını değiştirme. Reference STEP/evaluator verisi producer kararına giremez. Filename/case/hash/sample-coordinate hardcode yasak. Her fazda RED test → generic implementation → gerçek CAD/STEP → source-only guided run → evaluator → Plate guard → commit. Faz PASS olunca onay istemeden sonrakine geç. Yalnız bu plandaki HARD STOP koşullarında dur. `9/9 full_step` doğru olmadan G13 PASS deme.

---

# 1. Canlı check sonucu — mevcut HEAD’de ne değişti?

Son iki G12 commit:

```text
b5e11c8  G12.0 truth-lock
5605cb5  G12.1a disposition + coverage backend
```

G12.0 tamamlananlar:

```text
manifest 10/9/1 pinlendi
G11 correct-rate 1/9 pinlendi
G9 Plate evaluator tekrar PASS
reference producer/evaluator süreç sınırı eklendi
frozen historical hashes kaydedildi
ilgili suite 540 passed
```

G12.1a tamamlananlar:

```text
CALLOUT_SCHEMA_VERSION 3 → 4
not_model_input
redundant + duplicate_of
build_relevant_unsupported + reason
legacy ignored/unbindable → legacy_unclassified
callout_coverage(record)
coverage → build_readiness
set_disposition
set_ignored → not_model_input
set_unbindable → build_relevant_unsupported
bulk ignore yalnız not_model_input
GX export/import disposition desteği
```

G12 progress dosyası doğru biçimde:

```text
G12.0   DONE
G12.1a  DONE
G12.1b  waiting
G12.2+  waiting
```

diyor.

---

# 2. Canlı check sonucu — G12.1a henüz ürün yüzeyinde tamam değil

Backend yeni sözleşmeye geçti fakat `guided.html/js` hâlâ eski UX semantiğini taşıyor.

Şu anda UI’da hâlâ:

```text
[Modele uygulanmayacak]
```

butonu var ve:

```javascript
command('set_unbindable', ...)
```

çağırıyor.

Backend artık bu komutu:

```text
build_relevant_unsupported
```

olarak yorumluyor ve build’i BLOKLuyor.

Bu doğru backend davranışı fakat kullanıcı copy’si artık yanlış/eksik.

Daha önemlisi mevcut `guided.js`:

```javascript
if(row.ignored || row.unbindable) return true;
```

ile `rowResolved()` içinde `unbindable` satırı çözülmüş sayıyor.

Ayrıca successful command auto-advance listesinde:

```text
set_unbindable
```

var.

Sonuç:

```text
backend: unsupported gerçek ölçü = blocker
frontend navigation: unsupported gerçek ölçü = resolved/atla
```

Bu sözleşme çelişkisi G12.1b’nin ilk bug’ıdır.

---

# 3. Canlı check sonucu — eski G11 runner hâlâ blanket bulk davranışı taşıyor

Historical `g11_runner.py` halen:

```text
undecided = tüm kalan callout’lar
→ multi select
→ #callout-bulk-apply
→ kalanların tamamını ignored ilan et
```

yolunu kullanıyor.

Historical G11 dosyasını rewrite etme.

G12 için yeni runner v2:

```text
eval/g12_runner/
```

altında oluşturulacak.

Yeni runner:

```text
remaining != automatically not_model_input
```

olacak.

---

# 4. Dokümantasyon drift’i

`eval/g12_progress.md` güncel.

Fakat `docs/GUIDED_PROGRESS.md` dosyasının en üst legacy header’ı hâlâ:

```text
Current HEAD: 93194fa
Current task: G11 4/10 sürüyor
```

gibi tarihsel/stale bilgi taşıyor.

G12.1b tesliminde:

```text
üstte current snapshot
```

güncellenmeli.

Eski G1/G2/G3/G11 tarihsel tablolar silinmeyecek.

---

# 5. Test-count drift’i

G12.1a commit/README geniş regression için:

```text
630 passed
```

derken `eval/g12_progress.md` satırında:

```text
631 passed
```

görünüyor.

Bunu metinle tahmin ederek düzeltme.

G12.1b sonunda exact komutu tekrar koş ve tek authoritative sayı yaz:

```text
command
passed
failed
deselected
runtime
exit code
```

---

# 6. Değişmez kurallar

```text
machine detection != user decision
machine hint != transcription
parse != confirmation
proposal != target confirmation
ignored/not_model_input != unsupported geometry
valid STEP != correct STEP
bbox close != correct topology
reference STEP = evaluator only
```

Herhangi bir faz bunları gevşetirse FAIL.

---

# 7. Tarihsel kanıt freeze

Değiştirme:

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
eval/audits/20261007-guided-g11-fixes/**
```

Historical runner code da mümkünse değişmeden kalsın.

Yeni G12 runner ayrı namespace’te.

---

# 8. G12.1b — UI disposition sözleşmesini backend ile eşitle

## Amaç

Kullanıcı açıkça üç şeyden birini söyleyebilmeli:

```text
A. Bu modele ait bir geometri bilgisi değil.
B. Bu bilgi zaten başka bir kararla temsil ediliyor.
C. Bu gerçek geometri bilgisi ama bu sürüm uygulayamıyor.
```

A ve B kapsamı kapatabilir.

C build blocker’dır.

---

# 9. G12.1b UI copy — birebir uygulanacak

Normal kullanıcı metni:

```text
Bu bir ölçü/not değil
```

→ `not_model_input`

Yeni action:

```text
Zaten başka bir bilgiyle temsil ediliyor
```

→ `redundant`

Yeni action:

```text
Gerçek ölçü/not ama şu an modele uygulanamıyor
```

→ `build_relevant_unsupported`

Eski belirsiz:

```text
Modele uygulanmayacak
```

copy’sini kaldır/değiştir.

---

# 10. `target-unbindable` davranışı

Mevcut butonu semantik olarak yeniden kullanabilirsin fakat:

```text
ID = target-unbindable
```

kalabilir.

Kullanıcı label:

```text
Gerçek ölçü/not ama şu an modele uygulanamıyor
```

Command tercihen doğrudan:

```text
set_disposition(kind=build_relevant_unsupported)
```

kullansın.

Legacy `set_unbindable` UI’dan artık çağrılmasın.

Backend compatibility için kalabilir.

---

# 11. Unsupported disposition reason

`build_relevant_unsupported` reason boş bırakılamaz.

UI:

```text
Neden uygulanamıyor?
[______________________]
[Kaydet]
```

Minimum UX:

```text
textarea/input
```

Server hâlihazırda reason doğruluyorsa aynı command path’i kullan.

Frontend default fake reason yazmasın.

---

# 12. Redundant UX

Buton:

```text
Zaten başka bir bilgiyle temsil ediliyor
```

Tıklandıktan sonra:

```text
Dayanak seçin
```

Seçenekler:

```text
başka current callout
kalınlık kararı
dış profil kararı
kalibrasyon
hole decisions
bindings
view
trace
```

Backend’in current `decision:<name>` vocabulary’sini kullan.

Ham enum ana UI’da görünmesin.

---

# 13. Redundant citation validation UI

User:

```text
callout A redundant_of callout B
```

derse B:

```text
known
current
self değil
covered/compiled veya valid disposition
```

olmalı.

Server reject ederse:

```text
draft/selection preserved
error visible
no silent fallback
```

---

# 14. `rowResolved()` düzeltmesi

Current yanlış:

```javascript
if(row.ignored || row.unbindable) return true;
```

Yeni mantık backend disposition ile uyumlu olacak.

Resolved:

```text
not_model_input
redundant with valid reference
compiled/current callout
```

Unresolved/blocking:

```text
build_relevant_unsupported
legacy_unclassified
invalid/stale duplicate
stale transcription/parse/target
compile blocked
unclassified
```

Tercihen frontend kendi ikinci coverage engine’ini yazmasın.

Backend public/readiness response coverage bucket taşısın ve navigation onu kullansın.

---

# 15. Backend coverage UI authority

`build_readiness()` response’a açıkça ekle:

```json
{
  "coverage": {
    "counts": {},
    "coverage_complete": false,
    "rows": []
  }
}
```

veya mevcut public path içinde aynı bilgi.

Frontend:

```text
rowResolved = backend coverage bucket
```

olarak sadeleştirilsin.

Frontend parse/target state’lerinden coverage yeniden icat etmesin.

---

# 16. Next unresolved

`Sonraki eksik` şunları atlamamalı:

```text
build_relevant_unsupported
legacy_unclassified
invalid_duplicate
compile_blocked
stale
unclassified
```

Unsupported satıra geldiğinde panel:

```text
Bu gerçek bilgi şu an modele uygulanamıyor.
Model oluşturmak için bu capability çözülmeli veya karar düzeltilmeli.
```

desin.

---

# 17. Auto-advance

Auto-advance ONLY after row truly non-blocking becomes.

Allowed:

```text
transcription + complete target → compiled
not_model_input
valid redundant
```

NOT allowed:

```text
build_relevant_unsupported
failed disposition
legacy state
revision conflict
```

Current `set_unbindable` auto-advance kaldırılacak.

---

# 18. Readiness copy

Backend category copy:

```text
unsupported_build_relevant
→ “Bu gerçek ölçü/not mevcut modelleme yetenekleriyle uygulanamıyor.”

legacy_unclassified
→ “Bu alan eski oturumda kapsam dışı bırakılmış; nedenini yeniden seçin.”

stale_duplicate_reference
→ “Bu bilgi için seçilen dayanak artık güncel değil.”
```

Checklist item tıklanınca ilgili callout seçilecek.

---

# 19. Coverage summary UI

`Eksik kalanlar` üstünde küçük summary:

```text
42 modele ait değil
6 modele uygulandı
1 desteklenmiyor
2 kontrol bekliyor
```

Bu yalnız backend counts.

Ama normal kullanıcıya teknik bucket isimleri gösterme.

---

# 20. G12.1b RED browser/DOM tests

Önce RED:

```text
unsupported row is NOT rowResolved
unsupported action does NOT auto-next
unsupported action keeps build disabled
not_model_input resolves
valid redundant resolves
invalid redundant remains unresolved
legacy ignored remains unresolved
coverage count rendered from backend
```

---

# 21. G12.1b real Chrome acceptance

Yeni:

```text
eval/audits/20261007-g12-decision-coverage/browser/
```

Senaryo A — not model input:

```text
select metadata row
Bu bir ölçü/not değil
→ not_model_input
→ next unresolved advances
```

Senaryo B — unsupported:

```text
select real callout
mark unsupported + reason
→ build disabled
→ row still appears in unresolved/blocker navigation
```

Senaryo C — redundant:

```text
create/choose represented callout
mark second redundant
choose valid reference
→ coverage resolved
```

Senaryo D — stale duplicate:

```text
make cited target stale
→ redundant becomes blocker
```

Senaryo E — reload/undo:

```text
reload preserves disposition
undo restores prior state
```

---

# 22. G12 runner v2 — yeni dosya, G11 runner’a dokunma

Yeni:

```text
eval/g12_runner/recipe_v2.py
eval/g12_runner/g12_runner.py
```

G12.0 producer/evaluator boundary modüllerini reuse et.

---

# 23. Recipe v2 schema

```json
{
  "case_id": "...",
  "source_sha256": "...",
  "operator_basis": "source_drawing_only",
  "callout_actions": [
    {
      "callout_id": "...",
      "action": "not_model_input",
      "reason": "title block drawing number"
    }
  ],
  "profile_actions": [],
  "view_decisions": [],
  "strategy_decision": null,
  "dimension_bindings": [],
  "feature_links": [],
  "notes": []
}
```

---

# 24. Runner v2 — forbidden behavior

YASAK:

```text
undecided = all remaining
→ bulk ignore all
```

YASAK fields:

```text
ignore_rest
bulk_remaining
ignore_all_unhandled
```

Parser validation bunları reddetsin.

---

# 25. Runner v2 source-side dispositions

Every action explicit:

```text
callout_id
kind
reason
```

Bulk allowed only if recipe explicitly lists IDs:

```json
{
  "action": "bulk_not_model_input",
  "callout_ids": ["...", "..."],
  "reason": "title block rows"
}
```

Runner otomatik ID ekleyemez.

---

# 26. Runner v2 reference guard

Recipe producer side must NOT contain:

```text
reference bbox
reference volume
reference face count
reference cylinders
expected feature count
reference STEP path
```

Static schema test.

---

# 27. G12.1b progress cleanup

Fix top of `docs/GUIDED_PROGRESS.md`:

```text
Current HEAD: <new G12.1b commit>
Active plan: PLAN-24 + continuation
Current task: G12.1b complete / G12.2 next
G11 baseline: 1/9
```

Do not delete historical sections.

---

# 28. G12.1b regression gate

Focused:

```text
tests/test_callout_coverage.py
tests/test_guided_disposition.py
tests/test_guided_callout_http.py
tests/test_guided_html.py
tests/test_guided_callout_ux_advance.py
tests/test_callout_review.py
```

Then exact broad command:

```bash
pytest -q tests -k "not semread"
```

Reconcile 630/631 count by recording this run only.

---

# 29. G12.1b DONE definition

All required:

- UI exposes all three dispositions
- old “Modele uygulanmayacak” ambiguity removed
- unsupported needs reason
- redundant needs valid citation
- rowResolved follows backend coverage
- unsupported remains blocker/navigation item
- unsupported does not auto-advance
- bulk only not_model_input
- G12 runner v2 has no blanket remaining-ignore
- real Chrome passes
- broad not-semread green
- progress top current
- historical G11 evidence unchanged

PASS → G12.2.

---

# 30. G12.2 — explicit build strategy contract

Current biggest geometry bug:

```text
selected profile
→ implicit extrude
```

G12.2 removes this.

P2 does NOT need full revolve implementation yet.

It creates the strategy contract + safe dispatch.

---

# 31. BuildStrategyDecision model

Add to `Decisions`:

```python
class BuildStrategyDecision(BaseModel):
    kind: Literal[
        "extrude_profile",
        "revolve_profile",
        "multi_view_composite",
        "unsupported",
    ]
    primary_view_id: str | None = None
    section_view_id: str | None = None
    axis: Literal["X", "Y", "Z"] | None = None
    geometry_version: int
    strategy_key: str
    evidence: list[EvidenceRef]
```

`Decisions.build_strategy: BuildStrategyDecision | None = None`

Backward-compatible default None.

---

# 32. Build strategy is USER decision

System may produce:

```text
BuildStrategyProposal
```

but cannot persist strategy automatically.

Only user/external review explicit confirmation.

---

# 33. Strategy proposal module

New pure module:

```text
src/drawingto3d/build_strategy.py
```

Functions:

```python
propose_strategies(record) -> list[BuildStrategyProposal]
strategy_key(record, decisions=None) -> str
strategy_state(record) -> current/stale/missing
```

No filesystem/network/model/reference.

---

# 34. Strategy proposal evidence

Allowed:

```text
selected profile kind
confirmed/observed view information
section evidence
profile closure
concentric circle evidence
axis/centreline evidence
archetype only as weak evidence
```

Forbidden:

```text
case_id
filename
SHA
reference STEP
expected bbox
```

---

# 35. Safe proposal v1

At G12.2:

```text
closed non-circle profile + explicit thickness
→ extrude_profile proposal
```

Circle profile:

```text
DO NOT auto-propose high-confidence extrude
```

Revolve/multi-view proposals may be labeled:

```text
candidate / capability pending
```

until P6/P7 implementation.

---

# 36. Strategy persistence command

Add server command/API path, e.g.:

```text
set_build_strategy
```

Rules:

```text
one revision
one history step
undoable
reopen stable
server pins strategy_key
client cannot forge geometry_version/key
```

---

# 37. Strategy freshness v1

Stale on:

```text
profile_id change
contour correction change
existing sheet ViewConfirm change
geometry_version change
primary/section view decision later change
```

Do not key to unrelated UI edits.

---

# 38. make_plan dispatch

Refactor:

```text
make_plan
  → prepare_common_context
  → strategy dispatch
```

Functions:

```python
compile_extrude_plan(ctx)
compile_revolve_plan(ctx)      # P6 until then controlled unsupported
compile_multiview_plan(ctx)    # P7 until then controlled unsupported
```

NO default extrude.

---

# 39. Circle safety guard

Mandatory test:

```text
profile.kind == circle
+ strategy missing
→ no GeneralPlan
```

Even if:

```text
thickness exists
calibration exists
trace acknowledged
```

No accidental disk.

---

# 40. Explicit circle extrude

A real circular plate must still be possible.

Requires explicit:

```text
strategy = extrude_profile
```

confirmation.

No geometry-class blacklist.

---

# 41. Strategy readiness categories

Add:

```text
missing_build_strategy
stale_build_strategy
unsupported_build_strategy
```

Backend build uses same readiness.

---

# 42. Strategy UI

Panel/checklist task:

```text
Parçanın ana oluşturma biçimi

○ Sabit kalınlıklı profili uzat
○ Bir kesiti eksen etrafında döndür
○ Birden fazla görünüşü birlikte kullan
○ Bu sürümde desteklenmiyor
```

Technical evidence collapsed.

---

# 43. G12.2 RED tests

```text
missing strategy blocks make_plan
circle without strategy does not extrude
extrude strategy compiles existing Plate path
strategy client key forging ignored/rejected
profile change stales strategy
contour correction stales strategy
undo/reopen
unsupported strategy blocks
```

---

# 44. G12.2 Plate acceptance

Fresh Plate session:

```text
review callouts
confirm extrude strategy
build
STEP reopen
frozen Plate evaluator PASS
```

Plate must remain:

```text
120 × 80 × 15
4 holes
1 pocket
```

within frozen tolerances.

PASS → G12.3.

---

# 45. G12.3 — view-scoped geometry foundation

Do this BEFORE serious revolve/multi-view work.

Existing `views.py` is present but guided geometry is not adequately view-owned.

---

# 46. Persist view candidates once

On session create:

```text
load_page
segment_views(page)
```

Store machine candidates:

```text
view_candidates
```

Load/reopen must not silently resegment.

A reader/geometry migration may re-read under normal version rules.

---

# 47. Separate two concepts

Existing `ViewConfirm`:

```text
sheet/page axis orientation
```

New decision must represent:

```text
which orthographic/section views are used for solid
```

Do not overload old `ViewConfirm`.

Suggested:

```python
class DrawingViewDecision(BaseModel):
    view_id: str
    role: Literal["primary", "plan", "side", "section", "isometric_ignore", "unused"]
    geometry_version: int
```

---

# 48. Assign geometry to view

Add to base geometry where deterministic:

```text
profile.view_id
circle.view_id
primitive.view_id
```

Rule:

```text
fully/strongly inside one candidate → that view
ambiguous overlap → None
```

No nearest-view guess across ambiguous border.

---

# 49. Geometry contract bump

Because base geometry identity now includes view ownership:

```text
GEOMETRY_VERSION 3 → 4
```

should be considered/required.

If Hermes chooses not to bump, it must prove old target/strategy identities cannot remain falsely current.

Default recommendation: BUMP.

---

# 50. geometry_key update

Target geometry fingerprint includes:

```text
profile.view_id
circle.view_id
confirmed drawing-view decisions
```

Old target should stale when view ownership changes.

---

# 51. View UI

Canvas overlays:

```text
Görünüş 1
Görünüş 2
Kesit adayı
İzometrik adayı
```

User can classify.

No required machine auto-classification truth.

---

# 52. Geometry menu filtering

After primary view confirmed:

```text
profile list = that view by default
circle list = that view by default
```

Debug:

```text
Tüm geometrileri göster
```

allowed.

Compiler never uses cross-view geometry without explicit relation.

---

# 53. P3 RED tests

```text
profile gets view_id
circle gets view_id
ambiguous geometry gets None
cross-view target rejected or requires explicit relation
view role change stales target
view role change stales strategy
isometric default not solid source
legacy session migration safe
```

---

# 54. P3 real browser

Open a real multi-view source.

Without reference:

```text
view overlays visible
user selects primary/section roles
profile menu scopes
reload persists
```

No build correctness claim yet.

PASS → G12.4.

---

# 55. G12.4 — exact supported 2D constraints

Current trace + calibration is not sufficient for dimensionally correct shape.

Supported V1:

```text
X vertex-pair distance
Y vertex-pair distance
overall width
overall height
circle centre X spacing
circle centre Y spacing
diameter/radius values
```

---

# 56. Solver principle

Printed values control supported coordinates exactly.

Do NOT:

```text
fit one global scale and call dimensions applied
```

Do:

```text
constraint equations
→ solved coordinates
```

---

# 57. Provenance

Every solved coordinate records:

```text
binding id
callout id if any
printed value
unit
geometry targets
equation type
```

Trace coordinates separately flagged.

---

# 58. Solver statuses

```text
constrained
underconstrained
conflict
unsupported
```

No automatic averaging of conflicting dimensions.

---

# 59. Underconstrained policy

A draft may build only with explicit:

```text
trace assumption acknowledgement
```

Audit:

```text
dimension-derived coordinates = N
trace-derived coordinates = M
```

Final evaluator success still decides correctness.

---

# 60. P4 real CAD synthetic tests

Generate actual STEP and reopen:

```text
rectangle exact width/height
circle centres exact spacing
hole diameter exact
conflicting width refuses
underconstrained count correct
```

PASS → G12.5.

---

# 61. G12.5 — raster extrude recovery

Before reference evaluation classify manifest cases by SOURCE DRAWING ONLY.

Create committed:

```text
eval/audits/20261007-g12-raster-profile/cluster-classification.json
```

Fields:

```text
case_id
source_observed_views
source_observed_geometry_style
proposed_strategy_class
current_blocker
basis
```

---

# 62. Allowed cluster labels

```text
extrude_profile
axisymmetric_revolve
multi_view_composite
advanced_operation
insufficient_source_information
```

Production does not read this file.

---

# 63. Raster contour audit

Expose:

```text
profile id
view id
primitive ids
closed
self-intersection
join gaps
movement applied
bbox
area
line count
arc count
```

---

# 64. No tolerance tuning by sample

YASAK:

```text
Exercise13 needs 28px → set 28
```

Allowed:

```text
generic detector uncertainty study
synthetic 1/2/3/5px gaps
```

---

# 65. P5 real source gate

At least one source-classified `extrude_profile` case that was wrong/blocked in G11 must become:

```text
STEP produced
STEP reopen
shape_ok
 detail_ok
verdict PASS
```

Only then P5 PASS.

---

# 66. G12.6 — axisymmetric/revolve

Requirements:

```text
confirmed revolve strategy
confirmed section/profile view
confirmed axis
verified source dimensions
```

Face-on circle alone not enough.

---

# 67. Revolve representation

Use existing GeneralPlan `RevolveOp`.

Local section:

```text
radius >= 0
axial coordinate
```

No new CAD engine.

---

# 68. Revolve supported dimensions

```text
diameter → radius = d/2
radius
axial length
step diameter
step length
bore diameter
```

Source/user confirmed only.

---

# 69. Revolve features

After base revolve:

```text
bore → CutOp
face holes → CutOp
repeated holes → RepeatOp + CutOp
```

Only when source provides count/pattern/targets.

---

# 70. P6 synthetic real CAD

```text
stepped shaft
flange-like revolved body + bore
4 repeated holes
profile crossing axis rejected
missing axis blocked
face circle no section blocked
```

---

# 71. P6 real source gate

At least one previously `CAD_WRONG` axisymmetric case:

```text
→ evaluator PASS
```

Do not accept merely “bbox improved”.

PASS → G12.7.

---

# 72. G12.7 — multi-view composite v1

V1 is bounded:

```text
base = extrude OR revolve
secondary views supply feature depth/placement
```

Not arbitrary B-rep reconstruction.

---

# 73. ViewGraph

```python
ViewGraph:
    views
    relations
    primary
```

Relations:

```text
front ↔ plan
front ↔ side
section_of
```

Machine proposal + user confirmation.

---

# 74. FeatureLinkDecision

Cross-view information must explicitly say:

```text
these callouts/geometries describe same feature
```

Model:

```python
FeatureLinkDecision:
    feature_key
    callout_ids
    view_ids
    target_geometry_ids
```

---

# 75. No cross-view proximity magic

Same-size circles in two views:

```text
not automatically same feature
```

Need explicit relation.

---

# 76. P7 generic supported composition

Examples:

```text
front diameter + section depth → blind bore
front position + side depth → pocket/cut
front repeated holes + section thickness → through holes
```

---

# 77. P7 source gate

At least one source-classified multi-view full_step case:

```text
→ evaluator PASS
```

PASS → G12.8.

---

# 78. G12.8 — advanced bounded operation audit

Do NOT immediately add everything.

Create:

```text
capability-gap.json
```

Per remaining failure:

```text
source evidence
strategy
missing operation
existing GeneralPlan expressible?
small generic extension?
architecture-sized?
```

---

# 79. Existing geo capability reminder

Already available:

```text
fillet_edges
chamfer_edges
ring_revolve
fuse
cut
```

If GeneralPlan lacks exposure but source requires it, add bounded typed operation.

---

# 80. Fillet/chamfer

If needed:

```text
FilletOp
ChamferOp
```

with strict typed selection.

Do not allow arbitrary raw CadQuery selector from untrusted UI JSON.

---

# 81. Taper/cone

Prefer represent as revolve profile.

Do not add special op unless generic necessity proven.

---

# 82. Shell

Small extension only if:

```text
constant wall thickness
clear opening/face contract
```

Otherwise architecture-sized HARD STOP.

---

# 83. Sweep/elbow

Do not wire sample to `geo.ring_revolve`.

Either:

```text
generic typed SweepOp
```

or HARD STOP.

---

# 84. Every new CAD op test

Required:

```text
Pydantic validation
compiler output
real CadQuery
STEP export
STEP reopen
numeric geometry
negative cases
```

---

# 85. G12.9 — frozen manifest rerun

Fresh sessions.

Same final product HEAD.

No code edits during run.

Frozen manifest unchanged.

---

# 86. Producer/evaluator isolation

Use G12.0 split:

```text
produce_case.py
evaluate_case.py
```

Producer input strips:

```text
reference_identifier_evaluator_only
```

and any reference-derived values.

---

# 87. Final runner metrics

Per case:

```text
candidate_count
coverage buckets
strategy
views used
operation types
dimension-derived coords
trace-derived coords
build status
STEP reopen
shape_ok
detail_ok
verdict
user interventions
```

---

# 88. Main metrics

```text
GUIDED_CORRECT_STEP_RATE = correct / 9
WRONG_STEP_RATE = produced_wrong / 9
BLOCKED_RATE = blocked / 9
```

Do not reduce denominator.

---

# 89. Final target

Reference-backed:

```text
9/9 correct
0 wrong
0 unproduced
```

Scope-only:

```text
1/1 honest callout/scope result
```

---

# 90. Plate regression policy

After every architecture-level change:

```text
Plate replay
→ explicit extrude strategy
→ STEP
→ frozen evaluator PASS
```

Plate is regression guard.

Never tune generic algorithm only to Plate.

---

# 91. Wrong output safety principle

If new guard turns:

```text
wrong STEP
```

into:

```text
honest blocker
```

that is an improvement even if correct-rate temporarily unchanged.

Record both:

```text
wrong_step_rate
blocked_rate
```

---

# 92. Three-hypothesis rule

Same blocker max 3 generic hypotheses.

Each must record:

```text
hypothesis
evidence
RED test
implementation
synthetic result
real source result
```

Three fail:

```text
HARD STOP
```

No secret fourth sample tweak.

---

# 93. HARD STOP

Only if:

1. same capability has 3 failed generic hypotheses;
2. source/user input lacks a fact required for reference geometry;
3. producer would need reference STEP/evaluator fact;
4. required CAD paradigm is beyond bounded GeneralPlan extension;
5. evaluator cannot be made reliable independently;
6. only sample-specific hardcode can pass;
7. destructive historical evidence rewrite needed.

---

# 94. NOT HARD STOP

Do not stop for:

```text
ordinary failed test
UI bug
migration bug
view segmentation bug
constraint bug
CAD implementation bug
one real case failure
runner bug
```

Fix and continue.

---

# 95. No-hack static guard

Production `src/drawingto3d` must not branch on:

```text
plate-pocket-vector
drawing-2-vector
plastic-enclosure-vector
exercise-12-vector
exercise-51-raster
exercise-17-raster
exercise-13-raster
my-part-raster
flange-raster
```

Nor manifest SHA values.

---

# 96. Reference leakage static guard

Production must not read:

```text
eval/guided_10_manifest.json
reference_identifier_evaluator_only
reference STEP files
```

Evaluator namespace can.

---

# 97. Phase execution template

Every phase:

```text
1 inspect exact current code
2 write RED regression
3 confirm RED for expected reason
4 implement minimal generic contract
5 focused tests green
6 relevant historical regression
7 real CAD if geometry changed
8 real Chrome if UX changed
9 source-only real run
10 evaluator only after output exists
11 Plate guard
12 git diff --check
13 no-hack/reference scan
14 progress update
15 commit
16 immediately next phase
```

---

# 98. Broad regression checkpoints

Run:

```bash
pytest -q tests -k "not semread"
```

after:

```text
G12.1b
G12.2
G12.4 constraints
G12.6 revolve
G12.7 multi-view
final G12.9
```

---

# 99. Real Chrome checkpoints

Mandatory for:

```text
G12.1b dispositions
G12.2 strategy confirmation
G12.3 view assignment
G12.6 axis/section selection
G12.7 feature links
```

---

# 100. Evidence directories

```text
eval/audits/20261007-g12-decision-coverage/browser/
eval/audits/20261007-g12-build-strategy/
eval/audits/20261007-g12-views/
eval/audits/20261007-g12-constraints/
eval/audits/20261007-g12-raster-profile/
eval/audits/20261007-g12-axisymmetric/
eval/audits/20261007-g12-multiview/
eval/audits/20261007-g12-advanced/
eval/audits/20261007-g12-manifest-reruns/
```

No overwrite of previous runs.

---

# 101. Immediate next exact work — Hermes buradan başlasın

### Step 1

Add RED tests proving current UI mismatch:

```text
unsupported is not resolved
unsupported does not auto-next
unsupported remains readiness blocker
```

### Step 2

Expose backend coverage in readiness/public response.

### Step 3

Refactor `rowResolved()` to backend coverage.

### Step 4

Replace old ambiguous “Modele uygulanmayacak” UX with explicit unsupported reason flow.

### Step 5

Add redundant + citation flow.

### Step 6

Run real Chrome disposition acceptance.

### Step 7

Create G12 runner v2 and remove blanket remaining-ignore behavior from NEW runner.

### Step 8

Run broad not-semread suite and reconcile test-count drift.

### Step 9

Update progress current header.

### Step 10

Commit G12.1b.

Then automatically begin G12.2.

---

# 102. G12.1b expected files

Likely:

```text
src/drawingto3d/callout_readiness.py
src/drawingto3d/static/guided.html
src/drawingto3d/static/guided.js
src/drawingto3d/app.py       # only if response/API needed
src/drawingto3d/guided.py    # only if public coverage/command surface needed
src/drawingto3d/callout_review.py

tests/test_guided_html.py
tests/test_guided_callout_ux_advance.py
tests/test_guided_disposition.py
tests/test_guided_callout_http.py
tests/test_callout_coverage.py

eval/g12_runner/**
eval/audits/20261007-g12-decision-coverage/browser/**
```

Do not change CAD in G12.1b.

---

# 103. G12.2 expected files

Likely:

```text
src/drawingto3d/build_strategy.py
src/drawingto3d/guided.py
src/drawingto3d/static/guided.html
src/drawingto3d/static/guided.js
src/drawingto3d/callout_readiness.py

tests/test_build_strategy.py
tests/test_guided_build_strategy.py
```

Keep strategy pure logic out of JS.

---

# 104. G12.3/P3 expected files

Likely:

```text
src/drawingto3d/views.py
src/drawingto3d/guided.py
geometry option builder module(s)
callout_models geometry_key
```

If geometry ownership changes persisted identity:

```text
GEOMETRY_VERSION bump
```

with migration tests.

---

# 105. Current successful backend contracts to preserve

G12.1a already passed:

```text
not_model_input
redundant
build_relevant_unsupported
legacy_unclassified
callout_coverage
set_disposition
GX disposition import/export
```

Do not throw these away and create a parallel system.

UI/runner must consume them.

---

# 106. Current known stale comments/copy

Update misleading source comments such as build path claims equivalent to:

```text
“unbindable is a scope decision, not a blocker”
```

because G12.1 semantics changed.

Comments/tests/docs must agree with code.

---

# 107. Commit sequence recommendation

```text
G12.1b-1  UI coverage authority + navigation RED/green
G12.1b-2  disposition UX + real Chrome
G12.1b-3  G12 runner v2 + broad regression/progress
G12.2-1   BuildStrategy schema/proposals/store
G12.2-2   make_plan dispatch + Plate acceptance
G12.3     view-scoped geometry
G12.4     exact constraints
G12.5.x   raster extrude capability
G12.6.x   revolve capability
G12.7.x   multi-view capability
G12.8.x   bounded advanced ops
G12.9     frozen manifest rerun
```

---

# 108. Final DONE checklist

Hermes may say “G12 complete” only if ALL:

- [ ] G12.1b UI matches disposition backend
- [ ] unsupported row blocks and stays actionable
- [ ] redundant citation works
- [ ] new G12 runner has no blanket-ignore remainder
- [ ] docs progress current
- [ ] implicit extrude removed
- [ ] circle cannot silently become disk
- [ ] explicit strategy persisted/freshness-safe
- [ ] view-scoped geometry implemented
- [ ] cross-view accidental target impossible
- [ ] supported printed dimensions control geometry exactly
- [ ] raster extrude generic capability produces at least one recovered correct case
- [ ] revolve generic capability produces at least one recovered correct case
- [ ] multi-view v1 produces at least one recovered correct case
- [ ] remaining CAD gaps are closed or legitimate hard stop
- [ ] no case/hash/filename production hardcode
- [ ] no reference leakage
- [ ] Plate stays PASS
- [ ] final broad not-semread green
- [ ] frozen manifest unchanged
- [ ] final frozen run = 9/9 full_step correct
- [ ] scope-only = truthful/no silent guess
- [ ] evidence + progress committed/pushed

---

# 109. Final product statement allowed only after success

Allowed:

```text
Frozen guided evaluation:
9/9 reference-backed full_step cases geometrically correct;
1/1 scope-only case handled without silent geometry claim.
```

Not allowed:

```text
arbitrary drawings solved
fully automatic
all technical drawings supported
```

---

# 110. Tek cümlelik yön

```text
Önce yanlış STEP üretmeyi imkânsızlaştır; sonra doğru build strategy + doğru view + gerçek ölçü constraints + mevcut generic CAD operations ile doğruluğu yükselt.
```
