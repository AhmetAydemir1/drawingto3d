# PLAN.md — drawingto3d Semantic Reader / Evaluation Integrity

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `3e65ef6577c117135515e363b75c72263b34860e`

---

# 1. Objective

Build a trustworthy semantic-reading evaluation path before spending final VLM inference budget or connecting semantic output to CAD.

The target architecture remains:

```text
drawing
  ↓
deterministic evidence extraction
  ├──────────────┐
  │              ▼
  │        local VLM reader
  │              │
  ▼              ▼
deterministic   semantic candidates
candidates         │
  └───────┬────────┘
          ▼
      verifier
          ▼
    user decision
    when necessary
          ▼
    build eligibility
          ▼
 verified feature plan
          ▼
 deterministic CAD
```

Core rules:

- The extractor must not limit what the model can notice.
- Model output is a candidate, never engineering truth by itself.
- STEP creation is not proof of correctness.
- Missing/ambiguous information stays unresolved and may require the user.
- Reference STEP is evaluator-only.
- Regression/test drawings are not training data.
- No example-specific heuristics.
- No threshold loosening to make results pass.
- No `git reset`, `git clean`, bulk revert, or unrelated overwrite.

---

# 2. Current state

## 2.1 SEMREAD-001A

Implemented:

- multi-image Ollama transport,
- image identity,
- final-byte image hashing,
- structured response format,
- image-region references,
- raw/parsed response recording,
- truncation/transport gates,
- offline/local-only runtime path.

Committed handoff reports 001A complete.

Live `out/` artifacts are gitignored and were not independently inspected through GitHub.

---

## 2.2 SEMREAD-001B

Current repo contains:

```text
src/drawingto3d/semantic_candidates.py
src/drawingto3d/semantic_candidate_reader.py
src/drawingto3d/semantic_deterministic.py
src/drawingto3d/semantic_evaluation.py
src/drawingto3d/semantic_run_contract.py

eval/semread_001b_pilot.py
eval/semread_001b_reference.py
eval/semread_001b_snapshot.py
eval/semread_001b_corpus_probe.py

tests/test_semread_001b.py
tests/test_semread_001b_gates.py
tests/test_semantic_candidates.py
```

Current committed state reports:

```text
V/VE inference budget: 0 / 30
D development baseline: existing but stale after producer identity changes
test suite: 133 passing
```

The last commit fixed most of P0R:

```text
evaluator changes no longer invalidate raw predictions
producer/evaluator identities separated
HTTP request hash separated from manifest hash
canonical model metadata used for successful calls
attempt-NNNN directories
D stale detection
evaluation_run_id
```

However P0R is **not closed yet**.

---

# 3. Immediate decision

Do not start V/VE inference.

Required order:

```text
P0R-FINAL — close remaining artifact/runtime/input integrity gaps
P1        — evaluator correctness
P2        — acceptance gates
P3        — gold/reference integrity
P4        — deterministic baseline 10/10
P5        — freeze experiment
P6        — run V/VE
P7        — evaluate
P8        — decision
```

---

# 4. P0R-FINAL — Frozen settings must equal actual request settings

## Problem

`semantic_run_contract.py` freezes:

```text
top_p = 1.0
seed = 20261004
```

But current:

```text
ChatSettings
_ollama_chat()
```

do not support or forward `top_p` or `seed`.

`write_live_attempt()` detects unsupported settings but only records:

```text
settings_unsupported
```

and still sends the inference request.

This breaks the experiment contract.

The manifest may claim one setting contract while the actual request uses another.

## Required fix

Preferred:

Extend `ChatSettings`, `_ollama_chat()`, and `_chat_request()` so frozen settings are actually sent:

```text
top_p
seed
```

to Ollama `options`.

Then ensure trace/request manifest records them.

Alternative:

Remove unsupported settings from the frozen contract before any final inference.

### Hard rule

If a frozen prediction-affecting setting is unsupported:

