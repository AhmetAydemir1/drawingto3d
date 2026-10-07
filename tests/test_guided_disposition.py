"""G12.1 — disposition komutları ve kayıt yolu (PLAN-24 §11/§12/§13/§17).

Store katmanı: `set_disposition` (üç claim + geri alma), eski düğmelerin yeni anlamı
(`set_ignored` → not_model_input, `set_unbindable` → build_relevant_unsupported), toplu karar
(`bulk_set_ignored` yalnız 'modele ait değil' yazar), komşu düzenlemelerin kararı düşürmemesi,
revizyon çakışması, dışa/içe aktarma ve eski kaydın (legacy) bloklaması.
"""
import json

import pytest

import test_guided_callouts as helpers
from drawingto3d import callout_readiness
from drawingto3d.guided import GuidedStore

TOKEN = helpers.TOKEN


@pytest.fixture
def store(tmp_path):
    return helpers.store.__wrapped__(tmp_path)


def _revision(store):
    return store.load(TOKEN)["revision"]


def _command(store, action, payload=None):
    return store.edit_callout(TOKEN, _revision(store), action, payload or {})


def _review(store, callout_id="k1"):
    record = store.load(TOKEN)
    return next((row for row in record["decisions"].get("callout_reviews") or []
                 if row.get("callout_id") == callout_id), None)


def _transcribed(store, raw="80,00"):
    """Bir callout: metin yazılmış, hedefi yok — kapsam kararı vermeden build açılmaz."""
    helpers.seed_callouts(store)
    return _command(store, "transcribe", {"callout_id": "k1", "raw_text": raw})


def _write_review(store, row):
    """Elle kayıt cerrahisi: eski sürümün yazdığı gibi bir gözden geçirme satırı (legacy)."""
    record = store.load(TOKEN)
    record["decisions"]["callout_reviews"] = [
        item for item in record["decisions"].get("callout_reviews") or []
        if item.get("callout_id") != row["callout_id"]]
    record["decisions"]["callout_reviews"].append(row)
    helpers._atomic(helpers._session_path(store), record)
    return record


# --- set_disposition: üç claim, tek kapı (PLAN-24 §13) ---------------------------------------

def test_set_disposition_writes_the_claim_and_names_it_in_the_log(store):
    _transcribed(store)
    before = _revision(store)
    state = _command(store, "set_disposition", {"callout_id": "k1", "disposition": "not_model_input"})
    assert state["revision"] == before + 1
    review = _review(store)
    assert review["disposition"] == "not_model_input"
    assert review["ignored"] is False and review["unbindable"] is False
    assert review.get("duplicate_of") is None and review.get("disposition_reason") is None
    record = store.load(TOKEN)
    event = next(item for item in record["log"] if item["action"] == "set_callout_disposition")
    assert event["actor"] == "user" and "modele ait değil" in event["note"]
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is True, readiness["questions_text"]
    assert readiness["coverage"]["not_model_input"] == ["k1"]
    assert readiness["coverage"]["coverage_complete"] is True


def test_set_disposition_refuses_unknown_vocabulary_and_missing_pieces(store):
    _transcribed(store)
    before = _revision(store)
    for payload, needle in (
            ({"callout_id": "k1", "disposition": "ignore"}, "olmalı"),
            ({"callout_id": "k1", "disposition": "redundant"}, "dayanağını"),
            ({"callout_id": "k1", "disposition": "build_relevant_unsupported"}, "gerekçesiz"),
            ({"callout_id": "k1", "disposition": "redundant", "duplicate_of": "hayalet"}, "yok"),
            ({"callout_id": "k1", "disposition": "redundant", "duplicate_of": "k1"}, "kendini"),
            ({"callout_id": "k1", "disposition": "redundant", "duplicate_of": "decision:view"},
             "karar yok")):
        with pytest.raises(ValueError) as error:
            _command(store, "set_disposition", payload)
        assert needle in str(error.value), payload
    assert _revision(store) == before, "reddedilen komut revizyonu ilerletmez"
    assert _review(store) is None, "reddedilen komut kayda geçmez"


def test_redundant_with_a_present_decision_reference_is_a_settled_claim(store):
    _transcribed(store)
    _command(store, "set_disposition",
             {"callout_id": "k1", "disposition": "redundant", "duplicate_of": "decision:calibration"})
    review = _review(store)
    assert review["disposition"] == "redundant" and review["duplicate_of"] == "decision:calibration"
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is True
    assert readiness["coverage"]["redundant"] == ["k1"] and readiness["coverage"]["invalid_duplicate"] == []


def test_redundant_naming_a_foreign_or_self_callout_is_refused(store):
    helpers.seed_callouts(store)
    before = _revision(store)
    with pytest.raises(ValueError) as error:
        _command(store, "set_disposition",
                 {"callout_id": "k1", "disposition": "redundant", "duplicate_of": "k9"})
    assert "callout yok" in str(error.value)
    assert _revision(store) == before


def test_build_relevant_unsupported_is_written_and_blocks_the_build(store):
    _transcribed(store)
    _command(store, "set_disposition", {"callout_id": "k1",
                                        "disposition": "build_relevant_unsupported",
                                        "disposition_reason": "yazılı daralma ölçüsü; hedefi yok"})
    review = _review(store)
    assert review["disposition"] == "build_relevant_unsupported"
    assert review["disposition_reason"] == "yazılı daralma ölçüsü; hedefi yok"
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is False
    assert [q["category"] for q in readiness["questions"]] == ["unsupported_build_relevant"]
    assert "k1" in readiness["questions"][0]["text"]
    with pytest.raises(ValueError) as error:
        store.build(TOKEN, _revision(store))
    assert "k1" in str(error.value)
    assert store.load(TOKEN)["build"] is None


def test_clearing_a_disposition_opens_the_scope_again(store):
    _transcribed(store)
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "not_model_input"})
    assert store.readiness(TOKEN)["ready"] is True
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": None})
    assert _review(store) is None, "karar geri alınınca kayıt satırı da gider"
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is False, "metin var, hedef yok: kapsam yeniden açılır"
    assert readiness["coverage"]["unclassified"] == ["k1"]


# --- eski düğmelerin yeni anlamı (PLAN-24 §11) -----------------------------------------------

def test_set_ignored_and_restore_speak_the_new_contract(store):
    _transcribed(store)
    _command(store, "set_ignored", {"callout_id": "k1", "ignored": True})
    review = _review(store)
    assert review["ignored"] is True and review["disposition"] == "not_model_input"
    assert store.readiness(TOKEN)["ready"] is True
    _command(store, "set_ignored", {"callout_id": "k1", "ignored": False})
    assert _review(store) is None
    assert store.readiness(TOKEN)["ready"] is False
    assert "karar" not in store.readiness(TOKEN)["coverage"]


def test_set_unbindable_defaults_a_reason_and_restore_clears_the_claim(store):
    _transcribed(store)
    _command(store, "set_unbindable", {"callout_id": "k1", "unbindable": True})
    review = _review(store)
    assert review["unbindable"] is True
    assert review["disposition"] == "build_relevant_unsupported"
    assert "bağlanamıyor" in review["disposition_reason"]
    assert store.readiness(TOKEN)["ready"] is False
    _command(store, "set_unbindable", {"callout_id": "k1", "unbindable": False})
    assert _review(store) is None
    assert store.readiness(TOKEN)["ready"] is False          # metin/hedef hâlâ eksik


def test_set_unbindable_carries_the_reviewers_own_reason(store):
    _transcribed(store)
    _command(store, "set_unbindable", {"callout_id": "k1", "unbindable": True,
                                       "disposition_reason": "Ø50 cep derinliği bu sürümde yok"})
    assert _review(store)["disposition_reason"] == "Ø50 cep derinliği bu sürümde yok"


# --- toplu karar: asla 'gerçek ama uygulanamaz' demez (PLAN-24 §14) --------------------------

def _three_candidates(store):
    record = store.load(TOKEN)
    rows = []
    for index, text in enumerate(("80,00", "15,00", "A4"), start=1):
        rows.append(dict(helpers._candidate_row(record, f"k{index}"), machine_text_hint=text))
    helpers.seed_callouts(store, candidates=rows)
    return ["k1", "k2", "k3"]


def test_bulk_set_ignored_writes_not_model_input_for_every_row(store):
    ids = _three_candidates(store)
    _command(store, "bulk_set_ignored", {"callout_ids": ids, "ignored": True})
    record = store.load(TOKEN)
    reviews = {row["callout_id"]: row for row in record["decisions"]["callout_reviews"]}
    assert set(reviews) == set(ids)
    assert {row["disposition"] for row in reviews.values()} == {"not_model_input"}
    assert all(row["ignored"] is True for row in reviews.values())
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is True
    assert sorted(readiness["coverage"]["not_model_input"]) == ids
    assert readiness["coverage"]["build_relevant_unsupported"] == []


