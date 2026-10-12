"""Progress notes for long engine calls (apply, restore), sent to the app on the protocol
stream as {"event": "progress", "step", "i", "n"} lines without an id. Outside the RPC
server (tests, lab scripts) there is no stream and they go nowhere."""
import json
import time

out = None              # set by rpc.main() to the protocol stream
_last = 0.0


def emit(step, i=0, n=0, force=True):
    """Report `step` (an i18n key suffix), optionally `i` of `n` done. Non-forced notes are
    throttled to ~10 per second so a 700-edit apply does not flood the pipe."""
    global _last
    if out is None:
        return
    now = time.monotonic()
    if not force and now - _last < 0.1:
        return
    _last = now
    out.write(json.dumps({"event": "progress", "step": step, "i": i, "n": n}) + "\n")
    out.flush()
