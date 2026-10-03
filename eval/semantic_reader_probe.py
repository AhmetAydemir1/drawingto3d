"""SEMREAD-001A probe: sabit fixture'lar, dört gerçek yerel çağrı, runner altında kanıt paketi.

Bu sürücü ürün başarısı ölçmez. Ölçtüğü şey taşıma zinciri: kaynak → hazırlanan görseller (ham
sayfa/overlay/crop) → gerçek çoklu görsel isteği → şema/referans doğrulaması → benzersiz attempt
dizininde yazılı kanıt.

Sınırlar (goal sözleşmesi):

* Runner kökü mevcut ortak `out/lab`'dır; bu dizin (`out/lab/semread-001a`) yalnız **rapor köküdür**,
  ikinci bir kilit kurulmaz.
* Tek ağır iş, vaka başına en fazla 600 sn, koşu 7200 sn ve bu dar goal boyunca **en fazla 8 gerçek
  inference çağrısı**. Sayaç `state.json` içinde tutulur ve attempt/batch değiştirerek sıfırlanmaz.
* Fixture'lar çağrıdan **önce** sabitlenir (diske yazılır, sha256'sı vakaya girer); altın cevap ve
  komşu STEP yalnız evaluator tarafında kalır, reader'ın girdisine girmez.
* `--dry-run` hiçbir model çağrısı yapmaz ve hiçbir şey yazmaz (runner'ın kendi dry-run yolu).

Kullanım:

    python eval/semantic_reader_probe.py --dry-run
    python eval/semantic_reader_probe.py --live --cases L1,L2,L3,L4
    python eval/semantic_reader_probe.py --evaluate

Runner, her vakayı kendi alt sürecinde `--worker` ile çalıştırır; worker kanıtı attempt dizinine yazar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from drawingto3d.errors import UnavailableModel  # noqa: E402
from drawingto3d.inference_log import RecordedChat, Recorder  # noqa: E402
from drawingto3d.llama import LAYOUTS, ChatSettings, find_model, installed_models  # noqa: E402
from drawingto3d.observe import observe  # noqa: E402
from drawingto3d.semantic_images import (  # noqa: E402
    open_source,
    overlay_from_observations,
    prepare_crop,
    prepare_full_page,
)
from drawingto3d.semantic_reader import SemanticReader, leak_check, probe_prompt  # noqa: E402
from drawingto3d.semantic_schema import ImageBundle, probe_json_schema  # noqa: E402
from drawingto3d_lab import LAB_VERSION  # noqa: E402
from drawingto3d_lab.runner import WATCHED_FILES, Job, LabRunner  # noqa: E402
from drawingto3d_lab.state import code_fingerprint, read_json, sha256_file, write_json  # noqa: E402

EXIT_OK, EXIT_INPUT, EXIT_BUDGET, EXIT_MODEL = 0, 2, 3, 4

CASE_SCHEMA = "semread-001a-case/1"
EVALUATION_SCOPE = "semread-001a-transport"
LIVE_CALL_LIMIT = 8                      # ilk goal'in gerçek inference tavanı
# Sınır kayıtta tutulur, kodda gizlenmez. İlk uzatma L1–L4'ün geçerli/izlenebilir canlı kanıtı için
# yapıldı (8 -> 12). Bu devam goal'i **kümülatif tavanı 18'e** çıkarır: başlangıçta 11 çağrı
# kullanılmıştı. Onaltı, tam beş çağrıya (L1..L5) yer bırakıyordu ama tek bir zaman aşımı bile
# tekrar denemeyi imkânsız kılardı; iki çağrılık pay bilinçli olarak eklendi ve raporda "kalan"
# alanıyla birlikte görünür.
LIVE_CALL_LIMIT_EXTENDED = 12
LIVE_CALL_LIMIT_REASON = ("L1–L4 için geçerli/izlenebilir canlı kanıt istenmesi: önceki attempt'ler "
                          "image_id ve ölçülmüş boyut içermeyen kayıtlarla üretilmişti")
LIVE_CALL_LIMIT_CONTINUATION = 18
LIVE_CALL_LIMIT_CONTINUATION_REASON = (
    "devam goal'i: (1) nötr kimliği görsel mesajında taşıyan düzenle L1/L2 kimlik eşlemesini tamir "
    "etmek, (2) aynı iki görsele image-11/image-27 vererek kimliğe bağımlılığı sınamak (L5), "
    "(3) okuma sözleşmesi v2'ye çıktığı için önceki sürümle üretilmiş L1–L4 kanıtı bayatladı — dört "
    "vaka yeniden ölçülür. Kümülatif tavan 18 = 11 kullanılmış + 5 gerekli + 2 tekrar payı")
CASE_TIMEOUT_SECONDS = 600               # limitlerden daha sıkı olanı uygulanır
RUN_TIMEOUT_SECONDS = 7200
MODEL_TIMEOUT_SECONDS = 300              # HTTP zaman aşımı vaka bütçesinin yarısı: kesilme kaydedilebilsin

# Devam paketinin kendi dizini: eski kanıt **hiç değiştirilmeden** durur, yeni test/eval/kabul/rapor
# paketi buradaki benzersiz dizine yazılır. Paylaşılan runner kökü yine `out/lab`.
CONTINUATION_ID = "semread-001a-identity-20261004"

# Yeni untracked semantic kodu: `code_fingerprint` tracked dosyaları kapsar, bunlar kapsamaz.
SEMANTIC_WATCHED = ("src/drawingto3d/semantic_schema.py", "src/drawingto3d/semantic_images.py",
                    "src/drawingto3d/semantic_reader.py", "eval/semantic_reader_probe.py")

# Test/eval kanıtının **içerik kimliği** bu dosyalardan hesaplanır: ilgili kod, ilgili testler ve
# config. Dokümanlar (`docs/**`, devir notu) burada **yoktur** — yalnız bir Markdown eklemek kanıtı
# bayatlatmamalı. `git status` metni kimlik değildir: içerik hash'i okunur, `M` işareti okunmaz.
IDENTITY_SOURCE_GLOBS = ("src/drawingto3d/*.py", "src/drawingto3d_lab/*.py")
IDENTITY_CONFIG_FILES = ("eval/semantic_reader_probe.py", "pyproject.toml")

PLATE_PDF = ROOT / "examples" / "pdf with steps" / "5" / "Plate With A Pocket Drawing.PDF"
RASTER_DRAWING = ROOT / "examples" / "flange-elbow-90.png"

# Development'ta sabitlenmiş bölgeler (ürün kodunda örneğe özel kural yok; yalnız bu fixture'ın kaydı).
L3_CROP_BBOX = [0.30, 0.30, 0.42, 0.42]     # 600 dpi'da ~840x595 px: yeniden render, sonra resize yok
L4_CROP_BBOX = [0.10, 0.20, 0.90, 0.80]
FULL_PAGE_MAX_SIDE = 1024                   # bağlamı taşırmayan, kaydı tutulan politika

# Vaka şeması kapalıdır: altın/STEP etiketi gibi bir alan yanlışlıkla vakaya eklenirse burada düşer.
CASE_KEYS = frozenset({"schema", "case_id", "sources", "images", "payload_order", "forbidden_tokens",
                       "settings", "expected_images_per_call", "notes", "gold_file"})
IMAGE_KEYS = frozenset({"image_id", "kind", "source", "bbox_page_norm", "dpi", "resize_max_side"})
SOURCE_KEYS = frozenset({"path", "sha256", "page_index", "type"})
SETTING_KEYS = frozenset({"num_predict", "num_ctx", "temperature", "keep_alive", "timeout_s",
                          "image_max_side", "images_layout"})
# Görsellerin çoklu-görsel isteğinde nasıl çerçevelendiği. Sözleşme aynı: image ID ↔ gönderim sırası.
# Sözlük tek yerde (`drawingto3d.llama.LAYOUTS`): `single_message` tek mesajda N görsel,
# `per_image_message` görsel başına metinsiz mesaj, `per_image_message_labeled` görsel başına mesaj ve
# o mesajın metni **yalnız nötr kaynak kimliği** (`Image ID: image-2`). Ölçüm: tek mesajda iki yakın
# görsel bu backend'de ayrışmadı; görsel başına mesajda kimlik bağlandı ama L2'de model ilan edilen
# permütasyonu yok saydı. Etiketli düzen kimliği görselin kendi mesajına taşır — kaynak metadata'sı,
# cevap değil — ve tüm vakalara tek kural olarak uygulanır.
GOLD_KEYS = frozenset({"gold-sentinel", "shapes", "min_valid_regions", "expected_shapes"})

DEFAULT_SETTINGS = {"num_predict": 384, "num_ctx": 16384, "temperature": 0.0, "keep_alive": "5m",
                    "timeout_s": 300.0, "image_max_side": None,
                    "images_layout": "per_image_message_labeled"}


# ---------------------------------------------------------------- yollar


def report_root(base: Path | None = None) -> Path:
    return Path(base) if base is not None else ROOT / "out/lab/semread-001a"


def cases_dir(base: Path | None = None) -> Path:
    return report_root(base) / "cases"


def fixtures_dir(base: Path | None = None) -> Path:
    return report_root(base) / "fixtures"


def gold_dir(base: Path | None = None) -> Path:
    return report_root(base) / "gold"


def state_path(base: Path | None = None) -> Path:
    return report_root(base) / "state.json"


def acceptance_path(base: Path | None = None) -> Path:
    return report_root(base) / "acceptance.json"


def model_lock_path(base: Path | None = None) -> Path:
    return report_root(base) / "model-lock.json"


# ---------------------------------------------------------------- durum


def load_state(base: Path | None = None) -> dict:
    payload = read_json(state_path(base), default=None)
    if not isinstance(payload, dict):
        payload = {"schema": "semread-001a-state/1", "live_calls": [], "cases": {}, "blocked": None,
                   "next_command": None}
    payload.setdefault("live_calls", [])
    payload.setdefault("cases", {})
    return payload


def _identity_files() -> list[str]:
    """Kanıt kimliğine giren **ilgili** dosyalar: kod, testler, config. Dokümanlar burada yok."""
    names: set[str] = set(IDENTITY_CONFIG_FILES)
    for pattern in IDENTITY_SOURCE_GLOBS:
        names.update(str(path.relative_to(ROOT)) for path in sorted(ROOT.glob(pattern)))
    names.update(TEST_SUITES["semantic"])
    names.update(TEST_SUITES["regression"])
    return sorted(names)


def _environment_identity() -> dict:
    """Test ortamı kimliği: aynı kod başka bir Python/pytest sürümünde aynı kanıt değildir."""
    import platform  # noqa: PLC0415

    try:
        import pytest  # noqa: PLC0415

        pytest_version = pytest.__version__
    except ImportError:  # pragma: no cover - pytest yoksa kanıt zaten üretilemez
        pytest_version = "yok"
    return {"python": platform.python_version(), "pytest": pytest_version,
            "platform": platform.platform(), "implementation": platform.python_implementation()}


def test_command_identity() -> dict:
    """Kanıt komutu da kimliğin parçası: komut değişirse eski sonuç yeni komutu kapatmaz."""
    return {name: [sys.executable, "-m", "pytest", *TEST_SUITES[name], "-q"]
            for name in sorted(TEST_SUITES)}


def identity_detail() -> dict:
    """Kimliğin içeriği: hangi dosyalar hangi hash'le, hangi komut, hangi ortam."""
    files = {}
    for relative in _identity_files():
        path = ROOT / relative
        files[relative] = (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists()
                           else "yok")
    return {"files": files, "commands": test_command_identity(), "environment": _environment_identity()}


def evidence_identity(detail: dict | None = None) -> str:
    """İçerikten hesaplanan kanıt kimliği: `git status` metni değil, dosyaların kendisi.

    Neden böyle: (a) `docs/**.md` gibi bir doküman eklemek test kanıtını bayatlatmamalı, (b) `M`
    işaretli bir kaynak dosyanın **içeriği** değiştiğinde kanıt bayatlamalı. Bu yüzden karşılaştırma
    git durumuna değil, ilgili dosyaların + komutun + ortamın içeriğine bakar.
    """
    detail = detail if detail is not None else identity_detail()
    digest = hashlib.sha256()
    for relative in sorted(detail["files"]):
        digest.update(f"{relative}\0{detail['files'][relative]}\0".encode())
    digest.update(json.dumps(detail["commands"], sort_keys=True, ensure_ascii=False).encode())
    digest.update(json.dumps(detail["environment"], sort_keys=True, ensure_ascii=False).encode())
    return digest.hexdigest()


def continuation_dir(base: Path | None = None) -> Path:
    return report_root(base) / "continuations" / CONTINUATION_ID


def preserve_start_copies(base: Path | None = None) -> dict:
    """Eski rapor/kabul/state'i **değiştirmeden** bir kopyasını sakla (üzerine yazmaz).

    Devam paketi eski kanıtı sahiplenmez: başlangıç kopyaları hash'leriyle birlikte yazılır, böylece
    \"bu rapor güncellendi\" demek \"önceki kanıt kayboldu\" demek olmaz.
    """
    target = continuation_dir(base) / "start"
    target.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    for name, path in (("report.md", report_root(base) / "final" / "report.md"),
                       ("acceptance.json", acceptance_path(base)),
                       ("state.json", state_path(base))):
        if not path.exists():
            continue
        copy = target / name
        if not copy.exists():  # ilk kopya korunur; ikinci kez üzerine yazılmaz
            copy.write_bytes(path.read_bytes())
        manifest[name] = {"source": str(path), "copy": str(copy),
                          "sha256_at_start": sha256_file(copy)}
    write_json(target / "start-copies.json",
               {"schema": "semread-001a-start-copies/1", "continuation_id": CONTINUATION_ID,
                "recorded_at": _now(), "files": manifest})
    return manifest


