# PLAN.md — drawingto3d / SEMREAD-001B

**Date:** 2026-10-04  
**Repository:** `AhmetAydemir1/drawingto3d`  
**Observed main HEAD:** `a98d742790744d5d5f5dcb4adeca8f8ef38c28a6`

---

# 1. Current verdict

The project is now in late P3.

Current verified state:

```text
P0R-FINAL                                  CLOSED
P1 evaluator correctness                  CLOSED / implemented
P2 acceptance/evidence-chain logic        CLOSED / implemented
PLAN-7 B07 audit fixes                     CLOSED
P4 deterministic D                        10/10, 0 inference

tracked canonical gold infrastructure      DONE
tracked gold coverage                      6/10
P5 freeze                                  NOT CLOSED
P6 V/VE                                    NOT STARTED
V/VE inference budget                      0/30
```

Latest HEAD is a documentation-only progress commit for `frozen-exercise-13`.

The last full-suite result documented in the repository is:

```text
1155 passed
```

Do not start V/VE inference yet.

---

# 2. What changed since the previous plan

The previous major blocker:

```text
gold exists only under gitignored out/
```

has been fixed.

The repo now contains:

```text
eval/semread_001b_gold/
    manifest.json
    README.md
    specs/
```

and:

```text
eval/semread_001b_gold_manifest.py
```

with:

```text
--write
--check
--freeze
--verify
```

The canonical truth source is now tracked in Git.

This is the correct architecture.

---

# 3. Current tracked gold coverage

Tracked manifest currently contains 6 pages:

```text
dev-plate-pocket
dev-drawing-2
dev-flange-elbow
frozen-exercise-12
frozen-exercise-17
frozen-enclosure
```

Current:

```text
6 / 10
```

Remaining:

```text
dev-flange-book
frozen-exercise-13
frozen-exercise-51
frozen-views-exercise
```

All four remaining pages require raster/visual adjudication.

---

# 4. Immediate new audit issue — cross-claim corroboration can still be circular

`frozen-exercise-17` now has three valid tracked claims, but its corroboration graph is not actually independent.

Current pattern:

```text
Ø22 claim
  → scale basis = Ø20 claim

Ø20 claim
  → scale basis = Ø22 claim
```

The validator currently rejects only:

```text
claim basis_value == that same claim's size
```

So it catches direct self-circularity, but not mutual/graph circularity.

This means:

```text
A supports B
B supports A
```

can pass.

That is not independent corroboration.

---

# 5. Fix frozen-exercise-17 corroboration before freeze

The page already has independent linear dimensions documented:

```text
14.00 → ~248 px
10.00 → ~177 px
5.00  → ~89 px
4.00  → ~71 px
```

Use one or more of those as the scale root.

Preferred:

```text
scale basis = 10.00 mm linear dimension
measured span ≈177 px
scale ≈17.7 px/mm
```

Then use the other linear dimensions as cross-checks.

For all Ø22 / Ø20 claims:

```text
corroboration.kind = independent_scale
basis = independent linear dimension
basis_value = 10.0
```

or use a structured set of independent linear bases.

Do not use another evaluated Ø/R claim as the root.

The printed Ø22 / Ø20 values remain the truth source; pixel geometry is corroboration only.

---

# 6. Strengthen corroboration validation from local to graph-level

Current validation is claim-local.

Required rule:

A corroboration basis must terminate in an independent root, not another claim in the same measured claim set unless the dependency graph is acyclic and ultimately rooted outside those claims.

Simpler and safer rule for 001B:

```text
independent_scale basis
must come from a dimension outside the evaluated Ø/R claim set
```

Examples allowed:

```text
linear 10 mm dimension
linear 60 mm dimension
known non-target datum
reliably known raster physical calibration
```

Examples rejected:

```text
Ø22 claim based on Ø20 claim
Ø20 claim based on Ø22 claim
R30 claim based on R50 when R50 depends on R30
```

Add a test explicitly for mutual circularity.

---

# 7. frozen-exercise-13 — correct the planned measurement method

Current exploration found:

