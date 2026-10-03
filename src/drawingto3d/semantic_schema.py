"""SEMREAD-001A'nın küçük sözleşmesi: hazırlanan görsel, kaynak izi ve probe yanıtı.

Bu dosya genel bir ontoloji değildir. Yalnız üç şeyi tanımlar:

* `PreparedImage` — modele **gidecek son PNG byte'ları** ve o görselin kaynağa nasıl bağlandığı
  (kaynak hash'i, sayfa, crop kutusu, render biçimi, çözünürlük, dönüşüm). Hash ve boyut burada,
  byte'lardan hesaplanır: çağıranın beyanı doğrulanacak bir iddiadır, ölçüm değil.
* `Region` — normalize `[0,1]`, sol üst `(0,0)`, x sağa, y aşağı. Sonlu olmayan, aralık dışına çıkan,
  ters veya sıfır alanlı kutu **reddedilir**; `clamp` edilmez.
* `ProbeResponse` — modelin sözleşmesi: `schema_version`, `items[]` (`image_id`, `description`,
  `shape`, `region`). `shape` küçük ve sürümlü bir sınıflandırmadır (aynı seçenekler her görsele);
  `supported` ya da `source=user` bu şemada yoktur ve `extra="forbid"` ile reddedilir: modelin kendi
  beyanı kabul kararına dönüşemez.

Bilinmeyen görsel kimliği bir *referans* hatasıdır, şema hatası değil; ikisi ayrı ölçülür çünkü
"model yanlış görsele işaret etti" ile "model şemayı tutturamadı" farklı onarımlar ister. Bu probe
"her gönderilen görsele tam bir yanıt" ister: eksik, tekrarlanan, bilinmeyen kimlik ve boş `items`
reddedilir (bkz. `check_references`).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MANIFEST_SCHEMA = "semread-input-manifest/1"
PROBE_SCHEMA_VERSION = "semread-probe/2"
PREPROCESSING_VERSION = "semread-prep/1"

IMAGE_KINDS = ("full_page", "overlay", "crop")
SOURCE_TYPES = ("pdf", "raster")
RENDER_MODES = ("pdf_rerender", "native_raster")

# Şekil kontrolü tek bir sınıflandırma alanıyla yapılır: seçenekler **her görsele aynı** sunulur ve
# hangi kimliğin hangi sınıfı taşıdığı şemaya/prompta yazılmaz. `unknown` geçerli bir beyandır ama
# görsel kontrolü **başarısız/kararsız** bırakır: şema uyumu tek başına görsel başarı değildir.
SHAPE_CLASSES = ("triangle", "square", "circle", "other", "unknown")

# Kimlik nötr olmalı: kaynak hash'i, dosya adı ya da içerik adı modele ezberlenecek kimlik olarak
# verilmez. Bu yüzden yalnız `image-<sayı>` kabul edilir.
IMAGE_ID_PATTERN = re.compile(r"^image-[1-9][0-9]{0,5}$")


class SemanticInputError(ValueError):
    """Hazırlanan girdi sözleşmeyi tutmuyor."""


class UnsupportedSource(SemanticInputError):
    """İstenen sayfa/rotasyon/dosya türü bu dilimde desteklenmiyor."""


class ManifestMismatch(SemanticInputError):
    """Çağıranın beyanı ölçülen byte'larla çelişiyor."""


class ProbeParseError(ValueError):
    """Yanıt gövdesi JSON değil. Otomatik "tamir" yapılmaz."""


class ProbeSchemaError(ValueError):
    """JSON çözüldü ama sözleşmeye uymuyor (eksik/fazla alan, aralık dışı bbox)."""


class ProbeReferenceError(ValueError):
    """Yanıt, bu çağrıda gönderilmeyen bir görsel kimliğine işaret ediyor."""


def _finite(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"sonlu olmayan sayı: {value!r}")
    return number


