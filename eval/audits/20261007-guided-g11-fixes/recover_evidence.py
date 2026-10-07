"""G11R-04 — recover the evidence the official run failed to record, labeled as recovered.

    .venv/bin/python eval/audits/20261007-guided-g11-fixes/recover_evidence.py

The official G11 run wrote `session-public.json`/`review-bundle.json` only when a STEP came out, so
the failed cases (exercise-13, exercise-17, my-part, the reference-free elbow — whichever records
lack the files) carry no session/readiness evidence. The sessions themselves are still on disk and
unchanged. This script — read-only against `out/guided` — rebuilds for each such case:

  session-public.json      the session's last public state
  review-bundle.json       the review export bundle
  readiness.json           the readiness payload the build gate used
  server-error-recompute.json  the refusal text the build endpoint would answer with, replayed
                               read-only through the same gate chain (the run-time HTTP body was
                               never recorded); labeled as recomputed
  RECOVERY.json            the explicit recovered-after-run label: time, source, hash check

Old case records and old evidence are NOT modified; everything here lands under
`recovered/<case_id>/` in the G11 audit directory. Exit non-zero when a case cannot be matched or an
evidence file comes out empty.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d import callout_compile, callout_readiness, guided  # noqa: E402

G11 = ROOT / "eval/audits/20261007-guided-g11"
OUT = G11 / "recovered"
RECORD_EVIDENCE = ("session-public.json", "review-bundle.json")


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def needs_recovery(record: dict) -> bool:
    artifacts = record.get("artifacts") or {}
    return any(not (artifacts.get(name) and (ROOT / artifacts[name]).exists())
               for name in RECORD_EVIDENCE)


def find_session(record: dict) -> tuple[pathlib.Path | None, list[dict]]:
    """Session directories whose stored source digest matches the record (candidates reported)."""
    candidates = []
    for session_file in sorted((ROOT / "out/guided").glob("*/session.json")):
        try:
            data = load_json(session_file)
        except ValueError:
            continue
        if data.get("source_sha256") == record.get("source_sha256"):
            candidates.append({"token": session_file.parent.name,
                               "mtime": session_file.stat().st_mtime,
                               "revision": data.get("revision")})
    if not candidates:
        return None, []
    candidates.sort(key=lambda row: row["mtime"], reverse=True)
    return ROOT / "out/guided" / candidates[0]["token"], candidates


def recompute_refusal(store: guided.GuidedStore, token: str) -> dict:
    """Replay build()'s pre-side-effect gates read-only and keep the text each gate would raise."""
    r = store.load(token)
    result = {"recomputed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
              "how": "build() kapı zinciri okuma modunda oynatıldı (revizyon → geometry_stale → "
                     "hazırlık → çakışma → make_plan); koşu anında HTTP gövdesi kaydedilmemişti.",
              "message": None, "gate": None}
    try:
        if r.get("geometry_stale"):
            result.update(gate="geometry_stale", message="temel geometri kaynaktan yenilenemedi ("
                          + str((r["geometry_stale"] or {}).get("reason")) + ")")
            return result
        readiness = callout_readiness.build_readiness(r, sheet_issues=guided._sheet_issues(r))
        result["readiness_ready"] = readiness["ready"]
        result["readiness_questions"] = [row["text"] for row in readiness["questions"]]
        if not readiness["ready"]:
            result.update(gate="readiness", message="üretim için eksik/uyumsuz girdiler var: "
                          + " ".join(row["text"] for row in readiness["questions"][:3]))
            return result
        compiled = callout_compile.compile_callouts(r)
        result["conflicts"] = [str(item.get("detail") or item.get("reason"))
                               for item in compiled["conflicts"][:3]]
        if compiled["conflicts"]:
            result.update(gate="conflicts", message="callout kararları çelişiyor: "
                          + " ".join(result["conflicts"]))
            return result
        try:
            guided.make_plan({**r, "decisions": callout_compile.apply_compiled(r["decisions"], compiled)})
            result.update(gate="none",
                          message="kapılar okuma modunda geçti; koşudaki 400 başka bir katmandan "
                                  "gelmiş olmalı (ör. eşzamanlı revizyon) — kayıtta yalnız HTTP 400 var.")
        except Exception as error:  # noqa: BLE001 — make_plan's refusal is the recorded cause
            result.update(gate="make_plan",
                          message=f"{type(error).__name__}: {error}")
    except Exception as error:  # noqa: BLE001 — a replay failure is itself reported, never hidden
        result.update(gate="replay-error", message=f"{type(error).__name__}: {error}")
    return result