```text
SCALE 1:5
3300×2550 raster
7 visible Ø/R callouts
Hough primitives unreliable
```

Current rough candidate measurements:

```text
Ø60 hub outer ≈310 px
Ø25 hub hole ≈125 px
```

These imply slightly different scale estimates.

Do not solve this by making the Ø60 and Ø25 claims corroborate each other.

Instead choose an independent linear dimension from the same orthographic view.

The drawing has multiple candidates:

```text
170
60
30
25
240
50
10
```

Preferred process:

```text
1. visually identify a clear linear dimension and its extension-line endpoints
2. measure its pixel span
3. derive scale from that linear datum
4. verify with one or more other linear dimensions
5. only then use scale as optional corroboration for Ø/R targets
```

If no reliable independent span exists:

```text
do not force px/mm calibration
```

Use:

```text
printed callout
+
visual target binding
+
target_box_norm
+
corroboration.kind = none
```

That is valid.

---

# 8. Do not use drawing scale note alone as raster px/mm

A title-block statement:

```text
SCALE 1:5
```

does not by itself define pixel/mm in a raster file.

It only becomes a pixel calibration if the raster's physical reproduction DPI / paper dimensions are independently trustworthy.

Therefore:

```text
SCALE 1:5
+
unknown/resampled raster pixels
```

must not automatically produce px/mm.

For raster gold, extension-line dimensions are safer independent calibration roots.

---

# 9. Finish frozen-exercise-13

Current visually read target set:

```text
Ø25 — upper view hole
R25 — upper view right end
R30 — lower view upper-left fillet
Ø60 — hub outer diameter
R50 — right-end arc
Ø25 — lower hub hole
R10 — slot corner
```

Before writing spec:

1. resolve each leader/target visually;
2. measure normalized target boxes;
3. choose narrow honest exhaustiveness;
4. obtain independent scale only if useful;
5. avoid using Hough IDs when primitive quality is poor;
6. require `vision_checked=true`;
7. write tracked spec;
8. regenerate reference;
9. run `check_reference`;
10. update tracked manifest;
11. run `--verify --page frozen-exercise-13`.

Then coverage becomes:

```text
7/10
```

---

# 10. dev-flange-book

Still incomplete.

Known OCR hints may assist discovery, but must not become gold alone.

Required order:

```text
visual read
→ target binding
→ target_box_norm / credible observation
→ explicit vision evidence
→ strict validation
→ tracked spec
→ verify
```

Do not infer:

```text
THRU
depth
physical hole semantics
```

unless the drawing explicitly supports them.

---

# 11. frozen-exercise-51

Complete after ex13 or in parallel.

Use the same raster rules:

```text
visual callout
measured target box
independent calibration only if available
no case-specific extractor changes
```

Do not improve the deterministic extractor using knowledge from this frozen evaluation page.

Gold annotation is allowed; production/test-targeted heuristic changes are not.

---

# 12. frozen-views-exercise

This is expected to be one of the harder pages due to lower raster resolution.

For weak image evidence:

```text
unclear symbol/value → underdetermined or out of scope
```

Do not turn model/annotator confidence into exact engineering truth.

If leader binding cannot be resolved reliably:

```text
exclude claim from scorable gold
```

and document why.

---

# 13. Gold manifest architecture is correct — preserve it

Keep the tracked chain:

```text
tracked spec
→ generated gold-src
→ generated gold
→ strict reference validation
→ evaluation
```

The generated `out/` files may remain gitignored.

The truth source is:

```text
eval/semread_001b_gold/specs/
```

not the generated `out/` copy.

---

# 14. New P5 issue — gold manifest generation is not deterministic

Current `build_manifest()` writes:

```python
"created_at": datetime.now(...)
```

Therefore:

```text
same source/spec/reference content
→ run --write again
→ different manifest bytes
→ different manifest SHA256
```

If P5 freeze binds the full manifest file hash, the benchmark identity can change even though truth did not.

This is undesirable.

---

# 15. Add a stable gold-content identity

Do not use a timestamp-bearing manifest file hash as the semantic truth identity.

Preferred design:

```text
gold_content_identity =
SHA256(canonical sorted page entries)
```

