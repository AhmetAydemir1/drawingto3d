"""G1 store behaviour (PLAN-20 §6–§8): the callout records through the real `GuidedStore`.

Everything here runs on a synthetic vector sheet — one wire, two circles and a border — through
create/load/save/undo/accept/build, no PDF and no CAD where not needed. Parse fixtures are seeded
as session records the store reads; G1 has no parser and no store API may fake one.
"""
import hashlib
import json
import threading
from pathlib import Path

import pytest

from drawingto3d import callout_models, contour_audit, guided
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION
from drawingto3d.guided import GuidedStore, _atomic, drawing_options
from drawingto3d.observe import Observations

TOKEN = "a" * 32


def _base_record(tmp_path):
    primitives = []
    points = [[20, 20], [120, 20], [120, 80], [20, 80]]
    for i, point in enumerate(points):
        primitives.append(dict(id=f"g{i}", path_id=f"p{i}", kind="line", start=point,
                               end=points[(i + 1) % 4]))
    for i, centre in enumerate([[45, 45], [90, 50]]):
        primitives.append(dict(id=f"c{i}", path_id=f"cp{i}", kind="circle", centre=centre, radius=6))
    border = [[10, 10], [290, 10], [290, 190], [10, 190]]
    for i, point in enumerate(border):
        primitives.append(dict(id=f"g{4 + i}", path_id=f"b{i}", kind="line", start=point,
                               end=border[(i + 1) % 4]))
    inner = [[40, 40], [100, 40], [100, 60], [40, 60]]
    for i, point in enumerate(inner):
        primitives.append(dict(id=f"n{i}", path_id=f"n{i}", kind="line", start=point,
                               end=inner[(i + 1) % 4]))
    source = tmp_path / "source.pdf"
    source.write_bytes(b"fixture-source-hash")
    observations = Observations(source={"ref": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
                                frame={"width": 300, "height": 200}, text_placement="as-is",
                                primitives=primitives)
    options = drawing_options(observations)
    wire = next(row["id"] for row in options["profiles"] if row["kind"] == "wire")
    return {"version": 1, "geometry_version": guided.GEOMETRY_VERSION, "token": TOKEN, "revision": 0,
            "source": str(source), "source_sha256": observations.source.sha256, "options": options,
            "decisions": {"calibration": {"first": [20, 20], "second": [120, 20], "value": 50, "unit": "mm"},
                          "profile_id": wire, "thickness": 10,
                          "holes": [{"circle_id": "c0", "kind": "through", "diameter": 6},
                                    {"circle_id": "c1", "kind": "pocket", "diameter": 10, "depth": 3}],
                          "trace_acknowledged": True},
            "history": [], "build": None}


@pytest.fixture
def store(tmp_path):
    record = _base_record(tmp_path)
    store = GuidedStore(tmp_path / "store")
    folder = store.folder(TOKEN)
    folder.mkdir(parents=True)
    _atomic(folder / "session.json", record)
    return store


def _session_path(store):
    return store.folder(TOKEN) / "session.json"


def seed_callouts(store, *, candidate=True, candidates=None, parses=None, targets=None,
                  proposals=None, history=None):
    """An open fixture: the way G2/G4 will one day write candidates and parse results."""
    record = store.load(TOKEN)
    if candidates is not None:
        record["callout_candidates"] = [dict(row) for row in candidates]
    elif candidate:
        record["callout_candidates"] = [{
            "id": "k1", "source_digest": record["source_sha256"], "page_index": 0,
            "region": [0.1, 0.2, 0.4, 0.5], "crop_region": [0.05, 0.15, 0.45, 0.55],
            "source_kind": "vector_text", "observation_ids": [],
            "detector_version": "callout-detector/1",
            "geometry_version": record["geometry_version"], "machine_text_hint": "4x Ø8 THRU"}]
    if parses is not None:
        record["callout_parses"] = [dict(row) for row in parses]
    if targets is not None:
        record["decisions"]["callout_targets"] = [dict(row) for row in targets]
    if proposals is not None:
        record["proposals"] = list(proposals)
    if history is not None:
        record["history"] = list(history)
    _atomic(_session_path(store), record)
    return record


def current_payload(store, *, with_callouts=True, **updates):
    """The client's full decisions payload, built from what the store currently holds."""
    data = json.loads(json.dumps(store.load(TOKEN)["decisions"]))
    if not with_callouts:
        data.pop("transcriptions", None)
        data.pop("callout_targets", None)
    data.update(updates)
    return data


def _fake_build(store):
    record = store.load(TOKEN)
    folder = store.folder(TOKEN) / "build-0-oldfolder"
    folder.mkdir(exist_ok=True)
    (folder / "part.step").write_bytes(b"old step")
    record["build"] = {"revision": record["revision"], "status": "complete", "folder": str(folder),
                       "source_sha256": record["source_sha256"],
                       "geometry_version": record["geometry_version"]}
    _atomic(_session_path(store), record)
    return folder


def _transcription(raw="  4 × Ø8 THRU  "):
    return {"callout_id": "k1", "raw_text": raw, "source_region": [0.1, 0.2, 0.4, 0.5],
            "entered_by": "user", "revision": 777}


def _candidate_row(record, callout_id, **over):
    row = {"id": callout_id, "source_digest": record["source_sha256"], "page_index": 0,
           "region": [0.1, 0.2, 0.4, 0.5], "crop_region": [0.05, 0.15, 0.45, 0.55],
           "source_kind": "observation", "observation_ids": [], "detector_version": "callout-detector/1",
           "geometry_version": record["geometry_version"], "machine_text_hint": None}
    row.update(over)
    return row


def _parse_row(**over):
    row = {"callout_id": "k1", "parser_version": CALLOUT_PARSER_VERSION, "transcription_revision": 1,
           "status": "parsed", "form": "diameter", "size": 8.0, "count": None, "termination": "thru",
           "depth": None, "unit": None, "warnings": []}
    row.update(over)
    return row


def _target_row(record, **over):
    row = {"callout_id": "k1", "target_kind": "circle", "target_ids": ["c0"],
           "geometry_version": record["geometry_version"],
           "geometry_key": callout_models.geometry_key(record),
           "profile_id": record["decisions"]["profile_id"], "transcription_revision": 1,
           "parser_version": CALLOUT_PARSER_VERSION,
           "evidence": [{"kind": "user_click", "ref": "c0"}], "status": "confirmed"}
    row.update(over)
    return row


def _target_payload(**over):
    """A client-side confirmation as the save boundary receives it — no server fields filled in."""
    row = {"callout_id": "k1", "target_kind": "circle", "target_ids": ["c0"],
           "transcription_revision": 1, "parser_version": CALLOUT_PARSER_VERSION,
           "evidence": [{"kind": "user_click", "ref": "c0"}]}
    row.update(over)
    return row


def _transcribed(store, parses=None):
    """k1 written down (revision 1) with parse fixtures seeded — the open fixture state."""
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    store.save(TOKEN, 0, payload)
    seed_callouts(store, candidate=False, parses=[_parse_row()] if parses is None else parses)
    return store.load(TOKEN)


# --- persistence and reopen ----------------------------------------------

def test_save_persists_a_transcription_and_reopen_keeps_raw_text(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription()]
    state = store.save(TOKEN, 0, payload)
    assert state["revision"] == 1
    row = state["decisions"]["transcriptions"][0]
    assert row["raw_text"] == "  4 × Ø8 THRU  "          # birebir, boşluklarıyla
    assert row["normalized_text"] == "4 × Ø8 THRU"       # sunucunun ayrı, deterministik alanı
    assert row["revision"] == 1                          # sunucunun atadığı kimlik, istemcinin 777'si değil

    on_disk = json.loads(_session_path(store).read_text())
    assert on_disk["decisions"]["transcriptions"][0]["raw_text"] == "  4 × Ø8 THRU  "

    reopened = GuidedStore(store.root)                   # fresh instance, same folder
    public = reopened.public(reopened.load(TOKEN))
    assert public["decisions"]["transcriptions"][0]["raw_text"] == "  4 × Ø8 THRU  "
    assert public["callout_schema_version"] == 3                   # G3: alan/yok sayma; G5-GX: arc/profile + bağlanamaz + external_review
    assert public["callouts"] == [{
        "id": "k1", "page_index": 0, "source_kind": "vector_text", "manual": False, "ignored": False,
        "unbindable": False,
        "transcription": {"state": "current", "revision": 1, "reason": None},
        "parse": {"state": "current", "reason": None},
        "target": {"state": "missing", "reason": "needs_target"}}]


def test_a_machine_text_hint_never_becomes_a_decision(store):
    seed_callouts(store)
    public = store.public(store.load(TOKEN))
    assert public["callouts"][0]["transcription"]["state"] == "missing"
    assert public["callouts"][0]["target"]["state"] == "missing"
    assert public["decisions"].get("transcriptions", []) == []
    state = store.save(TOKEN, 0, current_payload(store, with_callouts=False, thickness=12.0))
    assert state["decisions"]["transcriptions"] == []
    assert state["decisions"]["callout_targets"] == []
    assert state["callout_candidates"][0]["machine_text_hint"] == "4x Ø8 THRU"   # yalnız öneri kalır


def test_a_second_transcription_for_the_same_callout_is_refused(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(), _transcription(raw="Ø10")]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="aynı callout"):
        store.save(TOKEN, 0, payload)
    assert _session_path(store).read_bytes() == before


