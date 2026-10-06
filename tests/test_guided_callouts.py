"""G1 store behaviour (PLAN-20 §6–§8): the callout records through the real `GuidedStore`.

Everything here runs on a synthetic vector sheet — one wire, two circles and a border — through
create/load/save/undo/accept/build, no PDF and no CAD where not needed. Parse fixtures are seeded
as session records the store reads; G1 has no parser and no store API may fake one.
"""
import hashlib
import json

import pytest

from drawingto3d import guided
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


def seed_callouts(store, *, candidate=True, candidates=None, parses=None, proposals=None, history=None):
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
    record["build"] = {"revision": 0, "status": "complete", "folder": str(folder),
                       "source_sha256": record["source_sha256"],
                       "geometry_version": record["geometry_version"]}
    _atomic(_session_path(store), record)
    return folder


def _transcription(raw="  4 × Ø8 THRU  "):
    return {"callout_id": "k1", "raw_text": raw, "source_region": [0.1, 0.2, 0.4, 0.5],
            "entered_by": "user", "revision": 777}


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
    assert public["callout_schema_version"] == 1
    assert public["callouts"] == [{
        "id": "k1", "page_index": 0, "source_kind": "vector_text",
        "transcription": {"state": "current", "revision": 1, "reason": None},
        "parse": {"state": "missing", "reason": "needs_parse"},
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
