"""Drive Football Life 2026 without a human: launch, look, press keys, quit.

    python game.py launch            back up saves, start Sider + the game, wait for the window
    python game.py shot [name] [w]   screenshot the game window to shots/<name>.png (width w)
    python game.py keys <k> [k ...]  press keys, e.g.  keys down down enter  /  keys esc*3
    python game.py status            is the game running, where is its window
    python game.py quit              close the game (and Sider with it)

Keys are sent as DirectInput scan codes via SendInput, which is what the game reads.
Every launch snapshots the save folder first, so a run can never cost a career.
"""
import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

GAME_DIR = Path(r"E:\FL2026")
GAME_EXE = GAME_DIR / "FL_2026.exe"
SIDER_EXE = GAME_DIR / "SiderAddons" / "sider.exe"
SAVE_DIR = Path(os.path.expanduser(r"~\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save"))
BACKUP_ROOT = GAME_DIR / "_archive" / "save-snapshots"
SHOTS = Path(__file__).resolve().parent / "shots"

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.SetProcessDPIAware()

# ---------------------------------------------------------------- processes

def pids(name):
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"')]


def game_window():
    """Largest visible top-level window owned by FL_2026.exe, or None."""
    owners = set(pids("FL_2026.exe"))
    if not owners:
        return None
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in owners and user32.IsWindowVisible(hwnd):
            r = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append(((r.right - r.left) * (r.bottom - r.top), hwnd, (r.left, r.top, r.right, r.bottom)))
        return True

    user32.EnumWindows(cb, 0)
    return max(found)[1:] if found else None


def client_rect(hwnd):
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, pt.x + r.right, pt.y + r.bottom


def park(hwnd):
    """Put the window at the top-left of the primary monitor, clear of the taskbar.

    It opens at a different place every launch, and when its bottom edge goes under the
    taskbar every screenshot (and so every screen match) changes.
    """
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    if (r.left, r.top) != (0, 0):
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0004)   # NOSIZE | NOZORDER
        time.sleep(0.3)


def focus(hwnd):
    # Windows refuses SetForegroundWindow from a background process unless the
    # caller has just produced input; a lone ALT tap satisfies the rule.
    park(hwnd)
    if user32.GetForegroundWindow() == hwnd:
        return
    _scan(0x38, False)
    _scan(0x38, True)
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

# ---------------------------------------------------------------- input

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x8

# name -> (scan code, extended)
KEYS = {
    "esc": (0x01, False), "enter": (0x1C, False), "space": (0x39, False),
    "tab": (0x0F, False), "backspace": (0x0E, False),
    "up": (0x48, True), "down": (0x50, True), "left": (0x4B, True), "right": (0x4D, True),
    "pgup": (0x49, True), "pgdn": (0x51, True), "home": (0x47, True), "end": (0x4F, True),
    "shift": (0x2A, False), "ctrl": (0x1D, False), "alt": (0x38, False),
    **{f"f{i}": (0x3A + i, False) for i in range(1, 11)},
    **{c: (s, False) for c, s in zip("1234567890", range(0x02, 0x0C))},
    **{c: (s, False) for c, s in zip("qwertyuiop", range(0x10, 0x1A))},
    **{c: (s, False) for c, s in zip("asdfghjkl", range(0x1E, 0x27))},
    **{c: (s, False) for c, s in zip("zxcvbnm", range(0x2C, 0x33))},
}


