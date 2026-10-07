"""G12.1b — kapsam kararı UI sözleşmesi (PLAN-25 §8–§21): gerçek betik, saplama DOM ile.

Ölçülen çelişki (PLAN-25 §2): backend'de `build_relevant_unsupported` build'i bloklarken arayüz
`row.ignored||row.unbindable` satırı çözülmüş sayıyor ve `set_unbindable` oto-ilerlemeye giriyordu.
Bu dosya yeni sözleşmeyi davranış olarak çiviler:

* çözülmüşlük kararı BACKEND kapsam kovasından okunur (`state.coverage`), tarayıcıda ikinci bir
  kapsam motoru yok;
* `not_model_input` ve geçerli `redundant` çözer ve oto-ilerler;
* `build_relevant_unsupported`, `legacy_unclassified` ve `invalid_duplicate` çözmez, zıplanmaz;
* "Sonraki eksik" desteklenmeyen satıra UĞRAR (atlamaz);
* kapsam özeti backend `counts`'undan çizilir; desteklenmeyen madde üretimi kapalı tutar;
* eski belirsiz “Modele uygulanmayacak” copy'si ve `set_unbindable` çağrısı arayüzden kalkar.

Sürücü, servis edilen `guided.js`'i olduğu gibi çalıştırır (yalnız preview import satırı çıkarılır);
kapsam kovalarını SUNUCUNUN yanıtı kurar — tarayıcının kendi hesabı değil.
"""
import json
import shutil
import subprocess

import pytest

from drawingto3d.app import ROOT

