"""Screenshot any top-level window by title substring: python winshot.py <title> <out.png> [width]"""
import ctypes
import ctypes.wintypes as wt
import sys

import mss
from PIL import Image

user32 = ctypes.WinDLL("user32")
user32.SetProcessDPIAware()


def find(title):
    hits = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        n = user32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(h, buf, n + 1)
        if buf.value == title and user32.IsWindowVisible(h):
            hits.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return hits[0] if hits else None


if __name__ == "__main__":
    title, out = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    h = find(title)
    if not h:
        sys.exit(f"no window titled {title!r}")
    user32.ShowWindow(h, 9)
    user32.SetForegroundWindow(h)
    r = wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    with mss.MSS() as s:
        g = s.grab({"left": r.left, "top": r.top, "width": r.right - r.left, "height": r.bottom - r.top})
    img = Image.frombytes("RGB", g.size, g.bgra, "raw", "BGRX")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)))
    img.save(out)
    print(out)
