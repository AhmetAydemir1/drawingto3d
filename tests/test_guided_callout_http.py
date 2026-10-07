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


# --- UX-01 B: atomic bulk "modele ait değil" ---------------------------------------------------------
# The plan's contract: one explicit bulk request closes every selected row in ONE revision, ONE history
# step, ONE undo and ONE audit event — never N sequential per-row writes. Unknown/foreign/stale/empty
# input rejects the whole action; already-ignored rows are a no-op inside an otherwise valid action.

def _three_candidates(record):
    return [record["callout_candidates"][0]
            if record.get("callout_candidates") else helpers._candidate_row(record, "k1"),
            helpers._candidate_row(record, "k2"),
            helpers._candidate_row(record, "k3")]


def _bulk_seeded(store):
    helpers.seed_callouts(store)
    record = helpers.seed_callouts(store, candidates=_three_candidates(store.load(TOKEN)))
    return record


def _ignored_ids(store):
    payload = helpers.current_payload(store)
    return {row["callout_id"] for row in payload.get("callout_reviews") or [] if row.get("ignored")}


def _bulk_rows(store):
    return [row for row in store.load(TOKEN).get("log") or [] if row.get("action") == "bulk_ignore_callouts"]


def test_ux01_bulk_ignore_is_one_revision_one_history_one_undo(live, store):
    record = _bulk_seeded(store)
    base = record["revision"]
    history = len(record.get("history") or [])
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "k2", "k3"], "ignored": True}})
    assert code == 200, body
    assert body["revision"] == base + 1
    record = store.load(TOKEN)
    assert len(record.get("history") or []) == history + 1           # tek geri alma adımı
    rows = _bulk_rows(store)
    assert len(rows) == 1                                            # tek denetim olayı, N satır değil
    assert rows[0]["value"]["count"] == 3
    assert sorted(rows[0]["value"]["callout_ids"]) == ["k1", "k2", "k3"]
    assert _ignored_ids(store) == {"k1", "k2", "k3"}
    code, body = live("/api/guided/undo", {"token": TOKEN, "revision": body["revision"]})
    assert code == 200, body
    assert _ignored_ids(store) == set()                              # tek undo üçünü birlikte geri getirdi


def test_ux01_bulk_ignore_rejects_unknown_id_whole(live, store):
    record = _bulk_seeded(store)
    base = record["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "hayalet"], "ignored": True}})
    assert code == 400, body
    assert _ignored_ids(store) == set()
    assert store.load(TOKEN)["revision"] == base                     # hiçbir kısmi yazım yok


def test_ux01_bulk_ignore_rejects_stale_revision_whole(live, store):
    record = _bulk_seeded(store)
    base = record["revision"]
    live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "set_ignored",
                                 "payload": {"callout_id": "k1", "ignored": True}})
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k2", "k3"], "ignored": True}})
    assert code == 400, body
    assert _ignored_ids(store) == {"k1"}                             # yalnız eski karar duruyor
    assert len(_bulk_rows(store)) == 0


def test_ux01_bulk_ignore_rejects_empty_list(live, store):
    record = _bulk_seeded(store)
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": record["revision"],
                                              "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": [], "ignored": True}})
    assert code == 400, body
    assert _ignored_ids(store) == set()


def test_ux01_bulk_ignore_accepts_already_ignored_rows_as_noop(live, store):
    record = _bulk_seeded(store)
    base = record["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "set_ignored",
                                              "payload": {"callout_id": "k1", "ignored": True}})
    assert code == 200, body
    base = body["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "k2"], "ignored": True}})
    assert code == 200, body                                         # zaten kapsam dışı satır hata değil
    assert body["revision"] == base + 1
    assert _ignored_ids(store) == {"k1", "k2"}
    rows = _bulk_rows(store)
    assert len(rows) == 1 and rows[0]["value"]["count"] == 2         # seçilen N, tek olay
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": body["revision"],
                                              "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1"], "ignored": True}})
    assert code == 200, body                                         # hepsi zaten kapsam dışı: no-op
    assert body["revision"] == base + 1                              # hiçbir şey değişmedi → yeni revizyon yok
    assert len(_bulk_rows(store)) == 1


def test_ux01_bulk_ignore_preserves_candidates_and_transcriptions(live, store):
    _bulk_seeded(store)
    payload = helpers.current_payload(store)
    payload["transcriptions"] = [dict(helpers._transcription(raw="4x Ø8 THRU"), callout_id="k2")]
    store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    candidates_before = store.load(TOKEN)["callout_candidates"]
    revision = store.load(TOKEN)["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": revision,
                                              "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "k2", "k3"], "ignored": True}})
    assert code == 200, body
    record = store.load(TOKEN)
    assert record["callout_candidates"] == candidates_before         # tespit kaydı değişmez
    kept = [row for row in record["decisions"].get("transcriptions") or [] if row["callout_id"] == "k2"]
    assert kept and kept[0]["raw_text"] == "4x Ø8 THRU"              # yazılan metin silinmez

def test_ux01_bulk_ignore_rejects_a_foreign_source_id_whole(live, store):
    """§14: kaynağı bu oturumla eşleşmeyen (foreign) bir kimlik varsa işlem tümden reddedilir."""
    foreign = helpers._candidate_row(store.load(TOKEN), "k9", source_digest="sha256:başka-bir-kaynak")
    helpers.seed_callouts(store, candidates=_three_candidates(store.load(TOKEN)) + [foreign])
    base = store.load(TOKEN)["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "k9"], "ignored": True}})
    assert code == 400, body
    assert _ignored_ids(store) == set()                              # hiçbir kısmi yazım yok
    assert store.load(TOKEN)["revision"] == base
    assert len(_bulk_rows(store)) == 0


def test_ux01_bulk_ignore_survives_a_session_reload(live, store):
    """§7.3: bulk ignore diskte kalıcıdır — reload/reopen durumu aynen geri okur."""
    _bulk_seeded(store)
    base = store.load(TOKEN)["revision"]
    code, body = live("/api/guided/callout", {"token": TOKEN, "revision": base, "action": "bulk_set_ignored",
                                              "payload": {"callout_ids": ["k1", "k2"], "ignored": True}})
    assert code == 200, body
    reopened = json.loads(helpers._session_path(store).read_text(encoding="utf-8"))   # diskten taze okuma
    kept = {row["callout_id"] for row in reopened["decisions"].get("callout_reviews") or [] if row.get("ignored")}
    assert kept == {"k1", "k2"}
    assert reopened["revision"] == body["revision"]
