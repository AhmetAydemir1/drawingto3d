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

import hashlib
from copy import deepcopy
import json
import re
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, create_model

from drawingto3d.errors import UnavailableModel
from drawingto3d.general import (
    NAME_PATTERN, GeneralPlan, Parameter, Sketch, SourceRef, _check_name,
    compile_general, evaluate_parameters, sketch_offset, sketch_values,
)

EVIDENCE_VERSION = 1
PROMPT_VERSION = "general-plan-v6-suggested-names"
SCHEMA_VERSION = "GeneralPlan v1"
REPLY_SCHEMA_VERSION = "GeneralPlan reply v4"
# The three-call interface (PLAN section 19.4): the same plan contract, asked in narrower questions.
# It is a different interface, so it carries its own version names.
#
# Its profile step asks one measured closed profile per call. The measured failure that changed its
# prompt: asked for every profile at once, the answer never closed — 4096 tokens filled with a
# repeated fragment (`radius_exprs_1d_array_2d_array_…`) — while the reading already says how many
# closed profiles the sheet has. The prompt therefore changed; the decoder grammar did not.
#
# The next round changed the evidence block: the readings carry two id spaces (the sheet's printed
# span ids, and the ids of the geometry the readings measured), they were rendered in one JSON blob
# under one heading, and the answer used the geometry space where the citation space belonged
# (`span_ids: ["h1","h2"]`) and drew a hole for the outline's profile call. Both interfaces render
# the block, so both carry a new prompt version; the grammar and the contract did not change.
#
# This round answers the refusals that change produced with the two rules the judge had been applying
# alone (`_RULE_EXPRESSIONS_USE_PARAMETERS`, `_RULE_PRINTED_CARRIES_ITS_VALUE`): the measured answer
# derived a spacing from span ids and gave a printed parameter a value its spans do not print. Words
# changed in both interfaces, so the version name moves for both. The naming/grouping hypothesis (a
# parameter per feature rather than one per printed number) is deliberately NOT in this round: it is
# unmeasured, and adding it would make the next run two variables.
#
# The round after measured the words alone: same evidence, same settings, new label — and the answer
# still wrote a span id where a name belongs. So the readings block now carries a legal name beside
# every printed number (`suggested_names`), derived from the reading's own kind and anchors. Both
# interfaces render that block, so the version name moves for both again; the judge, the grammar and
# the contract do not change.
PROMPT_VERSION_SPLIT = "general-plan-v6-split-suggested-names"
REPLY_SCHEMA_VERSION_SPLIT = "GeneralPlan reply v4 split"
PROFILE_TARGETS_VERSION = "measured-closed-profiles-v1"
# One profile is a small answer: one circle, or one closed chain. A decode that spends more than this
# on a single profile is looping, not thinking, and the record has to say "truncated" quickly instead
# of measuring the same repetition twice (the 4096-token loop above took 178 s).
PROFILE_PREDICT_CAP = 1024

# A small model answers in prose around the JSON it was asked for; take the outermost object.
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

# One wording for the plan's rules: the single-call prompt and the three step prompts quote these,
# so a rule can never be tightened in one interface and left loose in the other.
_RULE_NO_INVENTED_NUMBERS = "- Every number in the plan reaches the CAD process; a number you invent is a wrong part."
_RULE_CITE_SPANS = (
    "- A parameter that comes from the sheet cites the span id it was printed at: the ids under\n"
    "  \"printed numbers\" are the only ids `span_ids` may point at. The ids under \"measured regions\"\n"
    "  name geometry the readings measured — they are not citations, and a span_ids list that uses\n"
    "  one is refused."
)
_RULE_ASSUMED_AND_QUESTIONS = (
    "- If a dimension the geometry needs is not on the sheet, do not guess silently: use source\n"
    '  "assumed" with an explanation, and list the question you would ask the user in "questions"\n'
    "  as a list of short strings (it is fine for it to be empty)."
)
_RULE_SIMPLEST = "- Prefer the simplest operation sequence that reproduces the measurements."
# Measured on this provider: a `pattern` on a *string* is enforced by the decoder, `propertyNames` on
# an *object* is not (eval/name_probe.py). So the rule the persistent contract enforces with
# `general.NAME_PATTERN` has to be said in words as well, and a key that still arrives illegal is
# renamed by `normalize_reply_names` — losslessly — rather than the whole answer being thrown away.
_RULE_CAD_NAMES = (
    "- Names are CAD identifiers: lower-case letters, digits and underscore, starting with a letter\n"
    "  (hole_spacing_x, pocket_depth). A span id from the readings (pdf-0) is a citation for span_ids,\n"
    "  never a name: name a parameter after what it measures."
)
# Two refusals this judge produced in one measured run, neither of them answered by a rule in the
# question: a derived spacing written `(d2 - d4) / 2` (a span id read as a parameter name) and a
# printed parameter carrying 70,0 while its cited spans print 100,00 and 60,00. The judge already
# knows both (`evaluate_parameters`, `_check_parameter_citations`); these are the same two rules in
# words, so the answer is told what the check will ask instead of learning it from a refusal.
_RULE_EXPRESSIONS_USE_PARAMETERS = (
    "- A derived expression is arithmetic over the parameter names YOU declare, and nothing else. A span\n"
    "  id is a citation, not a name: to derive from a printed number, declare that number as its own\n"
    "  printed parameter first and use that name (hole_spacing_x / 2, never (d2 - d4) / 2)."
)
_RULE_PRINTED_CARRIES_ITS_VALUE = (
    "- A \"printed\" parameter carries the number its cited span prints — or the count printed beside it\n"
    "  (`4 x` -> unit \"count\") — in the plan's unit, with no arithmetic of your own: a value you\n"
    "  computed is source \"derived\", not \"printed\"."
)

# Each step is checked before handing its answer to the next; the final merge is checked again.
SPLIT_STEPS = ("parameters", "profile", "operations")
SPLIT_REQUIRED = {"parameters": ("parameters",), "profile": ("sketches",), "operations": ("operations", "result")}
STEP_VALIDATION_VERSION = "general-plan-step-validation-v1"


class _StepEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumptions: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


# Reuse the saved plan's field types, defaults and length constraints. No substitute geometry
# is constructed to validate an unfinished parameter/profile step.
_STEP_MODELS = {
    step: create_model(
        f"{step.title()}Reply", __base__=_StepEnvelope,
        **{key: (GeneralPlan.model_fields[key].annotation, deepcopy(GeneralPlan.model_fields[key]))
           for key in (("unit",) + keys if step == "parameters" else keys)},
    )
    for step, keys in SPLIT_REQUIRED.items()
}

