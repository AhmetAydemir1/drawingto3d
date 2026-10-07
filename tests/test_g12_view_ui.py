"""G12.3 — görünüş UI sözleşmesi (PLAN-25 §51/§52): gerçek betik, saplama DOM ile.

Adaylar sunucunun `view_candidates` yükünden çizilir (etiketler de sunucudan gelir; makine bir
sınıflandırma iddia etmez). Rol seçimi `/api/guided/view` komutudur ve istemci `geometry_version`
UYDURMAZ. Ana görünüş onaylandığında kontur/daire listeleri o görünüşe daralır; "Tüm geometrileri
göster" hata ayıklama kaçışıdır ve seçili öğe hiçbir zaman menüden kaybolmaz.

Mock-up değil, servis edilen `guided.js` koşar; aynı saplama DOM G12.1b sürücüsünden gelir.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import test_guided_disposition_ui as ui_helpers
from drawingto3d.app import ROOT

TAIL = """
// ---- deterministik sürücü ----
renderTarget=function(){};
loadReadiness=function(){};loadProposals=function(){};
const results={};
const calls=[];
function viewState(patch){return {token:'tok',revision:1,effective_callouts:[],callouts:[],coverage:null,
 decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p1'},questions:[],proposals:[],can_undo:false,
 view_candidates:[{id:'view-0',kind:'isometric',used_for_solid:false,label:'İzometrik adayı',bbox:{x:0,y:0,w:60,h:60}},
  {id:'view-1',kind:'front',used_for_solid:true,label:'Görünüş 1',bbox:{x:0,y:0,w:100,h:100}},
  {id:'view-2',kind:'front',used_for_solid:true,label:'Görünüş 2',bbox:{x:100,y:0,w:100,h:100}},
  {id:'view-3',kind:'section',used_for_solid:true,label:'Kesit adayı',bbox:{x:0,y:100,w:100,h:50}}],
 view_roles:{primary:'Ana görünüş',plan:'Üst görünüş',side:'Yan görünüş',section:'Kesit',
  isometric_ignore:'İzometrik (üretim kaynağı değil)',unused:'Kullanılmıyor'},
 drawing_views:[],
 options:{profiles:[{id:'p1',kind:'wire',view_id:'view-1',points:[[10,10],[20,10],[20,20],[10,20]]},
   {id:'p2',kind:'wire',view_id:'view-2',points:[[110,10],[120,10],[120,20],[110,20]]},
   {id:'p9',kind:'wire',view_id:null,points:[[500,500],[510,500],[510,510],[500,510]]}],
  circles:[{id:'c1',center:[50,50],radius:5,view_id:'view-1'},{id:'c2',center:[150,50],radius:5,view_id:'view-2'}],
  measurements:[]},...(patch||{})};}
function rows(){return el('view-choices').children.map(line=>({label:line.children[0].textContent,
 select:line.children[1]}));}
