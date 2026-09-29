"""Review6 W02 regresyonu: şüpheli ölçü de inceleme ister.

Denetimin karşı örneği: üç doğru ölçek gözlemi (60/600 px, 20/200 px, 40/400 px) + bir yanlış `9` (550 px)
→ `scale.verdict` `calibrated_with_suspects` diyor ve `wrong` şüpheli listesinde. Eski kapı yalnız
`contradictory` durumunu sorduğu için bu okuma inceleme istemeden kuruluma gidebiliyordu.

Burada sınanan şey kapının kararı: `_sheet_needs_review` şüpheli pafta için gerekçe döndürüyor mu, temiz
pafta için susuyor mu, ve şüpheli okuma doğrulanmamış okumalar arasında görünüyor mu. Üçü birlikte, kurulum
kapısının şüpheli ölçüde kapandığını gösterir (kapı bu iki koşulun ikisi de sağlanınca reddediyor).
"""

from __future__ import annotations

from drawingto3d import reason as reason_module
from drawingto3d import scale
from drawingto3d.schema import BBox, DimensionRecord, Span


def _span(span_id: str, value: float, length_px: float, *, mode: str = "dimension") -> Span:
    """Paftanın ölçtüğü okuma: değer + kendi ölçü çizgisinin piksel uzunluğu."""
    return Span(id=span_id, text=f"{value:g}", value=value, kind="linear", unit="mm",
                bbox=BBox(x=100.0, y=100.0, w=20.0, h=20.0),
                anchors=[[0.0, 0.0], [length_px, 0.0]], anchor_mode=mode, source="pdf_text")


class _FakePage:
    """Kapının kararı için yalnız span listesi gerekiyor; pafta okuması bu testte yapılmıyor."""

    def __init__(self, spans):
        self.spans = spans


def _suspect_spans() -> list[Span]:
    return [_span("a", 60.0, 600.0), _span("b", 20.0, 200.0), _span("c", 40.0, 400.0),
            _span("wrong", 9.0, 550.0)]


def test_a_suspect_sheet_asks_for_a_review(monkeypatch):
    """Üç doğru + bir yanlış `9`: pafta kendi ölçeğiyle çelişen okumayı adlandırıyor ve inceleme istiyor."""
    spans = _suspect_spans()
    verdict = scale.verdict(spans)
    assert verdict["state"] == "calibrated_with_suspects", verdict
    assert verdict.get("suspect") == ["wrong"], verdict

    monkeypatch.setattr(reason_module, "sheet_scale", lambda _page: verdict)

    assert reason_module._sheet_needs_review(_FakePage(spans)) is not None


def test_a_calibrated_sheet_asks_for_nothing(monkeypatch):
    """Üç okuma da aynı ölçekte buluşuyorsa pafta kendini anlatıyor: inceleme istenmez."""
    spans = _suspect_spans()[:3]
    verdict = scale.verdict(spans)
    assert verdict["state"] == "calibrated", verdict

    monkeypatch.setattr(reason_module, "sheet_scale", lambda _page: verdict)

    assert reason_module._sheet_needs_review(_FakePage(spans)) is None


def test_a_suspect_reading_becomes_a_question_with_the_scale_candidate(monkeypatch):
    """Ölçekle çelişen okuma sessizce düzeltilmez: ölçeğin dediği değer aday olarak sorulur (review6 W02)."""
    spans = [_span("nine", 9.0, 467.5), _span("sixty", 60.0, 506.0)]
    witnesses = [("a", 55.0, 467.5), ("b", 60.0, 506.0), ("c", 8.0, 67.5)]
    sheet = scale.verdict(spans, witnesses=witnesses)
    assert sheet["suspect"] == ["nine"], sheet
    monkeypatch.setattr(reason_module, "sheet_scale", lambda _page: sheet)

    rows = reason_module.suspect_questions(_FakePage(spans))

    assert [row["span_id"] for row in rows] == ["nine"], rows
    assert rows[0]["yazilan"] == "9"
    assert rows[0]["tam_sayi_adayi"] == 55.0, rows[0]
    assert "55" in rows[0]["soru"], rows[0]


def test_the_suspect_reading_is_among_the_unreviewed(monkeypatch):
    """Kullanıcı doğrulaması yoksa şüpheli okuma da doğrulanmamış okumalar listesinde görünür."""
    spans = _suspect_spans()
    verdict = scale.verdict(spans)
    monkeypatch.setattr(reason_module, "sheet_scale", lambda _page: verdict)
    records = [DimensionRecord(span_id=span.id, text=span.text, value=float(span.value),
                               role="edge", count=1) for span in spans]

    unreviewed = reason_module._unreviewed(records, spans)

    assert [row["span_id"] for row in unreviewed] == ["a", "b", "c", "wrong"]
    assert reason_module._sheet_needs_review(_FakePage(spans)) is not None
