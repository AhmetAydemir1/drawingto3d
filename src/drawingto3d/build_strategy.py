"""G12.2 — oluşturma biçimi (build strategy): öneri + tazeleme; saf modül (PLAN-25 §33–§35).

Strateji bir KULLANICI kararıdır (§32): bu modül yalnız *öneri* üretir ve kaydın kendi verisinden
türeyen bir parmak izi hesaplar; kalıcılık `GuidedStore.set_strategy` yolundan geçer, anahtar ve
geometri sürümü sunucuda çivilenir (§36). Modül dosya/ağ/model okumaz ve öneri kanıtına vaka
kimliği, dosya adı, özet (digest), referans ya da beklenen ölçü koymaz (§34).

Sözleşme:

```text
strategy_key(record)   → onayın bağlandığı parmak izi (kaynak + geometri sürümü + profil + kontur + görüş)
strategy_state(record) → missing | stale | current
propose_strategies(record) → [BuildStrategyProposal]   (kanıtlı, sıralı)
```

`propose_strategies` bir *öneridir*: hiçbir şeyi kaydetmez. Daire profiline yüksek güvenli extrude
önerilmez (§35) — kazara disk, açık onay olmadan doğmaz.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from drawingto3d import callout_models, contour_audit

KINDS = ("extrude_profile", "revolve_profile", "multi_view_composite", "unsupported")

STRATEGY_LABEL = {
    "extrude_profile": "Sabit kalınlıklı profili uzat",
    "revolve_profile": "Bir kesiti eksen etrafında döndür",
    "multi_view_composite": "Birden fazla görünüşü birlikte kullan",
    "unsupported": "Bu sürümde desteklenmiyor",
}
"""PLAN-25 §42'nin kullanıcı dili; teknik adlar yalnız katlanmış kanıtta görünür."""

StrategyKind = Literal["extrude_profile", "revolve_profile", "multi_view_composite", "unsupported"]


class BuildStrategyDecision(BaseModel):
    """Seçilmiş oluşturma biçimi ve bağlandığı okumanın parmak izi (PLAN-25 §31)."""

    model_config = ConfigDict(extra="forbid")
    kind: StrategyKind
    primary_view_id: str | None = None
    section_view_id: str | None = None
    axis: Literal["X", "Y", "Z"] | None = None
    geometry_version: int
    strategy_key: str
    evidence: list[dict] = Field(default_factory=list)


class BuildStrategyProposal(BaseModel):
    """Bir aday öneri: ne, neden, hangi kanıtla — ve ne kadar güvenle (PLAN-25 §33/§34)."""

    model_config = ConfigDict(extra="forbid")
    kind: StrategyKind
    label: str
    confidence: Literal["high", "low", "none"]
    status: Literal["candidate", "capability_pending"]
    reasons: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)


def strategy_key(record: dict, decisions: dict | None = None) -> str:
    """Onayın bağlandığı parmak izi.

    Kaydın kendi geometri parmak izi kullanılır (PLAN-20 §6.4): kaynak + geometri sürümü + seçili
    profil + kontur düzeltmesi + görüş kararı. Böylece profil değişince, kontur düzeltilince, görüş
    yeniden onaylanınca ya da okuma yeni bir sürüme geçince anahtar değişir (§37) — kalınlık gibi
    ilgisiz bir düzenleme anahtarı kıpırdatmaz.
    """
    return callout_models.geometry_key(record, decisions)


def strategy_state(record: dict) -> str:
    """`missing` / `stale` / `current` — depolanan onay, bugünkü okumayla karşılaştırılır."""
    stored = (record.get("decisions") or {}).get("build_strategy")
    if not stored:
        return "missing"
    return "current" if stored.get("strategy_key") == strategy_key(record) else "stale"


def strategy_of(record: dict) -> dict | None:
    stored = (record.get("decisions") or {}).get("build_strategy")
    return dict(stored) if isinstance(stored, dict) else None


STRATEGY_CATEGORY = {"missing": "missing_build_strategy", "stale": "stale_build_strategy"}
"""PLAN-25 §41: the readiness category each strategy state reports under."""


def strategy_questions(record: dict) -> list[str]:
    """The strategy gate in the user's own words — ONE rule for the build and for readiness.

    `make_plan` refuses with these sentences and `build_readiness` asks them as checklist items, so the
    checklist and the build can never disagree about what is still missing (PLAN-25 §38/§41).
    """
    decisions = record.get("decisions") or {}
    state = strategy_state(record)
    if state == "missing":
        return ["Parçanın ana oluşturma biçimini seçin (profil uzatma / döndürme / çok görünüş) — "
                "üretim kendiliğinden bir biçim varsaymaz."]
    if state == "stale":
        return ["Seçilen oluşturma biçiminin onayı güncel değil (profil, kontur, görüş ya da okuma "
                "değişti); yeniden onaylayın."]
    kind = (decisions.get("build_strategy") or {}).get("kind")
    if kind in ("unsupported", "revolve_profile", "multi_view_composite"):
        return [f"Seçilen oluşturma biçimi bu sürümde uygulanamıyor: "
                f"{STRATEGY_LABEL.get(kind, kind)}."]
    return []


def strategy_category(record: dict) -> str | None:
    """Which readiness category this record's strategy reports under, if it reports one at all."""
    state = strategy_state(record)
    if state != "current":
        return STRATEGY_CATEGORY[state]
    decisions = record.get("decisions") or {}
    kind = (decisions.get("build_strategy") or {}).get("kind")
    return "unsupported_build_strategy" if kind and strategy_questions(record) else None