HEAD = """// G12.1b sürücüsü: gerçek guided.js, saplama DOM ile.
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
renderTarget=function(){};
const gotoCalls=[];
goToCallout=(function(base){return function(id){gotoCalls.push(id);return base(id);};})(goToCallout);
const BUCKETS=['not_model_input','redundant','build_applied','build_relevant_unsupported','unclassified',
 'legacy_unclassified','stale','compile_blocked','invalid_duplicate'];
function cov(lists){const out={};for(const name of BUCKETS)out[name]=(lists&&lists[name])||[];
 const counts={};for(const name of BUCKETS)counts[name]=out[name].length;
 const blocking=['unclassified','legacy_unclassified','stale','compile_blocked','invalid_duplicate','build_relevant_unsupported'];
 return {...out,counts,total:BUCKETS.reduce((n,name)=>n+out[name].length,0),
  coverage_complete:blocking.every(name=>!counts[name])};}
function fx(ids){return {token:'tok',revision:1,effective_callouts:ids.map(id=>({id,ignored:false,unbindable:false,disposition:null})),callouts:[],
 coverage:cov({unclassified:ids}),decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p1'},
 options:{profiles:[{id:'p1',kind:'circle',points:[]}],circles:[],measurements:[]},questions:[],proposals:[],can_undo:false};}
function reset(ids){state=fx(ids);el('callout-show-ignored').checked=false;selectedCallout=null;gotoCalls.length=0;}
function reply(mutate,covLists){const post=JSON.parse(JSON.stringify(state));post.revision+=1;mutate(post);post.coverage=cov(covLists);return post;}
function mark(id,patch){return st=>{st.effective_callouts=st.effective_callouts.map(row=>row.id===id?{...row,...patch}:row);};}
const results={};
(async()=>{
 // §20: desteklenmeyen satır çözülmüş DEĞİL ve oto-ilerleme KURULMAZ.
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>reply(mark('k2',{disposition:'build_relevant_unsupported',unbindable:true}),
  {unclassified:['k1','k3'],build_relevant_unsupported:['k2']});
 await command('set_disposition',{callout_id:'k2',disposition:'build_relevant_unsupported',disposition_reason:'hedefi yok'});
 results.unsupported={selected:selectedCallout,goto:gotoCalls.slice(),resolved:rowResolved('k2'),
  unresolved:unresolvedRows().map(row=>row.id)};
 // §17: not_model_input çözer ve sıradaki açık alana ilerler.
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>reply(mark('k2',{disposition:'not_model_input',ignored:true}),{not_model_input:['k2'],unclassified:['k1','k3']});
 await command('set_disposition',{callout_id:'k2',disposition:'not_model_input'});
 results.notModelInput={selected:selectedCallout,goto:gotoCalls.slice(),resolved:rowResolved('k2')};
 // §17: geçerli redundant çözer.
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>reply(st=>{mark('k2',{disposition:'redundant',duplicate_of:'decision:calibration'})(st);st.decisions.calibration={first:[0,0],second:[1,0],value:50,unit:'mm'};},
  {redundant:['k2'],unclassified:['k1','k3']});
 await command('set_disposition',{callout_id:'k2',disposition:'redundant',duplicate_of:'decision:calibration'});
 results.redundantValid={selected:selectedCallout,goto:gotoCalls.slice(),resolved:rowResolved('k2')};
 // §14: dayanağı geçersiz redundant çözülmez.
 reset(['k1','k2','k3']);selectedCallout='k2';
 api=async()=>reply(mark('k2',{disposition:'redundant',duplicate_of:'k1'}),{invalid_duplicate:['k2'],unclassified:['k1','k3']});
 await command('set_disposition',{callout_id:'k2',disposition:'redundant',duplicate_of:'k1'});
 results.redundantInvalid={selected:selectedCallout,goto:gotoCalls.slice(),resolved:rowResolved('k2')};
 // §14: eski (legacy) yok sayma kaydı: kanıtsız — çözülmüş SAYILMAZ, gizlenmez, navigasyona girer.
 reset(['k1','k2','k3']);selectedCallout='k1';
 state.effective_callouts=state.effective_callouts.map(r=>r.id==='k2'?{...r,ignored:true}:r);
 state.coverage=cov({legacy_unclassified:['k2'],unclassified:['k1','k3']});
 render();
 results.legacy={selected:selectedCallout,resolved:rowResolved('k2'),
  visible:calloutList().map(row=>row.id),unresolved:unresolvedRows().map(row=>row.id)};
 el('callout-next').onclick();
 results.nextReachesLegacy={selected:selectedCallout};
 // §16: "Sonraki eksik" desteklenmeyen satırı ATLAMAZ.
 reset(['k1','k2','k3']);selectedCallout='k1';
 state.coverage=cov({unclassified:['k1'],build_relevant_unsupported:['k2'],not_model_input:['k3']});
 el('callout-next').onclick();
 results.nextReachesUnsupported={selected:selectedCallout};
 // §18/§19: kapsam özeti backend counts'undan; desteklenmeyen madde üretimi kapalı tutar.
 reset(['k1','k2','k3']);
 readiness={ready:false,questions:[{category:'unsupported_build_relevant',callout_id:'k2',action:'review_callout',
   reason:'build_relevant_unsupported',text:'«k2» gerçek ölçü/not olarak işaretli.'}],
  coverage:cov({not_model_input:['a1','a2'],build_applied:['b1'],build_relevant_unsupported:['k2'],unclassified:['k1','k3']})};
 renderReadiness();
 results.coverageSummary={text:el('coverage-summary').textContent,buildDisabled:el('build').disabled};
 // §18: kontrol listesi maddesi ilgili callout'u seçer.
 readinessGo(readiness.questions[0]);
 results.checklist={selected:selectedCallout};
 console.log('__RESULT__'+JSON.stringify(results));
})().catch(e=>{console.log('__ERROR__'+((e&&e.stack)||e));process.exit(1);});
"""

EXPECTED = {
    # Desteklenmeyen satır: çözülmüş değil, zıplanmaz, çözülmemişler arasında kalır.
    "unsupported": {"selected": "k2", "goto": [], "resolved": False, "unresolved": ["k1", "k2", "k3"]},
    # Not model input: çözer ve sonraki açık alana ilerler.
    "notModelInput": {"selected": "k3", "goto": ["k3"], "resolved": True},
    # Geçerli redundant: çözer ve ilerler.
    "redundantValid": {"selected": "k3", "goto": ["k3"], "resolved": True},
    # Geçersiz dayanak: çözülmez, zıplanmaz.
    "redundantInvalid": {"selected": "k2", "goto": [], "resolved": False},
    # Eski kayıt: kanıtsız, çözülmez, listede kalır ve navigasyona girer.
    "legacy": {"selected": "k1", "resolved": False, "visible": ["k1", "k2", "k3"],
               "unresolved": ["k1", "k2", "k3"]},
    "nextReachesLegacy": {"selected": "k2"},
    # Navigasyon desteklenmeyen satıra uğrar.
    "nextReachesUnsupported": {"selected": "k2"},
    # Kapsam özeti backend'den; üretim kapalı.
    "coverageSummary": {"buildDisabled": True},
    # Checklist maddesi ilgili callout'u seçer.
    "checklist": {"selected": "k2"},
}


