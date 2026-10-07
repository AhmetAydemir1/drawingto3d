"""G12R — bağımsız incelemenin bulguları için regresyonlar (20261007-guided-g12-2-independent-review).

Bu dosya incelemenin kendi kanıtlarını ürüne karşı çiviler; her test önce KIRMIZI olacak şekilde yazıldı.

- **R-01**: tarayıcının JSON turu sunucunun `10.0` kanıt değerini `10` yapar; aynı karar "sahte" sayılıp
  normal kayıt reddediliyordu. Değişen/uydurulan strateji yine reddedilmeli.
- **R-02**: `redundant` onayı kendi okuma/bölge bağlamına ve dayanağın ONAYLANAN değerine bağlı olmalı;
  metin, bölge ya da dayanak değişince kapsam yeniden onay istemeli (yoksa eski onay sessizce kapsar).
"""
from __future__ import annotations

import json
import pathlib

import pytest

from drawingto3d import callout_readiness
from drawingto3d.guided import GuidedStore

PLATE = pathlib.Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _browser_json(value):
    """Tarayıcının kendi turu: `JSON.stringify(10.0)` → `"10"` (ondalık, tam sayıysa düşer)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _browser_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_browser_json(item) for item in value]
    return value


def _session(tmp_path, *, thickness=10.0):
    """Kabul koşusunun kendi kurulumu: kontur + ölçek (100,00) + kalınlık + izleme onayı."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    options = opened["options"]
    span = next((row for row in options["measurements"] if row.get("text", "").strip() == "1 00,00"), None)
    circles = {row["id"]: row for row in options["circles"]}
    decisions = dict(store.load(token)["decisions"])
    decisions.update({
        "calibration": {"first": list(circles["g9"]["center"]), "second": list(circles["g11"]["center"]),
                        "value": 100.0, "unit": "mm", "span_id": (span or {}).get("id")},
        "profile_id": "outline_1", "thickness": thickness, "trace_acknowledged": True})
    store.save(token, opened["revision"], decisions)
    return store, token


def _revision(store, token):
    return store.load(token)["revision"]


def _redundant_rows(store, token):
    return {row["callout_id"]: row for row in
            (store.load(token)["decisions"].get("callout_reviews") or [])}


def _claim_a_callout(store, token, reference="decision:thickness", index=0):
    """Gerçek bir callout'u 'zaten temsil ediliyor' diye onaylar (sunucu dayanağı sabitler)."""
    rows = store.public(store.load(token))["callouts"]
    callout_id = rows[index]["id"]
    store.edit_callout(token, _revision(store, token), "set_disposition",
                       {"callout_id": callout_id, "disposition": "redundant", "duplicate_of": reference})
    return callout_id


# --- R-01: tarayıcı JSON turu --------------------------------------------------------------

def test_a_browser_json_roundtrip_of_the_approved_strategy_is_not_forged(tmp_path):
    """İnceleme kanıtı: kanıttaki `10.0` tarayıcıda `10` olur; aynı karar sahte sayılmamalı."""
    store, token = _session(tmp_path)
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    record = store.load(token)
    evidence = json.dumps(record["decisions"]["build_strategy"]["evidence"])
    assert '"value": 10.0' in evidence, evidence          # sunucu kanıtı ondalıklı yazıyor
    posted = json.loads(json.dumps(_browser_json(record["decisions"])))
    assert (json.dumps(posted["build_strategy"]) !=
            json.dumps(record["decisions"]["build_strategy"]))   # tur gerçekten dizgiyi değiştirdi
    state = store.save(token, record["revision"], posted)
    assert state["revision"] >= record["revision"]


def test_a_normal_save_after_the_approval_still_writes(tmp_path):
    """İnceleme senaryosu: onaydan SONRA kalınlık değişikliği normal kayıtla yazılabilmeli."""
    store, token = _session(tmp_path)
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    posted = json.loads(json.dumps(_browser_json(store.load(token)["decisions"])))
    posted["thickness"] = 20.0
    store.save(token, _revision(store, token), posted)
    assert store.load(token)["decisions"]["thickness"] == 20.0


