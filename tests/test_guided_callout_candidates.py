"""G2.3/G2.5 store integration (kök `PLAN.md` §26–§50): real `GuidedStore` sessions.

`create` persists the adapter's candidates from the *same* observations — one observe, no OCR
again, no model, no build, no parser. New sessions hold candidates and nothing else: no
transcriptions, no parses, no targets. Reopen and legacy loads read the persisted base state and
never redetect; a read never rewrites the file. Runnable on the repo's own plate test drawing.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from drawingto3d import callouts, guided
from drawingto3d import raster
from drawingto3d.callouts import CALLOUT_DETECTOR_VERSION, callout_candidates_from_observations
from drawingto3d.guided import GuidedStore
from drawingto3d.observe import Observations, observe

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
RASTER = Path("examples/flange-elbow-90.png")                       # gerçek raster + tesseract OCR


@pytest.fixture(scope="module")
def shared(tmp_path_factory):
    """One created session, reused by the read-only tests — `create` runs a real observation."""
    store = GuidedStore(tmp_path_factory.mktemp("shared") / "store")
    return {"store": store, "state": store.create(PLATE.read_bytes())}


@pytest.fixture
def plate(tmp_path):
    """A fresh store + session for tests that write to it."""
    store = GuidedStore(tmp_path / "store")
    return {"store": store, "state": store.create(PLATE.read_bytes())}


def _record(store, token):
    return json.loads((store.folder(token) / "session.json").read_text())


def _observations(store, token):
    return Observations.model_validate(json.loads((store.folder(token) / "observations.json").read_text()))


# --- G2.3 create integration -------------------------------------------------

def test_create_persists_the_adapters_candidates_exactly(shared):
    store, state = shared["store"], shared["state"]
    record = _record(store, state["token"])
    observations = _observations(store, state["token"])
    detection = callout_candidates_from_observations(observations, geometry_version=guided.GEOMETRY_VERSION)
    assert record["callout_candidates"]
    assert record["callout_candidates"] == [row.model_dump(mode="json") for row in detection.candidates]
    assert record["callout_parses"] == []


def test_every_candidate_points_back_to_its_own_observation_region(shared):
    store, state = shared["store"], shared["state"]
    record = _record(store, state["token"])
    observations = _observations(store, state["token"])
    texts = {row.id: row for row in observations.texts}
    for row in record["callout_candidates"]:
        assert row["source_digest"] == record["source_sha256"] == observations.source.sha256
        assert row["page_index"] == 0
        assert row["detector_version"] == CALLOUT_DETECTOR_VERSION
        assert row["geometry_version"] == guided.GEOMETRY_VERSION
        assert row["source_kind"] == "vector_text"                  # plate: pdf-text katmanı
        assert row["crop_region"] == row["region"]
        first = texts[row["observation_ids"][0]]
        bbox = first.bbox
        expected = [round(bbox.x / observations.frame.width, 8), round(bbox.y / observations.frame.height, 8),
                    round((bbox.x + bbox.w) / observations.frame.width, 8),
                    round((bbox.y + bbox.h) / observations.frame.height, 8)]
        assert row["region"] == expected                            # testte bağımsız normalizasyon (§98)


def test_create_creates_no_user_or_computed_semantic_records(shared):
    state = shared["state"]
    assert state["callout_candidates"]
    assert state["decisions"]["transcriptions"] == []
    assert state["decisions"]["callout_targets"] == []
    assert state["callout_parses"] == []
    hints = [row["machine_text_hint"] for row in state["callout_candidates"]]
    assert any(hints)                                               # ipucu var...
    assert not state["decisions"]["transcriptions"]                 # ...ama kendiliğinden karar olmadı
    for row in state["callouts"]:
        assert row["transcription"] == {"state": "missing", "revision": None, "reason": "needs_transcription"}
        assert row["parse"] == {"state": "missing", "reason": "needs_parse"}
        assert row["target"] == {"state": "missing", "reason": "needs_target"}


def test_create_has_no_build_or_callout_event_side_effects(shared):
    store, state = shared["store"], shared["state"]
    record = _record(store, state["token"])
    assert state["step"] is None and state["stl"] is None and state["build_status"] is None
    assert record["build"] is None
    actions = {row["action"] for row in record["log"]}
    assert not {"transcribe", "edit_transcription", "confirm_target", "parse", "build"} & actions
    assert not [row for row in record["log"] if row["actor"] == "user"]


def test_callout_detection_metadata_is_persisted(shared):
    store, state = shared["store"], shared["state"]
    record = _record(store, state["token"])
    assert record["callout_detection"]["detector_version"] == CALLOUT_DETECTOR_VERSION
    assert record["callout_detection"]["diagnostics"] == []         # plate: her ifade geçerli bir bölge


def test_create_observes_once_and_the_adapter_runs_once(plate, monkeypatch):
    store = plate["store"]
    observed, detected = [], []
    real_observe, real_adapter = guided.observe, callouts.callout_candidates_from_observations

    def counting_observe(path):
        observed.append(path)
        return real_observe(path)

    def counting_adapter(*args, **kwargs):
        detected.append(1)
        return real_adapter(*args, **kwargs)

    monkeypatch.setattr(guided, "observe", counting_observe)
    monkeypatch.setattr(callouts, "callout_candidates_from_observations", counting_adapter)
    store.create(PLATE.read_bytes())
    assert len(observed) == 1                                       # ikinci observe/OCR yok
    assert len(detected) == 1


def test_a_source_digest_mismatch_never_becomes_a_candidate_identity(plate, monkeypatch):
    store = plate["store"]
    real_observe = guided.observe

    def tampered(path):
        observations = real_observe(path)
        return observations.model_copy(update={"source": observations.source.model_copy(
            update={"sha256": "e" * 64})})

    monkeypatch.setattr(guided, "observe", tampered)
    state = store.create(PLATE.read_bytes())
    record = _record(store, state["token"])
    assert record["callout_candidates"] == []                       # kimlik uydurulmaz
    assert {"code": "source_digest_mismatch", "observation_id": None} in \
        record["callout_detection"]["diagnostics"]
    assert state["callouts"] == []


# --- base state is independent of later decisions ----------------------------

def test_unrelated_saves_and_an_undo_never_touch_the_candidate_base(plate, monkeypatch):
    store, state = plate["store"], plate["state"]
    token = state["token"]
    base = _record(store, token)["callout_candidates"]
    calls = []
    real_adapter = callouts.callout_candidates_from_observations
    monkeypatch.setattr(callouts, "callout_candidates_from_observations",
                        lambda *args, **kwargs: (calls.append(1), real_adapter(*args, **kwargs))[1])

    payload = json.loads(json.dumps(state["decisions"]))
    payload["thickness"] = 12.0
    saved = store.save(token, state["revision"], payload)
    assert _record(store, token)["callout_candidates"] == base
    profile = next(row["id"] for row in state["options"]["profiles"])
    payload = json.loads(json.dumps(saved["decisions"]))
    payload["profile_id"] = profile
    saved = store.save(token, saved["revision"], payload)
    record = _record(store, token)
    assert record["callout_candidates"] == base
    assert "callout_candidates" not in record["history"][-1]        # aday listesi karar snapshot'ı değildir
    store.save(token, saved["revision"], undo=True)
    assert _record(store, token)["callout_candidates"] == base
    assert calls == []                                              # save/undo adaptörü hiç çalıştırmaz (§93)


def test_a_build_outcome_never_moves_the_candidate_base(plate):
    store, state = plate["store"], plate["state"]
    token = state["token"]
    record = _record(store, token)
    base = record["callout_candidates"]
    folder = store.folder(token) / "build-0-fake"
    folder.mkdir(exist_ok=True)
    (folder / "part.step").write_bytes(b"fake")
    record["build"] = {"revision": record["revision"], "status": "complete", "folder": str(folder),
                       "source_sha256": record["source_sha256"],
                       "geometry_version": record["geometry_version"]}
    (store.folder(token) / "session.json").write_text(json.dumps(record, ensure_ascii=False))
    public = store.public(store.load(token))
    assert _record(store, token)["callout_candidates"] == base
    assert [row["id"] for row in public["callout_candidates"]] == [row["id"] for row in base]


# --- G2.5 reopen / legacy / source loss --------------------------------------

def test_reopen_keeps_the_candidates_and_writes_nothing(shared, monkeypatch):
    store, state = shared["store"], shared["state"]
    token = state["token"]
    path = store.folder(token) / "session.json"
    before = path.read_bytes()
    record = _record(store, token)
    calls = []
    real_adapter = callouts.callout_candidates_from_observations
    monkeypatch.setattr(callouts, "callout_candidates_from_observations",
                        lambda *args, **kwargs: (calls.append(1), real_adapter(*args, **kwargs))[1])
    again = GuidedStore(store.root).load(token)
    assert again["callout_candidates"] == record["callout_candidates"]   # kimlik/bölge/ipucu/versiyon aynen
    assert GuidedStore(store.root).public(again)["callout_candidates"] == state["callout_candidates"]
    assert path.read_bytes() == before                              # okuma dosyayı yeniden yazmaz (§45)
    assert calls == []                                              # load yeniden tespit etmez (§45)
    assert len(again["log"]) == len(record["log"])                  # sahte kullanıcı olayı yok (§48)
    assert not [row for row in again["log"] if row["actor"] == "user"]


def test_a_legacy_session_without_callouts_loads_read_only(plate, monkeypatch):
    store, state = plate["store"], plate["state"]
    token = state["token"]
    path = store.folder(token) / "session.json"
    record = _record(store, token)
    for key in ("callout_candidates", "callout_detection", "callout_schema_version"):
        record.pop(key)                                             # callout katmanı öncesi oturum
    profile = next(row["id"] for row in state["options"]["profiles"])
    record["decisions"]["profile_id"] = profile
    record["decisions"]["thickness"] = 12.0
    record["decisions"]["holes"] = [{"circle_id": state["options"]["circles"][0]["id"],
                                     "kind": "through", "diameter": 6.0}]
    path.write_text(json.dumps(record, ensure_ascii=False))
    before = path.read_bytes()

    def exploding_observe(path):
        raise AssertionError("legacy load gözlemciyi çağırmamalı")   # yeniden tespit yok (§20/§45)

    monkeypatch.setattr(guided, "observe", exploding_observe)
    loaded = GuidedStore(store.root).load(token)
    public = GuidedStore(store.root).public(loaded)
    assert public["callout_candidates"] == []                       # yeniden tespit yok (§45/§20)
    assert public["callouts"] == []
    assert public["decisions"]["transcriptions"] == []
    assert public["decisions"]["callout_targets"] == []
    assert public["decisions"]["profile_id"] == profile             # eski kararlar korunur, yeni bağ yok (§47)
    assert path.read_bytes() == before                              # okuma yazmaz


def test_a_lost_source_keeps_the_candidates(plate):
    store, state = plate["store"], plate["state"]
    token = state["token"]
    candidates = state["callout_candidates"]
    (store.folder(token) / "source.pdf").unlink()
    public = store.public(store.load(token))
    assert public["geometry"]["stale"]                              # mevcut davranış: tarihsel işaretlenir
    assert public["callout_candidates"] == candidates               # aday geçmişi silinmez (§49)
    assert public["step"] is None and public["build_status"] is None


# --- G2.4 real sources --------------------------------------------------------

def _expected_id(digest, region, source_kind):
    payload = {"detector_version": CALLOUT_DETECTOR_VERSION, "page_index": 0, "region": region,
               "source_digest": digest, "source_kind": source_kind}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_the_real_vector_drawing_yields_one_candidate_per_text_region():
    """PLAN-18 §36/§37/§41/§98: the plate's own text layer — every valid region, no semantic filter."""
    observations = observe(PLATE)
    detection = callout_candidates_from_observations(observations, geometry_version=guided.GEOMETRY_VERSION)
    assert observations.texts
    texts = {row.id: row for row in observations.texts}
    expected = set()
    for row in observations.texts:
        bbox = row.bbox
        region = [round(bbox.x / observations.frame.width, 8), round(bbox.y / observations.frame.height, 8),
                  round((bbox.x + bbox.w) / observations.frame.width, 8),
                  round((bbox.y + bbox.h) / observations.frame.height, 8)]
        expected.add(_expected_id(observations.source.sha256, region, "vector_text"))
    assert {row.id for row in detection.candidates} == expected     # 45/45: yüksek geri çağırma, filtre yok
    assert detection.diagnostics == []
    for row in detection.candidates:
        assert row.source_digest == observations.source.sha256
        assert row.page_index == 0
        assert row.source_kind == "vector_text"                     # pdf-text → vector_text
        assert row.observation_ids and all(item in texts for item in row.observation_ids)
        assert 0.0 <= row.region[0] < row.region[2] <= 1.0 and 0.0 <= row.region[1] < row.region[3] <= 1.0


