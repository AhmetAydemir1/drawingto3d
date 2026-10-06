"""G5 deterministic target proposal (`PLAN.md` §10): ranked, evidence-based, never a decision.

Everything runs on a synthetic record built here — the module reads a session record and nothing else
(no store, no CAD, no model, no reference). The plan's nine cases are pinned one by one, plus the
tiers, the ranking order and the ways a callout legitimately gets `[]`.
"""
import copy

import pytest

from callout_fixtures import ARC, SOURCE, TOKEN, WIRE, circle, kinds, record

from drawingto3d import callout_bind, callout_parse
from drawingto3d.callout_bind import EVIDENCE_TIERS, TARGET_KINDS, propose_targets
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION, geometry_key


# --- PLAN §10 — the nine required cases -------------------------------------------------

def test_one_diameter_and_one_circle_gives_that_circle():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32], circles=[circle("c0", [45.0, 45.0], mm=8.0)])
    proposals = propose_targets(row, "k1")
    assert kinds(proposals) == ["circle"] and proposals[0].target_ids == ["c0"]
    assert proposals[0].evidence_tier in ("T1", "T2", "T3")


def test_one_radius_and_one_arc_gives_that_arc():
    proposals = propose_targets(record("R8", [0.62, 0.10, 0.80, 0.30], circles=[], arcs=[ARC]), "k1")
    assert kinds(proposals) == ["arc"] and proposals[0].target_ids == ["a0"]
    assert proposals[0].evidence_tier == "T3"


def test_four_of_eight_gives_a_group_of_exactly_four():
    circles = [circle(f"c{i}", center, mm=16.0)
               for i, center in enumerate([[35.0, 40.0], [55.0, 40.0], [35.0, 60.0], [55.0, 60.0]])]
    row = record("4x Ø16", [0.05, 0.15, 0.30, 0.40], circles=circles, count=4)
    proposals = propose_targets(row, "k1")
    assert proposals[0].target_kind == "circle_group"
    assert proposals[0].target_ids == ["c0", "c1", "c2", "c3"]
    assert proposals[0].evidence_tier == "T3"
    assert any(item.kind == "count_compatibility" for item in proposals[0].evidence)


def test_a_leader_beats_proximity():
    """İki daire de bölgeye yakın; ipucu çizgisi yalnız c1'e temas ediyor → sıra onun."""
    circles = [circle("c0", [45.0, 45.0], mm=12.0), circle("c1", [95.0, 45.0], mm=12.0)]
    row = record("Ø12", [0.05, 0.15, 0.40, 0.40], circles=circles, leader=[[60.0, 30.0], [95.0, 41.0]])
    proposals = propose_targets(row, "k1")
    assert proposals[0].target_ids == ["c1"] and proposals[0].evidence_tier == "T1"
    assert proposals[1].target_ids == ["c0"] and proposals[1].evidence_tier == "T3"


def test_two_compatible_circles_stay_two_proposals_in_a_stable_order():
    circles = [{"id": "c0", "center": [45.0, 45.0], "radius": 6.0},
               {"id": "c1", "center": [60.0, 50.0], "radius": 6.0}]
    row = record("Ø12", [0.05, 0.15, 0.30, 0.40], circles=circles)
    first = propose_targets(row, "k1")
    assert len(first) == 2 and sorted(row.target_ids[0] for row in first) == ["c0", "c1"]
    assert [row.target_ids for row in first] == [row.target_ids for row in propose_targets(row, "k1")]


def test_no_compatible_target_is_an_empty_proposal_list():
    circles = [{"id": "c9", "center": [260.0, 20.0], "radius": 3.0}]        # bölgeden uzak, ölçü tutmuyor
    row = record("Ø8", [0.05, 0.60, 0.20, 0.80], circles=circles)
    assert propose_targets(row, "k1") == []


def test_a_diameter_proposal_never_creates_a_hole():
    """Öneri bir *hedef* söyler: daire → delik çıkarımı burada yapılmaz (PLAN §10)."""
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32])
    before = copy.deepcopy(row["decisions"])
    proposals = propose_targets(row, "k1")
    assert proposals and all(row.target_kind in TARGET_KINDS for row in proposals)
    blob = str([row.model_dump() for row in proposals])
    assert "hole" not in blob and "pocket" not in blob and "through" not in blob
    assert row["decisions"] == before, "öneri hiçbir kararı yazmaz"


