"""SEMREAD-001B — **dar** semantic aday sözleşmesi (ayrı sürüm).

Sürüm **/3** (SEMREAD-001D, PLAN-14 §3/§4/§6/§61): `CANDIDATE_READER_VERSION` de `/3`'e çıkar.
Bump'ın anlamı:

  * **semantic-empty aday geçersiz**: yalnız kanıt/bölge alanları taşıyan aday bu sözleşmede yoktur
    (wire'da `schema_semantic_empty` ile reddedilir — §5; sessiz tamir yok);
  * **semantic claim ≠ evidence-only**: ayrımın tek kaynağı yine `semantic_claim_flags` /
    `candidate_has_semantic_claim` / `evidence_flags`;
  * ortak görev metni **semantic-first**: önce basılı semantik olgu, sonra aday; bölge tek başına
    aday değildir, makine gözlem satırı semantik claim değildir (§6/§7);
  * **no-guess korunur**: okunamayan olgu için aday üretilmez, semantik-içerik kapısını doyurmak
    için olgu uydurulmaz (§8);
  * şema, aynı zorunluluğu **item açıklamasında** modelin gördüğü sözleşmeye taşır (§4);
    yapısal zorlama (`anyOf`) bilinçli olarak **eklenmedi** (§5: backend desteği kanıtlanmadan
    production şeması karmaşıklaştırılmaz).

Sürüm **/2** (SEMREAD-001C P1, PLAN-12 §15): bölge alanları şemada `minimum: 0, maximum: 1`
taşır ve ortak görev metni normalize koordinat kuralını açıkça öğretir; koordinat konvansiyonu
V ve VE kollarında **aynı** metinden ve **aynı** şema nesnesinden gelir (kopya literal yok).
Parser bu kuralı sessizce "tamir" etmez: 0..1 dışındaki bölge reddedilir.

Sürüm **/2** notları (SEMREAD-001C):
  * P1 (§15): region min/max + normalize kural; V/VE aynı metin, aynı şema nesnesi.
  * P2 (§16): opsiyonel alanlar yalnız varsayılan (`unknown`/`not_stated`) kalacaksa
    **atlanabilir**; `provenance` **model çıktısında yoktur** — harness parse sonrası enjekte
    eder (§16.2). `source.image_id` bilinçli olarak **kaldı**: VE overlay atfı gerçek kanıttır
    (§16.3 değerlendirmesi; kaldırmak kapsam kontrolünü karmaşıklaştırırdı).
  * P4 (§18): ayrıştırma hataları alt tür taşır (`kind`): `invalid_json`, `schema_error`,
    `schema_coordinate`, `schema_no_guess`.
  * 001D (PLAN-14 §3/§5): "semantic claim ≠ evidence-only" ayrımı **tek kaynak** fonksiyonlarla
    (`semantic_claim_flags` / `candidate_has_semantic_claim` / `evidence_flags`) tanımlanır ve wire
    sınırında uygulanır: yalnız kanıt/bölge alanları taşıyan aday `schema_semantic_empty` alt
    türüyle reddedilir (sessiz tamir yok). Şema/reader sürüm bump'ı 001D kimlik commit'indedir.

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
7. **Semantik içerik zorunlu (001D)**: yalnız kanıt/bölge alanları taşıyan aday bu sözleşmede
   geçerli değildir. Tanımın tek kaynağı `semantic_claim_flags`; boş `items` listesi ise geçerli bir
   **abstention** olarak kalır (dev sayfalarda içerik kapısı ayrıca aranır — PLAN-14 §7/§27).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

CANDIDATE_SCHEMA_VERSION = "semread-candidates/3"
CANDIDATE_READER_VERSION = "semread-candidate-reader/3"
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
                         "count", "termination", "depth", "target", "source", "uncertainty")
ALLOWED_RESPONSE_KEYS = ("schema_version", "items")

# PLAN-13 §5 — yapısal anti-loop: yanıt listesi sınırlıdır (pilot limiti; ürünün nihai kapasitesi
# değil). Şema ve ayrıştırıcı **aynı sözü verir**: 32'nin üzeri ne sessizce kırpılır ne tamir edilir
# (silent dedupe / truncated JSON repair yasak) — sözleşme dışı gövde `CandidateParseError` olur.
MAX_ITEMS = 32

# 001D §3 (PLAN-14 "semantic claim ≠ evidence-only") — **tek kaynak** ayrım. Bir aday ancak
# aşağıdaki kaynaklardan en az birini taşıyorsa semantik içeriklidir; liste kapalıdır ve parser,
# dev raporu, final değerlendirici ile testler aynı tanımı reuse eder (kopya mantık yasak).
# Geri kalan alanlar (representation, found_circles, target.state/observation_id, source.region,
# uncertainty) kanıt/bağlama metriğidir: tek başına adayı geçerli saymaz — bu ayrım gate gaming'i
# önler (yalnız gözlem satırı kopyalayan aday semantik sayılmaz).
SEMANTIC_CLAIM_SOURCES = ("callout_text", "form_symbol", "size", "count_printed", "termination",
                          "depth", "physical")
EVIDENCE_SOURCES = ("representation", "found_circles", "target_state", "target_observation_id",
                    "source_region", "uncertainty")


class CandidateParseError(ValueError):
    """Yanıt gövdesi sözleşmeye uymuyor. Bilinçli olarak **tamir yolu yoktur**.

    `kind` (P4 §18) hatanın alt türünü taşır: `invalid_json` (JSON katmanı), `schema_error`
    (sözleşme/doğrulama), `schema_coordinate` (0..1 dışı bölge), `schema_no_guess`
    (kanıtsız termination iddiası), `schema_semantic_empty` (001D §5: hiçbir semantic claim
    taşımayan aday). Taşıma/sınıflandırma bu türü **okur**, mesajı ayrıştırmaz.
    """

    def __init__(self, message: str, *, kind: str = "invalid_json") -> None:
        super().__init__(message)
        self.kind = kind


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
    # PLAN-13 §5: üst sınır şemada ve ayrıştırıcıda ortaktır (`MAX_ITEMS`).
    items: list[Candidate] = Field(default_factory=list, max_length=MAX_ITEMS)


# ----------------------------------------------------------------- model şeması

# Modelin gördüğü şemada **kanıt-yalnız** alanların işareti (001D §4/§7): bu alanların varlığı adayı
# geçerli kılmaz. Metin tek yerde durur, alan açıklamaları buradan türetilir (kopya literal yok).
EVIDENCE_ONLY_NOTE = " Evidence only: on its own this is not a semantic claim."

# Modelin gördüğü asgari sözleşme: parser'ın `schema_semantic_empty` reddiyle **aynı yönü** gösterir
# (§4). Yapısal zorlama (`anyOf`) bilinçli olarak eklenmez (§5).
SEMANTIC_CONTENT_REQUIREMENT = (
    "A candidate must contain at least one semantic claim. A region, representation, "
    "found-circle count, target binding, observation id or uncertainty alone is not a semantic "
    "claim.")


def candidate_json_schema() -> dict:
    """Modele verilen yanıt şeması: kapalı anahtarlar, alan bazında `status`, kimlik listesi yok.

    Şema **kimlik taşımaz** (hangi görselin ne olduğu, hangi gözlemin hangi hedefe ait olduğu
    yazılmaz); aynı şema V ve VE kolunda aynen kullanılır.
    """
    # Bölge sözleşmesi **tek** yerde tanımlanır; source.region, source.callout_region ve
    # target.region aynı nesneden türetilir (kopya literal yok) — koordinat kuralı üçünde de aynı.
    region = {
        "type": "object",
        "description": ("Normalized page coordinates in [0,1]. (0,0)=top-left, "
                        "(1,1)=bottom-right. Never use pixel coordinates."
                        + EVIDENCE_ONLY_NOTE),
        "properties": {key: {"type": "number", "minimum": 0.0, "maximum": 1.0}
                       for key in ("x0", "y0", "x1", "y1")},
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
                "maxItems": MAX_ITEMS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    # §4: parser'ın semantik-içerik reddiyle aynı yönü gösteren asgari sözleşme.
                    "description": SEMANTIC_CONTENT_REQUIREMENT,
                    "required": ["candidate_id", "source"],
                    "properties": {
                        "candidate_id": {"type": "string", "minLength": 1,
                                         "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]*$",
                                         "description": ("bu adaya verdiğin BENZERSİZ kısa kimlik "
                                                         "(ör. c1, c2); boş olamaz, '<' ile başlayamaz")},
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
                                         "description": ("çizimde ne var: circle/arc/other/unknown"
                                                         + EVIDENCE_ONLY_NOTE)},
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
                                                  "description": ("senin gördüğün circle sayısı"
                                                                  + EVIDENCE_ONLY_NOTE),
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
                                "region": {**region,
                                           "description": region["description"]
                                           + " Target region the callout points at."},
                                "observation_id": {"type": ["string", "null"],
                                                   "description": ("hedefteki gözlem kimliği; "
                                                                   "yoksa null"
                                                                   + EVIDENCE_ONLY_NOTE)},
                                "state": {"enum": ["bound", "unknown"], "default": "unknown",
                                          "description": ("callout→hedef bağlaması"
                                                          + EVIDENCE_ONLY_NOTE)},
                            },
                        },
                        "source": {
                            "type": "object", "additionalProperties": False,
                            "required": ["image_id", "region"],
                            "properties": {
                                # §16.3 değerlendirmesi: bilinçli olarak **kaldı** — VE kolunda
                                # overlay atfı gerçek kanıttır (ham sayfa mı, overlay mi?) ve kapsam
                                # kontrolü buna dayanır; deterministik enjeksiyon bu bilgiyi kaybeder.
                                "image_id": {"type": "string",
                                             "description": "verilen görsel kimliklerinden biri"},
                                "region": region,
                                "callout_region": region,
                            },
                        },
                        "uncertainty": {
                            "type": "object", "additionalProperties": False,
                            "description": "belirsizlik notu" + EVIDENCE_ONLY_NOTE,
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
You read ONE mechanical drawing page and report only the callouts/features you can actually read.

First identify a printed semantic fact. Only then create a candidate.
A region alone is not a candidate.
A machine observation row is not a semantic claim.
Do not emit a candidate unless it contains at least one semantic claim.

A semantic claim is something the drawing prints or states. Examples:
  * printed callout text;
  * an R (radius) or a Ø (diameter) symbol;
  * a printed size;
  * a printed count (for example the 4 in "4xØ8");
  * an explicit THRU;
  * an explicit finite depth;
  * a physical meaning the drawing explicitly supports.

These are evidence only. On their own they never make a candidate:
  * a circle/arc representation;
  * a found-circle count;
  * a target box;
  * an observation id;
  * a source region;
  * an uncertainty note.

If you cannot read at least one semantic fact, emit no candidate for that feature.
Do not invent a semantic fact merely to satisfy the semantic-content requirement.

Report, for every dimension callout that points at a feature:
  * the printed callout text exactly as printed, if you can read it;
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

Coordinate convention (applies to every region field: source.region, source.callout_region,
target.region):
  * All regions use normalized page coordinates: x0,y0,x1,y1 in [0,1].
    Top-left is (0,0), bottom-right is (1,1). Never return pixel coordinates.
  * Example only for coordinate format: {"x0":0.10,"y0":0.20,"x1":0.30,"y1":0.40}

Rules:
  * Never guess. If a field is not visible/stated, keep it unknown/not_stated and say why in
    `uncertainty.fields`.
  * Omit optional fields that would only contain default unknown/not_stated values.
  * A field you cannot read must not delete the fields you did read.
  * Use only the image ids you were given. `source.image_id` must be one of them.
  * `target.observation_id` may be null; a candidate that shows a valid region but no observation id
    is allowed.
  * Emit at most one candidate for the same visible callout→target pair.
  * Do not repeat a candidate with a new candidate_id.
  * When all supported visible callouts are reported, close the items array.
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
            "Observations are evidence, not candidate seeds.",
            "Do not create one candidate per observation row.",
            "Use an observation only if it helps support a semantic claim.",
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


# ----------------------------------------------------------------- semantik içerik (001D)


def _block(candidate: Any, name: str) -> Any:
    """Alt blok okuyucu: `Candidate` nesnesi ya da düz sözlük (kayıtlı `response-parsed.json`).

    Tanım hem parse edilmiş nesnelerde hem depodan okunan JSON sözlüklerinde çalışır; dev raporu ve
    final değerlendirici aynı fonksiyonu sözlüklerle çağırır (kopya semantic-content mantığı yok).
    """
    if isinstance(candidate, Mapping):
        return candidate.get(name)
    return getattr(candidate, name, None)


def _value(block: Any, name: str, default: Any = None) -> Any:
    """Blok alanı: sözlükte `.get`, modelde `getattr`; alan/blok yoksa ya da `None` ise `default`."""
    if block is None:
        return default
    value = block.get(name) if isinstance(block, Mapping) else getattr(block, name, None)
    return default if value is None else value


def semantic_claim_flags(candidate: "Candidate | Mapping[str, Any]") -> dict[str, bool]:
    """Adayın taşıdığı **semantic claim** kaynakları — kapalı bayrak sözlüğü (001D §3, tek kaynak).

    Kural: **semantic claim ≠ evidence-only**. Bayraklardan en az biri true ise aday semantik
    içeriklidir. Şema tutarlılık kuralları burada tekrarlanmaz (onlar `Candidate` validator'ında;
    ör. `thru` için `stated=True` şartı): bayraklar yalnız *ne iddia edildiğini* sayar.

      * `callout_text`  — callout metni dolu (şema `state=known` iken boş metni zaten reddeder);
      * `form_symbol`   — `form.symbol` R ya da çap (Ø); `none`/`unknown` sayılmaz;
      * `size`          — `size.state == known` (yazılı ölçü);
      * `count_printed` — `count.printed` var (yazılı adet, ör. `4xØ8`'in 4'ü);
      * `termination`   — `thru` ya da `finite` (şema `thru`yu yalnız `stated`, `finite`i yalnız
                          yazılı derinlikle kabul eder; ikisi de gerçek içerik iddiasıdır);
      * `depth`         — `depth.state == known` (yazılı derinlik);
      * `physical`      — `physical.kind != unknown` (`not_hole` dahil: "delik değil" de kanıtlı
                          bir fiziksel yorumdur).

    Girdi `Candidate` ya da düz sözlük olabilir (sözlük şema doğrulamasından geçmemişse eksik alan
    `unknown`/yok varsayılır). Anahtar sırası `SEMANTIC_CLAIM_SOURCES` ile birebir aynıdır.
    """
    callout = _block(candidate, "callout")
    form = _block(candidate, "form")
    size = _block(candidate, "size")
    count = _block(candidate, "count")
    termination = _block(candidate, "termination")
    depth = _block(candidate, "depth")
    physical = _block(candidate, "physical")
    return {
        "callout_text": bool(str(_value(callout, "text", "")).strip()),
        "form_symbol": _value(form, "symbol", "unknown") in ("R", "diameter"),
        "size": _value(size, "state", "unknown") == "known",
        "count_printed": _value(count, "printed") is not None,
        "termination": _value(termination, "kind", "unknown") in ("thru", "finite"),
        "depth": _value(depth, "state", "not_stated") == "known",
        "physical": _value(physical, "kind", "unknown") != "unknown",
    }


def candidate_has_semantic_claim(candidate: "Candidate | Mapping[str, Any]") -> bool:
    """Aday semantik içerik taşıyor mu: bayraklardan **en az biri** (001D §3/§5)."""
    return any(semantic_claim_flags(candidate).values())


def evidence_flags(candidate: "Candidate | Mapping[str, Any]") -> dict[str, bool]:
    """Semantic claim **sayılmayan** kanıt/bağlama sinyalleri (001D §3) — ayrı raporlanır.

    Bunların varlığı adayı geçerli kılmaz; yalnız yerelleştirme, gözlem-yankısı, hedef bağlama ve
    belirsizlik metriklerinin girdisidir:

      * `representation`        — çizilmiş temsil biliniyor (kind ≠ unknown; fiziksel yorum değil);
      * `found_circles`         — bulunan circle sayısı verilmiş (`count.found_circles`);
      * `target_state`          — hedef `bound` işaretli;
      * `target_observation_id` — hedefe gerçek gözlem kimliği bağlanmış;
      * `source_region`         — kaynak bölge kutusu var;
      * `uncertainty`           — belirsizlik notu/alanı var (`fields` ya da `reason`).

    Anahtar sırası `EVIDENCE_SOURCES` ile birebir aynıdır.
    """
    representation = _block(candidate, "representation")
    count = _block(candidate, "count")
    target = _block(candidate, "target")
    source = _block(candidate, "source")
    uncertainty = _block(candidate, "uncertainty")
    return {
        "representation": _value(representation, "kind", "unknown") != "unknown",
        "found_circles": _value(count, "found_circles") is not None,
        "target_state": _value(target, "state", "unknown") == "bound",
        "target_observation_id": _value(target, "observation_id") is not None,
        "source_region": _value(source, "region") is not None,
        "uncertainty": bool(_value(uncertainty, "fields", {}) or {})
        or bool(str(_value(uncertainty, "reason", "")).strip()),
    }


def _reject_semantic_empty(response: CandidateResponse) -> None:
    """001D §5/§20 — wire sınırı: semantik-içeriksiz aday **sessizce tamir edilmez**, reddedilir."""
    for item in response.items:
        if not candidate_has_semantic_claim(item):
            raise CandidateParseError(
                f"semantik-içeriksiz aday reddedildi (candidate_id={item.candidate_id!r}): callout "
                "metni, form R/Ø, ölçü, basılı adet, sonlanma, derinlik ve fiziksel yorum "
                "alanlarından hiçbiri dolu değil — yalnız kanıt/bölge alanları taşıyan aday bu "
                "sözleşmede geçerli değildir", kind="schema_semantic_empty")


# ----------------------------------------------------------------- ayrıştırma / doğrulama


def _schema_error_kind(exc: ValidationError) -> str:
    """Pydantic doğrulama hatasını alt türe çevir (P4 §18): mesaj **bizim** sabit metnimizdir."""
    blob = " ".join(str(error.get("msg", "")) for error in exc.errors())
    if "0..1 dışında" in blob or "boş ya da ters" in blob:
        return "schema_coordinate"
    if "termination" in blob:
        return "schema_no_guess"
    return "schema_error"


def parse_candidate_json(text: str) -> CandidateResponse:
    """Yanıt gövdesini **tamir etmeden** ayrıştır. Bozuksa `CandidateParseError` fırlatır.

    001D §5 akışı: JSON → yapısal doğrulama → **semantik-içerik doğrulaması** → referanslar
    (referans kontrolü çağıranda, `check_candidate_references`). Semantik-içeriksiz aday
    `schema_semantic_empty` alt türüyle reddedilir; boş `items` listesi geçerli abstention'dır.
    """
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
        raise CandidateParseError(f"tanımsız üst anahtar: {unexpected}", kind="schema_error")
    if payload.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        raise CandidateParseError(f"şema sürümü uyuşmuyor: {payload.get('schema_version')!r}",
                                  kind="schema_error")
    items = payload.get("items")
    if not isinstance(items, list):
        raise CandidateParseError("items liste değil", kind="schema_error")
    for item in items:
        if isinstance(item, dict):
            bad = sorted(set(item) - set(ALLOWED_CANDIDATE_KEYS))
            if bad:
                raise CandidateParseError(f"tanımsız aday anahtarı: {bad}", kind="schema_error")
            for forbidden in DECISION_FIELDS:
                if forbidden in item:
                    raise CandidateParseError(f"ürün kararı alanı yasak: {forbidden}",
                                              kind="schema_error")
    try:
        response = CandidateResponse.model_validate(payload)
    except ValidationError as exc:
        raise CandidateParseError(f"şema doğrulaması düştü: {exc.errors()[:3]}",
                                  kind=_schema_error_kind(exc)) from exc
    # Yapısal doğrulama geçtikten **sonra**: semantik-içerik kuralı (001D §5/§20). Sessiz tamir
    # yok — tek bir içeriksiz aday bile yanıtın tümünü reddettirir.
    _reject_semantic_empty(response)
    return response


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
    "DepthField", "EVIDENCE_ONLY_NOTE", "EVIDENCE_SOURCES", "FIELD_STATES", "FORBIDDEN_FIELDS",
    "FORM_SYMBOLS", "FormField",
    "Num", "PHYSICAL_CLASSES", "PROVENANCE_KINDS", "PhysicalField", "ProvenanceField",
    "REPRESENTATION_CLASSES", "Region", "RepresentationField", "SEMANTIC_CLAIM_SOURCES",
    "SEMANTIC_CONTENT_REQUIREMENT",
    "SourceField", "TERMINATIONS", "TASK_INSTRUCTIONS", "TargetField", "TerminationField", "UNITS",
    "UncertaintyField", "candidate_fingerprint", "candidate_has_semantic_claim",
    "candidate_json_schema", "candidate_prompt", "check_candidate_references", "evidence_flags",
    "numeric_tolerance", "parse_candidate_json", "regions_match", "semantic_claim_flags",
]
