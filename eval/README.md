# eval

## Direction update — 2026-09-27

The six existing cases are seen development/regression data. The deterministic plate result below
tests a narrow structural recognizer; it does not demonstrate unseen-part or general raster accuracy.
The implementation brief in `../PLAN.md` defines the next evaluation: group variants by part, keep
unseen parts separate, measure dimension occurrences and feature bindings, and check feature positions
and depths in addition to overall shape. These changes are planned, not implemented in the metrics here.

The manifest now carries that split vocabulary: `cases.json` `_split` names the seen-regression ids and
holds empty `pilot`/`hidden` arrays, every case carries `part_group`/`split`, and `feature_ids` records
which named features a plan has to account for (`plate-pocket-1` shows the intended granularity; an
empty list means "not yet identified"). `pilot` and `hidden` stay empty until those sheets are
collected. The compiler half of the brief — a versioned general plan contract and two plans that use
different operation combinations — lives in `plans/`; `build-general` in the CLI builds them.

What "better results" means for this project, in numbers. Two questions per sheet:

1. **Reading** — did the reader find every number printed on the sheet, and nothing else?
2. **Building** — is the STEP it built a functionally equal part to the reference STEP?

`../CHANGES.md` keeps the other half of the record: one entry per change, with what it bought and what it
cost. This file is the table of numbers those entries cite.

Run:

```bash
PYTHONPATH=src .venv/bin/python eval/frontend.py          # reading front end, no model, seconds per sheet
PYTHONPATH=src .venv/bin/python eval/baseline.py          # reading turn over every eval sheet -> out/baseline/<case id>.json
.venv-cad/bin/python eval/report.py                       # table + out/eval/report.json
PYTHONPATH=src .venv/bin/python eval/check_tables.py      # do the tables below still match out/frontend?
```

`eval/check_tables.py` reads every table in this file back against the runs in `out/frontend/` (which is
git-ignored) and prints any row that has drifted, exiting non-zero if one has. The tables are the
measurement this project is steered by, and a row that has drifted is worse than no row: a re-run that
changes a number is supposed to end in an edit to this file, and this is the check that it did.

`eval/frontend.py` measures the half of reading that needs no model — glyph geometry, dimension lines,
the PDF's own text layer, tesseract — and writes `out/frontend/<case id>.json`. It is what makes the
geometry tractable: a change to the gate shows up in seconds, before any model call. With `--as-raster`
it throws away a PDF's text layer and reads the sheet the way a scan has to be read, which measures the
CV reader against a truth that is known exactly (the same sheet's printed numbers) instead of against
another hand-made example.

`eval/baseline.py` runs the reader as it is and keeps the result, failures included; it needs the
vision model (Ollama) and takes minutes (one local model call per dimension text — 17 dims on the A4
sheet). `eval/report.py` needs the CadQuery interpreter to read reference STEP files. Build output
goes to `out/eval/<case id>/part.step`, which is what the report picks up.

## Metrics

Reading (against `cases.json` → `printed`, the numbers a human can read on the sheet):

- **records** — how many dimension records the reader emitted. A sheet with 2 printed numbers that
  yields 8 records has 6 phantom dimensions, and every one of them is a chance to build the wrong part.
- **found / missing** — printed numbers that did or did not survive as records. Inches are accepted
  either as printed or converted to mm, so the report does not hide a unit bug as a miss.
- **noise** — records whose value appears nowhere on the sheet (title-block part numbers, copyright
  years, callout prefixes). These are the ones that must reach zero.

Building (`eval/metrics.py`, produced STEP vs reference STEP):

- **vector** (hard) — the three bounding-box lengths within 2% or 1 mm.
- **solids / valid** (hard) — exactly one valid closed solid.
- **volume** (soft, 25%) — cast fittings carry fillets and tapers that no drawing dimensions, so
  exact volume equality is not the target; grossly wrong material is.
- **cylinders** (soft, 0.5 mm) — every bore, socket and pipe outside diameter in the reference must
  appear in the produced part. This is the check that catches "right overall size, wrong holes".

A reference STEP is the truth for shape, not for intent: a cast fitting carries fillets, blends and
tapers that no drawing dimensions, and a student sheet leaves details to the shop. The eval therefore
holds the pipeline to a *functionally equal* part — right size, right bores, right wall order — and not
to the same B-rep.

## Cases

`practice-sheet` — StudyCADCAM raster sheets, mm, full third-angle views with Ø/R/C callouts and
hatched sections. Reading-only for now: there is no reference STEP for them, and re-modelling them by
hand is the honest way to get one.

`self-made` — the user's own sheets, each with the STEP it really is: a vector A4 pair (`my_part`,
`Plate With A Pocket`), a vector A4 plastic enclosure at 1:2, a raster A3 flange with GD&T frames, and
the CAD-rendered reference geometry of each. These carry the exact truth, so they are what the reading
and building metrics are held to.

