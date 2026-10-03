"""SEMREAD-001A sözleşmesi: hazırlanan görselin izi, bbox kuralı ve yanıt şeması.

Burada ölçülen şey "model ne dedi" değil, **girdi ve yanıt sözleşmesi**: hash/boyut gönderilecek son
byte'lardan mı hesaplanıyor, beyan ölçümü ezebiliyor mu, aralık dışı bbox kırpılıyor mu (hayır),
gönderilmemiş kimlik ve tanımsız alan kabul ediliyor mu (hayır).
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

from drawingto3d.semantic_schema import (  # noqa: E402
    SHAPE_CLASSES,
    ImageBundle,
    ManifestMismatch,
    ProbeReferenceError,
    ProbeSchemaError,
    ProbeParseError,
    PreparedImage,
    Region,
    SemanticInputError,
    check_references,
    parse_probe_json,
    probe_json_schema,
    validate_probe_response,
)


def png(width: int = 8, height: int = 6, colour: int = 255) -> bytes:
    image = np.full((height, width, 3), colour, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def image(image_id: str = "image-1", *, kind: str = "full_page", data: bytes | None = None,
          **kwargs) -> PreparedImage:
    payload = data if data is not None else png()
    base = dict(image_id=image_id, kind=kind, png=payload, source_sha256="a" * 64,
                render_mode="pdf_rerender", render_dpi=200.0)
    base.update(kwargs)
    if kind == "crop":
        base.setdefault("source_bbox_page_norm", (0.25, 0.25, 0.75, 0.75))
    if kind == "overlay":
        base.setdefault("observation_snapshot_id", "snap-1")
    return PreparedImage(**base)


def good_payload(**item_overrides) -> dict:
    item = {"image_id": "image-1", "description": "kısa gözlem", "shape": "square",
            "region": {"x0": 0.1, "y0": 0.2, "x1": 0.5, "y1": 0.6}}
    item.update(item_overrides)
    return {"schema_version": "semread-probe/2", "items": [item]}


# -- kaynak izi ve hash ----------------------------------------------------


def test_hash_and_size_come_from_the_final_bytes_not_from_the_caller():
    data = png(12, 7)
    prepared = image(data=data)
    assert prepared.sha256 == hashlib.sha256(data).hexdigest()
    assert (prepared.width_px, prepared.height_px) == (12, 7)


def test_a_declared_hash_that_contradicts_the_bytes_is_an_error():
    with pytest.raises(ManifestMismatch):
        image(data=png(), sha256="b" * 64)


def test_a_declared_size_that_contradicts_the_bytes_is_an_error():
    prepared = image()
    with pytest.raises(ManifestMismatch):
        prepared.verify_declared(width_px=99)
    prepared.verify_declared(width_px=8, height_px=6, sha256=prepared.sha256)


def test_the_identity_has_to_be_neutral():
    """"image-1" kabul, kaynak hash'i ya da dosya adı kimlik olarak kabul değil."""
    with pytest.raises(SemanticInputError):
        image("a3f9c1.png")
    with pytest.raises(SemanticInputError):
        image("image-0")


def test_render_provenance_is_not_self_contradicting():
    with pytest.raises(SemanticInputError):
        image(kind="crop", render_mode="native_raster", render_dpi=200.0)
    with pytest.raises(SemanticInputError):
        image(kind="crop", render_mode="pdf_rerender", render_dpi=None)
    with pytest.raises(SemanticInputError):
        image(kind="full_page", source_bbox_page_norm=(0.1, 0.1, 0.2, 0.2))
    with pytest.raises(SemanticInputError):
        image(kind="crop", source_bbox_page_norm=None)
    with pytest.raises(SemanticInputError):
        image(kind="overlay", observation_snapshot_id=None)


def test_a_page_index_other_than_zero_is_refused_here_too():
    with pytest.raises(SemanticInputError):
        image(page_index=1)


# -- dönüşüm ---------------------------------------------------------------


def test_a_crop_maps_corners_and_centre_onto_the_source_page():
    prepared = image(kind="crop", source_bbox_page_norm=(0.2, 0.3, 0.6, 0.7))
    assert prepared.t_image_norm_to_page_norm == [[0.4, 0.0, 0.2], [0.0, 0.4, 0.3]]
    assert prepared.map_point_to_page(0.0, 0.0) == pytest.approx((0.2, 0.3))
    assert prepared.map_point_to_page(1.0, 1.0) == pytest.approx((0.6, 0.7))
    assert prepared.map_point_to_page(0.5, 0.5) == pytest.approx((0.4, 0.5))


