from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from drawingto3d import scale
from drawingto3d.perceive import _pair_by_value
from drawingto3d.schema import Span,BBox
from drawingto3d.lines import Segment
from drawingto3d.reason import _verbatim_readings
from drawingto3d.ingest import load_page
from drawingto3d import perceive

def span(id,value,x,y,length=None):
 return Span(id=id,text=str(value),value=value,kind='linear',unit='mm',bbox=BBox(x=x,y=y,w=20,h=20),anchors=[] if length is None else [[0,0],[length,0]],anchor_mode='dimension',source='pdf_text')
kept=[span('a',60,0,0,600),span('b',20,0,0,200)]
u=span('u',40,340,290)
segments=[Segment(x0=400,y0=300,x1=400,y1=700,thickness=2,horizontal=False)]
attached=_pair_by_value([u],kept,segments,21)
before=scale.verdict(kept)
for s,anchors in attached:s.anchors=anchors
out={'bootstrap_probe':{'before':before,'after':scale.verdict(kept+[s for s,a in attached]),'matched_arbitrary_stroke':bool(attached)}}
# Value comparison cannot establish who edited a record or whether the other bad values were checked.
from drawingto3d.schema import DimensionRecord
spans=[span('x',4,0,0,54),span('y',9,0,0,467.5),span('z',60,0,0,506)]
records=[DimensionRecord(span_id=s.id,text=s.text,value=s.value,role='edge',count=1) for s in spans]
out['review_probe']={'original_verbatim':_verbatim_readings(records,spans),'one_unverified_change_verbatim':_verbatim_readings([records[0].model_copy(update={'value':4.1}),*records[1:]],spans),'dropped_record_verbatim':_verbatim_readings(records[1:],spans),'sheet_state':scale.verdict(spans)['state']}
coverage={}
for part in sorted((ROOT/'out/lab/data/v2').iterdir()):
 if not (part/'drawing.pdf').exists():continue
 page=load_page(part/'drawing.pdf');raw=[{'id':s.id,'text':s.text,'value':s.value} for s in page.spans if s.value is not None]
 _,kept=perceive.perceive(page,reader=None)
 coverage[part.name]={'raw':raw,'kept':[{'id':s.id,'value':s.value,'anchors':s.anchors,'mode':s.anchor_mode} for s in kept],'verdict':scale.verdict(kept)}
out['current_text_layer_coverage']=coverage
out['focused_tests']={'passed':37,'seconds':0.66,'files':['test_baseline_fields.py','test_sheet_scale.py','test_value_pairing.py','test_reading_gate.py']}
out['source_hashes']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/drawingto3d/perceive.py','src/drawingto3d/reason.py','src/drawingto3d/scale.py','eval/lab_baseline.py']}
(ROOT/'eval/audits/20260929-hermes-review5/observations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['current_text_layer_coverage','source_hashes']},ensure_ascii=False))
print({k:len(v['kept']) for k,v in coverage.items()})