def test_a_count_does_not_invent_geometry():
    """Metin 4 diyor ama çizimde 2 uyumlu daire var: grup uydurulmaz, tekil öneriler sunulur."""
    circles = [{"id": "c0", "center": [45.0, 45.0], "radius": 6.0},
               {"id": "c1", "center": [70.0, 45.0], "radius": 6.0}]
    row = record("4x Ø12", [0.05, 0.15, 0.30, 0.40], circles=circles, count=4)
    proposals = propose_targets(row, "k1")
    assert proposals and all(row.target_kind == "circle" for row in proposals)
    assert not any(row.target_kind == "circle_group" for row in proposals)


def test_the_ranking_is_total_and_deterministic():
    circles = [{"id": "c0", "center": [45.0, 45.0], "radius": 6.0},
               {"id": "c1", "center": [95.0, 45.0], "radius": 6.0}]
    row = record("Ø12 mm", [0.05, 0.15, 0.40, 0.40], circles=circles, leader=[[60.0, 30.0], [95.0, 41.0]],
                 claims=[{"span_id": "s1", "form": "diameter", "printed_mm": 12.0,
                          "anchors": [{"geometry_id": "c0", "kind": "centre", "point_mm": [0, 0]}]}])
    order = [row.target_ids for row in propose_targets(row, "k1")]
    assert order == [["c1"], ["c0"]]
    tiers = [row.evidence_tier for row in propose_targets(row, "k1")]
    assert tiers == sorted(tiers, key=EVIDENCE_TIERS.index), "sıra kanıt katmanına göre artar"
    for _ in range(3):
        assert [row.target_ids for row in propose_targets(row, "k1")] == order


# --- katmanlar --------------------------------------------------------------------------

def test_a_printed_dimension_for_the_geometry_is_tier_two():
    row = record("Ø12", [0.05, 0.15, 0.40, 0.40],
                 claims=[{"span_id": "s7", "form": "diameter", "printed_mm": 12.0,
                          "anchors": [{"geometry_id": "c0", "kind": "centre", "point_mm": [0, 0]}]}])
    proposal = propose_targets(row, "k1")[0]
    assert proposal.evidence_tier == "T2" and proposal.target_ids == ["c0"]
    assert any(item.kind == "printed_dimension" and "s7" in item.ref for item in proposal.evidence)


def test_a_still_current_confirmation_comes_back_as_tier_zero():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32],
                 stored_target={"callout_id": "k1", "target_kind": "circle", "target_ids": ["c0"],
                                "geometry_version": 3, "profile_id": "outline_0",
                                "transcription_revision": 1, "parser_version": CALLOUT_PARSER_VERSION,
                                "evidence": [{"kind": "user_click", "ref": "c0"}], "status": "confirmed"})
    proposal = propose_targets(row, "k1")[0]
    assert proposal.evidence_tier == "T0" and proposal.target_ids == ["c0"]


def test_the_measured_size_decides_between_proximity_and_semantic_fit():
    """Ölçek varsa ölçü karşılaştırılır: çizilen Ø12 ≈ yazılan Ø12 → T3; Ø8 yazılmışsa yalnız yakınlık."""
    circles = [{"id": "c0", "center": [45.0, 45.0], "radius": 12.0}]        # 2 px/mm → Ø12 mm
    matching = propose_targets(record("Ø12 mm", [0.10, 0.20, 0.30, 0.35], circles=circles), "k1")[0]
    assert matching.evidence_tier == "T3" and "Ø12.000 mm" in matching.evidence[0].ref
    far = propose_targets(record("Ø8 mm", [0.10, 0.20, 0.30, 0.35], circles=circles), "k1")[0]
    assert far.evidence_tier == "T5" and far.target_ids == ["c0"]
    assert any(item.kind == "size_mismatch" for item in far.evidence), "uyuşmazlık saklanmaz"


