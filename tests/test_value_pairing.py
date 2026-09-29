"""Kapının yakınlıkla bağlayamadığı sayı için üretilen **adaylar** — okuma değil, soru.

Review5 V01: değerden türeyen eşleşme, seçildiği ölçeğin kanıtı olamaz. Bu yüzden `_value_candidates`
hiçbir şey bağlamıyor: sayı kayda girmiyor, `anchor_mode` değişmiyor, `scale.verdict` onu bağımsız bir
gözlem sayamıyor. Elde kalan şey aday listesi + kararı veren mesafe; doğrulama kullanıcıya kalıyor.

Ölçülmüş gerekçe (`iterations/value-pairing-repro`, pilot-step-01): sabitlenmiş okumalar 7.875 px/mm
üzerinde buluşuyor; atılan beş sayıdan `28` ve `40` kendi değerleri kadar uzun bir çizginin yanında,
iki `6` çağrısı 150 px uzaktaki yanlış dostlarla, `3` ise hiçbir şeyle eşleşmiyor.
"""

from __future__ import annotations

from drawingto3d import scale
from drawingto3d.lines import Segment
from drawingto3d.perceive import _beside_distance, _value_candidates
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


# 7.875 px/mm, the scale pilot-step-01's anchored readings agree on.
ANCHORS = [_anchored("a", 60.0, 100.0, 100.0, 572.5, 100.0),
           _anchored("b", 20.0, 100.0, 200.0, 257.5, 200.0)]


def test_a_number_beside_the_only_stroke_of_its_own_length_is_proposed():
    """40 mm × 7.875 = 315 px; sayı o çizginin yanında ve başka aday yok."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0), _segment(500.0, 700.0, 900.0, 700.0)]

    rows = _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)

    assert len(rows) == 1 and rows[0]["id"] == "u" and rows[0]["expected_px"] == 315.0
    assert len(rows[0]["candidates"]) == 1
    candidate = rows[0]["candidates"][0]
    assert candidate["endpoints"] == [[400.0, 300.0], [400.0, 615.0]]
    assert candidate["orientation"] == "vertical" and candidate["resolved"] is True


def test_a_candidate_is_never_attached_to_the_span():
    """Aday üretmek okumak değildir: span'ın ankrajı boş kalır, kayıt üretilmez."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)

    assert span.anchors == [] and span.anchor_mode == "dimension"


def test_a_candidate_does_not_become_a_third_scale_observation():
    """Review5 V01'in çekirdeği: iki ankraj + bir aday hâlâ `uncalibrated` olmalı."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    assert [row["id"] for row in _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)] == ["u"]
    assert scale.verdict(ANCHORS)["state"] == "uncalibrated"


def test_two_equally_close_strokes_leave_the_number_unresolved():
    """İki paralel çizgi de yanındaysa pafta hangisini kastettiğini söylemiyor: `resolved` False."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0), _segment(404.0, 300.0, 404.0, 615.0)]

    rows = _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)

    assert len(rows[0]["candidates"]) == 2
    assert all(candidate["resolved"] is False for candidate in rows[0]["candidates"])


def test_the_nearest_of_two_parallel_strokes_is_the_resolved_one():
    """28 mm'lik sayı x=786 çizgisinin 8 px, x=825 çizgisinin 61 px yanında: yakın olan çözülür."""
    span = _span("u", 28.0, x=750.0, y=529.0)
    segments = [_segment(786.0, 427.0, 786.0, 642.0), _segment(825.0, 427.0, 825.0, 642.0)]

    rows = _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)

    candidates = rows[0]["candidates"]
    assert [candidate["resolved"] for candidate in candidates] == [True, False]
    assert candidates[0]["endpoints"][0][0] == 786.0


def test_a_stroke_of_the_wrong_length_is_not_a_candidate():
    """Uzunluk tutmuyorsa çizgi o sayının değildir: 6 mm (47 px) bir 45 px çizgiye aday olmaz."""
    span = _span("u", 6.0, x=316.0, y=1151.0)
    segments = [_segment(830.0, 424.0, 875.0, 424.0)]

    rows = _value_candidates([span], ANCHORS, segments, TEXT_HEIGHT)

    assert rows[0]["candidates"] == []


def test_a_body_edge_of_the_same_length_is_a_candidate_and_stays_one():
    """Aynı uzunlukta gövde kenarı da aday olur: fonksiyon yalnız uzunluk ve konuma bakar.

    Bu yüzden sonuç doğrulanmış ölçü değil, sorulacak adaydır; kapı bunu okuma saymaz.
    """
    span = _span("u", 40.0, x=340.0, y=290.0)
    body_edge = _segment(400.0, 300.0, 400.0, 615.0)

    rows = _value_candidates([span], ANCHORS, [body_edge], TEXT_HEIGHT)

    assert len(rows[0]["candidates"]) == 1


def test_without_a_scale_from_the_anchored_readings_nothing_is_proposed():
    """Ölçek yoksa değerin kaç piksel olduğu bilinmiyor: aday üretilmez, uydurulmaz."""
    span = _span("u", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    assert _value_candidates([span], [], segments, TEXT_HEIGHT) == []
    assert _value_candidates([span], ANCHORS, segments, None) == []


def test_a_number_far_across_from_a_stroke_is_not_beside_it():
    """150 px uzaktaki çizgi 'yanında' değildir: metin yüksekliğinin sekiz katı sınır."""
    span = _span("u", 6.0, x=670.0, y=304.0)
    stroke = _segment(830.0, 424.0, 875.0, 424.0)

    assert _beside_distance(span, stroke, TEXT_HEIGHT) is None
