"""The lab runner: one heavy job at a time, idempotent, resumable, and honest about failures.

Version `drawingto3d-lab/1.0.0`.

This is the experiment harness, separate from the product package. It exists because a run that
cannot be resumed measures nothing after an interruption, and a second invocation of the same job
must not download or charge for the same work again.

Design rules, from the plan:

* One active heavy job. The lock records the pid, so a lock left behind by a dead process is
  reclaimed instead of blocking the next run forever.
* The idempotency key is the input hashes + the code fingerprint + the evaluator version + the
  settings. Any of those changing is a new job; the same combination is never executed twice.
* `job_status` (did the job itself finish?) and `product_verdict` (what the product answered) are
  separate. A command that exits 0 while its result JSON says the case failed is a failed case.
  Missing, unreadable or unknown-verdict JSON is never a pass.
* Every artifact is written atomically and a run is only complete when its marker — with per-file
  hashes — is written last. A run without a valid marker is `interrupted`, and its results are not
  read.
* The pilot limits live in `out/lab/settings.json` and are written once. They are read, not
  negotiated: nothing in this module raises them.
"""

from __future__ import annotations

LAB_VERSION = "drawingto3d-lab/1.0.0"
STATE_SCHEMA = "drawingto3d.lab.state/1"
RUN_SCHEMA = "drawingto3d.lab.run/1"
SETTINGS_SCHEMA = "drawingto3d.lab.settings/1"

PRODUCT_VERDICTS = ("pass", "fail", "needs_input", "unsupported", "timeout", "error", "not_evaluated")
JOB_STATUSES = ("pending", "running", "completed", "failed", "interrupted", "blocked", "cached", "dry_run")

# Limits of the first local pilot. Written to out/lab/settings.json on first use. Nothing in this
# package may raise them: the budget is a decision, not a default.
DEFAULT_LIMITS = {
    "heavy_jobs": 1,
    "initial_development_parts": 10,
    "case_timeout_seconds": 600,
    "run_timeout_seconds": 7200,
    "download_attempts": 2,
    "repair_rounds_per_error_class": 3,
    "min_free_disk_mb": 512,
}
