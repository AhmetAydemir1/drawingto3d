"""G2 callout candidate adapter (PLAN-18 §23): pure `Observations → CalloutCandidate` mapping.

The adapter is machine observation only: it turns printed-phrase regions into deterministic,
provenance-preserving candidates. It reads no file, runs no OCR, calls no model, touches no store,
and never promotes `value/unit/kind/count` or the machine hint into a decision. Identity is the
canonical JSON + SHA-256 of (source digest, page, canonical region, detector version, source kind);
the source path, filename, text, confidence and list position are deliberately outside it.
"""
import hashlib
import json

from drawingto3d.callouts import CALLOUT_DETECTOR_VERSION, callout_candidates_from_observations
from drawingto3d.observe import Frame, Observations, SourceRef, TextObservation
from drawingto3d.schema import BBox

DIGEST = "d" * 64


def observations(*texts, width=1000, height=500, digest=DIGEST, page=0, ref="/nonexistent/drawing.pdf"):
    """An in-memory observation record — the adapter must never need the ref to exist."""
    return Observations(
        source=SourceRef(ref=ref, sha256=digest, page=page),
        frame=Frame(width=width, height=height),
        text_placement="as-is",
        texts=list(texts),
    )


def text(id="t0", text="Ø8", x=100.0, y=50.0, w=200.0, h=100.0, method="pdf-text", **over):
    return TextObservation(id=id, text=text, bbox=BBox(x=x, y=y, w=w, h=h), method=method, **over)


def detect(record, **over):
    return callout_candidates_from_observations(record, **{"geometry_version": 3, **over})


def codes(result):
    return [(row.code, row.observation_id) for row in result.diagnostics]


def expected_id(digest, page, region, detector_version, source_kind):
    """PLAN-18 §14: the documented canonical payload, assembled here by hand."""
    payload = {"detector_version": detector_version, "page_index": page, "region": region,
               "source_digest": digest, "source_kind": source_kind}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --- normalization and provenance -----------------------------------------

def test_a_pixel_box_normalizes_into_the_page_region():
    result = detect(observations(text()))
    (candidate,) = result.candidates
    assert candidate.region == [0.1, 0.1, 0.3, 0.3]                 # PLAN-18 §10 pinli örnek
    assert candidate.crop_region == candidate.region                # G2: crop = region (padding G3'ün işi)


def test_the_candidate_carries_source_page_provenance_and_detector():
    result = detect(observations(text(id="t7")))
    (candidate,) = result.candidates
    assert candidate.source_digest == DIGEST
    assert candidate.page_index == 0
    assert candidate.observation_ids == ["t7"]
    assert candidate.detector_version == CALLOUT_DETECTOR_VERSION
    assert result.detector_version == CALLOUT_DETECTOR_VERSION
    assert candidate.geometry_version == 3
    assert candidate.machine_text_hint == "Ø8"
    assert candidate.id == expected_id(DIGEST, 0, [0.1, 0.1, 0.3, 0.3],
                                       CALLOUT_DETECTOR_VERSION, "vector_text")


def test_pdf_text_maps_to_vector_text():
    result = detect(observations(text(method="pdf-text")))
    assert result.candidates[0].source_kind == "vector_text"
    assert result.diagnostics == []


def test_tesseract_maps_to_raster_region():
    result = detect(observations(text(method="tesseract-tsv", confidence=88.0)))
    assert result.candidates[0].source_kind == "raster_region"
    assert result.diagnostics == []


def test_an_unknown_method_is_named_as_such_and_never_inferred_from_the_path():
    result = detect(observations(text(method="vlm-ocr"), ref="/drawings/sheet.pdf"))
    (candidate,) = result.candidates
    assert candidate.source_kind == "observation"                   # dosya uzantısından tahmin yok
    assert codes(result) == [("unknown_text_method", "t0")]
    assert candidate.observation_ids == ["t0"]


def test_value_unit_count_and_kind_never_become_decisions():
    reading = text(text="4x Ø8 THRU", value=8.0, unit="mm", kind="diameter", count=4)
    result = detect(observations(reading))
    (candidate,) = result.candidates
    assert candidate.model_dump().keys() == {"id", "source_digest", "page_index", "region", "crop_region",
                                             "source_kind", "observation_ids", "detector_version",
                                             "geometry_version", "machine_text_hint"}
    assert candidate.machine_text_hint == "4x Ø8 THRU"              # ham ipucu; hiçbir semantic terfi yok
    assert set(result.model_dump().keys()) == {"detector_version", "candidates", "diagnostics"}


# --- purity, determinism, identity ----------------------------------------

def test_the_adapter_never_mutates_its_input():
    record = observations(text(id="t0"), text(id="t1", x=400.0, y=300.0, text="Ø10"))
    before = record.model_dump(mode="json")
    detect(record)
    assert record.model_dump(mode="json") == before


def test_the_same_observations_produce_the_same_identity():
    record = observations(text())
    first, second = detect(record), detect(record)
    assert [row.id for row in first.candidates] == [row.id for row in second.candidates]
    assert first.model_dump() == second.model_dump()


def test_input_order_does_not_change_the_identity_set_or_the_output_order():
    a = text(id="t0", x=100.0, y=50.0)
    b = text(id="t1", x=50.0, y=300.0, text="Ø10")
    c = text(id="t2", x=600.0, y=50.0, text="25")
    forward = detect(observations(a, b, c))
    backward = detect(observations(c, b, a))
    assert [row.id for row in forward.candidates] == [row.id for row in backward.candidates]
    # Kararlı sıra (PLAN-18 §16): önce y0, sonra x0
    assert [row.region for row in forward.candidates] == [[0.1, 0.1, 0.3, 0.3],
                                                          [0.6, 0.1, 0.8, 0.3],
                                                          [0.05, 0.6, 0.25, 0.8]]


def test_each_identity_component_separates_the_id():
    base = detect(observations(text())).candidates[0].id
    digest = detect(observations(text(), digest="e" * 64)).candidates[0].id
    region = detect(observations(text(x=110.0))).candidates[0].id
    version = detect(observations(text()), detector_version="callout-detector/2").candidates[0].id
    kind = detect(observations(text(method="tesseract-tsv"))).candidates[0].id
    assert len({base, digest, region, version, kind}) == 5


def test_a_renamed_source_keeps_the_id_but_a_changed_digest_does_not():
    first = detect(observations(text(), ref="/a/plate.pdf")).candidates[0].id
    renamed = detect(observations(text(), ref="/b/renamed-elsewhere.pdf")).candidates[0].id
    changed = detect(observations(text(), digest="f" * 64)).candidates[0].id
    assert first == renamed                                          # kimlik yol değil, kaynak baytları
    assert first != changed


def test_the_hint_is_not_part_of_the_identity():
    a = detect(observations(text(text="Ø8"))).candidates[0]
    b = detect(observations(text(text="Ø10"))).candidates[0]
    assert a.id == b.id
    assert (a.machine_text_hint, b.machine_text_hint) == ("Ø8", "Ø10")


def test_geometry_version_is_recorded_but_not_part_of_the_identity():
    three = detect(observations(text()), geometry_version=3).candidates[0]
    four = detect(observations(text()), geometry_version=4).candidates[0]
    assert three.id == four.id                                       # geometry_version kimlikte yok
    assert (three.geometry_version, four.geometry_version) == (3, 4)


# --- exact dedup and hints -------------------------------------------------

def test_an_exact_duplicate_merges_provenance():
    first = text(id="t1")
    second = text(id="t0")                                           # aynı bölge, aynı hint
    result = detect(observations(second, first))
    (candidate,) = result.candidates
    assert candidate.observation_ids == ["t0", "t1"]                 # sıralı birleşim
    assert candidate.machine_text_hint == "Ø8"
    assert result.diagnostics == []


def test_conflicting_hints_leave_the_hint_open_with_a_diagnostic():
    result = detect(observations(text(id="t1", text="Ø8"), text(id="t0", text="Ø10")))
    (candidate,) = result.candidates
    assert candidate.machine_text_hint is None                       # çelişen ipucu gerçek değildir
    assert codes(result) == [("duplicate_hint_conflict", "t0")]


def test_nearby_but_distinct_regions_stay_two_candidates():
    result = detect(observations(text(id="t0"), text(id="t1", x=101.0)))
    assert len(result.candidates) == 2                               # körlemesine birleştirme yok
    assert {tuple(row.observation_ids) for row in result.candidates} == {("t0",), ("t1",)}


def test_the_same_observation_id_with_different_regions_is_never_overwritten():
    result = detect(observations(text(id="t0"), text(id="t0", x=400.0)))
    assert [row.observation_ids for row in result.candidates] == [["t0"], ["t0"]]


