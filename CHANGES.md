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
  negotiable; the guard removes it. `28.006` is also what the guard costs: a cluster of fragments whose
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

## Measured, not yet changed

The raster half of the callout: splitting a line of drawn words so that the number inside it is read on its
own. Measured on the plate's raster path — the `4` is a cluster of one, the three glyphs of `6,80` cluster
with the two glyphs of the line *below* them into one five-glyph cluster spanning 72 px and two printed
lines, and the crop of that is what tesseract answers `08°9` for. Evidence and the failing case are in
`eval/README.md` (Known gaps) and `out/probe/probe_callout_cluster.py`.