_RULE_USE_ACCEPTED = (
    "- The parameters are already fixed: use the accepted parameter names exactly as given, and add no\n"
    "  parameter of your own. A literal is allowed only where the readings state that number."
)
# The profile step asks one profile per call, so the names its calls choose have to merge into one
# dictionary: a name already used is taken, and the answer has to pick a different one.
_RULE_UNIQUE_SKETCH_NAMES = (
    "- Every profile has its own name, and a name already used is taken: the sketches become one\n"
    "  dictionary, so two profiles cannot share a name."
)

PLAN_SCHEMA_HINT = """\
Plan JSON, exactly these keys: version, unit, parameters, sketches, operations, result, assumptions,
expect (optional), questions (optional). Do not send source; the application supplies it.
Every name (a parameter, a sketch, an operation id, a body) is a CAD identifier: ^[a-z][a-z0-9_]*$ —
lower-case letters, digits and underscore, and the first character is a letter.

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
    answer_truncated: bool | None = None
    steps: list[dict] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)
    renames: list[dict] = Field(default_factory=list)
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
        _RULE_NO_INVENTED_NUMBERS,
        _RULE_CITE_SPANS,
        _RULE_EXPRESSIONS_USE_PARAMETERS,
        _RULE_PRINTED_CARRIES_ITS_VALUE,
        _RULE_CAD_NAMES,
        _RULE_ASSUMED_AND_QUESTIONS,
        _RULE_SIMPLEST,
        "",
    ]
    if notes:
        lines += ["Reading notes:"] + [f"- {note}" for note in notes] + [""]
    lines += _readings_line(evidence)
    return "\n".join(lines)


# A span id is the only identifier the readings block shows the answer, and it copied it into `expr`
# and into parameter names (`pdf-0`, `(d2 - d4) / 2`) even after both rules were written into the
# question (PLAN section 20). The fix belongs one step earlier: every printed number also gets a legal
# name, derived from the reading's own `kind`, the anchor kinds it was measured between and the
# anchors' own axis. Not a part template — a sheet the project has never seen is named the same way.
SUGGESTED_NAMES_VERSION = "reading-derived-names-v1"

_ANCHOR_WORDS = {
    "circle-centre": "circle", "circle": "circle",
    "arc-rim": "arc", "arc-centre": "arc", "arc": "arc",
    "line-end": "edge", "end": "edge", "edge": "edge",
    "vertex": "corner", "corner": "corner",
}


def _anchor_kind(anchor: dict) -> str:
    raw = str(anchor.get("kind") or "").strip()
    return _ANCHOR_WORDS.get(raw, raw.split("-")[0] if raw else "unknown")


def _suggested_name(kind: str, form: str, anchor_kinds: list[str], anchors: list[dict]) -> tuple[str, str]:
    """The base name and the axis a printed number's own reading suggests — no part knowledge."""
    form = form or kind
    if form in ("diameter", "radius", "angle"):
        return form, ""
    if form == "distance" or kind == "linear":
        axis = ""
        if len(anchors) >= 2:
            first = anchors[0].get("point_mm") or [0.0, 0.0]
            second = anchors[1].get("point_mm") or [0.0, 0.0]
            axis = "x" if abs(first[0] - second[0]) >= abs(first[1] - second[1]) else "y"
        shared = anchor_kinds[0] if anchor_kinds and len(set(anchor_kinds)) == 1 else ""
        base = f"{shared}_spacing" if shared else "distance"
        return (f"{base}_{axis}" if axis else base), axis
    return f"{kind}_size", ""


def suggested_names(evidence: dict) -> list[dict]:
    """One legal parameter name per printed number, from the reading's own kind and anchors.

    Same name for the same kind of measurement on any sheet; when two numbers are measured the same
    way both get an index (`diameter_1`, `diameter_2`) so the names stay unique and none is bare. The
    answer is told to copy one or write its own identifier — the point is that a name exists beside
    the span id, not that this name is the right one.
    """
    claims = {str(claim.get("span_id")): claim for claim in evidence.get("claims") or []}
    rows: list[tuple[str, str, str, str, str]] = []
    for record in evidence.get("printed") or []:
        span = str(record.get("span_id"))
        claim = claims.get(span) or {}
        kind = str(record.get("kind") or claim.get("form") or "linear")
        anchors = [anchor for anchor in (claim.get("anchors") or []) if isinstance(anchor, dict)]
        anchor_kinds = [_anchor_kind(anchor) for anchor in anchors]
        base, axis = _suggested_name(kind, str(claim.get("form") or ""), anchor_kinds, anchors)
        rows.append((span, kind, "+".join(anchor_kinds) or "unknown", base, axis))
    bases = [base for *_rest, base, _axis in rows]
    seen: dict[str, int] = {}
    suggestions: list[dict] = []
    for span, kind, anchor_text, base, axis in rows:
        seen[base] = seen.get(base, 0) + 1
        name = f"{base}_{seen[base]}" if bases.count(base) > 1 else base
        suggestions.append({"span_id": span, "kind": kind, "anchors": anchor_text, "axis": axis,
                            "name": name})
    return suggestions


def _suggested_names_line(evidence: dict) -> list[str]:
    """The suggested names, right beside the ids they belong to.

    Derived from the evidence at render time, never from a case id: `suggested_names` reads `kind`,
    the anchor kinds and the anchors' own coordinates, which every sheet's reading carries.
    """
    suggestions = suggested_names(evidence)
    if not suggestions:
        return []
    return ["Names for those numbers (each derived from that reading's own kind and the anchors it was "
            "measured between — copy one, or write your own CAD identifier):",
            json.dumps(suggestions, ensure_ascii=False, separators=(",", ":")),
            "A span id is not a name and never belongs inside an expression: cite it in `span_ids`, and "
            "build a derived expression out of the names you declare.",
            ""]


def _readings_line(evidence: dict) -> list[str]:
    """The evidence block as the model sees it, with its two id spaces named apart.

    Verification metadata can contain a reference STEP path/part name. It belongs to the run, not to
    the model's observations. The same evidence fields are kept for real and verified input, and the
    three step prompts reuse this line so both interfaces quote the readings identically.

    Measured (PLAN section 20, round after the per-profile step): the planner answered the outline's
    profile call with a hole's centre and diameter, and cited drawn-circle ids (`h1`, `h2`) in
    `span_ids` where the sheet's own printed span ids belonged. Both id spaces were sitting in one
    JSON blob under one heading, with nothing saying which of them can be cited. The content below is
    the same evidence as before; what changed is that the printed numbers and the measured regions are
    separated and each heading says what its ids are for.

    Measured again (PLAN section 20, the round after that): with the rules written out in words, the
    answer still put a span id where a name belongs (`expr: "(d2 - d4) / 2"`, a parameter named
    `pdf-0`) — the span id is the only identifier this block offers it. So every printed number also
    gets a legal name derived from the reading's own `kind` and anchors; see `suggested_names`.
    """
    lines: list[str] = []
    if "sheet" in evidence:
        lines += ["Sheet:", json.dumps(evidence["sheet"], ensure_ascii=False, separators=(",", ":"))]
    printed = evidence.get("printed") or []
    lines += [f"Printed numbers ({len(printed)}) — `span_ids` may point at these ids, and only these:",
              json.dumps(printed, ensure_ascii=False, separators=(",", ":"))]
    lines += _suggested_names_line(evidence)
    claims = evidence.get("claims") or []
    lines += [f"What the readings resolved about those numbers ({len(claims)}) — the form each was "
              "confirmed as, and the geometry points it was measured between:",
              json.dumps(claims, ensure_ascii=False, separators=(",", ":"))]
    if "geometry" in evidence:
        lines += ["Measured regions — these ids name geometry the readings measured (a circle, an arc, "
                  "the outer loop, where they sit and how big they are). They are NOT citations and "
                  "never belong in `span_ids`:",
                  json.dumps(evidence["geometry"], ensure_ascii=False, separators=(",", ":"))]
    notes = evidence.get("notes") or []
    if notes:
        lines += ["Reading notes:"] + [f"- {note}" for note in notes]
    lines += [f"Readings version: {evidence.get('version')}."]
    return lines


def plan_reply_schema() -> dict:
    """Express wire constraints that Pydantic defaults/after-validators do not export.

    The saved GeneralPlan is unchanged. Its union tags have Python defaults, which makes them
    optional in generated JSON Schema even though the union validator needs explicit tags.
    Parameter source/value rules and repeat exclusivity live in after-validators; explicitly
    represent them as closed alternatives for constrained decoding. Validation still judges the
    model answer; this does not repair or fill any generated geometry.
    """
    schema = GeneralPlan.model_json_schema()
    schema["title"] = REPLY_SCHEMA_VERSION
    schema["properties"].pop("source")
    schema["required"] = [key for key in schema["required"] if key != "source"]
    schema["$defs"].pop("SourceRef", None)
    schema["properties"]["questions"] = {"type": "array", "items": {"type": "string"}}
    definitions = schema["$defs"]
    for definition in definitions.values():
        for tag in ("type", "op"):
            if "const" in definition.get("properties", {}).get(tag, {}):
                required = definition.setdefault("required", [])
                if tag not in required:
                    required.append(tag)

    # The identifier rule, where the wire can carry it. Pydantic already exports `pattern` for the
    # fields it declares with one (`id`, `output`, `result`); the name *references* and the two keyed
    # collections have to be named here or the rule is only in Python's validator.
    for key in ("parameters", "sketches"):
        schema["properties"][key]["propertyNames"] = {"pattern": NAME_PATTERN}
    for operation, fields in _NAME_REFERENCE_FIELDS.items():
        for field in fields:
            definitions[_NAME_DEFINITIONS[operation]]["properties"][field] = {"type": "string",
                                                                             "pattern": NAME_PATTERN}
    definitions["FuseOp"]["properties"]["inputs"]["items"] = {"type": "string", "pattern": NAME_PATTERN}

    parameter = definitions["Parameter"]
    branches = []
    for source in ("printed", "derived", "assumed", "user"):
        branch = deepcopy(parameter)
        props = branch["properties"]
        props["source"] = {"type": "string", "const": source}
        key, excluded = ("expr", "value") if source == "derived" else ("value", "expr")
        props.pop(excluded)
        props[key] = {"type": "string" if key == "expr" else "number"}
        branch["required"] = ["unit", "source", key]
        if source == "derived":
            props["unit"] = {"type": "string", "enum": ["mm", "deg"]}
        if source == "printed":
            props["span_ids"]["minItems"] = 1
            branch["required"].append("span_ids")
        if source in ("assumed", "user"):
            props["explanation"]["minLength"] = 1
            branch["required"].append("explanation")
        branches.append(branch)
    definitions["Parameter"] = {"oneOf": branches}

    repeat = definitions["RepeatOp"]
    branches = []
    for mode, excluded in (("linear", "circular"), ("circular", "linear")):
        branch = deepcopy(repeat)
        branch["properties"].pop(excluded)
        branch["properties"][mode] = {"$ref": f"#/$defs/{'LinearRepeat' if mode == 'linear' else 'CircularRepeat'}"}
        branch["required"].append(mode)
        branches.append(branch)
    definitions["RepeatOp"] = {"oneOf": branches}
    return schema


def _sha256_text(text: str) -> str:
    """The prompt's fingerprint: a measurement cites the question it asked, not only its version name."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Where one identifier refers to another, by operation tag. The wire carries a `pattern` for these;
# the adapter below rewrites them when a key could not be constrained (this provider ignores
# `propertyNames` on an object).
_NAME_REFERENCE_FIELDS = {
    "extrude": ("sketch",),
    "revolve": ("sketch",),
    "repeat": ("input",),
    "cut": ("target", "tool"),
}
# The operation tag is what an answer writes; the definition name is what the schema calls it.
_NAME_DEFINITIONS = {"extrude": "ExtrudeOp", "revolve": "RevolveOp", "repeat": "RepeatOp", "cut": "CutOp"}
_NAME_FIELDS = ("id", "output")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# The name a run record uses for the rewrite, so two answers decoded the same way are comparable.
NAME_ADAPTER = "lossless-identifier-rewrite"


def _normalized_name(name: str) -> str:
    """One identifier in the contract's alphabet: lower case, digits, underscore, a letter first."""
    collapsed = re.sub(r"[^a-z0-9_]", "_", str(name).lower())
    return collapsed if collapsed[:1].isalpha() else f"p_{collapsed}"


def normalize_reply_names(payload: dict) -> tuple[dict, list[dict]]:
    """Rewrite an answer's own CAD identifiers into the contract's alphabet, changing nothing else.

    What this is for, measured (`eval/name_probe.py`): a `pattern` on a *string* is enforced by this
    provider's decoder, but `propertyNames` on an *object* is not, so a parameter or a sketch can
    still arrive keyed `hole_spacing_X` or `pdf-0` and the whole plan is then rejected over a
    spelling — an error the interface can name but cannot prevent.

    What it is *not*: a repair. No name is invented, no value, unit, citation, coordinate or entity is
    touched, and no expression is evaluated — the rewrite is a bijection on the names the answer
    already used, so two distinct names never become one (a collision takes a recorded suffix), and a
    name referenced from an expression or from another operation follows the key it names. Every
    rewrite is returned, and the raw answer is kept verbatim beside it, so the record shows what the
    model wrote and what the CAD process read.
    """
    data = deepcopy(payload)

    # Every name the answer uses, in the order it writes them. A legal name is left exactly as it is,
    # so a collision is decided in favour of the answer's own spelling.
    used: list[str] = []
    for name in list(_mapping(data.get("parameters"))) + list(_mapping(data.get("sketches"))):
        used.append(name)
    for operation in data.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        fields = _NAME_FIELDS + _NAME_REFERENCE_FIELDS.get(str(operation.get("op")), ())
        used += [_text(operation.get(field)) for field in fields]
        used += [_text(item) for item in (operation.get("inputs") or [])]
    used.append(_text(data.get("result")))
    used = [name for name in used if name]

    taken = {name for name in used if re.fullmatch(NAME_PATTERN, name)}
    mapping: dict[str, str] = {}
    for name in used:
        if name in mapping:
            continue
        chosen = _normalized_name(name)
        if chosen != name:
            # A legal name keeps its spelling; a rewritten one gives way if it would collide with it.
            candidate, suffix = chosen, 2
            while candidate in taken:
                candidate, suffix = f"{chosen}_{suffix}", suffix + 1
            chosen = candidate
        mapping[name] = chosen
        taken.add(chosen)

    def renamed(value):
        return mapping.get(value, value) if isinstance(value, str) else value

    def expression(text):
        """A formula follows the names it uses; a function call is not a parameter name."""
        if not isinstance(text, str):
            return text
        out, index = [], 0
        while index < len(text):
            match = _name_at(text, index, mapping)
            if match is not None:
                out.append(mapping[match])
                index += len(match)
                continue
            token = _IDENTIFIER.match(text, index)
            if token is None:
                out.append(text[index])
                index += 1
                continue
            after = text[token.end():token.end() + 1]
            out.append(token.group(0) if after == "(" else renamed(token.group(0)))
            index = token.end()
        return "".join(out)

    if isinstance(data.get("parameters"), dict):
        parameters = {}
        for name, parameter in data["parameters"].items():
            if isinstance(parameter, dict) and "expr" in parameter:
                parameter = {**parameter, "expr": expression(parameter["expr"])}
            parameters[renamed(name)] = parameter
        data["parameters"] = parameters
    if isinstance(data.get("sketches"), dict):
        data["sketches"] = {renamed(name): _renamed_sketch(sketch, renamed, expression)
                            for name, sketch in data["sketches"].items()}
    if isinstance(data.get("operations"), list):
        data["operations"] = [_renamed_operation(operation, renamed, expression)
                              for operation in data["operations"]]
    if "result" in data:
        data["result"] = renamed(data["result"])
    if isinstance(data.get("expect"), dict):
        data["expect"] = _renamed_expect(data["expect"], expression)
    renames = [{"from": name, "to": mapping[name]} for name in dict.fromkeys(used) if mapping[name] != name]
    return data, renames


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _name_at(text: str, index: int, mapping: dict) -> str | None:
    """The answer's own name starting here, longest first, and only whole-identifier matches.

    A name can carry characters an expression cannot (`pdf-0` tokenises as `pdf - 0`), so the name
    itself is matched before the identifier scanner gets a chance to see its parts — while a name that
    is merely a prefix of a longer identifier (`hole` inside `hole_spacing_x`) is not a match.
    """
    for name in sorted(mapping, key=len, reverse=True):
        if not text.startswith(name, index):
            continue
        before = text[index - 1:index]
        after = text[index + len(name):index + len(name) + 1]
        if (_IDENTIFIER.match(before) is None or before == "") and (_IDENTIFIER.match(after) is None or after == ""):
            return name
    return None


def _renamed_sketch(sketch: dict, renamed, expression) -> dict:
    if not isinstance(sketch, dict):
        return sketch
    out = dict(sketch)
    if "offset" in out:
        out["offset"] = expression(out["offset"])
    entities = []
    for entity in out.get("entities") or []:
        if not isinstance(entity, dict):
            entities.append(entity)
            continue
        entity = dict(entity)
        for field in ("start", "end", "center"):
            if isinstance(entity.get(field), list):
                entity[field] = [expression(item) for item in entity[field]]
        if "radius" in entity:
            entity["radius"] = expression(entity["radius"])
        entities.append(entity)
    if entities:
        out["entities"] = entities
    return out


def _renamed_operation(operation: dict, renamed, expression) -> dict:
    if not isinstance(operation, dict):
        return operation
    out = dict(operation)
    for field in _NAME_FIELDS + _NAME_REFERENCE_FIELDS.get(str(operation.get("op")), ()):
        if field in out:
            out[field] = renamed(out[field])
    if isinstance(out.get("inputs"), list):
        out["inputs"] = [renamed(item) for item in out["inputs"]]
    for field in ("distance", "angle"):
        if field in out:
            out[field] = expression(out[field])
    for mode in ("linear", "circular"):
        if not isinstance(out.get(mode), dict):
            continue
        out[mode] = dict(out[mode])
        for field in ("x_pitch", "y_pitch"):
            if field in out[mode]:
                out[mode][field] = expression(out[mode][field])
    return out


def _renamed_expect(expect: dict, expression) -> dict:
    out = dict(expect)
    if isinstance(out.get("bbox"), list):
        out["bbox"] = [expression(item) for item in out["bbox"]]
    if "volume" in out:
        out["volume"] = expression(out["volume"])
    return out


def _hint_section(prefix: str) -> str:
    """One paragraph of `PLAN_SCHEMA_HINT`, so a step prompt cannot drift from the single prompt."""
    for section in PLAN_SCHEMA_HINT.split("\n\n"):
        if section.startswith(prefix):
            return section
    raise ValueError(f"plan hint section not found: {prefix}")


def step_reply_schema(step: str, *, title: str | None = None) -> dict:
    """One step's decoder grammar: the plan's own leaf rules, only that step's top-level keys.

    Uses the same explicit wire constraints as the single-call schema. Semantic constraints
    (closed profiles, valid references and units) still require the final plan validator. `title`
    names one of several same-shaped calls in the record: the profile step asks one profile per
    call, and the run has to say which profile each grammar was sent for.
    """
    if step not in SPLIT_STEPS:
        raise ValueError(f"unknown plan step: {step}")
    full = plan_reply_schema()
    keys = {
        "parameters": ("unit", "parameters", "assumptions", "questions"),
        "profile": ("sketches", "assumptions", "questions"),
        "operations": ("operations", "result", "assumptions", "questions"),
    }[step]
    schema = {
        "title": title or f"{REPLY_SCHEMA_VERSION_SPLIT}: {step}",
        "type": "object",
        "properties": {key: full["properties"][key] for key in keys if key in full["properties"]},
        "required": list(SPLIT_REQUIRED[step]),
        "additionalProperties": False,
        "$defs": full.get("$defs", {}),
    }
    schema["properties"]["questions"] = {"type": "array", "items": {"type": "string"}}
    return schema


