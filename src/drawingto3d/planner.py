"""A local model's answer to "which operations does this sheet support?", kept as a plan.

The reading chain (`observe` -> `bind` -> `meaning`) produces *cited* observations; the model's job
is to choose the operations that turn them into a solid and to cite the spans it used. Its answer is
accepted only as a `GeneralPlan`, judged by the compiler's own rules — the schema, the closed-profile
check, the expression vocabulary and the CAD audit. A candidate that fails them is recorded as failed
with the reason attached; nothing here repairs an answer by hand, and nothing here gives the model the
reference STEP, the correct plan, the file name or the part family.

Two refusals are worth naming because they are the difference between a plan and a guess:

* a `printed` parameter must cite a span id that exists in the evidence the model was shown —
  a citation the sheet does not carry is a fabrication, not a reading;
* the plan's `source` identity is the harness's, never the model's — a model that volunteers one
  has it replaced by the run's and the fact recorded, because the file name would otherwise be an
  answer cue and discarding the whole answer would report a failure the model did not make.
"""

from __future__ import annotations

import json
import re
import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from drawingto3d.errors import UnavailableModel
from drawingto3d.general import GeneralPlan, SourceRef, compile_general, evaluate_parameters

EVIDENCE_VERSION = 1
PROMPT_VERSION = "general-plan-v1"
SCHEMA_VERSION = "GeneralPlan v1"

# A small model answers in prose around the JSON it was asked for; take the outermost object.
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

PLAN_SCHEMA_HINT = """\
Plan JSON, exactly these keys: version, unit, parameters, sketches, operations, result, assumptions,
expect (optional). Do not send any other key.

parameters: name -> object with exactly one of value/expr plus unit, source, span_ids, explanation.
  unit is "mm" or "in" for lengths, "deg" for angles, "count" for whole numbers.
  source "printed"  = the number is printed on the sheet -> give value AND span_ids (the cited ids) AND a
                      short explanation.
  source "derived"  = expr, arithmetic over other parameter names (+ - * / ** sqrt abs min max),
                      with unit "mm" or "deg"; no span_ids needed.
  source "assumed"  = a convention no number on the sheet states -> give value, explanation and
                      repeat it as a sentence in assumptions.
  A sheet value in inches stays value + unit "in"; the compiler converts it.

sketches: name -> {plane: "XY"|"XZ"|"YZ", offset: expression, entities: [...]}.
  entity line   = {"type":"line","start":[expr_x,expr_y],"end":[expr_x,expr_y]}
  entity arc    = {"type":"arc","center":[expr_x,expr_y],"radius":expr,"start_degrees":number,"end_degrees":number}
  entity circle = {"type":"circle","center":[expr_x,expr_y],"radius":expr}
  A profile is one circle, or a closed chain of lines and arcs whose ends meet in order.
  Coordinates are expressions over the parameters, in the plane's local x/y, centred on the origin
  unless the profile is drawn elsewhere.

operations: an ordered list; each entry has op, id, output, and:
  extrude  {"op":"extrude","id":..,"output":..,"sketch":..,"distance":expr}
  revolve  {"op":"revolve","id":..,"output":..,"sketch":..,"angle":expr}
  repeat   {"op":"repeat","id":..,"output":..,"input":..,"linear":{"x_pitch":expr,"x_count":int,
            "y_pitch":expr,"y_count":int}}   or   "circular":{"axis":"X"|"Y"|"Z","count":int,"span_degrees":number}
  cut      {"op":"cut","id":..,"output":..,"target":..,"tool":..}
  fuse     {"op":"fuse","id":..,"output":..,"inputs":[..,..]}
  output names a body, one per operation; a cut replaces its target; a repeat copies its input.
  Sketches cut material when they are the tool of a "cut" operation — extrude the tool first.

result: the name of the body that is the finished part.
"""


