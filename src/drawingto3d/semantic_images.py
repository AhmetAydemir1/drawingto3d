"""Kaynaktan modele gidecek görselleri hazırlama: ham sayfa, ayrı overlay, crop.

Üç kural bu dosyanın varlık sebebi:

1. **Kaynak izi.** Her görsel, hangi dosyanın (sha256) hangi sayfasından, hangi dönüşümle geldiğini
   taşır. Bir crop'un kaynak kutusu normalize `[x0,y0,x1,y1]` ise dönüşüm eksen hizalı ölçeklemedir ve
   kayda geçer; mm/CAD koordinatı değildir.
2. **Ayrıntı uydurulmaz.** PDF bölgesi kaynaktan yüksek çözünürlükte **yeniden render** edilir; raster
   crop kaynağın kendi piksellerinden alınır ve büyütme "yeni ayrıntı" diye sunulmaz (`native_raster`,
   `render_dpi=null`). Desteklenmeyen sayfa/rotasyon sessizce ilk sayfaya düşmez: açıkça reddedilir.
3. **Overlay ayrı görseldir.** Ham sayfayı değiştirmez, yalnız gerçek gözlem kimliklerini ve
   kutularını adresler; "bu deliktir" gibi bir semantik karar basmaz. Kimlik yeniden adlandırılırsa
   snapshot eşlemesi kayıtta durur.

Hash ve boyut buradan değil, hazırlanan **son byte'lardan** hesaplanır (`PreparedImage`), böylece
çağıranın metadata beyanı ölçümün yerine geçemez.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from pydantic import ValidationError

from drawingto3d.ingest import RASTER_DPI
from drawingto3d.observe import Observations
from drawingto3d.plan import source_hash
from drawingto3d.semantic_schema import (ImageBundle, ManifestMismatch, PreparedImage, Region,
                                         SemanticInputError, UnsupportedSource)

RAW_PAGE_DPI = float(RASTER_DPI)      # ham sayfa: 200 dpi (gözlem çerçevesiyle aynı)
CROP_DPI = 600.0                      # kaynaktan yeniden render edilen bölge
OVERLAY_VERSION = "semread-overlay/1"
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


@dataclass(frozen=True)
class SourcePage:
    """Bir kaynak dosyanın seçili sayfası: çerçeve ölçüsü, hash'i ve gerçekten decode edilen kare."""

    path: Path
    source_type: str
    sha256: str
    page_index: int
    rotation: int
    width_pt: float | None
    height_pt: float | None
    frame_width_px: int
    frame_height_px: int
    render_dpi: float | None
    frame_png: bytes

    def as_record(self) -> dict:
        return {
            "path": str(self.path), "source_type": self.source_type, "sha256": self.sha256,
            "page_index": self.page_index, "rotation": self.rotation,
            "size_pt": None if self.width_pt is None else [self.width_pt, self.height_pt],
            "frame_px": [self.frame_width_px, self.frame_height_px],
            "frame_dpi": self.render_dpi,
        }


def open_source(path: str | Path, *, page_index: int = 0) -> SourcePage:
    """Kaynağı aç ve çerçevesini sabitle. Desteklenmeyen sayfa/rotasyon burada düşer.

    Sessiz düşme yoktur: istenen sayfa yerine ilk sayfayı kullanmak, "sıfırıncı sayfa" sanılan
    kanıtı başka bir paftanın kanıtı yapar.
    """
    file = Path(path)
    if not file.exists():
        raise SemanticInputError(f"kaynak dosya yok: {file}")
    suffix = file.suffix.lower()
    if suffix == ".pdf":
        return _open_pdf(file, page_index)
    if suffix in RASTER_SUFFIXES:
        if page_index != 0:
            raise UnsupportedSource(f"tek karelik raster için page_index yalnız 0 olabilir: {page_index}")
        return _open_raster(file)
    raise UnsupportedSource(f"desteklenmeyen dosya türü: {suffix or '(yok)'}")


