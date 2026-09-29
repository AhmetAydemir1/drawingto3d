"""Model çağrılarının kaydı — adapter sınırında, cümle değil kanıt.

Baseline raporu "model çalıştı" diyorsa bunun kanıtı bir açıklama cümlesi olamaz: çağrının kendisi, hangi
adapter üzerinden, görüntü **istekte** var mıydı, çağrı döndü mü, hangi model/ayarla yapıldı. Kayıt,
çağrıyı yapan nesnenin sarmalayıcısında tutulur (`OllamaChat`, `OllamaVision`, `OllamaCoder`,
`LlamaCoder`); ürün kodu değişmeden çağrı sayısı ve görüntü durumu ölçülmüş olur. Alt sınıf kullanılıyor,
sarmalayıcı nesne değil: `reason._ask` çağrıyı `isinstance(model, LlamaCoder)` ile seçiyor, yani tipin
korunması gerekiyor.

Üç kural bu dosyanın varlık sebebi:

1. **Çağrıdan önce yazılır.** Her deneme adapter'a girmeden `started` olarak diske yazılır; dönüşte aynı
   `call_id` `completed`/`failed` olur. Süreç zaman aşımında öldürülürse kayıt `unfinished` kalır ve
   "kesilen çağrı" ile "hiç çağrı yok" birbirine karışmaz. (Önceki sürüm yalnız dönüşte yazdığı için
   kesilen bir çağrı kayıtta `calls: 0` görünüyordu.)
2. **Yazım atomik.** Dosya yanına yazılıp `os.replace` ile yerine konur; öldürülen bir süreç yarım JSON
   bırakmaz.
3. **Kayıt yolu komut başına ayrıdır** (`inference-log-read.json`, `-build.json`, …). Aynı yolu paylaşan
   iki komut birbirinin kanıtını ezerdi: `read` kaydı, ardından gelen `build` tarafından siliniyordu.

Ölçülen sınır dürüst yazılır: `image_attached` isteğin görüntü taşıdığını söyler, `server_ok` çağrının
hatasız döndüğünü söyler. Sunucunun görüntüyü *kullandığı* buradan anlaşılmaz; bu kayıt o iddiayı
kurmuş sayılmaz.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from drawingto3d.llama import LlamaCoder, OllamaChat, OllamaCoder, OllamaVision

SCHEMA = "drawingto3d.inference-log/2"
STARTED = "started"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class Recorder:
    """Bir komutun model çağrılarını tutar ve her adımda diske yazar."""

    def __init__(self, path: Path | None = None, *, label: str = "") -> None:
        self.path = Path(path) if path is not None else None
        self.label = label
        self.opened_at = _now()
        self.calls: list[dict] = []
        self.models: dict[str, dict] = {}
        # Kanıt dosyası baştan yazılır: "çağrı olmadı" da bir ölçümdür, "kanıt yok" değil.
        self.write()

    # -- adapter tanıtımı -------------------------------------------------

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
        self.write()

    # -- çağrının iki ucu -------------------------------------------------

    def started(self, kind: str, *, image_attached: bool = False, image_bytes: int = 0,
                prompt_chars: int = 0) -> str:
        """Adapter'a girmeden **önce** yazılır; dönen `call_id` ile çağrı kapatılır."""
        call_id = f"{len(self.calls) + 1:04d}"
        self.calls.append({"call_id": call_id, "kind": kind, "state": STARTED,
                           "started_at": _now(), "finished_at": None,
                           "image_attached": bool(image_attached), "image_bytes": int(image_bytes),
                           "prompt_chars": int(prompt_chars), "server_ok": None, "error": None})
        self.write()
        return call_id

    def finished(self, call_id: str, *, server_ok: bool = True, error: str | None = None) -> None:
        """Çağrıyı kapat: hatasız döndüyse `completed`, hata ile bittiyse `failed`."""
        for call in self.calls:
            if call["call_id"] == call_id:
                call["state"] = "completed" if error is None else "failed"
                call["finished_at"] = _now()
                call["server_ok"] = bool(server_ok) if error is None else False
                call["error"] = error
                break
        self.write()

    def note(self, kind: str, *, image_attached: bool = False, image_bytes: int = 0,
             prompt_chars: int = 0, error: str | None = None) -> str:
        """Tek adımlık kayıt (açılış ve kapanış aynı yerde): kısa yollar ve testler için."""
        call_id = self.started(kind, image_attached=image_attached, image_bytes=image_bytes,
                               prompt_chars=prompt_chars)
        self.finished(call_id, server_ok=error is None, error=error)
        return call_id

    # -- kayıt ------------------------------------------------------------

    def as_record(self) -> dict:
        attempts = len(self.calls)
        return {
            "schema": SCHEMA,
            "note": self.label,
            "opened_at": self.opened_at,
            "closed_at": _now(),
            "attempts": attempts,
            "completed": sum(1 for call in self.calls if call["state"] == "completed"),
            "failed": sum(1 for call in self.calls if call["state"] == "failed"),
            "unfinished": sum(1 for call in self.calls if call["state"] == STARTED),
            "inference_called": attempts > 0,
            "image_attached": any(call["image_attached"] for call in self.calls),
            "server_ok": any(call["server_ok"] is True for call in self.calls),
            "kinds": sorted({call["kind"] for call in self.calls}),
            "models": self.models,
            "calls": self.calls,
        }

    def write(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        scratch = self.path.with_name(self.path.name + ".tmp")
        scratch.write_text(json.dumps(self.as_record(), indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        os.replace(scratch, self.path)


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


def merge_records(records: list[dict]) -> dict:
    """Adım kayıtlarını kol özetine çevir: her komut kendi dosyasını yazar, özet hepsini birleştirir.

    `unfinished` ayrı sayılır ve `server_ok` yalnız hatasız dönen bir çağrı varsa true olur; "istek
    görüntü taşıdı" (`image_attached`) ile "sunucu kabul etti" aynı alanda birleştirilmez.
    """
    calls = [call for record in records for call in (record.get("calls") or [])]
    return {
        "records": len(records),
        "attempts": len(calls),
        "completed": sum(1 for call in calls if call.get("state") == "completed"),
        "failed": sum(1 for call in calls if call.get("state") == "failed"),
        "unfinished": sum(1 for call in calls if call.get("state") == STARTED),
        "inference_called": bool(calls),
        "image_attached": any(call.get("image_attached") for call in calls),
        "server_ok": any(call.get("server_ok") is True for call in calls),
        "kinds": sorted({call.get("kind") for call in calls if call.get("kind")}),
        "models": {kind: model for record in records for kind, model in (record.get("models") or {}).items()},
    }


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


class _Recorded:
    """Sarmalayıcıların ortak kitabı: çağrıyı aç, iç adapter'a gir, sonucu yaz."""

    _recorder: Recorder
    _kind: str = "model"

    def _enter(self, prompt, image_png: bytes | None) -> str:
        return self._recorder.started(self._kind, image_attached=image_png is not None,
                                      image_bytes=len(image_png or b""),
                                      prompt_chars=len(prompt) if isinstance(prompt, str) else 0)

    def _leave(self, call_id: str, error: BaseException | None) -> None:
        # BaseException'ı da kapatır (KeyboardInterrupt dâhil): kesilen çağrı kayıtta `failed` olur.
        # Süreç öldürülürse zaten yazılmış `started` kaydı diskte kalır ve `unfinished` sayılır.
        self._recorder.finished(call_id, server_ok=error is None,
                                error=None if error is None else repr(error))


class RecordedChat(_Recorded, OllamaChat):
    """`OllamaChat.complete`: metin ve (verilirse) görüntü — çağrı burada kaydedilir."""

    _kind = "chat"

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("chat", self)

    def complete(self, prompt: str, image_png: bytes | None = None, num_predict: int | None = None,
                 response_format: dict | str | None = None, stats: dict | None = None) -> str:
        call_id = self._enter(prompt, image_png)
        error: BaseException | None = None
        try:
            return super().complete(prompt, image_png=image_png, num_predict=num_predict,
                                    response_format=response_format, stats=stats)
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._leave(call_id, error)


class RecordedVision(_Recorded, OllamaVision):
    """`OllamaVision.ask`: çağrı görüntü taşır."""

    _kind = "vision"

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("vision", self)

    def ask(self, image_png: bytes, prompt: str, predict: int = 12) -> str:
        call_id = self._enter(prompt, image_png)
        error: BaseException | None = None
        try:
            return super().ask(image_png, prompt, predict=predict)
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._leave(call_id, error)


class RecordedCoder(_Recorded, OllamaCoder):
    """`OllamaCoder.complete`: metin kodu ister, görüntü göndermez."""

    _kind = "coder"

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("coder", self)

    def complete(self, prompt: str) -> str:
        call_id = self._enter(prompt, None)
        error: BaseException | None = None
        try:
            return super().complete(prompt)
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._leave(call_id, error)


class RecordedLlamaCoder(_Recorded, LlamaCoder):
    """`LlamaCoder.complete`: kod isterken pafta görüntüsünü de gönderir."""

    _kind = "coder"

    def __init__(self, *args, recorder: Recorder, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recorder = recorder
        self._recorder.describe("coder", self)

    def complete(self, image_png: bytes, prompt: str, max_tokens: int = 7680,
                 repeat_penalty: float = 1.0) -> str:
        call_id = self._enter(prompt, image_png)
        error: BaseException | None = None
        try:
            return super().complete(image_png, prompt, max_tokens=max_tokens,
                                    repeat_penalty=repeat_penalty)
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._leave(call_id, error)
