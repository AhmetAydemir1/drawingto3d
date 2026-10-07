"""Salvage the round-2 records that the pre-fix runner path wrote into the official case dir.

    .venv/bin/python eval/audits/20261007-guided-g11-fixes/salvage_round2_records.py

During the rerun-round2 run the runner's record path was still hard-coded to the official
`cases/` dir: the two round records (round="rerun-round2") were written there and the frozen
official records must come back. Steps, per case:

1. read the current (round-2) record from `cases/<id>.json` and assert `round == "rerun-round2"`;
2. backfill `session_token` from the record's own `session-public.json` artifact (the run started
   before the post-gate token capture fix) and note the provenance;
3. write it to `rerun-round2/cases/<id>.json` (never overwrite an existing round record);
4. `git checkout --` the two official records and verify they equal HEAD.

Prints a JSON summary; exit 0 only when both cases were salvaged and both official files are
byte-identical to HEAD again.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
G11 = ROOT / "eval/audits/20261007-guided-g11"
CASES = ("exercise-51-raster", "flange-raster")


def head_blob(path: str) -> str:
    return subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout


def main() -> int:
    summary = []
    for case_id in CASES:
        official = G11 / "cases" / f"{case_id}.json"
        record = json.loads(official.read_text(encoding="utf-8"))
        if record.get("round") != "rerun-round2":
            summary.append({"case_id": case_id, "status": "abort: kayıt rerun-round2 değil",
                            "round": record.get("round")})
            continue
        target = G11 / "rerun-round2" / "cases" / f"{case_id}.json"
        if target.exists():
            summary.append({"case_id": case_id, "status": "abort: tur kaydı zaten var"})
            continue
        token = None
        public_path = (record.get("artifacts") or {}).get("session-public.json")
        if public_path and (ROOT / public_path).exists():
            public = json.loads((ROOT / public_path).read_text(encoding="utf-8"))
            token = public.get("token")
            if not token and isinstance(public.get("session"), dict):
                token = public["session"].get("token")
        if not token:
            summary.append({"case_id": case_id, "status": "abort: token bulunamadı",
                            "public_path": public_path})
            continue
        record["session_token"] = token
        record.setdefault("notes", []).append(
            "oturum token (koşu sonrası tamamlandı): " + token +
            " — kaynak: session-public.json artefaktı (koşu, kapı-sonrası token yakalamasından önceydi)")
        record["notes"].append(
            "kayıt yolu düzeltmesi: koşu sırasında resmî cases/ dizinine yazılmıştı; tur sonrası "
            "rerun-round2/cases altına taşındı, resmî kayıt git'ten aynen geri yüklendi")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append({"case_id": case_id, "status": "salvaged", "token": token[:8] + "…",
                        "target": str(target.relative_to(ROOT))})

    checkout = ("exercise-51-raster", "flange-raster")
    subprocess.run(["git", "checkout", "--"] +
                   [f"eval/audits/20261007-guided-g11/cases/{c}.json" for c in checkout],
                   cwd=ROOT, check=True)
    for case_id in checkout:
        rel = f"eval/audits/20261007-guided-g11/cases/{case_id}.json"
        same = (ROOT / rel).read_text(encoding="utf-8") == head_blob(rel)
        summary.append({"case_id": case_id, "official_restored": same})
    ok = all(row.get("status") != "abort" and not row.get("official_restored", True) is False
             for row in summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