def test_a_changed_strategy_is_still_refused(tmp_path):
    store, token = _session(tmp_path)
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    posted = json.loads(json.dumps(store.load(token)["decisions"]))
    posted["build_strategy"]["kind"] = "revolve_profile"
    with pytest.raises(ValueError):
        store.save(token, _revision(store, token), posted)


def test_a_forged_strategy_key_is_still_refused(tmp_path):
    store, token = _session(tmp_path)
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    posted = json.loads(json.dumps(store.load(token)["decisions"]))
    posted["build_strategy"]["strategy_key"] = "0" * 64
    with pytest.raises(ValueError):
        store.save(token, _revision(store, token), posted)


def test_a_strategy_approved_twice_keeps_one_row_and_a_server_key(tmp_path):
    """Sözleşme: satırın tek yazarı komut; ikinci onay anahtarı SUNUCUDA yeniden hesaplar."""
    store, token = _session(tmp_path)
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    first = store.load(token)["decisions"]["build_strategy"]
    store.set_strategy(token, _revision(store, token), {"kind": "extrude_profile"})
    second = store.load(token)["decisions"]["build_strategy"]
    assert len(second["strategy_key"]) == 64 and first["kind"] == second["kind"] == "extrude_profile"
    posted = json.loads(json.dumps(_browser_json(store.load(token)["decisions"])))
    store.save(token, _revision(store, token), posted)      # ikinci turdan sonra da normal kayıt geçer


# --- R-02: kapsam onayı kendi bağlamına ve dayanağa bağlıdır -------------------------------

def test_the_new_scope_claim_category_has_a_question_and_a_checklist_task():
    """Kategori uydurulmadı: sunucu sorusu metni ve panelin görev adı aynı sözleşmede durur."""
    from drawingto3d.app import ROOT

    assert "stale_scope_claim" in callout_readiness.CATEGORIES
    assert callout_readiness._QUESTION["stale_scope_claim"].startswith("«{id}»")
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "stale_scope_claim:'Kapsam kararını yeniden ver'" in script
    assert "Okuma değişti: kararı yeniden onaylayın." in script


def test_the_approval_records_a_server_side_pin(tmp_path):
    """Onay `duplicate_of` ile birlikte dayanağın O ANKİ değerini ve satırın okumasını sabitler."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    review = _redundant_rows(store, token)[callout_id]
    pin = review.get("duplicate_pin") or {}
    assert pin.get("kind") == "decision" and pin.get("name") == "thickness"
    assert pin.get("value") == {"thickness": 10.0}
    assert pin.get("own", {}).get("region"), pin


def test_changing_the_cited_value_blocks_the_old_approval(tmp_path):
    """İnceleme: kalınlık 10 → 20; eski 'zaten temsil ediliyor' onayı artık kapsamaz."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    assert store.public(store.load(token))["coverage"]["redundant"] == [callout_id]
    store.save(token, _revision(store, token),
               {**store.load(token)["decisions"], "thickness": 20.0})
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == []
    assert coverage["invalid_duplicate"] == [callout_id]
    assert coverage["coverage_complete"] is False
    state = store.readiness(token)
    assert state["ready"] is False
    assert [q for q in state["questions"] if q["callout_id"] == callout_id
            and q["category"] == "stale_duplicate_reference"]


def test_changing_the_reading_text_blocks_the_old_approval(tmp_path):
    """İnceleme: metin 30.00 yapılınca eski onay sürüyordu; artık yeniden onay istemeli."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    store.edit_callout(token, _revision(store, token), "transcribe",
                       {"callout_id": callout_id, "raw_text": "30,00"})
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == []
    assert coverage["stale"] == [callout_id]
    assert coverage["coverage_complete"] is False
    state = store.readiness(token)
    assert state["ready"] is False
    assert [q for q in state["questions"] if q["callout_id"] == callout_id
            and q["category"] == "stale_scope_claim"]


def test_moving_the_region_blocks_the_old_approval(tmp_path):
    """İnceleme: bölge taşınınca transcription/parse `stale` oluyordu ama kapsam kapanıyordu."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    store.edit_callout(token, _revision(store, token), "edit_region",
                       {"callout_id": callout_id, "region": [0.12, 0.2, 0.42, 0.5]})
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == [] and coverage["stale"] == [callout_id]
    assert store.readiness(token)["ready"] is False


