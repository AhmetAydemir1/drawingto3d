"""Serve the real guided UI with an isolated synthetic session for manual review.

Only local test data. No model, PDF ingestion, CAD or existing session mutation.
"""
import json
import runpy
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw
from drawingto3d import app

ROOT = Path(__file__).resolve().parents[3]
H = runpy.run_path(str(ROOT / "tests/test_guided_callouts.py"))

with tempfile.TemporaryDirectory(prefix="guided-independent-ui-") as temporary:
    store = H["store"].__wrapped__(Path(temporary))
    H["seed_callouts"](store)
    store.edit_callout(H["TOKEN"], 0, "transcribe", {"callout_id": "k1", "raw_text": "Ø8 THRU"})
    drawing = Image.new("RGB", (300, 200), "white")
    canvas = ImageDraw.Draw(drawing)
    canvas.rectangle((10, 10, 290, 190), outline="black")
    canvas.rectangle((20, 20, 120, 80), outline="black")
    for x, y in ((45, 45), (90, 50)):
        canvas.ellipse((x - 6, y - 6, x + 6, y + 6), outline="black")
    drawing.save(store.folder(H["TOKEN"]) / "drawing.png")
    app.GUIDED = store
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/guided?session={H['TOKEN']}",
                      "session_file": str(H["_session_path"](store)),
                      "proposals": store.propose(H["TOKEN"], "k1")["proposals"]}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