def _open_pdf(file: Path, page_index: int) -> SourcePage:
    with pdfium.PdfDocument(str(file)) as document:
        if len(document) == 0:
            raise UnsupportedSource("pdf boş")
        if page_index != 0:
            raise UnsupportedSource(f"ilk kapsam yalnız page_index=0; istenen: {page_index}")
        page = document[0]
        rotation = int(page.get_rotation())
        if rotation != 0:
            raise UnsupportedSource(f"döndürülmüş sayfa desteklenmiyor: /Rotate={rotation}")
        width_pt, height_pt = (float(value) for value in page.get_size())
        bitmap = page.render(scale=RAW_PAGE_DPI / 72.0)
        frame = _bitmap_to_bgr(bitmap)
    return SourcePage(path=file, source_type="pdf", sha256=source_hash(file), page_index=0, rotation=0,
                      width_pt=width_pt, height_pt=height_pt,
                      frame_width_px=frame.shape[1], frame_height_px=frame.shape[0],
                      render_dpi=RAW_PAGE_DPI, frame_png=_encode_png(frame))


def _open_raster(file: Path) -> SourcePage:
    frame = cv2.imread(str(file), cv2.IMREAD_COLOR)
    if frame is None:
        raise UnsupportedSource(f"görüntü çözülemedi: {file}")
    return SourcePage(path=file, source_type="raster", sha256=source_hash(file), page_index=0,
                      rotation=0, width_pt=None, height_pt=None,
                      frame_width_px=frame.shape[1], frame_height_px=frame.shape[0],
                      render_dpi=None, frame_png=_encode_png(frame))


def _bitmap_to_bgr(bitmap) -> np.ndarray:
    array = bitmap.to_numpy()
    if array.ndim == 2:
        return cv2.cvtColor(array, cv2.COLOR_GRAY2BGR)
    if array.shape[2] == 4:
        array = cv2.cvtColor(array, cv2.COLOR_RGBA2BGR)
    elif array.shape[2] == 3:
        array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
    return array