class Region(BaseModel):
    """Normalize kutu: `[0,1]` içinde, sol üst origin, x sağa, y aşağı, pozitif alanlı.

    Kutu geçersizse hata verilir; geçerli hâle getirmek için kırpılmaz (`clamp` yok). Kırpma
    "model doğru söyledi" görüntüsü üretir ve yanlış bbox'ı kanıta çevirir.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    x0: float
    y0: float
    x1: float
    y1: float

    @field_validator("x0", "y0", "x1", "y1")
    @classmethod
    def _finite(cls, value: float) -> float:
        return _finite(value)

    def model_post_init(self, _context: Any) -> None:
        for name, value in (("x0", self.x0), ("y0", self.y0), ("x1", self.x1), ("y1", self.y1)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name}={value!r} [0,1] dışında: kutu kırpılmaz, reddedilir")
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError(f"ters ya da sıfır alanlı kutu: {self.as_bbox()}")

    def as_bbox(self) -> list[float]:
        return [float(self.x0), float(self.y0), float(self.x1), float(self.y1)]

    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)


class ProbeItem(BaseModel):
    """Bir görsele dair tek kayıt: kısa açıklama, şekil sınıfı ve (biliniyorsa) bölge.

    `description` metindir; görsel gözlemdir, semantik doğruluk kanıtı değildir. `region=None`
    "bilmiyorum" demenin yoludur ve geçerlidir. `shape` küçük ve sürümlü bir sınıflandırmadır: her
    görsele **aynı** seçenekler sunulur, hangi kimliğin hangi sınıfı taşıdığı burada yazılmaz.
    """

    model_config = ConfigDict(extra="forbid")

    image_id: str
    description: str
    shape: str
    region: Region | None = None

    @field_validator("image_id")
    @classmethod
    def _identity(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("image_id boş olamaz")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("description metin olmalı")
        return value

    @field_validator("shape")
    @classmethod
    def _shape(cls, value: str) -> str:
        if value not in SHAPE_CLASSES:
            raise ValueError(f"şekil sınıfı tanımsız: {value!r} (geçerli: {', '.join(SHAPE_CLASSES)})")
        return value


class ProbeResponse(BaseModel):
    """Modelin yanıt sözleşmesi (`semread-probe/2`). Fazladan alan kabul edilmez.

    `supported`/`source=user` gibi kabul beyanları bu şemada yoktur: model kendi yanıtına kabul
    damgası vuramaz, o karar uygulamanındır. Fazladan alan gelirse yanıt şema hatasıdır.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["semread-probe/2"]
    items: list[ProbeItem] = Field(default_factory=list)


