"""Drive the CareerLab window through the Chrome DevTools Protocol (app started with
--remote-debugging-port=9333). Evaluates JavaScript in the renderer, so UI tests need no
mouse and never touch the user's screen.

    python ui.py "<js expression>"        prints the JSON result (awaits promises)
"""
import json
import sys
import urllib.request

import websocket

PORT = 9333


def page_ws():
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
    return next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")


def evaluate(js, timeout=120):
    ws = websocket.create_connection(page_ws(), timeout=timeout, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                        "params": {"expression": js, "awaitPromise": True, "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == 1:
            ws.close()
            r = msg["result"]
            if "exceptionDetails" in r:
                raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description")
                                   or r["exceptionDetails"]["text"])
            return r["result"].get("value")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(evaluate(sys.argv[1]), ensure_ascii=False, indent=1))
