# drawingto3d

Turn a 2D technical drawing (PDF, PNG, JPG) into a 3D STEP solid — **offline**, on a local machine,
with the user able to correct the reading on the drawing itself.

Target box: one M1 / 16 GB Mac. No cloud service is contacted at run time; every model that runs is a
local one (Ollama) and every build step is deterministic Python.

> **Status: early research prototype, not a product.** One sheet converts end to end today, and the
> measurements that say what does and does not work are kept in the repository — including the
> failures. Nothing here claims general technical-drawing → STEP success.

## What is actually measured today

| Path | Measured result |
|---|---|
| Plate sheet, drawing → STEP through the rule-based engine (`propose` + `build-general`) | solid of **124 825.4 mm³** against the closed form's 124 825.4 (**0.0000 %**), bbox exactly **120.00 × 80.00 × 15.00 mm**, reopened STEP shows 4 hole cylinders + 1 pocket cylinder |
| Guided web UI (`/guided`) | calibration, contour choice, holes/pockets, draft STEP + STL preview, revision/undo, session reopen by URL — accepted in a real browser |
| Reading chain on vector PDFs (`observe` → `bind` → `meaning`) | every printed number located and bound; 14/17 to 17/17 claims resolved per sheet, each with its source span id |
| Raster sheets (PNG/JPG) | they read, then **refuse honestly**: no anchors → no scale → `pafta ölçeği okunamadı`. Contour closing on real scans is still open |
| Local model as planner (`model-plan`) | **fails**: the model returns a full JSON object but breaks the plan body (invalid `value`/`expr` choice, missing `type` discriminators, invented names). No model plan has reached the compiler yet |
| Four synthetic v2 parts, end-to-end | all four build a STEP and all four are **geometrically wrong** (bbox mismatch, wrong hole count/diameter). They are recorded as failures, and the current goal is to stop calling them "accepted" |

The full number table is [`eval/README.md`](eval/README.md); the accounting of what each change bought
and what it cost is [`CHANGES.md`](CHANGES.md).

## How it works

```
source file + source digest + page/view
  → unchanged base observations (observe)         vector PDF, or raster via Hough + tesseract
  → printed numbers bound to the ink they touch (bind)
  → each number read into the claim it supports (meaning)
  → supported measurement/relation constraints solved (sketch + sketch_constraints)
  → the plan those readings support (propose, or the local model)
  → deterministic CAD (general.py → build123d) → STEP + reopen + feature checks
  → only ever for the revision it was built from
```

Three data layers are kept apart: **base geometry** (source digest, reader version, stable ids),
**decisions** (profile, calibration, dimensions/relations, holes/pockets, contour edits, approvals) and
**computed result** (decision revision, solved geometry, audits, source statements, build status, file
paths). A new decision makes the old result stale instead of silently re-serving it.

Ground rules the code is held to (from [`PLAN.md`](PLAN.md)): no solution keyed on a file name, sample
number, known coordinate or fixed hole count; a reference STEP may only be read by the separate
evaluator; a guess is never presented as a measured dimension — the program asks instead; a valid solid
with correct outer dimensions is not proof that the part is right.

## Run it

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
pytest -q                                        # 820 tests collected
```

Reading chain over one sheet (`PYTHONPATH=src` is only needed for the `-m` form):

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli observe "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli bind    "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli meaning "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli propose "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/plate
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli build-general out/plate/plan.json out/plate/build \
  --drawing "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF"
```

(Verified end to end on that sheet: `build-general` reports `status: draft`, and its own plan audit passes
`valid_solid`, `export_round_trip`, declared bbox and volume, with 4 hole cylinders and 1 pocket cylinder —
"the CAD geometry matches the proposed plan"; the drawing reading is a separate check.)

Web UI:

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app     # → http://127.0.0.1:8765/guided
```

Local model as planner (needs Ollama with a vision model pulled; the model is only asked, never
trusted — its answer is judged by the schema, the citation check and the compiler):

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli model-plan "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF" out/model-plan-plate
```

Measurement harnesses:

```bash
PYTHONPATH=src .venv/bin/python eval/frontend.py                # reading front end, no model
PYTHONPATH=src .venv/bin/python eval/check_tables.py            # do the tables still match the records?
PYTHONPATH=src .venv/bin/python eval/baseline_report.py --check # model baseline records ↔ report
```

## Repository layout

| Path | What it holds |
|---|---|
| `src/drawingto3d/` | the product: `observe`/`raster`, `bind`, `meaning`, `proposal`, `planner`, `guided` + `app` + `static/`, `sketch`/`sketch_constraints`, `general`, `cadrun`, `cli` |
| `tests/` | 67 files, 820 tests |
| `eval/` | harnesses, the weak legacy metric and the feature-level evaluator, evidence packs, reports |
| `examples/` | drawings used as test/evaluation data only (see the note below) |
| `PLAN.md` | product acceptance conditions and the current status table |
| `HANDOFF.md` | the long session handoff record; `CHANGES.md` the change accounting |
| `docs/` | implementation plan, experiment-system brief, progress reviews, archived plans |
| `eval/reports/` | measured findings per slice, including the negative ones |

`out/` (run artefacts, sessions, STEPs) is git-ignored; the durable records live in `eval/reports/`,
`eval/audits/` and the documents above.

## Scope and honest limits

- Supported so far: a single-view, flat part archetype — profile extrusions, steps, through/blind
  holes, one rectangular pocket — plus user-guided draft generation for the same family.
- Not supported yet: raster scale anchoring, multi-view sheets, chain dimensions, asymmetric layouts,
  revolves, GD&T/manufacturing conformance. These refuse with a named reason rather than guessing.
- The shipped example drawings and STEP files come from public sources and a machining-training set;
  they are kept here as evaluation data and remain the property of their authors. If you own one of
  them and want it removed, open an issue.

## License

No license file is included yet, so all rights are reserved by default. If you want this to be
reusable, add the license you intend (MIT/Apache-2.0 are the usual choices for this kind of tool).