def test_bulk_restore_clears_only_the_not_model_input_claim(store):
    ids = _three_candidates(store)
    _command(store, "bulk_set_ignored", {"callout_ids": ids, "ignored": True})
    _command(store, "set_disposition", {"callout_id": "k3",
                                        "disposition": "build_relevant_unsupported",
                                        "disposition_reason": "gerçek ölçü; hedefi yok"})
    _command(store, "bulk_set_ignored", {"callout_ids": ids, "ignored": False})
    record = store.load(TOKEN)
    reviews = {row["callout_id"]: row for row in record["decisions"]["callout_reviews"]}
    assert set(reviews) == {"k3"}, "yalnız 'modele ait değil' geri alınır"
    assert reviews["k3"]["disposition"] == "build_relevant_unsupported", \
        "gerçek ama uygulanamaz kararı toplu geri alma kazara silmez"
    assert reviews["k3"]["ignored"] is False
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is False
    assert readiness["coverage"]["build_relevant_unsupported"] == ["k3"]


def test_set_ignored_many_also_only_ever_claims_not_model_input(store):
    ids = _three_candidates(store)
    _command(store, "set_ignored_many", {"callout_ids": ids})
    reviews = {row["callout_id"]: row for row in store.load(TOKEN)["decisions"]["callout_reviews"]}
    assert {row["disposition"] for row in reviews.values()} == {"not_model_input"}
    with pytest.raises(ValueError):
        _command(store, "set_ignored_many", {"callout_ids": ["k1"]})   # karara bağlanmış satır: ret


# --- komşu düzenlemeler kararı düşürmez (PLAN-24 §11 son paragraf) ---------------------------

def test_a_neighbouring_edit_never_drops_a_disposition(store):
    _transcribed(store)
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "redundant",
                                        "duplicate_of": "decision:calibration"})
    _command(store, "edit_region", {"callout_id": "k1", "region": [0.12, 0.2, 0.42, 0.5]})
    review = _review(store)
    assert review["disposition"] == "redundant" and review["duplicate_of"] == "decision:calibration"
    assert review["region_override"] == [0.12, 0.2, 0.42, 0.5]
    _command(store, "transcribe", {"callout_id": "k1", "raw_text": "15,00"})
    review = _review(store)
    assert review["disposition"] == "redundant", "metin düzeltmesi claim'i düşürmez"
    assert store.readiness(TOKEN)["ready"] is True
    reopened = GuidedStore(store.root)
    assert reopened.load(TOKEN)["decisions"]["callout_reviews"][0]["disposition"] == "redundant"


def test_undo_steps_the_disposition_back_and_keeps_the_earlier_one(store):
    _transcribed(store)
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "not_model_input"})
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "redundant",
                                        "duplicate_of": "decision:calibration"})
    revision = _revision(store)
    state = store.save(TOKEN, revision, helpers.current_payload(store), undo=True)
    assert state["revision"] == revision + 1
    assert _review(store)["disposition"] == "not_model_input", "geri alma bir adım geri gider"
    assert store.readiness(TOKEN)["ready"] is True


def test_a_revision_conflict_leaves_the_claim_unwritten(store):
    _transcribed(store)
    before = helpers._session_path(store).read_bytes()
    with pytest.raises(ValueError) as error:
        store.edit_callout(TOKEN, 0, "set_disposition",
                           {"callout_id": "k1", "disposition": "not_model_input"})
    assert "oturum değişti" in str(error.value)
    assert helpers._session_path(store).read_bytes() == before
    assert _review(store) is None


# --- dışa/içe aktarma: aynı doğrulama (PLAN-24 §17) ------------------------------------------

