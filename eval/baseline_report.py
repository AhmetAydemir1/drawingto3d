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
        except json.JSONDecodeError as exc:
            raise ValueError(f"bozuk koşu kaydı: {path}") from exc
        record["_path"] = path
        records.append(record)
    records.sort(key=lambda record: record.get("run", {}).get("started") or "")
    return records


def _seconds(value) -> str:
    return f"{value:.1f}" if isinstance(value, (int, float)) else "-"


def _interface(record: dict, run: dict) -> str:
    """Which interface asked the question, read from the record rather than guessed from one flag.

    A run that asked one nested body, three narrower calls and a run that rewrote the answer's own
    names are three different measurements of the same case; a table that prints one word for all of
    them makes the numbers look comparable when they are not.
    """
    observed = set()
    for row in record.get("results") or []:
        settings = row.get("stages", {}).get("plan", {}).get("settings", {}) or {}
        actual = settings.get("response_format", "")
        if "split" in actual:
            # Two split interfaces have been measured: three calls, and one call per measured closed
            # profile. The record's own settings say which one asked, so the table cannot present the
            # second as the first. A run that predates the per-profile step carries no marker.
            observed.add("adım başına profil" if settings.get("profile_targets") else "üç adımlı")
        elif actual.startswith("json-schema"):
            observed.add("json-schema")
        elif actual == "text":
            observed.add("serbest metin")
    if observed:
        return ("karma: " if len(observed) > 1 else "") + " / ".join(sorted(observed))
    interface = record.get("plan_interface")
    if interface == "split-per-profile":
        return "adım başına profil"
    if interface == "split-3-call":
        return "üç adımlı"
    if interface == "free-text":
        return "serbest metin"
    if interface == "json-schema":
        return "json-schema"
    return "json-schema" if run.get("structured_output") else "serbest metin"


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
        if "relations" in (run.get("conditions") or []):
            model = f"{model} *"
        interface = _interface(record, run)
        if run.get("name_normalization") and run["name_normalization"] != "off":
            # The answer's own names were rewritten before judging: a different interface, so a
            # different measurement, and the table has to say which one a number came from.
            interface += " + ad yazımı"
        lines.append(
            "| {id} | {started} | {model} | {conditions} | {schema} | {cases} | {statuses} | {classes} | {secs} |".format(
                id=run.get("id", "?"),
                started=(run.get("started") or "")[:16].replace("T", " "),
                model=model,
                conditions=",".join(run.get("conditions") or []),
                schema=interface,
                cases=len({row.get("case") for row in results}),
                statuses=(f"[{run.get('status', 'legacy')}] "
                          + (" ".join(f"{key}={value}" for key, value in sorted(statuses.items())) or "-")),
                classes=" ".join(f"{key}={value}" for key, value in sorted(classes.items())) or "-",
                secs=_seconds(run.get("seconds")),
            )
        )
    lines.append("")
    lines.append("`*` koşunun bağlamı kısmen elle doğrulanmış ilişki tablosundan gelir (`eval/relations/`): "
                 "o koşu otomatik PDF → STEP başarısı değil, planlama ve CAD katmanlarının ayrı ölçümüdür "
                 "(PLAN Bölüm 18B).")
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
        "| koşu | kullanılan takas başı MiB | kullanılan takas tepe MiB | boş sayfa en az MiB | ollama RSS tepe MiB |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in records:
        resources = record.get("resources") or {}
        run_id = (record.get("run") or {}).get("id", "?")
        if resources.get("measurement_version") != 2:
            lines.append(f"| {run_id} | geçersiz eski ölçüm | geçersiz eski ölçüm | geçersiz eski ölçüm | "
                         f"{resources.get('ollama_rss_mb_peak', '-')} |")
            continue
        lines.append(
            f"| {run_id} | {resources.get('swap_used_mb_start', '-')} | {resources.get('swap_used_mb_peak', '-')} | "
            f"{resources.get('pages_free_mb_min', '-')} | {resources.get('ollama_rss_mb_peak', '-')} |"
        )
    lines += ["", "Eski swap alanları `used` yerine `total` okuyordu; sayfa hesabı sabit 4096 bayt "
              "varsayıyordu. Bu değerler kaynak kayıtlarda korunur, bellek kararı için kullanılmaz. "
              "Ölçüm v2 işletim sisteminin sayfa boyutunu ve `used` alanını kullanır. Sistem sayıları "
              "diğer uygulamaları da içerir; Ollama RSS toplam birleşik bellek tüketimi değildir."]
    return lines


def block() -> str:
    records = runs()
    parts = [OPEN, ""]
    if not records:
        parts += ["Henüz kayıtlı koşu yok.", ""]
    else:
        parts += ["### Koşular", ""] + run_table(records) + [""]
        parts += ["### Vaka vaka", ""] + case_table(records) + [""]
        parts += ["### Koşu kaynakları (ölçüm sürümü denetlenir)", ""] + resources_table(records) + [""]
    parts += ["### Okuma tabanı (kapı sonrası kapsam)", "",
              "Katman `vektör` = PDF'in kendi metin katmanı, `raster` = görüntüden okuma. Kapsam, "
              "sayısal değer kümesinin kapsamıdır; her ölçü örneğinin, sembolün veya bağın doğruluğu değildir.",
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