def _assembled() -> str:
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    lines = script.splitlines()
    assert lines[0].startswith("import "), "guided.js'in ilk satırı preview import'u olmalı"
    return HEAD.replace("// __SCRIPT__", "\n".join(lines[1:])) + TAIL


def test_the_ui_resolves_rows_from_the_backend_coverage_bucket(tmp_path):
    """PLAN-25 §14/§15/§17: çözülmüşlük backend kapsamından; sekiz davranış senaryosu gerçek betikte."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok: guided.js davranış regresyonu bu makinede çalıştırılamıyor")
    source = tmp_path / "disposition_ui_driver.js"
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
        observed = results[scenario]
        for key, value in want.items():
            assert observed.get(key) == value, (scenario, key, observed.get(key), value)
    # §19: özet backend sayılarını insan dilinde taşır — teknik kova adı görünmez.
    summary = results["coverageSummary"]["text"]
    assert "2 modele ait değil" in summary, summary
    assert "1 modele uygulandı" in summary, summary
    assert "1 desteklenmiyor" in summary, summary
    assert "2 kontrol bekliyor" in summary, summary
    assert "not_model_input" not in summary and "build_applied" not in summary, summary


# --- servis edilen dosyaların sözleşmesi (PLAN-25 §9–§13, §101 adım 3-5) -------------------------

def test_the_three_dispositions_are_named_in_the_served_ui():
    """§9: üç claim kullanıcı copy'siyle var; eski belirsiz “Modele uygulanmayacak” kalkar."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    blob = html + script
    for wording in ("Bu bir ölçü/not değil", "Zaten başka bir bilgiyle temsil ediliyor",
                    "Gerçek ölçü/not ama şu an modele uygulanamıyor"):
        assert wording in blob, wording
    assert "Modele uygulanmayacak" not in blob, "eski belirsiz copy kalkmalı (PLAN-25 §9)"


def test_the_legacy_set_unbindable_command_is_no_longer_called_from_the_ui():
    """§10: arayüz doğrudan set_disposition kullanır; legacy komut yalnız backend uyumluluğunda kalır."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "command('set_unbindable'" not in script, "UI artık legacy komutu çağırmaz"
    assert "unbindable:!row.unbindable" not in script
    assert "disposition:'build_relevant_unsupported'" in script
    assert "disposition:'redundant'" in script
    assert "disposition:'not_model_input'" in script or "set_ignored" in script


def test_unsupported_needs_a_reason_and_redundant_needs_a_citation_in_the_ui():
    """§11/§12/§13: gerekçe alanı ve dayanak seçimi UI'da; frontend varsayılan gerekçe uydurmaz."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    for element in ("unsupported-box", "unsupported-reason", "unsupported-save",
                    "redundant-box", "redundant-reference", "redundant-save", "coverage-summary"):
        assert f'id="{element}"' in html, element
    assert "command('set_disposition'" in script
    assert "disposition_reason" in script
    # fake/boş gerekçe yazılmaz: kaydet yolu gerekçeyi kullanıcıdan ister
    assert "Neden uygulanamıyor?" in script or "Neden uygulanamıyor?" in html
    assert "Dayanak seçin" in html or "Dayanak seçin" in script


def test_auto_advance_never_follows_a_blocking_disposition():
    """§17: oto-ilerleme listesi çözen komutlardan oluşur; karar ayrıca rowResolved kapısından geçer."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "['transcribe','set_ignored','set_disposition'].includes(action)" in script
    assert "['transcribe','set_ignored','set_unbindable']" not in script
    assert "if(!rowResolved(previousId))return;" in script


def test_row_resolution_reads_the_public_coverage_payload():
    """§15: tarayıcı kendi ikinci kapsam motorunu kurmaz — kova sunucudan gelir."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "state.coverage" in script
    assert "row.ignored||row.unbindable)return true" not in script, \
        "eski çözülmüşlük kuralı kalkmalı (PLAN-25 §14)"