```text
send_attempted = false
blocking_kind = unsupported_frozen_setting
```

Do not silently drop it.

## Tests

Require:

```text
frozen top_p appears in serialized HTTP body
frozen seed appears in serialized HTTP body
trace options equal contract settings
unsupported frozen setting blocks send
```

---

# 5. P0R-FINAL — Complete attempt history for every execution path

## Problem

`new_attempt_dir()` can run before:

```text
open_source()
observe()
installed_models()
find_model()
```

Some of these operations happen outside the main protected exception path.

If they raise:

```text
attempt-NNNN directory may exist
but state.attempts may not get a record
```

The contract requires:

> every created attempt directory has exactly one attempt-history record.

## Required change

Wrap the complete worker lifecycle after attempt creation.

Recommended structure:

```python
directory = new_attempt_dir(...)
attempt_id = ...

try:
    source = ...
    observations = ...
    inputs = ...
    reservation = ...
    model = ...
    runtime = ...
    inference = ...
except KnownBlocked as exc:
    finalize_attempt(...)
except Exception as exc:
    finalize_attempt(state="local_error", ...)
    raise_or_return(...)
```

Use one common finalization helper.

Suggested helper:

```text
finalize_attempt(...)
```

must write:

```text
result.json or local-error.json
manifest.json when possible
artifact-index.json when possible
state.attempts history entry
```

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
sent
transport_error
parse_error
pass
fail
```

## Invariant

For every directory:

```text
attempts/<case>/attempt-NNNN/
```

exactly one matching attempt history entry exists.

No orphan directories.

---

# 6. P0R-FINAL — Input identity must bind the actual bytes sent to the model

## Problem

Current `input_identity(page)` hashes:

```text
source file
cached corpus page PNG
preprocessing code
image_max_side
input_strategy
```

But live inference creates its actual image bundle from:

```text
open_source(ROOT / page["path"])
prepare_arm_inputs(...)
```

The cached corpus PNG is not guaranteed to be byte-identical to the PNG actually sent to the model.

The experiment identity must describe the true inference input.

## Required design

After `prepare_arm_inputs()` compute:

```text
prompt_sha256
image_id
image_sha256
image_bytes
image_order
image_role
observation-table hash
```

Then derive:

```text
prediction_input_identity
```

from the actual prepared payload inputs.

Example:

```json
{
  "page_id": "...",
  "arm": "VE",
  "prompt_sha256": "...",
  "images": [
    {
      "image_id": "image-1",
      "sha256": "...",
      "bytes": 123456
    },
    {
      "image_id": "image-2",
      "sha256": "...",
      "bytes": 234567
    }
  ],
  "observation_table_sha256": "...",
  "preprocessing_identity": "..."
}
```

Hash this canonical object.

Store:

```text
prediction_input_identity
```

in attempt manifest.

## Reuse contract

A V/VE attempt is reusable only when current prepared input identity equals the attempt identity.

Do not rely only on the cached page PNG hash.

## Important

V vs VE intentionally have different input identities.

That is expected.

They must still share the same raw `image-1` byte hash.

---

# 7. P0R-FINAL — Remove run-contract drift from reader literals

## Problem

`semantic_run_contract.py` is intended to be the single source of truth.

But `semantic_candidate_reader.read_page()` still hard-codes:

```text
images_layout = "per_image_message_labeled"
image_label_prefix = "Image ID: "
```

If the contract changes, producer identity changes, but runtime behavior may remain on old literals.

## Required fix

Move all prediction-affecting reader values into the contract:

```text
images_layout
image_label_prefix
input_strategy
```

Pass them explicitly into `read_page()` or import them from one contract object.

No duplicate literals.

## Test

Changing the contract must change:

```text
producer_identity
actual request layout
actual request label prefix
```

together.

---

# 8. P0R-FINAL — Canonical runtime/model metadata path

## Problem

Successful attempt manifest now correctly uses:

```python
installed.as_dict()
```

However `runtime_identity()` still manually parses `/api/tags` and may record incomplete nested model metadata.

This creates two competing model metadata paths.

## Required fix

Use:

```python
installed_models()
find_model()
ModelInfo.as_dict()
```

as the only model metadata parser.

`runtime_identity()` should primarily provide:

```text
runtime endpoint
runtime version
runtime error
```

and reference canonical model metadata from the existing parser.

Avoid duplicate `/api/tags` parsing logic.

---

# 9. P0R-FINAL — Fix acceptance code for list-based attempt history

## Problem

`state["attempts"][case]` is now a list.

But `acceptance_rows()` still contains logic equivalent to:

```python
for row in state["attempts"].values():
    row.get(...)