function optionTexts(select){return select.children.map(opt=>opt.textContent);}
(async()=>{
 // §51: adaylar etiketleriyle ve rol menüsüyle çizilir; seçim yokken de görünür.
 state=viewState();render();
 results.panels={labels:rows().map(row=>row.label),
  roleOptions:optionTexts(rows()[0].select),
  chosen:rows().map(row=>row.select.value),
  stateText:el('view-state').textContent,
  debugCopy:el('show-all-geometry')?true:false};
 // §52: ana görünüş onaylıyken kontur/daire listeleri o görünüşe daralır; seçili öğe kaybolmaz.
 state=viewState({drawing_views:[{view_id:'view-1',role:'primary',geometry_version:4}],
   decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p1'}});render();
 const profileMenu=el('profile');
 results.scoped={profiles:profileMenu.children.map(opt=>opt.value),
   circles:el('circle')?el('circle').children.map(opt=>opt.value):null,
   chosenRole:rows()[1].select.value,
   stateText:el('view-state').textContent};
 // seçili kontur kapsam dışındaysa menüde kalır (karar görünür olmalı).
 state=viewState({drawing_views:[{view_id:'view-1',role:'primary',geometry_version:4}],
   decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p2'}});render();
 results.keptSelection={profiles:el('profile').children.map(opt=>opt.value)};
 // §52: hata ayıklama kaçışı tüm listeyi geri getirir (kullanıcı kendi seçimidir).
 const box=el('show-all-geometry');box.checked=true;box.onchange();
 results.debugAll={profiles:el('profile').children.map(opt=>opt.value)};
 // §47/§51: rol kaydı sunucu komutudur; gövde yalnız {token,revision,view_id,role} taşır.
 api=async(path,data)=>{calls.push([path,data]);
  return viewState({drawing_views:data.role?[{view_id:data.view_id,role:data.role,geometry_version:4}]
                                        :(state.drawing_views||[])});};
 const iso=rows()[0].select;iso.value='isometric_ignore';await iso.onchange();
 results.command={path:calls[0][0],body:calls[0][1]};
 const again=rows()[0].select;again.value='';await again.onchange();
 results.clear={path:calls[1][0],body:calls[1][1]};
 results.statusText=el('status').textContent;
 console.log('__RESULT__'+JSON.stringify(results));
})().catch(error=>{console.log('__ERROR__'+(error&&error.stack||error));});
"""

EXPECTED = {
    "panels": {
        "labels": ["İzometrik adayı", "Görünüş 1", "Görünüş 2", "Kesit adayı"],
        "chosen": ["", "", "", ""],
        "debugCopy": True,
    },
    "scoped": {
        "profiles": ["", "p1"],
        "circles": ["", "c1"],
        "chosenRole": "primary",
    },
    "keptSelection": {"profiles": ["", "p1", "p2"]},
    "debugAll": {"profiles": ["", "p1", "p2", "p9"]},
    "command": {"path": "/api/guided/view",
                "body": {"token": "tok", "revision": 1, "view_id": "view-0", "role": "isometric_ignore"}},
    "clear": {"path": "/api/guided/view",
              "body": {"token": "tok", "revision": 1, "view_id": "view-0", "role": None}},
}


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node yok")
    return node


def _run_driver(tmp_path):
    source = tmp_path / "driver.js"
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    lines = script.splitlines()
    assert lines[0].startswith("import "), "guided.js'in ilk satırı preview import'u olmalı"
    # `showStl` stub'ı HEAD'de tanımlı; import satırı driver'da çalışmaz (G12.1b sürücüsüyle aynı yol).
    assembled = ui_helpers.HEAD.replace("// __SCRIPT__", "\n".join(lines[1:])) + TAIL
    source.write_text(assembled, encoding="utf-8")
    proc = subprocess.run([_node(), str(source)], capture_output=True, text=True, timeout=120)
    stdout = proc.stdout
    assert "__ERROR__" not in stdout, stdout
    assert proc.returncode == 0, (proc.returncode, stdout, proc.stderr)
    assert "__RESULT__" in stdout, (stdout, proc.stderr)
    return json.loads(stdout.split("__RESULT__", 1)[1].splitlines()[0])


def test_the_view_panel_contract(tmp_path):
    results = _run_driver(tmp_path)
    for scenario, want in EXPECTED.items():
        observed = results.get(scenario) or {}
        for key, value in want.items():
            assert observed.get(key) == value, (scenario, key, observed.get(key), value)
    # §51: rol menüsü sunucunun kendi sözlüğüdür; "kullanılmıyor" da bir rol olarak görünür.
    assert "Ana görünüş" in results["panels"]["roleOptions"]
    assert "İzometrik (üretim kaynağı değil)" in results["panels"]["roleOptions"]


def test_the_served_panel_names_the_views_and_the_debug_escape():
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    for element in ("view-panel", "view-choices", "view-state", "show-all-geometry"):
        assert f'id="{element}"' in html, element
    assert "Tüm geometrileri göster" in html or "Tüm geometrileri göster" in script
    assert "Görünüş" in html or "Görünüş" in script
    # İstemci sürümü uydurmaz (PLAN-25 §47): komut yalnız kimlik ve rolle gider.
    assert "'/api/guided/view'" in script
    assert "geometry_version" not in script.split("chooseViewRole", 1)[1].split("function", 1)[0]
