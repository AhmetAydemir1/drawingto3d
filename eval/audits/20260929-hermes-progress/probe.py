"""Independent review probes; no cloud calls and no changes to product/lab data.

Run from repository: .venv/bin/python eval/audits/20260929-hermes-progress/probe.py
Findings are observations, not assertions of product correctness. After repairs,
observed_bad should become false for each probe; retain expected behaviour.
"""
from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path)
parser.add_argument("--pilot-root", type=Path, default=ROOT / "out/lab/data/raw")
args = parser.parse_args()
sys.path.insert(0, str(ROOT / "src"))
from drawingto3d_lab.runner import Job, LabRunner
from drawingto3d_lab.state import Lab, code_fingerprint, read_json, write_json
from drawingto3d_lab.generator import PartSpec, labels, printed_dimensions
from build123d import Box, Pos, export_step

spec = importlib.util.spec_from_file_location("review_metrics", ROOT / "eval/feature_metrics.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
findings = []


def record(name, bad, expected, observed):
    findings.append(dict(id=name, observed_bad=bool(bad), expected=expected, observed=observed))


class Fake:
    def __init__(self, missing=False):
        self.calls = 0
        self.missing = missing

    def __call__(self, command, *, timeout):
        self.calls += 1
        if not self.missing:
            Path(command[0]).write_text(json.dumps({"product_verdict": "pass", "tag": command[1]}))
        return dict(timed_out=False, exit_code=0, seconds=0.01, stdout="", stderr="")


def runner(root, fake):
    return LabRunner(root, root_repository=ROOT, runner=fake,
                     free_space_mb=lambda _: 10000, code_hash=lambda: "review-fixed")


with tempfile.TemporaryDirectory(prefix="hermes-review-") as tmp:
    tmp = Path(tmp)
    fake = Fake()
    run = runner(tmp / "multi", fake)
    jobs = [Job(id=i, command=["{result}", i]) for i in ("first", "second")]
    run.execute(jobs)
    states = run.lab.state()["jobs"]
    content = {i: read_json(Path(s["result_path"])) for i, s in states.items()}
    record("R01_multi_job_overwrite", content["first"]["tag"] != "first",
           "Each job retains its own result, manifest and matching completion marker.", content)

    fake = Fake(missing=True)
    run = runner(tmp / "missing", fake)
    job = Job(id="missing", command=["{result}", "missing"])
    first = run.execute([job])
    second = run.resume([job])
    record("R02_failed_result_cached", fake.calls == 1,
           "A missing/invalid result remains retryable; resume actually executes it.",
           dict(calls=fake.calls, first=first["executed"][0]["status"], resumed=second))

    def interrupted(command, *, timeout):
        raise KeyboardInterrupt("controlled interruption, not an external process")
    run = runner(tmp / "interrupt", interrupted)
    job = Job(id="interrupt", command=["{result}", "interrupt"])
    try:
        run.execute([job])
    except KeyboardInterrupt:
        pass
    resumed = run.resume([job])
    record("R03_interruption_not_registered", not resumed.get("resumed"),
           "Persist running state before launch; interrupted jobs can be discovered and resumed.",
           dict(state=run.lab.state(), resume=resumed))

    calls = []
    fake = Fake()
    def timed(command, *, timeout):
        calls.append(timeout)
        return fake(command, timeout=timeout)
    run = runner(tmp / "limits", timed)
    run.execute([Job(id="over-limit", command=["{result}", "x"], timeout_seconds=999999)])
    record("R04_case_timeout_bypassed", calls == [999999],
           "Reject or cap job timeout at case limit (600s), also enforce whole-run deadline.", calls)

    # Same git status text and revision, but different source bytes: use an isolated git repo.
    import subprocess
    repo = tmp / "git"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    source = repo / "unwatched.py"
    source.write_text("version = 1\n")
    subprocess.run(["git", "add", "unwatched.py"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Local review", "-c", "user.email=review@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], cwd=repo, check=True)
    source.write_text("version = 2\n")
    before = code_fingerprint(repo)
    source.write_text("version = 3\n")
    after = code_fingerprint(repo)
    record("R05_dirty_code_fingerprint_unchanged", before == after,
           "Changing already-dirty executable source invalidates cache.", dict(equal=before == after))

    # Planar pocket sits strictly between lattice probes. Independent analytic truth: 1 mm³ removed.
    block = Box(20, 24, 10)
    pocketed = block - Pos(1.25, 1.2, 4.5) * Box(1, 1, 1)
    plain_path, pocket_path = tmp / "plain.step", tmp / "pocket.step"
    export_step(block, str(plain_path))
    export_step(pocketed, str(pocket_path))
    plain, pocket = metrics.extract(plain_path), metrics.extract(pocket_path)
    verdict = metrics.compare(pocket, plain)
    record("R06_unsupported_planar_pocket_passes", verdict["verdict"] == "pass",
           "Unmeasured 1x1x1 mm extra pocket must fail or be not_evaluated, never full-part pass.",
           dict(verdict=verdict["verdict"], volume_delta_mm3=plain["volume_mm3"]-pocket["volume_mm3"],
                material=verdict["checks"].get("material"), unmodelled=pocket["unmodelled"]))

    unit = metrics.compare_printed(plain, {"units": "in", "features": []})
    record("R07_printed_units_ignored", unit["ok"] and not unit["units_ok"],
           "Printed unit mismatch cannot yield ok=true.", unit)

    # Use the existing source parameters, but no regenerate/overwrite of Hermes' outputs.
    params = dict(width=60.0, depth=40.0, thickness=6.0,
                  holes=[dict(x=15.0, y=10.0, diameter=8.0, through=True)])
    p = PartSpec(id="independent-review", family="review", template="plate_holes", params=params)
    dims = printed_dimensions(p)
    actual_x = next(d["value_mm"] for d in dims if d["role"] == "hole_x")
    expected_x = params["width"] / 2 + params["holes"][0]["x"]
    record("R08_edge_dimension_uses_centre_coordinate", actual_x != expected_x,
           "_draw_callouts draws from left edge; value must be 45, or use explicit centre datum for 15.",
           dict(printed_x=actual_x, left_edge_to_hole_mm=expected_x,
                printed_y=10, bottom_edge_to_hole_mm=30))

    block_labels = json.loads((args.pilot_root / "pilot-block-01/labels.json").read_text())
    layout = json.loads((args.pilot_root / "pilot-block-01/sheet-layout.json").read_text())
    expected = {d["role"] for d in block_labels["printed_dimensions"]}
    actual = {d["role"] for d in layout["printed_text"]}
    record("R09_claimed_dimension_not_printed", "pocket_height" in expected - actual,
           "Every printed_dimensions label must refer to a dimension actually present in drawing.",
           dict(missing_roles=sorted(expected-actual), expected_pocket_depth_mm=8))

tracked = ["eval/feature_metrics.py", "src/drawingto3d_lab/runner.py", "src/drawingto3d_lab/state.py",
           "src/drawingto3d_lab/generator.py", "src/drawingto3d_lab/pdfvec.py",
           "tests/test_feature_metrics.py", "tests/test_lab_runner.py"]
payload = dict(recorded_at=datetime.now(timezone.utc).isoformat(),
               source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in tracked},
               findings=findings)
destination = args.output or ROOT / "out/lab/review-probes" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
destination.parent.mkdir(parents=True, exist_ok=True)
if destination.exists():
    raise FileExistsError(f"Preserve prior audit evidence: {destination}")
destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+"\n")
for f in findings:
    print(f["id"], "REPRODUCED" if f["observed_bad"] else "not reproduced")
print(f"{sum(f['observed_bad'] for f in findings)}/{len(findings)} findings reproduced")
print(destination)
