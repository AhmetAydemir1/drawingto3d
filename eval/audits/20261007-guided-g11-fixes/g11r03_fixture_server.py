"""Three-callout real UI fixture for the G11R-03 ignore auto-advance check (temporary store).

Same shape as the independent review's two-callout fixture; the third callout lets the check verify
the MID-LIST case (ignore the middle row → the next open field after it, not the first), the
hint-ignore path, the show-ignored on/off states and the last-open-row case. Prints one JSON line
({"url", "session_file"}) and serves until killed. Runs under the project's own venv (PIL).
"""
import json
import runpy
import tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer
from PIL import Image, ImageDraw
from drawingto3d import app

ROOT = Path(__file__).resolve().parents[3]
H = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))
with tempfile.TemporaryDirectory(prefix="guided-g11r03-") as temporary:
    store = H["store"].__wrapped__(Path(temporary))
    r = store.load(H["TOKEN"])
    H["seed_callouts"](store, candidates=[
        H["_candidate_row"](r, "k1", machine_text_hint="TITLE", region=[.1, .1, .3, .3]),
        H["_candidate_row"](r, "k2", machine_text_hint="Ø8 THRU", region=[.4, .1, .6, .3]),
        H["_candidate_row"](r, "k3", machine_text_hint="M10 - 6H", region=[.7, .1, .9, .3])])
    picture = Image.new("RGB", (300, 200), "white")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((20, 20, 120, 80), outline="black")
    draw.text((30, 25), "TITLE", fill="black")
    picture.save(store.folder(H["TOKEN"]) / "drawing.png")
    app.GUIDED = store
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/guided?session={H['TOKEN']}",
                      "session_file": str(H["_session_path"](store))}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
