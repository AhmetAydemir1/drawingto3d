"""Read-only review probes; temporary stores only, no browser driver or historical writes."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'eval/g12_runner')]
import test_guided_callouts as H
from drawingto3d import guided
import recipe_v2, produce_case
OUT=Path(__file__).parent
results=[]
with tempfile.TemporaryDirectory() as tmp:
    s=H.store.__wrapped__(Path(tmp)); t=H.TOKEN; H.seed_callouts(s)
    def cmd(action,payload):return s.edit_callout(t,s.load(t)['revision'],action,payload)
    cmd('transcribe',{'callout_id':'k1','raw_text':'10.00'})
    cmd('set_disposition',{'callout_id':'k1','disposition':'redundant','duplicate_of':'decision:thickness'})
    before=s.readiness(t)
    d=s.load(t)['decisions'];d['thickness']=20
    s.save(t,s.load(t)['revision'],d)
    after=s.readiness(t)
    results.append({'probe':'cited_decision_value_changed','before_thickness':10,'after_thickness':20,'before_ready':before['ready'],'after_ready':after['ready'],'coverage':after['coverage'],'plan_thickness':guided.make_plan(s.load(t)).model_dump()['parameters']['thickness']})
    cmd('transcribe',{'callout_id':'k1','raw_text':'30.00'})
    edited=s.readiness(t)
    results.append({'probe':'redundant_own_text_changed','raw_text':'30.00','actual_thickness':20,'ready':edited['ready'],'coverage':edited['coverage']})
    cmd('edit_region',{'callout_id':'k1','region':[.5,.5,.8,.8]})
    moved=s.readiness(t)
    results.append({'probe':'redundant_region_changed','ready':moved['ready'],'coverage':moved['coverage'],'callout_states':s.public(s.load(t))['callouts']})
# Execute ONLY the acceptance script's leftover classification block against a stub store.
p=ROOT/'eval/audits/20261007-g12-strategy-plate/g12_strategy_plate_acceptance.py'
module=runpy.run_path(str(p))
main=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
start=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='decided' for t in n.targets))
end=next(i for i,n in enumerate(main.body[start:],start) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='readiness' for t in n.targets))
actions=[]
globals_={'store':SimpleNamespace(load=lambda t:{'decisions':{'callout_reviews':[],'callout_targets':[]}}),'token':'test','rows':{'NEW REAL DIMENSION 123.45':['unexpected-callout']},'_reason_for':module['_reason_for'],'decide':lambda *a:actions.append(a),'record':lambda *a:None}
exec(compile(ast.Module(body=main.body[start:end],type_ignores=[]),str(p),'exec'),globals_)
results.append({'probe':'acceptance_unknown_leftover','actions':actions})
results.append({'probe':'producer_default','driver':str(produce_case.DEFAULT_DRIVER.relative_to(ROOT)),'driver_reads_full_manifest':'ROOT / "eval/guided_10_manifest.json"' in produce_case.DEFAULT_DRIVER.read_text(),'driver_reads_reference':'entry.get("reference_identifier_evaluator_only")' in produce_case.DEFAULT_DRIVER.read_text(),'driver_uses_producer_input':'G12_PRODUCER_INPUT' in produce_case.DEFAULT_DRIVER.read_text()})
recipe={'case_id':'review','source_sha256':'a'*64,'operator_basis':'source_drawing_only','callout_actions':[],'strategy_decision':{'kind':'extrude_profile'},'profile_actions':[{'profile_id':'outline_1'}],'notes':['examples/reference.STEP']}
v=recipe_v2.validate(recipe)
results.append({'probe':'unapplied_recipe_fields','accepted':v,'planned_actions':recipe_v2.planned_actions(v)})
(OUT/'probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
# JavaScript JSON.parse/stringify collapses integral-valued floats to integer JSON tokens.
def js_numbers(x):
    if isinstance(x,float) and x.is_integer():return int(x)
    if isinstance(x,list):return [js_numbers(v) for v in x]
    if isinstance(x,dict):return {k:js_numbers(v) for k,v in x.items()}
    return x
with tempfile.TemporaryDirectory() as tmp:
    s=H.store.__wrapped__(Path(tmp));t=H.TOKEN
    s.set_strategy(t,s.load(t)['revision'],{'kind':'extrude_profile'})
    payload=js_numbers(s.public(s.load(t))['decisions'])
    stored=s.load(t)['decisions']['build_strategy']
    same=payload['build_strategy']==stored
    payload['thickness']=20
    try:s.save(t,s.load(t)['revision'],payload);error=None
    except ValueError as e:error=str(e)
    results.append({'probe':'browser_json_roundtrip_rejected','strategy_structurally_equal':same,'stored_evidence':stored['evidence'],'posted_evidence':payload['build_strategy']['evidence'],'error':error,'saved_thickness':s.load(t)['decisions']['thickness']})
(OUT/'probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results[-1],ensure_ascii=False,indent=2))
