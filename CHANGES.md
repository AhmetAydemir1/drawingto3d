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

## Measured, not yet changed

The raster half of the callout: splitting a line of drawn words so that the number inside it is read on its
own. Measured on the plate's raster path — the `4` is a cluster of one, the three glyphs of `6,80` cluster
with the two glyphs of the line *below* them into one five-glyph cluster spanning 72 px and two printed
lines, and the crop of that is what tesseract answers `08°9` for. Evidence and the failing case are in
`eval/README.md` (Known gaps) and `out/probe/probe_callout_cluster.py`.