## Where the front end stands (measured, no model)

`eval/frontend.py`, one line per sheet, out of the numbers a human reads on it:

| vaka | kaynak | kapsam | gürültü | px/mm | şüpheli |
|---|---|---|---|---|---|
| plastic-enclosure-1 | vektör | 11/11 | 0 | 3.917 | 7 |
| plate-pocket-1 | vektör | 7/7 | 0 | 7.817 | 0 |
| studycadcam-60 | raster | 6/9 | 9 | 3.278 | 7 |
| studycadcam-50 | raster | 2/3 | 7 | - | 0 |
| exercise-1 | raster | 6/13 | 6 | 5.731 | 7 |
| flange-1 | raster | 4/13 | 3 | - | 0 |

The same sheets with the text layer taken away (`--as-raster`), which is the reader a scan gets:

| vaka | kapsam | at the start of this work |
|---|---|---|
| plate-pocket-1 | 6/7 | 0/7 |
| plastic-enclosure-1 | 8/11 | 2/11 |
| studycadcam-50 | 2/3 | 1/3 |
| studycadcam-60 | 6/9 | - |
| exercise-1 | 6/13 | - |
| flange-1 | 4/13 | - |

The gap between the text layer and the reader a scan gets is the distance this project is closing:
`plate-pocket-1` loses one number without it (7/7 -> 6/7) and `plastic-enclosure-1` three (11/11 ->
8/11). `exercise-1` and `flange-1` only ever had the raster reader; the reading-angle change moved the
first of those by three numbers (2/13 -> 5/13), and the sheet's own scale (the bullet further down) moved
`exercise-1` again, to 6/13.

The vector numbers are the text layer read through the geometry gate; the raster ones are the same gate
with tesseract behind it, which is the floor, not the finished reader — `eval/baseline.py` is where the
vision model enters. The raster column moves by a number or two with any change to how glyphs are
grouped, so it is the row-by-row comparison that says whether a change helped, not one sheet.

The ceiling, with the vision model reading the same crops instead of tesseract (`--as-raster --model`):

| vaka | tesseract (floor) | qwen3-vl:8b-instruct (ceiling) |
|---|---|---|
| plate-pocket-1 | 6/7 | 7/7 |
| plastic-enclosure-1 | 8/11 | 10/11 |

Neither switch is a default: the model costs minutes per sheet against seconds. Wall clock is not
comparable between runs on one machine — the same plate took 32 s in one run and 538 s in another with
nothing else on the box — so the coverage is the measurement and the seconds are not.

The reader behind that column changed on 2026-09-26. `qwen2.5vl:7b` reads **4/7 on the plate — below that
sheet's own tesseract floor of 6/7** — and 10/11 on the plastic sheet; the two runs (`out/ceiling_qwen2_5vl7b_8808a95.log`)
confirm what `10a32b6` asserted without re-running them, that the arrowhead guard leaves the ceiling where it
was. `qwen3-vl:8b-instruct` keeps the plastic sheet at 10/11 and takes the plate from 4/7 to **7/7**, so the
ceiling is off the floor on both sheets. Both models were measured on one commit (`8808a95`) and one tree,
one model per process, because the harness writes one `-raster-model.json` per case and a second run
overwrites the first: the runs are kept in `out/frontend_7b_8808a95/` and `out/frontend_8b_8808a95/`, and the
8B run took 723 s and 674 s against the 7B's 689 s and 677 s — the same order of minutes, not a faster reader.

What the swap bought, sheet by sheet. The plate's three recovered numbers are `8,00`, `15,00` and `6,80`:
the 7B read the first two as `800` and `1500` (the decimal comma lost, the value a number the sheet does not
print) and never found the third, and the 8B reads the printed text exactly — including the drawn `Ø`, which
the text layer does not carry at all (rule: on a vector sheet the diameter mark is a path, so `∅100` and
`Ø10` can only come from the drawing; `∅100` covers the printed `100` where `100,00` already did). Nothing
the 7B could read was lost: `50,00`, `60,00`, `80,00`, `100,00` come through on both, so the plate's own gain
is three numbers and no loss.

