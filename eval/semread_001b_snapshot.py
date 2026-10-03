"""SEMREAD-001A'yı **geri kazanılabilir** bir snapshot ile sabitler (001B ağacı değiştirmeden önce).

Neden gerekli: 001B'nin ekleyeceği modüller `src/drawingto3d/*.py` glob'unu büyütür ve 001A'nın
**global kanıt kimliğini** değiştirir. 001A'nın başarısı kendi snapshot'ına aittir; bu yüzden ağaç
değişmeden önce

  (a) kimliğe giren kaynak/test/config dosyalarının **kopyaları** (`code/`),
  (b) 001A kanıt paketinin ve canlı attempt dizinlerinin **hash manifesti + kopyaları** (`evidence/`),
  (c) kimliğin nasıl yeniden hesaplandığı (dosya hash'leri + test komutları + ortam) yazılır.

Snapshot salt okunurdur: 001A kanıtı **silinmez, taşınmaz, damgalanmaz**. Bu betik hiçbir inference
yapmaz (gerçek çağrı sayısı 0).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/aydemir/Desktop/drawingto3d")
REPORT = ROOT / "out/lab/semread-001a"
RUNS = ROOT / "out/lab/runs"
SNAPSHOT_BASE = ROOT / "out/lab/semread-001b/snapshot"

# 001A'nın kimliğine giren dosyalar (001A kanıtındaki `_identity_files()` ile aynı kaynaklar) ve
# kanıtı yeniden kurmak için gereken ek dosyalar. Kopyalar `code/` altında yol yapısını korur.
CODE_FILES = (
    "eval/semantic_reader_probe.py",
    "pyproject.toml",
)
CODE_GLOBS = ("src/drawingto3d/*.py", "src/drawingto3d_lab/*.py")
EXTRA_CODE = (
    "tests/test_semantic_schema.py", "tests/test_semantic_images.py",
    "tests/test_semantic_transport.py", "tests/test_semantic_reader.py",
    "tests/test_semantic_reader_probe.py", "tests/test_inference_log.py",
    "tests/test_model_choice.py", "tests/test_reader.py", "tests/test_planner.py",
    "tests/test_chain_model.py", "tests/test_baseline_fields.py", "tests/test_lab_runner.py",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _load_001a_probe():
    """001A'nın kendi kodunu **değiştirmeden** yükleyip kimliğini ondan oku."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("probe_001a", ROOT / "eval/semantic_reader_probe.py")
    if spec is None or spec.loader is None:  # pragma: no cover - yol sabit, teorik koruma
        raise RuntimeError("001A probe kaynağı yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy(relative: str, target_root: Path, kind: str) -> dict:
    source = ROOT / relative
    if not source.exists():
        return {"path": relative, "kind": kind, "present": False, "sha256": None, "bytes": None,
                "copy": None}
    target = target_root / kind / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {"path": relative, "kind": kind, "present": True, "sha256": sha256_of(source),
            "bytes": source.stat().st_size, "copy": str(target.relative_to(target_root.parent.parent)),
            "copy_sha256": sha256_of(target)}


def main() -> int:
    probe = _load_001a_probe()
    state = json.loads((REPORT / "state.json").read_text(encoding="utf-8"))
    acceptance = json.loads((REPORT / "acceptance.json").read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot = SNAPSHOT_BASE / f"001a-{stamp}"
    snapshot.mkdir(parents=True, exist_ok=True)

    code_rows, missing = [], []
    for relative in (*CODE_FILES, *EXTRA_CODE):
        row = _copy(relative, snapshot, "code")
        code_rows.append(row)
        missing += [] if row["present"] else [relative]
    for pattern in CODE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            relative = str(path.relative_to(ROOT))
            row = _copy(relative, snapshot, "code")
            code_rows.append(row)
            missing += [] if row["present"] else [relative]

    evidence_rows = []
    for path in sorted(REPORT.rglob("*")):
        if path.is_dir():
            continue
        relative = str(path.relative_to(ROOT))
        row = _copy(relative, snapshot, "evidence")
        evidence_rows.append(row)

    attempt_rows = []
    for call in state.get("live_calls") or []:
        for path in sorted(Path(call["attempt_dir"]).rglob("*")):
            if path.is_dir():
                continue
            relative = str(path.relative_to(ROOT))
            row = _copy(relative, snapshot, "attempts")
            attempt_rows.append(row)

    identity_detail = probe.identity_detail()
    manifest = {
        "schema": "semread-001b-001a-snapshot/1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "why": ("001B eklenince `src/drawingto3d/*.py` glob'u büyür ve 001A'nın global kanıt kimliği "
                "değişir; 001A başarısı bu snapshot'a bağlıdır"),
        "head": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--short"),
        "001a": {
            "evidence_identity": probe.evidence_identity(identity_detail),
            "identity_detail": identity_detail,
            "acceptance_conclusion": acceptance.get("conclusion"),
            "acceptance_open": acceptance.get("open"),
            "next_command": state.get("next_command"),
            "live_calls": len(state.get("live_calls") or []),
            "budget_extensions": state.get("budget_extensions") or [],
            "cases": {case: {"attempt_dir": record.get("attempt_dir"),
                             "product_verdict": record.get("product_verdict"),
                             "code_identity": record.get("code_identity"),
                             "finished_at": record.get("finished_at")}
                      for case, record in (state.get("cases") or {}).items()},
        },
        "code_files": code_rows,
        "evidence_files": evidence_rows,
        "attempt_files": attempt_rows,
        "missing": missing,
        "totals": {"code": len(code_rows), "evidence": len(evidence_rows),
                   "attempts": len(attempt_rows)},
        "restore_note": ("Geri kazanma: `code/<yol>` dosyalarını repo köküne aynı yolla kopyala; "
                         "`evidence/<yol>` ve `attempts/<yol>` kanıt dizinlerini eski yerine döndür. "
                         "Hash'ler `sha256` alanında; doğrulama `verify_snapshot()` ile yapılır."),
    }
    (snapshot / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                            encoding="utf-8")

    broken = [row for row in (*code_rows, *evidence_rows, *attempt_rows)
              if row["present"] and row["sha256"] != row.get("copy_sha256")]
    print(json.dumps({"snapshot": str(snapshot), "totals": manifest["totals"],
                      "missing": missing, "copy_mismatch": len(broken),
                      "001a_identity": manifest["001a"]["evidence_identity"],
                      "001a_live_calls": manifest["001a"]["live_calls"],
                      "acceptance": manifest["001a"]["acceptance_conclusion"]},
                     ensure_ascii=False, indent=2))
    return 0 if not broken and not missing else 1


def verify_snapshot(snapshot: Path) -> dict:
    """Snapshot'taki her kopyayı yeniden hash'le: manifest ile uyuşmayan varsa bildir."""
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    rows = [*manifest["code_files"], *manifest["evidence_files"], *manifest["attempt_files"]]
    bad = [row["path"] for row in rows
           if row["present"] and sha256_of(snapshot / row["copy"].split("/", 1)[1]) != row["sha256"]]
    return {"checked": len(rows), "mismatch": bad}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        print(json.dumps(verify_snapshot(Path(sys.argv[2])), ensure_ascii=False, indent=2))
        raise SystemExit(0)
    raise SystemExit(main())
