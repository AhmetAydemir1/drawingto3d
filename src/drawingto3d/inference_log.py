"""Model çağrılarının kaydı — adapter sınırında, cümle değil kanıt.

Baseline raporu "model çalıştı" diyorsa bunun kanıtı bir açıklama cümlesi olamaz: çağrının kendisi,
hangi adapter üzerinden, görüntü gidip gitmediği ve hangi model/ayarla yapıldığı kaydedilmelidir. Kayıt,
çağrıyı yapan nesnenin **sarmalayıcısında** tutulur (`OllamaChat`, `OllamaVision`, `OllamaCoder`,
`LlamaCoder`); böylece ürün kodu değişmeden, çağrı sayısı ve görüntü durumu ölçülmüş olur.

Alt sınıf kullanılıyor, sarmalayıcı nesne değil: `reason._ask` çağrıyı `isinstance(model, LlamaCoder)`
ile seçiyor, dolayısıyla tipin korunması gerekiyor.

Kayıt her çağrıdan sonra diske yazılır: koşu zaman aşımına uğrasa ya da süreç ağacı öldürülse bile
"kaç çağrı yapıldı, görüntü gitti mi" sorusu cevaplanabilir kalır.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from drawingto3d.llama import LlamaCoder, OllamaChat, OllamaCoder, OllamaVision

SCHEMA = "drawingto3d.inference-log/1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class Recorder:
    """Tek bir koşunun model çağrılarını tutar ve her çağrıdan sonra diske yazar."""

    def __init__(self, path: Path | None = None, *, label: str = "") -> None:
        self.path = Path(path) if path is not None else None
        self.label = label
        self.calls: list[dict] = []
        self.models: dict[str, dict] = {}
        # Kanıt dosyası baştan yazılır: "çağrı olmadı" da bir ölçümdür. Dosya hiç yoksa satır
        # `inference_called: null` kalırdı ve "kanıt yok" ile "çağrı yok" karışırdı.
        self.write()

    def describe(self, kind: str, model: object, settings: dict | None = None) -> None:
        """Adapter'ı tanıt: hangi model, hangi ayar. Çağrı sayılmaz."""
        record: dict = {"kind": kind}
        model_label = getattr(model, "model", None)
        if isinstance(model_label, str):
            record["model"] = model_label
        if settings is None:
            reader = getattr(model, "settings_record", None)
            if callable(reader):
                try:
                    found = reader()
                except Exception:  # pragma: no cover - tanıtım kanıtı çağrıyı durdurmamalı
                    found = None
                settings = found if isinstance(found, dict) else None
        if isinstance(settings, dict):
            record["settings"] = settings
        self.models[kind] = record

    def note(self, kind: str, *, image_sent: bool, image_bytes: int = 0, prompt_chars: int = 0,
             ok: bool | None = None, error: str | None = None) -> None:
        """Bir çağrıyı kaydet. `ok` verilmezse hata taşınmasına bakılır: hata varsa çağrı düşmüştür."""
        self.calls.append({"index": len(self.calls) + 1, "kind": kind, "at": _now(),
                           "image_sent": bool(image_sent), "image_bytes": int(image_bytes),
                           "prompt_chars": int(prompt_chars),
                           "ok": (error is None) if ok is None else bool(ok), "error": error})
        self.write()

    def as_record(self) -> dict:
        kinds = sorted({call["kind"] for call in self.calls})
        return {
            "schema": SCHEMA,
            "note": self.label,
            "calls": len(self.calls),
            "inference_called": bool(self.calls),
            "image_sent": any(call["image_sent"] for call in self.calls),
            "kinds": kinds,
            "models": self.models,
            "calls_detail": self.calls,
        }

    def write(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.as_record(), indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")


def read_record(path: Path) -> dict | None:
    """Bir kaydı oku; yok ya da çözülemezse None (kanıt yoksa 'çağrı oldu' denemez)."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def recording_raster_models(recorder: Recorder) -> tuple["RecordedVision", OllamaCoder | LlamaCoder]:
    """Raster kolun adapter'ları: paftayı okuyan model ve kod yazan model, ikisi de kayıtlı.

    Hangi kod modelinin kurulu olduğu kararı ürünün kendi seçicisine bırakılır (`reason._default_coder`);
    seçim için kurulan örnek, kayıtlı sarmalayıcı kurulduktan sonra serbest bırakılır ki iki kopya
    ağırlık bellekte durmasın.
    """
    from drawingto3d.reason import _default_coder

    chosen = _default_coder()
    try:
        if isinstance(chosen, LlamaCoder):
            coder: OllamaCoder | LlamaCoder = RecordedLlamaCoder(recorder=recorder)
        else:
            coder = RecordedCoder(recorder=recorder)
    finally:
        release = getattr(chosen, "release", None)
        if callable(release):
            release()
    return RecordedVision(recorder=recorder), coder


def _note_prompt(recorder: Recorder, text: str) -> int:
    return len(text) if isinstance(text, str) else 0


class RecordedChat(OllamaChat):
    """`OllamaChat.complete`: metin ve (verilirse) görüntü — çağrı burada kaydedilir."""

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("chat", self)

    def complete(self, prompt: str, image_png: bytes | None = None, num_predict: int | None = None,
                 response_format: dict | str | None = None, stats: dict | None = None) -> str:
        try:
            reply = super().complete(prompt, image_png=image_png, num_predict=num_predict,
                                     response_format=response_format, stats=stats)
        except Exception as error:
            self._recorder.note("chat", image_sent=image_png is not None, error=repr(error),
                                prompt_chars=_note_prompt(self._recorder, prompt),
                                image_bytes=len(image_png or b""))
            raise
        self._recorder.note("chat", image_sent=image_png is not None,
                            image_bytes=len(image_png or b""),
                            prompt_chars=_note_prompt(self._recorder, prompt))
        return reply


class RecordedVision(OllamaVision):
    """`OllamaVision.ask`: her çağrı görüntü taşır."""

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("vision", self)

    def ask(self, image_png: bytes, prompt: str, predict: int = 12) -> str:
        try:
            reply = super().ask(image_png, prompt, predict=predict)
        except Exception as error:
            self._recorder.note("vision", image_sent=True, image_bytes=len(image_png or b""),
                                prompt_chars=_note_prompt(self._recorder, prompt), error=repr(error))
            raise
        self._recorder.note("vision", image_sent=True, image_bytes=len(image_png or b""),
                            prompt_chars=_note_prompt(self._recorder, prompt))
        return reply


class RecordedCoder(OllamaCoder):
    """`OllamaCoder.complete`: metin kodu ister, görüntü göndermez."""

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("coder", self)

    def complete(self, prompt: str) -> str:
        try:
            reply = super().complete(prompt)
        except Exception as error:
            self._recorder.note("coder", image_sent=False,
                                prompt_chars=_note_prompt(self._recorder, prompt), error=repr(error))
            raise
        self._recorder.note("coder", image_sent=False,
                            prompt_chars=_note_prompt(self._recorder, prompt))
        return reply


class RecordedLlamaCoder(LlamaCoder):
    """`LlamaCoder.complete`: kod isterken pafta görüntüsünü de gönderir."""

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("coder", self)

    def complete(self, image_png: bytes, prompt: str, max_tokens: int = 7680,
                 repeat_penalty: float = 1.0) -> str:
        try:
            reply = super().complete(image_png, prompt, max_tokens=max_tokens,
                                     repeat_penalty=repeat_penalty)
        except Exception as error:
            self._recorder.note("coder", image_sent=True, image_bytes=len(image_png or b""),
                                prompt_chars=_note_prompt(self._recorder, prompt), error=repr(error))
            raise
        self._recorder.note("coder", image_sent=True, image_bytes=len(image_png or b""),
                            prompt_chars=_note_prompt(self._recorder, prompt))
        return reply