def _encode_png(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise SemanticInputError("png kodlanamadı")
    return encoded.tobytes()


def frame_png(source: SourcePage) -> bytes:
    """Ham sayfa görüntüsü (yeniden çizilmiş, izlenebilir kare)."""
    return source.frame_png


def resize_png(png: bytes, max_side: int | None) -> tuple[bytes, dict]:
    """İsteğe bağlı küçültme; **büyütme yok**. Politika ve gerçek boyut kayda girer.

    Hiçbir şey yapılmadıysa `applied=False` yazılır: "resize politikası var" ile "resize uygulandı"
    aynı şey değildir ve ikisi de ölçülmeli.
    """
    policy = {"max_side": None if max_side is None else int(max_side), "applied": False,
              "interpolation": None, "from_px": None, "to_px": None}
    if max_side is None:
        return bytes(png), policy
    image = cv2.imdecode(np.frombuffer(bytes(png), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise SemanticInputError("resize için görsel çözülemedi")
    height, width = image.shape[:2]
    policy["from_px"] = [int(width), int(height)]
    longest = max(width, height)
    if longest <= int(max_side):
        policy["to_px"] = [int(width), int(height)]
        return bytes(png), policy
    scale = int(max_side) / float(longest)
    resized = cv2.resize(image, (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
                         interpolation=cv2.INTER_AREA)
    policy.update({"applied": True, "interpolation": "INTER_AREA",
                   "to_px": [int(resized.shape[1]), int(resized.shape[0])]})
    return _encode_png(resized), policy


def _normalise_bbox(bbox) -> tuple[float, float, float, float]:
    try:
        region = Region.model_validate(dict(zip(("x0", "y0", "x1", "y1"), [float(v) for v in bbox])))
    except (ValidationError, TypeError, ValueError) as exc:
        raise SemanticInputError(f"kaynak kutusu geçersiz: {exc}") from exc
    return (region.x0, region.y0, region.x1, region.y1)


def _pixel_box(source: SourcePage, bbox: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """Normalize kutuyu çerçevenin piksel kutuna çevir (sol üst origin, y aşağı)."""
    x0, y0, x1, y1 = bbox
    left = int(np.floor(x0 * source.frame_width_px))
    top = int(np.floor(y0 * source.frame_height_px))
    right = int(np.ceil(x1 * source.frame_width_px))
    bottom = int(np.ceil(y1 * source.frame_height_px))
    left, top = max(0, left), max(0, top)
    right, bottom = min(source.frame_width_px, max(right, left + 1)), min(source.frame_height_px,
                                                                       max(bottom, top + 1))
    return left, top, right, bottom


def prepare_full_page(source: SourcePage, image_id: str, *,
                      resize_max_side: int | None = None) -> PreparedImage:
    """Kaynağın kendi çerçevesi: PDF'te 200 dpi render, raster'da decode edilen pikseller."""
    png, policy = resize_png(source.frame_png, resize_max_side)
    return PreparedImage(
        image_id=image_id, kind="full_page", png=png, source_sha256=source.sha256,
        source_type=source.source_type, render_mode=("pdf_rerender" if source.source_type == "pdf"
                                                     else "native_raster"),
        render_dpi=source.render_dpi, resize_policy=policy)


def prepare_crop(source: SourcePage, image_id: str, bbox_page_norm,
                 *, dpi: float = CROP_DPI, resize_max_side: int | None = None) -> PreparedImage:
    """Seçili bölge: PDF kaynakta **yeniden render**, raster kaynakta native piksel.

    Raster'da bölge kaynağın kendi piksellerinden alınır (`native_raster`, `render_dpi=null`); bir
    raster crop'u büyütmek yeni ayrıntı üretmez, yalnız büyütülmüş bir kopya olur ve öyle kaydedilir.
    """
    box = _normalise_bbox(bbox_page_norm)
    if source.source_type == "pdf":
        png = _render_pdf_crop(source, box, dpi=float(dpi))
        mode, render_dpi = "pdf_rerender", float(dpi)
    else:
        frame = cv2.imdecode(np.frombuffer(source.frame_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        left, top, right, bottom = _pixel_box(source, box)
        png = _encode_png(frame[top:bottom, left:right])
        mode, render_dpi = "native_raster", None
    png, policy = resize_png(png, resize_max_side)
    return PreparedImage(
        image_id=image_id, kind="crop", png=png, source_sha256=source.sha256,
        source_type=source.source_type, source_bbox_page_norm=box,
        render_mode=mode, render_dpi=render_dpi, resize_policy=policy)


def _render_pdf_crop(source: SourcePage, bbox: tuple[float, float, float, float], *, dpi: float) -> bytes:
    """Bölgeyi kaynak PDF'ten yeniden render et — bütün paftayı yüksek çözünürlükte tutmadan.

    pypdfium2'nin `crop` alanı **kenarlardan kesilen** miktardır `(sol, alt, sağ, üst)`, mutlak
    koordinat değil; bu yüzden normalize kutu önce kesme miktarlarına çevrilir.
    """
    x0, y0, x1, y1 = bbox
    width_pt, height_pt = float(source.width_pt), float(source.height_pt)
    left_cut = max(0.0, x0 * width_pt)
    right_cut = max(0.0, (1.0 - x1) * width_pt)
    top_cut = max(0.0, y0 * height_pt)
    bottom_cut = max(0.0, (1.0 - y1) * height_pt)
    if width_pt - left_cut - right_cut <= 1.0 or height_pt - top_cut - bottom_cut <= 1.0:
        raise SemanticInputError(f"crop kutusu PDF sayfasında çok küçük: {bbox}")
    with pdfium.PdfDocument(str(source.path)) as document:
        page = document[0]
        bitmap = page.render(scale=dpi / 72.0, crop=(left_cut, bottom_cut, right_cut, top_cut))
        if bitmap.width < 1 or bitmap.height < 1:  # pragma: no cover - pdfium kendi sınırını denetler
            raise SemanticInputError(f"crop render boş çıktı: {bbox} @ {dpi} dpi")
        array = _bitmap_to_bgr(bitmap)
    return _encode_png(array)


def _overlay_entries(observations: Observations) -> list[dict]:
    """Çizilecek gerçek gözlemler ve ölçülmüş kutuları — snapshot da bunun üstünden kurulur.

    Overlay ile snapshot kimliğinin aynı listeden üretilmesi kasıtlıdır: ayrı iki liste, çizilen ile
    kaydedilenin sessizce ayrışması demekti.
    """
    entries: list[dict] = []
    for primitive in observations.primitives:
        entries.append({"id": primitive.id, "kind": primitive.kind,
                        "bbox": _primitive_box(primitive)})
    for text in observations.texts:
        entries.append({"id": text.id, "kind": text.kind, "bbox": _text_box(text)})
    return sorted(entries, key=lambda item: item["id"])


def overlay_from_observations(observations: Observations, image_id: str, *, source: SourcePage | None = None,
                              max_labels: int = 400,
                              resize_max_side: int | None = None) -> PreparedImage:
    """Gözlemleri ham sayfanın **üstüne ayrı bir görsel** olarak çiz.

    Yalnız gerçek gözlem kimlikleri ve ölçülmüş kutuları çizilir; hiçbir semantik karar ("delik",
    "çap") basılmaz. Kimliklerin kutusu/kimliği snapshot hash'ine girer, böylece kimlik yeniden
    adlandırılırsa eşleme kayıtta bulunur. `resize_max_side` verilirse policy kayda geçer ve
    gerçekten uygulanır: bildirilen ama uygulanmayan bir ayar kaydı yanıltıcı olurdu.
    """
    frame = observations.frame
    canvas = np.full((int(frame.height), int(frame.width), 3), 255, dtype=np.uint8)
    for path in observations.paths:
        _draw_box(canvas, path.bbox, (200, 200, 200), 1)
    for primitive in observations.primitives:
        if primitive.centre and primitive.radius:
            cv2.circle(canvas, (int(round(primitive.centre[0])), int(round(primitive.centre[1]))),
                       int(round(primitive.radius)), (180, 120, 40), 2)
    for text in observations.texts:
        _draw_box(canvas, text.bbox, (60, 60, 60), 1)
    for entry in _overlay_entries(observations)[:max_labels]:
        box = entry.get("bbox")
        if not box:
            continue
        cv2.putText(canvas, entry["id"], (int(box[0]), max(10, int(box[1]) - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
    if source is None:
        raise SemanticInputError("overlay için kaynak sayfa kaydı gerekli")
    png, policy = resize_png(_encode_png(canvas), resize_max_side)
    return PreparedImage(
        image_id=image_id, kind="overlay", png=png,
        source_sha256=observations.source.sha256, source_type=source.source_type,
        render_mode=("pdf_rerender" if source.source_type == "pdf" else "native_raster"),
        render_dpi=source.render_dpi,
        observation_snapshot_id=observation_snapshot_id(observations),
        resize_policy=policy)


def _draw_box(canvas: np.ndarray, bbox, colour: tuple[int, int, int], thickness: int) -> None:
    x, y, w, h = float(bbox.x), float(bbox.y), float(bbox.w), float(bbox.h)
    cv2.rectangle(canvas, (int(round(x)), int(round(y))), (int(round(x + w)), int(round(y + h))),
                  colour, thickness)


def _text_box(text) -> list[float] | None:
    box = text.bbox
    return [float(box.x), float(box.y), float(box.x + box.w), float(box.y + box.h)]


def _primitive_box(primitive) -> list[float] | None:
    if not primitive.centre or not primitive.radius:
        if primitive.start and primitive.end:
            return [min(primitive.start[0], primitive.end[0]), min(primitive.start[1], primitive.end[1]),
                    max(primitive.start[0], primitive.end[0]), max(primitive.start[1], primitive.end[1])]
        return None
    cx, cy = primitive.centre
    r = float(primitive.radius)
    return [cx - r, cy - r, cx + r, cy + r]


def observation_snapshot_id(observations: Observations) -> str:
    """Overlay ile aynı kural ve aynı veri: gerçek gözlem kimlikleri + ölçülmüş kutular.

    Kimlikler yeniden adlandırılırsa bu hash değişir, yani "hangi snapshot'a baktık" sorusu kayıtta
    cevaplanabilir kalır.
    """
    payload = {"version": OVERLAY_VERSION, "source_sha256": observations.source.sha256,
               "observations": _overlay_entries(observations)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def declared_conflict(image: PreparedImage, declared: dict) -> None:
    """Çağıranın beyanı ölçümle çelişiyorsa hata: beyan ölçüm sayılmaz."""
    image.verify_declared(sha256=declared.get("sha256"), width_px=declared.get("width_px"),
                          height_px=declared.get("height_px"))


__all__ = ["CROP_DPI", "ImageBundle", "ManifestMismatch", "OVERLAY_VERSION", "PreparedImage",
           "RAW_PAGE_DPI", "SourcePage", "declared_conflict", "frame_png", "observation_snapshot_id",
           "open_source", "overlay_from_observations", "prepare_crop", "prepare_full_page",
           "resize_png"]
