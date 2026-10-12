"""Capture the README screenshots from the running app (dev or packaged) over CDP.

    cd app && npx electron . --remote-debugging-port=9333
    python harness/readme_shots.py            -> docs/screenshots/*.png

Uses the test career (slot 1). Nothing is applied: edits staged for a shot are undone.
Page.captureScreenshot renders the page itself, so the window may be hidden or off-screen.
"""
import base64
import json
import sys
from pathlib import Path

import websocket

from ui import page_ws

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
W, H = 1440, 900


class Page:
    def __init__(self):
        self.ws = websocket.create_connection(page_ws(), timeout=180, suppress_origin=True)
        self.n = 0

    def cmd(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    def js(self, code):
        r = self.cmd("Runtime.evaluate", expression=f"(async()=>{{ {code} }})()",
                     awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    def shot(self, name):
        data = self.cmd("Page.captureScreenshot", format="png")["data"]
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{name}.png").write_bytes(base64.b64decode(data))
        print("saved", name)


PRELUDE = """
const w = (ms) => new Promise((r) => setTimeout(r, ms));
const $ = (s) => document.querySelector(s);
const until = async (f, t = 120) => { for (let i = 0; i < t && !f(); i++) await w(500); };
const club = async (name) => { [...document.querySelectorAll('#club-list li')].find((l) => l.textContent.trim().startsWith(name)).click(); await w(1500); };
const row = async (pred) => { [...document.querySelectorAll('#squad-body tr')].find(pred).click(); await w(1200); };
window.confirm = () => true;
"""


def main():
    p = Page()
    p.cmd("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
    try:
        p.js(PRELUDE + "location.reload();")
    except Exception:
        pass
    import time
    time.sleep(6)
    p = Page()
    p.cmd("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
    run = lambda code: p.js(PRELUDE + code)

    lang = sys.argv[1] if len(sys.argv) > 1 else "en"          # README screenshots are English
    run(f"await until(() => !$('#btn-league').disabled); if (LANG !== '{lang}') {{ await switchLanguage('{lang}'); await w(800); }}"
        "await row((r) => r.textContent.includes('Matheus Pereira'));")
    p.shot("01-squad-and-player")

    run("await row((r) => r.classList.contains('created')); $('.detail').scrollTop = 9999; await w(300);")
    p.shot("02-your-player")

    run("$('.detail').scrollTop = 0; await club('Aston Villa'); $('#btn-sync').click();"
        "await until(() => !/Fetching/.test($('#sync-body').textContent)); await w(800);")
    p.shot("03-club-sync")

    run("$('#btn-sync-stage').click(); await until(() => $('#staged-count').textContent !== '0'); await w(2500);"
        "$('#btn-review').click(); await until(() => /passed|break/.test($('#review-check').textContent));")
    p.shot("04-review-and-apply")

    run("$('#btn-undo-all').click(); await w(800); $('#btn-league').click();"
        "await until(() => $('#league-total').textContent); await w(500);")
    p.shot("05-league-sync")

    run("$('#btn-close-league').click(); await club('Cruzeiro'); await w(3500); $('#btn-backups').click(); await w(1200);"
        "const b = document.querySelector('.bk'); if (b) b.open = true; await w(300);")
    p.shot("06-backups")

    run("$('#btn-close-backups').click(); $('#player-search').value = 'Neymar';"
        "$('#player-search').dispatchEvent(new Event('input')); await w(1500);")
    p.shot("07-search")

    run("$('#search-results').classList.add('hidden'); $('#player-search').value = '';")
    p.cmd("Emulation.clearDeviceMetricsOverride")
    staged = run("return document.querySelector('#staged-count').textContent;")
    if staged != "0":
        sys.exit(f"warning: {staged} edits still staged")


if __name__ == "__main__":
    main()
