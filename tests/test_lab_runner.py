"""H02: the runner has to survive an interruption, refuse to pay twice, and never call a failure a pass.

Every test here drives a fake case command, so the assertions are about the runner's bookkeeping
rather than about a real experiment: interruption and resume, a second invocation of the same job,
a failing case, a timeout, a full disk, a missing result, an unreadable result, and cache
invalidation when the code changes. One test runs a real subprocess, because a runner whose process
handling was never exercised is not a runner.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d_lab import DEFAULT_LIMITS  # noqa: E402
from drawingto3d_lab.runner import Job, LabRunner, subprocess_runner  # noqa: E402
from drawingto3d_lab.state import Lab, idempotency_key, read_json  # noqa: E402


class FakeCase:
    """Stands in for a case command: writes what the test says it writes, and counts its calls."""

    def __init__(self, *, payload=None, raw=None, exit_code=0, timed_out=False, write_result=True,
                 seconds=1.5):
        self.payload = payload
        self.raw = raw
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.write_result = write_result
        self.seconds = seconds
        self.calls: list[list[str]] = []

    def __call__(self, command, *, timeout):
        self.calls.append(list(command))
        if self.timed_out:
            return {"timed_out": True, "exit_code": None, "seconds": timeout, "stdout": "", "stderr": ""}
        if self.write_result and "--result" in command:
            path = Path(command[command.index("--result") + 1])
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = dict(self.payload if self.payload is not None else {"product_verdict": "pass"})
            if "--tag" in command:
                payload["tag"] = command[command.index("--tag") + 1]
            path.write_text(self.raw if self.raw is not None else json.dumps(payload))
        return {"timed_out": False, "exit_code": self.exit_code, "seconds": self.seconds,
                "stdout": "çıktı", "stderr": ""}


def make_job(tmp_path: Path, name: str = "case-1", *, command: list[str] | None = None,
             inputs: list[Path] | None = None, timeout_seconds: int | None = 60,
             result: str = "result.json", error_class: str | None = None) -> Job:
    if inputs is None:
        source = tmp_path / "input.txt"
        source.write_text("girdi\n")
        inputs = [source]
    return Job(id=name, command=command or ["python3", "-c", "pass", "--result", "{result}"],
               inputs=inputs, timeout_seconds=timeout_seconds, result=result,
               error_class=error_class)


@pytest.fixture
def lab(tmp_path) -> Lab:
    return Lab(tmp_path / "lab")


def runner_with(lab: Lab, case: FakeCase, **kwargs) -> LabRunner:
    return LabRunner(lab.root, root_repository=lab.root.parent, runner=case,
                     free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A", **kwargs)


def test_dry_run_executes_nothing_and_writes_nothing(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    outcome = runner.execute([make_job(tmp_path)], dry_run=True)

    assert outcome["dry_run"] is True
    assert case.calls == []
    assert not (lab.root / "state.json").exists()
    assert not (lab.root / "settings.json").exists()
    assert not (lab.root / "runs").exists()
    assert outcome["planned"][0]["job"] == "case-1"
    assert outcome["planned"][0]["timeout_seconds"] == 60


def test_a_completed_job_is_never_executed_twice(lab, tmp_path) -> None:
    case = FakeCase(payload={"product_verdict": "pass"})
    runner = runner_with(lab, case)
    job = make_job(tmp_path)

    first = runner.execute([job])
    assert [entry["status"] for entry in first["executed"]] == ["completed"]
    assert len(case.calls) == 1

    second = runner.execute([job])
    assert second["executed"] == []
    assert len(case.calls) == 1, "aynı iş ikinci kez çalıştırıldı: yeniden indirme/ücretlendirme riski"
    assert runner.status()["runs"] and all(
        record["complete"] for record in runner.status()["runs"].values())


def test_changing_the_code_invalidates_the_cache(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    job = make_job(tmp_path)
    runner.execute([job])

    other_code = LabRunner(lab.root, root_repository=lab.root.parent, runner=case,
                           free_space_mb=lambda path: 10_000, code_hash=lambda: "code-B")
    outcome = other_code.execute([job])
    assert [entry["status"] for entry in outcome["executed"]] == ["completed"]
    assert len(case.calls) == 2, "kod değişince önbellek geçersiz olmalı"


def test_changing_an_input_invalidates_the_cache(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    job = make_job(tmp_path)
    runner.execute([job])
    job.inputs[0].write_text("değişmiş girdi\n")
    runner.execute([job])
    assert len(case.calls) == 2


def test_an_interrupted_run_is_not_reused_and_resume_reruns_it(lab, tmp_path) -> None:
    case = FakeCase(payload={"product_verdict": "fail", "reason": "yeniden koşu"})
    runner = runner_with(lab, case)
    job = make_job(tmp_path)

    # An interruption: the run directory holds a plausible-looking result but no marker, and the
    # state says the job was interrupted.
    interrupted = lab.run_directory("20260101-000000-deadbeef")
    (interrupted / "raw").mkdir(parents=True)
    (interrupted / "manifest.json").write_text("{}")
    (interrupted / "result.json").write_text(json.dumps({"product_verdict": "pass"}))
    state = lab.state()
    state["runs"][runner.key_for(job)] = {"run_id": interrupted.name, "job": job.id, "complete": False}
    state["jobs"][job.id] = {"status": "interrupted", "run_id": interrupted.name, "attempts": 1}
    lab.save_state(state)

    outcome = runner.resume([job])
    assert outcome["resumed"] == [job.id]
    assert len(case.calls) == 1, "yarım koşu sonrası iş yeniden çalışmalı"
    record = lab.state()["jobs"][job.id]
    assert record["run_id"] != interrupted.name
    assert record["attempts"] == 2
    assert not (interrupted / "complete.json").exists(), "yarım koşu tamamlandı sayılmamalı"
    assert runner.report([job])["jobs"][0]["product_verdict"] == "fail", \
        "yarım koşunun 'pass' sonucu kullanılmamalı"

    # And once it is complete, resuming does nothing.
    assert runner.resume([job])["resumed"] == []
    assert len(case.calls) == 1


def test_a_failing_case_is_failed_even_when_the_command_exits_zero(lab, tmp_path) -> None:
    case = FakeCase(payload={"product_verdict": "fail", "reason": "delik sayısı yanlış"}, exit_code=0)
    runner = runner_with(lab, case)
    record = runner.execute([make_job(tmp_path)])["executed"][0]
    assert record["status"] == "completed"       # the job ran
    assert record["product_verdict"] == "fail"   # the product did not
    assert record["exit_code"] == 0


def test_a_command_that_failed_but_claims_success_is_not_completed(lab, tmp_path) -> None:
    case = FakeCase(payload={"product_verdict": "pass"}, exit_code=2)
    runner = runner_with(lab, case)
    record = runner.execute([make_job(tmp_path)])["executed"][0]
    assert record["status"] == "failed"
    assert record["blocking_kind"] == "untrusted_success"


def test_a_timeout_is_a_timeout_not_a_pass(lab, tmp_path) -> None:
    case = FakeCase(timed_out=True)
    runner = runner_with(lab, case)
    record = runner.execute([make_job(tmp_path)])["executed"][0]
    assert record["status"] == "failed"
    assert record["product_verdict"] == "timeout"
    assert "60" in record["blocking_reason"]


@pytest.mark.parametrize("case_name,payload_kind,expected_kind", [
    ("missing", "missing", "missing_result"),
    ("invalid", "invalid", "invalid_result"),
    ("unknown", "unknown", "unknown_verdict"),
])
def test_missing_or_unreadable_results_are_never_pass(lab, tmp_path, case_name, payload_kind, expected_kind) -> None:
    raw = {"invalid": "{bu JSON değil", "unknown": json.dumps({"product_verdict": "başarılı"}),
           "missing": None}[payload_kind]
    case = FakeCase(write_result=payload_kind != "missing", raw=raw)
    runner = runner_with(lab, case)
    record = runner.execute([make_job(tmp_path, name=f"case-{case_name}")])["executed"][0]
    assert record["status"] == "failed"
    assert record["outcome"] == "execution_error", "okunamayan sonuç yürütme hatasıdır"
    assert record["product_verdict"] is None, "okunamayan sonuç bir ürün hükmü değildir"
    assert record["blocking_kind"] == expected_kind


def test_a_full_disk_blocks_before_anything_runs(lab, tmp_path) -> None:
    case = FakeCase()
    runner = LabRunner(lab.root, root_repository=lab.root.parent, runner=case,
                       free_space_mb=lambda path: 1, code_hash=lambda: "code-A")
    record = runner.execute([make_job(tmp_path)])["executed"][0]
    assert record["status"] == "blocked"
    assert record["blocking_kind"] == "disk"
    assert case.calls == [], "disk doluyken vaka çalıştırılmamalı"


def test_only_one_heavy_job_can_run(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    lab.acquire_heavy("başka-koşu", pid=os.getpid())  # a live process holds the slot

    outcome = runner.execute([make_job(tmp_path)])
    assert outcome["executed"] == []
    assert "başka bir ağır iş" in outcome["blocked"]["reason"]
    assert case.calls == []

    lab.release_heavy()
    assert runner.execute([make_job(tmp_path)])["executed"]


def test_a_lock_left_by_a_dead_process_is_reclaimed(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    lab.acquire_heavy("ölü-koşu", pid=999_999)  # no such process
    outcome = runner.execute([make_job(tmp_path)])
    assert outcome["executed"], "ölü süreçten kalan kilit yeni koşuyu engellememeli"


def test_the_pilot_limits_come_from_the_settings_file_and_are_not_raised(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    limits = lab.limits()
    assert limits == DEFAULT_LIMITS
    assert limits["initial_development_parts"] == 10
    assert limits["case_timeout_seconds"] == 600
    assert limits["run_timeout_seconds"] == 7200

    # A settings file with a smaller ceiling is obeyed, not overwritten.
    lab.settings_path.write_text(json.dumps({"schema": "x", "limits": {**DEFAULT_LIMITS,
                                                                      "initial_development_parts": 1}}))
    outcome = runner.execute([make_job(tmp_path, name=f"case-{index}") for index in range(2)])
    assert outcome["executed"] == []
    assert "pilot sınırını" in outcome["blocked"]["reason"]
    assert case.calls == []


def test_a_real_subprocess_run_writes_a_verdict_and_its_raw_output(lab, tmp_path) -> None:
    script = ("import json,sys; p=sys.argv[sys.argv.index('--result')+1];"
              "open(p,'w').write(json.dumps({'product_verdict':'pass'}));print('merhaba')")
    job = make_job(tmp_path, command=[sys.executable, "-c", script, "--result", "{result}"])
    runner = LabRunner(lab.root, root_repository=lab.root.parent, runner=subprocess_runner,
                       free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A")
    record = runner.execute([job])["executed"][0]
    assert record["status"] == "completed"
    assert record["product_verdict"] == "pass"
    stdout = Path(record["evidence_paths"][0]).parent / "raw" / "case-1.stdout"
    assert "merhaba" in stdout.read_text()
    assert read_json(Path(record["evidence_paths"][0]).parent / "complete.json")

    report = runner.report([job])
    assert report["jobs"][0]["job_status"] == "completed"
    assert report["jobs"][0]["product_verdict"] == "pass"
    assert report["job_status_counts"] == {"completed": 1}


# ---------------------------------------------------- review R01-R05 regressions
#
# Every test below asserts the behaviour the review asked for, and each one would have failed against
# the code the review measured: two jobs overwriting each other, a failed execution counted as a
# cached result, an interrupt that left no trace, a job timeout above the ceiling, and a code
# fingerprint that did not move when already-dirty source changed.


def test_two_jobs_in_one_run_keep_their_own_result_and_marker(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    jobs = [make_job(tmp_path, name=f"job-{tag}", command=["python3", "-c", "pass", "--result",
                                                           "{result}", "--tag", tag])
            for tag in ("first", "second")]

    outcome = runner.execute(jobs)
    records = {entry["job"]: entry for entry in outcome["executed"]}
    assert set(records) == {"job-first", "job-second"}
    assert len(case.calls) == 2

    state = lab.state()
    for tag in ("first", "second"):
        job_id = f"job-{tag}"
        directory = Path(state["jobs"][job_id]["attempt_dir"])
        assert directory == Path(state["jobs"][job_id]["result_path"]).parent
        assert directory.name == "attempt-1"
        assert directory.parent.name == job_id, "her iş kendi dizininde olmalı"
        # The result this job reads back is the one its own command wrote, not the other job's.
        assert read_json(Path(state["jobs"][job_id]["result_path"]))["tag"] == tag
        marker = read_json(directory / "complete.json")
        assert marker["job"] == job_id and marker["attempt"] == 1
        assert set(marker["results_sha256"]) == {"result.json"}
    assert Path(state["jobs"]["job-first"]["attempt_dir"]) != Path(
        state["jobs"]["job-second"]["attempt_dir"])


def test_a_failed_execution_is_not_cached_but_a_product_fail_is(lab, tmp_path) -> None:
    missing = FakeCase(write_result=False)
    runner = runner_with(lab, missing)
    job = make_job(tmp_path, name="missing")
    first = runner.execute([job])["executed"][0]
    assert first["outcome"] == "execution_error" and first["status"] == "failed"

    resumed = runner.resume([job])
    assert resumed["resumed"] == [job.id]
    assert len(missing.calls) == 2, "başarısız yürütme yeniden denenebilmeli"

    # A readable product verdict is a finished experiment: it is cached and not re-run.
    failing = FakeCase(payload={"product_verdict": "fail"})
    other = LabRunner(lab.root, root_repository=lab.root.parent, runner=failing,
                      free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A")
    verdict_job = make_job(tmp_path, name="verdict")
    other.execute([verdict_job])
    assert other.execute([verdict_job])["cached"] == [verdict_job.id]
    assert len(failing.calls) == 1
    record = lab.state()["jobs"]["verdict"]
    assert record["outcome"] == "fail" and record["complete"] is True


def test_an_interrupt_is_recorded_before_the_process_and_resumes(lab, tmp_path) -> None:
    """The R03 counter-example, run in a real subprocess.

    A KeyboardInterrupt raised inside a pytest test body is a session-level signal for pytest itself
    (it aborts the whole run even when the test handles it), so the interruption is exercised where it
    belongs: in its own process, exactly as the review's probe did it.
    """
    import subprocess

    job_input = tmp_path / "input.txt"
    job_input.write_text("girdi\n")
    script = f'''
import json, sys
sys.path.insert(0, {str(ROOT / "src")!r})
from pathlib import Path
from drawingto3d_lab.runner import Job, LabRunner

calls = []

def interrupted(command, *, timeout):
    calls.append(1)
    if len(calls) == 1:
        raise KeyboardInterrupt("kontrollü kesinti")
    return {{"timed_out": False, "exit_code": 0, "seconds": 0.1, "stdout": "", "stderr": ""}}

runner = LabRunner(Path({str(lab.root)!r}), root_repository=Path({str(ROOT)!r}), runner=interrupted,
                   free_space_mb=lambda path: 10000, code_hash=lambda: "code-A")
job = Job(id="interrupted", command=["python3", "-c", "pass", "--result", "{{result}}"],
          inputs=[Path({str(job_input)!r})], timeout_seconds=60)
try:
    runner.execute([job])
except KeyboardInterrupt:
    pass
state = runner.lab.state()
record = state["jobs"]["interrupted"]
print(json.dumps({{"status": record["status"], "attempt_dir": record["attempt_dir"],
                  "marker": (Path(record["attempt_dir"]) / "complete.json").exists(),
                  "lock": runner.lab.lock_path.exists(),
                  "resumed": runner.resume([job])["resumed"]}}))
'''
    output = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    payload = json.loads(output.stdout.strip().splitlines()[-1])

    assert payload["status"] == "interrupted", "kesinti kaydedilmeli"
    assert Path(payload["attempt_dir"]).name == "attempt-1"
    assert payload["marker"] is False, "yarım deneme tamamlanmış sayılmamalı"
    assert payload["lock"] is False, "kesintiden sonra kilit bırakılmalı"
    assert payload["resumed"] == ["interrupted"], "kesintiden sonra resume işi bulmalı"


def test_a_job_cannot_raise_the_case_timeout_ceiling(lab, tmp_path) -> None:
    seen = []
    case = FakeCase()

    def recording(command, *, timeout):
        seen.append(timeout)
        return case(command, timeout=timeout)

    record = LabRunner(lab.root, root_repository=lab.root.parent, runner=recording,
                       free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A").execute(
        [make_job(tmp_path, name="over-limit", timeout_seconds=999_999)])["executed"][0]

    assert seen == [600], "vaka sınırı 600 sn; istek yükseltemez"
    assert record["timeout_seconds"] == 600 and record["timeout_capped"] is True
    manifest = read_json(Path(record["attempt_dir"]) / "manifest.json")
    assert manifest["requested_timeout_seconds"] == 999_999
    assert manifest["timeout_seconds"] == 600 and manifest["timeout_capped"] is True
    assert lab.limits()["case_timeout_seconds"] == 600


def test_the_whole_run_deadline_stops_starting_new_jobs(lab, tmp_path) -> None:
    ticks = iter([0.0, 0.0, 10_000.0, 10_000.0, 10_000.0])
    case = FakeCase()
    runner = LabRunner(lab.root, root_repository=lab.root.parent, runner=case,
                       free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A",
                       clock=lambda: next(ticks))
    jobs = [make_job(tmp_path, name=f"deadline-{index}") for index in range(2)]
    outcome = runner.execute(jobs)

    assert len(outcome["executed"]) == 2
    assert len(case.calls) == 1, "süre dolduktan sonra yeni iş başlatılmamalı"
    blocked = outcome["executed"][1]
    assert blocked["status"] == "blocked" and blocked["blocking_kind"] == "run_deadline"
    assert "7200" in blocked["blocking_reason"]


def test_one_error_class_cannot_be_repaired_forever(lab, tmp_path) -> None:
    case = FakeCase(write_result=False)
    runner = runner_with(lab, case)
    job = make_job(tmp_path, name="repair", error_class="evaluator")

    for _ in range(3):
        runner.execute([job])
    assert len(case.calls) == 3, "üç düzeltme turu denenmeli"

    final = runner.execute([job])["executed"][0]
    assert final["status"] == "blocked" and final["blocking_kind"] == "repair_rounds"
    assert len(case.calls) == 3, "sınır dolduktan sonra komut çalıştırılmamalı"
    assert lab.limits()["repair_rounds_per_error_class"] == 3


def test_tampering_with_a_result_invalidates_the_cache(lab, tmp_path) -> None:
    case = FakeCase()
    runner = runner_with(lab, case)
    job = make_job(tmp_path)
    record = runner.execute([job])["executed"][0]
    Path(lab.state()["jobs"][job.id]["result_path"]).write_text(json.dumps({"product_verdict": "fail"}))

    assert runner.execute([job])["executed"], "hash tutmayan sonuç yeniden kullanılmamalı"
    assert len(case.calls) == 2
    assert record["status"] == "completed"


def test_the_code_fingerprint_follows_contents_not_the_status_text(tmp_path) -> None:
    """The review's R05: an already-dirty tracked file must move the fingerprint when it changes."""
    import subprocess

    from drawingto3d_lab.state import code_fingerprint

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    source = repo / "unwatched.py"
    source.write_text("version = 1\n")
    subprocess.run(["git", "add", "unwatched.py"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], cwd=repo, check=True)

    source.write_text("version = 2\n")          # dirty from here on
    before = code_fingerprint(repo)
    source.write_text("version = 3\n")          # still dirty: git status text is identical
    after = code_fingerprint(repo)

    assert before != after, "kirli kaynağın içeriği değişince fingerprint değişmeli"
    assert after == code_fingerprint(repo), "aynı içerik aynı fingerprint"


