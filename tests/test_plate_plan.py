import json
from pathlib import Path

import numpy as np
import pytest

from drawingto3d.ingest import load_page
from drawingto3d.plate import Unsupported, _from_paths, propose_plate
from drawingto3d.plan import PARAMETERS, PlatePlan, build_plan, check_plan, edit_plan
from drawingto3d.reason import reason_drawing
from drawingto3d.schema import BBox, Page, Span

DRAWING = Path('examples/pdf with steps/Plate With A Pocket Drawing.PDF')


@pytest.fixture(scope='module')
def proposal():
    plan = propose_plate(load_page(DRAWING))
    assert plan is not None
    return plan


def test_actual_drawing_binds_dimensions_to_features(proposal):
    assert [getattr(proposal, p) for p in PARAMETERS] == [120, 80, 15, 10, 100, 60, 6.8, 50, 8]
    assert proposal.evidence['width'].kind == 'derived'
    assert proposal.evidence['pocket_depth'].span_ids == ['pdf-6']
    assert proposal.assumptions


def test_no_model_needed_and_geometry_matches_plan(tmp_path, monkeypatch, proposal):
    def forbidden(*args, **kwargs):
        raise AssertionError('the deterministic plan must not call a model')
    monkeypatch.setattr('drawingto3d.reason.OllamaVision', forbidden)
    monkeypatch.setattr('drawingto3d.reason._default_coder', forbidden)
    review = reason_drawing(DRAWING, tmp_path, prefer_plan=True)
    assert review.plate_plan == proposal and review.step_path is None
    built = reason_drawing(DRAWING, tmp_path, plate_plan=review.plate_plan)
    assert built.step_path and Path(built.step_path).is_file()
    assert not built.audit.accepted  # inferred dimensions remain a reviewable draft
    assert all(built.audit.checks.values())
    facts = json.loads((tmp_path / 'geometry.json').read_text())
    assert facts['volume'] == pytest.approx(124825.423, abs=0.01)
    assert len(facts['cylinders']) == 9
    # A wrong hole position preserves volume and bounding box; the feature audit must catch it.
    facts['cylinders'][0][1] += 2
    assert not check_plan(proposal, facts)['passed']