def _scan(code, up, extended=False):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(0, code, flags, 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def press(name, hold=0.08, gap=0.25):
    code, ext = KEYS[name]
    _scan(code, False, ext)
    time.sleep(hold)
    _scan(code, True, ext)
    time.sleep(gap)

# ---------------------------------------------------------------- commands

def snapshot_saves(label="launch"):
    dest = BACKUP_ROOT / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    shutil.copytree(SAVE_DIR, dest)
    return dest


def cmd_launch():
    if pids("FL_2026.exe"):
        print("already running", game_window())
        return
    print("saves snapshot ->", snapshot_saves())
    if not pids("sider.exe"):
        subprocess.Popen([str(SIDER_EXE)], cwd=SIDER_EXE.parent)
        time.sleep(3)
    subprocess.Popen([str(GAME_EXE)], cwd=GAME_DIR)
    for _ in range(120):
        w = game_window()
        if w:
            print("window", w)
            return
        time.sleep(1)
    print("game window did not appear within 120 s")


def cmd_shot(name=None, width="1280"):
    import mss
    from PIL import Image
    w = game_window()
    if not w:
        sys.exit("game not running")
    hwnd, _ = w
    l, t, r, b = client_rect(hwnd)
    with mss.MSS() as s:
        g = s.grab({"left": l, "top": t, "width": r - l, "height": b - t})
    img = Image.frombytes("RGB", g.size, g.bgra, "raw", "BGRX")
    width = int(width)
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)))
    SHOTS.mkdir(exist_ok=True)
    path = SHOTS / f"{name or datetime.now().strftime('%H%M%S')}.png"
    img.save(path)
    print(path)


REFS = SHOTS / "ref"
SIZE = (256, 192)
# Compare only where the screens differ; a small highlight drowns in a full-frame diff.
# Boxes are fractions of the client area (l, t, r, b).
REGIONS = {
    "bal": (0.04, 0.42, 0.32, 0.58),       # Continuar / Novo / Carregar
    "icons": (0.10, 0.50, 0.17, 0.92),     # main-menu icon column
    "tabs": (0.0, 0.15, 0.36, 0.22),       # career hub tab bar, left part
    "popup": (0.04, 0.20, 0.22, 0.27),     # Proxima partida / Pular partida
}
REF_REGION = {"balmenu_cont": "bal", "balmenu_new": "bal", "balmenu_load": "bal",
              "menu_ball": "icons", "menu_ml": "icons", "menu_bal": "icons",
              "menu_edit": "icons", "menu_cfg": "icons", "hub_adv": "tabs", "hub_nt": "tabs", "pop_next": "popup", "pop_skip": "popup",
              "pop_prox": "popup"}


def _grab_small():
    import mss
    from PIL import Image
    w = game_window()
    if not w:
        return None
    park(w[0])
    l, t, r, b = client_rect(w[0])
    with mss.MSS() as s:
        g = s.grab({"left": l, "top": t, "width": r - l, "height": b - t})
    return Image.frombytes("RGB", g.size, g.bgra, "raw", "BGRX").convert("L").resize(SIZE)


def _score(cur, name):
    import numpy as np
    from PIL import Image
    a = np.asarray(cur, float)
    b = np.asarray(Image.open(REFS / f"{name}.png").convert("L").resize(SIZE), float)
    box = REGIONS.get(REF_REGION.get(name, ""))
    if box:
        l, t, r, bt = (int(box[0] * SIZE[0]), int(box[1] * SIZE[1]),
                       int(box[2] * SIZE[0]), int(box[3] * SIZE[1]))
        a, b = a[t:bt, l:r], b[t:bt, l:r]
    return float(np.abs(a - b).mean())


def cmd_ref(name):
    """Save the current screen as reference `name`."""
    REFS.mkdir(parents=True, exist_ok=True)
    _grab_small().save(REFS / f"{name}.png")
    print("saved ref", name)


def classify(names):
    """Which of `names` the screen is closest to, with all scores."""
    cur = _grab_small()
    if cur is None:
        return None, {}
    scores = {n: _score(cur, n) for n in names}
    return min(scores, key=scores.get), scores


def cmd_waitfor(name, timeout="90", tol="1.0"):
    """Block until the screen matches reference `name` (mean abs diff below tol)."""
    end = time.time() + float(timeout)
    best = 999
    while time.time() < end:
        cur = _grab_small()
        if cur is None:
            sys.exit(f"game not running (waiting for {name})")
        best = min(best, _score(cur, name))
        if best < float(tol):
            print(f"at {name} (diff {best:.1f})")
            return
        time.sleep(1)
    sys.exit(f"timeout waiting for {name} (best diff {best:.1f})")