def profile_targets(evidence: dict) -> list[dict]:
    """The closed profiles the readings themselves measured, in the order the sheet was read.

    A profile in the plan contract is one circle, or one closed chain of lines and arcs — and that is
    what a reading measures: the sheet's one closed outer loop, plus its closed circles. So this list
    is a *reading*, not a plan: it says which measured region each profile call is about, and leaves
    every name, entity, coordinate and expression to the model's answer. A reading that measured
    neither returns an empty list, and the profile step then asks for every profile in one call.
    """
    geometry = evidence.get("geometry") or {}
    targets: list[dict] = []
    outline = geometry.get("outline_mm")
    if isinstance(outline, dict) and ("width_mm" in outline or "height_mm" in outline):
        targets.append({"kind": "outline", "geometry_id": "outline", "measured": dict(outline)})
    elif isinstance(outline, list) and len(outline) >= 2:
        # The hand-verified relation table states the outline as a [width, height] pair.
        targets.append({"kind": "outline", "geometry_id": "outline",
                        "measured": {"width_mm": outline[0], "height_mm": outline[1]}})
    for index, circle in enumerate(geometry.get("circles") or []):
        if not isinstance(circle, dict) or "diameter_mm" not in circle:
            continue
        targets.append({"kind": "circle",
                        "geometry_id": str(circle.get("id") or f"circle_{index + 1}"),
                        "measured": {key: circle[key] for key in ("diameter_mm", "centre_mm", "kind")
                                     if key in circle}})
    return targets


def _profile_label(target: dict | None, index: int, count: int) -> str:
    """The name a failure uses for one profile call, so the record says which one stopped the run."""
    if target is None:
        return "profile"
    geometry_id = target.get("geometry_id")
    return f"profile {index}/{count}" + (f" ({geometry_id})" if geometry_id else "")


def _profile_limit(num_predict: int | None) -> int:
    """The bound on one profile call's output; the run's own limit stays the ceiling."""
    return PROFILE_PREDICT_CAP if num_predict is None else min(num_predict, PROFILE_PREDICT_CAP)


def step_prompt(step: str, evidence: dict, accepted: dict, notes: list[str] | None = None, *,
                target: dict | None = None, index: int | None = None, count: int | None = None,
                drawn: list[str] | None = None) -> str:
    """One step's question: the readings, that step's shape, and the earlier steps' accepted answers.

    The earlier answers are handed over verbatim rather than re-described, so a step cannot silently
    change a parameter name or a sketch name that a later step depends on. A profile call is told
    which measured closed profile it is about (`target`), and which sketch names its sibling calls
    already took — otherwise the one dictionary the profiles merge into would be a name collision
    the harness designed in.
    """
    intro = {
        "parameters": [
            "You are the CAD planner. Step 1 of 3: the parameters.",
            "Below are measured, cited readings from ONE engineering drawing.",
            "List the parameters the part needs — the ones printed on the sheet, the ones derived from",
            "them, and any convention the sheet does not state — and answer with ONE JSON object and",
            "nothing else: no prose, no code fence, no Python.",
            "",
            _hint_section("parameters:"),
            "Rules:",
            _RULE_CITE_SPANS,
            _RULE_EXPRESSIONS_USE_PARAMETERS,
            _RULE_PRINTED_CARRIES_ITS_VALUE,
            _RULE_CAD_NAMES,
            _RULE_ASSUMED_AND_QUESTIONS,
            "",
        ],
        "profile": [
            "You are the CAD planner. Step 2 of 3: the profiles.",
            "Below are measured, cited readings from ONE engineering drawing, then the parameters already",
            "accepted for it. Draw the closed profile this call is about and answer with ONE JSON object:",
            "no prose, no code fence, no Python.",
            "",
            _hint_section("sketches:"),
            "Rules:",
            _RULE_NO_INVENTED_NUMBERS,
            _RULE_CAD_NAMES,
            _RULE_USE_ACCEPTED,
            _RULE_UNIQUE_SKETCH_NAMES,
            "",
        ],
        "operations": [
            "You are the CAD planner. Step 3 of 3: the operations.",
            "Below are measured, cited readings from ONE engineering drawing, then the parameters and",
            "profiles already accepted for it. Choose the operation sequence and answer with ONE JSON",
            "object and nothing else: no prose, no code fence, no Python.",
            "",
            _hint_section("operations:"),
            _hint_section("result:"),
            "Rules:",
            _RULE_CAD_NAMES,
            _RULE_USE_ACCEPTED,
            _RULE_SIMPLEST,
            "",
        ],
    }[step]
    lines = list(intro)
    if step == "profile":
        if target is not None and index is not None and count is not None:
            # The region this call is about is handed over as its own keyed block. It used to be a
            # sentence with the measured numbers inside it, and the answer drew a *hole* for the
            # outline's call: which region the call is about has to be as structural as the id spaces.
            lines += ["Target profile (this call):",
                      json.dumps({"index": index, "count": count, "kind": target.get("kind"),
                                  "geometry_id": target.get("geometry_id"),
                                  "measured": target.get("measured") or {}},
                                 ensure_ascii=False, separators=(",", ":")),
                      "Draw exactly this one profile, as exactly one sketch: a closed chain of lines "
                      "and arcs that returns to its start, using the parameters already accepted.", ""]
        else:
            lines += ["Draw every closed profile the readings describe, one sketch each.", ""]
        if drawn:
            lines += ["Sketch names already used (taken; use another name for this profile): "
                      + ", ".join(sorted(drawn)), ""]
    if notes:
        lines += ["Reading notes:"] + [f"- {note}" for note in notes] + [""]
    lines += _readings_line(evidence)
    for earlier in SPLIT_STEPS[: SPLIT_STEPS.index(step)]:
        lines += ["", f"Accepted {earlier} (fixed; do not change it):",
                  json.dumps(accepted[earlier], ensure_ascii=False, separators=(",", ":"))]
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