def recover_case(store: guided.GuidedStore, record: dict, record_path: pathlib.Path) -> dict:
    case_id = record["case_id"]
    session_dir, candidates = find_session(record)
    if session_dir is None:
        return {"case_id": case_id, "status": "no-session", "candidates": []}
    token = session_dir.name
    session = load_json(session_dir / "session.json")
    # Read-only guard: Store.load() can migrate (and rewrite) a session whose geometry version is
    # old. Recovery must never modify old evidence, so such a session is skipped, not migrated.
    if session.get("geometry_version") != guided.GEOMETRY_VERSION \
            and not session.get("geometry_stale"):
        return {"case_id": case_id, "status": "skipped-migration-needed",
                "session_geometry_version": session.get("geometry_version"),
                "current": guided.GEOMETRY_VERSION, "token": token}
    target = OUT / case_id
    target.mkdir(parents=True, exist_ok=True)
    session_sha_before = _sha256(session_dir / "session.json")
    public = store.public(store.load(token))
    bundle = store.review_export(token)
    readiness = store.readiness(token)
    refusal = recompute_refusal(store, token)
    session_sha_after = _sha256(session_dir / "session.json")
    (target / "session-public.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "review-bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "server-error-recompute.json").write_text(
        json.dumps(refusal, ensure_ascii=False, indent=2), encoding="utf-8")
    recovered_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    label = {
        "case_id": case_id,
        "label": "recovered-after-run",
        "not_run_time_evidence": True,
        "recovered_at": recovered_at,
        "recovered_by": "G11R-04 düzeltme turu (eval/audits/20261007-guided-g11-fixes)",
        "recovered_from": str(session_dir.relative_to(ROOT) / "session.json"),
        "session_token": token,
        "source_sha256_match": session.get("source_sha256") == record.get("source_sha256"),
        "session_file_sha256_before": session_sha_before,
        "session_file_sha256_after": session_sha_after,
        "session_untouched": session_sha_before == session_sha_after,
        "session_candidates": candidates,
        "original_run": {"run_id": record.get("run_id"), "at": record.get("at"),
                         "git_head": record.get("git_head")},
        "original_record": {
            "artifacts": record.get("artifacts") or {},
            "failures": record.get("failures") or [],
            "console_errors": record.get("console_errors") or [],
            "rejected_requests": record.get("rejected_requests") or [],
            "note": f"eski kayıt olduğu gibi bırakıldı: {record_path.relative_to(ROOT)}",
        },
        "files": {
            "session-public.json": "koşu anında kaydedilmemişti; değişmemiş oturumun son "
                                   "durumundan yeniden üretildi",
            "review-bundle.json": "koşu anında kaydedilmemişti; inceleme paketinden yeniden üretildi",
            "readiness.json": "koşu anında kaydedilmemişti; hazırlık uç noktasından yeniden alındı",
            "server-error-recompute.json": "sunucunun koşu-anı yanıt gövdesi kayıtlı değil; aynı "
                                           "kapı zinciri okuma modunda yeniden oynatıldı",
        },
        "note": "Bu kanıt sonradan kurtarıldı: gerçekliği değişmemiş oturum kaydıyla sınırlıdır ve "
                "koşu anında kaydedilmiş gibi sunulmaz (G11R-04).",
    }
    (target / "RECOVERY.json").write_text(json.dumps(label, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return {"case_id": case_id, "status": "recovered", "token": token,
            "source_sha256_match": label["source_sha256_match"],
            "session_untouched": label["session_untouched"],
            "refusal_gate": refusal.get("gate"), "refusal_message": refusal.get("message"),
            "candidates": len(candidates),
            "files": sorted(name for name in
                            (path.name for path in target.iterdir()) if name.endswith(".json"))}


def main() -> int:
    store = guided.GuidedStore(ROOT / "out/guided")
    summary = []
    for record_path in sorted((G11 / "cases").glob("*.json")):
        record = load_json(record_path)
        if not needs_recovery(record):
            summary.append({"case_id": record["case_id"], "status": "already-recorded"})
            continue
        summary.append(recover_case(store, record, record_path))
    bad = [row for row in summary if row["status"] not in ("already-recorded", "recovered")]
    (OUT / "recovery-summary.json").write_text(
        json.dumps({"recovered_at_case_list": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    for row in summary:
        line = f"{row['case_id']}: {row['status']}"
        if row["status"] == "recovered":
            line += (f" (token …{row['token'][-6:]}, hash={'ok' if row['source_sha256_match'] else 'FARKLI'}"
                     f", untouched={'evet' if row['session_untouched'] else 'HAYIR'}"
                     f", gate={row['refusal_gate']})")
        print(line, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