def matches(name, tol=1.0):
    cur = _grab_small()
    return cur is not None and _score(cur, name) < tol


def select(key, target, group, tries=8):
    """Press `key` until, among the refs in `group`, `target` is the closest match.

    Classification instead of a threshold: neighbouring menu items differ by a
    highlight bar, too little for an absolute tolerance to separate reliably.
    """
    w = game_window()
    if not w:
        sys.exit("game not running")
    focus(w[0])
    for i in range(tries + 1):
        time.sleep(0.8)
        best, scores = classify(group)
        margin = sorted(scores.values())[1] - scores[best] if len(scores) > 1 else 0
        if best == target and margin > 1.0:
            print(f"at {target} after {i} x {key} ({', '.join(f'{k} {v:.1f}' for k, v in scores.items())})")
            return
        press(key)
    sys.exit(f"never reached {target}: {scores}")


def cmd_until(key, name, tries="8"):
    """Press `key` until the screen matches `name`; keys get dropped during animations."""
    w = game_window()
    if not w:
        sys.exit("game not running")
    focus(w[0])
    for i in range(int(tries) + 1):
        time.sleep(0.8)
        if matches(name):
            print(f"at {name} after {i} x {key}")
            return
        press(key)
    sys.exit(f"never reached {name}")


def cmd_tolist():
    """Launch if needed and stop on the BAL load list. Never loads a career."""
    if not game_window():
        cmd_launch()
    menus = ("menu_ball", "menu_ml", "menu_bal")
    end = time.time() + 180
    while True:                                        # intro, title, loading
        best, scores = classify(menus + ("title", "about"))
        if best in menus and scores[best] < 5:
            break
        if best == "about" and scores["about"] < 8:     # idle "SP Football Life" screen
            focus(game_window()[0]); press("esc"); time.sleep(2); continue
        if time.time() > end:
            sys.exit("never reached the main menu")
        w = game_window()
        if not w:
            sys.exit("game exited during boot")
        focus(w[0])
        if best == "title" or scores.get("title", 99) < 8 or time.time() < end - 150:
            press("enter")                             # skips the intro and the title
        time.sleep(2)
    select("down", "menu_bal", menus)
    press("enter")
    cmd_waitfor("balmenu_cont", 20, "6")
    select("down", "balmenu_load", ("balmenu_cont", "balmenu_new", "balmenu_load"))
    press("enter")
    cmd_waitfor("list_bal_slot1", 20, "3")
    cmd_shot("list", 640)


def cmd_advance(matches="1", minutes="60"):
    """From the career hub, skip `matches` matches, clicking through every screen.

    Every screen it presses Enter on is saved to shots/advance/ so the run can be audited
    (offers, dialogs). Stops early if the game exits or the time budget runs out.
    """
    log = SHOTS / "advance" / datetime.now().strftime("%H%M%S")
    log.mkdir(parents=True, exist_ok=True)
    end = time.time() + float(minutes) * 60
    done, n = 0, 0
    w = game_window()
    if not w:
        sys.exit("game not running")
    focus(w[0])
    if not matches_hub():
        sys.exit("not on the hub with Avancar o tempo selected")
    while done < int(matches) and time.time() < end:
        press("enter"); time.sleep(1.5)
        best, scores = classify(("pop_next", "pop_skip", "pop_prox"))
        if best == "pop_prox" and scores["pop_prox"] < 15:
            pass                              # single "Proximo": advance to next event, no match
        else:
            # Never trust a blind "down": a dropped key turns "skip" into "play the match".
            select("down", "pop_skip", ("pop_next", "pop_skip"), tries=4)
        press("enter")
        done += 1
        time.sleep(4)
        start_n = n
        while time.time() < end:
            if n - start_n > 40:
                sys.exit(f"match {done} took over 40 screens -- probably being played live; stopping")
            if not game_window():
                sys.exit(f"game exited after {done} matches")
            if matches_hub() and (time.sleep(1.5) or matches_hub()):
                break
            n += 1
            cmd_shot(f"advance/{log.name}/{n:04d}", "480")
            focus(game_window()[0])
            if popup_open():          # never confirm the play/skip menu blindly
                press("esc")
            else:
                press("enter")
            time.sleep(2.5)
        print(f"match {done} done ({n} screens)", flush=True)
    print(f"skipped {done} matches; screens logged in {log}")


