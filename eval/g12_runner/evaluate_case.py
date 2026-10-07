"""G12 değerlendirici aşaması — üretilen STEP + tam manifest girdisi + referans STEP (PLAN-24 §8).

```bash
.venv-cad/bin/python eval/g12_runner/evaluate_case.py <produced.step> --case <case_id> \
    [--manifest <path>] [--reference <yol>|-] [--round <koşu dizini>]
```

Bu, sınırın *değerlendirici* tarafıdır: referansı yalnızca bu süreç okur ve `reference_used`
alanında açıkça söyler. Formül donmuştur — `eval/metrics.py describe/compare`, yeni tolerans icat
edilmez (PLAN-24 §85). `-` (referans yok) verdict'i null bırakır: `callout_scope_only` vaka asla
geometrik doğruluk diye raporlanmaz.

G11 `evaluate_case.py` ile aynı sözleşme; G12 kopyası tam manifest girdisini de kayda geçirir ki
hangi referansın kullanıldığı kanıtta görünsün.

Çıktı: tek JSON satırı (+ `--round` verilirse `<round>/cases/<case>/evaluate.json`) ve geri dönüş
kodu: 0 = değerlendirme tamam, 3 = değerlendirme hatası (kayıtlı verdict, sessiz yutma yok).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import metrics  # noqa: E402  — donmuş değerlendirici formülü

DEFAULT_MANIFEST = ROOT / "eval/guided_10_manifest.json"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="G12 değerlendirici aşaması (referans yalnız burada)")
    parser.add_argument("produced", help="üretilen STEP")
    parser.add_argument("--case", required=True)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--reference", default=None, help="açık referans yolu ya da '-'")
    parser.add_argument("--round", default=None, help="koşu dizini (evaluate.json buraya yazılır)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    entry = next((row for row in manifest.get("cases") or [] if row.get("case_id") == args.case), None)
    if entry is None:
        print(f"vaka manifestte yok: {args.case}", file=sys.stderr)
        return 3
    reference = args.reference if args.reference is not None else entry.get("reference_identifier_evaluator_only")
    if reference is None:
        reference = "-"

    produced = pathlib.Path(args.produced)
    result = {"case_id": args.case, "produced": str(produced), "produced_sha256": None,
              "reference_used": None if reference == "-" else str(reference),
              "scope_class": entry.get("expected_scope_class"),
              "step_reopen": True, "bbox": None, "features": None,
              "final_geometry_verdict": None, "error": None}
    try:
        result["produced_sha256"] = sha256(produced)
        first = metrics.describe(str(produced))
        second = metrics.describe(str(produced))                 # gerçek yeniden açılış
        result["step_reopen"] = bool(second["solids"] == first["solids"])
        result["bbox"] = first["vector"]
        result["features"] = {"solids": first["solids"], "valid": first["valid"], "faces": first["faces"],
                              "cylinders": first["cylinders"], "face_types": first["face_types"]}
        if reference != "-":
            result["final_geometry_verdict"] = metrics.compare(first, metrics.describe(str(reference)))
    except Exception as error:  # noqa: BLE001 — her hata modu kayıtlı verdict'tir
        result["step_reopen"] = False
        result["error"] = f"{type(error).__name__}: {error}"
    if args.round:
        target = pathlib.Path(args.round) / "cases" / args.case / "evaluate.json"
        if not target.is_absolute():
            target = ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 3 if result["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
