# PLAN.md — drawingto3d / SEMREAD-001B

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `3d5bf73e6a448709049c3d91e2656bf85ab4cf9c`

---

# 1. Current verdict

The project has moved out of infrastructure repair and into gold/reference completion.

Current verified state from the repository and committed handoff:

```text
P0R-FINAL lifecycle / budget / prepared-input identity   ✅
P1 evaluator correctness                                 ✅
P2 B05/B06/B07 implementation                            ✅
PLAN-7 AUDIT-FIX-1/2                                     ✅
P4 deterministic D baseline                              ✅ 10/10, 0 VLM inference

P3 gold/reference                                        🚧 5/10
P5 freeze                                                 ❌
P6 V/VE                                                   ❌ 0/30
```

Latest HEAD reports:

```text
full pytest: 1155 passed
V/VE inference budget: 0 / 30
```

Current acceptance state documented after the latest evaluation:

```text
B01 closed
B02 open — gold 5/10
B03 closed
B04 closed
B05 open — 20 VLM cells to_run
B06 open — V/VE comparison not measured
B07 closed
```

This is now the correct pre-VLM shape.

Do not spend V/VE inference yet.

---

# 2. Important completed corrections — preserve them

Do not reopen these unless a concrete test fails.

## Evaluation identity ownership

The current implementation correctly treats:

```text
evaluation_identity
```

as evaluation-run ownership, not prediction validity.

An old attempt's evaluation identity is informational drift only.

Evaluator/gold changes can:

```text
reuse valid raw prediction
→ create a new evaluation_run_id
→ perform zero new inference
```

Keep this.

## B07 actual model-input evidence

For V/VE, B07 now validates:

```text
prediction-input.json
recomputed prediction_input_identity
manifest identity
result identity
history identity
selected-attempt identity
model/runtime/request evidence
```

Do not revert to page-PNG-only proof.

## D behavior

D is already:

```text
10/10
0 inference
valid_reuse
```

Gold changes alone do not require D reruns.

Only rerun D if its producer/input artifacts are genuinely stale.

---

# 3. New blocker before P5 — gold must be versioned outside `out/`

This is now the most important audit issue.

## Current problem

The handoff describes canonical gold/spec files under paths such as:

```text
out/lab/semread-001b/corpus/gold-specs/
out/lab/semread-001b/corpus/gold-src/
out/lab/semread-001b/corpus/gold/
```

But repository `.gitignore` contains:

```text
out/
```

Therefore the current 5/10 gold is local experiment state, not version-controlled source data.

A clean clone cannot reconstruct the exact benchmark truth merely from Git history.

Hashes written in documentation are useful evidence but are not a replacement for the actual truth files.

## Required architecture

Create a tracked canonical gold-source directory.

Recommended:

```text
eval/semread_001b_gold/
    manifest.json
    specs/
        dev-plate-pocket.json
        dev-drawing-2.json
        dev-flange-elbow.json
        ...
```

or:

```text
tests/fixtures/semread_001b/gold/
```

The exact path is less important than these properties:

```text
tracked by git
human/audit readable
no generated model predictions
no reference STEP-derived truth
stable IDs
explicit source page
explicit annotator/review state
```

## Generated artifacts

`out/lab/.../corpus/gold/` may remain generated runtime artifacts.

But they must be reproducibly generated from the tracked canonical spec.

Required relation:

```text
tracked gold spec
→ deterministic generator/validator
→ out/lab/.../gold/<page>.json
```

## Freeze rule

P5 must not freeze until:

```text
all 10 canonical gold specs are tracked
+
generated gold hashes match the tracked manifest
```

---

# 4. Add a gold manifest

Create a tracked:

```text
eval/semread_001b_gold/manifest.json
```

containing, per page:

```text
page_id
source path
source sha256
spec path
spec sha256
expected generated reference sha256
annotator
review_status
vision_checked when raster
exhaustiveness mode
claim count
```

Example:

```json
{
  "page_id": "dev-drawing-2",
  "source": "examples/pdf with steps/2/Drawing.pdf",
  "source_sha256": "...",
  "spec": "eval/semread_001b_gold/specs/dev-drawing-2.json",
  "spec_sha256": "...",
  "reference_sha256": "...",
  "annotator": "agent",
  "review_status": "provisional",
  "claim_count": 6
}
```

The freeze manifest should later bind this gold manifest hash.

---

# 5. P3 current progress

Current completed gold pages:

```text
dev-plate-pocket
dev-drawing-2
dev-flange-elbow
frozen-enclosure
frozen-exercise-12
```

Current total:

```text
5 / 10
```

Remaining:

```text
dev-flange-book
frozen-exercise-51
frozen-exercise-17
frozen-exercise-13
frozen-views-exercise
```

These five are raster pages and need visual adjudication.

---

# 6. P3 — frozen-exercise-17: do not solve scale circularly

This is the immediate active page.

Current observations documented:

```text
782 observations
593 line
166 arc
15 text
5 linear
3 circle
```

Vision read:

```text
Ø22.00
Ø20.00
Ø20.00
```

