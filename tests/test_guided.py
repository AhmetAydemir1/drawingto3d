"""User decisions must survive edits/restarts and produce the measured solid through GeneralPlan."""
import hashlib
import json
import math
from pathlib import Path

import pytest
from drawingto3d import guided
from drawingto3d.guided import Decisions, GuidedStore, drawing_options, make_plan, _atomic
from drawingto3d.observe import Observations, observe


SHEET_10 = Path("examples/pdf with steps/10/Exercise 12.pdf")
PLATE_SHEET = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def test_title_block_leaves_the_contour_and_number_menus():
    """`10/Exercise 12`: the sheet's biggest closed loop is its own title-block box.

    Before this change the flow offered that box as the part's outer contour (a `bound` proposal of
    457.17 x 139.78 mm) and put its text into the number menu (part number 2103017, scale `1: 5`).
    """
    options = drawing_options(observe(SHEET_10))
    wires = [p for p in options["profiles"] if p["kind"] == "wire"]
    widest = max((max(q[0] for q in p["points"]) - min(q[0] for q in p["points"]) for p in wires), default=0)
    # The title-block box is 708.6 px wide and must not be offered; what may remain are the sheet's own
    # views — measured after the arc handling was fixed, the widest offered contour on this sheet is the
    # 488 px part view (before, contours like it were skipped by an arc-direction gate that also caught
    # this box's neighbours, and the widest leftover was 96 px).
    assert widest < 620
    texts = [m["text"].strip() for m in options["measurements"]]
    assert "2103017" not in texts and "1: 5" not in texts
    assert any("antet/tablo" in note for note in options["notes"])


def test_border_held_text_is_still_offered():
    """The exclusion is about an *inner* annotation box: a sheet border holds the whole drawing."""
    options = drawing_options(observe(PLATE_SHEET))
    texts = [m["text"].strip() for m in options["measurements"]]
    assert len(options["profiles"]) == 11 and len(options["measurements"]) == 20
    assert "2026" in texts


def test_flow_names_the_class_and_withholds_plate_decisions(tmp_path):
    """`10/Exercise 12` is a flanged elbow: the flow reads the class before it offers anything.

    Before the class existed the flow offered 29 plate-shaped decisions for this sheet — the title-block
    box as the outer contour and 28 circles as through-holes — and the build then died on a geometry
    audit. Now nothing plate-shaped is offered: the outer size is a circle of the sheet's own flange face,
    and every hole belongs to one of that face's own printed diameters.
    """
    opened = GuidedStore(tmp_path / "store").create(SHEET_10.read_bytes())
    assert opened["archetype"]["class"] == "rotational-flanged"
    assert opened["archetype"]["evidence"]["circles"] == 5
    assert any(line["action"] == "class" for line in opened["log"])
    by_field = {item["field"]: item for item in opened["proposals"]}
    contour = next(p for p in opened["options"]["profiles"] if p["id"] == by_field["profile_id"]["value"])
    assert contour["kind"] == "circle"                    # not the 4-line title-block rectangle
    holes = [item for field, item in by_field.items() if field.startswith("hole:")]
    assert {item["value"]["diameter"] for item in holes} == {18.0, 76.0}


def test_flange_sheet_gets_its_own_decisions_and_builds(tmp_path):
    """`10/Exercise 12` is a flanged elbow: the flow decides its flange from the sheet's own numbers.

    Before this, the flow offered the title-block box as the contour and 28 holes through a plate that died
    in the geometry audit. Now: the face circle `circle_g50` is the outer size, the printed Ø20.00 (three
    of its rows) is the thickness, the stack's smallest circle (Ø76) is the bore, six Ø18 circles standing
    on the face are its bolt holes, and the calibration comes from the face's own printed Ø270 over 425.2
    px = 1.5747 px/mm instead of a 10 mm row resolved 3 % short. One accept leaves no question open.
    """
    store = GuidedStore(tmp_path / "store")
    opened = store.create(SHEET_10.read_bytes())
    fields = {item["field"]: item for item in opened["proposals"]}
    assert fields["profile_id"]["value"] == "circle_g50"
    assert fields["thickness"]["value"] == 20.0
    assert fields["hole:g60"]["value"]["diameter"] == 76.0                     # the bore
    assert fields["calibration"]["value"]["value"] == 270.0
    assert abs(fields["calibration"]["evidence"]["px_per_mm"] - 1.5747) < 0.001
    bolts = [item for field, item in fields.items() if field.startswith("hole:g4")]
    assert len(bolts) == 6 and {item["value"]["diameter"] for item in bolts} == {18.0}
    state = store.accept(opened["token"], opened["revision"])
    assert state["questions"] == []
    # The plate's own sheet keeps the calibration row it had: a row that agrees with the fitted scale.
    plate = store.create(PLATE_SHEET.read_bytes())
    row = next(item for item in plate["proposals"] if item["field"] == "calibration")
    assert row["value"]["value"] == 100.0


