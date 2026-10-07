"""G11R-04/G11R-05 — failure classification + always-recorded evidence (pure stdlib).

Imported by `g11_runner.py` (which drives real Chrome under the cdp venv) and loaded directly by the
regression suite under the project's own interpreter — so nothing here imports third-party code.

G11R-05 (independent review): a console or network error is not an evaluator failure. `classify_signals`
splits the raw browser signals into UI telemetry buckets:

  · `assets`       — auxiliary resource noise (favicon, /static/*): kept as UI telemetry, never a
                     failure code;
  · `api_failures` — HTTP >= 400 on /api/*: real server interactions recorded with status and URL
                     (the build's own root cause is additionally captured as the server's response
                     body/`error` text in `classify_build_error`);
  · `page_errors`  — in-page JS errors (an actual script error, not a resource 404);
  · `cancelled`    — aborted requests (status 0/empty url), e.g. the runner's own tab hygiene.

The `EVALUATOR` label belongs to the evaluator subprocess/parse/compare path alone (g11_runner.py).

G11R-04 (independent review): the evidence files that must exist per case no matter how the build
ended — `write_case_evidence` writes them; only the STEP/plan downloads stay gated on a real build.
`recovered_note` labels evidence that was reconstructed after the run instead of being recorded at
run time.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

EVIDENCE_ALWAYS = ("session-public.json", "review-bundle.json", "readiness.json")
EVIDENCE_BUILD_GATED = ("part.step", "plan.json", "plan-audit.json")


def _path_of(url: str) -> str:
    url = url or ""
    if "://" in url:
        url = "/" + url.split("://", 1)[1].split("/", 1)[-1] if "/" in url.split("://", 1)[1] else "/"
    return url.split("?", 1)[0]


def _is_asset(path: str) -> bool:
    return path.endswith("favicon.ico") or path.startswith("/static/")


def classify_signals(console_errors, rejected_requests) -> dict:
    """Split raw browser signals into telemetry buckets. Never mints a failure code."""
    assets: dict[str, dict] = {}
    api_failures: list[dict] = []
    page_errors: list[dict] = []
    cancelled: list[dict] = []
    api_seen: set[tuple] = set()
    page_seen: set[str] = set()

    def add_asset(path: str, entry: dict) -> None:
        current = assets.get(path)
        if current is None or (current.get("status") is None and entry.get("status") is not None):
            assets[path] = entry

    def add_api(entry: dict) -> None:
        key = (entry.get("status"), entry.get("url"))
        if key not in api_seen:
            api_seen.add(key)
            api_failures.append(entry)

    for row in console_errors or []:
        text = row.get("text") or ""
        url = row.get("url") or ""
        path = _path_of(url)
        if row.get("source") == "network" or "Failed to load resource" in text:
            entry = {"status": None, "url": url, "text": text[:200]}
            if path.startswith("/api/"):
                add_api(entry)
            else:  # favicon/static/other resource noise is UI telemetry
                add_asset(path or text[:80], entry)
        elif row.get("level") == "error":
            key = text[:300]
            if key not in page_seen:
                page_seen.add(key)
                page_errors.append({"text": key, "source": row.get("source") or ""})

    for row in rejected_requests or []:
        status = row.get("status") or 0
        url = row.get("url") or ""
        path = _path_of(url)
        entry = {"status": status, "url": url, "request": row.get("request")}
        if status == 0 and not url:
            cancelled.append(entry)
        elif _is_asset(path):
            add_asset(path, entry)
        elif path.startswith("/api/"):
            add_api(entry)
        else:
            add_asset(path or url, entry)

    return {"assets": list(assets.values()), "api_failures": api_failures,
            "page_errors": page_errors, "cancelled": cancelled}


def classify_build_error(error_text) -> tuple[str, str]:
    """G11R-05: the build's failure code follows its real cause — the server's own response text."""
    text = str(error_text or "")
    if "çeliş" in text:
        return "CONSTRAINT_CONFLICT", "callout kararları çelişiyor (sunucu yanıtı)"
    if "eksik/uyumsuz" in text or "hazır" in text and "değil" in text:
        return "CONSTRAINT_UNSUPPORTED", "hazırlık kapısı reddetti (sunucu yanıtı)"
    if "geometri" in text:
        return "CAD_UNSUPPORTED", "temel geometri kullanılamıyor (sunucu yanıtı)"
    return "CAD_UNSUPPORTED", "üretim sunucu tarafında durdu (sunucu yanıtı)"


def write_case_evidence(out_dir: pathlib.Path, session_public: dict, review_bundle: dict,
                        readiness: dict) -> list[str]:
    """Write the evidence files that exist regardless of build success; returns their names."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "session-public.json").write_text(
        json.dumps(session_public, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "review-bundle.json").write_text(
        json.dumps(review_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    return list(EVIDENCE_ALWAYS)


def recovered_note(source: str, recovered_at: str | None = None) -> dict:
    """The explicit label for evidence reconstructed after the run — never presented as run-time."""
    return {
        "label": "recovered-after-run",
        "not_run_time_evidence": True,
        "recovered_at": recovered_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "recovered_from": source,
        "note": "Bu kanıt koşu anında kaydedilmedi; değişmemiş oturum kaydından sonradan "
                "yeniden üretildi ve bu etiketle saklandı.",
    }
