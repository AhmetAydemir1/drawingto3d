"""Kapının yakınlıkla bağlayamadığı sayıyı paftanın kendi ölçeğiyle eşleştirme.

Ölçülmüş gerekçe (pilot-step-01, `iterations/value-pairing-repro`): sabitlenmiş üç okuma 7.875 px/mm
üzerinde buluşuyor; atılan sayılardan `28` ve `40` kendi değerleri kadar uzun tek bir çizginin yanında
duruyor, iki `6` çağrısının uzunluk eşleşmeleri 150 px uzakta, `3` mm'lik çizgi inceltmeden geçmiyor.
Bu dosya kuralı sabitler: tek anlamlıysa bağla, iki aday varsa bağlama, ölçek yoksa hiç deneme.
"""

from __future__ import annotations

from drawingto3d.lines import Segment
from drawingto3d.perceive import _beside_distance, _pair_by_value
from drawingto3d.schema import BBox, Span

TEXT_HEIGHT = 21.0


def _span(span_id: str, value: float, x: float, y: float, w: float = 30.0, h: float = 20.0) -> Span:
    return Span(id=span_id, text=f"{value:g}", value=value, kind="linear", unit="mm",
                bbox=BBox(x=x, y=y, w=w, h=h), anchors=[], anchor_mode="dimension", source="pdf_text")


def _anchored(span_id: str, value: float, x0: float, y0: float, x1: float, y1: float) -> Span:
    span = _span(span_id, value, min(x0, x1), min(y0, y1))
    span.anchors = [[x0, y0], [x1, y1]]
    span.anchor_mode = "dimension"
    return span


def _segment(x0: float, y0: float, x1: float, y1: float) -> Segment:
    horizontal = abs(y1 - y0) <= abs(x1 - x0)
    return Segment(x0=x0, y0=y0, x1=x1, y1=y1, thickness=2.0, horizontal=horizontal)


# 7.875 px/mm, the scale the anchored readings of pilot-step-01 agree on.
ANCHORS = [_anchored("a", 60.0, 100.0, 100.0, 572.5, 100.0),
           _anchored("b", 20.0, 100.0, 200.0, 257.5, 200.0)]


def test_a_number_beside_the_only_stroke_of_its_own_length_is_paired():
    """40 mm × 7.875 = 315 px; sayı o çizginin yanında ve başka aday yok."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0), _segment(500.0, 700.0, 900.0, 700.0)]

    attached = _pair_by_value([span], ANCHORS, segments, TEXT_HEIGHT)

    assert len(attached) == 1 and attached[0][1] == [[400.0, 300.0], [400.0, 615.0]]


def test_two_equally_close_strokes_leave_the_number_unpaired():
    """İki paralel çizgi de sayının yanındaysa pafta hangisini kastettiğini söylemiyor: bağlama."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0), _segment(404.0, 300.0, 404.0, 615.0)]

    assert _pair_by_value([span], ANCHORS, segments, TEXT_HEIGHT) == []


def test_the_nearest_of_two_parallel_strokes_wins_when_the_other_is_far():
    """28 mm'lik sayı x=786 çizgisinin 8 px, x=825 çizgisinin 61 px yanında: yakın olan onun."""
    span = _span("u", 28.0, x=750.0, y=529.0)
    segments = [_segment(786.0, 427.0, 786.0, 642.0), _segment(825.0, 427.0, 825.0, 642.0)]

    attached = _pair_by_value([span], ANCHORS, segments, TEXT_HEIGHT)

    assert len(attached) == 1 and attached[0][1][0][0] == 786.0


def test_a_stroke_of_the_wrong_length_is_not_the_numbers_line():
    """Uzunluk tutmuyorsa çizgi o sayının değildir: 6 mm (47 px) bir 45 px çizgiye bağlanmaz."""
    span = _span("u", 6.0, x=316.0, y=1151.0)
    segments = [_segment(830.0, 424.0, 875.0, 424.0)]

    assert _pair_by_value([span], ANCHORS, segments, TEXT_HEIGHT) == []


def test_without_a_scale_from_the_anchored_readings_nothing_is_paired():
    """Ölçek yoksa değerin kaç piksel olduğu bilinmiyor: sayı bağlanmaz, uydurulmaz."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    assert _pair_by_value([span], [], segments, TEXT_HEIGHT) == []


def test_a_number_far_across_from_a_stroke_is_not_beside_it():
    """150 px uzaktaki çizgi 'yanında' değildir: metin yüksekliğinin sekiz katı sınır."""
    span = _span("u", 6.0, x=670.0, y=304.0)
    stroke = _segment(830.0, 424.0, 875.0, 424.0)

    assert _beside_distance(span, stroke, TEXT_HEIGHT) is None
