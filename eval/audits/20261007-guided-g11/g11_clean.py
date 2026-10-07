"""Close every tab in the debug Chrome except the first page, so the runner is not starved."""
import json
import urllib.request

targets = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list"))
pages = [t for t in targets if t.get("type") == "page"]
print("pages before:", len(pages))
kept = 0
closed = 0
for target in pages:
    if target.get("url", "").startswith("about:blank") and kept == 0:
        kept = 1
        continue
    urllib.request.urlopen(f"http://127.0.0.1:9222/json/close/{target['id']}").read()
    closed += 1
print(f"kept={kept} closed={closed}")
left = [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list")) if t.get("type") == "page"]
print("pages after:", len(left))
