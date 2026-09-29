"""PLAN 8.6: the sheet's own frame and its axis directions are a *product*, not an assumption.

The rendered page frame is what the pixels live in; the part's frame is what the drawing means. On a
rotated sheet the two are not the same, and "page x = part x" is exactly the assumption the plan
forbids. These tests work on synthetic paths only: a border, a part, and the source's own /Rotate.
"""
import numpy as np
import pytest

from drawingto3d.observe import ANGLE_SNAP_DEGREES, Frame, PathObservation, Primitive, rotation_axes, sheet_frame
from drawingto3d.schema import BBox


def rect(path_id, x0, y0, x1, y1, closed=True):
    points = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return PathObservation(id=path_id, object_index=0, path_index=0, closed=closed,
                           bbox=BBox(x=x0, y=y0, w=x1 - x0, h=y1 - y0), points=points)


def edge(path_id, start, end):
    return PathObservation(id=path_id, object_index=0, path_index=1, closed=False,
                           bbox=BBox(x=min(start[0], end[0]), y=min(start[1], end[1]),
                                     w=abs(end[0] - start[0]), h=abs(end[1] - start[1])),
                           points=[list(start), list(end)])


def sheet_delta(paths, frame, rotation, start, end):
    """What the *sheet's own* axes say this drawn edge is — the reading the user will confirm."""
    product = sheet_frame(paths, frame, rotation)
    delta = np.array(end, dtype=float) - np.array(start, dtype=float)
    return {axis.name: float(delta @ np.array(axis.page)) for axis in product.axes}, product


def test_an_upright_sheet_publishes_its_own_frame_and_axes():
    border = rect("p0", 10, 10, 990, 690)
    part = rect("p1", 100, 300, 400, 400)
    product = sheet_frame([border, part], Frame(width=1000, height=700), 0)

    assert product.found is True, product.provenance
    assert product.rect == [10.0, 10.0, 990.0, 690.0]
    assert product.angle_degrees == pytest.approx(0.0, abs=0.6)
    assert product.aligned is True
    assert product.coverage is not None and product.coverage[0] == pytest.approx(0.98, abs=0.005)
    assert product.long_side_px == pytest.approx(980, abs=2) and product.short_side_px == pytest.approx(680, abs=2)
    assert [axis.name for axis in product.axes] == ["x", "y"]
    assert product.axes[0].page == [1.0, 0.0] and product.axes[1].page == [0.0, -1.0]
    assert "p0" in product.provenance and "kaplıyor" in product.provenance


def test_the_sheet_frame_is_not_the_page_frame_when_the_sheet_is_rotated():
    """PLAN 8.6's own acceptance: the same part measures the same in the sheet's frame at 0 and 90."""
    upright = ([rect("p0", 10, 10, 990, 690), edge("p1", (100, 300), (400, 300))],
               Frame(width=1000, height=700), 0)
    rotated = ([rect("p0", 10, 10, 690, 990), edge("p1", (100, 100), (100, 400))],
               Frame(width=700, height=1000), 90)
    upright_delta, upright_product = sheet_delta(*upright, start=(100, 300), end=(400, 300))
    rotated_delta, rotated_product = sheet_delta(*rotated, start=(100, 100), end=(100, 400))

    assert upright_product.axes[0].page == [1.0, 0.0]
    assert rotated_product.axes[0].page == [0.0, 1.0]
    assert upright_delta == pytest.approx(rotated_delta, abs=1e-6)
    assert upright_delta["x"] == pytest.approx(300.0) and upright_delta["y"] == pytest.approx(0.0)
    # The page deltas really do differ — so the equality above is the frame doing its job, not a no-op.
    assert (upright_delta["x"], rotated_delta["x"]) == (300.0, 300.0)


def test_a_portrait_frame_is_aligned_when_its_long_edge_is_vertical():
    """Regression (2/Drawing.pdf, 1653x2339): the frame's long edge is the vertical one there.

    Measuring only the long edge against the page's x axis read a perfectly axis-aligned portrait frame
    as a 90° deviation and put a "rotated sheet" note on an upright sheet. Both edge directions count.
    """
    product = sheet_frame([rect("p0", 118, 39, 1614, 2299)], Frame(width=1653, height=2339), 0)

    assert product.found is True
    assert product.angle_degrees == pytest.approx(0.0, abs=0.6), product.provenance
    assert product.aligned is True and product.notes == [], product.notes
    assert product.long_side_px == pytest.approx(2260, abs=3)


