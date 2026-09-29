"""Compare decoder enforcement with the old and corrected wire schemas, using identical prompts.

This is a contract diagnostic, not drawing reconstruction or CAD accuracy evaluation.
All answers, schemas and prompt hashes are saved before proceeding to the next call.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pydantic import TypeAdapter, ValidationError

from drawingto3d.general import Operation, Parameter, Sketch
from drawingto3d.llama import ChatSettings, OllamaChat, find_model, installed_models
from drawingto3d.planner import _sha256_text, step_reply_schema
from model_baseline import ResourceSampler, _atomic_json, code_record


PROBES = {
    "parameters": (
        "Return one parameter named hole_diameter for a printed 6.8 mm hole dimension, span d4. "
        "Use source printed, unit mm, value 6.8, and also include expr equal to '6.8'. "
        "Return just a JSON object with parameters."
    ),
    "profile": (
        "Return one sketch named disk, plane XY, offset '0', with one circular entity at "
        "['0','0'] and radius '5'. Omit the entity's type field. Return only JSON with sketches."
    ),
    "operations": (
        "Return one repeat operation id copies, output copies_body, input seed_body. "
        "Include both linear (x_pitch '10', x_count 2) and circular (axis Z, count 2). "
        "Omit the op field. Set result to copies_body. Return JSON with operations and result."
    ),
}


def validate(step: str, answer: str) -> dict:
    try:
        payload = json.loads(answer)
        key, target = {
            "parameters": ("parameters", dict[str, Parameter]),
            "profile": ("sketches", dict[str, Sketch]),
            "operations": ("operations", list[Operation]),
        }[step]
        TypeAdapter(target).validate_python(payload[key])
    except (ValueError, KeyError, TypeError) as exc:
        detail = str(exc)
        if isinstance(exc, ValidationError):
            detail = str(exc.errors(include_url=False, include_input=False))
        return {"contract_valid": False, "error": detail}
    return {"contract_valid": True, "scope": "leaf contract only; no drawing/citation/geometry check"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="saved full/steps v2 schema snapshot")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="qwen2.5vl:3b")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output already exists; choose a new path")
    old = json.loads(args.before.read_text())
    old_steps = old["steps"] if "steps" in old else old["schemas"]["v2"]
    schemas = {"v2": old_steps, "v3": {step: step_reply_schema(step) for step in PROBES}}
    settings = ChatSettings(model=args.model, num_ctx=8192, num_predict=700, timeout=180, temperature=0)
    model = find_model(installed_models(), args.model)
    chat = OllamaChat(model.name, settings=settings)
    record = {"scope": "decoder constraint probes; prompts intentionally conflict with the contract",
              "code": code_record(), "model": model.as_dict(), "settings": settings.as_dict(),
              "schemas": schemas, "results": [], "status": "running"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sampler = ResourceSampler()
    sampler.start()
    _atomic_json(args.out, record)
    try:
        for step, prompt in PROBES.items():
            for version, grammars in schemas.items():
                record["active"] = {"step": step, "version": version}
                _atomic_json(args.out, record)
                schema = grammars[step]
                stats = {}
                start = time.monotonic()
                answer = chat.complete(prompt, response_format=schema, stats=stats)
                row = {"step": step, "schema_version": version, "prompt": prompt,
                       "prompt_sha256": _sha256_text(prompt),
                       "schema_sha256": _sha256_text(json.dumps(schema, sort_keys=True)),
                       "answer": answer, "stats": stats, "seconds": round(time.monotonic() - start, 2),
                       **validate(step, answer)}
                record["results"].append(row)
                record["resources"] = sampler.record()
                _atomic_json(args.out, record)
                print(step, version, row["contract_valid"], row["seconds"], flush=True)
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
