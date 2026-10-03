# PLAN.md — drawingto3d Semantic Reader / Evaluation Integrity

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `dda5120fef02250b2c2b148b9219391b54e00ab3`

## 1. Objective

Strengthen drawing understanding without turning model output into product truth.

The target architecture is:

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
- Model output must never be treated as verified truth by itself.
- A STEP file existing is not proof of correctness.
- Missing or ambiguous dimensions must remain unresolved and may require the user.
- Reference STEP is evaluator-only.
- Test/regression drawings are never training data.
- No example-specific heuristics.
- No threshold loosening to make tests pass.
- No `git reset`, `git clean`, bulk revert, or overwriting unrelated work.

---

# 2. Current state

## 2.1 SEMREAD-001A

The current repository contains the 001A implementation:

- multi-image Ollama transport,
- image identity and payload tracing,
- image hashes and final-byte dimensions,
- structured response schema,
- image-region references,
- raw/parsed response capture,
- transport and truncation gates,
- semantic transport tests.

The committed handoff reports 001A complete.

The live `out/` evidence is gitignored and therefore was not independently verified from GitHub during this review.

## 2.2 SEMREAD-001B

The repository now contains:

```text
src/drawingto3d/semantic_candidates.py
src/drawingto3d/semantic_candidate_reader.py
src/drawingto3d/semantic_deterministic.py
src/drawingto3d/semantic_evaluation.py
eval/semread_001b_pilot.py
eval/semread_001b_reference.py
eval/semread_001b_snapshot.py
eval/semread_001b_corpus_probe.py
```

The D/V/VE design is substantially implemented.

However:

- gold/reference is not complete,
- real V/VE semantic pilot results are not complete,
- final inference budget should not be spent yet,
- several evaluator and artifact-integrity issues must be fixed first.

---

# 3. Immediate priority

Do **not** start the final V/VE inference matrix yet.

First complete a zero-inference repair pass.

Order:

```text
P0 artifact integrity
P1 evaluator correctness
P2 acceptance-gate correctness
P3 gold/reference integrity
P4 deterministic baseline completeness
P5 freeze experiment
P6 run V/VE
P7 evaluate
P8 decision
```

---

# 4. P0 — Immutable attempt artifacts

## Problem

001B currently writes semantic evidence to:

```text
out/lab/semread-001b/attempts/<page>-<arm>
```

The same page/arm can be rerun during development or final measurement.

This can overwrite previous evidence.

`state["attempts"][case_id]` also stores only one current record.

## Required change

Each run must have an immutable attempt identity.

Example:

```text
out/lab/semread-001b/attempts/
    <page>-<arm>/
        attempt-0001/
        attempt-0002/
```

or:

```text
<page>-<arm>-<phase>-<timestamp-or-run-id>
```

Each attempt must record:

```text
attempt_id
page_id
arm
phase
split
created_at
code_identity
evaluation_identity
input hash
page PNG hash
model tag
model digest
runtime version
settings
request hash
result
gates
artifact index
```

`state.json` should keep attempt history, not only the latest attempt.

Final matrix cells must reference a concrete immutable attempt.

---

# 5. P0 — Reuse and stale-result validation

## Problem

`reusable_attempt()` currently validates some metadata but does not robustly prove that the current input bytes are the same as the attempt input.

## Required checks

A reusable V/VE attempt must match all of:

```text
page_id
source hash
prepared page PNG hash
code identity
prompt/schema identity
preprocessing identity
model tag
actual model digest
runtime identity
generation settings
input strategy
```

A stale attempt must never silently enter a new evaluation.

`evaluate()` must not simply read:

```text
attempts/<case>/response-parsed.json
```

without validating the attempt selected for that matrix cell.

---

# 6. P0 — Actual runtime identity

## Problem

The code defines:

```text
EXPECTED_RUNTIME = "0.32.1"
```

but currently treats it mainly as expected/report metadata.

## Required change

Before a real V/VE call:

1. query the actual local Ollama/runtime version;
2. record it;
3. compare it with the frozen expected runtime for the experiment;
4. refuse or explicitly mark the attempt incompatible if the experiment contract requires an exact match.

Also record the actual installed model metadata, not only the expected digest:

```text
model name
digest
parameter size
quantization
capabilities
runtime version
```

---

# 7. P0 — Producer identity vs evaluator identity

## Problem

Current producer `code_identity()` includes broad source files including evaluator code.

Changing only evaluation logic can therefore invalidate raw predictions unnecessarily.

