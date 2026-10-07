"""G12.1 — callout disposition kapsamı ve sahte-hazır engeli (PLAN-24 §10–§16).

Saf katman: `callout_coverage(record)` ve `build_readiness(record)` yalnız kaydı okur. Buradaki her
test §17 matrisinin bir satırıdır:

* toplu „modele ait değil“ (legacy) artık 'hazır' sayılamaz;
* gerçek bir ölçü `build_relevant_unsupported` ise build açılmaz;
* başlık bloğu `not_model_input` bloklamaz;
* `redundant` dayanağı olmadan/diğer kayıt güncel değilken bloklar;
* derlenen callout `build_applied` olur;
* legacy ignored/unbindable kayıt `legacy_unclassified`'tır.
"""
import copy
import json

from drawingto3d import callout_readiness
from drawingto3d.callout_parse import semantic_parse

from callout_fixtures import record as fixture_record

REGION = [0.1, 0.2, 0.4, 0.5]


def _add_callout(row, callout_id, text, *, target=None):
    """İkinci bir callout: aday + metin (+ istenirse onaylı hedef) — saf kayıt cerrahisi."""
    row["callout_candidates"].append({"id": callout_id, "source_digest": row["source_sha256"],
                                      "page_index": 0, "region": [0.5, 0.2, 0.8, 0.5],
                                      "crop_region": [0.5, 0.2, 0.8, 0.5],
                                      "source_kind": "vector_text", "observation_ids": [],
                                      "detector_version": "callout-detector/1",
                                      "geometry_version": row["geometry_version"],
                                      "machine_text_hint": text})
    row["decisions"]["transcriptions"].append({"callout_id": callout_id, "raw_text": text,
                                               "normalized_text": text, "entered_by": "user",
                                               "source_region": [0.5, 0.2, 0.8, 0.5], "revision": 1})
    row["callout_parses"].append(semantic_parse(row["decisions"]["transcriptions"][-1]).model_dump(mode="json"))
    if target is not None:
        row["decisions"]["callout_targets"].append({
            "callout_id": callout_id, "transcription_revision": 1,
            "parser_version": row["callout_parses"][-1]["parser_version"], "geometry_version": row["geometry_version"],
            "target_kind": "circle", "target_ids": ["c0"],
            "evidence": [{"kind": "user_click", "ref": "c0"}], "status": "confirmed", "reconfirm": False,
            "geometry_key": record_key(row), **target})
    return row


def record_key(row):
    from drawingto3d.callout_models import geometry_key
    return geometry_key(row, row["decisions"])


def _coverage(row):
    return callout_readiness.callout_coverage(row)


def test_a_compiled_callout_is_build_applied_and_nothing_blocks():
    row = fixture_record("4 x Ø8 THRU", REGION, stored_target={})
    coverage = _coverage(row)
    assert coverage["build_applied"] == ["k1"]
    assert coverage["coverage_complete"] is True
    readiness = callout_readiness.build_readiness(row, sheet_issues=[])
    # G12.2 (PLAN-25 §41): kayıt artık kullanıcının onayladığı üretim biçimini de taşır, öyleyse
    # "hazır" sözü tam anlamıyla geçerlidir — kapsam da strateji de kapıyı kapatmaz.
    assert readiness["ready"] is True, readiness["categories"]
    assert readiness["questions"] == [], readiness["questions"]
    assert readiness["coverage"]["build_applied"] == ["k1"]


def test_title_block_as_not_model_input_does_not_block():
    row = fixture_record("A4", REGION, disposition="not_model_input")
    coverage = _coverage(row)
    assert coverage["not_model_input"] == ["k1"]
    assert coverage["coverage_complete"] is True
    readiness = callout_readiness.build_readiness(row, sheet_issues=[])
    assert readiness["ready"] is True and readiness["questions"] == [], readiness["categories"]


def test_a_real_dimension_marked_build_relevant_unsupported_blocks_the_build():
    row = fixture_record("80,00", REGION, disposition="build_relevant_unsupported",
                         disposition_reason="yazılı daralma ölçüsü; bu sürümde hedefi yok")
    coverage = _coverage(row)
    assert coverage["build_relevant_unsupported"] == ["k1"]
    assert coverage["coverage_complete"] is False
    readiness = callout_readiness.build_readiness(row, sheet_issues=[])
    assert readiness["ready"] is False
    assert any(q["category"] == "unsupported_build_relevant" and q["callout_id"] == "k1"
               for q in readiness["questions"]), readiness["questions"]


def test_blanket_legacy_ignore_cannot_claim_coverage_complete():
    """§10/§12: 66 aday → 66 'yok sayıldı' → hazır DEĞİL; eski kayıt sınıflandırılmamıştır."""
    row = fixture_record("4 x Ø8 THRU", REGION, ignored=True)
    _add_callout(row, "k2", "120,00")
    row["decisions"]["callout_reviews"].append({"callout_id": "k2", "ignored": True, "revision": 1})
    coverage = _coverage(row)
    assert coverage["legacy_unclassified"] == ["k1", "k2"]
    assert coverage["coverage_complete"] is False
    readiness = callout_readiness.build_readiness(row, sheet_issues=[])
    assert readiness["ready"] is False
    named = {q["callout_id"] for q in readiness["questions"] if q["category"] == "legacy_unclassified"}
    assert named == {"k1", "k2"}


