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
from drawingto3d.perceive import _beside_distance, _promote_unplaced, _value_candidates
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

# `consensus` asks for three readings before it will name a scale, so the promotion tests carry a third:
# a scale named from two readings is a coincidence, not the sheet's scale.
PLACED3 = [*ANCHORS, _anchored("c", 30.0, 100.0, 300.0, 336.25, 300.0)]


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


# --- Okunan ama baglanamayan sayi: kayit mi, soru mu? (review5: once oku, sonra bagla) ---


def test_a_refused_reading_with_one_stroke_of_its_value_becomes_a_record():
    """Tek aday ve sayının yanındaysa okuma kayda girer — ankrajın kaynağı `value` olarak yazılır."""
    span = _span("p", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    kept, rows = _promote_unplaced([span], PLACED3, segments, TEXT_HEIGHT)

    assert rows == [] and kept == [span]
    assert span.anchors == [[400.0, 300.0], [400.0, 615.0]]
    assert span.anchor_mode == "dimension" and span.anchor_source == "value"


def test_a_promoted_reading_is_not_calibration_evidence():
    """V01: kendi değeriyle seçilmiş çizgi ölçeğin kanıtı olamaz — `measure` onu görmez."""
    span = _span("p", 40.0, x=340.0, y=290.0)
    kept, _rows = _promote_unplaced([span], PLACED3, [_segment(400.0, 300.0, 400.0, 615.0)], TEXT_HEIGHT)

    assert kept == [span], "tek adaylı okuma kayda girmeliydi"
    assert scale.measure(kept) == []
    assert scale.measure_spans(kept) == []


def test_two_equally_close_strokes_leave_the_reading_a_question():
    """Yanında iki eşit yakın çizgi varsa pafta hangisini kastettiğini söylemiyor: kayıt yok."""
    span = _span("p", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0), _segment(404.0, 300.0, 404.0, 615.0)]

    kept, rows = _promote_unplaced([span], PLACED3, segments, TEXT_HEIGHT)

    assert kept == [] and len(rows) == 1
    assert rows[0]["reason"] == "no_single_stroke" and rows[0]["candidates"] == 2


def test_a_reading_with_no_stroke_of_its_length_stays_a_question():
    """Yanlış okumanın (`29`, pafta `25` basıyor) oturacağı çizgi yok: soru olarak geri döner."""
    span = _span("p", 29.0, x=670.0, y=517.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    kept, rows = _promote_unplaced([span], PLACED3, segments, TEXT_HEIGHT)

    assert kept == [] and rows[0]["reason"] == "no_stroke_of_its_length"


def test_without_a_scale_from_the_placed_readings_nothing_is_promoted():
    """Yerleştirilmiş okumalar bir ölçekte buluşmuyorsa değerin kaç piksel olduğu bilinmiyor."""
    span = _span("p", 40.0, x=340.0, y=290.0)

    kept, rows = _promote_unplaced([span], [], [_segment(400.0, 300.0, 400.0, 615.0)], TEXT_HEIGHT)

    assert kept == [] and rows[0]["reason"] == "no_scale_from_placed_readings"


def test_the_same_reading_seen_by_two_passes_is_promoted_once():
    """İki kümeleme geçişi aynı sayıyı iki kez okur; kayıt bir tane olmalı."""
    span = _span("p", 40.0, x=340.0, y=290.0)
    twin = _span("p2", 40.0, x=340.0, y=290.0)
    segments = [_segment(400.0, 300.0, 400.0, 615.0)]

    kept, rows = _promote_unplaced([span, twin], PLACED3, segments, TEXT_HEIGHT)

    assert len(kept) == 1 and rows == []


# --- Olcek, kapinin adlandiramadigi yerde aday ciftlerin cogunlugundan (H-R11) ---


def _three_agreeing_readings() -> tuple[list, list]:
    """Uc okuma, her birinin yaninda kendi degerinin 8 px/mm karsiligi kadar uzun bir cizgi."""
    readings = [_span("p1", 50.0, x=100.0, y=100.0), _span("p2", 30.0, x=100.0, y=200.0),
                _span("p3", 20.0, x=100.0, y=300.0)]
    strokes = [_segment(140.0, 90.0, 140.0, 490.0),   # 400 px / 50 mm = 8.0
               _segment(140.0, 190.0, 140.0, 430.0),  # 240 px / 30 mm = 8.0
               _segment(140.0, 290.0, 140.0, 450.0)]  # 160 px / 20 mm = 8.0
    return readings, strokes


def test_the_scale_is_bootstrapped_when_the_gate_placed_too_few_readings():
    """Kapi iki okuma tuttuysa olcek yoktu ve bu okumalar soru olarak kaliyordu; cogunluk olcegi adlandirir."""
    readings, strokes = _three_agreeing_readings()

    kept, rows = _promote_unplaced(readings, [], strokes, TEXT_HEIGHT)

    assert rows == []
    assert sorted(span.text for span in kept) == ["20", "30", "50"]
    assert all(span.anchor_source == "value" for span in kept)
    assert scale.measure(kept) == [], "terfi eden okumalar olcegin kaniti olamaz"


def test_two_agreeing_pairs_are_not_a_scale():
    """Iki cift tesaduf olabilir: destek ucun altindaysa hicbir okuma terfi etmez."""
    readings, strokes = _three_agreeing_readings()

    kept, rows = _promote_unplaced(readings[:2], [], strokes[:2], TEXT_HEIGHT)

    assert kept == [] and len(rows) == 2
    assert {row["reason"] for row in rows} == {"no_scale_from_placed_readings"}


def test_the_readings_the_gate_placed_count_as_witnesses_for_the_bootstrap():
    """Olculdu: kapi iki okuma yerleştirdi ve olcegi adlandiran uc ciftin biri onun kendi cizgisiydi.

    Kapi cizgiyi sayiya bakmadan (yakinlikla) secer, bu yuzden orani bagimsiz bir taniktir; yalniz
    `pending` okumalara bakmak cogunlugu bulamaz ve terfi hic olmaz.
    """
    placed = [_anchored("a", 50.0, 100.0, 100.0, 500.0, 100.0),   # 400 px / 50 mm = 8.0
              _anchored("b", 30.0, 100.0, 200.0, 340.0, 200.0)]   # 240 px / 30 mm = 8.0
    pending = _span("p", 20.0, x=100.0, y=300.0)
    strokes = [_segment(140.0, 290.0, 140.0, 450.0)]              # 160 px / 20 mm = 8.0

    assert scale.consensus(scale.measure(placed))[0] is None, "iki okuma tek basina olcek degil"
    kept, rows = _promote_unplaced([pending], placed, strokes, TEXT_HEIGHT)

    assert rows == [] and kept == [pending]
    assert pending.anchors == [[140.0, 290.0], [140.0, 450.0]]
    assert pending.anchor_source == "value"


def test_a_stroke_that_is_not_beside_the_number_supports_nothing():
    """1500 px otedeki uzun cizgi ne olcek kurar ne okuma yerlesir."""
    readings, strokes = _three_agreeing_readings()
    far = [_segment(1500.0, 90.0, 1500.0, 490.0), _segment(1500.0, 190.0, 1500.0, 430.0),
           _segment(1500.0, 290.0, 1500.0, 450.0)]

    kept, rows = _promote_unplaced(readings, [], far, TEXT_HEIGHT)

    assert kept == [] and len(rows) == 3
    assert {row["reason"] for row in rows} == {"no_scale_from_placed_readings"}