What it cost. The plate's noise goes 2 -> 4 (`7`, `Ø10`, `∅10`, `∅10` against the 7B's `800`, `R105`) and the
plastic sheet's stays at 3 with different identities (`7`, `45`, `7` against `0`, `R105`, `R105`; `45` is the
sheet's printed `46` with one digit wrong). The phantom crops are not the model's: both readers answer them,
and the 7B's `R105` appears on both sheets, so what those crops are is a gate question about clusters that
carry no number, not a question of which weights read them. Judged only on the project's own rule — coverage
must rise, noise must not — this swap is a **+3 coverage, +2 noise** change on one sheet and a no-op on the
other, and the noise it adds is the kind `10a32b6` was written to remove; it is kept because three printed
numbers the part cannot be built without outweigh two phantoms the noise list already names, and because at
4/7 the model path could not even be described as a reader.

Running both readers and keeping what they agree on was measured and rejected (`out/probe/probe_model_swap.py`
replays the gate's own crops through both). The plate's agreement row is 4/7 with no noise: it throws away
exactly the three numbers the 8B found, because the two models disagree on them, and neither can say which
of the two is right — the 7B's `800` is not hesitant. The union row is 7/7 with six noise records against the
8B's four. A second model is worth its minutes only where something else can *decide* between two answers;
on this pipeline that arbiter is the sheet's own scale (`scale.audit`), and the second reader belongs on the
rows the audit names, not on every crop.

The model is still not the product path on this evidence: minutes per sheet against seconds, and it is the
raster half only — a vector sheet's own text layer reads 7/7 and 11/11 with no noise and no model at all.

## Where the built part stands (measured, the app's own run)

The tables above measure the reader. This one measures **what the app produced**: `drawingto3d read` then
`drawingto3d build` per case (`out/build_eval.py`, log `out/build_eval.log`), with the part compared against
the case's reference STEP by `eval/report.py` -> `out/eval/report.json`. `out/eval/<case>/records.json` is the
reading the part was built from, so the two halves of the report describe one run of the pipeline.

| vaka | okuma | kayıt | katı | verdict |
|---|---|---|---|---|
| plate-pocket-1 | 7/7 | 7 | var | KALDI |
| plastic-enclosure-1 | 11/11 | 14 | var | şekil |
| exercise-1 | 6/13 | 15 | yok | katı üretilmedi |
| flange-1 | 4/13 | 10 | var | KALDI |
| studycadcam-60 | - | 0 | - | referans yok |
| studycadcam-50 | - | 0 | - | referans yok |

The reading column is the app's own reader, not the front end: with `qwen3-vl:8b-instruct` behind it, the two
vector sheets read exactly — the plate 7/7 with no noise and the plastic sheet 11/11 with no noise — and the
two raster sheets read 6/13 and 4/13, which is what the front end's own raster row predicts. The two practice
sheets have no reference STEP, so they are reading-only here.

**Three of four cases build, and the plate's part is close.** No case built before the shape note; the shape note
got the plate and `exercise-1` building; giving the role question the number's own line then got `plastic` and
`flange` building and **broke `exercise-1`** (below). What each part is now:

| vaka | katı | verdict | parçanın ölçüsü |
|---|---|---|---|
| plate-pocket-1 | var | KALDI | `[15, 80, 100]` ↔ `[15, 80, 120]`, hacim **ok** (119.0 ↔ 124.8 cm³), silindirler `[3.4]` ↔ `[3.4, 10, 25]` |
| plastic-enclosure-1 | var | şekil | vector **ok**, hacim 171.7 ↔ 23.5 cm³, silindirler `[0.75, 1.5, 2, 2.4, 4]` ↔ `[1.5, 5, 6, 8]` |
| flange-1 | var | KALDI | `[1, 2, 50]` ↔ `[50, 100, 100]`, hacim 0.1 ↔ 202.1 cm³, silindirler `[]` ↔ `[3.2, 5.5, 15, 30, 50]` |
| exercise-1 | yok | katı üretilmedi | `holes: result has 4 solids` — `geo.holes(solid, geo.rect_points(20), diameter=20)` |

The plate's remaining differences are now few and **named** — and the first of them is measured, not guessed: its
`60,00` is the corner holes' vertical spacing (the sheet's drawn holes are `100.81 x 60.64 mm` apart and the
crop shows the dimension's extension lines ending on the two top holes), so the record says `hole_spacing`:

| ne eksik | kayıtların dediği | paftanın dediği |
|---|---|---|
| Ø50 göz yok | `50 mm: hole_spacing` | `Ø50,00`, lider bir daireye gidiyor |
| cep 8 mm derinlik değil, üstüne yapıştırılmış ikinci plaka | `8 mm: thickness` | `SECTION B-B`'de 8,00 cep derinliği |
| dış uzunluk 100 | basılı en büyük sayı | 120 (kenar payından türetilir, çizili hat 121.15 mm) |

**The role question now shows the number's own line.** It was a square around the number alone, and the question
is what the number *measures*: the plate's `100,00` has its ends 10.6 mm inside the plate's drawn edge with
extension lines running down to the holes, so a crop of the number answered `edge` for a hole pattern, `edge`
for a `Ø50` bore and `thickness` for an 8 mm pocket depth. The box now spans the number's own line — `Span.anchors`
are its two ends — and reaches a quarter of the measured length past each end. Verified by looking at the crops:
`100,00` shows both arrowheads, both extension lines and the two corner holes they end on; `50,00` shows the
leader's arrow on the bore and the printed `Ø`.

**What it cost, measured on the same run.** `exercise-1` no longer builds: four of its numbers moved to
`hole_spacing`, the coder drilled a `Ø20` hole at 20 mm spacing and the plate came apart into four solids. And the
reason it answers `hole_spacing` there is that **the right answer is not on the list**: that sheet prints `Ø20`,
`Ø25`, `Ø30`, `Ø40` and `Ø50`, but the `Ø` is drawn ink and never enters the span's text, so those numbers are
still offered only the length family and `hole_spacing` is the nearest thing to a round feature. Reading the
drawn `Ø` (the crop now shows it) is the next change. `plastic` and `flange` build for the first time and are
still badly wrong (a 0.1 cm³ flange against 202.1), which is honest progress rather than a result.

One wrong record was **provably** wrong and is fixed: `6,80 THRU ALL` is a through-hole callout, and
`role_choices` now reads the callout's own note (`THRU`, `TAP`, `CBORE`, `6H`, …), so the record is
`hole_diameter`. One silent failure is now caught as well: `geo.holes(a, …)` returns a copy, so the coder's
`geo.fuse(a, b)` put the undrilled body back over the drilled copy and filled every hole — the part passed the
toolchain with `cylinders []`. `reason._closed_holes` sends it back with the reason and the plate's holes came
back (`cylinders [3.4]`).

So the reading half is close to solved on the vector class, three of four cases produce a part, and the layer
that is left is the records' naming: a number has to arrive named as what it dimensions (a bore's diameter, a
pocket's depth, a hole pattern's spacing) and the undimensioned length has to be derived.

