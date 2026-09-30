"""Independent review: fake adapters only, no inference/cloud and no product edits."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'src'))
from drawingto3d.inference_log import Recorder, RecordedChat, read_record
from drawingto3d.llama import OllamaChat

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

baseline = load('baseline_review3', 'eval/lab_baseline.py')
trace = load('trace_review3', 'eval/calibration_trace.py')
observations = {}
with tempfile.TemporaryDirectory(prefix='hermes-review3-') as tmp:
    tmp = Path(tmp)
    log = tmp/'inference-log.json'
    read = Recorder(log, label='read')
    read.note('vision', image_sent=True, image_bytes=100)
    before = read_record(log)
    build = Recorder(log, label='build')
    build.note('coder', image_sent=False)
    after = read_record(log)
    observations['T01_log_overwrite'] = dict(before=before, after=after,
        reproduced=before['image_sent'] and not after['image_sent'])

    interrupted = Recorder(tmp/'interrupted.json')
    def stop(*args, **kwargs):
        raise KeyboardInterrupt('controlled interruption, no real inference')
    with patch.object(OllamaChat, '__init__', lambda self,*args,**kwargs:None):
        with patch.object(OllamaChat, 'complete', stop):
            chat = RecordedChat('fake', recorder=interrupted)
            try:
                chat.complete('test', image_png=b'fake-image')
            except KeyboardInterrupt:
                pass
    observations['T02_unfinished_call'] = read_record(interrupted.path)

    commands = []
    plan = tmp/'model'/'plan.json'
    def cli(args, workdir, **kwargs):
        commands.append(args)
        if args[0]=='model-plan':
            plan.write_text('{}')
            return dict(timed_out=False,result={'plan':str(plan)})
        return dict(command=args,exit_code=2,result=None,stderr_tail='source path missing')
    with patch.object(baseline, '_cli', cli):
        baseline._model_step(tmp/'drawing.pdf', tmp)
    observations['T03_model_build_source'] = dict(commands=commands,
        missing_drawing_flag='--drawing' not in commands[-1])
    observations['T04_timeout'] = dict(actual_cli_seconds=baseline.CLI_TIMEOUT,
                                      agreed_case_seconds=600)

observations['calibration_now'] = []
for part in ('pilot-plate-01','pilot-plate-02','pilot-step-01'):
    row = trace.trace_part(ROOT/'out/lab/data/v2'/part)
    observations['calibration_now'].append(dict(part=part,pairs=row['calibration_pairs'],fits=row['fits'],
        kept=[s.get('text') for s in row['kept']],dropped=[s.get('text') for s in row['dropped_by_the_gate']]))
    print(part,row['calibration_pairs'],flush=True)
target=OUT/'observations.json'
if target.exists():
    raise FileExistsError('Preserve prior observations; choose a new audit output.')
target.write_text(json.dumps(observations,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in observations.items() if k!='calibration_now'},ensure_ascii=False))