def test_a_merged_provenance_set_is_capped_at_the_schema_limit_with_a_diagnostic():
    rows = [text(id=f"t{index}") for index in range(201)]            # aynı bölgenin 201 sahibi
    result = detect(observations(*rows))
    (candidate,) = result.candidates
    assert len(candidate.observation_ids) == 200
    assert codes(result) == [("provenance_ids_capped", "t0")]


# --- invalid input: skip + diagnostic, never clamp -------------------------

def test_a_zero_area_box_is_rejected_without_a_candidate():
    for over in ({"w": 0.0}, {"h": 0.0}, {"w": -5.0}):
        result = detect(observations(text(**over)))
        assert result.candidates == []
        assert codes(result) == [("invalid_bbox_area", "t0")]


def test_non_finite_boxes_are_rejected():
    for over in ({"x": float("nan")}, {"y": float("inf")}, {"w": float("-inf")}, {"h": float("nan")}):
        result = detect(observations(text(**over)))
        assert result.candidates == []
        assert codes(result) == [("invalid_bbox_nonfinite", "t0")]


def test_a_box_outside_the_frame_is_rejected_never_clamped():
    for over in ({"x": 900.0}, {"y": 450.0}, {"x": -10.0}):          # 1000×500 çerçeve
        result = detect(observations(text(**over)))
        assert result.candidates == []                               # sessiz kırpma yok
        assert codes(result) == [("bbox_outside_frame", "t0")]


def test_a_collapsed_canonical_region_is_rejected_with_a_diagnostic():
    result = detect(observations(text(x=100.0, y=50.0, w=1e-9, h=100.0)))   # 8 basamakta genişlik sıfır
    assert result.candidates == []
    assert codes(result) == [("region_collapsed", "t0")]


def test_an_invalid_frame_yields_an_honest_empty_result():
    for width, height in ((0, 500), (1000, 0)):
        result = detect(observations(text(), width=width, height=height))
        assert result.candidates == []
        assert codes(result) == [("invalid_frame", None)]


def test_empty_texts_yield_an_honest_empty_result():
    result = detect(observations())
    assert result.candidates == []                                   # sahte kutu üretilmez
    assert codes(result) == [("no_text_observations", None)]


def test_empty_texts_with_geometry_never_fabricate_text_boxes():
    record = observations()
    record.primitives = []                                           # geometri varlığı kutu doğurmaz
    record.notes = ["ölçü ifadesi yok"]
    result = detect(record)
    assert result.candidates == []
    assert codes(result) == [("no_text_observations", None)]


def test_a_page_other_than_zero_is_explicitly_unsupported():
    result = detect(observations(text(), page=1))
    assert result.candidates == []                                   # sessizce sayfa 0'a çevrilmez
    assert codes(result) == [("unsupported_page", None)]


def test_one_bad_box_does_not_take_the_whole_batch_down():
    result = detect(observations(text(id="t0"), text(id="t1", w=0.0), text(id="t2", x=500.0)))
    assert [row.observation_ids for row in result.candidates] == [["t0"], ["t2"]]
    assert codes(result) == [("invalid_bbox_area", "t1")]


# --- diagnostics determinism ----------------------------------------------

def test_diagnostics_are_deterministic_and_deduplicated():
    bad_a = text(id="t1", w=0.0)
    bad_b = text(id="t0", y=600.0)
    overlap = text(id="t1", w=0.0)                                   # aynı kimlikli ikinci bozuk kayıt
    forward = detect(observations(bad_b, bad_a, overlap, text(id="t9")))
    backward = detect(observations(overlap, text(id="t9"), bad_a, bad_b))
    assert codes(forward) == [("bbox_outside_frame", "t0"), ("invalid_bbox_area", "t1")]
    assert codes(backward) == codes(forward)


# --- purity guard (PLAN-18 §24/§25) ---------------------------------------

def test_the_adapter_never_reaches_for_uuid_random_or_the_filesystem():
    from drawingto3d import callouts
    leaked = {"uuid", "random", "Path", "subprocess", "os", "socket", "tempfile",
              "observe", "observe_raster", "cv2", "numpy"} & set(vars(callouts))
    assert leaked == set()                                           # kimlik yolu: yalnız sha256(canonical json)
