"""G9 UX turu (PLAN-23 §15 sonrası dar tur): toplu kapsam kararı + makine ipucu tek-tık kabulü.

The G9 run measured the burden: 45 candidates, 43 of them declared out of scope — one click per row.
This slice makes the *same decision* cheaper without making it less explicit, and adds nothing that
decides on the user's behalf:

- `set_ignored_many` — one explicit action closes every still-undecided callout, each as its own
  review row and its own log line. Refused whole if any named callout already carries a decision or
  does not exist: a bulk action must not report success while silently skipping a row.
- `transcribe` + `accept_hint` — the machine hint's single-click acceptance. The server checks the
  text really is this callout's own hint (a client cannot "accept" something else), the decision is
  still the user's, and the log names the hint it accepted.

Nothing here filters title-block candidates on its own and nothing is case-specific: the same two
commands act on any callout of any sheet, and every exclusion stays a declared, visible review row.
"""
import json

import pytest

import test_guided_callouts as helpers
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION

TOKEN = helpers.TOKEN
HINT = "4x Ø8 THRU"


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


def command(store, action, payload=None):
    """One user command at the session's current revision — the way the API sends it."""
    return store.edit_callout(TOKEN, store.load(TOKEN)["revision"], action, payload)


def bytes_of(store):
    return helpers._session_path(store).read_bytes()


def rows_of(state):
    return {row["id"]: row for row in state["effective_callouts"]}


def reviews_of(store):
    return {row["callout_id"]: row for row in store.load(TOKEN)["decisions"].get("callout_reviews") or []}


def log_of(store):
    return store.load(TOKEN).get("log") or []


def _three_undecided(store):
    """Three detected candidates, none of them decided yet — the G9 tail in miniature."""
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[
        helpers._candidate_row(record, "k1", machine_text_hint=HINT),
        helpers._candidate_row(record, "k2", region=[0.6, 0.1, 0.7, 0.2],
                               crop_region=[0.55, 0.05, 0.75, 0.25]),
        helpers._candidate_row(record, "k3", region=[0.6, 0.3, 0.7, 0.4],
                               crop_region=[0.55, 0.25, 0.75, 0.45]),
    ])
    return record


# --- set_ignored_many: one explicit action, every exclusion still visible -----------------------

def test_a_bulk_scope_decision_closes_every_undecided_callout_in_one_history_step(store):
    _three_undecided(store)
    before = store.load(TOKEN)
    state = command(store, "set_ignored_many", {"callout_ids": ["k1", "k2", "k3"]})
    record = store.load(TOKEN)
    assert state["revision"] == before["revision"] + 1
    assert len(record["history"]) == len(before["history"]) + 1
    reviews = reviews_of(store)
    assert sorted(reviews) == ["k1", "k2", "k3"]
    assert all(row["ignored"] is True for row in reviews.values())
    assert all(not row.get("unbindable") for row in reviews.values())
    assert all(row["revision"] == state["revision"] for row in reviews.values())
    assert all(rows_of(state)[key]["ignored"] for key in ("k1", "k2", "k3"))
    events = [row for row in log_of(store) if row["action"] == "ignore_callout"]
    assert sorted(row["field"] for row in events) == ["callout:k1", "callout:k2", "callout:k3"]
    assert all("toplu" in (row.get("note") or "") for row in events)


def test_a_bulk_scope_decision_keeps_a_region_the_user_drew_themselves(store):
    """The box the user corrected is not silently reset by declaring it not-a-callout."""
    _three_undecided(store)
    command(store, "edit_region", {"callout_id": "k2", "region": [0.62, 0.12, 0.72, 0.22]})
    command(store, "set_ignored_many", {"callout_ids": ["k1", "k2", "k3"]})
    row = reviews_of(store)["k2"]
    assert row["ignored"] is True and row["region_override"] == [0.62, 0.12, 0.72, 0.22]


def test_a_bulk_scope_decision_refuses_a_callout_that_already_carries_text(store):
    _three_undecided(store)
    command(store, "transcribe", {"callout_id": "k1", "raw_text": HINT})
    before, revision = bytes_of(store), store.load(TOKEN)["revision"]
    with pytest.raises(ValueError, match="karara bağlanmamış"):
        command(store, "set_ignored_many", {"callout_ids": ["k1", "k2", "k3"]})
    assert bytes_of(store) == before and store.load(TOKEN)["revision"] == revision


def test_a_bulk_scope_decision_refuses_a_callout_the_user_already_decided(store):
    _three_undecided(store)
    command(store, "set_unbindable", {"callout_id": "k2", "unbindable": True})
    before, revision = bytes_of(store), store.load(TOKEN)["revision"]
    with pytest.raises(ValueError, match="karara bağlanmamış"):
        command(store, "set_ignored_many", {"callout_ids": ["k1", "k2"]})
    assert bytes_of(store) == before and store.load(TOKEN)["revision"] == revision