# --- old sessions and old clients -----------------------------------------

def test_an_old_session_opens_serves_its_build_and_is_not_rewritten(store):
    folder = _fake_build(store)
    before = _session_path(store).read_bytes()
    record = store.load(TOKEN)                                  # no exception, no migration write
    assert _session_path(store).read_bytes() == before
    public = store.public(record)
    assert public["build_status"] == "complete" and public["step"]
    assert public["callouts"] == []
    assert "transcriptions" not in public["decisions"]          # eski kayıt olduğu gibi okunur
    path, _kind = store.artifact(TOKEN, "part.step")
    assert path == folder / "part.step"

    saved = store.save(TOKEN, 0, current_payload(store, with_callouts=False))
    assert saved["revision"] == 0                               # yalnız boş varsayılanlar eklendi: no-op
    assert saved["build_status"] == "complete" and saved["step"]
    assert _session_path(store).read_bytes() == before          # dosya kıpırdamaz
    store.artifact(TOKEN, "part.step")                          # eski çıktı eskisi gibi sunulur


def test_missing_keys_keep_callout_decisions_and_explicit_empty_removes_them(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    assert store.save(TOKEN, 0, payload)["revision"] == 1

    old_client = current_payload(store, with_callouts=False, thickness=12.0)
    state = store.save(TOKEN, 1, old_client)                    # eksik anahtar = mevcut değeri koru
    assert state["revision"] == 2
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"

    explicit = current_payload(store)
    explicit["transcriptions"] = []                             # açık boş liste = kaldırma isteği
    state = store.save(TOKEN, 2, explicit)
    assert state["revision"] == 3 and state["decisions"]["transcriptions"] == []
    assert state["callouts"][0]["transcription"] == {"state": "missing", "revision": None,
                                                     "reason": "needs_transcription"}


def test_an_unknown_callout_is_refused_without_touching_the_record(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [{"callout_id": "ghost", "raw_text": "Ø8",
                                  "source_region": [0.1, 0.2, 0.4, 0.5], "entered_by": "user"}]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="callout yok"):
        store.save(TOKEN, 0, payload)
    assert _session_path(store).read_bytes() == before


# --- revision discipline ---------------------------------------------------

def test_a_stale_revision_save_is_refused_and_the_record_keeps_its_first_value(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    store.save(TOKEN, 0, payload)
    before = _session_path(store).read_bytes()
    stale = dict(payload, thickness=12.0)                       # hâlâ revision 0 üzerinden
    with pytest.raises(ValueError, match="oturum değişti"):
        store.save(TOKEN, 0, stale)
    assert _session_path(store).read_bytes() == before


def test_saving_the_same_transcription_again_is_a_noop(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    store.save(TOKEN, 0, payload)
    before = _session_path(store).read_bytes()
    history = len(store.load(TOKEN)["history"])
    log = len(store.load(TOKEN)["log"])
    state = store.save(TOKEN, 1, current_payload(store))        # birebir aynı karar kümesi
    assert state["revision"] == 1
    assert len(store.load(TOKEN)["history"]) == history
    assert len(store.load(TOKEN)["log"]) == log
    assert _session_path(store).read_bytes() == before


def test_an_unrelated_edit_bumps_the_session_but_not_the_transcription_revision(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    store.save(TOKEN, 0, payload)
    state = store.save(TOKEN, 1, current_payload(store, thickness=22.0))
    assert state["revision"] == 2
    assert state["decisions"]["transcriptions"][0]["revision"] == 1     # gereksiz yere yeniden yazılmaz


def test_undo_accepts_a_history_entry_without_the_new_fields(store):
    seed_callouts(store)
    old = current_payload(store, with_callouts=False)
    record = store.load(TOKEN)
    record["history"] = [old]
    record["revision"] = 1
    _atomic(_session_path(store), record)
    state = store.save(TOKEN, 1, undo=True)
    assert state["revision"] == 2
    assert state["decisions"]["thickness"] == 10
    assert state["decisions"].get("transcriptions", []) == []
    assert state["callouts"][0]["parse"]["state"] == "missing"          # çökme yok, boş state doğru


def test_accept_keeps_callout_decisions_and_confirms_nothing(store):
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="4x Ø8 THRU")]
    store.save(TOKEN, 0, payload)
    seed_callouts(store, candidate=False, proposals=[
        {"field": "thickness", "value": 12.0, "confidence": "rule", "evidence": {"rule": "fixture"}},
        {"field": "callout:k1", "value": "4x Ø8 THRU", "confidence": "hint",
         "evidence": {"rule": "machine_text_hint"}},
    ])
    state = store.accept(TOKEN, 1)
    assert state["decisions"]["thickness"] == 12.0
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"
    assert state["decisions"]["callout_targets"] == []                  # metin ipucu onay sayılmaz
    assert state["callouts"][0]["transcription"]["state"] == "current"
    assert state["callouts"][0]["target"]["state"] == "missing"


# --- targets, parse freshness and rejections (T06/T09/T10/T11/T12/T17/T21) --

def test_a_target_confirmation_is_pinned_and_current(store):
    _transcribed(store)
    key = callout_models.geometry_key(store.load(TOKEN))
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    state = store.save(TOKEN, 1, payload)
    record = store.load(TOKEN)
    stored = state["decisions"]["callout_targets"][0]
    assert stored["geometry_key"] == key                                  # sunucu pinledi
    assert stored["geometry_version"] == record["geometry_version"]
    assert stored["profile_id"] == record["decisions"]["profile_id"]
    assert state["callouts"][0]["parse"] == {"state": "current", "reason": None}
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}

    reopened = GuidedStore(store.root)
    public = reopened.public(reopened.load(TOKEN))
    assert public["callouts"][0]["target"] == {"state": "current", "reason": None}


def test_a_vertex_pair_wraps_around_the_selected_contour(store):
    _transcribed(store)
    edges = _selected_edges(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload(target_kind="vertex_pair", target_ids=["v3", "v0"],
                                                  evidence=[{"kind": "user_click", "ref": "v3"}])]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    stored = state["decisions"]["callout_targets"][0]
    # G1R2-01 kimlik kuralı: `vN` kayıtlı bağlamdaki kararlı uç kimliğine çevrilerek saklanır
    assert stored["target_kind"] == "vertex_pair"
    assert stored["target_ids"] == [f"{edges[3]['id']}:start", f"{edges[0]['id']}:start"]
    assert state["callouts"][0]["target"]["state"] == "current"


def test_wrong_targets_are_refused_without_touching_the_record(store):
    _transcribed(store)
    before = _session_path(store).read_bytes()
    revision = store.load(TOKEN)["revision"]
    cases = [
        (_target_payload(target_ids=["ghost"]), "bulunamadı"),
        (_target_payload(target_kind="circle_group", target_ids=["c0", "ghost"]), "bulunamadı"),
        (_target_payload(target_kind="circle_group", target_ids=["c0", "c0"]), "benzersiz"),
        (_target_payload(target_kind="vertex_pair", target_ids=["v0", "v9"]), "kenarlarında yok"),
        (_target_payload(target_kind="vertex_pair", target_ids=["v0", "zzz"]), "kenarlarında yok"),
    ]
    for row, match in cases:
        payload = current_payload(store)
        payload["callout_targets"] = [row]
        with pytest.raises(ValueError, match=match):
            store.save(TOKEN, revision, payload)
    assert _session_path(store).read_bytes() == before


def test_a_target_needs_its_own_current_transcription(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["transcriptions"] = []
    payload["callout_targets"] = [_target_payload()]
    with pytest.raises(ValueError, match="transcription gerektirir"):
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)


def test_an_explicit_count_must_match_the_unique_targets(store):
    record = store.load(TOKEN)
    seed_callouts(store, candidates=[_candidate_row(record, "k1"),
                                     _candidate_row(record, "k2", region=[0.6, 0.1, 0.7, 0.2],
                                                    crop_region=[0.55, 0.05, 0.75, 0.25])])
    payload = current_payload(store)
    payload["transcriptions"] = [
        {"callout_id": "k1", "raw_text": "4x Ø8", "source_region": [0.1, 0.2, 0.4, 0.5], "entered_by": "user"},
        {"callout_id": "k2", "raw_text": "2x Ø8", "source_region": [0.6, 0.1, 0.7, 0.2], "entered_by": "user"},
    ]
    store.save(TOKEN, 0, payload)
    seed_callouts(store, candidate=False, parses=[_parse_row(count=4),
                                                  _parse_row(callout_id="k2", count=2)])
    revision = store.load(TOKEN)["revision"]
    for row in (_target_payload(target_ids=["c0"]),
                _target_payload(target_kind="circle_group", target_ids=["c0", "c1"])):
        payload = current_payload(store)
        payload["callout_targets"] = [row]
        with pytest.raises(ValueError, match="uyuşmuyor"):
            store.save(TOKEN, revision, payload)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload(callout_id="k2", target_kind="circle_group",
                                                  target_ids=["c0", "c1"])]
    state = store.save(TOKEN, revision, payload)
    assert state["callouts"][1]["target"]["state"] == "current"          # 2 adet = 2 hedef


def test_editing_the_text_replaces_the_stored_reading_and_keeps_history(store):
    """PLAN §9: metin değişince eski okuma *yerini yenisine bırakır* (eski metin geçmişte durur) ve
    hedef eskiyerek kalır — hedef kendiliğinden yenilenmez, onay kullanıcınındır."""
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    state = store.save(TOKEN, 1, payload)
    assert state["callouts"][0]["target"]["state"] == "current"

    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10")]
    state = store.save(TOKEN, 2, payload)
    callout = state["callouts"][0]
    assert callout["transcription"] == {"state": "current", "revision": 3, "reason": None}
    assert callout["parse"] == {"state": "current", "reason": None}
    reading = [row for row in store.load(TOKEN)["callout_parses"] if row["callout_id"] == "k1"]
    assert len(reading) == 1 and reading[0]["transcription_revision"] == 3
    assert (reading[0]["form"], reading[0]["size"]) == ("diameter", 10.0)
    assert callout["target"] == {"state": "stale", "reason": "transcription_changed"}
    history = store.load(TOKEN)["history"]
    old = [row for entry in history for row in entry.get("transcriptions", [])
           if row.get("raw_text") == "4x Ø8 THRU"]
    assert old and old[0]["revision"] == 1                               # A kaydı geçmişte duruyor


