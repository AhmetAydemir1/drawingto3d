"""Reviewable, deterministic CAD plans. No model or reference STEP is used here."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from drawingto3d.cadrun import CadFailure, run_program


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["printed", "derived", "user"]
    span_ids: list[str]
    explanation: str


class PlatePlan(BaseModel):
    """Centred rounded plate, four through holes, one centred circular blind pocket.

    Inferred symmetry is recorded as an assumption, never as a printed dimension.
    Dimensions and the source hash travel with the plan so replay is independent of a model.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    version: Literal[1] = 1
    family: Literal["plate_with_circular_pocket"] = "plate_with_circular_pocket"
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    thickness: float = Field(gt=0)
    corner_radius: float = Field(gt=0)
    hole_dx: float = Field(gt=0)
    hole_dy: float = Field(gt=0)
    hole_diameter: float = Field(gt=0)
    pocket_diameter: float = Field(gt=0)
    pocket_depth: float = Field(gt=0)
    evidence: dict[str, Evidence]
    assumptions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def geometry(self):
        if self.pocket_depth >= self.thickness:
            raise ValueError("cep derinliği kalınlıktan küçük olmalı")
        if 2 * self.corner_radius >= min(self.width, self.height):
            raise ValueError("köşe yarıçapı gövdeye sığmıyor")
        if self.pocket_diameter >= min(self.width, self.height) - 2 * self.corner_radius:
            raise ValueError("cep bu plaka ailesinin düz iç bölgesine sığmıyor")
        r = self.hole_diameter / 2
        # Signed distance to the rounded rectangle, eroded by the hole radius.
        qx = self.hole_dx / 2 - (self.width / 2 - self.corner_radius)
        qy = self.hole_dy / 2 - (self.height / 2 - self.corner_radius)
        distance = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - self.corner_radius
        if distance + r >= 0 or min(self.hole_dx, self.hole_dy) <= 2 * r:
            raise ValueError("delikler gövde dışına taşıyor veya birbirine değiyor")
        if math.hypot(self.hole_dx / 2, self.hole_dy / 2) <= r + self.pocket_diameter / 2:
            raise ValueError("cep ve köşe delikleri kesişiyor")
        if set(self.evidence) != set(PARAMETERS):
            raise ValueError("her CAD parametresi için kaynak gerekli")
        return self


PARAMETERS = ("width", "height", "thickness", "corner_radius", "hole_dx", "hole_dy",
              "hole_diameter", "pocket_diameter", "pocket_depth")


def source_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def edit_plan(plan: PlatePlan, parameters: dict) -> PlatePlan:
    if not isinstance(parameters, dict) or set(parameters) - set(PARAMETERS):
        raise ValueError("bilinmeyen CAD parametresi")
    data = plan.model_dump()
    changed = set()
    for name, raw_value in parameters.items():
        if isinstance(raw_value, bool):
            raise ValueError("parametre sayı olmalı")
        value = float(raw_value)
        if value != data[name]:
            changed.add(name)
            data[name] = value
            data["evidence"][name] = dict(kind="user", span_ids=[], explanation="Kullanıcı tarafından değiştirildi.")
    # A form sends every field, including unchanged values. Only actual overrides break
    # a derivation; changing its inputs must recompute it instead of keeping stale evidence.
    if changed & {"height", "hole_dy", "hole_dx"}:
        margin = (data["height"] - data["hole_dy"]) / 2
        for name, value in (("width", data["hole_dx"] + 2 * margin), ("corner_radius", margin)):
            if data["evidence"][name]["kind"] == "derived":
                data[name] = value
                data["evidence"][name]["explanation"] += "; kullanıcı değerleriyle yeniden hesaplandı"
    if changed:
        note = "Kullanıcı düzeltmeleri uygulandı; ilk önerinin çizimle eşleşmesi değiştirilen ölçüler için geçerli değildir."
        if note not in data["assumptions"]:
            data["assumptions"].append(note)
    return PlatePlan.model_validate(data)


def compile_plan(plan: PlatePlan) -> str:
    """Only numeric literals reach the CAD process; the plan contains no executable expressions."""
    return (
        f"solid = geo.plate({plan.width!r}, {plan.height!r}, {plan.thickness!r}, {plan.corner_radius!r})\n"
        f"solid = geo.holes(solid, geo.rect_points({plan.hole_dx!r}, {plan.hole_dy!r}), {plan.hole_diameter!r})\n"
        f"solid = geo.holes(solid, [(0, 0)], {plan.pocket_diameter!r}, depth={plan.pocket_depth!r})\n"
    )


def check_plan(plan: PlatePlan, facts: dict) -> dict:
    """Compare geometry, including every cylinder's position and depth, with the plan."""
    t, r = plan.thickness, plan.corner_radius
    expected_volume = ((plan.width * plan.height - (4 - math.pi) * r**2) * t
                       - math.pi * (plan.hole_diameter / 2)**2 * 4 * t
                       - math.pi * (plan.pocket_diameter / 2)**2 * plan.pocket_depth)
    cylinders = [[plan.hole_diameter / 2, x * plan.hole_dx / 2, y * plan.hole_dy / 2, 0, t]
                 for x in (-1, 1) for y in (-1, 1)]
    cylinders += [[r, x * (plan.width / 2 - r), y * (plan.height / 2 - r), 0, t]
                  for x in (-1, 1) for y in (-1, 1)]
    cylinders += [[plan.pocket_diameter / 2, 0, 0, t - plan.pocket_depth, t]]
    remaining = list(facts.get("cylinders", []))
    features_ok = True
    for expected in cylinders:
        match = next((i for i, got in enumerate(remaining)
                      if len(got) == 5 and max(abs(a - b) for a, b in zip(got, expected)) < 1e-4), None)
        if match is None:
            features_ok = False
        else:
            remaining.pop(match)
    checks = {
        "valid_solid": facts.get("valid") is True and facts.get("solids") == 1,
        "dimensions": len(facts.get("size", [])) == 3 and all(
            abs(a - b) < 1e-4 for a, b in zip(facts["size"], [plan.width, plan.height, t])),
        "volume": math.isclose(facts.get("volume", -1), expected_volume, rel_tol=1e-7, abs_tol=1e-4),
        "feature_positions_and_depths": features_ok and not remaining,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "expected_volume_mm3": expected_volume, "assumptions": plan.assumptions,
            "scope": "CAD geometry matches the proposed plan; drawing assumptions still need review."}


def build_plan(plan: PlatePlan, drawing: str | Path, folder: str | Path) -> tuple[Path, Path]:
    # Revalidate even plans constructed with model_copy(update=...).
    plan = PlatePlan.model_validate(plan.model_dump())
    if source_hash(drawing) != plan.source_sha256:
        raise ValueError("plan başka bir çizime ait; kaynak özeti uyuşmuyor")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    code = compile_plan(plan)
    step, stl = run_program(code, folder)
    facts = json.loads((folder / "geometry.json").read_text())
    audit = check_plan(plan, facts)
    (folder / "plan-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if not audit["passed"]:
        raise CadFailure("katı CAD planıyla uyuşmuyor: " + str(audit["checks"]), code)
    return step, stl
