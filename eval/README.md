# eval

What "better results" means for this project, in numbers. Two questions per sheet:

1. **Reading** — did the reader find every number printed on the sheet, and nothing else?
2. **Building** — is the STEP it built a functionally equal part to the reference STEP?

Run:

```bash
PYTHONPATH=src .venv/bin/python out/baseline.py     # reading turn only, one JSON per sheet in out/baseline/
.venv-cad/bin/python eval/report.py                 # table + out/eval/report.json
```

`out/baseline.py` is a script, not a package module: it calls `reason_drawing` with no records and
keeps whatever the reader produced, including its failures. It needs the vision model (Ollama).
`eval/report.py` needs the CadQuery interpreter to read reference STEP files.

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

A reference STEP is the truth for shape, not for intent: `2389K26` is a cast PVC elbow whose 174
faces nobody could or would rebuild from a catalog drawing. The eval therefore holds the pipeline to
a *functionally equal* part — right size, right bores, right wall order — and not to the same B-rep.

## Cases

`catalog-fitting` — McMaster-Carr vector PDFs, inches, two views plus a shaded isometric, 3 dimensions
total, and the part identity living in a callout (`2X 1 1/4 Pipe Size`) that only a standard table
resolves.

`practice-sheet` — StudyCADCAM raster sheets, mm, full third-angle views with Ø/R/C callouts and
hatched sections. Reading-only for now: there is no reference STEP for them, and re-modelling them by
hand is the honest way to get one.

## Known gaps

- Two reference pairs is not an eval set. Synthetic sheets (build a part in CadQuery, render the
  three views, keep the part as truth) are the plan for volume; they belong in this folder as
  `synthetic.py` when Phase 2 lands.
- Nothing here scores *how much of the drawing was used*. A part built from 2 of 8 records and a part
  built from all 8 can both pass `vector`; coverage has to be its own check.
