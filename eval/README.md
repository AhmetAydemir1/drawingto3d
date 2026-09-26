# eval

What "better results" means for this project, in numbers. Two questions per sheet:

1. **Reading** — did the reader find every number printed on the sheet, and nothing else?
2. **Building** — is the STEP it built a functionally equal part to the reference STEP?

Run:

```bash
PYTHONPATH=src .venv/bin/python eval/frontend.py          # reading front end, no model, seconds per sheet
PYTHONPATH=src .venv/bin/python eval/baseline.py          # reading turn over every eval sheet -> out/baseline/<case id>.json
.venv-cad/bin/python eval/report.py                       # table + out/eval/report.json
```

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
| plate-pocket-1 | vektör | 6/7 | 0 | 7.817 | 0 |
| studycadcam-60 | raster | 6/9 | 7 | 3.278 | 7 |
| studycadcam-50 | raster | 2/3 | 5 | - | 0 |
| exercise-1 | raster | 2/13 | 8 | 5.700 | 9 |
| flange-1 | raster | 3/13 | 4 | - | 0 |

The same sheets with the text layer taken away (`--as-raster`), which is the reader a scan gets:

| vaka | kapsam | at the start of this work |
|---|---|---|
| plate-pocket-1 | 4/7 | 0/7 |
| plastic-enclosure-1 | 6/11 | 2/11 |
| studycadcam-50 | 2/3 | 1/3 |
| studycadcam-60 | 6/9 | - |
| exercise-1 | 2/13 | - |
| flange-1 | 3/13 | - |

`exercise-1` lost the value it had gained: it reads 2/13 with the text layer where it read 3/13, the cost of
a crop being turned by the drawing's own geometry instead of by trial. Removing the text layer costs
`plate-pocket-1` two numbers (6/7 -> 4/7) and `plastic-enclosure-1` five (11/11 -> 6/11), which is the
distance between the text layer and the reader a scan has to use.

The vector numbers are the text layer read through the geometry gate; the raster ones are the same gate
with tesseract behind it, which is the floor, not the finished reader — `eval/baseline.py` is where the
vision model enters. The raster column moves by a number or two with any change to how glyphs are
grouped, so it is the row-by-row comparison that says whether a change helped, not one sheet.

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
   beside the blank end of the shaft, the shaft at any angle). Title block, part numbers, copyright years
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

- **A dimension drawn at an angle is still unread.** The strokes at an angle are found now
  (`lines.diagonal_strokes`, banded by the sheet's own thin weight and wired into the gate), and that plus
  the contrast rule below is what recovered `50,00` on `plate-pocket-1`: its line runs at 15° under the
  number, faint, and carries an arrowhead at one end, so the leader path takes it (5/7 -> 6/7). What stays
  unread is the *dimension* path: `dimension_for` reads a row of collinear strokes along an axis, so a
  dimension line drawn at an angle is invisible however well its stroke is found. The same shape on the
  flange is the `6 x Ø6.40` and `Ø11.00` callouts. Generalising the row to a direction (project onto the
  stroke's own axis and across it) is what closes this, and the row code is already written in projections.
- **Callouts drawn as curves are not text at all.** On `plate-pocket-1` the region of the `6,80 THRU ALL`
  callout contains *no* text-layer characters, and the same sheet's `Ø` marks are vector paths: a CAD tool
  that draws its callouts as outlines leaves nothing for the text layer to carry, and the value cannot be
  recovered by any amount of geometry on the strokes. The plate scores 6/7 for exactly this reason - all
  six numbers the text layer holds are read, and the seventh is a picture. Reading those is a different
  job (cluster the drawn glyphs, read the crop, keep the leader that anchors them), and it is the same job
  the raster sheets need.
- **The scale audit has no pixel floor.** `scale.RELATIVE_TOLERANCE` is 4% of the value; a 1.5 mm
  dimension on a 1:2 sheet is 6 px at 200 dpi, where one pixel of arrow or extension-line error is 17%.
  `plastic-enclosure-1` therefore reports 6 of its 14 readings as suspect although the fit itself
  (3.917 px/mm against the 3.937 a 1:2 A4 expects) is right. A reading should be judged against the
  larger of a relative tolerance and an absolute one in the sheet's own pixels.
- **Raster reading is the weak half.** With the text layer taken away the front end finds 3 of the 13
  printed numbers on `exercise-1`, 3 of 13 on `flange-1` and 4 of 7 on `plate-pocket-1`, against 6 of 7 on
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
