"""Reproduce the deterministic plate path and compare only after building.

    PYTHONPATH=src .venv/bin/python eval/plate_plan.py

The production planner never sees the reference STEP. This harness keeps its results
separate from out/eval, which measures the older role/model path.
"""
from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from drawingto3d.ingest import load_page
from drawingto3d.plate import propose_plate
from drawingto3d.plan import build_plan
from drawingto3d.cadrun import _cad_python


def main():
    drawing = ROOT / 'examples/pdf with steps/5/Plate With A Pocket Drawing.PDF'
    truth = ROOT / 'examples/pdf with steps/5/plate with a pocket.STEP'
    folder = ROOT / 'out/plate-plan'
    start = time.perf_counter()
    plan = propose_plate(load_page(drawing))
    if plan is None:
        raise SystemExit('plate plan not recognized')
    step, _ = build_plan(plan, drawing, folder)
    build_seconds = time.perf_counter() - start
    # Reference comparison occurs in the CAD interpreter, strictly after prediction.
    script = '''
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'eval'))
import metrics
import cadquery as cq
produced, truth = metrics.describe(sys.argv[2]), metrics.describe(sys.argv[3])
a = cq.importers.importStep(sys.argv[2]).val()
b = cq.importers.importStep(sys.argv[3]).val()
# This fixture uses the same coordinate frame. Do not move the prediction using truth.
difference = a.cut(b).Volume() + b.cut(a).Volume()
print(json.dumps(dict(produced=produced, truth=truth,
                     verdict=metrics.compare(produced, truth),
                     symmetric_difference_mm3=difference)))
'''
    completed = subprocess.run([_cad_python(), '-c', script, str(ROOT), str(step), str(truth)],
                               capture_output=True, text=True, check=True, timeout=120)
    report = json.loads(completed.stdout)
    report['build_seconds'] = round(build_seconds, 3)
    report['reference_used_for_prediction'] = False
    report['scope'] = 'One supported vector plate family; inferred dimensions remain draft assumptions.'
    (folder / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['verdict']['pass'] or report['symmetric_difference_mm3'] > 1e-3:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
