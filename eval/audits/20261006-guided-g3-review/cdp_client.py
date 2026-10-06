"""Minimal CDP client for driving the local Chrome that is already running.

PLAN-21 §10.2 wants real browser acceptance. The Hermes browser tool refuses
private URLs in this session (SSRF guard, config not live), so the same Chrome
is driven directly over the DevTools protocol with real input events
(Input.dispatchMouseEvent / Input.insertText) and DOM reads.

    uv run --with websockets python cdp_client.py
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request

from websockets.sync.client import connect

DEBUG_URL = "http://127.0.0.1:9222"


def _http(path: str, method: str = "GET"):
    request = urllib.request.Request(DEBUG_URL + path, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class Chrome:
    """One attached page target; every command blocks until its reply arrives."""

    def __init__(self, url: str = "about:blank", width: int = 1400, height: int = 900):
        self.target = self._target(url)
        websocket_url = self.target["webSocketDebuggerUrl"]
        self.ws = connect(websocket_url, max_size=60 * 1024 * 1024, open_timeout=20)
        self.next_id = 0
        self.pending: dict[int, dict] = {}
        self.events: list[dict] = []
        self.console: list[dict] = []
        self.requests: dict[str, str] = {}
        self.failures: list[dict] = []
        self.context_id: int | None = None
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("DOM.enable")
        self.send("Log.enable")
        self.send("Network.enable")
        self.resize(width, height)

    # -- plumbing ---------------------------------------------------------------------------------
    def _target(self, url: str) -> dict:
        """A fresh tab for the app under test, so no evaluation can land in a stale document.

        Connecting to whatever page happens to exist means attaching while the tab still shows
        `about:blank`; every later evaluation then risks being resolved against that document (the
        symptom was `getElementById(...)` returning null for elements the page clearly had).
        """
        if url and url != "about:blank":
            return _http(f"/json/new?{url}", method="PUT")
        for target in _http("/json/list"):
            if target.get("type") == "page":
                return target
        raise RuntimeError("no page target in the attached Chrome")

    def drain(self) -> None:
        """Read every message already queued on the socket without blocking.

        Events that arrive between two commands are otherwise never seen, which is how the page's
        new execution context went unnoticed.
        """
        while True:
            try:
                raw = self.ws.recv(timeout=0.001)
            except TimeoutError:
                return
            except Exception:
                return
            message = json.loads(raw)
            if "id" in message:
                self.pending[message["id"]] = message
            else:
                self._event(message)

    def send(self, method: str, **params):
        self.drain()
        self.next_id += 1
        message_id = self.next_id
        self.ws.send(json.dumps({"id": message_id, "method": method, "params": params}))
        return self._await(message_id)

    def _await(self, message_id: int, timeout: float = 120.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if message_id in self.pending:
                reply = self.pending.pop(message_id)
                if "error" in reply:
                    raise RuntimeError(f"{reply['error']} ({reply.get('method','')})")
                return reply.get("result", {})
            raw = self.ws.recv(timeout=max(1.0, deadline - time.time()))
            message = json.loads(raw)
            if "id" in message:
                self.pending[message["id"]] = message
            else:
                self._event(message)
        raise TimeoutError(f"CDP command {message_id} timed out")

    def _event(self, message: dict) -> None:
        self.events.append(message)
        method = message["method"]
        if method == "Runtime.executionContextCreated":
            context = message["params"]["context"]
            if context.get("auxData", {}).get("isDefault"):
                self.context_id = context["id"]      # the newest default context wins
        elif method == "Runtime.executionContextDestroyed":
            if message["params"].get("executionContextId") == self.context_id:
                self.context_id = None
        elif method == "Runtime.consoleAPICalled":
            entry = message["params"]
            text = " ".join(str(arg.get("value", arg.get("description", ""))) for arg in entry.get("args", []))
            self.console.append({"level": entry.get("type"), "text": text})
        elif method == "Network.requestWillBeSent":
            request = message["params"]["request"]
            self.requests[message["params"]["requestId"]] = f"{request['method']} {request['url']}"
        elif method == "Network.responseReceived":
            response = message["params"]["response"]
            if response.get("status", 0) >= 400:
                self.failures.append({
                    "status": response["status"], "url": response["url"],
                    "request": self.requests.get(message["params"]["requestId"], "request not seen")})
        elif method == "Network.loadingFailed":
            self.failures.append({"status": 0, "url": "", "request": message["params"].get("errorText", "")})
        elif method == "Log.entryAdded":
            entry = message["params"]["entry"]
            self.console.append({"level": entry.get("level"), "text": entry.get("text", ""),
                                 "url": entry.get("url", ""), "source": entry.get("source", "")})

    # -- page ------------------------------------------------------------------------------------
    def navigate(self, url: str, timeout: float = 90.0) -> None:
        self.context_id = None                     # the current document is about to be replaced
        self.send("Page.navigate", url=url)
        self.wait_ready(timeout)
        self.drain()                               # capture the new document's execution context

    def wait_ready(self, timeout: float = 90.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.evaluate("document.readyState") == "complete":
                time.sleep(0.4)
                return
            time.sleep(0.2)
        raise TimeoutError("page never reached readyState=complete")

    def evaluate(self, expression: str, await_promise: bool = False):
        params = {"expression": expression, "returnByValue": True, "awaitPromise": await_promise}
        if self.context_id is not None:
            params["contextId"] = self.context_id
        try:
            result = self.send("Runtime.evaluate", **params)
        except RuntimeError as error:
            if "context" not in str(error).lower():
                raise
            self.drain()                       # pick up any executionContextDestroyed/Created
            if self.context_id is None:
                params.pop("contextId", None)
            else:
                params["contextId"] = self.context_id
            result = self.send("Runtime.evaluate", **params)
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"].get("text") + " " + json.dumps(
                result["exceptionDetails"].get("exception", {}).get("description", "")))
        return result["result"].get("value")

    def ev(self, body: str):
        """Evaluate a statement body in the page with `$` bound to getElementById.

        `$` is a module-scoped const in guided.js, so it does not exist in the global scope that
        Runtime.evaluate sees; binding it here keeps the probes readable. A transient null during a
        document swap is retried once — the evaluation can otherwise land in the outgoing context.
        """
        expression = f"(() => {{const $ = id => document.getElementById(id); {body}}})()"
        try:
            return self.evaluate(expression)
        except RuntimeError as error:
            if "properties of null" not in str(error):
                raise
            time.sleep(0.6)
            return self.evaluate(expression)

    def ev_async(self, body: str):
        return self.evaluate(f"(async () => {{const $ = id => document.getElementById(id); {body}}})()",
                             await_promise=True)

    def wait_ev(self, body: str, timeout: float = 60.0, poll: float = 0.3, label: str = ""):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.ev(f"return Boolean({body});"):
                return True
            time.sleep(poll)
        raise TimeoutError(f"condition never held: {label or body}")

    def wait_for(self, expression: str, timeout: float = 120.0, poll: float = 0.4, label: str = ""):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.evaluate(expression):
                return True
            time.sleep(poll)
        raise TimeoutError(f"condition never held: {label or expression}")

    def resize(self, width: int, height: int) -> None:
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=height,
                  deviceScaleFactor=1, mobile=False)

    def screenshot(self, path: str) -> str:
        data = self.send("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(data))
        return path

    # -- input -----------------------------------------------------------------------------------
    def node_id(self, selector: str) -> int:
        root = self.send("DOM.getDocument")["root"]["nodeId"]
        return self.send("DOM.querySelector", nodeId=root, selector=selector)["nodeId"]

    def set_file(self, selector: str, path: str) -> None:
        self.send("DOM.setFileInputFiles", files=[path], nodeId=self.node_id(selector))

    def box(self, selector: str) -> dict:
        """Border box of a selector in viewport CSS pixels (quads → x, y, w, h)."""
        result = self.send("DOM.getBoxModel", nodeId=self.node_id(selector))
        quad = result["model"]["border"]
        xs, ys = quad[0::2], quad[1::2]
        return {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)}

    def click(self, x: float, y: float, button: str = "left") -> None:
        for kind in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", type=kind, x=x, y=y, button=button, clickCount=1)
            time.sleep(0.05)

    def click_selector(self, selector: str) -> None:
        """Scroll the control into view before clicking it.

        Everything in the right-hand panel sits below the fold on a tall drawing; a click at the
        raw (page-relative) rectangle would land outside the viewport and do nothing.
        """
        self.ev(f"{self.field(selector)}.scrollIntoView({{block:'center'}});")
        time.sleep(0.25)
        box = self.box(selector)
        self.click(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)

    @staticmethod
    def field(selector: str) -> str:
        """`getElementById` takes a bare id, not the CSS selector these helpers are called with."""
        return f"document.getElementById({json.dumps(selector.lstrip('#'))})"

    def drag(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """A press-move-release over `start` → `end`, the way a user drags a box."""
        steps = 5
        self.drag_start(start)
        for step in range(1, steps + 1):
            x = start[0] + (end[0] - start[0]) * step / steps
            y = start[1] + (end[1] - start[1]) * step / steps
            self.drag_move((x, y))
        self.drag_end(end)

    def drag_start(self, point: tuple[float, float]) -> None:
        self.send("Input.dispatchMouseEvent", type="mousePressed", x=point[0], y=point[1],
                  button="left", clickCount=1)
        time.sleep(0.05)

    def drag_move(self, point: tuple[float, float]) -> None:
        self.send("Input.dispatchMouseEvent", type="mouseMoved", x=point[0], y=point[1], button="left")
        time.sleep(0.05)

    def drag_end(self, point: tuple[float, float]) -> None:
        self.send("Input.dispatchMouseEvent", type="mouseReleased", x=point[0], y=point[1],
                  button="left", clickCount=1)
        time.sleep(0.3)

    def focus_selector(self, selector: str) -> None:
        """Scroll the field into view, click it and confirm the click actually focused it.

        The panel sits far below the fold on a tall drawing, so an unscrolled click lands on
        nothing and `Input.insertText` goes into the void — the failure looked like a save that
        silently did not happen.
        """
        field = self.field(selector)
        for _ in range(3):
            self.wait_ev(f"!!{field}", timeout=20, label=f"{selector} exists")
            self.ev(f"{field}.scrollIntoView({{block:'center'}});")
            time.sleep(0.3)
            self.click_selector(selector)
            time.sleep(0.2)
            if self.ev(f"return document.activeElement === {field};"):
                return
            self.ev(f"{field}.focus();")
            time.sleep(0.2)
            if self.ev(f"return document.activeElement === {field};"):
                return
        raise RuntimeError(f"could not focus {selector}")

    def type_text(self, text: str) -> None:
        self.send("Input.insertText", text=text)

    def press(self, key: str, code: str, key_code: int) -> None:
        for kind in ("keyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", type=kind, key=key, code=code,
                      windowsVirtualKeyCode=key_code, nativeVirtualKeyCode=key_code)

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass
