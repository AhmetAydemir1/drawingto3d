"""Running one job: the limits, the attempt directory, the marker, and what a result means.

A job is one experiment case. It declares the command to run, the inputs it reads, where its verdict
JSON goes and how long it may take. Every *attempt* of every job writes into its own directory —
`out/lab/runs/<run_id>/<job_id>/attempt-<n>/` — with its own manifest and its own completion marker,
so two jobs in one run cannot overwrite each other and an interrupted attempt is never mistaken for a
finished one.

What this module refuses to do:

* run a second heavy job while one is active (the slot is taken with an atomic create, not a
  read-then-write);
* execute a job whose idempotency key was already completed with a valid verdict — no re-download, no
  re-charge — while a *failed execution* stays retryable;
* accept a missing, unreadable, or unknown verdict as `pass`;
* hide a case failure behind a zero exit code, or a command failure behind a verdict;
* let a case timeout rise above the settings ceiling, or run past the whole-run deadline, or keep
  repairing one error class forever;
* leave a subprocess group behind after a timeout.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from drawingto3d_lab import LAB_VERSION, PRODUCT_VERDICTS, RUN_SCHEMA
from drawingto3d_lab.state import (Lab, atomic_write_text, code_fingerprint, data_fingerprint,
                                   idempotency_key, read_json, sha256_file, write_json)

# Files whose content decides whether a cached result is still valid. An uncommitted edit here is a
# different experiment even before it is committed.
WATCHED_FILES = ("src/drawingto3d_lab/runner.py", "src/drawingto3d_lab/state.py",
                 "src/drawingto3d_lab/generator.py", "eval/feature_metrics.py")

# Verdicts that mean the experiment itself ran and produced a result: these may be cached. Anything
# else is an execution problem and must stay retryable.
PRODUCT_OUTCOMES = ("pass", "fail", "needs_input", "unsupported", "not_evaluated")
TERMINAL_JOB_STATUSES = ("completed", "blocked")


@dataclass
class Job:
    """One experiment case."""

    id: str
    command: list[str]
    inputs: list[Path] = field(default_factory=list)
    result: str = "result.json"  # path inside the attempt directory
    timeout_seconds: int | None = None
    error_class: str | None = None
    notes: str = ""

    def as_dict(self) -> dict:
        return {"id": self.id, "command": list(self.command),
                "inputs": [str(path) for path in self.inputs], "result": self.result,
                "timeout_seconds": self.timeout_seconds, "error_class": self.error_class,
                "notes": self.notes}


def subprocess_runner(command: list[str], *, timeout: int, env: dict | None = None) -> dict:
    """The real runner: its own process group, a hard timeout, and both streams captured.

    A timeout kills the whole group, not just the direct child: a wrapper that started a compiler, a
    python worker or a download would otherwise keep running after the case was declared dead. `env`
    replaces the child's environment when the caller must hand one over (a driver running the product
    from a source tree has to set `PYTHONPATH`); None inherits this process's environment.
    """
    started = time.perf_counter()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, env=env)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return {"timed_out": False, "exit_code": process.returncode,
                "seconds": round(time.perf_counter() - started, 3),
                "stdout": _decode(stdout), "stderr": _decode(stderr), "descendants_alive": False}
    except subprocess.TimeoutExpired:
        group = _terminate_group(process)
        stdout, stderr = b"", b""
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - the group was already signalled
            pass
        return {"timed_out": True, "exit_code": None,
                "seconds": round(time.perf_counter() - started, 3),
                "stdout": _decode(stdout), "stderr": _decode(stderr),
                "descendants_alive": _group_alive(group)}


def _terminate_group(process: subprocess.Popen) -> int | None:
    """SIGTERM the whole process group, then SIGKILL it if it is still there."""
    try:
        group = os.getpgid(process.pid)
    except ProcessLookupError:
        return None
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(group, sig)
        except OSError:
            # ESRCH: nothing left. EPERM (macOS): the group leader is gone and there is no process
            # left that we can signal — which is the outcome this function is after, not a failure.
            return group
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline:
            if not _group_alive(group):
                return group
            time.sleep(0.05)
    return group


def _group_alive(group: int | None) -> bool:
    """Is there anything in this group still to signal?

    "Alive" has to mean "killpg(group, 0) worked", not "it did not say ESRCH": on macOS killing an
    already-dead group reports EPERM, so a naive check would call every reaped group alive and keep
    escalating signals for two seconds.
    """
    if group is None:
        return False
    try:
        os.killpg(group, 0)
    except OSError:
        return False
    return True


def _decode(raw) -> str:
    if raw is None:
        return ""
    return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw


class LabRunner:
    """Runs jobs under the lab root, one heavy job at a time."""

    def __init__(self, root: Path, *, root_repository: Path | None = None, runner=None,
                 free_space_mb=None, code_hash=None, clock=None) -> None:
        self.lab = Lab(Path(root))
        self.repository = Path(root_repository or Path(__file__).resolve().parents[2])
        self.runner = runner or subprocess_runner
        self.free_space_mb = free_space_mb or _free_space_mb
        self.code_hash = code_hash or (lambda: code_fingerprint(
            self.repository, [self.repository / name for name in WATCHED_FILES]))
        self.clock = clock or time.monotonic

    # -- status -----------------------------------------------------------

    def status(self) -> dict:
        state = self.lab.state()
        lock = read_json(self.lab.lock_path)
        if lock and not _alive(lock.get("pid")):
            lock = {**lock, "stale": True}
        return {
            "lab_version": LAB_VERSION,
            "root": str(self.lab.root),
            "limits": self.lab.limits(),
            "code_fingerprint": self.code_hash(),
            "heavy_job": lock,
            "jobs": state["jobs"],
            "runs": {key: dict(record) for key, record in state["runs"].items()},
        }

    def next_job(self, jobs: list[Job]) -> dict:
        """The single next thing to do, with its reason."""
        state = self.lab.state()
        for job in jobs:
            record = state["jobs"].get(job.id)
            if record is None or record.get("status") not in TERMINAL_JOB_STATUSES:
                return {"job": job.id, "reason": record.get("status") if record else "hiç çalışmadı",
                        "blocking_reason": record.get("blocking_reason") if record else None}
        return {"job": None, "reason": "bütün işler tamam", "blocking_reason": None}

    # -- running ----------------------------------------------------------

    def execute(self, jobs: list[Job], *, dry_run: bool = False) -> dict:
        """Run every job that has no cached verdict yet. `dry_run` touches nothing at all."""
        if dry_run:
            limits = self.lab.limits(create=False)
            planned = [self._plan(job, limits) for job in jobs]
            return {"dry_run": True, "planned": planned, "executed": [],
                    "note": "kuru koşu: indirme, model çağrısı, kaynak oluşturma veya dosya yazımı yok"}

        limits = self.lab.settings()["limits"]
        usable = [job for job in jobs if not self._cached(job, limits)]
        if len(usable) > limits["initial_development_parts"]:
            return {"dry_run": False, "executed": [],
                    "blocked": {"reason": f"{len(usable)} iş pilot sınırını aşıyor "
                                          f"({limits['initial_development_parts']})",
                                "limit": "initial_development_parts"}}
        if not usable:
            return {"dry_run": False, "executed": [], "cached": [job.id for job in jobs],
                    "note": "bütün işlerin geçerli sonucu zaten var"}

        run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        acquired = self.lab.acquire_heavy(run_id)
        if not acquired["acquired"]:
            return {"dry_run": False, "executed": [],
                    "blocked": {"reason": "başka bir ağır iş açık", "held_by": acquired["held_by"]}}
        token = (acquired.get("held_by") or {}).get("token")
        deadline = self.clock() + limits["run_timeout_seconds"]
        executed = []
        try:
            for job in usable:
                if self.clock() >= deadline:
                    executed.append(self._blocked(
                        job, run_id, "run_deadline",
                        f"koşu süresi {limits['run_timeout_seconds']} sn doldu"))
                    continue
                executed.append(self._run_one(job, run_id, limits))
        finally:
            self.lab.release_heavy(token)
        return {"dry_run": False, "executed": executed, "run_id": run_id}

    def resume(self, jobs: list[Job]) -> dict:
        """Re-run what an interruption or a failed attempt left behind.

        A job is resumable when its last attempt did not produce a verdict. Incomplete results are
        never reused: their directories keep their files but no completion marker, and the next
        attempt gets a new directory.
        """
        state = self.lab.state()
        pending = [job for job in jobs
                   if state["jobs"].get(job.id, {}).get("status") in ("interrupted", "failed", "running")]
        if not pending:
            return {"resumed": [], "note": "devam edilecek iş yok"}
        outcome = self.execute(pending)
        return {"resumed": [job.id for job in pending], **outcome}

    def report(self, jobs: list[Job]) -> dict:
        state = self.lab.state()
        records = []
        for job in jobs:
            record = state["jobs"].get(job.id, {})
            records.append({
                "job": job.id,
                "job_status": record.get("status", "pending"),
                "product_verdict": record.get("product_verdict"),
                "outcome": record.get("outcome"),
                "seconds": record.get("seconds"),
                "exit_code": record.get("exit_code"),
                "attempts": record.get("attempts", 0),
                "run_id": record.get("run_id"),
                "attempt_dir": record.get("attempt_dir"),
                "result_path": record.get("result_path"),
                "evidence_paths": record.get("evidence_paths", []),
                "blocking_reason": record.get("blocking_reason"),
                "next_action": record.get("next_action"),
            })
        counts: dict[str, int] = {}
        for record in records:
            counts[record["job_status"]] = counts.get(record["job_status"], 0) + 1
        return {"jobs": records, "job_status_counts": counts}

    # -- internals --------------------------------------------------------

    def _key(self, job: Job, limits: dict) -> str:
        return idempotency_key(code=self.code_hash(),
                               data=data_fingerprint(job.inputs),
                               evaluator_version=LAB_VERSION, settings=limits,
                               job=job.as_dict())

    def key_for(self, job: Job) -> str:
        """The idempotency key this job has right now, under the current settings."""
        return self._key(job, self.lab.limits(create=False))

    def _effective_timeout(self, job: Job, limits: dict) -> dict:
        """A case may ask for less than the ceiling, never more."""
        ceiling = int(limits["case_timeout_seconds"])
        requested = job.timeout_seconds
        if requested is None:
            return {"seconds": ceiling, "capped": False, "requested": None}
        requested = int(requested)
        if requested > ceiling:
            return {"seconds": ceiling, "capped": True, "requested": requested}
        return {"seconds": max(1, requested), "capped": False, "requested": requested}

    def _plan(self, job: Job, limits: dict) -> dict:
        timeout = self._effective_timeout(job, limits)
        state = self.lab.state()
        return {"job": job.id, "key": self._key(job, limits),
                "cached": self._cacheable(state["runs"].get(self._key(job, limits), {})),
                "requested_timeout_seconds": timeout["requested"],
                "timeout_seconds": timeout["seconds"], "timeout_capped": timeout["capped"],
                "inputs": {str(path): path.exists() for path in job.inputs}}

    def _cacheable(self, record: dict) -> bool:
        """Only a valid produced verdict counts as a completed experiment."""
        return bool(record and record.get("complete") and record.get("outcome") in PRODUCT_OUTCOMES
                    and self._marker_valid(record))

    def _cached(self, job: Job, limits: dict) -> bool:
        return self._cacheable(self.lab.state()["runs"].get(self._key(job, limits), {}))

    def _marker_valid(self, record: dict) -> bool:
        """The marker must name this attempt and hash the result files it claims."""
        directory = Path(record.get("attempt_dir") or "")
        payload = read_json(directory / "complete.json")
        if not payload:
            return False
        if (payload.get("run_id"), payload.get("job"), payload.get("attempt")) != (
                record.get("run_id"), record.get("job"), record.get("attempt")):
            return False
        hashes = payload.get("results_sha256") or {}
        if not hashes:
            return False
        for name, digest in hashes.items():
            path = directory / name
            if not path.exists() or sha256_file(path) != digest:
                return False
        return True

    def _blocked(self, job: Job, run_id: str, kind: str, reason: str) -> dict:
        state = self.lab.state()
        record = {
            "run_id": run_id, "status": "blocked", "product_verdict": None, "outcome": "blocked",
            "blocking_kind": kind, "blocking_reason": reason,
            "attempts": state["jobs"].get(job.id, {}).get("attempts", 0),
            "attempt_dir": None, "evidence_paths": [], "key": self.key_for(job),
            "next_action": "engeli kaldır ve yeniden koş",
        }
        state["jobs"][job.id] = {**state["jobs"].get(job.id, {}), **record}
        self.lab.save_state(state)
        return {"job": job.id, **record}

    def _run_one(self, job: Job, run_id: str, limits: dict) -> dict:
        state = self.lab.state()
        previous = state["jobs"].get(job.id, {})
        attempts = int(previous.get("attempts", 0)) + 1
        key = self._key(job, limits)

        # Repair rounds are counted from history, not from a scalar that each attempt rewrites: the
        # list holds the error classes of the execution errors since the last attempt that produced a
        # verdict. A case that keeps failing in the same class is blocked once it has used up its
        # tries, and stays blocked until the fixed code produces a verdict (which clears the list).
        history = list(previous.get("error_history") or [])
        limit = int(limits["repair_rounds_per_error_class"])
        if job.error_class and history.count(job.error_class) >= limit:
            return self._blocked(job, run_id, "repair_rounds",
                                 f"{job.error_class} hata sınıfında {limit} düzeltme turu doldu")
        repair_rounds = history.count(job.error_class) if job.error_class else 0

        free = self.free_space_mb(self.lab.root)
        if free is not None and free < limits["min_free_disk_mb"]:
            return self._blocked(job, run_id, "disk",
                                 f"boş disk {free} MB < {limits['min_free_disk_mb']} MB")

        timeout = self._effective_timeout(job, limits)
        directory = self.lab.run_directory(run_id) / job.id / f"attempt-{attempts}"
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        result_path = directory / job.result

        # Recorded *before* the process starts, so a kill in between still leaves the job discoverable
        # and resumable.
        running = {"run_id": run_id, "status": "running", "attempts": attempts, "attempt": attempts,
                   "attempt_dir": str(directory), "result_path": str(result_path), "key": key,
                   "started_at": _now(), "error_class": job.error_class,
                   "repair_rounds": repair_rounds}
        state["jobs"][job.id] = {**state["jobs"].get(job.id, {}), **running}
        self.lab.save_state(state)

        manifest = {
            "schema": RUN_SCHEMA, "lab_version": LAB_VERSION, "run_id": run_id, "job": job.as_dict(),
            "job_id": job.id, "attempt": attempts, "key": key, "code_fingerprint": self.code_hash(),
            "started_at": running["started_at"], "timeout_seconds": timeout["seconds"],
            "requested_timeout_seconds": timeout["requested"], "timeout_capped": timeout["capped"],
            "limits": limits, "result_path": job.result,
        }
        # The case is told where to put its verdict, so an attempt directory is self-contained. Plain
        # substitution, not str.format: a command may legitimately contain braces of its own.
        command = [part.replace("{run_dir}", str(directory)).replace("{result}", str(result_path))
                   for part in job.command]
        manifest["command"] = command
        write_json(directory / "manifest.json", manifest)

        try:
            outcome = self.runner(command, timeout=timeout["seconds"])
        except BaseException as exc:  # noqa: BLE001 - an interruption is recorded, then re-raised
            self._record_interruption(job, running, directory, exc)
            raise

        stdout = outcome.get("stdout", "")
        stderr = outcome.get("stderr", "")
        atomic_write_text(directory / "raw" / f"{job.id}.stdout", stdout)
        atomic_write_text(directory / "raw" / f"{job.id}.stderr", stderr)

        record: dict = {
            "run_id": run_id, "attempt": attempts, "attempts": attempts,
            "attempt_dir": str(directory), "key": key, "started_at": running["started_at"],
            "finished_at": _now(), "seconds": outcome.get("seconds"),
            "exit_code": outcome.get("exit_code"), "command": command,
            "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
            "timeout_seconds": timeout["seconds"], "timeout_capped": timeout["capped"],
            "descendants_alive": outcome.get("descendants_alive"),
            "raw": [str(directory / "raw" / f"{job.id}.stdout"),
                    str(directory / "raw" / f"{job.id}.stderr")],
            "error_class": job.error_class, "repair_rounds": repair_rounds,
            "error_history": history,
        }

        if outcome.get("timed_out"):
            record.update({"status": "failed", "product_verdict": "timeout",
                           "outcome": "execution_error", "blocking_kind": "timeout",
                           "blocking_reason": f"vaka {timeout['seconds']} sn içinde bitmedi"})
            if record["descendants_alive"]:
                record["blocking_reason"] += "; süreç grubu hâlâ ayakta"
            return self._record(job, record, directory)

        status, product_verdict, outcome_kind, detail = _read_verdict(result_path)
        record.update({"status": status, "product_verdict": product_verdict,
                       "outcome": outcome_kind, "result_path": str(result_path), **detail})
        if outcome.get("exit_code") not in (0, None) and status == "completed":
            # A command that failed while claiming success is not a completed job.
            record.update({"status": "failed", "outcome": "execution_error",
                           "blocking_kind": "untrusted_success",
                           "blocking_reason": f"komut {outcome['exit_code']} ile çıktı ama sonuç "
                                              f"JSON'u başarılı dedi"})
        if record["outcome"] == "execution_error":
            # One more used try for this error class; the limit is enforced on the next execute().
            if job.error_class:
                record["error_history"] = history + [job.error_class]
        elif record["outcome"] in PRODUCT_OUTCOMES:
            record["error_history"] = []  # a verdict came out: whatever was broken now runs
        hashes = {job.result: sha256_file(result_path)} if result_path.exists() else {}
        marker = {"schema": RUN_SCHEMA, "run_id": run_id, "job": job.id, "attempt": attempts,
                  "finished_at": record["finished_at"], "results_sha256": hashes}
        write_json(directory / "complete.json", marker)
        record["complete"] = record["outcome"] in PRODUCT_OUTCOMES and bool(hashes)
        return self._record(job, record, directory)

    def _record_interruption(self, job: Job, running: dict, directory: Path, exc: BaseException) -> None:
        """Keep the attempt directory, mark the job interrupted, and let the caller see the error."""
        state = self.lab.state()
        record = {**running, "status": "interrupted", "outcome": "interrupted",
                  "product_verdict": None, "blocking_kind": "interrupted",
                  "blocking_reason": f"{type(exc).__name__}: {exc}", "finished_at": _now(),
                  "evidence_paths": [str(directory / "manifest.json")],
                  "next_action": "resume ile yeniden koş"}
        state["jobs"][job.id] = {**state["jobs"].get(job.id, {}), **record}
        state["runs"][running["key"]] = {"run_id": running["run_id"], "job": job.id,
                                         "attempt": running["attempt"], "attempt_dir": str(directory),
                                         "complete": False, "outcome": "interrupted",
                                         "product_verdict": None}
        self.lab.save_state(state)

    def _record(self, job: Job, record: dict, directory: Path) -> dict:
        record.setdefault("next_action", "raporu oku")
        if record.get("outcome") == "execution_error":
            record["next_action"] = "hatayı düzelt ve resume ile yeniden koş"
            record["repair_rounds"] = int(record.get("repair_rounds", 0)) + 1
        record["evidence_paths"] = sorted({str(path) for path in
                                           [directory / "manifest.json"] + record.get("raw", [])})
        state = self.lab.state()
        state["jobs"][job.id] = {**state["jobs"].get(job.id, {}), **record}
        state["runs"][record["key"]] = {"run_id": record["run_id"], "job": job.id,
                                        "attempt": record["attempt"],
                                        "attempt_dir": record["attempt_dir"],
                                        "complete": bool(record.get("complete")),
                                        "outcome": record.get("outcome"),
                                        "product_verdict": record.get("product_verdict")}
        self.lab.save_state(state)
        return {key: value for key, value in record.items()
                if key in ("run_id", "status", "product_verdict", "outcome", "seconds", "exit_code",
                           "blocking_reason", "blocking_kind", "evidence_paths", "attempts",
                           "attempt_dir", "result_path", "timeout_seconds", "timeout_capped",
                           "descendants_alive", "repair_rounds")} | {"job": job.id}


def _read_verdict(path: Path) -> tuple[str, str | None, str, dict]:
    """`(job_status, product_verdict, outcome, detail)` from the case's result file.

    A verdict that cannot be read is an execution error, not a product result: it must not be cached
    and must not be reported as a pass. A readable verdict — including `fail` — is a finished
    experiment and may be cached; that is a result, not a failure to produce one.
    """
    if not path.exists():
        return "failed", None, "execution_error", {
            "blocking_reason": "sonuç JSON'u yazılmadı — pass sayılmaz",
            "blocking_kind": "missing_result"}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return "failed", None, "execution_error", {
            "blocking_reason": f"sonuç JSON'u bozuk: {exc}", "blocking_kind": "invalid_result"}
    if not isinstance(payload, dict):
        return "failed", None, "execution_error", {
            "blocking_reason": "sonuç JSON'u nesne değil", "blocking_kind": "invalid_result"}
    verdict = payload.get("product_verdict")
    if verdict not in PRODUCT_VERDICTS:
        return "failed", None, "execution_error", {
            "blocking_reason": f"bilinmeyen product_verdict: {verdict!r}",
            "blocking_kind": "unknown_verdict"}
    return "completed", verdict, verdict, {}


def _free_space_mb(path: Path) -> int | None:
    try:
        return shutil.disk_usage(path if path.exists() else path.parent).free // (1024 * 1024)
    except OSError:
        return None


def _alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
