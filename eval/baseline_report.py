"""The section 7 tables, built from the run records themselves.

    PYTHONPATH=src .venv/bin/python eval/baseline_report.py --write   # fill the generated block
    PYTHONPATH=src .venv/bin/python eval/baseline_report.py --check   # fail if it has drifted

A measurement report whose numbers were typed by hand is a claim, not a measurement: the numbers in
`eval/reports/model-baseline.md` come from `out/model-baseline/*/run.json` (one file per run, written by
`eval/model_baseline.py`) and from `out/frontend/*.json` (the reading condition's per-case records). `--check`
is the same comparison the README tables get: a run that changes a number leaves the report stale, and reading
it as current is how a stale number becomes a decision.

The narrative around the block is written by hand, because what the numbers mean is not derivable from them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "out" / "model-baseline"
FRONTEND = ROOT / "out" / "frontend"
REPORT = ROOT / "eval" / "reports" / "model-baseline.md"
OPEN = "<!-- generated: tables -->"
CLOSE = "<!-- /generated: tables -->"


def runs() -> list[dict]:
    records = []
    for path in sorted(RUNS.glob("*/run.json")):
        try:
            record = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        record["_path"] = path
        records.append(record)
    records.sort(key=lambda record: record.get("run", {}).get("started") or "")
    return records


def _seconds(value) -> str:
    return f"{value:.1f}" if isinstance(value, (int, float)) else "-"


def run_table(records: list[dict]) -> list[str]:
    lines = [
        "| koşu | başlangıç | model | koşullar | şema | vaka | sonuç | hata sınıfı | süre sn |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        run = record.get("run", {})
        results = record.get("results") or []
        statuses = record.get("statuses") or {}
        classes = record.get("error_classes") or {}
        model_block = record.get("model") or {}
        model = ((model_block.get("resolved") or {}).get("name")
                 or model_block.get("requested") or "-")
        if run.get("no_model"):
            model = "yok (model dışı)"
        if run.get("conditions") == ["relations"]:
            model = f"{model} *"
        lines.append(
            "| {id} | {started} | {model} | {conditions} | {schema} | {cases} | {statuses} | {classes} | {secs} |".format(
                id=run.get("id", "?"),
                started=(run.get("started") or "")[:16].replace("T", " "),
                model=model,
                conditions=",".join(run.get("conditions") or []),
                schema="json-schema" if run.get("structured_output") else "serbest metin",
                cases=len({row.get("case") for row in results}),
                statuses=" ".join(f"{key}={value}" for key, value in sorted(statuses.items())) or "-",
                classes=" ".join(f"{key}={value}" for key, value in sorted(classes.items())) or "-",
                secs=_seconds(run.get("seconds")),
            )
        )
    lines.append("")
    lines.append("`*` bağlam, elle doğrulanmış ilişki tablosundan gelir (`eval/relations/`): bu koşu otomatik "
                 "PDF → STEP başarısı değil, planlama ve CAD katmanlarının ayrı ölçümüdür (PLAN Bölüm 18B).")
    return lines


def case_table(records: list[dict]) -> list[str]:
    lines = [
        "| koşu | vaka | koşul | durum | hata sınıfı | gerekçe |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        run_id = (record.get("run") or {}).get("id", "?")
        for row in record.get("results") or []:
            reason = (row.get("reason") or "").replace("|", "/").replace("\n", " ")
            if len(reason) > 150:
                reason = reason[:147] + "..."
            lines.append(
                f"| {run_id} | {row.get('case')} | {row.get('condition')} | {row.get('status')} | "
                f"{row.get('error_class') or '-'} | {reason or '-'} |"
            )
    return lines


def _count(value) -> str:
    """`printed` and `covers` are lists of numbers in the frontend records, a count elsewhere."""
    if isinstance(value, (list, tuple, dict)):
        return str(len(value))
    return str(value) if value is not None else "-"


def _anchors(span: dict) -> int:
    """The frontend records count a span's anchors; a hand-written record may list them."""
    anchors = span.get("anchors")
    if isinstance(anchors, int):
        return anchors
    return len(anchors or [])