where entries include only truth-affecting fields:

```text
page_id
source_sha256
spec_sha256
reference_sha256
claim_count
vision_checked
exhaustiveness
```

Exclude:

```text
created_at
written_at
absolute local paths
machine-specific data
```

The manifest may retain `created_at` as metadata, but P5 should bind:

```text
gold_content_identity
```

not a nondeterministic full-file hash.

Alternative:

Remove `created_at` from the tracked manifest entirely.

---

# 16. New P5 issue — `--freeze` does not itself prove regeneration

Current:

```text
--freeze
```

calls the manifest consistency check.

It checks:

```text
tracked spec exists
source hash
spec hash
stored generated reference hash
10/10 coverage
```

But it does not automatically run the same regeneration proof as:

```text
--verify
```

Therefore a user can theoretically freeze:

```text
stored generated references
```

without proving that current code can regenerate those exact references.

---

# 17. Make P5 freeze atomic

Preferred behavior:

```text
--freeze
```

must internally require:

```text
1. coverage = 10/10
2. check_manifest(require_all=True)
3. regenerate every reference from tracked spec
4. compare regenerated hash with manifest reference hash
5. verify source hashes
6. verify spec hashes
7. compute stable gold_content_identity
8. write freeze artifact
```

One command should be enough.

Do not rely on a human remembering to run:

```text
--verify
```

separately.

If keeping commands separate, P5 gate must explicitly require both and record both results.

Atomic is safer.

---

# 18. Clean-clone reproducibility gate

Before P6, test from a clean working state/container:

```text
tracked repo
→ generate required corpus pages/observations
→ regenerate all 10 references
→ hashes match manifest
→ stable gold_content_identity matches freeze
```

No VLM inference.

This proves the benchmark truth is reproducible.

A local `out/` cache must not be necessary as hidden truth.

---

# 19. Check generated-reference determinism

`semread_001b_reference.py` itself produces deterministic JSON: it does not add timestamps.

Keep that.

Also ensure `gold_regions` generation does not include:

```text
runtime timestamps
temporary absolute paths
nondeterministic observation ordering
machine-specific values
```

in the generated reference path.

`--verify` must return byte-equivalent reference JSON across clean runs.

---

# 20. P3 completion gate

P3 closes only when:

```text
10/10 tracked canonical specs
10/10 generated references
10/10 check_reference.ok
10/10 manifest entries
10/10 --verify pass
no circular corroboration
```

Expected acceptance state immediately after P3 evaluation:

```text
B01 closed
B02 closed
B03 closed
B04 closed
B05 open
B06 open
B07 closed
```

B05/B06 correctly remain open until V/VE is measured.

---

# 21. D must remain reused

D is already:

```text
10/10
0 inference
```

Gold changes do not invalidate D predictions.

After 10/10 gold:

```text
evaluate existing D attempts
```

Do not rerun D merely because evaluation identity changed.

Rerun only if:

```text
producer identity changed
source/input changed
candidate schema changed
artifact invalid
```

---

# 22. P5 freeze content

The final freeze artifact should bind:

```text
HEAD / producer source identity
gold_content_identity
10 source hashes
10 spec hashes
10 reference hashes
candidate schema
prompt
semantic run contract
prediction input construction
MATCH_POLICY
evaluation implementation
acceptance implementation
model tag
model digest
runtime version
generation settings
corpus membership / split / group mapping
```

It should also state:

```text
gold annotator = agent
review_status = provisional
corpus is small / not independent holdout
```

Do not imply human-certified engineering truth.

---

# 23. Freeze must fail closed

P5 must fail if any of:

```text
missing tracked spec
untracked-only gold
source hash mismatch
spec hash mismatch
reference hash mismatch
regeneration mismatch
gold_content_identity mismatch
invalid raster vision evidence
invalid region
placeholder
circular corroboration
```

Do not permit warnings for these.

---

# 24. V/VE preflight after freeze

Before first real VLM call:

```text
--budget
--lifecycle
--matrix
freeze verification
V/VE raw image invariant
```

Expected:

```text
D valid_reuse = 10
V/VE to_run = 20
inference budget = 0/30
orphan attempts = 0
gold = 10/10
B02 = closed
B07 = closed
```

---

# 25. P6 execution

Then run only the frozen 001B experiment:

```text
model: qwen3-vl:8b-instruct
arms: V / VE
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

until 001B decision is complete.

---

# 26. Budget

Keep:

```text
development <= 10
final <= 20
total dispatched / possibly-dispatched <= 30
```

Current:

```text
0/30
```

No hidden retries.

Pre-send local failures do not consume inference budget.

---

# 27. P7 evaluation

After all intended cells receive a final disposition, produce a new immutable evaluation run.

Keep:

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

and per predicate:

```text
scorable_target_count
recovered_count
regressed_wrong_count
regressed_abstention_count
net_correct_gain
```

Separate:

```text
dev
frozen
```

---

# 28. Ambiguity must remain visible

Ambiguous matches are correctly excluded from semantic scoring.

Therefore final results must always display:

```text
semantic accuracy
+
ambiguous claim count/rate
+
localization coverage
```

Do not show semantic accuracy alone.

Otherwise abstained/ambiguous cases can make accuracy look stronger than end-to-end reading quality.

---

# 29. P8 decision

Allowed outcomes:

```text
CONTINUE_V
CONTINUE_VE
LIMIT_SCOPE
RESEARCH_FAILURE
STOP_SEMANTIC_READER
```

Use:

```text
net_correct_gain
regression severity
overclaim
abstention
ambiguity
binding accuracy
runtime
memory
failure rate
```

No single aggregate score should determine the result.

---

# 30. Product correctness remains separate

SEMREAD does not close:

```text
X01 STEP existence != accepted truth
X02 simulated eval answer != source=user
X03 radius/diameter evaluator semantics
X04 legacy evaluation paths need shared LabRunner integrity
```

Do not claim end-to-end CAD correctness from 001B.

---

# 31. Immediate next implementation package

Do this next:

```text
1. Fix frozen-exercise-17 corroboration to use independent linear datum(s).
2. Add cross-claim / mutual circularity validator test.
3. Add stable gold_content_identity excluding created_at.
4. Make --freeze require full --verify-style regeneration.
5. Finish frozen-exercise-13 using independent linear calibration or no calibration.
6. Finish dev-flange-book.
7. Finish frozen-exercise-51.
8. Finish frozen-views-exercise.
9. Reach tracked 10/10.
10. --verify all 10.
11. evaluate existing D attempts.
12. confirm B02/B07 closed and B05/B06 open.
13. clean-clone reproducibility test.
14. create P5 freeze artifact.
15. only then begin V/VE.
```

---

# 32. Required new tests

Add:

```text
mutual corroboration:
    claim A basis claim B
    claim B basis claim A
    → reject

corroboration graph:
    evaluated Ø/R claim used as only root
    → reject or require independent terminal root

linear independent basis:
    10 mm linear datum → diameter claim
    → accept

gold manifest:
    repeated build with unchanged content
    → same gold_content_identity

manifest metadata:
    created_at changes
    → gold_content_identity unchanged

freeze:
    stored references valid but regeneration mismatch
    → freeze fails

freeze:
    10/10 check passes + one --verify mismatch
    → freeze fails

clean regeneration:
    all tracked specs regenerate exact reference hashes
    → freeze passes
```

Retain existing 22 gold-manifest tests and B07 evidence-chain tests.

---

# 33. Current phase summary

```text
HEAD                 a98d742790744d5d5f5dcb4adeca8f8ef38c28a6
tracked gold         6/10
remaining gold       4 pages
D                     10/10 valid, 0 inference
B07                   closed
P5                    open
V/VE                   not started
inference budget       0/30
```

---

# 34. Final principle

The truth source is now correctly version-controlled.

The remaining job before VLM measurement is to make that truth **logically independent and reproducibly frozen**.

In particular:

> “not the same claim” is weaker than “independent evidence.”

Corroboration must ultimately root in an independent datum, and P5 must prove regeneration—not merely confirm that cached generated files match stored hashes.

After that, freeze once and measure.