plus linear dimensions.

The current handoff leaves a px/mm question:

```text
inner circle 285 px
outer circle 390 px
```

and considers deriving scale from the Ø20 target.

## Important correction

Do **not** use:

```text
assume inner circle = Ø20
→ derive px/mm
→ use that scale to prove inner circle = Ø20
```

That is circular evidence.

The exact engineering value must come from the printed callout, not pixel inference.

## Preferred evidence order

For a raster claim:

```text
1. visually read printed callout
2. visually follow leader / extension relationship
3. identify target region
4. use independent geometry only as corroboration
```

Pixel/mm calibration is optional for the claim if the callout and target binding are visually clear.

## If scale is needed for corroboration

Calibrate using an **independent** dimension, e.g.:

```text
socket depth 10.00
or another linear dimension in the same view
```

Then check whether geometry is compatible.

Do not calibrate from the same diameter being labeled.

## If independent calibration is unavailable

Use:

```text
target_box_norm
vision evidence
printed callout
```

and explicitly state that pixel geometry was not used to establish the exact mm value.

That is safer than inventing scale certainty.

---

# 7. P3 — dev-flange-book

Next development raster page.

Existing evidence indicates OCR can partially read:

```text
6x Ø6.40 depth 15.00
20.00
60.00
90.00
...
```

But OCR is not gold.

Required process:

```text
visual page inspection
→ callout reading
→ leader/target binding
→ target_box_norm or trustworthy observation primitive
→ vision evidence
→ check_reference
```

Do not infer THRU/depth unless explicitly supported by the drawing.

---

# 8. P3 — remaining frozen raster pages

Remaining:

```text
frozen-exercise-51
frozen-exercise-17
frozen-exercise-13
frozen-views-exercise
```

For each page:

1. dump observation table;
2. visually inspect callouts;
3. identify the semantic-reader task scope;
4. define conservative exhaustiveness;
5. choose target observation only if primitive quality is credible;
6. otherwise use measured normalized target box;
7. write claim evidence;
8. require `vision_checked=true`;
9. run strict reference validation;
10. add canonical tracked spec.

Do not expand scope just to increase claim count.

---

# 9. Raster gold rule

For every scorable raster claim:

```text
vision_checked = true
```

Claim evidence must explicitly say what was visually confirmed.

OCR may support discovery but cannot be the sole truth source.

If a symbol, target, termination, or value remains unclear:

```text
do not guess
```

Use one of:

```text
underdetermined
exclude from scorable scope
document as unresolved note
```

---

# 10. target_box_norm policy

Keep `target_box_norm` for raster pages when deterministic primitives are unreliable.

Requirements:

```text
4 finite values
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
visually measured
reason documented
```

If an observation ID is also retained:

```text
observation_id = provenance/trace
```

when the target box itself came from visual measurement.

Do not force a noisy Hough primitive to become benchmark truth.

---

# 11. Avoid circular geometric validation in all gold

General rule:

A claim's printed value must not be used to calibrate geometry and then the calibrated geometry used as independent proof of that same value.

Invalid pattern:

```text
printed Ø20
→ assume this feature is Ø20
→ derive scale
→ geometry measures Ø20
→ claim "independently verified"
```

Valid corroboration:

```text
independent scale/datum
→ measure target geometry
→ compare with printed value
```

or:

```text
printed value + unambiguous leader binding
→ claim truth
→ geometry only optional corroboration
```

This matters especially for raster drawings.

---

# 12. Gold scope / exhaustiveness

Keep supported modes:

```text
full_page
regions
predicates
```

Use the narrowest honest declaration.

Do not mark a page `full_page` if annotation only covers:

```text
diameter
radius
count
termination
depth
binding
```

This controls whether unmatched candidates become:

```text
false_positive
```

or:

```text
unscorable_extra_candidate
```

---

# 13. Gold completion gate per page

A page counts toward 10/10 only if:

```text
tracked canonical spec exists
generated reference exists
check_reference.ok == true
source/spec/reference hashes recorded
no placeholder
valid regions
valid exhaustiveness
valid truth states
raster vision requirements satisfied
```

JSON existence alone is not completion.

---

# 14. Do not rerun D after every gold edit

The B07 ownership fix is now implemented.

Therefore:

```text
gold edit
→ evaluation_identity changes
→ raw D prediction stays valid
```

Do not rerun D merely to refresh evaluation identity.

After each gold batch:

```text
--evaluate
```

may create a new immutable evaluation run.

Rerun D only if:

```text
producer_identity stale
source input stale
candidate schema stale
artifact broken
```

---

# 15. P3 completion target

After all remaining pages:

```text
gold = 10/10
B02 = closed
D raw attempts = 10/10 valid reuse
B07 = closed
```

Expected gates before VLM:

```text
B01 closed
B02 closed
B03 closed
B04 closed
B05 open
B06 open
B07 closed
```

This is the intended P5 entry state.

---

# 16. P5 — Freeze only versioned truth

Before freeze, ensure all benchmark-defining inputs are committed/versioned:

```text
10 canonical gold specs
gold manifest
source drawing hashes
candidate schema
prompt
run contract
prediction-input construction
MATCH_POLICY
evaluator implementation
acceptance logic
model tag
model digest
runtime version
generation settings
```

Produce a freeze file such as:

```text
eval/semread_001b_gold/FREEZE.json
```

or:

```text
docs/SEMREAD_001B_FREEZE.json
```

containing hashes of all critical inputs.

The freeze must not depend on untracked files as the sole source of truth.

---

# 17. Freeze verification

Before P6 run:

```text
fresh/clean-clone reproducibility check
```

At minimum prove:

```text
tracked gold specs
→ regenerate references
→ same reference hashes
→ same evaluation_identity
```

This can be done without any VLM inference.

If a clean clone cannot reproduce the 10 references, P5 is not closed.

---

# 18. P6 — V/VE execution

Only after P5.

Model remains:

```text
qwen3-vl:8b-instruct
```

Experiment remains:

```text
D
V
VE
```

Do not add:

```text
4B
adaptive crops
fusion
verifier
CAD
STEP
LoRA
```

during 001B.

---

# 19. P6 — budget

Current:

```text
0 / 30
```

Keep:

```text
development <= 10
final <= 20
total dispatched or possibly-dispatched <= 30
```

Before first VLM call verify:

```text
--budget
--lifecycle
--matrix
dry-run
```

Expected:

```text
10 D valid_reuse
20 VLM to_run
0 orphan attempts
0 unexpected previous inference calls
```

---

# 20. P7 final evaluation

After all intended V/VE cells receive final dispositions, create a new immutable evaluation run.

Required output already supported by the evaluator:

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

For each predicate:

```text
scorable_target_count
recovered_count
regressed_wrong_count
regressed_abstention_count
net_correct_gain
```

Separate:

```text
development
frozen
```

---

# 21. Do not let ambiguity hide benchmark weakness

Current matcher correctly excludes ambiguous localization from semantic field scoring.

Final report must therefore always show:

```text
ambiguous_claim_count
```

next to semantic accuracy.

A model/evaluator with high semantic accuracy but very high ambiguity is not equivalent to high end-to-end reading quality.

---

# 22. P8 decision

Allowed outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Decision should primarily use:

```text
predicate-level net_correct_gain
regression severity
overclaim
abstention
binding accuracy
ambiguity
runtime
memory
failure rate
```

Do not reduce the decision to one aggregate score.

---

# 23. Separate product-evaluation debt

SEMREAD does not close:

```text
X01 STEP existence != correctness
X02 simulated answer != source=user
X03 radius/diameter evaluator semantics
X04 legacy eval paths need shared LabRunner integrity
```

Keep these separate from semantic-reader benchmark success.

---

# 24. Immediate next task

Do this next:

```text
1. Create a tracked canonical gold/spec directory.
2. Move/copy the existing 5 gold specs into it without changing their truth.
3. Add a tracked gold manifest with source/spec/reference hashes.
4. Update gold generation to consume the tracked spec source.
5. Finish frozen-exercise-17 without circular px/mm reasoning.
6. Finish dev-flange-book.
7. Finish frozen-exercise-51.
8. Finish frozen-exercise-13.
9. Finish frozen-views-exercise.
10. Reach 10/10 strict valid gold.
11. Run evaluation using existing valid D attempts.
12. Confirm B02 + B07 closed, B05/B06 open.
13. Perform clean-clone gold reproducibility check.
14. Freeze P5.
15. Only then run V/VE.
```

---

# 25. Required tests before P5

Add/confirm:

```text
tracked gold spec → generated reference deterministic
tracked manifest reference_sha256 matches generated file
missing tracked spec → freeze fails
untracked-only gold → freeze fails
source drawing hash mismatch → freeze fails
gold spec hash mismatch → freeze fails

raster target_box_norm validation
raster vision_checked enforcement
raster claim vision evidence enforcement

frozen-exercise-17:
    printed callout value does not establish px/mm scale by itself
    target box can be valid without metric pixel calibration
```

Also retain the already-passing B07 tests:

```text
evaluator-only change reuses prediction
prediction-input tampering opens chain
selected artifact hash mismatch opens chain
old evaluation run preserved
```

---

# 26. Current phase summary

```text
HEAD             3d5bf73e6a448709049c3d91e2656bf85ab4cf9c
tests            1155 passed (committed handoff)
P0R-FINAL        CLOSED
P1               CLOSED / implemented
P2               CLOSED at implementation level
B07              CLOSED
P3               IN PROGRESS — 5/10 gold
P4               D 10/10, 0 inference
P5               NOT FROZEN
P6               NOT STARTED — 0/30
```

---

# 27. Final principle

The immediate risk is no longer evaluator plumbing.

It is now **truth reproducibility**.

Before the first real V/VE benchmark call:

> the exact gold used to judge the model must be version-controlled, reproducible from a clean clone, visually justified for raster pages, and free of circular pixel-to-mm reasoning.

Then freeze once and measure.
