"""G11R-03 (bağımsız inceleme): “Bu bir ölçü/not değil” sonrası oto-ilerleme, gerçek betikte.

Kök neden: karar satırı görünür listeden düştüğünde (ihmal edilenler gizliyken) `busy(false) → render()
→ renderCallouts()` seçimi temizliyordu; `advanceAfterDecision`'ın `selectedCallout===previousId`
kapısı bu yüzden erken dönüyor ve sıradaki açık alana geçilmiyordu (20261007 G9/G11 bağımsız
incelemesi, G11R-03 — gerçek tarayıcıda `ui_fix_regression.py` ile de doğrulandı).

Bu dosya servis edilen `guided.js`'i olduğu gibi (yalnız `preview.js` import satırı çıkarılmış) DOM
saplamalarıyla Node'da çalıştırır: `command → sunucu → yeniden çizim → oto-ilerleme` zincirinin
tamamı gerçek betik koduyla yürür. Senaryolar seçimin nereye taşındığını ve `goToCallout`
çağrılarını doğrular — sözleşme (hangi dize geçiyor) değil davranış.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

from drawingto3d.app import ROOT

HEAD = """// G11R-03 regresyon sürücüsü: gerçek guided.js, saplama DOM ile.
function makeCtx(){return new Proxy({},{get:(t,k)=>(k in t?t[k]:(...a)=>{}),set:(t,k,v)=>{t[k]=v;return true;}});}
function makeEl(id){const el={id,children:[],style:{},dataset:{},checked:false,value:'',textContent:'',hidden:false,disabled:false,
 classList:{add(){},remove(){},toggle(){},contains(){return false;}},
 replaceChildren(...a){el.children=a;},append(...a){el.children.push(...a);},addEventListener(){},removeEventListener(){},
 getContext(){return makeCtx();},scrollIntoView(){},focus(){},blur(){},click(){},select(){},remove(){},
 setPointerCapture(){},releasePointerCapture(){},querySelectorAll(){return [];},getBoundingClientRect(){return {x:0,y:0,width:10,height:10};}};return el;}
const registry={};function el(id){return registry[id]||(registry[id]=makeEl(id));}
globalThis.document={getElementById:id=>el(id),createElement:tag=>makeEl('new-'+String(tag)),createTextNode:t=>({textContent:String(t)}),querySelectorAll(){return [];},querySelector(){return null;},addEventListener(){},body:makeEl('body')};
globalThis.Image=class{constructor(){this.width=0;this.height=0;this.onload=null;this.onerror=null;}set src(v){}get src(){return '';}};
globalThis.location={search:'',href:'http://127.0.0.1/guided'};
globalThis.history={replaceState(){}};
globalThis.window=globalThis;
globalThis.fetch=async()=>{throw Error('fetch çağrılmamalı');};
function showStl(){return Promise.resolve();}
// __SCRIPT__
"""

TAIL = """
// ---- deterministik sürücü ----
renderTarget=function(){};loadReadiness=function(){};
const gotoCalls=[];
goToCallout=(function(base){return function(id){gotoCalls.push(id);return base(id);};})(goToCallout);
function fx(ids){return {token:'tok',revision:1,effective_callouts:ids.map(id=>({id,ignored:false,unbindable:false})),callouts:[],
 decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p1'},options:{profiles:[{id:'p1',kind:'circle',points:[]}],circles:[],measurements:[]},
 questions:[],proposals:[],can_undo:false};}
function reset(ids,showIgnored=false){state=fx(ids);el('callout-show-ignored').checked=showIgnored;selectedCallout=null;gotoCalls.length=0;}
function ignorePost(id){const post=JSON.parse(JSON.stringify(state));post.revision+=1;
 post.effective_callouts=post.effective_callouts.map(r=>r.id===id?{...r,ignored:true}:r);return post;}
