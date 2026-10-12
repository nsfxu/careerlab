"""Build the CareerLab Windows installer:  python build.py

1. runs the engine tests,
2. freezes the engine with PyInstaller  -> build/dist/careerlab-engine/
3. packages the Electron app with it    -> dist/CareerLab-Setup-<version>.exe

Needs Python with engine/requirements-dev.txt, and Node (npm install once in app/).
GitHub Actions runs this same script on every v* tag (.github/workflows/release.yml).
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE, APP, BUILD = ROOT / "engine", ROOT / "app", ROOT / "build"


def run(cmd, cwd):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, shell=(sys.platform == "win32" and cmd[0] in ("npm", "npx")))


def main():
    run([sys.executable, "-m", "pytest", "-q", "tests"], ENGINE)
    shutil.rmtree(BUILD / "dist" / "careerlab-engine", ignore_errors=True)
    run([sys.executable, "-m", "PyInstaller", "careerlab_engine.py", "--name", "careerlab-engine",
         "--onedir", "--console",            # console: the engine speaks over stdin/stdout
         "--noconfirm", "--clean",
         "--distpath", BUILD / "dist", "--workpath", BUILD / "work", "--specpath", BUILD,
         "--add-data", f"{ENGINE / 'fl26' / 'assets' / 'DBDump.lua'};fl26/assets",
         "--exclude-module", "tkinter", "--exclude-module", "pytest",
         "--exclude-module", "matplotlib", "--exclude-module", "websocket"], ENGINE)
    if not (APP / "node_modules").exists():
        run(["npm", "install"], APP)
    # publishing is the release workflow's job (and auto-update's, later), never the build's
    builder = ["npx", "electron-builder", "--win", "nsis", "--x64", "--publish", "never"]
    # locally a run right after freezing sometimes fails on a file still held by antivirus /
    # a just-closed CareerLab; a later run succeeds (CI never needed it)
    for attempt in range(3):
        try:
            run(builder, APP)
            break
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            print("electron-builder failed; retrying", flush=True)
            time.sleep(15)
    version = json.loads((APP / "package.json").read_text(encoding="utf-8"))["version"]
    print("installer:", ROOT / "dist" / f"CareerLab-Setup-{version}.exe")


if __name__ == "__main__":
    main()