def test_flange_sheet_builds_the_sheets_printed_flange(tmp_path):
    """The build of `10/Exercise 12` is the sheet's own flange: Ø270, 20 thick, Ø76 bore, six Ø18 holes.

    The reference `Exercise 12.STEP` carries the same flange (r135 outer, r38 bore, r9 holes, 20 mm thick);
    the elbow body and the second flange are not built yet, so this asserts the flange alone — and it is
    the first time a rotational sheet of this project reaches a solid at all.
    """
    store = GuidedStore(tmp_path / "store")
    opened = store.create(SHEET_10.read_bytes())
    state = store.accept(opened["token"], opened["revision"])
    state = store.build(opened["token"], state["revision"])
    build = state.get("build") or store.load(opened["token"])["build"]
    assert build["status"] == "complete", build.get("error")
    geometry = json.loads((Path(build["folder"]) / "geometry.json").read_text())
    assert geometry["valid"] and geometry["solids"] == 1
    assert [round(value) for value in geometry["size"]] == [270, 270, 20]
    radii = sorted({round(cylinder[0]) for cylinder in geometry["cylinders"]})
    assert radii == [9, 38, 135]          # the bolt holes, the bore, the outer face


def test_plate_still_gets_its_nine_decisions(tmp_path):
    opened = GuidedStore(tmp_path / "store").create(PLATE_SHEET.read_bytes())
    assert opened["archetype"]["class"] == "flat-part"
    assert len(opened["proposals"]) == 9


@pytest.fixture
def record(tmp_path):
    primitives=[]
    points=[[20,20],[120,20],[120,80],[20,80]]
    for i,p in enumerate(points):
        primitives.append(dict(id=f'g{i}',path_id=f'p{i}',kind='line',start=p,end=points[(i+1)%4]))
    for i,c in enumerate([[45,45],[90,50]]):
        primitives.append(dict(id=f'c{i}',path_id=f'cp{i}',kind='circle',centre=c,radius=6))
    # PLAN 8.6: a real sheet comes with its own border, and the flow asks about the view only where the
    # frame is missing, tilted or rotated. A synthetic sheet without one is the unrealistic case that
    # makes every build refuse for a reason no real drawing has, so the border is drawn here too.
    border=[[10,10],[290,10],[290,190],[10,190]]
    for i,p_ in enumerate(border):
        primitives.append(dict(id=f'g{4+i}',path_id=f'b{i}',kind='line',start=p_,end=border[(i+1)%4]))
    source=tmp_path/'source.pdf';source.write_bytes(b'fixture-source-hash')
    obs=Observations(source={'ref':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},
                     frame={'width':300,'height':200},text_placement='as-is',primitives=primitives)
    options=drawing_options(obs)
    # The sheet border is a frame loop and is skipped, so the part is the only wire offered: name it by
    # that fact instead of by an index the frame now occupies (PLAN 8.6's border moved it to outline_1).
    wire=next(p_['id'] for p_ in options['profiles'] if p_['kind']=='wire')
    return {'version':1,'geometry_version':guided.GEOMETRY_VERSION,'token':'a'*32,'revision':0,'source':str(source),'source_sha256':obs.source.sha256,
            'options':options,'decisions':{'calibration':{'first':[20,20],'second':[120,20],'value':50,'unit':'mm'},
            'profile_id':wire,'thickness':10,'holes':[{'circle_id':'c0','kind':'through','diameter':6},
            {'circle_id':'c1','kind':'pocket','diameter':10,'depth':3}],'trace_acknowledged':True},'history':[],'build':None}