@pytest.fixture(scope="module")
def raster_sheet():
    return observe(RASTER)                                          # gerçek raster + OCR yolu (bir kez)


def _region_of(observations, bbox):
    return [round(bbox.x / observations.frame.width, 8), round(bbox.y / observations.frame.height, 8),
            round((bbox.x + bbox.w) / observations.frame.width, 8),
            round((bbox.y + bbox.h) / observations.frame.height, 8)]


def test_the_real_raster_sheet_yields_raster_region_candidates(raster_sheet):
    """PLAN-18 §38/§39: the real OCR path produces raster candidates, region for region."""
    detection = callout_candidates_from_observations(raster_sheet, geometry_version=guided.GEOMETRY_VERSION)
    assert len(raster_sheet.texts) >= 10                            # probe: 27 OCR ifadesi (bu ortamda)
    assert detection.candidates
    assert {row.source_kind for row in detection.candidates} == {"raster_region"}
    for row in detection.candidates:
        assert row.source_digest == raster_sheet.source.sha256
        assert row.page_index == 0
        assert row.detector_version == CALLOUT_DETECTOR_VERSION
        assert row.geometry_version == guided.GEOMETRY_VERSION
        owners = {text.id for text in raster_sheet.texts if _region_of(raster_sheet, text.bbox) == row.region}
        assert owners
        assert set(row.observation_ids) == owners                   # provenance = bölgenin gerçek sahipleri
        assert "confidence" not in row.model_dump()                 # §40: aday modeli genişletilmedi


