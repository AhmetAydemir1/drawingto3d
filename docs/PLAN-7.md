# PLAN.md — drawingto3d / SEMREAD-001B

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `51ca151bf44ef8a1b2ca1eb7e1593426c56c9071`

---

# 1. Current verdict

The repository has moved materially forward.

The previous plan's main infrastructure work is now implemented:

```text
P0R-FINAL lifecycle finalization                  ✅
attempt ledger vs inference budget separation     ✅
actual prediction_input_identity                  ✅
prediction reuse based on prepared inputs         ✅
immutable evaluation_run artifacts                ✅

P1 predicate-wide recovery/regression              ✅
P1 ambiguous localization exclusion                ✅
P1 localization vs semantic metrics split          ✅
P1 exhaustiveness-aware extra candidates           ✅
P1 placeholder / region / observation validation   ✅
P1 raster vision validation                        ✅

P2 30-cell matrix dispositions                     ✅
P2 stricter B06 report gate                         ✅
P2 evidence-chain based B07                         ✅, but needs one semantic correction below

P4 deterministic D baseline                        ✅ 10/10, 0 VLM inference
```

The project is now primarily in **P3 — gold/reference completion**.

Current documented gold progress:

```text
2 / 10 complete
```

Completed gold includes `dev-drawing-2`; the raster development pages are currently being visually adjudicated. `dev-flange-elbow` callouts are mostly resolved; `R110` remains the explicit unresolved target question.

The V/VE inference budget is still:

```text
0 / 30
```

Keep it at zero until P3 + audit corrections + P5 freeze are complete.

---

# 2. Important correction before continuing

Do **not** follow the old instruction:

```text
10/10 gold
→ rerun D only to refresh evaluation_identity
```

if D's producer/input identity is unchanged.

That would contradict the architecture already implemented:

> evaluator/gold changes must not invalidate valid raw predictions.

The existing D raw candidates are reusable if:

```text
producer_identity unchanged
source/input unchanged
candidate schema unchanged
result artifact valid
```

A gold/evaluator change should create a **new evaluation run**, not require a new prediction attempt.

This matters even more for V/VE: after real calls exist, evaluator fixes must never force paid/restricted re-inference merely because an attempt recorded an older evaluation identity.

---

# 3. AUDIT-FIX-1 — B07 must not require attempt evaluation_identity == current evaluation_identity

## Current problem

The current evidence-chain code checks the selected attempt's recorded:

```text
evaluation_identity
```

against the current evaluator identity.

`acceptance_rows()` also requires:

```text
evaluation_stale_cells == []
```

for B07 to close.

This conflicts with the already-correct raw-prediction reuse rule:

```text
evaluator-only change
→ raw prediction remains valid
→ re-evaluate without new inference
```

## Required ownership

### Prediction attempt owns

```text
attempt_id
producer_identity
prediction_input_identity
model identity
runtime identity
request hash
raw/parsed response
result/gates
```

### Evaluation run owns

```text
evaluation_run_id
current evaluation_identity
selected attempt IDs
selected manifest/result hashes
gold/reference hashes
matching policy
metrics
acceptance result
```

The attempt's historical `evaluation_identity` may remain as provenance, but it must **not** determine prediction validity or B07 closure.

## Required change

In `evidence_chain_report()`:

Remove current-evaluator equality as a mandatory attempt check.

Instead validate:

```text
payload.evaluation_identity == current evaluation_identity
selected-attempts.json.evaluation_identity == current evaluation identity
evaluation_run_id binds current evaluator + selected attempts
```

Keep old attempt evaluation identity only as informational drift:

```text
attempt_evaluation_identity_at_creation
```

or equivalent.

## Required change

`evaluation_stale_cells` should not mean:

```text
raw prediction stale
```

Rename/reframe it as informational, for example:

```text
attempt_evaluation_identity_drift
```

It may be reported but must not require re-inference.

## B07 rule

B07 should close when:

```text
current evaluation run is valid
+
selected raw attempts have valid prediction evidence chains
```

not when every selected attempt happened to be created under the current evaluator version.

