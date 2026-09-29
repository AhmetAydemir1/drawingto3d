"""The bound-measurement fit: what the user ties to the drawing, and what the drawing says back.

These are the checks the flow's B slice rests on: one binding overrules a two-click calibration, several
agreeing bindings tighten it, a disagreeing set is *reported* rather than averaged away, and every feature
no binding reaches stays visibly traced.
"""
from __future__ import annotations

import pytest

from drawingto3d.sketch import Binding, diagnose, fit_scale, questions, unbound


def binding(value: float, first, second, span_id: str | None = None, unit: str = "mm") -> Binding:
    return Binding(value=value, unit=unit, span_id=span_id,
                   first={"kind": "centre", "id": first[0], "x": first[1], "y": first[2]},
                   second={"kind": "centre", "id": second[0], "x": second[1], "y": second[2]})


PLATE_EDGE = {"kind": "vertex", "id": "edge:0", "x": 0.0, "y": 0.0}


def test_one_binding_fits_the_scale_and_beats_a_two_click_calibration():
    """A single 100 mm binding between two centres 787.6 px apart fits 7.876 px/mm exactly."""
    fitted = fit_scale([binding(100.0, ("g9", 0.0, 0.0), ("g11", 787.6, 0.0))], 7.82)
    assert fitted["source"] == "bindings"
    assert abs(fitted["px_per_mm"] - 7.876) < 1e-6
    assert fitted["consistent"] and not fitted["conflicts"]
    row = fitted["rows"][0]
    assert row["drawn_mm"] == pytest.approx(100.0, abs=1e-3) and abs(row["residual_mm"]) < 1e-3


def test_two_agreeing_bindings_tighten_the_fit_and_keep_their_residuals_small():
    """80 mm over 629.2 px and 60 mm over 472.5 px: the slope weighs the longer dimension more."""
    fitted = fit_scale([binding(80.0, ("a", 0.0, 0.0), ("b", 629.2, 0.0), "t1"),
                        binding(60.0, ("c", 0.0, 0.0), ("d", 472.5, 0.0), "t2")], None)
    assert fitted["consistent"]
    # 629.2/80 = 7.865 and 472.5/60 = 7.875; the least-squares slope sits between them, nearer the longer.
    assert 7.865 < fitted["px_per_mm"] < 7.875
    assert all(abs(row["residual_mm"]) < 0.2 for row in fitted["rows"])


def test_a_drawing_that_is_not_to_scale_is_reported_not_averaged():
    """A 60 mm binding drawn 8 mm short of the 100 mm binding's scale is a conflict, with both rows kept."""
    fitted = fit_scale([binding(100.0, ("g9", 0.0, 0.0), ("g11", 787.6, 0.0), "t0"),
                        binding(60.0, ("g9", 0.0, 0.0), ("g10", 442.5, 0.0), "t2")], 7.82)
    assert not fitted["consistent"]
    # One scale cannot satisfy both: the fit lands between them and flags *both* rows, one long and one
    # short, instead of quietly believing one of them.
    assert len(fitted["conflicts"]) == 2
    residuals = {row["span_id"]: row["residual_mm"] for row in fitted["conflicts"]}
    assert residuals["t0"] > 1.0 and residuals["t2"] < -2.0
    asked = questions({"conflicts": fitted["conflicts"]})
    assert asked and "t0" in asked[0] and "t2" in asked[0] and "tutarlı değil" in asked[0]


def test_unbound_features_and_the_pre_join_gap_are_reported():
    """What no binding reaches stays traced, and an open contour is named in px."""
    profile = {"edges": [{"kind": "line"}, {"kind": "line"}, {"kind": "arc"}], "join_max_px": 0.25}
    circles = [{"id": "g9"}, {"id": "g11"}, {"id": "g8"}]
    bindings = [binding(100.0, ("g9", 0.0, 0.0), ("g11", 787.6, 0.0), "t0")]
    touched = unbound(profile, circles, bindings)
    assert touched["circles"] == ["g8"] and touched["profile_bound"] is False
    reported = diagnose(profile, circles, bindings, fit_scale(bindings, 7.82))
    assert reported["source"] == "bindings" and reported["bindings"] == 1
    # `join_gap_max_px` is the gap measured *before* a join; the boundary's real closure error belongs to
    # the contour audit (PLAN §26.3) — the two numbers must not wear the same name.
    assert reported["unbound_circles"] == ["g8"] and reported["join_gap_max_px"] == 0.25
    assert reported["px_per_mm"] == pytest.approx(7.876, abs=1e-3)


def test_without_bindings_the_calibration_scale_is_used_unchanged():
    """No binding, no claim: the flow keeps the two-click calibration and says where the scale came from."""
    fitted = fit_scale([], 7.82)
    assert fitted["px_per_mm"] == 7.82 and fitted["source"] == "calibration" and fitted["rows"] == []
    assert questions({"conflicts": []}) == []