const results={};
(async()=>{
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>ignorePost('k2');
 await command('set_ignored',{callout_id:'k2',ignored:true});
 results.mid={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k2']);selectedCallout='k2';
 api=async()=>ignorePost('k2');
 await command('set_ignored',{callout_id:'k2',ignored:true});
 results.last={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k1','k2','k3']);selectedCallout='k3';
 api=async()=>ignorePost('k3');
 await command('set_ignored',{callout_id:'k3',ignored:true});
 results.wrap={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k1','k2','k3'],true);selectedCallout='k2';
 api=async()=>ignorePost('k2');
 await command('set_ignored',{callout_id:'k2',ignored:true});
 results.show={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>{selectedCallout='k1';return ignorePost('k2');};
 await command('set_ignored',{callout_id:'k2',ignored:true});
 results.userMoved={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>JSON.parse(JSON.stringify(state));
 await command('set_ignored',{callout_id:'k2',ignored:true});
 results.unresolved={selected:selectedCallout,goto:gotoCalls.slice()};
 reset(['k1','k2']);selectedCallout=null;
 state.effective_callouts=state.effective_callouts.map(r=>r.id==='k2'?{...r,ignored:true}:r);
 advanceAfterDecision('k2',['k1']);
 results.missing={selected:selectedCallout,goto:gotoCalls.slice()};
 console.log('__RESULT__'+JSON.stringify(results));
})().catch(e=>{console.log('__ERROR__'+((e&&e.stack)||e));process.exit(1);});
"""

EXPECTED = {
    # G11R-03'ün ta kendisi: ortadaki satır kapatılınca sıradaki açık alan SONRAKİsidir (k3), başa dönmez.
    "mid": {"selected": "k3", "goto": ["k3"]},
    # Son açık satır kapanınca ilerlenecek yer yok — seçim uydurulmaz.
    "last": {"selected": None, "goto": []},
    # Sondan başa sarma gerçek çözülmemiş sırayı izler.
    "wrap": {"selected": "k1", "goto": ["k1"]},
    # “İhmal edilenleri göster” açıkken satır listede kalır; ilerleme yine kurulur.
    "show": {"selected": "k3", "goto": ["k3"]},
    # Kullanıcı komut sürerken başka satıra geçtiyse oto-ilerleme onu geri çekmez.
    "userMoved": {"selected": "k1", "goto": []},
    # Karar satırı GERÇEKTEN çözülmediyse (ignored=false) zıplanmaz.
    "unresolved": {"selected": "k2", "goto": []},
    # Savunma: önceki kimlik sırada yoksa tüm sıra baştan taranır.
    "missing": {"selected": "k1", "goto": ["k1"]},
}


def _assembled() -> str:
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    lines = script.splitlines()
    assert lines[0].startswith("import "), "guided.js'in ilk satırı preview import'u olmalı"
    return HEAD.replace("// __SCRIPT__", "\n".join(lines[1:])) + TAIL


def test_advance_after_the_not_a_measure_decision_reaches_the_next_open_field(tmp_path):
    """G11R-03: ignore/hint-ignore sonrası oto-ilerleme — yedi davranış senaryosu gerçek betikte."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok: guided.js davranış regresyonu bu makinede çalıştırılamıyor")
    assert "if(selectedCallout&&selectedCallout!==previousId)return;" in (
        ROOT / "guided.js").read_text(encoding="utf-8")
    source = tmp_path / "advance_driver.js"
    source.write_text(_assembled(), encoding="utf-8")
    proc = subprocess.run([node, str(source)], capture_output=True, text=True, timeout=120)
    stdout = proc.stdout
    assert "__ERROR__" not in stdout, stdout
    assert proc.returncode == 0, (proc.returncode, stdout, proc.stderr)
    marker = "__RESULT__"
    assert marker in stdout, (stdout, proc.stderr)
    results = json.loads(stdout.split(marker, 1)[1].splitlines()[0])
    assert set(results) == set(EXPECTED), (sorted(results), sorted(EXPECTED))
    for scenario, want in EXPECTED.items():
        assert results[scenario] == want, (scenario, results[scenario], want)


def test_the_recorded_order_comes_from_before_the_decision_not_the_filtered_list(tmp_path):
    """Sıra karar ÖNCESİ görünür listeden alınır: filtreli liste baştan taransa k3 değil k1 seçilirdi."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "previousOrder=calloutList().map(row=>row.id)" in script
    assert "advance={id:previous,order:previousOrder}" in script
    assert "base=order&&order.length?order:calloutList().map(row=>row.id)" in script
