"""G11R-03 — real-browser check of the ignore/hint-ignore auto-advance fix.

    ~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g11-fixes/g11r03_browser_check.py

Spawns the three-callout fixture server (project venv), drives REAL mouse clicks in Chrome 9222 and
checks the exact flows the review found broken, plus the states it asked for:

  S1  ignore the MIDDLE row (ignored hidden, the default) -> the next open field after it is selected
      (the reported bug: selection vanished and the detail panel closed)
  S2  "Sonraki eksik" still works manually and wraps to the first open row
  S3  the hint-ignore button ("Bu bir ölçü/not değil" under the hint) advances the same way
  S4  last open row, ignored rows shown -> no jump, the row stays selected and "all done" is shown
  S5  "Geri al" (restore) keeps the user in place
  S6  last open row, ignored rows hidden -> the list empties cleanly, "all done"

guided.js is a module, so its `let selectedCallout` is not reachable from Runtime.evaluate; the
selected callout is derived the way the list renders: visible-list order (server) + selected <li>
index (DOM). Writes `g11r03-ui-result.json` + screenshots next to this file; exit 0 only when every
check passed.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "eval/audits/20261007-guided-ux-round"))
sys.path.insert(0, str(ROOT / "eval/audits/20261006-guided-g3-review"))
import cdp_client as C  # noqa: E402
import ux_acceptance as UX  # noqa: E402

VENV_PYTHON = ROOT / ".venv/bin/python"


def spawn_server() -> tuple[subprocess.Popen, dict]:
    proc = subprocess.Popen([str(VENV_PYTHON), str(HERE / "g11r03_fixture_server.py")],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin:/usr/local/bin"})
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if not line.strip().startswith("{"):
        raise RuntimeError(f"fixture server did not report a URL: {line!r}")
    return proc, json.loads(line)


def ui(page: C.Chrome) -> dict:
    """What the user sees: rows, selected index, detail flag, remaining line, show-ignored flag."""
    return page.ev_async("""const li=[...document.querySelectorAll('#callout-list li')];
      return {rows: li.map(item=>item.textContent), selected: li.findIndex(item=>item.classList.contains('selected')),
              detailHidden: $('callout-detail').hidden, remaining: $('callout-remaining').textContent,
              showIgnored: $('callout-show-ignored').checked};""")


def visible_ids(server: dict, show_ignored: bool) -> list[str]:
    return [row["id"] for row in server["effective_callouts"] if show_ignored or not row["ignored"]]


def snapshot(page: C.Chrome) -> dict:
    """UI state + server state, with the selected callout id derived from the render order."""
    seen = ui(page)
    data = UX.server(page)
    ids = visible_ids(data, seen["showIgnored"])
    seen["revision"] = data["revision"]
    seen["selectedId"] = ids[seen["selected"]] if 0 <= seen["selected"] < len(ids) else None
    return seen


def wait_view(page: C.Chrome, wanted, timeout: float, label: str) -> dict:
    deadline = time.time() + timeout
    state = snapshot(page)
    while True:
        if wanted(state):
            return state
        if time.time() >= deadline:
            raise TimeoutError(f"view condition not met: {label} — last "
                               f"{json.dumps(state, ensure_ascii=False)}")
        time.sleep(0.35)
        state = snapshot(page)


def click_row(page: C.Chrome, callout_id: str, show_ignored: bool) -> None:
    box = UX.row_box(page, callout_id, show_ignored=show_ignored)
    page.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def reviews(data: dict) -> dict:
    return {row["callout_id"]: row for row in data["decisions"].get("callout_reviews") or []}


def main() -> int:
    server, meta = spawn_server()
    steps: list[dict] = []
    failures: list[str] = []
    page = None

    def check(label: str, condition: bool, detail: dict) -> None:
        steps.append({"step": label, "passed": bool(condition), **detail})
        if not condition:
            failures.append(label)
        print(f"[{'ok' if condition else 'FAIL'}] {label}", flush=True)

    try:
        page = C.Chrome(url=meta["url"])
        page.wait_ready()
        page.wait_ev("!$('controls').hidden", timeout=120, label="session open")
        UX.wait_state(page)
        page.screenshot(str(HERE / "g11r03-ui-00-baseline.png"))
        before = snapshot(page)
        check("S0 baseline: three open fields listed, none selected, detail hidden",
              len(before["rows"]) == 3 and before["selected"] == -1 and before["detailHidden"]
              and before["remaining"] == "3 kontrol kaldı", before)

        # S1 — the reported bug: ignore the MIDDLE row while ignored rows stay hidden.
        click_row(page, "k2", show_ignored=False)
        page.wait_ev("!$('callout-detail').hidden", timeout=30, label="k2 detail open")
        page.click_selector("#callout-ignore")
        data = UX.wait_server(page, lambda d: reviews(d).get("k2", {}).get("ignored") is True,
                              60, "k2 ignored")
        after = wait_view(page, lambda s: s["selectedId"] == "k3" and not s["detailHidden"], 20,
                          "advance to k3 after ignoring the middle row")
        page.screenshot(str(HERE / "g11r03-ui-01-after-ignore.png"))
        check("S1 ignore #callout-ignore (middle row, hidden): selection moved to the NEXT open field",
              after["selectedId"] == "k3" and not after["detailHidden"] and after["selected"] == 1
              and after["remaining"] == "2 kontrol kaldı",
              {"selectedId": after["selectedId"], "selected": after["selected"],
               "detailHidden": after["detailHidden"], "rows": after["rows"],
               "remaining": after["remaining"], "revision": data["revision"]})

        # S2 — the manual "Sonraki eksik" control still works and wraps.
        page.click_selector("#callout-next")
        wrap = wait_view(page, lambda s: s["selectedId"] == "k1", 20, "next wraps k3 -> k1")
        check("S2 manual Sonraki eksik wraps k3 -> k1",
              wrap["selectedId"] == "k1" and wrap["selected"] == 0, wrap)

        # S3 — the hint-ignore button follows the same fixed path (k1's hint exists).
        page.click_selector("#callout-hint-ignore")
        data = UX.wait_server(page, lambda d: reviews(d).get("k1", {}).get("ignored") is True,
                              60, "k1 hinted-ignored")
        hinted = wait_view(page, lambda s: s["selectedId"] == "k3" and not s["detailHidden"], 20,
                           "advance to k3 after hint-ignore")
        check("S3 hint-ignore advances to the only open field left (k3)",
              hinted["selectedId"] == "k3" and not hinted["detailHidden"]
              and hinted["remaining"] == "1 kontrol kaldı",
              {"selectedId": hinted["selectedId"], "detailHidden": hinted["detailHidden"],
               "rows": hinted["rows"], "remaining": hinted["remaining"],
               "revision": data["revision"]})

        # S4 — show ignored rows, then ignore the LAST open row: no jump, stays selected.
        page.click_selector("#callout-show-ignored")
        page.wait_ev("$('callout-show-ignored').checked", timeout=10, label="show ignored on")
        click_row(page, "k3", show_ignored=True)
        page.wait_ev("!$('callout-detail').hidden", timeout=30, label="k3 detail open")
        page.click_selector("#callout-ignore")
        data = UX.wait_server(page, lambda d: reviews(d).get("k3", {}).get("ignored") is True,
                              60, "k3 ignored")
        last = wait_view(page, lambda s: s["remaining"] == "Tüm ölçü/not kontrolleri tamamlandı.", 20,
                         "all-done line after the last row")
        check("S4 last open row with ignored-visible: list intact, row stays selected, all done",
              last["selectedId"] == "k3" and not last["detailHidden"] and len(last["rows"]) == 3
              and last["remaining"] == "Tüm ölçü/not kontrolleri tamamlandı.",
              {"selectedId": last["selectedId"], "rows": last["rows"],
               "remaining": last["remaining"], "revision": data["revision"]})

        # S5 — restore keeps the user where they are (un-ignoring returns the row to its default:
        # the server removes the review row rather than storing ignored=false).
        page.click_selector("#callout-restore")
        data = UX.wait_server(page, lambda d: "k3" not in reviews(d)
                              or reviews(d)["k3"].get("ignored") is False, 60, "k3 restored")
        restored = wait_view(page, lambda s: s["remaining"] == "1 kontrol kaldı", 20,
                             "one open field after restore")
        check("S5 restore: stays on k3, no auto-advance, one open field again",
              restored["selectedId"] == "k3",
              {"selectedId": restored["selectedId"], "remaining": restored["remaining"],
               "review_row_removed": "k3" not in reviews(data), "revision": data["revision"]})

        # S6 — hide ignored rows; ignoring the last open field empties the list cleanly.
        page.click_selector("#callout-show-ignored")
        page.wait_ev("!$('callout-show-ignored').checked", timeout=10, label="show ignored off")
        click_row(page, "k3", show_ignored=False)
        page.wait_ev("!$('callout-detail').hidden", timeout=30, label="k3 detail open again")
        page.click_selector("#callout-ignore")
        data = UX.wait_server(page, lambda d: reviews(d).get("k3", {}).get("ignored") is True,
                              60, "k3 ignored again")
        empty = wait_view(page, lambda s: s["rows"] == [], 20, "list empties")
        page.screenshot(str(HERE / "g11r03-ui-02-all-decided.png"))
        check("S6 last open row hidden: list empties, detail closes, all done",
              empty["rows"] == [] and empty["selectedId"] is None and empty["detailHidden"]
              and empty["remaining"] == "Tüm ölçü/not kontrolleri tamamlandı.",
              {"rows": empty["rows"], "selectedId": empty["selectedId"],
               "detailHidden": empty["detailHidden"], "remaining": empty["remaining"],
               "revision": data["revision"]})

        final_reviews = reviews(data)
        check("S7 server record: all three ignored, five revisions",
              data["revision"] == 5 and len(final_reviews) == 3
              and all(row["ignored"] for row in final_reviews.values()),
              {"revision": data["revision"],
               "reviews": {key: row["ignored"] for key, row in final_reviews.items()}})

        result = {"fixture": meta["url"],
                  "fixture_callouts": ["k1 TITLE", "k2 Ø8 THRU", "k3 M10 - 6H"],
                  "source": "guided.js G11R-03 fix in src/drawingto3d/static (served from disk)",
                  "steps": steps, "failures": failures, "passed": not failures}
    except Exception as error:  # noqa: BLE001 — the failure itself is the result
        result = {"fixture": meta.get("url"), "steps": steps,
                  "failures": failures + [f"{type(error).__name__}: {error}"], "passed": False}
        raise_error: Exception | None = error
    else:
        raise_error = None
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:  # noqa: BLE001 — tab hygiene is best-effort here
                pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    (HERE / "g11r03-ui-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("passed", "failures")}, ensure_ascii=False),
          flush=True)
    if raise_error is not None:
        raise raise_error
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