def test_a_profile_change_stales_the_target_within_the_same_geometry_version(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    pinned = store.load(TOKEN)["decisions"]["callout_targets"][0]
    wires = [row["id"] for row in store.load(TOKEN)["options"]["profiles"] if row["kind"] == "wire"]
    assert len(wires) >= 2

    payload = current_payload(store, profile_id=wires[1])
    state = store.save(TOKEN, 2, payload)
    assert store.load(TOKEN)["geometry_version"] == guided.GEOMETRY_VERSION   # sürüm artmadı
    callout = state["callouts"][0]
    assert callout["parse"]["state"] == "current"                        # metin aynıysa parse korunur
    assert callout["target"] == {"state": "stale", "reason": "geometry_changed"}
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    assert stored["profile_id"] == pinned["profile_id"]                  # taşınan onay byte-korunur
    assert stored["geometry_key"] == pinned["geometry_key"]

    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]           # açık yeniden onay
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    assert store.load(TOKEN)["decisions"]["callout_targets"][0]["profile_id"] == wires[1]


def test_a_changed_source_stales_the_callout_layer_and_the_build(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    _fake_build(store)
    public = store.public(store.load(TOKEN))
    assert public["build_status"] == "complete"
    assert public["callouts"][0]["target"]["state"] == "current"

    Path(store.load(TOKEN)["source"]).write_bytes(b"changed-source-bytes")   # kaynak değişti
    public = store.public(store.load(TOKEN))
    assert public["geometry"]["stale"] is not None
    assert public["callouts"][0]["transcription"]["state"] == "current"      # yazılan metin tarihsel kayıt
    assert public["callouts"][0]["parse"] == {"state": "stale", "reason": "source_unavailable"}
    assert public["callouts"][0]["target"] == {"state": "stale", "reason": "source_unavailable"}
    assert public["build_status"] == "historical" and public["step"] is None
    with pytest.raises(ValueError):
        store.artifact(TOKEN, "part.step")


def test_a_geometry_version_mismatch_stales_the_target(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    record = json.loads(_session_path(store).read_text())
    record["geometry_version"] = guided.GEOMETRY_VERSION + 1
    public = store.public(record)                                            # aynı public hesabı
    assert public["callouts"][0]["parse"]["state"] == "current"              # parse geometriye bağlı değil
    assert public["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}


def test_a_contour_change_stales_the_target_in_the_same_version(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    record = json.loads(_session_path(store).read_text())
    record["decisions"]["contour"] = {"drop": ["g3"], "approve_join": False}
    public = store.public(record)
    assert public["geometry"]["version"] == record["geometry_version"]        # sürüm aynı
    assert public["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}


def test_an_old_parser_version_fixture_stales_its_parse_and_target(store):
    record = _transcribed(store, parses=[_parse_row(parser_version="callout-parser/0")])
    seed_callouts(store, candidate=False,
                  targets=[_target_row(record, parser_version="callout-parser/0")])
    callout = store.public(store.load(TOKEN))["callouts"][0]
    assert callout["parse"] == {"state": "stale", "reason": "parser_version_changed"}
    assert callout["target"] == {"state": "stale", "reason": "parser_version_changed"}

    payload = current_payload(store)
    payload["callout_targets"] = [dict(payload["callout_targets"][0], reconfirm=True)]  # yeni onay denemesi
    with pytest.raises(ValueError, match="parser sürümüne bağlanmalı"):
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)


def test_loading_twice_changes_nothing(store):
    _transcribed(store)
    before = _session_path(store).read_bytes()
    first = store.load(TOKEN)
    second = store.load(TOKEN)
    assert _session_path(store).read_bytes() == before
    assert first["revision"] == second["revision"] == 1
    assert first["log"] == second["log"] and first["decisions"] == second["decisions"]


# --- undo, logging and build/artifact staleness (T13/T14/T15/T16/T22) -------

def test_undo_restores_the_earlier_callout_decisions_and_stales_the_build(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10")]                    # B
    store.save(TOKEN, 1, payload)
    snapshot = [entry for entry in store.load(TOKEN)["history"] if entry.get("transcriptions")][-1]
    state = store.save(TOKEN, 2, undo=True)
    assert state["revision"] == 3
    assert state["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"  # A geri geldi
    assert state["decisions"]["transcriptions"][0]["revision"] == 1
    assert state["decisions"] == snapshot                     # bağımsız snapshot aynen döndü
    assert state["build_status"] is None and state["step"] is None              # build stale, diriltme yok
    assert state["callouts"][0]["transcription"] == {"state": "current", "revision": 1, "reason": None}

    reopened = GuidedStore(store.root)
    again = reopened.public(reopened.load(TOKEN))
    assert again["revision"] == 3
    assert again["decisions"]["transcriptions"][0]["raw_text"] == "4x Ø8 THRU"


def test_undo_does_not_make_an_old_target_current_again(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)                                              # A bağlamında onay
    wires = [row["id"] for row in store.load(TOKEN)["options"]["profiles"] if row["kind"] == "wire"]
    store.save(TOKEN, 2, current_payload(store, profile_id=wires[1]))          # B bağlamı
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    store.save(TOKEN, 3, payload)                                              # B'de açık yeniden onay
    assert store.public(store.load(TOKEN))["callouts"][0]["target"]["state"] == "current"

    state = store.save(TOKEN, 4, undo=True)      # A onayı geri gelir, bağlam B kalır
    assert state["decisions"]["callout_targets"][0]["profile_id"] == wires[0]
    assert state["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}


def test_base_reading_and_options_survive_callout_edits_and_undo(store):
    _transcribed(store)
    before = json.loads(_session_path(store).read_text())
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10")]
    store.save(TOKEN, 2, payload)
    store.save(TOKEN, 3, undo=True)
    after = json.loads(_session_path(store).read_text())
    assert after["options"] == before["options"]                 # temel okuma kullanıcı girdisiyle değişmez
    assert after["source_sha256"] == before["source_sha256"]
    assert after.get("reading") == before.get("reading")
    assert after.get("proposals") == before.get("proposals")


def test_callout_events_are_user_actions_and_no_parser_is_invented(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10")]
    store.save(TOKEN, 2, payload)
    store.save(TOKEN, 3, undo=True)
    log = store.load(TOKEN)["log"]
    assert [row["action"] for row in log if row["action"] == "transcribe"].count("transcribe") == 1
    assert len([row for row in log if row["action"] == "edit_transcription"]) == 1
    assert len([row for row in log if row["action"] == "confirm_target"]) == 1
    assert any(row["actor"] == "user" and row["action"] == "undo" for row in log)
    assert not [row for row in log if "parse" in row["action"]]   # parser yokken parse olayı yazılmaz
    assert not [row for row in log if row["action"] in ("freshness", "stale")]
    event = next(row for row in log if row["action"] == "transcribe")
    assert event["value"] == "4x Ø8 THRU"
    assert all(row["actor"] != "parser" for row in log)


def test_a_later_edit_leaves_the_old_step_historical_and_never_current(store):
    _transcribed(store)
    folder = _fake_build(store)
    assert store.public(store.load(TOKEN))["build_status"] == "complete"
    revision = store.load(TOKEN)["revision"]
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10")]                    # transcription edit
    state = store.save(TOKEN, revision, payload)
    assert state["build_status"] is None and state["step"] is None
    with pytest.raises(ValueError):
        store.artifact(TOKEN, "part.step")
    assert (folder / "part.step").exists()                    # eski çıktı tarihsel olarak diskte kalır
    state = store.save(TOKEN, store.load(TOKEN)["revision"], undo=True)
    assert state["step"] is None and state["build_status"] is None             # undo da diriltmez


def test_a_target_edit_also_makes_the_old_step_historical(store):
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    store.save(TOKEN, 1, payload)
    folder = _fake_build(store)
    assert store.public(store.load(TOKEN))["step"]
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [{**stored, "target_ids": ["c1"]}]      # gerçek hedef düzenlemesi
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["step"] is None and state["build_status"] is None
    assert (folder / "part.step").exists()


def test_a_build_that_finishes_late_never_attaches_to_newer_decisions(store, monkeypatch):
    _transcribed(store)
    entered, release = threading.Event(), threading.Event()

    def slow(plan, source, folder):
        entered.set()
        release.wait(timeout=10)

    monkeypatch.setattr(guided, "build_general", slow)
    revision = store.load(TOKEN)["revision"]
    errors = []

    def run():
        try:
            store.build(TOKEN, revision)
        except Exception as exc:                                # çökme burada yakalanır
            errors.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    assert entered.wait(timeout=10)
    payload = current_payload(store)
    payload["thickness"] = 12.0
    store.save(TOKEN, revision, payload)                        # build sürerken yeni karar
    release.set()
    worker.join(timeout=10)
    assert errors == [] and not worker.is_alive()
    record = store.load(TOKEN)
    assert record.get("build") is None                          # geç sonuç yeni kararlara bağlanmaz
    assert store.public(record)["build_status"] is None


# --- düzeltme turu 1 (bağımsız inceleme): sunucu alanları, tek-save bağlamı, parse kapısı, uç sözleşmesi

def _selected_edges(store):
    record = store.load(TOKEN)
    return next(row["edges"] for row in record["options"]["profiles"]
                if row["id"] == record["decisions"]["profile_id"])


def _confirmed_target(store):
    """k1 transkript edilmiş, parse hazır, hedef onaylanmış — turun ortak başlangıç noktası."""
    _transcribed(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["callouts"][0]["target"]["state"] == "current"
    return state


def test_a_carried_target_keeps_its_persisted_server_fields(store):
    state = _confirmed_target(store)
    wires = [row["id"] for row in store.load(TOKEN)["options"]["profiles"] if row["kind"] == "wire"]
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=wires[1]))
    before = store.load(TOKEN)
    pinned = before["decisions"]["callout_targets"][0]
    assert store.public(before)["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}

    # istemci sunucu alanlarını kendisi güncelleyip onayı yeniden "current" yapmayı deniyor
    start = len(store.load(TOKEN)["log"])
    forged = dict(pinned)
    forged.update({"geometry_key": callout_models.geometry_key(before),
                   "geometry_version": before["geometry_version"], "profile_id": wires[1]})
    payload = current_payload(store)
    payload["callout_targets"] = [forged]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    stored = state["decisions"]["callout_targets"][0]
    assert stored["geometry_key"] == pinned["geometry_key"]
    assert stored["profile_id"] == wires[0]
    assert state["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}

    # evidence metnini değiştirmek de yeniden onay değildir: kalıcı kayıt değişmez
    drifted = dict(pinned)
    drifted["evidence"] = [{"kind": "user_click", "ref": "forged"}]
    payload = current_payload(store)
    payload["callout_targets"] = [drifted]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["decisions"]["callout_targets"][0]["evidence"] == pinned["evidence"]
    assert state["callouts"][0]["target"]["state"] == "stale"
    assert not [row for row in store.load(TOKEN)["log"][start:]          # G1R2-02: sürüklenme onay değil
                if row["action"] == "confirm_target"]


def test_a_real_reconfirmation_is_an_explicit_act(store):
    _confirmed_target(store)
    wires = [row["id"] for row in store.load(TOKEN)["options"]["profiles"] if row["kind"] == "wire"]
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=wires[1]))
    assert store.public(store.load(TOKEN))["callouts"][0]["target"]["state"] == "stale"

    row = dict(store.load(TOKEN)["decisions"]["callout_targets"][0])
    row["reconfirm"] = True
    payload = current_payload(store)
    payload["callout_targets"] = [row]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    stored = state["decisions"]["callout_targets"][0]
    assert stored["profile_id"] == wires[1]
    assert stored["geometry_key"] == callout_models.geometry_key(store.load(TOKEN))
    assert stored["reconfirm"] is False                        # istek tüketildi, kayıtta kalmaz
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}


def test_a_profile_switch_and_a_new_confirmation_in_one_save_agree(store):
    _transcribed(store)
    wires = [row["id"] for row in store.load(TOKEN)["options"]["profiles"] if row["kind"] == "wire"]
    payload = current_payload(store, profile_id=wires[1])
    payload["callout_targets"] = [_target_payload()]           # aynı save'de profil değişimi + yeni onay
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    stored = state["decisions"]["callout_targets"][0]
    assert stored["profile_id"] == wires[1]                    # pinlenen bağlam = seçili bağlam
    assert stored["geometry_key"] == callout_models.geometry_key(store.load(TOKEN))
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}


def test_a_new_confirmation_is_checked_against_the_new_context(store):
    _transcribed(store)
    record = store.load(TOKEN)
    old_edges = next(row["edges"] for row in record["options"]["profiles"]
                     if row["id"] == record["decisions"]["profile_id"])
    wires = [row["id"] for row in record["options"]["profiles"] if row["kind"] == "wire"]
    new_wire = next(row for row in wires if row != record["decisions"]["profile_id"])
    payload = current_payload(store, profile_id=new_wire)
    payload["callout_targets"] = [_target_payload(
        target_kind="vertex_pair",
        target_ids=[f"{old_edges[0]['id']}:start", f"{old_edges[2]['id']}:start"],
        evidence=[{"kind": "user_click", "ref": "old-contour"}])]
    with pytest.raises(ValueError, match="kenarlarında yok"):   # eski konturun ucu yeni bağlamda geçersiz
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)


@pytest.mark.parametrize("status", ["unsupported", "ambiguous"])
def test_a_failed_parse_cannot_be_the_basis_of_a_target_confirmation(store, status):
    _transcribed(store, parses=[_parse_row(status=status)])
    before = _session_path(store).read_bytes()
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    with pytest.raises(ValueError, match="parse durumu"):
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert _session_path(store).read_bytes() == before


def test_conflicting_parse_records_refuse_a_target_confirmation(store):
    _transcribed(store, parses=[_parse_row(), _parse_row(size=10.0)])
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload()]
    with pytest.raises(ValueError, match="çelişkili"):
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)


def test_a_vertex_pair_uses_the_stable_endpoint_ids(store):
    _transcribed(store)
    edges = _selected_edges(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload(
        target_kind="vertex_pair",
        target_ids=[f"{edges[0]['id']}:start", f"{edges[2]['id']}:start"],
        evidence=[{"kind": "user_click", "ref": "g0-start"}])]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    stored = state["decisions"]["callout_targets"][0]
    assert stored["target_ids"] == [f"{edges[0]['id']}:start", f"{edges[2]['id']}:start"]
    assert state["callouts"][0]["target"]["state"] == "current"


def test_a_vertex_pair_rejects_the_same_physical_point_twice(store):
    _transcribed(store)
    edges = _selected_edges(store)
    cases = [["v0", f"{edges[3]['id']}:end"],                         # kanonik ad ↔ komşu kenar ucu
             [f"{edges[0]['id']}:start", f"{edges[3]['id']}:end"]]   # iki kenarın aynı köşedeki uçları
    for ids in cases:
        payload = current_payload(store)
        payload["callout_targets"] = [_target_payload(
            target_kind="vertex_pair", target_ids=ids,
            evidence=[{"kind": "user_click", "ref": "same-corner"}])]
        with pytest.raises(ValueError, match="aynı fiziksel nokta"):
            store.save(TOKEN, store.load(TOKEN)["revision"], payload)


# --- düzeltme turu 2 (bağımsız inceleme): G1R2-01 etkin kontur doğrulaması, G1R2-02 yeniden onay günlüğü


def _other_wire(store):
    record = store.load(TOKEN)
    wires = [row["id"] for row in record["options"]["profiles"] if row["kind"] == "wire"]
    return next(wire for wire in wires if wire != record["decisions"]["profile_id"])


def _duplicate_side_session(store):
    """İnceleme tekrarındaki sentetik kontur: tekrarlı yarım kenar `d2`, kullanıcı çıkaracak (G1R2-01)."""
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="100 mm")]
    store.save(TOKEN, 0, payload)

    def line(edge_id, start, end):
        return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}

    record = store.load(TOKEN)
    profile = next(row for row in record["options"]["profiles"]
                   if row["id"] == record["decisions"]["profile_id"])
    edges = [line("a", (20, 20), (120, 20)), line("d2", (70, 20), (120, 20)),
             line("b", (120, 20), (120, 80)), line("c", (120, 80), (20, 80)),
             line("d", (20, 80), (20, 20))]
    profile["edges"] = edges
    profile["points"] = [edge["start"] for edge in edges]
    _atomic(_session_path(store), record)
    seed_callouts(store, candidate=False,
                  parses=[_parse_row(form="linear", size=100, termination=None, unit="mm")])
    return store.load(TOKEN)


