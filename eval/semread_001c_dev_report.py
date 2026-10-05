"""SEMREAD-001C — dev kapısı (§21) ve ölçüm raporu (§19/§43 araçları).

Defterden (out/lab/semread-001c) okur, 8 dev hücresinin durumunu ve §21 kapı ölçütlerini
hesaplar. **Hiçbir çağrı yapmaz.** Çıktı: stdout özeti + `--write` ile
`out/lab/semread-001c/dev-report.json` ve `dev-report.md`.

Hücre geçerliliği (§21/§44): hücrede `state == "pass"` bir attempt varsa geçerli sayılır;
hücre, en yeni pass attempt'inin kapı kanıtlarıyla raporlanır (hangi zarf revizyonunda koştuğu
`num_predict`/`num_ctx` ile birlikte). Kesilme/parse/taşıma retleri `failure_kind` ile sayılır.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = "semread-001c"
LAB = ROOT / "out/lab" / EXPERIMENT
DEV_PAGES = ("dev-plate-pocket", "dev-flange-book", "dev-flange-elbow", "dev-drawing-2")
ARMS = ("V", "VE")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def attempt_records() -> dict[str, list[dict]]:
    records: dict[str, list[dict]] = {}
    attempts_root = LAB / "attempts"
    if not attempts_root.exists():
        return records
    for cell_dir in sorted(attempts_root.iterdir()):
        if not cell_dir.is_dir():
            continue
        for attempt_dir in sorted(cell_dir.iterdir()):
            if not attempt_dir.is_dir():
                continue
            result = read_json(attempt_dir / "result.json")
            manifest = read_json(attempt_dir / "manifest.json") or {}
            resources = read_json(attempt_dir / "resources.json") or {}
            gates = read_json(attempt_dir / "gate-results.json") or {}
            parsed = read_json(attempt_dir / "response-parsed.json") or {}
            stats = resources.get("stats") or {}
            settings = manifest.get("settings") or {}
            records.setdefault(cell_dir.name, []).append({
                "attempt": attempt_dir.name,
                "state": (result or {}).get("state"),
                "failure_kind": (result or {}).get("failure_kind"),
                "blocking_kind": (result or {}).get("blocking_kind"),
                "seconds": (result or {}).get("seconds"),
                "done_reason": stats.get("done_reason"),
                "eval_count": stats.get("eval_count"),
                "prompt_eval_count": stats.get("prompt_eval_count"),
                "num_predict": settings.get("num_predict"),
                "num_ctx": settings.get("num_ctx"),
                "prompt_bytes": resources.get("prompt_bytes"),
                "response_bytes": resources.get("response_bytes"),
                "gates": {key: gates.get(key) for key in
                          ("parse", "references", "truncated", "leakage")},
                "regions_normalized": _regions_normalized(parsed),
                "candidates": len((parsed.get("items") or [])) or None,
            })
    return records


def _regions_normalized(parsed: dict) -> bool | None:
    """Parse edilmiş adayların tüm bölgeleri 0..1 içinde mi (piksel sızıntısı yok)?"""
    items = parsed.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        source = (item or {}).get("source") or {}
        for key in ("region", "callout_region"):
            region = source.get(key)
            if region is None:
                continue
            values = [region.get(k) for k in ("x0", "y0", "x1", "y1")]
            if any(not isinstance(v, (int, float)) or v < 0 or v > 1 for v in values):
                return False
        target = (item or {}).get("target") or {}
        region = target.get("region")
        if region:
            values = [region.get(k) for k in ("x0", "y0", "x1", "y1")]
            if any(not isinstance(v, (int, float)) or v < 0 or v > 1 for v in values):
                return False
    return True


def cell_view(records: list[dict]) -> dict:
    passes = [r for r in records if r["state"] == "pass"]
    chosen = passes[-1] if passes else (records[-1] if records else None)
    gates = (chosen or {}).get("gates") or {}
    parse_ok = bool((gates.get("parse") or {}).get("ok"))
    refs_ok = bool((gates.get("references") or {}).get("ok"))
    truncated = gates.get("truncated") or {}
    leakage = gates.get("leakage")
    return {
        "attempts": [{k: r[k] for k in ("attempt", "state", "failure_kind", "done_reason",
                                        "eval_count", "prompt_eval_count", "num_predict",
                                        "num_ctx", "seconds", "candidates")}
                     for r in records],
        "chosen_attempt": (chosen or {}).get("attempt"),
        "valid": bool(passes),
        "parse_ok": parse_ok,
        "references_ok": refs_ok,
        "done_reason_stop": truncated.get("done_reason") == "stop",
        "truncated_state": truncated.get("state"),
        "no_leakage": leakage == [] or leakage is None and chosen is None,
        "regions_normalized": (chosen or {}).get("regions_normalized"),
        "candidates": (chosen or {}).get("candidates"),
    }


def build_report() -> dict:
    records = attempt_records()
    cells: dict[str, dict] = {}
    rows: list[dict] = []
    for page in DEV_PAGES:
        for arm in ARMS:
            case_id = f"{page}-{arm}"
            view = cell_view(records.get(case_id, []))
            cells[case_id] = view
            rows.append({"cell": case_id, **{k: view[k] for k in
                                             ("valid", "parse_ok", "references_ok",
                                              "done_reason_stop", "regions_normalized",
                                              "no_leakage", "chosen_attempt", "candidates")}})
    gate = {
        "v_valid": sum(1 for r in rows if r["cell"].endswith("-V") and r["valid"]),
        "ve_valid": sum(1 for r in rows if r["cell"].endswith("-VE") and r["valid"]),
        "stop_all": all(r["done_reason_stop"] for r in rows if r["valid"]),
        "coordinates_all": all(r["regions_normalized"] is not False for r in rows if r["valid"]),
        "references_all": all(r["references_ok"] for r in rows if r["valid"]),
        "no_leakage_all": all(r["no_leakage"] for r in rows if r["valid"]),
    }
    gate["passed"] = (gate["v_valid"] == 4 and gate["ve_valid"] == 4 and gate["stop_all"]
                      and gate["coordinates_all"] and gate["references_all"]
                      and gate["no_leakage_all"])
    all_attempts = [r for recs in records.values() for r in recs]
    state = read_json(LAB / "state.json") or {}
    calls = state.get("live_calls") or []
    dispatched = [c for c in calls if c.get("send_state") not in
                  ("not_sent_model_mismatch", "not_sent_runtime_mismatch",
                   "not_sent_unsupported_setting")]
    by_send_state: dict[str, int] = {}
    for c in dispatched:
        by_send_state[c.get("send_state")] = by_send_state.get(c.get("send_state"), 0) + 1
    by_state: dict[str, int] = {}
    for r in all_attempts:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    truncation_kinds = [r.get("failure_kind") for r in all_attempts
                        if r["state"] in ("truncated_output",)]
    metrics = {
        "inference_dispatched": len(dispatched),
        "attempts_total": len(all_attempts),
        "by_state": by_state,
        "by_send_state": by_send_state,
        "truncated_output_count": len(truncation_kinds),
        "valid_cells": sum(1 for r in rows if r["valid"]),
        "valid_output_rate": round(sum(1 for r in rows if r["valid"]) / len(rows), 4),
        "budget": {"dev_used": sum(1 for c in dispatched if c.get("phase") == "dev"),
                   "dev_limit": 12, "final_used": sum(1 for c in dispatched
                                                      if c.get("phase") == "final"),
                   "final_limit": 20},
    }
    return {"schema": "semread-001c-dev-report/1", "cells": cells, "rows": rows,
            "gate": gate, "metrics": metrics}


def render_markdown(report: dict) -> str:
    rows = report["rows"]
    lines = ["# SEMREAD-001C — dev kapısı (§21) raporu", "",
             "| hücre | geçerli | parse | refs | stop | koord. | sızıntı | attempt | aday |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        def mark(value):
            return {True: "✓", False: "✗"}.get(value, "—")
        lines.append(f"| {r['cell']} | {mark(r['valid'])} | {mark(r['parse_ok'])} | "
                     f"{mark(r['references_ok'])} | {mark(r['done_reason_stop'])} | "
                     f"{mark(r.get('regions_normalized'))} | {mark(r['no_leakage'])} | "
                     f"{r['chosen_attempt'] or '—'} | {r['candidates'] or '—'} |")
    g = report["gate"]
    m = report["metrics"]
    lines += ["", f"**Kapı:** {'GEÇTİ' if g['passed'] else 'AÇIK'} — V {g['v_valid']}/4, "
              f"VE {g['ve_valid']}/4, stop={g['stop_all']}, koordinat={g['coordinates_all']}, "
              f"refs={g['references_all']}, sızıntı={g['no_leakage_all']}", "",
              f"**Bütçe (gönderim):** dev {m['budget']['dev_used']}/{m['budget']['dev_limit']} · "
              f"final {m['budget']['final_used']}/{m['budget']['final_limit']}",
              f"**Attempt durumları:** {m['by_state']}",
              f"**send_state:** {m['by_send_state']}",
              f"**valid_output_rate (hücre):** {m['valid_output_rate']}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="raporu deney dizinine yaz")
    args = parser.parse_args(argv)
    report = build_report()
    print(render_markdown(report))
    if args.write:
        (LAB / "dev-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        (LAB / "dev-report.md").write_text(render_markdown(report), encoding="utf-8")
        print(f"yazıldı: {LAB / 'dev-report.json'} + dev-report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