def save_state(state: dict, base: Path | None = None) -> Path:
    state["schema"] = "semread-001a-state/1"
    state["updated_at"] = _now()
    state.setdefault("live_call_limit", LIVE_CALL_LIMIT)
    # `head`/`working_tree` yalnız **bilgi** olarak yazılır; kanıt kimliği onlardan türetilmez.
    state["head"] = _git("rev-parse", "HEAD")
    state["working_tree"] = _git("status", "--porcelain")
    detail = identity_detail()
    state["identity_method"] = ("içerik: ilgili kod+test+config dosyaları, test komutu ve ortam "
                                "(git durum metni kimlik değildir)")
    state["identity_files"] = sorted(detail["files"])
    state["evidence_identity"] = evidence_identity(detail)
    state["environment"] = detail["environment"]
    state["evaluator_identity"] = state["evidence_identity"]
    state["working_tree_sha256"] = state["evidence_identity"]
    state["code_identity"] = code_identity()
    return write_json(state_path(base), state)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _rss_bytes() -> int | None:
    """Bu alt sürecin kendi RSS'i (ölçüm kapsamı açıkça yazılır; toplam RAM denmez)."""
    try:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ValueError, OSError):  # pragma: no cover - platform hatası
        return None
    return value if sys.platform == "darwin" else value * 1024


# ---------------------------------------------------------------- fixture'lar


def _encode(image: np.ndarray) -> bytes:
    import cv2  # noqa: PLC0415 - fixture üretimi dışında gerekmez

    ok, encoded = cv2.imencode(".png", image)
    if not ok:  # pragma: no cover
        raise SystemExit("fixture png kodlanamadı")
    return encoded.tobytes()


