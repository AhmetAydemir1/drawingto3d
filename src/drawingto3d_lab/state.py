"""Persistent state, fingerprints and the single-heavy-job lock.

Storage is plain JSON written atomically (temporary file in the same directory, then `os.replace`),
so a reader never sees a half-written state file and an interrupted write cannot corrupt the record.
SQLite is not needed at this size and would hide the file from a person reading `out/lab/`.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from drawingto3d_lab import DEFAULT_LIMITS, SETTINGS_SCHEMA, STATE_SCHEMA


def atomic_write_text(path: Path, text: str) -> Path:
    """Write text so that a reader sees either the old file or the whole new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp{os.getpid()}")
    temporary.write_text(text)
    os.replace(temporary, path)
    return path


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise ValueError(f"bozuk JSON: {path}") from exc


def read_lock_claim(path: Path):
    """Read a heavy-slot claim.

    A lock file that cannot be parsed is a claim that has not been published yet (someone created
    the file and has not written it), not a corrupt record: the two must not be answered the same
    way, because the honest answer here is "held, identity unknown", never "free".
    """
    try:
        payload = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload) -> Path:
    return atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def data_fingerprint(paths: list[Path]) -> dict[str, str]:
    """One hash per input file: the same bytes are the same input, a changed file is a new one."""
    return {str(path): sha256_file(path) for path in paths if path.exists()}