def _corrected_duplicate_contour():
    """`correct_profile`'ın bu düzeltme için gerçek çıktısı — düzeltilmiş kontur geçerlidir."""
    profile = {"id": "wire", "kind": "wire", "edges": [
        {"id": "a", "kind": "line", "start": [20, 20], "end": [120, 20]},
        {"id": "d2", "kind": "line", "start": [70, 20], "end": [120, 20]},
        {"id": "b", "kind": "line", "start": [120, 20], "end": [120, 80]},
        {"id": "c", "kind": "line", "start": [120, 80], "end": [20, 80]},
        {"id": "d", "kind": "line", "start": [20, 80], "end": [20, 20]}]}
    return guided.correct_profile(profile, guided.ContourFix(drop=["d2"]),
                                  join_tolerance_px=guided.RASTER_JOIN_TOLERANCE_PX,
                                  mid_join_px=guided.RASTER_JOIN_TOLERANCE_PX / 2.0)


def _removed_vertex_target():
    return _target_payload(target_kind="vertex_pair", target_ids=["d2:start", "c:start"],
                           evidence=[{"kind": "user_click", "ref": "d2:start,c:start"}])


def test_a_removed_endpoint_can_never_be_confirmed_in_the_same_save(store):          # R1-A
    _duplicate_side_session(store)
    corrected = _corrected_duplicate_contour()                    # düzeltilmiş kontur geçerlidir
    assert [edge["id"] for edge in corrected["edges"]] == ["a", "b", "c", "d"]
    assert contour_audit.audit_contour(corrected["edges"])["ok"] is True
    payload = current_payload(store, contour={"drop": ["d2"], "approve_join": False})
    payload["callout_targets"] = [_removed_vertex_target()]
    before, revision = _session_path(store).read_bytes(), store.load(TOKEN)["revision"]
    with pytest.raises(ValueError, match="düzeltmeden sonra"):
        store.save(TOKEN, revision, payload)
    assert _session_path(store).read_bytes() == before            # ret: kalıcı kayıt değişmez
    record = store.load(TOKEN)
    assert record["revision"] == revision
    assert not (record["decisions"].get("contour") or {}).get("drop")