def chain_evidence(reading) -> dict:
    """One real sheet's readings, in the block the planner is asked with.

    The reading chain (`observe` -> `bind` -> `meaning` -> `read_sheet`) produces this; the planner
    never sees a reference part, a file name of one, or an answer. What it sees is what the sheet
    itself prints (with the span id of every number) and what those numbers were measured to be
    attached to, plus the geometry measured in millimetres — the same input the rules-based proposal
    works from, so rules versus model is a comparison of the planner and not of the reading.
    """
    geometry = {
        "units": "mm; circle centres relative to the outline centre, in the sheet's own measured frame",
        "outline_mm": reading.outline_mm,
        "circles": reading.circles_mm,
        "components": reading.components,
    }
    notes = list(reading.notes) + ["kaynak: okuma zinciri (observe → bind → meaning)"]
    return measurements_evidence(
        px_per_mm=reading.sheet_px_per_mm,
        frame=reading.frame,
        printed=reading.printed,
        claims=reading.claims,
        geometry=geometry,
        notes=notes + [f"okuma reddi: {refusal}" for refusal in reading.refusals],
    )


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
    normalize_names: bool = False,
) -> PlanCandidate:
    """Ask the model once and judge the answer. Never raises for a bad answer: a failure is a
    recorded outcome, because the error class is the result this slice exists to produce.

    `structured` sends the plan's own JSON Schema as the decoder's grammar. The shape of a versioned
    plan is the product's contract, not a hint: without it a small model answers a plan-shaped object
    with the parameters as a list or the sketch bodies inline, and a schema-shaped failure gets read as
    "the model cannot plan" when it is the interface that is loose.

    `normalize_names` runs the lossless identifier rewrite (`normalize_reply_names`) on the answer
    before it is judged — a separate experiment, because the constraint it stands in for is not one
    this provider's decoder can carry for object keys. It is recorded in the run's settings either way.
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
        candidate.settings["response_format"] = f"json-schema:{REPLY_SCHEMA_VERSION}"
    candidate.settings["name_normalization"] = NAME_ADAPTER if normalize_names else "off"
    candidate.settings["suggested_names"] = SUGGESTED_NAMES_VERSION
    prompt = plan_prompt(evidence, notes=list(evidence.get("notes") or []))
    candidate.settings["prompt_sha256"] = _sha256_text(prompt)
    schema = plan_reply_schema() if structured else None
    if schema is not None:
        candidate.settings["schema_sha256"] = _sha256_text(json.dumps(schema, sort_keys=True))
    stats: dict = {}
    start = time.time()
    try:
        answer = chat.complete(
            prompt,
            num_predict=num_predict,
            response_format=schema,
            stats=stats,
        )
    except UnavailableModel as exc:
        candidate.seconds = round(time.time() - start, 2)
        candidate.errors.append(f"model yanıt vermedi: {exc}")
        return candidate
    candidate.seconds = round(time.time() - start, 2)
    candidate.answer = answer
    candidate.stats = {key: value for key, value in stats.items() if value is not None}
    # A missing `done_reason` means the provider did not say how it stopped: recording "not truncated"
    # there would be a claim the record cannot back (seen on a CLI run whose answer ended in a `}` loop).
    if stats.get("done_reason"):
        candidate.answer_truncated = stats.get("done_reason") == "length"
    payload = _object_in(answer)
    if payload is None:
        candidate.errors.append(
            "yanıtta JSON nesnesi yok" + (" (çıktı sınırında kesildi)" if candidate.answer_truncated else "")
        )
        candidate.status = "invalid"
        return candidate
    return _judge(candidate, payload, evidence, ref=ref, sha256=sha256, page=page,
                  normalize_names=normalize_names)


def validate_step_payload(step: str, payload: dict, accepted: dict[str, dict], evidence: dict,
                          *, normalize_names: bool = False) -> list[str]:
    """Check what is already knowable before spending another model call.

    Raw answers stay unchanged. When the optional name adapter is enabled, validate the same
    accumulated view that the final judge will normalize; provenance and dimensions stay intact.
    Passing here means structurally usable input for the next step, not verified drawing geometry.
    """
    try:
        combined = {key: value for part in (*accepted.values(), payload)
                    for key, value in part.items() if key not in ("questions", "assumptions")}
        if normalize_names:
            combined, _renames = normalize_reply_names(combined)
        current = {key: combined.get(key, value) for key, value in payload.items()}
        _STEP_MODELS[step].model_validate(current)
        parameters = TypeAdapter(dict[str, Parameter]).validate_python(combined["parameters"])
        for name in parameters:
            _check_name(name, "parametre")
        evaluate_parameters(parameters)
        printed = {str(record.get("span_id")): record for record in evidence.get("printed") or []}
        errors = _check_parameter_citations(parameters, printed, combined.get("unit", "mm"))
        if errors:
            return errors
        if step in ("profile", "operations"):
            sketches = TypeAdapter(dict[str, Sketch]).validate_python(combined["sketches"])
            for name, sketch in sketches.items():
                _check_name(name, "eskiz")
                sketch_values(name, sketch, parameters)
                sketch_offset(name, sketch, parameters)
        if step == "operations":
            # Only the temporary validation context is synthetic. The final judge attaches the
            # drawing's real source/hash, after checking all operation dependencies here.
            GeneralPlan.model_validate({**combined, "source": {"kind": "synthetic"}})
    except ValidationError as exc:
        return [_readable(exc)]
    except ValueError as exc:
        return [f"şema hatası: {exc}"]
    return []


def propose_plan_split(
    chat,
    evidence: dict,
    *,
    ref: str,
    sha256: str | None,
    page: int = 1,
    model_info: dict | None = None,
    num_predict: int | None = None,
    normalize_names: bool = False,
) -> PlanCandidate:
    """The same plan contract, asked in narrower questions instead of one (PLAN sections 19.4, 20).

    The parameters and the operations are asked once each; the profiles are asked one call per closed
    profile the readings measured (`profile_targets`), because the profile step is the one measured to
    spend its whole output budget on a repeated fragment. Each answer's structure, references and
    citations — and, for a profile, its closure — are checked before the next call is spent, and a
    failure records its own prompt, grammar, raw answer and stats, so the failure names the step (and
    the profile) that produced it.

    No step's answer is repaired by hand and no per-part template exists: a measured circle is a region
    the sheet carries, and everything the plan says about that region is the model's answer.
    """
    candidate = PlanCandidate(
        prompt_version=PROMPT_VERSION_SPLIT,
        settings=chat.settings_record(),
        model_info=model_info or {},
        source_ref=ref,
        evidence_kind="verified" if evidence.get("verified_by") else "readings",
    )
    targets = profile_targets(evidence)
    candidate.settings["response_format"] = (
        f"json-schema:{REPLY_SCHEMA_VERSION_SPLIT} (parameters + {len(targets) or 1} profil + operations"
        f" = {len(SPLIT_STEPS) + max(0, len(targets) - 1)} çağrı)"
    )
    candidate.settings["profile_targets"] = PROFILE_TARGETS_VERSION
    candidate.settings["suggested_names"] = SUGGESTED_NAMES_VERSION
    candidate.settings["name_normalization"] = NAME_ADAPTER if normalize_names else "off"
    candidate.settings["step_validation"] = STEP_VALIDATION_VERSION
    notes = list(evidence.get("notes") or [])
    accepted: dict[str, dict] = {}
    started = time.time()

    def stop() -> PlanCandidate:
        """The run is over; the wall time belongs to the candidate even when a step failed."""
        candidate.seconds = round(time.time() - started, 2)
        return candidate

    def check(step: str, payload: dict, label: str, record: dict, earlier: list[dict],
              extra_errors: list[str]) -> list[str]:
        """Judge this answer against everything accepted so far and record the verdict on its record."""
        errors = extra_errors or validate_step_payload(step, payload, accepted, evidence,
                                                       normalize_names=normalize_names)
        record["errors"] = errors
        payloads = (*accepted.values(), *earlier, payload)
        candidate.questions = _merged_strings(payloads, "questions")
        candidate.assumptions = _merged_strings(payloads, "assumptions")
        if errors:
            candidate.errors.extend(f"adım {label}: {error}" for error in errors)
            candidate.status = "invalid"
            return errors
        record["accepted"] = True
        return []

    payload = _ask_step(candidate, chat, step="parameters", label="parameters", extra={},
                        prompt=step_prompt("parameters", evidence, accepted, notes),
                        schema=step_reply_schema("parameters"), num_predict=num_predict)
    if payload is None:
        return stop()
    if check("parameters", payload, "parameters", candidate.steps[-1], [], _truncated(candidate.steps[-1])):
        return stop()
    accepted["parameters"] = payload

    profile_payloads: list[dict] = []
    sketches: dict[str, dict] = {}
    for index, target in enumerate(targets or [None], start=1):
        count = len(targets) or 1
        label = _profile_label(target, index, count)
        payload = _ask_step(
            candidate, chat, step="profile", label=label, num_predict=_profile_limit(num_predict),
            prompt=step_prompt("profile", evidence, accepted, notes, target=target, index=index,
                               count=count, drawn=list(sketches)),
            schema=step_reply_schema("profile", title=f"{REPLY_SCHEMA_VERSION_SPLIT}: profile {index}/{count}"),
            extra={"profile": {"index": index, "count": count, "kind": (target or {}).get("kind", "all"),
                               "geometry_id": (target or {}).get("geometry_id")}},
        )
        if payload is None:
            return stop()
        record = candidate.steps[-1]
        drawn = _mapping(payload.get("sketches"))
        if target is None:
            # The reading measured no closed profile to enumerate, so every profile was asked at once.
            extra_errors: list[str] = []
        elif not drawn:
            extra_errors = ["yanıtta eskiz yok"]
        elif len(drawn) > 1:
            extra_errors = [f"tek kapalı profil istendi, {len(drawn)} eskiz geldi: {sorted(drawn)}"]
        elif [name for name in drawn if name in sketches]:
            extra_errors = [f"bu adı başka bir profil aldı: {[name for name in drawn if name in sketches]}"]
        else:
            extra_errors = []
        if check("profile", payload, label, record, profile_payloads, extra_errors or _truncated(record)):
            return stop()
        profile_payloads.append(payload)
        sketches.update(drawn)
    accepted["profile"] = {"sketches": sketches,
                           "assumptions": _merged_strings(profile_payloads, "assumptions"),
                           "questions": _merged_strings(profile_payloads, "questions")}

    payload = _ask_step(candidate, chat, step="operations", label="operations", extra={},
                        prompt=step_prompt("operations", evidence, accepted, notes),
                        schema=step_reply_schema("operations"), num_predict=num_predict)
    if payload is None:
        return stop()
    if check("operations", payload, "operations", candidate.steps[-1], [], _truncated(candidate.steps[-1])):
        return stop()
    accepted["operations"] = payload

    merged = {
        "version": 1,
        "unit": accepted["parameters"].get("unit", "mm"),
        "parameters": accepted["parameters"]["parameters"],
        "sketches": accepted["profile"]["sketches"],
        "operations": accepted["operations"]["operations"],
        "result": accepted["operations"]["result"],
        "assumptions": _merged_strings(accepted.values(), "assumptions"),
        "questions": _merged_strings(accepted.values(), "questions"),
    }
    candidate.answer = json.dumps(merged, ensure_ascii=False, indent=1)
    judged = _judge(candidate, merged, evidence, ref=ref, sha256=sha256, page=page,
                    normalize_names=normalize_names)
    candidate.seconds = round(time.time() - started, 2)
    return judged


def _ask_step(candidate: PlanCandidate, chat, *, step: str, label: str, prompt: str, schema: dict,
              extra: dict, num_predict: int | None) -> dict | None:
    """One model call, recorded whatever happens; None means the run stopped here and the record says why.

    The record names the question (prompt fingerprint), the grammar (schema fingerprint and title), the
    output limit, the raw answer and the provider's own stop reason, so a failure can be re-read without
    asking the model again. `label` is what a failure calls this call: a step, or one profile of several.
    """
    record: dict = {
        "step": step,
        "label": label,
        "response_format": schema["title"],
        "prompt_version": PROMPT_VERSION_SPLIT,
        "validation_version": STEP_VALIDATION_VERSION,
        "accepted": False,
        "schema_sha256": _sha256_text(json.dumps(schema, sort_keys=True)),
        "prompt_sha256": _sha256_text(prompt),
        "num_predict": num_predict,
    }
    record.update(extra)
    stats: dict = {}
    start = time.time()
    try:
        answer = chat.complete(prompt, num_predict=num_predict, response_format=schema, stats=stats)
    except UnavailableModel as exc:
        record.update({"answer": "", "seconds": round(time.time() - start, 2),
                       "errors": [f"model yanıt vermedi: {exc}"]})
        candidate.steps.append(record)
        candidate.errors.append(f"adım {label}: model yanıt vermedi: {exc}")
        candidate.status = "invalid"
        return None
    record["seconds"] = round(time.time() - start, 2)
    record["answer"] = answer
    record["stats"] = {key: value for key, value in stats.items() if value is not None}
    record["answer_truncated"] = (stats.get("done_reason") == "length") if stats.get("done_reason") else None
    if record["answer_truncated"]:
        candidate.answer_truncated = True
    candidate.stats = _sum_stats(candidate.stats, record["stats"])
    payload = _object_in(answer)
    if payload is None:
        reason = "yanıtta JSON nesnesi yok" + (" (çıktı sınırında kesildi)" if record["answer_truncated"] else "")
        record["errors"] = [reason]
        candidate.steps.append(record)
        candidate.errors.append(f"adım {label}: {reason}")
        candidate.status = "invalid"
        return None
    if payload.pop("source", None) is not None:
        # The step schemas have no `source`; a model that volunteers one is not thereby wrong about the
        # part, so the run's identity takes its place and the fact is recorded once for the run.
        if not any("kaynağı (source)" in item for item in candidate.overrides):
            candidate.overrides.append("model kaynağı (source) verdi; koşunun kaynağı onun yerine geçti")
    missing = [key for key in SPLIT_REQUIRED[step] if key not in payload]
    if missing:
        record["errors"] = [f"eksik anahtar: {missing}"]
        candidate.steps.append(record)
        candidate.errors.append(f"adım {label}: eksik anahtar {missing}")
        candidate.status = "invalid"
        return None
    record["keys"] = sorted(payload)
    candidate.steps.append(record)
    return payload


def _truncated(record: dict) -> list[str]:
    """A partial answer is a failure even when the JSON happens to parse: it is not what was asked."""
    return ["çıktı sınırında kesildi; kısmi yanıt sonraki adıma aktarılamaz"] if record.get("answer_truncated") else []


def _sum_stats(total: dict, step: dict) -> dict:
    """Per-step stats stay in the step record; the candidate carries the run's totals."""
    summed = dict(total)
    summed["steps"] = summed.get("steps", 0) + 1
    for key in ("eval_count", "prompt_eval_count", "total_duration_ns"):
        if isinstance(step.get(key), (int, float)):
            summed[key] = summed.get(key, 0) + step[key]
    return summed


