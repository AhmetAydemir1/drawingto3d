"""SEMREAD-001B — **dar** semantic aday sözleşmesi (ayrı sürüm).

Kapsam bilinçli olarak küçüktür: bir aday, bir **callout/hedef** hakkında yalnız şu alanları taşır:

  circle representation / physical hole ayrımı · R vs Ø · basılı değer+birim · count ·
  THRU / finite / unknown sonlanma · açıkça yazılmış derinlik · callout→target binding.

Tasarım kuralları (001B goal'i, bölüm 2):

1. **Kanıt ile yorum ayrı alanlarda.** Çizilmiş bir circle gördü diye `physical.class` "hole" olamaz;
   derinlik yazmıyor diye `termination.class` "thru" sayılamaz. Her alanın kendi `status`'ü vardır ve
   bir alanın bilinmemesi diğer alanları silmez.
2. **Basılı count ile bulunan circle sayısı ayrı alanlarda** taşınır (`count.printed` vs
   `count.found_circles`); ikisi birbirinden türetilmez.
3. **Bilinmeyen `unknown` kalır**; tahmin yazılmaz, eksik alan doldurulmaz.
4. **Model kimlik uydurmaz**: `source.image_id` çağrıda gönderilen kimliklerden biri olmalı,
   `observation_id` yalnız kendisine verilen gözlem tablosundan seçilebilir (VE) ya da `null` olur.
   Bölge gösteren ama gözlem kimliği olmayan aday **geçerlidir** (extractor'ın temsil etmediği bir
   bölgeyi bildirmek yasak değildir).
5. **Boş/bozuk gövde onarılmaz**: `parse_candidate_json` `CandidateParseError` fırlatır.
6. **Model ürün kararı vermez**: `supported`/`confirmed`/`source=user` gibi alanlar şemada yoktur;
   şema bunları taşıyamaz (kapalı anahtar listesi, testle bağlı).
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

CANDIDATE_SCHEMA_VERSION = "semread-candidates/1"
CANDIDATE_READER_VERSION = "semread-candidate-reader/1"
CANDIDATE_RESPONSE_SCHEMA = "semread-candidate-response/1"

# ----------------------------------------------------------------- kapalı sözlükler

REPRESENTATION_CLASSES = ("circle", "arc", "other", "unknown")
PHYSICAL_CLASSES = ("hole", "pocket", "slot", "not_hole", "unknown")
FORM_SYMBOLS = ("R", "diameter", "none", "unknown")
TERMINATIONS = ("thru", "finite", "unknown")
FIELD_STATES = ("known", "unknown", "not_stated")
PROVENANCE_KINDS = ("deterministic", "vlm")
UNITS = ("mm", "in")

# Kapsam dışı kararlar burada **yasak**tır: model ürün kararı üretmez.
# İki ayrı liste vardır ve karıştırılmamalıdır:
#   * `DECISION_FIELDS` — **alan adı** düzeyinde yasak (gövdede bu anahtar hiç bulunamaz),
#   * `FORBIDDEN_FIELDS` — serbest metinde **terim** olarak aranan geniş küme (kolların sızıntı
#     kontrolünde kullanılır; "source"/"step" gibi kelimeler alan adı olarak meşru olabilir).
DECISION_FIELDS = ("supported", "confirmed", "rejected", "resolution", "user_decision", "decision")
FORBIDDEN_FIELDS = (*DECISION_FIELDS, "feature_plan", "cad", "fusion")

ALLOWED_CANDIDATE_KEYS = ("candidate_id", "callout", "representation", "physical", "form", "size",
                         "count", "termination", "depth", "target", "source", "provenance",
                         "uncertainty")
ALLOWED_RESPONSE_KEYS = ("schema_version", "items")


class CandidateParseError(ValueError):
    """Yanıt gövdesi sözleşmeye uymuyor. Bilinçli olarak **tamir yolu yoktur**."""


class CandidateReferenceError(ValueError):
    """Aday, gönderilmeyen bir kimliğe ya da var olmayan bir gözleme atıf yapıyor."""


# ----------------------------------------------------------------- yardımcı modeller


def _round(value: float) -> float:
    return float(round(value, 6))


class Region(BaseModel):
    """Normalize `[x0, y0, x1, y1]`, 0..1. Yalnız adres doğrulamasıdır; semantik doğruluk değildir."""

    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def _ordered(self) -> "Region":
        if not all(0.0 <= value <= 1.0 for value in (self.x0, self.y0, self.x1, self.y1)):
            raise ValueError("bölge 0..1 dışında")
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bölge boş ya da ters")
        return self

    def as_list(self) -> list[float]:
        return [_round(v) for v in (self.x0, self.y0, self.x1, self.y1)]

    def iou(self, other: "Region") -> float:
        inter_x0, inter_y0 = max(self.x0, other.x0), max(self.y0, other.y0)
        inter_x1, inter_y1 = min(self.x1, other.x1), min(self.y1, other.y1)
        if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
            return 0.0
        inter = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
        union = ((self.x1 - self.x0) * (self.y1 - self.y0) + (other.x1 - other.x0) *
                 (other.y1 - other.y0) - inter)
        return 0.0 if union <= 0 else inter / union

    def centre(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


class Num(BaseModel):
    """Bir sayısal alan: değer + birim ya da `unknown`. Tahmin yazılmaz."""

    value: float | None = None
    unit: Literal["mm", "in"] | None = None
    state: Literal["known", "unknown", "not_stated"] = "unknown"

    @model_validator(mode="after")
    def _coherent(self) -> "Num":
        if self.state == "known":
            if self.value is None or self.unit is None:
                raise ValueError("state=known için value ve unit zorunlu")
        elif self.value is not None:
            raise ValueError("unknown/not_stated alanda değer taşınamaz")
        return self


class CalloutText(BaseModel):
    text: str = ""
    state: Literal["known", "unknown"] = "unknown"

    @model_validator(mode="after")
    def _coherent(self) -> "CalloutText":
        if self.state == "known" and not self.text.strip():
            raise ValueError("state=known için callout metni boş olamaz")
        return self


class RepresentationField(BaseModel):
    """Ne **çizilmiş**: circle/arc/other/unknown. Fiziksel yorum değildir."""

    kind: Literal["circle", "arc", "other", "unknown"] = "unknown"
    diameter_px: float | None = None


class PhysicalField(BaseModel):
    """Fiziksel yorum. Kanıt yoksa `unknown` kalır — çizilmiş circle bunu kanıtlamaz."""

    kind: Literal["hole", "pocket", "slot", "not_hole", "unknown"] = "unknown"
    reason: str = ""


class FormField(BaseModel):
    symbol: Literal["R", "diameter", "none", "unknown"] = "unknown"


class CountField(BaseModel):
    printed: int | None = None
    found_circles: int | None = None
    state: Literal["known", "unknown", "not_stated"] = "unknown"

    @model_validator(mode="after")
    def _coherent(self) -> "CountField":
        if self.printed is not None and self.printed < 1:
            raise ValueError("basılı count en az 1 olur")
        if self.found_circles is not None and self.found_circles < 0:
            raise ValueError("bulunan circle sayısı negatif olamaz")
        if self.state == "known" and self.printed is None:
            raise ValueError("state=known için basılı count gerekir")
        return self


class TerminationField(BaseModel):
    kind: Literal["thru", "finite", "unknown"] = "unknown"
    stated: bool = False


class DepthField(BaseModel):
    value: float | None = None
    unit: Literal["mm", "in"] | None = None
    state: Literal["known", "unknown", "not_stated"] = "not_stated"

    @model_validator(mode="after")
    def _coherent(self) -> "DepthField":
        if self.state == "known":
            if self.value is None or self.unit is None:
                raise ValueError("state=known için derinlik değeri ve birimi zorunlu")
        elif self.value is not None:
            raise ValueError("yazılı olmayan derinlik değer taşıyamaz")
        return self


class TargetField(BaseModel):
    """Callout→target bağlama: hedef bölge, ve (varsa) o bölgedeki gerçek gözlem kimliği."""

    region: Region | None = None
    observation_id: str | None = None
    state: Literal["bound", "unknown"] = "unknown"


class SourceField(BaseModel):
    image_id: str
    region: Region
    callout_region: Region | None = None


class ProvenanceField(BaseModel):
    kind: Literal["deterministic", "vlm"] = "vlm"
    method: str = ""
    source_ref: str | None = None       # kaynak dosya/sayfa izi (deterministic kolda dolar)
    notes: list[str] = Field(default_factory=list)


class UncertaintyField(BaseModel):
    """Alan bazında belirsizlik: bir alanın bilinmemesi diğerlerini silmez."""

    fields: dict[str, str] = Field(default_factory=dict)
    reason: str = ""


class Candidate(BaseModel):
    candidate_id: str
    callout: CalloutText = Field(default_factory=CalloutText)
    representation: RepresentationField = Field(default_factory=RepresentationField)
    physical: PhysicalField = Field(default_factory=PhysicalField)
    form: FormField = Field(default_factory=FormField)
    size: Num = Field(default_factory=Num)
    count: CountField = Field(default_factory=CountField)
    termination: TerminationField = Field(default_factory=TerminationField)
    depth: DepthField = Field(default_factory=DepthField)
    target: TargetField = Field(default_factory=TargetField)
    source: SourceField
    provenance: ProvenanceField = Field(default_factory=ProvenanceField)
    uncertainty: UncertaintyField = Field(default_factory=UncertaintyField)

    @field_validator("candidate_id")
    @classmethod
    def _named(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate_id boş olamaz")
        return value

    @model_validator(mode="after")
    def _no_fabricated_termination(self) -> "Candidate":
        """Yazılı derinlik yokken `finite`, derinlik varken `thru` çelişir; ikisi de reddedilir."""
        if self.termination.kind == "finite" and self.depth.state != "known":
            raise ValueError("termination=finite için yazılı derinlik gerekir")
        if self.termination.kind == "thru" and self.depth.state == "known":
            raise ValueError("termination=thru ile açıkça yazılmış derinlik birlikte olamaz")
        if self.termination.kind == "thru" and not self.termination.stated:
            raise ValueError("thru yalnız yazılı bir gösterimle iddia edilebilir (stated=True)")
        return self


class CandidateResponse(BaseModel):
    schema_version: str = CANDIDATE_SCHEMA_VERSION
    items: list[Candidate] = Field(default_factory=list)


# ----------------------------------------------------------------- model şeması


def candidate_json_schema() -> dict:
    """Modele verilen yanıt şeması: kapalı anahtarlar, alan bazında `status`, kimlik listesi yok.

    Şema **kimlik taşımaz** (hangi görselin ne olduğu, hangi gözlemin hangi hedefe ait olduğu
    yazılmaz); aynı şema V ve VE kolunda aynen kullanılır.
    """
    region = {
        "type": "object",
        "properties": {key: {"type": "number"} for key in ("x0", "y0", "x1", "y1")},
        "required": ["x0", "y0", "x1", "y1"],
        "additionalProperties": False,
    }
    def num(state_enum: list[str], state_default: str, unit: bool = True) -> dict:
        properties: dict[str, Any] = {"value": {"type": ["number", "null"]}, "state":
                                      {"enum": state_enum, "default": state_default}}
        if unit:
            properties["unit"] = {"enum": ["mm", "in", None], "default": None}
        return {"type": "object", "properties": properties, "additionalProperties": False}

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "items"],
        "properties": {
            "schema_version": {"const": CANDIDATE_SCHEMA_VERSION},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["candidate_id", "source"],
                    "properties": {
                        "candidate_id": {"type": "string",
                                         "description": "bu adaya verdiğin kısa kimlik (ör. c1)"},
                        "callout": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "text": {"type": "string",
                                         "description": "okuduğun basılı metin; okuyamadıysan boş"},
                                "state": {"enum": ["known", "unknown"], "default": "unknown"},
                            },
                        },
                        "representation": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "kind": {"enum": list(REPRESENTATION_CLASSES),
                                         "description": "çizimde ne var: circle/arc/other/unknown"},
                                "diameter_px": {"type": ["number", "null"]},
                            },
                        },
                        "physical": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "kind": {"enum": list(PHYSICAL_CLASSES),
                                         "description": ("fiziksel yorum; kanıt yoksa unknown bırak. "
                                                         "Çizilmiş bir circle tek başına hole demek değildir")},
                                "reason": {"type": "string"},
                            },
                        },
                        "form": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "symbol": {"enum": list(FORM_SYMBOLS),
                                           "description": "R ya da çap (Ø) simgesi; yoksa none/unknown"},
                            },
                        },
                        "size": num(["known", "unknown", "not_stated"], "unknown"),
                        "count": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "printed": {"type": ["integer", "null"],
                                            "description": "callout'ta yazılı adet (ör. 4xØ8)",
                                            "minimum": 1},
                                "found_circles": {"type": ["integer", "null"],
                                                  "description": "senin gördüğün circle sayısı",
                                                  "minimum": 0},
                                "state": {"enum": ["known", "unknown", "not_stated"], "default": "unknown"},
                            },
                        },
                        "termination": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "kind": {"enum": list(TERMINATIONS),
                                         "description": "thru/finite/unknown; yazılı değilse unknown"},
                                "stated": {"type": "boolean",
                                           "description": "çizimde sonlanma açıkça yazılı mı"},
                            },
                        },
                        "depth": num(["known", "unknown", "not_stated"], "not_stated"),
                        "target": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "region": {**region, "description": "callout'un gösterdiği hedef bölge"},
                                "observation_id": {"type": ["string", "null"],
                                                   "description": "hedefteki gözlem kimliği; yoksa null"},
                                "state": {"enum": ["bound", "unknown"], "default": "unknown"},
                            },
                        },
                        "source": {
                            "type": "object", "additionalProperties": False,
                            "required": ["image_id", "region"],
                            "properties": {
                                "image_id": {"type": "string",
                                             "description": "verilen görsel kimliklerinden biri"},
                                "region": region,
                                "callout_region": region,
                            },
                        },
                        "provenance": {
                            "type": "object", "additionalProperties": False,
                            "properties": {"kind": {"enum": list(PROVENANCE_KINDS)},
                                           "method": {"type": "string"},
                                           "source_ref": {"type": ["string", "null"]},
                                           "notes": {"type": "array", "items": {"type": "string"}}},
                        },
                        "uncertainty": {
                            "type": "object", "additionalProperties": False,
                            "properties": {
                                "fields": {"type": "object", "additionalProperties": {"type": "string"},
                                           "description": "alan adı -> neden belirsiz"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }


# ----------------------------------------------------------------- görev metni

TASK_INSTRUCTIONS = """\
You read ONE mechanical drawing page and report only the callouts/features you can actually see.