def probe_json_schema() -> dict:
    """Ollama'nın `format` alanına verilecek JSON şeması — yanıtın *biçimi* ürün sözleşmesidir.

    Şema kimlikten bağımsızdır: izinli image ID'ler buraya yazılmaz (onlar prompt'tan gelir) ve
    şekil seçenekleri her görsele aynı sunulur, böylece şema bir kimlik→sınıf ipucu taşımaz.
    """
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": [PROBE_SCHEMA_VERSION]},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "image_id": {"type": "string"},
                        "description": {"type": "string"},
                        "shape": {"type": "string", "enum": list(SHAPE_CLASSES)},
                        "region": {
                            "type": ["object", "null"],
                            "properties": {
                                "x0": {"type": "number"},
                                "y0": {"type": "number"},
                                "x1": {"type": "number"},
                                "y1": {"type": "number"},
                            },
                            "required": ["x0", "y0", "x1", "y1"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["image_id", "description", "shape", "region"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["schema_version", "items"],
        "additionalProperties": False,
    }


def parse_probe_json(text: str) -> dict:
    """Ham yanıtı JSON olarak çöz. Bozuk/boş yanıt tamir edilmez, olduğu gibi raporlanır."""
    if not isinstance(text, str) or not text.strip():
        raise ProbeParseError("yanıt boş: çözülecek JSON yok")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProbeParseError(f"JSON çözülemedi: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProbeParseError(f"JSON nesne değil: {type(payload).__name__}")
    return payload


def validate_probe_response(payload: dict) -> ProbeResponse:
    """Şemayı uygula. Hata mesajı hangi alanın tutmadığını söyler; sessiz varsayım yoktur."""
    try:
        return ProbeResponse.model_validate(payload)
    except ValidationError as exc:
        raise ProbeSchemaError(f"şema tutmadı: {exc.error_count()} alan: {_first_errors(exc)}") from exc


def _first_errors(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:4]:
        location = ".".join(str(item) for item in error.get("loc") or ()) or "(kök)"
        parts.append(f"{location}: {error.get('msg')}")
    return "; ".join(parts)


def check_references(response: ProbeResponse, allowed_image_ids: list[str]) -> dict:
    """Referans **ve kapsam** kontrolü: yalnız bu çağrıda gönderilen kimlikler ve her biri tam bir kez.

    Bu probe'un sözleşmesi "her gönderilen görsele tam bir yanıt"tır: gönderilmemiş bir kimlik,
    tekrarlanan bir madde, yanıtsız kalan bir görsel ya da boş `items` reddedilir. "Az çok yakın"
    bir kimlik kabul edilmez ve bu kural ileride çok bölgeli bir çıktı sözleşmesine genellenmez.
    """
    allowed = list(allowed_image_ids)
    seen = [item.image_id for item in response.items]
    unknown = sorted({name for name in seen if name not in allowed})
    duplicates = sorted({name for name in seen if seen.count(name) > 1})
    missing = [name for name in allowed if name not in seen]
    coverage = {"sent": allowed, "answered": seen, "missing": missing,
                "duplicates": duplicates, "unknown": unknown,
                "exact": not (missing or duplicates or unknown) and len(seen) == len(allowed)}
    checks = [{"image_id": item.image_id, "allowed": item.image_id in allowed,
               "has_region": item.region is not None, "shape": item.shape}
              for item in response.items]
    if unknown:
        raise ProbeReferenceError(
            "gönderilmeyen görsel kimliği: " + ", ".join(unknown)
            + f"; bu çağrıda gönderilenler: {', '.join(allowed)}")
    if not allowed and seen:
        raise ProbeReferenceError("görsel gönderilmedi ama yanıt madde içeriyor")
    if not seen and allowed:
        raise ProbeReferenceError(
            "yanıt boş: her gönderilen görsel için bir madde gerekli "
            f"({', '.join(allowed)})")
    if duplicates:
        raise ProbeReferenceError("tekrarlanan görsel kimliği: " + ", ".join(duplicates)
                                  + " (her görsele tam bir madde)")
    if missing:
        raise ProbeReferenceError("yanıtsız görsel kimliği: " + ", ".join(missing)
                                  + f" (gönderilenler: {', '.join(allowed)})")
    return {"ok": True, "allowed_image_ids": allowed, "referenced_image_ids": sorted(set(seen)),
            "item_count": len(response.items), "coverage": coverage, "checks": checks}


@dataclass(frozen=True)
class PreparedImage:
    """Modele gidecek **son** PNG ve o byte'ların kaynak izi.

    Hash ve boyut burada, `png` byte'larından hesaplanır. Çağıran bir `sha256`/boyut beyan ederse
    `declared=` ile verir ve beyan ölçümle çelişirse `ManifestMismatch` yükselir: "dosya şu olmalı"
    iddiası, "dosya bu" ölçümünün yerine geçemez.
    """

    image_id: str
    kind: str
    png: bytes
    source_sha256: str
    source_type: str = "pdf"
    page_index: int = 0
    source_bbox_page_norm: tuple[float, float, float, float] | None = None
    render_mode: str = "pdf_rerender"
    render_dpi: float | None = None
    observation_snapshot_id: str | None = None
    resize_policy: dict = field(default_factory=dict)
    preprocessing_version: str = PREPROCESSING_VERSION
    # Çağıran bir hash beyan edebilir; beyan ölçümle çelişirse kayıt tutulmaz (aşağıda).
    sha256: str = ""

    def __post_init__(self) -> None:
        if not IMAGE_ID_PATTERN.match(self.image_id or ""):
            raise SemanticInputError(f"kimlik nötr değil: {self.image_id!r} (beklenen: image-<sayı>)")
        if self.kind not in IMAGE_KINDS:
            raise SemanticInputError(f"bilinmeyen kind: {self.kind!r}")
        if self.source_type not in SOURCE_TYPES:
            raise SemanticInputError(f"bilinmeyen source_type: {self.source_type!r}")
        if self.render_mode not in RENDER_MODES:
            raise SemanticInputError(f"bilinmeyen render_mode: {self.render_mode!r}")
        if self.page_index != 0:
            raise SemanticInputError("ilk kapsam yalnız page_index=0")
        if not isinstance(self.png, (bytes, bytearray)) or not self.png:
            raise SemanticInputError("hazırlanan görsel boş")
        if self.render_mode == "native_raster" and self.render_dpi is not None:
            raise SemanticInputError("native raster için render_dpi null olmalı")
        if self.render_mode == "pdf_rerender" and self.render_dpi is None:
            raise SemanticInputError("pdf_rerender için render_dpi yazılmalı")
        if self.kind == "crop" and self.source_bbox_page_norm is None:
            raise SemanticInputError("crop kaynak kutusu olmadan anlamlı değil")
        if self.kind != "crop" and self.source_bbox_page_norm is not None:
            raise SemanticInputError(f"{self.kind} için kaynak kutusu yazılmaz")
        if self.source_bbox_page_norm is not None:
            try:
                Region.model_validate(dict(zip(("x0", "y0", "x1", "y1"), self.source_bbox_page_norm)))
            except ValidationError as exc:
                raise SemanticInputError(f"crop kaynak kutusu geçersiz: {exc}") from exc
        if self.kind == "overlay" and not self.observation_snapshot_id:
            raise SemanticInputError("overlay gerçek gözlem snapshot'ı olmadan yazılamaz")
        object.__setattr__(self, "_frame", _decode_size(self.png))
        digest = hashlib.sha256(bytes(self.png)).hexdigest()
        if self.sha256 and self.sha256 != digest:
            raise ManifestMismatch(
                f"{self.image_id}: beyan edilen sha256 gönderilecek byte'larla uyuşmuyor "
                f"(beyan={self.sha256[:16]}…, ölçülen={digest[:16]}…)")
        object.__setattr__(self, "sha256", digest)

    # -- ölçülen alanlar ---------------------------------------------------

    @property
    def width_px(self) -> int:
        return self._frame[0]  # type: ignore[attr-defined]

    @property
    def height_px(self) -> int:
        return self._frame[1]  # type: ignore[attr-defined]

    def declared_matches(self, *, sha256: str | None = None, width_px: int | None = None,
                         height_px: int | None = None) -> bool:
        if sha256 is not None and sha256 != self.sha256:
            return False
        if width_px is not None and int(width_px) != self.width_px:
            return False
        if height_px is not None and int(height_px) != self.height_px:
            return False
        return True

    def verify_declared(self, *, sha256: str | None = None, width_px: int | None = None,
                        height_px: int | None = None) -> None:
        if not self.declared_matches(sha256=sha256, width_px=width_px, height_px=height_px):
            raise ManifestMismatch(
                f"{self.image_id}: beyan edilen sha256/boyut gönderilecek byte'larla uyuşmuyor "
                f"(ölçülen sha256={self.sha256[:16]}…, {self.width_px}x{self.height_px})")

    # -- dönüşüm -----------------------------------------------------------

    @property
    def t_image_norm_to_page_norm(self) -> list[list[float]]:
        """Görselin normalize çerçevesinden kaynak sayfanın normalize çerçevesine 2x3 afin dönüşüm.

        Full-page ve overlay için birim dönüşümdür. Crop için `[x0,y0,x1,y1]` kutusu eksen hizalı
        ölçeklemedir: `x_page = x0 + u*(x1-x0)`, `y_page = y0 + v*(y1-y0)`.
        """
        if self.kind == "crop" and self.source_bbox_page_norm is not None:
            x0, y0, x1, y1 = self.source_bbox_page_norm
            return [[round(x1 - x0, 9), 0.0, round(x0, 9)], [0.0, round(y1 - y0, 9), round(y0, 9)]]
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    def map_point_to_page(self, u: float, v: float) -> tuple[float, float]:
        (a, b, tx), (c, d, ty) = self.t_image_norm_to_page_norm
        return (a * _finite(u) + b * _finite(v) + tx, c * _finite(u) + d * _finite(v) + ty)

    def map_region_to_page(self, region: Region) -> list[float]:
        u0, v0 = self.map_point_to_page(region.x0, region.y0)
        u1, v1 = self.map_point_to_page(region.x1, region.y1)
        return [round(u0, 6), round(v0, 6), round(u1, 6), round(v1, 6)]

    # -- kayıt -------------------------------------------------------------

    def as_spec(self) -> dict:
        """Input manifest satırı: hash/boyut gönderilecek son byte'lardan."""
        return {
            "image_id": self.image_id,
            "kind": self.kind,
            "source_sha256": self.source_sha256,
            "source_type": self.source_type,
            "page_index": self.page_index,
            "prepared_image_sha256": self.sha256,
            "prepared_image_bytes": len(self.png),
            "width_px": self.width_px,
            "height_px": self.height_px,
            "render_mode": self.render_mode,
            "render_dpi": self.render_dpi,
            "source_bbox_page_norm": list(self.source_bbox_page_norm) if self.source_bbox_page_norm else None,
            "t_image_norm_to_page_norm": self.t_image_norm_to_page_norm,
            "observation_snapshot_id": self.observation_snapshot_id,
            "preprocessing_version": self.preprocessing_version,
            "resize_policy": dict(self.resize_policy),
        }


def _decode_size(png: bytes) -> tuple[int, int]:
    image = cv2.imdecode(np.frombuffer(bytes(png), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise SemanticInputError("hazırlanan görsel PNG olarak çözülemedi")
    height, width = image.shape[:2]
    return int(width), int(height)


class ImageBundle:
    """Bir çağrının görselleri: sıra **gönderim sırasıdır**, kimlikler hazırlıktan gelir.

    Kimlikleri sıraya göre üretmek, sıra değiştiğinde kimliğin de kayması demekti; o zaman model
    "ilk görsel" diyerek her zaman doğru cevap verir ve kimlik-sıra eşlemesi sınanmamış olurdu.
    Bu yüzden görsel nesnesi kimliğiyle gelir, `order` ise yalnız gönderim sırasını belirler.
    """

    def __init__(self, images: list[PreparedImage], *, order: list[str] | None = None) -> None:
        by_id = {image.image_id: image for image in images}
        if len(by_id) != len(images):
            raise SemanticInputError("aynı çağrıda yinelenen görsel kimliği")
        names = list(order) if order is not None else [image.image_id for image in images]
        if sorted(names) != sorted(by_id):
            missing = sorted(set(by_id) - set(names))
            extra = sorted(set(names) - set(by_id))
            raise SemanticInputError(f"sıra listesi görsellerle uyuşmuyor (eksik={missing}, fazla={extra})")
        self.images = [by_id[name] for name in names]

    def __len__(self) -> int:
        return len(self.images)

    @property
    def image_ids(self) -> list[str]:
        return [image.image_id for image in self.images]

    @property
    def pngs(self) -> list[bytes]:
        return [image.png for image in self.images]

    def by_id(self, image_id: str) -> PreparedImage:
        for image in self.images:
            if image.image_id == image_id:
                return image
        raise SemanticInputError(f"bu pakette olmayan görsel: {image_id!r}")

    def manifest(self, *, source: dict | None = None, notes: list[str] | None = None) -> dict:
        return {
            "schema": MANIFEST_SCHEMA,
            "preprocessing_version": PREPROCESSING_VERSION,
            "source": dict(source or {}),
            "image_order": self.image_ids,
            "images": [image.as_spec() for image in self.images],
            "notes": list(notes or []),
        }