HUBS = ("hub_adv", "hub_nt")      # club hub, national-team hub (yellow)


def matches_hub():
    """Career hub with Avancar o tempo selected. Same screen scores ~5, others 35+."""
    cur = _grab_small()
    return cur is not None and min(_score(cur, h) for h in HUBS) < 15


def popup_open():
    cur = _grab_small()
    return cur is not None and min(_score(cur, n) for n in ("pop_next", "pop_skip", "pop_prox")) < 30


def cmd_keys(*names):
    w = game_window()
    if not w:
        sys.exit("game not running")
    focus(w[0])
    for n in names:
        n, _, rep = n.partition("*")
        if n.startswith("wait"):
            time.sleep(float(n[4:] or 1))
            continue
        for _ in range(int(rep or 1)):
            press(n)
    print("sent", " ".join(names))


MACROS = {
    # from the title screen to the BAL load list. Deliberately stops there: the list
    # order is not fixed, so the slot must be confirmed on screen before pressing Enter.
    "loadlist": lambda: ["enter", "wait8", "down", "down", "enter", "wait3",
                         "down", "down", "enter", "wait3"],
    # from the hub to Informações do time > Plano de jogo
    # from the hub to Base de dados > Info. do time > Brasileirao A > Cruzeiro
    "dbcruzeiro": lambda: ["right", "right", "right", "right", "enter", "wait1", "down", "enter",
                           "wait3"] + ["down", "wait0.4"] * 20 + ["enter", "wait2"]
                          + ["down", "wait0.4"] * 4 + ["wait1"],
    "squad": lambda: ["right", "right", "right", "enter", "wait1", "down", "enter", "wait4"],
}


def cmd_macro(name, *args):
    cmd_keys(*MACROS[name](*args))


def cmd_status():
    print("game pids", pids("FL_2026.exe"), "sider pids", pids("sider.exe"))
    w = game_window()
    if w:
        print("window", w, "client", client_rect(w[0]), "foreground", user32.GetForegroundWindow() == w[0])


PROTECTED = ["BL00000001"]   # the user's real career: never left altered by a test run


def protect_check():
    """Restore protected saves to the last launch snapshot if a run changed them."""
    snaps = sorted(BACKUP_ROOT.glob("*-launch"))
    if not snaps:
        return
    for name in PROTECTED:
        ref, cur = snaps[-1] / name, SAVE_DIR / name
        if ref.exists() and cur.exists() and cur.read_bytes() != ref.read_bytes():
            shutil.copy2(cur, BACKUP_ROOT / f"{datetime.now():%Y%m%d-%H%M%S}-ALTERED-{name}")
            shutil.copy2(ref, cur)
            print(f"!!! {name} was changed during the run -- restored from {ref.parent.name}")
        else:
            print(f"{name} unchanged")


def cmd_quit():
    for p in pids("FL_2026.exe"):
        subprocess.run(["taskkill", "/PID", str(p)], capture_output=True)
    for _ in range(20):
        if not pids("FL_2026.exe"):
            break
        time.sleep(1)
    else:
        for p in pids("FL_2026.exe"):
            subprocess.run(["taskkill", "/F", "/PID", str(p)], capture_output=True)
    for p in pids("sider.exe"):
        subprocess.run(["taskkill", "/F", "/PID", str(p)], capture_output=True)
    print("game pids", pids("FL_2026.exe"), "sider pids", pids("sider.exe"))
    protect_check()


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["status"]
    globals()[f"cmd_{cmd}"](*args)
