"""G12.5 §61-§64 — raster profil kurtarma sözleşmesi.

Ölçüm (Exercise_51 zincir izi, 2026-10-08): cephe dış hattının gerçek ekleri 1.6-37 px
aralıklarla geliyor; buna karşılık mesafesiz köşe/yay kuralları yüzlerce px uzaktaki parçaları
zincire ekliyordu (962 adımın 222'si >100 px sıçramayla alınıyordu; en büyük 1965,7 px —
chain-trace-before.log). İki kural bu ayrımdan doğar:

- raster aralık toleransı, paftanın kendi ölçeğindeki gerçek ekleri kapatır (20 px bunları
  reddediyordu; ~40 px = bu paftalarda ~2.5 mm);
- köşe kuralı yalnız paylaşılan mürekkebin eriminde çalışır (satır taşması ~30 px + yay
  kırpması ~10 px); ötesi, halkası zincirin ucundan geçiyor diye uzaktaki bir yayı eklemek olur.
"""

from pathlib import Path

import cv2
import numpy as np

from drawingto3d import guided
from drawingto3d.observe import observe
from drawingto3d.proposal import RASTER_JOIN_TOLERANCE_PX, _loops


def test_raster_chain_closes_the_joins_the_drawing_actually_has():
    """Köşelerde 30 px'lik gerçek aralıklarla bölünmüş kontur yine kapanmalı."""
    lines = {
        "a": (np.array([0.0, 0.0]), np.array([320.0, 0.0])),
        "b": (np.array([350.0, 0.0]), np.array([350.0, 200.0])),
        "c": (np.array([350.0, 200.0]), np.array([30.0, 200.0])),
        "d": (np.array([0.0, 200.0]), np.array([0.0, 30.0])),
    }
    loops = _loops(lines, {}, corner_joins=True, join_tolerance_px=RASTER_JOIN_TOLERANCE_PX)
    assert loops, "30 px'lik gerçek eklerle zincir kapanmalı"
    assert {entity[0] for entity in loops[0]["entities"]} == {"a", "b", "c", "d"}


def test_raster_chain_does_not_close_a_loop_through_a_long_tangent_hop():
    """141 px'lik teğet sıçramasıyla "kapanan" şekil kapalı kontur sayılmamalı.

    İz ölçümü (Exercise_51): mesafesiz köşe kuralı yüzlerce px uzaktaki parçaları zincire
    katıp sahte döngüler kapatıyordu (100 px üstü sıçrama: 222 adet — chain-trace-before.log).

    Kurgu: yay (merkez (0,0), r=100, 0-90°) → ℓ (x=100 doğrusu; yayın çemberine teğet, foot
    (100,0), zincirin ucundan 141 px uzakta) → k (ℓ'nin ucundan yayın başlangıcına 20 px).
    Bugün ℓ "closing" sanılıp 141 px'lik sıçramayla alınıyor ve [yay, ℓ, k] kapalı sayılıyor.
    """
    arcs = {"arc1": (np.array([0.0, 0.0]), 100.0, 0.0, 90.0)}
    lines = {
        "ell": (np.array([100.0, -20.0]), np.array([100.0, 300.0])),
        "k": (np.array([100.0, 300.0]), np.array([100.0, -20.0])),
    }
    loops = _loops(lines, arcs, corner_joins=True, join_tolerance_px=RASTER_JOIN_TOLERANCE_PX)
    assert loops == [], "141 px'lik teğet sıçraması kapalı kontur üretmemeli"


def _gapped_rectangle_sheet(folder: Path, gap: int) -> Path:
    """3300x2300 pafta: köşelerinde `gap` px aralık bırakılmış dikdörtgen + daire + yay.

    Sağ alttaki yarım daire (r=100) paftayı ürünün raster okuma yoluna sokar: köşe birleşimi
    kuralı yalnız mürekkebi görüntüden gelen yaylar için açılır (`proposal.raster_arcs`).
    Dikdörtgenden uzakta, tek başına durur; ölçülen şey dikdörtgenin kendi kapanışıdır.
    """
    image = np.full((2300, 3300), 255, dtype=np.uint8)
    x0, x1, y0, y1 = 900, 2400, 700, 1600
    cv2.line(image, (x0 + gap, y0), (x1, y0), 0, 3)
    cv2.line(image, (x1, y0 + gap), (x1, y1), 0, 3)
    cv2.line(image, (x1 - gap, y1), (x0, y1), 0, 3)
    cv2.line(image, (x0, y1 - gap), (x0, y0), 0, 3)
    cv2.circle(image, (1650, 1150), 120, 0, 3)
    cv2.ellipse(image, (2850, 1980), (80, 80), 0, 180, 360, 0, 3)
    path = folder / f"gapped-{gap}.png"
    cv2.imwrite(str(path), image)
    return path


def test_a_gapped_synthetic_sheet_still_offers_its_closed_outline(tmp_path):
    """§64: sentetik aralık çalışması — küçük aralıklar kapanırken 30 px'lik gerçek ölçek de kapanmalı.

    20 px eşiği gerçek paftaların eklerini (24-37 px) reddediyordu; kural paftanın kendi
    ölçeğindeki aralıkları kapatmalı, 1/2/3/5 px ise regresyon pini.
    """
    for gap in (1, 2, 3, 5, 30):
        options = guided.drawing_options(observe(_gapped_rectangle_sheet(tmp_path, gap)))
        closed = [profile for profile in options["profiles"]
                  if profile.get("kind") == "wire" and (profile.get("contour") or {}).get("ok")]
        assert closed, f"{gap} px aralıkla kontur kapalı gelmeli. notlar: {options['notes']}"
        assert any(len(profile.get("edges") or []) == 4 for profile in closed), \
            f"{gap} px: kapanan teller arasında 4 kenarlı dikdörtgen olmalı"
