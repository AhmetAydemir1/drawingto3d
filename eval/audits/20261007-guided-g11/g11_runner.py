"""G11 runner — one manifest case, one fresh session, real Chrome, real input events.

    ~/.hermes/cache/scratch/cdp-venv/bin/python g11_runner.py recipes/<case_id>.json

Reads the case's recipe (see DELIVERY-PLAN.md: decisions are authored from the visible session data
and the drawing only — the reference STEP is never read here), drives the guided flow end to end,
writes `cases/<case_id>.json` + `shots/<case_id>-*.png` and downloads the case's artifacts into
`cases/<case_id>/`. Geometry verdicts are produced afterwards by `evaluate_case.py` under `.venv-cad`
(cadquery is not in this interpreter).

Exits non-zero when the case recorded any failure; a recorded failure does not stop the run — G12 is
where generic fixes happen.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

G11_DIR = pathlib.Path(__file__).parent
ROOT = G11_DIR.parents[2]
sys.path.insert(0, str(G11_DIR.parent / "20261007-guided-ux-round"))
sys.path.insert(0, str(G11_DIR.parent / "20261006-guided-g3-review"))
import browser_acceptance as G3  # noqa: E402
import cdp_client as C  # noqa: E402
import ux_acceptance as UX  # noqa: E402

APP = G3.APP
CAD_PYTHON = ROOT / ".venv-cad/bin/python"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()


def wait_ingest(page: C.Chrome, timeout: float = 600.0) -> dict:
    """The session is ready when the trace has run (`callouts` derives) and options are listed."""
    deadline = time.time() + timeout
    data = None
    while time.time() < deadline:
        data = UX.server(page)
        if data and data.get("callouts") is not None and data.get("options"):
            return data
        time.sleep(0.4)
    raise TimeoutError("session did not finish ingesting the drawing")


def canvas_point(page: C.Chrome, px_point: list) -> dict:
    """Viewport point of an image-space coordinate, scrolled into view (mirrors draw()'s transform)."""
    return page.ev_async(f"""const token = new URLSearchParams(location.search).get('session');
      const data = await (await fetch('/api/guided/' + token)).json();
      const image = new Image(); image.src = data.drawing; await image.decode();
      const canvas = $('sheet'), rect = canvas.getBoundingClientRect();
      const s = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
      const y = rect.top + {px_point[1]} * s * rect.height / canvas.height;
      return {{x: rect.left + {px_point[0]} * s * rect.width / canvas.width, y: y,
               page_y: window.scrollY + y}};""")


def click_image_point(page: C.Chrome, px_point: list) -> None:
    found = canvas_point(page, px_point)
    page.ev(f"window.scrollTo(0, Math.max(0, {found['page_y']} - window.innerHeight / 2));")
    time.sleep(0.3)
    target = canvas_point(page, px_point)
    page.click(target["x"], target["y"])


def click_element(page, selector: str) -> None:
    """Click any CSS selector via its box (click_selector only resolves plain ids)."""
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def main() -> int:
    recipe = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    case_id, run_id = recipe["case_id"], time.strftime("%Y%m%d-%H%M%S")
    manifest = json.loads((ROOT / "eval/guided_10_manifest.json").read_text(encoding="utf-8"))
    entry = next((row for row in manifest["cases"] if row["case_id"] == case_id), None)
    if entry is None:
        raise SystemExit(f"case {case_id!r} is not in the frozen manifest")
    source = ROOT / recipe["source_path"]
    out_dir = G11_DIR / "cases" / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = G11_DIR / "shots"
    shots.mkdir(exist_ok=True)

    record = {
        "case_id": case_id, "run_id": run_id, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_head": git_head(), "source_path": recipe["source_path"],
        "source_sha256": sha256(source),
        "source_sha256_checked": sha256(source) == entry["source_sha256"],
        "scope_class": entry["expected_scope_class"], "prior_exposure": entry["prior_exposure"],
        "recipe": pathlib.Path(sys.argv[1]).name,
        "candidate_count": None, "manual_region_count": None, "ignored_count": None,
        "transcription_count": None, "parse_success_count": None, "parse_edit_count": None,
        "proposal_count": 0, "proposal_accept_count": 0, "manual_target_correction_count": 0,
        "review_import_used": False, "build_blockers": [], "build_success": False,
        "step_reopen": None, "bbox": None, "features": None, "final_geometry_verdict": None,
        "user_interventions": {}, "failures": [], "notes": [],
        "artifacts": {},
    }

    def fail(code: str, detail) -> None:
        record["failures"].append({"code": code, "detail": detail})
        print(f"[FAIL:{code}] {json.dumps(detail, ensure_ascii=False)[:300]}", flush=True)

    def note(text: str) -> None:
        record["notes"].append(text)

    page = C.Chrome(url=APP + "/guided")
    page.wait_ready()
    page.set_file("#file", str(source))
    page.wait_ev("!$('controls').hidden", timeout=300, label="session opened")
    data = wait_ingest(page)
    record["candidate_count"] = len(data["effective_callouts"])
    page.screenshot(str(shots / f"{case_id}-01-candidates.png"))
    print(f"[case {case_id}] candidates={record['candidate_count']}", flush=True)

    # --- the reading's own proposals (calibration, holes): the user accepts them one by one ---------
    if recipe.get("accept_proposals"):
        for wanted in recipe["accept_proposals"]:
            rows = page.ev("""return [...document.querySelectorAll('#proposals .proposal')].map(
              row => row.textContent);""")
            index = next((i for i, text in enumerate(rows or []) if wanted in text), None)
            if index is None:
                fail("DETECT_MISS", {"what": "proposal row", "wanted": wanted,
                                     "visible": [text[:120] for text in rows or []]})
                continue
            selector = f"#proposals .proposal:nth-child({index + 1}) button"
            click_element(page, selector)
            time.sleep(0.9)
        page.screenshot(str(shots / f"{case_id}-00-proposals.png"))

    # --- contour ---------------------------------------------------------------------------------
    profile_id = recipe["contour"]["profile_id"]
    profile = next((row for row in data["options"]["profiles"] if row["id"] == profile_id), None)
    if profile is None:
        fail("DETECT_MISS", {"what": "contour", "profile_id": profile_id,
                             "visible": [row["id"] for row in data["options"]["profiles"]]})
    else:
        page.click_selector("#pick-profile")
        time.sleep(0.3)
        click_image_point(page, profile["points"][0])
        try:
            page.wait_ev(f"$('profile').value === {json.dumps(profile_id)}", timeout=30, label="profile")
        except TimeoutError:
            # a second vertex of the same profile is a fair retry: the click missed the edge
            click_image_point(page, profile["points"][len(profile["points"]) // 2])
            page.wait_ev(f"$('profile').value === {json.dumps(profile_id)}", timeout=30, label="profile retry")

    # --- calibration (skipped when the reading's own calibration proposal was accepted) ----------
    calibration = recipe.get("calibration")
    measurement = None
    if calibration:
        measurement = next((row for row in data["options"]["measurements"]
                            if row.get("text") == calibration["measurement_text"]), None)
        if measurement is None:
            fail("DETECT_MISS", {"what": "calibration measurement", "text": calibration["measurement_text"],
                                 "visible": [row.get("text") for row in data["options"]["measurements"]]})
        else:
            page.click_selector("#pick-calibration")
            for circle_id in calibration["circles"]:
                point = UX.circle_point(page, circle_id)
                page.click(point["x"], point["y"])
                time.sleep(0.2)
            page.ev(f"""const select = $('measurement'); select.value = '{measurement['id']}';
              select.dispatchEvent(new Event('change')); return true;""")
            page.click_selector("#apply-calibration")
            try:
                UX.wait_server(page, lambda d: bool(d["decisions"].get("calibration")), 40, "calibration")
            except TimeoutError:
                fail("TRANSCRIPTION", {"what": "calibration", "measurement": measurement.get("text")})

    # --- thickness -------------------------------------------------------------------------------
    if recipe.get("thickness_mm") is not None:
        page.focus_selector("#thickness")
        page.ev("$('thickness').value = '';")
        page.type_text(str(recipe["thickness_mm"]))
        page.click_selector("#apply-thickness")
        try:
            UX.wait_server(page, lambda d: d["decisions"].get("thickness") == float(recipe["thickness_mm"]),
                           40, "thickness")
        except TimeoutError:
            fail("TRANSCRIPTION", {"what": "thickness", "value": recipe["thickness_mm"]})

    # --- the traced draft (a user decision, not a silent default) --------------------------------
    if recipe.get("acknowledge_trace"):
        page.click_selector("#ack")
        try:
            UX.wait_server(page, lambda d: d["decisions"].get("trace_acknowledged") is True, 40, "ack")
        except TimeoutError:
            fail("TRANSCRIPTION", {"what": "trace acknowledgement"})

    # --- the authored callout decisions ----------------------------------------------------------
    typed_texts = hint_clicks = single_ignores = 0
    for step in recipe["decisions"]:
        hint = step["hint"]
        matches = [item for item in data["effective_callouts"]
                   if item.get("machine_text_hint") == hint]
        if step.get("region") and len(matches) > 1:
            # ambiguous printed text (e.g. two "20" boxes): the recipe's region centre picks the box
            wanted = step["region"]
            centre = lambda row: ((row["region"][0] + row["region"][2]) / 2,      # noqa: E731
                                 (row["region"][1] + row["region"][3]) / 2)
            want_x, want_y = (wanted[0] + wanted[2]) / 2, (wanted[1] + wanted[3]) / 2
            matches.sort(key=lambda row: (centre(row)[0] - want_x) ** 2 + (centre(row)[1] - want_y) ** 2)
        row = matches[0] if matches else None
        if row is None:
            fail("DETECT_MISS", {"what": "callout", "hint": hint})
            continue
        callout_id, action = row["id"], step["action"]
        if action == "ignore":
            UX.ignore_callout(page, callout_id)
            single_ignores += 1
            continue
        if action == "accept_hint":
            accepted = UX.accept_hint(page, callout_id)
            hint_clicks += 1
            stored = next((item for item in accepted["data"]["decisions"]["transcriptions"]
                           if item["callout_id"] == callout_id), None)
            if not stored or stored["raw_text"] != hint:
                fail("TRANSCRIPTION", {"hint": hint, "stored": (stored or {}).get("raw_text")})
        elif action == "transcribe":
            parse = UX.save_text(page, callout_id, step["text"])
            typed_texts += 1
            if parse["status"] != "parsed":
                code = "PARSE_AMBIGUOUS" if parse["status"] == "ambiguous" else "PARSE_UNSUPPORTED"
                fail(code, {"hint": hint, "text": step["text"], "status": parse["status"],
                            "warnings": parse["warnings"]})
        else:
            fail("TRANSCRIPTION", {"what": "unknown recipe action", "action": action})
            continue
        target = step.get("target")
        if target is None:
            note(f"{hint}: no target declared (left to readiness)")
        elif target == "unbindable":
            UX.declare_unbindable(page, callout_id)
        elif isinstance(target, dict) and target.get("proposal"):
            panel = UX.target_panel(page)
            record["proposal_count"] += len(panel["proposals"])
            if panel["proposals"]:
                page.click_selector("#target-confirm")
                UX.wait_server(page, lambda d: any(
                    item["callout_id"] == callout_id and item.get("status") == "confirmed"
                    for item in d["decisions"].get("callout_targets") or []), 60, "target proposal")
                record["proposal_accept_count"] += 1
            elif target.get("fallback_circles"):
                UX.save_target_manual(page, callout_id, target.get("kind", "circle"),
                                      target["fallback_circles"])
                record["manual_target_correction_count"] += 1
                note(f"{hint}: no proposal offered; decided by hand {target['fallback_circles']}")
            else:
                fail("BIND_NO_PROPOSAL", {"hint": hint})
        elif isinstance(target, dict) and target.get("circles"):
            UX.save_target_manual(page, callout_id, target.get("kind", "circle"), target["circles"])
            record["manual_target_correction_count"] += 1
        else:
            fail("BIND_WRONG_PROPOSAL", {"what": "unknown target recipe", "target": target})

    page.screenshot(str(shots / f"{case_id}-02-decided.png"))

    # --- the remaining scope: one explicit bulk decision (UX round flow) -------------------------
    bulk_rows = 0
    undecided = UX.undecided_ids(UX.server(page))
    if undecided:
        page.click_selector("#callout-ignore-many")
        page.wait_ev("$('status').textContent.includes('tekrar tıklayın')", timeout=30, label="bulk armed")
        page.click_selector("#callout-ignore-many")
        UX.wait_server(page, lambda d: all((UX.reviews_of(d).get(cid) or {}).get("ignored")
                                           for cid in undecided), 90, "bulk ignored")
        bulk_rows = len(undecided)
    final = UX.server(page)
    record["ignored_count"] = sum(1 for row in final["effective_callouts"] if row["ignored"])
    record["manual_region_count"] = len(final["decisions"].get("manual_callouts") or [])
    record["transcription_count"] = len(final["decisions"].get("transcriptions") or [])
    record["parse_success_count"] = sum(1 for row in final.get("callout_parses") or []
                                        if row["status"] == "parsed")
    log = final.get("log") or []
    record["parse_edit_count"] = sum(1 for row in log if row.get("action") == "edit_transcription")
    record["user_interventions"] = {
        "typed_texts": typed_texts, "hint_clicks": hint_clicks, "single_ignores": single_ignores,
        "bulk_rows": bulk_rows, "bulk_actions": 1 if bulk_rows else 0,
        "proposal_accepts": len(recipe.get("accept_proposals") or []),
        "profile_selections": 1, "calibration_entries": 1 if measurement else 0,
        "thickness_entries": 1 if recipe.get("thickness_mm") is not None else 0,
        "trace_acknowledgements": 1 if recipe.get("acknowledge_trace") else 0,
    }

    # --- readiness (its blockers are recorded verbatim, never smoothed) --------------------------
    readiness = UX.readiness_of(page)
    record["build_blockers"] = [row["text"] for row in readiness["questions"]]
    if record["build_blockers"]:
        for row in readiness["questions"]:
            print(f"[blocker] {row['category']}: {row['text'][:160]}", flush=True)
        page.screenshot(str(shots / f"{case_id}-03-blocked.png"))
    else:
        page.screenshot(str(shots / f"{case_id}-03-ready.png"))
        page.click_selector("#build")
        try:
            final = UX.wait_server(page, lambda d: bool(d.get("step")), timeout=420, label="built STEP")
            record["build_success"] = final.get("build_status") == "complete"
            if not record["build_success"]:
                fail("CAD_WRONG", {"build_status": final.get("build_status"), "error": final.get("error")})
        except TimeoutError:
            fail("CAD_UNSUPPORTED", {"what": "build did not produce a STEP"})
            final = UX.server(page)
        page.screenshot(str(shots / f"{case_id}-04-built.png"))

        for name, key in (("part.step", "step"), ("plan.json", "plan"), ("plan-audit.json", "audit")):
            url = APP + (final.get(key) or "")
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    (out_dir / name).write_bytes(response.read())
                record["artifacts"][name] = str((out_dir / name).relative_to(ROOT))
            except Exception as error:  # noqa: BLE001 - a missing artifact is a recorded failure
                fail("STEP_EXPORT", {"artifact": name, "error": str(error)})
        (out_dir / "session-public.json").write_text(json.dumps(final, ensure_ascii=False, indent=2),
                                                     encoding="utf-8")
        record["artifacts"]["session-public.json"] = str((out_dir / "session-public.json").relative_to(ROOT))
        bundle = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
          return await (await fetch('/api/guided/export', {method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")
        (out_dir / "review-bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
        record["artifacts"]["review-bundle.json"] = str((out_dir / "review-bundle.json").relative_to(ROOT))
        if (out_dir / "plan.json").exists():
            plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
            record["features"] = {"plan_lists": {key: len(value) for key, value in plan.items()
                                                 if isinstance(value, list)}}

    errors = [row for row in page.console if row["level"] == "error"]
    record["console_errors"] = errors
    record["rejected_requests"] = page.failures
    if errors or page.failures:
        fail("EVALUATOR", {"console_errors": errors, "rejected_requests": page.failures})
    page.close()

    # --- geometry verdict: the repo's own evaluator, in the CAD interpreter ----------------------
    if record["build_success"]:
        produced = out_dir / "part.step"
        reference = entry.get("reference_identifier_evaluator_only")
        command = [str(CAD_PYTHON), str(G11_DIR / "evaluate_case.py"), str(produced),
                   str(ROOT / reference) if reference else "-"]
        completed = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, timeout=900)
        (out_dir / "evaluate.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            fail("EVALUATOR", {"exit": completed.returncode, "log": "cases/%s/evaluate.log" % case_id})
        else:
            verdict = json.loads(completed.stdout.strip().splitlines()[-1])
            record["step_reopen"] = verdict["step_reopen"]
            record["bbox"] = verdict["bbox"]
            record["features"] = {**(record["features"] or {}), **verdict["features"]}
            record["final_geometry_verdict"] = verdict["final_geometry_verdict"]
            if verdict["step_reopen"] is False:
                fail("STEP_REOPEN", {"detail": "importStep failed on the produced file"})
            if record["final_geometry_verdict"] and not record["final_geometry_verdict"]["pass"]:
                fail("CAD_WRONG", {"checks": record["final_geometry_verdict"]["checks"]})
    elif record["build_blockers"]:
        fail("CONSTRAINT_UNSUPPORTED", {"what": "build never ran", "blockers": len(record["build_blockers"])})

    path = G11_DIR / "cases" / f"{case_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[{case_id}] failures={len(record['failures'])} build={record['build_success']} "
          f"verdict={'pass' if (record['final_geometry_verdict'] or {}).get('pass') else record['final_geometry_verdict'] and 'fail'}"
          f" -> {path.relative_to(ROOT)}", flush=True)
    return 1 if record["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