def test_the_lock_is_atomic_across_two_processes(tmp_path) -> None:
    """Two processes race for the one heavy slot; exactly one may win."""
    import subprocess

    root = tmp_path / "lab"
    script = ("import json,sys;sys.path.insert(0, sys.argv[1]);"
              "from drawingto3d_lab.state import Lab;"
              "print(json.dumps(Lab(sys.argv[2]).acquire_heavy('run-' + sys.argv[3])))")
    environment = {"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}
    processes = [subprocess.Popen([sys.executable, "-c", script, str(ROOT / "src"), str(root), tag],
                                  stdout=subprocess.PIPE, text=True, env=environment)
                 for tag in ("a", "b")]
    results = [json.loads(process.communicate()[0].strip().splitlines()[-1]) for process in processes]

    assert sum(1 for result in results if result["acquired"]) == 1, \
        f"kilit yarışında tam olarak bir süreç kazanmalı: {results}"
    assert sum(1 for result in results if not result["acquired"]) == 1
    Lab(root).release_heavy()
    assert Lab(root).acquire_heavy("after")["acquired"] is True


def test_a_timeout_kills_the_whole_process_group(lab, tmp_path) -> None:
    """The child of a wrapper must not survive the case's timeout."""
    from drawingto3d_lab.runner import subprocess_runner

    child_pid_file = tmp_path / "child.pid"
    child = f"import os,time;open({str(child_pid_file)!r},'w').write(str(os.getpid()));time.sleep(60)"
    wrapper = ("import subprocess,sys,time;"
               f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
               "time.sleep(60)")
    job = make_job(tmp_path, name="tree", command=[sys.executable, "-c", wrapper],
                   timeout_seconds=1, result="result.json")
    runner = LabRunner(lab.root, root_repository=lab.root.parent, runner=subprocess_runner,
                       free_space_mb=lambda path: 10_000, code_hash=lambda: "code-A")
    record = runner.execute([job])["executed"][0]

    assert record["product_verdict"] == "timeout"
    assert record["outcome"] == "execution_error"
    assert record["descendants_alive"] is False, "süreç grubu kapatılmalı"
    child_pid = int(child_pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