def test_re_approving_after_the_change_restores_coverage(tmp_path):
    """Düzeltme yolu: kullanıcı yeni durum üzerinden yeniden onaylar → kapsam yine kapanır."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    store.save(token, _revision(store, token),
               {**store.load(token)["decisions"], "thickness": 20.0})
    store.edit_callout(token, _revision(store, token), "set_disposition",
                       {"callout_id": callout_id, "disposition": "redundant",
                        "duplicate_of": "decision:thickness"})
    coverage = store.public(store.load(token))["coverage"]
    # Not: paftanın kalan satırları bu testte karara bağlanmadığı için `coverage_complete` beklenmez;
    # iddia, onayın kendisinin kapsamaya dönmesidir.
    assert coverage["redundant"] == [callout_id] and coverage["invalid_duplicate"] == []
    review = _redundant_rows(store, token)[callout_id]
    assert review["duplicate_pin"]["value"] == {"thickness": 20.0}


def test_undoing_the_re_approval_blocks_again(tmp_path):
    """Geri alma: yeniden onay geri alınınca eski (bayat) onay geri gelmez — satır açık kalır."""
    store, token = _session(tmp_path)
    callout_id = _claim_a_callout(store, token)
    store.save(token, _revision(store, token),
               {**store.load(token)["decisions"], "thickness": 20.0})
    store.edit_callout(token, _revision(store, token), "set_disposition",
                       {"callout_id": callout_id, "disposition": "redundant",
                        "duplicate_of": "decision:thickness"})
    store.save(token, _revision(store, token), store.load(token)["decisions"], undo=True)
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == [] and coverage["coverage_complete"] is False


def _transcribe_with_target(store, token, callout_id, kind, circles, text):
    """Gerçek kullanıcı yolu: metin + hedef onayı (kabul betiğinin de kullandığı biçim)."""
    store.edit_callout(token, _revision(store, token), "transcribe",
                       {"callout_id": callout_id, "raw_text": text})
    record = store.load(token)
    transcription = next(entry for entry in record["decisions"]["transcriptions"]
                         if entry["callout_id"] == callout_id)
    parse_row = next((entry for entry in record.get("callout_parses") or []
                      if entry["callout_id"] == callout_id), {})
    payload = dict(record["decisions"])
    payload["callout_targets"] = [entry for entry in payload.get("callout_targets") or []
                                  if entry["callout_id"] != callout_id]
    payload["callout_targets"].append({
        "callout_id": callout_id, "target_kind": kind, "target_ids": list(circles),
        "transcription_revision": transcription.get("revision"),
        "parser_version": parse_row.get("parser_version"),
        "evidence": [{"kind": "user_click", "ref": f"{kind} · {', '.join(circles)}"}],
        "reconfirm": False})
    store.save(token, _revision(store, token), payload)


def test_a_citation_chain_breaks_when_the_cited_reading_changes(tmp_path):
    """Zincir: k2 → k1; k1'in okuması değişince k2'nin dayanağı da güncel olmaz."""
    store, token = _session(tmp_path)
    # İpucu public callout satırında değil, kaydın KENDİ adaylarında yaşar (kabul betiği de böyle okur).
    candidates = store.load(token)["callout_candidates"]
    first = next(row["id"] for row in candidates if row.get("machine_text_hint") == "6,80 THRU ALL")
    second = next(row["id"] for row in candidates if row.get("machine_text_hint") == "50,00")
    _transcribe_with_target(store, token, first, "circle_group", ["g9", "g11", "g10", "g12"],
                            "4 x Ø6,80 THRU ALL")
    assert store.public(store.load(token))["coverage"]["build_applied"] == [first]
    store.edit_callout(token, _revision(store, token), "set_disposition",
                       {"callout_id": second, "disposition": "redundant", "duplicate_of": first})
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == [second], coverage["counts"]
    store.edit_callout(token, _revision(store, token), "transcribe",
                       {"callout_id": first, "raw_text": "4 x Ø7,00 THRU ALL"})
    coverage = store.public(store.load(token))["coverage"]
    assert coverage["redundant"] == [] and coverage["invalid_duplicate"] == [second], coverage["counts"]
