"""Bind span ids to roles. A number that was not read cannot be emitted."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Protocol

from drawingto3d.schema import Binding, Question, Span

FEATURE_KINDS = ("length", "diameter", "radius", "angle", "height", "depth", "other")

PROMPT = """You look at one technical drawing and the numbers already read from it.
Name each number's role in the language of the drawing. Do not use a fixed part template.
Use only span_id values from the list. Copy value exactly from that span. Never invent a millimetre.
Do not reuse words from this instruction as a role name.
kind "length" is the single overall length of the part. Use it for one span only.
kind is one of: length, diameter, radius, angle, height, depth, other.
Return JSON with a features list. Each item has role, span_id, value, and kind.
"""


class SemanticBinder(Protocol):
    def bind(self, spans: list[Span], image: bytes | None = None) -> list[Binding]: ...


class UnavailableModel(RuntimeError):
    """Local vision model is not installed. Cloud fallback is not allowed."""


class OllamaBinder:
    """Local Ollama only. No network host other than 127.0.0.1."""

    def __init__(self, model: str = "qwen2.5vl:7b", host: str = "http://127.0.0.1:11434") -> None:
        if "127.0.0.1" not in host and "localhost" not in host:
            raise UnavailableModel("bağlama yalnız yerel adrese gidebilir")
        self.model = model
        self.fallback = "qwen2.5vl:3b" if model != "qwen2.5vl:3b" else None
        self.host = host.rstrip("/")

    def bind(self, spans: list[Span], image: bytes | None = None) -> list[Binding]:
        installed = self._installed()
        chosen = next((name for name in (self.model, self.fallback) if name and name in installed), None)
        if chosen is None:
            raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez")
        try:
            text = self._chat(chosen, spans, image)
            used = chosen
        except UnavailableModel as exc:
            cause = exc.__cause__
            # #region agent log
            _dbg("bind.py:bind", "primary model unavailable", {"model": self.model, "error": str(exc), "cause": type(cause).__name__ if cause else None, "cause_msg": str(cause) if cause else None, "span_count": len(spans), "image": bool(image)}, "B")
            # #endregion
            if self.fallback is None or self.fallback == chosen:
                raise
            try:
                text = self._chat(self.fallback, spans, image)
            except UnavailableModel as fallback_exc:
                fallback_cause = fallback_exc.__cause__
                # #region agent log
                _dbg("bind.py:bind", "fallback model unavailable", {"model": self.fallback, "error": str(fallback_exc), "cause": type(fallback_cause).__name__ if fallback_cause else None, "cause_msg": str(fallback_cause) if fallback_cause else None}, "B")
                # #endregion
                raise
            used = self.fallback
        parsed = _parse_model_json(text)
        kept = validate_bindings(parsed, spans)
        # #region agent log
        _dbg("bind.py:bind", "model prompt and output", {"model": used, "prompt": PROMPT, "span_ids": [span.id for span in spans], "span_values": [span.value for span in spans], "raw": text[:4000], "parsed": [item.model_dump() for item in parsed], "kept": [item.model_dump() for item in kept]}, "C")
        # #endregion
        return kept

    def _chat(self, model: str, spans: list[Span], image: bytes | None) -> str:
        # #region agent log
        _dbg("bind.py:_chat", "sending prompt", {"model": model, "host": self.host, "prompt": PROMPT, "span_count": len(spans), "span_values": [span.value for span in spans], "image": bool(image)}, "C")
        # #endregion
        message: dict = {
            "role": "user",
            "content": PROMPT + "\n" + json.dumps([span.model_dump() for span in spans], ensure_ascii=False),
        }
        if image:
            message["images"] = [base64.standard_b64encode(image).decode("ascii")]
        payload = {"model": model, "stream": False, "format": "json", "messages": [message]}
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
        return body.get("message", {}).get("content", "")

    def _installed(self) -> set[str]:
        request = urllib.request.Request(f"{self.host}/api/tags")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
        return {str(item.get("name", "")) for item in body.get("models", [])}


def _dbg(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    # #region agent log
    import time

    try:
        line = json.dumps({"sessionId": "23360b", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000), "runId": "fork"}, ensure_ascii=False)
        with open("/Users/aydemir/Desktop/drawingto3d/.cursor/debug-23360b.log", "a") as handle:
            handle.write(line + "\n")
    except OSError:
        return
    # #endregion


def validate_bindings(proposed: list[Binding], spans: list[Span]) -> list[Binding]:
    """Drop any value that is not exactly one of the read spans."""
    by_id = {span.id: span for span in spans}
    accepted: list[Binding] = []
    for binding in proposed:
        span = by_id.get(binding.span_id)
        if span is not None and span.value is not None and abs(span.value - binding.value) < 1e-6:
            accepted.append(binding)
            continue
        matches = [item for item in spans if item.value is not None and abs(item.value - binding.value) < 1e-6]
        if len(matches) == 1:
            binding.span_id = matches[0].id
            accepted.append(binding)
    return accepted


def reject_invented(proposed: list[dict], spans: list[Span]) -> list[Question]:
    known = {span.id: span.value for span in spans}
    questions: list[Question] = []
    for item in proposed:
        span_id = str(item.get("span_id", ""))
        try:
            value = float(item["value"])
        except (KeyError, TypeError, ValueError):
            questions.append(Question(role=str(item.get("role", "?")), reason="sayı okunamadı"))
            continue
        if span_id not in known or known[span_id] is None or abs(known[span_id] - value) > 1e-6:
            questions.append(
                Question(
                    role=str(item.get("role", "?")),
                    reason="listedeki bir span değil",
                    span_ids=[span_id] if span_id else [],
                )
            )
    return questions


def _parse_model_json(text: str) -> list[Binding]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return []
    data = json.loads(text[start : end + 1])
    items = data.get("features") or data.get("bindings") or []
    from drawingto3d.ingest import parse_dimension

    bindings = []
    for item in items:
        role = str(item.get("role", ""))
        kind = str(item.get("kind", "other"))
        if kind not in FEATURE_KINDS:
            kind = role if role in FEATURE_KINDS else "other"
        try:
            value = float(item["value"])
        except (KeyError, TypeError, ValueError):
            _, value = parse_dimension(str(item.get("value", "")))
            if value is None:
                continue
        bindings.append(
            Binding(
                role=role,
                span_id=str(item.get("span_id", "")),
                value=value,
                kind=kind,  # type: ignore[arg-type]
            )
        )
    return bindings
