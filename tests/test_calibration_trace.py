"""Ölçü izleyicisinin eleme katmanları: neden düştüğü ölçülür, tahmin edilmez.

S02-b'nin sorusu "plate-01/02 neden kalibre etmiyor" idi; cevabın "eşik" değil "hangi sayı hangi
katmanda düştü" olduğunu göstermek için iz, sayıları metinle değil **kimlikle** eşler ve her eleme için
satırda ölçülen gerçeği yazar.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("calibration_trace", ROOT / "eval" / "calibration_trace.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["calibration_trace"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _facts(*, candidates=1, crossings=0, pairs=0, reading_across=True, arrowed=0) -> dict:
    return {"reading_across": reading_across, "text_size_px": 20.0, "text_span": [0.0, 20.0],
            "row_offset": 100.0, "reach_px": 60.0,
            "candidates": [{"extent": [0.0, 100.0], "offset": 100.0, "arrow_at_start": 0,
                            "arrow_at_end": 0}] * candidates,
            "arrowed_lines_that_bracket_the_text": [{}] * arrowed,
            "crossings": [float(index) for index in range(crossings)],
            "span_pairs_the_row_offers": [[0.0, 100.0]] * pairs}


def test_a_diameter_callout_is_named_as_a_callout_not_as_a_missed_dimension():
    """`Ø8 THRU` çaptır: kalibrasyon çifti olarak kullanılmaz ve bu, hatırlama kaybı gibi yazılmaz."""
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.diameter"), _facts())

    assert "çağrı ölçüsü" in reason


def test_a_number_with_no_line_beside_it_says_the_line_was_not_found():
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"),
                                 _facts(candidates=0, crossings=0))

    assert "aday çizgi yok" in reason


def test_a_line_without_crossings_says_the_number_does_not_stand_on_a_dimension_line():
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"), _facts(crossings=0))

    assert "kesişme yok" in reason and "aday=1" in reason


def test_a_single_crossing_says_the_other_end_is_missing():
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"), _facts(crossings=1))

    assert "tek kesişme" in reason


def test_two_crossings_without_a_pair_says_the_pair_could_not_be_built():
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"),
                                 _facts(crossings=2, pairs=0))

    assert "çift" in reason


def test_a_row_that_offers_a_pair_puts_the_loss_in_the_binding_stage():
    """Satır çifti sunuyorsa kayıp algılamada değil bağlamada: katman adı yazılır."""
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"),
                                 _facts(crossings=2, pairs=1))

    assert "bağlama" in reason


def test_a_vertical_row_is_named_as_vertical():
    module = load_module()
    reason = module._why_dropped(SimpleNamespace(kind="SpanKind.linear"),
                                 _facts(reading_across=False))

    assert "dikey" in reason


def test_a_missing_value_is_not_guessed():
    module = load_module()
    assert "okunamadı" in module._why_dropped(SimpleNamespace(kind="SpanKind.linear"), None)


def test_the_trace_keeps_the_two_drop_layers_apart_on_a_real_part():
    """Gerçek paftada katmanlar: basılı ≥ algılanan ≥ tutulan ve kimlikler kapsanır (metin değil)."""
    corpus = ROOT / "out/lab/data/v2"
    part = corpus / "pilot-plate-01"
    if not (part / "drawing.pdf").exists():
        pytest.skip("v2 korpusu diskte yok (out/ gitignore'da)")

    module = load_module()
    row = module.trace_part(part)

    printed_ids = {entry["id"] for entry in row["printed_numbers"]}
    perceived_ids = {entry["id"] for entry in row["perceived"]}
    kept_ids = {entry["id"] for entry in row["kept"]}
    dropped_ids = {entry["id"] for entry in row["dropped_by_the_gate"]}

    assert len(printed_ids) >= len(perceived_ids) >= len(kept_ids)
    assert kept_ids <= perceived_ids, "tutulan her sayı algılananlar arasında olmalı"
    assert dropped_ids and dropped_ids.isdisjoint(perceived_ids), \
        "hiç okunmayanlar algılananlarla kesişmemeli"
    assert all(entry["reason"] for entry in row["dropped_by_the_gate"]), \
        "her eleme bir gerekçe taşımalı"
