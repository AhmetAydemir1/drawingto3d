"""G4 store integration (`PLAN.md` §9): the derived parse, its freshness, and its limits.

The parser itself is tested in `test_callout_parse.py`; here the *store* is under test — a saved
transcription gets exactly one parse of the real parser, an edited text replaces it with one bound to
the new revision, a row that is already current is never rewritten, and the parse never becomes a
user decision (no history entry, no undo step, no client-supplied row). Everything runs through the
real `GuidedStore` on the synthetic vector sheet the G1 suite builds.
"""
import json

import pytest

import test_guided_callouts as helpers
from drawingto3d import callout_models, callout_parse
from drawingto3d.guided import GuidedStore

TOKEN = helpers.TOKEN


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


def record_of(store):
    return store.load(TOKEN)


def rows_of(store):
    return {row["callout_id"]: row for row in record_of(store).get("callout_parses") or []}


def states_of(store):
    return {row["id"]: row for row in store.public(record_of(store))["callouts"]}


def transcribe(store, action, payload):
    return store.edit_callout(TOKEN, record_of(store)["revision"], action, payload)


# --- bir kaydedilen metin → bir gerçek okuma --------------------------------------------

def test_saving_a_transcription_writes_the_real_parsers_own_reading(store):
    helpers.seed_callouts(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "  4 × Ø8 THRU  "})
    rows = rows_of(store)
    stored = record_of(store)["decisions"]["transcriptions"][0]
    expected = callout_parse.semantic_parse(stored, sheet_unit="mm").model_dump(mode="json")
    assert rows["k1"] == expected, "kayıtlı okuma gerçek parser'ın kendi çıktısıdır"
    assert (rows["k1"]["form"], rows["k1"]["size"], rows["k1"]["count"]) == ("diameter", 8.0, 4)
    assert rows["k1"]["transcription_revision"] == stored["revision"]
    assert states_of(store)["k1"]["parse"] == {"state": "current", "reason": None}


def test_the_stored_reading_never_carries_the_raw_text_back(store):
    """Okuma kullanıcının metnini yeniden yazmaz; metin yalnız transcription kaydında durur."""
    helpers.seed_callouts(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    blob = json.dumps(rows_of(store)["k1"])
    assert "Ø8" not in blob and "THRU" not in blob
    assert record_of(store)["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"


def test_a_manual_callout_is_parsed_like_any_other(store):
    helpers.seed_callouts(store, candidate=False)
    state = transcribe(store, "add_region", {"region": [0.2, 0.2, 0.35, 0.3]})
    manual_id = state["effective_callouts"][0]["id"]
    transcribe(store, "transcribe", {"callout_id": manual_id, "raw_text": "Ø10 DEPTH 6"})
    row = rows_of(store)[manual_id]
    assert (row["form"], row["size"], row["depth"], row["termination"]) == ("diameter", 10.0, 6.0, "blind")


def test_an_unsupported_text_is_stored_as_unsupported_not_as_a_guess(store):
    helpers.seed_callouts(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "M8x1.25"})
    row = rows_of(store)["k1"]
    assert row["status"] == "unsupported" and "unsupported_syntax" in row["warnings"]
    assert states_of(store)["k1"]["parse"]["state"] == "current", "okuma var; kullanılabilirliği ayrı soru"


# --- tazelik: güncel satır yeniden yazılmaz, eskisi yenilenir ---------------------------

def test_a_current_reading_is_never_rewritten(store):
    """Tohumlanmış (dışarıdan gelmiş) güncel bir okuma satırı kayıt için otoritedir."""
    helpers._transcribed(store)                                  # fixture: k1 rev 1, okuma tohumlandı
    before = record_of(store)["callout_parses"]
    payload = helpers.current_payload(store)
    payload["thickness"] = 22.0
    store.save(TOKEN, record_of(store)["revision"], payload)
    assert record_of(store)["callout_parses"] == before


def test_editing_the_text_replaces_the_old_reading_with_one_bound_to_the_new_revision(store):
    helpers._transcribed(store)
    old = rows_of(store)["k1"]
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "Ø10"})
    row = rows_of(store)["k1"]
    stored = record_of(store)["decisions"]["transcriptions"][0]
    assert stored["revision"] != old["transcription_revision"]
    assert row["transcription_revision"] == stored["revision"], "okuma yeni revizyona bağlanır"
    assert (row["form"], row["size"], row["count"], row["termination"]) == ("diameter", 10.0, None, None)
    assert row["parser_version"] == callout_models.CALLOUT_PARSER_VERSION
    assert states_of(store)["k1"]["parse"] == {"state": "current", "reason": None}
    assert len(record_of(store)["callout_parses"]) == 1, "callout başına tek güncel okuma"


def test_a_moved_region_never_gets_a_reading_computed_for_it(store):
    """Metin alanın kendisine ait: alan taşındıysa okuma yenilenmez, eskiyen metinle birlikte durur."""
    helpers._transcribed(store)
    transcribe(store, "edit_region", {"callout_id": "k1", "region": [0.6, 0.6, 0.7, 0.7]})
    row = rows_of(store)["k1"]
    assert row["transcription_revision"] == 1, "taşınan alan için yeni okuma uydurulmaz"
    assert states_of(store)["k1"]["transcription"]["state"] == "stale"
    assert states_of(store)["k1"]["parse"]["reason"] == "region_changed"