At the same time, `evaluation_identity()` does not fully bind the evaluator implementation bytes.

## Required split

### Producer identity

Hash only what can change the prediction:

```text
semantic candidate schema
candidate prompt
semantic reader
image preparation
llama transport
model settings
model digest/runtime
input corpus bytes
preprocessing
```

### Evaluation identity

Hash:

```text
gold/reference
reference schema
matching policy
semantic_evaluation.py
evaluation thresholds
field scoring logic
aggregation logic
```

Changing only the evaluator must allow existing valid raw predictions to be re-evaluated without new inference.

---

# 8. P1 — Recovery/regression must be predicate-wide

## Problem

`compare_arms()` currently computes recovery/regression primarily from the `size` field.

This is not sufficient for the 001B task.

## Required fields

Compute candidate recovery/regression independently for:

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

Report for each field:

```text
recovered_count
regressed_wrong_count
regressed_abstention_count
net_correct_gain
scorable_target_count
```

Also produce an overall summary, but do not hide predicate-level behavior inside one number.

Do not compare recovery-rate and regression-rate directly when they have different denominators.

---

# 9. P1 — Ambiguous matching policy

## Problem

The evaluator can identify close candidate matches as ambiguous but still score one selected candidate.

That can make semantic scoring depend on candidate ID/order.

## Required change

If multiple candidates are within the frozen ambiguity margin for one gold claim:

```text
matching_status = ambiguous
```

The claim must not be scored as though one arbitrary candidate were uniquely correct.

Choose and document one policy before final inference, for example:

```text
A) exclude semantic field scoring for ambiguous localization
or
B) score as unresolved/ambiguous
```

Do not silently pick lexicographically and continue as normal.

---

# 10. P1 — Localization precision is not semantic precision

## Problem

Current `candidate_precision = matched / candidates` mainly measures whether a candidate localized to a gold region.

A candidate can match the region while being semantically wrong.

## Required metric split

Rename or separate:

```text
localization_match_rate
semantic_field_accuracy
candidate_overclaim_rate
candidate_abstention_rate
```

Do not call localization matching alone “candidate precision” in the final report without qualification.

---

# 11. P1 — Annotation exhaustiveness must affect false-positive scoring

## Problem

Gold/reference files record `exhaustiveness`, but the evaluator does not yet use it to decide whether unmatched candidates are scorable false positives.

## Required change

Each reference must declare what area/task is exhaustively annotated.

Unmatched predictions outside exhaustively annotated scope must be:

```text
unscorable
```

not automatically false-positive.

Possible reference fields:

```json
{
  "exhaustiveness": {
    "mode": "full_page" | "regions" | "predicates_only",
    "regions": [],
    "predicates": []
  }
}
```

Final evaluator must distinguish:

```text
false_positive
unscorable_extra_candidate
```

---

# 12. P1 — Gold placeholders must fail validation

## Problem

Reference generation may emit placeholders such as:

```text
EKSİK: gerekçe yazılmadı
EKSİK: kapsam yazılmadı
```

These are non-empty strings and can currently pass truthiness checks.

## Required change

`check_reference()` must explicitly reject:

```text
EKSİK:
TODO
UNKNOWN PLACEHOLDER
empty/default placeholder values
```

Reference validation must fail when:

```text
scope missing
exhaustiveness missing
evidence missing
source_evidence missing
invalid region
unverified raster claim
duplicate claim
invalid state
```

No placeholder-filled gold may close B02.

---

# 13. P1 — Validate reference regions

For every gold target/callout region require:

```text
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

Reject:

```text
negative coordinates
coordinates > 1
zero-area regions
reversed boxes
NaN/inf
```

Add unit tests.

---

# 14. P1 — Observation-ID validation must fail closed

## Problem

During evaluation, if observation extraction fails, current code may fall back to an empty observation list.

That can skip observation-ID validation.

## Required change

If a gold claim uses `observation_id` and the observation table cannot be produced:

```text
reference_check = blocked/error
```

Do not silently validate the reference without checking the ID.

---

# 15. P1 — Circle representation and physical hole stay separate

Keep the existing distinction:

```text
circle_representation_present
physical_hole_present
callout_applies_to_feature
hole_termination
```

Never verify physical hole presence only because:

```text
model says hole
+
extractor sees circle
```

A circle primitive is geometric representation evidence, not physical-hole proof.

---

# 16. P2 — Acceptance gates must follow the full matrix

## Problem

Current B05/B06/B07 gates are too permissive.

## Required B05

B05 closes only if the intended final matrix is complete:

```text
10 pages × D/V/VE = 30 cells
```

Each cell must explicitly be one of:

```text
valid_result
valid_reuse
failed_attempt
blocked
```

`not_run` is not completion.

Failures remain part of the final measurement and must not disappear from metrics.

Development pages are part of the final 10-page matrix and cannot be omitted merely because frozen pages ran.

## Required B06

B06 closes only if the report contains:

```text
dev vs frozen separated
predicate-level metrics
D/V/VE comparison
recovery/regression counts
net gain
failure examples
runtime/cost
reference quality note
```

## Required B07

B07 closes only if:

```text
budget valid
attempt history intact
artifact hashes valid
selected final attempts explicit
producer identity valid
evaluation identity valid
input hashes valid
model/runtime identity valid
```

---

# 17. P3 — Gold/reference completion

Before V/VE final calls:

```text
10/10 page references
```

must exist and pass validation.

Each claim must contain at least:

```text
claim_id
target region
callout region where applicable
representation
physical semantic state
form
size + unit
printed count
termination
depth
truth state
evidence
source_evidence
```

Truth states:

```text
determinate_present
determinate_absent
underdetermined
```

The reference must reflect only what the drawing itself supports.

Reference STEP, generator parameters, or model predictions must not be used as drawing truth.

All agent-generated references remain:

```text
annotator=agent
review_status=provisional
```

unless a real human review is recorded.

---

# 18. P3 — Raster gold rule

Raster OCR alone is not enough for gold.

For raster references:

```text
vision_checked = true
```

must be required for scorable claims.

If OCR is noisy and visual verification cannot determine the claim:

```text
state = underdetermined
```

or exclude it from scorable scope.

Do not fabricate clean gold from OCR output.

---

# 19. P4 — Deterministic baseline

Run D on all 10 pages.

D must remain:

```text
zero VLM inference
```

D should be adapted to the common candidate contract without adding new intelligent heuristics for target fixtures.

Unproducible predicates remain:

```text
unknown
not_produced
abstained
```

Do not map legacy:

```text
confirmed
```

to application-level supported truth.

Record timing correctly:

```text
observe time
adapter time
total D time
```

Do not report adapter-only time as end-to-end reader latency.

---

# 20. P5 — Freeze the experiment before final V/VE

Freeze and hash:

```text
corpus manifest
page PNG bytes
gold/reference version
candidate schema
prompt
matching policy
evaluator implementation
image_max_side
num_ctx
num_predict
temperature
seed
model tag
model digest
runtime version
V/VE input definitions
```

After frozen results are seen:

- do not edit prompt to improve scores,
- do not change gold to fit predictions,
- do not loosen tolerances,
- do not remove hard cases.

A genuine annotation bug may be fixed only under a new reference/evaluation version while preserving the original result.

---

# 21. P6 — Run V/VE

Only after P0–P5 pass.

Current first model:

```text
qwen3-vl:8b-instruct
```

First 001B comparison remains:

```text
D
V
VE
```

No 4B comparison yet.

No adaptive crop.

No fusion/verifier.

No CAD/STEP.

No LoRA.

### V

```text
raw full-page only
```

### VE

```text
same raw full-page bytes
+
neutral observation overlay
+
addressable observation table
```

V and VE must use the same:

```text
model
digest
runtime
schema
task instructions
generation settings
raw page
```

The only intentional difference is deterministic observation evidence.

---

# 22. P6 — Budget

Keep:

```text
development <= 10
final <= 20
total <= 30
```

D consumes 0 inference.

Every real attempt is counted:

```text
success
timeout
HTTP error
parse failure
diagnostic call
```

Reservation happens before send.

No hidden retry budget.

Do not spend final calls until all zero-inference gates are closed.

---

# 23. P7 — Final metrics

For D/V/VE separately report:

```text
localization match rate
claim recall
omission
representation accuracy
physical accuracy
R/Ø accuracy
numeric value accuracy
unit accuracy
count accuracy
termination accuracy
depth accuracy
target binding accuracy
overclaim rate
abstention rate
parse/transport failure count
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
VE better
VE worse
net difference
```

Also separate:

```text
development
frozen
```

and report:

```text
drawing/page group count
not only claim count
```

No general reliability claim may be made from this 10-page provisional corpus.

---

# 24. P7 — Failure analysis

At minimum inspect real examples for any observed category:

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
schema failure
truncation
transport failure
```

Do not invent a category if no example exists.

