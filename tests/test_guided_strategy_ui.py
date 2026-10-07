"""G12.2 — oluşturma biçimi UI sözleşmesi (PLAN-25 §42): gerçek betik, saplama DOM ile.

Paneller sunucunun `build_strategy` yükünü çizer: seçenekler kullanıcı dilinde, “bu sürümde yok”
olanlar görünür ama seçilemez, kaydetme yolu `/api/guided/strategy` komutudur — istemci
`strategy_key`/`geometry_version` UYDURMAZ (onları sunucu sabitler, §36).

Mock-up değil, servis edilen `guided.js` koşar; aynı saplama DOM G12.1b sürücüsünden gelir.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import test_guided_disposition_ui as ui_helpers
from drawingto3d import callout_readiness
from drawingto3d.app import ROOT
from drawingto3d.build_strategy import STRATEGY_LABEL

TAIL = """
// ---- deterministik sürücü ----
renderTarget=function(){};
// `renderStrategy` seçenekleri DOM'a koyar; tıklanan yol için işaretli radyoyu bulacak sorgu gerekir.
document.querySelector=sel=>{if(sel!=='input[name="strategy"]:checked')return null;
 const found=[];(function walk(node){if(!node)return;for(const child of (node.children||[])){walk(child);
  if(child.type==='radio'&&child.name==='strategy'&&child.checked)found.push(child);}})(el('strategy-choices'));
 return found[0]||null;};
const proposals=[{kind:'extrude_profile',label:'Sabit kalınlıklı profili uzat',confidence:'high',
  status:'candidate',reasons:['seçilen kontur kapalı'],evidence:[{kind:'profile_closure',detail:'seçilen kontur kapalı'}]},
 {kind:'revolve_profile',label:'Bir kesiti eksen etrafında döndür',confidence:'none',
  status:'capability_pending',reasons:['eksen/kesit geometrisi bu sürümde kurulmuyor (G12.6)'],evidence:[]},
 {kind:'multi_view_composite',label:'Birden fazla görünüşü birlikte kullan',confidence:'none',
  status:'capability_pending',reasons:['görünüş grafiği G12.7'],evidence:[]}];
const labels={extrude_profile:'Sabit kalınlıklı profili uzat',revolve_profile:'Bir kesiti eksen etrafında döndür',
 multi_view_composite:'Birden fazla görünüşü birlikte kullan',unsupported:'Bu sürümde desteklenmiyor'};
function strategyState(){return {token:'tok',revision:1,effective_callouts:[],callouts:[],coverage:null,
 decisions:{transcriptions:[],holes:[],bindings:[],profile_id:'p1'},options:{profiles:[],circles:[],measurements:[]},
 questions:[],proposals:[],can_undo:false,build_strategy:arguments[0]};}
const results={};
const calls=[];
(async()=>{
 // §42: seçenekler sunucudan gelir — dördü de görünür, henüz seçim yok.
 state=strategyState({state:'missing',decision:null,labels,proposals});
 render();
 // Her radyo seçeneği bir <label> içinde: [input, span(+küçük not)]. Etiket metni span'dadır.
 const radios=()=>el('strategy-choices').children.map(label=>({input:label.children[0],span:label.children[1]}));
 const field=key=>radios().map(row=>key(row));
 results.options={labels:radios().map(row=>row.span.textContent),values:radios().map(row=>row.input.value),
  disabled:radios().map(row=>row.input.disabled),checked:radios().map(row=>row.input.checked),
  notes:radios().map(row=>(row.span.children[0]||{}).textContent||''),
  stateText:el('strategy-state').textContent};
 // §42: capability-pending seçenek seçilemez; seçim yoksa kaydetme çağrı YAPMAZ.
 el('strategy-save').onclick();
 results.noChoice={calls:calls.length,status:el('status').textContent};
 // §36/§42: kaydetme yolu sunucu komutudur; anahtar/sürüm istemciden GİTMEZ.
 api=async(path,data)=>{calls.push([path,data]);return strategyState({state:'current',decision:{kind:data.kind,
   strategy_key:'sunucunun',geometry_version:1},labels,proposals});};
 const extrude=radios().find(row=>row.input.value==='extrude_profile').input;extrude.checked=true;
 el('strategy-save').onclick();
 await new Promise(resolve=>setTimeout(resolve,10));
 results.save={calls,status:el('status').textContent,stateText:el('strategy-state').textContent};
 // §42: seçili karar panelde görünür.
 state=strategyState({state:'current',decision:{kind:'revolve_profile',strategy_key:'sunucunun',geometry_version:1},
  labels,proposals});render();
 results.current={checked:radios().map(row=>row.input.checked),stateText:el('strategy-state').textContent};
 console.log('__RESULT__'+JSON.stringify(results));
})().catch(e=>{console.log('__ERROR__'+((e&&e.stack)||e));process.exit(1);});
"""


def _assembled() -> str:
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    lines = script.splitlines()
    assert lines[0].startswith("import "), "guided.js'in ilk satırı preview import'u olmalı"
    head = ui_helpers.HEAD.replace(
        "function makeEl(id){",
        "function makeEl(id){")  # saplama DOM aynen paylaşılır
    return head.replace("// __SCRIPT__", "\n".join(lines[1:])) + TAIL


def test_the_strategy_panel_renders_the_servers_choices(tmp_path):
    """PLAN-25 §42: dört seçenek sırayla, pending olanlar kapalı, kaydetme sunucu komutuyla."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok: guided.js davranış regresyonu bu makinede çalıştırılamıyor")
    source = tmp_path / "strategy_ui_driver.js"
    source.write_text(_assembled(), encoding="utf-8")
    proc = subprocess.run([node, str(source)], capture_output=True, text=True, timeout=120)
    assert "__ERROR__" not in proc.stdout, proc.stdout
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    results = json.loads(proc.stdout.split("__RESULT__", 1)[1].splitlines()[0])
    # §42: dört kullanıcı cümlesi, tam plan sırasıyla ve sunucudan gelen metinlerle.
    assert results["options"]["labels"] == ["Sabit kalınlıklı profili uzat", "Bir kesiti eksen etrafında döndür",
                                            "Birden fazla görünüşü birlikte kullan", "Bu sürümde desteklenmiyor"]
    assert results["options"]["values"] == ["extrude_profile", "revolve_profile", "multi_view_composite",
                                            "unsupported"]
    # capability-pending seçenekler görünür ama seçilemez (§35/§42); hiçbiri önceden işaretli değil.
    assert results["options"]["disabled"] == [False, True, True, False]
    assert results["options"]["checked"] == [False, False, False, False]
    assert "Henüz seçilmedi" in results["options"]["stateText"]
    # Seçim yokken kaydetmek çağrı üretmez, kullanıcıya söylenir.
    assert results["noChoice"]["calls"] == 0
    assert "önce bir oluşturma biçimi seçin" in results["noChoice"]["status"].lower(), results["noChoice"]
    # Kaydetme: /api/guided/strategy + yalnız `kind` — istemci anahtar/sürüm uydurmaz (§36).
    path, data = results["save"]["calls"][0]
    assert path == "/api/guided/strategy"
    assert data["kind"] == "extrude_profile" and data["revision"] == 1
    assert "strategy_key" not in data and "geometry_version" not in data, data
    # §42: seçili karar panelde görünür.
    assert results["current"]["checked"] == [False, True, False, False]
    assert results["current"]["stateText"].startswith("Seçili: Bir kesiti eksen etrafında döndür")


