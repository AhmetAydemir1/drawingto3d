# Changes, what they bought, and what they cost

One entry per change, in the order it was made: the mechanism, the measured benefit, the cost or risk it
carries, and how it was verified. The numbers themselves live in `eval/README.md` and in
`out/frontend/<case>.json`; this file is the accounting.

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
nothing at all (above), and — found while measuring the pixel floor — the sheet that has the most of those
carries a different bug class, **a number matched to a line that was never its line**: 15 of
`plastic-enclosure-1`'s 20 auditable readings are small numbers standing on long lines (`1.50` on 113.5 px,
`2` on 181.5 px, `4.00` on 69 px). The audit names them correctly and it costs no coverage on that sheet
(8/11 with those numbers found anyway), but the anchors of those records are wrong, which matters the day
the reading is used for anything but counting.

Characterised (`out/probe/probe_mispairing.py`, output in `out/probe/mispairing.txt`): for each named
reading, *no stroke near the number fits its value at the sheet's own scale*. The `1.50` at box (1077,193)
was given a 113.5 px line and the strokes within 250 px of it measure 26.4, 11.0, 18.9, 18.9, 12.3 and
22.3 mm; `4.80` was given 69 px and the strokes near it measure 15.9, 18.2, 11.0, 17.9, 11.0 and 16.6 mm
where 4.8 mm is 18.8 px. So the gate is attaching a *neighbouring* dimension line to a number that has none
of its own — the same shape as the leader-carried `50,00`: a diameter or thickness callout needs no line.
The honest repair has the same two-phase shape as the re-read above (read, fit the sheet's scale, then check
each record's own line against it): prefer a stroke near the number whose length fits the value, and where
none does, record the reading without anchors rather than with a line that is not its own. That is a change
with its own whole-set sweep, so it is the next piece of work rather than a footnote to this one.

A scan of every cluster the gate refuses that tesseract *would* give a number for is
`out/probe/probe_refused_reads.py` — 30 on the plate, and what is behind them is not one kind of thing: the
printed `6,80` (twice — the note's number, which the gate refused for its leader and which the committed
change reads), the printed `50,00` (read as `250,00` from a crop 32 px wider to the left, where the accepted
cluster's own crop reads `90,00`), four numbers an accepted cluster already covers (`100,00`, `80,00`,
`60,00`, `16`), and the rest phantoms (`R8`, `9)`, `“3`, `3}`, `<6`, `2.`, `7`). A future change here has to
separate those kinds by something other than the possibility of a read — which is what the re-read above
does for the readings that carry their own line.