Each failure example should link back to:

```text
page
candidate
gold claim
source region
attempt ID
```

---

# 25. P8 — Decision after 001B

001B completion does not require V or VE to beat D.

Possible outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Decision must be based on measured gain and failure modes.

Do not automatically proceed to:

```text
001C
fusion
verifier
CAD
STEP
training
```

---

# 26. Separate blocker: product evaluation integrity X01–X04

The semantic benchmark is not a substitute for the older product-evaluation fixes.

These remain open in the current repository.

## X01 — Acceptance semantics

Current `reason.py` still contains a path ending with:

```python
Audit(accepted=True)
```

after STEP generation.

STEP creation must not itself imply product acceptance.

## X02 — Real user vs simulated user provenance

Current `eval/offline_flow.py` still programmatically answers questions and then marks all records:

```python
record["source"] = "user"
```

This is invalid provenance.

Simulated answers must remain explicitly:

```text
simulated_user
```

or equivalent.

## X03 — Radius/diameter evaluator semantics

`cadrun.py` records:

```text
cylinders[*][0] = radius
```

but `offline_flow.py` still treats the first element as diameter during comparison.

Fix evaluator semantics before trusting those feature results.

## X04 — Runner integrity

`offline_flow.py` and `end_to_end.py` still run their own subprocess chains outside the shared lab-runner protections.

Integrate them with existing:

```text
LabRunner
one-heavy-job lock
timeouts
run IDs
artifact freshness
hashes
state schema
```

Do not create a second runner.

---

# 27. Worktree safety

The repository may contain parallel-agent work.

Before editing any file:

```bash
git status
git diff -- <file>
```

Do not use:

```text
git reset
git clean
git stash
bulk revert
mass overwrite
```

Patch minimally.

Preserve unrelated changes.

---

# 28. Required test sequence before final inference

Run focused zero-inference tests first.

At minimum cover:

```text
immutable attempt IDs
attempt history
stale input rejection
runtime mismatch
actual model metadata
producer/evaluator identity separation
reference placeholder rejection
invalid reference region
observation extraction failure
exhaustiveness-aware unmatched candidate handling
ambiguous matching
predicate-wide recovery/regression
30-cell acceptance gate
budget phase enforcement
D performs zero inference
V gets no observation evidence
VE gets no gold/meaning leak
circle != hole
R != Ø
unknown != THRU
wrong-target/right-value
duplicate candidate
zero denominator
timeout/parse failure remains measurable
```

Then run affected 001A compatibility tests.

Do not perform new 001A live inference unless its own acceptance evidence truly becomes invalid.

---

# 29. SEMREAD-001B completion gate

SEMREAD-001B is complete only if all are true:

1. Immutable attempt storage exists.
2. Attempt reuse validates real input/model/runtime identities.
3. Producer and evaluator identities are separated correctly.
4. Gold is 10/10 and validation has no placeholders.
5. Reference regions and observation IDs are validated fail-closed.
6. Exhaustiveness affects false-positive scoring.
7. Ambiguous matching cannot arbitrarily score one candidate.
8. Recovery/regression is predicate-wide.
9. D runs on 10/10 pages with zero inference.
10. The final 30-cell D/V/VE matrix is complete.
11. V/VE real attempts stay within the 30-call total budget.
12. Failures remain visible and are not retried away.
13. Dev and frozen metrics are reported separately.
14. Real model digest and runtime are recorded.
15. B01–B07 are tied to actual evidence, not file existence.
16. Final report states reference status as provisional.
17. No verifier/CAD/user-effort success claim is made.
18. The run ends with a measured decision, not automatic expansion.

---

# 30. Next phase only after 001B

If 001B produces useful semantic gain:

```text
SEMREAD-001C
```

should test:

```text
extractor-miss recovery through ImageRegionRef
real underdetermination
no forced answer
```

Only after that should a narrow verifier/F path be added.

Then measure:

```text
accepted coverage
wrong-supported
accepted recovery
accepted regression
user intervention
```

Only then connect verified semantic claims into the existing CAD path.

---

# 31. Final principle

The project should optimize for:

> recovering correct information that the current reader misses, without converting model guesses into engineering truth.

The semantic reader is useful only when it improves the system as a whole.

The success question is not:

> “Did Qwen answer the drawing?”

It is:

> “Compared with the deterministic baseline, which correct claims were recovered, which correct claims were lost, which new errors appeared, what did it cost, and what evidence justifies allowing any of those claims to influence CAD?”
