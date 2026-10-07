"""G5/G8/G6/GX on the store and over the real HTTP boundary.

The modules have their own pure tests; here the questions are the *integration* ones: is the proposal
a read, does a declared "cannot bind" decision really unblock the callout, does the compiled chain
reach the plan the build hands to CAD, and does an imported review travel the same validated path a
click does — with `external_review` as its provenance and nothing written on refusal.
"""
import copy
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import pytest

import test_guided_callouts as helpers
import test_view_core as view_helpers
from drawingto3d import app, callout_bind, callout_compile, callout_models, callout_review, guided
from drawingto3d.callout_parse import semantic_parse

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


# --- R01/R02/R04/R05 — bağımsız inceleme düzeltme turu (2026-10-07) --------------------------

def _store_in(tmp_path, name, text, *, inches=False):
    """İncelemenin kendi fixture'ı: sentetik oturum, (inç kalibrasyon) ve metnin gerçek store
    komutuyla yazılışı — parse okuması gerçek parser yolundan türetilir."""
    folder = tmp_path / name
    folder.mkdir()
    fixture = helpers.store.__wrapped__(folder)
    helpers.seed_callouts(fixture)
    if inches:
        payload = helpers.current_payload(fixture)
        payload["calibration"] = {**payload["calibration"], "value": 50 / 25.4, "unit": "in"}
        fixture.save(TOKEN, 0, payload)
    fixture.edit_callout(TOKEN, fixture.load(TOKEN)["revision"], "transcribe",
                         {"callout_id": "k1", "raw_text": text})
    return fixture


def _confirm(fixture, kind, ids):
    """Hedefi kaydet ve derlenmiş zinciri gerçek GeneralPlan'a kadar çalıştır."""
    state = fixture.load(TOKEN)
    payload = helpers.current_payload(fixture, holes=[])
    payload["callout_targets"] = [helpers._target_payload(
        target_kind=kind, target_ids=ids,
        transcription_revision=state["decisions"]["transcriptions"][0]["revision"])]
    fixture.save(TOKEN, state["revision"], payload)
    state = fixture.load(TOKEN)
    compilation = callout_compile.compile_callouts(state)
    merged = callout_compile.apply_compiled(state["decisions"], compilation)
    return state, compilation, guided.make_plan({**state, "decisions": merged})


def _bbox(plan):
    edges = {name: float(value.value) for name, value in plan.parameters.items()
             if name.startswith("edge_")}
    xs = [value for name, value in edges.items() if name.endswith("_x")]
    ys = [value for name, value in edges.items() if name.endswith("_y")]
    return [max(xs) - min(xs), max(ys) - min(ys)]


def _with_callout_on(record, *, text, ids, region=(0.10, 0.20, 0.20, 0.32)):
    """İnceleme kaydına callout katmanı ekle: aday + gerçek parse + onaylı hedef (G5-G7 şekli)."""
    record["callout_candidates"] = [{"id": "k1", "source_digest": record["source_sha256"], "page_index": 0,
                                     "region": list(region), "crop_region": list(region),
                                     "source_kind": "vector_text", "observation_ids": [],
                                     "detector_version": "callout-detector/1",
                                     "geometry_version": record["geometry_version"],
                                     "machine_text_hint": text}]
    record["decisions"]["transcriptions"] = [{"callout_id": "k1", "raw_text": text, "normalized_text": text,
                                              "entered_by": "user", "source_region": list(region),
                                              "revision": 1}]
    record["callout_parses"] = [semantic_parse({"callout_id": "k1", "raw_text": text, "revision": 1},
                                               sheet_unit="mm").model_dump(mode="json")]
    target = {"callout_id": "k1", "transcription_revision": 1, "target_kind": "vertex_pair",
              "target_ids": list(ids), "profile_id": record["decisions"]["profile_id"],
              "parser_version": callout_models.CALLOUT_PARSER_VERSION,
              "geometry_version": record["geometry_version"],
              "evidence": [{"kind": "user_click", "ref": ids[0]}], "status": "confirmed",
              "reconfirm": False}
    target["geometry_key"] = callout_models.geometry_key(record)
    record["decisions"]["callout_targets"] = [target]
    return record


def test_a_vertical_callout_tie_leaves_the_plan_upright(tmp_path):
    """R01: (120,20) → (120,80) dik kenara `30 mm` — yön parça çerçevesinde -1, plan 50×30 mm kalır."""
    fixture = _store_in(tmp_path, "vertical", "30 mm")
    _state, compilation, plan = _confirm(fixture, "vertex_pair", ["g1:start", "g1:end"])
    binding = compilation["bindings"][0]
    assert fixture.readiness(TOKEN)["ready"] is True
    assert (binding["axis"], binding["direction"]) == ("y", -1)
    assert _bbox(plan) == [50.0, 30.0]


def test_a_horizontal_callout_tie_is_the_untouched_control(tmp_path):
    """R01 kontrolü: yatay `50 mm` doğruydu ve düzeltmeden sonra da aynı kalır."""
    fixture = _store_in(tmp_path, "horizontal", "50 mm")
    _state, compilation, plan = _confirm(fixture, "vertex_pair", ["g0:start", "g0:end"])
    binding = compilation["bindings"][0]
    assert (binding["axis"], binding["direction"]) == ("x", 1)
    assert _bbox(plan) == [50.0, 30.0]


def test_a_rotated_sheet_reads_the_tie_in_the_sheets_own_frame(tmp_path):
    """R01: çeyrek tur dönmüş pafta — bağ paftanın kendi ekseninden okunur; sadece dy işareti yetmez."""
    record = view_helpers._record(tmp_path, transpose=True, rotation=90, name="turned",
                                  view={"x_page": [0.0, 1.0], "y_page": [1.0, 0.0], "source": "sheet_frame"})
    _with_callout_on(record, text="30 mm", ids=["g1:start", "g1:end"])
    compiled = callout_compile.compile_callouts(record)
    binding = compiled["bindings"][0]
    assert (binding["axis"], binding["direction"]) == ("y", 1)
    plan = guided.make_plan({**record, "decisions": callout_compile.apply_compiled(record["decisions"],
                                                                                   compiled)})
    assert _bbox(plan) == [50.0, 30.0]


def test_a_printed_inch_blind_depth_reaches_the_plan_in_mm(tmp_path):
    """R02: `Ø.5 .25 DEEP in` — GeneralPlan'da çap 12.7 mm, derinlik 6.35 mm."""
    fixture = _store_in(tmp_path, "printed_inch", "Ø.5 .25 DEEP in")
    _state, compilation, plan = _confirm(fixture, "circle", ["c0"])
    assert fixture.readiness(TOKEN)["ready"] is True
    assert compilation["holes"][0]["diameter"] == 12.7
    assert float(plan.parameters["hole_0_depth"].value) == 6.35


def test_a_sheet_inch_blind_depth_reaches_the_plan_in_mm(tmp_path):
    """R02: birimsiz metin, kalibrasyondan çözülen `in` — derinlik yine 6.35 mm."""
    fixture = _store_in(tmp_path, "sheet_inch", "Ø.5 .25 DEEP", inches=True)
    state, compilation, plan = _confirm(fixture, "circle", ["c0"])
    assert state["decisions"]["calibration"]["unit"] == "in"
    assert compilation["rows"][0]["unit_source"] == "sheet"
    assert float(plan.parameters["hole_0_depth"].value) == 6.35


def _attempt_confirm(fixture, *, kind="circle", ids=("c0",)):
    """Kullanıcının onay denemesi: kayıt öncesi/sonrası bayt karşılaştırmasıyla."""
    state = fixture.load(TOKEN)
    before = helpers._session_path(fixture).read_bytes()
    payload = helpers.current_payload(fixture)
    payload["callout_targets"] = [helpers._target_payload(
        target_kind=kind, target_ids=list(ids),
        transcription_revision=state["decisions"]["transcriptions"][0]["revision"])]
    error = None
    try:
        fixture.save(TOKEN, state["revision"], payload)
    except ValueError as exc:
        error = str(exc)
    return error, helpers._session_path(fixture).read_bytes() == before


def test_an_unsupported_reading_asks_for_a_text_edit_not_a_target(tmp_path):
    """R04: gerçek akış — `M8` okuması unsupported; hazırlık parse_error der, onay yine reddedilir."""
    fixture = _store_in(tmp_path, "unsupported", "M8")
    assert fixture.load(TOKEN)["callout_parses"][0]["status"] == "unsupported"
    readiness = fixture.readiness(TOKEN)
    assert readiness["categories"] == {"parse_error": 1}
    assert "missing_target" not in readiness["categories"]
    assert readiness["questions"][0]["action"] == "edit_transcription"
    error, untouched = _attempt_confirm(fixture)
    assert error and untouched, "store onayı haklı reddeder ve dosyaya yazmaz"