@pytest.fixture
def store(tmp_path,record):
    store=GuidedStore(tmp_path/'store');folder=store.folder(record['token']);folder.mkdir(parents=True)
    _atomic(folder/'session.json',record)
    return store


def test_decisions_build_independent_expected_geometry(store,record):
    result=store.build(record['token'],0)
    assert result['build_status']=='complete',result.get('error')
    path,_=store.artifact(record['token'],'part.step')
    facts=json.loads((path.parent/'geometry.json').read_text())
    assert facts['valid'] and facts['solids']==1
    assert facts['size']==pytest.approx([50,30,10],abs=1e-5)
    assert facts['volume']==pytest.approx(50*30*10-math.pi*3**2*10-math.pi*5**2*3,abs=1e-3)
    assert {tuple(round(v,4) for v in row) for row in facts['cylinders']}=={
        (3,12.5,17.5,0,10),(5,35,15,7,10)}
    plan=json.loads((path.parent/'plan.json').read_text())
    assert plan['parameters']['thickness']['source']=='user'
    assert plan['parameters']['edge_0_start_x']['source']=='assumed'
    assert 'part.step' in result['step']


def test_revision_conflict_and_undo_keep_history(store,record):
    changes=record['decisions']|{'thickness':12}
    after=store.save(record['token'],0,changes)
    assert after['revision']==1 and after['can_undo']
    with pytest.raises(ValueError,match='oturum değişti'):store.save(record['token'],0,changes)
    reopened=GuidedStore(store.root).public(store.load(record['token']))
    assert reopened['decisions']['thickness']==12
    undone=store.save(record['token'],1,undo=True)
    assert undone['revision']==2 and undone['decisions']['thickness']==10


def test_edit_invalidates_old_artifact(store,record):
    raw=store.load(record['token']);raw['build']={'revision':0,'status':'complete','folder':'old'}
    _atomic(store.folder(record['token'])/'session.json',raw)
    after=store.save(record['token'],0,record['decisions']|{'thickness':15})
    assert after['step'] is None
    with pytest.raises(ValueError,match='güncel STEP yok'):store.artifact(record['token'],'part.step')


def test_failed_build_preserves_decisions_and_reason(store,record,monkeypatch):
    def fail(*args):raise ValueError('fixture build failed')
    monkeypatch.setattr(guided,'build_general',fail)
    result=store.build(record['token'],0)
    assert result['build_status']=='failed' and result['step'] is None
    assert result['decisions']['thickness']==10 and result['error']=='fixture build failed'


def test_late_build_cannot_publish_over_newer_decision(store,record,monkeypatch):
    def change(*args):store.save(record['token'],0,record['decisions']|{'thickness':15})
    monkeypatch.setattr(guided,'build_general',change)
    result=store.build(record['token'],0)
    assert result['revision']==1 and result['step'] is None


@pytest.mark.parametrize('change',[
    {'profile_id':'elsewhere'}, {'calibration':{'first':[20,20],'second':[20,20],'value':50}},
    {'calibration':{'first':[-10,20],'second':[120,20],'value':50}}, {'thickness':float('nan')},
    {'holes':[{'circle_id':'c0','kind':'pocket','diameter':6,'depth':10}]},
    {'holes':[{'circle_id':'absent','kind':'through','diameter':6}]},
    {'holes':[{'circle_id':'c0','kind':'through','diameter':6,'depth':2}]},
])
def test_invalid_decisions_never_overwrite_saved_choices(store,record,change):
    original=(store.folder(record['token'])/'session.json').read_bytes()
    with pytest.raises(ValueError):store.save(record['token'],0,record['decisions']|change)
    assert (store.folder(record['token'])/'session.json').read_bytes()==original


def test_source_change_refuses_replay(store,record):
    """P01-b.4 (was "the load raises"): a changed source makes the old result *historical*.

    The session must stay readable — its decisions and evidence are the user's own work — while nothing is
    replayed from an output that belongs to a different drawing, and recovery stays possible (`recheck`).
    """
    Path(record['source']).write_bytes(b'different drawing')
    loaded=store.load(record['token'])                       # no exception
    assert loaded["geometry_stale"] and "kaynak çizim değişmiş" in loaded["geometry_stale"]["reason"]
    state=store.public(loaded)
    assert state["build_status"] is None and state["step"] is None
    assert state["geometry"]["stale"], state["geometry"]
    assert store.load(record['token'])["decisions"]==record["decisions"]      # evidence stays readable
    with pytest.raises(ValueError,match='tarihsel'):store.build(record['token'],0)
    with pytest.raises(ValueError,match='tarihsel'):store.artifact(record['token'],'part.step')


