"""PLAN §26.4-A: the user's correction of a traced contour, on hand-built contours — no sheet involved.

The rule under test is the promise the interface makes: dropping an edge never invents geometry. What is left
is re-walked, a single gap is closed only within the tolerance the chain itself uses and only when the user
approved the join and no end moves further than the trace itself would move one, and anything else is refused
with the gap it would leave.
"""
import pytest

from drawingto3d import contour_audit
from drawingto3d.guided import (ENDPOINT_IDENTITY_TOLERANCE_PX, ContourFix, correct_profile,
                                 same_physical_point)

TOLERANCE = 20.0
MID_CAP = 10.0


def line(edge_id, start, end):
    return {"id": edge_id, "kind": "line", "start": list(start), "end": list(end)}


def profile(*edges, join_max_px=0.0):
    return {"edges": list(edges), "join_max_px": join_max_px, "points": []}


def corrected(edges, fix, **kwargs):
    return correct_profile(profile(*edges), fix, join_tolerance_px=TOLERANCE, mid_join_px=MID_CAP, **kwargs)


def test_dropping_a_duplicated_side_leaves_a_valid_square_without_moving_anything():
    """The measured failure of the real sheets: a second copy of one side, nothing else wrong."""
    edges = [line("a", (0, 0), (10, 0)), line("d2", (5, 0), (10, 0)), line("b", (10, 0), (10, 10)),
             line("c", (10, 10), (0, 10)), line("d", (0, 10), (0, 0))]
    raw = contour_audit.audit_contour(profile(*edges)["edges"])
    assert raw["ok"] is False and any(issue["kind"] == "overlap" for issue in raw["issues"])
    result = corrected(edges, ContourFix(drop=["d2"]))
    assert result["correction"] == {"dropped": ["d2"], "kept": 4, "joined": 0, "closed_gap_px": 0.0, "moved_px": 0.0}
    after = contour_audit.audit_contour(result["edges"])
    assert after["ok"] is True and after["closure_px"] == 0.0


def test_a_close_gap_after_dropping_closes_only_when_the_join_is_approved():
    """The join is the user's decision: without it the correction does not happen at all."""
    edges = [line("a", (0, 0), (10, 0)), line("x", (10, 0), (10, 3)), line("b", (10, 3), (10, 10)),
             line("c", (10, 10), (0, 10)), line("d", (0, 10), (0, 0))]
    with pytest.raises(ValueError, match="onaylamadan"):
        corrected(edges, ContourFix(drop=["x"]))
    result = corrected(edges, ContourFix(drop=["x"], approve_join=True))
    assert result["correction"]["joined"] == 1 and result["correction"]["closed_gap_px"] == 3.0
    assert result["correction"]["moved_px"] == 1.5
    after = contour_audit.audit_contour(result["edges"])
    assert after["ok"] is True


def test_a_gap_wider_than_the_chains_own_tolerance_is_refused():
    """20 px is what the chain accepts on a raster sheet; a correction may not be more generous than that."""
    edges = [line("a", (0, 0), (10, 0)), line("x", (10, 0), (10, 5)), line("b", (10, 45), (10, 60)),
             line("c", (10, 60), (0, 60)), line("d", (0, 60), (0, 0))]
    with pytest.raises(ValueError, match="açık kaldı"):
        corrected(edges, ContourFix(drop=["x"], approve_join=True))


def test_a_join_that_would_move_an_end_too_far_is_refused():
    """A gap the chain may link is not automatically a gap the user's correction may close.

    On a raster sheet the two limits coincide (tolerance 20 px, each end at most 10 px), so this rule only
    bites when the caller passes a tighter mid cap — the vector sheets' 5.5 px, for instance.
    """
    edges = [line("a", (0, 0), (10, 0)), line("x", (10, 0), (10, 5)), line("b", (10, 20), (10, 40)),
             line("c", (10, 40), (0, 40)), line("d", (0, 40), (0, 0))]
    with pytest.raises(ValueError, match="fazla uzaklaşıyor"):
        correct_profile(profile(*edges), ContourFix(drop=["x"], approve_join=True),
                        join_tolerance_px=TOLERANCE, mid_join_px=5.5)


def test_two_gaps_left_by_one_correction_are_refused():
    """One correction closes one gap; a second open end is a different decision, not a silent guess."""
    edges = [line("a", (0, 0), (10, 0)), line("b", (10, 1), (10, 10)), line("c", (10, 11), (0, 11)),
             line("d", (0, 11), (0, 0)), line("e", (0, 30), (10, 30))]
    with pytest.raises(ValueError, match="ayrı açıklık"):
        corrected(edges, ContourFix(drop=["e"], approve_join=True))


def test_dropping_every_edge_is_refused():
    edges = [line("a", (0, 0), (10, 0)), line("b", (10, 0), (0, 0))]
    with pytest.raises(ValueError, match="kenar kalmadı"):
        corrected(edges, ContourFix(drop=["a", "b"]))


def test_point_equality_is_the_audits_own_tolerance_not_the_repair_budget():
    """G1R3-01: iki uç yalnız denetimin kendi nokta toleransı içinde *aynı nokta*dır.

    Yanı baştaki 20 px onarım bütçesidir: kopuk bir konturun kapanışının ne kadar kaçabileceğini söyler,
    iki ölçülmüş ucun bir nokta olduğunu söylemez. Bu ikisi karıştığında 5/10/20 px'lik gerçek ölçüler
    seçilemiyordu.
    """
    at = [10.0, 10.0]
    assert same_physical_point(at, [10.0, 10.0]) is True
    assert same_physical_point(at, [10.0 + 0.49, 10.0]) is True            # toleransın hemen altı: hâlâ bir nokta
    assert same_physical_point(at, [10.0 + ENDPOINT_IDENTITY_TOLERANCE_PX, 10.0]) is True   # sınırı
    assert same_physical_point(at, [10.0 + 0.51, 10.0]) is False           # hemen üstü: iki ayrı nokta
    assert same_physical_point(at, [10.0, 10.0 - ENDPOINT_IDENTITY_TOLERANCE_PX]) is True   # uzaklık, eksen değil
    assert ENDPOINT_IDENTITY_TOLERANCE_PX == contour_audit.TOLERANCE_PX   # denetimin kendi sözleşmesi
    assert ENDPOINT_IDENTITY_TOLERANCE_PX != TOLERANCE                    # ... ve asla 20 px onarım bütçesi
