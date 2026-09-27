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
