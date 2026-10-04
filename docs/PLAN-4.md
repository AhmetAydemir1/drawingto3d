# PLAN.md — drawingto3d Semantic Reader / Evaluation Integrity

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `0498391f3c3fad1654979f92ca96669aa3d3d899`

---

# 1. Goal

Before spending the SEMREAD-001B VLM inference budget, make the experiment auditable enough that:

1. we know exactly what the model saw,
2. every execution attempt is recorded,
3. stale predictions cannot enter a new result,
4. evaluator changes do not force unnecessary re-inference,
5. the deterministic baseline and VLM arms are compared on the same truth contract,
6. failures remain visible,
7. no model candidate is treated as engineering truth.

Target flow:

```text
drawing
  ↓
deterministic evidence
  ├──────────────┐
  │              ▼
  │          local VLM
  │              │
  ▼              ▼
D candidates    V / VE candidates
  └────────┬─────────┘
           ▼
      evaluation
           ↓
      later: verifier
           ↓
      later: user review
           ↓
      later: build eligibility
           ↓
      deterministic CAD
```

SEMREAD-001B remains a **candidate-reading benchmark**.

It does not prove:

```text
CAD correctness
STEP correctness
automatic build safety
wrong-supported rate
user effort reduction
```

Those remain `not_evaluated`.

---

# 2. Current repo state

The current HEAD already implements a substantial part of P0/P0R.

## Completed or substantially completed

```text
immutable attempt-NNNN directories
attempt history lists
producer vs evaluation identity separation
evaluator-only changes do not invalidate raw prediction
HTTP request hash separated from trace/manifest hash
canonical ModelInfo metadata for successful attempts
runtime version check
D stale detection
evaluation_run_id
list-based attempt-history reader for acceptance code
IMAGES_LAYOUT / IMAGE_LABEL_PREFIX moved to run contract
unsupported frozen settings block send
top_p / seed removed from frozen contract because transport does not send them
```

Committed handoff reports:

```text
V/VE budget: 0/30
P0R-FINAL: IN PROGRESS
tests: 139 passed, 0 failed
```

The `out/` runtime artifacts are gitignored, so the committed code and handoff were reviewed, but live local artifacts were not independently inspected through GitHub.

---

# 3. Current decision

Do **not** start V/VE inference.

Required order:

```text
P0R-FINAL
    ↓
P1 evaluator correctness
    ↓
P2 acceptance gates
    ↓
P3 gold/reference
    ↓
P4 deterministic baseline 10/10
    ↓
P5 freeze experiment
    ↓
P6 V/VE inference
    ↓
P7 evaluation
    ↓
P8 decision
```

---

# 4. P0R-FINAL — Full attempt lifecycle finalization

This is the highest-priority remaining P0R item.

## Current problem

Both:

```python
write_live_attempt()
write_d_attempt()
```

create the immutable attempt directory before all local operations are protected.

Examples still outside the common failure boundary:

```text
open_source()
observe()
installed_models()
find_model()
```

If one raises after:

```text
new_attempt_dir(...)
```

then an attempt directory can exist without a complete final record.

That violates the intended invariant:

> every attempt directory has exactly one attempt-history record.

## Required design

Introduce one common finalization path.

Suggested helper:

```python
finalize_attempt(
    attempt_id,
    directory,
    page,
    arm,
    phase,
    state,
    verdict,
    gates,
    result,
    error=None,
    runtime=None,
    model_metadata=None,
    stats=None,
)
```

The helper should, whenever possible:

```text
write result.json or local-error.json
write/update manifest.json
write artifact-index.json
append exactly one state.attempts history record
preserve send_state / budget state
```

Do not scatter final history writes across unrelated branches.

## Required states

At minimum:

```text
local_error_source
local_error_observe
local_error_preparation
blocked_budget
blocked_model_discovery
blocked_model_mismatch
blocked_runtime_mismatch
blocked_unsupported_setting
sending
transport_error
parse_error
failed_gates
pass
```

## Required invariant

For every:

```text
attempts/<case>/attempt-NNNN/
```

there must be exactly one corresponding history entry.

No orphan directory.

No duplicate history row for one `attempt_id`.

---

# 5. P0R-FINAL — Separate attempt ledger from inference budget

## Current problem

`write_live_attempt()` currently reserves inference budget **before** several local preflight checks:

```text
model discovery
model digest validation
runtime validation
unsupported frozen-setting validation
```

Because `budget_report()` counts reservations, a request that is definitely never sent can consume the limited 30-call experiment budget.

This is inconsistent with the experiment intent:

```text
30 real VLM call attempts
```