class PlanCandidate(BaseModel):
    """One model answer about one sheet, with everything a run record has to be able to cite."""

    version: int = 1
    prompt_version: str = PROMPT_VERSION
    evidence_version: int = EVIDENCE_VERSION
    evidence_kind: Literal["readings", "verified"] = "readings"
    settings: dict = Field(default_factory=dict)
    model_info: dict = Field(default_factory=dict)
    source_ref: str = ""
    status: Literal["proposed", "invalid", "unsupported", "unavailable"] = "unavailable"
    plan: GeneralPlan | None = None
    answer: str = ""
    answer_truncated: bool = False
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)
    citations: dict = Field(default_factory=dict)
    resolved_parameters: dict = Field(default_factory=dict)
    stats: dict = Field(default_factory=dict)
    seconds: float = 0.0

    def as_record(self) -> dict:
        """The run record's view: the plan itself is written once, as an artifact."""
        data = self.model_dump(mode="json")
        data["plan"] = None if self.plan is None else {"parameters": list(self.plan.parameters), "operations":
                                                       [operation.op for operation in self.plan.operations]}
        return data


def plan_prompt(evidence: dict, notes: list[str] | None = None) -> str:
    """The whole question: the sheet's cited readings, and what a plan for them looks like.

    Deliberately absent: the file name, the number of parts this project has seen, any example
    plan, and any reference geometry. A plan has to be reachable from the readings alone.
    """
    lines = [
        "You are the CAD planner. Below are measured, cited readings from ONE engineering drawing.",
        "Choose the CAD operations that build the part the readings describe, and answer with ONE",
        "JSON object and nothing else: no prose, no code fence, no Python.",
        "",
        PLAN_SCHEMA_HINT,
        "Rules:",
        "- Every number in the plan reaches the CAD process; a number you invent is a wrong part.",
        "- A parameter that comes from the sheet cites the span id it was printed at.",
        "- If a dimension the geometry needs is not on the sheet, do not guess silently: use source",
        '  "assumed" with an explanation, and list the question you would ask the user in "questions"'
        "  as a list of short strings (it is fine for it to be empty).",
        "- Prefer the simplest operation sequence that reproduces the measurements.",
        "",
    ]
    if notes:
        lines += ["Reading notes:"] + [f"- {note}" for note in notes] + [""]
    lines += ["Readings:", json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))]
    return "\n".join(lines)


def measurements_evidence(
    *,
    px_per_mm: float | None,
    frame: dict | None,
    printed: list[dict],
    claims: list[dict],
    geometry: dict,
    notes: list[str],
) -> dict:
    """The evidence block, in one shape for both the reading chain and the verified input."""
    return {
        "version": EVIDENCE_VERSION,
        "sheet": {"px_per_mm": None if px_per_mm is None else round(px_per_mm, 4),
                  "frame": frame or {}, "scale_known": px_per_mm is not None},
        "printed": printed,
        "claims": claims,
        "geometry": geometry,
        "notes": notes,
    }


