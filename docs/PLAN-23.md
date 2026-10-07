# PLAN.md — drawingto3d / PLAN-23-HERMES-CONTINUOUS
## Guided Transcription → Semantics → Binding → CAD → 10-Sheet Acceptance
### Tek yetkiyle son kabul kapısına kadar kesintisiz yürütme planı

**Tarih:** 2026-10-06  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Doğrulanan başlangıç `main` HEAD:** `510bc3297851d23135c8ea382c7583dfc18ec848`  
**Tamamlanan temel:** G0 + G1 + G2 + G3 + G3R  
**Bu planın yetkisi:** H0 → G4 → G5 → G6 → GX → G7 → G8 → G9 → G10 → G11 → G12 loop → G13 → CLOSEOUT  
**SEMREAD-001D:** PARKED; bu plan full-page VLM araştırmasını yeniden açmaz  
**Model çağrısı:** varsayılan `0`  
**Ana hedef:** fixed 10-sheet sette kullanıcı-doğrulamalı akışla geometrik olarak doğru STEP  
**Operasyon kuralı:** Kullanıcı bu planı “uygula” diye verdiğinde fazlar arasında tekrar onay isteme.

---

# 0. Hermes’e verilecek başlangıç mesajı

> Kök `PLAN.md`yi uygula ve bu planın bitiş kriterine ulaşana kadar fazlar arasında tekrar kullanıcı onayı istemeden devam et. Başlangıç HEAD’i `510bc3297851d23135c8ea382c7583dfc18ec848`. G0/G1/G2/G3/G3R tamamlandı; bunları yeniden yazma. Önce H0 baseline hygiene’i kapat, ardından G4 deterministic parser, G5 target proposal, G6 target confirmation, GX review export/import, G7 confirmed callout → existing guided decisions compiler, G8 readiness/audit, G9 Plate golden path, G10 fixed 10-sheet manifest, G11 first run, G12 generic-fix loop ve G13 final acceptance sırasıyla ilerle. Her fazda test-first, provenance, no-guess, no-reference-leak ve session/revision/undo invariants korunacak. Bir faz kabul kapısını geçince otomatik sonraki faza geç. Yalnız bu plandaki HARD STOP koşullarında dur. G13 bitmeden “tamamlandı” deme.

---

# 1. Güncel durum

```text
HEAD = 510bc3297851d23135c8ea382c7583dfc18ec848

DONE
G0     guided-transcription pivot
G1     callout contracts + freshness + undo/stale
G1R1   independent fixes
G1R2   effective-contour target + reconfirm log
G2     Observations → deterministic CalloutCandidate
G3     overlay / crop / transcription / ignore / manual region UI
G1R3   point-identity tolerance fix
G3R    record-boundary hardening

LATEST ACCEPTANCE
304 selected pytest PASS
4 independent probes PASS
real Chrome 30/30 PASS
git diff --check clean
model calls = 0
```

Henüz yok:

```text
real deterministic semantic parser
automatic target proposal engine
proposal-based target confirmation UX
review export/import
confirmed callout → CAD decisions compiler
callout-aware build readiness
new guided Plate end-to-end
fixed 10-sheet acceptance
```

---

# 2. Kesintisiz yürütme yetkisi

Bu plan uygulanırken normal davranış:

```text
phase accepted
→ progress update
→ commit
→ immediately next phase
```

Hermes şu soruları sormaz:

```text
“G5’e geçeyim mi?”
“G6’yı açayım mı?”
“10-sheet run’a başlayayım mı?”
```

Yetki yalnız bu dosyanın scope’u için geçerlidir.

---

# 3. HARD STOP — yalnız bunlarda dur

1. Mevcut session/history migration’ı geri döndürülemez veri kaybı riski taşıyorsa.
2. Çözüm yeni CAD engine, yeni model servisi veya full-page VLM’i kritik yola koymayı gerektiriyorsa.
3. Doğru sonuç için reference STEP/evaluator bilgisini producer’a vermek gerekiyor gibi görünüyorsa.
4. Fixed 10-sheet manifestte temel scope krizi varsa ve generic çözüm makul değilse.
5. Aynı blocker için üç kaydedilmiş ve ayrıştırıcı hipotez başarısız olduysa.
6. Acceptance/evaluator güvenilmez ve küçük düzeltmeyle güvenilir hale getirilemiyorsa.
7. Force-push/history rewrite/kullanıcı dosyasını destructive overwrite ihtiyacı varsa.
8. Gerekli gerçek browser/CAD testini ortam nedeniyle koşmak mümkün değil ve dürüst alternatif kanıt yoksa.

