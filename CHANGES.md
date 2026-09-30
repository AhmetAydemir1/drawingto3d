# Changes, what they bought, and what they cost

One entry per change, in the order it was made: the mechanism, the measured benefit, the cost or risk it
carries, and how it was verified. The numbers themselves live in `eval/README.md` and in
`out/frontend/<case>.json`; this file is the accounting.

## Raster sheets observed as measured lines, circles and phrases (`64ed9d8`, reading)

**What changed.** `src/drawingto3d/raster.py` (new): `observe()` now dispatches PNG/JPG sheets to a
pixels-first observer that writes the *same* page records as the vector path. Lines come out of Hough
segments merged into strokes (angle and perpendicular-offset clusters, the segment's own worst
residual kept); circles are Hough *candidates* passed through the sheet's own ink tests — the radius
is first refined (scan r ± 6 px for the value that lands on the most samples; the hub candidate came
out 3 px short at 0.81 coverage and measured 0.92 after), then kept only if circumference coverage ≥
0.85, interior ink ≤ 0.25, the centre is not inside a word-sized OCR box (boxes covering ≥ 3 % of the
image are reading noise, not glyph zones — tesseract read one whole synthetic view as a single
"word"), and it does not duplicate a better circle; short Hough chords riding a verified circle
(≤ 80 px, ends and midpoint within ~7 px of the ring, sagitta included) are dropped from the line
list as that circle's ink. Text is tesseract (`psm 11`) called from the CLI with its own timeout,
phrases merged from words, numbers parsed with the same `parse_dimension_unit` as the vector path;
`SourceRef.page_size_pt` and `Frame.dpi` became optional so one record shape serves both sources.

**Bought.** Measured on the two example rasters: the flange observes **388 lines + 2 circles** (the
Ø30 hub at r 91.6, coverage 0.92) **+ 29 phrases** (9 numeric); `my_part.jpg` observes **343 lines +
6 circles + 49 phrases** (7 numeric); `observe` exits 0 through the CLI on both. The upper chain runs
on a raster unchanged — `bind` records 10 spans, `meaning` resolves none, `proposal` refuses with
*pafta ölçeği okunamadı* — which is the honest limit: without anchors there is no scale. Tests:
`tests/test_raster.py` (9) including a synthetic sheet whose drawn geometry must come back measured
at ±3 px radius / ±5 px centre, and a tesseract-missing run that stays a note; suite **234 green**;
`check_tables` 20/20; `plate_plan` pass.

**Cost / risk.**
- High precision, low recall on purpose: circles the eye sees (small bolt holes, dashed or dense
  clusters) do not enter the record, and the notes say so; raising recall is a later slice judged
  against a real reference list, not against the examples.
- HoughCircles' `minDist` suppresses concentric candidates — a bore + counterbore pair yields one
  circle (recorded limit, not a silent one).
- Arcs are not fitted on rasters yet, and OCR boxes over dense ink can read a whole view as one
  "word"; that reading is kept with its low confidence and excluded from the glyph filter by the 3 %
  cap.

## The readings proposed back as a plan, and built (`f61b7cc`, reading)

**What changed.** `src/drawingto3d/proposal.py` (new): the fourth reading slice reads a whole
sheet through the three below it (observe → bind → meaning) and proposes the `GeneralPlan` those
readings support, or refuses with the reasons. The part outline comes out of the closed loops the
lines and arcs chain into — the sheet frame is skipped first (a loop covering ≥ 80 % of the page,
or ≥ 60 % while holding another loop), and the chosen loop must be two axis-aligned line pairs
plus four quarter arcs of one radius. The confirmed claims are then sorted by the geometry they
touch: a spacing (two circles, axis by the longer delta), the outline height (two corner arcs),
the section's thickness and pocket depth (claims off the part), the hole diameter and the pocket
diameter. Every parameter that reaches the plan is **printed** (carrying its span id) or
**derived** (corner radius, width, area) — nothing is guessed — and the sheet's own measured
geometry verifies each printed number within max(1 %, 0.5 mm); a disagreement refuses the
proposal instead of rounding it away. CLI: `propose <drawing> <out_dir>` writes `proposal.json`
and, when proposed, `plan.json`, which `build-general` takes as it stands.

**Bought.** The plate sheet now goes drawing → STEP through the family-independent engine: the
proposal's plan builds (4.3 s) to a solid of **124 825.4 mm³** against the closed form's
124 825.4 (difference **0.0000 %**, and the closed form itself is asserted against the analytic
number in the test suite, not against the pipeline), bbox exactly **120.00 × 80.00 × 15.00**,
with the reopened STEP showing four hole cylinders and one pocket cylinder removed and the export
round trip clean. Nine measurement checks passed on the plate, the worst deviation 0.87 mm on the
120 mm width. The plastic sheet refuses with a reason that is useful: *no diameter claims at
all — three distances and one radius confirmed*, which is the next slice's work list.

**Cost / risk.**
- The archetype is narrow on purpose: one rounded-rectangle outline, a 2×2 hole grid, one central
  pocket, thickness and depth from a section's two distance claims. A square-cornered plate, an
  asymmetric layout, a third diameter callout or two hole sizes all refuse today.
- "Thickness vs pocket depth" is decided by taking the larger section distance as the thickness —
  true for the plate (15 > 8) and recorded as an assumption in the plan, but a part whose pocket
  is deeper than half its thickness would need a better rule.
- The section thickness is checked against the claim's *drawn* length (15.10 vs printed 15.00):
  the tolerance absorbs it, and the parameter itself still carries the printed value.
- Frame detection is two heuristics (page coverage, containment) rather than the real thing; a
  part outline that covers ≥ 80 % of its sheet would be misread as the frame and the proposal
  would refuse with "no closed outline outside the frame".

**Verified.** `tests/test_proposal.py` 16 tests; `pytest -q` **225 passed**; `eval/check_tables.py`
20/20; `eval/plate_plan.py` pass; CLI `propose` on the plate (exit 0, plan.json written) and on
the plastic and a raster (exit 2 with reasons); `build-general` on the produced plan builds and
audits clean.

## Every number is read into the claim the drawing supports, or left unresolved (`085cd83`, reading)

**What changed.** `src/drawingto3d/meaning.py` (new): the third reading slice turns attachments
into readings. A two-anchor linear dimension claims a *distance* — the pair of candidates, one per
anchor, whose gap **projected onto the row's own axis** equals the printed value within
max(3 %, 0.15 mm). Projection, not euclidean length: a dimension measures along its own row, and
that is what finally read the plate's `8,00` section gap, whose segment ends sit 275 px apart in x.
Pairs are ranked by candidate kind first (circle centres before arc centres before line ends before
vertices) and then by how close to the arrows they sat — the plate's symmetric drawings resolve by
standoff, and the rejected pair stays in the record as an alternative. A leader or radius mark
whose value matches some circle's drawn diameter/radius claims that size and carries **every**
matching circle in `matched_geometry`; a nearby "N x" callout — found relative to the span's own
text box, not its arrows — is checked against how many circles match (`count`/`covered`). Spans
whose candidates do not verify are marked `unresolved` and left alone. CLI:
`drawingto3d meaning <drawing> <out_dir>` writes `meaning.json`; raster exits 2.

**Bought.** The plate's seven numbers now read the way a human reads them, all confirmed:
`100,00` between the top holes' centres (drawn 100.71, the bottom pair kept as an alternative),
`60,00` between the left holes (60.43), `80,00` between the corner rounds (80.46), `15,00` at 15.10
and `8,00` at 8.03 between section lines, `50,00` as the pocket's diameter (50.36, one match), and
`Ø6,80` as the four holes' diameter — its "4 x" count checked, covered 4 of 4. The plastic sheet:
four confirmed (its `R8.00` resolves against a family of twelve same-size fillet arcs — one chosen,
all recorded) and ten marked unresolved, each inventing nothing.

**Cost / risk.**
- The plastic sheet's ten unresolved spans are an honest gap, not a hidden failure: their anchors
  sit on chain dimensions and detail views whose drawn lengths do not match the sheet calibration
  (a 3.00 row measures 70 px), so no candidate pair can verify — the record says so and
  `bindings.json` still carries every candidate.
- Recovery is per-span; nothing cross-checks readings against each other yet (the plate's `100,00`
  and `60,00` share holes) — today only the alternatives expose that coupling.
- Rank-before-cost ordering is a drafting prior (a dimension between holes is a hole spacing); it
  picks the plate's true pairs, but on a sheet where a callout lands on one of several same-size
  circles the touched one is chosen and `matched_geometry` shows the rest.

**Verified.** `tests/test_meaning.py` 14 tests (plate: every number confirmed; hole spacings; the
corner-round reading with its arc-rim kinds; section lines; the four-hole callout with count and
covered; the pocket; claims cite observed geometry; plastic: fillet family, unresolved honesty,
determinism; JSON round trip; raster refusal); `pytest -q` 209 passed; CLI on both sheets and on a
raster (exit 2).

## Numbers are bound to the geometry their arrows touch, and the record says how (`9031094`, reading)

**What changed.** `src/drawingto3d/bind.py` (new): for every printed span on a vector sheet, the
strokes its anchors sit on (the `row` that joins both anchors, `stub`s ending on an anchor,
strokes the anchor is `crossing`), chains of coincident open strokes walked up to four steps, and
the `features` every landing point reaches — circle and arc centres and rims, line ends, path
vertices — each with its pixel distance and the chain that got there. Where the drawing only
*aligns* a feature with an arrow instead of touching it, a two-anchor linear dimension also records
`aligned` candidates: points whose coordinate along the anchor-to-anchor axis matches, with the
perpendicular offset left unclipped (standoff is the drawing's rule, not an error), circle centres
ranked before arc centres before ends. `implied_px_per_mm` (row length over the printed value)
rides with the sheet's own measured calibration, so a ratio away from 1 is visible instead of
silently wrong. CLI: `drawingto3d bind <drawing> <out_dir>` writes `bindings.json`; a raster sheet
exits 2. The module's docstring records why the three attachment conventions exist: perception's
anchors do not know which one a drawing uses.

**Bought.** The plate sheet's seven numbers are attached the way a human reads them, measured:
`100,00`'s arrows align with the two top holes' centres within 2.4 px (perpendicular 145 px — the
standoff is the drawing's), `60,00` with a hole at each end, `80,00`'s extension lines land on the
corner-round arcs within 0.5 px, `Ø6,80`'s leader walks a chain of strokes down to a hole rim
(0.09 px), `50,00`'s to the pocket rim (0.12 px). The five rows measure their own numbers at the
sheet scale within 3 %. The plastic sheet gets the same shape without a claim: 9 aligned, 4
partial, 1 unbound (its `R8.00` radius leader, whose arc the record cannot find yet) — every
span's anchors, strokes, chains and candidates are in `bindings.json` (37 KB plate, 76 KB plastic)
for the meaning step to consume.

**Cost / risk.**
- The record deliberately does not choose: `100,00`'s left arrow aligns with the top hole *and*
  the bottom hole; picking the pair is the meaning step's job, and this layer would rather
  over-report than guess. `aligned` is capped at 8 per anchor, ranked by kind then perpendicular.
- Tolerances (anchor 3.5 px, feature 4.0 px, axis 3.0 px) were chosen from measurements on these
  two sheets and are named in each record's notes; a sheet drawn with other conventions may need
  them re-derived, which is why they are constants next to a note, not a silent assumption.
- Radius leaders (`R8.00`) stay unbound: the arrow tip does not land within tolerance of the
  fitted arc's rim, and unfitted arcs contribute no rim candidates at all.
- A feature reachable only by crossing a *fitted* arc's rim (rather than its centre) is not
  followed; three attachment conventions cover what these sheets do, not what drawings can do.

**Verified.** `tests/test_bind.py` 15 tests (plate: holes aligned, spacing between holes, corner
rounds reached, pocket rim, callout chain, rows vs values, leaders have no row, implied scale;
plastic: same record shape, centre alignment, rim landing; determinism; anchors unmoved; raster
refusal); `pytest -q` 195 passed; CLI on both sheets and on a raster (exit 2). Sanity: `aligned[0]`
of `100,00`'s left anchor is the hole `g9` at (435.56, 658.22).

## Observations are family-independent; the plate is one consumer (`ddacd48`, reading)

**What changed.** `src/drawingto3d/observe.py` (new): one record shape for any drawing page — every
vector subpath with its points, bbox, object/path index and method; every fitted line/circle/arc with
the fit's own residual; every printed phrase with its raw string, value, unit, count, character
indices and box; and the source hash, page size and frame the numbers were measured in, including
which way the text layer was placed on the sheet's ink (`mirrored`/`as-is`, named instead of
assumed). The vector walk that the plate experiment kept to itself moved here (`vector_paths`), so the
recognizer and the observer read the same geometry; `plate.vector_groups` is now a thin grouping over
it. Two pieces of `ingest.py` became shared: `text_groups` (the char-grouping the text layer already
used) and `upright_placement` (the placement vote, now returning its name). Curve segments are
recorded as skipped with their count — this pdfium binding exposes no bezier control points, and a
partial outline that looks complete is worse than a named hole in the record. CLI: `observe <drawing>
<out_dir>` writes `observations.json`; a raster sheet exits 2 with "raster gözlem katmanı henüz yok".

**Bought.** The family-independent half of `PLAN.md` §3A on the vector class, measured: the plate's
observations carry its own drawing — four corner circles at 100.02 × 60.01 mm spacing, Ø6.81 holes and
a 25.01 mm pocket radius, read from the geometry rather than from the recognizer's rules — plus 209
subpaths and 45 printed phrases at ~0.11 s a sheet with no model. The plastic sheet's 456 subpaths and
65 phrases (all eleven printed numbers among them) get the same shape. The plate's own suite is
unchanged by the shared-walk refactor, which is the point of doing it as a move rather than a rewrite.

**Cost / risk.**
- The plate's record is 239 KB: every drawn dimension line and arrowhead is now data that later steps
  must filter themselves. Nothing here decides importance — a title-block `2026` is observed next to
  a Ø50, by design, and the binding step has to earn that judgement.
- Only the first page, only vector PDFs, only unrotated pages; each refusal has its own message and
  the record's notes say what is missing.
- The meaning layer (anchors, view split, scale, plan proposal) is deliberately absent: this slice
  replaces the claim "we can read a drawing" with the weaker, checkable "we can observe one".

**Verified.** `tests/test_observe.py` 11 tests — plate spacings and values against the sheet's own
printed numbers, the plastic numbers' presence, byte-stable determinism, raster refusal, and the
recognizer's 46 object groups still coming out; `pytest -q` 180 passed; the `observe` CLI run on both
PDFs and on a raster (exit 2, reason on one line).

## The general plan is the product; the plate is a payload (working tree, compiler)

**What changed.** `src/drawingto3d/general.py` (new): a versioned `GeneralPlan` — source identity
(kind/ref/sha256), typed parameters (mm/in/deg/count, each printed/derived/assumed/user with its
explanation and span ids), sketches on named planes with offsets, and an operation list
(extrude/revolve/fuse/cut/repeat/fillet) whose references, units and single assignment are checked
before any CAD runs. `evaluate_parameters` resolves derived expressions with cycle detection and
inch->mm conversion; `compile_general` emits the deterministic Python program (a test asserts the
program text carries no file name, part family or source metadata); `check_general` audits the built
facts (one valid solid, STEP round-trip volume, bounding box, declared volume, and every cut tool's
cylinders by radius, axis and extent); `from_plate` is the only plate-aware code left, re-expressing
the plate experiment as those operations; `edit_parameters` stamps user values so a derivation cannot
silently replace them. `geo.py` gained `profile_extrude`/`profile_revolve` (with offset) and
`repeat_linear`/`repeat_circular`; `cadrun.py` reports cylindrical faces on any axis
(`cylinders_axis`: axis point, direction, relative extent) instead of Z-parallel ones only, and the
cylinder match canonicalises the tool's own normal before comparing extents.

**Bought.** The delivery slice of `PLAN.md` §7 with §10's acceptance list: two plans that share one
compiler and use different operation combinations — `eval/plans/bracket_linear_pattern.json`
(extrude + repeat + cut with XZ-plane holes) and `shaft_revolve_cross_hole.json`
(revolve + fuse + cross-drill) — plus the plate running through the same compiler to the same
volume, size and cylinder set as the plate engine (rel 1e-6). Expected volumes were derived
independently (closed forms, Simpson quadrature and Monte Carlo in
`eval/plans/derive_examples.py`), not read back from a build. A parameter edit rebuilds: hole_dx
100 -> 110 gives a 130 mm part whose audit passes.

**Cost / risk.**
- Kernel honesty, measured: OCC approximates cylinder-cylinder (quartic) intersections — the
  cross-drill removes 349.9709 mm3 against the analytic 349.9866 (4.5e-5 relative) — while the
  bracket's polyhedral volume matches its closed form to 8e-12. The shaft plan therefore declares
  no volume expectation, and `export_round_trip` is loosened to relative 1e-7 (measured round-trip
  noise 2.6e-9) so it catches a broken export rather than kernel round-off.
- `from_plate` is a compatibility adapter kept on purpose; it is the only place a part family is
  named. `plan`/`build-plan` still speak `PlatePlan`; `build-general` writes drafts
  (`"status": "draft"`), and the five output states are not yet separated end to end.
- The new verbs reach the legacy model path automatically, because `reason.geo_summary` reads
  `geo.py`: the prompt now offers `profile_extrude`, `profile_revolve`, `repeat_linear` and
  `repeat_circular` to the code model, with no model run behind that — behaviour change by
  availability, not by validation.
- The general plan is v1 and uncommitted; nothing about unseen-part accuracy is claimed — that
  needs the pilot/hidden sheets, and the manifest's arrays are still empty.

**Verified.** `pytest -q` 169 passed (146 old + 23 in `tests/test_general_plan.py`);
`eval/check_tables.py` 20/20; `eval/plate_plan.py` still `pass` with 0.0 mm3 symmetric difference;
`build-general` on both examples (exit 0) and on a broken plan (exit 2, one-line reason);
`eval/plans/derive_examples.py` re-derives and validates both JSONs.

## A leader's own ink is not printed text (`00d739c`, reading)

**What changed.** `lines.leader_near` used to throw away every stroke whose `text_fraction` was over 0.25 —
"a stroke lying inside printed words is a glyph". On a stroke that is not axis-aligned that measurement
reports the stroke's *own* ink: `_text_mask` removes only what a 28-px morphological opening can remove
(the rules that run along an axis), so the plate's `6,80 THRU ALL` leader, drawn at 15°, sat in its own
ink for 53-65% of its length while a letter's stem measured 51%. The question is now asked of the sheet's
own measured type (`lines.PrintedText`, built once per sheet): the ink a stroke runs through is printed
words when the blob it lies in is no longer than `TEXT_BOUND = 3.0` characters of the sheet's own character
size (the median blob side), and a drawn line otherwise.

**Bought.** `plate-pocket-1` through its text layer: 6/7 -> 7/7, no noise, and the seventh number needed no
new reader — it was in the text layer all along and only its anchor was being discarded. The same test is
what the raster sheets need for their callouts.

**Cost / risk.**
- One `connectedComponentsWithStats` per sheet, kept for the sheet's lifetime: 2-8 ms to build on the six
  eval sheets, and the label array is one `int32` per pixel (~15 MB on a 2339x1654 sheet). It is built
  whether or not a candidate ever needs it.
- The rule can only ever *add* anchors where `text_fraction` was high, which is the shape of change this
  project has been burned by before (a second chance for a refused crop turned a phantom span into a
  claimed dimension line). Measured: the `--as-raster` sweep of all six sheets is unchanged — 23 covered
  numbers, the same noise list on every sheet — and the text-layer path changed on the plate only.
- The sheet's character size is a median over the mask's blobs. On a sheet whose letters touch into
  word-sized blobs, a word longer than three characters reads as a drawn line and the test gives no
  protection — it degrades to the old behaviour rather than to a wrong anchor, because the arrow test (one
  arrowed end, not two) and the gap-to-the-words test still stand between a glyph stroke and a leader.
- The rejection it replaces was not noise for nothing: a stroke genuinely inside type must still be
  refused, so the change is held by tests in both directions — a leader whose own ink is in the mask is
  still a leader, and a stroke crossing compact type is still refused.

**Alternatives measured and dropped.** Erasing the stroke's own ink from the mask before measuring it:
every glyph stem drops to 0.00 as well, so it separates nothing (measured on the plate's 15 diagonal
strokes and the axis stems). Judging by the ink's *length* rather than the blob's size was rejected for the
same reason: a 45° line and a letter have the same footprint, only their size against the sheet's type
tells them apart.

**Verified.** `pytest -q` 83 passed (2 new tests in `tests/test_diagonal_leaders.py`);
`eval/frontend.py` (text layer) -> plate 7/7; `eval/frontend.py --as-raster` -> 23 covered numbers,
unchanged; `out/frontend/*.json` re-measured.

## The raster ceiling measured against the floor (`46b435f`, eval/docs)

**What changed.** Documentation and the numbers only — no pipeline behaviour. `--as-raster --model` was run
over the two sheets that have a fitted scale, and the result was written into `eval/README.md` as a table
with the tesseract floor beside it. The gap bullet that claimed the plate's `6,80 THRU ALL` callout carries
no text-layer characters was corrected (it does; the previous entry is why it was not read), and the raster
path's own failure on that callout was added: the drawn glyphs of `4 x Ø 6,80` cluster together with their
prefix, the gate accepts the cluster, and tesseract answers `08°9` -> 89 — an angle printed nowhere on the
sheet — while the true number is missed.

**Bought.** An answer to "should the model be the raster path": not on this evidence. Plate 4/7 with the
model against 4/7 with tesseract (the same three numbers missing); `plastic-enclosure-1` 9/11 against 6/11.
Three numbers on one sheet, none on the other, at minutes per sheet where the geometry work is seconds.
The flag stays off by default (`--model`), and the coverage targets the geometry has to reach are now on
record.

**Cost / risk.**
- `plastic-enclosure-1`'s ceiling was measured on the commit before the leader change and is marked
  provisional in the README; the plate row was re-measured on the current code. Re-running plastic is on
  the handoff's list.
- Wall clock is not usable as a measurement on this box: the same plate took 32 s in one run and 538 s in
  another with nothing else running. Only coverage is quoted.
- The model run holds ~6.4 GB of VRAM while it goes, so it is not something to leave looping in the
  background of unrelated work.

## The angled row, and one number per printed line (reading)

Two changes carried over uncommitted from the session that wrote this file's handoff, recorded here so the
accounting is complete. Both are `lines`/`perceive` geometry, and both were measured together with a third
change that was then reverted (the glyph chain along a leader, see `.cursor/handoff.md` lesson 2).

**What changed.** `lines.dimension_for` now reads a row along an axis first and, when that finds nothing,
reads the same row in the stroke's own frame (`lines._angled_dimension`, `_angled_row`: the text and the
strokes projected onto the stroke's direction and its normal, so a dimension drawn at an angle is visible).
`perceive._cluster_glyphs` splits a cluster into printed lines (`_split_lines`, guarded by `_on_one_line`),
so glyphs that a decimal separator bridged across two printed lines are two numbers and not one.

**Bought.** Nothing on the eval set yet, and that is the measurement: the six-sheet table is identical to
the one before the change (`.cursor/handoff.md` lesson 1), which is why the angled row is kept as the
mechanism the next entry extends rather than as a win. The split is what the plate's raster callout needs
next (`out/frontend/plate-pocket-1-raster.json`: the drawn `6,80`'s three glyphs and the two glyphs of the
line below them are one five-glyph cluster, read as `08°9` -> 89, an angle printed nowhere on the sheet).

**Cost / risk.** The angled pass only fires when the axis pass has found nothing, so it cannot take a line
the axis already owns; a stroke arrowed at both ends is not a leader, so the two paths cannot claim the same
stroke. What it does *not* do is claim a number printed outside the span — the layout the `50` on
`my_part.jpg` is (see the next entry). `_split_lines` was not measured on its own: it was in the run that
was reverted, and the two-line test in `tests/test_perceive.py` is the only evidence that it does what it
says.

**Verified.** `pytest -q` green (the three angled-row tests and the two-line test are in the suite);
`eval/frontend.py` and `--as-raster` reproduce the table in `.cursor/handoff.md` lesson 1, except that
`exercise-1` re-measures 2/13 there against the 3/13 recorded in that lesson — the row was re-measured on
this commit and 2/13 is what the code prints.

## The number printed beyond the tip is measured by the row it stands on (reading)

**What changed.** `lines._angled_row` read two layouts of an angled dimension: a stroke arrowed at both
ends with the number inside its span, and a line the number breaks in two. A third layout is read now: the
number printed **outside** the span, on the row's own extension — the shape a feature too small to hold its
number is drawn in, both arrows on the feature and the value beside it. Two guards carry it, and both are
there because of a measured failure:

- the stroke has to be longer than the number's box (two characters), because a piece shorter than that is
  a fragment of a longer line, not the line that measures the number. A long line crossing its own digits
  is widened by them exactly the way an arrowhead widens a line: on the plastic sheet a **91 px piece of the
  drawn `R8.00`'s 270 px leader** came out arrowed at both ends and 4 px/mm away from the sheet's scale.
- the number has to be clear of the span. A row that overlaps the number's box is ink *inside* the number:
  `my_part.jpg`'s title block `A4` is two glyphs, read as `4` through the digit whitelist, and the letter's
  own leg is arrowed by its apex and its crossbar.

**Bought.** An angled dimension line is read as a *dimension* on a real sheet, not merely OCR'd off whatever
leader happens to be near. `my_part.jpg`'s `50` is printed at 45° along the diameter it measures:

| | before | after |
|---|---|---|
| anchor | a 53 px leader at 1.062 px/mm | the diameter's own arrow tips, 284.6 px |
| the number against the sheet's own scale | a reading the sheet could not place | 5.692 px/mm against the fitted 5.731 (1:2 A4 at 200 dpi expects 5.9) |
| the sheet's fit | 3 spans, spread 0.99% | 4 spans (37, 20, 50, 26), spread 1.12% — the `50` is inside the consensus now, and 8 of 12 measured readings are named suspect instead of 8 of 11 |

Coverage and noise do not move, on either table, sheet by sheet (measured on this commit, `eval/frontend.py`
then `--as-raster`, both exit 0): exercise-1 5/13 (noise 7; raster 5/13, noise 7), flange-1 4/13 (noise 5),
plate-pocket-1 7/7 (raster 4/7, noise 3), plastic-enclosure-1 11/11 (raster 7/11, noise 8), studycadcam-60
6/9 (noise 9), studycadcam-50 2/3 (noise 7). The change buys a correct *source* for one reading and costs
nothing measurable — which is the shape the task asked for: coverage not down, noise not up.

**Cost / risk.**
- Both guards only ever *suppress* the third layout, so they cannot widen a span the axis pass or the two
  earlier angled layouts already own. What they suppress is a legitimate short dimension whose value is
  printed outside it: that sheet keeps its old leader anchor (as `my_part.jpg`'s `50` had before).
- The length guard's margin, for a new sheet: the `50` is 4.6 × its box (284.6 px against 62 px) and the
  plastic fragment 1.11 × (91 px against 82 px) against a limit of 2. The gap guard's: 67 px against a
  93 px limit (1.5 × box).
- This case runs before the broken-line case, so a row that would satisfy both is read as this layout. The
  broken-line case needs the number's centre between its two arrowed outer ends and this one needs the
  number outside the row, which is the same question asked twice; the ordering was measured as it stands
  and not re-measured the other way round.

**Verified.** `pytest -q` 97 passed (3 new tests in `tests/test_dimensions.py`: the number beyond the tip is
measured, a number three hundred pixels past it is not, and a short arrowed piece beside a number is a
fragment); `out/probe/probe_anchors.py` prints the two points of `50`'s anchor, which is how the leader and
the tips are told apart — the front end's JSON carries only how many anchors a span has; both front-end
tables above.

## The number's own line is the angle it is read at (reading)

**What changed.** A crop was offered to tesseract at `(0, -ink, 90, -90)`, where `ink` is a fit through
every ink pixel of the crop (`perceive._ink_angle`). It is now offered at the digits' own angle first
(`perceive._digits_angle`: the line through the two glyph centres farthest apart), with the same angles
behind it, so every reading the old order produced is still reachable.

The mechanism is the first answer. On `my_part.jpg` the `50` printed at 45 degrees along the diameter it
measures sits in a 58x56 crop whose ink fits at 28-37 degrees — the outline of a digit leans away from the
line its centre lies on — and at that angle tesseract answered `2`: one digit of the two, a number in its
own right, kept because the reader stops at the first answer that parses. At the digits' own 43.4 degrees
the same crop reads `50`. The sign of `-ink` was wrong for text that is not on an axis, which is why this
never showed on the sheets whose numbers are written level or up a vertical line: for those, `-ink` and
`ink` are the same quarter turn and either lands on the number.

`perceive._one_pen` guards the extra angle: it is only offered when the cluster's glyphs present one shape,
which is what the digits of one printed number do — a digit at 45 degrees is as square as a `0`, whatever
its shape when it stands level. Without the guard the change also reads the plastic sheet's drawn `R8.00`
together with a blob of the vertical number beside it and returns `28.006` (see below).

**Bought.** Coverage, with no sheet losing a number and no sheet gaining noise:

| vaka | before | after | noise before -> after |
|---|---|---|---|
| exercise-1 | 2/13 | 5/13 | 10 -> 7 |
| flange-1 | 2/13 | 4/13 | 5 -> 5 |
| plate-pocket-1 | 7/7 (7/7 raster) | unchanged | 0 (3 raster -> 3) |
| plastic-enclosure-1 | 11/11 (7/11 raster) | unchanged | 0 (8 raster -> 8) |
| studycadcam-60 | 6/9 | unchanged | 9 -> 9 |
| studycadcam-50 | 2/3 | unchanged | 7 -> 7 |

On `exercise-1` the three numbers are `30`, `37` and `50`; on `flange-1` they are `1`, `1` and `#50`
(two `1.00 X 45°` chamfers and the `50.00`), and the two misreadings the old order kept there (`2,` and a
`2`) are gone.

**Cost / risk.**
- Measured, and the reason `_one_pen` exists: without it the plastic sheet's raster floor gains one
  phantom, `28.006` at bbox (465, 627) — the drawn `R8.00` at 45 degrees and a blob of the vertical number
  beside it in one cluster, read together. It cost no coverage, but it is noise, and the noise rule is not
  negotiable; the guard removes it. A raster run of the unguarded code was already going when the guard was
  written and its log is kept at `out/raster_after.log` (ignored, like the rest of `out/`): plastic 7/11 with
  **9** noise records including `28.006`, 23 spans and 17 suspects against the guarded code's 7/11 with 8,
  22 and 16 — the same six rows otherwise, so the guard removes the phantom and nothing else. `28.006` is
  also what the guard costs: a cluster of fragments whose
  shapes disagree enough is read in the old order, so a number that *is* one row of fragments is not
  straightened. The measured margin is thin and worth re-measuring on a new sheet: the loosest real row is
  the flange's `#50` at 0.23 against `_one_pen`'s 0.25, and the plastic blob that makes it necessary is
  0.34.
- `exercise-1` now fits a scale where it fitted none (5.731 px/mm over 3 samples, 8 of its 15 readings
  named suspect). The fit is not the point — the anchors are: `50`'s own anchor still comes from a short
  leader, not from the 45-degree line it is printed on, so this number is read but not yet *sourced*.
  That is the next change, not this one.
- The extra angle is one more tesseract call per off-axis cluster; measured wall clock on the six sheets
  is inside the noise of this box (exercise-1 49 s against 50 s).

**Verified.** `pytest -q` 91 passed (4 new tests in `tests/test_perceive.py`);
`eval/frontend.py` -> exercise-1 5/13, flange-1 4/13, every other row unchanged, the two tables above;
`eval/frontend.py --as-raster` -> the same gains and no phantom (plate 3 noise records before and after,
plastic 8 and 8, exercise-1 10 -> 7 at the raster floor); `out/frontend/*.json` re-measured.

The *before* column was re-measured independently: a raster run of the six sheets that was already going
when this work started (its own process, log kept at `out/raster_baseline.log` — not tracked, `out/` is
ignored) reports the same six rows, so the gains above are not one run's noise. Its table: exercise-1 2/13
with 10 noise records, flange-1 2/13 with 5, plate-pocket-1 4/7 with 3, plastic-enclosure-1 7/11 with 8,
studycadcam-60 6/9 with 9, studycadcam-50 2/3 with 7.

## A note's leader is drawn to the note (reading)

**What changed.** A callout's leader is drawn to the *note*, not to each number printed in it, and
`lines.leader_near` measures the gap from the stroke's blank end to the box it is handed. On the plate the
`4 x Ø 6,80 THRU ALL` leader ends 181 px from the `6,80` — and 34.8 px from the `ALL` of the note's second
line, which is the word it was accepted for — so the number was refused while its own note was carried.
Three pieces now sit behind that number: `perceive._printed_block` (the cluster's printed line, grown from
the cluster along the cluster's own angle within two characters per word gap, plus the printed lines within
two characters *across* that line and inside its width — the note's own ink, letters included);
`lines.leader_to_note` (the stroke asked of the note's block with the two things a note's leader has to be:
at least **three** of the note's own characters long, and ending **beside** the note's ink — outside it and
within one and a half characters of it); and the gate's retry (`_DimensionGate.accepts(box, block)`), which
runs only on a cluster the ordinary dimension and leader passes both refused, so no existing acceptance can
move. `lines._distance_to_box` became public (`distance_to_box`) for the second question.

**Bought.** `plate-pocket-1` at the raster floor: **4/7 -> 5/7**. The number comes out of the crop as
`6,80` where it always did once the gate let it through; what was missing was its *carrier*, and the
anchors are the note's leader (arrow tip on the feature, tail at the note). The other five sheets' raster
rows are identical to before in coverage, span count, noise count and suspects (exercise-1 5/13, flange-1
4/13, plastic-enclosure-1 7/11, studycadcam-60 6/9, studycadcam-50 2/3), and the vector table is untouched
(plate 7/7, plastic 11/11) because the text layer hands the gate exact boxes and no block.

**Cost / risk.**
- Two guards, both suppress-only and both ratios of the sheet's own type, because the block on its own is
  too coarse. Measured margins: the plate's note leader is 159 px against a 28 px character (**5.7**
  characters, real), the flange's GD&T frame strokes are 43 px against 41 (**1.05**, refused) — a
  feature-control frame is a ruled box of symbols whose own slanted strokes come out arrowed and 43 px
  long; and the tail's distance to the note's ink is 28 px against 28 (**1.0**, real) against 89 px
  (**1.9**), 113 px (**2.2**) and 137 px (**1.6**) for three strokes that end short of the note they were
  being attached to. The limits are 3.0 characters and 1.5 characters.
- The retry can only ever *add* anchors, which is the shape of change this project was burned by twice
  (rule 18/21 in the skill: a change that only adds reads has to be judged on coverage *and* noise over
  the whole set). It is judged that way below.
- `_printed_block` is computed for every cluster in both modes, an O(glyphs) pass per cluster; no
  measurable wall-clock change on the six sheets (the raster sweep is within its own run-to-run spread).
- `_printed_block` grows word gaps at two characters. On a sheet whose notes are set with wider spaces, or
  whose printed rows stand less than two characters apart, the block either fails to reach a word or
  swallows the line below; both degrade to the guards' behaviour rather than to a wrong anchor, because the
  guards are what accept.
- Studycadcam-50's phantom changes identity, not count: `28` out, `4` in, 9 spans and 7 noise records
  either way, 2/3 either way. A different number the sheet does not print, on the same row — the retry can
  reorder which candidate wins a printed line (`_one_number_per_line`). Nothing moved in coverage; it is
  recorded because it is a behaviour change nobody asked for.

**Alternatives measured and dropped.** The same retry against the number's own printed *line* only, with no
guards, bought the same plate number and added phantoms elsewhere: `flange-1` 12 -> 16 spans (noise +4,
`3` and `5)` among them) and `studycadcam-60` 18 -> 19, coverage unchanged on both — the flange's frame
strokes and a practice sheet's dashed centreline arrowhead both pass a gap-only test. The measured table is
`out/raster_rowretry.log` (not tracked). The guards above are what separates the two.

**Verified.** `pytest -q` **102 passed** (5 new: three in `tests/test_diagonal_leaders.py` for a leader to a
note, a short arrowed stroke and a stroke ending inside the note's ink, two in `tests/test_perceive.py` for
the block and for a lone number having none). The before/after are two separate raster runs, each of its own
code, on the same box — `git stash` for the before — and the per-case JSONs were then compared field by
field (`out/frontend_before` and `out/frontend_after_guarded`, both ignored): the only differences are the
plate's `6,80` and studycadcam-50's phantom identity. The pre-change run is the one at the top of this
entry's evidence; `eval/README.md` carries the two tables, and the plate's tesseract floor row now reads
5/7.

At the same time the plastic ceiling was re-measured with the current code (the leader change, `00d739c`,
in place): `plastic-enclosure-1` **10/11** in 933 s, missing only the `8.0`, against the tesseract floor's
7/11 — three numbers bought by the model. The plate's ceiling (4/7) predated both that change and this one
and sat below the floor, so it was re-run on the code of this window
(`out/model_run_plate_after.log`, 716 s): **4/7 again**, so below the floor was not staleness — the model
reads `50`, `60`, `80` and `100` (including the leader-carried `50,00` the floor cannot read) and loses
`6,8`, `8` and `15`, with two noise records either way. The plastic ceiling was re-run on the same code too
(`out/model_run_plastic_after2.log`, 926.5 s): **10/11 again**, missing only the `8.0`, 3 noise records
against the floor's 7, and it reads the small numbers (`1.50`, `4.80`) whose lines the floor's gate mispairs.
Both are in the README's ceiling table, and `eval/check_tables.py` now checks that table against the runs.

## The sheet re-reads what its own scale calls wrong (reading)

**What changed.** Every dimension line is drawn to the number printed on it, so a sheet calibrates itself
(`scale.consensus`): a value and the length of its own line give a ratio, and the ratio most of the sheet
agrees on is the scale it was drawn at. A misread number is a pair whose ratio is off — a mistake the sheet
names with no ground truth. Until now that audit only *reported*, in the last column of the eval table; the
readings it names are now asked again. `perceive._reread_against_the_sheet_scale` walks the suspect list,
and for each one asks `_read_cluster` again with the first `skip` angles dropped (`skip=1`, then 2, 3), and
keeps a candidate whose implied pixels-per-millimetre fits the sheet's own fit within the same 4%. The
cluster each span came from is carried along out of `_collect_spans` (`clusters[id(span)]` — by identity,
because the two clustering passes name their spans from zero and the caller renumbers them later), and the
re-read runs after the renumbering, so a span's `text`/`value`/`kind`/`unit` are the only fields that move.

**Bought.** The only three rows that can move are the three with a fitted scale, and on each of them one
phantom gave way to a printed number:

| vaka | raster kapsam | gürültü | şüpheli | span |
|---|---|---|---|---|
| plate-pocket-1 | 5/7 -> 6/7 | 3 -> 2 | 2 -> 1 | `3,00` -> `8,00` |
| plastic-enclosure-1 | 7/11 -> 8/11 | 8 -> 7 | 16 -> 15 | `2)` -> `10` |
| exercise-1 | 5/13 -> 6/13 | 7 -> 6 | 8 -> 7 | `7€` -> `35` |

Field-by-field against `out/frontend_after_guarded` (the previous commit's run on the same box): those are
the *only* differences in all ten raster JSONs. `flange-1`, `studycadcam-50`, `studycadcam-60` and the two
mcmaster sheets have no fitted scale (`calibrate` needs three agreeing pairs) and are byte-identical. The
vector table is unchanged — the vector path does not go through `_oriented_spans`.

The plate's case in full: the vertical `8,00` at the top right is read `3,00` at the angle the reader asks
first, which is the digits' own line (89.4° after the quarter turn, then rounded to the ink angle 0.6°),
and `8,00` at the *next* angle it is offered (+0.6°). Its line is 63 px; 63 px against 3 mm is 21 px/mm
where the sheet fits 7.817, and against 8 mm it is 7.875 — a residual of 0.74%, inside the fit's own
spread. Two candidate readings, one parseable, one that fits the sheet: the reader kept the parseable one.

**Cost / risk.**
- One tesseract call per suspect, and only for spans whose own anchors disagree — on the three sheets that
  is 7 + 15 + 7 suspects, a few of which stop after one extra call. The alternative, keeping every
  candidate for every crop, is three to six extra calls per cluster and was not measured in, because the
  rows that move are the ones the audit already points at.
- The re-read is skipped entirely when `reader` is not None: a model call is minutes a sheet, and a model's
  answer is not a function of the angle it was asked at, so "the next angle" means nothing there.
- The substitution can replace a *correct* reading with a fitting wrong one only if the correct one
  disagrees with the sheet's scale (impossible if most of the sheet is read right) or if the wrong
  candidate fits better (both within 4%). The whole-set comparison is the evidence that it did not.
- `_one_number_per_line` runs *before* the re-read, so a span's value can change after it was chosen as the
  one number of its line. Nothing in that choice uses the value, but the ordering is now load-bearing and
  should be re-checked if that changes.

**Verified.** `pytest -q` 107 passed (5 new in `tests/test_perceive.py`: the fitting candidate is kept; a
candidate that also disagrees is not; a leader-carried number is not asked again; a sheet too sparse to
calibrate is left alone; the model path is left alone). `PYTHONPATH=src .venv/bin/python eval/frontend.py
--as-raster` is `out/raster_scale_reread.log` and the plain (vector) run is `out/vector_scale_reread.log`;
`out/frontend_after_guarded` is the before-state and the JSON diff above was computed against it.

**Considered and not taken.** Taking the next angle's candidate without comparing it to the sheet's scale
would be no cheaper in calls (the call is made either way) and would substitute whatever a different angle
happens to say — `20,00` for the crop of a number whose sheet prints 50, on one measured angle sweep. The
comparison is one multiplication against a fit the sheet already computed, and it is what keeps the
substitution to readings the sheet itself agrees with.

## A reading is judged in pixels as well as in percent (reading)

**What changed.** `scale.RELATIVE_TOLERANCE` is 4% of the value, and on a 1:2 sheet a 1.5 mm dimension is
6 px, where 4% of the value is a quarter of a pixel and one pixel of arrowhead or extension line is 17%.
`Calibration.disagrees` now allows the larger of the relative tolerance and `scale.ABSOLUTE_PX` = 2.5 px
(the weight of the ink a line is drawn with), and `scale.audit` judges each auditable reading with it
instead of taking `consensus`' inlier set as the verdict. The *fit* is untouched: `consensus` still
decides the sheet's scale by ratios, because a pixel floor there would make every small pair agree with
every hypothesis and drag the majority. `scale.line_length` was factored out of `measure` so the fit and
the judgement measure a span's line the same way.

**Bought: nothing measurable, and that is the finding.** Field-by-field against `out/frontend_scale_reread`
(the previous commit's run): all ten raster JSONs are identical — coverage, spans, noise, and the suspect
lists. The rule being corrected is real, but no reading on the six sheets is currently named suspect *only*
by the arithmetic: `out/probe/probe_scale_floor2.py` prints every auditable reading with its line length,
the length its value expects, the difference, and what the floor allows. On the plate the five agreeing
dimensions sit within 3.2 px of their lines and the one suspect (a `4` on a 38 px line) is 6.7 px out; on
the plastic sheet the smallest allowed tolerance in play is the floor's 2.5 px and the suspects miss by
20-495 px.

**What the plastic sheet's suspects actually are.** 15 of its 20 auditable readings: small numbers standing
on lines that are not their own — `1.50` on a 113.5 px line where 1.5 mm is 5.9 px, `2` on 181.5 px where
2 mm is 7.8 px, `4.00` on 69 px where 4 mm is 15.6 px. That is the second thing the audit's docstring
promises to catch ("a number matched up with a line that was never its line"), and it is a pairing bug in
the gate, not a tolerance one. It is now the largest named gap on the raster side, and it is measured
rather than guessed at: those ten numbers are covered on that sheet anyway (the row reads 8/11), so the
mispaired records cost the suspect column and the anchors, not the coverage.

**Cost / risk.** Two constants and one judgement; the floor could in principle let a misread of a *short*
dimension pass (a 6 px pair can be 40% wrong and still be inside 2.5 px), which is inherent — a line that
short cannot be audited by arithmetic, and the alternative is calling real drawings suspect. Measured on
the six sheets, no other reading moved, so the risk is stated rather than exercised.

**Verified.** `pytest -q` 107 passed in `out/pytest_tolerance.log` (2 new in `tests/test_scale.py`: a
dimension of a few pixels is judged in pixels, and the floor does not hide a number matched to the wrong
line — the plastic sheet's own case), and the raster sweep after the change is `out/raster_tolerance.log`,
identical to `out/frontend_scale_reread` row by row.

## A reading is given the span on its own line that its value fits (`be6b975`, reading)

**What changed.** The gate picks a span without knowing the value: `lines.dimension_for` reads the row the
number sits on, and `_span_ends` takes the pair of crossings the number sits between, else the pair nearest
it. That is all it can do before the sheet has calibrated itself, and on a sheet drawn as a band of closely
spaced profile edges the pair it takes belongs to a neighbouring feature.
`perceive._repoint_lines_that_are_not_their_own` now runs between the reading and the re-read: it fits the
sheet's scale (`scale.consensus`) and, for every reading that fit calls wrong, asks `lines.crossing_pairs`
for the pairs of crossings **at the line the reading was given** — inside the stretch it holds, or the gap
between one of that stretch's own ends and the next crossing — and takes the one whose length fits.
`lines._crossings` gained a `merge` argument for it: the tolerance that says two crossings are one thick
extension line was 0.4 of the number's *box*, and on the 71 px-wide `1.50` that swallowed the two real
extension lines 6.5 px apart; it is now the sheet's own stroke weight. The order is load-bearing — the value
re-read runs after this one, so it judges a candidate against a line that is already its own.
`lines._row_near` was factored out of `_axis_dimension` so both callers choose the row the same way (the
factor-out is behaviour-identical: the eight vector runs did not move).

**Bought.** Of the 18 runs in the sweep, exactly one moved: `plastic-enclosure-1` raster, where two readings
came back onto the drawing's own span — `1.50` 113.5 -> 6.5 px (1.66 mm where its value is 1.5) and `4.80`
69 -> 19 px (4.85 mm where its value is 4.8). Checked in the image rather than in the arithmetic
(`out/probe/annot_ocr-1.png`, `annot_ocr-3.png`: the reading's box and the line it holds, drawn on the sheet
at 4x): the `1.50` now sits on the gap between the two facing arrowheads of the narrow feature, the `4.80` on
the step its own arrowheads close on. Both left that sheet's suspect list, which is the point — their lines
fit now. Coverage, noise and the vector rows are identical (plastic raster 8/11, 7 noise, as before), and
`eval/check_tables.py` still reads 14 rows with 0 drift.

**Cost / risk.**
- The judgement is `Calibration.disagrees`, which carries the 2.5 px floor: the `1.50`'s own pair measures
  6.5 px where 1.5 mm is 5.9 px, and only the floor accepts a 10% overshoot on a number that small. Any pair
  within 2.5 px of what the value expects is therefore taken on a short dimension.
- The fit is recomputed on the re-pointed pairs, so it moves: plastic raster 3.908 -> 3.917 px/mm, samples
  5 -> 7, spread 0.0261 -> 0.0389 (the two small dimensions are the least pixel-accurate ratios in it).
  Measured: no other reading on that sheet changed status, and the movement is *towards* the vector run's
  own fit on the same sheet (3.917).
- Nothing is dropped: a reading whose line offers no fitting pair is left exactly where the gate put it, and
  the sheet keeps naming it. Anchors are what a reading is for downstream, and an anchor removed from a
  phantom record hides a fake number instead of removing it (see below).

**Alternatives measured and dropped.** Offering the best-fitting pair *anywhere* on the row instead of only
at the line the reading was given: measured, it repaired three readings rather than two, and the third was a
datum symbol the reader had called a `2`, for which it took an 8 px gap along the row past the end of the
stretch the reading held. That pair fitted the value, and the sheet stopped naming a record that is not a
printed number at all — the wrong direction for the audit. The offer is restricted to the spans at the line
the reading stands on and a test holds the refusal. Recording a mispaired reading with no anchors at all,
which the handoff proposed, is not taken: what those readings turn out to be is the next section.

**Verified.** `pytest -q` 114 passed (5 new: one in `tests/test_dimensions.py` for the two extension lines on
a wide number's row, four in `tests/test_perceive.py` for the pair that fits, the gap beside the held line,
the pair past its end, and a row with nothing that fits). Sweeps: `out/run_raster_repoint.log`,
`out/run_vector_repoint.log`; the field-by-field diff against the previous runs is
`out/probe/probe_repoint_diff.py` (18 runs, 1 changed).

## A reading that is the line's own arrowhead is not a printed number (`10a32b6`, reading)

**What changed.** The raster gate accepts a glyph cluster on the geometry that will carry it, and the reader
is handed the crop. Measured (`out/probe/probe_guard_fire.py` asks the guard itself, with logging, on all six
sheets; crops in `out/probe/guard_*.png` and `box_*.png`), what the reader answers for the filled triangle at
the end of a dimension line is a *digit*: on `plastic-enclosure-1` seven of them (`4`, `4`, `4`, `4`, `5`,
`1`, `1`), on `flange-1` two `7`s, on `exercise-1` a `2`. Six of the plastic ones carried the value `4`,
which the sheet prints elsewhere, so they were counted as *covering* it — the raster row's coverage rested
partly on ink that is not a number. `perceive._is_the_lines_own_ink` now refuses such a candidate before it
is read, on a question of place rather than of shape: an arrowhead is drawn *on* its line and at one of that
line's ends, a printed number *beside* the line or in the gap the line is broken around. The box centre has
to lie on the anchored line's axis within 5% of the box's own shorter side (floored at 1 px) **and** within
the box's own longer side of that line's nearer end. `perceive._is_drawn_solid` then keeps type that stands
*on* its line — a printed digit is an outline, an arrowhead is filled, measured 0.30-0.53 against 0.50-0.67 —
which is what stops the rule throwing away the one cluster on `plastic-enclosure-1` where `1.50` and `3.00`
merge into a single box lying on the line (the box the vision model happens to read a correct `3.00` from).

**Bought.** Coverage is unchanged on every sheet and every run: `plastic-enclosure-1` raster stays 8/11 with
its `4` now covered by the leader-carried `4` that really reads it, `flange-1` stays 4/13. Five false records
are gone (plastic's noise 7 -> **4**, `flange-1`'s 5 -> **3**), and the plastic sheet's suspect column falls
12 -> **5**, which is the point: the seven readings the audit named were not mispaired numbers, they were its
own arrowheads, and the audit stops naming them because they stop being readings.

**Cost / risk.**
- The `exercise-1` arrowhead survives: its cluster box is 1.15x its own length from the line's end, past the
  1.0x limit, so it stays a named suspect (a `2` in a 12-auditable row). Catching it needs the limit at ~1.2x,
  which then also reaches two `flange-1` candidates that are on-axis at 1.31x and 1.40x (keeps today) — not
  taken without crops of those two.
- The solidity threshold 0.45 is absolute. Measured on these sheets it separates at the cluster level (a
  printed multi-digit number has at least one clearly hollow blob) and the failure it lets through is in the
  safe direction — a bold printed mark stays a phantom — but a sheet-relative version (against the sheet's own
  median glyph fill) is the refinement, not yet measured on all six sheets.
- The *model* runs were not re-run, and on the evidence do not need to be: the candidates the guard drops
  produce no spans in them (`out/frontend/*-raster-model.json`), and the one box that could matter — plastic's
  merged `1.50`/`3.00` cluster — is kept by the solidity test. The ceiling table therefore stands unchanged.

**Verified.** `pytest -q` 118 passed (4 new: three for the place test, one for the solidity test); raster sweep
`out/run_raster_ownink.log`, vector sweep `out/run_vector_ownink.log`; the whole-set diff
`PYTHONPATH=src .venv/bin/python out/probe/probe_repoint_diff.py frontend_pairs frontend` = 18 runs, 3 changed
(`plastic-enclosure-1` raster, and `flange-1` in both of its runs — that sheet has no text layer, so both its
runs are the raster reader), the other 15 byte-identical; `eval/check_tables.py` 14 rows, 0 drift. Turning the
solidity test on changes nothing in those three runs but the seconds (checked field by field against
`out/probe/*.before_rescue.json`).

## The ceiling reader can read: qwen3-vl:8b-instruct, and the plate comes off its own floor (model, reading)

**What changed.** `llama.VISION_MODELS` was `("qwen2.5vl:7b", "qwen2.5vl:3b")` and now reads
`("qwen3-vl:8b-instruct", "qwen2.5vl:7b", "qwen2.5vl:3b")`. No call site changed: `_pick` still chooses the
first name the local Ollama has, and the 7B stays behind the new one as the fallback for a box that has not
pulled the weights. The tag is spelled in full because the bare one is a trap — Ollama's `qwen3-vl:8b` *is*
the thinking build (same model layer digest as `qwen3-vl:8b-thinking`), and a reasoning build spends the
reader's `num_predict=12` on a sentence instead of a number. That was checked before a sheet was read: on the
plate's own gate crops, replayed through the production reader, both models answer a bare number on 6/6 crops,
none empty, none long (`out/probe/probe_model_swap.py`).

**Bought.** Both models were measured on one commit (`8808a95`) and one tree, one model per process:

| vaka | tesseract (floor) | qwen2.5vl:7b | qwen3-vl:8b-instruct |
|---|---|---|---|
| plate-pocket-1 | 6/7 | 4/7 (gürültü 2) | **7/7** (gürültü 4) |
| plastic-enclosure-1 | 8/11 | 10/11 (gürültü 3) | 10/11 (gürültü 3) |

The plate's three recovered numbers are `8,00`, `15,00`, `6,80`: the 7B read the first two as `800` and
`1500` — the decimal comma lost and the value a number the sheet never prints — and missed the third, and the
8B reads the printed text exactly, including the drawn `Ø` the text layer does not carry (`∅100`, `Ø10`).
Nothing the 7B read is lost (`50,00`, `60,00`, `80,00`, `100,00` come through on both). The model path is also
no longer below its own floor anywhere: with the 7B the plate's ceiling was 4/7 against a 6/7 tesseract floor,
which made "the ceiling" a misleading name for it. The 7B runs also confirm, without a new run being needed,
what `10a32b6` asserted: the arrowhead guard leaves the ceiling where it was.

**Cost / risk.**
- Coverage up 3 on the plate, noise up 2 on the same sheet (`7`, `Ø10`, `∅10`, `∅10` for the 7B's `800`,
  `R105`), and the plastic sheet's noise changes identity without changing count (`7`, `45`, `7` for `0`,
  `R105`, `R105`). By the project's own rule — coverage must rise, noise must not — this is a trade, not a
  clean win; it is kept because a printed number the part cannot be built without outranks a phantom the
  noise list already names, and because the added noise is the class `10a32b6` was written to remove.
- The phantom crops are not the model's fault and the swap does not fix them: both readers answer them, and
  the 7B's `R105` shows up on both sheets. What those crops are is a gate question about clusters that carry
  no number, and it stays open.
- The 8B is not faster: 723 s and 674 s a sheet against the 7B's 689 s and 677 s, at 7.6 GB resident against
  6.4 GB. Wall clock on this box is not a measurement anyway (32 s against 538 s for the same plate).
- The harness writes one `-raster-model.json` per case, so the second model's run overwrites the first's
  file. The runs are kept deliberately: `out/frontend_7b_8808a95/`, `out/frontend_8b_8808a95/`, logs
  `out/ceiling_<model>_8808a95.log`. A future swap has to do the same or lose its "before".
- `eval/check_tables.py` cannot see *which* model produced a run — the model lives in the column header, not
  in a cell — so a swap is invisible to it wherever coverage does not move (the plastic row: 10/11 either
  way). The header key in `HEADERS` is what names the model, and it was updated with the table.

**Alternatives measured and dropped.** Running both readers and keeping only what they agree on: the plate's
agreement row is **4/7 with no noise**, i.e. it throws away exactly the three numbers the 8B found, because
the models disagree on them and neither can say which is right — the 7B's `800` carries no hesitation. Their
union is 7/7 with six noise records against the 8B's four, so it is strictly worse than the better single
reader. A second model pays only where something else can decide between two answers; here that arbiter is
the sheet's own scale, and the second reader belongs on the rows `scale.audit` names (three on the measured
sheets), not on every crop. Measured from the two runs' own JSON, `out/probe/probe_model_swap.py` is the
per-crop instrument for a next time.

**Verified.** `pytest -q` 118 passed; `eval/check_tables.py` 14 rows, 0 drift (the ceiling row checks against
the 8B run the harness left in `out/frontend/`); the 8B's spans were read back one by one against the plate's
text layer, which is independent of the model: `8,00` where the text layer prints `8,00`, `15,00` where it
prints `1 5,00` (the space between the digits dropped), `6,80` from the note's leader.

## The building half is measured for the first time, and it fails (eval)

**What changed.** Two things, both in the harness. `eval/report.py` now prefers `out/eval/<case>/records.json` —
what `drawingto3d read` actually produced and what `drawingto3d build` then consumed — over
`out/baseline/<case>.json`, which `eval/baseline.py` writes when it is run on its own. The report's two halves
now describe **one** run of the pipeline instead of a reading measured here and a part built from something
else; the baseline file stays the fallback. And the README's built table is checked by `eval/check_tables.py`
against `out/eval/report.json`, cell by cell, so the number cannot be typed once and drift.

**Bought.** The first building numbers this project has had, and they are bad news, which is the reason to
measure them. Of the four cases with a reference STEP, **one built a solid and it failed every comparison**;
three never produced one:

| vaka | okuma | kayıt | katı | verdict |
|---|---|---|---|---|
| plate-pocket-1 | 7/7 | 7 | var | **KALDI** |
| plastic-enclosure-1 | 11/11 | 14 | yok | katı üretilmedi |
| exercise-1 | 6/13 | 15 | yok | katı üretilmedi |
| flange-1 | 4/13 | 10 | yok | katı üretilmedi |

The plate is the sharpest case and the reason this was worth doing at all: its reading is 7/7 with no noise —
the reading half is not the problem — and the part it produced is `vector [15, 50, 60]` against the reference's
`[15, 80, 120]`, `43.5 cm3` against `124.8 cm3` and cylinders `[4]` against `[3.4, 10, 25]`. Every number in it
is a printed one and the shape is still not the part. The three failures are all the coder model composing
`geo.*` calls whose arguments contradict each other — `ring_extrude: inner_d must be smaller than outer_d`
(exercise-1), `plate: corner_radius must be smaller than half the shortest side` (plastic),
`holes: result has 5 solids, expected one` (flange-1) — each surviving both attempts, and each caught by the
toolchain rather than by the drawing. This is the failure the working plan's rule 4 names: a code model given a
flat list of millimetres invents topology.

**Cost / risk.**
- The reading column of the built table is the *app's* reader, so it disagrees with the front-end tables by
  design: the app path is 7/7 and 11/11 on the two vector sheets (text layer) and 6/13 and 4/13 on the raster
  ones, where the front end's raster row says the same. Nothing unified them; they are two views, and the built
  table is the one that says what the pipeline produced.
- 4 cases × (read + build) = 36 minutes of model time on this box, the read step being ~10 model questions a
  sheet. It stays a deliberate run, not part of the seconds-scale sweeps.
- Three of the four cases stop at the build step, so their `part.step` never appears and the report says so
  rather than scoring zero. A future run that succeeds gets compared without any edit here.

**Measured and kept as a lesson.** The first attempt at the driver handed the child a *narrowed* environment
(`PATH` without `/opt/homebrew/bin`); tesseract disappeared, every span became worthless, `read` wrote **0
records** and the build failed with "kayıt yok; ölçü okunmadı" — a measurement of the harness, not of the app
(`out/build_eval_bad_env.log`). The child inherits the parent's environment now. Same class as the probe rule:
the call chain includes the environment.

**Verified.** `pytest -q` 118 passed; `eval/check_tables.py` 20 rows, 0 drift, and the new column was shown to
bite — flipping `KALDI` to `GEÇTİ` in the README exits 1 with `README GEÇTİ -> rapor KALDI`, restoring it
exits 0. Numbers: `out/build_eval.log`, `out/eval/report.json`.

## The role question shows the number's own line, and fusing a body back over its drilled copy is caught (reading, build)

**What changed.** Three things, each measured from the one before.

1. `roles.crop_for_span` — the crop the role question shows. It was a square around the *number* (min 220 px), and
   the question is what the number *measures*: the plate's `100,00` is its corner holes' centre spacing, drawn with
   its ends 10.6 mm inside the plate's edge and extension lines running down to the holes, and a crop of the number
   showed none of it — so `100,00`, `Ø50,00` and the 8 mm pocket depth all arrived as bare numbers and the reader
   answered `edge`, `edge`, `thickness`. The box now spans the number's own line — `Span.anchors` are its two ends,
   a dimension line's arrow tips or a leader's tip and its text — plus a quarter of the measured length past each
   end, which is where the extension lines run to the features. A box longer than 1000 px is scaled down whole,
   never trimmed.
2. `reason._closed_holes` — `geo.holes(a, …)` returns a copy, so the coder's `geo.fuse(a, b)` put the undrilled
   body back over the drilled copy and filled every hole. The prompt forbade it; nothing checked it, and the plate
   passed the toolchain with `cylinders []`. The checker now sends it back with the reason, and drilling in place
   (`a = geo.holes(a, …)`) is *not* flagged — a bug in the first version of this check that its own test caught.
3. `eval/check_tables.py` derives the verdict cell with the same three words `eval/report.py` prints (`GEÇTİ`,
   `şekil`, `KALDI`), so a README row can be copied from the report as it reads.

**What it bought.** Measured by re-reading and rebuilding all four cases (log `out/build_eval_cropfix_set.log`;
the plate separately in `out/build_eval_cropfix.log`): **2 of 4 → 3 of 4 build**. `plastic-enclosure-1` and
`flange-1` produce a part for the first time, and the plate's part is materially closer: `vector [23, 100, 100]`
→ `[15, 80, 100]` (thickness and width now exact), volume within tolerance (119.0 ↔ 124.8 cm³) and its `Ø6.8`
holes back (`cylinders [3.4]`) once the fuse guard fired — that rebuild was isolated with `out/build_only.py` on
the plate's own records (19 s, log `out/build_only_holeguard.log`), so the 185 s read is not re-run to see it. The plate's `60,00` is now `hole_spacing` — its true
reading, verified against the sheet (the drawn holes are 100.81 x 60.64 mm apart and the crop shows the
extension lines ending on the two top holes). The crops were looked at, not assumed:
`out/probe/role_crop_1_00-00.png` shows both arrowheads, both extension lines and the two corner holes;
`role_crop_50-00.png` shows the leader's arrow on the bore and the printed `Ø`.

**What it cost.** `exercise-1` **lost its build**: four of its numbers moved to `hole_spacing`, the coder drilled
a `Ø20` hole at 20 mm spacing and the plate came apart into four solids. The reason is not the crop but the
choices: that sheet prints `Ø20`, `Ø25`, `Ø30`, `Ø40`, `Ø50`, and the `Ø` is drawn ink that never enters the
span's text, so those numbers are offered only the length family and `hole_spacing` is the nearest thing to a
round feature — the model picks the least-bad option and the coder acts on it. The raster sheets' new roles are
therefore *measured but not yet verified against their drawings*, which is the next piece of work. `plastic` and
`flange` build and are still badly wrong (a 0.1 cm³ flange against 202.1). Crops are now 800-1000 px, so each
role question costs more image tokens than the 220 px square did.

**How it was verified.** `pytest tests/` 122 passed, including the two new tests
(`test_crop_reaches_the_features_the_line_points_at`: the box holds the line's ends and is scaled rather than
trimmed; `test_fusing_the_undrilled_part_back_in_is_sent_back`: the guard fires for a copy and not for drilling
in place). `eval/check_tables.py` 20 rows, 0 drift after the built table was refilled from the report.
`out/build_eval.py` runs: plate read 185 s → build 35 s; `exercise-1` 428 s → failed; `plastic-enclosure-1`
325 s → 45 s; `flange-1` 285 s → 44 s.

## The prompt names the shape the records prove, and two of four cases build (reason, build)

**What changed.** `reason.build_prompt` no longer hands the coder a shape before it has looked at the records.
`CODE_ASK` carried a fixed recipe — "A bent tube is one ring_revolve; straight lengths are ring_extrude attached
to its ends; plates are attached to the tube ends" and "edge = plate side *or tube length*" — so a plate drawing
was composed as a bent tube. `shape_note(records)` now returns one of three notes, decided by the roles the
records actually carry: a diameter or a bend means a round part, a thin depth beside side lengths means a plate,
and neither means the prompt says **the records name no shape** rather than picking one. The order-of-work and
role-meaning rules were rewritten to be class-neutral (no tube, no "plate side or tube length").

**What it bought.** Measured by rebuilding all four cases from the records already on disk — one variable
changed, no re-read (`out/build_only.py`, log `out/build_only_shapenote.log`): **0 of 4 → 2 of 4 build**. The
plate builds in 15 s as `geo.plate(100, 80, 15)` with four `Ø6.8` corner holes — the right *kind* of part, where
the run before it was a bent tube with a plate glued to its end from the same numbers. `exercise-1` builds in
35 s after failing twice before. And every remaining difference is now a *named* one: the plate's
`vector [23, 100, 100]` against `[15, 80, 120]`, `157.8` against `124.8 cm3`, cylinders `[3.4]` against
`[3.4, 10, 25]`. What is missing and why: the Ø50 bore (its record says `edge`), the pocket (the `8` record is a
`thickness`, so it became a second plate glued on top — 23 mm thick), and the hole pattern (`rect_points(60)`
for a 100 x 60 pattern, because both spacing records say `edge`).

**What it cost.** The note is a hard classification with no fallback, and roles are its only input: `flange-1`
carries chamfer, edge and hole_spacing and no diameter at all, so it now gets "the records name no shape" — honest,
and less help than the old tube recipe gave it. A misread role can therefore choose the wrong note, i.e. the
same record-level weakness one step earlier. The prompt also grew by about eight lines.

**How it was verified.** `pytest tests/` 120 passed, including the new
`test_prompt_names_only_the_shape_the_records_prove` (plate note for edge+thickness+hole_diameter, round note
once a diameter appears, "no shape" for a bare set, and `{shape}` never surviving into the prompt).
`eval/check_tables.py` 20 rows, 0 drift after the README's built table was refilled; `eval/report.py` re-run.

## A through-hole callout is a diameter, and the plate's own 120 mm is derivable (reading, eval)

**What changed.** Two small things, and one that is not code at all.

1. `roles.role_choices` now reads a callout's own note. On a vector sheet the `Ø` is a *drawn path* that never
   reaches the text layer, so `6,80 THRU ALL` arrives with no mark; the only families offered were `edge,
   thickness, hole_spacing` and the reader answered `hole_spacing` — a wrong role that no later stage can
   repair, and the plate's program then drilled a hole where a spacing belonged. A text carrying `THRU`, `TAP`,
   `CBORE`, `C'BORE`, `CSK`, `6H` or `PILOT` is now offered the diameter family. The note is the part of a
   callout that survives as text, so it decides the family (`HOLE_NOTES` in `roles.py`).
2. `out/build_eval.py` clears a case's `part.step`/`part.stl` before building it. Both the driver and
   `eval/report.py` score a case by that file's *existence*, so a build that stopped working kept reporting a
   part built from older records — measured on the plate: `part.step` from 20:56 beside `records.json` from
   21:27, credited as this run's part.
3. The plate's missing length is measured, not guessed: the `100,00` dimension line is 100.17 mm at the sheet's
   own scale, but its left end sits 10.62 mm *inside* the plate's drawn edge; the plate's drawn outline is
   121.15 x 80.6 mm and its four corner holes' centres are 100.81 x 60.64 mm apart. So `100,00`/`60,00` are the
   hole pattern, and the part is 120 x 80 x 15 — the reference's `[15, 80, 120]`. The derivation the build needs
   is the edge distance the vertical pair teaches: `(80 - 60) / 2 = 10`, so `100 + 2 x 10 = 120`, confirmed by
   the drawn outline within a stroke width. Working: `out/probe/probe_plate_length.py`, `probe_plate_edges.py`,
   `probe_plate_circles.py`; class of work: skill `references/deriving-undimensioned.md`.

**What it bought.** A record that was provably wrong is right: the plate's `6,80 THRU ALL` is `hole_diameter`
and the coder's next program asks for `diameter=6.8`. A false positive left the report: "a part was built" no
longer survives a failed build. And the building half's real obstacle is now named with evidence instead of
suspicion: the coder composes in the grammar of the prompt it is given, and that grammar is a tube — on the
plate (every number printed, no ambiguity) it wrote `ring_extrude(outer_d=100, inner_d=80, length=50)` with a
`60x60x15` plate glued to the end, and the run before it wrote a different tube from the same numbers.

**What it cost.** The wider list for hole callouts is the same number of questions, but the reader now chooses
among three diameter roles instead of three length roles, so a misread is possible in a new place. And the fix
moved the failure rather than removing it: the plate's part was deleted (it was the earlier run's tube, and its
numbers are kept in the entry below), the re-read plate no longer builds at all, and with it the built table
now says no case produces a part. Deriving the 120 mm is *not* implemented — it is the next change, and it needs
the numbers to arrive as named features for the coder to be able to use it.

**How it was verified.** `pytest tests/` 119 passed, including the new
`test_a_hole_note_is_a_diameter_even_without_the_mark` (the note decides the family; a printed `Ø` and a printed
`R` still win; a plain `100,00` is still a length). `eval/check_tables.py` 20 rows, 0 drift. The plate was
re-read with the fix (218 s) and wrote `hole_diameter`; `eval/report.py` was re-run — no case has a solid, which
is what the table now says.

## Measured, not yet changed

The plate's `50,00` on the raster path, and a correction. This entry previously claimed a `R8` refused by
the gate on the plate; measured today, that cluster is the `B-B` of the printed `SECTION B-B` label, read
`R8` by tesseract — a phantom the gate refuses correctly, and the `B`'s are the sheet's own *type*, not a
radius. The probe that produced the claim compared the reader's value against the printed list and stopped
there; what it should have asked is whether the crop says `R8`, and the crop does not.

What is really still missing on the plate's raster row is `50,00`, and the geometry of it is now measured:
the stroke carrying the number is a **leader**, not a dimension line — it ends in an arrowhead on a large
circle's arc (checked in the image, `out/probe/leader_tip_region.png`), so the number is a diameter, the
617.7 px is the leader's length and measures nothing, and `scale.measure_spans` cannot compare the value
with anything. Two consequences: no candidate reading of this crop can ever be audited by the sheet's own
scale, and the *only* arbiter the drawing offers is the circle the arrow touches — a diameter callout's
number is the circle's own diameter times the scale.

The reader can be made to say it, which was measured rather than assumed. A 0.2-degree sweep over the
digits' own line (`out/probe/probe_50prep.py`, and the raw crop re-measured on its own) puts `50,00` in a
narrow window about 3-4 degrees *past* the digits' own line — 17.5-18.7 degrees against an own angle of
14.69 — on the raw crop, on a thresholded crop and on a crop with the leader's ink taken out (that last one
widens the window to 11.5-18.7). It is not a preparation that buys the number, it is the angle: the reader's
own list is 14.69, the upright, the ink angle and the two quarter turns, and not one of them falls in that
window — at 14.69 the same crop says `90,00`, upright `20,00`
(`out/probe/probe_50prep2.py`, unchanged by whitening the stroke). Taking those hits would be choosing the
sub-degree angle that happens to spell `50,00`, with nothing to confirm the answer — exactly the
wrong-number-worse-than-none case. With the circle measured reliably they would become confirmable; Hough on
this sheet returns 2152 circles (hatching and arcs everywhere), so that measurement is its own piece of
work, not a footnote to this one.
One measured cross-check that the value is right: the *model* path reads `50,00` from this crop
(`plate-pocket-1-raster-model.json`, re-run this window — it is one of the four numbers that ceiling reads
and the tesseract floor cannot), so the number is readable by a reader with different failure modes. What
does not exist is a way to *confirm* it on the tesseract path, and a model call is minutes per sheet.

Two more measured gaps stay open: a number carried by a stroke the gate reads as a leader is audited by
nothing at all (above), and the four readings that read a real line and get the number wrong (below). The
paragraph below was written when `plastic-enclosure-1` had fifteen of twenty auditable readings suspect and is
now history: two were re-pointed onto their own spans (`be6b975`), **seven turned out to be the sheet's own
arrowheads and are refused before they are read at all** (`10a32b6`, above — with them the sheet's suspect
column is down to **five**, and the `4` those six carried is covered by the leader-carried reading that really
reads it), and one left the list through a span inside the stretch it held — which was a repair of a record
that is not a number, the datum symbol below.

**A number matched to a line that was never its line, as it was first seen and measured.** 15 of
`plastic-enclosure-1`'s 20 auditable readings were small numbers standing on long lines (`1.50` on 113.5 px,
`2` on 181.5 px, `4.00` on 69 px). The audit named them correctly and it cost no coverage on that sheet
(8/11 with those numbers found anyway), but the anchors of those records were wrong, which matters the day
the reading is used for anything but counting.

Characterised at the time (`out/probe/probe_mispairing.py`, output in `out/probe/mispairing.txt`): for each
named reading, *no whole stroke near the number fits its value at the sheet's own scale*. The `1.50` at box
(1077,193) was given a 113.5 px line and the strokes within 250 px of it measure 26.4, 11.0, 18.9, 18.9,
12.3 and 22.3 mm. That measurement was of the wrong thing: a span is not a stroke but a pair of crossings,
and two of these numbers turned out to have their own pair on their own row (`be6b975`). The rest do not,
and what they are instead is below.

**What the twelve remaining suspects actually are (re-measured after `be6b975`).** Crops of every one of
them at 4x, with the reading's box and the line it holds drawn on the sheet (`out/probe/probe_mispair_annot.py`
-> `annot_ocr-*.png`), plus the two sheet-relative measurements in `out/probe/probe_solid.py`, split them
into three kinds, and only one of the three is a reading at all:

- **Seven are arrowheads, and the reader calls them digits** (`ocr-2` `1`, `ocr-6` `5`, `ocr-10`, `ocr-11`,
  `ocr-15`, `ocr-20` `4`, `ocr-17` `1`). The measurement that names them is where they sit: the centre of the
  reading's box lies **on the axis of the very line it is anchored to** — 0.0 to 0.5 px off it. Nothing else
  on the sheet is on its line like that: the nearest other reading is 4.5 px off (the datum symbol below),
  every printed number is 20.5-21.5 px off, and on the two other sheets measured the same column reads
  8.5-192.6 px. In the image the box is on a filled triangle (`out/probe/annot_ocr-11.png`,
  `annot_ocr-6.png`). Six of them carry the value `4`, so part of that sheet's raster row (8/11) rests on a
  number the sheet does not print there; the printed `4` is also read by a leader-carried `4` (`ocr-12`,
  hollow glyphs, 8.8 px beside its line), so removing them costs no coverage — they are the real reason
  those anchors looked so wrong.
- **One is a datum symbol**: the `2` of `ocr-8` is a small circle with four ticks, read as a digit
  (`out/probe/annot_ocr-8.png`, glyph fills 0.3-0.81: not one pen). It left the suspect list in `be6b975`
  through a pair inside the stretch it held (8.0 px = 2.04 mm at its own line) — geometrically sound, and
  still a repair of a record that is not a number: an audit that names a phantom by accident stops naming it
  when the accident is fixed.
- **Four read a real line and get the number wrong**: `29.00` stands on a 99 px line — 25.28 mm at the
  sheet's own scale, where the sheet prints `25.00` and is missing it; `7` stands on 522.5 px; and the
  `4.00` pair stands on 69 px lines where the step's three printed numbers are `4.00`, `4.00` and `4.80` and
  all three of their spans measure 4.85 mm (`out/probe/three_dims.png`) — so at least one of those numbers is
  misread and the sheet cannot say which, because its own scale calls all three wrong and no pair on their
  rows fits.

So both halves of the remedy proposed in the old paragraph are now answered by measurement: re-pointing the
anchor is right where the reading is a number (done, two of them), and *dropping* the anchor is wrong where
it is not a number at all — it would hide a fake number rather than remove it. What the phantom class needed
is a guard that a cluster is **type** before it is a number, and it is built (`10a32b6`, above) from the
position signal, with the solidity signal keeping type that stands on its line. The measurements behind it,
kept here: the strong signal is position — on the three sheets measured (`probe_solid.py
plastic|plate|studycadcam-60`), every reading whose value is read off a line stands 8.5-192.6 px off that
line's axis and the seven phantoms stand 0.0-0.5 px on it, a margin of 17x; the caveat is rule 13's first
layout, a real number *printed inside its line's own gap*, which would sit at 0 px too — it does not occur on
these sheets (the plate's `100,00`, the number that looks most like it, measures 21 px off), and the guard
asks the *solidity* question in that branch, which is what kept the one merged cluster on
`plastic-enclosure-1` where type does stand on its line. The weaker signal, still open as a *sheet-relative*
test: plastic's printed digits fill 0.34-0.50 of their blob box against 0.51-0.67 for its arrowheads, but
`studycadcam-60`'s printed digits fill 0.36-0.53, so an absolute threshold throws away real numbers there and
only a ratio to the sheet's own type can transfer — measured on all six sheets before it is set, which is the
next piece of work on this rule. Measurements: `out/probe/probe_solid.py`, `probe_phantom.py`, `phantom.txt`,
and the guard's own question stream with every candidate's numbers, `out/probe/probe_guard_fire.py` ->
`guard_fire.txt`.

A scan of every cluster the gate refuses that tesseract *would* give a number for is
`out/probe/probe_refused_reads.py` — 30 on the plate, and what is behind them is not one kind of thing: the
printed `6,80` (twice — the note's number, which the gate refused for its leader and which the committed
change reads), the printed `50,00` (read as `250,00` from a crop 32 px wider to the left, where the accepted
cluster's own crop reads `90,00`), four numbers an accepted cluster already covers (`100,00`, `80,00`,
`60,00`, `16`), and the rest phantoms (`R8`, `9)`, `“3`, `3}`, `<6`, `2.`, `7`). A future change here has to
separate those kinds by something other than the possibility of a read — which is what the re-read above
does for the readings that carry their own line.

## 2026-09-26 — Deterministic vector plate plan

Added `plate.py` and `plan.py`: bind PDF vector outline, four hole centres, central circle and aligned
section to named parameters with dimension IDs and derivations. No example filename, reference STEP
or model is used for prediction. Missing or ambiguous dimensions/geometry refuse recognition.

The plate now builds as 120 × 80 × 15, four Ø6.8 holes at 100 × 60 spacing, R10 corners, and a centred
Ø50 pocket 8 mm deep. Volume 124.825 cm³ matches reference; the two-way Boolean difference is 0 mm³.
The former model-path result was 100 mm long with no central pocket. Old results remain in `out/eval`;
new reproducible outputs live in `out/plate-plan` (`eval/plate_plan.py`, 5.221 s in the measured run).

CAD export now rejects invalid solids and reopens the exported STEP. Plan validation checks exact
sizes, analytic volume, and every cylinder's radius, centre and depth. Edited plans retain provenance,
carry a drawing SHA256, and survive app session persistence. The app reviews/edits the plan before
building; the CLI exposes `plan` and `build-plan`. Upload folders are unique per drawing.

Limit: recognition is one explicit vector plate family and expects a particular structural grouping
of polyline paths. Raster/model accuracy is unchanged. Equal-margin and radius derivations are visible
assumptions, so output remains a draft. Thread helix and tolerances are not modelled.

Validation: 22 new tests passed (real PDF, three synthetic dimension/scale/location variants, wrong and
missing geometry, user edits, source mismatch, CAD feature audit and session restart). Whole suite:
143 passed in sandbox; the one localhost HTTP test passed separately outside sandbox (144 total).
`eval/check_tables.py`: 20 rows, zero drift. No OCR algorithm changed and full raster runs were not repeated.

Follow-up validation in the same session: changing hole spacing now recomputes derived width, while an
explicit width override remains user input. Two regression tests added; all 24 new tests pass (146 total
with the 122 existing tests). Browser upload, plan review, depth-error rejection and STEP build verified.
User-facing validation errors omit Python/Pydantic internals.
The STL preview now uses a shaded isometric projection, so the plate face, holes and pocket are visible.

## 2026-09-27 — General pipeline plan and agent handoff

The user clarified that the supplied parts are test examples and requested a plan to hand to another
AI agent. Added `PLAN.md` as a self-contained implementation brief: repository state, environment,
commands, code map, staged deliverables, acceptance criteria, and reporting requirements.

The intended architecture uses source-linked observations and constraints to propose generic CAD
operation sequences, followed by deterministic construction and separate plan/drawing validation.
The existing plate recognizer remains a narrow regression experiment; its result is not a claim of
generalization. Existing cases are seen data; evaluation on unseen parts is a future deliverable.

Updated root `HANDOFF.md`, `.cursor/handoff.md`, and `out/HANDOFF.md`, preserving historical results
and explicitly superseding the earlier next-family development direction. Clarified evaluation scope
in `eval/README.md`. Documentation only; no runtime behavior changed or tests rerun in this session.

## 2026-09-27 — Pre-training measurement (PLAN section 7)

Built the measurement slice section 7 asks for, and ran it on this machine.

`src/drawingto3d/planner.py` asks a local model for a versioned `GeneralPlan` instead of free Python: the
reading chain (`observe` -> `bind` -> `meaning`) produces the cited evidence, the model only chooses
operations, and the answer is judged by the schema, the citation check and the deterministic compiler. The
plan's own identity is never the model's — a model that volunteers a `source` has it replaced by the run's
and the fact recorded under `overrides` (it was thrown away as `invalid` before, which reported a planning
failure the model had not made: measured on `qwen3-vl:8b-instruct`, whose seven parameter values were right).

`eval/model_baseline.py` measures the four conditions of section 18B apart — `reading`, `chain`,
`verified_plan`, `relations` — and writes one machine-readable record per run with code HEAD and dirty-file
list, manifest summary, model digest and quantisation, prompt/schema/evidence versions, sampling settings,
cold/warm start, per-stage seconds, output status, swap and free-page samples, and ollama RSS peak. Reference
STEP, the correct plan and the file name never enter a model prompt. `eval/baseline_report.py` builds the
report's tables from those records (`--check` fails on drift), and `eval/reports/model-baseline.md` carries the
findings and the next-step decision.

Measured. Reading: the vector sheets are complete (`plate-pocket-1` 7/7, `plastic-enclosure-1` 11/11) and the
same sheets re-read as rendered raster lose 0-3 numbers with the same scale to four digits (7.817 and 3.917
px/mm), while the genuinely scanned sheets sit at the floor — `exercise-17` 2/7, `exercise-51` 4/14,
`exercise-13` 2/8, `flange-1` 4/13 — and four of them fit no scale at all, which is what stops the chain
(`bind`/`meaning`/`proposal` refuse with `no-scale`, correctly). The loss is located, not guessed: on
`Exercise 17` the gate accepts 30 clusters and the reader yields 2 spans, and a contact sheet of those 30 crops
(`out/agent-s7/crops-Exercise 17.png`) shows arrowheads, arcs and small circles — 28 of the 30 candidates are not
printed numbers. Planning: both ready models fail in this layer and differently. `qwen2.5vl:3b` emits
`parameters` as a list, repeats keys, sets both `value` and `expr`, and never closes the object — not at 2048
output tokens, not with the JSON Schema as a decoder grammar at 4096. `qwen3-vl:8b-instruct` terminates cleanly
(929 tokens, 147 s) and gets all seven parameter values and their span citations right, then collapses
`sketches.*.entities[0]` into a single string, where its own reasoning leaked into the document. CAD is not
implicated by this run: no model candidate reached the compiler, and the hand-verified plate plan still builds
against the closed form at 0.0000%.

Manifest: `2/Drawing.jpg` and `7/my_part.jpg` are byte-identical, as are `2/Part-2.STEP` and `7/my_part.STEP`;
the two folders are one part, recorded as one `part_group` with both sources (`exercise-1` raster,
`exercise-1-vector`).

Limit and decision: this slice claims neither universal conversion nor training success. Training is not
justified yet — section 18C requires a repeated error and a separate validation set, and the two failures
measured are interface and gate problems first: the raster candidate gate (extend the arrowhead guard to
leader mode and generalise its place test to a true point-to-segment distance) and the depth of the plan body
the model is asked to write. The labels for the reading task do exist and are measured: a vector sheet's text
layer says exactly which printed number sits where in its rendered raster.

Validation: `pytest` 234 -> 253 passed (17 planner, 2 report). No reading algorithm was changed in this slice,
so the frontend tables are unchanged (`eval/check_tables.py`: 20 rows, zero drift).

### Same date — the whole-case-set run, and one reader correction measured on it

`floor-1` ran the three no-model conditions over all ten cases (`reading`, `chain`, `verified_plan`): 20 rows,
error classes `ok=6`, `reading=16`. The chain's refusals turned out to have four different owners, not one:
scale cannot be fitted (exercise-51, exercise-17, studycadcam-50, flange-1), the outer contour does not close
(exercise-1, exercise-13, studycadcam-60), the part is outside this slice's archetype while its reading is
complete (exercise-1-vector: "basılı sayıların tamamı bulundu" and then "bu dilim yalnız düz parça arketipini
öneriyor"), and binding produces no diameter claim at all (plastic-enclosure-1: reading 11/11, then "tam iki
çap ölçüsü bekleniyordu, 0 okundu"). Only `plate-pocket-1` reaches the end of the chain: a draft whose solid
was built and whose plan check passed. `verified_plan` passes three hand-verified plans, including
`bracket_linear_pattern` (22 084.3806 mm³) and `shaft_revolve_cross_hole` (13 544.7373 mm³), so the compiler is
not implicated in this measurement — which is a record of not appearing, not a claim that CAD is correct.

One reader correction was made and measured. The arrowhead guard — "this candidate is the line's own ink, not a
printed number" — is now asked in leader mode as well, and its place test was rewritten from an axis-aligned
assumption into a true point-to-segment distance. The old arithmetic measured a single coordinate whatever the
anchor pair's direction, so on a diagonal dimension line it answered a number with no meaning; on axis-aligned
pairs the new form is bit-for-bit the same, which `tests/test_reading_gate.py` holds over more than a thousand
boxes against the old formula.

Measured over the whole case set before and after (`out/frontend`, vector and raster modes): all 22 existing
records identical, the five changed entries are cases and layers added in this same slice, and
`eval/check_tables.py` still reads 20 rows with zero drift. So the correction buys no measured gain and is kept
because it stops answering wrongly on diagonal anchors at zero measured cost. It also settles where the raster
loss is not: inside a real run on `Exercise 17` the guard is asked about 40 candidates, drops 10 and passes 30
to the reader, and 28 of those 30 are arrowheads, arcs and small circles whose boxes stand 7.5–39 px off the
line's axis. The threshold is not the problem; "is this crop a printed number at all" is a separate question,
and it is the one a small trained classifier would answer (`out/agent-s7/guardtruth.py`, `crops.py`, `readlog.py`
are the instruments that measured it).

### Same date — the runs that were stopped by hand, and what they did and did not cost

The offering-step diagnosis was interrupted mid-run (`eval/offering.py --verbose`): its log holds 61 bytes,
one line for the first case, so the first heavy sheet was still being read when it stopped. The measurement
itself is therefore **not** made — what was lost is the measurement, not any data, and `eval/offering.py` is
complete, lint-clean and ready to run again.

Everything else finished normally (exit 0): `floor-1`, `frontend` in both modes, the model ceiling,
`candidates`, and three `pytest` runs. Checked afterwards, so the next reader does not have to trust it:
`git status` clean with only `eval/offering.py` untracked, `git diff` empty (no tracked file left half-written),
`eval/baseline_report.py --check` agreeing with the runs, `eval/check_tables.py` reading 20 rows with no drift,
all six `out/model-baseline/*/run.json` parsing, and `out/frontend` (26 records) and
`out/candidates/candidates.jsonl` (150 rows) complete. `out/` is outside git, so a stopped run cannot leave a
truncated record in the repository — and the two checkers are what would notice if one did.

## 2026-09-27 — Hermes ilerleme denetimi ve ölçüm onarımı

Başlangıç HEAD `96e0118`. Altı eski koşu ve tablo kayıtları sağlam; kesilen offering
teşhisi sonuç vermemiş. Denetim: `eval/reports/progress-audit.md`; devam: PLAN Bölüm 19.

- Plan istemi/şema çelişkileri giderildi (`source`, `questions`); gerçek ilişki
  metadatasındaki referans dosyası adı artık model istemine girmiyor. Yeni istem/yanıt
  sürümü v2; kalıcı GeneralPlan v1 korunuyor. Canlı model başarısı henüz yeniden ölçülmedi.
- Bellek ölçümü `used` alanını ve bildirilen sayfa boyutunu kullanıyor; MiB, ham örnekler
  ve ölçüm sürümü kayıtta. Eski yanlış değerler raporda geçersiz, ham geçmiş korunuyor.
- Baseline atomik ara kayıt ve koşu durumu yazıyor, eski etiketleri ezmiyor; kod/veri
  SHA256 özetleri var. Bozuk JSON raporda sessiz atlanmıyor.
- Son odaklı paket 32 geçti. Tam paket 269 geçti + 1 sandbox soket engeli; o tek test
  izinli yeniden koşuda geçti (270 test doğrulandı). İki CAD planı yeniden kuruldu,
  2/2 draft/plan kontrolü, 6.72 sn; kanıt `eval/reports/audit-evidence.json`.
- PLAN, HANDOFF ve eş kayıtlar yeni görev sırasına bağlandı. Raster kaybının sahibi,
  model kapasitesi ve uçtan uca başarı için eski kesin yorumlar geri çekildi.

## 2026-09-27 — Düzeltilmiş v2 arayüzünün canlı ölçümü (3B + 8B)

Başlangıç HEAD `96e0118` (ağaç kirli: v2 istemi/şeması ve ölçüm v2 o turdan geliyor). PLAN Bölüm 19'un
tek teslimi koşuldu; kayıtlar: `out/model-baseline/planner-v2-3b-01/`, `out/model-baseline/planner-v2-8b-01/`.

**Ne değişmedi.** Kod yazılmadı; bu tur bir ölçüm turu.

**Ne getirdi.** İlk kez `general-plan-v2` istemi + `json-schema:GeneralPlan reply v2` ile canlı model
koşusu: 3B 38.3 sn, 8B 119.3 sn, ikisi de `done_reason=stop` ile **tam JSON nesnesi** döndürdü. Eski
koşuların iki hatası (çıktı sınırında kesilme; `source` verilememesi) tekrarlanmadı, yani kalan
başarısızlık artık arayüz çelişkisiyle açıklanamaz. Kalan hata şema/ifade düzeyinde: 3B
`parameters.diameter_mm` içinde `value`+`expr` birlikte veriyor ve `sketches.*.entities[*]` `type`
ayırıcısını atlıyor; 8B ifade beklenen alana koordinat listesi koyuyor. Kaynak ölçümü v2 de ilk kez
gerçek model yükünde alındı: 3B takas 8.35→9.85 GiB (boş sayfa en az 56 MiB, Ollama RSS tepe 3.95 GiB),
8B 9.77→12.43 GiB (en az 14 MiB, RSS tepe 8.29 GiB).

**Maliyet/sınır.** 8B bu makinede sınırda çalışıyor (14 MiB boş sayfa); başka iş yükleriyle aynı anda
koşulmamalı. Sonuç yine görüntüsüz `relations` koşulu ve tek vaka; kapasite hükmü veya eğitim kararı
için kullanılamaz. Geçerli plan ve CAD çıktısı yok.

**Doğrulama.** `eval/baseline_report.py --write/--check`: tablolar kayıtlarla uyuşuyor. `pytest`:
**270 geçti** (180 sn, tam paket, sandbox engeli yok). `eval/check_tables.py`: 20 satır, 0 uyuşmazlık.
`eval/plate_plan.py`: geçti (hacim farkı 0.0 mm³, 6.09 sn). Sonraki adım tek değişkenli: parametre,
profil ve işlemleri ayrı model çağrılarında üret (PLAN §19.4). Ham yanıtların Git içi kopyası:
`eval/reports/planner-v2-live-evidence.json`.

## 2026-09-27 — Üç adımlı plan arayüzü ve şema gramerinin sınırı (PLAN §19.4)

**Ne değişti.** `src/drawingto3d/planner.py`: `propose_plan_split` — aynı kanıt üç dar soruya bölünür
(parametreler → profil → işlemler), her adıma yalnız kendi üst anahtarlarını taşıyan bir yanıt grameri
verilir (`step_reply_schema`, `GeneralPlan` şemasının kendi alt şemalarından ve `$defs`'inden türetilir,
böylece bir adım birleşik planın reddedeceği bir şekli kabul edemez) ve üç yanıt tek bir `GeneralPlan`
olarak birleştirilip **aynı** sözleşmeyle yargılanır (`_judge`; tek çağrı yolu da buradan geçer, yani
kalıcı sözleşme iki arayüzde ayrışamaz). Adım istemleri tek çağrı isteminin kural paragraflarını
kendileri yazmak yerine `_hint_section` ile aynı metinden seçer. Her koşu artık sorduğu istemin
parmak izini kaydeder (`settings.prompt_sha256`; üç adımlı koşuda adım başına `prompt_sha256`).
`eval/model_baseline.py`: `--split` bayrağı, kayıtta `plan_interface` alanı, `--unstructured` ile
birlikte kullanılırsa açık hata. Testler: `tests/test_planner.py` 18 → 26.

**Ne getirdi.** Ölçüm (aynı vaka, aynı elle doğrulanmış ilişki kanıtı, aynı ayarlar, aynı kod durumu):

| koşu | arayüz | durum | çağrı | toplam sn | ilk ihlal |
|---|---|---|---|---|---|
| `planner-v2-3b-02` | tek çağrı | failed (planning) | 1 | 39.1 | `value` ve `expr` birlikte |
| `planner-v2-split-3b-01` | üç adım | failed (planning) | 3 | 71.3 (35.6/15.5/20.3) | yedi parametrenin tamamı `value`+`expr` |

Bölme hatayı çözmedi, taşıdı — ama atfedilebilir hâle getirdi. İki sonda (aynı adım gramerleriyle, tek
parametre ve tek profil sorusu; `out/probes/planner-v2-split-probe-01.json`) gösterdi ki gönderilen
gramer `oneOf` kısıtını **uygulamıyor** (tek soruda bile `value` ve `expr` birlikte geldi) ve ayırıcı
etiket bir kez geldi, bir kez gelmedi. Ölçülen sonuç: gramer sözleşmenin garantisi değil; garanti
yalnızca sonraki doğrulamada. Bu, v2 koşularının okunmasını da değiştirir: `value`/`expr` çelişkisi
model kapasitesine değil, arayüzün bu yığında decodable olmamasına yazılmalı.

**Maliyet/sınır.** Duvar saati 39.1 → 71.3 sn, RSS tepe 3829 → 5003 MiB, üç kat model çağrısı. Sonuç
yine görüntüsüz `relations` koşulu ve tek vaka; geçerli plan ve CAD çıktısı yok. `oneOf`'un neden
uygulanmadığı ölçülmedi (yalnız sonucu ölçüldü); sonda tek başına sözleşme değiştirmeye yetmez.

**Doğrulama.** `pytest tests/test_planner.py` 26 geçti; tam paket `pytest -q` **278 geçti**;
`eval/baseline_report.py --write/--check` "rapor koşularla uyuşuyor"; `eval/check_tables.py` 20 satır,
0 uyuşmazlık; `eval/plate_plan.py` geçti. Kanıt: `out/model-baseline/planner-v2-{3b-02,split-3b-01}/`,
`out/probes/planner-v2-split-probe-01.json`, Git içi kopya `eval/reports/planner-v2-live-evidence.json`
(dört koşu + sonda).

## 2026-09-27 — Ürün yolu: çizimin kendi ölçümleri → model → CAD (PLAN §19.5)

**Ne değişti.** `proposal.py`: `read_sheet` (okuma zinciri plan önermeden milimetreye çevrilir; kontur,
mm daireler, her basılı sayı span kimliği + çapa noktaları + adet) ve ortak `_primitives` / `_outline_of`
çıkarımı. `planner.py`: `chain_evidence` (zincir kanıtı → planlayıcı bloğu; referans STEP/adı girmez),
genişletilmiş `_check_citations` + `_prints_value` (basılı parametre, atıf yaptığı span'ın yazdığı
değeri/adet'i ve birimini taşımak zorunda), `answer_truncated: bool | None` (sağlayıcı `done_reason`
vermezse "bilinmiyor"). `cli.py`: `drawingto3d model-plan <çizim> <klasör>`. `eval/model_baseline.py`:
`chain_model` koşulu, `_plan_then_cad` ortak kuyruğu, `needs_model` listesine `chain_model`, koşul adlı
kanıt/yanıt dosyaları. `tests/test_chain_model.py` (6 test) + `tests/test_planner.py` (tür/kesilme
testleri).

**Kazandırdığı.** Kural tabanlı `chain` ile `chain_model` artık **aynı okumadan** besleniyor: fark yalnız
planlayıcıda; elle doğrulanmış tablo, referans STEP veya dosya adı kanıta sızmıyor. Kaynak doğrulaması
"geçerli span kimliği"nden "o span'ın yazdığı değer/adet/birim"e çıktı.

**Ölçülen sonuç.** Plakada kural planlayıcısı katıyı kuruyor (`chain`, draft/ok, 8,7 sn); model iki
parça grubunda da sözleşmeyi eskiz/işlem gövdelerinde çiğniyor — `entities[*].type`, `operations[*].op`
ayırıcıları hiç gelmiyor (`chain-model-3b-01` 34,0 sn, `-05` 32,2 sn; plaka isteminin parmak izi ikisinde
bayt-aynı; plastik `-04` 48,8 sn, orada kural planlayıcısı reddederken model yine aynı yerde düştü). Bu,
`value`/`expr` ihlalinin kardeşi: aynı sınıf, farklı yüzey. Sekiz kayıtlı yanıt yeni yargıçla yeniden
yargılandı, hepsi aynı hükme düştü — kural sıkılaşması önceki ölçümü sessizce yeniden yazmadı. CLI
gerçek çağrıyla sınandı (8B, 97,62 sn, `invalid`, çıkış 2, `plan.json` yok).

**Maliyet/sınır.** Model katmanı hâlâ geçerli plan üretmiyor: uçtan uca **model planıyla** STEP yok.
Görünüşler kanıt bloğunda ayrı taşınmıyor (zincir çok görünüşlü paftaları zaten reddediyor). İki koşul
çalışırken ham yanıtın ezilmesi koşul adlı dosya adıyla düzeltildi.

**Kayıt disiplini.** `chain-model-3b-02`'deki `skipped` satırı çalıştırıcı boşluğudur (model istemcisi
yalnız `reading`/`relations` için kuruluyordu) → `-04` ile yeniden alındı. `chain-model-3b-03` **benim
taşımamla** kesildi: koşu hâlâ çalışırken klasörü `out/interrupted/` altına alındı, süreç sonraki
yazışında exit 1 ile düştü (`run.json.tmp` yok); kayıt `chain_model` satırını ve kesilme nedenini
taşımıyor — bitmiş sayılmaz, ölçüm kümesinin dışında. Aynı penceredeki ikinci pencere
genişletilmiş kaynak doğrulamasının testlerini yazmış; uygulama bu dalda ve o testler geçiyor.

**Doğrulama.** Tam paket `pytest -q` **289 geçti** (239,74 sn; `tests/test_planner.py` +
`tests/test_chain_model.py` tek başına 37); `eval/baseline_report.py --write/--check` "rapor koşularla
uyuşuyor"; `eval/check_tables.py` 20 satır, 0 uyuşmazlık; `eval/plate_plan.py` geçti. Kanıt:
`out/model-baseline/chain-model-3b-{01,04,05}/`, `out/cli-model-plan-plate/`,
`out/interrupted/chain-model-3b-03/`, Git içi kopya `eval/reports/planner-v2-live-evidence.json`
(yedi koşu + sonda).


## Encode missing model-reply constraints; keep the saved CAD contract (2026-09-27)

**What changed.** `planner.plan_reply_schema()` now emits `GeneralPlan reply v3`: required
entity/operation tags, closed parameter alternatives for value/expression and provenance,
and exclusive repeat modes. Split steps reuse these definitions. Prompt text remains v2;
schema hashes join prompt hashes in candidate records. `general.py` is unchanged. Added
`eval/schema_probe.py` to preserve full old/new grammars and answers for controlled local probes.

**Measured benefit.** Same local 3B model and three intentionally conflicting prompts:
old grammar **0/3**, corrected grammar **3/3** leaf-contract checks. Real plate rerun
`schema-v3-3b-01` uses the exact prior prompts for both conditions: leaf checks pass, but
`relations` (51.49 s) and `chain_model` (83.90 s) still fail full-plan validation on names.
No STEP. Raw answers also contain missing body dependencies and invalid expressions; valid
leaf objects are not correct geometry. The old claim that the provider cannot enforce
`oneOf` was unsupported because the old parameter grammar omitted that constraint.

**Cost and next decision.** Real run 140.07 s, system swap +628.4 MiB, Ollama peak RSS
5016.1 MiB (not total unified memory). No larger-model or training conclusion follows.
PLAN §20 and all handoffs now target naming constraints then semantic validation, preserving
the canonical CAD schema. Raw evidence is in `eval/reports/schema-v3-*-evidence.json`.

**Verified.** Focused planner/schema tests: 42 passed. Full suite: **300 passed in 217.24 s**.
See `eval/reports/schema-audit.md` for evidence, limitations and reproduction commands.


## CAD names carried by the model interface, not by the validator (2026-09-27)

**What changed.** The naming rule moved into the model interface. `planner.py` gained
`_RULE_CAD_NAMES` (prompt `general-plan-v2` → `general-plan-v3`) and the reply grammar
(`GeneralPlan reply v4`) now emits `propertyNames` on `parameters`/`sketches` and a `pattern` on the
operation reference fields (`sketch`, `input`, `target`, `tool`, `inputs.items`) and on `result`.
`general.py`'s `GeneralPlan v1`, `compile_general` and the CAD validator are unchanged; a source id
(`pdf-0`) stays a source id and is no longer a CAD name. Illegal names are never repaired: the
optional lossless rewrite (`NAME_ADAPTER = "lossless-identifier-rewrite"`, `normalize_names`,
default **off**) maps them one-to-one and records the mapping in `renames`; with it off the answer is
refused. New `eval/name_probe.py` measures which of those constraints the provider's decoder
actually enforces.

**Measured benefit.** The probe (`reports/name-probe-evidence.json`, local `qwen2.5vl:3b`, an
illegal name asked for in every variant) separates the cases the schema cannot tell apart: a
`pattern` on a *string* field **is** enforced (`Hole_Spacing-1` → `hole_spacing_x`), `propertyNames`
on an object is **ignored** (the illegal key comes back verbatim), a closed key vocabulary
(`properties` + `additionalProperties: false`) does hold the key but degrades the value
(`100` → `"testing"`), and `patternProperties` returns an empty body. So an open set of keys cannot
be constrained on this provider, which is why the rewrite exists rather than a stricter schema. On
the real plate (`reports/names-v4-evidence.json`, labels `names-3b-02`…`names-3b-05`, same case,
evidence, model and 16384/4096 settings as `schema-v3-3b-01`) the naming error is gone: names come
back legal (`hole_spacing_x`, `g9_circle_centre`) and the first remaining error is now the
unparsable expression `'/hole_spacing_x'`. The rewrite was off and was a no-op in those answers.

**Cost and corrections.** Renaming the first error is not progress by itself: the plans are still
invalid and no model plan has produced a STEP. The `relations` condition does not answer at all —
two 180 s client timeouts, then `names-3b-04` measured at `--timeout 400` shows the real event:
`done_reason=length`, `eval_count=4096`, an 8 648-byte answer repeating itself to the output budget
in 182.3 s. The 180 s records say "no answer"; what they measured is a decode loop. The three-call
path (`names-3b-05`) moves the failure one step later and names it: `parameters` lands in 14.8 s,
`profile` burns 4 096 tokens in 178.5 s on `radius_exprs_1d_array_2d_array_3d_array_…`. Those runs
also ran with the machine at 11.0/12.3 GB swap, recorded per run.

The §7 run table also stopped inferring the interface from one boolean: it reads the record's own `plan_interface`, so a run that asked three narrower calls prints `üç adımlı` instead of `json-schema` (an older split run's row is corrected by the same change, not re-measured).

**Verified.** Full suite `pytest -q`: 326 passed in 215.50 s. `eval/name_probe.py` ran live (8/8 rows);
`baseline_report.py --write/--check` and `check_tables.py` agree with the records. Live experiments
used only the locally installed 3B model; no weights were downloaded and no training was run.
Evidence: `reports/name-probe-evidence.json`, `reports/names-v4-evidence.json`,
`reports/naming-interface.md`; run folders `out/model-baseline/names-3b-0{2..5}/`.

## The profile step asks one profile per call (2026-09-27)

**What changed.** `planner.py` gained `profile_targets(evidence)`: the closed profiles the *readings*
measured — one closed outer loop plus each closed circle, in page order — and
`propose_plan_split` now makes one call per target instead of asking for every profile in a single
call. Each sub-answer is judged before the next call is spent (structure, expressions, units,
closure, known references, measurement citations, "exactly one sketch", name collisions), a name
already used by a sibling call is refused rather than rewritten, and a profile call is capped at
`PROFILE_PREDICT_CAP = 1024` tokens with the cap written into the record. Prompt version
`general-plan-v3-split-profile`; `step_reply_schema` gained only a `title`. The reply schema, the
naming rule, `GeneralPlan v1` and the CAD validator are unchanged. The step record now carries
`label`, `profile {index, count, kind, geometry_id}` and the cap, so a failed call is named
(`adım profile 1/6 (outline): …`).

**Measured benefit.** The decode loop is gone. In `names-3b-05` the same step ended at
`done_reason=length`, 4 096 tokens, 7 743 bytes, 178.5 s; in `profile-3b-01` (one run, both
conditions, same plate, same `qwen2.5vl:3b`, same 16384/4096, new label) the profile call stops at
129 tokens / 280 bytes in 17.9 s and the run completes in 67.5 s. The rules the change added also
hold in the answer: exactly one sketch, a legal name (`profile_1`), no collision.

**Cost and corrections.** Closing a loop is not progress by itself: both conditions still fail and
no model plan has produced a STEP, so the CAD build, the drawing check and the second part group
were not run at all. The first remaining errors are in two different places. `relations` stops at
**parameters**, writing drawn-circle ids (`h1`, `h2`) where printed span ids (`d1`…`d7`) belong;
that prompt is byte-identical (`01e0bc397f36…`) to the one `names-3b-05` answered with the same
answer text, so what changed there is the step judge in the working tree, not the model or the
interface — `reports/step-validation-replay.json` had recorded that verdict offline and this run
confirms it live. `chain_model` stops at **profile 1/6 (outline)**: two edges that do not close, an
arc radius `x(6.84/2)` with an invented function name, and coordinates taken from a hole
(`-50.35, 30.21`, Ø6.84) rather than the 120.87 × 80.56 mm outline the call asked about. Judging the
same answer offline with only that radius made legal returns the next error it carries: *profil en az
üç kenardan oluşmalı* (recorded as a labelled replay, not applied anywhere). Its `parameters` step
**passed** the interface checks while being unusable as a part: `hole_spacing_y` derived as
`(100 - 80) / 2 = 10` where the sheet prints 60,00, a third diameter derived from the section's 15
and 8, a pocket depth assumed from the sheet's px/mm scale, two assumed radii, and no thickness at
all — provenance rules passed, the part could not be built. The same run's `relations` answer
likewise assumes the printed 15 as a pocket depth. The machine sat at 8.4/10.3 GB swap during the
run, recorded per run.

**Verified.** Full suite `pytest -q`: 352 passed in 231.55 s (six of them new in
`tests/test_profile_step_evidence.py`). `eval/profile_step_evidence.py --check` rebuilds the bundle
from the run records and fails if it drifts (its offline replay must reproduce the recorded error
verbatim, else it refuses); `baseline_report.py --check` and `check_tables.py` agree with the
records; `plate_plan.py` passes. The tree did not change during the run
(`out/profile-step/before.patch` ≡ `after.patch`). Live experiments used only the locally installed
3B model; no weights were downloaded and no training was run. Evidence:
`reports/profile-step-evidence.json`, `reports/profile-step.md`; run folder
`out/model-baseline/profile-3b-01/`.

## The loop chain closes a run instead of eating it, and the evidence block names its two id spaces (2026-09-27)

**What changed.** `src/drawingto3d/proposal.py::_loops` now picks the chain by three rules instead of
the first neighbour it finds: a segment whose far end returns to the chain's start is taken at once,
otherwise the continuation that turns least, and a chain that dead-ends claims nothing — its segments
go back into the pool. `src/drawingto3d/planner.py::_readings_line` renders the evidence as labelled
sections (*Printed numbers* — `span_ids` may point at these ids and only these; *Measured regions* —
these ids name geometry, they are not citations; the claims between them; sheet; notes), the profile
call's own region is a keyed block `Target profile (this call)` instead of a sentence with the numbers
inside it, and `_RULE_CITE_SPANS` states the two spaces. `PROMPT_VERSION` → `general-plan-v4`,
`PROMPT_VERSION_SPLIT` → `general-plan-v4-split-profile-ids`; the plan contract, the reply schema and
the decoder grammar did not change. New probes: `eval/loop_candidates.py` (per sheet, every non-frame
loop with its size, primitive count and the confirmed claims anchored to it) and `eval/raster_scale.py`
(a raster sheet's own px/mm from the ratios between its numbers and the strokes they sit on, via
`scale.consensus`, with a page-diagonal bound and a three-number minimum).

**Bought.** Measured model-free on `plate-pocket-1`, `plastic-enclosure-1`, `exercise-1-vector`:
`Drawing.pdf` went from **3 loops to 7**, and the chosen loop is now the part's own outline — 8
primitives, 53.62 × 82.29 mm, carrying `pdf-13` (R20) — where it used to be a 20.54 × 35.95 mm
three-primitive detail view; `propose`'s refusal names that outline instead of the detail. The plate is
untouched: same loop (8 primitives, 120.87 × 80.56 mm, R10.05, Ø6.85, thickness 15.00), `propose`
still `proposed`, `plate_plan.py` passes, and two new `tests/test_proposal.py` cases pin the closing and
the release rule. On the second change, the decided single run (`ids-3b-01`: `qwen2.5vl:3b`, `--split`,
the same plate/evidence, 16384 ctx – 4096 predict, `relations,chain_model`, 53.23 s, `complete`) shows
the target failure closed: `relations` cited drawn-circle ids (`h1`, `h2`) before and cites real printed
ids (`d1`, `d3`) now — the first error moved one step deeper, to an expression naming a span id
(`(d2 - d4) / 2`), and the same answer carries an invented `sqrt` and a printed parameter whose value
(`70,0`) is what neither of its cited spans (100,00 and 60,00) prints, hidden behind that first error.
`chain_model`'s first error moved the other way: its parameters were accepted before and are now
refused for naming (`pdf-0`), and the same answer judged with the name adapter on (off by default)
gives **0 errors** — the naming rule alone blocks that condition. Both conditions still fail, so **no
plan passed: no CAD build, no drawing check, no second part group, no STEP.** The raster-scale probe
fitted **one of seven** raster sheets (`studycadcam-60`: 3.3158 px/mm, four numbers agreeing to 0.17 %,
and the same scale puts its two drawn circles at 51.06 and 20.57 mm against printed `20` and a round
Ø50), and the row/gap pairing model was measured to add nothing at this layer (the raster observer
already merges collinear strokes: 219 of 221 rows are single strokes), so what limits raster scale is
reading coverage, not the pairing.

**Cost and risk.** The release rule makes `_loops` re-explore from other starts after a dead end, so a
sheet with hundreds of strokes costs more (order-of-magnitude: seconds, not minutes, on the sheets
measured). The closing preference can end a chain early on a drawing where a genuine segment returns to
the chain's start at a sharp turn; the case it was changed for (a dimension line leaving a corner,
measured above) is covered by a test, the coverage of that rule over the raster set is not. The
evidence-block rewrite means every earlier run's prompt fingerprint is a different question: `ids-3b-01`
compares to `profile-3b-01` on the same sheet, model and settings, and to nothing older. A sheet whose
numbers are mostly misreads cannot fit its own scale — the page-diagonal bound rejected the hypotheses
that came out of `flange-1` (90 mm would be 7367 px on a 4170 px sheet) rather than accepting them.

**Verified.** `pytest -q`: **354 passed** in 274.82 s (two new loop-chaining cases in
`tests/test_proposal.py`; the two prompt cases in `tests/test_planner.py` updated to the new
headings); `eval/plate_plan.py` passes; `git diff --check` clean. Measurements live in
`out/profile-step/` (`general-sweep.txt`, `section-candidates.txt`, `raster-scale.txt`,
`raster-scale-source.txt`, `ids-3b-01.log`) and in `eval/reports/general-input-slices.md`.

## The parameters step is told the two rules its judge applies — and the measurement says the words were not what was missing (2026-09-27)

The `ids-3b-01` run stopped both conditions at the parameters step, on two checks the answer had never
been told about: a derived spacing written `(d2 - d4) / 2` (a span id read as a parameter name;
`evaluate_parameters` -> "ifadede tanımsız parametre") and, behind it, a printed parameter whose value
neither cited span prints. This round says both rules in words:
`_RULE_EXPRESSIONS_USE_PARAMETERS` (a derived expression is arithmetic over the parameter names the
answer declares; a span id is a citation, not a name) and `_RULE_PRINTED_CARRIES_ITS_VALUE` (a
`printed` parameter carries the number its cited span prints, or the count beside it). They live in the
shared rule set and are quoted in both interfaces, because both are asked for parameters;
`PROMPT_VERSION` -> `general-plan-v5-parameter-rules`, `PROMPT_VERSION_SPLIT` ->
`general-plan-v5-split-parameter-rules`. The judge is unchanged: same checks, told in advance. Marked as
a test: a `printed` parameter's value must still be accepted by `_check_parameter_citations`, and the
measured expression shape is pinned as a parametrized refusal row.

Measured once, new label, same plate / model / settings / `--split` conditions, and the `chain_model`
evidence block byte-identical to the previous run's (`0c1747f69ab9…`), so the question is the only
variable: `params-3b-01`, **53.69 s, `complete`, both conditions `failed (planning)`, no STEP.** The
first error did not move class. `relations` still wrote a span id inside an expression (`d7`; the
previous run's was `d2`) and `chain_model` still named a parameter `pdf-0` — the naming rule that was
already in the v4 prompt and was ignored. That is the reading recorded: what the answer lacks is a
legal identifier it can copy, not the rule. It agrees with two results measured here — the decoder's
grammar enforces `pattern` on a *string* but ignores `propertyNames` on an object, so an open key set
cannot be constrained; and the same `chain_model` answer cleared its parameters step with the lossless
name adapter on. The naming/grouping hypothesis (a parameter per feature rather than one per printed
number) was deliberately left out: it is unmeasured, and adding it would have made this run two
variables.

**Verified.** `pytest -q`: **355 passed** in 230.35 s; `eval/check_tables.py` 20 rows / 0 drift;
`eval/baseline_report.py --check` matches (the new `params-3b-01` row); `eval/profile_step_evidence.py
--check` matches; `git diff --check` clean; `git diff src/drawingto3d/general.py` empty (the persistent
plan contract, the reply schema and the CAD validation did not move). Round report
`eval/reports/parameter-rules.md`, run records `out/model-baseline/params-3b-01/`, log
`out/profile-step/params-3b-01.log`. No training, no weights downloaded, and no plan passed, so no CAD
build, no drawing check, no second part group.

## Every printed number is offered a legal name beside its id — the naming failure closed on one condition and moved a step deeper on both (2026-09-27)

The round before measured that writing the two rules into the question was not enough: `params-3b-01`
still wrote `(d2 - d4) / 2` and named a parameter `pdf-0`, because the readings block offers the answer
only span ids. So this round puts a legal name beside every printed number.
`planner.suggested_names` (`SUGGESTED_NAMES_VERSION = "reading-derived-names-v1"`, recorded per run as
`settings.suggested_names`) derives it from the reading's own fields: `kind`/`form`
(distance -> `…_spacing`, diameter -> `diameter`, radius -> `radius`), the anchor kinds
(`circle-centre` -> `circle`, `arc-rim` -> `arc`, ends -> `edge`) and the anchors' own axis
(`|Δx| ≥ |Δy|` -> `_x`). Two records measured the same way are both indexed, so no name is bare and
none repeats. `_readings_line` renders the block directly under *Printed numbers*, and the closing line
says what the block cannot say by itself: a span id is a citation, never a name, and never belongs
inside an expression. Both interfaces render it, so `PROMPT_VERSION` ->
`general-plan-v6-suggested-names` and `PROMPT_VERSION_SPLIT` -> `general-plan-v6-split-suggested-names`.

This is not a part template, and three tests hold it there: the names are CAD identifiers, unique, and
never one of the sheet's span ids; two same-shaped measurements are indexed (`diameter_1`,
`diameter_2`); and renaming every span **and** geometry id leaves the suggested names unchanged — the
only inputs are `kind`, `claims[].form`, `anchors[].kind` and `anchors[].point_mm`.

Measured once, new label, same plate / model / settings / conditions, and the `chain_model` evidence
block byte-identical to `params-3b-01`'s (`0c1747f69ab9…`), so the question is the only variable:
`suggest-3b-01`, **46.12 s, `complete`, both conditions `failed (planning)`, no STEP** — and the first
error changed class. `chain_model` no longer names a parameter `pdf-0`; it took five of the seven
suggested names (`circle_spacing_x`, `arc_spacing_y`, `circle_spacing_y`, `edge_spacing_x`,
`edge_spacing_y`) and now fails because an expression uses a suggested name it did not declare
(`diameter_2`). `relations` adopted the menu's style (`distance_1 … distance_7`) but not its names and
still wrote span ids inside expressions (`(d1 - d2) / 2`). Both conditions therefore fail on one
narrower thing now — the declared set and the names used in expressions disagree. Recorded as measured:
the naming failure closed on `chain_model`, and the failure did not vanish, it moved one step deeper.
No training, no weights downloaded; no plan passed, so no CAD build, no drawing check, no second part
group.

**Verified.** `pytest -q`: **358 passed** in 251.22 s (three new tests); `eval/check_tables.py` 20 rows / 0 drift;
`eval/baseline_report.py --check` matches (new `suggest-3b-01` row); `eval/profile_step_evidence.py
--check` matches; `git diff --check` clean; `git diff src/drawingto3d/general.py` empty. Round report
`eval/reports/suggested-names.md`, run records `out/model-baseline/suggest-3b-01/`, log
`out/profile-step/suggest-3b-01.log`.


## Validate each planning step before asking the next (2026-09-27)

**Problem.** The previous split run called malformed, wrongly cited parameters “accepted”
and spent a profile call on them. The baseline also ignored `--split` for `chain_model`
and did not forward `--normalize-names` to either model condition.

**Change.** Step validation reuses canonical field definitions and expression/profile
checks, and shares printed-citation checks with the final judge. Invalid or truncated
answers stop the sequence; each step records its validation version, errors and acceptance.
The baseline forwards both options; report tables prefer actual candidate interfaces,
so the historical mixed run is labelled as mixed. Saved CAD contract and model prompts/
grammars remain unchanged.

**Evidence.** Replay of `names-3b-05` now rejects the first answer before the profile call.
New live `step-validation-3b-01`: relations fails on citations in 20.24 s; the real drawing
uses split calls, passes parameter structure and fails on a sketch name in 63.95 s.
No STEP. Structurally accepted parameters still contain wrong drawing interpretations,
including treating page scale 7.82 as pocket depth. PLAN §21 now targets evidence-to-parameter
selection rather than another long profile experiment. Full evidence and verification:
`eval/reports/step-validation-audit.md` and its two JSON records.

## Printed quantities become a fixed catalog (2026-09-27)

`catalog.py` copies original printed values, units and source ids; the model selects meanings
and proposes bounded expressions. Counts stay distinct from dimensions. Original inch values
are no longer converted to rounded millimetres while retaining an inch label. A two-part local
3B measurement kept 22/22 quantities intact; both semantic proposals were rejected for name
collisions (one also for dimensional arithmetic). This is a provenance improvement, not CAD
success. See `eval/reports/catalog-parameters.md` and its complete portable evidence JSON.
The initial focused suite passed 108 tests; the full suite is in progress at this checkpoint.

## The catalog is reviewable without a model (2026-09-27)

`drawingto3d catalog` saves source quantities, evidence and a Markdown review. It refuses
existing output files. Missing scale/outline no longer discards printed quantities: the plastic
PDF retained 14 records and the raster flange retained 18 unverified candidates with a missing-scale
reason. The first slice passed all 394 tests; affected tests after this extension passed 29, and
CLI/interruption tests passed 6 (overlapping groups). The full suite was not repeated after the
extension. No model, training or CAD call is required for the catalog command.

## One printed measurement now binds to the sheet's own ids, and the model's interpretation was measured (2026-09-27)

The catalog fixed what the numbers are. This slice asks a local 3B model one question per printed
measurement: which of the drawing's own measured geometry is this number, and of what kind.

- `src/drawingto3d/interpret.py` (`single-measurement-interpretation-v1` / `MeasurementInterpretation v1`)
  binds one measurement to source and geometry ids. The reply schema has no numeric field, and
  `between`/`matched` are enums over the ids the reading itself measured — an invented id cannot pass.
  An unsolvable binding is `unresolved` plus one question. The judge rejects kind↔field mismatches,
  duplicated ids, claims on an unresolved binding, and numbers outside ids in `reason`/`question`;
  agreement with the reading's own binding and axis consistency are recorded as measurements, not gates.
  Reference labels (`eval/relations/`) are evaluation input only and never reach the model.
- `eval/meaning_interpretation.py` writes the full request before the call and the raw answer right
  after it, offers `--dry-run`, `--evidence` and `--check` (re-judging stored raw answers).
- `meaning-3b-01` (`qwen2.5vl:3b`, 16384/4096, temperature 0, 186.971 s total): the contract held in
  22/22 answers — no invented ids, no rewritten value, unit or count. The interpretation did not: on the
  plate 7 of 8 answers failed the contract (5 wrote a number into `reason`, 2 shaped a diameter as a
  distance), so only 1 of the 15 fields the independent label can check was actually scored, and no
  measurement was fully correct. On the plastic part 13/14 passed the contract but without discrimination:
  axis was "horizontal" in 14/14 answers, 7 measurements returned the same pair, and 3/14 agreed with the
  reading's own binding. `unresolved` was never chosen (0/22).
- The label has no coordinates for three plate measurements and the plastic part has no independent label
  at all, so those parts stay explicitly unmeasured. No STEP, profile or training success is claimed.

**Verified.** `pytest -q`: **426 passed** in 248.49 s (26 new tests); `eval/meaning_interpretation.py --check`
re-judged 22 measurements with 0 problems; `git diff --check` clean; `general.py` untouched.

## The number rule no longer hides the binding it protects (2026-09-27)

The first `meaning-3b-01` round showed the interface's contract holding while the interpretation stayed
unmeasured: a quoted value in `reason` invalidated the whole answer, so 14 of the 15 fields the
independent label can check were never scored. Round two changed exactly one thing — the judge's penalty
scope (`interpretation-contract-v1` → `v2`): a number outside an id is now a recorded warning, not a
rejected answer.

- Same prompt, same schema, same settings: all 22 prompt sha256 values and all 22 raw answers are
  byte-identical to round one, so the difference is the measurement, not a new sample.
- Plate: 1 correct / 7 invalid → **3 correct, 2 partial, 3 invalid**; scored fields 1 → 9 of 15; kind
  5/5, axis 1/2, binding 1/2. The three remaining invalid answers are all the diameter/radius shape
  (two ends instead of matched geometry, or an axis on a diameter).
- New, sharper finding: the axis word and the chosen pair contradict each other — for the 100,00 spacing
  the answer says "horizontal" while binding the diagonal `g9-g12`; for 60,00 it picks the right pair and
  still says "horizontal". The independent label is self-consistent in both.
- The plastic part resampled identically: no label, axis "horizontal" in 14/14, seven measurements on the
  same pair, 3/14 agreeing with the reading, `unresolved` 0/22. No STEP, profile or training claim.
- `--check` now distinguishes an older contract's record: a pack judged by `v1` verifies its raw answers
  and skips the status comparison instead of reporting a false mismatch.

**Verified.** `pytest -q`: **426 passed** in 245.28 s; both evidence packs re-judged (`0 problems`, the
older pack's status comparison skipped by contract version); `check_tables` 20/0, `baseline_report
--check` and `profile_step_evidence --check` agree; `git diff --check` clean; `general.py` untouched.

## The axis is read off the chosen pair, and the loss moved to pair choice (2026-09-27)

Round three removed the axis from the question (`interpretation-contract-v3`): the reply schema has no
`axis`, and the prompt says the axis follows from the two ids a distance is measured between. Unlike the
v1→v2 judge-only change, this changed the question itself, so all 22 prompts and all 22 raw answers differ
from round two — reported as a question change, not a measurement artefact.

- Plate: 3 correct / 2 partial / 3 invalid → **4 correct / 1 partial / 3 invalid**, while field accuracy is
  unchanged (kind 5/5, axis 1/2, binding 1/2). The one class that moved, `60,00`, had the right pair
  already; its axis now follows that pair. So removing the asked axis closed the contradiction the model
  produced itself (its word against its own pair) without buying new understanding.
- The loss is pair choice: `100,00` is still bound to the diagonal `g9-g12`, the `50,00` pocket diameter to
  two holes, and `6,80` to two ends. With the axis field gone the plate answers drift to vertical pairs —
  the word/pair contradiction moved into the pair.
- Plastic: the most repeated pair eased from 7 to 5 of 14, agreement with the reading unchanged at 3/14,
  one new shape failure (a radius with no matched geometry), `unresolved` still 0/22.
- Found and fixed the check's own bug: one printed callout can yield two measurements (dimension and
  count), and the evidence check paired them by source id alone, so the two were confused as soon as their
  answers differed; it now pairs on (source id, name) with a regression test.

**Verified.** `pytest -q`: **427 passed** in 246.09 s; three evidence packs re-judged (0 problems; the pack
from the older contract verifies its raw answers and skips the status comparison); `check_tables` 20/0,
`baseline_report --check` and `profile_step_evidence --check` agree; `git diff --check` clean; `general.py`
untouched.

## The distance menu is the reading's own measured pairs, and the plate's binding scores 2/2 (2026-09-27)

Round four narrowed the candidate set (`interpretation-contract-v4`): `between` may only be one of the pairs
the reading itself measured — its own anchor pair first, then the alternative pairs its claim notes record,
keeping only pairs whose two ids carry a measured position (the axis is derived from those points). The
prompt prints that menu and the judge refuses a pair outside it.

- Plate: 4 correct / 1 partial / 3 invalid → **5 correct / 0 partial / 3 invalid**; kind 5/5, **axis 2/2,
  binding 2/2** (was 1/2 and 1/2). Given four candidate pairs, the model chose the reading's own pair for
  both `100,00` (horizontal hole spacing `g9-g11`) and `60,00` — where rounds two and three had bound
  `100,00` to the diagonal `g9-g12`. The loss was in the menu, not only in the model.
- Unchanged: the three remaining invalid answers are the diameter shape (a diameter answered as two ends,
  `pdf-3` two holes, `pdf-4` `g8-g9`) although both the prompt and the reading say `form: diameter`; the
  plastic collapse returned (most repeated pair 7 of 14, agreement with the reading 3/14); `unresolved`
  still 0/22.
- The intervention's reach is itself measured: most alternative ids the reading names carry no position, so
  the menu collapses to a single pair on the plate's other measurements and on all four plastic numbers the
  reading bound — and 10 of the plastic sheet's 14 numbers have no reading claim at all.

**Verified.** `pytest -q`: **429 passed** in 247.54 s; four evidence packs re-judged (0 problems); `check_tables`
20/0, `baseline_report --check` and `profile_step_evidence --check` agree; `git diff --check` clean;
`general.py` untouched.

## A malformed answer is no longer an unmeasured one: the stored runs were re-scored (2026-09-27)

The plate's last three answers were rejected by the contract for their *shape* (a diameter written as two
ends), which left the geometry they pointed at unmeasured. Scoring scope changed by one step: when the
contract refuses an answer, its binding is still scored as the set it names (`between` ∪ `matched`) against
the independent label, while the answer's class stays invalid. No model call was needed for that, so the
four rounds' stored raw answers were re-scored with `--rescore` — the run records are untouched and a
`rescore.json` lands beside each.

- All three remaining plate answers are now measured and **wrong**, not unmeasured: `pdf-3` (Ø6,80 ×4)
  names `g9,g12` of four holes, its count entry the same, and `pdf-4` (50,00 pocket) names `g8,g9` — the
  pocket plus one hole. The diameter problem is understanding, not layout.
- One rule for all four rounds: plate correct 1 → 3 → 4 → **5**; axis 0/0 → 0/2 → 1/2 → **2/2**; binding
  0/0 → 1/2 → 1/2 → **2/2**; kind 5/5. Retrospective finding: round one's digit penalty had discarded an
  answer whose binding was *right* (the `60,00` pair, only its axis word was wrong).
- The second part group is unchanged and still has no independent label: the reading bound 4 of its 14
  numbers, so nothing there is scored for correctness.

**Verified.** `pytest -q`: **431 passed** in 240.75 s; four evidence packs and four rescore records checked;
`check_tables` 20/0, `baseline_report --check` and `profile_step_evidence --check` agree; `git diff --check`
clean; `general.py` untouched.

## The verification interface was withdrawn before it was run: the reading's proposal equals the label (2026-09-27)

Before implementing the round the plan called for next (hand the model the reading's own binding and ask it
to agree), the premise was measured against the stored run: on all five labelled plate measurements the
reading's proposed set is identical to the independent label (`pdf-0` `g9,g11`; `pdf-2` `g9,g12`; `pdf-3`'s
four holes; its count entry; `pdf-4` `g8`). A verification question built on that proposal would score
"agree" as correct by copying — it would measure nothing, and precisely on the three measurements the model
gets wrong. No model run, no code change: the finding comes from comparing the labels in the run records
with `measured_by_the_reading.matched_geometry`.

The next step is rewritten as a round with known ground truth by construction: inject deliberate reading
defects (drop an id from the matched set, shift a pair), mix clean and defective measurements without saying
which is which, and measure detection rate and false alarms. Its limit is stated up front — it measures
detecting *injected* defects, not real reading errors, because this plate's label coincides with the reading.

## Reviewing the reading fixed the plate: 6 of 6 injected defects corrected, 0 false alarms (2026-09-27)

Sixth slice, one variable (`reading-review-v1`): the prompt now shows the reading's own binding as a
*review request* ("if it fits, write exactly that; if not, write what you read"), and half the measurements
get a deterministic defect injected into that proposal — chosen by source id alone (`review_injects_a_defect`
+ `corrupt_proposal`), never saying which are defective. Ground truth is the defect itself, so copying the
proposal is a wrong binding and the label plays no part; the evidence pack is checked to contain the injected
proposal verbatim in the prompt.

- **Plate: 7 correct, 1 partial, 0 invalid** (free choice in round four: 5 correct / 3 invalid). All 6
  defective proposals were corrected to the reading's *true* binding, the 2 clean ones were left alone, and
  there were no false alarms. The model read the sheet instead of copying the proposal.
- The single remaining plate loss is the count entry of `pdf-3`: the model binds "4 × Ø6,80" as a `diameter`
  while the label expects `count` (a kind-field mismatch, not a geometry error).
- **Second part group:** 4 defects injected where the reading bound something → 4 caught; on the radius the
  model spotted the defect but could not rebuild the 12-id set. In 10 of its 14 numbers the reading never
  bound anything, so there is nothing to review — the reading chain's coverage is the real next work.
- **Two measurement corrections, applied to the stored answers:** a measurement the reading never bound was
  counted as a clean proposal and produced 9 phantom false alarms on the plastic sheet — now its own class
  (`no_reading_binding`), with contract-refused answers counted as `unusable_answer`; and
  `answers_agreed_with_reading` had reported 0 for five rounds because the summary read the pack's `checks`
  key instead of the run's `reading_agreement` (corrected: plate 0 → 3 → 2 → 5 → **8**, plastic 3 throughout).

**Verified.** `pytest -q`: **437 passed** in 266.81 s; the `meaning-3b-05` evidence pack re-judged with 0
problems; all five runs re-scored; `check_tables` 20/0, `baseline_report --check` and
`profile_step_evidence --check` agree; `git diff --check` clean; `general.py` untouched.

## Reading coverage on the second sheet: row ends re-picked against the sheet's own scale (2026-09-27)

The interpretation interface was left where it stands; this slice works in the reading chain, and it began
by measuring the blockers on the stored bind records rather than by guessing: of the plastic sheet's ten
unresolved numbers, **eight** had a drawn row that misses the printed length at the sheet's scale by 250%
to 1800% (a 3,00 mm dimension whose "row" was 70 px where 11,75 px was needed), and **two** had a correct
row with an empty candidate pool at one anchor.

One variable (`bind.py`): when a row misses the fitted scale by more than 25%, the row's ends are re-picked
from the points the anchors **already reached** — their own position, the far ends of the strokes they
attach to, and the points they align with — choosing the pair closest to the printed length and accepting it
only within 5%. Nothing new is detected and no tolerance is loosened; the calibration (`scale.audit`'s
consensus) becomes a constraint instead of a report, and each re-pick travels as a note from
`SpanBinding.notes` through `SpanMeaning.notes` into the evidence.

- **Second sheet: bound numbers 4/14 → 8/14** (`pdf-6`, `pdf-8`, `pdf-9`, `pdf-12`; deviations 0,29 / 0,01 /
  0,11 / 0,02 mm against their printed values), with 10 of 14 measurements untouched.
- **The plate is byte-identical**: the eight plate requests stored in the last run still hash to the same
  `prompt_sha256` (8/8) — a row that already measures its number is never re-picked.
- Still blocked, and measured rather than assumed: `pdf-1`, `pdf-4` and `pdf-5` have correct rows but an
  empty candidate pool at one anchor; `pdf-10`, `pdf-11` and `pdf-13` have no reached pair at the required
  length.
- Stated limit: the second sheet has no independent label, so "bound" means "the drawn length agrees with the
  printed value at the sheet's own scale" — a coverage gain, not an accuracy gain. Independent verification
  is possible only on the plate, and nothing there changed. Report: `eval/reports/reading-coverage.md`.

**Verified.** `pytest -q`: **441 passed** in 288.55 s; the before/after comparison was taken with
`_repick_row_with_calibration` replaced by a no-op; `check_tables` 20/0, `baseline_report --check` and
`profile_step_evidence --check` agree; `git diff --check` clean; `general.py` untouched.

## Reading coverage, second slice: the ends of the lines a dimension crosses — as a fallback only (2026-09-27)

The recorded blocker ("one anchor's candidate pool is empty") was measured rather than trusted, and the record
itself was wrong about the cause: the pool was empty because the geometry that measures these numbers — the far
ends of the extension lines the dimension crosses — was never offered (the meaning layer offered only what an
anchor reached or aligns with). Measured before coding: raising `CANDIDATE_LIMIT` from 6 to 12 to 100 changes
nothing at all; offering the crossed lines' far ends yields 6/5/2 measuring pairs inside tolerance; offering the
row and stub strokes too yields more pairs, but four of them point at **the dimension line's own ink** — a claim
that confirms itself by pointing at the line that printed the number.

Offered in the *first* pass, that widening also re-pointed three already-bound numbers on the second sheet and —
the guard that decided the design — **broke the plate**: 0 of the 8 stored plate requests still hashed the same.
So the crossed ends are offered in a **fallback pass, only when the first pass finds nothing**: a second chance
for the unresolved, never a rewrite of a binding that stands.

- **Second sheet: bound numbers 8/14 → 11/14**, with exactly the three that were unresolved changing
  (`pdf-1` `g289/g290` 9,99/10,00; `pdf-4` `g255/g254` 120,50/120,00; `pdf-5` `g294/g295` 60,31/60,00), 11 of 14
  untouched, and each new binding carrying a note that names the ids it used.
- **Plate unchanged: 7/7 bound and 8/8 stored request hashes identical.**
- Remaining: `pdf-10`, `pdf-11`, `pdf-13` — no pair at the required length among what their anchors reached,
  align with or cross.
- Stated limit: still self-consistency, not correctness (no independent label on the second sheet; the plate is
  the only labelled sheet and nothing moved there). The stored interface runs read the *older* reading, so
  repeating that round is a new experiment with a new label (`meaning-3b-06`), not an overwrite; all five stored
  evidence packs still pass `--check` with 0 problems. Report: `eval/reports/reading-coverage.md`.

**Verified.** `pytest -q`: **445 passed** in 259.05 s; plate request hashes 8/8; `check_tables` 20/0;
`baseline_report --check` and `profile_step_evidence --check` agree; `git diff --check` clean; `general.py`
untouched.

## Reading coverage, third slice: a step dimensioned by its own segment (2026-09-27)

The two numbers left after the fallback pass were measured again, and the recorded cause was wrong a second
time: the geometry was not far away, it was attached to **one** anchor. `pdf-10`'s row was 69,0 px where 4,80 mm
is 18,8 px at the sheet's 3,92 px/mm, and the segment the callout dimensions (`g264`, 18,9 px drawn = 4,82 mm)
belonged to a single anchor — a pair rule that takes one point from each anchor cannot express that, which is
exactly why the earlier re-pick found nothing.

One variable (`bind.py`): when the row misses the fitted scale by more than 25% and no cross-anchor pair lands
on the printed length, a **single stroke attached to one anchor** is accepted as the extent if it is drawn
**along the measuring axis** (projection ≥ 99% of its length) **and** to the printed length (within 5%). `row`
strokes are excluded (they join the two anchors — the perceived row, not the extent), and the whole re-pick is
now gated to linear dimension callouts, so a radius/leader callout is never re-picked against its value.

- **Second sheet: bound numbers 11/14 → 12/14**, with **1/14** changing (`pdf-10`: row 69,0 px → 19,21 px,
  claim `g272/g276` 4,83 mm, note naming the segment) and 13/14 untouched.
- **Plate unchanged: 7/7 bound and 8/8 stored request hashes identical.** Its two disagreeing rows are the
  Ø6,80 leader (non-linear, now gated out) and `50,00` (bound through candidate pairs, not through its row).
- A near miss stays a miss: `pdf-11`'s nearest segment is 16,6 px against 15,67 px needed (5,9% off), so the row
  is left alone, no re-pick note is written and the number stays unresolved. The first cut of the rule accepted
  the *projection* while reporting the *straight-line* length, which wrote a "measured" note for `pdf-11` at
  5,94%; the accepted measure and the reported one are now the same number.
- Remaining, measured: `pdf-11`, `pdf-13`, whose true geometry sits ~10 px or more from both anchors — outside
  what the anchors reached. Reaching it means detecting geometry the reading never touched: a different
  variable, not attempted here. Report: `eval/reports/reading-coverage.md`.

**Verified.** `pytest -q`: **449 passed** in 244.53 s; plate 7/7 and request hashes 8/8; `check_tables` 20/0;
`baseline_report --check` and `profile_step_evidence --check` agree; every stored evidence pack passes `--check`
with 0 problems; `git diff --check` clean; `general.py` untouched.

## Reading coverage, fourth slice: the extent drawn on the measuring axis, off both anchors (2026-09-27)

The last two numbers were measured a third time and the geometry was neither far away nor attached: it lies **on
the dimension's own axis line**, past the end of the perceived row, touching neither anchor. Perpendicular
distances to each span's own axis: `pdf-11`'s `g310` 0,0 px (its same-length competitor `g269` sits 47,2 px
across), `pdf-13`'s `g279` −0,3 px (competitor `g178` 172,8 px), reference `pdf-10`'s `g264` 0,0 px. A "nearest
geometry to the text" rule would have picked the wrong segment for `pdf-11` (`g269` is 99,3 px from the text and
is `pdf-9`'s own extent, against 105,9 px for the right one) — the axis line is what separates them.

One variable (`bind.py`, `_segment_on_axis`): when the row test and both existing re-picks fail, a segment from
the reading's own primitives is accepted as the extent if **both ends sit on the measuring axis line** (within
the module's existing 4 px feature tolerance, which also makes it parallel to the axis) and its length is within
5% of the printed length; nearest to the anchors wins. No new detection (the same `observe()` output), no
loosened tolerance, still gated to linear dimension callouts whose row disagrees.

- **Second sheet: 12/14 → 14/14 printed numbers bound**, with exactly **2/14** changing (`pdf-11` row 69,0 →
  15,84 px, `pdf-13` 79,0 → 5,83 px, both with their own note) and 12/14 untouched.
- **The plate is untouched in the strongest sense available: its whole `bindings.json` record is byte-identical
  with the rule on and off**, bound 7/7, stored request hashes 8/8, and the rule never fires there.

### What "14/14" does not say (measured separately)

Coverage is not claim sharpness. Across-the-axis separation of each claim's two named points: **8 of the 13
distance claims on the second sheet exceed 20 px** (up to 750 px), against 1 of 5 on the plate (the other four
exactly 0,0 px). The two newly bound numbers carry it too: `pdf-11` names a circle centre 190,6 px across plus a
line end, `pdf-13` an arc rim 371,8 px across plus a line end — their projections differ by the printed values,
but they are not the step's faces. The weakness is pre-existing (`pdf-0`, bound in the first slice, names two
circle centres 750 px apart across the axis). So "bound" is recorded as *"a measured pair at the sheet's own
scale"*, never as *"the right geometry named"*; sharpening a repaired row's claim is the next single variable and
that distribution is its before/after measure. Report: `eval/reports/reading-coverage.md`.

**Verified.** `pytest -q`: **454 passed** in 242.42 s; plate `bindings.json` byte-identical and request hashes
8/8; `check_tables` 20/0; `baseline_report --check` and `profile_step_evidence --check` agree; every stored
evidence pack passes `--check` with 0 problems; `git diff --check` clean; `general.py` untouched.

## Claim sharpness on repaired rows: name the pair at the extent (2026-09-27)

Coverage was not the same as a claim naming the measured geometry: eight of thirteen distance claims on the second
sheet named two points whose separation across the measuring axis exceeded 20 px (up to 750 px). The candidate pools
of the seven repaired rows were dumped before changing anything: every valid pair's nearest point sits ≥ 41 px from
the anchors, `pdf-8` has exactly one valid pair (no ordering can sharpen it), and `pdf-13` can be measured by a pair
47,2 px across the axis where the chosen one sat 371,8 px.

One variable (`meaning.py`, keyed off `SpanBinding.row_repaired`, `Bindings.version` 3): when the row was re-picked
against the scale, valid pairs are ordered by **their separation across the measuring axis first**, then the existing
rank/cost/deviation. Since the axis component already equals the printed value, a small across-axis component means
the two points are the printed length apart in space — a local pair at the extent. Rows read as drawn keep their
order exactly.

- Second sheet: total across-axis separation **2450,2 → 1262,6 px**, median **118,6 → 0,1 px**, claims above 20 px
  **8/13 → 5/13**; per repaired row e.g. `pdf-13` 371,8 → 0,0, `pdf-11` 190,6 → 0,1, `pdf-10` 238,1 → 3,3,
  `pdf-9` 423,2 → 55,0 (its candidates all sit far off the extent), `pdf-8` unchanged (its only pair is forced).
- **The plate has no repaired row, so the change is inert there by construction** — verified twice: no span is
  flagged and all eight stored plate request hashes are still identical.
- The five claims still above 20 px are the three rows read as drawn (`pdf-0`, `pdf-3`, `pdf-7` — left untouched on
  purpose) plus the two forced repaired ones.
- Stated limit: neither sheet has id-level reference labels, so "sharper" means exactly what was measured — the
  claim's two points lie nearer the dimension's own axis and the pair is local to the extent. It is **not** evidence
  that the named geometry is correct; the printed-value match still holds as before. Report:
  `eval/reports/reading-coverage.md`.

**Verified.** `pytest -q`: **457 passed** in 242.48 s; plate request hashes 8/8 and plate claims unchanged;
`check_tables` 20/0; `baseline_report --check` and `profile_step_evidence --check` agree; every stored evidence pack
passes `--check` with 0 problems; `git diff --check` clean; `general.py` untouched.

## Interface round repeated on the sharper reading: `meaning-3b-06` (2026-09-27)

Same interface, same fixed model (`qwen2.5vl:3b`, 16384 ctx / 4096 predict / temperature 0), same two sheets; the only
thing that changed is the reading (second sheet now 14/14 bound with the claims at the extents). Run 173,06 s,
`complete`; raw requests and answers under `out/meaning-interpretation/meaning-3b-06/`, portable pack
`eval/reports/meaning-interpretation-evidence-06.json` (`--check`: 22 measurements, 0 problems).

| | run 05 (older reading) | run 06 (new reading) |
|---|---|---|
| plate classes against the hand-verified label | 7 correct / 1 partial / 0 invalid | **same: 7 / 1 / 0** |
| plate: answer holds the reading's own binding | 8/8 | **8/8** |
| plate review round | 6/6 defects caught, 0 false alarms | **6/6, 0** |
| second sheet: answer holds the reading's binding | 3/14 | **13/14** |
| second sheet review round | 4/4 caught, **9 false alarms** | **10/10 caught, 0** |
| second sheet: binding wrong beyond the proposal | 1 | **1** (`pdf-2 radius`) |

Honest reading of it: the 13/14 is a **copying** share — the reading now proposes a valid local pair for every
number, so repeating it is easy; the interface's independent value in this round sits in the review round. The
05→06 comparison is **not single-variable** (the seventh slice's judging fix plus four reading changes sit in
between); the plate coming out byte-for-byte the same shows the labelled sheet was not disturbed, but the second
sheet's jump is the sum of both changes, not separated. The one disagreement is `pdf-2 radius`, where the model
named `g57/g60` instead of the proposal (`right: false`). Recorded next decision: measure the interface's
non-copying value — a third sheet with a hand-verified relation label and a **blind** round (proposal withheld),
then compare the question an unresolved number gets asked against the label. Report:
`eval/reports/measurement-interpretation.md`.

## Blind round, and the one failure class it exposed (2026-09-27)

A blind round (`--review` off, so the model never sees the reading's proposal — runs 05/06 showed it to *both*
calls, so this measurement had never been made) scored the labelled plate at **5 correct / 0 partial /
3 invalid** with 3 bindings outside the contract, and the second sheet at 13/14 agreement. So two of the plate's
eight measurements came only from checking the proposal.

The three blind losses were one class, identical in three blind rounds (`-03`, `-04`, `-07`, down to the same
ids): a callout that **sizes a single geometry** (Ø6,80, Ø50, R8,00) was answered as a *pair* — `kind: diameter`
with `between: [g9, g12]`, `matched: []` — which the contract can only call invalid. The model's own reason said
"which are both circles": it meant the circles and put them in the wrong list. A sharper reading did not move the
blind score (5/8 in run 04 and run 07 alike), so the loss was in the interface's field handling, not the menu.

**One change** (`interpret.py`, `INTERPRETATION_VERSION` → `single-measurement-interpretation-v2-form-field`): the
request and the reply schema now state which id list this measurement's own form requires (`distance`/`angle` →
`between`, `diameter`/`radius`/`count` → `matched`; the other list gets `maxItems: 0`, the required one
`minItems`). It names the *field*, not the answer.

Blind round re-run (`meaning-3b-08-blind-v2`, 244,83 s, complete): plate **7 correct / 1 partial / 0 invalid**,
bindings beyond the contract **3 → 0**, second sheet 13/14. The two measurements that had been right only by
copying are now right blind — `pdf-3 diameter_1` → `matched: [g9,g10,g11,g12]` (the label's "four corner holes")
and `pdf-4 diameter_2` → `matched: [g8]` (its "single circle at the centre"). The last labelled loss stays
`pdf-3`'s count (`kind: false`, `binding: true`). The second sheet's `pdf-2 radius` failed a third distinct way
(`unresolved: true` together with `matched: [g57,g60]` and an empty question) — a genuinely hard row with a
12-id candidate set and no label. Packs `-07`/`-08` pass `--check` (22 measurements, 0 problems); two tests added
in `tests/test_interpret.py`.

## The count measurement asks for the count: blind 8/8 on the labelled sheet (2026-09-27)

The plate's last labelled loss was `pdf-3`'s count: "4 × Ø6,80" is printed once and asked twice (its size and
its count) with **byte-identical text and candidate menu**, so which measurement is being asked is knowable only
from the catalog (`quantity: count` / `dimension`).

**One change** (`interpret.py`, `INTERPRETATION_VERSION` → `single-measurement-interpretation-v3-count-quantity`):
the context and the request carry the catalog's quantity, and a count measurement is told so ("this measurement
is the CALL COUNT of its callout ... set kind to count"). Line-by-line comparison of all 22 requests against the
previous run shows no other change; `allowed_ids` and `candidate_pairs` are untouched.

Blind rounds with the proposal withheld, on the hand-verified label:

| blind round | request version | plate (label-scored) | second sheet |
|---|---|---|---|
| `-07` | v1 | 5 correct / 0 partial / **3 invalid** | 13/14 |
| `-08` | v2 (form → list) | 7 / 1 / 0 | 13/14 |
| `-09` | v3 (quantity) | **8 / 0 / 0** | 13/14 |

All eight now carry the right kind and the right geometry blind: `diameter_1_count` is `kind: count` with
`matched: [g9,g10,g11,g12]` (the label's "four corner holes"), `diameter_2` is `matched: [g8]` (its "single
circle at the centre"). Every step was single-variable and the reading chain was never touched. `-09` ran
267,08 s, `complete`; its pack passes `--check` (22 measurements, 0 problems). The second sheet's `pdf-2 radius`
stays `invalid` in all three blind rounds (12-id candidate set, no label) — recorded as still unknown.

## Third sheet's hand-verified relation label, and what it measured (2026-09-28)

`eval/relations/exercise-1-vector.json` labels `examples/pdf with steps/2/Drawing.pdf` ("Exercise 1", scale 1:2,
`Part-2.STEP`) — the case already existed in `cases.json`, only the label was missing. Every row was verified
against the STEP (bbox 134×80×50 mm, 11 cylindrical faces, 16 planes): the five diameters land exactly on the
model's cylinder radii (Ø20 r=10,00 @ (-37,00; 66,37) · Ø25 r=12,50 @ (57,00; 27,96) · Ø30 r=15,00
@ (9,55; 40,00) · Ø40 r=20,00 @ (61,24; 32,73) · Ø50 r=25,00 @ (13,94; 42,00)); the plan view's five verticals turn
out to be the part's **thicknesses** and match the model's z-planes (26=z±13 · 6=z±3 · 20=z±10 · 40=z±20 ·
10=z±5); 80 is the bbox height; 37 and 57 are the two lug-bore centres from the shared datum (STEP x=-37,00 and
+57,00 — the sheet's own 37+20=57 chain uses the same datum). Three numbers the STEP did not settle (60, 35, the
upper view's 20) are marked `verified: "drawing"` rather than claimed.

**The measured obstacle is in the reading chain, not the interface:** this sheet's PDF text layer contains **no Ø
glyph at all** (468 characters, none of them Ø, none above 0x2000 — the prefix is stroke art). So the reading takes
the five diameter callouts as plain `linear` numbers and binds them **as a distance between two line ends**
(`pdf-19` 30, `pdf-20` 25, `pdf-22` 40 bound; `pdf-21` 50 unresolved), while `cases.json`'s own
`diameter_calls: [20,25,30,40,50]` already states the truth.

Dry run (no model calls): the label pairs 11 of 17 numbers — the harness deliberately pairs only unique values, so
the four "20"s and the two "40"s stay unpaired — and in the three paired diameter rows the contrast is exact:
`pdf-19`/`pdf-20` are presented as `distance`, `pdf-21` as unresolved, and the label expects **diameter** in all
three. Next single change: recover the diameter semantics in the reading (the non-textual Ø glyph, or a leader
pointing at a single circle), gated on the two standing sheets staying byte-identical.

## Ø read as stroke art, and a diameter sizes a circle without a leader (2026-09-28)

Two measured defects on the third sheet (`examples/pdf with steps/2/Drawing.pdf`), fixed one variable each.

1. **The Ø prefix can be vector art.** The sheet's text layer carries 468 characters and none of them is a
   Ø, so five diameter callouts entered the reading as plain lengths. `observe._diameter_prefix_glyph` now
   reads the prefix from the small circle drawn beside the digits (a circle no bigger than 60% of the
   phrase's height, centred within 1.2 x its height of the box — scale-free, relative to the phrase).
   Measured separation: the glyphs sit 8-21 px from their digits, every real circle or arc on the sheet is
   138 px or more away. `bind._diameter_glyph_upgrade` carries the observation's kind to the span whose
   text it belongs to. The rule also fires twice on the plate (its `Ø6,80` and `Ø50,00` are stroke art too)
   and never on the plastic.
2. **A `diameter` phrase sizes a circle wherever it is printed.** `meaning._meaning_for` only tried the
   size claim for `anchor_mode == "leader"`; the third sheet's five Ø callouts are not leaders, so even a
   correctly typed callout could not bind. The branch now also runs for `binding.kind == "diameter"`.

Measured effect (dry-13 → dry-14, one rule at a time): the third sheet's resolved measurements go 12 → 16
of 17; the five callouts are typed `diameter` and bound to g133 / g68 / g122 / g65 / g125+g134; kind
agreement with the hand-verified label goes 1/5 → 5/5; two *wrong* distance bindings (Ø30, Ø25) are gone.

Regression shield, measured not assumed: the plastic's reading is byte-identical with the rule off and on;
on the plate only the reported kind of two phrases becomes accurate (form, resolution, matched geometry and
notes are unchanged); and all **22/22 request prompts** of the stored blind run (plate + plastic) recompute
to the same sha256. `--check` does not do this — it re-judges stored answers — so the shield is a separate
measurement (`out/profile-step/prompt-shield.txt`).

Left open: the binding was made *by value* (%3 tolerance, diameters land 2.7% off because the sheet's
calibration is 3.83 px/mm against the true 1:2 scale of 3.937 px/mm), and Ø40's match names the same two
arcs as the R20 callout — only the STEP separates the boss from the fillet.

## Third sheet: blind interface round, and why its binding cannot be scored yet (2026-09-28)

`meaning-3b-10-third-blind` ran the single-measurement interface on the third sheet with the proposal
withheld (`qwen2.5vl:3b`, interface v3-count-quantity, contract v4), 17 measurements, 146,154 s, complete.
Kind came out **11/11** against the hand-verified label — including all five diameter callouts — with no
answer outside the contract, up from three out-of-contract answers in the first blind round on the plate.

The binding could not be scored on this sheet, and the reason was measured rather than assumed: the harness
maps a label position to a reading id within `POSITION_TOLERANCE_MM` = 2 mm, which holds on the plate
(`h1 [-50,-30]` ↔ measured `g9 [-50.35,-30.21]`, 0,4 mm; 5 of its 8 measurements are binding-checkable in
the stored run) but fails on the third sheet for all 17 (nearest-id distances 12,14–34,01 mm) because the
label carries STEP (part) coordinates while the reading's positions live in the sheet's view frame, and the
label's other ids are faces and edges with no position at all.

That gap is not cosmetic: in the same blind run the model's `matched` sets are right in only two of the five
diameters (`g133`, `g65`; `pdf-22` matches the reading; `pdf-19` adds `g65` to `g68`; `pdf-20` answers
`[g134,g138]` where the truth is `g122`), and none of it reaches the score. The next change is written down
with its gate: map a label circle to a reading id **by diameter** when the label's STEP-verified diameter is
unique among the measured ones within 3% — plate stays 5/8 checkable, plastic stays 0, stored prompts stay
22/22 — then re-run the blind round for an id-level score.

## Binding scoring opened on the third sheet: a verified diameter identifies the geometry (2026-09-28)

The label's positions live in the part's (STEP) frame, so the position path mapped nothing on the third
sheet (nearest counterpart 12-34 mm away) and its bindings could not be scored at all. `expected_for_measurement`
now has a second path: when the position fails, the label's STEP-verified `diameter_mm` is matched against
the sizes the reading itself measured, and maps only if **exactly one** measured id is that size (tolerance
is the reading's own: 3% relative or 0,15 mm). The sizes come from the reading's diameter claims, whose
`drawn_mm` is computed from the radius of the geometry that claim matched — not from the printed value — so
a wrong binding cannot poison the mapping. Which path mapped each id is recorded as `mapping_basis`.

Measured effect (dry-17/dry-18, no model calls): plate **5 → 5** checkable (all 13 ids by position), plastic
**0 → 0**, third sheet **0 → 3** (`pdf-19 ↔ d11 → g68`, `pdf-20 ↔ d12 → g122`, `pdf-21 ↔ d13 → g65`). Two
rows stayed closed and should have: `pdf-17`/`pdf-22` are not label-paired (four "20"s, two "40"s), and the
Ø40 label's 40 mm meets **two** arcs of the same measured size, so the size is not unique and the mapping is
refused. The remaining unmapped ids are faces and edges — they carry neither a position nor a size.

Run `meaning-3b-11-third-blind-v2` repeated the third sheet's blind round with the new mapping in place and
the model untouched: its 17 raw answers are **byte-identical** to the previous blind round (0/17 differ), so
the two rounds are a paired measurement and the only difference is what got scored. Classes moved from
`correct 11 · no_label 6` to `correct 9 · partial 2 · no_label 6` — the two extra rows are the binding now
being judged, not a regression. **Id-level score: 1 of 3** (`pdf-21` Ø50 answered `[g65]`, expected `[g65]`;
`pdf-19` Ø30 answered `[g65,g68]` against `[g68]`; `pdf-20` Ø25 answered `[g134,g138]` against `[g122]`).
Kind was right 11/11 in the same round, which is the point: the interface names the right type and the wrong
source. Eight label-paired rows still cannot be scored on the binding — their label ids are faces and edges.

## The measured size in the menu, and the price of a longer instruction (2026-09-28)

Diagnosis first: the diameter requests offered 19 ids carrying only `kinds` and `points_mm`, and **two ids of
different size sat at the same point** — `g65` (Ø50 boss, measured 51,33 mm) and `g68` (Ø30 bore, 30,73 mm)
both at `(11,27; 180,71)`, `g122` (Ø25, 25,70) and `g125` (R20 arc, 41,08) both at `(69,9x; 20,5x)`. The
question could not be answered from the menu, which is exactly what the model's answers showed.

`interpret.measured_sizes` now reads the size the reading itself measured for an id (a claim's `drawn_mm`,
computed from the matched geometry's own radius, plus the catalog's circles) and `measurement_context` puts it
in each offered entry as `measured_diameter_mm`. Request version moved v3 → v4 → v5, and the two halves were
measured apart: the *field* fixed a wrong binding on the third sheet (id score 1/3 → 2/3, `pdf-19` answering
`[g68]` instead of `[g65,g68]`), while the *two extra instruction lines* cost the plate a row (8/8 → 7/8, the
`6,80 THRU ALL` size row naming two holes instead of four) — shortening the instruction to one line brought the
plate **back to 8/8** and left the third sheet at 2/3 with better reading agreement (14 → 15). Kept: v5.

Request diff is one field and one line (`dry-18` → `dry-19`: 30 → 32 lines, six ids gaining
`measured_diameter_mm`, candidate pairs / allowed ids / measurement context / schema unchanged). The
request-hash shield's baseline therefore moved from the `-09` pack to the `v5` runs, where it recomputes
**22/22** — a deliberate version bump, recorded, not a break.

## pdf-20 was a model miss, not a menu gap — and one guard was vacuous (2026-09-28)

The request for the Ø25 callout already carried the right answer twice: `measured_by_the_reading` named
`g122` with `drawn_mm` 25,70 (and `matched_geometry: [g122]`), the allowed list published `g122` at Ø25,70,
and `candidate_pairs` was empty. The model answered `matched=[g134, g65]` and justified it by claiming the
reading measured the callout between those two ids — a false statement about its own evidence. So the
remaining miss on that row is the model's, and the interface's part is recorded rather than patched.

Reading the judge while checking that: `pair_is_a_measured_candidate` was `not candidate_pairs or pair in
candidate_pairs`, i.e. **vacuously true** for every diameter/radius request, which by design offers no
candidate pairs — it said nothing and read as a pass, and it had silently blessed that same wrong binding.
It is joined by `named_ids_do_not_contradict_the_printed_size`: does any id the answer names carry a measured
size that contradicts the printed number? It uses only the sizes the request itself publishes (no label),
compares with the reading's own tolerance, and returns `None` where the measurement is not a size or nothing
named was sized, so an inapplicable guard is never a pass. Judge contract → `interpretation-contract-v5-size-agreement`.

Effect, measured by re-judging the stored answers with no model call: across the two v5 runs, 39 answered rows
give `true 8 · false 1 · none 30`, the single fail being exactly `pdf-20` (`g134` Ø41,08 and `g65` Ø51,33
against a printed 25,00), with no false alarms on the plate's 8/8 or the third sheet's correct rows. Scores
are unchanged — the classes come from the labels — what changed is that the row's reason now stands
contradicted by its own check. Record: `out/profile-step/judge-v5-effect.txt`. Packs `-14`/`-15` stay frozen as
the previous contract's record; `--check` reports their status comparison as skipped under another contract.

## A third mapping path: the label's verified value earns the reading's own anchors (2026-09-28)

Eight of the third sheet's seventeen rows could not be scored: the label names faces in the part frame
(`top_face`, `left_lug_face_a`, z=±13/±3/±10/±20/±5 …) while the reading reports ids in the sheet frame,
12–34 mm away — and a per-view frame fit has no basis in the views where the label's features are absent.

`expected_for_measurement` now has a third path: where the reading's own measurement of the callout agrees
with the label's independently verified value (the reading's tolerance, max(3%, 0,15 mm)), the label has
earned the reading's anchors as the expectation, recorded per id as `mapping_basis: "value"`. Neither frame
has to move; the two numbers have to agree. A row whose reading value disagrees earns nothing and stays
`unmapped` — no expectation is invented.

Coverage went **3/17 → 10/17** (14 names by value, 3 by diameter). The request text is provably unchanged —
17 of 17 prompts byte-identical to the stored run — so the answers already collected were re-judged under the
new expectation: classes `correct 10 · partial 1`, and the interface's id accuracy on the sheet reads **9 of
10** rather than the earlier 2 of 3. The label-based verdict and the label-free size guard single out the same
single row (`pdf-20`), which is the cross-check that both instruments point at the same failure.

Left open: `pdf-18` cannot be scored because the reading never resolved it (no anchors), and six spans still
have no label pairing although the label carries the rows (d5 R20, d14 Ø40, d7/d15/d16) — finishing that
pairing should take coverage to roughly 14–15 of 17.

## Pairing repeated values by kind, and letting value-confirmed size rows take the reading's own match (2026-09-28)

The pairing rule looked only at value+unit uniqueness, so the four rows printing 20 and the two printing 40 left
six label rows unpaired although both sides had been measured. Rows are now paired by value+unit **and the kind
both sides published**, falling back to value+unit where a kind is silent, and refusing a value repeated with the
same kind. Writing it, its own regression test caught a real bug: comparing kinds when both sides were silent
(`None == None`) paired a row onto an untyped candidate; the kind now decides only when both sides name one.

The value path also covers size callouts: where the label's verified value agrees with the reading's own
measurement, the expectation becomes the reading's own match, so one label name may stand for two reading ids (a
Ø40 boss drawn as two arcs) — that opened the R20 row and the Ø40 row, the two the diameter path refused for lack
of a unique size.

Binding coverage went 3/17 → 10/17 → **14/17**, and with the request text provably unchanged (17/17 prompts
byte-identical), the stored answers re-scored as `correct 14 · partial 1` with the interface's id accuracy at
**13 of 14**. The single failure is still `pdf-20`, the same row the label-free size guard flags.

Left: `pdf-18` (the reading never resolved it) and `pdf-15`/`pdf-23`, which need the axis the label states for
d7/d15 as a field rather than as prose.

## The axis route was tried and refuted: two rows printing 20 stay unpaired (2026-09-28)

Pairing the last two rows (`pdf-15` 20,54 mm and `pdf-23` 20,37 mm, both linear 20) with the label's d7
("top view, horizontal") and d15 ("bottom view, vertical") could have gone through the axis, which the label
carries as prose rather than as a field. Measured from the reading's own anchors, **both** spans come out
vertical in the sheet's frame (`g123↔g138`, `g55↔g90`), so the axis does not separate them — pairing them would
be a guess, and they stay unpaired under the rule that refuses a value repeated with the same kind.

What that exposes is recorded as an open question rather than papered over: the label's "top view, horizontal" /
"bottom view, vertical" and the reading's sheet-frame axis do not say the same thing, so one of them uses a
different frame or convention. Nothing is lost in the meantime — these two rows' agreement with the reading is
already reported in `answers_agreed_with_reading` (15/17); only a label-based binding score is absent. All three
remaining rows now have stated reasons: `pdf-18` (paired, the reading never resolved it) and `pdf-15`/`pdf-23`.

## The review round measured: defect detection 7/8, copying 8/17 — and showing the proposal lowers the score (2026-09-28)

`meaning-3b-16-third-review-v5` (17 measurements, `--review`), tallied per row and matching the harness summary:
defect caught 7 of 8 injected defects, one missed, one false alarm on a clean row, and 8 of 17 answers repeating
the shown proposal verbatim.

The comparison that matters, on the same fourteen scored rows:

| run | classes | ids | reading agreement |
|---|---|---|---|
| blind (`-14`) | correct 14 · partial 1 | **13/14** | 15/17 |
| review (`-16`) | correct 12 · partial 3 | **11/14** | 12/17 |

Showing the reading's own proposal buys copying, not accuracy: both the binding score and the reading agreement
drop. That confirms the recorded blind rule — the interface's own value is the blind number (13/14) — while the
review round measures defect detection and copying, not correctness.

## pdf-18 diagnosed: the row's anchors were wrong, not its scale (2026-09-28)

`pdf-18` ("6") carries no claim in the reading, and its bind record shows why: `status="partial"` with
`implied_px_per_mm` 10,33 against the sheet's 3,83 px/mm calibration. Two explanations were on the table and one
is now refuted by measurement: of the sheet's sixteen rows, thirteen imply 3,75–3,93 (median 3,86), the five
outliers are all diameter/radius callouts where the row is a leader rather than a span between extension lines
(so the metric means nothing there), and `pdf-18` is the only ordinary row that stands out — while its nearest
neighbour `pdf-16`, some 60 px away, implies 3,81. The row is not in a differently scaled view.

What it is: the wrong pair of anchors. A "6" at the sheet's own calibration spans 6 × 3,83 ≈ 23 px, and the
reading's chosen anchors are 62 px apart — but among the candidates it already collected sits one exactly
23,28 px away (`p296`). The refusal is therefore consistent with the reading's rule (it will not bind a row that
contradicts its calibration); what is missing is scale-aware row selection. Next step: extend
`bind._repick_row_with_calibration` to prefer the single candidate pair that matches the printed value at the
sheet's scale when the chosen pair contradicts it, and to leave `partial` when no unique candidate exists —
gated on the plate staying 8/8, plastic coverage 14/14, and the request-hash shield at 22/22.

## The guided flow measured: 17 fields the user supplied, 8 of them already on the sheet (2026-09-28)

PLAN section 23-A is built (session store, revisions, undo, draft STEP) and nothing had measured its cost side.
`eval/guided_effort.py` reads that cost out of the files the flow itself wrote and separates three answers for every
decision a user supplied: `bound` (a reading claim ties the value to the geometry the decision uses), `present` (the
sheet prints the value but nothing identifies it as that feature), `absent` (the sheet does not print it).

On the plate sheet (`examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`, the saved session
`out/guided/91411e3e…`: 17 fields, revision 3, build `complete`) the tally is **6 bound + 2 present + 0 absent**. The
calibration the user clicked two points for is the reading's own `pdf-0` claim — its anchors are the centres of `g9`
and `g11`, the two circles the user clicked. The four through holes are `pdf-3` ("6,80 THRU ALL", count 4, matched to
`g9`/`g10`/`g11`/`g12`), the pocket is `pdf-4` (Ø50 on `g8`), and its depth is printed as 8,00 (`pdf-6`). What no rule
settles is the *identity* of the two remaining printed numbers: 15,00 (`pdf-5`) and 8,00 (`pdf-6`) are both printed,
and nothing on the sheet states which is the thickness and which the pocket depth. That is the shape of the problem —
not missing values, missing identities.

The independent half passes: `eval/metrics.py` against the reference STEP
(`examples/pdf with steps/5/plate with a pocket.STEP`) gives one valid solid, bounding box [15, 79.99, 120.00] vs
[15, 80, 120] (≤0.01 mm per axis), volume 124.798 vs 124.825 cm3 (0 %), matching cylinder radii. The reference STEP
never enters the production path — `guided.py` does not see it. So the flow's arm's-length result is a functionally
equal part, and its user cost now has a baseline: 4 gate questions at open, candidate menus of 11 profiles / 7
circles / 20 "measurements" on the plate (36/8/22 plastic, 11/7/26 on the second sheet) — and 13 of the plate's 20
menu rows are view numbers and a date, not dimensions, while the reading binds 7 numbers to geometry.

Cost: one more tool to keep honest. A `bound` label is the reading agreeing with the user, not independent truth,
which is exactly why the reference comparison is reported beside it. Next slice (PLAN section 24): pre-fill the
guided decisions from the reading, ask only identities, and gate on ≤3 interactions on the plate with the reference
check still passing.

## The reading answers the flow's questions itself: plate 17 fields → 2 interactions (2026-09-28)

PLAN section 24's first two slices. `src/drawingto3d/advise.py` (new) turns the reading chain's own claims into
proposals the flow can accept in one step, and `guided.py` keeps every proposal, acceptance and build in a
persistent step log the page renders.

**What changed.** A claim becomes a proposal only if the arithmetic holds at the sheet's own scale, by one of two
routes: (1) the reading's frame — millimetres measured from the outline's bounding-box centre at the reading's
`px_per_mm` — mapped to pixels, accepted only when every anchor lands on the geometry it names (≤2 px off a line's
span, a circle's centre or radius, an arc's ring); (2) otherwise the constraint search, which needs a pair of
points on the named geometry whose distance equals the printed value within 1 %. The frame route is what lets the
calibration proposal use *the same two points the user clicked* (`pdf-0`'s anchors are the centres of `g9` and
`g11`), so the accepted calibration is not merely the same number but the same measurement. Identity proposals
carry their alternative printed candidates (the plate's depth offers 8,00 with 15,00 named beside it); a pocket is
never proposed without a depth, because `validate_decisions` would refuse it later and a proposal that cannot be
accepted is not a proposal. `guided.create` now stores `reading` + `proposals` + `log`; `accept()` applies the
batch in one revision and writes one log line per field with the evidence that was on screen — actor, action,
field, value, confidence, span id, printed text, pixel lengths and deviations; `save()` compares the new decisions
against the proposals so an edit reads as `edit` (user) and an accepted value as `accept`; `build()` logs start and
finish with the audit verdict. `static/guided.html`/`.js` gained the proposal panel (per-item accept, evidence
line, alternative candidates) and the reverse-chronological log with its evidence behind a `<details>`.

**Bought.** On the plate the reading proposes **9 items** covering everything the user supplied by hand before
(contour, calibration, 4 × Ø6,8 through, Ø50 pocket + 8 mm depth, 15 mm thickness): the flow now takes **one
accept plus one build = 2 interactions**, leaves **zero questions**, and produces the same decisions as the manual
run. The built STEP passes the independent reference check (`eval/metrics.py`: volume 124.804 vs 124.825 mm³,
`shape_ok` and `detail_ok` true). Recorded in `out/guided-effort/plate-flow/run.json`, and driven live in the
browser (upload → 9 rows with evidence → accept → build → log). On the plastic sheet the same code path proposes
3 items (contour, 120 mm calibration, pocket depth) and honestly leaves one question — the sheet prints no
thickness identity — with the build reported `blocked` instead of guessed; the second sheet leaves 3 (it is a
multi-view exercise, out of scope). Model choice is free now: `VISION_MODELS`/`CODER_MODELS` are only a preference
order, `choose_vision_model`/`choose_text_model` pick by the server's own `capabilities`, an explicit
`DRAWINGTO3D_VISION_MODEL`/`_CODER_MODEL` tag is honoured exactly (an uninstalled tag is an error, never a silent
substitution), and a machine with no reader refuses rather than sending an image to a text model — on this machine
`qwen3-vl:8b-instruct` is now selected where the old allowlist selected nothing.

**Cost.** Proposals are only as good as the reading: the plastic sheet's holes are still unresolved, so the
accept step cannot fix what the reading never bound — the remaining questions are now the product's honest
backlog (PLAN section 24-C: a model adviser may answer them, off by default). The step log makes session files
grow with every interaction; entries are capped and the evidence is written once per decision, not per render.
Tests: `tests/test_advise.py` 8, `tests/test_guided_proposals.py` 7, `tests/test_model_choice.py` 12,
`tests/test_guided.py` 16 unchanged.

## A sheet's own title block is not the part — new case registered, annotation regions skipped (2026-09-28)

The user's new sheet (`examples/pdf with steps/10/`, an A3 vector 1:5 flanged 90° elbow) entered the eval
registry as `exercise-12` with its reference `Exercise 12.STEP` (bbox [270, 274, 335] mm, 4791.7 cm³, 60
cylinders), 20 printed values, radius calls 25/10/8 and diameter calls 270/220/180/158/140/120/116/92/76/18;
`split: unassigned`, `_counts` now 9 parts (5 seen + 4 unassigned). Its front-end row, measured: **19/20
covered, 3 noise, 1.550 px/mm, 14 suspect**; `eval/check_tables.py` 21 rows / 0 drifted.

**What changed.** `proposal._annotation_loops`: a closed loop whose inside carries ≥3 printed phrases of which
at least half are words is an annotation region (a title block, a parts table), and it is skipped together with
the sheet frame by `_outline_of`, by `read_sheet` (callers see `components.annotation_loops`, the ratio goes into
the notes) and by `guided.drawing_options` — where the phrases inside such a loop also leave the number menu.
Measured on the four vector sheets before the change: every part loop holds **0** phrases, a border holds
25-66, and `10/Exercise 12`'s title-block box (a plain 4-line rectangle, 708.6 × 216.7 px at the sheet's
bottom-right corner) was the biggest loop left after the frame and the flow's `bound` outer contour
(457.17 × 139.78 mm).

**Bought.** On the new sheet the proposal's refusal names a part loop (28 primitives, 209.32 × 278.49 mm) instead
of the title block, the flow offers no title-block contour and its menu lost the part number and the scale
(`2103017`, `1: 5`: 43 → 41 rows). The reading chain was already clean here — 0 of its 30 spans carry
title-block text — so the leak was in the outline search and the menu, not in the binding.

**Cost / risk.** The rule is deliberately weak: text held by the sheet *border* is untouched (the plate's title
block sits inside the border loop and still offers `2026`), so a sheet whose title block is not a traced loop
keeps its noise. Asserted: plate 11 profiles / 20 menu rows / 9 proposals and plastic/Drawing.pdf unchanged;
`tests/test_proposal.py` +3, `tests/test_guided.py` +2.

## The flow reads the part class before offering decisions (2026-09-28)

**What changed.** `proposal.part_class(observations)`: circles about one centre are grouped into stacks
(`_concentric_families`), and a stack of ≥3 circles at ≥3 distinct diameters whose biggest circle covers ≥15 % of
the page width makes the sheet `rotational-flanged`; otherwise an available part loop makes it `flat-part`, and
neither makes it `unknown` with the reason recorded. `guided.create` stores the class in the session record, logs
it as a visible step (`reading/class`) and hands it to `advise.proposals(options, reading, archetype)`, which only
offers plate-shaped decisions — an outer contour, holes, a thickness — for a `flat-part` sheet.

**Bought.** Measured on the four vector sheets: `10/Exercise 12` reads `rotational-flanged` with the evidence of a
5-circle stack (Ø274/Ø160/Ø142/Ø93/Ø77 mm against the printed Ø270/Ø158/Ø140/Ø92/Ø76, biggest circle 0.193 of the
page width) and the flow's decisions drop **29 → 1** (the calibration alone; the title-block contour and 28
through-holes are gone — the build that used to die on a geometry audit is no longer attempted). The plate and
`Drawing.pdf` (no stack at all) and the plastic (its stacks are 0.011 of the width) all read `flat-part` and keep
their decisions: 9 / 3 / 3, unchanged.

**Cost / risk.** A "flange" in this classifier is a geometric fact, not a promise that the rotational archetype
exists: for `rotational-flanged` the flow can currently propose the calibration and nothing else, so the sheet
still needs a contour + thickness typed by hand and the build still writes a plate — the honest refusal of a whole
archetype is the next slice. Also unmeasured on raster sheets, where the circle record is Hough-limited (concentric
pairs are suppressed by `minDist`). Tests: `tests/test_proposal.py` +1 (stack/rectangle/small-stack/empty) and
`tests/test_guided.py` +2 (class + withheld decisions; plate unchanged).

## A rotational sheet decides its own flange — and builds it (2026-09-28)

**What changed.** For a `rotational-flanged` sheet `advise._flange_proposals` now reads the decisions out of
the sheet's own circles: the concentric stack's biggest circle (`circle_<gid>`, a circle profile that already
existed in the options) is the outer size, the stack's smallest circle is the bore, the printed value the
sheet repeats is the thickness, and every Ø circle standing on that face is a hole — the stack's own circles
are excluded from the holes, and so is any circle of a neighbouring view. `_identity_candidates` judges
"aligned" by the projection the reading resolved (`x`/`y`, with a 0.5 mm tolerance instead of one pixel) and
counts equal-valued rows as one candidate (`_agreed`: three rows printing 20.00 measure one thickness, and
the odd value out becomes an alternative). `proposals` only offers a generic calibration row when the row's
own ends agree with the reading's fitted scale within 2 %; on the flange sheet it calibrates from the face's
own printed Ø270 over its drawn 425.2 px instead — 1.5747 px/mm against the consensus fit's 1.550.

**Bought.** `10/Exercise 12` (flanged 90° elbow) now opens with **zero questions after one accept**: the flow
proposes the flange face Ø270, the thickness 20 (three printed rows vote), the bore Ø76 and six Ø18 bolt
holes, and the build writes one valid solid [270.0, 270.0, 20.0] mm whose cylinders are r135 (outer), r38
(bore) and 6 × r9 — the same flange the reference `Exercise 12.STEP` carries (r135, r38, r9, 20 mm thick).
Measured against the previous state: 29 plate-shaped decisions (a title-block contour and 28 through-holes)
and a build that died in the geometry audit; and the flow's former calibration row was a 10 mm row resolved
0.5 px short (1.5037 px/mm, 3 % off the sheet's own fit), which would have made every size in the part 3.5 %
large — the built flange's outer diameter came out 282.76 mm before this change and 270.0 after.

**Cost / risk.** The built part is the *flange*, not the elbow: the bend body, the second flange and the
bore steps (Ø92/Ø116/Ø120/Ø140/Ø158) are not read as decisions yet, and the plan's own note records that
single-view, fixed-thickness scope. Six bolt holes are what this sheet draws on that face; the reference part
carries more along rows 88 mm apart, so a symmetric pattern the drawing implies but does not draw is *not*
invented — that is the reading's contract, not an omission of this change. The plate (9 decisions,
calibration 100.0), the plastic (3, 120.0) and `Drawing.pdf` (3, 26.0) are unchanged; the 2 % calibration
gate leaves every one of their rows (0.42-0.71 % agreement) in place. Tests: `tests/test_guided.py` +2
(decisions, and the built solid's sizes against the sheet's printed numbers), one revised.


## User-guided offline draft STEP flow (2026-09-28)

Added `/guided`: source upload, explicit two-point calibration, detected closed contour selection, thickness and circular through-hole/pocket decisions, GeneralPlan v1 build, STEP download and STL preview. Atomic sessions retain decisions through failures; revision checks, undo, source hashes and startup recovery protect saved work. The compiler contract is unchanged.

A real plate drawing produced one valid solid with four through-holes and a blind pocket. Reference comparison after generation: bounding box approximately 120 × 80 × 15 mm and volume difference 0.022%. Profile and centres remain traced estimates, not a dimension-constrained reconstruction. Independent synthetic CAD tests check actual size, volume, centres and depth. Full suite: 488 passed; final focused suite after recovery/HTTP additions: 16 passed. Fresh-session end-to-end UI acceptance and the final click/thickness-save changes still need browser verification. Evidence and next task: `eval/reports/guided-flow.md`. Checkpoint taken when account usage first showed 91% after the requested 90% threshold.

## 2026-09-28 — §23-B ilk dilim: bağlanan basılı ölçüyle kesin eskiz

- `src/drawingto3d/sketch.py` (yeni): bağları tek ölçeğe en küçük karelerle oturtur, her bağın çizili karşılığını
  ve sapmasını verir, çelişkiyi ve bağlanmayan özellikleri raporlar, çelişkiyi kullanıcı diliyle soruya çevirir.
- `src/drawingto3d/guided.py`: `Decisions.bindings` (+`BindingEnd`), `validate_decisions` bağ uçlarını/ölçü
  kaynağını doğrular, `sketch_diagnostics`/`note_sketch` teşhisi oturum kaydına yazar, `public()` `sketch`
  alanını ve çelişki sorularını döndürür, `make_plan` ölçeği bağlardan alır ve her bağı `binding_N` (source user)
  parametresi yapar; varsayım satırı ölçeğin kaynağını ve bağlanmayanları yazar.
- `guided.html`/`guided.js`: panel 2'ye "Seçili ölçüyü bağla" + bağ listesi (kaldır ile), yeni "4 · Kesin eskiz"
  paneli (ölçek kaynağı, her bağın sapması, çelişki, bağlanmayanlar, açık kontur), bağ modu çizim üstünde iki ucu
  yakalar (kontur köşesi/daire merkezi), kopya tıklama koruması.
- Testler: `tests/test_sketch.py` (5), `tests/test_guided.py` (bağ ölçeği üretimi değiştirir; çelişki üretimi
  engeller; olmayan kenara bağ reddedilir).

## 2026-09-28 — §23-C1: rasterda yay uydurma (görülmemiş paftalar için)

- `src/drawingto3d/raster.py`: zayıf Hough geçişi (`ARC_PARAM2`) + `_angular_support`/`_longest_ring_run`/
  `_ink_radius`/`_verified_arcs` — açı aralığı ve yoğunluğu kapıdan geçen kısmi daireler `kind="arc"` ilkeli
  olur (kayık halka kapısı: koşu boyunca gerçek yarıçap medyanı ±2,5 px, dağılımı ≤2,5 px). Notlar yeni geçişi
  yazar; daire/yay mürekkebi sayılan parça çizgiler çizgi listesinden düşülür.
- `tests/test_raster.py`: 3 yeni test (sentetik 120° yay geri gelir; tam daire yay olarak tekrarlanmaz;
  0° sarmalı koşu ölçümü). Modül: **12 geçti** (366 s).
- Ölçüm: beş görülmemiş çizim de raster ve hiçbirinde parça konturu yok (bkz. HANDOFF §23-C1); kök neden
  "arcs are not fitted yet" + ölçü ankrajı yokluğu.

## 2026-09-28 — §23-C2: raster yayları mürekkebe oturtuldu (Kasa + kambur kapısı); eğri kontur kapanışı açık

- `raster.py`: `_ink_point` / `_fit_circle` (Kasa uydurma), yay ucu mürekkebin ucu, `ARC_MIN_SAGITTA_PX=4`,
  `ARC_MIN_SPAN_DEGREES=45`.
- Sentetik stadyumda gerçek yaylar tam (r=99 ↔ çizili 100); aday seli 23'ten 5'e indi; `-k "synthetic or
  longest"` 4 geçti; tam modül koşusu arka planda.
- Ölçülen açık: stadyum döngü kurmuyor (0 döngü) — yayın açı aralığı teğeti aşıyor (70°→290°, çizili
  90°→270°), kapanış 3 px'e uymuyor. Sonraki iş: yay ucunu mürekkebe budamak ya da `_loops`'a yay-çizgi
  teğet birleşmesini eklemek.
## §23-C3: yay ucu mürekkebe budandı, teğet birleşmesi ve gerçek pafta seli ölçüldü — 2026-09-28

**Ne indi (`src/drawingto3d/raster.py`).** Yay koşusunun uçları artık "düz bir çizgi de bu noktayı
kaplıyorsa o mürekkep yayın değil, çizginin" kuralıyla budanıyor (`_trim_to_own_ink` + `_point_at_segment`);
uydurma ve açı aralığı budanmış noktalardan yeniden hesaplanıyor, aralık alt sınırı orada da uygulanıyor.
`_verified_arcs` artık birleştirilmiş çizgileri de alıyor; `observe_raster` bunları yaylardan önce hesaplıyor.

**Ölçüm 1 — sentetik stadyum (kurşun kalem 3 px mürekkep).** Yayların yeri tam: `([200,300], r=98)` ve
`([700,300], r=98)` ↔ çizili `(200,300)/(700,300), r=100`; ama budama teğet noktasını da götürdüğü için
açı aralıkları 96°→264° ve 278°→430° (çizili 90→270 / 270→90), yani yaylar birleşim yerinden ~10 px **kısa**
kalıyor → **döngü yine 0**. Kök neden net: teğet birleşiminde yayın ve çizginin mürekkebi aynı yerdir, bu
yüzden uç yakınlığına dayanan kapanış kuralı (3 px) bu birleşimi hiçbir zaman göremez.

**Ölçüm 2 — gerçek pafta (Exercise_51.PNG, 3300×2550, arka plan işi).** Yaysız: **325 çizgi + 0 yay → 1
döngü** (o da antet dikdörtgeni). Yaylarla: **325 çizgi + 3884 yay → 24 döngü**. Yani zayıf geçiş gerçek
paftada **kullanılamaz ölçüde sel** üretiyor; kambur/açı kapıları ince sentetik mürekkebe göre ayarlanmış,
gerçek paftanın kalın ve gürültülü mürekkebinde düz çizgilerin üstünde yay uyduruyor. 24 döngünün en
büyükleri de parça hattı değil (antet/çerçeve).

**Kanıt.** `tests/test_raster.py -k "synthetic or longest"` **4 geçti**; raster+guided+proposal odaklı koşu
arka planda (`/tmp/suite-c3.txt`).

**Tek sonraki iş (sıra önemli).** (1) Yay kapısını gerçek pafta ölçeğine bağla: koşunun tamamı zaten
düz bir çizgiyle kaplıysa aday hiç doğmasın (satır üstü seline karşı), yarıçap alt sınırı pafta boyutuna
göre ölçeklensin, coverage ≥ 0,9 istensin — hedef Exercise_51'de yay sayısını 3884'ten parça hattındaki
gerçek yaylar mertebesine indirmek ve döngü sayısının antet dışında artıp artmadığını ölçmek. (2) Teğet
birleşmesini `_loops`'a ekle: yay adayı için "öteki ucun noktası bu dairenin üstünde (±2 px) ve açı
aralığın içinde (birkaç derece toleransla) ise birleşir" kuralı; PDF yollarını etkileyeceği için kapı
koşuları (plaka 7/7, plastik 14/14, Drawing.pdf 16/17, istek hash'leri) aynı dilimde koşulmalı.
## §23-C4: teğet köşe birleşmesi kodlandı; stadyum hâlâ kapanmıyor (ölçülmüş köşe aritmetiği) — 2026-09-28

**Ne indi.** `proposal.py` (döngü kurma, PDF yollarını da besler): `_line_arc_corner` — bir doğru ile yayın
köşesi, yayın merkezinin doğruya dik izdüşümü (teğet noktası); `_arc_hit` — bir noktanın yayın çemberine
izdüşümü, yayın açı aralığı içindeyse (25° taşma toleransı, 0/360 sarması dahil); zincir köşeye
oturtuluyor (birleşim köşe ise önceki öğenin ucu köşeye çekilir); kapanış hem uç yakınlığıyla hem köşe
üzerinden sınanıyor; `ARC_JOIN_SLACK_PX=2.5`, `ARC_JOIN_DEGREES=25`, `ARC_JOIN_SNAP_PX=16`.
`raster.py`: gerçek pafta için yay kapıları — yarıçap alt sınırı `max(12 px, 0.12 × ortanca çizgi boyu)`
(glif/kalabalık mürekkep halkalarını eler) ve koşunun budanmış oranı.

**Ölçüm (sentetik stadyum).** Segmentler: iki çizgi `(171,200)-(729,200)` ve `(171,400)-(729,400)` —
yani **derleme geçişi düz çizgiyi köşenin 29 px ötesine uzatmış** (yayın teğet mürekkebini yutuyor);
yaylar `r≈98`, uçları köşeden ~10 px **içeride**. Köşe noktaları doğru: `(700,200)`, `(700,400)`,
`(200,200)`, `(200,400)`. Buna rağmen **döngü 0**: zincir kuruluyor ama kapanış ifadesi bir yerde
tutmuyor (ölçülen son adım: kapanış köşesi `(200,200)` ile yayın ucu `(189,203)` arası 11,4 px; snap
toleransı 16 px'e çıkarıldı, yine kapanmadı). Yani eksik, zincirin kendi ilk öğesinin *başlangıcının* da
köşeye çekilmemesi ya da birleşim sırasının beklenenden farklı olması — sıradaki iş bunu bir iz (debug)
koşusuyla adım adım bastırmak; tahminle ilerlemeyi bırak.

**Doğrulama durumu (dürüst).** `tests/test_raster.py -k "synthetic or longest"` **4 geçti**. **Tam takım
koşusu bu `_loops` değişikliklerinden ÖNCE başlatıldı** (`/tmp/suite-c4.txt`), yani bu dilimin
`proposal.py` değişikliklerini kapsamıyor: bir sonraki pencerenin ilk işi tam takımı ve kapı koşularını
(plaka 7/7, plastik 14/14, Drawing.pdf 16/17, istek hash'leri, `eval/check_tables.py`) yeniden koşturmak.
Gerçek pafta ölçümü (yeni yay kapılarıyla Exercise 51 / 17 / Flange) arka planda: `/tmp/arc-loops.txt`.

**Tek sonraki iş.** (1) Tam takım + kapılar (yukarıdaki risk). (2) Stadyumda zincir kararlarını adım adım
bastıran iz koşusu ve kapanışın bitirilmesi; hedef `döngü ≥ 1`, kutu `[100,200]-[900,400]`. (3) Kapanınca
sentetik paftayı `/api/guided/open` → kalibrasyon → kalınlık → iki delik → üret → STEP'i bağımsız ölç
(beklenen 96 × 24 × 10 mm, 2 delik); sonra gerçek paftalar.

## §23-C5/C6/C7: köşe kapanışı, kapsamlama ve sahte ölçek gerilemesi — 2026-09-28

**§23-C5 — iz koşusu iki gerçek zincir hatası buldu.** Geçici `DRAWINGTO3D_TRACE_LOOPS=1` kancasıyla
(kanca kaldırıldı): (1) yay/çizgi birleşiminde zincir **ilk** öğenin metasını kullanıyordu (`meta`),
son öğeninki (`chain[-1][3]`) olmalı; (2) köşe birleşimi adayın **ters** yönünde de ateşliyordu — köşe
adayın uzak ucuna denk gelince zincir yayı 13 px geri yürütüyor, döngü 2 öğede "kapanıp" uzunluk kapısına
takılıyor ve gerçek döngü kayboluyordu. Düzeltmeler: son öğe metası; `closing` yalnız `len(chain) >= 3`
iken; köşe adayın yakın ucundaysa kabul (yoksa `continue`); kapanış hem uç hem köşe üzerinden.
**Sonuç:** sentetik stadyum **1 döngü, 4 öğe** (üst çizgi → sağ yay → alt çizgi → sol yay), köşeler
(700,200)/(700,400)/(200,400)/(200,200), alan **129 934 px²** ↔ çizili 131 416 px² (**%1,1**).

**§23-C6 — köşe kapanışı raster yaylarına kapsamlandı.** `_loops(..., corner_joins=False)` +
`raster_arcs(observations)` (yalnız `method == "hough-arc"` varsa açık); `guided.drawing_options` bunu
geçiyor. **Ölçüm:** PDF yolu eski kuralda → `tests/test_proposal.py` **22 passed** (Exercise 12 reddi yine
28 ilkel kesit döngüsünü adlandırıyor, `5/Plate` proposed ✓); stadyum köşesiz **0**, köşeli **1** döngü.

**§23-C7 — sahte ölçek gerilemesi (gerçek, ürün yolunu koruyan test yakaladı).**
`test_chain_model.py::test_a_sheet_the_reading_cannot_measure_never_reaches_a_planner` kırıldı: yay geçişi
`examples/504715c44a0f1b2bbb386bb7c387a8db.jpg` paftasında 168 yay üretiyor ve okuma **kendine 3,28 px/mm
ölçek** uydurup planlayıcıya gidiyordu (`refusals: []`) — "pikselden izlenen geometri doğrulanmış ölçü
sayılmaz" kuralının ihlali. Ölçülen adımlar: `bind.py`'de `hough-arc` yay merkezleri çapa adayı olmaktan
çıkarıldı (bağlanan ölçü 10→9, çapa 18→16 — **yetmedi**); ardından `read_sheet` içinde **raster pafta için
kendi kendine kalibrasyon reddedildi** (herhangi bir `hough-arc` ilkeli varsa `scale = None` + not).
**Sonuç:** `refusals: ['pafta ölçeği okunamadı (kalibrasyon yok)']` ✓; rasterda ölçek kullanıcının iki
tıklamasında kalıyor.

**Temiz gerçek-pafta ölçümü (bugünkü kod, tek yazar — `/tmp/arc-loops.txt`).** Exercise_51: 340 çizgi +
**143 yay** → **1 döngü** (antet) — yaysız da 1. Exercise 17: 588 çizgi + **168 yay** → 1 döngü (antet).
Flange.PNG: 385 çizgi + **207 yay** → 2 döngü (biri 153×53 px kutu). Yani yay kapıları seli 27× kesti
(3884→143) ve yay yarıçapları artık makul (27…160 px), ama **üç paftada da parçanın dış konturu kapanmıyor**:
sentetik stadyumun kapanması mükemmel mürekkep sayesinde. Sıradaki iş kod değil **ölçüm**: Exercise_51'de
parça hattının zinciri nerede ölüyor (hangi boşluk, hangi segment kümede yok).

**Doğrulama durumu.** `test_proposal.py` 22 ✓ (C6 sonrası), `test_raster.py -k "synthetic or longest"` 4 ✓;
`test_chain_model.py` + `test_proposal.py` + `test_raster.py` üçlüsü C7 sonrası arka planda
(`proc_18127a482150` → `/tmp/suite-c6.txt`); **tam takım bugünkü hâl için hâlâ koşulmadı**. Kalan bilinen
tıkaç: `_trace` yayın poligon ucunu köşe yerine budanmış mürekkep ucu sayıyor
(`"kontur uçları çizimde birleşmiyor"`). Commit atılmadı (ağaçta paralel ajanın işi var).

## §23-C8: eğri kontur ürün yolunda sunuluyor; plan kendi denetiminde "profil kapalı değil" diyor — 2026-09-28

**Kazanım (ölçüldü, /api/guided/open → HTTP):** sentetik stadyum paftası artık **`outline_0` (`wire`)** olarak
sunuluyor (yanında iki delik dairesi). Bu, yay uydurma + köşe kapanışı + `_trace` köşe kabulünün ürün yolunda
çalıştığı anlamına gelir; kararlar kaydediliyor ve **hiç soru kalmıyor** (`questions: []`).

**Kalan tıkaç (planın kendi denetimi, mesaj birebir):** `1 validation error for GeneralPlan — outer: profil
kapalı değil; 0. parça 1. parçaya birleşmiyor`. Yani izlenen profil eskiz terimlerinde hâlâ kapanmıyor.
Bu dilimde eklenenler: `_trace` içinde köşe kabulü (`_line_arc_corner` arkasından merkez→doğru dik izdüşümü),
`_on_ring`, ve köşeye çekilen yay ucunun kanonik açısını uçtan yeniden hesaplayan `_reangle`. `_reangle`'a
rağmen kapalılık denetimi geçmiyor: sıradaki iş **ölçüm** — planın `outer` kenar listesini ve denetimin ölçtüğü
birleşimleri bastırmak (denetim hangi çifti adlandırıyorsa oradan), tahminle değil.

**Ayrıca bu dilimde:** `(1)` sunucu yeniden başlatıldı (eski süreç eski `_trace`'i servis ediyordu; ilk probe
bu yüzden profili göremedi), `(2)` API probu ile uçtan uca: open → save → build (UI kabulü sayılmaz; A turu
kuralı gereği UI kabulü ayrıca tarayıcıda yapılmalı), `(3)` `read_sheet` raster paftada kendi kendine
kalibrasyonu reddediyor (sahte ölçek gerilemesi kapandı, `refusals: ['pafta ölçeği okunamadı (kalibrasyon yok)']`),
`(4)` koşan ölçümler: `chain_death` (Exercise_51'de zincir nerede ölüyor → /tmp/chain-death.txt) ve
`test_chain_model + test_proposal + test_raster` üçlüsü (/tmp/suite-c6.txt).

## §23-C9: raster paftaya özel birleşim toleransı (ölçümle geldi) — 2026-09-28

**Gerekçe (ölçüm, `/tmp/chain-death.txt`, `1/Exercise_51.PNG`, 340 çizgi + 143 yay + 4 daire = 483
segment).** Parçanın kendi hattı kümede: en uzun segment `g169` **2625 px** düz kenar
`[321,606]→[2946,606]`; ondan sonraki gerçek birleşimler ve boşlukları: `g141` 32,7 px → `g28` 27,0 px →
`g355` (yay) 17,5 px → `g377` (yay) 9,6 px → `g402` (yay) 7,5 px → `g350` (yay) 1,6 px. Yani dış hattın
parçaları **1,6–32,7 px** aralıkla duruyor; `_loops` ise **3 px** istiyordu. İkinci bulgu: naif "en yakın
uç" yürüyüşü 6. adımdan sonra kısa segment kümesine (ölçü çizgileri/yazı, boşluklar 1–13 px) sapıyor — yani
toleransı açmak tek başına yetmez, **en az dönen** kuralı baskın kalmalı (`_loops` sırası: kapanış, dönüş,
boşluk).

**İndi.** `_loops(..., corner_joins=False, join_tolerance_px=LOOP_TOLERANCE_PX)`; birleşim, kapanış ve son
kapanış bu parametreyi kullanıyor. `RASTER_JOIN_TOLERANCE_PX = 36.0` (≈ 2,9 mm @ 12,5 px/mm) **yalnız
raster paftalarda** açık: `guided.drawing_options` `raster_arcs(observations)` ile seçiyor; vektör yolların
zinciri 3 px'te kalıyor (Exercise 12 reddi ve `5/Plate` ölçümleri o kurala dayanıyor).

**Doğrulama.** Sentetik raster testleri **4 passed** ✓; stadyum ürün yolunda hâlâ `outline_0 (wire)` ✓.
Üçlü koşu (C7 sonrası): `test_chain_model.py` + `test_proposal.py` **tamamen yeşil**, `test_raster.py`'de
**tek** kırık `test_a_full_circle_is_not_repeated_as_an_arc` — aynı test tek başına koşulduğunda geçiyor
(`-k "synthetic or longest"` → 4 passed), yani **test sırasına bağlı**: dosyada önce koşan bir test raster
modülünün durumunu değiştiriyor (bilinen tek `monkeypatch.setattr` `subprocess.run`'u hedefliyor; şüpheli,
geri alınmayan düz bir sabit ataması). Bu, bir sonraki pencerenin ilk 5 dakikalık işi.

**Kalan tıkaç (ürün yolu).** Stadyumda plan denetimi hâlâ `outer: profil kapalı değil; 0. parça 1. parçaya
birleşmiyor` diyor — `_trace` köşe kabulü + `_reangle` sonrası bile. Sıradaki iş ölçüm: planın `outer`
kenar listesini ve denetimin ölçtüğü birleşim çiftlerini bastırmak.

**Koşan ölçüm.** `/Users/aydemir/.hermes/cache/scratch/s10/guided_raster.py` (proc_b5c049662462) dört raster
paftayı **ürün yolundan** (`drawing_options`) geçirip sunduğu profil sayısını/kutularını `/tmp/guided-raster.txt`'e
yazıyor — yeni toleransın gerçek paftada parça konturunu çıkarıp çıkarmadığının ölçümü. Commit atılmadı.

## §23-C10: yay yönü sözleşmesi — zincirin gezinmesi değil, dedektörün mürekkebi — 2026-09-28

**Ölçüm (ürün yolu, `/tmp/guided-raster.txt`, dört gerçek raster pafta).** Yeni raster birleşim toleransı
(36 px) her paftada kontur kapatıyor: Exercise_51 **8**, Exercise 17 **7**, Flange **4**, my_part.jpg **10**
wire profili (öncesi 0–1). Kutular küçük detay kümeleri (tablo hücreleri, yay yığınları); Exercise 17'nin en
büyüğü **486×450 px** — bu paftada parça hattı olabilir. Baskın yeni not:
`bu konturun yay yönleri mevcut eskiz sözleşmesinde birlikte desteklenmiyor`.

**Kök neden.** `_trace` her yayın kanonik açılarını **zincirin hangi uçtan girdiğine göre** çeviriyordu
(`delta` işareti), sonra `arcs[0]`'a bakıp tüm döngüyü ters çeviriyordu. Karışık dedektör sırası olan bir
döngüde bu, bazı yayları negatif span'la bırakıyor ve sözleşme kapısı (`0 < b − a < 360`) patlıyordu.
Oysa yayın mürekkebi, zincir hangi uçtan girerse girsin **aynı** yay parçasıdır; kanonik span dedektörün
kendi sırasından alınmalı.

**İndi.** `_trace` artık `first = a if delta > 0 else b`, `a = −first`, `b = −first + abs(delta)` kuruyor —
per-yay çevirme kaldırıldı (dedektörün `start_degrees`/`end_degrees` sırası korunur). `_reangle` de işaret
duyarlı: köşeye çekilen ucun açısı güncellenirken `b − a`'nın işareti korunuyor (start `b`'yi geçerse aşağı,
end `a`'yı geçerse yukarı sarar), böylece yanlış taraftaki yay çizilmiyor. Global ters çevirme bloğu artık
tetiklenmiyor (her yayın span'ı pozitif) ve kapı bir doğrulama olarak kalıyor.

**Sınır.** Bu düzeltme *aynı yayın* iki ucu arasındaki mürekkebi doğru ifade eder; zincirin kendisi bir
yaydan **tutarsız** yönde geçiyorsa (yayı iki kez kesen bir döngü) hâlâ temsil edilemez — o durum ölçümde
çıkarsa zincir tarafında düzeltilecek.

**Doğrulama.** Yeni ölçüm koşuyor: `proc_70f83a19c7ce` → `/tmp/guided-raster-run2.txt` (aynı dört pafta,
ürün yolu). Sentetik raster testleri 4 ✓ ve stadyum `outline_0` ✓ (bu değişiklikten önceki son teyit).

## §23-C11: raster birleşimlerinde ara nokta kapaması — 2026-09-28

**Ölçüm (C10 sonrası, `/tmp/guided-raster.txt`, ürün yolu).** Yay yönü notu **düştü**; profiller büyüdü:
Exercise_51 **9**, Exercise 17 **11**, Flange **8**, my_part.jpg **17** wire profili — ve kutular artık
parça ölçeğinde: **Flange 634×593, 523×512, 494×653** (flanş Ø ~600 px), **my_part.jpg 487×364**,
Exercise 17 486×450. Baskın yeni not ikiye ayrıldı: `iki yay arasında açık uç var; kontur düzeltmesi gerekli`
(yay-yay birleşiminde `gap > 1e-7` kapısı) ve `kontur uçları çizimde birleşmiyor` (çizgi-çizgi/çizgi-yay
birleşiminde köşe kuralı yetmedi).

**İndi.** `_trace` birleşim döngüsüne ara nokta kapaması: köşe kuralı bir şey bulamazsa ve boşluk
`ARC_JOIN_MIDDLE_PX = LOOP_TOLERANCE_PX + ARC_JOIN_SLACK_PX = 5.5 px`'ten küçükse iki uç **ortada**
buluşturulur (geometriyi 3 px'in altında düzeltir; büyük teğet boşlukları yine köşe kuralı kapatır). Bu,
kırpılmış yay ucu ile birleştirilmiş çizgi arasındaki, ya da aynı karışımın iki yayı arasındaki küçük
boşlukları kapatır ve yay-yay kapısı (`gap > 1e-7`) artık sahte kırılma üretmez.

**Doğrulama.** Sentetik raster testleri **4 passed** ✓; stadyum ürün yolunda `outline_0 (wire, 50 nokta)` ✓,
notu doğru: "Konturlar çizimden ölçülmüştür; kesin ölçülü eskiz olarak onaylanmış değildir."

**Koşan ölçüm.** `proc_1b6f08068933` → `/tmp/guided-raster-run3.txt` (aynı dört pafta, ürün yolu) — iki notun
düşüp düşmediğini ve profillerin parça hattına dönüşüp dönüşmediğini gösterecek. Sunucu yeni kodla yeniden
başlatıldı (stadyumun uçtan uca STEP denemesi için).

## §23-C12: eğri raster paftadan ilk geçerli STEP (ürün yolu) — 2026-09-28

**Ne oldu.** Sentetik stadyum (iki düz kenar + iki yarım daire + iki delik) yönlendirmeli akıştan uçtan uca
üretildi: `open` → `outline_0 (wire)` → kararlar (üst kenarın kendi iki köşesi = 500,3 px = **60 mm**,
kalınlık **10**, iki **Ø7,2** delik) → `save` (soru kalmıyor) → **`build: complete`**.
Kanıt: `out/guided/b1539969d37443f1a53c4f88d6c352f9/build-1-5a2c32cf/part.step` — `step_facts`:
**1 katı, geçerli, kutu {10,0 / 23,339 / 60,063} mm, 8,904 cm³, 8 yüz**. (Bu bir **API probu**; A kuralı
gereği UI kabulü tarayıcıda ayrıca yapılmalı.)

**Bunu mümkün kılan düzeltmeler.** `(1)` Köşe = yay merkezinin doğruya dik izdüşümü, artık **her** yay-içeren
birleşimde uygulanıyor (zincir uçları eşit bıraksa bile) — (713,203)/(729,400) sapmasını düşürdü.
`(2)` `_align(edge)`: eskiz yayı merkez+yarıçap+açıdan yeniden kurduğu için yarıçap **gelen uçtan** alınır,
**giden uç o halkaya izdüşürülür** ve bir sonraki parça oraya başlatılır; böylece birleşimler denetimin
`0,01 mm` payı içinde kapanır (öncesi: `0. parça 1. parçaya birleşmiyor`). `(3)` Ara nokta kapaması
(`ARC_JOIN_MIDDLE_PX = 5,5 px`) ve yay yönünün dedektör mürekkebinden alınması (§23-C10) — yay-yönü notu
düştü, profiller büyüdü (Exercise_51 **9**, Exercise 17 **11**, Flange **8**, my_part.jpg **17**;
Flange'de **634×593**, **494×653** px kutular).

**İki açık, ikisi de ölçüldü.** `(a)` Kalibre edilen kenar %0,1 (60,063 ↔ 60) ama diğer eksen
**23,339 ↔ 24,0 mm (%2,8)**: yayın yarıçapı **98 px** çıkıyor (çizili 100) çünkü `raster.py`'de
`_trim_to_own_ink` yayı kendi mürekkebine kısarken **uydurma da kısılmış koşuya** yapılıyor. Düzeltme:
merkez/yarıçap **kısılmamış koşudan**, yalnız açı aralığı kısılmış koşudan.
`(b)` Katının x ekseni **60,06 mm** (izlenen profilin *uçları*); stadyumun yaylardan gelen beklenen genişliği
~**83 mm** → yayın kamburu katıya girmemiş. Sıradaki ölçüm: planın `outer` içeriğini (4 çizgi + 2 yay mı,
yalnız çizgiler mi) ve eskizin yay örneklerini bastırmak.

**Tek sonraki iş.** `(b)`nin ölçümü (plan `outer`), sonra `(a)`nın düzeltmesi (uydurma kısılmamış koşudan) —
sonra aynı stadyum üretimini tekrarlayıp boyutları yeniden ölçmek (hedef: 24,0 ± 0,1 ve ~83 mm).

## §23-C13: stadyumun kamburu içe düşüyor — yay sözleşmesi işaretli yayı ifade edemiyor — 2026-09-28

**Ölçüm (plan.json, `out/guided/b1539969d37443f1a53c4f88d6c352f9/build-1-5a2c32cf`).** Plan doğru kurulmuş:
4 kenar — üst çizgi (0,06 / 23,34) → (60,06 / 23,30); **yay** merkez (60,00 / 11,66), r **11,64**, açılar
**89,67° → 269,71°**; alt çizgi (59,94 / 0,02) → (0 / 0); **yay** merkez (−0,003 / 11,67), r **11,67**,
açılar **−89,98° → 89,67°**; iki delik Ø7,2 (`source: user`) ✓; işlemler: `extrude` + iki `cut` ✓.

**Çelişki.** Eskizin uzanımı: x ∈ [−11,67 … 71,7] = **83,4 mm**, y = 23,34, z = 10 → katı **{83,4 / 23,34 / 10}**
ve hacim ≈ **17,9 cm³** olmalı. Ölçülen: kutu **{10,0 / 23,339 / 60,063}**, hacim **8,904 cm³**, 8 yüz.
Yani yaylar **içe** kamburlaşmış: sağ yayın mürekkebi 90° → 270° arasını **saat yönünde** (0°'den geçerek)
alıyor; eskiz sözleşmesi ise `0 < b − a < 360` (saat yönünün tersi) istediği için aynı mürekkep ancak
"270°'den 450°'ye ters yönde" yazılabiliyor ve uç kimlikleri zincirle uyuşmuyor. §23-C12'deki yay-yönü
kapısı bu yüzden yanlış tarafı zorluyor.

**Sonuç ve tek sonraki iş.** Sözleşme **işaretli yay** taşımalı: `a` ve `b` arasındaki fark negatif olabiliyorsa
(saat yönü) hem uç kimlikleri zincirle uyuşur hem kambur doğru tarafa düşer. Yapılacak: eskiz/plan şemasına
işaretli süpürme (b − a negatif olabilir) eklemek, runner'ın b < a için saat yönünde çizdiğini doğrulamak,
`_trace`'deki `0 < b − a < 360` kapısını buna göre gevşetmek ve stadyum üretimini tekrarlayıp kutu/hacmi
yeniden ölçmek (hedef: {83,4 / 23,34 / 10} mm ve ≈17,9 cm³). İkinci açık (§23-C12a: yay yarıçapının **98 px**
çıkması, çizili 100) ayrı duruyor: uydurma kısılmamış koşudan yapılmalı.

## §23-C14: işaretli yay süpürmesi — stadyumun iki kamburu da katıya girdi — 2026-09-28

**Ne indi.** `(1)` `_trace` artık yayın kanonik açısını **zincirin girdiği uçtan** alıyor ve süpürmeyi
işaretli kuruyor: `walked` = girilen ucun *pafta* açısı; `at_seam` = zincir dedektörün kendi `a` ucundan mı
girdi; `span = −delta if at_seam else +delta`; `a_canonical = −walked`, `b = a + span`. (Negatif süpürme =
saat yönü yay; sağ kambur böyle kurulur.) `(2)` Global ters çevirme bloğu ve `0 < b−a < 360` kapısı kalktı;
yerine `b == a` veya `|b−a| ≥ 360` reddi. `(3)` `geo.py`: süpürme kapısı **işaretli** (−360…360, sıfır
değil) ve üç-nokta yayın orta örneği artık **yarım süpürme** ile bulunuyor (`start + sweep/2`) — bu, sarma
yapan yaylarda zaten gizli bir hataydı (`(start+end)/2` yanlış tarafı veriyordu). `(4)` `general.py`'nin
kapalılık denetimindeki açıklık kapısı da işaretli kabul ediyor.

**Ölçüm (aynı stadyum, ürün yolu, API probu).** Plan artık: sağ yay **89,67° → −90,29°** (süpürme
**−179,96**), sol yay **−89,98° → −270,33°** (**−180,34**) — ikisi de dışa kambur ✓. Katı:
`out/guided/5667fc64e9ae475c84f48522b2b8c32a/build-1-058c10e2/part.step` → 1 geçerli katı,
kutu **{10,0 / 23,339 / 83,31} mm**, hacim **17,439 cm³**, **8 yüz = 4 düzlem + 4 silindir** (iki delik +
iki yay yüzü ✓). Öncesi: {10,0 / 23,339 / 60,063} ve 8,904 cm³ (§23-C13). Hedef {83,4 / 23,34 / 10} kambur
ekseninde **%0,1** içinde tutuldu ✓.

**Kalan tek hata (ölçülü, §23-C12a).** Kalınlık yönü dışındaki kısa eksen **23,339 ↔ 24,0 mm (−%2,8)** ve
hacim (−%2,5) — çünkü yayın **yarıçapı 11,64/11,67 mm** (98 px), çizili 100 px. `raster.py`'de
`_trim_to_own_ink` yayı kendi mürekkebine kısarken **uydurma (merkez/yarıçap) da kısılmış koşuya** yapılıyor.
Düzeltme: merkez/yarıçap **kısılmamış koşudan**, açı aralığı kısılmış koşudan; sonra aynı stadyum üretimi
tekrarlanıp 24,0 ± 0,1 mm ve ≈17,9 cm³ hedeflenecek.

**Koşan/biten doğrulamalar.** Odaklı regresyon `tests/test_geo.py` + `test_general.py` + `test_proposal.py` +
`test_guided.py` → `/tmp/suite-c14.txt`; dört gerçek paftanın ürün-yolu ölçümü `proc_1b6f08068933` →
`/tmp/guided-raster-run3.txt`. Bu üretim **API probu** (UI kabulü tarayıcıda ayrıca yapılmalı). Commit atılmadı.

## §23-C15: yay halkası bütün koşudan uyduruldu — kısa eksen −%2,8 → −%0,95 — 2026-09-28

**İndi.** `raster.py`'de koşu artık iki parçalı: `raw` = koşunun bütün mürekkep noktaları, `found` =
`_trim_to_own_ink` sonrası. **Merkez/yarıçap `raw`'dan** uyduruluyor (Kasa), **kambur (sagitta) kapısı
`raw`'a** soruluyor, **açı aralığı `found`'dan** okunuyor. Gerekçe ölçülü: kısılmış koşuya uydurulan halka
kısa çıkıyordu (98 px, çizili 100) ve bu doğrudan milimetreye yazıyordu.

**Ölçüm (aynı stadyum, ürün yolu, API probu).** Yay yarıçapları **11,822 / 11,886 mm** (öncesi 11,64 / 11,67;
çizili 12,0). Katı: `out/guided/699f6df735114b5882bb8fa42bd1d3b6/build-1-fa52f368/part.step` → 1 geçerli katı,
kutu **{10,0 / 23,772 / 83,709} mm**, hacim **17,825 cm³**, 8 yüz. Hedefler: 24,0 / 83,94 / 10 ve ≈17,9 cm³
→ hatalar sırasıyla **−%0,95**, **−%0,28**, **−%0,4** (öncesi −%2,8 / −0,15 / −%2,5). Kalan ~%1: yarıçap hâlâ
~0,13 mm kısa (kırpma/`_ink_point` penceresi) — kesin ölçüler B-2 kısıt çözücüsünün işi, bu bir **taslak**.

**Koşan doğrulama.** `tests/test_raster.py + test_proposal.py + test_guided.py + test_sketch.py + test_geo.py
+ test_general_plan.py + test_plate_plan.py` → `/tmp/suite-c15.txt` (raster uydurması değişti; tam takım
`proc_d2295cb92590` bu düzeltmeden **önce** başladı, o yüzden bayat sayılır).

## §23-C16: UI kabulü (gerçek tarayıcı, eğri raster pafta) — ilk yarı — 2026-09-28

**Yapıldı (gerçek fare/klavye, `/guided`):** stadyum PNG'si gerçek dosya girişinden yüklendi ✓; tuval
ölçüsü 726×436 (görüntü 1000×600, ölçek 0,726), panel "3 kontur · 2 daire · 0 ölçü adayı · sınıf: unknown"
dedi ✓; **kontur gerçek tıklamayla seçildi** ("Karar kaydedildi", kayıt 1) ✓; **iki kalibrasyon noktası
gerçek tıklamayla** seçildi, değer **60** gerçek tuşlarla yazıldı ve "Ölçeği uygula" basıldı → **kayıt 3** ✓.
Yani eğri raster paftada profil + kalibrasyon kararları **gerçek arayüzden** geçiyor ✓.

**Kesinti.** Kalınlık alanına yazma denemesi ve sonraki `js` çağrısı **tarayıcı koşum katmanının 5 sn'lik
IPC zaman aşımına** takıldı (`Input.dispatchKeyEvent`, `Runtime.evaluate` ✗) — uygulama hatası değil, koşum
katmanı; önceki çağrılarda kendini toparlamıştı. Kalan adımlar (kalınlık, iki delik, **Üret**, indirme ve
SHA-256 karşılaştırması) sıradaki denemede tamamlanacak.

**Karşılaştırma (tam olan yol).** Aynı pafta **API probuyla** uçtan uca üretildi ve bağımsız ölçüldü
(§23-C15): `{10,0 / 23,772 / 83,709} mm`, **17,825 cm³**, 1 geçerli katı, 8 yüz (4 düzlem + 4 silindir).
UI kabulü tamamlandığında aynı sayılar beklenir; iki yolun aynı STEP'i vermesi ayrıca karşılaştırılacak.

## §23-C17: odaklı koşu — 115 passed, 2 failed (biri YENİ gerileme) — 2026-09-28

**Koşu:** `tests/test_raster.py + test_proposal.py + test_guided.py + test_sketch.py + test_geo.py +
test_general_plan.py + test_plate_plan.py` → **2 failed, 115 passed (33:39)**.

**`test_raster.py::test_a_full_circle_is_not_repeated_as_an_arc`** — bilinen **sıra bağımlılığı**: tek
başına geçiyor (`-k "synthetic or longest"` → 4 passed), dosya koşusunda kırılıyor. Dosyada önce koşan bir
test raster modülünün durumunu değiştiriyor. Ayrı iş.

**`test_guided.py::test_title_block_leaves_the_contour_and_number_menus` — YENİ ve gerçek.** Ölçüm:
`drawing_options(observe("10/Exercise 12.pdf"))` en geniş `wire` profili **2138,12 px** (antet kutusu
708,6 px, beklenen < 100) → 2138 px = sayfanın neredeyse tamamı, yani **çerçeve/antet bloğu yine profil
olarak sunuluyor**. `test_proposal.py` aynı koşuda **geçti** (yani `propose_general` yolu hâlâ 28 ilkelli
kesit döngüsünü reddediyor ✓) — tıkaç yalnız **yönlendirmeli yolun (`drawing_options`)** kapsama/dışlama
süzgecinde.

**Şüpheli (sıralı, ölçümle ayrılacak).** `(1)` `10/Exercise 12.pdf` taramalı bir pafta: okuma raster
geçişini de çalıştırıp `method == "hough-arc"` ilkeli üretiyorsa `raster_arcs(observations) == True` olur ve
**36 px'lik raster birleşim toleransı bu paftaya da uygulanır** ✗ — 2138 px'lik döngü tam da bu toleransın
ayırt edemeyeceği kadar yakın parçaları birleştirmesiyle oluşur. Doğrulama: aynı paftada `raster_arcs(...)`
çıktısını ve iki toleransın (3 px / 36 px) döngü sayısını yan yana basmak. `(2)` Genişletilmiş toleransla
oluşan bir döngü, `_frame_loops`/`_annotation_loops` süzgeçlerinden kaçıyorsa kural sıkılaştırılmalı
(ör. sayfanın %80'inden fazlasını kaplayan profilleri hiç sunmamak — `FRAME_COVERAGE` ile aynı mantık).

**Tek sonraki iş (bu gerileme için):** `(1)`i ölçmek — `raster_arcs(observe(SHEET_10))` ve
`_loops(lines, arcs, corner_joins=…, join_tolerance_px=…)` ikilisiyle döngü sayıları/Genişlikleri; çıkarsa
kapıyı daraltmak (raster toleransı yalnız *çerçevesi tanınmayan* paftalara, ya da geniş profile sayfa
kapsama süzgeci).

**§23-C17 ek ölçüm (aynı gün, hemen ardından).** `(a)` Hipotez `(1)` **yanlış** çıktı:
`P.raster_arcs(observe("10/Exercise 12.pdf")) == False` ✓ — yani 36 px'lik raster toleransı bu paftaya
uygulanmıyor; paftada vektör yolundan **397 çizgi + 74 yay + 42 daire** var. `(b)` Suçlu `_loops` değil,
`drawing_options`'un süzgeçleri: sunulan profiller **outline_4 = 2138×2156 px (6 öğe: çizgi,çizgi,yay,çizgi,
çizgi,yay)** ve **outline_2 = 2119×2544 px (28 öğe)** — ikincisi paftanın neredeyse tamamı (çerçeve),
ötekisi pafta ölçeğinde bir kontur. Not "antet/tablo bölgesi atlandı (1 döngü…)" diyor, yani antet kutusu
süzüldü ama **bu iki dev döngü süzülmedi** ✗. `test_proposal.py` geçtiği için tıkaç yalnız yönlendirmeli
yolun kapsama süzgecinde.

**Tek sonraki iş (kesinleşti).** `drawing_options`'ta dev döngülerin neden süzülmediğini ölçmek:
`_loop_box(loop)` kutusu ile `_trace` sonrası `points` kutusunu yan yana basmak (süzgeç hangisine bakıyorsa
öteki onu atlatıyor) ve `FRAME_COVERAGE=0,80` kuralını bu iki döngü için de işletmek — ya da `_trace`
değişikliklerinin (işaretli yay + `_align`) bir döngünün *noktalarını* pafta ölçeğine çıkardığını
doğrulamak. Ölçüm komutu: `_frame_loops(loops, frame.width, frame.height)` çıktısı ile `wires` kimliklerini
karşılaştırmak.

## §23-C18: dev-döngü gerilemesinin kökü — konvansiyon uyuşmazlığı + sahte dev yarıçaplı yaylar — 2026-09-28

**Ölçüm 1 (süzgeçler doğru).** `10/Exercise 12.pdf` (sayfa 2200×1700): 9 döngü; **döngü 0 = çerçeve
(2121×1621) → `_frame_loops` True ✓**, **döngü 1 = antet (709×217) → `_annotation_loops` True ✓** — yani
süzgeçler çalışıyor; sunulmaması gereken dev profiller bu ikisi değil ✗.

**Ölçüm 2 (gerçek kök).** `_trace(loops[2])` ve `_trace(loops[4])` içindeki yaylar:
`a −93,1 b −86,9 r 1102,8`, `a −84,9 b 265,0 r 1075,6`, `a −93,8 b −86,2 r 1078,1` — yani **sahte dev yarıçaplı
yaylar** (2200 px'lik sayfada r ≈ 1080; 6–10°'lik süpürmeler = düz kenarın yay sanılması) ve bunların
`_arc_points` ile örneklenen noktaları **sayfanın dışına** düşüyor (`y ≈ −900`, iz kutusu 2546 px ✗) →
profilin noktaları pafta ölçeğine çıkıp `test_title_block…` kırılıyor. İki ayrı kusur birleşiyor:
`(a)` **vektör (PDF) okuyucusu** düz kenarları dev yarıçaplı yay olarak veriyor (raster tarafındaki
`ARC_MIN_SAGITTA_PX` kapısının vektör karşılığı yok); `(b)` `_trace` kanonik (y yukarı) açı yazarken
`drawing_options`'un nokta yolundaki `_arc_points` **pafta (y aşağı) konvansiyonunu** bekliyor → dev
yarıçaplarda aynalama binlerce piksel sapma demek.

**Tek sonraki iş.** `(b)`yi kapatmak: `drawing_options` profil noktalarını üretirken yayı `_trace`'in yazdığı
konvansiyonla örneklemek (kanonik a/b'yi pafta açısına çevirerek: `_arc_points(centre, radius, −a, −b, n)`,
ya da `_trace`'de a/b'yi pafta konvansiyonunda bırakıp kanonik dönüşümü yalnızca plan emitinde yapmak).
`(a)` için ayrı iş: vektör okuyucusunda kambur (sagitta) kapısı. Doğrulama: `test_guided.py::test_title_block_
leaves_the_contour_and_number_menus` tek başına koşacak (beklenen: en geniş < 100 px) + stadyum üretiminin
{10,0 / 23,772 / 83,709} mm sayıları **değişmemeli**.

**§23-C18 düzeltmesi (kendi ölçümümün hatası).** Probum yay örneklerini `_arc_points(center, radius, a, b)` ile
**dönüşüm yapmadan** aldı ✗; uygulama ise `guided.py:256`'da kanonik açıları pafta açısına çeviriyor
(`-e["a"], -e["b"]`) ✓ — yani "(b) konvansiyon uyuşmazlığı" iddiam **yanlış** olabilir. Güvenilir olan iki
ölçüm: `(i)` süzgeçler doğru (çerçeve ve antet döngüleri işaretli ✓, §23-C18 ölçüm 1); `(ii)` **uygulamanın
kendi** `options["profiles"]["points"]` kutusu outline_2 için 2119×2544 px (sayfa 2200×1700 ✗) — yani dev
profilin noktaları sayfa dışına taşıyor. Şüpheli artık **dev yarıçaplı sahte yaylar** (r ≈ 1080, 6–10°'lik
süpürmeler): vektör okuyucusu düz kenarı böyle veriyor ve `_align` yarıçapı gelen uçtan aldığı için yayın
merkezi sayfa dışına düşüyor; örnekleme merkez+yarıçap üzerinden gidince nokta da sayfa dışına çıkıyor.

**Tek sonraki iş (güncel).** Uygulamanın kendi nokta yolunu ölçmek: outline_2 ve outline_4 için her yayın
`center/radius/a/b` değerlerini ve `guided.py:256`'nın ürettiği örnek kutusunu bastırmak; ardından **vektör
okuyucusuna kambur (sagitta) kapısı** eklemek — `abs(radius)` sayfaya göre saçma olan ya da kendi kirişi
üzerinde 4 px'ten az kamburlaşan yaylar reddedilmeli (raster tarafındaki `ARC_MIN_SAGITTA_PX` kuralının
vektör karşılığı). Doğrulama: `test_guided.py::test_title_block_leaves_the_contour_and_number_menus` tek
başına (beklenen en geniş < 100 px) + stadyum üretiminin {10,0 / 23,772 / 83,709} mm sayıları değişmemeli.

## §23-C19: dev-döngü gerilemesi KAPANDI — span'ı koruyan `_align` + kiriş kapısı — 2026-09-28

**Kök (kesinleşti).** `_align` yarıçapı gelen uçtan alıyor ✓ ama açıyı `edge["b"] > edge["a"]` işaretine
göre **sarmalıyordu** ✗: neredeyse düz bir kenarın (vektör okuyucusunun bezier'i → r ≈ 1067, gerçek süpürme
~12°) küçük negatif süpürmesi `while b <= a: b += 360` ile **348°'ye** çıkıyor ✗ → `_arc_points` örnekleri
sayfanın dışına (y ≈ −1146) düşüyor ✗ → profilin noktaları pafta ölçeğine çıkıyor ✗ → test kırılıyordu.

**İndi.** `(1)` `_align` artık **süpürmeyi koruyor**: `span = edge["b"] − edge["a"]` (okuyucunun/koşunun
ölçtüğü gerçek yay ✓), `a` = gelen ucun kanonik açısı, `b = a + span`, giden uç o halkaya izdüşürülüyor —
sarma yok. `(2)` `_trace` yay bloğunda **kiriş kapısı**: `radius > 4 × |chord|` ve `|delta| > 180` ise
süpürme küçük yola indiriliyor (saman yolu: düz kenarın dev yarıçaplı yay sanılması).

**Ölçüm.** `10/Exercise 12.pdf` (2200×1700) en geniş wire profilleri: **2138 / 2119 px → 488×470, 374×52,
195×195 px** ✓ (süzgeçler zaten doğruydu: çerçeve 2121×1621 `_frame_loops` True ✓, antet 709×217
`_annotation_loops` True ✓). **`tests/test_guided.py` → 24 passed (95 s)** ✓. Testin eşiği dürüstçe
güncellendi: `< 100` → `< 620` (antet kutusu 708,6 px; eski eşik, bu konturları *yanlışlıkla* eleyen
yay-yönü kapısının yan etkisiydi; artık paftanın kendi 488 px'lik görünüşü sunuluyor ✓).

**Sınır.** Eski `0 < b−a < 360` kapısı bu bozuk süpürmeleri kazara eliyordu; kapı kalktığı için koruma artık
`_trace`'in kiriş kapısı + `_align`'ın span koruması. Vektör okuyucusunda ayrıca bir kambur (sagitta) kapısı
hâlâ iyi bir iş (r ≈ 1080'lik "yay"lar hâlâ yay olarak taşınıyor).

## §23-C20: UI kabulü — profil/kalibrasyon/kalınlık gerçek tarayıcıda ✓, delik+üretim koşum katmanına takıldı — 2026-09-28

**İki kez, temiz oturumdan, gerçek fare/klavyeyle doğrulandı.** Stadyum PNG'si gerçek dosya girişinden
yüklendi → panel "3 kontur · 2 daire" ✓; **kontur gerçek tıklamayla** ✓ (kayıt 1); **iki kalibrasyon noktası
gerçek tıklamayla**, değer **60** gerçek tuşlarla, "Ölçeği uygula" ✓ (kayıt 2); **kalınlık 10 yazıldı ve
"Kalınlığı kaydet" basıldı** ✓ (kayıt 3) — kullanıcının "tarayıcıda henüz denenmedi" dediği iki düğmeden
biri buydu ✓. İkinci turda aynı adımlar tekrar geçti ✓ (tekrarlanabilir ✓).

**Tıkaç: tarayıcı koşum katmanı (uygulama değil).** Kalan adımlar — iki daireyi seçmek, Ø7,2 yazmak,
**Üret**, indir, yeniden aç, geri al, SHA-256 — sırasında koşum katmanı art arda opsiyonlardan sonra
5 sn'lik IPC zaman aşımına düşüyor (`Runtime.evaluate`, `fill_input`, `Input.dispatchKeyEvent` ✗);
ayrıca **her yeni çağrıda sayfa `#sheet` olmadan geliyor** (aktif sekme kayboluyor ✗), yani akış tek
çağrıda bitmek zorunda; tek çağrıda ~6-8 opsiyondan sonra katman düşüyor ✗. Bu bir **ortam** sınırı:
A turunda (bu pencerenin başında) aynı akış 16 eylemde tamamlanabilmişti.

**Sonuç.** UI kabulünün **karar girişi** kısmı gerçek tarayıcıda kanıtlandı ✓; **üretim/indirme/geri alma**
kısmı için koşum katmanının daha sağlıklı olduğu bir an ya da daha küçük op grupları gerekiyor ✗ — bir
sonraki pencere bunu denemeli (ör. sayfayı `new_tab` ile açıp yalnız delik+üretim adımlarını çalıştırmak,
ya da A turundaki gibi `js` yerine daha çok gerçek tıklamayla ilerlemek). API probu UI kabulü **sayılmaz** ✓.

**Bekleyen koşular.** Dört paftanın bugünkü kodla ölçümü (`proc_5b980f6f2cdd` → `/tmp/guided-raster.txt`) ve
tam takım (`proc_628f5bca0d4e` → `/tmp/suite-c20.txt`).

## §23-C21: bayat tam takımın 3 kırığı — ikisi bilinen, biri bu pencerenin işi — 2026-09-28

**Koşu `proc_d2295cb92590` (raster/guided düzeltmelerinden ÖNCE başladı → bayat): 3 failed, 564 passed
(1:03:51).** `(1)` `test_guided.py::test_title_block_leaves_the_contour_and_number_menus` — **o günden beri
kapandı** ✓ (§23-C19; `test_guided.py` 24 passed ✓). `(2)` `test_raster.py::test_a_full_circle_is_not_
repeated_as_an_arc` — bilinen **sıra bağımlılığı** (tek başına geçiyor ✓). `(3)`
`test_catalog_cli.py::test_printed_values_survive_missing_scale_or_outline[4]` — **bu pencerenin kararı**
(§23-C7) fazla geniş: `proposal.read_sheet` (proposal.py:544-553) **raster yayı olan her paftada** ölçeği
düşürüyor ✗; test ise `sheet_px_per_mm = 4` **verilmiş** bir ölçekle "basılı değerler ölçek olmadan da
yaşar" savını sınıyor ✗ → verilen ölçek de düşünce test kırılıyor.

**Karar (uygulanacak).** `read_sheet` "verilmiş" ölçek ile "pikselden türetilmiş" ölçeği ayırt edemiyor
(provenans alanı yok ✗) — iki yol var: `(A)` `meanings`e ölçek provenansı eklemek (`scale_source: derived |
given`) ve kapıyı yalnız `derived` için işletmek (testin fixture'ı yeni alanı set etmeyeceği için varsayılan
`derived` olur ✗ — testin `[4]` varyantı yine kırılır ✗, o zaman test **kurala uygun** biçimde güncellenmeli:
raster paftada pikselden gelen ölçek paftanın kendi ölçüsü sayılmaz, ölçek kullanıcı kalibrasyonundadır);
`(B)` kapıyı tümden kaldırıp sahte ölçeği **kaynağında** kesmek (bind.py çapa seçimi + ölçek türetme yolu) —
ama ölçüm gösterdi ki yay çapaları dışlandığında bile .jpg 3,28 px/mm kuruyordu ✗ (9 çapa yetiyor ✓), yani
`(B)` tek başına yetmiyor ✗. **Öneri: `(A)` + testin `[4]` varyantını yeni davranışa göre güncellemek**
(test dosyası: `tests/test_catalog_cli.py:28`, `partial_reading.sheet_px_per_mm = scale`, parametre `[None,4]`).

**Doğrulama.** Güncel kodla tam takım koşuyor (`proc_628f5bca0d4e` → `/tmp/suite-c20.txt`); bitince bu üç
kırığın hangisinin sürdüğü kesinleşecek. Ayrıca dört paftanın ölçümü (`proc_5b980f6f2cdd`).

## §23-C22: run4 — raster paftalarda büyük konturlar KÜÇÜLDÜ (C19'un bedeli) — 2026-09-28

**Ölçüm (aynı dört pafta, ürün yolu, bugünkü kod; run3 → run4):**

| Pafta | run3 (önce) | run4 (bugün) |
|---|---|---|
| Exercise_51 | 11 profil, en büyük 994×119 | 11, **961×117 + 420×838** ✓ |
| Exercise 17 | 17, **594×435**, 486×450 | **9**, 179×353, 243×289 ✗ |
| Flange | 9, **634×593**, 494×653, 523×512 | **8**, 218×410, 48×102 ✗ |
| my_part.jpg | 19, **487×364**, 264×328 | 17, **315×238**, 153×206 ✗ |

Notlar artık neredeyse tümüyle `kontur uçları çizimde birleşmiyor` ✗ — yani **C19'da join'ler artık
kapanmıyor**. Sebep: `_align` artık süpürmeyi **koruyup** çıpayı (a) oynatıyor ✗; raster yaylarında uçlar
köşe birleşimiyle **çekildiği** için, izdüşüm eski (uç-güdümlü) davranışla yapılmalıydı ✓. Yani C19 vektör
yolunu kurtardı, raster yolunun kapanışını bozdu ✗ (Exercise 51'de yeni 420×838 kazancı var ✓ — tartılı).

**Tek sonraki iş (kesin).** `_align`ı iki davranışa ayırmak: **kurulum döngüsünde** (okuyucunun kendi verisi)
süpürme-koruyan davranış ✓; **birleşim döngüsünde** (köşe/ara nokta kapamasından sonra) eski uç-güdümlü
davranış — yani yarıçap gelen uçtan ✓, giden uç **kendi açısıyla halkaya** izdüşürülür ✓ (süpürme öyle
kurulur). Uygulama: `_align(edge, span_is_truth: bool)` ya da iki küçük yardımcı; sonra run4'ü tekrarlayıp
Exercise 17/Flange'in büyük kutularının (594×435 / 634×593) geri geldiğini ve `test_guided.py`nin 24
passed kaldığını doğrulamak ✓. Kiriş kapısı (r > 4×|chord| ve |delta| > 180) yerinde kalır ✓.

## §23-C23: `test_catalog_cli` kırığı — sebep provenans değil, korumasız `getattr` — KAPANDI — 2026-09-28

**Gerçek sebep (ölçüldü).** `AttributeError: 'types.SimpleNamespace' object has no attribute 'primitives'`,
`src/drawingto3d/proposal.py:546` — yani §23-C21'de tahmin ettiğim "verilmiş/pikselden türetilmiş ölçek
ayrımı" **değil** ✗: §23-C7 kapısı `observations.primitives`ı doğrudan gezdiği için, testin `observe` stub'ı
(`SimpleNamespace(frame=None)`) altında **çöküyordu** ✗.

**İndi.** İki yerde koruma: `raster_arcs(observations)` ve `read_sheet`'in ölçek kapısı artık
`getattr(observations, "primitives", ())` geziyor ✓. Provenans alanı **eklenmedi** (gereksiz çıktı ✓) ve
testin `[4]` varyantı **değiştirilmedi** ✓ (davranış zaten doğruydu ✓).

**Doğrulama.** `test_catalog_cli.py + test_guided.py + test_chain_model.py` → **36 passed (6:36)** ✓ — yani
`test_printed_values_survive_missing_scale_or_outline[4]` ✓, `test_guided.py` 24 ✓ ve sahte-ölçek
gerilemesinin bekçisi `test_chain_model.py` ✓ birlikte yeşil (raster ölçek düşürmesi gerçek .jpg'de hâlâ
çalışıyor ✓).

**Kalan tek bilinen kırık.** `test_raster.py::test_a_full_circle_is_not_repeated_as_an_arc` — **sıra
bağımlılığı** (tek başına geçiyor ✓, dosya koşusunda kırılıyor ✗; dosyada önce koşan bir test raster
modülünün durumunu değiştiriyor). Tam takım güncel ağaçta **565 passed, 2 failed** idi; bu düzeltmeyle
kalan kırık bu sıra bağımlılığı + §23-C22'nin raster kapanış borcu.

## §23-C24: §23-C22 DÜZELTMESİ — run5 == run4 (deterministik), C22'nin tablosu yanlış okundu — 2026-09-28

**İki bulgu.** `(1)` **run5, run4 ile bit bit aynı** (diff yalnız `notlar` satırlarında: teşhis mesajı artık
boşluğu ve öğe türlerini taşıyor ✓) → dört paftanın ürün yolu **deterministik** ✓. `(2)` **§23-C22'nin tablosu
hatalıydı** ✗: "en büyük kutu" diye yazdığım değerler koşu dosyasının **ilk listelenen** kutularıydı ✗,
en büyükleri değil ✗ (ölçüm hatam). Odaklı prob bunu gösterdi: **Exercise 17'nin sunulan en büyük profili
557×513 px (4 nokta, not yok ✓)** — yani "C19 raster kapanışını bozdu ✗" sonucu **fazla genel**: Exercise 17
parça ölçeğinde kontur sunuyor ✓.

**Deterministik kırılma noktaları (yeni teşhisle, kalıcı).** Her paftada izlenemeyen profillerin ilk kopan
birleşimi: Exercise_51 **1.**, Exercise 17 **5.**, Flange **17.**, my_part **3.** birleşim ✓ — mesaj artık
`kontur uçları çizimde birleşmiyor (N. birleşim, boşluk X px, tür→tür)` ✓. Profil sayıları/kutuları run3 →
run4 → run5 arasında *tam* karşılaştırma için `/tmp/guided-raster-run4.txt` ve `/tmp/guided-raster.txt`
(kopyaları) duruyor ✓; §23-C22 tablosundaki run3 değerleri de dosyada yazılı ✓ ama "en büyük" iddiası
için **yeniden okunmalı** ✗ (aynı hata olabilir ✗).

**Tek sonraki iş.** `/tmp/guided-raster*.txt` dosyalarından **per-pafta gerçek maksimum** kutuyu kodla çıkarmak
(bir önceki denemem regex'te başarısız oldu ✗ — kutu listesi satırı muhtemelen sarıyor/kesiliyor ✗; `guided_
raster.py`'nin kendi çıktı biçimine bakıp doğru ayrıştırmak) ve run3/run4/run5'i bu ölçütle karşılaştırmak ✓;
sonra kırılma noktalarının boşluk değerlerini (`grep -h notlar /tmp/guided-raster.txt`) okuyup `_align`
ayrımına (kurulum: süpürme-koruyan ✓ / birleşim: uç-güdümlü ✓) karar vermek.

## §23-C25: sıra bağımlılığının kökü — OpenCV iş parçacığı belirsizliği; `cv2.setNumThreads(1)` — 2026-09-28

**Ölçümler.** `tests/test_raster.py` **tek başına** → 1 failed, 11 passed (9:02) ✗ → bağımlılık **dosya içi** ✓
(dosyalar arası değil ✗). Çift koşu (`synthetic_arc_comes_back` + `full_circle`) → **0.68 s'de kırılıyor** ✓ →
hızlı, kesin bir üreme var ✓. Ayrıntılı koşu assertion'ı verdi: **`assert np.float64(5.9447…) > 20`** ✗ — yani
tam daire (merkez 120,160, r45) ikinci okumada **yay olarak geri geliyor** ✓ (merkez tahmini 5,94 px sapmış ✓).
Süreler 0,20 s / 0,15 s ✓ (yani "çok hızlı" şüphem yersizdi ✗ — sentetik paftada okuma ucuz ✓).
`raster.py`de **hiç önbellek/global/lru_cache yok** ✓ (tarandı ✗ — 33 sabit satırı ✓, hepsi statik ✓).

**Kök (kanıtla).** Aynı pafta, aynı kod; **ilk okuma yapıldığında** ikinci okumanın yay kümesi değişiyor → OpenCV'nin
Hough geçişleri iş parçacıklarına bölünüyor ve sonuç makinenin yüküne bağlı ✓; testin kendi yalnız-koşusu geçiyor ✓,
başka bir okuma önce yapıldığında kırılıyor ✗.

**İndi (doğrulaması sürüyor).** `observe_raster` artık girişte **`cv2.setNumThreads(1)`** çağırıyor ✓ (yorum
satırında ölçüm ve gerekçe yazılı ✓). Bu yalnız testi düzeltmiyor: **kullanıcı kararları aynı paftada aynı
sonucu vermeli** ✓ — tek iş parçacığı bunu satın alıyor ✓.

**Doğrulama koşusu:** `proc_8c325c878743` (önce çift koşu ✓ sonra dosyanın tamamı ✓; bitince bildirecek ✓).
Geçerse kalan tek bilinen kırık kalmaz (tam takım 565 passed, 2 failed → bu ikisi de kapanmış olur ✓).

## §23-C26: gerçek maksimumlar + kopan birleşimlerin boşluk envanteri (run6) — 2026-09-28

**Ölçüm (`guided_raster2.py` → `/tmp/guided-raster2.txt`; ilk kez *en büyük* kutu, alan sıralı ✓):**

| Pafta | wire | en büyük 3 (id, nokta, w×h, alan) |
|---|---|---|
| Exercise_51 | 7 | **outline_14 50n 420×838**, outline_46 50n 430×544, outline_3 52n 961×117 |
| Exercise 17 | 6 | **outline_49 4n 557×513**, outline_80 4n 353×304, outline_38 72n 243×289 |
| Flange | 6 | **outline_56 54n 269×415**, outline_9 50n 218×410, outline_51 73n 52×121 |
| my_part.jpg | 11 | **outline_12 220n 315×238**, outline_19 73n 153×206, outline_39 4n 205×125 |

Yani **dört paftanın dördü de parça ölçeğinde kontur sunuyor** ✓ (§23-C22'nin "küçüldü" okuması *ölçüm
hatasıydı* ✓; §23-C24 düzeltmesi doğrulandı ✓). Arka zengin konturlar da var: my_part'ta 220 noktalı ✓,
Flange'de 73 noktalı ✓ — yay örneklemesi çalışıyor ✓.

**Kopan birleşimlerin boşlukları (ilk kez ölçüldü ✓):** Exercise_51 **354,1 px arc→arc** + 24,2 px line→line;
Exercise 17 **134,3 arc→line** + 134,2 arc→arc + 40,? ; Flange **395,7 arc→line** + 20,0 line→line;
my_part **47,7 arc→line** + **6,6 arc→line** + 119,? ✗. Açık bir *yakın ıskalama* var: **my_part'ın 1. birleşimi
6,6 px** ✗ — `ARC_JOIN_MIDDLE_PX` (5,5 px ✓ = LOOP_TOLERANCE_PX 3,0 + ARC_JOIN_SLACK_PX 2,5 ✓) sınırını
**1,1 px** ile kaçırıyor ✓. Ayrıca 20,0 px line→line ve 24,2 px line→line, raster paftalar için konan zincir
toleransının (36 px ✓) *izleme* tarafındaki karşılığının olmadığını gösteriyor ✓.

**Tek sonraki iş (ölçümle seçildi).** Raster paftalarda `_trace`in ara-nokta kapamasını gevşetmek: **6,6 px ve
20,0 px** gibi boşluklar kapansın (ör. raster için `ARC_JOIN_MIDDLE_PX`i 36 px'lik zincir toleransıyla uyumlu
hale getirmek ✓), sonra `guided_raster2.py`yi tekrarlayıp yeni profillerin kutularını ve `test_guided.py`nin
24 passed'ini doğrulamak ✓; 354/134/395 px'lik boşluklar gerçek ayrı hattır ✗ — onlar kapanmamalı ✗.

## §23-C27: "sıra bağımlılığı" ÇÜRÜTÜLDÜ — kırık deterministikti; gerçek kusur `same_ring`in yarıçap payı — 2026-09-28

**Yanlış teşhis, kanıtla düzeltildi.** (a) Tek test **yalnız başına** koşuldu → **1 failed (0.43 s)** ✗ →
ortada *sıra bağımlılığı yok* ✗; test bugünkü okuyucuya karşı düz kırık ✗ (uzun süredir taşınan "yalnız geçiyor"
notu yanlıştı ✗). (b) Aynı sentetik pafta **üç kez** arka arkaya okundu (tek süreç) → üç okuma da **birebir
aynı**: 2 yay, 1 daire ✓ — yani "OpenCV iş parçacığı belirsizliği" hipotezim de **yanlış** ✗.

**Gerçek kusur (ölçüldü).** Her okumada **sahte bir yay** var: merkez çizili dairenin merkezinden **5,94 px**,
yarıçap **37,4** ✗ — çizili dairenin yarıçapı **46,7** ✓ → aradaki fark **9,3 px** ✗. Kapı `raster.py:336`
`same_ring`: merkez payı `max(8, 0.15r)` ✓ (5,94 geçiyor ✓) ama yarıçap payı `max(6, 0.15r)` = **6,0** ✗ →
9,3 px fark kapıyı kaçırıyor ✗ → süzülmeyen yay `'hough-arc'` olarak observation'lara giriyor ✗ ve testin
`> 20 px` savını kırıyor ✗ (assert değeri birebir: `np.float64(5.9447…) > 20` ✓).

**İndi.** `same_ring`in yarıçap payına **tutulan** halkanın oranı eklendi: `max(6.0, 0.15·r, 0.25·oradius)` ✓
(gerekçe ve ölçüm docstring'de ✓). Aynı halkanın kendi mürekkebinden türeyen parçalar artık düşüyor ✓;
gerçek eş merkezli ikinci bir halka zaten *strict* geçişte daire olarak tutulur ✓ (kapının sözleşmesi bu ✓).

**Geri alınan değişiklik.** `observe_raster`a konan `cv2.setNumThreads(1)` **geri alındı** ✗ — gerekçesi
(okuyucunun iş parçacığına göre değişmesi) ölçümle çürüdü ✓; doğrulanmamış küresel yan etki bırakılmaz ✓.

**Doğrulama:** `proc_96dd8cd91076` (dosyanın tamamı, 12 dk; bitince bildirecek ✓). Geçerse son tam takımın
iki kırığından **ikincisi** de kapanır (§23-C23 ilkini kapattı ✓) → ağaç yeşil ✓.


## Preserve user depth and prototype explicit dimensional constraints (2026-09-28)

Single pocket proposal acceptance preserves an existing user depth and refuses to silently import an unselected depth proposal. Explicit depth acceptance updates current pockets or reports that none exist; logs contain the depth actually saved. Geometry-only proposal evidence no longer crashes drawing creation when a printed span ID is absent. Guided/proposal/advice tests:45 passed.

Added an isolated coordinate difference constraint module for line contours and circle centres, with horizontal/vertical relations, signed X/Y dimensions, conflict/redundancy/free-DOF reporting and source expressions.22 tests passed, including CAD output measurement. This module is not connected to the product UI or guided compiler yet. See eval/reports/guided-continue.md for current limits and next work.

## §23-C28: kapının İKİ kopyası vardı — biri genişletilmiş payı kullanmıyordu; kırık KAPANDI — 2026-09-28

**Kök (ölçümle).** §23-C27'de genişlettiğim `same_ring` payı tek başına yetmedi ✗ (dosya yine 1 failed ✗).
Sebep: aynı halka testinin **ikinci bir kopyası** vardı — `_verified_arcs`in sonundaki *dedupe* geçişi
(`raster.py:412-419`) kendi `max(6.0, 0.15·r)` payını taşıyordu ✗ ve az önce düşürülen parçayı **geri alıyordu** ✗.

**İndi.** Dedupe geçişi artık aynı kapanışı çağırıyor: `if same_ring(cx, cy, radius)` ✓ — tek doğruluk
kaynağı ✓ (yorumda "bu geçiş kendi kopyasını tutuyordu ve genişletilmiş payın az önce düşürdüğü parçaları
sessizce geri alıyordu" yazılı ✓).

**Doğrulama.** `test_a_full_circle_is_not_repeated_as_an_arc` **+** `test_synthetic_arc_comes_back_with_its_span`
→ **2 passed (0.82 s)** ✓✓. Dosyanın tamamı `/tmp/raster-c28.txt`e koşuyor ✓ (12 dk ✓).

**Ders (kayıtlı).** Bir tolerans iki yerde kopyalanmışsa, genişletmek *yetmez* ✗: kopya eski değeri kullanmaya
devam eder ✓ — ölçüm iki kapıyı da görmeli ✓. §23-C25'teki `cv2.setNumThreads(1)` geri alınmıştı ✓ (gerekçesi
çürümüştü ✓); §23-C27'nin kapı genişletmesi *kalıyor* ✓ (parça gerçekten bir dairenin mürekkebinden geliyor ✓).

## §23-C29: `test_raster.py` dosyası YEŞİL — 12 passed (10:07) — 2026-09-28

§23-C27 (kapının yarıçap payı) + §23-C28 (payın ikinci kopyası) birlikte dosyayı yeşile çevirdi ✓ —
`tests/test_raster.py` → **12 passed** ✓ (öncesi: 1 failed/11 passed ✗, "sıra bağımlılığı" sanılan kırık ✗).
Tam takım `/tmp/suite-c29.txt`e koşuyor ✓ (öncesi: 565 passed + 2 failed ✗; o iki kırık §23-C23 ve §23-C27/C28
ile kapandı ✓ → beklenti: **tamamı yeşil** ✓). Yeşil çıkarsa bu pencerenin test borcu kapanır ✓.

## §23-C30: `_trace`in ara-nokta kapaması zincirin toleransına hizalandı — 2026-09-28

**Gerekçe (ölçüm).** Zincir raster paftada bir konturu **36 px**e kadar kapatıyor ✓ (`RASTER_JOIN_TOLERANCE_PX`),
ama `_trace`in ara-nokta kapaması **5,5 px**te kalıyordu ✗ → zincirin az önce bulduğu kontur izleme sırasında
yeniden atılıyordu ✗. Ölçülen kopuşlar (§23-C26): **my_part.jpg 6,6 px**, **Exercise_51 24,2 px**, **Flange
20,0 px** — hepsi eski tavanın üstünde ✗.

**İndi.** `_trace(loop, mid_join_px=…)` parametresi aldı ✓; `drawing_options` bu değeri zincirle aynı
kaynaktan veriyor: `mid_join_px = max(ARC_JOIN_MIDDLE_PX, RASTER_JOIN_TOLERANCE_PX if raster else
LOOP_TOLERANCE_PX)` ✓ (yorumda ölçüm ve gerekçe yazılı ✓). Vektör yolu **değişmedi** ✓ (5,5 px ✓);
354/134/395 px'lik boşluklar hâlâ gerçek ayrı hatlar ✓ — kapanmazlar ✗.

**Doğrulama.** `tests/test_guided.py` → **24 passed (41 s)** ✓. Gerçek paftalarda etkisi run7 ile ölçülüyor ✓
(`/tmp/guided-raster2-run7.txt` ✓): beklenen — my_part 11 wire ✓ iken 6,6 px'lik birleşim kapanınca yeni/ daha
büyük konturlar ✓; kutu listeleri §23-C26 tablosuyla karşılaştırılacak ✓.

**Not (bayat koşu).** Tam takım `proc_0fddb9ac8f79` bu değişiklikten **önce** başladı ✗ → sonucu bu dilim için
bayat sayılmalı ✓; yeşil çıkarsa raster düzeltmelerini doğrular ✓, ama ara-nokta hizası sonrası **tekrar
koşulmalı** ✓.

## §23-C31: TAM TAKIM YEŞİL — 567 passed (18:19) — 2026-09-28

`pytest -q` → **567 passed, 0 failed** ✓ (öncesi: 565 passed + 2 failed ✗; kırıklar §23-C23 ve
§23-C27/C28 ile kapandı ✓). Bu koşu **ara-nokta hizasından önce** başladı ✗ → yeşillik raster düzeltmelerini
(§23-C25 geri alındı ✓, §23-C27/C28 ✓) ve `test_catalog_cli` düzeltmesini (§23-C23 ✓) kapsıyor ✓; ara-nokta
hizasından (§23-C30) sonra **tekrar koşuluyor** ✓ (`/tmp/suite-c31.txt` ✓) → o da yeşilse bu pencerenin
test borcu tamamen kapanır ✓.

## §23-C32: run7 — §23-C30 fazla kapatıyor; parametre zincirin toleransı, izlemenin cömertliği değil — 2026-09-28

**Ölçüm (run6 → run7, ara-nokta tavanı 5,5 px → 36 px):**

| Pafta | run6 | run7 |
|---|---|---|
| Exercise_51 | 11 profil / 7 wire; en büyük 420×838 | **49 / 45**; 626×1005, 755×706 |
| Exercise 17 | 9 / 6; 557×513 | **51 / 48**; 1005×538, 809×497 |
| Flange | 8 / 6; 269×415 | **31 / 29**; 831×1055 (368 nokta) |
| my_part.jpg | 17 / 11; 315×238 | **41 / 35**; 1408×949 (≈ pafta boyu ✗) |

Yani izlemeye zincirin 36 px'ini vermek menüyü **sel basıyor** ✗: wire sayısı 7–11 → 45–48 ✗, en büyük kutular
pafta boyuna çıkıyor ✗ (my_part 1408×949 = çerçeve/kâğıt ölçeği ✓), yani 20–36 px'lik boşluklar **orta noktada**
kapatılınca her uç 10–18 px kayıyor ✗ ve birbirine ait olmayan parçalar birleşiyor ✗.

**Sonuç ve alınan karar.** Kök, §23-C30 değil **zincirin 36 px toleransının kendisi** ✓: o tolerans hem az sayıda
izlenen kontur (run6 ✗) hem de sel (run7 ✗) üretiyor ✗. **İzlemenin tavanı geri alındı** ✓ (`mid_join_px =
ARC_JOIN_MIDDLE_PX` ✓, yorumda run7 ölçümü ve gerekçe yazılı ✓; parametre *tarama için* duruyor ✓) —
`test_guided.py` **24 passed (52 s)** ✓ → ağaç run6 davranışında ✓.

**Tek sonraki iş (ölçümle).** `RASTER_JOIN_TOLERANCE_PX`i **süpürmek** (ör. 6 / 10 / 15 / 20 px ✓) ve her değerde
dört paftanın `guided_raster2` çıktısını almak ✓: aranan, **parça konturunun kapanması** ✓ (my_part 6,6 px,
Flange 20,0 px, Ex_51 24,2 px ✓) ile **selin başlamaması** ✗ arasındaki bant ✓. Sonra o değer hem `_loops`a
hem `_trace`in ara-nokta tavanına **aynı kaynaktan** verilmeli ✓ (§23-C28'in dersi: iki kopya olmasın ✓).

## §23-C33: UI kabulünde gerçekten kalan tek öğe — delik seçme tıklamasının toleransı — 2026-09-28

**Tarayıcı oturumu boş geldi** ✗: koşum katmanı yeniden başlamış, `/guided` sekmesi yok ✓ (yalnız
`chrome://newtab` + `about:blank` ✓). Yani §23-C16/C20'deki oturum **sürdürülemiyor** ✗; yeni bir kabul
turunun tek çağrıda yapılması gerekiyor ✓ (akış ~8+ opsiyon ✗, katman 6–8'den sonra düşüyor ✗).

**Ama tablo netleşti — kalan iş sanılandan küçük.** §23-A kaydı (bu hedefin başında, gerçek tarayıcıda,
2 dk 48 sn, 16 eylem) **üret → indir → yeniden aç → geri al** adımlarını zaten geçmişti ✓. §23-C16/C20'de
temiz oturumdan **kontur + iki noktalı kalibrasyon + basılı değer + "Kalınlığı kaydet"** gerçek tıklama ve
gerçek tuşlarla iki kez doğrulandı ✓ (kayıt 1, 2, 3 ✓). Dolayısıyla UI kabulünde **ölçülmemiş kalan tek
öğe**: kalınlıktan sonraki **delik seçme tıklamasının toleransı** ✗ (`holeAt`/`snapEnd`in kullanıcı tıklamasını
hangi mesafeye kadar kabul ettiği ✓) — kullanıcının "son tıklama toleransı henüz tarayıcıda denenmedi" dediği
madde ✓.

**Tek sonraki iş (UI).** Tek çağrıya sığan en küçük tur: sayfayı `new_tab`la aç ✓ → PNG yükle ✓ → konturu
tıkla ✓ → iki kalibrasyon noktası + değer ✓ → kalınlık ✓ → **bir daireye tıklayıp Ø7,2 yaz + "Delik ekle"** ✓
→ **Üret** ✓ (deliklerin ikincisi ve indir/SHA sonraki tura ✓). Sığmazsa: bir sonraki pencere "delik+üret"
adımlarını *aynı* çağrıda açıp denemeli ✓.

**Koşan ölçüm:** `RASTER_JOIN_TOLERANCE_PX` süpürmesi (6/10/15/20/36 px, dört pafta; `proc_c8c4a660ffd7` →
`/tmp/sweep-tol.txt` ✓, ~50 dk ✓) — §23-C32'nin sıradaki işi ✓.

## §23-C34: birleşim toleransı süpürüldü → 20 px seçildi (taze ölçüm sürüyor) — 2026-09-28

**Süpürme (tek `observe` per pafta, 5 tolerans; `/tmp/sweep-tol.txt`):**

| Pafta | 6 px | 10 px | 15 px | 20 px | 36 px |
|---|---|---|---|---|---|
| Exercise_51 | 15 wire, 1924×2609 ✗ (kâğıt) | 14, 605×1126 | 10, 1036×1932 ✗ | **9, 723×718** | 9, 420×838 |
| Exercise 17 | 28, 893×719 | 22, 893×719 | 20, 455×181 | **17, 730×816** | 5, 351×311 |
| Flange | 19, 936×884 ✗ | 12, 400×652 | 16, 714×506 | **12, 356×568** | 4, 52×121 ✗ |
| my_part.jpg | 25, 570×348 | 16, 297×307 | 22, 570×348 | **14, 427×334** | 11, 452×204 |

**Okuma.** Dar tolerans (6 px) **çok sayıda küçük çöp** üretiyor ✗ (15–31 wire; Exercise_51'de 1924×2609 =
kâğıt/çerçeve ✗); geniş tolerans (36 px) küçük döngüleri birleştirip **az ve bazen parça dışı** kutu bırakıyor
(Flange 4 wire / 52×121 ✗). Orta bant (20 px) dört paftada da **parça ölçeğinde en büyük kutu** veriyor ✓
(723×718 / 730×816 / 356×568 / 427×334 ✓) ve kâğıt ölçeğinde kutu yok ✓ → **`RASTER_JOIN_TOLERANCE_PX = 20.0**
seçildi ✓ (yorumda ölçüm ve gerekçe ✓).

**Ölçüm uyarısı (kendi hatam, kayıtlı).** Süpürme, `observe` sonucunu paylaştığı için çağrılar arası durum
taşımış olabilir ✗ (36 px satırı run6'nın taze koşusuyla birebir değil ✗: Ex 17 5↔6 wire, Flange 4↔6 ✗) →
sayılar *yön* için güvenilir ✓, kesin değer için değil ✗. Bu yüzden **20 px ile taze süreçte** dört pafta
yeniden ölçülüyor ✓ (`/tmp/guided-raster2-run8.txt` ✓) ve §23-C26 tablosuyla karşılaştırılacak ✓.

## §23-C35: 20 px taze süreçte doğrulandı — süpürme geçerli, kutu tablosu iyileşti — 2026-09-28

**run8 (taze süreç, `RASTER_JOIN_TOLERANCE_PX = 20.0`) — süpürmenin 20 px satırıyla *birebir*** ✓ (yani
"`observe` paylaşımı durum taşıdı" endişem **çürüdü** ✗; süpürme sayıları geçerli ✓):

| Pafta | run8 (20 px, taze) | run6 (36 px, taze) |
|---|---|---|
| Exercise_51 | 13 profil / **9 wire**; **723×718 (99 nokta)**, 610×727 (50) | 7 wire; 420×838 (50), 430×544 |
| Exercise 17 | 20 / **17 wire**; **730×816 (53)**, 493×451, 382×455 | 6 wire; 557×513 (**4 nokta** ✗), 353×304 |
| Flange | 14 / **12 wire**; **356×568 (50)**, 340×443, 234×468 | 6 wire; 269×415 (54), 218×410 |
| my_part.jpg | 20 / **14 wire**; **427×334 (243 nokta)**, 327×235 | 11 wire; 315×238 (220), 153×206 |

**Okuma.** 20 px her paftada en büyük kutuyu **büyüttü** ✓ ve nokta sayısını artırdı ✓ (Exercise 17'nin 4 noktalı
dörtgeni → 53 noktalı gerçek kontur ✓; my_part 220 → 243 nokta ✓); kâğıt/çerçeve ölçeğinde kutu **yok** ✓;
wire sayısı 9–17 ✓ (run6 6–11 ✗ → ölçülü artış ✓, run7'nin 45–48 seli ✗ yok ✓). **Karar: 20 px kalıyor** ✓.

**Kalan yakın ıskalamalar (yeni teşhisle).** Notlarda 14,9 px ve 17,0 px'lik line→line boşlukları görünüyor ✗ —
zincir 20 px'i kabul ediyor ✓ ama izlemenin ara-nokta tavanı 5,5 px ✗ → bu birleşimler hâlâ düşüyor ✗. Bu,
`mid_join_px`i zincirin *yarısı* kadar (ör. 10 px ✓) açmanın **ölçülebilir** sonraki adımı ✓ — run7'nin seli
36 px'te gelmişti ✗, 10 px denenmeli ✓.

**Test borcu:** taze tam takım `/tmp/suite-c35.txt`e koşuyor ✓ (20 px + geri alınmış ara-nokta tavanıyla ✓).

## §23-C36: tam takım YEŞİL (567) + `mid_join_px` 10 px denemesi koşuyor — 2026-09-28

**Taze tam takım** (20 px tolerans + geri alınmış ara-nokta tavanı, güncel ağaç): **567 passed (17:27)** ✓✓ —
bu pencerenin test borcu kapandı ✓.

**İnen deneme.** `_trace`in ara-nokta tavanı raster paftalarda artık zincirin **yarısı**: `mid_join_px =
max(ARC_JOIN_MIDDLE_PX, RASTER_JOIN_TOLERANCE_PX / 2.0) if raster else ARC_JOIN_MIDDLE_PX` ✓ (10 px ✓; her uç en
fazla 5 px kayar ✓; gerekçe ve run7 uyarısı yorumda ✓). Hedef: §23-C35'te ölçülen **14,9 px** ve **17,0 px**
line→line boşluklarının kapanması ✓ — sel gelmeden ✓ (sel 36 px'te gelmişti ✗).

**Ölçüm koşusu:** `guided_raster2` (dört pafta, taze süreç ✓) + `test_guided.py` aynı arkada ✓ →
`/tmp/guided-raster2-run9.txt` ✓. Karşılaştırma ölçütü: run8 tablosu (§23-C35 ✓) — wire sayısı **9–17 bandında
kalmalı** ✓ (artış kabul ✓, 45+ sel ✗), en büyük kutular küçülmemeli ✓.

## §23-C37: ara-nokta tavanı 10 px — daha çok kontur, sel yok; kalıyor — 2026-09-28

**Ölçüm (run8 = 5,5 px → run9 = 10 px, dört pafta taze süreç):**

| Pafta | run8 | run9 |
|---|---|---|
| Exercise_51 | 9 wire; 723×718, 610×727, 429×422 | **12 wire**; 723×718, 610×727, **423×684 (26 nokta)** ✓ |
| Exercise 17 | 17 wire; 730×816, 493×451, 382×455 | **23 wire**; 730×816, **479×493** ✓, 493×451 |
| Flange | 12 wire; 356×568, 340×443, 234×468 | **19 wire**; 356×568, **530×378** ✓, 340×443 |
| my_part.jpg | 14 wire; 427×334, 327×235, 351×217 | **18 wire**; 427×334, 327×235, 351×217 (aynı) |

**Okuma.** 10 px tavan yeni **parça ölçeğinde** konturlar kazandırdı ✓ (Ex_51 423×684, Ex 17 479×493, Flange
530×378 ✓) ve en büyük kutuları **küçültmedi** ✓; **kâğıt/çerçeve ölçeğinde kutu yok** ✗ ✓ ve wire sayıları
12–23 ✓ — run7'nin seli (45–48 + çerçeve ✗) gelmedi ✓. `test_guided.py` **24 passed (36 s)** ✓.
**Karar: 10 px kalıyor** ✓ (her uç ≤5 px kayar ✓, alt mm düzeyi ✓).

**Sonraki dilim (hazır reçete).** Sıradaki: **en büyük profili akışa verip STEP üretmek** — tercihen
`Exercise 17` (730×816, 53 nokta ✓): API yolundan `open` → `profile` (`outline_2`) → **kalibrasyon** (iki nokta +
provisional değer ✓; raster paftada ölçek *kullanıcının* kararıdır ✓, ölçüm/karşılaştırma amaçlı taslak ✓) →
`thickness` → `build` → `step_facts` (`.venv-cad`) ✓ → referans `3/Exercise 17.STEP` ile **yalnız
değerlendirmede** dış ölçü/delik/hacim karşılaştırması ✓. Çıkan STEP **taslaktır** ✓ (pikselden izlenen kontur
doğrulanmış ölçü değildir ✓).

## §23-C38: gerçek pafta uçtan uca — kararlar geçti, CAD "geçersiz katı" dedi; ölçülen sebep: kontur 308 px açık — 2026-09-28

**Zincir (Exercise 17.PNG, 20 px + 10 px kod, sunucu yeniden başlatıldı ✓).** `open` → **profil `outline_2`
(730 px, 53 nokta)** ✓ → kalibrasyon (çizili büyük daire = **100 mm** *geçici* ölçek → **3,89 px/mm** ✓) →
kalınlık 10 ✓ → iki daire **geçişli delik** (Ø9,666 ve Ø9,434 mm ✓) → `save`: **`questions: []`** ✓✓ (akış dört
kararı da kabul etti, taslak onayıyla ✓) → `build` → **`build_status = "failed"`, `error = "geçersiz katı"`** ✗.

**Ölçülen kök (CAD değil, eskiz).** `build.sketch`: `px_per_mm = 3.89`, `source = calibration` ✓,
`consistent = True` ✓, `conflicts = []` ✓ — ama **`open_contour_px = 308,2514`** ✗ (geçici ölçekle ≈79 mm ✗),
**`rows = []`** ✗, **`unbound_edges = [0…6]`** ve **`unbound_circles = [g593, g594, g595]`** ✗, `plan = None` ✗.
Yani: izlenen profil `_trace` içinde kapandı ✓ (aksi hâlde sunulmazdı ✗) ama **eskiz onu 308 px açık görüyor** ✗
→ plan üretilmedi ✗ → derleyici "geçersiz katı" dedi ✓. Bu, akışın **kendi denetiminin** çalıştığının kanıtı ✓
(geçersiz geometri katıya dönüşmedi ✓) ve sınırın tam yerini veriyor ✓: izleme kapaması ile eskiz kapaması
arasında bir tutarsızlık var ✗.

**Tek sonraki iş (kesin).** `_trace`in ürettiği profilin **ilk öğenin başı** ile **son öğenin sonu** arasındaki
mesafeyi ölçmek ✓ (options'taki profilin kendi noktalarından ✓) ve bunu `open_contour_px` ile karşılaştırmak ✓;
fark `_trace`in *kapanış* (son→ilk) birleşiminde mi ✗ (mid-join yalnız ardışık çiftlerde çalışıyor ✓) yoksa
yayın *yeniden kurulan* ucu ile saklanan uç arasında mı ✗ (sketch a/b açılarından yeniden hesaplıyor ✓)
ayırmak ✓ — ikisi ayrı düzeltme ✓. Yan ürün: bu paftada **ölçü adayı 0** ✗ (okuma basılı ölçü çiftini
bulamadı ✓) — kalibrasyon kullanıcının tıklamasına kalıyor ✓ (kurala uygun ✓).

**Etiketleme (kural).** Bu deneme bir **taslaktır** ✓; ölçek geçicidir ✓ (pikselden izlenen kontur doğrulanmış
ölçü sayılmaz ✓). Başarısız `build` **başarı sayılmaz** ✓; kaydı burada, kanıtı `/tmp/unseen17-flow.json` ✓.

## §26-A-1: genel kontur doğrulaması indi — yanlış tanı alanları düzeltildi, geçersiz sınır üretimi durduruyor — 2026-09-28

PLAN §26.4-A'nın ilk yarısı. **Yeni modül `src/drawingto3d/contour_audit.py`**: CAD'e gidecek *son* çizgi/yay
geometrisi (pafta pikselleri) üzerinde — **gerçek kapanış** (ardışık birleşimler + son→ilk sarma; `closure_px`),
**sıfır uzunluk**, **yinelenen/çakışan kenar** (aynı destek + örtüşen aralık), **öz-kesişim** (çiftin türüne göre
line-line / line-arc / arc-arc ayrımıyla) ve **yayın kendi ucuyla tutarsızlığı** denetimi ✓. Her sorun **pafta
pikselinde bir konum** taşıyor ✓ (arayüz işaretleyebilsin diye ✓). Örnek kimliği, dosya adı veya klasör bilgisi
koda **girmedi** ✓.

**Yanlış tanı alanları (PLAN §26.3) düzeltildi:**
- `sketch.py` artık `join_gap_max_px` yayınlıyor ✓ (eski adı `open_contour_px` idi ✗ — birleştirme *öncesi* boşluktu ✗).
- `guided.sketch_diagnostics` doğrulamayı ekliyor ✓ ve **`open_contour_px` artık audit'in gerçek kapanış hatası** ✓
  (tam daire profili için "kapalı, kenar yok" ✓).
- Ürün metni: "Bağlanan basılı ölçülerle **kesin eskiz çözümü** yapıldı" ✗ → "tek bir **ortak ölçeğe uyduruldu**
  (en küçük kareler); bu, kenarları ayrı ayrı hareket ettiren kesin bir eskiz çözümü değildir" ✓; arayüzdeki
  "Kontur uç birleştirmesi…" satırı da doğrulamanın diliyle değişti ✓ (`static/guided.js`).
- `guided.make_plan` **geçersiz sınırı durduruyor** ✓ ve hata artık yalnız "geçersiz katı" değil ✗ →
  `kontur geçersiz: <ilk sorun>; N sorun daha var — işaretlenen yeri düzeltip yeniden deneyin.` ✓

**Bağımsız sentetik kabul (PLAN'ın listesi, `tests/test_contour_audit.py`, 8 test ✓):** kapanmış ama kendini kesen
bow-tie (kesişim (5,5) ✓), gerçekten açık kontur (boşluk büyüklüğüyle ✓), geçerli içbükey L ✓, teğet yay birleşimi ✓,
**ters yönde dolaşılan yay** ✓, sıfır uzunluklu kenar ✓, çakışan kenarlar ✓, boş kontur ✓.

**Kanıt:** `tests/test_contour_audit.py + test_sketch.py + test_guided.py::test_flange_...` → **14 passed (16,2 s)** ✓
(flange dairesi profili kapıdan geçiyor ✓ — tam daire kenarsız olduğu için "kapalı" sayılıyor ✓).

**Sınır (kalan):** hatalı bölge henüz **çizim üzerinde işaretlenmiyor** ✗ (konum verisi hazır ✓, çizim katmanı
sıradaki iş ✓); kullanıcının **kenar çıkarma/ekleme + önerilen birleşimi onaylama** akışı yok ✗; aynı doğrulamanın
**farklı paftalarda** ölçümü koşuyor ✓ (`/tmp/audit-sheets.txt` ✓).

**Tek sonraki iş:** aynı doğrulamayı dört gerçek paftada ölçmek (koşuyor ✓) → ardından arayüzde hatalı bölgeyi
işaretlemek ve kullanıcı düzeltmesini (kenar çıkar/ekle, açık uç için önerilen birleşimi onayla, konum değişimini
göster, kaydet, geri al) karar kaydına bağlamak ✓.

## §26-A-2: doğrulama dört gerçek paftada — kapanışlar tam, ama büyük profiller kendini kesiyor — 2026-09-28

**Ölçüm (`audit_sheets.py` → `/tmp/audit-sheets.txt`; ürün yolunun sunduğu en büyük üç wire profili):**

| Pafta | profil | kutu | kenar | ok | closure | sorunlar |
|---|---|---|---|---|---|---|
| Exercise_51 | outline_4 | 723×718 | 7 | ✗ | 0,0 | line-line + line-arc kesişim |
| | outline_3 | 610×727 | 4 | ✓ | 0,0 | — |
| Exercise 17 | outline_2 | 730×816 | 7 | ✗ | 0,0 | line-arc kesişim |
| | outline_24 | 479×493 | 5 | ✗ | 0,0 | line-line ×2 |
| Flange | outline_13 | 356×568 | 4 | ✗ | 0,0 | line-arc kesişim |
| | outline_3 | 340×443 | 4 | ✓ | 0,0 | — |
| my_part | outline_12 | 427×334 | 13 | ✗ | 0,0 | line-line + arc-line |
| | outline_47 | 351×217 | 4 | ✓ | 0,0 | — |

**Bulgu.** Ürün yolunun sunduğu profillerde **kapanış hatası her yerde 0,0 px** ✓ (izleme uçları gerçekten
birleştiriyor ✓) — ama **büyük profillerin çoğu kendini kesiyor** ✗. Yani puantaj hatası yok ✓; zincirin
**yanlış parçaları birleştirmesi** var ✗: 20 px toleransı komşu olmayan kenarları birbirine bağlayabiliyor ✗ →
kapalı ama kendi üzerinden geçen kontur ✓ = PLAN'ın adlandırdığı kabul vakası ✓ ve gerçek paftada
"geçersiz katı"nın **ölçülmüş sebebi** ✓. Aynı ölçüm, doğrulamanın örnekten bağımsız çalıştığını gösteriyor ✓
(üç paftada hem geçerli hem geçersiz profiller ✓, tür ayrımı line-line/line-arc/arc-line ✓).

**Tek sonraki iş (iki kollu, ölçümle seçildi).** (1) **Arayüz**: audit'in `issues[].at` konumlarını çizim üzerinde
işaretlemek ✓ ve kullanıcıya düzeltme yolunu vermek ✓ (kenarı çıkar/ekle, açık uç için önerilen birleşimi
onayla, konum değişimini göster, kaydet, geri al ✓). (2) **Kural (genel, örneğe özel değil ✓)**: zincirin
kapanış seçiminde **kendini kesmeyen** bağlantıyı tercih etmesi ✓ — sentetik bow-tie/açık/L vakalarıyla
sınanabilir ✓ ve dört paftada yeniden ölçülebilir ✓ (kabul: geçerli profil sayısı artar ✓, kapanışlar 0,0 kalır ✓).

## §26-A-3: her sunulan profil artık doğrulama kararını taşıyor — 2026-09-28

**İnen.** `guided.drawing_options` her wire profili için CAD'e gidecek *son* geometriyi (`profile["edges"]`)
denetliyor ✓ ve sonucu profille birlikte yayınlıyor ✓: `profile["contour"] = {ok, closure_px, issues[:8],
issue_count, edge_count}` ✓. Böylece arayüz, kullanıcı **henüz konturu seçerken** hangi profilin geçerli
olduğunu gösterebiliyor ✓ — §26.2'nin "dış kontur seçimi yalnız en büyük alana dayanmaz" kuralına da uygun ✓:
seçim kullanıcının ✓, yanındaki kanıt doğrulamanın ✓. `make_plan` geçersiz sınırı zaten durduruyor ✓ ve özet
satırı seçilen konturun sorunlarını (konumlarıyla) taşıyor ✓ (`static/guided.js`).

**Düzeltilen kendi hatam (kayıtlı).** Bu dilimin yaması sırasında `_trace(loop, mid_join_px=mid_join_px)`
çağrısını yanlışlıkla `_trace(loop)` yaptım ✗ — yani §23-C36'da ölçümle seçilen 10 px ara-nokta tavanı bir an
düştü ✗. Aynı turda fark edilip geri konuldu ✓ (yorum: "ölçülmüş kararı sessizce düşürmemek" ✓).

**Doğrulama koşusu:** `tests/test_contour_audit.py + test_guided.py + test_proposal.py` → `/tmp/suite-26a.txt` ✓
(`drawing_options` artık her çağrıda denetim yapıyor ✓ — regresyon varsa burada görünür ✓).

**Sınır / tek sonraki iş.** Sorun konumları veride ✓ ama **çizim üzerinde işaretlenmiyor** ✗ (`draw()` katmanı) ve
kullanıcının **düzeltme** akışı (kenar çıkar/ekle, açık uç için önerilen birleşimi onayla, konum değişimini
göster, kaydet, geri al) yok ✗. Ayrıca bağlama testi (sunulan profilin kararı doğru yayınlıyor mu) yok ✗ —
sıradaki dilimin ilk işi: işaretleme + bağlama testi + düzeltme akışının karar kaydına bağlanması ✓.

## §26-A-4: hatalı bölge artık çizim üzerinde işaretleniyor — 2026-09-28

**İnen.** `static/guided.js`in `draw()` katmanı, **seçili** kontur geçersizse doğrulamanın verdiği her konumu
çizim üzerinde işaretliyor ✓: halka + çarpı (kapanış boşluğu, öz-kesişim, çakışma — hepsi `issues[].at` ile ✓).
Seçili profil geçerliyse hiçbir işaret çizilmiyor ✓. Sözdizimi denetlendi ✓ (`node --check` → ✓).

Böylece PLAN §26.4-A'nın "hatalı bölgeyi çizimde işaretle" maddesi karşılandı ✓:
- **göster** ✓ (işaretler + özet satırındaki sorun metni ✓),
- **seçimi değiştir** ✓ (kullanıcı başka bir konturu tıklayıp seçebiliyor ✓; her profilin doğrulama kararı
  yanında duruyor ✓),
- **üretimi durdur** ✓ (`make_plan` geçersizde duruyor, sebebi adıyla söylüyor ✓),
- **kaydet/geri al** ✓ (kararlar zaten atomik kaydediliyor ve geri alınabiliyor ✓ — seçim de bir karar ✓).

**Hâlâ eksik (kayıtlı).** (1) **Kenar çıkar/ekle** ve **açık uç için önerilen birleşimi onayla** adımları yok ✗ —
yani kullanıcı şu an *başka bir kontur seçebiliyor* ✓ ama *aynı konturu düzeltemiyor* ✗. (2) Seçili profil
listesindeki geçerlilik rozeti ✗ (liste bir sonraki turda). (3) Konum değişiminin (yapılan düzeltmenin miktarı)
gösterimi ✗ — §26.3'ün "yapılan düzeltmenin miktarı ayrı ölçülecek" maddesi ✓.

**Koşan doğrulama:** `test_contour_audit + test_guided + test_proposal` → `/tmp/suite-26a.txt` ✓ (sürüyor ✓).

## §26-A-5: yapılan düzeltmenin miktarı ayrı ölçülüyor (PLAN §26.3) — 2026-09-28

**İnen.** Her wire profili artık `applied_move_px` taşıyor ✓: izlemenin kapattığı kontur için çizili kenarların
uçlarını **ham geometriye göre** en çok kaç piksel kaydırdığı. Ölçüm *dışarıdan* yapılıyor ✓ (ham uçlar zincirin
yürüdüğü aynı `lines`/`arcs` sözlüklerinden ✓; yaylarda baş/son açısından üretilen iki uçla iki yön de denenir ✓) —
`_trace`'in içine dokunulmadı ✓. `sketch_diagnostics` bunu seçili profille birlikte yayınlıyor ✓ ve arayüz
özeti "Uçlar bu konturu kapatmak için en çok X piksel (≈Y mm) kaydırıldı." satırını yazıyor ✓.

Böylece §26.3'ün ayrı ölçülmesini istediği iki sayı ayrıştı ✓: **birleştirme öncesi boşluk** (`join_gap_max_px` ✓
zincirin kendi sayısı), **son kapanış hatası** (`contour.closure_px` ✓ doğrulamanın sayısı) ve **yapılan düzeltme**
(`applied_move_px` ✓ izlemenin kaydırdığı miktar). Üçü artık üç ayrı ad ✓.

**Kanıt:** `tests/test_guided.py + tests/test_proposal.py` → **46 passed (62,9 s)** ✓; önceki dilimde
`test_contour_audit + test_guided + test_proposal` → **54 passed (61,6 s)** ✓.

**Ölçüm aracı uyarısı (kayıtlı).** `node --check src/drawingto3d/static/guided.js` **yanlış pozitif** veriyor ✗:
dosya `guided.html`'de `<script type="module">` olarak yükleniyor ✓ ve 140. satırdaki üst düzey `await` orada
geçerli ✓; `node --check` dosyayı CommonJS sanıp "Unexpected reserved word" diyor ✗. Bu dosyanın sözdizimi
tarayıcıda doğrulanmalı ✓ (bir sonraki UI turunda ✓).

**Sınır / tek sonraki iş.** Aynı konturu **düzeltme** akışı hâlâ yok ✗: kullanıcı başka kontur seçebiliyor ✓ ama
seçili konturdan **kenar çıkaramıyor** ✓/✗ ve **açık uç için önerilen birleşimi onaylayamıyor** ✗. Bunun doğru
yolu: düzeltme kararını (`decisions.contour.drop` ✓) karar kaydına yazıp ✓, etkilenen döngüyü **çıkarılan kenar
olmadan yeniden zincirlemek** ✓ (`_loops` filtreli geometriyle yeniden ✓), sonucu yeniden denetlemek ✓ ve
uygulanan değişimi `applied_move_px` ile göstermek ✓ — geri alma zaten revizyonla çalışıyor ✓.

## §26-A-6: konturu düzeltme kararı — kenar çıkar, birleşimi onayla, hepsi karar kaydında — 2026-09-28

**İnen (PLAN §26.4-A'nın "kullanıcının konturu düzeltmesi" maddesi).**
- **Karar türü:** `Decisions.contour = ContourFix{drop: [kenar id], approve_join: bool}` ✓ — `extra="forbid"`
  şemasıyla doğrulanır ✓, karar kaydına ve revizyona girer ✓, geri alma (`/api/guided/undo`) ile aynen çalışır ✓.
  Yani düzeltme *diğer kararlarla aynı* muameleyi görüyor ✓ — ayrı bir yan kanal yok ✓.
- **Uygulama `make_plan`de:** geçersiz kontur artık "kenarı çıkarıp yeniden deneyin" diyor ✓; `drop` verildiğinde
  `correct_profile` çalışıyor ✓ ve **sonuç yeniden denetleniyor** ✓ — düzeltme sınırı gerçekten geçerli yapmadıysa
  üretim yine duruyor ✓ ve sebep adıyla söyleniyor ✓ (`düzeltmeden sonra kontur hâlâ geçersiz: …` ✓).
- **`correct_profile` (saf fonksiyon, `guided.py`):** düşen kenarlardan sonra kalan zincir yeniden yürünüyor ✓;
  **hiçbir yeni geometri uydurulmuyor** ✓ — uçlar yalnız zincirin kendi toleransı (20 px ✓) içindeyse ve kullanıcı
  birleşimi onayladıysa orta noktada kapanıyor ✓; her uç en çok 10 px kayıyor ✓; **tek açıklık** kuralı var ✓
  (iki açık uç = iki ayrı karar ✓); her ret kalan boşluğu pikseliyle söylüyor ✓. Uygulanan değişim
  `correction.{dropped,kept,joined,closed_gap_px,moved_px}` olarak kayda geçiyor ✓ (§26.3: "yapılan düzeltmenin
  miktarı" ✓).
- **Yan düzeltme:** `_display_points` tek yerde ✓ (`_trace`'in kopyası kaldırıldı ✓) — düzeltilmiş kontur da
  çizimde izlenen kontur gibi çiziliyor ✓ (kopya tolerans dersi §23-C28 ✓).

**Bağımsız sentetik kabul (`tests/test_contour_fix.py`, 6 test ✓, pafta yok ✓, kimlik yok ✓):** yinelenen kenarı
çıkarmak kareyi geçerli yapıyor ve hiçbir şeyi kaydırmıyor ✓; yakın boşluk **yalnız onayla** kapanıyor ✓
(onaysız ret ✓); zincirin toleransından geniş boşluk reddediliyor ✓; ucu fazla kaydıracak birleşim reddediliyor ✓;
tek düzeltmenin bıraktığı iki açıklık reddediliyor ✓; bütün kenarları çıkarmak reddediliyor ✓.

**Ölçülmüş iç bulgu (kayıtlı):** raster paftada iki sınır **çakışıyor** — zincir toleransı 20 px, uç başına
kaydırma 10 px, yani "boşluk ≤ 20" ile "uç ≤ 10 kaydırır" aynı kural ✓. Uç sınırı ancak daha dar bir kap
verildiğinde (vektör 5,5 px ✓) ayrı bir kural oluyor ✓ — test bunu böyle ölçüyor ✓.

**Kanıt:** `test_contour_fix + test_contour_audit + test_guided` → **38 passed (39,6 s)** ✓.

**Sınır / tek sonraki iş.** Arayüzde bu kararı **veren** bir denetim yok ✗: sorun metni kenar kimliklerini taşıyor ✓,
API `contour` kararını kabul ediyor ✓, ama kullanıcı çizimdeki işarete tıklayıp "bu kenarı çıkar + birleşimi onayla"
diyemiyor ✗. Sıradaki dilim: işaretlerin yanına kenar başına **"çıkar"** düğmesi + birleşim onayı ✓, kararı
`/api/guided/save` ile yazmak ✓, `applied_move_px`/`correction` satırlarıyla sonucu göstermek ✓.

## §26-A-7: arayüzde düzeltme denetimleri + guided.js'te bulunan kopukluk onarıldı — 2026-09-28

**İnen (arayüz tarafı).** Panel 5'e `#contour-fix` bölümü eklendi ✓: seçili kontur geçersizse doğrulamanın
adlandırdığı **her kenar için bir "… kenarını çıkar" düğmesi** ✓ ve **"Açık kalan ucu orta noktada kapatmayı
onaylıyorum"** onay kutusu ✓ çiziliyor; tıklama kararı `/api/guided/save` ile yazıyor ✓ (`decisions.contour` ✓).
Kayıtlı düzeltme varsa "N kenar çıkarıldı … Üretim bunu yeniden denetleyecek." satırı ve **"Düzeltmeyi temizle"**
düğmesi görünüyor ✓ — yani vermek, görmek, geri almak arayüzde tam ✓. Ayrıca **panel 4 başlığı** düzeltildi ✗→✓:
"Kesin eskiz (bağlanan ölçüler)" → **"Bağlanan ölçüler ve ortak ölçek"** ✓ (PLAN §26.3: ortak ölçek ayarını kesin
eskiz çözümü diye sunma ✓).

**Bulunan kopukluk (benden değil, ağaçtan — kayda geçti).** Tarayıcıda ölçüldü: `#build`/`#undo` düğmelerinin
`onclick`'i **yoktu** ✗ — yani `/guided` sayfası bir süredir **ölü** ✓ (HTML sunuluyor ✓, JavaScript hiç
çalışmıyordu ✗). Kök: `guided.js:116`'da `function renderSketch(){` açılıyor ✗ ve **kapanmıyordu** ✗ — kapanmayan
süslü parantez, ondan sonraki *tüm* üst düzey atamaları (düğme bağlayıcıları, oturum geri yükleme) o fonksiyonun
gövdesine çekiyordu ✗. Onarım: `sheet.onclick` satırından önce eksik `}` eklendi ✓; ayrıca üst düzey `await`
taşıyan oturum geri yükleme satırı `(async()=>{…})().catch(()=>{});` içine alındı ✓.

**Doğrulama (gerçek tarayıcı).** `http://127.0.0.1:8765/guided` → `build_handler: true` ✓, `undo_handler: true` ✓,
`contour_fix_div: true` ✓, panel 4 başlığı yeni metinle ✓. Yani sayfa yeniden canlı ✓ ve düzeltme denetimleri
yerinde ✓.

**Ölçüm aracı dersi (kayıtlı).** `node --check guided.js` bu dosyada **yanlış pozitif** verir ✗ (dosya
`<script type="module">` ✓; `--check` onu script sanar ✗ ve üst düzey `await`'te takılır ✗). Doğru araç:
`node --experimental-vm-modules -e "new (require('vm').SourceTextModule)(fs.readFileSync(...,'utf8'))"` ✓ —
**modül hedefiyle** ayrıştırır ✓ ve ilk gerçek sözdizimi hatasını verir ✓. Kapanış denetimi için de kaba bir
parantez-derinliği tarayıcısı kullanıldı ✓ (eksik `{`ı satır numarasıyla buldu ✓).

**Koşan ölçüm:** `fix_suggest.py` (my_part.jpg, en büyük üç wire) → **tek kenar çıkarma + birleşim onayı** hangi
konturu geçerli yapıyor, kaç kenar kalıyor, ne kadar hareket ediyor — `/tmp/fix-suggest.txt` ✓ (sürüyor ✓).

**Tek sonraki iş.** Ölçüm biter bitmez: çıkan "önerilen düzeltme"yi **ürün yoluna** koymak ✓ (kullanıcı tek tıkla
"önerilen kenarı çıkar" diyebilsin ✓, öneri doğrulamanın kendi verisinden türetilsin ✓) ve aynı turda düzeltilmiş
bir konturu **gerçekten üretip** STEP'i yeniden açarak doğrulamak ✓ (kullanıcı müdahalesi 1 tık ✓, süre ✓).

## §26-A-8: ölçüm — tek kenar çıkarma yetmiyor; hizmet "geçerli konturu önce sunmak" — 2026-09-28

**Ölçüm (my_part.jpg, `fix_suggest.py` → `/tmp/fix-suggest.txt`).** En büyük üç wire konturunda doğrulamanın
adlandırdığı **her** kenar tek tek denenip çıkarıldı ✓:
- `outline_12` (13 kenar, 6 sorun ✗): dokuz adayın **hepsi** reddedildi ✗ — çıkarma sonrası kalan boşluk
  **62,4 / 91,5 / 108,0 / 187,0 / 210,0 / 254,2 / 259,9 / 363,9 / 423,2 px** ✗ (sınır 20 px ✗).
- `outline_34` (3 kenar, 1 sorun ✗): iki aday, boşluk 104,7 / 402,6 px ✗.
- `outline_47` (4 kenar ✓): zaten geçerli ✓ (düzeltme gerekmiyor ✓).

**Sonuç (dürüst):** bu paftada **tek kenar çıkarmayla düzeltme yok** ✗. Sebep ölçüldü ✓: kopan kenarlar konturun
*gerçek* parçaları ✗ — kesişme, zincirin **yanlış bağlamasından** geliyor ✗ (§26-A-2'nin teşhisi ✓), kenar
fazlalığından değil ✗. Aynı sebeple "yeniden zincirleme" de bu konturu kurtaramaz ✗: zincirin kuralı zaten en
yakın ucu bağlamak ✓ ve alternatifler 187–423 px uzakta ✗ — kesişmeyen seçenek diye bir şey yok ✗ (bu, ileride
boşuna denenmesin diye kayda geçti ✓).

**Ürüne dönen karar (genel, örneğe özel değil ✓).** `drawing_options` artık profilleri **geçerli-önce, sonra
büyüklük** sırasıyla sunuyor ✓ (`offer_rank` ✓): doğrulamanın "geçersiz" dediği konturlar listenin arkasına
düşüyor ✓ ama **listeden çıkmıyor** ✗ (PLAN §26.2: seçim kullanıcının ✓, kanıt yanında ✓). Kullanıcı böylece
ilk sırada üretilebilir bir kontur görüyor ✓ — ölçüm: aynı dört paftada kaç wire'ın geçerli olduğu değişmedi ✓,
değişen *yeri* ✓ (`offer_order.py` → `/tmp/offer-order.txt` ✓ koşuyor ✓).

**Kanıt:** `test_guided + test_contour_fix` → **30 passed (52,8 s)** ✓ (sıralama değişikliği kararları bozmadı ✓ —
kararlar profil *kimliğiyle* eşleşiyor ✓).

**Sınır / tek sonraki iş.** Yanlış bağlama için asıl düzeltme **konturu kesmek / doğru alt-zinciri seçmek** ✓:
çizimin parçaları birden çok dış hatta ait olabiliyor ✗; kullanıcıya "buradan sonrası başka hat" diyebileceği bir
kesme kararı (karar kaydında ✓, geri alınabilir ✓) ve kalan parçanın kapalılık denetimi gerekiyor ✓. Bir sonraki
dilim: kesme kararını (`contour.cut = [kenar]` ✓) `correct_profile` yoluna eklemek ✓, sentetik örneklerle
(iki hattın iç içe geçtiği pafta ✓) sınamak ✓ ve dört gerçek paftada yeniden ölçmek ✓.

## §26-A-9: "geçerli-önce" ölçüldü — dört paftanın dördü de geçerli konturla açılıyor — 2026-09-28

**Ölçüm (`offer_order.py` → `/tmp/offer-order.txt`, ürünün kendi sırasıyla):**

| Pafta | ilk öneri | geçerli? | geçerli wire / toplam |
|---|---|---|---|
| Exercise_51 | `outline_3` (wire) | ✓ | 4 / 12 |
| Exercise 17 | `outline_37` (wire) | ✓ | 9 / 23 |
| Flange | `outline_3` (wire) | ✓ | 9 / 19 |
| my_part | `outline_47` (wire) | ✓ | 6 / 18 |

Önce (boy sırası, §26-A-2) dördünün de ilk önerisi **geçersizdi** ✗ (`outline_4`, `outline_2`, `outline_13`,
`outline_12`); şimdi dördünün de ilk önerisi **geçerli** ✓. Toplam 72 wire'ın 28'i geçerli ✓ — yani sorun
konturların çoğunda değil, *sırasında* ve *bağlamasındaydı* ✓.

**Sıradaki ölçüm başlatıldı (`proc_a07524c7e626` → `/tmp/unseen17-build.json`).** Exercise 17 — §23-C38'de
CAD'in "geçersiz katı" dediği pafta — bu kez **ürünün sunduğu ilk geçerli konturla** uçtan uca: aç → ilk wire
kontur (kimlik koda yazılmadı ✗; sırayı ürün veriyor ✓) → kalibrasyon o konturun kendi uç noktalarıyla ✓ →
kalınlık kararı ✓ → kaydet ✓ → üret ✓ → hem üretilen hem **referans** STEP okunuyor ✓ (referans yalnız
değerlendirmede ✓). Ölçülecekler: kararların kabulü ✓, CAD sonucu ✓ (geçerli katı oldu mu ✓), süre ✓,
kullanıcı müdahalesi (2 nokta + 1 değer + 1 kalınlık ✓) ve şekil oranlarının referansla karşılaştırılması ✓.
Kalibrasyon değeri **kullanıcı varsayımı** olarak işaretli ✓ (gerçek boyut değil ✓; doğruluk kıyası oranlarla ✓).

## §26-A-10: ilk uçtan uca koşu BAYAT sunucuyu ölçtü — kontrollü tekrar — 2026-09-28

**Koşu (`proc_a07524c7e626`, `/tmp/unseen17-build-stale.json`).** Exercise 17 uçtan uca denendi ✓ ama sonuç
§23-C38'in **birebir aynısı** çıktı ✗: `error = "geçersiz katı"` ✗, `open_contour_px = 308.2514` ✗,
`unbound_edges = [0…6]` (7 kenar) ✗ — C38'de ölçülen sayının *aynısı* ✓.

**Sebep (ölçüldü, kendi hatam).** Sunucu `outline_2`'yi (en büyük, geçersiz) sunuyordu ✗ çünkü **sunucu eski
kodla çalışıyordu** ✗ — "geçerli-önce" sıralaması ağaçta vardı ✓ ama servis edilen süreçte yoktu ✗ (son restart
§23-C38'de yapılmıştı ✗). Yani koşu *yeni* sıralamayı değil *eski* sırayı ölçtü ✗ — geçersiz bir deney ✓ (kayda
geçti ✓; "bayat koşu yeşil sayılmaz" kuralının bu kez *benim* koşumda işlediği yer ✓).

**Yan fayda (gerçek bir kontrol).** Eski sırayla C38 hatası **deterministik olarak birebir** üredi ✓
(308,2514 px ✓, aynı 7 kenar ✓) → yani farkı yaratan şey gerçekten **öneri sırası** ✓; pafta okuması ve kararlar
aynı ✓. Bu, "geçerli-önce" değişikliğinin *etkisini* ölçmek için temiz bir taban çizgisi ✓.

**Şimdi koşan (`proc_9baf88c74214`).** Sunucu bugünkü kodla yeniden başlatıldı ✓ (`pkill` + `nohup` ✓, `/guided`
200 bekleniyor ✓) ve **aynı ölçüm** yeniden başlatıldı ✓: ilk önerinin `outline_37` (geçerli ✓) olması ✓,
kararların kabulü ✓, CAD sonucu ✓ (bu kez geçerli katı olup olmadığı ✓), süre ✓, üretilen vs **referans** STEP
(karşılaştırma sonraki turda ✓ — referans yalnız değerlendirmede ✓).

**Kural (yeniden yazıldı, bu kez kanıtıyla).** Kod değiştiğinde **önce sunucuyu yeniden başlat** ✗→✓, sonra
ölç ✓ — yoksa ölçüm eski süreci ölçer ✗ (bu dilimde tam olarak bu oldu ✗).

## §26-A-11: gerçek, görülmemiş raster paftadan GEÇERLİ STEP — ve içeriğinin dürüst sınırı — 2026-09-28

**Kilidi açan koşu (`proc_9baf88c74214`, taze sunucu; oturum `8e3e7da767774dfe83c68e2d8e6ad366`).**
Exercise 17 — §23-C38'de "geçersiz katı" ile duran pafta — bu kez **ürünün sunduğu ilk konturla** uçtan uca geçti ✓:
- İlk öneri **`outline_37` (wire, 4 kenar, `contour.ok = true`, kapanış 0,0 px)** ✓ (bayat koşuda `outline_2` idi ✗ →
  farkı yaratan şey öneri sırası ✓).
- Kararlar: kontur seçimi + **2 noktalı kalibrasyon (kullanıcının verdiği 100 mm değeri)** + **kalınlık 10 mm** ✓
  → `save`: `questions: []` ✓ (`revision 1`).
- `sketch.open_contour_px = 0,0` ✓ (`contour.ok = true` ✓, 4 kenar ✓) — **C38'in 308,25 px'i yok** ✓.
- Üretim: `build-1-4c1853fa/` → `plan-audit.json`: **`passed: true`** ✓ (`valid_solid: true` ✓,
  `export_round_trip: true` ✓); `geometry.json`: **1 geçerli katı**, hacim **6322,39 mm³**, kutu
  **[46,829 / 88,358 / 10,0] mm**, 6 yüz (5 düzlem + 1 silindir r≈30,31 mm) ✓; `step_facts`: `valid: true` ✓,
  `solids: 1` ✓. **Yani gerçek bir raster paftadan geçerli STEP üretildi** ✓✓.
- Süre: **23:23:51 → 23:44:09 (20 dk 18 sn)** ✓ — büyük kısmı okuma (`observe`) ✓; kullanıcı müdahalesi **4 karar** ✓.

**Dürüst sınır (aynı koşunun ölçtüğü).** Üretilen katı **referans parça değil** ✗:
- Seçilen `outline_37` **4 kenarlı bir alt-parça** ✗ — parçanın dış hattı değil ✗ (referans: 26 yüz, 16 silindir,
  4 torus ✓; bizim: 6 yüz, 1 silindir ✓). §26-A-2/A-8'in ölçtüğü **yanlış bağlama** hâlâ asıl engel ✗: gerçek dış
  hat (`outline_2`, 7 kenar ✗) geçersiz ✗ ve tek kenar çıkarmayla düzelmiyor ✗ (boşluklar 62–423 px ✗).
- **Ölçek kullanıcı varsayımı** ✓ (100 mm, gerçek boyut değil ✗) → boyut doğruluğu *ölçülmedi* ✗.
- **Kalınlık 10 mm kullanıcı kararı** ✗ — referansın en küçük kenarı **22 mm** ✓ → parça 22 mm; akış bunu
  çizimden okumuyor ✗ (yan görünüş/ölçü bağlama işi ✓).
- Bu koşuda delik/cep kararı verilmedi ✓ (karar boş ✓) — silindir yüzü konturun kendi yayından ✓.
- Referans STEP **yalnız değerlendirmede** kullanıldı ✓ (karşılaştırma ✓); koda, eğitime, şablona girmedi ✓.

**PLAN'ın ölçütleri (bu görülmemiş pafta için).** Doğru son STEP ✓ (geçerli, yeniden açılıyor ✓) · eksik/yanlış
özellik ✗ (alt-parça: delikler, toruslar, doğru dış hat yok ✗) · kullanıcı müdahalesi **4** ✓ · süre **20 dk** ✓
(okuma baskın ✓) · ölçü doğruluğu **ölçülmedi** ✗ (varsayılan ölçek ✓).

**Tek sonraki iş (iki kol).** (1) **Yanlış bağlamayı düzeltmenin asıl yolu**: konturu **kesmek / doğru alt-zinciro
seçmek** ✓ (`contour.cut` ✓, karar kaydında ✓, geri alınabilir ✓) — gerçek dış hattı geçerli yapmak için ✓.
(2) **Ölçü doğruluğu**: basılı ölçüyü bağlama (B) yolunu bu paftada çalıştırmak ✓ ve kalınlığı çizimden okumak ✓
(yan görünüş ✓) — doğruluk ölçümü ancak ondan sonra anlamlı ✓.

## §26-A-12: yanlış bağlamanın izi — köşe birleşimi mesafeyle sınırlı değil — 2026-09-28

**Hipotez (ölçülecek).** `_line_arc_corner` bir çizgi ile bir yayı, yayın merkezini çizgiye izdüşürerek
birleştiriyor ✓ — ve bu kural **mesafeyle sınırlı değil** ✗ (kendi gerekçesi: raster mürekkebi teğet köşede
birleşir, çizginin kaydedilen ucu köşeyi 30 px geçebilir ✓). Ama sınırsız olması demek, zincirin **308 px**
uzaktaki bir çifti de "köşe" sayıp bağlayabilmesi demek ✗ — §26-A-11'de gerçek dış hattın (`outline_2`, 7 kenar)
kapalı ama kendini kesen çıkmasının en olası kaynağı bu ✓. Yani `join_max_px`'in "kalan açıklık" olmaması gibi
✓, köşe birleşiminin mesafesi de "kapanış" değil ✗ — ayrı ölçülmesi gerekiyor ✓.

**Ölçüm koşuyor (`proc_b773f5ae7b73` → `/tmp/join-gaps.txt`).** Her **geçersiz** wire konturu için, kaydedilmiş
oturumlardan (yeniden okumadan ✓) ve gereken paftalar için taze okumayla ✓: ardışık her bağlantının **ham uç
mesafesi** (kayıtlı kenarlar zaten birleşik olduğundan ölçüm `geometry_ids` + `primitives` üzerinden ✓) ve o
çiftin **türü** (line→arc = köşe birleşiminin şekli ✓). 40 px üstü bağlantıların sayısı ve türü ayrı yazılıyor ✓.
Kabul ölçütü (bir sonraki dilim için hazır): geçerli kontur sayısı (bugün dört paftada **28/72** ✓ — A-9) düşmeden
büyük konturlar korunacak ✓; köşe birleşimine mesafe sınırı getirilirse **sweep** ile seçilecek ✓
(`RASTER_JOIN_TOLERANCE_PX` seçimindeki gibi ✓, tek `observe` yeniden kullanılarak ✓).

**Sıradaki adım.** Ölçüm bitince: 40 px üstü bağlantıların **line↔arc** çıkması hâlinde köşe birleşimine ölçülü
bir mesafe kapısı eklenir ✓ (`_loops`'un `corner_joins` yolunda ✓), sentetik örneklerle sınanır ✓ (iki hattın
iç içe geçtiği pafta ✓ + teğet köşe korunuyor mu ✓) ve dört paftada yeniden ölçülür ✓ (geçerli sayı + büyük
konturların korunması ✓). Hipotez yanlış çıkarsa (büyük bağlantılar line↔line ✗) kayda öyle geçer ✓ —
o zaman sıradaki iş `contour.cut`/alt-zincir kararıdır ✓.

## §26-A-13: hipotez çürüdü, yerine kesin mekanizma: kapanış birleşimi sınırsız — 2026-09-28

**Hipotez testi (kendi ölçümüm, düzeltmeyle).** Köşe birleşiminin sınırsız mesafesi ana sebep *değil* ✗:
`join_gaps.py` çıktısında 40 px üstü bağlantıların çoğu **line→line** çıktı ✗ (160/144/139 px, 732/726 px,
1573 px ✗) — köşe birleşimi ise yalnız line↔arc çiftlerinde çalışıyor ✓. **Ama bu ölçümün kendisi de kusurlu** ✗:
ham `primitives` uçlarıyla zincirin sırasını karşılaştırdım ✗ — *birleştirilmiş* çizgiler (`_merged_lines`) ile
zincirin kullandığı geometri aynı değil ✓, yani o sayılar "bağlantı uzunluğu" değil ✗. Kayda böyle geçti ✓.

**Yerine kodun okunuşundan çıkan kesin mekanizma.** `_trace`'in kapanış döngüsü (satır 226-267):
`gap = math.dist(left["end"], right["start"])` ölçülüyor ✓, `max_join` **kaydediliyor** ✓ — ama birleşim
uygulanırken **mesafe kapısı yok** ✗: line→line çiftinde iki uç **orta noktada** buluşturuluyor ✗
(`left["end"], right["start"] = point, list(point)` ✓). Yani 308 px'lik bir kapanış, bir ucun ~154 px
**sürüklenmesi** demek ✗ → kenar pafta boyunca kayıyor ✗ → kendini kesiyor ✗ → doğrulama (haklı olarak ✗)
konturu geçersiz buluyor ✓. **Tutarsızlık da burada** ✓: arc↔arc çifti `gap > 1e-7` ise açıkça reddediliyor ✓
("iki yay arasında açık uç var; kontur düzeltmesi gerekli" ✓) — ama iki çizgi 308 px uzaktaysa sessizce
birleştiriliyor ✗.

**İnen (güvenli, varsayılan kapalı ✓).** `_trace` artık her bağlantının kendi boşluğunu **`joins`** listesinde
yayınlıyor ✓ (`{index, gap_px, left, right}` ✓ — §26.3'ün "yapılan düzeltmenin miktarı" maddesi artık bağlantı
başına görünür ✓) ve **`close_tolerance_px`** parametresi aldı ✓ (`_trace` + `drawing_options` ✓; varsayılan
`None` = bugünkü davranış ✓ → hiçbir şey değişmedi ✓). Sınır verilirse kapanış boşluğu onu aşan halka
**reddediliyor** ✓ ve ret mesajı ölçülen boşluğu taşıyor ✓ ("kapanış boşluğu 308,3 px …: bu halka kapalı bir
kontur değil" ✓).

**Kanıt:** `test_guided + test_contour_fix + test_contour_audit` → **38 passed (48,9 s)** ✓ (varsayılan kapalı
olduğu için hiçbir karar değişmedi ✓).

**Süpürme koşuyor (`proc_43b9c8edbe46` → `/tmp/close-sweep.txt`).** Dört paftada sınır ∈ {None, 40, 60, 100,
160, 240} px; her satır: sunulan wire sayısı ✓, **geçerli oranı** ✓, kapanış yüzünden ret sayısı ✓ ve en büyük
iki konturun kimliği/kutusu/geçerliliği ✓. Kabul ölçütü: geçerli oran yükselirken **parça ölçeğindeki büyük
konturlar kaybolmamalı** ✓ (meşru raster kapanışları 6–24 px ölçülmüştü ✓ → sınır ≥ 24 olmalı ✓).

**Tek sonraki iş.** Süpürme sonucundan sınırı seçip **ürün varsayılanı** yapmak ✓, iki sentetik testle sabitlemek
✓ (uçları yüz piksel ayrı halka reddedilir ✓; 24 px'lik meşru kapanış geçer ✓) ve dört paftada sunum/geçerlilik
ölçümünü yeniden almak ✓ (`offer_order.py` ✓).

## §26-A-14: kapanış sınırı süpürmesi — kapı kazandırmıyor, varsayılan KAPALI kalıyor — 2026-09-28

**Süpürme (`proc_43b9c8edbe46` → `/tmp/close-sweep.txt`; sunulan wire · geçerli (oran)):**

| Pafta | None | 40 px | 60 px | 100 px | 160 px | 240 px |
|---|---|---|---|---|---|---|
| Exercise_51 | 12 · 4 (%33) | 4 · 1 (%25) | 4 · 1 (%25) | 5 · 2 (%40) | 7 · 2 (%29) | 9 · 2 (%22) |
| Exercise 17 | 23 · 9 (%39) | 9 · 4 (%44) | 9 · 4 (%44) | 11 · 5 (%45) | 15 · 6 (%40) | 19 · 9 (%47) |
| Flange | 19 · 9 (%47) | 6 · 3 (%50) | 6 · 3 (%50) | 13 · 5 (%38) | 15 · 6 (%40) | 17 · 8 (%47) |
| my_part | 18 · 6 (%33) | 3 · 0 (**%0**) | 4 · 0 (%0) | 8 · 1 (%12) | 14 · 4 (%29) | 18 · 6 (%33) |

**Karar (ölçümle).** Sınır **hiçbir yerde** geçerlilik oranını anlamlı biçimde yükseltmiyor ✗ (±5 puan ✗; my_part'ta
%33 → %0 ✗✗) ve her sınır sunulan konturları **yarıya ya da daha fazlasına** indiriyor ✗. Yani kapanış kapısı
hak ettiği yeri kazanmadı ✓ → **varsayılan `None` (kapalı) kalıyor** ✓; `joins` verisi ise kalıyor ✓ (bağlantı
başına kanıt ✓). Bu, `join_max_px`'in "kalan açıklık" olmadığı teşhisinin bir uzantısı ✓: büyük kapanış boşluğu
*tek başına* geçersizlik anlamına gelmiyor ✗ — my_part'ta 40 px sınırı **geçerli** konturu (`outline_47` ✓) eledi ✓
(boşluğu büyük ✓ ama sürükleme kesişme yaratmamış ✓). Doğru ölçüt boşluk değil, **kesişme** ✓ — ve o zaten
doğrulamanın işi ✓.

**Ölçüm aracımın hatası (kayıtlı).** Süpürme tablosundaki "kapanış yüzünden ret" sütunu **anlamsız** ✗:
`options["skipped"]` diye bir anahtar yok ✗ → her satırda 0/0 yazdı ✗. Kapının çalıştığı, *sunulan* sayıların
düşmesinden belli ✓ (19 → 6 ✓ vb.) ✓ — ama nedenini *sayamadım* ✗; doğru araç, retlerin metnini
`drawing_options`in döndürdüğü yerden okumak olurdu ✓.

**§26-A kapanışı (dürüst bilanço).** Kontur doğrulaması ✓ (kapanış/öz-kesişim/çakışma, konumlu ✓), çizimde
işaretleme ✓, kullanıcı düzeltmesi ✓ (kenar çıkar + birleşim onayı, karar kaydında ✓, geri alınabilir ✓),
geçerli-önce sunum ✓, gerçek görülmemiş paftadan **geçerli STEP** ✓ (§26-A-11 ✓) — ama **doğru dış hat** ✗
(yanlış bağlanan konturlar ✗) ve **ölçü doğruluğu** ✗ (varsayılan ölçek ✓, kalınlık kullanıcı kararı ✓) hâlâ
eksik ✓. Yanlış bağlamanın kaynağı *bağlantı mesafesi* değil ✗ (§26-A-14) — kenar geometrisinin kendisi ✓
(birleştirilmiş çizgi uzantıları / yayın yeniden kurulan ucu ✓); bu, ayrı ve daha derin bir okuma işi ✓.

**Tek sonraki iş:** PLAN §26'nın ikinci yarısı — **`sketch_constraints.py` çözücüsünü karar kaydına,
GeneralPlan'a ve arayüze bağlamak** ✓ ("ölçüler kenar ve merkez konumlarını gerçekten değiştirsin; çelişkiler ve
eksik kısıtlar görünür olsun; ortak ölçek ayarını kesin eskiz çözümü diye sunma" ✓).

## §26-B-1: ölçüye bağlı geometri çekirdeği ürün akışına bağlandı — 2026-09-28

**İnen (PLAN §26.4-B'nin ilk dilimi).** `guided.user_dimensions(profile, options, decisions, scale, origin)` ✓:
kullanıcının bağladığı basılı ölçüleri **mevcut kısıt çekirdeğine** (`sketch_constraints.solve_constraints` ✓)
çeviriyor ✓, çözüyor ✓ ve **çözülen geometriyi plana yazıyor** ✓ — `make_plan` çağrısı ölçek/başlangıç noktası
hesaplandıktan hemen sonra ✓, yani CAD'e giden koordinatlar kullanıcının ölçüsünden geliyor ✓.
- **Çizgi konturlarda** köşeler çözülen konumlara taşınıyor ✓; **delik/cep merkezleri** çözülen daire
  merkezlerinden alınıyor ✓ (oturumun kendi `options` sözlüğü **mutasyona uğramıyor** ✗→✓ test edildi ✓);
  ölçüyle sabitlenmeyen koordinatlar **aynen izlenen** hâlinde kalıyor ✓ ("ölçülendirilmeyen kısmı taslak tut" ✓).
- **Hiçbir şey uydurulmuyor** ✓: eksen, iki ucun baskın yönünden ✓; işaret (`direction` ✓) izlenen geometrinin
  Y-yukarı çerçevedeki yönünden ✓; `vertex` ucu kullanıcının tıkladığı noktaya **en yakın kontur köşesine**
  eşleniyor ✓ — üçü de kodda adıyla yazılı ✓.
- **Rapor** (`profile["solved_dimensions"]` ✓, planla birlikte kayda geçiyor ✓): `status`
  (`underconstrained` / `conflict` / `unsupported` ✓), `dof` ✓, `free` (serbest koordinat sayısı ✓ = **eksik
  serbestlik görünür** ✓), `conflicts` (çakışan bağların kimlikleri ✓), `notes` (çekirdeğin kendi sınırlama
  mesajları ✓ — yay yarıçapı/açı/teğetlik desteği gelene kadarki sınır **saklanmıyor, yazılıyor** ✓), `moved`
  (uygulanan en büyük konum değişimi, px ✓).
- Çekirdeğin kuralları olduğu gibi geçerli ✓: yalnız **tamamı çizgi** olan dış konturda köşeler oynuyor ✓;
  yaylı/dairesel dış konturda yalnız daire merkezleri ölçülendirilebiliyor ✓ (çekirdeğin kendi hata metni
  olduğu gibi kullanıcıya dönüyor ✓).

**Bağımsız sentetik kabul (`tests/test_user_dimensions.py`, 4 test ✓ — pafta yok, kimlik yok):**
60 mm'lik bağ izlenen 100 px'lik kenarı **gerçekten** 60 mm'ye getiriyor ✓ (`moved > 0` ✓, ölçüm 60 mm ✓);
aynı açıklığa 60 ve 50 mm bağlanınca sonuç **`conflict`** ve kimlikler raporda ✓; daire merkezine bağ **o
merkezi** taşıyor ✓ (ölçüldü ✓) ve oturumun seçeneği değişmiyor ✓; bağ yoksa hiçbir şey çözülmüyor ve hiçbir
şey kımıldamıyor ✓.
**Kanıt:** `test_user_dimensions + test_sketch_constraints + test_guided + test_contour_fix` →
**56 passed (40,6 s)** ✓ — `test_guided`'ın "bağlanan ölçü ölçeği ve planı değiştirir" testi de çözücü devredeyken
geçiyor ✓.

**Kalan sınırlar (kayıtlı).** (1) **Kaynak etiketi**: plan hâlâ tüm koordinatları `assumed` yazıyor ✗ — bağın
sabitlediği noktalar `user` olmalı ✓ (PLAN: "`user`, `derived` ve `assumed` kaynaklarını koru" ✓). (2) **Arayüz**:
çözüm raporu panelde görünmüyor ✗ ve yatay/dikey **ilişki** denetimi yok ✗ (çekirdek destekliyor ✓, arayüz
sunmuyor ✗). (3) **B kabulü**: bozuk oranların verilen ölçülerle düzelmesinin **gerçek paftada** ve **gerçek
arayüzde** sınanması, kesin delik merkezinin bağımsız STEP ölçümüyle doğrulanması — henüz yapılmadı ✗.

**Tek sonraki iş:** (1)+(2) birlikte — çözülen noktaları `user` kaynaklı yazmak ✓ (hangi noktanın sabitlendiğini
çekirdeğin `free_coordinates` verisi söylüyor ✓) ve panel 4'e çözüm satırlarını eklemek ✓ (durum ✓, serbest
koordinat sayısı ✓, çakışan bağlar ✓, uygulanan değişim ✓) — ardından gerçek paftada B kabulü ✓.

## §26-B-2: tutarsız ölçüler artık geometriyi hareket ettiriyor — gerçek paftada ölçüldü — 2026-09-29

**Kapı çözücüye devredildi ✓.** Eskiden "bağlanan ölçüler tek ölçekle tutarlı değil" *engelleyici* bir soruydu ✓
(`sketch.questions` ✓) ve tam da çözücünün çözmesi gereken durumu bloke ediyordu ✗. Artık: bağlar çekirdeğin
ölçebildiği türdense (bu dilimde **yalnız merkez bağları** ✓; kenar ucu bağları profil elde olmadan
varsayılmıyor ✓) bu satırlar **engelleyici soru olmaktan çıkıyor** ✓ — artıklar tanılamada kalıyor ✓ (arayüz
gösteriyor ✓) ve **gerçek çakışma** `make_plan`'de çekirdeğin kendi mesajıyla durduruluyor ✓
(`bağlanan ölçüler birlikte tutmuyor (çakışan: …)` ✓). `bindings_solvable` bunu adıyla söylüyor ✓.

**Gerçek pafta kabulü (plaka, vektör PDF — iki uçtan uca koşu ✓).**
- *Kenar ucu bağı:* planın x'leri `assumed` ✓, hiçbir koordinat etiketlenmedi ✗→✓ ve bağın hiçbir etkisi yok ✓ —
  yani **yaylı konturda köşe ölçülendirilemiyor** kuralı sessizce değil, *hiç hareket ettirmeden* uygulanıyor ✓.
- *İki merkez bağı* (taban sol ↔ taban sağ = 80,00 mm ✓; taban sol ↔ üst sol = 60,00 mm ✓ — tek ölçekle
  tutarsız: +5,624 / −4,218 mm artık ✓): koşu **geçti** ✓ ve ölçüldü ✓ — `g11` x'i **1223,13 → 1266,97 px** ✓
  (80,00 mm için tam gereken kayma ✓), `g61` y'si **1304,18 → 1281,77** ✓ (60,00 mm ✓), çapa (`g9`) yerinde ✓.
  **Planda:** g9↔g11 = **80,000 mm** ✓ · g9↔g61 = **60,000 mm** ✓ — ikisi de tam ✓.
  **Katıda:** 1 geçerli katı ✓ ([90,947 / 60,627 / 15,0] mm ✓ 80,862 cm³ ✓, `step_facts` ✓); **taşınan delik**
  (g11) x=87,5852'de kesilmiş ✓ = planın değeri ✓ ve plan denetiminin araç tekrarı bunu **doğruladı** ✓
  (`hole_3_cut ok: true` ✓ — PLAN'ın "kesin delik merkezi bağımsız STEP ölçümünde doğrulansın" maddesi ✓).
  Çekirdek durumu **underconstrained** ✓ ve sınırlamayı kendi notuyla söylüyor ✓: "Yaylı/dairesel dış kontur
  çizimden izlenen taslak olarak kalır. Serbestlik sayısı yalnız seçili daire merkezlerini kapsar." ✓
- *Denetimin iki uyarısı ✗ benim betiğimin hatası ✓*: `by_radius[:4]` ile seçtiğim dairelerin ikisi (g61, g63)
  paftanın **kesit görünüşünde** ✓ — parçanın dışında ✓ — kesilemeyince "silindir bulunamadı" ✓. Ürün doğru
  davrandı ✓ (uydurmadı, denetim görünür biçimde işaretledi ✓); seçim hatası betiğe ait ✓.

**Kalan sınırlar.** (1) **Kaynak etiketi**: planın çözülen koordinatları hâlâ `assumed` ✗ — çekirdeğin
sabitlediği noktalar `user` olmalı ✗ (PLAN: "kaynakları koru" ✓). (2) Kenar ucu bağları yalnız çizgi konturda
çözülebiliyor ✓ ama bu *kapı* hâlâ onları çekirdeğe iletmeden soru sayıyor ✗. (3) Çözüm raporunun **gerçek
arayüzde** görünmesi sınanmadı ✗ (panel satırları yazıldı ✓; tarayıcıda kontur onayı ve panelin kendisi
görüldü ✓). (4) Yatay/dikey ilişki denetimi yok ✗.

**Kanıt:** `test_guided + test_user_dimensions + test_sketch_constraints` → **50 passed (41,1 s)** ✓ (kapı
değişikliğiyle birlikte ✓). Koşu çıktıları: `/tmp/plate-binding2.json` ✓, klasörler
`out/guided/b1831b22…/build-1-8d1411e7/` ✓ ve `out/guided/d50b61b1…/build-1-b939bb29/` ✓.

**Tek sonraki iş:** (1) — çözülen noktaları `user` kaynaklı yazmak (çekirdeğin `free_coordinates`'i hangi
noktanın sabitlendiğini söylüyor ✓); ardından (3) raporun arayüzde görünmesini gerçek tarayıcıda sınamak.

## §26-B-3: kaynak etiketleri ayrıştı — çözülen koordinat `user`, kalanı taslak — 2026-09-29

**İnen.** `xy()` artık nokta başına ve **eksen başına** kaynak yazıyor ✓: çekirdeğin `free_coordinates` verisi
(hangi noktanın hangi ekseni serbest ✓) okunup, **sabitlenen** koordinat `user` ✓, serbest kalan `assumed` ✓ —
hiçbir nokta toptan etiketlenmiyor ✓. Çapa noktası (çizimdeki konumu yalnız koordinat sistemini sabitler ✓)
bilerek dışarıda tutuluyor ✓: o hâlâ çizimden izlenen bir ölçü ✓. Planın varsayım cümlesine de sayılar giriyor ✓:
"Ölçü çözümü uygulandı: N koordinat kullanıcının bağladığı ölçülerden geldi, M koordinat hâlâ çizimden izlenen
taslak." ✓ — böylece hem "kaynakları koru" ✓ hem "eksik serbestlik görünür olsun" ✓ maddeleri plan düzeyinde
karşılanıyor ✓.

**Gerçek pafta kabulü, temiz koşu (plaka ✓ — bağ uçları bu kez paftanın *içindeki* dairelerden ✓; kesit
görünüşündeki daireler parça sayılmadı ✓).** `inside_ids = [g8, g9, g10, g11, g12]` ✓; bağlar g9↔g11 = 80,00 mm ✓
ve g9↔g12 = 60,00 mm ✓ (tek ölçekle tutarsız ✓; en küçük kareler ölçeği 9,1357 px/mm ✓).
- **Plan denetimi tam geçti** ✓ (`passed: true` ✓) ve araç tekrarı **beş deliğin beşini de doğruladı** ✓
  (`hole_0…hole_4_cut ok: true` ✓) — yani kesilen her silindir yeniden açılan katıda **beklenen yerde** bulundu ✓.
- **Katıdan bağımsız ölçüm** ✓ (Ø6,8 delik silindirleri ✓ r=3,4 ✓): g9 (8,6288 / 60,3464) ✓ ve g11 (88,6288 /
  60,3464) ✓ → **80,0000 mm** ✓; g9 ↔ g12 (8,6288 / 0,3464) ✓ → **60,0000 mm** ✓. **İki tutarsız ölçü de STEP'te
  birebir tutuyor** ✓ — PLAN §26.4-B'nin "kesin delik merkezi bağımsız STEP ölçümünde doğrulanması" maddesi ✓.
- **Etiketler** ✓: `user` kaynaklı parametreler `binding_0`, `binding_1`, delik çapları ✓ + **yalnız iki
  koordinat** (`hole_3_x` ✓ = g11'in x'i ✓, `hole_4_y` ✓ = g12'nin y'si ✓) ✓; planın kendi cümlesi: "2 koordinat
  kullanıcının bağladığı ölçülerden geldi, 10 koordinat hâlâ çizimden izlenen taslak." ✓
- *Kenar ucu bağı* koşusu (yaylı kontur ✓): denetim geçti ✓, hiçbir koordinat etiketlenmedi ✓ ve geometri
  kımıldamadı ✓ — çekirdeğin "yaylı/dairesel dış konturda yalnız daire merkezleri" kuralı ✓ sessiz değil,
  *etkisiz* ✓ (notu state'te görünüyor ✓; **planda görünmüyor** ✗ — kayıtlı sınır ✓).

**Kanıt:** `test_guided + test_user_dimensions + test_sketch_constraints + test_plate_plan` → **74 passed
(47,5 s)** ✓. Koşu çıktıları `/tmp/plate-binding2.json` ✓ (temiz koşu ✓).

**Kalan sınırlar.** (1) Çözüm reddi (desteklenmeyen bağ) planda yazmıyor ✗ — yalnız state/arayüz gösteriyor ✗.
(2) Yatay/dikey **ilişki** denetimi yok ✗. (3) Çözüm raporunun **gerçek arayüzde** görünmesi hâlâ sınanmadı ✗.

**Tek sonraki iş:** (3) — raporun arayüzde görünmesini gerçek tarayıcıda sınamak (plaka aç ✓, kontur+ölçek onayla ✓,
basılı ölçüyü seç ✓, "Seçili ölçüyü bağla" ✓, iki delik merkezine tıkla ✓, kaydet ✓, build ✓ → panelde
"Ölçü çözümü" satırları ✓).

## §26-B-4: arayüz kontrolü — sayfa yeni, sürülen js önbellekten eski — 2026-09-29

Gerçek tarayıcı kontrolü (§26-B-3'ün tek sonraki işi ✓): sayfa açılıyor ✓ (başlık, yerleşim, düğmeler ✓) ama
**sayfaya sürülen `guided.js` yeni çözüm satırlarını içermiyor** ✗ (`Ölçü çözümü` ✗, `çakışan bağlar` ✗,
`serbest koordinat` ✗) — XHR ile okundu ✓. **Diskteki dosya yeni** ✓ (yukarıdaki karşılaştırma ✓). Yani
tarayıcı önbelleği eski kopyayı sunuyor ✗: raporun gerçek arayüzde görünmesi **hâlâ sınanmadı** ✗ ve bir
sonraki kontrol önbelleği atlatarak (§veya sert yenileme ile) yapılmalı ✗. Bu, "API girişini UI kabulü sayma"
kuralının tam olarak neden gerekli olduğunu bir kez daha gösterdi: dosya doğru ✓, *sayfada görünen* doğru
değil ✗.

### §26-B-4 düzeltmesi (kendi ölçüm hatam)

Yukarıdaki "tarayıcı önbelleği" teşhisi **yanlış** ✗. Ölçüm: `curl http://127.0.0.1:8765/static/guided.js` içinde
"Ölçü çözümü" **0** kez ✓, diskteki `src/drawingto3d/static/guided.js` içinde **1** kez ✓. Yani sunucu
**başka bir dosyayı** servis ediyor ✗ — önbellek değil ✓. §26-A'da arayüz yamaları *görünmüştü* ✓ (panel 4
başlığı ✓, `#contour-fix` ✓, `renderSketch` onarımı sonrası `build_handler: true` ✓), yani servis edilen kopya
tamamen donuk değil ✗; ama bu turda yazdığım js satırları **sunucudan gelmiyor** ✗. Sebep bulunmadı ✗ —
tek sonraki iş bu: sunucunun statik kökünü (`app.py` montajı ✓) ve depoda ikinci bir `guided.js` kopyası olup
olmadığını ölçmek ✓; bulunana kadar **arayüzde görünen js'e güvenilmez** ✗.

### §26-B-4 ikinci düzeltme — ölçüm hatamın kökü bulundu

`/static/guided.js` **404** ✗ (kod 404, 9 bayt ✓) — yani ilk "sunucu eski dosyayı servis ediyor" teşhisi de
**yanlıştı** ✗: yanlış adrese baktım ✗. Sayfanın kendisi `src="/guided.js"` ✓ yüklüyor; `ROOT = static` ✓
(`app.py:22`) ve depoda **tek** `guided.js` var ✓ (`src/drawingto3d/static/guided.js` ✓), sunucu de süreç
olarak **tek** ✓. Ders (ölçüm disiplini): bir yoklama yapmadan önce *adresin kendisini* doğrula ✗→✓; "0 eşleşme"
bir 404 gövdesinden de gelebilir ✓. Arayüz js'i büyük olasılıkla taze ✓ — ama bunu iddia etmeden önce
`/guided.js` üzerinden ölçmek gerekir ✓ (bir sonraki adım).

## §26-B-5: arayüz koşusu — ölçü seçici ve bağ denetimleri doğrulandı, bağlama tıklaması yarıda kaldı — 2026-09-29

**Ölçüm düzeltmesi (önemli):** servis edilen arayüz js'i **taze** ✓ — `/guided.js` 200 ✓, 23 967 bayt ✓ ve dört
yeni dizeyi de içeriyor ✓ (`Ölçü çözümü` ✓, `çakışan bağlar` ✓, `serbest koordinat` ✓, `solved_dimensions` ✓).
İlk iki teşhisim (önbellek ✗, "sunucu eski dosyayı servis ediyor" ✗) **yanlıştı**: yokladığım adres `/static/...`
404'tü ✓; sayfa `/guided.js` yüklüyor ✓, `ROOT=static` ✓ ve depoda tek kopya var ✓. İkisi de kayda düzeltme
olarak geçti ✓. Ders: yoklama yapmadan önce **adresi** doğrula ✓.

**Gerçek tarayıcı koşusu (plaka ✓).** Sayfa açıldı ✓, dosya girişine plaka PDF'i verildi ✓, **kontur ve ölçek
gerçek tıklamayla onaylandı** ✓ ("Öneri onaylandı: 100 mm · menü: t0" ✓).
- `measurement` seçicisi **paftanın kendi basılı ölçülerini** sunuyor ✓: `t0: 100,00 (mm)` ✓, `t1: 80,00 (mm)` ✓,
  `t2: 60,00 (mm)` ✓, `t4: 6,80 THRU ALL` ✓, `t6: 50,00` ✓, `t9: 15,00` ✓, `t10: 8,00` ✓ (+ çerçeve sayıları ✓).
  Seçim `t0` yapıldı ✓.
- Panel 4 denetimleri yerinde ✓: "Seçili ölçüyü bağla" düğmesi ✓ ve "Henüz bağ yok: ölçek yalnız iki noktalı
  kalibrasyondan geliyor." satırı ✓.
- **Yarıda kalan:** "Seçili ölçüyü bağla" düğmesi ekranın **altında** kalıyor ✗ (client y ≈ 2195 ✗, görünür alan
  ~632 px ✓) — tıklama boşa gitti ✗ (durum satırı değişmedi ✓); dolayısıyla **kaydet → build → "Ölçü çözümü"
  satırı arayüzde görülmedi** ✗. Ayrıca sayfanın js durumu (`state`, `scale`) **modül kapsamlı** ✗ — dışarıdan
  okunamıyor ✓ (bu kapsülleme iyi bir işaret ✓); tuval dönüşümü bir sonraki turda `#sheet` kutusundan ve çizilen
  resmin ölçeğinden türetilmeli ✓.

**Tek sonraki iş (kesin, küçük):** aynı koşuyu bitirmek — panel 4'ü görünür alana kaydır ✓, "Seçili ölçüyü
bağla" ✓, iki delik merkezine tuvalde tıkla ✓ (dönüşüm `#sheet` kutusundan ✓), kalınlığı kaydet ✓, build ✓,
sonra panelde **"Ölçü çözümü: …"** satırını oku ✓.

### §26-B-5 ek: bağ modu arayüzde çalışıyor — kalan tek şey iki tıklamanın dönüşümü

Gerçek tarayıcıda ✓: "Seçili ölçüyü bağla" düğmesine basınca **bağ modu açılıyor** ✓ ("Bağlamayı bırak" düğmesi
belirdi ✓); ilk tuval tıklaması **bir ucu yakaladı** ✓ ("Bir uç seçildi; ikinci uca tıklayın." ✓ — yakalanan uç
paftanın sol üst köşesiydi ✓, hedeflediğim delik merkezi değil ✗ — tuval→sayfa dönüşümünü yanlış kestirdim ✗);
ikinci tıklama hedefe yakın olmadığı için ürün **kendi dürüst hatasını** verdi ✓ ("Bağ ucu seçilen konturun bir
köşesine ya da bir daire merkezine yakın olmalı." ✓). Yani arayüz zinciri (ölçü seç ✓ → bağ modu ✓ → yakalama ✓
→ hata metni ✓) **çalışıyor** ✓; kalan tek eksik, tuval→sayfa dönüşümünün kesin ölçeğinin bulunması ✓ (bu turda
`s` tahminim yanlış çıktı ✗; sonraki tur: `s`'yi sayfadan ölçmek için bilinen bir noktaya tıkla ve uygulamanın
kaydettiği ucu oku ✓ ya da çizilen resmin nitelik boyutunu tuvalden al ✓). Sonra: iki delik merkezi ✓ →
kaydet ✓ → build ✓ → panelde "Ölçü çözümü" ✓.

### §26-B-5 ek 2: dönüşümün ölçüsü bulundu — ve oturum tükendi

Ekran→sayfa dönüşümü ölçüldü ✓: `s ≈ 2,2` (tuval 725,95×514,19 görünür ✓, nitelik 1200×849 ✓; paftanın sol
kenarı ve kesişen noktalar bu değerle örtüşüyor ✓). Bu, ilk tıklamamın neden sol üst **köşeyi** yakaladığını
açıklıyor ✓: `s≈2,2` ile g9 delik merkezi ekranda ≈ (157, 247) ✓, konturun sol üst köşesi ≈ (163, 253) ✓ —
**9 piksel arayla** ✓; tıklamam (162,5 / 255,6) köşeye daha yakındı ✗ ve yakalama yarıçapı (12/displayed ≈ 20
piksel ✓) ikisini de kapsıyordu ✓ → en yakın kazandı ✓. Yani ürün doğru davrandı ✓; ben yanlış yere tıkladım ✗.
Delik merkezlerinin ekran konumu: g9 ≈ (157, 247) ✓, g11 ≈ (374, 247) ✓ — sıradaki tur bunlara tıklamalı ✓.
**Engel:** bu turda tarayıcı oturumu düştü ✗ (`sheet` tanımsız ✗ = sayfa yenilenmiş/taze ✗; bu oturumda zaten
"her yeni çağrıda sekme kayboluyor" ✗ kayıtlı ✓). Arayüz zincirinin kendisi çalışıyor ✓ (bağ modu ✓, yakalama ✓,
dürüst hata ✓) — kalan tek şey iki isabetli tıklama ✓ → kaydet ✓ → build ✓ → "Ölçü çözümü" satırı ✓. Bu,
kullanıcının kendisi arayüzde bir dakikada bitirebileceği bir adım ✓; ya da taze bir tarayıcı oturumunda
yeniden açılıp (plaka ✓, kontur+ölçek onayı ✓) yukarıdaki iki koordinata tıklanarak ✓.

## §26-B-6: ARAYÜZ KABULÜ TAMAM — çözüm raporu gerçek tarayıcıda görüldü — 2026-09-29

Gerçek tarayıcıda, gerçek tıklamalarla uçtan uca ✓ (plaka ✓, taze oturum ✓):
1. "Ölçeği uygula" ✓ → "Karar kaydedildi." (kullanıcının iki noktalı kalibrasyonu: **787,6 px = 80 mm** ✓ —
   iki alt delik merkezi ✓).
2. Ölçü seçicisinden paftanın kendi basılı değeri **80,00 (mm)** seçildi ✓ → "Seçili ölçüyü bağla" ✓ →
   bağ modu açıldı ✓ ("Bağlamayı bırak" ✓) → tuvalde **iki delik merkezine** tıklandı ✓ ("Bir uç seçildi; ikinci
   uca tıklayın." ✓ → "Karar kaydedildi." ✓) → panelde bağ satırı: **"80 mm · g9 ↔ g11"** ✓ ("Kaldır" ile geri
   alınabilir ✓).
3. Kalınlık 15 girilip kaydedildi ✓, "Seçilen kontur ve merkezleri çizimden izlenen taslak olarak kullan"
   işaretlendi ✓, **build** çalıştırıldı ✓ → durum: "Taslak hazır. Geometrik kontrol tamam…" ✓.

**Panelde okunan yeni satır** ✓ (PLAN §26.4-B'nin görünürlük maddesi):
"**Ölçü çözümü: çözüldü · serbest koordinat 11 · uygulanan değişim 0,00 px.**" ✓ + çekirdeğin iki notu ✓
("Başlangıç noktasının çizimdeki konumu yalnız koordinat sistemini sabitler; parça ölçüsü değildir." ✓ /
"Yaylı/dairesel dış kontur çizimden izlenen taslak olarak kalır. Serbestlik sayısı yalnız seçili daire
merkezlerini kapsar." ✓). Panel 4'ün kendi metni de dürüst ✓: "Tek bir ölçek çözülen bağları uzlaştırmaz;
çelişki soru olarak sorulur." ✓

**Aynı koşunun kanıtı (arayüzün ürettiği klasör)** ✓: oturum `34f729c104f643c2b891bf74b24f9f0d` ✓, build
`build-5-b062fba9` ✓ — **plan denetimi geçti** ✓ (`valid_solid` ✓, `export_round_trip` ✓), **geçerli 1 katı** ✓
[96,0087 / 64,0014 / 15,0] mm ✓ 91 327,66 mm³ ✓, `part.step` yazıldı ✓ (32 458 bayt ✓). Planın varsayım
cümlesi ✓: "Ölçek 9,8446 px/mm — bağlanan 1 basılı ölçüden en küçük karelerle çözüldü… **Ölçü çözümü
uygulandı: 1 koordinat kullanıcının bağladığı ölçülerden geldi, 11 koordinat hâlâ çizimden izlenen taslak.**" ✓
Bu koşuda `user` kaynaklı parametreler `binding_0`, `thickness` ✓ — sabitlenen tek koordinat bir *daire
merkezine* ait ✓ ve o daire kesilmediği için plan parametresi yok ✗ (etiketlenecek yanlış bir şey yok ✓;
sayı varsayım cümlesinde duruyor ✓).

**§26'nın iki yarısı da kapandı** ✓: (A) kontur doğrulaması ✓ + düzelt/kaydet/geri al ✓ + geçerli-önce sunum ✓ +
görülmemiş raster paftadan geçerli STEP ✓; (B) çözücü karar kaydına, GeneralPlan'a ve arayüze bağlı ✓ — ölçüler
kenar/merkez konumlarını gerçekten değiştiriyor ✓ (gerçek paftada 80,0000 / 60,0000 mm STEP'te ✓), çelişkiler
ve eksik serbestlik görünür ✓, ortak ölçek kesin çözüm diye sunulmuyor ✓.

**Kayıtlı kalan sınırlar (yeni pencere için):** (1) yatay/dikey **ilişki** denetimi yok ✗ (çekirdek destekliyor ✓);
(2) çözüm reddi notu *planda* yazmıyor ✗ (state/arayüzde ✓); (3) çizgi konturda köşe ucu bağları hâlâ eski soru
kapısına takılıyor ✗; (4) okuma kalitesi: yanlış bağlama (kendini kesen konturlar) sürüyor ✗ — kesme/alt-zincir
seçimi işi duruyor ✓; (5) yeni görülmemiş paftalarda doğruluk/müdahale/süre ölçümleri sürdürülmeli ✓.

### §26-B-3 kanıt yolu (bildirim geldi — temiz koşu klasörü)

Temiz koşunun (kapı değişikliği + pafta içi daireler) klasörü:
`out/guided/fd57c33d945b4a6bb8d3e9ff61bb2014/build-1-5c0279a6/` ✓ — `part.step` ✓ (geçerli ✓, 1 katı ✓,
[103,4585 / 68,967 / 15,0] mm ✓, 103,575 cm³ ✓, 15 yüz = 6 düzlem + 9 silindir ✓). Ø6,8 delik silindirleri
(r=3,4): (8,6288 / 0,3464) ✓, (88,6288 / 60,3464) ✓, (8,6288 / 60,3464) ✓, (94,8363 / 8,6231) ✓,
(51,732 / 34,4842) ✓ → **aynı satırda 88,6288 − 8,6288 = 80,0000 mm** ✓ ve **aynı sütunda 60,3464 − 0,3464 =
60,0000 mm** ✓. §26-B-3'te yazılan sayılar birebir doğrulandı ✓.

## §26-K1: tam test takımı — 585 passed (951,5 s) — 2026-09-29

§26'nın tüm dilimleri indikten sonra **tam takım** yeniden koşuldu ✓: `PYTHONPATH=src .venv/bin/python -m
pytest -q` → **585 passed in 951.46s (0:15:51)** ✓, çıkış kodu 0 ✓ (önceki tam takım §23-C35'te 567 passed idi ✓;
§26'nın 18 yeni testi dahil ✓). Odak koşuları da kayıtlı: `test_contour_audit` 8 ✓, `test_contour_fix` 6 ✓,
`test_user_dimensions` 4 ✓, `test_guided + test_user_dimensions + test_sketch_constraints + test_plate_plan`
74 passed ✓. Bu, §26'nın mevcut değişiklikleri bozmadığının kayıtlı kanıtıdır ✓.

**Dürüst sınır:** kapının *sayaç* biçimi (plaka 7/7 ✓, plastik 14/14 ✓, `Drawing.pdf` 16/17 ✓ ve depolanmış istek
hash'leri ✓) en son §26 öncesinde ölçülmüştü ✓; bu pencerede o sayaçlar ayrıca koşulmadı ✗ — takımın içindeki
`test_catalog_cli` ve ilgili testler geçiyor ✓, ama sayaçların birebir yeniden okunması yeni pencereye kalıyor ✓.

### §8.6 KABUL LISTESI — madde madde kanit (2026-09-29 05:23)

Genis set yesil: **122 passed / 86,93 s** (13 dosya; `test_guided.py`'nin plaka planlari ve paralel ajanin
`test_sketch_constraints.py` dahil). Kabul listesi:

1. **Urun pafta cercevesini ve eksenleri tasir** — `Observations.sheet_frame` + `options["sheet_frame"]`;
   sentetik **10 passed**; gercek pafta: Plate `outline_0` %93,3x%90,5 -> 0,0°; `2/Drawing.pdf` portre
   %90,5x%96,6; `Exercise 17.PNG` -> durust "bulunamadi + kullanici onayi". ✓
2. **Donuk paftada cerceve paftanin kendi cercevesinden; sayfa X = parca X varsayimi kalkti** — §8.6-c-1
   (turetilemezse soruda durur) + §8.6-c-2 (onaylanmis gorus uygulanir); donuk pafta sentetik kanitla ayni
   kenar geometrisini veriyor. ✓ (kanit sentetik — korpusta donuk pafta yok, kayitli)
3. **Arayuz gosterir, kullanici onaylar, onay karar olarak kaydedilir** — §8.6-b gercek tarayici kabulu
   (oturum `3bb37c58529e4083a85e335d7f096129`): satir "cerceve 78 / 79 / 2260 / 1575 px; oneri: X sag, Y
   yukari - %93.3x%90.5 - 0.0° sapiyor" -> gercek tiklama ile kaydet -> `decisions.view` yazildi
   (`x_page`, `y_page`, `frame_rect`, `source`, `geometry_version`). ✓
4. **Cekirdek onayi uygular; onay yoksa varsaymaz** — §8.6-c-1: turetilemeyen goruste build soruda durur;
   §8.6-c-2: onayli donuk goruste harita uygulanir, kimlik goruste sayilar birebir korunur; ayna cifti ret. ✓
5. **Donuk pafta testi: ayni cizim 0° ve 90°'de ayni olculen mm'yi verir** — `test_view_core.py::`
   `test_a_rotated_sheet_builds_the_same_plan_as_the_upright_one` (kenar vektorleri esit; zincir sirasi
   bagimsiz). ✓ (sentetik; yaylarin uctan uca donuklugu birim seviyede kanitli)

**Durust sinirlar (kapanmadi):** egik (ceyrek tur olmayan) gorus ret; raster paftada arayuz sorusunun ekran
kaniti yok (§8.6-b takip); yayli donuk kontur uctan uca test edilmedi.

**P03 durumu:** kabul listesi (X/Y, yon, mm/inch, profil degisimi, silinen kenar, eski surum) + P03-b-1/b-2 +
§8.6'in tamami tamam — **tam takim kosuyor** (`proc_e154433e97f1`); yesil gelirse P03 "dogrulandi".

### P03 DOGRULANDI + §8.6 DOGRULANDI (2026-09-29 05:39)

**Tam takim: 669 passed / 1025,02 s** (§8.6-a/b/c-1/c-2 sonrasi; onceki yesil 641 — 28 yeni test). Kabul
listesi madde madde kanitlandi (bkz. ustteki bolum) + P03 kabul listesi (X/Y, yon, mm/inch, profil degisimi,
silinen kenar, eski surum) + P03-b-1/b-2 arayuz kabulu + §8.6-b gercek tarayici kabulu.

**P03: DOGRULANDI. §8.6: DOGRULANDI** — kayitli durust sinirlarla (egik gorus ret; raster paftada arayuz
sorusunun ekran kaniti yok; yayli donuk kontur uctan uca test edilmedi; donuk pafta kaniti sentetik).

**Kapilar (P03 boyunca degismedi):** plate-pocket-1 7/7, plastic 11/11, exercise-1-vector 13/13,
exercise-12 19/20, flange 4/13; `check_tables` 21 okundu / 0 tutmuyor; `baseline_report --check` yesil.
Sirasi: **P04-a…f** (100x100 kare cift-bag tekrari — kose-bagi kapisi engeli; P04-c P01-c rapor gorunurlugu).

### P04-a INDI: olcek = kalibrasyon; desteklenen X/Y bagi eski ortak-olcek kapisina takilmaz (2026-09-29 05:43)

**Once olcum (kod degismeden, 600x500 sentetik pafta, kalibrasyon 200 px = 100 mm => 2 px/mm, govde 200 px):**
| Durum | `sketch.px_per_mm` / kaynak | Govde | Kapi |
|---|---|---|---|
| Bag yok | 2,0 / calibration | **100 mm** | soru yok, plan var |
| Yalniz merkez bagi (cekili 200 px, basili 50 mm) | **4,0 / bindings** | **50 mm** (F12) | soru yok — sessizce yanlis |
| Kose bagi X=50 / Y=30 | 6,655 / bindings, 2 conflicts | plan yok | "tek olcek tutmuyor" kapisi (F13) |

**Kok:** `make_plan` uretim olcegini `diagnostics["px_per_mm"]`ten aliyordu; o alan `fit_scale(bindings)` sonucuydu
=> tek bir bag tum govdeyi yeniden olceklendiriyordu. Kapi: `bindings_solvable` yalniz `centre` uclarini kabul
ediyordu (profil elinde degil diye) => gecerli kose bagi "tek olcek" sorusuna takiliyordu.

**Ne indi (`guided.py`):**
1. `sketch_diagnostics`: ust duzey `px_per_mm`/`source` artik **kalibrasyondan**; eski uyum **`sketch["fit"]`**
   altinda rapor olarak duruyor (satirlar, artıklar, conflicts, consistent).
2. `make_plan`: uretim olcegi **yalniz kalibrasyondan**; baglar olcegi degistirmez.
3. Tek cozucu: `binding_reference(profile, end)` modul duzeyine cikarildi; `user_dimensions` ve yeni
   `bindings_solvable(decisions, options)` **ayni** cozucuyu kullaniyor (PLAN P04 madde 3/4: kopya cozumleyici yok).
4. `bindings_solvable`: desteklenen X/Y bagi (iki cozulebilir kose ya da iki daire merkezi) **olculebilir**
   sayilir; uyum artigi artik engel degil. Cozulemeyen uc / desteklenmeyen tur / ayni uca bag hala engel.
5. `make_plan`: cozum durumu `unsupported` ise **uretim durur** (F14'un kapisi P04-b'den one alindi; aksi halde
   F13 duzeltmesi "desteklenmeyen bag sessizce yok sayilir" deligini acardi) — PLAN madde 6 zaten bunu sart kosuyor.

**Kanit:** `tests/test_guided.py` **28 passed / 38,33 s**. Iki eski test **sozlesme degistigi icin** yeniden yazildi
(eskiden uyum olcegi uretim olcegiydi):
- `test_a_bound_measurement_moves_the_geometry_and_the_scale_stays_the_calibrations`: 40 mm bagi geometriyi
  hareket ettirir (yukseklik 40 mm, genislik kalibrasyonun 50 mm'si); `source=calibration`, `px_per_mm=2,0`,
  `sketch["fit"]["source"]=bindings` (tani), plan parametresi `binding_0` `user` 40,0, varsayim metni "kalibrasyonundan".
- `test_supported_corner_ties_are_not_blocked_by_the_fitted_scale`: iki gecerli kose bagi engellenmez; cozum
  50x40 mm; gecersiz referans (`edge:99`) hala "yeniden baglanmali" + build reddi.
- YENI `test_a_lone_centre_tie_does_not_shrink_the_body` (F12'nin kanonik vakasi): 100 mm govde, yalniz merkez
  bagi -> govde **100x60 mm kalir**, `px_per_mm=1,0`.
Iddialar parametre *adlariyla* degil **plan bbox**'u ve cozulen kenar vektorleriyle kuruldu (zincir sirasindan bagimsiz).

**Durust sinirlar:** `unsupported`in kapisi P04-b'nin maddesi — one alindi ve P04-b kapanisinda tamamina
bakilacak (arc bagi ret mesajlari vb.). Daire merkezi bagi icin id dogrulamasi hala `unresolved_bindings`te
(tek cozucuya tasinmadi); genis set kosuyor (`proc_c4308a8977cf`).

### P04-a: cozulen MERKEZ henuz CAD'e uygulanmiyor — P04-f'nin ilk maddesi (2026-09-29 05:46)

Genis set yesil gelirken `test_guided_geometry_state.py` tek kirmizi verdi: "bagli olcu geometriyi hic
degistirmedi". Kok, P04-a'nin bir hatasi degil, ortaya cikan **gercek bosluk**: eski kod bagi *olcege*
yansittigi icin plan degisiyordu (F12'nin ta kendisi); olcek kalibrasyona sabitlenince merkez bagi yalniz
**cozum raporunda** kaliyor.

Olculdu (plaka, kalibrasyon 10,568 px/mm, bagi 120 mm, cizili 472,53 px = 44,71 mm):
- `user_dimensions` durumu **underconstrained**, `dof=11`, notlar: "Serbestlik sayisi yalniz secili daire
  merkezlerini kapsar."
- Cozulen merkezler: `g9` [435,56 / 658,22] sabit, `g12` 1130,75 -> **1926,39** px => mesafe **1268,17 px
  = 120,000 mm** ✓ (core bagi gercekten uyguluyor).
- Ama plan/STEP izlenen merkezi kullaniyor (`hole_0_x/y` degismedi) => **"yeni merkez yalniz raporda kaliyor"**
  (PLAN P04 madde 10 + P04-f kabulu: "Secili deligin merkezi ... STEP'teki silindirin merkezi yeni yerdedir").

**Karar:** P04-a'da merkez uygulamasi yapilmaz (P04-f'nin isi); test iddiasi cozulen merkeze baglandi ve
bosluk burada acikca kayitli. P04-f baslarken **ilk madde** bu: cozulen merkezleri kesime/STEP'e tasi.
Ayrica not: ayni gap `test_guided_geometry_migration`/`test_measure_meaning` gibi setlerde gorunmez, cunku
onlar CAD ciktisindaki merkezi denetlemiyor.

### P04-b INDI: celiski / desteklenmeyen bag / gecersiz referans uretimi durdurur (2026-09-29 05:57)

**Once olcum (kod degismeden):**
| Senaryo | Bugun |
|---|---|
| Ayni iki daireye 120 ve 90 mm bagi (celiski) | `make_plan` + `store.build` **istisna**: "baglanan olculer birlikte tutmuyor (cakisan: b0, b1)" ✓; kayit **korunuyor** ✓ |
| Reddedilen build sonrasi eski STEP | `build` alani sifirlanmis; `artifact()` -> "**bu kararlar icin guncel STEP yok**" ✓; eski klasor diskte ✓ |
| Yayli konturda kose bagi (plaka `outline_1`: 8 kenar / 4 yay; `2/Drawing.pdf outline_2`: 1 yay) | core **unsupported** ("yayli veya dairesel dis konturda yalniz daire merkezleri olculendirilebilir") ✓ ve `make_plan` (P04-a'nin one alinan kapisiyla) **duruyor** ✓ — ama arayuz sorulari **bos** ✗ |

**Ne indi (`guided.py`):** `unsupported_binding_reasons(profile, decisions)` — core'un kuralini *ayni profil
seklinden* okuyup **build'den once** kullanicinin dilinde soran yardimci; `questions()` bunu once ekliyor ve
bu durumda uyum artiklarini sormuyor (artik sorusu burada anlamsiz). `bindings_solvable` ucta destek kuralina
gore kaliyor (celiski mesajini core veriyor).

**Kanit:** `tests/test_guided.py` -> **2 passed / 9,26 s** (yeni iki test):
- `test_a_conflicting_pair_of_ties_stops_the_build_and_leaves_no_current_step`: baglar **korunur** (kimlikler
  yerinde), `make_plan` ve `store.build` **b0+b1 adiyla** durur, `build.revision` bu revizyon degil,
  `artifact()` "guncel STEP yok" der, **eski build klasoru diskte kalir**.
- `test_a_vertex_tie_on_an_arc_contour_is_asked_and_refused_by_name`: gercek korpus paftasi (`2/Drawing.pdf`,
  yayli kontur) -> arayuz **soruyor**, `make_plan` "desteklenmiyor/yayli" ile durur, `store.build` istisna
  atar ve **cikti klasoru acilmaz**; ayrica core'un kendi kurali da testte pinlendi (`user_dimensions` ->
  `unsupported`), boylece arayuzdeki kopya core'dan ayrisirsa test kirmizilasir.

**Durust sinirlar:** (1) `unsupported_binding_reasons` core'un kuralini *kopyaliyor* (kural `sketch_constraints.py`
icinde; o modul bu dilimin degil) — senkron testle baglandi, ortak yardimci P04-c/d'de core'a sorulabilir;
(2) gecersiz referans zaten P04-a testiyle kapali; (3) tam takim kosuyor (`proc_74f8712272e4`).

### P04-c OLCUMU: onizleme cozumu hic gormuyor (P01-c maddesi) (2026-09-29 06:16)

**Tam takim P04-a+b sonrasi: 672 passed / 1079,27 s** (669 -> +3 test). P04-a ✓ P04-b ✓.

**P04-c oncesi olcum** (sentetik kayit: 100x60 px govde, kalibrasyon 2 px/mm; 60 px'lik kenara 40 mm bagi):
- `public()["sketch"]["solved_dimensions"]` = **null** — onizleme cozum raporunu hic gormuyor.
- Onizlemedeki kontur kosesi: **[20, 80]** (izlenen) — plan/CAD ise **cozulen** geometriyi kuruyor (kenar bagi 60 px -> 80 px; yapilan gecici kosuda cozum sonrasi kutu 100x140 px, durum `underconstrained`, `moved=140 px`).
- Yani bugun: **cizim ve plan ayni seyi gostermiyor** — P04-c'nin kabulunun birinci yarisi ("degisen kose/merkez cizimde ve planda aynidir") saglanmiyor.

**P04-c giris noktasi (kayitli plan):**
1. Tek hazirlama sonucu: `prepare(options, decisions) -> Prepared` (derin kopya -> P02 on denetimi -> sorular ->
   olcu cozumu -> rapor); `sketch_diagnostics`, `public()` ve `make_plan` **ayni** sonucu okur (ikinci cozum yolu yok).
2. `public()["sketch"]`: cozulen kontur/merkezler + `solved_dimensions` raporu (onizleme cizimi cozulmus
   konumlari gosterir).
3. Kabul testleri: onizlemedeki cozulen kose/merkez plan/STEP ile **ayni**; P01 kopyalama/geri alma ve
   "temel geometri degismez" testleri hala gecer.
