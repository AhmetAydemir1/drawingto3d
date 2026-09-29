"""Dort v2 girdide uctan uca urun yolu: hangi asamada ne oluyor, STEP cikiyor mu.

Review6: "ucdan uca olcum, okumalar mukemmel olana kadar ertelenmemeli". Bu arac urun zincirini
(`observe -> bind -> meaning -> propose -> build-general`) her v2 girdi icin gercekten kosturur ve
asamalarin cikis kodunu, reddin gerekcesini ve uretilen STEP'i kaydeder. Teshis araci degil bir urun
olcumudur: hicbir seyi duzeltmez, yalnizca ne oldugunu yazar.

Raster (`drawing.png`) girdiler icin urun yolunda bugun yalniz `read` var; bu yuzden png tarafi okuma
sonucunu (kac kayit tutuldu, hangileri soru olarak kaldi) kaydeder ve orada durur - eksik olan sey
gizlenmez, `stopped_at` alanina yazilir.

Kullanim: `python eval/end_to_end.py [vaka ...]`   (varsayilan: out/lab/data/v2/pilot-*)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "out/lab/data/v2"
OUT = ROOT / "out/lab/product-goal/e2e"
PDF_CHAIN = ["observe", "bind", "meaning", "propose", "build-general"]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def _run(stage: str, args: list[str], cwd: Path) -> dict:
    """Bir asamanin gercek cagrisi: cikis kodu, kisa cikti, uretilen dosyalar."""
    before = {path.name: path.stat().st_mtime for path in cwd.glob("*")}
    proc = subprocess.run([sys.executable, "-m", "drawingto3d", stage, *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=900, env=ENV)
    after = {path.name: path for path in cwd.glob("*")}
    text = (proc.stdout or "") + (proc.stderr or "")
    return {
        "stage": stage,
        "args": args,
        "exit": proc.returncode,
        "output_tail": text.strip().splitlines()[-4:],
        "new_files": sorted(name for name in after if before.get(name) != after[name].stat().st_mtime),
    }


def _case(name: str, sources: list[str]) -> dict:
    case_dir = DATA / name
    labels = json.loads((case_dir / "labels.json").read_text(encoding="utf-8"))
    row: dict = {"case": name, "labels": labels, "sources": {}}
    for source in sources:
        drawing = case_dir / f"drawing.{source}"
        if not drawing.exists():
            row["sources"][source] = {"missing": str(drawing)}
            continue
        work = OUT / name / source
        work.mkdir(parents=True, exist_ok=True)
        if source == "pdf":
            stages, stopped = [], None
            for stage in PDF_CHAIN:
                if stage == "build-general":
                    # Bu asamaya cizim degil, onceki adimin yazdigi plan veriliyor: `build-general plan out_dir`.
                    plans = sorted(work.glob("*plan*.json"))
                    if not plans:
                        stages.append({"stage": stage, "args": [], "exit": 2, "new_files": [],
                                       "output_tail": ["plan dosyası yok: önceki aşama plan yazmadı"]})
                        stopped = stage
                        break
                    args = [str(plans[-1]), str(work), "--drawing", str(drawing)]
                else:
                    args = [str(drawing), str(work)]
                step = _run(stage, args, work)
                stages.append(step)
                if step["exit"] != 0:
                    stopped = stage
                    break
            steps = sorted(path for path in work.glob("*") if path.suffix in (".step", ".stp"))
            row["sources"][source] = {
                "stages": stages,
                "stopped_at": stopped,
                "step_files": [str(path.relative_to(ROOT)) for path in steps],
                "step_bytes": [path.stat().st_size for path in steps],
            }
        else:
            step = _run("read", [str(drawing), str(work)], work)
            records = json.loads((work / "records.json").read_text(encoding="utf-8")) \
                if (work / "records.json").exists() else None
            row["sources"][source] = {
                "stages": [step],
                "stopped_at": "read" if step["exit"] != 0 else "raster_product_path_ends_here",
                "records": ({"count": len(records)} if isinstance(records, list) else
                            (sorted(records) if isinstance(records, dict) else None)),
            }
    return row


def main(argv: list[str]) -> int:
    names = argv or sorted(path.name for path in DATA.glob("pilot-*"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [_case(name, ["pdf", "png"]) for name in names]
    (OUT / "e2e.json").write_text(json.dumps({"cases": rows}, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    print(f"{'vaka':<16} {'kaynak':<5} {'durdu':<28} {'step':>5}  son cikti")
    for row in rows:
        for source, data in row["sources"].items():
            if "missing" in data:
                print(f"{row['case']:<16} {source:<5} {'dosya yok':<28} {'-':>5}")
                continue
            tail = ""
            if data["stages"]:
                lines = [line for line in data["stages"][-1]["output_tail"] if line.strip("{}[] ,")]
                tail = (max(lines, key=len) if lines else " | ".join(data["stages"][-1]["output_tail"]))[:92]
            print(f"{row['case']:<16} {source:<5} {data['stopped_at'] or 'tamam':<28} "
                  f"{len(data.get('step_files', [])):>5}  {tail}")
    print(f"\nkayit: {OUT / 'e2e.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