def _selected_profile(record: dict) -> dict | None:
    decisions = record.get("decisions") or {}
    profile_id = decisions.get("profile_id")
    return next((row for row in (record.get("options") or {}).get("profiles") or []
                 if row.get("id") == profile_id), None)


def _closure_evidence(profile: dict) -> dict:
    """Seçilen konturun kapanışı — sayısal, kaydın kendi geometrisinden."""
    if profile.get("kind") == "circle":
        return {"kind": "profile_closure", "detail": "seçilen profil tek daire (kapalı)",
                "closed": True, "circle": True}
    audit = contour_audit.audit_contour(profile.get("edges") or [])
    issues = audit.get("issues") or []
    return {"kind": "profile_closure",
            "detail": "seçilen kontur kapalı" if audit.get("ok") else
                      f"seçilen kontur kapalı değil ({len(issues)} sorun)",
            "closed": bool(audit.get("ok")), "circle": False}


def _thickness_evidence(record: dict) -> dict | None:
    value = (record.get("decisions") or {}).get("thickness")
    if not value:
        return None
    return {"kind": "thickness", "detail": "sabit kalınlık kullanıcı tarafından girildi",
            "value": float(value)}


def _view_evidence(record: dict) -> list[dict]:
    """Onaylanmış görüş ve okumanın kendi çerçeve/eksen bilgisi — karar değil, gözlem."""
    decisions = record.get("decisions") or {}
    rows: list[dict] = []
    view = decisions.get("view")
    if view:
        rows.append({"kind": "view_confirmed", "detail": "görüş yönü kullanıcı tarafından onaylandı",
                     "x_page": view.get("x_page"), "y_page": view.get("y_page")})
    frame = (record.get("options") or {}).get("sheet_frame") or {}
    if frame.get("found"):
        rows.append({"kind": "sheet_frame", "detail": "pafta çerçevesi okundu",
                     "aligned": frame.get("aligned") is not False,
                     "rotation": frame.get("rotation") or 0})
    return rows


def propose_strategies(record: dict) -> list[BuildStrategyProposal]:
    """Kanıta dayalı öneriler — sıralı, hiçbir şeyi kaydetmeyen (PLAN-25 §33–§35)."""
    decisions = record.get("decisions") or {}
    profile = _selected_profile(record)
    if profile is None:
        return []
    closure_row = _closure_evidence(profile)
    thickness_row = _thickness_evidence(record)
    view_rows = _view_evidence(record)
    evidence = ([closure_row] + ([thickness_row] if thickness_row else []) + view_rows)
    closure = bool(closure_row["closed"])
    thickness = thickness_row is not None
    proposals: list[BuildStrategyProposal] = []
    if profile.get("kind") == "circle":
        # §35: daire profili kazara disk olmasın — öneri görünür, ama güven "low"; kullanıcı açıkça seçer.
        proposals.append(BuildStrategyProposal(
            kind="extrude_profile", label=STRATEGY_LABEL["extrude_profile"], confidence="low", status="candidate",
            reasons=["daire profil: silindir/disk ayrımı yalnız kullanıcı onayıyla doğar"],
            evidence=evidence))
    else:
        strong = closure and thickness
        proposals.append(BuildStrategyProposal(
            kind="extrude_profile", label=STRATEGY_LABEL["extrude_profile"],
            confidence="high" if strong else "low", status="candidate",
            reasons=([] if strong else [("kontur kapalı değil" if not closure else "sabit kalınlık girilmedi")]),
            evidence=evidence))
    proposals.append(BuildStrategyProposal(
        kind="revolve_profile", label=STRATEGY_LABEL["revolve_profile"], confidence="none",
        status="capability_pending", reasons=["eksen/kesit geometrisi bu sürümde kurulmuyor (G12.6)"],
        evidence=[closure_row]))
    proposals.append(BuildStrategyProposal(
        kind="multi_view_composite", label=STRATEGY_LABEL["multi_view_composite"], confidence="none",
        status="capability_pending", reasons=["görünüş grafiği bu sürümde kurulmuyor (G12.7)"],
        evidence=_view_evidence(record)))
    return proposals


def decision_for(record: dict, decisions: dict, kind: str, *, payload: dict | None = None) -> dict:
    """Sunucunun çivilediği karar: anahtar ve geometri sürümü istemciden DEĞİL, kayıttan gelir (§36).

    Öneri kanıtı da burada yeniden üretilir; istemcinin gönderdiği `strategy_key`,
    `geometry_version` ve `evidence` alanları yok sayılır (kopyalanmaz, doğrulanmaz, sessizce
    düzeltilmez: hiç okunmazlar).
    """
    payload = payload or {}
    if kind not in KINDS:
        raise ValueError(f"oluşturma biçimi tanınmıyor: {kind!r} (izinli: {', '.join(KINDS)})")
    matching = next((row for row in propose_strategies({**record, "decisions": decisions})
                     if row.kind == kind), None)
    return BuildStrategyDecision(
        kind=kind,
        primary_view_id=payload.get("primary_view_id"),
        section_view_id=payload.get("section_view_id"),
        axis=payload.get("axis"),
        geometry_version=int(record.get("geometry_version") or 1),
        strategy_key=strategy_key(record, decisions),
        evidence=list(matching.evidence) if matching else [],
    ).model_dump(mode="json")


__all__ = ["KINDS", "STRATEGY_LABEL", "BuildStrategyDecision", "BuildStrategyProposal",
           "decision_for", "propose_strategies", "strategy_key", "strategy_of", "strategy_state"]