def test_an_ambiguous_reading_asks_for_a_text_edit_not_a_target(tmp_path):
    fixture = _store_in(tmp_path, "ambiguous", "Ø8 9")
    assert fixture.load(TOKEN)["callout_parses"][0]["status"] == "ambiguous"
    readiness = fixture.readiness(TOKEN)
    assert readiness["categories"] == {"parse_ambiguous": 1}
    assert "missing_target" not in readiness["categories"]
    error, untouched = _attempt_confirm(fixture)
    assert error and untouched


def _bundle_for(fixture):
    bundle = fixture.review_export(TOKEN)
    bundle["actions"] = [{"action": "confirm_target", "callout_id": "k1",
                          "target_kind": "circle", "target_ids": ["c0"]}]
    return bundle


def _attempt_import(fixture, bundle):
    state = fixture.load(TOKEN)
    before = helpers._session_path(fixture).read_bytes()
    error = None
    try:
        fixture.review_import(TOKEN, state["revision"], bundle)
    except ValueError as exc:
        error = str(exc)
    return error, helpers._session_path(fixture).read_bytes() == before


def test_an_import_of_the_same_context_still_lands_and_undo_restores(tmp_path):
    """R05 kontrolü: bağlam aynıyken import eskisi gibi uygulanır; undo kararları aynen geri getirir."""
    fixture = _store_in(tmp_path, "current_control", "Ø8 THRU")
    bundle = _bundle_for(fixture)
    before = fixture.load(TOKEN)
    error, _wrote = _attempt_import(fixture, bundle)
    assert error is None, error
    imported = fixture.load(TOKEN)
    assert callout_models.callout_states(imported)[0]["target"]["state"] == "current"
    fixture.save(TOKEN, imported["revision"], undo=True)
    undone = fixture.load(TOKEN)
    assert undone["decisions"] == before["decisions"]
    assert undone["revision"] > imported["revision"] > before["revision"]


def test_a_bundle_from_an_obsolete_parser_header_is_refused_whole(tmp_path):
    """R05: paketin başlığı sunucunun parser sürümü değilse import tamamıyla reddedilir."""
    fixture = _store_in(tmp_path, "old_parser", "Ø8 THRU")
    bundle = _bundle_for(fixture)
    bundle["parser_version"] = "callout-parser/obsolete"
    error, untouched = _attempt_import(fixture, bundle)
    assert error and "parser_version_mismatch" in error
    assert untouched and not fixture.load(TOKEN)["decisions"].get("callout_targets")


def test_a_bundle_exported_before_a_geometry_migration_is_refused_whole(tmp_path):
    """R05: base revision eşit kalsa da geometri bağlamı değiştiyse eski paket onay yazamaz."""
    fixture = _store_in(tmp_path, "migrated", "Ø8 THRU")
    bundle = _bundle_for(fixture)
    original = fixture.load(TOKEN)
    fresh = copy.deepcopy(original["options"])
    next(row for row in fresh["circles"] if row["id"] == "c0")["center"] = [70, 45]
    with patch.object(guided, "GEOMETRY_VERSION", original["geometry_version"] + 1), \
            patch.object(guided, "observe", return_value=None), \
            patch.object(guided, "drawing_options", return_value=fresh):
        migrated = fixture.load(TOKEN)                # gerçek migration yazısı (meşru, revision'ı artırmaz)
        error, untouched = _attempt_import(fixture, bundle)   # anlık görüntü: migration sonrası, import öncesi
    assert migrated["geometry_version"] == original["geometry_version"] + 1
    assert callout_models.geometry_key(original) != callout_models.geometry_key(migrated)
    assert bundle["base_revision"] == migrated["revision"], "kontrol yalnız revision'a bakmıyor"
    assert error and "geometry" in error
    assert untouched, "reddedilen import migration'ın kendi yazısından sonra dosyaya dokunmaz"
    assert not fixture.load(TOKEN)["decisions"].get("callout_targets")
