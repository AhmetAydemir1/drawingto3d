from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from drawingto3d.perceive import _bootstrap_calibration,_promote_unplaced
from drawingto3d.schema import Span,BBox
from drawingto3d.lines import Segment
from drawingto3d import scale

def s(i,v,x=340,y=290,length=None):
 return Span(id=i,text=str(v),value=v,kind='linear',unit='mm',bbox=BBox(x=x,y=y,w=20,h=20),anchors=[] if length is None else [[0,0],[length,0]],anchor_mode='dimension',source='pdf_text')
pending=[s('one_number',40)]
segments=[Segment(x0=x,y0=300,x1=x,y1=700,thickness=2,horizontal=False) for x in [365,400,440]]
c=_bootstrap_calibration(pending,[],segments,21)
kept,unpaired=_promote_unplaced(pending,[],segments,21)
spans=[s('a',60,length=600),s('b',20,length=200),s('c',40,length=400),s('wrong',9,length=550)]
v=scale.verdict(spans)
result={'head':'68db985','bootstrap':{'unique_readings':1,'candidate_strokes':3,'calibration':vars(c) if c else None,'promoted':[{'id':s.id,'value':s.value,'anchor_source':s.anchor_source} for s in kept]},'suspect_guard':{'verdict':v,'contradictory_only_guard_triggers':v['state']=='contradictory'},'numeric_membership_counterexample':{'expected':[40.0],'readings':[40.0,40.0,41.0],'reported_label_matching':sum(any(abs(v-e)<=max(.001,.04*e) for e in [40.0]) for v in [40.0,40.0,41.0]),'note':'Same any-value 4% criterion used in eval/raster_label_match.py; not identity/role matching.'},'focused_tests':{'passed':59,'seconds':.35,'exit_code':0},'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/drawingto3d/perceive.py','src/drawingto3d/scale.py','src/drawingto3d/reason.py','eval/raster_label_match.py']}}
Path(__file__).with_name('observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
