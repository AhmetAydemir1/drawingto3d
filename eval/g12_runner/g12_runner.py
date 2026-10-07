"""G12 koşucu v2 sürücüsü — reçeteyi satır satır uygular, kalanı KENDİLİĞİNDEN kapatmaz (PLAN-25 §22–§25).

`produce_case.py --driver eval/g12_runner/g12_runner.py --recipe <reçete.json>` ile çağrılır:
üretici girdisi (`G12_PRODUCER_INPUT`), vaka kimliği (`G12_CASE_ID`) ve koşu dizini (`G12_ROUND_DIR`)
ortamdan gelir. Sürücü yalnız kaynak çizimi ve reçeteyi okur — referans bilgisi ne okur ne yazar.

Akış:

```text
reçete (doğrulanır) → kaynak sha256 reçeteyle eşleşir → oturum açılır
→ her eylem sırayla, YALNIZ reçetedeki kimliklere (set_disposition / bulk_set_ignored)
→ readiness okunur (kapsam kovaları kayda girer)
→ hazırsa build; değilse build YOK ve neden kayıtta
```

Yasak davranış (PLAN-25 §24): "kalanları kapsam dışı ilan et". Bu sürücüde `planned_actions()`
dışında istek üretilemez; kalan satırlar çözülmemiş kalır ve readiness onları blok olarak gösterir.
Kayıt bunu açık söyler (`remaining_closed_automatically: false`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from recipe_v2 import RecipeError, load, planned_actions  # noqa: E402

APP = os.environ.get("G12_APP", "http://127.0.0.1:8765")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:  # noqa: BLE001 — HEAD kaydı kanıttır; yokluğu koşuyu durdurmaz
        return "unknown"


class HttpTransport:
    """Uygulamanın HTTP yüzeyi (PLAN-25 §22): oturum açma + callout komutu + readiness + build."""

    def __init__(self, app: str = APP):
        self.app = app.rstrip("/")

    def _post(self, path: str, payload: dict | None = None, raw: bytes | None = None) -> dict:
        if raw is not None:
            body, headers = raw, {"Content-Type": "application/octet-stream"}
        else:
            body = json.dumps(payload, ensure_ascii=False).encode()
            headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(self.app + path, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            try:
                message = json.loads(detail).get("error")
            except Exception:  # noqa: BLE001 — gövde JSON değilse ham metin kayda geçer
                message = detail
            raise RuntimeError(f"{path}: {message or error}") from error

    def open(self, payload: bytes) -> dict:
        return self._post("/api/guided/open", raw=payload)

    def command(self, token: str, revision: int, action: str, payload: dict) -> dict:
        return self._post("/api/guided/callout",
                          {"token": token, "revision": revision, "action": action, "payload": payload})

    def strategy(self, token: str, revision: int, payload: dict) -> dict:
        """`/api/guided/strategy` (G12R-05): gövde `{token, revision, kind}` — anahtarı sunucu yazar."""
        return self._post("/api/guided/strategy", {"token": token, "revision": revision, **payload})

    def readiness(self, token: str) -> dict:
        return self._post("/api/guided/readiness", {"token": token})

    def build(self, token: str, revision: int) -> dict:
        return self._post("/api/guided/build", {"token": token, "revision": revision})


def run_recipe(recipe: dict, transport, *, source_path: pathlib.Path, case_id: str | None = None,
               out_dir: pathlib.Path | None = None, build_if_ready: bool = True) -> dict:
    """Reçeteyi uygula ve koşu kaydını döndür — saf akış, taşıma parametredir (testler saplama verir)."""
    requests = planned_actions(recipe)
    record = {
        "case_id": case_id or recipe.get("case_id"), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_head": git_head(), "source_path": str(source_path),
        "source_sha256_recipe": recipe.get("source_sha256"), "source_sha256_file": None,
        "source_sha256_checked": False, "session_token": None, "candidate_count": None,
        "effective_callout_count": None, "planned_requests": len(requests), "actions": [],
        "coverage": None, "readiness_ready": None, "readiness_questions": [],
        "build_status": None, "remaining_closed_automatically": False,
        "action_ids": [], "failures": [], "notes": [],
    }

    def fail(code: str, detail) -> None:
        record["failures"].append({"code": code, "detail": detail})

    try:
        digest = sha256_file(pathlib.Path(source_path))
    except OSError as error:
        fail("source-unreadable", str(error))
        return _write(record, out_dir)
    record["source_sha256_file"] = digest
    record["source_sha256_checked"] = digest == recipe.get("source_sha256")
    if not record["source_sha256_checked"]:
        fail("source-sha-mismatch", {"file": digest, "recipe": recipe.get("source_sha256")})
        return _write(record, out_dir)

    try:
        state = transport.open(pathlib.Path(source_path).read_bytes())
    except Exception as error:  # noqa: BLE001 — oturum açılamadıysa koşu burada biter
        fail("session-open-failed", str(error))
        return _write(record, out_dir)
    token = state.get("token")
    record["session_token"] = token
    record["candidate_count"] = len(state.get("callout_candidates") or [])
    record["effective_callout_count"] = len(state.get("effective_callouts") or [])

    for item in requests:
        entry = {"http_action": item["http_action"], "reason": item["reason"],
                 "callout_id": item["payload"].get("callout_id"),
                 "callout_ids": item["payload"].get("callout_ids"), "revision_before": state.get("revision"),
                 "ok": False, "error": None}
        try:
            if item["http_action"] == "set_strategy":
                state = transport.strategy(token, state.get("revision"), item["payload"])
            else:
                state = transport.command(token, state.get("revision"), item["http_action"],
                                          item["payload"])
            entry["ok"] = True
            entry["revision_after"] = state.get("revision")
        except Exception as error:  # noqa: BLE001 — reddedilen eylem kayda geçer ve koşu DURUR
            entry["error"] = str(error)
            record["actions"].append(entry)
            fail("action-refused", {"action": item["http_action"], "detail": str(error)})
            return _write(record, out_dir)
        record["actions"].append(entry)
        if item["payload"].get("callout_ids") or item["payload"].get("callout_id"):
            record["action_ids"].extend(item["payload"].get("callout_ids")
                                        or [item["payload"].get("callout_id")])
    record["effective_callout_count"] = len(state.get("effective_callouts") or [])
    record["coverage"] = state.get("coverage")

    try:
        readiness = transport.readiness(token)
    except Exception as error:  # noqa: BLE001 — readiness okunamazsa build denenmez
        fail("readiness-unreadable", str(error))
        return _write(record, out_dir)
    record["readiness_ready"] = bool(readiness.get("ready"))
    record["readiness_questions"] = [{"category": row.get("category"), "callout_id": row.get("callout_id")}
                                     for row in readiness.get("questions") or []]
    record["coverage"] = readiness.get("coverage") or record["coverage"]

    if not record["readiness_ready"]:
        # PLAN-25 §24: kalan satırlar KAPATILMAZ; build yok ve neden kayıtta durur.
        record["build_status"] = "skipped:not-ready"
        return _write(record, out_dir)
    if not build_if_ready:
        record["build_status"] = "skipped:disabled"
        return _write(record, out_dir)
    try:
        built = transport.build(token, state.get("revision"))
        record["build_status"] = built.get("build_status") or ("complete" if built.get("step") else "unknown")
        record["build_error"] = built.get("error")
    except Exception as error:  # noqa: BLE001 — build reddi kayda geçer
        record["build_status"] = "refused"
        record["build_error"] = str(error)
    return _write(record, out_dir)


def _write(record: dict, out_dir: pathlib.Path | None) -> dict:
    if out_dir is not None:
        out_dir = pathlib.Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "g12-run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    return record


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="G12 koşucu v2: reçeteyi satır satır uygular")
    parser.add_argument("recipe")
    parser.add_argument("--round", default=None, help="koşu dizini (varsayılan: G12_ROUND_DIR)")
    parser.add_argument("--app", default=APP)
    parser.add_argument("--no-build", action="store_true", help="hazır olsa bile build denemez")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        recipe = load(args.recipe)
    except RecipeError as error:
        print(f"[RECIPE-REFUSED] {error}", file=sys.stderr, flush=True)
        return 2
    producer_path = os.environ.get("G12_PRODUCER_INPUT")
    case_id = os.environ.get("G12_CASE_ID") or recipe["case_id"]
    source_path = None
    if producer_path and pathlib.Path(producer_path).is_file():
        producer = json.loads(pathlib.Path(producer_path).read_text(encoding="utf-8"))
        source_path = ROOT / producer["source_path"]
        if producer.get("case_id") != recipe["case_id"]:
            print(f"[BOUNDARY] üretici girdisi başka vaka: {producer.get('case_id')} != {recipe['case_id']}",
                  file=sys.stderr, flush=True)
            return 2
    if source_path is None:
        print("[BOUNDARY] G12_PRODUCER_INPUT yok: koşucu kaynağını üretici girdisinden alır",
              file=sys.stderr, flush=True)
        return 2
    round_dir = args.round or os.environ.get("G12_ROUND_DIR")
    out_dir = pathlib.Path(round_dir) / "cases" / case_id if round_dir else None
    record = run_recipe(recipe, HttpTransport(args.app), source_path=pathlib.Path(source_path),
                        case_id=case_id, out_dir=out_dir, build_if_ready=not args.no_build)
    print(json.dumps({key: record[key] for key in ("case_id", "planned_requests", "readiness_ready",
                                                   "build_status", "failures")}, ensure_ascii=False), flush=True)
    return 1 if record["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
