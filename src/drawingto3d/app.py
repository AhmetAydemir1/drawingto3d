"""Local review UI. Nothing is fetched from the network."""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from drawingto3d.errors import UnavailableModel
from drawingto3d.cadrun import CadFailure
from drawingto3d.ingest import load_page
from drawingto3d.reason import reason_drawing
from drawingto3d.plan import edit_plan
from drawingto3d.guided import GuidedStore
from drawingto3d.schema import ROLES, Audit, ConvertResult, DimensionRecord, Source, Span, View

ROOT = Path(__file__).resolve().parent / "static"
SESSION_DIR = Path("out") / "sessions"
SESSIONS: dict[str, dict] = {}
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
GUIDED = GuidedStore(Path("out") / "guided")


def main() -> None:
    _load_sessions()
    GUIDED.recover_interrupted()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("http://127.0.0.1:8765")
    server.serve_forever()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/guided", "/guided.js", "/preview.js"}:
            name = "guided.html" if path == "/guided" else path[1:]
            kind = "text/html; charset=utf-8" if path == "/guided" else "text/javascript; charset=utf-8"
            self._send(200, kind, (ROOT / name).read_bytes())
            return
        if path.startswith("/api/guided/") or path.startswith("/guided-session/"):
            try:
                if path.startswith("/api/guided/"):
                    self._send(200, "application/json", json.dumps(GUIDED.public(GUIDED.load(path.split("/")[-1]))).encode())
                else:
                    parts = path.strip("/").split("/")
                    if len(parts) != 3: raise ValueError("dosya yolu geçersiz")
                    file, kind = GUIDED.artifact(parts[1], parts[2])
                    self._send(200, kind, file.read_bytes())
            except (ValueError, OSError) as exc:
                self._send(404, "application/json", json.dumps({"error": str(exc)}).encode())
            return
        if path in {"/", "/index.html"}:
            self._send(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
            return
        if path.startswith("/session/"):
            self._session_file(path)
            return
        if path.startswith("/api/job/"):
            self._job(path.removeprefix("/api/job/"))
            return
        self._send(404, "text/plain", b"not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if path.startswith("/api/guided/"):
            try:
                if path == "/api/guided/open":
                    payload = _file_bytes(body)
                    if not payload: raise ValueError("PDF/PNG/JPG dosyası gerekli")
                    result = GUIDED.create(payload)
                else:
                    data = json.loads(body)
                    if not isinstance(data, dict): raise ValueError("karar kaydı nesne olmalı")
                    if path == "/api/guided/save":
                        result = GUIDED.save(data.get("token"), data.get("revision"), data.get("decisions"))
                    elif path == "/api/guided/accept":
                        fields = data.get("fields")
                        if fields is not None and not isinstance(fields, list): raise ValueError("fields liste olmalı")
                        result = GUIDED.accept(data.get("token"), data.get("revision"), fields)
                    elif path == "/api/guided/callout":
                        # PLAN-21 §6.4: one user command on the callout layer, through the same
                        # store lock / revision / save / history path as every other decision.
                        result = GUIDED.edit_callout(data.get("token"), data.get("revision"),
                                                     data.get("action"), data.get("payload"))
                    elif path == "/api/guided/propose":
                        # G5 (PLAN §10): a read — ranked target proposals for one callout, written nowhere.
                        result = GUIDED.propose(data.get("token"), data.get("callout_id"))
                    elif path == "/api/guided/strategy":
                        # G12.2 (PLAN-25 §36): the explicit build strategy — the server pins the key
                        # and the geometry version; the client names the kind and nothing else.
                        result = GUIDED.set_strategy(data.get("token"), data.get("revision"),
                                                     {key: value for key, value in data.items()
                                                      if key not in ("token", "revision")})
                    elif path == "/api/guided/view":
                        # G12.3 (PLAN-25 §47): görünüş rolleri — istemci yalnız aday kimliğini ve rolü
                        # adlandırır; geometry_version'ı sunucu kendi kaydından damgalar.
                        result = GUIDED.set_drawing_view(data.get("token"), data.get("revision"),
                                                         data.get("view_id"), data.get("role"))
                    elif path == "/api/guided/readiness":
                        # G8 (PLAN §14): what the build waits on, in the shared categories.
                        result = GUIDED.readiness(data.get("token"))
                    elif path == "/api/guided/export":
                        # GX (PLAN §12): the review bundle for a session, sources and local artifacts
                        # untouched.
                        result = GUIDED.review_export(data.get("token"))
                    elif path == "/api/guided/import":
                        # GX (PLAN §12): untrusted input — validated against this record, all-or-nothing,
                        # with external_review as its provenance.
                        result = GUIDED.review_import(data.get("token"), data.get("revision"),
                                                      data.get("bundle"))
                    elif path == "/api/guided/undo":
                        result = GUIDED.save(data.get("token"), data.get("revision"), undo=True)
                    elif path == "/api/guided/build":
                        result = GUIDED.build(data.get("token"), data.get("revision"))
                    else: raise ValueError("işlem bulunamadı")
                self._send(200, "application/json", json.dumps(result, ensure_ascii=False).encode())
            except (ValueError, OSError) as exc:
                self._send(400, "application/json", json.dumps({"error":str(exc)}, ensure_ascii=False).encode())
            return
        if path == "/api/convert":
            self._convert(body)
            return
        if path == "/api/solid":
            self._solid(body)
            return
        self._send(404, "text/plain", b"not found")

    def _convert(self, body: bytes) -> None:
        payload = _file_bytes(body)
        if not payload:
            self._send(400, "application/json", b'{"error":"dosya yok"}')
            return
        folder = Path("out") / "upload" / uuid.uuid4().hex
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / "drawing.png"
        if payload[:5] == b"%PDF-":
            source = folder / "drawing.pdf"
        source.write_bytes(payload)
        job_id = _start_reason_job(source, folder / "auto")
        self._send(202, "application/json", json.dumps({"job": job_id}).encode())

    def _solid(self, body: bytes) -> None:
        """Corrected roles come back; the code model builds one solid from them."""
        try:
            data = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, "application/json", '{"error":"gövde okunamadı"}'.encode())
            return
        session = SESSIONS.get(str(data.get("token", "")))
        if session is None:
            self._send(404, "application/json", b'{"error":"oturum yok"}')
            return
        result: ConvertResult = session["result"]
        if result.plate_plan is not None:
            try:
                plan = edit_plan(result.plate_plan, data.get("parameters", {}))
            except (ValueError, TypeError) as exc:
                message = str(exc)
                if isinstance(exc, ValidationError):
                    message = exc.errors()[0]["msg"].removeprefix("Value error, ")
                self._send(400, "application/json", json.dumps({"error": message}, ensure_ascii=False).encode())
                return
            out_dir = Path(session["source"]).parent / "auto"
            job_id = _start_solid_job(session["source"], out_dir, [], result.page, plate_plan=plan)
            self._send(202, "application/json", json.dumps({"job": job_id}).encode())
            return
        try:
            records = merge_records(result.records, data.get("records") or [])
        except (ValueError, TypeError):
            self._send(400, "application/json", '{"error":"kayıt geçersiz"}'.encode())
            return
        if not records:
            self._send(400, "application/json", '{"error":"kayıt yok"}'.encode())
            return
        out_dir = Path(session["source"]).parent / "auto"
        job_id = _start_solid_job(session["source"], out_dir, records, result.page)
        self._send(202, "application/json", json.dumps({"job": job_id}).encode())

    def _job(self, job_id: str) -> None:
        with LOCK:
            job = JOBS.get(job_id)
            if job is None:
                self._send(404, "application/json", b'{"error":"is yok"}')
                return
            payload = {
                "events": list(job["events"]),
                "done": job["done"],
                "error": job["error"],
                "result": job["public"],
            }
        self._send(200, "application/json", json.dumps(payload).encode())

    def _session_file(self, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        token = parts[1] if len(parts) > 1 else ""
        session = SESSIONS.get(token)
        if session is None:
            self._send(404, "text/plain", b"oturum yok")
            return
        result: ConvertResult = session["result"]
        if path.endswith("/drawing") and result.page is not None:
            self._send(200, "image/png", result.page.image_png)
            return
        if path.endswith("/part.stl") and result.stl_path:
            self._send(200, "model/stl", Path(result.stl_path).read_bytes())
            return
        if path.endswith("/part.step") and result.step_path:
            self._send(200, "application/step", Path(result.step_path).read_bytes())
            return
        if path.endswith("/audit.json"):
            self._send(200, "application/json", result.audit.model_dump_json().encode())
            return
        if path.endswith("/plan.json") and result.plate_plan:
            self._send(200, "application/json", result.plate_plan.model_dump_json(indent=2).encode())
            return
        self._send(404, "text/plain", b"not found")

    def _send(self, status: int, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        return


def _start_reason_job(source, out_dir) -> str:
    job_id = uuid.uuid4().hex[:8]
    job = {"events": [], "done": False, "error": None, "public": None}
    with LOCK:
        JOBS[job_id] = job

    def progress(title: str, detail: str) -> None:
        with LOCK:
            job["events"].append({"title": title, "detail": detail})

    def run() -> None:
        try:
            result = reason_drawing(source, out_dir, progress=progress, prefer_plan=True)
            _remember(job_id, source, result)
            with LOCK:
                job["public"] = _public(result, job_id)
                job["done"] = True
        except UnavailableModel:
            _fail(job, "Yerel model yanıt vermiyor.")
        except CadFailure:
            _fail(job, "CadQuery programı çalışmadı.")
        except Exception:
            _fail(job, "İş tamamlanamadı.")

    threading.Thread(target=run, daemon=True).start()
    return job_id


def merge_records(current: list[DimensionRecord], edits: list[dict]) -> list[DimensionRecord]:
    """Apply the user's role and value edits by span_id. Edited rows are marked as user input."""
    by_id = {record.span_id: record for record in current}
    for edit in edits:
        span_id = str(edit.get("span_id", ""))
        record = by_id.get(span_id)
        if record is None:
            continue
        changed = False
        role = edit.get("role")
        if role is not None and role != record.role:
            if role not in ROLES:
                raise ValueError(f"bilinmeyen rol: {role}")
            record.role = role
            changed = True
        if edit.get("value") is not None:
            value = float(edit["value"])
            if value <= 0:
                raise ValueError("değer pozitif olmalı")
            if abs(value - record.value) > 1e-9:
                record.value = value
                changed = True
        if edit.get("count") is not None:
            count = int(edit["count"])
            if count < 1:
                raise ValueError("adet en az 1")
            if count != record.count:
                record.count = count
                changed = True
        if changed:
            record.source = Source.user
    return list(by_id.values())


def _start_solid_job(source, out_dir, records: list[DimensionRecord], page, plate_plan=None) -> str:
    job_id = uuid.uuid4().hex[:8]
    job = {"events": [], "done": False, "error": None, "public": None}
    with LOCK:
        JOBS[job_id] = job

    def progress(title: str, detail: str) -> None:
        with LOCK:
            job["events"].append({"title": title, "detail": detail})

    def run() -> None:
        try:
            result = reason_drawing(source, out_dir, records=records, progress=progress, plate_plan=plate_plan)
            if result.page is not None and page is not None:
                result.page.spans = list(page.spans)
                result.page.views = list(page.views)
            _remember(job_id, source, result)
            with LOCK:
                job["public"] = _public(result, job_id)
                job["done"] = True
        except UnavailableModel:
            _fail(job, "Yerel model yanıt vermiyor.")
        except CadFailure as exc:
            detail = " — ".join(line.strip() for line in exc.stderr.strip().splitlines()[-2:] if line.strip())
            _fail(job, "CadQuery programı çalışmadı." + (f" Son hata: {detail[:240]}" if detail else ""))
        except Exception:
            _fail(job, "İş tamamlanamadı.")

    threading.Thread(target=run, daemon=True).start()
    return job_id


def _fail(job: dict, message: str) -> None:
    with LOCK:
        job["events"].append({"title": "Durdu", "detail": message})
        job["error"] = message
        job["done"] = True


def _file_bytes(body: bytes) -> bytes:
    if body.startswith((b"%PDF-", b"\x89PNG", b"\xff\xd8")):
        return body
    marker = body.split(b"\r\n", 1)[0]
    start = body.find(b"\r\n\r\n")
    if start < 0 or not marker.startswith(b"--"):
        return b""
    payload = body[start + 4 :]
    end = payload.rfind(b"\r\n" + marker)
    if end >= 0:
        payload = payload[:end]
    return payload


def _remember(token: str, source, result: ConvertResult) -> None:
    """Keep the sheet in memory and on disk so a restart does not drop the open review."""
    SESSIONS[token] = {"source": str(source), "result": result}
    page = result.page
    payload = {
        "source": str(source),
        "accepted": result.audit.accepted,
        "records": [record.model_dump() for record in result.records],
        "spans": [span.model_dump() for span in page.spans] if page else [],
        "views": [view.model_dump() for view in page.views] if page else [],
        "step_path": result.step_path,
        "stl_path": result.stl_path,
        "plate_plan": result.plate_plan.model_dump() if result.plate_plan else None,
        "audit": result.audit.model_dump(),
        "questions": [q.model_dump() for q in result.questions],
    }
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    (SESSION_DIR / f"{token}.json").write_text(json.dumps(payload), encoding="utf-8")


def _load_sessions() -> None:
    if not SESSION_DIR.is_dir():
        return
    for path in SESSION_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            page = load_page(data["source"])
            page.spans = [Span.model_validate(item) for item in data.get("spans") or []]
            page.views = [View.model_validate(item) for item in data.get("views") or []]
            result = ConvertResult(
                audit=Audit.model_validate(data.get("audit", {"accepted": bool(data.get("accepted"))})),
                records=[DimensionRecord.model_validate(item) for item in data.get("records") or []],
                page=page,
                step_path=data.get("step_path"),
                stl_path=data.get("stl_path"),
                plate_plan=data.get("plate_plan"),
                questions=data.get("questions", []),
            )
            SESSIONS[path.stem] = {"source": data["source"], "result": result}
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            continue


def _public(result: ConvertResult, token: str) -> dict:
    page = result.page
    return {
        "token": token,
        "accepted": result.audit.accepted,
        "questions": [question.model_dump() for question in result.questions],
        "bindings": [entry.model_dump() for entry in result.audit.entries],
        "records": [record.model_dump() for record in result.records],
        "plate_plan": result.plate_plan.model_dump() if result.plate_plan else None,
        "roles": list(ROLES),
        "spans": [span.model_dump() for span in page.spans] if page else [],
        "views": [view.model_dump() for view in page.views] if page else [],
        "step": f"/session/{token}/part.step" if result.step_path else None,
        "stl": f"/session/{token}/part.stl" if result.stl_path else None,
        "audit": f"/session/{token}/audit.json",
        "plan": f"/session/{token}/plan.json" if result.plate_plan else None,
        "drawing": f"/session/{token}/drawing",
    }


if __name__ == "__main__":
    main()