def _merged_strings(payloads, key: str) -> list[str]:
    """`assumptions`/`questions` from every step, in step order, without repeats."""
    out: list[str] = []
    for payload in payloads:
        for item in _strings((payload or {}).get(key)):
            if item not in out:
                out.append(item)
    return out


def _judge(candidate: PlanCandidate, payload: dict, evidence: dict, *, ref: str, sha256: str | None,
           page: int, normalize_names: bool = False) -> PlanCandidate:
    """The one place an answer becomes a plan: schema, citations, resolved parameters, compiler.

    Both interfaces end here, so the persistent plan contract cannot differ between them.
    """
    candidate.questions = _strings(payload.pop("questions", []))
    # A model that volunteers the plan's own identity is not thereby wrong about the part: the run owns
    # provenance, so its source takes the model's place and the fact is recorded. Discarding the candidate
    # here would report a planning failure the model did not make — measured on `qwen3-vl:8b-instruct`,
    # whose seven parameters were right and whose answer was thrown away over this one key.
    if payload.pop("source", None) is not None:
        candidate.overrides.append("model kaynağı (source) verdi; koşunun kaynağı onun yerine geçti")
    if normalize_names:
        before = json.dumps(payload, sort_keys=True)
        payload, candidate.renames = normalize_reply_names(payload)
        if json.dumps(payload, sort_keys=True) == before:
            candidate.settings["name_normalization"] = f"{NAME_ADAPTER} (değişiklik yok)"
    payload.setdefault("version", 1)
    payload.setdefault("unit", "mm")
    payload.setdefault("assumptions", [])
    payload["source"] = SourceRef(kind="drawing", ref=ref, sha256=sha256, page=page).model_dump(mode="json")
    printed = {str(record.get("span_id")): record for record in evidence.get("printed") or []}
    try:
        plan = GeneralPlan.model_validate(payload)
    except ValidationError as exc:
        candidate.status = "invalid"
        candidate.errors.append(_readable(exc))
        return candidate
    citation_errors = _check_citations(plan, printed)
    candidate.citations = {
        "spans_cited": sorted({span for parameter in plan.parameters.values() for span in parameter.span_ids}),
        "spans_available": len(printed),
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


def _check_citations(plan: GeneralPlan, printed: dict[str, dict]) -> list[str]:
    """A printed parameter cites a span the sheet really carries — and carries what that span prints.

    A span id alone proves nothing: the id can be real while the number beside it is the model's own
    arithmetic, so the cited record has to back the value as well — the printed number, or the count
    printed beside it ("4 x 6,80 THRU ALL") — in that parameter's own unit. An assumed parameter says why.
    """
    return _check_parameter_citations(plan.parameters, printed, plan.unit)


def _check_parameter_citations(parameters: dict[str, Parameter], printed: dict[str, dict],
                              unit: str) -> list[str]:
    """The same provenance check for a complete plan or its first, unfinished step."""
    errors: list[str] = []
    for name, parameter in parameters.items():
        if parameter.source == "printed":
            unknown = [span for span in parameter.span_ids if span not in printed]
            if unknown:
                errors.append(f"parametre {name!r}: kanıtta olmayan ölçü kaydına atıf {unknown}")
                continue
            if parameter.value is None:
                continue
            records = [printed[span] for span in parameter.span_ids]
            foreign = [(record.get("span_id"), record.get("unit")) for record in records
                       if parameter.unit != "count" and record.get("unit")
                       and str(record["unit"]) != str(parameter.unit)]
            if foreign:
                errors.append(f"parametre {name!r}: atıf yapılan ölçünün birimi parametreden farklı "
                              f"({parameter.unit}): {foreign}")
                continue
            if not any(_prints_value(record, parameter.value, parameter.unit) for record in records):
                shown = [(record.get("span_id"), record.get("value"), record.get("count"))
                         for record in records]
                errors.append(f"parametre {name!r}={parameter.value}: atıf yapılan ölçüler bu değeri "
                              f"yazmıyor (span, değer, adet): {shown}")
        elif parameter.source == "assumed" and not parameter.explanation:
            errors.append(f"parametre {name!r}: varsayımın gerekçesi yok")
    return errors


def _prints_value(record: dict, value: float, unit: str = "mm") -> bool:
    """A dimension and its repetition count are distinct quantities from the same callout."""
    candidate = (record.get("count") if unit == "count" and record.get("unit") != "count"
                 else record.get("value"))
    if unit == "count" and (not isinstance(candidate, (int, float))
                            or isinstance(candidate, bool) or candidate < 1
                            or not float(candidate).is_integer()):
        return False
    return (isinstance(candidate, (int, float)) and not isinstance(candidate, bool)
            and abs(candidate - value) <= max(1e-9, 1e-6 * abs(value)))


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
    for error in exc.errors(include_url=False):
        where = ".".join(str(item) for item in error["loc"])
        message = str(error["msg"]).removeprefix("Value error, ")
        if error["type"] == "string_pattern_mismatch" and error.get("input") is not None:
            # Pydantic's own wording for the pattern ("String should match pattern ...") does not say
            # which name was illegal; the record's first error has to be readable on its own.
            message = f"ad kuralına uymuyor ({NAME_PATTERN}): {error['input']!r}"
        parts.append(f"{where}: {message}" if where else message)
    return "şema hatası: " + "; ".join(parts) if parts else "şema hatası"