Bunların dışında kullanıcı onayı beklemeden çöz ve devam et.

---

# 4. Değişmez ürün ilkeleri

```text
base observation ≠ user decision ≠ computed result
machine hint ≠ user transcription
semantic parse ≠ raw user text
target proposal ≠ target confirmation
valid STEP/solid ≠ correct geometry
OCR ≠ truth
reference STEP = evaluator-only
```

No-guess:

```text
yazmayan bilgiyi uydurma
belirsizliği açık bırak
unsupported ≠ guessed success
```

---

# 5. Repo / commit hijyeni

Başlangıçta kaydet:

```text
git status --short
git rev-parse HEAD
git log -5 --oneline
```

`PLAN-17-HERMES.md` gibi kullanıcı/untracked dosyalarını stage etme. `git add .` kullanma. Her faz logical commit. Historical numbered plans overwrite edilmez.

---

# 6. H0 — temiz baseline

## H0.1 planner pin

Bilinen full-suite kırmızı:

```text
tests/test_planner.py::test_settings_record_is_the_run_record_fields
```

Current `ChatSettings.as_dict()` artık:

```text
repeat_penalty
repeat_last_n
```

alanlarını taşıyor.

Düzeltme:

```text
production behavior geri alınmaz
test pinli key seti current run-record contract’a güncellenir
```

Önce single failing test, sonra `tests/test_planner.py`.

## H0.2 full baseline

Ardından:

```text
python -m pytest -q
```

Hedef: `0 failures`.

## H0 acceptance

- planner pin current contract ile uyumlu
- targeted planner tests green
- full pytest green veya yalnız HARD STOP sınıfı environment blocker dürüst kayıtlı
- progress exact counts/runtime/HEAD ile güncel

PASS → commit → otomatik G4.

---

# 7. G4 — deterministic callout parser

Amaç:

```text
TranscriptionDecision.raw_text
→ deterministic SemanticParse
```

Authority yalnız kullanıcı transcription’ıdır; machine hint authority değildir.

Önerilen modül:

```text
src/drawingto3d/callout_parse.py
```

Pure API:

```python
parse_callout(raw_text: str, *, sheet_unit: str | None = None) -> SemanticParse
```

No filesystem/network/model/OCR/reference.

Parser identity:

```text
CALLOUT_PARSER_VERSION = "callout-parser/2"
```

(v2: standart `THRU ALL` niteleyicisi — G9 koşusunda paftadaki `4 x Ø6,80 THRU ALL` notu okunamadığı
için genel düzeltme; v1 okumaları bu sürümle bayatlar.)

---

# 8. G4 grammar v2

Destek:

```text
plain number
integer / decimal
mm / in
Ø / ⌀ / DIA / DIAM
R
x / X / × count
THRU / THROUGH
THRU ALL / THROUGH ALL (standart niteleyici; yalnız THRU'dan hemen sonra)
DEPTH / DEEP
simple diameter + depth
simple radius
plain linear dimension
```

Pozitif matrix:

```text
25
25.0
25 mm
Ø8
⌀8
DIA 8
8 DIA
R5
4x Ø8
4 X Ø8
4 × Ø8 THRU
4 x Ø6,80 THRU ALL
Ø8 THROUGH ALL
Ø10 6 DEEP
Ø10 DEPTH 6
.375 DIA
```

No-guess:

```text
Ø8 → diameter=8
NOT auto hole
NOT auto thru
NOT auto count=1

R5 → radius=5
NOT auto fillet
```

Unit yoksa `unresolved`.

Error taxonomy en az:

```text
empty_text
unsupported_syntax
ambiguous_number
missing_value_after_symbol
conflicting_symbols
conflicting_units
count_without_feature
unknown_tokens
```

---

# 9. G4 integration ve kabul

Transcription değişirse parse stale. Ignored callout build-relevant sayılmaz. Parser event user event değildir.

UI parsed summary gösterir:

```text
raw text
form
size
count
unit
termination
depth
warnings
status
```

G4 gate:

- pure/deterministic parser
- positive + negative matrix
- Unicode/whitespace properties
- raw text preserved
- no-guess
- parse freshness
- old session compatibility
- UI summary
- selected regressions green
- real browser acceptance extended

PASS → commit → G5.

---

# 10. G5 — deterministic target proposal

Amaç:

```text
callout region
+ current SemanticParse
+ current geometry
+ deterministic evidence
→ ranked TargetProposal[]
```

Proposal user decision değildir.

Önerilen:

```text
src/drawingto3d/callout_bind.py
```

TargetProposal:

```text
callout_id
target_kind
target_ids[]
geometry_version
evidence_tier
evidence[]
```

Evidence priority:

```text
T0 existing explicit deterministic bind evidence
T1 leader / arrow connectivity
T2 dimension / extension-line topology
T3 semantic geometry compatibility
T4 count compatibility
T5 spatial proximity
```

Examples:

```text
diameter → circle/circle_group candidate
radius → arc candidate
plain linear → vertex_pair/edge candidate
```

Ama `circle → hole` otomatik inference değildir.

Ambiguous → multiple proposals. No valid → `[]`.

G5 tests:

```text
Ø8 one circle
R5 one arc
4xØ8 group
leader beats proximity
ambiguous two circles
no compatible target
diameter does not create physical hole
count does not invent geometry
deterministic ranking
```

PASS → commit → G6.

---

# 11. G6 — target confirmation UX

Flow:

```text
proposal highlight
→ user confirm
OR
→ user selects another target
```

UI modes:

```text
target-circle
target-group
target-arc
target-endpoints
target-profile
```

Panel:

```text
Önerilen hedef
[Onayla]
[Başka hedef seç]
[Birden fazla hedef seç]
[Bağlama yok / desteklenmiyor]
```

Existing `CalloutTargetDecision` ve explicit reconfirm contracts reuse.

Stale triggers:

```text
geometry/profile/contour change
transcription revision change
parser binding/version change
relevant region change
```

Real browser acceptance:

```text
transcribe Ø8
parse visible
proposal highlight
confirm
reload
geometry change → stale
manual reselect/reconfirm
undo/reopen
```

PASS → commit → GX.

---

# 12. GX — review export/import

Bu faz özellikle G4–G6 sonrasında yapılır.

Amaç:

```text
session review bundle export
→ external reviewer
→ reviewed actions import
→ same server validation/history/revision path
```

Bu sayede ChatGPT/Hermes kullanıcı yerine review kararlarını hazırlayabilir.

Export en az:

```text
schema_version
session token/id
base_revision
source_digest
page
callout IDs
regions
machine hint
raw transcription
semantic parse
target proposals
confirmed target
ignored/freshness state
```

Import action set ilk sürüm:

```text
transcribe
ignore
restore
confirm_target
select_target
```

Critical invariant:

```text
IMPORT
→ existing edit/confirmation validation
→ history
→ revision
→ stale handling
→ audit
```

Arka kapıdan record mutation yok.

Provenance explicit:

```text
source = external_review
```

Stale `base_revision` reject. Unknown callout/source/target reject. Tercih all-or-nothing validation/apply.

GX gate:

- export round-trip
- stale import reject
- same validation as UI
- explicit provenance
- undo/reopen
- no base observation mutation
- manual UI still works

PASS → commit → G7.

---

# 13. G7 — confirmed callout → existing decisions compiler

Amaç:

```text
current transcription
+ current SemanticParse
+ current confirmed target
→ existing guided Decisions / constraints
```

Yeni CAD engine yok.

Örnek:

```text
Ø8 THRU + confirmed circle_3 + resolved mm
→ Hole(circle_id=circle_3, kind=through, diameter=8)
```

```text
4x Ø8 THRU + 4 confirmed circles
→ 4 through-hole decisions
```

```text
40 + confirmed vertex_pair + x axis + mm
→ existing Binding(value=40, axis=x, ...)
```

Unsupported semantics:

```text
READ success
BIND success
CAD unsupported
```

Conflict with existing manual decision → explicit conflict, no silent overwrite.

Provenance chain:

```text
existing decision
← compiler record
← confirmed target
← parse
← raw transcription
← callout
← source
```

PASS → commit → G8.

---

# 14. G8 — build readiness + audit

Backend `questions()` authority.

Categories:

```text
missing_transcription
parse_error
parse_ambiguous
missing_unit
missing_target
ambiguous_target
stale_target
unsupported_semantic
callout_conflict
missing_profile
missing_view
missing_calibration
geometry_conflict
unsupported_cad_feature
```

Build only when all relevant inputs current/resolved.

Audit feature başına:

```text
callout_id
raw text
parser version
semantic fields
target ids
geometry key/version
compiled decision
generated feature
```

Stale STEP current sunulmaz.

PASS → commit → G9.

---

# 15. G9 — Plate golden path

Tam yeni workflow:

```text
drawing
→ candidates
→ transcription
→ parse
→ proposal
→ confirmation
→ compile
→ build
→ STEP
→ evaluator
```

Expected Plate regression:

```text
bbox 120 × 80 × 15 mm
volume 124825.4 mm³
4 hole cylinders
1 pocket cylinder
STEP reopen
```

Fresh session ve gerçek UI/browser. Test code kullanıcı cevaplarını gizlice session’a enjekte etmez.

GX import ayrıca test edilir ama manual UI path en az bir kez gerçek yürür.

Fail ise generic fix + rerun; kullanıcı onayı bekleme.

PASS → G10.

---

# 16. G10 — fixed 10-sheet manifest

Sonuç görülmeden freeze:

```text
eval/guided_10_manifest.json
```

Fields:

```text
manifest_version
created_at_git_head
case_id
source_path
source_sha256
page/view
format
expected_scope_class
reference_available
reference_identifier_evaluator_only
```

Exactly 10.

Diversity mümkün olduğunca:

```text
vector PDF
raster
plate/profile
holes
pockets
radius/arc
count
THRU
depth
multiple callouts
layout variation
```

Her case run öncesi scope declare. Run sonrası scope retroaktif değiştirilmez.

Reference STEP producer’a kapalı.

PASS → commit manifest → G11.

---

# 17. G11 — first fixed 10-sheet run

Her case:

```text
fresh session
same HEAD
no code edit mid-case
```

Record:

```text
candidate_count
manual_region_count
ignored_count
transcription_count
parse_success/edit_count
proposal_count
proposal_accept_count
manual_target_correction_count
review_import_used
build blockers
build success
STEP reopen
bbox
feature count/dimensions
final geometry verdict
user interventions
```

Primary metric:

```text
GUIDED_CORRECT_STEP_RATE
```

Failure taxonomy:

```text
DETECT_MISS
DETECT_FALSE_POSITIVE
TRANSCRIPTION
PARSE_UNSUPPORTED
PARSE_AMBIGUOUS
BIND_NO_PROPOSAL
BIND_WRONG_PROPOSAL
BIND_STALE
CONSTRAINT_UNSUPPORTED
CONSTRAINT_CONFLICT
CAD_UNSUPPORTED
CAD_WRONG
STEP_EXPORT
STEP_REOPEN
EVALUATOR
```

Deliverables:

```text
eval/guided_10_report.json
eval/guided_10_report.md
```

G11 bitince otomatik G12.

---

# 18. G12 — generic-fix loop

G12 tek tur değildir:

```text
G12.1
G12.2
G12.3
...
```

Acceptance’a kadar devam eder.

Priority:

```text
1 data loss / wrong accepted result
2 shared CAD correctness blocker
3 shared constraint blocker
4 shared binding blocker
5 parser grammar gap
6 detector/manual-region UX
7 intervention optimization
```

Case-specific hardcode yasak:

```python
if filename == ...
if case_id == ...
if source_sha == known_case ...
if x ~= known_coordinate ...
```

Her cluster:

```text
reproduce
→ classify
→ failing regression
→ generic fix
→ focused green
→ historical regression
```

Fix batch sonrası fixed manifest yeniden koşulur.

Termination yalnız:

```text
A. 10/10 correct STEP → G13
B. HARD STOP → user report
```

Bunun dışında devam et.

---

# 19. G13 — final acceptance

Final clean run, fresh sessions, fixed manifest, final candidate commit.

Required:

```text
10/10 source opens
10/10 session persists
10/10 no silent guess
10/10 full callout audit chain
10/10 STEP for declared in-scope cases
10/10 STEP reopen
10/10 geometrically correct
```

Final full regression:

```text
python -m pytest -q
```

0 failures.

Real browser guided acceptance green.

GX acceptance:

```text
at least 2 manual-UI cases
at least 2 external-review-import-style cases
```

Both paths must converge to equivalent semantic/build decisions where appropriate.

Reference leakage audit mandatory.

PASS → CLOSEOUT.

---

# 20. CLOSEOUT

Update:

```text
docs/GUIDED_PROGRESS.md
report.md
README status
```

Historical plans preserved.

If 10/10 achieved, wording:

```text
fixed guided 10-sheet evaluation passes 10/10
```

Do NOT claim:

```text
arbitrary technical drawings fully automatic
```

Guided scope and known limitations remain explicit.

---

# 21. Test strategy

Every phase:

```text
unit
store/integration
HTTP
browser when UX changes
relevant historical regressions
```

Full pytest mandatory:

```text
H0
G13
```

Also after major cross-cutting G12 fixes.

Fake DOM-only browser testing is insufficient for G4/G6/G8 UX; current Chrome/CDP acceptance pattern reuse.

---

# 22. Evidence standard

Every task records:

```text
task id
HEAD/worktree
command
exit code
passed/failed/skipped
runtime
log path
result
next task
```

No fake success:

```text
skip != pass
blocked != pass
valid STEP != correct geometry
parser fixture != real parser
proposal != confirmation
selected suite != full pytest
local tests != external CI
```

---

# 23. User intervention metrics

Per sheet count:

```text
typed transcriptions
machine hints accepted
manual regions
ignored false positives
manual target corrections
feature confirmations
review import usage
```

These metrics guide later automation work.

---

# 24. Security / trust boundary for GX

External review JSON is untrusted input.

Validate:

```text
schema
revision
source digest
callout ID
target IDs
region bounds
allowed actions
```

Import never mutates raw record directly.

---

# 25. Product boundaries

Raster:

```text
SCALE 1:5 != px/mm calibration
```

Detection miss:

```text
manual region
```

Parser unknown:

```text
unsupported
```

Binding ambiguous:

```text
user target selection
```

CAD unsupported:

```text
explicit blocker
```

Evaluator-only reference remains isolated.

---

# 26. Self-review requirement

Every major phase after first implementation pass:

```text
bypass path?
stale/freshness bug?
legacy migration?
silent inference?
UI/server mismatch?
provenance gap?
```

If found, fix within phase without asking user.

---

# 27. Historical regressions that must remain green

```text
G1 target/reconfirm
G1R2 effective contour
G1R3 point tolerance
G2 candidate identity/reopen
G3 UI/session
G3R save-bypass/freshness/schema/diagnostics
```

---

# 28. Suggested commit sequence

```text
H0  baseline test-contract hygiene
G4  deterministic callout parser
G5  deterministic target proposal
G6  target confirmation UX
GX  review export/import
G7  confirmed-callout compiler
G8  readiness/audit
G9  Plate golden path
G10 fixed manifest
G11 first run evidence
G12.x generic fix batches
G13 acceptance
CLOSEOUT docs
```

---

# 29. “Bitti” tanımı

Hermes ancak hepsi sağlandığında master plan tamamlandı der:

- H0 full-suite baseline green
- G4 real parser accepted
- G5 real target proposals accepted
- G6 confirmation UX accepted
- GX review export/import accepted
- G7 compiler accepted
- G8 readiness/audit accepted
- G9 Plate geometrically correct
- G10 manifest frozen before results
- G11 first run fully recorded
- G12 all in-scope failures resolved generically
- G13 fixed manifest 10/10 geometrically correct
- final full pytest 0 failures
- final real browser acceptance green
- no reference leakage
- no example-specific hardcode
- final progress/report truthful

---

# 30. Eğer 10/10’a ulaşılamazsa

Hermes “yaklaşık tamam” deyip bırakmaz.

Ya G12 loop ile devam eder ya da yalnız HARD STOP gerekçesiyle `BLOCKED` raporu verir.

BLOCKED raporu:

```text
exact blocker
repro
three hypotheses tried if applicable
why architecture/scope decision is required
what remains working
what user must decide
```

---

# 31. Şimdiki tek başlangıç işi

Bu plan uygulandığı anda:

```text
H0.1
```

ile başla: `test_planner` pinini current `ChatSettings.as_dict()` contract’a getir; ardından H0 full baseline; sonra otomatik G4.

---

# 32. Handoff snapshot

```text
START HEAD
510bc3297851d23135c8ea382c7583dfc18ec848

DONE
G0/G1/G2/G3/G3R

CURRENT PRODUCT
Detected callout overlay + crop + user text + ignore/restore
+ manual region/edit + persistence/undo/reopen.

NOT DONE
Real parse
target proposal
proposal-based target confirmation
review export/import
callout→CAD compile
10-sheet acceptance

KNOWN BASELINE ISSUE
planner run-record key-set test stale against
repeat_penalty/repeat_last_n; fix H0 first.

AUTHORITY
Do not stop between phases for approval.
Continue through G13 unless HARD STOP.

FINAL TARGET
Fixed 10-sheet manifest:
10/10 geometrically correct STEP,
full pytest green,
real browser acceptance green,
no silent guess,
no reference leakage.
```

---

# 33. Final operating principle

```text
Önce doğru guided ürün.
Sonra otomasyon.
```

Hermes’in görevi yalnız kod yazmak değil; her aşamanın gerçekten çalıştığını kanıtlayarak bir sonraki aşamaya geçmektir.

Planın sonu:

```text
fixed 10-sheet guided workflow
→ 10/10 correct STEP
→ clean regression
→ honest closeout
```

olmadan görev bitmiş sayılmaz.
