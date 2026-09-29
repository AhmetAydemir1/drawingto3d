# eval

## Current product checkpoint — 2026-09-28

User-guided draft generation is now implemented. Read [guided-flow.md](reports/guided-flow.md) and [its evidence](reports/guided-flow-evidence.json). Full suite 488 passed; final focused suite 16 passed. One real PDF produced a valid draft STEP; exact dimension constraints and complete UI acceptance remain open. Older interpretation scores below are not independent geometric accuracy. PLAN Section 23/23.1 defines current next work.

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
different operation combinations — lives in `plans/`; `build-general` in the CLI builds them. The
reading half now has four slices: `observe.py` plus `drawingto3d observe` write one family-independent
record per vector sheet (subpaths, fitted primitives, printed phrases with their source characters,
frame and text placement), and PNG/JPG sheets go through `raster.py` into the *same* record (Hough
lines and ink-verified circles, tesseract phrases with confidence; measured: flange 388 lines +
2 circles + 29 phrases, `my_part.jpg` 343 lines + 6 circles + 49 phrases); `bind.py` plus `drawingto3d bind` attaches every printed number to the
geometry its arrows touch — rows, stubs, crossed strokes, chains of coincident strokes and, for
two-anchor dimensions, candidates aligned along the measuring axis, all with pixel distances and the
row length against the sheet's calibration; and `meaning.py` plus `drawingto3d meaning` reads each
number into the claim the drawing supports — a distance between two candidates projected onto the
row's axis, a diameter/radius carrying every matching circle, a count checked against how many
circles match — or marks it unresolved; and `proposal.py` plus `drawingto3d propose` proposes the `GeneralPlan`
those readings support — the part outline out of the sheet's closed loops with the sheet frame
skipped, every parameter printed with its span id or derived by expression, every printed number
checked against the same sheet's measured geometry — or refuses with the reasons (the plastic
sheet: no diameter claims at all). `proposal.py` also exposes the reading chain's own measurements
(`read_sheet`) and `planner.py` turns them into the block the model planner is asked with
(`chain_evidence`), so `drawingto3d model-plan` can ask the local model the same question `propose`
answers with rules: it writes the evidence, the model's raw answer and, when the answer meets the
contract, the plan; otherwise it exits 2 with the reason and no plan. What is still missing: raster
anchors and scale (a raster sheet
binds and then resolves `no-scale` on every claim — `propose` refuses with *pafta ölçeği okunamadı*;
`model-plan` never calls the model for such a sheet)
and the wider
archetypes (multi-view sheets, chain dimensions, asymmetric layouts); the refusal lists name them.

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
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --no-model --conditions reading,chain,verified_plan --label <label>
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen3-vl:8b-instruct --conditions relations --cases plate-pocket-1 --label <label>
PYTHONPATH=src .venv/bin/python eval/model_baseline.py --model qwen2.5vl:3b --conditions chain,chain_model --cases plate-pocket-1,plastic-enclosure-1 --label <label>
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --write    # section 7 tables, built from the run records
PYTHONPATH=src .venv/bin/python eval/guided_effort.py --drawing "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" --accept-and-build --reference "examples/pdf with steps/5/plate with a pocket.STEP" --label plate-flow
```

`eval/guided_effort.py` measures what the guided flow asks the user for, against what the drawing already
answered. `--session` reads a saved session's own decisions back to the reading (which claims stand behind
each value, and which printed number the flow never offered); `--drawing` opens a sheet through the product
path and records the questions and candidate menus a user meets at open; `--accept-and-build` takes the
reading's proposals in one step, builds, and records the interaction count, the decisions and the questions
that are left. It writes `out/guided-effort/<label>/run.json`. The independent half — is the STEP the flow
produced equal to the reference part? — is `eval/metrics.py`, which needs cadquery and therefore runs in the
CAD environment: `.venv-cad/bin/python eval/metrics.py <produced.step> <reference.step>`.

`eval/model_baseline.py` measures section 18B's conditions apart — `reading`, `chain`, `chain_model`,
`verified_plan` and `relations` — because an end-to-end score cannot say which layer failed. `chain_model`
is the product path: the sheet is read by the chain (`read_sheet` → `chain_evidence`, millimetres, every
printed number with its span id and every claim with its anchor points) and the local model is asked the
same question the rules-based `chain` answers from the same measurements, so the two planners are compared
on the reading alone. It writes one
machine-readable record per run under `out/model-baseline/<label>/` with the code HEAD and dirty-file list,
the manifest summary, the model digest and quantisation, the prompt/schema/evidence versions, the sampling
settings, cold and warm start, per-stage seconds, the output status, swap and free-page samples and the ollama
RSS peak. Reference STEPs, the correct plan and the file name never enter a model prompt; a `relations` run
reads its context from a hand-verified table in `eval/relations/` and is a diagnosis, not an automatic
PDF → STEP success. `eval/baseline_report.py` builds the tables of `eval/reports/model-baseline.md` from those
records and from `out/frontend/`; `--check` fails when a run has changed a number the report still quotes.
`eval/reports/model-baseline.md` carries the findings and the next-step decision.

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
| exercise-12 | vektör | 19/20 | 3 | 1.550 | 14 |

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


## Model reply grammar audit (2026-09-27)

That work: `../PLAN.md` §20 and `reports/schema-audit.md`. Required tags and
parameter/repeat alternatives were missing from the model-facing grammar. Reply v3 adds
them while retaining `GeneralPlan v1`. Same-prompt leaf probes improved from 0/3 to 3/3;
real plate model plans still fail (names, with further semantic faults visible in raw output).
No model-generated STEP success is claimed. Reproduce the small diagnostic with
`schema_probe.py`; both full evidence bundles are in `reports/schema-v3-*-evidence.json`.


## CAD names in the model interface (2026-09-27)

Current next work: `../PLAN.md` §20 and `reports/naming-interface.md`. The reply grammar now
carries `propertyNames` and `pattern` for CAD identifiers (prompt `general-plan-v3`, schema
`GeneralPlan reply v4`) while `GeneralPlan v1` and the CAD validator are unchanged. A recorded
provider probe (`reports/name-probe-evidence.json`) shows this provider enforces a `pattern` on a
*string* field but ignores `propertyNames` on an object; a closed key vocabulary holds the key and
degrades the value (`100` → `"testing"`), and `patternProperties` returns an empty body. So an open
set of keys cannot be constrained here, and the lossless identifier rewrite (`NAME_ADAPTER`,
default off) is the recorded fallback. Four real plate runs, labels `names-3b-02`…`names-3b-05`
(`reports/names-v4-evidence.json`): the name error is gone, the first error is now the unparsable
expression `'/hole_spacing_x'`, and larger answers never close — `relations` ends at
`done_reason=length`, 4096 tokens, 182.3 s, so the earlier 180 s "no answer" is that loop being cut
by the client. The three-call path lands the `parameters` step in 14.8 s and loses the `profile`
step to the same loop; that step is the single next change. No model-generated STEP is claimed.

## The profile step asks one profile per call (2026-09-27)

Current next work: `../PLAN.md` §20 and `reports/profile-step.md`. The profile step now asks for one
call per closed profile the readings measured (`profile_targets`: one closed outer loop plus each
closed circle), and each sub-answer is judged before the next call is spent — structure,
expressions, closure, known references, measurement citations, "exactly one sketch", name
collisions — with a profile call capped at `PROFILE_PREDICT_CAP = 1024` tokens. Prompt version
`general-plan-v3-split-profile`; the reply schema, the naming rule, `GeneralPlan v1` and the CAD
validator are unchanged. A run label of `profile-3b-01` measured it once, same plate, same
`qwen2.5vl:3b`, same 16384/4096 settings (`reports/profile-step-evidence.json`).

The loop is gone: the same step that used to end at `done_reason=length` with 4096 tokens and 7 743
bytes of repetition (178.5 s) now stops at 129 tokens in 17.9 s. Both conditions still fail, so no
CAD build, no drawing check and no second part group were measured. The first remaining errors are
in two different places: `relations` stops at **parameters**, citing drawn-circle ids (`h1`, `h2`)
where printed span ids (`d1`…`d7`) belong — that prompt is byte-identical to the one `names-3b-05`
answered with the same answer, so what changed is the step judge, not the model or the interface;
`chain_model` stops at **profile 1/6 (outline)**, with two edges that do not close and an arc radius
`x(6.84/2)` whose numbers come from a hole rather than the 120.87 × 80.56 mm outline. Its
`parameters` step passed the interface checks while being unusable as a part: `hole_spacing_y`
derived as `(100 - 80) / 2 = 10` where the sheet prints 60,00, a third diameter derived from the
section's 15 and 8, a pocket depth assumed from the sheet's px/mm scale, and no thickness at all.
That is the separation this section insists on: valid JSON is not a plan, and an accepted step is
not a measured part.

## Loops, the second archetype's gate, raster scale and the evidence block's id spaces (2026-09-27)

Round report: `reports/general-input-slices.md`; next work: `../PLAN.md` §20. Two model-free probes
came out of it. `eval/loop_candidates.py [case-id …]` prints, per sheet, every non-frame loop with its
size, primitive count, whether it is a rounded rectangle, and how many confirmed claims are anchored to
it (plus the distances that touch neither the loop nor circle centres — the candidates a general
flat-part archetype would read a thickness from). `eval/raster_scale.py [case-id …]` fits a raster
sheet's own px/mm from the ratios between its numbers and the strokes they sit on, through
`scale.consensus`, rejecting a hypothesis whose largest printed value would be longer than the page's
diagonal and any fit supported by fewer than three distinct numbers; it also tries a row/gap pairing.

**Loop chaining changed and moved the sheets it was aimed at.** `proposal._loops` now takes the segment
that closes the chain first, otherwise the continuation that turns least, and a chain that dead-ends
claims nothing (its segments return to the pool). `exercise-1-vector` (`Drawing.pdf`) went from 3 loops
to 7 and its chosen loop is now the part's outline — 8 primitives, 53.62 × 82.29 mm, carrying `pdf-13`
(R20) — where it used to be a 20.54 × 35.95 mm detail view; `propose`'s refusal names that outline now.
The plate is unchanged (same loop and measurements, `propose` still `proposed`, `plate_plan.py`
passes). The second archetype the plan asked for was **not written**: its honest gate is a contour whose
own extents are confirmed by printed dimensions with exactly one section distance left over, and no
measured vector sheet passes it (plate 1/2 extents bound and 2 candidates; `plastic-enclosure-1` 0/2
and 4; `Drawing.pdf` 0/2 and 10), so the code would sit unexercised — the gate and its reason are
recorded instead, with binding coverage as its prerequisite.

**Raster scale is downstream of reading coverage, not a lock of its own.** The reading path already
calibrates from the spans `bind` anchors: `exercise-1` 5.73, `exercise-13` 2.88, `studycadcam-60` 3.28
px/mm, while on four sheets `bind` anchors nothing and the refusal stays `pafta ölçeği okunamadı`.
The new probe independently fits **3.3158 px/mm** on `studycadcam-60` (four numbers agreeing to 0.17 %,
within 1.1 % of the path's 3.28) and the same scale puts that sheet's two drawn circles at 51.06 and
20.57 mm against printed `20` and a round Ø50. Where a scale exists the next gate is contour closure:
343 strokes on `exercise-1` produce no closed part outline (`çizgiler/yaylar döngü kurmuyor`), and
`studycadcam-60` has no loop outside its page frame. The row/gap pairing model adds nothing at this
layer — the raster observer already merges collinear strokes (219 of 221 rows are single strokes).
The previous round's table, which recorded `pafta ölçeği okunamadı` for all seven rasters, could not be
reproduced this round; the raster reading path did not change between the two (`bind.py` 01:58,
`meaning.py` 01:58, `raster.py` 02:46, all before that sweep), so today's run is the measurement.

**The evidence block now names its two id spaces, and the run `ids-3b-01` shows the target failure
closing.** `planner._readings_line` renders *Printed numbers* (`span_ids` may point at these ids and
only these), *Measured regions* (geometry ids — not citations), the claims between them, the sheet and
the notes; the profile call's region is a keyed block `Target profile (this call)`; `PROMPT_VERSION`
moved to `general-plan-v4` and `PROMPT_VERSION_SPLIT` to `general-plan-v4-split-profile-ids`. One run
(`qwen2.5vl:3b`, `--split`, same plate/evidence, 16384 ctx – 4096 predict, `relations,chain_model`,
53.23 s, `complete`, both conditions `failed/planning`): `relations` cites real printed ids (`d1`, `d3`)
where it used to cite drawn circles (`h1`, `h2`), and its first error moved one step deeper — an
expression naming a span id (`(d2 - d4) / 2`), with an invented `sqrt` and a printed parameter whose
value (`70.0`) is what neither cited span (100.00, 60.00) prints sitting behind that first error
(offline labelled replay). `chain_model`'s first error moved to the naming rule (`pdf-0`); the same
answer judged with the name adapter on gives **0 errors**, so on that condition the naming rule alone
blocks the parameters step. No plan passed: no CAD build, no drawing check, no second part group, no
STEP, and no training or capacity conclusion is drawn from this.

**The parameters step's two refusals were restated as rules, and the measurement says the words did
not close the class (2026-09-27).** Round report: `reports/parameter-rules.md`. The judge did not
change; `_RULE_EXPRESSIONS_USE_PARAMETERS` (a derived expression is arithmetic over the parameter names
the answer declares — a span id is a citation, not a name) and `_RULE_PRINTED_CARRIES_ITS_VALUE` (a
`printed` parameter carries the number its cited span prints, or the count beside it) were added to the
shared rule set and are quoted in both interfaces, because both are asked for parameters. Versions:
`general-plan-v5-parameter-rules` and `general-plan-v5-split-parameter-rules`. One run with a new label
(`params-3b-01`; same plate, model, 16384/4096, `--split`, conditions `relations,chain_model`, and the
`chain_model` evidence block byte-identical to `ids-3b-01`'s — so the question is the only variable):
53.69 s, `complete`, both conditions `failed/planning`. The first error did not move class: `relations`
still put a span id inside an expression (`d7`, was `d2`) and `chain_model` still named a parameter
`pdf-0` — the naming rule that was already in the v4 prompt and was ignored. Read that as measured, not
as a wording failure to retry: this provider's grammar constrains a *string* with `pattern` but ignores
`propertyNames` on an object, and the same `chain_model` answer cleared its parameters step with the
lossless name adapter on. What the answer lacks is a legal identifier to copy. Still no plan: no CAD
build, no drawing check, no second part group, no STEP.

**Every printed number now carries a legal name beside its id, and the naming failure moved one step
deeper (2026-09-27).** Round report: `reports/suggested-names.md`. `params-3b-01` measured that writing
the two rules into the question was not enough — the readings block offered the answer only span ids, so
it kept using them as names. `planner.suggested_names` (recorded as `settings.suggested_names =
reading-derived-names-v1`) derives one name per printed record from the reading's own `kind`/`form`,
its anchor kinds (`circle-centre` → `circle`, `arc-rim` → `arc`, ends → `edge`) and the anchors' own
axis; two records measured the same way get indices (`diameter_1`, `diameter_2`). `_readings_line`
renders that block right after *Printed numbers*, so both interfaces carry it; versions move to
`general-plan-v6-suggested-names` / `general-plan-v6-split-suggested-names`. Not a part template: the
only inputs are reading fields, and a test renames every span and geometry id and demands the same
names. One run, new label (`suggest-3b-01`; same plate/model/settings/conditions, `chain_model` evidence
byte-identical to `params-3b-01`'s — the question is the only variable): 46.12 s, `complete`, both
conditions `failed/planning`, no STEP. The class moved: `chain_model` no longer names a parameter
`pdf-0` — it used five of the seven suggested names — and both conditions now fail on the same narrower
thing, an expression naming something the answer did not declare (`diameter_2`, `d1`); `relations`
adopted the menu's style (`distance_1 … distance_7`) but not its names. Still no plan: no CAD build, no
drawing check, no second part group, no STEP.


## Split-step validation audit (2026-09-27)

Current next work: `../PLAN.md` §21 and `reports/step-validation-audit.md`. Parameter
citations and profile expressions/closure are now checked before the next model call.
The real-drawing baseline now honors `--split`; the earlier `names-3b-05` was a mixed
interface run. New `step-validation-3b-01` has no valid plan or STEP. Next measure evidence
to parameter selection, including drawing meaning, rather than only JSON validity.

## Parametre kataloğu ölçümü (2026-09-27)

`PYTHONPATH=src .venv/bin/python eval/catalog_parameters.py --label YENI_ETIKET` yalnız
basılı ölçü seçimi/anlam/türetme adımını iki farklı görülmüş parça grubunda ölçer. Yeni etiket
zorunludur; `out/catalog-parameters/` altında istek öncesi ve cevap sonrası kalıcı kayıt tutulur.
`catalog-3b-01` iki cevabı da reddetti; katalog değerleri 22/22 korundu. Anlam/CAD doğruluğu
ayrı ve açık kalır. Rapor: `reports/catalog-parameters.md`; taşınabilir ham kanıt:
`reports/catalog-parameter-evidence.json`. Bu komut STEP üretmez.

### Ölçüleri model olmadan inceleme

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d catalog "cizim.pdf" out/olcu-inceleme
```

Yeni bir çıktı klasörü seçin. Komut `catalog.json`, `evidence.json` ve okunabilir `review.md`
üretir. Ölçek ya da kontur eksikse ölçüler korunur, eksik bilgi ayrıca gösterilir. Bu komut
STEP üretmez; `needs_review`/`needs_input` durumları anlam ve geometri onayı değildir.

**Tek ölçü yorum arayüzü ölçüldü (2026-09-27).** `eval/meaning_interpretation.py` tek bir basılı ölçüyü
(`qwen2.5vl:3b`, 16384/4096, sıcaklık 0) çizimin **kendi** kaynak ve geometri kimliklerine bağlatır;
sayısal türetme istemez, çözülemeyen bağı `unresolved` + soru olarak bırakır. İstek her çağrıdan önce,
cevap hemen sonra `out/meaning-interpretation/<etiket>/` altına yazılır; `--dry-run` model çağırmadan
istekleri üretir, `--check <paket>` kayıtlı ham cevapları yeniden yargılar.

- Arayüz `src/drawingto3d/interpret.py`; şemada sayısal alan yok ve geometri kimlikleri yalnız sunulan
  gerçek kimliklerin `enum`'u. Referans etiket (`eval/relations/<parça>.json`) **yalnız** değerlendirmede
  kullanılır: eşleşme basılı değer+birim ile, etiket kimliği okuma kimliğine en yakın konumla bağlanır;
  eşlenmeyen uçta alan "ölçülemez" sayılır.
- `meaning-3b-01` sonucu: sözleşme 22/22 cevapta tuttu, ama plakada 7/8 cevap sözleşmede düştü (5'i
  gerekçede sayı yazdı), etiketin denetlediği 15 alandan yalnız 1'i puanlandı, tam doğru 0; plastikte
  13/14 sözleşmeden geçti ama eksen 14/14 "horizontal" ve 7 ölçü aynı çifti gösterdi, bağımsız etiket
  olmadığı için doğruluk ölçülmedi; `unresolved` 0/22. Ayrıntı `eval/reports/measurement-interpretation.md`.
- Bu sayılar bir STEP, profil veya genel çizim başarısı değildir; sıradaki tek değişken gerekçedeki
  sayı yasağının kapsamıdır (bağ yüzünden atılmasın), sonra aday kümesini daraltmak.

**Sayı yasağının kapsamı ölçüldü (2026-09-27, `meaning-3b-02`).** Aynı istem ve aynı ham cevaplarla
(22/22 birebir), yalnız yargı sözleşmesi `interpretation-contract-v1` → `v2`: kimlik dışı sayı artık
cevabı düşürmüyor, `warnings` alanına yazılıyor. Plaka 1 doğru/7 geçersiz → **3 doğru/2 kısmi/3
geçersiz**; puanlanan alan 1 → **9** (15 denetlenebilirden); tür 5/5, eksen 1/2, bağ 1/2. Kalan
geçersiz sınıf çap/yarıçap şekli. Yeni bulgu: eksen kelimesi ile seçilen çift tutarsız. Plastik
cevapları aynı kaldı (etiket yok, eksen 14/14 "horizontal", 7 ölçü aynı çift, `unresolved` 0/22).
`--check` eski sözleşmeyle üretilmiş pakette durum karşılaştırmasını atlar, ham cevabı doğrular.

**Eksen artık sorulmuyor (2026-09-27, `meaning-3b-03`).** `interpretation-contract-v3`: şemada `axis` yok,
eksen seçilen iki uçtan türetiliyor; istem de bu yüzden değişti (istem ve ham cevaplar v2'ye göre 22/22
farklı — v1→v2 saf yargıç değişikliğiydi, bu tur sorunun kendisini değiştirdi). Plaka 3 doğru/2 kısmi/3
geçersiz → **4/1/3**, ama alan doğruluğu değişmedi (tür 5/5, eksen 1/2, bağ 1/2): kayıp çift seçiminde.
Plastikte en sık çift 7× → 5×, okuma bağıyla uyuşan 3/14, `unresolved` 0/22. Bu turda denetimin kendi
hatası da bulundu: bir çağrıdan iki ölçü (boyut + adet) üreten kayıtta eşleşme artık (kaynak kimliği, ad)
çiftiyle yapılıyor.

**Aday kümesi okumanın kendi ölçtüğü çiftler (2026-09-27, `meaning-3b-04`).** `interpretation-contract-v4`:
`between` yalnız okumanın ölçtüğü çiftlerden seçilebilir (kendi ankraj çifti + claim `notes` içindeki
alternatifler; iki ucu da ölçülmüş konum taşıyanlar). Plaka 4 doğru/1 kısmi/3 geçersiz → **5/0/3**;
tür 5/5, eksen **2/2**, bağ **2/2**. Dört adaylı iki ölçüde model okumanın kendi çiftini seçti. Kalan üç
geçersiz cevap çap şeklinde; plastikte okuma bağı 4 sayıda, 10 ölçüde hiç yok; `unresolved` 0/22.
Daralmanın erişimi ölçüldü: notlardaki alternatiflerin çoğu konum taşımadığı için menüye giremiyor.

**Şekli reddedilen cevap artık "ölçülemedi" değil (2026-09-27).** `compare`, sözleşme bir cevabı
reddettiğinde bağı yine puanlar: işaret edilen küme (`between` ∪ `matched`) etiketle karşılaştırılır,
cevabın sınıfı "geçersiz" kalır (`binding_beyond_contract`). Model sorusu değişmediği için yeni koşu
yapılmadı; dört koşunun kayıtlı cevapları `--rescore <koşu klasörü>` ile yeniden puanlandı (koşu kaydı
değişmez, `rescore.json` yanına yazılır). Sonuç: plakada ölçülemeyen alan kalmadı — kalan üç cevap
ölçülü şekilde yanlış (`pdf-3` dört deliğin yarısı, `pdf-4` cebe fazladan delik); tek kural altında dört
koşu 1 → 3 → 4 → 5 doğru, eksen 0/2 → 1/2 → 2/2, bağ 1/2 → 2/2.

**İnceleme turu: okumanın önerisi + deterministik kusur (2026-09-27, `meaning-3b-05`).** `eval/meaning_interpretation.py --review`
istemde okumanın kendi bağını inceleme isteği olarak gösterir; ölçülerin yarısına yalnız kaynak kimliğinden
türeyen kusur enjekte edilir (`drawingto3d.interpret.reading_proposal` / `review_injects_a_defect` /
`corrupt_proposal`, sürüm `reading-review-v1`). Doğruluk yapı gereği bilinir; etiket kullanılmaz, kopyalamak
yanlış bağ sayılır. Özet alanları: `review` (`corrupted`, `defect_caught`, `clean`, `false_alarms`, `copied`,
`binding_wrong_beyond_copy`, `no_reading_binding`, `unusable_answer`). Plaka 7 doğru/1 kısmi; 6/6 kusur
düzeltildi, 0 yanlış alarm. Ayrıca `answers_agreed_with_reading` anahtar hatası düzeltildi (beş turdur 0
görünüyordu).

