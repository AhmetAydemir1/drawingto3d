"""G12 üretici aşaması — bir vakanın üretici yükünü kurar ve sürücüyü *referanssız* çalıştırır (PLAN-24 §8).

```bash
.venv/bin/python eval/g12_runner/produce_case.py --case <case_id> \
    --round eval/audits/20261007-g12-manifest-reruns/run-01 \
    [--recipe <reçete.json>] [--driver <sürücü.py>] [--python <yorumlayıcı>] \
    [--driver-arg ARG]...
```

Akış: manifest → `producer_input.producer_view()` (referans alanları düşer) →
`<round>/cases/<case>/producer-input.json` → env/argv/yük sınır denetimi → sürücü alt süreci →
`<round>/cases/<case>/produce-run.json` (çıkış kodu, HEAD, üretici girdisinin sha256'sı).

Sürücüye referans yolu yalnız geçmez, geçemez: `assert_reference_free` ihlalde `ReferenceLeakage`
atar ve alt süreç hiç başlatılmaz. Bu dosya vaka adına göre dallanmaz; sürücü bir parametredir.

Varsayılan sürücü **kaynak-only G12 sürücüsüdür** (`g12_runner.py`, G12R-04): üretici girdisini ve
reçeteyi okur, sonucu yalnız verilen tur dizinine yazar. Tarihsel G11 koşucusu bu yolda REDDEDİLİR —
tam manifesti kendi okur, evaluator'ı kendisi başlatır ve kendi `cases/` dizinine yazar; o dosya
tarihsel kanıt olarak yerinde durur ama G12 üretici aşamasının sürücüsü olamaz.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from producer_input import (PRODUCER_FIELDS, ReferenceLeakage, assert_reference_free,  # noqa: E402
                            producer_view, reference_values)

DEFAULT_MANIFEST = ROOT / "eval/guided_10_manifest.json"
DEFAULT_DRIVER = HERE / "g12_runner.py"
DEFAULT_PYTHON = "/Users/aydemir/.hermes/cache/scratch/cdp-venv/bin/python"

LEGACY_DRIVER_NAMES = ("g11_runner.py",)
"""G12 üretici yolunda çalışmayacak tarihsel sürücü adları (G12R-04)."""
LEGACY_DRIVER_DIRS = ("20261007-guided-g11",)
EXIT_LEGACY_DRIVER = 4
"""Tarihsel sürücü reddi: hiçbir dosya yazılmadan dönülür."""


def load_manifest(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_entry(manifest: dict, case_id: str) -> dict:
    for entry in manifest.get("cases") or []:
        if entry.get("case_id") == case_id:
            return entry
    raise SystemExit(f"vaka manifestte yok: {case_id}")


def build_producer_input(case_id: str, manifest_path: pathlib.Path, round_dir: pathlib.Path) -> dict:
    """Üretici girdisini yaz ve döndür — saf dosya işi; süreç başlatmaz (testler bunu kullanır)."""
    manifest = load_manifest(manifest_path)
    entry = find_entry(manifest, case_id)
    producer = producer_view(entry)
    target = round_dir / "cases" / case_id / "producer-input.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(producer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"producer": producer, "path": target, "reference_values": reference_values(manifest)}


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display(path: pathlib.Path) -> str:
    """Koşu kaydındaki yol: repo içindeyse göreli, değilse mutlak (test koşuları tmp'de olabilir)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:  # noqa: BLE001 — HEAD kaydı kanıt alanıdır; yokluğu koşuyu durdurmaz
        return "unknown"


def refuse_legacy_driver(driver: pathlib.Path) -> str | None:
    """Eski koşucu G12 üretici aşamasının sürücüsü olamaz — adı ya da tarihsel dizini yeter (G12R-04)."""
    if driver.name in LEGACY_DRIVER_NAMES:
        return "legacy-g11-driver"
    if any(part in driver.as_posix() for part in LEGACY_DRIVER_DIRS):
        return "legacy-g11-driver"
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="G12 üretici aşaması (referanssız)")
    parser.add_argument("--case", required=True)
    parser.add_argument("--round", required=True, help="koşu dizini (ör. eval/audits/.../run-01)")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--recipe", default=None, help="sürücüye verilecek reçete (varsa)")
    parser.add_argument("--driver", default=str(DEFAULT_DRIVER))
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="sürücüyü çalıştıracak yorumlayıcı")
    parser.add_argument("--driver-arg", action="append", default=[], help="sürücüye eklenecek argüman")
    parser.add_argument("--prepare-only", action="store_true",
                        help="yalnız üretici girdisini yaz + sınırı denetle; sürücüyü çalıştırma")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, _app_environment: dict | None = None) -> int:
    """`_app_environment` yalnız sürücünün ortamına eklenir (testler sahte uygulamayı böyle gösterir)."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    refused = refuse_legacy_driver(pathlib.Path(args.driver))
    if refused:
        print(f"[DRIVER-REFUSED] {refused}: G12 üretici yolu kaynak-only sürücü çalıştırır "
              f"(verilen: {args.driver})", file=sys.stderr, flush=True)
        return EXIT_LEGACY_DRIVER
    round_dir = pathlib.Path(args.round)
    if not round_dir.is_absolute():
        round_dir = ROOT / round_dir
    built = build_producer_input(args.case, pathlib.Path(args.manifest), round_dir)
    producer, path = built["producer"], built["path"]

    driver = pathlib.Path(args.driver)
    if not driver.is_absolute():
        driver = ROOT / driver
    command = [args.python, str(driver)]
    if args.recipe:
        command.append(args.recipe)
    command += list(args.driver_arg)

    env = dict(os.environ)
    env.update(_app_environment or {})
    env["G12_PRODUCER_INPUT"] = str(path)
    env["G12_CASE_ID"] = args.case
    env["G12_ROUND_DIR"] = str(round_dir)
    try:
        assert_reference_free({"producer_input": producer, "env": env, "argv": command},
                              reference_values=built["reference_values"], where="produce_case")
    except ReferenceLeakage as leakage:
        print(f"REFERENCE-LEAKAGE: {leakage}", file=sys.stderr, flush=True)
        return 2

    if args.prepare_only or not driver.exists():
        record = {"case_id": args.case, "driver": str(driver), "driver_ran": False,
                  "prepare_only": bool(args.prepare_only), "driver_exists": driver.exists(),
                  "git_head": git_head(),
                  "producer_input": display(path),
                  "producer_input_sha256": sha256_file(path),
                  "reference_checked": True, "producer_fields": list(PRODUCER_FIELDS)}
        (path.parent / "produce-run.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return 0 if args.prepare_only else 3

    completed = subprocess.run(command, cwd=ROOT, env=env)
    record = {"case_id": args.case, "driver": str(driver), "driver_ran": True,
              "exit": completed.returncode, "recipe": args.recipe, "git_head": git_head(),
              "producer_input": display(path),
              "producer_input_sha256": sha256_file(path),
              "reference_checked": True, "producer_fields": list(PRODUCER_FIELDS)}
    (path.parent / "produce-run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False), flush=True)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