Report, for every dimension callout that points at a feature:
  * what is drawn there (circle / arc / other / unknown);
  * the physical meaning ONLY if the drawing states it (hole / pocket / slot / not_hole / unknown).
    A drawn circle does not by itself mean a hole: leave `physical.kind` as unknown unless the
    drawing says so (for example a section view, a note, or a depth/THRU word).
  * whether the symbol is R (radius) or Ø (diameter); do not turn one into the other;
  * the printed value and its unit (mm or in) exactly as printed;
  * the printed count (for example the 4 in "4xØ8") and, separately, how many circles you found;
  * how the feature ends: "thru" only if the drawing writes it; "finite" only if a depth is written;
    otherwise unknown;
  * the depth value if (and only if) the drawing writes one;
  * where the callout points (target region), and which image you are looking at.

Rules:
  * Never guess. If a field is not visible/stated, keep it unknown/not_stated and say why in
    `uncertainty.fields`.
  * A field you cannot read must not delete the fields you did read.
  * Use only the image ids you were given. `source.image_id` must be one of them.
  * `target.observation_id` may be null; a candidate that shows a valid region but no observation id
    is allowed.
  * Do not output CAD code, do not decide what should be modelled, do not mark anything as
    supported/confirmed/rejected. You report observations, not decisions.
  * Reply with JSON only, matching the given schema.