**Okuma kapsamı: satır ölçeğe uymuyorsa uçlar yeniden seçilir (2026-09-27, `bind.py`).** Satır paftanın
ölçeğinden %25'ten fazla saparsa uçlar, çapanın zaten gördüğü noktalar arasından ölçeğin gerektirdiği
uzunluğa en yakın çiftle yeniden seçilir (kabul %5; satır uyuyorsa dokunulmaz, yeni geometri yok,
tolerans gevşetilmez). Plastikte bağlı sayı 4/14 → 8/14, 10/14 ölçü değişmedi, plaka istek özetleri
8/8 aynı. Ayrıntı ve öncesi/sonrası yöntemi: `eval/reports/reading-coverage.md`.

**Okuma kapsamı, ikinci dilim: çapanın kestiği çizgilerin uzak uçları (yalnız yedek geçiş).** Ölçüyü veren
geometri, uzatma çizgilerinin uzak uçlarıydı ve yorum katmanı onları hiç sunmuyordu; `CANDIDATE_LIMIT`
büyütmek hiçbir şey değiştirmiyor (ölçüldü). Kestiği çizgilerin uçları ilk geçişte sunulunca plaka bozuldu
(8/8 istek özeti 0/8'e düştü) ve plastikte duran üç bağ yeniden yazıldı; bu yüzden yalnız **ilk geçiş hiçbir
şey bulamadığında** çalışan bir yedek geçiş olarak eklendi. Plastikte bağlı sayı 8/14 → **11/14**, tam olarak
çözülemeyen üçü değişti, 11/14 dokunulmadı; plaka 7/7 ve 8/8 aynı. `row`/`stub` (ölçü çizgisinin kendi
mürekkebi) asla sunulmaz. Ayrıntı: `eval/reports/reading-coverage.md`.

**Okuma kapsamı, üçüncü dilim: kendi segmentiyle ölçülen basamak (2026-09-27, `bind.py`).** Satır ölçekten
%25'ten fazla sapıyorsa ve çapalar arası çift yoksa, **tek çapaya bağlı** bir çizgi ölçü kabul edilir: eksen
boyunca çizilmiş (izdüşüm ≥ uzunluğun %99'u) ve basılı uzunlukta (%5). `row` çizgileri hariç; kural yalnız
lineer + `dimension` çağrılarında. Plastik 11/14 → **12/14** (yalnız `pdf-10`; satır 69,0 → 19,21 px),
13/14 dokunulmadı, plaka 7/7 ve 8/8 istek özeti aynı. Yakın ıska (`pdf-11`, %5,9) ıska kalır ve not yazılmaz.
Ayrıntı: `eval/reports/reading-coverage.md`.

**Okuma kapsamı, dördüncü dilim: ölçü ekseni üzerindeki segment (2026-09-27, `bind.py`).** Satır testi ve iki
yeniden seçim başarısızsa, okumanın kendi ilkellerinden bir çizgi, **iki ucu da ölçü ekseni çizgisi üzerinde**
(mevcut 4 px ölçü sınırı içinde) ve uzunluğu basılı değerin %5'i içinde ise ölçü kabul edilir; çapaya en yakın
olan kazanır. Plastik **14/14** (iki ölçü değişti, 12/14 dokunulmadı), plakanın `bindings.json` kaydı kural
açık/kapalıyken **bayt bayt aynı**, kural plakada hiç çalışmıyor. Ayrı ölçüm: plastikte 13 mesafe bağının
8'inde iki nokta arasındaki dik açıklık 20 px'ten büyük — kapsam var, bağ her zaman ölçülen yüzü adlandırmıyor.
Ayrıntı: `eval/reports/reading-coverage.md`.

**Bağ keskinliği (2026-09-27, `meaning.py`):** satır ölçeğe göre yeniden seçildiyse (`SpanBinding.row_repaired`,
`Bindings.version` 3) geçerli çiftler **önce eksene dik açıklığa** göre sıralanır; eksen bileşeni zaten basılı
değeri tuttuğu için küçük dik açıklık, uzayda basılı uzunluk kadar ayrılmış **yerel** bir çift demektir. Plastikte
dik açıklık toplamı 2450,2 → **1262,6 px**, medyan 118,6 → **0,1 px**, 20 px üstü 8/13 → **5/13**; plakada
onarılmış satır yok, değişiklik orada etkisiz (8/8 istek özeti aynı). Kalan 5: çizildiği gibi okunan üç satır
(dokunulmadı) + seçeneği olmayan iki onarılmış satır. Kimlik düzeyinde referans etiket yok: "keskin" = "noktalar
ölçünün eksenine daha yakın", "doğru geometri" kanıtı değil. Ayrıntı: `eval/reports/reading-coverage.md`.

**Arayüz turu yeni okumayla (`meaning-3b-06`, 2026-09-27):** aynı model, aynı paftalar; okuma artık plastikte
14/14 bağlı ve bağlar ölçünün yanında. Plaka 7 doğru/1 kısmi/0 geçersiz + inceleme 6/6 (değişmedi); plastikte cevap
okumanın bağını 13/14 tutuyor (05: 3/14 — bu bir **kopyalama** payıdır) ve inceleme turu 10/10 kusuru yakalıyor,
yanlış alarm 0 (05: 4/4 + 9 yanlış alarm). 05→06 tek değişkenli değil: arada yedinci dilimin yargı düzeltmesi ve
dört okuma değişikliği var. Ham koşu `out/meaning-interpretation/meaning-3b-06/`, paket
`eval/reports/meaning-interpretation-evidence-06.json` (`--check`: 0 sorun).

**Kör tur ve alan düzeltmesi (2026-09-27, `interpret.py`):** `--review` olmadan koşan turda model okumanın
önerisini hiç görmez (05/06'da her iki çağrı da görüyordu). Kör plaka: 5 doğru/0 kısmi/**3 geçersiz**, sözleşme
dışı bağ 3. Üç kayıp da tek sınıftı ve üç kör koşuda birebir aynıydı: tek geometri boyutlandıran çağrı (Ø/ R)
`between`'e çift olarak yazılıyordu. İstek + şema artık bu ölçünün formuna göre listeyi söylüyor
(`distance`/`angle` → `between`, `diameter`/`radius`/`count` → `matched`; karşı alan `maxItems: 0`) —
`single-measurement-interpretation-v2-form-field`. Yeni kör tur `meaning-3b-08-blind-v2`: plaka **7/1/0**,
sözleşme dışı bağ **0**, plastik 13/14; `pdf-3`'ün adedi tek kayıp olarak kaldı. Paketler
`eval/reports/meaning-interpretation-evidence-0{7,8}.json` (`--check`: 0 sorun).

**Adet ölçüsü (2026-09-27, `interpret.py`):** "4 × Ø6,80" bir kez basılıp iki kez soruluyor (çap + adet) ve metin
ile aday menüsü aynı; hangi ölçünün sorulduğunu yalnız katalog bilir. İstek artık ölçünün miktarını taşıyor ve
`count` ise bunu söylüyor (`single-measurement-interpretation-v3-count-quantity`). Kör turlar: plaka `-07` v1
**5/0/3 geçersiz** → `-08` v2 **7/1/0** → `-09` v3 **8/0/0**; plastik 13/14 (tek ayrışma `pdf-2 radius`,
üç kör koşuda geçersiz, etiketsiz). Paket `eval/reports/meaning-interpretation-evidence-09.json`.

**Üçüncü pafta etiketi (`eval/relations/exercise-1-vector.json`, 2026-09-28):** `2/Drawing.pdf` + `Part-2.STEP`
için elle doğrulanmış ilişki etiketi (STEP: kutu 134×80×50, beş çap r=10/12,5/15/20/25, z=±13/±3/±10/±20/±5
kalınlıkları). Ölçülen engel: paftanın metin katmanında **Ø glifi yok**, okuma beş çap çağrısını `linear` sayıp
iki çizgi ucu arasında mesafe gibi bağlıyor (`pdf-19`/`20`/`22` bağlı, `pdf-21` çözülemiyor); etiketle kuru koşuda
11/17 satır eşleşiyor (çift değerliler hariç) ve üç çap satırında okuma `distance`, etiket `diameter` diyor.