def test_a_unit_less_number_uses_the_sheets_declared_unit():
    """Birim yazılmadıysa sayfanın beyan edilen birimi (kalibrasyon) ölçüyü çözer; o da yoksa karşılaştırılmaz."""
    circles = [circle("c0", [45.0, 45.0], mm=12.0)]
    proposal = propose_targets(record("Ø12", [0.10, 0.20, 0.30, 0.35], circles=circles), "k1")[0]
    assert proposal.evidence_tier == "T3" and "Ø12.000 mm" in proposal.evidence[0].ref
    no_sheet = propose_targets(record("Ø12", [0.10, 0.20, 0.30, 0.35], circles=circles,
                                      calibration=False), "k1")[0]
    assert no_sheet.evidence_tier == "T3"
    assert any("birim yok" in item.ref for item in no_sheet.evidence), "birimsiz ölçü karşılaştırılmaz"


def test_an_inch_text_is_compared_in_millimetres():
    circles = [{"id": "c0", "center": [45.0, 45.0], "radius": 12.0}]        # 24 px = 12 mm = 0.472 in
    row = record("Ø0.472 in", [0.10, 0.20, 0.32, 0.35], circles=circles)
    assert propose_targets(row, "k1")[0].evidence_tier == "T3"


def test_a_plain_number_finds_the_two_ends_that_measure_it():
    row = record("50", [0.05, 0.05, 0.45, 0.20])            # 50 mm = 100 px = g0'ın uzunluğu
    proposals = propose_targets(row, "k1")
    assert proposals and proposals[0].target_kind == "vertex_pair"
    assert proposals[0].target_ids == ["g0:start", "g0:end"]
    assert proposals[0].evidence_tier == "T3"


def test_a_contour_whose_own_size_is_the_number_is_offered_too():
    row = record("50", [0.05, 0.05, 0.45, 0.20])            # kontur 100×60 px = 50×30 mm
    proposals = propose_targets(row, "k1")
    contours = [item for item in proposals if item.target_kind == "profile"]
    assert contours and contours[0].target_ids == ["outline_0"]


def test_without_a_scale_no_size_is_compared():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32], px_per_mm=None)
    proposal = propose_targets(row, "k1")[0]
    assert proposal.target_ids == ["c0"]
    assert "ölçek yok" in " ".join(item.ref for item in proposal.evidence)


def test_a_short_list_is_a_menu_not_a_flood():
    circles = [{"id": f"c{i}", "center": [30.0 + 6 * i, 45.0], "radius": 6.0} for i in range(14)]
    row = record("Ø12", [0.0, 0.0, 1.0, 1.0], circles=circles)
    assert len(propose_targets(row, "k1")) == callout_bind.PROPOSAL_LIMIT
    assert len(propose_targets(row, "k1", limit=2)) == 2


# --- öneri üretilmeyen hâller -----------------------------------------------------------

def test_an_ignored_callout_gets_no_proposal():
    assert propose_targets(record("Ø8", [0.10, 0.20, 0.20, 0.32], ignored=True), "k1") == []


def test_without_a_reading_there_is_nothing_to_propose():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32])
    row["callout_parses"] = []
    assert propose_targets(row, "k1") == []
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32])
    row["decisions"]["transcriptions"] = []
    assert propose_targets(row, "k1") == []


@pytest.mark.parametrize("text", ["M8x1.25", "Ø8 10", "Ø8 HELLO"])
def test_an_unreadable_text_proposes_nothing(text):
    row = record(text, [0.10, 0.20, 0.30, 0.35])
    assert row["callout_parses"][0]["status"] != "parsed"
    assert propose_targets(row, "k1") == []


def test_a_stale_reading_is_not_used():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32])
    row["callout_parses"][0]["parser_version"] = "callout-parser/0"
    assert propose_targets(row, "k1") == []


def test_an_unknown_callout_is_refused_quietly():
    assert propose_targets(record("Ø8", [0.10, 0.20, 0.20, 0.32]), "nope") == []


def test_the_proposal_carries_the_geometry_version_it_was_read_against():
    row = record("Ø8", [0.10, 0.20, 0.20, 0.32])
    for proposal in propose_targets(row, "k1"):
        assert proposal.geometry_version == row["geometry_version"]
        assert proposal.callout_id == "k1"
        assert proposal.evidence and all(item.kind and item.ref for item in proposal.evidence)
