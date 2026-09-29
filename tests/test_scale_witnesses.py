"""H-R17: yerleşmiş okumalar yetmediğinde ölçek aday çiftlerden kurulur — okuma başına bir oy.

Rasterda ölçülmüş durum: iki yerleşmiş okuma var (biri yanlış `9`, öteki `60`) ve pafta `contradictory`
diyordu; oysa aynı paftanın aday çiftleri 8.43 px/mm'de buluşuyordu. Bu testler kararın kendisini tutuyor:
tanıklar ölçeği kurabilmeli, tek okumanın üç çizgisi üç oy sayılmamalı, eşit güçlü iki küme ölçek olmamalı.
"""

from __future__ import annotations

from drawingto3d import scale
from drawingto3d.schema import BBox, Span


def _reading(span_id: str, value: float, length_px: float) -> Span:
    """Yerleşmiş bir okuma: değer + kendi ölçü çizgisinin piksel uzunluğu."""
    return Span(id=span_id, text=f"{value:g}", value=value, kind="linear", unit="mm",
                bbox=BBox(x=100.0, y=100.0, w=20.0, h=20.0),
                anchors=[[0.0, 0.0], [length_px, 0.0]], anchor_mode="dimension")


def test_witnesses_name_the_scale_when_the_placed_readings_fall_short():
    """İki yerleşmiş okuma (biri yanlış `9`) + tanıklar: ölçek kurulur ve yanlış okuma şüpheli olur."""
    spans = [_reading("nine", 9.0, 467.5), _reading("sixty", 60.0, 506.0)]
    witnesses = [("nine", 9.0, 467.5), ("fiftyfive", 55.0, 467.5), ("sixty", 60.0, 506.0),
                 ("eight", 8.0, 67.5)]

    report = scale.verdict(spans, witnesses=witnesses)

    assert report["state"] == "calibrated_with_suspects", report
    assert report["suspect"] == ["nine"], report
    assert abs(report["px_per_mm"] - 8.44) < 0.1, report
    assert report["witness_readings"] == 4


def test_a_witness_scale_needs_a_reading_the_gate_placed_to_confirm_it():
    """Tanık ölçeği, kapının kendi yerleştirdiği bir okumayla doğrulanmazsa paftanın ölçeği sayılmaz."""
    spans = [_reading("nine", 9.0, 467.5)]
    witnesses = [("a", 55.0, 467.5), ("b", 60.0, 506.0), ("c", 8.0, 67.5)]

    report = scale.verdict(spans, witnesses=witnesses)

    assert report["state"] == "uncalibrated", report
    assert report["suspect"] == []
    assert report["px_per_mm"] is None


def test_a_witness_scale_contradicted_by_most_placed_readings_is_not_adopted():
    """Örnek paftadaki durum: 12 yerleşmiş okumanın 2'si bir oranda buluşuyor — çoğunluk karşı çıkıyorsa ölçek değil."""
    spans = [_reading("good", 60.0, 506.0), _reading("two", 2.0, 132.0),
             _reading("long", 620.0, 147.0), _reading("panel", 260.0, 93.7)]
    witnesses = [("a", 55.0, 467.5), ("b", 60.0, 506.0), ("c", 8.0, 67.5)]

    report = scale.verdict(spans, witnesses=witnesses)

    # Ölçek kabul edilmedi: yerleşmiş okumaların çoğu tanık oranına karşı çıkıyor ve kendi aralarında da
    # anlaşan ikili yok (durum bu yüzden `contradictory`).
    assert report["px_per_mm"] is None, report
    assert report["suspect"] == [], report
    assert report["state"] in ("contradictory", "uncalibrated"), report


def test_one_reading_crossed_with_three_strokes_is_one_voice():
    """Tek okumanın yanındaki üç çizgi üç okuma değildir: ölçek kurulmaz (review6 W01)."""
    report = scale.verdict([], witnesses=[("one", 40.0, 400.0), ("one", 40.0, 401.0), ("one", 40.0, 399.0)])

    assert report["state"] == "uncalibrated", report
    assert report["px_per_mm"] is None


def test_two_equally_supported_clusters_leave_the_sheet_without_a_scale():
    """İki bağımsız küme aynı sayıda okumayı açıklıyorsa pafta hangisine çizildiğini söylemiyor."""
    witnesses = [("a", 10.0, 100.0), ("b", 20.0, 200.0), ("c", 30.0, 300.0),
                 ("d", 7.0, 140.0), ("e", 14.0, 280.0), ("f", 21.0, 420.0)]

    report = scale.verdict([], witnesses=witnesses)

    assert report["state"] == "uncalibrated", report
    assert report["px_per_mm"] is None