def _no_text_sheet(folder: Path) -> Path:
    """A small drawn sheet with strokes but no printed phrase — a valid raster, no OCR text."""
    image = np.full((240, 320), 255, dtype=np.uint8)
    cv2.line(image, (40, 40), (280, 40), 0, 3)
    cv2.line(image, (280, 40), (280, 200), 0, 3)
    cv2.line(image, (280, 200), (40, 200), 0, 3)
    path = folder / "no-text-sheet.png"
    cv2.imwrite(str(path), image)
    return path


def test_a_real_raster_sheet_without_text_is_an_honest_none(tmp_path, monkeypatch):
    """PLAN-18 §39/§99: OCR okumadıysa [] döner; geometriden sahte kutu üretilmez; ikinci OCR yok."""
    observations = observe(_no_text_sheet(tmp_path))
    assert observations.texts == []                                 # OCR bir ifade okumadı
    assert observations.primitives                                  # geometri var...

    def forbidden(*_args, **_kwargs):
        raise AssertionError("adaptör ikinci OCR çağrısı yapmamalı")

    monkeypatch.setattr(raster.subprocess, "run", forbidden)
    detection = callout_candidates_from_observations(observations, geometry_version=guided.GEOMETRY_VERSION)
    assert detection.candidates == []                               # ...ama çağrı çıkarılmaz (§39)
    assert [row.code for row in detection.diagnostics] == ["no_text_observations"]
