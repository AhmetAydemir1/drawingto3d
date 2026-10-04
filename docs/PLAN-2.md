# PLAN.md — drawingto3d Semantic Reader / Evaluation Integrity

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `27bbe8d783061da3e198da17c46c98a6a8d012b9`

## 1. Objective

Build a trustworthy semantic-reading evaluation path before spending final VLM inference budget or connecting the reader to CAD.

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

- The extractor must not limit what the VLM can notice.
- Model output is a candidate, never engineering truth by itself.
- STEP creation is not proof of correctness.
- Missing or ambiguous information remains unresolved and may require the user.
- Reference STEP stays evaluator-only.
- Regression/test drawings are not training data.
- No example-specific heuristics.
- No threshold loosening or test fitting.
- No `git reset`, `git clean`, bulk revert, or unrelated overwrite.

---

# 2. Current state

## 2.1 SEMREAD-001A

001A is implemented in the repository:

- multi-image local Ollama transport,
- image identity,
- final-byte image hashing,
- structured response format,
- region references,
- raw/parsed response recording,
- truncation and transport gates,
- local/offline constraints.

Committed handoff reports 001A complete.

The live `out/` artifacts are gitignored and therefore were not independently verified through GitHub during review.

## 2.2 SEMREAD-001B

The repository includes:

```text
src/drawingto3d/semantic_candidates.py
src/drawingto3d/semantic_candidate_reader.py
src/drawingto3d/semantic_deterministic.py
src/drawingto3d/semantic_evaluation.py
eval/semread_001b_pilot.py
eval/semread_001b_reference.py
eval/semread_001b_snapshot.py
eval/semread_001b_corpus_probe.py
tests/test_semread_001b.py
tests/test_semread_001b_gates.py
tests/test_semantic_candidates.py
```

D / V / VE scaffolding exists.

Current committed handoff reports:

```text
V/VE inference budget: 0 / 30
D development baseline: 4 / 4 pages
001B tests: 71 passed
```

Those run claims come from committed project documentation; live local artifacts were not independently inspected through GitHub.

---

# 3. Current decision

Do **not** start final V/VE inference yet.

`27bbe8d` implements most of the intended P0 repair, but P0 is not fully closed.

Required order:

```text
P0R — finish artifact/identity repair
P1  — evaluator correctness
P2  — acceptance-gate correctness
P3  — gold/reference integrity
P4  — deterministic baseline 10/10
P5  — freeze experiment
P6  — run V/VE
P7  — evaluate
P8  — decision
```

---

# 4. P0R — Finish artifact and identity integrity

## P0R-1 — Evaluator changes must not invalidate raw predictions

### Current problem

`producer_identity()` and `evaluation_identity()` are now separate.

However `reusable_attempt()` still requires:

```text
manifest.evaluation_identity == current evaluation_identity
```

This contradicts the intended contract:

> evaluator/gold fixes must allow already-valid raw predictions to be re-evaluated without new inference.

### Required behavior

Prediction reuse must depend on **producer identity**, input identity, model/runtime identity, settings, and prediction transport gates.

It must **not** require evaluation identity equality.

Evaluation identity belongs to the evaluation result, not prediction validity.

### Required test

Create a valid V/VE attempt.

Then change only evaluator identity.

Expected:

```text
raw prediction reusable = true
old evaluation stale = true
new evaluation can be produced without inference
```

---

## P0R-2 — `semread_001b_pilot.py` cannot fully belong to producer identity

### Current problem

`PRODUCER_IDENTITY_FILES` contains:

```text
eval/semread_001b_pilot.py
```

But that file contains both:

```text
prediction orchestration
evaluation
acceptance gates
report generation
```

Therefore changing only B05/B06/B07 or report rendering changes producer identity and invalidates raw predictions.

### Required fix

Choose one:

### Preferred

Split the file:

```text
eval/semread_001b_run.py
eval/semread_001b_evaluate.py
```