def test_a_saved_correction_keeps_refusing_its_removed_endpoint(store):              # R1-B
    _duplicate_side_session(store)
    state = store.save(TOKEN, 1, current_payload(store, contour={"drop": ["d2"], "approve_join": False}))
    assert state["decisions"]["contour"]["drop"] == ["d2"]        # yalnız düzeltme kaydı engellenmez
    assert state["decisions"]["callout_targets"] == []
    payload = current_payload(store)
    payload["callout_targets"] = [_removed_vertex_target()]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="düzeltmeden sonra"):
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert _session_path(store).read_bytes() == before            # düzeltme kaydı korunur


def test_a_removed_edge_stales_its_target_and_refuses_the_reconfirm(store):          # R1-C
    _duplicate_side_session(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_removed_vertex_target()]
    state = store.save(TOKEN, 1, payload)                         # d2 yerindeyken onay kabul edilir
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    state = store.save(TOKEN, 2, current_payload(store, contour={"drop": ["d2"], "approve_join": False}))
    assert state["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="düzeltmeden sonra"):    # eski hedefe yeniden onay reddedilir
        store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert _session_path(store).read_bytes() == before
    assert store.public(store.load(TOKEN))["callouts"][0]["target"] == \
        {"state": "stale", "reason": "geometry_changed"}          # eski hedef stale kalır


def test_a_confirmation_on_the_corrected_contour_uses_the_new_context(store):        # R1-D
    _duplicate_side_session(store)
    payload = current_payload(store, contour={"drop": ["d2"], "approve_join": False})
    payload["callout_targets"] = [_target_payload(target_kind="vertex_pair",
                                                  target_ids=["a:start", "c:start"],
                                                  evidence=[{"kind": "user_click", "ref": "a:start,c:start"}])]
    state = store.save(TOKEN, 1, payload)
    stored = state["decisions"]["callout_targets"][0]
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    assert stored["profile_id"] == state["decisions"]["profile_id"]
    assert stored["geometry_key"] == callout_models.geometry_key(store.load(TOKEN))


def test_an_unrelated_edit_leaves_a_carried_stale_target_and_logs_no_confirmation(store):   # R1-E
    _confirmed_target(store)
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=_other_wire(store)))
    start = len(store.load(TOKEN)["log"])
    payload = current_payload(store)
    payload["thickness"] = 12.0
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}
    assert not [row for row in store.load(TOKEN)["log"][start:]
                if row["action"] == "confirm_target"]