A local configuration error is not a VLM call.

## Required design

Use two ledgers/concepts:

### Attempt ledger

Every execution attempt is recorded.

This includes:

```text
local preparation failure
model missing
runtime mismatch
unsupported frozen setting
budget rejection
```

### Inference budget ledger

Consumes budget only when a network inference send is about to occur or send outcome is uncertain.

Recommended order:

```text
create attempt
→ source/observe/prepare
→ validate frozen settings
→ discover/validate model
→ validate runtime
→ build exact request inputs
→ reserve inference slot
→ immediately perform model send
```

If send definitely did not occur:

```text
inference_calls = 0
```

and it should not consume the 30-call inference budget.

If send status is uncertain because of a transport interruption after dispatch:

```text
count it
```

## Concurrency requirement

Reservation must still happen immediately before the network send under the existing shared lock so concurrent workers cannot oversubscribe the cap.

---

# 6. P0R-FINAL — `prediction_input_identity`

This is the second major remaining P0R item.

## Current problem

Current `input_identity(page)` hashes items such as:

```text
source bytes
cached corpus page PNG
preprocessing files
image_max_side
input_strategy
```

But live inference actually sends the output of:

```text
open_source(...)
prepare_arm_inputs(...)
candidate_prompt(...)
```

The cached corpus PNG is not sufficient proof of the exact bytes seen by the model.

## Required identity

After preparing the actual bundle, build a canonical object:

```json
{
  "schema": "semread-001b-prediction-input/1",
  "page_id": "...",
  "arm": "V",
  "prompt_sha256": "...",
  "images": [
    {
      "image_id": "image-1",
      "sha256": "...",
      "bytes": 12345,
      "order": 0
    }
  ],
  "observation_table_sha256": null,
  "preprocessing_identity": "...",
  "contract_version": "..."
}
```

For VE:

```json
{
  "arm": "VE",
  "images": [
    {"image_id": "image-1", "...": "..."},
    {"image_id": "image-2", "...": "..."}
  ],
  "observation_table_sha256": "..."
}
```

Hash the canonical representation as:

```text
prediction_input_identity
```

## Reuse rule

A V/VE attempt is reusable only if its stored:

```text
prediction_input_identity
```

matches the currently prepared input identity.

Do not rely on the cached `page_png_sha256` as the primary prediction-input identity.

## V / VE invariant

The experiment must explicitly prove:

```text
V.image-1.sha256 == VE.image-1.sha256
```

for the same page.

Their complete prediction input identities will differ because VE additionally receives:

```text
overlay
observation table
```

That is expected.

---

# 7. P0R-FINAL — Fix stale settings metadata

## Current problem

`semantic_run_contract.py` correctly removed:

```text
top_p
seed
```

from the frozen contract.

However `semantic_candidate_reader.py` still contains:

```python
SHARED_SETTINGS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 20261004,
}
```

This no longer describes the experiment contract.

Even if currently unused, it is misleading and can be consumed later accidentally.

## Required fix

Prefer removing `SHARED_SETTINGS`.

If a compatibility export is required, derive it from:

```text
semantic_run_contract.SETTINGS
```

Never maintain a second settings definition.

## Rule

There must be exactly one source of truth for prediction-affecting settings.

---

# 8. P0R-FINAL — Clarify `input_strategy`

## Current issue

Shared contract currently contains:

```text
input_strategy = "single_full_page"
```

But VE actually sends:

```text
raw full page
+ overlay image
+ observation table
```

The value can be interpreted as the raw-page strategy, but as written it can misdescribe the full model input.

## Required fix

Prefer explicit fields:

```text
raw_page_strategy = "single_full_page"
```

and per-attempt:

```text
arm_input_variant = "V"
arm_input_variant = "VE"
```

or:

```text
evidence_mode = "none"
evidence_mode = "deterministic_overlay_and_table"
```

Do not encode arm-specific evidence behavior in an ambiguous shared setting.

---

# 9. P0R-FINAL — Canonical model/runtime metadata

The latest commit substantially fixes this.

Keep:

```text
installed_models()
→ find_model()
→ ModelInfo.as_dict()
```

as the single parser for model metadata.

`runtime_identity()` should remain responsible for:

```text
endpoint
runtime version
runtime error
canonical model metadata reference
```

Do not add a second manual `/api/tags` parser again.

---

# 10. P0R-FINAL — Evaluation artifacts should be immutable too

Current:

```text
evaluation_run_id
evaluation_stale_cells
```

is useful.

Strengthen this by writing evaluation output under:

```text
out/lab/semread-001b/evaluations/<evaluation_run_id>/
```

