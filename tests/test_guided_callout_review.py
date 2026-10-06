"""G3 callout review (PLAN-21 §6): the user's own region, ignore and text decisions.

Everything runs through the real `GuidedStore` — one user command in, one history step, one global
revision out — on the synthetic vector sheet the G1 suite builds. Parse fixtures are seeded session
records, exactly as in G1: G3 is text and region *review*, this slice ships no parser, no target
suggester and no callout→CAD compiler, and nothing here claims one ran.
"""
import json

import pytest

import test_guided_callouts as helpers
from drawingto3d import callout_models
from drawingto3d.guided import GuidedStore, _atomic

TOKEN = helpers.TOKEN
OTHER_SOURCE = "b" * 64


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


def command(store, action, payload=None):
    """One user command at the session's current revision — the way the API sends it."""
    return store.edit_callout(TOKEN, store.load(TOKEN)["revision"], action, payload)


def record_of(store):
    return store.load(TOKEN)


def rows_of(state, key):
    return {row["id"]: row for row in state["effective_callouts"]}


def states_of(state):
    return {row["id"]: row for row in state["callouts"]}


def bytes_of(store):
    return helpers._session_path(store).read_bytes()


# --- the one effective view (PLAN-21 §6.2) ----------------------------------------------

def test_effective_callouts_is_the_base_list_until_the_user_adds_something(store):
    helpers.seed_callouts(store)
    record = record_of(store)
    base = json.dumps(record["callout_candidates"], sort_keys=True)
    rows = callout_models.effective_callouts(record)
    assert [row["id"] for row in rows] == ["k1"]
    row = rows[0]
    assert row["manual"] is False and row["source_kind"] == "vector_text"
    assert row["region"] == row["base_region"] == [0.1, 0.2, 0.4, 0.5]      # tespit edilen bölge
    assert row["region_override"] is None and row["ignored"] is False
    assert row["crop_region"] == [0.05, 0.15, 0.45, 0.55]                   # tespitin kendi crop'u
    assert row["machine_text_hint"] == "4x Ø8 THRU"
    assert row["provenance"]["kind"] == "detected"
    assert json.dumps(record["callout_candidates"], sort_keys=True) == base  # türetmek veriyi değiştirmez


def test_computing_the_effective_view_writes_nothing(store):
    helpers.seed_callouts(store)
    before, revision = bytes_of(store), record_of(store)["revision"]
    record = record_of(store)
    callout_models.effective_callouts(record)
    callout_models.callout_states(record)
    store.public(record)
    assert bytes_of(store) == before
    assert record_of(store)["revision"] == revision
    assert not [row for row in record_of(store).get("log") or [] if row["actor"] == "user"]


def test_a_manual_region_is_the_users_own_area_and_not_a_detection(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    rows = rows_of(state, "effective_callouts")
    manual = rows[_manual_id(state)]
    assert manual["manual"] is True and manual["source_kind"] == "manual"
    assert manual["page_index"] == 0
    assert manual["region"] == manual["base_region"] == [0.2, 0.2, 0.3, 0.3]
    assert manual["machine_text_hint"] is None                    # makine tespiti diye sunulmaz
    assert manual["provenance"] == {"kind": "manual", "observation_ids": [], "detector_version": None,
                                   "geometry_version": None}
    assert manual["crop_region"][0] <= 0.2 and manual["crop_region"][2] >= 0.3   # crop bölgeyi kapsar
    assert [row["id"] for row in state["callout_candidates"]] == ["k1"]          # temel liste dokunulmadı


def test_a_region_override_moves_only_the_effective_region(store):
    helpers.seed_callouts(store)
    state = command(store, "edit_region", {"callout_id": "k1", "region": [0.30, 0.30, 0.36, 0.34]})
    row = rows_of(state, "effective_callouts")["k1"]
    assert row["region"] == [0.30, 0.30, 0.36, 0.34]
    assert row["region_override"] == [0.30, 0.30, 0.36, 0.34]
    assert row["base_region"] == [0.1, 0.2, 0.4, 0.5]             # tespit bölgesi ve kanıtı duruyor
    assert row["provenance"]["kind"] == "detected"
    assert row["crop_region"][0] <= 0.30 and row["crop_region"][2] >= 0.36       # crop yeni bölgeyi kapsar
    base = record_of(store)
    assert base["callout_candidates"][0]["region"] == [0.1, 0.2, 0.4, 0.5]       # makine kaydı aynı
    assert base["callout_candidates"][0]["crop_region"] == [0.05, 0.15, 0.45, 0.55]


def _manual_id(state):
    return next(row["id"] for row in state["effective_callouts"] if row["manual"])


# --- identity is the server's (PLAN-21 §6.1) -------------------------------------------

def test_a_manual_callout_takes_its_own_server_assigned_identity(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3],
                                          "id": "manual:" + "0" * 32, "source_digest": OTHER_SOURCE,
                                          "page_index": 0})
    manual_id = _manual_id(state)
    assert callout_models.re.fullmatch(callout_models.MANUAL_ID_PATTERN, manual_id)
    assert manual_id != "manual:" + "0" * 32                      # istemcinin kimliği kabul edilmez
    stored = next(row for row in state["decisions"]["manual_callouts"] if row["id"] == manual_id)
    assert stored["source_digest"] == record_of(store)["source_sha256"]
    assert stored["revision"] == 1                                # sunucunun atadığı revizyon
    second = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    ids = [row["id"] for row in second["decisions"]["manual_callouts"]]
    assert len(ids) == 2 and manual_id in ids                 # aynı yerde ikinci kullanıcı eylemi ayrı ID


def test_an_unknown_callout_or_a_foreign_source_is_refused_without_a_write(store):
    helpers.seed_callouts(store)
    before = bytes_of(store)
    with pytest.raises(ValueError, match="böyle bir callout yok"):
        command(store, "edit_region", {"callout_id": "k9", "region": [0.2, 0.2, 0.3, 0.3]})
    with pytest.raises(ValueError, match="böyle bir callout yok"):
        command(store, "transcribe", {"callout_id": "manual:" + "1" * 32, "raw_text": "Ø8"})
    assert bytes_of(store) == before
    # Başka oturumun kaynağına ait bir kayıt: kimliği burada geçerli olsa da kaynak uyuşmaz.
    record = record_of(store)
    record["decisions"]["manual_callouts"] = [{"id": "manual:" + "2" * 32, "source_digest": OTHER_SOURCE,
                                               "page_index": 0, "region": [0.2, 0.2, 0.3, 0.3],
                                               "revision": 1}]
    _atomic(helpers._session_path(store), record)
    tampered = bytes_of(store)
    with pytest.raises(ValueError, match="kaynağına ait değil"):
        store.edit_callout(TOKEN, record["revision"], "transcribe",
                           {"callout_id": "manual:" + "2" * 32, "raw_text": "Ø8"})
    assert bytes_of(store) == tampered


@pytest.mark.parametrize("region", [
    [0.4, 0.2, 0.1, 0.5],          # ters kutu
    [0.2, 0.2, 0.2, 0.3],          # sıfır genişlik
    [0.2, 0.2, 0.3, 0.3, 0.4],     # dört sayı değil
    [-0.1, 0.2, 0.3, 0.3],         # sayfa dışı
    [0.2, 0.2, 1.3, 0.3],          # sayfa dışı
    ["a", "b", "c", "d"],          # sayı değil
    None,                          # eksik
])
def test_a_region_the_server_cannot_draw_is_refused(store, region):
    helpers.seed_callouts(store)
    before = bytes_of(store)
    with pytest.raises(ValueError):
        command(store, "add_region", {"region": region})
    assert bytes_of(store) == before
    assert record_of(store)["revision"] == 0


def test_only_the_first_page_can_hold_a_region_in_this_slice(store):
    helpers.seed_callouts(store)
    with pytest.raises(ValueError, match="0. sayfada"):
        command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3], "page_index": 1})


# --- one command, one history step, one revision (PLAN-21 §6.4) -------------------------

def test_every_review_command_is_one_history_step_and_one_revision(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    assert state["revision"] == 1 and len(record_of(store)["history"]) == 1
    state = command(store, "edit_region", {"callout_id": "k1", "region": [0.3, 0.3, 0.36, 0.34]})
    assert state["revision"] == 2 and len(record_of(store)["history"]) == 2
    state = command(store, "set_ignored", {"callout_id": manual_id, "ignored": True})
    assert state["revision"] == 3 and len(record_of(store)["history"]) == 3
    actions = [row["action"] for row in record_of(store)["log"] if row["actor"] == "user"]
    # The fixture's raw ints (50, 6) are normalised by the first save and reported as an edit of
    # those fields; the user's own callout commands sit behind them, in order, one each.
    assert [name for name in actions if name.startswith(("add_", "edit_callout", "ignore", "restore"))] == \
        ["add_callout_region", "edit_callout_region", "ignore_callout"]


def test_repeating_a_command_is_a_noop(store):
    helpers.seed_callouts(store)
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    revision, log, history = record_of(store)["revision"], len(record_of(store)["log"]), \
        len(record_of(store)["history"])
    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    assert state["revision"] == revision                          # ikinci kez aynı karar: yazılmaz
    assert len(record_of(store)["log"]) == log and len(record_of(store)["history"]) == history


def test_an_unknown_command_is_refused(store):
    helpers.seed_callouts(store)
    with pytest.raises(ValueError, match="işlem bulunamadı"):
        command(store, "delete_everything", {})


def test_a_stale_revision_command_is_refused_and_keeps_the_stored_decisions(store):
    helpers.seed_callouts(store)
    command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    before = bytes_of(store)
    with pytest.raises(ValueError, match="oturum değişti"):
        store.edit_callout(TOKEN, 0, "set_ignored", {"callout_id": "k1", "ignored": True})
    assert bytes_of(store) == before


def test_a_review_survives_undo_and_a_fresh_store_instance(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    command(store, "edit_region", {"callout_id": manual_id, "region": [0.22, 0.22, 0.32, 0.32]})
    command(store, "set_ignored", {"callout_id": manual_id, "ignored": True})
    reopened = GuidedStore(store.root)
    public = reopened.public(reopened.load(TOKEN))
    rows = {row["id"]: row for row in public["effective_callouts"]}
    assert rows[manual_id]["ignored"] is True
    assert rows[manual_id]["region"] == [0.22, 0.22, 0.32, 0.32]  # undo/reopen kimliği ve bölgeyi korur
    state = store.save(TOKEN, record_of(store)["revision"], undo=True)
    assert not rows_of(state, "effective_callouts")[manual_id]["ignored"]
    assert rows_of(state, "effective_callouts")[manual_id]["region"] == [0.22, 0.22, 0.32, 0.32]


# --- the user's text (PLAN-21 §6.3) ----------------------------------------------------

def test_the_text_is_kept_verbatim_and_the_source_region_is_the_servers(store):
    helpers.seed_callouts(store)
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "  4 × Ø8 THRU  ",
                                          "source_region": [0.9, 0.9, 0.95, 0.95],
                                          "revision": 777})
    row = state["decisions"]["transcriptions"][0]
    assert row["raw_text"] == "  4 × Ø8 THRU  "                   # birebir, kırpılmadan
    assert row["normalized_text"] == "4 × Ø8 THRU"                # sunucunun ayrı alanı
    assert row["source_region"] == [0.1, 0.2, 0.4, 0.5]           # etkin bölge; istemcinin kutusu değil
    assert row["revision"] == 1                                   # sunucunun revizyonu
    assert states_of(state)["k1"]["transcription"] == {"state": "current", "revision": 1, "reason": None}


def test_a_manual_callout_can_carry_the_users_text(store):
    helpers.seed_callouts(store, candidates=[])                    # metinsiz/açıklamasız sayfa
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    assert states_of(state)[manual_id]["transcription"]["reason"] == "needs_transcription"
    state = command(store, "transcribe", {"callout_id": manual_id, "raw_text": "Ø12"})
    row = state["decisions"]["transcriptions"][0]
    assert row["callout_id"] == manual_id and row["raw_text"] == "Ø12"
    assert row["source_region"] == [0.2, 0.2, 0.3, 0.3]
    assert states_of(state)[manual_id]["transcription"]["state"] == "current"


@pytest.mark.parametrize("raw_text", ["", "   ", "\n\t "])
def test_a_blank_text_is_refused(store, raw_text):
    helpers.seed_callouts(store)
    before = bytes_of(store)
    with pytest.raises(ValueError):
        command(store, "transcribe", {"callout_id": "k1", "raw_text": raw_text})
    assert bytes_of(store) == before
    assert (record_of(store)["decisions"].get("transcriptions") or []) == []
    assert (record_of(store)["decisions"].get("callout_reviews") or []) == []


def test_moving_the_region_stales_the_old_text_and_never_rewrites_it(store):
    helpers.seed_callouts(store)
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    revision = state["decisions"]["transcriptions"][0]["revision"]
    helpers.seed_callouts(store, candidate=False, parses=[helpers._parse_row(transcription_revision=revision)])
    assert states_of(store.public(record_of(store)))["k1"]["parse"] == {"state": "current", "reason": None}

    state = command(store, "edit_region", {"callout_id": "k1", "region": [0.30, 0.30, 0.36, 0.34]})
    stored = state["decisions"]["transcriptions"][0]
    assert stored["raw_text"] == "4x Ø8 THRU"                     # metin silinmez
    assert stored["source_region"] == [0.1, 0.2, 0.4, 0.5]        # eski snapshot sessizce güncellenmez
    assert stored["revision"] == revision                         # metin kararı yeniden yazılmadı
    row = states_of(state)["k1"]
    assert row["transcription"] == {"state": "stale", "revision": revision, "reason": "region_changed"}
    assert row["parse"] == {"state": "stale", "reason": "region_changed"}
    assert row["target"] == {"state": "missing", "reason": "needs_target"}


def test_saving_the_text_again_on_the_new_region_is_a_new_user_decision(store):
    helpers.seed_callouts(store)
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    first = state["decisions"]["transcriptions"][0]["revision"]
    helpers.seed_callouts(store, candidate=False, parses=[helpers._parse_row(transcription_revision=first)])
    command(store, "edit_region", {"callout_id": "k1", "region": [0.30, 0.30, 0.36, 0.34]})
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    row = state["decisions"]["transcriptions"][0]
    assert row["revision"] != first                               # yeni transcription revision'ı
    assert row["source_region"] == [0.30, 0.30, 0.36, 0.34]       # incelenen yeni alan
    assert states_of(state)["k1"]["transcription"]["state"] == "current"
    assert states_of(state)["k1"]["parse"] == {"state": "stale", "reason": "transcription_changed"}
    events = [item["action"] for item in record_of(store)["log"] if item["actor"] == "user"]
    assert events.count("edit_transcription") == 1                # gerçek kullanıcı eylemi olarak kayıtlı


def test_ignore_keeps_the_text_and_restore_brings_the_callout_back(store):
    helpers.seed_callouts(store)
    command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    assert states_of(state)["k1"]["ignored"] is True
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"   # metin duruyor
    assert rows_of(state, "effective_callouts")["k1"]["ignored"] is True

    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": False})
    assert states_of(state)["k1"]["ignored"] is False
    assert state["decisions"]["callout_reviews"] == []            # iki karar da geri alındı: kayıt kalkar
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"


def test_a_text_cannot_be_written_to_an_ignored_callout(store):
    helpers.seed_callouts(store)
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    before = bytes_of(store)
    with pytest.raises(ValueError, match="geri alın"):
        command(store, "transcribe", {"callout_id": "k1", "raw_text": "Ø8"})
    assert bytes_of(store) == before
    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": False})
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "Ø8"})
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "Ø8"


def test_an_ignore_flag_that_is_not_a_boolean_is_refused(store):
    helpers.seed_callouts(store)
    for value in (1, "true", None):
        with pytest.raises(ValueError):
            command(store, "set_ignored", {"callout_id": "k1", "ignored": value})


# --- old sessions, old clients, undo (PLAN-21 §6.1/§9-U10) ------------------------------

