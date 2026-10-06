"""Reproduce the ignored-callout /save bypass through the real HTTP handler.

Only binds 127.0.0.1 with an OS-assigned port and uses a temporary synthetic store.
Exit 1 means /save still accepts the text that /callout correctly refuses.
"""
import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from drawingto3d import app
from review_probes import H, TOKEN, make_store


def main():
    with tempfile.TemporaryDirectory(prefix="guided-g3-http-review-") as temporary:
        store = make_store(Path(temporary), "session")
        app.GUIDED = store
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def post(path, data):
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}" + path,
                data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(request)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.code, json.load(response)

        try:
            ignored_code, ignored = post("/api/guided/callout", {
                "token": TOKEN, "revision": 0, "action": "set_ignored",
                "payload": {"callout_id": "k1", "ignored": True}})
            assert ignored_code == 200
            revision = ignored["revision"]
            before = H["_session_path"](store).read_bytes()
            command_code, command = post("/api/guided/callout", {
                "token": TOKEN, "revision": revision, "action": "transcribe",
                "payload": {"callout_id": "k1", "raw_text": "Ø8"}})
            command_unchanged = H["_session_path"](store).read_bytes() == before
            save_code, state = post("/api/guided/save", {
                "token": TOKEN, "revision": revision,
                "decisions": H["current_payload"](store, transcriptions=[H["_transcription"]("Ø8")])})
            save_unchanged = H["_session_path"](store).read_bytes() == before
            passed = command_code == save_code == 400 and command_unchanged and save_unchanged
            print(json.dumps({"reviewed_baseline": "2cdb4d0", "command_status": command_code,
                              "command_error": command.get("error"), "command_unchanged": command_unchanged,
                              "save_status": save_code, "save_unchanged": save_unchanged,
                              "saved_callout": state.get("callouts"), "passed": passed},
                             ensure_ascii=False, indent=2))
            return 0 if passed else 1
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