def test_legacy_unbindable_is_also_unclassified_not_unsupported():
    """§11: eski „bağlanamaz“ bloğu yeni sözleşmede kanıtsızdır — legacy_unclassified."""
    row = fixture_record("50,00", REGION, unbindable=True)
    coverage = _coverage(row)
    assert coverage["legacy_unclassified"] == ["k1"]
    assert coverage["build_relevant_unsupported"] == []
    assert callout_readiness.build_readiness(row, sheet_issues=[])["ready"] is False


def test_redundant_with_a_decision_reference_does_not_block():
    row = fixture_record("15,00", REGION, disposition="redundant", duplicate_of="decision:calibration")
    coverage = _coverage(row)
    assert coverage["redundant"] == ["k1"]
    assert coverage["invalid_duplicate"] == []
    assert coverage["coverage_complete"] is True
    readiness = callout_readiness.build_readiness(row, sheet_issues=[])
    assert readiness["ready"] is True and readiness["questions"] == [], readiness["categories"]


def test_redundant_citing_another_covered_callout_does_not_block():
    row = fixture_record("4 x Ø8 THRU", REGION, stored_target={})
    _add_callout(row, "k2", "M8 - 6H THRU ALL")
    row["decisions"]["callout_reviews"].append({"callout_id": "k2", "ignored": False, "revision": 1,
                                                "disposition": "redundant", "duplicate_of": "k1"})
    coverage = _coverage(row)
    assert coverage["redundant"] == ["k2"]
    assert coverage["build_applied"] == ["k1"]
    assert coverage["coverage_complete"] is True


def test_redundant_with_unknown_or_absent_reference_blocks():
    unknown = fixture_record("15,00", REGION, disposition="redundant", duplicate_of="k9-not-there")
    coverage = _coverage(unknown)
    assert coverage["invalid_duplicate"] == ["k1"]
    assert coverage["coverage_complete"] is False
    readiness = callout_readiness.build_readiness(unknown, sheet_issues=[])
    assert readiness["ready"] is False
    assert any(q["category"] == "stale_duplicate_reference" for q in readiness["questions"])

    absent_decision = fixture_record("15,00", REGION, disposition="redundant", duplicate_of="decision:thickness")
    coverage = _coverage(absent_decision)               # fixture'da thickness kararı yok
    assert coverage["invalid_duplicate"] == ["k1"]
    assert callout_readiness.build_readiness(absent_decision, sheet_issues=[])["ready"] is False


def test_redundant_citing_an_undecided_callout_blocks():
    row = fixture_record("4 x Ø8 THRU", REGION, stored_target={})
    _add_callout(row, "k2", "50,00")                    # k2: metin var, hedef/karar yok
    row["decisions"]["callout_reviews"].append({"callout_id": "k1", "ignored": False, "revision": 1,
                                                "disposition": "redundant", "duplicate_of": "k2"})
    coverage = _coverage(row)
    assert coverage["invalid_duplicate"] == ["k1"]
    assert coverage["coverage_complete"] is False


def test_stale_transcription_is_counted_stale_not_silently_dropped():
    row = fixture_record("4 x Ø8 THRU", REGION, region_override=[0.2, 0.2, 0.5, 0.5])
    coverage = _coverage(row)
    assert coverage["stale"] == ["k1"]
    assert coverage["coverage_complete"] is False
    assert callout_readiness.build_readiness(row, sheet_issues=[])["ready"] is False


def test_an_undecided_candidate_is_unclassified():
    row = fixture_record("4 x Ø8 THRU", REGION, ignored=True)
    row["decisions"]["callout_reviews"] = []            # karar tamamen kaldırıldı
    coverage = _coverage(row)
    assert coverage["unclassified"] == ["k1"]
    assert coverage["coverage_complete"] is False
    assert callout_readiness.build_readiness(row, sheet_issues=[])["ready"] is False


def test_disposition_state_is_reported_per_callout_in_the_public_shape():
    """Panelin gördüğü etkin liste kararı taşır: disposition + dayanak (UI §13'ün verisi)."""
    from drawingto3d.callout_models import effective_callouts
    row = fixture_record("15,00", REGION, disposition="redundant", duplicate_of="decision:calibration",
                         disposition_reason=None)
    callout = effective_callouts(row)[0]
    assert callout["disposition"] == "redundant"
    assert callout["duplicate_of"] == "decision:calibration"
    assert callout["disposition_reason"] is None
    copy.deepcopy(row)                                  # kayıt saf kalmalı: kopya alınabilmeli
    json.dumps(row)