def propose_plan(
    chat,
    evidence: dict,
    *,
    ref: str,
    sha256: str | None,
    page: int = 1,
    model_info: dict | None = None,
    num_predict: int | None = None,
    structured: bool = True,
) -> PlanCandidate:
    """Ask the model once and judge the answer. Never raises for a bad answer: a failure is a
    recorded outcome, because the error class is the result this slice exists to produce.

    `structured` sends the plan's own JSON Schema as the decoder's grammar. The shape of a versioned
    plan is the product's contract, not a hint: without it a small model answers a plan-shaped object
    with the parameters as a list or the sketch bodies inline, and a schema-shaped failure gets read as
    "the model cannot plan" when it is the interface that is loose.
    """
    candidate = PlanCandidate(
        settings=chat.settings_record(),
        model_info=model_info or {},
        source_ref=ref,
        evidence_kind="verified" if evidence.get("verified_by") else "readings",
    )
    if structured:
        # The record must name the interface the answer was produced under: a schema-constrained decode
        # and a free-text one are two different measurements of the model.
        candidate.settings["response_format"] = f"json-schema:{SCHEMA_VERSION}"
    prompt = plan_prompt(evidence, notes=list(evidence.get("notes") or []))
    stats: dict = {}
    start = time.time()
    try:
        answer = chat.complete(
            prompt,
            num_predict=num_predict,
            response_format=GeneralPlan.model_json_schema() if structured else None,
            stats=stats,
        )
    except UnavailableModel as exc:
        candidate.seconds = round(time.time() - start, 2)
        candidate.errors.append(f"model yanıt vermedi: {exc}")
        return candidate
    candidate.seconds = round(time.time() - start, 2)
    candidate.answer = answer
    candidate.stats = {key: value for key, value in stats.items() if value is not None}
    candidate.answer_truncated = stats.get("done_reason") == "length"
    payload = _object_in(answer)
    if payload is None:
        candidate.errors.append(
            "yanıtta JSON nesnesi yok" + (" (çıktı sınırında kesildi)" if candidate.answer_truncated else "")
        )
        candidate.status = "invalid"
        return candidate
    candidate.questions = _strings(payload.pop("questions", []))
    # A model that volunteers the plan's own identity is not thereby wrong about the part: the run owns
    # provenance, so its source takes the model's place and the fact is recorded. Discarding the candidate
    # here would report a planning failure the model did not make — measured on `qwen3-vl:8b-instruct`,
    # whose seven parameters were right and whose answer was thrown away over this one key.
    if payload.pop("source", None) is not None:
        candidate.overrides.append("model kaynağı (source) verdi; koşunun kaynağı onun yerine geçti")
    payload.setdefault("version", 1)
    payload.setdefault("unit", "mm")
    payload.setdefault("assumptions", [])
    payload["source"] = SourceRef(kind="drawing", ref=ref, sha256=sha256, page=page).model_dump(mode="json")
    known = {str(span["span_id"]) for span in evidence.get("printed") or []}
    try:
        plan = GeneralPlan.model_validate(payload)
    except ValidationError as exc:
        candidate.status = "invalid"
        candidate.errors.append(_readable(exc))
        return candidate
    citation_errors = _check_citations(plan, known)
    candidate.citations = {
        "spans_cited": sorted({span for parameter in plan.parameters.values() for span in parameter.span_ids}),
        "spans_available": len(known),
    }
    if citation_errors:
        candidate.status = "invalid"
        candidate.errors.extend(citation_errors)
        candidate.plan = None
        return candidate
    candidate.plan = plan
    candidate.status = "proposed"
    candidate.assumptions = list(plan.assumptions)
    candidate.resolved_parameters = {name: round(value, 4)
                                    for name, value in evaluate_parameters(plan.parameters).items()}
    try:
        candidate.citations["program_lines"] = len(compile_general(plan).splitlines())
    except ValueError as exc:
        candidate.status = "invalid"
        candidate.plan = None
        candidate.errors.append(f"plan derlenemedi: {exc}")
    return candidate


def _check_citations(plan: GeneralPlan, known: set[str]) -> list[str]:
    """A printed parameter cites a span the sheet really carries; an assumed one says why."""
    errors: list[str] = []
    for name, parameter in plan.parameters.items():
        if parameter.source == "printed":
            unknown = [span for span in parameter.span_ids if span not in known]
            if unknown:
                errors.append(f"parametre {name!r}: kanıtta olmayan ölçü kaydına atıf {unknown}")
        elif parameter.source == "assumed" and not parameter.explanation:
            errors.append(f"parametre {name!r}: varsayımın gerekçesi yok")
    return errors


def _object_in(answer: str) -> dict | None:
    cleaned = answer.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = _OBJECT.search(cleaned)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _readable(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors(include_url=False, include_input=False):
        where = ".".join(str(item) for item in error["loc"])
        message = str(error["msg"]).removeprefix("Value error, ")
        parts.append(f"{where}: {message}" if where else message)
    return "şema hatası: " + "; ".join(parts) if parts else "şema hatası"