def reading_table() -> list[str]:
    lines = [
        "| vaka | katman | span | basılı | kapsam | ankrajlı | px/mm | gürültü |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = {path.stem: json.loads(path.read_text()) for path in sorted(FRONTEND.glob("*.json"))}
    for stem, record in records.items():
        spans = record.get("spans") or []
        calibration = record.get("calibration") or {}
        px_per_mm = calibration.get("px_per_mm") if isinstance(calibration, dict) else None
        anchors = sum(1 for span in spans if _anchors(span) == 2)
        # The same sheet is read through the PDF's text layer and again as a raster; the record's own
        # `vector_text` says which, and the file name says whether a model read it. A `-raster` record only
        # measures something when the sheet has a text layer to be thrown away: for a sheet that is already
        # a scan it repeats the base measurement, so it is dropped rather than listed twice under two names.
        id_ = str(record.get("id") or "")
        suffix = stem[len(id_):].lstrip("-")
        base = records.get(id_) or {}
        if suffix == "raster" and not base.get("vector_text"):
            continue
        layer = "vektör" if record.get("vector_text") else "raster"
        if suffix == "raster":
            layer = "raster (vektör paftanın render'ı)"
        elif suffix:
            layer = f"raster ({suffix})"
        lines.append(
            "| {id} | {layer} | {spans} | {printed} | {covered}/{printed} | {anchors} | {px_per_mm} | {noise} |".format(
                id=record.get("id"),
                layer=layer,
                spans=len(spans),
                printed=_count(record.get("printed")),
                covered=len(record.get("covers") or []),
                anchors=anchors,
                px_per_mm=f"{px_per_mm:.4f}" if isinstance(px_per_mm, (int, float)) else "-",
                noise=len(record.get("noise") or []),
            )
        )
    return lines


def resources_table(records: list[dict]) -> list[str]:
    lines = [
        "| koşu | takas başı MB | takas tepe MB | boş sayfa en az MB | ollama RSS tepe MB |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in records:
        resources = record.get("resources") or {}
        run_id = (record.get("run") or {}).get("id", "?")
        lines.append(
            f"| {run_id} | {resources.get('swap_used_mb_start', '-')} | {resources.get('swap_used_mb_peak', '-')} | "
            f"{resources.get('pages_free_mb_min', '-')} | {resources.get('ollama_rss_mb_peak', '-')} |"
        )
    return lines


def block() -> str:
    records = runs()
    parts = [OPEN, ""]
    if not records:
        parts += ["Henüz kayıtlı koşu yok.", ""]
    else:
        parts += ["### Koşular", ""] + run_table(records) + [""]
        parts += ["### Vaka vaka", ""] + case_table(records) + [""]
        parts += ["### Koşu kaynakları (Apple M1, 16 GB, takas ölçülü)", ""] + resources_table(records) + [""]
    parts += ["### Okuma tabanı (kapı sonrası kapsam)", "",
              "Katman `vektör` = PDF'in kendi metin katmanı, `raster` = aynı pafta görüntüden okunmuş.",
              ""] + reading_table() + [""]
    parts += [CLOSE]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="raporun üretilen bloğunu tazele")
    parser.add_argument("--check", action="store_true", help="blok koşularla uyuşmuyorsa çıkış kodu 1")
    arguments = parser.parse_args()
    if not REPORT.exists():
        print(f"rapor yok: {REPORT}", file=sys.stderr)
        return 2
    text = REPORT.read_text()
    if OPEN not in text or CLOSE not in text:
        print(f"rapor işaretleri eksik: {OPEN} ... {CLOSE}", file=sys.stderr)
        return 2
    head, rest = text.split(OPEN, 1)
    _, tail = rest.split(CLOSE, 1)
    fresh = block()
    stale = f"{head}{fresh}{tail}"
    if arguments.check:
        if stale != text:
            print("rapor koşularla uyuşmuyor: eval/baseline_report.py --write", file=sys.stderr)
            return 1
        print("rapor koşularla uyuşuyor")
        return 0
    if arguments.write:
        REPORT.write_text(stale)
        print(f"yazıldı: {REPORT}")
        return 0
    print(fresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