def test_incomplete_choices_do_not_compile(record):
    record['decisions']['calibration']=None
    with pytest.raises(ValueError,match='uzunluğunu'):make_plan(record)


def test_startup_marks_interrupted_build_without_losing_choices(store,record):
    record['build']={'revision':0,'status':'running','folder':'partial'}
    _atomic(store.folder(record['token'])/'session.json',record)
    reopened=GuidedStore(store.root);reopened.recover_interrupted()
    result=reopened.public(reopened.load(record['token']))
    assert result['build_status']=='interrupted' and result['step'] is None
    assert result['decisions']['thickness']==10 and result['error']


def test_http_revision_and_artifact_contract(store,record,monkeypatch):
    import threading,urllib.request,urllib.error
    from http.server import ThreadingHTTPServer
    from drawingto3d import app
    monkeypatch.setattr(app,'GUIDED',store)
    server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    def post(path,data):
        req=urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response:return json.load(response)
    try:
        changed=post('/api/guided/save',{'token':record['token'],'revision':0,'decisions':record['decisions']|{'thickness':12}})
        assert changed['revision']==1
        with urllib.request.urlopen(url+'/api/guided/'+record['token']) as response:assert json.load(response)['decisions']['thickness']==12
        with pytest.raises(urllib.error.HTTPError) as error:
            post('/api/guided/save',{'token':record['token'],'revision':0,'decisions':record['decisions']})
        assert error.value.code==400
        restored=post('/api/guided/undo',{'token':record['token'],'revision':1})
        assert restored['decisions']['thickness']==10
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url+'/guided-session/'+record['token']+'/part.step')
        assert error.value.code==404
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def plan_bbox(plan):
    """The solved contour's own extent in mm, read off the plan's edge vertex parameters.

    Parameter *names* follow the chain, so a solved square may start at another corner; the extent is what
    the acceptance talks about ("the body stays 100 mm", "a 50 x 40 rectangle").
    """
    import re as _re
    xs, ys = [], []
    for name, row in plan.parameters.items():
        match = _re.fullmatch(r"edge_\d+_(start|end)_([xy])", name)
        if match:
            (xs if match.group(2) == "x" else ys).append(float(row.value))
    return (max(xs) - min(xs), max(ys) - min(ys))


def binding_record(record, pairs):
    """The synthetic sheet with printed measurements the user bound to its own corners."""
    ends = {(20, 20): ("edge:0", 20, 20), (120, 20): ("edge:0", 120, 20),
            (120, 80): ("edge:1", 120, 80), (20, 80): ("edge:3", 20, 80)}
    def axis_direction(first, second):
        axis = "x" if abs(second[0] - first[0]) >= abs(second[1] - first[1]) else "y"
        delta = (second[0] - first[0]) if axis == "x" else (first[1] - second[1])
        return axis, (1 if delta >= 0 else -1)

    bindings = [{"value": value, "unit": "mm", "span_id": None, "axis": axis_direction(first, second)[0],
                 "direction": axis_direction(first, second)[1],
                 "first": {"kind": "vertex", "id": ends[first][0], "x": first[0], "y": first[1]},
                 "second": {"kind": "vertex", "id": ends[second][0], "x": second[0], "y": second[1]}}
                for value, first, second in pairs]
    return {**record["decisions"], "bindings": bindings}