def test_undo_and_reopen_after_a_correction_never_resurrect_a_mismatched_target(store):     # R1-F
    _duplicate_side_session(store)
    payload = current_payload(store)
    payload["callout_targets"] = [_removed_vertex_target()]
    store.save(TOKEN, 1, payload)
    store.save(TOKEN, 2, current_payload(store, contour={"drop": ["d2"], "approve_join": False}))

    reopened = GuidedStore(store.root)                            # reopen: tazelik yeniden hesaplanır
    assert reopened.public(reopened.load(TOKEN))["callouts"][0]["target"] == \
        {"state": "stale", "reason": "geometry_changed"}          # uymayan hedef current olmaz

    state = reopened.save(TOKEN, 3, undo=True)                    # düzeltmeden önceki tutarlı duruma dönüş
    assert state["decisions"]["contour"]["drop"] == []            # düzeltme geri alındı
    assert state["decisions"]["callout_targets"][0]["target_ids"] == ["d2:start", "c:start"]
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}   # o zamanki geometriye uyar


def test_v_names_resolve_in_the_recorded_context_never_the_corrected_list(store):    # R1-H
    _duplicate_side_session(store)
    payload = current_payload(store, contour={"drop": ["d2"], "approve_join": False})
    payload["callout_targets"] = [_target_payload(target_kind="vertex_pair", target_ids=["v1", "c:start"],
                                                  evidence=[{"kind": "user_click", "ref": "v1,c"}])]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="yeniden seçin"):        # v1 = kayıtlı bağlamda d2:start; yok
        store.save(TOKEN, 1, payload)
    assert _session_path(store).read_bytes() == before

    payload = current_payload(store, contour={"drop": ["d2"], "approve_join": False})
    payload["callout_targets"] = [_target_payload(target_kind="vertex_pair", target_ids=["v0", "v2"],
                                                  evidence=[{"kind": "user_click", "ref": "v0,v2"}])]
    state = store.save(TOKEN, 1, payload)                         # anlam korunuyorsa kararlı kimliğe çevrilir
    assert state["decisions"]["callout_targets"][0]["target_ids"] == ["a:start", "b:start"]
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}


def test_a_stale_to_current_reconfirm_is_written_to_the_log(store):                  # R2-A
    _confirmed_target(store)
    other = _other_wire(store)
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=other))
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    assert store.public(store.load(TOKEN))["callouts"][0]["target"] == \
        {"state": "stale", "reason": "geometry_changed"}
    start = len(store.load(TOKEN)["log"])
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    confirms = [row for row in store.load(TOKEN)["log"][start:]
                if row["actor"] == "user" and row["action"] == "confirm_target"]
    assert len(confirms) == 1                                     # tam 1 yeni onay olayı
    evidence, fresh = confirms[0]["evidence"], state["decisions"]["callout_targets"][0]
    assert evidence["callout_id"] == "k1" and evidence["profile_id"] == other
    assert evidence["geometry_key"] == fresh["geometry_key"]
    assert evidence["transcription_revision"] == 1
    assert fresh["reconfirm"] is False                            # istek tüketildi


