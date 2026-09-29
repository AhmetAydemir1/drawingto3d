"""Read-only P01/P03 audit probes. Any session write uses TemporaryDirectory.

Run from repository root:
  PYTHONPATH=src .venv/bin/python out/goal-audit-20260929-ycgu28h8/audit_geometry_state_probe.py

These assertions describe the independently checked defects as of 2026-09-29;
this evidence script is not a permanent product acceptance test.
"""
import copy
import json
import runpy
import tempfile
from pathlib import Path
from unittest.mock import patch

from drawingto3d import guided

helpers = runpy.run_path('tests/test_stable_identities.py')
old = helpers['options']()
fresh = copy.deepcopy(old)
fresh['profiles'][0]['edges'][0]['id'] = 'reader_changed_edge'
fresh['measurements'] = [{'id': 'different_text', 'text': '999'}]
accepted = guided._same_geometry(old, fresh)
assert accepted is True
print('migration accepts changed edge IDs / measurement IDs:', accepted)

legacy = helpers['decisions']([
    helpers['tie'](60.0, helpers['end']('edge:0', (0, 0)),
                   helpers['end']('edge:1', (100, 100)))
])
other = copy.deepcopy(old)
other['profiles'][0]['id'] = 'outline_other'
for edge in other['profiles'][0]['edges']:
    edge['id'] = 'new_' + edge['id']
changed = legacy.model_copy(update={'profile_id': 'outline_other'})
unresolved = guided.unresolved_bindings(other, changed)
assert unresolved == []
print('legacy binding after profile changed to entirely different edges:', unresolved)

stable = helpers['decisions']([
    helpers['tie'](60.0, helpers['end']('e0:start', (0, 0)),
                   helpers['end']('e1:start', (100, 0)))
]).model_copy(update={'profile_id': None})
try:
    guided.questions(stable, None, old)
except AttributeError as error:
    assert str(error) == "'NoneType' object has no attribute 'get'"
    print('clearing selected profile with stable bindings:', type(error).__name__, str(error))
else:
    raise AssertionError('Expected missing-profile crash was not reproduced')

with tempfile.TemporaryDirectory(prefix='audit-p01-') as temporary:
    store = guided.GuidedStore(Path(temporary))
    token = 'a' * 32
    store.folder(token).mkdir()
    record = {
        'token': token, 'revision': 2, 'options': copy.deepcopy(old),
        'decisions': legacy.model_dump(mode='json'), 'history': [],
        'build': {'status': 'complete', 'revision': 2, 'folder': temporary},
        'log': [], 'source': str(Path(temporary) / 'source.pdf'),
    }
    record['options']['profiles'][0]['solved_dimensions'] = {'status': 'solved'}
    mismatched = copy.deepcopy(old)
    mismatched['profiles'].append({'id': 'extra'})
    with patch.object(guided, 'observe', return_value=None), \
         patch.object(guided, 'drawing_options', return_value=mismatched):
        migrated = store._migrated(token, record)
    public = store.public(migrated)
    assert migrated.get('geometry_stale')
    assert public['build_status'] == 'complete'
    assert public['step'] == f'/guided-session/{token}/part.step'
    assert 'geometry_stale' not in public
    assert public['error'] is None
    print('failed migration keeps complete STEP advertised:',
          bool(migrated.get('geometry_stale')), public['build_status'], public['step'])
    print('failed migration reason exposed publicly:',
          'geometry_stale' in public, public['error'])

print('All four independently constructed defect probes reproduced.')
