"""Temporary real-app fixture for strategy UI and stale redundant-decision review."""
import json
from pathlib import Path
import sys
import tempfile
from http.server import ThreadingHTTPServer
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
import test_guided_callouts as H
from drawingto3d import app
with tempfile.TemporaryDirectory(prefix='g12-independent-') as tmp:
    store=H.store.__wrapped__(Path(tmp));t=H.TOKEN
    H.seed_callouts(store)
    store.edit_callout(t,store.load(t)['revision'],'transcribe',{'callout_id':'k1','raw_text':'10.00'})
    store.edit_callout(t,store.load(t)['revision'],'set_disposition',{'callout_id':'k1','disposition':'redundant','duplicate_of':'decision:thickness'})
    store.set_strategy(t,store.load(t)['revision'],{'clear':True})
    im=Image.new('RGB',(300,200),'white');ImageDraw.Draw(im).text((30,30),'10.00',fill='black');im.save(store.folder(t)/'drawing.png')
    app.GUIDED=store
    server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/guided?session={t}'}),flush=True)
    try:server.serve_forever()
    finally:server.server_close()