def test_a_reconfirmation_on_a_new_transcription_binding_is_logged(store):           # R2-B
    _confirmed_target(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw="Ø10 THRU")]
    store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    revision = store.load(TOKEN)["decisions"]["transcriptions"][0]["revision"]
    assert revision != 1
    assert store.public(store.load(TOKEN))["callouts"][0]["target"] == \
        {"state": "stale", "reason": "transcription_changed"}
    seed_callouts(store, candidate=False, parses=[_parse_row(transcription_revision=revision)])
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    start = len(store.load(TOKEN)["log"])
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, transcription_revision=revision, reconfirm=True)]
    state = store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    confirms = [row for row in store.load(TOKEN)["log"][start:] if row["action"] == "confirm_target"]
    assert len(confirms) == 1
    assert confirms[0]["evidence"]["transcription_revision"] == revision   # yeni bağ audit'te görünür


@pytest.mark.parametrize("parses", [
    [_parse_row(status="unsupported")],
    [_parse_row(status="ambiguous")],
    [_parse_row(), _parse_row(size=10.0)],
])
def test_a_reconfirm_against_a_failed_parse_changes_nothing(store, parses):          # R2-D
    _confirmed_target(store)
    seed_callouts(store, candidate=False, parses=parses)
    revision = store.load(TOKEN)["revision"]
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="parse"):
        store.save(TOKEN, revision, payload)
    assert _session_path(store).read_bytes() == before            # log/revision/history değişmez
    assert store.load(TOKEN)["revision"] == revision


def test_reopen_and_public_freshness_write_no_confirmation_events(store):            # R2-E
    _confirmed_target(store)
    other = _other_wire(store)
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=other))
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    log, revision = store.load(TOKEN)["log"], store.load(TOKEN)["revision"]
    reopened = GuidedStore(store.root)                            # reopen + public tekrarları
    record = reopened.load(TOKEN)
    reopened.public(record)
    after = reopened.load(TOKEN)
    assert after["log"] == log and after["revision"] == revision  # yeni onay olayı yok


def test_a_reconfirm_in_the_unchanged_context_stays_a_noop(store):                   # §5.2 tercihi
    _confirmed_target(store)
    revision, start = store.load(TOKEN)["revision"], len(store.load(TOKEN)["log"])
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    state = store.save(TOKEN, revision, payload)
    assert state["revision"] == revision                          # güncel bağlamda değişiklik yok: yazılmaz
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    assert not [row for row in store.load(TOKEN)["log"][start:] if row["action"] == "confirm_target"]


def test_an_undo_after_a_reconfirmation_logs_no_fake_confirmation(store):            # R2-F
    _confirmed_target(store)
    other = _other_wire(store)
    store.save(TOKEN, store.load(TOKEN)["revision"], current_payload(store, profile_id=other))
    stored = store.load(TOKEN)["decisions"]["callout_targets"][0]
    payload = current_payload(store)
    payload["callout_targets"] = [dict(stored, reconfirm=True)]
    store.save(TOKEN, store.load(TOKEN)["revision"], payload)
    start = len(store.load(TOKEN)["log"])
    state = store.save(TOKEN, store.load(TOKEN)["revision"], undo=True)
    assert state["callouts"][0]["target"] == {"state": "stale", "reason": "geometry_changed"}
    assert state["build_status"] is None and state["step"] is None
    events = store.load(TOKEN)["log"][start:]
    assert any(row["action"] == "undo" for row in events)         # undo kendi olayını kullanır
    assert not [row for row in events if row["action"] == "confirm_target"]


# --- düzeltme turu 3 (PLAN-21 §4): G1R3-01 — nokta eşitliği onarım bütçesi değildir ---------------


def _short_side_session(store, width):
    """Geçerli fakat kendi kısa kenarı `width` px olan bir kontur: küçük, gerçek bir ölçü (G1R3-01).

    Kontur denetimi her genişlikte geçmelidir; bulgu yalnızca *geçerli* geometriye aittir, 1 px'lik
    çizgi kalınlığı sınırının altındaki bir kutuyla hata iddia edilmez.
    """
    seed_callouts(store)
    payload = current_payload(store)
    payload["transcriptions"] = [_transcription(raw=f"{width / 2:g} mm")]
    store.save(TOKEN, 0, payload)
    seed_callouts(store, candidate=False, parses=[_parse_row(
        form="linear", size=width / 2, count=None, unit="mm", termination=None)])
    record = store.load(TOKEN)
    profile = next(row for row in record["options"]["profiles"]
                   if row["id"] == record["decisions"]["profile_id"])
    points = [[20, 20], [20 + width, 20], [20 + width, 80], [20, 80]]
    edges = [{"id": f"short{i}", "kind": "line", "start": point, "end": points[(i + 1) % 4]}
             for i, point in enumerate(points)]
    assert contour_audit.audit_contour(edges)["ok"] is True
    profile["edges"], profile["points"] = edges, points
    _atomic(_session_path(store), record)
    return record


@pytest.mark.parametrize("width", [5, 10, 20, 21])
def test_two_short_ends_are_two_distinct_points(store, width):                       # G1R3-01
    """Araları 20 px'den kısa iki ölçü ucu, onarım bütçesi yüzünden "aynı nokta" sayılamaz."""
    record = _short_side_session(store, width)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload(
        target_kind="vertex_pair", target_ids=["short0:start", "short0:end"],
        evidence=[{"kind": "user_click", "ref": "short0:start,short0:end"}])]
    state = store.save(TOKEN, record["revision"], payload)
    assert state["callouts"][0]["target"] == {"state": "current", "reason": None}
    assert state["decisions"]["callout_targets"][0]["target_ids"] == ["short0:start", "short0:end"]


def test_a_short_contours_shared_corner_is_still_one_point(store):                   # G1R3-01
    """Küçük ölçüler kabul edilirken komşu iki kenarın aynı köşe ucu hâlâ reddedilir."""
    record = _short_side_session(store, 5)
    payload = current_payload(store)
    payload["callout_targets"] = [_target_payload(
        target_kind="vertex_pair", target_ids=["short0:end", "short1:start"],
        evidence=[{"kind": "user_click", "ref": "same-corner"}])]
    before = _session_path(store).read_bytes()
    with pytest.raises(ValueError, match="aynı fiziksel nokta"):
        store.save(TOKEN, record["revision"], payload)
    assert _session_path(store).read_bytes() == before           # ret: kalıcı kayıt değişmez
