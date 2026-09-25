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
| plastic-enclosure-1 | vektör | 11/11 | 0 | 3.917 | 6 |
| plate-pocket-1 | vektör | 5/7 | 0 | 7.867 | 0 |
| exercise-1 | raster | 3/13 | 6 | 5.85 | 8 |
| studycadcam-60 | raster | 6/9 | 6 | 3.312 | 7 |
| studycadcam-50 | raster | 0/3 | 2 | - | 0 |
| flange-1 | raster | 3/13 | 1 | - | 0 |

The vector numbers are the text layer read through the geometry gate; the raster ones are the same gate
with tesseract behind it, which is the floor, not the finished reader — `eval/baseline.py` is where the
vision model enters.

## How a number is read

`perceive` finds printed numbers by the geometry that carries them, not by their size:

1. `lines.thin_segments` keeps strokes 2–4 px thick and 36–1400 px long. On the A4 practice sheet the
   outlines and title-block rules measure 5–6 px, so weight alone is not the filter — the arrows are.
2. A candidate is a cluster of glyphs with a **dimension line** beside it (`lines.dimension_line_near`:
   an arrow at both ends, the number between) or a **leader** (`lines.leader_near`: one arrow, the words
   beside the blank end of the shaft). Title block, part numbers, copyright years and the frame band all
   die here: on `my_part.jpg`, 364 glyph candidates become 21 that cover 10 of the 13 printed values.
3. Text along a vertical line is printed a quarter turn round, so a glyph is judged on its longest side
   and its crop is turned upright before it is read. Filtering those digits on height (or on width) is
   how a printed 80 arrives as a bare `0`.
4. `reader.read_dimension` asks the local vision model first, tesseract second, and reports agreement. An
   answer that does not fit the crop it came from — letters on a dimension line, more digits than the box
   could hold — is refused instead of kept; that is where `R100` and `R105` hallucinations come from.
5. Every accepted number keeps the two ends of its own line as `Span.anchors`, so its value stays
   attached to the geometry that printed it.
6. `scale.audit` fits the sheet's own scale (px per mm) from those anchors and names the records that do
   not fit it — a misread, or a number attached to a line that was never its own. On `my_part.jpg`:
   5.95 px/mm with a 2.4% spread (A4 at 200 dpi, scale 1:2, expects 5.9) — no title block, dpi or scale
   note needed.

## Known gaps

- **Diagonal strokes are not found.** `lines.thin_segments` returns horizontal and vertical strokes only,
  so every leader drawn at an angle — which is how most callouts are drawn — is invisible to the gate. On
  `plate-pocket-1` that is `Ø50,00` and `6,80 THRU ALL`: the sheet's two callouts, both lost while all five
  linear dimensions come through. On the flange it is the `6 x Ø6.40` and `Ø11.00` counterbore callouts.
- **The scale audit has no pixel floor.** `scale.RELATIVE_TOLERANCE` is 4% of the value; a 1.5 mm
  dimension on a 1:2 sheet is 6 px at 200 dpi, where one pixel of arrow or extension-line error is 17%.
  `plastic-enclosure-1` therefore reports 6 of its 14 readings as suspect although the fit itself
  (3.917 px/mm against the 3.937 a 1:2 A4 expects) is right. A reading should be judged against the
  larger of a relative tolerance and an absolute one in the sheet's own pixels.
- **Raster reading is the weak half.** The front end finds 3/13 printed numbers on `exercise-1` and 3/13
  on `flange-1` when the text layer is absent; on the same sheets with the text layer it finds all of
  them. `eval/frontend.py --as-raster` is the harness for this — it reads a vector sheet's raster with
  the truth known exactly, so the CV reader can be improved without another hand-made example.
- Synthetic sheets (build a part in CadQuery, render the three views, keep the part as truth) are the
  plan for volume; they belong in this folder as `synthetic.py` when Phase 2 lands.
- Nothing here scores *how much of the drawing was used*. A part built from 2 of 8 records and a part
  built from all 8 can both pass `vector`; coverage has to be its own check.
- The reading front end is not yet the path the build takes: `reason_drawing` reads one question per
  number through `roles.read_records`, which asks the vision model about every span the gate kept. Wiring
  the two together is what turns the measured coverage above into measured records.