def test_a_bound_measurement_moves_the_geometry_and_the_scale_stays_the_calibrations(store, record):
    """PLAN P04-a: the sheet's height is drawn 60 px, the calibration calls that 30 mm, the user binds 40 mm.

    The printed tie is honoured *by moving the geometry*, not by re-fitting the sheet: the part's own scale
    stays the one the user measured with two known points (2 px/mm here), so the height becomes the bound
    40 mm while the width stays the calibrated 50 mm. The fitted scale that disagrees with the drawing is
    still reported — as a diagnostic (`sketch["fit"]`), never as the scale the part is built at.
    """
    opened = store.save(record["token"], 0, binding_record(record, [(40.0, (20, 20), (20, 80))]))
    assert opened["sketch"]["source"] == "calibration"
    assert opened["sketch"]["px_per_mm"] == pytest.approx(2.0)
    assert opened["sketch"]["fit"]["source"] == "bindings"          # the diagnostic still says what it fits
    assert opened["sketch"]["fit"]["rows"][0]["value_mm"] == 40.0
    assert opened["questions"] == []
    built = store.build(record["token"], opened["revision"])
    assert built["build_status"] == "complete", built.get("error")
    step, _ = store.artifact(record["token"], "part.step")
    geometry = json.loads((step.parent / "geometry.json").read_text())
    size = geometry["size"]
    assert size[1] == pytest.approx(40.0, abs=0.01)          # the bound height, solved, not the scale
    assert size[0] == pytest.approx(50.0, abs=0.01)          # the width the calibration measured
    plan = json.loads(next(iter((step.parent).glob("plan.json"))).read_text())
    assert plan["parameters"]["binding_0"]["source"] == "user"
    assert plan["parameters"]["binding_0"]["value"] == 40.0
    assert "kalibrasyonundan" in " ".join(plan["assumptions"])


def test_supported_corner_ties_are_not_blocked_by_the_fitted_scale(store, record):
    """PLAN P04-a / F13: 40 mm over the 60 px edge and 50 mm over the 100 px one both hold in the core.

    They cannot both hold under *one* fitted scale — that is why the residual report must stay a report.
    The two ties are supported X/Y differences between valid corners, so the build runs and the solved
    rectangle is 50 x 40 mm. A binding that points at geometry the sheet does not have is still refused.
    """
    opened = store.save(record["token"], 0, binding_record(record, [(40.0, (20, 20), (20, 80)),
                                                                 (50.0, (20, 20), (120, 20))]))
    assert not opened["sketch"]["fit"]["consistent"] and len(opened["sketch"]["fit"]["conflicts"]) == 2
    assert not any("tek ölçekle tutarlı değil" in question for question in opened["questions"]), \
        opened["questions"]
    plan = make_plan({**record, "decisions": opened["decisions"]})
    width, height = plan_bbox(plan)
    assert width == pytest.approx(50.0, abs=1e-6) and height == pytest.approx(40.0, abs=1e-6)

    bad = {**record["decisions"], "bindings": [{"value": 40.0, "unit": "mm", "span_id": None,
                                                "axis": "y", "direction": -1,
                                                "first": {"kind": "vertex", "id": "edge:99", "x": 20, "y": 20},
                                                "second": {"kind": "vertex", "id": "edge:3", "x": 20, "y": 80}}]}
    saved = store.save(record["token"], opened["revision"], bad)      # PLAN §8.9: kept, never re-mapped
    assert any("yeniden bağlanmalı" in question for question in saved["questions"]), saved["questions"]
    with pytest.raises(ValueError):
        store.build(record["token"], saved["revision"])


def test_a_lone_centre_tie_does_not_shrink_the_body(store, record):
    """PLAN P04-a / F12: the 100 mm body (100 px at a 1 px/mm calibration) stays 100 mm.

    Only a centre-distance tie is added, and its printed value disagrees with the calibration. Before this
    slice the fit overruled the calibration and the whole body came out half size; the tie must instead move
    the two centres to the printed distance and leave the body's own scale alone.
    """
    calibration = dict(record["decisions"]["calibration"], value=100.0)     # 100 px = 100 mm -> 1 px/mm
    tie = {"id": "m0", "value": 20.0, "unit": "mm", "span_id": None, "axis": "x", "direction": 1,
           "first": {"kind": "centre", "id": "c0", "x": 45, "y": 45},
           "second": {"kind": "centre", "id": "c1", "x": 90, "y": 50}}
    opened = store.save(record["token"], 0, {**record["decisions"], "calibration": calibration,
                                             "bindings": [tie]})
    assert opened["sketch"]["source"] == "calibration"
    assert opened["sketch"]["px_per_mm"] == pytest.approx(1.0)
    assert opened["questions"] == []
    plan = make_plan({**record, "decisions": opened["decisions"]})
    width, height = plan_bbox(plan)
    assert width == pytest.approx(100.0, abs=1e-6) and height == pytest.approx(60.0, abs=1e-6)