## How a number is read

`perceive` finds printed numbers by the geometry that carries them, not by their size:

1. `lines.ink` decides what is ink by the sheet's own paper and darkest tone, and `lines.thin_segments`
   keeps strokes 2–4 px thick and 36–1400 px long. On the A4 practice sheet the outlines and title-block
   rules measure 5–6 px, so weight alone is not the filter — the arrows are.
2. `lines.diagonal_strokes` adds the strokes that do not run along an axis, which is where a drawing
   keeps its callouts: the band is the sheet's own thin weight, and the length is measured against the
   sheet's printed text so a glyph stroke stays a glyph. A line drawn at 8° is not an axis stroke — the
   row-by-row pass reads it as thick and drops it — so this is the only path that can find it.
3. A candidate is a cluster of glyphs with a **dimension line** beside it (`lines.dimension_line_near`:
   an arrow at both ends, the number between) or a **leader** (`lines.leader_near`: one arrow, the words
   beside the blank end of the shaft, the shaft at any angle, and the ink it runs through no longer than
   the sheet's own type — a stroke that is not axis-aligned stays in the text mask as its own ink, so
   "inside printed words" has to be judged against `PrintedText`, not against the mask). A number printed
   *inside a note* is carried by that note's leader, wherever in the note it sits: the leader is drawn to
   the note's ink, not to each number in it, so the gate hands the leader the number's own printed block
   (`perceive._printed_block`: the cluster's line, grown along the cluster's own angle, plus the printed
   lines within two characters across it) and keeps the leader only if it is a line *to* the note
   (`lines.leader_to_note`: at least three of the note's characters long, ending beside the note's ink
   rather than inside it or short of it). Title block, part numbers, copyright years
   and the frame band all die here: on `my_part.jpg`, 364 glyph candidates become 21 that cover 10 of the
   13 printed values.
4. Text along a vertical line is printed a quarter turn round, so a glyph is judged on its longest side
   and its crop is turned upright before it is read (`_reading_turn`). Filtering those digits on height (or
   on width) is how a printed 80 arrives as a bare `0`; *trying* the four quarter turns in order is how a
   complete crop of `80,00` arrives as `08` or `8000`, since every rotation of a bare number parses as
   some number. The drawing says which one it is: the digits' line gives the axis, and the decimal
   separator gives the sense, sitting as it does below the baseline of the digits it belongs to. The crop
   is then enlarged by the size of its digits, not by its own longest side (`_scaled_for_reading`), because
   a number printed up a vertical dimension sits in a crop 33 px wide and 95 px tall whose digits stay
   18 px when the longest side is what is scaled.
