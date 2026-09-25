"""Eval report: what the pipeline read, and what it built, against the ground truth.

    .venv-cad/bin/python eval/report.py            # table on stdout, JSON in out/eval/report.json

Reading side compares every dimension record with the numbers a human can read on the sheet
(eval/cases.json). Building side compares out/eval/<case>/part.step with the case's reference STEP.
A case with no reference STEP is reading-only; a case with no built part says so instead of scoring 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402 - sibling script, same directory

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).resolve().parent / "cases.json"
BASELINE = ROOT / "out" / "baseline"
BUILT = ROOT / "out" / "eval"
REPORT = ROOT / "out" / "eval" / "report.json"

IN_MM = 25.4


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    rows = [_case(case) for case in cases]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"cases": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    _print(rows)
    print(f"\nrapor: {REPORT}")


def _case(case: dict) -> dict:
    row = {
        "id": case["id"],
        "class": case["class"],
        "unit": case["unit"],
        "printed": case["printed"],
        "reading": _reading(case),
        "truth": None,
        "built": None,
        "verdict": None,
    }
    truth_path = ROOT / case["step"] if case.get("step") else None
    if truth_path and truth_path.is_file():
        try:
            row["truth"] = metrics.describe(truth_path)
        except Exception as exc:  # noqa: BLE001 - a broken reference is reported, not raised
            row["truth"] = {"error": f"{type(exc).__name__}: {exc}"}
    built_path = BUILT / case["id"] / "part.step"
    if built_path.is_file():
        try:
            row["built"] = metrics.describe(built_path)
        except Exception as exc:  # noqa: BLE001
            row["built"] = {"error": f"{type(exc).__name__}: {exc}"}
    if row["truth"] and row["built"] and "error" not in row["truth"] and "error" not in row["built"]:
        row["verdict"] = metrics.compare(row["built"], row["truth"])
    return row


def _reading(case: dict) -> dict:
    """Every record the reader produced, split into 'a printed number' and 'noise'."""
    path = BASELINE / f"{case['id']}.json"
    if not path.is_file():
        return {"status": "okunmadı", "records": 0, "found": [], "missing": case["printed"], "noise": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("error"):
        return {"status": "hata", "records": 0, "found": [], "missing": case["printed"], "noise": [], "error": data["error"]}
    printed = list(case["printed"])
    if case["unit"] == "in":
        candidates = [{value, round(value * IN_MM, 3)} for value in printed]
    else:
        candidates = [{float(value)} for value in printed]
    records = data.get("records") or []
    found: list[float] = []
    noise: list[dict] = []
    for record in records:
        value = float(record["value"])
        hit = next((printed[index] for index, group in enumerate(candidates) if _in(value, group)), None)
        if hit is None:
            noise.append({"text": record["text"], "value": value, "role": record["role"]})
        elif hit not in found:
            found.append(hit)
    return {
        "status": "okundu",
        "records": len(records),
        "seconds": data.get("seconds"),
        "found": sorted(found),
        "missing": sorted(set(printed) - set(found)),
        "noise": noise,
        "roles": _roles(records),
    }


def _roles(records: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for record in records:
        counts[record["role"]] = counts.get(record["role"], 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def _in(value: float, group: set[float]) -> bool:
    return any(abs(value - option) < 1e-6 for option in group)


def _key(case: dict) -> str:
    """Baseline files are named after the sheet, not the eval id: 2389K26.pdf -> 2389K26."""
    return Path(case["drawing"]).stem.split("_")[0]


def _print(rows: list[dict]) -> None:
    print(f"{'durum':<10} {'durum':<6} {'okunan':<8} {'basılı':<24} {'bulunan':<16} {'eksik':<16} {'gürültü'}")
    for row in rows:
        reading = row["reading"]
        found = metrics._fmt(reading["found"]) if reading["found"] else "-"
        missing = metrics._fmt(reading["missing"]) if reading["missing"] else "-"
        noise = ", ".join(f"{item['text']}->{item['value']:g}" for item in reading.get("noise", [])) or "-"
        print(f"{row['id']:<28} {reading['status']:<6} {reading.get('records', 0):<8} {metrics._fmt(row['printed']):<24} {found:<16} {missing:<16} {noise}")

    print("\nkatı:")
    for row in rows:
        if row["verdict"] is None:
            state = "referans yok" if not row["truth"] else "katı üretilmedi"
            print(f"  {row['id']:<28} {state}")
            continue
        verdict = row["verdict"]
        mark = "GEÇTİ" if verdict["pass"] else ("şekil" if verdict["shape_ok"] else "KALDI")
        detail = "; ".join(
            f"{name}={'ok' if check['ok'] else 'yok'}" for name, check in verdict["checks"].items()
        )
        print(f"  {row['id']:<28} {mark:<6} {detail}")
        for name, check in verdict["checks"].items():
            if not check["ok"]:
                print(f"      {name}: {check['got']}  beklenen {check['want']}")


if __name__ == "__main__":
    main()