```

The value is now usually a list, not an attempt record.

This can break `--evaluate` / acceptance generation.

## Required fix

Add one canonical flattening helper:

```python
def all_attempt_records(state) -> list[dict]:
    ...
```

Support backward compatibility:

```text
old dict record
new list of records
```

Then all acceptance/report code must consume the flattened records.

No direct assumptions about state storage shape outside the helper.

## Test

Acceptance generation must work with:

```text
old single-record state
new list-record state
mixed migrated state
empty state
```

---

# 10. P0R-FINAL — D baseline stale validation

The stale D logic exists and should remain.

But the final P0R test gate must verify:

```text
D producer change → D stale
source change → D stale
page/preprocessing change → D stale where relevant
candidate schema change → D stale
valid D → reuse
```

D reruns cost zero VLM inference.

Prefer rerun over questionable reuse.

---

# 11. P0R-FINAL — Evaluation identity and stale evaluation behavior

Raw prediction reuse should ignore evaluator-only changes.

But the system should explicitly mark:

```text
old evaluation = stale
raw prediction = valid
```

Current `evaluation_stale_cells` is a good start.

Final contract:

```text
prediction validity
≠
evaluation validity
```

A new evaluator version must be able to:

```text
reuse raw prediction
produce new evaluation_run_id
preserve old evaluation artifact
```

Do not overwrite old evaluation results if practical.

Preferred:

```text
out/lab/semread-001b/evaluations/<evaluation-run-id>/
```

containing:

```text
evaluation.json
report.md
acceptance.json
selected-attempts.json
```

A top-level pointer may reference the latest evaluation.

---

# 12. P0R-FINAL completion gate

P0R is closed only when all are true:

1. Frozen settings equal actual serialized request settings.
2. Unsupported frozen setting blocks send.
3. No attempt directory can exist without a history record.
4. Model discovery/source/observe exceptions are recorded.
5. Prediction input identity uses actual prepared images/prompt.
6. V and VE raw page bytes are proven identical.
7. Reader layout/prefix comes from the run contract.
8. Canonical model parser is the only model metadata path.
9. List-based attempt history works in acceptance/report code.
10. V/VE stale reuse checks actual prediction input identity.
11. D stale reuse checks deterministic producer/input identity.
12. Evaluator-only changes preserve raw predictions.
13. New evaluator run receives a new evaluation_run_id.
14. No real V/VE inference was spent to close P0R.

Until then:

```text
P0R = IN PROGRESS
```

---

# 13. P1 — Evaluator correctness

Only after P0R closes.

---

## P1-1 Predicate-wide recovery/regression

Current recovery/regression is still too size-centric.

Required predicates:

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
    recovered
    - regressed_wrong
    - regressed_abstention
```

Do not compare recovery and regression rates with different denominators as if they were directly comparable.

---

## P1-2 Ambiguous matching

Current evaluator can still select one candidate when matching is ambiguous.

Required policy before final inference:

```text
ambiguous localization
→ matching_status=ambiguous
→ do not semantic-score an arbitrary candidate
→ count ambiguity separately
```

Candidate ordering/ID must not affect semantic accuracy.

---

## P1-3 Separate localization from semantics

Replace generic interpretation of:

```text
candidate_precision
```

with explicit metrics:

```text
localization_match_rate
semantic_field_accuracy
candidate_overclaim_rate
candidate_abstention_rate
```

A candidate can localize correctly and still be semantically wrong.

---

## P1-4 Use annotation exhaustiveness

Reference `exhaustiveness` must decide whether an unmatched prediction is:

```text
false_positive
```

or:

```text
unscorable_extra_candidate
```

Unannotated scope cannot automatically count as error.

---

## P1-5 Reject gold placeholders

Reject:

```text
EKSİK:
TODO
TBD
placeholder
```

even if non-empty.

B02 cannot close with placeholder gold.

---

## P1-6 Validate normalized regions

Require:

```text
finite
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

Reject:

```text
NaN
inf
negative
>1
zero area
reversed region
```

---

## P1-7 Observation-ID checking must fail closed

If gold contains an observation ID and observation extraction fails:

```text
reference validation = blocked/error
```

Do not skip ID validation by passing an empty list.

---

## P1-8 Circle is not automatically a physical hole

Keep separate:

```text
circle_representation_present
physical_hole_present
callout_applies_to_feature
hole_termination
```

A visual/deterministic circle does not prove a physical hole.

---

# 14. P2 — Acceptance gates

B05/B06/B07 must be rewritten after P1.

---

## B05 — complete 30-cell matrix

Target:

```text
10 pages × D/V/VE = 30 cells
```

Each cell must have final disposition:

```text
valid_result
valid_reuse
failed_attempt
blocked
```

`not_run` means incomplete.

Failures stay visible.

Development pages remain part of the final matrix.

---

## B06 — real report contract

Must contain:

```text
dev/frozen separation
predicate-level metrics
D/V/VE comparison
recovery/regression
net gain
failure examples
runtime/cost
reference quality
parse/transport failures
```

A non-empty comparison object is not enough.

---

## B07 — evidence integrity

Must validate selected attempts:

```text
attempt history
artifact presence
artifact hash
producer identity
prediction input identity
model identity
runtime identity
HTTP request hash
budget ledger
matrix selection
evaluation identity
```

---

# 15. P3 — Gold/reference integrity

Before final V/VE inference:

```text
10/10 references
```

must pass strict validation.

Each scorable claim needs:

```text
claim_id
target region
callout region where applicable
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
exhaustiveness context
```

Truth states:

```text
determinate_present
determinate_absent
underdetermined
```

Reference STEP does not define what the drawing says.

---

# 16. P3 — Raster gold rule

OCR alone is not gold.

Raster claim requires:

```text
vision_checked = true
```

or explicit human/visual adjudication.

Unreadable:

```text
underdetermined
```

or excluded from scorable scope.

---

# 17. P4 — Deterministic baseline 10/10

Run D on all ten pages after producer identity is stable.

D:

```text
0 VLM inference
```

No case-specific heuristics.

Unsupported predicates stay:

```text
unknown
not_produced
abstained
```

Record:

```text
observe time
adapter time
total deterministic time
```

Do not call adapter-only time end-to-end reader time.

---

# 18. P5 — Freeze experiment

Before final V/VE:

Freeze and hash:

```text
corpus manifest
source drawing bytes
prepared raw page bytes
gold/reference
candidate schema
prompt
run contract
V/VE input definitions
matching policy
evaluator implementation
aggregation implementation
image_max_side
num_ctx
num_predict
temperature
top_p
seed
keep_alive
model tag
model digest
runtime version
```

After final results are visible:

- no prompt tuning,
- no gold editing to fit predictions,
- no tolerance loosening,
- no hard-case removal,
- no selective reruns for bad results.

A genuine bug creates a new version and preserves old evidence.

---

# 19. P6 — V/VE experiment

Only after P0R–P5 close.

First model:

```text
qwen3-vl:8b-instruct
```

No 4B yet.

No adaptive crop.

No fusion.

No verifier.

No CAD.

No STEP.

No LoRA.

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
task instructions
generation settings
raw page bytes
```