def test_plan_is_bound_to_source_file(tmp_path, proposal):
    other = tmp_path / 'drawing.pdf'
    other.write_bytes(b'not the original drawing')
    with pytest.raises(ValueError, match='özet'):
        build_plan(proposal, other, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('changes', [
    {'pocket_depth': 15}, {'thickness': float('nan')}, {'hole_diameter': 30},
    {'width': 110, 'hole_dx': 130}, {'pocket_diameter': 70}, {'width': float('inf')},
    {'hole_dx': True}, {'unexpected': 42},
])
def test_invalid_edits_do_not_reach_cad(proposal, changes):
    with pytest.raises((ValueError, TypeError)):
        edit_plan(proposal, changes)


def test_user_edits_have_their_own_provenance(proposal):
    changed = edit_plan(proposal, {'pocket_depth': 6})
    assert changed.pocket_depth == 6
    assert changed.evidence['pocket_depth'].kind == 'user'
    assert proposal.pocket_depth == 8
    assert PlatePlan.model_validate_json(changed.model_dump_json()) == changed


def test_derived_dimensions_follow_edited_inputs(proposal):
    fields = {p: getattr(proposal, p) for p in PARAMETERS}
    fields['hole_dx'] = 110
    changed = edit_plan(proposal, fields)
    assert changed.width == 130 and changed.corner_radius == 10
    assert changed.evidence['width'].kind == 'derived'


def test_explicit_override_is_not_replaced_by_a_derivation(proposal):
    changed = edit_plan(proposal, {'width': 150, 'hole_dx': 110})
    assert changed.width == 150 and changed.evidence['width'].kind == 'user'


def test_other_examples_are_not_silently_treated_as_plates():
    assert propose_plate(load_page('examples/pdf with steps/plastic enclosue.pdf')) is None
    assert propose_plate(load_page('examples/pdf with steps/Flange.PNG')) is None


def synthetic(tmp_path, width=160, height=100, margin=12, thickness=18, depth=5, scale=4, shift=(500, 600)):
    """Independent drawing geometry: no STEP and no expected evaluation dimensions as input."""
    hole_diameter, pocket_diameter = 7, 40
    x, y = shift
    left, right = x - width * scale / 2, x + width * scale / 2
    top, bottom = y - height * scale / 2, y + height * scale / 2
    r = margin * scale
    def arc(cx, cy, radius, a, b):
        angles = np.linspace(a, b, 80)
        return np.column_stack((cx + radius * np.cos(angles), cy + radius * np.sin(angles)))
    paths = [arc(cx, cy, r, a, a + np.pi / 2) for cx, cy, a in
             [(right-r, bottom-r, 0), (left+r, bottom-r, np.pi/2),
              (left+r, top+r, np.pi), (right-r, top+r, 3*np.pi/2)]]
    paths += [np.array([[left+r, z], [right-r, z]]) for z in (top, bottom)]
    paths += [np.array([[z, top+r], [z, bottom-r]]) for z in (left, right)]
    paths += [arc(cx, cy, hole_diameter*scale/2, 0, 2*np.pi)
              for cx in (left+r, right-r) for cy in (top+r, bottom-r)]
    paths += [arc(x, y, pocket_diameter*scale/2, 0, 2*np.pi)]
    st = top - 150
    sf, sb = st + depth*scale, st + thickness*scale
    pl, pr = x-pocket_diameter*scale/2, x+pocket_diameter*scale/2
    vertices = [[left,st], [pl,st], [pl,sf], [pr,sf], [pr,st], [right,st], [right,sb], [left,sb]]
    section = [np.array([a,b]) for a,b in zip(vertices, vertices[1:]+vertices[:1])]
    specs = [
        (width-2*margin, [[left+r, top-30], [right-r, top-30]], 'dimension', ''),
        (height, [[left-40,top], [left-40,bottom]], 'dimension', ''),
        (height-2*margin, [[left-20,top+r], [left-20,bottom-r]], 'dimension', ''),
        (hole_diameter, [[left+r,bottom-r], [left-50,bottom+50]], 'leader', ' THRU ALL'),
        (pocket_diameter, [[pr,y], [right+60,y+80]], 'leader', ''),
        (thickness, [[left-40,st], [left-40,sb]], 'dimension', ''),
        (depth, [[right+40,st], [right+40,sf]], 'dimension', ''),
    ]
    spans = [Span(id=f'd{i}', value=v, text=str(v)+suffix, anchors=anchors, anchor_mode=mode,
                  bbox=BBox(x=0,y=0,w=30,h=15)) for i,(v,anchors,mode,suffix) in enumerate(specs)]
    source = tmp_path/'synthetic.pdf'
    source.write_bytes(b'independent synthetic geometry')
    page = Page(path=str(source), width=2000,height=2000,image_png=b'',spans=spans)
    return page, paths, [paths,section], spans, scale


@pytest.mark.parametrize('params', [
    {}, {'width': 140, 'height': 90, 'margin': 8, 'thickness': 12, 'depth': 4, 'scale': 2},
    {'width': 210, 'height': 130, 'margin': 15, 'scale': 7, 'shift': (1200,1500)},
])
def test_recognition_varies_with_geometry_not_example_numbers(tmp_path, params):
    args = synthetic(tmp_path, **params)
    plan = _from_paths(*args)
    assert plan.width == params.get('width',160)
    assert plan.height == params.get('height',100)
    assert plan.corner_radius == params.get('margin',12)
    assert plan.thickness == params.get('thickness',18)
    assert plan.pocket_depth == params.get('depth',5)


@pytest.mark.parametrize('damage', ['missing_depth','extra_dimension','second_section','unequal_holes','wrong_leader'])
def test_ambiguous_or_unsupported_geometry_is_refused(tmp_path, damage):
    page, paths, groups, spans, scale = synthetic(tmp_path)
    if damage == 'missing_depth':
        spans.pop()
    elif damage == 'extra_dimension':
        spans.append(spans[0].model_copy(update={'id':'unbound'}))
    elif damage == 'second_section':
        groups.append(groups[1])
    elif damage == 'unequal_holes':
        paths[8] = paths[8] + [10,0]
    else:
        spans[4].anchors = [[1900,1900],[1990,1990]]
    with pytest.raises(Unsupported):
        _from_paths(page,paths,groups,spans,scale)


def test_plan_and_audit_survive_session_restart(tmp_path, monkeypatch, proposal):
    from drawingto3d import app
    monkeypatch.setattr(app, 'SESSION_DIR', tmp_path/'sessions')
    monkeypatch.setattr(app, 'SESSIONS', {})
    result = reason_drawing(DRAWING, tmp_path/'build', prefer_plan=True)
    app._remember('plate', str(DRAWING), result)
    app.SESSIONS.clear()
    app._load_sessions()
    restored = app.SESSIONS['plate']['result']
    assert restored.plate_plan == proposal
    assert restored.questions == result.questions
    assert app._public(restored, 'plate')['plate_plan']['width'] == 120
