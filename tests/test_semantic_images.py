"""Görsel hazırlama: PDF crop yeniden render, raster crop native, dönüşüm ve reddetme.

Ölçülen ayrım şu: kaynaktan **yeniden çizilen** bölge ile kaynağın **kendi piksellerinden** alınan
bölge aynı şey değildir. İlki yeni ayrıntı kazanır (600 dpi), ikincisi kazanmaz (`render_dpi=null`).
Desteklenmeyen sayfa/rotasyon ise sessizce ilk sayfaya düşmez, açıkça reddedilir.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.semantic_images import (  # noqa: E402
    CROP_DPI,
    RAW_PAGE_DPI,
    declared_conflict,
    observation_snapshot_id,
    open_source,
    overlay_from_observations,
    prepare_crop,
    prepare_full_page,
    resize_png,
)
from drawingto3d.semantic_schema import ManifestMismatch, SemanticInputError, UnsupportedSource  # noqa: E402

PLATE_PDF = ROOT / "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF"
RASTER = ROOT / "examples/flange-elbow-90.png"


@pytest.fixture(scope="module")
def plate():
    return open_source(PLATE_PDF)


@pytest.fixture(scope="module")
def raster():
    return open_source(RASTER)


# -- kaynak sınırı ---------------------------------------------------------


def test_the_raw_page_is_rendered_at_the_observation_frame_resolution(plate):
    assert plate.source_type == "pdf"
    assert plate.render_dpi == RAW_PAGE_DPI
    assert plate.frame_width_px == round(plate.width_pt * RAW_PAGE_DPI / 72.0)
    assert plate.sha256 == hashlib.sha256(PLATE_PDF.read_bytes()).hexdigest()


def test_a_page_other_than_the_first_is_refused_not_silently_substituted():
    with pytest.raises(UnsupportedSource):
        open_source(PLATE_PDF, page_index=1)


def test_a_rotated_page_is_refused(monkeypatch):
    import pypdfium2 as pdfium

    monkeypatch.setattr(pdfium.PdfPage, "get_rotation", lambda self: 90)
    with pytest.raises(UnsupportedSource):
        open_source(PLATE_PDF)


def test_an_unsupported_file_type_is_refused(tmp_path):
    other = tmp_path / "not-a-drawing.txt"
    other.write_text("merhaba")
    with pytest.raises(UnsupportedSource):
        open_source(other)


def test_a_raster_source_has_no_render_dpi_and_keeps_the_decoded_pixels(raster):
    assert raster.source_type == "raster" and raster.render_dpi is None
    decoded = cv2.imread(str(RASTER), cv2.IMREAD_COLOR)
    assert (raster.frame_width_px, raster.frame_height_px) == (decoded.shape[1], decoded.shape[0])
    with pytest.raises(UnsupportedSource):
        open_source(RASTER, page_index=1)


# -- PDF crop: kaynaktan yeniden render -----------------------------------


def test_a_pdf_crop_is_re_rendered_from_the_source(plate):
    crop = prepare_crop(plate, "image-3", [0.25, 0.25, 0.6, 0.6])
    assert crop.render_mode == "pdf_rerender" and crop.render_dpi == CROP_DPI
    assert crop.kind == "crop" and crop.source_bbox_page_norm == (0.25, 0.25, 0.6, 0.6)
    # Bölgenin kendi çözünürlüğü 600 dpi'dır; ham sayfadan (200 dpi) dört kat daha geniş.
    assert crop.width_px == pytest.approx((0.6 - 0.25) * plate.width_pt * CROP_DPI / 72.0, rel=0.01)
    assert crop.height_px == pytest.approx((0.6 - 0.25) * plate.height_pt * CROP_DPI / 72.0, rel=0.01)


def test_the_same_source_region_is_kept_across_two_render_resolutions(plate):
    coarse = prepare_crop(plate, "image-3", [0.2, 0.3, 0.5, 0.65], dpi=300)
    fine = prepare_crop(plate, "image-3", [0.2, 0.3, 0.5, 0.65], dpi=600)
    assert coarse.source_bbox_page_norm == fine.source_bbox_page_norm
    assert fine.width_px / coarse.width_px == pytest.approx(2.0, rel=0.01)
    assert fine.height_px / coarse.height_px == pytest.approx(2.0, rel=0.01)
    # Aynı bölge: iki çözünürlükte de merkez aynı sayfa koordinatına çözülür.
    centre = [0.5, 0.5]
    assert coarse.map_point_to_page(*centre) == fine.map_point_to_page(*centre)


def test_the_crop_frame_maps_onto_the_page_corners(plate):
    crop = prepare_crop(plate, "image-3", [0.1, 0.2, 0.9, 0.8])
    assert crop.map_point_to_page(0.0, 0.0) == pytest.approx((0.1, 0.2))
    assert crop.map_point_to_page(1.0, 1.0) == pytest.approx((0.9, 0.8))
    assert crop.map_point_to_page(0.5, 0.25) == pytest.approx((0.5, 0.35))


def test_a_crop_of_the_whole_page_is_not_a_silent_fallback(plate):
    with pytest.raises(SemanticInputError):
        prepare_crop(plate, "image-3", [float("nan"), 0.0, 1.0, 1.0])


# -- raster crop: native piksel -------------------------------------------


def test_a_raster_crop_comes_from_the_native_pixels_and_gains_nothing(raster):
    crop = prepare_crop(raster, "image-2", [0.1, 0.2, 0.9, 0.8])
    assert crop.render_mode == "native_raster" and crop.render_dpi is None
    source = cv2.imdecode(np.frombuffer(raster.frame_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    left, top = int(np.floor(0.1 * raster.frame_width_px)), int(np.floor(0.2 * raster.frame_height_px))
    right = int(np.ceil(0.9 * raster.frame_width_px))
    bottom = int(np.ceil(0.8 * raster.frame_height_px))
    assert (crop.width_px, crop.height_px) == (right - left, bottom - top)
    expected = source[top:bottom, left:right]
    decoded = cv2.imdecode(np.frombuffer(crop.png, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded.shape[:2] == expected.shape[:2]
    assert np.array_equal(decoded, expected), "native crop kaynağın pikselleri olmalı, yeniden çizim değil"
    # Crop'un kendi çerçevesi kaynak sayfanın o bölgesine çözülür.
    assert crop.map_point_to_page(0.0, 0.0) == pytest.approx((0.1, 0.2))
    assert crop.map_point_to_page(1.0, 1.0) == pytest.approx((0.9, 0.8))


def test_a_raster_full_page_is_declared_as_native(raster):
    full = prepare_full_page(raster, "image-1")
    assert full.render_mode == "native_raster" and full.render_dpi is None
    assert (full.width_px, full.height_px) == (raster.frame_width_px, raster.frame_height_px)


# -- hash, boyut, resize ---------------------------------------------------


def test_the_hash_is_measured_on_the_bytes_that_would_be_sent(plate):
    full = prepare_full_page(plate, "image-1")
    assert full.sha256 == hashlib.sha256(full.png).hexdigest()
    assert full.as_spec()["prepared_image_sha256"] == full.sha256
    assert full.as_spec()["prepared_image_bytes"] == len(full.png)


def test_a_resize_changes_the_hash_and_is_recorded_as_applied(plate):
    full = prepare_full_page(plate, "image-1")
    small = prepare_full_page(plate, "image-1", resize_max_side=600)
    assert small.sha256 != full.sha256
    assert small.resize_policy["applied"] is True
    assert small.resize_policy["from_px"] == [full.width_px, full.height_px]
    assert max(small.resize_policy["to_px"]) == 600
    assert (small.width_px, small.height_px) == tuple(small.resize_policy["to_px"])


def test_an_upscale_is_never_applied_and_the_policy_says_so(plate):
    full = prepare_full_page(plate, "image-1")
    same, policy = resize_png(full.png, 100000)
    assert policy["applied"] is False and same == full.png
    assert policy["to_px"] == [full.width_px, full.height_px]


def test_a_conflicting_caller_declaration_is_refused(plate):
    full = prepare_full_page(plate, "image-1")
    declared_conflict(full, {"sha256": full.sha256, "width_px": full.width_px})
    with pytest.raises(ManifestMismatch):
        declared_conflict(full, {"sha256": full.sha256, "width_px": full.width_px + 1})


# -- overlay ---------------------------------------------------------------


def test_the_overlay_is_a_separate_image_that_addresses_real_observation_ids(plate):
    from drawingto3d.observe import observe

    observations = observe(PLATE_PDF)
    overlay = overlay_from_observations(observations, "image-2", source=plate)
    frame = prepare_full_page(plate, "image-1")

    assert overlay.kind == "overlay" and overlay.png != frame.png
    assert (overlay.width_px, overlay.height_px) == (frame.width_px, frame.height_px)
    assert overlay.observation_snapshot_id == observation_snapshot_id(observations)
    assert observations.paths and overlay.observation_snapshot_id


def test_an_overlay_without_a_snapshot_is_refused(plate):
    with pytest.raises(SemanticInputError):
        from drawingto3d.semantic_schema import PreparedImage

        PreparedImage(image_id="image-2", kind="overlay", png=b"x", source_sha256="a" * 64,
                      render_mode="pdf_rerender", render_dpi=200.0)
