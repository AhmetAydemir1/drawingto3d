"""Paftanın kendi ölçeği: sayılar paftanın geometrisiyle doğrulandı mı, doğrulanamadı mı, çelişiyor mu.

Review4 iki okuma hatasını kanıtladı ve ikisi de "sayı okundu" ile "sayı doğru" arasındaki farkı
kapatmıyordu:

* görünüş etiketi (`FRONT`) bir lidere takılıp whitelist'li son turda `2` diye okundu — bir kelime
  sayı değildir;
* paftanın kendi ölçeği (her ölçü çizgisi üzerindeki sayıya göre çizilmiştir) hesaba katılmadı:
  dört okumanın üçü yanlıştı, ölçek denetimi bir çoğunluk bulamadı ve sessizce devam edildi.
  Ölçülmüş hâli: aynı paftada 13.5, 51.9 ve 8.4 px/mm — üç ayrı ölçek, yani en az biri yanlış.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from drawingto3d import perceive as perceive_module
from drawingto3d import reason as reason_module
from drawingto3d import scale
from drawingto3d.cadrun import CadFailure
from drawingto3d.reason import _sheet_needs_review, _unreviewed, reason_drawing
from drawingto3d.schema import BBox, DimensionRecord, Source, Span

DRAWING = Path("examples/flange-elbow-90.png")


def _span(span_id: str, value: float, length_px: float, *, mode: str = "dimension") -> Span:
    return Span(id=span_id, text=f"{value:g}", value=value, kind="linear", unit="mm",
                bbox=BBox(x=0, y=0, w=10, h=10),
                anchors=[[0.0, 0.0], [length_px, 0.0]], anchor_mode=mode, source="ocr")


def test_a_sheet_whose_numbers_contradict_itself_is_named_as_such():
    """Üç okuma, üç ayrı ölçek: bu "ölçek yok" değil, "sayılar birbirini yalanyor"dur."""
    spans = [_span("ocr-0", 4.0, 54.0), _span("ocr-1", 9.0, 467.5), _span("ocr-2", 60.0, 506.0)]

    report = scale.verdict(spans)

    assert report["state"] == "contradictory"
    assert report["px_per_mm"] is None and report["inliers"] == []
    assert report["ratios"] == [13.5, 51.9444, 8.4333]
    assert "yalanlıyor" in report["note"]


def test_too_few_readings_is_uncalibrated_and_not_a_contradiction():
    """İki okuma ölçek kurmaya yetmez ama aynı ölçeği tutuyorsa hiçbir şey çelişmez."""
    report = scale.verdict([_span("ocr-0", 60.0, 506.0), _span("ocr-1", 40.0, 337.0)])

    assert report["state"] == "uncalibrated"
    assert report["usable_readings"] == 2 and report["px_per_mm"] is None
    assert report["note"].startswith("ölçülecek okuma sayısı 2: en az ikisi aynı ölçeği tutuyor")


def test_two_readings_that_deny_each_other_are_a_contradiction_not_a_gap():
    """Üç okuma olmadan çoğunluk kurulamaz; ama iki okuma altı kat ayrı ölçek veriyorsa çelişki vardır."""
    report = scale.verdict([_span("ocr-1", 9.0, 467.5), _span("ocr-2", 60.0, 506.0)])

    assert report["state"] == "contradictory"
    assert report["ratios"] == [51.9444, 8.4333]
    assert "yalanlıyor" in report["note"]


def test_readings_that_agree_calibrate_the_sheet_and_the_odd_one_is_named():
    """Bir okuma uymuyorsa ölçek kurulur ve uymayan okuma `suspect` olarak adlandırılır."""
    spans = [_span(f"ocr-{index}", 60.0, 506.0) for index in range(3)]
    spans.append(_span("ocr-3", 3.0, 506.0))

    report = scale.verdict(spans)

    assert report["state"] == "calibrated_with_suspects"
    assert report["samples"] == 3 and report["px_per_mm"] == pytest.approx(8.4333, abs=1e-3)
    assert report["suspect"] == ["ocr-3"]


def test_a_printed_word_is_never_forced_into_a_number(monkeypatch):
    """Review4: lidere takılan `FRONT` etiketi whitelist turunda `2` diye okunmuştu."""
    glyphs = [perceive_module.Glyph(cx=20.0 + index * 20, cy=20.0, x=int(10 + index * 20), y=10,
                                    w=18, h=26, separator=False) for index in range(5)]
    crop_source = np.full((60, 140), 255, dtype=np.uint8)
    crop_source[10:40, 10:130] = 30

    def fake_ocr(crop, angle, whitelist):
        return "FRONT" if not whitelist else "2"

    monkeypatch.setattr(perceive_module, "_ocr_upright", fake_ocr)

    span = perceive_module._read_cluster(crop_source, glyphs, [0, 1, 2, 3, 4], 0, None,
                                         [[0.0, 0.0], [0.0, 100.0]], "leader")

    assert span is None, "görünüş etiketi ölçü olamaz"


def test_a_symbol_is_not_forced_into_a_number(monkeypatch):
    """pilot-block-01: (481,697) kutusunda üçgen sembolü var; whitelist turu onu `4` diye okumuştu.

    Ölçülmüş denemeler: `A`, `>`, `—`, `` — hiçbiri rakam değil. Rakam sınırlaması olmadan cevap
    veremeyen bir tur her mürekkepten bir sayı çıkarır; bu yüzden yalnız dürüst bir turda rakam
    görüldüyse sorulur.
    """
    glyphs = [perceive_module.Glyph(cx=20.0, cy=20.0, x=10, y=10, w=24, h=28, separator=False)]
    crop_source = np.full((60, 60), 255, dtype=np.uint8)
    crop_source[10:40, 10:40] = 30
    answers = {0.0: "A", -89.17: ">", 90.0: "—", -90.0: ""}

    monkeypatch.setattr(perceive_module, "_ocr_upright",
                        lambda crop, angle, whitelist: "4" if whitelist else answers.get(round(angle, 2), ""))

    span = perceive_module._read_cluster(crop_source, glyphs, [0], 0, None,
                                         [[0.0, 0.0], [0.0, 54.0]], "dimension")

    assert span is None, "üzerinde sayı olmayan mürekkep ölçü olamaz"


def test_a_forced_pass_settles_a_number_the_honest_pass_saw(monkeypatch):
    """Rakam sınırlaması uydurmaz ama netleştirir: dürüst tur `1O` dediyse `10` kabul edilir."""
    glyphs = [perceive_module.Glyph(cx=20.0, cy=20.0, x=10, y=10, w=18, h=26, separator=False)]
    crop_source = np.full((60, 60), 255, dtype=np.uint8)
    crop_source[10:40, 10:40] = 30

    monkeypatch.setattr(perceive_module, "_ocr_upright",
                        lambda crop, angle, whitelist: "10" if whitelist else "1O")

    span = perceive_module._read_cluster(crop_source, glyphs, [0], 0, None,
                                         [[0.0, 0.0], [0.0, 54.0]], "dimension")

    assert span is not None and span.value == 10.0


def test_the_guard_asks_who_verified_the_reading_not_what_the_value_is():
    """Review5 V02: 4→4.1 gibi programatik bir değişiklik ya da satır silmek inceleme sayılmaz."""
    spans = [_span("ocr-0", 4.0, 54.0), _span("ocr-1", 9.0, 467.5), _span("ocr-2", 60.0, 506.0)]
    from_sheet = [DimensionRecord(span_id=span.id, text=span.text, value=float(span.value),
                                  role="edge", count=1) for span in spans]

    assert [row["span_id"] for row in _unreviewed(from_sheet, spans)] == ["ocr-0", "ocr-1", "ocr-2"]

    programmatic = [from_sheet[0].model_copy(update={"value": 4.1}), *from_sheet[1:]]
    assert "ocr-0" in [row["span_id"] for row in _unreviewed(programmatic, spans)], \
        "değeri oynatmak doğrulama değildir"

    deleted = from_sheet[1:]
    missing = [row for row in _unreviewed(deleted, spans) if row["reason"] == "tabloda yok"]
    assert [row["span_id"] for row in missing] == ["ocr-0"], "silinen okuma hâlâ doğrulanmamıştır"

    reviewed = [record.model_copy(update={"source": Source.user}) for record in from_sheet]
    assert _unreviewed(reviewed, spans) == []


class _Coder:
    """Refusal must come before the code model is asked anything."""

    def complete(self, *args, **kwargs):
        raise AssertionError("coder asked")


def _build(tmp_path, records, monkeypatch):
    spans = [_span("ocr-0", 4.0, 54.0), _span("ocr-1", 9.0, 467.5), _span("ocr-2", 60.0, 506.0)]
    monkeypatch.setattr("drawingto3d.reason.perceive_with_report", lambda page, reader=None: ([], spans, {}))
    return reason_drawing(DRAWING, tmp_path, coder=_Coder(), records=records)


def test_a_build_from_an_unreviewed_contradicting_table_is_refused(tmp_path, monkeypatch):
    """Sayılar birbirini yalanlarken katı kurmak yanlış parçayı doğru gibi göstermenin yoluydu."""
    records = [DimensionRecord(span_id=f"ocr-{index}", text=text, value=value, role="edge", count=1)
               for index, (text, value) in enumerate((("4", 4.0), ("09", 9.0), ("60", 60.0)))]

    with pytest.raises(CadFailure) as excinfo:
        _build(tmp_path, records, monkeypatch)

    assert "çelişiyor" in str(excinfo.value)
    assert "ocr-1=9" in str(excinfo.value), "reddin gerekçesi ölçülmüş okumaları da yazar"


def test_a_reviewed_table_reaches_the_coder(tmp_path, monkeypatch):
    """Kullanıcı bir sayıyı değiştirdiyse tablo artık paftanın okuması değildir; kapı açılır."""
    records = [DimensionRecord(span_id=f"ocr-{index}", text=text, value=value, role="edge", count=1,
                               source=Source.user)
               for index, (text, value) in enumerate((("40", 40.0), ("55", 55.0), ("60", 60.0)))]

    with pytest.raises(AssertionError):
        _build(tmp_path, records, monkeypatch)
