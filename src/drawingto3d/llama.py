"""Local llama-server client. No host other than 127.0.0.1.

Three clients live here, in the order the pipeline grows:

  `OllamaVision`  one short question about one crop (a printed number, a role)
  `OllamaCoder`   a short `geo.*` program written from plain-text dimension records
  `LlamaCoder`    free Python for a whole sheet through a local llama-server

`OllamaChat` is the one the measurement harness uses: every setting that changes an answer
(model tag, context length, sampling, output limit, keep_alive) is an argument of the run and is
reported back by `settings()`, so a run's record says what produced it instead of what happened to
be installed. `installed_models()` reports the weights the machine actually holds. Existing
clients keep their behaviour; nothing here picks a model silently for a run it did not describe.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from drawingto3d.errors import UnavailableModel

PROMPT = (
    "Generate the CADQuery code needed to create the CAD for the provided image. "
    "Just the code, no other words."
)

# What this machine is likely to hold, best first. These are preferences, not a gate: a run names its
# model explicitly (`find_model`) and the product takes whatever is installed that can do the job.
# The instruct build of qwen3-vl is the one a number reader wants. Ollama's bare `qwen3-vl:8b` tag is
# the *thinking* build (same model layer as `qwen3-vl:8b-thinking`), and a thinking build spends the
# reader's 12-token budget on reasoning instead of the number, so the tag is named in full here.
VISION_MODELS = ("qwen3-vl:8b-instruct", "qwen2.5vl:7b", "qwen2.5vl:3b")
CODER_MODELS = ("qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:3b")
# Only for a server too old to report capabilities: a family name that reads images.
VISION_NAME_HINTS = ("vl", "vision", "llava", "gemma3", "minicpm-v", "moondream")


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
        self.model = choose_vision_model(self.host)

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
        self.model = choose_text_model(self.host)

    def complete(self, prompt: str) -> str:
        return _ollama_chat(self.host, self.model, prompt, None, self.timeout, 700)

    def release(self) -> None:
        _ollama_unload(self.host, self.model)


def _vision_capable(models: list[ModelInfo]) -> list[str]:
    """Installed tags that can read an image, best known first.

    The server's own `capabilities` decide it. A server too old to report them falls back to family
    names — and a machine with no vision model anywhere gets an empty list, never a text model that
    would answer an image with fluent nonsense.
    """
    reporting = [model for model in models if model.capabilities]
    if reporting:
        capable = [model.name for model in reporting if "vision" in model.capabilities]
    else:
        capable = [model.name for model in models
                   if any(hint in model.name.lower() for hint in VISION_NAME_HINTS)]
    for candidate in VISION_MODELS:
        if candidate in capable:
            return [candidate] + [name for name in capable if name != candidate]
    return capable


def choose_vision_model(host: str | None = None, env_var: str = "DRAWINGTO3D_VISION_MODEL") -> str:
    """The tag this machine will read images with: the caller's choice, else the best installed one.

    An explicit choice (environment) is honoured exactly — an uninstalled tag is an error, not a
    silent substitution — so a measurement that names a model gets that model or nothing.
    """
    models = installed_models(host)
    wanted = os.environ.get(env_var)
    if wanted:
        return find_model(models, wanted).name
    capable = _vision_capable(models)
    if not capable:
        available = ", ".join(sorted(model.name for model in models)) or "(hiç yok)"
        raise UnavailableModel(f"kurulu modeller arasında görüntü okuyabilen yok ({available}); "
                               "akış kurallı okumayla sürer")
    return capable[0]


def choose_text_model(host: str | None = None, env_var: str = "DRAWINGTO3D_CODER_MODEL") -> str:
    """The tag this machine will write programs with: the caller's choice, else a coder if it has one,
    else any installed model. Text is the one job every model can do."""
    models = installed_models(host)
    wanted = os.environ.get(env_var)
    if wanted:
        return find_model(models, wanted).name
    if not models:
        raise UnavailableModel("Ollama'da kurulu model yok")
    capable = [model.name for model in models if not model.capabilities or "completion" in model.capabilities]
    for candidate in CODER_MODELS:
        if candidate in capable:
            return candidate
    named = [name for name in capable if "coder" in name.lower()]
    return (named or capable or [model.name for model in models])[0]


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
    response_format: dict | str | None = None,
    stats: dict | None = None,
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
    if response_format is not None:
        # Constrained decoding: the answer's *shape* is the product contract (a versioned plan), not a
        # hint to the model. Without it a 3B model answers a plan-shaped object with the wrong nesting
        # and the failure reads as "the model cannot plan".
        payload["format"] = response_format
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
    if stats is not None:
        stats.update({
            "done_reason": body.get("done_reason"),
            "eval_count": body.get("eval_count"),
            "prompt_eval_count": body.get("prompt_eval_count"),
            "total_duration_ns": body.get("total_duration"),
            "load_duration_ns": body.get("load_duration"),
        })
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


# --- what the machine holds, and what one run was told to use ------------------------


@dataclass(frozen=True)
class ModelInfo:
    """One installed weight set, as the local server describes it. The tag is part of the
    model — a thinking build under a different tag answers differently — so the digest is
    recorded beside the name and not instead of it."""

    name: str
    digest: str = ""
    size_bytes: int = 0
    parameter_size: str = ""
    quantization: str = ""
    context_length: int = 0
    families: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "size_gb": round(self.size_bytes / 1e9, 3),
            "parameter_size": self.parameter_size,
            "quantization": self.quantization,
            "context_length": self.context_length,
            "families": list(self.families),
            "capabilities": list(self.capabilities),
        }


def installed_models(host: str | None = None) -> list[ModelInfo]:
    """Every model the local Ollama holds, with the metadata a run record needs.

    Raises `UnavailableModel` when the local server cannot be reached: a missing dependency is
    reported as a missing dependency, never as a model that answered nothing.
    """
    origin = _local_origin(host or os.environ.get("DRAWINGTO3D_OLLAMA_URL", "http://127.0.0.1:11434"))
    request = urllib.request.Request(origin + "/api/tags")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").strip()
        raise UnavailableModel(f"yerel model listesi reddedildi ({exc.code}): {_short(detail)}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UnavailableModel("yerel model yanıt vermiyor; buluta düşülmez") from exc
    models: list[ModelInfo] = []
    for item in body.get("models", []):
        details = item.get("details") or {}
        models.append(
            ModelInfo(
                name=str(item.get("name", "")),
                digest=str(item.get("digest", "")),
                size_bytes=int(item.get("size") or 0),
                parameter_size=str(details.get("parameter_size", "")),
                quantization=str(details.get("quantization_level", "")),
                context_length=int(details.get("context_length") or 0),
                families=tuple(str(value) for value in details.get("families") or ()),
                capabilities=tuple(str(value) for value in item.get("capabilities") or ()),
            )
        )
    return models


def find_model(models: list[ModelInfo], wanted: str) -> ModelInfo:
    """The installed model whose tag is `wanted`. A prefix match is accepted for a tag written
    without its quantisation suffix, but an ambiguous prefix is refused rather than guessed."""
    exact = [model for model in models if model.name == wanted]
    if exact:
        return exact[0]
    partial = [model for model in models if model.name.startswith(wanted)]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        available = ", ".join(sorted(model.name for model in models)) or "(hiç yok)"
        raise UnavailableModel(f"istenen model kurulu değil: {wanted!r}; kurulu olanlar: {available}")
    raise UnavailableModel(
        f"model adı belirsiz: {wanted!r} -> " + ", ".join(sorted(model.name for model in partial))
    )


@dataclass
class ChatSettings:
    """Everything about a call that can change its answer, so a run record can name it."""

    model: str
    num_ctx: int = 16384
    temperature: float = 0.0
    num_predict: int = 512
    keep_alive: str = "5m"
    timeout: float = 300.0
    image_max_side: int | None = None
    images_per_call: int = 1
    response_format: str | None = None

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "num_predict": self.num_predict,
            "keep_alive": self.keep_alive,
            "timeout_s": self.timeout,
            "image_max_side": self.image_max_side,
            "images_per_call": self.images_per_call,
            "response_format": self.response_format or "text",
        }


class OllamaChat:
    """A local chat call whose settings are the caller's, not the installation's default.

    `OllamaVision` and `OllamaCoder` pick a model by preference order, which is right for the
    product path and wrong for a measurement: a run that compares two models has to say which one
    it asked. This client takes the model and the sampling explicitly and reports them back.
    """

    def __init__(self, model: str, host: str | None = None, settings: ChatSettings | None = None) -> None:
        raw = host or os.environ.get("DRAWINGTO3D_OLLAMA_URL", "http://127.0.0.1:11434")
        self.host = _local_origin(raw)
        self.settings = settings or ChatSettings(model=model)
        if self.settings.model != model:
            raise ValueError("ChatSettings.model ile verilen model uyuşmuyor")

    @property
    def model(self) -> str:
        return self.settings.model

    def complete(self, prompt: str, image_png: bytes | None = None, num_predict: int | None = None,
                 response_format: dict | str | None = None, stats: dict | None = None) -> str:
        return _ollama_chat(
            self.host,
            self.settings.model,
            prompt,
            image_png,
            self.settings.timeout,
            self.settings.num_predict if num_predict is None else num_predict,
            temperature=self.settings.temperature,
            num_ctx=self.settings.num_ctx,
            response_format=response_format,
            stats=stats,
        )

    def unload(self) -> None:
        _ollama_unload(self.host, self.settings.model)

    def settings_record(self) -> dict:
        return self.settings.as_dict()