def shape_fixtures(base: Path | None = None) -> tuple[Path, Path]:
    """L1/L2'nin nötr görselleri: bir büyük üçgen, bir büyük kare. Bir kez yazılır, değişmez.

    Fixture çağrıdan önce sabitlenir: ikinci koşuda dosya zaten varsa yeniden üretilmez, çünkü
    üretimi tekrarlamak "aynı fixture" iddiasını sessizce başka bir dosyaya çevirirdi.
    """
    import cv2  # noqa: PLC0415

    directory = fixtures_dir(base) / "L1"
    triangle = directory / "shape-a.png"
    square = directory / "shape-b.png"
    if triangle.exists() and square.exists():
        return triangle, square
    directory.mkdir(parents=True, exist_ok=True)
    size, margin = 512, 90
    canvas = np.full((size, size, 3), 255, dtype=np.uint8)
    points = np.array([[size // 2, margin], [margin, size - margin], [size - margin, size - margin]],
                      dtype=np.int32)
    triangle.write_bytes(_encode(cv2.fillPoly(canvas.copy(), [points], (30, 30, 30))))
    square.write_bytes(_encode(cv2.rectangle(canvas.copy(), (margin, margin),
                                             (size - margin, size - margin), (30, 30, 30), -1)))
    return triangle, square


def _source_record(path: Path, *, page_index: int = 0) -> dict:
    source = open_source(path, page_index=page_index)
    return {"path": str(path), "sha256": source.sha256, "page_index": page_index,
            "type": source.source_type}


def case_definition(case_id: str, base: Path | None = None) -> dict:
    """Vakanın verisi: hangi kaynak, hangi görseller, hangi sıra. Görseller burada hazırlanmaz."""
    settings = dict(DEFAULT_SETTINGS)
    if case_id in ("L1", "L2", "L5"):
        triangle, square = shape_fixtures(base)
        # L5 kimlik kontrolüdür: **aynı iki görsel**, yalnız kimlikler nötr biçimde yeniden verilir
        # (image-11/image-27). Beklenen eşleme yalnız evaluator'ın altın dosyasında durur; böylece
        # "model sabit image-1/image-2 cevabına mı yaslanıyor" sorusu ölçülebilir.
        if case_id == "L5":
            images = [{"image_id": "image-11", "kind": "full_page", "source": "shape-a"},
                      {"image_id": "image-27", "kind": "full_page", "source": "shape-b"}]
            order = ["image-11", "image-27"]
            notes = ("kimlik kontrolü: L1/L2'nin aynı iki görseli yeni nötr kimliklerle; beklenen "
                     "eşleme yalnız evaluator altınında")
        else:
            images = [{"image_id": "image-1", "kind": "full_page", "source": "shape-a"},
                      {"image_id": "image-2", "kind": "full_page", "source": "shape-b"}]
            order = ["image-1", "image-2"] if case_id == "L1" else ["image-2", "image-1"]
            notes = "nötr görseller: bir büyük üçgen, bir büyük kare; prompt içeriği söylemez"
        return {
            "schema": CASE_SCHEMA, "case_id": case_id,
            "sources": {"shape-a": _source_record(triangle), "shape-b": _source_record(square)},
            "images": images, "payload_order": order,
            "forbidden_tokens": ["shape-a.png", "shape-b.png", "STEP", "part.step"],
            "settings": settings, "expected_images_per_call": 2,
            "gold_file": str(gold_dir(base) / f"{case_id}.json"),
            "notes": notes,
        }
    if case_id == "L3":
        return {
            "schema": CASE_SCHEMA, "case_id": case_id,
            "sources": {"plate": _source_record(PLATE_PDF)},
            "images": [
                {"image_id": "image-1", "kind": "full_page", "source": "plate",
                 "resize_max_side": FULL_PAGE_MAX_SIDE},
                {"image_id": "image-2", "kind": "overlay", "source": "plate",
                 "resize_max_side": FULL_PAGE_MAX_SIDE},
                {"image_id": "image-3", "kind": "crop", "source": "plate",
                 "bbox_page_norm": L3_CROP_BBOX, "dpi": 600.0},
            ],
            "payload_order": ["image-1", "image-2", "image-3"],
            "forbidden_tokens": ["Plate With A Pocket Drawing.PDF", "plate with a pocket.STEP", "STEP"],
            "settings": settings, "expected_images_per_call": 3,
            "gold_file": str(gold_dir(base) / "L3.json"),
            "notes": "ham sayfa 200 dpi (1024 px'e küçültülür), gözlem overlay'i, 600 dpi crop",
        }
    if case_id == "L4":
        return {
            "schema": CASE_SCHEMA, "case_id": case_id,
            "sources": {"raster": _source_record(RASTER_DRAWING)},
            "images": [
                {"image_id": "image-1", "kind": "full_page", "source": "raster"},
                {"image_id": "image-2", "kind": "crop", "source": "raster",
                 "bbox_page_norm": L4_CROP_BBOX},
            ],
            "payload_order": ["image-1", "image-2"],
            "forbidden_tokens": ["flange-elbow-90.png", "STEP"],
            "settings": settings, "expected_images_per_call": 2,
            "gold_file": str(gold_dir(base) / "L4.json"),
            "notes": "raster kaynak: ham kodlanmış kare + native crop (büyütme yok)",
        }
    raise SystemExit(f"bilinmeyen vaka: {case_id}")


def case_ids() -> tuple[str, ...]:
    """L1/L2 asıl kimlik eşlemesi, L3/L4 çizim taşıması, L5 kimlik bağımlılığı kontrolü."""
    return ("L1", "L2", "L3", "L4", "L5")


# A01–A12 asıl kabul satırlarıdır; A13 devam goal'inin ek kimlik kontrolüdür ve **genelleme iddiası
# değildir**: yalnız "aynı iki görsel yeni nötr kimliklerle de doğru bağlanıyor" sorusunu ölçer.
CONTROL_ROWS = ("A13",)


def _validate_case(case: dict) -> None:
    """Kapalı şema: altın/STEP alanı vakaya sızarsa burada düşer (sentinel denetimi)."""
    unknown = set(case) - CASE_KEYS
    if unknown:
        raise SystemExit(f"vaka şemasında tanımsız alan: {sorted(unknown)}")
    if case.get("schema") != CASE_SCHEMA:
        raise SystemExit(f"vaka şeması bilinmiyor: {case.get('schema')!r}")
    for entry in case.get("images") or []:
        extra = set(entry) - IMAGE_KEYS
        if extra:
            raise SystemExit(f"{case.get('case_id')}: görsel kaydında tanımsız alan: {sorted(extra)}")
    for name, source in (case.get("sources") or {}).items():
        extra = set(source) - SOURCE_KEYS
        if extra:
            raise SystemExit(f"{case.get('case_id')}: {name} kaynağında tanımsız alan: {sorted(extra)}")
    extra_settings = set(case.get("settings") or {}) - SETTING_KEYS
    if extra_settings:
        raise SystemExit(f"{case.get('case_id')}: bilinmeyen ayar: {sorted(extra_settings)}")
    layout = (case.get("settings") or {}).get("images_layout")
    if layout is not None and layout not in LAYOUTS:
        raise SystemExit(f"{case.get('case_id')}: bilinmeyen görsel çerçevelemesi: {layout!r}")
    order = list(case.get("payload_order") or [])
    ids = [entry["image_id"] for entry in case.get("images") or []]
    if sorted(order) != sorted(ids):
        raise SystemExit(f"{case.get('case_id')}: payload_order görsellerle uyuşmuyor")


def build_bundle(case: dict) -> tuple[dict, ImageBundle]:
    """Vakadan kaynakları ve görselleri hazırla; dosyaların hash'i vakadaki kayıtla eşleşmeli."""
    _validate_case(case)
    sources = {}
    for name, record in case["sources"].items():
        path = Path(record["path"])
        if not path.exists():
            raise SystemExit(f"{case['case_id']}: kaynak yok: {path}")
        measured = sha256_file(path)
        if record.get("sha256") and measured != record["sha256"]:
            raise SystemExit(f"{case['case_id']}: {name} kaynağı vakadaki hash'le uyuşmuyor "
                             f"(vaka={record['sha256'][:12]}…, ölçülen={measured[:12]}…)")
        sources[name] = open_source(path, page_index=int(record.get("page_index") or 0))

    images = []
    for entry in case["images"]:
        source = sources[entry["source"]]
        resize = entry.get("resize_max_side")
        if entry["kind"] == "full_page":
            images.append(prepare_full_page(source, entry["image_id"], resize_max_side=resize))
        elif entry["kind"] == "crop":
            images.append(prepare_crop(source, entry["image_id"], entry["bbox_page_norm"],
                                       dpi=float(entry.get("dpi") or 600.0),
                                       resize_max_side=resize))
        elif entry["kind"] == "overlay":
            observations = observe(source.path)
            images.append(overlay_from_observations(observations, entry["image_id"], source=source,
                                                    resize_max_side=resize))
        else:
            raise SystemExit(f"{case['case_id']}: bilinmeyen görsel türü: {entry['kind']}")
    bundle = ImageBundle(images, order=list(case["payload_order"]))
    if len(bundle) != int(case["expected_images_per_call"]):
        raise SystemExit(f"{case['case_id']}: beklenen görsel sayısı tutmuyor")
    return sources, bundle


# ---------------------------------------------------------------- model kilidi


def ollama_runtime_version(host: str = "http://127.0.0.1:11434") -> str | None:
    try:
        with urllib.request.urlopen(host + "/api/version", timeout=5) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    return str(payload.get("version")) if isinstance(payload, dict) else None


def model_lock(model: str, *, host: str | None = None) -> dict:
    """Kurulu tek vision modelini tam tag/digest'le sabitle; uygun model yoksa açıkça söyle."""
    models = installed_models(host)
    found = find_model(models, model)
    return {"schema": "semread-001a-model-lock/1", "model": found.name, "digest": found.digest,
            "size_bytes": found.size_bytes, "parameter_size": found.parameter_size,
            "quantization": found.quantization, "capabilities": list(found.capabilities),
            "runtime_version": ollama_runtime_version(),
            "recorded_at": _now()}


def unreadable_lock(model: str, reason: str) -> dict:
    """Yerel sunucu okunamadıysa: uydurma digest yok, engel açıkça yazılır."""
    return {"schema": "semread-001a-model-lock/1", "model": model, "digest": None,
            "runtime_version": None, "unavailable_reason": reason, "recorded_at": _now()}


def default_model() -> str:
    """Kurulu en iyi vision modeli: kıyaslama yok, tek model seçilir ve sabitlenir."""
    from drawingto3d.llama import choose_vision_model

    return choose_vision_model()


# ---------------------------------------------------------------- iş listesi


def code_identity() -> str:
    watched = [ROOT / name for name in WATCHED_FILES + SEMANTIC_WATCHED]
    return code_fingerprint(ROOT, watched)


def effective_limit(state: dict) -> int:
    """Yürürlükteki çağrı tavanı: uzatma yapıldıysa **kayıtta** yazar, kodda saklanmaz."""
    return int(state.get("live_call_limit") or LIVE_CALL_LIMIT)


def extend_budget(base: Path | None = None, limit: int = LIVE_CALL_LIMIT_EXTENDED,
                  reason: str = LIVE_CALL_LIMIT_REASON) -> dict:
    """Tavanı yükselt ve **neden**ini kayda geç; düşürmek reddedilir (kanıt geriye küçülemez)."""
    state = load_state(base)
    current = effective_limit(state)
    if limit < current:
        raise SystemExit(f"tavan düşürülemez: {current} -> {limit}")
    state["live_call_limit"] = int(limit)
    state.setdefault("budget_extensions", []).append(
        {"from": current, "to": int(limit), "reason": reason, "at": _now(),
         "used_before": len(state["live_calls"])})
    save_state(state, base)
    return {"limit": int(limit), "from": current, "reason": reason}


def make_jobs(cases: list[dict], lock: dict, *, lab_root: Path, base: Path | None = None,
              timeout: int = CASE_TIMEOUT_SECONDS) -> list[Job]:
    jobs = []
    for case in cases:
        case_file = cases_dir(base) / f"{case['case_id']}-case.json"
        inputs = [case_file, model_lock_path(base),
                  cases_dir(base) / f"{case['case_id']}-prompt.txt",
                  cases_dir(base) / f"{case['case_id']}-response-schema.json"]
        inputs += [Path(record["path"]) for record in case["sources"].values()]
        settings = case["settings"]
        command = [
            sys.executable, str(Path(__file__).resolve()), "--worker",
            "--case-file", str(case_file),
            "--model", lock["model"], "--model-digest", str(lock.get("digest") or "unknown"),
            "--runtime", str(lock.get("runtime_version") or "unknown"),
            "--report-root", str(report_root(base)),
            "--num-predict", str(settings["num_predict"]),
            "--num-ctx", str(settings["num_ctx"]),
            "--temperature", str(settings["temperature"]),
            "--keep-alive", str(settings["keep_alive"]),
            "--images-layout", str(settings["images_layout"]),
            "--timeout", str(settings["timeout_s"]),
            # Runner'ın kendi yer tutucuları: attempt dizini ve sonuç yolu tek kaynaktan gelir.
            "--attempt-dir", "{run_dir}",
            "--result", "{result}",
        ]
        if settings.get("image_max_side"):
            command += ["--image-max-side", str(settings["image_max_side"])]
        unique = {str(item): item for item in inputs}
        jobs.append(Job(id=f"semread-001a-{case['case_id'].lower()}", command=command,
                        inputs=[unique[key] for key in sorted(unique)], timeout_seconds=timeout,
                        notes=f"SEMREAD-001A {case['case_id']}: transport-only acceptance"))
    return jobs


def require_inputs(jobs: list[Job]) -> None:
    """Eksik required input hash'ten **önce** reddedilir (sessizce atlanmaz)."""
    missing = [str(path) for job in jobs for path in job.inputs if not Path(path).exists()]
    if missing:
        raise SystemExit("eksik zorunlu girdi: " + ", ".join(sorted(set(missing))))


def prepare_case_files(cases: list[dict], base: Path | None = None) -> None:
    """Vaka dosyası, prompt ve şemayı çağrıdan önce diske yaz: hash'e giren şey gönderilen şeydir."""
    cases_dir(base).mkdir(parents=True, exist_ok=True)
    for case in cases:
        _validate_case(case)
        _, bundle = build_bundle(case)
        prompt = probe_prompt(bundle)
        (cases_dir(base) / f"{case['case_id']}-prompt.txt").write_text(prompt, encoding="utf-8")
        write_json(cases_dir(base) / f"{case['case_id']}-response-schema.json", probe_json_schema())
        write_json(cases_dir(base) / f"{case['case_id']}-case.json", case)


def write_gold(base: Path | None = None) -> dict:
    """Altın cevap **yalnız evaluator tarafında**: reader'ın girdisine hiçbir biçimde girmez.

    Sınıf sözlüğü (triangle/square/…) sözleşmedir ve prompt'ta açıkça yazılıdır; altın olan şey
    **kimlik→sınıf eşlemesidir** ve yalnız burada durur. Sentinel denetimi de bu yüzden çıplak sınıf
    adını değil, eşleme izini arar (bkz. `_gold_isolation`).
    """
    directory = gold_dir(base)
    directory.mkdir(parents=True, exist_ok=True)
    golds = {
        "L1": {"case_id": "L1", "gold-sentinel": "gold-sentinel-7f3ac1",
               "shapes": {"image-1": "triangle", "image-2": "square"}, "min_valid_regions": 0},
        "L2": {"case_id": "L2", "gold-sentinel": "gold-sentinel-7f3ac1",
               "shapes": {"image-1": "triangle", "image-2": "square"}, "min_valid_regions": 0},
        "L5": {"case_id": "L5", "gold-sentinel": "gold-sentinel-7f3ac1",
               "shapes": {"image-11": "triangle", "image-27": "square"}, "min_valid_regions": 0},
        "L3": {"case_id": "L3", "gold-sentinel": "gold-sentinel-7f3ac1", "shapes": {},
               "min_valid_regions": 1},
        "L4": {"case_id": "L4", "gold-sentinel": "gold-sentinel-7f3ac1", "shapes": {},
               "min_valid_regions": 1},
    }
    for case_id, payload in golds.items():
        write_json(directory / f"{case_id}.json", payload)
    return golds


# ---------------------------------------------------------------- worker


def _write_artifacts(directory: Path, *, case: dict, bundle: ImageBundle, prompt: str,
                     schema: dict, outcome: dict, resources: dict) -> dict:
    """Attempt dizinine kanıt paketini yaz; en sonda dosya hash'lerini içeren index."""
    images_dir = directory / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for image in bundle.images:
        (images_dir / f"{image.image_id}.png").write_bytes(image.png)
    write_json(directory / "input-manifest.json",
               bundle.manifest(source={"case_id": case["case_id"],
                                       "sources": {name: record["sha256"]
                                                   for name, record in case["sources"].items()},
                                       "page_index": 0},
                               notes=[case.get("notes") or ""]))
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(directory / "response-schema.json", schema)
    write_json(directory / "request-manifest.json", outcome.get("request") or {})
    write_json(directory / "reference-checks.json",
               {"schema": "semread-001a-reference-checks/1", "case_id": case["case_id"],
                "reference": outcome.get("reference") or {},
                "leakage": outcome.get("leakage") or []})
    write_json(directory / "resources.json", resources)
    if outcome.get("raw_response") is not None or outcome.get("raw_body") is not None:
        write_json(directory / "response-raw.json",
                   {"schema": "semread-001a-raw-response/1",
                    "content": outcome.get("raw_response"), "body": outcome.get("raw_body")})
    if outcome.get("failure_kind"):
        write_json(directory / "response-error.json",
                   {"schema": "semread-001a-response-error/1",
                    "kind": outcome.get("failure_kind"), "detail": outcome.get("failure_detail")})
    if isinstance(outcome.get("parsed"), dict):
        write_json(directory / "response-parsed.json", outcome["parsed"])

    verdict, gates = transport_verdict(case, outcome)
    result = {
        "product_verdict": verdict,
        "job": f"semread-001a-{case['case_id'].lower()}",
        "case_id": case["case_id"],
        "evaluation_scope": EVALUATION_SCOPE,
        "semantic_evaluation": "not_evaluated",
        "cad_evaluation": "not_evaluated",
        "not_evaluated_note": "Bu vaka yalnız görsel taşıma ve yapısal yanıt kapılarını ölçer: "
                              "çizimin doğru okunduğu ya da doğru STEP üretildiği iddia edilmez.",
        "gates": gates,
        "failure_kind": outcome.get("failure_kind"),
        "images_per_call": (outcome.get("request") or {}).get("images_per_call"),
        "reason": ("taşıma kapıları geçti" if verdict == "pass"
                   else f"taşıma kapısı geçmedi: {outcome.get('failure_kind') or gates}"),
    }
    write_json(directory / "result.json", result)
    write_json(directory / "artifact-index.json", artifact_index(directory))
    return result


def transport_verdict(case: dict, outcome: dict) -> tuple[str, dict]:
    """Taşıma kapıları: gönderilen liste, ham yanıt, parse, şema, referans, kapsam ve kesilme durumu.

    Kesilme kapısı katıdır: `truncated` değilse yetinilmez, `complete` **ve** tamamlanma metadata'sı
    (done_reason + token sayımları) gerekir. `unknown` (metadata gelmedi) canlı kabulü geçirmez.
    """
    request = outcome.get("request") or {}
    truncated = outcome.get("truncated") or {}
    coverage = (outcome.get("reference") or {}).get("coverage") or {}
    gates = {
        "images_sent_as_expected": request.get("images_per_call") == case["expected_images_per_call"],
        "request_has_hash": bool(request.get("request_sha256")),
        "request_has_image_ids": bool(request.get("images")) and all(
            entry.get("image_id") for entry in request.get("images") or []),
        "messages_layout_recorded": bool(request.get("messages_layout")),
        "raw_answer_recorded": outcome.get("raw_response") is not None,
        "parsed": bool((outcome.get("parse") or {}).get("ok")),
        "schema_valid": bool((outcome.get("schema") or {}).get("ok")),
        "references_valid": bool((outcome.get("reference") or {}).get("ok")),
        "coverage_exact": coverage.get("exact") is True,
        "not_truncated": truncated.get("state") == "complete",
        "completion_metadata": truncated.get("metadata_complete") is True,
        "no_leakage": not (outcome.get("leakage") or []),
        "transport_ok": request.get("outcome") == "ok",
    }
    return ("pass" if all(gates.values()) else "fail"), gates


def artifact_index(directory: Path) -> dict:
    """Attempt dizinindeki dosyaların varlık+hash kaydı (runner marker'ı yalnız result'ı hash'ler)."""
    entries = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "artifact-index.json":
            entries[str(path.relative_to(directory))] = {"sha256": sha256_file(path),
                                                         "bytes": path.stat().st_size}
    return {"schema": "semread-001a-artifact-index/1", "files": entries,
            "file_count": len(entries), "recorded_at": _now()}


def verify_artifact_index(directory: Path) -> dict:
    """Index'teki her dosya var mı ve hash'i tutuyor mu? Eksik/fazla dosya da raporlanır.

    Runner'ın *kendi* yazdığı dosyalar (`manifest.json`, `complete.json`, `raw/**`) iş bittikten
    sonra attempt dizinine düşer; bunlar vaka kanıtı olmadığı için index dışı sayılmaz, ama index'in
    saymadığı başka bir dosya varsa kanıt tam sayılmaz.
    """
    index = read_json(directory / "artifact-index.json", default=None)
    if not isinstance(index, dict) or not index.get("files"):
        return {"ok": False, "reason": "artifact-index.json yok ya da boş", "entries": []}
    entries, problems = [], []
    for name, record in index["files"].items():
        path = directory / name
        if not path.exists():
            problems.append(f"eksik dosya: {name}")
            entries.append({"file": name, "exists": False, "sha256_matches": False})
            continue
        matches = sha256_file(path) == record.get("sha256")
        if not matches:
            problems.append(f"hash uyuşmuyor: {name}")
        entries.append({"file": name, "exists": True, "sha256_matches": matches})
    present = {str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file()}
    extra = sorted(name for name in present - set(index["files"]) - {"artifact-index.json"}
                   if not _runner_owned(name))
    if extra:
        problems.append(f"index dışı dosya: {', '.join(extra)}")
    return {"ok": not problems, "problems": problems, "entries": entries,
            "file_count": index.get("file_count")}


def _runner_owned(name: str) -> bool:
    """Runner'ın attempt dizinine kendi eklediği kanıt-dışı dosyalar (vaka kanıtı değil)."""
    return name in {"manifest.json", "complete.json"} or name.startswith("raw/")


def run_worker(args) -> int:
    case = json.loads(Path(args.case_file).read_text(encoding="utf-8"))
    directory = Path(args.attempt_dir)
    result_path = Path(args.result)
    directory.mkdir(parents=True, exist_ok=True)

    state = load_state(Path(args.report_root))
    limit = effective_limit(state)
    if len(state["live_calls"]) >= limit:
        print(json.dumps({"refused": "live call budget exhausted", "used": len(state["live_calls"]),
                          "limit": limit}, ensure_ascii=False))
        return EXIT_BUDGET

    try:
        sources, bundle = build_bundle(case)
    except BaseException as exc:  # noqa: BLE001 - girdi reddi kanıt olarak yazılır, yutulmaz
        write_json(directory / "response-error.json",
                   {"schema": "semread-001a-response-error/1", "kind": "input_refused",
                    "detail": f"{type(exc).__name__}: {exc}"})
        write_json(directory / "resources.json", {"input_refused": True})
        write_json(directory / "artifact-index.json", artifact_index(directory))
        print(json.dumps({"input_refused": str(exc)}, ensure_ascii=False))
        return EXIT_INPUT

    pinned_prompt = (cases_dir(Path(args.report_root)) /
                     f"{case['case_id']}-prompt.txt").read_text(encoding="utf-8")
    prompt = probe_prompt(bundle)
    if prompt != pinned_prompt:
        write_json(directory / "response-error.json",
                   {"schema": "semread-001a-response-error/1", "kind": "prompt_drift",
                    "detail": "diskteki prompt ile paketten üretilen prompt aynı değil"})
        write_json(directory / "artifact-index.json", artifact_index(directory))
        return EXIT_INPUT

    lock = read_json(model_lock_path(Path(args.report_root)), default={}) or {}
    installed = find_model(installed_models(), args.model)
    if installed.digest != args.model_digest:
        write_json(result_path, {
            "product_verdict": "fail", "case_id": case["case_id"],
            "evaluation_scope": EVALUATION_SCOPE, "semantic_evaluation": "not_evaluated",
            "cad_evaluation": "not_evaluated",
            "blocking_kind": "model_changed",
            "reason": f"kurulu model digest'i kilitli digest'ten farklı: {installed.digest[:12]}… != "
                      f"{args.model_digest[:12]}…",
            "gates": {"model_lock_matches": False}})
        return EXIT_MODEL

    # Çağrı sayacı çağrıdan **önce** yazılır: süreç öldürülürse "hiç çağrılmadı" görünmez.
    attempt_id = f"{case['case_id']}-{directory.name}"
    state = load_state(Path(args.report_root))
    state["live_calls"].append({"case_id": case["case_id"], "attempt": attempt_id,
                                "attempt_dir": str(directory), "model": args.model,
                                "started_at": _now(), "pid": os.getpid()})
    save_state(state, Path(args.report_root))

    settings = ChatSettings(model=args.model, num_ctx=int(args.num_ctx),
                            temperature=float(args.temperature), num_predict=int(args.num_predict),
                            keep_alive=args.keep_alive, timeout=float(args.timeout),
                            images_layout=args.images_layout,
                            image_max_side=(int(args.image_max_side)
                                            if args.image_max_side else None))
    recorder = Recorder(directory / "inference-log.json", label=f"semread-001a {case['case_id']}")
    chat = RecordedChat(args.model, settings=settings, recorder=recorder)
    started = time.perf_counter()
    outcome = SemanticReader(chat, num_predict=int(args.num_predict)).probe(
        bundle, forbidden=list(case["forbidden_tokens"]), images_layout=args.images_layout)
    wall = round(time.perf_counter() - started, 3)

    stats = outcome.get("stats") or {}
    resources = {
        "schema": "semread-001a-resources/1",
        "case_id": case["case_id"],
        "wall_seconds": wall,
        "transport_seconds": (outcome.get("request") or {}).get("transport_seconds"),
        "rss": {"value_bytes": _rss_bytes(),
                "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
                "scope": "bu vaka alt sürecinin kendi RSS'i; toplam model RAM'i değildir"},
        "backend": {"model": args.model, "digest": args.model_digest, "runtime_version": args.runtime,
                    "total_duration_ns": stats.get("total_duration_ns"),
                    "eval_count": stats.get("eval_count"),
                    "prompt_eval_count": stats.get("prompt_eval_count"),
                    "done_reason": stats.get("done_reason")},
        "unavailable": {"backend_peak_memory_bytes": None,
                        "reason": "Ollama süreç içi tepe bellek ölçüsü bu araçtan okunamıyor"},
        "limits": {"model_http_timeout_seconds": float(args.timeout),
                   "case_timeout_seconds": CASE_TIMEOUT_SECONDS,
                   "batch_timeout_seconds": RUN_TIMEOUT_SECONDS,
                   "live_call_limit_initial": LIVE_CALL_LIMIT,
                   "live_call_limit": effective_limit(load_state(Path(args.report_root))),
                   "live_calls_used": len(load_state(Path(args.report_root))["live_calls"])},
    }
    result = _write_artifacts(directory, case=case, bundle=bundle, prompt=prompt,
                              schema=probe_json_schema(), outcome=outcome, resources=resources)

    state = load_state(Path(args.report_root))
    state["cases"][case["case_id"]] = {
        "attempt_dir": str(directory), "product_verdict": result["product_verdict"],
        "gates": result["gates"], "failure_kind": result["failure_kind"],
        "images_per_call": result["images_per_call"],
        "expected_images_per_call": case["expected_images_per_call"],
        "wall_seconds": wall,
        "model": args.model, "model_digest": args.model_digest, "runtime_version": args.runtime,
        "code_identity": code_identity(), "head": _git("rev-parse", "HEAD"), "finished_at": _now(),
    }
    state["next_command"] = ("python eval/semantic_reader_probe.py --evaluate"
                             if all(result["gates"].values()) else
                             f"kanıt: {directory} (failure={result['failure_kind']})")
    save_state(state, Path(args.report_root))
    print(json.dumps({"case_id": case["case_id"], "verdict": result["product_verdict"],
                      "gates": result["gates"], "attempt_dir": str(directory)},
                     ensure_ascii=False))
    return EXIT_OK


# ---------------------------------------------------------------- evaluator


# Görsel kontrol eşleşmesi **sınıf alanının birebir eşitliği** ile yapılır (bkz. `_shape_match`).
# Açıklama metninde anahtar sözcük aramak kaldırıldı: "not a square" gibi bir yanıtı geçirirdi.
SHAPE_MATCH_METHOD = "exact_class_equality"

# A01–A08: hedefli testlerin kanıtı junit XML'inden okunur; test adı eşleşmeleri burada kapalıdır.
TEST_MAP = {
    "A01": {"files": ["junit/regression.xml"],
            "cases": ["test_inference_log", "test_model_choice", "test_reader",
                      "test_a_multi_image_call", "test_a_text_only_call_records_zero_images",
                      "test_a_single_image_call_still_counts_as_one"]},
    "A02": {"files": ["junit/semantic.xml"],
            "cases": ["test_three_images_are_serialised", "test_reversing_the_image_list",
                      "test_the_prompt_and_the_image_list", "test_images_and_the_old_single_image"]},
    "A03": {"files": ["junit/semantic.xml"],
            "cases": ["test_non_default_settings", "test_a_declared_resize_limit",
                      "test_no_declared_limit_means_no_resize"]},
    "A04": {"files": ["junit/semantic.xml"],
            "cases": ["test_a_pdf_crop_is_re_rendered", "test_the_same_source_region_is_kept",
                      "test_a_raster_crop_comes_from_the_native_pixels",
                      "test_the_crop_frame_maps_onto_the_page_corners",
                      "test_a_page_other_than_the_first_is_refused", "test_a_rotated_page_is_refused"]},
    "A05": {"files": ["junit/semantic.xml"],
            "cases": ["test_a_bad_bbox_is_refused", "test_a_response_may_only_reference",
                      "test_a_stale_snapshot_identity_is_refused",
                      "test_the_schema_carries_no_acceptance_field",
                      "test_an_image_id_that_was_never_sent_is_a_reference_error"]},
    "A06": {"files": ["junit/semantic.xml"],
            "cases": ["test_an_http_rejection_names_its_layer", "test_a_timeout_is_not_reported",
                      "test_an_empty_answer_keeps_the_raw_body", "test_a_broken_body_is_reported",
                      "test_a_broken_json_answer_is_kept_as_raw", "test_a_truncated_answer_is_recorded",
                      "test_an_unknown_truncation_cannot_pass_the_live_gate",
                      "test_a_response_without_exact_coverage_cannot_pass_the_gate",
                      "test_a_wrong_image_count_is_refused_by_the_verdict"]},
    "A07": {"files": ["junit/semantic.xml"],
            "cases": ["test_a_dry_run_calls_no_model_and_writes_nothing",
                      "test_the_probe_uses_the_shared_runner_root"]},
    "A08": {"files": ["junit/semantic.xml"],
            "cases": ["test_changing_the_prompt_or_schema_changes_the_cache_key",
                      "test_the_model_digest_is_part_of_the_cache_identity",
                      "test_untracked_semantic_code_is_watched",
                      "test_a_watched_untracked_file_really_changes_the_fingerprint",
                      "test_a_missing_required_input_is_refused_before_hashing",
                      "test_adding_only_a_document_does_not_change_the_evidence_identity",
                      "test_changing_the_content_of_a_relevant_source_file_changes_the_evidence_identity",
                      "test_the_identity_includes_the_command_and_the_environment"]},
}

# Kimlik eşlemesi satırı (A09) ve sentinel satırı (A11): canlı kanıtın yanında bu sözleşme testleri.
IDENTITY_TESTS = ("test_a_missing_identity_in_the_answer_keeps_the_row_open",
                  "test_a_duplicate_answer_item_keeps_the_row_open",
                  "test_a_state_attempt_verdict_contradiction_is_recorded_and_blocks_closure",
                  "test_shape_matching_is_exact_class_equality_not_substring_search",
                  "test_an_unknown_or_missing_class_is_not_a_visual_success",
                  "test_a_missing_message_layout_cannot_close_a_row",
                  "test_the_control_case_uses_new_neutral_ids_for_the_same_two_images",
                  "test_identical_bytes_under_two_ids_are_not_merged_into_one_identity",
                  "test_a_declared_identity_that_contradicts_the_bytes_is_not_a_join")
TEST_MAP["A09"] = {"files": ["junit/semantic.xml"], "cases": list(IDENTITY_TESTS)}
TEST_MAP["A11"] = {"files": ["junit/semantic.xml"],
                   "cases": ["test_a_skipped_or_failing_sentinel_test_blocks_the_row",
                             "test_the_blocker_note_explains_an_open_row_from_evidence"]}


def junit_dir(base: Path | None = None) -> Path:
    return report_root(base) / "junit"


# Test kanıtı yalnız bu adlandırılmış setlerle üretilir: komut sabittir, serbest argüman yok.
TEST_SUITES = {
    "semantic": ("tests/test_semantic_schema.py", "tests/test_semantic_images.py",
                 "tests/test_semantic_transport.py", "tests/test_semantic_reader.py",
                 "tests/test_semantic_reader_probe.py"),
    "regression": ("tests/test_inference_log.py", "tests/test_model_choice.py",
                   "tests/test_reader.py", "tests/test_planner.py", "tests/test_chain_model.py",
                   "tests/test_baseline_fields.py", "tests/test_lab_runner.py"),
}


def record_test_evidence(names: list[str], base: Path | None = None) -> dict:
    """Testleri koş, junit'i ve **hangi içeriğe ait olduğunu** yaz.

    Sidecar olmadan junit kanıtı tarihsiz bir iddia olurdu: başka bir revizyonun testi bu ağaçta
    kabul satırı kapatamaz. Kimlik `git status` metninden değil, ilgili dosyaların **içeriğinden**,
    test komutundan ve ortamdan hesaplanır (bkz. `evidence_identity`): yalnız bir doküman eklemek
    kanıtı bayatlatmaz, `M` işaretli bir kaynağın içeriği değişirse bayatlatır. Eski sidecar'lar
    yeniden damgalanmaz; yeni koşu kendi kimliğini taşıyan yeni bir sidecar yazar.
    """
    junit_dir(base).mkdir(parents=True, exist_ok=True)
    detail = identity_detail()
    identity = evidence_identity(detail)
    written: dict[str, dict] = {}
    for name in names:
        if name not in TEST_SUITES:
            raise SystemExit(f"bilinmeyen test seti: {name} (geçerli: {sorted(TEST_SUITES)})")
        xml = junit_dir(base) / f"{name}.xml"
        command = [sys.executable, "-m", "pytest", *TEST_SUITES[name], "-q",
                   f"--junitxml={xml}"]
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        suite = ElementTree.parse(xml).getroot() if xml.exists() else None
        nodes = [suite] if suite is not None and suite.tag == "testsuite" else (
            [] if suite is None else list(suite))
        totals = {key: sum(int(node.get(key) or 0) for node in nodes)
                  for key in ("tests", "failures", "errors", "skipped")}
        sidecar = {"schema": "semread-001a-test-evidence/2", "suite": name,
                   "command": command, "exit_code": done.returncode, "totals": totals,
                   "identity": identity, "identity_method": ("içerik: ilgili kod+test+config "
                                                             "dosyaları, test komutu ve ortam"),
                   "identity_files": detail["files"], "environment": detail["environment"],
                   "head": _git("rev-parse", "HEAD"), "head_is_identity": False,
                   "recorded_at": _now(), "junit": str(xml),
                   "tail": done.stdout.strip().splitlines()[-1:]}
        write_json(junit_dir(base) / f"{name}.tree.json", sidecar)
        written[name] = sidecar
    return written


def _read_junit(base: Path) -> dict:
    """junit XML'lerinden test adı → sonuç, **içerik kimliğiyle** birlikte.

    Her junit dosyasının yanında `<ad>.tree.json` sidecar'ı olmalı. Sidecar yoksa ya da içindeki
    kimlik güncel içerikten farklıysa o test sonucu bu ağaç için kanıt sayılmaz: eski bir revizyonda
    (ya da eski bir komut/ortamda) geçmiş bir test bugünkü kodu kapatmaz.
    """
    results: dict[str, dict] = {}
    current = evidence_identity()
    for path in sorted(junit_dir(base).glob("*.xml")):
        sidecar = read_json(path.with_suffix(".tree.json"), default=None)
        recorded = (sidecar or {}).get("identity")
        stale = not recorded or recorded != current
        try:
            tree = ElementTree.parse(path)
        except ElementTree.ParseError:  # pragma: no cover - bozuk XML kanıt değildir
            results[f"{path.name}::<ayrıştırılamadı>"] = {"file": path.name, "failed": True,
                                                          "skipped": False, "stale": stale}
            continue
        for node in tree.iter("testcase"):
            name = f"{node.get('classname') or ''}::{node.get('name') or ''}"
            failed = any(child.tag in ("failure", "error") for child in node)
            skipped = any(child.tag == "skipped" for child in node)
            results[name] = {"file": path.name, "failed": failed, "skipped": skipped,
                             "stale": stale, "identity": recorded}
    return results


def load_runner_state(base: Path | None = None) -> dict:
    """Ortak LabRunner durumu (salt okunur): kaç attempt yapıldığını rapor için buradan okuruz.

    Varsayılan düzende rapor kökü `out/lab/semread-001a` olduğu için paylaşılan runner kökü onun
    kardeşidir: `out/lab`. İkinci bir kilit/state kurulmaz, yalnız okunur.
    """
    payload = read_json(report_root(base).parent / "state.json", default=None)
    return payload if isinstance(payload, dict) else {}


def _record_completeness(images: list[dict]) -> dict:
    """Actual-request kaydı hangi alanları taşıyor? Eski sürümle yazılmış attempt'ler eksik olabilir.

    Eksik alan "kanıt yok" demek değildir (gövde hash'i ve gönderilen hash yine kayıtlıdır), ama
    rapor bunu söylemeli: kayıt şeması ile kaydın yazıldığı sürüm karışmasın.
    """
    return {"request_has_image_ids": bool(images) and all(entry.get("image_id") for entry in images),
            "request_has_sent_sizes": bool(images) and all(
                entry.get("sent_width_px") and entry.get("sent_height_px") for entry in images)}


def _attempt_images(directory: Path) -> dict[str, dict]:
    """Attempt dizinindeki `images/*.png` — gönderilen byte'ların diskteki karşılığı.

    Kayıtlı manifest hangi sürümle yazılmış olursa olsun, gönderilen hash'i diskteki dosyayla
    eşleştirmek mümkündür: kimlik↔byte bağı bu ölçümle kurulur, manifest alanına güvenilmez.
    """
    found: dict[str, dict] = {}
    for path in sorted((directory / "images").glob("*.png")):
        payload = path.read_bytes()
        width, height = _png_size(payload)
        found[path.stem] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                            "width_px": width, "height_px": height}
    return found


def _png_size(payload: bytes) -> tuple[int | None, int | None]:
    """PNG IHDR'den okunan boyut; okunamazsa (None, None)."""
    if len(payload) < 24 or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, None
    width, height = struct.unpack(">II", payload[16:24])
    return int(width), int(height)


def _test_gate(requirement: dict, results: dict, base: Path) -> tuple[str, list[str], list[str], list[str]]:
    """Kabul satırı ancak **bildirilen dosyadan, güncel ağaca ait, hepsi geçmiş** testle kapanır."""
    declared = [Path(name).name for name in requirement["files"]]
    evidence, missing, stale = [], [], []
    for name, record in sorted(results.items()):
        if not any(token in name for token in requirement["cases"]):
            continue
        if Path(record["file"]).name not in declared:
            continue  # başka setin testi bu satırı kapatmaz
        evidence.append(f"{name} [{record['file']}]")
        if record["failed"] or record["skipped"]:
            missing.append(name)
        if record.get("stale"):
            stale.append(name)
    present = [str(junit_dir(base) / file) for file in declared if (junit_dir(base) / file).exists()]
    files_complete = len(present) == len(declared)
    status = "closed" if (evidence and not missing and not stale and files_complete) else "open"
    return status, evidence, present, sorted(set(stale + ([] if files_complete else
                                                          [f"eksik kanıt dosyası: {declared}"])))


def _attempt_code_matches(directory: Path) -> bool:
    """Attempt, **şu anki** kod kimliğiyle mi üretildi?

    Runner, attempt manifestine koşu anındaki `code_fingerprint`'i yazar. Kanıt bugünkü kodla
    yeniden üretilebilir olmadıkça kabul satırı kapatılamaz: eski bir sürümün başarısı bu ağaçta
    geçerli bir ölçüm değildir.
    """
    manifest = read_json(directory / "manifest.json", default=None)
    if not isinstance(manifest, dict) or not manifest.get("code_fingerprint"):
        return False
    return manifest["code_fingerprint"] == code_identity()


def _shape_match(gold: dict, parsed: dict | None) -> dict:
    """L1/L2/L5: modelin **sınıf alanı** altın kimlik→sınıf eşlemesiyle birebir tutuyor mu?

    Değerlendirme kimlik→sınıf ilişkisi üzerindedir, açıklama metninin alt-dizgesi üzerinde değil:
    "not a square", "triangle or square" gibi ifadeler eskiden eşleşme sayılabiliyordu ve bu, cevabı
    şaşırtan modeli doğru yazardı. Eksik madde yine kaçırmadır; `unknown`/`other` ve tanımsız sınıf
    da tutmaz — şema uyumu tek başına görsel başarı değildir.
    """
    if not parsed:
        return {"checked": False, "reason": "parse edilmiş yanıt yok"}
    expected_shapes = gold.get("shapes") or {}
    hits, misses, missing_items = {}, [], []
    for image_id, expected in sorted(expected_shapes.items()):
        items = [item for item in (parsed.get("items") or [])
                 if item.get("image_id") == image_id]
        if not items:
            missing_items.append(image_id)
            misses.append(image_id)
            hits[image_id] = {"expected": expected, "shape": None, "matched": False,
                              "note": "yanıtta bu görsel için madde yok"}
            continue
        shape = items[0].get("shape")
        matched = shape == expected
        hits[image_id] = {"expected": expected, "shape": shape,
                          "description": items[0].get("description"), "matched": matched}
        if not matched:
            misses.append(image_id)
    return {"checked": bool(expected_shapes), "method": "exact_class_equality",
            "per_image": hits, "misses": misses, "missing_items": missing_items,
            "all_matched": bool(expected_shapes) and not misses}


def _case_attempt_history(base: Path | None, case_id: str) -> list[dict]:
    """Bir vakanın geçmiş attempt'leri: çerçeveleme, verdict ve yol — araştırmanın izi.

    Kabul satırları en güncel attempt'e bakar; ama "neden bu çerçeveleme" sorusunun cevabı geçmişte
    durur. Bu liste kanıt dosyalarından okunur, elle yazılmaz.
    """
    job = f"semread-001a-{case_id.lower()}"
    runs = report_root(base).parent / "runs"
    history: list[dict] = []
    for job_dir in sorted(runs.glob(f"*/{job}")):
        for attempt in sorted(job_dir.glob("attempt-*")):
            request = read_json(attempt / "request-manifest.json", default={}) or {}
            result = read_json(attempt / "result.json", default={}) or {}
            history.append({
                "attempt": str(attempt),
                "run": job_dir.parent.name,
                "name": attempt.name,
                "layout": request.get("images_layout"),
                "images": request.get("images_per_call"),
                "verdict": result.get("product_verdict") or result.get("blocking_kind") or "kayıtsız",
            })
    return history


def _valid_regions(directory: Path, minimum: int) -> dict:
    checks = read_json(directory / "reference-checks.json", default={}) or {}
    reference = checks.get("reference") or {}
    resolved = [row for row in (reference.get("resolved_regions_page_norm") or [])
                if row.get("region_page_norm")]
    return {"required": minimum, "resolved_count": len(resolved), "ok": len(resolved) >= minimum,
            "resolved": resolved}


def _gold_isolation(directory: Path, gold: dict, base: Path | None, case_id: str) -> dict:
    """Altının reader'ın girdisine girmediğini **evaluator tarafında** kanıtla.

    Aranan iz iki tanedir: snapshot'a özel `gold-sentinel` ve altın **eşlemesi** (kimlik→sınıf).
    Sınıf sözlüğü (triangle/square/…) prompt'ta zaten açıkça yazılıdır: sözleşme olan bu sözlüğü altın
    saymak sentinel'i işe yaramaz hale getirirdi. Bu yüzden denetim, bir kimliğin kendi sınıfıyla
    **yan yana** geçmesini arar (ör. `image-1 = triangle` ya da `image-1 … triangle`); modele giden
    şey incelenir, modelin yanıtı değil. Görsel mesajlarının metinleri (etiketler) da istek kaydında
    olduğu için bu taramanın kapsamındadır.
    """
    sentinel = str(gold.get("gold-sentinel") or "")
    pairs = sorted((gold.get("shapes") or {}).items())
    texts = {}
    for name in ("prompt.txt", "request-manifest.json", "input-manifest.json"):
        path = directory / name
        texts[name] = path.read_text(encoding="utf-8") if path.exists() else ""
    case_file = cases_dir(base) / f"{case_id}-case.json"
    texts["cases"] = case_file.read_text(encoding="utf-8") if case_file.exists() else ""
    found = []
    for name, text in texts.items():
        if sentinel and sentinel in text:
            found.append(f"{name}: altın sentinel izi")
        if name in ("prompt.txt", "request-manifest.json"):
            for image_id, shape in pairs:
                for pattern in (rf"{re.escape(image_id)}\b[^\n]{{0,40}}{re.escape(shape)}",
                                rf"{re.escape(shape)}\b[^\n]{{0,40}}{re.escape(image_id)}"):
                    if re.search(pattern, text, flags=re.IGNORECASE):
                        found.append(f"{name}: altın eşleme izi ({image_id}={shape})")
                        break
    return {"sentinel": sentinel, "pairs_checked": [f"{name}={shape}" for name, shape in pairs],
            "checked": sorted(texts), "found": found, "clean": not found}


def budget_audit(state: dict, base: Path | None = None) -> dict:
    """Bütçe denetimi: gerçek kullanım **çağrı kayıtlarından** sayılır, rapordan devralınmaz.

    Devir notundaki "11 kullanıldı" sayısı bir iddiadır; burada state'teki her çağrı kaydı ve runner'ın
    attempt sayısı ayrı ayrı okunur. Kümülatif tavan bu goal'de 16'dır: ilk tavan 8, önceki uzatma 12.
    """
    calls = state.get("live_calls") or []
    by_case: dict[str, int] = {}
    for call in calls:
        case_id = str(call.get("case_id") or "?")
        by_case[case_id] = by_case.get(case_id, 0) + 1
    jobs = (load_runner_state(base).get("jobs") or {})
    attempts = sum(int((job or {}).get("attempts") or 0) for job in jobs.values())
    return {"used": len(calls), "limit": effective_limit(state), "initial_limit": LIVE_CALL_LIMIT,
            "extensions": state.get("budget_extensions") or [], "used_by_case": by_case,
            "runner_attempts_total": attempts,
            "remaining": max(0, effective_limit(state) - len(calls)),
            "method": ("state.live_calls kayıtları sayılır (çağrı başına bir kayıt, çağrıdan önce "
                       "yazılır); runner attempt sayısı ayrı alan olarak raporlanır"),
            "counting_note": ("zaman aşımı ve başarısız istekler de bu sayıya girer; doğrudan tanı "
                              "çağrıları da kayıt altındadır")}


def sent_image_join(request: dict, on_disk: dict) -> dict:
    """Gönderilen her kaydı diskteki görselle eşleştir — **hash→ID birleştirmesi yapmadan**.

    Birincil anahtar istek kaydındaki `image_id`'dir; beyan ile ölçüm çelişirse eşleme kurulmaz.
    Kimlik taşımayan (eski) kayıtlarda hash'e düşülür, ama o hash birden çok dosyaya karşılık
    geliyorsa tek bir ad seçilmez: "aynı byte'lar, iki kimlik" durumu belirsiz olarak yazılır.
    """
    by_hash: dict[str, list[str]] = {}
    for name, record in on_disk.items():
        by_hash.setdefault(record["sha256"], []).append(name)
    rows, ambiguous = [], []
    for entry in request.get("images") or []:
        digest = entry.get("sent_sha256")
        declared = entry.get("image_id")
        candidates = sorted(by_hash.get(digest or "", []))
        resolved, note = None, None
        if declared and declared in on_disk:
            resolved = declared
            if digest and on_disk[declared]["sha256"] != digest:
                resolved, note = None, "beyan edilen kimliğin byte'ı kayıttaki hash'le uyuşmuyor"
        elif len(candidates) == 1:
            resolved = candidates[0]
            note = "kimlik kayıtta yok; tek hash eşleşmesiyle kuruldu"
        elif len(candidates) > 1:
            note = "belirsiz: aynı hash birden çok görselde, tek ad seçilmedi"
        elif declared:
            note = "diskte bu kayda karşılık gelen görsel yok"
        if note and not resolved:
            ambiguous.append({"index": entry.get("index"), "declared_image_id": declared,
                              "note": note})
        rows.append({"index": entry.get("index"), "declared_image_id": declared,
                     "resolved_image_id": resolved, "sent_sha256": digest,
                     "hash_candidates": candidates,
                     "bytes": (on_disk.get(resolved or "") or {}).get("bytes"),
                     "width_px": (on_disk.get(resolved or "") or {}).get("width_px"),
                     "height_px": (on_disk.get(resolved or "") or {}).get("height_px"),
                     "note": note})
    return {"rows": rows, "ids": [row["resolved_image_id"] for row in rows],
            "resolved_count": len([row for row in rows if row["resolved_image_id"]]),
            "entry_count": len(rows), "ambiguous": ambiguous,
            "all_bound": bool(rows) and all(row["resolved_image_id"] for row in rows)}


def evaluate(base: Path | None = None) -> dict:
    """Kanıtı **diskteki** dosyalardan yeniden kur: hash kontrolü, altın eşleşmesi, kabul tablosu.

    Karar attempt'in **sürümlü ham kanıtından** (result.json + request/response dosyaları) okunur;
    state'teki `product_verdict` bayrağı yalnız karşılaştırma için kullanılır ve çelişki açıkça
    yazılır. Üretici (attempt'i üreten kod/model) ve değerlendirici (bu koşunun kodu) kimlikleri ayrı
    alanlardır: eski bir attempt'ın başarısı bugünkü evaluator'ın ürünü gibi görünmez.
    """
    root = report_root(base)
    state = load_state(base)
    junit = _read_junit(base)
    evaluator = {"identity": evidence_identity(), "method": "content+command+environment",
                 "probe_schema_versions": {"case": CASE_SCHEMA},
                 "code_identity": code_identity(), "path": str(Path(__file__).resolve())}
    evaluations: dict[str, dict] = {}
    for case_id in case_ids():
        record = (state.get("cases") or {}).get(case_id)
        if not record:
            evaluations[case_id] = {"present": False, "reason": "bu vaka için live koşu kaydı yok"}
            continue
        directory = Path(record["attempt_dir"])
        index = verify_artifact_index(directory)
        gold = read_json(gold_dir(base) / f"{case_id}.json", default={}) or {}
        parsed = read_json(directory / "response-parsed.json", default=None)
        checks = read_json(directory / "reference-checks.json", default={}) or {}
        # Karar ham kanıttan gelir: attempt'in kendi result.json'u (state bayrağı değil).
        raw_result = read_json(directory / "result.json", default={}) or {}
        attempt_manifest = read_json(directory / "manifest.json", default={}) or {}
        shapes = _shape_match(gold, parsed) if gold.get("shapes") else {"checked": None}
        regions = _valid_regions(directory, int(gold.get("min_valid_regions") or 0))
        isolation = _gold_isolation(directory, gold, base, case_id)
        request = read_json(directory / "request-manifest.json", default={}) or {}
        on_disk = _attempt_images(directory)
        join = sent_image_join(request, on_disk)
        coverage_recorded = ((checks.get("reference") or {}).get("coverage") or {})
        answered = [item.get("image_id") for item in (parsed or {}).get("items") or []]
        coverage = {
            "sent": join["ids"], "answered": answered,
            "missing": [name for name in join["ids"] if name and name not in answered],
            "duplicates": sorted({name for name in answered if answered.count(name) > 1}),
            "unknown": sorted({name for name in answered if name not in join["ids"]}),
            "empty_answer": not answered,
            "from_response": True,
            "recorded_by_reader": coverage_recorded or None,
        }
        coverage["exact"] = (bool(join["ids"]) and not coverage["missing"]
                             and not coverage["duplicates"] and not coverage["unknown"])
        producer = {
            "code_fingerprint": attempt_manifest.get("code_fingerprint"),
            "code_fingerprint_matches_current": _attempt_code_matches(directory),
            "model": attempt_manifest.get("model") or record.get("model"),
            "model_digest": record.get("model_digest"),
            "runtime_version": record.get("runtime_version"),
            "request_sha256": request.get("request_sha256"),
            "prompt_sha256": request.get("prompt_sha256"),
            "images_layout": request.get("images_layout"),
            "attempt_dir": str(directory),
        }
        visual = ("pass" if shapes.get("all_matched") is True else
                  ("fail" if shapes.get("checked") is True else "not_evaluated"))
        transport = {"parsed": bool((checks.get("reference") or {}).get("ok")) and bool(parsed),
                     "schema_valid": bool((checks.get("reference") or {}).get("ok")) and bool(parsed),
                     "references_ok": bool((checks.get("reference") or {}).get("ok")),
                     "coverage_exact": coverage["exact"],
                     "gates": raw_result.get("gates") or {},
                     "verdict_from_attempt": raw_result.get("product_verdict")}
        state_verdict = record.get("product_verdict")
        evaluations[case_id] = {
            "present": True, "attempt_dir": str(directory),
            "product_verdict": raw_result.get("product_verdict") or state_verdict,
            "state_verdict": state_verdict,
            "state_attempt_contradiction": (state_verdict is not None
                                            and raw_result.get("product_verdict") is not None
                                            and state_verdict != raw_result.get("product_verdict")),
            "gates": raw_result.get("gates") or record.get("gates"),
            "artifact_index": {"ok": index["ok"], "problems": index.get("problems") or [],
                               "file_count": index.get("file_count")},
            "images_per_call": request.get("images_per_call"),
            "expected_images_per_call": record.get("expected_images_per_call"),
            "request_sha256": request.get("request_sha256"),
            "image_ids_sent": join["ids"],
            "image_join": {"rows": join["rows"], "ambiguous": join["ambiguous"],
                           "all_bound": join["all_bound"]},
            "image_hashes": [row["sent_sha256"] for row in join["rows"]],
            "image_sizes": [[row["width_px"], row["height_px"]] for row in join["rows"]],
            "image_bytes_on_disk": {name: record["bytes"] for name, record in on_disk.items()},
            "record_completeness": _record_completeness(request.get("images") or []),
            "messages_layout": request.get("messages_layout") or [],
            "images_layout": request.get("images_layout"),
            "code_fingerprint_matches": _attempt_code_matches(directory),
            "producer": producer, "evaluator": evaluator,
            "runner_attempts": ((load_runner_state(base).get("jobs") or {}).get(
                f"semread-001a-{case_id.lower()}") or {}).get("attempts"),
            "coverage": coverage,
            "separations": {"transport": "pass" if transport["parsed"] and transport["coverage_exact"]
                                         and transport["references_ok"] else "fail",
                            "coverage": "pass" if coverage["exact"] else "fail",
                            "visual_control": visual,
                            "case_acceptance": None},
            "schema_valid": bool((checks.get("reference") or {}).get("ok")) and bool(parsed),
            "references": {"ok": bool((checks.get("reference") or {}).get("ok")),
                           "referenced": (checks.get("reference") or {}).get("referenced_image_ids")},
            "leakage": checks.get("leakage") or [],
            "gold_isolation": isolation,
            "shapes": shapes, "regions": regions,
            "gold": str(gold_dir(base) / f"{case_id}.json"),
        }

    def complete(entry: dict) -> bool:
        """Canlı kanıtın **eksiksiz** olması: ham kanıt verdict'i, güncel kod, izlenebilir istek."""
        record = entry.get("record_completeness") or {}
        coverage = entry.get("coverage") or {}
        join = entry.get("image_join") or {}
        gaps = [name for name, ok in (
            ("attempt ham kanıtı (result.json) yok", bool(entry.get("product_verdict"))),
            ("attempt verdict'i pass değil", entry.get("product_verdict") == "pass"),
            ("artifact index doğrulanmadı", (entry.get("artifact_index") or {}).get("ok") is True),
            ("kanıt güncel kod kimliğiyle üretilmedi", entry.get("code_fingerprint_matches") is True),
            ("istek kaydında image_id yok", record.get("request_has_image_ids") is True),
            ("istek kaydında ölçülmüş boyut yok", record.get("request_has_sent_sizes") is True),
            ("istek kaydında mesaj düzeni yok", bool(entry.get("messages_layout"))),
            ("görsel kimlikleri byte'lara bağlanamadı", join.get("all_bound") is True),
            ("yanıt kapsamı tam değil", coverage.get("exact") is True),
            ("kesilme/kapı kaydı yok", bool((entry.get("gates") or {}).get("not_truncated"))),
            ("tamamlanma metadata'sı yok", (entry.get("gates") or {}).get("completion_metadata") is True),
            ("state ile attempt verdict'i çelişiyor", not entry.get("state_attempt_contradiction")),
        ) if not ok]
        entry["incomplete_reasons"] = gaps
        return not gaps

    def live(case_id: str, predicate) -> tuple[str, list[str], list[str]]:
        entry = evaluations.get(case_id) or {}
        if not entry.get("present"):
            return "open", [f"{case_id}: live kayıt yok"], ["live koşu kaydı yok"]
        gaps = []
        if not complete(entry):
            gaps = entry.get("incomplete_reasons") or []
        matched = predicate(entry)
        if not matched:
            gaps = gaps + [f"{case_id}: vaka koşulu tutmadı"]
        return ("closed" if not gaps else "open"), [entry["attempt_dir"]], gaps

    def visual_ok(entry: dict) -> bool:
        return (entry.get("shapes") or {}).get("all_matched") is True

    l1_status, l1_ev, l1_gaps = live("L1", visual_ok)
    l2_status, l2_ev, l2_gaps = live("L2", visual_ok)
    l5_status, l5_ev, l5_gaps = live("L5", visual_ok)

    def l34_ok(case_id: str, expected: int) -> tuple[bool, list[str]]:
        entry = evaluations.get(case_id) or {}
        if not entry.get("present"):
            return False, [f"{case_id}: live kayıt yok"]
        gaps = [] if complete(entry) else (entry.get("incomplete_reasons") or [])
        if entry.get("images_per_call") != expected:
            gaps.append(f"{case_id}: görsel sayısı {entry.get('images_per_call')} != {expected}")
        if not entry.get("schema_valid"):
            gaps.append(f"{case_id}: şema/referans kontrolü geçmedi")
        regions = entry.get("regions") or {}
        if not regions.get("ok"):
            gaps.append(f"{case_id}: geçerli sayfa bölgesi yok "
                        f"({regions.get('resolved_count')}/{regions.get('required')})")
        return (not gaps), gaps

    ok3, gaps3 = l34_ok("L3", 3)
    ok4, gaps4 = l34_ok("L4", 2)
    l3_ev = [str((evaluations.get("L3") or {}).get("attempt_dir") or "L3: kayıt yok")]
    l4_ev = [str((evaluations.get("L4") or {}).get("attempt_dir") or "L4: kayıt yok")]

    test_status: dict[str, tuple[str, list[str], list[str], list[str]]] = {}
    for requirement_id, requirement in TEST_MAP.items():
        test_status[requirement_id] = _test_gate(requirement, junit, base)

    sentinel_evidence, sentinel_problems = [], []
    for name, record in sorted(junit.items()):
        if not ("sentinel" in name or "gold" in name):
            continue
        if record.get("stale"):
            sentinel_problems.append(f"{name}: kanıt güncel içerik kimliğine ait değil")
        elif record.get("failed") or record.get("skipped"):
            sentinel_problems.append(f"{name}: test geçmedi/atlandı")
        else:
            sentinel_evidence.append(name)
    if not sentinel_evidence and not sentinel_problems:
        sentinel_problems.append("güncel içerik kimliğine ait sentinel/altın testi yok")
    live_leakage_clean = all(not (evaluations.get(case, {}).get("leakage") or [])
                             for case in case_ids() if evaluations.get(case, {}).get("present"))
    live_gold_clean = all((evaluations.get(case, {}).get("gold_isolation") or {}).get("clean")
                          for case in case_ids() if evaluations.get(case, {}).get("present"))

    rows = {}
    for requirement_id in ("A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"):
        status, evidence, junit_files, problems = test_status[requirement_id]
        rows[requirement_id] = {"status": status, "evidence": evidence,
                                "junit_files": junit_files, "problems": problems,
                                "closure": "verdict" if status == "closed" else "indeterminate"}
    # A09: canlı kimlik eşlemesi **ve** bu satırı koruyan sözleşme testleri birlikte gerekir.
    a09_tests = test_status.get("A09", ("open", [], [], []))
    rows["A09"] = {"status": "closed" if (l1_status == l2_status == "closed"
                                          and a09_tests[0] == "closed") else "open",
                   "evidence": l1_ev + l2_ev + a09_tests[1], "closure": "verdict",
                   "problems": l1_gaps + l2_gaps + list(a09_tests[3]),
                   "detail": {"L1": l1_status, "L2": l2_status, "identity_tests": a09_tests[0],
                              "visual_control": [(evaluations.get(case) or {}).get("shapes", {})
                                                 .get("all_matched") for case in ("L1", "L2")]}}
    rows["A10"] = {"status": "closed" if (ok3 and ok4) else "open", "evidence": l3_ev + l4_ev,
                   "closure": "verdict", "problems": gaps3 + gaps4,
                   "detail": {"L3_görsel": (evaluations.get("L3") or {}).get("images_per_call"),
                              "L4_görsel": (evaluations.get("L4") or {}).get("images_per_call"),
                              "L3_region": (evaluations.get("L3") or {}).get("regions"),
                              "L4_region": (evaluations.get("L4") or {}).get("regions")}}
    a11_tests = test_status.get("A11", ("open", [], [], []))
    rows["A11"] = {"status": "closed" if (sentinel_evidence and not sentinel_problems
                                          and live_leakage_clean and live_gold_clean
                                          and a11_tests[0] == "closed") else "open",
                   "evidence": sentinel_evidence + a11_tests[1] + [str(root / "cases")],
                   "closure": "verdict" if sentinel_evidence else "indeterminate",
                   "problems": sentinel_problems + list(a11_tests[3]) +
                               ([] if live_leakage_clean else ["canlı leakage"]) +
                               ([] if live_gold_clean else ["canlı altın izolasyonu temiz değil"])}
    report = root / "final" / "report.md"
    four = ("L1", "L2", "L3", "L4")
    all_live = all((evaluations.get(case) or {}).get("present") for case in four)
    indexes_ok = all((evaluations.get(case, {}).get("artifact_index") or {}).get("ok")
                     for case in four)
    fresh_live = all((evaluations.get(case, {}) or {}).get("code_fingerprint_matches") is True
                     for case in four if (evaluations.get(case) or {}).get("present"))
    request_meta_ok = all((evaluations.get(case, {}).get("record_completeness") or {}).get(
        "request_has_image_ids") and ((evaluations.get(case, {}).get("image_join") or {}).get("all_bound"))
        for case in four if (evaluations.get(case) or {}).get("present"))
    identity_records = all(bool(((evaluations.get(case, {}) or {}).get("producer") or {}).get("request_sha256"))
                           and bool((evaluations.get(case, {}) or {}).get("evaluator"))
                           for case in case_ids() if (evaluations.get(case) or {}).get("present"))
    rows["A13"] = {"status": "closed" if l5_status == "closed" else "open",
                   "evidence": l5_ev, "closure": "verdict", "problems": l5_gaps,
                   "note": ("ek kimlik kontrolü: L1/L2'nin aynı iki görseli yeni nötr kimliklerle "
                            "(image-11/image-27). Genelleme iddiası değildir.")}
    # Rapor önce yazılır, sonra varlığı kanıt olarak kaydedilir: dosya gerçekten diskte olmalı.
    preserve_start_copies(base)
    rows["A12"] = {"status": "open", "evidence": [str(report), "attempt/artifact-index.json"],
                   "closure": "indeterminate"}
    report.parent.mkdir(parents=True, exist_ok=True)
    state["live_calls"] = state.get("live_calls") or []
    # Engel, rapor yazılmadan önce belirlenir: rapor açık satırların nedenini de taşımalı.
    state["blocked"] = _blocker_note(rows, evaluations)
    report.write_text(_report_markdown(base, rows, evaluations, junit, state), encoding="utf-8")
    a12_problems = [name for name, ok in (("dört vaka canlı kanıtı (L1–L4)", all_live),
                                          ("artifact index", indexes_ok),
                                          ("güncel kod kimliği", fresh_live),
                                          ("istek metadata'sı + kimlik bağı", request_meta_ok),
                                          ("üretici/değerlendirici kimlik kaydı", identity_records))
                    if not ok]
    rows["A12"] = {"status": "closed" if (report.exists() and not a12_problems) else "open",
                   "evidence": [str(report)] + [evaluations.get(case, {}).get("attempt_dir", "")
                                                for case in case_ids() if (evaluations.get(case) or {}).get("present")],
                   "closure": "verdict" if all_live else "indeterminate",
                   "problems": a12_problems}
    budget = budget_audit(state, base)
    # Rapor A12/bütçe nihai durumunu da taşımalı: satır değiştiyse rapor bir kez daha yazılır.
    report.write_text(_report_markdown(base, rows, evaluations, junit, state), encoding="utf-8")

    open_rows = sorted(name for name, row in rows.items() if row["status"] != "closed")
    core_open = [name for name in open_rows if name not in CONTROL_ROWS]
    payload = {
        "schema": "semread-001a-acceptance/1", "goal": "SEMREAD-001A",
        "continuation_id": CONTINUATION_ID,
        "evaluation_scope": EVALUATION_SCOPE,
        "semantic_evaluation": "not_evaluated", "cad_evaluation": "not_evaluated",
        "budget": budget,
        "live_calls_used": budget["used"], "live_call_limit": budget["limit"],
        "live_call_limit_initial": LIVE_CALL_LIMIT,
        "budget_extensions": budget["extensions"],
        "head": _git("rev-parse", "HEAD"), "working_tree": _git("status", "--porcelain"),
        "identity": {"method": ("içerik: ilgili kod+test+config dosyaları, test komutu ve ortam; "
                                "git durum metni kimlik değildir"),
                     "evidence_identity": evaluator["identity"],
                     "evaluator": evaluator,
                     "producer_identities": {case: ((evaluations.get(case) or {}).get("producer") or {})
                                             for case in case_ids()
                                             if (evaluations.get(case) or {}).get("present")}},
        "code_identity": state.get("code_identity"),
        "tests_seen": len(junit),
        "test_evidence_identity": {name: (record.get("identity") or "")[:16] + "…"
                                   for name, record in sorted(junit.items())[:1]},
        "acceptance": rows, "open": open_rows, "open_core": core_open,
        "control_rows": list(CONTROL_ROWS),
        "separations": {case: (evaluations.get(case) or {}).get("separations")
                        for case in case_ids() if (evaluations.get(case) or {}).get("present")},
        "conclusion": ("SEMREAD-001A complete" if not open_rows
                       else f"implementation status: {len(rows) - len(open_rows)}/{len(rows)} kabul "
                            f"satırı kapandı; açık çekirdek: {core_open or '—'}; "
                            f"açık kontrol: {[n for n in open_rows if n in CONTROL_ROWS] or '—'}"),
        "evaluations": evaluations,
        "evaluated_at": _now(),
    }
    write_json(acceptance_path(base), payload)
    state["next_command"] = _next_command(rows, evaluations, budget)
    state["open_acceptance"] = open_rows
    state["blocked"] = _blocker_note(rows, evaluations)
    save_state(state, base)
    write_continuation_package(payload, rows, evaluations, budget, base)
    return payload


def _next_command(rows: dict, evaluations: dict, budget: dict) -> str:
    """Gerçek sıradaki işi yaz — `--evaluate`'ı tekrar önermek engeli kaldırmaz."""
    open_core = [name for name, row in rows.items()
                 if row["status"] != "closed" and name not in CONTROL_ROWS]
    if not open_core and rows.get("A13", {}).get("status") == "closed":
        return "SEMREAD-001A complete: 001B başlatılmaz"
    if budget.get("remaining", 0) <= 0:
        return (f"bütçe tükendi ({budget.get('used')}/{budget.get('limit')}): yeni canlı çağrı için "
                f"tavan uzatılmalı, aksi halde açık satırlar kanıtsız kalır")
    if "A09" in open_core:
        detail = rows.get("A09", {}).get("problems") or []
        return ("L2 için aynı bütçeyle yeni bir çağrı yap: önce `--dry-run` ile planı doğrula, sonra "
                "`--live --cases L2`; açık neden: " + ("; ".join(detail[:3]) or "yanıt hizası"))
    if "A10" in open_core:
        return "L3/L4 için `--live --cases L3,L4` (bölge kanıtı ve görsel sayısı kapıları)"
    if "A12" in open_core:
        return "eksik kanıtı tamamla: `--record-tests semantic,regression` ardından `--evaluate`"
    return ("açık satırlar: " + ", ".join(open_core) + " — kanıt dosyalarını incele "
            "(`acceptance.json → acceptance[*].problems`)")


def write_continuation_package(payload: dict, rows: dict, evaluations: dict, budget: dict,
                               base: Path | None = None) -> dict:
    """Devam paketini benzersiz dizine yaz: yeni test/eval/kabul/rapor orada toplanır.

    Eski kanıt (`out/lab/runs/**`, önceki `final/report.md`) yerinde kalır; bu paket onun yerine
    geçmez, yanına yazılır. Paylaşılan runner kökü değişmez.
    """
    target = continuation_dir(base)
    (target / "final").mkdir(parents=True, exist_ok=True)
    (target / "junit").mkdir(parents=True, exist_ok=True)
    write_json(target / "acceptance.json", payload)
    (target / "final" / "report.md").write_text(_report_markdown(base, rows, evaluations,
                                                                 _read_junit(base), load_state(base)),
                                                encoding="utf-8")
    for path in sorted(junit_dir(base).glob("*")):
        if path.is_file():
            (target / "junit" / path.name).write_bytes(path.read_bytes())
    detail = identity_detail()
    write_json(target / "identity.json",
               {"schema": "semread-001a-continuation-identity/1",
                "continuation_id": CONTINUATION_ID, "recorded_at": _now(),
                "identity": evidence_identity(detail), "identity_method": detail and
                "içerik: ilgili kod+test+config dosyaları, test komutu ve ortam",
                "files": detail["files"], "commands": detail["commands"],
                "environment": detail["environment"],
                "budget": budget,
                "start_copies": str(target / "start" / "start-copies.json"),
                "changing_files": sorted((load_runner_state(base).get("jobs") or {}).keys())})
    return {"continuation_dir": str(target), "identity": evidence_identity(detail)}
def _file_time(path: Path) -> str:
    """Dosyanın disk zamanı — koşu anını iddia etmeden, kanıtın ne zaman yazıldığını söyler."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(
            microsecond=0).isoformat()
    except OSError:  # pragma: no cover
        return "bilinmiyor"


def _sidecar_note(path: Path) -> str:
    """Kanıtın hangi içeriğe ait olduğunu ve bugüne uyup uymadığını tek kelimeyle yaz."""
    sidecar = read_json(path.with_suffix(".tree.json"), default=None)
    recorded = (sidecar or {}).get("identity")
    if not recorded:
        return "YOK (bu kanıt bir içerik kimliğine bağlı değil)"
    return f"{recorded[:16]}…/{'güncel' if recorded == evidence_identity() else 'ESKİ'}"


def _row_for_case(rows: dict, case_id: str) -> str | None:
    """Vakanın hangi kabul satırına bağlı olduğunu yaz (rapor okunurken karışmasın)."""
    mapping = {"L1": "A09", "L2": "A09", "L3": "A10", "L4": "A10", "L5": "A13"}
    return (rows.get(mapping.get(case_id, ""), {}) or {}).get("status")


def _budget_note(state: dict) -> str:
    """Bütçe uzatmalarını tek satırda yaz: tavan değiştiyse rapor bunu saklamaz."""
    parts = [f"{item.get('from')}->{item.get('to')} ({item.get('reason')})"
             for item in state.get("budget_extensions") or []]
    return "; ".join(parts) if parts else "yok"


def _blocker_note(rows: dict, evaluations: dict) -> str | None:
    """Açık satırların **nedenini** yaz: engel, kanıttan okunan tek cümlelik durumdur."""
    reasons: list[str] = []
    for case_id in case_ids():
        entry = evaluations.get(case_id) or {}
        if not entry.get("present"):
            if rows.get("A09", {}).get("status") != "closed" or rows.get("A10", {}).get("status") != "closed":
                reasons.append(f"{case_id}: live koşu kaydı yok")
            continue
        shapes = entry.get("shapes") or {}
        if shapes.get("checked") and not shapes.get("all_matched"):
            detail = shapes.get("missing_items") or []
            label = f"maddesi yok: {detail}" if detail else ""
            reasons.append(f"{case_id}: gold şekil eşleşmesi tutmadı "
                           f"(kaçan={shapes.get('misses')} {label})".strip())
        if not (entry.get("artifact_index") or {}).get("ok"):
            reasons.append(f"{case_id}: kanıt index'i doğrulanmadı")
        # Kanıtın *kendisi* eksikse nedenini yaz: kapanmayan satır sessiz kalmamalı.
        record = entry.get("record_completeness") or {}
        if not record.get("request_has_image_ids"):
            reasons.append(f"{case_id}: istek kaydında image_id yok")
        if not record.get("request_has_sent_sizes"):
            reasons.append(f"{case_id}: istek kaydında ölçülmüş boyut yok")
        if entry.get("code_fingerprint_matches") is not True:
            reasons.append(f"{case_id}: kanıt güncel kod kimliğiyle üretilmedi")
    open_tests = [name for name in ("A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08")
                  if rows.get(name, {}).get("status") != "closed"]
    if open_tests:
        problems = sorted({item for name in open_tests for item in (rows.get(name) or {}).get("problems") or []})
        detail = f" ({'; '.join(problems)})" if problems else ""
        reasons.append("test kapısı açık: " + ", ".join(open_tests) + detail)
    return "; ".join(reasons) if reasons else None


def _report_markdown(base: Path | None, rows: dict, evaluations: dict, junit: dict,
                     state: dict) -> str:
    """Raporu kanıt dosyalarından üret: elle yazılan sayı yok, her satır bir yola bağlı."""
    lock = read_json(model_lock_path(base), default={}) or {}
    lines: list[str] = [
        "# SEMREAD-001A — taşıma probe'u son raporu",
        "",
        "Bu rapor `eval/semantic_reader_probe.py --evaluate` tarafından attempt dizinlerindeki kanıt",
        "dosyalarından üretilir. Ölçüm kapsamı `semread-001a-transport`: görsel taşıma zinciri ve yapısal",
        "yanıt kapıları. Çizimin doğru okunduğu, delik/cavity çıkarıldığı veya STEP üretildiği **iddia",
        "edilmez** (semantic/CAD: not_evaluated).",
        "",
        "## Koşu kimliği",
        "",
        f"- HEAD (bilgi; kimlik değil): `{_git('rev-parse', 'HEAD')}`",
        f"- kanıt içerik kimliği: `{state.get('evidence_identity') or state.get('working_tree_sha256')}`",
        f"  — yöntem: {state.get('identity_method')}",
        f"- değerlendirici (bu koşunun kodu): `{state.get('evaluator_identity')}`; probe sürümleri: "
        f"case `{CASE_SCHEMA}`, reader `semread-reader/2`, yanıt şeması `semread-probe/2`",
        f"- ortam: Python {((state.get('environment') or {}).get('python'))}, pytest "
        f"{(state.get('environment') or {}).get('pytest')}, {(state.get('environment') or {}).get('platform')}",
        f"- model: `{lock.get('model')}` digest `{lock.get('digest')}`",
        f"- runtime: Ollama `{lock.get('runtime_version')}`; model boyutu {lock.get('size_bytes')} B, "
        f"{lock.get('quantization')}",
        f"- bütçe: vaka {CASE_TIMEOUT_SECONDS} s, batch {RUN_TIMEOUT_SECONDS} s, gerçek çağrı tavanı "
        f"{effective_limit(state)} (ilk tavan {LIVE_CALL_LIMIT}; uzatmalar: {_budget_note(state)}); "
        f"kullanılan {len(state.get('live_calls') or [])}",
        f"- engel (blocked): {state.get('blocked')}",
        f"- sıradaki iş: {state.get('next_command')}",
        "",
        "## Değişen dosyalar (çalışma ağacı)",
        "",
        "```",
        (_git("status", "--porcelain") or "(temiz)"),
        "```",
        "",
        "## Çalıştırılan testler",
        "",
    ]
    suites_dir = junit_dir(base)
    for path in sorted(suites_dir.glob("*.xml")) if suites_dir.exists() else []:
        try:
            suite = ElementTree.parse(path).getroot()
        except ElementTree.ParseError:  # pragma: no cover
            lines.append(f"- {path.name}: okunamadı")
            continue
        suites = [suite] if suite.tag == "testsuite" else list(suite)
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        for node in suites:
            for key in totals:
                totals[key] += int(node.get(key) or 0)
        lines.append(
            f"- `{path.name}`: tests={totals['tests']} failures={totals['failures']} "
            f"errors={totals['errors']} skipped={totals['skipped']} "
            f"(bitiş: {_file_time(path)}; ağaç parmak izi: {_sidecar_note(path)})")
    lines += ["", "## Kabul tablosu (A01–A13)", "",
              "A01–A12 çekirdek satırlardır; **A13** devam goal'inin ek kimlik kontrolüdür ve genelleme",
              "iddiası taşımaz. Bir satır ancak kanıtı güncel içerik kimliğine ait, hepsi geçmiş testlerle",
              "kapanır; `indeterminate` = kanıt yok, `open` = kanıt var ama kapı tutmadı.", "",
              "| # | Durum | Kapanış | Kanıt |", "| --- | --- | --- | --- |"]
    for requirement_id in sorted(rows):
        row = rows[requirement_id]
        evidence = row.get("evidence") or []
        shown = ", ".join(f"`{item}`" for item in evidence[:3])
        more = f" (+{len(evidence) - 3})" if len(evidence) > 3 else ""
        lines.append(f"| {requirement_id} | {row['status']} | {row.get('closure')} | {shown}{more} |")
    problem_rows = {name: row.get("problems") for name, row in sorted(rows.items())
                    if row.get("problems")}
    if problem_rows:
        lines += ["", "### Açık satırların nedenleri (kanıttan)", ""]
        for name, problems in problem_rows.items():
            lines.append(f"- **{name}**: " + "; ".join(str(item) for item in problems))
    lines += ["", "## Ayırma: taşıma / kapsam / görsel kontrol / vaka kabulü", "",
              "| Vaka | Taşıma | Kapsam | Görsel kontrol | Vaka kabulü |",
              "| --- | --- | --- | --- | --- |"]
    for case_id in case_ids():
        entry = evaluations.get(case_id) or {}
        if not entry.get("present"):
            lines.append(f"| {case_id} | — | — | — | live kayıt yok |")
            continue
        separation = entry.get("separations") or {}
        lines.append(f"| {case_id} | {separation.get('transport')} | {separation.get('coverage')} | "
                     f"{separation.get('visual_control')} | "
                     f"{'kapandı' if _row_for_case(rows, case_id) == 'closed' else 'açık'} |")
    lines += ["", "L3/L4'te çizimin doğru okunduğu değerlendirilmez (`semantic_evaluation: "
              "not_evaluated`): orada yalnız taşıma, kapsam ve bölge kapıları ölçülür. L1/L2/L5'te görsel "
              "kontrol, altın kimlik→sınıf eşlemesiyle **birebir sınıf eşitliği** ile yapılır.", ""]
    lines += ["", "## L1–L5 sonuçları", ""]
    for case_id in case_ids():
        entry = evaluations.get(case_id) or {}
        if not entry.get("present"):
            lines += [f"### {case_id}", "", f"- live koşu yok: {entry.get('reason')}", ""]
            continue
        directory = Path(entry["attempt_dir"])
        prompt = directory / "prompt.txt"
        inputs = read_json(directory / "input-manifest.json", default={}) or {}
        resources = read_json(directory / "resources.json", default={}) or {}
        raw = read_json(directory / "response-raw.json", default={}) or {}
        prepared = {image.get("image_id"): image for image in inputs.get("images") or []}
        on_disk = _attempt_images(directory)
        by_hash = {record["sha256"]: name for name, record in on_disk.items()}
        lines += [
            f"### {case_id} — verdict `{entry.get('product_verdict')}`",
            "",
            f"- attempt dizini: `{directory}` (dosya sayısı {entry['artifact_index'].get('file_count')}, "
            f"index doğrulaması {'geçti' if entry['artifact_index']['ok'] else 'GEÇMEDİ'})",
            f"- prompt: `{prompt}` ({prompt.stat().st_size if prompt.exists() else 0} B, "
            f"sha256 {sha256_file(prompt)[:16] + '…' if prompt.exists() else '—'})",
            f"- gönderilen görseller: {entry.get('images_per_call')}; çerçeveleme "
            f"`{entry.get('images_layout') or 'bilinmiyor'}`; request sha256 "
            f"`{(entry.get('request_sha256') or '')[:16]}…`",
            f"- yanıt kapsamı: {len(entry.get('coverage', {}).get('answered') or [])}/"
            f"{len(entry.get('image_ids_sent') or [])} görsel"
            + (f", eksik: {entry['coverage']['missing']}" if entry.get("coverage", {}).get("missing") else ""),
            f"- runner attempt sayısı: {entry.get('runner_attempts')}; kayıt alanları: "
            f"image_id={'var' if (entry.get('record_completeness') or {}).get('request_has_image_ids') else 'YOK'} "
            f"ölçülmüş boyut={'var' if (entry.get('record_completeness') or {}).get('request_has_sent_sizes') else 'YOK'} "
            f"(eksik alan gövde hash'ini geçersiz kılmaz)",
        ]
        history = _case_attempt_history(base, case_id)
        if len(history) > 1:
            lines.append(
                "- attempt geçmişi (" + str(len(history)) + "): " + "; ".join(
                    f"`{item['run'][:20]}/{item['name']}` "
                    f"çerçeveleme={item['layout'] or '—'} görsel={item['images']} → {item['verdict']}"
                    for item in history))
        request_images = read_json(directory / "request-manifest.json", default={}) or {}
        join = entry.get("image_join") or {}
        for row in join.get("rows") or []:
            image_id = row.get("resolved_image_id")
            sent = {"index": row.get("index"), "sent_sha256": row.get("sent_sha256")}
            source = prepared.get(image_id) or {}
            lines.append(
                f"  - sıra {sent.get('index')}: `{image_id or 'eşleşmedi'}` "
                f"(beyan `{row.get('declared_image_id') or '—'}`, {row.get('bytes')} B, "
                f"{row.get('width_px')}x{row.get('height_px')} px) "
                f"kind={source.get('kind')} "
                f"kaynak={str(source.get('source_sha256') or '')[:12]}…/s.{source.get('page_index')} "
                f"gönderilen={str(sent.get('sent_sha256') or '')[:12]}… "
                f"render={source.get('render_mode')} dpi={source.get('render_dpi')} "
                f"crop={source.get('source_bbox_page_norm')} "
                f"image→page={source.get('t_image_norm_to_page_norm')} resize={sent.get('resize')}"
                + (f" NOT={row.get('note')}" if row.get("note") else ""))
        if (request_images.get("messages_layout") or []):
            labels = [f"`{item.get('label')}`" if item.get("label") else
                      f"(metinsiz) {item.get('image_ids')}"
                      for item in request_images["messages_layout"]]
            lines.append(f"  - mesaj düzeni (`{entry.get('images_layout')}`): " + " | ".join(labels))
        lines += [
            f"- ayrım: taşıma `{(entry.get('separations') or {}).get('transport')}`, kapsam "
            f"`{(entry.get('separations') or {}).get('coverage')}`, görsel kontrol "
            f"`{(entry.get('separations') or {}).get('visual_control')}` "
            f"({'şekil sınıfı birebir karşılaştırıldı' if (entry.get('shapes') or {}).get('checked') else 'bu vakada değerlendirilmedi'})",
            f"- üretici (attempt): kod `{str((entry.get('producer') or {}).get('code_fingerprint') or '')[:16]}…` "
            f"(güncel: {(entry.get('producer') or {}).get('code_fingerprint_matches_current')}), model "
            f"`{(entry.get('producer') or {}).get('model')}` digest "
            f"`{str((entry.get('producer') or {}).get('model_digest') or '')[:12]}…`, request "
            f"`{str((entry.get('producer') or {}).get('request_sha256') or '')[:16]}…`",
            f"- değerlendirici (bu koşu): `{str((entry.get('evaluator') or {}).get('identity') or '')[:16]}…` "
            f"— attempt kararı `{(entry.get('producer') or {}).get('attempt_dir')}` altındaki `result.json`dan "
            f"okundu; state bayrağı `{entry.get('state_verdict')}` "
            f"(çelişki: {entry.get('state_attempt_contradiction')})",
        ]
        lines += [
            f"- yanıt: parse={entry.get('references', {}).get('ok')} şema/referans kontrolü "
            f"`reference-checks.json`; ham yanıt `response-raw.json` "
            f"({len(str(raw.get('content') or ''))} karakter)",
            f"- ölçümler: süre {resources.get('wall_seconds')} s (taşıma "
            f"{resources.get('transport_seconds')} s), token: prompt "
            f"{(resources.get('backend') or {}).get('prompt_eval_count')} / üretilen "
            f"{(resources.get('backend') or {}).get('eval_count')}, done_reason "
            f"`{(resources.get('backend') or {}).get('done_reason')}`",
            f"- kaynak: `resources.json` (Python RSS kapsamı açıkça yazılı; toplam RAM iddiası yok)",
            f"- altın ayrımı: {(entry.get('gold_isolation') or {}).get('clean')} "
            f"({(entry.get('gold_isolation') or {}).get('found')})",
        ]
        if (entry.get("shapes") or {}).get("checked"):
            shapes = entry["shapes"]
            lines.append(f"- gold görsel kontrolü (yalnız evaluator, yöntem "
                         f"`{shapes.get('method') or SHAPE_MATCH_METHOD}`): all_matched="
                         f"{shapes.get('all_matched')}, kaçan={shapes.get('misses')}, "
                         f"maddesi olmayan={shapes.get('missing_items')}")
            for image_id, detail in sorted((shapes.get("per_image") or {}).items()):
                lines.append(f"  - `{image_id}`: beklenti={detail.get('expected')} "
                             f"model sınıfı={detail.get('shape')} tuttu={detail.get('matched')} "
                             f"(açıklama: \"{detail.get('description')}\")")
        lines += [
            f"- kapılar: `{entry.get('gates')}`",
            "",
        ]
    lines += [
        "## Yeniden çalıştırma",
        "",
        "```bash",
        "# plan (çağrı yok, bütçe harcamaz)",
        ".venv/bin/python eval/semantic_reader_probe.py --dry-run",
        "# hedefli testler + içerik kimliği sidecar'ı (önce bu, sonra canlı: kanıt aynı içeriğe ait olsun)",
        ".venv/bin/python eval/semantic_reader_probe.py --record-tests semantic,regression",
        "# yalnız kararı veren çağrı: L2 önce (kimlik eşlemesi), sonra L1 (aynı düzenin doğal sırası)",
        ".venv/bin/python eval/semantic_reader_probe.py --live --cases L2",
        ".venv/bin/python eval/semantic_reader_probe.py --live --cases L1",
        "# çizim taşıması ve bölge kapıları",
        ".venv/bin/python eval/semantic_reader_probe.py --live --cases L3,L4",
        "# ek kimlik kontrolü: aynı iki görsel, yeni nötr kimlikler (image-11/image-27)",
        ".venv/bin/python eval/semantic_reader_probe.py --live --cases L5",
        "# kanıtı diskten yeniden kur, kabul tablosunu ve bu raporu yaz",
        ".venv/bin/python eval/semantic_reader_probe.py --evaluate",
        "# bütçe tavanı (kümülatif 16) yetmezse: nedenini kayda geçerek uzat",
        ".venv/bin/python eval/semantic_reader_probe.py --extend-budget",
        "```",
        "",
        "## Ölçülmeyenler",
        "",
        "- `image_attached`/`images_in_request` isteğin görüntü taşıdığını söyler; sunucunun görüntüyü",
        "  kullandığını buradan anlaşılmaz.",
        "- Model açıklaması semantic doğruluk kanıtı değildir; delik/cavity veya STEP sonucu bu probe'da",
        "  kapatılmaz. L3/L4'te görsel kontrol `not_evaluated` kalır; X01–X03 açık kalır.",
        "- A13 yalnız \"aynı iki görsel yeni nötr kimliklerle de bağlanıyor\" sorusunu ölçer: kimlik",
        "  desteğinin genelleştiğini iddia etmez (tek fixture çifti, tek model).",
        "- Uzun koşularda ısı/enerji ölçümü yapılmadı; yalnız işlem süresi ve backend token sayaçları var.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def _select(cases: str | None) -> list[str]:
    if not cases:
        return list(case_ids())
    wanted = [name.strip().upper() for name in cases.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in case_ids()]
    if unknown:
        raise SystemExit(f"bilinmeyen vaka: {unknown}")
    return wanted


def build_parser() -> argparse.ArgumentParser:
    """Tek parser: hem ana giriş hem worker aynı tanımı kullanır (komut-argüman drift'i imkânsız)."""
    parser = argparse.ArgumentParser(description="SEMREAD-001A taşıma probe'u")
    parser.add_argument("--cases", default=None, help="L1,L2,L3,L4 (varsayılan: hepsi)")
    parser.add_argument("--lab-root", type=Path, default=ROOT / "out/lab",
                        help="ortak lab kökü (ikinci bir kilit kurulmaz)")
    parser.add_argument("--report-root", type=Path, default=None,
                        help="goal rapor kökü (varsayılan: out/lab/semread-001a)")
    parser.add_argument("--model", default=None, help="kurulu tek vision modeli (varsayılan: seçici)")
    parser.add_argument("--dry-run", action="store_true", help="planı yaz, hiçbir çağrı yapma")
    parser.add_argument("--live", action="store_true", help="gerçek yerel çağrıları runner altında koş")
    parser.add_argument("--evaluate", action="store_true", help="kanıtı diskten yeniden kur ve kabul yaz")
    parser.add_argument("--timeout", type=float, default=float(MODEL_TIMEOUT_SECONDS),
                        help="model HTTP zaman aşımı (saniye); vaka bütçesi ayrı: 600")
    # worker
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--case-file", default=None)
    parser.add_argument("--attempt-dir", default=None)
    parser.add_argument("--result", default=None)
    parser.add_argument("--model-digest", default=None)
    parser.add_argument("--runtime", default="unknown")
    parser.add_argument("--num-predict", type=int, default=DEFAULT_SETTINGS["num_predict"])
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_SETTINGS["num_ctx"])
    parser.add_argument("--temperature", type=float, default=DEFAULT_SETTINGS["temperature"])
    parser.add_argument("--keep-alive", default=DEFAULT_SETTINGS["keep_alive"])
    parser.add_argument("--image-max-side", type=float, default=None)
    parser.add_argument("--images-layout", choices=LAYOUTS, default=DEFAULT_SETTINGS["images_layout"],
                        help="görsellerin istekte çerçevelenmesi (sözleşme aynı: ID ↔ sıra)")
    parser.add_argument("--record-tests", default=None,
                        help="test setlerini koş, junit + ağaç parmak izini yaz (ör. semantic,regression)")
    parser.add_argument("--extend-budget", action="store_true",
                        help="çağrı tavanını uzat ve nedenini kayda geç (yükseltme; düşürme reddedilir)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    base = args.report_root
    if args.worker:
        return run_worker(args)

    if args.evaluate:
        payload = evaluate(base)
        print(json.dumps({"acceptance": str(acceptance_path(base)), "open": payload["open"],
                          "conclusion": payload["conclusion"]}, ensure_ascii=False, indent=2))
        return EXIT_OK

    if args.extend_budget:
        # Kümülatif tavan: bu devam goal'i 16'ya çıkarır; neden kayda geçer (kodda gizlenmez).
        print(json.dumps(extend_budget(base, LIVE_CALL_LIMIT_CONTINUATION,
                                       LIVE_CALL_LIMIT_CONTINUATION_REASON),
                         ensure_ascii=False, indent=2))
        return EXIT_OK

    if args.record_tests:
        names = [name.strip() for name in args.record_tests.split(",") if name.strip()]
        written = record_test_evidence(names, base)
        print(json.dumps({name: {"totals": item["totals"], "exit_code": item["exit_code"]}
                          for name, item in written.items()}, ensure_ascii=False, indent=2))
        return EXIT_OK

    model = args.model or default_model()
    cases = [case_definition(case_id, base) for case_id in _select(args.cases)]
    write_gold(base)
    prepare_case_files(cases, base)
    try:
        lock = model_lock(model)
    except UnavailableModel as exc:
        # Yerel sunucu/model yok: digest uydurulmaz ve live koşu engelli yazılır; plan yine üretilir.
        lock = unreadable_lock(model, str(exc))
    write_json(model_lock_path(base), lock)
    jobs = make_jobs(cases, lock, lab_root=args.lab_root, base=base,
                     timeout=CASE_TIMEOUT_SECONDS)
    require_inputs(jobs)

    runner = LabRunner(args.lab_root, root_repository=ROOT, code_hash=code_identity)
    if args.dry_run or not args.live:
        plan = runner.execute(jobs, dry_run=True)
        print(json.dumps({"dry_run": True, "model": lock, "jobs": [
            {"job": entry["job"], "timeout_seconds": entry["timeout_seconds"],
             "cached": entry["cached"], "inputs_present": all(entry["inputs"].values())}
            for entry in plan["planned"]]}, ensure_ascii=False, indent=2))
        return EXIT_OK

    if not lock.get("digest"):
        payload = {"implementation_ready": True, "live_validation_blocked": lock.get("unavailable_reason"),
                   "next_command": f"yerel modeli hazırla ve '{sys.executable} "
                                   f"eval/semantic_reader_probe.py --live' komutunu koş"}
        state = load_state(base)
        state["blocked"] = payload["live_validation_blocked"]
        state["next_command"] = payload["next_command"]
        save_state(state, base)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_MODEL

    state = load_state(base)
    if len(state["live_calls"]) + len(jobs) > effective_limit(state):
        raise SystemExit(f"bütçe yetmiyor: kullanılan {len(state['live_calls'])} + {len(jobs)} > "
                         f"{effective_limit(state)}")
    outcome = runner.execute(jobs)
    print(json.dumps(outcome, ensure_ascii=False, indent=2, default=str))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