def test_a_missing_key_keeps_the_new_decisions_and_an_explicit_empty_removes_them(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    payload = helpers.current_payload(store, with_callouts=False)
    payload.pop("manual_callouts", None)
    payload.pop("callout_reviews", None)
    payload["thickness"] = 12
    state = store.save(TOKEN, state["revision"], payload)
    assert len(state["decisions"]["manual_callouts"]) == 1        # eksik anahtar = mevcut değeri koru
    payload = helpers.current_payload(store)
    payload["manual_callouts"] = []
    state = store.save(TOKEN, state["revision"], payload)
    assert state["decisions"]["manual_callouts"] == []            # açık boş liste = kullanıcının kaldırması


def test_a_history_entry_from_an_older_schema_still_undoes(store):
    helpers.seed_callouts(store)
    old = {"calibration": None, "profile_id": None, "holes": [], "bindings": []}
    helpers.seed_callouts(store, history=[old])
    state = store.save(TOKEN, record_of(store)["revision"], undo=True)
    assert (state["decisions"].get("manual_callouts") or []) == []   # yeni alanlar varsayılanla okunur
    assert (state["decisions"].get("callout_reviews") or []) == []
    assert state["revision"] == 1
    assert state["callouts"][0]["transcription"]["state"] == "missing"   # çökme yok, boş state doğru


def test_an_edit_makes_the_old_step_historical_without_resurrecting_it(store):
    helpers.seed_callouts(store)
    folder = helpers._fake_build(store)
    state = store.public(record_of(store))
    assert state["step"] is not None
    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    assert state["build_status"] is None and state["step"] is None
    with pytest.raises(ValueError):
        store.artifact(TOKEN, "part.step")
    assert (folder / "part.step").exists()                        # eski dosya tarihsel olarak duruyor


def test_the_base_candidates_and_the_reading_never_move_from_a_review(store):
    helpers.seed_callouts(store, proposals=[{"field": "thickness", "value": 10, "confidence": "rule",
                                             "evidence": {"rule": "fixture"}}])
    before = record_of(store)
    base = json.dumps(before["callout_candidates"], sort_keys=True)
    proposals = json.dumps(before["proposals"], sort_keys=True)
    options = json.dumps(before["options"], sort_keys=True)
    command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    command(store, "edit_region", {"callout_id": "k1", "region": [0.3, 0.3, 0.36, 0.34]})
    command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    after = record_of(store)
    assert json.dumps(after["callout_candidates"], sort_keys=True) == base
    assert json.dumps(after["proposals"], sort_keys=True) == proposals
    assert json.dumps(after["options"], sort_keys=True) == options
    assert (after.get("callout_parses") or []) == []               # hiçbir parse uydurulmadı
    assert after["callout_schema_version"] == 2                    # G3 yazımı yeni sürümü damgalar


# --- düzeltme turu 4 (PLAN-22 §4, G3R-01): eski /save yeni komut kurallarını atlayamaz ----------

def test_a_public_save_cannot_create_or_change_a_manual_region(store):
    """İstemci kendi `manual:` kaydını /save ile yazamaz; alanı yalnız add_region üretir."""
    helpers.seed_callouts(store)
    before = bytes_of(store)
    forged = {"id": "manual:" + "0" * 32, "source_digest": OTHER_SOURCE, "page_index": 7,
              "region": [0.2, 0.2, 0.3, 0.3], "revision": 999}
    payload = helpers.current_payload(store)
    payload["manual_callouts"] = [forged]
    with pytest.raises(ValueError, match="add_region"):
        store.save(TOKEN, 0, payload)
    assert bytes_of(store) == before

    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    stored = next(row for row in record_of(store)["decisions"]["manual_callouts"] if row["id"] == manual_id)
    before = bytes_of(store)
    moved = {**stored, "region": [0.5, 0.5, 0.6, 0.6]}              # var olanın bölgesini değiştirme denemesi
    payload = helpers.current_payload(store)
    payload["manual_callouts"] = [moved]
    with pytest.raises(ValueError, match="edit_region"):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before

    carried = store.save(TOKEN, record_of(store)["revision"], helpers.current_payload(store))
    assert carried["decisions"]["manual_callouts"] == [stored]      # aynen taşıma serbest
    cleared = store.save(TOKEN, record_of(store)["revision"],
                         {**helpers.current_payload(store), "manual_callouts": []})
    assert cleared["decisions"]["manual_callouts"] == []            # açık [] = kullanıcının kaldırması
    events = [row["action"] for row in record_of(store)["log"] if row["actor"] == "user"]
    assert events.count("veto") == 1                                # kaldırma gerçek olay olarak kayda geçti


def test_a_public_save_cannot_set_a_review_decision(store):
    """Yok sayma/bölge kararı /save ile doğmaz: bilinmeyen referans da, tanıdık kimlik de reddedilir."""
    helpers.seed_callouts(store)
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["callout_reviews"] = [{"callout_id": "unknown-callout", "ignored": True, "revision": 999}]
    with pytest.raises(ValueError, match="set_ignored"):
        store.save(TOKEN, 0, payload)
    payload = helpers.current_payload(store)
    payload["callout_reviews"] = [{"callout_id": "k1", "ignored": True}]
    with pytest.raises(ValueError, match="set_ignored"):
        store.save(TOKEN, 0, payload)
    payload = helpers.current_payload(store)
    payload["callout_reviews"] = [{"callout_id": "k1", "region_override": [0.3, 0.3, 0.4, 0.4]}]
    with pytest.raises(ValueError, match="edit_region"):
        store.save(TOKEN, 0, payload)
    assert bytes_of(store) == before
    assert record_of(store)["revision"] == 0


def test_clearing_the_review_list_is_a_real_restore_not_a_silent_edit(store):
    helpers.seed_callouts(store)
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    state = store.save(TOKEN, record_of(store)["revision"],
                       {**helpers.current_payload(store), "callout_reviews": []})
    assert state["decisions"]["callout_reviews"] == []
    assert states_of(state)["k1"]["ignored"] is False
    events = [row["action"] for row in record_of(store)["log"] if row["actor"] == "user"]
    assert events.count("restore_callout") == 1                     # komut bir kez, fark günlüğü tekrar etmez


def test_a_public_save_cannot_write_text_to_an_ignored_callout(store):
    helpers.seed_callouts(store)
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["transcriptions"] = [helpers._transcription()]
    with pytest.raises(ValueError, match="geri alın"):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before
    carried = store.save(TOKEN, record_of(store)["revision"], helpers.current_payload(store))
    assert carried["decisions"]["transcriptions"] == []             # aynen taşınan eski metin yok: ret yok


def test_a_public_save_checks_the_text_region_against_the_effective_region(store):
    """Metnin kaynak bölgesi sunucunun etkin bölgesi olmalı; istemci kendi snapshot'ını yazamaz."""
    helpers.seed_callouts(store)
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["transcriptions"] = [{**helpers._transcription(), "source_region": [0.6, 0.6, 0.7, 0.7]}]
    with pytest.raises(ValueError, match="etkin bölge"):
        store.save(TOKEN, 0, payload)
    assert bytes_of(store) == before
    payload = helpers.current_payload(store)
    payload["transcriptions"] = [helpers._transcription(raw="4x Ø8 THRU")]      # doğru bölge: kabul
    state = store.save(TOKEN, 0, payload)
    assert state["decisions"]["transcriptions"][0]["source_region"] == [0.1, 0.2, 0.4, 0.5]
    assert states_of(state)["k1"]["transcription"]["state"] == "current"


def test_an_unrelated_full_save_carries_every_g3_row_verbatim(store):
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    command(store, "transcribe", {"callout_id": manual_id, "raw_text": "Ø12"})
    command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    before = record_of(store)["decisions"]
    state = store.save(TOKEN, record_of(store)["revision"],
                       helpers.current_payload(store, thickness=12.0))
    assert state["decisions"]["thickness"] == 12.0
    for key in ("manual_callouts", "callout_reviews", "transcriptions"):
        assert state["decisions"][key] == before[key]               # ilgisiz kayıt G3 satırlarını bozmaz


def test_the_full_review_flow_still_works_end_to_end(store):
    """add_region → transcribe → edit_region → yeniden kaydet → ignore → restore → undo."""
    helpers.seed_callouts(store)
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    manual_id = _manual_id(state)
    first = command(store, "transcribe", {"callout_id": manual_id, "raw_text": "Ø12"})
    revision = first["decisions"]["transcriptions"][0]["revision"]
    state = command(store, "edit_region", {"callout_id": manual_id, "region": [0.22, 0.22, 0.32, 0.32]})
    assert states_of(state)[manual_id]["transcription"] == {"state": "stale", "revision": revision,
                                                            "reason": "region_changed"}
    state = command(store, "transcribe", {"callout_id": manual_id, "raw_text": "Ø12"})
    row = states_of(state)[manual_id]["transcription"]
    assert row["state"] == "current" and row["revision"] != revision
    state = command(store, "set_ignored", {"callout_id": manual_id, "ignored": True})
    state = command(store, "set_ignored", {"callout_id": manual_id, "ignored": False})
    assert states_of(state)[manual_id]["ignored"] is False
    assert rows_of(state, "effective_callouts")[manual_id]["region"] == [0.22, 0.22, 0.32, 0.32]
    state = store.save(TOKEN, record_of(store)["revision"], undo=True)
    assert state["can_undo"] is True
    assert len(state["decisions"]["manual_callouts"]) == 1          # undo alanı silmez
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "Ø12"


# --- düzeltme turu 4 (PLAN-22 §5, G3R-02): yeni onayın tazeliği --------------------------------

def test_a_new_confirmation_after_a_region_move_needs_a_current_text_and_parse(store):
    record = helpers._transcribed(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    state = store.save(TOKEN, record["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}

    state = command(store, "edit_region", {"callout_id": "k1", "region": [0.6, 0.6, 0.7, 0.7]})
    assert state["callouts"][0]["transcription"]["state"] == "stale"
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [{**helpers._target_payload(), "target_ids": ["c1"]}]  # yeni onay denemesi
    with pytest.raises(ValueError, match="transcription"):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before                                # ret: dosya/log/history aynı

    # Pozitif kontrol: metni yeni etkin bölgede açıkça yeniden kaydet, güncel parse fixture'ı hazırla
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8 THRU"})
    revision = state["decisions"]["transcriptions"][0]["revision"]
    helpers.seed_callouts(store, candidate=False,
                          parses=[helpers._parse_row(transcription_revision=revision)])
    start = len(record_of(store)["log"])
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [{**helpers._target_payload(), "target_ids": ["c1"],
                                   "transcription_revision": revision}]
    state = store.save(TOKEN, record_of(store)["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    confirms = [row for row in record_of(store)["log"][start:] if row["action"] == "confirm_target"]
    assert len(confirms) == 1                                       # tek gerçek onay olayı


def test_a_region_move_and_a_target_confirmation_in_one_save_cannot_skip_freshness(store):
    """R-01 dış mutasyonu reddeder; ortak commit yolu kendi son durumunu yine denetler."""
    helpers._transcribed(store)
    review = {"callout_id": "k1", "region_override": [0.6, 0.6, 0.7, 0.7], "ignored": False}
    payload = helpers.current_payload(store)
    payload["callout_reviews"] = [review]
    payload["callout_targets"] = [{**helpers._target_payload(), "target_ids": ["c1"]}]
    before = bytes_of(store)
    with pytest.raises(ValueError):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before
    # taşınan kayıt satırı ile (kullanıcı komutuyla kaydedilmiş) bölge değişimi: yine ret
    command(store, "edit_region", {"callout_id": "k1", "region": [0.6, 0.6, 0.7, 0.7]})
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [{**helpers._target_payload(), "target_ids": ["c1"]}]
    with pytest.raises(ValueError, match="transcription"):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before
    assert record_of(store)["decisions"]["callout_targets"] == []


def test_an_ignored_callout_cannot_be_confirmed_and_a_carried_target_is_untouched(store):
    helpers.seed_callouts(store)
    state = command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    before = bytes_of(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    with pytest.raises(ValueError, match="geri alın"):
        store.save(TOKEN, record_of(store)["revision"], payload)
    assert bytes_of(store) == before


def test_a_carried_stale_target_survives_an_unrelated_full_save(store):
    """PLAN.md §5: aynen taşınan stale target + ilgisiz kalınlık kaydı çalışır; satır bayt aynı kalır."""
    record = helpers._transcribed(store)
    payload = helpers.current_payload(store)
    payload["callout_targets"] = [helpers._target_payload()]
    state = store.save(TOKEN, record["revision"], payload)
    assert state["callouts"][0]["target"]["state"] == "current"

    command(store, "edit_region", {"callout_id": "k1", "region": [0.6, 0.6, 0.7, 0.7]})
    stale = store.public(store.load(TOKEN))
    assert stale["callouts"][0]["target"]["state"] == "stale"       # eski onay current değil
    target_before = record_of(store)["decisions"]["callout_targets"]
    assert target_before                                                # taşınacak gerçek satır var

    state = store.save(TOKEN, record_of(store)["revision"],
                       helpers.current_payload(store, thickness=12.0))  # ilgisiz tam kayıt
    assert state["decisions"]["thickness"] == 12.0
    assert state["decisions"]["callout_targets"] == target_before       # ne yeniden damga ne düşme
    assert state["callouts"][0]["target"]["state"] == "stale"           # stale kalır, current olmaz


# --- düzeltme turu 4 (PLAN-22 §6, G3R-03): şema damgası gerçek yazımda ------------------------

def test_a_v1_session_is_stamped_by_its_first_real_write_and_reads_stay_read_only(store):
    helpers.seed_callouts(store)
    record = store.load(TOKEN)
    record["callout_schema_version"] = 1
    _atomic(helpers._session_path(store), record)
    before = bytes_of(store)
    public = store.public(store.load(TOKEN))
    assert public["callout_schema_version"] == 1                    # okuma sürümü yükseltmez
    assert bytes_of(store) == before
    noop = store.save(TOKEN, 0, helpers.current_payload(store))
    assert noop["callout_schema_version"] == 1 and bytes_of(store) == before   # no-op yazmaz
    state = command(store, "add_region", {"region": [0.2, 0.2, 0.3, 0.3]})
    assert state["callout_schema_version"] == callout_models.CALLOUT_SCHEMA_VERSION == 2
    assert store.load(TOKEN)["callout_schema_version"] == 2


def test_a_versionless_legacy_session_is_stamped_on_a_real_write_only(store):
    helpers.seed_callouts(store)
    record = store.load(TOKEN)
    record.pop("callout_schema_version", None)
    record["callout_candidates"] = []
    record.pop("callout_detection", None)
    _atomic(helpers._session_path(store), record)
    assert store.public(store.load(TOKEN))["callout_schema_version"] is None
    state = store.save(TOKEN, 0, helpers.current_payload(store, with_callouts=False, thickness=12.0))
    assert state["revision"] == 1 and state["callout_schema_version"] == 2


def test_a_future_unknown_schema_version_is_never_downgraded(store):
    helpers.seed_callouts(store)
    record = store.load(TOKEN)
    record["callout_schema_version"] = 7                            # bilinmeyen ileri şema
    _atomic(helpers._session_path(store), record)
    state = store.save(TOKEN, 0, helpers.current_payload(store, thickness=12.0))
    assert state["callout_schema_version"] == 7


def test_undo_never_lowers_the_callout_schema_version(store):
    helpers.seed_callouts(store)
    record = store.load(TOKEN)
    record["callout_schema_version"] = 1
    record["history"] = [record["decisions"]]
    record["revision"] = 1
    _atomic(helpers._session_path(store), record)
    state = store.save(TOKEN, 1, undo=True)
    assert state["revision"] == 2
    assert state["callout_schema_version"] == 2                      # history'de sürüm alanı yok: geriye düşmez


# --- düzeltme turu 4 (PLAN-22 §7, G3R-04): tespit metadata'sı public'te -----------------------

def test_the_public_state_serves_the_detection_metadata_and_admits_its_absence(store):
    helpers.seed_callouts(store)
    record = store.load(TOKEN)
    record["callout_detection"] = {"detector_version": "callout-detector/1",
                                   "diagnostics": [{"code": "source_digest_mismatch", "observation_id": None}]}
    _atomic(helpers._session_path(store), record)
    public = store.public(store.load(TOKEN))
    assert public["callout_detection"] == record["callout_detection"]        # round-trip, uydurma yok
    record = store.load(TOKEN)
    record.pop("callout_detection", None)
    _atomic(helpers._session_path(store), record)
    public = store.public(store.load(TOKEN))
    assert public["callout_detection"] is None                      # eski kayıt: açık "yok"
    assert public["callout_candidates"][0]["id"] == "k1"            # mevcut davranış bozulmadı
