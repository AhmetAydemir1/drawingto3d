"""G11 runner — one manifest case, one fresh session, real Chrome, real input events.

    ~/.hermes/cache/scratch/cdp-venv/bin/python g11_runner.py recipes/<case_id>.json
    ~/.hermes/cache/scratch/cdp-venv/bin/python g11_runner.py rerun-round2/recipes/<case_id>.json \
        --round rerun-round2

Reads the case's recipe (see DELIVERY-PLAN.md: decisions are authored from the visible session data
and the drawing only — the reference STEP is never read here), drives the guided flow end to end,
writes `<round>/cases/<case_id>.json` + `<round>/shots/<case_id>-*.png` and downloads the case's
artifacts into `<round>/cases/<case_id>/`. Geometry verdicts are produced afterwards by
`evaluate_case.py` under `.venv-cad` (cadquery is not in this interpreter).

G11R-04/G11R-05 (independent review): session, export bundle, readiness, session token, recipe
identity and the server's own error response are recorded for every case — recorded no matter how
the build ended; only STEP/plan downloads stay gated on a real build. Browser/network noise is
telemetry (`browser_signals`), never the EVALUATOR code — that label belongs to the evaluator
subprocess alone, and build failures are classified by the server's response.

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
import g11_evidence as EVIDENCE  # noqa: E402  (same directory)
import ux_acceptance as UX  # noqa: E402

APP = G3.APP
CAD_PYTHON = ROOT / ".venv-cad/bin/python"


def parse_args(argv: list[str]) -> tuple[str, str | None]:
    """Recipe path plus the optional round directory (`--round rerun-round2`)."""
    args = list(argv)
    round_name = None
    if "--round" in args:
        index = args.index("--round")
        if index + 1 >= len(args):
            raise SystemExit("--round needs a directory name, e.g. --round rerun-round2")
        round_name = args[index + 1]
        del args[index:index + 2]
    if len(args) != 1:
        raise SystemExit("usage: g11_runner.py <recipe.json> [--round <dir>]")
    return args[0], round_name


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


def click_image_point(page: C.Chrome, px_point: list) -> dict:
    """Viewport point of an image-space coordinate; click directly when visible (proven path)."""
    target = canvas_point(page, px_point)
    if not (20 <= target["y"] <= 700 and 30 <= target["x"] <= 1100):
        page.ev("$('sheet').scrollIntoView({block:'start'});")
        time.sleep(0.4)
        target = canvas_point(page, px_point)
    page.click(target["x"], target["y"])
    return target


def click_element(page, selector: str) -> None:
    """Click any CSS selector via its box (click_selector only resolves plain ids)."""
    page.ev(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}});")
    time.sleep(0.25)
    box = page.box(selector)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def accept_hint_ux01(page: C.Chrome, callout_id: str) -> dict:
    """UX-01 one-click acceptance: select the row, then click “Evet, doğru” — one real input.

    (Replaces the UX-round helper whose single click targeted `#callout-hint-save`; UX-01 renamed the
    controls to `#callout-hint-yes`/`-edit`/`-ignore`.)
    """
    box = UX.row_box(page, callout_id)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    page.wait_ev("!$('callout-hint-yes').hidden", timeout=30, label="hint row")
    before = {"line": page.ev("return $('callout-hint-line').textContent;"),
              "field": page.ev("return $('callout-text').value;"),
              "clicks": 1}
    page.click_selector("#callout-hint-yes")
    data = UX.wait_server(page, lambda d: any(
        row["callout_id"] == callout_id and row.get("raw_text")
        for row in d["decisions"].get("transcriptions") or []), 60, f"hint accepted ({callout_id})")
    return {"before": before, "data": data}


def build_response_probe(page: C.Chrome) -> dict:
    """The server's own answer to the failed build POST: raw body via CDP plus the UI's error text.

    G11R-04/G11R-05: a refused build must carry the actual server response, and the failure code is
    classified from that text — not from the browser's generic resource errors.
    """
    probe: dict = {"captured": False}
    try:
        probe["ui_error_text"] = page.ev("return $('status').textContent;")
    except Exception:  # noqa: BLE001 — the probe itself must never abort the record
        pass
    try:
        request_id = next((rid for rid, label in reversed(list(page.requests.items()))
                           if "/api/guided/build" in label), None)
        if request_id:
            body = page.send("Network.getResponseBody", requestId=request_id)
            raw = body.get("body", "")
            probe.update({"captured": True, "request": page.requests[request_id],
                          "body_text": raw[:4000]})
            try:
                probe["body"] = json.loads(raw)
            except (ValueError, TypeError):
                probe["body"] = None
    except Exception as error:  # noqa: BLE001 — a failed capture is recorded, never smoothed over
        probe["capture_error"] = f"{type(error).__name__}: {error}"
    return probe


def main() -> int:
    recipe_path, round_name = parse_args(sys.argv[1:])
    recipe_path = pathlib.Path(recipe_path)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    case_id, run_id = recipe["case_id"], time.strftime("%Y%m%d-%H%M%S")
    manifest = json.loads((ROOT / "eval/guided_10_manifest.json").read_text(encoding="utf-8"))
    entry = next((row for row in manifest["cases"] if row["case_id"] == case_id), None)
    if entry is None:
        raise SystemExit(f"case {case_id!r} is not in the frozen manifest")
    source = ROOT / recipe["source_path"]
    base = G11_DIR / round_name if round_name else G11_DIR
    out_dir = base / "cases" / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = base / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    record = {
        "case_id": case_id, "run_id": run_id, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "round": round_name or "official",
        "git_head": git_head(), "source_path": recipe["source_path"],
        "source_sha256": sha256(source),
        "source_sha256_checked": sha256(source) == entry["source_sha256"],
        "scope_class": entry["expected_scope_class"], "prior_exposure": entry["prior_exposure"],
        "recipe": recipe_path.name, "recipe_file": str(recipe_path.relative_to(ROOT))
        if recipe_path.is_relative_to(ROOT) else str(recipe_path),
        "recipe_sha256": sha256(recipe_path),
        "recipe_notes": recipe.get("notes") or [],
        "input_verification": recipe.get("input_verification"),
        "session_token": None, "session_origin": "token-recovered" if recipe.get("session_token")
        else "fresh-upload",
        "calibration": None, "readiness": None, "build_error_response": None, "browser_signals": None,
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

    token = recipe.get("session_token")
    if token:
        # recover an orphaned session: the server computed it but the client fetch died
        note(f"oturum token ile bağlandı: {token} (taze yükleme değil)")
        page = C.Chrome(url=APP + "/guided?session=" + token)
        page.wait_ready()
    else:
        page = C.Chrome(url=APP + "/guided")
        page.wait_ready()
        page.set_file("#file", str(source))
        # the token lands in the URL as soon as the upload does — keep it for reattachment
        for _ in range(240):
            token = page.ev("return new URLSearchParams(location.search).get('session');")
            if token:
                note(f"session token: {token}")
                break
            time.sleep(0.5)
    record["session_token"] = token
    try:
        page.wait_ev("!$('controls').hidden", timeout=900, label="session opened")
    except Exception:                                    # noqa: BLE001 — gate timeout or a dead CDP link
        if not token:
            raise
        note("client gate failed; reattaching via token (slow raster ingest)")
        try:
            page.close()
        except Exception:
            pass
        page = C.Chrome(url=APP + "/guided?session=" + token)
        page.wait_ready()
        page.wait_ev("!$('controls').hidden", timeout=2700, label="session opened (reattached)")
    # G11R-04: yavaş raster ingest'lerinde open-fetch 120 sn'lik ilk yoklamadan sonra çözülür; kapı
    # açıldığında token URL'de garantidir — burada yakalanır ki kayıt oturum token'ı olmadan kalmasın.
    if not token:
        token = page.ev("return new URLSearchParams(location.search).get('session');")
        if token:
            note(f"oturum token (kapı sonrası yakalandı): {token}")
    record["session_token"] = token
    data = wait_ingest(page, timeout=2700)
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
        # Server-authoritative: never skip the pick because the select's DOM happens to show the id.
        # (The pilot's exercise-13 run ended `missing_profile` at the gate with no profile write in the
        # session log — the DOM skip at this line was the only non-failing path through the block.)
        server_now = UX.server(page) or {}
        if (server_now.get("decisions") or {}).get("profile_id") != profile_id:
            page.click_selector("#pick-profile")
            time.sleep(0.3)
            picked = False
            for point in (profile["points"][0], profile["points"][len(profile["points"]) // 2],
                          profile["points"][len(profile["points"]) // 4]):
                click_image_point(page, point)
                try:
                    # the server, not the select's DOM value: that is where the decision lives
                    UX.wait_server(page, lambda d: d["decisions"].get("profile_id") == profile_id,
                                   20, "profile")
                    picked = True
                    break
                except TimeoutError:
                    page.click_selector("#pick-profile")
                    time.sleep(0.3)
            if not picked:
                fail("DETECT_MISS", {"what": "contour click", "profile_id": profile_id,
                                     "reason": "sunucu seçimi kaydetmedi"})

    # --- contour validation issues (PLAN §7.3 UI): the user drops the marked edge / approves the join
    edge_drops = 0
    for _round in range(3):
        drops = page.ev(
            """[...$('contour-fix').querySelectorAll('button')]"""
            """.filter(b => b.textContent.includes('kenarını çıkar')).map(b => b.textContent)""")
        if not drops:
            break
        before = len(((UX.server(page) or {}).get("decisions", {}).get("contour", {}).get("drop") or []))
        click_element(page, "#contour-fix button")  # the panel marks which edge to remove
        try:
            UX.wait_server(page, lambda d: len(d["decisions"].get("contour", {}).get("drop") or []) > before,
                           30, "edge drop")
            edge_drops += 1
            note(f"kontur düzeltmesi: kenar çıkarıldı ({drops[0]})")
        except TimeoutError:
            fail("CONSTRAINT_UNSUPPORTED", {"what": "contour edge drop", "panel": drops[:2]})
            break
    if page.ev("!![...$('contour-fix').querySelectorAll('input[type=checkbox]')].length"):
        if not page.ev("(() => { const b = $('contour-fix').querySelector('input[type=checkbox]'); return b && b.checked; })()"):
            click_element(page, "#contour-fix input[type=checkbox]")
            try:
                UX.wait_server(page, lambda d: bool((d["decisions"].get("contour") or {}).get("approve_join")),
                               20, "contour join")
            except TimeoutError:
                fail("CONSTRAINT_UNSUPPORTED", {"what": "contour join approval"})

    # --- calibration (skipped when the reading's own calibration proposal was accepted) ----------
    # G11R-02: a recipe may carry `manual_value` — the user read the printed number, the value is
    # typed into `#cal-value` and the two clicked snap points are the span the printed dimension
    # actually measures ("Ölçüyü ben gireceğim"). An OCR measurement row is only selected when the
    # recipe names one; an uncertain OCR guess is never presented as a certain decision.
    calibration = recipe.get("calibration")
    if calibration:
        manual = calibration.get("manual_value")
        if manual is not None:
            page.click_selector("#pick-calibration")
            for circle_id in calibration["circles"]:
                point = UX.circle_point(page, circle_id)
                page.click(point["x"], point["y"])
                time.sleep(0.2)
            page.focus_selector("#cal-value")
            page.ev("$('cal-value').value = '';")
            page.type_text(str(manual))
            page.ev("const select = $('cal-unit'); select.value = '%s'; return select.value;"
                    % calibration.get("unit", "mm"))
            page.click_selector("#apply-calibration")
            try:
                saved = UX.wait_server(
                    page, lambda d: (d["decisions"].get("calibration") or {}).get("value") == float(manual),
                    40, "calibration (manual)")
                record["calibration"] = saved["decisions"]["calibration"]
            except TimeoutError:
                fail("TRANSCRIPTION", {"what": "calibration", "manual_value": manual,
                                       "circles": calibration["circles"]})
        else:
            measurement = next((row for row in data["options"]["measurements"]
                                if row.get("text") == calibration["measurement_text"]), None)
            if measurement is None:
                fail("DETECT_MISS", {"what": "calibration measurement",
                                     "text": calibration["measurement_text"],
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
                    saved = UX.wait_server(page, lambda d: bool(d["decisions"].get("calibration")),
                                           40, "calibration")
                    record["calibration"] = saved["decisions"]["calibration"]
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
        acked = False
        for _attempt in range(3):
            if (UX.server(page) or {}).get("decisions", {}).get("trace_acknowledged") is True:
                acked = True
                break
            if not page.ev("$('ack').checked"):
                page.click_selector("#ack")
            try:
                UX.wait_server(page, lambda d: d["decisions"].get("trace_acknowledged") is True, 15, "ack")
                acked = True
                break
            except TimeoutError:
                page.ev("location.reload(); true;")   # a fresh render re-syncs the draft state
                page.wait_ready()
                time.sleep(1.2)
        if not acked:
            fail("TRANSCRIPTION", {"what": "trace acknowledgement"})

    # --- the view direction / sheet frame: the user confirms it before producing (PLAN §8.6) ------
    if recipe.get("confirm_view") and not (UX.server(page) or {}).get("decisions", {}).get("view"):
        if not page.ev("$('view-ack').checked"):
            page.click_selector("#view-ack")
        page.click_selector("#view-confirm")
        try:
            UX.wait_server(page, lambda d: bool(d["decisions"].get("view")), 40, "view")
        except TimeoutError:
            fail("CONSTRAINT_UNSUPPORTED", {"what": "view confirmation"})

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
            accepted = accept_hint_ux01(page, callout_id)
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

    # --- the remaining scope: one explicit bulk decision (UX-01 §7 flow) --------------------------
    bulk_rows = 0
    undecided = UX.undecided_ids(UX.server(page))
    if undecided:
        page.click_selector("#callout-multi")
        page.wait_ev("$('callout-bulk-bar').hidden === false", timeout=30, label="select mode")
        for callout_id in undecided:
            box = UX.row_box(page, callout_id)
            page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
            time.sleep(0.12)
        page.click_selector("#callout-bulk-apply")
        UX.wait_server(page, lambda d: all((UX.reviews_of(d).get(cid) or {}).get("ignored")
                                           for cid in undecided), 120, "bulk ignored")
        bulk_rows = len(undecided)
    final = UX.server(page)
    record["ignored_count"] = sum(1 for row in final["effective_callouts"] if row["ignored"])
    record["manual_region_count"] = len(final["decisions"].get("manual_callouts") or [])
    record["transcription_count"] = len(final["decisions"].get("transcriptions") or [])
    record["parse_success_count"] = sum(1 for row in final.get("callout_parses") or []
                                        if row["status"] == "parsed")
    log = final.get("log") or []
    record["parse_edit_count"] = sum(1 for row in log if row.get("action") == "edit_transcription")
    # §29 counters, derived from the session's own log (the pilot's hardcoded `profile_selections: 1`
    # claimed a selection for a session that had none — counters must come from the record).
    typed_from_log = [row for row in log if row.get("action") in ("transcribe", "edit_transcription")
                      and not (row.get("evidence") or {}).get("accepted_hint")]
    hints_from_log = [row for row in log if (row.get("evidence") or {}).get("accepted_hint") is True]
    singles_from_log = [row for row in log if row.get("action") == "ignore_callout"
                        and (row.get("evidence") or {}).get("bulk") is not True]
    bulk_from_log = [row for row in log if row.get("action") == "bulk_ignore_callouts"]
    decisions_now = final.get("decisions") or {}
    record["user_interventions"] = {
        "typed_texts": len(typed_from_log) or typed_texts,
        "hint_clicks": len(hints_from_log) or hint_clicks,
        "single_ignores": len(singles_from_log) or single_ignores,
        "bulk_rows": sum(int((row.get("value") or {}).get("count") or 0) for row in bulk_from_log) or bulk_rows,
        "bulk_actions": len(bulk_from_log),
        "edge_drops": edge_drops,
        "proposal_accepts": len(recipe.get("accept_proposals") or []),
        "profile_selections": 1 if decisions_now.get("profile_id") else 0,
        "calibration_entries": 1 if decisions_now.get("calibration") else 0,
        "thickness_entries": 1 if decisions_now.get("thickness") is not None else 0,
        "trace_acknowledgements": 1 if decisions_now.get("trace_acknowledged") else 0,
    }

    # --- readiness (its blockers are recorded verbatim, never smoothed) --------------------------
    readiness = UX.readiness_of(page)
    record["readiness"] = {
        "ready": readiness.get("ready"),
        "questions": [row["text"] for row in readiness.get("questions") or []],
        "captured": "run-time",
    }
    record["build_blockers"] = [row["text"] for row in readiness["questions"]]
    final = None
    if record["build_blockers"]:
        for row in readiness["questions"]:
            print(f"[blocker] {row['category']}: {row['text'][:160]}", flush=True)
        page.screenshot(str(shots / f"{case_id}-03-blocked.png"))
    else:
        page.screenshot(str(shots / f"{case_id}-03-ready.png"))
        try:
            page.wait_ev("!$('build').disabled", timeout=120, label="build enabled")
        except TimeoutError:
            late = UX.readiness_of(page)
            record["build_blockers"] = [row["text"] for row in late["questions"]] or \
                ["üretim düğmesi 120 sn içinde etkinleşmedi"]
            fail("CONSTRAINT_UNSUPPORTED", {"what": "build button stayed disabled"})
            final = UX.server(page)
        else:
            page.click_selector("#build")
            try:
                final = UX.wait_server(page, lambda d: bool(d.get("step")), timeout=420, label="built STEP")
                record["build_success"] = final.get("build_status") == "complete"
                if not record["build_success"]:
                    # the build ran and stopped inside CAD: the server's own error text is the cause
                    code, why = EVIDENCE.classify_build_error(final.get("error"))
                    fail(code, {"what": "build ran and failed", "cause": why,
                                "build_status": final.get("build_status"),
                                "error": final.get("error")})
            except TimeoutError:
                # the endpoint refused (or produced nothing): keep the server's actual response
                record["build_error_response"] = build_response_probe(page)
                body = record["build_error_response"].get("body")
                body_error = body.get("error") if isinstance(body, dict) else None
                code, why = EVIDENCE.classify_build_error(
                    body_error or record["build_error_response"].get("ui_error_text"))
                fail(code, {"what": "build did not produce a STEP", "cause": why,
                            "server_response": record["build_error_response"]})
                final = UX.server(page)
            page.screenshot(str(shots / f"{case_id}-04-built.png"))

    # --- per-case evidence: written no matter how the build ended (G11R-04) ----------------------
    if final is None:
        final = UX.server(page)
    if final.get("step"):  # STEP/plan downloads stay gated on a real build
        for name, key in (("part.step", "step"), ("plan.json", "plan"), ("plan-audit.json", "audit")):
            url = APP + (final.get(key) or "")
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    (out_dir / name).write_bytes(response.read())
                record["artifacts"][name] = str((out_dir / name).relative_to(ROOT))
            except Exception as error:  # noqa: BLE001 - a missing artifact is a recorded failure
                fail("STEP_EXPORT", {"artifact": name, "error": str(error)})
        plan_file = out_dir / "plan.json"
        if plan_file.exists() and plan_file.read_text(encoding="utf-8", errors="replace").lstrip().startswith("{"):
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
            record["features"] = {"plan_lists": {key: len(value) for key, value in plan.items()
                                                 if isinstance(value, list)}}
    bundle = page.ev_async("""const token = new URLSearchParams(location.search).get('session');
      return await (await fetch('/api/guided/export', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})})).json();""")
    for name in EVIDENCE.write_case_evidence(out_dir, final, bundle, readiness):
        record["artifacts"][name] = str((out_dir / name).relative_to(ROOT))
    if not final.get("step"):
        note("build çıktısı yok: session/review/readiness kanıtı yine de kaydedildi; yalnız "
             "STEP/plan indirmeleri gerçek üretime bağlı kaldı (G11R-04).")

    errors = [row for row in page.console if row["level"] == "error"]
    record["console_errors"] = errors
    record["rejected_requests"] = page.failures
    record["browser_signals"] = EVIDENCE.classify_signals(errors, page.failures)
    # G11R-05: console/network noise is UI telemetry — never the EVALUATOR code, whose only source
    # is the evaluator subprocess below; a refused build carries its own server-side cause above.
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

    # G11R-04: round koşularında kayıt da turun kendi dizinine yazılır (koşu sırasında yol resmî
    # vaka dizinine sabitti; rerun-round2 kayıtları yanlışlıkla oraya yazıldı — tur sonrası taşındı).
    path = base / "cases" / f"{case_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[{case_id}] failures={len(record['failures'])} build={record['build_success']} "
          f"verdict={'pass' if (record['final_geometry_verdict'] or {}).get('pass') else record['final_geometry_verdict'] and 'fail'}"
          f" -> {path.relative_to(ROOT)}", flush=True)
    return 1 if record["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