---

# 4. AUDIT-FIX-2 — B07 must validate prediction_input_identity, not only cached page PNG

## Current problem

`reusable_attempt()` correctly checks actual prepared-input identity.

But `evidence_chain_report()` still uses a page-PNG check as its input-chain proof.

That is weaker than the new prediction contract.

## Required V / VE evidence checks

For each selected V/VE attempt:

1. `prediction-input.json` exists.
2. Recompute:

```text
prediction_input_identity(prediction-input.json)
```

3. It equals:

```text
manifest.prediction_input_identity
result.prediction_input_identity
selected-attempts.json prediction_input_identity
history row prediction_input_identity
```

where those fields are expected to exist.

4. Selected attempt's producer/model/runtime/request hashes are valid.
5. Matrix selection points to that exact attempt.

The cached:

```text
page_png_sha256
```

may remain metadata, but it must not be the primary B07 proof for V/VE.

## D

For D:

```text
prediction_input_identity = not_applicable
```

because no model prompt/images are sent.

D input integrity remains based on source/producer/candidate artifacts.

---

# 5. AUDIT-FIX-3 — Evaluation artifact immutability needs one final check

The current versioned path is correct:

```text
evaluations/<evaluation_run_id>/
```

Before freeze, add/confirm tests that:

```text
same raw attempts + new evaluator
→ new evaluation_run_id
→ old evaluation directory preserved
→ no inference call
```

Also confirm `selected-attempts.json` records:

```text
attempt_id
manifest_sha256
result_sha256
prediction_input_identity
```

and the evaluation run uses those exact selected artifacts.

---

# 6. P3 — Complete gold/reference 10/10

This is now the main workstream.

Current documented state:

```text
2 / 10 gold complete
8 / 10 remaining
```

Remaining:

```text
dev-flange-book
dev-flange-elbow
6 frozen pages
```

---

# 7. P3 — Finish dev-flange-elbow carefully

Current visual reading has established:

```text
4-R20
4x2-Ø60
4x2-Ø30
Ø210
Ø290
R260
C10
R110
```

The latest review resolved:

```text
4x2-Ø60 / 4x2-Ø30
→ two flanges × 4 holes
→ count_printed = 8
```

Do not reinterpret this as "8 visible circles"; this is a **printed callout count**.

## R110

The handoff still lists one unresolved question:

```text
R110 target
```

Do not guess.

Use one of:

```text
A. visually resolve its leader/target and include it
B. if still ambiguous, exclude it from scorable claims and document it in scope/notes
C. mark underdetermined only if the drawing itself is genuinely insufficient
```

Do not infer the target from expected CAD/reference geometry.

---

# 8. P3 — Raster target-region policy

Keep the newly-added raster method:

```text
target_box_norm
```

for cases where Hough primitives are unreliable.

Requirements:

```text
normalized 0..1
x0 < x1
y0 < y1
visually measured
reason documented
vision_checked = true
```

If an observation ID is also stored, treat it as trace/provenance only when the actual target region came from visual measurement.

Do not force a noisy Hough primitive to become gold merely because the evaluator prefers an observation ID.

---

# 9. P3 — Raster gold evidence rule

For every raster scorable claim:

```text
vision_checked = true
```

and claim evidence must explicitly identify visual adjudication.

OCR can support the reading but cannot be the sole gold source.

If a symbol/value cannot be visually resolved:

```text
do not fabricate clean gold
```

Use:

```text
underdetermined
```

or exclude from exhaustive/scorable scope, depending on what is unresolved.

---

# 10. P3 — Feature claim vs representation claim

Keep the distinction already established in the evaluator:

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

For multi-view drawings:

```text
one physical feature
≠
one claim per visible representation
```

When the same feature appears in multiple views:

- choose the clearest target representation for the claim,
- mention other representations in evidence/notes,
- do not double-count one physical feature merely because it appears twice.

---

# 11. P3 — Gold scope/exhaustiveness

Every reference must contain a valid structured exhaustiveness declaration.

Use only the supported modes:

```text
full_page
regions
predicates
```

