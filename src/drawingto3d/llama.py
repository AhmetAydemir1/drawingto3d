"""Local llama-server client. No host other than 127.0.0.1."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from drawingto3d.errors import UnavailableModel

PROMPT = (
    "Generate the CADQuery code needed to create the CAD for the provided image. "
    "Just the code, no other words."
)

# The instruct build of qwen3-vl is the one a number reader wants. Ollama's bare `qwen3-vl:8b` tag is
# the *thinking* build (same model layer as `qwen3-vl:8b-thinking`), and a thinking build spends the
# reader's 12-token budget on reasoning instead of the number, so the tag is named in full here.
# qwen2.5vl stays behind it as the fallback for a box that has not pulled the newer weights.
VISION_MODELS = ("qwen3-vl:8b-instruct", "qwen2.5vl:7b", "qwen2.5vl:3b")
CODER_MODELS = ("qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:3b")


def retry_prompt(code: str, error: str) -> str:
    return (
        "The CadQuery program failed. Fix it. Use the millimetre numbers printed on the drawing. "
        "Assign the finished solid to a variable named solid. Return only Python code.\n\n"
        f"Problem:\n{error}\n\nProgram:\n{code}\n\n"
        "Write a new program that does not repeat this mistake. Change the failing line."
    )


class OllamaVision:
    """Local vision model answers one short question about one crop. Unloaded with release()."""

    def __init__(self, host: str | None = None, timeout: float = 180) -> None:
        raw = host or os.environ.get("DRAWINGTO3D_OLLAMA_URL", "http://127.0.0.1:11434")
        self.host = _local_origin(raw)
        self.timeout = timeout
        self.model = _pick(_ollama_names(self.host), VISION_MODELS)

    def ask(self, image_png: bytes, prompt: str, predict: int = 12) -> str:
        return _ollama_chat(self.host, self.model, prompt, image_png, self.timeout, predict, temperature=0.0)

    def release(self) -> None:
        """keep_alive 0: drop the weights so the code model fits in memory."""
        _ollama_unload(self.host, self.model)


class OllamaCoder:
    """Local code model writes a short geo.* program from the dimension records. No image."""

    def __init__(self, host: str | None = None, timeout: float = 300) -> None:
        raw = host or os.environ.get("DRAWINGTO3D_OLLAMA_URL", "http://127.0.0.1:11434")
        self.host = _local_origin(raw)
        self.timeout = timeout
        self.model = _pick(_ollama_names(self.host), CODER_MODELS)

    def complete(self, prompt: str) -> str:
        return _ollama_chat(self.host, self.model, prompt, None, self.timeout, 700)

    def release(self) -> None:
        _ollama_unload(self.host, self.model)


def _ollama_names(host: str) -> set[str]:
    request = urllib.request.Request(host + "/api/tags")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
    return {str(item.get("name", "")) for item in body.get("models", [])}


def _pick(names: set[str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in names:
            return candidate
    raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez")


def _ollama_unload(host: str, model: str) -> None:
    payload = {"model": model, "messages": [], "keep_alive": 0}
    request = urllib.request.Request(
        host + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except (urllib.error.URLError, TimeoutError):
        return


def _ollama_chat(
    host: str,
    model: str,
    prompt: str,
    image_png: bytes | None,
    timeout: float,
    predict: int,
    temperature: float = 0.2,
    num_ctx: int = 16384,
) -> str:
    message: dict = {"role": "user", "content": prompt}
    if image_png is not None:
        message["images"] = [base64.standard_b64encode(image_png).decode("ascii")]
    payload = {
        "model": model,
        "stream": False,
        "messages": [message],
        "keep_alive": "5m",
        # num_ctx must be set: Ollama's default 4096 is smaller than one whole-sheet image, and the
        # 400 it returns ("exceeds the available context size") is not a model failure.
        "options": {"temperature": temperature, "num_predict": predict, "num_ctx": num_ctx},
    }
    request = urllib.request.Request(
        host + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").strip()
        raise UnavailableModel(f"yerel model isteği reddedildi ({exc.code}): {_short(detail)}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
    text = str(body.get("message", {}).get("content", ""))
    if not text.strip():
        raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez")
    return text


def _short(text: str, limit: int = 300) -> str:
    """One line of the provider's complaint, so a rejected request is not reported as silence."""
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("…" if len(collapsed) > limit else "")


class LlamaCoder:
    """Ortho2CAD via a local llama-server. Cloud hosts are rejected."""

    def __init__(self, host: str | None = None, timeout: float = 1500) -> None:
        raw = host or os.environ.get("DRAWINGTO3D_LLAMA_URL", "http://127.0.0.1:8080")
        self.host = _local_origin(raw)
        self.timeout = timeout

    def complete(self, image_png: bytes, prompt: str, max_tokens: int = 7680, repeat_penalty: float = 1.0) -> str:
        encoded = base64.standard_b64encode(image_png).decode("ascii")
        payload = {
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "repeat_penalty": repeat_penalty,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            self.host + "/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc


def _local_origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.scheme not in {"http", "https"}:
        raise UnavailableModel("bağlama yalnız yerel adrese gidebilir")
    return url.rstrip("/")