"""


def candidate_prompt(image_ids: list[str], *, observations: list[dict] | None = None) -> str:
    """Ortak görev prompt'u. V: observations=None, VE: gerçek gözlem tablosu eklenir.

    Fark **yalnız** gözlem girdisidir: görev metni, şema, kimlik listesi iki kolda aynıdır. Gözlem
    tablosu yalnız gerçek gözlem kimliği/metni/ilkel türü/bölgesini taşır; gold, `meaning` sonucu ya
    da deterministic karar burada **yoktur** ve gözlemlerin yanlış olabileceği açıkça yazılır.
    """
    lines = [TASK_INSTRUCTIONS, "", f"Image ids (use exactly these): {', '.join(image_ids)}", ""]
    if observations:
        lines += [
            "A first pass over the same page produced these machine observations. They can be wrong "
            "or incomplete: question them instead of trusting them. They carry no interpretation, "
            "only what was measured.",
            "",
            "observation_id | kind | text | value | unit | region(x0,y0,x1,y1 normalized)",
        ]
        for entry in observations:
            box = entry.get("region") or []
            box_text = ",".join(f"{float(v):.4f}" for v in box) if box else "-"
            lines.append(f"{entry.get('id','-')} | {entry.get('kind','-')} | "
                         f"{(entry.get('text') or '-')!s} | "
                         f"{'-' if entry.get('value') is None else entry['value']} | "
                         f"{(entry.get('unit') or '-')} | {box_text}")
        lines.append("")
    lines.append("Reply with JSON only, matching the response schema you were given.")
    return "\n".join(lines)


# ----------------------------------------------------------------- ayrıştırma / doğrulama


def parse_candidate_json(text: str) -> CandidateResponse:
    """Yanıt gövdesini **tamir etmeden** ayrıştır. Bozuksa `CandidateParseError` fırlatır."""
    if text is None or not str(text).strip():
        raise CandidateParseError("boş yanıt gövdesi")
    raw = str(text).strip()
    if raw.startswith("```"):
        raise CandidateParseError("kod bloğu içinde gövde: şema dışı sarmalayıcı kabul edilmez")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CandidateParseError(f"bozuk JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CandidateParseError("gövde nesne değil")
    unexpected = sorted(set(payload) - set(ALLOWED_RESPONSE_KEYS))
    if unexpected:
        raise CandidateParseError(f"tanımsız üst anahtar: {unexpected}")
    if payload.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        raise CandidateParseError(f"şema sürümü uyuşmuyor: {payload.get('schema_version')!r}")
    items = payload.get("items")
    if not isinstance(items, list):
        raise CandidateParseError("items liste değil")
    for item in items:
        if isinstance(item, dict):
            bad = sorted(set(item) - set(ALLOWED_CANDIDATE_KEYS))
            if bad:
                raise CandidateParseError(f"tanımsız aday anahtarı: {bad}")
            for forbidden in DECISION_FIELDS:
                if forbidden in item:
                    raise CandidateParseError(f"ürün kararı alanı yasak: {forbidden}")
    try:
        return CandidateResponse.model_validate(payload)
    except ValidationError as exc:
        raise CandidateParseError(f"şema doğrulaması düştü: {exc.errors()[:3]}") from exc


def check_candidate_references(response: CandidateResponse, sent_image_ids: list[str],
                               allowed_observation_ids: list[str] | None = None,
                               allowed_image_ids: list[str] | None = None) -> dict:
    """Kimlik/kapsam kontrolü: her gönderilen görsel için en az bir aday, bilinmeyen kimlik yok.

    Katı kapsam kuralı (001A dersi): **gönderilen her görsel** yanıtta temsil edilmeli; her görsel
    birden çok aday taşıyabilir, ama bilinmeyen bir kimliğe atıf yapılamaz. Aynı `candidate_id`'nin
    tekrarı da bir kapsam hatasıdır.

    `allowed_image_ids` kapsamdan **geniştir**: VE kolunda ham sayfa ile aynı sayfanın overlay'i iki
    ayrı görseldir, ama ikisi de aynı paftayı gösterir; bu yüzden yalnız *sayfa* kimliği kapsam
    ister, overlay kimliği atıf yapılabilir olmakla birlikte zorunlu değildir.
    """
    sent = list(dict.fromkeys(sent_image_ids))
    allowed = list(dict.fromkeys(allowed_image_ids or sent))
    seen_ids: list[str] = []
    duplicates: list[str] = []
    unknown_images: list[str] = []
    unknown_observations: list[str] = []
    for item in response.items:
        if item.candidate_id in seen_ids:
            duplicates.append(item.candidate_id)
        seen_ids.append(item.candidate_id)
        if item.source.image_id not in allowed:
            unknown_images.append(item.source.image_id)
        observation_id = item.target.observation_id
        if observation_id is not None and allowed_observation_ids is not None \
                and observation_id not in allowed_observation_ids:
            unknown_observations.append(observation_id)
    covered = sorted({item.source.image_id for item in response.items if item.source.image_id in sent})
    missing = [image_id for image_id in sent if image_id not in covered]
    ok = not (duplicates or unknown_images or unknown_observations or missing)
    return {
        "ok": ok,
        "coverage": {"sent": sent, "covered": covered, "missing": missing, "exact": not missing},
        "allowed_image_ids": allowed,
        "duplicate_candidate_ids": sorted(set(duplicates)),
        "unknown_image_ids": sorted(set(unknown_images)),
        "unknown_observation_ids": sorted(set(unknown_observations)),
        "candidates": len(response.items),
    }


def candidate_fingerprint(response: CandidateResponse) -> str:
    """Aday listesinin içerik hash'i (rapor/kimlik için; sıra normalize edilir)."""
    payload = json.dumps([item.model_dump(mode="json") for item in response.items],
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def numeric_tolerance(value: float, *, relative: float = 0.02, absolute: float = 0.05) -> float:
    """Sayısal karşılaştırma toleransı: `max(mutlak, göreli * değer)`. Final öncesi sabitlenir."""
    return max(absolute, relative * abs(value))


def regions_match(first: Region | None, second: Region | None, *, iou_threshold: float = 0.15,
                  centre_tolerance: float = 0.05) -> bool:
    """Bölge eşleşmesi: ya yeterli IoU ya da merkezlerin normalize yakınlığı."""
    if first is None or second is None:
        return False
    if first.iou(second) >= iou_threshold:
        return True
    (fx, fy), (sx, sy) = first.centre(), second.centre()
    return math.dist((fx, fy), (sx, sy)) <= centre_tolerance


__all__ = [
    "ALLOWED_CANDIDATE_KEYS", "ALLOWED_RESPONSE_KEYS", "CANDIDATE_READER_VERSION",
    "CANDIDATE_RESPONSE_SCHEMA", "CANDIDATE_SCHEMA_VERSION", "CalloutText", "Candidate",
    "CandidateParseError", "CandidateReferenceError", "CandidateResponse", "CountField",
    "DepthField", "FIELD_STATES", "FORBIDDEN_FIELDS", "FORM_SYMBOLS", "FormField", "Num",
    "PHYSICAL_CLASSES", "PROVENANCE_KINDS", "PhysicalField", "ProvenanceField", "REPRESENTATION_CLASSES",
    "Region", "RepresentationField", "SourceField", "TERMINATIONS", "TASK_INSTRUCTIONS", "TargetField",
    "TerminationField", "UNITS", "UncertaintyField", "candidate_fingerprint", "candidate_json_schema",
    "candidate_prompt", "check_candidate_references", "numeric_tolerance", "parse_candidate_json",
    "regions_match",
]