def test_export_carries_the_disposition_and_import_applies_it_on_the_same_path(store):
    _transcribed(store)
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "redundant",
                                        "duplicate_of": "decision:calibration"})
    bundle = store.review_export(TOKEN)
    row = next(item for item in bundle["callouts"] if item["callout_id"] == "k1")
    assert row["disposition"] == "redundant" and row["duplicate_of"] == "decision:calibration"

    importable = {key: bundle[key] for key in ("bundle_version", "schema_version", "session", "base_revision",
                                               "source_digest", "parser_version", "geometry_version",
                                               "geometry_key")}
    importable["actions"] = [{"action": "set_disposition", "callout_id": "k1",
                              "disposition": "build_relevant_unsupported",
                              "disposition_reason": "dış inceleme: bu bilgi modelde yok"}]
    revision = _revision(store)
    state = store.review_import(TOKEN, revision, importable)
    assert state["revision"] == revision + 1
    review = _review(store)
    assert review["disposition"] == "build_relevant_unsupported"
    assert review["disposition_reason"] == "dış inceleme: bu bilgi modelde yok"
    event = [item for item in store.load(TOKEN)["log"]
             if item["action"] == "set_callout_disposition"][-1]
    assert event["actor"] == "external_review"
    assert store.readiness(TOKEN)["ready"] is False


def test_import_refuses_a_bad_disposition_whole(store):
    _transcribed(store)
    bundle = store.review_export(TOKEN)
    before = helpers._session_path(store).read_bytes()
    for bad in ({"action": "set_disposition", "callout_id": "k1", "disposition": "ignore"},
                {"action": "set_disposition", "callout_id": "k1", "disposition": "redundant"},
                {"action": "set_disposition", "callout_id": "k1", "disposition": "redundant",
                 "duplicate_of": "decision:view"},
                {"action": "set_disposition", "callout_id": "k1", "disposition": "redundant",
                 "duplicate_of": "hayalet"},
                {"action": "set_disposition", "callout_id": "k1",
                 "disposition": "build_relevant_unsupported"}):
        attempt = {key: bundle[key] for key in ("bundle_version", "schema_version", "session",
                                                "base_revision", "source_digest", "parser_version",
                                                "geometry_version", "geometry_key")}
        attempt["actions"] = [bad]
        with pytest.raises(ValueError) as error:
            store.review_import(TOKEN, _revision(store), attempt)
        assert "içe aktarma reddedildi" in str(error.value)
    assert helpers._session_path(store).read_bytes() == before
    assert _review(store) is None


# --- genel durum kapsamı taşır (PLAN-25 §15): tarayıcı kendi kapsam motorunu kurmaz ----------

def test_the_public_state_carries_the_coverage_audit(store):
    _transcribed(store)
    public = store.public(store.load(TOKEN))
    assert public["coverage"]["unclassified"] == ["k1"]
    assert public["coverage"]["counts"]["unclassified"] == 1
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "redundant",
                                        "duplicate_of": "decision:calibration"})
    public = store.public(store.load(TOKEN))
    assert public["coverage"]["redundant"] == ["k1"]
    assert public["coverage"]["counts"]["unclassified"] == 0
    assert public["coverage"]["counts"]["redundant"] == 1


# --- legacy kayıt: kanıtsız, bloklar (PLAN-24 §12) -------------------------------------------

def test_a_legacy_ignored_record_blocks_until_the_user_reviews_it_again(store):
    helpers.seed_callouts(store)
    _write_review(store, {"callout_id": "k1", "ignored": True, "revision": 1})
    readiness = store.readiness(TOKEN)
    assert readiness["ready"] is False
    assert readiness["coverage"]["legacy_unclassified"] == ["k1"]
    assert [q["category"] for q in readiness["questions"]] == ["legacy_unclassified"]
    with pytest.raises(ValueError) as error:
        store.build(TOKEN, _revision(store))
    assert "k1" in str(error.value)
    _command(store, "set_disposition", {"callout_id": "k1", "disposition": "not_model_input"})
    assert store.readiness(TOKEN)["ready"] is True


def test_legacy_rows_are_never_promoted_by_a_neighbouring_edit(store):
    helpers.seed_callouts(store)
    _write_review(store, {"callout_id": "k1", "unbindable": True, "revision": 1})
    _command(store, "edit_region", {"callout_id": "k1", "region": [0.12, 0.2, 0.42, 0.5]})
    review = _review(store)
    assert review.get("disposition") is None, "eski bayrak claim'e terfi etmez"
    assert review["unbindable"] is True
    assert store.readiness(TOKEN)["coverage"]["legacy_unclassified"] == ["k1"]
    assert callout_readiness.build_readiness(store.load(TOKEN))["ready"] is False