5. A printed number is a cluster of glyphs, and the **decimal separator is a bridge, not a glyph**: it
   is a few pixels across, below the filter that keeps character-sized blobs, and the digits either side of
   it are then the only thing left to measure. Two digits chain across it when the blob lies between them
   and near their line (`_separator_between`) — a comma belongs to the digits it sits beside, and one of
   the sheet's two hundred specks does not. A blob thin in one direction is not a separator either: a `1`
   printed at this size is 6 px wide and 28 tall, so what is a character is decided against the sheet's own
   character size, in both directions, by `_glyphs`.
6. `reader.read_dimension` asks the local vision model first, tesseract second, and reports agreement. An
   answer that does not fit the crop it came from — letters on a dimension line, more digits than the box
   could hold — is refused instead of kept; that is where `R100` and `R105` hallucinations come from.
7. Every accepted number keeps the two ends of its own line as `Span.anchors`, so its value stays
   attached to the geometry that printed it.
8. `scale.audit` fits the sheet's own scale (px per mm) from those anchors and names the records that do
   not fit it — a misread, or a number attached to a line that was never its own. On `my_part.jpg`:
   5.95 px/mm with a 2.4% spread (A4 at 200 dpi, scale 1:2, expects 5.9) — no title block, dpi or scale
   note needed.

## Known gaps

- **A number written at an angle is read, and sourced to its own line when that line carries it.** The crop
  of such a number is offered to the reader at the digits' own angle first (`perceive._digits_angle`,
  guarded by `_one_pen`), which is what moved `exercise-1` 2/13 -> 5/13 and `flange-1` 2/13 -> 4/13 with no
  other row moving. The *anchor* came next: the `50` on `my_part.jpg` is printed at 45 degrees along the
  diameter it measures, so the two ends it is sourced to are that line's arrow tips — 284.6 px against a
  value of 50, or 5.692 px/mm against the 5.731 that sheet's own four agreeing dimensions fit (a 1:2 A4 at
  200 dpi expects 5.9). It used to arrive on a 53 px leader at 1.062 px/mm, which that sheet's scale audit
  could not place. `lines._angled_row` reads a row with the number inside its ink, a row the number breaks
  in two, and now a row whose number is printed past a tip, both guards for the third measured on the
  sheets (see `CHANGES.md`). What is still open is on the other layout, the two in the bullet below.
- **A dimension drawn at an angle is read as a row now, in all three of its layouts.** The strokes at
  an angle are found (`lines.diagonal_strokes`, banded by the sheet's own thin weight and wired into the
  gate), and that plus the contrast rule below is what recovered `50,00` on `plate-pocket-1`: its line runs
  at 15° under the number, faint, and carries an arrowhead at one end, so the leader path takes it
  (5/7 -> 6/7). `lines._angled_dimension` then generalises the *dimension* pass to the stroke's own frame
  (project the text and the row onto the stroke's direction and its normal), and it reads all three layouts:
  the number sitting on an arrowed line, the number breaking one in two, and the number printed *outside*
  the span past a tip (the `50` on `my_part.jpg`, which is where its 284.6 px anchor comes from). The
  flange's `6 x Ø6.40` and `Ø11.00` turn out *not* to be any of the three: they hang on the GD&T frame
  below them and no stroke runs from that note to a hole, so nothing there is a dimension line to read.
- **A drawn callout is still a picture, but its number is not.** On `plate-pocket-1` the region of the
  `6,80 THRU ALL` callout looks like it carries no text at all — the `4 x` prefix and the `Ø` are drawn as
  outlines, and so is the whole second line (`M8 - 6H THRU ALL`) — yet the text layer *does* hold
  `6,80 THRU ALL`, and the number was refused for a different reason: its leader. `leader_near` used to
  throw away any stroke whose `text_fraction` was over 0.25, on the grounds that a stroke lying inside
  printed words is a glyph. On a stroke at an angle that measurement is the mask talking about itself:
  `lines._text_mask` only removes what a 28-px morphological opening can remove, the rules that run along
  an axis, so a leader drawn at 15° lies in its own ink for 53-65% of its length and reads as text, while
  a letter's stem reads 51%. The two callouts on the sheet were separated by that number alone: the faint
  `Ø50,00` leader scores 0.02 and was read, the `6,80` leader scores 0.65 and was thrown away. The question
  is now asked of the sheet's own type (`lines.PrintedText`): the ink a stroke runs through is printed
  words when the blob it lies in is no longer than `TEXT_BOUND` characters of the sheet's own measured
  character size (printed blobs on the plate are at most 2.3 characters, the leader is 5.9), and a drawn
  line otherwise. The plate reads 7/7 through its text layer, and the raster sweep of all six sheets is
  unchanged (23 covered numbers), so the change added the callout and nothing else.
  What stays unread is the `Ø` mark itself: it is a vector path, not text, so the record that reaches the
  interpreter is a linear `6.80` rather than a diameter, and the `4 x` multiplicity is a picture too. Those
  are the marks a reader has to get from the drawing, and they are the same job the raster sheets need.
  On the raster path the same callout was missing for a reason that had nothing to do with *reading* it:
  the drawn line is not merged into one cluster (the `4 x Ø` prefix and the words of the note are separate
  clusters, and the three glyphs of `6,80` read back as `6,80` when they are read at all), and the number
  was refused by the **gate**. `leader_near` measures the gap from the stroke's blank end to the box it is
  handed, and the note's leader ends 181 px from the `6,80` — 28 px from the note's own ink, 34.8 px from
  the `ALL` of its second line, which is the word it was accepted for. The plate's raster floor is 4/7 ->
  **5/7** now: the gate hands the leader the number's own printed block and `lines.leader_to_note` asks of
  it what a note's leader has to be (see `CHANGES.md` for the guards and the two sheets they were measured
  against). What is still open here is the mark, not the number: the `Ø` and the `4 x` are drawn, so the
  record arrives as a linear `6.8` rather than a diameter.
