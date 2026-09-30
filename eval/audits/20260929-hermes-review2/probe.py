"""Read-only product diagnosis; writes evidence only into this audit directory."""
import hashlib
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'src'))
from drawingto3d.ingest import load_page
from drawingto3d.perceive import perceive
from drawingto3d.scale import measure, measure_spans, consensus
from drawingto3d.cli import plan_from_drawing
from drawingto3d_lab.state import Lab

rows = []
for part in ('pilot-plate-01', 'pilot-plate-02', 'pilot-step-01'):
    path = ROOT / 'out/lab/data/v2' / part / 'drawing.pdf'
    page = load_page(path)
    raw = [dict(text=s.text, value=s.value) for s in page.spans]
    _, spans = perceive(page)
    pairs = measure(spans)
    fits = {}
    for minimum in (2, 3):
        fit, inliers = consensus(pairs, minimum=minimum)
        fits[str(minimum)] = dict(calibration=asdict(fit) if fit else None, inliers=inliers)
    row = dict(part=part, raw_text=raw,
               retained=[dict(text=s.text,value=s.value,anchor_mode=s.anchor_mode,
                              anchors=s.anchors) for s in spans],
               calibration_pairs=pairs, fits=fits)
    rows.append(row)
    print(part, 'pairs=', pairs, 'fits=', fits, flush=True)

class SpyChat:
    model = 'spy-no-network'
    calls = 0
    def complete(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('Unexpected inference; this probe should stop at calibration')

with tempfile.TemporaryDirectory(prefix='hermes-review2-') as tmp:
    spy = SpyChat()
    payload, reason = plan_from_drawing(
        ROOT / 'out/lab/data/v2/pilot-plate-01/drawing.pdf', Path(tmp)/'plan', spy)
    spy_result = dict(inference_calls=spy.calls, payload=payload, reason=reason)
    lab = Lab(Path(tmp)/'lock')
    lab.root.mkdir()
    # Window after O_EXCL creates the file and before the owner writes its payload.
    lab.lock_path.write_bytes(b'')
    try:
        lock_result = dict(result=lab.acquire_heavy('contender'))
    except Exception as exc:
        lock_result = dict(exception=type(exc).__name__, message=str(exc))

manifest = json.loads((ROOT/'out/lab/review-checkpoint/artifact-manifest.json').read_text())
checked = []
def walk(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            p=ROOT/value['path']
            checked.append(dict(path=value['path'],exists=p.is_file(),
                                matches=p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==value['sha256']))
        for v in value.values(): walk(v)
    elif isinstance(value,list):
        for v in value: walk(v)
walk(manifest)
payload=dict(calibration=rows, model_call_probe=spy_result, partial_lock_probe=lock_result,
             manifest_checked=len(checked),manifest_mismatches=[x for x in checked if not x['matches']])
(OUT/'observations.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
print('model inference calls:',spy.calls)
print('partial lock:',lock_result)
print('manifest checked:',len(checked),'mismatches:',payload['manifest_mismatches'])
