"""Print the release notes for a version, from CHANGELOG.md:  python tools/release_notes.py 1.0.0"""
import re
import sys
from pathlib import Path


def notes(version, changelog):
    m = re.search(rf"^## {re.escape(version)}\b.*?\n(.*?)(?=^## |\Z)", changelog, re.S | re.M)
    body = m.group(1).strip() if m else f"CareerLab {version}"
    return (body + f"\n\n**Install:** download `CareerLab-Setup-{version}.exe` below and run it. "
            "Installed copies update themselves.\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    print(notes(sys.argv[1], (root / "CHANGELOG.md").read_text(encoding="utf-8")), end="")
