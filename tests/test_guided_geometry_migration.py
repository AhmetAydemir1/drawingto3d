"""P01 acceptance (PLAN.md): a record written before the geometry-version split is migrated from its
source — decisions kept, no silent moves, one remembered failure, atomic write. Real store path only.
"""
import hashlib
import json
from pathlib import Path

import pytest

from drawingto3d import guided
from drawingto3d.guided import GEOMETRY_VERSION, GuidedStore

PLATE_SHEET = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _as_legacy(store, token):
    """Write the session file the way a pre-P01 record looks: no geometry version, and base geometry the
    old build may already have rewritten (a leftover solve report and a moved edge end)."""
    path = store.folder(token) / "session.json"
    record = json.loads(path.read_text())
    record.pop("geometry_version", None)
    profile = next(p for p in record["options"]["profiles"] if p.get("edges"))
    profile["solved_dimensions"] = {"status": "solved"}
    edge = profile["edges"][0]
    edge["start"] = [edge["start"][0] + 37.0, edge["start"][1] - 11.0]
    path.write_text(json.dumps(record, ensure_ascii=False))
    return record


def test_legacy_record_gets_its_base_geometry_back_and_keeps_decisions(tmp_path):
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE_SHEET.read_bytes())
    token = opened["token"]
    decisions = store.load(token)["decisions"]
    _as_legacy(store, token)

    loaded = store.load(token)                                   # migration happens here
    assert loaded.get("geometry_version") == GEOMETRY_VERSION
    assert loaded["decisions"] == decisions                      # the user's decisions are untouched
    fresh = guided.drawing_options(guided.observe(Path(loaded["source"])))
    # G12.3 (PLAN-25 §46/§48): the migration re-reads the base geometry and records each row's view
    # owner on top of it; the geometry itself is exactly the fresh read's. A circle-kind profile shares
    # its nested `circle` object with the circles list, so the ownership key can appear at either level.
    def _without_owner(row):
        return {key: (_without_owner(value) if isinstance(value, dict) else value)
                for key, value in row.items() if key != "view_id"}
    assert [_without_owner(p) for p in loaded["options"]["profiles"]] == fresh["profiles"]
    assert [_without_owner(c) for c in loaded["options"]["circles"]] == fresh["circles"]
    assert all("view_id" in row for row in loaded["options"]["circles"])
    assert all("view_id" in row for row in loaded["options"]["profiles"])
    assert not any("solved_dimensions" in profile for profile in loaded["options"]["profiles"])
    assert any(line["action"] == "migrate" for line in loaded["log"])

    again = store.load(token)                                    # written to disk, idempotent
    assert again["options"] == loaded["options"]


def test_identity_mismatch_keeps_the_old_geometry_and_blocks_the_build(tmp_path, monkeypatch):
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE_SHEET.read_bytes())
    token = opened["token"]
    record = _as_legacy(store, token)

    # A reader change: the same drawing no longer yields the same identities.
    changed = json.loads(json.dumps(record["options"]))
    changed["profiles"] = changed["profiles"][1:]
    monkeypatch.setattr(guided, "drawing_options", lambda observations: json.loads(json.dumps(changed)))

    loaded = store.load(token)
    assert loaded.get("geometry_stale"), "eslesmeyen kimlik 'temiz' sayildi"
    assert loaded["options"] == record["options"]                                        # nothing moved
    with pytest.raises(ValueError, match="tarihsel"):
        store.build(token, loaded["revision"])


def test_the_raw_record_is_backed_up_before_any_migration(tmp_path):
    """P01-a.1: the user's own file is preserved, re-openable, before the new options replace anything."""
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE_SHEET.read_bytes())["token"]
    raw = _as_legacy(store, token)
    store.load(token)
    backup = store.folder(token) / "session.backup.json"
    assert backup.is_file()
    assert json.loads(backup.read_text()) == raw            # exactly the pre-migration session
    assert "geometry_version" not in json.loads(backup.read_text())


def test_a_changed_edge_id_or_measurement_id_is_not_the_same_geometry(tmp_path):
    """The audit's F03 counter-example, with the corrected expectation.

    The audit probe asserted `_same_geometry(...) is True` while an edge id and a measurement id had both
    changed (it read the absent `span_id` field). The correct rule: ids decide, and a moved coordinate
    alone does not — that is the old build's leftover, reported by `_moved_geometry`, not a reader change.
    """
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE_SHEET.read_bytes())["token"]
    base = store.load(token)["options"]
    assert guided._same_geometry(base, json.loads(json.dumps(base)))

    changed_edge = json.loads(json.dumps(base))
    next(p for p in changed_edge["profiles"] if p.get("edges"))["edges"][0]["id"] = "reader_changed_edge"
    assert not guided._same_geometry(base, changed_edge)
    assert any("kenar kimlikleri" in step for step in guided._geometry_diff(base, changed_edge))

    changed_measure = json.loads(json.dumps(base))
    changed_measure["measurements"][0]["id"] = "different_text"
    assert not guided._same_geometry(base, changed_measure)
    assert any("ölçü kimlikleri" in step for step in guided._geometry_diff(base, changed_measure))

    moved_end = json.loads(json.dumps(base))
    profile = next(p for p in moved_end["profiles"] if p.get("edges"))
    profile["edges"][0]["start"] = [profile["edges"][0]["start"][0] + 37.0, profile["edges"][0]["start"][1] - 11.0]
    assert guided._same_geometry(base, moved_end)            # same drawing, moved coordinates
    assert guided._moved_geometry(base, moved_end) >= 1      # ... and that is not silent


def test_a_record_whose_edge_id_changed_is_stale_not_refreshed(tmp_path, monkeypatch):
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE_SHEET.read_bytes())["token"]
    record = _as_legacy(store, token)
    changed = json.loads(json.dumps(record["options"]))
    next(p for p in changed["profiles"] if p.get("edges"))["edges"][0]["id"] = "reader_changed_edge"
    monkeypatch.setattr(guided, "drawing_options", lambda observations: json.loads(json.dumps(changed)))

    loaded = store.load(token)
    assert loaded.get("geometry_stale"), "kenar kimligi degisimi 'temiz' sayildi"
    assert "kenar kimlikleri" in loaded["geometry_stale"]["reason"], loaded["geometry_stale"]
    assert loaded["options"] == record["options"]            # nothing moved
    with pytest.raises(ValueError, match="tarihsel"):
        store.build(token, loaded["revision"])


def test_an_unreadable_source_is_stale_not_a_crash(tmp_path):
    """P01-a.5: the version marker's absence proves nothing, so an unreadable source must stop the build
    with a reason instead of raising out of every `load` (the audit's "one remembered failure")."""
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE_SHEET.read_bytes())["token"]
    _as_legacy(store, token)
    junk = b"this is no longer a drawing"
    (store.folder(token) / "source.pdf").write_bytes(junk)
    path = store.folder(token) / "session.json"
    record = json.loads(path.read_text())
    record["source_sha256"] = hashlib.sha256(junk).hexdigest()    # the digest matches; the reader still fails
    path.write_text(json.dumps(record, ensure_ascii=False))

    loaded = store.load(token)                                # must not raise
    assert loaded.get("geometry_stale"), loaded.get("geometry_stale")
    assert "okunamadı" in loaded["geometry_stale"]["reason"], loaded["geometry_stale"]
    assert (store.folder(token) / "session.backup.json").is_file()
    assert store.load(token)["geometry_stale"] == loaded["geometry_stale"]     # remembered, idempotent
    with pytest.raises(ValueError, match="tarihsel"):
        store.build(token, loaded["revision"])
