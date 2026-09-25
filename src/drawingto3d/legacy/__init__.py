"""Retired first-generation path. Kept for reference, not imported by the app.

What it did: segment views (OpenCV), read every dimension text with tesseract, ask the vision
model to name each number's role, then build a FeatureGraph and a build123d solid, stopping with
a question whenever a number was missing.

Why it is retired: the binder guessed roles from a flat number list with no anchors on the drawing,
so the graph was only as good as a 7B vision call per number, and the review UI never showed the
user what had been understood.

Worth reusing later (do not delete):
  legacy/contours.py   view_outline / view_islands -> closed mm contours from a view bitmap
  legacy/solid.py      build_part -> deterministic profile+thickness+holes builder
  legacy/strategies.py graph_from_bindings -> span-cited FeatureGraph construction
  schema.FeatureGraph  the intermediate model those three fed

Its tests live in legacy/tests/. They need a fixture image that is not in the repo
(examples/solidworks-katc4b1-8-1024x729.jpg) and are therefore skipped there.
Run them with: pytest src/drawingto3d/legacy/tests
"""