def test_a_full_page_and_an_overlay_map_identity():
    for kind in ("full_page", "overlay"):
        prepared = image(kind=kind)
        assert prepared.t_image_norm_to_page_norm == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        assert prepared.map_point_to_page(0.25, 0.75) == pytest.approx((0.25, 0.75))


def test_region_in_a_crop_frame_is_resolved_to_the_page_frame():
    prepared = image(kind="crop", source_bbox_page_norm=(0.1, 0.2, 0.5, 0.6))
    region = Region(x0=0.0, y0=0.5, x1=0.5, y1=1.0)
    assert prepared.map_region_to_page(region) == pytest.approx([0.1, 0.4, 0.3, 0.6])


# -- bbox kuralı -----------------------------------------------------------


@pytest.mark.parametrize("box", [
    {"x0": -0.01, "y0": 0.0, "x1": 0.5, "y1": 0.5},
    {"x0": 0.0, "y0": 0.0, "x1": 1.01, "y1": 0.5},
    {"x0": 0.5, "y0": 0.0, "x1": 0.5, "y1": 0.5},
    {"x0": 0.6, "y0": 0.0, "x1": 0.4, "y1": 0.5},
    {"x0": float("nan"), "y0": 0.0, "x1": 0.5, "y1": 0.5},
    {"x0": 0.0, "y0": float("inf"), "x1": 0.5, "y1": 0.5},
])
def test_a_bad_bbox_is_refused_and_not_clamped(box):
    with pytest.raises((ProbeSchemaError, ValueError)):
        validate_probe_response(good_payload(region=box))


def test_a_null_region_is_an_allowed_abstention():
    response = validate_probe_response(good_payload(region=None))
    assert response.items[0].region is None


# -- yanıt şeması ----------------------------------------------------------


def test_the_schema_carries_no_acceptance_field_and_rejects_one():
    """`supported`/`source=user` sözleşmede yok; gelirse yanıt şema hatasıdır."""
    text = str(probe_json_schema())
    assert "supported" not in text and "source" not in text
    with pytest.raises(ProbeSchemaError):
        validate_probe_response(good_payload(supported=True))
    with pytest.raises(ProbeSchemaError):
        validate_probe_response({"schema_version": "semread-probe/1", "items": [],
                                 "source": "user"})


def test_an_unknown_schema_version_is_refused():
    """Şema sürümü sözleşmenin parçası: eski sürüm ("/1") ve uydurma sürüm kabul edilmez."""
    with pytest.raises(ProbeSchemaError):
        validate_probe_response({"schema_version": "semread-probe/1", "items": []})
    with pytest.raises(ProbeSchemaError):
        validate_probe_response({"schema_version": "semread-probe/3", "items": []})


def test_the_shape_field_is_a_small_versioned_class_list_with_the_same_options_for_every_image():
    """Sınıf alanı kimlik→sınıf eşlemesi taşımaz: seçenekler her görsel için aynıdır."""
    schema = probe_json_schema()
    shapes = schema["properties"]["items"]["items"]["properties"]["shape"]
    assert shapes == {"type": "string", "enum": list(SHAPE_CLASSES)}
    text = str(schema)
    assert "image-" not in text, "şema bir kimlik adı taşımamalı"
    assert schema["properties"]["items"]["items"]["required"] == ["image_id", "description", "shape",
                                                                 "region"]


def test_a_shape_class_outside_the_contract_is_a_schema_error():
    with pytest.raises(ProbeSchemaError):
        validate_probe_response(good_payload(shape="beşgen"))
    with pytest.raises(ProbeSchemaError):
        validate_probe_response(good_payload(shape="Triangle"))
    # `unknown` geçerli bir beyandır: şema onu kabul eder, görsel kontrolü onu reddeder.
    assert validate_probe_response(good_payload(shape="unknown")).items[0].shape == "unknown"


def test_a_missing_shape_is_a_schema_error_not_an_empty_answer():
    payload = good_payload()
    payload["items"][0].pop("shape")
    with pytest.raises(ProbeSchemaError):
        validate_probe_response(payload)


def test_a_broken_body_is_not_repaired():
    with pytest.raises(ProbeParseError):
        parse_probe_json("")
    with pytest.raises(ProbeParseError):
        parse_probe_json('{"schema_version": "semread-probe/1", "items": [}')
    with pytest.raises(ProbeParseError):
        parse_probe_json("[1, 2, 3]")