Be conservative.

If the annotator has only exhaustively labeled the semantic-reader feature families:

```text
diameter
radius
count
termination
depth
target binding
```

do not claim full-page exhaustiveness over unrelated dimensions/features.

This directly controls whether unmatched model candidates become:

```text
false_positive
```

or:

```text
unscorable_extra_candidate
```

---

# 12. P3 — Gold validation gate

Before declaring one page done, require:

```text
check_reference(...).ok == true
```

with:

```text
no placeholders
valid target region
valid callout region
valid truth state
valid exhaustiveness
observation IDs checked fail-closed when present
raster vision requirements satisfied
```

Never count a gold file merely because the JSON exists.

---

# 13. Do not rerun D after every gold edit

Gold changes evaluation identity.

That does **not** mean D raw candidates changed.

During P3:

```text
write gold
→ validate gold
→ do NOT rerun D just to update historical evaluation_identity
```

After all 10 gold files are done:

```text
evaluate existing valid D attempts under the new evaluation run
```

Only rerun a D page if:

```text
producer_identity changed
source/input changed
candidate schema changed
D attempt artifact invalid
```

This avoids wasting long deterministic OCR/Hough runs.

---

# 14. Re-evaluate D after 10/10 gold

D already has:

```text
10 / 10 raw attempts
0 VLM inference
```

After gold completion and B07 semantics fix:

```text
--evaluate
```

should re-score the existing D candidates under the current gold/evaluator.

Expected:

```text
new evaluation_run_id
same valid D prediction attempts
no inference
```

Record the final D baseline before V/VE.

---

# 15. P2/B07 acceptance state after the semantic fix

After AUDIT-FIX-1/2 and 10/10 gold:

Expected pre-VLM gate state should be approximately:

```text
B01 closed
B02 closed
B03 closed
B04 closed
B07 closed

B05 open — V/VE cells not run
B06 open — V/VE comparison not measured
```

That is the correct pre-P6 state.

Do not attempt to close B05/B06 before V/VE; they are measurement gates.

---

# 16. P5 — Freeze after gold and evaluator are final

Only after:

```text
10/10 gold valid
AUDIT-FIX-1 complete
AUDIT-FIX-2 complete
D baseline re-evaluated
pre-VLM B01/B02/B03/B04/B07 closed
```

freeze:

```text
corpus manifest
source bytes
gold hashes
candidate schema
prompt
run contract
prediction-input construction
V/VE evidence modes
MATCH_POLICY
semantic_evaluation.py
acceptance/evaluation semantics
model tag
model digest
runtime version
generation settings
```

Produce one freeze manifest.

After freeze:

```text
no prompt tuning
no gold fitting
no matching-policy tuning
no tolerance loosening
no selective case removal
```

---

# 17. P6 — V/VE run strategy

Only after P5 freeze.

Current model:

```text
qwen3-vl:8b-instruct
```

Keep first experiment limited to:

```text
D
V
VE
```

Do not add yet:

```text
4B
adaptive crops
fusion
verifier
CAD
STEP
LoRA
```

---

# 18. P6 — Development vs final call budget

Use the existing cap:

```text
development <= 10
final <= 20
total dispatched / possibly-dispatched <= 30
```

Before spending calls, perform:

```text
--matrix
--budget
--lifecycle
dry-run
```

and confirm:

```text
20 VLM cells intended
0 accidental stale/retry cells
0 orphan attempts
0 existing dispatched calls unless explicitly expected
```

---

# 19. Suggested V/VE execution order

Do not immediately spend all 20 final calls.

Recommended:

```text
1. small development V/VE batch
2. inspect transport/schema/identity artifacts only
3. do not tune against semantic correctness unless this is explicitly still development
4. once contract behavior is confirmed, freeze final execution
5. run the 20 final cells
```

Development calls still count toward the 30 total cap.

No hidden retries.

---

# 20. P7 — Final evaluation

Once final cells are complete, generate one new immutable evaluation run.

Required metrics already implemented:

```text
localization_match_rate
semantic_field_accuracy
target_binding_accuracy
candidate_overclaim_rate
candidate_abstention_rate
ambiguous_claim_count
false_positive_candidate_count
unscorable_extra_candidate_count
claim_recall
omission
```

Per-predicate D-vs-V and D-vs-VE:

```text
scorable_target_count
recovered_count
regressed_wrong_count
regressed_abstention_count
net_correct_gain
```

VE-vs-V:

```text
per-predicate better
per-predicate worse
net difference
```

Separate:

```text
development
frozen
```

in the report.

---

# 21. P7 — Failure examples are mandatory

The final report should link real examples for every observed failure family:

```text
ambiguous localization
wrong target binding
wrong R/Ø
wrong value
wrong unit
wrong count
wrong termination
wrong depth
physical overclaim
omission
extra candidate
transport failure
parse failure
```

Do not invent categories that did not occur.

Every example should identify:

```text
page_id
arm
attempt_id
candidate_id
gold claim
region
```

---

# 22. P8 — Decision

Allowed results:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

The VLM does not have to beat D for the experiment to be valid.

Primary decision evidence:

```text
predicate-level net_correct_gain
regression severity
overclaim
abstention
binding accuracy
runtime
memory
failure rate
```

Do not use only one aggregate score.

---

# 23. SEMREAD-001C only after the decision

If 001B shows useful semantic value, then 001C should test:

```text
extractor-missed feature discovery
ImageRegionRef without deterministic observation ID
real underdetermination
no forced answer
```

Do not start 001C before the 001B decision.

---

# 24. Product-evaluation debt remains separate

SEMREAD progress does not close:

```text
X01 STEP existence != product correctness
X02 simulated answers != source=user
X03 cylinder radius/diameter evaluator semantics
X04 legacy evaluation paths should use shared LabRunner integrity
```

Do not convert semantic benchmark progress into product-correctness claims.

---

# 25. Immediate next task

Do this next, in order:

```text
1. Fix B07 evaluation-identity ownership.
2. Make B07 validate prediction_input_identity artifacts directly.
3. Add regression tests for both fixes.
4. Finish dev-flange-elbow gold (resolve or explicitly scope out R110).
5. Finish dev-flange-book gold.
6. Write and validate the 6 frozen gold references.
7. Reach 10/10 valid gold.
8. Re-evaluate existing D raw attempts without rerunning them unless producer/input stale.
9. Confirm pre-VLM gates: B01/B02/B03/B04/B07 closed; B05/B06 open.
10. Freeze P5.
11. Only then request/perform V/VE calls.
```

---

# 26. Required new tests before P5

Add or confirm:

```text
evaluator-only change:
    raw attempt reusable
    B07 can still close under new evaluation run
    zero inference

attempt old evaluation_identity:
    informational only
    not a prediction-validity failure

prediction-input artifact:
    recomputed identity == manifest identity
    recomputed identity == result identity
    recomputed identity == selected-attempt identity

tampered prediction-input.json:
    B07 opens

tampered manifest/result prediction identity:
    B07 opens

new evaluator:
    new evaluation_run_id
    old evaluation directory preserved

gold change:
    existing D prediction remains reusable
    new evaluation can score it without rerun

target_box_norm:
    valid normalized visual box accepted
    invalid/reversed/out-of-range box rejected

raster reference:
    vision_checked false → reject
    missing visual claim evidence → reject
```

---

# 27. Current phase summary

```text
P0R-FINAL     essentially closed
P1            implemented
P2            implemented, with B07 identity-ownership correction required
P3            IN PROGRESS — 2/10 gold
P4            D raw baseline 10/10 complete, 0 inference
P5            not frozen
P6            not started — 0/30
P7            not measured
P8            no decision yet
```

---

# 28. Final principle

The project has moved past infrastructure construction.

The immediate risk is now **evaluation contamination**, not missing plumbing.

Before spending VLM calls:

> gold must be complete, evaluation identity must belong to the evaluation run rather than the prediction attempt, and B07 must prove the exact prepared model input instead of relying on a nearby page-PNG proxy.

Then freeze once and measure.
