# Flanged / rotational archetype — the evidence on disk, before any code (2026-09-28)

What the goal ("any PDF in, a solid out, minimum questions") needs beyond the plate archetype, measured on the
two artefacts we have for the same part: the sheet `examples/pdf with steps/10/Exercise 12.pdf` and its own
reference `Exercise 12.STEP` (this project treats the reference as the arbiter of the reading, never as input to
it).

Reproduce: `PYTHONPATH=src .venv/bin/python eval/flange_evidence.py exercise-12` (writes
`out/flange-evidence/exercise-12.json`), and the STEP-side facts with `.venv-cad/bin/python` (see the notes at
the end).

## 1. What the sheet's own geometry gives (vectors only, no model)

| fact | value |
| --- | --- |
| circles read | 42 |
| px/mm fitted by the reading | 1.550 (front end: 19/20 covered, 14 suspect rows) |
| concentric stack | 1 — centre (347.0, 379.7) px, 5 circles, Ø77.17 / 93.50 / 142.25 / 160.55 / 274.31 mm |
| printed diameters matched into that stack | Ø76, Ø92, Ø140, Ø158, Ø270 — **every one drawn 1.6 % larger than printed** |
| bolt ring about that centre | 6 × Ø18.32 mm on Ø227.61 mm (spread 0.000) |
| printed plain values on the sheet | 88.00 · 112.00 · 132.00 · 170.00 · 54.00 · 86.00 · 20.00 · 19.00 · 6.00 · 10.00 … |

The consistent +1.6 % is a *calibration* fact, not a reading failure: 425.2 px / Ø270 prints = 1.5748 px/mm, the
reading fitted 1.550 from its own rows (whose rounding is ±1 mm at 1:5). Two consequences, and the second is the
one that matters:

- a feature that carries a printed number needs **no** scale — the printed value is the decision, the drawn size
  is only a check (this is what `meaning.py`'s claims already do);
- the scale (and with it the ±1 % check tolerance) is only needed for *un-dimensioned* geometry — and on this
  sheet the tolerance has to come from the sheet's own row noise: with 1 % fixed, five correctly printed
  diameters land as `suspect` and 14 rows are flagged, while the same five are confirmed under 3 %.

## 2. What the reference STEP gives (`.venv-cad/bin/python`, cadquery)

- edges 206 · faces of the body: 9 tori, 60 cylinders (the front end's reading of it)
- **flange thickness 20 mm**: every Ø18 hole is a cylinder 20 long (circle centres 20 apart along its axis)
- **Ø18 holes, 36 of them, with two perpendicular axes**:
  - normal **y** (one flange face): 24 holes, radial groups of 4 at radii 83.09 · 88.19 · 93.01 · 107.08 · 112.15 · 116.99 mm
  - normal **x** (the perpendicular flange): 12 holes, groups of 4 at radii 80.27 · 83.28 · 89.00 · 91.73 mm
- the radii are the sheet's printed **88.00** and **112.00** — those are *bolt spacings/radii*, not PCDs, and the
  hole pattern is a **grid** (the reference's own holes sit 88 mm apart in rows), not a single bolt circle
- printed diameters ↔ reference radii (all within 0.5 mm): Ø270 → r135 ✓ · Ø220 → r110 ✓ · Ø180 → r90 ✓ ·
  Ø158 → r79 ✓ · Ø140 → r70 ✓ · Ø120 → r60 ✓ · Ø116 → r58 ✓ · Ø92 → r46 ✓ · Ø76 → r38 ✓ · Ø18 → r9 (holes) ✓ ·
  R25 → r25 ✓ · R10 → r10 ✓ · R8 → r8 ✓

So the sheet's printed number set is *complete and consistent* for this part: the read is not the bottleneck —
which is the same conclusion the front end reached (19/20). The bottleneck is that no archetype reads this set
and no plan shape draws it.

## 3. What the archetype must therefore decide (and how each decision is checkable)

1. **Class** — done (`proposal.part_class`): `rotational-flanged`, evidence = the 5-circle stack, biggest circle
   0.193 of the page width.
2. **Flange faces** — one per concentric stack: outer Ø from the biggest circle (274.31 px-measured ↔ printed
   Ø270), bores from the smaller circles in the same stack (Ø76/Ø92/…), thickness from the sheet's own printed
   thickness pair (20.00, twice) or from the reference-verified hole length.
3. **Bolt pattern** — *not* a PCD. From the face view: hole diameter (Ø18.32 measured ↔ printed Ø18), the
   spacings (88.00, 112.00) and the count per row; the reference's 4-fold groups say 4 rows × 6 holes on the big
   flange (24) and 4 × 3 on the other (12). A circular-PCD assumption would put holes in the wrong places — this
   is the trap to avoid, and the reference is what proves it.
4. **Body** — a 90° bend between the two flange axes, diameters from the same printed chain (Ø158/Ø140/Ø120 and
   the printed 132.00 as the likely bend radius); `geo.ring_revolve` already exists for exactly this.
5. **Scale anchor** — the fitted 1.550 px/mm disagrees with the printed round numbers by 1.6 %. Anchoring the
   scale on one round-numbered feature (Ø270 on a 425.2 px circle → 1.5748) would remove that error and would
   also be the *only* way a raster sheet can get a scale at all (see the eight raster sheets that still refuse
   with "pafta ölçeği okunamadı").

## 4. Slice order proposed (each with its own measurement) — C1/C2 landed same day

| # | slice | gate | state |
| --- | --- | --- | --- |
| C1 | scale anchor from a printed round value (`fit the scale so one printed diameter lands on its round number`, per sheet) | plate 7/7, plastic 14/14, `Drawing.pdf` 16/17 and the stored request hashes unchanged; sheet 10's drawn-vs-printed deviation 1.6 % → <0.5 % | **done** via the flange's own printed Ø270 (425.2 px → 1.5747 px/mm) + the 2 % agreement gate on row-based calibrations (`advise.CALIBRATION_AGREEMENT`); the flat sheets' rows (0.42-0.71 % agreement) are untouched |
| C2 | rotational decisions: flange stack → outer Ø/bore/thickness + bolt grid (diameter, spacings, count) as *proposals* the flow can already show | the four sheets' decision counts unchanged except sheet 10 (1 → the flange decisions); each decision's evidence quotes the span ids | **done**: `advise._flange_proposals` (10 decisions for sheet 10, one accept leaves no question open); holes keep their own measured centres rather than a PCD |
| C3 | plan shape for the class (two flanges + `ring_revolve` body, fuse, bolt holes as cuts) + build | build produces one valid solid; `step_facts.py` against `Exercise 12.STEP`: bbox within 2 %/1 mm and the Ø18 hole count/positions checked as a *new* fact type (grid, not PCD) | **half done**: the flange face builds — [270.0, 270.0, 20.0] mm, cylinders r135/r38/6 × r9 (the reference's own flange); the bend body and the second flange are still open |

C1 is small, general and testable now; C2 is the decision layer; C3 is the modelling slice and the first one
that can honestly claim "this PDF opened".

## 5. Open questions to settle before C3

- Which of the printed Ø116/Ø120 is the big flange's bore and which is the body's neck? (Both exist as reference
  radii r58/r60.)
- The bend: printed 132.00 vs the reference's r135 (flange OD radius) — need the section view's arc to decide
  whether the body's centreline radius is 132 or 135.
- Does the flow *ask* for anything on a rotational sheet once C2 exists? Target: nothing but a confirmation.