def code_fingerprint(root: Path, watched: list[Path] | None = None) -> str:
    """A fingerprint of the code that would run: the *contents* of the working tree.

    A revision plus the `git status` text is not enough, and that is exactly how a cache goes stale:
    an edit to a file that was already dirty changes nothing in either, and a cached result produced
    by different code is then reused. So every tracked file's bytes are hashed, plus any watched file
    that decides the experiment but may not be committed yet.

    Data that is not tracked by git is fingerprinted separately (`data_fingerprint`), per input file.
    """
    parts = []
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                  text=True, check=True).stdout.strip()
        listing = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True,
                                 check=True).stdout.decode()
        parts.append(f"git:{revision}")
        for name in sorted(name for name in listing.split("\0") if name):
            path = root / name
            if path.is_file():
                parts.append(f"{name}:{sha256_file(path)}")
    except (OSError, subprocess.CalledProcessError):
        parts.append("git:unavailable")
    for path in watched or []:
        if path.exists():
            parts.append(f"{path.name}:{sha256_file(path)}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def settings_digest(settings: dict) -> str:
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()


def idempotency_key(*, code: str, data: dict, evaluator_version: str, settings: dict,
                    job: dict) -> str:
    """Same inputs, same code, same evaluator, same settings, same job → same key.

    The key is what stops a second invocation from re-downloading or re-charging for work that was
    already done.
    """
    payload = {
        "code": code,
        "data": data,
        "evaluator": evaluator_version,
        "settings": settings_digest(settings),
        "job": {key: value for key, value in job.items() if key not in ("notes",)},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class Lab:
    """Paths and the state file of one lab root (`out/lab` by default)."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    # -- settings ---------------------------------------------------------

    @property
    def settings_path(self) -> Path:
        return self.root / "settings.json"

    def settings(self, *, create: bool = True) -> dict:
        """The pilot limits. Written once with their schema; never raised by this module."""
        existing = read_json(self.settings_path)
        if existing is None:
            if not create:
                return {"schema": SETTINGS_SCHEMA, "limits": dict(DEFAULT_LIMITS)}
            payload = {"schema": SETTINGS_SCHEMA, "limits": dict(DEFAULT_LIMITS),
                       "created_at": _now()}
            write_json(self.settings_path, payload)
            return payload
        if "limits" not in existing:
            raise ValueError(f"ayar dosyasında limits yok: {self.settings_path}")
        return existing

    def limits(self, *, create: bool = True) -> dict:
        return self.settings(create=create)["limits"]

    # -- state ------------------------------------------------------------

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    def state(self) -> dict:
        state = read_json(self.state_path)
        if state is None:
            state = {"schema": STATE_SCHEMA, "updated_at": _now(), "jobs": {}, "runs": {}}
        state.setdefault("jobs", {})
        state.setdefault("runs", {})
        return state

    def save_state(self, state: dict) -> Path:
        state["schema"] = STATE_SCHEMA
        state["updated_at"] = _now()
        return write_json(self.state_path, state)

    def run_directory(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    def next_markdown(self) -> Path:
        return self.root / "next.md"

    # -- the single heavy job --------------------------------------------

    @property
    def lock_path(self) -> Path:
        return self.root / "heavy.lock"

    def acquire_heavy(self, run_id: str, *, pid: int | None = None) -> dict:
        """Take the one heavy-job slot, atomically.

        Every contender takes the slot's guard (`flock` on `heavy.guard`, a file that is never deleted
        and so has no window of its own) before it looks at the claim, and the claim is published with
        `os.link`, which is atomic *and* carries its content: a reader either finds no lock file at all
        or finds a complete claim. Creating the file first and writing the JSON afterwards left a window
        in which a reader found an empty file; that window is a claim being published, never a free slot.

        The guard is what makes reclaiming single-winner. Without it, a reclaimer's check ("the owner is
        dead") and its move (the stale file aside) are two steps, and a contender that publishes between
        them has its *live* claim moved aside — measured on this repository: three processes racing for a
        dead owner's lock produced **two** winners, one of them holding a claim the other had already
        discarded.
        """
        pid = os.getpid() if pid is None else pid
        token = secrets.token_hex(8)
        payload = json.dumps({"run_id": run_id, "pid": pid, "token": token,
                              "started_at": _now(), "host": os.uname().nodename}, indent=2) + "\n"
        with self._slot():
            existing = read_lock_claim(self.lock_path)
            if existing is None and self.lock_path.exists():
                # An unpublished claim: someone created the file and has not written it yet. Wait for it
                # to become readable, then report the holder; never treat it as a free slot, and never
                # delete it — it may be a claim being written right now.
                existing = self._wait_for_claim()
                if existing is None:
                    return {"acquired": False, "held_by": None, "published": False, "reclaimed": False}
            reclaimed = False
            if existing is not None and self.lock_path.exists():
                if _process_alive(existing.get("pid")):
                    return {"acquired": False, "held_by": existing, "reclaimed": False}
                self.lock_path.unlink(missing_ok=True)
                reclaimed = True
            if not self._publish_claim(payload):
                return {"acquired": False, "held_by": read_lock_claim(self.lock_path), "reclaimed": False}
            return {"acquired": True, "reclaimed": reclaimed,
                    "held_by": {"run_id": run_id, "pid": pid, "token": token}}

    @property
    def guard_path(self) -> Path:
        """The file every contender takes before touching the slot; never deleted, so it has no window."""
        return self.root / "heavy.guard"

    @contextmanager
    def _slot(self):
        """Hold the slot's guard for the whole of a check-and-change."""
        self.root.mkdir(parents=True, exist_ok=True)
        handle = open(self.guard_path, "a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def _publish_claim(self, payload: str) -> bool:
        """Publish a complete claim in one step; False means the slot is taken."""
        scratch = self.lock_path.with_name(f".claim-{os.getpid()}-{secrets.token_hex(4)}")
        scratch.write_text(payload, encoding="utf-8")
        try:
            os.link(scratch, self.lock_path)
        except FileExistsError:
            return False
        finally:
            scratch.unlink(missing_ok=True)
        return True

    def _wait_for_claim(self, *, timeout_seconds: float = 0.5, step_seconds: float = 0.005):
        """Wait for an in-flight publication; returns the claim, or None if it never appears."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            claim = read_lock_claim(self.lock_path)
            if claim is not None or not self.lock_path.exists():
                return claim
            if time.monotonic() >= deadline:
                return None
            time.sleep(step_seconds)

    def release_heavy(self, token: str | None = None) -> bool:
        """Give the slot up. Only the caller's own claim is removed.

        Taken under the same guard as `acquire_heavy`: without it, a contender that publishes between
        this read and this unlink would have its live claim deleted.
        """
        with self._slot():
            current = read_lock_claim(self.lock_path)
            if current is None:
                if self.lock_path.exists():
                    return False  # an unpublished claim is not ours to delete
                return True
            # A token is evidence of ownership; without one, only this process's own claim is released.
            mine = ((current.get("token") == token) if token is not None
                    else (current.get("pid") == os.getpid()))
            if not mine:
                return False
            try:
                self.lock_path.unlink()
            except FileNotFoundError:  # pragma: no cover - already released
                return True
            return True


def _process_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
