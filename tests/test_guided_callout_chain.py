"""G5/G8/G6/GX on the store and over the real HTTP boundary.

The modules have their own pure tests; here the questions are the *integration* ones: is the proposal
a read, does a declared "cannot bind" decision really unblock the callout, does the compiled chain
reach the plan the build hands to CAD, and does an imported review travel the same validated path a
click does — with `external_review` as its provenance and nothing written on refusal.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import test_guided_callouts as helpers
from drawingto3d import app, callout_bind, callout_compile, callout_models, callout_review, guided

TOKEN = helpers.TOKEN


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


def _revision(store):
    return store.load(TOKEN)["revision"]


def _record(store):
    return store.load(TOKEN)


def _states(state):
    return {row["id"]: row for row in state["callouts"]}


def _bundle_with(store, actions, **over):
    """A bundle as a reviewer would return it: exported here, actions filled in flat."""
    bundle = store.review_export(TOKEN)
    bundle["actions"] = actions
    bundle.update(over)
    return bundle


# --- G5: proposal is a read --------------------------------------------------

def test_propose_ranks_targets_and_writes_nothing(store):
    helpers._transcribed(store)
    before_revision, before_file = _revision(store), helpers._session_path(store).read_bytes()
    result = store.propose(TOKEN, "k1")
    assert result["callout_id"] == "k1"
    assert result["proposals"], "bölgedeki daireler öneri olarak dönmeli"
    tiers = [item["evidence_tier"] for item in result["proposals"]]
    assert tiers == sorted(tiers), "öneriler kanıt katmanına göre sıralı gelmeli"
    assert all(item["target_kind"] in callout_bind.TARGET_KINDS for item in result["proposals"])
    assert all(item["evidence"] for item in result["proposals"]), "her öneri kanıtını göstermeli"
    assert result["target"] is None, "henüz onaylanmış hedef yok"
    assert _revision(store) == before_revision
    assert helpers._session_path(store).read_bytes() == before_file, "öneri okumak kaydı değiştirmemeli"


def test_propose_puts_the_stored_confirmation_first_and_says_where_it_came_from(store):
    helpers._transcribed(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    store.save(TOKEN, _revision(store), payload)
    result = store.propose(TOKEN, "k1")
    assert result["proposals"][0]["evidence_tier"] == "T0"
    assert result["proposals"][0]["target_ids"] == ["c0"]
    assert result["target"]["target_ids"] == ["c0"], "seçili hedef ayrıca döner"


def test_propose_needs_a_known_callout_and_writes_nothing(store):
    helpers.seed_callouts(store)
    before_file = helpers._session_path(store).read_bytes()
    with pytest.raises(ValueError) as error:
        store.propose(TOKEN, "yok")
    assert "bulunamadı" in str(error.value)
    assert helpers._session_path(store).read_bytes() == before_file


# --- G8: readiness names the reason, per category -----------------------------

def test_readiness_names_an_unbound_callout_with_its_id(store):
    helpers._transcribed(store)
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is False
    row = next(item for item in readiness["questions"]
               if item["category"] in ("missing_target", "ambiguous_target"))
    assert row["callout_id"] == "k1"
    assert "k1" in row["text"], "bekleyen callout'un kimliği soruda görünmeli"
    assert row["action"] == "confirm_target", "sorunun yanıtı panelin hangi düğmesi olduğunu söylemeli"


def test_readiness_carries_the_sheets_own_questions_in_categories(store):
    helpers._transcribed(store)
    payload = helpers.current_payload(store)
    payload["calibration"] = None
    payload["profile_id"] = None
    store.save(TOKEN, _revision(store), payload)
    readiness = store.readiness(TOKEN)
    categories = {item["category"] for item in readiness["questions"]}
    assert "missing_calibration" in categories
    assert "missing_profile" in categories
    assert readiness["questions_text"], "sorular metin olarak da taşınmalı"


def test_readiness_is_ready_once_the_chain_and_the_sheet_are_decided(store):
    # Ölçü kullanıcının kendi kararıyla aynı (Ø6): derleme onu onaylar, çelişki doğmaz.
    helpers._transcribed(store, parses=[helpers._parse_row(size=6.0)])
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    store.save(TOKEN, _revision(store), payload)
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is True, readiness["questions_text"]
    assert readiness["questions"] == []
    # Kullanıcı zaten Ø6 through deliğini kendi vermiş: derleme yeni bir şey eklemez, eşleşmeyi söyler.
    assert readiness["compiled"]["compiled_holes"] == 0
    assert readiness["compiled"]["callouts"] == 1
    assert readiness["rows"][0]["status"] == "compiled"
    assert readiness["rows"][0]["reason"] == "manual_decision_matches"


# --- G6: "cannot bind" is a user decision that unblocks the build -------------

def test_cannot_bind_is_a_review_decision_that_unblocks_the_callout(store):
    helpers._transcribed(store)
    store.edit_callout(TOKEN, _revision(store), "set_unbindable",
                       {"callout_id": "k1", "unbindable": True})
    record = _record(store)
    review = next(row for row in record["decisions"]["callout_reviews"] if row["callout_id"] == "k1")
    assert review["unbindable"] is True and review["ignored"] is False
    event = next(item for item in record["log"] if item["action"] == "unbindable_callout")
    assert event["actor"] == "user" and "bağlanamadı" in event["note"]
    assert _states(store.public(record))["k1"]["unbindable"] is True, "panel kararı göstermeli"
    assert store.readiness(TOKEN)["ready"] is True


def test_cannot_bind_and_not_a_callout_are_mutually_exclusive(store):
    helpers._transcribed(store)
    store.edit_callout(TOKEN, _revision(store), "set_unbindable",
                       {"callout_id": "k1", "unbindable": True})
    store.edit_callout(TOKEN, _revision(store), "set_ignored", {"callout_id": "k1", "ignored": True})
    review = next(row for row in _record(store)["decisions"]["callout_reviews"]
                  if row["callout_id"] == "k1")
    assert review["ignored"] is True and review["unbindable"] is False
    store.edit_callout(TOKEN, _revision(store), "set_unbindable",
                       {"callout_id": "k1", "unbindable": True})
    review = next(row for row in _record(store)["decisions"]["callout_reviews"]
                  if row["callout_id"] == "k1")
    assert review["ignored"] is False and review["unbindable"] is True


def test_a_refused_build_names_the_pending_callout_and_starts_nothing(store):
    helpers._transcribed(store)
    with pytest.raises(ValueError) as error:
        store.build(TOKEN, _revision(store))
    assert "k1" in str(error.value)
    assert _record(store)["build"] is None, "bekleyen callout varken üretim başlamamalı"
    assert not list(store.folder(TOKEN).glob("build-*")), "yarım klasör bırakılmamalı"


def test_a_conflicting_manual_hole_stops_the_build(store, monkeypatch):
    helpers._transcribed(store)                      # okuma Ø8 der, kullanıcının kararı c0 için Ø6
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    store.save(TOKEN, _revision(store), payload)
    compilation = callout_compile.compile_callouts(_record(store))
    assert [item["reason"] for item in compilation["conflicts"]] == ["manual_conflict"]
    monkeypatch.setattr(guided, "build_general",
                        lambda plan, source, folder: pytest.fail("çelişkiyle üretim başlamamalı"))
    with pytest.raises(ValueError) as error:
        store.build(TOKEN, _revision(store))
    assert "çelişiyor" in str(error.value)
    assert _record(store)["build"] is None


def test_the_compiled_callout_reaches_the_plan_the_build_hands_to_cad(store, monkeypatch):
    helpers._transcribed(store, parses=[helpers._parse_row(size=6.0)])
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    payload["holes"] = [row for row in payload["holes"] if row["circle_id"] != "c0"]
    store.save(TOKEN, _revision(store), payload)
    plans = []

    def fake(plan, source, folder):
        plans.append(plan)
        folder.mkdir(parents=True, exist_ok=True)      # klasörü gerçek üretici kurar
        (folder / "part.step").write_bytes(b"step")

    monkeypatch.setattr(guided, "build_general", fake)
    store.build(TOKEN, _revision(store))
    assert _record(store)["build"]["status"] == "complete"
    plan, = plans
    assert plan.parameters and plan.sketches, "plan yine de tam kurulmalı"
    logged = next(item for item in _record(store)["log"] if item.get("field") == "callout_compile")
    assert logged["evidence"]["compiled_holes"] == 1, "derleme özeti kayda geçmeli"
    assert logged["evidence"]["callouts"] == 1


# --- GX: export / import over the store --------------------------------------

def test_export_is_the_reviewers_picture_of_one_session(store):
    helpers._transcribed(store)
    bundle = store.review_export(TOKEN)
    assert bundle["bundle_version"] == callout_review.BUNDLE_VERSION
    assert bundle["schema_version"] == callout_models.CALLOUT_SCHEMA_VERSION
    assert bundle["session"] == TOKEN and bundle["base_revision"] == _revision(store)
    assert bundle["source_digest"] == _record(store)["source_sha256"]
    row = bundle["callouts"][0]
    assert row["callout_id"] == "k1" and row["raw_text"] is not None
    assert row["semantic_parse"] and row["target_proposals"], "incelemeci okumayı ve önerileri görmeli"
    assert row["freshness"]["parse"]["state"] == "current"
    for name in callout_review.IMPORT_ACTIONS:
        assert name in bundle["instructions"], "hangi eylemlerin geçerli olduğu pakette yazmalı"


def test_import_applies_actions_with_external_provenance_and_can_be_undone(store):
    helpers.seed_callouts(store)
    before = _revision(store)
    bundle = _bundle_with(store, [{"action": "transcribe", "callout_id": "k1",
                                   "raw_text": "Ø8 THRU"}])
    store.review_import(TOKEN, before, bundle)
    assert _revision(store) == before + 1
    record = _record(store)
    transcription = next(row for row in record["decisions"]["transcriptions"]
                         if row["callout_id"] == "k1")
    assert transcription["raw_text"] == "Ø8 THRU"
    assert transcription["entered_by"] == "external_review", "dış inceleme kullanıcı gibi görünmemeli"
    events = [item for item in record["log"] if item["action"] == "transcribe"]
    assert events and events[-1]["actor"] == "external_review"
    assert "Dış inceleme" in events[-1]["note"]
    store.save(TOKEN, _revision(store), undo=True)
    assert _revision(store) >= before
    assert not _record(store)["decisions"].get("transcriptions"), "geri alma metni geri almalı"


def test_import_refuses_a_tampered_bundle_and_writes_nothing(store):
    helpers._transcribed(store)
    before_revision = _revision(store)
    before_file = helpers._session_path(store).read_bytes()
    bundle = _bundle_with(store, [{"action": "transcribe", "callout_id": "yok",
                                   "raw_text": "Ø8 THRU"}])
    with pytest.raises(ValueError) as error:
        store.review_import(TOKEN, before_revision, bundle)
    assert "reddedildi" in str(error.value)
    assert _revision(store) == before_revision
    assert helpers._session_path(store).read_bytes() == before_file


def test_import_is_all_or_nothing_and_needs_the_current_revision(store):
    helpers.seed_callouts(store)
    before_revision = _revision(store)
    bundle = _bundle_with(store, [{"action": "transcribe", "callout_id": "k1",
                                   "raw_text": "Ø8 THRU"},
                                  {"action": "transcribe", "callout_id": "yok",
                                   "raw_text": "Ø8 THRU"}])
    with pytest.raises(ValueError):
        store.review_import(TOKEN, before_revision, bundle)
    assert not _record(store)["decisions"].get("transcriptions"), "hiçbir eylem uygulanmamalı"
    good = _bundle_with(store, [{"action": "transcribe", "callout_id": "k1",
                                 "raw_text": "Ø8 THRU"}])
    with pytest.raises(ValueError) as error:
        store.review_import(TOKEN, before_revision + 5, good)
    assert "oturum değişti" in str(error.value)


def test_import_of_a_confirmation_goes_through_the_same_gates(store):
    helpers._transcribed(store, parses=[helpers._parse_row(size=6.0)])
    before = _revision(store)
    bundle = _bundle_with(store, [{"action": "confirm_target", "callout_id": "k1",
                                   "target_kind": "circle", "target_ids": ["c0"]}])
    store.review_import(TOKEN, before, bundle)
    target = next(row for row in _record(store)["decisions"]["callout_targets"]
                  if row["callout_id"] == "k1")
    assert target["status"] == "confirmed" and target["target_ids"] == ["c0"]
    assert target["evidence"][0]["kind"] == "external_review"
    assert target["parser_version"] == callout_models.CALLOUT_PARSER_VERSION
    assert target["transcription_revision"] == 1
    assert store.readiness(TOKEN)["ready"] is True


def test_import_refuses_a_target_without_a_current_reading(store):
    helpers.seed_callouts(store)                     # metin yok, okuma yok
    bundle = _bundle_with(store, [{"action": "confirm_target", "callout_id": "k1",
                                   "target_kind": "circle", "target_ids": ["c0"]}])
    with pytest.raises(ValueError) as error:
        store.review_import(TOKEN, _revision(store), bundle)
    assert "no_transcription" in str(error.value)
    assert not _record(store)["decisions"].get("callout_targets")


# --- the HTTP boundary for the new endpoints ---------------------------------

@pytest.fixture
def live(store, monkeypatch):
    monkeypatch.setattr(app, "GUIDED", store)
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def post(path, data):
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}" + path,
                                         data=json.dumps(data).encode(),
                                         headers={"Content-Type": "application/json"})
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
        thread.join(timeout=5)


def test_the_proposal_readiness_and_export_endpoints_answer_over_http(live, store):
    helpers._transcribed(store)
    code, body = live("/api/guided/propose", {"token": TOKEN, "callout_id": "k1"})
    assert code == 200 and body["proposals"]
    code, body = live("/api/guided/readiness", {"token": TOKEN})
    assert code == 200 and body["ready"] is False
    code, body = live("/api/guided/export", {"token": TOKEN})
    assert code == 200 and body["callouts"][0]["callout_id"] == "k1"


def test_an_import_over_http_is_refused_whole_when_it_is_wrong(live, store):
    helpers.seed_callouts(store)
    code, body = live("/api/guided/import", {"token": TOKEN, "revision": _revision(store),
                                             "bundle": {"bundle_version": "x"}})
    assert code == 400 and "reddedildi" in body["error"]
    assert not _record(store)["decisions"].get("transcriptions")