def test_a_sheet_without_a_border_says_so_and_keeps_the_page_axes():
    product = sheet_frame([rect("p0", 100, 100, 200, 200)], Frame(width=1000, height=700), 90)

    assert product.found is False
    assert product.rect is None and product.angle_degrees is None
    assert product.axes[0].page == [0.0, 1.0], product.axes[0]
    assert "bulunamadı" in product.provenance and "1 kapalı yolun" in product.provenance
    assert any("kullanıcı onayı" in note for note in product.notes), product.notes


def test_a_tilted_border_reports_its_own_angle_instead_of_the_page_axes():
    tilt = np.radians(7.0)
    corners = np.array([[10, 10], [990, 10], [990, 690], [10, 690]], dtype=float)
    centre = corners.mean(axis=0)
    rotated = (corners - centre) @ np.array([[np.cos(tilt), -np.sin(tilt)],
                                             [np.sin(tilt), np.cos(tilt)]]) + centre
    border = PathObservation(id="p0", object_index=0, path_index=0, closed=True,
                             bbox=BBox(x=float(rotated[:, 0].min()), y=float(rotated[:, 1].min()),
                                       w=float(rotated[:, 0].max() - rotated[:, 0].min()),
                                       h=float(rotated[:, 1].max() - rotated[:, 1].min())),
                             points=[[float(x), float(y)] for x, y in rotated])
    product = sheet_frame([border], Frame(width=1000, height=700), 0)

    assert product.found is True
    assert product.angle_degrees == pytest.approx(7.0, abs=1.0), product.angle_degrees
    assert product.aligned is False
    assert ANGLE_SNAP_DEGREES == 2.0
    assert any("görsel kenarlardan değil" in note and "kullanıcı onayı" in note for note in product.notes), product.notes


@pytest.mark.parametrize("rotation,expected_x,expected_y", [
    (0, [1.0, 0.0], [0.0, -1.0]),
    (90, [0.0, 1.0], [1.0, 0.0]),
    (180, [-1.0, 0.0], [0.0, 1.0]),
    (270, [0.0, -1.0], [-1.0, 0.0]),
])
def test_rotation_axes_is_a_quarter_turn_table(rotation, expected_x, expected_y):
    axes = rotation_axes(rotation)

    assert [axis.name for axis in axes] == ["x", "y"]
    assert axes[0].page == expected_x and axes[1].page == expected_y
    assert all(axis.source == f"sayfa /Rotate={rotation}" for axis in axes)
    first, second = (np.array(axis.page) for axis in axes)
    assert np.linalg.norm(first) == pytest.approx(1.0) and np.linalg.norm(second) == pytest.approx(1.0)
    assert float(first @ second) == pytest.approx(0.0, abs=1e-12)
    assert rotation_axes(45) == []


def test_drawing_options_publishes_the_sheet_frame_from_the_loop_it_skips():
    """The menu already skips the sheet frame; now it also says what that frame is."""
    from drawingto3d.guided import drawing_options
    from drawingto3d.observe import Observations, SourceRef

    def line(pid, start, end):
        return Primitive(id=pid, path_id="synthetic", kind="line", start=list(start), end=list(end),
                         method="two-point")

    primitives = [
        line("g0", (10, 10), (990, 10)), line("g1", (990, 10), (990, 690)),
        line("g2", (990, 690), (10, 690)), line("g3", (10, 690), (10, 10)),
        line("g4", (100, 100), (300, 100)), line("g5", (300, 100), (300, 200)),
        line("g6", (300, 200), (100, 200)), line("g7", (100, 200), (100, 100)),
    ]
    observations = Observations(source=SourceRef(ref="synthetic.pdf", sha256="0" * 64, rotation=0),
                                frame=Frame(width=1000, height=700), text_placement="as-is",
                                primitives=primitives)
    options = drawing_options(observations)
    product = options["sheet_frame"]

    assert product is not None and product["found"] is True, product
    assert min(product["coverage"]) >= 0.8, product["coverage"]
    assert product["rotation"] == 0 and product["axes"][0]["page"] == [1.0, 0.0]
    assert any("izlemenin atladığı" in note for note in product["notes"]), product["notes"]
