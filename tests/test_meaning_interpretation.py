"""The measuring instrument itself: label pairing, id mapping and the verdict classes.

A wrong instrument would report a wrong measurement, so the comparison is tested on synthetic
labels before any model answer is judged: labels are evaluation input only, and an ambiguous or
incomplete label must downgrade the verdict instead of inventing agreement.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

import meaning_interpretation as mi  # noqa: E402  (needs eval/ on the path)


EVIDENCE = {
    "printed": [
        {"span_id": "pdf-0", "value": 100.0, "unit": "mm", "text": "100,00", "kind": "linear"},
        {"span_id": "pdf-1", "value": 80.0, "unit": "mm", "text": "80,00", "kind": "linear"},
        {"span_id": "pdf-3", "value": 6.8, "unit": "mm", "text": "6,80 THRU ALL", "kind": "linear", "count": 4},
    ],
    "claims": [
        {"span_id": "pdf-0", "form": "distance", "anchors": [
            {"geometry_id": "g9", "kind": "circle-centre", "point_mm": [-50.35, -30.21]},
            {"geometry_id": "g11", "kind": "circle-centre", "point_mm": [50.36, -30.21]}]},
        {"span_id": "pdf-1", "form": "distance", "anchors": [
            {"geometry_id": "g4", "kind": "arc-rim", "point_mm": [-51.37, -40.23]},
            {"geometry_id": "g2", "kind": "arc-rim", "point_mm": [-51.37, 40.23]}]},
        {"span_id": "pdf-3", "form": "diameter", "anchors": [
            {"geometry_id": "g12", "kind": "circle-centre", "point_mm": [-50.35, 30.21]}],
         "matched_geometry": ["g9", "g12", "g10", "g11"]},
    ],
    "geometry": {"circles": [
        {"id": "g9", "diameter_mm": 6.85, "centre_mm": [-50.35, -30.21]},
        {"id": "g10", "diameter_mm": 6.84, "centre_mm": [50.36, 30.21]},
        {"id": "g11", "diameter_mm": 6.84, "centre_mm": [50.36, -30.21]},
        {"id": "g12", "diameter_mm": 6.85, "centre_mm": [-50.35, 30.21]}]},
}

LABEL = {
    "printed": [{"span_id": "d1", "value": 100.0, "unit": "mm"},
                {"span_id": "d2", "value": 80.0, "unit": "mm"},
                {"span_id": "d4", "value": 6.8, "unit": "mm", "count": 4}],
    "claims": [
        {"span_id": "d1", "form": "distance", "between": ["h1", "h2"]},
        {"span_id": "d2", "form": "distance", "between": ["arc_top_left", "arc_bottom_left"]},
        {"span_id": "d4", "form": "diameter", "matched_geometry": ["h1", "h2", "h3", "h4"]},
    ],
    "geometry": {"circles": [
        {"id": "h1", "centre_mm": [-50.0, -30.0]}, {"id": "h2", "centre_mm": [50.0, -30.0]},
        {"id": "h3", "centre_mm": [-50.0, 30.0]}, {"id": "h4", "centre_mm": [50.0, 30.0]}]},
}


def answer(kind="distance", axis="horizontal", between=("g9", "g11"), matched=(), unresolved=False,
           status="needs_review", errors=(), question=""):
    """A judged candidate: the axis is derived from the pair, so it is reported beside it."""
    return {"status": status, "errors": list(errors), "questions": [question] if question else [],
            "axis": axis,
            "interpretation": None if status in ("invalid", "unavailable") else {
                "span_id": "pdf-0", "kind": kind, "between": list(between),
                "matched": list(matched), "unresolved": unresolved, "question": question, "reason": "r"}}


def test_label_is_paired_by_printed_value_and_unit():
    assert mi.pair_label_with_reading(EVIDENCE, LABEL) == {"d1": "pdf-0", "d2": "pdf-1", "d4": "pdf-3"}
    doubled = {"printed": [{"span_id": "x", "value": 100.0, "unit": "mm"}]}
    assert mi.pair_label_with_reading({**EVIDENCE, "printed": EVIDENCE["printed"] + [
        {"span_id": "pdf-9", "value": 100.0, "unit": "mm"}]}, doubled) == {}


def test_a_positional_label_gives_kind_axis_and_binding_in_reading_ids():
    pairs = mi.pair_label_with_reading(EVIDENCE, LABEL)
    expected = mi.expected_for_measurement(EVIDENCE, LABEL, "pdf-0", pairs)
    assert expected["form"] == "distance" and expected["axis"] == "horizontal"
    assert expected["ids"] == ["g11", "g9"] and expected["binding_checkable"] is True
    assert expected["unmapped_label_ids"] == []


def test_a_label_without_coordinates_cannot_check_a_binding():
    pairs = mi.pair_label_with_reading(EVIDENCE, LABEL)
    expected = mi.expected_for_measurement(EVIDENCE, LABEL, "pdf-1", pairs)
    assert expected["form"] == "distance" and "axis" not in expected
    assert expected["binding_checkable"] is False and expected["unmapped_label_ids"]
    verdict = mi.compare(answer(axis="vertical"), expected)
    assert verdict["class"] == "correct" and verdict["fields"] == {"kind": True}


def test_a_diameter_label_checks_the_geometry_it_sizes():
    pairs = mi.pair_label_with_reading(EVIDENCE, LABEL)
    expected = mi.expected_for_measurement(EVIDENCE, LABEL, "pdf-3", pairs)
    assert expected["ids"] == ["g10", "g11", "g12", "g9"] and expected["binding_checkable"] is True
    right = mi.compare(answer(kind="diameter", axis="none", between=(), matched=("g9", "g12", "g10", "g11")),
                       expected)
    assert right["class"] == "correct"
    wrong = mi.compare(answer(kind="diameter", axis="none", between=(), matched=("g9", "g12")), expected)
    assert wrong["class"] == "partial" and wrong["fields"] == {"kind": True, "binding": False}
    bad_kind = mi.compare(answer(kind="count", axis="none", between=(), matched=("g9", "g12", "g10", "g11")),
                          expected)
    assert bad_kind["class"] == "partial" and bad_kind["fields"]["kind"] is False


def test_verdict_classes_separate_correctness_from_ambiguity_and_failure():
    pairs = mi.pair_label_with_reading(EVIDENCE, LABEL)
    expected = mi.expected_for_measurement(EVIDENCE, LABEL, "pdf-0", pairs)
    assert mi.compare(answer(kind="diameter", axis="vertical", between=("g9", "g12")),
                      expected)["class"] == "contradiction"
    assert mi.compare(answer(between=("g9", "g11"), axis="vertical"), expected)["class"] == "partial"
    unresolved = mi.compare(answer(kind="unclear", axis="none", between=(), unresolved=True,
                                   status="needs_input", question="which edges?"), expected)
    assert unresolved["class"] == "unresolved" and unresolved["detail"] == "which edges?"
    assert mi.compare(answer(status="invalid", errors=["ölçüde olmayan geometri kimliği: ['g99']"]),
                      expected)["class"] == "invalid"
    assert mi.compare(answer(), {})["class"] == "no_label"
    assert mi.compare(answer(), {"form": "distance"})["fields"] == {"kind": True}


def test_the_summary_counts_correct_and_ambiguous_separately():
    pairs = mi.pair_label_with_reading(EVIDENCE, LABEL)
    expected = mi.expected_for_measurement(EVIDENCE, LABEL, "pdf-0", pairs)
    rows = [{"verdict": mi.compare(answer(), expected), "checks": {"reading_binding_confirmed": True}},
            {"verdict": mi.compare(answer(kind="diameter", axis="vertical", between=("g9", "g12")),
                                   expected), "checks": {}},
            {"verdict": mi.compare(answer(kind="unclear", axis="none", between=(), unresolved=True,
                                          status="needs_input", question="?"), expected), "checks": {}}]
    summary = mi.summarise(rows)
    assert summary == {"measurements": 3, "classes": {"correct": 1, "contradiction": 1, "unresolved": 1},
                       "correct": 1, "ambiguous": 1, "answers_agreed_with_reading": 1,
                       "binding_scored_beyond_contract": {"right": 0, "wrong": 0}}


def _fake_run(tmp_path, monkeypatch, answer_text, judge_version="interpretation-contract-v2"):
    """A stored run folder and evidence pack shaped exactly like the harness writes them."""
    import json

    from drawingto3d.interpret import interpret_measurement, measurement_context
    from test_planner import FakeChat

    folder = tmp_path / "out" / "probe-01"
    (folder / "requests").mkdir(parents=True)
    (folder / "answers").mkdir()
    context = measurement_context(EVIDENCE, "pdf-0")
    stem = "case-a--pdf-0--circle_spacing_x"
    candidate = interpret_measurement(
        FakeChat(answer_text), EVIDENCE, "pdf-0",
        on_request=lambda payload: (folder / "requests" / f"{stem}.request.json").write_text(
            json.dumps(payload, ensure_ascii=False)))
    dumped = candidate.model_dump(mode="json")
    dumped["request"]["judge_version"] = judge_version
    (folder / "answers" / f"{stem}.json").write_text(json.dumps(dumped))
    row = {"span_id": "pdf-0", "name": "circle_spacing_x", "entry": {"value": 100.0, "unit": "mm"},
           "answer": dumped, "expected": {}, "verdict": {"class": "no_label", "fields": {}}}
    case = {"id": "case-a", "drawing": "examples/x.pdf", "label_pairs": {}, "summary": {}, "measurements": [row]}
    (folder / "case-a.json").write_text(json.dumps({**case, "measurements": [row]}))
    pack = mi.evidence_pack({"cases": [case], "status": "complete", "versions": {}, "settings": {}}, folder)
    pack_path = folder / "evidence.json"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False))
    return folder, pack_path, stem


def test_evidence_check_reproduces_judges_and_flags_tampering(tmp_path, monkeypatch):
    import json

    answer = json.dumps({"span_id": "pdf-0", "kind": "distance", "axis": "horizontal",
                         "between": ["g9", "g11"], "matched": [], "unresolved": False,
                         "question": "", "reason": "two hole centres"})
    folder, pack_path, stem = _fake_run(tmp_path, monkeypatch, answer)
    assert mi.check_pack(pack_path) == 0
    # A tampered raw answer must not pass as the finished record.
    stored = json.loads((folder / "answers" / f"{stem}.json").read_text())
    stored["answer"] = stored["answer"].replace("g11", "g12")
    (folder / "answers" / f"{stem}.json").write_text(json.dumps(stored))
    assert mi.check_pack(pack_path) == 1
    # An older contract is skipped, not silently accepted as reproducible.
    (folder / "answers" / f"{stem}.json").write_text(json.dumps(
        {**stored, "answer": stored["answer"].replace("g12", "g11")}))
    _, pack_path_old, _ = _fake_run(tmp_path / "old", monkeypatch, answer, judge_version="")
    assert mi.check_pack(pack_path_old) == 0


def test_two_measurements_of_one_callout_are_not_confused(tmp_path, monkeypatch):
    """A printed '4 x Ø6,8' yields a dimension and a count: the check keys on (source, name)."""
    import json

    answer = json.dumps({"span_id": "pdf-0", "kind": "distance",
                         "between": ["g9", "g11"], "matched": [], "unresolved": False,
                         "question": "", "reason": "two hole centres"})
    folder, pack_path, stem = _fake_run(tmp_path, monkeypatch, answer)
    case_path = folder / "case-a.json"
    case = json.loads(case_path.read_text())
    second = json.loads(json.dumps(case["measurements"][0]))
    second["name"] = "circle_spacing_x_count"
    second["answer"]["answer"] = answer.replace("g11", "g12")
    second["answer"]["interpretation"]["between"] = ["g9", "g12"]
    (folder / "answers" / "case-a--pdf-0--circle_spacing_x_count.json").write_text(
        json.dumps(second["answer"]))
    (folder / "requests" / "case-a--pdf-0--circle_spacing_x_count.request.json").write_text(
        (folder / "requests" / f"{stem}.request.json").read_text())
    case["measurements"].append(second)
    case_path.write_text(json.dumps(case))
    pack_path.write_text(json.dumps(mi.evidence_pack(
        {"cases": [case], "status": "complete", "versions": {}, "settings": {}}, folder), ensure_ascii=False))
    assert mi.check_pack(pack_path) == 0


def test_a_malformed_answer_is_still_scored_on_the_geometry_it_names():
    """A diameter answered as two ends is invalid — but its binding can still be called wrong."""
    expected = {"form": "diameter", "ids": ["g10", "g11", "g12", "g9"], "binding_checkable": True}
    malformed = {"status": "invalid", "errors": ["diameter için iki uç değil, eşleşen geometri gerekli"],
                 "interpretation": {"span_id": "pdf-3", "kind": "diameter", "between": ["g9", "g12"],
                                    "matched": [], "unresolved": False, "question": "", "reason": "r"}}
    verdict = mi.compare(malformed, expected)
    assert verdict["class"] == "invalid"
    scored = verdict["binding_beyond_contract"]
    assert scored["ids"] == ["g12", "g9"] and scored["expected_ids"] == expected["ids"]
    assert scored["right"] is False and scored["contract_status"] == "invalid"
    # The same shape with the right set scores as right; a label that cannot check the binding scores nothing.
    right = {**malformed, "interpretation": {**malformed["interpretation"],
                                             "between": [], "matched": ["g9", "g12", "g10", "g11"]}}
    assert mi.compare(right, expected)["binding_beyond_contract"]["right"] is True
    assert mi.compare(malformed, {"form": "diameter"})["binding_beyond_contract"] == {}
    assert mi.compare({"status": "invalid", "errors": ["x"], "interpretation": None},
                      expected)["binding_beyond_contract"] == {}


def test_rescoring_a_stored_run_calls_no_model_and_writes_beside_it(tmp_path):
    import json

    folder = tmp_path / "run-01"
    folder.mkdir()
    (folder / "run.json").write_text(json.dumps({
        "versions": {"judge": "interpretation-contract-v4"}, "status": "complete",
        "cases": [{"id": "case-a", "measurements": [
            {"span_id": "pdf-0", "name": "w", "answer": {"status": "needs_review", "errors": [],
                                                         "interpretation": {"kind": "distance", "between": ["g9", "g11"],
                                                                           "matched": [], "unresolved": False}},
             "expected": {"form": "distance", "ids": ["g11", "g9"], "binding_checkable": True}},
            {"span_id": "pdf-3", "name": "d", "answer": {"status": "invalid", "errors": ["şekil"],
                                                         "interpretation": {"kind": "diameter", "between": ["g9", "g12"],
                                                                            "matched": [], "unresolved": False}},
             "expected": {"form": "diameter", "ids": ["g10", "g11", "g12", "g9"], "binding_checkable": True}}]}]}))
    assert mi.rescore(folder) == 0
    written = json.loads((folder / "rescore.json").read_text())
    assert written["judge"] == "interpretation-contract-v4"
    summary = written["cases"][0]["summary"]
    assert summary["classes"] == {"correct": 1, "invalid": 1}
    assert summary["binding_scored_beyond_contract"] == {"right": 0, "wrong": 1}
    # The run record is not rewritten by a rescore.
    assert "rescore" not in (folder / "run.json").read_text()


def _review_row(corrupted, answer, injected, reading):
    row = {"proposal_corrupted": corrupted, "proposal_injected": injected, "proposal_reading": reading,
           "answer": {"status": "needs_review", "errors": [], "interpretation": {
               "span_id": "pdf-0", "kind": answer["kind"], "between": answer.get("between", []),
               "matched": answer.get("matched", []), "unresolved": False, "question": "", "reason": "r"}}}
    return {**row, "review": mi.review_verdict(row)}


def test_a_review_answer_is_scored_by_the_defect_not_by_the_label():
    injected = {"kind": "distance", "between": ["g11", "g10"], "matched": []}
    reading = {"kind": "distance", "between": ["g11", "g9"], "matched": []}
    copied = _review_row(True, {"kind": "distance", "between": ["g11", "g10"]}, injected, reading)
    assert copied["review"] == {"class": "defect_missed", "right": False, "copied": True}
    caught = _review_row(True, {"kind": "distance", "between": ["g9", "g11"]}, injected, reading)
    assert caught["review"] == {"class": "defect_caught", "right": True, "copied": False}
    # Disagreeing with the defect is not enough: a third, still wrong binding is not a correction.
    third = _review_row(True, {"kind": "distance", "between": ["g9", "g10"]}, injected, reading)
    assert third["review"]["class"] == "defect_caught" and third["review"]["right"] is False
    kept = _review_row(False, {"kind": "distance", "between": ["g9", "g11"]}, reading, reading)
    assert kept["review"] == {"class": "clean_kept", "right": True, "copied": True}
    alarm = _review_row(False, {"kind": "distance", "between": ["g9", "g10"]}, reading, reading)
    assert alarm["review"] == {"class": "false_alarm", "right": False, "copied": False}
    broken = {"proposal_corrupted": True, "proposal_injected": injected, "proposal_reading": reading,
              "answer": {"status": "invalid", "errors": ["şekil"], "interpretation": None}}
    assert mi.review_verdict(broken)["class"] == "no_binding"
    # A reading that bound nothing offers nothing to keep: that is not a false alarm.
    nothing = {"kind": "unclear", "between": [], "matched": []}
    unbound = _review_row(False, {"kind": "distance", "between": ["g9", "g10"]}, nothing, nothing)
    assert unbound["review"]["class"] == "no_reading_binding"
    assert mi.review_summary([unbound])["false_alarms"] == 0
    assert mi.review_summary([unbound])["no_reading_binding"] == 1


def test_the_review_summary_reports_detection_and_false_alarms_separately():
    injected = {"kind": "distance", "between": ["g11", "g10"], "matched": []}
    reading = {"kind": "distance", "between": ["g11", "g9"], "matched": []}
    rows = [_review_row(True, {"kind": "distance", "between": ["g11", "g10"]}, injected, reading),
            _review_row(True, {"kind": "distance", "between": ["g9", "g11"]}, injected, reading),
            _review_row(True, {"kind": "distance", "between": ["g9", "g10"]}, injected, reading),
            _review_row(False, {"kind": "distance", "between": ["g9", "g11"]}, reading, reading),
            _review_row(False, {"kind": "distance", "between": ["g9", "g10"]}, reading, reading)]
    summary = mi.review_summary(rows)
    assert summary == {"corrupted": 3, "defect_caught": 2, "clean": 2, "false_alarms": 1, "copied": 2,
                       "binding_wrong_beyond_copy": 1, "no_reading_binding": 0, "unusable_answer": 0}
    assert mi.summarise([{**row, "verdict": {"class": "correct", "fields": {}}} for row in rows])["review"] == summary


def test_agreement_with_the_reading_is_read_from_either_record_shape():
    """The harness stores it as `reading_agreement`, the pack as `checks`; one key alone read zero."""
    assert mi.summarise([{"verdict": {"class": "correct", "fields": {}}, "reading_agreement": True}])[
        "answers_agreed_with_reading"] == 1
    assert mi.summarise([{"verdict": {"class": "correct", "fields": {}},
                          "checks": {"reading_binding_confirmed": True}}])[
        "answers_agreed_with_reading"] == 1
    assert mi.summarise([{"verdict": {"class": "correct", "fields": {}}, "reading_agreement": False}])[
        "answers_agreed_with_reading"] == 0
    assert mi.summarise([{"verdict": {"class": "correct", "fields": {}}}])[
        "answers_agreed_with_reading"] == 0


def test_a_verified_diameter_identifies_the_geometry_when_the_frames_disagree():
    """A label written in the part's own frame still scores the binding, because a size is an identity.

    Measured need: the third sheet's label carries STEP coordinates and every position lands 12-34 mm
    from its measured counterpart, so the position path mapped nothing. The size path needs the label's
    verified diameter and the reading's own measured sizes (a claim records the size of the geometry it
    matched, taken from that geometry's radius), and refuses unless exactly one measured id is that size.
    """
    evidence = {
        "printed": [{"span_id": "pdf-19", "value": 30.0, "unit": "mm", "text": "30", "kind": "diameter"}],
        "claims": [{"span_id": "pdf-19", "form": "diameter", "drawn_mm": 30.73,
                    "matched_geometry": ["g68"], "anchors": [
                        {"geometry_id": "g68", "kind": "arc-centre", "point_mm": [11.27, 180.71]}]}],
    }
    label = {
        "printed": [{"span_id": "d11", "value": 30.0, "unit": "mm"}],
        "claims": [{"span_id": "d11", "form": "diameter", "matched_geometry": ["bore30"]}],
        "geometry": {"circles": [{"id": "bore30", "diameter_mm": 30.0, "centre_mm": [9.55, 40.0]}]},
    }
    pairs = mi.pair_label_with_reading(evidence, label)
    expected = mi.expected_for_measurement(evidence, label, "pdf-19", pairs)
    assert expected["reading_id_mapping"] == {"bore30": "g68"}
    assert expected["mapping_basis"] == {"bore30": "diameter"}
    assert expected["binding_checkable"] is True and expected["ids"] == ["g68"]
    assert mi.compare(answer(kind="diameter", axis="none", between=(), matched=("g65", "g68")),
                      expected)["class"] == "partial"
    assert mi.compare(answer(kind="diameter", axis="none", between=(), matched=("g68",)),
                      expected)["class"] == "correct"


def test_two_geometries_of_the_same_size_leave_the_diameter_label_unmapped():
    """Ø40 meets two arcs of the same radius on that sheet: an ambiguous size maps nothing."""
    evidence = {
        "printed": [{"span_id": "pdf-22", "value": 40.0, "unit": "mm", "text": "40", "kind": "diameter"}],
        "claims": [{"span_id": "pdf-22", "form": "diameter", "drawn_mm": 41.08,
                    "matched_geometry": ["g125", "g134"]}],
    }
    label = {
        "printed": [{"span_id": "d14", "value": 40.0, "unit": "mm"}],
        "claims": [{"span_id": "d14", "form": "diameter", "matched_geometry": ["boss40"]}],
        "geometry": {"circles": [{"id": "boss40", "diameter_mm": 40.0, "centre_mm": [61.24, 32.73]}]},
    }
    pairs = mi.pair_label_with_reading(evidence, label)
    expected = mi.expected_for_measurement(evidence, label, "pdf-22", pairs)
    assert expected["reading_id_mapping"] == {}
    assert expected["mapping_basis"] == {}
    assert expected["unmapped_label_ids"] == ["boss40"]
    assert expected["binding_checkable"] is False


def test_a_label_value_that_the_reading_reproduces_earns_the_readings_own_anchors():
    """Third mapping path: neither frame has to agree, but the two numbers must.

    Measured need: on the third sheet 8 of 17 rows stayed unscored because the label names faces in the
    part's frame (top_face, z=±13 …) while the reading reports ids in the sheet's frame, 12–34 mm apart, so
    the position path maps nothing. Where the reading's own measurement of the callout agrees with the
    label's independently verified value, the expectation becomes the reading's anchors — the model is then
    scored against the reading on a row the reading is itself confirmed on, and `mapping_basis` says
    "value" so a reader can see which comparison was actually made. A disagreement earns nothing.
    """
    evidence = {
        "printed": [{"span_id": "pdf-8", "value": 80.0, "unit": "mm", "text": "80", "kind": "linear"}],
        "claims": [{"span_id": "pdf-8", "form": "distance", "drawn_mm": 82.0, "anchors": [
            {"geometry_id": "g4", "kind": "arc-rim", "point_mm": [-51.37, -40.23]},
            {"geometry_id": "g2", "kind": "arc-rim", "point_mm": [-51.37, 40.23]}]}],
        "geometry": {"circles": []},
    }
    label = {
        "printed": [{"span_id": "d1", "value": 80.0, "unit": "mm"}],
        "claims": [{"span_id": "d1", "form": "distance", "between": ["top_face", "bottom_face"],
                    "verified_mm": 80.0, "verified": "step"}],
        "geometry": {"circles": []},
    }
    pairs = mi.pair_label_with_reading(evidence, label)
    expected = mi.expected_for_measurement(evidence, label, "pdf-8", pairs)
    assert expected["mapping_basis"] == {"top_face": "value", "bottom_face": "value"}
    assert expected["binding_checkable"] is True and expected["ids"] == ["g2", "g4"]
    assert mi.compare(answer(kind="distance", axis="vertical", between=("g2", "g4")),
                      expected)["fields"]["binding"] is True

    # The same row with a reading that measured something else: no expectation is invented.
    far_off = {**evidence, "claims": [{**evidence["claims"][0], "drawn_mm": 60.0}]}
    refused = mi.expected_for_measurement(far_off, label, "pdf-8", pairs)
    assert refused["binding_checkable"] is False
    assert refused["unmapped_label_ids"] == ["top_face", "bottom_face"]
    assert refused["ids"] == []


def test_a_repeated_value_is_paired_by_the_kind_both_sides_published():
    """Four rows print 20 and two print 40 on the third sheet; a bare value cannot pair them.

    Measured need: six of the seventeen label rows stayed unpaired for this reason although both sides had
    been measured — the reading publishes the kind it classified (the Ø/R prefix), so value+unit+kind pairs
    them. An unstated kind is not evidence: where either side is silent the old value+unit rule decides, and a
    value repeated with the same kind is still left unpaired rather than guessed.
    """
    evidence = {"printed": [
        {"span_id": "pdf-13", "value": 20.0, "unit": "mm", "kind": "radius"},
        {"span_id": "pdf-17", "value": 20.0, "unit": "mm", "kind": "diameter"},
        {"span_id": "pdf-15", "value": 20.0, "unit": "mm", "kind": "linear"}]}
    label = {"printed": [
        {"span_id": "d5", "value": 20.0, "unit": "mm", "kind": "radius"},
        {"span_id": "d7", "value": 20.0, "unit": "mm", "kind": "linear"}]}
    assert mi.pair_label_with_reading(evidence, label) == {"d5": "pdf-13", "d7": "pdf-15"}
    doubled = {"printed": evidence["printed"] + [{"span_id": "pdf-23", "value": 20.0, "unit": "mm", "kind": "linear"}]}
    assert mi.pair_label_with_reading(doubled, label) == {"d5": "pdf-13"}       # d7 has two linear candidates
    silent = mi.pair_label_with_reading(doubled, {"printed": [
        {"span_id": "d9", "value": 20.0, "unit": "mm", "kind": "diameter"},
        {"span_id": "d15", "value": 20.0, "unit": "mm"}]})
    assert silent == {"d9": "pdf-17"}                                          # the silent row cannot be placed


def test_a_size_callout_the_value_confirms_takes_the_readings_own_match():
    """One label name can cover two reading ids: a Ø40 boss is drawn as two arcs.

    Measured need: the R20 row and the Ø40 row were the last two the diameter path refused (two equal arcs
    leave `_unique_by_diameter` nothing to choose). Where the label's independently verified value agrees with
    the reading's own measurement of the callout, the expectation becomes the reading's own match, so the
    mapping stays one-to-one only where the names and the ids line up.
    """
    evidence = {
        "printed": [{"span_id": "pdf-13", "value": 20.0, "unit": "mm", "text": "R20", "kind": "radius"}],
        "claims": [{"span_id": "pdf-13", "form": "radius", "drawn_mm": 20.54,
                    "anchors": [{"geometry_id": "g134", "kind": "arc-centre", "point_mm": [-26.76, -20.61]}],
                    "matched_geometry": ["g134", "g125"]}],
        "geometry": {"circles": []},
    }
    label = {
        "printed": [{"span_id": "d5", "value": 20.0, "unit": "mm", "kind": "radius"}],
        "claims": [{"span_id": "d5", "form": "radius", "matched_geometry": ["fillet_r20"], "verified_mm": 20.0}],
        "geometry": {"circles": []},
    }
    pairs = mi.pair_label_with_reading(evidence, label)
    expected = mi.expected_for_measurement(evidence, label, "pdf-13", pairs)
    assert expected["binding_checkable"] is True and expected["ids"] == ["g125", "g134"]
    assert expected["mapping_basis"] == {"fillet_r20": "value"}
    assert mi.compare(answer(kind="radius", axis="none", between=(), matched=("g125", "g134")),
                      expected)["fields"]["binding"] is True
    far_off = {**evidence, "claims": [{**evidence["claims"][0], "drawn_mm": 12.0}]}
    assert mi.expected_for_measurement(far_off, label, "pdf-13", pairs)["binding_checkable"] is False