@pytest.mark.parametrize("payload, match", [
    ({"callout_ids": []}, "kimlikleri listesi gerekli"),
    ({"callout_ids": "k1"}, "kimlikleri listesi gerekli"),
    ({"callout_ids": ["k1", "k1"]}, "iki kez"),
    ({"callout_ids": ["k1", 7]}, "metin olmalı"),
    ({"callout_ids": ["k1", ""]}, "metin olmalı"),
    ({"callout_ids": ["k1", "ghost"]}, "böyle bir callout yok"),
])
def test_a_bulk_scope_decision_validates_its_payload_before_any_write(store, payload, match):
    _three_undecided(store)
    before, revision = bytes_of(store), store.load(TOKEN)["revision"]
    with pytest.raises(ValueError, match=match):
        command(store, "set_ignored_many", payload)
    assert bytes_of(store) == before and store.load(TOKEN)["revision"] == revision


def test_undo_brings_every_bulk_ignored_callout_back(store):
    _three_undecided(store)
    after_bulk = command(store, "set_ignored_many", {"callout_ids": ["k1", "k2", "k3"]})
    state = store.save(TOKEN, after_bulk["revision"], undo=True)
    assert state["revision"] == after_bulk["revision"] + 1
    assert reviews_of(store) == {}
    assert not any(row["ignored"] for row in rows_of(state).values())


# --- transcribe + accept_hint: the single click is the user's, and the log names the hint --------

def test_accepting_a_machine_hint_writes_the_text_and_names_the_hint_in_the_log(store):
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[helpers._candidate_row(record, "k1", machine_text_hint=HINT)])
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": HINT, "accept_hint": True})
    stored = store.load(TOKEN)["decisions"]["transcriptions"]
    assert len(stored) == 1 and stored[0]["raw_text"] == HINT and stored[0]["entered_by"] == "user"
    events = [row for row in log_of(store) if row["action"] == "transcribe"]
    assert len(events) == 1
    assert events[0]["evidence"]["accepted_hint"] is True
    assert events[0]["evidence"]["machine_text_hint"] == HINT
    assert "ipucu" in events[0]["note"].lower()
    assert state["callouts"][0]["transcription"]["state"] == "current"


def test_an_accepted_hint_is_an_ordinary_transcription_for_the_parse_chain(store):
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[helpers._candidate_row(record, "k1", machine_text_hint=HINT)])
    command(store, "transcribe", {"callout_id": "k1", "raw_text": HINT, "accept_hint": True})
    parses = [row for row in store.load(TOKEN)["callout_parses"] if row["callout_id"] == "k1"]
    assert len(parses) == 1
    assert parses[0]["status"] == "parsed" and parses[0]["count"] == 4 and parses[0]["size"] == 8.0
    assert parses[0]["parser_version"] == CALLOUT_PARSER_VERSION


def test_a_hint_acceptance_whose_text_is_not_the_hint_is_refused(store):
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[helpers._candidate_row(record, "k1", machine_text_hint=HINT)])
    before = bytes_of(store)
    with pytest.raises(ValueError, match="birebir aynı"):
        command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8", "accept_hint": True})
    assert bytes_of(store) == before
    assert (store.load(TOKEN)["decisions"].get("transcriptions") or []) == []


def test_a_hint_acceptance_is_refused_when_the_callout_has_no_hint(store):
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[helpers._candidate_row(record, "k1")])
    before = bytes_of(store)
    with pytest.raises(ValueError, match="makine ipucu yok"):
        command(store, "transcribe", {"callout_id": "k1", "raw_text": "4x Ø8", "accept_hint": True})
    assert bytes_of(store) == before
    assert (store.load(TOKEN)["decisions"].get("transcriptions") or []) == []


def test_a_hint_flag_that_is_not_a_boolean_is_refused(store):
    record = store.load(TOKEN)
    helpers.seed_callouts(store, candidates=[helpers._candidate_row(record, "k1", machine_text_hint=HINT)])
    before = bytes_of(store)
    with pytest.raises(ValueError, match="true/false"):
        command(store, "transcribe", {"callout_id": "k1", "raw_text": HINT, "accept_hint": "yes"})
    assert bytes_of(store) == before
    assert (store.load(TOKEN)["decisions"].get("transcriptions") or []) == []


def test_the_ordinary_transcription_path_does_not_gain_the_flag(store):
    """Bilinçli yazım tarafı değişmedi: bayraksız transcribe aynen eskisi gibi çalışır."""
    _three_undecided(store)
    state = command(store, "transcribe", {"callout_id": "k1", "raw_text": "Ø10 DELIK"})
    assert state["callouts"][0]["transcription"]["state"] == "current"
    events = [row for row in log_of(store) if row["action"] == "transcribe"]
    assert len(events) == 1 and "accepted_hint" not in events[0]["evidence"]
    assert json.loads(json.dumps(store.load(TOKEN)["decisions"]["transcriptions"][0]["raw_text"])) == "Ø10 DELIK"