def test_an_ignored_callout_keeps_its_reading_and_its_own_state(store):
    helpers._transcribed(store)
    before = rows_of(store)["k1"]
    transcribe(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    assert rows_of(store)["k1"] == before, "yok saymak okumayı silmez ya da değiştirmez"
    state = states_of(store)["k1"]
    assert state["ignored"] is True and state["parse"]["state"] == "current"


def test_undo_brings_the_earlier_text_back_with_its_own_reading(store):
    helpers._transcribed(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "Ø10"})
    store.save(TOKEN, record_of(store)["revision"], undo=True)
    stored = record_of(store)["decisions"]["transcriptions"][0]
    row = rows_of(store)["k1"]
    assert stored["raw_text"] == "4x Ø8 THRU"
    assert row["transcription_revision"] == stored["revision"]
    assert (row["form"], row["size"], row["count"]) == ("diameter", 8.0, 4)
    assert states_of(store)["k1"]["parse"] == {"state": "current", "reason": None}


def test_a_parser_version_bump_stales_the_old_row_and_the_next_save_refreshes_it(store):
    helpers._transcribed(store, parses=[helpers._parse_row(parser_version="callout-parser/0")])
    assert states_of(store)["k1"]["parse"] == {"state": "stale", "reason": "parser_version_changed"}
    payload = helpers.current_payload(store)
    payload["thickness"] = 21.0
    store.save(TOKEN, record_of(store)["revision"], payload)
    row = rows_of(store)["k1"]
    assert row["parser_version"] == callout_models.CALLOUT_PARSER_VERSION
    assert states_of(store)["k1"]["parse"] == {"state": "current", "reason": None}


# --- okuma bir kullanıcı kararı değildir ----------------------------------------------

def test_the_reading_is_derived_data_with_no_history_step_and_no_user_event(store):
    helpers.seed_callouts(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    record = record_of(store)
    assert len(record["history"]) == 1, "tek kullanıcı kararı = tek geçmiş adımı"
    blob = json.dumps(record["history"])
    assert "callout_parses" not in blob and "parser_version" not in blob, "okuma geçmişe karışmaz"
    actions = [row["action"] for row in record["log"]]
    assert actions.count("transcribe") == 1
    assert not [row for row in record["log"] if "parse" in row["action"] or row["actor"] == "parser"]


def test_a_client_cannot_send_its_own_reading(store):
    """`/save` bir okuma yazamaz: okuma yalnız sunucunun kendi türetmesidir (PLAN §9)."""
    helpers.seed_callouts(store)
    before = helpers._session_path(store).read_bytes()
    payload = helpers.current_payload(store)
    payload["callout_parses"] = [helpers._parse_row()]
    with pytest.raises(Exception):
        store.save(TOKEN, 0, payload)
    assert helpers._session_path(store).read_bytes() == before
    assert not record_of(store).get("callout_parses"), "reddedilen kayıt hiçbir okuma bırakmaz"


def test_a_refused_save_never_leaves_a_reading_behind(store):
    helpers.seed_callouts(store)
    before = helpers._session_path(store).read_bytes()
    payload = helpers.current_payload(store)
    payload["transcriptions"] = [helpers._transcription(raw="4x Ø8 THRU")]
    payload["callout_targets"] = [helpers._target_payload()]        # henüz okuma yok: onay dayanaksız
    with pytest.raises(ValueError, match="parse"):
        store.save(TOKEN, 0, payload)
    assert helpers._session_path(store).read_bytes() == before
    assert not record_of(store).get("callout_parses"), "reddedilen kayıt hiçbir okuma bırakmaz"


def test_the_sheet_unit_is_the_users_own_calibration_not_a_guess(store):
    """Pafta birimi kullanıcının kendi kalibrasyonundan gelir; yazılmayan birimi doldurmaz."""
    helpers.seed_callouts(store)
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "25"})
    assert rows_of(store)["k1"]["unit"] is None
    assert "unit_unresolved" in rows_of(store)["k1"]["warnings"]
    transcribe(store, "transcribe", {"callout_id": "k1", "raw_text": "25 in"})
    assert rows_of(store)["k1"]["unit"] == "in"
    assert rows_of(store)["k1"]["warnings"] == ["unit_differs_from_sheet"], "mm paftada in yazılmış"


def test_an_old_session_without_any_reading_opens_and_stays_untouched(tmp_path):
    """Okuma alanı olmayan eski kayıt açılır; okuma yokluğu `needs_parse` olarak okunur."""
    record = helpers._base_record(tmp_path)
    record.pop("callout_parses", None)
    store = GuidedStore(tmp_path / "store")
    folder = store.folder(TOKEN)
    folder.mkdir(parents=True)
    from drawingto3d.guided import _atomic
    _atomic(folder / "session.json", record)
    helpers.seed_callouts(store, candidate=True)
    state = store.public(store.load(TOKEN))
    assert record_of(store).get("callout_parses") is None
    assert state["callouts"][0]["parse"] == {"state": "missing", "reason": "needs_parse"}
