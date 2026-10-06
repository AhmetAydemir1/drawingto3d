"""G3R-01: the real HTTP boundary — `/save` cannot bypass the `/callout` rules.

The store-level tests prove the validation; this proves the app's own dispatch hands both paths the
same rules (calling `store.edit_callout()` is not an HTTP test). One ephemeral 127.0.0.1 server on an
OS-assigned port, a temporary synthetic store, no model and no CAD work.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import test_guided_callouts as helpers
from drawingto3d import app

TOKEN = helpers.TOKEN


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


@pytest.fixture
def live(store, monkeypatch):
    monkeypatch.setattr(app, "GUIDED", store)
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def post(path, data):
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}" + path,
            data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    try:
        yield post
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_save_cannot_bypass_the_callout_rules(live, store):
    helpers.seed_callouts(store)
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": 0, "action": "set_ignored",
                                              "payload": {"callout_id": "k1", "ignored": True}})
    assert code == 200, body
    revision = body["revision"]
    before = helpers._session_path(store).read_bytes()
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": revision, "action": "transcribe",
                                              "payload": {"callout_id": "k1", "raw_text": "Ø8"}})
    assert code == 400 and "geri alın" in body["error"]            # komut yolu doğru reddediyor
    assert helpers._session_path(store).read_bytes() == before
    decisions = helpers.current_payload(store)
    decisions["transcriptions"] = [helpers._transcription("Ø8")]
    code, body = live("/api/guided/save", {"token": TOKEN, "revision": revision, "decisions": decisions})
    assert code == 400 and "geri alın" in body["error"]            # aynı metin /save'den geçemez
    assert helpers._session_path(store).read_bytes() == before
    decisions = helpers.current_payload(store)
    decisions["manual_callouts"] = [{"id": "manual:" + "0" * 32, "source_digest": "b" * 64,
                                     "page_index": 7, "region": [0.2, 0.2, 0.3, 0.3], "revision": 999}]
    code, body = live("/api/guided/save", {"token": TOKEN, "revision": revision, "decisions": decisions})
    assert code == 400 and "add_region" in body["error"]           # istemcinin alanı da geçemez
    assert helpers._session_path(store).read_bytes() == before
    decisions = helpers.current_payload(store)
    decisions["thickness"] = 12.0
    code, body = live("/api/guided/save", {"token": TOKEN, "revision": revision, "decisions": decisions})
    assert code == 200 and body["revision"] == revision + 1        # ilgisiz gerçek kayıt hâlâ çalışıyor


def test_http_save_cannot_confirm_a_target_on_a_stale_region(live, store):
    helpers._transcribed(store)
    revision = store.load(TOKEN)["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": revision, "action": "edit_region",
                                              "payload": {"callout_id": "k1", "region": [0.6, 0.6, 0.7, 0.7]}})
    assert code == 200, body
    revision = body["revision"]
    before = helpers._session_path(store).read_bytes()
    decisions = helpers.current_payload(store)
    decisions["callout_targets"] = [helpers._target_payload()]
    code, body = live("/api/guided/save", {"token": TOKEN, "revision": revision, "decisions": decisions})
    assert code == 400 and "transcription" in body["error"]        # tazelik kapısı HTTP'de de kapalı
    assert helpers._session_path(store).read_bytes() == before