Intentional difference only:

```text
deterministic observation evidence
```

---

# 20. P6 — Budget

Keep:

```text
development <= 10
final <= 20
total <= 30
```

Every real send attempt counts:

```text
success
timeout
HTTP failure
parse failure
diagnostic call
```

Reservation before send.

No hidden retry budget.

Do not spend any final V/VE call before P0R–P5 are closed.

---

# 21. P7 — Metrics

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

Do not claim broad reliability from the ten-page provisional corpus.

---

# 22. P7 — Failure analysis

Inspect observed examples of:

```text
wrong localization
wrong R/Ø
wrong numeric value
wrong unit
wrong count
wrong termination
wrong depth
wrong target binding
physical overclaim
feature omission
ambiguous localization
schema failure
truncation
transport failure
```

Each failure example should identify:

```text
page_id
attempt_id
candidate_id
gold claim
source region
arm
```

---

# 23. P8 — Decision

001B does not require the AI to win.

Allowed outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Decision based on:

```text
net semantic gain
regression
failure severity
runtime
memory
coverage
abstention
```

No automatic transition to 001C/CAD/training.

---

# 24. Separate product-evaluation debt — X01–X04

SEMREAD does not replace these.

They remain separate blockers for product correctness.

## X01

STEP existence must not imply:

```text
accepted=true
```

## X02

Programmatically generated answers must not be marked:

```text
source=user
```

Use:

```text
simulated_user
```

or equivalent.

## X03

Cylinder evaluator must respect:

```text
cadrun cylinder value = radius
```

and not treat it as diameter.

## X04

`offline_flow.py` / `end_to_end.py` should use existing lab runner protections instead of independent subprocess orchestration.

Do not create another runner.

---

# 25. Worktree safety

Before edits:

```bash
git status
git diff -- <file>
```

Never:

```text
git reset
git clean
git stash
bulk revert
mass overwrite
```

Preserve parallel-agent changes.

---

# 26. Zero-inference test gate before P1/P2 completion

At minimum cover:

```text
unsupported frozen setting blocks send
top_p reaches actual request
seed reaches actual request
actual request settings equal run contract
every attempt directory has one history entry
open_source failure recorded
observe failure recorded
model-discovery failure recorded
runtime failure recorded
actual prepared image hashes determine input identity
prompt hash determines input identity
V/VE raw page hash identical
contract layout reaches runtime request
contract label prefix reaches runtime request
canonical model metadata
acceptance supports list-based attempts
old state migration compatibility
D stale source detection
D stale producer detection
evaluator-only change reuses prediction
producer change invalidates prediction
new evaluator creates new evaluation_run_id
```

Then continue with P1 tests.

---

# 27. P0R-FINAL completion definition

P0R-FINAL is complete only when:

```text
frozen contract == actual request
prediction input identity == actual sent inputs
every attempt directory == one history record
raw prediction validity independent of evaluator changes
D/V/VE stale detection is reliable
acceptance/report code understands the current state schema
```

and no new V/VE inference was required.

---

# 28. Immediate next task

Do only this next:

```text
P0R-FINAL
```

Specifically:

```text
1. top_p/seed request support or remove-before-freeze
2. fail-closed unsupported frozen settings
3. full lifecycle attempt finalization
4. actual prepared-input identity
5. run-contract literals wired into reader
6. canonical runtime/model metadata cleanup
7. list-based acceptance migration
8. focused zero-inference tests
```

After these pass:

```text
P0R = CLOSED
```

Then move to:

```text
P1 evaluator correctness
```

---

# 29. Final principle

The purpose of this work is not:

> “Make the VLM produce plausible engineering JSON.”

It is:

> “Know exactly what bytes and settings the model saw, preserve every execution and evaluation decision, compare it fairly against the deterministic baseline, and never allow a model guess to become engineering truth without verification.”