- **The scale audit now judges a reading in pixels as well as in percent — and that changed nothing, which
  is itself the measurement.** `scale.RELATIVE_TOLERANCE` is 4% of the value; a 1.5 mm dimension on a 1:2
  sheet is 6 px at 200 dpi, where one pixel of arrow or extension-line error is 17%, so `disagrees` now
  allows the larger of 4% and `scale.ABSOLUTE_PX` (2.5 px, the weight of the ink a line is drawn with). The
  rule it corrects is real, but no row on the six sheets moves: every reading the audit names today is off
  its line by far more than the ink — the plate's five agreeing dimensions are within 3.2 px of their lines
  and its one suspect (a `4` on a 38 px line) is 6.7 px out. What `plastic-enclosure-1` reports is not a
  tolerance artefact either: its 15 suspects of 20 auditable readings are numbers standing on lines that are
  not their own (`1.50` on a 113.5 px line where 1.5 mm is 5.9 px, `2` on 181.5 px where 2 mm is 7.8 px), the
  "number matched up with a line that was never its line" the audit's own docstring describes. Measured by
  `out/probe/probe_scale_floor2.py`; the audit's fit is unchanged (`consensus` is still ratio-only, or the
  small pairs would agree with any hypothesis and drag the majority).
- **A sheet is its own ground truth, so it can read its own mistakes again.** Every dimension line is
  drawn to the number printed on it, so the sheet fits its own scale (`scale.consensus`, a majority of the
  ratios between a value and the line it was read from) and a misread number is a pair whose ratio is off —
  a mistake the sheet names without being told the answer. That audit ran after reading and only
  *reported*; now the readings it names are asked again, at the angles the reader was not asked the first
  time, and a candidate that fits the sheet's own scale replaces one that does not (`perceive.
  _reread_against_the_sheet_scale`). Three numbers came back on three sheets, each one a phantom leaving:
  `plate-pocket-1` 5/7 -> **6/7** (the vertical `8,00`, read `3,00` at the angle its digits' own line gives
  — 63 px of line against 3 mm is 21 px/mm where the sheet fits 7.817 — and `8,00` 0.6° past it, at 7.875),
  `exercise-1` 5/13 -> **6/13** (`7€` giving way to `35`) and `plastic-enclosure-1` 7/11 -> **8/11** (`2)`
  giving way to `10`). Noise fell by one on each of the three sheets, no row lost a number, and the two
  sheets with no fitted scale (`flange-1`, `studycadcam-50`) and the four vector rows are unchanged. The
  re-read is skipped when a model is reading: one call per crop is minutes a sheet, and a model's answer is
  not a function of the angle it was asked at.
- **A number a leader carries cannot be checked against the scale at all.** `scale.measure_spans` reads the
  two ends of a span's own dimension line, and a leader's two ends say nothing about the value, so the
  audit never names a leader-mode span and the re-read above never touches one. The plate's `50,00` is
  exactly that case: on the raster path the stroke carrying it is taken as a leader (its other arrow is not
  drawn, or not found), its 617.6 px against a printed 50 is 12.35 px/mm where the sheet fits 7.817, and
  tesseract reads `90,00` at the digits' own line and `20,00` at the upright — no angle it is offered gives
  `50,00`, so this one is a reading job, not a geometry one. It is the last number missing from the plate's
  raster row.
- **The line's own arrowhead is not a printed number, and the reader has to be told so.** Measured: the
  reader answers a *digit* for the filled triangle at the end of a dimension line — seven of them on
  `plastic-enclosure-1` (`4`, `4`, `4`, `4`, `5`, `1`, `1`), two `7`s on `flange-1`, a `2` on `exercise-1` —
  and six of the plastic ones carried the value `4`, so they were counted as *covering* it and part of that
  sheet's raster row rested on ink that is not a number. The question that names them is place, not shape:
  the candidate's box centre lies **on the axis of the very line it is anchored to** (0.0-0.5 px, against
  4.5-192.6 px for every reading the sheet prints) and within its own length of that line's end — an
  arrowhead is drawn on its line and at an end of it, a printed number beside the line or in the gap the line
  is broken around. `perceive._is_the_lines_own_ink` refuses such a candidate before the reader is handed it,
  and `perceive._is_drawn_solid` keeps type that stands *on* its line (a printed digit is an outline,
  an arrowhead is filled: 0.30-0.53 against 0.50-0.67 of the blob's own box), which is what stopped the rule
  throwing away the one cluster on `plastic-enclosure-1` where `1.50` and `3.00` merge into a box lying on the
  line. Coverage is unchanged on every sheet; five false records are gone (plastic 7 -> **4** noise, `flange-1`
  5 -> **3**) and plastic's suspect column falls 12 -> **5**. What it does not catch: `exercise-1`'s own
  arrowhead, 1.15x its own length from the line's end, which stays a named suspect (`10a32b6`).
- **Raster reading is the weak half.** With the text layer taken away the front end finds 6 of the 13
  printed numbers on `exercise-1`, 4 of 13 on `flange-1` and 6 of 7 on `plate-pocket-1`, against 7 of 7 on
  that sheet read through its text layer. Three causes were measured on the plate sheet, and all three are
  fixed: a decimal separator too small to survive the glyph filter left the digits on either side of it
  30.6 px apart against a 25.6 px reach, so *every* dimension on the sheet came apart at its comma
  (`100,00` arriving as `10` and `00`); a crop was enlarged by its own longest side, which left the 33 x 95
  crop of a number printed up a vertical dimension at its original 18 px digits, and the reader returned
  `08` for `80,00`; and the quarter turn a crop is read at was *tried* rather than worked out, four
  rotations in turn with the first parseable answer winning, so a complete crop of `80,00` came back as
  `8000`. The turn now comes from the drawing: the digits' line gives the axis, the decimal separator gives
  the sense, because a separator sits below the baseline of the digits it belongs to. `eval/frontend.py
  --as-raster` is the harness for all of this — it reads a vector sheet's raster with the truth known
  exactly, so the CV reader can be improved without another hand-made example. It moved a row of numbers,
  not cleanly: `plate-pocket-1` 0/7 -> 4/7 and `plastic-enclosure-1` 2/11 -> 6/11 (both now with a fitted
  scale, 7.817 and 3.908 px/mm against 7.874 and 3.937 expected), `studycadcam-50` 1/3 -> 2/3, while
  `exercise-1` went 3/13 -> 2/13 and `studycadcam-60` 7/9 -> 6/9. Both costs are in the table.
- **A second preparation of a crop is not additive, and was measured and dropped.** Offering the reader
  the crop both as it stands and as the drawing's own ink (`lines.ink` on the crop, thickened by a pixel)
  was tried because it reads two more crops on `plastic-enclosure-1`. It is not additive: on
  `studycadcam-50` the coverage fell 2/3 -> 0/3 and on `flange-1` 3/13 -> 2/13, with five extra spans across
  the set. The mechanism is worth keeping: a crop tesseract refuses used to contribute nothing, and a second
  preparation turns the refusal into a *value* - a phantom span that then claims a dimension line and blocks
  the true number printed on that same row. A reader's refusal is doing work, so a fallback has to be
  measured on coverage, not on how many crops it reads.
- **What the raster reader still gets wrong is the read itself, not the geometry.** The clusters, the
  turning and the scale are right on `plastic-enclosure-1` now (6 of 11, fitted 3.908 px/mm), and what is
  missing it reads as `1`, `5`, `7`, `29.00`, `00` - single digits and fragments of numbers whose digits
  are 12 px tall. Reading a 12 px digit is a reader problem (the vision model in `eval/baseline.py`, or
  binarising and thinning the crop before tesseract), and `--as-raster` is what measures it.
- **A sheet is not two tones.** Splitting the grey histogram in the middle (Otsu) reads a drawing as ink
  and paper, and a drawing has three tones: text, thin lines, paper. On `plate-pocket-1` the text runs
  0-50 grey, the paper sits at 255 and every dimension line is printed at 161-235, so Otsu's split at 158
  kept the title block and the glyph stems and dropped exactly the lines the numbers hang on — which is
  why that sheet's leader at 75° was invisible to every earlier pass. Ink is judged now against the
  sheet's own paper and its own darkest tone (`lines.ink`), and a stroke's weight is the median of the
  samples that found ink rather than of all of them, because a faint line is missed at some sample points
  and missing it is not evidence of thinness.
- Synthetic sheets (build a part in CadQuery, render the three views, keep the part as truth) are the
  plan for volume; they belong in this folder as `synthetic.py` when Phase 2 lands.
- Nothing here scores *how much of the drawing was used*. A part built from 2 of 8 records and a part
  built from all 8 can both pass `vector`; coverage has to be its own check.
- The reading front end is not yet the path the build takes: `reason_drawing` reads one question per
  number through `roles.read_records`, which asks the vision model about every span the gate kept. Wiring
  the two together is what turns the measured coverage above into measured records.
- **The plate's overall length is not printed on the sheet, and it is derivable from the sheet's own
  symmetry.** Measured on the raster at the sheet's own 7.817 px/mm: the `100,00` dimension line is 783 px
  (100.17 mm) but its left end sits 83 px (10.62 mm) *inside* the plate's drawn left edge; the plate's drawn
  outline is 947 x 630 px (121.15 x 80.6 mm); and the four corner holes' centres are 788 x 474 px
  (100.81 x 60.64 mm) apart. So `100,00` and `60,00` are the **hole pattern**, not the part, and the plate is
  120 x 80 x 15 — which is the reference part's `[15, 80, 120]`. The derivation is the edge distance the
  vertical pair teaches: `(80 - 60) / 2 = 10 mm`, applied to the 100 pattern gives `100 + 2 x 10 = 120 mm`,
  and the drawn outline confirms it to within a stroke width. Nothing printed says 120, so the build has to
  derive it; a reader that takes the biggest printed number for the part's size builds a 100 mm plate.
  Working: `out/probe/probe_plate_length.py`, `probe_plate_edges.py`, `probe_plate_circles.py`; the class of
  work is written up in the skill's `references/deriving-undimensioned.md`.
- **The code model composes in the grammar of the prompt it is given, and that grammar is a tube.** Measured:
  on the plate — where all seven numbers are printed and unambiguous — the coder wrote
  `ring_extrude(outer_d=100, inner_d=80, length=50)` and glued a `60x60x15` plate to its end, and the run
  before it wrote a different tube from the same numbers. No amount of better reading can repair this (rule
  4): the numbers have to reach the coder as named features, and inventing the composition is exactly what it
  is doing instead. This is the first thing to fix on the building half.

## Deterministic plate plan (2026-09-26)

A separate path now binds vector contours and dimension anchors to an explicit CAD plan:

```sh
PYTHONPATH=src .venv/bin/python eval/plate_plan.py
```

This does not overwrite `out/eval` or the model-path tables above. It writes `out/plate-plan`.
The planner sees only the drawing. The harness opens the reference STEP after production.

| case | dimensions | volume | cylinders | symmetric difference |
|---|---|---|---|---|
| plate-pocket-1 | 120 × 80 × 15 mm | 124.825 cm³ | radii 3.4, 10, 25 mm | 0 mm³ |

The exported STEP is reimported and checked for validity, all nine cylindrical faces' positions and
axial extents, bounding box and analytic volume. Reference comparison also checks both Boolean
differences, in this fixture's shared coordinate frame. The measured build took 5.221 s on Apple M1
16 GB; this is one run, not a general performance guarantee.

Supported recognition is deliberately narrow: one rounded rectangular plate with four equal corner
holes, one central circular pocket and an aligned section, expressed as top-level polyline PDF paths.
The width and corner radius are derived from equal margins after checking the drawn outline; these
remain visible assumptions. Outputs are drafts (`audit.accepted=False`) even when all plan checks pass.
The app tries this path first; unsupported drawings use the existing model path. CLI `plan/build-plan`
select it explicitly. Raster recognition, other part families and arbitrary PDF path grouping remain open.
See `../HANDOFF.md` for reproduction and next work.
