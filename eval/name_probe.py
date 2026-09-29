"""Which name constraints a decoder grammar can carry here, measured on the provider itself.

The plan's contract requires CAD identifiers (`general.NAME_PATTERN`). Three places in a plan answer
carry a name, and they are not equally constrainable:

  * a *string field* that names a body or a sketch (`sketch`, `target`, `tool`, `input`, `ids`),
  * an *object key* (`parameters`, `sketches`),
  * a *closed vocabulary* of keys (the same object, spelled out).

JSON Schema can express all three (`pattern`, `propertyNames`, `enum` inside `propertyNames`). Whether
the *decoder* enforces them is a property of the provider, not of the schema, and the answer decides
what the interface has to do about a name that arrives illegal. So each question is asked twice: once
with the constraint and once without it, same prompt, same settings. The difference between the two
answers is the constraint's effect; if a control answer already complies there is nothing to read.

This measures the grammar, not the part. No drawing is read and no CAD is built.

    PYTHONPATH=src .venv/bin/python eval/name_probe.py --out eval/reports/name-probe-evidence.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d.general import NAME_PATTERN  # noqa: E402
from drawingto3d.llama import ChatSettings, OllamaChat, find_model, installed_models  # noqa: E402
from drawingto3d.planner import (  # noqa: E402
    _NAME_DEFINITIONS,
    _NAME_REFERENCE_FIELDS,
    _object_in,
    _sha256_text,
    plan_reply_schema,
)
from model_baseline import ResourceSampler, _atomic_json, code_record  # noqa: E402

NAME_RE = re.compile(NAME_PATTERN)
# A name the contract rejects, in the two ways the recorded answers produced: a capital and a hyphen.
ILLEGAL = "Hole_Spacing-X"

_VALUE = {"type": "number"}
_PARAMETERS = {"type": "object", "additionalProperties": _VALUE}


def _object(*, constrained: bool) -> dict:
    schema = {"type": "object", "properties": {"parameters": json.loads(json.dumps(_PARAMETERS))},
              "required": ["parameters"], "additionalProperties": False}
    if constrained:
        schema["properties"]["parameters"]["propertyNames"] = {"pattern": NAME_PATTERN}
    return schema


def _vocabulary(*, constrained: bool) -> dict:
    """A closed key vocabulary: the schema names every key the answer may use."""
    parameters: dict = {"type": "object", "additionalProperties": {"type": "string"}}
    if constrained:
        parameters["properties"] = {"hole_spacing_x": {"type": "string"}}
        parameters["additionalProperties"] = False
    return {"type": "object", "properties": {"parameters": parameters},
            "required": ["parameters"], "additionalProperties": False}


def _pattern_properties(*, constrained: bool) -> dict:
    schema = {"type": "object", "properties": {"parameters": json.loads(json.dumps(_PARAMETERS))},
              "required": ["parameters"], "additionalProperties": False}
    if constrained:
        schema["properties"]["parameters"] = {"type": "object",
                                              "patternProperties": {NAME_PATTERN: _VALUE},
                                              "additionalProperties": False}
    return schema


def _string_field(*, constrained: bool) -> dict:
    """`result` as the plan declares it: a body name the contract checks with the same pattern."""
    name: dict = {"type": "string"}
    if constrained:
        name["pattern"] = NAME_PATTERN
    return {"type": "object", "properties": {"result": name}, "required": ["result"],
            "additionalProperties": False}


PROBES = {
    "string-field": {
        "schema": _string_field,
        "how": "`pattern` on a string field (`result`)",
        "prompt": f"Return the finished body's name exactly as {ILLEGAL!r}. Answer JSON only.",
        "reads": lambda payload: [str(payload["result"])] if payload.get("result") else [],
    },
    "property-names": {
        "schema": _object,
        "how": "`propertyNames.pattern` on an object (`parameters`)",
        "prompt": f"Return one parameter, keyed exactly {ILLEGAL!r}, with the string value '100'. "
                  "Answer JSON only.",
        "reads": lambda payload: [str(key) for key in (payload.get("parameters") or {})],
    },
    "property-names-enum": {
        "schema": _vocabulary,
        "how": "a closed key vocabulary (`properties` + `additionalProperties: false`)",
        "prompt": f"Return one parameter, keyed exactly {ILLEGAL!r} with value '100'. Answer JSON only.",
        "reads": lambda payload: [str(key) for key in (payload.get("parameters") or {})],
    },
    "pattern-properties": {
        "schema": _pattern_properties,
        "how": "`patternProperties` with `additionalProperties: false`",
        "prompt": f"Return one parameter, keyed exactly {ILLEGAL!r} with the value 100. Answer JSON only.",
        "reads": lambda payload: [str(key) for key in (payload.get("parameters") or {})],
    },
}


def verdict(names: list[str]) -> dict:
    """`legal` says the decoder kept the illegal name out *and* answered something."""
    illegal = [name for name in names if not NAME_RE.fullmatch(name)]
    return {"names": names, "illegal_names": illegal, "legal": bool(names) and not illegal}


def wire_name_fields() -> dict:
    """What the reply schema the run actually sends says about each place a plan names something."""
    schema = plan_reply_schema()
    definitions = schema.get("$defs", {})
    fields = {}
    for operation, names in _NAME_REFERENCE_FIELDS.items():
        definition = definitions.get(_NAME_DEFINITIONS[operation], {})
        # A union definition carries its properties in each branch (`RepeatOp`).
        branches = definition.get("oneOf") or [definition]
        fields[operation] = {field: [branch.get("properties", {}).get(field) for branch in branches]
                             for field in names}
    fields["fuse"] = {"inputs.items": definitions.get("FuseOp", {}).get("properties", {})
                      .get("inputs", {}).get("items")}
    return {
        "property_names": {key: schema["properties"][key].get("propertyNames")
                           for key in ("parameters", "sketches")},
        "reference_fields": fields,
        "result": schema["properties"]["result"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="qwen2.5vl:3b")
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--predict", type=int, default=200)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"çıktı zaten var; yeni yol seç: {args.out}")

    model = find_model(installed_models(), args.model)
    settings = ChatSettings(model=model.name, num_ctx=args.num_ctx, num_predict=args.predict,
                            timeout=180, temperature=0)
    chat = OllamaChat(model.name, settings=settings)
    record = {
        "scope": "decoder constraints on a name, measured with and without each constraint; "
                 "no drawing read, no CAD built",
        "provider": "ollama",
        "code": code_record(),
        "model": model.as_dict(),
        "settings": settings.as_dict(),
        "name_pattern": NAME_PATTERN,
        "requested_illegal_name": ILLEGAL,
        "wire": wire_name_fields(),
        "results": [],
        "status": "running",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sampler = ResourceSampler()
    sampler.start()
    _atomic_json(args.out, record)
    try:
        for probe, spec in PROBES.items():
            for variant in ("control", "constrained"):
                schema = spec["schema"](constrained=variant == "constrained")
                record["active"] = {"probe": probe, "variant": variant}
                _atomic_json(args.out, record)
                stats: dict = {}
                start = time.monotonic()
                try:
                    answer = chat.complete(spec["prompt"], response_format=schema, stats=stats)
                    failure = None
                except Exception as exc:  # a refused request is a result, not a crash
                    answer, failure = "", f"{type(exc).__name__}: {exc}"
                payload: dict = {}
                if answer.strip():
                    payload = _object_in(answer) or {}
                reading = spec["reads"](payload)
                row = {
                    "probe": probe,
                    "variant": variant,
                    "constraint": spec["how"],
                    "prompt": spec["prompt"],
                    "prompt_sha256": _sha256_text(spec["prompt"]),
                    "schema_sha256": _sha256_text(json.dumps(schema, sort_keys=True)),
                    "schema": schema,
                    "answer": answer,
                    "request_error": failure,
                    "stats": stats,
                    "seconds": round(time.monotonic() - start, 2),
                    "names": reading,
                    "verdict": verdict(reading),
                }
                record["results"].append(row)
                record["resources"] = sampler.record()
                _atomic_json(args.out, record)
                print(f"{probe:<22} {variant:<12} {row['verdict']['names']} {row['seconds']}s",
                      flush=True)
        record["status"] = "complete"
        record["active"] = None
    except BaseException as exc:
        record["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        record["error"] = str(exc)
        raise
    finally:
        sampler.stop()
        record["resources"] = sampler.record()
        _atomic_json(args.out, record)
        chat.unload()


if __name__ == "__main__":
    main()
