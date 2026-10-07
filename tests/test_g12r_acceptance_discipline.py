"""G12R-03 — kabul betiği "kalan satırı" KAPATAMAZ: karar listesi yazılıdır, beklenmeyen satır durdurur.

Ölçülen şey betiğin kendi sözleşmesidir: paftanın okumasından yazılmış listeler reçeteyi ve reçete
dışını tam kapsar; reçetede ya da yazılı listede olmayan bir metin görülürse kabul durur. Gerekçe
fonksiyonunun bilinmeyen metne varsayılan dönmesi (eski `_reason_for`) kaldırılmıştır.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "eval/audits/20261007-g12r-strategy-plate/g12r_strategy_plate_acceptance.py"
PLATE = ROOT / "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF"


def _load():
    spec = importlib.util.spec_from_file_location("g12r_plate_acceptance", ACCEPTANCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_unknown_row_stops_the_acceptance():
    """İncelemenin probe'u: reçetede olmayan YENİ bir ölçü satırı otomatik kapanamaz."""
    module = _load()
    written = {item["hint"]: item["reason"] for item in module.NON_MODEL_RECIPE}
    recipe = [item["hint"] for item in module.CALL_RECIPE]
    rows = {"50,00": ["k1"], "NEW REAL DIMENSION 123.45": ["k9"], "A4": ["k2"]}
    assert module.unexpected_rows(rows, written, recipe) == ["NEW REAL DIMENSION 123.45"]
    assert module.unexpected_rows({"50,00": ["k1"], "A4": ["k2"]}, written, recipe) == []


def test_the_written_lists_cover_every_row_the_plate_actually_shows():
    """Paftanın bugünkü okuması: her ipucu ya reçetede ya YAZILI listede — artık satır kalmıyor."""
    module = _load()
    from drawingto3d.guided import GuidedStore
    import tempfile

    store = GuidedStore(pathlib.Path(tempfile.mkdtemp()) / "store")
    opened = store.create(PLATE.read_bytes())
    hints = sorted({(row.get("machine_text_hint") or "").strip()
                    for row in store.load(opened["token"])["callout_candidates"]})
    written = {item["hint"]: item["reason"] for item in module.NON_MODEL_RECIPE}
    recipe = [item["hint"] for item in module.CALL_RECIPE]
    assert module.unexpected_rows({hint: ["k"] for hint in hints}, written, recipe) == []
    assert len(written) + len(recipe) >= len(hints), "liste paftadan küçük olamaz"


def test_every_written_row_carries_its_own_reason_and_no_fallback_remains():
    """Her satırın gerekçesi elle yazılıdır; bilinmeyen metne dönen varsayılan gerekçe YOK."""
    module = _load()
    assert not hasattr(module, "_reason_for") and not hasattr(module, "FALLBACK_REASON")
    reasons = [item["reason"].strip() for item in module.NON_MODEL_RECIPE]
    assert all(reasons), "her yazılı satır gerekçe taşır"
    assert all("varsayılan" not in reason and "parçası (kendi kutusunda" not in reason
               for reason in reasons), "eski varsayılan gerekçe metni kalmadı"
    hints = [item["hint"] for item in module.NON_MODEL_RECIPE]
    assert len(hints) == len(set(hints)), "yazılı listede yinelenen ipucu yok"