def test_removing_the_profile_keeps_the_ties_and_asks_instead_of_failing(store, record):
    """A0.2: no contour chosen is a normal missing decision. A tie the user already made stays in the record,
    the flow asks for a contour and for re-binding, the build waits — the save path does not raise."""
    saved = store.save(record["token"], 0, binding_record(record, [(40.0, (20, 20), (20, 80))]))
    assert saved["questions"] == [], saved["questions"]

    without = {**saved["decisions"], "profile_id": None}
    after = store.save(record["token"], saved["revision"], without)
    assert after["decisions"]["bindings"] == saved["decisions"]["bindings"]
    assert any("dış konturu seçin" in question for question in after["questions"]), after["questions"]
    assert any("kontur seçilmemiş" in question for question in after["questions"]), after["questions"]

    reopened = store.load(record["token"])
    assert reopened["decisions"]["profile_id"] is None
    assert reopened["decisions"]["bindings"] == saved["decisions"]["bindings"]
    with pytest.raises(ValueError):
        store.build(record["token"], after["revision"])


PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _fake_complete_build(store, token, *, with_identity, file_bytes=b"old step"):
    """A session that already carries a finished output, the way a pre-P01 record could."""
    record = store.load(token)
    folder = store.folder(token) / "build-0-oldfolder"
    folder.mkdir(exist_ok=True)
    (folder / "part.step").write_bytes(file_bytes)
    record["build"] = {"revision": 0, "status": "complete", "folder": str(folder)}
    if with_identity:
        record["build"].update({"source_sha256": record["source_sha256"],
                                "geometry_version": record["geometry_version"]})
    _atomic(store.folder(token) / "session.json", record)
    return folder


def test_a_migrated_record_never_serves_its_old_step_as_current(tmp_path):
    """P01-b.2: even a *successful* migration demotes the old output — an output that belongs to the
    pre-migration geometry is not the drawing's current result. The file itself is kept (evidence)."""
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE.read_bytes())["token"]
    folder = _fake_complete_build(store, token, with_identity=False)
    path = store.folder(token) / "session.json"
    record = json.loads(path.read_text())
    record.pop("geometry_version", None)                     # a pre-P01 record, build and all
    path.write_text(json.dumps(record, ensure_ascii=False))

    state = store.public(store.load(token))                  # geometry is refreshed here
    assert state["geometry"]["stale"] is None, state["geometry"]
    assert state["build_status"] == "historical", state["build_status"]
    assert state["step"] is None and state["stl"] is None and state["plan"] is None
    assert state["geometry"]["historical"] == str(folder)
    assert (folder / "part.step").exists()                   # the old file is not deleted
    with pytest.raises(ValueError, match="güncel STEP yok"):
        store.artifact(token, "part.step")


def test_a_stale_record_keeps_its_evidence_and_recheck_recovers_it(tmp_path):
    """P01-b.3/5: stale means historical *and* recoverable — the old file stays, the decisions stay, and
    `recheck` restores a current output once the source is back."""
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE.read_bytes())["token"]
    folder = _fake_complete_build(store, token, with_identity=True)
    before_decisions = store.load(token)["decisions"]
    source = store.folder(token) / "source.pdf"
    good = source.read_bytes()

    # The real "source is not there" case: the file the session points at is gone. (A *v3* record is not
    # re-read from source at all, so a digest check is what can notice this; a forged digest is not a user
    # scenario and is covered by the pre-migration path in `test_an_unreadable_source_is_stale_not_a_crash`.)
    moved = source.with_name("source.moved")
    source.rename(moved)

    state = store.public(store.load(token))
    assert state["geometry"]["stale"] and "okunamadı" in state["geometry"]["stale"], state["geometry"]
    assert state["build_status"] == "historical"
    assert state["step"] is None
    assert state["decisions"] == before_decisions                    # the user's work is still there
    assert (folder / "part.step").exists()
    with pytest.raises(ValueError, match="tarihsel"):
        store.build(token, state["revision"])

    moved.rename(source)                                            # the user puts the file back
    assert source.read_bytes() == good
    state = store.recheck(token)
    assert state["geometry"]["stale"] is None, state["geometry"]
    assert state["build_status"] == "complete", state["build_status"]
    assert state["step"], state
    path_, _kind = store.artifact(token, "part.step")
    assert path_ == folder / "part.step"                              # the same, now-current output