Prediction identity hashes only run-producing code.

Evaluation identity hashes only evaluation/report code.

### Acceptable temporary alternative

Move all prediction-affecting constants/functions into a small dedicated module and hash that module instead of the entire pilot file.

### Required invariant

Changing:

```text
acceptance_rows()
render_report()
reference validation
semantic_evaluation.py
```

must not invalidate raw V/VE predictions.

Changing:

```text
prompt
candidate schema
image preparation
V/VE inputs
model settings
model digest
transport behavior
```

must invalidate them.

---

## P0R-3 — Store the actual HTTP request hash

### Current problem

Attempt manifest field:

```text
request_sha256
```

is currently derived from the JSON representation of the recorded request trace.

That is not necessarily the hash of the actual HTTP request bytes.

The transport layer already exposes the real request-body hash.

### Required fix

Store both explicitly:

```text
http_request_sha256
request_manifest_sha256
```

`http_request_sha256` must come from the actual serialized request bytes generated by the transport layer.

Do not overload one field with two meanings.

---

## P0R-4 — Record actual model metadata correctly

### Current problem

`llama.py::installed_models()` correctly reads Ollama metadata from nested `details`.

`runtime_identity()` separately parses `/api/tags` and currently looks for fields such as:

```text
parameter_size
quantization_level
family
```

at the wrong level.

These may be missing in the recorded runtime metadata.

### Required fix

Reuse:

```python
installed = find_model(installed_models(), MODEL)
installed.as_dict()
```

as the canonical model metadata record.

Manifest must include:

```text
name
digest
size_bytes
parameter_size
quantization
context_length
families
capabilities
runtime version
```

`runtime_identity()` may still supply runtime version, but model metadata should use the established parser.

---

## P0R-5 — Every attempt must enter attempt history

### Current problem

Immutable attempt directories are created before several early exits.

Some early exits can return before `record_attempt()`:

```text
local preparation error
budget block
model mismatch
runtime mismatch
```

Thus disk may contain an attempt directory while `state.attempts` does not contain it.

### Required fix

Every created attempt receives a final state record.

Suggested states:

```text
prepared
blocked_budget
blocked_model_mismatch
blocked_runtime_mismatch
local_error
sent
transport_error
parse_error
pass
fail
```

The budget ledger and attempt ledger are different concepts and both must remain complete.

### Required invariant

For every:

```text
attempts/<case>/attempt-NNNN/
```

there is exactly one corresponding attempt-history entry.

---

## P0R-6 — Deterministic D attempts need stale validation too

### Current problem

V/VE reuse has identity checks.

D currently becomes matrix-ready mainly when the latest D attempt contains:

```text
response-parsed.json
```

This can allow stale deterministic baseline data after:

```text
source bytes change
observe/bind/meaning code changes
D adapter changes
candidate schema changes
```

### Required fix

D must use a deterministic equivalent of reusable-attempt validation.

Check:

```text
producer identity
source hash
page PNG hash if relevant
candidate schema
D adapter version
result validity
```

D rerun costs zero VLM inference, so stale D should be rerun rather than reused.

---

## P0R-7 — Freeze naming semantics around identities

Use these meanings consistently:

```text
producer_identity
    everything that can change raw prediction bytes/content

input_identity
    source bytes + prepared image bytes + preprocessing contract

model_identity
    tag + digest + runtime + generation settings

evaluation_identity
    gold + matching + scorer + aggregation + evaluation thresholds

attempt_id
    immutable execution instance

evaluation_run_id
    immutable evaluation instance over selected attempts
```

Avoid legacy `code_identity` in new schema except for backward compatibility.

---

## P0R-8 — P0 completion gate

P0 is complete only if all are true:

1. Immutable attempt directories.
2. Complete attempt history for every directory.
3. Raw prediction reuse ignores evaluator-only changes.
4. Producer identity excludes evaluator/report-only code.
5. Actual HTTP request hash is stored.
6. Actual model metadata is stored through canonical parser.
7. Runtime version is measured and checked.
8. V/VE stale input/model/runtime reuse is rejected.
9. D stale baseline reuse is rejected.
10. Evaluation can be rerun with new evaluator identity without new inference.
11. Focused tests cover every rule above.

Until then:

```text
P0 = IN PROGRESS
```

not complete.

---

# 5. P1 — Evaluator correctness

Do not spend V/VE inference before P1 is closed.

---

## P1-1 — Predicate-wide recovery/regression

### Current problem

`compare_arms()` currently measures recovery/regression mainly through `size`.

### Required predicates

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

For each predicate report:

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

Do not compare rates with different denominators as if they were directly comparable.

---

## P1-2 — Ambiguous matching must not arbitrarily score one candidate

### Current problem

If multiple candidates are similarly plausible localization matches, evaluator can still select one candidate and score its semantic fields.

This can make results depend on candidate ordering/ID.

### Required policy

Freeze one policy before final inference.

Recommended:

```text
ambiguous localization
→ matching_status=ambiguous
→ semantic field score excluded
→ ambiguity counted separately
```

Alternative policy is allowed only if explicitly documented before results.

---

## P1-3 — Localization and semantics need separate metrics

Do not report:

```text
matched / candidates
```

as generic candidate precision.

Use:

```text
localization_match_rate
semantic_field_accuracy
candidate_overclaim_rate
candidate_abstention_rate
```

A candidate localized correctly but semantically wrong must not look correct.

---

## P1-4 — Annotation exhaustiveness must affect false positives

### Current problem

Reference files contain `exhaustiveness` metadata but evaluator does not yet use it.

### Required behavior

Reference defines scorable scope.

Example:

```json
{
  "exhaustiveness": {
    "mode": "full_page",
    "predicates": ["form", "size", "termination"]
  }
}
```

or:

```json
{
  "exhaustiveness": {
    "mode": "regions",
    "regions": [...]
  }
}
```

Unmatched candidates outside exhaustively annotated scope become:

```text
unscorable_extra_candidate
```

not:

```text
false_positive
```

Final report must show both.

---

## P1-5 — Gold placeholder rejection

Reference validation must reject placeholders such as:

```text
EKSİK:
TODO
TBD
UNKNOWN PLACEHOLDER
```

Non-empty placeholder strings are not valid evidence.

B02 cannot close while any gold record contains placeholder material.

---

## P1-6 — Reference region validation

Every normalized region must satisfy:

```text
finite coordinates
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

Reject:

```text
NaN
inf
negative values
>1 values
zero-area boxes
reversed boxes
```

---

## P1-7 — Observation-ID validation must fail closed

### Current problem

If observation extraction fails during reference checking, an empty observation list can cause ID validation to be skipped.

### Required behavior

If a claim contains:

```text
observation_id
```

and observation extraction fails:

```text
reference_validation = error/blocked
```

Do not silently approve the reference.

---

## P1-8 — Circle representation is not physical hole truth

Preserve distinct predicates:

```text
circle_representation_present
physical_hole_present
callout_applies_to_feature
hole_termination
```

Never treat:

```text
VLM says hole
+
extractor sees circle
```

as independent proof of a physical hole.

---

# 6. P2 — Acceptance gates

Current B05/B06/B07 remain too permissive.

---

## P2-1 — B05 must validate the complete 30-cell matrix

Target matrix:

```text
10 pages × D/V/VE = 30 cells
```

Each cell must be explicitly one of:

```text
valid_result
valid_reuse
failed_attempt
blocked
```

`not_run` means matrix incomplete.

Failures stay part of final measurement.

Development pages cannot disappear because frozen pages ran.

B05 closes only when all 30 intended cells have a recorded final disposition.

---

## P2-2 — B06 must require the actual final report contract

B06 closes only if report contains:

```text
dev/frozen separation
predicate-level metrics
D/V/VE comparison
recovery/regression counts
net gain
failure examples
runtime/cost
reference-quality note
transport/parse failure counts
```

A non-empty `vs_d` object is not enough.

---

## P2-3 — B07 must validate evidence integrity

B07 closes only if all selected final attempts satisfy:

```text
attempt history entry exists
artifact directory exists
artifact hashes valid
producer identity valid
input identity valid
model identity valid
runtime identity valid
request hash recorded
budget ledger valid
matrix selection explicit
evaluation identity recorded
```

An empty/clean budget record alone must not close B07.

---

# 7. P3 — Gold/reference integrity

Before final V/VE inference:

```text
10 / 10 references
```

must exist and pass strict validation.

Each scorable claim must contain:

```text
claim_id
target region
callout region when applicable
representation
physical interpretation
form
size + unit
printed count
termination
depth
truth state
evidence
source_evidence
exhaustiveness context
```

Allowed truth states:

```text
determinate_present
determinate_absent
underdetermined
```

Reference STEP must not decide drawing truth.

---

## P3-1 — Raster reference rule

OCR alone is not gold.

Raster claims require:

```text
vision_checked = true
```

or explicit human/visual adjudication.

If unreadable:

```text
underdetermined
```

or exclude from scorable scope.

Do not create clean gold by trusting noisy OCR.

---

# 8. P4 — Deterministic baseline 10/10

Run D on all ten pages.

D must:

```text
perform zero VLM inference
```

D should not receive new case-specific heuristics.

Unsupported predicates remain:

```text
unknown
not_produced
abstained
```

Do not map legacy:

```text
confirmed
```

to product-level `supported`.

Record:

```text
observe time
adapter time
total deterministic time
```

Do not call adapter-only time end-to-end reader latency.

---

# 9. P5 — Freeze experiment

Before any final V/VE call, freeze and hash:

```text
corpus manifest
source drawing bytes
prepared page PNG bytes
gold/reference version
candidate schema
prompt
V/VE input definition
matching policy
semantic evaluator code
aggregation code
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
- no selective reruns because a result is bad.

A genuine bug creates a new version and preserves prior evidence.

---

# 10. P6 — Run V/VE

Only after P0R–P5 pass.

First 001B model remains:

```text
qwen3-vl:8b-instruct
```

No 4B comparison yet.

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

V and VE must share:

```text
model
digest
runtime
schema
task instructions
generation settings
raw page
```

The only intentional difference is observation evidence.

---

# 11. P6 — Budget

Keep:

```text
development <= 10
final <= 20
total <= 30
```

Every real inference attempt counts:

```text
success
timeout
HTTP failure
parse failure
diagnostic call
```

Reservation occurs before send.

No hidden retries.

Final budget must remain untouched until P0R–P5 are closed.

---

# 12. P7 — Final metrics

For D/V/VE separately:

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

Also report:

```text
drawing/page group count
claim count
```

Do not generalize reliability from the provisional ten-page corpus.

---

# 13. P7 — Failure analysis

Inspect representative real failures for every category that actually occurs:

```text
wrong localization
wrong R/Ø
wrong value
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

Each example must link to:

```text
page_id
attempt_id
candidate_id
gold claim
source region
arm
```

Do not invent failure categories without observed examples.

---

# 14. P8 — Decision

001B completion does not require AI to win.

Allowed outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Decision must use:

```text
net semantic gain
regression
failure severity
runtime
memory
coverage
abstention
```

Do not automatically proceed to 001C or CAD integration.

---

# 15. Separate unresolved product-evaluation debt: X01–X04

SEMREAD does not replace these fixes.

They remain open in the current repository.

---

## X01 — Acceptance semantics

`reason.py` still contains a path that ends with:

```python
Audit(accepted=True)
```

after STEP generation.

STEP existence is not product correctness.

---

## X02 — Real user vs simulated user

`eval/offline_flow.py` still programmatically answers questions and then marks records:

```python
record["source"] = "user"
```

This is invalid provenance.

Automated test answers must remain:

```text
simulated_user
```

or equivalent.

---

## X03 — Radius/diameter evaluator semantics

`cadrun.py` stores:

```text
cylinders[*][0] = radius
```

`offline_flow.py` still treats that value as diameter in comparison.

Fix before trusting cylinder feature metrics.

---

## X04 — Shared runner integrity

`offline_flow.py` and `end_to_end.py` still execute independent subprocess flows instead of using the shared lab-runner protections.

Integrate:

```text
one-heavy-job lock
timeouts
run IDs
artifact hashes
freshness
state schema
```

through existing `drawingto3d_lab`.

Do not build a second runner.

---

# 16. Worktree safety

Parallel-agent work may exist.

Before edits:

```bash
git status
git diff -- <file>
```

Never use:

```text
git reset
git clean
git stash
bulk revert
mass overwrite
```

Preserve unrelated work.

---

# 17. Zero-inference test gate before V/VE

At minimum add/keep tests for:

```text
immutable attempt numbering
complete attempt history
pre-send failure history
producer/evaluator identity separation
evaluator change does not invalidate prediction
producer change does invalidate prediction
actual HTTP request hash
canonical model metadata
runtime mismatch
source hash mismatch
page PNG mismatch
D stale attempt detection
gold placeholder rejection
gold region validation
observation-ID fail-closed
exhaustiveness-aware false positives
ambiguous localization policy
predicate-wide recovery/regression
30-cell B05
strict B06
strict B07
D zero inference
V no observation leakage
VE no gold/meaning leakage
circle != hole
R != Ø
unknown != THRU
wrong-target/right-value
zero-denominator metrics
timeout and parse failures remain visible
```

Run affected 001A compatibility tests afterward.

Do not spend new 001A inference unless its old acceptance evidence becomes invalid.

---

# 18. SEMREAD-001B completion gate

SEMREAD-001B is complete only if all are true:

1. P0R fully closed.
2. Every attempt directory has history.
3. Raw predictions survive evaluator-only changes.
4. Producer identity excludes evaluator-only logic.
5. Actual HTTP request hash is preserved.
6. Actual model/runtime identity is preserved.
7. D and V/VE stale reuse is rejected.
8. Gold is 10/10 and placeholder-free.
9. Reference regions are validated.
10. Observation-ID validation fails closed.
11. Exhaustiveness affects false-positive scoring.
12. Ambiguous matching cannot arbitrarily score a candidate.
13. Recovery/regression is predicate-wide.
14. D is 10/10 with zero inference.
15. Final 30-cell matrix has a disposition for every cell.
16. V/VE remain within 30-call budget.
17. Failures remain visible.
18. Dev/frozen are reported separately.
19. Reference remains explicitly provisional.
20. No verifier/CAD/user-effort success claim is made.
21. Final output contains an explicit evidence-based decision.

---

# 19. Next phase only after 001B

If 001B shows useful semantic value:

```text
SEMREAD-001C
```

should test:

```text
extractor-miss recovery using ImageRegionRef
real underdetermination
no forced answer
```

Only after that add a narrow verifier/F path.

Then measure:

```text
accepted_coverage
wrong_supported
accepted_recovery
accepted_regression
user_intervention
```

Only after verified semantic claims exist should they be adapted into the CAD path.

---

# 20. Final principle

The goal is not:

> “Make the VLM answer technical drawings.”

The goal is:

> “Recover correct drawing information the current deterministic reader misses, while preserving provenance, preventing stale or contaminated evaluation, measuring regressions explicitly, and never turning a model guess into engineering truth without verification.”

The immediate task is therefore:

```text
finish P0R
→ finish P1
→ finish P2
→ complete P3/P4
→ freeze P5
→ only then spend V/VE inference budget
```