# -- referans --------------------------------------------------------------


def test_a_response_may_only_reference_images_this_call_sent():
    response = validate_probe_response(good_payload(image_id="image-9"))
    with pytest.raises(ProbeReferenceError):
        check_references(response, ["image-1", "image-2"])


def test_a_stale_snapshot_identity_is_refused_the_same_way():
    response = validate_probe_response(good_payload(image_id="image-1"))
    assert check_references(response, ["image-1"])["ok"] is True
    with pytest.raises(ProbeReferenceError):
        check_references(response, ["image-2"])


def test_a_duplicate_identity_in_a_response_is_a_reference_error():
    """Her gönderilen görsele **tam bir** yanıt: aynı kimliği iki kez yazmak kapsamı bozar."""
    payload = {"schema_version": "semread-probe/2",
               "items": [good_payload()["items"][0], good_payload()["items"][0]]}
    with pytest.raises(ProbeReferenceError):
        check_references(validate_probe_response(payload), ["image-1"])


def test_a_missing_identity_in_a_response_is_a_reference_error():
    """Gönderilen iki görselden birine yanıt yoksa kapsam tam değildir; kabul edilmez."""
    response = validate_probe_response(good_payload(image_id="image-1"))
    with pytest.raises(ProbeReferenceError):
        check_references(response, ["image-1", "image-2"])


def test_an_empty_answer_for_sent_images_is_a_reference_error():
    response = validate_probe_response({"schema_version": "semread-probe/2", "items": []})
    with pytest.raises(ProbeReferenceError):
        check_references(response, ["image-1"])
    # Hiç görsel gönderilmediyse boş yanıt doğrudur.
    assert check_references(response, [])["coverage"]["exact"] is True


def test_a_response_that_invents_items_without_any_sent_image_is_a_reference_error():
    response = validate_probe_response(good_payload(image_id="image-1"))
    with pytest.raises(ProbeReferenceError):
        check_references(response, [])


def test_exact_coverage_is_recorded_as_a_verdict_not_only_as_a_pass():
    response = validate_probe_response({"schema_version": "semread-probe/2", "items": [
        {"image_id": "image-2", "description": "kare", "shape": "square", "region": None},
        {"image_id": "image-1", "description": "üçgen", "shape": "triangle", "region": None},
    ]})
    report = check_references(response, ["image-1", "image-2"])
    assert report["coverage"] == {"sent": ["image-1", "image-2"],
                                  "answered": ["image-2", "image-1"],
                                  "missing": [], "duplicates": [], "unknown": [], "exact": True}
    assert [row["shape"] for row in report["checks"]] == ["square", "triangle"]


# -- paket ---------------------------------------------------------------


def test_a_bundle_refuses_duplicate_identities_and_an_inconsistent_order():
    with pytest.raises(SemanticInputError):
        ImageBundle([image("image-1"), image("image-1")])
    with pytest.raises(SemanticInputError):
        ImageBundle([image("image-1")], order=["image-2"])


def test_reversing_the_payload_order_keeps_each_identity_with_its_own_image():
    first = image("image-1", data=png(colour=10))
    second = image("image-2", data=png(colour=200))
    forward = ImageBundle([first, second])
    backward = ImageBundle([first, second], order=["image-2", "image-1"])

    assert forward.image_ids == ["image-1", "image-2"]
    assert backward.image_ids == ["image-2", "image-1"]
    assert forward.by_id("image-1").sha256 == backward.by_id("image-1").sha256
    assert [entry["image_id"] for entry in backward.manifest()["images"]] == ["image-2", "image-1"]


def test_the_manifest_records_order_hashes_and_the_transform():
    bundle = ImageBundle([image("image-1", kind="crop", source_bbox_page_norm=(0.1, 0.1, 0.3, 0.3)),
                          image("image-2")])
    manifest = bundle.manifest(source={"sha256": "f" * 64, "page_index": 0})
    assert manifest["schema"] == "semread-input-manifest/1"
    assert manifest["image_order"] == ["image-1", "image-2"]
    crop = manifest["images"][0]
    assert crop["t_image_norm_to_page_norm"] == [[0.2, 0.0, 0.1], [0.0, 0.2, 0.1]]
    assert crop["prepared_image_sha256"] == bundle.by_id("image-1").sha256
    assert manifest["images"][1]["source_bbox_page_norm"] is None