# --- backend: kontrol listesi kategorileri (PLAN-25 §41) -----------------------------------------

PLATE_SHEET = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _categories(record):
    from drawingto3d import callout_readiness

    return [row["category"] for row in callout_readiness.build_readiness(record)["questions"]]


def test_readiness_carries_the_strategy_categories(tmp_path):
    """§41: strateji maddesi readiness'te kendi kategorisiyle durur; build ile aynı cümleyi söyler."""
    import test_guided_geometry_state as geometry_helpers
    from drawingto3d.guided import GuidedStore

    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE_SHEET.read_bytes())
    token = opened["token"]
    _wire, _circles, decisions = geometry_helpers.decisions_for(opened["options"])
    store.save(token, opened["revision"], decisions)
    geometry_helpers._declare_callouts_out_of_scope(store, token)

    # Strateji yok: madde "seç" der.
    record = store.load(token)
    assert "missing_build_strategy" in _categories(record)
    readiness = callout_readiness.build_readiness(record)
    text = " ".join(row["text"] for row in readiness["questions"])
    assert "oluşturma biçimini seçin" in text, text
    assert readiness["ready"] is False

    # Onaylandı: madde kalkar.
    store.set_strategy(token, store.load(token)["revision"], {"kind": "extrude_profile"})
    record = store.load(token)
    assert "missing_build_strategy" not in _categories(record)

    # Profil değişti: karar güncelliğini yitirir, madde "yeniden onayla" olur.
    other = next(row["id"] for row in record["options"]["profiles"] if row["id"] != decisions["profile_id"])
    payload = dict(record["decisions"])
    payload["profile_id"] = other
    store.save(token, record["revision"], payload)
    record = store.load(token)
    assert "stale_build_strategy" in _categories(record)
    text = " ".join(row["text"] for row in callout_readiness.build_readiness(record)["questions"])
    assert "yeniden onaylayın" in text, text

    # "Bu sürümde desteklenmiyor": kendi kategorisi, kendi cümlesi.
    store.set_strategy(token, record["revision"], {"kind": "unsupported"})
    record = store.load(token)
    assert "unsupported_build_strategy" in _categories(record)
    text = " ".join(row["text"] for row in callout_readiness.build_readiness(record)["questions"])
    assert "bu sürümde uygulanamıyor" in text, text


def test_the_checklist_task_for_the_strategy_is_named_in_the_ui():
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    for category in ("missing_build_strategy", "stale_build_strategy", "unsupported_build_strategy"):
        assert category in script, category
    assert "choose_build_strategy" in script
    assert "Parçanın ana oluşturma biçimini seç" in script


# --- servis edilen dosyaların sözleşmesi (§42) --------------------------------------------------

def test_the_served_panel_names_the_choice_and_the_limits():
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    for element in ("strategy-panel", "strategy-choices", "strategy-state", "strategy-save",
                    "strategy-evidence"):
        assert f'id="{element}"' in html, element
    assert "Parçanın ana oluşturma biçimi" in html
    assert "Bu sürüm yalnız profil uzatma uygular" in html
    assert "/api/guided/strategy" in script
    assert "strategy_key" not in script, "istemci anahtarı taşımaz; anahtarı sunucu sabitler (§36)"
    # Kaydetme yükü yalnız türü taşır: sunucu anahtarı ve geometri sürümünü kendisi sabitler.
    assert "{token:state.token,revision:state.revision,kind}" in script
    assert "(bu sürümde yok)" in script and "capability_pending" in script


def test_the_four_choice_labels_are_one_copy_of_the_plans_wording():
    """§42'nin dört cümlesi backend'de tek yerde durur; panel onları sunucudan okur."""
    assert STRATEGY_LABEL == {
        "extrude_profile": "Sabit kalınlıklı profili uzat",
        "revolve_profile": "Bir kesiti eksen etrafında döndür",
        "multi_view_composite": "Birden fazla görünüşü birlikte kullan",
        "unsupported": "Bu sürümde desteklenmiyor",
    }