containing:

```text
evaluation.json
acceptance.json
report.md
selected-attempts.json
```

A convenience pointer/copy may remain under:

```text
final/
```

but old evaluations should not be silently overwritten when:

```text
gold changes
evaluator changes
matching policy changes
```

Prediction immutability and evaluation immutability should follow the same audit principle.

---

# 11. P0R-FINAL completion gate

P0R-FINAL closes only when all are true:

1. `open_source()` failure is finalized.
2. `observe()` failure is finalized.
3. preparation failure is finalized.
4. model discovery failure is finalized.
5. model digest mismatch is finalized.
6. runtime mismatch is finalized.
7. unsupported setting is finalized.
8. transport/parse/gate failures are finalized.
9. every attempt directory has exactly one history row.
10. local/preflight failures do not consume VLM inference budget.
11. actual prepared images are part of prediction input identity.
12. prompt hash is part of prediction input identity.
13. VE observation-table hash is part of prediction input identity.
14. V/VE raw-page hash equality is tested.
15. stale prediction reuse uses `prediction_input_identity`.
16. `SHARED_SETTINGS` drift is removed.
17. input strategy/evidence mode is unambiguous.
18. evaluator-only change keeps raw prediction reusable.
19. evaluation run gets its own identity/artifact.
20. no V/VE inference was required to implement these fixes.

Until then:

```text
P0R-FINAL = IN PROGRESS
```

---

# 12. P1 — Evaluator correctness

P1 code remains largely unchanged at the current HEAD.

Do not run final V/VE before this is fixed.

---

## P1-1 Predicate-wide recovery/regression

## Current problem

`compare_arms()` still compares mainly:

```text
size
```

This does not measure the intended semantic task.

## Required predicates

At minimum:

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

For each predicate:

```text
scorable_target_count
recovered_count
regressed_wrong_count
regressed_abstention_count
net_correct_gain
```

Definition:

```text
net_correct_gain =
    recovered_count
    - regressed_wrong_count
    - regressed_abstention_count
```

Also report overall totals, but never hide predicate behavior behind one aggregate.

---

# 13. P1 — Ambiguous matching

## Current problem

`match_claims()` detects nearby competing candidates but still selects one candidate and puts it into normal scoring.

That can make semantic accuracy depend on candidate order/ID.

## Required frozen policy

Recommended:

```text
ambiguous localization
→ matching_status = ambiguous
→ do not semantic-score an arbitrary candidate
→ count separately
```

Do not silently choose a candidate and score its semantics as if localization were unique.

---

# 14. P1 — Separate localization from semantic quality

Current metric:

```text
candidate_precision = matched / candidates
```

primarily measures localization matching.

Rename/split into:

```text
localization_match_rate
semantic_field_accuracy
candidate_overclaim_rate
candidate_abstention_rate
```

A region match does not mean the semantic interpretation is correct.

---

# 15. P1 — Exhaustiveness-aware false positives

## Current problem

References carry an `exhaustiveness` concept, but `semantic_evaluation.py` does not use it.

## Required behavior

Reference explicitly defines what is exhaustively annotated:

```text
full page
specific regions
specific predicates
```

An unmatched candidate outside scorable exhaustive scope is:

```text
unscorable_extra_candidate
```

not automatically:

```text
false_positive
```

Report both separately.

---

# 16. P1 — Strict gold validation

Current `check_reference()` still accepts non-empty placeholder strings.

Reference builder can still emit:

```text
EKSİK: gerekçe yazılmadı
EKSİK
EKSİK: kapsam yazılmadı
EKSİK: hangi bölgeler tarandı
```

These must fail validation.

Reject explicit placeholder markers:

```text
EKSİK
TODO
TBD
PLACEHOLDER
```

B02 cannot close while any remain.

---

# 17. P1 — Region validation

Current `check_reference()` verifies that a target region exists, but not that the normalized region is geometrically valid.

Require:

```text
finite coordinates
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

Reject:

```text
NaN
inf
negative
> 1
zero-area box
reversed box
malformed length/type
```

Validate both:

```text
target region
callout region
```

---

# 18. P1 — Observation-ID validation must fail closed

Current behavior:

```python
if observation_id is not None and observation_ids and observation_id not in observation_ids:
```

If observation extraction fails and `observation_ids=[]`, ID validation is skipped.

Required:

```text
gold has observation_id
+
observation extraction unavailable
→ reference validation blocked/error
```

Do not silently treat it as valid.

---

# 19. P1 — Raster gold rule

Reference builder currently adds a `review_flag` when raster source evidence does not mention vision.

The strict validator must enforce it.

For raster scorable claims:

```text
vision_checked = true
```

and/or explicit visually adjudicated source evidence is required.

OCR alone is not gold.

Unreadable evidence becomes:

```text
underdetermined
```

or unscorable.

---

# 20. P1 — Circle is not automatically a hole

Keep separate:

```text
circle representation
physical hole interpretation
callout binding
termination
```

Never treat:

```text
model says hole
+
deterministic extractor sees circle
```

as two independent proofs of a physical hole.

---

# 21. P2 — Acceptance gates

Current B05/B06/B07 remain too weak.

---

## B05 — Require complete 30-cell matrix

Target:

```text
10 pages × D/V/VE = 30 cells
```

Each must end in exactly one final disposition:

```text
valid_result
valid_reuse
failed_attempt
blocked
```

`not_run` means incomplete.

Do not only count frozen V/VE history rows.

Development pages are part of the final matrix too.

---

## B06 — Require complete report contract

Close only if final report contains:

```text
dev/frozen separation
predicate-level metrics
D/V/VE comparison
predicate-wide recovery/regression
net gain
failure examples
runtime/cost
reference-quality note
parse failure count
transport failure count
ambiguity count
unscorable-extra count
```

A non-empty `vs_d` dictionary is not sufficient.

---

## B07 — Validate evidence chain

Close only when selected final cells pass:

```text
attempt-history consistency
artifact existence
artifact hash validation
producer identity
prediction_input_identity
model identity
runtime identity
HTTP request hash
budget ledger
matrix selection
evaluation identity
```

A clean budget object alone is not evidence integrity.

---

# 22. P3 — Gold/reference completion

Before final V/VE:

```text
10 / 10 references
```

must pass strict validation.

Each scorable claim should contain:

```text
claim_id
target region
callout region when applicable
representation
physical interpretation
form
size + unit
count
termination
depth
truth state
evidence
source_evidence
exhaustiveness scope
```

Truth states:

```text
determinate_present
determinate_absent
underdetermined
```

Reference STEP must never define what the drawing itself says.

---

# 23. P4 — Deterministic baseline 10/10

After producer/input identities are stable, rerun D for all ten pages.

D must use:

```text
0 VLM inference
```

Do not add case-specific heuristics to improve the benchmark.

Unsupported predicates remain:

```text
unknown
not_produced
abstained
```

Record separately:

```text
observe time
adapter time
total deterministic reader time
```

The current adapter-only timing note is not enough for an end-to-end latency comparison.

---

# 24. P5 — Freeze experiment

Before final V/VE, freeze and hash:

```text
corpus manifest
source drawing bytes
actual prepared raw-page identity
gold/reference version
candidate schema
prompt
run contract
V/VE evidence modes
matching policy
evaluator implementation
aggregation implementation
image_max_side
num_ctx
num_predict
temperature
keep_alive
model tag
model digest
runtime version
```

Do not list settings the runtime does not actually send.

After final predictions are visible:

- no prompt tuning,
- no gold edits to fit predictions,
- no tolerance loosening,
- no hard-case removal,
- no selective rerun because output is bad.

A real bug creates a new version and preserves old evidence.

---

# 25. P6 — V / VE experiment

Only after P0R-FINAL through P5 are closed.

First model remains:

```text
qwen3-vl:8b-instruct
```

No:

```text
4B comparison
adaptive crop
fusion
verifier
CAD
STEP
LoRA
```

yet.

## V

```text
raw full page
```

## VE

```text
same raw full-page bytes
+
neutral overlay
+
addressable observation table
```

Shared:

```text
model
digest
runtime
candidate schema
task prompt family
generation settings
raw image-1 bytes
```

Intentional difference:

```text
deterministic observation evidence
```

---

# 26. P6 — Inference budget

Keep:

```text
development <= 10
final <= 20
total real inference attempts <= 30
```

Count:

```text
sent success
sent timeout
sent HTTP error
sent parse failure
send-status uncertain
```

Do not count:

```text
local source failure
local observe failure
local preparation failure
known model mismatch
known runtime mismatch
unsupported local setting
budget rejection
```

Those belong in the attempt ledger but are not model inference calls.

No hidden retries.

---

# 27. P7 — Final metrics

For D/V/VE:

```text
localization_match_rate
claim_recall
omission
representation_accuracy
physical_accuracy
R_vs_diameter_accuracy
numeric_value_accuracy
unit_accuracy
count_accuracy
termination_accuracy
depth_accuracy
target_binding_accuracy
overclaim_rate
abstention_rate
ambiguous_localization_count
unscorable_extra_candidate_count
transport_failure_count
parse_failure_count
```

For V vs D and VE vs D, per predicate:

```text
recovered
regressed_wrong
regressed_abstention
net_correct_gain
```

For VE vs V:

```text
VE_better
VE_worse
net_difference
```

Separate:

```text
development
frozen
```

Report both:

```text
page/group count
claim count
```

Do not make broad reliability claims from this provisional ten-page corpus.

---

# 28. P7 — Failure analysis

Inspect real observed examples of:

```text
wrong localization
ambiguous localization
wrong R/Ø
wrong numeric value
wrong unit
wrong count
wrong termination
wrong depth
wrong target binding
physical overclaim
feature omission
schema failure
truncation
transport failure
```

Each example must link to:

```text
page_id
attempt_id
candidate_id
gold claim
source region
arm
```

---

# 29. P8 — Decision

SEMREAD-001B does not require the VLM to outperform D.

Allowed outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Decision based on measured:

```text
net semantic gain
regression
failure severity
runtime
memory
coverage
abstention
```

No automatic transition to 001C or CAD integration.

---

# 30. Separate product-evaluation debt — X01–X04

SEMREAD does not replace these product-evaluation fixes.

They remain separate blockers before product correctness claims.

## X01 — Acceptance semantics

STEP creation must not automatically imply:

```text
accepted=true
```

## X02 — User provenance

Programmatically generated answers must not be marked:

```text
source=user
```

Use explicit simulated provenance.

## X03 — Radius/diameter evaluation

Cylinder metrics must respect the actual `cadrun` radius semantics.

Do not compare radius as diameter.

## X04 — Shared runner

Legacy offline/end-to-end evaluation paths should use existing lab-runner protections instead of parallel subprocess orchestration.

Do not build a second runner.

---

# 31. Documentation cleanup

The current handoff contains both newer:

```text
139 passed
```

and an older trailing:

```text
71 passed
```

test-status section.

Clean stale duplicated status blocks so handoff documents describe one current state.

Also remove/update stale:

```text
SHARED_SETTINGS
```

from `semantic_candidate_reader.py`.

Documentation should never imply a setting is used when it is not in the actual request.

---

# 32. Zero-inference test gate before P1

Add/retain tests for:

```text
open_source failure → exactly one history record
observe failure → exactly one history record
prepare failure → exactly one history record
model discovery failure → exactly one history record
model digest mismatch → exactly one history record
runtime mismatch → exactly one history record
unsupported setting → exactly one history record
no orphan attempt directory
no duplicate history record
pre-send failures consume zero inference budget
reservation immediately precedes send
actual prompt hash changes prediction_input_identity
actual raw image bytes change prediction_input_identity
overlay bytes change VE prediction_input_identity
observation-table change changes VE prediction_input_identity
V and VE image-1 hashes identical
stale prediction identity rejected
evaluator-only change keeps raw prediction reusable
evaluation-run ID changes with evaluator identity
SHARED_SETTINGS removed/derived
arm evidence mode represented explicitly
```

Then run existing 001A compatibility tests.

No V/VE inference is needed for these.

---

# 33. P0R-FINAL exit criteria

Mark:

```text
P0R-FINAL = CLOSED
```

only when:

```text
attempt lifecycle is total
attempt ledger and inference budget are distinct
prediction identity represents actual model inputs
no duplicate settings contract exists
V/VE raw-page equality is mechanically checked
stale prediction reuse is based on actual prepared inputs
evaluation artifacts are versioned/identifiable
```

Then immediately move to P1.

Do not spend final inference between P0R and P1.

---

# 34. Immediate next implementation task

Do only the following next:

```text
1. implement finalize_attempt / total lifecycle handling
2. move all local preflight before inference-budget reservation
3. implement prediction_input_identity from actual prepared bundle
4. use prediction_input_identity in reusable_attempt()
5. remove stale SHARED_SETTINGS
6. clarify arm input/evidence mode
7. add focused zero-inference tests
8. optionally make evaluation artifacts immutable by evaluation_run_id
```

After these are green:

```text
P0R-FINAL = CLOSED
```

Then begin:

```text
P1 evaluator correctness
```

---

# 35. Final principle

The benchmark is trustworthy only if:

> the recorded experiment contract is the experiment that actually ran.

The next goal is not to make Qwen perform better.

The next goal is to remove the last ways in which:

```text
an execution can disappear,
a non-call can consume the model-call budget,
a stale input can be reused,
or metadata can describe something different from what the model actually saw.
```

Only after that should semantic accuracy be measured.
